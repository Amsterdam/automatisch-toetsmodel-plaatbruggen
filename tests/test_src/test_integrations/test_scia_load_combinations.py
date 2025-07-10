"""
Tests for SCIA load combinations module.

Tests for load combination creation functions using SCIA API.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_combinations import (
    create_basic_sls_combination,
    create_basic_uls_combination,
    create_wind_uls_combination,
)


class TestBasicULSCombination:
    """Test basic ULS combination creation."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_create_basic_uls_combination_success(self, mock_create_combo: Mock) -> None:
        """Test successful basic ULS combination creation."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_uls_combo = Mock()
        mock_create_combo.return_value = mock_uls_combo

        result = create_basic_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case)

        # Verify call to utility function
        mock_create_combo.assert_called_once_with(
            mock_model,
            "ULS",
            "ULS_Basic_G0+TS",
            {mock_self_weight_case: 1.25, mock_traffic_case: 1.25},
            "Basic ULS: 1.25*G0 + 1.25*TS (Self-weight + Traffic)",
        )
        assert result is mock_uls_combo

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_create_basic_uls_combination_custom_name(self, mock_create_combo: Mock) -> None:
        """Test ULS combination with custom name."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_uls_combo = Mock()
        mock_create_combo.return_value = mock_uls_combo

        result = create_basic_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case, "Custom_ULS_Name")

        # Verify custom name is used
        mock_create_combo.assert_called_once_with(
            mock_model,
            "ULS",
            "Custom_ULS_Name",
            {mock_self_weight_case: 1.25, mock_traffic_case: 1.25},
            "Basic ULS: 1.25*G0 + 1.25*TS (Self-weight + Traffic)",
        )
        assert result is mock_uls_combo


class TestBasicSLSCombination:
    """Test basic SLS combination creation."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_create_basic_sls_combination_success(self, mock_create_combo: Mock) -> None:
        """Test successful basic SLS combination creation."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_sls_combo = Mock()
        mock_create_combo.return_value = mock_sls_combo

        result = create_basic_sls_combination(mock_model, mock_self_weight_case, mock_traffic_case)

        # Verify call to utility function
        mock_create_combo.assert_called_once_with(
            mock_model,
            "SLS_CHAR",
            "SLS_Basic_G0+TS",
            {mock_self_weight_case: 1.0, mock_traffic_case: 1.0},
            "Basic SLS: 1.0*G0 + 1.0*TS (Self-weight + Traffic)",
        )
        assert result is mock_sls_combo

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_create_basic_sls_combination_custom_name(self, mock_create_combo: Mock) -> None:
        """Test SLS combination with custom name."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_sls_combo = Mock()
        mock_create_combo.return_value = mock_sls_combo

        result = create_basic_sls_combination(mock_model, mock_self_weight_case, mock_traffic_case, "Custom_SLS_Name")

        # Verify custom name is used
        mock_create_combo.assert_called_once_with(
            mock_model,
            "SLS_CHAR",
            "Custom_SLS_Name",
            {mock_self_weight_case: 1.0, mock_traffic_case: 1.0},
            "Basic SLS: 1.0*G0 + 1.0*TS (Self-weight + Traffic)",
        )
        assert result is mock_sls_combo


class TestWindULSCombination:
    """Test wind ULS combination creation."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_create_wind_uls_combination_success(self, mock_create_combo: Mock) -> None:
        """Test successful wind ULS combination creation."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_wind_case = Mock()
        mock_wind_combo = Mock()
        mock_create_combo.return_value = mock_wind_combo

        result = create_wind_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case, mock_wind_case)

        # Verify call with wind factors
        mock_create_combo.assert_called_once_with(
            mock_model,
            "ULS",
            "ULS_Wind_G0+TS+W",
            {mock_self_weight_case: 1.35, mock_traffic_case: 1.5, mock_wind_case: 0.9},  # 1.5 * 0.6 = 0.9
            "ULS with Wind: 1.35*G0 + 1.5*TS + 0.9*W (Self-weight + Traffic + Wind)",
        )
        assert result is mock_wind_combo

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_create_wind_uls_combination_custom_name(self, mock_create_combo: Mock) -> None:
        """Test wind ULS combination with custom name."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_wind_case = Mock()
        mock_wind_combo = Mock()
        mock_create_combo.return_value = mock_wind_combo

        result = create_wind_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case, mock_wind_case, "Custom_Wind_ULS")

        # Verify custom name is used
        mock_create_combo.assert_called_once_with(
            mock_model,
            "ULS",
            "Custom_Wind_ULS",
            {mock_self_weight_case: 1.35, mock_traffic_case: 1.5, mock_wind_case: 0.9},
            "ULS with Wind: 1.35*G0 + 1.5*TS + 0.9*W (Self-weight + Traffic + Wind)",
        )
        assert result is mock_wind_combo


class TestLoadCombinationFactors:
    """Test load combination factors are correct."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_uls_factors_correct(self, mock_create_combo: Mock) -> None:
        """Test ULS load factors are correct."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_uls_combo = Mock()
        mock_create_combo.return_value = mock_uls_combo

        create_basic_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case)

        # Verify factors
        call_args = mock_create_combo.call_args
        factors = call_args[0][3]  # Fourth positional argument
        assert factors[mock_self_weight_case] == 1.25
        assert factors[mock_traffic_case] == 1.25

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_sls_factors_correct(self, mock_create_combo: Mock) -> None:
        """Test SLS load factors are correct."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_sls_combo = Mock()
        mock_create_combo.return_value = mock_sls_combo

        create_basic_sls_combination(mock_model, mock_self_weight_case, mock_traffic_case)

        # Verify factors
        call_args = mock_create_combo.call_args
        factors = call_args[0][3]  # Fourth positional argument
        assert factors[mock_self_weight_case] == 1.0
        assert factors[mock_traffic_case] == 1.0

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_wind_factors_correct(self, mock_create_combo: Mock) -> None:
        """Test wind load factors are correct."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_wind_case = Mock()
        mock_wind_combo = Mock()
        mock_create_combo.return_value = mock_wind_combo

        create_wind_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case, mock_wind_case)

        # Verify factors
        call_args = mock_create_combo.call_args
        factors = call_args[0][3]  # Fourth positional argument
        assert factors[mock_self_weight_case] == 1.35
        assert factors[mock_traffic_case] == 1.5
        assert factors[mock_wind_case] == 0.9  # 1.5 * 0.6


class TestLoadCombinationNaming:
    """Test load combination naming conventions."""

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_default_naming_pattern(self, mock_create_combo: Mock) -> None:
        """Test default naming pattern follows convention."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_wind_case = Mock()
        mock_create_combo.return_value = Mock()

        # Test each function's default name
        create_basic_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case)
        create_basic_sls_combination(mock_model, mock_self_weight_case, mock_traffic_case)
        create_wind_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case, mock_wind_case)

        # Verify naming pattern
        calls = mock_create_combo.call_args_list
        assert len(calls) == 3

        # Check names
        assert calls[0][0][2] == "ULS_Basic_G0+TS"
        assert calls[1][0][2] == "SLS_Basic_G0+TS"
        assert calls[2][0][2] == "ULS_Wind_G0+TS+W"

    @patch("src.integrations.scia_integration.scia_load_combinations.create_load_combination_by_type")
    def test_combination_type_consistency(self, mock_create_combo: Mock) -> None:
        """Test combination types are consistent."""
        mock_model = Mock()
        mock_self_weight_case = Mock()
        mock_traffic_case = Mock()
        mock_wind_case = Mock()
        mock_create_combo.return_value = Mock()

        create_basic_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case)
        create_basic_sls_combination(mock_model, mock_self_weight_case, mock_traffic_case)
        create_wind_uls_combination(mock_model, mock_self_weight_case, mock_traffic_case, mock_wind_case)

        # Verify combination types
        calls = mock_create_combo.call_args_list
        assert len(calls) == 3

        # Check types
        assert calls[0][0][1] == "ULS"  # Basic ULS
        assert calls[1][0][1] == "SLS_CHAR"  # Basic SLS
        assert calls[2][0][1] == "ULS"  # Wind ULS


if __name__ == "__main__":
    pytest.main([__file__])
