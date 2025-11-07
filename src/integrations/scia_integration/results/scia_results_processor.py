"""
Core functions for processing SCIA analysis results data.

This module provides utilities to extract and process SCIA analysis results including:
- 2D force tables (basis and elementaire ontwerpgrootheden)
- 1D force tables (integration strips)
- CS (Cross Section) tables for ULS, SLS kar, and SLS freq

New CS Table Functions:
    - find_2d_force_tables_cs: Find a specific CS table type
    - find_all_2d_cs_force_tables: Find all CS table types at once

CS Table Types (results from SCIA section on plane objects):
    - "cs ULS": Ultimate Limit State cross sections
    - "cs SLS kar": Serviceability Limit State - characteristic cross sections
    - "cs SLS freq": Serviceability Limit State - frequent cross sections
"""

import functools
from pathlib import Path
from typing import Any, Callable, Union

import pandas as pd

from src.integrations.scia_integration.constants.results import (
    CS_BASIS_TABLE_PATTERN,
    CS_ELEMENTAIRE_TABLE_PATTERN,
    CS_TABLE_TYPES,
)

from .scia_result_helpers import get_nested_result_data


def _export_dataframe_to_excel_view(df: pd.DataFrame, filename: str, sheet_name: str = "Data") -> None:
    """
    Export DataFrame to Excel file for debugging (view processing).

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


def merge_xyz_to_coords_xyz(data_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Merges 'x', 'y', and 'z' keys into a single 'coords_xyz' key (list of (x, y, z) tuples) and removes the originals.

    :param data_dict: Dictionary with keys including 'x', 'y', 'z'
    :type data_dict: dict[str, Any]
    :returns: Modified dictionary with 'coords_xyz' and without 'x', 'y', 'z'
    :rtype: dict[str, Any]
    """
    if not all(k in data_dict for k in ("x", "y", "z")):
        return data_dict

    x_vals = data_dict.get("x", [])
    y_vals = data_dict.get("y", [])
    z_vals = data_dict.get("z", [])

    # Ensure all are lists of the same length
    if not (isinstance(x_vals, list) and isinstance(y_vals, list) and isinstance(z_vals, list)):
        return data_dict
    if not (len(x_vals) == len(y_vals) == len(z_vals)):
        return data_dict

    coords_xyz = [(x, y, z) for x, y, z in zip(x_vals, y_vals, z_vals)]
    data_dict["coords_xyz"] = coords_xyz

    # Remove x, y, z keys
    for k in ("x", "y", "z"):
        data_dict.pop(k, None)

    return data_dict


def get_unique_coords_xyz_dataframe(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame with all unique (name, coords_xyz) combinations
    from both input DataFrames, ensuring no duplicates.

    :param df1: First DataFrame (e.g., df_elementaire)
    :type df1: pd.DataFrame
    :param df2: Second DataFrame (e.g., df_basis)
    :type df2: pd.DataFrame
    :returns: DataFrame with unique (name, coords_xyz) combinations (no duplicates)
    :rtype: pd.DataFrame
    """
    # Collect all (name, coords_xyz) pairs from both DataFrames
    pairs_list = []

    for df in [df1, df2]:
        if df.empty or "coords_xyz" not in df.columns or "Naam" not in df.columns:
            continue

        for _, row in df.iterrows():
            coord = tuple(row["coords_xyz"]) if isinstance(row["coords_xyz"], list) else row["coords_xyz"]
            name = str(row["Naam"])
            pairs_list.append((name, coord))

    # Remove duplicates while preserving order
    unique_pairs_set = set()
    unique_pairs_list = []

    for name, coord in pairs_list:
        pair_key = (name, str(coord))  # Use string representation for set membership
        if pair_key not in unique_pairs_set:
            unique_pairs_set.add(pair_key)
            unique_pairs_list.append({"name": name, "coords_xyz": coord})

    return pd.DataFrame(unique_pairs_list)


def get_name_for_coords(coords_value: tuple[float, float, float] | list[float], df_elementaire: pd.DataFrame, df_basis: pd.DataFrame) -> str:
    """
    Find the name for given coordinates by searching in both elementaire and basis DataFrames.

    :param coords_value: The coordinate tuple to search for
    :type coords_value: Any
    :param df_elementaire: DataFrame with elementaire ontwerpgrootheden
    :type df_elementaire: pd.DataFrame
    :param df_basis: DataFrame with basis grootheden
    :type df_basis: pd.DataFrame
    :returns: The name corresponding to the coordinates, or "zone name not found" if not found
    :rtype: str
    """
    # Convert coords_value to tuple for consistent comparison
    if isinstance(coords_value, list):
        coords_value = tuple(coords_value)  # type: ignore[assignment]

    # Try to find the name in df_elementaire first
    if "coords_xyz" in df_elementaire.columns and "Naam" in df_elementaire.columns:
        # Use direct equality comparison which is much faster than string conversion
        elementaire_matches = df_elementaire[df_elementaire["coords_xyz"] == coords_value]
        if not elementaire_matches.empty:
            return str(elementaire_matches.iloc[0]["Naam"])

    # If not found, try df_basis
    if "coords_xyz" in df_basis.columns and "Naam" in df_basis.columns:
        basis_matches = df_basis[df_basis["coords_xyz"] == coords_value]
        if not basis_matches.empty:
            return str(basis_matches.iloc[0]["Naam"])

    return "zone name not found"


def get_max_abs_for_column(coords_value: tuple[float, float, float] | list[float], df: pd.DataFrame, col: str) -> float:
    """
    Get the original value that has the maximum absolute value for a specific column matching the given coordinates.

    This function finds the value with the largest absolute magnitude but returns the original value
    with its sign preserved (e.g., if values are [2, -5, 3], it returns -5 because |-5| = 5 is maximum).

    :param coords_value: The coordinate tuple to search for
    :type coords_value: Any
    :param df: DataFrame to search in
    :type df: pd.DataFrame
    :param col: Column name to get the value with maximum absolute value from
    :type col: str
    :returns: Original value that has maximum absolute value, or NaN if not found or not numeric
    :rtype: float
    """
    if "coords_xyz" not in df.columns or col not in df.columns:
        return float("nan")

    # Convert coords_value to tuple for consistent comparison
    if isinstance(coords_value, list):
        coords_value = tuple(coords_value)  # type: ignore[assignment]

    # Use direct equality comparison which is much faster than string conversion
    matches = df[df["coords_xyz"] == coords_value]

    if matches.empty:
        return float("nan")

    # Convert to numeric, handling any non-numeric values as NaN, then find the value with maximum absolute value
    numeric_values = pd.to_numeric(matches[col], errors="coerce")
    if numeric_values.isna().all():
        return float("nan")
    # Find the original value that has the maximum absolute value
    max_abs_idx = numeric_values.abs().idxmax()
    return numeric_values.loc[max_abs_idx]


def _extract_scia_table_data(results: dict[str, Any], selected_table: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """
    Extract basis and elementaire data for a specific table from SCIA results.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param selected_table: Table name to extract
    :type selected_table: str
    :returns: Tuple of (basis_data, elementaire_data)
    :rtype: tuple[dict[str, Any] | None, dict[str, Any] | None]
    """
    # Read "basis grootheden"
    basis_data = (
        results.get("xml_parsing", {})
        .get("parsed_tables", {})
        .get(f"Interne 2D-krachten basis {selected_table}", {})
        .get("data", {})
        .get("p0", None)  # P0 is nodes
    )

    # Read "elementaire ontwerpgrootheden"
    elementaire_data = (
        results.get("xml_parsing", {})
        .get("parsed_tables", {})
        .get(f"Interne 2D-krachten elementair {selected_table}", {})
        .get("data", {})
        .get("p0", None)  # p0 is nodes
    )

    return basis_data, elementaire_data


def find_2d_force_tables_cs(results: dict[str, Any], table_type: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """
    Find and extract basis and elementaire CS (Cross Section) tables for 2D forces.

    These tables contain results from SCIA section on plane objects (cross sections).

    New table series:
    - Interne 2D-krachten basis cs ULS
    - Interne 2D-krachten elementair cs ULS
    - Interne 2D-krachten basis cs SLS kar
    - Interne 2D-krachten elementair cs SLS kar
    - Interne 2D-krachten basis cs SLS freq
    - Interne 2D-krachten elementair cs SLS freq

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param table_type: Table type to extract (e.g., "cs ULS", "cs SLS kar", "cs SLS freq")
    :type table_type: str
    :returns: Tuple of (basis_data, elementaire_data)
    :rtype: tuple[dict[str, Any] | None, dict[str, Any] | None]
    """
    # Read "basis grootheden" CS table
    basis_table_name = CS_BASIS_TABLE_PATTERN.format(table_type=table_type)
    basis_data = get_nested_result_data(results, basis_table_name, data_key="p1")  # P1 is sections

    # If not found with p1, try p0 (nodes)
    if basis_data is None:
        basis_data = get_nested_result_data(results, basis_table_name, data_key="p0")

    # Read "elementaire ontwerpgrootheden" CS table
    elementaire_table_name = CS_ELEMENTAIRE_TABLE_PATTERN.format(table_type=table_type)
    elementaire_data = get_nested_result_data(results, elementaire_table_name, data_key="p1")  # P1 is sections

    # If not found with p1, try p0 (nodes)
    if elementaire_data is None:
        elementaire_data = get_nested_result_data(results, elementaire_table_name, data_key="p0")

    return basis_data, elementaire_data


def find_all_2d_cs_force_tables(
    results: dict[str, Any],
) -> dict[str, tuple[dict[str, Any] | None, dict[str, Any] | None]]:
    """
    Find all CS (Cross Section) 2D force tables at once.

    These tables contain results from SCIA section on plane objects (cross sections).

    Searches for all three CS table types:
    - ULS (Ultimate Limit State cross sections)
    - SLS kar (Serviceability Limit State - characteristic cross sections)
    - SLS freq (Serviceability Limit State - frequent cross sections)

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Dictionary mapping table type to (basis_data, elementaire_data) tuples
    :rtype: dict[str, tuple[dict[str, Any] | None, dict[str, Any] | None]]
    """
    all_tables: dict[str, tuple[dict[str, Any] | None, dict[str, Any] | None]] = {}

    for table_type in CS_TABLE_TYPES:
        basis_data, elementaire_data = find_2d_force_tables_cs(results, table_type)
        all_tables[str(table_type)] = (basis_data, elementaire_data)

    return all_tables


def _process_cs_selected_result_tables(results: dict[str, Any], selected_result_tables: list[str]) -> dict[str, Any]:
    """
    Process and merge SCIA CS table data for selected result tables.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param selected_result_tables: List of table types to process (e.g., ["ULS", "SLS kar"])
    :type selected_result_tables: list[str]
    :returns: Dictionary with processed CS table data
    :rtype: dict[str, Any]
    """
    selected_data_scia_cs = {}

    # Read the selected CS data from the "results" into a new dict
    for selected_table in selected_result_tables:
        basis_data, elementaire_data = find_2d_force_tables_cs(results, selected_table)

        basis_table_name = CS_BASIS_TABLE_PATTERN.format(table_type=selected_table)
        elementaire_table_name = CS_ELEMENTAIRE_TABLE_PATTERN.format(table_type=selected_table)

        selected_data_scia_cs[basis_table_name] = basis_data
        selected_data_scia_cs[elementaire_table_name] = elementaire_data

    # Merge x, y, z into coords_xyz for CS force tables
    for key, data in selected_data_scia_cs.items():
        if data is not None and isinstance(data, dict):
            selected_data_scia_cs[key] = merge_xyz_to_coords_xyz(data)

    return selected_data_scia_cs


def _map_cs_section_to_zone(
    _cs_name: str,
    coords_xyz: tuple[float, float, float],
    bridge_segments: list[Any],  # List of BridgeSegmentDimensions
) -> str:
    """
    Map a CS section to its corresponding geometric zone based on coordinates.

    This function determines which load/reinforcement zone a CS section belongs to
    by analyzing its spatial coordinates and comparing them to the bridge geometry.

    Zone numbering format: "{zone_type}-{segment_number}"
    - zone_type: 1 (top outer/bz1), 2 (middle/bz2), 3 (bottom outer/bz3)
    - segment_number: 1-based segment index

    Bridge coordinate system:
    - X-axis: Longitudinal direction (along bridge length)
    - Y-axis: Transverse direction (across bridge width)
        * Positive Y: Top/left side (zone 1 - bz1)
        * Near 0: Middle (zone 2 - bz2)
        * Negative Y: Bottom/right side (zone 3 - bz3)
    - Z-axis: Vertical direction (height)

    :param _cs_name: Name of the CS section (currently unused, kept for future error messages/debugging)
    :type _cs_name: str
    :param coords_xyz: Coordinates of the CS section as (x, y, z) tuple
    :type coords_xyz: tuple[float, float, float]
    :param bridge_segments: List of bridge segment objects from VIKTOR parametrization (Munch)
                           or Pydantic models. Each segment should have:
                           - Length: 'l' (VIKTOR) or 'segment_length' (Pydantic)
                           - Zone widths: bz1, bz2, bz3
    :type bridge_segments: list[Any]
    :returns: Zone identifier (e.g., "1-1", "2-1", etc.)
              Returns "unknown-zone" if coordinates don't match any zone
    :rtype: str
    :raises ValueError: If bridge_segments is empty or None
    """
    if not bridge_segments:
        raise ValueError("Bridge segments data is required for zone mapping")

    # Convert coordinates to float (they may be strings from DataFrame)
    x, y, z = coords_xyz
    x = float(x)
    y = float(y)
    z = float(z)

    # --- Step 1: Determine segment number based on x-coordinate (longitudinal position) ---
    cumulative_length = 0.0
    segment_number = 1  # Default to first segment

    for i in range(1, len(bridge_segments)):  # Start from index 1
        # Get segment length - support both VIKTOR Munch (l) and Pydantic model (segment_length)
        segment_length = getattr(bridge_segments[i], "l", None) or getattr(bridge_segments[i], "segment_length", 0.0)
        segment_length = float(segment_length) if segment_length is not None else 0.0
        cumulative_length += segment_length

        if x <= cumulative_length:
            segment_number = i
            break
    else:
        # If x is beyond all segments, assign to last segment
        segment_number = len(bridge_segments) - 1

    # --- Step 2: Determine zone type based on y-coordinate (transverse position) ---
    # Get segment geometry at the identified segment
    segment = bridge_segments[segment_number]

    # Ensure bz values are floats (may be stored as strings or other types)
    bz2 = float(segment.bz2)
    bz3 = float(segment.bz3)

    # Calculate zone boundaries based on bz1, bz2, bz3 values
    # Bridge cross-section from top to bottom (in Y direction):
    #   Zone 1 (bz1): from (bz2/2 + bz1) to (bz2/2)
    #   Zone 2 (bz2): from (bz2/2) to (-bz2/2)
    #   Zone 3 (bz3): from (-bz2/2) to (-bz2/2 - bz3)

    half_bz2 = bz2 / 2.0
    y_bottom_zone1 = half_bz2  # Bottom boundary of zone 1 = top of zone 2
    y_bottom_zone2 = -half_bz2  # Bottom boundary of zone 2 = top of zone 3
    y_bottom_zone3 = -half_bz2 - bz3  # Bottom boundary of zone 3

    # Determine zone type based on y-coordinate
    if y > y_bottom_zone1:  # Strictly greater for zone 1
        zone_type = 1  # Top zone (bz1)
    elif y > y_bottom_zone2:  # Includes boundary with zone 1
        zone_type = 2  # Middle zone (bz2)
    elif y >= y_bottom_zone3:
        zone_type = 3  # Bottom zone (bz3)
    else:
        # Y-coordinate is outside the bridge geometry
        return "unknown-zone"

    # --- Step 3: Return formatted zone identifier ---
    return f"{zone_type}-{segment_number}"


def _prepare_basis_dataframe(df_basis: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare basis DataFrame with required columns.

    :param df_basis: Raw basis DataFrame
    :type df_basis: pd.DataFrame
    :returns: Prepared DataFrame with name, coords_xyz, belasting, and shear forces
    :rtype: pd.DataFrame
    """
    if not df_basis.empty and "coords_xyz" in df_basis.columns:
        return df_basis[["Naam", "coords_xyz", "Belasting", "v_x", "v_y"]].copy()
    return pd.DataFrame()


def _prepare_elementaire_dataframe(df_elementaire: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare elementaire DataFrame with required columns.

    :param df_elementaire: Raw elementaire DataFrame
    :type df_elementaire: pd.DataFrame
    :returns: Prepared DataFrame with name, coords_xyz, belasting, moments, and normal forces
    :rtype: pd.DataFrame
    """
    if not df_elementaire.empty and "coords_xyz" in df_elementaire.columns:
        elementaire_cols = ["Naam", "coords_xyz", "Belasting", "m_xD+", "m_xD-", "m_yD+", "m_yD-", "n_xD", "n_yD"]
        elementaire_cols_present = [col for col in elementaire_cols if col in df_elementaire.columns]
        return df_elementaire[elementaire_cols_present].copy()
    return pd.DataFrame()


def _merge_basis_and_elementaire(df_basis_merge: pd.DataFrame, df_elementaire_merge: pd.DataFrame) -> pd.DataFrame:
    """
    Merge basis and elementaire DataFrames on (Naam, coords_xyz, Belasting).

    :param df_basis_merge: Prepared basis DataFrame
    :type df_basis_merge: pd.DataFrame
    :param df_elementaire_merge: Prepared elementaire DataFrame
    :type df_elementaire_merge: pd.DataFrame
    :returns: Merged DataFrame
    :rtype: pd.DataFrame
    """
    if not df_basis_merge.empty and not df_elementaire_merge.empty:
        return df_basis_merge.merge(df_elementaire_merge, on=["Naam", "coords_xyz", "Belasting"], how="outer")
    if not df_basis_merge.empty:
        return df_basis_merge.copy()
    if not df_elementaire_merge.empty:
        return df_elementaire_merge.copy()
    return pd.DataFrame()


def _extract_max_force_rows(df_combined: pd.DataFrame, force_columns: list[str]) -> list[pd.Series]:  # type: ignore[type-arg]
    """
    Extract rows with maximum absolute values for each force column.

    :param df_combined: Combined DataFrame with all forces
    :type df_combined: pd.DataFrame
    :param force_columns: List of force column names
    :type force_columns: list[str]
    :returns: List of rows representing max values
    :rtype: list[pd.Series]
    """
    result_rows: list[pd.Series] = []  # type: ignore[type-arg]
    for (name, coords_xyz), group in df_combined.groupby(["name", "coords_xyz"]):
        for force_col in force_columns:
            if force_col in group.columns:
                abs_max_idx = group[force_col].abs().idxmax()
                if pd.notna(abs_max_idx):
                    max_row = group.loc[abs_max_idx].copy()
                    max_row["max_for_column"] = force_col
                    result_rows.append(max_row)  # type: ignore[arg-type]
    return result_rows


def _add_zone_mapping(df_result: pd.DataFrame, bridge_segments: list[Any] | None) -> pd.DataFrame:
    """
    Add zone mapping to the result DataFrame.

    :param df_result: Result DataFrame
    :type df_result: pd.DataFrame
    :param bridge_segments: Optional list of bridge segment objects
    :type bridge_segments: list[Any] | None
    :returns: DataFrame with zone column added
    :rtype: pd.DataFrame
    """
    if not df_result.empty and bridge_segments and len(bridge_segments) > 0:
        try:
            df_result["zone"] = df_result.apply(lambda row: _map_cs_section_to_zone(row["name"], row["coords_xyz"], bridge_segments), axis=1)
        except Exception:
            import traceback

            traceback.print_exc()
            df_result["zone"] = "mapping-failed"
    return df_result


def _process_single_cs_result_table(
    selected_data_scia_cs: dict[str, Any], selected_table: str, bridge_segments: list[Any] | None = None
) -> pd.DataFrame:
    """
    Process a single CS result table and return the processed DataFrame.

    New processing logic:
    1. Merge x,y,z into coords_xyz (already done)
    2. Combine basis and elementaire tables based on (name, coords_xyz, belasting)
    3. For each unique (name, coords_xyz), find rows with max absolute values
       for v_x, v_y, m_xD+, m_xD-, m_yD+, m_yD-, n_xD, n_yD (8 rows per unique combination)

    :param selected_data_scia_cs: Dictionary with CS table data
    :type selected_data_scia_cs: dict[str, Any]
    :param selected_table: Table type (e.g., "ULS", "SLS freq")
    :type selected_table: str
    :param bridge_segments: Optional list of bridge segment objects (VIKTOR Munch or Pydantic).
                           Each segment needs: l/segment_length (length), bz1, bz2, bz3 (widths)
    :type bridge_segments: list[Any] | None
    :returns: Processed DataFrame with filtered rows (8 per unique name+coords combination)
    :rtype: pd.DataFrame
    """
    elementaire_ontwerpgrootheden = selected_data_scia_cs.get(CS_ELEMENTAIRE_TABLE_PATTERN.format(table_type=selected_table), None)
    basis_grootheden = selected_data_scia_cs.get(CS_BASIS_TABLE_PATTERN.format(table_type=selected_table), None)

    # Convert to DataFrames
    df_elementaire = pd.DataFrame(elementaire_ontwerpgrootheden) if elementaire_ontwerpgrootheden is not None else pd.DataFrame()
    df_basis = pd.DataFrame(basis_grootheden) if basis_grootheden is not None else pd.DataFrame()

    if df_elementaire.empty and df_basis.empty:
        return pd.DataFrame()

    # Prepare and merge dataframes
    df_basis_merge = _prepare_basis_dataframe(df_basis)
    df_elementaire_merge = _prepare_elementaire_dataframe(df_elementaire)
    df_combined = _merge_basis_and_elementaire(df_basis_merge, df_elementaire_merge)

    if df_combined.empty:
        return pd.DataFrame()

    # Rename columns for consistency
    df_combined = df_combined.rename(columns={"Naam": "name", "Belasting": "belasting"})

    # Convert force columns to numeric
    force_columns = ["v_x", "v_y", "m_xD+", "m_xD-", "m_yD+", "m_yD-", "n_xD", "n_yD"]
    for col in force_columns:
        if col in df_combined.columns:
            df_combined[col] = pd.to_numeric(df_combined[col], errors="coerce")

    # DEDUPLICATION: For each CS name, keep only the first unique coordinate
    df_combined = (
        df_combined.groupby("name", as_index=False, group_keys=False)
        .apply(lambda group: group[group["coords_xyz"] == group["coords_xyz"].iloc[0]], include_groups=False)
        .reset_index(drop=True)
    )

    # Extract rows with max absolute values
    result_rows = _extract_max_force_rows(df_combined, force_columns)
    df_result = pd.DataFrame(result_rows) if result_rows else pd.DataFrame()

    # Add zone mapping if bridge_segments are provided and return
    return _add_zone_mapping(df_result, bridge_segments)


def process_scia_cs_results(results: dict[str, Any], bridge_segments: list[Any] | None = None) -> dict[str, pd.DataFrame]:
    """
    Process SCIA CS (Cross Section) force analysis results to create DataFrames.

    This function extracts CS force data from SCIA results, processes coordinates,
    and creates DataFrames with unique coordinate locations and their corresponding
    maximum force/moment values for cross section elements.

    CS tables contain:
    - v_x, v_y: Shear forces (from basis table)
    - m_xD+, m_xD-, m_yD+, m_yD-: Moments (from elementaire table)
    - n_xD, n_yD: Normal forces (from elementaire table)
    - belasting: Load case name

    Optionally adds zone identification if bridge_segments are provided.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param bridge_segments: Optional list of bridge segment objects (VIKTOR Munch or Pydantic).
                           Each segment needs: l/segment_length (length), bz1, bz2, bz3 (widths)
    :type bridge_segments: list[Any] | None
    :returns: Dictionary containing DataFrames for each CS result table type
    :rtype: dict[str, pd.DataFrame]
    """
    # Setting to read SCIA xml for CS forces - only ULS and SLS freq
    selected_result_tables = ["ULS", "SLS freq"]

    # Process selected CS result tables
    selected_data_scia_cs = _process_cs_selected_result_tables(results, selected_result_tables)

    # Create empty dict for storing results for each selected table
    results_cs = {}

    # Create DataFrames for each selected CS result class table
    for selected_table in selected_result_tables:
        df_result = _process_single_cs_result_table(selected_data_scia_cs, selected_table, bridge_segments)
        results_cs[selected_table] = df_result

        # DEBUG EXPORT: Export processed CS results for view
        if not df_result.empty:
            safe_table_name = selected_table.replace(" ", "_")
            _export_dataframe_to_excel_view(df_result, f"cs_view_{safe_table_name}", f"CS_{safe_table_name}_View")

    return results_cs


def _combine_uls_and_sls_dataframes(df_uls: pd.DataFrame, df_sls_freq: pd.DataFrame) -> pd.DataFrame:
    """
    Combine ULS and SLS freq DataFrames with result_type labels.

    :param df_uls: ULS DataFrame
    :type df_uls: pd.DataFrame
    :param df_sls_freq: SLS freq DataFrame
    :type df_sls_freq: pd.DataFrame
    :returns: Combined DataFrame with result_type column
    :rtype: pd.DataFrame
    """
    combined_dfs = []

    if not df_uls.empty:
        df_uls_copy = df_uls.copy()
        df_uls_copy["result_type"] = "ULS"
        combined_dfs.append(df_uls_copy)

    if not df_sls_freq.empty:
        df_sls_copy = df_sls_freq.copy()
        df_sls_copy["result_type"] = "SLS freq"
        combined_dfs.append(df_sls_copy)

    if not combined_dfs:
        return pd.DataFrame()

    return pd.concat(combined_dfs, ignore_index=True)


def _extract_envelope_for_zone_and_type(
    df_combined: pd.DataFrame, zone: str, result_type: str, force_columns: list[str], seen_combinations: set
) -> list[pd.Series]:  # type: ignore[type-arg]
    """
    Extract envelope rows for a specific zone and result type.

    :param df_combined: Combined DataFrame with all data
    :type df_combined: pd.DataFrame
    :param zone: Zone identifier
    :type zone: str
    :param result_type: Result type (ULS or SLS freq)
    :type result_type: str
    :param force_columns: List of force column names
    :type force_columns: list[str]
    :param seen_combinations: Set of already seen combinations to avoid duplicates
    :type seen_combinations: set
    :returns: List of envelope rows
    :rtype: list[pd.Series]
    """
    envelope_rows: list[pd.Series] = []  # type: ignore[type-arg]
    zone_type_data = df_combined[(df_combined["zone"] == zone) & (df_combined["result_type"] == result_type)]

    if zone_type_data.empty:
        return envelope_rows

    for force_col in force_columns:
        if force_col in zone_type_data.columns:
            abs_max_idx = zone_type_data[force_col].abs().idxmax()
            if pd.notna(abs_max_idx):
                combination_key = (zone, result_type, force_col, abs_max_idx)
                if combination_key not in seen_combinations:
                    seen_combinations.add(combination_key)
                    row = zone_type_data.loc[abs_max_idx].copy()
                    row["max_for_column"] = force_col
                    envelope_rows.append(row)  # type: ignore[arg-type]

    return envelope_rows


def extract_cs_force_envelopes(results: dict[str, Any], bridge_segments: list[Any] | None = None) -> pd.DataFrame:
    """
    Extract force envelopes from CS (Cross Section) results for ULS and SLS freq combined.

    For each unique zone and result type (ULS/SLS freq), finds rows with maximum absolute values
    for each force component (v_x, v_y, m_xD+, m_xD-, m_yD+, m_yD-, n_xD, n_yD).

    Returns a combined DataFrame sorted by zone and result type.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param bridge_segments: Optional list of bridge segment objects for zone mapping
    :type bridge_segments: list[Any] | None
    :returns: Combined DataFrame with envelope results sorted by zone and result type
    :rtype: pd.DataFrame
    """
    # Process CS results to get ULS and SLS freq DataFrames
    cs_results = process_scia_cs_results(results, bridge_segments)

    df_uls = cs_results.get("ULS", pd.DataFrame())
    df_sls_freq = cs_results.get("SLS freq", pd.DataFrame())

    # Combine ULS and SLS freq tables
    df_combined = _combine_uls_and_sls_dataframes(df_uls, df_sls_freq)

    if df_combined.empty:
        return pd.DataFrame()

    # Check if zone column exists
    if "zone" not in df_combined.columns:
        return df_combined  # Return as-is if no zone mapping

    # Force columns to find max absolute values for
    force_columns = ["v_x", "v_y", "m_xD+", "m_xD-", "m_yD+", "m_yD-", "n_xD", "n_yD"]

    # Extract envelope rows for all zones and result types
    envelope_rows: list[pd.Series] = []  # type: ignore[type-arg]
    seen_combinations: set = set()

    for zone in sorted(df_combined["zone"].unique()):
        for result_type in ["ULS", "SLS freq"]:
            zone_envelope = _extract_envelope_for_zone_and_type(df_combined, zone, result_type, force_columns, seen_combinations)
            envelope_rows.extend(zone_envelope)

    # Create result DataFrame and sort
    if envelope_rows:
        df_envelope = pd.DataFrame(envelope_rows)
        return df_envelope.sort_values(by=["zone", "result_type", "max_for_column"]).reset_index(drop=True)

    return pd.DataFrame()


def _extract_scia_1d_table_data(results: dict[str, Any], selected_table: str) -> dict[str, Any] | None:
    """
    Extract 1D forces data for a specific table from SCIA results.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param selected_table: Table name to extract
    :type selected_table: str
    :returns: 1D forces data or None
    :rtype: dict[str, Any] | None
    """
    # Read 1D forces data
    table_data = results.get("xml_parsing", {}).get("parsed_tables", {}).get(f"Interne 1D-krachten {selected_table}", {}).get("data", None)

    # If we found table data, try to extract the actual results
    if table_data and isinstance(table_data, dict):
        # Check if the data is under "Resultaten over integratiestroken:"
        integration_results = table_data.get("Resultaten over integratiestroken:")
        if integration_results:
            return integration_results

        # Otherwise return the data as-is
        return table_data

    return None


def _create_value_lookup_for_column(df: pd.DataFrame, column: str) -> dict[tuple, list[float]]:
    """
    Create value lookup dictionary for a specific column.

    Keys are (name, coords_xyz) tuples.

    :param df: DataFrame to process
    :type df: pd.DataFrame
    :param column: Column name to create lookup for
    :type column: str
    :returns: Value lookup dictionary with (name, coords_xyz) as keys
    :rtype: dict[tuple, list[float]]
    """
    value_lookup: dict[tuple, list[float]] = {}

    if df.empty or "coords_xyz" not in df.columns or column not in df.columns or "Naam" not in df.columns:
        return value_lookup

    for _, row in df.iterrows():
        coord = tuple(row["coords_xyz"]) if isinstance(row["coords_xyz"], list) else row["coords_xyz"]
        name = str(row["Naam"])
        key = (name, coord)

        if key not in value_lookup:
            value_lookup[key] = []
        try:
            val = pd.to_numeric(row[column], errors="coerce")
            if not pd.isna(val):
                value_lookup[key].append(val)
        except (ValueError, TypeError):
            pass

    return value_lookup


def _create_lookup_dictionaries(df: pd.DataFrame, columns: list[str]) -> tuple[dict[tuple, str], dict[str, dict[tuple, list[float]]]]:
    """
    Create lookup dictionaries for faster (name, coordinate)-based access.

    :param df: DataFrame to process
    :type df: pd.DataFrame
    :param columns: List of columns to create lookups for
    :type columns: list[str]
    :returns: Tuple of (empty_dict_for_compatibility, value_lookups)
    :rtype: tuple[dict[tuple, str], dict[str, dict[tuple, list[float]]]]
    """
    value_lookups = {}
    for column in columns:
        value_lookups[column] = _create_value_lookup_for_column(df, column)

    # Return empty dict for first element (was name_lookup, no longer needed but kept for compatibility)
    return {}, value_lookups


def process_scia_1d_results(results: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Process SCIA 1D force analysis results to create DataFrames with coordinate and force data.

    This function extracts 1D force data from SCIA results and processes coordinates,
    creating DataFrames with unique coordinate locations and their corresponding
    force/moment values for beam elements. The processing includes grouping rows
    with same 'Naam' and 'dx' values, merging 'Belasting' values, and finding
    absolute maximum values for force/moment columns.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Dictionary containing DataFrames for each 1D result table
    :rtype: dict[str, pd.DataFrame]
    """
    # Setting to read SCIA xml for 1D forces
    selected_result_tables = ["ULS", "SLS kar", "SLS freq"]
    selected_data_scia_1d = {}

    # Read the 1D force data from the "results" into a new dict
    for selected_table in selected_result_tables:
        data_1d = _extract_scia_1d_table_data(results, selected_table)
        selected_data_scia_1d[f"Interne 1D-krachten {selected_table}"] = data_1d

    # Create empty dict for storing results for each selected table
    results_1d = {}

    # Create DataFrames for each selected 1D result class table
    for selected_table in selected_result_tables:
        data_1d = selected_data_scia_1d.get(f"Interne 1D-krachten {selected_table}", None)

        # Convert 1D data to DataFrame
        df_1d = pd.DataFrame(data_1d) if data_1d is not None else pd.DataFrame()

        # Process the DataFrame with grouping and aggregation (similar to what was done in IDEA interface)
        if not df_1d.empty and data_1d is not None:
            df_1d = process_raw_integration_strip_data(data_1d)

        results_1d[selected_table] = df_1d

    return results_1d


def _process_selected_result_tables(results: dict[str, Any], selected_result_tables: list[str]) -> dict[str, Any]:
    """Process and merge SCIA table data for selected result tables."""
    selected_data_scia = {}

    # Read the selected data from the "results" into a new dict
    for selected_table in selected_result_tables:
        basis_data, elementaire_data = _extract_scia_table_data(results, selected_table)
        selected_data_scia[f"Interne 2D-krachten basis {selected_table}"] = basis_data
        selected_data_scia[f"Interne 2D-krachten elementair {selected_table}"] = elementaire_data

    # Merge x, y, z into coords_xyz for 2D force tables
    for key, data in selected_data_scia.items():
        if data is not None and isinstance(data, dict):
            selected_data_scia[key] = merge_xyz_to_coords_xyz(data)

    return selected_data_scia


def _populate_force_values_from_lookup(unique_coords_df: pd.DataFrame, lookup_dict: dict, column_name: str) -> None:
    """
    Populate force/moment values from lookup dictionary into dataframe.

    Lookup dictionary has (name, coords_xyz) as keys.

    :param unique_coords_df: DataFrame with 'name' and 'coords_xyz' columns
    :type unique_coords_df: pd.DataFrame
    :param lookup_dict: Lookup dictionary with (name, coords_xyz) keys
    :type lookup_dict: dict
    :param column_name: Column name to populate
    :type column_name: str
    """
    values = []
    for _, row in unique_coords_df.iterrows():
        name = row["name"]
        coord = row["coords_xyz"]
        coord_tuple = tuple(coord) if isinstance(coord, list) else coord
        key = (name, coord_tuple)

        coord_values = lookup_dict.get(key, [])
        if coord_values:
            # Find value with maximum absolute value
            max_abs_val = max(coord_values, key=abs)
            values.append(max_abs_val)
        else:
            values.append(float("nan"))
    unique_coords_df[column_name] = values


def _process_single_result_table(selected_data_scia: dict[str, Any], selected_table: str) -> pd.DataFrame:
    """
    Process a single result table and return the processed DataFrame.

    For regular 2D node results, groups by unique (name, coordinates) combinations.
    """
    elementaire_ontwerpgrootheden = selected_data_scia.get(f"Interne 2D-krachten elementair {selected_table}", None)
    basis_grootheden = selected_data_scia.get(f"Interne 2D-krachten basis {selected_table}", None)

    # Convert elementaire_ontwerpgrootheden and basis_grootheden to DataFrames
    df_elementaire = pd.DataFrame(elementaire_ontwerpgrootheden) if elementaire_ontwerpgrootheden is not None else pd.DataFrame()
    df_basis = pd.DataFrame(basis_grootheden) if basis_grootheden is not None else pd.DataFrame()

    # Create a DataFrame containing all unique (name, coords_xyz) combinations from both DataFrames
    unique_coords_df = get_unique_coords_xyz_dataframe(df_elementaire, df_basis)

    if unique_coords_df.empty:
        return unique_coords_df

    # Create lookup dictionaries for faster (name, coordinate)-based access
    _, elementaire_lookup = _create_lookup_dictionaries(df_elementaire, ["m_xD+", "m_xD-", "m_yD+", "m_yD-"])
    _, basis_lookup = _create_lookup_dictionaries(df_basis, ["v_x", "v_y"])

    # Populate force/moment values from basis lookup (shear forces)
    for orig_col in ["v_x", "v_y"]:
        if orig_col in basis_lookup:
            _populate_force_values_from_lookup(unique_coords_df, basis_lookup[orig_col], orig_col)

    # Populate force/moment values from elementaire lookup (moments)
    for orig_col in ["m_xD+", "m_xD-", "m_yD+", "m_yD-"]:
        if orig_col in elementaire_lookup:
            _populate_force_values_from_lookup(unique_coords_df, elementaire_lookup[orig_col], orig_col)

    return unique_coords_df


def process_scia_2d_results(results: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Process SCIA 2D force analysis results to create DataFrames with coordinate and force data.

    This function extracts 2D force and displacement data from SCIA results, processes coordinates,
    and creates DataFrames with unique coordinate locations and their corresponding
    maximum force/moment values for plate elements.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Dictionary containing DataFrames for each 2D result table
    :rtype: dict[str, pd.DataFrame]
    """
    # Setting to read SCIA xml for 2D forces
    selected_result_tables = ["ULS", "SLS kar", "SLS freq"]

    # Process selected result tables
    selected_data_scia = _process_selected_result_tables(results, selected_result_tables)

    # Create empty dict for storing results for each selected table
    results_2d = {}

    # Create DataFrames for each selected result class table
    for selected_table in selected_result_tables:
        results_2d[selected_table] = _process_single_result_table(selected_data_scia, selected_table)

    return results_2d


def get_processed_1d_data_for_idea(results: dict[str, Any], result_type: str) -> pd.DataFrame:
    """
    Get processed 1D SCIA data as a DataFrame for use in IDEA integration.

    This function extracts raw 1D data from SCIA results and processes it by:
    - Grouping rows with same 'Naam' and 'dx' values
    - Merging 'Belasting' values into single cells
    - Finding absolute maximum values for force/moment columns

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param result_type: Type of results to extract ("SLS kar", "SLS freq", "ULS")
    :type result_type: str
    :returns: Processed DataFrame with grouped and filtered 1D data
    :rtype: pd.DataFrame
    """
    try:
        # Map result types to table names (using exact table names from SCIA)
        table_mapping = {"SLS kar": "SLS kar", "SLS freq": "SLS freq", "ULS": "ULS"}

        selected_table = table_mapping.get(result_type, "SLS kar")

        # Extract raw 1D data directly from parsed tables
        xml_parsing = results.get("xml_parsing", {})
        parsed_tables = xml_parsing.get("parsed_tables", {})
        table_name = f"Interne 1D-krachten {selected_table}"
        table_data = parsed_tables.get(table_name, {}).get("data", {})

        # Look for integration results
        integration_results = table_data.get("Resultaten over integratiestroken:")
        if not integration_results or not isinstance(integration_results, dict):
            # If no integration results, check for other data structure
            if table_data:
                # Look for any other data structure that might contain the results
                for value in table_data.values():
                    if isinstance(value, dict) and len(value) > 0:
                        integration_results = value
                        break

            if not integration_results:
                return pd.DataFrame()

        # Process the raw data with grouping and filtering
        df_processed = process_raw_integration_strip_data(integration_results)

    except Exception:
        # Return empty DataFrame on any error
        return pd.DataFrame()
    else:
        return df_processed


def _extract_column_data(integration_results: dict[str, Any]) -> tuple[list[str], dict[str, list]]:
    """
    Extract available columns and column data from integration results.

    :param integration_results: Raw integration results from SCIA
    :type integration_results: dict[str, Any]
    :returns: Tuple of (available_columns, column_data)
    :rtype: tuple[list[str], dict[str, list]]
    """
    available_columns = []
    column_data = {}

    for key, value in integration_results.items():
        if isinstance(value, list) and len(value) > 0:
            available_columns.append(key)
            column_data[key] = value

    return available_columns, column_data


def _convert_numeric_columns(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Convert numeric columns to proper types.

    :param df_raw: Raw DataFrame
    :type df_raw: pd.DataFrame
    :returns: DataFrame with converted numeric columns
    :rtype: pd.DataFrame
    """
    numeric_columns = ["N", "V_y", "V_z", "M_x", "M_y", "M_z", "dx"]
    for col in numeric_columns:
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce").fillna(0)
    return df_raw


def _abs_max_aggregator(series: pd.Series) -> float:
    """Find the value with the maximum absolute value."""
    series_clean = series.dropna()
    if series_clean.empty:
        return 0
    # Find index of maximum absolute value
    abs_max_idx = series_clean.abs().idxmax()
    return series_clean.loc[abs_max_idx]


def _extract_coords_from_strip_name(name: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """
    Extract start and end coordinates from a SCIA integration strip name.

    Name format: strip_Z1_1_(0, 0.5, 0)_(15, 0.5, 0)
    Returns: ((0, 0.5, 0), (15, 0.5, 0))

    :param name: SCIA integration strip name containing coordinate information
    :type name: str
    :returns: Tuple of (start_coordinates, end_coordinates)
    :rtype: tuple[tuple[float, float, float], tuple[float, float, float]]
    """
    parts = name.split("_")
    start_str = parts[-2].strip("()")
    end_str = parts[-1].strip("()")

    start_coords_list = list(map(float, start_str.split(",")))
    end_coords_list = list(map(float, end_str.split(",")))

    # Ensure we have exactly 3 coordinates for each point
    if len(start_coords_list) >= 3 and len(end_coords_list) >= 3:
        start_coords = (start_coords_list[0], start_coords_list[1], start_coords_list[2])
        end_coords = (end_coords_list[0], end_coords_list[1], end_coords_list[2])
        return start_coords, end_coords
    return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)  # Default if not enough coordinates


def _calculate_normalized_direction_vector(
    coords_start: tuple[float, float, float], coords_end: tuple[float, float, float]
) -> tuple[float, float, float]:
    """
    Calculate normalized direction vector from start to end coordinates.

    This function computes the unit direction vector for a strip element, which is used
    to determine the local coordinate system of the integration strip.

    :param coords_start: Start coordinates (x, y, z)
    :type coords_start: tuple[float, float, float]
    :param coords_end: End coordinates (x, y, z)
    :type coords_end: tuple[float, float, float]
    :returns: Normalized direction vector (dx, dy, dz)
    :rtype: tuple[float, float, float]
    """
    # Calculate direction vector
    dx = coords_end[0] - coords_start[0]
    dy = coords_end[1] - coords_start[1]
    dz = coords_end[2] - coords_start[2]

    # Calculate magnitude
    magnitude = (dx**2 + dy**2 + dz**2) ** 0.5

    # Return normalized vector (avoid division by zero)
    if magnitude > 1e-10:  # Small tolerance for numerical precision
        return (dx / magnitude, dy / magnitude, dz / magnitude)
    return (0.0, 0.0, 0.0)  # Default to zero vector if zero-length vector


def _create_aggregation_functions(df_columns: list[str]) -> dict[str, Union[str, Callable[[pd.Series], Any]]]:
    """
    Create aggregation functions for DataFrame grouping.

    :param df_columns: List of DataFrame column names
    :type df_columns: list[str]
    :returns: Dictionary of aggregation functions
    :rtype: dict[str, Union[str, Callable[[pd.Series], Any]]]
    """
    numeric_columns = ["N", "V_y", "V_z", "M_x", "M_y", "M_z", "dx"]
    agg_functions: dict[str, Union[str, Callable[[pd.Series], Any]]] = {}

    for col in df_columns:
        if col == "Belasting":
            # Merge Belasting values into single cell (concatenate unique values)
            agg_functions[col] = lambda x: " | ".join(sorted(x.dropna().astype(str).unique()))
        elif col in numeric_columns and col not in ["Naam", "dx"]:
            # Find absolute maximum for force/moment columns
            agg_functions[col] = _abs_max_aggregator
        elif col in ["Naam", "dx"]:
            # Keep first value for grouping columns
            agg_functions[col] = "first"
        else:
            # For other columns, take first non-null value
            agg_functions[col] = lambda x: x.dropna().iloc[0] if not x.dropna().empty else ""

    return agg_functions


def process_raw_integration_strip_data(integration_results: dict[str, Any]) -> pd.DataFrame:
    """
    Process raw 1D SCIA integration strip data by grouping rows with same name and dx values.

    Groups rows by 'Naam' and 'dx', merges 'Belasting' values into single cells,
    and finds absolute maximum values for force/moment columns.

    :param integration_results: Raw integration results from SCIA
    :type integration_results: dict[str, Any]
    :returns: Processed DataFrame with grouped and filtered data
    :rtype: pd.DataFrame
    """
    # Extract available columns and data
    available_columns, column_data = _extract_column_data(integration_results)

    if not available_columns or not column_data:
        return pd.DataFrame()

    # Create DataFrame from raw data
    df_raw = pd.DataFrame(column_data)

    if df_raw.empty:
        return pd.DataFrame()

    # Convert numeric columns to proper types
    df_raw = _convert_numeric_columns(df_raw)

    # Group by 'Naam' and 'dx'
    if "Naam" not in df_raw.columns or "dx" not in df_raw.columns:
        return df_raw  # Return original if grouping columns don't exist

    # Define aggregation functions
    agg_functions = _create_aggregation_functions(df_raw.columns.tolist())

    # Apply grouping and aggregation
    df_processed = df_raw.groupby(["Naam", "dx"], as_index=False).agg(agg_functions)

    # Sort by Naam and dx for consistent ordering
    df_processed.sort_values(["Naam", "dx"]).reset_index(drop=True)

    # Create two new columns that contains the start and end coordinates as tuples extracted from the 'Naam' column
    # Name = strip_Z1_1_(0, 0.5, 0)_(15, 0.5, 0) -> coords_start = (0, 0.5, 0) and coords_end = (15, 0.5, 0)
    df_processed["coords_start"], df_processed["coords_end"] = zip(*df_processed["Naam"].apply(_extract_coords_from_strip_name))

    # Based on the extracted start and end coordinates, create a new column containing a normalized direction vector (dx, dy, dz)
    # we will use to later determine the local axis system of the strip
    df_processed["direction_vector"] = df_processed.apply(
        lambda row: _calculate_normalized_direction_vector(row["coords_start"], row["coords_end"]), axis=1
    )

    return df_processed


# Simple cache for processed results to avoid reprocessing the same data
@functools.lru_cache(maxsize=32)
def _cached_process_scia_results(_results_hash: int) -> dict[str, pd.DataFrame] | None:
    """
    Cached wrapper for process_scia_node_results_for_idea.

    :param _results_hash: Hash of the results dictionary for caching
    :type _results_hash: int
    :returns: Processed results or None if failed
    :rtype: dict[str, pd.DataFrame] | None
    """
    # This is just the cache wrapper - actual processing happens in the calling function
    return None


def _get_results_hash(results: dict[str, Any]) -> int:
    """
    Create a simple hash of the results dictionary for caching.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Hash value for caching
    :rtype: int
    """
    # Create a simple hash based on the structure and some key values
    try:
        # Hash based on available table keys and some sample data
        xml_parsing = results.get("xml_parsing", {})
        parsed_tables = xml_parsing.get("parsed_tables", {})

        # Create a signature from table names and basic structure
        table_names = sorted(parsed_tables.keys())
        signature = str(table_names)

        # Add some sample data if available
        for table_name in table_names[:3]:  # Only check first 3 tables to avoid excessive computation
            table_data = parsed_tables.get(table_name, {})
            if isinstance(table_data, dict):
                signature += str(len(str(table_data)[:100]))  # Add length of first 100 chars

        return hash(signature)
    except Exception:
        # Fallback to a simple hash if anything goes wrong
        return hash(str(results)[:200])


def _extract_integration_strip_results(results: dict[str, Any], result_type: str) -> dict[str, Any] | None:
    """
    Extract integration strip results from SCIA results.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param result_type: Type of results to extract
    :type result_type: str
    :returns: Integration strip results or None if not found
    :rtype: dict[str, Any] | None
    """
    # Map result types to table names (using exact table names from SCIA)
    table_mapping = {"SLS kar": "SLS kar", "SLS freq": "SLS freq", "ULS": "ULS"}
    selected_table = table_mapping.get(result_type, "SLS kar")

    # Extract raw 1D data directly from parsed tables
    xml_parsing = results.get("xml_parsing", {})
    parsed_tables = xml_parsing.get("parsed_tables", {})
    table_name = f"Interne 1D-krachten {selected_table}"
    table_data = parsed_tables.get(table_name, {}).get("data", {})

    # Look for integration strip results
    integration_strip_results = table_data.get("Resultaten over integratiestroken:")
    if (not integration_strip_results or not isinstance(integration_strip_results, dict)) and table_data:
        # If no integration strip results, check for other data structure
        # Look for any other data structure that might contain the results
        for value in table_data.values():
            if isinstance(value, dict) and len(value) > 0:
                integration_strip_results = value
                break

    return integration_strip_results


# Module-level cache for processed results
_processed_results_cache: dict[int, dict[str, pd.DataFrame]] = {}


def get_processed_results_with_cache(results: dict[str, Any]) -> dict[str, pd.DataFrame] | None:
    """
    Get processed SCIA 2D node results with caching to avoid reprocessing.

    Note: This function now uses the direct 2D processing instead of the removed
    process_scia_node_results_for_idea function.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Processed results or None if failed
    :rtype: dict[str, pd.DataFrame] | None
    """
    # Use simple caching to avoid reprocessing the same results
    try:
        results_hash = _get_results_hash(results)
    except Exception:
        return None

    if results_hash in _processed_results_cache:
        return _processed_results_cache[results_hash]

    try:
        # Use the direct 2D processing function
        processed_results = process_scia_2d_results(results)

        # Cache the results (limit cache size to prevent memory issues)
        if len(_processed_results_cache) > 10:
            # Remove oldest entry
            oldest_key = next(iter(_processed_results_cache))
            del _processed_results_cache[oldest_key]
        _processed_results_cache[results_hash] = processed_results
    except Exception:
        return None
    else:
        return processed_results


# Module-level cache for integration strip results
_integration_strip_results_cache: dict[int, dict[str, pd.DataFrame]] = {}


def get_processed_integration_strip_results_with_cache(results: dict[str, Any]) -> dict[str, pd.DataFrame] | None:
    """
    Get processed SCIA integration strip (1D) results with caching to avoid reprocessing.

    Note: This function now uses the direct 1D processing instead of the removed
    process_scia_integration_strip_results_for_idea function.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Processed integration strip results or None if failed
    :rtype: dict[str, pd.DataFrame] | None
    """
    # Use simple caching to avoid reprocessing the same results
    try:
        results_hash = _get_results_hash(results)
    except Exception:
        return None

    if results_hash in _integration_strip_results_cache:
        return _integration_strip_results_cache[results_hash]

    try:
        # Use the direct 1D processing function
        processed_results = process_scia_1d_results(results)

        # Cache the results (limit cache size to prevent memory issues)
        if len(_integration_strip_results_cache) > 10:
            # Remove oldest entry
            oldest_key = next(iter(_integration_strip_results_cache))
            del _integration_strip_results_cache[oldest_key]
        _integration_strip_results_cache[results_hash] = processed_results
    except Exception:
        return None
    else:
        return processed_results
        return processed_results
