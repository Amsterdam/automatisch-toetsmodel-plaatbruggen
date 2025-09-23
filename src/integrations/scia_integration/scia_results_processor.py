"""Core functions for processing SCIA analysis results data."""

import functools
from typing import Any, Callable, Union

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
    Returns a DataFrame with all unique values from the 'coords_xyz' column
    in both input DataFrames, ensuring no duplicates.

    :param df1: First DataFrame (e.g., df_elementaire)
    :type df1: pd.DataFrame
    :param df2: Second DataFrame (e.g., df_basis)
    :type df2: pd.DataFrame
    :returns: DataFrame with unique 'coords_xyz' values (no duplicates)
    :rtype: pd.DataFrame
    """
    # Get coordinates from both DataFrames
    coords1 = df1["coords_xyz"].dropna() if "coords_xyz" in df1.columns else pd.Series([], dtype=object)
    coords2 = df2["coords_xyz"].dropna() if "coords_xyz" in df2.columns else pd.Series([], dtype=object)

    # Combine all coordinates
    all_coords = pd.concat([coords1, coords2], ignore_index=True)

    # Remove duplicates by converting tuples to strings for comparison, then back to tuples
    unique_coords_set = set()
    unique_coords_list = []

    for coord in all_coords:
        coord_str = str(coord)
        if coord_str not in unique_coords_set:
            unique_coords_set.add(coord_str)
            unique_coords_list.append(coord)

    return pd.DataFrame({"coords_xyz": unique_coords_list})


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
        .get("Basis grootheden", None)
    )

    # Read "elementaire ontwerpgrootheden"
    elementaire_data = (
        results.get("xml_parsing", {})
        .get("parsed_tables", {})
        .get(f"Interne 2D-krachten elementair {selected_table}", {})
        .get("data", {})
        .get("Elementaire ontwerpgrootheden", None)
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


def _create_name_lookup(df: pd.DataFrame) -> dict[tuple, str]:
    """
    Create name lookup dictionary from DataFrame.

    :param df: DataFrame to process
    :type df: pd.DataFrame
    :returns: Name lookup dictionary
    :rtype: dict[tuple, str]
    """
    name_lookup: dict[tuple, str] = {}

    if df.empty or "coords_xyz" not in df.columns or "Naam" not in df.columns:
        return name_lookup

    for _, row in df.iterrows():
        coord = tuple(row["coords_xyz"]) if isinstance(row["coords_xyz"], list) else row["coords_xyz"]
        if coord not in name_lookup:
            name_lookup[coord] = str(row["Naam"])

    return name_lookup


def _create_value_lookup_for_column(df: pd.DataFrame, column: str) -> dict[tuple, list[float]]:
    """
    Create value lookup dictionary for a specific column.

    :param df: DataFrame to process
    :type df: pd.DataFrame
    :param column: Column name to create lookup for
    :type column: str
    :returns: Value lookup dictionary
    :rtype: dict[tuple, list[float]]
    """
    value_lookup: dict[tuple, list[float]] = {}

    if df.empty or "coords_xyz" not in df.columns or column not in df.columns:
        return value_lookup

    for _, row in df.iterrows():
        coord = tuple(row["coords_xyz"]) if isinstance(row["coords_xyz"], list) else row["coords_xyz"]
        if coord not in value_lookup:
            value_lookup[coord] = []
        try:
            val = pd.to_numeric(row[column], errors="coerce")
            if not pd.isna(val):
                value_lookup[coord].append(val)
        except (ValueError, TypeError):
            pass

    return value_lookup


def _create_lookup_dictionaries(df: pd.DataFrame, columns: list[str]) -> tuple[dict[tuple, str], dict[str, dict[tuple, list[float]]]]:
    """
    Create lookup dictionaries for faster coordinate-based access.

    :param df: DataFrame to process
    :type df: pd.DataFrame
    :param columns: List of columns to create lookups for
    :type columns: list[str]
    :returns: Tuple of (name_lookup, value_lookups)
    :rtype: tuple[dict[tuple, str], dict[str, dict[tuple, list[float]]]]
    """
    name_lookup = _create_name_lookup(df)

    value_lookups = {}
    for column in columns:
        value_lookups[column] = _create_value_lookup_for_column(df, column)

    return name_lookup, value_lookups


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


def _populate_coordinate_names(unique_coords_df: pd.DataFrame, elementaire_name_lookup: dict, basis_name_lookup: dict) -> None:
    """Populate coordinate names in the dataframe."""
    coords_list = unique_coords_df["coords_xyz"].tolist()
    names = []
    for coord in coords_list:
        coord_tuple = tuple(coord) if isinstance(coord, list) else coord
        name = elementaire_name_lookup.get(coord_tuple) or basis_name_lookup.get(coord_tuple, "zone name not found")
        names.append(name)
    unique_coords_df["name"] = names


def _populate_force_values_from_lookup(unique_coords_df: pd.DataFrame, coords_list: list, lookup_dict: dict, column_name: str) -> None:
    """Populate force/moment values from lookup dictionary into dataframe."""
    values = []
    for coord in coords_list:
        coord_tuple = tuple(coord) if isinstance(coord, list) else coord
        coord_values = lookup_dict.get(coord_tuple, [])
        if coord_values:
            # Find value with maximum absolute value
            max_abs_val = max(coord_values, key=abs)
            values.append(max_abs_val)
        else:
            values.append(float("nan"))
    unique_coords_df[column_name] = values


def _process_single_result_table(selected_data_scia: dict[str, Any], selected_table: str) -> pd.DataFrame:
    """Process a single result table and return the processed DataFrame."""
    elementaire_ontwerpgrootheden = selected_data_scia.get(f"Interne 2D-krachten elementair {selected_table}", None)
    basis_grootheden = selected_data_scia.get(f"Interne 2D-krachten basis {selected_table}", None)

    # Convert elementaire_ontwerpgrootheden and basis_grootheden to DataFrames
    df_elementaire = pd.DataFrame(elementaire_ontwerpgrootheden) if elementaire_ontwerpgrootheden is not None else pd.DataFrame()
    df_basis = pd.DataFrame(basis_grootheden) if basis_grootheden is not None else pd.DataFrame()

    # Create a DataFrame containing all unique values from the 'coords_xyz' column in both DataFrames
    unique_coords_df = get_unique_coords_xyz_dataframe(df_elementaire, df_basis)

    if unique_coords_df.empty:
        return unique_coords_df

    # Create lookup dictionaries for faster coordinate-based access
    elementaire_name_lookup, elementaire_lookup = _create_lookup_dictionaries(df_elementaire, ["m_xD+", "m_xD-", "m_yD+", "m_yD-"])
    basis_name_lookup, basis_lookup = _create_lookup_dictionaries(df_basis, ["v_x", "v_y"])

    # Populate names
    _populate_coordinate_names(unique_coords_df, elementaire_name_lookup, basis_name_lookup)

    coords_list = unique_coords_df["coords_xyz"].tolist()

    # Populate force/moment values from basis lookup (shear forces)
    for orig_col in ["v_x", "v_y"]:
        if orig_col in basis_lookup:
            _populate_force_values_from_lookup(unique_coords_df, coords_list, basis_lookup[orig_col], orig_col)

    # Populate force/moment values from elementaire lookup (moments)
    for orig_col in ["m_xD+", "m_xD-", "m_yD+", "m_yD-"]:
        if orig_col in elementaire_lookup:
            _populate_force_values_from_lookup(unique_coords_df, coords_list, elementaire_lookup[orig_col], orig_col)

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
    return df_processed.sort_values(["Naam", "dx"]).reset_index(drop=True)


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
    Get processed SCIA results with caching to avoid reprocessing.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Processed results or None if failed
    :rtype: dict[str, pd.DataFrame] | None
    """
    # Import here to avoid circular imports
    from src.integrations.idea_integration.scia_to_idea_functions import process_scia_node_results_for_idea

    # Use simple caching to avoid reprocessing the same results
    try:
        results_hash = _get_results_hash(results)
    except Exception:
        return None

    if results_hash in _processed_results_cache:
        return _processed_results_cache[results_hash]

    try:
        processed_results = process_scia_node_results_for_idea(results)

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
    Get processed SCIA integration strip results with caching to avoid reprocessing.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Processed integration strip results or None if failed
    :rtype: dict[str, pd.DataFrame] | None
    """
    # Import here to avoid circular imports
    from src.integrations.idea_integration.scia_to_idea_functions import process_scia_integration_strip_results_for_idea

    # Use simple caching to avoid reprocessing the same results
    try:
        results_hash = _get_results_hash(results)
    except Exception:
        return None

    if results_hash in _integration_strip_results_cache:
        return _integration_strip_results_cache[results_hash]

    try:
        processed_results = process_scia_integration_strip_results_for_idea(results)

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
