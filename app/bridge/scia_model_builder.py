"""
Module for constructing SCIA models using a concrete implementation of the SciaModelBuilder interface.

This module acts as the bridge between the VIKTOR SDK and the core logic from the src layer.
"""

from io import BytesIO
from pathlib import Path
from typing import Any, Literal

from src.integrations.scia_integration.scia_model import define_complete_bridge_model
from src.integrations.scia_integration.scia_model_interface import (
    SciaCombinationType,
    SciaLoadCase,
    SciaLoadCombination,
    SciaLoadGroup,
    SciaModelBuilder,
)
from src.integrations.scia_integration.scia_results import get_result_summary, validate_analysis_results

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.core import File
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock scia module for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    File = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False


class ViktorSciaModelBuilder(SciaModelBuilder):
    """
    A concrete implementation of the SciaModelBuilder protocol using the VIKTOR SDK.

    This class maintains the state of the SCIA model being built, including created
    nodes, materials, plates, and load infrastructure.
    """

    def __init__(self) -> None:
        """Initializes the ViktorSciaModelBuilder."""
        if not VIKTOR_AVAILABLE or scia is None:
            raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")
        self.model: scia.Model = scia.Model()
        self.materials: dict[str, scia.Material] = {}
        self.nodes: dict[str, scia.Node] = {}
        self.plates: dict[str, scia.Plane] = {}
        self.load_groups: dict[str, scia.LoadGroup] = {}
        self.load_cases: dict[str, scia.LoadCase] = {}
        self.surface_loads: dict[str, scia.FreeSurfaceLoad] = {}  # Track surface loads

    def create_material(self, name: str, material_id: int = 0) -> scia.Material:
        """Creates a material and stores it."""
        material = scia.Material(material_id, name)
        self.materials[name] = material
        return material

    def create_node(self, name: str, x: float, y: float, z: float) -> scia.Node:
        """Creates a node and stores it."""
        node = self.model.create_node(name, x, y, z)
        self.nodes[name] = node
        return node

    def create_plate(
        self,
        name: str,
        corner_node_names: list[str],
        thickness: float,
        material_name: str,
    ) -> scia.Plane:
        """Creates a plate (plane) and stores it."""
        if material_name not in self.materials:
            raise ValueError(f"Material '{material_name}' not found.")
        material = self.materials[material_name]

        corner_nodes = []
        for node_name in corner_node_names:
            if node_name not in self.nodes:
                raise ValueError(f"Node '{node_name}' not found.")
            corner_nodes.append(self.nodes[node_name])

        plate = self.model.create_plane(
            corner_nodes,
            thickness,
            name=name,
            material=material,
        )
        self.plates[name] = plate
        return plate

    def create_load_group(
        self,
        name: str,
        load_option: Literal["PERMANENT", "VARIABLE", "ACCIDENTAL", "SEISMIC"],
        relation: Literal["STANDARD", "EXCLUSIVE", "TOGETHER"],
        load_type: str | None,
    ) -> SciaLoadGroup:
        """Creates a load group and stores it."""
        load_option_map = {
            "PERMANENT": scia.LoadGroup.LoadOption.PERMANENT,
            "VARIABLE": scia.LoadGroup.LoadOption.VARIABLE,
            "ACCIDENTAL": scia.LoadGroup.LoadOption.ACCIDENTAL,
            "SEISMIC": scia.LoadGroup.LoadOption.SEISMIC,
        }
        relation_map = {
            "STANDARD": scia.LoadGroup.RelationOption.STANDARD,
            "EXCLUSIVE": scia.LoadGroup.RelationOption.EXCLUSIVE,
            "TOGETHER": scia.LoadGroup.RelationOption.TOGETHER,
        }
        load_type_map = {
            "CAT_A": scia.LoadGroup.LoadTypeOption.CAT_A,
            "CAT_B": scia.LoadGroup.LoadTypeOption.CAT_B,
            "CAT_C": scia.LoadGroup.LoadTypeOption.CAT_C,
            "CAT_D": scia.LoadGroup.LoadTypeOption.CAT_D,
            "CAT_E": scia.LoadGroup.LoadTypeOption.CAT_E,
            "CAT_F": scia.LoadGroup.LoadTypeOption.CAT_F,
            "CAT_G": scia.LoadGroup.LoadTypeOption.CAT_G,
            "CAT_H": scia.LoadGroup.LoadTypeOption.CAT_H,
            "WIND": scia.LoadGroup.LoadTypeOption.WIND,
            "SNOW": scia.LoadGroup.LoadTypeOption.SNOW,
            "TEMPERATURE": scia.LoadGroup.LoadTypeOption.TEMPERATURE,
            "RAIN_WATER": scia.LoadGroup.LoadTypeOption.RAIN_WATER,
            "CONSTRUCTION_LOADS": scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS,
        }

        scia_load_type = None
        if load_type:
            scia_load_type = load_type_map[load_type]

        group = self.model.create_load_group(
            name,
            load_option_map[load_option],
            relation_map[relation],
            scia_load_type,
        )
        self.load_groups[name] = group
        return group

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
        """Creates a load case and stores it."""
        if group_name not in self.load_groups:
            raise ValueError(f"Load group '{group_name}' not found.")
        group = self.load_groups[group_name]

        load_case = None
        if case_type == "PERMANENT":
            if permanent_type is None:
                raise ValueError("Permanent load case type must be specified.")
            permanent_type_map = {
                "SELF_WEIGHT": scia.LoadCase.PermanentLoadType.SELF_WEIGHT,
                "STANDARD": scia.LoadCase.PermanentLoadType.STANDARD,
                "PRIMARY_EFFECT": scia.LoadCase.PermanentLoadType.PRIMARY_EFFECT,
            }
            load_case = self.model.create_permanent_load_case(name, description, group, permanent_type_map[permanent_type])
        elif case_type == "VARIABLE":
            if any(arg is None for arg in [variable_type, specification, duration]):
                raise ValueError("Variable load case requires type, specification, and duration.")
            variable_type_map = {"STATIC": scia.LoadCase.VariableLoadType.STATIC, "PRIMARY_EFFECT": scia.LoadCase.VariableLoadType.PRIMARY_EFFECT}
            spec_map = {
                "STANDARD": scia.LoadCase.Specification.STANDARD,
                "STATIC_WIND": scia.LoadCase.Specification.STATIC_WIND,
                "SNOW": scia.LoadCase.Specification.SNOW,
                "TEMPERATURE": scia.LoadCase.Specification.TEMPERATURE,
                "EARTHQUAKE": scia.LoadCase.Specification.EARTHQUAKE,
            }
            dur_map = {
                "INSTANTANEOUS": scia.LoadCase.Duration.INSTANTANEOUS,
                "SHORT": scia.LoadCase.Duration.SHORT,
                "MEDIUM": scia.LoadCase.Duration.MEDIUM,
                "LONG": scia.LoadCase.Duration.LONG,
            }
            load_case = self.model.create_variable_load_case(
                name,
                description,
                group,
                variable_type_map[variable_type],  # type: ignore[index]
                specification=spec_map[specification],  # type: ignore[index]
                duration=dur_map[duration],  # type: ignore[index]
            )
        else:
            raise ValueError(f"Unsupported load case type: {case_type}")

        self.load_cases[name] = load_case
        return load_case

    def create_surface_load(
        self,
        name: str,
        load_case_name: str,
        corner_points: list[tuple[float, float, float]],
        load_value: float,
    ) -> scia.FreeSurfaceLoad:
        """Creates a free surface load."""
        if load_case_name not in self.load_cases:
            raise ValueError(f"Load case '{load_case_name}' not found.")
        load_case = self.load_cases[load_case_name]

        if len(corner_points) != 4:
            raise ValueError(f"Exactly 4 corner points required for patch load, got {len(corner_points)}")
        points_2d = [(p[0], p[1]) for p in corner_points]

        surface_load = self.model.create_free_surface_load(
            name=name,
            load_case=load_case,
            direction=scia.FreeSurfaceLoad.Direction.Z,
            q1=load_value,
            points=points_2d,
            distribution=scia.FreeSurfaceLoad.Distribution.UNIFORM,
        )
        self.surface_loads[name] = surface_load
        return surface_load

    def create_line_load_on_plane(
        self,
        name: str,
        load_case_name: str,
        plane_name: str,
        edge_index: int,
        load_value: float,
    ) -> scia.LineForceSurface:
        """Creates a uniform line load on a plane edge."""
        if load_case_name not in self.load_cases:
            raise ValueError(f"Load case '{load_case_name}' not found for line load '{name}'.")
        if plane_name not in self.plates:
            raise ValueError(f"Plate '{plane_name}' not found for line load '{name}'.")

        load_case = self.load_cases[load_case_name]
        plane = self.plates[plane_name]

        return self.model.create_line_load_on_plane(
            name=name,
            edge=(plane, edge_index),
            p1=load_value,
            load_case=load_case,
            direction=scia.LineForceSurface.Direction.Z,
        )

    def create_free_line_load(  # noqa: PLR0913
        self,
        name: str,
        load_case_name: str,
        point_1: tuple[float, float],
        point_2: tuple[float, float],
        load_value: float,
        direction: Literal["X", "Y", "Z"] = "Z",
    ) -> scia.FreeLineLoad:
        """Creates a uniform free line load."""
        if load_case_name not in self.load_cases:
            raise ValueError(f"Load case '{load_case_name}' not found for line load '{name}'.")
        load_case = self.load_cases[load_case_name]

        dir_map = {"X": scia.FreeLineLoad.Direction.X, "Y": scia.FreeLineLoad.Direction.Y, "Z": scia.FreeLineLoad.Direction.Z}

        return self.model.create_free_line_load(
            name=name,
            p1=point_1,
            p2=point_2,
            q=load_value,
            load_case=load_case,
            direction=dir_map[direction],
        )

    def create_load_combination(
        self,
        name: str,
        combination_type: SciaCombinationType,
        load_case_factors: dict[SciaLoadCase, float],
        description: str,
    ) -> SciaLoadCombination:
        """Creates a load combination and stores it."""
        combo_type_map = {
            "ENVELOPE_ULTIMATE": scia.LoadCombination.Type.ENVELOPE_ULTIMATE,
            "ENVELOPE_SERVICEABILITY": scia.LoadCombination.Type.ENVELOPE_SERVICEABILITY,
            "LINEAR_ULTIMATE": scia.LoadCombination.Type.LINEAR_ULTIMATE,
            "LINEAR_SERVICEABILITY": scia.LoadCombination.Type.LINEAR_SERVICEABILITY,
            "EN_ULS_SET_B": scia.LoadCombination.Type.EN_ULS_SET_B,
            "EN_ULS_SET_C": scia.LoadCombination.Type.EN_ULS_SET_C,
            "EN_SLS_CHAR": scia.LoadCombination.Type.EN_SLS_CHAR,
            "EN_SLS_FREQ": scia.LoadCombination.Type.EN_SLS_FREQ,
            "EN_SLS_QUASI": scia.LoadCombination.Type.EN_SLS_QUASI,
            "EN_ACC_ONE": scia.LoadCombination.Type.EN_ACC_ONE,
            "EN_ACC_TWO": scia.LoadCombination.Type.EN_ACC_TWO,
            "EN_SEISMIC": scia.LoadCombination.Type.EN_SEISMIC,
        }
        combo_class = combo_type_map.get(combination_type.value)

        if combo_class is None:
            raise ValueError(f"Unsupported combination type: {combination_type}")

        combination = self.model.create_load_combination(name, combo_class, description)
        for load_case, factor in load_case_factors.items():
            combination.add_load_case(load_case, factor)
        return combination

    def create_line_support_on_plane(
        self,
        name: str,
        plane_name: str,
        edge_index: int,
        freedom: dict[str, str],
        stiffness: dict[str, float],
    ) -> scia.LineSupport:
        """Creates a line support on a plane edge."""
        if plane_name not in self.plates:
            raise ValueError(f"Plate '{plane_name}' not found for line support '{name}'.")
        plane = self.plates[plane_name]

        freedom_map = {
            "FREE": scia.LineSupport.Freedom.FREE,
            "RIGID": scia.LineSupport.Freedom.RIGID,
            "FLEXIBLE": scia.LineSupport.Freedom.FLEXIBLE,
        }

        return self.model.create_line_support_on_plane(
            name=name,
            edge=(plane, edge_index),
            x=freedom_map[freedom["x"]],
            y=freedom_map[freedom["y"]],
            z=freedom_map[freedom["z"]],
            rx=freedom_map[freedom["rx"]],
            ry=freedom_map[freedom["ry"]],
            rz=freedom_map[freedom["rz"]],
            stiffness_x=stiffness.get("stiffness_x"),
            stiffness_y=stiffness.get("stiffness_y"),
        )

    def get_model(self) -> scia.Model:
        """Returns the constructed SCIA model."""
        return self.model

    def generate_xml_input(self) -> tuple[BytesIO, BytesIO]:
        """Generates XML and DEF files from the SCIA model."""
        xml_file, def_file = self.model.generate_xml_input()
        return xml_file, def_file

    def run_analysis(self, xml_file: Any, def_file: Any, esa_template: Any) -> Any:
        """Runs the SCIA analysis and returns the analysis object."""
        if not VIKTOR_AVAILABLE or scia is None:
            raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")
        scia_analysis = scia.SciaAnalysis(xml_file, def_file, esa_template)
        scia_analysis.execute(timeout=600)
        return scia_analysis

    def extract_analysis_results(self, analysis: Any) -> dict[str, Any]:
        """Extracts results from a completed SCIA analysis."""
        if not hasattr(analysis, "get_xml_output_file"):
            raise ValueError("Invalid SCIA analysis object - missing get_xml_output_file method")

        try:
            # Get the XML output file containing results
            xml_output_file = analysis.get_xml_output_file()

            # Debug: Print analysis object structure
            print(f"[DEBUG] Analysis object type: {type(analysis)}")
            print(f"[DEBUG] Analysis object attributes: {[attr for attr in dir(analysis) if not attr.startswith('_')]}")
            print(f"[DEBUG] XML output file type: {type(xml_output_file)}")
            print(f"[DEBUG] XML output file size: {getattr(xml_output_file, 'size', 'unknown')}")

            # Extract various result types
            results = {
                "xml_output_file": xml_output_file,
                "displacements": self.get_displacement_results(analysis),
                "internal_forces": self.get_internal_force_results(analysis),
                "reactions": self.get_reaction_results(analysis),
                "stresses": self.get_stress_results(analysis),
                "analysis_status": self.get_analysis_status(analysis),
            }

            return results

        except Exception as e:
            raise ValueError(f"Failed to extract SCIA analysis results: {e!s}")

    def get_displacement_results(self, analysis: Any) -> dict[str, Any]:
        """Extracts displacement results from SCIA analysis."""
        # Debug: Explore analysis object for displacement data
        print(f"[DEBUG] Exploring displacement results...")
        print(f"[DEBUG] Analysis object: {analysis}")

        # TODO: Implement displacement extraction based on SCIA API
        # This will depend on the specific SCIA SDK methods available
        return {
            "status": "not_implemented",
            "message": "Displacement extraction to be implemented based on SCIA API",
            "debug_info": {
                "analysis_type": str(type(analysis)),
                "available_attrs": [attr for attr in dir(analysis) if not attr.startswith("_")],
            },
        }

    def get_internal_force_results(self, analysis: Any) -> dict[str, Any]:
        """Extracts internal force results from SCIA analysis."""
        # TODO: Implement internal force extraction based on SCIA API
        # This will depend on the specific SCIA SDK methods available
        return {
            "status": "not_implemented",
            "message": "Internal force extraction to be implemented based on SCIA API",
        }

    def get_reaction_results(self, analysis: Any) -> dict[str, Any]:
        """Extracts reaction force results from SCIA analysis."""
        # TODO: Implement reaction force extraction based on SCIA API
        # This will depend on the specific SCIA SDK methods available
        return {
            "status": "not_implemented",
            "message": "Reaction force extraction to be implemented based on SCIA API",
        }

    def get_stress_results(self, analysis: Any) -> dict[str, Any]:
        """Extracts stress results from SCIA analysis."""
        # TODO: Implement stress extraction based on SCIA API
        # This will depend on the specific SCIA SDK methods available
        return {
            "status": "not_implemented",
            "message": "Stress extraction to be implemented based on SCIA API",
        }

    def get_analysis_status(self, analysis: Any) -> dict[str, Any]:
        """Gets the status and metadata of the SCIA analysis."""
        try:
            # Check if analysis has been executed
            has_results = hasattr(analysis, "get_xml_output_file")

            # Debug: Print detailed analysis object info
            print(f"[DEBUG] Analysis status check:")
            print(f"[DEBUG] - Has get_xml_output_file: {has_results}")
            print(f"[DEBUG] - Has status attr: {hasattr(analysis, 'status')}")
            print(f"[DEBUG] - Has error attr: {hasattr(analysis, 'error')}")

            status = {
                "executed": has_results,
                "has_results": has_results,
                "error_message": None,
            }

            # Try to get more detailed status information if available
            if hasattr(analysis, "status"):
                status["detailed_status"] = analysis.status
                print(f"[DEBUG] - Status value: {analysis.status}")
            if hasattr(analysis, "error"):
                status["error_message"] = analysis.error
                print(f"[DEBUG] - Error value: {analysis.error}")

            return status

        except Exception as e:
            print(f"[DEBUG] Exception in get_analysis_status: {e}")
            return {
                "executed": False,
                "has_results": False,
                "error_message": str(e),
            }

    def parse_xml_results(self, xml_output_file: Any) -> dict[str, Any]:
        """Parses the XML output file to extract structured results."""
        # TODO: Implement XML parsing based on SCIA output format
        # This will require understanding the SCIA XML output structure
        return {
            "status": "not_implemented",
            "message": "XML parsing to be implemented based on SCIA output format",
            "file_size": getattr(xml_output_file, "size", 0) if xml_output_file else 0,
        }


# =============================================================================
# TOP-LEVEL BUILDER FUNCTIONS
# =============================================================================


def generate_bridge_xml_files(params: Any) -> tuple[BytesIO, BytesIO]:  # noqa: ANN401
    """
    Generate the XML and DEF files for a complete bridge model.

    :param params: The bridge parameters from the VIKTOR parametrization.
    :return: A tuple containing the XML and DEF files as BytesIO objects.
    """
    builder = ViktorSciaModelBuilder()
    define_complete_bridge_model(builder, params)
    return builder.generate_xml_input()


def setup_bridge_analysis(params: Any, template_path: Path) -> tuple[Any, Any, Any]:  # noqa: ANN401
    """
    Set up the SCIA analysis by generating input files and loading the template.

    :param params: The bridge parameters from the VIKTOR parametrization.
    :param template_path: The path to the ESA template file.
    :return: A tuple containing the XML file, DEF file, and ESA template file.
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")
    xml_file, def_file = generate_bridge_xml_files(params)
    esa_template = File.from_path(template_path)
    return xml_file, def_file, esa_template


def run_scia_analysis(params: Any, template_path: Path) -> scia.SciaAnalysis:  # noqa: ANN401
    """
    Run the complete SCIA analysis and return the analysis object.

    :param params: The bridge parameters.
    :param template_path: The path to the ESA template file.
    :return: The executed SCIA analysis object.
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")
    xml_file, def_file, esa_template = setup_bridge_analysis(params, template_path)
    scia_analysis = scia.SciaAnalysis(xml_file, def_file, esa_template)
    scia_analysis.execute(timeout=600)
    return scia_analysis


def get_scia_analysis_results(params: Any, template_path: Path) -> dict[str, Any]:  # noqa: ANN401
    """
    Run SCIA analysis and extract results.

    :param params: The bridge parameters.
    :param template_path: The path to the ESA template file.
    :return: Dictionary containing extracted analysis results.
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    # Create builder and generate input files
    builder = ViktorSciaModelBuilder()
    define_complete_bridge_model(builder, params)
    xml_file, def_file = builder.generate_xml_input()
    esa_template = File.from_path(template_path)

    # Run the analysis using the builder interface
    analysis = builder.run_analysis(xml_file, def_file, esa_template)

    # Extract results using the builder interface
    results = builder.extract_analysis_results(analysis)

    # Validate results
    is_valid, validation_messages = validate_analysis_results(results)
    if not is_valid:
        results["validation_errors"] = validation_messages

    # Add summary
    results["summary"] = get_result_summary(results)

    return results
