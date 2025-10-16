"""
SCIA definitions and interface module.

This module defines a formal interface (Protocol) for building a SCIA model.
This allows the `src` layer to define the logic for constructing a bridge model,
while the `app` layer provides the concrete implementation using the VIKTOR SDK.
This approach decouples the core logic from the specific SDK implementation.
"""

from typing import Any, Literal, Protocol

from .types import (
    SciaAnalysis,
    SciaCombinationType,
    SciaFile,
    SciaFreeLineLoad,
    SciaFreeSurfaceLoad,
    SciaIntegrationStrip,
    SciaLineForceSurface,
    SciaLineSupport,
    SciaLoadCase,
    SciaLoadCombination,
    SciaLoadGroup,
    SciaMaterial,
    SciaModel,
    SciaNode,
    SciaPlate,
    SciaResultClass,
    SciaResults,
)


class SciaModelBuilder(Protocol):
    """
    Interface (Protocol) for a SCIA model builder.

    This protocol defines the methods that the core logic in `src` can use
    to build a SCIA model, without being directly dependent on the VIKTOR SDK.
    The `app` layer will provide a concrete implementation of this protocol.
    """

    def create_material(self, name: str, material_id: int = 0) -> SciaMaterial:
        """Creates a material in the SCIA model."""
        ...

    def create_node(self, name: str, x: float, y: float, z: float) -> SciaNode:
        """Creates a node in the SCIA model."""
        ...

    def create_plate(
        self,
        name: str,
        corner_node_names: list[str],
        thickness: float,
        material_name: str,
    ) -> SciaPlate:
        """Creates a plate (plane) in the SCIA model."""
        ...

    def create_load_group(
        self,
        name: str,
        load_option: Literal["PERMANENT", "VARIABLE", "ACCIDENTAL", "SEISMIC"],
        relation: Literal["STANDARD", "EXCLUSIVE", "TOGETHER"],
        load_type: (
            Literal[
                "CAT_A",
                "CAT_B",
                "CAT_C",
                "CAT_D",
                "CAT_E",
                "CAT_F",
                "CAT_G",
                "CAT_H",
                "WIND",
                "SNOW",
                "TEMPERATURE",
                "RAIN_WATER",
                "CONSTRUCTION_LOADS",
            ]
            | None
        ),
    ) -> SciaLoadGroup:
        """Creates a load group in the SCIA model."""
        ...

    def create_load_case(  # noqa: PLR0913
        self,
        name: str,
        description: str,
        group_name: str,
        case_type: Literal["PERMANENT", "VARIABLE"],
        permanent_type: Literal["SELF_WEIGHT", "STANDARD", "PRIMARY_EFFECT"] | None = None,
        variable_type: Literal["STATIC", "PRIMARY_EFFECT"] | None = None,
        specification: Literal["STANDARD", "STATIC_WIND", "SNOW", "TEMPERATURE", "EARTHQUAKE"] | None = None,
        duration: Literal["INSTANTANEOUS", "SHORT", "MEDIUM", "LONG"] | None = None,
    ) -> SciaLoadCase:
        """Creates a load case in the SCIA model."""
        ...

    def create_surface_load(
        self,
        name: str,
        load_case_name: str,
        corner_points: list[tuple[float, float, float]],
        load_value: float,
    ) -> SciaFreeSurfaceLoad:
        """Creates a free surface load in the SCIA model."""
        ...

    def create_line_load_on_plane(
        self,
        name: str,
        load_case_name: str,
        plane_name: str,
        edge_index: int,
        load_value: float,
    ) -> SciaLineForceSurface:
        """Creates a uniform line load on a plane edge in the SCIA model."""
        ...

    def create_free_line_load(  # noqa: PLR0913
        self,
        name: str,
        load_case_name: str,
        point_1: tuple[float, float],
        point_2: tuple[float, float],
        load_value: float,
        direction: Literal["X", "Y", "Z"] = "Z",
    ) -> SciaFreeLineLoad:
        """Creates a uniform free line load between two XY points."""
        ...

    def create_load_combination(
        self,
        name: str,
        combination_type: SciaCombinationType,
        load_case_factors: dict[SciaLoadCase, float],
        description: str,
    ) -> SciaLoadCombination:
        """Creates a load combination in the SCIA model."""
        ...

    def create_result_class(
        self,
        name: str,
        combinations: list[SciaLoadCombination] | None = None,
        nonlinear_combinations: list[Any] | None = None,
    ) -> SciaResultClass:
        """Creates a result class in the SCIA model."""
        ...

    def create_line_support_on_plane(
        self,
        name: str,
        plane_name: str,
        edge_index: int,
        freedom: dict[str, str],
        stiffness: dict[str, float],
    ) -> SciaLineSupport:
        """Creates a line support on a plane edge in the SCIA model."""
        ...

    def create_integration_strip(
        self,
        plane: str,
        point_1: tuple[float, float, float],
        point_2: tuple[float, float, float],
        width: float,
    ) -> SciaIntegrationStrip:
        """Creates an integration strip in the SCIA model."""
        ...

    def get_model(self) -> SciaModel:
        """Returns the final, fully constructed SCIA model object."""
        ...

    def generate_xml_input(self) -> tuple[SciaFile, SciaFile]:
        """Generates the XML and DEF file from the constructed model."""
        ...

    def run_analysis(self, xml_file: SciaFile, def_file: SciaFile, esa_template: SciaFile) -> SciaAnalysis:
        """Runs the SCIA analysis and returns the analysis object."""
        ...

    def extract_analysis_results(self, analysis: SciaAnalysis) -> SciaResults:
        """Extracts results from a completed SCIA analysis."""
        ...

    def get_displacement_results(self, analysis: SciaAnalysis) -> dict[str, Any]:
        """Extracts displacement results from SCIA analysis."""
        ...

    def get_internal_force_results(self, analysis: SciaAnalysis) -> dict[str, Any]:
        """Extracts internal force results from SCIA analysis."""
        ...

    def get_reaction_results(self, analysis: SciaAnalysis) -> dict[str, Any]:
        """Extracts reaction force results from SCIA analysis."""
        ...

    def get_stress_results(self, analysis: SciaAnalysis) -> dict[str, Any]:
        """Extracts stress results from SCIA analysis."""
        ...

    def get_analysis_status(self, analysis: SciaAnalysis) -> dict[str, Any]:
        """Gets the status and metadata of the SCIA analysis."""
        ...

    def parse_xml_results(self, xml_output_file: SciaFile) -> dict[str, Any]:
        """Parses the XML output file to extract structured results."""
        ...
