"""
SCIA integration strips creation module.

This module handles the creation of integration strips for SCIA models.
Integration strips are used to extract forces and stresses across defined strips
in the bridge deck zones.

For each zone in the SCIA model (Z1_1, Z2_1, Z3_1, Z1_2, etc.), integration strips
are created in both X and Y directions. Multiple strips are created to cover the
complete zone surface.

Strip Types:
1. Regular strips: Cover the zone surface between supports
2. Support strips: Special strips near support locations (width = 0.9 * thickness)

Strip Placement Logic:
- For zones >= 1m: Place 1m wide strips every 0.5m
- For zones < 1m: Place single strip with width equal to zone dimension at center
- Gap filling: Add strips when gap > 0.5m to ensure complete coverage
- Overlap prevention: Regular strips avoid support areas using exclusion zones

Strip Naming:
- Regular: strip_dir-{direction}_reg_{zone}_w-{width}_nr-{number}
- Support: strip_dir-{direction}_sup-{x}_{zone}_w-{width}_nr-{number}
- Zone format: Z1-1, Z2-1, Z3-2 (hyphen separator for clarity)
- Examples: strip_dir-x_reg_Z1-1_w-1.0_nr-1, strip_dir-y_sup-5.0_Z1-1_w-0.54_nr-1
"""

from typing import Any, TypedDict

from .scia_model_interface import SciaModelBuilder


class SupportLocation(TypedDict):
    """Type definition for support location dictionary."""

    x_coord: float
    segment_idx: int
    type: str  # 'start', 'end', or 'intermediate'


class ZoneBoundaries(TypedDict):
    """Type definition for zone boundary dictionary."""

    y_min: float
    y_max: float


class ZoneXBoundaries(TypedDict):
    """Type definition for zone X-axis boundary dictionary."""

    x_start: float
    x_end: float


# Integration strip configuration
STRIP_WIDTH = 1.0  # Width of each integration strip in meters
STRIP_SPACING = 0.5  # Spacing between strip centers in meters
SUPPORT_STRIP_FACTOR = 0.9  # Factor for support strip dimensions (0.9 * thickness)


class _FilteringBuilderWrapper:
    """
    Wrapper for SciaModelBuilder that filters integration strip creation by name.

    This wrapper intercepts create_integration_strip calls and only passes through
    strips whose custom_name is in the allowed set. All other builder methods are
    delegated to the wrapped builder.

    Used for Stage 2 analysis to create only governing strips.
    """

    def __init__(self, wrapped_builder: SciaModelBuilder, allowed_names: set[str]) -> None:
        """
        Initialize the filtering wrapper.

        :param wrapped_builder: The actual builder to wrap
        :param allowed_names: Set of strip names that are allowed to be created
        """
        self._wrapped = wrapped_builder
        self._allowed_names = allowed_names
        self._created_count = 0
        self._skipped_count = 0

    def create_integration_strip(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """
        Intercept integration strip creation and filter by name.

        Only creates strips whose custom_name is in the allowed set.
        """
        custom_name = kwargs.get("custom_name", "")

        if custom_name in self._allowed_names:
            self._created_count += 1
            return self._wrapped.create_integration_strip(*args, **kwargs)

        # Strip not in governing set, skip it
        self._skipped_count += 1
        return None

    def get_stats(self) -> dict[str, int]:
        """Get statistics about filtered strip creation."""
        return {
            "created": self._created_count,
            "skipped": self._skipped_count,
            "total_attempted": self._created_count + self._skipped_count,
        }

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        """Delegate all other attribute access to the wrapped builder."""
        return getattr(self._wrapped, name)


def _get_support_locations(params: Any) -> list[SupportLocation]:  # noqa: ANN401
    """
    Get all support locations with their X coordinates and types.

    Bridge segments array structure:
    - Row 0: Start of bridge at X=0 (start of section 1), length=0
    - Row 1: End of section 1 (at X=0+length_1), Row 1's 'l' field = length of section 1
    - Row 2: End of section 2 (at X=0+length_1+length_2), Row 2's 'l' field = length of section 2
    - Row 3: End of section 3 (at X=0+length_1+length_2+length_3), Row 3's 'l' field = length of section 3
    - etc.

    Each row has an 'is_support' field indicating if there's a support at that location.
    'is_support' values: 'Nee' (no support) or support type like 'Verende oplegging (x,y)'

    :param params: Bridge parameters
    :return: List of support info dicts with 'x_coord', 'segment_idx', 'type' ('start', 'end', or 'intermediate')
    """
    supports: list[SupportLocation] = []
    num_rows = len(params.bridge_segments_array)

    # Detect supports from bridge_segments_array
    # Row 0: Start of bridge at X=0 (start of section 1)
    row_0_support = getattr(params.bridge_segments_array[0], "is_support", "Nee")
    if row_0_support and row_0_support != "Nee":
        supports.append(SupportLocation(x_coord=0.0, segment_idx=0, type="start"))

    # Rows 1 to n-1: Each row represents a segment boundary
    # Row i is at the end of section i (and start of section i+1 if not last row)
    # Row i's 'l' field contains the LENGTH of section i
    cumulative_x = 0.0
    for row_idx in range(1, num_rows):
        row = params.bridge_segments_array[row_idx]
        # Row i's length is the length OF section i, add it to get position of this row
        segment_length = getattr(row, "l", 0.0)
        cumulative_x += segment_length

        is_support = getattr(row, "is_support", "Nee")

        if is_support and is_support != "Nee":
            # Determine support type based on position
            if row_idx == num_rows - 1:
                # Last row = end support
                supports.append(SupportLocation(x_coord=cumulative_x, segment_idx=row_idx, type="end"))
            else:
                # Intermediate row = intermediate support (end of section i / start of section i+1)
                supports.append(SupportLocation(x_coord=cumulative_x, segment_idx=row_idx, type="intermediate"))

    return supports


def _get_zone_thickness(params: Any, zone_position: int, segment_idx: int) -> float:  # noqa: ANN401
    """
    Get the thickness of a specific zone.

    :param params: Bridge parameters
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: Segment index (0-based)
    :return: Zone thickness in meters
    """
    segment = params.bridge_segments_array[segment_idx]

    # Get thickness - dz for zones 1 and 3, dz_2 for zone 2
    return getattr(segment, "dz", 0.5) if zone_position in [1, 3] else getattr(segment, "dz_2", 0.5)


def _get_excluded_x_ranges(
    supports: list[SupportLocation],
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
) -> list[tuple[float, float]]:
    """
    Get X ranges that should be excluded from regular strip placement (support strip areas).

    :param supports: List of support locations
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: Segment index (0-based)
    :param params: Bridge parameters
    :return: List of (x_min, x_max) tuples representing excluded ranges
    """
    excluded_ranges = []
    thickness = _get_zone_thickness(params, zone_position, segment_idx)
    support_strip_length = SUPPORT_STRIP_FACTOR * thickness

    for support in supports:
        support_x = support["x_coord"]
        support_type = support["type"]

        if support_type == "start":
            # Support at beginning: exclude [x, x + length]
            excluded_range = (support_x, support_x + support_strip_length)
            excluded_ranges.append(excluded_range)
        elif support_type == "end":
            # Support at end: exclude [x - length, x]
            excluded_range = (support_x - support_strip_length, support_x)
            excluded_ranges.append(excluded_range)
        else:  # intermediate
            # Intermediate support: exclude both sides [x - length, x + length]
            excluded_range = (support_x - support_strip_length, support_x + support_strip_length)
            excluded_ranges.append(excluded_range)

    return excluded_ranges


def _calculate_zone_boundaries(params: Any, zone_position: int, segment_idx: int) -> ZoneBoundaries:  # noqa: ANN401
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

    return ZoneBoundaries(y_min=y_min, y_max=y_max)


def _calculate_zone_x_boundaries(params: Any, segment_idx: int) -> ZoneXBoundaries:  # noqa: ANN401
    """
    Calculate the X-axis (longitudinal) boundaries for a specific segment.

    :param params: Bridge parameters
    :param segment_idx: Segment index (0-based)
    :return: Dictionary with x_start and x_end boundaries
    """
    # Calculate cumulative length up to this segment
    x_start = sum(seg.l for seg in params.bridge_segments_array[:segment_idx])
    x_end = x_start + params.bridge_segments_array[segment_idx].l

    return ZoneXBoundaries(x_start=x_start, x_end=x_end)


def _split_range_by_exclusions(
    range_start: float,
    range_end: float,
    excluded_ranges: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """
    Split a range into segments by excluding specified sub-ranges.

    :param range_start: Start of the range to split
    :param range_end: End of the range to split
    :param excluded_ranges: List of (x_min, x_max) tuples to exclude
    :return: List of (x_min, x_max) tuples representing valid segments
    """
    if not excluded_ranges:
        return [(range_start, range_end)]

    # Sort excluded ranges by start position
    sorted_exclusions = sorted(excluded_ranges, key=lambda x: x[0])

    segments = []
    current_pos = range_start

    for orig_excl_start, orig_excl_end in sorted_exclusions:
        # Clip exclusion to range boundaries
        excl_start = max(orig_excl_start, range_start)
        excl_end = min(orig_excl_end, range_end)

        # Skip if exclusion is outside range
        if excl_end <= range_start or excl_start >= range_end:
            continue

        # Add segment before exclusion if it exists
        if current_pos < excl_start:
            segments.append((current_pos, excl_start))

        # Move position past exclusion
        current_pos = max(current_pos, excl_end)

    # Add final segment if space remains
    if current_pos < range_end:
        segments.append((current_pos, range_end))

    return segments


def _create_integration_strip_x_direction(  # noqa: PLR0913
    builder: SciaModelBuilder,
    plane_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
    excluded_ranges: list[tuple[float, float]] | None = None,
) -> None:
    """
    Create multiple integration strips in the X direction (longitudinal) for a zone.

    Creates multiple strips spaced evenly across the zone width to cover
    the complete zone surface. Avoids excluded X ranges (support strip areas).

    :param builder: The SCIA model builder instance
    :param plane_name: Name of the plane/zone (e.g., "Z1_1")
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: Segment index (0-based)
    :param params: Bridge parameters
    :param excluded_ranges: List of (x_min, x_max) tuples to exclude
    """
    # Get zone boundaries
    y_bounds = _calculate_zone_boundaries(params, zone_position, segment_idx)
    x_bounds = _calculate_zone_x_boundaries(params, segment_idx)

    excluded_ranges = excluded_ranges or []

    # Calculate zone dimensions
    zone_width_y = y_bounds["y_max"] - y_bounds["y_min"]
    zone_length_x = x_bounds["x_end"] - x_bounds["x_start"]

    # Skip if zone is too small
    if zone_width_y < 0.1 or zone_length_x < 0.1:
        return

    # Special case: zone narrower than 1m - place single strip with reduced width
    if zone_width_y < 1.0:
        strip_width = zone_width_y
        strip_y = (y_bounds["y_min"] + y_bounds["y_max"]) / 2

        # Format zone name: Z1_1 -> Z1-1
        zone_name = plane_name.replace("_", "-")

        # Split X range by excluded areas
        x_segments = _split_range_by_exclusions(x_bounds["x_start"], x_bounds["x_end"], excluded_ranges)

        half_width = strip_width / 2
        for seg_idx, (x_start, x_end) in enumerate(x_segments):
            custom_name = f"strip_dir-x_reg_{zone_name}_w-{strip_width:.2f}_nr-{seg_idx + 1}"

            builder.create_integration_strip(
                plane=plane_name,
                point_1=(x_start, strip_y, 0.0),
                point_2=(x_end, strip_y, 0.0),
                width=strip_width,
                custom_name=custom_name,
            )

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

    # Split X range by excluded areas
    x_segments = _split_range_by_exclusions(x_bounds["x_start"], x_bounds["x_end"], excluded_ranges)

    # Create integration strips
    zone_name = plane_name.replace("_", "-")
    strip_counter = 1
    for strip_y in strip_positions:
        # Create strips in each X segment
        for x_start, x_end in x_segments:
            # Generate custom name: strip_dir-{direction}_reg_{zone}_w-{width}_nr-{number}
            custom_name = f"strip_dir-x_reg_{zone_name}_w-{strip_width:.1f}_nr-{strip_counter}"

            # Create the strip with custom name
            builder.create_integration_strip(
                plane=plane_name,
                point_1=(x_start, strip_y, 0.0),
                point_2=(x_end, strip_y, 0.0),
                width=strip_width,
                custom_name=custom_name,
            )
            strip_counter += 1


def _create_integration_strip_y_direction(  # noqa: PLR0913, PLR0912, C901
    builder: SciaModelBuilder,
    plane_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
    excluded_ranges: list[tuple[float, float]] | None = None,
) -> None:
    """
    Create multiple integration strips in the Y direction (transverse) for a zone.

    Creates multiple strips spaced evenly across the zone length to cover
    the complete zone surface. Avoids excluded X ranges (support strip areas).

    :param builder: The SCIA model builder instance
    :param plane_name: Name of the plane/zone (e.g., "Z1_1")
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: Segment index (0-based)
    :param params: Bridge parameters
    :param excluded_ranges: List of (x_min, x_max) tuples to exclude
    """
    # Get zone boundaries
    y_bounds = _calculate_zone_boundaries(params, zone_position, segment_idx)
    x_bounds = _calculate_zone_x_boundaries(params, segment_idx)

    excluded_ranges = excluded_ranges or []

    # Calculate zone dimensions
    zone_width_y = y_bounds["y_max"] - y_bounds["y_min"]
    zone_length_x = x_bounds["x_end"] - x_bounds["x_start"]

    # Skip if zone is too small
    if zone_width_y < 0.1 or zone_length_x < 0.1:
        return

    # Special case: zone narrower than 1m - place single strip with reduced width
    if zone_width_y < 1.0:
        strip_width = zone_width_y
        strip_x = (x_bounds["x_start"] + x_bounds["x_end"]) / 2

        # Format zone name: Z1_1 -> Z1-1
        zone_name = plane_name.replace("_", "-")
        custom_name = f"strip_dir-y_reg_{zone_name}_w-{strip_width:.1f}_nr-1"

        builder.create_integration_strip(
            plane=plane_name,
            point_1=(strip_x, y_bounds["y_min"], 0.0),
            point_2=(strip_x, y_bounds["y_max"], 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
        return

    # Special case: zone shorter than 1m - place single strip with reduced width
    if zone_length_x < 1.0:
        strip_width = zone_length_x
        strip_x = (x_bounds["x_start"] + x_bounds["x_end"]) / 2

        # Format zone name: Z1_1 -> Z1-1
        zone_name = plane_name.replace("_", "-")
        custom_name = f"strip_dir-y_reg_{zone_name}_w-{strip_width:.1f}_nr-1"

        builder.create_integration_strip(
            plane=plane_name,
            point_1=(strip_x, y_bounds["y_min"], 0.0),
            point_2=(strip_x, y_bounds["y_max"], 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
        return

    # Standard case: zone >= 1m, use 1m strips
    strip_width = 1.0
    half_width = strip_width / 2

    # Calculate strip positions: place strips every 0.5m starting from x_min (bridge start)
    # Working forward: x_min + 0.5, x_min + 1.0, x_min + 1.5, etc.
    # This matches the bridge construction direction (X=0 to increasing X)
    strip_positions = []

    # Find the minimum allowed X (after any start exclusion zone)
    min_x_after_exclusion = x_bounds["x_start"] + half_width
    for excl_start, excl_end in excluded_ranges:
        # If exclusion starts at or near segment start, adjust min_x
        if excl_start <= x_bounds["x_start"] + 0.1:  # Exclusion at or near start
            # First regular strip should be at: exclusion_end + half_width
            candidate_min = excl_end + half_width
            min_x_after_exclusion = max(min_x_after_exclusion, candidate_min)

    # Start from minimum allowed position and work forward
    current_x = min_x_after_exclusion

    # Place strips every STRIP_SPACING (0.5m) until we reach the end
    while current_x <= x_bounds["x_end"] - half_width:
        strip_positions.append(current_x)
        current_x += STRIP_SPACING

    # Check if we need additional strips to fill gaps
    # Three cases:
    # 1. Gap <= 0.5m: No extra strip needed
    # 2. Gap > 0.5m, NO support: Add strip at boundary_x - 0.5m
    # 3. Gap > 0.5m, HAS support: Add strip at support_exclusion_start - 0.5m

    if strip_positions:
        # Find all exclusion zones that are not at the segment start
        # Sort them by start position
        interior_exclusions = [(excl_start, excl_end) for excl_start, excl_end in excluded_ranges if excl_start > x_bounds["x_start"] + 0.1]
        interior_exclusions.sort()

        # Check gap before each interior exclusion zone (support areas)
        for excl_start, excl_end in interior_exclusions:
            # Find the last regular strip before this exclusion
            strips_before_exclusion = [x for x in strip_positions if x + half_width < excl_start - 0.05]

            if strips_before_exclusion:
                last_strip_before = max(strips_before_exclusion)
                gap_start = last_strip_before + half_width  # Edge of last strip
                gap_end = excl_start  # Start of exclusion zone
                gap_size = gap_end - gap_start

                # Case 3: Gap > 0.5m with support - add strip at excl_start - 0.5m
                if gap_size > 0.5 + 0.05:  # 5cm tolerance
                    gap_fill_position = excl_start - 0.5  # 0.5m before support exclusion edge
                    if gap_fill_position > x_bounds["x_start"] and gap_fill_position not in strip_positions:
                        strip_positions.append(gap_fill_position)

        # Check gap at the segment end
        last_strip_x = max(strip_positions) if strip_positions else min_x_after_exclusion
        last_coverage_end = last_strip_x + half_width

        # Check if there's an exclusion zone at the segment end
        has_exclusion_at_end = any(excl_end >= x_bounds["x_end"] - 0.1 for _, excl_end in excluded_ranges)

        if not has_exclusion_at_end:
            # Case 2: No support at end, check gap to boundary
            gap_to_boundary = x_bounds["x_end"] - last_coverage_end

            if gap_to_boundary > 0.5 + 0.05:  # Gap > 0.5m
                # Add strip at boundary - 0.5m
                gap_fill_position = x_bounds["x_end"] - 0.5
                if gap_fill_position not in strip_positions:
                    strip_positions.append(gap_fill_position)
            # Case 1: Gap <= 0.5m - no extra strip needed (implicit)

    elif x_bounds["x_end"] - x_bounds["x_start"] >= strip_width:
        # No strips placed yet but zone is large enough, add one at minimum position
        strip_positions.append(min_x_after_exclusion)

    # Filter out strip positions that overlap with excluded ranges (support areas)
    # Check if strip's coverage area (center ± half_width) overlaps with exclusion zones
    filtered_positions = []
    for strip_x in strip_positions:
        is_excluded = False
        strip_x_min = strip_x - half_width
        strip_x_max = strip_x + half_width

        for excl_start, excl_end in excluded_ranges:
            # Check if strip's coverage area overlaps with excluded range
            # Overlap occurs if: strip_x_min < excl_end AND strip_x_max > excl_start
            if strip_x_min < excl_end and strip_x_max > excl_start:
                is_excluded = True
                break
        if not is_excluded:
            filtered_positions.append(strip_x)

    # Create integration strips
    zone_name = plane_name.replace("_", "-")
    for i, strip_x in enumerate(filtered_positions):
        # Generate custom name: strip_dir-{direction}_reg_{zone}_w-{width}_nr-{number}
        custom_name = f"strip_dir-y_reg_{zone_name}_w-{strip_width:.1f}_nr-{i + 1}"

        # Create the strip with custom name
        builder.create_integration_strip(
            plane=plane_name,
            point_1=(strip_x, y_bounds["y_min"], 0.0),
            point_2=(strip_x, y_bounds["y_max"], 0.0),
            width=strip_width,
            custom_name=custom_name,
        )


def create_all_integration_strips(builder: SciaModelBuilder, params: Any) -> None:  # noqa: ANN401
    """
    Create all integration strips for all zones in the SCIA model.

    For each zone (Z1_1, Z2_1, Z3_1, Z1_2, etc.), this function creates:
    - Support strips near support locations (width = 0.9 * thickness)
    - Regular integration strips in the X direction (longitudinal)
    - Regular integration strips in the Y direction (transverse)

    Regular strips avoid overlapping with support strip areas.

    :param builder: The SCIA model builder instance
    :param params: Bridge parameters
    """
    _create_integration_strips_internal(builder, params, filter_strip_names=None)


def create_selective_integration_strips(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    governing_strip_names: set[str],
) -> dict[str, int]:
    """
    Create ONLY the integration strips specified in governing_strip_names.

    This is used for Stage 2 analysis where we model only the governing strips
    identified from Stage 1. Uses the same creation logic as create_all_integration_strips
    but filters by strip name.

    :param builder: The SCIA model builder instance
    :param params: Bridge parameters
    :param governing_strip_names: Set of strip names to create (e.g., {'strip_dir-x_reg_Z1-1_w-1.0_nr-1', ...})
    :return: Statistics dictionary with 'created', 'skipped', and 'total_attempted' counts
    """
    return _create_integration_strips_internal(builder, params, filter_strip_names=governing_strip_names)


def _create_integration_strips_internal(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    filter_strip_names: set[str] | None = None,
) -> dict[str, int]:
    """
    Internal function to create integration strips with optional filtering.

    :param builder: The SCIA model builder instance
    :param params: Bridge parameters
    :param filter_strip_names: If provided, only create strips with names in this set
    :return: Statistics dictionary with 'created', 'skipped', 'total_attempted' counts (empty dict if no filtering)
    """
    # Wrap the builder to intercept create_integration_strip calls
    wrapper = None
    if filter_strip_names is not None:
        wrapper = _FilteringBuilderWrapper(builder, filter_strip_names)
        builder = wrapper

    # Get all support locations first
    supports = _get_support_locations(params)

    # Get number of segments
    num_segments = len(params.bridge_segments_array)

    # Iterate through segments (starting from segment 1)
    for segment_idx in range(1, num_segments):
        segment_num = segment_idx  # Segment number for naming (1-based for plates)

        # Create integration strips for each zone in this segment
        for zone_position in [1, 2, 3]:
            plane_name = f"Z{zone_position}_{segment_num}"

            # Get excluded X ranges (support strip areas)
            excluded_ranges = _get_excluded_x_ranges(supports, zone_position, segment_idx, params)

            # Create support strips at relevant support locations
            _create_support_strips(
                builder=builder,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                supports=supports,
            )

            # Create regular integration strips in X direction (longitudinal)
            # These will avoid the support strip areas
            _create_integration_strip_x_direction(
                builder=builder,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                excluded_ranges=excluded_ranges,
            )

            # Create regular integration strips in Y direction (transverse)
            # These will avoid the support strip areas
            _create_integration_strip_y_direction(
                builder=builder,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                excluded_ranges=excluded_ranges,
            )

    # Log and return filtering statistics if filtering was applied
    if wrapper is not None:
        stats = wrapper.get_stats()
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Selective strip creation: {stats['created']} created, "
            f"{stats['skipped']} skipped out of {stats['total_attempted']} total"
        )
        return stats
    
    return {}



def _create_support_strips(  # noqa: PLR0913, PLR0912, C901
    builder: SciaModelBuilder,
    plane_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
    supports: list[SupportLocation],
) -> None:
    """
    Create support strips near support locations for a zone.

    Support strips have width = 0.9 * thickness and are placed near supports.
    Since segments are defined by rows in bridge_segments_array, we need to check
    if supports exist at the segment boundaries (start or end X coordinates).

    :param builder: The SCIA model builder instance
    :param plane_name: Name of the plane/zone (e.g., "Z1_1")
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: Segment index (1-based, matching segment numbering)
    :param params: Bridge parameters
    :param supports: List of support locations
    """
    y_bounds = _calculate_zone_boundaries(params, zone_position, segment_idx)
    x_bounds = _calculate_zone_x_boundaries(params, segment_idx)

    thickness = _get_zone_thickness(params, zone_position, segment_idx)
    support_strip_width = SUPPORT_STRIP_FACTOR * thickness
    half_width = support_strip_width / 2

    zone_name = plane_name.replace("_", "-")

    for support in supports:
        support_x = support["x_coord"]
        support_type = support["type"]

        # Check if support is at segment start or end boundary
        at_start = abs(support_x - x_bounds["x_start"]) < 0.01
        at_end = abs(support_x - x_bounds["x_end"]) < 0.01

        if not (at_start or at_end):
            continue

        # Determine which side(s) to place strips
        strip_locations = []
        if support_type == "start":
            # Right side only
            strip_x = support_x + half_width
            if x_bounds["x_start"] <= strip_x <= x_bounds["x_end"]:
                strip_locations.append(("right", strip_x))
        elif support_type == "end":
            # Left side only
            strip_x = support_x - half_width
            if x_bounds["x_start"] <= strip_x <= x_bounds["x_end"]:
                strip_locations.append(("left", strip_x))
        else:  # intermediate
            # Both sides
            strip_x_left = support_x - half_width
            strip_x_right = support_x + half_width
            if x_bounds["x_start"] <= strip_x_left <= x_bounds["x_end"]:
                strip_locations.append(("left", strip_x_left))
            if x_bounds["x_start"] <= strip_x_right <= x_bounds["x_end"]:
                strip_locations.append(("right", strip_x_right))

        # Create Y-direction strip (transverse, perpendicular to support)
        for side, strip_x_center in strip_locations:
            custom_name = f"strip_dir-y_sup-{support_x:.1f}_{zone_name}_w-{support_strip_width:.2f}_nr-1"

            builder.create_integration_strip(
                plane=plane_name,
                point_1=(strip_x_center, y_bounds["y_min"], 0.0),
                point_2=(strip_x_center, y_bounds["y_max"], 0.0),
                width=support_strip_width,
                custom_name=custom_name,
            )

        # Create X-direction strips (longitudinal, along support area)
        # These follow standard rules but with limited length
        for side, strip_x_base in strip_locations:
            # Define the X range for these strips
            if support_type == "start":
                x_min = support_x
                x_max = min(support_x + support_strip_width, x_bounds["x_end"])
            elif support_type == "end" or side == "left":
                x_min = max(support_x - support_strip_width, x_bounds["x_start"])
                x_max = support_x
            else:  # right
                x_min = support_x
                x_max = min(support_x + support_strip_width, x_bounds["x_end"])

            # Create X strips following standard spacing rules
            _create_support_x_strips(
                builder=builder,
                plane_name=plane_name,
                zone_name=zone_name,
                y_bounds=y_bounds,
                x_min=x_min,
                x_max=x_max,
                support_x=support_x,
                side=side,
            )


def _create_support_x_strips(  # noqa: PLR0913
    builder: SciaModelBuilder,
    plane_name: str,
    zone_name: str,
    y_bounds: ZoneBoundaries,
    x_min: float,
    x_max: float,
    support_x: float,
    side: str,  # noqa: ARG001
) -> None:
    """
    Create X-direction strips in support area.

    :param builder: The SCIA model builder instance
    :param plane_name: Name of the plane/zone
    :param zone_name: Formatted zone name (Z1-1)
    :param y_bounds: Y boundaries of zone
    :param x_min: Minimum X for strips
    :param x_max: Maximum X for strips
    :param support_x: Support X coordinate
    :param side: 'left' or 'right'
    """
    zone_width_y = y_bounds["y_max"] - y_bounds["y_min"]

    # Special case: zone narrower than 1m
    if zone_width_y < 1.0:
        strip_width = zone_width_y
        strip_y = (y_bounds["y_min"] + y_bounds["y_max"]) / 2

        custom_name = f"strip_dir-x_sup-{support_x:.1f}_{zone_name}_w-{strip_width:.2f}_nr-1"

        builder.create_integration_strip(
            plane=plane_name,
            point_1=(x_min, strip_y, 0.0),
            point_2=(x_max, strip_y, 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
        return

    # Standard case: place strips every 0.5m
    strip_width = 1.0
    half_width = strip_width / 2

    strip_positions = []
    current_y = y_bounds["y_max"] - 0.5

    while current_y >= y_bounds["y_min"] + half_width:
        strip_positions.append(current_y)
        current_y -= 0.5

    # Add bottom strip if needed
    if strip_positions:
        lowest_strip_y = strip_positions[-1]
        lowest_coverage_bottom = lowest_strip_y - half_width
        if lowest_coverage_bottom > y_bounds["y_min"] + 0.05:
            strip_positions.append(y_bounds["y_min"] + half_width)
    else:
        strip_positions.append(y_bounds["y_min"] + half_width)

    for i, strip_y in enumerate(strip_positions):
        custom_name = f"strip_dir-x_sup-{support_x:.1f}_{zone_name}_w-{strip_width:.1f}_nr-{i + 1}"

        builder.create_integration_strip(
            plane=plane_name,
            point_1=(x_min, strip_y, 0.0),
            point_2=(x_max, strip_y, 0.0),
            width=strip_width,
            custom_name=custom_name,
        )
