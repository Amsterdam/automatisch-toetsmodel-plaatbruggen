"""Tests for CS section zone mapping functionality."""

from src.data_models.bridge_models import BridgeSegmentDimensions
from src.integrations.scia_integration.results.scia_results_processor import _map_cs_section_to_zone


class TestCSZoneMapping:
    """Test zone mapping for CS sections based on coordinates."""

    def test_zone_mapping_zone_1_segment_1(self) -> None:
        """Test mapping to zone 1 (top) of segment 1."""
        # Create simple bridge with 2 segments
        bridge_segments = [
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=0.0),  # D1
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=10.0),  # D2, 10m from D1
        ]

        # Coordinates in zone 1 (top outer zone, bz1)
        # Zone 1 Y-range: from (bz2/2 + bz1) = 4.0 to (bz2/2) = 2.0
        # So y=3.0 should be in zone 1
        coords = (5.0, 3.0, 0.0)  # x=5m (within segment 1), y=3.0 (in zone 1), z=0

        result = _map_cs_section_to_zone("ULS", coords, bridge_segments)

        assert result == "1-1", f"Expected zone '1-1', got '{result}'"

    def test_zone_mapping_zone_2_segment_1(self) -> None:
        """Test mapping to zone 2 (middle) of segment 1."""
        bridge_segments = [
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=0.0),
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=10.0),
        ]

        # Coordinates in zone 2 (middle zone, bz2)
        # Zone 2 Y-range: from (bz2/2) = 2.0 to (-bz2/2) = -2.0
        # So y=0.0 should be in zone 2
        coords = (5.0, 0.0, 0.0)

        result = _map_cs_section_to_zone("ULS", coords, bridge_segments)

        assert result == "2-1", f"Expected zone '2-1', got '{result}'"

    def test_zone_mapping_zone_3_segment_1(self) -> None:
        """Test mapping to zone 3 (bottom) of segment 1."""
        bridge_segments = [
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=0.0),
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=10.0),
        ]

        # Coordinates in zone 3 (bottom outer zone, bz3)
        # Zone 3 Y-range: from (-bz2/2) = -2.0 to (-bz2/2 - bz3) = -4.0
        # So y=-3.0 should be in zone 3
        coords = (5.0, -3.0, 0.0)

        result = _map_cs_section_to_zone("ULS", coords, bridge_segments)

        assert result == "3-1", f"Expected zone '3-1', got '{result}'"

    def test_zone_mapping_segment_2(self) -> None:
        """Test mapping to different segment based on x-coordinate."""
        bridge_segments = [
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=0.0),  # D1
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=10.0),  # D2, 10m from D1
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=10.0),  # D3, 20m from D1
        ]

        # x=15m should be in segment 2 (between D2 at 10m and D3 at 20m)
        coords = (15.0, 3.0, 0.0)

        result = _map_cs_section_to_zone("ULS", coords, bridge_segments)

        assert result == "1-2", f"Expected zone '1-2', got '{result}'"

    def test_zone_mapping_outside_bridge(self) -> None:
        """Test coordinates outside bridge geometry."""
        bridge_segments = [
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=0.0),
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=10.0),
        ]

        # y=-5.0 is outside bridge (below zone 3 which ends at -4.0)
        coords = (5.0, -5.0, 0.0)

        result = _map_cs_section_to_zone("ULS", coords, bridge_segments)

        assert result == "unknown-zone", f"Expected 'unknown-zone', got '{result}'"

    def test_zone_mapping_variable_width_bridge(self) -> None:
        """Test with variable width bridge (different bz values per segment)."""
        bridge_segments = [
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=0.0),  # D1
            BridgeSegmentDimensions(bz1=3.0, bz2=6.0, bz3=3.0, segment_length=10.0),  # D2, wider bridge, 10m from D1
        ]

        # With 2 D-points, we have 1 segment (segment 1)
        # In segment 1, the geometry at any x-position is the geometry of the segment
        # Since segment 1 uses the geometry from index 1 (D2), zone 1 Y-range: from (6/2 + 3) = 6.0 to (6/2) = 3.0
        # So y=4.0 should be in zone 1 of segment 1
        coords = (5.0, 4.0, 0.0)  # x=5m is within segment 1

        result = _map_cs_section_to_zone("ULS", coords, bridge_segments)

        assert result == "1-1", f"Expected zone '1-1', got '{result}'"

    def test_zone_mapping_boundary_conditions(self) -> None:
        """Test boundary conditions between zones."""
        bridge_segments = [
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=0.0),
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=10.0),
        ]

        # Test exactly at zone boundary (bz2/2 = 2.0)
        # This should be in zone 2 (middle), as zone 1 is y >= 2.0 and zone 2 is y >= -2.0
        coords = (5.0, 2.0, 0.0)

        result = _map_cs_section_to_zone("ULS", coords, bridge_segments)

        assert result == "2-1", f"Expected zone '2-1' at boundary, got '{result}'"

    def test_zone_mapping_raises_error_no_segments(self) -> None:
        """Test that function raises error when no segments provided."""
        import pytest

        with pytest.raises(ValueError, match="Bridge segments data is required"):
            _map_cs_section_to_zone("ULS", (5.0, 0.0, 0.0), [])

    def test_zone_mapping_first_segment_x_zero(self) -> None:
        """Test mapping at x=0 (start of bridge)."""
        bridge_segments = [
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=0.0),
            BridgeSegmentDimensions(bz1=2.0, bz2=4.0, bz3=2.0, segment_length=10.0),
        ]

        # x=0 should be in segment 1
        coords = (0.0, 3.0, 0.0)

        result = _map_cs_section_to_zone("ULS", coords, bridge_segments)

        assert result == "1-1", f"Expected zone '1-1' at x=0, got '{result}'"
