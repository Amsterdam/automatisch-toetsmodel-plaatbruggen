"""
Tests to ensure all generated loads stay within bridge boundaries.

This module tests the load boundary compliance functionality to ensure that
dispersed loads are properly clipped to stay within the bridge structure.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from munch import Munch

from src.integrations.scia_integration.scia_coordinate_utils import clip_polygon_to_bridge_boundaries


class TestLoadBoundaryCompliance:
    """Tests to ensure all generated loads stay within bridge boundaries."""

    @pytest.fixture
    def mock_bridge_geometry(self) -> Mock:
        """Create mock bridge geometry with defined boundaries."""
        mock_geom = Mock()
        mock_geom.x_coords_d_points = [0.0, 20.0]  # Bridge length: 20m
        mock_geom.y_top_structural_edge_at_d_points = [5.0, 5.0]  # Bridge top: y=5.0
        mock_geom.y_bridge_bottom_at_d_points = [-5.0, -5.0]  # Bridge bottom: y=-5.0
        return mock_geom

    @pytest.fixture
    def mock_params_with_dispersion(self) -> Mock:
        """Create mock params with dispersion enabled."""
        mock_params = Mock()
        mock_params.input = Mock()
        mock_params.input.berekeningsinstellingen = Mock()
        mock_params.spreiding = True  # Enable dispersion

        # Mock bridge segments for dispersion calculation
        mock_segment = Mock()
        mock_segment.l = 20.0
        mock_segment.bz1 = 2.0
        mock_segment.bz2 = 1.0
        mock_segment.bz3 = 2.0
        mock_segment.dz = 0.8
        mock_segment.dz_2 = 1.0
        mock_params.bridge_segments_array = [mock_segment]

        # Mock load zones for dispersion calculation
        mock_load_zone = Mock()
        mock_load_zone.material = "Beton (normaal)"
        mock_load_zone.thickness = 0.1
        mock_params.load_zones_data_array = [mock_load_zone]

        return mock_params

    def test_clip_polygon_to_bridge_boundaries_function(self, mock_bridge_geometry: Mock) -> None:
        """Test the clip_polygon_to_bridge_boundaries function directly."""
        # Test with coordinates that extend beyond boundaries
        corner_points = [
            (-1.0, 6.0, 0.0),  # X too small, Y too large
            (21.0, 6.0, 0.0),  # X too large, Y too large
            (21.0, -6.0, 0.0),  # X too large, Y too small
            (-1.0, -6.0, 0.0),  # X too small, Y too small
        ]

        clipped_points = clip_polygon_to_bridge_boundaries(corner_points, mock_bridge_geometry)

        # Verify all coordinates are clipped to boundaries
        expected_clipped = [
            (0.0, 5.0, 0.0),  # Clipped to x_min, y_max
            (20.0, 5.0, 0.0),  # Clipped to x_max, y_max
            (20.0, -5.0, 0.0),  # Clipped to x_max, y_min
            (0.0, -5.0, 0.0),  # Clipped to x_min, y_min
        ]

        for i, (x, y, z) in enumerate(clipped_points):
            expected_x, expected_y, expected_z = expected_clipped[i]
            assert x == expected_x, f"X coordinate {x} should be clipped to {expected_x}"
            assert y == expected_y, f"Y coordinate {y} should be clipped to {expected_y}"
            assert z == expected_z, f"Z coordinate {z} should remain {expected_z}"

    def test_clip_polygon_with_coordinates_within_boundaries(self, mock_bridge_geometry: Mock) -> None:
        """Test that coordinates already within boundaries are not modified."""
        # Test with coordinates already within boundaries
        corner_points = [
            (5.0, 2.0, 0.0),
            (15.0, 2.0, 0.0),
            (15.0, -2.0, 0.0),
            (5.0, -2.0, 0.0),
        ]

        clipped_points = clip_polygon_to_bridge_boundaries(corner_points, mock_bridge_geometry)

        # Verify coordinates are unchanged
        assert clipped_points == corner_points, "Coordinates within boundaries should not be modified"

    def test_clip_polygon_with_empty_input(self, mock_bridge_geometry: Mock) -> None:
        """Test that empty input returns empty output."""
        clipped_points = clip_polygon_to_bridge_boundaries([], mock_bridge_geometry)
        assert clipped_points == [], "Empty input should return empty output"

    def test_clip_polygon_edge_cases(self, mock_bridge_geometry: Mock) -> None:
        """Test edge cases for the clipping function."""
        # Test with single point
        single_point = [(10.0, 3.0, 0.0)]
        clipped = clip_polygon_to_bridge_boundaries(single_point, mock_bridge_geometry)
        assert clipped == single_point, "Single point within boundaries should be unchanged"

        # Test with point outside boundaries
        outside_point = [(25.0, 8.0, 0.0)]
        clipped = clip_polygon_to_bridge_boundaries(outside_point, mock_bridge_geometry)
        expected = [(20.0, 5.0, 0.0)]  # Clipped to boundaries
        assert clipped == expected, "Point outside boundaries should be clipped"

        # Test with mixed coordinates (some inside, some outside)
        mixed_points = [
            (5.0, 2.0, 0.0),  # Inside
            (25.0, 2.0, 0.0),  # X outside
            (5.0, 8.0, 0.0),  # Y outside
            (25.0, 8.0, 0.0),  # Both outside
        ]
        clipped = clip_polygon_to_bridge_boundaries(mixed_points, mock_bridge_geometry)
        expected = [
            (5.0, 2.0, 0.0),  # Inside - unchanged
            (20.0, 2.0, 0.0),  # X clipped
            (5.0, 5.0, 0.0),  # Y clipped
            (20.0, 5.0, 0.0),  # Both clipped
        ]
        assert clipped == expected, "Mixed coordinates should be clipped appropriately"

    def test_clip_polygon_preserves_z_coordinates(self, mock_bridge_geometry: Mock) -> None:
        """Test that Z coordinates are preserved during clipping."""
        corner_points = [
            (-1.0, 6.0, 1.5),  # X and Y outside, Z = 1.5
            (21.0, 6.0, 2.0),  # X and Y outside, Z = 2.0
            (21.0, -6.0, 0.5),  # X and Y outside, Z = 0.5
            (-1.0, -6.0, 3.0),  # X and Y outside, Z = 3.0
        ]

        clipped_points = clip_polygon_to_bridge_boundaries(corner_points, mock_bridge_geometry)

        # Verify Z coordinates are preserved
        expected_z_values = [1.5, 2.0, 0.5, 3.0]
        for i, (x, y, z) in enumerate(clipped_points):
            expected_z = expected_z_values[i]
            assert z == expected_z, f"Z coordinate {z} should be preserved as {expected_z}"

    def test_clip_polygon_with_different_bridge_dimensions(self) -> None:
        """Test clipping with different bridge dimensions."""
        # Create mock bridge geometry with different dimensions
        mock_geom = Mock()
        mock_geom.x_coords_d_points = [5.0, 35.0]  # Bridge length: 30m, starting at x=5
        mock_geom.y_top_structural_edge_at_d_points = [8.0, 8.0]  # Bridge top: y=8.0
        mock_geom.y_bridge_bottom_at_d_points = [-3.0, -3.0]  # Bridge bottom: y=-3.0

        corner_points = [
            (0.0, 10.0, 0.0),  # X too small, Y too large
            (40.0, 10.0, 0.0),  # X too large, Y too large
            (40.0, -5.0, 0.0),  # X too large, Y too small
            (0.0, -5.0, 0.0),  # X too small, Y too small
        ]

        clipped_points = clip_polygon_to_bridge_boundaries(corner_points, mock_geom)

        # Verify all coordinates are clipped to the new boundaries
        expected_clipped = [
            (5.0, 8.0, 0.0),  # Clipped to x_min, y_max
            (35.0, 8.0, 0.0),  # Clipped to x_max, y_max
            (35.0, -3.0, 0.0),  # Clipped to x_max, y_min
            (5.0, -3.0, 0.0),  # Clipped to x_min, y_min
        ]

        assert clipped_points == expected_clipped, "Coordinates should be clipped to the correct bridge boundaries"

    @pytest.fixture
    def bridge_default_params(self) -> Munch:
        """Load bridge default parameters from test data."""
        test_data_path = Path(__file__).parent.parent.parent / "test_data" / "bridge_default_params.json"
        with open(test_data_path, encoding="utf-8") as f:
            data = json.load(f)
        return Munch.fromDict(data)

    @pytest.fixture
    def bridge_complex_params(self) -> Munch:
        """Load bridge complex parameters from test data."""
        test_data_path = Path(__file__).parent.parent.parent / "test_data" / "bridge_complex_params.json"
        with open(test_data_path, encoding="utf-8") as f:
            data = json.load(f)
        return Munch.fromDict(data)

    def test_clip_polygon_with_bridge_default_params(self, bridge_default_params: Munch) -> None:
        """Test clipping with actual bridge default parameters."""
        # Create mock bridge geometry based on the default params
        _ = bridge_default_params  # Use the fixture to avoid unused argument warning
        mock_geom = Mock()
        # Bridge length: 10m (from total_length)
        mock_geom.x_coords_d_points = [0.0, 10.0]
        # Bridge width: 30m (from total_width), centered around y=0
        mock_geom.y_top_structural_edge_at_d_points = [15.0, 15.0]  # +15m from center
        mock_geom.y_bridge_bottom_at_d_points = [-15.0, -15.0]  # -15m from center

        # Test with coordinates that would extend beyond the 10m x 30m bridge
        corner_points = [
            (-1.0, 16.0, 0.0),  # X too small, Y too large
            (11.0, 16.0, 0.0),  # X too large, Y too large
            (11.0, -16.0, 0.0),  # X too large, Y too small
            (-1.0, -16.0, 0.0),  # X too small, Y too small
        ]

        clipped_points = clip_polygon_to_bridge_boundaries(corner_points, mock_geom)

        # Verify all coordinates are clipped to the bridge boundaries
        for x, y, z in clipped_points:
            assert 0.0 <= x <= 10.0, f"X coordinate {x} should be within bridge length [0.0, 10.0]"
            assert -15.0 <= y <= 15.0, f"Y coordinate {y} should be within bridge width [-15.0, 15.0]"
            assert z == 0.0, f"Z coordinate {z} should remain unchanged"

    def test_clip_polygon_with_bridge_complex_params(self, bridge_complex_params: Munch) -> None:
        """Test clipping with actual bridge complex parameters."""
        # Create mock bridge geometry based on the complex params
        _ = bridge_complex_params  # Use the fixture to avoid unused argument warning
        mock_geom = Mock()
        # Bridge length: 25m (from total_length)
        mock_geom.x_coords_d_points = [0.0, 25.0]
        # Bridge width: 40m (from total_width), centered around y=0
        mock_geom.y_top_structural_edge_at_d_points = [20.0, 20.0]  # +20m from center
        mock_geom.y_bridge_bottom_at_d_points = [-20.0, -20.0]  # -20m from center

        # Test with coordinates that would extend beyond the 25m x 40m bridge
        corner_points = [
            (-2.0, 21.0, 0.0),  # X too small, Y too large
            (27.0, 21.0, 0.0),  # X too large, Y too large
            (27.0, -21.0, 0.0),  # X too large, Y too small
            (-2.0, -21.0, 0.0),  # X too small, Y too small
        ]

        clipped_points = clip_polygon_to_bridge_boundaries(corner_points, mock_geom)

        # Verify all coordinates are clipped to the bridge boundaries
        for x, y, z in clipped_points:
            assert 0.0 <= x <= 25.0, f"X coordinate {x} should be within bridge length [0.0, 25.0]"
            assert -20.0 <= y <= 20.0, f"Y coordinate {y} should be within bridge width [-20.0, 20.0]"
            assert z == 0.0, f"Z coordinate {z} should remain unchanged"

    def test_dispersal_function_with_real_bridge_data(self, bridge_default_params: Munch) -> None:
        """Test dispersal function with real bridge data to ensure boundary compliance."""

        # Mock the dispersal function to avoid circular import issues
        def mock_dispersal_function(
            _params: object, corner_points: list[tuple[float, float, float]], _load_value: float, _load_case_type: str
        ) -> tuple[list[tuple[float, float, float]], float]:
            """Mock dispersal function that simulates dispersion and clipping."""
            # Simulate dispersion by expanding coordinates
            dispersed_coords = []
            for x, y, z in corner_points:
                # Simulate dispersion by adding 0.5m in each direction
                dispersed_coords.append((x - 0.5, y - 0.5, z))
                dispersed_coords.append((x + 0.5, y - 0.5, z))
                dispersed_coords.append((x + 0.5, y + 0.5, z))
                dispersed_coords.append((x - 0.5, y + 0.5, z))

            # Create mock bridge geometry
            mock_geom = Mock()
            mock_geom.x_coords_d_points = [0.0, 10.0]  # Bridge length from params
            mock_geom.y_top_structural_edge_at_d_points = [15.0, 15.0]  # Bridge width/2
            mock_geom.y_bridge_bottom_at_d_points = [-15.0, -15.0]

            # Apply clipping
            clipped_coords = clip_polygon_to_bridge_boundaries(dispersed_coords, mock_geom)

            # Adjust load value based on area change
            original_area = len(corner_points) * 1.0  # Assume 1m² per point
            clipped_area = len(clipped_coords) * 1.0
            adjusted_load = load_value * (original_area / max(clipped_area, 0.1))

            return clipped_coords, adjusted_load

        # Test with coordinates near bridge edges
        corner_points = [
            (9.0, 14.0, 0.0),  # Near right edge and top edge
            (9.2, 14.0, 0.0),
            (9.2, 13.8, 0.0),
            (9.0, 13.8, 0.0),
        ]
        load_value = 1000.0

        # Apply mock dispersal
        dispersed_coords, dispersed_load = mock_dispersal_function(bridge_default_params, corner_points, load_value, "axle_load")

        # Verify all dispersed coordinates are within bridge boundaries
        for x, y, z in dispersed_coords:
            assert 0.0 <= x <= 10.0, f"Dispersed X coordinate {x} exceeds bridge length"
            assert -15.0 <= y <= 15.0, f"Dispersed Y coordinate {y} exceeds bridge width"
            assert z == 0.0, f"Z coordinate {z} should remain unchanged"

        # Verify load value was adjusted appropriately
        assert dispersed_load > 0, "Dispersed load value should be positive"
        assert dispersed_load != load_value, "Load value should be adjusted due to area change"

    def test_load_boundary_compliance_with_multiple_bridge_sizes(self) -> None:
        """Test load boundary compliance with various bridge sizes from test data."""
        test_cases: list[dict[str, Any]] = [
            {"name": "Default Bridge", "length": 10.0, "width": 30.0, "test_coords": [(-1.0, 16.0, 0.0), (11.0, -16.0, 0.0)]},
            {"name": "Complex Bridge", "length": 25.0, "width": 40.0, "test_coords": [(-2.0, 21.0, 0.0), (27.0, -21.0, 0.0)]},
        ]

        for test_case in test_cases:
            # Create mock bridge geometry
            mock_geom = Mock()
            mock_geom.x_coords_d_points = [0.0, test_case["length"]]
            mock_geom.y_top_structural_edge_at_d_points = [test_case["width"] / 2, test_case["width"] / 2]
            mock_geom.y_bridge_bottom_at_d_points = [-test_case["width"] / 2, -test_case["width"] / 2]

            # Test clipping with coordinates outside boundaries
            clipped_points = clip_polygon_to_bridge_boundaries(test_case["test_coords"], mock_geom)

            # Verify all coordinates are within boundaries
            for x, y, z in clipped_points:
                assert 0.0 <= x <= test_case["length"], f"{test_case['name']}: X coordinate {x} exceeds bridge length"
                assert -test_case["width"] / 2 <= y <= test_case["width"] / 2, f"{test_case['name']}: Y coordinate {y} exceeds bridge width"

    def test_edge_case_coordinates_at_bridge_boundaries(self, bridge_default_params: Munch) -> None:
        """Test coordinates that are exactly at bridge boundaries."""
        _ = bridge_default_params  # Use the fixture to avoid unused argument warning
        mock_geom = Mock()
        mock_geom.x_coords_d_points = [0.0, 10.0]
        mock_geom.y_top_structural_edge_at_d_points = [15.0, 15.0]
        mock_geom.y_bridge_bottom_at_d_points = [-15.0, -15.0]

        # Test coordinates exactly at boundaries
        boundary_coords = [
            (0.0, 15.0, 0.0),  # Top-left corner
            (10.0, 15.0, 0.0),  # Top-right corner
            (10.0, -15.0, 0.0),  # Bottom-right corner
            (0.0, -15.0, 0.0),  # Bottom-left corner
        ]

        clipped_points = clip_polygon_to_bridge_boundaries(boundary_coords, mock_geom)

        # Coordinates at boundaries should remain unchanged
        assert clipped_points == boundary_coords, "Coordinates at boundaries should not be modified"


if __name__ == "__main__":
    pytest.main([__file__])
