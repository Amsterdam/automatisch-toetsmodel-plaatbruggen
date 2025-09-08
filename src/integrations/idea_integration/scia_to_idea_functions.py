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
        coords_value = tuple(coords_value)

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
        coords_value = tuple(coords_value)

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


def process_scia_results_for_idea(results: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Process SCIA analysis results to create a DataFrame suitable for IDEA StatiCa integration.

    This function extracts force and displacement data from SCIA results, processes coordinates,
    and creates a comprehensive DataFrame with unique coordinate locations and their corresponding
    maximum force/moment values.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: DataFrame containing unique coordinates with force results
    :rtype: pd.DataFrame
    """
    # Setting to read SCIA xml
    selected_result_tables = ["ULS", "SLS kar", "SLS freq"]
    selected_data_scia = {}

    # Read the selected data from the "results" into a new dict
    for selected_table in selected_result_tables:
        # Read "basis grootheden"
        selected_data_scia[f"Interne 2D-krachten basis {selected_table}"] = (
            results.get("xml_parsing", {})
            .get("parsed_tables", {})
            .get(f"Interne 2D-krachten basis {selected_table}", {})
            .get("data", {})
            .get("Basis grootheden", None)
        )
        # Read "elementaire ontwerpgrootheden"
        selected_data_scia[f"Interne 2D-krachten elementair {selected_table}"] = (
            results.get("xml_parsing", {})
            .get("parsed_tables", {})
            .get(f"Interne 2D-krachten elementair {selected_table}", {})
            .get("data", {})
            .get("Elementaire ontwerpgrootheden", None)
        )

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

        # Optimize by creating lookup dictionaries instead of using apply() with repeated DataFrame searches
        # Create lookup dictionaries for faster coordinate-based access
        elementaire_name_lookup = {}
        elementaire_lookup = {}
        if not df_elementaire.empty and "coords_xyz" in df_elementaire.columns:
            # Create name lookup
            if "Naam" in df_elementaire.columns:
                for _, row in df_elementaire.iterrows():
                    coord = tuple(row["coords_xyz"]) if isinstance(row["coords_xyz"], list) else row["coords_xyz"]
                    if coord not in elementaire_name_lookup:
                        elementaire_name_lookup[coord] = str(row["Naam"])

            # Create value lookups for moment columns
            for col in ["m_xD+", "m_xD-", "m_yD+", "m_yD-"]:
                if col in df_elementaire.columns:
                    elementaire_lookup[col] = {}
                    for _, row in df_elementaire.iterrows():
                        coord = tuple(row["coords_xyz"]) if isinstance(row["coords_xyz"], list) else row["coords_xyz"]
                        if coord not in elementaire_lookup[col]:
                            elementaire_lookup[col][coord] = []
                        try:
                            val = pd.to_numeric(row[col], errors="coerce")
                            if not pd.isna(val):
                                elementaire_lookup[col][coord].append(val)
                        except (ValueError, TypeError):
                            pass

        basis_name_lookup = {}
        basis_lookup = {}
        if not df_basis.empty and "coords_xyz" in df_basis.columns:
            # Create name lookup
            if "Naam" in df_basis.columns:
                for _, row in df_basis.iterrows():
                    coord = tuple(row["coords_xyz"]) if isinstance(row["coords_xyz"], list) else row["coords_xyz"]
                    if coord not in basis_name_lookup:
                        basis_name_lookup[coord] = str(row["Naam"])

            # Create value lookups for shear columns
            for col in ["v_x", "v_y"]:
                if col in df_basis.columns:
                    basis_lookup[col] = {}
                    for _, row in df_basis.iterrows():
                        coord = tuple(row["coords_xyz"]) if isinstance(row["coords_xyz"], list) else row["coords_xyz"]
                        if coord not in basis_lookup[col]:
                            basis_lookup[col][coord] = []
                        try:
                            val = pd.to_numeric(row[col], errors="coerce")
                            if not pd.isna(val):
                                basis_lookup[col][coord].append(val)
                        except (ValueError, TypeError):
                            pass

        # Now populate the DataFrame efficiently using vectorized operations
        coords_list = unique_coords_df["coords_xyz"].tolist()

        # Populate names
        names = []
        for coord in coords_list:
            coord_tuple = tuple(coord) if isinstance(coord, list) else coord
            name = elementaire_name_lookup.get(coord_tuple) or basis_name_lookup.get(coord_tuple, "zone name not found")
            names.append(name)
        unique_coords_df["name"] = names

        # Populate force/moment values
        for col_name, lookup_dict in [("v_x_max", basis_lookup.get("v_x", {})), ("v_y_max", basis_lookup.get("v_y", {}))]:
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

        # Store unique results in the dictionary
        unique_results[selected_table] = unique_coords_df

    return unique_results
