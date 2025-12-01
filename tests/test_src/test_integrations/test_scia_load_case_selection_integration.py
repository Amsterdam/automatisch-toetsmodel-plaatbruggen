"""
Integration tests for SCIA load case selection functionality.

These tests verify that the load case selection table in the parametrization
actually controls which load cases are generated in the SCIA model.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.load_system.scia_load_cases import create_all_load_cases


class TestLoadCaseSelectionIntegration:
    """Integration tests for load case selection functionality."""

    def test_load_case_selection_disables_generation(self) -> None:
        """Test that disabled load types in the selection table are not generated."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with selective load case selection
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": False, "load_type": "Permanent", "load_case_count": 5},  # Disabled
            {"include": True, "load_type": "Temperatuur", "load_case_count": 4},
            {"include": False, "load_type": "UDL", "load_case_count": "dynamisch"},  # Disabled
            {"include": True, "load_type": "Voetgangers", "load_case_count": 1},
            {"include": False, "load_type": "Dienstvoertuig", "load_case_count": "dynamisch"},  # Disabled
            {"include": False, "load_type": "Onbedoeld voertuig", "load_case_count": "dynamisch"},  # Disabled
            {"include": False, "load_type": "TS", "load_case_count": "dynamisch"},  # Disabled
            {"include": False, "load_type": "Tram", "load_case_count": "dynamisch"},  # Disabled
        ]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify only enabled load types were called
            mock_self_weight.assert_called_once_with(mock_builder)  # Enabled
            mock_dead_loads.assert_not_called()  # Disabled
            mock_temperature.assert_called_once_with(mock_builder)  # Enabled
            mock_udl.assert_not_called()  # Disabled
            mock_pedestrian.assert_called_once_with(mock_builder)  # Enabled
            mock_service.assert_not_called()  # Disabled
            mock_unintended.assert_not_called()  # Disabled
            mock_tandem.assert_not_called()  # Disabled
            mock_tram_track.assert_not_called()  # Disabled (TS is disabled)

            # Verify result only contains enabled load types
            expected_keys = [
                "self_weight",
                "temperature_cases",
                "pedestrian",
            ]
            assert list(result.keys()) == expected_keys

    def test_load_case_selection_enables_all_generation(self) -> None:
        """Test that all load types are generated when all are enabled."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with all load types enabled
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": True, "load_type": "Permanent", "load_case_count": 5},
            {"include": True, "load_type": "Temperatuur", "load_case_count": 4},
            {"include": True, "load_type": "UDL", "load_case_count": "dynamisch"},
            {"include": True, "load_type": "Voetgangers", "load_case_count": 1},
            {"include": True, "load_type": "Dienstvoertuig", "load_case_count": "dynamisch"},
            {"include": True, "load_type": "Onbedoeld voertuig", "load_case_count": "dynamisch"},
            {"include": True, "load_type": "TS", "load_case_count": "dynamisch"},
            {"include": True, "load_type": "Tram", "load_case_count": "dynamisch"},
        ]
        # Set criteria for tram loads to be enabled
        params.berekeningsniveau = "Werkelijke wegindeling"
        params.load_zones_data_array = [{"zone_type": "Tram", "d1_width": 1.435}]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify all load types were called
            mock_self_weight.assert_called_once_with(mock_builder)
            mock_dead_loads.assert_called_once_with(mock_builder)
            mock_temperature.assert_called_once_with(mock_builder)
            mock_udl.assert_called_once_with(mock_builder, params)
            mock_pedestrian.assert_called_once_with(mock_builder)
            mock_service.assert_called_once_with(mock_builder, params)
            mock_unintended.assert_called_once_with(mock_builder, params)
            mock_tandem.assert_called_once_with(mock_builder, params)
            mock_tram_track.assert_called_once_with(mock_builder, params)

            # Verify result contains all load types
            expected_keys = [
                "self_weight",
                "dead_load_cases",
                "temperature_cases",
                "udl_main_cases",
                "udl_other_cases",
                "udl_rest_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_rs1_cases",
                "tandem_rs2_cases",
                "tandem_rs3_cases",
                "tram_track_tandem_cases",
            ]
            assert list(result.keys()) == expected_keys

    def test_load_case_selection_mixed_enabled_disabled(self) -> None:
        """Test mixed enabled/disabled load types."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with mixed selection
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": True, "load_type": "Permanent", "load_case_count": 5},
            {"include": False, "load_type": "Temperatuur", "load_case_count": 4},  # Disabled
            {"include": True, "load_type": "UDL", "load_case_count": "dynamisch"},
            {"include": False, "load_type": "Voetgangers", "load_case_count": 1},  # Disabled
            {"include": True, "load_type": "Dienstvoertuig", "load_case_count": "dynamisch"},
            {"include": False, "load_type": "Onbedoeld voertuig", "load_case_count": "dynamisch"},  # Disabled
            {"include": True, "load_type": "TS", "load_case_count": "dynamisch"},
            {"include": True, "load_type": "Tram", "load_case_count": "dynamisch"},
        ]
        # Set criteria for tram loads to be enabled
        params.berekeningsniveau = "Werkelijke wegindeling onderliggend wegennet"
        params.load_zones_data_array = [{"zone_type": "Tram", "d1_width": 1.435}]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify only enabled load types were called
            mock_self_weight.assert_called_once_with(mock_builder)  # Enabled
            mock_dead_loads.assert_called_once_with(mock_builder)  # Enabled
            mock_temperature.assert_not_called()  # Disabled
            mock_udl.assert_called_once_with(mock_builder, params)  # Enabled
            mock_pedestrian.assert_not_called()  # Disabled
            mock_service.assert_called_once_with(mock_builder, params)  # Enabled
            mock_unintended.assert_not_called()  # Disabled
            mock_tandem.assert_called_once_with(mock_builder, params)  # Enabled
            mock_tram_track.assert_called_once_with(mock_builder, params)  # Enabled

            # Verify result only contains enabled load types
            expected_keys = [
                "self_weight",
                "dead_load_cases",
                "udl_main_cases",
                "udl_other_cases",
                "udl_rest_cases",
                "service_vehicle_cases",
                "tandem_rs1_cases",
                "tandem_rs2_cases",
                "tandem_rs3_cases",
                "tram_track_tandem_cases",
            ]
            assert list(result.keys()) == expected_keys

    def test_load_case_selection_missing_table_defaults_to_all_enabled(self) -> None:
        """Test that missing selection table defaults to all enabled, but Tram is gated."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params without load_case_selection_table
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        # Don't set load_case_selection_table attribute
        # Don't set berekeningsniveau or load_zones_data_array (Tram should be blocked)

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify all load types were called (default behavior)
            # Note: Tram is NOT called because gating criteria are not met
            mock_self_weight.assert_called_once_with(mock_builder)
            mock_dead_loads.assert_called_once_with(mock_builder)
            mock_temperature.assert_called_once_with(mock_builder)
            mock_udl.assert_called_once_with(mock_builder, params)
            mock_pedestrian.assert_called_once_with(mock_builder)
            mock_service.assert_called_once_with(mock_builder, params)
            mock_unintended.assert_called_once_with(mock_builder, params)
            mock_tandem.assert_called_once_with(mock_builder, params)
            mock_tram_track.assert_not_called()  # Tram blocked by gating logic

            # Verify result contains all load types except tram
            expected_keys = [
                "self_weight",
                "dead_load_cases",
                "temperature_cases",
                "udl_main_cases",
                "udl_other_cases",
                "udl_rest_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_rs1_cases",
                "tandem_rs2_cases",
                "tandem_rs3_cases",
            ]
            assert list(result.keys()) == expected_keys

    def test_load_case_selection_empty_table_defaults_to_all_enabled(self) -> None:
        """Test that empty selection table defaults to all enabled, but Tram is gated."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with empty load_case_selection_table
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = []
        # Don't set berekeningsniveau or load_zones_data_array (Tram should be blocked)

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify all load types were called (default behavior)
            # Note: Tram is NOT called because gating criteria are not met
            mock_self_weight.assert_called_once_with(mock_builder)
            mock_dead_loads.assert_called_once_with(mock_builder)
            mock_temperature.assert_called_once_with(mock_builder)
            mock_udl.assert_called_once_with(mock_builder, params)
            mock_pedestrian.assert_called_once_with(mock_builder)
            mock_service.assert_called_once_with(mock_builder, params)
            mock_unintended.assert_called_once_with(mock_builder, params)
            mock_tandem.assert_called_once_with(mock_builder, params)
            mock_tram_track.assert_not_called()  # Tram blocked by gating logic

            # Verify result contains all load types except tram
            expected_keys = [
                "self_weight",
                "dead_load_cases",
                "temperature_cases",
                "udl_main_cases",
                "udl_other_cases",
                "udl_rest_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_rs1_cases",
                "tandem_rs2_cases",
                "tandem_rs3_cases",
            ]
            assert list(result.keys()) == expected_keys

    def test_load_case_selection_invalid_load_type_ignored(self) -> None:
        """Test that invalid load types in the table are ignored."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with some invalid load types
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": True, "load_type": "Invalid Load Type", "load_case_count": 5},  # Invalid
            {"include": True, "load_type": "Temperatuur", "load_case_count": 4},
            {"include": False, "load_type": "Another Invalid Type", "load_case_count": "dynamisch"},  # Invalid
        ]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify only valid enabled load types were called
            mock_self_weight.assert_called_once_with(mock_builder)  # Valid and enabled
            mock_dead_loads.assert_called_once_with(mock_builder)  # Valid but not in table (defaults to enabled)
            mock_temperature.assert_called_once_with(mock_builder)  # Valid and enabled
            mock_udl.assert_called_once_with(mock_builder, params)  # Valid but not in table (defaults to enabled)
            mock_pedestrian.assert_called_once_with(mock_builder)  # Valid but not in table (defaults to enabled)
            mock_service.assert_called_once_with(mock_builder, params)  # Valid but not in table (defaults to enabled)
            mock_unintended.assert_called_once_with(mock_builder, params)  # Valid but not in table (defaults to enabled)
            mock_tandem.assert_called_once_with(mock_builder, params)  # Valid but not in table (defaults to enabled)
            mock_tram_track.assert_not_called()  # Valid but not in table (blocked by gating logic)

            # Verify result contains all load types except tram (invalid ones are ignored, valid ones default to enabled except Tram)
            expected_keys = [
                "self_weight",
                "dead_load_cases",
                "temperature_cases",
                "udl_main_cases",
                "udl_other_cases",
                "udl_rest_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_rs1_cases",
                "tandem_rs2_cases",
                "tandem_rs3_cases",
            ]
            expected_keys = [
                "self_weight",
                "dead_load_cases",
                "temperature_cases",
                "udl_main_cases",
                "udl_other_cases",
                "udl_rest_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_rs1_cases",
                "tandem_rs2_cases",
                "tandem_rs3_cases",
            ]
            assert list(result.keys()) == expected_keys

    def test_tram_load_case_blocked_when_criteria_not_met(self) -> None:
        """Test that tram loads are blocked when criteria are not met, even if checked."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with tram checked but criteria not met
        params = Mock()
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = [
            {"include": True, "load_type": "Tram", "load_case_count": 10},  # Checked but should be blocked
        ]
        # Set calculation level to "Theoretische wegindeling" (not one of the three required)
        params.berekeningsniveau = "Theoretische wegindeling"
        # No tram zones defined
        params.load_zones_data_array = []

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as _mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as _mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as _mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as _mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as _mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as _mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as _mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as _mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify tram loads were NOT called even though checked
            mock_tram_track.assert_not_called()

            # Verify result does not contain tram loads
            assert "tram_track_tandem_cases" not in result

    def test_tram_load_case_allowed_when_criteria_met(self) -> None:
        """Test that tram loads are allowed when all criteria are met."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with tram checked and criteria met
        params = Mock()
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = [
            {"include": True, "load_type": "Tram", "load_case_count": 10},
        ]
        # Set calculation level to one of the three "Werkelijke wegindeling" options
        params.berekeningsniveau = "Werkelijke wegindeling"
        # Define at least one tram zone
        params.load_zones_data_array = [{"zone_type": "Tram", "d1_width": 1.435}]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as _mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as _mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as _mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as _mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as _mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as _mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as _mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as _mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify tram loads were called
            mock_tram_track.assert_called_once_with(mock_builder, params)

            # Verify result contains tram loads
            assert "tram_track_tandem_cases" in result

    def test_tram_load_case_blocked_when_no_tram_zones(self) -> None:
        """Test that tram loads are blocked when no tram zones are defined."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with correct calculation level but no tram zones
        params = Mock()
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = [
            {"include": True, "load_type": "Tram", "load_case_count": 10},
        ]
        # Set calculation level to one of the three "Werkelijke wegindeling" options
        params.berekeningsniveau = "Werkelijke wegindeling met bebording"
        # No tram zones defined
        params.load_zones_data_array = [{"zone_type": "Auto", "d1_width": 3.0}]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case") as _mock_self_weight,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases") as _mock_dead_loads,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases") as _mock_temperature,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases") as _mock_udl,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case") as _mock_pedestrian,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases") as _mock_service,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases") as _mock_unintended,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases") as _mock_tandem,
            patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify tram loads were NOT called
            mock_tram_track.assert_not_called()

            # Verify result does not contain tram loads
            assert "tram_track_tandem_cases" not in result


if __name__ == "__main__":
    pytest.main([__file__])
