# SCIA Loads Helper Refactoring Plan

## Problem
`scia_loads_helper.py` has grown to 2237 lines with multiple responsibilities, making it difficult to maintain and navigate.

## Proposed Structure

Split into focused modules within `src/integrations/scia_integration/`:

### 1. `lane_positioning.py` (~400 lines)
**Purpose**: All lane position calculation logic

**Functions to move**:
- `amount_of_notional_lanes()`
- `amount_of_notional_lanes_from_center()`
- `calculate_possibilities_lane_orientation()`
- `calculate_start_of_lanes()`
- **Theoretical lane positions**:
  - `generate_theoretical_lane_positions_bg8000()`
  - `generate_theoretical_lane_positions_bg9000()`
  - `generate_theoretical_lane_positions_bg10000()`
- **Real lane positions**:
  - `generate_real_lane_positions_bg8000()`
  - `generate_real_lane_positions_bg8000_two_road_zones()`
  - `generate_real_lane_positions_bg9000()`
  - `generate_real_lane_positions_bg9000_two_road_zones()`
  - `generate_real_lane_positions_bg10000()`
  - `generate_real_lane_positions_bg10000_two_road_zones()`

**Rationale**: Centralizes all logic for calculating where lanes should be positioned on the bridge.

---

### 2. `bridge_geometry_helpers.py` (~250 lines)
**Purpose**: Bridge-specific geometry queries and coordinate extraction

**Functions to move**:
- `get_reference_period()`
- `get_number_of_road_zones()`
- `get_widths_of_two_road_zones()`
- `obtain_y_coordinates_road()`
- `obtain_y_coordinates_two_road_zones()`

**Rationale**: Focused on extracting geometric information from bridge parametrization.

---

### 3. `load_calculators.py` (~300 lines)
**Purpose**: Load value calculation logic

**Functions to move**:
- `calculate_real_tandem_values()`
- `calculate_real_udl_values()`
- `calculate_pavement_load_from_dynamic_array()`
- `calculate_pavement_load_from_material()`
- `create_material_surface_load()`
- `add_material_loads()`

**Rationale**: All load intensity calculations in one place.

---

### 4. `tandem_sequencers.py` (~150 lines)
**Purpose**: Longitudinal tandem positioning logic

**Functions to move**:
- `tandem_system_sequencer()`
- `tandem_system_sequencer_single_axis()`
- `tandem_system_sequencer_single_axis_rotated()`

**Constants to move**:
- `TANDEM_WHEEL_OFFSETS`

**Rationale**: Handles x-coordinate positioning of tandem systems along bridge length.

---

### 5. `udl_load_generators.py` (~400 lines)
**Purpose**: UDL polygon creation

**Functions to move**:
- `create_theoretical_udl_traffic_loads()`
- `create_real_udl_traffic_loads()`

**Rationale**: Complex UDL generation logic deserves its own module.

---

### 6. `tandem_load_generators.py` (~900 lines)
**Purpose**: All tandem system load case generation

**Functions to move**:
- `_create_tandem_wheels()` (helper)
- **Theoretical tandems**:
  - `tandem_systems_theoretical_lanes_bg8000()`
  - `tandem_systems_theoretical_lanes_bg9000()`
  - `tandem_systems_theoretical_lanes_bg10000()`
- **Real tandems**:
  - `tandem_systems_real_lanes_bg8000()`
  - `tandem_systems_real_lanes_bg9000()`
  - `tandem_systems_real_lanes_bg10000()`

**Rationale**: All tandem load case generation in one place. Still large but cohesive.

**Alternative**: Could split into `tandem_load_generators_theoretical.py` and `tandem_load_generators_real.py` if preferred.

---

### 7. `vehicle_load_helpers.py` (~150 lines)
**Purpose**: Service and accidental vehicle load utilities

**Functions to move**:
- `_calculate_wheel_corners_vehicle()`
- `calc_vehicle_load_locations()`
- `interpolate_points_along_line()`

**Rationale**: Specialized vehicle load calculations separate from tandems.

---

### 8. Updated `scia_loads_helper.py` (orchestration only, ~100 lines)
**Purpose**: High-level orchestration and re-exports for backward compatibility

**Content**:
```python
"""
SCIA loads helper - Orchestration and backward compatibility.

This module provides high-level functions and re-exports for backward compatibility.
Most functionality has been moved to specialized modules.
"""

# Re-export all functions for backward compatibility
from .lane_positioning import (
    amount_of_notional_lanes,
    amount_of_notional_lanes_from_center,
    generate_theoretical_lane_positions_bg8000,
    generate_real_lane_positions_bg8000,
    # ... etc
)

from .bridge_geometry_helpers import (
    get_reference_period,
    get_number_of_road_zones,
    # ... etc
)

# ... (continue for all modules)

__all__ = [
    # Export everything for backward compatibility
]
```

**Rationale**: Maintains existing import paths while organizing code better.

---

## Migration Strategy

### Phase 1: Create New Modules (No Breaking Changes)
1. Create all 7 new modules with functions copied from `scia_loads_helper.py`
2. Keep original `scia_loads_helper.py` intact
3. Update imports in new modules to reference each other
4. Add comprehensive docstrings to new modules

### Phase 2: Update scia_loads_helper.py (Maintain Compatibility)
1. Replace function implementations with re-exports from new modules
2. Maintain all existing function signatures
3. Keep `__all__` export list complete
4. Test that all existing imports still work

### Phase 3: Update Internal References
1. Update other SCIA integration files to import from new modules directly
2. Update tests to use new module structure
3. Verify all tests pass

### Phase 4: Documentation & Cleanup
1. Update `__init__.py` docstrings to reflect new structure
2. Add architecture documentation showing the new organization
3. Run quality checks (`python ruft.py`)

## Benefits

1. **Maintainability**: Each module has single responsibility (~150-400 lines)
2. **Testability**: Easier to write focused unit tests
3. **Navigation**: Developers can quickly find relevant functions
4. **Backward Compatibility**: Existing code continues to work via re-exports
5. **Future Growth**: Clear pattern for where to add new functions

## File Size Summary

After refactoring:
- `lane_positioning.py`: ~400 lines
- `bridge_geometry_helpers.py`: ~250 lines  
- `load_calculators.py`: ~300 lines
- `tandem_sequencers.py`: ~150 lines
- `udl_load_generators.py`: ~400 lines
- `tandem_load_generators.py`: ~900 lines
- `vehicle_load_helpers.py`: ~150 lines
- `scia_loads_helper.py`: ~100 lines (re-exports only)

**Total**: Same functionality, better organized

## Alternative: Further Split Tandem Generators

If `tandem_load_generators.py` at 900 lines is still too large, consider:

- `tandem_load_generators_theoretical.py` (~450 lines): BG8000/9000/10000 theoretical
- `tandem_load_generators_real.py` (~450 lines): BG8000/9000/10000 real

This would keep all modules under 500 lines.

## Questions to Consider

1. Should we keep all re-exports in `scia_loads_helper.py`, or deprecate it gradually?
2. Do you prefer splitting tandem generators into theoretical/real, or keep them together?
3. Should `two_road_zones` functions be in separate modules or alongside single-zone versions?
4. Are there any other SCIA integration files that need similar refactoring?

