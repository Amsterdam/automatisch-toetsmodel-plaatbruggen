"""
Tests for SCIA loads module.

Tests for load application functions and tandem load integration using a mocked builder.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_builder() -> Mock:
    """Fixture to provide a mocked SciaModelBuilder."""
    return Mock()


@pytest.fixture
def mock_params() -> Mock:
    """Fixture to provide mocked VIKTOR parameters."""
    return Mock()


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
        mock_generate.assert_called_once_with(mock_extract.return_value, mode="theoretical")
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
        def mock_calc_locations_side_effect(x_coord, y_coord, vehicle_length, vehicle_width, wheel_contact_area):
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
            def mock_calc_locations_side_effect(x_coord, y_coord, vehicle_length, vehicle_width, wheel_contact_area):
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

    @patch("src.integrations.scia_integration.scia_loads.add_accidental_vehicle_loads")
    @patch("src.integrations.scia_integration.scia_loads.add_service_vehicle_loads")
    @patch("src.integrations.scia_integration.scia_loads.add_theoretical_tandem_loads")
    @patch("src.integrations.scia_integration.scia_loads.get_bridge_geom_data")
    def test_create_all_loads(
        self,
        mock_get_bridge_geom: Mock,
        mock_add_tandem: Mock,
        mock_add_service: Mock,
        mock_add_accidental: Mock,
        mock_builder: Mock,
        mock_params: Mock,
    ) -> None:
        """Test that `create_all_loads` calls all load functions."""
        from src.integrations.scia_integration.scia_loads import create_all_loads

        # Create a mock load_cases dictionary
        mock_load_cases = {
            "dead_load_cases": {"leuning": Mock(name="BG2004"), "asfalt": Mock(), "uitvulling": Mock(), "ophogingen": Mock()},
            "pedestrian": Mock(name="BG5001"),
            "service_vehicle_cases": {"y_plus_x10.0": Mock(name="BG6001")},
            "unintended_vehicle_cases": {"rs_1_x10.0_forward": Mock(name="BG7001")},
            "udl_traffic_cases": {"rs_1": Mock(name="BG4001"), "rs_2": Mock(name="BG4002"), "rs_3": Mock(name="BG4003")},
        }

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
        mock_bridge_geom = Mock()
        mock_bridge_geom.y_top_structural_edge_at_d_points = [5.0]
        mock_bridge_geom.y_bridge_bottom_at_d_points = [-5.0]
        mock_bridge_geom.x_coords_d_points = [0.0, 25.0]
        mock_get_bridge_geom.return_value = mock_bridge_geom

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


if __name__ == "__main__":
    pytest.main([__file__])
