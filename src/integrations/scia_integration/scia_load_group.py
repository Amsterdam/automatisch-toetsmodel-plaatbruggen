"""
Module for creating SCIA load group definitions.

These functions generate LoadGroupDefinition objects, which serve as pure Python blueprints for creating actual SCIA load groups in the app layer.
This keeps this module independent of the VIKTOR SDK.
"""

from typing import Any, TypeAlias

from .scia_definitions import LoadGroupDefinition

# Type alias for SCIA model object (kept for type hinting consistency in higher-level functions)
SciaModel: TypeAlias = Any


def create_permanent_load_group() -> LoadGroupDefinition:
    """
    Create definition for permanent load group LG1.

    :returns: Definition for the permanent load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG1",
        load_option="PERMANENT",
        relation="STANDARD",
        load_type="CAT_G",  # Category G: Storage and industrial areas
    )


def create_traffic_load_group() -> LoadGroupDefinition:
    """
    Create definition for traffic load group LG2.

    :returns: Definition for the traffic load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG2",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="VARIABLE_LOADS",
    )


def create_wind_load_group() -> LoadGroupDefinition:
    """
    Create definition for wind load group LG3.

    :returns: Definition for the wind load group.
    :rtype: LoadGroupDefinition
    """
    return LoadGroupDefinition(
        name="LG3",
        load_option="VARIABLE",
        relation="STANDARD",
        load_type="VARIABLE_LOADS",
    )


def create_basic_load_groups() -> dict[str, LoadGroupDefinition]:
    """
    Create all basic load group definitions for bridge analysis.

    :returns: Dictionary of basic load group definitions.
    :rtype: dict[str, LoadGroupDefinition]
    """
    return {
        "permanent": create_permanent_load_group(),
        "traffic": create_traffic_load_group(),
        "wind": create_wind_load_group(),
    }
