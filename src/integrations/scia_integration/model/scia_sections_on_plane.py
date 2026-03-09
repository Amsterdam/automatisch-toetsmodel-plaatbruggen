"""
SCIA sections on plane creation module.

This module handles the creation of SectionOnPlane objects for SCIA models.
Sections on plane are used to retrieve calculation results (forces, moments) at
specific cross-section positions along the bridge deck zones.

Placement mirrors the integration-strip coverage so that sections on plane are
created at every location where an integration strip exists:

* **X-direction sections** – longitudinal cuts at each Y position used by
  X-direction integration strips. Every 0.5 m in Y across the zone width,
  each section spans up to 1.0 m in X (step = 0.5 m) split by support
  exclusion areas.

* **Y-direction sections** – transverse cuts at each X position used by
  Y-direction integration strips. Every 0.5 m in X along the zone,
  each section spans up to 1.0 m in Y (step = 0.5 m).

* **Support sections** – cuts near support locations mirroring support strips,
  in both X and Y directions.

Naming convention
-----------------
* X regular:   ``sec_dir-x_reg_{zone}_y-{y:.2f}_nr-{n}_part-{p}``
* Y regular:   ``sec_dir-y_reg_{zone}_x-{x:.2f}_nr-{n}_part-{p}``
* X support:   ``sec_dir-x_sup-{sup_x:.1f}_{zone}_y-{y:.2f}_nr-{n}_part-{p}``
* Y support:   ``sec_dir-y_sup-{sup_x:.1f}_{zone}_nr-{n}``

This module is **completely separate** from scia_integration_strips.py.
Zone boundary helpers and support location logic are imported from that module
to avoid duplication.
"""

from typing import Any

from src.integrations.scia_integration.model.scia_integration_strips import (
    SUPPORT_STRIP_FACTOR,
    SupportLocation,
    _calculate_zone_boundaries,
    _calculate_zone_x_boundaries,
    _get_excluded_x_ranges,
    _get_support_locations,
    _get_zone_thickness,
    _split_range_by_exclusions,
)

from .scia_model_interface import SciaModelBuilder

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECTION_LENGTH: float = 1.0  # m — maximum length of each SectionOnPlane
SECTION_STEP: float = 0.5  # m — step between consecutive section starts
_FLOAT_TOL: float = 0.001  # m — tolerance for floating-point comparisons


# ---------------------------------------------------------------------------
# Generic section-start calculator (works for both X and Y spans)
# ---------------------------------------------------------------------------


def _calculate_section_starts(span_start: float, span_end: float) -> list[float]:
    """
    Return an ordered list of section start positions covering [span_start, span_end].

    Algorithm:
    1. Place full 1 m sections every 0.5 m starting from *span_start*.
    2. If the last full section does not reach *span_end* (gap > tolerance),
       append one fit section anchored at ``span_end − SECTION_LENGTH`` so that
       it ends exactly at *span_end* with a full 1 m length.
    3. If no full section fits at all (span shorter than ``SECTION_LENGTH``),
       place a single section starting at *span_start*.  The fit logic is
       **not** applied in this case because there is no preceding section to
       "attach" the fit to, and computing ``span_end − SECTION_LENGTH`` would
       produce a start *before* ``span_start`` whenever the span is smaller
       than ``SECTION_LENGTH``.

    :param span_start: Start coordinate in [m]
    :param span_end: End coordinate in [m]
    :return: Ordered list of section start coordinates
    """
    starts: list[float] = []
    current = span_start

    while current + SECTION_LENGTH <= span_end + _FLOAT_TOL:
        starts.append(current)
        current += SECTION_STEP

    # Fit section: only when at least one full section was placed AND a gap remains.
    if starts:
        last_end = starts[-1] + SECTION_LENGTH
        gap = span_end - last_end
        if gap > _FLOAT_TOL:
            fit_start = span_end - SECTION_LENGTH
            if abs(fit_start - starts[-1]) > _FLOAT_TOL:
                starts.append(fit_start)

    # Fallback: span is shorter than SECTION_LENGTH — place one section at span_start.
    if not starts:
        starts.append(span_start)

    return starts


def _get_section_end(start: float, boundary_end: float) -> float:
    """Return the end position for a section, clamped to *boundary_end*."""
    return min(start + SECTION_LENGTH, boundary_end)


# ---------------------------------------------------------------------------
# Y-position calculator for X-direction sections
# ---------------------------------------------------------------------------


def _calculate_y_positions_for_x_sections(y_min: float, y_max: float) -> list[float]:
    """
    Return Y positions at which X-direction sections should be created.

    Mirrors the Y-position logic in ``_create_integration_strip_x_direction``:
    positions placed every 0.5 m starting at y_max − 0.5, with an extra position
    at ``y_min + 0.5`` when the lowest position does not fully cover the bottom.

    :param y_min: Zone Y minimum in [m]
    :param y_max: Zone Y maximum in [m]
    :return: List of Y centre positions
    """
    zone_width = y_max - y_min
    half_width = 0.5

    if zone_width < 0.1:
        return []

    # Narrow zone: single section at zone center
    if zone_width < 1.0:
        return [(y_min + y_max) / 2.0]

    positions: list[float] = []
    current_y = y_max - 0.5
    while current_y >= y_min + half_width:
        positions.append(current_y)
        current_y -= SECTION_STEP

    # Add bottom position if the lowest position does not cover y_min
    if positions:
        if positions[-1] - half_width > y_min + 0.05:
            positions.append(y_min + half_width)
    else:
        positions.append(y_min + half_width)

    return positions


# ---------------------------------------------------------------------------
# X-position calculator for Y-direction sections
# ---------------------------------------------------------------------------


def _calculate_x_positions_for_y_sections(
    x_start: float,
    x_end: float,
    y_min: float,
    y_max: float,
    excluded_ranges: list[tuple[float, float]],
) -> list[float]:
    """
    Return X positions at which Y-direction sections should be created.

    Mirrors the X-position logic in ``_create_integration_strip_y_direction``,
    including start-exclusion adjustment and gap-filling for interior supports.

    :param x_start: Zone X start in [m]
    :param x_end: Zone X end in [m]
    :param y_min: Zone Y minimum in [m]
    :param y_max: Zone Y maximum in [m]
    :param excluded_ranges: X ranges occupied by support strips
    :return: List of filtered X centre positions
    """
    zone_length_x = x_end - x_start
    zone_width_y = y_max - y_min
    half_width = 0.5

    if zone_width_y < 0.1 or zone_length_x < 0.1:
        return []

    # Narrow or short zone: single section at centre
    if zone_width_y < 1.0 or zone_length_x < 1.0:
        return [(x_start + x_end) / 2.0]

    # Adjust start for any exclusion zone anchored at segment start
    min_x = x_start + half_width
    for excl_start, excl_end in excluded_ranges:
        if excl_start <= x_start + 0.1:
            candidate_min = excl_end + half_width
            min_x = max(min_x, candidate_min)

    positions: list[float] = []
    current_x = min_x
    while current_x <= x_end - half_width:
        positions.append(current_x)
        current_x += SECTION_STEP

    if positions:
        # Gap-filling for interior exclusion zones (intermediate supports)
        interior_exclusions = [(es, ee) for es, ee in excluded_ranges if es > x_start + 0.1]
        interior_exclusions.sort()
        for excl_start, excl_end in interior_exclusions:
            strips_before = [x for x in positions if x + half_width < excl_start - 0.05]
            if strips_before:
                last_before = max(strips_before)
                gap_size = excl_start - (last_before + half_width)
                if gap_size > 0.5 + 0.05:
                    gap_pos = excl_start - 0.5
                    if gap_pos > x_start and gap_pos not in positions:
                        positions.append(gap_pos)

        # Gap-filling at segment end (when no end-support exclusion)
        has_exclusion_at_end = any(ee >= x_end - 0.1 for _, ee in excluded_ranges)
        if not has_exclusion_at_end:
            last_x = max(positions)
            gap_to_boundary = x_end - (last_x + half_width)
            if gap_to_boundary > 0.5 + 0.05:
                gap_pos = x_end - 0.5
                if gap_pos not in positions:
                    positions.append(gap_pos)

    elif x_end - x_start >= 1.0:
        positions.append(min_x)

    # Remove positions whose coverage overlaps an exclusion zone
    filtered: list[float] = []
    for x in positions:
        if not any((x - half_width) < ee and (x + half_width) > es for es, ee in excluded_ranges):
            filtered.append(x)

    # Post-filter gap-fill: positions that overlapped the end-support exclusion were
    # removed above, which can leave a gap between the last surviving position and the
    # start of the end exclusion that was invisible before filtering.
    end_exclusions = [(es, ee) for es, ee in excluded_ranges if ee >= x_end - 0.1]
    if filtered and end_exclusions:
        excl_start = min(es for es, ee in end_exclusions)
        last_filtered = max(filtered)
        if excl_start - last_filtered > SECTION_STEP + 0.05:
            gap_pos = excl_start - half_width
            if gap_pos > last_filtered + 0.05 and gap_pos not in filtered:
                filtered.append(gap_pos)

    return filtered


# ---------------------------------------------------------------------------
# Section creation – X direction
# ---------------------------------------------------------------------------


def _create_sections_x_direction(
    builder: SciaModelBuilder,
    plane_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
    excluded_ranges: list[tuple[float, float]] | None = None,
) -> None:
    """
    Create X-direction SectionOnPlane objects at every Y position for a zone.

    One set of sections per Y position (matching integration-strip Y spacing).
    Each section spans up to 1.0 m in X (SECTION_STEP = 0.5 m). X range is
    split by support exclusion areas, identical to regular integration strips.

    :param builder: The SCIA model builder instance
    :param plane_name: SCIA plane name, e.g. ``"Z1_1"``
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: 1-based segment index
    :param params: Bridge parameters
    :param excluded_ranges: X ranges to exclude (support areas)
    """
    y_bounds = _calculate_zone_boundaries(params, zone_position, segment_idx)
    x_bounds = _calculate_zone_x_boundaries(params, segment_idx)
    excluded_ranges = excluded_ranges or []

    if (y_bounds["y_max"] - y_bounds["y_min"]) < 0.1 or (x_bounds["x_end"] - x_bounds["x_start"]) < 0.1:
        return

    zone_name = plane_name.replace("_", "-")
    y_positions = _calculate_y_positions_for_x_sections(y_bounds["y_min"], y_bounds["y_max"])
    x_segments = _split_range_by_exclusions(x_bounds["x_start"], x_bounds["x_end"], excluded_ranges)

    for y_nr, y_pos in enumerate(y_positions, start=1):
        part_nr = 1
        for x_seg_start, x_seg_end in x_segments:
            for start in _calculate_section_starts(x_seg_start, x_seg_end):
                end = _get_section_end(start, x_seg_end)
                length = end - start
                section_name = f"sec_dir-x_reg_{zone_name}_y-{y_pos:.2f}_nr-{y_nr}_part-{part_nr}_l-{length:.2f}"
                builder.create_section_on_plane(
                    point_1=(start, y_pos, 0.0),
                    point_2=(end, y_pos, 0.0),
                    name=section_name,
                )
                part_nr += 1


# ---------------------------------------------------------------------------
# Section creation – Y direction
# ---------------------------------------------------------------------------


def _create_sections_y_direction(
    builder: SciaModelBuilder,
    plane_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
    excluded_ranges: list[tuple[float, float]] | None = None,
) -> None:
    """
    Create Y-direction SectionOnPlane objects at every X position for a zone.

    One set of sections per X position (matching Y-direction integration-strip
    spacing). Each section spans up to 1.0 m in Y (SECTION_STEP = 0.5 m).

    :param builder: The SCIA model builder instance
    :param plane_name: SCIA plane name, e.g. ``"Z1_1"``
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: 1-based segment index
    :param params: Bridge parameters
    :param excluded_ranges: X ranges to exclude (support areas)
    """
    y_bounds = _calculate_zone_boundaries(params, zone_position, segment_idx)
    x_bounds = _calculate_zone_x_boundaries(params, segment_idx)
    excluded_ranges = excluded_ranges or []

    if (y_bounds["y_max"] - y_bounds["y_min"]) < 0.1 or (x_bounds["x_end"] - x_bounds["x_start"]) < 0.1:
        return

    zone_name = plane_name.replace("_", "-")
    x_positions = _calculate_x_positions_for_y_sections(
        x_bounds["x_start"],
        x_bounds["x_end"],
        y_bounds["y_min"],
        y_bounds["y_max"],
        excluded_ranges,
    )

    for nr, x_pos in enumerate(x_positions, start=1):
        for part_nr, start in enumerate(_calculate_section_starts(y_bounds["y_min"], y_bounds["y_max"]), start=1):
            end = _get_section_end(start, y_bounds["y_max"])
            length = end - start
            section_name = f"sec_dir-y_reg_{zone_name}_x-{x_pos:.2f}_nr-{nr}_part-{part_nr}_l-{length:.2f}"
            builder.create_section_on_plane(
                point_1=(x_pos, start, 0.0),
                point_2=(x_pos, end, 0.0),
                name=section_name,
            )


# ---------------------------------------------------------------------------
# Support sections
# ---------------------------------------------------------------------------


def _create_support_sections(
    builder: SciaModelBuilder,
    plane_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,  # noqa: ANN401
    supports: list[SupportLocation],
) -> None:
    """
    Create sections on plane near support locations, mirroring support strip placement.

    For each support at a segment boundary:
    * One Y-direction section (transverse cut) spanning the zone width.
    * X-direction sections at all Y positions within the support zone length.

    :param builder: The SCIA model builder instance
    :param plane_name: SCIA plane name, e.g. ``"Z1_1"``
    :param zone_position: Zone position (1, 2, or 3)
    :param segment_idx: 1-based segment index
    :param params: Bridge parameters
    :param supports: All support locations from :func:`_get_support_locations`
    """
    y_bounds = _calculate_zone_boundaries(params, zone_position, segment_idx)
    x_bounds = _calculate_zone_x_boundaries(params, segment_idx)
    thickness = _get_zone_thickness(params, zone_position, segment_idx)

    support_section_width = SUPPORT_STRIP_FACTOR * thickness
    half_width = support_section_width / 2
    zone_name = plane_name.replace("_", "-")

    for support in supports:
        support_x = support["x_coord"]
        support_type = support["type"]

        at_start = abs(support_x - x_bounds["x_start"]) < 0.01
        at_end = abs(support_x - x_bounds["x_end"]) < 0.01
        if not (at_start or at_end):
            continue

        # Determine X centre positions for support cuts (mirrors support strip logic)
        strip_locations: list[tuple[str, float]] = []
        if support_type == "start":
            x_center = support_x + half_width
            if x_bounds["x_start"] <= x_center <= x_bounds["x_end"]:
                strip_locations.append(("right", x_center))
        elif support_type == "end":
            x_center = support_x - half_width
            if x_bounds["x_start"] <= x_center <= x_bounds["x_end"]:
                strip_locations.append(("left", x_center))
        else:  # intermediate
            x_left = support_x - half_width
            x_right = support_x + half_width
            if x_bounds["x_start"] <= x_left <= x_bounds["x_end"]:
                strip_locations.append(("left", x_left))
            if x_bounds["x_start"] <= x_right <= x_bounds["x_end"]:
                strip_locations.append(("right", x_right))

        for side, x_center in strip_locations:
            # Y-direction section (transverse cut at the support X centre)
            for nr, start in enumerate(_calculate_section_starts(y_bounds["y_min"], y_bounds["y_max"]), start=1):
                end = _get_section_end(start, y_bounds["y_max"])
                length = end - start
                section_name = f"sec_dir-y_sup-{support_x:.1f}_{zone_name}_nr-{nr}_l-{length:.2f}"
                builder.create_section_on_plane(
                    point_1=(x_center, start, 0.0),
                    point_2=(x_center, end, 0.0),
                    name=section_name,
                )

            # X-direction sections at every Y position within support zone length
            if support_type == "start":
                x_min, x_max = support_x, min(support_x + support_section_width, x_bounds["x_end"])
            elif support_type == "end" or side == "left":
                x_min, x_max = max(support_x - support_section_width, x_bounds["x_start"]), support_x
            else:
                x_min, x_max = support_x, min(support_x + support_section_width, x_bounds["x_end"])

            y_positions = _calculate_y_positions_for_x_sections(y_bounds["y_min"], y_bounds["y_max"])
            for y_nr, y_pos in enumerate(y_positions, start=1):
                for part_nr, start in enumerate(_calculate_section_starts(x_min, x_max), start=1):
                    end = _get_section_end(start, x_max)
                    length = end - start
                    section_name = (
                        f"sec_dir-x_sup-{support_x:.1f}_{zone_name}_y-{y_pos:.2f}_nr-{y_nr}_part-{part_nr}_l-{length:.2f}"
                    )
                    builder.create_section_on_plane(
                        point_1=(start, y_pos, 0.0),
                        point_2=(end, y_pos, 0.0),
                        name=section_name,
                    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def create_all_sections_on_plane(builder: SciaModelBuilder, params: Any) -> None:  # noqa: ANN401
    """
    Create all SectionOnPlane objects for every zone in every segment.

    For each zone the following are created in order:
    1. Support sections (at segment start/end support boundaries)
    2. Regular X-direction sections at all Y positions (avoiding support areas)
    3. Regular Y-direction sections at all X positions (avoiding support areas)

    :param builder: The SCIA model builder instance
    :param params: Bridge parameters
    """
    supports = _get_support_locations(params)
    num_segments = len(params.bridge_segments_array)

    for segment_idx in range(1, num_segments):
        for zone_position in (1, 2, 3):
            plane_name = f"Z{zone_position}_{segment_idx}"
            excluded_ranges = _get_excluded_x_ranges(supports, zone_position, segment_idx, params)

            _create_support_sections(
                builder=builder,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                supports=supports,
            )
            _create_sections_x_direction(
                builder=builder,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                excluded_ranges=excluded_ranges,
            )
            _create_sections_y_direction(
                builder=builder,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                excluded_ranges=excluded_ranges,
            )


def create_selective_sections_on_plane(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    governing_section_names: set[str],
) -> dict[str, int]:
    """
    Create ONLY the SectionOnPlane objects whose names appear in *governing_section_names*.

    Used for Stage 2 of the two-stage analysis: after Stage 1 identifies which sections
    are governing (via the envelope), Stage 2 rebuilds the model with only those sections
    so the full-template run produces a small, fast XML output file.

    The creation logic is identical to :func:`create_all_sections_on_plane`; sections
    whose generated name is **not** in *governing_section_names* are silently skipped.

    :param builder: The SCIA model builder instance
    :param params: Bridge parameters
    :param governing_section_names: Set of section name strings to create
    :return: Stats dict with keys ``"created"``, ``"skipped"``, ``"total_attempted"``
    """
    wrapper = _FilteringSectionBuilderWrapper(builder, governing_section_names)

    supports = _get_support_locations(params)
    num_segments = len(params.bridge_segments_array)

    for segment_idx in range(1, num_segments):
        for zone_position in (1, 2, 3):
            plane_name = f"Z{zone_position}_{segment_idx}"
            excluded_ranges = _get_excluded_x_ranges(supports, zone_position, segment_idx, params)

            _create_support_sections(
                builder=wrapper,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                supports=supports,
            )
            _create_sections_x_direction(
                builder=wrapper,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                excluded_ranges=excluded_ranges,
            )
            _create_sections_y_direction(
                builder=wrapper,
                plane_name=plane_name,
                zone_position=zone_position,
                segment_idx=segment_idx,
                params=params,
                excluded_ranges=excluded_ranges,
            )

    return {
        "created": wrapper.created,
        "skipped": wrapper.skipped,
        "total_attempted": wrapper.created + wrapper.skipped,
    }


class _FilteringSectionBuilderWrapper:
    """
    Thin proxy around a :class:`SciaModelBuilder` that forwards every call
    **except** :meth:`create_section_on_plane`, which is filtered by name.

    Sections whose ``name`` is not in *allowed_names* are skipped silently.
    All other builder methods are delegated to the underlying *builder*.
    """

    def __init__(self, builder: SciaModelBuilder, allowed_names: set[str]) -> None:
        self._builder = builder
        self._allowed = allowed_names
        self.created: int = 0
        self.skipped: int = 0

    def create_section_on_plane(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        name: str = kwargs.get("name", args[2] if len(args) > 2 else "")
        if name in self._allowed:
            self.created += 1
            return self._builder.create_section_on_plane(*args, **kwargs)
        self.skipped += 1
        return None

    def __getattr__(self, item: str) -> Any:  # noqa: ANN401
        return getattr(self._builder, item)
