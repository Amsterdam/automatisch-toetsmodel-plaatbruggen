"""
Module for defining section on plane objects in SCIA.

This module handles the creation of section planes for bridge spans, including
special handling for spans with intermediate segments and zone boundaries.

For detailed documentation on how section plane creation works, see:
docs/scia_section_on_plane_logic.md
"""

from typing import Any

from src.data_models.scia_models import Boundary, Section, SectionOnPlaneDefinition, Span
from src.integrations.scia_integration.constants.geometry import (
    SECTION_ON_PLANE_INTERMEDIATE_OFFSET,
    SECTION_ON_PLANE_LENGTH,
    SECTION_ON_PLANE_NARROW_BZ2_THRESHOLD,
    SECTION_ON_PLANE_OFFSET_FACTOR,
    SECTION_ON_PLANE_SPACING,
    SECTION_ON_PLANE_TOLERANCE,
)
from src.integrations.scia_integration.model.scia_model_interface import SciaModelBuilder, SciaSectionOnPlane
from src.integrations.scia_integration.types import BridgeParametrization


def _create_span_from_segments(
    current_span_segments: list[Any],
    span_start_x: float,
    span_index: int,
    bridge_dz: float,
    bridge_dz_2: float,
) -> Span:
    """
    Create a Span object from a list of segments.

    Validates that all segments have consistent zone widths, then creates and returns a Span object.

    Note: Thickness values (dz, dz_2) are provided as parameters because only the first segment
    in the entire bridge has editable thickness fields in the parametrization. Other segments
    have OutputFields that display but don't store these values.

    :param current_span_segments: List of segments that form the span
    :type current_span_segments: list[Any]
    :param span_start_x: X-coordinate where the span starts in [m]
    :type span_start_x: float
    :param span_index: Index of the span (1-based)
    :type span_index: int
    :param bridge_dz: Thickness of zones 1 and 3 from first bridge segment [m]
    :type bridge_dz: float
    :param bridge_dz_2: Thickness of zone 2 from first bridge segment [m]
    :type bridge_dz_2: float
    :returns: Span object representing the identified span
    :rtype: Span
    :raises ValueError: If segments have inconsistent zone widths
    """
    span_length = sum(seg.l for seg in current_span_segments[1:])  # Skip first segment (l=0)
    span_end_x = span_start_x + span_length

    # Get zone widths from the first segment (they should be consistent)
    bz1 = current_span_segments[0].bz1
    bz2 = current_span_segments[0].bz2
    bz3 = current_span_segments[0].bz3

    # Verify all segments in the span have the same zone widths
    for seg in current_span_segments:
        if seg.bz1 != bz1 or seg.bz2 != bz2 or seg.bz3 != bz3:
            msg = f"Inconsistent zone widths in span {span_index}. All segments in a span must have the same bz1, bz2, and bz3 values."
            raise ValueError(msg)

    span_width = bz1 + bz2 + bz3
    min_thickness = min(bridge_dz, bridge_dz_2)

    # Calculate intermediate segment boundaries (x-coordinates where segments meet)
    intermediate_segment_x_positions = []
    current_x = span_start_x
    for seg in current_span_segments[1:-1]:  # Skip first and last segment
        current_x += seg.l
        intermediate_segment_x_positions.append(current_x)

    num_segment_definitions = len(current_span_segments)

    return Span(
        start_x=span_start_x,
        end_x=span_end_x,
        length=span_length,
        width=span_width,
        bz1=bz1,
        bz2=bz2,
        bz3=bz3,
        min_thickness=min_thickness,
        span_index=span_index,
        num_segment_definitions=num_segment_definitions,
        intermediate_segment_x_positions=intermediate_segment_x_positions,
    )


def _identify_spans(segments: list[Any]) -> list[Span]:
    """
    Identify spans from the bridge segments.

    A span is defined by segments between two supports. It starts at a support
    and continues through segments without supports until reaching the next support.

    Note: Thickness values (dz, dz_2) are read from the first bridge segment only,
    as per the parametrization design where only the first segment has editable thickness fields.

    :param segments: List of bridge segments from params.bridge_segments_array
    :type segments: list[Any]
    :returns: List of identified spans
    :rtype: list[Span]
    :raises ValueError: If span has inconsistent zone widths across segments
    """
    if not segments:
        return []

    # Get thickness values from the first segment (they're uniform across the entire bridge)
    first_segment = segments[0]
    bridge_dz = getattr(first_segment, "dz", 0.7)  # Fallback to default if not present
    bridge_dz_2 = getattr(first_segment, "dz_2", 0.8)  # Fallback to default if not present

    spans = []
    current_span_segments = []
    x_position = 0.0
    span_index = 0

    for segment in segments:
        # Skip the first segment (is_first_segment=True, l=0)
        if segment.is_first_segment:
            current_span_segments = [segment]
            continue

        # Add segment to current span
        current_span_segments.append(segment)

        # Check if this segment ends with a support (end of span)
        if segment.is_support != "Nee":
            span_index += 1
            span = _create_span_from_segments(current_span_segments, x_position, span_index, bridge_dz, bridge_dz_2)
            spans.append(span)

            # Update x_position for next span
            x_position = span.end_x

            # Start new span with the current segment as the first segment
            current_span_segments = [segment]

    # Handle incomplete span at the end (if segments don't end with a support)
    if current_span_segments and len(current_span_segments) > 1:
        span_index += 1
        span = _create_span_from_segments(current_span_segments, x_position, span_index, bridge_dz, bridge_dz_2)
        spans.append(span)

    return spans


def _generate_positions_with_spacing(  # noqa: PLR0913
    start: float,
    end: float,
    spacing: float,
    section_length: float,
    tolerance: float,
    *,
    section_extends_forward: bool = True,
) -> list[float]:
    """
    Generate positions with regular spacing from start to end.

    :param start: Start position in [m]
    :type start: float
    :param end: End limit position in [m]
    :type end: float
    :param spacing: Spacing between positions in [m]
    :type spacing: float
    :param section_length: Length of each section in [m]
    :type section_length: float
    :param tolerance: Tolerance for endpoint inclusion in [m]
    :type tolerance: float
    :param section_extends_forward: If True, section extends forward from position (x-dir or y-down).
                                     If False, position is the section itself (y-dir x-positions)
    :type section_extends_forward: bool
    :returns: List of positions
    :rtype: list[float]
    """
    positions = []
    current = start

    if section_extends_forward:
        # For x-direction or y-direction sections extending from the position
        while current + section_length <= end + tolerance:
            positions.append(current)
            current += spacing

        # Add final position if needed
        if positions:
            if section_length > 0:  # X-direction or y-direction extending
                last_section_end = positions[-1] + section_length
                if last_section_end < end - tolerance:
                    positions.append(end - section_length)
            # Point positions (for y-direction x-positions)
            elif abs(positions[-1] - end) > tolerance:
                positions.append(end)
    else:
        # For point positions (y-direction x-coordinates)
        while current <= end + tolerance:
            positions.append(current)
            current += spacing

        # Add endpoint if needed
        if positions and abs(positions[-1] - end) > tolerance:
            positions.append(end)

    return positions


def _add_boundary_positions(boundaries: list[Boundary]) -> list[float]:
    """
    Generate positions at boundary ± offset for all boundaries.

    :param boundaries: List of Boundary objects
    :type boundaries: list[Boundary]
    :returns: List of positions at boundaries with offsets
    :rtype: list[float]
    """
    positions = []
    for boundary in boundaries:
        pos_before, pos_after = boundary.get_positions_at_boundary()
        positions.extend([pos_before, pos_after])
    return positions


def _filter_positions_for_boundaries(  # noqa: PLR0913, C901, PLR0912
    positions: list[float],
    section_length: float,
    boundaries: list[Boundary],
    tolerance: float,
    strict_tolerance: float,
    *,
    is_extending_section: bool = True,
    extends_forward: bool = True,
) -> list[float]:
    """
    Filter positions to avoid boundaries and add boundary positions.

    Unified filtering for all boundary types and section directions.

    :param positions: List of positions to filter
    :type positions: list[float]
    :param section_length: Length of each section in [m] (0 for point sections)
    :type section_length: float
    :param boundaries: List of Boundary objects to avoid
    :type boundaries: list[Boundary]
    :param tolerance: Regular tolerance for boundary detection in [m]
    :type tolerance: float
    :param strict_tolerance: Strict tolerance for final filtering in [m]
    :type strict_tolerance: float
    :param is_extending_section: True for sections with length, False for point sections
    :type is_extending_section: bool
    :param extends_forward: True if section extends forward (x-dir), False if backward (y-dir down)
    :type extends_forward: bool
    :returns: Filtered and adjusted list of positions
    :rtype: list[float]
    """
    if not boundaries:
        return positions

    boundary_positions = [b.position for b in boundaries]
    filtered = []

    # Filter out positions that conflict with boundaries
    for pos in positions:
        if is_extending_section and section_length > 0:
            # Create section to check for conflicts
            if extends_forward:
                section = Section(start=pos, end=pos + section_length, direction="x")
            else:
                section = Section(start=pos, end=pos - section_length, direction="y")

            # Check if section crosses or touches any boundary
            has_conflict = any(section.crosses_or_touches_boundary(bp, tolerance) for bp in boundary_positions)
            if not has_conflict:
                filtered.append(pos)
        else:
            # Point section (y-direction x-coordinate) - check if position is too close to any boundary
            has_conflict = any(abs(pos - bp) < boundaries[0].offset for bp in boundary_positions)
            if not has_conflict:
                filtered.append(pos)

    # Add positions at boundaries with offset
    boundary_offset_positions = _add_boundary_positions(boundaries)

    # For x-direction sections extending forward, add edge sections at each boundary
    if extends_forward and section_length > 0:
        edge_positions = []
        for boundary in boundaries:
            # Edge section ending before boundary: end at boundary - offset, start at end - section_length
            section_end = boundary.position - boundary.offset
            section_start = section_end - section_length
            edge_positions.append(section_start)

            # Edge section starting after boundary: start at boundary + offset
            section_start = boundary.position + boundary.offset
            edge_positions.append(section_start)

        boundary_offset_positions.extend(edge_positions)

    # For y-direction sections extending downward, add edge sections at each boundary
    if not extends_forward and section_length > 0:
        edge_positions = []
        for boundary in boundaries:
            # Edge section in zone above boundary (ending just above boundary)
            # Section extends downward and ends at boundary + offset (above the boundary in y-coord)
            # End (bottom) = boundary + offset
            # Start (top) = end + section_length
            section_end_above = boundary.position + boundary.offset
            section_start_above = section_end_above + section_length
            edge_positions.append(section_start_above)

            # Edge section in zone below boundary (starting just below boundary)
            # Section starts at boundary - offset (below the boundary in y-coord)
            # Start (top) = boundary - offset
            section_start_below = boundary.position - boundary.offset
            edge_positions.append(section_start_below)

        boundary_offset_positions.extend(edge_positions)

    # Combine filtered and boundary positions
    all_positions = filtered + boundary_offset_positions

    # Final strict filtering for x-direction extending sections
    if extends_forward and section_length > 0:
        final_positions = []
        for pos in all_positions:
            section = Section(start=pos, end=pos + section_length, direction="x")
            has_conflict = any(section.crosses_or_touches_boundary(bp, strict_tolerance) for bp in boundary_positions)
            if not has_conflict:
                final_positions.append(pos)
        return sorted(set(final_positions))

    # Final strict filtering for y-direction extending sections
    if not extends_forward and section_length > 0:
        final_positions = []
        for pos in all_positions:
            section = Section(start=pos, end=pos - section_length, direction="y")
            has_conflict = any(section.crosses_or_touches_boundary(bp, strict_tolerance) for bp in boundary_positions)
            if not has_conflict:
                final_positions.append(pos)
        return sorted(set(final_positions), reverse=True)

    return sorted(set(all_positions), reverse=(not extends_forward))


class SectionGridGenerator:
    """
    Generates section grid for a single span with boundary awareness.

    :param span: The span to generate sections for
    :type span: Span
    :param section_length: Length of each section in [m]
    :type section_length: float
    :param spacing: Spacing between sections in [m]
    :type spacing: float
    :param offset_factor: Factor for edge offsets (multiplied by min_thickness)
    :type offset_factor: float
    :param intermediate_offset: Offset from boundaries in [m]
    :type intermediate_offset: float
    :param tolerance: Tolerance for position calculations in [m]
    :type tolerance: float
    """

    def __init__(  # noqa: PLR0913
        self,
        span: Span,
        section_length: float,
        spacing: float,
        offset_factor: float,
        intermediate_offset: float,
        tolerance: float,
    ) -> None:
        """Initialize the section grid generator."""
        self.span = span
        self.section_length = section_length
        self.spacing = spacing
        self.offset_factor = offset_factor
        self.intermediate_offset = intermediate_offset
        self.tolerance = tolerance
        self.strict_tolerance = intermediate_offset / 2

        # Calculate boundaries
        self.segment_boundaries = [
            Boundary(position=pos, offset=intermediate_offset, boundary_type="segment") for pos in span.intermediate_segment_x_positions
        ]
        self.zone_boundaries = self._calculate_zone_boundaries()

        # Calculate span limits
        self.x_start = span.start_x + offset_factor * span.min_thickness
        self.x_end = span.end_x - offset_factor * span.min_thickness
        self.y_top = span.bz1 + span.bz2 / 2
        self.y_bottom = -(span.bz3 + span.bz2 / 2)

    def _calculate_zone_boundaries(self) -> list[Boundary]:
        """
        Calculate zone boundary positions.

        :returns: List of zone boundaries
        :rtype: list[Boundary]
        """
        return [
            Boundary(position=self.span.bz2 / 2, offset=self.intermediate_offset, boundary_type="zone"),
            Boundary(position=-self.span.bz2 / 2, offset=self.intermediate_offset, boundary_type="zone"),
        ]

    def _generate_x_positions_for_x_sections(self) -> list[float]:
        """
        Generate x-positions for x-direction sections.

        :returns: List of x-positions
        :rtype: list[float]
        """
        positions = _generate_positions_with_spacing(
            self.x_start,
            self.x_end,
            self.spacing,
            self.section_length,
            self.tolerance,
            section_extends_forward=True,
        )

        # Filter for intermediate segment boundaries if present
        if self.span.num_segment_definitions > 2:
            positions = _filter_positions_for_boundaries(
                positions,
                self.section_length,
                self.segment_boundaries,
                self.tolerance,
                self.strict_tolerance,
                is_extending_section=True,
                extends_forward=True,
            )

        return positions

    def _generate_y_positions_for_x_sections(self) -> list[float]:
        """
        Generate y-positions for x-direction sections (where horizontal lines are placed).

        :returns: List of y-positions
        :rtype: list[float]
        """
        # Generate positions from top to bottom
        positions = []
        y_current = self.y_top
        while y_current >= self.y_bottom:
            positions.append(y_current)
            y_current -= self.spacing

        # Add final position if needed
        if positions and positions[-1] > self.y_bottom + self.tolerance:
            positions.append(self.y_bottom)

        # Filter for zone boundaries
        positions = _filter_positions_for_boundaries(
            positions,
            0,  # Point sections (lines at y-coordinate)
            self.zone_boundaries,
            self.tolerance,
            self.strict_tolerance,
            is_extending_section=False,
            extends_forward=True,
        )

        return sorted(positions, reverse=True)

    def _generate_x_positions_for_y_sections(self) -> list[float]:
        """
        Generate x-positions for y-direction sections (where vertical sections are placed).

        :returns: List of x-positions
        :rtype: list[float]
        """
        positions = _generate_positions_with_spacing(
            self.x_start,
            self.x_end,
            self.spacing,
            0,  # Point positions
            self.tolerance,
            section_extends_forward=False,
        )

        # Filter for intermediate segment boundaries if present
        if self.span.num_segment_definitions > 2:
            # Remove positions too close to boundaries
            filtered = []
            for pos in positions:
                is_valid = all(abs(pos - boundary.position) >= self.intermediate_offset for boundary in self.segment_boundaries)
                if is_valid:
                    filtered.append(pos)

            # Add positions at boundaries
            boundary_positions = _add_boundary_positions(self.segment_boundaries)
            return sorted(set(filtered + boundary_positions))

        return positions

    def _generate_y_positions_for_y_sections(self) -> list[float]:
        """
        Generate y-positions for y-direction sections (top of downward-extending sections).

        :returns: List of y-positions
        :rtype: list[float]
        """
        # Generate positions from top downward
        positions = []
        y_current = self.y_top
        while y_current - self.section_length >= self.y_bottom - self.tolerance:
            positions.append(y_current)
            y_current -= self.spacing

        # Add final position if needed
        if positions:
            last_bottom = positions[-1] - self.section_length
            if last_bottom > self.y_bottom + self.tolerance:
                positions.append(self.y_bottom + self.section_length)

        # Filter for zone boundaries
        return _filter_positions_for_boundaries(
            positions,
            self.section_length,
            self.zone_boundaries,
            self.tolerance,
            self.strict_tolerance,
            is_extending_section=True,
            extends_forward=False,
        )

    def generate_x_direction_sections(self) -> list[SectionOnPlaneDefinition]:
        """
        Generate all x-direction sections for the span.

        :returns: List of x-direction section definitions
        :rtype: list[SectionOnPlaneDefinition]
        """
        x_positions = self._generate_x_positions_for_x_sections()
        y_positions = self._generate_y_positions_for_x_sections()

        sections = []
        for i, x_pos in enumerate(x_positions):
            for j, y_pos in enumerate(y_positions):
                sections.append(
                    SectionOnPlaneDefinition(
                        name=f"span_{self.span.span_index}_x_sec_{i}_{j}",
                        point_1=(x_pos, y_pos, 0.0),
                        point_2=(x_pos + self.section_length, y_pos, 0.0),
                        draw=None,
                        direction_of_cut=None,
                    )
                )

        return sections

    def generate_y_direction_sections(self) -> list[SectionOnPlaneDefinition]:
        """
        Generate all y-direction sections for the span.

        :returns: List of y-direction section definitions
        :rtype: list[SectionOnPlaneDefinition]
        """
        x_positions = self._generate_x_positions_for_y_sections()
        y_positions = self._generate_y_positions_for_y_sections()

        sections = []
        for i, x_pos in enumerate(x_positions):
            for j, y_pos in enumerate(y_positions):
                sections.append(
                    SectionOnPlaneDefinition(
                        name=f"span_{self.span.span_index}_y_sec_{i}_{j}",
                        point_1=(x_pos, y_pos, 0.0),
                        point_2=(x_pos, y_pos - self.section_length, 0.0),
                        draw=None,
                        direction_of_cut=None,
                    )
                )

        return sections

    def generate_special_sections_for_narrow_bz2(self) -> list[SectionOnPlaneDefinition]:
        """
        Generate special sections when bz2 <= SECTION_ON_PLANE_NARROW_BZ2_THRESHOLD.

        Creates:
        - X-direction sections at y=0 (centerline)
        - Y-direction sections spanning the bz2 zone interior

        :returns: List of special section definitions
        :rtype: list[SectionOnPlaneDefinition]
        """
        sections: list[SectionOnPlaneDefinition] = []

        if self.span.bz2 > SECTION_ON_PLANE_NARROW_BZ2_THRESHOLD:
            return sections

        x_positions_x = self._generate_x_positions_for_x_sections()
        x_positions_y = self._generate_x_positions_for_y_sections()

        # Special x-direction sections at y=0
        for i, x_pos in enumerate(x_positions_x):
            sections.append(
                SectionOnPlaneDefinition(
                    name=f"span_{self.span.span_index}_x_sec_y0_{i}",
                    point_1=(x_pos, 0.0, 0.0),
                    point_2=(x_pos + self.section_length, 0.0, 0.0),
                    draw=None,
                    direction_of_cut=None,
                )
            )

        # Special y-direction sections spanning bz2 interior
        top_zone_boundary = self.span.bz2 / 2
        bottom_zone_boundary = -self.span.bz2 / 2
        special_section_top = top_zone_boundary - self.intermediate_offset
        special_section_bottom = bottom_zone_boundary + self.intermediate_offset

        for i, x_pos in enumerate(x_positions_y):
            sections.append(
                SectionOnPlaneDefinition(
                    name=f"span_{self.span.span_index}_y_sec_special_{i}",
                    point_1=(x_pos, special_section_top, 0.0),
                    point_2=(x_pos, special_section_bottom, 0.0),
                    draw=None,
                    direction_of_cut=None,
                )
            )

        return sections

    def generate_all_sections(self) -> list[SectionOnPlaneDefinition]:
        """
        Generate complete section grid for the span.

        :returns: List of all section definitions for the span
        :rtype: list[SectionOnPlaneDefinition]
        """
        sections = []
        sections.extend(self.generate_x_direction_sections())
        sections.extend(self.generate_y_direction_sections())
        sections.extend(self.generate_special_sections_for_narrow_bz2())
        return sections


def create_section_definitions(params: BridgeParametrization) -> list[SectionOnPlaneDefinition]:
    """
    Create section on plane definitions for the bridge model.

    Creates a grid of 1m sections with 0.5m overlaps for each span:
    - X-direction sections: 1m long in x, repeated every 0.5m in x and y
    - Y-direction sections: 1m long in y, repeated every 0.5m in y and x
    - Special sections for narrow zones (bz2 <= SECTION_ON_PLANE_NARROW_BZ2_THRESHOLD)

    :param params: Bridge parameters containing geometry and settings data
    :type params: BridgeParametrization
    :returns: List of SectionOnPlaneDefinition objects
    :rtype: list[SectionOnPlaneDefinition]
    """
    spans = _identify_spans(params.bridge_segments_array)

    all_sections = []
    for span in spans:
        generator = SectionGridGenerator(
            span=span,
            section_length=SECTION_ON_PLANE_LENGTH,
            spacing=SECTION_ON_PLANE_SPACING,
            offset_factor=SECTION_ON_PLANE_OFFSET_FACTOR,
            intermediate_offset=SECTION_ON_PLANE_INTERMEDIATE_OFFSET,
            tolerance=SECTION_ON_PLANE_TOLERANCE,
        )
        all_sections.extend(generator.generate_all_sections())

    return all_sections


def create_sections_on_plane(
    builder: SciaModelBuilder,
    section_definitions: list[SectionOnPlaneDefinition],
) -> list[SciaSectionOnPlane]:
    """
    Define and create section on plane objects in the SCIA model.

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param section_definitions: List of SectionOnPlaneDefinition objects
    :type section_definitions: list[SectionOnPlaneDefinition]
    :returns: List of created SectionOnPlane objects
    :rtype: list[SciaSectionOnPlane]
    """
    return [
        builder.create_section_on_plane(
            name=section_def.name,
            point_1=section_def.point_1,
            point_2=section_def.point_2,
            draw=section_def.draw,
            direction_of_cut=section_def.direction_of_cut,
        )
        for section_def in section_definitions
    ]


def create_all_sections_on_plane(
    builder: SciaModelBuilder,
    section_definitions: list[SectionOnPlaneDefinition],
) -> list[SciaSectionOnPlane]:
    """
    Define and create all section on plane objects for the bridge model.

    This function provides a consistent API pattern matching other "create_all_*" functions
    in the SCIA model builder.

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param section_definitions: List of SectionOnPlaneDefinition objects
    :type section_definitions: list[SectionOnPlaneDefinition]
    :returns: List of created SectionOnPlane objects
    :rtype: list[SciaSectionOnPlane]
    """
    return create_sections_on_plane(builder, section_definitions)
