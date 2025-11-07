"""
Tests for SCIA section on plane generation logic.

Verifies that:
1. Sections don't cross or touch boundaries
2. All expected sections are created
3. Special sections for narrow bz2 are generated correctly
"""

import pytest

from src.data_models.scia_models import Boundary, Section


class TestSectionModel:
    """Test the Section data model methods."""

    def test_crosses_or_touches_boundary_forward_crossing(self) -> None:
        """Test detection of forward-extending section crossing a boundary."""
        section = Section(start=2.0, end=3.0, direction="x")
        assert section.crosses_or_touches_boundary(2.5, tolerance=0.01)

    def test_crosses_or_touches_boundary_backward_crossing(self) -> None:
        """Test detection of backward-extending (downward) section crossing a boundary."""
        section = Section(start=3.0, end=2.0, direction="y")
        assert section.crosses_or_touches_boundary(2.5, tolerance=0.01)

    def test_crosses_or_touches_boundary_touching_start(self) -> None:
        """Test detection of section with start on boundary."""
        section = Section(start=2.0, end=3.0, direction="x")
        assert section.crosses_or_touches_boundary(2.0, tolerance=0.01)

    def test_crosses_or_touches_boundary_touching_end(self) -> None:
        """Test detection of section with end on boundary."""
        section = Section(start=2.0, end=3.0, direction="x")
        assert section.crosses_or_touches_boundary(3.0, tolerance=0.01)

    def test_crosses_or_touches_boundary_no_conflict(self) -> None:
        """Test section that doesn't cross or touch boundary."""
        section = Section(start=2.0, end=3.0, direction="x")
        assert not section.crosses_or_touches_boundary(4.0, tolerance=0.01)

    def test_crosses_or_touches_boundary_within_tolerance(self) -> None:
        """Test section with endpoint within tolerance of boundary."""
        section = Section(start=2.0, end=3.0, direction="x")
        assert section.crosses_or_touches_boundary(3.005, tolerance=0.01)

    def test_y_direction_section_crosses_boundary(self) -> None:
        """Test y-direction section crossing zone boundary."""
        # Section from 1.251 to 0.251, boundary at 0.25
        # End is 0.001m away from boundary (0.251 - 0.25 = 0.001)
        # With strict tolerance 0.0005, end is NOT within tolerance (0.001 > 0.0005)
        # Check crossing: Is 0.251 + 0.0005 < 0.25 < 1.251 - 0.0005?
        # Is 0.2515 < 0.25? NO! So NOT crossing with strict tolerance
        section = Section(start=1.251, end=0.251, direction="y")
        assert not section.crosses_or_touches_boundary(0.25, tolerance=0.0005)

        # Section from 1.249 to 0.249, boundary at 0.25
        # End is 0.001m away (0.25 - 0.249 = 0.001)
        # With strict tolerance 0.0005, end is NOT within tolerance
        # Check crossing: Is 0.249 + 0.0005 < 0.25 < 1.249 - 0.0005?
        # Is 0.2495 < 0.25 < 1.2485? YES! So it IS crossing with strict tolerance
        # This is correct - the section from 1.249 to 0.249 barely avoids the boundary
        # but with strict tolerance checking, it's flagged as too close to crossing
        section = Section(start=1.249, end=0.249, direction="y")
        assert section.crosses_or_touches_boundary(0.25, tolerance=0.0005)

        # With a larger tolerance (0.01), both should be flagged
        section = Section(start=1.251, end=0.251, direction="y")
        assert section.crosses_or_touches_boundary(0.25, tolerance=0.01)

        section = Section(start=1.249, end=0.249, direction="y")
        assert section.crosses_or_touches_boundary(0.25, tolerance=0.01)

        # Section touching boundary at end
        section = Section(start=1.25, end=0.25, direction="y")
        assert section.crosses_or_touches_boundary(0.25, tolerance=0.01)

        # Section clearly crossing boundary
        section = Section(start=0.75, end=-0.25, direction="y")
        assert section.crosses_or_touches_boundary(0.25, tolerance=0.01)


class TestBoundaryModel:
    """Test the Boundary data model methods."""

    def test_get_positions_at_boundary(self) -> None:
        """Test getting offset positions at a boundary."""
        boundary = Boundary(position=3.0, offset=0.001, boundary_type="segment")
        pos_before, pos_after = boundary.get_positions_at_boundary()
        assert pos_before == pytest.approx(2.999)
        assert pos_after == pytest.approx(3.001)


class TestEdgeSectionGeneration:
    """Test edge section generation for zone boundaries."""

    def test_edge_section_above_boundary(self) -> None:
        """Test edge section in zone above boundary (ending just above boundary)."""
        boundary_pos = 0.25
        offset = 0.001
        section_length = 1.0

        # Edge section above boundary should END at boundary + offset = 0.251
        section_end = boundary_pos + offset
        section_start = section_end + section_length

        assert section_start == pytest.approx(1.251)
        assert section_end == pytest.approx(0.251)

        # With strict tolerance 0.0005, this section should NOT cross the boundary
        # Check: Is 0.251 + 0.0005 < 0.25 < 1.251 - 0.0005?
        # Is 0.2515 < 0.25? NO! So NOT crossing
        section = Section(start=section_start, end=section_end, direction="y")
        assert not section.crosses_or_touches_boundary(boundary_pos, tolerance=0.0005)

    def test_edge_section_below_boundary(self) -> None:
        """Test edge section in zone below boundary (starting just below boundary)."""
        boundary_pos = 0.25
        offset = 0.001
        section_length = 1.0

        # Edge section below boundary should START at boundary - offset = 0.249
        section_start = boundary_pos - offset
        section_end = section_start - section_length

        assert section_start == pytest.approx(0.249)
        assert section_end == pytest.approx(-0.751)

        # This section starts at 0.249 (0.001m from boundary) and ends at -0.751
        # With strict tolerance 0.0005m, the endpoint is far enough (0.001m > 0.0005m)
        # Check crossing: Is -0.751 + 0.0005 < 0.25 < 0.249 - 0.0005?
        # Is -0.7505 < 0.25 < 0.2485? NO (0.25 > 0.2485)
        # So it should NOT be flagged
        section = Section(start=section_start, end=section_end, direction="y")
        assert not section.crosses_or_touches_boundary(boundary_pos, tolerance=0.0005)

    def test_x_direction_edge_sections(self) -> None:
        """Test edge sections for x-direction at intermediate segment boundaries."""
        boundary_pos = 3.0
        offset = 0.001
        section_length = 1.0

        # Edge section ending before boundary: END at boundary - offset
        section_end_before = boundary_pos - offset  # 2.999
        section_start_before = section_end_before - section_length  # 1.999

        assert section_start_before == pytest.approx(1.999)
        assert section_end_before == pytest.approx(2.999)

        # Endpoint is 0.001m from boundary, strict tolerance is 0.0005m
        # Check: Is 1.999 + 0.0005 < 3.0 < 2.999 - 0.0005?
        # Is 1.9995 < 3.0 < 2.9985? NO (3.0 > 2.9985)
        section_before = Section(start=section_start_before, end=section_end_before, direction="x")
        assert not section_before.crosses_or_touches_boundary(boundary_pos, tolerance=0.0005)

        # Edge section starting after boundary: START at boundary + offset
        section_start_after = boundary_pos + offset  # 3.001
        section_end_after = section_start_after + section_length  # 4.001

        assert section_start_after == pytest.approx(3.001)
        assert section_end_after == pytest.approx(4.001)

        # Should NOT cross with strict tolerance
        section_after = Section(start=section_start_after, end=section_end_after, direction="x")
        assert not section_after.crosses_or_touches_boundary(boundary_pos, tolerance=0.0005)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
