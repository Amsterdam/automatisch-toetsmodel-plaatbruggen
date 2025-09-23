"""Functions for processing SCIA results data for IDEA StatiCa integration."""

from typing import Any

import pandas as pd

from src.integrations.scia_integration.scia_results_processor import (
    process_scia_1d_results,
    process_scia_2d_results,
)


def process_scia_node_results_for_idea(results: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Process SCIA analysis results to create a DataFrame suitable for IDEA StatiCa integration.

    This function uses the general SCIA 2D processing and then applies IDEA-specific
    column naming and data formatting.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Dictionary containing DataFrames for each result table with IDEA-specific formatting
    :rtype: dict[str, pd.DataFrame]
    """
    # Use the general 2D processing function
    raw_results_2d = process_scia_2d_results(results)

    # Convert to IDEA-specific format
    idea_results_2d = {}

    for selected_table, df_2d in raw_results_2d.items():
        if df_2d.empty:
            idea_results_2d[selected_table] = df_2d
            continue

        # Create copy to avoid modifying original
        idea_df = df_2d.copy()

        # Rename columns to IDEA-specific names (with _max suffix)
        column_mapping = {"v_x": "v_x_max", "v_y": "v_y_max", "m_xD+": "m_xD+_max", "m_xD-": "m_xD-_max", "m_yD+": "m_yD+_max", "m_yD-": "m_yD-_max"}

        for old_col, new_col in column_mapping.items():
            if old_col in idea_df.columns:
                idea_df[new_col] = idea_df[old_col]
                idea_df = idea_df.drop(columns=[old_col])

        idea_results_2d[selected_table] = idea_df

    # Add node_ prefix to all keys to distinguish from integration strip results
    prefixed_results = {f"node_{key}": value for key, value in idea_results_2d.items()}

    return prefixed_results


def process_scia_integration_strip_results_for_idea(results: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Process SCIA 1D force analysis results to create DataFrames suitable for IDEA StatiCa integration.

    This function uses the general SCIA 1D processing and then applies IDEA-specific
    column naming and data formatting.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Dictionary containing DataFrames for each 1D result table with IDEA-specific formatting
    :rtype: dict[str, pd.DataFrame]
    """
    # Use the general 1D processing function
    raw_results_1d = process_scia_1d_results(results)

    # Convert to IDEA-specific format
    idea_results_1d = {}

    for selected_table, df_1d in raw_results_1d.items():
        if df_1d.empty:
            idea_results_1d[selected_table] = df_1d
            continue

        # Create copy to avoid modifying original
        idea_df = df_1d.copy()

        # Drop the E/W/N column if it exists it's not needed for IDEA
        if "E/W/N" in idea_df.columns:
            idea_df = idea_df.drop(columns=["E/W/N"])

        # Drop the N column if it exists it's not needed for IDEA
        if "N" in idea_df.columns:
            idea_df = idea_df.drop(columns=["N"])

        # Rename columns to IDEA-specific names (with _max suffix)
        column_mapping = {
            "N": "n_max",
            "V_y": "v_y_max",
            "V_z": "v_z_max",
            "M_x": "m_x_max",
            "M_y": "m_y_max",
            "M_z": "m_z_max",
            "Naam": "name",  # Rename Dutch "Naam" to English "name" for consistency
        }

        for old_col, new_col in column_mapping.items():
            if old_col in idea_df.columns:
                idea_df[new_col] = idea_df[old_col]
                idea_df = idea_df.drop(columns=[old_col])

        idea_results_1d[selected_table] = idea_df

    # Add strip_ prefix to all keys to distinguish from node results
    prefixed_results = {f"strip_{key}": value for key, value in idea_results_1d.items()}

    return prefixed_results
