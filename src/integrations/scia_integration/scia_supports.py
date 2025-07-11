"""Module for defining SCIA support elements."""

from .scia_definitions import LineSupportDefinition, PlateDefinition


def define_line_supports(plate_definitions: list[PlateDefinition]) -> list[LineSupportDefinition]:
    """
    Define line supports on the first and last edges of the bridge deck.

    :param plate_definitions: A list of PlateDefinition objects.
    :return: A list of LineSupportDefinition objects.
    """
    if not plate_definitions:
        return []

    # Determine the last section number. It is max_span_number + 1.
    span_numbers = (
        int(plate_def.name.split("_")[1])
        for plate_def in plate_definitions
        if len(plate_def.name.split("_")) > 1 and plate_def.name.split("_")[1].isdigit()
    )
    max_span_number = max(span_numbers, default=0)
    last_section_number = max_span_number + 1

    # The logic from `get_line_support_edges_for_bridge` assumes an ordered list of planes.
    # The plate definitions are created span-by-span, zone-by-zone (Z1, Z2, Z3).
    # This order is consistent and can be used directly.
    support_defs = []

    # Supports at the start of the bridge (cross section 1)
    for plate_def in plate_definitions[:3]:
        zone_number = int(plate_def.name.split("_")[0][1:])
        support_defs.append(
            LineSupportDefinition(
                name=f"SLB_opleg_as_1:{zone_number}",
                plane_name=plate_def.name,
                edge_index=4,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            )
        )

    # Supports at the end of the bridge (last 3 plates, edge index 2)
    for plate_def in plate_definitions[-3:]:
        zone_number = int(plate_def.name.split("_")[0][1:])
        support_defs.append(
            LineSupportDefinition(
                name=f"SLB_opleg_as_{last_section_number}:{zone_number}",
                plane_name=plate_def.name,
                edge_index=2,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            )
        )

    return support_defs
