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
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BridgeGeometryData:
    """
    Data structure for bridge geometry information extracted from bridge parameters.

    :param total_length: Total length of the bridge in meters
    :type total_length: float
    :param total_width: Total width of the bridge in meters
    :type total_width: float
    :param thickness: Thickness of the bridge deck in meters
    :type thickness: float
    :param material_name: Name of the material to use
    :type material_name: str
    """

    total_length: float
    total_width: float
    thickness: float
    material_name: str


def extract_bridge_geometry_from_params(bridge_segments_params: list[dict[str, Any]], concrete_material: str | None = None) -> BridgeGeometryData:
    """
    Extract bridge geometry data from bridge segment parameters.

    Currently creates a simple rectangular approximation:
    - Length: Sum of all segment lengths
    - Width: Uses width of first segment only (bz1 + bz2 + bz3)
    - Thickness: Hardcoded to 0.5m

    TODO: Future improvements:
    - Support variable width along bridge length from params.input.dimensions.bridge_segments_array
    - Support variable thickness per zone (dz, dz_2 parameters) from bridge segments
    - Handle complex bridge shapes with proper geometry interpolation
    - Extract materials from params.info.concrete_strength_class for realistic modeling
    - Add reinforcement support from params.input.geometrie_wapening zones
    - Implement load cases from params.input.belastingzones.load_zones_array

    :param bridge_segments_params: List of bridge segment parameter dictionaries
    :type bridge_segments_params: list[dict[str, Any]]
    :param concrete_material: Concrete material grade (e.g., "C30/37") from material system
    :type concrete_material: str | None
    :returns: Bridge geometry data for SCIA model creation
    :rtype: BridgeGeometryData
    :raises ValueError: If bridge_segments_params is empty or invalid
    """
    if not bridge_segments_params:
        raise ValueError("No bridge segments provided")

    # Calculate total length: sum of all segment lengths
    # Note: first segment usually has l=0 (starting point), so we sum all l values
    total_length = sum(float(segment.get("l", 0)) for segment in bridge_segments_params)

    if total_length <= 0:
        raise ValueError("Bridge total length must be positive")

    # Use width of first segment as approximation
    # This should be enhanced to handle variable width along bridge length
    first_segment = bridge_segments_params[0]
    bz1 = float(first_segment.get("bz1", 0))
    bz2 = float(first_segment.get("bz2", 0))
    bz3 = float(first_segment.get("bz3", 0))
    total_width = bz1 + bz2 + bz3

    if total_width <= 0:
        raise ValueError("Bridge total width must be positive")

    # Variable thickness support - NO AVERAGING, SEPARATE ZONES REQUIRED
    # Currently using hardcoded thickness, but should use actual bridge dimensions:
    #
    # CORRECT THICKNESS IMPLEMENTATION (3 SEPARATE ZONES):
    # - Zone 1 (right side, width=bz1): thickness = dz
    # - Zone 2 (middle, width=bz2): thickness = dz_2 (can be different from zones 1&3)
    # - Zone 3 (left side, width=bz3): thickness = dz
    #
    # NOTE: Do NOT use average thickness - create 3 separate plate elements with their own thicknesses
    # The simplified rectangular model should be replaced with proper multi-zone implementation
    # Extract actual thickness from bridge_segments_array when zone-specific implementation is added
    # Use construction_height for realistic deck thickness (convert from mm to m) when available
    thickness = 0.5  # Hardcoded for now - will be replaced by 3-zone implementation

    # Material selection from centralized material system
    # Use provided material or get default from centralized system
    if concrete_material is None:
        from src.common.materials import get_default_materials

        defaults = get_default_materials()
        material_name = defaults["concrete"]
    else:
        # Validate material exists in project database and is SCIA-compatible
        from src.common.materials import get_supported_scia_materials, normalize_material_name, validate_material_exists

        if not validate_material_exists(concrete_material, "concrete"):
            supported_materials = get_supported_scia_materials()["concrete"]
            raise ValueError(
                f"Concrete material '{concrete_material}' not found in project database. SCIA-supported materials: {supported_materials}"
            )
        # Use normalized material name to ensure compatibility with CSV database format
        material_name = normalize_material_name(concrete_material)

    return BridgeGeometryData(total_length=total_length, total_width=total_width, thickness=thickness, material_name=material_name)


def create_simple_scia_plate_model(bridge_geometry: BridgeGeometryData) -> tuple[Any, Any]:
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

    :param bridge_geometry: Bridge geometry data
    :type bridge_geometry: BridgeGeometryData
    :returns: Tuple of (xml_file, def_file) for SCIA analysis
    :rtype: tuple[Any, Any]
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

    # Create material - using correct VIKTOR SCIA API from tutorial
    # The Material constructor requires (material_id, material_name) as shown in tutorial
    material = scia.Material(0, bridge_geometry.material_name)

    # Create corner nodes for rectangular plate
    # Coordinate system: X = length direction, Y = width direction, Z = height
    node1 = model.create_node("N1", 0, 0, 0)
    node2 = model.create_node("N2", bridge_geometry.total_length, 0, 0)
    node3 = model.create_node("N3", bridge_geometry.total_length, bridge_geometry.total_width, 0)
    node4 = model.create_node("N4", 0, bridge_geometry.total_width, 0)

    # Create rectangular plane (plate) element using correct API from tutorial
    # From tutorial: model.create_plane(corner_nodes, thickness, name='...', material=material)
    corner_nodes = [node1, node2, node3, node4]
    model.create_plane(corner_nodes, bridge_geometry.thickness, name="BridgePlate", material=material)

    # Skip mesh setup for now - can be added later if needed
    # Basic mesh will be handled by SCIA automatically

    # Generate XML input files
    xml_file, def_file = model.generate_xml_input()

    return xml_file, def_file


def create_scia_analysis_from_template(xml_file: io.BytesIO, def_file: io.BytesIO, template_path: Path) -> Any:  # noqa: ANN401
    """
    Create SCIA analysis using template file and generated XML input.

    :param xml_file: Generated XML input file
    :type xml_file: io.BytesIO
    :param def_file: Generated definition file
    :type def_file: io.BytesIO
    :param template_path: Path to the ESA template file
    :type template_path: Path
    :returns: SCIA analysis object ready for execution
    :rtype: Any (SCIA analysis object)
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


def create_bridge_scia_model(
    bridge_segments_params: list[dict[str, Any]], template_path: Path, concrete_material: str | None = None
) -> tuple[Any, Any, Any]:
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
    # Extract bridge geometry with material
    bridge_geometry = extract_bridge_geometry_from_params(bridge_segments_params, concrete_material)

    # Create SCIA model
    xml_file, def_file = create_simple_scia_plate_model(bridge_geometry)

    # Create analysis with template
    scia_analysis = create_scia_analysis_from_template(xml_file, def_file, template_path)

    return xml_file, def_file, scia_analysis
