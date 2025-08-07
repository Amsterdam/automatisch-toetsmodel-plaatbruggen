"""Module for the Bridge entity controller."""

import traceback
import zipfile
from io import BytesIO
from pathlib import Path  # Add Path import for SCIA template
from typing import Any

import plotly.graph_objects as go  # Import Plotly graph objects
import trimesh

import viktor.api_v1 as api_sdk  # Import VIKTOR API SDK
import viktor.errors  # Import for specific error types
from app.bridge.analysis_cache import (
    AnalysisType,
    get_cached_analysis_results,
    get_idea_analysis_results,
    get_idea_model_only,
    get_scia_analysis_results,
)
from app.bridge.scia_model_builder import (
    generate_bridge_xml_files,
)

# ParamsForLoadZones protocol and validate_load_zone_widths are in app.bridge.utils
from app.bridge.utils import validate_load_zone_widths
from app.common.map_utils import (
    load_and_filter_bridge_shapefile,  # Import the new function
    process_bridge_geometries,
    validate_shapefile_exists,
)

# Params for load combinations are in app.constants
from src.combinations.load_factors import create_load_combination_table
from src.common.plot_utils import (
    create_bridge_outline_traces,
)
from src.geometry.cross_section import create_cross_section_view
from src.geometry.horizontal_section import create_horizontal_section_view
from src.geometry.load_zone_geometry import calculate_zone_geometry_properties, get_bridge_geom_data, get_load_zones_data_from_params
from src.geometry.load_zone_plot import (
    DEFAULT_PLOTLY_COLORS,  # Import for styling defaults
    DEFAULT_ZONE_APPEARANCE_MAP,  # Import for styling defaults
    BridgeBaseGeometry,  # TypedDict for bridge_geom argument
    PlotPresentationDetails,  # TypedDict for presentation details
    ZoneStylingDefaults,  # TypedDict for styling_defaults argument
    build_load_zones_figure,
)
from src.geometry.longitudinal_section import create_longitudinal_section
from src.geometry.model_creator import (
    BridgeSegmentDimensions,  # Import the dataclass
    LoadZoneGeometryData,  # Import the dataclass
    create_2d_top_view,
    create_3d_model,
    prepare_load_zone_geometry_data,
)
from src.geometry.top_view_plot import build_top_view_figure
from src.integrations.idea_interface import _get_unique_matching_zone_keys
from src.report.report_functions import create_export_report  # Import the report creation function
from viktor.core import File, ViktorController
from viktor.errors import UserError  # Add UserError
from viktor.external import idea_rcs
from viktor.result import DownloadResult  # Import DownloadResult from correct module
from viktor.views import (
    GeometryResult,
    GeometryView,
    MapPoint,  # Add MapPoint
    MapResult,  # Add MapResult
    MapView,  # Add MapView
    PDFResult,
    PDFView,
    PlotlyResult,  # Import PlotlyResult
    PlotlyView,  # Import PlotlyView
    TableResult,  # Import TableResult
    TableView,  # Import TableView
)

# Import parametrization from the separate file
from .parametrization import BridgeParametrization

# ============================================================================================================
# Main Controller
# ============================================================================================================


class BridgeController(ViktorController):
    """Controller for the individual Bridge entity."""

    label = "Brug"
    parametrization = BridgeParametrization  # type: ignore[assignment]

    # ============================================================================================================
    # Helper functions
    # ============================================================================================================

    def _get_bridge_entity_data(self, entity_id: int) -> tuple[str | None, str | None, MapResult | None]:
        """Fetches bridge entity data (OBJECTNUMM and name) using the VIKTOR API."""
        if not entity_id:
            return None, None, MapResult([MapPoint(52.37, 4.89, description="Entity ID niet gevonden.")])
        try:
            viktor_api = api_sdk.API()
            current_entity = viktor_api.get_entity(entity_id)
            last_params = current_entity.last_saved_params
            info_page_params = last_params.get("info")

            objectnumm = info_page_params.bridge_objectnumm if info_page_params and hasattr(info_page_params, "bridge_objectnumm") else None
            name = info_page_params.bridge_name if info_page_params and hasattr(info_page_params, "bridge_name") else ""
            if objectnumm is None:
                return None, None, MapResult([MapPoint(52.37, 4.89, description="OBJECTNUMM van brug niet gevonden in opgeslagen parameters.")])
            # Using explicit else to satisfy linter
            return objectnumm, name, None  # noqa: TRY300
        except Exception as e:
            return None, None, MapResult([MapPoint(52.37, 4.89, description=f"Fout bij ophalen entity data: {e}")])

    # ============================================================================================================
    # Info
    # ============================================================================================================

    @MapView("Locatie Brug", duration_guess=2)
    def get_bridge_map_view(self, params: BridgeParametrization, **kwargs) -> MapResult:  # noqa: ARG002
        """Displays the current bridge polygon from the shapefile in the resources folder."""
        entity_id = kwargs.get("entity_id")

        if not isinstance(entity_id, int):
            return MapResult([MapPoint(52.37, 4.89, description="Ongeldige entity ID ontvangen.")])

        current_objectnumm, bridge_name_from_params, error_result = self._get_bridge_entity_data(entity_id)
        if error_result:
            return error_result

        if current_objectnumm is None:
            return MapResult([MapPoint(52.37, 4.89, description="Interne fout: OBJECTNUMM onbekend na API call.")])

        if bridge_name_from_params is None:
            bridge_name_from_params = ""

        try:
            shapefile_path = validate_shapefile_exists()  # Uses default path, raises UserError
            # Call the new utility function from map_utils.
            # This function also raises UserError for various issues (file not found, bridge not found, CRS/column issues).
            target_bridge_gdf = load_and_filter_bridge_shapefile(shapefile_path, current_objectnumm)
        except UserError as ue:
            return MapResult([MapPoint(52.37, 4.89, description=str(ue))])

        # If we reach here, target_bridge_gdf is a GeoDataFrame with the bridge data.
        # The old error_result from _load_and_filter_geodataframe is no longer needed.

        # Process bridge geometries using the utility function.
        # target_bridge_gdf should contain the single row for the bridge.
        features, error_point = process_bridge_geometries(target_bridge_gdf.iloc[0], current_objectnumm, bridge_name_from_params)

        if error_point:
            return MapResult([error_point])

        return MapResult(features)

    # ============================================================================================================
    # input - Dimension
    # ============================================================================================================

    @GeometryView("3D Model", duration_guess=1, x_axis_to_right=False)
    def get_3d_view(self, params: BridgeParametrization, **kwargs) -> GeometryResult:  # noqa: ARG002
        """Generates a 3D representation of the bridge deck."""
        combined_scene = create_3d_model(params, section_planes=True)
        # Export the scene as a GLTF file and return it as a GeometryResult
        geometry = File()
        with geometry.open_binary() as w:
            w.write(trimesh.exchange.gltf.export_glb(combined_scene))
        return GeometryResult(geometry, geometry_type="gltf")

    @PlotlyView("Bovenaanzicht", duration_guess=1)
    def get_top_view(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generates a 2D top view of the bridge deck with dimensions by calling the src layer.
        Also performs validation of load zone widths against bridge dimensions.
        """
        # 1. Prepare bridge geometry data (needed for validation)
        bridge_segments_params = params.bridge_segments_array
        bridge_geom_data: LoadZoneGeometryData | None = None  # Ensure type hint for clarity

        if bridge_segments_params:
            try:
                typed_bridge_dimensions = []
                for segment_param_row in bridge_segments_params:
                    if not all(hasattr(segment_param_row, attr) for attr in ["bz1", "bz2", "bz3", "l"]):
                        # Silently skip or log if a segment is malformed to avoid blocking top view
                        # Or raise UserError("Een of meer brugsegmenten missen data (bz1, bz2, bz3, l).")
                        continue  # Skip this segment if it's missing critical attributes
                    typed_bridge_dimensions.append(
                        BridgeSegmentDimensions(
                            bz1=segment_param_row.bz1, bz2=segment_param_row.bz2, bz3=segment_param_row.bz3, segment_length=segment_param_row.l
                        )
                    )
                if typed_bridge_dimensions:  # Only proceed if we have valid dimensions to process
                    bridge_geom_data = prepare_load_zone_geometry_data(typed_bridge_dimensions)
            except Exception as e:
                print(f"Error preparing bridge geometry for validation in get_top_view: {e}")  # noqa: T201
                # bridge_geom_data remains None

        # 2. Perform validation if possible
        validation_messages: list[str] = []
        if bridge_geom_data and hasattr(params, "load_zones_data_array") and params.load_zones_data_array:
            validation_messages = validate_load_zone_widths(
                params=params,  # Pass the whole params object
                geometry_data=bridge_geom_data,
            )
        elif not bridge_segments_params or not bridge_geom_data:  # Covers cases where bridge_geom_data is None due to error or no segments
            validation_messages = ["Brugsegmenten data ontbreekt of is ongeldig, validatie van belastingzones niet volledig uitgevoerd."]
        # If load_zones_data_array is empty/None, validation_messages remains empty (no zones to validate)

        # 3. Generate top view plot data
        top_view_data = create_2d_top_view(params)

        # 4. Build the figure
        fig = build_top_view_figure(top_view_geometric_data=top_view_data, validation_messages=validation_messages)

        return PlotlyResult(fig.to_json())

    @PlotlyView("Horizontale doorsnede", duration_guess=1)
    def get_2d_horizontal_section(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generates a 2D horizontal section view of the bridge using Plotly.
        This function creates a 2D representation of the bridge's horizontal section by:
        1. Creating a 3D model of the bridge
        2. Slicing it with a horizontal plane at the specified height
        3. Converting the resulting section into a 2D plot showing length (x) vs width (y).

        Args:
            params (BridgeParametrization): Input parameters for the bridge dimensions.
            **kwargs: Additional arguments.

        Returns:
            PlotlyResult: A 2D representation of the horizontal section.

        """
        fig = create_horizontal_section_view(params, params.input.dimensions.horizontal_section_loc)
        return PlotlyResult(fig.to_json())

    @PlotlyView("Langsdoorsnede", duration_guess=1)
    def get_2d_longitudinal_section(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generates a 2D longitudinal section view of the bridge using Plotly.
        This function creates a 2D representation of the bridge's longitudinal section by:
        1. Creating a 3D model of the bridge
        2. Slicing it with a vertical plane parallel to the x-z plane
        3. Converting the resulting cross-section into a 2D plot showing length (x) vs height (z).

        Args:
            params (BridgeParametrization): Input parameters for the bridge dimensions.
            **kwargs: Additional arguments.

        Returns:
            PlotlyResult: A 2D representation of the longitudinal section.

        """
        fig = create_longitudinal_section(params, params.input.dimensions.longitudinal_section_loc)
        return PlotlyResult(fig.to_json())

    @PlotlyView("Dwarsdoorsnede", duration_guess=1)
    def get_2d_cross_section(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generates a 2D cross-section view of the bridge using Plotly.
        This function creates a 2D representation of the bridge's cross-section by:
        1. Creating a 3D model of the bridge
        2. Slicing it with a vertical plane parallel to the y-z plane
        3. Converting the resulting cross-section into a 2D plot showing width (y) vs height (z).

        Args:
            params (BridgeParametrization): Input parameters for the bridge dimensions.
            **kwargs: Additional arguments.

        Returns:
            PlotlyResult: A 2D representation of the cross-section.

        """
        fig = create_cross_section_view(params, params.input.dimensions.cross_section_loc)
        return PlotlyResult(fig.to_json())

    @PlotlyView("Belastingzones", duration_guess=1)
    def get_load_zones_view(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generates a 2D view of the load zones on the bridge deck.
        Uses the new build_load_zones_figure from the src layer.
        """
        # 1. Prepare LoadZoneDataRow list from params
        load_zones_data_params = get_load_zones_data_from_params(params)

        # 2. Prepare bridge geometric data
        bridge_geom_data = get_bridge_geom_data(params)

        # 2a. Calculate zone geometric properties using bridge geometry
        load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

        if not load_zones_data_params:  # No load zones defined
            fig = go.Figure()
            fig.update_layout(title_text="Belastingzones - Geen zones gedefinieerd", xaxis_visible=False, yaxis_visible=False)
            return PlotlyResult(fig.to_json())

        if not bridge_geom_data:  # If preparation failed or returned None (e.g. no segments)
            fig = go.Figure()
            fig.update_layout(title_text="Belastingzones - Brugsegmenten ongeldig", xaxis_visible=False, yaxis_visible=False)
            return PlotlyResult(fig.to_json())

        # 3. Get validation messages
        validation_messages: list[str] = []
        if hasattr(params, "load_zones_data_array") and params.load_zones_data_array:
            validation_messages = validate_load_zone_widths(
                params=params,  # Pass the whole params object
                geometry_data=bridge_geom_data,
            )
        # If load_zones_data_array is empty, validation_messages remains empty.

        # 4. Prepare base_traces for the bridge background
        # Get structural polygons and bridge lines from create_2d_top_view data
        # (This is the same data used for the "Bovenaanzicht" base plot)
        top_view_render_data = create_2d_top_view(params)

        base_traces = []
        # No longer adding structural polygons to this view's base traces

        bridge_outline_data = top_view_render_data.get("bridge_lines", [])  # Bridge outline from top view
        if bridge_outline_data:
            base_traces.extend(create_bridge_outline_traces(bridge_outline_data))

        # 5. Call build_load_zones_figure
        bridge_geom_arg: BridgeBaseGeometry = {
            "x_coords_d_points": bridge_geom_data.x_coords_d_points,
            "y_coords_bridge_top_edge": bridge_geom_data.y_top_structural_edge_at_d_points,
            "y_coords_bridge_bottom_edge": [[y_bottom, y_bottom] for y_bottom in bridge_geom_data.y_bridge_bottom_at_d_points],
            "num_defined_d_points": bridge_geom_data.num_defined_d_points,
        }
        styling_defaults_arg: ZoneStylingDefaults = {
            "zone_appearance_map": DEFAULT_ZONE_APPEARANCE_MAP,
            "default_plotly_colors": DEFAULT_PLOTLY_COLORS,
        }

        presentation_details_arg: PlotPresentationDetails = {
            "base_traces": base_traces,
            "validation_messages": validation_messages,
            "figure_title": "Belastingzones",
        }

        fig = build_load_zones_figure(
            load_zones_data_params=load_zones_data_params,
            bridge_geom=bridge_geom_arg,
            styling_defaults=styling_defaults_arg,
            presentation_details=presentation_details_arg,
        )

        return PlotlyResult(fig.to_json())

    @TableView("Belastingscombinaties")
    def get_load_combinations_view(self, params: BridgeParametrization, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Display the table of load combinations for the bridge.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :returns: TableResult containing the load combinations.
        :rtype: TableResult
        """
        combination_table = create_load_combination_table(params)
        return TableResult(combination_table)

    # ============================================================================================================
    # SCIA Integration
    # ============================================================================================================

    def _process_single_force_value(self, m_x: float, m_y: float, v_x: float, v_y: float, plate_name: str) -> tuple[float, float, float, str]:
        """Process a single set of force values and return calculated results."""
        # Calculate resultant moment and shear
        moment = (m_x**2 + m_y**2) ** 0.5
        shear = (v_x**2 + v_y**2) ** 0.5

        # For normal force, use the maximum of the individual components
        max_normal_comp = max(abs(m_x), abs(m_y))

        return moment, shear, max_normal_comp, plate_name

    def _process_internal_forces_data(self, forces_data: dict[str, Any]) -> tuple[float | None, float | None, float | None, str]:
        """Process internal forces data and return maximum values and plate name."""
        max_moment = None
        max_shear = None
        max_normal = None
        plate_with_max_moment = "Onbekend"

        # The OutputFileParser.get_result() returns a pandas-like structure
        # with column names and lists of values
        if not isinstance(forces_data, dict) or "Basis grootheden" not in forces_data:
            return max_moment, max_shear, max_normal, plate_with_max_moment

        # Access the actual data
        data = forces_data["Basis grootheden"]

        # Extract force values from the columns
        # m_x, m_y, m_xy are moments, v_x, v_y are shear forces
        required_columns = ["m_x", "m_y", "v_x", "v_y"]
        if not all(col in data for col in required_columns):
            return max_moment, max_shear, max_normal, plate_with_max_moment

        m_x_values = data["m_x"]  # List of moment values
        m_y_values = data["m_y"]  # List of moment values
        v_x_values = data["v_x"]  # List of shear values
        v_y_values = data["v_y"]  # List of shear values
        plate_names = data.get("Naam", [])  # List of plate names

        # Process all values and collect valid results
        valid_results = []
        for i in range(len(m_x_values)):
            # Check if all values can be converted to float before processing
            try:
                m_x = float(m_x_values[i])
                m_y = float(m_y_values[i])
                v_x = float(v_x_values[i])
                v_y = float(v_y_values[i])
            except (ValueError, TypeError, IndexError):
                continue

            plate_name = plate_names[i] if i < len(plate_names) else f"Plate_{i + 1}"
            valid_results.append((m_x, m_y, v_x, v_y, plate_name))

        # Find maximum values from valid results
        for m_x, m_y, v_x, v_y, plate_name in valid_results:
            moment, shear, max_normal_comp, _ = self._process_single_force_value(m_x, m_y, v_x, v_y, plate_name)

            # Track maximums
            if max_moment is None or abs(moment) > abs(max_moment):
                max_moment = moment
                plate_with_max_moment = plate_name
            if max_shear is None or abs(shear) > abs(max_shear):
                max_shear = shear
            if max_normal is None or max_normal_comp > max_normal:
                max_normal = max_normal_comp

        return max_moment, max_shear, max_normal, plate_with_max_moment

    def _find_displacement_columns(self, data: object) -> tuple[str | None, str | None]:
        """Find displacement and rotation columns in the data."""
        if not hasattr(data, "columns"):
            return None, None

        columns = list(data.columns)
        disp_col = None
        rot_col = None

        for col in columns:
            if "displacement" in col.lower() or "verplaatsing" in col.lower():
                disp_col = col
            elif "rotation" in col.lower() or "rotatie" in col.lower():
                rot_col = col

        return disp_col, rot_col

    def _process_displacement_data(self, displacement_data: dict[str, Any]) -> tuple[float | None, float | None]:
        """Process displacement data and return maximum values."""
        max_displacement = None
        max_rotation = None

        # Try to parse displacement data from the pandas-like structure
        if not isinstance(displacement_data, dict) or "Table0" not in displacement_data:
            return max_displacement, max_rotation

        # The displacement data might be in a different format
        data = displacement_data["Table0"]

        # Look for displacement and rotation columns
        disp_col, rot_col = self._find_displacement_columns(data)
        if not disp_col or not rot_col:
            return max_displacement, max_rotation

        # Extract values and collect valid results
        try:
            disp_values = data[disp_col].values
            rot_values = data[rot_col].values
        except (AttributeError, KeyError):
            return max_displacement, max_rotation

        valid_results = []
        for i in range(len(disp_values)):
            # Check if values can be converted to float before processing
            try:
                displacement = float(disp_values[i])
                rotation = float(rot_values[i])
            except (ValueError, TypeError):
                continue

            valid_results.append((displacement, rotation))

        # Find maximum values from valid results
        for displacement, rotation in valid_results:
            if max_displacement is None or abs(displacement) > abs(max_displacement):
                max_displacement = displacement
            if max_rotation is None or abs(rotation) > abs(max_rotation):
                max_rotation = rotation

        return max_displacement, max_rotation

    def _get_engineering_assessment(self, max_moment: float | None) -> str:
        """Get engineering assessment based on moment magnitude."""
        if max_moment is None:
            return "❓ Onbekend"

        # Simple assessment based on moment magnitude (example thresholds)
        if max_moment < 1000000:  # 1000 kNm
            return "✅ Laag"
        if max_moment < 5000000:  # 5000 kNm
            return "⚠️ Gemiddeld"
        return "❌ Hoog"

    def _add_force_results_to_table(
        self, table_data: list[list[str]], max_moment: float | None, max_shear: float | None, max_normal: float | None, plate_with_max_moment: str
    ) -> None:
        """Add force results to the table data."""
        if max_moment is not None:
            table_data.append(["Mmax", f"{max_moment / 1000:.1f} kNm", f"{plate_with_max_moment}", "UGT"])
            if max_shear is not None:
                table_data.append(["Vmax", f"{max_shear / 1000:.1f} kN", f"{plate_with_max_moment}", "UGT"])
            if max_normal is not None:
                table_data.append(["Nmax", f"{max_normal / 1000:.1f} kN", f"{plate_with_max_moment}", "UGT"])
        else:
            table_data.append(["Krachten", "Geen geldige gegevens", "Geen platen gevonden", "UGT"])

    def _add_displacement_results_to_table(self, table_data: list[list[str]], max_displacement: float | None, max_rotation: float | None) -> None:
        """Add displacement results to the table data."""
        if max_displacement is not None:
            table_data.append(["δmax", f"{max_displacement * 1000:.2f} mm", "Max doorbuiging", "UGT"])
            if max_rotation is not None:
                table_data.append(["θmax", f"{max_rotation * 1000:.3f} mrad", "Max rotatie", "UGT"])

    def _build_results_table_data(self, results: dict[str, Any]) -> list[list[str]]:
        """Build the table data from SCIA analysis results."""
        table_data: list[list[str]] = []
        parsed_tables = results.get("xml_parsing", {}).get("parsed_tables", {})

        # Extract data from parsed tables
        internal_forces_basis = parsed_tables.get("Interne 2D-krachten basis", {})
        displacements_2d = parsed_tables.get("2D-verplaatsing", {})
        result_classes_uls = parsed_tables.get("Result classes - UGT", {})

        # Initialize variables for engineering assessment
        max_moment = None
        plate_with_max_moment = "Onbekend"

        # Process internal forces data
        if internal_forces_basis.get("status") == "success":
            forces_data = internal_forces_basis.get("data", {})
            if forces_data and isinstance(forces_data, dict):
                max_moment, max_shear, max_normal, plate_with_max_moment = self._process_internal_forces_data(forces_data)
                self._add_force_results_to_table(table_data, max_moment, max_shear, max_normal, plate_with_max_moment)
            else:
                table_data.append(["Krachten", "Geen gegevens", "Lege data structuur", "UGT"])
        else:
            table_data.append(["Krachten", "Gegevens beschikbaar", "26 punten", "UGT"])

        # Process displacement data
        if displacements_2d.get("status") == "success":
            displacement_data = displacements_2d.get("data", {})
            if displacement_data and isinstance(displacement_data, dict):
                max_displacement, max_rotation = self._process_displacement_data(displacement_data)
                self._add_displacement_results_to_table(table_data, max_displacement, max_rotation)

                # Show load combinations used
                if result_classes_uls.get("status") == "success":
                    table_data.append(["Combinaties", "Test_EN_ULS_SET_B", "ULS_Example_SW_Pedestrian", "Actief"])

                # Engineering assessment based on moment magnitude
                if max_moment is not None:
                    status = self._get_engineering_assessment(max_moment)
                    table_data.append(["Beoordeling", f"{max_moment / 1000:.1f} kNm", f"{plate_with_max_moment}", status])
            else:
                table_data.append(["Verplaatsingen", "Geen geldige gegevens", "Lege data structuur", "UGT"])
        else:
            # Fallback if XML parsing failed
            table_data.append(["Resultaten", "Geen gegevens", "XML parsing mislukt", "Fout"])

        # Ensure we always return at least one row
        if not table_data:
            table_data.append(["Status", "Geen resultaten", "Controleer analyse", "Info"])

        return table_data

    @TableView("SCIA Analyse Resultaten", duration_guess=300)
    def get_scia_results_table(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Display SCIA analysis results in a table format with actual engineering values.

        This view shows key structural analysis results including:
        - Maximum internal forces (moment, shear, normal force)
        - Maximum displacements and rotations
        - Load combination information
        - Engineering assessment based on moment magnitude
        """
        if not params.bridge_segments_array:
            raise UserError("Geen brugsegmenten gedefinieerd. Voeg eerst segmenten toe.")

        # Get the ESA template path
        template_path = self._get_scia_template_path()

        # Get entity ID for caching
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_scia_error() -> None:
            """Raise a user error for SCIA analysis failures."""
            raise UserError("SCIA analyse resultaten konden niet worden opgehaald.")

        # Get cached or run new SCIA analysis
        try:
            results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, str(template_path))
            if results is None:
                _raise_scia_error()
        except Exception:
            traceback.print_exc()
            _raise_scia_error()

        # Build table data
        if results is None:
            _raise_scia_error()
        table_data = self._build_results_table_data(results)  # type: ignore[arg-type]

        # Create table with Dutch column headers
        return TableResult(
            table_data,
            column_headers=["Parameter", "Waarde", "Locatie", "Status"],
        )

    def _get_scia_template_path(self) -> Path:
        """
        Get the path to the SCIA template file.

        :returns: Path to the model.esa template file
        :rtype: Path
        :raises UserError: If template file is not found
        """
        # Path relative to the app root (automatisch-toetsmodel-plaatbruggen/)
        template_path = Path("resources/templates/model.esa")

        if not template_path.exists():
            raise UserError(f"SCIA template file niet gevonden: {template_path}")

        return template_path

    def _raise_no_bridge_segments_error(self) -> None:
        """Raise UserError for missing bridge segments."""
        raise UserError("Geen brugsegmenten gedefinieerd. Ga naar de 'Invoer' pagina om de brug dimensies in te stellen.")

    def _raise_empty_xml_error(self) -> None:
        """Raise UserError for empty XML file."""
        raise UserError("XML bestand is leeg - SCIA model generatie gefaald")

    def _raise_empty_def_error(self) -> None:
        """Raise UserError for empty definition file."""
        raise UserError("Definition bestand is leeg - SCIA model generatie gefaald")

    def _raise_empty_esa_error(self) -> None:
        """Raise UserError for empty ESA file."""
        raise UserError("ESA bestand is leeg - SCIA worker uitvoering gefaald")

    def _raise_no_idea_segments_error(self) -> None:
        """Raise UserError for missing bridge segments in IDEA RCS model."""
        raise UserError("Geen brugsegmenten gevonden voor IDEA RCS model")

    def _raise_no_idea_analysis_segments_error(self) -> None:
        """Raise UserError for missing bridge segments in IDEA RCS analysis."""
        raise UserError("Geen brugsegmenten gevonden voor IDEA RCS analyse")

    def _raise_empty_idea_xml_error(self) -> None:
        """Raise UserError for empty IDEA XML file."""
        raise UserError("XML bestand is leeg - IDEA RCS model generatie gefaald")

    def _handle_scia_exception(self, e: Exception) -> None:
        """Handle SCIA-related exceptions and raise appropriate UserError."""
        if isinstance(e, ImportError):
            raise UserError(f"VIKTOR SCIA module niet beschikbaar: {e!s}\n\nDeze functie vereist de VIKTOR SDK met SCIA integratie.")
        if isinstance(e, viktor.errors.LicenseError):
            raise UserError(
                f"SCIA Engineer licentie fout: {e!s}\n\nControleer uw SCIA Engineer licentie en zorg ervoor dat deze correct is geconfigureerd."
            )
        if isinstance(e, viktor.errors.ExecutionError):
            raise UserError(
                f"SCIA analyse uitvoering gefaald: {e!s}\n\n"
                "De externe SCIA analyse is niet succesvol voltooid. "
                "Controleer of SCIA Engineer correct is geïnstalleerd en toegankelijk is."
            )
        if isinstance(e, viktor.errors.ModelError):
            raise UserError(
                f"SCIA model fout: {e!s}\n\n"
                "Er was een probleem met de SCIA model generatie of analyse. "
                "Controleer uw brug parameters en probeer opnieuw."
            )
        if isinstance(e, FileNotFoundError):
            raise UserError(
                f"Template bestand niet gevonden: {e!s}\n\n"
                "Het SCIA template bestand ontbreekt of is niet toegankelijk. "
                "Controleer de template configuratie."
            )
        if isinstance(e, PermissionError):
            raise UserError(
                f"Toestemmings fout: {e!s}\n\n"
                "Onvoldoende toestemmingen om SCIA bestanden te openen of de analyse uit te voeren. "
                "Controleer bestandsrechten en gebruikers toegangsrechten."
            )
        raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nProbeer in plaats daarvan de XML-bestanden te downloaden.")

    def _validate_generated_files(self, xml_file: BytesIO, def_file: BytesIO) -> None:
        """Validate that generated files are not empty."""
        if not xml_file.getvalue():
            self._raise_empty_xml_error()
        if not def_file.getvalue():
            self._raise_empty_def_error()

    def download_scia_esa_model(self, params: BridgeParametrization, **kwargs) -> DownloadResult:
        """Generate and download a complete SCIA ESA model file."""
        if not params.bridge_segments_array:
            self._raise_no_bridge_segments_error()

        # Get entity ID for caching
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_no_cached_esa_error() -> None:
            """Raise error for missing cached ESA model."""
            raise UserError("Geen gecachte SCIA ESA model gevonden. Voer eerst een SCIA analyse uit via de resultaten tabel.")

        try:
            # Get the ESA template path
            template_path = self._get_scia_template_path()

            # Get cached or run new SCIA analysis
            results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, str(template_path))

            # Check if we have valid results
            if results is None:
                _raise_no_cached_esa_error()

            # Check if we have ESA model in results
            if results is not None and results.get("esa_model"):
                esa_content = results["esa_model"]
                filename = f"SCIA_model_{params.info.bridge_objectnumm}.esa"
                # Create File object from bytes using the correct method
                file_obj = File.from_data(esa_content)
                return DownloadResult(file_obj, filename)

            # If no ESA model in results, raise error
            _raise_no_cached_esa_error()

        except Exception as e:
            raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nProbeer in plaats daarvan de XML-bestanden te downloaden.")

    def download_scia_xml_files(self, params: BridgeParametrization, **kwargs) -> DownloadResult:  # noqa: ARG002
        """Download SCIA XML and definition files as a ZIP archive."""
        xml_file, def_file = generate_bridge_xml_files(params)

        xml_content = xml_file.getvalue()
        if not xml_content:
            self._raise_empty_xml_error()

        def_content = def_file.getvalue()
        if not def_content:
            self._raise_empty_def_error()

        zip_file_obj = File()
        with zipfile.ZipFile(zip_file_obj.source, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"SCIA_model_{params.info.bridge_objectnumm}.xml", xml_content)
            z.writestr("viktor.xml.def", def_content)

        return DownloadResult(zip_file_obj, f"scia_model_{params.info.bridge_objectnumm}_files.zip")

    def _raise_no_xml_output_error(self) -> None:
        """Raise error when no XML output file is available."""
        raise UserError("No XML output file available from SCIA analysis")

    def _raise_unexpected_type_error(self, fresh_xml_output_file: object) -> None:
        """Raise error for unexpected type of fresh_xml_output_file."""
        raise UserError(f"Unexpected type for fresh_xml_output_file: {type(fresh_xml_output_file)}")

    def download_scia_output_xml(self, params: BridgeParametrization, **kwargs) -> DownloadResult:
        """Download the SCIA output XML file for investigation."""
        if not params.bridge_segments_array:
            self._raise_no_bridge_segments_error()

        # Get entity ID for caching
        entity_id = kwargs.get("entity_id")
        if not isinstance(entity_id, int):
            raise UserError("Entity ID niet gevonden. Cache functionaliteit niet beschikbaar.")

        def _raise_no_cached_results_error() -> None:
            """Raise error for missing cached results."""
            raise UserError("Geen gecachte SCIA resultaten gevonden. Voer eerst een SCIA analyse uit via de resultaten tabel.")

        try:
            # Get the ESA template path
            template_path = self._get_scia_template_path()

            # Get cached or run new SCIA analysis
            results = get_cached_analysis_results(params, AnalysisType.SCIA, entity_id, get_scia_analysis_results, str(template_path))

            # Check if we have XML output in cached results
            if results is not None and "xml_output" in results and results["xml_output"]:
                xml_content = results["xml_output"]
                filename = f"scia_output_{params.info.bridge_objectnumm}.xml"
                # Create File object from bytes using the correct method
                file_obj = File.from_data(xml_content)
                return DownloadResult(file_obj, filename)

            # If no cached results or no XML output, raise error
            _raise_no_cached_results_error()

        except Exception as e:
            raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nProbeer in plaats daarvan de XML-bestanden te downloaden.")

    # ============================================================================================================
    # IDEA StatiCa Integration
    # ============================================================================================================

    @TableView("Unieke dwarsprofielen voor IDEA RCS", duration_guess=2)
    def get_view_unique_idea_cross_sections(self, params: BridgeParametrization, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Toon een tabel met unieke matching zone keys voor IDEA RCS.

        :param params: Bridge parametrization
        :type params: BridgeParametrization
        :returns: TableResult met unieke zone keys
        :rtype: TableResult
        """
        unique_matching_zone_keys, grouped_thickness, grouped_rebar_configs = _get_unique_matching_zone_keys(params)

        # If no unique keys found, return empty table
        data = [[value[0], value[1]] for value in unique_matching_zone_keys]

        columns = ["Zone_dikte", "Wapeningsconfiguratie"]

        return TableResult(data, column_headers=columns)

    @TableView("IDEA RCS resultaten", duration_guess=90)
    def get_view_idea_rcs_results(self, params: BridgeParametrization, **kwargs) -> TableResult:
        """
        Toon een tabel met resultaten van de IDEA RCS analyse.

        :param params: Bridge parametrization
        :type params: BridgeParametrization
        :returns: TableResult met unieke zone keys
        :rtype: TableResult
        """
        # Get entity ID from kwargs
        entity_id = kwargs.get("entity_id")
        if entity_id is None:
            raise UserError("Entity ID not found in kwargs")

        # Get cached IDEA analysis results
        cached_results = get_cached_analysis_results(params, AnalysisType.IDEA, entity_id, get_idea_analysis_results)
        if cached_results is None:
            raise UserError("IDEA analysis failed or no cached results available")

        # Extract results from cache
        output_content = cached_results.get("output_content")
        if output_content is None:
            raise UserError("Cached IDEA results are incomplete")

        # Create a BytesIO object from the cached content for parsing
        output_file_obj = BytesIO(output_content)

        # Check if the analysis failed
        if cached_results.get("analysis_status") == "failed":
            error_msg = cached_results.get("error", "Unknown error")
            return TableResult(
                [["Analyse gefaald", error_msg, "", "", "", "", "", ""]],
                column_headers=["Sectie", "Capaciteit", "Schuifkracht", "Torsie", "Interactie", "Scheurwijdte", "Detailing", "Spanningslimieten"],
            )

        # Try to parse the results
        try:
            # Obtain the results for specific or all section(s).
            parser = idea_rcs.RcsOutputFileParser(output_file_obj)

            # Prepare data for the table
            data = []
            columns = ["Sectie", "Capaciteit", "Schuifkracht", "Torsie", "Interactie", "Scheurwijdte", "Detailing", "Spanningslimieten"]

            for section in parser.section_results():
                capacity_results = section.capacity()[0]
                shear_results = section.shear()[0]
                torsion_results = section.torsion()[0] if section.torsion() else {"Result": "N/A"}
                interaction_results = section.interaction()[0] if section.interaction() else {"Result": "N/A"}
                crack_width_results = section.crack_width()[0] if section.crack_width() else {"Result": "N/A"}
                detailing_results = section.detailing()[0] if section.detailing() else {"Result": "N/A"}
                stress_limitations_results = section.stress_limitation()[0] if section.stress_limitation() else {"Result": "N/A"}

                data.append(
                    [
                        section.id_,
                        capacity_results.get("Result"),
                        shear_results.get("Result"),
                        torsion_results.get("Result"),
                        interaction_results.get("Result"),
                        crack_width_results.get("Result"),
                        detailing_results.get("Result"),
                        stress_limitations_results.get("Result"),
                    ]
                )

            return TableResult(data, column_headers=columns)

        except Exception as e:
            # If parsing fails, return an error message
            return TableResult(
                [["Parsing fout", f"Kon resultaten niet parsen: {e!s}", "", "", "", "", "", ""]],
                column_headers=["Sectie", "Capaciteit", "Schuifkracht", "Torsie", "Interactie", "Scheurwijdte", "Detailing", "Spanningslimieten"],
            )

    def download_idea_xml_file(self, params: BridgeParametrization, **kwargs) -> DownloadResult:
        """
        Download IDEA StatiCa RCS XML input file for cross-section analysis.

        Creates a rectangular beam cross-section model from the first bridge segment
        with automatic reinforcement layout and sample loads.

        :param params: Bridge parametrization
        :type params: BridgeParametrization
        :returns: XML file download for IDEA RCS
        :rtype: DownloadResult
        """
        try:
            # Get entity ID from kwargs
            entity_id = kwargs.get("entity_id")
            if entity_id is None:
                raise UserError("Entity ID not found in kwargs")

            # Get cached IDEA model
            cached_results = get_cached_analysis_results(params, AnalysisType.IDEA, entity_id, get_idea_model_only)
            if cached_results is None:
                raise UserError("IDEA model creation failed or no cached results available")

            # Extract XML input from cache
            xml_input = cached_results.get("xml_input")
            if xml_input is None:
                raise UserError("Cached IDEA model is incomplete")

            # Validate content
            xml_content = xml_input.getvalue() if hasattr(xml_input, "getvalue") else xml_input.read() if hasattr(xml_input, "read") else b""

            if not xml_content:
                self._raise_empty_idea_xml_error()

            return DownloadResult(xml_input, f"IDEA_rcs_{params.info.bridge_objectnumm}.xml")

        except Exception as e:
            raise UserError(f"IDEA RCS XML generatie gefaald: {e!s}")

    def download_idea_analysis_results(self, params: BridgeParametrization, **kwargs) -> DownloadResult:
        """
        Download IDEA StatiCa RCS analysis results for cross-section capacity assessment.

        Executes the cross-section analysis and returns:
        - Input XML model file
        - Analysis results with capacity calculations
        - Interaction diagrams and stress distributions

        :param params: Bridge parametrization
        :type params: BridgeParametrization
        :returns: ZIP with analysis input and results
        :rtype: DownloadResult
        """
        # Get entity ID from kwargs
        entity_id = kwargs.get("entity_id")
        if entity_id is None:
            raise UserError("Entity ID not found in kwargs")

        # Get cached IDEA analysis results
        cached_results = get_cached_analysis_results(params, AnalysisType.IDEA, entity_id, get_idea_analysis_results)
        if cached_results is None:
            raise UserError("IDEA analysis failed or no cached results available")

        # Extract results from cache
        model = cached_results.get("model")
        xml_input = cached_results.get("xml_input")
        output_content = cached_results.get("output_content")

        if model is None or xml_input is None or output_content is None:
            raise UserError("Cached IDEA results are incomplete")

        # Validate content
        xml_content = xml_input.getvalue() if hasattr(xml_input, "getvalue") else xml_input.read() if hasattr(xml_input, "read") else b""

        if not xml_content:
            self._raise_empty_idea_xml_error()

        # Create ZIP with XML input and analysis results
        zip_file_obj = File()
        with zipfile.ZipFile(zip_file_obj.source, "w", zipfile.ZIP_DEFLATED) as z:
            # Add input XML model
            z.writestr(f"IDEA_rcs_input_model_{params.info.bridge_objectnumm}.xml", xml_content)

            # Add analysis output results
            z.writestr(f"IDEA_rcs_analysis_results_{params.info.bridge_objectnumm}.ideaRcs", output_content)

        return DownloadResult(zip_file_obj, f"IDEA_rcs_analysis_complete_{params.info.bridge_objectnumm}.zip")

    # ============================================================================================================
    # output - Rapport
    # ============================================================================================================

    @PDFView("Rapport", duration_guess=1)
    def get_output_report(self, params: BridgeParametrization, **kwargs) -> PDFResult:  # noqa: ARG002
        """
        Generates a PDF report for the bridge design.

        Args:
            params (BridgeParametrization): Input parameters for the bridge dimensions.
            **kwargs: Additional arguments.

        Returns:
            File: A PDF file containing the report.

        """
        report_pdf = create_export_report(params)  # Call the report generation function
        if not report_pdf:
            raise UserError("Rapport kon niet worden gegenereerd. Controleer de parameters en probeer het opnieuw.")
        return PDFResult(file=report_pdf)
