"""
Integration Strip to IDEA Adapter Functions.

This module provides functions to convert integration strip results into the format
expected by IDEA StatiCa RCS integration, replacing the previous cross-section approach.

The integration strip envelope data needs to be transformed to match the format that
IDEA expects for cross-section capacity checks.

Mapping logic:
- X-direction strips (x_reg/x_sup) → dwars (transverse) cross-section in IDEA
- Y-direction strips (y_reg/y_sup) → langs (longitudinal) cross-section in IDEA

Force mapping:
- For X-direction strips: N → N, V_z → Qz, M_x → My
- For Y-direction strips: N → N, V_y → Qz, M_y → My

For each zone and each value of "filtered_for" (gefilterd voor), we create one extreme
combining ULS and SLS freq data.
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

    The input envelope DataFrame has columns:
    - zone: Zone identifier (e.g., "Z1-1")
    - direction: "x" or "y"
    - limit_state: "ULS" or "SLSfreq"
    - filtered_for: What was maximized (e.g., "max_N", "min_V_y")
    - N, V_y, V_z, M_x, M_y, M_z: Force/moment values
    - load_case: Load case name
    - dx: Position along strip

    The returned DataFrame should have columns matching what _apply_integration_strip_loads_to_slabs expects:
    - zone: Zone identifier
    - direction: "x" or "y" (from strip direction)
    - filtered_for: What was maximized
    - limit_state: "ULS" or "SLSfreq"
    - N, Qz, My: Mapped force values for IDEA
    - load_case: Load case name
    - dx: Position

    :param results: SCIA analysis results dictionary with integration_strips data
    :type results: dict[str, Any]
    :returns: DataFrame formatted for IDEA RCS integration
    :rtype: pd.DataFrame
    :raises ValueError: If integration_strips data is missing
    """
    # Check if we have integration strip data
    integration_strips = results.get("integration_strips")

    if integration_strips is None:
        msg = "Integration strips data not found in results. Ensure SCIA analysis has been run."
        raise ValueError(msg)

    # Get the envelope DataFrame
    df_envelope = integration_strips.get("envelope", pd.DataFrame())

    if df_envelope.empty:
        return pd.DataFrame()

    # Create copy to avoid modifying cached data
    idea_df = df_envelope.copy()

    # Verify required columns exist
    required_columns = ["zone", "direction", "limit_state", "filtered_for"]
    missing_columns = [col for col in required_columns if col not in idea_df.columns]

    if missing_columns:
        error_msg = f"Missing required columns for IDEA integration: {missing_columns}"
        raise ValueError(error_msg)

    # Map the forces based on direction
    return _map_strip_forces_to_idea_format(idea_df)


def _map_strip_forces_to_idea_format(
    df_strips: pd.DataFrame,
) -> pd.DataFrame:
    """
    Map integration strip forces to IDEA's expected format.

    For X-direction strips (transverse/dwars):
    - N → N (normal force)
    - V_z → Qz (shear force)
    - M_x → My (bending moment)

    For Y-direction strips (longitudinal/langs):
    - N → N (normal force)
    - V_y → Qz (shear force)
    - M_y → My (bending moment)

    Also normalizes zone names from "Z1-1" format to "1-1" format to match
    bridge segment zone naming conventions.

    :param df_strips: DataFrame with integration strip envelope results
    :type df_strips: pd.DataFrame
    :returns: DataFrame with forces mapped to IDEA format (N, Qz, My)
    :rtype: pd.DataFrame
    """
    if df_strips.empty:
        return pd.DataFrame()

    # Create a copy to avoid modifying input
    result_df = df_strips.copy()

    # Normalize zone names: "Z1-1" → "1-1"
    if "zone" in result_df.columns:
        result_df["zone"] = result_df["zone"].str.replace("Z", "", regex=False)

    # Initialize the IDEA columns
    result_df["Qz"] = 0.0
    result_df["My"] = 0.0

    # Map forces based on direction
    # X-direction: V_z → Qz, M_x → My
    x_mask = result_df["direction"] == "x"
    if x_mask.any():
        result_df.loc[x_mask, "Qz"] = result_df.loc[x_mask, "V_z"]
        result_df.loc[x_mask, "My"] = result_df.loc[x_mask, "M_x"]

    # Y-direction: V_y → Qz, M_y → My
    y_mask = result_df["direction"] == "y"
    if y_mask.any():
        result_df.loc[y_mask, "Qz"] = result_df.loc[y_mask, "V_y"]
        result_df.loc[y_mask, "My"] = result_df.loc[y_mask, "M_y"]

    # Note: N is already present and doesn't need mapping

    return result_df


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

    This is now handled by _map_strip_forces_to_idea_format, but kept for compatibility.

    :param df_strips: DataFrame with integration strip envelope results
    :type df_strips: pd.DataFrame
    :returns: DataFrame in cross-section format for IDEA
    :rtype: pd.DataFrame
    """
    return _map_strip_forces_to_idea_format(df_strips)
