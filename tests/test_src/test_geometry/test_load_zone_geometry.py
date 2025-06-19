"""
Test module for load zone geometry calculations.

This module contains tests for calculating load zone geometry properties such as
bottom coordinates and related geometric operations.
"""

import math
import unittest

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


if __name__ == "__main__":
    unittest.main()
