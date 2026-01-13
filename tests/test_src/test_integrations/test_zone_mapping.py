"""
Test module for zone mapping functionality.

This module tests the coordinate-based zone mapping between SCIA results and bridge segments:
- Longitudinal position (X) mapping to segment numbers
- Transverse position (Y) mapping to zone types (bz1, bz2, bz3)
- Zone identifier generation (format: "type-segment")
- Bridge geometry interpretation
- Edge cases and boundary conditions

Tests cover:
- Basic zone mapping for standard positions
- Segment boundary detection
- Zone type determination based on Y-coordinates
- Bridge geometry with varying segment lengths and widths
- Error handling for invalid inputs
- Unknown zone detection
"""

import pytest

from src.integrations.scia_integration.results.scia_results_processor import _map_cs_section_to_zone


class MockBridgeSegment:
    """Mock bridge segment for testing."""

    def __init__(self, length: float, bz1: float, bz2: float, bz3: float) -> None:
        """Initialize mock segment."""
        self.l = length
        self.segment_length = length  # Support both VIKTOR and Pydantic naming
        self.bz1 = bz1
        self.bz2 = bz2
        self.bz3 = bz3


class TestLongitudinalPositionMapping:
    """Tests for mapping X-coordinate to segment number."""

    @pytest.fixture
    def simple_bridge_segments(self) -> list[MockBridgeSegment]:
        """Create simple bridge with 3 equal segments."""
        return [
            MockBridgeSegment(length=0.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Segment 0 (definition)
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Segment 1
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Segment 2
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Segment 3
        ]

    def test_first_segment_mapping(self, simple_bridge_segments: list[MockBridgeSegment]) -> None:
        """Test mapping to first segment (0 < x <= 10)."""
        # Test at start, middle, and end of first segment
        test_cases = [
            (0.1, 1),  # Near start
            (5.0, 1),  # Middle
            (10.0, 1),  # At boundary
        ]

        for x, expected_segment in test_cases:
            zone = _map_cs_section_to_zone("CS1", (x, 0.0, 0.0), simple_bridge_segments)
            segment_number = int(zone.split("-")[1])
            assert segment_number == expected_segment, f"Failed for x={x}"

    def test_second_segment_mapping(self, simple_bridge_segments: list[MockBridgeSegment]) -> None:
        """Test mapping to second segment (10 < x <= 20)."""
        test_cases = [
            (10.1, 2),
            (15.0, 2),
            (20.0, 2),
        ]

        for x, expected_segment in test_cases:
            zone = _map_cs_section_to_zone("CS2", (x, 0.0, 0.0), simple_bridge_segments)
            segment_number = int(zone.split("-")[1])
            assert segment_number == expected_segment, f"Failed for x={x}"

    def test_third_segment_mapping(self, simple_bridge_segments: list[MockBridgeSegment]) -> None:
        """Test mapping to third segment (20 < x <= 30)."""
        test_cases = [
            (20.1, 3),
            (25.0, 3),
            (30.0, 3),
        ]

        for x, expected_segment in test_cases:
            zone = _map_cs_section_to_zone("CS3", (x, 0.0, 0.0), simple_bridge_segments)
            segment_number = int(zone.split("-")[1])
            assert segment_number == expected_segment, f"Failed for x={x}"

    def test_beyond_last_segment(self, simple_bridge_segments: list[MockBridgeSegment]) -> None:
        """Test that positions beyond last segment map to last segment."""
        x = 35.0  # Beyond 30m
        zone = _map_cs_section_to_zone("CS_end", (x, 0.0, 0.0), simple_bridge_segments)
        segment_number = int(zone.split("-")[1])
        assert segment_number == 3, "Should map to last segment"


class TestTransversePositionMapping:
    """Tests for mapping Y-coordinate to zone type (bz1, bz2, bz3)."""

    @pytest.fixture
    def standard_bridge_segments(self) -> list[MockBridgeSegment]:
        """Create bridge with standard cross-section."""
        # bz1=0.5m (top), bz2=3.0m (middle), bz3=0.5m (bottom)
        # Zone boundaries:
        # Zone 1 (bz1): y > 1.5 (from bz2/2=1.5 to bz2/2+bz1=2.0)
        # Zone 2 (bz2): -1.5 < y <= 1.5
        # Zone 3 (bz3): -2.0 <= y <= -1.5
        return [
            MockBridgeSegment(length=0.0, bz1=0.5, bz2=3.0, bz3=0.5),
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),
        ]

    def test_zone_1_top(self, standard_bridge_segments: list[MockBridgeSegment]) -> None:
        """Test mapping to zone 1 (top/bz1)."""
        # Zone 1 is above bz2/2
        # With bz2=3.0, zone 1 is y > 1.5
        test_cases = [
            1.6,  # Just above boundary
            1.75,  # Middle of zone 1
            2.0,  # At top
        ]

        for y in test_cases:
            zone = _map_cs_section_to_zone("CS1", (5.0, y, 0.0), standard_bridge_segments)
            zone_type = int(zone.split("-")[0])
            assert zone_type == 1, f"Failed for y={y}, got zone {zone}"

    def test_zone_2_middle(self, standard_bridge_segments: list[MockBridgeSegment]) -> None:
        """Test mapping to zone 2 (middle/bz2)."""
        # Zone 2 is from -bz2/2 to +bz2/2
        # With bz2=3.0, zone 2 is -1.5 < y <= 1.5
        test_cases = [
            -1.4,  # Near bottom boundary
            0.0,  # Center
            1.5,  # At top boundary
        ]

        for y in test_cases:
            zone = _map_cs_section_to_zone("CS2", (5.0, y, 0.0), standard_bridge_segments)
            zone_type = int(zone.split("-")[0])
            assert zone_type == 2, f"Failed for y={y}, got zone {zone}"

    def test_zone_3_bottom(self, standard_bridge_segments: list[MockBridgeSegment]) -> None:
        """Test mapping to zone 3 (bottom/bz3)."""
        # Zone 3 is from -(bz2/2 + bz3) to -bz2/2
        # With bz2=3.0, bz3=0.5, zone 3 is -2.0 <= y <= -1.5
        test_cases = [
            -2.0,  # At bottom
            -1.75,  # Middle of zone 3
            -1.5,  # At top boundary (inclusive)
        ]

        for y in test_cases:
            zone = _map_cs_section_to_zone("CS3", (5.0, y, 0.0), standard_bridge_segments)
            zone_type = int(zone.split("-")[0])
            assert zone_type == 3, f"Failed for y={y}, got zone {zone}"

    def test_outside_bridge_geometry(self, standard_bridge_segments: list[MockBridgeSegment]) -> None:
        """Test that positions outside bridge geometry return unknown-zone."""
        test_cases = [
            3.0,  # Above zone 1
            -3.0,  # Below zone 3
        ]

        for y in test_cases:
            zone = _map_cs_section_to_zone("CS_out", (5.0, y, 0.0), standard_bridge_segments)
            assert zone == "unknown-zone", f"Should return unknown-zone for y={y}"


class TestZoneIdentifierFormat:
    """Tests for zone identifier formatting."""

    @pytest.fixture
    def multi_segment_bridge(self) -> list[MockBridgeSegment]:
        """Create bridge with multiple segments."""
        return [
            MockBridgeSegment(length=0.0, bz1=0.5, bz2=3.0, bz3=0.5),
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Segment 1
            MockBridgeSegment(length=15.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Segment 2
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Segment 3
        ]

    def test_zone_identifier_format(self, multi_segment_bridge: list[MockBridgeSegment]) -> None:
        """Test that zone identifier has correct format: type-segment."""
        # Zone 1 (top) of segment 1
        zone = _map_cs_section_to_zone("CS1", (5.0, 1.6, 0.0), multi_segment_bridge)
        assert zone == "1-1", f"Expected '1-1', got '{zone}'"

        # Zone 2 (middle) of segment 2
        zone = _map_cs_section_to_zone("CS2", (15.0, 0.0, 0.0), multi_segment_bridge)
        assert zone == "2-2", f"Expected '2-2', got '{zone}'"

        # Zone 3 (bottom) of segment 3
        zone = _map_cs_section_to_zone("CS3", (30.0, -1.6, 0.0), multi_segment_bridge)
        assert zone == "3-3", f"Expected '3-3', got '{zone}'"

    def test_all_zones_in_segment(self, multi_segment_bridge: list[MockBridgeSegment]) -> None:
        """Test mapping to all three zones in a single segment."""
        x = 5.0  # Segment 1
        expected_zones = {
            1.6: "1-1",  # Zone 1
            0.0: "2-1",  # Zone 2
            -1.6: "3-1",  # Zone 3
        }

        for y, expected_zone in expected_zones.items():
            zone = _map_cs_section_to_zone("CS", (x, y, 0.0), multi_segment_bridge)
            assert zone == expected_zone, f"For y={y}, expected {expected_zone}, got {zone}"


class TestVaryingBridgeGeometry:
    """Tests for bridges with varying cross-sections."""

    def test_varying_segment_lengths(self) -> None:
        """Test bridge with different segment lengths."""
        bridge_segments = [
            MockBridgeSegment(length=0.0, bz1=0.5, bz2=3.0, bz3=0.5),
            MockBridgeSegment(length=5.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Short segment
            MockBridgeSegment(length=20.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Long segment
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),  # Medium segment
        ]

        test_cases = [
            (2.5, 1),  # In segment 1 (0-5)
            (15.0, 2),  # In segment 2 (5-25)
            (30.0, 3),  # In segment 3 (25-35)
        ]

        for x, expected_segment in test_cases:
            zone = _map_cs_section_to_zone("CS", (x, 0.0, 0.0), bridge_segments)
            segment_number = int(zone.split("-")[1])
            assert segment_number == expected_segment

    def test_varying_zone_widths(self) -> None:
        """Test bridge with different zone widths per segment."""
        # Segment 1: narrow zones
        # Segment 2: wide zones
        bridge_segments = [
            MockBridgeSegment(length=0.0, bz1=0.3, bz2=2.0, bz3=0.3),
            MockBridgeSegment(length=10.0, bz1=0.3, bz2=2.0, bz3=0.3),  # Narrow
            MockBridgeSegment(length=10.0, bz1=0.8, bz2=4.0, bz3=0.8),  # Wide
        ]

        # Test zone 1 in narrow segment (bz2/2 = 1.0, zone 1 at y > 1.0)
        zone = _map_cs_section_to_zone("CS1", (5.0, 1.1, 0.0), bridge_segments)
        assert zone == "1-1"

        # Test zone 1 in wide segment (bz2/2 = 2.0, zone 1 at y > 2.0)
        zone = _map_cs_section_to_zone("CS2", (15.0, 2.1, 0.0), bridge_segments)
        assert zone == "1-2"

    def test_asymmetric_zones(self) -> None:
        """Test bridge with different top and bottom zone widths."""
        bridge_segments = [
            MockBridgeSegment(length=0.0, bz1=0.8, bz2=3.0, bz3=0.3),  # bz1 > bz3
            MockBridgeSegment(length=10.0, bz1=0.8, bz2=3.0, bz3=0.3),
        ]

        # Zone 1 boundary: bz2/2 = 1.5, should be at y > 1.5
        zone_1 = _map_cs_section_to_zone("CS1", (5.0, 1.6, 0.0), bridge_segments)
        assert zone_1 == "1-1"

        # Zone 3 boundary: -(bz2/2 + bz3) = -1.8, should be at -1.8 <= y <= -1.5
        zone_3 = _map_cs_section_to_zone("CS3", (5.0, -1.6, 0.0), bridge_segments)
        assert zone_3 == "3-1"


class TestBoundaryConditions:
    """Tests for boundary conditions and edge cases."""

    @pytest.fixture
    def boundary_test_bridge(self) -> list[MockBridgeSegment]:
        """Create bridge for boundary testing."""
        return [
            MockBridgeSegment(length=0.0, bz1=0.5, bz2=3.0, bz3=0.5),
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),
        ]

    def test_segment_boundary_handling(self, boundary_test_bridge: list[MockBridgeSegment]) -> None:
        """Test CS sections exactly at segment boundaries."""
        # At x=10.0, should belong to segment 1 (cumulative <= 10.0)
        zone_at_10 = _map_cs_section_to_zone("CS1", (10.0, 0.0, 0.0), boundary_test_bridge)
        segment_at_10 = int(zone_at_10.split("-")[1])

        # At x=10.001, should belong to segment 2
        zone_after_10 = _map_cs_section_to_zone("CS2", (10.001, 0.0, 0.0), boundary_test_bridge)
        segment_after_10 = int(zone_after_10.split("-")[1])

        assert segment_at_10 == 1
        assert segment_after_10 == 2

    def test_zone_boundary_handling(self, boundary_test_bridge: list[MockBridgeSegment]) -> None:
        """Test CS sections exactly at zone boundaries."""
        # At y=1.5 (boundary between zone 2 and zone 1)
        # Based on code: y > bz2/2 for zone 1, so y=1.5 should be zone 2
        zone_at_boundary = _map_cs_section_to_zone("CS", (5.0, 1.5, 0.0), boundary_test_bridge)
        zone_type = int(zone_at_boundary.split("-")[0])
        assert zone_type == 2, "Boundary value should belong to zone 2"

        # Just above boundary should be zone 1
        zone_above = _map_cs_section_to_zone("CS", (5.0, 1.501, 0.0), boundary_test_bridge)
        zone_type_above = int(zone_above.split("-")[0])
        assert zone_type_above == 1

    def test_zero_position(self, boundary_test_bridge: list[MockBridgeSegment]) -> None:
        """Test CS section at origin (0, 0, 0)."""
        # Should map to segment 1, zone 2
        zone = _map_cs_section_to_zone("CS_origin", (0.001, 0.0, 0.0), boundary_test_bridge)
        assert zone == "2-1"


class TestErrorHandling:
    """Tests for error handling and invalid inputs."""

    def test_empty_bridge_segments(self) -> None:
        """Test that empty bridge segments raises ValueError."""
        with pytest.raises(ValueError, match="Bridge segments data is required"):
            _map_cs_section_to_zone("CS1", (5.0, 0.0, 0.0), [])

    def test_none_bridge_segments(self) -> None:
        """Test that None bridge segments raises ValueError."""
        with pytest.raises(ValueError, match="Bridge segments data is required"):
            _map_cs_section_to_zone("CS1", (5.0, 0.0, 0.0), None)  # type: ignore[arg-type]

    def test_string_coordinates(self) -> None:
        """Test that string coordinates are converted to float."""
        bridge_segments = [
            MockBridgeSegment(length=0.0, bz1=0.5, bz2=3.0, bz3=0.5),
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),
        ]

        # Pass coordinates as strings (can happen from DataFrame)
        zone = _map_cs_section_to_zone("CS1", ("5.0", "0.0", "0.0"), bridge_segments)  # type: ignore[arg-type]
        assert zone == "2-1"

    def test_negative_x_coordinate(self) -> None:
        """Test handling of negative X coordinate."""
        bridge_segments = [
            MockBridgeSegment(length=0.0, bz1=0.5, bz2=3.0, bz3=0.5),
            MockBridgeSegment(length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),
        ]

        # Negative X should map to first segment
        zone = _map_cs_section_to_zone("CS_neg", (-1.0, 0.0, 0.0), bridge_segments)
        segment_number = int(zone.split("-")[1])
        assert segment_number == 1


class TestPydanticModelSupport:
    """Tests for supporting both VIKTOR Munch and Pydantic models."""

    def test_pydantic_segment_length(self) -> None:
        """Test segment with segment_length attribute (Pydantic)."""

        class PydanticSegment:
            def __init__(self, segment_length: float, bz1: float, bz2: float, bz3: float) -> None:
                self.segment_length = segment_length
                self.bz1 = bz1
                self.bz2 = bz2
                self.bz3 = bz3

        bridge_segments = [
            PydanticSegment(segment_length=0.0, bz1=0.5, bz2=3.0, bz3=0.5),
            PydanticSegment(segment_length=10.0, bz1=0.5, bz2=3.0, bz3=0.5),
        ]

        zone = _map_cs_section_to_zone("CS1", (5.0, 0.0, 0.0), bridge_segments)  # type: ignore[arg-type]
        assert zone == "2-1"

    def test_viktor_munch_length(self) -> None:
        """Test segment with l attribute (VIKTOR Munch)."""

        class MunchSegment:
            def __init__(self, l: float, bz1: float, bz2: float, bz3: float) -> None:  # noqa: E741
                self.l = l
                self.bz1 = bz1
                self.bz2 = bz2
                self.bz3 = bz3

        bridge_segments = [
            MunchSegment(l=0.0, bz1=0.5, bz2=3.0, bz3=0.5),
            MunchSegment(l=10.0, bz1=0.5, bz2=3.0, bz3=0.5),
        ]

        zone = _map_cs_section_to_zone("CS1", (5.0, 0.0, 0.0), bridge_segments)  # type: ignore[arg-type]
        assert zone == "2-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
