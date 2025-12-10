"""Tests for load combination Pydantic models."""

import unittest
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.combination_models import LoadCombinationConfig


class TestLoadCombinationConfig(unittest.TestCase):
    """Test cases for LoadCombinationConfig model."""

    def test_valid_config_creation(self) -> None:
        """Test creating a valid LoadCombinationConfig."""
        config = LoadCombinationConfig(cc_class="CC2", design_code="NEN 8700 verbouw", construction_year=2010)

        assert config.cc_class == "CC2"
        assert config.design_code == "NEN 8700 verbouw"
        assert config.construction_year == 2010

    def test_all_valid_cc_classes(self) -> None:
        """Test all valid consequence classes."""
        valid_classes: list[str] = ["CC1a/b", "CC2", "CC3"]

        for cc_class in valid_classes:
            if cc_class in ["CC1a/b", "CC2", "CC3"]:  # Type guard for MyPy
                config = LoadCombinationConfig(cc_class=cc_class, design_code="NEN 8700 verbouw", construction_year=2010)  # type: ignore[arg-type]
                assert config.cc_class == cc_class

    def test_all_valid_design_codes(self) -> None:
        """Test all valid design codes."""
        valid_codes: list[str] = ["NEN 8700 verbouw", "NEN 8700 gebruik", "NEN 8700 afkeur"]

        for design_code in valid_codes:
            if design_code in ["NEN 8700 verbouw", "NEN 8700 gebruik", "NEN 8700 afkeur"]:  # Type guard for MyPy
                config = LoadCombinationConfig(cc_class="CC2", design_code=design_code, construction_year=2010)  # type: ignore[arg-type]
                assert config.design_code == design_code

    def test_invalid_cc_class_rejected(self) -> None:
        """Test that invalid consequence classes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadCombinationConfig(
                cc_class="CC4",  # type: ignore[arg-type]  # Invalid
                design_code="NEN 8700 verbouw",
                construction_year=2010,
            )

        error_msg = str(exc_info.value)
        assert "cc_class" in error_msg
        assert "CC1a/b" in error_msg
        assert "CC2" in error_msg
        assert "CC3" in error_msg

    def test_invalid_design_code_rejected(self) -> None:
        """Test that invalid design codes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadCombinationConfig(
                cc_class="CC2",
                design_code="EN 1990",  # type: ignore[arg-type]  # Invalid
                construction_year=2010,
            )

        error_msg = str(exc_info.value)
        assert "design_code" in error_msg
        assert "NEN 8700 verbouw" in error_msg

    def test_construction_year_too_old_rejected(self) -> None:
        """Test that construction years before 1850 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadCombinationConfig(
                cc_class="CC2",
                design_code="NEN 8700 verbouw",
                construction_year=1800,  # Too old
            )

        error_msg = str(exc_info.value)
        assert "construction_year" in error_msg
        assert "1850" in error_msg

    def test_construction_year_too_future_rejected(self) -> None:
        """Test that construction years too far in the future are rejected."""
        current_year = datetime.now(UTC).year
        future_year = current_year + 20  # Too far in future

        with pytest.raises(ValidationError) as exc_info:
            LoadCombinationConfig(cc_class="CC2", design_code="NEN 8700 verbouw", construction_year=future_year)

        error_msg = str(exc_info.value)
        assert "too far in the future" in error_msg
        assert f"max: {current_year + 10}" in error_msg

    def test_construction_year_edge_cases_valid(self) -> None:
        """Test construction year edge cases that should be valid."""
        current_year = datetime.now(UTC).year

        # Test minimum valid year
        config_min = LoadCombinationConfig(cc_class="CC2", design_code="NEN 8700 verbouw", construction_year=1850)
        assert config_min.construction_year == 1850

        # Test maximum valid year
        config_max = LoadCombinationConfig(cc_class="CC2", design_code="NEN 8700 verbouw", construction_year=current_year + 10)
        assert config_max.construction_year == current_year + 10

        # Test current year
        config_current = LoadCombinationConfig(cc_class="CC2", design_code="NEN 8700 verbouw", construction_year=current_year)
        assert config_current.construction_year == current_year

    def test_from_params_dict_valid(self) -> None:
        """Test creating config from valid params dictionary."""
        params = {"cc_class": "CC2", "design_code": "NEN 8700 verbouw", "info": {"construction_year": 2010}}

        config = LoadCombinationConfig.from_params_dict(params)

        assert config.cc_class == "CC2"
        assert config.design_code == "NEN 8700 verbouw"
        assert config.construction_year == 2010

    def test_from_params_dict_missing_cc_class(self) -> None:
        """Test error when cc_class is missing from params."""
        params = {"design_code": "NEN 8700 verbouw", "info": {"construction_year": 2010}}

        with pytest.raises(KeyError, match="Missing required parameter: cc_class"):
            LoadCombinationConfig.from_params_dict(params)

    def test_from_params_dict_missing_design_code(self) -> None:
        """Test error when design_code is missing from params."""
        params = {"cc_class": "CC2", "info": {"construction_year": 2010}}

        with pytest.raises(KeyError, match="Missing required parameter: design_code"):
            LoadCombinationConfig.from_params_dict(params)

    def test_from_params_dict_missing_info(self) -> None:
        """Test error when info section is missing from params."""
        params = {"cc_class": "CC2", "design_code": "NEN 8700 verbouw"}

        with pytest.raises(KeyError, match="Missing required parameter: info"):
            LoadCombinationConfig.from_params_dict(params)

    def test_from_params_dict_missing_construction_year(self) -> None:
        """Test error when construction_year is missing from info."""
        params = {"cc_class": "CC2", "design_code": "NEN 8700 verbouw", "info": {}}

        with pytest.raises(KeyError, match="Missing required parameter: info.construction_year"):
            LoadCombinationConfig.from_params_dict(params)

    def test_from_params_dict_string_construction_year(self) -> None:
        """Test that string construction_year is converted to int."""
        params = {
            "cc_class": "CC2",
            "design_code": "NEN 8700 verbouw",
            "info": {"construction_year": "2010"},  # String instead of int
        }

        config = LoadCombinationConfig.from_params_dict(params)
        assert config.construction_year == 2010
        assert isinstance(config.construction_year, int)

    def test_to_tuple_conversion(self) -> None:
        """Test conversion to tuple for backward compatibility."""
        config = LoadCombinationConfig(cc_class="CC2", design_code="NEN 8700 verbouw", construction_year=2010)

        result = config.to_tuple()
        expected = ("CC2", "NEN 8700 verbouw", "2010")

        assert result == expected
        assert isinstance(result[2], str)  # construction_year should be string in tuple

    def test_whitespace_stripping(self) -> None:
        """Test that whitespace is automatically stripped from string inputs."""
        config = LoadCombinationConfig(
            cc_class="  CC2  ",  # type: ignore[arg-type]  # Extra whitespace
            design_code="  NEN 8700 verbouw  ",  # type: ignore[arg-type]  # Extra whitespace
            construction_year=2010,
        )

        assert config.cc_class == "CC2"
        assert config.design_code == "NEN 8700 verbouw"

    def test_validation_assignment_enabled(self) -> None:
        """Test that validation occurs on assignment after creation."""
        config = LoadCombinationConfig(cc_class="CC2", design_code="NEN 8700 verbouw", construction_year=2010)

        # This should raise a validation error
        with pytest.raises(ValidationError):
            config.cc_class = "INVALID"  # type: ignore[assignment]

    def test_comprehensive_integration_scenario(self) -> None:
        """Test a comprehensive scenario with realistic data."""
        # Simulate data from seed files
        params = {"cc_class": "CC2", "design_code": "NEN 8700 verbouw", "info": {"construction_year": 2000}}

        # Create config
        config = LoadCombinationConfig.from_params_dict(params)

        # Verify all fields
        assert config.cc_class == "CC2"
        assert config.design_code == "NEN 8700 verbouw"
        assert config.construction_year == 2000

        # Test tuple conversion for backward compatibility
        cc_class, design_code, construction_year_str = config.to_tuple()
        assert cc_class == "CC2"
        assert design_code == "NEN 8700 verbouw"
        assert construction_year_str == "2000"


if __name__ == "__main__":
    unittest.main()
