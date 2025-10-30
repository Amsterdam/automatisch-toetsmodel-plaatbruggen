"""Module for defining SCIA support elements."""

from src.integrations.scia_integration.scia_enums import LineSupportFreedom

from .scia_model_interface import SciaLineSupport, SciaModelBuilder


def _get_support_freedom_and_stiffness(support_type: str) -> tuple[dict[str, LineSupportFreedom], dict[str, float]]:
    """
    Get the freedom and stiffness parameters for a support type.

    :param support_type: The support type string
    :return: Tuple of (freedom dict, stiffness dict)
    """
    if support_type == "Inklemming":
        freedom = {
            "x": LineSupportFreedom.RIGID,
            "y": LineSupportFreedom.RIGID,
            "z": LineSupportFreedom.RIGID,
            "rx": LineSupportFreedom.RIGID,
            "ry": LineSupportFreedom.RIGID,
            "rz": LineSupportFreedom.RIGID,
        }
        stiffness: dict[str, float] = {}  # Rigid supports don't need stiffness values
    else:  # support_type == "Verende oplegging (x,y)":
        freedom = {
            "x": LineSupportFreedom.FLEXIBLE,
            "y": LineSupportFreedom.FLEXIBLE,
            "z": LineSupportFreedom.RIGID,
            "rx": LineSupportFreedom.FREE,
            "ry": LineSupportFreedom.RIGID,
            "rz": LineSupportFreedom.RIGID,
        }
        stiffness = {"stiffness_x": 1e7, "stiffness_y": 1e6}

    return freedom, stiffness


def _get_plates_and_edge_for_support(d_point_index: int, num_d_points: int, plate_names: list[str]) -> tuple[list[str], int, int] | None:
    """
    Determine which plates and edge to use for a D-point support.

    :param d_point_index: The D-point index (0-based)
    :param num_d_points: Total number of D-points
    :param plate_names: List of plate names
    :return: Tuple of (plates_for_support, edge_index, section_number) or None if not found
    """
    if d_point_index == 0:
        # First D-point: supports at start of bridge (first 3 plates, edge index 4)
        plates_for_support = plate_names[:3]
        edge_index = 4
        section_number = 1
    elif d_point_index == num_d_points - 1:
        # Last D-point: supports at end of bridge (last 3 plates, edge index 2)
        plates_for_support = plate_names[-3:]
        edge_index = 2
        section_number = d_point_index + 1
    else:
        # Intermediate D-point: need to find the correct plates for this section
        segment_end_idx = d_point_index * 3  # Current segment's plates

        if segment_end_idx < len(plate_names):
            # Support at the boundary between segments - use edge 2 of current segment plates
            plates_for_support = plate_names[segment_end_idx : segment_end_idx + 3]
            edge_index = 4  # Start edge of current segment
        else:
            # Fallback if we can't find the right plates
            return None
        section_number = d_point_index + 1

    return plates_for_support, edge_index, section_number


def create_line_supports(builder: SciaModelBuilder, plate_names: list[str], support_types: list[str] | None = None) -> list[SciaLineSupport]:
    """
    Define and create line supports based on user-specified support types.

    :param builder: The SCIA model builder instance.
    :param plate_names: An ordered list of created plate names.
    :param support_types: List of support type strings for each D-point.
                         Options: "Nee", "Verende oplegging (x,y)", "Inklemming".
                         If None, defaults to supports at first and last positions only.
    :return: A list of the created LineSupport objects.
    """
    if not plate_names:
        return []

    # Determine the number of D-points from plate names
    # e.g., for plates "Z1_1", "Z2_1", "Z3_1", "Z1_2", etc., the span numbers are 1, 2.
    span_numbers = {int(name.split("_")[1]) for name in plate_names if len(name.split("_")) > 1 and name.split("_")[1].isdigit()}
    max_span_number = max(span_numbers, default=0)
    num_d_points = max_span_number + 1

    # Handle support types
    if support_types is None:
        # Fallback: create supports at first and last positions only (legacy behavior)
        support_types = ["Verende oplegging (x,y)"] + ["Nee"] * (num_d_points - 2) + (["Verende oplegging (x,y)"] if num_d_points > 1 else [])

    # Ensure support_types list matches number of D-points
    while len(support_types) < num_d_points:
        support_types.append("Nee")

    support_objects = []

    # Create supports based on support_types
    for d_point_index in range(num_d_points):
        support_type = support_types[d_point_index]

        # Skip if no support is specified
        if support_type == "Nee":
            continue

        # Determine which plates and edge to use for this D-point
        plates_info = _get_plates_and_edge_for_support(d_point_index, num_d_points, plate_names)
        if plates_info is None:
            continue

        plates_for_support, edge_index, section_number = plates_info

        # Create support for each zone at this D-point
        for plate_name in plates_for_support:
            zone_number = int(plate_name.split("_")[0][1:])

            # Get support parameters
            freedom, stiffness = _get_support_freedom_and_stiffness(support_type)

            support_objects.append(
                builder.create_line_support_on_plane(
                    name=f"SLB_opleg_as_{section_number}:{zone_number}",
                    plane_name=plate_name,
                    edge_index=edge_index,
                    freedom=freedom,
                    stiffness=stiffness,
                )
            )

    return support_objects


def create_all_supports(builder: SciaModelBuilder, plate_names: list[str], support_types: list[str] | None = None) -> list[SciaLineSupport]:
    """
    Define and create all support types for the bridge model.

    :param builder: The SCIA model builder instance.
    :param plate_names: An ordered list of created plate names.
    :param support_types: List of support type strings for each D-point.
    :return: A list of all created support objects.
    """
    all_supports = []
    all_supports.extend(create_line_supports(builder, plate_names, support_types))
    # Extend with other support types if needed

    return all_supports
