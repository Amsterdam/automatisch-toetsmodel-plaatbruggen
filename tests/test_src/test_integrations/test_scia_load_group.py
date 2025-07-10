"""
Tests for SCIA load group definitions.

This module tests the creation of SCIA load group definitions.
"""

from unittest.mock import Mock, patch

from src.integrations.scia_integration.scia_definitions import LoadGroupDefinition
from src.integrations.scia_integration.scia_load_group import (
    create_accidental_vehicle_group,
    create_all_load_groups,
    create_crowd_load_group,
    create_dead_load_group,
    create_permanent_group,
    create_service_vehicle_group,
    create_temperature_group,
    create_ts_lane_1_group,
    create_ts_lane_2_group,
    create_ts_lane_3_group,
    create_udl_group,
)


class TestLoadGroupCreation:
    """Tests for creating individual load group definitions."""

    def test_create_permanent_group(self) -> None:
        """Test the permanent load group definition."""
        definition = create_permanent_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG1000"
        assert definition.load_option == "PERMANENT"
        assert definition.relation == "STANDARD"
        assert definition.load_type is None

    def test_create_dead_load_group(self) -> None:
        """Test the dead load group definition."""
        definition = create_dead_load_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG2000"
        assert definition.load_option == "PERMANENT"
        assert definition.relation == "STANDARD"
        assert definition.load_type is None

    def test_create_temperature_group(self) -> None:
        """Test the temperature load group definition."""
        definition = create_temperature_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG3000"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "EXCLUSIVE"
        assert definition.load_type == "TEMPERATURE"

    def test_create_udl_group(self) -> None:
        """Test the UDL load group definition."""
        definition = create_udl_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG4000"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "STANDARD"
        assert definition.load_type == "CONSTRUCTION_LOADS"

    def test_create_crowd_load_group(self) -> None:
        """Test the crowd load group definition."""
        definition = create_crowd_load_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG5000"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "EXCLUSIVE"
        assert definition.load_type == "CONSTRUCTION_LOADS"

    def test_create_service_vehicle_group(self) -> None:
        """Test the service vehicle load group definition."""
        definition = create_service_vehicle_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG6000"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "EXCLUSIVE"
        assert definition.load_type == "CONSTRUCTION_LOADS"

    def test_create_accidental_vehicle_group(self) -> None:
        """Test the accidental vehicle load group definition."""
        definition = create_accidental_vehicle_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG7000"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "EXCLUSIVE"
        assert definition.load_type == "CONSTRUCTION_LOADS"

    def test_create_ts_lane_1_group(self) -> None:
        """Test the TS lane 1 load group definition."""
        definition = create_ts_lane_1_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG8000"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "EXCLUSIVE"
        assert definition.load_type == "CONSTRUCTION_LOADS"

    def test_create_ts_lane_2_group(self) -> None:
        """Test the TS lane 2 load group definition."""
        definition = create_ts_lane_2_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG9000"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "EXCLUSIVE"
        assert definition.load_type == "CONSTRUCTION_LOADS"

    def test_create_ts_lane_3_group(self) -> None:
        """Test the TS lane 3 load group definition."""
        definition = create_ts_lane_3_group()
        assert isinstance(definition, LoadGroupDefinition)
        assert definition.name == "LG10000"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "EXCLUSIVE"
        assert definition.load_type == "CONSTRUCTION_LOADS"


class TestAllLoadGroups:
    """Tests for the helper function that creates all load groups."""

    def test_create_all_load_groups_calls(self) -> None:
        """Test that all individual creation functions are called."""
        import src.integrations.scia_integration.scia_load_group as load_group_module

        group_creators = {
            "permanent": "create_permanent_group",
            "dead_load": "create_dead_load_group",
            "temperature": "create_temperature_group",
            "udl": "create_udl_group",
            "crowd": "create_crowd_load_group",
            "service_vehicle": "create_service_vehicle_group",
            "accidental_vehicle": "create_accidental_vehicle_group",
            "ts_lane_1": "create_ts_lane_1_group",
            "ts_lane_2": "create_ts_lane_2_group",
            "ts_lane_3": "create_ts_lane_3_group",
        }

        with patch.multiple(load_group_module, **{name: Mock() for name in group_creators.values()}) as mocks:
            for mock_func in mocks.values():
                mock_func.return_value = Mock(spec=LoadGroupDefinition)

            definitions = create_all_load_groups()

            for key, creator_name in group_creators.items():
                assert key in definitions
                mocks[creator_name].assert_called_once()
                assert definitions[key] is mocks[creator_name].return_value
            assert len(definitions) == len(group_creators)

    def test_create_all_load_groups_return_structure(self) -> None:
        """Test that the function returns the expected dictionary structure."""
        definitions = create_all_load_groups()
        expected_keys = [
            "permanent",
            "dead_load",
            "temperature",
            "udl",
            "crowd",
            "service_vehicle",
            "accidental_vehicle",
            "ts_lane_1",
            "ts_lane_2",
            "ts_lane_3",
        ]
        assert list(definitions.keys()) == expected_keys
        for key in expected_keys:
            assert isinstance(definitions[key], LoadGroupDefinition)
