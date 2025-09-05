"""
Functions for processing SCIA results data for IDEA StatiCa integration.
"""
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


def get_name_for_coords(coords_value: Any, df_elementaire: pd.DataFrame, df_basis: pd.DataFrame) -> str:
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
    # Try to find the name in df_elementaire first
    if "coords_xyz" in df_elementaire.columns and "Naam" in df_elementaire.columns:
        # Use string comparison for more reliable matching
        coords_str = str(coords_value)
        elementaire_matches = df_elementaire[df_elementaire["coords_xyz"].astype(str) == coords_str]
        if not elementaire_matches.empty:
            return str(elementaire_matches.iloc[0]["Naam"])
    
    # If not found, try df_basis
    elif "coords_xyz" in df_basis.columns and "Naam" in df_basis.columns:
        coords_str = str(coords_value)
        basis_matches = df_basis[df_basis["coords_xyz"].astype(str) == coords_str]
        if not basis_matches.empty:
            return str(basis_matches.iloc[0]["Naam"])
    else:
        return "zone name not found"


def get_max_abs_for_column(coords_value: Any, df: pd.DataFrame, col: str) -> float:
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
    
    # Use string comparison for more reliable matching
    coords_str = str(coords_value)
    matches = df[df["coords_xyz"].astype(str) == coords_str]
    
    if matches.empty:
        return float("nan")
    
    # Convert to numeric, handling any non-numeric values as NaN, then find the value with maximum absolute value
    numeric_values = pd.to_numeric(matches[col], errors='coerce')
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

        # Add a 'name' column to unique_coords_df by matching 'coords_xyz' in df_elementaire and df_basis
        unique_coords_df["name"] = unique_coords_df["coords_xyz"].apply(lambda c: get_name_for_coords(c, df_elementaire, df_basis))

        # Add v_x_max and v_y_max columns to unique_coords_df by matching coords_xyz in df_basis
        unique_coords_df["v_x_max"] = unique_coords_df["coords_xyz"].apply(lambda c: get_max_abs_for_column(c, df_basis, "v_x"))
        unique_coords_df["v_y_max"] = unique_coords_df["coords_xyz"].apply(lambda c: get_max_abs_for_column(c, df_basis, "v_y"))

        # Add m_xD+, m_xD-, m_yD+, m_yD- columns to unique_coords_df by matching coords_xyz in df_elementaire
        unique_coords_df["m_xD+_max"] = unique_coords_df["coords_xyz"].apply(lambda c: get_max_abs_for_column(c, df_elementaire, "m_xD+"))
        unique_coords_df["m_xD-_max"] = unique_coords_df["coords_xyz"].apply(lambda c: get_max_abs_for_column(c, df_elementaire, "m_xD-"))
        unique_coords_df["m_yD+_max"] = unique_coords_df["coords_xyz"].apply(lambda c: get_max_abs_for_column(c, df_elementaire, "m_yD+"))
        unique_coords_df["m_yD-_max"] = unique_coords_df["coords_xyz"].apply(lambda c: get_max_abs_for_column(c, df_elementaire, "m_yD-"))

        # Store unique results in the dictionary
        unique_results[selected_table] = unique_coords_df

    return unique_results