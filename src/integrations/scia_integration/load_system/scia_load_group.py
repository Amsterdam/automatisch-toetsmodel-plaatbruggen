"""
Module for creating SCIA load groups.

These functions call the SciaModelBuilder to directly construct SCIA load groups.
This keeps this module independent of the VIKTOR SDK by programming against an interface.
"""

from src.integrations.scia_integration.model.scia_model_interface import SciaLoadGroup, SciaModelBuilder
from src.integrations.scia_integration.scia_enums import (
    LoadGroupLoadType,
    LoadGroupOption,
    LoadGroupRelation,
)


def create_permanent_load_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the permanent load group LG1000 (Self-weight).

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG1000 - Permanent",
        load_option=LoadGroupOption.PERMANENT,
        relation=LoadGroupRelation.STANDARD,
        load_type=None,
    )


def create_dead_load_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the dead load group LG2000 (Resting loads).

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG2000 - Rustende belasting",
        load_option=LoadGroupOption.PERMANENT,
        relation=LoadGroupRelation.STANDARD,
        load_type=None,
    )


def create_temperature_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the temperature load group LG3000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG3000 - Temperatuur",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.TEMPERATURE,
    )


def create_udl_conf_a_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the UDL configuration A load group LG4000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG4000 - UDL - conf. A",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.STANDARD,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_udl_conf_b_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the UDL configuration B load group LG4001.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG4001 - UDL - conf. B",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.STANDARD,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_udl_conf_c_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the UDL configuration C load group LG4002.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG4002 - UDL - conf. C",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.STANDARD,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_crowd_load_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the crowd load group LG5000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG5000 - Mensenmenigte",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_service_vehicle_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the service vehicle load group LG6000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG6000 - Dienstvoertuig",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_accidental_vehicle_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the accidental vehicle load group LG7000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG7000 - Onbedoeld voertuig",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_ts_lane_1_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the Tandem System lane 1 load group LG8000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG8000 - TS rijstrook 1",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_ts_lane_2_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the Tandem System lane 2 load group LG9000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG9000 - TS rijstrook 2",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_ts_lane_3_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the Tandem System lane 3 load group LG10000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG10000 - TS rijstrook 3",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_tram_track_1_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the Tandem System for tram track 1 load group LG11000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG11000 - TS tramspoor 1",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_tram_track_2_group(builder: SciaModelBuilder) -> SciaLoadGroup:
    """
    Create the Tandem System for tram track 2 load group LG12000.

    :param builder: The SCIA model builder instance.
    :return: The created SCIA load group.
    """
    return builder.create_load_group(
        name="LG12000 - TS tramspoor 2",
        load_option=LoadGroupOption.VARIABLE,
        relation=LoadGroupRelation.EXCLUSIVE,
        load_type=LoadGroupLoadType.CONSTRUCTION_LOADS,
    )


def create_all_load_groups(builder: SciaModelBuilder) -> dict[str, SciaLoadGroup]:
    """
    Create all basic load groups for bridge analysis using the builder.

    :param builder: The SCIA model builder instance.
    :returns: Dictionary of all created load group objects.
    :rtype: dict[str, SciaLoadGroup]
    """
    return {
        "permanent_self_weight": create_permanent_load_group(builder),
        "dead_load": create_dead_load_group(builder),
        "temperature": create_temperature_group(builder),
        "udl_conf_a": create_udl_conf_a_group(builder),
        "udl_conf_b": create_udl_conf_b_group(builder),
        "udl_conf_c": create_udl_conf_c_group(builder),
        "crowd": create_crowd_load_group(builder),
        "service_vehicle": create_service_vehicle_group(builder),
        "accidental_vehicle": create_accidental_vehicle_group(builder),
        "ts_lane_1": create_ts_lane_1_group(builder),
        "ts_lane_2": create_ts_lane_2_group(builder),
        "ts_lane_3": create_ts_lane_3_group(builder),
        "ts_tram_track_1": create_tram_track_1_group(builder),
        "ts_tram_track_2": create_tram_track_2_group(builder),
    }
