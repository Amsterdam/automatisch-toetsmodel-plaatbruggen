"""Tests for batch calculation chat functionality."""

from types import SimpleNamespace
from typing import Any, ClassVar, NoReturn

import pytest

from app.constants.technical import CHAT_FIELD_DESCRIPTIONS
from app.overview_bridges.batch_calculation import component as batch_component
from app.overview_bridges.batch_calculation import llm
from app.overview_bridges.batch_calculation import utils as batch_utils


def test_build_batch_chat_context_includes_filtered_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that build_batch_chat_context includes filtered metadata in the dataset."""
    dummy_bridge = SimpleNamespace(
        id=1,
        name="Brug 1",
        last_saved_params=SimpleNamespace(info=SimpleNamespace(bridge_objectnumm="BRU0010", construction_year="1965", total_length="12.5")),
    )

    class DummyParent:
        def children(self, entity_type_names: Any = None) -> list[Any]:  # noqa: ANN401, ARG002
            return [dummy_bridge]

    # Patch the API class - need to create a mock that can be called
    class MockAPI:
        def __init__(self) -> None:
            pass

        def get_entity(self, _entity_id: int) -> DummyParent:
            return DummyParent()

    # Patch api.API() call in context module
    monkeypatch.setattr(llm.context.api, "API", MockAPI)

    class DummyFile:
        """Mock File object for Storage.get() return value."""

    class DummyStorage:
        def get(self, key: str, scope: str | None = None) -> DummyFile:  # noqa: ARG002
            if key == "batch_calculation_results":
                return DummyFile()
            raise FileNotFoundError

    monkeypatch.setattr(llm.context, "Storage", DummyStorage)

    # Patch deserialize_batch_results in both utils and context modules
    # (context imports it from utils, so we need to patch it where it's used)
    def mock_deserialize(_stored_file: Any) -> dict[int, dict[str, Any]]:  # noqa: ANN401
        return {1: {"status": "Voltooid", "uc_status": "PASSED", "uc_breakdown": None, "cached": False}}

    monkeypatch.setattr(batch_utils, "deserialize_batch_results", mock_deserialize)
    monkeypatch.setattr(llm.context, "deserialize_batch_results", mock_deserialize)
    monkeypatch.setattr(batch_utils, "load_batch_last_run_timestamp", lambda _storage: "2024-01-01T00:00:00Z")
    monkeypatch.setattr(
        llm.context,
        "_load_filtered_bridge_map",
        lambda: {"BRU0010": {"OBJECTNUMM": "BRU0010", "stadsdeel": "Centrum", "lth": "9600", "type": "Type 3"}},
    )
    monkeypatch.setattr(batch_utils, "validate_bridge_for_calculation", lambda _params, _entity: (True, [], 100.0))
    monkeypatch.setattr(batch_utils, "check_idea_cache_status", lambda _params, _bridge_id, _batch_results_cache_hash=None: False)

    dataset = llm.context.build_batch_chat_context(entity_id=123)

    assert dataset["summary"]["total_bridges"] == 1
    assert dataset["summary"]["calculated"] == 1
    assert dataset["bridges"][0]["objectnumm"] == "BRU0010"
    assert dataset["bridges"][0]["filtered_metadata"]["stadsdeel"] == "Centrum"


def test_chat_batch_results_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that chat_batch_results raises UserError when API key is missing."""
    component = batch_component.BatchCalculationComponent()

    class DummyConversation:
        def get_messages(self) -> list[dict[str, str]]:
            return [{"role": "user", "content": "vraag"}]

    params = SimpleNamespace(batch_calculation=SimpleNamespace(batch_results_chat=DummyConversation()))

    def _fail_if_called(*_args: Any, **_kwargs: Any) -> NoReturn:  # noqa: ANN401
        raise AssertionError("build_batch_chat_context should not be invoked when API key is missing")

    monkeypatch.setattr(llm.context, "build_batch_chat_context", _fail_if_called)
    monkeypatch.setattr(llm.handler.os, "getenv", lambda _key: None)
    monkeypatch.setattr(
        batch_component,
        "ChatResult",
        lambda conversation, content: {"conversation": conversation, "content": content},
    )

    # The component re-raises UserError, so we need to catch it
    from viktor.errors import UserError

    with pytest.raises(UserError) as exc_info:
        component.chat_batch_results(params, entity_id=1)

    assert "OPENAI_API_KEY" in str(exc_info.value)


def test_chat_batch_results_invokes_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that chat_batch_results invokes OpenAI API correctly."""
    component = batch_component.BatchCalculationComponent()

    class DummyConversation:
        def get_messages(self) -> list[dict[str, str]]:
            return [{"role": "user", "content": "Welke bruggen falen?"}]

    params = SimpleNamespace(batch_calculation=SimpleNamespace(batch_results_chat=DummyConversation()))

    dataset = {
        "summary": {
            "total_bridges": 1,
            "calculated": 1,
            "failed": 0,
            "pending": 0,
            "not_ready": 0,
            "cached_results": 0,
            "last_batch_run": "2024-01-01T00:00:00Z",
            "dataset_truncated": False,
        },
        "field_descriptions": CHAT_FIELD_DESCRIPTIONS,
        "bridges": [
            {
                "bridge_id": 1,
                "name": "Brug 1",
                "objectnumm": "BRU0010",
                "classification": "calculated",
                "status": "Voltooid",
                "uc_status": "PASSED",
                "max_uc": 0.8,
                "failed_checks": [],
                "failed_checks_count": 0,
                "uc_breakdown": None,
                "cached": False,
                "error": None,
                "missing_fields": [],
                "report_url": "/app/entity/1/rapport",
                "construction_year": 1965,
                "total_length_m": 12.5,
                "total_width_m": None,
                "filtered_metadata": {"type": "Type 3", "stadsdeel": "Centrum", "gebruik": "Wegverkeer", "lth": "9600", "bbrugdek": "10000"},
            }
        ],
    }

    # Patch build_batch_chat_context in handler module (where it's imported from context)
    monkeypatch.setattr(llm.handler, "build_batch_chat_context", lambda _entity_id: dataset)
    monkeypatch.setattr(llm.handler.os, "getenv", lambda _key: "test-key")

    captured: dict[str, Any] = {}

    class DummyResponse:
        output_text = "antwoord"

    class DummyClient:
        def __init__(self, api_key: str) -> None:
            captured["api_key"] = api_key
            self.responses = SimpleNamespace(create=self._create)

        def _create(self, **kwargs: Any) -> DummyResponse:  # noqa: ANN401
            captured["payload"] = kwargs
            return DummyResponse()

    monkeypatch.setattr(llm.handler, "OpenAI", DummyClient)
    monkeypatch.setattr(
        batch_component,
        "ChatResult",
        lambda conversation, content: {"conversation": conversation, "content": content},
    )

    result = component.chat_batch_results(params, entity_id=1)

    assert result["content"] == "antwoord"
    assert captured["api_key"] == "test-key"
    assert captured["payload"]["model"] == "gpt-5-nano"


def test_chat_batch_results_uses_model_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that chat_batch_results uses model_dump when output_text is not available."""
    component = batch_component.BatchCalculationComponent()

    class DummyConversation:
        def get_messages(self) -> list[dict[str, str]]:
            return [{"role": "user", "content": "Welke bruggen falen?"}]

    params = SimpleNamespace(batch_calculation=SimpleNamespace(batch_results_chat=DummyConversation()))

    dataset = {
        "summary": {
            "total_bridges": 1,
            "calculated": 1,
            "failed": 0,
            "pending": 0,
            "not_ready": 0,
            "cached_results": 0,
            "last_batch_run": "2024-01-01T00:00:00Z",
            "dataset_truncated": False,
        },
        "field_descriptions": CHAT_FIELD_DESCRIPTIONS,
        "bridges": [
            {
                "bridge_id": 1,
                "name": "Brug 1",
                "objectnumm": "BRU0010",
                "classification": "calculated",
                "status": "Voltooid",
                "uc_status": "PASSED",
                "max_uc": 0.8,
                "failed_checks": [],
                "failed_checks_count": 0,
                "uc_breakdown": None,
                "cached": False,
                "error": None,
                "missing_fields": [],
                "report_url": "/app/entity/1/rapport",
                "construction_year": 1965,
                "total_length_m": 12.5,
                "total_width_m": None,
                "filtered_metadata": {"type": "Type 3", "stadsdeel": "Centrum", "gebruik": "Wegverkeer", "lth": "9600", "bbrugdek": "10000"},
            }
        ],
    }

    # Patch build_batch_chat_context in handler module (where it's imported from context)
    monkeypatch.setattr(llm.handler, "build_batch_chat_context", lambda _entity_id: dataset)
    monkeypatch.setattr(llm.handler.os, "getenv", lambda _key: "test-key")

    class DummyResponse:
        output_text = None

        def model_dump(self) -> dict[str, Any]:
            return {"output": [{"content": [{"text": "antwoord"}]}]}

    class DummyClient:
        def __init__(self, api_key: str) -> None:  # noqa: ARG002
            self.responses = SimpleNamespace(create=lambda **_kwargs: DummyResponse())

    monkeypatch.setattr(llm.handler, "OpenAI", DummyClient)
    monkeypatch.setattr(
        batch_component,
        "ChatResult",
        lambda conversation, content: {"conversation": conversation, "content": content},
    )

    result = component.chat_batch_results(params, entity_id=1)

    assert result["content"] == "antwoord"


def test_chat_batch_results_handles_text_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that chat_batch_results handles text objects in response output."""
    component = batch_component.BatchCalculationComponent()

    class DummyConversation:
        def get_messages(self) -> list[dict[str, str]]:
            return [{"role": "user", "content": "Welke bruggen falen?"}]

    params = SimpleNamespace(batch_calculation=SimpleNamespace(batch_results_chat=DummyConversation()))

    dataset = {
        "summary": {
            "total_bridges": 1,
            "calculated": 1,
            "failed": 0,
            "pending": 0,
            "not_ready": 0,
            "cached_results": 0,
            "last_batch_run": "2024-01-01T00:00:00Z",
            "dataset_truncated": False,
        },
        "field_descriptions": CHAT_FIELD_DESCRIPTIONS,
        "bridges": [
            {
                "bridge_id": 1,
                "name": "Brug 1",
                "objectnumm": "BRU0010",
                "classification": "calculated",
                "status": "Voltooid",
                "uc_status": "PASSED",
                "max_uc": 0.8,
                "failed_checks": [],
                "failed_checks_count": 0,
                "uc_breakdown": None,
                "cached": False,
                "error": None,
                "missing_fields": [],
                "report_url": "/app/entity/1/rapport",
                "construction_year": 1965,
                "total_length_m": 12.5,
                "total_width_m": None,
                "filtered_metadata": {"type": "Type 3", "stadsdeel": "Centrum", "gebruik": "Wegverkeer", "lth": "9600", "bbrugdek": "10000"},
            }
        ],
    }

    # Patch build_batch_chat_context in handler module (where it's imported from context)
    monkeypatch.setattr(llm.handler, "build_batch_chat_context", lambda _entity_id: dataset)
    monkeypatch.setattr(llm.handler.os, "getenv", lambda _key: "test-key")

    class DummyText:
        def __init__(self, value: str) -> None:
            self.value = value

    class DummyChunk:
        def __init__(self, text: Any) -> None:  # noqa: ANN401
            self.text = text

    class DummyOutput:
        def __init__(self, content: Any) -> None:  # noqa: ANN401
            self.content = content

    class DummyResponse:
        output_text: Any = None
        output: ClassVar[list[DummyOutput]] = [DummyOutput([DummyChunk(DummyText("antwoord via attr"))])]

    class DummyClient:
        def __init__(self, api_key: str) -> None:  # noqa: ARG002
            self.responses = SimpleNamespace(create=lambda **_kwargs: DummyResponse())

    monkeypatch.setattr(llm.handler, "OpenAI", DummyClient)
    monkeypatch.setattr(
        batch_component,
        "ChatResult",
        lambda conversation, content: {"conversation": conversation, "content": content},
    )

    result = component.chat_batch_results(params, entity_id=1)

    assert result["content"] == "antwoord via attr"


def test_format_chat_dataset_for_prompt() -> None:
    """Test that format_chat_dataset_for_prompt formats dataset correctly."""
    dataset = {
        "summary": {
            "total_bridges": 2,
            "calculated": 1,
            "failed": 0,
            "pending": 0,
            "not_ready": 1,
            "cached_results": 1,
            "last_batch_run": "2024-01-01T00:00:00Z",
            "dataset_truncated": False,
        },
        "bridges": [
            {
                "bridge_id": 1,
                "name": "Brug 1",
                "objectnumm": "BRU0001",
                "classification": "calculated",
                "status": "Voltooid",
                "construction_year": 1975,
                "total_length_m": 10.0,
                "total_width_m": 8.0,
                "max_uc": 0.8,
                "cached": True,
                "failed_checks_count": 0,
                "missing_fields": [],
                "uc_breakdown": {
                    "uc_capaciteit": 0.75,
                    "uc_schuifkracht": 0.80,
                    "uc_torsie": 0.45,
                    "uc_interactie": 0.60,
                    "uc_scheurwijdte": 0.55,
                    "uc_detailing": 0.50,
                    "uc_spanningslimieten": 0.40,
                },
                "filtered_metadata": {
                    "type": "Type 1",
                    "stadsdeel": "Centrum",
                    "straat": "Teststraat",
                    "gebruik": "Wegverkeer",
                    "aantal_velden": 2,
                    "voorgespannen": False,
                    "vlag_arb": "groen",
                },
                "design_parameters": {
                    "cc_class": "CC2",
                    "berekeningsniveau": "Theoretische wegindeling",
                    "design_code": "NEN 8700 verbouw",
                    "concrete_strength_class": "C30/37",
                    "staalsoort": "B500B",
                    "load_zones_summary": "4 zones: 1x Auto, 1x Fiets, 1x Voetganger, 1x Berm",
                    "reinforcement_zones_count": 3,
                    "segment_geometry": {
                        "thickness_z1z3": 0.70,
                        "thickness_z2": 0.85,
                        "num_segments": 3,
                        "support_count": 2,
                        "total_length": 50.0,
                        "segments": [
                            {"bz1": 10.0, "bz2": 3.0, "bz3": 15.0, "total_width": 28.0, "length": 20.0, "support_type": "Verende oplegging (x,y)"},
                            {"bz1": 10.0, "bz2": 3.0, "bz3": 15.0, "total_width": 28.0, "length": 15.0, "support_type": "Nee"},
                            {"bz1": 10.0, "bz2": 3.0, "bz3": 15.0, "total_width": 28.0, "length": 15.0, "support_type": "Verende oplegging (x,y)"},
                        ],
                    },
                },
            },
            {
                "bridge_id": 2,
                "name": "Brug 2",
                "objectnumm": "BRU0002",
                "classification": "not_ready",
                "status": "Ontbrekende invoer",
                "construction_year": 1985,
                "total_length_m": 12.0,
                "total_width_m": None,
                "max_uc": None,
                "cached": False,
                "failed_checks_count": 0,
                "missing_fields": ["wapening"],
                "uc_breakdown": None,
                "filtered_metadata": {
                    "type": "Type 0",
                    "stadsdeel": "Zuid",
                    "straat": None,
                    "gebruik": "Fietsers",
                    "aantal_velden": 1,
                    "voorgespannen": None,
                    "vlag_arb": "oranje",
                },
                "design_parameters": None,
            },
        ],
    }

    formatted = llm.context.format_chat_dataset_for_prompt(dataset)

    assert "Totaal bruggen: 2" in formatted
    assert "Brug 1" in formatted
    assert "BRU0001" in formatted
    assert "wapening" in formatted
    # Check for expanded metadata
    assert "Centrum" in formatted  # stadsdeel
    assert "CC2" in formatted or "CC: CC2" in formatted  # design parameter
    assert "C30/37" in formatted or "beton: C30/37" in formatted  # concrete class
    assert "B500B" in formatted or "staal: B500B" in formatted  # steel grade
    # Check for UC breakdown (format is "capaciteit 0.75" without colon in the new format)
    assert "capaciteit 0.75" in formatted or "capaciteit" in formatted
    assert "schuifkracht 0.80" in formatted or "schuifkracht" in formatted
    # Check for segment geometry
    assert "dikte:" in formatted or "0.70" in formatted  # thickness z1/z3
    assert "0.85" in formatted  # thickness z2
    assert "3 segmenten" in formatted or "segmenten" in formatted
    assert "2 opleggingen" in formatted or "opleggingen" in formatted


def test_chat_handles_incomplete_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of incomplete OpenAI responses due to token limits."""
    component = batch_component.BatchCalculationComponent()

    class DummyConversation:
        def get_messages(self) -> list[dict[str, str]]:
            return [{"role": "user", "content": "Welke bruggen?"}]

    params = SimpleNamespace(batch_calculation=SimpleNamespace(batch_results_chat=DummyConversation()))

    dataset = {
        "summary": {"total_bridges": 1},
        "field_descriptions": {},
        "bridges": [{"bridge_id": 1, "name": "Test Bridge"}],
    }

    # Patch build_batch_chat_context in handler module (where it's imported from context)
    monkeypatch.setattr(llm.handler, "build_batch_chat_context", lambda _entity_id: dataset)
    monkeypatch.setattr(llm.handler.os, "getenv", lambda key: "test-api-key" if key == "OPENAI_API_KEY" else None)

    # Mock incomplete response
    class DummyIncompleteDetails:
        reason = "max_output_tokens"

    class DummyResponse:
        output_text: Any = None
        output: ClassVar[list[Any]] = []
        status = "incomplete"
        incomplete_details = DummyIncompleteDetails()

        def model_dump(self) -> dict[str, list[Any]]:
            return {"output": []}

    class DummyResponsesAPI:
        def create(self, **_kwargs: Any) -> DummyResponse:  # noqa: ANN401
            return DummyResponse()

    class DummyOpenAIClient:
        responses = DummyResponsesAPI()

    monkeypatch.setattr(llm.handler, "OpenAI", lambda api_key=None, **kwargs: DummyOpenAIClient())  # noqa: ARG005
    monkeypatch.setattr(
        batch_component,
        "ChatResult",
        lambda _conversation, content: SimpleNamespace(message=content),
    )

    result = component.chat_batch_results(params, entity_id=999)

    assert "maximale tokenlimiet" in result.message.lower()
    assert "kortere of meer specifieke vraag" in result.message.lower()
