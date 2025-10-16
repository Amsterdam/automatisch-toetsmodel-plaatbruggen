"""
Controller for the individual Bridge entity.

This module serves as the main entry point for VIKTOR to discover the BridgeController.
The actual implementation uses a component-based architecture for better organization and
maintainability, with components located in the app/bridge/bridgeController/ subfolder.

Components:
- InfoViews: Bridge information and location views
- GeometryViews: 3D models and 2D section views
- SciaIntegration: SCIA Engineer analysis integration
- IdeaIntegration: IDEA StatiCa RCS integration
- ReportViews: PDF report generation
- ControllerUtils: Common utilities and error handling

Note: VIKTOR's introspection doesn't follow Python's MRO, so all view and download methods
from components are explicitly referenced as class attributes at the bottom of the class.
"""

from app.bridge.bridgeController.controller_utils import ControllerUtils
from app.bridge.bridgeController.geometry_views import GeometryViews
from app.bridge.bridgeController.idea_integration import IdeaIntegration
from app.bridge.bridgeController.info_views import InfoViews
from app.bridge.bridgeController.report_views import ReportViews
from app.bridge.bridgeController.scia_integration import SciaIntegration
from app.bridge.parametrization import BridgeParametrization
from viktor.core import ViktorController


class BridgeController(
    ControllerUtils,  # Must be first - provides utility methods for other mixins
    InfoViews,  # Info and map views
    GeometryViews,  # 3D and 2D geometry visualizations
    SciaIntegration,  # SCIA Engineer integration
    IdeaIntegration,  # IDEA StatiCa integration
    ReportViews,  # PDF report generation
    ViktorController,  # Must be last - base VIKTOR controller
):
    """
    Controller for the individual Bridge entity.

    This controller combines multiple component classes to provide:
    - Bridge information and location views (InfoViews)
    - 3D models and 2D section views (GeometryViews)
    - SCIA Engineer analysis integration (SciaIntegration)
    - IDEA StatiCa RCS integration (IdeaIntegration)
    - PDF report generation (ReportViews)
    - Common utilities and error handling (ControllerUtils)
    """

    label = "Brug"
    parametrization = BridgeParametrization  # type: ignore[assignment]

    # Explicit method references for VIKTOR introspection
    # VIKTOR's introspection doesn't follow MRO, so we explicitly reference all view/download methods
    # from component classes. These methods are inherited but need to be explicitly listed for VIKTOR to find them.

    # From InfoViews
    get_bridge_map_view = InfoViews.get_bridge_map_view
    get_load_combinations_view = InfoViews.get_load_combinations_view

    # From GeometryViews
    get_3d_view = GeometryViews.get_3d_view
    get_top_view = GeometryViews.get_top_view
    get_2d_horizontal_section = GeometryViews.get_2d_horizontal_section
    get_2d_longitudinal_section = GeometryViews.get_2d_longitudinal_section
    get_2d_cross_section = GeometryViews.get_2d_cross_section
    get_load_zones_view = GeometryViews.get_load_zones_view

    # From SciaIntegration
    get_scia_results_view_sls_kar = SciaIntegration.get_scia_results_view_sls_kar
    get_scia_results_view_sls_freq = SciaIntegration.get_scia_results_view_sls_freq
    get_scia_results_view_uls = SciaIntegration.get_scia_results_view_uls
    get_scia_1d_results_view_sls_kar = SciaIntegration.get_scia_1d_results_view_sls_kar
    get_scia_1d_results_view_sls_freq = SciaIntegration.get_scia_1d_results_view_sls_freq
    get_scia_1d_results_view_uls = SciaIntegration.get_scia_1d_results_view_uls
    get_scia_results_table = SciaIntegration.get_scia_results_table
    get_force_envelopes = SciaIntegration.get_force_envelopes
    download_scia_esa_model = SciaIntegration.download_scia_esa_model
    download_scia_xml_files = SciaIntegration.download_scia_xml_files
    download_scia_output_xml = SciaIntegration.download_scia_output_xml

    # From IdeaIntegration
    get_view_unique_idea_cross_sections = IdeaIntegration.get_view_unique_idea_cross_sections
    get_view_idea_rcs_results = IdeaIntegration.get_view_idea_rcs_results
    download_idea_xml_file = IdeaIntegration.download_idea_xml_file
    download_idea_analysis_results = IdeaIntegration.download_idea_analysis_results

    # From ReportViews
    get_output_report = ReportViews.get_output_report
