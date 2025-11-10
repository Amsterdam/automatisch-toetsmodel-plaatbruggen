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


def check_idea_cache_status(bridge_params: Any, bridge_entity_id: int, batch_results_cache_hash: str | None = None) -> bool:  # noqa: ANN401
    """
    Check if valid IDEA analysis results are cached for a bridge.

    This checks if cached results exist for the CURRENT parameter state.
    If parameters changed, hash mismatch will return False (cache invalid).

    Strategy:
    1. First try to find cache with current params hash
    2. If batch_results_cache_hash is provided, compare with current hash to determine cache validity
    3. Fall back to checking if ANY cache keys exist for this bridge

    :param bridge_params: Bridge parametrization object
    :type bridge_params: Any
    :param bridge_entity_id: Bridge entity ID
    :type bridge_entity_id: int
    :param batch_results_cache_hash: Optional cache hash from batch results (if available)
    :type batch_results_cache_hash: str | None
    :returns: True if valid cached IDEA results exist, False otherwise
    :rtype: bool
    """
    from app.bridge.analysis_cache import AnalysisCache
    from src.common.constants.technical import AnalysisType

    try:
        cache = AnalysisCache()
        
        # Generate hash for current parameters
        current_hash = cache._generate_input_hash(bridge_params, AnalysisType.IDEA, None)
        
        # If we have a batch results cache hash, compare it
        if batch_results_cache_hash is not None:
            # If hashes match, cache should be valid (assuming it was stored during batch calc)
            if current_hash == batch_results_cache_hash:
                # Try to retrieve the cache to confirm it exists
                cached_results = cache.get_cached_analysis(bridge_params, AnalysisType.IDEA, bridge_entity_id)
                if cached_results is not None:
                    return True
                # Hash matches but cache not found - might be in different storage scope
                # Fall through to check storage keys
        
        # Step 1: Try to get cached results with current params
        cached_results = cache.get_cached_analysis(bridge_params, AnalysisType.IDEA, bridge_entity_id)
        if cached_results is not None:
            return True
        
        # Step 2: Check if ANY cache exists for this bridge entity in current storage
        try:
            all_keys = cache.storage.list(scope="entity")
            # Look for any cache keys for this bridge entity (any hash)
            bridge_cache_keys = [key for key in all_keys if key.startswith(f"analysis_cache_{bridge_entity_id}_{AnalysisType.IDEA.value}_")]
            
            if bridge_cache_keys:
                # Cache exists but current hash doesn't match - check if it matches batch hash
                if batch_results_cache_hash:
                    # Check if any of the cache keys match the batch hash
                    expected_key_prefix = f"analysis_cache_{bridge_entity_id}_{AnalysisType.IDEA.value}_{batch_results_cache_hash}"
                    if any(key == expected_key_prefix for key in bridge_cache_keys):
                        # Batch hash matches an existing cache key - cache is valid
                        return True
                # Cache exists but hash doesn't match current params - parameters changed
                return False
            
            # No cache keys found in current storage
            # If we have a batch hash but no cache keys, cache might be in bridge entity storage
            # or was cleared. For now, return False (no valid cache found).
            return False
            
        except Exception:
            # If we can't list keys, assume no cache
            return False
            
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
    Serialize batch results dictionary to a VIKTOR File object.

    Uses pickle and base64 encoding to store the results in VIKTOR Storage.

    :param batch_results: Dictionary mapping bridge IDs to their calculation results
    :type batch_results: dict[int, dict[str, Any]]
    :returns: File object containing serialized batch results
    :rtype: File
    """
    # Pickle the results and encode as base64 to avoid binary data issues
    pickled_data = pickle.dumps(batch_results)
    encoded_data = base64.b64encode(pickled_data).decode("utf-8")
    return File.from_data(encoded_data)


def deserialize_batch_results(stored_file: File) -> dict[int, dict[str, Any]]:
    """
    Deserialize batch results from a VIKTOR File object.

    Reads base64-encoded pickled data and returns the batch results dictionary.

    :param stored_file: File object from VIKTOR Storage containing serialized batch results
    :type stored_file: File
    :returns: Dictionary mapping bridge IDs to their calculation results
    :rtype: dict[int, dict[str, Any]]
    """
    # Extract content from file object
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
    pickled_data = base64.b64decode(encoded_data)
    return pickle.loads(pickled_data)

