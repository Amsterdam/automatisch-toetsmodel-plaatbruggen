"""
SCIA results extraction and processing utilities.

This module provides functions for extracting and processing results from SCIA analysis.
These functions are pure Python and can be used by the app layer to retrieve analysis results.
"""

from typing import Any

from src.integrations.scia_integration.model.scia_model_interface import SciaAnalysis, SciaModelBuilder


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

    This function now uses the centralized unit conversion system to ensure
    units mapping and value conversion stay in sync.

    :param results: The complete results dictionary from extract_analysis_results
    :returns: Mapping from category -> { result_component: unit_string }
    :rtype: dict[str, dict[str, str]]
    """
    # Import the centralized unit conversion system
    from .scia_unit_conversion import build_units_mapping as build_units_mapping_centralized

    # Use the centralized system
    return build_units_mapping_centralized(results)
