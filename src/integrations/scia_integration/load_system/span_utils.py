"""
Utilities for identifying bridge spans from segments.

This module provides functions to identify and create spans from bridge segment data.
A span is defined by segments between two supports.

Note: These functions were previously part of scia_section_on_plane.py but are still
needed for UDL generation even after section-on-plane functionality was removed.
"""

from typing import Any

from src.data_models.scia_models import Span


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
