"""Module for defining SCIA support elements."""

from .scia_model_builder import SciaModelBuilder


def define_line_supports(builder: SciaModelBuilder, plate_names: list[str]) -> None:
    """
    Define line supports on the first and last edges of the bridge deck.

    :param builder: The SCIA model builder.
    :param plate_names: An ordered list of plate names.
    """
    if not plate_names:
        return

    # Determine the last section number from plate names like "Z1_1", "Z2_1", ...
    span_numbers = (
        int(plate_name.split("_")[1]) for plate_name in plate_names if len(plate_name.split("_")) > 1 and plate_name.split("_")[1].isdigit()
    )
    max_span_number = max(span_numbers, default=0)
    last_section_number = max_span_number + 1

    # The logic assumes an ordered list of plates, e.g., ["Z1_0", "Z2_0", "Z1_1", "Z2_1", ...]
    # And supports are applied at the start of the first segment and end of the last.
    first_plates = [plate_name for plate_name in plate_names if plate_name.endswith("_0")]
    last_plates = [plate_name for plate_name in plate_names if plate_name.endswith(f"_{last_section_number}")]

    # Support at the start of the bridge (edge 0 of first plates)
    for i, plate_name in enumerate(first_plates):
        builder.add_line_support_on_plate_edge(
            name=f"Support_Start_{i}",
            plate_name=plate_name,
            edge_index=0,
            support_type="Rx,Ry,Rz,Tx,Ty,Tz",  # Pinned support
        )

    # Support at the end of the bridge (edge 2 of last plates)
    for i, plate_name in enumerate(last_plates):
        builder.add_line_support_on_plate_edge(
            name=f"Support_End_{i}",
            plate_name=plate_name,
            edge_index=2,
            support_type="Ry,Rz,Tx,Ty,Tz",  # Roller support
        )
