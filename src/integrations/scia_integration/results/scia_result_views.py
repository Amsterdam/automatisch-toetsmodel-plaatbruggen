"""Functions for creating SCIA result views for VIKTOR tables."""

from typing import TYPE_CHECKING, Any

import pandas as pd
from viktor.views import TableResult

if TYPE_CHECKING:
    from .scia_unit_conversion import SciaUnitConverter

from src.integrations.scia_integration.constants.results import (
    CS_TABLE_TYPES,
    MAX_ERROR_MESSAGE_LENGTH,
)

from .scia_results_processor import (
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


def _get_cs_table_headers(include_zone: bool = False) -> list[str]:
    """
    Generate headers for CS (Cross Section) result tables.

    :param include_zone: Whether to include the Zone column
    :type include_zone: bool
    :returns: List of header strings
    :rtype: list[str]
    """
    headers = ["Name"]
    if include_zone:
        headers.append("Zone")
    headers.extend(
        [
            "Coordinates",
            "Belasting",
            "Max For",
            "Vx (kN/m)",
            "Vy (kN/m)",
            "MxD+ (kNm/m)",
            "MxD- (kNm/m)",
            "MyD+ (kNm/m)",
            "MyD- (kNm/m)",
            "NxD (kN/m)",
            "NyD (kN/m)",
        ]
    )
    return headers


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

    # Check if zone column exists in the DataFrame and is not empty
    has_zone_column = "zone" in processed_cs_df.columns and not processed_cs_df.empty

    # Create headers with units
    headers = _get_cs_table_headers(include_zone=has_zone_column)

    # Check if we have any data
    if processed_cs_df.empty:
        # Create a row with "No data" message plus N/A for all other columns
        # Number of N/A values = len(headers) - 1 (for the message)
        no_data_row = [f"Geen {result_type} data"] + ["N/A"] * (len(headers) - 1)
        return [no_data_row], headers

    table_data = []

    # Column mapping (processed DataFrame uses same column names as raw SCIA data)
    # CS tables use lowercase with underscores: v_x, v_y, m_xD+, m_xD-, m_yD+, m_yD-, n_xD, n_yD

    # Format each row
    for _, row in processed_cs_df.iterrows():
        # Get name
        name = row.get("name", "N/A")

        # Get coordinates
        coords_xyz = row.get("coords_xyz", (0.0, 0.0, 0.0))
        coords = format_coordinates_safe(coords_xyz)

        # Get belasting (load case name)
        belasting = row.get("belasting", "N/A")

        # Get which column this row represents the max for
        max_for_column = row.get("max_for_column", "N/A")

        # Get force/moment values (already max absolute values from processing)
        # Use lowercase column names with underscores as in the raw SCIA data
        v_x = row.get("v_x", 0.0)
        v_y = row.get("v_y", 0.0)
        m_xd_plus = row.get("m_xD+", 0.0)
        m_xd_minus = row.get("m_xD-", 0.0)
        m_yd_plus = row.get("m_yD+", 0.0)
        m_yd_minus = row.get("m_yD-", 0.0)
        n_xd = row.get("n_xD", 0.0)
        n_yd = row.get("n_yD", 0.0)

        # Format values with units (using appropriate component names for converter)
        v_x_str = converter.format_value_with_unit(v_x, "v_x", decimals=2, default="N/A")
        v_y_str = converter.format_value_with_unit(v_y, "v_y", decimals=2, default="N/A")
        m_xd_plus_str = converter.format_value_with_unit(m_xd_plus, "m_xD+", decimals=2, default="N/A")
        m_xd_minus_str = converter.format_value_with_unit(m_xd_minus, "m_xD-", decimals=2, default="N/A")
        m_yd_plus_str = converter.format_value_with_unit(m_yd_plus, "m_yD+", decimals=2, default="N/A")
        m_yd_minus_str = converter.format_value_with_unit(m_yd_minus, "m_yD-", decimals=2, default="N/A")
        n_xd_str = converter.format_value_with_unit(n_xd, "n_xD", decimals=2, default="N/A")
        n_yd_str = converter.format_value_with_unit(n_yd, "n_yD", decimals=2, default="N/A")

        # Build row data - order must match headers exactly
        if has_zone_column:
            # With zone: Name, Zone, Coordinates, Belasting, Max For, Vx, Vy, MxD+, MxD-, MyD+, MyD-, NxD, NyD (13 columns)
            zone = row.get("zone", "N/A")
            row_data = [
                str(name),
                str(zone),
                coords,
                str(belasting),
                str(max_for_column),
                v_x_str,
                v_y_str,
                m_xd_plus_str,
                m_xd_minus_str,
                m_yd_plus_str,
                m_yd_minus_str,
                n_xd_str,
                n_yd_str,
            ]
        else:
            # Without zone: Name, Coordinates, Belasting, Max For, Vx, Vy, MxD+, MxD-, MyD+, MyD-, NxD, NyD (12 columns)
            row_data = [
                str(name),
                coords,
                str(belasting),
                str(max_for_column),
                v_x_str,
                v_y_str,
                m_xd_plus_str,
                m_xd_minus_str,
                m_yd_plus_str,
                m_yd_minus_str,
                n_xd_str,
                n_yd_str,
            ]

        table_data.append(row_data)

    return table_data, headers


def create_scia_cs_results_table(results: dict[str, Any], table_type: str, bridge_segments: list[Any] | None = None) -> TableResult:
    """
    Create a VIKTOR TableResult from CS (Cross Section) SCIA analysis results.

    CS tables contain results from SCIA section on plane objects (cross sections).
    This function processes the CS data to find unique coordinate locations and
    their maximum absolute force/moment values.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param table_type: Type of CS table to extract ("ULS", "SLS freq")
    :type table_type: str
    :param bridge_segments: Optional list of bridge segments for zone mapping
    :type bridge_segments: list[Any] | None
    :returns: VIKTOR TableResult with formatted CS data including units
    :rtype: TableResult
    :raises Exception: If processing fails
    """
    from .scia_results_processor import process_scia_cs_results

    try:
        # Process all CS results (gets DataFrames with unique coords and max absolute values)
        # Pass bridge_segments to enable zone mapping
        cs_results = process_scia_cs_results(results, bridge_segments=bridge_segments)

        # Get the specific table type we want
        processed_cs_df = cs_results.get(table_type, pd.DataFrame())

        # Create table data from the processed DataFrame
        table_data, headers = create_scia_cs_table_data(processed_cs_df, table_type)

        return TableResult(table_data, column_headers=headers)

    except Exception as e:
        # Handle errors from processing function
        error_message = f"Fout bij verwerken {table_type} resultaten: {str(e)[:MAX_ERROR_MESSAGE_LENGTH]}..."
        # Use headers without Zone column for error case (zone mapping may have failed)
        default_headers = _get_cs_table_headers(include_zone=False)
        # Create error row with appropriate number of N/A values
        error_row = ["Verwerkingsfout", error_message] + ["N/A"] * (len(default_headers) - 2)
        return TableResult([error_row], column_headers=default_headers)


def create_all_scia_cs_results_tables(results: dict[str, Any], bridge_segments: list[Any] | None = None) -> dict[str, TableResult]:
    """
    Create VIKTOR TableResults for all CS (Cross Section) table types.

    CS tables contain results from SCIA section on plane objects (cross sections).

    Creates tables for:
    - ULS (Ultimate Limit State)
    - SLS freq (Serviceability Limit State - frequent)

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param bridge_segments: Optional list of bridge segments for zone mapping
    :type bridge_segments: list[Any] | None
    :returns: Dictionary mapping table type to TableResult
    :rtype: dict[str, TableResult]
    """
    cs_tables: dict[str, TableResult] = {}

    for table_type in CS_TABLE_TYPES:
        cs_tables[table_type] = create_scia_cs_results_table(results, table_type, bridge_segments=bridge_segments)

    return cs_tables


def create_scia_cs_envelope_table(results: dict[str, Any], bridge_segments: list[Any] | None = None) -> TableResult:
    """
    Create a VIKTOR TableResult for CS force envelopes (ULS and SLS freq combined).

    For each unique zone, shows rows with maximum absolute values for each force component.
    Combines ULS and SLS freq results and sorts by zone.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param bridge_segments: Optional list of bridge segments for zone mapping
    :type bridge_segments: list[Any] | None
    :returns: TableResult with envelope data
    :rtype: TableResult
    """
    from .scia_results_processor import extract_cs_force_envelopes
    from .scia_unit_conversion import SciaUnitConverter

    try:
        # Extract force envelopes from CS results
        df_envelope = extract_cs_force_envelopes(results, bridge_segments=bridge_segments)

        if df_envelope.empty:
            return TableResult(
                [["Geen gegevens", "Geen CS resultaten beschikbaar", "", "", "", "", "", "", "", "", "", "", "", ""]],
                column_headers=[
                    "Zone",
                    "Type",
                    "Naam",
                    "Coördinaten",
                    "Belasting",
                    "Max For",
                    "Vx (kN/m)",
                    "Vy (kN/m)",
                    "MxD+ (kNm/m)",
                    "MxD- (kNm/m)",
                    "MyD+ (kNm/m)",
                    "MyD- (kNm/m)",
                    "NxD (kN/m)",
                    "NyD (kN/m)",
                ],
            )

        # Create converter for formatting values
        converter = SciaUnitConverter("2D")

        # Build table headers
        headers = [
            "Zone",
            "Type",
            "Naam",
            "Coördinaten",
            "Belasting",
            "Max For",
            "Vx (kN/m)",
            "Vy (kN/m)",
            "MxD+ (kNm/m)",
            "MxD- (kNm/m)",
            "MyD+ (kNm/m)",
            "MyD- (kNm/m)",
            "NxD (kN/m)",
            "NyD (kN/m)",
        ]

        table_data = []

        # Format each row
        for _, row in df_envelope.iterrows():
            zone = row.get("zone", "N/A")
            result_type = row.get("result_type", "N/A")
            name = row.get("name", "N/A")
            coords_xyz = row.get("coords_xyz", (0.0, 0.0, 0.0))
            coords = format_coordinates_safe(coords_xyz)
            belasting = row.get("belasting", "N/A")
            max_for_column = row.get("max_for_column", "N/A")

            # Get force/moment values
            v_x = row.get("v_x", 0.0)
            v_y = row.get("v_y", 0.0)
            m_xd_plus = row.get("m_xD+", 0.0)
            m_xd_minus = row.get("m_xD-", 0.0)
            m_yd_plus = row.get("m_yD+", 0.0)
            m_yd_minus = row.get("m_yD-", 0.0)
            n_xd = row.get("n_xD", 0.0)
            n_yd = row.get("n_yD", 0.0)

            # Format values with units
            v_x_str = converter.format_value_with_unit(v_x, "v_x", decimals=2, default="N/A")
            v_y_str = converter.format_value_with_unit(v_y, "v_y", decimals=2, default="N/A")
            m_xd_plus_str = converter.format_value_with_unit(m_xd_plus, "m_xD+", decimals=2, default="N/A")
            m_xd_minus_str = converter.format_value_with_unit(m_xd_minus, "m_xD-", decimals=2, default="N/A")
            m_yd_plus_str = converter.format_value_with_unit(m_yd_plus, "m_yD+", decimals=2, default="N/A")
            m_yd_minus_str = converter.format_value_with_unit(m_yd_minus, "m_yD-", decimals=2, default="N/A")
            n_xd_str = converter.format_value_with_unit(n_xd, "n_xD", decimals=2, default="N/A")
            n_yd_str = converter.format_value_with_unit(n_yd, "n_yD", decimals=2, default="N/A")

            row_data = [
                str(zone),
                str(result_type),
                str(name),
                coords,
                str(belasting),
                str(max_for_column),
                v_x_str,
                v_y_str,
                m_xd_plus_str,
                m_xd_minus_str,
                m_yd_plus_str,
                m_yd_minus_str,
                n_xd_str,
                n_yd_str,
            ]

            table_data.append(row_data)

        return TableResult(table_data, column_headers=headers)

    except Exception as e:
        import traceback

        traceback.print_exc()
        error_message = f"Fout bij verwerken CS envelopes: {str(e)[:100]}..."
        return TableResult(
            [["Fout", error_message, "", "", "", "", "", "", "", "", "", "", "", ""]],
            column_headers=[
                "Zone",
                "Type",
                "Naam",
                "Coördinaten",
                "Belasting",
                "Max For",
                "Vx (kN/m)",
                "Vy (kN/m)",
                "MxD+ (kNm/m)",
                "MxD- (kNm/m)",
                "MyD+ (kNm/m)",
                "MyD- (kNm/m)",
                "NxD (kN/m)",
                "NyD (kN/m)",
            ],
        )
