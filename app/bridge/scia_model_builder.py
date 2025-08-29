"""
Module for constructing SCIA models using a concrete implementation of the SciaModelBuilder interface.

This module acts as the bridge between the VIKTOR SDK and the core logic from the src layer.
"""

import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

from src.integrations.scia_integration.scia_model import define_complete_bridge_model
from src.integrations.scia_integration.scia_model_interface import (
    SciaAnalysis,
    SciaCombinationType,
    SciaFile,
    SciaLoadCase,
    SciaLoadCombination,
    SciaLoadGroup,
    SciaModelBuilder,
)

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.core import File
    from viktor.external import scia
    from viktor.external.scia import OutputFileParser

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock scia module for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    File = None  # type: ignore[misc,assignment]
    OutputFileParser = None  # type: ignore[misc,assignment]
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
        self.load_combinations: dict[str, scia.LoadCombination] = {}  # Track load combinations
        self.result_classes: dict[str, scia.ResultClass] = {}  # Track result classes

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

        for load_case in load_case_factors:
            # Check if this load case is in our stored load cases
            found_in_stored = False
            for stored_case in self.load_cases.values():
                if stored_case == load_case:
                    found_in_stored = True
                    break
            if not found_in_stored:
                pass

        # Convert load_case_factors to the format expected by SCIA
        scia_load_cases = dict(load_case_factors)

        # Create the combination with load cases included
        combination = self.model.create_load_combination(name, combo_class, scia_load_cases, description=description)
        self.load_combinations[name] = combination
        return combination

    def create_result_class(
        self,
        name: str,
        combinations: list[scia.LoadCombination] | None = None,
        nonlinear_combinations: list[Any] | None = None,
    ) -> scia.ResultClass:
        """Creates a result class in the SCIA model."""
        # Ensure we have at least one combination or nonlinear combination
        if not combinations and not nonlinear_combinations:
            raise ValueError("A result class should at least consist of 'combinations' or 'nonlinear_combinations'.")

        # Create the result class with combinations
        if combinations:
            result_class = self.model.create_result_class(name, combinations=combinations)
        else:
            # Create with nonlinear combinations (future implementation)
            result_class = self.model.create_result_class(name, nonlinear_combinations=nonlinear_combinations)

        self.result_classes[name] = result_class
        return result_class

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

    def run_analysis(self, xml_file: File, def_file: File, esa_template: File) -> SciaAnalysis:
        """Runs the SCIA analysis and returns the analysis object."""
        if not VIKTOR_AVAILABLE or scia is None:
            raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")
        scia_analysis = scia.SciaAnalysis(xml_file, def_file, esa_template)
        scia_analysis.execute(timeout=600)
        return scia_analysis

    def extract_analysis_results(self, analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts results from a completed SCIA analysis."""
        if not hasattr(analysis, "get_xml_output_file"):
            raise ValueError("Invalid SCIA analysis object - missing get_xml_output_file method")

        try:
            # Get the XML output file containing results
            xml_output_file = analysis.get_xml_output_file()

            # Extract various result types
            results = {
                "xml_output_file": xml_output_file,
                "displacements": self.get_displacement_results(analysis),
                "internal_forces": self.get_internal_force_results(analysis),
                "reactions": self.get_reaction_results(analysis),
                "stresses": self.get_stress_results(analysis),
                "analysis_status": self.get_analysis_status(analysis),
                "xml_parsing": self.parse_xml_results(xml_output_file),
            }

            # Add units mapping for downstream consumers
            from src.integrations.scia_integration.scia_results import build_units_mapping

            units_mapping = build_units_mapping(results)
            results["units"] = units_mapping

        except Exception as e:
            raise ValueError(f"Failed to extract SCIA analysis results: {e!s}")
        else:
            return results

    def _try_get_table_result(self, xml_output_file: File, table_name: str) -> dict[str, object] | None:
        """Try to get a table result from the XML output file."""
        try:
            table_data = OutputFileParser.get_result(xml_output_file, table_name)
        except Exception:
            return None
        else:
            return {
                "status": "success",
                "data": table_data,
                "message": f"Results extracted successfully from '{table_name}'",
                "table_name": table_name,
            }

    def _try_parse_table(self, fresh_xml_content: File, table_name: str) -> dict[str, object]:
        """Try to parse a specific table from the XML content."""
        # Check if this is a result class table that needs custom parsing
        if "Resultaatklasses" in table_name:
            return self._parse_result_class_table(fresh_xml_content, table_name)
        try:
            table_data = OutputFileParser.get_result(fresh_xml_content, table_name)
        except Exception as e:
            return {
                "status": "not_found",
                "message": f"Table '{table_name}' not found in XML output",
                "error": str(e),
            }
        else:
            return {
                "status": "success",
                "data": table_data,
                "message": f"Successfully extracted {table_name}",
            }

    def get_displacement_results(self, analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts displacement results from SCIA analysis."""
        try:
            xml_output_file = analysis.get_xml_output_file()

            # Actual table names from SCIA output
            displacement_table_names = ["2D-verplaatsing", "1D-vervormingen", "Displacements", "Displacement"]

            for table_name in displacement_table_names:
                result = self._try_get_table_result(xml_output_file, table_name)
                if result:
                    return result

            return {
                "status": "not_found",
                "message": f"Displacement results not found. Tried: {', '.join(displacement_table_names)}",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to extract displacement results: {e}",
                "error": str(e),
            }

    def get_internal_force_results(self, _analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts internal force results from SCIA analysis."""
        try:
            xml_output_file = _analysis.get_xml_output_file()

            # Actual table names from SCIA output
            internal_force_table_names = [
                "Interne 2D-krachten basis",
                "Interne 2D-krachten elementair",
                "Interne 1D-krachten",
                "2D internal forces",
                "Internal forces",
            ]

            for table_name in internal_force_table_names:
                result = self._try_get_table_result(xml_output_file, table_name)
                if result:
                    return result

            return {
                "status": "not_found",
                "message": f"Internal force results not found. Tried: {', '.join(internal_force_table_names)}",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to extract internal force results: {e}",
                "error": str(e),
            }

    def get_reaction_results(self, _analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts reaction force results from SCIA analysis."""
        try:
            xml_output_file = _analysis.get_xml_output_file()

            # Common reaction table names (may not be present in this analysis)
            reaction_table_names = ["Reactions", "Reaction", "Support reactions", "Support reaction"]

            for table_name in reaction_table_names:
                result = self._try_get_table_result(xml_output_file, table_name)
                if result:
                    return result

            return {
                "status": "not_found",
                "message": f"Reaction results not found. Tried: {', '.join(reaction_table_names)}",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to extract reaction results: {e}",
                "error": str(e),
            }

    def get_stress_results(self, _analysis: SciaAnalysis) -> dict[str, object]:
        """Extracts stress results from SCIA analysis."""
        try:
            xml_output_file = _analysis.get_xml_output_file()

            # Common stress table names (may not be present in this analysis)
            stress_table_names = ["Stresses", "Stress", "Stress results", "Stress analysis"]

            for table_name in stress_table_names:
                result = self._try_get_table_result(xml_output_file, table_name)
                if result:
                    return result

            return {
                "status": "not_found",
                "message": f"Stress results not found. Tried: {', '.join(stress_table_names)}",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to extract stress results: {e}",
                "error": str(e),
            }

    def get_analysis_status(self, analysis: SciaAnalysis) -> dict[str, Any]:
        """Gets the status and metadata of the SCIA analysis."""
        try:
            # Check if analysis has been executed
            has_results = hasattr(analysis, "get_xml_output_file")

            status: dict[str, Any] = {
                "executed": has_results,
                "has_results": has_results,
                "error_message": None,
            }

            # Try to get more detailed status information if available
            if hasattr(analysis, "status"):
                status["detailed_status"] = analysis.status
            if hasattr(analysis, "error"):
                status["error_message"] = analysis.error

            return status  # noqa: TRY300

        except Exception as e:
            return {
                "executed": False,
                "has_results": False,
                "error_message": str(e),
            }

    def _read_xml_content(self, xml_output_file: SciaFile) -> bytes | None:
        """Read XML content from the output file."""
        try:
            if hasattr(xml_output_file, "getvalue"):
                return xml_output_file.getvalue()
            if hasattr(xml_output_file, "read"):
                if hasattr(xml_output_file, "seek"):
                    xml_output_file.seek(0)
                content = xml_output_file.read()
                if hasattr(xml_output_file, "seek"):
                    xml_output_file.seek(0)  # Reset position
                return content
            return None  # noqa: TRY300
        except Exception:
            return None

    def _parse_table_details(self, table: ET.Element) -> dict[str, Any] | None:
        """Parse details for a single table."""
        table_name = table.get("name")
        if not table_name:
            return None

        # Check for data rows
        data_rows = table.findall(".//row")
        has_data = bool(data_rows)

        # Check for object elements (metadata)
        objects = table.findall(".//obj")
        has_objects = bool(objects)

        return {
            "name": table_name,
            "has_data": has_data,
            "has_objects": has_objects,
            "data_rows": len(data_rows),
            "objects": len(objects),
        }

    def _discover_available_tables(self, xml_output_file: SciaFile) -> tuple[list[str], list[dict[str, Any]]]:  # noqa: C901
        """Discover available tables in the XML output file."""
        available_tables: list[str] = []
        table_details: list[dict[str, Any]] = []

        xml_content = self._read_xml_content(xml_output_file)
        if not xml_content:
            return available_tables, table_details

        try:
            # Parse XML to find table names and check if they have data.
            root = ET.fromstring(xml_content)

            # Handle XML namespace if present
            namespace = ""
            if root.tag.startswith("{"):
                namespace = root.tag.split("}")[0] + "}"

            # Parse XML tables (SCIA might or might not use namespaces)
            # Try multiple search strategies to find all tables
            all_tables = []

            # Strategy 1: Direct search (with and without namespace)
            all_tables.extend(root.findall(".//table"))
            if namespace:
                all_tables.extend(root.findall(f".//{namespace}table"))

            # Strategy 2: Search within containers (with and without namespace)
            for container in root.findall(".//container"):
                all_tables.extend(container.findall(".//table"))
                if namespace:
                    all_tables.extend(container.findall(f".//{namespace}table"))

            if namespace:
                for container in root.findall(f".//{namespace}container"):
                    all_tables.extend(container.findall(".//table"))
                    all_tables.extend(container.findall(f".//{namespace}table"))

            # Remove duplicates and process
            seen_tables = set()
            for table in all_tables:
                table_name = table.get("name", "")
                if table_name and table_name not in seen_tables:
                    seen_tables.add(table_name)
                    table_detail = self._parse_table_details(table)
                    if table_detail:
                        available_tables.append(table_detail["name"])
                        table_details.append(table_detail)

        except Exception as e:
            # If XML parsing fails, add error info but continue with default tables
            table_details.append(
                {
                    "name": "XML_PARSING_ERROR",
                    "error": str(e),
                    "has_data": False,
                    "has_objects": False,
                    "data_rows": 0,
                    "objects": 0,
                }
            )

        return available_tables, table_details

    def _get_result_table_names(self, available_tables: list[str]) -> list[str]:
        """Get the list of result table names to try."""
        # First, add any tables that look like result classes from available tables
        dynamic_result_tables = [table for table in available_tables if "resultaat" in table.lower() or "result" in table.lower()]

        # List of common result tables to try to extract (with variations)
        static_result_tables = [
            # Actual table names from SCIA output
            "2D-verplaatsing",
            "1D-vervormingen",
            "Interne 2D-krachten basis",
            "Interne 2D-krachten elementair",
            "Interne 1D-krachten",
            # Result Classes (exact names from XML output)
            "Resultaatklasses - ULS",
            "Resultaatklasses - SLS kar",
            "Resultaatklasses - SLS freq",
            "Resultaatklasses - SLS qp",
            "Resultaatklasses - FAT",
            "Resultaatklasses - All ULS",
            "Resultaatklasses - All SLS",
            "Resultaatklasses - All ULS+SLS",
            # Fallback names
            "Displacements",
            "Displacement",
            "2D internal forces",
            "Internal forces",
            "Internal Forces",
            "Reactions",
            "Reaction",
            "Stresses",
            "Stress",
            "Result classes - UGT",
            "Result classes - ULS",
            "Result classes - SLS",
            "Result classes",
            "UGT",
            "ULS",
            "SLS",
        ]
        result_tables = [*dynamic_result_tables, *static_result_tables]

        # Add discovered tables to the list
        for table_name in available_tables:
            if table_name not in result_tables:
                result_tables.append(table_name)

        return result_tables

    def _create_fresh_xml_content(self, xml_output_file: SciaFile) -> SciaFile:
        """Create a fresh BytesIO object for OutputFileParser."""
        from io import BytesIO

        fresh_xml_content: SciaFile

        if hasattr(xml_output_file, "getvalue"):
            fresh_xml_content = BytesIO(xml_output_file.getvalue())
        elif hasattr(xml_output_file, "read"):
            if hasattr(xml_output_file, "seek"):
                xml_output_file.seek(0)
            fresh_xml_content = BytesIO(xml_output_file.read())
            if hasattr(xml_output_file, "seek"):
                xml_output_file.seek(0)  # Reset position
        else:
            fresh_xml_content = xml_output_file

        return fresh_xml_content

    def _parse_result_class_table(self, xml_content: File, table_name: str) -> dict[str, object]:  # noqa: C901, PLR0912
        """Custom parser for result class tables with obj/p2 structure."""
        try:
            # Debug: Log that we're entering the custom parser
            # Entering custom parser for result class table

            # Read XML content
            xml_bytes = self._read_xml_content(xml_content)
            if not xml_bytes:
                return {
                    "status": "error",
                    "message": f"Could not read XML content for {table_name}",
                    "error": "Empty XML content",
                }

            # Parse XML
            root = ET.fromstring(xml_bytes)

            # Handle XML namespace if present
            namespace = ""
            if root.tag.startswith("{"):
                namespace = root.tag.split("}")[0] + "}"

            # Find the specific table - try multiple search strategies
            table_element = None
            found_tables = []

            # Strategy 1: Direct search (with and without namespace)
            for table in root.findall(".//table"):
                table_name_attr = table.get("name", "")
                found_tables.append(table_name_attr)
                if table_name_attr == table_name:
                    table_element = table
                    break

            if namespace and table_element is None:
                for table in root.findall(f".//{namespace}table"):
                    table_name_attr = table.get("name", "")
                    if table_name_attr not in found_tables:
                        found_tables.append(table_name_attr)
                    if table_name_attr == table_name:
                        table_element = table
                        break

            # Strategy 2: If not found, try searching within containers
            if table_element is None:
                for container in root.findall(".//container"):
                    for table in container.findall(".//table"):
                        table_name_attr = table.get("name", "")
                        if table_name_attr not in found_tables:
                            found_tables.append(table_name_attr)
                        if table_name_attr == table_name:
                            table_element = table
                            break
                    if table_element is not None:
                        break

            # Strategy 3: If namespace exists, try containers with namespace
            if namespace and table_element is None:
                for container in root.findall(f".//{namespace}container"):
                    for table in container.findall(".//table"):
                        table_name_attr = table.get("name", "")
                        if table_name_attr not in found_tables:
                            found_tables.append(table_name_attr)
                        if table_name_attr == table_name:
                            table_element = table
                            break
                    if table_element is not None:
                        break

                    for table in container.findall(f".//{namespace}table"):
                        table_name_attr = table.get("name", "")
                        if table_name_attr not in found_tables:
                            found_tables.append(table_name_attr)
                        if table_name_attr == table_name:
                            table_element = table
                            break
                    if table_element is not None:
                        break

            if table_element is None:
                return {
                    "status": "not_found",
                    "message": f"Table '{table_name}' not found in XML",
                    "error": f"Cannot find table '{table_name}' in output XML. Found tables: {found_tables[:10]}",
                }

            # Extract result class data
            result_data = self._extract_result_class_data(table_element)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to parse result class table {table_name}",
                "error": str(e),
            }
        else:
            return {
                "status": "success",
                "data": result_data,
                "message": f"Successfully parsed result class table {table_name}",
            }

    def _extract_result_class_data(self, table_element: ET.Element) -> dict[str, Any]:  # noqa: C901, PLR0912
        """Extract data from a result class table element."""
        result_data: dict[str, Any] = {
            "table_name": table_element.get("name", "Unknown"),
            "load_combinations": [],
            "metadata": {},
        }

        # Detect namespace from the table element
        namespace = ""
        if table_element.tag.startswith("{"):
            namespace = table_element.tag.split("}")[0] + "}"

        # Find the main obj element (should be the result class definition)
        main_obj = table_element.find(".//obj")
        if main_obj is None and namespace:
            main_obj = table_element.find(f".//{namespace}obj")

        result_data["debug_obj_found"] = main_obj is not None

        if main_obj is not None:
            # Extract metadata from p0 and p1 elements
            p0_elem = main_obj.find("p0")
            if p0_elem is None and namespace:
                p0_elem = main_obj.find(f"{namespace}p0")

            p1_elem = main_obj.find("p1")
            if p1_elem is None and namespace:
                p1_elem = main_obj.find(f"{namespace}p1")

            if p0_elem is not None:
                result_data["metadata"]["name"] = p0_elem.get("v", "")
            if p1_elem is not None:
                result_data["metadata"]["unique_id"] = p1_elem.get("v", "")

            # Extract load combinations from p2 table
            p2_element = main_obj.find("p2")
            if p2_element is None and namespace:
                p2_element = main_obj.find(f"{namespace}p2")

            result_data["debug_p2_found"] = p2_element is not None

            if p2_element is not None:
                # Extract load combination rows - try different search strategies
                rows = p2_element.findall(".//row")
                if not rows and namespace:
                    rows = p2_element.findall(f".//{namespace}row")
                if not rows:
                    rows = p2_element.findall("row")  # Direct children only
                if not rows and namespace:
                    rows = p2_element.findall(f"{namespace}row")  # Direct children with namespace

                result_data["debug_row_count"] = len(rows)

                for row in rows:
                    combo_data = {}

                    # Extract load combination data from p1 element
                    p1_elem = row.find("p1")
                    if p1_elem is None and namespace:
                        p1_elem = row.find(f"{namespace}p1")

                    if p1_elem is not None:
                        combo_data["id"] = p1_elem.get("i", "")
                        combo_data["name"] = p1_elem.get("n", "")

                    # Extract other parameters (p6, p7, p8, p9)
                    for param in ["p6", "p7", "p8", "p9"]:
                        param_elem = row.find(param)
                        if param_elem is None and namespace:
                            param_elem = row.find(f"{namespace}{param}")

                        if param_elem is not None:
                            combo_data[param] = param_elem.get("v", "")

                    if combo_data:
                        result_data["load_combinations"].append(combo_data)
            else:
                result_data["debug_row_count"] = 0
        else:
            result_data["debug_p2_found"] = False
            result_data["debug_row_count"] = 0

        return result_data

    def parse_xml_results(self, xml_output_file: SciaFile) -> dict[str, Any]:
        """Parses the XML output file to extract structured results."""
        # parse_xml_results method called
        try:
            # Discover available tables
            available_tables, table_details = self._discover_available_tables(xml_output_file)
            # Discovered available tables

            # Get result table names
            result_tables = self._get_result_table_names(available_tables)

            # Create fresh XML content for parsing
            fresh_xml_content = self._create_fresh_xml_content(xml_output_file)

            # Parse all tables
            parsed_results = {}
            # Processing result tables
            for table_name in result_tables:
                # About to parse table
                parsed_results[table_name] = self._try_parse_table(fresh_xml_content, table_name)

            return {
                "status": "success",
                "parsed_tables": parsed_results,
                "available_tables": available_tables,
                "table_details": table_details,
                "total_tables_found": sum(1 for r in parsed_results.values() if r["status"] == "success"),
                "total_tables_attempted": len(result_tables),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to parse XML results: {e}",
                "error": str(e),
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


def run_scia_analysis(params: Any, template_path: Path) -> SciaAnalysis:  # noqa: ANN401
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


def _extract_xml_output_for_caching(analysis: SciaAnalysis) -> bytes | None:
    """
    Extract XML output from analysis for caching purposes.

    :param analysis: The SCIA analysis object.
    :return: XML output as bytes or None if extraction fails.
    """
    try:
        xml_output_file = analysis.get_xml_output_file()
        if xml_output_file:
            if hasattr(xml_output_file, "getvalue"):
                return xml_output_file.getvalue()
            if hasattr(xml_output_file, "read"):
                xml_output_file.seek(0)
                content = xml_output_file.read()
                xml_output_file.seek(0)  # Reset position
                return content
            return xml_output_file
    except Exception:
        # If XML output extraction fails, continue without it
        pass
    return None


def _extract_esa_model_for_caching(analysis: SciaAnalysis) -> bytes | None:
    """
    Extract ESA model from analysis for caching purposes.

    :param analysis: The SCIA analysis object.
    :return: ESA model as bytes or None if extraction fails.
    """
    try:
        # Try to get the updated ESA model
        esa_model_file = analysis.get_updated_esa_model(as_file=True)

        # If that fails, try alternative method
        if esa_model_file is None and hasattr(analysis, "get_esa_model"):
            esa_model_file = analysis.get_esa_model(as_file=True)

        # Extract content from the file
        if esa_model_file:
            content = _extract_content_from_file(esa_model_file)
            if content:
                return content

        # If no ESA model file obtained, try without as_file parameter
        try:
            esa_model_file = analysis.get_updated_esa_model()
            if esa_model_file:
                if hasattr(esa_model_file, "getvalue"):
                    return esa_model_file.getvalue()
                if hasattr(esa_model_file, "read"):
                    esa_model_file.seek(0)
                    content = esa_model_file.read()
                    esa_model_file.seek(0)
                    return content
                return esa_model_file
        except Exception:
            pass

    except Exception:
        pass

    return None


def _extract_content_from_file(file_obj: Any) -> bytes | None:  # noqa: ANN401
    """
    Extract content from a file object, handling different types.

    :param file_obj: The file object to extract content from.
    :return: File content as bytes or None if extraction fails.
    """
    content = None
    try:
        if isinstance(file_obj, bytes):
            content = file_obj
        elif hasattr(file_obj, "getvalue"):
            content = file_obj.getvalue()
        elif hasattr(file_obj, "read"):
            file_obj.seek(0)
            content = file_obj.read()
            file_obj.seek(0)  # Reset position
        else:
            content = file_obj
    except Exception:
        content = None

    return content


def _run_scia_analysis_with_builder(params: Any, template_path: Path) -> tuple[SciaAnalysis, dict[str, object]]:  # noqa: ANN401
    """
    Run SCIA analysis using the builder interface and extract basic results.

    :param params: The bridge parameters.
    :param template_path: The path to the ESA template file.
    :return: Tuple of (analysis object, basic results dictionary).
    """
    # Create builder and generate input files
    builder = ViktorSciaModelBuilder()
    define_complete_bridge_model(builder, params)
    xml_file, def_file = builder.generate_xml_input()
    esa_template = File.from_path(template_path)

    # Run the analysis using the builder interface
    analysis = builder.run_analysis(xml_file, def_file, esa_template)

    # Extract results using the builder interface
    results = builder.extract_analysis_results(analysis)

    return analysis, results


def get_scia_analysis_results(params: Any, template_path: Path) -> dict[str, Any]:  # noqa: ANN401
    """
    Run SCIA analysis and extract results.

    :param params: The bridge parameters.
    :param template_path: The path to the ESA template file.
    :return: Dictionary containing extracted analysis results.
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    # Run analysis and get basic results
    analysis, results = _run_scia_analysis_with_builder(params, template_path)

    # Extract additional data for caching
    results["xml_output"] = _extract_xml_output_for_caching(analysis)

    # Extract ESA model
    esa_model = _extract_esa_model_for_caching(analysis)
    results["esa_model"] = esa_model

    # Add summary information
    results["summary"] = {
        "analysis_status": results.get("analysis_status", "unknown"),
        "xml_parsing": results.get("xml_parsing", {}),
        "has_esa_model": esa_model is not None,
    }

    return results
