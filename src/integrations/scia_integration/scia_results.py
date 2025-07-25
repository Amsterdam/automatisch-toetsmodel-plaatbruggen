"""
SCIA results extraction and processing utilities.

This module provides functions for extracting and processing results from SCIA analysis.
These functions are pure Python and can be used by the app layer to retrieve analysis results.
"""

from typing import Any

from .scia_model_interface import SciaAnalysis, SciaModelBuilder


def extract_analysis_results(builder: SciaModelBuilder, analysis: SciaAnalysis) -> dict[str, object]:
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
    summary = {
        "analysis_successful": results.get("analysis_status", {}).get("executed", False),
        "has_displacements": results.get("displacements", {}).get("status") != "not_implemented",
        "has_internal_forces": results.get("internal_forces", {}).get("status") != "not_implemented",
        "has_reactions": results.get("reactions", {}).get("status") != "not_implemented",
        "has_stresses": results.get("stresses", {}).get("status") != "not_implemented",
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
    uls_combinations = []
    for combo_name, combo in load_combinations.items():
        if "ULS" in combo_name or "UGT" in combo_name:
            uls_combinations.append(combo)

    if uls_combinations:
        builder.create_result_class(name="Ultimate Limit State (ULS)", combinations=uls_combinations)

    # Create SLS (Serviceability Limit State) result class
    sls_combinations = []
    for combo_name, combo in load_combinations.items():
        if "SLS" in combo_name or "BGT" in combo_name or "serviceability" in combo_name.lower():
            sls_combinations.append(combo)

    if sls_combinations:
        builder.create_result_class(name="Serviceability Limit State (SLS)", combinations=sls_combinations)

    # Create a general result class with all combinations if no specific ones found
    if not uls_combinations and not sls_combinations and load_combinations:
        all_combinations = list(load_combinations.values())
        builder.create_result_class(name="All Load Combinations", combinations=all_combinations)
