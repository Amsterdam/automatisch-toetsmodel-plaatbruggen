"""
Load value calculation utilities for bridge load analysis.

This module provides functions for calculating load values including tandem loads,
UDL values, and pavement loads based on design codes and material properties.
"""

from typing import TYPE_CHECKING, Any

from src.common.materials import get_material_densities
from src.integrations.scia_integration.constants.loads import (
    TANDEM_CONTACT_AREA_SIDE,
    TANDEM_LOAD_BASE_VALUE,
)

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


def calculate_theoretical_tandem_values(
    params: "BridgeParametrization",  # noqa: ARG001
    length_bridgedeck: float,  # noqa: ARG001
) -> float:
    """
    Calculate theoretical tandem base load (per unit area).

    In the new system, all tandem loads use the same base value (100 kN = 625000 N/m²).
    Lane-specific factors and dynamic factors (psi, alpha_trend, alpha_q) are applied
    at the load combination stage, not here.

    :param params: Bridge parameters (unused, kept for API compatibility)
    :type params: BridgeParametrization
    :param length_bridgedeck: Length of the bridge deck (unused, kept for API compatibility)
    :type length_bridgedeck: float
    :returns: Base load value in N/m² (same for all tandem lanes)
    :rtype: float
    """
    # Convert base load (N) to load per unit area (N/m²)
    return TANDEM_LOAD_BASE_VALUE / (TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE)


def calculate_real_tandem_values(
    params: "BridgeParametrization",  # noqa: ARG001
    length_bridgedeck: float,  # noqa: ARG001
) -> float:
    """
    Calculate real tandem base load (per unit area).

    In the new system, all tandem loads use the same base value (100 kN = 625000 N/m²).
    Lane-specific factors and dynamic factors (psi, alpha_trend, alpha_q) are applied
    at the load combination stage, not here.

    :param params: Bridge parameters (unused, kept for API compatibility)
    :type params: BridgeParametrization
    :param length_bridgedeck: Length of the bridge deck (unused, kept for API compatibility)
    :type length_bridgedeck: float
    :returns: Base load value in N/m² (same for all tandem lanes)
    :rtype: float
    """
    # Convert base load (N) to load per unit area (N/m²)
    return TANDEM_LOAD_BASE_VALUE / (TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE)


def calculate_pavement_load_from_dynamic_array(
    load_zones_array: list[dict[str, Any]],
    thickness_field: str = "pavement_thickness",
    material_field: str = "pavement_material",
) -> list[float]:
    """
    Calculate the load (kN/m²) for each row in the load zones dynamic array.

    :param load_zones_array: List of dicts from the Belastingzones DynamicArray (params.load_zones_data_array)
    :type load_zones_array: list[dict[str, Any]]
    :param thickness_field: Name of the thickness field in each row (default: "pavement_thickness")
    :type thickness_field: str
    :param material_field: Name of the material field in each row (default: "pavement_material")
    :type material_field: str
    :returns: List of calculated loads (kN/m²) for each row (0.0 if missing or unknown material)
    :rtype: list[float]
    """
    # Build a lookup for material densities (case-insensitive)
    density_lookup = {name.lower(): density for name, density in get_material_densities()}
    result: list[float] = []
    for row in load_zones_array:
        thickness = row.get(thickness_field, 0.0)
        material = row.get(material_field, "")
        if not material or not isinstance(thickness, int | float):
            result.append(0.0)
            continue
        density = density_lookup.get(str(material).lower(), 0.0)
        load = thickness * density if density > 0 and thickness > 0 else 0.0
        result.append(load)
    return result


def calculate_pavement_load_from_material(
    thickness: float,
    material: str,
) -> float:
    """
    Calculate the pavement load (kN/m²) from the material properties.

    :param thickness: Pavement thickness in meters
    :type thickness: float
    :param material: Pavement material name
    :type material: str
    :returns: Calculated load (kN/m²) (0.0 if missing or unknown material)
    :rtype: float
    """
    # Build a lookup for material densities (case-insensitive)
    density_lookup = {name.lower(): density for name, density in get_material_densities()}

    if not material or not isinstance(thickness, int | float):
        return 0.0

    density = density_lookup.get(str(material).lower(), 0.0)
    return thickness * density if density > 0 and thickness > 0 else 0.0
