"""Functions for generating reports."""

from datetime import datetime
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

from docxtpl import DocxTemplate  # type: ignore[import]
from munch import Munch  # type: ignore[import-untyped]
from viktor.core import File
from viktor.utils import convert_word_to_pdf

from app.constants import OUTPUT_REPORT_PATH
from src.integrations.scia_integration.scia_coordinate_utils import (
    get_bridge_deck_zone_materials_and_thickness,
)


def return_traffic_class(params: Munch) -> str:
    """
    Return a formatted string based on the traffic class parameter.

    Args:
        params: Dictionary containing parameters. Must include:
            - traffic_class (str): The traffic class value.

    Returns:
        str: Formatted traffic class string.

    """
    if params.berekeningsniveau == "Werkelijke wegindeling met bebording":
        return f"Werkelijke wegindeling met bebording, {params.signage}"
    return params.berekeningsniveau


def return_design_code(params: Munch) -> str:
    """
    Return a formatted string based on the design code parameter.

    Args:
        params: Dictionary containing parameters. Must include:
            - design_code (str): The design code value.

    Returns:
        str: Formatted design code string.

    """
    if params.design_code == "NEN 8700 verbouw":
        return "Verbouwniveau"
    if params.design_code == "NEN 8700 gebruik":
        return "Gebruiksniveau"
    if params.design_code == "NEN 8700 afkeur":
        return "Afkeurniveau"
    return "Verbouwniveau"


def obtain_plate_thickness(params: object) -> dict:
    """
    Obtain the plate thickness from the parameters.

    Args:
        params: Object containing parameters. Must include:
            - geometrie_plaatdikte (float): The plate thickness value.

    Returns:
        dict: Dictionary with the plate thickness.

    """
    return get_bridge_deck_zone_materials_and_thickness(params)


def obtain_loadzone_properties(params: object) -> dict[str, str]:
    """
    Obtain unique pavement materials and their thicknesses from load zones.

    Args:
        params: Object containing parameters with load zone information.

    Returns:
        dict[str, str]: Dictionary mapping unique pavement materials to their thicknesses with units (in meters)

    """
    # Let's directly use the load_zones_data_array from params since that contains what we need
    load_zones = getattr(params, "load_zones_data_array", None)

    # Create dictionary from the raw load zones data
    pavement_materials: dict[str, str] = {}
    if load_zones is not None:
        for zone in load_zones:
            material = getattr(zone, "pavement_material", None)
            thickness = getattr(zone, "pavement_thickness", None)
            if material is not None and thickness is not None:
                # Format the thickness with 3 decimal places and add "m" unit
                pavement_materials[material] = f"{float(thickness):.3f} m"

    return pavement_materials


def obtain_idea_unity_checks(cached_idea_results: dict[str, Any]) -> dict[str, str]:  # noqa: C901, PLR0912
    """
    Extract unity check values from IDEA analysis results per check category.

    This function processes the cached IDEA results to extract the maximum unity check (UC)
    value for each check category across all sections. Unity check values indicate how close
    the design is to its limit (1.0 = at limit, >1.0 = over limit).

    Args:
        cached_idea_results: Dictionary containing processed IDEA analysis results with structure:
            - "data": list of lists containing table data
            - "headers": list of column headers
            - "success": boolean indicating if analysis succeeded

    Returns:
        dict[str, str]: Dictionary mapping check category names to their maximum UC values, formatted as strings.
            Categories include: "Capaciteit", "Schuifkracht", "Torsie", "Interactie",
            "Scheurwijdte", "Detailing", "Spanningslimieten"

    """
    # Initialize result dictionary with N/A values
    unity_checks = {
        "Capaciteit": "N/A",
        "Schuifkracht": "N/A",
        "Torsie": "N/A",
        "Interactie": "N/A",
        "Scheurwijdte": "N/A",
        "Detailing": "N/A",
        "Spanningslimieten": "N/A",
    }

    # Check if analysis succeeded
    if not cached_idea_results.get("success"):
        return unity_checks

    # Get data and headers
    data = cached_idea_results.get("data")
    headers = cached_idea_results.get("headers")

    if not data or not headers or not isinstance(data, list) or not isinstance(headers, list):
        return unity_checks

    # Find indices of UC columns in headers
    uc_column_indices: dict[str, int | None] = {
        "Capaciteit": None,
        "Schuifkracht": None,
        "Torsie": None,
        "Interactie": None,
        "Scheurwijdte": None,
        "Detailing": None,
        "Spanningslimieten": None,
    }

    # Map headers to indices (UC columns have "UC " prefix)
    for idx, header in enumerate(headers):
        if header == "UC Capaciteit":
            uc_column_indices["Capaciteit"] = idx
        elif header == "UC Schuifkracht":
            uc_column_indices["Schuifkracht"] = idx
        elif header == "UC Torsie":
            uc_column_indices["Torsie"] = idx
        elif header == "UC Interactie":
            uc_column_indices["Interactie"] = idx
        elif header == "UC Scheurwijdte":
            uc_column_indices["Scheurwijdte"] = idx
        elif header == "UC Detailing":
            uc_column_indices["Detailing"] = idx
        elif header == "UC Spanningslimieten":
            uc_column_indices["Spanningslimieten"] = idx

    # Track maximum UC values for each category
    max_uc_values: dict[str, float] = {}

    # Iterate through all data rows to find maximum UC values
    for row in data:
        if not isinstance(row, list):
            continue

        for category, col_idx in uc_column_indices.items():
            if col_idx is None or col_idx >= len(row):
                continue

            uc_value_str = row[col_idx]

            # Skip N/A values
            if uc_value_str == "N/A" or uc_value_str is None:
                continue

            try:
                # Convert string to float
                uc_value = float(uc_value_str)

                # Update maximum value
                if category not in max_uc_values or uc_value > max_uc_values[category]:
                    max_uc_values[category] = uc_value
            except (ValueError, TypeError):
                # Skip invalid values
                continue

    # Format the results
    for category, uc_value in max_uc_values.items():
        unity_checks[category] = f"{uc_value:.2f}"

    return unity_checks


def create_export_report(params: Munch, cached_idea_results: dict[str, Any] | None = None) -> File:
    """
    Create a report for the export process using a Word template.

    Uses :class:`docxtpl.DocxTemplate` to fill a Word template with the provided parameters
    and converts the result to a PDF using VIKTOR's utilities.

    VERY IMPORTANT : Variables must not contains characters like <, > and & unless using Escaping

    Args:
        params: Dictionary containing parameters for the report. Must include:
            - export_id (str): Unique identifier for the export
            - export_status (str): Current status of the export
        cached_idea_results: Optional dictionary containing cached IDEA analysis results.
            If provided, unity check values will be included in the report.

    Returns:
        File: A PDF file containing the filled report.

    Raises:
        KeyError: If any required parameters are missing from the params dict.
        OSError: If there are issues accessing the template or saving temporary files.

    """
    # Load the template
    doc = DocxTemplate(OUTPUT_REPORT_PATH)  # Create the context dict for the template
    # Get unity check values if IDEA results are provided
    unity_checks: dict[str, str] = {}
    if cached_idea_results is not None:
        unity_checks = obtain_idea_unity_checks(cached_idea_results)

    context = {
        "BRIDGE_NAME": params.info.bridge_name,
        "BRIDGE_ID": params.info.bridge_objectnumm,
        "CONSTRUCTION_YEAR": params.info.construction_year,
        "DATE": datetime.now(tz=ZoneInfo("Europe/Amsterdam")).strftime("%d-%m-%Y"),
        "DESIGN_CODE": return_design_code(params),
        "CONSEQUENCE_CLASS": params.cc_class,
        "TRAFFICCLASS": return_traffic_class(params),
        "CONCRETE_CLASS": params.concrete_strength_class,
        "REINFORCEMENT_CLASS": params.input.geometrie_wapening.staalsoort,
        "PLATE_THICKNESS1": obtain_plate_thickness(params)["zone_1_1"]["thickness_start_d_line"],
        "PLATE_THICKNESS2": round(
            (
                obtain_plate_thickness(params)["zone_1_1"]["thickness_start_d_line"]
                + obtain_plate_thickness(params)["zone_2_1"]["thickness_start_d_line"]
            ),
            2,
        ),
        "LOAD_ZONES": obtain_loadzone_properties(params),
        "UC_CAPACITY": unity_checks.get("Capaciteit", "N/A"),
        "UC_SHEARFORCE": unity_checks.get("Schuifkracht", "N/A"),
        "UC_TORSION": unity_checks.get("Torsie", "N/A"),
        "UC_INTERACTION": unity_checks.get("Interactie", "N/A"),
        "UC_CRACK_WIDTH": unity_checks.get("Scheurwijdte", "N/A"),
        "UC_DETAILING": unity_checks.get("Detailing", "N/A"),
        "UC_STRESSLIMITATION": unity_checks.get("Spanningslimieten", "N/A"),
    }
    # Render the template
    doc.render(context)
    # Save the rendered document to a BytesIO object
    doc_binary = BytesIO()
    doc.save(doc_binary)
    doc_binary.seek(0)  # Reset pointer to start of buffer
    # Convert to PDF
    file = File.from_data(doc_binary.read())
    with file.open_binary() as f:
        return convert_word_to_pdf(f)
