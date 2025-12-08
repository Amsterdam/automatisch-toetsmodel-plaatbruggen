"""
SCIA integration strips creation module.

This module handles the creation of integration strips for SCIA models.
Integration strips are used to extract forces and stresses across defined strips
in the bridge deck zones.

For each zone in the SCIA model (Z1_1, Z2_1, Z3_1, Z1_2, etc.), integration strips
are created in both X and Y directions. Multiple strips are created to cover the
complete zone surface.

Strip Placement Logic:
- For zones >= 1m: Place 1m wide strips every 0.5m from max boundary
- For zones < 1m: Place single strip with width equal to zone dimension at center
- Additional strip added at min boundary if needed to cover complete surface

Strip Naming:
- Format: strip_{zone}_{width}_{direction}_{number}
- Zone format: Z1-1, Z2-1, Z3-2 (hyphen separator for clarity)
- Examples: strip_Z1-1_1.0_X_1, strip_Z2-1_0.8_Y_2
- Names are set using the _name attribute workaround after creation
- The custom names appear in SCIA output and results
"""

from typing import Any

from .scia_model_interface import SciaModelBuilder

# Integration strip configuration
STRIP_WIDTH = 1.0  # Width of each integration strip in meters
STRIP_SPACING = 0.5  # Spacing between strip centers in meters


def _calculate_zone_boundaries(params: Any, zone_position: int, segment_idx: int) -> dict[str, float]:  # noqa: ANN401
    """
    Calculate the Y-axis boundaries for a specific zone.

    :param params: Bridge parameters
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: Segment index (0-based)
    :return: Dictionary with y_min and y_max boundaries
    """
    segment = params.bridge_segments_array[segment_idx]

    # Zone layout: Zone 1 (left/top) | Zone 2 (middle) | Zone 3 (right/bottom)
    # Y-coordinates from top to bottom:
    #   Zone 1: from (bz2/2 + bz1) to (bz2/2)
    #   Zone 2: from (bz2/2) to (-bz2/2)
    #   Zone 3: from (-bz2/2) to (-bz2/2 - bz3)

    if zone_position == 1:
        y_max = segment.bz1 + segment.bz2 / 2
        y_min = segment.bz2 / 2
    elif zone_position == 2:
        y_max = segment.bz2 / 2
        y_min = -segment.bz2 / 2
    elif zone_position == 3:
        y_max = -segment.bz2 / 2
        y_min = -segment.bz3 - segment.bz2 / 2
    else:
        raise ValueError(f"Invalid zone position: {zone_position}. Must be 1, 2, or 3.")

    return {"y_min": y_min, "y_max": y_max}


def _calculate_zone_x_boundaries(params: Any, segment_idx: int) -> dict[str, float]:  # noqa: ANN401
    """
    Calculate the X-axis (longitudinal) boundaries for a specific segment.

    :param params: Bridge parameters
    :param segment_idx: Segment index (0-based)
    :return: Dictionary with x_start and x_end boundaries
    """
    # Calculate cumulative length up to this segment
    x_start = sum(seg.l for seg in params.bridge_segments_array[:segment_idx])
    x_end = x_start + params.bridge_segments_array[segment_idx].l

    return {"x_start": x_start, "x_end": x_end}


def _create_integration_strip_x_direction(
    builder: SciaModelBuilder,
    plane_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Create multiple integration strips in the X direction (longitudinal) for a zone.

    Creates multiple strips spaced evenly across the zone width to cover
    the complete zone surface.

    :param builder: The SCIA model builder instance
    :param plane_name: Name of the plane/zone (e.g., "Z1_1")
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: Segment index (0-based)
    :param params: Bridge parameters
    """
    # Get zone boundaries
    y_bounds = _calculate_zone_boundaries(params, zone_position, segment_idx)
    x_bounds = _calculate_zone_x_boundaries(params, segment_idx)

    # Calculate zone dimensions
    zone_width_y = y_bounds["y_max"] - y_bounds["y_min"]
    zone_length_x = x_bounds["x_end"] - x_bounds["x_start"]

    # Skip if zone is too small
    if zone_width_y < 0.1 or zone_length_x < 0.1:
        print(f"  [WARNING] Zone too small for integration strips (width: {zone_width_y:.3f}m, length: {zone_length_x:.3f}m)")
        return

    # Special case: zone narrower than 1m - place single strip with reduced width
    if zone_width_y < 1.0:
        strip_width = zone_width_y
        strip_y = (y_bounds["y_min"] + y_bounds["y_max"]) / 2
        
        # Format zone name: Z1_1 -> Z1-1
        zone_name = plane_name.replace('_', '-')
        custom_name = f"strip_{zone_name}_{strip_width:.1f}_X_1"
        
        print(f"[DEBUG] Creating X-direction integration strips for {plane_name}")
        print(f"  Zone Y-bounds: {y_bounds['y_min']:.3f} to {y_bounds['y_max']:.3f} (width: {zone_width_y:.3f}m)")
        print(f"  Special case: zone < 1m, single strip with width {strip_width:.3f}m at center")
        print(f"  X-bounds: {x_bounds['x_start']:.3f} to {x_bounds['x_end']:.3f}m")
        
        integration_strip = builder.create_integration_strip(
            plane=plane_name,
            point_1=(x_bounds["x_start"], strip_y, 0.0),
            point_2=(x_bounds["x_end"], strip_y, 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
        
        actual_name = getattr(integration_strip, 'name', custom_name)
        half_width = strip_width / 2
        print(f"    Strip 1/1 '{actual_name}' at Y={strip_y:.3f}m (covers {strip_y - half_width:.3f} to {strip_y + half_width:.3f})")
        return

    # Standard case: zone >= 1m, use 1m strips
    strip_width = 1.0
    half_width = strip_width / 2
    
    # Calculate strip positions: place strips every 0.5m starting from y_max
    # Working downward: y_max - 0.5, y_max - 1.0, y_max - 1.5, etc.
    strip_positions = []
    current_y = y_bounds["y_max"] - 0.5
    
    while current_y >= y_bounds["y_min"] + half_width:
        strip_positions.append(current_y)
        current_y -= 0.5
    
    # Check if we need an additional strip at the bottom to cover remaining area
    if strip_positions:
        lowest_strip_y = strip_positions[-1]
        lowest_coverage_bottom = lowest_strip_y - half_width
        
        # If there's uncovered area at the bottom, add strip at y_min + half_width
        if lowest_coverage_bottom > y_bounds["y_min"] + 0.05:  # 5cm tolerance
            strip_positions.append(y_bounds["y_min"] + half_width)
    else:
        # No strips placed yet, add one at y_min + half_width
        strip_positions.append(y_bounds["y_min"] + half_width)

    num_strips = len(strip_positions)

    # Debug print
    print(f"[DEBUG] Creating X-direction integration strips for {plane_name}")
    print(f"  Zone Y-bounds: {y_bounds['y_min']:.3f} to {y_bounds['y_max']:.3f} (width: {zone_width_y:.3f}m)")
    print(f"  Strip width: {strip_width:.3f}m (extends ±{half_width:.3f}m from center)")
    print(f"  Number of strips: {num_strips}")
    print(f"  X-bounds: {x_bounds['x_start']:.3f} to {x_bounds['x_end']:.3f}m")

    # Create integration strips
    zone_name = plane_name.replace('_', '-')
    for i, strip_y in enumerate(strip_positions):
        # Calculate strip coverage area for debug
        strip_y_min = strip_y - half_width
        strip_y_max = strip_y + half_width
        
        # Generate custom name: strip_{zone}_{width}_{direction}_{number}
        custom_name = f"strip_{zone_name}_{strip_width:.1f}_X_{i+1}"
        
        # Create the strip with custom name
        integration_strip = builder.create_integration_strip(
            plane=plane_name,
            point_1=(x_bounds["x_start"], strip_y, 0.0),
            point_2=(x_bounds["x_end"], strip_y, 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
        
        # Log the custom name that was set
        actual_name = getattr(integration_strip, 'name', custom_name)
        print(f"    Strip {i+1}/{num_strips} '{actual_name}' at Y={strip_y:.3f}m (covers {strip_y_min:.3f} to {strip_y_max:.3f})")


def _create_integration_strip_y_direction(
    builder: SciaModelBuilder,
    plane_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Create multiple integration strips in the Y direction (transverse) for a zone.

    Creates multiple strips spaced evenly across the zone length to cover
    the complete zone surface.

    :param builder: The SCIA model builder instance
    :param plane_name: Name of the plane/zone (e.g., "Z1_1")
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: Segment index (0-based)
    :param params: Bridge parameters
    """
    # Get zone boundaries
    y_bounds = _calculate_zone_boundaries(params, zone_position, segment_idx)
    x_bounds = _calculate_zone_x_boundaries(params, segment_idx)

    # Calculate zone dimensions
    zone_width_y = y_bounds["y_max"] - y_bounds["y_min"]
    zone_length_x = x_bounds["x_end"] - x_bounds["x_start"]

    # Skip if zone is too small
    if zone_width_y < 0.1 or zone_length_x < 0.1:
        print(f"  [WARNING] Zone too small for integration strips (width: {zone_width_y:.3f}m, length: {zone_length_x:.3f}m)")
        return

    # Special case: zone narrower than 1m - place single strip with reduced width
    if zone_width_y < 1.0:
        strip_width = zone_width_y
        strip_x = (x_bounds["x_start"] + x_bounds["x_end"]) / 2
        
        # Format zone name: Z1_1 -> Z1-1
        zone_name = plane_name.replace('_', '-')
        custom_name = f"strip_{zone_name}_{strip_width:.1f}_Y_1"
        
        print(f"[DEBUG] Creating Y-direction integration strips for {plane_name}")
        print(f"  Y-bounds: {y_bounds['y_min']:.3f} to {y_bounds['y_max']:.3f} (width: {zone_width_y:.3f}m)")
        print(f"  Special case: zone < 1m, single strip with width {strip_width:.3f}m at center")
        print(f"  X-bounds: {x_bounds['x_start']:.3f} to {x_bounds['x_end']:.3f}m\")")
        
        integration_strip = builder.create_integration_strip(
            plane=plane_name,
            point_1=(strip_x, y_bounds["y_min"], 0.0),
            point_2=(strip_x, y_bounds["y_max"], 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
        
        actual_name = getattr(integration_strip, 'name', custom_name)
        half_width = strip_width / 2
        print(f"    Strip 1/1 '{actual_name}' at X={strip_x:.3f}m (covers {strip_x - half_width:.3f} to {strip_x + half_width:.3f})")
        return

    # Special case: zone shorter than 1m - place single strip with reduced width
    if zone_length_x < 1.0:
        strip_width = zone_length_x
        strip_x = (x_bounds["x_start"] + x_bounds["x_end"]) / 2
        
        # Format zone name: Z1_1 -> Z1-1
        zone_name = plane_name.replace('_', '-')
        custom_name = f"strip_{zone_name}_{strip_width:.1f}_Y_1"
        
        print(f"[DEBUG] Creating Y-direction integration strips for {plane_name}")
        print(f"  X-bounds: {x_bounds['x_start']:.3f} to {x_bounds['x_end']:.3f} (length: {zone_length_x:.3f}m)")
        print(f"  Special case: zone < 1m, single strip with width {strip_width:.3f}m at center")
        print(f"  Y-bounds: {y_bounds['y_min']:.3f} to {y_bounds['y_max']:.3f}m")
        
        integration_strip = builder.create_integration_strip(
            plane=plane_name,
            point_1=(strip_x, y_bounds["y_min"], 0.0),
            point_2=(strip_x, y_bounds["y_max"], 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
        
        actual_name = getattr(integration_strip, 'name', custom_name)
        half_width = strip_width / 2
        print(f"    Strip 1/1 '{actual_name}' at X={strip_x:.3f}m (covers {strip_x - half_width:.3f} to {strip_x + half_width:.3f})")
        return

    # Standard case: zone >= 1m, use 1m strips
    strip_width = 1.0
    half_width = strip_width / 2
    
    # Calculate strip positions: place strips every 0.5m starting from x_max
    # Working backward: x_max - 0.5, x_max - 1.0, x_max - 1.5, etc.
    strip_positions = []
    current_x = x_bounds["x_end"] - 0.5
    
    while current_x >= x_bounds["x_start"] + half_width:
        strip_positions.append(current_x)
        current_x -= 0.5
    
    # Check if we need an additional strip at the start to cover remaining area
    if strip_positions:
        first_strip_x = strip_positions[-1]
        first_coverage_start = first_strip_x - half_width
        
        # If there's uncovered area at the start, add strip at x_min + half_width
        if first_coverage_start > x_bounds["x_start"] + 0.05:  # 5cm tolerance
            strip_positions.append(x_bounds["x_start"] + half_width)
    else:
        # No strips placed yet, add one at x_min + half_width
        strip_positions.append(x_bounds["x_start"] + half_width)

    num_strips = len(strip_positions)

    # Debug print
    print(f"[DEBUG] Creating Y-direction integration strips for {plane_name}")
    print(f"  X-bounds: {x_bounds['x_start']:.3f} to {x_bounds['x_end']:.3f} (length: {zone_length_x:.3f}m)")
    print(f"  Strip width: {strip_width:.3f}m (extends ±{half_width:.3f}m from center)")
    print(f"  Number of strips: {num_strips}")
    print(f"  Y-bounds: {y_bounds['y_min']:.3f} to {y_bounds['y_max']:.3f}m")

    # Create integration strips
    zone_name = plane_name.replace('_', '-')
    for i, strip_x in enumerate(strip_positions):
        # Calculate strip coverage area for debug
        strip_x_min = strip_x - half_width
        strip_x_max = strip_x + half_width
        
        # Generate custom name: strip_{zone}_{width}_{direction}_{number}
        custom_name = f"strip_{zone_name}_{strip_width:.1f}_Y_{i+1}"
        
        # Create the strip with custom name
        integration_strip = builder.create_integration_strip(
            plane=plane_name,
            point_1=(strip_x, y_bounds["y_min"], 0.0),
            point_2=(strip_x, y_bounds["y_max"], 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
        
        # Log the custom name that was set
        actual_name = getattr(integration_strip, 'name', custom_name)
        print(f"    Strip {i+1}/{num_strips} '{actual_name}' at X={strip_x:.3f}m (covers {strip_x_min:.3f} to {strip_x_max:.3f})")


def create_all_integration_strips(builder: SciaModelBuilder, params: Any) -> None:  # noqa: ANN401
    """
    Create all integration strips for all zones in the SCIA model.

    For each zone (Z1_1, Z2_1, Z3_1, Z1_2, etc.), this function creates:
    - Multiple integration strips in the X direction (longitudinal)
    - Multiple integration strips in the Y direction (transverse)

    The strips are distributed evenly across each zone to cover the complete
    zone surface. Strip spacing is configured to provide comprehensive coverage.

    :param builder: The SCIA model builder instance
    :param params: Bridge parameters
    """
    print("\n[DEBUG] ========== Creating Integration Strips ==========")

    # Get number of segments (excluding the first definition segment)
    num_segments = len(params.bridge_segments_array)

    # Iterate through segments (starting from segment 1, as segment 0 is a definition segment)
    for segment_idx in range(1, num_segments):
        segment_num = segment_idx  # Segment number for naming (1-based for plates)

        # Create integration strips for each zone in this segment
        for zone_position in [1, 2, 3]:
            plane_name = f"Z{zone_position}_{segment_num}"

            print(f"\n[DEBUG] Processing zone: {plane_name}")

            # Create integration strip in X direction (longitudinal)
            _create_integration_strip_x_direction(
                builder=builder,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
            )

            # Create integration strip in Y direction (transverse)
            _create_integration_strip_y_direction(
                builder=builder,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
            )

    print("\n[DEBUG] ========== Integration Strips Creation Complete ==========\n")
