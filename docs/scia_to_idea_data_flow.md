# SCIA to IDEA Data Flow Documentation

This document describes how cross-section (CS) force and moment data is extracted from SCIA Engineer analysis results and applied to IDEA StatiCa RCS models for reinforced concrete section checks.

## Overview

The data flow follows these main steps:

1. **SCIA Analysis Results** → Extract cross-section force envelopes
2. **CS Envelope Processing** → Filter and combine ULS and SLS frequent results
3. **IDEA Load Application** → Create extremes on IDEA slabs for each zone and direction

## Data Pipeline

### 1. SCIA Results Extraction

**Module**: `src/integrations/scia_integration/scia_results_processor.py`

**Key Functions**:
- `process_scia_cs_results()` - Main processing function for cross-section results
- `extract_cs_force_envelopes()` - Combines and filters ULS and SLS freq data

**Result Table Types**:
- `ULS` - Ultimate Limit State results (fundamental combinations)
- `SLS freq` - Serviceability Limit State frequent combinations

**Note**: SLS characteristic (`SLS kar`) is no longer used in the workflow.

**Table Name Pattern**:
```python
CS_BASIS_TABLE_PATTERN = "Interne 2D-krachten basis {table_type}"
```

**Force Components Extracted**:
- `v_x`, `v_y` - Shear forces
- `m_xD+`, `m_xD-`, `m_yD+`, `m_yD-` - Bending moments (positive and negative)
- `n_xD`, `n_yD` - Normal forces (new addition)

**Envelope Structure**:

Each row in the envelope DataFrame represents the maximum absolute value for a specific force component at a cross-section location:

| Column | Description |
|--------|-------------|
| `name` | Cross-section name (e.g., "SEC_Z1_1_y0.500") |
| `coords_xyz` | (x, y, z) coordinates of the point |
| `belasting` | Load combination name |
| `zone` | Zone identifier (e.g., "1-1", "2-2") |
| `max_for_column` | Which force component this row maximizes |
| `result_type` | "ULS" or "SLS freq" |
| `v_x_max`, `v_y_max` | Maximum shear forces |
| `m_xD+_max`, `m_xD-_max`, `m_yD+_max`, `m_yD-_max` | Maximum moments |
| `n_xD_max`, `n_yD_max` | Maximum normal forces |

**Important**: Each (zone, max_for_column) combination appears **twice** in the envelope - once for ULS and once for SLS freq.

### 2. Data Processing for IDEA

**Module**: `src/integrations/idea_integration/scia_to_idea_functions.py`

**Function**: `process_scia_cs_results_for_idea()`

**Processing Steps**:
1. Calls `extract_cs_force_envelopes()` to get filtered envelope data
2. Adds `_max` suffix to force column names for consistency
3. Returns processed DataFrame ready for IDEA application

**Module**: `src/integrations/idea_integration/idea_interface.py`

**Function**: `_process_scia_cs_results_for_idea_input()`

**Additional Processing**:
- Adds `Mx` column: selects value with maximum absolute magnitude from `m_xD+_max` and `m_xD-_max`
- Adds `My` column: selects value with maximum absolute magnitude from `m_yD+_max` and `m_yD-_max`
- Adds `Nx` and `Ny` columns: direct copies of `n_xD_max` and `n_yD_max`

### 3. IDEA Extreme Creation

**Module**: `src/integrations/idea_integration/idea_interface.py`

**Function**: `_apply_cs_loads_to_slabs()`

**IDEA Model Structure**:
- Each slab corresponds to a specific thickness and reinforcement configuration
- Each slab has two directions: `langs` (longitudinal) and `dwars` (transverse)
- Zones are mapped to slabs based on thickness and reinforcement zone configuration

**Extreme Creation Logic**:

For each unique `(zone, max_for_column)` combination:

1. **Extract Data**:
   - Get ULS row for this combination
   - Get SLS freq row for this combination

2. **Create Two Extremes** (one per direction):

   **Direction: "langs"** (uses SCIA Y-direction forces):
   - Shear force (Qz): `v_y_max` from ULS and SLS freq
   - Bending moment (My): `My` from ULS and SLS freq
   - Normal force (N): `Ny` from ULS and SLS freq (if supported)
   
   **Direction: "dwars"** (uses SCIA X-direction forces):
   - Shear force (Qz): `v_x_max` from ULS and SLS freq
   - Bending moment (My): `Mx` from ULS and SLS freq
   - Normal force (N): `Nx` from ULS and SLS freq (if supported)

3. **Combine Load Types**:
   - `fundamental` = internal forces from ULS row (ultimate limit state)
   - `frequent` = internal forces from SLS freq row (serviceability frequent)

4. **Name Format**:
   ```
   {slab_key}_{direction}-{zone}-{cs_name}-{coords}-{max_for}-ULS:{belasting_uls}/SLS:{belasting_sls}
   ```
   
   Example:
   ```
   CS_d0.4_1_langs-1-1-SEC_Z1_1_y0.500-(10.5,0.5,0.0)-v_y-ULS:BG_4003/SLS:BG_SLS_Kar
   ```

**Extreme Count Example**:

For zone "1-1" with 8 force components to maximize:
- `v_x`, `v_y`, `m_xD+`, `m_xD-`, `m_yD+`, `m_yD-`, `n_xD`, `n_yD`
- Each appears twice in envelope (ULS + SLS freq)
- Creates **16 total extremes**: 8 combinations × 2 directions

## Force Direction Mapping

| SCIA Direction | Force Type | IDEA Direction | IDEA Parameter |
|----------------|------------|----------------|----------------|
| Y-direction | Shear | langs | Qz |
| Y-direction | Moment | langs | My |
| Y-direction | Normal | langs | N |
| X-direction | Shear | dwars | Qz |
| X-direction | Moment | dwars | My |
| X-direction | Normal | dwars | N |

**Note**: IDEA's coordinate system for cross-sections is different from SCIA's global coordinates. The mapping ensures forces are applied correctly relative to the cross-section orientation.

## Key Design Decisions

### Why Two Extremes Per Combination?

Each cross-section must be checked for forces in both principal directions:
- **langs**: Longitudinal reinforcement direction (typically along bridge axis)
- **dwars**: Transverse reinforcement direction (typically across bridge width)

The same SCIA load combination produces different critical forces depending on which direction is being checked.

### Why Combine ULS and SLS Freq?

IDEA StatiCa requires both limit states for comprehensive section checks:
- **Fundamental (ULS)**: Checks ultimate capacity (yielding, crushing)
- **Frequent (SLS freq)**: Checks serviceability (crack widths, stresses)

### Why Remove SLS Characteristic?

The SLS characteristic combination is not used in the current IDEA analysis workflow. Only frequent serviceability checks are performed.

### Normal Force Support

Normal forces (`n_xD`, `n_yD`) were added to support:
- Compression/tension from axial loading
- Combined bending and axial force interaction
- More accurate capacity calculations

**Note**: Some IDEA builder versions may not support the `N` parameter. The code includes fallback logic to handle this gracefully.

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ SCIA Engineer Analysis Results                                  │
│ - Interne 2D-krachten basis ULS                                 │
│ - Interne 2D-krachten basis SLS freq                            │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ extract_cs_force_envelopes()                                     │
│ - Combines ULS and SLS freq tables                              │
│ - Filters by zones (1-1, 1-2, 2-1, 2-2, 3-1, 3-2)              │
│ - Adds result_type column                                       │
│ - Keeps both ULS and SLS freq rows for each (zone, max_for)    │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ process_scia_cs_results_for_idea()                               │
│ - Renames columns with _max suffix                              │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ _process_scia_cs_results_for_idea_input()                        │
│ - Adds Mx, My (max absolute from ± directions)                  │
│ - Adds Nx, Ny (copies of normal forces)                         │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ _apply_cs_loads_to_slabs()                                       │
│ For each (zone, max_for_column):                                │
│   1. Get ULS row                                                │
│   2. Get SLS freq row                                           │
│   3. Create "langs" extreme (v_y, My, Ny)                       │
│      - fundamental = ULS values                                 │
│      - frequent = SLS freq values                               │
│   4. Create "dwars" extreme (v_x, Mx, Nx)                       │
│      - fundamental = ULS values                                 │
│      - frequent = SLS freq values                               │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ IDEA StatiCa RCS Model                                          │
│ - Extremes applied to slabs                                     │
│ - Ready for capacity analysis                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Code References

### Key Files
- `src/integrations/scia_integration/scia_results_processor.py` - SCIA result extraction
- `src/integrations/idea_integration/scia_to_idea_functions.py` - Data processing bridge
- `src/integrations/idea_integration/idea_interface.py` - IDEA model application
- `src/integrations/scia_integration/constants/results.py` - Table name patterns

### Key Constants
```python
CS_TABLE_TYPES = ("ULS", "SLS freq")  # No more SLS kar
CS_BASIS_TABLE_PATTERN = "Interne 2D-krachten basis {table_type}"
```

### Force Columns
```python
# Input columns (from SCIA)
force_cols = ["v_x", "v_y", "m_xD+", "m_xD-", "m_yD+", "m_yD-", "n_xD", "n_yD"]

# Output columns (for IDEA)
# With _max suffix: v_x_max, v_y_max, etc.
# Plus derived: Mx, My, Nx, Ny
```

## Future Enhancements

Potential improvements to the data flow:

1. **Support for Additional Load Combinations**: Extend beyond ULS and SLS freq
2. **Dynamic Zone Detection**: Automatically detect zones from SCIA model
3. **Load Case Filtering**: Allow users to select which load cases to process
4. **Performance Optimization**: Cache envelope data to avoid reprocessing
5. **Validation Checks**: Add data quality checks before IDEA application

## Troubleshooting

### Common Issues

**Problem**: IDEA results show N/A
- **Cause**: No extremes created for a slab/zone
- **Solution**: Check that zone names match between SCIA results and IDEA slab configuration

**Problem**: Missing force components
- **Cause**: Table name pattern mismatch
- **Solution**: Verify `CS_BASIS_TABLE_PATTERN` matches SCIA result table names

**Problem**: Wrong number of extremes
- **Cause**: Duplicate rows in envelope or missing ULS/SLS freq pairs
- **Solution**: Check `extract_cs_force_envelopes()` filtering logic

### Debug Tips

1. **Check Envelope Data**: Print or export the envelope DataFrame to verify structure
2. **Verify Zone Matching**: Ensure SCIA zones match IDEA slab zone assignments
3. **Count Extremes**: Each (zone, max_for_column) should create exactly 2 extremes
4. **Check Force Values**: Verify forces are non-zero and reasonable magnitude

## Related Documentation

- `docs/scia_cs_results_processing.md` - Detailed SCIA CS results extraction
- `docs/architecture.md` - Overall project architecture
- `docs/pydantic_developer_guide.md` - Data model documentation
