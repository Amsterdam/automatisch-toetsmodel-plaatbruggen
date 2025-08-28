"""
Tests for SCIA bridge geometry functions.

Tests for bridge parameter extraction, geometry calculations, and coordinate transformations
from scia_load_generators.py and scia_coordinate_utils.py modules.
"""

from unittest.mock import Mock, patch

import pytest

from src.geometry.bridge_geometry_data import create_node_and_thickness_dict
from src.integrations.scia_integration.scia_coordinate_utils import (
    align_bridge_coordinates_to_scia,
    convert_loads_to_scia_format,
    convert_wheel_coordinates_to_3d,
    extract_zone_boundaries,
)
from src.integrations.scia_integration.scia_load_generators import (
    extract_bridge_dimensions,
    generate_tandem_loads,
)


class TestBridgeDimensionExtraction:
    """Test bridge dimension extraction functions."""

    def test_extract_bridge_dimensions_single_segment(self) -> None:
        """Test extracting dimensions from single segment."""
        params = Mock()
        segment = Mock()
        segment.l = 10.0
        segment.bz1 = 8.0
        segment.bz2 = 4.0
        segment.bz3 = 12.0
        segment.dz = 1.5
        segment.dz_2 = 2.0
        params.bridge_segments_array = [segment]

        result = extract_bridge_dimensions(params)

        assert result.total_length == 10.0
        assert result.total_width == 24.0  # 8+4+12
        assert result.zone_widths["bz1"] == 8.0
        assert result.zone_widths["bz2"] == 4.0
        assert result.zone_widths["bz3"] == 12.0
        assert result.first_segment_thickness == 1.5
        assert result.first_segment_thickness_2 == 2.0

    def test_extract_bridge_dimensions_multiple_segments(self) -> None:
        """Test extracting dimensions from multiple segments."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=5.0, bz2=3.0, bz3=7.0, dz=1.8, dz_2=2.2),
            Mock(l=15, bz1=6.0, bz2=4.0, bz3=8.0, dz=2.0, dz_2=2.5),
            Mock(l=20, bz1=7.0, bz2=5.0, bz3=9.0, dz=2.2, dz_2=2.8),
        ]

        result = extract_bridge_dimensions(params)

        assert result.total_length == 35.0  # 0+15+20
        assert result.total_width == 15.0  # 5+3+7 (from first segment)
        assert result.first_segment_thickness == 1.8

    def test_extract_bridge_dimensions_empty_segments(self) -> None:
        """Test error handling with empty segments."""
        params = Mock()
        params.bridge_segments_array = []

        with pytest.raises(IndexError, match="No bridge segments provided"):
            extract_bridge_dimensions(params)


class TestZoneBoundaryExtraction:
    """Test zone boundary calculation."""

    def test_extract_zone_boundaries_single_segment(self) -> None:
        """Test zone boundary calculation for single segment."""
        params = Mock()
        segment = Mock()
        segment.bz1 = 10.0
        segment.bz2 = 5.0
        segment.bz3 = 15.0
        params.bridge_segments_array = [segment]

        result = extract_zone_boundaries(params)

        boundaries = result["segment_1"]
        assert boundaries["z1_left"] == 12.5  # bz1 + bz2/2 = 10 + 2.5
        assert boundaries["z1_right"] == 2.5  # bz2/2 = 2.5
        assert boundaries["z3_left"] == -2.5  # -bz2/2 = -2.5
        assert boundaries["z3_right"] == -17.5  # -bz3 - bz2/2 = -15 - 2.5

    def test_extract_zone_boundaries_multiple_segments(self) -> None:
        """Test zone boundary calculation for multiple segments."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(bz1=8.0, bz2=4.0, bz3=12.0),
            Mock(bz1=10.0, bz2=6.0, bz3=14.0),
        ]

        result = extract_zone_boundaries(params)

        # First segment
        seg1 = result["segment_1"]
        assert seg1["z1_left"] == 10.0  # 8 + 2
        assert seg1["z1_right"] == 2.0  # 4/2
        assert seg1["z3_left"] == -2.0  # -4/2
        assert seg1["z3_right"] == -14.0  # -12 - 2

        # Second segment
        seg2 = result["segment_2"]
        assert seg2["z1_left"] == 13.0  # 10 + 3
        assert seg2["z1_right"] == 3.0  # 6/2
        assert seg2["z3_left"] == -3.0  # -6/2
        assert seg2["z3_right"] == -17.0  # -14 - 3


class TestTandemLoadGeneration:
    """Test tandem load generation with the new clean interface."""

    def test_generate_tandem_loads_theoretical_mode(self) -> None:
        """Test tandem load generation in theoretical mode."""
        params = Mock()
        mock_segment = Mock()
        mock_segment.l = 50
        mock_segment.bz1 = 8.0
        mock_segment.bz2 = 4.0
        mock_segment.bz3 = 12.0
        mock_segment.dz = 1.8
        mock_segment.dz_2 = 2.0  # Add missing attribute
        params.bridge_segments_array = [mock_segment]

        # Add required attributes for theoretical functions
        params.__getitem__ = Mock(return_value="NEN 8700")  # For params["design_code"]

        # This should call the new clean function
        result = generate_tandem_loads(params, mode="theoretical")

        # The result should be a list of load cases
        assert isinstance(result, list)
        # We can't test the exact content without mocking the helper functions,
        # but we can test that it returns the expected structure

    def test_generate_tandem_loads_actual_mode(self) -> None:
        """Test tandem load generation in actual mode."""
        params = Mock()
        mock_segment = Mock()
        mock_segment.l = 50
        mock_segment.bz1 = 8.0
        mock_segment.bz2 = 4.0
        mock_segment.bz3 = 12.0
        mock_segment.dz = 1.8
        mock_segment.dz_2 = 2.0  # Add missing attribute
        params.bridge_segments_array = [mock_segment]

        # Mock the load zones data that actual mode needs
        params.load_zones_data_array = []

        # Mock the road geometry function to avoid the "Road width must be positive" error
        with patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_road") as mock_road:
            mock_road.return_value = (10.0, 9.0)  # y_top=10.0, width=9.0

            # This should call the new clean function
            result = generate_tandem_loads(params, mode="actual")

        # The result should be a list of load cases
        assert isinstance(result, list)

    def test_generate_tandem_loads_invalid_mode(self) -> None:
        """Test error handling for invalid mode."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=50, bz1=8.0, bz2=4.0, bz3=12.0, dz=1.8),
        ]

        with pytest.raises(ValueError, match="Invalid mode 'invalid'"):
            generate_tandem_loads(params, mode="invalid")


class TestCoordinateConversion:
    """Test coordinate conversion functions."""

    def test_convert_wheel_coordinates_to_3d(self) -> None:
        """Test 2D to 3D coordinate conversion."""
        wheel_2d = [[10.0, 1.0], [10.4, 1.0], [10.4, 1.4], [10.0, 1.4]]

        result = convert_wheel_coordinates_to_3d(wheel_2d)

        expected = [(10.0, 1.0, 0.0), (10.4, 1.0, 0.0), (10.4, 1.4, 0.0), (10.0, 1.4, 0.0)]
        assert result == expected

    def test_align_bridge_coordinates_to_scia(self) -> None:
        """Test coordinate system alignment."""
        coords = [(10.0, 1.0, 0.0), (10.4, 1.0, 0.0), (10.4, 1.4, 0.0), (10.0, 1.4, 0.0)]
        bridge_center_y = 2.0

        result = align_bridge_coordinates_to_scia(coords, bridge_center_y)

        expected = [(10.0, 3.0, 0.0), (10.4, 3.0, 0.0), (10.4, 3.4, 0.0), (10.0, 3.4, 0.0)]
        assert result == expected

    def test_convert_loads_to_scia_format(self) -> None:
        """Test tandem data format conversion."""
        tandem_data = [
            {
                "load_case": "TestTandem",
                "loads": [
                    {
                        "wheels": [[[10.0, 1.0], [10.4, 1.0], [10.4, 1.4], [10.0, 1.4]]],
                        "load": 150000.0,
                    }
                ],
            }
        ]

        result = convert_loads_to_scia_format(tandem_data)

        assert len(result) == 1
        scia_load = result[0]
        assert scia_load["load_case"] == "TestTandem"
        assert len(scia_load["patch_loads"]) == 1
        patch_load = scia_load["patch_loads"][0]
        assert patch_load["load_value"] == 150000.0
        assert len(patch_load["corners"]) == 4
        # Check 3D conversion
        assert patch_load["corners"][0] == (10.0, 1.0, 0.0)


class TestNodeAndThicknessDictCreation:
    """Test node and thickness dictionary creation."""

    def test_create_node_and_thickness_dict_single_segment(self) -> None:
        """Test node creation with single bridge segment."""
        params = Mock()
        segment = Mock()
        segment.l = 10.0
        segment.bz1 = 5.0
        segment.bz2 = 3.0
        segment.bz3 = 4.0
        segment.dz = 2.0
        segment.dz_2 = 2.5
        params.bridge_segments_array = [segment]

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Should only create first cross-section nodes
        expected_nodes = {
            "K_dek:1_1": [10.0, 6.5, 0],  # x=10, y=bz1+bz2/2=5+1.5=6.5
            "K_dek:1_2": [10.0, 1.5, 0],  # x=10, y=bz2/2=1.5
            "K_dek:1_3": [10.0, -1.5, 0],  # x=10, y=-bz2/2=-1.5
            "K_dek:1_4": [10.0, -5.5, 0],  # x=10, y=-bz3-bz2/2=-4-1.5=-5.5
        }

        assert nodes_dict == expected_nodes
        assert thickness_dict == {}  # No plates with single segment

    def test_create_node_and_thickness_dict_multiple_segments(self) -> None:
        """Test node creation with multiple segments."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.0, dz_2=2.5),
            Mock(l=10, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.1, dz_2=2.6),
            Mock(l=8, bz1=5.0, bz2=3.0, bz3=4.0, dz=2.2, dz_2=2.7),
        ]

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Check cumulative lengths
        assert nodes_dict["K_dek:1_1"][0] == 0  # First segment
        assert nodes_dict["K_dek:2_1"][0] == 10  # Second segment
        assert nodes_dict["K_dek:3_1"][0] == 18  # Third segment (10+8)

        # Check thickness data for plates between segments
        expected_thickness = {
            "Z1_1": 2.1,
            "Z2_1": 2.6,
            "Z3_1": 2.1,
            "Z1_2": 2.2,
            "Z2_2": 2.7,
            "Z3_2": 2.2,
        }
        assert thickness_dict == expected_thickness

    def test_create_node_and_thickness_dict_empty_segments(self) -> None:
        """Test behavior with empty segments array."""
        params = Mock()
        params.bridge_segments_array = []

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        assert nodes_dict == {}
        assert thickness_dict == {}


class TestCoordinateCalculationAccuracy:
    """Test coordinate calculation accuracy with known values."""

    def test_coordinate_calculation_accuracy(self) -> None:
        """Test coordinate calculation accuracy with known bridge dimensions."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=0, bz1=10.0, bz2=5.0, bz3=15.0, dz=1.0, dz_2=1.0),
            Mock(l=20, bz1=10.0, bz2=5.0, bz3=15.0, dz=1.0, dz_2=1.0),
        ]

        nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

        # Check first cross-section coordinates
        # Zone layout: Zone 3 (15m) | Zone 2 (5m) | Zone 1 (10m)
        assert nodes_dict["K_dek:1_1"] == [0, 12.5, 0]  # Zone 1 left
        assert nodes_dict["K_dek:1_2"] == [0, 2.5, 0]  # Zone 1 right
        assert nodes_dict["K_dek:1_3"] == [0, -2.5, 0]  # Zone 3 left
        assert nodes_dict["K_dek:1_4"] == [0, -17.5, 0]  # Zone 3 right

        # Check second cross-section coordinates
        assert nodes_dict["K_dek:2_1"] == [20, 12.5, 0]
        assert nodes_dict["K_dek:2_2"] == [20, 2.5, 0]
        assert nodes_dict["K_dek:2_3"] == [20, -2.5, 0]
        assert nodes_dict["K_dek:2_4"] == [20, -17.5, 0]


if __name__ == "__main__":
    pytest.main([__file__])
