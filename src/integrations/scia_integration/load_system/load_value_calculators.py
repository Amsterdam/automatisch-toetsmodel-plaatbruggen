"""
Load value calculation utilities for bridge load analysis.

This module provides functions for calculating load values including tandem loads,
UDL values, and pavement loads based on design codes and material properties.
"""

from typing import TYPE_CHECKING, Any

from src.combinations.load_factors import get_alpha_q_nen_en_1991_2
from src.common.constants import SIGNAGE_LOAD_FACTORS
from src.common.materials import get_material_densities
from src.integrations.scia_integration.constants.loads import (
    ALPHA_Q_MAIN_LANE_ONDERLIGGEND,
    ALPHA_Q_ONDERLIGGEND,
    ALPHA_Q_OTHER_LANE_ONDERLIGGEND,
    NOBS_DEFAULT,
    SIGNAGE_WEIGHT_OPTIONS,
    TANDEM_CONTACT_AREA_SIDE,
    TANDEM_LOAD_BASE_MAIN,
    TANDEM_LOAD_BASE_SECOND,
    TANDEM_LOAD_BASE_THIRD,
    UDL_OTHER_LANE_VALUE,
    UDL_REST_AREA_VALUE,
)

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


def calculate_real_tandem_values(
    params: "BridgeParametrization",
    length_bridgedeck: float,
    psi_nen_8701_factor: float,
    alpha_trend_factor: float,
) -> tuple[float, float, float]:
    """
    Calculate tandem values based on berekeningsniveau and other factors.

    :param params: Bridge parameters containing berekeningsniveau and signage settings
    :param length_bridgedeck: Length of the bridge deck
    :param psi_nen_8701_factor: NEN 8701 factor
    :param alpha_trend_factor: Alpha trend factor from NEN 8701
    :returns: Tuple of (load_main, load_second, load_third)
    """
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


def calculate_real_udl_values(
    params: "BridgeParametrization",
    length_bridgedeck: float,
    udl_value: float,
    psi_nen_8701_factor: float,
    alpha_trend_factor: float,
) -> tuple[float, float, float]:
    """
    Calculate UDL values based on berekeningsniveau and other factors.

    :param params: Bridge parameters containing berekeningsniveau and signage settings
    :param length_bridgedeck: Length of the bridge deck
    :param udl_value: Base UDL value
    :param psi_nen_8701_factor: NEN 8701 factor
    :param alpha_trend_factor: Alpha trend factor from NEN 8701
    :returns: Tuple of (main_value, other_value, rest_value)
    """
    if params.berekeningsniveau == "Werkelijke wegindeling":
        alpha_q_factors = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)
        main_value = udl_value * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
        other_value = UDL_OTHER_LANE_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
        rest_value = UDL_REST_AREA_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
    elif params.berekeningsniveau == "Werkelijke wegindeling onderliggend wegennet":
        alpha_q_factors = [ALPHA_Q_MAIN_LANE_ONDERLIGGEND, ALPHA_Q_OTHER_LANE_ONDERLIGGEND]
        main_value = udl_value * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
        other_value = UDL_OTHER_LANE_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
        rest_value = UDL_REST_AREA_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
    elif params.berekeningsniveau == "Werkelijke wegindeling met bebording":
        # Get the selected signage option and map to load factor
        signage_index = SIGNAGE_WEIGHT_OPTIONS.index(params.signage)
        load_factor = SIGNAGE_LOAD_FACTORS[signage_index]
        # Apply the load factor to all values
        main_value = udl_value * load_factor
        other_value = UDL_OTHER_LANE_VALUE
        rest_value = UDL_REST_AREA_VALUE
    else:  # Fallback for safety
        main_value = udl_value
        other_value = UDL_OTHER_LANE_VALUE
        rest_value = UDL_REST_AREA_VALUE

    return main_value, other_value, rest_value


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
