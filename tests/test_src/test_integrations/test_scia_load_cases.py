"""
Tests for SCIA load cases module.

Tests for load case creation functions using direct SCIA API.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_definitions import LoadCaseDefinition
from src.integrations.scia_integration.scia_load_cases import (
    create_basic_permanent_load_cases,
    create_self_weight_load_case,
    create_tandem_load_case,
    create_wind_load_case,
)


class TestSelfWeightLoadCase:
    """Tests for creating the self-weight load case definition."""

    def test_create_self_weight_load_case(self) -> None:
        """Test the successful creation of a self-weight load case definition."""
        permanent_group_name = "LG1_Permanent"
        definition = create_self_weight_load_case(permanent_group_name)

        assert isinstance(definition, LoadCaseDefinition)
        assert definition.name == "BG01"
        assert definition.group_name == permanent_group_name
        assert definition.case_type == "PERMANENT"
        assert definition.permanent_type == "SELF_WEIGHT"
        assert definition.description == "Eigen gewicht"

    def test_create_self_weight_load_case_return_type(self) -> None:
        """Verify that the function returns a LoadCaseDefinition."""
        definition = create_self_weight_load_case("LG1")
        assert isinstance(definition, LoadCaseDefinition)


class TestWindLoadCase:
    """Tests for creating the wind load case definition."""

    def test_create_wind_load_case(self) -> None:
        """Test the successful creation of a wind load case definition."""
        wind_group_name = "LG3_Wind"
        definition = create_wind_load_case(wind_group_name)

        assert isinstance(definition, LoadCaseDefinition)
        assert definition.name == "Q2_Wind"
        assert definition.group_name == wind_group_name
        assert definition.case_type == "VARIABLE"
        assert definition.specification == "STATIC_WIND"
        assert definition.duration == "SHORT"
        assert definition.description == "Wind Load"

    def test_create_wind_load_case_return_type(self) -> None:
        """Verify that the function returns a LoadCaseDefinition."""
        definition = create_wind_load_case("LG3")
        assert isinstance(definition, LoadCaseDefinition)


class TestTandemLoadCase:
    """Tests for creating tandem load case definitions."""

    @pytest.mark.parametrize(
        "mode, expected_desc_part",
        [
            ("theoretical", "Tandem System - Theoretical Lane"),
            ("eurocode", "Load Model 1 - Tandem System"),
            ("shiftable", "Tandem System - Shiftable Position"),
            ("actual", "Tandem System - Actual Lane"),
            ("unknown", "Tandem System"),
        ],
    )
    def test_create_tandem_load_case_modes(self, mode: str, expected_desc_part: str) -> None:
        """Test tandem load case creation for different modes."""
        traffic_group_name = "LG2_Traffic"
        case_name = "TS_Lane1"
        definition = create_tandem_load_case(
            traffic_group_name,
            case_name,
            mode=mode,
        )

        assert isinstance(definition, LoadCaseDefinition)
        assert definition.name == case_name
        assert definition.group_name == traffic_group_name
        assert definition.case_type == "VARIABLE"
        assert f"{expected_desc_part} {case_name}" in definition.description

    def test_create_tandem_load_case_return_type(self) -> None:
        """Verify that the function returns a LoadCaseDefinition."""
        definition = create_tandem_load_case("LG2", "TS1")
        assert isinstance(definition, LoadCaseDefinition)


class TestBasicPermanentLoadCases:
    """Tests for the helper function that creates all basic permanent load cases."""

    @patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case")
    def test_create_basic_permanent_load_cases(self, mock_create_self_weight: Mock) -> None:
        """Test that the self-weight creation function is called."""
        permanent_group_name = "PermanentLoads"
        mock_sw_def = Mock()
        mock_create_self_weight.return_value = mock_sw_def

        definitions = create_basic_permanent_load_cases(permanent_group_name)

        mock_create_self_weight.assert_called_once_with(permanent_group_name)
        assert definitions["self_weight"] is mock_sw_def
        assert len(definitions) == 1

    def test_create_basic_permanent_load_cases_return_structure(self) -> None:
        """Test that the function returns the expected dictionary structure."""
        definitions = create_basic_permanent_load_cases("PermanentGroup")

        assert "self_weight" in definitions
        assert isinstance(definitions["self_weight"], LoadCaseDefinition)


class TestLoadCaseIntegration:
    """Placeholder for future integration tests between different load case types."""

    def test_placeholder(self) -> None:
        """Placeholder test."""
        assert True


if __name__ == "__main__":
    pytest.main([__file__])
