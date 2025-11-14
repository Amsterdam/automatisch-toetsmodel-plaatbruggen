"""Utility functions for batch calculation."""

import base64
import json
import logging
import pickle
from datetime import datetime, timezone
from typing import Any

import viktor.api_v1 as api
from app.constants import BRIDGE_DATA_PATH
from viktor.core import File, Storage
from viktor.errors import UserError

logger = logging.getLogger(__name__)

MAX_BRIDGES_IN_CHAT_CONTEXT = 60
LAST_BATCH_RUN_KEY = "batch_calculation_last_run"
CHAT_FIELD_DESCRIPTIONS = {
    "construction_year": "Stichtingsjaar van de brug (filtered_bridges.json of parametrisatie).",
    "total_length_m": "Totale lengte in meters; voorkeur uit parametrisatie, anders filtered_bridges.json.",
    "total_width_m": "Totale brugbreedte in meters (voor zover bekend).",
    "max_uc": "Hoogste unity check (UC) uit IDEA; UC ≥ 1 betekent afkeur.",
    "uc_status": "IDEA-status: PASSED of FAILED op basis van max UC.",
    "classification": (
        "Verwerkingsstatus: calculated (berekend), failed (berekend maar UC ≥ 1 of fout), "
        "pending (wel compleet, nog niet berekend) of not_ready (ontbrekende invoer)."
    ),
    "cached": "Geeft aan of resultaten rechtstreeks uit de analyse-cache komen.",
    "missing_fields": "Lijst van ontbrekende verplichte invoervelden indien de brug nog niet berekend kan worden.",
}


def validate_bridge_for_calculation(bridge_params: Any, bridge_entity: Any) -> tuple[bool, list[str], float]:  # noqa: ANN401, C901, PLR0912
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
    :param bridge_entity: Bridge entity object
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
    if total_checks > 0:
        completion_percentage = (passed_checks / total_checks) * 100.0
    else:
        completion_percentage = 0.0

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
    uc_breakdown = {}
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


def check_idea_cache_status(bridge_params: Any, bridge_entity_id: int, batch_results_cache_hash: str | None = None) -> bool:  # noqa: ANN401
    """
    Check if valid IDEA analysis results are cached for a bridge.

    This checks if cached results exist for the CURRENT parameter state.
    If parameters changed, hash mismatch will return False (cache invalid).

    Strategy:
    1. Generate hash for current parameters
    2. Try to retrieve cache with current hash
    3. If batch_results_cache_hash is provided, only use it if it matches current hash exactly
    4. Only return True if cache exists with exact current hash match

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
<<<<<<< HEAD

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

=======
        
        # If batch_results_cache_hash is provided, it must match current hash exactly
        # If it doesn't match, parameters have changed and cache is invalid
        if batch_results_cache_hash is not None:
            if current_hash != batch_results_cache_hash:
                # Hash mismatch - parameters changed, cache is invalid
                return False
        
        # Try to get cached results with current params hash
        # This will only return results if cache exists with exact hash match
        cached_results = cache.get_cached_analysis(bridge_params, AnalysisType.IDEA, bridge_entity_id)
        if cached_results is not None:
            return True
        
        # No cache found with current hash - cache is invalid or doesn't exist
        return False
            
>>>>>>> ATP-302-Batch-Berekening-Pagina-wordt-benoemd-maar-kan-ik-niet-vinden
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


def _load_batch_results_from_storage(storage: Storage) -> dict[int, dict[str, Any]]:
    """
    Helper to load stored batch calculation results.

    :param storage: VIKTOR storage instance
    :type storage: Storage
    :returns: Batch results keyed by bridge ID
    :rtype: dict[int, dict[str, Any]]
    """
    try:
        stored_file = storage.get("batch_calculation_results", scope="entity")
    except FileNotFoundError:
        return {}
    if isinstance(stored_file, bool):
        return {}
    try:
        return deserialize_batch_results(stored_file)
    except (TypeError, AttributeError):
        return {}


def _load_filtered_bridge_map() -> dict[str, dict[str, Any]]:
    """
    Load the filtered bridges dataset and return a lookup map.

    :returns: Mapping from OBJECTNUMM (upper-case) to metadata dict
    :rtype: dict[str, dict[str, Any]]
    """
    try:
        with BRIDGE_DATA_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    bridge_map: dict[str, dict[str, Any]] = {}
    for entry in data:
        objectnumm = str(entry.get("OBJECTNUMM", "")).strip()
        if objectnumm:
            bridge_map[objectnumm.upper()] = entry
    return bridge_map


def _safe_float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError, AttributeError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None


def _extract_objectnumm(params: Any) -> str | None:
    info = getattr(params, "info", None)
    candidates = [
        getattr(info, "bridge_objectnumm", None) if info else None,
        getattr(params, "bridge_objectnumm", None),
    ]
    for candidate in candidates:
        if candidate:
            text = str(candidate).strip()
            if text:
                return text
    return None


def _extract_construction_year(params: Any, filtered_entry: dict[str, Any] | None) -> int | None:
    info = getattr(params, "info", None)
    if info:
        year = _safe_int(getattr(info, "construction_year", None))
        if year:
            return year
    if filtered_entry:
        year = _safe_int(filtered_entry.get("stichtingsjaar"))
        if year:
            return year
    return None


def _extract_total_length(params: Any, filtered_entry: dict[str, Any] | None) -> float | None:
    info = getattr(params, "info", None)
    if info:
        length = _safe_float(getattr(info, "total_length", None))
        if length:
            return length
        length = _safe_float(getattr(info, "theoretical_length", None))
        if length:
            return length
    if filtered_entry:
        length = _safe_float(filtered_entry.get("lth"))
        if length:
            return length
    return None


def _extract_total_width(params: Any, filtered_entry: dict[str, Any] | None) -> float | None:
    info = getattr(params, "info", None)
    if info:
        width = _safe_float(getattr(info, "total_width", None))
        if width:
            return width
        width = _safe_float(getattr(info, "deck_width", None))
        if width:
            return width
    if filtered_entry:
        width = _safe_float(filtered_entry.get("bbrugdek"))
        if width:
            return width
    return None


def _summarize_load_zones(params: Any) -> str:  # noqa: ANN401
    """
    Create human-readable summary of load zones.

    :param params: Bridge parameters object
    :type params: Any
    :returns: Human-readable summary (e.g., "4 zones: 2x Auto, 1x Fiets, 1x Voetganger")
    :rtype: str
    """
    load_zones_array = getattr(params, "load_zones_data_array", None)
    if not load_zones_array or not isinstance(load_zones_array, (list, tuple)):
        return "Geen belastingzones"

    # Count zone types
    zone_counts: dict[str, int] = {}
    for zone in load_zones_array:
        zone_type = getattr(zone, "zone_type", None)
        if zone_type:
            zone_counts[zone_type] = zone_counts.get(zone_type, 0) + 1

    if not zone_counts:
        return "Geen belastingzones"

    # Format as "4 zones: 2x Auto, 1x Fiets, 1x Voetganger"
    total = sum(zone_counts.values())
    zone_parts = [f"{count}x {zone_type}" for zone_type, count in sorted(zone_counts.items())]
    return f"{total} zones: {', '.join(zone_parts)}"


def _extract_segment_geometry(params: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    Extract segment geometry parameters from bridge parametrization.

    :param params: Bridge parameters object
    :type params: Any
    :returns: Dictionary with thickness_z1z3, thickness_z2, num_segments, segments (list),
              support_count, total_length
    :rtype: dict[str, Any]
    """
    geometry: dict[str, Any] = {
        "thickness_z1z3": None,
        "thickness_z2": None,
        "num_segments": 0,
        "segments": [],
        "support_count": 0,
        "total_length": 0.0,
    }

    # Access bridge segments array
    segments_array = getattr(params, "bridge_segments_array", None)
    if not segments_array or not isinstance(segments_array, (list, tuple)):
        return geometry

    geometry["num_segments"] = len(segments_array)

    # Extract thickness from first segment (uniform across bridge)
    if len(segments_array) > 0:
        first_segment = segments_array[0]
        dz = getattr(first_segment, "dz", None)
        dz_2 = getattr(first_segment, "dz_2", None)
        geometry["thickness_z1z3"] = _safe_float(dz) if dz is not None else None
        geometry["thickness_z2"] = _safe_float(dz_2) if dz_2 is not None else None

    # Extract segment-level data
    total_length = 0.0
    support_count = 0
    segments_data = []

    for segment in segments_array:
        seg_data = {}
        
        # Zone widths
        bz1 = _safe_float(getattr(segment, "bz1", None))
        bz2 = _safe_float(getattr(segment, "bz2", None))
        bz3 = _safe_float(getattr(segment, "bz3", None))
        seg_data["bz1"] = bz1
        seg_data["bz2"] = bz2
        seg_data["bz3"] = bz3
        
        # Total width for this segment
        if bz1 is not None and bz2 is not None and bz3 is not None:
            seg_data["total_width"] = bz1 + bz2 + bz3
        else:
            seg_data["total_width"] = None
        
        # Segment length
        l_value = _safe_float(getattr(segment, "l", None))
        seg_data["length"] = l_value
        if l_value is not None:
            total_length += l_value
        
        # Support type
        is_support = getattr(segment, "is_support", None)
        seg_data["support_type"] = str(is_support) if is_support else None
        if is_support and is_support != "Nee":
            support_count += 1
        
        segments_data.append(seg_data)

    geometry["segments"] = segments_data
    geometry["support_count"] = support_count
    geometry["total_length"] = total_length

    return geometry


def _extract_design_parameters(params: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    Extract key design parameters from bridge parametrization.

    :param params: Bridge parameters object
    :type params: Any
    :returns: Dictionary with design parameters including cc_class, berekeningsniveau,
              design_code, concrete_strength_class, staalsoort, load_zones_summary,
              reinforcement_zones_count, and segment_geometry
    :rtype: dict[str, Any]
    """
    design_params: dict[str, Any] = {}

    # Extract CC class, berekeningsniveau, design_code
    berekeningsinstellingen = getattr(params, "berekeningsinstellingen", None)
    if not berekeningsinstellingen:
        input_obj = getattr(params, "input", None)
        if input_obj:
            berekeningsinstellingen = getattr(input_obj, "berekeningsinstellingen", None)

    if berekeningsinstellingen:
        design_params["cc_class"] = getattr(berekeningsinstellingen, "cc_class", None)
        design_params["berekeningsniveau"] = getattr(berekeningsinstellingen, "berekeningsniveau", None)
        design_params["design_code"] = getattr(berekeningsinstellingen, "design_code", None)

    # Extract concrete strength class
    design_params["concrete_strength_class"] = getattr(params, "concrete_strength_class", None)

    # Extract reinforcement steel grade
    geometrie_wapening = getattr(params, "geometrie_wapening", None)
    if not geometrie_wapening:
        input_obj = getattr(params, "input", None)
        if input_obj:
            geometrie_wapening = getattr(input_obj, "geometrie_wapening", None)

    if geometrie_wapening:
        design_params["staalsoort"] = getattr(geometrie_wapening, "staalsoort", None)

    # Summarize load zones
    design_params["load_zones_summary"] = _summarize_load_zones(params)

    # Count reinforcement zones
    reinforcement_zones = getattr(params, "reinforcement_zones_array", None)
    if reinforcement_zones and isinstance(reinforcement_zones, (list, tuple)):
        design_params["reinforcement_zones_count"] = len(reinforcement_zones)
    else:
        design_params["reinforcement_zones_count"] = 0

    # Extract segment geometry
    design_params["segment_geometry"] = _extract_segment_geometry(params)

    return design_params


def build_batch_chat_context(entity_id: int) -> dict[str, Any]:
    """
    Prepare structured data for the batch results chat.

    :param entity_id: Overview Bridges entity ID
    :type entity_id: int
    :returns: Dictionary containing summary info and per-bridge records
    :rtype: dict[str, Any]
    """
    viktor_api = api.API()
    parent_entity = viktor_api.get_entity(entity_id)
    bridge_entities = parent_entity.children(entity_type_names=["Bridge"])

    storage = Storage()
    batch_results = _load_batch_results_from_storage(storage)
    last_run_timestamp = load_batch_last_run_timestamp(storage)
    filtered_map = _load_filtered_bridge_map()

    records: list[dict[str, Any]] = []
    summary = {
        "total_bridges": len(bridge_entities),
        "calculated": 0,
        "failed": 0,
        "pending": 0,
        "not_ready": 0,
        "cached_results": 0,
        "last_batch_run": last_run_timestamp,
        "dataset_truncated": False,
    }

    for bridge_entity in bridge_entities:
        params = bridge_entity.last_saved_params
        objectnumm = _extract_objectnumm(params)
        filtered_entry = filtered_map.get(objectnumm.upper()) if objectnumm else None
        is_ready, missing_fields, _ = validate_bridge_for_calculation(params, bridge_entity)

        bridge_id = bridge_entity.id
        result = batch_results.get(bridge_id, {})
        cache_flag = bool(result.get("cached"))
        uc_status = result.get("uc_status")
        max_uc = result.get("max_uc")
        failed_checks = result.get("failed_checks", [])
        error_message = result.get("error")
        status_label = result.get("status", "Onbekend") if result else "Niet berekend"

        classification = "calculated"
        if result:
            summary["calculated"] += 1
            if cache_flag:
                summary["cached_results"] += 1
            if (
                (isinstance(max_uc, (int, float)) and max_uc >= 1)
                or (isinstance(uc_status, str) and uc_status.upper() == "FAILED")
                or ("Gefaald" in str(status_label))
            ):
                classification = "failed"
                summary["failed"] += 1
        elif is_ready:
            classification = "pending"
            summary["pending"] += 1
            cache_flag = cache_flag or check_idea_cache_status(params, bridge_id)
            if cache_flag:
                summary["cached_results"] += 1
            status_label = "Klaar voor berekening"
        else:
            classification = "not_ready"
            summary["not_ready"] += 1
            status_label = "Ontbrekende invoer"

        record = {
            "bridge_id": bridge_id,
            "name": bridge_entity.name,
            "objectnumm": objectnumm,
            "classification": classification,
            "status": status_label,
            "uc_status": uc_status,
            "max_uc": max_uc,
            "failed_checks": failed_checks,
            "failed_checks_count": len(failed_checks),
            "uc_breakdown": result.get("uc_breakdown") if result else None,
            "cached": cache_flag,
            "error": error_message,
            "missing_fields": missing_fields,
            "report_url": generate_bridge_report_url(bridge_id),
            "construction_year": _extract_construction_year(params, filtered_entry),
            "total_length_m": _extract_total_length(params, filtered_entry),
            "total_width_m": _extract_total_width(params, filtered_entry),
            "filtered_metadata": {
                "type": filtered_entry.get("type") if filtered_entry else None,
                "stadsdeel": filtered_entry.get("stadsdeel") if filtered_entry else None,
                "straat": filtered_entry.get("straat") if filtered_entry else None,
                "kw_naam": filtered_entry.get("kw_naam") if filtered_entry else None,
                "gebruik": filtered_entry.get("gebruik") if filtered_entry else None,
                "voorgespannen": filtered_entry.get("voorgespannen") if filtered_entry else None,
                "aantal_velden": filtered_entry.get("aantal_velden") if filtered_entry else None,
                "statisch_systeem": filtered_entry.get("statisch_systeem") if filtered_entry else None,
                "kruisingshoek": filtered_entry.get("kruisingshoek") if filtered_entry else None,
                "lth": filtered_entry.get("lth") if filtered_entry else None,
                "slankheid_dek": filtered_entry.get("slankheid_dek") if filtered_entry else None,
                "bbrugdek": filtered_entry.get("bbrugdek") if filtered_entry else None,
                "vlag_arb": filtered_entry.get("vlag_arb") if filtered_entry else None,
            },
            "design_parameters": _extract_design_parameters(params) if classification in ["calculated", "pending"] else None,
        }
        records.append(record)

    priority_map = {"failed": 0, "pending": 1, "calculated": 2, "not_ready": 3}
    records.sort(key=lambda rec: (priority_map.get(rec["classification"], 99), rec["name"]))

    if len(records) > MAX_BRIDGES_IN_CHAT_CONTEXT:
        summary["dataset_truncated"] = True
        records = records[:MAX_BRIDGES_IN_CHAT_CONTEXT]

    return {
        "summary": summary,
        "field_descriptions": CHAT_FIELD_DESCRIPTIONS,
        "bridges": records,
    }


def _format_uc_value(max_uc: Any) -> str:
    if isinstance(max_uc, (int, float)):
        return f"{max_uc:.2f}"
    return "onbekend"


def format_chat_dataset_for_prompt(dataset: dict[str, Any]) -> str:
    """
    Convert the structured dataset to a concise textual summary for the LLM prompt.

    :param dataset: Structured dataset produced by build_batch_chat_context
    :type dataset: dict[str, Any]
    :returns: Readable textual summary
    :rtype: str
    """
    summary = dataset.get("summary", {})
    lines = [
        "Overzicht batchresultaten:",
        f"- Totaal bruggen: {summary.get('total_bridges', 0)} "
        f"(berekend {summary.get('calculated', 0)}, klaar voor berekening {summary.get('pending', 0)}, "
        f"ontbrekende gegevens {summary.get('not_ready', 0)})",
        f"- Laatste batch uitgevoerd: {summary.get('last_batch_run') or 'onbekend'}",
    ]
    
    if summary.get('dataset_truncated'):
        lines.append(f"- NOTITIE: Dataset bevat meer bruggen, alleen eerste {MAX_BRIDGES_IN_CHAT_CONTEXT} getoond")

    lines.append("\nBruggen:")

    bridges = dataset.get("bridges", [])
    for bridge in bridges:
        name = bridge.get("name") or "Onbekend"
        objectnumm = bridge.get("objectnumm") or "?"
        bridge_id = bridge.get("bridge_id")
        classification = bridge.get("classification", "onbekend")
        build_year = bridge.get("construction_year")
        length = bridge.get("total_length_m")
        width = bridge.get("total_width_m")
        max_uc = bridge.get("max_uc")
        cached = bridge.get("cached")
        failed_checks_count = bridge.get("failed_checks_count") or 0
        missing_fields = bridge.get("missing_fields") or []
        filtered = bridge.get("filtered_metadata", {})
        design_params = bridge.get("design_parameters")
        
        # Build user-friendly bridge line
        parts = [f"• {name} ({objectnumm})"]
        
        # Add basic metadata
        metadata_parts = []
        if build_year:
            metadata_parts.append(f"bouwjaar {build_year}")
        if length:
            metadata_parts.append(f"{length:.1f}m lang")
        if width:
            metadata_parts.append(f"{width:.1f}m breed")
        
        # Add filtered metadata
        if filtered.get("straat"):
            metadata_parts.append(f"straat: {filtered['straat']}")
        if filtered.get("stadsdeel"):
            metadata_parts.append(f"stadsdeel: {filtered['stadsdeel']}")
        if filtered.get("type"):
            metadata_parts.append(f"type: {filtered['type']}")
        if filtered.get("gebruik"):
            metadata_parts.append(f"gebruik: {filtered['gebruik']}")
        if filtered.get("aantal_velden"):
            metadata_parts.append(f"{filtered['aantal_velden']} velden")
        if filtered.get("statisch_systeem"):
            metadata_parts.append(f"systeem: {filtered['statisch_systeem']}")
        if filtered.get("voorgespannen") is True:
            metadata_parts.append("voorgespannen")
        elif filtered.get("voorgespannen") is False:
            metadata_parts.append("niet voorgespannen")
        if filtered.get("vlag_arb"):
            metadata_parts.append(f"ARB: {filtered['vlag_arb']}")
        
        # Add design parameters for calculated/pending bridges
        if design_params:
            if design_params.get("cc_class"):
                metadata_parts.append(f"CC: {design_params['cc_class']}")
            if design_params.get("concrete_strength_class"):
                metadata_parts.append(f"beton: {design_params['concrete_strength_class']}")
            if design_params.get("staalsoort"):
                metadata_parts.append(f"staal: {design_params['staalsoort']}")
            if design_params.get("berekeningsniveau"):
                metadata_parts.append(f"niveau: {design_params['berekeningsniveau']}")
            if design_params.get("load_zones_summary"):
                metadata_parts.append(design_params["load_zones_summary"])
            
            # Add segment geometry if available
            segment_geom = design_params.get("segment_geometry")
            if segment_geom:
                # Thickness values
                dz = segment_geom.get("thickness_z1z3")
                dz2 = segment_geom.get("thickness_z2")
                if dz is not None and dz2 is not None:
                    metadata_parts.append(f"dikte: z1/z3={dz:.2f}m, z2={dz2:.2f}m")
                elif dz is not None:
                    metadata_parts.append(f"dikte z1/z3: {dz:.2f}m")
                
                # Segment count and support count
                num_segs = segment_geom.get("num_segments", 0)
                support_cnt = segment_geom.get("support_count", 0)
                if num_segs > 0:
                    seg_parts = []
                    seg_parts.append(f"{num_segs} segmenten")
                    if support_cnt > 0:
                        seg_parts.append(f"{support_cnt} opleggingen")
                    
                    # Show segment lengths if available
                    segments = segment_geom.get("segments", [])
                    if segments:
                        lengths = [s.get("length") for s in segments if s.get("length") is not None]
                        if lengths and len(lengths) > 0:
                            lengths_str = "-".join([f"{l:.1f}" for l in lengths])
                            seg_parts.append(f"lengtes: {lengths_str}m")
                        
                        # Check if widths vary across segments
                        widths = [s.get("total_width") for s in segments if s.get("total_width") is not None]
                        if widths and len(set(widths)) > 1:
                            seg_parts.append("variabele breedte")
                    
                    metadata_parts.append(", ".join(seg_parts))
        
        if metadata_parts:
            parts.append(f" [{', '.join(metadata_parts)}]")
        
        # Add calculation status and results
        if classification == "calculated":
            uc_str = f"UC {max_uc:.2f}" if isinstance(max_uc, (int, float)) else "UC onbekend"
            results_available = "berekeningsresultaten beschikbaar" if cached else "berekend"
            
            # Add UC breakdown showing top 3 highest values prominently
            uc_breakdown = bridge.get("uc_breakdown")
            if uc_breakdown:
                # Collect all UC values with their names
                uc_values = []
                uc_names = {
                    "uc_capaciteit": "capaciteit",
                    "uc_schuifkracht": "schuifkracht",
                    "uc_torsie": "torsie",
                    "uc_interactie": "interactie",
                    "uc_scheurwijdte": "scheurwijdte",
                    "uc_detailing": "detailing",
                    "uc_spanningslimieten": "spanningslimieten",
                }
                for key, name in uc_names.items():
                    value = uc_breakdown.get(key)
                    if value is not None and value > 0:
                        uc_values.append((name, value))
                
                # Sort by value descending and take top 3
                uc_values.sort(key=lambda x: x[1], reverse=True)
                top_uc = uc_values[:3]
                
                if top_uc:
                    top_str = ", ".join([f"{name} {val:.2f}" for name, val in top_uc])
                    parts.append(f" → {uc_str} (hoogste: {top_str}) ({results_available})")
                else:
                    parts.append(f" → {uc_str} ({results_available})")
            else:
                parts.append(f" → {uc_str} ({results_available})")
            
            if failed_checks_count > 0:
                parts.append(f", {failed_checks_count} checks gefaald")
        elif classification == "pending":
            parts.append(" → klaar voor berekening")
        elif classification == "not_ready":
            if missing_fields:
                missing_preview = ", ".join(missing_fields[:3])
                if len(missing_fields) > 3:
                    missing_preview += f" (+{len(missing_fields) - 3} meer)"
                parts.append(f" → ontbrekende gegevens: {missing_preview}")
            else:
                parts.append(" → ontbrekende gegevens")
        
        lines.append("".join(parts))

    if not bridges:
        lines.append("Geen brugdata beschikbaar.")

    return "\n".join(lines)


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

    print(
        f"DEBUG [deserialize_batch_results:ENTRY]: Received type={type(stored_file)}, isinstance(bool)={isinstance(stored_file, bool)}, isinstance(File)={isinstance(stored_file, File)}, value={stored_file}",
        flush=True,
    )

    # Validate input type - be very explicit about what we expect
    # Check for boolean first (most common invalid type)
    if isinstance(stored_file, bool):
        error_msg = f"Received boolean instead of File: {stored_file}"
        print(f"ERROR: {error_msg}")
        raise TypeError(error_msg)

    # Then check for File type
    if not isinstance(stored_file, File):
        file_type = type(stored_file)
        error_msg = f"Expected File object, got {file_type.__name__}: {stored_file}"
        print(f"ERROR: {error_msg}")
        raise TypeError(error_msg)

    # Verify method exists before calling it
    if not hasattr(stored_file, "open_binary"):
        file_type = type(stored_file)
        error_msg = f"File object missing 'open_binary' method. Got type: {file_type.__name__}, value: {stored_file}"
        print(f"ERROR: {error_msg}")
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
        print(f"ERROR: {error_msg}")
        # Try fallback methods as last resort
        print("WARNING: Attempting fallback methods for file extraction")
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
