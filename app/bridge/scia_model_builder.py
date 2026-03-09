"""
Module for constructing SCIA models using a concrete implementation of the SciaModelBuilder interface.

This module acts as the bridge between the VIKTOR SDK and the core logic from the src layer.
"""

import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.integrations.scia_integration.model.scia_model import define_bridge_model_sections_on_plane, define_complete_bridge_model
from src.integrations.scia_integration.model.scia_model_interface import (
    SciaAnalysis,
    SciaFile,
    SciaLoadCase,
    SciaLoadCombination,
    SciaLoadGroup,
    SciaModelBuilder,
)
from src.integrations.scia_integration.scia_enums import (
    LineLoadDirection,
    LineSupportCSys,
    LineSupportFreedom,
    LoadCaseActionType,
    LoadCaseDuration,
    LoadCaseSpecification,
    LoadCombinationType,
    LoadGroupLoadType,
    LoadGroupOption,
    LoadGroupRelation,
    PermanentLoadType,
    VariableLoadType,
)

# Global VIKTOR imports with error handling for CI/testing environments
if TYPE_CHECKING:
    from viktor.core import File, progress_message
    from viktor.errors import UserError
    from viktor.external import scia
    from viktor.external.scia import OutputFileParser

    VIKTOR_AVAILABLE = True
else:
    try:
        from viktor.core import File, progress_message
        from viktor.errors import UserError
        from viktor.external import scia
        from viktor.external.scia import OutputFileParser

        VIKTOR_AVAILABLE = True
    except ImportError:
        # Mock scia module for environments without VIKTOR SDK
        scia = None  # type: ignore[misc,assignment]
        File = None  # type: ignore[misc,assignment]
        progress_message = None  # type: ignore[misc,assignment]
        OutputFileParser = None  # type: ignore[misc,assignment]
        UserError = Exception  # type: ignore[misc,assignment]
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
        mesh_setup = scia.object.MeshSetup(average_1d=0.2, average_2d=0.2, division_2d_1d=50)
        self.model: scia.Model = scia.Model(mesh_setup=mesh_setup)
        self.materials: dict[str, scia.Material] = {}
        self.nodes: dict[str, scia.Node] = {}
        self.plates: dict[str, scia.Plane] = {}
        self.load_groups: dict[str, scia.LoadGroup] = {}
        self.load_cases: dict[str, scia.LoadCase] = {}
        self.surface_loads: dict[str, scia.FreeSurfaceLoad] = {}  # Track surface loads
        self.load_combinations: dict[str, scia.LoadCombination] = {}  # Track load combinations
        self.result_classes: dict[str, scia.ResultClass] = {}  # Track result classes
        self.integration_strips: dict[str, scia.IntegrationStrip] = {}  # Map custom_name -> strip object
        self.sections_on_plane: dict[str, scia.SectionOnPlane] = {}  # Map name -> SectionOnPlane object

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

    def create_integration_strip(
        self,
        plane: str,
        point_1: tuple[float, float, float],
        point_2: tuple[float, float, float],
        width: float,
        custom_name: str,
    ) -> scia.IntegrationStrip:
        """
        Creates an integration strip on a plane and stores it with custom name.

        Integration strips are used to extract integrated forces and stresses
        across a defined strip width on a plane element.

        Uses workaround to set custom name via _name attribute after creation.

        :param plane: Name of the plane to create the strip on
        :param point_1: Start point (x, y, z) coordinates in [m]
        :param point_2: End point (x, y, z) coordinates in [m]
        :param width: Width of the integration strip in [m]
        :param custom_name: Custom name for the strip (e.g., 'strip_Z1_1_X_1')
        :return: Created IntegrationStrip object
        """
        # Get the plane object from stored plates
        if plane not in self.plates:
            raise ValueError(f"Plane '{plane}' not found in model. Create the plane first.")

        plane_obj = self.plates[plane]

        # Create the SCIA integration strip (SDK generates default name)
        integration_strip = self.model.create_integration_strip(
            plane=plane_obj,
            point_1=point_1,
            point_2=point_2,
            width=width,
        )

        # Workaround: Set custom name via private _name attribute
        if hasattr(integration_strip, "_name"):
            integration_strip._name = custom_name  # noqa: SLF001

        # Store strip with custom name
        self.integration_strips[custom_name] = integration_strip

        return integration_strip

    def create_section_on_plane(
        self,
        point_1: tuple[float, float, float],
        point_2: tuple[float, float, float],
        *,
        name: str,
        draw: Any | None = None,
        direction_of_cut: tuple[float, float, float] | None = None,
    ) -> scia.SectionOnPlane:
        """
        Creates a section on a 2D-member plane and stores it.

        :param point_1: Start position (x, y, z) in [m]
        :param point_2: End position (x, y, z) in [m]
        :param name: Name shown in SCIA (e.g. 'sec_Z1-1_x_nr-1')
        :param draw: Plane in which the section is drawn (default: Z_DIRECTION)
        :param direction_of_cut: In-plane cut direction vector (default: (0, 0, 1))
        :return: Created SectionOnPlane object
        """
        kwargs: dict[str, Any] = {
            "point_1": point_1,
            "point_2": point_2,
            "name": name,
        }
        if draw is not None:
            kwargs["draw"] = draw
        if direction_of_cut is not None:
            kwargs["direction_of_cut"] = direction_of_cut

        section = self.model.create_section_on_plane(**kwargs)

        # Workaround: Set custom name via private _name attribute (same as integration strips)
        if hasattr(section, "_name"):
            section._name = name  # noqa: SLF001

        self.sections_on_plane[name] = section
        return section

    def create_load_group(
        self,
        name: str,
        load_option: LoadGroupOption,
        relation: LoadGroupRelation,
        load_type: LoadGroupLoadType | None,
    ) -> SciaLoadGroup:
        """
        Creates a load group and stores it.

        :param name: Name of the load group
        :param load_option: Load option enum (PERMANENT, VARIABLE, ACCIDENTAL, SEISMIC)
        :param relation: Relation enum (STANDARD, EXCLUSIVE, TOGETHER)
        :param load_type: Optional load type enum
        :return: Created load group
        """
        # Extract SDK enums from bridge enums
        sdk_load_option = load_option.value
        sdk_relation = relation.value
        sdk_load_type = load_type.value if load_type else None

        group = self.model.create_load_group(
            name,
            sdk_load_option,
            sdk_relation,
            sdk_load_type,
        )
        self.load_groups[name] = group
        return group

    def create_load_case(  # noqa: PLR0913
        self,
        name: str,
        description: str,
        group_name: str,
        case_type: LoadCaseActionType,
        permanent_type: PermanentLoadType | None = None,
        variable_type: VariableLoadType | None = None,
        specification: LoadCaseSpecification | None = None,
        duration: LoadCaseDuration | None = None,
    ) -> SciaLoadCase:
        """
        Creates a load case and stores it.

        :param name: Name of the load case
        :param description: Description of the load case
        :param group_name: Name of the load group this case belongs to
        :param case_type: Action type enum (PERMANENT or VARIABLE)
        :param permanent_type: Permanent load type enum
        :param variable_type: Variable load type enum
        :param specification: Load specification enum
        :param duration: Load duration enum
        :return: Created load case
        """
        if group_name not in self.load_groups:
            raise ValueError(f"Load group '{group_name}' not found.")
        group = self.load_groups[group_name]

        # Check if permanent type
        is_permanent = case_type == LoadCaseActionType.PERMANENT

        if is_permanent:
            if permanent_type is None:
                raise ValueError("Permanent load case type must be specified.")
            sdk_permanent_type = permanent_type.value
            load_case = self.model.create_permanent_load_case(name, description, group, sdk_permanent_type)
        else:
            if any(arg is None for arg in [variable_type, specification, duration]):
                raise ValueError("Variable load case requires type, specification, and duration.")
            sdk_variable_type = variable_type.value  # type: ignore[union-attr]
            sdk_specification = specification.value  # type: ignore[union-attr]
            sdk_duration = duration.value  # type: ignore[union-attr]
            load_case = self.model.create_variable_load_case(
                name,
                description,
                group,
                sdk_variable_type,
                specification=sdk_specification,
                duration=sdk_duration,
            )

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
        direction: LineLoadDirection = LineLoadDirection.Z,  # type: ignore[assignment]
    ) -> scia.FreeLineLoad:
        """
        Creates a uniform free line load.

        :param name: Name of the line load
        :param load_case_name: Name of the load case
        :param point_1: First point (x, y)
        :param point_2: Second point (x, y)
        :param load_value: Load value
        :param direction: Direction enum (X, Y, or Z), defaults to Z
        :return: Created free line load
        """
        if load_case_name not in self.load_cases:
            raise ValueError(f"Load case '{load_case_name}' not found for line load '{name}'.")
        load_case = self.load_cases[load_case_name]

        # Extract SDK enum from bridge enum
        sdk_direction = direction.value

        return self.model.create_free_line_load(
            name=name,
            p1=point_1,
            p2=point_2,
            q=load_value,
            load_case=load_case,
            direction=sdk_direction,
        )

    def create_thermal_surface_load(
        self,
        name: str,
        load_case_name: str,
        plane_name: str,
        top_delta: float,
        bottom_delta: float,
    ) -> scia.ThermalSurfaceLoad:
        """
        Creates a thermal (temperature) surface load on a plane.

        This method applies a temperature gradient through the thickness of a plane element.
        The temperature distribution varies linearly from top_delta at the +Z surface to
        bottom_delta at the -Z surface, creating thermal stresses and deformations.

        :param name: Name of the thermal load
        :param load_case_name: Name of the load case
        :param plane_name: Name of the plane/plate to apply the load to
        :param top_delta: Temperature difference at +Z surface (°C)
        :param bottom_delta: Temperature difference at -Z surface (°C)
        :return: The created thermal surface load object
        :raises ValueError: If load case or plane not found
        """
        if load_case_name not in self.load_cases:
            raise ValueError(f"Load case '{load_case_name}' not found for thermal load '{name}'.")
        if plane_name not in self.plates:
            raise ValueError(f"Plate '{plane_name}' not found for thermal load '{name}'.")

        load_case = self.load_cases[load_case_name]
        plane = self.plates[plane_name]

        # Create the thermal surface load using VIKTOR SDK
        return self.model.create_thermal_surface_load(
            name=name,
            load_case=load_case,
            plane=plane,
            delta=None,
            top_delta=top_delta,
            bottom_delta=bottom_delta,
        )

    def create_load_combination(
        self,
        name: str,
        combination_type: LoadCombinationType,
        load_case_factors: dict[SciaLoadCase, float],
        description: str,
    ) -> SciaLoadCombination:
        """
        Creates a load combination and stores it.

        :param name: Name of the load combination
        :param combination_type: Combination type enum
        :param load_case_factors: Dictionary mapping load cases to their factors
        :param description: Description of the combination
        :return: Created load combination
        """
        for load_case in load_case_factors:
            # Check if this load case is in our stored load cases
            found_in_stored = False
            for stored_case in self.load_cases.values():
                if stored_case == load_case:
                    found_in_stored = True
                    break
            if not found_in_stored:
                pass

        # Extract SDK enum from bridge enum
        sdk_combination_type = combination_type.value

        # Convert load_case_factors to the format expected by SCIA
        scia_load_cases = dict(load_case_factors)

        # Create the combination with load cases included
        combination = self.model.create_load_combination(name, sdk_combination_type, scia_load_cases, description=description)
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
        freedom: dict[str, LineSupportFreedom],
        stiffness: dict[str, float],
        c_sys: LineSupportCSys | None = None,
    ) -> scia.LineSupport:
        """
        Creates a line support on a plane edge.

        :param name: Name of the line support
        :param plane_name: Name of the plane to attach support to
        :param edge_index: Edge index on the plane
        :param freedom: Dictionary with freedom enum values for x, y, z, rx, ry, rz directions
        :param stiffness: Dictionary with stiffness values for x and y directions
        :param c_sys: Coordinate system (default: GLOBAL)
        :return: Created line support
        """
        if plane_name not in self.plates:
            raise ValueError(f"Plate '{plane_name}' not found for line support '{name}'.")
        plane = self.plates[plane_name]

        # Extract SDK enums from bridge enums
        sdk_freedom = {key: value.value for key, value in freedom.items()}
        sdk_c_sys = c_sys.value if c_sys is not None else None

        return self.model.create_line_support_on_plane(
            name=name,
            edge=(plane, edge_index),
            x=sdk_freedom["x"],
            y=sdk_freedom["y"],
            z=sdk_freedom["z"],
            rx=sdk_freedom["rx"],
            ry=sdk_freedom["ry"],
            rz=sdk_freedom["rz"],
            stiffness_x=stiffness.get("stiffness_x"),
            stiffness_y=stiffness.get("stiffness_y"),
            c_sys=sdk_c_sys,
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
        scia_analysis.execute(timeout=3600)
        return scia_analysis

    def extract_analysis_results(self, analysis: SciaAnalysis) -> dict[str, object]:
        """
        Extracts results from a completed SCIA analysis.

        Optimized to:
        - Read XML output file only once
        - Parse XML only once
        - Extract only actively used result types (internal_forces, xml_parsing)
        - Skip unused result types (displacements, reactions, stresses)
        """
        if not hasattr(analysis, "get_xml_output_file"):
            raise ValueError("Invalid SCIA analysis object - missing get_xml_output_file method")

        try:
            # Get the XML output file ONCE (previously called 6 times)
            xml_output_file = analysis.get_xml_output_file()

            # Extract only actively used result types
            results = {
                "xml_output_file": xml_output_file,
                "internal_forces": self.get_internal_force_results(xml_output_file),
                "analysis_status": self.get_analysis_status(analysis),
                "xml_parsing": self.parse_xml_results(xml_output_file),
            }

            # Add units mapping for downstream consumers
            from src.integrations.scia_integration.results.scia_unit_conversion import build_units_mapping

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

    def get_internal_force_results(self, xml_output_file: SciaFile) -> dict[str, object]:
        """Extracts internal force results from SCIA analysis."""
        try:
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

    def _extract_namespace(self, root: ET.Element | None) -> str:
        """Extract XML namespace from root element."""
        if root is None or not root.tag.startswith("{"):
            return ""
        return root.tag.split("}")[0] + "}"

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

    def _discover_available_tables(  # noqa: C901, PLR0912
        self,
        xml_output_file: SciaFile,
        root: ET.Element | None = None,
        namespace: str | None = None,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Discover available tables in the XML output file.

        :param xml_output_file: The XML output file to parse
        :param root: Optional pre-parsed XML root element (optimization)
        :param namespace: Optional pre-extracted namespace (optimization)
        :return: Tuple of (available_tables, table_details)
        """
        available_tables: list[str] = []
        table_details: list[dict[str, Any]] = []

        # Use pre-parsed root if provided, otherwise parse now
        if root is None:
            xml_content = self._read_xml_content(xml_output_file)
            if not xml_content:
                return available_tables, table_details

            try:
                root = ET.fromstring(xml_content)
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

        # Use pre-extracted namespace if provided, otherwise extract now
        if namespace is None:
            namespace = self._extract_namespace(root)

        try:
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

            # Use centralized namespace extraction
            namespace = self._extract_namespace(root)

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

        # Use centralized namespace extraction
        namespace = self._extract_namespace(table_element)

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
        """
        Parses the XML output file to extract structured results.

        Optimized to parse XML once and reuse the parsed root for table discovery.
        """
        try:
            # Parse XML once
            xml_content = self._read_xml_content(xml_output_file)
            if not xml_content:
                return {
                    "status": "error",
                    "message": "Could not read XML content",
                    "error": "Empty XML content",
                }

            root = ET.fromstring(xml_content)
            namespace = self._extract_namespace(root)

            # Discover available tables with pre-parsed root (optimization)
            available_tables, table_details = self._discover_available_tables(xml_output_file, root, namespace)

            # Get result table names
            result_tables = self._get_result_table_names(available_tables)

            # Create fresh XML content for parsing
            fresh_xml_content = self._create_fresh_xml_content(xml_output_file)

            # Parse all tables
            parsed_results = {}
            for table_name in result_tables:
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
    scia_analysis.execute(timeout=3600)
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


def _run_scia_analysis_with_builder(
    params: Any,  # noqa: ANN401
    template_path: Path,
    analysis_context: dict[str, Any] | None = None,
) -> tuple[SciaAnalysis, dict[str, object]]:
    """
    Run SCIA analysis using the builder interface and extract basic results.

    :param params: The bridge parameters.
    :param template_path: The path to the ESA template file.
    :param analysis_context: Optional context dict with bridge_position, total_bridges, bridge_name, batch_percentage
    :return: Tuple of (analysis object, basic results dictionary).
    """
    # Build progress message prefix from context
    if analysis_context:
        prefix = f"Bridge {analysis_context['bridge_position']}/{analysis_context['total_bridges']}: {analysis_context['bridge_name']}\n"
        percentage = analysis_context.get("batch_percentage")
    else:
        prefix = ""
        percentage = None

    # Create builder and generate input files
    progress_message(f"{prefix}Genereren SCIA model...", percentage=percentage)
    builder = ViktorSciaModelBuilder()
    define_complete_bridge_model(builder, params)
    xml_file, def_file = builder.generate_xml_input()
    esa_template = File.from_path(template_path)

    # Run the analysis using the builder interface
    progress_message(f"{prefix}Uitvoeren SCIA berekening...", percentage=percentage)
    analysis = builder.run_analysis(xml_file, def_file, esa_template)

    # Extract results using the builder interface
    progress_message(f"{prefix}Extraheren resultaten...", percentage=percentage)
    results = builder.extract_analysis_results(analysis)

    return analysis, results


def get_scia_analysis_results(params: Any, template_path: Path, analysis_context: dict[str, Any] | None = None) -> dict[str, Any]:  # noqa: ANN401
    """
    Run SCIA analysis and extract results.

    Routes to the correct analysis function based on the selected result object type
    (``params.calc_page.calc_selection.result_object_type``):

    - **Integratiestroken** (default): two-stage optimization using integration strips.
    - **Secties op vlak**: two-stage optimization using sections on plane.

    :param params: The bridge parameters.
    :param template_path: The governing ESA template path (used for strips stage 1 or SoP).
    :param analysis_context: Optional context dict with bridge_position, total_bridges, bridge_name, batch_percentage
    :return: Dictionary containing extracted analysis results.
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    from app.constants import SCIA_TEMPLATE_FULL_PATH, SCIA_TEMPLATE_PATH, SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH
    from app.constants.technical import ENABLE_SECTIONS_ON_PLANE, RESULT_OBJECT_SECTIONS_ON_PLANE

    # Determine selected result type
    try:
        result_type = params.calc_page.calc_selection.result_object_type
    except AttributeError:
        result_type = RESULT_OBJECT_SECTIONS_ON_PLANE if ENABLE_SECTIONS_ON_PLANE else None

    if result_type == RESULT_OBJECT_SECTIONS_ON_PLANE:
        return get_scia_analysis_results_sections_on_plane(
            params=params,
            template_path=SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH,
            analysis_context=analysis_context,
        )

    # Default: two-stage integration-strips analysis
    return run_two_stage_scia_analysis(
        params=params,
        governing_template_path=SCIA_TEMPLATE_PATH,
        full_template_path=SCIA_TEMPLATE_FULL_PATH,
        analysis_context=analysis_context,
    )



def _generate_and_cache_integration_strips(results: dict[str, Any]) -> dict[str, Any]:
    """
    Generate and return integration strip dataframes for caching.

    Processes all 8 integration strip tables and creates an envelope DataFrame.

    :param results: Raw SCIA analysis results
    :return: Dictionary with cached integration strip data
    """
    try:
        from src.integrations.scia_integration.results.scia_integration_strips_processor import (
            process_all_integration_strips,
        )

        # Process all integration strip results
        integration_strips_data = process_all_integration_strips(results)
    except Exception as e:
        # Raise UserError for consistent error handling (matching analysis_cache.py behavior)
        raise UserError(
            f"Fout bij genereren integratiestroken: {e!s}. Voer een nieuwe SCIA berekening uit om de integratiestroken opnieuw te genereren."
        ) from e

    return {
        "integration_strips": integration_strips_data,
    }


def create_bridge_scia_model(params: Any, template_path: Path) -> tuple[Any, Any, Any]:  # noqa: ANN401
    """
    Module-level factory for SCIA input and analysis.

    Exists to support tests patching this symbol. In production it constructs
    input files and a SCIA analysis object using the builder utilities.

    :param params: Bridge parametrization object
    :type params: Any
    :param template_path: Path to SCIA template file
    :type template_path: Path
    :returns: Tuple of (xml_file, def_file, analysis)
    :rtype: tuple[Any, Any, Any]
    """
    xml_file, def_file = generate_bridge_xml_files(params)
    if VIKTOR_AVAILABLE and scia is not None:
        esa_template = File.from_path(template_path)
        scia_analysis = scia.SciaAnalysis(xml_file, def_file, esa_template)
        return xml_file, def_file, scia_analysis
    return xml_file, def_file, None


def run_two_stage_scia_analysis(
    params: Any,  # noqa: ANN401
    governing_template_path: Path,
    full_template_path: Path,
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute two-stage SCIA analysis optimization.

    Stage 1: Model ALL strips → Export ONLY governing results → Identify critical strips
    Stage 2: Model ONLY governing strips → Export FULL results → Fast processing

    :param params: Bridge parameters
    :param governing_template_path: Path to template that exports only governing/envelope results
    :param full_template_path: Path to template that exports full results
    :param analysis_context: Optional context dict with bridge_position, total_bridges, bridge_name, batch_percentage
    :return: Combined results dictionary with optimization metrics
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    from src.integrations.scia_integration.model.scia_integration_strips import create_selective_integration_strips
    from src.integrations.scia_integration.model.scia_model import define_complete_bridge_model
    from src.integrations.scia_integration.results.scia_integration_strips_processor import (
        extract_governing_strip_names,
        process_all_integration_strips,
    )

    # Build progress message prefix from context
    if analysis_context:
        prefix = f"Bridge {analysis_context['bridge_position']}/{analysis_context['total_bridges']}: {analysis_context['bridge_name']}\n"
        percentage = analysis_context.get("batch_percentage")
    else:
        prefix = ""
        percentage = None

    # Determine selected method label for progress messages
    try:
        result_type = params.calc_page.calc_selection.result_object_type
    except AttributeError:
        result_type = "Integratiestroken"
    method_label = result_type  # e.g. "Integratiestroken" or "Secties op vlak"

    # === STAGE 1: Governing Analysis ===
    progress_message(f"{prefix}Stage 1: Analyseren met {method_label} (governing results)...", percentage=percentage)

    # Build model with ALL strips (existing logic)
    builder_stage1 = ViktorSciaModelBuilder()
    define_complete_bridge_model(builder_stage1, params)  # Creates all strips
    total_strips_stage1 = len(builder_stage1.integration_strips)

    # Generate input files and run with governing template
    xml_file, def_file = builder_stage1.generate_xml_input()
    esa_template_gov = File.from_path(governing_template_path)
    analysis_stage1 = builder_stage1.run_analysis(xml_file, def_file, esa_template_gov)

    # Extract governing results (small XML output)
    progress_message(f"{prefix}Stage 1: Extraheren governing resultaten...", percentage=percentage)
    results_stage1 = builder_stage1.extract_analysis_results(analysis_stage1)

    # Process to identify governing strips
    progress_message(f"{prefix}Identificeren governing strips...", percentage=percentage)
    processed_strips_stage1 = process_all_integration_strips(results_stage1)
    envelope_df = processed_strips_stage1["envelope"]
    governing_strip_names = extract_governing_strip_names(envelope_df)

    # Log statistics
    governing_count = len(governing_strip_names)
    reduction_pct = (1 - governing_count / total_strips_stage1) * 100 if total_strips_stage1 > 0 else 0

    progress_message(
        f"{prefix}Governing strips: {governing_count}/{total_strips_stage1} ({reduction_pct:.1f}% reductie)",
        percentage=percentage,
    )

    # === STAGE 2: Detailed Analysis ===
    progress_message(f"{prefix}Stage 2: Bouwen model met {governing_count} governing strips...", percentage=percentage)

    # Build model with ONLY governing strips
    builder_stage2 = ViktorSciaModelBuilder()

    # Import necessary functions from scia_model module
    from app.bridge.utils import _validate_first_and_last_supports
    from src.integrations.scia_integration.load_system.scia_load_cases import create_all_load_cases
    from src.integrations.scia_integration.load_system.scia_load_combinations import create_all_load_combinations
    from src.integrations.scia_integration.load_system.scia_load_group import create_all_load_groups
    from src.integrations.scia_integration.model.scia_model import create_bridge_geometry
    from src.integrations.scia_integration.model.scia_supports import create_all_supports
    from src.integrations.scia_integration.results.scia_result_classes import create_all_result_classes
    from src.integrations.scia_integration.scia_loads import create_all_loads

    # Build model structure (same as define_complete_bridge_model but without all strips)
    # 0. Validate support configuration
    _validate_first_and_last_supports(params)

    # 1. Build Geometry
    plate_names = create_bridge_geometry(builder_stage2, params)

    # 2. Extract support types
    support_types = None
    if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
        support_types = [segment.is_support for segment in params.bridge_segments_array]

    # 3. Build Line Supports
    create_all_supports(builder_stage2, plate_names, support_types)

    # 4. Build ONLY governing integration strips (this is the key difference)
    strip_stats = create_selective_integration_strips(builder_stage2, params, governing_strip_names)

    # Show updated progress with actual strip counts
    if strip_stats:
        progress_message(
            f"{prefix}Stage 2: {strip_stats['created']} strips aangemaakt ({strip_stats['skipped']} overgeslagen van {strip_stats['total_attempted']} totaal)",
            percentage=percentage,
        )

    # 5. Build Load Groups
    create_all_load_groups(builder_stage2)

    # 6. Build ALL Load Cases
    all_load_cases = create_all_load_cases(builder_stage2, params)

    # 7. Apply all loads
    create_all_loads(builder_stage2, params, all_load_cases)

    # 8. Build Load Combinations
    all_load_combinations = create_all_load_combinations(params, builder_stage2, all_load_cases)

    # 9. Create Result Classes
    create_all_result_classes(params, builder_stage2, all_load_combinations)

    # Run with full results template
    progress_message(f"{prefix}Stage 2: Uitvoeren SCIA berekening met {strip_stats.get('created', governing_count)} strips...", percentage=percentage)
    xml_file2, def_file2 = builder_stage2.generate_xml_input()
    esa_template_full = File.from_path(full_template_path)
    analysis_stage2 = builder_stage2.run_analysis(xml_file2, def_file2, esa_template_full)

    # Extract full results (small file because only governing strips)
    progress_message(f"{prefix}Stage 2: Extraheren complete resultaten...", percentage=percentage)
    results_stage2 = builder_stage2.extract_analysis_results(analysis_stage2)

    # Extract additional data for caching
    results_stage2["xml_output"] = _extract_xml_output_for_caching(analysis_stage2)
    results_stage2["esa_model"] = _extract_esa_model_for_caching(analysis_stage2)

    # Process stage 2 integration strips
    cached_integration_strips_stage2 = _generate_and_cache_integration_strips(results_stage2)
    results_stage2.update(cached_integration_strips_stage2)

    # === COMBINE RESULTS ===
    stage1_xml_size = len(results_stage1.get("xml_output", b"") or b"")
    stage2_xml_size = len(results_stage2.get("xml_output", b"") or b"")

    combined_results = {
        # Primary results for downstream processing (stage 2 full results)
        "integration_strips": results_stage2.get("integration_strips"),
        "xml_parsing": results_stage2.get("xml_parsing"),
        "analysis_status": results_stage2.get("analysis_status"),
        "xml_output": results_stage2.get("xml_output"),
        "esa_model": results_stage2.get("esa_model"),
        # Metadata about the two-stage optimization
        "two_stage_optimization": {
            "stage1_results": results_stage1,
            "governing_strip_names": list(governing_strip_names),
            "optimization_stats": {
                "total_strips_stage1": total_strips_stage1,
                "governing_strips_stage2": governing_count,
                "reduction_percentage": reduction_pct,
                "stage1_xml_size_bytes": stage1_xml_size,
                "stage2_xml_size_bytes": stage2_xml_size,
                "total_xml_size_bytes": stage1_xml_size + stage2_xml_size,
                "strips_created": strip_stats.get("created", governing_count),
                "strips_skipped": strip_stats.get("skipped", 0),
                "strips_total_attempted": strip_stats.get("total_attempted", total_strips_stage1),
            },
        },
        # Summary information
        "summary": {
            "analysis_status": results_stage2.get("analysis_status", "unknown"),
            "xml_parsing": results_stage2.get("xml_parsing", {}),
            "has_esa_model": results_stage2.get("esa_model") is not None,
            "has_integration_strips": bool(cached_integration_strips_stage2),
            "two_stage_optimized": True,
        },
    }

    return combined_results


# =============================================================================
# SECTIONS ON PLANE — TOP-LEVEL BUILDER FUNCTIONS
# =============================================================================


def run_two_stage_scia_analysis_sections_on_plane(
    params: Any,  # noqa: ANN401
    governing_template_path: Path,
    full_template_path: Path,
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute two-stage SCIA analysis for sections on plane.

    Stage 1: Build model with ALL sections → governing template → identify governing sections.
    Stage 2: Build model with ONLY governing sections → full template → complete results.

    :param params: Bridge parameters
    :param governing_template_path: Path to template that exports only governing/envelope results
    :param full_template_path: Path to template that exports full results
    :param analysis_context: Optional context dict with bridge_position, total_bridges,
        bridge_name, batch_percentage for progress reporting.
    :return: Combined results dictionary with optimization metrics
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    from src.integrations.scia_integration.model.scia_model import define_bridge_model_sections_on_plane
    from src.integrations.scia_integration.model.scia_sections_on_plane import create_selective_sections_on_plane
    from src.integrations.scia_integration.results.scia_sections_on_plane_processor import (
        extract_governing_section_names,
        process_all_sections_on_plane,
    )

    if analysis_context:
        prefix = f"Bridge {analysis_context['bridge_position']}/{analysis_context['total_bridges']}: {analysis_context['bridge_name']}\n"
        percentage = analysis_context.get("batch_percentage")
    else:
        prefix = ""
        percentage = None

    # === STAGE 1: Governing Analysis ===
    progress_message(f"{prefix}Stage 1: Genereren SCIA model (alle secties op vlak)...", percentage=percentage)
    builder_stage1 = ViktorSciaModelBuilder()
    define_bridge_model_sections_on_plane(builder_stage1, params)
    total_sections_stage1 = len(builder_stage1.sections_on_plane)

    xml_file, def_file = builder_stage1.generate_xml_input()
    esa_template_gov = File.from_path(governing_template_path)

    progress_message(f"{prefix}Stage 1: Uitvoeren SCIA berekening (governing results)...", percentage=percentage)
    analysis_stage1 = builder_stage1.run_analysis(xml_file, def_file, esa_template_gov)

    progress_message(f"{prefix}Stage 1: Extraheren governing resultaten...", percentage=percentage)
    results_stage1 = builder_stage1.extract_analysis_results(analysis_stage1)

    # Process Stage 1 results to identify governing sections
    progress_message(f"{prefix}Identificeren governing secties op vlak...", percentage=percentage)
    processed_stage1 = process_all_sections_on_plane(results_stage1)
    envelope_df = processed_stage1["envelope"]
    governing_section_names = extract_governing_section_names(envelope_df)

    governing_count = len(governing_section_names)
    reduction_pct = (1 - governing_count / total_sections_stage1) * 100 if total_sections_stage1 > 0 else 0

    progress_message(
        f"{prefix}Governing secties: {governing_count}/{total_sections_stage1} ({reduction_pct:.1f}% reductie)",
        percentage=percentage,
    )

    # === STAGE 2: Detailed Analysis ===
    progress_message(f"{prefix}Stage 2: Bouwen model met {governing_count} governing secties op vlak...", percentage=percentage)

    builder_stage2 = ViktorSciaModelBuilder()

    from app.bridge.utils import _validate_first_and_last_supports
    from src.integrations.scia_integration.load_system.scia_load_cases import create_all_load_cases
    from src.integrations.scia_integration.load_system.scia_load_combinations import create_all_load_combinations
    from src.integrations.scia_integration.load_system.scia_load_group import create_all_load_groups
    from src.integrations.scia_integration.model.scia_model import create_bridge_geometry
    from src.integrations.scia_integration.model.scia_supports import create_all_supports
    from src.integrations.scia_integration.results.scia_result_classes import create_all_result_classes
    from src.integrations.scia_integration.scia_loads import create_all_loads

    _validate_first_and_last_supports(params)
    plate_names = create_bridge_geometry(builder_stage2, params)

    support_types = None
    if hasattr(params, "bridge_segments_array") and params.bridge_segments_array:
        support_types = [segment.is_support for segment in params.bridge_segments_array]

    create_all_supports(builder_stage2, plate_names, support_types)

    # Create ONLY governing sections
    section_stats = create_selective_sections_on_plane(builder_stage2, params, governing_section_names)

    progress_message(
        f"{prefix}Stage 2: {section_stats['created']} secties aangemaakt "
        f"({section_stats['skipped']} overgeslagen van {section_stats['total_attempted']} totaal)",
        percentage=percentage,
    )

    create_all_load_groups(builder_stage2)
    all_load_cases = create_all_load_cases(builder_stage2, params)
    create_all_loads(builder_stage2, params, all_load_cases)
    all_load_combinations = create_all_load_combinations(params, builder_stage2, all_load_cases)
    create_all_result_classes(params, builder_stage2, all_load_combinations)

    progress_message(f"{prefix}Stage 2: Uitvoeren SCIA berekening met {section_stats['created']} secties...", percentage=percentage)
    xml_file2, def_file2 = builder_stage2.generate_xml_input()
    esa_template_full = File.from_path(full_template_path)
    analysis_stage2 = builder_stage2.run_analysis(xml_file2, def_file2, esa_template_full)

    progress_message(f"{prefix}Stage 2: Extraheren complete resultaten...", percentage=percentage)
    results_stage2 = builder_stage2.extract_analysis_results(analysis_stage2)
    results_stage2["xml_output"] = _extract_xml_output_for_caching(analysis_stage2)
    results_stage2["esa_model"] = _extract_esa_model_for_caching(analysis_stage2)

    # Pre-process sections-on-plane data for caching
    import contextlib
    with contextlib.suppress(Exception):
        results_stage2["sections_on_plane"] = process_all_sections_on_plane(results_stage2)

    stage1_xml_size = len(results_stage1.get("xml_output", b"") or b"")
    stage2_xml_size = len(results_stage2.get("xml_output", b"") or b"")

    return {
        # Primary results for downstream processing (Stage 2 full results)
        "sections_on_plane": results_stage2.get("sections_on_plane"),
        "xml_parsing": results_stage2.get("xml_parsing"),
        "analysis_status": results_stage2.get("analysis_status"),
        "xml_output": results_stage2.get("xml_output"),
        "esa_model": results_stage2.get("esa_model"),
        # Metadata about the two-stage optimization
        "two_stage_optimization": {
            "governing_section_names": list(governing_section_names),
            "optimization_stats": {
                "total_sections_stage1": total_sections_stage1,
                "governing_sections_stage2": governing_count,
                "reduction_percentage": reduction_pct,
                "stage1_xml_size_bytes": stage1_xml_size,
                "stage2_xml_size_bytes": stage2_xml_size,
                "sections_created": section_stats["created"],
                "sections_skipped": section_stats["skipped"],
            },
        },
        "summary": {
            "analysis_status": results_stage2.get("analysis_status", "unknown"),
            "has_esa_model": results_stage2.get("esa_model") is not None,
            "has_sections_on_plane": bool(results_stage2.get("sections_on_plane")),
            "two_stage_optimized": True,
        },
    }


def generate_bridge_xml_files_sections_on_plane(params: Any) -> tuple[BytesIO, BytesIO]:  # noqa: ANN401
    """
    Generate the XML and DEF input files for a sections-on-plane bridge model.

    Calls :func:`define_bridge_model_sections_on_plane` which creates
    SectionOnPlane objects instead of integration strips.

    :param params: The bridge parameters from the VIKTOR parametrization.
    :return: A tuple containing the XML and DEF files as BytesIO objects.
    """
    builder = ViktorSciaModelBuilder()
    define_bridge_model_sections_on_plane(builder, params)
    return builder.generate_xml_input()


def setup_bridge_analysis_sections_on_plane(
    params: Any,  # noqa: ANN401
    template_path: Path,
) -> tuple[Any, Any, Any]:
    """
    Prepare all inputs for a sections-on-plane SCIA analysis.

    :param params: The bridge parameters from the VIKTOR parametrization.
    :param template_path: Path to the ESA template file
        (use ``SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH`` or
        ``SCIA_TEMPLATE_SECTIONS_ON_PLANE_FULL_PATH``).
    :return: A tuple of (xml_file, def_file, esa_template).
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")
    xml_file, def_file = generate_bridge_xml_files_sections_on_plane(params)
    esa_template = File.from_path(template_path)
    return xml_file, def_file, esa_template


def get_scia_analysis_results_sections_on_plane(
    params: Any,  # noqa: ANN401
    template_path: Path,
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the two-stage sections-on-plane SCIA analysis and return results.

    Stage 1: Build model with ALL sections → governing template → identify governing sections.
    Stage 2: Build model with ONLY governing sections → full template → complete results.

    :param params: The bridge parameters.
    :param template_path: Path to the **governing** ESA template (Stage 1).
    :param analysis_context: Optional context dict with bridge_position,
        total_bridges, bridge_name, batch_percentage for progress reporting.
    :return: Dictionary containing extracted analysis results.
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    from app.constants import SCIA_TEMPLATE_SECTIONS_ON_PLANE_FULL_PATH

    return run_two_stage_scia_analysis_sections_on_plane(
        params=params,
        governing_template_path=template_path,
        full_template_path=SCIA_TEMPLATE_SECTIONS_ON_PLANE_FULL_PATH,
        analysis_context=analysis_context,
    )

