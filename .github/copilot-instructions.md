# Python Coding Standards

This project adheres to the following Python coding standards and conventions:

## Style Guide

*   Code **must** follow the PEP 8 style guide: https://peps.python.org/pep-0008/
*   Style adherence is enforced using **Ruff**. Configuration can be found in `.ruff.toml`.
*   Use **double quotes (`"`)** for strings (Ruff rule `Q000`). Single quotes are disallowed.
*   Ensure imports are sorted (Ruff rule `I001`). Ruff can automatically fix this.
*   Avoid commented-out code (Ruff rule `ERA001`). Remove it instead.

## Docstrings

*   All public modules, classes, functions, and methods **must** have docstrings.
*   Docstrings **must** follow the reStructuredText (reST) format, including parameter descriptions (`:param:`), types (`:type:`), return values (`:returns:`, `:rtype:`), and exceptions raised (`:raises:`).
*   Multi-line docstring summaries should start on the second line (Ruff rule `D213`).

## Type Hinting

*   All function and method signatures (parameters and return types) **must** include type hints.
*   Variables should have type hints where it enhances clarity.
*   Type checking is enforced using **Mypy** (although installation/configuration might be needed). Basic annotation checks are also done by Ruff (`ANN` codes).
*   Aim for clear and understandable type hints. Use modern types (e.g., `list` instead of `typing.List`).
*   Unused function/method arguments (e.g., in placeholders) should be prefixed with an underscore (`_`) to satisfy linters (Ruff rule `ARG001`/`ARG002`). Update the name and docstring when the argument is used.

## Project Structure & Imports

*   Use `__init__.py` files (even if empty) to create explicit packages. Implicit namespace packages are discouraged (Ruff rule `INP001`).
*   Unused imports (`F401`) are generally disallowed, **except** in `app/**/__init__.py` files where they are explicitly ignored via `.ruff.toml` configuration. This allows importing controllers/symbols to define the package structure or make them easily accessible.

## Import Organization

All Python files **must** structure their imports according to PEP 8 standards and the following rules:

### Import Order

Imports must be organized in the following order, with each group separated by a blank line:

1.  **Standard library imports**: Built-in Python modules (e.g., `os`, `sys`, `pathlib`, `json`).
2.  **Third-party imports**: External packages installed via pip (e.g., `viktor`, `pydantic`, `numpy`, `pandas`).
3.  **Local application imports**: Modules from the current project (e.g., `from src.data_models import...`, `from app.constants import...`).

### Import Style

*   **Absolute imports** are preferred over relative imports for clarity.
*   **Relative imports** (using `.` or `..`) may be used within a package when it improves readability, but must be consistent within that package.
*   Use `from module import SpecificClass` for specific imports rather than `import module` when only a few items are needed.
*   Avoid wildcard imports (`from module import *`) as they pollute the namespace and make it unclear what is being imported.

### Sorting Within Groups

*   Within each group, imports should be sorted alphabetically by module name.
*   `from` imports should come after direct `import` statements within the same group.
*   Multi-line imports should use parentheses for clarity:
    ```python
    from module import (
        FirstClass,
        SecondClass,
        ThirdClass,
    )
    ```

### Type Hint Imports

*   Type hint imports from `typing` or `collections.abc` should be placed in the third-party imports section.
*   Use `from __future__ import annotations` at the very top of the file (before any other imports) when using forward references or to enable postponed evaluation of annotations (PEP 563).
*   For imports only used in type hints, use `if TYPE_CHECKING:` blocks to avoid runtime overhead:
    ```python
    from typing import TYPE_CHECKING
    
    if TYPE_CHECKING:
        from module import ExpensiveClass
    ```

### Example

```python
"""Module docstring explaining the module's purpose."""
from __future__ import annotations

# Standard library imports
import json
import os
from pathlib import Path

# Third-party imports
from pydantic import BaseModel, Field
from viktor.core import ViktorController
from viktor.parametrization import NumberField, Page

# Local application imports
from app.constants.technical import DEFAULT_CONCRETE_STRENGTH
from src.data_models.bridge_models import BridgeGeometry
from src.loads.load_calculator import calculate_dead_load


class MyClass:
    """Class implementation."""
    pass
```

### Enforcement

*   Ruff automatically checks and can fix import sorting (rule `I001`).
*   Run `ruff check --fix` to automatically organize imports according to these rules.

## General

*   Comments should be clear, concise, and explain the *why* behind non-obvious code, not just *what* the code does.


---
description: 
globs: 
alwaysApply: true
---
# Project Structure Overview

This project follows a layered architecture to ensure separation of concerns, testability, and maintainability.

## Main Project Directory

The main project folder is **`automatisch-toetsmodel-plaatbruggen/`** and all work should be done within this directory.

## Key Directories

Within the `automatisch-toetsmodel-plaatbruggen/` folder:

*   **`app/`**: Contains all code related to the VIKTOR SDK interface. **No core calculation logic should reside here.** Organized by feature/entity type.
    *   `app/overview_bridges/`: Logic related to the batch calculation entity (parent entity).
        *   `controller.py`: Controller and Views for the batch entity.
        *   `parametrization.py`: Parametrization for the batch entity.
        *   `utils.py`: Utility functions specific to the batch entity UI/logic.
    *   `app/bridge/`: Logic related to the individual bridge entity (child entity).
        *   `controller.py`: Main controller entry point - imports component-based controllers.
        *   `parametrization.py`: Parametrization for the bridge entity.
        *   `analysis_cache.py`: Caching mechanism for bridge analysis results.
        *   `cache_parameters.py`: Parameters used for cache invalidation.
        *   `scia_model_builder.py`: Builds SCIA Engineer models from bridge parameters.
        *   `idea_model_builder.py`: Builds IDEA StatiCa RCS models from bridge parameters.
        *   `utils.py`: Utility functions specific to the bridge entity UI/logic.
        *   `bridgeController/`: Component-based controller modules (InfoViews, GeometryViews, SciaIntegration, IdeaIntegration, Optimization, ReportViews, ControllerUtils).
    *   `app/common/`: Shared utilities across app modules.
        *   `map_utils.py`: Utilities for map views and GIS functionality.
    *   `app/constants/`: VIKTOR layer constants.
        *   `paths.py`: File paths and resource locations.
        *   `technical.py`: Technical constants like standard rebar diameters.
        *   `ui_texts.py`: User interface text constants.
*   **`src/`**: Contains the core calculation logic, domain models, and external tool integrations. **This layer must NOT import the `viktor` SDK.**
    *   `src/data_models/`: Pydantic data models for type-safe data structures.
        *   `bridge_models.py`: Bridge geometry and configuration models.
        *   `load_models.py`: Load case and combination models.
        *   `material_models.py`: Material property models.
        *   `scia_models.py`: SCIA Engineer specific models.
        *   `idea_models.py`: IDEA StatiCa RCS specific models.
        *   `geometry_models.py`: Geometric element models.
        *   `geometry_data_models.py`: Geometric data structures.
        *   `combination_models.py`: Load combination models.
        *   `vehicle_models.py`: Vehicle load models.
        *   `plotting_models.py`: Plotting and visualization models.
    *   `src/geometry/`: Geometry creation and visualization logic.
        *   `bridge_geometry_data.py`: Bridge geometry data extraction.
        *   `cross_section.py`: Cross-section geometry.
        *   `horizontal_section.py`: Horizontal section views.
        *   `longitudinal_section.py`: Longitudinal section views.
        *   `top_view_plot.py`: Top view plotting.
        *   `load_zone_geometry.py`: Load zone geometry calculations.
        *   `load_zone_plot.py`: Load zone visualization.
        *   `model_creator.py`: 3D model creation.
    *   `src/combinations/`: Load combination logic.
        *   `load_factors.py`: Load factors and combination rules.
    *   `src/loads/`: Load calculation modules (currently being developed).
    *   `src/integrations/`: Code for interacting with external software.
        *   `scia_integration/`: SCIA Engineer integration (model generation, analysis execution, result parsing).
        *   `idea_integration/`: IDEA StatiCa RCS integration (model generation, analysis execution, result parsing).
    *   `src/common/`: Shared utilities/models across `src/` modules.
        *   `csv_parser.py`: CSV file parsing utilities.
        *   `gis_utils.py`: GIS and coordinate conversion utilities.
        *   `materials.py`: Material property utilities.
        *   `plot_utils.py`: Plotting helper functions.
        *   `constants/`: Shared constants across src modules.
    *   `src/report/`: Report generation logic.
        *   `report_functions.py`: Functions for generating PDF reports.
*   **`resources/`**: Static resources and data files.
    *   `resources/data/`: Data files and configuration.
        *   `bridges/`: Bridge-specific data files.
        *   `code_tables/`: Code tables and standards data.
        *   `materials/`: Material properties (CSV files: betonkwaliteit.csv, betonstaalkwaliteit.csv, etc.).
        *   `idea_materials/`: IDEA StatiCa material definitions.
    *   `resources/gis/`: GIS shapefiles (Bruggenkaart.shp, etc.).
    *   `resources/styles/`: CSS styles for reports.
    *   `resources/templates/`: Templates for external tools (model.esa for SCIA).
*   **`tests/`**: Contains all tests.
    *   `tests/test_app/`: Tests for the `app` layer (VIKTOR layer).
    *   `tests/test_src/`: High-priority unit tests for the core logic in `src/`.
    *   `tests/test_data/`: Test data files.
    *   `conftest.py`: Pytest configuration and fixtures.
    *   `test_utils.py`: Testing utility functions.
*   **`docs/`**: Contains project documentation.
    *   `architecture.md`: Detailed description of the project architecture.
    *   `code_style.md`: Coding standards and style guide.
    *   `development_workflow.md`: Development workflow and guidelines.
    *   `pydantic_developer_guide.md`: Guide for using Pydantic models.
    *   `testing_uitleg.md`: Testing explanation and guidelines.
*   **`scripts/`**: Development and CI/CD scripts.
    *   `quality_check_and_push.py`: Pre-push quality checks.
    *   `run_enhanced_tests.py`: Enhanced test runner.
    *   `run_mypy.py`: Type checking script.
    *   `run_ruff_check.py`: Linting script.
    *   `run_ruff_format.py`: Code formatting script.
    *   `run_viktor_tests.py`: VIKTOR-specific test runner.

## Core Principle

The strict separation between the VIKTOR interface (`app/`) and the core logic (`src/`) is crucial. The `app` layer handles user interaction and calls the `src/` layer, which performs the calculations independently of VIKTOR.


---
description: VIKTOR SDK 3D Modeling Tips & Tricks
globs: 
alwaysApply: false
---
# VIKTOR SDK 3D Modeling Tips & Tricks

This document summarizes lessons learned while creating 3D geometry using the VIKTOR SDK, particularly focusing on potential pitfalls and recommended practices observed in `app/bridge/bridgeController/controller.py`.

## Geometry Creation Issues & Recommendations

### `SquareBeam` and `RectangularExtrusion` Constructors

*   **Problem**: Both `vkt.SquareBeam` and `vkt.geometry.RectangularExtrusion` constructors caused numerous `TypeError` exceptions related to the number of arguments (e.g., `__init__() takes exactly 4 positional arguments (5 given)` or `__init__() takes at least 4 positional arguments (3 given)`). Attempts to use keyword arguments (`width=`, `depth=`, etc.) or providing `material` or `start_point` arguments often failed unpredictably.
*   **Recommendation**: For creating simple rectangular prisms (cuboids), reliably use `vkt.SquareBeam` with exactly **three positional arguments**: `vkt.SquareBeam(width, depth, height)`.
    *   `width` corresponds to the X-dimension.
    *   `depth` corresponds to the Y-dimension.
    *   `height` corresponds to the Z-dimension.
*   Avoid passing `material` or `start_point` directly to these constructors if encountering issues. Assign materials or position objects *after* creation using methods like `.material = my_material` or `.translate(my_vector)`. `RectangularExtrusion` seemed particularly problematic and might be best avoided for simple cases.

### `Polygon` Constructor

*   **Problem**: The `vkt.geometry.Polygon` constructor expects vertices as a single iterable. Passing points as separate arguments (e.g., `Polygon(p1, p2, p3, p4)`) results in `TypeError: __init__() takes exactly 2 positional arguments (5 given)`.
*   **Recommendation**: Always pass the list or tuple of `Point` objects to the `Polygon` constructor: `Polygon([p1, p2, p3, p4])`.

### `Extrusion` Class

*   **Problem**: Using the generic `vkt.geometry.Extrusion` with a `Polygon` profile also led to errors (`TypeError: 'Polygon' object is not subscriptable`, `AttributeError: 'Polygon' object has no attribute 'z'`).
*   **Recommendation**: Be cautious when using the generic `Extrusion` class. For simple shapes like cuboids, prefer specialized classes like `SquareBeam` or `CircularExtrusion`. If using `Extrusion`, ensure the profile object(s) are passed correctly (potentially within a list, e.g., `Extrusion([my_polygon], vector)`), but be aware of potential internal issues.

## Positioning and Assembly

*   **Problem**: Positioning multiple geometric elements (like a deck and pillars) separately using absolute coordinates can lead to subtle alignment issues, making objects appear disconnected.
*   **Recommendation**: For assembling multiple components:
    1.  Create all individual components centered at or relative to the origin (z=0).
    2.  Group the components together using `vkt.Group()`.
    3.  Translate the entire `Group` to its final position using a single `.translate()` operation.
    *   This ensures all relative positions are maintained correctly during the final placement.

See `app/bridge/bridgeController/controller.py` for examples of applying these principles.


This cursor rule may need updating as the codebase has undergone significant refactoring...


---
description: 
globs: 
alwaysApply: true
---
# VIKTOR SDK: DynamicArray Field Visibility Learnings

This document outlines key learnings and limitations encountered when implementing conditional visibility for fields within or dependent on `DynamicArray` components in the VIKTOR SDK, specifically concerning the `visible` callback.

## Key Takeaways & Limitations:

1.  **Accessing DynamicArray Data in Callbacks (`params` object):**
    *   When a `DynamicArray` is defined in the `ViktorParametrization` class with a `name` attribute (e.g., `input.dimensions.array = DynamicArray("Segments", name="bridge_segments_array")`), the actual array data within the `params` object (passed to `visible` callbacks or other controller methods) is often accessed directly using that `name` as an attribute of the top-level `params` object.
    *   **Example:** If `DynamicArray` is named `"bridge_segments_array"`, its data is likely at `params.bridge_segments_array`, *not* `params.input.dimensions.array` (the assignment path) within the callback.
    *   The exact access path can be subtle. It's crucial to inspect the `params` object (e.g., by printing `dir(params)` or `params` itself) within the callback to determine the correct path to the `DynamicArray`'s data.
    *   Initial assumptions about the path (e.g., following the class attribute structure like `params.input.tab_name.array_attribute_name`) may not hold true for data access via the `name` property of `DynamicArray`.

2.  **`PythonCondition` Unavailability/Issues:**
    *   Attempts to use `viktor.parametrization.PythonCondition` for conditional visibility led to `ImportError`. This suggests it might not be available in all SDK versions or has specific usage requirements not met.
    *   The alternative and successful approach was to assign direct function references to the `visible` parameter. This is often achieved by creating dedicated wrapper functions or using a factory pattern (as demonstrated in `app/bridge/parametrization.py`) to generate these callbacks, especially when adapting common logic with different parameters.

3.  **Internal VIKTOR Errors with Loop-Generated Fields:**
    *   Dynamically creating parametrization fields (e.g., `NumberField`s) within a `Tab` or `DynamicArray` using a `for` loop and `setattr` at class definition time can lead to unexpected internal VIKTOR errors (e.g., `TypeError: 'int' object has no attribute '_generate_entity_type'`).
    *   **Solution:** Explicitly define each field, even if repetitive. For a variable number of fields (like D1 to D15 widths), pre-define up to a maximum and use the `visible` callback to show only the necessary ones.

4.  **`params` Object Context in `DynamicArray` Row Callbacks:**
    *   When a `visible` callback is attached to a field *inside* a `DynamicArray` row (e.g., `my_array.my_field.visible = callback_func`), the `params` object passed to `callback_func` is typically the **top-level parametrization object**, not just the data for that specific row.
    *   This allows the callback to access other parts of the parametrization, like `params.some_other_field` or `params.name_of_dynamic_array` (as learned in point 1) to make decisions.
    *   Accessing `params.root` might be necessary if the `params` object passed is a nested `Munch` object that doesn't directly have the top-level fields, but in our case, the `name` property made the array accessible from the `params` object itself.

5.  **Debugging `visible` Callbacks:**
    *   Liberal use of `print()` statements within the callback functions (to inspect `params`, its attributes, and intermediate values) is essential for debugging why a field might not be showing/hiding as expected.
    *   Check the VIKTOR application logs carefully for these prints.

6.  **Callback Signature for `visible`**:
    *   Callback functions assigned to the `visible` parameter **must** include `**kwargs` in their signature (e.g., `def my_visibility_callback(params, **kwargs):`).
    *   The SDK requires this format even if `kwargs` are not explicitly used within the callback. Failure to include it can result in a `TypeError` regarding the expected signature.

7.  **Direct Function References for `visible` Callbacks**:
    *   Using direct references to named functions (or functions returned by a factory, as seen in `app/bridge/parametrization.py`) for `visible` callbacks is the most robust approach.
    *   While lambda functions might seem concise, they can sometimes cause issues (e.g., `AttributeError: 'functools.partial' object has no attribute '__name__'`, or similar issues with lambdas if not correctly defined).
    *   Creating multiple small, dedicated wrapper functions is a reliable strategy if a common underlying logic needs to be called with different constant parameters for different fields. Each wrapper would have the correct signature (`params, **kwargs`) and call the shared logic appropriately.

8.  **Importing SDK Components:**
    *   Always ensure that components like `Label`, `Button`, etc., are available in `viktor.parametrization` for the specific SDK version being used. If not, they might need to be imported from more specific modules (e.g., `ActionButton` from `viktor.parametrization`) or alternative components should be used (`Text` instead of `Label`). `ImportError` will indicate such issues.

9.  **Conditional Defaults in Programmatically Created Fields:**
    *   When creating fields (e.g., `NumberField`) programmatically, such as in a loop using `setattr`, the `default` parameter can be a Python expression, including conditional logic.
    *   **Example:** `default=1.0 if _idx_field <= 2 else 0.0` can be used to set different default values based on an index or other conditions during field creation.

## Example Structure for `visible` Callback (Successful Pattern):

This section now includes a more advanced example using a callback factory, suitable for managing visibility of multiple similar fields (e.g., d1_width, d2_width, etc.) within a `DynamicArray` based on other parts of the parametrization, reflecting the pattern in `app/bridge/parametrization.py`.

```python
# In your parametrization.py
from collections.abc import Callable # For type hinting the factory
from viktor.parametrization import (
    # ... other imports ...
    NumberField,
    DynamicArray,
    Page,
    Tab,
    ViktorParametrization
)

# Helper to get data from one DynamicArray (e.g., number of defined segments)
def _get_current_num_segments(params_obj) -> int: # Add type hint for params_obj if known
    try:
        dimension_array = params_obj.bridge_segments_array
        if dimension_array is None or not isinstance(dimension_array, list | tuple):
            return 0
        return len(dimension_array)
    except AttributeError:
        return 0

# Helper to get data from another DynamicArray (e.g., the one being populated)
def _get_current_num_load_zones(params_obj) -> int: # Add type hint for params_obj if known
    try:
        # Assuming 'load_zones_data_array' is the 'name' of the DynamicArray for load zones
        load_zones_array = params_obj.load_zones_data_array
        if load_zones_array is None or not isinstance(load_zones_array, list | tuple):
            return 0
        return len(load_zones_array)
    except AttributeError:
        return 0

# Factory function to create visibility callbacks for dX_width fields
def _create_dx_width_visibility_callback(required_segment_count: int) -> Callable[..., list[bool]]:
    """
    Factory function to create visibility callback functions for dX_width fields
    within a DynamicArray (e.g., 'load_zones_data_array').
    """
    def dx_width_visibility_function(params, **kwargs) -> list[bool]:  # noqa: ANN001, ARG001
        num_segments = _get_current_num_segments(params)
        num_load_zones = _get_current_num_load_zones(params)

        if num_load_zones == 0:
            return []

        visibility_list = []
        for i in range(num_load_zones):
            is_visible = (num_segments >= required_segment_count) and (i < num_load_zones - 1)
            visibility_list.append(is_visible)
        return visibility_list

    return dx_width_visibility_function

# Generate all required callbacks (e.g., for D1 to D15 width fields)
MAX_SUPPORTED_D_FIELDS = 15
DX_WIDTH_VISIBILITY_CALLBACKS = {
    i: _create_dx_width_visibility_callback(i) for i in range(1, MAX_SUPPORTED_D_FIELDS + 1)
}

class BridgeParametrization(ViktorParametrization): # Example class name, adapt as needed
    input = Page("Input Page")
    input.my_tab = Tab("My Data Tab")

    input.my_tab.dimension_defining_array = DynamicArray(
        "Bridge Segments",
        name="bridge_segments_array",
        default=[{}, {}]
    )
    # Define fields for dimension_defining_array as needed...

    input.my_tab.belastingzones = Tab("Belastingzones") # As per app/bridge/parametrization.py
    input.my_tab.belastingzones.load_zones_array = DynamicArray(
        "Belastingzones", # Label for the array
        name="load_zones_data_array" # Name used for params access
    )

    for _idx_field in range(1, MAX_SUPPORTED_D_FIELDS + 1):
        _field = NumberField(
            label=f"Width at D{_idx_field}",
            default=1.0 if _idx_field <= 2 else 0.0,
            suffix="m",
            description=f"Width for D{_idx_field}. Visible if D{_idx_field} exists and this is not the last load zone.",
            visible=DX_WIDTH_VISIBILITY_CALLBACKS[_idx_field],
        )
        # Assuming load_zones_array is on input.my_tab.belastingzones as per app/bridge/parametrization.py structure
        setattr(input.my_tab.belastingzones.load_zones_array, f"d{_idx_field}_width", _field)


# --- Simpler example for a single field's visibility using a dedicated wrapper ---
# Helper to get data from DynamicArray
def _get_relevant_array_length(params, **kwargs) -> int: # noqa: ARG001
    if not hasattr(params, "name_of_dynamic_array_from_its_name_property"):
        return 0
    the_array = params.name_of_dynamic_array_from_its_name_property
    if the_array is None or not isinstance(the_array, list):
        return 0
    return len(the_array)

# Generic visibility logic
def _show_if_array_long_enough_logic(params, *, min_length: int, **kwargs) -> bool:
    actual_length = _get_relevant_array_length(params, **kwargs)
    return actual_length >= min_length

# Dedicated wrapper functions for specific thresholds
def show_if_array_length_ge_3(params, **kwargs) -> bool:
    return _show_if_array_long_enough_logic(params, min_length=3, **kwargs)

def show_if_array_length_ge_5(params, **kwargs) -> bool:
    return _show_if_array_long_enough_logic(params, min_length=5, **kwargs)
# --- End example of dedicated wrapper functions ---

class AnotherParametrization(ViktorParametrization): # Example class name
    # ...
    my_page = Page("My Page")
    my_page.my_dynamic_array_container = Tab("DA Container")
    my_page.my_dynamic_array_container.actual_array_attr = DynamicArray(
        "My Items",
        name="name_of_dynamic_array_from_its_name_property"
    )
    # ...

    my_page.another_field_on_tab = NumberField(
        "Conditionally Visible Field",
        # ...
        visible=show_if_array_length_ge_3 # Assign the dedicated wrapper directly
    )

    my_page.another_dynamic_array = DynamicArray("Other Items")
    my_page.another_dynamic_array.conditional_field_in_row = NumberField(
        "Conditional Row Field",
        visible=show_if_array_length_ge_5 # Assign the dedicated wrapper directly
        # Here, _show_if_array_long_enough_logic (via wrapper) still gets the top-level params
        # and can access params.name_of_dynamic_array_from_its_name_property
    )

```

---
description: 
globs: 
alwaysApply: true
---
# VIKTOR SDK Usage Guidelines

This rule provides guidelines and quick references for using the VIKTOR SDK within this project.

## Core Principle

*   The VIKTOR SDK **must only** be imported and used within the `viktor/` directory and its submodules.
*   The `src/` directory **must remain** independent of the VIKTOR SDK.

## Key SDK Modules & Documentation

When working within the `viktor/` layer, refer to the official VIKTOR documentation for detailed API information:

**IMPORTANT:** Always consult the relevant documentation link below *before* implementing or modifying code that uses a specific VIKTOR SDK component to ensure correct usage and parameterization.

### User Interface & Interaction

*   **Parametrization (`viktor.parametrization`)**: Defines the user interface (input fields, pages, tabs, buttons).
    *   Use classes like `Page`, `Tab`, `TextField`, `NumberField`, `OptionField`, `ActionButton`, `DownloadButton`, `ChildEntityManager`, etc.
    *   Documentation: https://docs.viktor.ai/sdk/api/parametrization/

*   **Views (`viktor.views`)**: Defines how data and results are presented to the user.
    *   Use classes like `GeometryView`, `PlotlyView`, `DataView`, `MapView`, `PDFView`, etc.
    *   Decorate controller methods with the corresponding view decorator (e.g., `@GeometryView(...)`).
    *   Documentation: https://docs.viktor.ai/sdk/api/views/

*   **Controller (`viktor.core.ViktorController`)**: The central class connecting parametrization, views, and logic.
    *   Defines methods called by `ActionButton`, `DownloadButton`, and view decorators.
    *   Manages interaction between the VIKTOR layer (`viktor/`) and the core logic layer (`src/`).
    *   Main Documentation: https://docs.viktor.ai/sdk/api/core/

### Data & Results

*   **Result Objects (`viktor.result`)**: Defines the structure for results returned by download or analysis methods.
    *   Use classes like `DownloadResult`, `OptimizationResult`, etc.
    *   Documentation: https://docs.viktor.ai/sdk/api/result/

*   **Geometry (`viktor.geometry`)**: Classes for creating and manipulating 3D geometry objects (Points, Lines, Polygons, Extrusions, etc.).
    *   Used for generating visualizations in `GeometryView` or preparing data for external tools.
    *   Documentation: https://docs.viktor.ai/sdk/api/geometry/

*   **Core Utilities (`viktor.core`)**: Fundamental classes like `File`, `Color`, `Storage`, `UserMessage`.
    *   Documentation: https://docs.viktor.ai/sdk/api/core/

### External Integrations (`viktor.external`)

*   Modules for interacting with external software.
*   **SCIA Engineer (`viktor.external.scia`)**: Specific classes and methods (`Model`, `SciaAnalysis`, etc.) for generating SCIA input (XML), running analyses, and parsing results.
    *   Documentation: https://docs.viktor.ai/sdk/api/external/scia/
*   **Word (`viktor.external.word`)**: For generating reports using Word templates (`render_word_file`, `WordFileTag`, `WordFileImage`).
    *   Documentation: https://docs.viktor.ai/sdk/api/external/word/
*   **IDEA StatiCa Concrete (`viktor.external.idea`)**: For interacting with IDEA StatiCa RCS.
    *   Documentation: https://docs.viktor.ai/sdk/api/external/idea/
*   **Generic (`viktor.external.generic`)**: For running generic external command-line programs (`GenericAnalysis`).
    *   Documentation: https://docs.viktor.ai/sdk/api/external/generic/
*   *(Check documentation for other specific software integrations if needed)*

### Development & Utilities

*   **Testing (`viktor.testing`)**: Utilities for testing VIKTOR applications.
    *   Provides tools to mock VIKTOR components and simulate parametrization.
    *   Documentation: https://docs.viktor.ai/sdk/api/testing/

*   **Errors (`viktor.errors`)**: Custom VIKTOR exception types.
    *   Use `UserError` to show user-friendly error messages in the interface, `InternalError` for other exceptions.
    *   Documentation: https://docs.viktor.ai/sdk/api/errors/

*   **Utilities (`viktor.utils`)**: Helper functions for common tasks.
    *   Includes functions like `memoize`, `convert_word_to_pdf`, `merge_pdf_files`, `render_jinja_template`, etc.
    *   Documentation: https://docs.viktor.ai/sdk/api/utils/

### General References

*   **Top-Level API Reference**: Overview of all available modules.
    *   Documentation: https://docs.viktor.ai/sdk/api/api-v1/

*   **Changelog**: Check for recent SDK updates, new features, or deprecations.
    *   Documentation: https://docs.viktor.ai/sdk/changelog/

## Finding Data

*   User input is accessed via the `params` object passed to controller methods (e.g., `params.my_page.my_field`).
*   Data from the core logic layer (`src/`) should be retrieved by calling functions/methods in `src/` from within the `viktor/` controller methods.
*   Results for views are returned by the corresponding view methods in the controller.

## Parametrization Field Access Patterns

**CRITICAL**: When a parametrization field has a `name` attribute, the field data is accessible differently than the attribute path where it's defined.

### Field Access Rules

*   **Fields WITH `name` attribute**: Access directly on `params` using the `name` value
    ```python
    # Parametrization definition
    info.concrete_strength_class = OptionField("Label", name="concrete_strength_class", ...)
    
    # ✅ Correct access in controller/cache
    value = params.concrete_strength_class
    
    # ❌ Incorrect access (will not work)
    value = params.info.concrete_strength_class
    ```

*   **Fields WITHOUT `name` attribute**: Access via the attribute path
    ```python
    # Parametrization definition  
    info.bridge_objectnumm = TextField("Label", ...)
    
    # ✅ Correct access
    value = params.info.bridge_objectnumm
    ```

### Examples from Codebase

*   `bridge_segments_array` (has `name="bridge_segments_array"`) → Access as `params.bridge_segments_array`
*   `concrete_strength_class` (has `name="concrete_strength_class"`) → Access as `params.concrete_strength_class`
*   `bridge_objectnumm` (no `name` attribute) → Access as `params.info.bridge_objectnumm`

### Debugging Field Access

*   Use `print(dir(params))` to see available attributes on the `params` object
*   Use `hasattr(params, "field_name")` to check if a field with `name` attribute exists
*   When in doubt, print the `params` object structure to understand the access pattern

## Callback Function Signatures

**CRITICAL**: All callback functions used in VIKTOR parametrization fields **must** include `**kwargs` in their signature.

*   **Required signature**: `func(..., **kwargs)` or `func(params, **kwargs)` for parametrization callbacks
*   **Example**: Functions used in `OptionField.options`, `visible` callbacks, `Lookup` functions, etc.

```python
# ✅ Correct - includes **kwargs
def _get_rebar_diameter_options(**kwargs) -> list[int]:  # noqa: ARG001
    return sorted(STANDARD_REBAR_DIAMETERS)

# ✅ Correct - includes params and **kwargs
def _show_field_callback(params, **kwargs) -> bool:  # noqa: ANN001, ARG001
    return params.some_condition

# ❌ Incorrect - missing **kwargs (will cause TypeError)
def _get_options() -> list[int]:
    return sorted(STANDARD_REBAR_DIAMETERS)
```

*   Add `# noqa: ARG001` to suppress unused argument warnings from linters
*   This is a VIKTOR SDK requirement, even if `**kwargs` is not used in the function body

## General Guidelines

*   When writing new code, make use of comments and docstrings to explain the purpose and functionality of your code.
*   When modifying code, don't delete existing comments or docstrings.
