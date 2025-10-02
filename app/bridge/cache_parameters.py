"""
Cache parameter definitions for SCIA and IDEA analyses.

This module centralizes which parameters trigger cache invalidation:
- SCIA cache: Invalidates when SHARED_PARAMETERS change
- IDEA cache: Invalidates when SHARED_PARAMETERS OR IDEA_ONLY_PARAMETERS change

To add/remove parameters: just add/remove paths from the lists below.

Path syntax:
  - Simple: "input.berekeningsinstellingen.cc_class"
  - Array: "bridge_segments_array[*].bz1" (extracts field from each array item)
"""

from typing import Any, TypedDict

from src.common.constants.technical import AnalysisType


class ParameterGroup(TypedDict):
    """Parameter group with name and list of paths."""

    name: str
    paths: list[str]


# ============================================================================
# SHARED PARAMETERS (affect both SCIA and IDEA analyses)
# ============================================================================

SHARED_PARAMETERS: list[ParameterGroup] = [
    {
        "name": "bridge_segments",
        "paths": [
            "bridge_segments_array[*].bz1",
            "bridge_segments_array[*].bz2",
            "bridge_segments_array[*].bz3",
            "bridge_segments_array[*].dz",
            "bridge_segments_array[*].dz_2",
            "bridge_segments_array[*].l",
            "bridge_segments_array[*].is_first_segment",
            "bridge_segments_array[*].is_support",
        ],
    },
    {
        "name": "load_zones",
        "paths": [
            "load_zones_data_array[*].zone_type",
            "load_zones_data_array[*].pavement_thickness",
            "load_zones_data_array[*].pavement_material",
            *[f"load_zones_data_array[*].d{i}_width" for i in range(1, 16)],
        ],
    },
    {
        "name": "load_combinations",
        "paths": [
            "input.berekeningsinstellingen.cc_class",
            "input.berekeningsinstellingen.design_code",
            "info.construction_year",
        ],
    },
    {
        "name": "materials",
        "paths": [
            "concrete_strength_class",
        ],
    },
]

# ============================================================================
# IDEA-ONLY PARAMETERS (only affect IDEA analysis)
# ============================================================================

IDEA_ONLY_PARAMETERS: list[ParameterGroup] = [
    {
        "name": "reinforcement_zones",
        "paths": [
            "reinforcement_zones_array[*].zone_number",
            "reinforcement_zones_array[*].hoofdwapening_langs_boven_diameter",
            "reinforcement_zones_array[*].hoofdwapening_langs_boven_hart_op_hart",
            "reinforcement_zones_array[*].hoofdwapening_langs_onder_diameter",
            "reinforcement_zones_array[*].hoofdwapening_langs_onder_hart_op_hart",
            "reinforcement_zones_array[*].hoofdwapening_dwars_boven_diameter",
            "reinforcement_zones_array[*].hoofdwapening_dwars_boven_hart_op_hart",
            "reinforcement_zones_array[*].hoofdwapening_dwars_onder_diameter",
            "reinforcement_zones_array[*].hoofdwapening_dwars_onder_hart_op_hart",
            "reinforcement_zones_array[*].heeft_bijlegwapening",
            "reinforcement_zones_array[*].bijlegwapening_langs_boven_diameter",
            "reinforcement_zones_array[*].bijlegwapening_langs_onder_diameter",
            "reinforcement_zones_array[*].bijlegwapening_dwars_boven_diameter",
            "reinforcement_zones_array[*].bijlegwapening_dwars_onder_diameter",
        ],
    },
    {
        "name": "reinforcement_geometry",
        "paths": [
            "input.geometrie_wapening.staalsoort",
            "input.geometrie_wapening.dekking_boven",
            "input.geometrie_wapening.dekking_onder",
            "input.geometrie_wapening.langswapening_buiten",
        ],
    },
]


# ============================================================================
# Parameter Extraction Functions
# ============================================================================


def _get_nested_value(obj: Any, path: str) -> Any:  # noqa: ANN401
    """Get nested value using dot notation (e.g., "input.settings.value")."""
    for attr in path.split("."):
        obj = getattr(obj, attr, None)
        if obj is None:
            break
    return obj


def _extract_single_param(params: Any, path: str) -> Any:  # noqa: ANN401
    """Extract a single parameter value from params using path notation."""
    # Handle array notation like "bridge_segments_array[*].bz1"
    if "[*]" in path:
        array_path, field_name = path.split("[*].")
        array_obj = _get_nested_value(params, array_path)
        if array_obj and hasattr(array_obj, "__iter__"):
            return [getattr(item, field_name, None) for item in array_obj]
        return []
    # Handle simple dot notation like "input.berekeningsinstellingen.cc_class"
    return _get_nested_value(params, path)


def get_cache_parameters_for_analysis(analysis_type: AnalysisType) -> list[ParameterGroup]:
    """Get parameter groups for the specified analysis type."""
    if analysis_type == AnalysisType.SCIA:
        return SHARED_PARAMETERS
    if analysis_type == AnalysisType.IDEA:
        return SHARED_PARAMETERS + IDEA_ONLY_PARAMETERS
    raise ValueError(f"Unsupported analysis type: {analysis_type}")


def extract_parameters_for_analysis(
    params: Any,  # noqa: ANN401
    analysis_type: AnalysisType,
) -> dict[str, Any]:
    """Extract all relevant parameters for caching based on analysis type."""
    parameter_groups = get_cache_parameters_for_analysis(analysis_type)
    extracted: dict[str, Any] = {}

    for group in parameter_groups:
        group_data: dict[str, Any] = {}
        for path in group["paths"]:
            # Use the last part of the path as the key
            key = path.split("[*].")[-1] if "[*]" in path else path.split(".")[-1]
            group_data[key] = _extract_single_param(params, path)

        extracted[group["name"]] = group_data

    return extracted
