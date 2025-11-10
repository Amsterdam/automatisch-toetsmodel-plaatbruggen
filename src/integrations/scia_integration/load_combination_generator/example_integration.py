"""
Example integration of traffic load combination generator with SCIA model.

This module demonstrates how to use the combination generator to create
valid traffic load combinations for SCIA Engineer models.
"""

from typing import Any

from src.integrations.scia_integration.load_combination_generator import (
    CombinationConstraints,
    TrafficLoadCombinationGenerator,
)
from src.integrations.scia_integration.load_combination_generator.combination_validator import (
    export_combinations_for_scia,
    filter_combinations_by_criteria,
    get_combination_summary,
    validate_all_combinations,
)


def generate_valid_traffic_combinations(all_load_cases: dict[str, Any]) -> dict[str, list[str]]:
    """
    Generate valid traffic load combinations from SCIA load cases.

    This is the main integration point that can be called from the SCIA
    model creation workflow.

    :param all_load_cases: Dictionary of all load cases from create_all_load_cases()
    :type all_load_cases: dict[str, Any]
    :returns: Dictionary mapping combination IDs to lists of load case names
    :rtype: dict[str, list[str]]
    """
    # Step 1: Create generator with constraints
    constraints = CombinationConstraints(
        max_lanes=3,
        allow_mixed_configurations=False,  # Traffic loads must be in same configuration
        require_udl_with_tandem=False,
    )

    generator = TrafficLoadCombinationGenerator(constraints=constraints)

    # Step 2: Extract metadata from load cases
    print("Extracting load metadata...")
    metadata = generator.extract_metadata_from_load_cases(all_load_cases)
    print(f"Found {len(metadata)} traffic load cases")

    # Step 3: Generate combinations
    print("Generating valid combinations...")
    result = generator.generate_traffic_combinations(metadata)

    # Step 4: Print summary
    print(get_combination_summary(result))

    # Step 5: Validate all combinations
    print("\nValidating combinations...")
    valid_combos, errors = validate_all_combinations(result)

    if errors:
        print(f"WARNING: Found {len(errors)} invalid combinations:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
    else:
        print("✓ All combinations are valid!")

    # Step 6: Export for SCIA
    print(f"\nExporting {len(valid_combos)} valid combinations...")
    scia_combinations = export_combinations_for_scia(valid_combos, result.load_metadata)

    return scia_combinations


def filter_critical_combinations(all_load_cases: dict[str, Any]) -> dict[str, list[str]]:
    """
    Generate only critical traffic load combinations.

    This creates a reduced set of combinations focusing on the most severe cases:
    - Multi-lane combinations (2 or 3 lanes active)
    - Combinations with both UDL and tandem loads
    - All configurations included

    :param all_load_cases: Dictionary of all load cases
    :type all_load_cases: dict[str, Any]
    :returns: Dictionary of critical combinations
    :rtype: dict[str, list[str]]
    """
    generator = TrafficLoadCombinationGenerator()
    metadata = generator.extract_metadata_from_load_cases(all_load_cases)
    result = generator.generate_traffic_combinations(metadata)

    # Filter for critical combinations
    critical_combos = filter_combinations_by_criteria(
        result,
        min_lane_count=2,  # At least 2 lanes
        require_udl=True,  # Must have UDL
        configurations=["A", "B", "C"],  # All configs
    )

    print(f"Generated {len(critical_combos)} critical combinations (from {result.total_count} total)")

    # Export
    critical_dict = export_combinations_for_scia(critical_combos, result.load_metadata)
    return critical_dict


def example_usage_in_scia_model() -> None:
    """
    Example of how to integrate with SCIA model creation.

    This shows where in the SCIA workflow you would call the combination generator.
    """
    # Assuming you have a SCIA model builder and params
    # from src.integrations.scia_integration.model.scia_model import define_complete_bridge_model
    # from src.integrations.scia_integration.load_system.scia_load_cases import create_all_load_cases

    # ... after creating geometry and load groups ...

    # Create all load cases
    # all_load_cases = create_all_load_cases(builder, params)

    # Generate valid traffic combinations
    # valid_traffic_combos = generate_valid_traffic_combinations(all_load_cases)

    # Now create Eurocode combinations using only valid traffic combinations
    # For each Eurocode combination type (ULS, SLS, etc.):
    #   For each traffic combination:
    #     Create SCIA combination with:
    #       - Permanent loads (with appropriate factors)
    #       - Temperature loads (with appropriate factors)
    #       - This specific traffic combination (with appropriate factors)

    # Example pseudo-code:
    # for combo_id, traffic_load_cases in valid_traffic_combos.items():
    #     # Create ULS combination with these traffic loads
    #     load_case_factors = {}
    #     load_case_factors.update(get_permanent_factors())  # γG = 1.35
    #     for traffic_case_name in traffic_load_cases:
    #         load_case_factors[traffic_case_name] = 1.5  # γQ = 1.5
    #
    #     create_load_combination(
    #         builder=builder,
    #         combination_type=LoadCombinationType.ULS,
    #         combination_name=f"ULS_{combo_id}",
    #         load_case_factors=load_case_factors,
    #         description=f"ULS with {combo_id}",
    #     )


if __name__ == "__main__":
    # This is an example/documentation file
    # In real usage, this would be called from the SCIA model creation workflow
    print("This is an example integration file.")
    print("See the function docstrings for usage instructions.")
