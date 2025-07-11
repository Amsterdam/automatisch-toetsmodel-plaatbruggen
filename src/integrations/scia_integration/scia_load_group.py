"""
Module for creating SCIA load groups.

These functions generate LoadGroupDefinition objects, which serve as pure Python blueprints for creating actual SCIA load groups in the app layer.
This keeps this module independent of the VIKTOR SDK.
"""

from .scia_model_builder import SciaModelBuilder


def create_permanent_load_group(builder: SciaModelBuilder) -> None:
    """
    Create definition for permanent load group LG1000 (Self-weight).

    :param builder: The SCIA model builder.
    """
    builder.add_load_group(
        name="LG1000",
        load_option="PERMANENT",
        relation="STANDARD",
        load_type=None,
    )


def create_dead_load_group(builder: SciaModelBuilder) -> None:
    """
    Create definition for dead load group LG1001.

    :param builder: The SCIA model builder.
    """
    builder.add_load_group(
        name="LG1001",
        load_option="PERMANENT",
        relation="STANDARD",
        load_type=None,
    )


def create_variable_load_group_q(builder: SciaModelBuilder) -> None:
    """
    Create definition for variable load group LG1 (Q).

    :param builder: The SCIA model builder.
    """
    builder.add_load_group(
        name="LG1",
        load_option="VARIABLE",
        relation="TOGETHER",
        load_type="CAT_G_TRAFFIC_ROAD",
    )


def create_variable_load_group_tandem(builder: SciaModelBuilder) -> None:
    """
    Create definition for variable load group LG2 (Tandem).

    :param builder: The SCIA model builder.
    """
    builder.add_load_group(
        name="LG2",
        load_option="VARIABLE",
        relation="EXCLUSIVE",
        load_type="CAT_G_TRAFFIC_ROAD",
    )


def create_all_load_groups(builder: SciaModelBuilder) -> None:
    """
    Create definitions for all standard load groups.

    :param builder: The SCIA model builder.
    """
    create_permanent_load_group(builder)
    create_dead_load_group(builder)
    create_variable_load_group_q(builder)
    create_variable_load_group_tandem(builder)
