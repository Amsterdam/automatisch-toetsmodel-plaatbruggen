"""Module for defining integration strips in SCIA."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .scia_model_interface import SciaIntegrationStrip, SciaModelBuilder

# Use string annotation to avoid circular import
if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


@dataclass
class SegmentGeometry:
    """Class to hold segment geometry data for easier access."""
    index: int  # 1-based index of the segment
    x_start: float  # Start x-coordinate
    x_end: float  # End x-coordinate
    top_y: float  # Top y-coordinate (z1_left)
    mid_upper_y: float  # Middle upper y-coordinate (z1_right/z2_left)
    mid_lower_y: float  # Middle lower y-coordinate (z2_right/z3_left)
    bottom_y: float  # Bottom y-coordinate (z3_right)


def _get_segment_geometry(segment: Any, segment_idx: int, x_start: float) -> SegmentGeometry:
    """
    Extract geometry data for a bridge segment.

    Args:
        segment: Bridge segment containing geometry data
        segment_idx: 1-based index of the segment
        x_start: x-coordinate where this segment starts

    Returns:
        SegmentGeometry object with all coordinates
    """
    return SegmentGeometry(
        index=segment_idx,
        x_start=x_start,
        x_end=x_start + segment.l,
        top_y=segment.bz1 + segment.bz2 / 2,  # z1_left
        mid_upper_y=segment.bz2 / 2,          # z1_right/z2_left
        mid_lower_y=-segment.bz2 / 2,         # z2_right/z3_left
        bottom_y=-(segment.bz3 + segment.bz2 / 2)  # z3_right
    )


def create_strip_definitions(params: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    """
    Create integration strip definitions for analyzing bridge deck forces.

    Creates integration strips in two directions:
    1. Cross-directional strips (3 connected strips) in the middle of the bridge span
    2. Longitudinal strips (one per segment) in the middle of each zone

    Args:
        params: Bridge parameters containing geometry data

    Returns:
        List of dictionaries containing integration strip definitions with:
            - plane: Name of the plate where the strip will be created
            - point_1: Start coordinates (x, y, z) in [m]
            - point_2: End coordinates (x, y, z) in [m]
            - width: Width of the integration strip in [m]
    """
    strip_definitions = []
    strip_width = 1.0  # Width of integration strips in [m]

    # Find the segment that contains the midpoint of the bridge
    total_length = sum(segment.l for segment in params.bridge_segments_array)
    mid_length = total_length / 2
    
    # Get geometry data for all segments
    segments_geom = []
    x_pos = 0
    for idx, segment in enumerate(params.bridge_segments_array, start=0):
        geom = _get_segment_geometry(segment, idx, x_pos)
        segments_geom.append(geom)
        x_pos += segment.l
    
    # Find segment containing the midpoint
    mid_segment_geom = None
    for geom in segments_geom:
        if geom.x_start <= mid_length <= geom.x_end:
            mid_segment_geom = geom
            break
    
    if mid_segment_geom is None:
        raise ValueError("Could not find segment containing bridge midpoint")
    
    # Create cross-directional strips (Z1, Z2, Z3)
    # Zone 1 (top)
    strip_definitions.append({
        "plane": f"Z1_{mid_segment_geom.index}",
        "point_1": (mid_length, mid_segment_geom.top_y, 0),
        "point_2": (mid_length, mid_segment_geom.mid_upper_y, 0),
        "width": strip_width
    })
    
    # Zone 2 (middle)
    strip_definitions.append({
        "plane": f"Z2_{mid_segment_geom.index}",
        "point_1": (mid_length, mid_segment_geom.mid_upper_y, 0),
        "point_2": (mid_length, mid_segment_geom.mid_lower_y, 0),
        "width": strip_width
    })
    
    # Zone 3 (bottom)
    strip_definitions.append({
        "plane": f"Z3_{mid_segment_geom.index}",
        "point_1": (mid_length, mid_segment_geom.mid_lower_y, 0),
        "point_2": (mid_length, mid_segment_geom.bottom_y, 0),
        "width": strip_width
    })
    
    # Create longitudinal strips
    # One strip per segment, in middle of each zone
    print("Creating longitudinal integration strips...")
    print("Segment geometries:", segments_geom)
    for idx, geom in enumerate(segments_geom[:-1]):  # Skip last segment as it's the end
        next_geom = segments_geom[idx + 1]
        
        # Zone 1 (top zone)
        y_mid_current = (geom.top_y + geom.mid_upper_y) / 2
        y_mid_next = (next_geom.top_y + next_geom.mid_upper_y) / 2
        strip_definitions.append({
            "plane": f"Z1_{geom.index}",
            "point_1": (geom.x_start, y_mid_current, 0),
            "point_2": (geom.x_end, y_mid_next, 0),
            "width": strip_width
        })
        
        # Zone 2 (middle zone)
        y_mid_current = (geom.mid_upper_y + geom.mid_lower_y) / 2
        y_mid_next = (next_geom.mid_upper_y + next_geom.mid_lower_y) / 2
        strip_definitions.append({
            "plane": f"Z2_{geom.index}",
            "point_1": (geom.x_start, y_mid_current, 0),
            "point_2": (geom.x_end, y_mid_next, 0),
            "width": strip_width
        })
        
        # Zone 3 (bottom zone)
        y_mid_current = (geom.mid_lower_y + geom.bottom_y) / 2
        y_mid_next = (next_geom.mid_lower_y + next_geom.bottom_y) / 2
        strip_definitions.append({
            "plane": f"Z3_{geom.index}",
            "point_1": (geom.x_start, y_mid_current, 0),
            "point_2": (geom.x_end, y_mid_next, 0),
            "width": strip_width
        })
    
    print(f"Created {len(strip_definitions)} integration strip definitions.")
    print("Integration strip definitions:", strip_definitions)
    
    return strip_definitions


def create_integration_strips(
        builder: SciaModelBuilder,
        strip_definitions: list[dict],
) -> list[SciaIntegrationStrip]:
    """
    Define and create integration strips in the SCIA model.

    :param builder: The SCIA model builder instance.
    :param strip_definitions: A list of dictionaries defining each strip with keys:
                              'name', 'point_1', 'point_2', and 'width'.
    :return: A list of the created IntegrationStrip objects.
    """
    strip_objects = []

    for strip_def in strip_definitions:
        strip_objects.append(
            builder.create_integration_strip(
                plane=strip_def['plane'],
                point_1=strip_def['point_1'],
                point_2=strip_def['point_2'],
                width=strip_def['width'],
            )
        )

    return strip_objects

def create_all_integration_strips(builder: SciaModelBuilder, strip_definitions: list[dict]) -> list[SciaIntegrationStrip]:
    """
    Define and create all integration strips for the bridge model.

    :param builder: The SCIA model builder instance.
    :param strip_definitions: A list of dictionaries defining each strip with keys:
                              'name', 'point_1', 'point_2', and 'width'.
    :return: A list of the created IntegrationStrip objects.
    """
    all_strips = []
    all_strips.extend(create_integration_strips(builder, strip_definitions))
    return all_strips