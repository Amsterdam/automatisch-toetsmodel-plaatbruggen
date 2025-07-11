"""
Module for creating SCIA load definitions.

This module provides functions for creating definitions of SCIA loads, load cases, and load combinations.
These definitions are pure Python objects that can be used by the app layer to construct the actual SCIA model.
"""

from typing import Any

from src.integrations.scia_integration.scia_model_builder import SciaModelBuilder

from .scia_bridge_geometry import (
    convert_tandem_data_to_scia_format,
    generate_tandem_loads_for_bridge,
)
from .scia_load_cases import create_tandem_system_load_cases


def create_patch_surface_load(
    builder: SciaModelBuilder,
    case_name: str,
    plate_name: str,
    load_value: float,
) -> None:
    """
    Create a definition for a patch surface load on a plate.

    :param builder: The SCIA model builder.
    :param case_name: The name of the load case for this load.
    :param plate_name: The name of the plate to apply the load to.
    :param load_value: The value of the surface load.
    """
    builder.add_surface_load(
        name=f"Load_{case_name}_{plate_name}",
        case_name=case_name,
        plate_name=plate_name,
        value=load_value,
        direction="Z",
    )


def add_theoretical_tandem_loads(params: Any, builder: SciaModelBuilder, plate_names: list[str]) -> list[str]:
    """
    Generate and add theoretical tandem loads to the SCIA model.

    This function calculates tandem system loads based on bridge geometry,
    creates the necessary load cases, and applies the loads as surface loads
    to the corresponding plates.

    :param params: The VIKTOR parametrization object.
    :param builder: The SCIA model builder.
    :param plate_names: A list of all plate names in the model.
    :return: A list of the created tandem load case names.
    """
    tandem_cases = create_tandem_system_load_cases(builder)
    tandem_data = generate_tandem_loads_for_bridge(params)
    scia_tandem_data = convert_tandem_data_to_scia_format(tandem_data)

    for tandem_load in scia_tandem_data:
        case_name = tandem_load["load_case"]
        plate_name = tandem_load["plate_name"]

        if plate_name in plate_names:
            create_patch_surface_load(
                builder=builder,
                case_name=case_name,
                plate_name=plate_name,
                load_value=tandem_load["load_value"],
            )
    return tandem_cases


"""Add actual tandem loads based on user-defined lanes."""


def add_actual_tandem_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _traffic_group: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add actual tandem loads based on user-defined lanes."""
    # TODO: Implement logic for actual tandem loads
    # - Extract actual lane positions from params
    # - Generate tandem loads for those lanes
    # - Apply to model
    return []


"""Add railing loads to the SCIA model."""


def add_railing_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _permanent_group: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add railing loads to the SCIA model."""
    # TODO: Implement railing load application
    # - Get railing positions from geometry
    # - Apply line loads along railing paths
    return []


"""Add pedestrian loads to the SCIA model."""


def add_pedestrian_loads(
    _model: Any,  # noqa: ANN401
    _params: Any,  # noqa: ANN401
    _traffic_group: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add pedestrian loads to the SCIA model."""
    # TODO: Implement pedestrian load application
    # - Get pedestrian zone polygons
    # - Apply surface loads to pedestrian areas
    return []
