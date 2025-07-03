"""
Test module for load zone geometry calculations.

This module contains tests for calculating load zone geometry properties such as
bottom coordinates and related geometric operations.
"""

import math
import unittest

import pytest

from src.geometry.load_zone_geometry import (
    LoadZoneDataRow,  # Import for type hinting if needed in test setup
    calculate_zone_bottom_y_coords,
)


class TestCalculateZoneBottomYCoords(unittest.TestCase):
    """Test cases for calculating zone bottom Y coordinates."""

    def test_last_zone_returns_bridge_bottom_coords(self) -> None:
        """Test that the last zone returns bridge bottom coordinates."""
        # Arrange
        zone_idx = 1
        num_load_zones = 2  # Current zone is the last one
        num_defined_d_points = 3
        y_coords_top = [10.0, 10.0, 10.0]  # Not used for last zone logic itself
        y_bridge_bottom = [0.0, -0.5, 0.0]
        zone_params: LoadZoneDataRow = {}  # Not used for last zone logic

        # Act
        result = calculate_zone_bottom_y_coords(zone_idx, num_load_zones, num_defined_d_points, y_coords_top, y_bridge_bottom, zone_params)

        # Assert
        assert result == y_bridge_bottom
        assert result is not y_bridge_bottom  # Ensure it's a copy

    def test_non_last_zone_basic_calculation(self) -> None:
        """Test basic calculation for non-last zone bottom Y coordinates."""
        # Arrange
        zone_idx = 0
        num_load_zones = 2  # Current zone is NOT the last one
        num_defined_d_points = 3
        y_coords_top = [10.0, 9.5, 9.0]
        y_bridge_bottom = [0.0, 0.0, 0.0]  # Not used directly
        zone_params: LoadZoneDataRow = {
            "d1_width": 1.0,
            "d2_width": 1.5,
            "d3_width": 2.0,
        }
        expected_y_bottom = [
            10.0 - 1.0,  # 9.0
            9.5 - 1.5,  # 8.0
            9.0 - 2.0,  # 7.0
        ]

        # Act
        result = calculate_zone_bottom_y_coords(zone_idx, num_load_zones, num_defined_d_points, y_coords_top, y_bridge_bottom, zone_params)

        # Assert
        assert len(result) == num_defined_d_points
        for i in range(num_defined_d_points):
            assert math.isclose(result[i], expected_y_bottom[i])

    def test_non_last_zone_missing_d_width_defaults_to_zero(self) -> None:
        """Test that missing d_width values default to zero for non-last zones."""
        # Arrange
        zone_idx = 0
        num_load_zones = 2
        num_defined_d_points = 3
        y_coords_top = [10.0, 9.5, 9.0]
        y_bridge_bottom = [0.0, 0.0, 0.0]
        zone_params: LoadZoneDataRow = {
            "d1_width": 1.0,
            # d2_width is missing
            "d3_width": 2.0,
        }
        expected_y_bottom = [
            10.0 - 1.0,  # 9.0
            9.5 - 0.0,  # 9.5 (d2_width defaults to 0)
            9.0 - 2.0,  # 7.0
        ]

        # Act
        result = calculate_zone_bottom_y_coords(zone_idx, num_load_zones, num_defined_d_points, y_coords_top, y_bridge_bottom, zone_params)
        # Assert
        assert len(result) == num_defined_d_points
        for i in range(num_defined_d_points):
            assert math.isclose(result[i], expected_y_bottom[i])

    def test_non_last_zone_invalid_d_width_type_defaults_to_zero(self) -> None:
        """Test that invalid d_width types default to zero for non-last zones."""
        # Arrange
        zone_idx = 0
        num_load_zones = 2
        num_defined_d_points = 2
        y_coords_top = [5.0, 5.0]
        y_bridge_bottom = [0.0, 0.0]
        zone_params: LoadZoneDataRow = {
            "d1_width": 1.0,
        }
        # Intentionally add invalid type for testing error handling
        zone_params["d2_width"] = "should_be_float"  # type: ignore[typeddict-item]
        expected_y_bottom = [
            5.0 - 1.0,  # 4.0
            5.0 - 0.0,  # 5.0 (d2_width defaults to 0 due to invalid type)
        ]
        # Act
        result = calculate_zone_bottom_y_coords(zone_idx, num_load_zones, num_defined_d_points, y_coords_top, y_bridge_bottom, zone_params)
        # Assert
        assert len(result) == num_defined_d_points
        assert math.isclose(result[0], expected_y_bottom[0])
        assert math.isclose(result[1], expected_y_bottom[1])

    def test_non_last_zone_zero_d_points(self) -> None:
        """Test non-last zone calculation when there are zero d_points."""
        # Arrange
        zone_idx = 0
        num_load_zones = 2
        num_defined_d_points = 0  # No D-points
        y_coords_top: list[float] = []
        y_bridge_bottom: list[float] = []
        zone_params: LoadZoneDataRow = {}
        expected_y_bottom: list[float] = []

        # Act
        result = calculate_zone_bottom_y_coords(zone_idx, num_load_zones, num_defined_d_points, y_coords_top, y_bridge_bottom, zone_params)
        # Assert
        assert result == expected_y_bottom

    def test_non_last_zone_more_d_points_than_widths_in_params(self) -> None:
        """Test non-last zone when there are more d_points than width parameters."""
        # Arrange
        zone_idx = 0
        num_load_zones = 2
        num_defined_d_points = 3  # d1, d2, d3 expected
        y_coords_top = [10.0, 9.0, 8.0]
        y_bridge_bottom = [0.0, 0.0, 0.0]
        zone_params: LoadZoneDataRow = {  # Only d1_width provided
            "d1_width": 2.0,
        }
        expected_y_bottom = [
            10.0 - 2.0,  # 8.0
            9.0 - 0.0,  # 9.0 (d2_width defaults to 0)
            8.0 - 0.0,  # 8.0 (d3_width defaults to 0)
        ]
        # Act
        result = calculate_zone_bottom_y_coords(zone_idx, num_load_zones, num_defined_d_points, y_coords_top, y_bridge_bottom, zone_params)
        # Assert
        assert len(result) == num_defined_d_points
        for i in range(num_defined_d_points):
            assert math.isclose(result[i], expected_y_bottom[i])


class TestTheoreticalTrafficLanes:
    """Test theoretical traffic lane calculation based on bridge width."""

    def test_calculate_theoretical_traffic_lanes_exact_division(self) -> None:
        """Test theoretical lanes when bridge width divides evenly by 3."""
        from src.geometry.load_zone_geometry import calculate_theoretical_traffic_lanes

        # 30m bridge ÷ 3 = 10 lanes, 0m rest
        bridge_width = 30.0
        result = calculate_theoretical_traffic_lanes(bridge_width)

        assert result["num_lanes"] == 10
        assert result["lane_width"] == 3.0
        assert result["rest_width"] == 0.0
        assert result["total_lanes_width"] == 30.0

    def test_calculate_theoretical_traffic_lanes_with_remainder(self) -> None:
        """Test theoretical lanes when bridge width has remainder."""
        from src.geometry.load_zone_geometry import calculate_theoretical_traffic_lanes

        # 10m bridge ÷ 3 = 3 lanes (3m each) + 1m rest
        bridge_width = 10.0
        result = calculate_theoretical_traffic_lanes(bridge_width)

        assert result["num_lanes"] == 3
        assert result["lane_width"] == 3.0
        assert result["rest_width"] == 1.0
        assert result["total_lanes_width"] == 9.0

    def test_calculate_theoretical_traffic_lanes_edge_cases(self) -> None:
        """Test theoretical lanes with edge cases."""
        from src.geometry.load_zone_geometry import calculate_theoretical_traffic_lanes

        # Very narrow bridge: 2.5m ÷ 3 = 0 lanes, 2.5m rest
        result_narrow = calculate_theoretical_traffic_lanes(2.5)
        assert result_narrow["num_lanes"] == 0
        assert result_narrow["lane_width"] == 3.0
        assert result_narrow["rest_width"] == 2.5
        assert result_narrow["total_lanes_width"] == 0.0

        # Exactly 3m bridge: 3m ÷ 3 = 1 lane, 0m rest
        result_exact = calculate_theoretical_traffic_lanes(3.0)
        assert result_exact["num_lanes"] == 1
        assert result_exact["lane_width"] == 3.0
        assert result_exact["rest_width"] == 0.0
        assert result_exact["total_lanes_width"] == 3.0

    def test_calculate_theoretical_traffic_lanes_custom_lane_width(self) -> None:
        """Test theoretical lanes with custom lane width."""
        from src.geometry.load_zone_geometry import calculate_theoretical_traffic_lanes

        # 15m bridge with 3.5m lane width: 15 ÷ 3.5 = 4 lanes + 1m rest
        bridge_width = 15.0
        lane_width = 3.5
        result = calculate_theoretical_traffic_lanes(bridge_width, lane_width)

        assert result["num_lanes"] == 4
        assert result["lane_width"] == 3.5
        assert result["rest_width"] == 1.0  # 15 - (4 * 3.5) = 1.0
        assert result["total_lanes_width"] == 14.0

    def test_calculate_theoretical_traffic_lanes_zero_width(self) -> None:
        """Test error handling for invalid bridge width."""
        from src.geometry.load_zone_geometry import calculate_theoretical_traffic_lanes

        with pytest.raises(ValueError, match="Bridge width must be positive"):
            calculate_theoretical_traffic_lanes(0.0)

        with pytest.raises(ValueError, match="Bridge width must be positive"):
            calculate_theoretical_traffic_lanes(-5.0)

    def test_calculate_theoretical_traffic_lanes_invalid_lane_width(self) -> None:
        """Test error handling for invalid lane width."""
        from src.geometry.load_zone_geometry import calculate_theoretical_traffic_lanes

        with pytest.raises(ValueError, match="Lane width must be positive"):
            calculate_theoretical_traffic_lanes(10.0, 0.0)

        with pytest.raises(ValueError, match="Lane width must be positive"):
            calculate_theoretical_traffic_lanes(10.0, -2.0)


class TestGenerateTheoreticalLoadZones:
    """Test generation of theoretical load zone data structures."""

    def test_generate_theoretical_load_zones_with_lanes_only(self) -> None:
        """Test generating zones when bridge width divides evenly (no rest zone)."""
        from src.geometry.load_zone_geometry import generate_theoretical_load_zones

        # 30m bridge = 10 lanes, no rest
        bridge_width = 30.0
        num_d_points = 3

        result = generate_theoretical_load_zones(bridge_width, num_d_points)

        assert len(result) == 10  # Only lane zones

        # Check first lane zone
        assert result[0]["zone_type"] == "Auto"
        assert result[0]["d1_width"] == 3.0
        assert result[0]["d2_width"] == 3.0
        assert result[0]["d3_width"] == 3.0

        # Check last lane zone
        assert result[9]["zone_type"] == "Auto"
        assert result[9]["d1_width"] == 3.0

    def test_generate_theoretical_load_zones_with_rest(self) -> None:
        """Test generating zones when bridge has remainder (includes rest zone)."""
        from src.geometry.load_zone_geometry import generate_theoretical_load_zones

        # 10m bridge = 3 lanes + 1m rest
        bridge_width = 10.0
        num_d_points = 2

        result = generate_theoretical_load_zones(bridge_width, num_d_points)

        assert len(result) == 4  # 3 lane zones + 1 rest zone

        # Check lane zones
        for i in range(3):
            assert result[i]["zone_type"] == "Auto"
            assert result[i]["d1_width"] == 3.0
            assert result[i]["d2_width"] == 3.0

        # Check rest zone (last zone)
        assert result[3]["zone_type"] == "Berm"
        assert result[3]["d1_width"] == 1.0
        assert result[3]["d2_width"] == 1.0

    def test_generate_theoretical_load_zones_variable_d_points(self) -> None:
        """Test generating zones with different numbers of D-points."""
        from src.geometry.load_zone_geometry import generate_theoretical_load_zones

        # Test with 5 D-points
        bridge_width = 12.0  # 4 lanes + 0m rest
        num_d_points = 5

        result = generate_theoretical_load_zones(bridge_width, num_d_points)

        assert len(result) == 4  # 4 lanes, no rest

        # Check that all D-point widths are set correctly
        for zone in result:
            # Check all 5 D-points explicitly for TypedDict compatibility
            assert zone["d1_width"] == 3.0
            assert zone["d2_width"] == 3.0
            assert zone["d3_width"] == 3.0
            assert zone["d4_width"] == 3.0
            assert zone["d5_width"] == 3.0

    def test_generate_theoretical_load_zones_narrow_bridge(self) -> None:
        """Test generating zones for very narrow bridge (no lanes possible)."""
        from src.geometry.load_zone_geometry import generate_theoretical_load_zones

        # 2m bridge = 0 lanes, 2m rest
        bridge_width = 2.0
        num_d_points = 2

        result = generate_theoretical_load_zones(bridge_width, num_d_points)

        assert len(result) == 1  # Only rest zone
        assert result[0]["zone_type"] == "Berm"
        assert result[0]["d1_width"] == 2.0
        assert result[0]["d2_width"] == 2.0

    def test_generate_theoretical_load_zones_pavement_properties(self) -> None:
        """Test that theoretical zones have correct pavement properties."""
        from src.geometry.load_zone_geometry import generate_theoretical_load_zones

        bridge_width = 15.0  # 5 lanes + 0m rest
        num_d_points = 2

        result = generate_theoretical_load_zones(bridge_width, num_d_points)

        # Check pavement properties for lane zones
        for zone in result:
            if zone["zone_type"] == "Auto":
                assert zone["pavement_thickness"] == 0.1  # Default for Auto
                assert zone["pavement_material"] == "Asfalt"
            elif zone["zone_type"] == "Berm":
                assert zone["pavement_thickness"] == 0.05  # Default for Berm
                assert zone["pavement_material"] == "Gravel"

    def test_generate_theoretical_load_zones_custom_lane_width(self) -> None:
        """Test generating zones with custom lane width."""
        from src.geometry.load_zone_geometry import generate_theoretical_load_zones

        # 14m bridge with 3.5m lanes = 4 lanes + 0m rest
        bridge_width = 14.0
        num_d_points = 2
        lane_width = 3.5

        result = generate_theoretical_load_zones(bridge_width, num_d_points, lane_width)

        assert len(result) == 4  # 4 lanes, no rest

        # Check lane widths
        for zone in result:
            assert zone["d1_width"] == 3.5
            assert zone["d2_width"] == 3.5

    def test_generate_theoretical_load_zones_error_handling(self) -> None:
        """Test error handling for invalid inputs."""
        from src.geometry.load_zone_geometry import generate_theoretical_load_zones

        # Invalid bridge width
        with pytest.raises(ValueError):
            generate_theoretical_load_zones(0.0, 3)

        # Invalid number of D-points
        with pytest.raises(ValueError, match="Number of D-points must be positive"):
            generate_theoretical_load_zones(10.0, 0)

        with pytest.raises(ValueError, match="Number of D-points must be positive"):
            generate_theoretical_load_zones(10.0, -1)


if __name__ == "__main__":
    pytest.main([__file__])
