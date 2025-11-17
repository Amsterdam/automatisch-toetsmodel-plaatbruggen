"""Utility functions for batch calculation."""

import base64
import logging
import pickle
from typing import Any

from viktor.core import File
from viktor.errors import UserError

logger = logging.getLogger(__name__)


def validate_bridge_for_calculation(bridge_params: Any, bridge_entity: Any) -> tuple[bool, list[str], float]:  # noqa: ANN401, ARG001
    """
    Check if bridge is ready for calculation and calculate completion percentage.

    Validates all crucial parameters based on cache_parameters.py:
    - Bridge segments with required fields (dz, is_support, etc.)
    - Load zones array
    - Load combination parameters
    - Materials (concrete strength class)
    - Reinforcement zones and geometry

    :param bridge_params: Bridge parametrization object
    :type bridge_params: Any
    :param bridge_entity: Bridge entity object (unused, kept for API compatibility)
    :type bridge_entity: Any
    :returns: Tuple of (is_ready, missing_fields, completion_percentage)
    :rtype: tuple[bool, list[str], float]
    """
    # Deferred import to avoid circular import issues
    from app.bridge.utils import validate_reinforcement_zone_selections

    missing_fields = []
    passed_checks = 0
    total_checks = 0

    # ========================================================================
    # CHECK 1: Bridge Segments (SHARED_PARAMETERS)
    # ========================================================================
    total_checks += 1
    if hasattr(bridge_params, "bridge_segments_array") and bridge_params.bridge_segments_array:
        segments = bridge_params.bridge_segments_array
        if len(segments) >= 2:
            # Check each segment has required fields: dz, dz_2, bz1, bz2, bz3, is_support
            # Note: 'l' (length) is not considered crucial for calculation
            segments_valid = True
            for idx, segment in enumerate(segments):
                segment_issues = []

                # Check dz (thickness) - required
                dz = getattr(segment, "dz", None)
                if dz is None or (isinstance(dz, (int, float)) and dz <= 0):
                    segment_issues.append("dikte (dz)")

                # Check dz_2 (secondary thickness) - required
                dz_2 = getattr(segment, "dz_2", None)
                if dz_2 is None or (isinstance(dz_2, (int, float)) and dz_2 <= 0):
                    segment_issues.append("dikte 2 (dz_2)")

                # Check bz1, bz2, bz3 (bridge zone widths)
                bz1 = getattr(segment, "bz1", None)
                bz2 = getattr(segment, "bz2", None)
                bz3 = getattr(segment, "bz3", None)
                if bz1 is None or (isinstance(bz1, (int, float)) and bz1 <= 0):
                    segment_issues.append("breedte zone 1 (bz1)")
                if bz2 is None or (isinstance(bz2, (int, float)) and bz2 <= 0):
                    segment_issues.append("breedte zone 2 (bz2)")
                if bz3 is None or (isinstance(bz3, (int, float)) and bz3 <= 0):
                    segment_issues.append("breedte zone 3 (bz3)")

                # Check is_support (support) - required
                is_support = getattr(segment, "is_support", None)
                if is_support is None or (isinstance(is_support, str) and is_support.strip() == ""):
                    segment_issues.append("oplegging")
                elif isinstance(is_support, str) and is_support.strip().lower() == "nee" and (idx == 0 or idx == len(segments) - 1):
                    # First and last segments must be supports
                    segment_issues.append("oplegging (eerste/laatste segment moet oplegging hebben)")

                if segment_issues:
                    missing_fields.append(f"Segment D{idx}: {', '.join(segment_issues)}")
                    segments_valid = False

            if segments_valid:
                passed_checks += 1
            # Don't add generic message if we already added specific segment issues
            elif not any("Segment D" in field for field in missing_fields):
                missing_fields.append("Brugsegmenten: vereiste velden ontbreken")
        else:
            missing_fields.append("Minimaal 2 brugsegmenten vereist")
    else:
        missing_fields.append("Geen brugsegmenten gedefinieerd")

    # ========================================================================
    # CHECK 2: Load Zones (SHARED_PARAMETERS)
    # ========================================================================
    total_checks += 1
    if hasattr(bridge_params, "load_zones_data_array") and bridge_params.load_zones_data_array:
        load_zones = bridge_params.load_zones_data_array
        if len(load_zones) > 0:
            # Check each zone has zone_type and at least one dX_width
            load_zones_valid = True
            for idx, zone in enumerate(load_zones):
                zone_type = getattr(zone, "zone_type", None)
                if not zone_type or (isinstance(zone_type, str) and not zone_type.strip()):
                    missing_fields.append(f"Belastingzone {idx + 1}: zone type ontbreekt")
                    load_zones_valid = False

                # Check if zone has at least one dX_width value
                has_width = False
                for d_idx in range(1, 16):
                    d_width = getattr(zone, f"d{d_idx}_width", None)
                    if d_width is not None and isinstance(d_width, (int, float)) and d_width > 0:
                        has_width = True
                        break

                if not has_width:
                    missing_fields.append(f"Belastingzone {idx + 1}: geen breedtewaarden (dX_width) gedefinieerd")
                    load_zones_valid = False

            if load_zones_valid:
                passed_checks += 1
            # Missing fields already added above
        else:
            missing_fields.append("Geen belastingzones gedefinieerd")
    else:
        missing_fields.append("Belastingzones array ontbreekt")

    # ========================================================================
    # CHECK 3: Load Combinations (SHARED_PARAMETERS)
    # ========================================================================
    total_checks += 1
    load_combinations_valid = True

    # Check cc_class (can be at top level or in input.berekeningsinstellingen)
    cc_class = getattr(bridge_params, "cc_class", None)
    if not cc_class:
        berekeningsinstellingen = getattr(getattr(bridge_params, "input", None), "berekeningsinstellingen", None)
        cc_class = getattr(berekeningsinstellingen, "cc_class", None) if berekeningsinstellingen else None
    if not cc_class or (isinstance(cc_class, str) and not cc_class.strip()):
        missing_fields.append("Combinatieklasse (cc_class)")
        load_combinations_valid = False

    # Check design_code (can be at top level or in input.berekeningsinstellingen)
    design_code = getattr(bridge_params, "design_code", None)
    if not design_code:
        berekeningsinstellingen = getattr(getattr(bridge_params, "input", None), "berekeningsinstellingen", None)
        design_code = getattr(berekeningsinstellingen, "design_code", None) if berekeningsinstellingen else None
    if not design_code or (isinstance(design_code, str) and not design_code.strip()):
        missing_fields.append("Ontwerpcode (design_code)")
        load_combinations_valid = False

    # Check berekeningsniveau
    berekeningsniveau = getattr(bridge_params, "berekeningsniveau", None)
    if not berekeningsniveau:
        berekeningsinstellingen = getattr(getattr(bridge_params, "input", None), "berekeningsinstellingen", None)
        berekeningsniveau = getattr(berekeningsinstellingen, "berekeningsniveau", None) if berekeningsinstellingen else None
    if not berekeningsniveau or (isinstance(berekeningsniveau, str) and not berekeningsniveau.strip()):
        missing_fields.append("Berekeningsniveau")
        load_combinations_valid = False

    # Check signage
    signage = getattr(bridge_params, "signage", None)
    if not signage or (isinstance(signage, str) and not signage.strip()):
        missing_fields.append("Bebording (signage)")
        load_combinations_valid = False

    if load_combinations_valid:
        passed_checks += 1

    # ========================================================================
    # CHECK 4: Materials (SHARED_PARAMETERS)
    # ========================================================================
    total_checks += 1
    # NOTE: This field has name="concrete_strength_class" in parametrization,
    # so it's stored at the TOP LEVEL of bridge_params, NOT in bridge_params.info!
    concrete_class = getattr(bridge_params, "concrete_strength_class", None)
    if concrete_class and isinstance(concrete_class, str) and concrete_class.strip():
        passed_checks += 1
    else:
        missing_fields.append("Betonsterkteklasse")

    # ========================================================================
    # CHECK 5: Reinforcement Zones (IDEA_ONLY_PARAMETERS)
    # ========================================================================
    total_checks += 1
    # Check if reinforcement zones array exists and is not empty BEFORE calling validation
    if not hasattr(bridge_params, "reinforcement_zones_array") or not bridge_params.reinforcement_zones_array:
        missing_fields.append("Wapeningszones configuratie (geen zones gedefinieerd)")
    else:
        # Only validate if array exists and has items
        try:
            validate_reinforcement_zone_selections(bridge_params)
            passed_checks += 1
        except (UserError, Exception):
            missing_fields.append("Wapeningszones configuratie (duplicaten of ongeldige selectie)")

    # ========================================================================
    # CHECK 6: Reinforcement Geometry (IDEA_ONLY_PARAMETERS)
    # ========================================================================
    total_checks += 1
    reinforcement_geometry_valid = True

    try:
        geometrie_wapening = getattr(getattr(bridge_params, "input", None), "geometrie_wapening", None)
        if not geometrie_wapening:
            missing_fields.append("Wapeningsgeometrie configuratie")
            reinforcement_geometry_valid = False
        else:
            # Check staalsoort (steel quality)
            steel_quality = getattr(geometrie_wapening, "staalsoort", None)
            if not steel_quality or (isinstance(steel_quality, str) and not steel_quality.strip()):
                missing_fields.append("Staalkwaliteit wapening (staalsoort)")
                reinforcement_geometry_valid = False

            # Check dekking_boven (top cover)
            dekking_boven = getattr(geometrie_wapening, "dekking_boven", None)
            if dekking_boven is None or (isinstance(dekking_boven, (int, float)) and dekking_boven <= 0):
                missing_fields.append("Dekking boven (dekking_boven)")
                reinforcement_geometry_valid = False

            # Check dekking_onder (bottom cover)
            dekking_onder = getattr(geometrie_wapening, "dekking_onder", None)
            if dekking_onder is None or (isinstance(dekking_onder, (int, float)) and dekking_onder <= 0):
                missing_fields.append("Dekking onder (dekking_onder)")
                reinforcement_geometry_valid = False

            # Check langswapening_buiten (longitudinal reinforcement placement)
            langswapening_buiten = getattr(geometrie_wapening, "langswapening_buiten", None)
            if langswapening_buiten is None:
                missing_fields.append("Langswapening buiten configuratie")
                reinforcement_geometry_valid = False
    except (AttributeError, Exception):
        missing_fields.append("Wapeningsgeometrie configuratie (sectie ontbreekt)")
        reinforcement_geometry_valid = False

    if reinforcement_geometry_valid:
        passed_checks += 1

    # Calculate completion percentage
    completion_percentage = (passed_checks / total_checks) * 100.0 if total_checks > 0 else 0.0

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
            max_uc = max(max_uc, uc_value)
            if uc_value >= 1.0:
                failed_checks.append(row[0] if row else "Unknown")

    return {"max_uc": max_uc, "status": "PASSED" if max_uc < 1.0 else "FAILED", "failed_checks": failed_checks}


def check_idea_cache_status(bridge_params: Any, bridge_entity_id: int, batch_results_cache_hash: str | None = None) -> bool:  # noqa: ANN401
    """
    Check if valid IDEA analysis results are cached for a bridge.

    IDEA cache existence implies SCIA cache is valid, since IDEA cannot run without SCIA.
    Therefore, we only need to check IDEA cache.

    :param bridge_params: Bridge parametrization object (used if batch_results_cache_hash not provided)
    :type bridge_params: Any
    :param bridge_entity_id: Bridge entity ID
    :type bridge_entity_id: int
    :param batch_results_cache_hash: Optional cache hash from batch results (if available)
    :type batch_results_cache_hash: str | None
    :returns: True if valid cached IDEA results exist, False otherwise
    :rtype: bool
    """
    from app.bridge.analysis_cache import has_valid_idea_cache

    try:
        # IDEA cache existence is proof that SCIA cache is valid
        # (IDEA cannot be calculated without SCIA)
        return has_valid_idea_cache(bridge_params, bridge_entity_id, batch_results_cache_hash)

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
    :raises TypeError: If stored_file is not a File object
    """
    # DEBUG: Detailed type information at function entry
    from viktor.core import File

    # Validate input type - be very explicit about what we expect
    # Check for boolean first (most common invalid type)
    if isinstance(stored_file, bool):
        error_msg = f"Received boolean instead of File: {stored_file}"
        logger.error(error_msg)
        raise TypeError(error_msg)

    # Then check for File type
    if not isinstance(stored_file, File):
        file_type = type(stored_file)
        error_msg = f"Expected File object, got {file_type.__name__}: {stored_file}"
        logger.error(error_msg)
        raise TypeError(error_msg)

    # Verify method exists before calling it
    if not hasattr(stored_file, "open_binary"):
        file_type = type(stored_file)
        error_msg = f"File object missing 'open_binary' method. Got type: {file_type.__name__}, value: {stored_file}"
        logger.error(error_msg)
        raise TypeError(error_msg)

    # Extract content from file object
    # VIKTOR File objects should be opened with open_binary() for binary data
    try:
        with stored_file.open_binary() as f:
            encoded_data = f.read()
    except AttributeError as e:
        # This should not happen if hasattr check passed, but catch it anyway
        file_type = type(stored_file)
        error_msg = f"open_binary() failed on {file_type.__name__}: {e}"
        logger.error(error_msg)
        # Try fallback methods as last resort
        logger.warning("Attempting fallback methods for file extraction")
        if hasattr(stored_file, "getvalue"):
            encoded_data = stored_file.getvalue()
        elif hasattr(stored_file, "read"):
            stored_file.seek(0)
            encoded_data = stored_file.read()
        else:
            raise TypeError(f"Cannot extract data from File object of type {file_type.__name__}")

    # Ensure we have string data for base64 decoding
    if isinstance(encoded_data, bytes):
        encoded_data = encoded_data.decode("utf-8")

    # Decode from base64 and unpickle
    pickled_data = base64.b64decode(encoded_data)
    return pickle.loads(pickled_data)
