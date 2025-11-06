# SCIA CS Results Processing Documentation

## Overview

This document explains how SCIA Engineer Cross Section (CS) results are processed, filtered, and displayed in the VIKTOR application.

## Architecture

The SCIA results processing is divided into three main layers:

1. **Data Processing Layer** (`src/integrations/scia_integration/results/scia_results_processor.py`)
2. **View Layer** (`src/integrations/scia_integration/results/scia_result_views.py`)
3. **Controller Layer** (`app/bridge/bridgeController/scia_integration.py`)

---

## 1. Data Processing Layer

### Main Processing Function: `process_scia_cs_results()`

This function orchestrates the entire CS results processing pipeline:

```python
def process_scia_cs_results(results, bridge_segments) -> dict[str, pd.DataFrame]:
    """Process CS results for ULS and SLS freq analysis types."""
```

**Input:**
- `results`: Dictionary containing SCIA XML output data
- `bridge_segments`: List of bridge segment objects for zone mapping

**Output:**
- Dictionary with keys `"ULS"` and `"SLS freq"`, each containing a processed DataFrame

**Processing Steps:**
1. Loops through analysis types: `"ULS"` and `"SLS freq"` (SLS kar is no longer used)
2. Finds the corresponding CS tables in the SCIA results
3. Calls `_process_single_cs_result_table()` for each table
4. Returns dictionary of processed DataFrames

---

### Single Table Processing: `_process_single_cs_result_table()`

This function processes a single CS result table (either ULS or SLS freq):

```python
def _process_single_cs_result_table(table_data, table_type, bridge_segments) -> pd.DataFrame:
```

**Processing Pipeline:**

#### Step 1: Data Extraction
- Extracts "basis" data (basic load combinations) from the table
- Extracts "elementaire" data (individual load cases) from the table
- Coordinates are parsed from the table (format: `"[x, y, z]"`)
- Uses `find_2d_force_tables_cs()` which tries p1 (sections) first, then falls back to p0 (nodes) if needed

#### Step 2: Data Merging
- Merges basis and elementaire DataFrames on columns: `["Naam", "coords_xyz", "Belasting"]`
- Uses outer join to keep all combinations
- Renames columns: `"Naam"` → `"name"`, `"Belasting"` → `"belasting"`

#### Step 3: Force Column Conversion
- Converts force/moment columns to numeric:
  - `v_x`, `v_y` (shear forces)
  - `m_xD+`, `m_xD-`, `m_yD+`, `m_yD-` (bending moments)
  - `n_xD`, `n_yD` (normal forces)

#### Step 4: Coordinate Deduplication
- Each CS has data at two coordinates (start and end of section line)
- The values at both coordinates are identical
- Keeps only the first coordinate per CS name using:
  ```python
  df.groupby("name").apply(lambda group: group[group["coords_xyz"] == group["coords_xyz"].iloc[0]])
  ```

#### Step 5: Force Envelope Extraction
- For each unique `(name, coords_xyz)` combination:
  - Finds the row with **maximum absolute value** for each of the 8 force components
  - This results in up to 8 rows per CS location
  - Adds column `"max_for_column"` to track which force component each row represents

#### Step 6: Zone Mapping
- Maps each CS section to a bridge zone (e.g., "zone_1", "zone_2")
- Uses `_map_cs_section_to_zone()` which:
  - Extracts X-coordinate from the CS name
  - Compares against bridge segment boundaries (based on cumulative widths)
  - Assigns appropriate zone label

**Output DataFrame Columns:**
- `name`: CS section name (e.g., "CS_D1_L", "CS_D2_R")
- `coords_xyz`: Coordinate string (e.g., "[1.5, 2.0, 0.0]")
- `belasting`: Load case/combination name
- `v_x`, `v_y`: Shear forces
- `m_xD+`, `m_xD-`, `m_yD+`, `m_yD-`: Bending moments
- `n_xD`, `n_yD`: Normal forces
- `max_for_column`: Which force component this row represents the maximum for
- `zone`: Bridge zone identifier (e.g., "zone_1")

---

### Envelope Extraction: `extract_cs_force_envelopes()`

This function combines ULS and SLS freq results to create a comprehensive envelope:

```python
def extract_cs_force_envelopes(results, bridge_segments) -> pd.DataFrame:
```

**Purpose:** 
For each zone and analysis type (ULS/SLS freq), find the rows with maximum absolute values for all 8 force components.

**Processing Steps:**

1. **Get Processed Results:**
   - Calls `process_scia_cs_results()` to get ULS and SLS freq DataFrames

2. **Add Result Type Column:**
   - Adds `"result_type"` column to each DataFrame ("ULS" or "SLS freq")

3. **Combine DataFrames:**
   - Concatenates ULS and SLS freq DataFrames

4. **Extract Envelopes per Zone and Result Type:**
   - Groups by `(zone, result_type)` combinations
   - For each force column (`v_x`, `v_y`, `m_xD+`, etc.):
     - Finds the row with maximum absolute value
     - Adds row to result with `"max_for_column"` indicator
   - Uses deduplication tracking with set of `(zone, result_type, force_col, index)` tuples to prevent duplicates

5. **Sort Results:**
   - Sorts by: `zone` → `result_type` → `max_for_column`

**Output:**
- DataFrame with **16 rows per zone** (8 force components × 2 result types)
- Shows both ULS and SLS freq maximum values for each force component
- Example: Zone 1 will have:
  - ULS row with max v_x
  - SLS freq row with max v_x
  - ULS row with max v_y
  - SLS freq row with max v_y
  - ... (and so on for all 8 force components)

---

## 2. View Layer

### Individual CS Table View: `create_scia_cs_results_table()`

Creates a formatted table for a single analysis type (ULS or SLS freq):

**Steps:**
1. Calls `process_scia_cs_results()` to get processed data
2. Selects the appropriate DataFrame (ULS or SLS freq)
3. Formats coordinates for display using `format_coordinates_safe()`
4. Applies unit conversions (N/m → kN/m, Nm/m → kNm/m)
5. Rounds values to 2 decimal places
6. Removes technical columns (`coords_xyz`, `max_for_column`)
7. Returns `TableResult` with formatted data

**Display Columns:**
- Zone, Name, Coordinates, Belasting
- v_x [kN/m], v_y [kN/m]
- m_xD+ [kNm/m], m_xD- [kNm/m], m_yD+ [kNm/m], m_yD- [kNm/m]
- n_xD [kN/m], n_yD [kN/m]

---

### Envelope Table View: `create_scia_cs_envelope_table()`

Creates the combined ULS + SLS freq envelope table:

**Steps:**
1. Calls `extract_cs_force_envelopes()` to get combined envelope data
2. Formats coordinates for display
3. Applies unit conversions
4. Rounds values to 2 decimal places
5. Removes technical columns
6. Returns `TableResult` with envelope data

**Display Columns:**
- Same as individual CS table, plus:
- `result_type`: "ULS" or "SLS freq" (indicates which analysis the row came from)
- `max_for_column`: Which force component this row represents (e.g., "v_x", "m_yD+")

---

## 3. Controller Layer

### SCIA Integration Component

**View Methods:**

1. **`get_scia_cs_results_view_uls()`**
   - Displays ULS CS results only
   - Decorated with `@TableView("SCIA CS ULS")`

2. **`get_scia_cs_results_view_sls_freq()`**
   - Displays SLS freq CS results only
   - Decorated with `@TableView("SCIA CS SLS freq")`

3. **`get_scia_results_table()`**
   - Displays combined envelope table (ULS + SLS freq)
   - Decorated with `@TableView("SCIA Analyse Resultaten")`
   - Shows 16 rows per zone (8 force components × 2 analysis types)

**Common Flow:**
1. Validate bridge segments exist
2. Get entity ID for caching
3. Load cached SCIA results or trigger new analysis
4. Call appropriate view creation function
5. Return `TableResult` for display

---

## Data Flow Summary

```
SCIA XML Results
       ↓
find_2d_force_tables_cs() - Extract CS tables (try p1, fallback to p0)
       ↓
_process_single_cs_result_table() - Process each table (ULS, SLS freq)
       ├─ Merge basis + elementaire data
       ├─ Convert force columns to numeric
       ├─ Deduplicate coordinates (keep first per CS)
       ├─ Extract force envelopes (8 rows per CS)
       └─ Map to bridge zones
       ↓
process_scia_cs_results() - Returns dict with ULS and SLS freq DataFrames
       ↓
       ├─ create_scia_cs_results_table() - Individual table view
       │      ↓
       │  Format → Convert units → Return TableResult
       │
       └─ extract_cs_force_envelopes() - Combined envelope
              ├─ Add result_type column
              ├─ Combine ULS + SLS freq
              ├─ Extract max absolute per (zone, result_type, force)
              └─ Sort by zone, result_type, force
                     ↓
              create_scia_cs_envelope_table()
                     ↓
              Format → Convert units → Return TableResult
```

---

## Key Design Decisions

### Why Cross Sections (CS)?
- CS results provide force/moment values **per meter width** of the bridge deck
- More suitable for plate-like structures than node or beam results
- Directly applicable for concrete reinforcement design

### Why Remove SLS kar?
- Only ULS and SLS freq are needed for design calculations
- Reduces data volume and processing time
- Simplifies user interface

### Why 8 Rows per CS Location?
- Need to capture maximum values for all force components:
  - 2 shear forces: v_x, v_y
  - 4 bending moments: m_xD+, m_xD-, m_yD+, m_yD-
  - 2 normal forces: n_xD, n_yD
- Each component's maximum may occur under different load cases

### Why Show Both ULS and SLS freq?
- Different analysis types for different design checks:
  - ULS: Ultimate limit state (strength design)
  - SLS freq: Serviceability limit state - frequent combination (crack width, deflection)
- Designer needs both for complete assessment

### Why Coordinate Deduplication?
- SCIA outputs CS data at both start and end coordinates of the section line
- Values are identical at both locations
- Keeping only one reduces data volume by 50% without losing information

### Why Zone Mapping?
- Groups CS results by bridge segment zones
- Facilitates comparison across bridge length
- Enables zone-specific design decisions

---

## Future Improvements

- Add filtering options in the UI (by zone, force component)
- Export to Excel with formatting
- Add visualization (force diagrams per zone)
- Link directly to IDEA StatiCa reinforcement design

---

## Related Files

- **Processing:** `src/integrations/scia_integration/results/scia_results_processor.py`
- **Views:** `src/integrations/scia_integration/results/scia_result_views.py`
- **Controller:** `app/bridge/bridgeController/scia_integration.py`
- **Constants:** `src/integrations/scia_integration/constants/results.py`
- **Tests:** `tests/test_src/test_integrations/test_scia_result_views_unit_conversion.py`
