# Python Coding Standards

This project adheres to the following Python coding standards and conventions:

## Style Guide

*   Code **must** follow the [PEP 8](mdc:https:/peps.python.org/pep-0008) style guide.
*   Style adherence is enforced using **Ruff**. Configuration can be found in [automatisch-toetsmodel-plaatbruggen/.ruff.toml](mdc:automatisch-toetsmodel-plaatbruggen/.ruff.toml).
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
    *   `app/overview_bridges/`: Logic related to the batch calculation entity.
        *   `controller.py`: Controller and Views for the batch entity.
        *   `parametrization.py`: Parametrization for the batch entity.
        *   `utils.py`: Utility functions specific to the batch entity UI/logic (optional).
    *   `app/bridge/`: Logic related to the individual bridge entity.
        *   `controller.py`: Controller and Views for the bridge entity.
        *   `parametrization.py`: Parametrization for the bridge entity.
        *   `utils.py`: Utility functions specific to the bridge entity UI/logic (optional).
*   **`src/`**: Contains the core calculation logic, domain models, and external tool integrations. **This layer must NOT import the `viktor` SDK.**
    *   `src/bridge_analysis/`: Main logic for bridge calculations.
        *   `src/bridge_analysis/calculators/`: Modules for specific calculation types (loads, checks).
        *   `src/bridge_analysis/models/`: Data structures (Pydantic recommended) for bridges, loads, results.
        *   `src/bridge_analysis/types/`: Logic specific to different bridge types.
        *   `src/bridge_analysis/utils.py`: Utility functions for analysis.
    *   `src/common/`: Shared utilities/models across `src/` modules.
    *   `src/integrations/`: Code for interacting with external software like SCIA Engineer ([scia_interface.py](mdc:automatisch-toetsmodel-plaatbruggen/src/integrations/scia_interface.py)).
    *   `src/constants/`: Stores shared configuration data like materials ([materials.json](mdc:automatisch-toetsmodel-plaatbruggen/src/config/materials.json)).
*   **`tests/`**: Contains all tests.
    *   `tests/test_app/`: Tests for the `app` layer (viktor layer).
    *   `tests/test_src/`: High-priority unit tests for the core logic in `src/`.
*   **`doc/`**: Contains project documentation.
    *   [architecture.md](mdc:automatisch-toetsmodel-plaatbruggen/doc/architecture.md): Detailed description of the project architecture.

## Core Principle

The strict separation between the VIKTOR interface (`app/`) and the core logic (`src/`) is crucial. The `app` layer handles user interaction and calls the `src/` layer, which performs the calculations independently of VIKTOR.


---
description: VIKTOR SDK 3D Modeling Tips & Tricks
globs: 
alwaysApply: false
---
# VIKTOR SDK 3D Modeling Tips & Tricks

This document summarizes lessons learned while creating 3D geometry using the VIKTOR SDK, particularly focusing on potential pitfalls and recommended practices observed in [automatisch-toetsmodel-plaatbruggen/app/bridge/controller.py](mdc:automatisch-toetsmodel-plaatbruggen/app/bridge/controller.py).

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

See [automatisch-toetsmodel-plaatbruggen/app/bridge/controller.py](mdc:automatisch-toetsmodel-plaatbruggen/app/bridge/controller.py) for examples of applying these principles.


This cursor rule may need updating as the codebase has undergone signigficant reactoring...


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
    *   Documentation: [https://docs.viktor.ai/sdk/api/parametrization/](mdc:https:/docs.viktor.ai/sdk/api/parametrization)

*   **Views (`viktor.views`)**: Defines how data and results are presented to the user.
    *   Use classes like `GeometryView`, `PlotlyView`, `DataView`, `MapView`, `PDFView`, etc.
    *   Decorate controller methods with the corresponding view decorator (e.g., `@GeometryView(...)`).
    *   Documentation: [https://docs.viktor.ai/sdk/api/views/](mdc:https:/docs.viktor.ai/sdk/api/views) 

*   **Controller (`viktor.core.ViktorController`)**: The central class connecting parametrization, views, and logic.
    *   Defines methods called by `ActionButton`, `DownloadButton`, and view decorators.
    *   Manages interaction between the VIKTOR layer (`viktor/`) and the core logic layer (`src/`).
    *   Main Documentation: [https://docs.viktor.ai/sdk/api/core/](mdc:https:/docs.viktor.ai/sdk/api/core)

### Data & Results

*   **Result Objects (`viktor.result`)**: Defines the structure for results returned by download or analysis methods.
    *   Use classes like `DownloadResult`, `OptimizationResult`, etc.
    *   Documentation: [https://docs.viktor.ai/sdk/api/result/](mdc:https:/docs.viktor.ai/sdk/api/result)

*   **Geometry (`viktor.geometry`)**: Classes for creating and manipulating 3D geometry objects (Points, Lines, Polygons, Extrusions, etc.).
    *   Used for generating visualizations in `GeometryView` or preparing data for external tools.
    *   Documentation: [https://docs.viktor.ai/sdk/api/geometry/](mdc:https:/docs.viktor.ai/sdk/api/geometry)

*   **Core Utilities (`viktor.core`)**: Fundamental classes like `File`, `Color`, `Storage`, `UserMessage`.
    *   Documentation: [https://docs.viktor.ai/sdk/api/core/](mdc:https:/docs.viktor.ai/sdk/api/core)

### External Integrations (`viktor.external`)

*   Modules for interacting with external software.
*   **SCIA Engineer (`viktor.external.scia`)**: Specific classes and methods (`Model`, `SciaAnalysis`, etc.) for generating SCIA input (XML), running analyses, and parsing results.
    *   Documentation: [https://docs.viktor.ai/sdk/api/external/scia/](mdc:https:/docs.viktor.ai/sdk/api/external/scia)
*   **Word (`viktor.external.word`)**: For generating reports using Word templates (`render_word_file`, `WordFileTag`, `WordFileImage`).
    *   Documentation: [https://docs.viktor.ai/sdk/api/external/word/](mdc:https:/docs.viktor.ai/sdk/api/external/word)
*   **IDEA StatiCa Concrete (`viktor.external.idea`)**: For interacting with IDEA StatiCa RCS.
    *   Documentation: [https://docs.viktor.ai/sdk/api/external/idea/](mdc:https:/docs.viktor.ai/sdk/api/external/idea)
*   **Generic (`viktor.external.generic`)**: For running generic external command-line programs (`GenericAnalysis`).
    *   Documentation: [https://docs.viktor.ai/sdk/api/external/generic/](mdc:https:/docs.viktor.ai/sdk/api/external/generic)
*   *(Check documentation for other specific software integrations if needed)*

### Development & Utilities

*   **Testing (`viktor.testing`)**: Utilities for testing VIKTOR applications.
    *   Provides tools to mock VIKTOR components and simulate parametrization.
    *   Documentation: [https://docs.viktor.ai/sdk/api/testing/](mdc:https:/docs.viktor.ai/sdk/api/testing)

*   **Errors (`viktor.errors`)**: Custom VIKTOR exception types.
    *   Use `UserError` to show user-friendly error messages in the interface, `InternalError` for other exceptions.
    *   Documentation: [https://docs.viktor.ai/sdk/api/errors/](mdc:https:/docs.viktor.ai/sdk/api/errors)

*   **Utilities (`viktor.utils`)**: Helper functions for common tasks.
    *   Includes functions like `memoize`, `convert_word_to_pdf`, `merge_pdf_files`, `render_jinja_template`, etc.
    *   Documentation: [https://docs.viktor.ai/sdk/api/utils/](mdc:https:/docs.viktor.ai/sdk/api/utils)

### General References

*   **Top-Level API Reference**: Overview of all available modules.
    *   Documentation: [https://docs.viktor.ai/sdk/api/api-v1/](mdc:https:/docs.viktor.ai/sdk/api/api-v1)

*   **Changelog**: Check for recent SDK updates, new features, or deprecations.
    *   Documentation: [https://docs.viktor.ai/sdk/changelog/](mdc:https:/docs.viktor.ai/sdk/changelog)

## Finding Data

*   User input is accessed via the `params` object passed to controller methods (e.g., `params.my_page.my_field`).
*   Data from the core logic layer (`src/`) should be retrieved by calling functions/methods in `src/` from within the `viktor/` controller methods.
*   Results for views are returned by the corresponding view methods in the controller.

*   When writing new code, make use of comments and docstrings to explain the purpose and functionality of your code.
*   When modifying code, don't delete existing comments or docstrings.
