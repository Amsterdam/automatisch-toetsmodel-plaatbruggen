"""Module for creating longitudinal section views of the bridge."""

from typing import TYPE_CHECKING

import plotly.graph_objects as go
import trimesh

from src.common.constants.geometry import (
    ANNOTATION_Y_OFFSET_CROSS_SECTION,
    ANNOTATION_Y_OFFSET_HORIZONTAL,
    DIMENSION_TEXT_X_OFFSET,
)
from src.geometry.model_creator import create_3d_model, create_cross_section

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


def create_longitudinal_section(params: "BridgeParametrization", section_loc: float) -> go.Figure:
    """
    Creates a 2D longitudinal section view of the bridge using Plotly.
    This function creates a 2D representation of the bridge's longitudinal section by:
    1. Creating a 3D model of the bridge
    2. Slicing it with a vertical plane parallel to the x-z plane
    3. Converting the resulting cross-section into a 2D plot showing length (x) vs height (z).

    Args:
        params (dict | Munch): Input parameters for the bridge dimensions.
        section_loc (float): Location of the longitudinal section along the y-axis.

    Returns:
        go.Figure: A 2D representation of the longitudinal section.

    """
    # Generate the 3D model without coordinate axes
    scene = create_3d_model(params, axes=False)
    combined_mesh = trimesh.util.concatenate(scene.geometry.values())

    # Define the slicing plane for the longitudinal section
    # The plane is vertical (normal to y-axis) at the specified location
    plane_origin = [0, section_loc, 0]
    plane_normal = [0, 1, 0]

    # Create the cross-section by slicing the 3D model
    combined_scene_2d = create_cross_section(combined_mesh, plane_origin, plane_normal, axes=False)
    combined_scene_2d_mesh = trimesh.util.concatenate(combined_scene_2d.geometry.values())

    # Extract vertices and entities from the sliced mesh
    vertices = combined_scene_2d_mesh.vertices
    entities = combined_scene_2d_mesh.entities

    # Initialize the Plotly figure
    fig = go.Figure()

    # Collect all x and z coordinates to determine the plot range
    all_x = []
    all_z = []
    for entity in entities:
        points = entity.points
        for point in points:
            all_x.append(vertices[point][0])
            all_z.append(vertices[point][2])

    # Calculate plot ranges with padding for better visualization
    x_range = [min(all_x) - 2, max(all_x) + 2]
    z_range = [min(all_z) - 2, max(all_z) + 2]

    # Create line traces for each entity in the cross-section
    for entity in entities:
        x = []
        z = []
        points = entity.points
        for point in points:
            x.append(vertices[point][0])
            z.append(vertices[point][2])

        # Add each line segment to the plot
        fig.add_trace(
            go.Scatter(
                x=x,
                y=z,
                mode="lines",
                line={"color": "black"},  # Consistent black color for all lines
            )
        )

    # Prepare annotations
    all_annotations = []

    # Create lists for row_labels and l values
    row_labels = list(range(len(params.bridge_segments_array)))
    l_values = []
    l_values_cumulative = []
    l_cumulative = 0
    h_values = []
    h_values_extra_hight = []
    h_values_output = []
    h_center_y = []

    for segment in params.bridge_segments_array:
        l_values.append(segment.l)
        l_cumulative += segment.l
        l_values_cumulative.append(l_cumulative)
        h_values.append(segment.dz)
        h_values_extra_hight.append(segment.dz_2 - segment.dz)

    zone_center_x = [cum + val / 2 for cum, val in zip(l_values_cumulative, l_values[1:])]

    # find in which zone the section is located
    zone_nr = 0
    # Check zone based on section location relative to the first cross-section
    if params.bridge_segments_array[0].bz2 / 2 < section_loc:
        zone_nr = 1
    elif section_loc < -params.bridge_segments_array[0].bz2 / 2:
        zone_nr = 3
    else:
        zone_nr = 2

    # check if extra height if so add the extra height to the height
    if max(all_z) > 0:
        h_values_output = [h + h_extra for h, h_extra in zip(h_values, h_values_extra_hight)]
        h_center_y = [((-h + h_extra) / 2) for h, h_extra in zip(h_values, h_values_extra_hight)]
    else:
        h_values_output = h_values
        h_center_y = [-h / 2 for h in h_values]

    # Add cross-section labels
    cross_section_labels = [
        go.layout.Annotation(
            x=cs_x,
            y=max(all_z) + ANNOTATION_Y_OFFSET_HORIZONTAL,  # Position above the highest point
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
        for i, cs_x in zip(row_labels, l_values_cumulative)  # Use the extracted lists
    ]

    all_annotations.extend(cross_section_labels)

    # add zone labels
    zone_labels = [
        go.layout.Annotation(
            x=zcx,
            y=ch_y,  # Position above the highest point
            text=f"<b>Z{zone_nr}-{sub_zone_nr}</b>",
            showarrow=False,
            font={"size": 15, "color": "black"},
            align="center",
            xanchor="center",
            yanchor="bottom",
            textangle=0,
            ax=0,
            ay=0,
        )
        for zcx, ch_y, sub_zone_nr in zip(zone_center_x, h_center_y[1:], row_labels[1:])  # Use the extracted lists
    ]
    all_annotations.extend(zone_labels)

    # Add dimension annotations
    dimension_annotations = [
        # Length dimension
        go.layout.Annotation(
            x=zcx,
            y=min(all_z) - ANNOTATION_Y_OFFSET_CROSS_SECTION,
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
        for length, zcx in zip(l_values[1:], zone_center_x)  # Use the extracted lists
    ]

    dimension_annotations.extend(
        [
            # Height dimension
            go.layout.Annotation(
                x=cs_x - DIMENSION_TEXT_X_OFFSET,
                y=ch_y,
                text=f"<b>h = {ch}m</b>",
                showarrow=False,
                font={"size": 12, "color": "blue"},
                align="center",
                xanchor="right",
                yanchor="middle",
                textangle=-90,
                ax=0,
                ay=0,
            )
            for ch, ch_y, cs_x in zip(h_values_output, h_center_y, l_values_cumulative)  # Use the extracted lists
        ]
    )

    all_annotations.extend(dimension_annotations)

    # Configure the plot layout with appropriate ranges and labels
    fig.update_layout(
        title="Langsdoorsnede (Longitudinal Section)",
        xaxis={"range": x_range, "constrain": "domain", "title": "X-as - Lengte [m]"},
        yaxis={
            "range": z_range,
            "scaleanchor": "x",
            "scaleratio": 1,  # Maintain aspect ratio for proper visualization
            "title": "Z-as - Hoogte [m]",  # Z-as is the vertical axis shown as Y-axis in the plot
        },
        annotations=all_annotations,
        showlegend=False,
    )

    return fig
