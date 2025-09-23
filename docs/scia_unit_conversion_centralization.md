# SCIA Unit Conversion Centralization

## Problem

Previously, the SCIA units mapping and value conversion were handled in two separate places:

1. **Units mapping**: `build_units_mapping()` in `scia_results_creator.py` determined what units should be displayed (e.g., "kN", "kNm")
2. **Value conversion**: `safe_float_format()` in `scia_result_views.py` converted actual values from N to kN and Nm to kNm

This separation created a risk that the units mapping and value conversion could get out of sync, leading to incorrect unit labels or improper conversions.

## Solution

Created a centralized unit conversion system in `src/integrations/scia_integration/scia_unit_conversion.py` that keeps units mapping and value conversion together to ensure they stay in sync.

### Key Components

#### 1. `UnitConversion` Dataclass
Represents a unit conversion with:
- `display_unit`: The unit string to display (e.g., "kN", "kNm")
- `conversion_factor`: Factor to convert from raw SCIA units (N→kN = 1/1000)
- `raw_unit`: The original unit from SCIA (for documentation)

#### 2. `SciaUnitConverter` Class
Centralized converter that handles both 1D (beam) and 2D (plate) elements:
- Maintains conversion definitions for all force/moment components
- Provides consistent unit mapping and value conversion
- Supports both absolute units (1D: kN, kNm) and per-unit-length units (2D: kN/m, kNm/m)

#### 3. Factory Method
`SciaUnitConverter.create_for_table_type(table_name)` automatically detects element type from SCIA table names:
- Tables containing "2D" → creates 2D converter (kN/m, kNm/m units)
- Tables containing "1D" or unknown → creates 1D converter (kN, kNm units)

### Usage Examples

#### Basic Usage
```python
from src.integrations.scia_integration.scia_unit_conversion import SciaUnitConverter

# Create converter for 1D beam elements
converter = SciaUnitConverter("1D")

# Get display unit
unit = converter.get_display_unit("Vy")  # Returns "kN"

# Convert value from N to kN
converted = converter.convert_value(1000.0, "Vy")  # Returns 1.0

# Format value with unit
formatted = converter.format_value_with_unit(1000.0, "Vy")  # Returns "1.0 kN"
```

#### Automatic Table Type Detection
```python
# Automatically detect element type from table name
converter = SciaUnitConverter.create_for_table_type("Internal Forces 2D")
print(converter.get_display_unit("v_x"))  # Returns "kN/m" for 2D elements

converter = SciaUnitConverter.create_for_table_type("Internal Forces 1D")
print(converter.get_display_unit("Vy"))   # Returns "kN" for 1D elements
```

#### Consistent Units Mapping
```python
from src.integrations.scia_integration.scia_unit_conversion import build_units_mapping

results = {"internal_forces": {"table_name": "Internal Forces 2D"}}
units = build_units_mapping(results)
# Returns: {"internal_forces": {"v_x": "kN/m", "m_x": "kNm/m", ...}}
```

### Backward Compatibility

The existing functions continue to work exactly as before:
- `build_units_mapping()` in `scia_results_creator.py` now delegates to the centralized system
- `safe_float_format()` in `scia_result_views.py` now uses the centralized conversion logic
- All existing unit tests continue to pass

### Benefits

1. **Consistency**: Units mapping and value conversion are guaranteed to stay in sync
2. **Maintainability**: Single place to update conversion factors and unit definitions
3. **Extensibility**: Easy to add new force/moment components or element types
4. **Type Safety**: Clear data structures with explicit conversion factors
5. **Documentation**: Conversion factors and raw units are explicitly documented
6. **Testing**: Comprehensive test coverage ensures reliability

### Integration Points

The centralized system is now used by:
- `scia_results_creator.py`: For building units mappings
- `scia_result_views.py`: For value formatting and conversion
- `scia_model_builder.py`: For attaching units to analysis results

### Example: Adding New Force Component

To add a new force component, simply add it to the appropriate conversion dictionary:

```python
# In SciaUnitConverter._CONVERSIONS_2D or _CONVERSIONS_1D
"new_component": UnitConversion("kN/m", 1/1000, "N/m"),
```

The component will automatically be available for:
- Units mapping generation
- Value conversion
- Formatted display

This ensures that when new components are added, both the units and conversion logic are defined in one place, preventing inconsistencies.
