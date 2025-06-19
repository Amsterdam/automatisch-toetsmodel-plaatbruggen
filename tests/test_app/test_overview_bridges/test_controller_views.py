"""Tests for VIKTOR views in app.overview_bridges.controller module."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from app.overview_bridges.controller import OverviewBridgesController
from tests.test_data.seed_loader import load_overview_bridges_default_params
from tests.test_utils import view_test_wrapper


class TestOverviewBridgesControllerViews(unittest.TestCase):
    """Test cases for OverviewBridgesController VIKTOR views."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = OverviewBridgesController()
        self.default_params = load_overview_bridges_default_params()

    def test_controller_has_parametrization(self) -> None:
        """Test that the controller has the correct parametrization."""
        from app.overview_bridges.parametrization import OverviewBridgesParametrization

        assert self.controller.parametrization == OverviewBridgesParametrization

    def test_controller_label(self) -> None:
        """Test that the controller has the correct label."""
        assert self.controller.label == "Overzicht Bruggen"

    def test_controller_children_configuration(self) -> None:
        """Test that the controller has correct children configuration."""
        assert self.controller.children == ["Bridge"]
        assert self.controller.show_children_as == "Table"

    # ============================================================================================================
    # PHASE 1: Basic Method Existence Tests
    # ============================================================================================================

    def test_view_methods_exist(self) -> None:
        """Test that the view methods exist and are callable."""
        view_methods = [
            "get_map_view",
            "view_readme_changelog",
        ]

        for method_name in view_methods:
            with self.subTest(method=method_name):
                assert hasattr(self.controller, method_name)
                assert callable(getattr(self.controller, method_name))

    # ============================================================================================================
    # PHASE 2: Full View Execution Tests - Bypassing VIKTOR Decorators
    # ============================================================================================================

    @patch("app.overview_bridges.controller.get_default_shapefile_path")
    @patch("app.overview_bridges.controller.get_filtered_bridges_json_path")
    @patch("app.overview_bridges.controller.validate_shapefile_exists")
    @patch("app.overview_bridges.controller.load_and_prepare_shapefile")
    @patch("app.overview_bridges.controller.process_all_bridges_geometries")
    @patch("builtins.open")
    @patch("os.path.exists")
    @view_test_wrapper("get_map_view")
    def test_get_map_view_execution_with_bridges(  # noqa: PLR0913
        self,
        mock_exists: MagicMock,
        mock_open: MagicMock,
        mock_process_geometries: MagicMock,
        mock_load_shapefile: MagicMock,
        mock_validate_shapefile: MagicMock,
        mock_filtered_path: MagicMock,
        mock_default_path: MagicMock,
    ) -> None:
        """Test actual execution of get_map_view with bridges data."""
        # Arrange
        mock_default_path.return_value = "/fake/path/bridges.shp"
        mock_filtered_path.return_value = "/fake/path/filtered_bridges.json"
        mock_validate_shapefile.return_value = "/fake/path/bridges.shp"
        mock_exists.return_value = True

        # Mock JSON file content using MagicMock for proper context manager support
        mock_file = MagicMock()
        mock_file.read.return_value = '[{"OBJECTNUMM": "BRIDGE-001"}]'
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock GeoDataFrame and processing
        mock_gdf = MagicMock()
        mock_gdf.empty = False
        mock_load_shapefile.return_value = mock_gdf

        # Mock processed features
        mock_features = [MagicMock(), MagicMock()]
        mock_process_geometries.return_value = mock_features

        # Access the original method directly
        original_method = self.controller.__class__.get_map_view

        # Act - call bypassing decorator
        result = original_method(self.controller, self.default_params)

        # Assert
        from viktor.views import MapResult

        assert isinstance(result, MapResult)
        assert len(result.features) == 2

        # Verify method calls
        mock_default_path.assert_called_once()
        mock_filtered_path.assert_called_once()
        mock_validate_shapefile.assert_called_once()
        mock_load_shapefile.assert_called_once()
        mock_process_geometries.assert_called_once()

    @patch("app.overview_bridges.controller.get_default_shapefile_path")
    @patch("app.overview_bridges.controller.get_filtered_bridges_json_path")
    @patch("app.overview_bridges.controller.validate_shapefile_exists")
    @patch("os.path.exists")
    @view_test_wrapper("get_map_view")
    def test_get_map_view_execution_no_bridges(
        self, mock_exists: MagicMock, mock_validate_shapefile: MagicMock, mock_filtered_path: MagicMock, mock_default_path: MagicMock
    ) -> None:
        """Test get_map_view when no bridges are found."""
        # Arrange
        mock_default_path.return_value = "/fake/path/bridges.shp"
        mock_filtered_path.return_value = "/fake/path/filtered_bridges.json"
        mock_validate_shapefile.return_value = "/fake/path/bridges.shp"
        mock_exists.return_value = False

        # Access the original method directly
        original_method = self.controller.__class__.get_map_view

        # Act & Assert - should raise UserError for missing filter file
        from viktor.errors import UserError

        with pytest.raises(UserError) as context:
            original_method(self.controller, self.default_params)

        assert "Filter bestand niet gevonden" in str(context.value)

    @patch("app.overview_bridges.controller.CHANGELOG_PATH", "/fake/changelog.md")
    @patch("app.overview_bridges.controller.README_PATH", "/fake/readme.md")
    @patch("app.overview_bridges.controller.CSS_PATH", "/fake/style.css")
    @patch("builtins.open")
    @patch("markdown.markdown")
    @view_test_wrapper("view_readme_changelog")
    def test_view_readme_changelog_execution(self, mock_markdown: MagicMock, mock_open: MagicMock) -> None:
        """Test actual execution of view_readme_changelog."""
        # Arrange
        mock_file_content = MagicMock()
        mock_file_content.read.return_value = "# Test Content"
        mock_open.return_value.__enter__.return_value = mock_file_content

        mock_markdown.return_value = "<h1>Test Content</h1>"

        # Access the original method directly
        original_method = self.controller.__class__.view_readme_changelog

        # Act - call bypassing decorator (method doesn't take params)
        result = original_method(self.controller)

        # Assert
        from viktor.views import WebResult

        assert isinstance(result, WebResult)

        # Verify markdown conversion was called
        assert mock_markdown.call_count == 2  # Called for both README and CHANGELOG

        # Verify file opening was attempted
        assert mock_open.called

    # ============================================================================================================
    # Error Handling Tests
    # ============================================================================================================

    @patch("app.overview_bridges.controller.get_default_shapefile_path")
    @view_test_wrapper("get_map_view")
    def test_get_map_view_error_handling(self, mock_default_path: MagicMock) -> None:
        """Test error handling in get_map_view when shapefile path fails."""
        # Arrange
        mock_default_path.side_effect = Exception("Path determination failed")

        # Access the original method directly
        original_method = self.controller.__class__.get_map_view

        # Act & Assert
        from viktor.errors import UserError

        with pytest.raises(UserError) as context:
            original_method(self.controller, self.default_params)

        assert "Fout bij het bepalen van bestandspaden" in str(context.value)

    @patch("app.overview_bridges.controller.README_PATH", "/nonexistent/readme.md")
    @patch("builtins.open")
    @view_test_wrapper("view_readme_changelog")
    def test_view_readme_changelog_file_error(self, mock_open: MagicMock) -> None:
        """Test error handling in view_readme_changelog when files are missing."""
        # Arrange
        mock_open.side_effect = FileNotFoundError("File not found")

        # Access the original method directly
        original_method = self.controller.__class__.view_readme_changelog

        # Act & Assert - should raise FileNotFoundError (method doesn't wrap file errors)
        with pytest.raises(FileNotFoundError) as context:
            original_method(self.controller)

        assert "File not found" in str(context.value)

    # ============================================================================================================
    # Data Validation Tests
    # ============================================================================================================

    def test_seed_data_loaded_correctly(self) -> None:
        """Test that seed data is loaded correctly for view testing."""
        # Test that params object has expected structure
        assert self.default_params is not None

        # The overview bridges parametrization should have minimal structure
        # since it's mainly for managing children and viewing documentation
        assert hasattr(self.default_params, "__dict__") or hasattr(self.default_params, "_asdict")


if __name__ == "__main__":
    unittest.main()
