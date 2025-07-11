"""
SCIA supports builder module.

This module contains functions for creating SCIA support objects (e.g., Line Supports)
from their corresponding pure Python definitions. This isolates the VIKTOR SDK-
dependent "build" logic from the "definition" logic.
"""

from typing import Any

from src.integrations.scia_integration.scia_definitions import LineSupportDefinition
from src.integrations.scia_integration.scia_load_combinations import (
    SciaLoadCombination,
    SciaModel,
)

try:
    from viktor.external import scia
except ImportError:
    scia = None


def create_line_support_from_definition(model: SciaModel, definition: LineSupportDefinition, plates: dict[str, Any]) -> SciaLoadCombination:
    """
    Create a SCIA Line Support from a LineSupportDefinition.

    :param model: The SCIA model object.
    :param definition: The LineSupportDefinition object.
    :param plates: A dictionary of existing SCIA plate objects, keyed by name.
    :return: The created SCIA LineSupport object.
    """
    if definition.plane_name not in plates:
        raise ValueError(f"Plate '{definition.plane_name}' not found for line support '{definition.name}'.")

    target_plane = plates[definition.plane_name]

    # Map freedom strings to SCIA Freedom enum
    freedom_map = {
        "FREE": scia.LineSupport.Freedom.FREE,
        "RIGID": scia.LineSupport.Freedom.RIGID,
        "FLEXIBLE": scia.LineSupport.Freedom.FLEXIBLE,
    }

    return model.create_line_support_on_plane(
        (target_plane, definition.edge_index),
        name=definition.name,
        x=freedom_map[definition.freedom["x"]],
        y=freedom_map[definition.freedom["y"]],
        z=freedom_map[definition.freedom["z"]],
        rx=freedom_map[definition.freedom["rx"]],
        ry=freedom_map[definition.freedom["ry"]],
        rz=freedom_map[definition.freedom["rz"]],
        stiffness_x=definition.stiffness.get("stiffness_x"),
        stiffness_y=definition.stiffness.get("stiffness_y"),
    )
