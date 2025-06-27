"""
SCIA Engineer integration for bridge analysis.

Creates SCIA models from bridge parameters with:
- Multi-zone plates (Zone 1, 2, 3) with variable thickness
- Proper node positioning from bridge_segments_array
- Load framework demonstration
"""

import io
from io import BytesIO
from pathlib import Path
from typing import Any, TypeAlias, Union

from app.bridge.parametrization import BridgeParametrization
from src.integrations.scia_utils import create_patch_surface_load

# Type aliases
SciaNode: TypeAlias = object
SciaModel: TypeAlias = "SciaModelProtocol"


class SciaModelProtocol:
    """Protocol for SCIA model objects."""

    def create_node(self, name: str, x: float, y: float, z: float) -> "SciaNode":
        """Create a node in the SCIA model."""


class NodeTracker:
    """Helper to track and reuse nodes in SCIA model."""

    def __init__(self, scia_model: SciaModel) -> None:
        self.model = scia_model
        self._nodes_by_coords: dict[tuple[float, float, float], SciaNode] = {}
        self._nodes_by_name: dict[str, SciaNode] = {}

    def get_or_create_node(self, name: str, x: float, y: float, z: float) -> SciaNode:
        """Get existing node at coordinates or create new one."""
        coords = (x, y, z)

        if coords in self._nodes_by_coords:
            return self._nodes_by_coords[coords]

        node = self.model.create_node(name, x, y, z)
        self._nodes_by_coords[coords] = node
        self._nodes_by_name[name] = node
        return node

    def get_node_by_name(self, name: str) -> SciaNode:
        """Get node by name."""
        return self._nodes_by_name[name]


def create_node_and_thickness_dict(params: BridgeParametrization) -> tuple[dict[str, list[float]], dict[str, float]]:
    """
    Create node positions and thickness data from bridge parameters.

    :param params: Bridge parameters
    :returns: (nodes_dict, thickness_dict)
    """
    dynamic_arrays = len(params.bridge_segments_array)
    nodes_dict = {}
    thickness_dict = {}

    def calculate_cross_section_positions(segment_idx: int) -> dict[str, float]:
        """Calculate node positions for cross section."""
        l_sum = sum(item["l"] for item in params.bridge_segments_array[: segment_idx + 1])
        segment = params.bridge_segments_array[segment_idx]

        return {
            "x": l_sum,
            "z1_left": segment.bz1 + segment.bz2 / 2,
            "z1_right": segment.bz2 / 2,
            "z3_left": -segment.bz2 / 2,
            "z3_right": -segment.bz3 - segment.bz2 / 2,
        }

    # Create first cross section
    if dynamic_arrays > 0:
        pos = calculate_cross_section_positions(0)
        nodes_dict.update(
            {
                "K_dek:1_1": [pos["x"], pos["z1_left"], 0],
                "K_dek:1_2": [pos["x"], pos["z1_right"], 0],
                "K_dek:1_3": [pos["x"], pos["z3_left"], 0],
                "K_dek:1_4": [pos["x"], pos["z3_right"], 0],
            }
        )

    # Create remaining cross sections and thickness data
    for dynamic_array in range(1, dynamic_arrays):
        pos = calculate_cross_section_positions(dynamic_array)
        d_num = dynamic_array + 1

        nodes_dict.update(
            {
                f"K_dek:{d_num}_1": [pos["x"], pos["z1_left"], 0],
                f"K_dek:{d_num}_2": [pos["x"], pos["z1_right"], 0],
                f"K_dek:{d_num}_3": [pos["x"], pos["z3_left"], 0],
                f"K_dek:{d_num}_4": [pos["x"], pos["z3_right"], 0],
            }
        )

        thickness_dict.update(
            {
                f"Z1_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz,
                f"Z2_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz_2,
                f"Z3_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz,
            }
        )

    return nodes_dict, thickness_dict


def create_simple_scia_plate_model(params: BridgeParametrization) -> Union[tuple[BytesIO, BytesIO]]:
    """
    Create SCIA bridge model with multi-zone plates.

    Creates:
    - Cross-sections at each bridge segment
    - Three zone plates (Zone 1, 2, 3) with variable thickness
    - Demonstration loads using scia_utils framework

    Coordinate system:
    - X: Longitudinal (cumulative segment lengths)
    - Y: Transverse (zone boundaries from bz1, bz2, bz3)
    - Z: Vertical (0 at top surface)

    Zone layout: Zone 3 | Zone 2 | Zone 1
                |--bz3--|--bz2--|--bz1--|

    :param params: Bridge parameters
    :returns: (xml_file, def_file) for SCIA analysis
    """
    try:
        from viktor.external import scia
    except ImportError as e:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.") from e

    # Create model and material
    model = scia.Model()
    node_tracker = NodeTracker(model)
    material = scia.Material(0, "C30/37")

    # Get geometry data
    nodes_dict, thickness_dict = create_node_and_thickness_dict(params)
    dynamic_arrays = len(params.bridge_segments_array)
    scia_nodes = {}

    # Create initial cross section nodes
    for node_suffix in range(1, 5):
        node_name = f"K_dek:1_{node_suffix}"
        coords = nodes_dict.get(node_name)
        if coords is None:
            raise ValueError(f"Coordinates for node '{node_name}' not found.")
        scia_nodes[node_name] = node_tracker.get_or_create_node(node_name, coords[0], coords[1], coords[2])

    # Create plates between cross sections
    for span in range(1, dynamic_arrays):
        next_span = span + 1

        # Create next cross section nodes
        for node_suffix in range(1, 5):
            node_name = f"K_dek:{next_span}_{node_suffix}"
            if node_name not in scia_nodes:
                coords = nodes_dict.get(node_name)
                if coords is None:
                    raise ValueError(f"Coordinates for node '{node_name}' not found.")
                scia_nodes[node_name] = node_tracker.get_or_create_node(node_name, coords[0], coords[1], coords[2])

        # Create zone plates
        # Zone 1 plate
        corner_nodes_z1 = [
            scia_nodes[f"K_dek:{span}_1"],
            scia_nodes[f"K_dek:{next_span}_1"],
            scia_nodes[f"K_dek:{next_span}_2"],
            scia_nodes[f"K_dek:{span}_2"],
        ]
        model.create_plane(corner_nodes_z1, thickness_dict.get(f"Z1_{span}"), name=f"Z1_{span}", material=material)

        # Zone 3 plate
        corner_nodes_z3 = [
            scia_nodes[f"K_dek:{span}_3"],
            scia_nodes[f"K_dek:{next_span}_3"],
            scia_nodes[f"K_dek:{next_span}_4"],
            scia_nodes[f"K_dek:{span}_4"],
        ]
        model.create_plane(corner_nodes_z3, thickness_dict.get(f"Z3_{span}"), name=f"Z3_{span}", material=material)

        # Zone 2 plate
        corner_nodes_z2 = [
            scia_nodes[f"K_dek:{span}_2"],
            scia_nodes[f"K_dek:{next_span}_2"],
            scia_nodes[f"K_dek:{next_span}_3"],
            scia_nodes[f"K_dek:{span}_3"],
        ]
        model.create_plane(corner_nodes_z2, thickness_dict.get(f"Z2_{span}"), name=f"Z2_{span}", material=material)

    # Add demonstration loads
    _add_dummy_wheel_loads(model)

    return model.generate_xml_input()


def _add_dummy_wheel_loads(model: SciaModel) -> dict[str, Any]:
    """
    Demonstrate load framework from scia_utils.

    Shows 4-step workflow:
    1. Create load groups
    2. Create load cases
    3. Create load combinations (EN 1990 factors)
    4. Apply loads (wheel patches)

    To replace with real loads:
    - Extract from params.input.belastingzones
    - Use src.loadcase_helper_functions
    - Map to bridge segments
    """
    from src.integrations.scia_utils import (
        create_load_case_complete,
        create_load_combination_by_type,
        create_load_group_by_type,
    )

    # Create load groups
    permanent_group = create_load_group_by_type(model, "PERMANENT", "LG_Permanent")
    traffic_group = create_load_group_by_type(model, "VARIABLE", "LG_Traffic", "CAT_G")
    wind_group = create_load_group_by_type(model, "VARIABLE", "LG_Wind", "WIND")

    # Create load cases
    dead_load_case = create_load_case_complete(
        model, permanent_group, "G1_DeadLoad", "Superimposed dead load", case_type="PERMANENT", permanent_type="STANDARD"
    )

    lm1_case = create_load_case_complete(
        model, traffic_group, "Q1_LM1", "Load Model 1 - Tandem + UDL", case_type="VARIABLE", variable_type="STATIC", duration="SHORT"
    )

    wind_case = create_load_case_complete(
        model, wind_group, "Q2_Wind", "Wind Load", case_type="VARIABLE", variable_type="STATIC", specification="STATIC_WIND", duration="SHORT"
    )

    # Create load combinations (EN 1990 factors)
    uls_basic = create_load_combination_by_type(model, "ULS", "ULS_1_G+LM1", {dead_load_case: 1.35, lm1_case: 1.5})

    uls_wind = create_load_combination_by_type(model, "ULS", "ULS_2_G+LM1+W", {dead_load_case: 1.35, lm1_case: 1.5, wind_case: 1.5 * 0.6})

    sls_char = create_load_combination_by_type(model, "SLS_CHAR", "SLS_Char_G+LM1", {dead_load_case: 1.0, lm1_case: 1.0})

    # Apply LM1 tandem loads (dummy positions)
    wheel_1_corners = [(10.0, 1.8, 0.0), (10.4, 1.8, 0.0), (10.4, 2.2, 0.0), (10.0, 2.2, 0.0)]
    wheel_2_corners = [(10.0, -0.2, 0.0), (10.4, -0.2, 0.0), (10.4, 0.2, 0.0), (10.0, 0.2, 0.0)]
    wheel_3_corners = [(11.2, 1.8, 0.0), (11.6, 1.8, 0.0), (11.6, 2.2, 0.0), (11.2, 2.2, 0.0)]
    wheel_4_corners = [(11.2, -0.2, 0.0), (11.6, -0.2, 0.0), (11.6, 0.2, 0.0), (11.2, 0.2, 0.0)]

    # 300kN/0.16m² = 1,875,000 N/m², 200kN/0.16m² = 1,250,000 N/m²
    create_patch_surface_load(model, lm1_case, wheel_1_corners, 1875000.0, "LM1_Axle1_Wheel1")
    create_patch_surface_load(model, lm1_case, wheel_2_corners, 1875000.0, "LM1_Axle1_Wheel2")
    create_patch_surface_load(model, lm1_case, wheel_3_corners, 1250000.0, "LM1_Axle2_Wheel1")
    create_patch_surface_load(model, lm1_case, wheel_4_corners, 1250000.0, "LM1_Axle2_Wheel2")

    return {
        "load_groups": {"permanent": permanent_group, "traffic": traffic_group, "wind": wind_group},
        "load_cases": {"dead_load": dead_load_case, "lm1": lm1_case, "wind": wind_case},
        "combinations": {"uls_basic": uls_basic, "uls_wind": uls_wind, "sls_char": sls_char},
    }


def create_scia_analysis_from_template(xml_file: io.BytesIO, def_file: io.BytesIO, template_path: Path) -> Any:  # noqa: ANN401
    """
    Create SCIA analysis using template file.

    :param xml_file: Generated XML input file
    :param def_file: Generated definition file
    :param template_path: Path to ESA template
    :returns: SCIA analysis object
    """
    try:
        from viktor.core import File
        from viktor.external import scia
    except ImportError as e:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.") from e

    if not template_path.exists():
        raise FileNotFoundError(f"SCIA template file not found: {template_path}")

    esa_template = File.from_path(template_path)
    return scia.SciaAnalysis(xml_file, def_file, esa_template)


def create_bridge_scia_model(params: BridgeParametrization, template_path: Path) -> tuple[Any, Any, Any]:
    """
    Main function to create complete SCIA model from bridge parameters.

    Creates geometry from bridge_segments_array and sets up analysis with template.

    TODO: Integrate with load zone data from params.input.belastingzones for realistic loads.

    :param params: Bridge parameters
    :param template_path: Path to ESA template file
    :returns: (xml_file, def_file, scia_analysis)
    """
    xml_file, def_file = create_simple_scia_plate_model(params)
    scia_analysis = create_scia_analysis_from_template(xml_file, def_file, template_path)
    return xml_file, def_file, scia_analysis
