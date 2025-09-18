"""Functions for processing SCIA results data for IDEA StatiCa integration."""

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
    table_data = (
        results.get("xml_parsing", {})
        .get("parsed_tables", {})
        .get(f"Interne 1D-krachten {selected_table}", {})
        .get("data", None)
    )
    
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


def _populate_dataframe_from_lookups(
    unique_coords_df: pd.DataFrame,
    elementaire_name_lookup: dict[tuple, str],
    basis_name_lookup: dict[tuple, str],
    elementaire_lookup: dict[str, dict[tuple, list[float]]],
    basis_lookup: dict[str, dict[tuple, list[float]]],
) -> pd.DataFrame:
    """
    Populate DataFrame with values from lookup dictionaries.

    :param unique_coords_df: DataFrame with unique coordinates
    :type unique_coords_df: pd.DataFrame
    :param elementaire_name_lookup: Name lookup for elementaire data
    :type elementaire_name_lookup: dict[tuple, str]
    :param basis_name_lookup: Name lookup for basis data
    :type basis_name_lookup: dict[tuple, str]
    :param elementaire_lookup: Value lookups for elementaire data
    :type elementaire_lookup: dict[str, dict[tuple, list[float]]]
    :param basis_lookup: Value lookups for basis data
    :type basis_lookup: dict[str, dict[tuple, list[float]]]
    :returns: Populated DataFrame
    :rtype: pd.DataFrame
    """
    coords_list = unique_coords_df["coords_xyz"].tolist()

    # Populate names
    names = []
    for coord in coords_list:
        coord_tuple = tuple(coord) if isinstance(coord, list) else coord
        name = elementaire_name_lookup.get(coord_tuple) or basis_name_lookup.get(coord_tuple, "zone name not found")
        names.append(name)
    unique_coords_df["name"] = names

    # Populate force/moment values from basis lookup (shear forces)
    for col_name, orig_col in [("v_x_max", "v_x"), ("v_y_max", "v_y")]:
        lookup_dict = basis_lookup.get(orig_col, {})
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
        unique_coords_df[col_name] = values

    # Populate force/moment values from elementaire lookup (moments)
    for col_name, orig_col in [("m_xD+_max", "m_xD+"), ("m_xD-_max", "m_xD-"), ("m_yD+_max", "m_yD+"), ("m_yD-_max", "m_yD-")]:
        lookup_dict = elementaire_lookup.get(orig_col, {})
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
        unique_coords_df[col_name] = values

    return unique_coords_df


def _populate_1d_dataframe_from_lookup(
    unique_coords_df: pd.DataFrame,
    name_lookup: dict[tuple, str],
    data_lookup: dict[str, dict[tuple, list[float]]],
) -> pd.DataFrame:
    """
    Populate DataFrame with 1D force values from lookup dictionaries.

    :param unique_coords_df: DataFrame with unique coordinates
    :type unique_coords_df: pd.DataFrame
    :param name_lookup: Name lookup for data
    :type name_lookup: dict[tuple, str]
    :param data_lookup: Value lookups for 1D force data
    :type data_lookup: dict[str, dict[tuple, list[float]]]
    :returns: Populated DataFrame
    :rtype: pd.DataFrame
    """
    coords_list = unique_coords_df["coords_xyz"].tolist()
    print(f"DEBUG: _populate_1d_dataframe_from_lookup received {len(coords_list)} coordinates")  # noqa: T201
    print(f"DEBUG: Sample coordinates: {coords_list[:3] if coords_list else 'None'}")  # noqa: T201

    # Populate names
    names = []
    for coord in coords_list:
        coord_tuple = tuple(coord) if isinstance(coord, list) else coord
        name = name_lookup.get(coord_tuple, "zone name not found")
        names.append(name)
    unique_coords_df["name"] = names
    print(f"DEBUG: Populated {len(names)} names, sample: {names[:3] if names else 'None'}")  # noqa: T201

    # Populate 1D force values (normal force, shear forces, bending moments)
    force_columns = [
        ("n_max", "N"),        # Normal force
        ("v_y_max", "V_y"),    # Shear force Y
        ("v_z_max", "V_z"),    # Shear force Z
        ("m_y_max", "M_y"),    # Bending moment Y
        ("m_z_max", "M_z"),    # Bending moment Z
        ("m_x_max", "M_x"),    # Torsional moment X
    ]

    for col_name, orig_col in force_columns:
        lookup_dict = data_lookup.get(orig_col, {})
        print(f"DEBUG: Processing column {col_name} (from {orig_col}), lookup_dict has {len(lookup_dict)} entries")  # noqa: T201
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
        unique_coords_df[col_name] = values
        print(f"DEBUG: Populated {col_name} with {len([v for v in values if not pd.isna(v)])} non-NaN values out of {len(values)}")  # noqa: T201

    return unique_coords_df


def process_scia_results_for_idea(results: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Process SCIA analysis results to create a DataFrame suitable for IDEA StatiCa integration.

    This function extracts force and displacement data from SCIA results, processes coordinates,
    and creates a comprehensive DataFrame with unique coordinate locations and their corresponding
    maximum force/moment values.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Dictionary containing DataFrames for each result table
    :rtype: dict[str, pd.DataFrame]
    """
    # Setting to read SCIA xml
    selected_result_tables = ["ULS", "SLS kar", "SLS freq"]
    selected_data_scia = {}

    # Read the selected data from the "results" into a new dict
    for selected_table in selected_result_tables:
        basis_data, elementaire_data = _extract_scia_table_data(results, selected_table)
        selected_data_scia[f"Interne 2D-krachten basis {selected_table}"] = basis_data
        selected_data_scia[f"Interne 2D-krachten elementair {selected_table}"] = elementaire_data

    # Merge x, y, z into coords_xyz for both elementaire_ontwerpgrootheden and basis_grootheden tables
    for key, data in selected_data_scia.items():
        if data is not None and isinstance(data, dict):
            selected_data_scia[key] = merge_xyz_to_coords_xyz(data)

    # Create empty dict for storing unique results on coords_xyz for each selected table
    unique_results = {}

    # Create DataFrames for each selected result class table
    for selected_table in selected_result_tables:
        elementaire_ontwerpgrootheden = selected_data_scia.get(f"Interne 2D-krachten elementair {selected_table}", None)
        basis_grootheden = selected_data_scia.get(f"Interne 2D-krachten basis {selected_table}", None)

        # Convert elementaire_ontwerpgrootheden and basis_grootheden to DataFrames
        df_elementaire = pd.DataFrame(elementaire_ontwerpgrootheden) if elementaire_ontwerpgrootheden is not None else pd.DataFrame()
        df_basis = pd.DataFrame(basis_grootheden) if basis_grootheden is not None else pd.DataFrame()

        # Create a DataFrame containing all unique values from the 'coords_xyz' column in both DataFrames
        unique_coords_df = get_unique_coords_xyz_dataframe(df_elementaire, df_basis)

        if unique_coords_df.empty:
            unique_results[selected_table] = unique_coords_df
            continue

        # Create lookup dictionaries for faster coordinate-based access
        elementaire_name_lookup, elementaire_lookup = _create_lookup_dictionaries(df_elementaire, ["m_xD+", "m_xD-", "m_yD+", "m_yD-"])
        basis_name_lookup, basis_lookup = _create_lookup_dictionaries(df_basis, ["v_x", "v_y"])

        # Populate the DataFrame efficiently using the lookup dictionaries
        unique_coords_df = _populate_dataframe_from_lookups(
            unique_coords_df, elementaire_name_lookup, basis_name_lookup, elementaire_lookup, basis_lookup
        )

        # Store unique results in the dictionary
        unique_results[selected_table] = unique_coords_df

    return unique_results


def process_scia_1d_results_for_idea(results: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Process SCIA 1D force analysis results to create DataFrames suitable for IDEA StatiCa integration.

    This function extracts 1D force data from SCIA results, processes coordinates,
    and creates comprehensive DataFrames with unique coordinate locations and their corresponding
    maximum force/moment values for beam elements.

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
        print(f"DEBUG: 1D data for {selected_table}: {type(data_1d)} with keys {list(data_1d.keys()) if isinstance(data_1d, dict) else 'Not a dict'}")  # noqa: T201
        selected_data_scia_1d[f"Interne 1D-krachten {selected_table}"] = data_1d

    # Merge x, y, z into coords_xyz for 1D force tables
    for key, data in selected_data_scia_1d.items():
        if data is not None and isinstance(data, dict):
            selected_data_scia_1d[key] = merge_xyz_to_coords_xyz(data)

    # Create empty dict for storing unique results on coords_xyz for each selected table
    unique_results_1d = {}

    # Create DataFrames for each selected 1D result class table
    for selected_table in selected_result_tables:
        data_1d = selected_data_scia_1d.get(f"Interne 1D-krachten {selected_table}", None)
        print(f"DEBUG: Raw data_1d for {selected_table}: {type(data_1d)}")  # noqa: T201
        if isinstance(data_1d, dict) and data_1d:
            print(f"DEBUG: data_1d keys: {list(data_1d.keys())}")  # noqa: T201
            print(f"DEBUG: Sample data_1d entries: {dict(list(data_1d.items())[:3])}")  # noqa: T201

        # Convert 1D data to DataFrame
        df_1d = pd.DataFrame(data_1d) if data_1d is not None else pd.DataFrame()
        print(f"DEBUG: DataFrame for {selected_table}: shape = {df_1d.shape}, columns = {list(df_1d.columns) if not df_1d.empty else 'Empty'}")  # noqa: T201

        if df_1d.empty:
            unique_results_1d[selected_table] = df_1d
            continue

        # Create a DataFrame containing all unique values from the 'coords_xyz' column
        if "coords_xyz" in df_1d.columns:
            unique_coords = df_1d["coords_xyz"].drop_duplicates().tolist()
            unique_coords_df = pd.DataFrame({"coords_xyz": unique_coords})
            print(f"DEBUG: Created unique_coords_df with {len(unique_coords)} unique coordinates for {selected_table}")  # noqa: T201
        else:
            print(f"DEBUG: No 'coords_xyz' column found in DataFrame for {selected_table}")  # noqa: T201
            unique_coords_df = pd.DataFrame()

        if unique_coords_df.empty:
            unique_results_1d[selected_table] = unique_coords_df
            continue

        # Create lookup dictionaries for faster coordinate-based access for 1D forces
        # 1D beam forces include: normal force (N), shear forces (V_y, V_z), moments (M_x, M_y, M_z)
        name_lookup, data_lookup = _create_lookup_dictionaries(df_1d, ["N", "V_y", "V_z", "M_x", "M_y", "M_z"])
        print(f"DEBUG: name_lookup has {len(name_lookup)} entries for {selected_table}")  # noqa: T201
        print(f"DEBUG: data_lookup keys: {list(data_lookup.keys())} for {selected_table}")  # noqa: T201
        print(f"DEBUG: Sample name_lookup entries: {dict(list(name_lookup.items())[:3])}")  # noqa: T201
        print(f"DEBUG: Sample data_lookup entries for N: {dict(list(data_lookup.get('N', {}).items())[:3])}")  # noqa: T201

        # Populate the DataFrame efficiently using the lookup dictionaries
        unique_coords_df = _populate_1d_dataframe_from_lookup(unique_coords_df, name_lookup, data_lookup)
        print(f"DEBUG: Final DataFrame for {selected_table}: shape = {unique_coords_df.shape}, columns = {list(unique_coords_df.columns)}")  # noqa: T201

        # Store unique results in the dictionary
        unique_results_1d[selected_table] = unique_coords_df

    print(f"DEBUG: Final unique_results_1d keys: {list(unique_results_1d.keys())}")  # noqa: T201
    return unique_results_1d
