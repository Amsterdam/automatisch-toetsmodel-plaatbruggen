"""
Geometry visualization component for BridgeController.

This component provides all geometry-related views including
3D models, 2D sections, and load zone visualizations.
"""

import plotly.graph_objects as go
import trimesh
from viktor.core import File
from viktor.views import GeometryResult, GeometryView, PlotlyResult, PlotlyView

from app.bridge.parametrization import BridgeParametrization
from app.bridge.utils import _validate_first_and_last_supports, validate_load_zone_widths, validate_reinforcement_zone_selections
from src.common.plot_utils import create_bridge_outline_traces
from src.data_models.plotting_models import BridgeBaseGeometry, PlotPresentationDetails, ZoneStylingDefaults
from src.geometry.cross_section import create_cross_section_view
from src.geometry.horizontal_section import create_horizontal_section_view
from src.geometry.load_zone_geometry import calculate_zone_geometry_properties, get_bridge_geom_data, get_load_zones_data_from_params
from src.geometry.load_zone_plot import DEFAULT_PLOTLY_COLORS, DEFAULT_ZONE_APPEARANCE_MAP, build_load_zones_figure
from src.geometry.longitudinal_section import create_longitudinal_section
from src.geometry.model_creator import (
    BridgeSegmentDimensions,
    LoadZoneGeometryData,
    create_2d_top_view,
    create_3d_model,
    prepare_load_zone_geometry_data,
)
from src.geometry.top_view_plot import build_top_view_figure


class GeometryViews:
    """
    Component providing geometry visualization views.

    Contains methods for:
    - 3D model visualization
    - 2D top view with validation
    - Horizontal, longitudinal, and cross-sections
    - Load zone visualization
    """

    @GeometryView("3D Model", duration_guess=1, x_axis_to_right=False)
    def get_3d_view(self, params: BridgeParametrization, **kwargs) -> GeometryResult:  # noqa: ARG002
        """
        Generate a 3D representation of the bridge deck.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: GeometryResult with 3D model
        :rtype: GeometryResult
        """
        validate_reinforcement_zone_selections(params)
        _validate_first_and_last_supports(params)

        combined_scene = create_3d_model(params, section_planes=True)
        geometry = File()
        with geometry.open_binary() as w:
            w.write(trimesh.exchange.gltf.export_glb(combined_scene))
        return GeometryResult(geometry, geometry_type="gltf")

    @PlotlyView("Bovenaanzicht", duration_guess=1)
    def get_top_view(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generate a 2D top view of the bridge deck with dimensions.

        Also performs validation of load zone widths against bridge dimensions.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: PlotlyResult with 2D top view
        :rtype: PlotlyResult
        """
        validate_reinforcement_zone_selections(params)
        _validate_first_and_last_supports(params)

        # 1. Prepare bridge geometry data (needed for validation)
        bridge_segments_params = params.bridge_segments_array
        bridge_geom_data: LoadZoneGeometryData | None = None

        if bridge_segments_params:
            try:
                typed_bridge_dimensions = []
                for segment_param_row in bridge_segments_params:
                    if not all(hasattr(segment_param_row, attr) for attr in ["bz1", "bz2", "bz3", "l"]):
                        continue
                    typed_bridge_dimensions.append(
                        BridgeSegmentDimensions(
                            bz1=segment_param_row.bz1, bz2=segment_param_row.bz2, bz3=segment_param_row.bz3, segment_length=segment_param_row.l
                        )
                    )
                if typed_bridge_dimensions:
                    bridge_geom_data = prepare_load_zone_geometry_data(typed_bridge_dimensions)
            except Exception as e:
                print(f"Error preparing bridge geometry for validation in get_top_view: {e}")  # noqa: T201

        # 2. Perform validation if possible
        validation_messages: list[str] = []
        if bridge_geom_data and hasattr(params, "load_zones_data_array") and params.load_zones_data_array:
            validation_messages = validate_load_zone_widths(params=params, geometry_data=bridge_geom_data)
        elif not bridge_segments_params or not bridge_geom_data:
            validation_messages = ["Brugsegmenten data ontbreekt of is ongeldig, validatie van belastingzones niet volledig uitgevoerd."]

        # 3. Generate top view plot data
        top_view_data = create_2d_top_view(params)

        # 4. Build the figure
        fig = build_top_view_figure(top_view_geometric_data=top_view_data, validation_messages=validation_messages)

        return PlotlyResult(fig.to_json())

    @PlotlyView("Horizontale doorsnede", duration_guess=1)
    def get_2d_horizontal_section(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generate a 2D horizontal section view of the bridge using Plotly.

        Creates a 2D representation by:
        1. Creating a 3D model of the bridge
        2. Slicing it with a horizontal plane at the specified height
        3. Converting the section into a 2D plot showing length (x) vs width (y)

        :param params: Input parameters for the bridge dimensions
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: A 2D representation of the horizontal section
        :rtype: PlotlyResult
        """
        _validate_first_and_last_supports(params)
        fig = create_horizontal_section_view(params, params.input.dimensions.horizontal_section_loc)
        return PlotlyResult(fig.to_json())

    @PlotlyView("Langsdoorsnede", duration_guess=1)
    def get_2d_longitudinal_section(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generate a 2D longitudinal section view of the bridge using Plotly.

        Creates a 2D representation by:
        1. Creating a 3D model of the bridge
        2. Slicing it with a vertical plane parallel to the x-z plane
        3. Converting the section into a 2D plot showing length (x) vs height (z)

        :param params: Input parameters for the bridge dimensions
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: A 2D representation of the longitudinal section
        :rtype: PlotlyResult
        """
        _validate_first_and_last_supports(params)
        fig = create_longitudinal_section(params, params.input.dimensions.longitudinal_section_loc)
        return PlotlyResult(fig.to_json())

    @PlotlyView("Dwarsdoorsnede", duration_guess=1)
    def get_2d_cross_section(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generate a 2D cross-section view of the bridge using Plotly.

        Creates a 2D representation by:
        1. Creating a 3D model of the bridge
        2. Slicing it with a vertical plane parallel to the y-z plane
        3. Converting the section into a 2D plot showing width (y) vs height (z)

        :param params: Input parameters for the bridge dimensions
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: A 2D representation of the cross-section
        :rtype: PlotlyResult
        """
        _validate_first_and_last_supports(params)
        fig = create_cross_section_view(params, params.input.dimensions.cross_section_loc)
        return PlotlyResult(fig.to_json())

    @PlotlyView("Belastingzones", duration_guess=1)
    def get_load_zones_view(self, params: BridgeParametrization, **kwargs) -> PlotlyResult:  # noqa: ARG002
        """
        Generate a 2D view of the load zones on the bridge deck.

        Uses the build_load_zones_figure from the src layer.

        :param params: Bridge parametrization object
        :type params: BridgeParametrization
        :param kwargs: Additional arguments
        :returns: PlotlyResult with load zones visualization
        :rtype: PlotlyResult
        """
        _validate_first_and_last_supports(params)

        # 1. Prepare LoadZoneDataRow list from params
        load_zones_data_params = get_load_zones_data_from_params(params)

        # 2. Prepare bridge geometric data
        bridge_geom_data = get_bridge_geom_data(params)

        # 2a. Calculate zone geometric properties using bridge geometry
        load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

        if not load_zones_data_params:
            fig = go.Figure()
            fig.update_layout(title_text="Belastingzones - Geen zones gedefinieerd", xaxis_visible=False, yaxis_visible=False)
            return PlotlyResult(fig.to_json())

        if not bridge_geom_data:
            fig = go.Figure()
            fig.update_layout(title_text="Belastingzones - Brugsegmenten ongeldig", xaxis_visible=False, yaxis_visible=False)
            return PlotlyResult(fig.to_json())

        # 3. Get validation messages
        validation_messages: list[str] = []
        if hasattr(params, "load_zones_data_array") and params.load_zones_data_array:
            validation_messages = validate_load_zone_widths(params=params, geometry_data=bridge_geom_data)

        # 4. Prepare base_traces for the bridge background
        top_view_render_data = create_2d_top_view(params)

        base_traces = []
        bridge_outline_data = top_view_render_data.get("bridge_lines", [])
        if bridge_outline_data:
            base_traces.extend(create_bridge_outline_traces(bridge_outline_data))

        # 5. Call build_load_zones_figure
        bridge_geom_arg = BridgeBaseGeometry(
            x_coords_d_points=bridge_geom_data.x_coords_d_points,
            y_coords_bridge_top_edge=bridge_geom_data.y_top_structural_edge_at_d_points,
            y_coords_bridge_bottom_edge=[[y_bottom, y_bottom] for y_bottom in bridge_geom_data.y_bridge_bottom_at_d_points],
            num_defined_d_points=bridge_geom_data.num_defined_d_points,
        )
        styling_defaults_arg = ZoneStylingDefaults(
            zone_appearance_map=DEFAULT_ZONE_APPEARANCE_MAP,
            default_plotly_colors=DEFAULT_PLOTLY_COLORS,
        )

        presentation_details_arg = PlotPresentationDetails(
            base_traces=base_traces,
            validation_messages=validation_messages,
            figure_title="Belastingzones",
        )

        fig = build_load_zones_figure(
            load_zones_data_params=load_zones_data_params,
            bridge_geom=bridge_geom_arg,
            styling_defaults=styling_defaults_arg,
            presentation_details=presentation_details_arg,
        )

        return PlotlyResult(fig.to_json())
