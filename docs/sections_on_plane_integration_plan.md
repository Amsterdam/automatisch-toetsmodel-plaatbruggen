# Plan: Integration of "Section on 2D-member" (SectionOnPlane)

## Goal

Add `SectionOnPlane` objects to the SCIA model to retrieve calculation results at
cross-section positions. These run in **two dedicated templates** (full and governing,
mirroring the integration-strip template split) and are kept fully isolated from the
existing integration-strip code.

All logic lives in a dedicated module
`src/integrations/scia_integration/model/scia_sections_on_plane.py` — nothing is
added to `scia_integration_strips.py`.

User-facing toggles in the parametrization control whether integration strips and/or
sections on plane are included in the model build, so each feature can be switched off
independently to reduce computation time.

---

## Templates

Four ESA templates are used — one pair for integration strips, one pair for sections
on plane:

| Template file | Purpose |
|---|---|
| `resources/templates/model_governing_integrationstrips.esa` | Integration strips — governing analysis (reduced load cases) |
| `resources/templates/model_full_integrationstrips.esa` | Integration strips — full analysis (all load cases) |
| `resources/templates/model_governing_sectionsonplane.esa` | Sections on plane — governing analysis (reduced load cases) |
| `resources/templates/model_full_sectionsonplane.esa` | Sections on plane — full analysis (all load cases) |

The integration-strip templates were renamed from `model_governing.esa` /
`model_full.esa` for clarity. The sections-on-plane templates are created by the
user. All four are referenced through path constants in `constants/paths.py`.

---

## Result Object Selection (UI)

A single mutually-exclusive `OptionField` (radio buttons) in the **"Berekening selectie"** tab
(`calc_page.calc_selection`) in `app/bridge/parametrization.py` controls which type of result
objects is created. Only one type can be active at a time; the field replaces the earlier
two-toggle `BooleanField` design.

```python
# In BridgeParametrization — calc_page.calc_selection tab

calc_page.calc_selection.lb_result_objects = LineBreak()
calc_page.calc_selection.result_object_type = OptionField(
    "Type resultaatobjecten",
    options=[RESULT_OBJECT_INTEGRATION_STRIPS, RESULT_OBJECT_SECTIONS_ON_PLANE],
    default=RESULT_OBJECT_INTEGRATION_STRIPS,
    variant="radio",
    flex=80,
    description=(
        "Kies welk type resultaatobjecten in het SCIA model worden aangemaakt. "
        "Integratiestroken zijn standaard; secties op vlak zijn een alternatief."
    ),
)
```

The constants are defined in `app/constants/technical.py`:

```python
RESULT_OBJECT_INTEGRATION_STRIPS: str = "Integratiestroken"
RESULT_OBJECT_SECTIONS_ON_PLANE:   str = "Secties op vlak"
```

The model orchestration layer reads the field as:

```python
try:
    result_type = params.calc_page.calc_selection.result_object_type
except AttributeError:
    result_type = None  # graceful fallback for legacy / test params

enable_strips   = (result_type == RESULT_OBJECT_INTEGRATION_STRIPS) if result_type is not None else ENABLE_INTEGRATION_STRIPS
enable_sections = (result_type == RESULT_OBJECT_SECTIONS_ON_PLANE)  if result_type is not None else ENABLE_SECTIONS_ON_PLANE
```

A safety guard raises `ValueError` if both flags are somehow `True` simultaneously
(impossible via the OptionField but catches any programmatic misuse).

## Template Routing

`controller_utils._get_scia_template_path(params)` reads
`params.calc_page.calc_selection.result_object_type` and returns the correct governing
template:

| Selection | Template used |
|---|---|
| `"Integratiestroken"` (default) | `model_governing_integrationstrips.esa` |
| `"Secties op vlak"` | `model_governing_sectionsonplane.esa` |

All five call sitesin `scia_integration.py` pass `params` to this method.


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
| `src/integrations/scia_integration/model/scia_sections_on_plane.py` | Placement calculations and builder calls — **completely separate from** `scia_integration_strips.py` |
| `src/integrations/scia_integration/results/scia_sections_on_plane_processor.py` | Parse raw SCIA output tables for sections on plane |
| `src/integrations/scia_integration/results/scia_sections_on_plane_views.py` | Helper that formats results into VIKTOR `TableResult` |

### Modules to modify

| File | Change |
|---|---|
| `src/integrations/scia_integration/model/scia_model_interface.py` | Add `create_section_on_plane` to `SciaModelBuilder` Protocol |
| `app/bridge/scia_model_builder.py` | Implement `create_section_on_plane` in `ViktorSciaModelBuilder`; apply `_name` workaround post-creation |
| `app/constants/paths.py` | Add `SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH` and `SCIA_TEMPLATE_SECTIONS_ON_PLANE_FULL_PATH` |
| `app/constants/technical.py` | Add `RESULT_OBJECT_INTEGRATION_STRIPS`, `RESULT_OBJECT_SECTIONS_ON_PLANE`; set `ENABLE_SECTIONS_ON_PLANE = False` |
| `app/constants/__init__.py` | Export the four new constants |
| `src/integrations/scia_integration/model/scia_model.py` | Update `define_complete_bridge_model` to read `params.calc_page.calc_selection.result_object_type` (OptionField) and enable exactly one result-object type; add conflict guard |
| `app/bridge/bridgeController/controller_utils.py` | Update `_get_scia_template_path(self, params)` to route to correct governing template based on OptionField selection |
| `app/bridge/bridgeController/scia_integration.py` | Pass `params` to all 5 `_get_scia_template_path(params)` call sites |
| `app/bridge/parametrization.py` | Replace two `BooleanField` toggles with single `OptionField` (`result_object_type`, radio variant, default = `"Integratiestroken"`) |

---

## Detailed Step-by-Step

### Step 1 — Path constants

```python
# src/integrations/scia_integration/constants/paths.py

# Integration strips templates (renamed for clarity)
SCIA_TEMPLATE_PATH = SCIA_RESOURCES_PATH / "templates" / "model_governing_integrationstrips.esa"
SCIA_TEMPLATE_FULL_PATH = SCIA_RESOURCES_PATH / "templates" / "model_full_integrationstrips.esa"

# Sections on plane templates
SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH = (
    SCIA_RESOURCES_PATH / "templates" / "model_governing_sectionsonplane.esa"
)
SCIA_TEMPLATE_SECTIONS_ON_PLANE_FULL_PATH = (
    SCIA_RESOURCES_PATH / "templates" / "model_full_sectionsonplane.esa"
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

**5a — Guard integration strips with toggle in `define_complete_bridge_model`:**

```python
# src/integrations/scia_integration/model/scia_model.py

def define_complete_bridge_model(builder: SciaModelBuilder, params: Any) -> None:
    ...
    create_all_supports(builder, plate_names, support_types)

    # 4. Build Integration Strips — guarded by toggle
    if getattr(params, "enable_integration_strips", True):
        create_all_integration_strips(builder, params)

    create_all_load_groups(builder)
    ...
```

**5b — New dedicated model function for sections on plane:**

```python
from .scia_sections_on_plane import create_all_sections_on_plane

def define_bridge_model_sections_on_plane(
    builder: SciaModelBuilder,
    params: Any,
) -> None:
    """
    Build the complete SCIA model that uses sections-on-plane instead of
    integration strips.

    Uses the same geometry, supports, loads, and combinations as
    `define_complete_bridge_model`. Integration strips are never created here.
    The sections-on-plane creation is guarded by the `enable_sections_on_plane`
    toggle so the entire model build can be skipped cheaply.
    """
    _validate_first_and_last_supports(params)

    plate_names = create_bridge_geometry(builder, params)

    support_types = None
    try:
        if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
            support_types = [segment.is_support for segment in params.bridge_segments_array]
    except AttributeError:
        pass
    create_all_supports(builder, plate_names, support_types)

    # Sections on plane — guarded by toggle
    if getattr(params, "enable_sections_on_plane", True):
        create_all_sections_on_plane(builder, params)   # ← replaces integration strips

    create_all_load_groups(builder)
    all_load_cases = create_all_load_cases(builder, params)
    create_all_loads(builder, params, all_load_cases)
    all_load_combinations = create_all_load_combinations(params, builder, all_load_cases)
    create_all_result_classes(params, builder, all_load_combinations)
```

---

### Step 6 — Top-level builder functions (app layer)

Mirrors the existing integration-strip pattern: two separate entry points, one for
the **full** template (all load cases) and one for the **governing** template.

```python
# app/bridge/scia_model_builder.py

def generate_bridge_xml_files_sections_on_plane(params: Any) -> tuple[BytesIO, BytesIO]:
    """Generate XML + DEF files for the sections-on-plane model."""
    builder = ViktorSciaModelBuilder()
    define_bridge_model_sections_on_plane(builder, params)
    return builder.generate_xml_input()


def setup_bridge_analysis_sections_on_plane(
    params: Any,
    template_path: Path,
) -> tuple[Any, Any, Any]:
    """Prepare all inputs for a sections-on-plane SCIA analysis."""
    xml_file, def_file = generate_bridge_xml_files_sections_on_plane(params)
    esa_template = File.from_path(template_path)
    return xml_file, def_file, esa_template


def get_scia_analysis_results_sections_on_plane(
    params: Any,
    template_path: Path,          # pass FULL or GOVERNING path from the caller
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the sections-on-plane analysis and return results.

    Callers choose the template:
    - Full analysis  → SCIA_TEMPLATE_SECTIONS_ON_PLANE_FULL_PATH
    - Governing      → SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH
    """
    xml_file, def_file, esa_template = setup_bridge_analysis_sections_on_plane(
        params, template_path
    )
    analysis = scia.SciaAnalysis(xml_file, def_file, esa_template)
    analysis.execute(timeout=3600)
    builder = ViktorSciaModelBuilder()          # re-use extraction helper
    return builder.extract_analysis_results(analysis)
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

Add a clearly delimited new section to `app/bridge/bridgeController/scia_integration.py`.
Use the **governing** template for the primary views (fast); add a separate view or
download for full results if needed.

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
        SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH,
    )
    return create_sections_on_plane_table_view(results, combination_type="ULS")


@TableView("Secties op vlak SLS freq", duration_guess=600)
def get_sections_on_plane_sls_freq(
    self, params: BridgeParametrization, **kwargs
) -> TableResult:
    results = get_scia_analysis_results_sections_on_plane(
        params,
        SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH,
    )
    return create_sections_on_plane_table_view(results, combination_type="SLS_FREQ")
```

Register view names in the `scia = Page(...)` block in `parametrization.py`
(inside the `views=[...]` list of the SCIA Page).

### Step 9 — Parametrization toggles

Add `enable_integration_strips` and `enable_sections_on_plane` toggles to
`app/bridge/parametrization.py` as described in the **Enable / Disable Toggles**
section above.

---

## Invariants / Design Decisions

| Decision | Rationale |
|---|---|
| Separate module `scia_sections_on_plane.py` | No code added to `scia_integration_strips.py`; features are fully independent and can be tested/modified in isolation |
| Two ESA templates (full + governing) | Mirrors integration-strip template pattern; governs analysis scope without code changes |
| X-direction sections only | Sections on plane return cross-sectional results; Y-direction would duplicate integration-strip functionality |
| `enable_integration_strips` + `enable_sections_on_plane` toggles | Users can disable either feature to reduce SCIA computation time; `getattr(..., True)` default keeps backward compatibility |
| Toggles placed in "Berekening selectie" tab | Consistent with existing `load_case_selection_table` which also controls model content |
| `direction_of_cut` defaults to SDK default | `(0, 0, 1)` is the SCIA default; expose as parameter only if non-default cuts are required in future |
| Reuse `_calculate_zone_boundaries` and `_calculate_zone_x_boundaries` | Avoids duplicating zone geometry logic; import from `scia_integration_strips.py` |
| Governing template used for primary TableViews | Consistent with integration-strip view pattern; full-template analysis is available separately |

---

## File Creation Order (recommended)

1. `constants/paths.py` — add two new path constants (full + governing)
2. `model/scia_model_interface.py` — extend Protocol with `create_section_on_plane`
3. `app/bridge/scia_model_builder.py` — implement concrete method + `sections_on_plane` dict
4. `model/scia_sections_on_plane.py` — **new module** (placement logic + builder calls)
5. `model/scia_model.py` — add `define_bridge_model_sections_on_plane`; add toggle guard in `define_complete_bridge_model`
6. `app/bridge/scia_model_builder.py` — add top-level functions (full + governing template variants)
7. `results/scia_sections_on_plane_processor.py` — results parsing
8. `results/scia_sections_on_plane_views.py` — table view helpers
9. `bridgeController/scia_integration.py` — new `@TableView` methods (separate section)
10. `app/bridge/parametrization.py` — add `enable_integration_strips` and `enable_sections_on_plane` toggles + register new view names in SCIA Page

---

## Open Questions

- **Table names in XML output**: Confirm the result table identifiers that the new ESA
  templates expose for section-on-plane results (needed for step 7).
- **`draw` parameter**: Determine whether `Z_DIRECTION` (SDK default) is correct for
  all zones or whether it depends on the zone orientation.
- **Caching**: Decide whether the sections-on-plane analysis should share the existing
  `analysis_cache.py` mechanism or have its own cache key.
- **Full-template access**: Decide whether the full-template sections-on-plane analysis
  needs a dedicated `@TableView` or just a download button (analogous to the integration-strip full analysis).
