"""Functions for generating reports."""

from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from docxtpl import DocxTemplate  # type: ignore[import]
from munch import Munch  # type: ignore[import-untyped]
from viktor.core import File
from viktor.utils import convert_word_to_pdf

from app.constants import OUTPUT_REPORT_PATH


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
    context = {
        "BRIDGE_ID": params.info.bridge_objectnumm,
        "DATE": datetime.now(tz=ZoneInfo("Europe/Amsterdam")).strftime("%d-%m-%Y"),
        # Add more template variables as needed
    }

    # Render the template
    doc.render(context)

    # Save the rendered document to a BytesIO object
    doc_binary = BytesIO()
    doc.save(doc_binary)
    doc_binary.seek(0)  # Reset pointer to start of buffer    # Convert to PDF
    file = File.from_data(doc_binary.read())
    with file.open_binary() as f:
        return convert_word_to_pdf(f)
