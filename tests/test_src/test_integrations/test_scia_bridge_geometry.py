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
    get_bridge_deck_zone_coordinates,
    get_bridge_deck_zone_materials_and_thickness,
    get_bridge_load_zone_coordinates,
    get_bridge_load_zone_materials_and_thickness,
    get_deck_mat_and_thick_at_coord,
    get_dispersion_at_coord,
    get_load_mat_and_thick_at_coord,
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

        # Set berekeningsniveau to theoretical mode
        params.berekeningsniveau = "Theoretische wegindeling"

        # Add required attributes for theoretical functions
        params.__getitem__ = Mock(return_value="NEN 8700")  # For params["design_code"]

        # This should call the new clean function (mode parameter is ignored)
        result = generate_tandem_loads(params)

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

        # Set berekeningsniveau to actual mode
        params.berekeningsniveau = "Werkelijke wegindeling"

        # Configure dictionary-style access for design_code
        params.__getitem__ = Mock(side_effect=lambda x: "NEN 8700 afkeur" if x == "design_code" else None)
        params.__contains__ = Mock(return_value=True)  # For 'in' operator

        # Mock the load zones data that actual mode needs
        params.load_zones_data_array = []

        # Mock the road geometry function to avoid the "Road width must be positive" error
        with patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_road") as mock_road:
            mock_road.return_value = (10.0, 9.0)  # y_top=10.0, width=9.0

            # This should call the new clean function (mode parameter is ignored)
            result = generate_tandem_loads(params)

        # The result should be a list of load cases
        assert isinstance(result, list)

    def test_generate_tandem_loads_invalid_berekeningsniveau(self) -> None:
        """Test error handling for invalid berekeningsniveau value."""
        params = Mock()
        params.bridge_segments_array = [
            Mock(l=50, bz1=8.0, bz2=4.0, bz3=12.0, dz=1.8),
        ]
        # Set an invalid berekeningsniveau value (should fallback to theoretical)
        params.berekeningsniveau = "Invalid value"

        # Mock the design_code access for theoretical mode
        params.__getitem__ = Mock(return_value="NEN 8700 verbouw")

        # Should not raise an error, but fallback to theoretical mode
        result = generate_tandem_loads(params)
        assert isinstance(result, list)


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


class TestFullOutputDeckAndLoadZone:
    """Comprehensive output test for deck/load/load zone functions."""

    @staticmethod
    def make_params() -> Mock:
        """Create mock parameters for full output deck/load/load zone tests."""
        # D-parameters (bridge segments)
        # dz_2 values calculated to match expected zone_2 thickness: dz_2 = dz + expected_thickness
        d1 = Mock(bz1=10, bz2=3, bz3=16, dz=2.0, dz_2=2.8, afstand=None, oplegging=True, l=0)
        d2 = Mock(bz1=12, bz2=7, bz3=20, dz=2.4, dz_2=3.7, afstand=12, oplegging=False, l=12)
        d3 = Mock(bz1=15, bz2=4, bz3=17, dz=0.06, dz_2=0.4, afstand=9, oplegging=False, l=9)
        d4 = Mock(bz1=10, bz2=2, bz3=12, dz=0.785, dz_2=2.019, afstand=4, oplegging=True, l=4)
        params = Mock()
        params.bridge_segments_array = [d1, d2, d3, d4]

        # Load zones
        lz1 = Mock(type="Voetgangers", thickness=0.1, material="Asfalt", width_at_d=[1, 5, 9, 6])
        lz2 = Mock(type="Fietsers", thickness=0.445, material="Grind", width_at_d=[17, 7, 4, 3])
        lz3 = Mock(type="Berm", thickness=0.781, material="Beton (gewapend)", width_at_d=[7, 4, 8, 6])
        lz4 = Mock(type="Auto", thickness=0.873, material="Tegels", width_at_d=[9, 23, 16, None])
        params.load_zones = [lz1, lz2, lz3, lz4]
        params.load_zones_data_array = params.load_zones  # Fix for function expectation
        return params

    def test_full_output(self) -> None:
        """Comprehensive output test for deck/load/load zone functions."""
        params = self.make_params()

        deck_zone_coord = get_bridge_deck_zone_coordinates(params=params)
        load_zone_coord = get_bridge_load_zone_coordinates(params=params)
        assert deck_zone_coord == {
            "zone_1_1": [[0.0, 11.5, 0.0], [12.0, 15.5, 0.0], [12.0, 3.5, 0.0], [0.0, 1.5, 0.0]],
            "zone_2_1": [[0.0, 1.5, 0.0], [12.0, 3.5, 0.0], [12.0, -3.5, 0.0], [0.0, -1.5, 0.0]],
            "zone_3_1": [[0.0, -1.5, 0.0], [12.0, -3.5, 0.0], [12.0, -23.5, 0.0], [0.0, -17.5, 0.0]],
            "zone_1_2": [[12.0, 15.5, 0.0], [21.0, 17.0, 0.0], [21.0, 2.0, 0.0], [12.0, 3.5, 0.0]],
            "zone_2_2": [[12.0, 3.5, 0.0], [21.0, 2.0, 0.0], [21.0, -2.0, 0.0], [12.0, -3.5, 0.0]],
            "zone_3_2": [[12.0, -3.5, 0.0], [21.0, -2.0, 0.0], [21.0, -19.0, 0.0], [12.0, -23.5, 0.0]],
            "zone_1_3": [[21.0, 17.0, 0.0], [25.0, 11.0, 0.0], [25.0, 1.0, 0.0], [21.0, 2.0, 0.0]],
            "zone_2_3": [[21.0, 2.0, 0.0], [25.0, 1.0, 0.0], [25.0, -1.0, 0.0], [21.0, -2.0, 0.0]],
            "zone_3_3": [[21.0, -2.0, 0.0], [25.0, -1.0, 0.0], [25.0, -13.0, 0.0], [21.0, -19.0, 0.0]],
        }
        assert load_zone_coord == {
            "load_zone_1_1": [[0.0, 11.5, 0.0], [12.0, 15.5, 0.0], [12.0, 10.5, 0.0], [0.0, 10.5, 0.0]],
            "load_zone_2_1": [[0.0, 10.5, 0.0], [12.0, 10.5, 0.0], [12.0, 3.5, 0.0], [0.0, -6.5, 0.0]],
            "load_zone_3_1": [[0.0, -6.5, 0.0], [12.0, 3.5, 0.0], [12.0, -0.5, 0.0], [0.0, -13.5, 0.0]],
            "load_zone_4_1": [[0.0, -13.5, 0.0], [12.0, -0.5, 0.0], [12.0, -23.5, 0.0], [0.0, -17.5, 0.0]],
            "load_zone_1_2": [[12.0, 15.5, 0.0], [21.0, 17.0, 0.0], [21.0, 8.0, 0.0], [12.0, 10.5, 0.0]],
            "load_zone_2_2": [[12.0, 10.5, 0.0], [21.0, 8.0, 0.0], [21.0, 5.0, 0.0], [12.0, 3.5, 0.0]],
            "load_zone_3_2": [[12.0, 3.5, 0.0], [21.0, 5.0, 0.0], [21.0, -3.0, 0.0], [12.0, -0.5, 0.0]],
            "load_zone_4_2": [[12.0, -0.5, 0.0], [21.0, -3.0, 0.0], [21.0, -19.0, 0.0], [12.0, -23.5, 0.0]],
            "load_zone_1_3": [[21.0, 17.0, 0.0], [25.0, 11.0, 0.0], [25.0, 5.0, 0.0], [21.0, 8.0, 0.0]],
            "load_zone_2_3": [[21.0, 8.0, 0.0], [25.0, 5.0, 0.0], [25.0, 2.0, 0.0], [21.0, 5.0, 0.0]],
            "load_zone_3_3": [[21.0, 5.0, 0.0], [25.0, 2.0, 0.0], [25.0, -4.0, 0.0], [21.0, -3.0, 0.0]],
            "load_zone_4_3": [[21.0, -3.0, 0.0], [25.0, -4.0, 0.0], [25.0, -13.0, 0.0], [21.0, -19.0, 0.0]],
        }

        deck_zone_materials = get_bridge_deck_zone_materials_and_thickness(params=params)
        assert deck_zone_materials == {
            "zone_1_1": {"material": "C40/50", "thickness_start_d_line": 2, "thickness_end_d_line": 2.4, "distance_between_d_lines": 12},
            "zone_2_1": {"material": "C40/50", "thickness_start_d_line": 0.8, "thickness_end_d_line": 1.3, "distance_between_d_lines": 12},
            "zone_3_1": {"material": "C40/50", "thickness_start_d_line": 2, "thickness_end_d_line": 2.4, "distance_between_d_lines": 12},
            "zone_1_2": {"material": "C40/50", "thickness_start_d_line": 2.4, "thickness_end_d_line": 0.06, "distance_between_d_lines": 9},
            "zone_2_2": {"material": "C40/50", "thickness_start_d_line": 1.3, "thickness_end_d_line": 0.34, "distance_between_d_lines": 9},
            "zone_3_2": {"material": "C40/50", "thickness_start_d_line": 2.4, "thickness_end_d_line": 0.06, "distance_between_d_lines": 9},
            "zone_1_3": {"material": "C40/50", "thickness_start_d_line": 0.06, "thickness_end_d_line": 0.785, "distance_between_d_lines": 4},
            "zone_2_3": {"material": "C40/50", "thickness_start_d_line": 0.34, "thickness_end_d_line": 1.234, "distance_between_d_lines": 4},
            "zone_3_3": {"material": "C40/50", "thickness_start_d_line": 0.06, "thickness_end_d_line": 0.785, "distance_between_d_lines": 4},
        }
        load_zone_materials = get_bridge_load_zone_materials_and_thickness(params=params)
        assert load_zone_materials == {
            "load_zone_1_1": {"material": "Asfalt", "thickness": 0.1},
            "load_zone_2_1": {"material": "Grind", "thickness": 0.445},
            "load_zone_3_1": {"material": "Beton (gewapend)", "thickness": 0.781},
            "load_zone_4_1": {"material": "Tegels", "thickness": 0.873},
            "load_zone_1_2": {"material": "Asfalt", "thickness": 0.1},
            "load_zone_2_2": {"material": "Grind", "thickness": 0.445},
            "load_zone_3_2": {"material": "Beton (gewapend)", "thickness": 0.781},
            "load_zone_4_2": {"material": "Tegels", "thickness": 0.873},
            "load_zone_1_3": {"material": "Asfalt", "thickness": 0.1},
            "load_zone_2_3": {"material": "Grind", "thickness": 0.445},
            "load_zone_3_3": {"material": "Beton (gewapend)", "thickness": 0.781},
            "load_zone_4_3": {"material": "Tegels", "thickness": 0.873},
        }

        deck_materials, deck_thickness = get_deck_mat_and_thick_at_coord(params=params, coord=[5, 5, 0])
        load_materials, load_thickness = get_load_mat_and_thick_at_coord(params=params, coord=[5, 5, 0])
        dispersion = get_dispersion_at_coord(params=params, coord=[5, 5, 0])

        assert deck_materials == "C40/50"
        assert deck_thickness is not None
        assert pytest.approx(deck_thickness, rel=1e-2) == 2.1666666666666665
        assert load_materials == "Grind"
        assert load_thickness is not None
        assert pytest.approx(load_thickness, rel=1e-2) == 0.445
        assert dispersion["deck_zone"] is not None
        assert isinstance(dispersion["deck_zone"], float)
        assert dispersion["load_zone"] is not None
        assert isinstance(dispersion["load_zone"], float)


if __name__ == "__main__":
    pytest.main([__file__])
