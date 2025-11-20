"""LLM handler for batch calculation chat functionality."""

import os
from typing import Any

try:
    from openai import OpenAI
except ModuleNotFoundError:  # pragma: no cover - fallback for environments without openai installed
    OpenAI = None  # type: ignore[assignment]

from viktor.errors import UserError

from .context import build_batch_chat_context, format_chat_dataset_for_prompt


def generate_batch_chat_response(entity_id: int, messages: list[dict[str, Any]]) -> str:  # noqa: ANN401
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
        raise UserError(
            "Er zijn nog geen batchresultaten beschikbaar voor deze overzichtsentity. Voer eerst een batchberekening uit."
        )

    dataset_summary = format_chat_dataset_for_prompt(dataset)
    system_prompt = (
        "Je naam is RoboLong, een data-assistent die helpt met het opzoeken en filteren van batchresultaten van plaatbruggen. "
        "Je favoriete brug is de Berlage brug (hoewel deze niet in de huidige dataset voorkomt). "
        "Je rol is UITSLUITEND het verstrekken van informatie op basis van de beschikbare data. "
        "\n\n"
        "BELANGRIJKE REGELS:\n"
        "- Beantwoord ALLEEN wat letterlijk gevraagd wordt - geef GEEN extra informatie, suggesties, of adviezen\n"
        "- Bij vragen zoals 'wat kun je doen?' of 'hoe kan je helpen?', geef een korte lijst van MOGELIJKE vragen (bijv. 'Je kunt vragen stellen over UC-waarden, bruggen per bouwjaar, ontbrekende gegevens, etc.') - geef GEEN data of samenvattingen\n"
        "- Bij begroetingen (zoals 'hallo', 'hi'), groet kort terug en wacht op een vraag\n"
        "- Doe GEEN aanbevelingen, geef GEEN workflow-tips, stel GEEN acties voor\n"
        "- Gebruik het woord 'samengevat' NOOIT - geef samenvattingen alleen als expliciet gevraagd (bijv. 'geef een samenvatting')\n"
        "- Rapporteer alleen feiten uit de data, zonder interpretatie of advies\n"
        "\n\n"
        "COMMUNICATIE & PRESENTATIE:\n"
        "- Gebruik vakjargon natuurlijk (bijv. 'UC-waarde', 'berekening') maar verberg interne implementatiedetails\n"
        "- Spreek over 'berekende bruggen', 'bruggen waar gegevens ontbreken' - NIET 'calculated', 'pending', 'not_ready', 'failed'\n"
        "- Als een brug berekend is ('berekeningsresultaten beschikbaar' of 'berekend'), vermeld dan NOOIT 'ontbrekende velden' - die zijn per definitie aanwezig\n"
        "- Rapporteer UC-waarden als getallen (bijv. 'UC 1,25') zonder format-details te noemen\n"
        "- Gebruik opmaak voor leesbaarheid: bullet points (•), regelafbrekingen, en structuur\n"
        "- Presenteer lijsten overzichtelijk met één brug per regel\n"
        "- Wees beknopt maar leesbaar - vermeld alleen wat direct relevant is voor de vraag\n"
        "\n\n"
        "BESCHIKBARE VELDEN PER BRUG:\n"
        "Basis identificatie: objectnummer (BRU-code), naam, bouwjaar, lengte, breedte\n"
        "Locatie: straat, stadsdeel\n"
        "Structurele eigenschappen: type, gebruik, voorgespannen (ja/nee), aantal_velden, statisch_systeem, kruisingshoek\n"
        "Design parameters (berekende bruggen): CC-klasse, berekeningsniveau, ontwerpcode, betonklasse, staalsoort, belastingzones, "
        "dekdikte (zones 1/3 en zone 2), segmentgeometrie (aantal segmenten, lengtes, breedtes, opleggingen)\n"
        "Resultaten (berekende bruggen): max UC, status, gefaalde checks, UC details per type (capaciteit, schuifkracht, torsie, interactie, scheurwijdte, detailing, spanningslimieten)\n"
        "Prioriteit: vlag_arb (rood/oranje/groen)\n"
        "\n\n"
        "BESCHIKBARE DATA:\n"
        f"{dataset_summary}"
    )

    openai_messages = [{"role": "system", "content": system_prompt}]
    user_message_present = False
    for message in messages or []:
        role = message.get("role")
        content = message.get("content")
        if not content:
            continue
        if role == "user":
            user_message_present = True
        openai_messages.append({"role": role, "content": content})

    if not user_message_present:
        openai_messages.append(
            {
                "role": "user",
                "content": "De gebruiker heeft nog geen vraag gesteld. Geef alleen een vriendelijke begroeting van maximaal 1 zin. Geef GEEN samenvatting, overzicht of voorbeeldvragen.",
            }
        )

    if OpenAI is None:
        raise UserError(
            "De Python-package 'openai' is niet geïnstalleerd. Installeer deze afhankelijkheid om de chatfunctie te gebruiken."
        )

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model="gpt-5-nano",
            input=openai_messages,
            max_output_tokens=30000,  # Increased to allow for reasoning + actual response
            reasoning={"effort": "low"},  # Use low effort reasoning to save tokens for the actual answer
        )
        answer = getattr(response, "output_text", None)
        if not answer:
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
                            fragments.append(str(text_obj.value))
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
                except Exception as dump_error:
                    print(f"DEBUG: Failed to parse OpenAI response via model_dump: {dump_error}")
                    print(f"DEBUG: Raw response dump: {response}")
            if fragments:
                answer = "\n".join(fragments)
            else:
                try:
                    print(f"DEBUG: OpenAI response without text: {response}")
                except Exception:
                    pass

        # Check if response was incomplete
        if not answer:
            status = getattr(response, "status", None)
            incomplete_details = getattr(response, "incomplete_details", None)
            if status == "incomplete" and incomplete_details:
                reason = getattr(incomplete_details, "reason", "unknown")
                if reason == "max_output_tokens":
                    answer = (
                        "Het AI-model heeft de maximale tokenlimiet bereikt tijdens het redeneren. "
                        "Probeer een kortere of meer specifieke vraag te stellen."
                    )
                else:
                    answer = f"Het antwoord is onvolledig (reden: {reason}). Probeer het opnieuw."
            else:
                answer = "Er is geen antwoord ontvangen van het LLM."
    except Exception as exc:
        print(f"ERROR: OpenAI request failed: {exc}")
        raise UserError("Het is niet gelukt om een antwoord op te halen van de AI-service. Probeer het later nog eens.") from exc

    return answer

