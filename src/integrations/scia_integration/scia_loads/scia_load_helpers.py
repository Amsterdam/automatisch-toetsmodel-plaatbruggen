"""
SCIA load helpers module.

This module provides common utilities and orchestration functions for SCIA load creation.
It includes the main load orchestration function and utility functions used across
different load types.
"""

from typing import Any

from src.integrations.scia_integration.model.scia_model_interface import SciaModelBuilder
from src.integrations.scia_integration.types import BridgeParametrization


def add_pedestrian_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
    _load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add pedestrian loads to the SCIA model.

    This is a placeholder function that will be implemented based on
    pedestrian area parameters when the requirements are defined.

    :param _builder: The SCIA model builder instance (unused)
    :type _builder: SciaModelBuilder
    :param _params: VIKTOR parameters for the bridge (unused)
    :type _params: Any
    :param _load_cases: Dictionary of created load cases (unused)
    :type _load_cases: dict[str, Any]
    :returns: Empty list (placeholder)
    :rtype: list[Any]
    """
    # This will be implemented based on pedestrian area parameters.
    return []


def create_all_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:
    """
    Create and apply all load types to the bridge model.

    This function orchestrates the application of all loads, including:
    - Material loads (asphalt, concrete fill, pavement, parapet, crowd)
    - Traffic loads (UDL, tandem system, service vehicle, accidental vehicle)
    - Pedestrian loads (placeholder)

    Loads are applied conditionally based on which load cases exist in the load_cases dictionary.

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases (may be empty for some categories)
    :type load_cases: dict[str, Any]
    :raises ValueError: When load creation fails
    """
    try:
        # Import load functions from their respective modules
        from .scia_point_loads import add_accidental_vehicle_loads, add_service_vehicle_loads, add_theoretical_tandem_loads, add_tram_loads
        from .scia_surface_loads import (
            add_asfalt_loads,
            add_concrete_fill_loads,
            add_crowd_loads,
            add_parapet_loads,
            add_pavement_loads,
            add_udl_loads,
        )

        # Apply material loads (these depend on dead_load_cases)
        if "dead_load_cases" in load_cases:
            add_asfalt_loads(builder, params, load_cases)
            add_concrete_fill_loads(builder, params, load_cases)
            add_pavement_loads(builder, params, load_cases)
            add_parapet_loads(builder, params, load_cases)
            add_crowd_loads(builder, params, load_cases)

        # Apply UDL traffic loads
        if "udl_traffic_cases" in load_cases:
            add_udl_loads(builder, params, load_cases)

        # Apply tandem system loads
        if "tandem_cases" in load_cases:
            add_theoretical_tandem_loads(builder, params, load_cases)

        # Apply service vehicle loads
        if "service_vehicle_cases" in load_cases:
            add_service_vehicle_loads(builder, params, load_cases)

        # Apply unintended vehicle loads
        if "unintended_vehicle_cases" in load_cases:
            add_accidental_vehicle_loads(builder, params, load_cases)

        # Apply tram loads
        if "tram_track_tandem_cases" in load_cases:
            add_tram_loads(builder, params, load_cases)

        # TODO: Add calls to other load functions when they are implemented
        # add_actual_tandem_loads(builder, params, load_cases)  # noqa: ERA001
        # add_railing_loads(builder, params, load_cases)  # noqa: ERA001
        # add_pedestrian_loads(builder, params, load_cases)  # noqa: ERA001

    except Exception as e:
        raise ValueError(f"Failed to create loads: {e}") from e
