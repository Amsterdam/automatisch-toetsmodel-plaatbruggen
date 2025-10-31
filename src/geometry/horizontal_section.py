"""Module for creating horizontal section views of the bridge."""

from typing import TYPE_CHECKING

import plotly.graph_objects as go
import trimesh
from munch import Munch  # type: ignore[import-untyped]

from src.common.constants.geometry import (
    ANNOTATION_Y_OFFSET_CROSS_SECTION,
    ANNOTATION_Y_OFFSET_HORIZONTAL,
)
from src.geometry.model_creator import create_3d_model, create_cross_section

if TYPE_CHECKING:
    pass


def create_horizontal_section_annotations(params: dict | Munch, all_y: list[float]) -> list[go.layout.Annotation]:
    """
    Create Plotly annotation objects for the horizontal section view.

    :param params: Input parameters for the bridge dimensions.
    :type params: dict | Munch
    :param all_y: List of all y-coordinates in the section.
    :type all_y: list[float]
    :returns: List of Plotly annotation objects for the horizontal section.
    :rtype: list[go.layout.Annotation]
    """
    if not isinstance(params, Munch):
        params = Munch.fromDict(params)
    all_annotations = []
    only_zone2 = False
    if params.input.dimensions.horizontal_section_loc >= 0:
        only_zone2 = True

    row_labels = list(range(len(params.bridge_segments_array)))
    l_values = []
    l_values_cumulative = []
    l_cumulative = 0
    b_values_1 = []
    b_values_2 = []
    b_values_3 = []
    zone1_center_y = []
    zone2_center_y = []
    zone3_center_y = []

    for segment in params.bridge_segments_array:
        l_values.append(segment.l)
        l_cumulative += segment.l
        l_values_cumulative.append(l_cumulative)
        b_values_1.append(segment.bz1)
        b_values_2.append(segment.bz2)
        b_values_3.append(segment.bz3)
        zone1_center_y.append(segment.bz2 / 2 + segment.bz1 / 2)
        zone2_center_y.append(0)
        zone3_center_y.append(-segment.bz2 / 2 - segment.bz3 / 2)

    zone_center_x = [cum + val / 2 for cum, val in zip(l_values_cumulative, l_values[1:])]

    cross_section_labels = [
        go.layout.Annotation(
            x=cs_x,
            y=max(all_y) + ANNOTATION_Y_OFFSET_HORIZONTAL,
            text=f"<b>D-{i + 1}</b>",
            showarrow=False,
            font={"size": 15, "color": "black"},
            align="center",
            xanchor="center",
            yanchor="bottom",
            textangle=0,
            ax=0,
            ay=0,
        )
        for i, cs_x in zip(row_labels, l_values_cumulative)
    ]
    all_annotations.extend(cross_section_labels)

    zone_labels = []
    if not only_zone2:
        zone1_labels = [
            go.layout.Annotation(
                x=zcx,
                y=cz1,
                text=f"<b>Z1-{i + 1}</b>",
                showarrow=False,
                font={"size": 12, "color": "black"},
                align="center",
                xanchor="center",
                yanchor="middle",
                textangle=0,
                ax=0,
                ay=0,
            )
            for i, zcx, cz1 in zip(row_labels, zone_center_x, zone1_center_y)
        ]
        zone_labels.extend(zone1_labels)
    zone2_labels = [
        go.layout.Annotation(
            x=zcx,
            y=cz2,
            text=f"<b>Z2-{i + 1}</b>",
            showarrow=False,
            font={"size": 12, "color": "black"},
            align="center",
            xanchor="center",
            yanchor="middle",
            textangle=0,
            ax=0,
            ay=0,
        )
        for i, zcx, cz2 in zip(row_labels, zone_center_x, zone2_center_y)
    ]
    zone_labels.extend(zone2_labels)
    if not only_zone2:
        zone3_labels = [
            go.layout.Annotation(
                x=zcx,
                y=cz3,
                text=f"<b>Z3-{i + 1}</b>",
                showarrow=False,
                font={"size": 12, "color": "black"},
                align="center",
                xanchor="center",
                yanchor="middle",
                textangle=0,
                ax=0,
                ay=0,
            )
            for i, zcx, cz3 in zip(row_labels, zone_center_x, zone3_center_y)
        ]
        zone_labels.extend(zone3_labels)
    all_annotations.extend(zone_labels)

    dimension_annotations = [
        go.layout.Annotation(
            x=zcx,
            y=min(all_y) - ANNOTATION_Y_OFFSET_CROSS_SECTION,
            text=f"<b>l = {length}m</b>",
            showarrow=False,
            font={"size": 12, "color": "red"},
            align="center",
            xanchor="center",
            yanchor="top",
            textangle=0,
            ax=0,
            ay=0,
        )
        for length, zcx in zip(l_values[1:], zone_center_x)
    ]
    all_annotations.extend(dimension_annotations)

    if not only_zone2:
        width_annotations_zone1 = [
            go.layout.Annotation(
                x=zcx - 1,
                y=cz1,
                text=f"<b>b = {bz1}m</b>",
                showarrow=False,
                font={"size": 12, "color": "green"},
                align="center",
                xanchor="center",
                yanchor="middle",
                textangle=-90,
                ax=0,
                ay=0,
            )
            for zcx, cz1, bz1 in zip(l_values_cumulative, zone1_center_y, b_values_1)
        ]
        all_annotations.extend(width_annotations_zone1)
    width_annotations_zone2 = [
        go.layout.Annotation(
            x=zcx - 1,
            y=cz2,
            text=f"<b>b = {bz2}m</b>",
            showarrow=False,
            font={"size": 12, "color": "green"},
            align="center",
            xanchor="center",
            yanchor="middle",
            textangle=-90,
            ax=0,
            ay=0,
        )
        for zcx, cz2, bz2 in zip(l_values_cumulative, zone2_center_y, b_values_2)
    ]
    if not only_zone2:
        width_annotations_zone3 = [
            go.layout.Annotation(
                x=zcx - 1,
                y=cz3,
                text=f"<b>b = {bz3}m</b>",
                showarrow=False,
                font={"size": 12, "color": "green"},
                align="center",
                xanchor="center",
                yanchor="middle",
                textangle=-90,
                ax=0,
                ay=0,
            )
            for zcx, cz3, bz3 in zip(l_values_cumulative, zone3_center_y, b_values_3)
        ]
        all_annotations.extend(width_annotations_zone3)
    all_annotations.extend(width_annotations_zone2)
    return all_annotations


def create_horizontal_section_view(params: dict | Munch, section_loc: float) -> go.Figure:
    """
    Creates a 2D horizontal section view of the bridge using Plotly.
    This function creates a 2D representation of the bridge's horizontal section by:
    1. Creating a 3D model of the bridge
    2. Slicing it with a horizontal plane at the specified height
    3. Converting the resulting section into a 2D plot showing length (x) vs width (y).

    Args:
        params (dict | Munch): Input parameters for the bridge dimensions.
        section_loc (float): Location of the horizontal section along the z-axis.

    Returns:
        go.Figure: A 2D representation of the horizontal section.

    """
    if isinstance(params, dict) and not isinstance(params, Munch):
        params = Munch.fromDict(params)
    # Generate the 3D model without coordinate axes
    scene = create_3d_model(params, axes=False)
    combined_mesh = trimesh.util.concatenate(scene.geometry.values())

    # Define the slicing plane for the horizontal section
    # The plane is horizontal (normal to z-axis) at the specified height
    plane_origin = [0, 0, section_loc]
    plane_normal = [0, 0, 1]

    # Create the section by slicing the 3D model
    combined_scene_2d = create_cross_section(combined_mesh, plane_origin, plane_normal, axes=False)
    combined_scene_2d_mesh = trimesh.util.concatenate(combined_scene_2d.geometry.values())

    # Extract vertices and entities from the sliced mesh
    vertices = combined_scene_2d_mesh.vertices
    entities = combined_scene_2d_mesh.entities

    # Initialize the Plotly figure
    fig = go.Figure()

    # Collect all x and y coordinates to determine the plot range
    all_x = []
    all_y = []
    for entity in entities:
        points = entity.points
        for point in points:
            all_x.append(vertices[point][0])
            all_y.append(vertices[point][1])

    # Calculate plot ranges with padding for better visualization
    x_range = [min(all_x) - 2, max(all_x) + 2]
    y_range = [min(all_y) - 2, max(all_y) + 2]

    # Create line traces for each entity in the section
    for entity in entities:
        x = []
        y = []
        points = entity.points
        for point in points:
            x.append(vertices[point][0])
            y.append(vertices[point][1])

        # Add each line segment to the plot
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                line={"color": "black"},  # Consistent black color for all lines
            )
        )

    # Prepare annotations using the new function
    all_annotations = create_horizontal_section_annotations(params, all_y)

    # Configure the plot layout with appropriate ranges and labels
    fig.update_layout(
        title="Horizontale doorsnede (Horizontal Section)",
        showlegend=False,
        autosize=True,
        xaxis={"range": x_range, "constrain": "domain", "title": "X-as - Lengte [m]"},
        yaxis={"range": y_range, "scaleanchor": "x", "scaleratio": 1, "title": "Y-as - Breedte [m]"},
        margin={"l": 50, "r": 50, "t": 50, "b": 50},
        annotations=all_annotations,
    )

    return fig
