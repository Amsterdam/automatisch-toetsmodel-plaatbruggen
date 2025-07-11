"""
SCIA load combinations utility module.

This module provides utilities for creating and managing definitions for load combinations in SCIA Engineer.

.. warning::
    The load combination factors and logic implemented in this module are simplified placeholders for architectural and demonstration purposes.
    They are **not** based on official Eurocode or NEN standards.
    A future task is to implement correct, configurable load combination logic based on relevant engineering codes (e.g., NEN 8700/8701).
"""

from .scia_model_builder import SciaModelBuilder


def create_load_combination(
    builder: SciaModelBuilder,
    name: str,
    comb_type: str,
    description: str,
    cases: list[tuple[str, float]],
) -> None:
    """
    Create a definition for a SCIA load combination.

    :param builder: The SCIA model builder.
    :param name: The name of the load combination.
    :param comb_type: The type of combination (e.g., "ULS_GEO_STR_B").
    :param description: A description for the combination.
    :param cases: A list of tuples, where each tuple contains the load case name and its corresponding factor.
    """
    builder.add_load_combination(
        name=name,
        comb_type=comb_type,
        description=description,
        cases=cases,
    )


def create_standard_load_combinations(builder: SciaModelBuilder, self_weight_case: str, tandem_cases: list[str]) -> None:
    """
    Creates a simplified set of ULS load combinations.

    - One combination for self-weight only.
    - One combination for each tandem load case, combined with self-weight.

    :param builder: The SCIA model builder.
    :param self_weight_case: The name of the self-weight load case.
    :param tandem_cases: A list of names for the tandem load cases.
    """
    # Self-weight only combination
    create_load_combination(
        builder,
        name="CO1",
        comb_type="ULS_GEO_STR_B",
        description="Self-weight only",
        cases=[(self_weight_case, 1.2)],
    )

    # Combinations for each tandem load case
    for i, tandem_case in enumerate(tandem_cases, start=2):
        create_load_combination(
            builder,
            name=f"CO{i}",
            comb_type="ULS_GEO_STR_B",
            description=f"Self-weight + {tandem_case}",
            cases=[(self_weight_case, 1.2), (tandem_case, 1.5)],
        )
