"""Module for defining SCIA support elements."""

from .scia_model_interface import SciaLineSupport, SciaModelBuilder


def create_line_supports(builder: SciaModelBuilder, plate_names: list[str]) -> list[SciaLineSupport]:
    """
    Define and create line supports on the first and last edges of the bridge deck.

    :param builder: The SCIA model builder instance.
    :param plate_names: An ordered list of created plate names.
    :return: A list of the created LineSupport objects.
    """
    if not plate_names:
        return []

    # Determine the last section number from the plate names.
    # e.g., for plates "Z1_1", "Z2_1", "Z3_1", "Z1_2", etc., the span numbers are 1, 2.
    span_numbers = {int(name.split("_")[1]) for name in plate_names if len(name.split("_")) > 1 and name.split("_")[1].isdigit()}
    max_span_number = max(span_numbers, default=0)
    last_section_number = max_span_number + 1

    # The logic relies on an ordered list of plates, created span-by-span, zone-by-zone.
    support_objects = []

    # Supports at the start of the bridge (first 3 plates, edge index 4)
    for plate_name in plate_names[:3]:
        zone_number = int(plate_name.split("_")[0][1:])
        support_objects.append(
            builder.create_line_support_on_plane(
                name=f"SLB_opleg_as_1:{zone_number}",
                plane_name=plate_name,
                edge_index=4,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            )
        )

    # Supports at the end of the bridge (last 3 plates, edge index 2)
    for plate_name in plate_names[-3:]:
        zone_number = int(plate_name.split("_")[0][1:])
        support_objects.append(
            builder.create_line_support_on_plane(
                name=f"SLB_opleg_as_{last_section_number}:{zone_number}",
                plane_name=plate_name,
                edge_index=2,
                freedom={"x": "FLEXIBLE", "y": "FLEXIBLE", "z": "RIGID", "rx": "FREE", "ry": "RIGID", "rz": "RIGID"},
                stiffness={"stiffness_x": 1e7, "stiffness_y": 1e6},
            )
        )

    return support_objects


def create_all_supports(builder: SciaModelBuilder, plate_names: list[str]) -> list[SciaLineSupport]:
    """
    Define and create all support types for the bridge model.

    :param builder: The SCIA model builder instance.
    :param plate_names: An ordered list of created plate names.
    :return: A list of all created support objects.
    """
    all_supports = []
    all_supports.extend(create_line_supports(builder, plate_names))
    # Extend with other support types if needed

    return all_supports
