"""
Tests for SCIA load combinations module.

Tests for load combination creation functions using a mocked SciaModelBuilder.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_combinations import (
    create_all_load_combinations,
    create_basic_sls_combination,
    create_basic_uls_combination,
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
        create_load_combination(mock_builder, SciaCombinationType.ULS, "TestCombo", factors, "A test combo")

        mock_builder.create_load_combination.assert_called_once_with(
            name="TestCombo",
            combination_type=SciaCombinationType.ULS,
            load_case_factors=factors,
            description="A test combo",
        )

    def test_create_load_combination_default_description(self, mock_builder: Mock) -> None:
        """Test that a default description is created if none is provided."""
        create_load_combination(mock_builder, SciaCombinationType.SLS_CHAR, "DefaultDescCombo", {})
        mock_builder.create_load_combination.assert_called_once()
        assert mock_builder.create_load_combination.call_args[1]["description"] == "Load combination: DefaultDescCombo"


class TestBasicCombinations:
    """Tests for the basic ULS and SLS combination helper functions."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination")
    def test_create_basic_uls_combination(self, mock_create: Mock, mock_builder: Mock) -> None:
        """Test that the base creator is called with correct ULS parameters."""
        sw_case = Mock()
        ts_case = Mock()
        create_basic_uls_combination(mock_builder, sw_case, ts_case, "MyULS")

        expected_factors = {sw_case: 1.25, ts_case: 1.25}
        mock_create.assert_called_once_with(
            mock_builder,
            SciaCombinationType.ULS,
            "MyULS",
            expected_factors,
            "Basic ULS: 1.25*G0 + 1.25*TS (Self-weight + Traffic)",
        )

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination")
    def test_create_basic_sls_combination(self, mock_create: Mock, mock_builder: Mock) -> None:
        """Test that the base creator is called with correct SLS parameters."""
        sw_case = Mock()
        ts_case = Mock()
        create_basic_sls_combination(mock_builder, sw_case, ts_case, "MySLS")

        expected_factors = {sw_case: 1.0, ts_case: 1.0}
        mock_create.assert_called_once_with(
            mock_builder,
            SciaCombinationType.SLS_CHAR,
            "MySLS",
            expected_factors,
            "Basic SLS: 1.0*G0 + 1.0*TS (Self-weight + Traffic)",
        )


class TestCreateAllLoadCombinations:
    """Tests for the main function that creates a list of standard combinations."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_basic_uls_combination")
    def test_create_all_load_combinations(self, mock_create_uls: Mock, mock_builder: Mock) -> None:
        """Test that combination helpers are called for the placeholder logic."""
        mock_sw_case = Mock()
        mock_ts_case_1 = Mock()
        mock_ts_case_2 = Mock()

        all_load_cases = {
            "standard_cases": {"self_weight": mock_sw_case},
            "tandem_cases": {"ts1": mock_ts_case_1, "ts2": mock_ts_case_2},
        }

        combinations = create_all_load_combinations(mock_builder, all_load_cases)

        assert len(combinations) == 1
        mock_create_uls.assert_called_once_with(mock_builder, mock_sw_case, mock_ts_case_1, "UGT_Placeholder")
        assert combinations[0] == mock_create_uls.return_value

    def test_create_all_load_combinations_no_cases(self, mock_builder: Mock) -> None:
        """Test behavior when load cases are missing."""
        combinations = create_all_load_combinations(mock_builder, {})
        assert combinations == []

        combinations = create_all_load_combinations(mock_builder, {"standard_cases": {}, "tandem_cases": {}})
        assert combinations == []
