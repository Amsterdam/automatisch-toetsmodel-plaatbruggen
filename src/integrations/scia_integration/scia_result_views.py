"""Functions for creating SCIA result views for VIKTOR tables."""

import functools
from typing import Any

import pandas as pd
from viktor.views import TableResult

from src.integrations.idea_integration.scia_to_idea_functions import process_scia_results_for_idea


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
                for key, value in table_data.items():
                    if isinstance(value, dict) and len(value) > 0:
                        integration_results = value
                        break

            if not integration_results:
                return pd.DataFrame()

        # Process the raw data with grouping and filtering
        df_processed = process_raw_1d_data_for_view(integration_results)

        return df_processed

    except Exception:
        # Return empty DataFrame on any error
        return pd.DataFrame()


def process_raw_1d_data_for_view(integration_results: dict[str, Any]) -> pd.DataFrame:
    """
    Process raw 1D SCIA data by grouping rows with same name and dx values.

    Groups rows by 'Naam' and 'dx', merges 'Belasting' values into single cells,
    and finds absolute maximum values for force/moment columns.

    :param integration_results: Raw integration results from SCIA
    :type integration_results: dict[str, Any]
    :returns: Processed DataFrame with grouped and filtered data
    :rtype: pd.DataFrame
    """
    # Get available columns (all keys that are lists)
    available_columns = []
    column_data = {}

    for key, value in integration_results.items():
        if isinstance(value, list) and len(value) > 0:
            available_columns.append(key)
            column_data[key] = value

    if not available_columns or not column_data:
        return pd.DataFrame()

    # Create DataFrame from raw data
    df_raw = pd.DataFrame(column_data)

    if df_raw.empty:
        return pd.DataFrame()

    # Convert numeric columns to proper types
    numeric_columns = ["N", "V_y", "V_z", "M_x", "M_y", "M_z", "dx"]
    for col in numeric_columns:
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce").fillna(0)

    # Group by 'Naam' and 'dx'
    if "Naam" not in df_raw.columns or "dx" not in df_raw.columns:
        return df_raw  # Return original if grouping columns don't exist

    # Define aggregation functions
    agg_functions = {}

    for col in df_raw.columns:
        if col == "Belasting":
            # Merge Belasting values into single cell (concatenate unique values)
            agg_functions[col] = lambda x: " | ".join(sorted(x.dropna().astype(str).unique()))
        elif col in numeric_columns and col not in ["Naam", "dx"]:
            # Find absolute maximum for force/moment columns
            def abs_max_aggregator(series):
                """Find the value with the maximum absolute value."""
                series_clean = series.dropna()
                if series_clean.empty:
                    return 0
                # Find index of maximum absolute value
                abs_max_idx = series_clean.abs().idxmax()
                return series_clean.loc[abs_max_idx]

            agg_functions[col] = abs_max_aggregator
        elif col in ["Naam", "dx"]:
            # Keep first value for grouping columns
            agg_functions[col] = "first"
        else:
            # For other columns, take first non-null value
            agg_functions[col] = lambda x: x.dropna().iloc[0] if not x.dropna().empty else ""

    # Apply grouping and aggregation
    df_processed = df_raw.groupby(["Naam", "dx"], as_index=False).agg(agg_functions)

    # Sort by Naam and dx for consistent ordering
    df_processed = df_processed.sort_values(["Naam", "dx"]).reset_index(drop=True)

    return df_processed


# Simple cache for processed results to avoid reprocessing the same data
@functools.lru_cache(maxsize=32)
def _cached_process_scia_results(_results_hash: int) -> dict[str, pd.DataFrame] | None:
    """
    Cached wrapper for process_scia_results_for_idea.

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


def safe_float_format(value: str | float, unit: str = "", default: str = "N/A") -> str:
    """
    Safely format a value as a float with one decimal place and optional unit.
    Automatically converts force values from N to kN and moment values from Nm to kNm.

    This function now uses the centralized unit conversion system to ensure
    consistent conversion logic.

    :param value: Value to format
    :type value: Any
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


def create_scia_table_data(df: pd.DataFrame, result_type: str, units_mapping: dict[str, str] | None = None) -> tuple[list[list[str]], list[str]]:
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


def create_scia_1d_table_data(df: pd.DataFrame, result_type: str, units_mapping: dict[str, str] | None = None) -> tuple[list[list[str]], list[str]]:
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
        "Coordinates",
        "Name",
        f"N Max ({force_units['N']})",  # Normal force
        f"Vy Max ({force_units['V_y']})",  # Shear force Y
        f"Vz Max ({force_units['V_z']})",  # Shear force Z
        f"Mx Max ({force_units['M_x']})",  # Torsional moment X
        f"My Max ({force_units['M_y']})",  # Bending moment Y
        f"Mz Max ({force_units['M_z']})",  # Bending moment Z
    ]

    if df.empty:
        return [[f"Geen {result_type} 1D data", f"{result_type} 1D resultaten niet beschikbaar", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]], headers

    # Use vectorized operations instead of row-by-row iteration
    # Format coordinates
    coords_formatted = df["coords_xyz"].apply(format_coordinates_safe)

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
    names = df.get("name", pd.Series(["N/A"] * len(df))).astype(str)

    table_data = [
        [
            coords_formatted.iloc[i],
            names.iloc[i],
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


# Module-level cache for processed results
_processed_results_cache: dict[int, dict[str, pd.DataFrame]] = {}


def create_scia_result_table(results: dict[str, Any], result_type: str) -> TableResult:
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

        # Use simple caching to avoid reprocessing the same results
        results_hash = _get_results_hash(results)

        if results_hash in _processed_results_cache:
            processed_results = _processed_results_cache[results_hash]
        else:
            processed_results = process_scia_results_for_idea(results)
            # Cache the results (limit cache size to prevent memory issues)
            if len(_processed_results_cache) > 10:
                # Remove oldest entry
                oldest_key = next(iter(_processed_results_cache))
                del _processed_results_cache[oldest_key]
            _processed_results_cache[results_hash] = processed_results

        # Extract the specific DataFrame from the processed results
        if processed_results and isinstance(processed_results, dict):
            result_df = processed_results.get(result_type)

            if result_df is not None and not result_df.empty:
                table_data, headers = create_scia_table_data(result_df, result_type, units_mapping)
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
        # Fallback if processed results don't have expected structure
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
            [["Geen data", "SCIA resultaten verwerking gefaald", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]], column_headers=default_headers
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


def create_scia_1d_result_table(results: dict[str, Any], result_type: str) -> TableResult:
    """
    Create a VIKTOR TableResult from SCIA 1D analysis results for a specific result type.

    This version processes the raw 1D data by grouping rows with same name and dx values,
    merging Belasting values, and finding absolute max for force/moment columns.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param result_type: Type of results to extract ("SLS kar", "SLS freq", "ULS")
    :type result_type: str
    :returns: VIKTOR TableResult with processed 1D data
    :rtype: TableResult
    :raises Exception: If processing fails
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
                for key, value in table_data.items():
                    if isinstance(value, dict) and len(value) > 0:
                        integration_results = value
                        break

            if not integration_results:
                return TableResult(
                    [["Geen 1D data beschikbaar", f"Geen {result_type} resultaten gevonden", "N/A", "N/A", "N/A"]],
                    column_headers=["Info", "Status", "Detail", "Extra", "Opmerking"],
                )

        # Process the raw data with grouping and filtering
        df_processed = process_raw_1d_data_for_view(integration_results)

        if df_processed.empty:
            return TableResult(
                [["Geen data na verwerking", f"Geen {result_type} data na filtering", "N/A", "N/A", "N/A"]],
                column_headers=["Info", "Status", "Detail", "Extra", "Opmerking"],
            )

        # Convert and process data with unit conversion
        from .scia_unit_conversion import SciaUnitConverter

        # Create a 1D converter for proper unit handling
        converter = SciaUnitConverter("1D")

        # Get column order for display
        available_columns = df_processed.columns.tolist()

        # Create headers with units for common 1D force components
        headers_with_units = []
        for col in available_columns:
            col_lower = col.lower()
            if col_lower in ["n"]:
                headers_with_units.append(f"{col} ({converter.get_display_unit('N')})")
            elif col_lower in ["v_y", "vy"]:
                headers_with_units.append(f"{col} ({converter.get_display_unit('Vy')})")
            elif col_lower in ["v_z", "vz"]:
                headers_with_units.append(f"{col} ({converter.get_display_unit('Vz')})")
            elif col_lower in ["m_x", "mx"]:
                headers_with_units.append(f"{col} ({converter.get_display_unit('Mx')})")
            elif col_lower in ["m_y", "my"]:
                headers_with_units.append(f"{col} ({converter.get_display_unit('My')})")
            elif col_lower in ["m_z", "mz"]:
                headers_with_units.append(f"{col} ({converter.get_display_unit('Mz')})")
            elif col_lower in ["dx", "dy", "dz", "x", "y", "z"]:
                headers_with_units.append(f"{col} (m)")
            elif "kracht" in col_lower or "force" in col_lower:
                headers_with_units.append(f"{col} (kN)")
            elif "moment" in col_lower:
                headers_with_units.append(f"{col} (kNm)")
            elif "coord" in col_lower or "positie" in col_lower:
                headers_with_units.append(f"{col} (m)")
            else:
                # No unit for non-numeric columns (names, IDs, etc.)
                headers_with_units.append(col)

        headers = headers_with_units

        # Create table data from processed DataFrame
        table_rows = []
        for _, row in df_processed.iterrows():
            table_row = []
            for col in available_columns:
                value = row[col]

                # Check if value is numeric (int, float, or numeric string)
                is_numeric = False
                numeric_value = None

                if isinstance(value, (int, float)):
                    is_numeric = True
                    numeric_value = value
                elif isinstance(value, str) and value.strip():
                    try:
                        numeric_value = float(value)
                        is_numeric = True
                    except (ValueError, TypeError):
                        is_numeric = False

                if is_numeric and numeric_value is not None:
                    col_lower = col.lower()
                    # Use the converter for proper unit conversion and formatting
                    if col_lower in ["n"]:
                        formatted_value = f"{converter.convert_value(numeric_value, 'N'):.1f}"
                    elif col_lower in ["v_y", "vy"]:
                        formatted_value = f"{converter.convert_value(numeric_value, 'Vy'):.1f}"
                    elif col_lower in ["v_z", "vz"]:
                        formatted_value = f"{converter.convert_value(numeric_value, 'Vz'):.1f}"
                    elif col_lower in ["m_x", "mx"]:
                        formatted_value = f"{converter.convert_value(numeric_value, 'Mx'):.1f}"
                    elif col_lower in ["m_y", "my"]:
                        formatted_value = f"{converter.convert_value(numeric_value, 'My'):.1f}"
                    elif col_lower in ["m_z", "mz"]:
                        formatted_value = f"{converter.convert_value(numeric_value, 'Mz'):.1f}"
                    # Coordinates/distances: keep in meters
                    elif col_lower in ["dx", "dy", "dz", "x", "y", "z"] or "coord" in col_lower or "positie" in col_lower:
                        formatted_value = f"{numeric_value:.3f}"
                    # Pattern-based conversion for other force/moment columns
                    elif "kracht" in col_lower or "force" in col_lower:
                        formatted_value = f"{converter.convert_value(numeric_value, 'N'):.1f}"
                    elif "moment" in col_lower:
                        formatted_value = f"{converter.convert_value(numeric_value, 'Mx'):.1f}"
                    else:
                        # Other numeric values - format as-is
                        formatted_value = f"{numeric_value:.3f}"
                else:
                    formatted_value = str(value)
                table_row.append(formatted_value)

            table_rows.append(table_row)

        return TableResult(table_rows, column_headers=headers)

    except Exception as e:
        error_message = f"Error processing 1D results: {e!s}"
        return TableResult(
            [["Verwerkingsfout", error_message, "N/A", "N/A", "N/A"]], column_headers=["Error", "Details", "Extra1", "Extra2", "Extra3"]
        )

    except Exception as e:
        # Handle errors
        error_message = f"Error extracting {result_type} 1D data: {str(e)[:100]}..."
        default_headers = ["Error Type", "Message", "Details"]
        return TableResult([["1D Data Error", error_message, f"Failed for: {result_type}"]], column_headers=default_headers)
