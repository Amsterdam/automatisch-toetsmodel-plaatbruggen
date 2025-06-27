"""Module for creating the Plotly Figure for the Load Zones view."""

from typing import Any, TypedDict

import plotly.graph_objects as go
from plotly.colors import qualitative as qual_colors  # For default colors

from src.geometry.load_zone_geometry import LoadZoneDataRow, calculate_zone_bottom_y_coords

DEFAULT_PLOTLY_COLORS = qual_colors.Plotly


# --- TypedDicts for Argument Grouping ---
class BridgeBaseGeometry(TypedDict):
    """TypedDict for basic bridge geometric data used in plotting."""

    x_coords_d_points: list[float]
    y_coords_bridge_top_edge: list[float]
    y_coords_bridge_bottom_edge: list[list[float]]
    num_defined_d_points: int


class ZoneStylingDefaults(TypedDict):
    """TypedDict for zone styling defaults (appearance map and colors)."""

    zone_appearance_map: dict[str, dict[str, Any]]
    default_plotly_colors: list[str]


class ZoneBoundaryLineStyle(TypedDict):
    """TypedDict for styling parameters of zone boundary lines."""

    line_color: str
    sbs_line_thickness: float
    sbs_offset: float
    absolute_edge_thickness: float


class ZonePlottingGeometry(TypedDict):
    """TypedDict for common geometric data used in plotting individual zone components."""

    x_coords: list[float]  # Can be x_coords_d_points or specific zone x_coords
    y_coords_top: list[float]
    y_coords_bottom: list[float]
    # num_defined_d_points can be added if consistently needed by all users of this


class PlotPresentationDetails(TypedDict):
    """TypedDict for ancillary details related to plot presentation."""

    base_traces: list[go.Scatter] | None
    validation_messages: list[str] | None
    figure_title: str


# --- End TypedDicts ---

DEFAULT_ZONE_APPEARANCE_MAP: dict[str, dict[str, Any]] = {
    "Voetgangers": {
        "line_color": "silver",
        "pattern_shape": "+",
        "pattern_fgcolor": "silver",
        "fill_color": "rgba(192,192,192,0.2)",
        "pattern_solidity": 0.5,
    },
    "Fietsers": {
        "line_color": "crimson",
        "pattern_shape": "",
        "fill_color": "rgba(220,20,60,0.3)",
    },
    "Auto": {
        "line_color": "darkslategrey",
        "pattern_shape": "",
        "fill_color": "rgba(47,79,79,0.15)",
    },
    "Berm": {
        "line_color": "goldenrod",  # Or another suitable border color
        "pattern_shape": "x",  # Cross-hatch pattern
        "pattern_fgcolor": "darkgoldenrod",  # Color for the pattern lines
        "fill_color": "rgba(255, 255, 0, 0.3)",  # Yellow with transparency
        "pattern_solidity": 0.5,
    },
}


def get_zone_appearance_properties(
    zone_type_text: str,
    zone_idx: int,
    zone_appearance_map: dict[str, dict[str, Any]] = DEFAULT_ZONE_APPEARANCE_MAP,
    default_plotly_colors: list[str] = DEFAULT_PLOTLY_COLORS,
    is_exceeding_limits: bool = False,
) -> dict[str, Any]:
    """
    Determines visual properties for a load zone based on its type, index, and limits.

    Args:
        zone_type_text: The type of the load zone (e.g., "Voetgangers").
        zone_idx: The index of the load zone.
        zone_appearance_map: A mapping from zone type to visual properties.
        default_plotly_colors: A list of default colors to cycle through.
        is_exceeding_limits: True if the zone exceeds bridge geometric limits.

    Returns:
        A dictionary of Plotly visual properties for the zone.

    """
    if is_exceeding_limits:
        return {
            "line_color": "red",
            "fill_color": "rgba(255, 0, 0, 0.3)",
            "pattern_shape": "x",
            "pattern_fgcolor": "red",
            "pattern_solidity": 0.5,
        }
    appearance = zone_appearance_map.get(zone_type_text, {})
    return {
        "line_color": appearance.get("line_color", default_plotly_colors[zone_idx % len(default_plotly_colors)]),
        "fill_color": appearance.get(
            "fill_color",
            f"rgba({default_plotly_colors[zone_idx % len(default_plotly_colors)].lstrip('rgb(').rstrip(')')},0.1)"
            if default_plotly_colors[zone_idx % len(default_plotly_colors)].startswith("rgb(")
            else "rgba(200,200,200,0.1)",
        ),
        "pattern_shape": appearance.get("pattern_shape", ""),
        "pattern_fgcolor": appearance.get(
            "pattern_fgcolor", appearance.get("line_color", default_plotly_colors[zone_idx % len(default_plotly_colors)])
        ),
        "pattern_solidity": appearance.get("pattern_solidity", 0.4 if appearance.get("pattern_shape") else 0.0),
    }


def create_zone_fill_trace(
    x_coords: list[float],
    y_coords_top: list[float],
    y_coords_bottom: list[float],
    appearance_props: dict[str, Any],
) -> go.Scatter | None:
    """
    Creates a Plotly Scatter trace for the filled area of a load zone.

    Args:
        x_coords: X-coordinates for the zone boundaries.
        y_coords_top: Y-coordinates for the top boundary of the zone.
        y_coords_bottom: Y-coordinates for the bottom boundary of the zone.
        appearance_props: Dictionary of visual properties for the fill.

    Returns:
        A go.Scatter trace object for the fill, or None if inputs are invalid.

    """
    if not (x_coords and y_coords_top and y_coords_bottom):
        return None
    fill_x_coords = list(x_coords) + list(x_coords)[::-1]
    fill_y_coords = list(y_coords_top) + list(y_coords_bottom)[::-1]
    return go.Scatter(
        x=fill_x_coords,
        y=fill_y_coords,
        mode="none",
        fill="toself",
        fillcolor=appearance_props["fill_color"],
        fillpattern={
            "shape": appearance_props.get("pattern_shape", ""),
            "fgcolor": appearance_props.get("pattern_fgcolor"),
            "solidity": appearance_props.get("pattern_solidity"),
        },
        hoverinfo="skip",
        showlegend=False,
    )


def create_zone_boundary_line_traces(
    zone_idx: int,
    num_load_zones: int,
    geometry: ZonePlottingGeometry,
    style: ZoneBoundaryLineStyle,
) -> list[go.Scatter]:
    """
    Creates Plotly Scatter traces for the boundary lines of a load zone.
    Handles absolute edges for the first/last zones and shared edges between zones.
    """
    traces = []
    line_common = {"mode": "lines", "hoverinfo": "skip", "showlegend": False}
    x_coords = geometry["x_coords"]
    y_coords_top = geometry["y_coords_top"]
    y_coords_bottom = geometry["y_coords_bottom"]

    if zone_idx == 0:
        traces.append(
            go.Scatter(x=x_coords, y=y_coords_top, line={"color": style["line_color"], "width": style["absolute_edge_thickness"]}, **line_common)
        )
    else:
        traces.append(
            go.Scatter(
                x=x_coords,
                y=[y - style["sbs_offset"] for y in y_coords_top],
                line={"color": style["line_color"], "width": style["sbs_line_thickness"]},
                **line_common,
            )
        )
    if zone_idx == num_load_zones - 1:
        traces.append(
            go.Scatter(x=x_coords, y=y_coords_bottom, line={"color": style["line_color"], "width": style["absolute_edge_thickness"]}, **line_common)
        )
    else:
        traces.append(
            go.Scatter(
                x=x_coords,
                y=[y + style["sbs_offset"] for y in y_coords_bottom],
                line={"color": style["line_color"], "width": style["sbs_line_thickness"]},
                **line_common,
            )
        )
    return traces


def create_zone_main_label_annotation(
    zone_idx: int,
    zone_type_text: str,
    geometry: ZonePlottingGeometry,  # Using ZonePlottingGeometry
    x_offset: float = 2.0,
) -> go.layout.Annotation:
    """Creates the main label annotation for a load zone (e.g., 'bz1: Type')."""
    # Unpack relevant coordinates from geometry
    # Assuming x_coords in ZonePlottingGeometry corresponds to x_coords_d_points for this label
    x_coord_at_end = geometry["x_coords"][-1]
    y_top_end = geometry["y_coords_top"][-1]
    y_bottom_end = geometry["y_coords_bottom"][-1]

    return go.layout.Annotation(
        x=x_coord_at_end + x_offset,
        y=(y_top_end + y_bottom_end) / 2,
        text=f"<b>bz{zone_idx + 1}</b>: <i>{zone_type_text}</i>",
        showarrow=False,
        font={"size": 10, "color": "black"},
        xanchor="left",
        yanchor="middle",
    )


def create_zone_width_annotations(
    zone_param_data: LoadZoneDataRow,
    geometry: ZonePlottingGeometry,  # Using the new TypedDict
    num_defined_d_points: int,  # Still needed if not in ZonePlottingGeometry or differs
    zone_idx: int,
    num_load_zones: int,
) -> list[go.layout.Annotation]:
    """Creates width annotations for each D-section within a load zone."""
    annotations = []
    is_last_zone = zone_idx == num_load_zones - 1
    # Unpack geometry
    x_coords_d_points = geometry["x_coords"]  # Assuming x_coords in ZonePlottingGeometry is x_coords_d_points here
    y_coords_top_current_zone = geometry["y_coords_top"]
    y_coords_bottom_current_zone = geometry["y_coords_bottom"]

    for d_idx in range(num_defined_d_points):
        raw_width_val = zone_param_data.get(f"d{d_idx + 1}_width")
        width_val: float = raw_width_val if isinstance(raw_width_val, int | float) else 0.0

        current_zone_calculated_width = abs(y_coords_top_current_zone[d_idx] - y_coords_bottom_current_zone[d_idx])

        # Display width is either the parameter or the calculated remaining space for the last zone
        display_width = current_zone_calculated_width if is_last_zone else width_val

        if display_width > 0.01:
            annotations.append(
                go.layout.Annotation(
                    x=x_coords_d_points[d_idx],
                    y=(y_coords_top_current_zone[d_idx] + y_coords_bottom_current_zone[d_idx]) / 2.0,
                    text=f"{display_width:.2f}m",
                    showarrow=False,
                    font={"size": 8, "color": "black"},
                    bgcolor="rgba(255,255,255,0.6)",
                    borderpad=1,
                    xanchor="center",
                    yanchor="middle",
                )
            )
    return annotations


def build_load_zones_figure(
    load_zones_data_params: list[LoadZoneDataRow],
    bridge_geom: BridgeBaseGeometry,
    styling_defaults: ZoneStylingDefaults,
    presentation_details: PlotPresentationDetails,  # New grouped argument
) -> go.Figure:
    """Builds the Plotly Figure for the Load Zones view."""
    # Unpack presentation_details
    base_traces = presentation_details.get("base_traces")  # Use .get for optional keys if not all are required
    validation_messages = presentation_details.get("validation_messages")
    figure_title = presentation_details.get("figure_title", "Belastingzones")  # Provide default if get is used

    fig = go.Figure()
    if base_traces:
        for trace in base_traces:
            fig.add_trace(trace)

    all_annotations: list[go.layout.Annotation] = []
    # Unpack bridge_geom for easier access
    x_coords_d_points = bridge_geom["x_coords_d_points"]
    y_coords_bridge_bottom_edge: list[list[float]] = bridge_geom["y_coords_bridge_bottom_edge"]
    num_defined_d_points = bridge_geom["num_defined_d_points"]
    y_coords_bridge_top_edge = bridge_geom["y_coords_bridge_top_edge"]

    # Unpack styling_defaults
    zone_appearance_map = styling_defaults["zone_appearance_map"]
    default_plotly_colors = styling_defaults["default_plotly_colors"]

    # Unpack presentation details
    base_traces = presentation_details.get("base_traces")
    validation_messages = presentation_details.get("validation_messages")
    figure_title = presentation_details.get("figure_title", "Belastingzones")

    # Style for shared boundary lines
    sbs_line_thickness = 0.7
    sbs_offset = 0.003  # Small offset for shared lines
    absolute_edge_thickness = 1.5

    for zone_idx, zone_param_data in enumerate(load_zones_data_params):
        zone_type_text = zone_param_data.get("zone_type", f"Zone {zone_idx + 1}")
        # Ensure access via get for TypedDict compatibility
        zone_widths_per_d: list[float] = zone_param_data.get("zone_widths_per_d", [])  # type: ignore[assignment]
        y_coords_top_of_current_zone: list[float] = zone_param_data.get("y_coords_top_current_zone", [])  # type: ignore[assignment]

        if not zone_widths_per_d or not y_coords_top_of_current_zone:
            # Skip this zone if essential data is missing
            # This should not happen anymore since controller calculates these fields
            continue  # Skip this zone and continue to next iteration

        # Extract y_bridge_bottom_at_d_points from bridge_geom (list[list[float]] -> list[float])
        # Using the first element [0] of each [min_y, max_y] pair
        y_bridge_bottom_at_d_points = [bottom_edge[0] for bottom_edge in y_coords_bridge_bottom_edge]

        y_coords_bottom_of_current_zone: list[float] = calculate_zone_bottom_y_coords(
            zone_idx, len(load_zones_data_params), num_defined_d_points, y_coords_top_of_current_zone, y_bridge_bottom_at_d_points, zone_param_data
        )

        # Determine if any part of this zone is lower than the absolute bridge bottom
        # (e.g., due to errors or extreme parameters)
        exceeds_limits = any(
            y_coords_bottom_of_current_zone[d_idx]
            < y_coords_bridge_bottom_edge[d_idx][0] - 1e-3  # Compare y_coord of zone with min_y of bridge bottom
            for d_idx in range(num_defined_d_points)
        )
        # Check if the zone exceeds the top of the bridge
        exceeds_limits = exceeds_limits or any(
            y_coords_top_of_current_zone[d_idx] > y_coords_bridge_top_edge[d_idx] + 1e-3  # Compare y_coord of zone with y_coord of bridge top
            for d_idx in range(num_defined_d_points)
        )

        current_zone_exceeds_limits = exceeds_limits

        appearance_props = get_zone_appearance_properties(
            zone_type_text, zone_idx, zone_appearance_map, default_plotly_colors, is_exceeding_limits=current_zone_exceeds_limits
        )

        current_zone_geom_for_plotting: ZonePlottingGeometry = {
            "x_coords": x_coords_d_points,
            "y_coords_top": y_coords_top_of_current_zone,
            "y_coords_bottom": y_coords_bottom_of_current_zone,
        }

        fill_trace = create_zone_fill_trace(
            x_coords_d_points,  # Or current_zone_geom_for_plotting["x_coords"] if strictly adhering
            y_coords_top_of_current_zone,
            y_coords_bottom_of_current_zone,
            appearance_props,
        )
        if fill_trace:
            fig.add_trace(fill_trace)

        boundary_style: ZoneBoundaryLineStyle = {
            "line_color": appearance_props["line_color"],
            "sbs_line_thickness": sbs_line_thickness,
            "sbs_offset": sbs_offset,
            "absolute_edge_thickness": absolute_edge_thickness,
        }
        boundary_traces = create_zone_boundary_line_traces(
            zone_idx,
            len(load_zones_data_params),
            geometry=current_zone_geom_for_plotting,  # Pass the new geometry group
            style=boundary_style,
        )
        for trace in boundary_traces:
            fig.add_trace(trace)

        all_annotations.append(
            create_zone_main_label_annotation(
                zone_idx=zone_idx,
                zone_type_text=zone_type_text,
                geometry=current_zone_geom_for_plotting,  # Pass the grouped geometry
                # x_offset uses its default value
            )
        )

        all_annotations.extend(
            create_zone_width_annotations(
                zone_param_data,
                geometry=current_zone_geom_for_plotting,  # Pass the new geometry group
                num_defined_d_points=num_defined_d_points,  # Still pass if it varies or not part of current_zone_geom
                zone_idx=zone_idx,
                num_load_zones=len(load_zones_data_params),
            )
        )

    if validation_messages:
        consolidated_warning_text = "<br>".join([f"<b>Waarschuwing:</b> {msg}" for msg in validation_messages])
        all_annotations.append(
            go.layout.Annotation(
                text=consolidated_warning_text,
                align="left",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.01,
                y=-0.15,
                xanchor="left",
                yanchor="top",
                font={"color": "orangered", "size": 13},
                bgcolor="rgba(255, 224, 153, 0.85)",
                borderpad=0,
                width=800,
            )
        )

    fig.update_layout(
        title_text=figure_title,
        xaxis_title="Afstand (m)",
        yaxis_title="Breedte (m)",
        yaxis_scaleanchor="x",
        yaxis_scaleratio=1,
        annotations=all_annotations,
        plot_bgcolor="white",
        margin={"l": 50, "r": 150, "t": 50, "b": 150 if validation_messages else 50},
        showlegend=False,
        hovermode="closest",
    )
    return fig
