"""Module for the Bridge entity controller."""

import zipfile
from pathlib import Path  # Add Path import for SCIA template

import plotly.graph_objects as go  # Import Plotly graph objects
import trimesh

import viktor.api_v1 as api_sdk  # Import VIKTOR API SDK
import viktor.errors  # Import for specific error types
from app.bridge.scia_model_builder import generate_bridge_xml_files, setup_bridge_analysis

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
from src.integrations.idea_interface import _get_unique_matching_zone_keys, create_bridge_idea_model, run_idea_analysis
from src.report.report_functions import create_export_report  # Import the report creation function
from viktor.core import File, ViktorController
from viktor.errors import UserError  # Add UserError
from viktor.external import idea_rcs, scia
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
                        print(f"Warning: Malformed bridge segment data in get_top_view: {segment_param_row}")  # noqa: T201
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

    @TableView("SCIA Analyse Resultaten", duration_guess=3)
    def get_scia_results_table(self, params: BridgeParametrization, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Display SCIA analysis results in a table format.

        This is a proof of concept showing how SCIA results can be presented
        in a structured table view for colleagues.

        :param params: Bridge parametrization object
        :returns: TableResult containing SCIA analysis results
        """
        if not params.bridge_segments_array:
            return TableResult(
                [["Geen brugsegmenten gedefinieerd", "N/A", "N/A", "N/A"]], column_headers=["Status", "Displacements", "Internal Forces", "Reactions"]
            )

        try:
            # Get the template path
            template_path = self._get_scia_template_path()

            # Import the analysis function
            from app.bridge.scia_model_builder import run_scia_analysis

            # Run SCIA analysis to get results
            analysis = run_scia_analysis(params, template_path)

            # Extract results using the builder
            from app.bridge.scia_model_builder import ViktorSciaModelBuilder

            builder = ViktorSciaModelBuilder()
            results = builder.extract_analysis_results(analysis)

            # Debug: Check if we have XML output
            xml_output_file = analysis.get_xml_output_file()
            xml_content_size = 0
            if xml_output_file:
                if hasattr(xml_output_file, "getvalue"):
                    xml_content_size = len(xml_output_file.getvalue())
                elif hasattr(xml_output_file, "read"):
                    xml_output_file.seek(0)
                    xml_content_size = len(xml_output_file.read())
                    xml_output_file.seek(0)

            # Prepare table data
            table_data = []

            # Analysis status
            analysis_status = results.get("analysis_status", {})
            status = analysis_status.get("status", "Unknown")
            has_results = analysis_status.get("has_results", False)

            # Add debug information
            table_data.append(["🔍 Debug Info", f"XML Size: {xml_content_size} bytes", f"Analysis Status: {status}", f"Has Results: {has_results}"])

            # Add explanation for colleagues
            table_data.append(
                ["💡 Explanation", "Tables found but may be empty", "Check if SCIA analysis produced results", "Verify load cases and combinations"]
            )
            
            # Add SCIA model structure information from XML
            xml_parsing = results.get("xml_parsing", {})
            if xml_parsing:
                # Show result classes found in XML
                result_class_tables = []
                for table_name in xml_parsing.get("available_tables", []):
                    if "Resultaatklasses" in table_name:
                        result_class_tables.append(table_name)
                
                if result_class_tables:
                    table_data.append(["🎯 Result Classes (XML)", f"Found: {len(result_class_tables)}", "Available", "Created"])
                    for i, class_name in enumerate(result_class_tables):
                        table_data.append([f"  Class {i+1}", class_name, "Active", "Ready"])
                else:
                    table_data.append(["🎯 Result Classes", "None found in XML", "Check SCIA template", "N/A"])
                
                # Show load combinations found in XML
                load_combo_tables = []
                for table_name in xml_parsing.get("available_tables", []):
                    if "Combinatie" in table_name or "combination" in table_name.lower():
                        load_combo_tables.append(table_name)
                
                if load_combo_tables:
                    table_data.append(["🔗 Load Combinations (XML)", f"Found: {len(load_combo_tables)}", "Available", "Created"])
                    for i, combo_name in enumerate(load_combo_tables):
                        table_data.append([f"  Combo {i+1}", combo_name, "Active", "Ready"])
                else:
                    table_data.append(["🔗 Load Combinations", "None found in XML", "Check SCIA template", "N/A"])
                
                # Show specific combinations from result classes
                table_data.append(["📊 SCIA Template Combos", "From Result Classes", "Status", "Type"])
                table_data.append(["  Ultimate combination", "ULS", "Active", "Default"])
                table_data.append(["  Serviceability combination", "SLS", "Active", "Default"])
                table_data.append(["  UGT Combinatie", "ULS", "Active", "Default"])
                table_data.append(["  BGT-combinatie", "SLS", "Active", "Default"])
                table_data.append(["  Nonlinear combinations", "Nonlinear", "Active", "Default"])

            # Get individual result types
            displacements = results.get("displacements", {})
            internal_forces = results.get("internal_forces", {})
            reactions = results.get("reactions", {})

            # Create status row
            table_data.append(
                [
                    f"Analysis: {status}",
                    f"Displacements: {displacements.get('status', 'N/A')}",
                    f"Forces: {internal_forces.get('status', 'N/A')}",
                    f"Reactions: {reactions.get('status', 'N/A')}",
                ]
            )

            # Add result details if available
            if has_results:
                # Add displacement details
                if displacements.get("status") == "success":
                    table_data.append(
                        [
                            "✅ Success",
                            f"Table: {displacements.get('table_name', 'Unknown')}",
                            f"Data points: {len(displacements.get('data', {}))}",
                            "Available",
                        ]
                    )
                else:
                    table_data.append(["❌ Failed", f"Error: {displacements.get('message', 'Unknown error')}", "N/A", "N/A"])

                # Add internal forces details
                if internal_forces.get("status") == "success":
                    table_data.append(
                        [
                            "✅ Success",
                            "Available",
                            f"Table: {internal_forces.get('table_name', 'Unknown')}",
                            f"Data points: {len(internal_forces.get('data', {}))}",
                        ]
                    )
                else:
                    table_data.append(["❌ Failed", "N/A", f"Error: {internal_forces.get('message', 'Unknown error')}", "N/A"])

                # Add reaction details
                if reactions.get("status") == "success":
                    table_data.append(["✅ Success", "Available", "Available", f"Table: {reactions.get('table_name', 'Unknown')}"])
                else:
                    table_data.append(["❌ Failed", "N/A", "N/A", f"Error: {reactions.get('message', 'Unknown error')}"])

                # Add XML parsing summary
                xml_parsing = results.get("xml_parsing", {})
                if xml_parsing:
                    available_tables = xml_parsing.get("available_tables", [])
                    table_details = xml_parsing.get("table_details", [])
                    total_found = xml_parsing.get("total_tables_found", 0)
                    total_attempted = xml_parsing.get("total_tables_attempted", 0)

                    table_data.append(
                        ["📊 XML Summary", f"Found: {total_found}", f"Attempted: {total_attempted}", f"Tables: {len(available_tables)}"]
                    )

                    # Show detailed table information
                    if table_details:
                        for i, detail in enumerate(table_details):
                            status_icon = "✅" if detail.get("has_data") else "⚠️"
                            data_info = f"Data: {detail.get('data_rows', 0)} rows"
                            object_info = f"Objects: {detail.get('objects', 0)}"

                            table_data.append([f"{status_icon} Table {i + 1}", detail.get("name", "Unknown"), data_info, object_info])
                    elif available_tables:
                        # Fallback to simple table names if details not available
                        for i, table_name in enumerate(available_tables):
                            table_data.append([f"📋 Table {i + 1}", table_name, "Available", "Parsed"])
                    else:
                        table_data.append(["⚠️ No Tables Found", "XML parsing failed", "Check XML structure", "Verify SCIA output"])
            else:
                table_data.append(["⚠️ No Results", "Analysis completed but no results available", "Check SCIA output format", "Verify table names"])

            return TableResult(table_data, column_headers=["Status", "Displacements", "Internal Forces", "Reactions"])

        except Exception as e:
            # Return error information in table format
            error_data = [
                ["❌ Analysis Failed", f"Error: {e!s}", "N/A", "N/A"],
                ["💡 Suggestion", "Check bridge parameters", "Verify SCIA template", "Review error logs"],
            ]
            return TableResult(error_data, column_headers=["Status", "Displacements", "Internal Forces", "Reactions"])



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

    def download_scia_esa_model(self, params: BridgeParametrization, **kwargs) -> DownloadResult:  # noqa: ARG002
        """Generate and download a complete SCIA ESA model file."""
        if not params.bridge_segments_array:
            self._raise_no_bridge_segments_error()

        try:
            template_path = self._get_scia_template_path()
            xml_file, def_file, esa_template = setup_bridge_analysis(params, template_path)

            # Validate generated files before analysis
            if not xml_file.getvalue():
                self._raise_empty_xml_error()
            if not def_file.getvalue():
                self._raise_empty_def_error()

            # Create SciaAnalysis object with positional arguments (correct VIKTOR SDK pattern)
            scia_analysis = scia.SciaAnalysis(xml_file, def_file, esa_template)

            # Execute analysis and get the ESA file
            scia_analysis.execute(timeout=600)  # 10-minute timeout
            esa_file = scia_analysis.get_updated_esa_model(as_file=True)

            if not esa_file:
                self._raise_empty_esa_error()

            return DownloadResult(esa_file, f"SCIA_model_{params.info.bridge_objectnumm}.esa")

        except ImportError as e:
            raise UserError(f"VIKTOR SCIA module niet beschikbaar: {e!s}\n\nDeze functie vereist de VIKTOR SDK met SCIA integratie.")
        except viktor.errors.LicenseError as e:
            raise UserError(
                f"SCIA Engineer licentie fout: {e!s}\n\nControleer uw SCIA Engineer licentie en zorg ervoor dat deze correct is geconfigureerd."
            )
        except viktor.errors.ExecutionError as e:
            raise UserError(
                f"SCIA analyse uitvoering gefaald: {e!s}\n\n"
                "De externe SCIA analyse is niet succesvol voltooid. "
                "Controleer of SCIA Engineer correct is geïnstalleerd en toegankelijk is."
            )
        except viktor.errors.ModelError as e:
            raise UserError(
                f"SCIA model fout: {e!s}\n\n"
                "Er was een probleem met de SCIA model generatie of analyse. "
                "Controleer uw brug parameters en probeer opnieuw."
            )
        except FileNotFoundError as e:
            raise UserError(
                f"Template bestand niet gevonden: {e!s}\n\n"
                "Het SCIA template bestand ontbreekt of is niet toegankelijk. "
                "Controleer de template configuratie."
            )
        except PermissionError as e:
            raise UserError(
                f"Toestemmings fout: {e!s}\n\n"
                "Onvoldoende toestemmingen om SCIA bestanden te openen of de analyse uit te voeren. "
                "Controleer bestandsrechten en gebruikers toegangsrechten."
            )
        except Exception as e:
            raise UserError(f"Onverwachte fout tijdens SCIA analyse: {e!s}\n\nProbeer in plaats daarvan de XML-bestanden te downloaden.")

    def download_scia_output_xml(self, params: BridgeParametrization, **kwargs) -> DownloadResult:  # noqa: ARG002
        """Download the SCIA output XML file for investigation."""
        if not params.bridge_segments_array:
            self._raise_no_bridge_segments_error()

        try:
            # Get the template path
            template_path = self._get_scia_template_path()

            # Import the analysis function
            from app.bridge.scia_model_builder import run_scia_analysis

            # Get a fresh copy of the XML output file directly from the analysis
            # The one in results might have been consumed by parsing functions

            # Run the analysis again to get a fresh XML output file
            template_path = self._get_scia_template_path()
            analysis = run_scia_analysis(params, template_path)
            fresh_xml_output_file = analysis.get_xml_output_file()

            if not fresh_xml_output_file:
                raise UserError("No XML output file available from SCIA analysis")

            # Create a filename with bridge identifier
            bridge_id = params.info.bridge_objectnumm or "unknown_bridge"
            filename = f"scia_output_{bridge_id}.xml"

            # Create a File object and write the XML content to it
            xml_file = File()

            # Get the XML content as bytes
            if hasattr(fresh_xml_output_file, "read"):
                # It's a BytesIO-like object
                xml_content = fresh_xml_output_file.read()
            elif hasattr(fresh_xml_output_file, "getvalue"):
                # It's a BytesIO object
                xml_content = fresh_xml_output_file.getvalue()
            elif isinstance(fresh_xml_output_file, str):
                # It's a string, encode it to bytes
                xml_content = fresh_xml_output_file.encode("utf-8")
            elif isinstance(fresh_xml_output_file, bytes):
                # It's already bytes
                xml_content = fresh_xml_output_file
            else:
                raise UserError(f"Unexpected type for fresh_xml_output_file: {type(fresh_xml_output_file)}")

            # Write the content to the File object using the correct method
            with xml_file.open_binary() as f:
                f.write(xml_content)

            return DownloadResult(xml_file, filename)

        except ImportError as e:
            raise UserError(f"VIKTOR SCIA module not available: {e!s}\n\nThis function requires the VIKTOR SDK with SCIA integration.")
        except viktor.errors.LicenseError as e:
            raise UserError(f"SCIA Engineer license error: {e!s}\n\nPlease check your SCIA Engineer license and ensure it's properly configured.")
        except viktor.errors.ExecutionError as e:
            raise UserError(
                f"SCIA analysis execution failed: {e!s}\n\n"
                "The external SCIA analysis did not complete successfully. "
                "Check if SCIA Engineer is properly installed and accessible."
            )
        except viktor.errors.ModelError as e:
            raise UserError(
                f"SCIA model error: {e!s}\n\n"
                "There was an issue with the SCIA model generation or analysis. "
                "Check your bridge parameters and try again."
            )
        except viktor.errors.SciaParsingError as e:
            raise UserError(
                f"SCIA output parsing error: {e!s}\n\n"
                "The SCIA analysis completed but the output could not be parsed. "
                "This might indicate an issue with the SCIA output format."
            )
        except FileNotFoundError as e:
            raise UserError(
                f"Template file not found: {e!s}\n\nThe SCIA template file is missing or not accessible. Please check the template configuration."
            )
        except PermissionError as e:
            raise UserError(
                f"Permission error: {e!s}\n\n"
                "Insufficient permissions to access SCIA files or execute the analysis. "
                "Check file permissions and user access rights."
            )
        except Exception as e:
            # Catch any other unexpected errors
            raise UserError(
                f"Unexpected error during SCIA analysis: {e!s}\n\n"
                "An unexpected error occurred. Please try again or contact support if the issue persists."
            )

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

    @TableView("IDEA RCS resultaten", duration_guess=4)
    def get_view_idea_rcs_results(self, params: BridgeParametrization, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Toon een tabel met resultaten van de IDEA RCS analyse.

        :param params: Bridge parametrization
        :type params: BridgeParametrization
        :returns: TableResult met unieke zone keys
        :rtype: TableResult
        """
        # Generate XML input file
        model = create_bridge_idea_model(params)
        xml_input = model.generate_xml_input()

        analysis = idea_rcs.IdeaRcsAnalysis(xml_input, return_rcs_file=True)
        analysis.execute(120)

        idea_output_xml_bytes = analysis.get_output_file(as_file=True)

        # Obtain the results for specific or all section(s).
        with idea_output_xml_bytes.open_binary() as f:
            parser = idea_rcs.RcsOutputFileParser(f)

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

    def download_idea_xml_file(self, params: BridgeParametrization, **kwargs) -> DownloadResult:  # noqa: ARG002
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
            # Generate XML input file
            model = create_bridge_idea_model(params)
            xml_file = model.generate_xml_input()

            # Validate content
            xml_content = xml_file.getvalue() if hasattr(xml_file, "getvalue") else xml_file.read() if hasattr(xml_file, "read") else b""

            if not xml_content:
                self._raise_empty_idea_xml_error()

            return DownloadResult(xml_content, f"IDEA_rcs_{params.info.bridge_objectnumm}.xml")

        except Exception as e:
            raise UserError(f"IDEA RCS XML generatie gefaald: {e!s}")

    def download_idea_analysis_results(self, params: BridgeParametrization, **kwargs) -> DownloadResult:  # noqa: ARG002
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
        # Generate XML input file
        model = create_bridge_idea_model(params)
        xml_file = model.generate_xml_input()

        # Validate content
        xml_content = xml_file.getvalue() if hasattr(xml_file, "getvalue") else xml_file.read() if hasattr(xml_file, "read") else b""

        if not xml_content:
            self._raise_empty_idea_xml_error()

        # Run cross-section analysis
        output_file = run_idea_analysis(model, timeout=240)

        # Create ZIP with XML input and analysis results
        zip_file_obj = File()
        with zipfile.ZipFile(zip_file_obj.source, "w", zipfile.ZIP_DEFLATED) as z:
            # Add input XML model
            z.writestr(f"IDEA_rcs_input_model_{params.info.bridge_objectnumm}.xml", xml_content)

            # Add analysis output results
            if hasattr(output_file, "getvalue"):
                output_content = output_file.getvalue()
                z.writestr(f"IDEA_rcs_analysis_results_{params.info.bridge_objectnumm}.ideaRcs", output_content)
            elif hasattr(output_file, "source"):
                # If it's a File object
                with output_file.open_binary() as f:
                    z.writestr(f"IDEA_rcs_analysis_results_{params.info.bridge_objectnumm}.ideaRcs", f.read())

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
