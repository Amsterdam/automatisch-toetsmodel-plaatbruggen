"""
Tests for SCIA load group definitions.

This module tests the creation of SCIA load group definitions by mocking the SciaModelBuilder.
"""

from unittest.mock import Mock

from src.integrations.scia_integration.load_system.scia_load_group import (
    create_accidental_vehicle_group,
    create_all_load_groups,
    create_crowd_load_group,
    create_dead_load_group,
    create_permanent_load_group,
    create_service_vehicle_group,
    create_temperature_group,
    create_ts_lane_1_group,
    create_ts_lane_2_group,
    create_ts_lane_3_group,
    create_udl_group,
)
from src.integrations.scia_integration.scia_enums import (
    LoadGroupLoadType,
    LoadGroupOption,
    LoadGroupRelation,
)


class TestLoadGroupCreation:
    """Tests for creating individual load group definitions."""

    def test_create_permanent_load_group(self) -> None:
        """Test the permanent load group definition."""
        builder = Mock()
        create_permanent_load_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG1000 - Permanent",
            load_option=LoadGroupOption.PERMANENT,
            relation=LoadGroupRelation.STANDARD,
            load_type=None,
        )

    def test_create_dead_load_group(self) -> None:
        """Test the dead load group definition."""
        builder = Mock()
        create_dead_load_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG2000 - Rustende belasting",
            load_option=LoadGroupOption.PERMANENT,
            relation=LoadGroupRelation.STANDARD,
            load_type=None,
        )

    def test_create_temperature_group(self) -> None:
        """Test the temperature load group definition."""
        builder = Mock()
        create_temperature_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG3000 - Temperatuur",
            load_option=LoadGroupOption.VARIABLE,
            relation=LoadGroupRelation.EXCLUSIVE,
            load_type=LoadGroupLoadType.TEMPERATURE,
        )

    def test_create_udl_group(self) -> None:
        """Test the UDL load group definition."""
        builder = Mock()
        create_udl_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG4000 - UDL",
            load_option=LoadGroupOption.VARIABLE,
            relation=LoadGroupRelation.STANDARD,
            load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
        )

    def test_create_crowd_load_group(self) -> None:
        """Test the crowd load group definition."""
        builder = Mock()
        create_crowd_load_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG5000 - Mensenmenigte",
            load_option=LoadGroupOption.VARIABLE,
            relation=LoadGroupRelation.EXCLUSIVE,
            load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
        )

    def test_create_service_vehicle_group(self) -> None:
        """Test the service vehicle load group definition."""
        builder = Mock()
        create_service_vehicle_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG6000 - Dienstvoertuig",
            load_option=LoadGroupOption.VARIABLE,
            relation=LoadGroupRelation.EXCLUSIVE,
            load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
        )

    def test_create_accidental_vehicle_group(self) -> None:
        """Test the accidental vehicle load group definition."""
        builder = Mock()
        create_accidental_vehicle_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG7000 - Onbedoeld voertuig",
            load_option=LoadGroupOption.VARIABLE,
            relation=LoadGroupRelation.EXCLUSIVE,
            load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
        )

    def test_create_ts_lane_1_group(self) -> None:
        """Test the TS lane 1 load group definition."""
        builder = Mock()
        create_ts_lane_1_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG8000 - TS rijstrook 1",
            load_option=LoadGroupOption.VARIABLE,
            relation=LoadGroupRelation.EXCLUSIVE,  # Tandem loads are mutually exclusive
            load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
        )

    def test_create_ts_lane_2_group(self) -> None:
        """Test the TS lane 2 load group definition."""
        builder = Mock()
        create_ts_lane_2_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG9000 - TS rijstrook 2",
            load_option=LoadGroupOption.VARIABLE,
            relation=LoadGroupRelation.EXCLUSIVE,  # Tandem loads are mutually exclusive
            load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
        )

    def test_create_ts_lane_3_group(self) -> None:
        """Test the TS lane 3 load group definition."""
        builder = Mock()
        create_ts_lane_3_group(builder)
        builder.create_load_group.assert_called_once_with(
            name="LG10000 - TS rijstrook 3",
            load_option=LoadGroupOption.VARIABLE,
            relation=LoadGroupRelation.EXCLUSIVE,  # Tandem loads are mutually exclusive
            load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
        )


class TestAllLoadGroups:
    """Tests for the helper function that creates all load groups."""

    def test_create_all_load_groups_calls(self) -> None:
        """Test that all individual creation functions are called."""
        builder = Mock()
        result = create_all_load_groups(builder)

        # Check that the builder was called 12 times (added tram track groups)
        assert builder.create_load_group.call_count == 12
        # Check that the result dictionary has 12 entries
        assert len(result) == 12
        assert "permanent_self_weight" in result
        assert "ts_lane_3" in result

    def test_create_all_load_groups_return_structure(self) -> None:
        """Test that the function returns the expected dictionary structure."""
        builder = Mock()
        definitions = create_all_load_groups(builder)
        expected_keys = [
            "permanent_self_weight",
            "dead_load",
            "temperature",
            "udl",
            "crowd",
            "service_vehicle",
            "accidental_vehicle",
            "ts_lane_1",
            "ts_lane_2",
            "ts_lane_3",
            "ts_tram_track_1",
            "ts_tram_track_2",
        ]
        assert list(definitions.keys()) == expected_keys
        # Check if returned values are the mock's return values
        assert definitions["permanent_self_weight"] == builder.create_load_group.return_value
