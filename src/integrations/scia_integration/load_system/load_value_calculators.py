"""
Load value calculation utilities for bridge load analysis.

This module provides functions for calculating load values including tandem loads,
UDL values, and pavement loads based on design codes and material properties.
"""

from typing import TYPE_CHECKING, Any

from src.combinations.load_factors import get_alpha_q_nen_en_1991_2, get_alpha_trend_nen_8701, get_psi_nen_8701
from src.common.constants import SIGNAGE_LOAD_FACTORS
from src.common.materials import get_material_densities
from src.integrations.scia_integration.constants.loads import (
    ALPHA_Q_ONDERLIGGEND,
    NOBS_DEFAULT,
    SIGNAGE_WEIGHT_OPTIONS,
    TANDEM_CONTACT_AREA_SIDE,
    TANDEM_LOAD_BASE_MAIN,
    TANDEM_LOAD_BASE_SECOND,
    TANDEM_LOAD_BASE_THIRD,
)
from src.integrations.scia_integration.load_system.lane_calculations import get_reference_period

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


def calculate_theoretical_tandem_values(
    params: "BridgeParametrization",
    length_bridgedeck: float,
) -> tuple[float, float, float]:
    """
    Calculate theoretical tandem values using standard alpha_q factors.

    This function calculates tandem loads for theoretical lane positions
    using the standard NEN-EN 1991-2 alpha_q adjustment factors. All required
    load factors (psi, alpha_trend, alpha_q) are calculated internally.

    :param params: Bridge parameters containing reference period information
    :type params: BridgeParametrization
    :param length_bridgedeck: Length of the bridge deck in meters
    :type length_bridgedeck: float
    :returns: Tuple of (load_main, load_second, load_third) in N/m²
    :rtype: tuple[float, float, float]
    """
    # Calculate required factors
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]

    # Calculate load values
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    load_main = TANDEM_LOAD_BASE_MAIN / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = TANDEM_LOAD_BASE_SECOND / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = TANDEM_LOAD_BASE_THIRD / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor

    return load_main, load_second, load_third


def calculate_real_tandem_values(
    params: "BridgeParametrization",
    length_bridgedeck: float,
) -> tuple[float, float, float]:
    """
    Calculate tandem values based on berekeningsniveau and other factors.

    This function calculates tandem loads for real lane positions based on
    the calculation level (berekeningsniveau). All required load factors
    (psi, alpha_trend, alpha_q) are calculated internally.

    :param params: Bridge parameters containing berekeningsniveau and signage settings
    :type params: BridgeParametrization
    :param length_bridgedeck: Length of the bridge deck in meters
    :type length_bridgedeck: float
    :returns: Tuple of (load_main, load_second, load_third) in N/m²
    :rtype: tuple[float, float, float]
    """
    # Calculate required factors
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))

    # Calculate base load values
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    base_main = TANDEM_LOAD_BASE_MAIN / contact_area
    base_second = TANDEM_LOAD_BASE_SECOND / contact_area
    base_third = TANDEM_LOAD_BASE_THIRD / contact_area

    if params.berekeningsniveau == "Werkelijke wegindeling":
        alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]
        load_main = base_main * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
        load_second = base_second * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
        load_third = base_third * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    elif params.berekeningsniveau == "Werkelijke wegindeling onderliggend wegennet":
        alpha_q_factor = ALPHA_Q_ONDERLIGGEND
        load_main = base_main * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
        load_second = base_second * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
        load_third = base_third * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    elif params.berekeningsniveau == "Werkelijke wegindeling met bebording":
        signage_index = SIGNAGE_WEIGHT_OPTIONS.index(params.signage)
        load_factor = SIGNAGE_LOAD_FACTORS[signage_index]
        load_main = base_main * load_factor
        load_second = base_second * load_factor
        load_third = base_third * load_factor
    else:  # Fallback for safety
        load_main = base_main
        load_second = base_second
        load_third = base_third

    return load_main, load_second, load_third


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
