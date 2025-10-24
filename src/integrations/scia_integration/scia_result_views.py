"""Functions for creating SCIA result views for VIKTOR tables."""

from typing import TYPE_CHECKING, Any

import pandas as pd
from viktor.views import TableResult

if TYPE_CHECKING:
    from .scia_unit_conversion import SciaUnitConverter

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
    Safely format coordinates as a string with 2 decimal places.

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
            return f"({x:.2f}, {y:.2f}, {z:.2f})"
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
            formatted_cols[col] = df[col].apply(lambda x: converter.format_value_with_unit(x, component, decimals=2, default="N/A"))
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


def _get_force_units_mapping(units_mapping: dict[str, str], converter: "SciaUnitConverter") -> dict[str, str]:
    """
    Get force units mapping with fallback to converter defaults.

    :param units_mapping: Provided units mapping
    :type units_mapping: dict[str, str]
    :param converter: SCIA unit converter
    :type converter: SciaUnitConverter
    :returns: Force units mapping
    :rtype: dict[str, str]
    """
    force_components = ["N", "V_y", "V_z", "M_x", "M_y", "M_z"]
    force_units = {}
    for component in force_components:
        # Use provided units mapping if available, otherwise get from converter
        if component in units_mapping:
            force_units[component] = units_mapping[component]
        else:
            force_units[component] = converter.get_display_unit(component)
    return force_units


def _create_headers_with_units(force_units: dict[str, str]) -> list[str]:
    """
    Create table headers with units for SCIA integration strip results.

    :param force_units: Force units mapping
    :type force_units: dict[str, str]
    :returns: List of headers with units
    :rtype: list[str]
    """
    return [
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


def _format_numeric_columns(df: pd.DataFrame, converter: "SciaUnitConverter") -> dict[str, pd.Series]:
    """
    Format numeric columns with their respective units using the converter.

    :param df: DataFrame with SCIA 1D results
    :type df: pd.DataFrame
    :param converter: SCIA unit converter
    :type converter: SciaUnitConverter
    :returns: Dictionary of formatted column data
    :rtype: dict[str, pd.Series]
    """
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
            formatted_cols[col] = df[col].apply(lambda x: converter.format_value_with_unit(x, component, decimals=2, default="N/A"))
        else:
            formatted_cols[col] = pd.Series(["N/A"] * len(df))

    return formatted_cols


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

    # Get force units mapping
    force_units = _get_force_units_mapping(units_mapping, converter)

    # Create headers with units for 1D beam forces
    headers = _create_headers_with_units(force_units)

    if df.empty:
        return [
            [f"Geen {result_type} 1D data", f"{result_type} 1D resultaten niet beschikbaar", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]
        ], headers

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
    formatted_cols = _format_numeric_columns(df, converter)

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


def create_scia_cs_table_data(processed_cs_df: pd.DataFrame, result_type: str) -> tuple[list[list[str]], list[str]]:
    """
    Create table data and headers from processed CS (Cross Section) SCIA results.

    CS tables contain results from SCIA section on plane objects (cross sections).
    This function takes a processed DataFrame where each row represents a unique coordinate
    with maximum absolute force/moment values already calculated.

    :param processed_cs_df: Processed DataFrame with unique coordinates and max absolute values
    :type processed_cs_df: pd.DataFrame
    :param result_type: Type of results (cs ULS, cs SLS kar, cs SLS freq)
    :type result_type: str
    :returns: Tuple of (table_data, headers)
    :rtype: tuple[list[list[str]], list[str]]
    """
    from .scia_unit_conversion import SciaUnitConverter

    # Create a converter for 2D elements (CS tables are cross sections on plane objects)
    converter = SciaUnitConverter("2D")

    # Create headers with units
    headers = [
        "Name",
        "Coordinates",
        "Vx (kN/m)",
        "Vy (kN/m)",
        "MxD+ (kNm/m)",
        "MxD- (kNm/m)",
        "MyD+ (kNm/m)",
        "MyD- (kNm/m)",
    ]

    # Check if we have any data
    if processed_cs_df.empty:
        return [[f"Geen {result_type} data", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]], headers

    table_data = []

    # Column mapping (processed DataFrame uses same column names as raw SCIA data)
    # CS tables use lowercase with underscores: v_x, v_y, m_xD+, m_xD-, m_yD+, m_yD-

    # Format each row
    for _, row in processed_cs_df.iterrows():
        # Get name
        name = row.get("name", "N/A")

        # Get coordinates
        coords_xyz = row.get("coords_xyz", (0.0, 0.0, 0.0))
        coords = format_coordinates_safe(coords_xyz)

        # Get force/moment values (already max absolute values from processing)
        # Use lowercase column names with underscores as in the raw SCIA data
        v_x = row.get("v_x", 0.0)
        v_y = row.get("v_y", 0.0)
        m_xd_plus = row.get("m_xD+", 0.0)
        m_xd_minus = row.get("m_xD-", 0.0)
        m_yd_plus = row.get("m_yD+", 0.0)
        m_yd_minus = row.get("m_yD-", 0.0)

        # Format values with units (using appropriate component names for converter)
        v_x_str = converter.format_value_with_unit(v_x, "v_x", decimals=2, default="N/A")
        v_y_str = converter.format_value_with_unit(v_y, "v_y", decimals=2, default="N/A")
        m_xd_plus_str = converter.format_value_with_unit(m_xd_plus, "m_xD+", decimals=2, default="N/A")
        m_xd_minus_str = converter.format_value_with_unit(m_xd_minus, "m_xD-", decimals=2, default="N/A")
        m_yd_plus_str = converter.format_value_with_unit(m_yd_plus, "m_yD+", decimals=2, default="N/A")
        m_yd_minus_str = converter.format_value_with_unit(m_yd_minus, "m_yD-", decimals=2, default="N/A")

        row_data = [
            str(name),
            coords,
            v_x_str,
            v_y_str,
            m_xd_plus_str,
            m_xd_minus_str,
            m_yd_plus_str,
            m_yd_minus_str,
        ]
        table_data.append(row_data)

    return table_data, headers


def create_scia_cs_results_table(results: dict[str, Any], table_type: str) -> TableResult:
    """
    Create a VIKTOR TableResult from CS (Cross Section) SCIA analysis results.

    CS tables contain results from SCIA section on plane objects (cross sections).
    This function processes the CS data to find unique coordinate locations and
    their maximum absolute force/moment values.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param table_type: Type of CS table to extract ("ULS", "SLS kar", "SLS freq")
    :type table_type: str
    :returns: VIKTOR TableResult with formatted CS data including units
    :rtype: TableResult
    :raises Exception: If processing fails
    """
    from .scia_results_processor import process_scia_cs_results

    try:
        # Process all CS results (gets DataFrames with unique coords and max absolute values)
        cs_results = process_scia_cs_results(results)

        # Get the specific table type we want
        processed_cs_df = cs_results.get(table_type, pd.DataFrame())

        # Create table data from the processed DataFrame
        table_data, headers = create_scia_cs_table_data(processed_cs_df, table_type)

        return TableResult(table_data, column_headers=headers)

    except Exception as e:
        # Handle errors from processing function
        error_message = f"Fout bij verwerken {table_type} resultaten: {str(e)[:100]}..."
        default_headers = [
            "Name",
            "Coordinates",
            "Vx (kN/m)",
            "Vy (kN/m)",
            "MxD+ (kNm/m)",
            "MxD- (kNm/m)",
            "MyD+ (kNm/m)",
            "MyD- (kNm/m)",
        ]
        return TableResult([["Verwerkingsfout", error_message, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]], column_headers=default_headers)


def create_all_scia_cs_results_tables(results: dict[str, Any]) -> dict[str, TableResult]:
    """
    Create VIKTOR TableResults for all CS (Cross Section) table types.

    CS tables contain results from SCIA section on plane objects (cross sections).

    Creates tables for:
    - ULS (Ultimate Limit State)
    - SLS kar (Serviceability Limit State - characteristic)
    - SLS freq (Serviceability Limit State - frequent)

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :returns: Dictionary mapping table type to TableResult
    :rtype: dict[str, TableResult]
    """
    table_types = ["ULS", "SLS kar", "SLS freq"]
    cs_tables = {}

    for table_type in table_types:
        cs_tables[table_type] = create_scia_cs_results_table(results, table_type)

    return cs_tables
