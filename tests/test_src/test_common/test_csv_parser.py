"""Tests for CSV/Excel parser module."""

from io import BytesIO

import pytest

from src.common.csv_parser import (
    _convert_field_value,
    _convert_to_boolean,
    _convert_to_float,
    _convert_to_integer,
    parse_bridge_csv,
    parse_bridge_excel,
)


class TestCSVParser:
    """Test CSV parsing functionality."""

    def test_parse_simple_csv(self) -> None:
        """Test parsing a simple CSV with basic bridge data."""
        csv_content = (
            "Kunstwerk nummer;Type;stadsdeel;Straat;KW naam;voorgespannen;Stichtingsjaar\n"
            "BRU0010;Type 3;Centrum;Blauwburgwal;Lijnbaansbrug;nee;1963\n"
            "BRU0027;Type 1;Centrum;Herengracht;Beulingsluis;nee;2000\n"
        )
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        assert len(result) == 2
        assert result[0]["OBJECTNUMM"] == "BRU0010"
        assert result[0]["type"] == "Type 3"
        assert result[0]["stadsdeel"] == "Centrum"
        assert result[0]["voorgespannen"] is False
        assert result[1]["OBJECTNUMM"] == "BRU0027"

    def test_parse_csv_with_integer_fields(self) -> None:
        """Test parsing CSV with integer fields."""
        csv_content = "Kunstwerk nummer;Aantal velden;Constructiehoogte dek\nBRU0010;3;430\n"
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        assert len(result) == 1
        assert result[0]["aantal_velden"] == 3
        assert result[0]["constructiehoogte_dek"] == 430
        assert isinstance(result[0]["aantal_velden"], int)
        assert isinstance(result[0]["constructiehoogte_dek"], int)

    def test_parse_csv_with_float_fields(self) -> None:
        """Test parsing CSV with float fields."""
        csv_content = "Kunstwerk nummer;kruisingshoek\nBRU0010;77.2\n"
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        assert len(result) == 1
        assert result[0]["kruisingshoek"] == 77.2
        assert isinstance(result[0]["kruisingshoek"], float)

    def test_parse_csv_with_null_values(self) -> None:
        """Test parsing CSV with null values (empty, -, None)."""
        csv_content = "Kunstwerk nummer;Type;stadsdeel;Straat\nBRU0010;;-;\n"
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        assert len(result) == 1
        assert result[0]["OBJECTNUMM"] == "BRU0010"
        assert "type" not in result[0]
        assert "stadsdeel" not in result[0]
        assert "straat" not in result[0]

    def test_parse_csv_with_boolean_fields(self) -> None:
        """Test parsing CSV with boolean fields."""
        csv_content = "Kunstwerk nummer;voorgespannen;Randbelasting\nBRU0010;ja;nee\nBRU0027;nee;ja\n"
        result = parse_bridge_csv(csv_content.encode("utf-8"))

        assert len(result) == 2
        assert result[0]["voorgespannen"] is True
        assert result[0]["randbelasting"] is False
        assert result[1]["voorgespannen"] is False
        assert result[1]["randbelasting"] is True

    def test_parse_csv_missing_required_field(self) -> None:
        """Test parsing CSV with missing required OBJECTNUMM field."""
        csv_content = "Type;stadsdeel\nType 3;Centrum\n"
        with pytest.raises(ValueError) as exc_info:
            parse_bridge_csv(csv_content.encode("utf-8"))

        assert "Kunstwerk nummer" in str(exc_info.value)

    def test_parse_empty_csv(self) -> None:
        """Test parsing an empty CSV file."""
        csv_content = "Kunstwerk nummer\n"

        with pytest.raises(ValueError) as exc_info:
            parse_bridge_csv(csv_content.encode("utf-8"))

        assert "No valid bridge data" in str(exc_info.value)

    def test_convert_field_value_boolean(self) -> None:
        """Test converting boolean field values."""
        assert _convert_field_value("voorgespannen", "ja") is True
        assert _convert_field_value("voorgespannen", "nee") is False
        assert _convert_field_value("voorgespannen", "yes") is True
        assert _convert_field_value("voorgespannen", "no") is False
        assert _convert_field_value("voorgespannen", "-") is None
        assert _convert_field_value("voorgespannen", "") is None

    def test_convert_field_value_integer(self) -> None:
        """Test converting integer field values."""
        assert _convert_field_value("aantal_velden", "3") == 3
        assert _convert_field_value("aantal_velden", 3) == 3
        assert _convert_field_value("aantal_velden", 3.5) == 3
        assert _convert_field_value("aantal_velden", "-") is None
        assert _convert_field_value("aantal_velden", "") is None

    def test_convert_field_value_float(self) -> None:
        """Test converting float field values."""
        assert _convert_field_value("kruisingshoek", "77.2") == 77.2
        assert _convert_field_value("kruisingshoek", 77.2) == 77.2
        assert _convert_field_value("kruisingshoek", 77) == 77.0
        assert _convert_field_value("kruisingshoek", "-") is None
        assert _convert_field_value("kruisingshoek", "") is None

    def test_convert_to_boolean(self) -> None:
        """Test boolean conversion function."""
        assert _convert_to_boolean("ja") is True
        assert _convert_to_boolean("Ja") is True
        assert _convert_to_boolean("yes") is True
        assert _convert_to_boolean("true") is True
        assert _convert_to_boolean("1") is True
        assert _convert_to_boolean("nee") is False
        assert _convert_to_boolean("no") is False
        assert _convert_to_boolean("false") is False
        assert _convert_to_boolean("0") is False
        assert _convert_to_boolean("-") is None
        assert _convert_to_boolean("") is None
        assert _convert_to_boolean(None) is None

    def test_convert_to_integer(self) -> None:
        """Test integer conversion function."""
        assert _convert_to_integer("3") == 3
        assert _convert_to_integer(3) == 3
        assert _convert_to_integer(3.5) == 3
        assert _convert_to_integer("3.5") == 3
        assert _convert_to_integer("-") is None
        assert _convert_to_integer("") is None
        assert _convert_to_integer(None) is None
        assert _convert_to_integer("not_a_number") is None

    def test_convert_to_float(self) -> None:
        """Test float conversion function."""
        assert _convert_to_float("77.2") == 77.2
        assert _convert_to_float(77.2) == 77.2
        assert _convert_to_float(77) == 77.0
        assert _convert_to_float("-") is None
        assert _convert_to_float("") is None
        assert _convert_to_float(None) is None
        assert _convert_to_float("not_a_number") is None


class TestExcelParser:
    """Test Excel parsing functionality."""

    def test_parse_simple_excel(self) -> None:
        """Test parsing a simple Excel file with basic bridge data."""
        # Create a simple Excel file in memory
        import openpyxl

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        assert sheet is not None

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

        assert len(result) == 2
        assert result[0]["OBJECTNUMM"] == "BRU0010"
        assert result[0]["type"] == "Type 3"
        assert result[0]["stadsdeel"] == "Centrum"
        assert result[1]["OBJECTNUMM"] == "BRU0027"

    def test_parse_excel_with_numeric_types(self) -> None:
        """Test parsing Excel with numeric types (integers and floats)."""
        import openpyxl

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        assert sheet is not None

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

        assert len(result) == 1
        assert result[0]["aantal_velden"] == 3
        assert result[0]["kruisingshoek"] == 77.2
        assert isinstance(result[0]["aantal_velden"], int)
        assert isinstance(result[0]["kruisingshoek"], float)
