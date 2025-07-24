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


class TestAllLoads:
    """Test the main orchestrator for creating all loads."""

    @patch("src.integrations.scia_integration.scia_loads.add_theoretical_tandem_loads")
    def test_create_all_loads(self, mock_add_tandem: Mock, mock_builder: Mock, mock_params: Mock) -> None:
        """Test that `create_all_loads` calls the tandem load function."""
        from src.integrations.scia_integration.scia_loads import create_all_loads

        # Create a mock load_cases dictionary
        mock_load_cases = {
            "dead_load_cases": {"leuning": Mock(name="BG2004")},
            "pedestrian": Mock(name="BG5001"),
            "service_vehicle_cases": {
                "y_plus": Mock(name="BG6001"),
                "y_minus": Mock(name="BG6002"),
            },
        }

        create_all_loads(mock_builder, mock_params, mock_load_cases)
        mock_add_tandem.assert_called_once_with(mock_builder, mock_params, mock_load_cases)
        # TODO: Add asserts for other load types when implemented


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
