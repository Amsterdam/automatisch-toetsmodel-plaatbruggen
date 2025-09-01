"""
SCIA results extraction and processing utilities.

This module provides functions for extracting and processing results from SCIA analysis.
These functions are pure Python and can be used by the app layer to retrieve analysis results.
"""

from typing import Any

from .scia_model_interface import SciaAnalysis, SciaModelBuilder


def extract_analysis_results(builder: SciaModelBuilder, analysis: SciaAnalysis) -> dict[str, Any]:
    """
    Extract results from a completed SCIA analysis using the builder interface.

    :param builder: The SCIA model builder instance
    :param analysis: The completed SCIA analysis object
    :returns: Dictionary containing extracted analysis results
    :rtype: dict[str, Any]
    """
    try:
        # Extract results using the builder interface
        results = builder.extract_analysis_results(analysis)

        # Validate results
        is_valid, validation_messages = validate_analysis_results(results)
        results["validation"] = {
            "is_valid": is_valid,
            "messages": validation_messages,
        }

        # Add summary
        results["result_summary"] = get_result_summary(results)

        # Attach units mapping for downstream consumers
        units_mapping = build_units_mapping(results)
        results["units"] = units_mapping

        # Also place units inside individual sections when present (convenience)
        if isinstance(results.get("internal_forces"), dict):
            results["internal_forces"].setdefault("units", units_mapping.get("internal_forces", {}))

    except Exception as e:
        raise ValueError(f"Failed to extract SCIA analysis results: {e!s}")
    else:
        return results


def get_result_summary(results: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a summary of the analysis results.

    :param results: The complete results dictionary from extract_analysis_results
    :returns: Summary of key results and statistics
    :rtype: dict[str, Any]
    """

    # Helper function to safely get status from result sections
    def _get_status(section_data: object) -> str:
        if isinstance(section_data, dict):
            return section_data.get("status", "unknown")
        return "unknown"

    summary = {
        "analysis_successful": results.get("analysis_status", {}).get("executed", False),
        "has_displacements": _get_status(results.get("displacements")) != "not_implemented",
        "has_internal_forces": _get_status(results.get("internal_forces")) != "not_implemented",
        "has_reactions": _get_status(results.get("reactions")) != "not_implemented",
        "has_stresses": _get_status(results.get("stresses")) != "not_implemented",
    }

    # Add error information if available
    error_msg = results.get("analysis_status", {}).get("error_message")
    if error_msg:
        summary["error_message"] = error_msg

    return summary


def validate_analysis_results(results: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that the analysis results are complete and usable.

    :param results: The complete results dictionary from extract_analysis_results
    :returns: Tuple of (is_valid, list_of_validation_messages)
    :rtype: tuple[bool, list[str]]
    """
    validation_messages = []

    # Check if analysis was executed
    if not results.get("analysis_status", {}).get("executed", False):
        validation_messages.append("Analysis was not executed successfully")

    # Check for error messages
    error_msg = results.get("analysis_status", {}).get("error_message")
    if error_msg:
        validation_messages.append(f"Analysis error: {error_msg}")

    # TODO: Add more validation checks as result extraction is implemented

    is_valid = len(validation_messages) == 0
    return is_valid, validation_messages


def build_units_mapping(results: dict[str, Any]) -> dict[str, dict[str, str]]:
    """
    Build a best-effort units mapping for SCIA results.

    The mapping is returned under a top-level structure keyed by result category
    (e.g. "internal_forces", "reactions", "stresses"). For internal forces,
    units depend on whether the selected table represents 1D (beam) or 2D (plate)
    forces. This is inferred from the table name when available.

    :param results: The complete results dictionary from extract_analysis_results
    :returns: Mapping from category -> { result_component: unit_string }
    :rtype: dict[str, dict[str, str]]
    """
    # Determine internal force units based on table type (1D vs 2D)
    internal_forces_entry = results.get("internal_forces")
    table_name = None
    if isinstance(internal_forces_entry, dict):
        table_name = internal_forces_entry.get("table_name")

    # Units for the actual force components extracted from SCIA XML headers
    # Note: Values are converted from N to kN and from Nmm to kNm during extraction
    internal_forces_units_2d = {
        # Bending moments per unit length (2D plates) - converted from Nmm to kNm
        "m_x": "kNm/m",
        "m_y": "kNm/m",
        "m_xy": "kNm/m",
        # Shear forces per unit length (2D plates) - converted from N to kN
        "v_x": "kN/m",
        "v_y": "kN/m",
        # Membrane forces per unit length (2D plates) - converted from N to kN
        "n_x": "kN/m",
        "n_y": "kN/m",
        "n_xy": "kN/m",
        # Envelope components for 2D plates - converted from Nmm to kNm
        "m_xD+": "kNm/m",
        "m_xD-": "kNm/m",
        "m_yD+": "kNm/m",
        "m_yD-": "kNm/m",
        "m_cD+": "kNm/m",
        "m_cD-": "kNm/m",
        # Envelope components for 2D plates - converted from N to kN
        "n_xD": "kN/m",
        "n_yD": "kN/m",
        "n_cD": "kN/m",
    }

    # For 1D elements (if any), use standard beam force units
    # Note: Values are converted from N to kN and from Nmm to kNm during extraction
    internal_forces_units_1d = {
        # Standard 1D beam forces (fallback if 1D tables are encountered) - converted from N to kN
        "N": "kN",
        "Vy": "kN",
        "Vz": "kN",
        # Standard 1D beam moments - converted from Nmm to kNm
        "Mx": "kNm",
        "My": "kNm",
        "Mz": "kNm",
    }

    # Heuristic: consider any table name containing "2D" as plate forces; "1D" as beam forces
    # If none is present, fall back to the 1D convention commonly used for line/beam results.
    internal_forces_units: dict[str, str]
    if isinstance(table_name, str) and ("2D" in table_name or "2d" in table_name.lower()):
        # 2D plates: include both raw SCIA field keys and envelope component keys used downstream
        internal_forces_units = {
            **internal_forces_units_2d,
            # Envelope component names used by force envelopes / views
            "N": "kN/m",
            "Vy": "kN/m",
            "Vz": "kN/m",
            "Mxd+": "kNm/m",
            "Mxd-": "kNm/m",
            "Myd+": "kNm/m",
            "Myd-": "kNm/m",
        }
    elif isinstance(table_name, str) and ("1D" in table_name or "1d" in table_name.lower()):
        # 1D beams: include envelope-style moment keys as well
        internal_forces_units = {
            **internal_forces_units_1d,
            "Mxd+": "kNm",
            "Mxd-": "kNm",
            "Myd+": "kNm",
            "Myd-": "kNm",
        }
    else:
        internal_forces_units = {
            **internal_forces_units_1d,
            "Mxd+": "kNm",
            "Mxd-": "kNm",
            "Myd+": "kNm",
            "Myd-": "kNm",
        }

    # Compose final mapping
    units: dict[str, dict[str, str]] = {
        "internal_forces": internal_forces_units,
    }

    return units


def _extract_combinations_by_type(load_combinations: dict[str, Any], combo_type: str) -> list[Any]:
    """
    Extract load combinations by type from the load combinations dictionary.

    :param load_combinations: Dictionary of created load combinations
    :param combo_type: Type to filter by (ULS, SLS, etc.)
    :returns: List of combinations of the specified type
    """
    if not load_combinations:
        return []

    items_iter = []
    if isinstance(load_combinations, dict):
        items_iter = list(load_combinations.items())
    elif hasattr(load_combinations, "items"):
        try:
            items_iter = list(load_combinations.items())
        except Exception:
            items_iter = []

    combinations = []
    for combo_name, combo in items_iter:
        if combo_type in combo_name:
            combinations.append(combo)

    return combinations


def _extract_sls_combinations(load_combinations: dict[str, Any]) -> list[Any]:
    """
    Extract SLS (Serviceability Limit State) combinations.

    :param load_combinations: Dictionary of created load combinations
    :returns: List of SLS combinations
    """
    if not load_combinations:
        return []

    items_iter = []
    if isinstance(load_combinations, dict):
        items_iter = list(load_combinations.items())
    elif hasattr(load_combinations, "items"):
        try:
            items_iter = list(load_combinations.items())
        except Exception:
            items_iter = []

    combinations = []
    for combo_name, combo in items_iter:
        if "SLS" in combo_name or "BGT" in combo_name or "serviceability" in combo_name.lower():
            combinations.append(combo)

    return combinations


def _extract_all_combinations(load_combinations: dict[str, Any]) -> list[Any]:
    """
    Extract all load combinations.

    :param load_combinations: Dictionary of created load combinations
    :returns: List of all combinations
    """
    if not load_combinations:
        return []

    try:
        all_combinations = list(load_combinations.values())
    except Exception:
        all_combinations = []

    return all_combinations


def create_result_classes_for_bridge(builder: SciaModelBuilder, load_combinations: dict[str, Any]) -> None:
    """
    Create result classes for bridge analysis.

    This function creates the necessary result classes that tell SCIA which
    load combinations to analyze and what results to output.

    :param builder: The SCIA model builder instance
    :param load_combinations: Dictionary of created load combinations
    """
    if not load_combinations:
        return

    # Create ULS result class
    uls_combinations = _extract_combinations_by_type(load_combinations, "ULS")
    uls_combinations.extend(_extract_combinations_by_type(load_combinations, "UGT"))

    if uls_combinations:
        builder.create_result_class(name="Ultimate Limit State (ULS)", combinations=uls_combinations)

    # Create SLS (Serviceability Limit State) result class
    sls_combinations = _extract_sls_combinations(load_combinations)

    if sls_combinations:
        builder.create_result_class(name="Serviceability Limit State (SLS)", combinations=sls_combinations)

    # Create a general result class with all combinations if no specific ones found
    if not uls_combinations and not sls_combinations and load_combinations:
        all_combinations = _extract_all_combinations(load_combinations)
        if all_combinations:
            builder.create_result_class(name="All Load Combinations", combinations=all_combinations)
