"""Utility functions for batch calculation."""

import base64
import pickle
from datetime import datetime, timezone
from typing import Any

from app.constants.technical import LAST_BATCH_RUN_KEY, STORAGE_STATUS_KEY
from viktor.core import File, Storage
from viktor.errors import UserError


def validate_bridge_for_calculation(bridge_params: Any, bridge_entity: Any) -> tuple[bool, list[str], float]:  # noqa: ANN401, ARG001, C901, PLR0912, PLR0915
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


def _find_header_index(headers: list[str], target: str) -> int | None:
    """
    Find index of header in list, return None if not found.

    :param headers: List of header strings
    :type headers: list[str]
    :param target: Target header to find
    :type target: str
    :returns: Index of header or None if not found
    :rtype: int | None
    """
    try:
        return headers.index(target)
    except ValueError:
        return None


def _safe_parse_uc(value: Any) -> float | None:  # noqa: ANN401
    """
    Safely parse UC value from string or number, return None for N/A.

    :param value: Value to parse (can be string, number, or None)
    :type value: Any
    :returns: Parsed float value or None
    :rtype: float | None
    """
    if value is None or value == "N/A":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def extract_uc_summary_from_idea_results(idea_results: dict[str, Any]) -> dict[str, Any]:
    """
    Extract UC summary from IDEA analysis results.

    Now includes detailed breakdown of all 7 UC check types.

    :param idea_results: IDEA analysis results dictionary
    :type idea_results: dict[str, Any]
    :returns: Summary dictionary with max_uc, status, failed_checks, and uc_breakdown
    :rtype: dict[str, Any]
    """
    from src.integrations.idea_integration.idea_results_processor import IdeaResultsProcessor

    processed = IdeaResultsProcessor.process_idea_results(idea_results)

    if not processed.get("success"):
        return {
            "max_uc": None,
            "status": "FAILED",
            "failed_checks": [],
            "uc_breakdown": None,
            "error": processed.get("error", "Unknown error"),
        }

    headers = processed.get("headers", [])
    data = processed.get("data", [])

    # Map header indices for UC columns
    uc_indices = {
        "uc_capaciteit": _find_header_index(headers, "UC Capaciteit"),
        "uc_schuifkracht": _find_header_index(headers, "UC Schuifkracht"),
        "uc_torsie": _find_header_index(headers, "UC Torsie"),
        "uc_interactie": _find_header_index(headers, "UC Interactie"),
        "uc_scheurwijdte": _find_header_index(headers, "UC Scheurwijdte"),
        "uc_detailing": _find_header_index(headers, "UC Detailing"),
        "uc_spanningslimieten": _find_header_index(headers, "UC Spanningslimieten"),
    }

    # Find maximum UC value for each check type
    uc_breakdown: dict[str, float | None] = {}
    max_overall_uc = 0.0
    failed_checks = []

    for check_name, col_idx in uc_indices.items():
        if col_idx is None:
            uc_breakdown[check_name] = None
            continue

        max_uc_for_check = 0.0
        for row in data:
            if col_idx < len(row):
                uc_value = _safe_parse_uc(row[col_idx])
                if uc_value is not None:
                    max_uc_for_check = max(max_uc_for_check, uc_value)
                    max_overall_uc = max(max_overall_uc, uc_value)

                    if uc_value >= 1.0:
                        section_name = row[0] if len(row) > 0 else "Unknown"
                        if section_name not in failed_checks:
                            failed_checks.append(section_name)

        uc_breakdown[check_name] = max_uc_for_check if max_uc_for_check > 0 else None

    return {
        "max_uc": max_overall_uc,
        "status": "PASSED" if max_overall_uc < 1.0 else "FAILED",
        "failed_checks": failed_checks,
        "uc_breakdown": uc_breakdown,
    }


def check_idea_cache_status(bridge_params: Any, bridge_entity_id: int, batch_results_cache_hash: str | None = None) -> bool:  # noqa: ANN401, C901
    """
    Check if valid IDEA analysis results are cached for a bridge.

    IDEA cache existence implies SCIA cache is valid, since IDEA cannot run without SCIA.
    Therefore, we only need to check IDEA cache.

    Reads cache status marker from parent (overview) storage to avoid cross-entity access issues.

    :param bridge_params: Bridge parametrization object (used to generate current hash)
    :type bridge_params: Any
    :param bridge_entity_id: Bridge entity ID
    :type bridge_entity_id: int
    :param batch_results_cache_hash: Optional cache hash from batch results (if available)
    :type batch_results_cache_hash: str | None
    :returns: True if valid cached IDEA results exist, False otherwise
    :rtype: bool
    """
    import json

    from viktor.core import Storage

    from app.bridge.analysis_cache import _get_analysis_cache
    from src.common.constants.technical import AnalysisType

    try:
        # Read marker from parent (overview) storage
        marker_key = f"bridge_{bridge_entity_id}_idea_cache_status"
        storage = Storage()

        try:
            marker_file = storage.get(marker_key, scope="workspace")
        except Exception:
            return False

        # Parse marker data
        marker_json = marker_file.getvalue() if hasattr(marker_file, "getvalue") else marker_file
        if isinstance(marker_json, bytes):
            marker_json = marker_json.decode("utf-8")
        marker_data = json.loads(marker_json)

        cached_hash = marker_data.get("cache_hash")

        # If batch_results_cache_hash provided, use it for comparison
        if batch_results_cache_hash is not None:
            result = cached_hash == batch_results_cache_hash
            # Verify actual cache file exists (not just marker)
            if result:  # Only verify if hash matches
                try:
                    cache = _get_analysis_cache()
                    # Try to read actual cache file from entity storage
                    cache_file = cache.get_cached_analysis(
                        params=bridge_params, analysis_type=AnalysisType.IDEA, entity_id=bridge_entity_id, template_path=None
                    )
                    if cache_file is None:
                        result = False
                except FileNotFoundError:
                    result = False
                except Exception:
                    result = False
            return result

        # Otherwise, generate current hash and compare
        cache = _get_analysis_cache()
        current_hash = cache._generate_input_hash(bridge_params, AnalysisType.IDEA, None)  # noqa: SLF001
        result = cached_hash == current_hash
        # Verify actual cache file exists (not just marker)
        if result:  # Only verify if hash matches
            try:
                # Try to read actual cache file from entity storage
                cache_file = cache.get_cached_analysis(
                    params=bridge_params, analysis_type=AnalysisType.IDEA, entity_id=bridge_entity_id, template_path=None
                )
                if cache_file is None:
                    result = False
            except FileNotFoundError:
                result = False
            except Exception:
                result = False
        return result  # noqa: TRY300

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


def record_batch_last_run_timestamp(storage: Storage, timestamp: datetime | None = None) -> None:
    """
    Store the timestamp of the last successful batch calculation run.

    :param storage: VIKTOR storage instance
    :type storage: Storage
    :param timestamp: Timestamp to store. Defaults to current UTC time if not provided.
    :type timestamp: datetime | None
    """
    ts = timestamp or datetime.now(timezone.utc)
    storage.set(LAST_BATCH_RUN_KEY, File.from_data(ts.isoformat()), scope="entity")


def load_batch_last_run_timestamp(storage: Storage) -> str | None:
    """
    Load the timestamp of the last successful batch calculation run.

    :param storage: VIKTOR storage instance
    :type storage: Storage
    :returns: ISO formatted timestamp or None if not available
    :rtype: str | None
    """
    try:
        ts_file = storage.get(LAST_BATCH_RUN_KEY, scope="entity")
    except FileNotFoundError:
        return None
    if isinstance(ts_file, bool):
        return None
    if isinstance(ts_file, File):
        with ts_file.open() as fh:
            content = fh.read().strip()
            return content or None
    if hasattr(ts_file, "getvalue"):
        value = ts_file.getvalue()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return value.strip() or None
    return None


def record_storage_status(storage: Storage, success: bool, message: str, details: dict[str, Any] | None = None) -> None:
    """
    Record storage operation status for monitoring in production.

    :param storage: VIKTOR storage instance
    :type storage: Storage
    :param success: Whether the storage operation succeeded
    :type success: bool
    :param message: Status message
    :type message: str
    :param details: Optional additional details (e.g., number of results saved, error type)
    :type details: dict[str, Any] | None
    """
    import json

    status_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "message": message,
        "details": details or {},
    }
    try:
        status_json = json.dumps(status_data, indent=2)
        storage.set(STORAGE_STATUS_KEY, File.from_data(status_json), scope="entity")
    except Exception as e:
        print(f"Warning: Failed to record storage status: {e}")


def load_storage_status(storage: Storage) -> dict[str, Any] | None:
    """
    Load the last storage operation status.

    :param storage: VIKTOR storage instance
    :type storage: Storage
    :returns: Status dictionary with timestamp, success, message, and details, or None if not available
    :rtype: dict[str, Any] | None
    """
    try:
        status_file = storage.get(STORAGE_STATUS_KEY, scope="entity")
    except FileNotFoundError:
        return None
    if isinstance(status_file, bool):
        return None
    if isinstance(status_file, File):
        try:
            import json

            with status_file.open() as fh:
                content = fh.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8")
                return json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Failed to load storage status: {e}")
            return None
    return None


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
    # Validate input type - be very explicit about what we expect
    # Check for boolean first (most common invalid type)
    if isinstance(stored_file, bool):
        error_msg = f"Received boolean instead of File: {stored_file}"
        print(f"Error: {error_msg}")
        raise TypeError(error_msg)

    # Then check for File type
    if not isinstance(stored_file, File):
        file_type = type(stored_file)
        error_msg = f"Expected File object, got {file_type.__name__}: {stored_file}"
        print(f"Error: {error_msg}")
        raise TypeError(error_msg)

    # Verify method exists before calling it
    if not hasattr(stored_file, "open_binary"):
        file_type = type(stored_file)
        error_msg = f"File object missing 'open_binary' method. Got type: {file_type.__name__}, value: {stored_file}"
        print(f"Error: {error_msg}")
        raise TypeError(error_msg)

    # Extract content from file object
    # VIKTOR File objects should be opened with open_binary() for binary data
    try:
        with stored_file.open_binary() as f:
            encoded_data = f.read()
    except AttributeError:
        # This should not happen if hasattr check passed, but catch it anyway
        file_type = type(stored_file)
        print(f"Error: open_binary() failed on {file_type.__name__}")
        import traceback
        print(traceback.format_exc())
        # Try fallback methods as last resort
        print("Warning: Attempting fallback methods for file extraction")
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
