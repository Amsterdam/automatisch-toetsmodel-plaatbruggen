## ['v0.0.24'] - 2026-02-xx

### Fixed
- Typo on the "Berekening optimalisatie" page: 'gecahched' to 'gecached'

## [`v0.0.23`] - 2026-01-19

### Changed
- **Cache Size Limit Increased to 250MB**: Increased total cache size limit from 50MB to 250MB across all caching logic
  - Updated `max_cache_size_mb` in `cache_analysis_results()` from 50MB to 250MB
  - Updated smart ESA filtering logic to use 250MB threshold for total cache size
  - Updated all related comments and documentation to reflect 250MB limit
  - Allows caching of larger analysis results for better performance
  - ESA models still excluded intelligently if they would push total cache over 250MB

## [`v0.0.22`] - 2026-01-19

### Fixed
- **Request-Level Cache in Online Environment**: Fixed critical caching issue where SCIA analysis results were not being reused across different views in VIKTOR's online platform
  - Changed `request_cache` from instance variable to class-level variable in `AnalysisCache`
  - Ensures in-memory cache is shared across all `AnalysisCache` instances within the same worker process
  - Views like "Integratiestroken Enveloppen" now correctly reuse cached SCIA results instead of recalculating
  - This fix enables proper two-level caching: fast in-memory access + persistent VIKTOR Storage

### Changed
- **Smart ESA Model Caching**: Implemented intelligent ESA caching based on total cache size
  - ESA models > 250MB are never cached
  - ESA models < 250MB are cached only if total cache stays under 250MB limit
  - If including ESA would exceed 250MB, ESA is excluded but other results remain cached
  - ESA files regenerated on-demand when excluded (quick operation)
  - Maximizes cache efficiency while respecting Storage limits
  - Added diagnostic progress messages to identify cache status
  
### Fixed (continued)
- **Code Quality**: Fixed Ruff linting errors
  - Added `ClassVar` annotation for mutable class attributes (RUF012)
  - Renamed `_request_cache` to public `request_cache` to avoid private member access warning (SLF001)

## [`v0.0.21`] - 2026-01-12

### Fixed
- **SCIA Cache Reuse for Integration Strip Views**: Fixed issue where SCIA calculation would restart when viewing integration strip envelopes after downloading IDEA model

- **IDEA Force Mapping for Y-Direction Strips**: Corrected force mapping from SCIA to IDEA for Y-direction (langs/longitudinal) integration strips
  - Fixed shear force mapping: Changed from V_y → Qz to V_z → Qz for Y-direction strips
  - Bending moment mapping remains M_y → My for Y-direction strips
  - X-direction (dwars/transverse) strips already correctly mapped V_z → Qz and M_x → My

## [`v0.0.20`] - 2025-12-11

### Added
- **Integration Strips Implementation**: Complete implementation of SCIA integration strips to replace cross-section (section on plane) approach
  - Added integration strip creation in SCIA model (regular and support strips in x and y directions)
  - Implemented strip results extraction and processing from SCIA XML output
  - Support for 8 strip table types: ULS/SLSfreq × x/y directions × regular/support strips
  - Strip results include internal 1D forces (N, Vy, Vz, Mx, My, Mz) at positions along strips
  - Added strip result views with unit conversion and width normalization
  - Integration strips data passed to IDEA interface with dummy coupling
  - Updated SCIA ESA template to support integration strips
  - Added comprehensive test suite for strip unit conversion and processing

### Changed
- **Cross-Section Approach Removed**: Cleaned up deprecated cross-section (CS) related code and UI components
  - Removed CS-specific UI elements and views
  - Integration strips now serve as primary method for internal force extraction
- **SCIA Results Caching**: Enhanced caching system to store integration strip results
  - Strip results cached alongside other SCIA analysis data
  - Improved performance for repeated strip result access

### Fixed
- **Integration Strip Unit Conversion**: Fixed unit and width normalization for strip results
  - Corrected force and moment unit conversions (kN, kNm)
  - Fixed width correction factors for normalized force values

## [`v0.0.19`] - 2025-12-05

### Fixed
- **SCIA CS ULS/SLS View Empty Data Issue**: Fixed missing data in SCIA Cross Section (CS) ULS and SLS freq visualization views
  - Root cause: CS tables use different data structure (`p0` key) compared to regular 2D force tables (nested Dutch headers)
  - Updated `find_2d_force_tables_cs()` to use correct data key `"p0"` instead of Dutch header keys
  - Added CS dataframes (`df_cs_uls`, `df_cs_sls_freq`, `df_cs_envelope`) to cache storage for improved performance
  - Enhanced `process_scia_cs_results()` and `extract_cs_force_envelopes()` to use cached dataframes when available
  - All CS views (ULS, SLS freq, Analyse Resultaten, CS visualisatie) now handle old cache gracefully with informative messages
  - CS views properly display force, moment, and normal force data for all cross sections

- **Statusoverzicht Cache Status Display**: Fixed bridges showing "Klaar voor berekening" instead of "Berekening actueel" after successful batch calculation
  - Status determination now checks both entity cache AND batch results storage
  - Bridges in batch_results are correctly marked as cached regardless of cache file validation
  - "Ververs Statusoverzicht" button now correctly displays updated status for all calculated bridges

- **Batch Calculation Robustness**: Fixed batch calculations stopping prematurely after first bridge
  - Removed unreliable file-based cancellation check that caused false positive exits
  - Fixed progress counter to correctly display bridge numbers (e.g., "1/3", "2/3", "3/3")
  - Batch calculation now processes all bridges without interruption
  - Users can still cancel via VIKTOR UI which terminates the entire job naturally

### Changed
- **Request-Level Cache Optimization**: Added in-memory request-level cache to prevent redundant storage lookups when multiple views load the same SCIA/IDEA results
  - Three-tier caching strategy: entity storage (persistent) → request cache (in-memory) → hash memoization
  - First view loads from storage and caches results in memory for current request
  - Subsequent views in same request reuse in-memory cache (instant access, no storage reads)
  - Dramatically improves performance when switching between SCIA views (CS ULS, CS visualisatie, Analyse Resultaten)
  - Visualization parameter changes no longer trigger storage lookups or recalculations
  - 10-20x faster view switching, 100-300x faster overall for cached calculations

- **Code Quality**: Removed debug print statements from batch calculation component
  - Cleaner logging output without development debug messages
  - Production-ready error handling without verbose console output

## [`v0.0.18`] - 2025-12-01
### Added
  **Shared Cache parameters**: added spreiding to the shared cache parameters.
  **SCIA CS Results Data Source Tracking**: Added "Bron" column to CS result tables (ULS, SLS freq, envelope) to indicate whether values are from SCIA match ("SCIA") or calculated ("Afgeleid") when no match exists between basis and elementaire tables.

### Changed
- **SCIA XML Download verbeterd**: XML download bevat nu ook ESA template bestand voor handmatige import.
  - Gebruikers kunnen XML + DEF + ESA template downloaden als ZIP.
  - Deze bestanden kunnen handmatig geïmporteerd worden in SCIA Engineer zonder berekening.
  - Sneller dan volledige berekening voor situaties waarin handmatige aanpassingen nodig zijn.
  - Note: ESA zonder berekening downloaden is niet mogelijk via VIKTOR API (vereist execute()).
  - Changed how the dimensions are inputed.
- **SCIA CS Missing Value Calculation**: Implemented SCIA elementary design magnitude formulas to calculate missing design moments and normal forces when basis and elementaire tables don't have matching rows. Uses proper engineering relationships: mxd_plus/minus, myd_plus/minus, nxd, nyd formulas from `scia_elem_des_mag.py`.
  - Added tram loading to the load selection table.
- **Load combinations**: Changed the system with which load combinations are generated.
  - Updated the load combination table with new columns to differentiate between the tandem system and udl notional lanes and rest parts.
  - Changed the implementation of load value calculation factors alpha trend, psi_NEN, alpha_Q and
  implented a lane factors to differentiate between governing notional lanes.
  - Moved calculation of these factors to seperate helper functions.
  - Implemented these helper functions into the load combination table, which now represent combined load factors.
  - Changed the load value of the tandem systems in the SCIA model to a default of 100 kN.
  - Changed the load value of the UDL loads in the SCIA model to a default value of 2.5 kN per square meter.
- **Mesh to 0.2**: changed the mesh of 2d members from 1.0 to 0.2 m.

### Fixed
- **Tram Load Fix**: Fixed tram load case creation when no tram zones are modeled - now correctly skips tram loads when load zones are empty or contain no tram zones.
- **Result classes**: Fixed assignment of load combinations to result classes. There was an error in index handling.
- **Issue with dimension table thickness**: Fixed an issue with the thickness not applying to all dimension rows.
- **SCIA CS NaN Values**: Fixed JSON serialization errors caused by NaN values in CS results. When outer merge creates NaN for unmatched rows, missing values are now calculated using SCIA formulas instead of causing serialization failures.
- **Load polygon dispersal**: Fixed proper load polygon dispersal for load polygons around bridge deck edges.
  - Service vehicle and accidental vehicle loads are now positioned correctly along the edge of the bridge deck.
  - Adapted the existing function `clip_polygon_to_bridge_boundaries()` to `move_polygon_to_bridge_boundaries()`, to comply with new functionality of this helper function.


## [`v0.0.17`] - 2025-11-13
### Added
- Temperature loads on 2D elements
- **UDL load system**: Added "schaakbordpatroon" for UDL in BG4000 series.
Introduced a new naming system with span, lane and configuration identification.
- Load combinations with group 5 that include the tram loading.
- **Separated VIKTOR and GitHub Documentation**: Created `VIKTOR_README.md` with simplified user-facing content for VIKTOR platform.
  - VIKTOR shows only essential information: description, usage, and contact.
  - README.md retains full documentation including developer setup for GitHub.
  - Both files maintained separately for clarity.
- **SCIA CS Visualization**: New interactive PlotlyView for visualizing SCIA Cross Section (CS) analysis results.
- **Caching System Documentation**: Added comprehensive documentation in `.github/Rules/caching_system.md` explaining cache architecture and usage.
- **Dataframe Caching**: SCIA CS dataframes (ULS, SLS freq, envelope) now cached for improved performance across views.

### Changed
- Fixed surface loads with zero area which caused model singularities in SCIA.
- Changed the load case naming system for the UDL series, according to the new load polygon positioning system.
- Changed the load case naming system for the tandem loads. Now every tandem load has its own load case and better identifier.
- Re-assigned the UDL and tandem loads to load groups.
- Fixed and improved the load combination system, with a better naming system around configuration names.
New folder in the directory for the load combination generator.
- **IDEA Rebar Spacing Calculation**: Modified rebar positioning algorithm to use exact requested heart-to-heart spacing instead of recalculating based on integer rebar count
  - Changed from `n_rebars = int(width / hoh)` to `n_rebars = width / hoh` (no integer conversion)
  - Uses exact requested spacing value (e.g., 150mm input → 150mm IDEA spacing)
  - Rounds to nearest integer only for determining even/odd layout pattern
- Extended the load combination table with a column for the tram loading under "Bijzondere voertuigen".
- **IDEA RCS uitleg en tabbladen**: Verbeterde en verduidelijkte uitleg van het SCIA → IDEA proces, met nadruk op:
  - Heldere beschrijving van de 6 processtappen, inclusief uitlezen van dwarskrachten en het belang van 2 extremen per unieke zone
  - Toelichting dat tabblad 1 de unieke plaatelementen toont per combinatie van plaatdikte en wapeningsconfiguratie
  - Nieuwe kolommen met verduidelijking toegevoegd aan IDEA resultaat tabellen. 
- **SCIA Results Parser Optimization**: Major performance improvements to `extract_analysis_results` in `scia_model_builder.py`:
  - Reduced XML file reads from 6 to 1 (60-80% performance improvement)
  - Added dataframe caching for CS results (ULS, SLS freq, envelope)
- **Cache Performance Optimization**: Optimized cache checking with hash memoization (10-50x faster on repeated checks)
- **SCIA Views Performance**: All SCIA CS views now use cached dataframes instead of reprocessing XML data
- **SCIA UI text**: updated the UI text.
- **UI text invoer dimensies**: changed UI tekst by renaming code variable names like bz, bz2 and dz etc.

### Fixed
- **IDEA Integration**: Fixed SCIA to IDEA data flow to properly use cached envelope dataframes with correct column naming (_max suffix)
- **SCIA Table Sorting**: Fixed force/moment columns (Vx, Vy, MxD+, MxD-, MyD+, MyD-, NxD, NyD) to use numeric values instead of strings with units, enabling proper sorting in SCIA CS ULS, SCIA CS SLS freq, and SCIA Analyse Resultaten tables

### Removed
- **SCIA Results Cleanup**: Removed 3 unused functions from `scia_results_processor.py` (~75 lines):
  - `get_name_for_coords()` - Legacy coordinate name lookup (no usages)
  - `get_max_abs_for_column()` - Legacy max absolute value finder (no usages)
  - `find_all_2d_cs_force_tables()` - Replaced by `_process_cs_selected_result_tables()` (no usages)
  - See `.github/Rules/scia_results_cleanup_analysis.md` for detailed analysis

## [`v0.0.16`] - 2025-10-30
### Added
- Added dynamic load factor for tram load
- Tram loads VIKTOR input and modelling of the loads in SCIA
- **Optimisation button**: Optimisation option to automatically calculate different calculation levels till passing UC checks are found.
- **SCIA to IDEA Cross-Section Load Integration**: Refactored cross-section load transfer from SCIA to IDEA StatiCa
  - Uses filtered CS envelope data combining ULS and SLS freq results (SLS kar removed)
  - Supports normal forces (n_xD, n_yD) in addition to shear and moment forces
  - Creates two IDEA extremes per (zone, max_for_column) combination - one for each direction (langs/dwars)
  - Each extreme combines fundamental (ULS) and frequent (SLS freq) load values
  - Removed deprecated node and integration strip processing functions
  - Streamlined data flow: SCIA envelope → processed DataFrame → IDEA extremes
- **Bridge Database Management System**: Complete workflow for managing bridge inventory data
  - New "Brug Database Management" page in OverviewBridges entity for centralized data management
  - CSV and Excel file upload functionality to update bridge database (`filtered_bridges.json`)
  - Download current bridge data as CSV template for easy editing
  - Automatic creation of new bridge entities and updating of existing entities from uploaded data
  - Robust file parsing with multi-tier encoding detection (UTF-8, Latin-1, with BOM support)
  - Automatic handling of empty rows and whitespace in column headers
  - Clear step-by-step instructions with requirements and workflow guidance
  - Excel-compatible CSV export with UTF-8 BOM for proper character display
  - Comprehensive test suite for CSV/Excel parsing with 18 test cases covering various scenarios
  - User-friendly success/error messages with detailed feedback on created/updated bridge counts
- **Manual Support Selection**: Users can now manually select support types for each D-point location instead of automatic first/last positioning.
  - Support options: "Nee" (no support), "Verende oplegging (x,y)" (roller), "Inklemming" (fixed), "Scharnieroplegging" (pinned)
  - Supports visualization and SCIA integration for all support types
  - Support annotations in bridge top view update based on user selections
  - Distinct Unicode symbols for each support type: ⧋ (roller), ▲ (fixed), ⧊ (pinned)
- **Automatic Bridge Type Classification**: Added real-time bridge type determination based on support configuration.
  - Displays "Statisch bepaald" for exactly 2 supports (Scharnieroplegging + Roloplegging) at begin/end positions
  - Displays "Statisch onbepaald" for all other support configurations
  - Live updates as user modifies support selections
- **Support Configuration Validation**: Added visual feedback and validation for first/last section support requirements
  - Real-time output field with colored status indicators (🟢 valid / 🔴 invalid)
  - Automatic validation when running SCIA analysis with clear error messages
  - Ensures bridge model has required supports before analysis execution
- **Management summary**: Added basic param values and unity check values to the management summary.
- **2D sections on 2d members**: Added 2D sections in SCIA and the link with with IDEA 
- **Dual road zone support**: Added functionality to add two seperate road zones on the bridge instead of one single zone in the middle, for the real road layout. Adapted the lane generation and load generation functions for the UDL and Tandem system loads.
- **SCIA section plane handling**: Enhanced section plane creation for multi-segment spans and zone boundaries
  - Sections respect intermediate segment boundaries with 1mm offset
  - Sections avoid crossing zone boundaries (bz1/bz2/bz3)
  - Special section coverage for narrow middle zones (bz2 ≤ 1.002m)
  - Comprehensive documentation in `docs/scia_section_on_plane_logic.md`

### Changed
- **SCIA material selection**: SCIA model now uses `params.concrete_strength_class` with fallback to `DEFAULT_CONCRETE_STRENGTH_CLASS` (C30/37).
- **Dynamic Material Loading**: Replaced all hardcoded material lists with dynamic CSV file reading
  - Material lists now loaded at runtime from `Concrete_All.csv` and `Reinforcement_All.csv`
  - Adding new materials to CSV files automatically makes them available throughout the application
- **Refactored cache code**: code cleanup
- **Bridge Entity Management**: Enhanced regeneration workflow to update existing entities instead of only creating new ones
  - `regenerate_bridges_action` now updates parameters of existing bridge entities based on uploaded data
  - Provides detailed feedback showing count of newly created vs. updated bridges
  - Ensures data consistency between uploaded CSV files and VIKTOR entities
- **Support System Overhaul**: Replaced automatic support calculation with user-controlled OptionField for each bridge segment
  - Updated SCIA model integration to handle multiple support types with correct structural constraints
- **Report template**: Changed the report template to a shorter management summary.
- **Explanatory text loadzones**: Added explanation for the application of a separated tram zone on the loadzones tab. 
- **Refactored cache code**: code cleanup
- **Rebar input fields**: Changed all rebar diameter fields from `NumberField` to `OptionField` in the parametrization, using a single source of truth for standard diameters.

### Fixed
- Fixed a typo on the calculation page, changed "werden" to "worden".
- Fixed parameter access patterns for DynamicArray fields in VIKTOR parametrization
- IDEA crack width results: Fixed extraction and display of crack width results from IDEA StatiCa (handles both short- and long-term, no longer shows N/A when results exist).
- Pydantic validation: Improved legacy material support and reinforcement validation (historical concrete/steel, 0mm/negative heights, etc.).

- Refactored SCIA section-plane logic; fixed boundary/edge-section placement and Pydantic v2 compatibility issues. (QA checks passed)


## [`v0.0.15`] - 2025-10-02
### Added
- **Invoer - Dimensies**: minimum values for the dimension field.
  - Description that the bridge always consists of 3 zones.
  - Instructions how to model a bridge with one thickness
  **Source fields for concrete and steel aquality**: added fields for concrete and steelquality source
  **Progress messages**: added progress messages to VIKTOR loading screens (views and download buttons).

### Changed
- **Invoer - berekeningsinstellingen**: NEN 8700 gebruik is now default veiligheidsniveai. Renamed Berekeningsniveau to Verkeersbelasting.
- **SCIA Results Processor Refactor**: Rewrote coordinate extraction and normalized direction vector logic in `scia_results_processor.py` for improved robustness and clarity.
- **Invoer- Wapening**: Order of the fields adjusted, so that you first have longitudinal and transverse top, and then longitudinal and transverse bottom.
  - renamed diameter to Ø in order to shorten the field names for visibility on low resolution screens 

### Fixed
- **IDEA Integration Strip Loads**: Fixed integration strip loads not being applied to IDEA model due to incorrect column name references
  - Updated `_find_matching_strips` and `_apply_strip_loads_to_slab_direction` functions to use 'name' instead of 'Naam'
  - SCIA strip load now apply correctly to IDEA slabs, fixed multiple issues.
- **SCIA TS load issues**: Fixed tow issues regarding the creation of TS load 

## [`v0.0.14`] - 2025-09-23
### Fixed
- **IDEA Integration Strip Results Merge**: Fixed KeyError 'Naam' in IDEA StatiCa integration when processing strip results
  - Updated `_process_scia_integration_strip_results_for_idea_input` function to use correct column name 'name' instead of 'Naam'
  - The upstream processing already renamed 'Naam' to 'name' but the merge operation was still using the old column name
  - Added comprehensive test coverage for the merge functionality in `test_scia_strip_merge_fix.py`
  - This resolves crashes when downloading IDEA analysis results that include integration strip data

## [`v0.0.13`] - 2025-09-23
### Added
- **IDEA StatiCa Integration Enhancements**: Improved the integration with IDEA StatiCa to support returning and processing results from the software.
  - Added integration strip checks to IDEA 
  - Added enhanced functionality to parse and handle results from IDEA StatiCa analyses.
  - Enhanced error handling and logging for IDEA StatiCa workflows.

### Changed
- **Integration Logic**: Refactored integration logic to streamline communication with IDEA StatiCa.
- **Explanatory text**: Changed the explanatory text throughout the app since it contained outdated information and mixed Dutch and English language 
- **Calculation settings**: Changed "Werkelijke wegindeling onderliggend wegennet met bebording", to "Werkelijke wegindeling met bebording".
- **Calculation settings SCIA**: Changed location from "In nodes avg. on macro" to "a"In nodes avg." for node results

## [`v0.0.12`] - 2025-09-18
### Added
- **Load Case Selection System**: Added load case selection table in SCIA → Berekening tab for controlling calculation times
  - Users can enable/disable specific load types (Eigen gewicht, Permanent, UDL, TS, etc.)
  - Table shows load case count per type as calculation time indicator
  - Conditional load case creation based on user selection
- **Historical Materials for IDEA Integration**: Added support for historical material classes in IDEA StatiCa integration
  - Extended material compatibility to include legacy concrete and steel grades
- **Centralized SCIA Unit Conversion System**: Implemented centralized unit handling to ensure units mapping and value conversion stay synchronized
  - Added `UnitConversion` dataclass to store display units, conversion factors, and raw units together
  - Comprehensive test suite with 20+ tests ensuring conversion consistency and backward compatibility
- **Comprehensive SCIA Units Testing**: Added extensive test coverage for SCIA units handling
  - 13 tests for `build_units_mapping()` function covering 1D/2D table detection and edge cases
  - 11 tests for `_format_complete_force_state()` method verifying proper unit application in formatted strings
  - Tests cover 2D plate units (kN/m, kNm/m) vs 1D beam units (kN, kNm)
  - Edge case handling: missing data, non-dict structures, partial units mapping
- **SCIA Units Infrastructure**: Enhanced units mapping and error handling
  - Improved `get_result_summary()` to handle non-dict section data gracefully
  - Units are consistently applied from data extraction through user interface display
- **Traffic load cases**: Added tandem loads and udl for real road layout
  - Added functionality dependent on radio button for road layout
  - Added accidental vehicle according to TAB, parallel and perpendicular to driving direction
  - Added the dispersal function to all the vertical traffic load cases, with a maximum dispersion of 1.0 by 1.0 meters
- **Calculation level**: Added the option for calculation level "werkelijke wegindeling onderliggend wegennet" and "Werkelijke wegindeling onderliggend wegennet met bebording", with different load factors for tandem systems and UDL.
- **Integration strips**: Added four integration strips to the model for both the theoretical and real road layout. One in cross direction at half-span and three longitudinal, one in the middle of the bridge deck, and one at either side of the bridge or road, 0.5 meters inward.

### Changed
- **SCIA Page Structure**: Restructured SCIA page with Downloads and Berekening tabs
- **Load Type Naming**: Shortened names (Permanent, UDL, TS, etc.) for better readability
- **Load Case Selection Interface**: Optimized table layout with checkbox-first design and tooltips
- **Refactored SCIA Unit Handling**: Migrated existing unit conversion functions to use centralized system
  - Maintained full backward compatibility - all existing tests continue to pass
- **Refactoring code SCIA load generation**: Refactored code for the loads helper functions
- **Input tab for calculation settings**: Added explanatory text and changed the tab name from "Belastingcombinaties" to
"Berekeningsinstellingen", since the user input on this tab controls settings for the model calculation in general,
not only for load combinations.
- **Info tab**: Changed and removed irrelevant input fields on the info tab, and changed name of tab to "Paspoortinformatie".

### Fixed
- **VIKTOR Tab Structure Compliance**: Fixed parametrization structure by moving all fields inside tabs
- **JSON Serialization Error**: Fixed load case selection table default values to be JSON-serializable
- **SCIA Unit Synchronization Risk**: Eliminated risk of units mapping and value conversion getting out of sync
- **SCIA Unit Conversion**: Fixed missing unit conversion from N to kN and Nm to kNm in three SCIA result tables
- **SCIA Result Views**: Added proper units display in table headers and values for consistent engineering units
- **Load Boundary Compliance**: Fixed dispersed loads extending beyond bridge dimensions
  - Added `clip_polygon_to_bridge_boundaries()` function to constrain load areas within bridge boundaries
  - Integrated clipping into `dispersal_function()` to automatically clip all dispersed coordinates
  - Prevents wheel loads and other dispersed loads from extending beyond bridge structure
  - Comprehensive test suite verifies load boundary compliance with real bridge data

## [`v0.0.11`] - 2025-08-28
### Added
- **Resource File Access Testing**: Added comprehensive test suite for resource file access patterns
  - Tests all resource paths use absolute paths consistently
  - Verifies critical files exist in repository
  - Validates cross-platform path compatibility
  - Ensures proper file accessibility (binary for templates, UTF-8 for CSVs)
  - Prevents future production deployment issues with missing resources
  - Alpha_q, alpha_trend and psi_nen_8701 factors to vertical traffic loads of load model 1.

### Changed
- **Load Cases**: Altered the generation of UDL traffic loads to a polygon per notional lane and for the remainder of bridge deck

### Fixed
- **SCIA Template Path Issue**: Potential fix for production deployment issue where SCIA template file was not found
  - Changed from relative path (`resources/templates/model.esa`) to absolute path using `SCIA_TEMPLATE_PATH` constant
  - Added `SCIA_TEMPLATE_PATH` constant to `app/constants.py` for consistency with other resource paths
  - Aims to ensure consistent behavior between development and production environments
  - May resolve error: "SCIA template file niet gevonden: resources/templates/model.esa" in production
- **Development Environment Portability**: Fixed user-specific paths in development tools
  - Added `.ruft_venv/` to `.gitignore` to prevent committing user-specific virtual environment paths
  - Removed existing `.ruft_venv` directory from git tracking to avoid path conflicts between developers
  - Quality check script already uses portable relative paths and cross-platform logic
  - Enhanced `setup_dev.py` to automatically create RUFT virtual environment and install all dependencies
  - Added clear IDE setup instructions with exact Python interpreter path for VS Code/Cursor

## [`v0.0.10`] - 2025-08-14
### Added
- **Analysis Caching System**: Added parameter-based caching for SCIA and IDEA calculations
  - Caches analysis results based on input parameters
  - Automatically invalidates cache when parameters change
  - Unified caching API for both SCIA and IDEA analyses
- **Traffic Load Cases**: Added UDL traffic load case implementation
  - Uniform distributed load patterns for traffic analysis
  - Integration with existing load combination system
- **Load Combinations**: Added combinations for service vehicle and accidental vehicle
  - Service vehicle load combinations per design requirements
  - Accidental vehicle impact scenarios
  - SCIA load combinations
- Graceful error handling for XML parsing issues in IDEA results
- **Result Classes**: Added result classes to the SCIA model

### Changed
- **Performance Improvements**: Significant speedup for repeated calculations through caching
  - SCIA: ~14 seconds vs 5+ minutes for new analysis
  - IDEA: ~0.5 seconds vs 10+ seconds for new analysis
  - Automatic cache invalidation when any relevant parameter changes
- **SCIA Functions**: Updated tandem system functions for correct load positioning
  - Improved load placement accuracy
  - Enhanced spatial distribution of forces
- Refactored functions for load combination table

### Removed
- **Redundant Caching Functions**: Simplified API by unifying caching under single function
  - Removed separate caching functions in favor of unified approach
  - Reduced code complexity in caching module

### Fixed
- **IDEA XML Parsing**: Fixed UTF-16 encoded XML parsing issues in IDEA results
  - Proper handling of IDEA output content
  - Improved error handling in results view

## [`v0.0.9`] - 2025-07-31
### Added
- SCIA load cases BG 4000 series, 6000 series, 7000 series, 8000 series, 9000 series and 10000 series
- Accidental vehicle load

### Changed

### Removed

### Fixed
- Service vehicle loadvehicle load.

## [`v0.0.8`] - 2025-07-17
### Added
- IDEA model builder
- IDEA export + viewer
- SCIA load cases BG 1001, 2001, 2002, 2003, 4000 series, 5001 , 8000 series, 9000 series and 10000 series
- **SCIA Analysis Results Table**: Basic structural analysis results display
  - Force results (Mmax, Vmax, Nmax) with location information
  - Displacement results (δmax, θmax) for deformation analysis
  - Load combination information showing active combinations
  - Engineering assessment with moment magnitude evaluation
  - Clean table format with Parameter, Value, Location, and Status columns

### Changed
- SCIA model builder logic
- Refactored code

### Removed
- Removed old Steel and Concrete classes

### Fixed
- Report generator


## [`v0.0.7`] - 2025-07-03
### Added
- Added the option to add supports in Input -> Dimensions
- Added line supports to the SCIA model
- Added csv file for material densities
- Inputfield for line load parapet
- **SCIA Load Framework**: Standardized load cases and combinations
  - EN 1990 compliant load groups (PERMANENT, VARIABLE, ACCIDENTAL, SEISMIC)
  - Full parameter control for permanent and variable load cases
  - Support for ULS, SLS, accidental and seismic combinations
  - Localized patch surface loads with automatic plane creation
  - String-based interface for easy usage
  - Working demonstration with realistic wheel loads
- **Realistic Tandem Load Integration**
  - Support for single lane, double lane, and multi-lane tandem configurations
  - Automatic lane count determination
  - Integration with actual bridge geometry
- **Dutch Standard Load Combinations (NEN 8700/8701)**
  - Automatic gamma factors based on consequence class, safety level, and construction year
  - Psi factors calculated from bridge span length and reference period
  - Support for 6.10a and 6.10b load combination equations
  - ULS combinations: Dead + Traffic, Dead + Traffic + Wind, Dead + Wind + Traffic
  - SLS combinations: Characteristic and Frequent combinations
  - Configurable parameters for consequence class, safety level, and construction year

### Changed
- **Load Module Organization**: Restructured load-related functionality for better package organization
  - Moved `loadcase_helper_functions.py` from `src/` to `src/loads/loadcase_helper_functions.py`
  - Created new `src/loads/` package with proper `__init__.py` documentation
  - Updated all import statements and references throughout codebase
  - Updated documentation and comments to reflect new module location
  - Maintained backward compatibility and functionality during reorganization
- **SCIA File Naming**: Simplified SCIA download zip file naming conventions
  - ESA model files: `{bridge_id}_model.esa` (e.g., `BRU2196_model.esa`)
  - Input files ZIP: `{bridge_id}_Input_Files.zip` (e.g., `BRU2196_Input_Files.zip`)
  - XML files within ZIP: `{bridge_id}.xml` (bridge-specific naming)
  - DEF files within ZIP: `viktor.xml.def` (keeps standard name for XML reference)
  - Added `model.esa` template file to input files ZIP for proper workflow
  - Updated README instructions to Dutch with step-by-step SCIA Engineer import workflow
- **SCIA Model Documentation**: Updated function documentation to accurately reflect complete bridge model creation
  - Corrected `create_simple_scia_plate_model()` description from "simple rectangular plate" to "complete bridge model"
  - Added detailed documentation of zone structure, coordinate system, and node naming conventions
  - Clarified integration points for load zone data replacement

### Removed
### Fixed

## [`v0.0.6`] - 2025-06-19

### Added

#### User-Facing
- Horizontal spawn arrow to the topview
- **SCIA Engineer Integration**: Complete integration with SCIA Engineer for structural analysis
  - SCIA model preview with 3D visualization of bridge geometry
  - XML and DEF file downloads for SCIA Engineer import
  - ESA model generation with worker integration for complete analysis
  - Automatic bridge plate model creation from parametrized dimensions
  - Template-based SCIA project setup with I/O document configuration
- **IDEA StatiCa RCS Integration**: Cross-section analysis capability for bridge assessment
  - IDEA RCS model preview showing reinforced concrete cross-section
  - XML model file download for IDEA StatiCa RCS import
  - Complete analysis workflow with capacity calculations and results download
  - Automatic cross-section generation from first bridge segment parameters
  - Reinforcement layout creation based on parametrized wapening configurations
- **Material Compatibility System**: Comprehensive material support across integrations
  - Centralized material database from CSV files (concrete, reinforcement, prestressing steel)
  - Material validation and normalization for localization support (decimal separator handling)
  - Automatic material mapping for old bridge materials to modern Eurocode equivalents
  - Clear user notifications about material compatibility and automatic conversions
  - Enhanced parametrization descriptions with integration compatibility information
  - Strength-based material mapping (QR24→B500A, QR40→B500B, QR48→B500C)
  - Full support for historical materials (QR series, FeB grades, St. grades) in SCIA
  - IDEA StatiCa limited to modern Eurocode materials (B500A/B/C) with automatic fallback
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
- **SCIA Interface Module** (`src/integrations/scia_interface.py`):
  - Geometry extraction from VIKTOR parameters to SCIA-compatible data structures
  - SCIA model creation with materials, nodes, plates, and analysis setup
  - Worker integration for automated analysis execution
  - Template file management and I/O document configuration
- **IDEA Interface Module** (`src/integrations/idea_interface.py`):
  - Cross-section data extraction from bridge segment parameters
  - IDEA RCS model creation with concrete materials and reinforcement layouts
  - Material enum mapping between project database and IDEA StatiCa enums
  - Analysis execution with timeout handling and result processing
- **Material System Architecture** (`src/common/materials.py`):
  - CSV-based material database with getter functions for each material type
  - Material validation and normalization functions
  - Integration-specific material support functions (SCIA vs IDEA compatibility)
  - Material compatibility information system for user guidance
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
- **Global Import Architecture for CI Pipeline Compatibility**
  - **CI/CD COMPATIBILITY**: Moved all dynamic imports to global level for Linux CI pipeline compatibility
    - Fixed `src.integrations.scia_interface.py` dynamic imports of `get_gamma_factors` and `get_psi_factor`
    - Fixed test imports that were previously inside function calls
    - Added robust import fallback mechanism with `LOAD_FACTORS_AVAILABLE` flag
    - **RESOLVED**: Import issues that could cause failures in GitHub Actions CI environment
    - **ARCHITECTURE**: Maintains clean separation while ensuring cross-platform compatibility
  - **TEST INFRASTRUCTURE**: Updated all test mocking to use correct global import paths
    - Fixed patching of `src.integrations.scia_interface.get_gamma_factors` instead of module-level imports
    - Added proper `LOAD_FACTORS_AVAILABLE` flag handling in tests
    - **VERIFICATION**: All 5 traffic load combination tests passing

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

## [Unreleased]

### Added
- **Comprehensive Load Cases**: Implemented the full set of required load cases for bridge analysis, including self-weight, resting loads, temperature, UDL, pedestrian, service vehicle, unintended vehicle, and tandem systems.
- **Comprehensive Load Groups**: Defined all required SCIA load groups (Permanent, Resting, Temperature, UDL, Crowd, Service Vehicle, Accidental Vehicle, and Tandem Systems) with correct types and relations.
- **Theoretical Traffic Lane Integration (Phase 1)**: Connected tandem loads to theoretical traffic lanes from `load_zone_geometry` system
  - New `tandem_systems_theoretical_lanes()` function generates tandems positioned at theoretical lane centers
  - Enhanced `determine_tandem_function_for_bridge()` with mode selection: "theoretical" vs "eurocode"
  - Theoretical mode uses geometric lane division (bridge_width ÷ 3m) for comprehensive coverage
  - Eurocode mode maintains existing Eurocode notional lane compliance
  - Architecture prepared for Phase 2 (shiftable lanes) and Phase 3 (actual parametrized lanes)
  - Comprehensive test suite covering lane positioning, mode selection, and integration patterns
  - Load case naming distinguishes modes: "TH" prefix for theoretical, "BG" prefix for eurocode

#### Minimal Traffic Load Combinations for Single Lane Testing
- **SIMPLIFIED LOAD COMBINATIONS**: Implemented minimal traffic load combinations focusing on single lane testing
  - Based on `leading_action_positions` approach from `load_factors.py`
  - **Implemented**: `("gr1a", "TS")` - Tandem System leading action
  - **TODO**: Remaining traffic actions (`UDL`, `Enkele as`, `Horizontale belasting`, etc.)
- **NEW FUNCTION**: `_create_traffic_load_combinations_minimal()`
  - Focuses specifically on tandem system (TS) combinations
  - Creates ULS and SLS combinations for both NEN 8700 6.10a and 6.10b equations
  - Includes leading tandem + up to 2 accompanying tandems with psi factors
  - Proper gamma factors from NEN 8700 and psi factors from NEN 8701
- **DEPRECATED**: `_create_dutch_standard_load_combinations()` now redirects to minimal implementation
  - Complex multi-load-type combinations moved to TODO for future implementation
  - Maintains compatibility while simplifying for testing
- **COMPREHENSIVE TESTING**: Updated test suite for minimal traffic combinations
  - Tests single tandem scenarios
  - Tests multiple tandem scenarios (leading + accompanying)
  - Tests fallback behavior and error handling
  - Verifies proper `gr1a TS` naming convention

#### Code Quality Improvements
- **COMPREHENSIVE DOCUMENTATION**: Added detailed TODO sections for future load combination expansion
  - Permanent combinations: `("Perm", "Permanent")`, `("Perm", "Voorspanning")`, `("Perm zet", "Zetting")`
  - Wind combinations: `("Wind gr1a", "Wind Fwk")`, `("Wind gr2", "Wind Fwk")`
  - Temperature combinations: `("Temp gr1", "Temperatuur")`
  - Environmental combinations: `("Sneeuw", "Sneeuw")`
  - Accidental combinations: `("Cal gr1a", "Calamiteit")`, `("Cal gr2", "Calamiteit")`
- **CLEAR IMPLEMENTATION PATH**: Provides step-by-step strategy for expanding from minimal to comprehensive combinations
- **MAINTAINED COMPATIBILITY**: All existing integrations continue to work through redirect mechanism

### Modified

- **INTEGRATION POINT 4**: Updated from comprehensive Dutch combinations to minimal traffic focus
- **TEST STRUCTURE**: Reorganized test classes to separate minimal traffic tests from deprecated compatibility tests
- **LOAD COMBINATION NAMING**: Changed from generic traffic combinations to specific `gr1a_TS` pattern
- **FALLBACK BEHAVIOR**: Updated fallback combinations to use tandem-specific naming (`G+TS` instead of `G+Q`)

### Architecture Impact

- **MINIMAL VIABLE PRODUCT**: Establishes working foundation for single lane traffic analysis
- **SCALABLE DESIGN**: Framework ready for systematic expansion to remaining leading actions
- **CLEAR SEPARATION**: Distinguishes between implemented features and planned expansions
- **INTEGRATION FRIENDLY**: Maintains compatibility with existing tandem load generation system

## Previous Entries

### Realistic Tandem Load Integration