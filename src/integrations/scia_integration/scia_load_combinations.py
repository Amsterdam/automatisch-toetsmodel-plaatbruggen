"""
SCIA load combinations utility module.

This module provides utilities for creating and managing load combinations in SCIA Engineer
by calling methods on the SciaModelBuilder interface.

.. warning::
    The load combination factors and logic implemented in this module are simplified placeholders for architectural and demonstration purposes.
    They are **not** based on official Eurocode or NEN standards.
    A future task is to implement correct, configurable load combination logic based on relevant engineering codes (e.g., NEN 8700/8701).
"""

from typing import Any

from .scia_model_interface import SciaCombinationType, SciaLoadCombination, SciaModelBuilder

# Type aliases for SCIA objects
SciaModel = Any
SciaLoadCase = Any


# Main function to create a load combination
def create_load_combination(
    builder: SciaModelBuilder,
    combination_type: SciaCombinationType,
    combination_name: str,
    load_case_factors: dict[SciaLoadCase, float],
    description: str = "",
) -> SciaLoadCombination:
    """
    Create a SCIA load combination using the builder.

    :param builder: The SCIA model builder instance.
    :param combination_type: "ULS", "SLS_CHAR", etc.
    :param combination_name: Name for the combination.
    :param load_case_factors: Dictionary mapping load case objects to their factors.
    :param description: Optional description.
    :return: The created SCIA Load Combination object.
    :rtype: SciaLoadCombination
    """
    return builder.create_load_combination(
        name=combination_name,
        combination_type=combination_type,
        load_case_factors=load_case_factors,
        description=description or f"Load combination: {combination_name}",
    )


# placeholder for now
def create_basic_uls_combination(
    builder: SciaModelBuilder,
    self_weight_case: SciaLoadCase,
    traffic_case: SciaLoadCase,
    combination_name: str = "ULS_Basic_G0+TS",
) -> SciaLoadCombination:
    """
    Create a basic ULS combination using the builder.

    :param builder: The SCIA model builder instance.
    :param self_weight_case: The self-weight load case object.
    :param traffic_case: The traffic load case object.
    :param combination_name: Name for the combination.
    :return: The created SciaLoadCombination for the ULS combination.
    :rtype: SciaLoadCombination
    """
    factors = {
        self_weight_case: 1.25,
        traffic_case: 1.25,
    }
    return create_load_combination(
        builder, SciaCombinationType.ULS, combination_name, factors, "Basic ULS: 1.25*G0 + 1.25*TS (Self-weight + Traffic)"
    )


# placeholder for now
def create_basic_sls_combination(
    builder: SciaModelBuilder,
    self_weight_case: SciaLoadCase,
    traffic_case: SciaLoadCase,
    combination_name: str = "SLS_Basic_G0+TS",
) -> SciaLoadCombination:
    """
    Create a basic SLS combination using the builder.

    :param builder: The SCIA model builder instance.
    :param self_weight_case: The self-weight load case object.
    :param traffic_case: The traffic load case object.
    :param combination_name: Name for the combination.
    :return: The created SciaLoadCombination for the SLS combination.
    :rtype: SciaLoadCombination
    """
    factors = {
        self_weight_case: 1.0,
        traffic_case: 1.0,
    }
    return create_load_combination(
        builder, SciaCombinationType.SLS_CHAR, combination_name, factors, "Basic SLS: 1.0*G0 + 1.0*TS (Self-weight + Traffic)"
    )


def create_all_load_combinations(builder: SciaModelBuilder, all_load_cases: dict[str, dict[str, SciaLoadCase]]) -> list[SciaLoadCombination]:
    """
    Create a list of all standard ULS and SLS load combinations.

    This function will orchestrate the creation of all required load combinations.
    The commented-out code below serves as a placeholder and guide for implementation.

    :param builder: The SCIA model builder instance.
    :param all_load_cases: A nested dictionary of all available SciaLoadCase objects.
    :return: A list of created SciaLoadCombination objects.
    :rtype: list[SciaLoadCombination]
    """
    all_combinations = []

    # --- Tijdelijke placeholder combinatie ---
    # Voeg één UGT-combinatie toe om ervoor te zorgen dat het model correct bouwt.
    # Dit moet later worden vervangen door de volledige logica.
    standard_cases = all_load_cases.get("standard_cases", {})
    tandem_cases_dict = all_load_cases.get("tandem_cases", {})

    self_weight_case = standard_cases.get("self_weight")
    # Pak het eerste tandemgeval als placeholder voor de verkeerslast
    first_tandem_case = next(iter(tandem_cases_dict.values()), None)

    if self_weight_case and first_tandem_case:
        placeholder_combo = create_basic_uls_combination(builder, self_weight_case, first_tandem_case, "UGT_Placeholder")
        all_combinations.append(placeholder_combo)

    # --- BGT Combinaties ---
    # TODO: Collega's moeten logica implementeren voor het maken van BGT combinaties (Karakteristiek, Frequent, Quasi-Permanent).

    return all_combinations


# TODO: Additional load combination creation functions to be added for complete bridge analysis
# - create_advanced_uls_combination() - with configurable NEN 8700 factors
# - create_advanced_sls_combination() - with configurable NEN 8701 factors
# - create_multiple_traffic_combinations() - for multiple traffic scenarios
# - create_seismic_combinations() - for seismic load combinations
# - create_construction_stage_combinations() - for construction stages
# - create_fatigue_combinations() - for fatigue limit states
# - create_accidental_combinations() - for accidental situations
