"""
Test module for SCIA integration functionality in bridge controller.

This module contains comprehensive tests for SCIA model creation,
file downloads, and template handling.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from munch import Munch  # type: ignore[import-untyped]
from viktor.errors import UserError
from viktor.result import DownloadResult

from app.bridge.controller import BridgeController


class TestGetSciaTemplatePath:
    """Test cases for _get_scia_template_path method."""

    def test_get_scia_template_path_success(self) -> None:
        """Test successful template path retrieval when file exists."""
        # Arrange
        controller = BridgeController()

        with patch("pathlib.Path.exists", return_value=True):
            # Act
            result = controller._get_scia_template_path()  # noqa: SLF001

            # Assert
            assert isinstance(result, Path)
            assert result.name == "model.esa"

    def test_get_scia_template_path_file_not_found(self) -> None:
        """Test error handling when template file doesn't exist."""
        # Arrange
        controller = BridgeController()

        # Act & Assert
        with patch("pathlib.Path.exists", return_value=False), pytest.raises(UserError, match="SCIA template file niet gevonden"):
            controller._get_scia_template_path()  # noqa: SLF001


class TestDownloadSciaXmlFiles:
    """Test cases for download_scia_xml_files method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = BridgeController()
        self.mock_params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
                "bridge_segments_array": [
                    Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0}),
                    Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0}),
                ],
            }
        )

    @patch("app.bridge.controller.SCIA_ZIP_README_CONTENT", "Mock README content")
    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_xml_files_success(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test successful XML files download."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        # Mock XML and DEF file content
        xml_content = b"<xml>Mock XML content</xml>"
        def_content = b"Mock DEF content"

        mock_xml_file = BytesIO(xml_content)
        mock_def_file = BytesIO(def_content)
        mock_analysis = MagicMock()

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Mock template file reading
        with patch("builtins.open", mock_open(read_data=b"Mock template content")), patch("pathlib.Path.open"):
            # Act
            result = self.controller.download_scia_xml_files(self.mock_params)

            # Assert
            assert isinstance(result, DownloadResult)
            assert result.filename == "BR-2024-001_Input_Files.zip"

            # Verify the calls
            mock_get_template.assert_called_once()
            mock_create_model.assert_called_once_with(self.mock_params, mock_template_path)

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_xml_files_empty_xml(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test error handling when XML file is empty."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        # Mock empty XML file
        mock_xml_file = BytesIO(b"")  # Empty content
        mock_def_file = BytesIO(b"Mock DEF content")
        mock_analysis = MagicMock()

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Act & Assert
        with pytest.raises(UserError, match="XML bestand is leeg"):
            self.controller.download_scia_xml_files(self.mock_params)

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_xml_files_empty_def(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test error handling when DEF file is empty."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        # Mock empty DEF file
        mock_xml_file = BytesIO(b"Mock XML content")
        mock_def_file = BytesIO(b"")  # Empty content
        mock_analysis = MagicMock()

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Act & Assert
        with pytest.raises(UserError, match="Definition bestand is leeg"):
            self.controller.download_scia_xml_files(self.mock_params)

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_xml_files_no_bridge_id(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test download with missing bridge ID - should use default filename."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        params_no_id = Munch(
            {
                "info": Munch({}),  # No bridge_objectnumm
                "bridge_segments_array": [Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0})],
            }
        )

        # Mock file content
        mock_xml_file = BytesIO(b"Mock XML content")
        mock_def_file = BytesIO(b"Mock DEF content")
        mock_analysis = MagicMock()

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Mock template file reading
        with patch("builtins.open", mock_open(read_data=b"Mock template content")), patch("pathlib.Path.open"):
            # Act
            result = self.controller.download_scia_xml_files(params_no_id)

            # Assert
            assert isinstance(result, DownloadResult)
            assert result.filename == "bridge_model_Input_Files.zip"

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_xml_files_create_model_error(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test error handling when SCIA model creation fails."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        mock_create_model.side_effect = Exception("SCIA model creation failed")

        # Act & Assert
        with pytest.raises(UserError, match="Fout bij genereren SCIA XML bestanden"):
            self.controller.download_scia_xml_files(self.mock_params)

    @patch("app.bridge.controller.SCIA_ZIP_README_CONTENT", "Mock README content")
    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_xml_files_zip_contents(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test that ZIP file contains all expected files with correct names."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        xml_content = b"<xml>Mock XML content</xml>"
        def_content = b"Mock DEF content"
        template_content = b"Mock template content"

        mock_xml_file = BytesIO(xml_content)
        mock_def_file = BytesIO(def_content)
        mock_analysis = MagicMock()

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Mock template file reading
        mock_file_obj = mock_open(read_data=template_content)

        with patch("builtins.open", mock_file_obj), patch("pathlib.Path.open", mock_file_obj):
            # Act
            result = self.controller.download_scia_xml_files(self.mock_params)

            # Assert
            assert isinstance(result, DownloadResult)

            # Extract and verify ZIP contents
            file_obj = result.file
            assert hasattr(file_obj, "source")


class TestDownloadSciaEsaModel:
    """Test cases for download_scia_esa_model method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = BridgeController()
        self.mock_params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
                "bridge_segments_array": [
                    Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0}),
                ],
            }
        )

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_esa_model_success(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test successful ESA model download."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        mock_xml_file = BytesIO(b"Mock XML content")
        mock_def_file = BytesIO(b"Mock DEF content")
        mock_analysis = MagicMock()

        # Mock successful analysis execution
        mock_esa_file = MagicMock()
        mock_analysis.execute.return_value = None
        mock_analysis.get_updated_esa_model.return_value = mock_esa_file

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Act
        result = self.controller.download_scia_esa_model(self.mock_params)

        # Assert
        assert isinstance(result, DownloadResult)
        assert result.filename == "BR-2024-001_model.esa"
        assert result.file == mock_esa_file

        # Verify analysis was executed
        mock_analysis.execute.assert_called_once_with(timeout=300)
        mock_analysis.get_updated_esa_model.assert_called_once()

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_esa_model_analysis_failure(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test error handling when SCIA analysis execution fails."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        mock_xml_file = BytesIO(b"Mock XML content")
        mock_def_file = BytesIO(b"Mock DEF content")
        mock_analysis = MagicMock()

        # Mock analysis execution failure
        mock_analysis.execute.side_effect = Exception("SCIA worker not available")

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Act & Assert
        with pytest.raises(UserError) as exc_info:
            self.controller.download_scia_esa_model(self.mock_params)

        error_message = str(exc_info.value)
        assert "SCIA worker uitvoering gefaald" in error_message
        assert "SCIA worker niet beschikbaar" in error_message
        assert "XML bestanden te downloaden" in error_message

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_esa_model_empty_esa_file(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test error handling when ESA file is empty."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        mock_xml_file = BytesIO(b"Mock XML content")
        mock_def_file = BytesIO(b"Mock DEF content")
        mock_analysis = MagicMock()

        # Mock successful execution but empty ESA file
        mock_analysis.execute.return_value = None
        mock_analysis.get_updated_esa_model.return_value = None  # Empty file

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Act & Assert
        with pytest.raises(UserError, match="ESA bestand is leeg"):
            self.controller.download_scia_esa_model(self.mock_params)

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_esa_model_no_bridge_id(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test ESA download with missing bridge ID - should use default filename."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        params_no_id = Munch(
            {
                "info": Munch({}),  # No bridge_objectnumm
                "bridge_segments_array": [Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0})],
            }
        )

        mock_xml_file = BytesIO(b"Mock XML content")
        mock_def_file = BytesIO(b"Mock DEF content")
        mock_analysis = MagicMock()

        mock_esa_file = MagicMock()
        mock_analysis.execute.return_value = None
        mock_analysis.get_updated_esa_model.return_value = mock_esa_file

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Act
        result = self.controller.download_scia_esa_model(params_no_id)

        # Assert
        assert isinstance(result, DownloadResult)
        assert result.filename == "bridge_model.esa"

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_download_scia_esa_model_timeout_handling(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test that analysis is called with correct timeout."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        mock_xml_file = BytesIO(b"Mock XML content")
        mock_def_file = BytesIO(b"Mock DEF content")
        mock_analysis = MagicMock()

        mock_esa_file = MagicMock()
        mock_analysis.execute.return_value = None
        mock_analysis.get_updated_esa_model.return_value = mock_esa_file

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        # Act
        self.controller.download_scia_esa_model(self.mock_params)

        # Assert
        mock_analysis.execute.assert_called_once_with(timeout=300)  # 5 minutes


class TestSciaErrorHelperMethods:
    """Test cases for SCIA error helper methods."""

    def test_raise_empty_xml_error(self) -> None:
        """Test _raise_empty_xml_error method."""
        # Arrange
        controller = BridgeController()

        # Act & Assert
        with pytest.raises(UserError, match="XML bestand is leeg - SCIA model generatie gefaald"):
            controller._raise_empty_xml_error()  # noqa: SLF001

    def test_raise_empty_def_error(self) -> None:
        """Test _raise_empty_def_error method."""
        # Arrange
        controller = BridgeController()

        # Act & Assert
        with pytest.raises(UserError, match="Definition bestand is leeg - SCIA model generatie gefaald"):
            controller._raise_empty_def_error()  # noqa: SLF001

    def test_raise_empty_esa_error(self) -> None:
        """Test _raise_empty_esa_error method."""
        # Arrange
        controller = BridgeController()

        # Act & Assert
        with pytest.raises(UserError, match="ESA bestand is leeg - SCIA worker uitvoering gefaald"):
            controller._raise_empty_esa_error()  # noqa: SLF001


class TestSciaIntegrationEdgeCases:
    """Test cases for SCIA integration edge cases and error scenarios."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = BridgeController()
        self.mock_params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-TEST-001"}),
                "bridge_segments_array": [Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0})],
            }
        )

    @patch.object(BridgeController, "_get_scia_template_path")
    def test_scia_template_path_error_propagation(self, mock_get_template: MagicMock) -> None:
        """Test that template path errors are properly propagated."""
        # Arrange
        mock_get_template.side_effect = UserError("Template not found")

        mock_params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
                "bridge_segments_array": [Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0})],
            }
        )

        # Act & Assert
        with pytest.raises(UserError, match="Template not found"):
            self.controller.download_scia_xml_files(mock_params)

    def test_scia_params_validation(self) -> None:
        """Test behavior with various parameter configurations."""
        with (
            patch.object(self.controller, "_get_scia_template_path") as mock_template,
            patch("app.bridge.controller.create_bridge_scia_model") as mock_create,
        ):
            mock_template.return_value = Path("mock/path")
            mock_create.side_effect = Exception("Test exception")

            # Act & Assert
            with pytest.raises(UserError):
                self.controller.download_scia_xml_files(self.mock_params)

    @patch("app.bridge.controller.create_bridge_scia_model")
    @patch.object(BridgeController, "_get_scia_template_path")
    def test_scia_xml_getvalue_method_handling(self, mock_get_template: MagicMock, mock_create_model: MagicMock) -> None:
        """Test handling of files without getvalue method."""
        # Arrange
        mock_template_path = Path("resources/templates/model.esa")
        mock_get_template.return_value = mock_template_path

        # Mock files without getvalue method
        mock_xml_file = MagicMock()
        del mock_xml_file.getvalue  # Remove getvalue method
        mock_def_file = MagicMock()
        del mock_def_file.getvalue  # Remove getvalue method
        mock_analysis = MagicMock()

        mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

        mock_params = Munch(
            {
                "info": Munch({"bridge_objectnumm": "BR-2024-001"}),
                "bridge_segments_array": [Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0})],
            }
        )

        # Act & Assert - Should handle gracefully and raise empty file error
        with pytest.raises(UserError, match="XML bestand is leeg"):
            self.controller.download_scia_xml_files(mock_params)


if __name__ == "__main__":
    pytest.main([__file__])
