"""
SCIA Engineer integration module for bridge analysis.

This module provides functionality to create SCIA models from bridge parameters.
Currently implements a simple rectangular plate model as a starting point.

Future enhancements needed:
- Support for complex bridge geometry matching the actual bridge shape (1:1 with bridge segments)
- Variable thickness across zones (zone 1, 2, 3 have different thickness values)
- Load cases and combinations from params.input.belastingzones and belastingcombinaties
- Support for different bridge types from params.info.bridge_type and static_system
- Material property customization from params.info.concrete_strength_class
- Reinforcement modeling from params.input.geometrie_wapening zones
- Extract all geometry from params.input.dimensions.bridge_segments_array instead of hardcoded values
"""

import io
from io import BytesIO
from pathlib import Path
from typing import Any, TypeAlias, Union

from app.bridge.parametrization import (
    BridgeParametrization,
)
from src.integrations.scia_utils import create_load_case_with_name, create_patch_surface_load

# Type alias for SCIA Engineer node objects
SciaNode: TypeAlias = object  # More specific type if available from SCIA API
SciaModel: TypeAlias = "SciaModelProtocol"


class SciaModelProtocol:
    """
    Protocol for SCIA model objects used in SCIA integration.

    This class defines the expected interface for SCIA model objects, including methods for node creation and other model manipulations.
    """

    def create_node(self, name: str, x: float, y: float, z: float) -> "SciaNode":
        """
        Create a node in the SCIA model.

        :param name: Name of the node
        :type name: str
        :param x: X-coordinate of the node
        :type x: float
        :param y: Y-coordinate of the node
        :type y: float
        :param z: Z-coordinate of the node
        :type z: float
        :returns: The created SCIA node object
        :rtype: SciaNode
        """
        # Define the expected behavior of the create_node method


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


def create_simple_scia_plate_model(params: BridgeParametrization) -> Union[tuple[BytesIO, BytesIO]]:
    """
    Create a complete SCIA bridge model from bridge parameters.

    This function creates a detailed bridge model with:
    - Multiple cross-sections at each D1, D2, D3... location from bridge_segments_array
    - Three separate zone plates (Zone 1, Zone 2, Zone 3) between cross-sections
    - Variable thickness per zone (dz for zones 1&3, dz_2 for zone 2)
    - Proper node positioning based on actual bridge geometry (bz1, bz2, bz3 widths)
    - Cumulative length calculation from segment distances
    - Concrete material (C30/37)
    - Demonstration load patches using scia_utils functions

    Bridge Structure Created:
    - **Nodes**: Created at each cross-section with naming "K_dek:X_Y" where X=section, Y=zone
    - **Zone 1 plates**: Right side of bridge (thickness = dz)
    - **Zone 2 plates**: Middle of bridge (thickness = dz_2, can differ from zones 1&3)
    - **Zone 3 plates**: Left side of bridge (thickness = dz)
    - **Load demonstrations**: Example wheel loads and equipment loads

    Coordinate System:
    - X: Bridge longitudinal direction (cumulative segment lengths)
    - Y: Bridge transverse direction (zone boundaries based on bz1, bz2, bz3)
    - Z: Vertical direction (0 at top surface, negative downward)

    Zone Layout (transverse direction):
    ```
    Zone 3    Zone 2    Zone 1
    |--bz3--|--bz2--|--bz1--|
    ```

    TODO: Future enhancements:
    - Replace _add_dummy_wheel_loads() with real load zone data from params.input.belastingzones
    - Add material customization from params.info.concrete_strength_class
    - Add support conditions based on bridge type
    - Add load combinations for ULS/SLS analysis

    :param params: BridgeParametrization object with bridge segment data
    :type params: BridgeParametrization
    :returns: Tuple of (xml_file, def_file) for SCIA analysis
    :rtype: tuple[io.BytesIO, io.BytesIO]
    :raises ImportError: If VIKTOR SCIA module is not available
    :raises ValueError: If bridge segment data is invalid
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

    # Add dummy wheel loads to demonstrate the utils
    _add_dummy_wheel_loads(model)

    # Generate XML input files
    xml_file, def_file = model.generate_xml_input()

    return xml_file, def_file


def _add_dummy_wheel_loads(model: SciaModel) -> None:
    """
    Add dummy load patterns to the SCIA model for demonstration. This entire function can be replaced with the load zone data from the params.input.belastingzones.

    This function shows how the interface layer uses the generic utility functions
    from `scia_utils.py` to add specific loads to the model. Demonstrates both:
    1. Individual patch loads (for custom/special loads)
    2. Vehicle load patterns (for standard traffic loads)

    DUMMY VALUES: This function uses hardcoded coordinates and load values.
    A real implementation would derive these from `params.input.belastingzones`.

    :param model: The SCIA model instance to which loads will be added.
    :type model: SciaModel
    """
    # 1. Create load cases for different load types
    traffic_load_case = create_load_case_with_name(model, "LM1_Traffic", "VARIABLE")
    special_load_case = create_load_case_with_name(model, "SpecialEquipment", "VARIABLE")

    # 2. EXAMPLE: Individual patch loads for special equipment
    # DUMMY VALUES: Construction equipment or special loads
    
    # Crane outrigger patch (1.5m x 1.0m at x=5m, y=2m)
    crane_corners = [
        (4.25, 1.5, 0.0),   # Bottom-left: x-0.75, y-0.5
        (5.75, 1.5, 0.0),   # Bottom-right: x+0.75, y-0.5
        (5.75, 2.5, 0.0),   # Top-right: x+0.75, y+0.5
        (4.25, 2.5, 0.0),   # Top-left: x-0.75, y+0.5
    ]
    create_patch_surface_load(
        model=model,
        load_case=special_load_case,
        corner_points=crane_corners,
        load_value=50000.0,     # 50 kN/m² equipment pressure
        load_name="CraneOutrigger_1"
    )

    # Maintenance equipment patch (2.0m x 0.8m at x=15m, y=-1.5m)
    maintenance_corners = [
        (14.0, -1.9, 0.0),  # Bottom-left: x-1.0, y-0.4
        (16.0, -1.9, 0.0),  # Bottom-right: x+1.0, y-0.4
        (16.0, -1.1, 0.0),  # Top-right: x+1.0, y+0.4
        (14.0, -1.1, 0.0),  # Top-left: x-1.0, y+0.4
    ]
    create_patch_surface_load(
        model=model,
        load_case=special_load_case,
        corner_points=maintenance_corners,
        load_value=75000.0,     # 75 kN/m² equipment pressure
        load_name="MaintenanceEquip_1"
    )

    # 3. EXAMPLE: Individual wheel loads using existing tandem system data
    # TODO: Integrate with tandem_systems_axes_single_lane() from loadcase_helper_functions.py
    # This would use the existing backend logic and convert to SCIA loads via create_patch_surface_load()
    
    # DUMMY EXAMPLE: Single wheel load patch
    wheel_corners = [
        (9.8, -0.2, 0.0),   # Bottom-left
        (10.2, -0.2, 0.0),  # Bottom-right  
        (10.2, 0.2, 0.0),   # Top-right
        (9.8, 0.2, 0.0),    # Top-left
    ]
    create_patch_surface_load(
        model=model,
        load_case=traffic_load_case,
        corner_points=wheel_corners,
        load_value=468750.0,  # 468.75 kN/m² (example wheel pressure)
        load_name="ExampleWheel_1"
    )


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
    :param concrete_material: Concrete material grade (e.g., "C30/37") from material system
    :type concrete_material: str | None
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
