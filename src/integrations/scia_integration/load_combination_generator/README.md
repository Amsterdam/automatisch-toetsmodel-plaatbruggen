# Traffic Load Combination Generator

This module provides a sophisticated system for generating valid traffic load combinations for SCIA Engineer models. It ensures that only physically possible combinations are created, respecting configuration constraints and preventing invalid load scenarios.

## Problem Statement

When creating load combinations in SCIA Engineer, the default behavior combines all load cases from load groups without considering:

1. **Configuration conflicts**: Traffic loads from different configurations (A, B, C) represent mutually exclusive positioning scenarios
2. **Lane conflicts**: Multiple tandem loads on the same notional lane cannot occur simultaneously
3. **Position overlaps**: Tandem loads from different configurations at the same position conflict
4. **UDL-Tandem mismatch**: UDL and tandem loads from different configurations shouldn't be combined

This leads to **invalid combinations** that overestimate design forces.

## Solution

This module provides:

1. **Metadata extraction**: Parses load case names and titles to extract configuration, lane, and position data
2. **Rule-based filtering**: Applies engineering rules to prevent invalid combinations
3. **Systematic generation**: Creates all valid combinations within each configuration
4. **Validation**: Verifies that generated combinations satisfy all constraints

## Key Concepts

### Configuration (A, B, C)

Traffic loads are generated in three configurations representing different positioning scenarios:
- **Configuration A**: Specific lane arrangement (e.g., 300 kN on lane 1, 200 kN on lane 2, 100 kN on lane 3)
- **Configuration B**: Alternative arrangement (e.g., 300 kN on lane 1, 100 kN on lane 2, 200 kN on lane 3)
- **Configuration C**: Another arrangement specific to the bridge geometry

**Rule**: Traffic loads can only be combined within the same configuration.

### Notional Lanes (RS 1, RS 2, RS 3)

Tandem loads are positioned on notional lanes representing traffic lanes across the bridge width.

**Rule**: Only one tandem load per notional lane in any combination.

### Load Categories

- **TRAFFIC_UDL**: Uniformly distributed traffic loads
- **TRAFFIC_TANDEM**: Tandem system (concentrated axle loads)
- Other categories (permanent, temperature, etc.) are not subject to configuration rules

## Usage

### Basic Usage

```python
from src.integrations.scia_integration.load_combination_generator import (
    TrafficLoadCombinationGenerator,
    CombinationConstraints,
)

# Create generator with default constraints
generator = TrafficLoadCombinationGenerator()

# Extract metadata from SCIA load cases
all_load_cases = create_all_load_cases(builder, params)
metadata = generator.extract_metadata_from_load_cases(all_load_cases)

# Generate valid combinations
result = generator.generate_traffic_combinations(metadata)

# Print summary
from src.integrations.scia_integration.load_combination_generator.combination_validator import get_combination_summary
print(get_combination_summary(result))
```

### Advanced Usage with Custom Constraints

```python
from src.integrations.scia_integration.load_combination_generator import (
    TrafficLoadCombinationGenerator,
    CombinationConstraints,
)

# Define custom constraints
constraints = CombinationConstraints(
    max_lanes=3,  # Bridge has 3 notional lanes
    allow_mixed_configurations=False,  # Enforce configuration separation
    require_udl_with_tandem=False,  # UDL optional with tandem
)

generator = TrafficLoadCombinationGenerator(constraints=constraints)

# ... rest of the workflow
```

### Filtering Combinations

```python
from src.integrations.scia_integration.load_combination_generator.combination_validator import (
    filter_combinations_by_criteria,
)

# Get only combinations with at least 2 lanes
multi_lane_combos = filter_combinations_by_criteria(
    result,
    min_lane_count=2,
    require_udl=True,
    configurations=["A", "B"],  # Only configs A and B
)

# Get combinations grouped by lane count
by_lanes = get_combinations_by_lane_count(result)
print(f"Single lane combinations: {len(by_lanes.get(1, []))}")
print(f"Two lane combinations: {len(by_lanes.get(2, []))}")
```

### Validation

```python
from src.integrations.scia_integration.load_combination_generator.combination_validator import (
    validate_all_combinations,
)

# Validate all generated combinations
valid_combos, errors = validate_all_combinations(result)

if errors:
    print(f"Found {len(errors)} invalid combinations:")
    for error in errors:
        print(f"  - {error}")
else:
    print("All combinations are valid!")
```

### Export for SCIA Integration

```python
from src.integrations.scia_integration.load_combination_generator.combination_validator import (
    export_combinations_for_scia,
)

# Export in SCIA-compatible format
scia_combinations = export_combinations_for_scia(result.combinations, result.load_metadata)

# Use with SCIA model builder
for combo_id, load_case_names in scia_combinations.items():
    # Create SCIA combination with only these load cases
    # ... integrate with existing SCIA combination creation
    pass
```

## Architecture

### Module Structure

```
load_combination_generator/
├── __init__.py                  # Public API
├── models.py                    # Pydantic data models
├── traffic_load_rules.py        # Combination validation rules
├── combination_generator.py     # Main generation logic
├── combination_validator.py     # Validation and export utilities
└── README.md                    # This file
```

### Data Flow

1. **Input**: SCIA load cases from `create_all_load_cases()`
2. **Metadata Extraction**: Parse titles to extract configuration, lane, position
3. **Grouping**: Separate loads by configuration (A, B, C)
4. **Generation**: For each configuration, create all valid combinations
5. **Validation**: Verify combinations satisfy all rules
6. **Output**: Validated combinations ready for SCIA integration

### Key Classes

#### `LoadMetadata`
Represents metadata for a single load case:
- `configuration`: A, B, C, or None
- `notional_lane`: 1, 2, 3, or None
- `position_x`: Position on bridge for tandem loads
- `category`: TRAFFIC_UDL, TRAFFIC_TANDEM, etc.

#### `TrafficLoadCombination`
Represents a valid combination of traffic loads:
- `configuration`: Configuration this combination belongs to
- `udl_loads`: List of UDL load case names
- `tandem_loads`: Dictionary mapping lanes to tandem load names

#### `TrafficLoadRules`
Static methods for validating combinations:
- `can_combine_configurations()`: Check if configs can combine
- `can_combine_tandem_loads()`: Check if tandems can combine
- `validate_combination()`: Full combination validation

#### `TrafficLoadCombinationGenerator`
Main generator class:
- `extract_metadata_from_load_cases()`: Parse load case structure
- `generate_traffic_combinations()`: Create all valid combinations

## Integration with Existing SCIA System

### Option 1: Pre-filter load cases

Before creating SCIA combinations, filter load cases:

```python
# Generate valid combinations
result = generator.generate_traffic_combinations(metadata)

# For each Eurocode combination, use only valid traffic combinations
for eurocode_combo in ["ULS", "SLS_CHAR", etc.]:
    for traffic_combo in result.combinations:
        # Create SCIA combination with:
        # - Permanent loads (always included)
        # - Temperature loads (as per code)
        # - Only this specific traffic combination
        create_load_combination(builder, ..., traffic_combo.get_all_load_cases())
```

### Option 2: Replace traffic load groups

Instead of using load groups for traffic loads, create individual combinations:

```python
# Don't use load groups LG4000, LG8000, LG9000, LG10000 in combinations
# Instead, create explicit combinations with specific load cases
```

### Option 3: Post-filter SCIA combinations

Generate combinations in SCIA, then filter invalid ones:

```python
# Generate combinations normally
scia_combinations = create_all_load_combinations(params, builder, all_load_cases)

# Filter to keep only valid traffic combinations
valid_combinations = filter_scia_combinations_by_rules(scia_combinations, result)
```

## Example Output

```
============================================================
Traffic Load Combination Generation Summary
============================================================

Total combinations generated: 2847

By configuration:
  Configuration A: 949 combinations
  Configuration B: 949 combinations
  Configuration C: 949 combinations

Statistics:
  Average loads per combination: 3.2
  Combinations with tandem: 1898
  UDL-only combinations: 949

============================================================
```

## Testing

The module includes comprehensive tests (to be created):

```bash
pytest tests/test_src/test_integrations/test_load_combination_generator/ -v
```

## Future Enhancements

1. **Dominant lane logic**: Implement proper dominant/other lane factors per Eurocode
2. **Position-based filtering**: Prevent overlapping tandem loads more precisely
3. **Optimization**: Reduce number of combinations using envelope analysis
4. **SCIA API integration**: Direct SCIA combination creation from generated combinations
5. **Combination importance**: Rank combinations by likelihood/severity

## References

- Eurocode 1 (EN 1991): Load Model 1 definitions
- NEN 8700: Dutch national annex for traffic loads
- SCIA Engineer documentation: Load combinations


