"""Functions for creating SCIA result views for VIKTOR tables."""

from typing import Any

import pandas as pd
from viktor.views import TableResult

from .scia_results_processor import (
    get_processed_integration_strip_results_with_cache,
    get_processed_results_with_cache,
)


def safe_float_format(value: str | float, unit: str = "", default: str = "N/A") -> str:
    """
    Safely format a value as a float with one decimal place and optional unit.

    Automatically converts force values from N to kN and moment values from Nm to kNm.

    This function now uses the centralized unit conversion system to ensure
    consistent conversion logic.

    :param value: Value to format
    :type value: str | float
    :param unit: Unit to append to the formatted value
    :type unit: str
    :param default: Default value if formatting fails
    :type default: str
    :returns: Formatted string with unit or default value
    :rtype: str
    """
    # Import the centralized conversion function
    from .scia_unit_conversion import safe_float_format as safe_float_format_centralized

    # Use the centralized system
    return safe_float_format_centralized(value, unit, default)


def format_coordinates_safe(coords: tuple[float, ...] | list[float] | str | None) -> str:
    """
    Safely format coordinates as a string.

    :param coords: Coordinate data (tuple, list, or other)
    :type coords: tuple[float, ...] | list[float] | str | None
    :returns: Formatted coordinate string
    :rtype: str
    """
    if coords is None:
        return "N/A"

    try:
        if isinstance(coords, (list, tuple)) and len(coords) >= 3:
            # Convert to floats safely
            x = float(coords[0]) if coords[0] is not None else 0.0
            y = float(coords[1]) if coords[1] is not None else 0.0
            z = float(coords[2]) if coords[2] is not None else 0.0
            return f"({x:.1f}, {y:.1f}, {z:.1f})"
        return str(coords)
    except (ValueError, TypeError, IndexError):
        return "N/A"


def create_scia_node_table_data(df: pd.DataFrame, result_type: str, units_mapping: dict[str, str] | None = None) -> tuple[list[list[str]], list[str]]:
    """
    Create table data and headers from a SCIA results DataFrame.

    This function uses the centralized unit conversion system to ensure
    consistent formatting and unit conversion.

    :param df: DataFrame with SCIA results
    :type df: pd.DataFrame
    :param result_type: Type of results (SLS kar, SLS freq, ULS)
    :type result_type: str
    :param units_mapping: Mapping of column names to their units
    :type units_mapping: dict[str, str] | None
    :returns: Tuple of (table_data, headers)
    :rtype: tuple[list[list[str]], list[str]]
    """
    from .scia_unit_conversion import SciaUnitConverter

    units_mapping = units_mapping or {}

    # Create a converter to handle the formatting consistently
    # Determine element type from units mapping (presence of "/m" indicates 2D)
    has_per_meter_units = any("/m" in unit for unit in units_mapping.values())
    element_type = "2D" if has_per_meter_units else "1D"
    converter = SciaUnitConverter(element_type)

    # Create headers with units where available - use converter for consistency
    force_units = {}
    for component in ["v_x", "v_y", "m_xD+", "m_xD-", "m_yD+", "m_yD-"]:
        # Use provided units mapping if available, otherwise get from converter
        if component in units_mapping:
            force_units[component] = units_mapping[component]
        else:
            force_units[component] = converter.get_display_unit(component)

    headers = [
        "Coordinates",
        "Name",
        f"Vx Max ({force_units['v_x']})",
        f"Vy Max ({force_units['v_y']})",
        f"MxD+ Max ({force_units['m_xD+']})",
        f"MxD- Max ({force_units['m_xD-']})",
        f"MyD+ Max ({force_units['m_yD+']})",
        f"MyD- Max ({force_units['m_yD-']})",
    ]

    if df.empty:
        return [[f"Geen {result_type} data", f"{result_type} resultaten niet beschikbaar", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]], headers

    # Use vectorized operations instead of row-by-row iteration
    # Format coordinates
    coords_formatted = df["coords_xyz"].apply(format_coordinates_safe)

    # Format numeric columns with their respective units using the converter
    numeric_columns = ["v_x_max", "v_y_max", "m_xD+_max", "m_xD-_max", "m_yD+_max", "m_yD-_max"]
    column_to_component = {
        "v_x_max": "v_x",
        "v_y_max": "v_y",
        "m_xD+_max": "m_xD+",
        "m_xD-_max": "m_xD-",
        "m_yD+_max": "m_yD+",
        "m_yD-_max": "m_yD-",
    }

    formatted_cols = {}
    for col in numeric_columns:
        if col in df.columns:
            component = column_to_component.get(col, "")
            # Use converter to format values with consistent conversion
            formatted_cols[col] = df[col].apply(lambda x: converter.format_value_with_unit(x, component, decimals=1, default="N/A"))
        else:
            formatted_cols[col] = pd.Series(["N/A"] * len(df))

    # Create table data using list comprehension with pre-computed values
    # The name column should be available after IDEA processing
    names = df.get("name", pd.Series(["N/A"] * len(df))).astype(str)

    table_data = [
        [
            coords_formatted.iloc[i],
            names.iloc[i],
            formatted_cols["v_x_max"].iloc[i],
            formatted_cols["v_y_max"].iloc[i],
            formatted_cols["m_xD+_max"].iloc[i],
            formatted_cols["m_xD-_max"].iloc[i],
            formatted_cols["m_yD+_max"].iloc[i],
            formatted_cols["m_yD-_max"].iloc[i],
        ]
        for i in range(len(df))
    ]

    return table_data, headers


def create_scia_integration_strip_table_data(
    df: pd.DataFrame, result_type: str, units_mapping: dict[str, str] | None = None
) -> tuple[list[list[str]], list[str]]:
    """
    Create table data and headers from a SCIA 1D results DataFrame.

    This function uses the centralized unit conversion system to ensure
    consistent formatting and unit conversion for 1D beam forces.

    :param df: DataFrame with SCIA 1D results
    :type df: pd.DataFrame
    :param result_type: Type of results (SLS kar, SLS freq, ULS)
    :type result_type: str
    :param units_mapping: Mapping of column names to their units
    :type units_mapping: dict[str, str] | None
    :returns: Tuple of (table_data, headers)
    :rtype: tuple[list[list[str]], list[str]]
    """
    from .scia_unit_conversion import SciaUnitConverter

    units_mapping = units_mapping or {}

    # Create a converter for 1D beam elements
    converter = SciaUnitConverter("1D")

    # Create headers with units for 1D beam forces
    force_components = ["N", "V_y", "V_z", "M_x", "M_y", "M_z"]
    force_units = {}
    for component in force_components:
        # Use provided units mapping if available, otherwise get from converter
        if component in units_mapping:
            force_units[component] = units_mapping[component]
        else:
            force_units[component] = converter.get_display_unit(component)

    headers = [
        "Name",
        "dx (m)",
        "Direction Vector",
        f"N Max ({force_units['N']})",  # Normal force
        f"Vy Max ({force_units['V_y']})",  # Shear force Y
        f"Vz Max ({force_units['V_z']})",  # Shear force Z
        f"Mx Max ({force_units['M_x']})",  # Torsional moment X
        f"My Max ({force_units['M_y']})",  # Bending moment Y
        f"Mz Max ({force_units['M_z']})",  # Bending moment Z
    ]

    if df.empty:
        return [[f"Geen {result_type} 1D data", f"{result_type} 1D resultaten niet beschikbaar", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]], headers

    # Use vectorized operations instead of row-by-row iteration
    # Format dx values (integration strip positions)
    def format_dx_value(x: str | float | None) -> str:
        """Safely format dx values, handling various input types."""
        if pd.isna(x):
            return "N/A"
        try:
            # Try to convert to float first
            float_val = float(x)
        except (ValueError, TypeError):
            # If conversion fails, return as string
            return str(x) if x is not None else "N/A"
        else:
            return f"{float_val:.2f}"

    dx_formatted = df.get("dx", pd.Series([0.0] * len(df))).apply(format_dx_value)

    # Format direction vector values
    def format_direction_vector(direction_vector: tuple[float, float, float] | list[float] | str | None) -> str:
        """Safely format direction vector values as (x,y,z) for SCIA 1D views."""
        if direction_vector is None:
            return "N/A"
        try:
            if isinstance(direction_vector, (list, tuple)) and len(direction_vector) >= 3:
                x, y, z = float(direction_vector[0]), float(direction_vector[1]), float(direction_vector[2])
                return f"({x:.0f},{y:.0f},{z:.0f})"
            return str(direction_vector)
        except (ValueError, TypeError, IndexError):
            return "N/A"

    direction_vector_formatted = df.get("direction_vector", pd.Series([None] * len(df))).apply(format_direction_vector)

    # Format numeric columns with their respective units using the converter
    numeric_columns = ["n_max", "v_y_max", "v_z_max", "m_x_max", "m_y_max", "m_z_max"]
    column_to_component = {
        "n_max": "N",
        "v_y_max": "V_y",
        "v_z_max": "V_z",
        "m_x_max": "M_x",
        "m_y_max": "M_y",
        "m_z_max": "M_z",
    }

    formatted_cols = {}
    for col in numeric_columns:
        if col in df.columns:
            component = column_to_component.get(col, "")
            # Use converter to format values with consistent conversion
            formatted_cols[col] = df[col].apply(lambda x: converter.format_value_with_unit(x, component, decimals=1, default="N/A"))
        else:
            formatted_cols[col] = pd.Series(["N/A"] * len(df))

    # Create table data using list comprehension with pre-computed values
    names = df.get("Naam", df.get("name", pd.Series(["N/A"] * len(df)))).astype(str)

    table_data = [
        [
            names.iloc[i],
            dx_formatted.iloc[i],
            direction_vector_formatted.iloc[i],
            formatted_cols["n_max"].iloc[i],
            formatted_cols["v_y_max"].iloc[i],
            formatted_cols["v_z_max"].iloc[i],
            formatted_cols["m_x_max"].iloc[i],
            formatted_cols["m_y_max"].iloc[i],
            formatted_cols["m_z_max"].iloc[i],
        ]
        for i in range(len(df))
    ]

    return table_data, headers


def create_scia_node_results_table(results: dict[str, Any], result_type: str) -> TableResult:
    """
    Create a VIKTOR TableResult from SCIA analysis results for a specific result type.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param result_type: Type of results to extract ("SLS kar", "SLS freq", "ULS")
    :type result_type: str
    :returns: VIKTOR TableResult with formatted data including units
    :rtype: TableResult
    :raises Exception: If processing fails
    """
    try:
        # Extract units mapping from results
        units_mapping = results.get("units", {}).get("internal_forces", {})

        # Use the centralized processing function with caching
        processed_results = get_processed_results_with_cache(results)

        # Extract the specific DataFrame from the processed results
        if processed_results and isinstance(processed_results, dict):
            # Try both the direct key and the "node_" prefixed key
            result_df = processed_results.get(result_type)
            if result_df is None:
                # Try with "node_" prefix
                node_key = f"node_{result_type}"
                result_df = processed_results.get(node_key)

            if result_df is not None and not result_df.empty:
                table_data, headers = create_scia_node_table_data(result_df, result_type, units_mapping)
                return TableResult(table_data, column_headers=headers)

        # DataFrame not found or empty - use default headers with units
        default_headers = [
            "Coordinates",
            "Name",
            "Vx Max (kN)",
            "Vy Max (kN)",
            "MxD+ Max (kNm)",
            "MxD- Max (kNm)",
            "MyD+ Max (kNm)",
            "MyD- Max (kNm)",
        ]
        return TableResult(
            [[f"Geen {result_type} data", f"{result_type} resultaten niet beschikbaar", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]],
            column_headers=default_headers,
        )

    except Exception as e:
        # Handle errors from processing function
        error_message = f"Fout bij verwerken {result_type} resultaten: {str(e)[:100]}..."
        default_headers = [
            "Coordinates",
            "Name",
            "Vx Max (kN)",
            "Vy Max (kN)",
            "MxD+ Max (kNm)",
            "MxD- Max (kNm)",
            "MyD+ Max (kNm)",
            "MyD- Max (kNm)",
        ]
        return TableResult([["Verwerkingsfout", error_message, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]], column_headers=default_headers)


def create_scia_integration_strip_results_table(results: dict[str, Any], result_type: str) -> TableResult:
    """
    Create a VIKTOR TableResult from SCIA integration strip analysis results for a specific result type.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param result_type: Type of results to extract ("SLS kar", "SLS freq", "ULS")
    :type result_type: str
    :returns: VIKTOR TableResult with formatted data including units
    :rtype: TableResult
    :raises Exception: If processing fails
    """
    try:
        # Extract units mapping from results
        units_mapping = results.get("units", {}).get("internal_forces", {})

        # Use the centralized processing function with caching
        processed_results = get_processed_integration_strip_results_with_cache(results)

        # Extract the specific DataFrame from the processed results
        if processed_results and isinstance(processed_results, dict):
            # Try both the direct key and the "strip_" prefixed key
            result_df = processed_results.get(result_type)
            if result_df is None:
                # Try with "strip_" prefix
                strip_key = f"strip_{result_type}"
                result_df = processed_results.get(strip_key)

            if result_df is not None and not result_df.empty:
                table_data, headers = create_scia_integration_strip_table_data(result_df, result_type, units_mapping)
                return TableResult(table_data, column_headers=headers)

        # DataFrame not found or empty - use default headers with units
        default_headers = [
            "Name",
            "dx (m)",
            "Direction Vector",
            "N Max (kN)",
            "Vy Max (kN)",
            "Vz Max (kN)",
            "Mx Max (kNm)",
            "My Max (kNm)",
            "Mz Max (kNm)",
        ]
        return TableResult(
            [
                [
                    f"Geen {result_type} strip data",
                    f"{result_type} integration strip resultaten niet beschikbaar",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                ]
            ],
            column_headers=default_headers,
        )

    except Exception as e:
        # Handle errors from processing function
        error_message = f"Fout bij verwerken {result_type} integration strip resultaten: {str(e)[:100]}..."
        default_headers = [
            "Name",
            "dx (m)",
            "Direction Vector",
            "N Max (kN)",
            "Vy Max (kN)",
            "Vz Max (kN)",
            "Mx Max (kNm)",
            "My Max (kNm)",
            "Mz Max (kNm)",
        ]
        return TableResult([["Verwerkingsfout", error_message, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]], column_headers=default_headers)
