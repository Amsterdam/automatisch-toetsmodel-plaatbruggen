# Plan: Integration of "Section on 2D-member" (SectionOnPlane)

## Goal

Add `SectionOnPlane` objects to the SCIA model to retrieve calculation results at
cross-section positions. These run in a **separate template** (`model_governing_sectionsonplane.esa`)
and are kept fully isolated from the existing integration-strip code.

---

## Placement Logic

| Parameter | Value |
|---|---|
| Max section length | 1.0 m |
| Overlap with previous section | 0.5 m |
| Step between section starts | 0.5 m |

### Algorithm (per zone, per segment, per axis direction)

```
sections_on_plane_positions:
    start = zone_x_start
    while start + SECTION_LENGTH <= zone_x_end:
        point_1 = (start, y_center, 0)  # only X-direction
        point_2 = (start + SECTION_LENGTH, y_center, 0)
        yield SectionOnPlane(point_1, point_2, ...)
        start += STEP                    # 0.5 m

    # Last "fit" section covering remaining end
    remaining = zone_x_end - (start - STEP + SECTION_LENGTH)
    if remaining > 0:
        fit_start = zone_x_end - STEP   # = end - 0.5 m
        point_1 = (fit_start, y_center, 0)
        point_2 = (zone_x_end, y_center, 0)
        yield SectionOnPlane(point_1, point_2, ...)
```

**Example** — zone length = 1.7 m → sections starting at **0.0, 0.5, 1.2** (last = 1.7 − 0.5).

The y-coordinate for each section follows the same zone-center logic used for
integration strips (`_calculate_zone_boundaries` → mid-point of `[y_min, y_max]`).

---

## Architecture

### Modules to create

| File | Role |
|---|---|
| `src/integrations/scia_integration/model/scia_sections_on_plane.py` | Placement calculations and builder calls — mirrors `scia_integration_strips.py` |
| `src/integrations/scia_integration/results/scia_sections_on_plane_processor.py` | Parse raw SCIA output tables for sections on plane |
| `src/integrations/scia_integration/results/scia_sections_on_plane_views.py` | Helper that formats results into VIKTOR `TableResult` |

### Modules to modify

| File | Change |
|---|---|
| `src/integrations/scia_integration/model/scia_model_interface.py` | Add `create_section_on_plane` to `SciaModelBuilder` Protocol |
| `app/bridge/scia_model_builder.py` | Implement `create_section_on_plane` in `ViktorSciaModelBuilder`; add `self.sections_on_plane: dict[str, scia.SectionOnPlane]` |
| `src/integrations/scia_integration/constants/paths.py` | Add `SCIA_TEMPLATE_SECTIONS_ON_PLANE_PATH` |
| `src/integrations/scia_integration/model/scia_model.py` | Add `define_bridge_model_sections_on_plane(builder, params)` — calls `create_bridge_geometry`, supports, loads, **and** `create_all_sections_on_plane`. Does **not** call `create_all_integration_strips`. |
| `app/bridge/scia_model_builder.py` (top-level functions) | Add `setup_bridge_analysis_sections_on_plane` and `get_scia_analysis_results_sections_on_plane` that use the new template and model function |
| `app/bridge/bridgeController/scia_integration.py` | Add new `@TableView` methods for SectionOnPlane results (separate section) |

---

## Detailed Step-by-Step

### Step 1 — Path constant

```python
# src/integrations/scia_integration/constants/paths.py
SCIA_TEMPLATE_SECTIONS_ON_PLANE_PATH = (
    SCIA_RESOURCES_PATH / "templates" / "model_governing_sectionsonplane.esa"
)
```

---

### Step 2 — Protocol extension

Add to `SciaModelBuilder` in `scia_model_interface.py`:

```python
def create_section_on_plane(
    self,
    point_1: tuple[float, float, float],
    point_2: tuple[float, float, float],
    *,
    name: str,
    draw: Any | None = None,
    direction_of_cut: tuple[float, float, float] | None = None,
) -> SciaSectionOnPlane:
    """
    Creates a section on a 2D-member plane.

    :param point_1: Start position (x, y, z) in [m]
    :param point_2: End position (x, y, z) in [m]
    :param name: Name shown in SCIA
    :param draw: Plane in which the section is drawn (default: Z_DIRECTION)
    :param direction_of_cut: In-plane cut direction vector (default: (0, 0, 1))
    :return: Created SectionOnPlane object
    """
    ...
```

---

### Step 3 — Concrete builder implementation

In `ViktorSciaModelBuilder`:

```python
# __init__
self.sections_on_plane: dict[str, scia.SectionOnPlane] = {}

# method
def create_section_on_plane(
    self,
    point_1: tuple[float, float, float],
    point_2: tuple[float, float, float],
    *,
    name: str,
    draw: Any | None = None,
    direction_of_cut: tuple[float, float, float] | None = None,
) -> scia.SectionOnPlane:
    section = self.model.create_section_on_plane(
        point_1=point_1,
        point_2=point_2,
        name=name,
        draw=draw,
        direction_of_cut=direction_of_cut,
    )
    self.sections_on_plane[name] = section
    return section
```

> The SCIA SDK's `Model.create_section_on_plane` method signature matches the
> API described in the user request. Verify the exact module path when the new
> ESA template is available.

---

### Step 4 — Placement module `scia_sections_on_plane.py`

```
src/integrations/scia_integration/model/scia_sections_on_plane.py
```

#### Constants

```python
SECTION_LENGTH = 1.0   # m — maximum section length
SECTION_STEP   = 0.5   # m — step between section starts (= SECTION_LENGTH - overlap)
```

#### Naming convention

```
sec_{zone}_{direction}_nr-{number}
# e.g.  sec_Z1-1_x_nr-1,  sec_Z2-2_x_nr-3
```

(Analogous to the strip naming but with prefix `sec_`.)

#### Core functions

```python
def _calculate_section_starts(
    zone_x_start: float,
    zone_x_end: float,
) -> list[float]:
    """
    Return list of section start positions covering [zone_x_start, zone_x_end].

    Full 1 m sections every 0.5 m; last section is a fit ending at zone_x_end.
    """

def _create_sections_for_zone(
    builder: SciaModelBuilder,
    zone_name: str,
    zone_position: int,
    segment_idx: int,
    params: Any,
) -> None:
    """
    Create all SectionOnPlane objects for one zone (X-direction only).

    The y-coordinate is the mid-point of the zone's y-boundaries.
    The z-coordinate is 0.0 (bridge deck plane).
    direction_of_cut defaults to (0, 0, 1) (SDK default).
    """

def create_all_sections_on_plane(builder: SciaModelBuilder, params: Any) -> None:
    """
    Entry point: create sections for every zone and every segment.

    Called from `define_bridge_model_sections_on_plane` in scia_model.py.
    """
```

---

### Step 5 — Model orchestration

Add to `scia_model.py`:

```python
from .scia_sections_on_plane import create_all_sections_on_plane

def define_bridge_model_sections_on_plane(
    builder: SciaModelBuilder,
    params: Any,
) -> None:
    """
    Build the complete SCIA model that uses sections-on-plane.

    Uses the same geometry, supports, loads, and combinations as
    `define_complete_bridge_model`, but replaces integration strips
    with sections on plane.
    """
    plate_names = create_bridge_geometry(builder, params)

    support_types = ...  # same extraction as define_complete_bridge_model
    create_all_supports(builder, plate_names, support_types)

    create_all_sections_on_plane(builder, params)   # ← NEW, replaces strips

    create_all_load_groups(builder)
    all_load_cases = create_all_load_cases(builder, params)
    create_all_loads(builder, params, all_load_cases)
    all_load_combinations = create_all_load_combinations(params, builder, all_load_cases)
    create_all_result_classes(params, builder, all_load_combinations)
```

---

### Step 6 — Top-level builder functions (app layer)

In `app/bridge/scia_model_builder.py`, add:

```python
def generate_bridge_xml_files_sections_on_plane(params: Any) -> tuple[BytesIO, BytesIO]:
    builder = ViktorSciaModelBuilder()
    define_bridge_model_sections_on_plane(builder, params)
    return builder.generate_xml_input()

def setup_bridge_analysis_sections_on_plane(
    params: Any,
    template_path: Path,
) -> tuple[Any, Any, Any]:
    xml_file, def_file = generate_bridge_xml_files_sections_on_plane(params)
    esa_template = File.from_path(template_path)
    return xml_file, def_file, esa_template

def get_scia_analysis_results_sections_on_plane(
    params: Any,
    template_path: Path,
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run analysis with sections-on-plane template and return results."""
    ...
```

---

### Step 7 — Results processing

```
src/integrations/scia_integration/results/scia_sections_on_plane_processor.py
```

- Parse SCIA output XML for the sections-on-plane result tables (table names to be
  determined from the new ESA template once provided).
- Return a `dict[str, pd.DataFrame]` keyed by section name, analogous to the
  integration-strip processor.

```
src/integrations/scia_integration/results/scia_sections_on_plane_views.py
```

- `create_sections_on_plane_table_view(results, zone_filter, ...)` → `TableResult`

---

### Step 8 — Controller views

Add a new section to `app/bridge/bridgeController/scia_integration.py`:

```python
# ====================================================
# Sections on Plane Results Table Views
# ====================================================

@TableView("Secties op vlak ULS", duration_guess=600)
def get_sections_on_plane_uls(
    self, params: BridgeParametrization, **kwargs
) -> TableResult:
    results = get_scia_analysis_results_sections_on_plane(
        params,
        SCIA_TEMPLATE_SECTIONS_ON_PLANE_PATH,
    )
    return create_sections_on_plane_table_view(results, combination_type="ULS")

@TableView("Secties op vlak SLS freq", duration_guess=600)
def get_sections_on_plane_sls_freq(
    self, params: BridgeParametrization, **kwargs
) -> TableResult:
    ...
```

Register the views in `BridgeController` (and `parametrization.py` if tabs need updating).

---

## Invariants / Design Decisions

| Decision | Rationale |
|---|---|
| X-direction sections only | Sections on plane return cross-sectional results; placing them in Y would duplicate integration-strip functionality |
| Separate ESA template | Sections on plane require different result configuration in SCIA; keeps templates independent |
| No filtering wrapper needed (initially) | The number of sections is smaller than integration strips; add a `_FilteringBuilderWrapper` equivalent only if performance requires it |
| `direction_of_cut` defaults to SDK default | `(0, 0, 1)` is the SCIA default; expose as parameter only if non-default cuts are required in future |
| Reuse `_calculate_zone_boundaries` and `_calculate_zone_x_boundaries` | Avoids duplicating zone geometry logic; import them from `scia_integration_strips.py` |

---

## File Creation Order (recommended)

1. `constants/paths.py` — add path constant  
2. `model/scia_model_interface.py` — extend Protocol  
3. `app/bridge/scia_model_builder.py` — implement concrete method + tracking dict  
4. `model/scia_sections_on_plane.py` — new module (core logic)  
5. `model/scia_model.py` — add `define_bridge_model_sections_on_plane`  
6. `app/bridge/scia_model_builder.py` — add top-level functions  
7. `results/scia_sections_on_plane_processor.py` — results parsing  
8. `results/scia_sections_on_plane_views.py` — table view helpers  
9. `bridgeController/scia_integration.py` — new TableView methods  

---

## Open Questions

- **Table names in XML output**: Confirm the result table identifiers that the new ESA
  template exposes for section-on-plane results (needed for step 7).
- **`draw` parameter**: Determine whether `Z_DIRECTION` (SDK default) is correct for
  all zones or whether it depends on the zone orientation.
- **Caching**: Decide whether the sections-on-plane analysis should share the existing
  `analysis_cache.py` mechanism or have its own cache key.
