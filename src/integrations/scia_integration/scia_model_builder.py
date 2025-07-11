"""
Module for constructing SCIA models using the VIKTOR SDK.

This module provides a concrete implementation of the SciaBuilderProtocol,
wrapping the viktor.external.scia SDK.
"""

from typing import Any, Literal

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock scia module for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False


class SciaModelBuilder:
    """
    A builder for SCIA models that uses the VIKTOR SDK.

    This class keeps track of the created SCIA objects (nodes, plates, etc.)
    and provides methods to add new components to the model.
    """

    def __init__(self) -> None:
        """Initialize the SciaModelBuilder."""
        if not VIKTOR_AVAILABLE or scia is None:
            raise ImportError("VIKTOR SDK with SCIA integration is required to use SciaModelBuilder.")
        self._model = scia.Model()
        self._nodes: dict[str, Any] = {}
        self._materials: dict[str, Any] = {}
        self._plates: dict[str, Any] = {}

    def get_model(self) -> Any:
        """
        Returns the underlying SCIA model object.

        :returns: The raw SCia model object from the VIKTOR SDK.
        """
        return self._model

    def add_node(self, name: str, x: float, y: float, z: float) -> Any:
        """
        Adds a node to the model.

        :param name: The name of the node.
        :param x: The x-coordinate of the node.
        :param y: The y-coordinate of the node.
        :param z: The z-coordinate of the node.
        :returns: The created node object.
        """
        if name in self._nodes:
            raise ValueError(f"Node with name '{name}' already exists.")
        node = self._model.create_node(name, x, y, z)
        self._nodes[name] = node
        return node

    def add_material(self, name: str, material_id: int = 0) -> Any:
        """
        Adds a material to the model.

        :param name: The name of the material (e.g., "C30/37").
        :param material_id: The SCIA material ID. Defaults to 0.
        :returns: The created material object.
        """
        if name in self._materials:
            return self._materials[name]  # Return existing material if already created
        material = scia.Material(material_id, name)
        self._materials[name] = material
        return material

    def add_plate(
        self,
        name: str,
        corner_node_names: list[str],
        thickness: float,
        material_name: str,
    ) -> Any:
        """
        Adds a plate (plane) to the model.

        :param name: The name of the plate.
        :param corner_node_names: A list of four node names defining the plate's corners.
        :param thickness: The thickness of the plate.
        :param material_name: The name of the material for the plate.
        :returns: The created plate object.
        """
        if name in self._plates:
            raise ValueError(f"Plate with name '{name}' already exists.")
        if material_name not in self._materials:
            raise ValueError(f"Material '{material_name}' not found. Please add it first.")
        material = self._materials[material_name]
        corner_nodes = [self._nodes[node_name] for node_name in corner_node_names]
        plate = self._model.create_plane(corner_nodes, thickness, name=name, material=material)
        self._plates[name] = plate
        return plate

    def add_line_support_on_plate_edge(
        self,
        name: str,
        plate_name: str,
        edge_index: int,
        support_type: str,
    ) -> Any:
        """
        Adds a line support on a specified edge of a plate.

        :param name: The name of the line support.
        :param plate_name: The name of the plate to apply the support to.
        :param edge_index: The index of the edge (0-3).
        :param support_type: The type of support (e.g., "Rx,Ry,Rz,Tx,Ty,Tz").
        :returns: The created support object.
        """
        if plate_name not in self._plates:
            raise ValueError(f"Plate with name '{plate_name}' not found.")
        plate = self._plates[plate_name]
        support = self._model.create_line_support_on_plate_edge(name, plate, edge_index, support_type)
        return support

    def add_load_group(
        self,
        name: str,
        load_option: Literal["PERMANENT", "VARIABLE"],
        relation: Literal["STANDARD", "TOGETHER", "EXCLUSIVE"],
        load_type: str | None = None,
    ) -> Any:
        """
        Adds a load group to the model.

        :param name: The name of the load group.
        :param load_option: The load option ("PERMANENT" or "VARIABLE").
        :param relation: The relation type ("STANDARD", "TOGETHER", "EXCLUSIVE").
        :param load_type: The specific load type (e.g., "CAT_G_TRAFFIC_ROAD"). Optional.
        """
        load_group = self._model.create_load_group(name, load_option, relation, load_type)
        return load_group

    def add_load_case(
        self,
        name: str,
        description: str,
        case_type: Literal["PERMANENT", "VARIABLE"],
        group_name: str,
        **kwargs: str,
    ) -> Any:
        """
        Adds a load case to the model.

        :param name: The name of the load case.
        :param description: A description for the load case.
        :param case_type: The type of case ("PERMANENT" or "VARIABLE").
        :param group_name: The name of the load group this case belongs to.
        :param kwargs: Additional keyword arguments for the SCIA SDK.
        """
        load_case = self._model.create_load_case(
            name,
            case_type,
            group=group_name,
            description=description,
            **kwargs,
        )
        return load_case

    def add_load_combination(
        self,
        name: str,
        comb_type: str,
        description: str,
        cases: list[tuple[str, float]],
    ) -> Any:
        """
        Adds a load combination to the model.

        :param name: The name of the combination.
        :param comb_type: The type of combination (e.g., "ULS_GEO_STR_B").
        :param description: A description for the combination.
        :param cases: A list of tuples, each containing a load case name and its factor.
        """
        combination = self._model.create_load_combination(name, comb_type, description, cases=cases)
        return combination

    def add_surface_load(
        self,
        name: str,
        case_name: str,
        plate_name: str,
        value: float,
        direction: str = "Z",
    ) -> Any:
        """
        Adds a surface load to a plate.

        :param name: The name of the load.
        :param case_name: The name of the load case to add the load to.
        :param plate_name: The name of the plate where the load is applied.
        :param value: The magnitude of the load.
        :param direction: The direction of the load ('X', 'Y', or 'Z').
        """
        if plate_name not in self._plates:
            raise ValueError(f"Plate with name '{plate_name}' not found.")
        plate = self._plates[plate_name]
        surface_load = self._model.create_surface_load(name, case_name, plate, value, direction=direction)
        return surface_load
