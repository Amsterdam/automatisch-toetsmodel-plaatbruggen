"""Module for defining integration strips in SCIA."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.common.constants.technical import EDGE_OFFSET, INTEGRATION_STRIP_WIDTH
from src.data_models.bridge_models import BridgeSegmentDimensions

from .scia_loads_helper import obtain_y_coordinates_road
from .scia_model_interface import SciaIntegrationStrip, SciaModelBuilder

# Use string annotation to avoid circular import
if TYPE_CHECKING:
    pass

BridgeParametrization = Any  # Replace with actual BridgeParametrization type if available


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


def determine_zone_index(y_coord: float, geom: SegmentGeometry) -> int:
    """
    Determine the zone index based on the y-coordinate position.

    Args:
        y_coord: The y-coordinate to check
        geom: The segment geometry containing boundary coordinates

    Returns:
        int: Zone index (1, 2, or 3)

    """
    if geom.top_y >= y_coord >= geom.mid_upper_y:
        return 1
    if geom.mid_upper_y >= y_coord >= geom.mid_lower_y:
        return 2
    if geom.mid_lower_y >= y_coord >= geom.bottom_y:
        return 3
    # If y_coord is outside any zone, default to closest zone
    if y_coord > geom.top_y:
        return 1
    return 3


def _get_segment_geometry(segment: BridgeSegmentDimensions, segment_idx: int, x_start: float) -> SegmentGeometry:
    """
    Extract geometry data for a bridge segment.

    Args:
        segment: Bridge segment containing geometry data with zone widths and dimensions
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
        mid_upper_y=segment.bz2 / 2,  # z1_right/z2_left
        mid_lower_y=-segment.bz2 / 2,  # z2_right/z3_left
        bottom_y=-(segment.bz3 + segment.bz2 / 2),  # z3_right
    )


def create_theoretical_integration_strips(params: BridgeParametrization) -> list[dict[str, Any]]:
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
    strip_definitions.append(
        {
            "plane": f"Z1_{mid_segment_geom.index}",
            "point_1": (mid_length, mid_segment_geom.top_y, 0),
            "point_2": (mid_length, mid_segment_geom.mid_upper_y, 0),
            "width": INTEGRATION_STRIP_WIDTH,
        }
    )

    # Zone 2 (middle)
    strip_definitions.append(
        {
            "plane": f"Z2_{mid_segment_geom.index}",
            "point_1": (mid_length, mid_segment_geom.mid_upper_y, 0),
            "point_2": (mid_length, mid_segment_geom.mid_lower_y, 0),
            "width": INTEGRATION_STRIP_WIDTH,
        }
    )

    # Zone 3 (bottom)
    strip_definitions.append(
        {
            "plane": f"Z3_{mid_segment_geom.index}",
            "point_1": (mid_length, mid_segment_geom.mid_lower_y, 0),
            "point_2": (mid_length, mid_segment_geom.bottom_y, 0),
            "width": INTEGRATION_STRIP_WIDTH,
        }
    )

    # Create longitudinal strips
    for idx, geom in enumerate(segments_geom[1:]):
        # Create one longitudinal strip with dynamic zone detection
        y_middle = (geom.top_y + geom.bottom_y) / 2  # Calculate the y-coordinate
        y_top = geom.top_y - EDGE_OFFSET  # Slightly below top edge
        y_bottom = geom.bottom_y + EDGE_OFFSET  # Slightly above bottom edge
        zone_index_middle = determine_zone_index(y_middle, geom)
        zone_index_top_edge = determine_zone_index(y_top, geom)
        zone_index_bottom_edge = determine_zone_index(y_bottom, geom)

        strip_definitions.append(
            {
                "plane": f"Z{zone_index_middle}_{geom.index}",  # Unique name for longitudinal strip
                "point_1": (geom.x_start, y_middle, 0),  # Start at current segment's start
                "point_2": (geom.x_end, y_middle, 0),  # End at current segment's end
                "width": INTEGRATION_STRIP_WIDTH,
            }
        )
        strip_definitions.append(
            {
                "plane": f"Z{zone_index_top_edge}_{geom.index}",  # Unique name for top edge strip
                "point_1": (geom.x_start, y_top, 0),  # Start at current segment's start
                "point_2": (geom.x_end, y_top, 0),  # End at current segment's end
                "width": INTEGRATION_STRIP_WIDTH,
            }
        )
        strip_definitions.append(
            {
                "plane": f"Z{zone_index_bottom_edge}_{geom.index}",  # Unique name for bottom edge strip
                "point_1": (geom.x_start, y_bottom, 0),  # Start at current segment's start
                "point_2": (geom.x_end, y_bottom, 0),  # End at current segment's end
                "width": INTEGRATION_STRIP_WIDTH,
            }
        )

    return strip_definitions


def create_real_integration_strips(params: BridgeParametrization) -> list[dict[str, Any]]:
    """
    Create integration strip definitions based on the real road layout.

    Creates integration strips in two directions:
    1. Cross-directional strip in the middle of the bridge span
    2. Three longitudinal strips:
       - One in the middle of the bridge width
       - Two 0.5m inward from each side of the road (only for "Auto" zones)

    Args:
        params: Bridge parameters containing geometry and load zone data

    Returns:
        List of dictionaries containing integration strip definitions with:
            - plane: Name of the plate where the strip will be created
            - point_1: Start coordinates (x, y, z) in [m]
            - point_2: End coordinates (x, y, z) in [m]
            - width: Width of the integration strip in [m]

    """
    strip_definitions = []

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

    # Get car traffic zone data
    y_top, road_width = obtain_y_coordinates_road(params)
    print(y_top, road_width)
    # Calculate y-coordinates for strips
    y_middle = (geom.top_y + geom.bottom_y) / 2  # Middle of the bridge width
    y_top_road = y_top - EDGE_OFFSET  # 0.5m inward from top road edge
    y_bottom_road = y_top - road_width + EDGE_OFFSET  # 0.5m inward from bottom road edge
    zone_index_middle = determine_zone_index(y_middle, mid_segment_geom)
    zone_index_top_edge = determine_zone_index(y_top_road, mid_segment_geom)
    zone_index_bottom_edge = determine_zone_index(y_bottom_road, mid_segment_geom)

    # Create cross-directional strip at mid-span
    # Zone 1 (top)
    strip_definitions.append(
        {
            "plane": f"Z1_{mid_segment_geom.index}",
            "point_1": (mid_length, mid_segment_geom.top_y, 0),
            "point_2": (mid_length, mid_segment_geom.mid_upper_y, 0),
            "width": INTEGRATION_STRIP_WIDTH,
        }
    )

    # Zone 2 (middle)
    strip_definitions.append(
        {
            "plane": f"Z2_{mid_segment_geom.index}",
            "point_1": (mid_length, mid_segment_geom.mid_upper_y, 0),
            "point_2": (mid_length, mid_segment_geom.mid_lower_y, 0),
            "width": INTEGRATION_STRIP_WIDTH,
        }
    )

    # Zone 3 (bottom)
    strip_definitions.append(
        {
            "plane": f"Z3_{mid_segment_geom.index}",
            "point_1": (mid_length, mid_segment_geom.mid_lower_y, 0),
            "point_2": (mid_length, mid_segment_geom.bottom_y, 0),
            "width": INTEGRATION_STRIP_WIDTH,
        }
    )
    # Create longitudinal strips
    for idx, geom in enumerate(segments_geom[1:]):
        # Middle strip
        strip_definitions.append(
            {
                "plane": f"Z{zone_index_middle}_{geom.index}",  # Unique name for longitudinal strip
                "point_1": (geom.x_start, y_middle, 0),  # Start at current segment's start
                "point_2": (geom.x_end, y_middle, 0),  # End at current segment's end
                "width": INTEGRATION_STRIP_WIDTH,
            }
        )
        strip_definitions.append(
            {
                "plane": f"Z{zone_index_top_edge}_{geom.index}",  # Unique name for top edge strip
                "point_1": (geom.x_start, y_top_road, 0),  # Start at current segment's start
                "point_2": (geom.x_end, y_top_road, 0),  # End at current segment's end
                "width": INTEGRATION_STRIP_WIDTH,
            }
        )
        strip_definitions.append(
            {
                "plane": f"Z{zone_index_bottom_edge}_{geom.index}",  # Unique name for bottom edge strip
                "point_1": (geom.x_start, y_bottom_road, 0),  # Start at current segment's start
                "point_2": (geom.x_end, y_bottom_road, 0),  # End at current segment's end
                "width": INTEGRATION_STRIP_WIDTH,
            }
        )

    return strip_definitions


def create_strip_definitions(params: BridgeParametrization) -> list[dict[str, Any]]:
    """
    Create integration strip definitions based on the calculation level setting.

    For "Theoretische wegindeling", creates strips based on theoretical road layout.
    For other calculation levels, creates strips based on the actual road layout.

    Args:
        params: Bridge parameters containing geometry and settings data

    Returns:
        List of strip definitions appropriate for the selected calculation level

    """
    is_theoretical = params.berekeningsniveau == "Theoretische wegindeling"

    if is_theoretical:
        return create_theoretical_integration_strips(params)
    return create_real_integration_strips(params)


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
    return [
        builder.create_integration_strip(
            plane=strip_def["plane"],
            point_1=strip_def["point_1"],
            point_2=strip_def["point_2"],
            width=strip_def["width"],
        )
        for strip_def in strip_definitions
    ]


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
