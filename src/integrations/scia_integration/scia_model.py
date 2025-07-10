"""
SCIA model creation utilities.

This module handles the creation of complete SCIA bridge models including
geometry, nodes, plates, and loads. Requires VIKTOR SCIA SDK.
Does NOT handle XML generation or analysis execution.
"""

from typing import Any, TypeAlias

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock objects for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False

# Import geometry extraction functions from dedicated module
from .scia_bridge_geometry import create_node_and_thickness_dict

# Import load application functions from dedicated module
from .scia_loads import add_theoretical_tandem_loads, create_load_infrastructure
from .scia_supports import create_scia_line_supports

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
        """Initialize the node tracker."""
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


def create_multi_zone_bridge_model(params: Any) -> Any:  # noqa: ANN401
    """
    Create SCIA bridge model with multi-zone plates and variable thickness.

    Creates a sophisticated bridge model with:
    - Cross-sections at each bridge segment
    - Three zone plates (Zone 1, 2, 3) with variable thickness
    - Proper coordinate system and node management
    - NO LOADS (geometry only - use create_complete_bridge_model for loads)

    Coordinate system:
    - X: Longitudinal (cumulative segment lengths)
    - Y: Transverse (zone boundaries from bz1, bz2, bz3)
    - Z: Vertical (0 at top surface)

    Zone layout: Zone 3 | Zone 2 | Zone 1
                |--bz3--|--bz2--|--bz1--|

    :param params: Bridge parameters
    :returns: SCIA model object with bridge geometry only
    :rtype: Any
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    # Create model and material
    model = scia.Model()
    node_tracker = NodeTracker(model)
    material = scia.Material(0, "C30/37")

    # Get geometry data
    nodes_dict, thickness_dict = create_node_and_thickness_dict(params)
    dynamic_arrays = len(params.bridge_segments_array)
    scia_nodes = {}
    scia_planes = []

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

        # Create zone plates and collect them in a list with their numbering for sorting
        # Each entry: (zone_number, span_number, plane_object)
        # Zone 1 plate
        corner_nodes_z1 = [
            scia_nodes[f"K_dek:{span}_1"],
            scia_nodes[f"K_dek:{next_span}_1"],
            scia_nodes[f"K_dek:{next_span}_2"],
            scia_nodes[f"K_dek:{span}_2"],
        ]
        plane_z1 = model.create_plane(corner_nodes_z1, thickness_dict.get(f"Z1_{span}"), name=f"Z1_{span}", material=material)
        scia_planes.append((1, span, plane_z1))

        # Zone 3 plate
        corner_nodes_z3 = [
            scia_nodes[f"K_dek:{span}_3"],
            scia_nodes[f"K_dek:{next_span}_3"],
            scia_nodes[f"K_dek:{next_span}_4"],
            scia_nodes[f"K_dek:{span}_4"],
        ]
        plane_z3 = model.create_plane(corner_nodes_z3, thickness_dict.get(f"Z3_{span}"), name=f"Z3_{span}", material=material)
        scia_planes.append((3, span, plane_z3))

        # Zone 2 plate
        corner_nodes_z2 = [
            scia_nodes[f"K_dek:{span}_2"],
            scia_nodes[f"K_dek:{next_span}_2"],
            scia_nodes[f"K_dek:{next_span}_3"],
            scia_nodes[f"K_dek:{span}_3"],
        ]
        plane_z2 = model.create_plane(corner_nodes_z2, thickness_dict.get(f"Z2_{span}"), name=f"Z2_{span}", material=material)
        scia_planes.append((2, span, plane_z2))

    # Sort planes by (span, zone) for consistent ordering: all Z1, Z2, Z3 per span
    scia_planes_sorted = [plane for _, _, plane in sorted(scia_planes, key=lambda x: (x[1], x[0]))]
    # Create line supports on the first and last three edges of the bridge plates
    create_scia_line_supports(model, scia_planes_sorted)

    return model


def create_complete_bridge_model(params: Any) -> Any:  # noqa: ANN401
    """
    Create complete SCIA bridge model with geometry and loads.

    This is the main function for creating a fully functional bridge model that includes:
    - Multi-zone bridge geometry (via create_multi_zone_bridge_model)
    - Load infrastructure (groups, basic load cases)
    - Applied theoretical tandem loads
    - Load combinations

    Use this function when you need a complete, analysis-ready bridge model.
    Use create_multi_zone_bridge_model() only when you need geometry without loads.

    :param params: Bridge parameters
    :returns: Complete SCIA model object with geometry and loads
    :rtype: Any
    """
    # Step 1: Create bridge geometry
    scia_model = create_multi_zone_bridge_model(params)

    # Step 2: Create load infrastructure (groups and basic load cases)
    infrastructure = create_load_infrastructure(scia_model)
    load_groups = infrastructure["load_groups"]

    # Step 3: Add theoretical tandem loads
    #add_theoretical_tandem_loads(scia_model, params, load_groups["traffic"])

    return scia_model


# Backwards compatibility alias
create_simple_scia_plate_model = create_multi_zone_bridge_model
