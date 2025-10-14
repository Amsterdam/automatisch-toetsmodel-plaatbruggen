"""Functions for generating reports."""

from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from docxtpl import DocxTemplate  # type: ignore[import]
from munch import Munch  # type: ignore[import-untyped]
from viktor.core import File
from viktor.utils import convert_word_to_pdf

from app.constants import OUTPUT_REPORT_PATH
from src.integrations.scia_integration.scia_coordinate_utils import get_bridge_deck_zone_materials_and_thickness, get_bridge_load_zone_materials_and_thickness

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
    else:
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
    elif params.design_code == "NEN 8700 gebruik":
        return "Gebruiksniveau"
    elif params.design_code == "NEN 8700 afkeur":
        return "Afkeurniveau"
    else:
        return "Verbouwniveau"
    
def obtain_plate_thickness(params:object) -> dict:
    """
    Obtain the plate thickness from the parameters.

    Args:
        params: Object containing parameters. Must include:
            - geometrie_plaatdikte (float): The plate thickness value.

    Returns:
        dict: Dictionary with the plate thickness.
    """
    materials = get_bridge_deck_zone_materials_and_thickness(params)
    print(materials)
    return materials

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
    for zone in load_zones:
        material = getattr(zone, "pavement_material", None)
        thickness = getattr(zone, "pavement_thickness", None)
        if material is not None and thickness is not None:
            # Format the thickness with 3 decimal places and add "m" unit
            pavement_materials[material] = f"{float(thickness):.3f} m"
    
    return pavement_materials

def create_export_report(params: Munch) -> File:
    """
    Create a report for the export process using a Word template.

    Uses :class:`docxtpl.DocxTemplate` to fill a Word template with the provided parameters
    and converts the result to a PDF using VIKTOR's utilities.

    VERY IMPORTANT : Variables must not contains characters like <, > and & unless using Escaping

    Args:
        params: Dictionary containing parameters for the report. Must include:
            - export_id (str): Unique identifier for the export
            - export_status (str): Current status of the export

    Returns:
        File: A PDF file containing the filled report.

    Raises:
        KeyError: If any required parameters are missing from the params dict.
        OSError: If there are issues accessing the template or saving temporary files.

    """
    # Load the template
    doc = DocxTemplate(OUTPUT_REPORT_PATH)  # Create the context dict for the template
    print(dir(params))
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
        "PLATE_THICKNESS2": round((obtain_plate_thickness(params)["zone_1_1"]["thickness_start_d_line"]
            + obtain_plate_thickness(params)["zone_2_1"]["thickness_start_d_line"]),2),
        "LOAD_ZONES": obtain_loadzone_properties(params),
        # Add more template variables as needed
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
