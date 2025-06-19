"""Module for creating the Plotly Figure for the Top View of the bridge."""

from typing import Any

import plotly.graph_objects as go

# Assuming create_text_annotations_from_data is in src.common.plot_utils
from src.common.plot_utils import create_text_annotations_from_data


def _add_zone_polygon_traces(fig: go.Figure, zone_polygons_data: list[dict[str, Any]]) -> None:
    """Adds structural zone polygon traces to the figure."""
    for poly in zone_polygons_data:
        vertices = poly.get("vertices", [])
        if vertices:
            x_coords = [v[0] for v in vertices] + [vertices[0][0]]
            y_coords = [v[1] for v in vertices] + [vertices[0][1]]
            fig.add_trace(
                go.Scatter(
                    x=x_coords,
                    y=y_coords,
                    mode="lines",
                    fill="toself",
                    fillcolor=poly.get("color", "rgba(128,128,128,0.1)"),
                    line={"width": 0},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )


def _add_bridge_outline_traces(fig: go.Figure, bridge_lines_data: list[dict[str, Any]]) -> None:
    """Adds bridge outline traces to the figure."""
    for i, line_segment in enumerate(bridge_lines_data):
        fig.add_trace(
            go.Scatter(
                x=[line_segment["start"][0], line_segment["end"][0]],
                y=[line_segment["start"][1], line_segment["end"][1]],
                mode="lines",
                line={"color": "blue", "width": 2},
                hoverinfo="none",
                showlegend=False,
                name=f"Bridge Outline Segment {i}",
            )
        )


def _create_zone_label_annotations(zone_annotations_data: list[dict[str, Any]]) -> list[go.layout.Annotation]:
    """Creates annotations for structural zone labels."""
    return [
        go.layout.Annotation(
            x=ann["x"],
            y=ann["y"],
            text=f"<b>{ann['text']}</b>",
            showarrow=False,
            font={"size": 14, "color": "DarkSlateGray"},
            ax=0,
            ay=0,
        )
        for ann in zone_annotations_data
    ]


def _create_dimension_text_annotations(dimension_texts_data: list[dict[str, Any]]) -> list[go.layout.Annotation]:
    """Creates annotations for dimension value labels."""
    annotations = []
    for dim_text in dimension_texts_data:
        text_align = "center"
        xanchor = "center"
        yanchor = "middle"
        current_textangle = dim_text.get("textangle", 0)

        if current_textangle == 180:
            xanchor = "right"
            yanchor = "middle"
            text_align = "right"
        elif current_textangle in (90, -90):
            xanchor = "center"
            yanchor = "middle"
            text_align = "center"
        elif dim_text.get("type") == "length":
            text_align = "center"
            xanchor = "center"
            yanchor = "bottom"
        else:  # Default for width type usually
            text_align = "left"
            xanchor = "left"
            yanchor = "middle"

        annotations.append(
            go.layout.Annotation(
                x=dim_text["x"],
                y=dim_text["y"],
                text=f"<b>{dim_text['text']}</b>",
                showarrow=False,
                font={"size": 12, "color": "red"},
                align=text_align,
                xanchor=xanchor,
                yanchor=yanchor,
                textangle=current_textangle,
                ax=0,
                ay=0,
            )
        )
    return annotations


def _create_validation_warning_annotations(validation_messages: list[str]) -> list[go.layout.Annotation]:
    """Creates annotations for validation warning messages."""
    annotations = []
    if validation_messages:
        consolidated_warning_text = "<br>".join([f"<b>Waarschuwing (Belastingzones):</b> {msg}" for msg in validation_messages])
        annotations.append(
            go.layout.Annotation(
                text=consolidated_warning_text,
                align="left",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.0,
                y=-0.12,
                xanchor="left",
                yanchor="top",
                font={"color": "orangered", "size": 13},
                bgcolor="rgba(255, 224, 153, 0.85)",
                borderpad=0,
                width=900,
            )
        )
    return annotations


def _create_north_arrow_annotation() -> list[go.layout.Annotation]:
    """Creates a horizontal span arrow annotation above the plot title."""
    return [
        go.layout.Annotation(
            text="⥊",  # Unicode right-pointing double-headed arrow
            x=0.9,  # Center of the plot
            y=1.05,  # Just above the title
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"size": 75, "color": "black"},
            align="center",
            xanchor="center",
            yanchor="middle",
        )
    ]


def build_top_view_figure(top_view_geometric_data: dict[str, Any], validation_messages: list[str] | None = None) -> go.Figure:
    """
    Builds the Plotly Figure for the 2D Top View of the bridge deck.

    Args:
        top_view_geometric_data: A dictionary containing pre-calculated geometric data.
        validation_messages: A list of warning message strings to display on the plot.

    Returns:
        go.Figure: The Plotly figure object.

    """
    if validation_messages is None:
        validation_messages = []

    fig = go.Figure()
    all_annotations: list[go.layout.Annotation] = []

    _add_zone_polygon_traces(fig, top_view_geometric_data.get("zone_polygons", []))
    _add_bridge_outline_traces(fig, top_view_geometric_data.get("bridge_lines", []))

    all_annotations.extend(_create_zone_label_annotations(top_view_geometric_data.get("zone_annotations", [])))
    all_annotations.extend(_create_dimension_text_annotations(top_view_geometric_data.get("dimension_texts", [])))
    # Add span arrows
    all_annotations.extend(_create_north_arrow_annotation())

    cs_labels_data = top_view_geometric_data.get("cross_section_labels", [])
    if cs_labels_data:
        all_annotations.extend(
            create_text_annotations_from_data(
                label_data=cs_labels_data,
                font_size=15,
                font_color="black",
                align="center",
                xanchor="center",
                yanchor="bottom",
            )
        )

    all_annotations.extend(_create_validation_warning_annotations(validation_messages))

    fig.update_layout(
        title="Bovenaanzicht (Top View)",
        xaxis_title="Length (m)",
        yaxis_title="Width (m)",
        showlegend=False,
        autosize=True,
        hovermode="closest",
        yaxis={"scaleanchor": "x", "scaleratio": 1},
        annotations=all_annotations,
        margin={"l": 20, "r": 20, "t": 100, "b": 20},
        plot_bgcolor="white",
    )
    return fig
