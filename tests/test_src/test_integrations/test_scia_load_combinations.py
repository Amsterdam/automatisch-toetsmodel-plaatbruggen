"""
Tests for SCIA load combinations module.

Tests for load combination creation functions using a mocked SciaModelBuilder.
"""

from unittest.mock import Mock, patch
from app.bridge.parametrization import BridgeParametrization

import pytest

from src.integrations.scia_integration.scia_load_combinations import (
    create_all_load_combinations,
    create_load_combination,
)
from src.integrations.scia_integration.scia_model_interface import SciaCombinationType


@pytest.fixture
def mock_builder() -> Mock:
    """Fixture to provide a mocked SciaModelBuilder."""
    return Mock()


class TestCreateLoadCombination:
    """Tests for the base load combination creation function."""

    def test_create_load_combination(self, mock_builder: Mock) -> None:
        """Test the successful creation of a load combination."""
        mock_lc1 = Mock()
        mock_lc2 = Mock()
        factors = {mock_lc1: 1.5, mock_lc2: 1.0}
        create_load_combination(mock_builder, SciaCombinationType.EN_ULS_SET_B, "TestCombo", factors, "A test combo")

        mock_builder.create_load_combination.assert_called_once_with(
            name="TestCombo",
            combination_type=SciaCombinationType.EN_ULS_SET_B,
            load_case_factors=factors,
            description="A test combo",
        )

    def test_create_load_combination_default_description(self, mock_builder: Mock) -> None:
        """Test that a default description is created if none is provided."""
        create_load_combination(mock_builder, SciaCombinationType.EN_SLS_CHAR, "DefaultDescCombo", {})
        mock_builder.create_load_combination.assert_called_once()
        assert mock_builder.create_load_combination.call_args[1]["description"] == "Load combination: DefaultDescCombo"


class TestCreateAllLoadCombinations:
    """Tests for the main function that creates a list of standard combinations."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination")
    def test_create_all_load_combinations_with_pedestrian(self, params: BridgeParametrization, mock_create: Mock, mock_builder: Mock) -> None:
        """Test that combination is created when pedestrian load case is available."""
        mock_sw_case = Mock()
        mock_pedestrian_case = Mock()

        all_load_cases = {
            "standard_cases": {"self_weight": mock_sw_case, "pedestrian": mock_pedestrian_case},
        }

        combinations = create_all_load_combinations(params, mock_builder, all_load_cases)

        assert len(combinations) == 1
        mock_create.assert_called_once_with(
            builder=mock_builder,
            combination_type=SciaCombinationType.EN_ULS_SET_B,
            combination_name="ULS_Example_SW_Pedestrian",
            load_case_factors={mock_sw_case: 1.35, mock_pedestrian_case: 1.50},
            description="Example ULS: 1.35*G + 1.50*Q (Self-weight + Pedestrian)",
        )
        assert combinations[0] == mock_create.return_value

    def test_create_all_load_combinations_no_self_weight(self, params:BridgeParametrization, mock_builder: Mock) -> None:
        """Test behavior when self-weight load case is missing."""
        combinations = create_all_load_combinations(params, mock_builder, {})
        assert combinations == []

        combinations = create_all_load_combinations(params, mock_builder, {"standard_cases": {}})
        assert combinations == []

    def test_create_all_load_combinations_no_pedestrian(self, params: BridgeParametrization, mock_builder: Mock) -> None:
        """Test behavior when pedestrian load case is missing."""
        mock_sw_case = Mock()
        all_load_cases = {
            "standard_cases": {"self_weight": mock_sw_case},
        }

        combinations = create_all_load_combinations(params, mock_builder, all_load_cases)
        assert combinations == []  # No combinations created without pedestrian case

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination")
    def test_create_all_load_combinations_exception_handling(self, params: BridgeParametrization, mock_create: Mock, mock_builder: Mock) -> None:
        """Test that exceptions in combination creation are handled gracefully."""
        mock_create.side_effect = Exception("Test exception")

        mock_sw_case = Mock()
        mock_pedestrian_case = Mock()
        all_load_cases = {
            "standard_cases": {"self_weight": mock_sw_case, "pedestrian": mock_pedestrian_case},
        }

        combinations = create_all_load_combinations(params, mock_builder, all_load_cases)
        assert combinations == []  # Should return empty list if combination creation fails
