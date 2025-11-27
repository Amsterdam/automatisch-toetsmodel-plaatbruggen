"""Context building functions for batch calculation LLM chat."""

import json
from typing import Any

import viktor.api_v1 as api
from viktor.core import Storage

from app.constants import BRIDGE_DATA_PATH
from app.overview_bridges.batch_calculation.utils import (
    check_idea_cache_status,
    deserialize_batch_results,
    generate_bridge_report_url,
    load_batch_last_run_timestamp,
    validate_bridge_for_calculation,
)

MAX_BRIDGES_IN_CHAT_CONTEXT = 60

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


def _safe_float(value: Any) -> float | None:  # noqa: ANN401
    """
    Safely convert value to float.

    :param value: Value to convert
    :type value: Any
    :returns: Float value or None
    :rtype: float | None
    """
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError, AttributeError):
        return None


def _safe_int(value: Any) -> int | None:  # noqa: ANN401
    """
    Safely convert value to int.

    :param value: Value to convert
    :type value: Any
    :returns: Int value or None
    :rtype: int | None
    """
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None


def _extract_objectnumm(params: Any) -> str | None:  # noqa: ANN401
    """
    Extract object number from bridge parameters.

    :param params: Bridge parameters object
    :type params: Any
    :returns: Object number string or None
    :rtype: str | None
    """
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


def _extract_construction_year(params: Any, filtered_entry: dict[str, Any] | None) -> int | None:  # noqa: ANN401
    """
    Extract construction year from bridge parameters or filtered entry.

    :param params: Bridge parameters object
    :type params: Any
    :param filtered_entry: Filtered bridge metadata entry
    :type filtered_entry: dict[str, Any] | None
    :returns: Construction year or None
    :rtype: int | None
    """
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


def _extract_total_length(params: Any, filtered_entry: dict[str, Any] | None) -> float | None:  # noqa: ANN401
    """
    Extract total length from bridge parameters or filtered entry.

    :param params: Bridge parameters object
    :type params: Any
    :param filtered_entry: Filtered bridge metadata entry
    :type filtered_entry: dict[str, Any] | None
    :returns: Total length in meters or None
    :rtype: float | None
    """
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


def _extract_total_width(params: Any, filtered_entry: dict[str, Any] | None) -> float | None:  # noqa: ANN401
    """
    Extract total width from bridge parameters or filtered entry.

    :param params: Bridge parameters object
    :type params: Any
    :param filtered_entry: Filtered bridge metadata entry
    :type filtered_entry: dict[str, Any] | None
    :returns: Total width in meters or None
    :rtype: float | None
    """
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

    if summary.get("dataset_truncated"):
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
