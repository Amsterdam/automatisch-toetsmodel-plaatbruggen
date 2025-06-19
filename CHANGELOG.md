## [`v0.0.6`] - 2025-xx-xx

### Added

#### User-Facing
- Horizontal spawn arrow to the topview
- Pavement properties for load zones:
  - Added thickness field for pavement/surfacing per load zone (default 5cm)
  - Added material selection field with options: Asfalt, Beton, Klinkers, Grind, Tegels
  - Added explanatory text about eigengewicht calculation (thickness * material density → kN/m2)

#### Developer-Facing
- Comprehensive Phase 2 VIKTOR view testing infrastructure:
  - Full view execution tests for all `BridgeController` and `OverviewBridgesController` views
  - Advanced VIKTOR result object handling (`DataResult`, `PlotlyResult`, `MapResult`, `GeometryResult`, `PDFResult`)
  - Decorator bypassing for authentic view method testing
  - 15 new test methods covering all controller views with realistic parameter data
- Dutch testing documentation (`docs/testing_uitleg.md`) with workflows, AI assistance guidance, and seed file maintenance procedures
- Pavement material constants and infrastructure:
  - Added `PAVEMENT_MATERIAL_OPTIONS` constant with material types
  - Added `LOAD_ZONES_INFO_TEXT` constant for centralized text management
  - TODO comments for Eurocode 1 material density implementation and CSV loading
- Load zone geometric calculation system:
  - Added `_calculate_zone_geometry_properties` method following dimensions pattern
  - Proper zone stacking logic from bridge top to bottom
  - Integration with existing `prepare_load_zone_geometry_data` function
- Test data seed files updated with pavement parameters for comprehensive testing coverage

### Changed

#### User-Facing
- Split concrete cover input into separate fields for top and bottom cover
- Split shear reinforcement input into separate fields for top and bottom
- Reinforcement input reworked to apply configurations to multiple zones, with updated explanatory text

#### Developer-Facing
- Enhanced development workflow with improved pre-commit hooks:
  - Auto-commit formatting changes
  - Better error reporting and guidance
  - Consistent tooling for `ruff`, `mypy`, and tests

### Fixed

#### User-Facing
- Load zones view functionality restored after missing geometric calculations were implemented

#### Developer-Facing
- Load zones IndexError resolved by implementing proper geometric property calculations
- Unicode character issues in constants (replaced × with * and ² with 2 for ASCII compatibility)
- Ruff configuration updated to ignore TODO comments (FIX002) as they will be addressed in separate issues
- LoadZoneDataRow TypedDict updated to include pavement parameters and calculated geometric fields


## [`v0.0.5`] - 2025-05-22

### Added
#### User-Facing
- Enhanced reinforcement visualization in all three bridge zones:
  - Added support for shear reinforcement bars in all zones
  - Proper handling of both reinforcement configurations (longitudinal/shear inside/outside)
  - Extension of reinforcement system to dynamically added zones
  - Correct positioning of reinforcement in additional segments based on cumulative distances
  - Accurate height calculations for shear reinforcement in the middle zone (bz2)
- Added "Info" page to the `Bridge` entity, displaying a map view of the specific bridge.
- Implemented parametrization for "Belastingzones" (Load Zones) within the `Bridge` entity:
    - Added a "Belastingzones" tab to the "Invoer" page.
    - Introduced a `DynamicArray` (`load_zones_array`) for defining multiple load zones, each with a selectable `zone_type` (e.g., "Voetgangers", "Fietsers", "Auto").
    - Added `NumberField`s (`d1_width` to `d15_width`) for specifying zone widths at each bridge cross-section (D-point), with dynamic visibility for D3-D15 based on defined bridge segments.
    - Configured a default of two load zones upon entity creation.
- Developed a new "Belastingzones" `PlotlyView` in `BridgeController` to visualize load zones:
    - Displays a 2D top-down view of the bridge outline.
    - Draws lines representing the boundaries of each load zone, stacked downwards.
    - The final load zone extends to the bottom of the bridge's structural area.
    - Annotates each zone with its type at the right end of the plot.
    - Adds "D1", "D2", etc., labels at the top, aligned with bridge cross-sections.
- Enhanced "Belastingzones" (Load Zones) functionality:
    - Introduced a new "Berm" load zone type with a distinct visual style (yellow, cross-hatch).
    - Updated the default load zone configuration to include a "Berm" zone.
    - Implemented validation for load zone widths:
        - Ensures total zone width does not exceed available bridge width at each D-point.
        - Displays clear warning annotations on "Bovenaanzicht" and "Belastingzones" views if discrepancies are found.
        - Highlights individual load zones in red on the "Belastingzones" view if they geometrically exceed bridge boundaries.
- Dynamic zone numbering system in reinforcement tab:
    - Automatic zone number generation based on bridge segments
    - Format "location-segment" (e.g., "1-1", "2-1", "3-1", "1-2", etc.)
    - First number indicates location (1=left, 2=middle, 3=right)
    - Second number indicates segment number
- New OptionField for zone selection in reinforcement input:
  - Options dynamically generated based on number of bridge segments
  - Options list updates automatically when segments are added/removed
  - Proper zone labeling helps users identify reinforcement locations

#### Developer-Facing
- Added `wapening_buigstraal.csv` containing minimum bending radii specifications for different reinforcement bar diameters (6mm to 40mm) according to Eurocode 2.

### Changed
#### User-Facing
- Renamed map view from "Kaart Huidige Brug" to "Locatie Brug" in bridge entity
- Updated bridge deck parametrization for zone 2 thickness:
  - Replaced "Extra dikte zone 2" (`dze`) with "Dikte zone 2 (`dz_2`)" to directly input total thickness.
  - Updated `model_creator.py` to use the new `dz_2` parameter for 3D model generation.

#### Developer-Facing
- Refactored reinforcement creation code in `model_creator.py`:
  - Split into modular, single-responsibility functions
  - Added helper functions for zone parameter extraction
  - Added zone dimension calculation functions
  - Improved reinforcement positioning calculations
  - Enhanced readability and maintainability of the code
- Added support for the `langswapening_buiten` radio button:
  - Dynamic switching between reinforcement configurations
  - Proper spacing calculations between rebar layers
  - Correct positioning of longitudinal and shear reinforcement based on configuration
- Reorganized resources directory structure for better organization:
  - Created subdirectories for different resource types: `data/materials`, `data/bridges`, `gis`, `templates`, `styles`, `images`, and `symbols`
  - Moved material CSV files to `resources/data/materials/`
  - Moved bridge data files to `resources/data/bridges/`
  - Moved GIS files to `resources/gis/`
  - Moved document templates to `resources/templates/`
  - Moved style files to `resources/styles/`
- Refactored map and geometry processing logic from `BridgeController` and `OverviewBridgesController` into a new shared utility module: `app/common/map_utils.py`.
- Updated `BridgeController` and `OverviewBridgesController` to utilize the new shared map utilities.
- Modified `BridgeController`'s `get_bridge_map_view` method to fetch `last_saved_params` using `viktor.api_v1` for improved robustness in retrieving entity parameters.
- Performed internal refactoring of `BridgeController`'s `get_bridge_map_view` and related helper methods to enhance structure and address linter warnings.
- Simplified shapefile path retrieval in `BridgeController` by inlining the `_get_shapefile_path` helper method into `get_bridge_map_view`.
- Centralized individual bridge shapefile loading and filtering by moving logic from `BridgeController`._load_and_filter_geodataframe` to a new `load_and_filter_bridge_shapefile` function in `app/common/map_utils.py`.

### Fixed
#### User-Facing
- Resolved issues where `OBJECTNUMM` was not found in `Bridge` entity parameters by:
    - Moving hidden `TextField` parameters (`bridge_objectnumm`, `bridge_name`) into the newly created "Info" page.
    - Updating parameter access in `BridgeController` to `params.info.bridge_objectnumm`.
- Addressed `AttributeError: info` for older `Bridge` entities by:
    - Making parameter access in `BridgeController` more robust using `params.get("info")`.
    - Updating `OverviewBridgesController` (`_create_missing_children` method) to correctly structure parameters under an "info" key when creating new bridge entities.

#### Developer-Facing
- 

## [`v0.0.4`] - 2025-05-08

### Added
- Added `betonkwaliteit.csv` containing concrete quality specifications with strength parameters
- Added `betonstaalkwaliteit.csv` containing reinforcement steel quality specifications with yield and design strengths
- Added `voorspanstaalkwaliteit.csv` containing prestressing steel quality specifications with strength and allowable stress parameters
- Added an explanatory text field for the bridge segments in the parametrization.

### Changed
- Set default of two items for the bridge segments dynamic array.
- Enhanced the 2D top view (`create_2d_top_view` in `src/geometry/model_creator.py`) to include:
    - Clear visual separation of bridge zones (1, 2, and 3) for each segment.
    - Background coloring for each zone to improve visual distinction.
    - Detailed dimension labels for segment lengths (`l`) and zone widths (`bz1`, `bz2`, `bz3`) at each cross-section.
    - Identifier labels (e.g., "D1", "D2") for each cross-section.
    - Zone numbering within each segment (e.g., "1-1", "2-1", "3-1").

### Fixed
- Corrected visibility logic for "Afstand tot vorige snede" field in the bridge dimensions dynamic array, ensuring it is hidden for the first segment.
- Suppressed a `DeprecationWarning` from `geopandas._compat` related to `shapely.geos` to keep console output clean. This is an internal `geopandas` issue and does not affect functionality.

## [`v0.0.3`] - 2025-05-08

### Added
- Viktor CI/CD pipeline
- Home page with documentation view
- More detailed README content including Usage, Technologies, and Contribution guidelines.
- Link to live VIKTOR application in README.
- Hover effect on changelog version sections.
- Set `OverviewBridges` entity as the default start page for the application.
- Implemented 3D visualization of bridge geometry based on parametrized dimensions.
- Added dynamic 2D views: top view, longitudinal section, and cross-section, derived from the 3D model.
- Introduced detailed parametrization for bridge entities, including:
    - Multi-section bridge dimensions using a dynamic array.
    - Reinforcement geometry parameters.
    - Load zone definitions and intensities.
    - Load combination factors.
    - Controls for section view locations.
- Added placeholder pages for SCIA integration, Calculation, and Reporting within the bridge entity.

### Fixed
- Initial configuration issues
- Pre-commit configuration to correctly install `types-Markdown` and `types-shapely` for `mypy` hook.
- Corrected developer installation instructions in README.
- Corrected contact email format in README.
- `ARG002` VIKTOR view signature conflict with Ruff.

### Changed
- Updated documentation structure
- Improved styling for README and Changelog view (layout, spacing, typography, colors).
- Restructured README for better user/developer audience separation.
- Clarified contribution workflow distinction (internal vs. external).

## [`v0.0.2`] - 2025-05-01

### Added
- Initial release
- Basic bridge data visualization
- Integration with map services

### Fixed
- Development environment setup

### Changed
- Initial project structure

## [`v0.0.1`] - 2025-05-01