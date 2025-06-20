"""Module for the Bridge entity controller."""

import zipfile
from pathlib import Path  # Add Path import for SCIA template
from typing import Any, TypedDict, cast  # Import cast, Any, and TypedDict

import plotly.graph_objects as go  # Import Plotly graph objects
import trimesh
import viktor.api_v1 as api_sdk  # Import VIKTOR API SDK
from viktor.core import File, ViktorController
from viktor.errors import UserError  # Add UserError
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

# ParamsForLoadZones protocol and validate_load_zone_widths are in app.bridge.utils
from app.bridge.utils import validate_load_zone_widths
from app.common.map_utils import (
    load_and_filter_bridge_shapefile,  # Import the new function
    process_bridge_geometries,
    validate_shapefile_exists,
)

# Params for load combinations are in app.constants
from app.constants import SCIA_ZIP_README_CONTENT  # Import the SCIA ZIP readme content
from src.combinations.load_factors import create_load_combination_table
from src.common.plot_utils import (
    create_bridge_outline_traces,
)
from src.geometry.cross_section import create_cross_section_view
from src.geometry.horizontal_section import create_horizontal_section_view
from src.geometry.load_zone_geometry import LoadZoneDataRow
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
from src.integrations.scia_interface import create_bridge_scia_model

from src.report.report_functions import create_export_report  # Import the report creation function

# Import parametrization from the separate file
from .parametrization import (
    MAX_LOAD_ZONE_SEGMENT_FIELDS,  # Import the constant
    BridgeParametrization,
)


# Define TypedDict for a row from params.bridge_segments_array
class BridgeSegmentParamRow(TypedDict):
    """
    Represents the structure of a single row item from params.bridge_segments_array.
    This TypedDict is used to provide type hinting for these row objects.
    """

    bz1: float
    bz2: float
    bz3: float
    l: float  # noqa: E741 # 'l' matches the field name in BridgeParametrization (input.dimensions.array.l)
    # Add other fields like dz, dz_2, col_6, is_first_segment if accessed, with appropriate types


class BridgeController(ViktorController):
    """Controller for the individual Bridge entity."""

    label = "Brug"
    parametrization = BridgeParametrization  # type: ignore[assignment]

    def _create_bridge_segment_dimensions_from_params(self, segment_param_row: BridgeSegmentParamRow) -> BridgeSegmentDimensions:
        """Validates a segment param row and returns BridgeSegmentDimensions or raises UserError."""
        # The attribute check `hasattr` is still useful as a runtime check before typed access,
        # though MyPy will now also check based on BridgeSegmentParamRow.
        required_attrs = ["bz1", "bz2", "bz3", "l"]
        # For TypedDict, we'd ideally check presence of keys.
        # However, VIKTOR param objects are often Munch-like, so hasattr can work at runtime.
        # For Mypy, the key is using dictionary access below.
        if not all(key in segment_param_row for key in required_attrs):
            raise UserError("Een of meer brugsegmenten missen benodigde data (bz1, bz2, bz3, l) in Dimensies.")
        return BridgeSegmentDimensions(
            bz1=segment_param_row["bz1"], bz2=segment_param_row["bz2"], bz3=segment_param_row["bz3"], segment_length=segment_param_row["l"]
        )

    def _prepare_bridge_geometry_for_plotting(self, bridge_segments_params: list) -> LoadZoneGeometryData | None:
        """Helper to prepare BridgeSegmentDimensions and LoadZoneGeometryData from params."""
        if not bridge_segments_params:
            return None
        try:
            typed_bridge_dimensions = []
            for segment_param_row in bridge_segments_params:
                # Call the new helper method
                segment_data = self._create_bridge_segment_dimensions_from_params(segment_param_row)
                typed_bridge_dimensions.append(segment_data)

            if not typed_bridge_dimensions:
                return None
            return prepare_load_zone_geometry_data(typed_bridge_dimensions)
        except UserError:
            raise
        except Exception as e:
            print(f"Error preparing bridge geometry for load zones view: {e}")  # noqa: T201
            raise UserError("Fout bij voorbereiden bruggeometrie. Controleer de Dimensies tab.") from e

    def _calculate_zone_geometry_properties(
        self, load_zones_data_params: list[LoadZoneDataRow], bridge_geom_data: LoadZoneGeometryData
    ) -> list[LoadZoneDataRow]:
        """
        Calculate geometric properties for each load zone based on bridge geometry.
        This adds the missing zone_widths_per_d and y_coords_top_current_zone fields.
        """
        if not load_zones_data_params or not bridge_geom_data:
            return load_zones_data_params

        updated_zones = []
        current_y_top = bridge_geom_data.y_top_structural_edge_at_d_points.copy()

        for zone_idx, zone_data in enumerate(load_zones_data_params):
            # Create a copy of the zone data
            updated_zone = dict(zone_data)

            # Calculate zone widths for each D-point
            zone_widths = []
            for d_idx in range(bridge_geom_data.num_defined_d_points):
                d_width_field = f"d{d_idx + 1}_width"
                width_value = zone_data.get(d_width_field)
                if isinstance(width_value, (int, float)):
                    zone_widths.append(float(width_value))
                else:
                    zone_widths.append(0.0)

            # Add calculated geometric properties
            updated_zone["zone_widths_per_d"] = zone_widths
            updated_zone["y_coords_top_current_zone"] = current_y_top.copy()

            # Update current_y_top for next zone (unless it's the last zone)
            if zone_idx < len(load_zones_data_params) - 1:
                # Move the top position down by the zone width for each D-point
                for d_idx in range(bridge_geom_data.num_defined_d_points):
                    current_y_top[d_idx] -= zone_widths[d_idx]

            updated_zones.append(cast(LoadZoneDataRow, updated_zone))

        return updated_zones

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
        load_zones_data_params: list[LoadZoneDataRow] = []
        if params.load_zones_data_array:
            for row_param in params.load_zones_data_array:
                # Construct a dictionary that matches LoadZoneDataRow fields
                temp_row_data: dict[str, Any] = {
                    "zone_type": row_param.zone_type,
                    "pavement_thickness": getattr(row_param, "pavement_thickness", 0.05),  # Default 5cm
                    "pavement_material": getattr(row_param, "pavement_material", "Asfalt"),  # Default Asfalt
                }
                for i in range(1, MAX_LOAD_ZONE_SEGMENT_FIELDS + 1):
                    field_name = f"d{i}_width"
                    value = getattr(row_param, field_name, None)
                    # LoadZoneDataRow has dX_width as float | None, so store None if getattr returns None
                    temp_row_data[field_name] = value

                row_data = cast(LoadZoneDataRow, temp_row_data)
                load_zones_data_params.append(row_data)

        if not load_zones_data_params:  # No load zones defined
            fig = go.Figure()
            fig.update_layout(title_text="Belastingzones - Geen zones gedefinieerd", xaxis_visible=False, yaxis_visible=False)
            return PlotlyResult(fig.to_json())

        # 2. Prepare bridge geometric data
        bridge_geom_data = self._prepare_bridge_geometry_for_plotting(params.bridge_segments_array)
        if not bridge_geom_data:  # If preparation failed or returned None (e.g. no segments)
            fig = go.Figure()
            fig.update_layout(title_text="Belastingzones - Brugsegmenten ongeldig", xaxis_visible=False, yaxis_visible=False)
            return PlotlyResult(fig.to_json())

        # 2a. Calculate zone geometric properties using bridge geometry
        load_zones_data_params = self._calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

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
    def get_load_combinations_view(self, **kwargs) -> TableResult:  # noqa: ARG002
        """
        Display the table of load combinations for the bridge.

        :returns: TableResult containing the load combinations.
        :rtype: TableResult
        """
        combination_table = create_load_combination_table()
        return TableResult(combination_table)

    # ============================================================================================================
    # SCIA Integration
    # ============================================================================================================

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

    def download_scia_xml_files(self, params: BridgeParametrization, **kwargs) -> DownloadResult:  # noqa: ARG002
        """
        Generate and download SCIA XML input files.

        Creates the SCIA model XML and definition files that can be imported into SCIA Engineer.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :returns: ZIP file containing XML and definition files
        :rtype: DownloadResult
        """
        try:
            # Get template path
            template_path = self._get_scia_template_path()

            # Create SCIA model
            xml_file, def_file, _ = create_bridge_scia_model(params, template_path)

            # Debug: Check if files have content
            xml_content = xml_file.getvalue() if hasattr(xml_file, "getvalue") else b""
            def_content = def_file.getvalue() if hasattr(def_file, "getvalue") else b""

            if not xml_content:
                self._raise_empty_xml_error()
            if not def_content:
                self._raise_empty_def_error()

            # Create ZIP file using VIKTOR's recommended approach from documentation
            import zipfile

            # Use File object and write directly to it
            zip_file_obj = File()
            with zipfile.ZipFile(zip_file_obj.source, "w", zipfile.ZIP_DEFLATED) as z:
                # Add XML file
                z.writestr("bridge_model.xml", xml_content)
                # Add definition file
                z.writestr("viktor.xml.def", def_content)

                # Add a readme file with instructions
                readme_content = SCIA_ZIP_README_CONTENT
                z.writestr("README.txt", readme_content)

            # Generate filename with bridge info if available
            bridge_name = getattr(params.info, "bridge_name", "UnknownBridge") or "UnknownBridge"
            bridge_id = getattr(params.info, "bridge_objectnumm", "") or ""

            filename_parts = ["SCIA_Model"]
            if bridge_name and bridge_name != "UnknownBridge":
                filename_parts.append(bridge_name.replace(" ", "_"))
            if bridge_id:
                filename_parts.append(bridge_id)
            filename_parts.append("XML_Files.zip")

            filename = "_".join(filename_parts)

            # Return File object directly as shown in VIKTOR documentation
            return DownloadResult(zip_file_obj, filename)

        except Exception as e:
            raise UserError(f"Fout bij genereren SCIA XML bestanden: {e!s}")

    def download_scia_esa_model(self, params: BridgeParametrization, **kwargs) -> DownloadResult:  # noqa: ARG002
        """
        Generate and download complete SCIA model as ESA file.

        Creates a complete SCIA model file that can be directly opened in SCIA Engineer.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :returns: ESA model file for download
        :rtype: DownloadResult
        """
        # Get template path
        template_path = self._get_scia_template_path()

        # Create SCIA model and analysis
        xml_file, def_file, scia_analysis = create_bridge_scia_model(params, template_path)

        # Execute the analysis to generate the ESA model
        # Note: This requires SCIA worker to be available
        try:
            scia_analysis.execute(timeout=300)  # 5 minute timeout

            # Get the updated ESA model with our geometry
            esa_model_file = scia_analysis.get_updated_esa_model()

            # Debug: Check if ESA model file has content
            if not esa_model_file:
                self._raise_empty_esa_error()

            # Generate filename
            bridge_name = getattr(params.info, "bridge_name", "UnknownBridge") or "UnknownBridge"
            bridge_id = getattr(params.info, "bridge_objectnumm", "") or ""

            filename_parts = ["SCIA_Model"]
            if bridge_name and bridge_name != "UnknownBridge":
                filename_parts.append(bridge_name.replace(" ", "_"))
            if bridge_id:
                filename_parts.append(bridge_id)
            filename_parts.append("Model.esa")

            filename = "_".join(filename_parts)

            return DownloadResult(esa_model_file, filename)

        except Exception as worker_error:
            # If SCIA worker fails, provide helpful error message
            error_msg = (
                f"SCIA worker uitvoering gefaald: {worker_error!s}\n\n"
                "Mogelijke oorzaken:\n"
                "- SCIA worker niet beschikbaar of niet correct geïnstalleerd\n"
                "- SCIA Engineer licentie problemen\n"
                "- Template bestand incompatibel met huidige SCIA versie\n\n"
                "Probeer in plaats daarvan de XML bestanden te downloaden."
            )
            raise UserError(error_msg)

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

    # ============================================================================================================
    # IDEA StatiCa Integration
    # ============================================================================================================

    @GeometryView("IDEA RCS Dwarsdoorsnede", duration_guess=3, x_axis_to_right=True)
    def get_idea_model_preview(self, params: BridgeParametrization, **kwargs) -> GeometryResult:  # noqa: ARG002
        """
        Generate 3D preview of IDEA StatiCa RCS cross-section model.

        Shows the cross-section as viewed from the front, with:
        - Concrete section as gray rectangular block
        - Reinforcement bars as detailed cylinders
        - Proper proportions for cross-section analysis

        :param params: Bridge parametrization
        :type params: BridgeParametrization
        :returns: 3D visualization of the cross-section for RCS analysis
        :rtype: GeometryResult
        """
        try:
            # Extract bridge segments for cross-section analysis
            bridge_segments_list = []
            if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
                for segment in params.bridge_segments_array:
                    segment_dict = {
                        "bz1": getattr(segment, "bz1", 0),
                        "bz2": getattr(segment, "bz2", 0),
                        "bz3": getattr(segment, "bz3", 0),
                        "dz": getattr(segment, "dz", 0.5),
                        "dz_2": getattr(segment, "dz_2", 0.5),
                        "l": getattr(segment, "l", 0),
                    }
                    bridge_segments_list.append(segment_dict)

            if not bridge_segments_list:
                self._raise_no_idea_segments_error()

            # Extract cross-section from first segment
            from src.integrations.idea_interface import extract_cross_section_from_params

            # Use materials from params.info when available
            concrete_material = getattr(params.info, "concrete_strength_class", None) or "C30/37"
            reinforcement_material = getattr(params.info, "steel_quality_reinforcement", None) or "B500B"

            cross_section_data = extract_cross_section_from_params(bridge_segments_list, concrete_material, reinforcement_material)

            # Create scene
            scene = trimesh.Scene()

            # Create concrete plate - horizontal orientation for bridge deck cross-section
            # For a bridge plate, thickness is the height, width is the width
            plate_thickness = cross_section_data.height
            plate_width = cross_section_data.width
            plate_length = max(2.0, plate_width * 0.3)  # Show some depth for 3D visualization

            concrete_plate = trimesh.creation.box(extents=[plate_width, plate_length, plate_thickness])
            # Light concrete gray
            concrete_plate.visual.face_colors = [180, 180, 180, 255]
            scene.add_geometry(concrete_plate, node_name="ConcretePlate")

            # Create reinforcement visualization
            from src.integrations.idea_interface import create_reinforcement_layout

            reinforcement = create_reinforcement_layout(cross_section_data)

            # Add reinforcement bars as cylinders running in length direction (Y-axis)
            bar_length = plate_length * 1.1  # Slightly longer than plate for visibility

            # Top reinforcement bars (near top surface of plate)
            top_z_position = plate_thickness / 2 - 0.055  # 55mm from top
            for i, (x, y, diameter) in enumerate(reinforcement.main_bars_top):
                # Create cylinder for reinforcement bar running in Y direction
                bar_cylinder = trimesh.creation.cylinder(
                    radius=diameter / 2000,  # Convert mm to m
                    height=bar_length,
                    sections=8,
                )
                # Rotate to align with Y-axis (length direction)
                bar_cylinder.apply_transform(trimesh.transformations.rotation_matrix(angle=3.14159 / 2, direction=[1, 0, 0]))
                # Position the bar (x from reinforcement, y=0 center, z=top layer)
                bar_cylinder.apply_translation([x - plate_width / 2, 0, top_z_position])
                # Dark steel color
                bar_cylinder.visual.face_colors = [101, 67, 33, 255]  # Dark brown steel
                scene.add_geometry(bar_cylinder, node_name=f"TopReinforcement_{i}")

            # Bottom reinforcement bars (near bottom surface of plate)
            bottom_z_position = -plate_thickness / 2 + 0.055  # 55mm from bottom
            for i, (x, y, diameter) in enumerate(reinforcement.main_bars_bottom):
                # Create cylinder for reinforcement bar running in Y direction
                bar_cylinder = trimesh.creation.cylinder(
                    radius=diameter / 2000,  # Convert mm to m
                    height=bar_length,
                    sections=8,
                )
                # Rotate to align with Y-axis (length direction)
                bar_cylinder.apply_transform(trimesh.transformations.rotation_matrix(angle=3.14159 / 2, direction=[1, 0, 0]))
                # Position the bar (x from reinforcement, y=0 center, z=bottom layer)
                bar_cylinder.apply_translation([x - plate_width / 2, 0, bottom_z_position])
                # Dark steel color
                bar_cylinder.visual.face_colors = [101, 67, 33, 255]  # Dark brown steel
                scene.add_geometry(bar_cylinder, node_name=f"BottomReinforcement_{i}")

            # Add coordinate system indicator for orientation
            # Small coordinate arrows to show orientation
            arrow_scale = min(plate_width, plate_thickness) * 0.1

            # X-axis arrow (red) - width direction
            x_arrow = trimesh.creation.cylinder(radius=0.01, height=arrow_scale)
            x_arrow.apply_transform(trimesh.transformations.rotation_matrix(angle=3.14159 / 2, direction=[0, 0, 1]))
            x_arrow.apply_translation([plate_width / 2 + arrow_scale / 2, -plate_length / 2 - 0.1, -plate_thickness / 2 - 0.1])
            x_arrow.visual.face_colors = [255, 0, 0, 255]  # Red for X
            scene.add_geometry(x_arrow, node_name="X_Axis")

            # Z-axis arrow (blue) - thickness/height direction
            z_arrow = trimesh.creation.cylinder(radius=0.01, height=arrow_scale)
            z_arrow.apply_translation([plate_width / 2 + 0.1, -plate_length / 2 - 0.1, -plate_thickness / 2 + arrow_scale / 2])
            z_arrow.visual.face_colors = [0, 0, 255, 255]  # Blue for Z
            scene.add_geometry(z_arrow, node_name="Z_Axis")

            # Export as GLTF
            geometry_file = File()
            with geometry_file.open_binary() as w:
                w.write(trimesh.exchange.gltf.export_glb(scene))

            return GeometryResult(geometry_file, geometry_type="gltf")

        except Exception as e:
            raise UserError(f"IDEA RCS dwarsdoorsnede preview gefaald: {e!s}")

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
            # Extract bridge segments for cross-section analysis
            bridge_segments_list = []
            if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
                for segment in params.bridge_segments_array:
                    segment_dict = {
                        "bz1": getattr(segment, "bz1", 0),
                        "bz2": getattr(segment, "bz2", 0),
                        "bz3": getattr(segment, "bz3", 0),
                        "dz": getattr(segment, "dz", 0.5),
                        "dz_2": getattr(segment, "dz_2", 0.5),
                        "l": getattr(segment, "l", 0),
                    }
                    bridge_segments_list.append(segment_dict)

            if not bridge_segments_list:
                self._raise_no_idea_analysis_segments_error()

            # Create IDEA RCS cross-section model with materials from params.info
            from src.integrations.idea_interface import create_bridge_idea_model

            try:
                # Generate XML input file
                model = create_bridge_idea_model(bridge_segments_list)
                xml_file = model.generate_xml_input()

                # Validate content
                xml_content = xml_file.getvalue() if hasattr(xml_file, "getvalue") else xml_file.read() if hasattr(xml_file, "read") else b""

                if not xml_content:
                    self._raise_empty_idea_xml_error()

                return DownloadResult(xml_content, "idea_rcs_cross_section.xml")

            except Exception as e:
                raise UserError(f"IDEA RCS XML generatie gefaald: {e!s}")

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
        try:
            # Extract bridge segments for cross-section analysis
            bridge_segments_list = []
            if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
                for segment in params.bridge_segments_array:
                    segment_dict = {
                        "bz1": getattr(segment, "bz1", 0),
                        "bz2": getattr(segment, "bz2", 0),
                        "bz3": getattr(segment, "bz3", 0),
                        "dz": getattr(segment, "dz", 0.5),
                        "dz_2": getattr(segment, "dz_2", 0.5),
                        "l": getattr(segment, "l", 0),
                    }
                    bridge_segments_list.append(segment_dict)

            if not bridge_segments_list:
                self._raise_no_idea_analysis_segments_error()

            # Create IDEA RCS cross-section model with materials from params.info
            from src.integrations.idea_interface import create_bridge_idea_model, run_idea_analysis

            try:
                # Generate XML input file
                model = create_bridge_idea_model(bridge_segments_list)
                xml_file = model.generate_xml_input()

                # Validate content
                xml_content = xml_file.getvalue() if hasattr(xml_file, "getvalue") else xml_file.read() if hasattr(xml_file, "read") else b""

                if not xml_content:
                    self._raise_empty_idea_xml_error()

                # Run cross-section analysis
                output_file = run_idea_analysis(model, timeout=120)

                # Create ZIP with XML input and analysis results
                zip_file_obj = File()
                with zipfile.ZipFile(zip_file_obj.source, "w", zipfile.ZIP_DEFLATED) as z:
                    # Add input XML model
                    z.writestr("rcs_input_model.xml", xml_content)

                    # Add analysis output results
                    if hasattr(output_file, "getvalue"):
                        output_content = output_file.getvalue()
                        z.writestr("rcs_analysis_results.xml", output_content)
                    elif hasattr(output_file, "source"):
                        # If it's a File object
                        with output_file.open_binary() as f:
                            z.writestr("rcs_analysis_results.xml", f.read())

                return DownloadResult(zip_file_obj, "idea_rcs_analysis_complete.zip")

            except Exception as e:
                error_msg = (
                    f"IDEA RCS analyse uitvoering gefaald: {e!s}\n\n"
                    "Mogelijke oorzaken:\n"
                    "- IDEA RCS worker niet beschikbaar of niet correct geïnstalleerd\n"
                    "- IDEA StatiCa licentie problemen of expired\n"
                    "- Cross-section model configuratie ongeldig\n"
                    "- Timeout tijdens capaciteitsberekeningen\n\n"
                    "💡 Suggesties:\n"
                    "- Controleer IDEA StatiCa installatie en licentie\n"
                    "- Probeer in plaats daarvan alleen de XML input te downloaden\n"
                    "- Verhoog timeout voor complexe doorsneden\n"
                    "- Verificeer brugsegment dimensies (bz1, bz2, bz3, dz, dz_2)"
                )
                raise UserError(error_msg)

        except Exception as e:
            error_msg = (
                f"IDEA RCS analyse uitvoering gefaald: {e!s}\n\n"
                "Mogelijke oorzaken:\n"
                "- IDEA RCS worker niet beschikbaar of niet correct geïnstalleerd\n"
                "- IDEA StatiCa licentie problemen of expired\n"
                "- Cross-section model configuratie ongeldig\n"
                "- Timeout tijdens capaciteitsberekeningen\n\n"
                "💡 Suggesties:\n"
                "- Controleer IDEA StatiCa installatie en licentie\n"
                "- Probeer in plaats daarvan alleen de XML input te downloaden\n"
                "- Verhoog timeout voor complexe doorsneden\n"
                "- Verificeer brugsegment dimensies (bz1, bz2, bz3, dz, dz_2)"
            )
            raise UserError(error_msg)


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