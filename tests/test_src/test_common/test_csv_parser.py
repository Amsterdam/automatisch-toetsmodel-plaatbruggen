"""Tests for CSV/Excel parser module."""

import unittest
from io import BytesIO

from src.common.csv_parser import (
    parse_bridge_csv,
    parse_bridge_excel,
    _convert_field_value,
    _convert_to_boolean,
    _convert_to_integer,
    _convert_to_float,
)


class TestCSVParser(unittest.TestCase):
    """Test CSV parsing functionality."""

    def test_parse_simple_csv(self) -> None:
        """Test parsing a simple CSV with basic bridge data."""
        csv_content = (
            "Kunstwerk nummer;Type;stadsdeel;Straat;KW naam;voorgespannen;Stichtingsjaar\n"
            "BRU0010;Type 3;Centrum;Blauwburgwal;Lijnbaansbrug;nee;1963\n"
            "BRU0027;Type 1;Centrum;Herengracht;Beulingsluis;nee;2000\n"
        )
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["OBJECTNUMM"], "BRU0010")
        self.assertEqual(result[0]["type"], "Type 3")
        self.assertEqual(result[0]["stadsdeel"], "Centrum")
        self.assertEqual(result[0]["voorgespannen"], False)
        self.assertEqual(result[1]["OBJECTNUMM"], "BRU0027")

    def test_parse_csv_with_integer_fields(self) -> None:
        """Test parsing CSV with integer fields."""
        csv_content = (
            "Kunstwerk nummer;Aantal velden;Constructiehoogte dek\n"
            "BRU0010;3;430\n"
        )
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["aantal_velden"], 3)
        self.assertEqual(result[0]["constructiehoogte_dek"], 430)
        self.assertIsInstance(result[0]["aantal_velden"], int)
        self.assertIsInstance(result[0]["constructiehoogte_dek"], int)

    def test_parse_csv_with_float_fields(self) -> None:
        """Test parsing CSV with float fields."""
        csv_content = (
            "Kunstwerk nummer;kruisingshoek\n"
            "BRU0010;77.2\n"
        )
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["kruisingshoek"], 77.2)
        self.assertIsInstance(result[0]["kruisingshoek"], float)

    def test_parse_csv_with_null_values(self) -> None:
        """Test parsing CSV with null values (empty, -, None)."""
        csv_content = (
            "Kunstwerk nummer;Type;stadsdeel;Straat\n"
            "BRU0010;;-;\n"
        )
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["OBJECTNUMM"], "BRU0010")
        self.assertNotIn("type", result[0])
        self.assertNotIn("stadsdeel", result[0])
        self.assertNotIn("straat", result[0])

    def test_parse_csv_with_boolean_fields(self) -> None:
        """Test parsing CSV with boolean fields."""
        csv_content = (
            "Kunstwerk nummer;voorgespannen;Randbelasting\n"
            "BRU0010;ja;nee\n"
            "BRU0027;nee;ja\n"
        )
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["voorgespannen"], True)
        self.assertEqual(result[0]["randbelasting"], False)
        self.assertEqual(result[1]["voorgespannen"], False)
        self.assertEqual(result[1]["randbelasting"], True)

    def test_parse_csv_missing_required_field(self) -> None:
        """Test parsing CSV with missing required OBJECTNUMM field."""
        csv_content = (
            "Type;stadsdeel\n"
            "Type 3;Centrum\n"
        )
        with self.assertRaises(ValueError) as context:
            parse_bridge_csv(csv_content.encode("utf-8"))

        self.assertIn("OBJECTNUMM", str(context.exception))

    def test_parse_empty_csv(self) -> None:
        """Test parsing an empty CSV file."""
        csv_content = "Kunstwerk nummer\n"

        with self.assertRaises(ValueError) as context:
            parse_bridge_csv(csv_content.encode("utf-8"))

        self.assertIn("No valid bridge data", str(context.exception))

    def test_convert_field_value_boolean(self) -> None:
        """Test converting boolean field values."""
        self.assertEqual(_convert_field_value("voorgespannen", "ja"), True)
        self.assertEqual(_convert_field_value("voorgespannen", "nee"), False)
        self.assertEqual(_convert_field_value("voorgespannen", "yes"), True)
        self.assertEqual(_convert_field_value("voorgespannen", "no"), False)
        self.assertEqual(_convert_field_value("voorgespannen", "-"), None)
        self.assertEqual(_convert_field_value("voorgespannen", ""), None)

    def test_convert_field_value_integer(self) -> None:
        """Test converting integer field values."""
        self.assertEqual(_convert_field_value("aantal_velden", "3"), 3)
        self.assertEqual(_convert_field_value("aantal_velden", 3), 3)
        self.assertEqual(_convert_field_value("aantal_velden", 3.5), 3)
        self.assertEqual(_convert_field_value("aantal_velden", "-"), None)
        self.assertEqual(_convert_field_value("aantal_velden", ""), None)

    def test_convert_field_value_float(self) -> None:
        """Test converting float field values."""
        self.assertEqual(_convert_field_value("kruisingshoek", "77.2"), 77.2)
        self.assertEqual(_convert_field_value("kruisingshoek", 77.2), 77.2)
        self.assertEqual(_convert_field_value("kruisingshoek", 77), 77.0)
        self.assertEqual(_convert_field_value("kruisingshoek", "-"), None)
        self.assertEqual(_convert_field_value("kruisingshoek", ""), None)

    def test_convert_to_boolean(self) -> None:
        """Test boolean conversion function."""
        self.assertEqual(_convert_to_boolean("ja"), True)
        self.assertEqual(_convert_to_boolean("Ja"), True)
        self.assertEqual(_convert_to_boolean("yes"), True)
        self.assertEqual(_convert_to_boolean("true"), True)
        self.assertEqual(_convert_to_boolean("1"), True)
        self.assertEqual(_convert_to_boolean("nee"), False)
        self.assertEqual(_convert_to_boolean("no"), False)
        self.assertEqual(_convert_to_boolean("false"), False)
        self.assertEqual(_convert_to_boolean("0"), False)
        self.assertEqual(_convert_to_boolean("-"), None)
        self.assertEqual(_convert_to_boolean(""), None)
        self.assertEqual(_convert_to_boolean(None), None)

    def test_convert_to_integer(self) -> None:
        """Test integer conversion function."""
        self.assertEqual(_convert_to_integer("3"), 3)
        self.assertEqual(_convert_to_integer(3), 3)
        self.assertEqual(_convert_to_integer(3.5), 3)
        self.assertEqual(_convert_to_integer("3.5"), 3)
        self.assertEqual(_convert_to_integer("-"), None)
        self.assertEqual(_convert_to_integer(""), None)
        self.assertEqual(_convert_to_integer(None), None)
        self.assertEqual(_convert_to_integer("not_a_number"), None)

    def test_convert_to_float(self) -> None:
        """Test float conversion function."""
        self.assertEqual(_convert_to_float("77.2"), 77.2)
        self.assertEqual(_convert_to_float(77.2), 77.2)
        self.assertEqual(_convert_to_float(77), 77.0)
        self.assertEqual(_convert_to_float("-"), None)
        self.assertEqual(_convert_to_float(""), None)
        self.assertEqual(_convert_to_float(None), None)
        self.assertEqual(_convert_to_float("not_a_number"), None)


class TestExcelParser(unittest.TestCase):
    """Test Excel parsing functionality."""

    def test_parse_simple_excel(self) -> None:
        """Test parsing a simple Excel file with basic bridge data."""
        # Create a simple Excel file in memory
        import openpyxl

        workbook = openpyxl.Workbook()
        sheet = workbook.active

        # Add headers
        sheet.append(["Kunstwerk nummer", "Type", "stadsdeel", "Straat", "KW naam"])

        # Add data rows
        sheet.append(["BRU0010", "Type 3", "Centrum", "Blauwburgwal", "Lijnbaansbrug"])
        sheet.append(["BRU0027", "Type 1", "Centrum", "Herengracht", "Beulingsluis"])

        # Save to BytesIO
        excel_file = BytesIO()
        workbook.save(excel_file)
        excel_file.seek(0)

        # Parse
        result = parse_bridge_excel(excel_file.getvalue())

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["OBJECTNUMM"], "BRU0010")
        self.assertEqual(result[0]["type"], "Type 3")
        self.assertEqual(result[0]["stadsdeel"], "Centrum")
        self.assertEqual(result[1]["OBJECTNUMM"], "BRU0027")

    def test_parse_excel_with_numeric_types(self) -> None:
        """Test parsing Excel with numeric types (integers and floats)."""
        import openpyxl

        workbook = openpyxl.Workbook()
        sheet = workbook.active

        # Add headers
        sheet.append(["Kunstwerk nummer", "Aantal velden", "kruisingshoek"])

        # Add data row with numeric types
        sheet.append(["BRU0010", 3, 77.2])

        # Save to BytesIO
        excel_file = BytesIO()
        workbook.save(excel_file)
        excel_file.seek(0)

        # Parse
        result = parse_bridge_excel(excel_file.getvalue())

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["aantal_velden"], 3)
        self.assertEqual(result[0]["kruisingshoek"], 77.2)
        self.assertIsInstance(result[0]["aantal_velden"], int)
        self.assertIsInstance(result[0]["kruisingshoek"], float)

