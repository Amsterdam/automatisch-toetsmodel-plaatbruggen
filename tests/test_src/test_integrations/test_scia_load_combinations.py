"""
Tests for SCIA load combinations module.

Tests for load combination creation functions using SCIA API.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_definitions import (
    LoadCombinationDefinition,
    SciaCombinationType,
)
from src.integrations.scia_integration.scia_load_combinations import (
    create_basic_sls_combination,
    create_basic_uls_combination,
    create_load_combination,
    create_standard_load_combinations,
    create_wind_uls_combination,
)


class TestCreateLoadCombination:
    """Tests for the base load combination creation function."""

    def test_create_load_combination(self) -> None:
        """Test the successful creation of a load combination definition."""
        factors = {"LC1": 1.5, "LC2": 1.0}
        definition = create_load_combination(SciaCombinationType.ULS, "TestCombo", factors, "A test combo")

        assert isinstance(definition, LoadCombinationDefinition)
        assert definition.name == "TestCombo"
        assert definition.combination_type == SciaCombinationType.ULS
        assert definition.load_case_factors == factors
        assert definition.description == "A test combo"

    def test_create_load_combination_default_description(self) -> None:
        """Test that a default description is created if none is provided."""
        definition = create_load_combination(SciaCombinationType.SLS_CHAR, "DefaultDescCombo", {})
        assert definition.description == "Load combination: DefaultDescCombo"


class TestBasicUlsCombination:
    """Tests for the basic ULS combination helper function."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination")
    def test_create_basic_uls_combination(self, mock_create: Mock) -> None:
        """Test that the base creator is called with correct ULS parameters."""
        mock_create.return_value = Mock()
        result = create_basic_uls_combination("SW_Case", "TS_Case", "MyULS")

        expected_factors = {"SW_Case": 1.25, "TS_Case": 1.25}
        mock_create.assert_called_once_with(
            SciaCombinationType.ULS,
            "MyULS",
            expected_factors,
            "Basic ULS: 1.25*G0 + 1.25*TS (Self-weight + Traffic)",
        )
        assert result is mock_create.return_value


class TestBasicSlsCombination:
    """Tests for the basic SLS combination helper function."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination")
    def test_create_basic_sls_combination(self, mock_create: Mock) -> None:
        """Test that the base creator is called with correct SLS parameters."""
        mock_create.return_value = Mock()
        result = create_basic_sls_combination("SW_Case", "TS_Case", "MySLS")

        expected_factors = {"SW_Case": 1.0, "TS_Case": 1.0}
        mock_create.assert_called_once_with(
            SciaCombinationType.SLS_CHAR,
            "MySLS",
            expected_factors,
            "Basic SLS: 1.0*G0 + 1.0*TS (Self-weight + Traffic)",
        )
        assert result is mock_create.return_value


class TestWindUlsCombination:
    """Tests for the ULS combination with wind helper function."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination")
    def test_create_wind_uls_combination(self, mock_create: Mock) -> None:
        """Test that the base creator is called with correct wind ULS parameters."""
        mock_create.return_value = Mock()
        result = create_wind_uls_combination("SW_Case", "TS_Case", "Wind_Case", "MyWindULS")

        expected_factors = {
            "SW_Case": 1.35,
            "TS_Case": 1.5,
            "Wind_Case": 1.5 * 0.6,
        }
        mock_create.assert_called_once_with(
            SciaCombinationType.ULS,
            "MyWindULS",
            expected_factors,
            "ULS with Wind: 1.35*G0 + 1.5*TS + 0.9*W (Self-weight + Traffic + Wind)",
        )
        assert result is mock_create.return_value


class TestStandardLoadCombinations:
    """Tests for the main function that creates a list of standard combinations."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_basic_uls_combination")
    @patch("src.integrations.scia_integration.scia_load_combinations.create_basic_sls_combination")
    @patch("src.integrations.scia_integration.scia_load_combinations.create_wind_uls_combination")
    def test_create_standard_load_combinations(self, mock_wind_uls: Mock, mock_sls: Mock, mock_uls: Mock) -> None:
        """Test that combination helpers are called for each tandem case."""
        tandem_cases = ["TS1", "TS2"]
        definitions = create_standard_load_combinations("SelfWeight", tandem_cases, "Wind")

        # Should be 3 combinations per tandem case (ULS, SLS, Wind ULS)
        assert mock_uls.call_count == 2
        assert mock_sls.call_count == 2
        assert mock_wind_uls.call_count == 2
        assert len(definitions) == 6

        # Check call arguments for the first tandem case
        mock_uls.assert_any_call("SelfWeight", "TS1", "ULS_T1")
        mock_sls.assert_any_call("SelfWeight", "TS1", "SLS_T1")
        mock_wind_uls.assert_any_call("SelfWeight", "TS1", "Wind", "ULS_WIND_T1")

        # Check call arguments for the second tandem case
        mock_uls.assert_any_call("SelfWeight", "TS2", "ULS_T2")
        mock_sls.assert_any_call("SelfWeight", "TS2", "SLS_T2")
        mock_wind_uls.assert_any_call("SelfWeight", "TS2", "Wind", "ULS_WIND_T2")


if __name__ == "__main__":
    pytest.main([__file__])
