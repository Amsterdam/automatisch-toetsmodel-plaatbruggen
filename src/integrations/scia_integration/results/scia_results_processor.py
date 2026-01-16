"""
Core functions for processing SCIA analysis results data.

This module provides utilities to extract and process SCIA analysis results including:
- 2D force tables (basis and elementaire ontwerpgrootheden)
- 1D force tables (integration strips)
"""

import functools
from typing import Any

import pandas as pd


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


def get_max_abs_for_column(coords_value: tuple[float, float, float] | list[float], df: pd.DataFrame, col: str) -> float | str:
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
    :returns: Original value that has maximum absolute value, or "N/A" if not found or not numeric
    :rtype: float | str
    """
    if "coords_xyz" not in df.columns or col not in df.columns:
        return "N/A"

    # Convert coords_value to tuple for consistent comparison
    if isinstance(coords_value, list):
        coords_value = tuple(coords_value)  # type: ignore[assignment]

    # Use direct equality comparison which is much faster than string conversion
    matches = df[df["coords_xyz"] == coords_value]

    if matches.empty:
        return "N/A"

    # Convert to numeric, handling any non-numeric values as NaN, then find the value with maximum absolute value
    numeric_values = pd.to_numeric(matches[col], errors="coerce")
    if numeric_values.isna().all():
        return "N/A"
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
            values.append("N/A")
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
        df_table = _process_single_result_table(selected_data_scia, selected_table)
        # Fill any remaining NaN values with "N/A"
        if not df_table.empty:
            df_table = df_table.fillna("N/A")
        results_2d[selected_table] = df_table

    return results_2d


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
