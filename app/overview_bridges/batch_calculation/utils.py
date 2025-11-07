"""Utility functions for batch calculation."""

import base64
import pickle
from typing import Any

from viktor.core import File
from viktor.errors import UserError


def validate_bridge_for_calculation(bridge_params: Any, bridge_entity: Any) -> tuple[bool, list[str], float]:  # noqa: ANN401
    """
    Check if bridge is ready for calculation and calculate completion percentage.

    :param bridge_params: Bridge parametrization object
    :type bridge_params: Any
    :param bridge_entity: Bridge entity object
    :type bridge_entity: Any
    :returns: Tuple of (is_ready, missing_fields, completion_percentage)
    :rtype: tuple[bool, list[str], float]
    """
    # Deferred import to avoid circular import issues
    from app.bridge.utils import validate_reinforcement_zone_selections

    missing_fields = []
    total_checks = 5  # Total number of validation checks
    passed_checks = 0

    # Check 1: bridge_segments_array
    if hasattr(bridge_params, "bridge_segments_array") and len(bridge_params.bridge_segments_array) >= 2:
        passed_checks += 1
    else:
        missing_fields.append("Minimaal 2 brugsegmenten")

    # Check 2: reinforcement zones
    try:
        validate_reinforcement_zone_selections(bridge_params)
        passed_checks += 1
    except (UserError, Exception):
        missing_fields.append("Wapeningszones configuratie")

    # Check 3: info section exists (for completeness, but not strictly required for calculation)
    if hasattr(bridge_params, "info") and bridge_params.info:
        passed_checks += 1

    # Check 4: concrete_strength_class
    # NOTE: This field has name="concrete_strength_class" in parametrization (line 673),
    # so it's stored at the TOP LEVEL of bridge_params, NOT in bridge_params.info!
    concrete_class = getattr(bridge_params, "concrete_strength_class", None)
    if concrete_class and isinstance(concrete_class, str) and concrete_class.strip():
        passed_checks += 1
    else:
        missing_fields.append("Betonsterkteklasse")

    # Check 5: steel_quality (staalsoort) - located in input.geometrie_wapening, not info
    # Default is "B500B", so this should usually be present
    try:
        geometrie_wapening = getattr(getattr(bridge_params, "input", None), "geometrie_wapening", None)
        steel_quality = getattr(geometrie_wapening, "staalsoort", None) if geometrie_wapening else None
        if steel_quality and isinstance(steel_quality, str) and steel_quality.strip():
            passed_checks += 1
        else:
            missing_fields.append("Staalkwaliteit wapening")
    except (AttributeError, Exception):
        missing_fields.append("Staalkwaliteit wapening")

    # Calculate completion percentage
    completion_percentage = (passed_checks / total_checks) * 100.0
    is_ready = len(missing_fields) == 0

    return (is_ready, missing_fields, completion_percentage)


def calculate_estimated_batch_time(num_ready_bridges: int) -> str:
    """
    Return formatted time estimate string.

    :param num_ready_bridges: Number of bridges ready for calculation
    :type num_ready_bridges: int
    :returns: Formatted time estimate string
    :rtype: str
    """
    if num_ready_bridges == 0:
        return "Geen geschikte bruggen"

    min_minutes = num_ready_bridges * 15
    max_minutes = num_ready_bridges * 30

    min_hours = min_minutes // 60
    max_hours = max_minutes // 60

    if max_hours == 0:
        return f"{min_minutes}-{max_minutes} minuten"

    return f"{min_hours}-{max_hours} uur ({min_minutes}-{max_minutes} minuten)"


def extract_uc_summary_from_idea_results(idea_results: dict[str, Any]) -> dict[str, Any]:
    """
    Extract UC summary from IDEA analysis results.

    :param idea_results: IDEA analysis results dictionary
    :type idea_results: dict[str, Any]
    :returns: Summary dictionary with max_uc, status, failed_checks
    :rtype: dict[str, Any]
    """
    from src.integrations.idea_integration.idea_results_processor import IdeaResultsProcessor

    processed = IdeaResultsProcessor.process_idea_results(idea_results)

    if not processed.get("success"):
        return {
            "max_uc": None,
            "status": "FAILED",
            "failed_checks": [],
            "error": processed.get("error", "Unknown error"),
        }

    # Extract UC values from table data
    max_uc = 0.0
    failed_checks = []

    for row in processed.get("data", []):
        # Row format varies, extract UC values where available
        if len(row) > 1 and isinstance(row[1], (int, float)):
            uc_value = float(row[1])
            if uc_value > max_uc:
                max_uc = uc_value
            if uc_value >= 1.0:
                failed_checks.append(row[0] if row else "Unknown")

    return {"max_uc": max_uc, "status": "PASSED" if max_uc < 1.0 else "FAILED", "failed_checks": failed_checks}


def check_idea_cache_status(bridge_params: Any, bridge_entity_id: int) -> bool:  # noqa: ANN401
    """
    Check if valid IDEA analysis results are cached for a bridge.

    This checks if cached results exist for the CURRENT parameter state.
    If parameters changed, hash mismatch will return False (cache invalid).

    :param bridge_params: Bridge parametrization object
    :type bridge_params: Any
    :param bridge_entity_id: Bridge entity ID
    :type bridge_entity_id: int
    :returns: True if valid cached IDEA results exist, False otherwise
    :rtype: bool
    """
    from app.bridge.analysis_cache import AnalysisCache
    from src.common.constants.technical import AnalysisType

    try:
        cache = AnalysisCache()
        cached_results = cache.get_cached_analysis(bridge_params, AnalysisType.IDEA, bridge_entity_id)
        return cached_results is not None
    except Exception:
        # If cache check fails (e.g., storage issues), assume no cache
        return False


def generate_bridge_report_url(entity_id: int) -> str:
    """
    Generate URL to bridge rapport page.

    :param entity_id: Entity ID of the bridge
    :type entity_id: int
    :returns: URL string to bridge rapport page
    :rtype: str
    """
    return f"/app/entity/{entity_id}/rapport"


def serialize_batch_results(batch_results: dict[int, dict[str, Any]]) -> File:
    """
    Serialize batch calculation results dict to a File object for Storage.

    :param batch_results: Dictionary of batch calculation results
    :type batch_results: dict[int, dict[str, Any]]
    :returns: File object containing serialized results
    :rtype: File
    """
    # Pickle the results and encode as base64 to avoid binary data issues
    cached_data = pickle.dumps(batch_results)
    encoded_data = base64.b64encode(cached_data).decode("utf-8")
    return File.from_data(encoded_data)


def deserialize_batch_results(stored_file: File) -> dict[int, dict[str, Any]]:
    """
    Deserialize batch calculation results from a File object from Storage.

    :param stored_file: File object from Storage containing serialized results
    :type stored_file: File
    :returns: Dictionary of batch calculation results
    :rtype: dict[int, dict[str, Any]]
    """
    # Read the base64-encoded data
    if hasattr(stored_file, "getvalue"):
        encoded_data = stored_file.getvalue()
    elif hasattr(stored_file, "read"):
        stored_file.seek(0)
        encoded_data = stored_file.read()
    else:
        encoded_data = stored_file

    # Ensure we have string data for base64 decoding
    if isinstance(encoded_data, bytes):
        encoded_data = encoded_data.decode("utf-8")

    # Decode from base64 and unpickle
    cached_data = base64.b64decode(encoded_data)
    return pickle.loads(cached_data)

