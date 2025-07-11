"""
Tests for SCIA load cases module.

Tests for load case creation functions using direct SCIA API.
"""

import pytest

from src.integrations.scia_integration.scia_definitions import LoadCaseDefinition
from src.integrations.scia_integration.scia_load_cases import (
    create_pedestrian_load_case,
    create_resting_load_cases,
    create_self_weight_load_case,
    create_service_vehicle_load_cases,
    create_tandem_rs_load_cases,
    create_temperature_load_cases,
    create_udl_traffic_load_cases,
    create_unintended_vehicle_load_cases,
)


class TestSelfWeightLoadCase:
    """Tests for creating the self-weight load case definition."""

    def test_create_self_weight_load_case(self) -> None:
        """Test the successful creation of a self-weight load case definition."""
        definition = create_self_weight_load_case()

        assert isinstance(definition, LoadCaseDefinition)
        assert definition.name == "BG1001"
        assert definition.group_name == "LG1000"
        assert definition.case_type == "PERMANENT"
        assert definition.permanent_type == "SELF_WEIGHT"
        assert definition.description == "Eigen gewicht"

    def test_create_self_weight_load_case_return_type(self) -> None:
        """Verify that the function returns a LoadCaseDefinition."""
        definition = create_self_weight_load_case()
        assert isinstance(definition, LoadCaseDefinition)


class TestRestingLoadCases:
    """Tests for creating resting load case definitions."""

    def test_create_resting_load_cases(self) -> None:
        """Test creation of resting load cases."""
        definitions = create_resting_load_cases()
        assert len(definitions) == 5
        assert definitions[0].name == "BG2001"
        assert definitions[0].group_name == "LG2000"
        assert definitions[0].case_type == "PERMANENT"
        assert definitions[0].permanent_type == "STANDARD"
        assert definitions[0].description == "Rustende belasting - Asfalt"
        assert definitions[4].name == "BG2005"
        assert definitions[4].description == "Rustende belasting - Lichtmast"


class TestTemperatureLoadCases:
    """Tests for creating temperature load case definitions."""

    def test_create_temperature_load_cases(self) -> None:
        """Test creation of temperature load case definitions."""
        definitions = create_temperature_load_cases()
        assert len(definitions) == 4
        assert definitions[0].name == "BG3001"
        assert definitions[0].group_name == "LG3000"
        assert definitions[0].case_type == "VARIABLE"
        assert definitions[0].specification == "TEMPERATURE"
        assert definitions[0].duration == "LONG"
        assert definitions[0].description == "Temperatuur, dek - Temp combi 1"


class TestUdlTrafficLoadCases:
    """Tests for creating UDL traffic load case definitions."""

    def test_create_udl_traffic_load_cases(self) -> None:
        """Test creation of UDL traffic load case definitions."""
        definitions = create_udl_traffic_load_cases()
        assert len(definitions) == 4
        assert definitions[0].name == "BG4001"
        assert definitions[0].group_name == "LG4000"
        assert definitions[0].case_type == "VARIABLE"
        assert definitions[0].duration == "SHORT"


class TestPedestrianLoadCase:
    """Tests for creating pedestrian load case definition."""

    def test_create_pedestrian_load_case(self) -> None:
        """Test creation of pedestrian load case definition."""
        definition = create_pedestrian_load_case()
        assert definition.name == "BG5001"
        assert definition.group_name == "LG5000"
        assert definition.case_type == "VARIABLE"
        assert definition.duration == "SHORT"


class TestServiceVehicleLoadCases:
    """Tests for creating service vehicle load case definitions."""

    def test_create_service_vehicle_load_cases(self) -> None:
        """Test creation of service vehicle load case definitions."""
        definitions = create_service_vehicle_load_cases()
        assert len(definitions) == 3
        assert definitions[0].name == "BG6001"
        assert definitions[0].group_name == "LG6000"


class TestUnintendedVehicleLoadCases:
    """Tests for creating unintended vehicle load case definitions."""

    def test_create_unintended_vehicle_load_cases(self) -> None:
        """Test creation of unintended vehicle load case definitions."""
        definitions = create_unintended_vehicle_load_cases()
        assert len(definitions) == 3
        assert definitions[0].name == "BG7001"
        assert definitions[0].group_name == "LG7000"


class TestTandemRSLoadCases:
    """Tests for creating tandem RS load case definitions."""

    @pytest.mark.parametrize(("rs", "group", "prefix"), [(1, "LG8000", "BG80"), (2, "LG9000", "BG90"), (3, "LG10000", "BG100")])
    def test_create_tandem_rs_load_cases(self, rs: int, group: str, prefix: str) -> None:
        """Test creation of tandem RS load case definitions for different RS values."""
        from src.loads.loadcase_helper_functions import tandem_system_sequencer

        length_bridgedeck = 50.0
        thickness_bridgedeck = 0.5

        definitions = create_tandem_rs_load_cases(rs, length_bridgedeck, thickness_bridgedeck)
        expected_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
        assert len(definitions) == len(expected_positions)

        assert definitions[0].group_name == group
        assert definitions[0].name.startswith(prefix)

        # Check the description of the first and last load case
        first_pos_str = f"{expected_positions[0]:g}"
        assert f"x = {first_pos_str} m" in definitions[0].description
        last_pos_str = f"{expected_positions[-1]:g}"
        assert f"x = {last_pos_str} m" in definitions[-1].description

    def test_invalid_rs_raises_value_error(self) -> None:
        """Test that invalid RS value raises ValueError."""
        with pytest.raises(ValueError):
            create_tandem_rs_load_cases(4, 50.0, 0.5)


if __name__ == "__main__":
    pytest.main([__file__])
