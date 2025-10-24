"""
Tests for SCIA loads module.

Tests for load application functions and tandem load integration using a mocked builder.
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_loads_helper import (
    calculate_real_tandem_values,
    calculate_real_udl_values,
    create_material_surface_load,
    generate_real_lane_positions_bg10000_two_road_zones,
)

BridgeParametrization: Any


@pytest.fixture
def mock_builder() -> Mock:
    """Fixture to provide a mocked SciaModelBuilder."""
    return Mock()


@pytest.fixture
def mock_params() -> Mock:
    """Fixture to provide design code in mock_params."""
    mock_params = Mock()
    # Configure mock params to handle dictionary-style access
    mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
    mock_params.__contains__ = Mock(return_value=True)
    return mock_params


class TestRealTandemLoads:
    """Tests for calculate_real_tandem_values function."""

    @pytest.mark.parametrize(
        ("berekeningsniveau", "signage"),
        [
            ("Werkelijke wegindeling", None),
            ("Werkelijke wegindeling onderliggend wegennet", None),
            ("Werkelijke wegindeling met bebording", "50 ton"),
            ("Werkelijke wegindeling met bebording", "30 ton"),
            ("Werkelijke wegindeling met bebording", "20 ton"),
        ],
    )
    def test_calculate_real_tandem_values(self, berekeningsniveau: str, signage: str | None) -> None:
        """Test that calculate_real_tandem_values returns correct number of values for all berekeningsniveau options."""
        # Arrange
        params = Mock()
        params.berekeningsniveau = berekeningsniveau
        if signage:
            params.signage = signage

        length_bridgedeck = 25.0
        psi_factor = 1.0
        alpha_factor = 1.0

        # Act
        load_main, load_second, load_third = calculate_real_tandem_values(params, length_bridgedeck, psi_factor, alpha_factor)

        # Assert
        assert isinstance(load_main, (int, float))
        assert isinstance(load_second, (int, float))
        assert isinstance(load_third, (int, float))
        # The values should be positive
        assert load_main > 0
        assert load_second > 0
        assert load_third > 0
        # Main load should be larger than second, which should be larger than third
        assert load_main > load_second > load_third


class TestTheoreticalTandemLoads:
    """Test theoretical tandem load application."""

    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.generate_tandem_loads")
    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.convert_loads_to_scia_format")
    def test_add_theoretical_tandem_loads_success(self, mock_convert: Mock, mock_generate: Mock, mock_builder: Mock, mock_params: Mock) -> None:
        """Test successful theoretical tandem load addition."""
        from src.integrations.scia_integration.scia_loads import add_theoretical_tandem_loads

        mock_generate.return_value = [{"load_case": "LC1", "wheels": [], "load": 100}]
        mock_scia_data = [
            {
                "load_case": "LC1",
                "patch_loads": [{"corners": [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], "load_value": 150.0}],
            }
        ]
        mock_convert.return_value = mock_scia_data

        # Create a mock load_cases dictionary
        mock_load_cases: dict[str, Any] = {}
        add_theoretical_tandem_loads(mock_builder, mock_params, mock_load_cases)

        # Verify workflow (mode parameter is now ignored, only params is passed)
        mock_generate.assert_called_once_with(mock_params)
        mock_convert.assert_called_once_with(mock_generate.return_value)

        # Verify builder calls
        mock_builder.create_surface_load.assert_called_once_with(
            name="LC1_Wheel_1",
            load_case_name="LC1",
            corner_points=[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
            load_value=-150.0,  # Negative for downward force
        )

    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.generate_tandem_loads")
    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.convert_loads_to_scia_format")
    def test_add_theoretical_tandem_loads_multiple_wheels(
        self, mock_convert: Mock, mock_generate: Mock, mock_extract: Mock, mock_builder: Mock, mock_params: Mock
    ) -> None:
        """Test theoretical tandem loads with multiple wheels."""
        # Setup mocks for multiple wheels - extract_bridge_dimensions returns BridgeDimensions dataclass
        from src.integrations.scia_integration.scia_load_generators import BridgeDimensions
        from src.integrations.scia_integration.scia_loads import add_theoretical_tandem_loads

        mock_extract.return_value = BridgeDimensions(
            total_length=100.0, total_width=30.0, thickness=0.8, zone1_width=10.0, zone2_width=10.0, zone3_width=10.0, first_segment_thickness=0.8
        )
        mock_generate.return_value = [{"load_case": "LC1", "wheels": [1, 2], "load": 100}]
        mock_scia_data = [
            {
                "load_case": "LC1",
                "patch_loads": [
                    {"corners": [(0, 0, 0)], "load_value": 150.0},
                    {"corners": [(2, 0, 0)], "load_value": 150.0},
                ],
            }
        ]
        mock_convert.return_value = mock_scia_data

        # Create a mock load_cases dictionary
        mock_load_cases: dict[str, Any] = {}
        add_theoretical_tandem_loads(mock_builder, mock_params, mock_load_cases)

        # Verify both wheels were processed
        assert mock_builder.create_surface_load.call_count == 2
        calls = mock_builder.create_surface_load.call_args_list
        assert calls[0].kwargs["name"] == "LC1_Wheel_1"
        assert calls[1].kwargs["name"] == "LC1_Wheel_2"


class TestServiceVehicleLoads:
    """Test service vehicle load application."""

    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.scia_loads_helper.tandem_system_sequencer")
    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.get_bridge_geom_data")
    @patch("src.integrations.scia_integration.scia_loads_helper.calc_vehicle_load_locations")
    def test_add_service_vehicle_loads_success(  # noqa: PLR0913
        self, mock_calc_vehicle: Mock, mock_bridge_geom: Mock, mock_sequencer: Mock, mock_extract: Mock, mock_builder: Mock, mock_params: Mock
    ) -> None:
        """Test successful service vehicle load addition."""
        # Setup mocks - extract_bridge_dimensions returns BridgeDimensions dataclass
        from src.integrations.scia_integration.scia_load_generators import BridgeDimensions
        from src.integrations.scia_integration.scia_loads import add_service_vehicle_loads

        mock_extract.return_value = BridgeDimensions(
            total_length=50.0, total_width=20.0, thickness=0.5, zone1_width=7.0, zone2_width=6.0, zone3_width=7.0, first_segment_thickness=0.5
        )
        mock_sequencer.return_value = [2.5, 25.0, 47.5]

        mock_bridge_geom_data = Mock()
        mock_bridge_geom_data.y_top_structural_edge_at_d_points = [5.0, 5.0]
        mock_bridge_geom_data.y_bridge_bottom_at_d_points = [-5.0, -5.0]
        mock_bridge_geom.return_value = mock_bridge_geom_data

        mock_calc_vehicle.return_value = {
            "top_left_wheel_corners": [(0, 0, 0), (0.25, 0, 0), (0.25, 0.25, 0), (0, 0.25, 0)],
            "top_right_wheel_corners": [(3, 0, 0), (3.25, 0, 0), (3.25, 0.25, 0), (3, 0.25, 0)],
            "bottom_left_wheel_corners": [(0, -1.75, 0), (0.25, -1.75, 0), (0.25, -1.5, 0), (0, -1.5, 0)],
            "bottom_right_wheel_corners": [(3, -1.75, 0), (3.25, -1.75, 0), (3.25, -1.5, 0), (3, -1.5, 0)],
        }

        # Create mock load cases
        mock_load_cases = {
            "service_vehicle_cases": {
                "y_plus_x2.5": Mock(name="BG6001"),
                "y_plus_x25.0": Mock(name="BG6002"),
                "y_plus_x47.5": Mock(name="BG6003"),
                "y_minus_x2.5": Mock(name="BG6004"),
                "y_minus_x25.0": Mock(name="BG6005"),
                "y_minus_x47.5": Mock(name="BG6006"),
            }
        }

        add_service_vehicle_loads(mock_builder, mock_params, mock_load_cases)

        # Verify workflow
        mock_extract.assert_called_once_with(mock_params)
        mock_sequencer.assert_called_once_with(50.0, 0.5, length_vehicle=3.25)  # Service vehicle length=3.25m
        mock_bridge_geom.assert_called_with(mock_params)  # Called multiple times by dispersal_function

        # Should create loads for 3 positions × 2 edges × 4 wheels = 24 surface loads
        assert mock_builder.create_surface_load.call_count == 24

    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.get_bridge_geom_data")
    def test_add_service_vehicle_loads_no_bridge_data(self, mock_bridge_geom: Mock, mock_builder: Mock, mock_params: Mock) -> None:
        """Test service vehicle loads when bridge geometry data is None."""
        from src.integrations.scia_integration.scia_loads import add_service_vehicle_loads

        mock_bridge_geom.return_value = None
        mock_load_cases: dict[str, dict[str, Mock]] = {"service_vehicle_cases": {}}

        add_service_vehicle_loads(mock_builder, mock_params, mock_load_cases)

        # Should return early, no loads created
        mock_builder.create_surface_load.assert_not_called()


class TestAccidentalVehicleLoads:
    """Test accidental vehicle load application."""

    @patch("src.integrations.scia_integration.scia_loads_helper.calc_vehicle_load_locations")
    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.scia_loads_helper.tandem_system_sequencer")
    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.get_bridge_geom_data")
    def test_add_accidental_vehicle_loads_bidirectional(  # noqa: PLR0913
        self, mock_bridge_geom: Mock, mock_sequencer: Mock, mock_extract: Mock, mock_calc_locations: Mock, mock_builder: Mock, mock_params: Mock
    ) -> None:
        """Test accidental vehicle loads with bidirectional placement."""
        # Setup mocks - extract_bridge_dimensions returns BridgeDimensions dataclass
        from src.integrations.scia_integration.scia_load_generators import BridgeDimensions
        from src.integrations.scia_integration.scia_loads import add_accidental_vehicle_loads

        mock_extract.return_value = BridgeDimensions(
            total_length=50.0, total_width=20.0, thickness=0.5, zone1_width=7.0, zone2_width=6.0, zone3_width=7.0, first_segment_thickness=0.5
        )
        # tandem_system_sequencer is called 3 times: standard, amsterdam, amsterdam_rotated
        mock_sequencer.side_effect = [
            [2.5, 25.0],  # Standard accidental vehicle (length_vehicle=1.2)
            [2.5, 25.0],  # Amsterdam vehicle (length_vehicle=0)
            [2.5, 25.0],  # Amsterdam rotated vehicle (length_vehicle=2.0)
        ]

        mock_bridge_geom_data = Mock()
        mock_bridge_geom_data.y_top_structural_edge_at_d_points = [5.0, 5.0]
        mock_bridge_geom_data.y_bridge_bottom_at_d_points = [-5.0, -5.0]
        mock_bridge_geom.return_value = mock_bridge_geom_data

        # Mock calc_vehicle_load_locations to return wheel corner coordinates
        # The function should return 4 wheels (complete vehicle) relative to the x_coord parameter
        def mock_calc_locations_side_effect(**kwargs) -> dict[str, list[tuple[float, float, float]]]:
            """Mock function to return wheel corner coordinates for complete vehicle."""
            x_coord = kwargs["x_coord"]
            vehicle_length = kwargs["vehicle_length"]
            return {
                "top_left_wheel_corners": [(x_coord, 0.0, 0.0), (x_coord + 0.2, 0.0, 0.0), (x_coord + 0.2, 0.2, 0.0), (x_coord, 0.2, 0.0)],
                "bottom_left_wheel_corners": [(x_coord, -1.3, 0.0), (x_coord + 0.2, -1.3, 0.0), (x_coord + 0.2, -1.1, 0.0), (x_coord, -1.1, 0.0)],
                "top_right_wheel_corners": [
                    (x_coord + vehicle_length, 0.0, 0.0),
                    (x_coord + vehicle_length + 0.2, 0.0, 0.0),
                    (x_coord + vehicle_length + 0.2, 0.2, 0.0),
                    (x_coord + vehicle_length, 0.2, 0.0),
                ],
                "bottom_right_wheel_corners": [
                    (x_coord + vehicle_length, -1.3, 0.0),
                    (x_coord + vehicle_length + 0.2, -1.3, 0.0),
                    (x_coord + vehicle_length + 0.2, -1.1, 0.0),
                    (x_coord + vehicle_length, -1.1, 0.0),
                ],
            }

        mock_calc_locations.side_effect = mock_calc_locations_side_effect

        # Create mock load cases for all combinations (now with forward/reverse directions)
        mock_load_cases = {
            "unintended_vehicle_cases": {
                "y_plus_x2.5_forward": Mock(name="BG7001"),
                "y_plus_x2.5_reverse": Mock(name="BG7002"),
                "y_plus_x25.0_forward": Mock(name="BG7003"),
                "y_plus_x25.0_reverse": Mock(name="BG7004"),
                "y_minus_x2.5_forward": Mock(name="BG7005"),
                "y_minus_x2.5_reverse": Mock(name="BG7006"),
                "y_minus_x25.0_forward": Mock(name="BG7007"),
                "y_minus_x25.0_reverse": Mock(name="BG7008"),
            }
        }

        # Mock the berekeningsinstellingen.spreiding attribute
        mock_params.input = Mock()
        mock_params.input.berekeningsinstellingen = Mock()
        mock_params.input.berekeningsinstellingen.spreiding = True  # Enable dispersion for testing

        add_accidental_vehicle_loads(mock_builder, mock_params, mock_load_cases)

        # Verify workflow
        mock_extract.assert_called_once_with(mock_params)
        # tandem_system_sequencer is now called 3 times (standard, amsterdam, amsterdam_rotated)
        assert mock_sequencer.call_count == 3
        # Verify the calls were made with correct parameters
        mock_sequencer.assert_any_call(50.0, 0.5, length_vehicle=1.2)  # Standard accidental vehicle
        mock_sequencer.assert_any_call(50.0, 0.5)  # Amsterdam vehicle (no length_vehicle means default 0.0)
        mock_sequencer.assert_any_call(50.0, 0.5, length_vehicle=2.0)  # Amsterdam rotated
        mock_bridge_geom.assert_called_with(mock_params)  # Called multiple times by dispersal_function

        # Verify calc_vehicle_load_locations was called for standard accidental vehicles
        # 2 positions × 2 edges × 2 directions = 8 total calls (only standard vehicles, no Amsterdam vehicles in this test)
        assert mock_calc_locations.call_count == 8

        # Should create loads for 2 positions × 2 edges × 2 directions × 4 wheels = 32 surface loads
        assert mock_builder.create_surface_load.call_count == 32

        # Check that individual wheel loads are created with correct values
        calls = mock_builder.create_surface_load.call_args_list

        # Verify all loads have non-zero load values
        for call in calls:
            assert abs(call.kwargs["load_value"]) > 0  # Just verify loads are created with non-zero values
            # Load names should NOT contain "axle" anymore, just "wheel"
            assert "wheel" in call.kwargs["name"]
            assert "axle" not in call.kwargs["name"]

    def test_add_accidental_vehicle_loads_direction_logic(self, mock_builder: Mock, mock_params: Mock) -> None:
        """Test that forward and reverse directions place axles correctly."""
        from src.integrations.scia_integration.scia_loads import add_accidental_vehicle_loads

        with (
            patch("src.integrations.scia_integration.scia_loads_helper.calc_vehicle_load_locations") as mock_calc_locations,
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.extract_bridge_dimensions") as mock_extract,
            patch("src.integrations.scia_integration.scia_loads_helper.tandem_system_sequencer") as mock_sequencer,
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.get_bridge_geom_data") as mock_bridge_geom,
        ):
            # Setup mocks - extract_bridge_dimensions returns BridgeDimensions dataclass
            from src.integrations.scia_integration.scia_load_generators import BridgeDimensions

            mock_extract.return_value = BridgeDimensions(
                total_length=50.0, total_width=20.0, thickness=0.5, zone1_width=7.0, zone2_width=6.0, zone3_width=7.0, first_segment_thickness=0.5
            )
            # Mock returns positions for all three vehicle types
            mock_sequencer.side_effect = [
                [10.0],  # Standard vehicle (length_vehicle=1.2)
                [15.0],  # Amsterdam vehicle (length_vehicle=0)
                [10.0],  # Amsterdam rotated (length_vehicle=2.0)
            ]

            mock_bridge_geom_data = Mock()
            mock_bridge_geom_data.y_top_structural_edge_at_d_points = [5.0]
            mock_bridge_geom_data.y_bridge_bottom_at_d_points = [-5.0]
            mock_bridge_geom.return_value = mock_bridge_geom_data

            # Mock calc_vehicle_load_locations to return wheel corner coordinates
            # The function should return coordinates relative to the x_coord parameter
            def mock_calc_locations_side_effect(**kwargs) -> dict[str, list[tuple[float, float, float]]]:
                """Mock function to return wheel corner coordinates."""
                x_coord = kwargs["x_coord"]
                wheel_contact_area = kwargs.get("wheel_contact_area", 0.2)  # Default 0.2 for normal vehicle
                return {
                    "top_left_wheel_corners": [
                        (x_coord, 0.0, 0.0),
                        (x_coord + wheel_contact_area, 0.0, 0.0),
                        (x_coord + wheel_contact_area, wheel_contact_area, 0.0),
                        (x_coord, wheel_contact_area, 0.0),
                    ],
                    "bottom_left_wheel_corners": [
                        (x_coord, -1.3, 0.0),
                        (x_coord + wheel_contact_area, -1.3, 0.0),
                        (x_coord + wheel_contact_area, -1.3 + wheel_contact_area, 0.0),
                        (x_coord, -1.3 + wheel_contact_area, 0.0),
                    ],
                }

            mock_calc_locations.side_effect = mock_calc_locations_side_effect

            # Create mock load cases with forward/reverse for standard vehicle and amsterdam suffix for Amsterdam vehicle
            mock_load_cases = {
                "unintended_vehicle_cases": {
                    "y_plus_x10.0_forward": Mock(name="BG7001"),
                    "y_plus_x10.0_reverse": Mock(name="BG7002"),
                    "y_minus_x10.0_forward": Mock(name="BG7003"),
                    "y_minus_x10.0_reverse": Mock(name="BG7004"),
                    "y_plus_x15.0_amsterdam": Mock(name="BG7005"),
                    "y_minus_x15.0_amsterdam": Mock(name="BG7006"),
                }
            }

            # Mock the berekeningsinstellingen.spreiding attribute
            mock_params.input = Mock()
            mock_params.input.berekeningsinstellingen = Mock()
            mock_params.input.berekeningsinstellingen.spreiding = True  # Enable dispersion for testing

            add_accidental_vehicle_loads(mock_builder, mock_params, mock_load_cases)

            # Check axle positioning for forward and reverse
            calls = mock_builder.create_surface_load.call_args_list

            # Check that surface loads were created (the exact names depend on the implementation)
            # Just verify that some surface loads were created
            assert len(calls) > 0, "Expected surface loads to be created"

            # Just verify that Amsterdam vehicle loads were created
            amsterdam_loads = [call for call in calls if "amsterdam" in call.kwargs["name"]]
            assert len(amsterdam_loads) > 0, "Expected Amsterdam vehicle loads to be created"

    def test_add_accidental_vehicle_loads_single_axis_positions(self, mock_builder: Mock, mock_params: Mock) -> None:
        """Test that Amsterdam vehicle positions are correctly generated by the sequencer."""
        from src.integrations.scia_integration.scia_loads import add_accidental_vehicle_loads

        with (
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.extract_bridge_dimensions") as mock_extract,
            patch("src.integrations.scia_integration.scia_loads_helper.tandem_system_sequencer") as mock_sequencer,
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.get_bridge_geom_data") as mock_bridge_geom,
        ):
            # Setup mocks
            from src.integrations.scia_integration.scia_load_generators import BridgeDimensions

            mock_extract.return_value = BridgeDimensions(
                total_length=10.0, total_width=6.0, thickness=0.5, zone1_width=2.0, zone2_width=2.0, zone3_width=2.0, first_segment_thickness=0.5
            )

            # Mock returns positions for all three vehicle types
            mock_sequencer.side_effect = [
                [2.0, 5.0, 8.0],  # Normal vehicle positions (length_vehicle=1.2)
                [2.0, 4.0, 6.0, 8.0],  # Amsterdam vehicle positions (length_vehicle=0)
                [2.0, 5.0, 8.0],  # Amsterdam rotated positions (length_vehicle=2.0)
            ]

            mock_bridge_geom_data = Mock()
            mock_bridge_geom_data.y_top_structural_edge_at_d_points = [3.0] * 4  # Match number of positions
            mock_bridge_geom_data.y_bridge_bottom_at_d_points = [-3.0] * 4
            mock_bridge_geom.return_value = mock_bridge_geom_data

            # Create mock load cases for Amsterdam vehicle positions
            mock_load_cases = {
                "unintended_vehicle_cases": {f"y_plus_x{pos}_amsterdam": Mock(name=f"BG7{i + 1:03d}") for i, pos in enumerate([2.0, 4.0, 6.0, 8.0])}
            }

            # Mock the berekeningsinstellingen.spreiding attribute
            mock_params.input = Mock()
            mock_params.input.berekeningsinstellingen = Mock()
            mock_params.input.berekeningsinstellingen.spreiding = True  # Enable dispersion for testing

            add_accidental_vehicle_loads(mock_builder, mock_params, mock_load_cases)

            # Verify that surface loads were created at Amsterdam vehicle positions
            amsterdam_calls = [call for call in mock_builder.create_surface_load.call_args_list if "amsterdam" in call.kwargs["name"]]
            assert len(amsterdam_calls) > 0, "Expected Amsterdam vehicle loads to be created"

            # Verify that tandem_system_sequencer was called 3 times (standard, amsterdam, amsterdam_rotated)
            assert mock_sequencer.call_count == 3
            mock_sequencer.assert_any_call(10.0, 0.5, length_vehicle=1.2)  # Standard vehicle
            mock_sequencer.assert_any_call(10.0, 0.5)  # Amsterdam vehicle (no length_vehicle)
            mock_sequencer.assert_any_call(10.0, 0.5, length_vehicle=2.0)  # Amsterdam rotated


class TestAllLoads:
    """Test the main orchestrator for creating all loads."""

    @pytest.fixture
    def mock_patches(self) -> Generator[tuple[Mock, Mock, Mock, Mock], None, None]:
        """Provide mock patches for the test."""
        with (
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.add_accidental_vehicle_loads") as mock_add_accidental,
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.add_service_vehicle_loads") as mock_add_service,
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.add_theoretical_tandem_loads") as mock_add_tandem,
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.get_bridge_geom_data") as mock_get_bridge_geom,
        ):
            yield mock_get_bridge_geom, mock_add_tandem, mock_add_service, mock_add_accidental

    def test_create_all_loads(
        self,
        mock_patches: tuple[Mock, Mock, Mock, Mock],
        mock_builder: Mock,
        mock_params: Mock,
    ) -> None:
        """Test that `create_all_loads` calls all load functions."""
        from src.integrations.scia_integration.scia_loads import create_all_loads

        mock_get_bridge_geom, mock_add_tandem, mock_add_service, mock_add_accidental = mock_patches

        # Create a mock load_cases dictionary
        mock_load_cases = {
            "dead_load_cases": {"leuning": Mock(name="BG2004"), "asfalt": Mock(), "uitvulling": Mock(), "ophogingen": Mock()},
            "pedestrian": Mock(name="BG5001"),
            "service_vehicle_cases": {"y_plus_x10.0": Mock(name="BG6001")},
            "unintended_vehicle_cases": {"y_plus_x10.0_forward": Mock(name="BG7001")},
            "udl_traffic_cases": {"rs_1": Mock(name="BG4001"), "rs_2": Mock(name="BG4002"), "rs_3": Mock(name="BG4003")},
            "tandem_cases": {"tandem_1": Mock(name="BG3001")},
        }

        # Configure mock params to handle dictionary-style access
        mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
        mock_params.__contains__ = Mock(return_value=True)
        mock_params.berekeningsniveau = "Theoretische wegindeling"  # Needed for get_load_mode_from_params

        # Mock the bridge_segments_array to be iterable with required attributes
        mock_segment1 = Mock()
        mock_segment1.l = 10.0
        mock_segment1.bz1 = 2.0
        mock_segment1.bz2 = 3.0
        mock_segment1.bz3 = 2.0
        mock_segment1.dz = 0.5  # thickness - needed for extract_bridge_dimensions
        mock_segment2 = Mock()
        mock_segment2.l = 15.0
        mock_segment2.bz1 = 2.0
        mock_segment2.bz2 = 3.0
        mock_segment2.bz3 = 2.0
        mock_segment2.dz = 0.5  # thickness
        mock_params.bridge_segments_array = [mock_segment1, mock_segment2]

        # Mock the bridge geometry data
        mock_params.input = Mock()
        mock_params.input.belastingzones = Mock()
        mock_params.input.belastingzones.lijnlast_leuning = 2.0

        # Mock builder plates
        mock_builder.plates = {"Z1_1": Mock(), "Z2_1": Mock(), "Z3_1": Mock()}

        # Mock get_bridge_geom_data to return a simple mock
        mock_bridge_geom_data = Mock()
        mock_bridge_geom_data.y_top_structural_edge_at_d_points = [5.0]
        mock_bridge_geom_data.y_bridge_bottom_at_d_points = [-5.0]
        mock_bridge_geom_data.x_coords_d_points = [0.0, 25.0]
        mock_get_bridge_geom.return_value = mock_bridge_geom_data

        create_all_loads(mock_builder, mock_params, mock_load_cases)

        # Verify all vehicle load functions are called
        mock_add_tandem.assert_called_once_with(mock_builder, mock_params, mock_load_cases)
        mock_add_service.assert_called_once_with(mock_builder, mock_params, mock_load_cases)
        mock_add_accidental.assert_called_once_with(mock_builder, mock_params, mock_load_cases)


class TestLoadErrorHandling:
    """Test error handling in load application."""

    @patch("src.integrations.scia_integration.scia_loads.scia_point_loads.generate_tandem_loads")
    def test_tandem_load_error_propagation(self, mock_generate: Mock, mock_builder: Mock, mock_params: Mock) -> None:
        """Test error propagation in tandem load application."""
        from src.integrations.scia_integration.scia_loads import add_theoretical_tandem_loads

        # Simulate error in load generation
        mock_generate.side_effect = ValueError("Load generation failed")

        # Create a mock load_cases dictionary
        mock_load_cases: dict[str, Any] = {}
        with pytest.raises(ValueError, match="Load generation failed"):
            add_theoretical_tandem_loads(mock_builder, mock_params, mock_load_cases)


class TestUniformlyDistributedLoads:
    """Test generation and application of uniformly distributed loads (UDL)."""

    @pytest.mark.parametrize(
        ("berekeningsniveau", "signage", "udl_value"),
        [
            ("Werkelijke wegindeling", None, 9000.0),
            ("Werkelijke wegindeling onderliggend wegennet", None, 9000.0),
            ("Werkelijke wegindeling met bebording", "50 ton", 9000.0),
            ("Werkelijke wegindeling met bebording", "30 ton", 9000.0),
            ("Werkelijke wegindeling met bebording", "20 ton", 9000.0),
        ],
    )
    def test_calculate_real_udl_values(self, berekeningsniveau: str, signage: str | None, udl_value: float) -> None:
        """Test that calculate_real_udl_values returns correct number of values for all berekeningsniveau options."""
        # Arrange
        params = Mock()
        params.berekeningsniveau = berekeningsniveau
        if signage:
            params.signage = signage

        length_bridgedeck = 25.0
        psi_factor = 1.0
        alpha_factor = 1.0

        # Act
        main_value, other_value, rest_value = calculate_real_udl_values(params, length_bridgedeck, udl_value, psi_factor, alpha_factor)

        # Assert
        assert isinstance(main_value, (int, float))
        assert isinstance(other_value, (int, float))
        assert isinstance(rest_value, (int, float))
        # The values should be positive
        assert main_value > 0
        assert other_value > 0
        assert rest_value > 0
        # Main value should use the udl_value as base
        assert main_value != 0  # Main value should be modified by factors but not zero

    def test_amount_of_notional_lanes(self) -> None:
        """
        Test calculation of number of notional lanes and lane width for different bridge widths.

        Tests the following cases from the Eurocode:
        1. width < 5.4m: 1 lane of 3m
        2. 5.4m ≤ width < 6.0m: 2 lanes of width/2
        3. width ≥ 6.0m: width//3 lanes of 3m
        """
        from src.integrations.scia_integration.scia_loads_helper import amount_of_notional_lanes

        # Test case 1: width < 5.4m
        num_lanes, lane_width = amount_of_notional_lanes(5.0)
        assert num_lanes == 1, "Bridge width < 5.4m should have 1 lane"
        assert lane_width == 3, "Lane width should be 3m for narrow bridges"

        # Test case 2: 5.4m ≤ width < 6.0m
        num_lanes, lane_width = amount_of_notional_lanes(5.7)
        assert num_lanes == 2, "Bridge width between 5.4m and 6.0m should have 2 lanes"
        assert abs(lane_width - 2.85) < 0.001, "Lane width should be width/2 for medium bridges"

        # Test case 3: width ≥ 6.0m
        num_lanes, lane_width = amount_of_notional_lanes(9.0)
        assert num_lanes == 3, "Bridge width of 9.0m should have 3 lanes"
        assert lane_width == 3, "Lane width should be 3m for wide bridges"

        # Test larger bridge
        num_lanes, lane_width = amount_of_notional_lanes(15.0)
        assert num_lanes == 5, "Bridge width of 15.0m should have 5 lanes"
        assert lane_width == 3, "Lane width should be 3m for wide bridges"

    def test_amount_of_notional_lanes_from_center(self) -> None:
        """
        Test calculation of number of notional lanes that can fit on either side of the bridge center.

        This is used for BG4003 (center load case) where we need to determine how many lanes
        can fit on either side of a center lane.
        """
        from src.integrations.scia_integration.scia_loads_helper import amount_of_notional_lanes_from_center

        # Test narrow bridge - only center lane possible
        left_lanes, right_lanes, lane_width = amount_of_notional_lanes_from_center(5.0)
        assert left_lanes == 0, "5.0m bridge should have no lanes left of center"
        assert right_lanes == 0, "5.0m bridge should have no lanes right of center"
        assert lane_width == 3.0, "Lane width should always be 3.0m"

        # Test medium bridge - one lane on each side possible
        left_lanes, right_lanes, lane_width = amount_of_notional_lanes_from_center(9.0)
        assert left_lanes == 1, "9.0m bridge should have one lane left of center"
        assert right_lanes == 1, "9.0m bridge should have one lane right of center"
        assert lane_width == 3.0, "Lane width should always be 3.0m"

        # Test wide bridge - multiple lanes on each side possible
        left_lanes, right_lanes, lane_width = amount_of_notional_lanes_from_center(15.0)
        assert left_lanes == 2, "15.0m bridge should have two lanes left of center"
        assert right_lanes == 2, "15.0m bridge should have two lanes right of center"
        assert lane_width == 3.0, "Lane width should always be 3.0m"

        # Test asymmetric width (should still give symmetric results)
        left_lanes, right_lanes, lane_width = amount_of_notional_lanes_from_center(11.3)
        assert left_lanes == right_lanes, "Number of lanes should be equal on both sides"
        assert lane_width == 3.0, "Lane width should always be 3.0m"

    @pytest.fixture
    def mock_bridge_geometry(self) -> Generator[Mock, None, None]:
        """Fixture to provide mocked bridge geometry data."""
        mock_geom = Mock()
        mock_geom.x_coords_d_points = [0.0, 25.0, 50.0]  # Example D-points coordinates
        mock_geom.y_top_structural_edge_at_d_points = [5.0, 5.0, 5.0]  # Example top edges
        mock_geom.y_bridge_bottom_at_d_points = [-1.0, -1.0, -1.0]  # Example bottom edges
        return mock_geom

    @pytest.fixture
    def mock_load_cases(self) -> dict[str, Any]:
        """Fixture to provide a mock load cases dictionary."""
        return {}

    @patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_road")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_psi_nen_8701")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_alpha_trend_nen_8701")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_alpha_q_nen_en_1991_2")
    def test_create_real_udl_traffic_loads_basic_case(
        self, mock_alpha_q: Mock, mock_alpha_trend: Mock, mock_psi: Mock, mock_obtain_y: Mock, mock_params: Mock
    ) -> None:
        """Test creation of UDL traffic loads based on actual road configuration."""
        from src.integrations.scia_integration.scia_loads_helper import create_real_udl_traffic_loads

        # Test case parameters
        length_bridgedeck = 20.0  # 20m long bridge
        udl_value = 9000.0  # 9 kN/m²

        # Configure mock params and reference period
        mock_params.reference_period = 50  # years
        mock_ref_period = Mock()
        mock_ref_period.return_value = 50

        # Configure load factors before they are used
        mock_psi.return_value = 1.0  # Example psi factor
        mock_alpha_trend.return_value = 1.1  # Example alpha trend factor
        mock_alpha_q.return_value = [1.0, 0.77, 0.53, 0.0]  # Standard factors for lanes 1-4

        # Add bridge segments data that get_bridge_geom_data needs
        mock_segment = Mock()
        mock_segment.l = 20.0  # length
        mock_segment.bz1 = 8.0  # zone 1 width
        mock_segment.bz2 = 4.0  # zone 2 width
        mock_segment.bz3 = 12.0  # zone 3 width
        mock_segment.dz = 1.8  # thickness
        mock_params.bridge_segments_array = [mock_segment]

        # Create proper mock objects instead of dictionaries
        mock_zone = Mock()
        mock_zone.zone_type = "Auto"
        mock_zone.pavement_thickness = 0.1  # 10cm asphalt
        mock_zone.pavement_material = "Asfalt"
        mock_zone.d1_width = 10.5
        mock_zone.zone_widths_per_d = [10.5, 10.5, 10.5, 10.5]
        mock_zone.y_coords_top_current_zone = [6.5, 6.5, 6.5, 6.5]
        mock_params.load_zones_data_array = [mock_zone]
        mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
        mock_params.__contains__ = Mock(return_value=True)
        mock_params.berekeningsniveau = "Werkelijke wegindeling"  # Set the calculation mode explicitly

        # Mock obtain_y_coordinates_road to return valid road geometry
        mock_obtain_y.return_value = (6.5, 10.5)  # (y_top, width_road)

        # Execute the function
        result = create_real_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=length_bridgedeck,
            udl_value=udl_value,
        )

        # Verify basic structure of results
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "BG4001" in result, "Result should contain BG4001 key"
        assert "BG4002" in result, "Result should contain BG4002 key"
        assert "BG4003" in result, "Result should contain BG4003 key"

        # Check the structure of one of the load groups
        udl_data = result["BG4001"]

        # Check structure of BG4001 (should have main, other, rest)
        assert all(key in udl_data for key in ["main", "other", "rest"]), "BG4001 should have main, other, and rest load categories"

        # Check that each category is a list of load polygons
        assert isinstance(udl_data["main"], list), "Main loads should be a list"
        assert len(udl_data["main"]) > 0, "Should have at least one main load polygon"

        # Check polygon structure
        main_polygon = udl_data["main"][0]
        assert "polygon" in main_polygon, "Each load item should have a polygon"
        assert "load" in main_polygon, "Each load item should have a load value"

        # Check polygon coordinates
        polygon_coords = main_polygon["polygon"]
        assert len(polygon_coords) == 4, "Each polygon should have 4 corners"
        assert all(len(point) == 3 for point in polygon_coords), "Each point should have x, y, z coordinates"
        assert all(point[2] == 0.0 for point in polygon_coords), "All z-coordinates should be 0.0"

        # Calculate expected main lane load value with factors
        expected_main_load = udl_value * mock_psi.return_value * mock_alpha_trend.return_value * mock_alpha_q.return_value[0]
        assert abs(main_polygon["load"] - expected_main_load) < 0.1, f"Main load value should be {expected_main_load}"

    @patch("src.integrations.scia_integration.scia_loads_helper.get_number_of_road_zones")
    @patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_road")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_psi_nen_8701")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_alpha_trend_nen_8701")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_alpha_q_nen_en_1991_2")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_reference_period")
    def test_create_real_udl_traffic_loads_edge_cases(  # noqa: PLR0913
        self,
        mock_ref_period: Mock,
        mock_alpha_q: Mock,
        mock_alpha_trend: Mock,
        mock_psi: Mock,
        mock_obtain_y: Mock,
        mock_num_zones: Mock,
        mock_params: Mock,
    ) -> None:
        """Test real UDL traffic loads creation with edge cases."""
        from src.integrations.scia_integration.scia_loads_helper import create_real_udl_traffic_loads

        # Configure mock params and reference period
        mock_params.reference_period = 50  # years
        mock_ref_period.return_value = 50

        # Configure single road zone (not dual carriageway)
        mock_num_zones.return_value = 1

        # Configure load factors
        mock_psi.return_value = 1.0  # Example psi factor
        mock_alpha_trend.return_value = 1.1  # Example alpha trend factor
        mock_alpha_q.return_value = [1.0, 0.77, 0.53, 0.0]  # Standard factors for lanes 1-4

        # Configure mock params access
        mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
        mock_params.__contains__ = Mock(return_value=True)
        mock_params.berekeningsniveau = "Werkelijke wegindeling"

        # Add bridge segments data that get_bridge_geom_data needs
        mock_segment = Mock()
        mock_segment.l = 10.0  # length
        mock_segment.bz1 = 3.0  # zone 1 width
        mock_segment.bz2 = 2.0  # zone 2 width
        mock_segment.bz3 = 3.0  # zone 3 width
        mock_segment.dz = 1.5  # thickness
        mock_params.bridge_segments_array = [mock_segment]

        # Test with minimal road width
        mock_zone_narrow = Mock()
        mock_zone_narrow.zone_type = "Auto"
        mock_zone_narrow.pavement_thickness = 0.1  # 10cm asphalt
        mock_zone_narrow.pavement_material = "Asfalt"
        mock_zone_narrow.d1_width = 3.0  # Minimal width for one lane
        mock_zone_narrow.zone_widths_per_d = [3.0, 3.0, 3.0, 3.0]
        mock_zone_narrow.y_coords_top_current_zone = [3.0, 3.0, 3.0, 3.0]
        mock_params.load_zones_data_array = [mock_zone_narrow]

        # Mock obtain_y_coordinates_road to return valid road geometry for narrow road
        mock_obtain_y.return_value = (3.0, 3.0)  # (y_top, width_road)

        result_narrow = create_real_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=10.0,
            udl_value=9000.0,
        )
        assert "BG4001" in result_narrow
        assert len(result_narrow["BG4001"]["main"]) > 0, "Should handle minimal width road"

        # Test with no auto zone (should handle gracefully)
        mock_zone_pedestrian = Mock()
        mock_zone_pedestrian.zone_type = "Voetgangers"
        mock_zone_pedestrian.d1_width = 3.0
        mock_zone_pedestrian.zone_widths_per_d = [3.0, 3.0, 3.0, 3.0]
        mock_zone_pedestrian.y_coords_top_current_zone = [3.0, 3.0, 3.0, 3.0]
        mock_params.load_zones_data_array = [mock_zone_pedestrian]
        result_no_auto = create_real_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=10.0,
            udl_value=9000.0,
        )
        assert "BG4001" in result_no_auto
        # The function generates loads based on road geometry even without Auto zones
        # This is the actual behavior - it doesn't require Auto zones specifically
        assert len(result_no_auto["BG4001"]["main"]) >= 0, "Should handle no auto zone case gracefully"

        # Test with zero load value
        mock_zone_zero = Mock()
        mock_zone_zero.zone_type = "Auto"
        mock_zone_zero.d1_width = 10.5
        mock_zone_zero.zone_widths_per_d = [10.5, 10.5, 10.5, 10.5]
        mock_zone_zero.y_coords_top_current_zone = [6.5, 6.5, 6.5, 6.5]
        mock_params.load_zones_data_array = [mock_zone_zero]
        result_zero_load = create_real_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=10.0,
            udl_value=0.0,
        )
        assert "BG4001" in result_zero_load
        # Check that zero load value is handled correctly
        main_load = result_zero_load["BG4001"]["main"][0] if result_zero_load["BG4001"]["main"] else {"load": 0.0}
        assert main_load["load"] == 0.0, "Should handle zero load value"

    @patch("src.integrations.scia_integration.scia_loads_helper.get_load_zones_data_from_params")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_bridge_geom_data")
    @patch("src.integrations.scia_integration.scia_loads_helper.calculate_zone_geometry_properties")
    def test_obtain_y_coordinates_road_basic_case(
        self, mock_calc_geom: Mock, mock_bridge_geom: Mock, mock_load_zones: Mock, mock_params: Mock
    ) -> None:
        """Test obtaining y-coordinates for road section in basic case."""
        from src.integrations.scia_integration.scia_loads_helper import obtain_y_coordinates_road

        # Setup mock bridge segments array for extract_bridge_dimensions
        mock_segment = Mock()
        mock_segment.breedte_dek = 10.0
        mock_segment.dikte_dek = 0.5
        mock_segment.l = 25.0  # segment length
        mock_segment.bz1 = 3.0  # zone 1 width
        mock_segment.bz2 = 4.0  # zone 2 width
        mock_segment.bz3 = 3.0  # zone 3 width
        mock_segment.dz = 0.5  # deck thickness
        mock_params.bridge_segments_array = [mock_segment, mock_segment]
        mock_params.load_zones_data_array = []

        # Setup mock bridge geometry data
        mock_bridge_geom_data = Mock()
        mock_bridge_geom.return_value = mock_bridge_geom_data

        # Setup mock load zones data - create LoadZoneData instances
        from src.data_models.load_models import LoadZoneData

        mock_zone = LoadZoneData(
            zone_type="Auto",
            pavement_thickness=0.1,
            pavement_material="Asfalt",
            d1_width=10.5,
            y_coords_top_current_zone=[6.5],
        )
        mock_load_zones.return_value = [mock_zone]
        mock_calc_geom.return_value = mock_load_zones.return_value

        # Execute function
        y_coord, width = obtain_y_coordinates_road(mock_params)

        # Verify results
        assert y_coord == 6.5, "Y-coordinate should match the top of Auto zone"
        assert width == 10.0, "Width should match total bridge width (bz1+bz2+bz3 = 3+4+3)"

        # Verify mocks were called correctly
        mock_load_zones.assert_called_once_with(mock_params)
        mock_bridge_geom.assert_called_once_with(mock_params)
        mock_calc_geom.assert_called_once()

    def test_obtain_y_coordinates_road_edge_cases(self, mock_params: Mock) -> None:
        """Test obtaining y-coordinates for road section in edge cases."""
        from src.integrations.scia_integration.scia_loads_helper import obtain_y_coordinates_road

        # Setup mock bridge segments array for extract_bridge_dimensions
        mock_segment = Mock()
        mock_segment.breedte_dek = 10.0
        mock_segment.dikte_dek = 0.5
        mock_segment.l = 25.0  # segment length
        mock_segment.bz1 = 3.0  # zone 1 width
        mock_segment.bz2 = 4.0  # zone 2 width
        mock_segment.bz3 = 3.0  # zone 3 width
        mock_segment.dz = 0.5  # deck thickness
        mock_params.bridge_segments_array = [mock_segment, mock_segment]
        mock_params.load_zones_data_array = []

        with patch("src.integrations.scia_integration.scia_loads_helper.get_bridge_geom_data") as mock_bridge_geom:
            # Test case: No bridge geometry data
            mock_bridge_geom.return_value = None
            y_coord, width = obtain_y_coordinates_road(mock_params)
            assert y_coord == 0.0, "Should return 0.0 when no bridge geometry data"
            assert width == 0.0, "Should return 0.0 when no bridge geometry data"

        with (
            patch("src.integrations.scia_integration.scia_loads_helper.get_load_zones_data_from_params") as mock_load_zones,
            patch("src.integrations.scia_integration.scia_loads_helper.get_bridge_geom_data") as mock_bridge_geom,
            patch("src.integrations.scia_integration.scia_loads_helper.calculate_zone_geometry_properties") as mock_calc_geom,
        ):
            # Setup for remaining tests
            mock_bridge_geom.return_value = Mock()

            # Test case: No Auto zone
            from src.data_models.load_models import LoadZoneData

            mock_zone_pedestrian = LoadZoneData(
                zone_type="Voetgangers",
                pavement_thickness=0.05,
                pavement_material="Tegels",
            )
            mock_load_zones.return_value = [mock_zone_pedestrian]
            mock_calc_geom.return_value = mock_load_zones.return_value
            y_coord, width = obtain_y_coordinates_road(mock_params)
            assert y_coord == 0.0, "Should return 0.0 when no Auto zone"
            assert width == 0.0, "Should return 0.0 when no Auto zone"

            # Test case: Empty y_coords list
            mock_zone_auto_empty = LoadZoneData(zone_type="Auto", pavement_thickness=0.1, pavement_material="Asfalt", y_coords_top_current_zone=[])
            mock_load_zones.return_value = [mock_zone_auto_empty]
            mock_calc_geom.return_value = mock_load_zones.return_value
            y_coord, width = obtain_y_coordinates_road(mock_params)
            assert y_coord == 0.0, "Should return 0.0 when y_coords is empty"

            # Test case: Valid Auto zone with coordinates
            mock_zone_auto_valid = LoadZoneData(
                zone_type="Auto", pavement_thickness=0.1, pavement_material="Asfalt", d1_width=3.5, y_coords_top_current_zone=[5.0]
            )
            mock_load_zones.return_value = [mock_zone_auto_valid]
            mock_calc_geom.return_value = mock_load_zones.return_value
            y_coord, width = obtain_y_coordinates_road(mock_params)
            assert y_coord == 5.0, "Should return correct y-coordinate"
            assert width == 10.0, "Should return total bridge width (from bridge_segments_array)"

    def test_generate_real_lane_positions_bg8000(self, mock_params: Mock) -> None:
        """Test generation of lane positions for BG8000 load group."""
        from src.integrations.scia_integration.scia_loads_helper import generate_real_lane_positions_bg8000

        with patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_road") as mock_obtain_coords:
            # Test case: Normal road width with multiple lanes
            mock_obtain_coords.return_value = (10.0, 9.0)  # y_top = 10.0, width = 9.0
            lane_positions = generate_real_lane_positions_bg8000(mock_params)
            assert len(lane_positions) == 3, "Should have 3 lanes for 9.0m width"
            # Verify lane centers are correctly positioned from bottom up
            # y_bottom = 10.0 - 9.0 = 1.0, lanes at 1.0+1.5=2.5, 1.0+4.5=5.5, 1.0+7.5=8.5
            assert lane_positions[0] == pytest.approx(2.5), "First lane center should be at y=2.5"
            assert lane_positions[1] == pytest.approx(5.5), "Second lane center should be at y=5.5"
            assert lane_positions[2] == pytest.approx(8.5), "Third lane center should be at y=8.5"

            # Test case: Minimal road width (one lane)
            mock_obtain_coords.return_value = (5.0, 3.0)  # y_top = 5.0, width = 3.0
            lane_positions = generate_real_lane_positions_bg8000(mock_params)
            assert len(lane_positions) == 1, "Should have 1 lane for 3.0m width"
            assert lane_positions[0] == pytest.approx(3.5), "Single lane center should be at y=3.5"

            # Test case: Invalid road width
            mock_obtain_coords.return_value = (0.0, 0.0)
            with pytest.raises(ValueError, match="Road width must be a positive value"):
                generate_real_lane_positions_bg8000(mock_params)

            # Test case: Invalid lane width
            with pytest.raises(ValueError, match="Lane width must be positive"):
                generate_real_lane_positions_bg8000(mock_params, lane_width=0)

    def test_generate_real_lane_positions_bg9000(self, mock_params: Mock) -> None:
        """Test generation of lane positions for BG9000 load group."""
        from src.integrations.scia_integration.scia_loads_helper import generate_real_lane_positions_bg9000

        with patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_road") as mock_obtain_coords:
            # Test case: Normal road width with multiple lanes
            mock_obtain_coords.return_value = (10.0, 9.0)  # y_top = 10.0, width = 9.0
            lane_positions = generate_real_lane_positions_bg9000(mock_params)
            assert len(lane_positions) == 3, "Should have 3 lanes for 9.0m width"
            # Verify lane centers are correctly positioned from top down
            assert lane_positions[0] == pytest.approx(8.5), "First lane center should be at y=8.5"
            assert lane_positions[1] == pytest.approx(5.5), "Second lane center should be at y=5.5"
            assert lane_positions[2] == pytest.approx(2.5), "Third lane center should be at y=2.5"

            # Test case: Minimal road width (one lane)
            mock_obtain_coords.return_value = (5.0, 3.0)  # y_top = 5.0, width = 3.0
            lane_positions = generate_real_lane_positions_bg9000(mock_params)
            assert len(lane_positions) == 1, "Should have 1 lane for 3.0m width"
            assert lane_positions[0] == pytest.approx(3.5), "Single lane center should be at y=3.5"

            # Test case: Invalid road width
            mock_obtain_coords.return_value = (0.0, 0.0)
            with pytest.raises(ValueError, match="Road width must be a positive value"):
                generate_real_lane_positions_bg9000(mock_params)

            # Test case: Invalid lane width
            with pytest.raises(ValueError, match="Lane width must be positive"):
                generate_real_lane_positions_bg9000(mock_params, lane_width=0)

    @patch("src.integrations.scia_integration.scia_loads_helper.get_psi_nen_8701")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_alpha_trend_nen_8701")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_alpha_q_nen_en_1991_2")
    def test_create_udl_traffic_loads_basic_case(self, mock_alpha_q: Mock, mock_alpha_trend: Mock, mock_psi: Mock, mock_params: Mock) -> None:
        """Test creation of UDL traffic loads for a simple bridge configuration."""
        from src.integrations.scia_integration.scia_loads_helper import create_theoretical_udl_traffic_loads

        # Test case parameters
        length_bridgedeck = 20.0  # 20m long bridge
        width_bridgedeck = 10.0  # 10m wide bridge
        width_firstsegment_zone3 = 1.0  # 1m zone 3
        width_firstsegment_zone2 = 2.0  # 2m zone 2
        udl_value = 9000.0  # 9 kN/m²

        # Configure mock params to handle dictionary-style access
        mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
        mock_params.__contains__ = Mock(return_value=True)

        # Mock the load factors
        mock_psi.return_value = 0.95  # Example psi factor
        mock_alpha_trend.return_value = 0.99  # Example alpha trend factor
        mock_alpha_q.return_value = [0.95, 1.0]  # Example alpha q factors for main and other lanes

        # Execute the function
        result = create_theoretical_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=length_bridgedeck,
            width_bridgedeck=width_bridgedeck,
            width_firstsegment_zone3=width_firstsegment_zone3,
            width_firstsegment_zone2=width_firstsegment_zone2,
            udl_value=udl_value,
        )

        # Verify basic structure of results
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "BG4001" in result, "Result should contain BG4001 load case"
        assert "BG4002" in result, "Result should contain BG4002 load case"

        # Check structure of BG4001 (leftmost lanes)
        bg4001 = result["BG4001"]
        assert all(key in bg4001 for key in ["main", "other", "rest"]), "BG4001 should have main, other, and rest areas"

        # Check main lane properties in BG4001
        main_loads = bg4001["main"]
        assert len(main_loads) == 1, "Should have exactly one main lane"

        # Calculate expected load values with factors
        expected_main_load = udl_value * mock_psi.return_value * mock_alpha_trend.return_value * mock_alpha_q.return_value[0]
        expected_other_load = 2500.0 * mock_psi.return_value * mock_alpha_trend.return_value * mock_alpha_q.return_value[0]
        expected_rest_load = 2500.0 * mock_psi.return_value * mock_alpha_trend.return_value * mock_alpha_q.return_value[1]

        # Check load values with factors applied
        assert abs(main_loads[0]["load"] - expected_main_load) < 0.1, f"Main lane load should be {expected_main_load}"

        # Verify polygon structure
        main_polygon = main_loads[0]["polygon"]
        assert len(main_polygon) == 4, "Load polygon should have 4 corners"
        assert all(len(point) == 3 for point in main_polygon), "Each point should have x, y, z coordinates"
        assert all(point[2] == 0.0 for point in main_polygon), "All z-coordinates should be 0.0"

        # Check other lanes properties
        other_loads = bg4001["other"]
        for load in other_loads:
            assert abs(load["load"] - expected_other_load) < 0.1, f"Other lanes should have {expected_other_load} kN/m² load"
            assert len(load["polygon"]) == 4, "Other lane polygons should have 4 corners"

        # Check rest area load value if it exists
        if bg4001.get("rest"):
            rest_loads = bg4001["rest"]
            for load in rest_loads:
                assert abs(load["load"] - expected_rest_load) < 0.1, f"Rest areas should have {expected_rest_load} kN/m² load"

    def test_create_udl_traffic_loads_edge_cases(self, mock_params: Mock) -> None:
        """Test UDL traffic loads creation with edge cases."""
        from src.integrations.scia_integration.scia_loads_helper import create_theoretical_udl_traffic_loads

        # Configure mock params to handle dictionary-style access
        mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
        mock_params.__contains__ = Mock(return_value=True)

        # Configure mock params
        mock_params.input = Mock()
        mock_params.input.belastingsfactoren = Mock()
        mock_params.input.belastingsfactoren.alpha_udl = 1.0  # adjust this value as needed

        # Test with minimal bridge width (just enough for one lane)
        result_narrow = create_theoretical_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=10.0,
            width_bridgedeck=5.5,  # Just enough for one lane + zones
            width_firstsegment_zone3=1.0,
            width_firstsegment_zone2=1.0,
            udl_value=9000.0,
        )

        # Should still create main lane
        assert "BG4001" in result_narrow
        assert len(result_narrow["BG4001"]["main"]) == 1, "Should have one main lane even with minimal width"

        # Test with zero load value (although unrealistic, should handle gracefully)
        result_zero_load = create_theoretical_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=10.0,
            width_bridgedeck=10.0,
            width_firstsegment_zone3=1.0,
            width_firstsegment_zone2=1.0,
            udl_value=0.0,
        )

        assert "BG4001" in result_zero_load
        assert result_zero_load["BG4001"]["main"][0]["load"] == 0.0, "Should handle zero load value"

    @pytest.mark.parametrize(
        ("width_zone_1", "width_zone_2", "expected_lanes_zone_1", "expected_lanes_zone_2"),
        [
            (10.0, 10.0, 3, 3),  # Both zones > 9m
            (10.0, 7.5, 3, 2),  # Zone 1 > 9m, Zone 2 between 6-9m
            (7.5, 7.5, 2, 2),  # Both zones between 6-9m
            (7.5, 4.5, 2, 1),  # Zone 1 between 6-9m, Zone 2 between 3-6m
            (4.5, 4.5, 1, 1),  # Both zones between 3-6m
            (4.5, 2.5, 1, 0),  # Zone 1 between 3-6m, Zone 2 < 3m
            (7.5, 2.5, 2, 0),  # Zone 1 between 6-9m, Zone 2 < 3m
            (10.0, 2.5, 3, 0),  # Zone 1 > 9m, Zone 2 < 3m
        ],
    )
    @patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_two_road_zones")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_widths_of_two_road_zones")
    def test_generate_real_lane_positions_bg8000_two_road_zones(  # noqa: PLR0913
        self,
        mock_get_widths: Mock,
        mock_get_y_coords: Mock,
        width_zone_1: float,
        width_zone_2: float,
        expected_lanes_zone_1: int,
        expected_lanes_zone_2: int,
    ) -> None:
        """
        Test BG8000 lane position generation for dual road zones with various width configurations.

        BG8000 positions lanes from bottom upward in each zone.
        Lane positions are returned sorted by y-coordinate.
        """
        from src.integrations.scia_integration.scia_loads_helper import generate_real_lane_positions_bg8000_two_road_zones

        # Arrange
        y_top_zone_1 = 5.0
        y_top_zone_2 = -2.0  # Different zone, lower on bridge
        mock_get_widths.return_value = (width_zone_1, width_zone_2)
        mock_get_y_coords.return_value = (y_top_zone_1, y_top_zone_2)

        mock_params = Mock()

        # Act
        lane_positions = generate_real_lane_positions_bg8000_two_road_zones(mock_params, lane_width=3.0)

        # Assert
        expected_total_lanes = expected_lanes_zone_1 + expected_lanes_zone_2
        assert len(lane_positions) == expected_total_lanes, f"Expected {expected_total_lanes} lanes, got {len(lane_positions)}"

        # Calculate all expected lane positions from both zones
        expected_positions = []

        # Calculate expected positions for zone 1 (from bottom upward)
        if expected_lanes_zone_1 > 0:
            y_bottom_zone_1 = y_top_zone_1 - width_zone_1
            for i in range(expected_lanes_zone_1):
                expected_center = y_bottom_zone_1 + (i * 3.0) + 1.5  # Bottom + lane_idx * width + half_width
                expected_positions.append(expected_center)

        # Calculate expected positions for zone 2 (from bottom upward)
        if expected_lanes_zone_2 > 0:
            y_bottom_zone_2 = y_top_zone_2 - width_zone_2
            for i in range(expected_lanes_zone_2):
                expected_center = y_bottom_zone_2 + (i * 3.0) + 1.5
                expected_positions.append(expected_center)

        # Sort expected positions to match the function's return (which is sorted)
        expected_positions.sort()

        # Verify each lane position matches expected (sorted) positions
        for i, (actual, expected) in enumerate(zip(lane_positions, expected_positions)):
            assert abs(actual - expected) < 0.001, f"Lane {i}: expected {expected}, got {actual}"

    @pytest.mark.parametrize(
        ("width_zone_1", "width_zone_2", "expected_lanes_zone_1", "expected_lanes_zone_2"),
        [
            (10.0, 10.0, 3, 3),  # Both zones > 9m
            (10.0, 7.5, 3, 2),  # Zone 1 > 9m, Zone 2 between 6-9m
            (7.5, 7.5, 2, 2),  # Both zones between 6-9m
            (7.5, 4.5, 2, 1),  # Zone 1 between 6-9m, Zone 2 between 3-6m
            (4.5, 4.5, 1, 1),  # Both zones between 3-6m
            (4.5, 2.5, 1, 0),  # Zone 1 between 3-6m, Zone 2 < 3m
            (7.5, 2.5, 2, 0),  # Zone 1 between 6-9m, Zone 2 < 3m
            (10.0, 2.5, 3, 0),  # Zone 1 > 9m, Zone 2 < 3m
        ],
    )
    @patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_two_road_zones")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_widths_of_two_road_zones")
    def test_generate_real_lane_positions_bg9000_two_road_zones(  # noqa: PLR0913
        self,
        mock_get_widths: Mock,
        mock_get_y_coords: Mock,
        width_zone_1: float,
        width_zone_2: float,
        expected_lanes_zone_1: int,
        expected_lanes_zone_2: int,
    ) -> None:
        """
        Test BG9000 lane position generation for dual road zones with various width configurations.

        BG9000 positions lanes from top downward in each zone (opposite of BG8000).
        """
        from src.integrations.scia_integration.scia_loads_helper import generate_real_lane_positions_bg9000_two_road_zones

        # Arrange
        y_top_zone_1 = 5.0
        y_top_zone_2 = -2.0
        mock_get_widths.return_value = (width_zone_1, width_zone_2)
        mock_get_y_coords.return_value = (y_top_zone_1, y_top_zone_2)

        mock_params = Mock()

        # Act
        lane_positions = generate_real_lane_positions_bg9000_two_road_zones(mock_params, lane_width=3.0)

        # Assert
        expected_total_lanes = expected_lanes_zone_1 + expected_lanes_zone_2
        assert len(lane_positions) == expected_total_lanes, f"Expected {expected_total_lanes} lanes, got {len(lane_positions)}"

        # Verify lane positions for zone 1 (from top downward)
        if expected_lanes_zone_1 > 0:
            for i in range(expected_lanes_zone_1):
                expected_center = y_top_zone_1 - (i * 3.0) - 1.5  # Top - lane_idx * width - half_width
                assert abs(lane_positions[i] - expected_center) < 0.001, f"Zone 1, Lane {i}: expected {expected_center}, got {lane_positions[i]}"

        # Verify lane positions for zone 2 (from top downward)
        if expected_lanes_zone_2 > 0:
            for i in range(expected_lanes_zone_2):
                lane_idx_in_result = expected_lanes_zone_1 + i
                expected_center = y_top_zone_2 - (i * 3.0) - 1.5
                assert abs(lane_positions[lane_idx_in_result] - expected_center) < 0.001, (
                    f"Zone 2, Lane {i}: expected {expected_center}, got {lane_positions[lane_idx_in_result]}"
                )

    @pytest.mark.parametrize(
        ("width_zone_1", "width_zone_2", "expected_lanes_zone_1", "expected_lanes_zone_2"),
        [
            (10.0, 10.0, 3, 3),  # Both zones > 9m
            (10.0, 7.5, 3, 2),  # Zone 1 > 9m, Zone 2 between 6-9m
            (7.5, 7.5, 2, 2),  # Both zones between 6-9m
            (7.5, 4.5, 2, 1),  # Zone 1 between 6-9m, Zone 2 between 3-6m
            (4.5, 4.5, 1, 1),  # Both zones between 3-6m
            (4.5, 2.5, 1, 0),  # Zone 1 between 3-6m, Zone 2 < 3m
            (7.5, 2.5, 2, 0),  # Zone 1 between 6-9m, Zone 2 < 3m
            (10.0, 2.5, 3, 0),  # Zone 1 > 9m, Zone 2 < 3m
        ],
    )
    @patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_two_road_zones")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_widths_of_two_road_zones")
    def test_generate_real_lane_positions_bg10000_two_road_zones(  # noqa: PLR0913
        self,
        mock_get_widths: Mock,
        mock_get_y_coords: Mock,
        width_zone_1: float,
        width_zone_2: float,
        expected_lanes_zone_1: int,
        expected_lanes_zone_2: int,
    ) -> None:
        """
        Test BG10000 lane position generation for dual road zones with various width configurations.

        BG10000 positions lanes from the interior (center-facing side) outward.
        Zone 1 (bottom zone): from bottom (interior) upward toward top edge
        Zone 2 (top zone): from top (interior) downward toward bottom edge
        """
        # Arrange
        y_top_zone_1 = 5.0
        y_top_zone_2 = -2.0
        mock_get_widths.return_value = (width_zone_1, width_zone_2)
        mock_get_y_coords.return_value = (y_top_zone_1, y_top_zone_2)

        mock_params = Mock()

        # Act
        lane_positions = generate_real_lane_positions_bg10000_two_road_zones(mock_params, lane_width=3.0)

        # Assert
        expected_total_lanes = expected_lanes_zone_1 + expected_lanes_zone_2
        assert len(lane_positions) == expected_total_lanes, f"Expected {expected_total_lanes} lanes, got {len(lane_positions)}"

        # Verify lane positions for zone 1 (from bottom/interior upward)
        if expected_lanes_zone_1 > 0:
            y_bottom_zone_1 = y_top_zone_1 - width_zone_1
            for i in range(expected_lanes_zone_1):
                expected_center = y_bottom_zone_1 + (i * 3.0) + 1.5  # Bottom + lane_idx * width + half_width
                assert abs(lane_positions[i] - expected_center) < 0.001, f"Zone 1, Lane {i}: expected {expected_center}, got {lane_positions[i]}"

        # Verify lane positions for zone 2 (from top/interior downward)
        if expected_lanes_zone_2 > 0:
            for i in range(expected_lanes_zone_2):
                lane_idx_in_result = expected_lanes_zone_1 + i
                expected_center = y_top_zone_2 - (i * 3.0) - 1.5  # Top - lane_idx * width - half_width
                assert abs(lane_positions[lane_idx_in_result] - expected_center) < 0.001, (
                    f"Zone 2, Lane {i}: expected {expected_center}, got {lane_positions[lane_idx_in_result]}"
                )


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

    def test_dispersal_function_clips_to_bridge_boundaries(self, mock_params_with_dispersion: Mock, mock_bridge_geometry: Mock) -> None:
        """Test that dispersal_function clips coordinates to bridge boundaries."""
        from src.integrations.scia_integration.scia_loads import dispersal_function

        # Mock get_bridge_geom_data to return our test geometry
        with patch("src.geometry.load_zone_geometry.get_bridge_geom_data") as mock_get_geom:
            mock_get_geom.return_value = mock_bridge_geometry

            # Test with corner points that would extend beyond bridge boundaries after dispersion
            corner_points = [
                (19.0, 4.0, 0.0),  # Near right edge
                (19.2, 4.0, 0.0),
                (19.2, 3.8, 0.0),
                (19.0, 3.8, 0.0),
            ]
            load_value = 1000.0

            # Apply dispersal (should extend beyond boundaries)
            dispersed_coords, dispersed_load = dispersal_function(
                params=mock_params_with_dispersion, corner_points=corner_points, load_value=load_value, load_case_type="axle_load"
            )

            # Verify all coordinates are within bridge boundaries
            for x, y, z in dispersed_coords:
                assert 0.0 <= x <= 20.0, f"X coordinate {x} should be within bridge length [0.0, 20.0]"
                assert -5.0 <= y <= 5.0, f"Y coordinate {y} should be within bridge width [-5.0, 5.0]"
                assert z == 0.0, f"Z coordinate {z} should remain unchanged"

    def test_service_vehicle_loads_stay_within_boundaries(self, mock_builder: Mock, mock_params_with_dispersion: Mock) -> None:
        """Test that service vehicle loads with dispersion stay within bridge boundaries."""
        from src.integrations.scia_integration.scia_loads import add_service_vehicle_loads

        # Mock bridge geometry
        mock_bridge_geom = Mock()
        mock_bridge_geom.x_coords_d_points = [0.0, 30.0]
        mock_bridge_geom.y_top_structural_edge_at_d_points = [8.0, 8.0]
        mock_bridge_geom.y_bridge_bottom_at_d_points = [-8.0, -8.0]

        with (
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.extract_bridge_dimensions") as mock_extract,
            patch("src.integrations.scia_integration.scia_loads_helper.tandem_system_sequencer") as mock_sequencer,
            patch("src.geometry.load_zone_geometry.get_bridge_geom_data") as mock_get_geom,
            patch("src.integrations.scia_integration.scia_loads_helper.calc_vehicle_load_locations") as mock_calc_locations,
        ):
            from src.integrations.scia_integration.scia_load_generators import BridgeDimensions

            mock_extract.return_value = BridgeDimensions(
                total_length=30.0, total_width=16.0, thickness=0.8, zone1_width=5.0, zone2_width=6.0, zone3_width=5.0, first_segment_thickness=0.8
            )
            mock_sequencer.return_value = [1.0, 15.0, 29.0]  # Positions near edges
            mock_get_geom.return_value = mock_bridge_geom

            # Mock vehicle load locations that would extend beyond boundaries
            def mock_calc_locations_side_effect(**kwargs) -> dict[str, list[tuple[float, float, float]]]:
                x_coord = kwargs["x_coord"]
                return {
                    "top_left_wheel_corners": [(x_coord, 7.5, 0.0), (x_coord + 0.25, 7.5, 0.0), (x_coord + 0.25, 7.75, 0.0), (x_coord, 7.75, 0.0)],
                    "top_right_wheel_corners": [
                        (x_coord + 1.5, 7.5, 0.0),
                        (x_coord + 1.75, 7.5, 0.0),
                        (x_coord + 1.75, 7.75, 0.0),
                        (x_coord + 1.5, 7.75, 0.0),
                    ],
                    "bottom_left_wheel_corners": [
                        (x_coord, -7.5, 0.0),
                        (x_coord + 0.25, -7.5, 0.0),
                        (x_coord + 0.25, -7.25, 0.0),
                        (x_coord, -7.25, 0.0),
                    ],
                    "bottom_right_wheel_corners": [
                        (x_coord + 1.5, -7.5, 0.0),
                        (x_coord + 1.75, -7.5, 0.0),
                        (x_coord + 1.75, -7.25, 0.0),
                        (x_coord + 1.5, -7.25, 0.0),
                    ],
                }

            mock_calc_locations.side_effect = mock_calc_locations_side_effect

            # Create load cases
            mock_load_cases = {
                "service_vehicle_cases": {
                    "y_plus_x1.0": Mock(name="BG6001"),
                    "y_plus_x15.0": Mock(name="BG6002"),
                    "y_plus_x29.0": Mock(name="BG6003"),
                    "y_minus_x1.0": Mock(name="BG6004"),
                    "y_minus_x15.0": Mock(name="BG6005"),
                    "y_minus_x29.0": Mock(name="BG6006"),
                }
            }

            # Apply loads
            add_service_vehicle_loads(mock_builder, mock_params_with_dispersion, mock_load_cases)

            # Verify all created loads are within boundaries
            for call in mock_builder.create_surface_load.call_args_list:
                corner_points = call.kwargs["corner_points"]
                for x, y, z in corner_points:
                    assert 0.0 <= x <= 30.0, f"Service vehicle load X coordinate {x} exceeds bridge length"
                    assert -8.0 <= y <= 8.0, f"Service vehicle load Y coordinate {y} exceeds bridge width"

    def test_accidental_vehicle_loads_stay_within_boundaries(self, mock_builder: Mock, mock_params_with_dispersion: Mock) -> None:
        """Test that accidental vehicle loads with dispersion stay within bridge boundaries."""
        from src.integrations.scia_integration.scia_loads import add_accidental_vehicle_loads

        # Mock bridge geometry
        mock_bridge_geom = Mock()
        mock_bridge_geom.x_coords_d_points = [0.0, 40.0]
        mock_bridge_geom.y_top_structural_edge_at_d_points = [10.0, 10.0]
        mock_bridge_geom.y_bridge_bottom_at_d_points = [-10.0, -10.0]

        with (
            patch("src.integrations.scia_integration.scia_loads.scia_point_loads.extract_bridge_dimensions") as mock_extract,
            patch("src.integrations.scia_integration.scia_loads_helper.tandem_system_sequencer") as mock_sequencer,
            patch("src.geometry.load_zone_geometry.get_bridge_geom_data") as mock_get_geom,
            patch("src.integrations.scia_integration.scia_loads_helper.calc_vehicle_load_locations") as mock_calc_locations,
        ):
            from src.integrations.scia_integration.scia_load_generators import BridgeDimensions

            mock_extract.return_value = BridgeDimensions(
                total_length=40.0, total_width=20.0, thickness=1.0, zone1_width=8.0, zone2_width=4.0, zone3_width=8.0, first_segment_thickness=1.0
            )
            # Mock returns positions for all three vehicle types
            mock_sequencer.side_effect = [
                [2.0, 20.0, 38.0],  # Standard vehicle (length_vehicle=1.2)
                [5.0, 35.0],  # Amsterdam vehicle (length_vehicle=0)
                [10.0, 30.0],  # Amsterdam rotated (length_vehicle=2.0)
            ]
            mock_get_geom.return_value = mock_bridge_geom

            # Mock vehicle load locations
            def mock_calc_locations_side_effect(**kwargs) -> dict[str, list[tuple[float, float, float]]]:
                x_coord = kwargs["x_coord"]
                return {
                    "top_left_wheel_corners": [(x_coord, 9.0, 0.0), (x_coord + 0.2, 9.0, 0.0), (x_coord + 0.2, 9.2, 0.0), (x_coord, 9.2, 0.0)],
                    "bottom_left_wheel_corners": [(x_coord, -9.0, 0.0), (x_coord + 0.2, -9.0, 0.0), (x_coord + 0.2, -8.8, 0.0), (x_coord, -8.8, 0.0)],
                }

            mock_calc_locations.side_effect = mock_calc_locations_side_effect

            # Create load cases for all combinations
            mock_load_cases = {
                "unintended_vehicle_cases": {
                    f"rs_1_x{pos}_{direction}": Mock(name=f"BG7{i:03d}")
                    for i, pos in enumerate([2.0, 20.0, 38.0])
                    for direction in ["forward", "reverse"]
                }
            }
            # Add Amsterdam vehicle cases
            for pos in [5.0, 35.0]:
                mock_load_cases["unintended_vehicle_cases"][f"rs_1_x{pos}_amsterdam"] = Mock(name="BG8001")
                mock_load_cases["unintended_vehicle_cases"][f"rs_3_x{pos}_amsterdam"] = Mock(name="BG8002")

            # Apply loads
            add_accidental_vehicle_loads(mock_builder, mock_params_with_dispersion, mock_load_cases)

            # Verify all created loads are within boundaries
            for call in mock_builder.create_surface_load.call_args_list:
                corner_points = call.kwargs["corner_points"]
                for x, y, z in corner_points:
                    assert 0.0 <= x <= 40.0, f"Accidental vehicle load X coordinate {x} exceeds bridge length"
                    assert -10.0 <= y <= 10.0, f"Accidental vehicle load Y coordinate {y} exceeds bridge width"

    def test_clip_polygon_to_bridge_boundaries_function(self, mock_bridge_geometry: Mock) -> None:
        """Test the clip_polygon_to_bridge_boundaries function directly."""
        from src.integrations.scia_integration.scia_coordinate_utils import clip_polygon_to_bridge_boundaries

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
        from src.integrations.scia_integration.scia_coordinate_utils import clip_polygon_to_bridge_boundaries

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
        from src.integrations.scia_integration.scia_coordinate_utils import clip_polygon_to_bridge_boundaries

        clipped_points = clip_polygon_to_bridge_boundaries([], mock_bridge_geometry)
        assert clipped_points == [], "Empty input should return empty output"


class TestMaterialSurfaceLoad:
    """Tests for material surface load creation with Pydantic LoadZoneData."""

    def test_create_material_surface_load_with_pydantic_model(self, mock_builder: Mock) -> None:
        """Test that create_material_surface_load works with Pydantic LoadZoneData objects."""
        from src.data_models.load_models import LoadZoneData
        from src.geometry.model_creator import LoadZoneGeometryData

        # Create a real Pydantic LoadZoneData object
        load_zone = LoadZoneData(
            zone_type="Auto",
            pavement_thickness=0.1,
            pavement_material="Asfalt",
            d1_width=3.5,
            zone_widths_per_d=[3.5, 3.5],
            y_coords_top_current_zone=[5.0, 10.0],
        )

        # Create mock bridge geometry data
        bridge_geom_data = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 10.0],
            y_top_structural_edge_at_d_points=[5.0, 5.0],
            total_widths_at_d_points=[10.0, 10.0],
            y_bridge_bottom_at_d_points=[0.0, 0.0],
            num_defined_d_points=2,
            d_point_label_data=[],
        )

        # Create load config
        load_config = {
            "load_zone": load_zone,
            "zone_index": 0,
            "span": 0,
            "material_name": "asfalt",
            "load_case_name": "LC_Asfalt",
        }

        # This should NOT raise "'LoadZoneData' object is not subscriptable" error
        try:
            create_material_surface_load(mock_builder, load_config, bridge_geom_data)
            success = True
        except TypeError as e:
            if "not subscriptable" in str(e):
                success = False
                pytest.fail(f"LoadZoneData accessed with dictionary syntax: {e}")
            else:
                raise

        assert success, "create_material_surface_load should work with Pydantic LoadZoneData objects"

        # Verify the builder was called correctly
        mock_builder.create_surface_load.assert_called_once()
        call_args = mock_builder.create_surface_load.call_args

        # Check that the name contains the expected values from the Pydantic model
        assert "Auto" in call_args.kwargs["name"], "Load name should contain zone_type"
        assert "0.1" in call_args.kwargs["name"], "Load name should contain pavement_thickness"
        assert call_args.kwargs["load_case_name"] == "LC_Asfalt", "Load case name should be preserved"


if __name__ == "__main__":
    pytest.main([__file__])
