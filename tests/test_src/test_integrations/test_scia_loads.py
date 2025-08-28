"""
Tests for SCIA loads module.

Tests for load application functions and tandem load integration using a mocked builder.
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import Mock, patch

import pytest

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


class TestTheoreticalTandemLoads:
    """Test theoretical tandem load application."""

    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    @patch("src.integrations.scia_integration.scia_loads.generate_tandem_loads_for_bridge")
    @patch("src.integrations.scia_integration.scia_loads.convert_tandem_data_to_scia_format")
    def test_add_theoretical_tandem_loads_success(
        self, mock_convert: Mock, mock_generate: Mock, mock_extract: Mock, mock_builder: Mock, mock_params: Mock
    ) -> None:
        """Test successful theoretical tandem load addition."""
        from src.integrations.scia_integration.scia_loads import add_theoretical_tandem_loads

        # Setup mocks
        mock_extract.return_value = {"width_bridgedeck": 30.0, "length_bridgedeck": 100.0}
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

        # Verify workflow
        mock_extract.assert_called_once_with(mock_params)
        mock_generate.assert_called_once_with(mock_params, mock_extract.return_value, mode="theoretical")
        mock_convert.assert_called_once_with(mock_generate.return_value)

        # Verify builder calls
        mock_builder.create_surface_load.assert_called_once_with(
            name="LC1_Wheel_1",
            load_case_name="LC1",
            corner_points=[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
            load_value=-150.0,  # Negative for downward force
        )

    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    @patch("src.integrations.scia_integration.scia_loads.generate_tandem_loads_for_bridge")
    @patch("src.integrations.scia_integration.scia_loads.convert_tandem_data_to_scia_format")
    def test_add_theoretical_tandem_loads_multiple_wheels(
        self, mock_convert: Mock, mock_generate: Mock, mock_extract: Mock, mock_builder: Mock, mock_params: Mock
    ) -> None:
        """Test theoretical tandem loads with multiple wheels."""
        from src.integrations.scia_integration.scia_loads import add_theoretical_tandem_loads

        # Setup mocks for multiple wheels
        mock_extract.return_value = {"width_bridgedeck": 30.0, "length_bridgedeck": 100.0}
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

    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    @patch("src.integrations.scia_integration.scia_loads.tandem_system_sequencer")
    @patch("src.integrations.scia_integration.scia_loads.get_bridge_geom_data")
    @patch("src.integrations.scia_integration.scia_loads.calc_vehicle_load_locations")
    def test_add_service_vehicle_loads_success(  # noqa: PLR0913
        self, mock_calc_vehicle: Mock, mock_bridge_geom: Mock, mock_sequencer: Mock, mock_extract: Mock, mock_builder: Mock, mock_params: Mock
    ) -> None:
        """Test successful service vehicle load addition."""
        from src.integrations.scia_integration.scia_loads import add_service_vehicle_loads

        # Setup mocks
        mock_extract.return_value = {"length_bridgedeck": 50.0, "thickness_bridgedeck": 0.5}
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
        mock_sequencer.assert_called_once_with(50.0, 0.5)
        mock_bridge_geom.assert_called_once_with(mock_params)

        # Should create loads for 3 positions × 2 edges × 4 wheels = 24 surface loads
        assert mock_builder.create_surface_load.call_count == 24

    @patch("src.integrations.scia_integration.scia_loads.get_bridge_geom_data")
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

    @patch("src.integrations.scia_integration.scia_loads.calc_vehicle_load_locations")
    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    @patch("src.integrations.scia_integration.scia_loads.tandem_system_sequencer")
    @patch("src.integrations.scia_integration.scia_loads.get_bridge_geom_data")
    def test_add_accidental_vehicle_loads_bidirectional(  # noqa: PLR0913
        self, mock_bridge_geom: Mock, mock_sequencer: Mock, mock_extract: Mock, mock_calc_locations: Mock, mock_builder: Mock, mock_params: Mock
    ) -> None:
        """Test accidental vehicle loads with bidirectional placement."""
        from src.integrations.scia_integration.scia_loads import add_accidental_vehicle_loads

        # Setup mocks
        mock_extract.return_value = {"length_bridgedeck": 50.0, "thickness_bridgedeck": 0.5}
        mock_sequencer.return_value = [2.5, 25.0]  # 2 positions for easier testing

        mock_bridge_geom_data = Mock()
        mock_bridge_geom_data.y_top_structural_edge_at_d_points = [5.0, 5.0]
        mock_bridge_geom_data.y_bridge_bottom_at_d_points = [-5.0, -5.0]
        mock_bridge_geom.return_value = mock_bridge_geom_data

        # Mock calc_vehicle_load_locations to return wheel corner coordinates
        # The function should return coordinates relative to the x_coord parameter
        def mock_calc_locations_side_effect(**kwargs) -> dict[str, list[tuple[float, float, float]]]:
            """Mock function to return wheel corner coordinates."""
            x_coord = kwargs["x_coord"]
            return {
                "top_left_wheel_corners": [(x_coord, 0.0, 0.0), (x_coord + 0.2, 0.0, 0.0), (x_coord + 0.2, 0.2, 0.0), (x_coord, 0.2, 0.0)],
                "bottom_left_wheel_corners": [(x_coord, -1.3, 0.0), (x_coord + 0.2, -1.3, 0.0), (x_coord + 0.2, -1.1, 0.0), (x_coord, -1.1, 0.0)],
            }

        mock_calc_locations.side_effect = mock_calc_locations_side_effect

        # Create mock load cases for all combinations
        mock_load_cases = {
            "unintended_vehicle_cases": {
                "rs_1_x2.5_forward": Mock(name="BG7001"),
                "rs_1_x25.0_forward": Mock(name="BG7002"),
                "rs_1_x2.5_reverse": Mock(name="BG7003"),
                "rs_1_x25.0_reverse": Mock(name="BG7004"),
                "rs_3_x2.5_forward": Mock(name="BG7005"),
                "rs_3_x25.0_forward": Mock(name="BG7006"),
                "rs_3_x2.5_reverse": Mock(name="BG7007"),
                "rs_3_x25.0_reverse": Mock(name="BG7008"),
            }
        }

        add_accidental_vehicle_loads(mock_builder, mock_params, mock_load_cases)

        # Verify workflow
        mock_extract.assert_called_once_with(mock_params)
        mock_sequencer.assert_called_once_with(50.0, 0.5)
        mock_bridge_geom.assert_called_once_with(mock_params)

        # Verify calc_vehicle_load_locations was called for both front and rear axles
        # 2 positions × 2 edges × 2 directions × 2 axles = 16 total calls
        assert mock_calc_locations.call_count == 16

        # Should create loads for 2 positions × 2 edges × 2 directions × 4 wheels = 32 surface loads
        assert mock_builder.create_surface_load.call_count == 32

        # Check that individual wheel loads are created with correct values
        calls = mock_builder.create_surface_load.call_args_list
        front_wheel_calls = [call for call in calls if "front_left" in call.kwargs["name"] or "front_right" in call.kwargs["name"]]
        rear_wheel_calls = [call for call in calls if "rear_left" in call.kwargs["name"] or "rear_right" in call.kwargs["name"]]

        assert len(front_wheel_calls) == 16  # 40 kN loads (2 wheels per axle)
        assert len(rear_wheel_calls) == 16  # 20 kN loads (2 wheels per axle)

        # Verify front wheel loads are calculated pressure values (40 kN / 0.04 m² = 1,000,000 N/m²)
        for call in front_wheel_calls:
            assert abs(call.kwargs["load_value"] - (-1000000)) < 1  # Allow small floating-point precision error

        # Verify rear wheel loads are calculated pressure values (20 kN / 0.04 m² = 500,000 N/m²)
        for call in rear_wheel_calls:
            assert abs(call.kwargs["load_value"] - (-500000)) < 1  # Allow small floating-point precision error

    def test_add_accidental_vehicle_loads_direction_logic(self, mock_builder: Mock, mock_params: Mock) -> None:
        """Test that forward and reverse directions place axles correctly."""
        from src.integrations.scia_integration.scia_loads import add_accidental_vehicle_loads

        with (
            patch("src.integrations.scia_integration.scia_loads.calc_vehicle_load_locations") as mock_calc_locations,
            patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge") as mock_extract,
            patch("src.integrations.scia_integration.scia_loads.tandem_system_sequencer") as mock_sequencer,
            patch("src.integrations.scia_integration.scia_loads.get_bridge_geom_data") as mock_bridge_geom,
        ):
            # Setup mocks
            mock_extract.return_value = {"length_bridgedeck": 50.0, "thickness_bridgedeck": 0.5}
            mock_sequencer.return_value = [10.0]  # Single position

            mock_bridge_geom_data = Mock()
            mock_bridge_geom_data.y_top_structural_edge_at_d_points = [5.0]
            mock_bridge_geom_data.y_bridge_bottom_at_d_points = [-5.0]
            mock_bridge_geom.return_value = mock_bridge_geom_data

            # Mock calc_vehicle_load_locations to return wheel corner coordinates
            # The function should return coordinates relative to the x_coord parameter
            def mock_calc_locations_side_effect(**kwargs) -> dict[str, list[tuple[float, float, float]]]:
                """Mock function to return wheel corner coordinates."""
                x_coord = kwargs["x_coord"]
                return {
                    "top_left_wheel_corners": [(x_coord, 0.0, 0.0), (x_coord + 0.2, 0.0, 0.0), (x_coord + 0.2, 0.2, 0.0), (x_coord, 0.2, 0.0)],
                    "bottom_left_wheel_corners": [(x_coord, -1.3, 0.0), (x_coord + 0.2, -1.3, 0.0), (x_coord + 0.2, -1.1, 0.0), (x_coord, -1.1, 0.0)],
                }

            mock_calc_locations.side_effect = mock_calc_locations_side_effect

            # Create mock load cases
            mock_load_cases = {
                "unintended_vehicle_cases": {
                    "rs_1_x10.0_forward": Mock(name="BG7001"),
                    "rs_1_x10.0_reverse": Mock(name="BG7002"),
                }
            }

            add_accidental_vehicle_loads(mock_builder, mock_params, mock_load_cases)

            # Check axle positioning for forward and reverse
            calls = mock_builder.create_surface_load.call_args_list

            # Forward direction: front wheels at x=10.0, rear wheels at x=11.2
            forward_front = next(call for call in calls if "forward_front_left" in call.kwargs["name"])
            forward_rear = next(call for call in calls if "forward_rear_left" in call.kwargs["name"])

            assert forward_front.kwargs["corner_points"][0][0] == 10.0  # Front wheel X position
            assert forward_rear.kwargs["corner_points"][0][0] == 11.2  # Rear wheel X position

            # Reverse direction: front wheels at x=11.2, rear wheels at x=10.0
            reverse_front = next(call for call in calls if "reverse_front_left" in call.kwargs["name"])
            reverse_rear = next(call for call in calls if "reverse_rear_left" in call.kwargs["name"])

            assert reverse_front.kwargs["corner_points"][0][0] == 11.2  # Front wheel X position
            assert reverse_rear.kwargs["corner_points"][0][0] == 10.0  # Rear wheel X position


class TestAllLoads:
    """Test the main orchestrator for creating all loads."""

    @pytest.fixture
    def mock_patches(self) -> Generator[tuple[Mock, Mock, Mock, Mock], None, None]:
        """Provide mock patches for the test."""
        with (
            patch("src.integrations.scia_integration.scia_loads.add_accidental_vehicle_loads") as mock_add_accidental,
            patch("src.integrations.scia_integration.scia_loads.add_service_vehicle_loads") as mock_add_service,
            patch("src.integrations.scia_integration.scia_loads.add_theoretical_tandem_loads") as mock_add_tandem,
            patch("src.integrations.scia_integration.scia_loads.get_bridge_geom_data") as mock_get_bridge_geom,
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
            "unintended_vehicle_cases": {"rs_1_x10.0_forward": Mock(name="BG7001")},
            "udl_traffic_cases": {"rs_1": Mock(name="BG4001"), "rs_2": Mock(name="BG4002"), "rs_3": Mock(name="BG4003")},
        }

        # Configure mock params to handle dictionary-style access
        mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
        mock_params.__contains__ = Mock(return_value=True)

        # Mock the bridge_segments_array to be iterable with required attributes
        mock_segment1 = Mock()
        mock_segment1.l = 10.0
        mock_segment1.bz1 = 2.0
        mock_segment1.bz2 = 3.0
        mock_segment1.bz3 = 2.0
        mock_segment2 = Mock()
        mock_segment2.l = 15.0
        mock_segment2.bz1 = 2.0
        mock_segment2.bz2 = 3.0
        mock_segment2.bz3 = 2.0
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

    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    def test_tandem_load_error_propagation(self, mock_extract: Mock, mock_builder: Mock, mock_params: Mock) -> None:
        """Test error propagation in tandem load application."""
        from src.integrations.scia_integration.scia_loads import add_theoretical_tandem_loads

        # Simulate error in parameter extraction
        mock_extract.side_effect = ValueError("Parameter extraction failed")

        # Create a mock load_cases dictionary
        mock_load_cases: dict[str, Any] = {}
        with pytest.raises(ValueError, match="Parameter extraction failed"):
            add_theoretical_tandem_loads(mock_builder, mock_params, mock_load_cases)


class TestUniformlyDistributedLoads:
    """Test generation and application of uniformly distributed loads (UDL)."""

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

    @patch("src.integrations.scia_integration.scia_loads_helper.get_psi_nen_8701")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_alpha_trend_nen_8701")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_alpha_q_nen_en_1991_2")
    def test_create_real_udl_traffic_loads_basic_case(
        self, mock_alpha_q: Mock, mock_alpha_trend: Mock, mock_psi: Mock, mock_params: Mock
    ) -> None:
        """Test creation of UDL traffic loads based on actual road configuration."""
        from src.integrations.scia_integration.scia_loads_helper import create_real_udl_traffic_loads

        # Test case parameters
        length_bridgedeck = 20.0  # 20m long bridge
        udl_value = 9000.0  # 9 kN/m²

        # Configure mock params
        mock_params.reference_period = 50  # years
        mock_params.load_zones_data_array = [
            {
                "zone_type": "Auto",
                "d1_width": 10.5,
                "zone_widths_per_d": [10.5, 10.5, 10.5, 10.5],
                "y_coords_top_current_zone": [6.5, 6.5, 6.5, 6.5]
            }
        ]
        mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
        mock_params.__contains__ = Mock(return_value=True)

        # Mock the load factors
        mock_psi.return_value = 1.0  # Example psi factor
        mock_alpha_trend.return_value = 1.1  # Example alpha trend factor
        mock_alpha_q.return_value = [1.0, 0.77, 0.53, 0.0]  # Standard factors for lanes 1-4

        # Execute the function
        result = create_real_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=length_bridgedeck,
            udl_value=udl_value,
        )

        # Verify basic structure of results
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "UDL_Real" in result, "Result should contain UDL_Real key"
        
        udl_data = result["UDL_Real"]
        
        # Check structure of UDL_Real
        assert all(key in udl_data for key in ["load_name", "load_value", "load_direction", "geometry"]), \
            "UDL_Real should have load_name, load_value, load_direction, and geometry"
        
        # Check load direction
        assert udl_data["load_direction"] == "z", "Load direction should be vertical (z)"
        
        # Check geometry properties
        geometry = udl_data["geometry"]
        assert isinstance(geometry, list), "Geometry should be a list"
        assert len(geometry) > 0, "Geometry should not be empty"
        
        # Verify each polygon in geometry
        for poly in geometry:
            assert len(poly) == 4, "Each polygon should have 4 corners"
            assert all(len(point) == 3 for point in poly), "Each point should have x, y, z coordinates"
            assert all(point[2] == 0.0 for point in poly), "All z-coordinates should be 0.0"
        
        # Calculate expected load value with factors
        expected_load = udl_value * mock_psi.return_value * mock_alpha_trend.return_value * mock_alpha_q.return_value[0]
        assert abs(udl_data["load_value"] - expected_load) < 0.1, f"Load value should be {expected_load}"

    def test_create_real_udl_traffic_loads_edge_cases(self, mock_params: Mock) -> None:
        """Test real UDL traffic loads creation with edge cases."""
        from src.integrations.scia_integration.scia_loads_helper import create_real_udl_traffic_loads

        # Configure mock params
        mock_params.__getitem__ = Mock(side_effect=lambda x: "NEN-EN 1991-2" if x == "design_code" else None)
        mock_params.__contains__ = Mock(return_value=True)
        mock_params.reference_period = 50

        # Test with minimal road width
        mock_params.load_zones_data_array = [
            {
                "zone_type": "Auto",
                "d1_width": 3.0,  # Minimal width for one lane
                "zone_widths_per_d": [3.0, 3.0, 3.0, 3.0],
                "y_coords_top_current_zone": [3.0, 3.0, 3.0, 3.0]
            }
        ]
        result_narrow = create_real_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=10.0,
            udl_value=9000.0,
        )
        assert "UDL_Real" in result_narrow
        assert len(result_narrow["UDL_Real"]["geometry"]) > 0, "Should handle minimal width road"

        # Test with no auto zone (should handle gracefully)
        mock_params.load_zones_data_array = [
            {
                "zone_type": "Voetgangers",
                "d1_width": 3.0,
                "zone_widths_per_d": [3.0, 3.0, 3.0, 3.0],
                "y_coords_top_current_zone": [3.0, 3.0, 3.0, 3.0]
            }
        ]
        result_no_auto = create_real_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=10.0,
            udl_value=9000.0,
        )
        assert "UDL_Real" in result_no_auto
        assert len(result_no_auto["UDL_Real"]["geometry"]) == 0, "Should handle no auto zone case"

        # Test with zero load value
        mock_params.load_zones_data_array = [
            {
                "zone_type": "Auto",
                "d1_width": 10.5,
                "zone_widths_per_d": [10.5, 10.5, 10.5, 10.5],
                "y_coords_top_current_zone": [6.5, 6.5, 6.5, 6.5]
            }
        ]
        result_zero_load = create_real_udl_traffic_loads(
            params=mock_params,
            length_bridgedeck=10.0,
            udl_value=0.0,
        )
        assert "UDL_Real" in result_zero_load
        assert result_zero_load["UDL_Real"]["load_value"] == 0.0, "Should handle zero load value"

    @patch("src.integrations.scia_integration.scia_loads_helper.get_load_zones_data_from_params")
    @patch("src.integrations.scia_integration.scia_loads_helper.get_bridge_geom_data")
    @patch("src.integrations.scia_integration.scia_loads_helper.calculate_zone_geometry_properties")
    def test_obtain_y_coordinates_road_basic_case(
        self, mock_calc_geom: Mock, mock_bridge_geom: Mock, mock_load_zones: Mock, mock_params: Mock
    ) -> None:
        """Test obtaining y-coordinates for road section in basic case."""
        from src.integrations.scia_integration.scia_loads_helper import obtain_y_coordinates_road

        # Setup mock bridge geometry data
        mock_bridge_geom_data = Mock()
        mock_bridge_geom.return_value = mock_bridge_geom_data

        # Setup mock load zones data
        mock_load_zones.return_value = [
            {
                "zone_type": "Auto",
                "d1_width": 10.5,
                "y_coords_top_current_zone": [6.5]
            }
        ]
        mock_calc_geom.return_value = mock_load_zones.return_value

        # Execute function
        y_coord, width = obtain_y_coordinates_road(mock_params)

        # Verify results
        assert y_coord == 6.5, "Y-coordinate should match the top of Auto zone"
        assert width == 10.5, "Width should match d1_width of Auto zone"

        # Verify mocks were called correctly
        mock_load_zones.assert_called_once_with(mock_params)
        mock_bridge_geom.assert_called_once_with(mock_params)
        mock_calc_geom.assert_called_once()

    def test_obtain_y_coordinates_road_edge_cases(self, mock_params: Mock) -> None:
        """Test obtaining y-coordinates for road section in edge cases."""
        from src.integrations.scia_integration.scia_loads_helper import obtain_y_coordinates_road

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
            mock_load_zones.return_value = [{"zone_type": "Voetgangers"}]
            mock_calc_geom.return_value = mock_load_zones.return_value
            y_coord, width = obtain_y_coordinates_road(mock_params)
            assert y_coord == 0.0, "Should return 0.0 when no Auto zone"
            assert width == 0.0, "Should return 0.0 when no Auto zone"

            # Test case: Empty y_coords list
            mock_load_zones.return_value = [{"zone_type": "Auto", "y_coords_top_current_zone": []}]
            mock_calc_geom.return_value = mock_load_zones.return_value
            y_coord, width = obtain_y_coordinates_road(mock_params)
            assert y_coord == 0.0, "Should return 0.0 when y_coords is empty"

            # Test case: Invalid d1_width (non-numeric)
            mock_load_zones.return_value = [
                {
                    "zone_type": "Auto",
                    "d1_width": "invalid",
                    "y_coords_top_current_zone": [5.0]
                }
            ]
            mock_calc_geom.return_value = mock_load_zones.return_value
            y_coord, width = obtain_y_coordinates_road(mock_params)
            assert width == 0.0, "Should return 0.0 when d1_width is invalid"

    def test_generate_real_lane_positions_bg8000(self, mock_params: Mock) -> None:
        """Test generation of lane positions for BG8000 load group."""
        from src.integrations.scia_integration.scia_loads_helper import generate_real_lane_positions_bg8000

        with (
            patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_road") as mock_obtain_coords
        ):
            # Test case: Normal road width with multiple lanes
            mock_obtain_coords.return_value = (10.0, 9.0)  # y_top = 10.0, width = 9.0
            lane_positions = generate_real_lane_positions_bg8000(mock_params)
            assert len(lane_positions) == 3, "Should have 3 lanes for 9.0m width"
            # Verify lane centers are correctly positioned from bottom up
            assert lane_positions[0] == pytest.approx(1.5), "First lane center should be at y=1.5"
            assert lane_positions[1] == pytest.approx(4.5), "Second lane center should be at y=4.5"
            assert lane_positions[2] == pytest.approx(7.5), "Third lane center should be at y=7.5"

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

        with (
            patch("src.integrations.scia_integration.scia_loads_helper.obtain_y_coordinates_road") as mock_obtain_coords
        ):
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


if __name__ == "__main__":
    pytest.main([__file__])
