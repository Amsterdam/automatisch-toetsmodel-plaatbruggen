"""
SCIA Engineer utility functions for creating localized loads and patches.

This module provides helper functions to create specific load patches within larger
SCIA plane elements, using internal edges to define load areas.
"""

from typing import Any, TypeAlias

# Type aliases for SCIA objects (using Any for external SDK types)
SciaModel: TypeAlias = Any
SciaNode: TypeAlias = Any
SciaPlane: TypeAlias = Any
SciaLoadCase: TypeAlias = Any
SciaSurfaceLoad: TypeAlias = Any


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
