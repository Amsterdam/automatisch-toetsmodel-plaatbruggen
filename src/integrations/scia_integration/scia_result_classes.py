"""
SCIA result classes utility module.

This module provides utilities for creating and managing result classes in SCIA Engineer
by calling methods on the SciaModelBuilder interface.

:module: scia_result_classes
:synopsis: Utilities for creating SCIA result classes.
"""

from typing import Any

from src.integrations.scia_integration.scia_load_combinations import filter_by_prefix, load_combination_table_without_rounding
from .scia_model_interface import SciaModelBuilder, SciaLoadCombination, SciaResultClass

# ===================================================================================================================
# Functions
# ===================================================================================================================

def create_uls_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder
) -> list[SciaResultClass]:
    """
    Create ULS result class (6.10a/6.10b).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :returns: List of SCIA result classes for ULS.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    uls_combinations = filter_by_prefix(df_combinations, ["6.10a", "6.10b"])
    return builder.create_result_class(
        name="ULS",
        combinations=uls_combinations,
        nonlinear_combinations=None
    )


def create_sls_kar_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder
) -> list[SciaResultClass]:
    """
    Create SLS characteristic result class (6.14).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :returns: List of SCIA result classes for SLS characteristic.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    sls_kar_combinations = filter_by_prefix(df_combinations, ["6.14"])
    return builder.create_result_class(
        name="SLS kar",
        combinations=sls_kar_combinations,
        nonlinear_combinations=None
    )

def create_sls_freq_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder
) -> list[SciaResultClass]:
    """
    Create SLS frequent result classes (6.15).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :returns: List of SCIA result classes for SLS frequent.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    sls_freq_combinations = filter_by_prefix(df_combinations, ["6.15"])
    return builder.create_result_class(
        name="SLS freq",
        combinations=sls_freq_combinations,
        nonlinear_combinations=None
    )

def create_sls_qp_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder
) -> list[SciaResultClass]:
    """
    Create SLS quasi-permanent result classes (6.16).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :returns: List of SCIA result classes for SLS quasi-permanent.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    sls_qp_combinations = filter_by_prefix(df_combinations, ["6.16"])
    return builder.create_result_class(
        name="SLS qp",
        combinations=sls_qp_combinations,
        nonlinear_combinations=None
    )


def create_fat_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder
) -> list[SciaResultClass]:
    """
    Create fatigue result classes (6.67, 6.69).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :returns: List of SCIA result classes for fatigue.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    fat_combinations = filter_by_prefix(df_combinations, ["6.67", "6.69"])
    return builder.create_result_class(
        name="FAT",
        combinations=fat_combinations,
        nonlinear_combinations=None
    )


def create_all_result_classes(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
) -> list[SciaResultClass]:
    """
    Create all result classes for the bridge model (ULS, SLS, fatigue, etc.).

    Aggregates outputs from dedicated helper functions for each result class family.
    Extend this function with extra families (temperature-only, accidental scenarios, etc.) when implemented.

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :returns: List of all created SCIA result classes.
    :rtype: list[SciaResultClass]
    """
    result_classes: list[SciaResultClass] = []

    # Standard combinations from the NEN 8700 table (one function per family)
    result_classes.extend(create_uls_result_class_from_table(params, builder))
    result_classes.extend(create_sls_kar_result_class_from_table(params, builder))
    result_classes.extend(create_sls_freq_result_class_from_table(params, builder))
    result_classes.extend(create_sls_qp_result_class_from_table(params, builder))
    result_classes.extend(create_fat_result_class_from_table(params, builder))

    return result_classes