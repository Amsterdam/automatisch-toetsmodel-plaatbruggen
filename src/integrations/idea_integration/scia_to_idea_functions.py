"""
Functions for processing SCIA results data for IDEA StatiCa integration.

This module processes three types of SCIA results for use in IDEA RCS:

1. **2D Node Results** (process_scia_node_results_for_idea):
   - Results at node points on the slab
   - Zone identification: Embedded in the 'name' column
   - Returns: dict with 'node_ULS', 'node_SLS kar', 'node_SLS freq' keys

2. **Integration Strip Results** (process_scia_integration_strip_results_for_idea):
   - 1D force results along integration strips
   - Zone identification: Extracted from strip name (e.g., "strip_Z3_1_(...)" -> "3-1")
   - Returns: dict with 'strip_ULS', 'strip_SLS kar', 'strip_SLS freq' keys

3. **CS Section Results** (process_scia_cs_results_for_idea):
   - Results from cross-sections defined on plane objects
   - Zone identification: Coordinate-based mapping (done in scia_results_processor)
   - Returns: dict with 'cs_ULS', 'cs_SLS kar', 'cs_SLS freq' keys
   - Note: Requires bridge_segments to be passed for zone identification
"""

from pathlib import Path
from typing import Any

import pandas as pd

from src.integrations.scia_integration.scia_results_processor import (
    process_scia_1d_results,
    process_scia_2d_results,
)


def _export_cs_dataframe_to_excel(df: pd.DataFrame, filename: str, sheet_name: str = "Data") -> None:
    """
    Export CS DataFrame to Excel file for debugging (SCIA to IDEA conversion).

    Creates files in C:/temp/ directory for easy manual inspection.

    :param df: DataFrame to export
    :type df: pd.DataFrame
    :param filename: Name of the Excel file (without extension)
    :type filename: str
    :param sheet_name: Name of the Excel sheet
    :type sheet_name: str
    """
    try:
        # Create temp directory if it doesn't exist
        temp_dir = Path("C:/temp")
        temp_dir.mkdir(exist_ok=True)

        # Export to Excel
        filepath = temp_dir / f"{filename}.xlsx"
        df.to_excel(filepath, sheet_name=sheet_name, index=False)
        print(f"✓ SCIA→IDEA EXPORT: {len(df)} rows to: {filepath}")
    except Exception as e:
        print(f"✗ SCIA→IDEA EXPORT FAILED {filename}: {e}")


def map_cs_section_to_zone(cs_name: str, coords_xyz: tuple[float, float, float], bridge_segments: list[Any]) -> str:
    """
    Map CS section to zone - delegates to scia_results_processor.

    This is a compatibility wrapper. The actual zone mapping is now done in
    scia_results_processor._map_cs_section_to_zone() and applied during
    process_scia_cs_results() if bridge_segments are provided.

    :param cs_name: Name of the CS section
    :type cs_name: str
    :param coords_xyz: Coordinates as (x, y, z) tuple
    :type coords_xyz: tuple[float, float, float]
    :param bridge_segments: List of bridge segment dimension objects
    :type bridge_segments: list[Any]
    :returns: Zone identifier (e.g., "1-1", "2-1")
    :rtype: str
    """
    from src.integrations.scia_integration.scia_results_processor import _map_cs_section_to_zone

    return _map_cs_section_to_zone(cs_name, coords_xyz, bridge_segments)


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
    return {f"node_{key}": value for key, value in idea_results_2d.items()}


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
    return {f"strip_{key}": value for key, value in idea_results_1d.items()}


def process_scia_cs_results_for_idea(results: dict[str, Any], bridge_segments: list[Any]) -> dict[str, pd.DataFrame]:
    """
    Process SCIA CS (Cross Section) analysis results for IDEA StatiCa integration.

    This function processes CS section results and applies IDEA-specific column naming
    and data formatting. Zone information should already be present in the results
    if bridge_segments were provided to the SCIA processing function.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param bridge_segments: List of bridge segment dimension objects (BridgeSegmentDimensions)
                           Required for coordinate-based zone matching if not already in results
    :type bridge_segments: list[Any]
    :returns: Dictionary containing DataFrames for each CS result table with IDEA-specific formatting
    :rtype: dict[str, pd.DataFrame]
    :raises ValueError: If bridge_segments is empty or None
    """
    if not bridge_segments:
        raise ValueError("Bridge segments data is required for CS results processing")

    # Use the general CS processing function with bridge_segments for zone mapping
    from src.integrations.scia_integration.scia_results_processor import process_scia_cs_results

    raw_results_cs = process_scia_cs_results(results, bridge_segments)

    # DEBUG EXPORT: Export raw CS results from SCIA processor (before IDEA conversion)
    for selected_table, df_raw in raw_results_cs.items():
        if not df_raw.empty:
            safe_table_name = selected_table.replace(" ", "_")
            _export_cs_dataframe_to_excel(df_raw, f"cs_scia_to_idea_raw_{safe_table_name}", f"CS_{safe_table_name}_Raw")

    # Convert to IDEA-specific format
    idea_results_cs = {}

    for selected_table, df_cs in raw_results_cs.items():
        if df_cs.empty:
            idea_results_cs[selected_table] = df_cs
            continue

        # Create copy to avoid modifying original
        idea_df = df_cs.copy()

        # Rename columns to IDEA-specific names (with _max suffix)
        column_mapping = {
            "v_x": "v_x_max",
            "v_y": "v_y_max",
            "m_xD+": "m_xD+_max",
            "m_xD-": "m_xD-_max",
            "m_yD+": "m_yD+_max",
            "m_yD-": "m_yD-_max",
        }

        for old_col, new_col in column_mapping.items():
            if old_col in idea_df.columns:
                idea_df[new_col] = idea_df[old_col]
                idea_df = idea_df.drop(columns=[old_col])

        # Zone column should already be present from process_scia_cs_results
        # If not present (e.g., bridge_segments were not provided earlier), add it now
        if "zone" not in idea_df.columns and "name" in idea_df.columns and "coords_xyz" in idea_df.columns:
            idea_df["zone"] = idea_df.apply(lambda row: map_cs_section_to_zone(row["name"], row["coords_xyz"], bridge_segments), axis=1)

        idea_results_cs[selected_table] = idea_df

    # DEBUG EXPORT: Export IDEA-formatted CS results (after conversion)
    for selected_table, df_idea in idea_results_cs.items():
        if not df_idea.empty:
            safe_table_name = selected_table.replace(" ", "_")
            _export_cs_dataframe_to_excel(df_idea, f"cs_scia_to_idea_converted_{safe_table_name}", f"CS_{safe_table_name}_IDEA")

    # Add cs_ prefix to all keys to distinguish from node and strip results
    return {f"cs_{key}": value for key, value in idea_results_cs.items()}
