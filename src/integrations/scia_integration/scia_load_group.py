"""
Module for creating SCIA load group definitions.

These functions generate LoadGroupDefinition objects, which serve as pure Python blueprints for creating actual SCIA load groups in the app layer.
This keeps this module independent of the VIKTOR SDK.
"""

from .scia_definitions import LoadGroupDefinition


def create_permanent_load_group() -> LoadGroupDefinition:
    """
    Create definition for permanent load group LG1000 (Self-weight).

    :returns: Definition for the permanent load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG1000",
        load_option="PERMANENT",
        relation="STANDARD",
        load_type=None,
    )


def create_dead_load_group() -> LoadGroupDefinition:
    """
    Create definition for dead load group LG2000 (Resting loads).

    :returns: Definition for the dead load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG2000",
        load_option="PERMANENT",
        relation="STANDARD",
        load_type=None,
    )


def create_temperature_group() -> LoadGroupDefinition:
    """
    Create definition for temperature load group LG3000.

    :returns: Definition for the temperature load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG3000",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="TEMPERATURE",
    )


def create_udl_group() -> LoadGroupDefinition:
    """
    Create definition for UDL traffic load group LG4000.

    :returns: Definition for the UDL traffic group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG4000",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="CONSTRUCTION_LOADS",
    )


def create_crowd_load_group() -> LoadGroupDefinition:
    """
    Create definition for crowd load group LG5000 (LM4).

    :returns: Definition for the crowd load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG5000",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="CONSTRUCTION_LOADS",
    )


def create_service_vehicle_group() -> LoadGroupDefinition:
    """
    Create definition for service vehicle load group LG6000.

    :returns: Definition for the service vehicle load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG6000",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="CONSTRUCTION_LOADS",
    )


def create_accidental_vehicle_group() -> LoadGroupDefinition:
    """
    Create definition for accidental vehicle load group LG7000.

    :returns: Definition for the accidental vehicle load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG7000",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="CONSTRUCTION_LOADS",
    )


def create_ts_lane_1_group() -> LoadGroupDefinition:
    """
    Create definition for Tandem System lane 1 load group LG8000.

    :returns: Definition for the TS lane 1 load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG8000",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="CONSTRUCTION_LOADS",
    )


def create_ts_lane_2_group() -> LoadGroupDefinition:
    """
    Create definition for Tandem System lane 2 load group LG9000.

    :returns: Definition for the TS lane 2 load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG9000",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="CONSTRUCTION_LOADS",
    )


def create_ts_lane_3_group() -> LoadGroupDefinition:
    """
    Create definition for Tandem System lane 3 load group LG10000.

    :returns: Definition for the TS lane 3 load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG10000",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="CONSTRUCTION_LOADS",
    )


def create_all_load_groups() -> dict[str, LoadGroupDefinition]:
    """
    Create all basic load group definitions for bridge analysis.

    :returns: Dictionary of all load group definitions.
    :rtype: dict[str, LoadGroupDefinition]
    """
    return {
        "permanent_self_weight": create_permanent_load_group(),
        "permanent_other": create_dead_load_group(),
        "temperature": create_temperature_group(),
        "udl": create_udl_group(),
        "crowd": create_crowd_load_group(),
        "service_vehicle": create_service_vehicle_group(),
        "accidental_vehicle": create_accidental_vehicle_group(),
        "ts_lane_1": create_ts_lane_1_group(),
        "ts_lane_2": create_ts_lane_2_group(),
        "ts_lane_3": create_ts_lane_3_group(),
    }
