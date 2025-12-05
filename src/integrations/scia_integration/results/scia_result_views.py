"""Functions for creating SCIA result views for VIKTOR tables."""

from typing import TYPE_CHECKING, Any

import pandas as pd
from viktor.views import PlotlyResult, TableResult

if TYPE_CHECKING:
    from src.integrations.scia_integration.results.scia_unit_conversion import SciaUnitConverter

from src.integrations.scia_integration.constants.results import (
    CS_TABLE_TYPES,
    MAX_ERROR_MESSAGE_LENGTH,
)

from .scia_results_processor import (
    get_processed_results_with_cache,
)


def get_available_cs_coordinates(
    results: dict[str, Any],
    result_type: str,
    direction: str,
    bridge_segments: list[Any] | None = None,
) -> list[float]:
    """
    Get available coordinates for cross sections from SCIA CS results.

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param result_type: Type of results ("ULS" or "SLS freq")
    :type result_type: str
    :param direction: Direction for cross sections ("X-richting" or "Y-richting")
    :type direction: str
    :param bridge_segments: Optional list of bridge segments for zone mapping
    :type bridge_segments: list[Any] | None
    :returns: Sorted list of unique coordinates
    :rtype: list[float]
    """
    from .scia_results_processor import process_scia_cs_results

    try:
        # Process CS results to get the DataFrame
        cs_results = process_scia_cs_results(results, bridge_segments=bridge_segments)
        df_cs_results = cs_results.get(result_type, pd.DataFrame())

        if df_cs_results.empty:
            return []

        # Determine coordinate axis: X-richting filters on Y coordinate, Y-richting filters on X coordinate
        coord_index = 0 if direction == "Y-richting" else 1  # 0=X, 1=Y, 2=Z

        # Extract unique coordinates
        coordinates = set()
        for _, row in df_cs_results.iterrows():
            coords = row.get("coords_xyz", (0, 0, 0))
            try:
                coord_value = float(coords[coord_index])
                coordinates.add(coord_value)
            except (ValueError, TypeError, IndexError):
                continue

        # Return sorted list
        return sorted(coordinates)

    except Exception:
        return []


def create_scia_cs_plotly_visualization(  # noqa: C901, PLR0913, PLR0911, PLR0912, PLR0915
    results: dict[str, Any],
    *,
    result_type: str,
    direction: str,
    max_type: str,
    position_index: int,
    bridge_segments: list[Any] | None = None,
) -> PlotlyResult:
    """
    Create a Plotly visualization with 4 subplots for SCIA CS results.

    The visualization shows 4 subplots stacked vertically:
    1. Vx and Vy (shear forces)
    2. MxD+ and MxD- (moments in x-direction)
    3. MyD+ and MyD- (moments in y-direction)
    4. NxD and NyD (normal forces)

    :param results: SCIA analysis results dictionary
    :type results: dict[str, Any]
    :param result_type: Type of results ("ULS" or "SLS freq")
    :type result_type: str
    :param direction: Direction for cross sections ("X-richting" or "Y-richting")
    :type direction: str
    :param max_type: Component to maximize for ("v_x", "v_y", "m_xD+", etc.)
    :type max_type: str
    :param position_index: Index of the cross section to display (0-based)
    :type position_index: int
    :param bridge_segments: Optional list of bridge segments for zone mapping
    :type bridge_segments: list[Any] | None
    :returns: PlotlyResult with 4 subplots
    :rtype: PlotlyResult
    """
    from plotly import graph_objects as go
    from plotly.subplots import make_subplots
    from viktor.views import PlotlyResult

    from .scia_results_processor import process_scia_cs_results

    try:
        # Try to use cached dataframe first
        cache_key = "df_cs_uls" if result_type == "ULS" else "df_cs_sls_freq"
        df_cs_results = results.get(cache_key)

        # If not in cache, process on demand
        if df_cs_results is None or df_cs_results.empty:
            cs_results = process_scia_cs_results(results, bridge_segments=bridge_segments)
            df_cs_results = cs_results.get(result_type, pd.DataFrame())

        if df_cs_results.empty:
            # Return empty plot with message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Geen {result_type} data beschikbaar",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 16},
            )
            fig.update_layout(title=f"SCIA CS {result_type} Visualisatie")
            return PlotlyResult(fig.to_json())

        # Determine which coordinate to filter on (the FIXED coordinate)
        # X-richting: cross-sections perpendicular to X, so Y is FIXED (filter on Y, coord_index=1)
        # Y-richting: cross-sections perpendicular to Y, so X is FIXED (filter on X, coord_index=0)
        coord_index = 1 if direction == "X-richting" else 0  # 0=X, 1=Y, 2=Z

        # Extract all unique positions for this direction
        unique_positions = []
        for _, row in df_cs_results.iterrows():
            coords = row.get("coords_xyz", (0, 0, 0))
            try:
                coord_value = float(coords[coord_index])
                if coord_value not in unique_positions:
                    unique_positions.append(coord_value)
            except (ValueError, TypeError, IndexError):
                continue

        # Sort positions
        unique_positions.sort()

        if not unique_positions:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Geen coördinaten gevonden voor {direction}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 16},
            )
            fig.update_layout(title=f"SCIA CS {result_type} Visualisatie")
            return PlotlyResult(fig.to_json())

        # Check if position_index is valid
        if position_index < 0 or position_index >= len(unique_positions):
            fig = go.Figure()
            fig.add_annotation(
                text=f"Doorsnede nummer {position_index} niet beschikbaar. Beschikbare doorsnedes: 0 tot {len(unique_positions) - 1}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 14},
            )
            fig.update_layout(title=f"SCIA CS {result_type} Visualisatie")
            return PlotlyResult(fig.to_json())

        # Get the actual position for this index
        position = unique_positions[position_index]
        tolerance = 0.01  # 1cm tolerance for coordinate matching

        # CRITICAL: For display in title, we need the FIXED coordinate, not the varying one
        # X-richting: we vary along X (plot X-axis), so Y is fixed -> display Y coordinate
        # Y-richting: we vary along Y (plot Y-axis), so X is fixed -> display X coordinate
        if direction == "X-richting":
            # X-richting: filter on Y coordinate (coord_index=1), display this Y value
            display_coord_label = "Y"
            display_coord_value = position
        else:
            # Y-richting: filter on X coordinate (coord_index=0), display this X value
            display_coord_label = "X"
            display_coord_value = position

        # Filter data based on direction and position
        filtered_rows = []
        for idx, row in df_cs_results.iterrows():
            coords = row.get("coords_xyz", (0, 0, 0))
            # Safely convert coordinate to float
            try:
                coord_value = float(coords[coord_index])
                if abs(coord_value - position) < tolerance:
                    filtered_rows.append(row)
            except (ValueError, TypeError, IndexError):
                # Skip rows with invalid coordinates
                continue

        print(f"DEBUG: Filtered {len(filtered_rows)} rows at position {position:.2f}m (tolerance={tolerance})")
        
        if not filtered_rows:
            # Return empty plot with message
            print(f"DEBUG: No rows found after filtering for position {position:.2f}m")
            fig = go.Figure()
            fig.add_annotation(
                text=f"Geen data gevonden bij {direction} positie {position:.2f}m",
                xref="paper",
                yref="paper",
                x=0.5,
                # Skip rows with invalid coordinates
                continue

        if not filtered_rows:
            # Return empty plot with message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Geen data gevonden bij {direction} positie {position:.2f}m",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
        # Filter for max_type: get rows where max_for_column matches max_type
        df_max = df_filtered[df_filtered["max_for_column"] == max_type].copy()

        if df_max.empty:
            # Return empty plot with message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Geen data gevonden voor maximale waarde {max_type}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 16},
            )
            fig.update_layout(title=f"SCIA CS {result_type} Visualisatie")
            return PlotlyResult(fig.to_json()) cross-sections perpendicular to Y, varying along Y

        if direction == "X-richting":
            # X-richting: plot along X (length), so we vary X coordinate
            other_coord_index = 0  # X-coordinate varies
            plot_along_length = True
        else:
            # Y-richting: plot along Y (width), so we vary Y coordinate
            other_coord_index = 1  # Y-coordinate varies
            plot_along_length = False

        # Helper function to safely convert single value to float - NO MODIFICATIONS
        def safe_float_convert(val: Any) -> float:  # noqa: ANN401
            """Convert value to float, handling various input types. Returns RAW value from table."""
            try:
                # If already numeric, return as-is
                if isinstance(val, (int, float)):
                    return float(val)
                # If string, convert directly (values already have dot as decimal)
                if isinstance(val, str):
                    val_cleaned = val.strip()
                    if val_cleaned:
                        return float(val_cleaned)
                    return 0.0
                # Try direct conversion for other types
                return float(val)
            except (ValueError, TypeError, AttributeError):
                return 0.0  # Default to 0 if conversion fails

        # Extract sort coordinate safely from coords_xyz tuple
        df_max["sort_coord"] = df_max["coords_xyz"].apply(
            lambda c: safe_float_convert(c[other_coord_index]) if isinstance(c, (list, tuple)) and len(c) > other_coord_index else 0.0
        )
        df_max = df_max.sort_values("sort_coord")

        # Extract x-axis values (the varying coordinate) - this represents position along bridge
        x_values = df_max["sort_coord"].tolist()

        # Set appropriate labels based on what we're plotting along
        if plot_along_length:
            # Plotting along X (length)
            x_label = "Positie langs brug (X) [m]"
            direction_text = "langsdoorsnede"
        else:
            # Plotting along Y (width)
            x_label = "Positie over breedte (Y) [m]"
            direction_text = "dwarsdoorsnede"

        # Calculate total bridge length/width for x-axis range
        if bridge_segments and len(bridge_segments) > 0:
            if plot_along_length:
                # Plotting along length: sum all segment lengths (skip first segment with l=0)
                x_range_max = sum(safe_float_convert(getattr(seg, "l", 0)) for seg in bridge_segments[1:])
                x_range_min = 0.0
            else:
                # Plotting along width: calculate Y-coordinate range from bz1, bz2, bz3
                # Y=0 is at center of bz2, Y_min = -(bz3+bz2/2), Y_max = bz1+bz2/2
                max_bz2 = max(safe_float_convert(getattr(seg, "bz2", 0)) for seg in bridge_segments)
                max_bz1 = max(safe_float_convert(getattr(seg, "bz1", 0)) for seg in bridge_segments)
                max_bz3 = max(safe_float_convert(getattr(seg, "bz3", 0)) for seg in bridge_segments)
                x_range_min = -(max_bz3 + max_bz2 / 2)
                x_range_max = max_bz1 + max_bz2 / 2
        # Fallback: use data min/max with small margin
        elif x_values:
            data_min = min(x_values)
            data_max = max(x_values)
            margin = (data_max - data_min) * 0.05 if data_max > data_min else 1
            x_range_min = data_min - margin
            x_range_max = data_max + margin
        else:
            x_range_min = 0
            x_range_max = 10

        # Extract RAW force/moment values from DataFrame and convert from N to kN, Nm to kNm
        # SCIA provides forces in Newton (N) and moments in Newton-meter (Nm)
        # We convert to kilonewton (kN) and kilonewton-meter (kNm) for better readability
        def extract_column_as_floats(df: pd.DataFrame, col_name: str, is_moment: bool = False) -> list[float]:  # noqa: ARG001
            """
            Extract column values, convert to floats, and apply unit conversion.

            Args:
                df: DataFrame to extract from
                col_name: Column name
                is_moment: True for moments (Nm to kNm), False for forces (N to kN)

            Returns:
                List of converted values in kN or kNm

            """
            if col_name not in df.columns:
                return [0.0] * len(df)
            # Convert from N to kN or Nm to kNm by dividing by 1000
            return [safe_float_convert(val) / 1000.0 for val in df[col_name]]

        # Shear forces: N to kN
        v_x_values = extract_column_as_floats(df_max, "v_x", is_moment=False)
        v_y_values = extract_column_as_floats(df_max, "v_y", is_moment=False)
        # Moments: Nm to kNm
        m_xd_plus_values = extract_column_as_floats(df_max, "m_xD+", is_moment=True)
        m_xd_minus_values = extract_column_as_floats(df_max, "m_xD-", is_moment=True)
        m_yd_plus_values = extract_column_as_floats(df_max, "m_yD+", is_moment=True)
        m_yd_minus_values = extract_column_as_floats(df_max, "m_yD-", is_moment=True)
        # Normal forces: N to kN
        n_xd_values = extract_column_as_floats(df_max, "n_xD", is_moment=False)
        n_yd_values = extract_column_as_floats(df_max, "n_yD", is_moment=False)

        # Create subplots: 4 rows, 1 column - ALWAYS create all 4 subplots
        fig = make_subplots(
            rows=4,
            cols=1,
            subplot_titles=(
                "Dwarskrachten (Vx, Vy)",
                "Momenten X-richting (MxD+, MxD-)",
                "Momenten Y-richting (MyD+, MyD-)",
                "Normaalkrachten (NxD, NyD)",
            ),
            vertical_spacing=0.08,
            shared_xaxes=True,
        )

        # Subplot 1: Vx and Vy - ALWAYS show even if values are zero
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=v_x_values,
                mode="lines+markers",
                name="Vx",
                line={"color": "blue", "width": 2},
                marker={"size": 6},
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=v_y_values,
                mode="lines+markers",
                name="Vy",
                line={"color": "lightblue", "width": 2},
                marker={"size": 6},
            ),
            row=1,
            col=1,
        )
        fig.update_yaxes(title_text="Dwarskracht [kN/m]", row=1, col=1)
        fig.update_xaxes(range=[x_range_min, x_range_max], row=1, col=1)

        # Subplot 2: MxD+ and MxD- - ALWAYS show even if values are zero
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=m_xd_plus_values,
                mode="lines+markers",
                name="MxD+",
                line={"color": "red", "width": 2},
                marker={"size": 6},
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=m_xd_minus_values,
                mode="lines+markers",
                name="MxD-",
                line={"color": "darkred", "width": 2},
                marker={"size": 6},
            ),
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="Moment [kNm/m]", row=2, col=1)
        fig.update_xaxes(range=[x_range_min, x_range_max], row=2, col=1)

        # Subplot 3: MyD+ and MyD- - ALWAYS show even if values are zero
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=m_yd_plus_values,
                mode="lines+markers",
                name="MyD+",
                line={"color": "green", "width": 2},
                marker={"size": 6},
            ),
            row=3,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=m_yd_minus_values,
                mode="lines+markers",
                name="MyD-",
                line={"color": "darkgreen", "width": 2},
                marker={"size": 6},
            ),
            row=3,
            col=1,
        )
        fig.update_yaxes(title_text="Moment [kNm/m]", row=3, col=1)
        fig.update_xaxes(range=[x_range_min, x_range_max], row=3, col=1)

        # Subplot 4: NxD and NyD - ALWAYS show even if values are zero
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=n_xd_values,
                mode="lines+markers",
                name="NxD",
                line={"color": "purple", "width": 2},
                marker={"size": 6},
            ),
            row=4,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=n_yd_values,
                mode="lines+markers",
                name="NyD",
                line={"color": "magenta", "width": 2},
                marker={"size": 6},
            ),
            row=4,
            col=1,
        )
        fig.update_yaxes(title_text="Normaalkracht [kN/m]", row=4, col=1)
        fig.update_xaxes(range=[x_range_min, x_range_max], row=4, col=1)

        # Update x-axis label (only on bottom subplot)
        fig.update_xaxes(title_text=x_label, row=4, col=1)

        # Update overall layout
        max_info = f"{display_coord_label}={display_coord_value:.2f}m"
        title_text = (
            f"SCIA CS {result_type} - {direction_text}, doorsnede {position_index + 1}/{len(unique_positions)} ({max_info}), voor max {max_type}"
        )
        fig.update_layout(
            title_text=title_text,
            height=1200,  # Tall enough for 4 subplots
            showlegend=True,
            hovermode="x unified",
        )

        fig.update_layout(
            title_text=title_text,
            height=1200,  # Tall enough for 4 subplots
            showlegend=True,
            hovermode="x unified",
        )

        return PlotlyResult(fig.to_json())

    except Exception as e:
        import traceback

        traceback.print_exc()
        # Return error plot
            y=0.5,
            showarrow=False,
            font={"size": 14},
        )
        fig.update_layout(title="SCIA CS Visualisatie - Fout")
        return PlotlyResult(fig.to_json())


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
        if isinstance(coords, list | tuple) and len(coords) >= 3:
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
            "Bron",
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


def _convert_force_value_safe(converter: "SciaUnitConverter", value: float, component: str) -> str | float:
    """Safely convert a force/moment value to display units, returning numeric value or 'N/A'."""
    try:
        return round(converter.convert_value(value, component), 2)
    except (ValueError, TypeError):
        return "N/A"


def create_scia_cs_table_data(processed_cs_df: pd.DataFrame, result_type: str) -> tuple[list[list[str | float]], list[str]]:
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
        no_data_row: list[str | float] = [f"Geen {result_type} data", *(["N/A"] * (len(headers) - 1))]
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
        
        # Get bron (data source)
        bron = row.get("Bron", "SCIA")

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

        # Convert values to display units (without unit strings for sortability)
        v_x_val = _convert_force_value_safe(converter, v_x, "v_x")
        v_y_val = _convert_force_value_safe(converter, v_y, "v_y")
        m_xd_plus_val = _convert_force_value_safe(converter, m_xd_plus, "m_xD+")
        m_xd_minus_val = _convert_force_value_safe(converter, m_xd_minus, "m_xD-")
        m_yd_plus_val = _convert_force_value_safe(converter, m_yd_plus, "m_yD+")
        m_yd_minus_val = _convert_force_value_safe(converter, m_yd_minus, "m_yD-")
        n_xd_val = _convert_force_value_safe(converter, n_xd, "n_xD")
        n_yd_val = _convert_force_value_safe(converter, n_yd, "n_yD")

        # Build row data - order must match headers exactly
        if has_zone_column:
            # With zone: Name, Zone, Coordinates, Belasting, Bron, Max For, Vx, Vy, MxD+, MxD-, MyD+, MyD-, NxD, NyD (14 columns)
            zone = row.get("zone", "N/A")
            row_data = [
                str(name),
                str(zone),
                coords,
                str(belasting),
                str(bron),
                str(max_for_column),
                v_x_val,
                v_y_val,
                m_xd_plus_val,
                m_xd_minus_val,
                m_yd_plus_val,
                m_yd_minus_val,
                n_xd_val,
                n_yd_val,
            ]
        else:
            # Without zone: Name, Coordinates, Belasting, Bron, Max For, Vx, Vy, MxD+, MxD-, MyD+, MyD-, NxD, NyD (13 columns)
            row_data = [
                str(name),
                coords,
                str(belasting),
                str(bron),
                str(max_for_column),
                v_x_val,
                v_y_val,
                m_xd_plus_val,
                m_xd_minus_val,
                m_yd_plus_val,
                m_yd_minus_val,
                n_xd_val,
                n_yd_val,
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
        # Try to use cached dataframe first
        cache_key = "df_cs_uls" if table_type == "ULS" else "df_cs_sls_freq"
        processed_cs_df = results.get(cache_key)

        # If not in cache, process on demand
        if processed_cs_df is None or processed_cs_df.empty:
            cs_results = process_scia_cs_results(results, bridge_segments=bridge_segments)
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
        # Try to use cached dataframe first
        df_envelope = results.get("df_cs_envelope")

        # If not in cache, process on demand
        if df_envelope is None or df_envelope.empty:
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
            "Bron",
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
            bron = row.get("Bron", "SCIA")
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

            # Convert values to display units (without unit strings for sortability)
            v_x_val = _convert_force_value_safe(converter, v_x, "v_x")
            v_y_val = _convert_force_value_safe(converter, v_y, "v_y")
            m_xd_plus_val = _convert_force_value_safe(converter, m_xd_plus, "m_xD+")
            m_xd_minus_val = _convert_force_value_safe(converter, m_xd_minus, "m_xD-")
            m_yd_plus_val = _convert_force_value_safe(converter, m_yd_plus, "m_yD+")
            m_yd_minus_val = _convert_force_value_safe(converter, m_yd_minus, "m_yD-")
            n_xd_val = _convert_force_value_safe(converter, n_xd, "n_xD")
            n_yd_val = _convert_force_value_safe(converter, n_yd, "n_yD")

            row_data = [
                str(zone),
                str(result_type),
                str(name),
                coords,
                str(belasting),
                str(bron),
                str(max_for_column),
                v_x_val,
                v_y_val,
                m_xd_plus_val,
                m_xd_minus_val,
                m_yd_plus_val,
                m_yd_minus_val,
                n_xd_val,
                n_yd_val,
            ]

            table_data.append(row_data)

        return TableResult(table_data, column_headers=headers)

    except Exception as e:
        import traceback

        traceback.print_exc()
        error_message = f"Fout bij verwerken CS envelopes: {str(e)[:100]}..."
        return TableResult(
            [["Fout", error_message, "", "", "", "", "", "", "", "", "", "", "", "", ""]],
            column_headers=[
                "Zone",
                "Type",
                "Naam",
                "Coördinaten",
                "Belasting",
                "Bron",
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
