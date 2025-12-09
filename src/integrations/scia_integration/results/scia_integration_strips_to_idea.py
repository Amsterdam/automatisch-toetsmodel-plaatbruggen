"""
Integration Strip to IDEA Adapter Functions.

This module provides functions to convert integration strip results into the format
expected by IDEA StatiCa RCS integration, replacing the previous cross-section approach.

The integration strip envelope data needs to be transformed to match the format that
IDEA expects for cross-section capacity checks.
"""

from typing import Any

import pandas as pd


def process_integration_strips_for_idea(
    results: dict[str, Any],
) -> pd.DataFrame:
    """
    Process integration strip envelope results for IDEA StatiCa integration.

    This function transforms the integration strip envelope data into the format
    expected by IDEA RCS. It replaces the previous process_scia_cs_results_for_idea()
    function that worked with cross-section results.

    The returned DataFrame should have columns matching IDEA's expectations:
    - zone: Zone identifier (e.g., "Z1-1")
    - direction: "x" or "y"
    - limit_state: "ULS" or "SLSfreq"
    - Force/moment columns with appropriate naming
    - Load case information

    :param results: SCIA analysis results dictionary with integration_strips data
    :type results: dict[str, Any]
    :returns: DataFrame formatted for IDEA RCS integration
    :rtype: pd.DataFrame
    :raises ValueError: If integration_strips data is missing
    """
    # Check if we have integration strip data
    integration_strips = results.get("integration_strips")

    if integration_strips is None:
        raise ValueError("Integration strips data not found in results. Ensure SCIA analysis has been run.")

    # Get the envelope DataFrame
    df_envelope = integration_strips.get("envelope", pd.DataFrame())

    if df_envelope.empty:
        return pd.DataFrame()

    # Create copy to avoid modifying cached data
    idea_df = df_envelope.copy()

    # TODO: Transform data to match IDEA's expected format
    # This will depend on how IDEA expects to receive the data
    # For now, we return the envelope as-is
    # Future steps (step 3 from user requirements) will implement the actual transformation

    # Verify required columns exist
    required_columns = ["zone", "direction", "limit_state"]
    missing_columns = [col for col in required_columns if col not in idea_df.columns]

    if missing_columns:
        error_msg = f"Missing required columns for IDEA integration: {missing_columns}"
        raise ValueError(error_msg)

    return idea_df


def map_integration_strip_forces_to_cross_section_format(
    df_strips: pd.DataFrame,
) -> pd.DataFrame:
    """
    Map integration strip forces to the cross-section format expected by IDEA.

    This function bridges the gap between integration strip results and the
    cross-section format that IDEA RCS expects. It may involve:
    - Aggregating forces from multiple strips per zone
    - Converting force naming conventions
    - Restructuring data layout

    :param df_strips: DataFrame with integration strip envelope results
    :type df_strips: pd.DataFrame
    :returns: DataFrame in cross-section format for IDEA
    :rtype: pd.DataFrame
    """
    # TODO: Implement the mapping logic based on IDEA's requirements
    # This is placeholder logic that will be refined in step 3

    if df_strips.empty:
        return pd.DataFrame()

    # For now, return a copy
    # The actual implementation will depend on IDEA's specific requirements
    result_df = df_strips.copy()

    return result_df
