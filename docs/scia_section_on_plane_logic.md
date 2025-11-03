# SCIA Section on Plane Logic Documentation

## Overview

This document explains how the `scia_section_on_plane.py` module creates 2D section planes for bridge analysis in SCIA Engineer. Section planes are used to extract internal forces and stresses at specific locations in the 3D bridge model.

The module implements a sophisticated grid system that adapts to:
- **Intermediate segment boundaries** within spans
- **Zone boundaries** between different bridge cross-section zones (bz1, bz2, bz3)
- **Special cases** for narrow middle zones (bz2 ≤ 1.002m)

## Key Concepts

### Section Types

The module creates two types of section planes:

1. **X-direction sections** (horizontal, extending in x-direction)
   - Fixed length: 1.0m in the x-direction
   - Positioned at different y-coordinates across the bridge width
   - Spaced every 0.5m in both x and y directions

2. **Y-direction sections** (vertical, extending downward in y-direction)
   - Fixed length: 1.0m in the y-direction (downward from start point)
   - Positioned at different x-coordinates along the bridge length
   - Spaced every 0.5m in both x and y directions

### Bridge Geometry

**Coordinate System**:
- X-axis: Along bridge length (longitudinal)
- Y-axis: Across bridge width (transverse), positive upward
- Z-axis: Horizontal perpendicular to bridge axis

**Zone Structure** (in y-direction):
```
        y = bz2/2 + bz1
    ┌─────────────────┐
    │      bz1        │ (Top zone)
    ├─────────────────┤ ← Zone boundary 1: y = bz2/2
    │      bz2        │ (Middle zone, centered at y=0)
    ├─────────────────┤ ← Zone boundary 2: y = -bz2/2
    │      bz3        │ (Bottom zone)
    └─────────────────┘
        y = -(bz2/2 + bz3)
```

**Span Structure** (in x-direction):
- A span is defined by two supports (start and end)
- May contain intermediate segments without supports
- Each segment boundary is tracked as an `intermediate_segment_x_position`

## Constants

Defined in `src/integrations/scia_integration/constants/geometry.py`:

- **SECTION_ON_PLANE_LENGTH**: 1.0m - length of each section
- **SECTION_ON_PLANE_SPACING**: 0.5m - spacing between section positions
- **SECTION_ON_PLANE_OFFSET_FACTOR**: 0.9 - edge offset factor (0.9 × min_thickness)
- **SECTION_ON_PLANE_INTERMEDIATE_OFFSET**: 0.001m (1mm) - offset from boundaries
- **SECTION_ON_PLANE_TOLERANCE**: 0.01m (10mm) - tolerance for boundary detection

## Section Creation Algorithm

### Step 1: Span Identification

The `_identify_spans()` function groups segments into spans:
- A span starts with a segment where `is_first_segment == True`
- Continues until the next segment with `is_first_segment == True` or end of segments
- For each span, calculates:
  - `num_segment_definitions`: Count of segment definition points (including start/end supports)
  - `intermediate_segment_x_positions`: X-coordinates of intermediate boundaries

Example:
```
Segments: [seg0 (l=0, is_first=True), seg1 (l=3m), seg2 (l=5m)]
→ Span with 3 segment definitions at x = [0, 3, 8]m
→ Intermediate boundaries at x = [3]m
```

### Step 2: X-Direction Section Generation

For each span:

1. **Generate initial x-positions**:
   - Start: `x_start_limit + OFFSET_FACTOR × min_thickness`
   - End: `x_end_limit - OFFSET_FACTOR × min_thickness`
   - Spacing: Every 0.5m
   - Add final position at end if needed

2. **Filter for intermediate segment boundaries** (if `num_segment_definitions > 2`):
   - Remove sections that cross intermediate boundaries
   - Add shortened sections ending 0.001m before each boundary
   - Add sections starting 0.001m after each boundary
   - Ensure mandatory sections exist at all boundaries

3. **Generate y-positions** (where to place x-direction sections):
   - Start: `y_top` (outer edge of bz1)
   - End: `y_bottom` (outer edge of bz3)
   - Spacing: Every 0.5m downward

4. **Filter y-positions for zone boundaries**:
   - Remove positions on zone boundaries
   - Add positions at `boundary ± 0.001m`

5. **Special handling for narrow bz2** (if `bz2 ≤ 1.002m`):
   - Add x-direction sections at y=0 (centerline of bz2)
   - Uses all x-positions respecting intermediate boundaries

6. **Create section definitions**:
   - For each (x_pos, y_pos) combination
   - Section extends from `x_pos` to `x_pos + 1.0m`
   - Positioned at height `y_pos`

### Step 3: Y-Direction Section Generation

For each span:

1. **Generate initial x-positions** (where to place y-direction sections):
   - Same as x-direction positions
   - Also filtered for intermediate boundaries if needed

2. **Generate y-positions** (starting points for downward sections):
   - Start: `y_top`
   - End: `y_bottom + section_length` (so bottom reaches `y_bottom`)
   - Spacing: Every 0.5m

3. **Filter and adjust for zone boundaries**:
   - Remove sections that start/end exactly on boundaries
   - Remove sections that cross boundaries
   - Add edge sections at each boundary:
     - Section ending 0.001m above boundary
     - Section starting 0.001m below boundary
   - **Strict tolerance check** (0.0005m): Remove sections within 0.0005m of boundaries
     - Allows intentional 0.001m offset sections
     - Blocks unintentional boundary-touching sections

4. **Special handling for narrow bz2** (if `bz2 ≤ 1.002m`):
   - Add y-direction sections spanning the full height of bz2
   - Start: `(bz2/2) - 0.001m` (just below top boundary)
   - End: `(-bz2/2) + 0.001m` (just above bottom boundary)
   - Length: approximately `bz2 - 0.002m`
   - Uses x-positions respecting intermediate boundaries

5. **Create section definitions**:
   - For each (x_pos, y_pos) combination
   - Section extends downward from `y_pos` to `y_pos - 1.0m`
   - Positioned at `x_pos`

## Boundary Handling Details

### Intermediate Segment Boundaries (X-Direction)

**Problem**: Sections cannot cross segment boundaries where material properties or geometry change.

**Solution**: `_filter_and_adjust_x_direction_sections()`
1. Check each section: does it cross a boundary?
2. If yes:
   - Add section ending at `boundary - 0.001m`
   - Add section starting at `boundary + 0.001m`
3. Ensure all boundaries have sections (even if no regular section crossed them)
4. Track which boundaries have sections to prevent duplicates

**Example**:
```
Regular section at x=2.5m would span [2.5, 3.5]m
Boundary at x=3.0m
→ Replace with:
   - Section [2.0, 3.0-0.001]m (ends before boundary)
   - Section [3.0+0.001, 4.0+0.001]m (starts after boundary)
```

### Zone Boundaries (Y-Direction)

**Problem**: X-direction sections at certain y-coordinates would cross zone boundaries. Y-direction sections extending downward might cross zone boundaries.

**Solution for X-direction sections**: `_filter_y_positions_for_zone_boundaries_x_sections()`
1. Remove y-positions on boundaries
2. Add y-positions at `boundary ± 0.001m`

**Solution for Y-direction sections**: `_filter_and_adjust_y_positions_for_zone_boundaries()`
1. Remove sections starting or ending on boundaries
2. Remove sections crossing boundaries
3. Add edge sections:
   - Ending `0.001m` above boundary (top side)
   - Starting `0.001m` below boundary (bottom side)
4. **Strict tolerance check**: Remove any remaining sections within 0.0005m of boundaries
   - This catches sections that might touch boundaries due to rounding
   - Preserves the intentional 0.001m offset sections

**Example (Y-direction):**
```
Zone boundary at y=0.25m (bz1/bz2)
Regular sections might be at y=[1.25, 0.75, 0.25, -0.25, -0.75]m

After filtering:
- Remove y=0.25m (on boundary)
- Add y=0.251m (above boundary)
- Add y=0.249m (below boundary)
→ Final: [1.25, 0.75, 0.251, 0.249, -0.25, -0.75]m

For each y-position, section extends down 1.0m
- Section at y=0.75m: from 0.75 to -0.25m → CROSSES boundary at 0.25m → REMOVED
- Section at y=1.25m: from 1.25 to 0.25m → ENDS ON boundary → REMOVED  
- Edge section at y=1.249m: from 1.249 to 0.249m → 0.001m above boundary → KEPT
- Edge section at y=0.249m: from 0.249 to -0.751m → starts 0.001m below, crosses -0.25m boundary → REMOVED in strict check
```

## Special Case: Narrow bz2 Zones

When `bz2 ≤ 1.002m`, the middle zone is too narrow for regular section coverage. The module adds special sections:

### Special X-Direction Sections
- Positioned at y=0 (centerline of bz2)
- Uses all x-positions (respecting intermediate segment boundaries)
- Provides horizontal coverage through the middle zone

### Special Y-Direction Sections
- Span the full interior height of bz2
- Start: `y = (bz2/2) - 0.001m` ≈ 0.249m (for bz2=0.5m)
- End: `y = (-bz2/2) + 0.001m` ≈ -0.249m (for bz2=0.5m)
- Section length: approximately `bz2 - 0.002m` ≈ 0.498m
- Uses x-positions respecting intermediate boundaries
- Provides vertical coverage through the narrow middle zone

**Rationale**: With regular 1.0m sections and 0.5m spacing, a zone narrower than 1.002m cannot fit regular sections without crossing boundaries. These special shorter sections ensure complete coverage.

## Code Structure

### Main Functions

- **`create_section_definitions(params)`**: Main entry point
  - Identifies spans
  - Creates x-direction and y-direction sections for each span
  - Applies all filtering and boundary handling
  - Returns list of `SectionOnPlaneDefinition` objects

- **`create_all_sections_on_plane(params, model_builder)`**: Wrapper function
  - Calls `create_section_definitions()`
  - Uses SCIA model builder to add sections to model

### Helper Functions

- **`_identify_spans(segments)`**: Groups segments into spans
- **`_create_span_from_segments(...)`**: Creates `Span` dataclass from segment list
- **`_filter_and_adjust_x_direction_sections(...)`**: Handles intermediate boundaries for x-sections
- **`_add_intermediate_boundary_positions(...)`**: Adds x-positions at intermediate boundaries for y-sections
- **`_filter_y_positions_for_zone_boundaries_x_sections(...)`**: Filters y-coords for x-sections
- **`_filter_and_adjust_y_positions_for_zone_boundaries(...)`**: Filters y-positions for y-sections, adds edge sections

### Data Classes

- **`Span`**: Represents a bridge span
  - Geometric properties (start_x, end_x, bz1, bz2, bz3, etc.)
  - `num_segment_definitions`: Count of segment definition points
  - `intermediate_segment_x_positions`: List of intermediate boundary x-coordinates

## Tolerance Management

The module uses two tolerance values:

1. **SECTION_ON_PLANE_TOLERANCE** (0.01m):
   - Used for initial boundary detection
   - Determines if a section is "close enough" to a boundary to be considered problematic

2. **Strict Tolerance** (0.0005m):
   - Used in final filtering for y-direction sections
   - Calculated as `SECTION_ON_PLANE_INTERMEDIATE_OFFSET / 2`
   - Blocks sections within 0.5mm of boundaries
   - Allows sections exactly 1mm offset from boundaries

This two-tier system ensures:
- Intentional offset sections (at 1mm) are preserved
- Accidental boundary-touching sections are removed
- No sections end up exactly on boundaries

## Example: Complete Section Generation

For a span with:
- Length: 8m (x: 0 to 8m)
- bz1 = 2.0m, bz2 = 0.5m, bz3 = 4.2m
- 3 segment definitions at x = [0, 3, 8]m (intermediate boundary at x=3m)
- min_thickness = 0.3m

**Zone boundaries**:
- bz1/bz2: y = 0.5/2 = 0.25m
- bz2/bz3: y = -0.5/2 = -0.25m

**X-direction sections**:
1. X-positions (initial): [0.27, 0.77, 1.27, ..., 7.73]m (spacing 0.5m, edge offset 0.9×0.3=0.27m)
2. X-positions (after filtering for x=3m boundary): [0.27, 0.77, ..., 2.27, 2.999, 3.001, 3.501, ..., 7.73]m
3. Y-positions: [2.25, 1.75, ..., 0.251, 0.249, -0.249, -0.251, ..., -4.45]m (with boundary offsets)
4. Special sections at y=0 (bz2 ≤ 1.002m): All x-positions × y=0
5. Total: Approximately 13 x-positions × 17 y-positions = 221 x-direction sections

**Y-direction sections**:
1. X-positions: Same as x-direction (filtered for intermediate boundary)
2. Y-positions (initial): [2.25, 1.75, ..., -3.45]m
3. Y-positions (after zone boundary filtering + edge sections): Approximately 11 positions
4. Special spanning sections (bz2 ≤ 1.002m): 13 x-positions × 1 special y-section
5. Total: Approximately (13 × 11) + 13 = 156 y-direction sections

**Grand total**: Approximately 377 section definitions for this span

## Related Files

- **Implementation**: `src/integrations/scia_integration/model/scia_section_on_plane.py`
- **Constants**: `src/integrations/scia_integration/constants/geometry.py`
- **Data Models**: `src/data_models/scia_models.py` (`SectionOnPlaneDefinition`)
- **Usage Example**: `app/bridge/scia_model_builder.py` (calls via `define_complete_bridge_model()`)

## Version History

- **Initial implementation**: Basic section grid with regular spacing
- **Intermediate boundary support**: Added filtering for multi-segment spans  
- **Zone boundary support**: Added filtering for zone boundaries
- **Narrow bz2 support**: Added special sections for zones ≤ 1.002m wide
- **Strict tolerance**: Added two-tier tolerance system for precise boundary handling
