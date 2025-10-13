"""
Integration tests for SCIA load case selection functionality.

These tests verify that the load case selection table in the parametrization
actually controls which load cases are generated in the SCIA model.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_cases import create_all_load_cases


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
            {"include": False, "load_type": "UDL", "load_case_count": 3},  # Disabled
            {"include": True, "load_type": "Voetgangers", "load_case_count": 1},
            {"include": False, "load_type": "Dienstvoertuig", "load_case_count": 20},  # Disabled
            {"include": False, "load_type": "Onbedoeld voertuig", "load_case_count": 50},  # Disabled
            {"include": False, "load_type": "TS", "load_case_count": 30},  # Disabled
        ]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
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
            {"include": True, "load_type": "UDL", "load_case_count": 3},
            {"include": True, "load_type": "Voetgangers", "load_case_count": 1},
            {"include": True, "load_type": "Dienstvoertuig", "load_case_count": 20},
            {"include": True, "load_type": "Onbedoeld voertuig", "load_case_count": 50},
            {"include": True, "load_type": "TS", "load_case_count": 30},
        ]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify all load types were called
            mock_self_weight.assert_called_once_with(mock_builder)
            mock_dead_loads.assert_called_once_with(mock_builder)
            mock_temperature.assert_called_once_with(mock_builder)
            mock_udl.assert_called_once_with(mock_builder)
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
                "udl_traffic_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_cases",
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
            {"include": True, "load_type": "UDL", "load_case_count": 3},
            {"include": False, "load_type": "Voetgangers", "load_case_count": 1},  # Disabled
            {"include": True, "load_type": "Dienstvoertuig", "load_case_count": 20},
            {"include": False, "load_type": "Onbedoeld voertuig", "load_case_count": 50},  # Disabled
            {"include": True, "load_type": "TS", "load_case_count": 30},
        ]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify only enabled load types were called
            mock_self_weight.assert_called_once_with(mock_builder)  # Enabled
            mock_dead_loads.assert_called_once_with(mock_builder)  # Enabled
            mock_temperature.assert_not_called()  # Disabled
            mock_udl.assert_called_once_with(mock_builder)  # Enabled
            mock_pedestrian.assert_not_called()  # Disabled
            mock_service.assert_called_once_with(mock_builder, params)  # Enabled
            mock_unintended.assert_not_called()  # Disabled
            mock_tandem.assert_called_once_with(mock_builder, params)  # Enabled
            mock_tram_track.assert_called_once_with(mock_builder, params)  # Enabled (part of TS)

            # Verify result only contains enabled load types
            expected_keys = [
                "self_weight",
                "dead_load_cases",
                "udl_traffic_cases",
                "service_vehicle_cases",
                "tandem_cases",
                "tram_track_tandem_cases",
            ]
            assert list(result.keys()) == expected_keys

    def test_load_case_selection_missing_table_defaults_to_all_enabled(self) -> None:
        """Test that missing selection table defaults to all enabled."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params without load_case_selection_table
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        # Don't set load_case_selection_table attribute

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify all load types were called (default behavior)
            mock_self_weight.assert_called_once_with(mock_builder)
            mock_dead_loads.assert_called_once_with(mock_builder)
            mock_temperature.assert_called_once_with(mock_builder)
            mock_udl.assert_called_once_with(mock_builder)
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
                "udl_traffic_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_cases",
                "tram_track_tandem_cases",
            ]
            assert list(result.keys()) == expected_keys

    def test_load_case_selection_empty_table_defaults_to_all_enabled(self) -> None:
        """Test that empty selection table defaults to all enabled."""
        # Create a mock builder
        mock_builder = Mock()

        # Create mock params with empty load_case_selection_table
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        params.load_case_selection_table = []

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify all load types were called (default behavior)
            mock_self_weight.assert_called_once_with(mock_builder)
            mock_dead_loads.assert_called_once_with(mock_builder)
            mock_temperature.assert_called_once_with(mock_builder)
            mock_udl.assert_called_once_with(mock_builder)
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
                "udl_traffic_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_cases",
                "tram_track_tandem_cases",
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
            {"include": False, "load_type": "Another Invalid Type", "load_case_count": 3},  # Invalid
        ]

        # Mock all the individual load case creation functions
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            # Execute the function
            result = create_all_load_cases(mock_builder, params)

            # Verify only valid enabled load types were called
            mock_self_weight.assert_called_once_with(mock_builder)  # Valid and enabled
            mock_dead_loads.assert_called_once_with(mock_builder)  # Valid but not in table (defaults to enabled)
            mock_temperature.assert_called_once_with(mock_builder)  # Valid and enabled
            mock_udl.assert_called_once_with(mock_builder)  # Valid but not in table (defaults to enabled)
            mock_pedestrian.assert_called_once_with(mock_builder)  # Valid but not in table (defaults to enabled)
            mock_service.assert_called_once_with(mock_builder, params)  # Valid but not in table (defaults to enabled)
            mock_unintended.assert_called_once_with(mock_builder, params)  # Valid but not in table (defaults to enabled)
            mock_tandem.assert_called_once_with(mock_builder, params)  # Valid but not in table (defaults to enabled)
            mock_tram_track.assert_called_once_with(mock_builder, params)  # Valid but not in table (defaults to enabled)

            # Verify result contains all load types (invalid ones are ignored, valid ones default to enabled)
            expected_keys = [
                "self_weight",
                "dead_load_cases",
                "temperature_cases",
                "udl_traffic_cases",
                "pedestrian",
                "service_vehicle_cases",
                "unintended_vehicle_cases",
                "tandem_cases",
                "tram_track_tandem_cases",
            ]
            assert list(result.keys()) == expected_keys


if __name__ == "__main__":
    pytest.main([__file__])
