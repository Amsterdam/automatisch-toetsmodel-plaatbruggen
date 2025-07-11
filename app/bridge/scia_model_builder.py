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
                spec_map[specification],  # type: ignore[index]
                dur_map[duration],  # type: ignore[index]
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

        return self.model.create_free_surface_load(
            name=name,
            load_case=load_case,
            direction=scia.FreeSurfaceLoad.Direction.Z,
            q1=load_value,
            points=points_2d,
            distribution=scia.FreeSurfaceLoad.Distribution.UNIFORM,
        )

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
        if combination_type.value == scia.Combination.Type.ENVELOPE_SERVICEABILITY.value:
            combo_class = scia.Combination.Type.ENVELOPE_SERVICEABILITY
        elif combination_type.value == scia.Combination.Type.ENVELOPE_ULTIMATE.value:
            combo_class = scia.Combination.Type.ENVELOPE_ULTIMATE
        else:
            raise ValueError(f"Unsupported combination type: {combination_type}")

        combination = self.model.create_combination(name, combo_class, description)
        for load_case, factor in load_case_factors.items():
            combination.add_load_case(load_case, factor)
        return combination

    def create_line_support(
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

        return self.model.create_line_support(
            name=name,
            edge=(plane, edge_index),
            ux=freedom_map[freedom.get("ux", "FREE")],
            uy=freedom_map[freedom.get("uy", "FREE")],
            uz=freedom_map[freedom.get("uz", "FREE")],
            fix=freedom_map[freedom.get("fix", "FREE")],
            fiy=freedom_map[freedom.get("fiy", "FREE")],
            fiz=freedom_map[freedom.get("fiz", "FREE")],
            stiffness_x=stiffness.get("stiffness_x", 0.0),
            stiffness_y=stiffness.get("stiffness_y", 0.0),
            stiffness_z=stiffness.get("stiffness_z", 0.0),
            stiffness_fix=stiffness.get("stiffness_fix", 0.0),
            stiffness_fiy=stiffness.get("stiffness_fiy", 0.0),
            stiffness_fiz=stiffness.get("stiffness_fiz", 0.0),
        )

    def get_model(self) -> scia.Model:
        """Returns the constructed SCIA model."""
        return self.model

    def generate_xml_input(self) -> tuple[BytesIO, BytesIO]:
        """Generates XML and DEF files from the SCIA model."""
        xml_file, def_file = self.model.generate_xml_input()
        return xml_file, def_file


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
    scia_analysis = scia.SciaAnalysis(xml_input_file=xml_file, xml_def_file=def_file, esa_template_file=esa_template)
    scia_analysis.execute(timeout=600)
    return scia_analysis
