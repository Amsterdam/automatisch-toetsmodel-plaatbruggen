"""
SCIA definitions and interface module.

This module defines a formal interface (Protocol) for building a SCIA model.
This allows the `src` layer to define the logic for constructing a bridge model,
while the `app` layer provides the concrete implementation using the VIKTOR SDK.
This approach decouples the core logic from the specific SDK implementation.
"""

from enum import Enum
from io import BytesIO
from typing import Protocol, Union

# Type aliases for better type safety
SciaFile = Union[BytesIO, bytes]
SciaAnalysis = object  # This would be more specific if we had access to the actual SCIA types


class SciaCombinationType(Enum):
    """Enumeration for SCIA Load Combination types, aligned with the VIKTOR SDK."""

    ENVELOPE_ULTIMATE = "ENVELOPE_ULTIMATE"
    ENVELOPE_SERVICEABILITY = "ENVELOPE_SERVICEABILITY"
    LINEAR_ULTIMATE = "LINEAR_ULTIMATE"
    LINEAR_SERVICEABILITY = "LINEAR_SERVICEABILITY"
    EN_ULS_SET_B = "EN_ULS_SET_B"
    EN_ULS_SET_C = "EN_ULS_SET_C"
    EN_SLS_CHAR = "EN_SLS_CHAR"
    EN_SLS_FREQ = "EN_SLS_FREQ"
    EN_SLS_QUASI = "EN_SLS_QUASI"
    EN_ACC_ONE = "EN_ACC_ONE"
    EN_ACC_TWO = "EN_ACC_TWO"
    EN_SEISMIC = "EN_SEISMIC"


class SciaModelBuilder(Protocol):
    """Protocol defining the interface for SCIA model builders."""

    def create_material(self, name: str, material_id: int = 0) -> object:
        """Creates a material and stores it."""
        ...

    def create_node(self, name: str, x: float, y: float, z: float) -> object:
        """Creates a node and stores it."""
        ...

    def create_plate(
        self,
        name: str,
        corner_node_names: list[str],
        thickness: float,
        material_name: str,
    ) -> object:
        """Creates a plate (plane) and stores it."""
        ...

    def create_load_group(
        self,
        name: str,
        load_option: str,
        relation: str,
        load_type: str | None,
    ) -> object:
        """Creates a load group and stores it."""
        ...

    def create_load_case(
        self,
        name: str,
        description: str,
        group_name: str,
        case_type: str,
        permanent_type: str | None = None,
        variable_type: str | None = None,
        specification: str | None = None,
        duration: str | None = None,
    ) -> object:
        """Creates a load case and stores it."""
        ...

    def create_surface_load(
        self,
        name: str,
        load_case_name: str,
        corner_points: list[tuple[float, float, float]],
        load_value: float,
    ) -> object:
        """Creates a free surface load."""
        ...

    def create_line_load_on_plane(
        self,
        name: str,
        load_case_name: str,
        plane_name: str,
        edge_index: int,
        load_value: float,
    ) -> object:
        """Creates a uniform line load on a plane edge."""
        ...

    def create_free_line_load(
        self,
        name: str,
        load_case_name: str,
        point_1: tuple[float, float],
        point_2: tuple[float, float],
        load_value: float,
        direction: str = "Z",
    ) -> object:
        """Creates a uniform free line load."""
        ...

    def create_load_combination(
        self,
        name: str,
        combination_type: "SciaCombinationType",
        load_case_factors: dict[object, float],
        description: str,
    ) -> object:
        """Creates a load combination and stores it."""
        ...

    def create_result_class(
        self,
        name: str,
        combinations: list[object] | None = None,
        nonlinear_combinations: list[object] | None = None,
    ) -> object:
        """Creates a result class in the SCIA model."""
        ...

    def create_line_support_on_plane(
        self,
        name: str,
        plane_name: str,
        edge_index: int,
        freedom: dict[str, str],
        stiffness: dict[str, float],
    ) -> object:
        """Creates a line support on a plane edge."""
        ...

    def get_model(self) -> object:
        """Returns the constructed SCIA model."""
        ...

    def generate_xml_input(self) -> tuple[BytesIO, BytesIO]:
        """Generates XML and DEF files from the SCIA model."""
        ...

    def run_analysis(self, xml_file: SciaFile, def_file: SciaFile, esa_template: SciaFile) -> SciaAnalysis:
        """Runs the SCIA analysis and returns the analysis object."""
        ...

    def extract_analysis_results(self, analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts results from a completed SCIA analysis."""
        ...

    def get_displacement_results(self, analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts displacement results from SCIA analysis."""
        ...

    def get_internal_force_results(self, analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts internal force results from SCIA analysis."""
        ...

    def get_reaction_results(self, analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts reaction force results from SCIA analysis."""
        ...

    def get_stress_results(self, analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts stress results from SCIA analysis."""
        ...

    def get_analysis_status(self, analysis: SciaAnalysis) -> dict[str, object]:
        """Gets the status and metadata of the SCIA analysis."""
        ...

    def parse_xml_results(self, xml_output_file: SciaFile) -> dict[str, object]:
        """Parses the XML output file to extract structured results."""
        ...
