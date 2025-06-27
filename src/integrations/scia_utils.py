"""
SCIA Engineer utility functions for creating localized loads and patches.

This module provides helper functions to create specific load patches within larger
SCIA plane elements, using internal edges to define load areas.
"""

from typing import Any

# Type aliases for SCIA objects (using Any for external SDK types)
SciaModel: type[Any] = Any
SciaNode: type[Any] = Any
SciaPlane: type[Any] = Any
SciaLoadCase: type[Any] = Any
SciaSurfaceLoad: type[Any] = Any


def create_patch_surface_load(
    model: SciaModel,
    load_case: SciaLoadCase,
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_name: str = "PatchLoad",
) -> SciaSurfaceLoad:
    """
    Create a surface load on a specific 4-point patch by creating a separate load plane.

    This function creates a localized load area by:
    1. Creating nodes at the 4 corner points
    2. Creating a thin plane (patch) with these 4 nodes
    3. Applying surface load to the patch plane

    :param model: SCIA model instance
    :type model: SciaModel
    :param load_case: SCIA load case for the load application
    :type load_case: SciaLoadCase
    :param corner_points: List of 4 corner coordinates [(x1,y1,z1), (x2,y2,z2), (x3,y3,z3), (x4,y4,z4)]
                         Points should be ordered to form a valid rectangle/quadrilateral
    :type corner_points: list[tuple[float, float, float]]
    :param load_value: Load magnitude in [N/m²] (positive = downward for typical bridge loads)
    :type load_value: float
    :param load_name: Name identifier for the load (default: "PatchLoad")
    :type load_name: str

    :returns: Created SCIA surface load object
    :rtype: SciaSurfaceLoad
    :raises ValueError: If corner_points doesn't contain exactly 4 points
    :raises ImportError: If VIKTOR SCIA module is not available

    Example usage:
        >>> # Define wheel load patch corners (2m x 1m patch on bridge deck)
        >>> wheel_corners = [
        ...     (10.0, 5.0, 0.0),  # Point 1: x=10m, y=5m, z=0m
        ...     (12.0, 5.0, 0.0),  # Point 2: x=12m, y=5m, z=0m
        ...     (12.0, 6.0, 0.0),  # Point 3: x=12m, y=6m, z=0m
        ...     (10.0, 6.0, 0.0),  # Point 4: x=10m, y=6m, z=0m
        ... ]
        >>> # Apply 150 kN/m² wheel load (typical heavy vehicle)
        >>> wheel_load = create_patch_surface_load(
        ...     model=scia_model,
        ...     load_case=live_load_case,
        ...     corner_points=wheel_corners,
        ...     load_value=150000.0,  # 150 kN/m² in N/m²
        ...     load_name="WheelLoad_Axle1",
        ... )
    """
    try:
        # Import VIKTOR SCIA module only when needed
        from viktor.external import scia
    except ImportError as e:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.") from e

    # Validate input
    if len(corner_points) != 4:
        raise ValueError(f"Exactly 4 corner points required, got {len(corner_points)}")

    # STEP 1: Create nodes at patch corners
    # Use patch-specific naming to avoid conflicts with existing bridge nodes
    patch_nodes = []
    for i, (x, y, z) in enumerate(corner_points, 1):
        node_name = f"{load_name}_Corner_{i}"
        patch_node = model.create_node(node_name, x, y, z)
        patch_nodes.append(patch_node)

    # STEP 2: Create material for the load patch
    # Use material ID of 999 to avoid conflicts with bridge materials (typically 0, 1, 2, etc.)
    material = scia.Material(999, "C30/37")

    # STEP 3: Create a thin plane (patch) for the load area
    # PROVEN APPROACH: Create separate plane instead of using internal edges
    load_patch_plane = model.create_plane(patch_nodes, 0.01, material=material, name=f"{load_name}_Plane")

    # STEP 4: Apply surface load to the patch plane (vertical downward by default)
    return model.create_surface_load(
        name=load_name,
        load_case=load_case,
        plane=load_patch_plane,  # Apply to the dedicated patch plane
        direction=scia.SurfaceLoad.Direction.Z,
        load_type=scia.SurfaceLoad.Type.FORCE,
        load_value=load_value,
        c_sys=scia.SurfaceLoad.CSys.GLOBAL,
        location=scia.SurfaceLoad.Location.LENGTH,
    )


def create_wheel_load_pattern(
    model: SciaModel,
    load_case: SciaLoadCase,
    axle_position_x: float,
    axle_position_y: float,
    axle_load: float = 100000.0,
) -> list[SciaSurfaceLoad]:
    """
    Create a typical vehicle axle load pattern with two wheel loads.

    DUMMY VALUES: This function uses typical heavy vehicle dimensions.
    Real implementation should extract values from load zone parameters.

    :param model: SCIA model instance
    :type model: SciaModel

    :param load_case: SCIA load case for vehicle loads
    :type load_case: SciaLoadCase
    :param axle_position_x: Axle center position in bridge longitudinal direction [m]
    :type axle_position_x: float
    :param axle_position_y: Axle center position in bridge transverse direction [m]
    :type axle_position_y: float

    :param axle_load: Total axle load [N] (default: 100kN, distributed equally to wheels)
    :type axle_load: float
    :returns: List of created wheel surface loads [left_wheel, right_wheel]
    :rtype: list[SciaSurfaceLoad]

    Example usage:
        >>> # Create 200kN axle load at bridge midspan
        >>> axle_loads = create_wheel_load_pattern(
        ...     model=scia_model,
        ...     load_case=lm1_load_case,
        ...     axle_position_x=20.0,  # 20m from bridge start
        ...     axle_position_y=0.0,  # Bridge centerline
        ...     axle_load=200000.0,  # 200 kN total axle load
        ... )
    """
    # DUMMY VALUES: Use fixed wheel geometry (replace with real parameters)
    wheel_spacing = 2.0  # 2m between wheels
    wheel_contact_length = 0.6  # 0.6m contact patch length
    wheel_contact_width = 0.4  # 0.4m contact patch width

    # Calculate individual wheel load (half of axle load)
    wheel_load = axle_load / 2.0

    # Calculate wheel contact pressure [N/m²]
    contact_area = wheel_contact_length * wheel_contact_width
    wheel_pressure = wheel_load / contact_area

    # Define wheel positions (left and right of axle centerline)
    half_spacing = wheel_spacing / 2.0
    left_wheel_y = axle_position_y - half_spacing
    right_wheel_y = axle_position_y + half_spacing

    # Create wheel contact patches
    wheel_loads = []

    # Left wheel
    left_corners = [
        (axle_position_x - wheel_contact_length / 2, left_wheel_y - wheel_contact_width / 2, 0.0),
        (axle_position_x + wheel_contact_length / 2, left_wheel_y - wheel_contact_width / 2, 0.0),
        (axle_position_x + wheel_contact_length / 2, left_wheel_y + wheel_contact_width / 2, 0.0),
        (axle_position_x - wheel_contact_length / 2, left_wheel_y + wheel_contact_width / 2, 0.0),
    ]

    left_wheel_load = create_patch_surface_load(
        model=model,
        load_case=load_case,
        corner_points=left_corners,
        load_value=wheel_pressure,
        load_name=f"LeftWheel_X{axle_position_x:.1f}",
    )
    wheel_loads.append(left_wheel_load)

    # Right wheel
    right_corners = [
        (axle_position_x - wheel_contact_length / 2, right_wheel_y - wheel_contact_width / 2, 0.0),
        (axle_position_x + wheel_contact_length / 2, right_wheel_y - wheel_contact_width / 2, 0.0),
        (axle_position_x + wheel_contact_length / 2, right_wheel_y + wheel_contact_width / 2, 0.0),
        (axle_position_x - wheel_contact_length / 2, right_wheel_y + wheel_contact_width / 2, 0.0),
    ]

    right_wheel_load = create_patch_surface_load(
        model=model,
        load_case=load_case,
        corner_points=right_corners,
        load_value=wheel_pressure,
        load_name=f"RightWheel_X{axle_position_x:.1f}",
    )
    wheel_loads.append(right_wheel_load)

    return wheel_loads


def create_load_case_with_name(model: SciaModel, load_case_name: str, load_case_type: str = "VARIABLE") -> SciaLoadCase:
    """
    Helper function to create a SCIA load case with proper naming.

    DUMMY VALUES: Using standard load case types.
    Real implementation should integrate with bridge load combinations.

    :param model: SCIA model instance
    :type model: SciaModel
    :param load_case_name: Name for the load case (e.g., "LM1_TrafficLoad")
    :type load_case_name: str
    :param load_case_type: Type of load case - "PERMANENT" or "VARIABLE" (default: "VARIABLE")
    :type load_case_type: str
    :returns: Created SCIA load case
    :rtype: SciaLoadCase
    :raises ImportError: If VIKTOR SCIA module is not available
    """
    # Verify VIKTOR SCIA module is available
    try:
        import viktor.external.scia  # noqa: F401
    except ImportError as e:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.") from e

    # Create load case based on type
    if load_case_type.upper() == "PERMANENT":
        return model.create_load_case_permanent(load_case_name)
    if load_case_type.upper() == "VARIABLE":
        return model.create_load_case_variable(load_case_name)
    raise ValueError(f"Invalid load case type '{load_case_type}'. Use 'PERMANENT' or 'VARIABLE'")


def example_usage_simple_patch_load(
    model: SciaModel,
) -> SciaSurfaceLoad:
    """
    Example function demonstrating how to create a simple 4-point patch load.

    DUMMY VALUES CLEARLY MARKED: This function shows how colleagues can use the patch loading system.
    Replace dummy coordinates and load values with real bridge parameters.

    :param model: SCIA model instance with existing bridge geometry
    :type model: SciaModel
    :returns: Created surface load object
    :rtype: SciaSurfaceLoad

    Example integration in bridge analysis:
        >>> # After creating bridge model with plates
        >>> scia_model = create_simple_scia_plate_model(params)
        >>> # Apply a simple patch load (creates its own patch plane)
        >>> patch_load = example_usage_simple_patch_load(scia_model)
        >>> # Generate XML with loads included
        >>> xml_file, def_file = scia_model.generate_xml_input()
    """
    # DUMMY VALUES - Replace with real bridge coordinates and load data

    # Create load case for the patch loads
    live_load_case = create_load_case_with_name(model, "TrafficLoad_LM1", "VARIABLE")

    # Define a 2m x 1.5m load patch at position (15m longitudinal, 3m transverse)
    # DUMMY COORDINATES - Replace with actual bridge coordinate system
    patch_corners = [
        (15.0, 3.0, 0.0),  # Corner 1: x=15m, y=3m (bottom-left)
        (17.0, 3.0, 0.0),  # Corner 2: x=17m, y=3m (bottom-right)
        (17.0, 4.5, 0.0),  # Corner 3: x=17m, y=4.5m (top-right)
        (15.0, 4.5, 0.0),  # Corner 4: x=15m, y=4.5m (top-left)
    ]

    # DUMMY LOAD VALUE - Replace with actual traffic load from Eurocode
    # 100 kN/m² = 100,000 N/m² (typical heavy vehicle pressure)
    load_pressure = 100000.0  # N/m²

    # Create the patch load
    return create_patch_surface_load(
        model=model,
        load_case=live_load_case,
        corner_points=patch_corners,
        load_value=load_pressure,
        load_name="ExamplePatchLoad",
    )
