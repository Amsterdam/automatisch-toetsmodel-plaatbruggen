"""
Module for defining section on plane objects in SCIA.

This module handles the creation of section planes for bridge spans, including
special handling for spans with intermediate segments and zone boundaries.

For detailed documentation on how section plane creation works, see:
docs/scia_section_on_plane_logic.md
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.data_models.scia_models import SectionOnPlaneDefinition
from src.integrations.scia_integration.constants.geometry import (
    SECTION_ON_PLANE_INTERMEDIATE_OFFSET,
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
    :param num_segment_definitions: Number of segment definition points within the span (including start and end supports)
    :type num_segment_definitions: int
    :param intermediate_segment_x_positions: X-coordinates of intermediate segment boundaries in [m]
    :type intermediate_segment_x_positions: list[float]
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
    num_segment_definitions: int
    intermediate_segment_x_positions: list[float]


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

    # Calculate intermediate segment boundaries (x-coordinates where segments meet)
    # Skip the first segment (l=0) and calculate cumulative x positions
    intermediate_segment_x_positions = []
    current_x = span_start_x

    for seg in current_span_segments[1:-1]:  # Skip first and last segment
        current_x += seg.l
        intermediate_segment_x_positions.append(current_x)

    # Count the number of segment definition points
    # This includes: start point + intermediate points + end point
    # Each segment in current_span_segments represents a definition point
    # So the total number of segment definitions = len(current_span_segments)
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


def _filter_and_adjust_x_direction_sections(
    section_positions: list[float],
    section_length: float,
    intermediate_x_positions: list[float],
) -> list[float]:
    """
    Filter and adjust x-direction section positions to avoid crossing intermediate segment boundaries.

    For sections that would cross a boundary:
    - Adds a shortened section that ends just before the boundary (at boundary - INTERMEDIATE_OFFSET)
    - Adds a section that starts just after the boundary (at boundary + INTERMEDIATE_OFFSET)

    Also ensures that for each intermediate boundary, there's always a section ending at boundary - INTERMEDIATE_OFFSET,
    even if no regular section would cross that boundary.

    :param section_positions: List of section start positions
    :type section_positions: list[float]
    :param section_length: Length of each section in [m]
    :type section_length: float
    :param intermediate_x_positions: X-coordinates of intermediate segment boundaries in [m]
    :type intermediate_x_positions: list[float]
    :returns: Adjusted list of section positions
    :rtype: list[float]
    """
    if not intermediate_x_positions:
        return section_positions

    adjusted_positions = []
    added_shortened_count = 0
    boundaries_with_sections_before = set()
    boundaries_with_sections_after = set()  # Track sections added after boundaries

    for pos in section_positions:
        section_start = pos
        section_end = pos + section_length
        # Find all boundaries crossed by this section
        boundaries_crossed = [bx for bx in intermediate_x_positions if section_start < bx < section_end]

        if not boundaries_crossed:
            # Section doesn't cross any boundary, keep it
            adjusted_positions.append(pos)
        else:
            for boundary_x in boundaries_crossed:
                # Add a section that ends just before the boundary
                end_before = boundary_x - SECTION_ON_PLANE_INTERMEDIATE_OFFSET
                start_before = end_before - section_length
                if start_before >= section_start - SECTION_ON_PLANE_TOLERANCE:
                    adjusted_positions.append(start_before)
                    boundaries_with_sections_before.add(boundary_x)
                    added_shortened_count += 1

                # Add a section that starts just after the boundary (only if not already added)
                if boundary_x not in boundaries_with_sections_after:
                    start_after = boundary_x + SECTION_ON_PLANE_INTERMEDIATE_OFFSET
                    adjusted_positions.append(start_after)
                    boundaries_with_sections_after.add(boundary_x)
                    added_shortened_count += 1

    # Ensure all boundaries have sections ending before them
    for boundary_x in intermediate_x_positions:
        if boundary_x not in boundaries_with_sections_before:
            # No section was added that ends at this boundary, add one
            end_before = boundary_x - SECTION_ON_PLANE_INTERMEDIATE_OFFSET
            start_before = end_before - section_length
            adjusted_positions.append(start_before)
            added_shortened_count += 1

        if boundary_x not in boundaries_with_sections_after:
            # Also add section after this boundary if not already added
            start_after = boundary_x + SECTION_ON_PLANE_INTERMEDIATE_OFFSET
            adjusted_positions.append(start_after)
            boundaries_with_sections_after.add(boundary_x)
            added_shortened_count += 1

    return sorted(adjusted_positions)


def _filter_section_positions_for_intermediate_segments(
    section_positions: list[float],
    section_length: float,
    intermediate_x_positions: list[float],
    is_x_direction: bool,
) -> list[float]:
    """
    Filter section positions to avoid crossing intermediate segment boundaries.

    For x-direction sections: Handled by _filter_and_adjust_x_direction_sections.

    For y-direction sections: Removes x-positions where the section (at that x)
    would violate the intermediate boundary rules.

    :param section_positions: List of section positions to filter
    :type section_positions: list[float]
    :param section_length: Length of each section in [m]
    :type section_length: float
    :param intermediate_x_positions: X-coordinates of intermediate segment boundaries in [m]
    :type intermediate_x_positions: list[float]
    :param is_x_direction: True if filtering x-direction sections, False for y-direction
    :type is_x_direction: bool
    :returns: Filtered list of section positions
    :rtype: list[float]
    """
    if not intermediate_x_positions:
        return section_positions

    if is_x_direction:
        return _filter_and_adjust_x_direction_sections(section_positions, section_length, intermediate_x_positions)

    filtered_positions = []
    removed_count = 0

    for pos in section_positions:
        # For y-direction sections, pos is an x-coordinate where we place a vertical section
        # The section doesn't extend in x, so we just need to check if it's too close to a boundary
        # Add offset constraint: must be at least INTERMEDIATE_OFFSET away from boundaries
        is_valid = True
        for boundary_x in intermediate_x_positions:
            if abs(pos - boundary_x) < SECTION_ON_PLANE_INTERMEDIATE_OFFSET:
                is_valid = False
                break
        if is_valid:
            filtered_positions.append(pos)
        else:
            removed_count += 1

    return filtered_positions


def _add_intermediate_boundary_positions(
    x_positions: list[float],
    intermediate_x_positions: list[float],
) -> list[float]:
    """
    Add section positions at intermediate segment boundaries with proper offset.

    For each intermediate boundary, adds two positions:
    - One at boundary_x - INTERMEDIATE_OFFSET (before the boundary)
    - One at boundary_x + INTERMEDIATE_OFFSET (after the boundary)

    :param x_positions: Existing list of x-positions
    :type x_positions: list[float]
    :param intermediate_x_positions: X-coordinates of intermediate segment boundaries in [m]
    :type intermediate_x_positions: list[float]
    :returns: Extended list of x-positions including boundary positions
    :rtype: list[float]
    """
    if not intermediate_x_positions:
        return x_positions

    all_positions = list(x_positions)
    added_count = 0

    for boundary_x in intermediate_x_positions:
        # Add position before the boundary
        pos_before = boundary_x - SECTION_ON_PLANE_INTERMEDIATE_OFFSET
        all_positions.append(pos_before)
        added_count += 1

        # Add position after the boundary
        pos_after = boundary_x + SECTION_ON_PLANE_INTERMEDIATE_OFFSET
        all_positions.append(pos_after)
        added_count += 1

    # Sort and return
    sorted_positions = sorted(all_positions)

    return sorted_positions


def _filter_y_positions_for_zone_boundaries_x_sections(
    y_positions: list[float],
    zone_boundary_y_positions: list[float],
) -> list[float]:
    """
    Filter y-positions for x-direction sections to avoid placing sections on zone boundaries.

    X-direction sections are horizontal lines at a specific y-coordinate. This function:
    1. Removes y-positions that are exactly on zone boundaries
    2. Adds new y-positions at zone_boundary ± INTERMEDIATE_OFFSET

    :param y_positions: List of y-coordinates for horizontal x-direction sections
    :type y_positions: list[float]
    :param zone_boundary_y_positions: Y-coordinates of zone boundaries in [m]
    :type zone_boundary_y_positions: list[float]
    :returns: Filtered and adjusted list of y-positions
    :rtype: list[float]
    """
    if not zone_boundary_y_positions:
        return y_positions

    # Step 1: Filter out positions that are on or very close to zone boundaries
    filtered_positions = []
    removed_count = 0

    for pos in y_positions:
        on_boundary = any(abs(pos - boundary_y) < SECTION_ON_PLANE_TOLERANCE for boundary_y in zone_boundary_y_positions)

        if not on_boundary:
            filtered_positions.append(pos)
        else:
            removed_count += 1

    # Step 2: Add positions at zone boundaries with offset
    for boundary_y in zone_boundary_y_positions:
        # Add position above boundary
        pos_above = boundary_y + SECTION_ON_PLANE_INTERMEDIATE_OFFSET
        filtered_positions.append(pos_above)

        # Add position below boundary
        pos_below = boundary_y - SECTION_ON_PLANE_INTERMEDIATE_OFFSET
        filtered_positions.append(pos_below)

    return sorted(filtered_positions, reverse=True)  # Sort descending (top to bottom)


def _filter_and_adjust_y_positions_for_zone_boundaries(
    y_positions: list[float],
    section_length: float,
    zone_boundary_y_positions: list[float],
) -> list[float]:
    """
    Filter y-positions to avoid crossing zone boundaries and add boundary sections.

    This function:
    1. Removes any y-positions where a y-direction section would cross a zone boundary
    2. Adds new y-positions at zone_boundary ± INTERMEDIATE_OFFSET for sections parallel to boundaries
    3. Re-checks all positions to ensure no section crosses/touches boundaries

    Y-direction sections extend DOWNWARD from y_position (top) to y_position - section_length (bottom).

    :param y_positions: List of y-positions (TOP of each y-direction section)
    :type y_positions: list[float]
    :param section_length: Length of each section in [m] (extends downward)
    :type section_length: float
    :param zone_boundary_y_positions: Y-coordinates of zone boundaries in [m]
    :type zone_boundary_y_positions: list[float]
    :returns: Filtered and adjusted list of y-positions
    :rtype: list[float]
    """
    if not zone_boundary_y_positions:
        return y_positions

    # Step 1: Filter out positions where sections would cross, start at, or end at zone boundaries
    filtered_positions = []
    removed_count = 0

    for pos in y_positions:
        # Y-direction section extends from pos (top) downward to pos - section_length (bottom)
        section_top = pos
        section_bottom = pos - section_length

        # Check each zone boundary against this section
        should_remove = False
        for boundary_y in zone_boundary_y_positions:
            # Check if boundary is between top and bottom (crossing)
            if section_bottom < boundary_y < section_top:
                should_remove = True
                break
            # Check if section top is exactly at the boundary
            if abs(section_top - boundary_y) < SECTION_ON_PLANE_TOLERANCE:
                should_remove = True
                break
            # Check if section bottom is exactly at the boundary
            if abs(section_bottom - boundary_y) < SECTION_ON_PLANE_TOLERANCE:
                should_remove = True
                break

        if not should_remove:
            filtered_positions.append(pos)
        else:
            removed_count += 1

    # Step 2: Add positions at zone boundaries with offset
    # Y-direction sections extend DOWNWARD from pos (top) to pos - section_length (bottom)

    # Sort boundaries to identify top and bottom boundaries
    sorted_boundaries = sorted(zone_boundary_y_positions, reverse=True)  # Descending order
    top_boundary = sorted_boundaries[0] if sorted_boundaries else None
    bottom_boundary = sorted_boundaries[-1] if sorted_boundaries else None

    for boundary_y in zone_boundary_y_positions:
        # Section ending just above the boundary
        # Bottom should be at boundary_y + INTERMEDIATE_OFFSET
        # Top should be at bottom + section_length
        section_bottom_above = boundary_y + SECTION_ON_PLANE_INTERMEDIATE_OFFSET
        section_top_above = section_bottom_above + section_length
        filtered_positions.append(section_top_above)

        # Section starting just below the boundary
        # Top should be at boundary_y - INTERMEDIATE_OFFSET
        section_top_below = boundary_y - SECTION_ON_PLANE_INTERMEDIATE_OFFSET
        filtered_positions.append(section_top_below)

    # Add edge sections:
    # 1. Section ending at top boundary - offset (extending from top of span)
    if top_boundary is not None:
        section_bottom_edge_top = top_boundary - SECTION_ON_PLANE_INTERMEDIATE_OFFSET
        section_top_edge_top = section_bottom_edge_top + section_length
        filtered_positions.append(section_top_edge_top)

    # 2. Section starting at bottom boundary + offset (extending to bottom of span)
    if bottom_boundary is not None:
        section_top_edge_bottom = bottom_boundary + SECTION_ON_PLANE_INTERMEDIATE_OFFSET
        section_bottom_edge_bottom = section_top_edge_bottom - section_length
        filtered_positions.append(section_top_edge_bottom)

    # Step 3: Final check - remove any positions that still cross boundaries or are exactly on boundaries
    # Sections at boundary ± INTERMEDIATE_OFFSET are intentional and should be kept
    # Use a stricter tolerance to distinguish between "exactly at boundary" vs "at boundary ± offset"
    strict_tolerance = SECTION_ON_PLANE_INTERMEDIATE_OFFSET / 2  # Half of the offset (0.0005m)
    final_positions = []
    final_removed_count = 0

    for pos in filtered_positions:
        section_top = pos
        section_bottom = pos - section_length

        should_remove = False
        removal_reason = ""

        for boundary_y in zone_boundary_y_positions:
            # Check if section crosses the boundary (boundary is strictly between top and bottom)
            if section_bottom < boundary_y < section_top:
                should_remove = True
                removal_reason = f"CROSSES boundary at {boundary_y:.4f}m"
                break

            # Check if section top is exactly at boundary (use strict tolerance)
            if abs(section_top - boundary_y) < strict_tolerance:
                should_remove = True
                removal_reason = f"top EXACTLY AT boundary {boundary_y:.4f}m (diff={abs(section_top - boundary_y):.6f}m)"
                break

            # Check if section bottom is exactly at boundary (use strict tolerance)
            if abs(section_bottom - boundary_y) < strict_tolerance:
                should_remove = True
                removal_reason = f"bottom EXACTLY AT boundary {boundary_y:.4f}m (diff={abs(section_bottom - boundary_y):.6f}m)"
                break

        if not should_remove:
            final_positions.append(pos)
        else:
            final_removed_count += 1

    return sorted(final_positions, reverse=True)  # Sort descending (top to bottom)


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

        # Calculate zone boundary y-coordinates
        # Understanding the coordinate system:
        # - bz1, bz2, bz3 are WIDTHS (not y-coordinates)
        # - y_top_outer = bz1 + bz2/2 (top of the cross-section)
        # - y_bottom_outer = -(bz3 + bz2/2) (bottom of the cross-section)
        # - bz2 is centered at y=0, extending from y=-bz2/2 to y=+bz2/2
        # - bz1 is above bz2, extending from y=bz2/2 to y=bz2/2+bz1
        # - bz3 is below bz2, extending from y=-bz2/2-bz3 to y=-bz2/2

        # Boundary between bz1 (top) and bz2 (middle) is at the bottom edge of bz1
        # This is at y = bz2/2 (top of bz2)
        y_boundary_bz1_bz2 = span.bz2 / 2

        # Boundary between bz2 (middle) and bz3 (bottom) is at the top edge of bz3
        # This is at y = -bz2/2 (bottom of bz2)
        y_boundary_bz2_bz3 = -span.bz2 / 2

        zone_boundary_y_positions = [y_boundary_bz1_bz2, y_boundary_bz2_bz3]

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

        # For spans with more than 2 segment definitions, filter positions and add intermediate boundary positions
        if span.num_segment_definitions > 2:
            original_count = len(x_positions_x_dir)

            # Filter and adjust x-direction sections that would cross intermediate segment boundaries
            # This also adds sections before and after boundaries automatically
            x_positions_x_dir = _filter_section_positions_for_intermediate_segments(
                x_positions_x_dir,
                section_length,
                span.intermediate_segment_x_positions,
                is_x_direction=True,
            )

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

        # Filter y-positions to avoid zone boundaries and add sections at boundaries
        original_y_count = len(y_positions)
        y_positions = _filter_y_positions_for_zone_boundaries_x_sections(
            y_positions,
            zone_boundary_y_positions,
        )

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

        # SPECIAL FEATURE: If bz2 <= 1.002m, add special x-direction sections at y=0
        if span.bz2 < 1.002:
            # Add x-direction sections at y=0
            for i, x_pos in enumerate(x_positions_x_dir):
                section_definitions.append(
                    SectionOnPlaneDefinition(
                        name=f"span_{span.span_index}_x_sec_y0_{i}",
                        point_1=(x_pos, 0.0, 0.0),  # Left side at y=0
                        point_2=(x_pos + section_length, 0.0, 0.0),  # Right side at y=0
                        draw=None,
                        direction_of_cut=None,
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

        # For spans with more than 2 segment definitions, filter positions and add intermediate boundary positions
        if span.num_segment_definitions > 2:
            original_count = len(x_positions_y_dir)

            # Filter out x-positions that are too close to intermediate boundaries
            x_positions_y_dir = _filter_section_positions_for_intermediate_segments(
                x_positions_y_dir,
                section_length,
                span.intermediate_segment_x_positions,
                is_x_direction=False,
            )
            # Add y-direction sections at intermediate boundaries (with offset)
            x_positions_y_dir = _add_intermediate_boundary_positions(
                x_positions_y_dir,
                span.intermediate_segment_x_positions,
            )

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

        # Apply zone boundary filtering to y-section positions
        # Y-direction sections extend downward, so they can cross zone boundaries
        original_y_count = len(y_section_positions)
        y_section_positions = _filter_and_adjust_y_positions_for_zone_boundaries(
            y_section_positions,
            section_length,
            zone_boundary_y_positions,
        )

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

        # SPECIAL FEATURE: If bz2 <= 1.002m, add special y-direction sections spanning from top to bottom zone boundary
        if span.bz2 <= 1.002:
            # These sections start at top zone boundary - offset and end at bottom zone boundary + offset
            # They span the bz2 zone with offset from both boundaries
            # Top boundary (bz1/bz2): y_boundary_bz1_bz2 = bz2/2 = 0.25m
            # Bottom boundary (bz2/bz3): y_boundary_bz2_bz3 = -bz2/2 = -0.25m
            top_zone_boundary = zone_boundary_y_positions[0]  # Upper boundary (bz1/bz2)
            bottom_zone_boundary = zone_boundary_y_positions[1]  # Lower boundary (bz2/bz3)

            # Section starts just below the top boundary (inside bz2)
            special_section_top = top_zone_boundary - SECTION_ON_PLANE_INTERMEDIATE_OFFSET
            # Section ends just above the bottom boundary (inside bz2)
            special_section_bottom = bottom_zone_boundary + SECTION_ON_PLANE_INTERMEDIATE_OFFSET

            # Create these special sections at regular x positions (following the y-direction pattern)
            for i, x_pos in enumerate(x_positions_y_dir):
                section_definitions.append(
                    SectionOnPlaneDefinition(
                        name=f"span_{span.span_index}_y_sec_special_{i}",
                        point_1=(x_pos, special_section_top, 0.0),  # Top
                        point_2=(x_pos, special_section_bottom, 0.0),  # Bottom
                        draw=None,
                        direction_of_cut=None,
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
