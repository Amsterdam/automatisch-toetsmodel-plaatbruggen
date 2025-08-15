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

import sys
import types
from io import BytesIO
from typing import Any

import pytest


def _ensure_module(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        sys.modules[name] = module
    return module


# Root viktor module
viktor = _ensure_module("viktor")


# viktor.errors
errors = _ensure_module("viktor.errors")


class UserError(Exception):
    """User error exception for testing."""


errors.UserError = UserError


# viktor.views with pass-through decorators and simple result classes
views = _ensure_module("viktor.views")


def _passthrough_decorator(*_d_args: Any, **_d_kwargs: Any) -> Any:  # noqa: ANN401
    """Create a passthrough decorator for testing."""

    def _wrap(func: Any) -> Any:  # noqa: ANN401
        return func

    return _wrap


class GeometryResult:  # Minimal surface compatible class
    """Minimal geometry result stub for testing."""

    def __init__(self, *_args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize geometry result with file, figure, data, and features."""
        self.file = kwargs.get("file")
        self.figure = kwargs.get("figure")
        self.data = kwargs.get("data")
        self.features = kwargs.get("features", [])


class PlotlyResult:
    """Minimal plotly result stub for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize plotly result with figure."""
        # Common usage stores a JSON string in figure
        self.figure = kwargs.get("figure") or (args[0] if args else None)


class TableResult:
    """Minimal table result stub for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize table result with data."""
        self.data = kwargs.get("data") or (args[0] if args else None)


class WebResult:
    """Minimal web result stub for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize web result with content."""
        self.content = kwargs.get("content") or (args[0] if args else None)


class MapResult:
    """Minimal map result stub for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize map result with features."""
        self.features = kwargs.get("features") or (args[0] if args else [])
        # For tests that inspect description-like fields, allow generic attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


# Minimal map feature classes used by app.common.map_utils
class MapFeature:
    """Base map feature class for testing."""


class MapPoint(MapFeature):
    """Map point feature for testing."""

    def __init__(self, lat: float, lon: float, description: str | None = None) -> None:
        """Initialize map point with coordinates and description."""
        self.lat = lat
        self.lon = lon
        self._description = description or ""


class MapPolygon(MapFeature):
    """Map polygon feature for testing."""

    def __init__(self, points: list[MapPoint], description: str | None = None, color: Any | None = None) -> None:  # noqa: ANN401
        """Initialize map polygon with points, description and color."""
        self.points = points
        self._description = description or ""
        self.color = color


views.GeometryView = _passthrough_decorator
views.PlotlyView = _passthrough_decorator
views.TableView = _passthrough_decorator
views.MapView = _passthrough_decorator
views.PDFView = _passthrough_decorator
views.WebView = _passthrough_decorator
views.GeometryResult = GeometryResult
views.PlotlyResult = PlotlyResult
views.TableResult = TableResult
views.WebResult = WebResult
views.MapResult = MapResult


class PDFResult:
    """Minimal PDF result stub for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize PDF result with file."""
        self.file = kwargs.get("file") or (args[0] if args else None)


views.PDFResult = PDFResult
views.MapFeature = MapFeature
views.MapPoint = MapPoint
views.MapPolygon = MapPolygon


# viktor.result
result = _ensure_module("viktor.result")


class DownloadResult:
    """Download result stub for testing."""

    def __init__(self, file: Any, filename: str) -> None:  # noqa: ANN401
        """Initialize download result with file and filename."""
        self.file = file
        self.filename = filename


result.DownloadResult = DownloadResult


# viktor.api_v1
api_v1 = _ensure_module("viktor.api_v1")


class API:  # pragma: no cover - only a stub for importability
    """API stub for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize API stub."""


api_v1.API = API


# viktor.core
core = _ensure_module("viktor.core")


class ViktorController:  # Minimal base class for controllers
    """Minimal VIKTOR controller base class for testing."""


core.ViktorController = ViktorController


class File:
    """Minimal File stub with helpers used in tests."""

    def __init__(self, data: bytes | None = None) -> None:
        """Initialize file with data."""
        self._data = data or b""
        # Add source attribute for zipfile operations
        self.source = BytesIO()

    @classmethod
    def from_data(cls, data: bytes) -> File:
        """Create file from data."""
        return cls(data)

    @classmethod
    def from_path(cls, path: str) -> File:
        """Create file from path."""
        try:
            with open(path, "rb") as f:
                return cls(f.read())
        except Exception:
            return cls(b"")

    def open_binary(self) -> object:  # Simple context manager returning a BytesIO
        """Open file as binary context manager."""

        class _Ctx:
            def __init__(self, data: bytes) -> None:
                self._data = data

            def __enter__(self) -> Any:  # noqa: ANN401
                from io import BytesIO

                return BytesIO(self._data)

            def __exit__(self, exc_type: object | None, exc: object | None, tb: object | None) -> None:  # noqa: PYI036
                return None

        return _Ctx(self._data)


core.File = File


class Color:
    """Color stub for testing."""

    def __init__(self, r: int, g: int, b: int) -> None:
        """Initialize color with RGB values."""
        self.r, self.g, self.b = r, g, b

    @classmethod
    def blue(cls) -> Color:
        """Create blue color."""
        return cls(0, 0, 255)

    @classmethod
    def red(cls) -> Color:
        """Create red color."""
        return cls(255, 0, 0)


core.Color = Color


# Provide symbols often imported from the root viktor module
class InitialEntity:  # Placeholder symbol used by app/__init__.py
    """Initial entity stub for testing."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:  # noqa: ANN401
        """Initialize initial entity stub."""


viktor.InitialEntity = InitialEntity


# Optional: provide a minimal parametrization module to avoid import errors at import-time
parametrization = _ensure_module("viktor.parametrization")


class _Dummy:  # Generic stand-in for parametrization classes
    """Generic dummy class for parametrization stubs."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize dummy class."""


# Expose common names that might be imported; all behave as inert placeholders
for _name in (
    # Core parametrization containers
    "Parametrization",
    "Page",
    "Tab",
    # Field types
    "Text",
    "TextField",
    "TextAreaField",
    "NumberField",
    "OptionField",
    "MultiSelectField",
    "BooleanField",
    "OutputField",
    # Dynamic array and constraints
    "DynamicArray",
    "DynamicArrayConstraint",
    # UI helpers / layout
    "LineBreak",
    # Visibility / lookups
    "Lookup",
    "RowLookup",
    "IsFalse",
    # Actions
    "ActionButton",
    "DownloadButton",
    # Managers
    "ChildEntityManager",
):
    setattr(parametrization, _name, _Dummy)

# Also expose some frequently (and sometimes incorrectly) imported names on the root viktor module
setattr(viktor, "DynamicArray", getattr(parametrization, "DynamicArray"))

# viktor.utils
utils = _ensure_module("viktor.utils")


def convert_word_to_pdf(_file_like: object) -> File:
    """Convert Word file to PDF stub for testing."""
    # Return a placeholder PDF-like File object
    return File.from_data(b"%PDF-1.4\n%stub-pdf\n")


utils.convert_word_to_pdf = convert_word_to_pdf

# viktor.external.idea_rcs (enums only for import-time usage in mappings)
external = _ensure_module("viktor.external")
idea_rcs = _ensure_module("viktor.external.idea_rcs")


class _EnumBase:
    """Base enum class for testing."""


class ConcreteMaterial(_EnumBase):
    """Concrete material enum for testing."""

    C12_15 = object()
    C16_20 = object()
    C20_25 = object()
    C25_30 = object()
    C30_37 = object()
    C35_45 = object()
    C40_50 = object()
    C45_55 = object()
    C50_60 = object()
    C55_67 = object()
    C60_75 = object()
    C70_85 = object()
    C80_95 = object()
    C90_105 = object()


class ReinforcementMaterial(_EnumBase):
    """Reinforcement material enum for testing."""

    B_400A = object()
    B_400B = object()
    B_400C = object()
    B_500A = object()
    B_500B = object()
    B_500C = object()
    B_550A = object()
    B_550B = object()
    B_600A = object()
    B_600B = object()
    B_600C = object()


idea_rcs.ConcreteMaterial = ConcreteMaterial
idea_rcs.ReinforcementMaterial = ReinforcementMaterial


# viktor.core.Storage (simple key-value in-memory stub)
class Storage:
    """Simple in-memory storage stub for testing."""

    def __init__(self) -> None:
        """Initialize empty storage."""
        self._store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        """Get value by key."""
        return self._store.get(key)

    def set(self, key: str, value: bytes) -> None:
        """Set value for key."""
        self._store[key] = value

    def list(self, prefix: str | None = None) -> list[str]:  # noqa: ARG002
        """List all keys."""
        return list(self._store.keys())


core.Storage = Storage

# viktor.external.scia - minimal stub API used in builder
scia = _ensure_module("viktor.external.scia")


class _Enum:
    """Simple enum stub for testing."""

    def __init__(self, value: str | int) -> None:
        """Initialize enum with value."""
        self.value = value


class Material:
    """Material stub for testing."""

    def __init__(self, material_id: int, name: str) -> None:
        """Initialize material with ID and name."""
        self.material_id = material_id
        self.name = name


class Node:
    """Node stub for testing."""

    def __init__(self, name: str, x: float, y: float, z: float) -> None:
        """Initialize node with name and coordinates."""
        self.name = name
        self.x, self.y, self.z = x, y, z


class Plane:
    """Plane stub for testing."""

    def __init__(self, name: str, corner_nodes: list[Node], thickness: float, material: Material) -> None:
        """Initialize plane with name, corner nodes, thickness and material."""
        self.name = name
        self.corner_nodes = corner_nodes
        self.thickness = thickness
        self.material = material


class LoadGroup:
    """Load group stub for testing."""

    class LoadOption:
        """Load option enums."""

        PERMANENT = _Enum("PERMANENT")
        VARIABLE = _Enum("VARIABLE")
        ACCIDENTAL = _Enum("ACCIDENTAL")
        SEISMIC = _Enum("SEISMIC")

    class RelationOption:
        """Relation option enums."""

        STANDARD = _Enum("STANDARD")
        EXCLUSIVE = _Enum("EXCLUSIVE")
        TOGETHER = _Enum("TOGETHER")

    class LoadTypeOption:
        """Load type option enums."""

        CAT_A = _Enum("CAT_A")
        CAT_B = _Enum("CAT_B")
        CAT_C = _Enum("CAT_C")
        CAT_D = _Enum("CAT_D")
        CAT_E = _Enum("CAT_E")
        CAT_F = _Enum("CAT_F")
        CAT_G = _Enum("CAT_G")
        CAT_H = _Enum("CAT_H")
        WIND = _Enum("WIND")
        SNOW = _Enum("SNOW")
        TEMPERATURE = _Enum("TEMPERATURE")
        RAIN_WATER = _Enum("RAIN_WATER")
        CONSTRUCTION_LOADS = _Enum("CONSTRUCTION_LOADS")


class LoadCase:
    """Load case stub for testing."""

    def __init__(self, name: str = "default_load_case") -> None:
        """Initialize load case with name."""
        self.name = name

    class PermanentLoadType:
        """Permanent load type enums."""

        SELF_WEIGHT = _Enum("SELF_WEIGHT")
        STANDARD = _Enum("STANDARD")
        PRIMARY_EFFECT = _Enum("PRIMARY_EFFECT")

    class VariableLoadType:
        """Variable load type enums."""

        STATIC = _Enum("STATIC")
        PRIMARY_EFFECT = _Enum("PRIMARY_EFFECT")

    class Specification:
        """Specification enums."""

        STANDARD = _Enum("STANDARD")
        STATIC_WIND = _Enum("STATIC_WIND")
        SNOW = _Enum("SNOW")
        TEMPERATURE = _Enum("TEMPERATURE")
        EARTHQUAKE = _Enum("EARTHQUAKE")

    class Duration:
        """Duration enums."""

        INSTANTANEOUS = _Enum("INSTANTANEOUS")
        SHORT = _Enum("SHORT")
        MEDIUM = _Enum("MEDIUM")
        LONG = _Enum("LONG")


class FreeSurfaceLoad:
    """Free surface load stub for testing."""

    class Direction:
        """Direction enums."""

        X = _Enum("X")
        Y = _Enum("Y")
        Z = _Enum("Z")

    class Distribution:
        """Distribution enums."""

        UNIFORM = _Enum("UNIFORM")


class LineForceSurface:
    """Line force surface stub for testing."""

    class Direction:
        """Direction enums."""

        X = _Enum("X")
        Y = _Enum("Y")
        Z = _Enum("Z")


class FreeLineLoad:
    """Free line load stub for testing."""

    class Direction:
        """Direction enums."""

        X = _Enum("X")
        Y = _Enum("Y")
        Z = _Enum("Z")


class LoadCombination:
    """Load combination stub for testing."""

    class Type:
        """Type enums."""

        ENVELOPE_ULTIMATE = _Enum("ENVELOPE_ULTIMATE")
        ENVELOPE_SERVICEABILITY = _Enum("ENVELOPE_SERVICEABILITY")
        LINEAR_ULTIMATE = _Enum("LINEAR_ULTIMATE")
        LINEAR_SERVICEABILITY = _Enum("LINEAR_SERVICEABILITY")
        EN_ULS_SET_B = _Enum("EN_ULS_SET_B")
        EN_ULS_SET_C = _Enum("EN_ULS_SET_C")
        EN_SLS_CHAR = _Enum("EN_SLS_CHAR")
        EN_SLS_FREQ = _Enum("EN_SLS_FREQ")
        EN_SLS_QUASI = _Enum("EN_SLS_QUASI")
        EN_ACC_ONE = _Enum("EN_ACC_ONE")
        EN_ACC_TWO = _Enum("EN_ACC_TWO")
        EN_SEISMIC = _Enum("EN_SEISMIC")


class ResultClass:
    """Result class stub for testing."""


class LineSupport:
    """Line support stub for testing."""

    class Freedom:
        """Freedom enums."""

        FREE = _Enum("FREE")
        RIGID = _Enum("RIGID")
        FLEXIBLE = _Enum("FLEXIBLE")


class Model:
    """Model stub for testing."""

    def create_node(self, name: str, x: float, y: float, z: float) -> Node:
        """Create a node."""
        return Node(name, x, y, z)

    def create_plane(self, corner_nodes: list[Node], thickness: float, name: str, material: Material) -> Plane:
        """Create a plane."""
        return Plane(name, corner_nodes, thickness, material)

    def create_load_group(self, name: str, *_args: object, **_kwargs: object) -> LoadGroup:  # noqa: ARG002
        """Create a load group."""
        return LoadGroup()

    def create_permanent_load_case(self, *args: object, **kwargs: object) -> LoadCase:  # noqa: ARG002
        """Create a permanent load case."""
        return LoadCase()

    def create_variable_load_case(self, *args: object, **kwargs: object) -> LoadCase:  # noqa: ARG002
        """Create a variable load case."""
        return LoadCase()

    def create_free_surface_load(self, *args: object, **kwargs: object) -> FreeSurfaceLoad:  # noqa: ARG002
        """Create a free surface load."""
        return FreeSurfaceLoad()

    def create_line_load_on_plane(self, *args: object, **kwargs: object) -> LineForceSurface:  # noqa: ARG002
        """Create a line load on plane."""
        return LineForceSurface()

    def create_free_line_load(self, *args: object, **kwargs: object) -> FreeLineLoad:  # noqa: ARG002
        """Create a free line load."""
        return FreeLineLoad()

    def create_load_combination(self, *args: object, **kwargs: object) -> LoadCombination:  # noqa: ARG002
        """Create a load combination."""
        return LoadCombination()

    def create_result_class(self, *args: object, **kwargs: object) -> ResultClass:  # noqa: ARG002
        """Create a result class."""
        return ResultClass()

    def generate_xml_input(self) -> tuple[BytesIO, BytesIO]:
        """Generate XML input."""
        from io import BytesIO

        return BytesIO(b"<xml/>"), BytesIO(b"<def/>")


class SciaAnalysis:
    """SCIA analysis stub for testing."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        """Initialize SCIA analysis."""
        self.status = "ok"
        self.error = None

    def execute(self, timeout: int = 0) -> None:  # noqa: ARG002
        """Execute analysis."""
        return

    def get_xml_output_file(self) -> BytesIO:
        """Get XML output file."""
        from io import BytesIO

        return BytesIO(b"<results><table name='Displacements'><row/></table></results>")

    def get_updated_esa_model(self, as_file: bool = False) -> File | bytes:
        """Get updated ESA model."""
        if as_file:
            return File.from_data(b"ESA")
        return b"ESA"


class OutputFileParser:
    """Output file parser stub for testing."""

    @staticmethod
    def get_result(_file_like: object, _table_name: str) -> dict[str, list]:
        """Get result from file."""
        return {"columns": [], "rows": []}


scia.Material = Material
scia.Node = Node
scia.Plane = Plane
scia.LoadGroup = LoadGroup
scia.LoadCase = LoadCase
scia.FreeSurfaceLoad = FreeSurfaceLoad
scia.LineForceSurface = LineForceSurface
scia.FreeLineLoad = FreeLineLoad
scia.LoadCombination = LoadCombination
scia.ResultClass = ResultClass
scia.LineSupport = LineSupport
scia.Model = Model
scia.SciaAnalysis = SciaAnalysis
scia.OutputFileParser = OutputFileParser


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
