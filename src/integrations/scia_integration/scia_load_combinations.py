"""
SCIA load combinations utility module.

This module provides utilities for creating and managing definitions for load combinations in SCIA Engineer.

.. warning::
    The load combination factors and logic implemented in this module are simplified placeholders for architectural and demonstration purposes.
    They are **not** based on official Eurocode or NEN standards.
    A future task is to implement correct, configurable load combination logic based on relevant engineering codes (e.g., NEN 8700/8701).
"""

from typing import Any

from .scia_definitions import LoadCombinationDefinition, SciaCombinationType

# Type aliases for SCIA objects
SciaModel = Any
SciaLoadCase = Any
SciaLoadCombination = Any


def create_load_combination(
    combination_type: SciaCombinationType,
    combination_name: str,
    load_case_factors: dict[str, float],
    description: str = "",
) -> LoadCombinationDefinition:
    """
    Create a definition for a SCIA load combination.

    :param combination_type: "ULS", "SLS_CHAR", etc.
    :param combination_name: Name for the combination.
    :param load_case_factors: Dictionary mapping load case names to their factors.
    :param description: Optional description.
    :return: A LoadCombinationDefinition object.
    :rtype: LoadCombinationDefinition
    """
    return LoadCombinationDefinition(
        name=combination_name,
        combination_type=combination_type,
        load_case_factors=load_case_factors,
        description=description or f"Load combination: {combination_name}",
    )


def create_basic_uls_combination(
    self_weight_case_name: str,
    traffic_case_name: str,
    combination_name: str = "ULS_Basic_G0+TS",
) -> LoadCombinationDefinition:
    """
    Create a definition for a basic ULS combination.

    :param self_weight_case_name: Name of the self-weight load case.
    :param traffic_case_name: Name of the traffic load case.
    :param combination_name: Name for the combination.
    :return: A LoadCombinationDefinition for the ULS combination.
    :rtype: LoadCombinationDefinition
    """
    factors = {
        self_weight_case_name: 1.25,
        traffic_case_name: 1.25,
    }
    return create_load_combination(SciaCombinationType.ULS, combination_name, factors, "Basic ULS: 1.25*G0 + 1.25*TS (Self-weight + Traffic)")


def create_basic_sls_combination(
    self_weight_case_name: str,
    traffic_case_name: str,
    combination_name: str = "SLS_Basic_G0+TS",
) -> LoadCombinationDefinition:
    """
    Create a definition for a basic SLS combination.

    :param self_weight_case_name: Name of the self-weight load case.
    :param traffic_case_name: Name of the traffic load case.
    :param combination_name: Name for the combination.
    :return: A LoadCombinationDefinition for the SLS combination.
    :rtype: LoadCombinationDefinition
    """
    factors = {
        self_weight_case_name: 1.0,
        traffic_case_name: 1.0,
    }
    return create_load_combination(SciaCombinationType.SLS_CHAR, combination_name, factors, "Basic SLS: 1.0*G0 + 1.0*TS (Self-weight + Traffic)")


def create_wind_uls_combination(
    self_weight_case_name: str,
    traffic_case_name: str,
    wind_case_name: str,
    combination_name: str = "ULS_Wind_G0+TS+W",
) -> LoadCombinationDefinition:
    """
    Create a definition for a ULS combination with wind loads.

    :param self_weight_case_name: Name of the self-weight load case.
    :param traffic_case_name: Name of the traffic load case.
    :param wind_case_name: Name of the wind load case.
    :param combination_name: Name for the combination.
    :return: A LoadCombinationDefinition for the ULS combination with wind.
    :rtype: LoadCombinationDefinition
    """
    factors = {
        self_weight_case_name: 1.35,
        traffic_case_name: 1.5,
        wind_case_name: 1.5 * 0.6,  # Wind with reduction factor
    }
    return create_load_combination(
        SciaCombinationType.ULS,
        combination_name,
        factors,
        "ULS with Wind: 1.35*G0 + 1.5*TS + 0.9*W (Self-weight + Traffic + Wind)",
    )


def create_standard_load_combinations(
    self_weight_case_name: str,
    wind_case_name: str,
    tandem_load_case_names: list[str],
) -> list[LoadCombinationDefinition]:
    """
    Create a list of standard ULS and SLS load combination definitions.

    :param self_weight_case_name: Name of the self-weight load case.
    :param wind_case_name: Name of the wind load case.
    :param tandem_load_case_names: List of tandem load case names.
    :return: A list of LoadCombinationDefinition objects.
    :rtype: list[LoadCombinationDefinition]
    """
    definitions = []
    for i, tandem_case_name in enumerate(tandem_load_case_names):
        combo_id = f"T{i + 1}"
        definitions.append(create_basic_uls_combination(self_weight_case_name, tandem_case_name, f"ULS_{combo_id}"))
        definitions.append(create_basic_sls_combination(self_weight_case_name, tandem_case_name, f"SLS_{combo_id}"))
        definitions.append(create_wind_uls_combination(self_weight_case_name, tandem_case_name, wind_case_name, f"ULS_WIND_{combo_id}"))
    return definitions


# TODO: Additional load combination creation functions to be added for complete bridge analysis
# - create_advanced_uls_combination() - with configurable NEN 8700 factors
# - create_advanced_sls_combination() - with configurable NEN 8701 factors
# - create_multiple_traffic_combinations() - for multiple traffic scenarios
# - create_seismic_combinations() - for seismic load combinations
# - create_construction_stage_combinations() - for construction stages
# - create_fatigue_combinations() - for fatigue limit states
# - create_accidental_combinations() - for accidental situations
