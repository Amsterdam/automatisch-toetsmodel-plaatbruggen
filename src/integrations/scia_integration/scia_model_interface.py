"""
SCIA definitions and interface module.

This module defines a formal interface (Protocol) for building a SCIA model.
This allows the `src` layer to define the logic for constructing a bridge model,
while the `app` layer provides the concrete implementation using the VIKTOR SDK.
This approach decouples the core logic from the specific SDK implementation.

.. note::
    As of the modernization effort, this Protocol now uses SDK enum types directly
    instead of string literals and custom enums. The `app` layer re-exports these
    types from `app.bridge.scia_types` for convenience.
"""

from io import BytesIO
from typing import Any, Protocol

# Type aliases for opaque SCIA objects that the builder implementation will handle.
# The src layer treats these as abstract types.
SciaObject = Any
SciaModel = Any
SciaNode = Any
SciaMaterial = Any
SciaPlate = Any
SciaLoadGroup = Any
SciaLoadCase = Any
SciaLoadCombination = Any
SciaLineSupport = Any
SciaFreeSurfaceLoad = Any
SciaLineForceSurface = Any
SciaFreeLineLoad = Any
SciaAnalysis = Any
SciaResults = Any
SciaResultClass = Any
SciaIntegrationStrip = Any

# Type aliases for SCIA SDK enum types
# These are opaque to the src layer - the app layer provides concrete implementations
LoadGroupOption = Any
LoadGroupRelation = Any
LoadGroupLoadType = Any
LoadCaseActionType = Any
LoadCasePermanentType = Any
LoadCaseVariableType = Any
LoadCaseSpecification = Any
LoadCaseDuration = Any
LoadCombinationType = Any
FreeLineLoadDirection = Any
LineSupportFreedom = Any

# Type aliases for file objects
SciaFile = BytesIO | bytes

# Backward compatibility: Keep SciaCombinationType as alias to LoadCombinationType
SciaCombinationType = LoadCombinationType


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
        load_option: str,
        relation: str,
        load_type: str | None,
    ) -> SciaLoadGroup:
        """
        Creates a load group in the SCIA model.

        :param name: Name of the load group
        :param load_option: SDK enum for load option (PERMANENT, VARIABLE, ACCIDENTAL, SEISMIC)
        :param relation: SDK enum for relation (STANDARD, EXCLUSIVE, TOGETHER)
        :param load_type: Optional SDK enum for load type
        """
        ...

    def create_load_case(  # noqa: PLR0913
        self,
        name: str,
        description: str,
        group_name: str,
        case_type: str,
        permanent_type: str | None = None,
        variable_type: str | None = None,
        specification: str | None = None,
        duration: str | None = None,
    ) -> SciaLoadCase:
        """
        Creates a load case in the SCIA model.

        :param name: Name of the load case
        :param description: Description of the load case
        :param group_name: Name of the load group
        :param case_type: SDK enum for action type (PERMANENT or VARIABLE)
        :param permanent_type: SDK enum for permanent load type (if permanent)
        :param variable_type: SDK enum for variable load type (if variable)
        :param specification: SDK enum for specification (if variable)
        :param duration: SDK enum for duration (if variable)
        """
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
        direction: str = "Z",
    ) -> SciaFreeLineLoad:
        """
        Creates a uniform free line load between two XY points.

        :param name: Name of the line load
        :param load_case_name: Name of the load case
        :param point_1: First point (x, y)
        :param point_2: Second point (x, y)
        :param load_value: Load value
        :param direction: SDK enum for direction (X, Y, or Z)
        """
        ...

    def create_load_combination(
        self,
        name: str,
        combination_type: str,
        load_case_factors: dict[SciaLoadCase, float],
        description: str,
    ) -> SciaLoadCombination:
        """
        Creates a load combination in the SCIA model.

        :param name: Name of the load combination
        :param combination_type: SDK enum for combination type
        :param load_case_factors: Dictionary mapping load cases to factors
        :param description: Description of the combination
        """
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
        """
        Creates a line support on a plane edge in the SCIA model.

        :param name: Name of the line support
        :param plane_name: Name of the plane
        :param edge_index: Edge index on the plane
        :param freedom: Dictionary with SDK enum values for x, y, z, rx, ry, rz
        :param stiffness: Dictionary with stiffness values
        """
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
