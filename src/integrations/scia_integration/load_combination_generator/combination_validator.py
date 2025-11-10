"""
Validation utilities for load combinations.

This module provides functions to validate combinations and export
validated combinations for use in SCIA models.
"""

from .models import CombinationGenerationResult, LoadMetadata, TrafficLoadCombination
from .traffic_load_rules import TrafficLoadRules


def validate_all_combinations(result: CombinationGenerationResult) -> tuple[list[TrafficLoadCombination], list[str]]:
    """
    Validate all generated combinations and return valid ones with errors.

    :param result: Result containing combinations to validate
    :type result: CombinationGenerationResult
    :returns: Tuple of (valid_combinations, error_messages)
    :rtype: tuple[list[TrafficLoadCombination], list[str]]
    """
    valid_combinations = []
    all_errors = []

    for combo in result.combinations:
        is_valid, errors = TrafficLoadRules.validate_combination(combo, result.load_metadata)
        if is_valid:
            valid_combinations.append(combo)
        else:
            error_msg = f"Combination {combo.combination_id}: {'; '.join(errors)}"
            all_errors.append(error_msg)

    return valid_combinations, all_errors


def get_combination_summary(result: CombinationGenerationResult) -> str:
    """
    Create a human-readable summary of generated combinations.

    :param result: Combination generation result
    :type result: CombinationGenerationResult
    :returns: Formatted summary string
    :rtype: str
    """
    lines = [
        "=" * 60,
        "Traffic Load Combination Generation Summary",
        "=" * 60,
        "",
        f"Total combinations generated: {result.total_count}",
        "",
        "By configuration:",
    ]

    for config, count in result.by_configuration.items():
        lines.append(f"  Configuration {config}: {count} combinations")

    if result.statistics:
        lines.extend(
            [
                "",
                "Statistics:",
                f"  Average loads per combination: {result.statistics.get('avg_loads_per_combination', 0):.1f}",
                f"  Combinations with tandem: {result.statistics.get('combinations_with_tandem', 0)}",
                f"  UDL-only combinations: {result.statistics.get('combinations_udl_only', 0)}",
            ]
        )

    if result.warnings:
        lines.extend(
            [
                "",
                "Warnings:",
            ]
        )
        for warning in result.warnings:
            lines.append(f"  - {warning}")

    lines.append("=" * 60)

    return "\n".join(lines)


def export_combinations_for_scia(combinations: list[TrafficLoadCombination], load_metadata: dict[str, LoadMetadata]) -> dict[str, list[str]]:
    """
    Export combinations in a format suitable for SCIA integration.

    Returns a dictionary mapping combination IDs to lists of load case names.

    :param combinations: List of validated combinations
    :type combinations: list[TrafficLoadCombination]
    :param load_metadata: Load metadata for reference
    :type load_metadata: dict[str, LoadMetadata]
    :returns: Dictionary of combination_id -> load_case_names
    :rtype: dict[str, list[str]]
    """
    export_dict = {}
    for combo in combinations:
        export_dict[combo.combination_id] = combo.get_all_load_cases()
    return export_dict


def get_combinations_by_lane_count(
    result: CombinationGenerationResult,
) -> dict[int, list[TrafficLoadCombination]]:
    """
    Group combinations by the number of active lanes (with tandem loads).

    Useful for analyzing load distribution and selecting critical combinations.

    :param result: Combination generation result
    :type result: CombinationGenerationResult
    :returns: Dictionary mapping lane_count -> list of combinations
    :rtype: dict[int, list[TrafficLoadCombination]]
    """
    groups: dict[int, list[TrafficLoadCombination]] = {}

    for combo in result.combinations:
        lane_count = combo.get_lane_count()
        if lane_count not in groups:
            groups[lane_count] = []
        groups[lane_count].append(combo)

    return groups


def filter_combinations_by_criteria(
    result: CombinationGenerationResult,
    min_lane_count: int | None = None,
    max_lane_count: int | None = None,
    require_udl: bool = False,
    configurations: list[str] | None = None,
) -> list[TrafficLoadCombination]:
    """
    Filter combinations based on specified criteria.

    :param result: Combination generation result
    :type result: CombinationGenerationResult
    :param min_lane_count: Minimum number of lanes with tandem loads
    :type min_lane_count: int | None
    :param max_lane_count: Maximum number of lanes with tandem loads
    :type max_lane_count: int | None
    :param require_udl: Whether to require UDL loads in combination
    :type require_udl: bool
    :param configurations: List of configuration codes to include (e.g., ["A", "B"])
    :type configurations: list[str] | None
    :returns: Filtered list of combinations
    :rtype: list[TrafficLoadCombination]
    """
    filtered = []

    for combo in result.combinations:
        # Check lane count
        lane_count = combo.get_lane_count()
        if min_lane_count is not None and lane_count < min_lane_count:
            continue
        if max_lane_count is not None and lane_count > max_lane_count:
            continue

        # Check UDL requirement
        if require_udl and not combo.udl_loads:
            continue

        # Check configuration
        if configurations is not None and combo.configuration.value not in configurations:
            continue

        filtered.append(combo)

    return filtered
