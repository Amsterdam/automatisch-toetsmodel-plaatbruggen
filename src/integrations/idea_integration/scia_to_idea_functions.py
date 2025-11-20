"""
Functions for processing SCIA results data for IDEA StatiCa integration.

This module processes SCIA CS (Cross Section) results for use in IDEA RCS:

**CS Section Results** (process_scia_cs_results_for_idea):
   - Results from cross-sections defined on plane objects
   - Zone identification: Coordinate-based mapping (done in scia_results_processor)
   - Returns: DataFrame with filtered envelope data (ULS and SLS freq only)
   - Note: Requires bridge_segments to be passed for zone identification
   - Normal forces (n_xD, n_yD) are included in the results
"""

from pathlib import Path
from typing import Any

import pandas as pd


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
    except Exception:
        pass


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
    from src.integrations.scia_integration.results.scia_results_processor import _map_cs_section_to_zone

    return _map_cs_section_to_zone(cs_name, coords_xyz, bridge_segments)


def process_scia_cs_results_for_idea(
    results: dict[str, Any],
    bridge_segments: list[Any],
) -> pd.DataFrame:
    """
    Process SCIA CS (Cross Section) force envelope results for IDEA StatiCa integration.

    This function uses the filtered envelope data from extract_cs_force_envelopes which
    contains only the maximum absolute force/moment values per zone for ULS and SLS freq.
    SLS kar results are no longer used.

    The returned DataFrame includes:
    - Force/moment columns: v_x, v_y, m_xD+, m_xD-, m_yD+, m_yD-, n_xD, n_yD (with _max suffix)
    - Metadata: name, zone, coords_xyz, belasting, max_for_column, result_type

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param bridge_segments: List of bridge segment dimension objects (BridgeSegmentDimensions)
                           Required for coordinate-based zone matching
    :type bridge_segments: list[Any]
    :returns: DataFrame with filtered CS envelope results in IDEA-specific format
    :rtype: pd.DataFrame
    :raises ValueError: If bridge_segments is empty or None
    """
    if not bridge_segments:
        raise ValueError("Bridge segments data is required for CS results processing")

    # Try to use cached envelope dataframe first (performance optimization)
    df_envelope = results.get("df_cs_envelope")

    # If not cached or empty, extract from raw results
    if df_envelope is None or (isinstance(df_envelope, pd.DataFrame) and df_envelope.empty):
        from src.integrations.scia_integration.results.scia_results_processor import extract_cs_force_envelopes

        df_envelope = extract_cs_force_envelopes(results, bridge_segments)

    if df_envelope.empty:
        return pd.DataFrame()

    # Create copy to avoid modifying original cached data
    idea_df = df_envelope.copy()

    # Rename force/moment columns to IDEA-specific names (add _max suffix if not present)
    column_mapping = {
        "v_x": "v_x_max",
        "v_y": "v_y_max",
        "m_xD+": "m_xD+_max",
        "m_xD-": "m_xD-_max",
        "m_yD+": "m_yD+_max",
        "m_yD-": "m_yD-_max",
        "n_xD": "n_xD_max",
        "n_yD": "n_yD_max",
    }

    for old_col, new_col in column_mapping.items():
        if old_col in idea_df.columns and new_col not in idea_df.columns:
            idea_df[new_col] = idea_df[old_col]
            idea_df = idea_df.drop(columns=[old_col])

    # Zone column should already be present from extract_cs_force_envelopes
    # Verify it exists
    if "zone" not in idea_df.columns:
        error_msg = "Zone column missing from CS envelope data. Ensure bridge_segments are provided."
        raise ValueError(error_msg)

    return idea_df
