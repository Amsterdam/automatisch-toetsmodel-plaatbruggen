"""
SCIA load combinations utility module.

This module provides utilities for creating and managing load combinations in SCIA Engineer
by calling methods on the SciaModelBuilder interface.

.. warning::
    The load combination factors and logic implemented in this module are simplified placeholders for architectural and demonstration purposes.
    They are **not** based on official Eurocode or NEN standards.
    A future task is to implement correct, configurable load combination logic based on relevant engineering codes (e.g., NEN 8700/8701).
"""

import traceback
from typing import Any

from .scia_model_interface import SciaCombinationType, SciaLoadCombination, SciaModelBuilder

# Type aliases for SCIA objects
SciaModel = Any
SciaLoadCase = Any


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


def _create_example_combination(
    builder: SciaModelBuilder, self_weight_case: SciaLoadCase, all_load_cases: dict[str, dict]
) -> list[SciaLoadCombination]:
    """
    Create an example load combination to demonstrate the pattern.

    This function serves as an example for colleagues to understand:
    - How to access load cases from the all_load_cases dictionary
    - How to define load factors
    - How to create combinations using the builder

    :param builder: The SCIA model builder instance.
    :param self_weight_case: The self-weight load case object.
    :param all_load_cases: A nested dictionary of all available SciaLoadCase objects.
    :return: A list of created SciaLoadCombination objects.
    :rtype: list[SciaLoadCombination]
    """
    combinations = []

    # Example: Get pedestrian load case from the nested dictionary
    pedestrian_case = all_load_cases.get("pedestrian")

    if pedestrian_case:
        # Example: Define load factors for ULS combination
        # These are placeholder values - colleagues should replace with proper NEN/Eurocode factors
        load_factors = {
            self_weight_case: 1.35,  # γG for permanent loads (ULS)
            pedestrian_case: 1.50,  # γQ for variable loads (ULS)
        }

        try:
            # Try creating a simple self-weight only combination first
            simple_factors = {self_weight_case: 1.0}

            # Try different combination types
            combo_types_to_try = [
                SciaCombinationType.EN_ULS_SET_B,
                SciaCombinationType.LINEAR_ULTIMATE,
                SciaCombinationType.ENVELOPE_ULTIMATE,
            ]

            for combo_type in combo_types_to_try:
                try:
                    simple_combo = create_load_combination(
                        builder=builder,
                        combination_type=combo_type,
                        combination_name=f"Test_{combo_type.value}",
                        load_case_factors=simple_factors,
                        description=f"Test: 1.0*G (Self-weight only) - {combo_type.value}",
                    )
                    combinations.append(simple_combo)
                    break  # Stop if one works
                except Exception:
                    continue

            # Now try the full combination
            uls_combo = create_load_combination(
                builder=builder,
                combination_type=SciaCombinationType.EN_ULS_SET_B,
                combination_name="ULS_Example_SW_Pedestrian",
                load_case_factors=load_factors,
                description="Example ULS: 1.35*G + 1.50*Q (Self-weight + Pedestrian)",
            )
            combinations.append(uls_combo)
        except Exception:
            traceback.print_exc()
    else:
        # Try to create a simple self-weight only combination as fallback
        try:
            load_factors = {self_weight_case: 1.0}
            simple_combo = create_load_combination(
                builder=builder,
                combination_type=SciaCombinationType.EN_ULS_SET_B,
                combination_name="ULS_Self_Weight_Only",
                load_case_factors=load_factors,
                description="Simple ULS: 1.0*G (Self-weight only)",
            )
            combinations.append(simple_combo)
        except Exception:
            pass

    return combinations


def create_all_load_combinations(builder: SciaModelBuilder, all_load_cases: dict[str, dict]) -> list[SciaLoadCombination]:
    """
    Create a list of standard ULS and SLS load combinations.

    This function serves as the main entry point for load combination creation.
    Colleagues should extend this function by adding more helper functions
    following the pattern shown in _create_example_combination().

    :param builder: The SCIA model builder instance.
    :param all_load_cases: A nested dictionary of all available SciaLoadCase objects.
        Structure example:
        {
            "standard_cases": {"self_weight": SciaLoadCase, "pedestrian": SciaLoadCase},
            "dead_load_cases": {"asfalt": SciaLoadCase, "uitvulling": SciaLoadCase, ...},
            "temperature_cases": {"combi_1": SciaLoadCase, ...},
            "udl_traffic_cases": {"rs_1": SciaLoadCase, ...},
            "tandem_cases": {"tandem_rs1_x1.2": SciaLoadCase, ...},
            ...
        }
    :return: A list of created SciaLoadCombination objects.
    :rtype: list[SciaLoadCombination]
    """
    all_combinations = []

    # Get the main permanent load case (required for all combinations)
    self_weight_case = all_load_cases.get("self_weight")

    if not self_weight_case:
        return []  # Cannot create combinations without self-weight

    # Create example combinations using the helper function
    all_combinations.extend(_create_example_combination(builder, self_weight_case, all_load_cases))

    # TODO: add more helper functions here following the same pattern:
    # TODO: Add _create_temperature_combinations function for temperature load combinations
    # TODO: Add _create_traffic_combinations function for traffic load combinations (tandem, UDL)
    # TODO: Add _create_dead_load_combinations function for dead load combinations (asphalt, filling, etc.)
    # TODO: Add _create_sls_combinations function for SLS combinations
    # TODO: Add _create_accidental_combinations function for accidental situation combinations

    return all_combinations


# TODO: Additional load combination creation functions to be added by colleagues:
#
# Example structure for _create_temperature_combinations:
# - Get temperature_cases from all_load_cases.get("temperature_cases", {})
# - Define appropriate load factors for temperature combinations
# - Create combinations using create_load_combination function
#
# Example structure for _create_traffic_combinations:
# - Get tandem_cases from all_load_cases.get("tandem_cases", {})
# - Get udl_cases from all_load_cases.get("udl_traffic_cases", {})
# - Define appropriate load factors for traffic combinations
# - Create combinations using create_load_combination function
#
# Example structure for _create_dead_load_combinations:
# - Get dead_load_cases from all_load_cases.get("dead_load_cases", {})
# - Define appropriate load factors for dead load combinations
# - Create combinations using create_load_combination function
