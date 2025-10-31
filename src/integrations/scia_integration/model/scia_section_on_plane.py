"""Module for defining section on plane objects in SCIA."""

from dataclasses import dataclass
from typing import Any

from src.data_models.scia_models import SectionOnPlaneDefinition
from src.integrations.scia_integration.constants.geometry import (
    SECTION_ON_PLANE_LENGTH,
    SECTION_ON_PLANE_OFFSET_FACTOR,
    SECTION_ON_PLANE_SPACING,
    SECTION_ON_PLANE_TOLERANCE,
)
from src.integrations.scia_integration.model.scia_model_interface import SciaModelBuilder, SciaSectionOnPlane
from src.integrations.scia_integration.types import BridgeParametrization


@dataclass
class Span:
    """
    Represents a span in the bridge structure.

    A span is defined by segments between two supports. It starts with a support
    and ends with a support, potentially containing intermediate segments without supports.

    :param start_x: X-coordinate where the span starts in [m]
    :type start_x: float
    :param end_x: X-coordinate where the span ends in [m]
    :type end_x: float
    :param length: Total length of the span in [m]
    :type length: float
    :param width: Total width of the span (bz1 + bz2 + bz3) in [m]
    :type width: float
    :param bz1: Width of zone 1 in [m]
    :type bz1: float
    :param bz2: Width of zone 2 in [m]
    :type bz2: float
    :param bz3: Width of zone 3 in [m]
    :type bz3: float
    :param min_thickness: Minimum thickness (min of dz and dz_2) in [m]
    :type min_thickness: float
    :param span_index: Index of the span (1-based)
    :type span_index: int
    """

    start_x: float
    end_x: float
    length: float
    width: float
    bz1: float
    bz2: float
    bz3: float
    min_thickness: float
    span_index: int


def _create_span_from_segments(
    current_span_segments: list[Any],
    span_start_x: float,
    span_index: int,
) -> Span:
    """
    Create a Span object from a list of segments.

    Validates that all segments have consistent zone widths and thicknesses,
    then creates and returns a Span object.

    :param current_span_segments: List of segments that form the span
    :type current_span_segments: list[Any]
    :param span_start_x: X-coordinate where the span starts in [m]
    :type span_start_x: float
    :param span_index: Index of the span (1-based)
    :type span_index: int
    :returns: Span object representing the identified span
    :rtype: Span
    :raises ValueError: If segments have inconsistent zone widths or thicknesses
    """
    span_length = sum(seg.l for seg in current_span_segments[1:])  # Skip first segment (l=0)
    span_end_x = span_start_x + span_length

    # Get zone widths and thicknesses from the first segment (they should be consistent)
    bz1 = current_span_segments[0].bz1
    bz2 = current_span_segments[0].bz2
    bz3 = current_span_segments[0].bz3
    dz = current_span_segments[0].dz
    dz_2 = current_span_segments[0].dz_2

    # Verify all segments in the span have the same zone widths and thicknesses
    for seg in current_span_segments:
        if seg.bz1 != bz1 or seg.bz2 != bz2 or seg.bz3 != bz3:
            raise ValueError(f"Inconsistent zone widths in span {span_index}. All segments in a span must have the same bz1, bz2, and bz3 values.")
        if seg.dz != dz or seg.dz_2 != dz_2:
            raise ValueError(f"Inconsistent thicknesses in span {span_index}. All segments in a span must have the same dz and dz_2 values.")

    span_width = bz1 + bz2 + bz3
    min_thickness = min(dz, dz_2)

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
    )


def _identify_spans(segments: list[Any]) -> list[Span]:
    """
    Identify spans from the bridge segments.

    A span is defined by segments between two supports. It starts at a support
    and continues through segments without supports until reaching the next support.

    :param segments: List of bridge segments from params.bridge_segments_array
    :type segments: list[Any]
    :returns: List of identified spans
    :rtype: list[Span]
    :raises ValueError: If span has inconsistent zone widths or thicknesses across segments, or if segments list is empty
    """
    if not segments:
        return []

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
            span = _create_span_from_segments(current_span_segments, x_position, span_index)
            spans.append(span)

            # Update x_position for next span
            x_position = span.end_x

            # Start new span with the current segment as the first segment
            current_span_segments = [segment]

    # Handle incomplete span at the end (if segments don't end with a support)
    # Only create a span if there are segments beyond the first one
    if current_span_segments and len(current_span_segments) > 1:
        span_index += 1
        span = _create_span_from_segments(current_span_segments, x_position, span_index)
        spans.append(span)

    return spans


def create_section_definitions(params: BridgeParametrization) -> list[SectionOnPlaneDefinition]:  # noqa: C901, PLR0912
    """
    Create section on plane definitions for the bridge model.

    Creates a grid of 1m sections with 0.5m overlaps for each span:
    - X-direction sections: 1m long in x, repeated every 0.5m in x, and every 0.5m in y
      with x-offset of +0.9 * min_thickness at span start and -0.9 * min_thickness at span end
    - Y-direction sections: 1m long in y, repeated every 0.5m in y, and every 0.5m in x
      with same x-offsets as x-direction sections

    :param params: Bridge parameters containing geometry and settings data
    :type params: BridgeParametrization
    :returns: List of SectionOnPlaneDefinition objects containing section definitions
    :rtype: list[SectionOnPlaneDefinition]
    """
    section_definitions = []
    section_length = SECTION_ON_PLANE_LENGTH
    spacing = SECTION_ON_PLANE_SPACING

    # Identify spans from segments
    spans = _identify_spans(params.bridge_segments_array)

    # Create sections for each span
    for span in spans:
        # Calculate y-coordinates for the outer edges
        # Top edge: bz1 + half of bz2
        y_top_outer = span.bz1 + span.bz2 / 2
        # Bottom edge: -(bz3 + half of bz2)
        y_bottom_outer = -(span.bz3 + span.bz2 / 2)

        # Calculate offsets
        x_offset_start = SECTION_ON_PLANE_OFFSET_FACTOR * span.min_thickness
        x_offset_end = -SECTION_ON_PLANE_OFFSET_FACTOR * span.min_thickness
        y_offset_top = 0.0  # Offset from top edge in [m] (configurable for future use)
        y_offset_bottom = 0.0  # Offset from bottom edge in [m] (configurable for future use)

        # Apply y-offsets to get the actual y-limits for sections
        y_top = y_top_outer - y_offset_top
        y_bottom = y_bottom_outer + y_offset_bottom

        # Apply x-offsets to get the actual x-limits for sections
        # Starting at span.start_x + offset_factor*min_thickness and with last section ending at or before span.end_x - offset_factor*min_thickness
        x_start = span.start_x + x_offset_start
        x_end_limit = span.end_x + x_offset_end

        # X-DIRECTION SECTIONS
        # These sections are 1m long in x-direction, repeated every 0.5m in x, and every 0.5m in y
        # Calculate x-positions for x-direction sections
        # x_positions_x_dir stores the START x-coordinate (left side) of each section
        # Sections extend rightward from this position
        x_positions_x_dir = []

        x_current = x_start
        # Continue while the END of the section (x_current + section_length) is <= x_end_limit
        while x_current + section_length <= x_end_limit:
            x_positions_x_dir.append(x_current)
            x_current += spacing

        # Add a final section if the last section doesn't reach the end
        if x_positions_x_dir:
            last_x_section_start = x_positions_x_dir[-1]
            last_x_section_end = last_x_section_start + section_length
            # Check if last section end is before x_end_limit (with tolerance)
            if last_x_section_end < x_end_limit - SECTION_ON_PLANE_TOLERANCE:
                # Add one more section with start at x_end_limit - section_length
                # This section will extend from x_end_limit - section_length (start) to x_end_limit (end)
                x_positions_x_dir.append(x_end_limit - section_length)

        # For each x-position, create sections at different y-coordinates
        # Start from the top and work downward
        # y_positions stores the y-coordinate of each horizontal section line
        y_positions = []
        y_current = y_top
        while y_current >= y_bottom:
            y_positions.append(y_current)
            y_current -= spacing

        # Add a final y position at y_bottom if the last position doesn't reach it
        if y_positions:
            last_y_position = y_positions[-1]
            if last_y_position > y_bottom + SECTION_ON_PLANE_TOLERANCE:
                y_positions.append(y_bottom)

        # Create x-direction sections at regular y positions
        for i, x_pos in enumerate(x_positions_x_dir):
            for j, y_pos in enumerate(y_positions):
                section_definitions.append(
                    SectionOnPlaneDefinition(
                        name=f"span_{span.span_index}_x_sec_{i}_{j}",
                        point_1=(x_pos, y_pos, 0.0),  # Left side of section
                        point_2=(x_pos + section_length, y_pos, 0.0),  # Right side of section (extending rightward)
                        draw=None,  # Will use default Z_DIRECTION
                        direction_of_cut=None,  # Will use default (0, 0, 1)
                    )
                )

        # Y-DIRECTION SECTIONS
        # -------------------
        # These sections are 1m long in y-direction, repeated every 0.5m in y, and every 0.5m in x

        # Calculate x-positions for y-direction sections (separate from x-direction)
        x_positions_y_dir = []
        x_current = x_start
        # Continue while we're within the span limits
        while x_current <= x_end_limit:
            x_positions_y_dir.append(x_current)
            x_current += spacing

        # Add an additional x position at x_end_limit if the last position doesn't reach it
        if x_positions_y_dir:
            last_x_position = x_positions_y_dir[-1]
            if abs(last_x_position - x_end_limit) > SECTION_ON_PLANE_TOLERANCE:
                # Add x position exactly at x_end_limit
                x_positions_y_dir.append(x_end_limit)

        # Calculate y-positions for sections (1m long in y direction)
        # Start from the top and work downward
        # y_section_positions stores the TOP y-coordinate of each section
        # Sections extend downward from this position
        y_section_positions = []
        y_current = y_top
        while y_current - section_length >= y_bottom:
            y_section_positions.append(y_current)  # Store the TOP position
            y_current -= spacing

        # Add a final section if the last section doesn't reach the bottom
        # The section is 1m long in y direction, extending downward from y_pos to y_pos - section_length
        # We want a section starting at y_bottom + section_length (top) and ending at y_bottom (bottom)
        if y_section_positions:
            last_y_section_top = y_section_positions[-1]
            last_y_section_bottom = last_y_section_top - section_length
            # Check if last section bottom is above y_bottom (with tolerance)
            if last_y_section_bottom > y_bottom + SECTION_ON_PLANE_TOLERANCE:
                # Add one more section with top at y_bottom + section_length
                # This section will extend from y_bottom + section_length (top) to y_bottom (bottom)
                y_section_positions.append(y_bottom + section_length)

        # Create y-direction sections at regular x positions
        for i, x_pos in enumerate(x_positions_y_dir):
            for j, y_pos in enumerate(y_section_positions):
                section_definitions.append(
                    SectionOnPlaneDefinition(
                        name=f"span_{span.span_index}_y_sec_{i}_{j}",
                        point_1=(x_pos, y_pos, 0.0),  # Top of section
                        point_2=(x_pos, y_pos - section_length, 0.0),  # Bottom of section (extending downward)
                        draw=None,  # Will use default Z_DIRECTION
                        direction_of_cut=None,  # Will use default (0, 0, 1)
                    )
                )

    return section_definitions


def create_sections_on_plane(
    builder: SciaModelBuilder,
    section_definitions: list[SectionOnPlaneDefinition],
) -> list[SciaSectionOnPlane]:
    """
    Define and create section on plane objects in the SCIA model.

    :param builder: The SCIA model builder instance.
    :type builder: SciaModelBuilder
    :param section_definitions: A list of SectionOnPlaneDefinition objects defining each section
    :type section_definitions: list[SectionOnPlaneDefinition]
    :returns: A list of the created SectionOnPlane objects.
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
    in the SCIA model builder (e.g., create_all_integration_strips, create_all_supports).
    Currently, it is a simple wrapper around create_sections_on_plane() but may be extended
    in the future for additional processing or validation.

    :param builder: The SCIA model builder instance.
    :type builder: SciaModelBuilder
    :param section_definitions: A list of SectionOnPlaneDefinition objects defining each section
    :type section_definitions: list[SectionOnPlaneDefinition]
    :returns: A list of the created SectionOnPlane objects.
    :rtype: list[SciaSectionOnPlane]
    """
    return create_sections_on_plane(builder, section_definitions)
