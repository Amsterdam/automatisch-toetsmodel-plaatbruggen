"""
SCIA Engineer integration module for bridge analysis.

This module provides functionality to create SCIA models from bridge parameters.
Currently implements a simple rectangular plate model as a starting point.

Future enhancements needed:
- Support for complex bridge geometry matching the actual bridge shape (1:1 with bridge segments)
- Variable thickness across zones (zone 1, 2, 3 have different thickness values)
- Load cases and combinations
- Support for different bridge types
- Material property customization
"""

import io
from io import BytesIO
from pathlib import Path
from typing import Any, TypeAlias, Tuple, Union

from munch import Munch  # type: ignore[import-untyped]

# Type alias for SCIA Engineer node objects
SciaNode: TypeAlias = object  # More specific type if available from SCIA API
SciaModel: TypeAlias = "SciaModelProtocol"


class SciaModelProtocol:
    def create_node(self, name: str, x: float, y: float, z: float) -> "SciaNode": ...  # Define the expected behavior of the create_node method


from app.bridge.parametrization import (
    BridgeParametrization,
)


class NodeTracker:
    """Helper class to track and reuse nodes in SCIA model creation."""

    def __init__(self, scia_model: SciaModel) -> None:
        """
        Initialize the node tracker.

        :param scia_model: SCIA model instance
        """
        self.model = scia_model
        self._nodes_by_coords: dict[tuple[float, float, float], SciaNode] = {}
        self._nodes_by_name: dict[str, SciaNode] = {}

    def get_or_create_node(self, name: str, x: float, y: float, z: float) -> SciaNode:
        """
        Get an existing node at the given coordinates or create a new one.

        :param name: Name for the node (used if creating new)
        :param x: X coordinate
        :param y: Y coordinate
        :param z: Z coordinate
        :returns: SCIA node object
        """
        coords = (x, y, z)

        # First check if we already have a node at these coordinates
        if coords in self._nodes_by_coords:
            return self._nodes_by_coords[coords]

        # If not, create a new node
        node = self.model.create_node(name, x, y, z)
        self._nodes_by_coords[coords] = node
        self._nodes_by_name[name] = node
        return node

    def get_node_by_name(self, name: str) -> SciaNode:
        """
        Get a node by its name.

        :param name: Name of the node
        :returns: SCIA node object
        :raises KeyError: If node with given name doesn't exist
        """
        return self._nodes_by_name[name]


def create_node_and_thickness_dict(params: BridgeParametrization) -> tuple[dict[str, list[float]], dict[str, float]]:
    """
    Create dictionaries containing node positions and thickness data for SCIA model.

    :param params: Bridge parameters containing segment data
    :returns: Tuple of (nodes_dict, thickness_dict) where:
             - nodes_dict: Maps node names to [x, y, z] coordinates
             - thickness_dict: Maps zone names to thickness values
    """
    # Determine the number of sub-zones based on input dimensions
    dynamic_arrays = len(params.bridge_segments_array)

    nodes_dict = {}
    thickness_dict = {}

    # Helper function to calculate node positions for a cross section
    def calculate_cross_section_positions(segment_idx: int) -> dict[str, float]:
        """
        Calculate node positions for a specific cross section.

        :param segment_idx: Index of the bridge segment
        :returns: Dictionary with x and z coordinates for the cross section nodes
        """
        # Calculate cumulative length for this cross section
        l_sum = sum(item["l"] for item in params.bridge_segments_array[: segment_idx + 1])
        segment = params.bridge_segments_array[segment_idx]

        return {
            "x": l_sum,
            "z1_left": segment.bz1 + segment.bz2 / 2,  # Zone 1 left edge
            "z1_right": segment.bz2 / 2,  # Zone 1 right edge (boundary with Zone 2)
            "z3_left": -segment.bz2 / 2,  # Zone 3 left edge (boundary with Zone 2)
            "z3_right": -segment.bz3 - segment.bz2 / 2,  # Zone 3 right edge
        }

    # Create nodes for the first cross section (start of bridge)
    if dynamic_arrays > 0:
        pos = calculate_cross_section_positions(0)
        nodes_dict.update(
            {
                # First cross section nodes
                "K_dek:1_1": [pos["x"], pos["z1_left"], 0],  # Zone 1 left
                "K_dek:1_2": [pos["x"], pos["z1_right"], 0],  # Zone 1 right
                "K_dek:1_3": [pos["x"], pos["z3_left"], 0],  # Zone 3 left
                "K_dek:1_4": [pos["x"], pos["z3_right"], 0],  # Zone 3 right
            }
        )

    for dynamic_array in range(1, dynamic_arrays):
        pos = calculate_cross_section_positions(dynamic_array)
        d_num = dynamic_array + 1  # Node numbering starts at 1

        # Add only the nodes for this cross section
        nodes_dict.update(
            {
                # (zone 1)
                f"K_dek:{d_num}_1": [pos["x"], pos["z1_left"], 0],  # Zone 1 left
                f"K_dek:{d_num}_2": [pos["x"], pos["z1_right"], 0],  # Zone 1 right
                # (zone 3)
                f"K_dek:{d_num}_3": [pos["x"], pos["z3_left"], 0],  # Zone 3 left
                f"K_dek:{d_num}_4": [pos["x"], pos["z3_right"], 0],  # Zone 3 right
            }
        )

        # Add thickness data for the plates that will be created using these nodes
        thickness_dict.update(
            {
                # (zone 1)
                f"Z1_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz,
                # (zone 2)
                f"Z2_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz_2,
                # (zone 3)
                f"Z3_{dynamic_array}": params.bridge_segments_array[dynamic_array].dz,
            }
        )

    return nodes_dict, thickness_dict

def create_simple_scia_plate_model(params: BridgeParametrization) -> Union[Tuple[BytesIO, BytesIO]]:
    """
    Create a simple rectangular plate SCIA model from bridge geometry.

    Creates a basic rectangular plate with:
    - 4 corner nodes
    - 1 rectangular plane element
    - Basic concrete material
    - Simple mesh setup

    TODO: Future enhancements for complete bridge modeling:

    1. COMPLEX GEOMETRY WITH NODES PER CROSS-SECTION (D1, D2, D3, etc.):
       - Create nodes at each cross-section (D1, D2, D3...) defined in bridge_segments_params
       - Node naming convention: "D{section}.{zone}" (e.g., D1.1, D1.2, D1.3, D2.1, D2.2, D2.3)
       - For each cross-section at position x_i, create nodes:
         * D{i}.1: Y-coordinate at -bz2/2 - bz3 (left edge zone 3)
         * D{i}.2: Y-coordinate at -bz2/2 (zone 2/3 boundary)
         * D{i}.3: Y-coordinate at +bz2/2 (zone 1/2 boundary)
         * D{i}.4: Y-coordinate at +bz2/2 + bz1 (right edge zone 1)
         * Z-coordinates: 0 (top), -dz (zone 1&3), -dz_2 (zone 2 bottom)

       Example implementation pattern:
       ```python
       nodes = {}
       x_position = 0
       for i, segment in enumerate(bridge_segments_params):
           if i > 0:  # Skip first segment (reference point)
               x_position += segment["l"]
           section_name = f"D{i + 1}"

           # Zone boundaries in Y direction
           y_left_edge = -(segment["bz2"] / 2 + segment["bz3"])
           y_zone23_boundary = -segment["bz2"] / 2
           y_zone12_boundary = segment["bz2"] / 2
           y_right_edge = segment["bz2"] / 2 + segment["bz1"]

           # Create nodes for this cross-section
           nodes[f"{section_name}.1"] = model.create_node(f"{section_name}.1", x_position, y_left_edge, 0)
           nodes[f"{section_name}.2"] = model.create_node(f"{section_name}.2", x_position, y_zone23_boundary, 0)
           nodes[f"{section_name}.3"] = model.create_node(f"{section_name}.3", x_position, y_zone12_boundary, 0)
           nodes[f"{section_name}.4"] = model.create_node(f"{section_name}.4", x_position, y_right_edge, 0)

           # Bottom nodes for different zone thicknesses
           nodes[f"{section_name}.1B"] = model.create_node(f"{section_name}.1B", x_position, y_left_edge, -segment["dz"])
           nodes[f"{section_name}.2B"] = model.create_node(f"{section_name}.2B", x_position, y_zone23_boundary, -segment["dz_2"])
           nodes[f"{section_name}.3B"] = model.create_node(f"{section_name}.3B", x_position, y_zone12_boundary, -segment["dz_2"])
           nodes[f"{section_name}.4B"] = model.create_node(f"{section_name}.4B", x_position, y_right_edge, -segment["dz"])
       ```

         2. MULTIPLE ZONES WITH DIFFERENT MATERIALS/THICKNESSES:
        - Create separate material for each zone (material from INFO page parameters)
        - Zone 1 (right): thickness = dz, material = from params.info.material_grade
        - Zone 2 (middle): thickness = dz_2 (can differ from zones 1&3), material = from params.info.material_grade
        - Zone 3 (left): thickness = dz, material = from params.info.material_grade

    Example:
        ```python
        # Get material from INFO page parameters (when available)
        base_material_name = bridge_params.get("info", {}).get("material_grade", "C30/37")

        # Create materials for different zones (could be same or different materials)
        zone1_material = scia.Material(1, f"{base_material_name}_Zone1")
        zone2_material = scia.Material(2, f"{base_material_name}_Zone2")
        zone3_material = scia.Material(3, f"{base_material_name}_Zone3")

       # Create plates for each zone between adjacent cross-sections
       for i in range(len(bridge_segments_params) - 1):
           current_section = f"D{i+1}"
           next_section = f"D{i+2}"

           # Zone 1 plate (right side)
           zone1_nodes = [nodes[f"{current_section}.3"], nodes[f"{next_section}.3"],
                         nodes[f"{next_section}.4"], nodes[f"{current_section}.4"]]
           zone1_plate = model.create_plane(zone1_nodes, segments[i]["dz"],
                                          name=f"Zone1_{current_section}_{next_section}",
                                          material=zone1_material)

           # Zone 2 plate (middle)
           zone2_nodes = [nodes[f"{current_section}.2"], nodes[f"{next_section}.2"],
                         nodes[f"{next_section}.3"], nodes[f"{current_section}.3"]]
           zone2_plate = model.create_plane(zone2_nodes, segments[i]["dz_2"],
                                          name=f"Zone2_{current_section}_{next_section}",
                                          material=zone2_material)

           # Zone 3 plate (left side)
           zone3_nodes = [nodes[f"{current_section}.1"], nodes[f"{next_section}.1"],
                         nodes[f"{next_section}.2"], nodes[f"{current_section}.2"]]
           zone3_plate = model.create_plane(zone3_nodes, segments[i]["dz"],
                                          name=f"Zone3_{current_section}_{next_section}",
                                          material=zone3_material)
       ```

    3. LOAD CASES AND COMBINATIONS:
       - Define basic load cases: Dead load, Live load, Wind, Temperature
       - Create load combinations according to Eurocode (ULS/SLS)

    Example:
       ```python
       # Create load cases
       dead_load_case = model.create_load_case("DL", "Dead Load")
       live_load_case = model.create_load_case("LL", "Live Load")
       wind_load_case = model.create_load_case("WL", "Wind Load")

       # Apply loads to plates
       # Dead load: self-weight (automatic in SCIA)
       # Live load: traffic loads from load zone data
       for zone_plate in zone_plates:
           # Apply distributed load (N/m²)
           live_load = model.create_surface_load(
               load_case=live_load_case,
               surface=zone_plate,
               load_value=5000,  # 5 kN/m² typical traffic load
               direction="Z",  # Vertical downward
               coordinate_system="Global",
           )

       # Create load combinations (ULS)
       uls_combo = model.create_load_combination("ULS1", "Ultimate Limit State 1")
       uls_combo.add_load_case(dead_load_case, factor=1.35)  # γG = 1.35
       uls_combo.add_load_case(live_load_case, factor=1.5)  # γQ = 1.5

       # Create load combinations (SLS)
       sls_combo = model.create_load_combination("SLS1", "Serviceability Limit State 1")
       sls_combo.add_load_case(dead_load_case, factor=1.0)
       sls_combo.add_load_case(live_load_case, factor=1.0)
       ```

    4. BOUNDARY CONDITIONS AND SUPPORTS:
       - Add supports at bridge bearings/abutments
       - Define appropriate restraints based on bridge type

    Example:
       ```python
       # Support at start (abutment)
       start_support = model.create_point_support(
           node=nodes["D1.1"],
           ux=True,
           uy=True,
           uz=True,  # Fixed translation
           rx=False,
           ry=False,
           rz=False,  # Free rotation
       )

       # Support at end (expansion bearing)
       end_support = model.create_point_support(
           node=nodes[f"D{len(segments)}.1"],
           ux=False,
           uy=True,
           uz=True,  # Free in X (expansion)
           rx=False,
           ry=False,
           rz=False,
       )
       ```

    5. MESH REFINEMENT:
       - Define appropriate mesh density for different zones
       - Consider stress concentration areas

    Example:
       ```python
       # Create mesh setup for refined analysis
       mesh_setup = model.create_mesh_setup("BridgeMesh", max_element_size=1.0)

       # Apply mesh to all plates
       for plate in all_plates:
           model.assign_mesh_setup(plate, mesh_setup)
       ```

    Current implementation is a simplified rectangular plate for initial development.

    :param params: BridgeParametrization object with input parameters
    :type params: BridgeParametrization
    :returns: Tuple of (xml_file, def_file) for SCIA analysis
    :rtype: tuple[io.BytesIO, io.BytesIO]
    :raises ImportError: If VIKTOR SCIA module is not available

    """
    try:
        # Import VIKTOR SCIA module only when needed
        # This allows the core logic to be tested without VIKTOR dependencies
        from viktor.external import scia
    except ImportError as e:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.") from e

    # Create empty SCIA model using correct VIKTOR SCIA API
    model = scia.Model()

    # Initialize the node tracker to avoid duplicate nodes
    node_tracker = NodeTracker(model)

    # Create material
    material_name = "C30/37"
    material = scia.Material(0, material_name)

    # Get node coordinates and thicknesses
    nodes_dict, thickness_dict = create_node_and_thickness_dict(params)

    # Determine the number of sub-zones based on input dimensions
    dynamic_arrays = len(params.bridge_segments_array)

    # Dictionary to store SCIA nodes for reuse
    scia_nodes = {}

    # Create initial nodes for the first cross section
    for node_suffix in range(1, 5):  # Create all 4 nodes of first cross section
        node_name = f"K_dek:1_{node_suffix}"
        coords = nodes_dict.get(node_name)
        if coords is None:
            raise ValueError(f"Coordinates for node '{node_name}' not found in nodes_dict.")
        scia_nodes[node_name] = node_tracker.get_or_create_node(node_name, coords[0], coords[1], coords[2])

    # Create plates between cross sections
    for span in range(1, dynamic_arrays):
        # Create nodes for the next cross section if they don't exist
        next_span = span + 1
        for node_suffix in range(1, 5):  # Create all 4 nodes of next cross section
            node_name = f"K_dek:{next_span}_{node_suffix}"
            if node_name not in scia_nodes:  # Only create if not already exists
                coords = nodes_dict.get(node_name)
                if coords is None:
                    raise ValueError(f"Coordinates for node '{node_name}' not found in nodes_dict.")
                scia_nodes[node_name] = node_tracker.get_or_create_node(node_name, coords[0], coords[1], coords[2])

        # Create Zone 1 plate (using nodes 1 and 2 from current and next cross section)
        corner_nodes_z1 = [
            scia_nodes[f"K_dek:{span}_1"],
            scia_nodes[f"K_dek:{next_span}_1"],
            scia_nodes[f"K_dek:{next_span}_2"],
            scia_nodes[f"K_dek:{span}_2"],
        ]
        model.create_plane(corner_nodes_z1, thickness_dict.get(f"Z1_{span}"), name=f"Z1_{span}", material=material)

        # Create Zone 3 plate (using nodes 3 and 4 from current and next cross section)
        corner_nodes_z3 = [
            scia_nodes[f"K_dek:{span}_3"],
            scia_nodes[f"K_dek:{next_span}_3"],
            scia_nodes[f"K_dek:{next_span}_4"],
            scia_nodes[f"K_dek:{span}_4"],
        ]
        model.create_plane(corner_nodes_z3, thickness_dict.get(f"Z3_{span}"), name=f"Z3_{span}", material=material)

        # Create Zone 2 plate (using nodes 2 and 3 from both cross sections)
        corner_nodes_z2 = [
            scia_nodes[f"K_dek:{span}_2"],
            scia_nodes[f"K_dek:{next_span}_2"],
            scia_nodes[f"K_dek:{next_span}_3"],
            scia_nodes[f"K_dek:{span}_3"],
        ]
        model.create_plane(corner_nodes_z2, thickness_dict.get(f"Z2_{span}"), name=f"Z2_{span}", material=material)

    # Generate XML input files
    xml_file, def_file = model.generate_xml_input()

    return xml_file, def_file


def create_scia_analysis_from_template(xml_file: io.BytesIO, def_file: io.BytesIO, template_path: Path) -> Any:  # noqa: ANN401
    """
    Create SCIA analysis using template file and generated XML input.

    :param xml_file: Generated XML input file as a BytesIO stream
    :type xml_file: io.BytesIO
    :param def_file: Generated definition file as a BytesIO stream
    :type def_file: io.BytesIO
    :param template_path: Path to the ESA template file
    :type template_path: Path
    :returns: SCIA analysis object ready for execution
    :rtype: viktor.external.scia.SciaAnalysis
    :raises ImportError: If VIKTOR SCIA module is not available
    :raises FileNotFoundError: If template file doesn't exist
    """
    try:
        from viktor.core import File
        from viktor.external import scia
    except ImportError as e:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.") from e

    if not template_path.exists():
        raise FileNotFoundError(f"SCIA template file not found: {template_path}")

    # Load template file
    esa_template = File.from_path(template_path)

    # Create SCIA analysis using tutorial format: SciaAnalysis(input_xml, input_def, input_esa)
    return scia.SciaAnalysis(xml_file, def_file, esa_template)


def create_bridge_scia_model(params: BridgeParametrization, template_path: Path) -> tuple[Any, Any, Any]:
    """
    Main function to create complete SCIA model from bridge parameters.

    This is the primary interface function that:
    1. Extracts geometry from bridge parameters
    2. Creates SCIA model with rectangular plate approximation
    3. Sets up analysis with template file

    TODO: Integration with load zone data for realistic loading:

    LOAD ZONE INTEGRATION:
    The current implementation creates geometry only. For complete analysis, integrate with
    load zone data from params.load_zones_data_array to apply realistic traffic loads:

         ```python
     def create_bridge_scia_model(bridge_segments_params, template_path,
                                  load_zones_params=None, info_params=None):
         # Extract material from INFO page parameters
         material_grade = "C30/37"  # Default
         if info_params:
             material_grade = info_params.get("material_grade", "C30/37")

         # Current geometry creation with proper materials...
         xml_file, def_file = create_complex_scia_plate_model(bridge_geometry, material_grade)

         # Add load cases and load zone integration
         if load_zones_params:
             model = add_load_zones_to_scia_model(model, load_zones_params, bridge_segments_params)
             xml_file, def_file = model.generate_xml_input()  # Regenerate with loads

         # Create analysis...
         return xml_file, def_file, scia_analysis

    def add_load_zones_to_scia_model(model, load_zones_params, bridge_segments_params):
        # Map load zones to SCIA plate elements
        # Apply distributed loads based on load zone types (LM1, SV, etc.)
        # Consider load zone widths at each D-section (d1_width, d2_width, etc.)

        for zone_idx, load_zone in enumerate(load_zones_params):
            zone_type = load_zone.get("load_zone_type", "LM1")

            # Get load intensities for this zone type
            if zone_type == "LM1":
                characteristic_load = 9.0  # kN/m² (TS tandem + UDL)
            elif zone_type == "SV":
                characteristic_load = 15.0  # kN/m² (Special Vehicle)
            # ... other load types

            # Apply loads to appropriate plate elements for this zone
            # Consider varying zone width along bridge length (d1_width, d2_width, etc.)

        return model
    ```

    COORDINATE SYSTEM INTEGRATION:
    Ensure SCIA coordinate system matches the bridge coordinate system used in the 3D view
    and load zone calculations. Currently:
    - X: Bridge longitudinal direction (length)
    - Y: Bridge transverse direction (width, zones 1-2-3)
    - Z: Vertical (thickness direction)

    :param bridge_segments_params: Bridge segment parameters from VIKTOR
    :type bridge_segments_params: list[dict[str, Any]]
    :param template_path: Path to ESA template file
    :type template_path: Path
    :returns: Tuple of (xml_file, def_file, scia_analysis)
    :rtype: tuple[Any, Any, Any]
    :raises ValueError: If bridge parameters are invalid
    :raises FileNotFoundError: If template file doesn't exist
    :raises ImportError: If VIKTOR SCIA module is not available
    """
    # Create SCIA model
    xml_file, def_file = create_simple_scia_plate_model(params)

    # Create analysis with template
    scia_analysis = create_scia_analysis_from_template(xml_file, def_file, template_path)

    return xml_file, def_file, scia_analysis
