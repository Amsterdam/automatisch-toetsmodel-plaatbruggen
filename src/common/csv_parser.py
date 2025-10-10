"""
CSV/Excel parser for bridge inventory data.

This module provides functions to parse bridge data from CSV or Excel files
and convert it to the JSON format used by filtered_bridges.json.
"""

import csv
import io
from typing import Any

import openpyxl

# Column name mappings from CSV/Excel to JSON field names
COLUMN_MAPPINGS = {
    "Kunstwerk nummer": "OBJECTNUMM",
    "Type": "type",
    "stadsdeel": "stadsdeel",
    "Straat": "straat",
    "KW naam": "kw_naam",
    "voorgespannen": "voorgespannen",
    "Stichtingsjaar": "stichtingsjaar",
    "Gebruik": "gebruik",
    "Betonsterkteklasse": "betonsterkteklasse",
    "Staalkwaliteit wapening": "staalkwaliteit_wapening",
    "Staalkwaliteit voorgespanning": "staalkwaliteit_voorgespanning",
    "Deklaag": "deklaag",
    "Staalkwaliteit constructiestaal": "staalkwaliteit_constructiestaal",
    "Aantal velden": "aantal_velden",
    "Statisch systeem (zoals aangehouden in berekening)": "statisch_systeem",
    "kruisingshoek": "kruisingshoek",
    "Ldag": "ldag",
    "Lth": "lth",
    "Constructiehoogte dek": "constructiehoogte_dek",
    "Slankheid dek lth/h": "slankheid_dek",
    "bbrugdek": "bbrugdek",
    "Breedte noord/oost": "breedte_noord_oost",
    "Breedte zuid/west": "breedte_zuid_west",
    "Opleggingen": "opleggingen",
    "Orthotropie / Isotropie": "orthotropie_isotropie",
    "Liggers in plaat": "liggers_in_plaat",
    "Breedte rijwegen": "breedte_rijwegen",
    "Breedte trambaan": "breedte_trambaan",
    "Breedte fietspad": "breedte_fietspad",
    "Breedte voetpad noord/oost": "breedte_voetpad_noord_oost",
    "Breedte voetpad zuid/west": "breedte_voetpad_zuid_west",
    "Dikte schampkant": "dikte_schampkant",
    "Randbelasting": "randbelasting",
    "Ontwerpbelasting": "ontwerpbelasting",
    "Originele berekening": "originele_berekening",
    "Modificatie berekening": "modificatie_berekening",
    "Herberekening": "herberekening",
    "Vlag ARB": "vlag_arb",
    "Basale toets GHPO": "basale_toets_ghpo",
    "Opdrachtnemer IHA": "opdrachtnemer_iha",
    "Steunpuntswapening (langsrichting) diameter": "steunpuntswapening_langsrichting_diameter",
    "Steunpuntswapening (langsrichting) h.o.h.-afstand": "steunpuntswapening_langsrichting_hoh_afstand",
    "Steunpuntswapening laag": "steunpuntswapening_laag",
    "Veldwapening (langsrichting) diameter": "veldwapening_langsrichting_diameter",
    "Veldwapening (langsrichting) h.o.h.-afstand": "veldwapening_langsrichting_hoh_afstand",
    "Veldwapening (langrichting) laag": "veldwapening_langsrichting_laag",
    "Veldwapening (dwarsrichting) diameter": "veldwapening_dwarsrichting_diameter",
    "Veldwapening (dwarsrichting) h.o.h.-afstand": "veldwapening_dwarsrichting_hoh_afstand",
    "Veldwapening (dwarsrichting) laag": "veldwapening_dwarsrichting_laag",
    "Dekking buitenkant wapening": "dekking_buitenkant_wapening",
}

# Fields that should be converted to boolean
BOOLEAN_FIELDS = {"voorgespannen", "randbelasting"}

# Fields that should be converted to integer
INTEGER_FIELDS = {"aantal_velden", "constructiehoogte_dek"}

# Fields that should be converted to float
FLOAT_FIELDS = {"kruisingshoek"}


def parse_bridge_csv(file_content: bytes) -> list[dict[str, Any]]:
    """
    Parse bridge data from a CSV file with semicolon delimiter.

    :param file_content: Raw bytes of the CSV file.
    :type file_content: bytes
    :returns: List of bridge data dictionaries.
    :rtype: list[dict[str, Any]]
    :raises ValueError: If CSV parsing fails or required fields are missing.
    """
    try:
        # Decode bytes to string with error handling for problematic characters
        try:
            text_content = file_content.decode("utf-8-sig")  # Handle BOM if present
        except UnicodeDecodeError:
            # Try with Latin-1 if UTF-8 fails (common for Windows CSV files)
            try:
                text_content = file_content.decode("latin-1")
            except UnicodeDecodeError:
                # Last resort: use UTF-8 with error replacement
                text_content = file_content.decode("utf-8-sig", errors="replace")

        csv_file = io.StringIO(text_content)

        # Parse CSV with semicolon delimiter
        reader = csv.DictReader(csv_file, delimiter=";")

        # Normalize column headers by stripping whitespace
        if reader.fieldnames:
            reader.fieldnames = [field.strip() if field else field for field in reader.fieldnames]

        bridges = []
        skipped_rows = []

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            # Skip empty rows (all values are None, empty string, or whitespace)
            if not any(v and str(v).strip() for v in row.values()):
                continue

            try:
                bridge_data = _convert_row_to_bridge_data(row)

                # Skip rows without OBJECTNUMM (instead of failing)
                if not bridge_data.get("OBJECTNUMM"):
                    skipped_rows.append(row_num)
                    continue

                bridges.append(bridge_data)
            except ValueError:
                # Log but don't fail on individual row errors
                skipped_rows.append(row_num)
                continue

        if not bridges:
            available_columns = list(reader.fieldnames) if reader.fieldnames else []
            raise ValueError(
                f"No valid bridge data found in CSV file. "
                f"Available columns: {', '.join(available_columns[:10])}... "
                f"Expected 'Kunstwerk nummer' column."
            )

        return bridges

    except UnicodeDecodeError as e:
        raise ValueError(f"Failed to decode CSV file. Please ensure it's UTF-8 encoded: {e}")
    except csv.Error as e:
        raise ValueError(f"Failed to parse CSV file: {e}")


def parse_bridge_excel(file_content: bytes) -> list[dict[str, Any]]:
    """
    Parse bridge data from an Excel file (.xlsx).

    :param file_content: Raw bytes of the Excel file.
    :type file_content: bytes
    :returns: List of bridge data dictionaries.
    :rtype: list[dict[str, Any]]
    :raises ValueError: If Excel parsing fails or required fields are missing.
    """
    try:
        # Load workbook from bytes
        excel_file = io.BytesIO(file_content)
        workbook = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        sheet = workbook.active

        # Get header row
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise ValueError("Excel file is empty")

        headers = rows[0]
        if not headers:
            raise ValueError("Excel file has no header row")

        # Normalize headers by stripping whitespace
        headers = [str(h).strip() if h else h for h in headers]

        bridges = []
        skipped_rows = []

        for row_num, row_values in enumerate(rows[1:], start=2):  # Start at 2 (header is row 1)
            # Skip empty rows (all values are None, empty, or whitespace)
            if not any(v and str(v).strip() if v is not None else False for v in row_values):
                continue

            # Convert row to dictionary
            row_dict = dict(zip(headers, row_values))

            try:
                bridge_data = _convert_row_to_bridge_data(row_dict)

                # Skip rows without OBJECTNUMM (instead of failing)
                if not bridge_data.get("OBJECTNUMM"):
                    skipped_rows.append(row_num)
                    continue

                bridges.append(bridge_data)
            except ValueError:
                # Log but don't fail on individual row errors
                skipped_rows.append(row_num)
                continue

        if not bridges:
            raise ValueError(
                f"No valid bridge data found in Excel file. Available columns: {', '.join(headers[:10])}... Expected 'Kunstwerk nummer' column."
            )

        return bridges

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to parse Excel file: {e}")


def _convert_row_to_bridge_data(row: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a CSV/Excel row to bridge data format.

    :param row: Dictionary mapping column names to values.
    :type row: dict[str, Any]
    :returns: Bridge data dictionary with JSON field names.
    :rtype: dict[str, Any]
    :raises ValueError: If data conversion fails.
    """
    bridge_data: dict[str, Any] = {}

    # Normalize row keys by stripping whitespace
    normalized_row = {k.strip() if k else k: v for k, v in row.items()}

    for csv_col, json_field in COLUMN_MAPPINGS.items():
        value = normalized_row.get(csv_col)

        # Convert value based on field type
        converted_value = _convert_field_value(json_field, value)

        # Only add non-None values
        if converted_value is not None:
            bridge_data[json_field] = converted_value

    return bridge_data


def _convert_field_value(field_name: str, value: Any) -> Any:
    """
    Convert a field value to the appropriate type.

    :param field_name: JSON field name.
    :type field_name: str
    :param value: Raw value from CSV/Excel.
    :type value: Any
    :returns: Converted value or None.
    :rtype: Any
    """
    # Handle None, empty strings, and "-" as null values
    if value is None or value == "" or value == "-":
        return None

    # Strip whitespace from strings
    if isinstance(value, str):
        value = value.strip()
        if not value or value == "-":
            return None

    # Convert boolean fields
    if field_name in BOOLEAN_FIELDS:
        return _convert_to_boolean(value)

    # Convert integer fields
    if field_name in INTEGER_FIELDS:
        return _convert_to_integer(value)

    # Convert float fields
    if field_name in FLOAT_FIELDS:
        return _convert_to_float(value)

    # Return as-is (string or already correct type from Excel)
    return value


def _convert_to_boolean(value: Any) -> bool | None:
    """
    Convert a value to boolean.

    :param value: Value to convert.
    :type value: Any
    :returns: Boolean value or None.
    :rtype: bool | None
    """
    if value is None or value == "" or value == "-":
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ["ja", "yes", "true", "1", "x"]:
            return True
        if value_lower in ["nee", "no", "false", "0", ""]:
            return False

    return None


def _convert_to_integer(value: Any) -> int | None:
    """
    Convert a value to integer.

    :param value: Value to convert.
    :type value: Any
    :returns: Integer value or None.
    :rtype: int | None
    """
    if value is None or value == "" or value == "-":
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    return None


def _convert_to_float(value: Any) -> float | None:
    """
    Convert a value to float.

    :param value: Value to convert.
    :type value: Any
    :returns: Float value or None.
    :rtype: float | None
    """
    if value is None or value == "" or value == "-":
        return None

    if isinstance(value, float | int):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    return None
