"""
SCIA result classes utility module.

This module provides utilities for creating and managing result classes in SCIA Engineer
by calling methods on the SciaModelBuilder interface.

:module: scia_result_classes
:synopsis: Utilities for creating SCIA result classes.
"""

from typing import Any

from pandas import DataFrame

from src.integrations.scia_integration.load_system.scia_load_combinations import load_combination_table_without_rounding
from src.integrations.scia_integration.model.scia_model_interface import SciaModelBuilder, SciaResultClass

# ===================================================================================================================
# Functions
# ===================================================================================================================


def _get_combination_name(combination: Any) -> str:  # noqa: ANN401
    """
    Extract the name/identifier from a SCIA combination object.

    :param combination: SCIA combination like object created by the builder.
    :type combination: Any
    :returns: Combination name if present, otherwise an empty string.
    :rtype: str
    """
    for attr in ("name", "Name", "description", "Description"):
        if hasattr(combination, attr):
            return str(getattr(combination, attr))
    return ""


def _normalize_combination_name(name: str) -> str:
    """
    Normalize SCIA combination names so they can be compared to DataFrame indices.

    Removes configuration suffixes like ``" - Config A"`` which are injected when
    combinations contain traffic loads. This matches the raw combination name used
    as DataFrame index entries (e.g., ``"6.10a LC1"``).

    :param name: Raw combination name provided by SCIA.
    :type name: str
    :returns: Normalized combination name without configuration suffix.
    :rtype: str
    """
    config_separator = " - Config "
    if config_separator in name:
        return name.split(config_separator, 1)[0].strip()
    return name.strip()


def filter_list_by_df_index(index_df: DataFrame, filter_list: list, prefixes: list[str]) -> list[Any]:
    """
    Filter items in ``filter_list`` whose index in ``index_df`` starts with any of the given prefixes.

    :param index_df: DataFrame whose index is checked for prefixes.
    :type index_df: pandas.DataFrame
    :param filter_list: List of items to filter (must have 'index' attribute or be indexable).
    :type filter_list: list
    :param prefixes: List of string prefixes to match.
    :type prefixes: list[str]
    :returns: List of items from ``filter_list`` whose index in ``index_df`` matches any prefix.
    :rtype: list[Any]
    """
    normalized_indices = {
        str(df_index).strip()
        for df_index in index_df.index
        if any(str(df_index).startswith(prefix) for prefix in prefixes)
    }

    filtered_items = []
    for combination in filter_list:
        combination_name = _normalize_combination_name(_get_combination_name(combination))
        if combination_name in normalized_indices:
            filtered_items.append(combination)
    return filtered_items


def create_uls_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_combinations: list[Any],
) -> list[SciaResultClass]:
    """
    Create ULS result class (6.10a/6.10b).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :param all_load_combinations: List of all load combinations.
    :type all_load_combinations: list[Any]
    :returns: List containing the SCIA result class for ULS.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    uls_combinations = filter_list_by_df_index(index_df=df_combinations, filter_list=all_load_combinations, prefixes=["6.10a", "6.10b"])
    return [builder.create_result_class(name="ULS", combinations=uls_combinations, nonlinear_combinations=None)]


def create_sls_kar_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_combinations: list[Any],
) -> list[SciaResultClass]:
    """
    Create SLS characteristic result class (6.14b).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :param all_load_combinations: List of all load combinations.
    :type all_load_combinations: list[Any]
    :returns: List containing the SCIA result class for SLS characteristic.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    sls_kar_combinations = filter_list_by_df_index(index_df=df_combinations, filter_list=all_load_combinations, prefixes=["6.14b"])
    return [builder.create_result_class(name="SLS kar", combinations=sls_kar_combinations, nonlinear_combinations=None)]


def create_sls_freq_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_combinations: list[Any],
) -> list[SciaResultClass]:
    """
    Create SLS frequent result class (6.15b).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :param all_load_combinations: List of all load combinations.
    :type all_load_combinations: list[Any]
    :returns: List containing the SCIA result class for SLS frequent.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    sls_freq_combinations = filter_list_by_df_index(index_df=df_combinations, filter_list=all_load_combinations, prefixes=["6.15b"])
    return [builder.create_result_class(name="SLS freq", combinations=sls_freq_combinations, nonlinear_combinations=None)]


def create_sls_qp_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_combinations: list[Any],
) -> list[SciaResultClass]:
    """
    Create SLS quasi-permanent result class (6.16b).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :param all_load_combinations: List of all load combinations.
    :type all_load_combinations: list[Any]
    :returns: List containing the SCIA result class for SLS quasi-permanent.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    sls_qp_combinations = filter_list_by_df_index(index_df=df_combinations, filter_list=all_load_combinations, prefixes=["6.16b"])
    return [builder.create_result_class(name="SLS qp", combinations=sls_qp_combinations, nonlinear_combinations=None)]


def create_fat_result_class_from_table(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_combinations: list[Any],
) -> list[SciaResultClass]:
    """
    Create fatigue result class (6.67, 6.69).

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :param all_load_combinations: List of all load combinations.
    :type all_load_combinations: list[Any]
    :returns: List containing the SCIA result class for fatigue.
    :rtype: list[SciaResultClass]
    """
    df_combinations = load_combination_table_without_rounding(params)
    fat_combinations = filter_list_by_df_index(index_df=df_combinations, filter_list=all_load_combinations, prefixes=["6.67", "6.69"])
    return [builder.create_result_class(name="FAT", combinations=fat_combinations, nonlinear_combinations=None)]


def create_all_result_classes(
    params: Any,  # noqa: ANN401
    builder: SciaModelBuilder,
    all_load_combinations: list[Any],
) -> list[SciaResultClass]:
    """
    Create all result classes for the bridge model (ULS, SLS, fatigue).

    Aggregates outputs from dedicated helper functions for each result class family.
    Extend this function with extra families (temperature-only, accidental scenarios, etc.) when implemented.

    Result classes:
        - ULS (6.10a, 6.10b)
        - SLS characteristic (6.14b)
        - SLS frequent (6.15b)
        - SLS quasi-permanent (6.16b)
        - Fatigue (6.67, 6.69)

    :param params: Input parameters for result class generation.
    :type params: Any
    :param builder: SCIA model builder instance.
    :type builder: SciaModelBuilder
    :param all_load_combinations: List of all load combinations.
    :type all_load_combinations: list[Any]
    :returns: List of all created SCIA result classes.
    :rtype: list[SciaResultClass]
    """
    result_classes: list[SciaResultClass] = []

    # Create all result classes
    result_classes.extend(create_uls_result_class_from_table(params, builder, all_load_combinations))
    result_classes.extend(create_sls_kar_result_class_from_table(params, builder, all_load_combinations))
    result_classes.extend(create_sls_freq_result_class_from_table(params, builder, all_load_combinations))
    result_classes.extend(create_sls_qp_result_class_from_table(params, builder, all_load_combinations))
    result_classes.extend(create_fat_result_class_from_table(params, builder, all_load_combinations))

    return result_classes
