"""
SCIA load cases utility module.

This module provides functions for creating definitions of standard SCIA load cases.
These definitions are pure Python objects that can be used by the app layer to
construct the actual SCIA model.
"""

from typing import Literal

from src.integrations.scia_integration.scia_model_builder import SciaModelBuilder
from src.loads.loadcase_helper_functions import tandem_system_sequencer


def create_load_case(
    builder: SciaModelBuilder,
    group_name: str,
    case_name: str,
    description: str,
    case_type: Literal["PERMANENT", "VARIABLE"],
    **kwargs: str,
) -> None:
    """
    Create a definition for a SCIA load case.

    :param builder: The SCIA model builder.
    :param group_name: Name of the load group this case belongs to.
    :param case_name: Name for the load case.
    :param description: Description of the load case.
    :param case_type: Type of the load case ("PERMANENT" or "VARIABLE").
    """
    builder.add_load_case(
        name=case_name,
        description=description,
        case_type=case_type,
        group_name=group_name,
        **kwargs,
    )


def create_self_weight_load_case(builder: SciaModelBuilder) -> None:
    """
    Create a definition for the self-weight load case.

    :param builder: The SCIA model builder.
    """
    create_load_case(
        builder,
        group_name="LG1000",
        case_name="BG1001",
        description="Self-weight",
        case_type="PERMANENT",
        action_type="PERMANENT_G",
    )


def create_dead_load_case(builder: SciaModelBuilder) -> None:
    """
    Create a definition for the dead load case.

    :param builder: The SCIA model builder.
    """
    create_load_case(
        builder,
        group_name="LG1001",
        case_name="BG1002",
        description="Dead load",
        case_type="PERMANENT",
        action_type="PERMANENT_G",
    )


def create_tandem_system_load_cases(builder: SciaModelBuilder) -> list[str]:
    """
    Create load cases for each tandem system based on the sequence.

    :param builder: The SCIA model builder.
    :return: A list of the created load case names.
    """
    tandem_load_cases = []
    for tandem_system in tandem_system_sequencer():
        case_name = f"TS{tandem_system['id']}"
        description = f"Tandem System: {tandem_system['name']} - Lane: {tandem_system['lane_number']}"
        create_load_case(
            builder,
            group_name="LG2",
            case_name=case_name,
            description=description,
            case_type="VARIABLE",
        )
        tandem_load_cases.append(case_name)
    return tandem_load_cases


def create_all_standard_load_cases(builder: SciaModelBuilder) -> None:
    """
    Create definitions for all standard load cases.

    :param builder: The SCIA model builder.
    """
    create_self_weight_load_case(builder)
    create_dead_load_case(builder)
    create_tandem_system_load_cases(builder)
