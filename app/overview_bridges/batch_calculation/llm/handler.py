"""LLM handler for batch calculation chat functionality."""

import os
import re
from typing import Any

try:
    from openai import OpenAI  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - fallback for environments without openai installed
    OpenAI = None  # type: ignore[assignment, misc]

from viktor.errors import UserError

from .context import build_batch_chat_context, format_chat_dataset_for_prompt
from .system_prompt import build_system_prompt


def _format_newlines_for_viktor(text: str) -> str:
    r"""
    Format newlines for proper display in VIKTOR Chat component.

    VIKTOR's Chat doesn't render single \\n as line breaks.
    This converts single newlines to double newlines for proper paragraph spacing.

    :param text: Raw text from LLM
    :type text: str
    :returns: Text with formatted newlines
    :rtype: str
    """
    # Replace single newlines with double newlines (but preserve existing double newlines)
    # First normalize: replace 2+ newlines with a placeholder
    text = re.sub(r"\n{2,}", "<<PARAGRAPH>>", text)
    # Then convert single newlines to double
    text = text.replace("\n", "\n\n")
    # Restore paragraphs (which should stay as double newlines)
    return text.replace("<<PARAGRAPH>>", "\n\n")


def _extract_answer_from_response(response: Any) -> str | None:  # noqa: ANN401, C901, PLR0912
    """
    Extract answer text from OpenAI response object.

    :param response: OpenAI response object
    :type response: Any
    :returns: Answer text or None if not found
    :rtype: str | None
    """
    answer = getattr(response, "output_text", None)
    if answer:
        return _format_newlines_for_viktor(answer)

    fragments: list[str] = []
    output = getattr(response, "output", None)
    if output and isinstance(output, list):
        for item in output:
            contents = getattr(item, "content", None)
            if not contents:
                contents = item.get("content") if isinstance(item, dict) else None
            if not contents:
                continue
            for chunk in contents:
                text_obj = getattr(chunk, "text", None)
                if text_obj is None and isinstance(chunk, dict):
                    text_obj = chunk.get("text")
                if isinstance(text_obj, str):
                    fragments.append(text_obj)
                elif hasattr(text_obj, "value"):
                    value = getattr(text_obj, "value", None)
                    if value is not None:
                        fragments.append(str(value))
                elif isinstance(text_obj, dict):
                    value = text_obj.get("value") or text_obj.get("text")
                    if isinstance(value, str):
                        fragments.append(value)

    if not fragments and hasattr(response, "model_dump"):
        try:
            dumped = response.model_dump()
            for item in dumped.get("output", []):
                for content in item.get("content", []):
                    text_obj = content.get("text")
                    if isinstance(text_obj, dict):
                        value = text_obj.get("value") or text_obj.get("text")
                        if value:
                            fragments.append(str(value))
                    elif isinstance(text_obj, str):
                        fragments.append(text_obj)
        except Exception:
            pass

    if fragments:
        return _format_newlines_for_viktor("\n".join(fragments))
    return None


def _handle_incomplete_response(response: Any) -> str:  # noqa: ANN401
    """
    Handle incomplete response from OpenAI API.

    :param response: OpenAI response object
    :type response: Any
    :returns: Error message for incomplete response
    :rtype: str
    """
    status = getattr(response, "status", None)
    incomplete_details = getattr(response, "incomplete_details", None)
    if status == "incomplete" and incomplete_details:
        reason = getattr(incomplete_details, "reason", "unknown")
        if reason == "max_output_tokens":
            return (
                "Het AI-model heeft de maximale tokenlimiet bereikt tijdens het redeneren. Probeer een kortere of meer specifieke vraag te stellen."
            )
        return f"Het antwoord is onvolledig (reden: {reason}). Probeer het opnieuw."
    return "Er is geen antwoord ontvangen van het LLM."


def _build_openai_messages(dataset_summary: str, messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Build OpenAI messages list from dataset summary and conversation messages.

    :param dataset_summary: Formatted dataset summary
    :type dataset_summary: str
    :param messages: List of conversation messages
    :type messages: list[dict[str, Any]]
    :returns: List of OpenAI message dictionaries
    :rtype: list[dict[str, str]]
    """
    system_prompt = build_system_prompt(dataset_summary)

    openai_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    user_message_present = False
    for message in messages or []:
        role = message.get("role")
        content = message.get("content")
        if not content or not role:
            continue
        if role == "user":
            user_message_present = True
        openai_messages.append({"role": str(role), "content": str(content)})

    if not user_message_present:
        openai_messages.append(
            {
                "role": "user",
                "content": (
                    "De gebruiker heeft nog geen vraag gesteld. Geef alleen een vriendelijke begroeting "
                    "van maximaal 1 zin. Geef GEEN samenvatting, overzicht of voorbeeldvragen."
                ),
            }
        )

    return openai_messages


def generate_batch_chat_response(entity_id: int, messages: list[dict[str, Any]]) -> str:
    """
    Generate a chat response for batch calculation results using OpenAI GPT-5 Nano.

    :param entity_id: Overview Bridges entity ID
    :type entity_id: int
    :param messages: List of conversation messages
    :type messages: list[dict[str, Any]]
    :returns: Response text from the LLM, or error message string
    :rtype: str
    :raises UserError: If API key is missing or OpenAI package is not installed
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise UserError(
            "Er is geen OPENAI_API_KEY geconfigureerd. Stel deze in via `viktor-cli start --env OPENAI_API_KEY=...` "
            "of via de Apps > Variables pagina."
        )

    dataset = build_batch_chat_context(entity_id)
    if not dataset.get("bridges"):
        raise UserError("Er zijn nog geen batchresultaten beschikbaar voor deze overzichtsentity. Voer eerst een batchberekening uit.")

    dataset_summary = format_chat_dataset_for_prompt(dataset)
    openai_messages = _build_openai_messages(dataset_summary, messages)

    if OpenAI is None:
        raise UserError("De Python-package 'openai' is niet geïnstalleerd. Installeer deze afhankelijkheid om de chatfunctie te gebruiken.")

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(  # type: ignore[call-overload]
            model="gpt-5-nano",
            input=openai_messages,
            max_output_tokens=30000,
            reasoning={"effort": "low"},
        )
        answer = _extract_answer_from_response(response)

        if not answer:
            answer = _handle_incomplete_response(response)
    except Exception as exc:
        raise UserError("Het is niet gelukt om een antwoord op te halen van de AI-service. Probeer het later nog eens.") from exc

    return answer
