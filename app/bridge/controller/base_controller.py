"""
Main BridgeController class using mixin architecture.

This module defines the main BridgeController by composing all
functionality mixins in the correct inheritance order.
"""

from app.bridge.controller.controller_utils import ControllerUtilsMixin
from app.bridge.controller.geometry_views import GeometryViewsMixin
from app.bridge.controller.idea_integration import IdeaIntegrationMixin
from app.bridge.controller.info_views import InfoViewsMixin
from app.bridge.controller.report_views import ReportViewsMixin
from app.bridge.controller.scia_integration import SciaIntegrationMixin
from app.bridge.parametrization import BridgeParametrization
from viktor.core import ViktorController


class BridgeController(
    ControllerUtilsMixin,  # Must be first - provides utility methods for other mixins
    InfoViewsMixin,  # Info and map views
    GeometryViewsMixin,  # 3D and 2D geometry visualizations
    SciaIntegrationMixin,  # SCIA Engineer integration
    IdeaIntegrationMixin,  # IDEA StatiCa integration
    ReportViewsMixin,  # PDF report generation
    ViktorController,  # Must be last - base VIKTOR controller
):
    """
    Controller for the individual Bridge entity.

    This controller combines multiple mixins to provide:
    - Bridge information and location views (InfoViewsMixin)
    - 3D models and 2D section views (GeometryViewsMixin)
    - SCIA Engineer analysis integration (SciaIntegrationMixin)
    - IDEA StatiCa RCS integration (IdeaIntegrationMixin)
    - PDF report generation (ReportViewsMixin)
    - Common utilities and error handling (ControllerUtilsMixin)

    The mixin architecture provides:
    - Clear separation of concerns (94% reduction from 1974 to ~100 lines)
    - Better testability (each mixin can be tested independently)
    - Easier maintenance (related functionality grouped together)
    - Parallel development (teams can work on different mixins)

    Method Resolution Order (MRO):
    1. ControllerUtilsMixin - provides helper methods used by other mixins
    2. InfoViewsMixin - bridge location map and load combinations
    3. GeometryViewsMixin - 3D model and 2D section views
    4. SciaIntegrationMixin - SCIA analysis views and downloads
    5. IdeaIntegrationMixin - IDEA RCS analysis views and downloads
    6. ReportViewsMixin - PDF report generation
    7. ViktorController - base VIKTOR functionality

    Total Views: 15
    - 1 MapView (bridge location)
    - 6 PlotlyView (3D model, 2D sections, load zones)
    - 7 TableView (load combinations, SCIA results, IDEA results)
    - 1 PDFView (report)

    Total Downloads: 5
    - 3 SCIA downloads (ESA model, XML files, output XML)
    - 2 IDEA downloads (XML model, analysis results)

    Performance:
    - All SCIA and IDEA analyses use caching for optimal performance
    - Cache is automatically invalidated when relevant parameters change
    - Entity-scoped storage ensures isolated caching per bridge

    Usage:
        controller = BridgeController()
        result = controller.get_3d_view(params)
    """

    label = "Brug"
    parametrization = BridgeParametrization  # type: ignore[assignment]
