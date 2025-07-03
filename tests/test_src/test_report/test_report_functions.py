"""
Test module for report generation functionality.

This module contains comprehensive tests for report creation,
template processing, and PDF conversion functions.
"""

import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from munch import Munch  # type: ignore[import-untyped]

from src.report.report_functions import create_export_report


class TestCreateExportReport(unittest.TestCase):
    """Test cases for create_export_report function."""

    @patch("src.report.report_functions.convert_word_to_pdf")
    @patch("src.report.report_functions.File")
    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_success(
        self,
        mock_output_path: MagicMock,
        mock_docx_template: MagicMock,
        mock_file: MagicMock,
        mock_convert_word_to_pdf: MagicMock,
    ) -> None:
        """Test successful report creation with valid parameters."""
        # Arrange
        mock_template_path = "/path/to/template.docx"
        mock_output_path.return_value = mock_template_path

        mock_doc = MagicMock()
        mock_docx_template.return_value = mock_doc

        mock_file_instance = MagicMock()
        mock_file.from_data.return_value = mock_file_instance

        mock_pdf_file = MagicMock()
        mock_convert_word_to_pdf.return_value = mock_pdf_file

        # Create test parameters
        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
            }
        )

        # Act
        result = create_export_report(params)

        # Assert
        mock_docx_template.assert_called_once_with(mock_output_path)
        mock_doc.render.assert_called_once()
        mock_doc.save.assert_called_once()
        mock_file.from_data.assert_called_once()
        mock_convert_word_to_pdf.assert_called_once()
        assert result == mock_pdf_file

    @patch("src.report.report_functions.convert_word_to_pdf")
    @patch("src.report.report_functions.File")
    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_context_variables(
        self,
        mock_output_path: MagicMock,
        mock_docx_template: MagicMock,
        mock_file: MagicMock,
        mock_convert_word_to_pdf: MagicMock,
    ) -> None:
        """Test that report context contains expected variables."""
        # Arrange
        mock_template_path = "/path/to/template.docx"
        mock_output_path.return_value = mock_template_path

        mock_doc = MagicMock()
        mock_docx_template.return_value = mock_doc

        mock_file_instance = MagicMock()
        mock_file.from_data.return_value = mock_file_instance

        mock_pdf_file = MagicMock()
        mock_convert_word_to_pdf.return_value = mock_pdf_file

        # Create test parameters
        bridge_id = "BR-2024-TEST"
        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": bridge_id}),
            }
        )

        # Act
        create_export_report(params)

        # Assert - Check that render was called with correct context
        mock_doc.render.assert_called_once()
        render_call_args = mock_doc.render.call_args[0][0]

        assert "BRIDGE_ID" in render_call_args
        assert render_call_args["BRIDGE_ID"] == bridge_id
        assert "DATE" in render_call_args
        # Verify date format (DD-MM-YYYY)
        assert len(render_call_args["DATE"]) == 10
        assert render_call_args["DATE"].count("-") == 2

    @patch("src.report.report_functions.datetime")
    @patch("src.report.report_functions.convert_word_to_pdf")
    @patch("src.report.report_functions.File")
    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_date_format(
        self,
        mock_output_path: MagicMock,
        mock_docx_template: MagicMock,
        mock_file: MagicMock,
        mock_convert_word_to_pdf: MagicMock,
        mock_datetime: MagicMock,
    ) -> None:
        """Test that report uses correct date format and timezone."""
        # Arrange
        mock_template_path = "/path/to/template.docx"
        mock_output_path.return_value = mock_template_path

        mock_doc = MagicMock()
        mock_docx_template.return_value = mock_doc

        mock_file_instance = MagicMock()
        mock_file.from_data.return_value = mock_file_instance

        mock_pdf_file = MagicMock()
        mock_convert_word_to_pdf.return_value = mock_pdf_file

        # Mock datetime to return a specific date
        mock_now = MagicMock()
        mock_now.strftime.return_value = "15-03-2024"
        mock_datetime.now.return_value = mock_now

        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
            }
        )

        # Act
        create_export_report(params)

        # Assert
        mock_datetime.now.assert_called_once_with(tz=ZoneInfo("Europe/Amsterdam"))
        mock_now.strftime.assert_called_once_with("%d-%m-%Y")

        render_call_args = mock_doc.render.call_args[0][0]
        assert render_call_args["DATE"] == "15-03-2024"

    def test_create_export_report_missing_bridge_id(self) -> None:
        """Test handling of missing bridge ID parameter."""
        # Arrange
        params = Munch(
            {
                "info": Munch({}),  # Missing bridge_objectnumm
            }
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            create_export_report(params)

    def test_create_export_report_missing_info_section(self) -> None:
        """Test handling of missing info section in parameters."""
        # Arrange
        params = Munch({})  # Missing info section

        # Act & Assert
        with pytest.raises(AttributeError):
            create_export_report(params)

    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_template_load_error(self, mock_output_path: MagicMock, mock_docx_template: MagicMock) -> None:
        """Test handling of template loading errors."""
        # Arrange
        mock_template_path = "/path/to/nonexistent_template.docx"
        mock_output_path.return_value = mock_template_path
        mock_docx_template.side_effect = OSError("Template file not found")

        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
            }
        )

        # Act & Assert
        with pytest.raises(OSError, match="Template file not found"):
            create_export_report(params)

    @patch("src.report.report_functions.convert_word_to_pdf")
    @patch("src.report.report_functions.File")
    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_template_render_error(
        self,
        mock_output_path: MagicMock,
        mock_docx_template: MagicMock,
        mock_file: MagicMock,
        mock_convert_word_to_pdf: MagicMock,
    ) -> None:
        """Test handling of template rendering errors."""
        # Arrange
        mock_template_path = "/path/to/template.docx"
        mock_output_path.return_value = mock_template_path

        mock_doc = MagicMock()
        mock_doc.render.side_effect = Exception("Template rendering failed")
        mock_docx_template.return_value = mock_doc

        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
            }
        )

        # Act & Assert
        with pytest.raises(Exception, match="Template rendering failed"):
            create_export_report(params)

    @patch("src.report.report_functions.convert_word_to_pdf")
    @patch("src.report.report_functions.File")
    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_save_error(
        self,
        mock_output_path: MagicMock,
        mock_docx_template: MagicMock,
        mock_file: MagicMock,
        mock_convert_word_to_pdf: MagicMock,
    ) -> None:
        """Test handling of document save errors."""
        # Arrange
        mock_template_path = "/path/to/template.docx"
        mock_output_path.return_value = mock_template_path

        mock_doc = MagicMock()
        mock_doc.save.side_effect = OSError("Cannot save document")
        mock_docx_template.return_value = mock_doc

        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
            }
        )

        # Act & Assert
        with pytest.raises(OSError, match="Cannot save document"):
            create_export_report(params)

    @patch("src.report.report_functions.convert_word_to_pdf")
    @patch("src.report.report_functions.File")
    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_pdf_conversion_error(
        self,
        mock_output_path: MagicMock,
        mock_docx_template: MagicMock,
        mock_file: MagicMock,
        mock_convert_word_to_pdf: MagicMock,
    ) -> None:
        """Test handling of PDF conversion errors."""
        # Arrange
        mock_template_path = "/path/to/template.docx"
        mock_output_path.return_value = mock_template_path

        mock_doc = MagicMock()
        mock_docx_template.return_value = mock_doc

        mock_file_instance = MagicMock()
        mock_file.from_data.return_value = mock_file_instance

        mock_convert_word_to_pdf.side_effect = Exception("PDF conversion failed")

        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
            }
        )

        # Act & Assert
        with pytest.raises(Exception, match="PDF conversion failed"):
            create_export_report(params)

    @patch("src.report.report_functions.convert_word_to_pdf")
    @patch("src.report.report_functions.File")
    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_file_operations(
        self,
        mock_output_path: MagicMock,
        mock_docx_template: MagicMock,
        mock_file: MagicMock,
        mock_convert_word_to_pdf: MagicMock,
    ) -> None:
        """Test that file operations are performed in correct sequence."""
        # Arrange
        mock_template_path = "/path/to/template.docx"
        mock_output_path.return_value = mock_template_path

        mock_doc = MagicMock()
        mock_docx_template.return_value = mock_doc

        mock_binary_io = MagicMock(spec=BytesIO)
        mock_doc.save.side_effect = lambda x: x  # Just return the BytesIO object

        mock_file_instance = MagicMock()
        mock_file_instance.open_binary.return_value.__enter__.return_value = mock_binary_io
        mock_file.from_data.return_value = mock_file_instance

        mock_pdf_file = MagicMock()
        mock_convert_word_to_pdf.return_value = mock_pdf_file

        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
            }
        )

        # Act
        result = create_export_report(params)

        # Assert sequence of operations
        mock_docx_template.assert_called_once_with(mock_output_path)
        mock_doc.render.assert_called_once()
        mock_doc.save.assert_called_once()
        mock_file.from_data.assert_called_once()
        mock_file_instance.open_binary.assert_called_once()
        mock_convert_word_to_pdf.assert_called_once_with(mock_binary_io)
        assert result == mock_pdf_file

    @patch("src.report.report_functions.convert_word_to_pdf")
    @patch("src.report.report_functions.File")
    @patch("src.report.report_functions.DocxTemplate")
    @patch("src.report.report_functions.OUTPUT_REPORT_PATH")
    def test_create_export_report_special_characters_in_bridge_id(
        self,
        mock_output_path: MagicMock,
        mock_docx_template: MagicMock,
        mock_file: MagicMock,
        mock_convert_word_to_pdf: MagicMock,
    ) -> None:
        """Test handling of special characters in bridge ID."""
        # Arrange
        mock_template_path = "/path/to/template.docx"
        mock_output_path.return_value = mock_template_path

        mock_doc = MagicMock()
        mock_docx_template.return_value = mock_doc

        mock_file_instance = MagicMock()
        mock_file.from_data.return_value = mock_file_instance

        mock_pdf_file = MagicMock()
        mock_convert_word_to_pdf.return_value = mock_pdf_file

        # Bridge ID with special characters (note: function documentation warns about <, >, & characters)
        bridge_id_with_special_chars = "BR-2024-001/A"
        params = Munch(
            {
                "info": Munch({"bridge_objectnumm": bridge_id_with_special_chars}),
            }
        )

        # Act
        create_export_report(params)

        # Assert - Verify that special characters are passed through as-is
        render_call_args = mock_doc.render.call_args[0][0]
        assert render_call_args["BRIDGE_ID"] == bridge_id_with_special_chars


if __name__ == "__main__":
    unittest.main()
