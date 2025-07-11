"""
Tests for SCIA loads module.

Tests for load application functions and tandem load integration.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_combinations import (
    create_standard_load_combinations,
)
from src.integrations.scia_integration.scia_loads import (
    add_actual_tandem_loads,
    add_theoretical_tandem_loads,
)


class TestTheoreticalTandemLoads:
    """Test theoretical tandem load application."""

    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    @patch("src.integrations.scia_integration.scia_loads.generate_tandem_loads_for_bridge")
    @patch("src.integrations.scia_integration.scia_loads.convert_tandem_data_to_scia_format")
    @patch("src.integrations.scia_integration.scia_loads.create_tandem_load_case")
    @patch("src.integrations.scia_integration.scia_loads.create_patch_surface_load")
    def test_add_theoretical_tandem_loads_success(
        self, mock_patch_load: Mock, mock_create_case: Mock, mock_convert: Mock, mock_generate: Mock, mock_extract: Mock
    ) -> None:
        """Test successful theoretical tandem load addition."""
        mock_params = Mock()
        mock_traffic_group = Mock()
        mock_traffic_group.name = "TrafficGroup"
        mock_load_case = Mock()

        # Setup mocks
        mock_bridge_params = {"width_bridgedeck": 30.0, "length_bridgedeck": 100.0}
        mock_extract.return_value = mock_bridge_params

        mock_raw_data = [{"tandem_id": "TH6001", "wheels": []}]
        mock_generate.return_value = mock_raw_data

        mock_scia_data = [{"load_case": "TH6001", "patch_loads": [{"corners": [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], "load_value": 150.0}]}]
        mock_convert.return_value = mock_scia_data
        mock_create_case.return_value = mock_load_case

        result = add_theoretical_tandem_loads(mock_params, mock_traffic_group.name)

        # Verify workflow
        mock_extract.assert_called_once_with(mock_params)
        mock_generate.assert_called_once_with(mock_bridge_params, mode="theoretical")
        mock_convert.assert_called_once_with(mock_raw_data)
        mock_create_case.assert_called_once_with(mock_traffic_group.name, "TH6001", "theoretical")
        mock_patch_load.assert_called_once_with(
            "TH6001",
            [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
            -150.0,  # Negative for downward force
            "TH6001_Wheel_1",
        )

        assert "load_case_definitions" in result
        assert "surface_load_definitions" in result

    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    @patch("src.integrations.scia_integration.scia_loads.generate_tandem_loads_for_bridge")
    @patch("src.integrations.scia_integration.scia_loads.convert_tandem_data_to_scia_format")
    @patch("src.integrations.scia_integration.scia_loads.create_tandem_load_case")
    @patch("src.integrations.scia_integration.scia_loads.create_patch_surface_load")
    def test_add_theoretical_tandem_loads_multiple_wheels(
        self, mock_patch_load: Mock, mock_create_case: Mock, mock_convert: Mock, mock_generate: Mock, mock_extract: Mock
    ) -> None:
        """Test theoretical tandem loads with multiple wheels."""
        mock_params = Mock()
        mock_traffic_group = Mock()
        mock_traffic_group.name = "TrafficGroup"
        mock_load_case = Mock()

        # Setup mocks for multiple wheels
        mock_bridge_params = {"width_bridgedeck": 30.0, "length_bridgedeck": 100.0}
        mock_extract.return_value = mock_bridge_params

        mock_raw_data = [
            {
                "tandem_id": "TH6001",
                "wheels": [{"wheel_id": "W1"}, {"wheel_id": "W2"}],
            }
        ]
        mock_generate.return_value = mock_raw_data

        mock_scia_data = [
            {
                "load_case": "TH6001",
                "patch_loads": [
                    {"corners": [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], "load_value": 150.0},
                    {"corners": [(2, 0, 0), (3, 0, 0), (3, 1, 0), (2, 1, 0)], "load_value": 150.0},
                ],
            }
        ]
        mock_convert.return_value = mock_scia_data
        mock_create_case.return_value = mock_load_case

        result = add_theoretical_tandem_loads(mock_params, mock_traffic_group.name)

        # Verify both wheels were processed
        assert mock_patch_load.call_count == 2

        # Check wheel naming
        calls = mock_patch_load.call_args_list
        assert calls[0][0][3] == "TH6001_Wheel_1"
        assert calls[1][0][3] == "TH6001_Wheel_2"

        assert "load_case_definitions" in result


class TestActualTandemLoads:
    """Test actual tandem load application."""

    def test_add_actual_tandem_loads_placeholder(self) -> None:
        """Test actual tandem loads placeholder implementation."""
        mock_model = Mock()
        mock_params = Mock()
        mock_traffic_group = Mock()

        result = add_actual_tandem_loads(mock_model, mock_params, mock_traffic_group)

        # Should return empty list (placeholder)
        assert result == []


class TestStandardLoadCombinations:
    """Test standard load combinations creation."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_basic_uls_combination")
    @patch("src.integrations.scia_integration.scia_load_combinations.create_basic_sls_combination")
    @patch("src.integrations.scia_integration.scia_load_combinations.create_wind_uls_combination")
    def test_create_standard_load_combinations_success(self, mock_wind_combo: Mock, mock_sls_combo: Mock, mock_uls_combo: Mock) -> None:
        """Test successful standard load combinations creation."""
        mock_self_weight_case = "SW"
        mock_wind_case = "WIND"
        mock_tandem_cases = ["TS1", "TS2"]

        mock_uls_result = Mock()
        mock_sls_result = Mock()
        mock_wind_result = Mock()

        mock_uls_combo.return_value = mock_uls_result
        mock_sls_combo.return_value = mock_sls_result
        mock_wind_combo.return_value = mock_wind_result

        result = create_standard_load_combinations(mock_self_weight_case, mock_tandem_cases, mock_wind_case)

        # Verify calls for each tandem case
        assert mock_uls_combo.call_count == 2
        assert mock_sls_combo.call_count == 2
        assert mock_wind_combo.call_count == 2
        assert len(result) == 6


class TestLoadApplicationIntegration:
    """Test load application integration scenarios."""

    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    def test_tandem_parameter_extraction(self, mock_extract: Mock) -> None:
        """Test tandem parameter extraction from bridge."""
        mock_params = Mock()
        mock_bridge_params = {"width_bridgedeck": 30.0, "length_bridgedeck": 100.0}
        mock_extract.return_value = mock_bridge_params

        # This tests the integration with geometry extraction
        from src.integrations.scia_integration.scia_loads import add_theoretical_tandem_loads

        # Mock the rest of the chain
        with (
            patch("src.integrations.scia_integration.scia_loads.generate_tandem_loads_for_bridge") as mock_generate,
            patch("src.integrations.scia_integration.scia_loads.convert_tandem_data_to_scia_format") as mock_convert,
            patch("src.integrations.scia_integration.scia_loads.create_tandem_load_case") as mock_create,
            patch("src.integrations.scia_integration.scia_loads.create_patch_surface_load"),
        ):
            mock_generate.return_value = []
            mock_convert.return_value = []
            mock_create.return_value = Mock()

            mock_traffic_group = "Traffic"
            add_theoretical_tandem_loads(mock_params, mock_traffic_group)

        # Verify parameter extraction was called
        mock_extract.assert_called_once_with(mock_params)


class TestLoadErrorHandling:
    """Test error handling in load application."""

    @patch("src.integrations.scia_integration.scia_loads.extract_tandem_parameters_from_bridge")
    def test_tandem_load_error_propagation(self, mock_extract: Mock) -> None:
        """Test error propagation in tandem load application."""
        mock_params = Mock()
        mock_traffic_group = "Traffic"

        # Simulate error in parameter extraction
        mock_extract.side_effect = Exception("Parameter extraction failed")

        with pytest.raises(Exception, match="Parameter extraction failed"):
            add_theoretical_tandem_loads(mock_params, mock_traffic_group)


if __name__ == "__main__":
    pytest.main([__file__])
