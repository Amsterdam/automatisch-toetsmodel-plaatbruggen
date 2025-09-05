"""
Test module for load factor calculations and validations.

This module contains tests for the load factor functions including gamma factors,
psi factors, alpha trend factors, and alpha Q factors according to Dutch standards.
"""

import unittest
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.combinations.load_factors import (
    create_load_combination_table,
    get_alpha_q_nen_en_1991_2,
    get_alpha_trend_nen_8701,
    get_gamma_factors,
    get_psi_nen_8701,
)


class TestGetGammaFactors(unittest.TestCase):
    """Test cases for the get_gamma_factors function."""

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_gamma_factors_valid_input(self, mock_read_csv: Mock) -> None:
        """Test get_gamma_factors with valid input parameters."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "gevolgklasse": ["CC1a", "CC1a", "CC2", "CC2"],
                "toetsniveau": ["Verbouw", "Verbouw", "Gebruik", "Gebruik"],
                "vergelijking": ["6.10a", "6.10b", "6.10a", "6.10b"],
                "gamma_Gjsup": [1.2, 1.2, 1.3, 1.3],
                "gamma_Gjsup_bb2003": [1.1, 1.1, 1.2, 1.2],
                "gamma_Gjinf": [1.0, 1.0, 1.0, 1.0],
                "gamma_Qverkeer": [1.35, 1.35, 1.4, 1.4],
                "gamma_Qverkeer_bb2003": [1.25, 1.25, 1.3, 1.3],
                "gamma_Qwind": [1.5, 1.5, 1.5, 1.5],
                "gamma_Qoverig": [1.5, 1.5, 1.5, 1.5],
                "gamma_Gset_lin": [1.2, 1.2, 1.2, 1.2],
                "gamma_Gset_nonlin": [1.35, 1.35, 1.35, 1.35],
                "gamma_P": [1.0, 1.0, 1.0, 1.0],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result = get_gamma_factors("CC1a", "NEN 8700 verbouw", "2010")

        # Assert
        assert isinstance(result, dict)
        assert "6.10a" in result
        assert "6.10b" in result
        assert result["6.10a"]["gamma_Gjsup"] == 1.2
        assert result["6.10b"]["gamma_Gjsup"] == 1.2

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_gamma_factors_building_year_2003_or_before(self, mock_read_csv: Mock) -> None:
        """Test get_gamma_factors adjusts factors for buildings from 2003 or before."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "gevolgklasse": ["CC2", "CC2"],
                "toetsniveau": ["Gebruik", "Gebruik"],
                "vergelijking": ["6.10a", "6.10b"],
                "gamma_Gjsup": [1.3, 1.3],
                "gamma_Gjsup_bb2003": [1.2, 1.2],
                "gamma_Gjinf": [1.0, 1.0],
                "gamma_Qverkeer": [1.4, 1.4],
                "gamma_Qverkeer_bb2003": [1.3, 1.3],
                "gamma_Qwind": [1.5, 1.5],
                "gamma_Qoverig": [1.5, 1.5],
                "gamma_Gset_lin": [1.2, 1.2],
                "gamma_Gset_nonlin": [1.35, 1.35],
                "gamma_P": [1.0, 1.0],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result = get_gamma_factors("CC2", "NEN 8700 gebruik", "2000")

        # Assert
        assert result["6.10a"]["gamma_Gjsup"] == 1.2  # Should use bb2003 value
        assert result["6.10a"]["gamma_Qverkeer"] == 1.3  # Should use bb2003 value

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_gamma_factors_invalid_cc_class(self, mock_read_csv: Mock) -> None:
        """Test get_gamma_factors raises ValueError for invalid CC class."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "gevolgklasse": ["CC1a", "CC2"],
                "toetsniveau": ["Verbouw", "Gebruik"],
                "vergelijking": ["6.10a", "6.10b"],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act & Assert
        with pytest.raises(ValueError, match="No gamma factors found for CC class 'CC9'"):
            get_gamma_factors("CC9", "NEN 8700 verbouw", "2010")

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_gamma_factors_invalid_safety_level(self, mock_read_csv: Mock) -> None:
        """Test get_gamma_factors raises ValueError for invalid safety level."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "gevolgklasse": ["CC1a", "CC2"],
                "toetsniveau": ["Verbouw", "Gebruik"],
                "vergelijking": ["6.10a", "6.10b"],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act & Assert
        with pytest.raises(ValueError, match="No gamma factors found for CC class 'CC1a' and safety level 'Invalid'"):
            get_gamma_factors("CC1a", "Invalid", "2010")


class TestGetPsiNen8701(unittest.TestCase):
    """Test cases for the get_psi_nen_8701 function."""

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_psi_nen_8701_valid_input(self, mock_read_csv: Mock) -> None:
        """Test get_psi_nen_8701 with valid input parameters."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "ref_period": [0.083, 1.0, 15.0, 100.0],
                "20": [0.5, 0.6, 0.7, 0.8],
                "50": [0.6, 0.7, 0.8, 0.9],
                "100": [0.7, 0.8, 0.9, 1.0],
                "200": [0.8, 0.9, 1.0, 1.1],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result = get_psi_nen_8701(50.0, 15.0)

        # Assert
        assert isinstance(result, float)
        assert result > 0

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_psi_nen_8701_span_clamping(self, mock_read_csv: Mock) -> None:
        """Test get_psi_nen_8701 clamps span values outside valid range."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "ref_period": [1.0],
                "20": [0.6],
                "200": [0.9],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result_low = get_psi_nen_8701(10.0, 1.0)  # Should clamp to 20
        result_high = get_psi_nen_8701(300.0, 1.0)  # Should clamp to 200

        # Assert
        assert isinstance(result_low, float)
        assert isinstance(result_high, float)

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_psi_nen_8701_reference_period_clamping(self, mock_read_csv: Mock) -> None:
        """Test get_psi_nen_8701 clamps reference period values outside valid range."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "ref_period": [0.083, 100.0],
                "50": [0.6, 0.9],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result_low = get_psi_nen_8701(50.0, 0.01)  # Should clamp to min
        result_high = get_psi_nen_8701(50.0, 150.0)  # Should clamp to max

        # Assert
        assert isinstance(result_low, float)
        assert isinstance(result_high, float)


class TestGetAlphaTrendNen8701(unittest.TestCase):
    """Test cases for the get_alpha_trend_nen_8701 function."""

    @patch("src.combinations.load_factors.pd.read_csv")
    @patch("src.combinations.load_factors.datetime.datetime")
    def test_get_alpha_trend_nen_8701_valid_input(self, mock_datetime: Mock, mock_read_csv: Mock) -> None:
        """Test get_alpha_trend_nen_8701 with valid input parameters."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "span": [0, 50, 100],
                "2010": [1.0, 1.1, 1.2],
                "2030": [1.1, 1.2, 1.3],
                "2060": [1.2, 1.3, 1.4],
            }
        )
        mock_read_csv.return_value = mock_df

        # Mock current year as 2025
        mock_now = Mock()
        mock_now.year = 2025
        mock_datetime.now.return_value = mock_now

        # Act
        result = get_alpha_trend_nen_8701(50.0, 30)

        # Assert
        assert isinstance(result, float)
        assert result > 0

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_alpha_trend_nen_8701_span_clamping(self, mock_read_csv: Mock) -> None:
        """Test get_alpha_trend_nen_8701 clamps span values outside valid range."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "span": [0, 100],
                "2030": [1.0, 1.2],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result_low = get_alpha_trend_nen_8701(-10.0, 30)  # Should clamp to 0
        result_high = get_alpha_trend_nen_8701(150.0, 30)  # Should clamp to 100

        # Assert
        assert isinstance(result_low, float)
        assert isinstance(result_high, float)


class TestGetAlphaQNenEn19912(unittest.TestCase):
    """Test cases for the get_alpha_q_nen_en_1991_2 function."""

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_alpha_q_nen_en_1991_2_valid_input(self, mock_read_csv: Mock) -> None:
        """Test get_alpha_q_nen_en_1991_2 with valid input parameters."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "nobs": [200, 1000, 2000000],
                "20": [1.0, 1.1, 1.3],
                "50": [1.05, 1.15, 1.35],
                "200": [1.1, 1.2, 1.4],
                "alpha_qr": [0.8, 0.9, 1.0],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result = get_alpha_q_nen_en_1991_2(50.0, 1000)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], float)  # alpha_q
        assert isinstance(result[1], float)  # alpha_qr

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_alpha_q_nen_en_1991_2_span_clamping(self, mock_read_csv: Mock) -> None:
        """Test get_alpha_q_nen_en_1991_2 clamps span values outside valid range."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "nobs": [1000],
                "20": [1.1],
                "200": [1.4],
                "alpha_qr": [0.9],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result_low = get_alpha_q_nen_en_1991_2(10.0, 1000)  # Should clamp to 20
        result_high = get_alpha_q_nen_en_1991_2(300.0, 1000)  # Should clamp to 200

        # Assert
        assert isinstance(result_low, list)
        assert isinstance(result_high, list)
        assert len(result_low) == 2
        assert len(result_high) == 2

    @patch("src.combinations.load_factors.pd.read_csv")
    def test_get_alpha_q_nen_en_1991_2_nobs_clamping(self, mock_read_csv: Mock) -> None:
        """Test get_alpha_q_nen_en_1991_2 clamps Nobs values outside valid range."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "nobs": [200, 2000000],
                "50": [1.0, 1.4],
                "alpha_qr": [0.8, 1.0],
            }
        )
        mock_read_csv.return_value = mock_df

        # Act
        result_low = get_alpha_q_nen_en_1991_2(50.0, 100)  # Should clamp to 200
        result_high = get_alpha_q_nen_en_1991_2(50.0, 3000000)  # Should clamp to 2000000

        # Assert
        assert isinstance(result_low, list)
        assert isinstance(result_high, list)
        assert len(result_low) == 2
        assert len(result_high) == 2


class TestCreateLoadCombinationTable(unittest.TestCase):
    """Test cases for the create_load_combination_table function."""

    @patch("src.combinations.load_factors.get_gamma_factors")
    @patch("src.combinations.load_factors.pd.read_csv")
    def test_create_load_combination_table_valid_input(self, mock_read_csv: Mock, mock_get_gamma_factors: Mock) -> None:
        """Test create_load_combination_table with valid input parameters."""
        # Arrange
        mock_gamma_factors = {
            "6.10a": {"gamma_Gjsup": 1.2, "gamma_Qverkeer": 1.35, "gamma_Qwind": 1.5, "gamma_Qoverig": 1.5},
            "6.10b": {"gamma_Gjsup": 1.2, "gamma_Qverkeer": 1.35, "gamma_Qwind": 1.5, "gamma_Qoverig": 1.5},
        }
        mock_get_gamma_factors.return_value = mock_gamma_factors

        mock_df = pd.DataFrame(
            {
                "Combinatie": ["6.10a Perm", "6.10a gr1a", "6.10b Wind gr1a"],
                "Permanent": [1.0, 0.0, 1.0],
                "TS": [0.0, 1.0, 0.0],
                "UDL": [0.0, 1.0, 0.0],
                "Fiets- en voetpaden": [0.0, 0.3, 0.0],
                "Mensenmenigte": [0.0, 0.0, 0.0],
                "Temperatuur": [0.0, 0.6, 0.3],
            }
        )
        mock_df = mock_df.set_index("Combinatie")
        mock_read_csv.return_value = mock_df

        params = {
            "cc_class": "CC2",
            "design_code": "NEN 8700 gebruik",
            "info": {"construction_year": "2010"},
        }

        # Act
        result = create_load_combination_table(params)

        # Assert
        assert result is not None
        # The function returns a Styler object, so we can check its type
        from pandas.io.formats.style import Styler

        assert isinstance(result, Styler)

    def test_create_load_combination_table_missing_cc_class(self) -> None:
        """Test create_load_combination_table raises KeyError for missing cc_class."""
        # Arrange
        params = {
            "design_code": "NEN 8700 gebruik",
            "info": {"construction_year": "2010"},
        }

        # Act & Assert
        with pytest.raises(KeyError, match="Missing required parameter: cc_class"):
            create_load_combination_table(params)

    def test_create_load_combination_table_missing_construction_year(self) -> None:
        """Test create_load_combination_table raises KeyError for missing construction_year."""
        # Arrange
        params = {
            "cc_class": "CC2",
            "design_code": "NEN 8700 gebruik",
            "info": {},
        }

        # Act & Assert
        with pytest.raises(KeyError, match="Missing required parameter: info.construction_year"):
            create_load_combination_table(params)


if __name__ == "__main__":
    unittest.main()
