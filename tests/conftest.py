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
    pass


errors.UserError = UserError


# viktor.views with pass-through decorators and simple result classes
views = _ensure_module("viktor.views")


def _passthrough_decorator(*_d_args: Any, **_d_kwargs: Any):  # noqa: ANN401
    def _wrap(func):
        return func

    return _wrap


class GeometryResult:  # Minimal surface compatible class
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self.file = kwargs.get("file")
        self.figure = kwargs.get("figure")
        self.data = kwargs.get("data")
        self.features = kwargs.get("features", [])


class PlotlyResult:
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        # Common usage stores a JSON string in figure
        self.figure = kwargs.get("figure") or (args[0] if args else None)


class TableResult:
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self.data = kwargs.get("data") or (args[0] if args else None)


class WebResult:
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self.content = kwargs.get("content") or (args[0] if args else None)


class MapResult:
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self.features = kwargs.get("features") or (args[0] if args else [])
        # For tests that inspect description-like fields, allow generic attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


# Minimal map feature classes used by app.common.map_utils
class MapFeature:
    pass


class MapPoint(MapFeature):
    def __init__(self, lat: float, lon: float, description: str | None = None) -> None:
        self.lat = lat
        self.lon = lon
        self._description = description or ""


class MapPolygon(MapFeature):
    def __init__(self, points: list[MapPoint], description: str | None = None, color: Any | None = None) -> None:  # noqa: ANN401
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
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self.file = kwargs.get("file") or (args[0] if args else None)


views.PDFResult = PDFResult
views.MapFeature = MapFeature
views.MapPoint = MapPoint
views.MapPolygon = MapPolygon


# viktor.result
result = _ensure_module("viktor.result")


class DownloadResult:
    def __init__(self, file: Any, filename: str) -> None:
        self.file = file
        self.filename = filename


result.DownloadResult = DownloadResult


# viktor.api_v1
api_v1 = _ensure_module("viktor.api_v1")


class API:  # pragma: no cover - only a stub for importability
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        pass


api_v1.API = API


# viktor.core
core = _ensure_module("viktor.core")


class ViktorController:  # Minimal base class for controllers
    pass


core.ViktorController = ViktorController


class File:
    """Minimal File stub with helpers used in tests."""

    def __init__(self, data: bytes | None = None) -> None:
        self._data = data or b""
        # Add source attribute for zipfile operations
        self.source = BytesIO()

    @classmethod
    def from_data(cls, data: bytes) -> File:
        return cls(data)

    @classmethod
    def from_path(cls, path) -> File:  # noqa: ANN001
        try:
            with open(path, "rb") as f:
                return cls(f.read())
        except Exception:
            return cls(b"")

    def open_binary(self):  # Simple context manager returning a BytesIO
        class _Ctx:
            def __init__(self, data: bytes) -> None:
                self._data = data

            def __enter__(self):
                from io import BytesIO

                return BytesIO(self._data)

            def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
                return None

        return _Ctx(self._data)


core.File = File


class Color:
    def __init__(self, r: int, g: int, b: int) -> None:
        self.r, self.g, self.b = r, g, b

    @classmethod
    def blue(cls) -> Color:
        return cls(0, 0, 255)

    @classmethod
    def red(cls) -> Color:
        return cls(255, 0, 0)


core.Color = Color


# Provide symbols often imported from the root viktor module
class InitialEntity:  # Placeholder symbol used by app/__init__.py
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:  # noqa: ANN401
        pass


viktor.InitialEntity = InitialEntity


# Optional: provide a minimal parametrization module to avoid import errors at import-time
parametrization = _ensure_module("viktor.parametrization")


class _Dummy:  # Generic stand-in for parametrization classes
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        pass


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


def convert_word_to_pdf(_file_like):  # noqa: ANN001
    # Return a placeholder PDF-like File object
    return File.from_data(b"%PDF-1.4\n%stub-pdf\n")


utils.convert_word_to_pdf = convert_word_to_pdf

# viktor.external.idea_rcs (enums only for import-time usage in mappings)
external = _ensure_module("viktor.external")
idea_rcs = _ensure_module("viktor.external.idea_rcs")


class _EnumBase:
    pass


class ConcreteMaterial(_EnumBase):
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
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def set(self, key: str, value: bytes) -> None:
        self._store[key] = value

    def list(self, prefix: str | None = None) -> list[str]:  # noqa: ARG002
        return list(self._store.keys())


core.Storage = Storage

# viktor.external.scia - minimal stub API used in builder
scia = _ensure_module("viktor.external.scia")


class _Enum:
    def __init__(self, value: str | int) -> None:
        self.value = value


class Material:
    def __init__(self, material_id: int, name: str) -> None:
        self.material_id = material_id
        self.name = name


class Node:
    def __init__(self, name: str, x: float, y: float, z: float) -> None:
        self.name = name
        self.x, self.y, self.z = x, y, z


class Plane:
    def __init__(self, name: str, corner_nodes: list[Node], thickness: float, material: Material) -> None:
        self.name = name
        self.corner_nodes = corner_nodes
        self.thickness = thickness
        self.material = material


class LoadGroup:
    class LoadOption:
        PERMANENT = _Enum("PERMANENT")
        VARIABLE = _Enum("VARIABLE")
        ACCIDENTAL = _Enum("ACCIDENTAL")
        SEISMIC = _Enum("SEISMIC")

    class RelationOption:
        STANDARD = _Enum("STANDARD")
        EXCLUSIVE = _Enum("EXCLUSIVE")
        TOGETHER = _Enum("TOGETHER")

    class LoadTypeOption:
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
    def __init__(self, name: str = "default_load_case"):
        self.name = name
        
    class PermanentLoadType:
        SELF_WEIGHT = _Enum("SELF_WEIGHT")
        STANDARD = _Enum("STANDARD")
        PRIMARY_EFFECT = _Enum("PRIMARY_EFFECT")

    class VariableLoadType:
        STATIC = _Enum("STATIC")
        PRIMARY_EFFECT = _Enum("PRIMARY_EFFECT")

    class Specification:
        STANDARD = _Enum("STANDARD")
        STATIC_WIND = _Enum("STATIC_WIND")
        SNOW = _Enum("SNOW")
        TEMPERATURE = _Enum("TEMPERATURE")
        EARTHQUAKE = _Enum("EARTHQUAKE")

    class Duration:
        INSTANTANEOUS = _Enum("INSTANTANEOUS")
        SHORT = _Enum("SHORT")
        MEDIUM = _Enum("MEDIUM")
        LONG = _Enum("LONG")


class FreeSurfaceLoad:
    class Direction:
        X = _Enum("X")
        Y = _Enum("Y")
        Z = _Enum("Z")

    class Distribution:
        UNIFORM = _Enum("UNIFORM")


class LineForceSurface:
    class Direction:
        X = _Enum("X")
        Y = _Enum("Y")
        Z = _Enum("Z")


class FreeLineLoad:
    class Direction:
        X = _Enum("X")
        Y = _Enum("Y")
        Z = _Enum("Z")


class LoadCombination:
    class Type:
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
    pass


class LineSupport:
    class Freedom:
        FREE = _Enum("FREE")
        RIGID = _Enum("RIGID")
        FLEXIBLE = _Enum("FLEXIBLE")


class Model:
    def create_node(self, name: str, x: float, y: float, z: float) -> Node:
        return Node(name, x, y, z)

    def create_plane(self, corner_nodes: list[Node], thickness: float, name: str, material: Material) -> Plane:
        return Plane(name, corner_nodes, thickness, material)

    def create_load_group(self, name: str, *_args, **_kwargs) -> LoadGroup:
        return LoadGroup()

    def create_permanent_load_case(self, *args, **kwargs) -> LoadCase:
        return LoadCase()

    def create_variable_load_case(self, *args, **kwargs) -> LoadCase:
        return LoadCase()

    def create_free_surface_load(self, *args, **kwargs) -> FreeSurfaceLoad:
        return FreeSurfaceLoad()

    def create_line_load_on_plane(self, *args, **kwargs) -> LineForceSurface:
        return LineForceSurface()

    def create_free_line_load(self, *args, **kwargs) -> FreeLineLoad:
        return FreeLineLoad()

    def create_load_combination(self, *args, **kwargs) -> LoadCombination:
        return LoadCombination()

    def create_result_class(self, *args, **kwargs) -> ResultClass:
        return ResultClass()

    def generate_xml_input(self):
        from io import BytesIO

        return BytesIO(b"<xml/>"), BytesIO(b"<def/>")


class SciaAnalysis:
    def __init__(self, *_args, **_kwargs) -> None:
        self.status = "ok"
        self.error = None

    def execute(self, timeout: int = 0) -> None:  # noqa: ARG002
        return None

    def get_xml_output_file(self):
        from io import BytesIO

        return BytesIO(b"<results><table name='Displacements'><row/></table></results>")

    def get_updated_esa_model(self, as_file: bool = False):
        if as_file:
            return File.from_data(b"ESA")
        return b"ESA"


class OutputFileParser:
    @staticmethod
    def get_result(_file_like, _table_name: str):  # noqa: ANN001
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
def params() -> Any:
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
