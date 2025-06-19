"""Module for creating cross section views of the bridge."""

import plotly.graph_objects as go
import trimesh
from munch import Munch  # type: ignore[import-untyped]

from src.geometry.model_creator import create_3d_model, create_cross_section


def create_cross_section_annotations(params: dict | Munch, all_z: list[float]) -> list[go.layout.Annotation]:
    """
    Create Plotly annotation objects for the cross-section view.

    :param params: Input parameters for the bridge dimensions.
    :type params: dict | Munch
    :param all_z: List of all z-coordinates in the cross-section.
    :type all_z: list[float]
    :returns: List of Plotly annotation objects for the cross-section.
    :rtype: list[go.layout.Annotation]
    """
    if not isinstance(params, Munch):
        params = Munch.fromDict(params)

    # Early exit if there are no segments to process
    if not params.get("bridge_segments_array"):
        return []

    l_values = []
    l_values_cumulative = []
    l_cumulative = 0
    b_values_1 = []
    b_values_2 = []
    b_values_3 = []
    zone1_center_y = []
    zone2_center_y = []
    zone3_center_y = []
    zone1_h = []
    zone2_h = []
    zone3_h = []
    zone1_h_center_y = []
    zone2_h_center_y = []
    zone3_h_center_y = []
    zone1_h_location = []
    zone2_h_location = []
    zone3_h_location = []

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

        zone1_h.append(segment.dz)
        zone2_h.append(segment.dz_2)
        zone3_h.append(segment.dz)

        zone1_h_center_y.append(-segment.dz / 2)
        zone2_h_center_y.append(-segment.dz + segment.dz_2 / 2)
        zone3_h_center_y.append(-segment.dz / 2)

        zone1_h_location.append(segment.bz2 / 2)
        zone2_h_location.append(-segment.bz2 / 2)
        zone3_h_location.append(-segment.bz2 / 2 - segment.bz3)

    # Find which segment the cross section is located in
    section_loc_param = params.input.dimensions.cross_section_loc
    segment_index = 0
    for i, cumulative_length in enumerate(l_values_cumulative):
        if section_loc_param <= cumulative_length:
            segment_index = i
            break

    all_annotations: list[go.layout.Annotation] = []

    # Zone labels
    zone_labels = [
        go.layout.Annotation(
            x=zone1_center_y[segment_index],
            y=zone1_h_center_y[segment_index],
            text=f"<b>Z1-{segment_index}</b>",
            showarrow=False,
            font={"size": 12, "color": "black"},
            align="center",
            xanchor="center",
            yanchor="middle",
            textangle=0,
            ax=0,
            ay=0,
        ),
        go.layout.Annotation(
            x=zone2_center_y[segment_index],
            y=zone2_h_center_y[segment_index],
            text=f"<b>Z2-{segment_index}</b>",
            showarrow=False,
            font={"size": 12, "color": "black"},
            align="center",
            xanchor="center",
            yanchor="middle",
            textangle=0,
            ax=0,
            ay=0,
        ),
        go.layout.Annotation(
            x=zone3_center_y[segment_index],
            y=zone3_h_center_y[segment_index],
            text=f"<b>Z3-{segment_index}</b>",
            showarrow=False,
            font={"size": 12, "color": "black"},
            align="center",
            xanchor="center",
            yanchor="middle",
            textangle=0,
            ax=0,
            ay=0,
        ),
    ]
    all_annotations.extend(zone_labels)

    # Width dimension annotations for each zone
    min_z = min(all_z)
    zone_width_annotations = [
        go.layout.Annotation(
            x=zone1_center_y[segment_index],
            y=min_z - 1.0,
            text=f"<b>b = {b_values_1[segment_index]}m</b>",
            showarrow=False,
            font={"size": 12, "color": "green"},
            align="center",
            xanchor="center",
            yanchor="middle",
            textangle=0,
            ax=0,
            ay=0,
        ),
        go.layout.Annotation(
            x=zone2_center_y[segment_index],
            y=min_z - 1.0,
            text=f"<b>b = {b_values_2[segment_index]}m</b>",
            showarrow=False,
            font={"size": 12, "color": "green"},
            align="center",
            xanchor="center",
            yanchor="middle",
            textangle=0,
            ax=0,
            ay=0,
        ),
        go.layout.Annotation(
            x=zone3_center_y[segment_index],
            y=min_z - 1.0,
            text=f"<b>b = {b_values_3[segment_index]}m</b>",
            showarrow=False,
            font={"size": 12, "color": "green"},
            align="center",
            xanchor="center",
            yanchor="middle",
            textangle=0,
            ax=0,
            ay=0,
        ),
    ]
    all_annotations.extend(zone_width_annotations)

    # Height dimension annotations for each zone
    zone_height_annotations = [
        go.layout.Annotation(
            x=zone1_h_location[segment_index],
            y=zone1_h_center_y[segment_index],
            text=f"<b>h = {zone1_h[segment_index]}m</b>",
            showarrow=False,
            font={"size": 12, "color": "blue"},
            align="center",
            xanchor="right",
            yanchor="middle",
            textangle=-90,
            ax=0,
            ay=0,
        ),
        go.layout.Annotation(
            x=zone2_h_location[segment_index],
            y=zone2_h_center_y[segment_index],
            text=f"<b>h = {zone2_h[segment_index]}m</b>",
            showarrow=False,
            font={"size": 12, "color": "blue"},
            align="center",
            xanchor="right",
            yanchor="middle",
            textangle=-90,
            ax=0,
            ay=0,
        ),
        go.layout.Annotation(
            x=zone3_h_location[segment_index],
            y=zone3_h_center_y[segment_index],
            text=f"<b>h = {zone3_h[segment_index]}m</b>",
            showarrow=False,
            font={"size": 12, "color": "blue"},
            align="center",
            xanchor="right",
            yanchor="middle",
            textangle=-90,
            ax=0,
            ay=0,
        ),
    ]
    all_annotations.extend(zone_height_annotations)

    return all_annotations


def create_cross_section_view(params: dict | Munch, section_loc: float) -> go.Figure:
    """
    Creates a 2D cross-section view of the bridge using Plotly.
    This function creates a 2D representation of the bridge's cross-section by:
    1. Creating a 3D model of the bridge
    2. Slicing it with a vertical plane parallel to the y-z plane
    3. Converting the resulting cross-section into a 2D plot showing width (y) vs height (z).

    Args:
        params (dict | Munch): Input parameters for the bridge dimensions.
        section_loc (float): Location of the cross-section along the x-axis.

    Returns:
        go.Figure: A 2D representation of the cross-section.

    """
    if isinstance(params, dict) and not isinstance(params, Munch):
        params = Munch.fromDict(params)
    # Generate the 3D model without coordinate axes
    scene = create_3d_model(params, axes=False)
    combined_mesh = trimesh.util.concatenate(scene.geometry.values())

    # Define the slicing plane for the cross-section
    # The plane is vertical (normal to x-axis) at the specified location
    plane_origin = [section_loc, 0, 0]
    plane_normal = [1, 0, 0]

    # Create the cross-section by slicing the 3D model
    combined_scene_2d = create_cross_section(combined_mesh, plane_origin, plane_normal, axes=False)
    combined_scene_2d_mesh = trimesh.util.concatenate(combined_scene_2d.geometry.values())

    # Extract vertices and entities from the sliced mesh
    vertices = combined_scene_2d_mesh.vertices
    entities = combined_scene_2d_mesh.entities

    # Initialize the Plotly figure
    fig = go.Figure()

    # Collect all x and y coordinates to determine the plot range
    all_y = []
    all_z = []
    for entity in entities:
        points = entity.points
        for point in points:
            all_y.append(vertices[point][1])
            all_z.append(vertices[point][2])

    # Calculate plot ranges with padding for better visualization
    y_range = [min(all_y) - 2, max(all_y) + 2]
    z_range = [min(all_z) - 2, max(all_z) + 2]

    # Create line traces for each entity in the section
    for entity in entities:
        y = []
        z = []
        points = entity.points
        for point in points:
            y.append(vertices[point][1])
            z.append(vertices[point][2])

        # Add each line segment to the plot
        fig.add_trace(
            go.Scatter(
                x=y,
                y=z,
                mode="lines",
                line={"color": "black"},  # Consistent black color for all lines
            )
        )

    # Add annotations to layout using the new function
    all_annotations = create_cross_section_annotations(params, all_z)
    fig.update_layout(annotations=all_annotations)

    # Configure the plot layout with appropriate ranges and labels
    fig.update_layout(
        title="Dwarsdoorsnede (Cross Section)",
        xaxis={"range": y_range, "constrain": "domain", "title": "Y-as - Breedte [m]"},
        yaxis={
            "range": z_range,
            "scaleanchor": "x",
            "scaleratio": 1,  # Maintain aspect ratio for proper visualization
            "title": "Z-as - Hoogte [m]",  # Z-as is the vertical axis shown as Y-axis in the plot
        },
        showlegend=False,
    )

    return fig


def calculate_max_array(params: object, **kwargs) -> int:  # noqa: ARG001
    """Calculate the maximum number of reinforcement zones based on the number of bridge segments."""
    sections = len(params.bridge_segments_array)  # type: ignore[attr-defined]
    return 3 * (sections - 1)
