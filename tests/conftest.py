"""
Test configuration: lightweight VIKTOR shim for unit-test collection.

This shim enables importing app-layer modules in a normal Python environment
without a live VIKTOR runtime by providing minimal stand-ins for commonly
used VIKTOR symbols (errors, views, result, api_v1, core, etc.).

Heavy, end-to-end VIKTOR tests should remain in the dedicated VIKTOR test
runner. This shim is only for unit/integration tests that mock external
behavior and validate structure or business logic.
"""

from __future__ import annotations

import pytest

# VIKTOR SDK stubs for unit tests
# These are lightweight stand-ins for VIKTOR symbols to prevent import-time failures
# in test environments where the full VIKTOR SDK is not available

# Core VIKTOR modules
viktor = type("viktor", (), {})  # type: ignore[misc]
viktor.errors = type("viktor.errors", (), {})  # type: ignore[attr-defined]
viktor.views = type("viktor.views", (), {})  # type: ignore[attr-defined]
viktor.result = type("viktor.result", (), {})  # type: ignore[attr-defined]
viktor.api_v1 = type("viktor.api_v1", (), {})  # type: ignore[attr-defined]
viktor.core = type("viktor.core", (), {})  # type: ignore[attr-defined]
viktor.utils = type("viktor.utils", (), {})  # type: ignore[attr-defined]
viktor.external = type("viktor.external", (), {})  # type: ignore[attr-defined]
viktor.external.idea_rcs = type("viktor.external.idea_rcs", (), {})  # type: ignore[attr-defined]
viktor.external.scia = type("viktor.external.scia", (), {})  # type: ignore[attr-defined]

# Error types
UserError = type("UserError", (Exception,), {})  # type: ignore[misc]
viktor.errors.UserError = UserError  # type: ignore[attr-defined]


# View decorators and result types
def _passthrough_decorator(*args: object, **kwargs: object) -> object:  # type: ignore[misc]
    """Pass-through decorator for view methods."""

    def decorator(func: object) -> object:  # type: ignore[misc]
        return func

    return decorator


GeometryView = _passthrough_decorator  # type: ignore[misc]
PlotlyView = _passthrough_decorator  # type: ignore[misc]
TableView = _passthrough_decorator  # type: ignore[misc]
MapView = _passthrough_decorator  # type: ignore[misc]
PDFView = _passthrough_decorator  # type: ignore[misc]
WebView = _passthrough_decorator  # type: ignore[misc]

# Result types
GeometryResult = type("GeometryResult", (), {})  # type: ignore[misc]
PlotlyResult = type("PlotlyResult", (), {})  # type: ignore[misc]
TableResult = type("TableResult", (), {})  # type: ignore[misc]
WebResult = type("WebResult", (), {})  # type: ignore[misc]
MapResult = type("MapResult", (), {})  # type: ignore[misc]
MapFeature = type("MapFeature", (), {})  # type: ignore[misc]
MapPoint = type("MapPoint", (), {})  # type: ignore[misc]
MapPolygon = type("MapPolygon", (), {})  # type: ignore[misc]

viktor.views.GeometryView = _passthrough_decorator  # type: ignore[attr-defined]
viktor.views.PlotlyView = _passthrough_decorator  # type: ignore[attr-defined]
viktor.views.TableView = _passthrough_decorator  # type: ignore[attr-defined]
viktor.views.MapView = _passthrough_decorator  # type: ignore[attr-defined]
viktor.views.PDFView = _passthrough_decorator  # type: ignore[attr-defined]
viktor.views.WebView = _passthrough_decorator  # type: ignore[attr-defined]
viktor.views.GeometryResult = GeometryResult  # type: ignore[attr-defined]
viktor.views.PlotlyResult = PlotlyResult  # type: ignore[attr-defined]
viktor.views.TableResult = TableResult  # type: ignore[attr-defined]
viktor.views.WebResult = WebResult  # type: ignore[attr-defined]
viktor.views.MapResult = MapResult  # type: ignore[attr-defined]
viktor.views.MapFeature = MapFeature  # type: ignore[attr-defined]
viktor.views.MapPoint = MapPoint  # type: ignore[attr-defined]
viktor.views.MapPolygon = MapPolygon  # type: ignore[attr-defined]


# Result types
class DownloadResult:
    """Download result stub for testing."""

    def __init__(self, file: object, filename: str) -> None:
        """Initialize download result with file and filename."""
        self.file = file
        self.filename = filename


viktor.result.DownloadResult = DownloadResult  # type: ignore[attr-defined]

# API and controller types
API = type("API", (), {})  # type: ignore[misc]
viktor.api_v1.API = API  # type: ignore[attr-defined]

ViktorController = type("ViktorController", (), {})  # type: ignore[misc]
viktor.core.ViktorController = ViktorController  # type: ignore[attr-defined]

# Core types
File = type("File", (), {})  # type: ignore[misc]
viktor.core.File = File  # type: ignore[attr-defined]

Color = type("Color", (), {})  # type: ignore[misc]
viktor.core.Color = Color  # type: ignore[attr-defined]

InitialEntity = type("InitialEntity", (), {})  # type: ignore[misc]
viktor.InitialEntity = InitialEntity  # type: ignore[attr-defined]


# Utility functions
def convert_word_to_pdf() -> object:  # type: ignore[misc]
    """Mock convert_word_to_pdf function."""
    return None


viktor.utils.convert_word_to_pdf = convert_word_to_pdf  # type: ignore[attr-defined]

# IDEA RCS types
ConcreteMaterial = type("ConcreteMaterial", (), {})  # type: ignore[misc]
ReinforcementMaterial = type("ReinforcementMaterial", (), {})  # type: ignore[misc]
viktor.external.idea_rcs.ConcreteMaterial = ConcreteMaterial  # type: ignore[attr-defined]
viktor.external.idea_rcs.ReinforcementMaterial = ReinforcementMaterial  # type: ignore[attr-defined]

# Storage type
Storage = type("Storage", (), {})  # type: ignore[misc]
viktor.core.Storage = Storage  # type: ignore[attr-defined]

# SCIA types
Material = type("Material", (), {})  # type: ignore[misc]
Node = type("Node", (), {})  # type: ignore[misc]
Plane = type("Plane", (), {})  # type: ignore[misc]
LoadGroup = type("LoadGroup", (), {})  # type: ignore[misc]
LoadCase = type("LoadCase", (), {})  # type: ignore[misc]
FreeSurfaceLoad = type("FreeSurfaceLoad", (), {})  # type: ignore[misc]
LineForceSurface = type("LineForceSurface", (), {})  # type: ignore[misc]
FreeLineLoad = type("FreeLineLoad", (), {})  # type: ignore[misc]
LoadCombination = type("LoadCombination", (), {})  # type: ignore[misc]
ResultClass = type("ResultClass", (), {})  # type: ignore[misc]
LineSupport = type("LineSupport", (), {})  # type: ignore[misc]
Model = type("Model", (), {})  # type: ignore[misc]
SciaAnalysis = type("SciaAnalysis", (), {})  # type: ignore[misc]
OutputFileParser = type("OutputFileParser", (), {})  # type: ignore[misc]

viktor.external.scia.Material = Material  # type: ignore[attr-defined]
viktor.external.scia.Node = Node  # type: ignore[attr-defined]
viktor.external.scia.Plane = Plane  # type: ignore[attr-defined]
viktor.external.scia.LoadGroup = LoadGroup  # type: ignore[attr-defined]
viktor.external.scia.LoadCase = LoadCase  # type: ignore[attr-defined]
viktor.external.scia.FreeSurfaceLoad = FreeSurfaceLoad  # type: ignore[attr-defined]
viktor.external.scia.LineForceSurface = LineForceSurface  # type: ignore[attr-defined]
viktor.external.scia.FreeLineLoad = FreeLineLoad  # type: ignore[attr-defined]
viktor.external.scia.LoadCombination = LoadCombination  # type: ignore[attr-defined]
viktor.external.scia.ResultClass = ResultClass  # type: ignore[attr-defined]
viktor.external.scia.LineSupport = LineSupport  # type: ignore[attr-defined]
viktor.external.scia.Model = Model  # type: ignore[attr-defined]
viktor.external.scia.SciaAnalysis = SciaAnalysis  # type: ignore[attr-defined]
viktor.external.scia.OutputFileParser = OutputFileParser  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Pytest fixtures for src-level integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def params() -> object:
    """
    Provide minimal project parameters for combination/load tests.

    Exposes attributes used by load combination table helpers:
    - cc_class
    - design_code
    - info.construction_year
    """

    class _Info:
        construction_year = 2010

    class _Params:
        cc_class = "CC2"
        design_code = "NEN 8700 verbouw"
        info = _Info()

    return _Params()
