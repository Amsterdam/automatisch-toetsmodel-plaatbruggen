"""Tests for VIKTOR views in app.bridge.controller module."""

import json
import unittest
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.bridge.controller import BridgeController
from tests.test_data.seed_loader import load_bridge_complex_params, load_bridge_default_params
from tests.test_utils import view_test_wrapper


class TestBridgeControllerViews(unittest.TestCase):
    """Test cases for BridgeController VIKTOR views."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = BridgeController()
        self.default_params = load_bridge_default_params()
        self.complex_params = load_bridge_complex_params()

    def test_view_methods_exist(self) -> None:
        """Test that all view methods exist and are callable."""
        view_methods = [
            "get_3d_view",
            "get_2d_cross_section",
            "get_2d_horizontal_section",
            "get_2d_longitudinal_section",
            "get_top_view",
            "get_load_zones_view",
            "get_output_report",
            "get_bridge_map_view",
        ]

        for method_name in view_methods:
            with self.subTest(method=method_name):
                assert hasattr(self.controller, method_name)
                assert callable(getattr(self.controller, method_name))

    def test_controller_has_parametrization(self) -> None:
        """Test that the controller has the correct parametrization."""
        from app.bridge.parametrization import BridgeParametrization

        assert self.controller.parametrization == BridgeParametrization

    def test_controller_label(self) -> None:
        """Test that the controller has the correct label."""
        assert self.controller.label == "Brug"

    # ============================================================================================================
    # PHASE 2: Full View Execution Tests - Bypassing VIKTOR Decorators
    # ============================================================================================================

    @patch("app.bridge.controller.create_3d_model")
    @patch("trimesh.exchange.gltf.export_glb")
    @view_test_wrapper("get_3d_view")
    def test_get_3d_view_execution(self, mock_export_glb: MagicMock, mock_create_3d: MagicMock) -> None:
        """Test actual execution of get_3d_view with mocked dependencies."""
        # Arrange
        mock_scene = MagicMock()
        mock_create_3d.return_value = mock_scene
        mock_export_glb.return_value = b"fake_gltf_data"

        # Access the original method directly
        original_method = self.controller.__class__.get_3d_view

        # Act - call bypassing decorator
        result = original_method(self.controller, self.default_params)

        # Assert
        from viktor.views import GeometryResult

        assert isinstance(result, GeometryResult)
        mock_create_3d.assert_called_once_with(self.default_params, section_planes=True)
        mock_export_glb.assert_called_once_with(mock_scene)

    @patch("app.bridge.controller.build_top_view_figure")
    @patch("app.bridge.controller.create_2d_top_view")
    @patch("app.bridge.controller.validate_load_zone_widths")
    @view_test_wrapper("get_top_view")
    def test_get_top_view_execution(self, mock_validate_widths: MagicMock, mock_create_2d: MagicMock, mock_build_figure: MagicMock) -> None:
        """Test actual execution of get_top_view with mocked dependencies."""
        # Arrange
        mock_top_view_data: dict[str, list[Any]] = {"bridge_lines": [], "structural_polygons": []}
        mock_create_2d.return_value = mock_top_view_data
        mock_validate_widths.return_value = []

        mock_fig = Mock()
        mock_fig.to_json.return_value = '{"data": [], "layout": {}}'
        mock_build_figure.return_value = mock_fig

        # Access the original method directly
        original_method = self.controller.__class__.get_top_view

        # Act - call bypassing decorator
        result = original_method(self.controller, self.default_params)

        # Assert
        from viktor.views import PlotlyResult

        assert isinstance(result, PlotlyResult)
        mock_create_2d.assert_called_once_with(self.default_params)
        mock_build_figure.assert_called_once()

        # Verify JSON result is valid - PlotlyResult stores figure in .figure attribute
        json_result = json.loads(result.figure)
        assert "data" in json_result
        assert "layout" in json_result

    @patch("app.bridge.controller.create_horizontal_section_view")
    @view_test_wrapper("get_2d_horizontal_section")
    def test_get_2d_horizontal_section_execution(self, mock_create_horizontal: MagicMock) -> None:
        """Test actual execution of get_2d_horizontal_section."""
        # Arrange
        mock_fig = Mock()
        mock_fig.to_json.return_value = '{"data": [], "layout": {"title": "Horizontal Section"}}'
        mock_create_horizontal.return_value = mock_fig

        # Access the original method directly
        original_method = self.controller.__class__.get_2d_horizontal_section

        # Act - call bypassing decorator
        result = original_method(self.controller, self.default_params)

        # Assert
        from viktor.views import PlotlyResult

        assert isinstance(result, PlotlyResult)
        mock_create_horizontal.assert_called_once_with(self.default_params, self.default_params.input.dimensions.horizontal_section_loc)

        # Verify JSON result - PlotlyResult stores figure in .figure attribute
        json_result = json.loads(result.figure)
        assert "layout" in json_result

    @patch("app.bridge.controller.create_longitudinal_section")
    @view_test_wrapper("get_2d_longitudinal_section")
    def test_get_2d_longitudinal_section_execution(self, mock_create_longitudinal: MagicMock) -> None:
        """Test actual execution of get_2d_longitudinal_section."""
        # Arrange
        mock_fig = Mock()
        mock_fig.to_json.return_value = '{"data": [], "layout": {"title": "Longitudinal Section"}}'
        mock_create_longitudinal.return_value = mock_fig

        # Access the original method directly
        original_method = self.controller.__class__.get_2d_longitudinal_section

        # Act - call bypassing decorator
        result = original_method(self.controller, self.default_params)

        # Assert
        from viktor.views import PlotlyResult

        assert isinstance(result, PlotlyResult)
        mock_create_longitudinal.assert_called_once_with(self.default_params, self.default_params.input.dimensions.longitudinal_section_loc)

    @patch("app.bridge.controller.create_cross_section_view")
    @view_test_wrapper("get_2d_cross_section")
    def test_get_2d_cross_section_execution(self, mock_create_cross: MagicMock) -> None:
        """Test actual execution of get_2d_cross_section."""
        # Arrange
        mock_fig = Mock()
        mock_fig.to_json.return_value = '{"data": [], "layout": {"title": "Cross Section"}}'
        mock_create_cross.return_value = mock_fig

        # Access the original method directly
        original_method = self.controller.__class__.get_2d_cross_section

        # Act - call bypassing decorator
        result = original_method(self.controller, self.default_params)

        # Assert
        from viktor.views import PlotlyResult

        assert isinstance(result, PlotlyResult)
        mock_create_cross.assert_called_once_with(self.default_params, self.default_params.input.dimensions.cross_section_loc)

    @patch("app.bridge.controller.build_load_zones_figure")
    @view_test_wrapper("get_load_zones_view")
    def test_get_load_zones_view_execution_with_zones(self, mock_build_zones: MagicMock) -> None:
        """Test actual execution of get_load_zones_view with load zones present."""
        # Arrange
        mock_fig = Mock()
        mock_fig.to_json.return_value = '{"data": [], "layout": {"title": "Load Zones"}}'
        mock_build_zones.return_value = mock_fig

        # Access the original method directly
        original_method = self.controller.__class__.get_load_zones_view

        # Act - call bypassing decorator
        result = original_method(self.controller, self.default_params)

        # Assert
        from viktor.views import PlotlyResult

        assert isinstance(result, PlotlyResult)

        # Verify JSON result
        json_result = json.loads(result.figure)
        assert "data" in json_result
        assert "layout" in json_result

    @view_test_wrapper("get_load_zones_view")
    def test_get_load_zones_view_no_zones(self) -> None:
        """Test get_load_zones_view when no load zones are defined."""
        # Arrange - create params with empty load zones
        params_no_zones = self.default_params.copy()
        params_no_zones.load_zones_data_array = []

        # Access the original method directly
        original_method = self.controller.__class__.get_load_zones_view

        # Act - call bypassing decorator
        result = original_method(self.controller, params_no_zones)

        # Assert
        from viktor.views import PlotlyResult

        assert isinstance(result, PlotlyResult)

        # Should return a figure with appropriate message
        json_result = json.loads(result.figure)
        assert "layout" in json_result

    @patch("app.bridge.controller.api_sdk.API")
    @view_test_wrapper("get_bridge_map_view")
    def test_get_bridge_map_view_execution_invalid_entity(self, _mock_api_class: MagicMock) -> None:  # noqa: PT019
        """Test get_bridge_map_view with invalid entity ID."""
        # Access the original method directly
        original_method = self.controller.__class__.get_bridge_map_view

        # Act - call bypassing decorator with entity_id in kwargs
        result = original_method(self.controller, self.default_params, entity_id=None)

        # Assert
        from viktor.views import MapResult

        assert isinstance(result, MapResult)
        assert len(result.features) > 0

        # Should contain error message
        error_point = result.features[0]
        assert "Ongeldige entity ID" in error_point._description  # noqa: SLF001

    @view_test_wrapper("get_output_report")
    def test_get_output_report_execution(self) -> None:
        """Test actual execution of get_output_report."""
        # Access the original method directly
        original_method = self.controller.__class__.get_output_report

        # Act - call bypassing decorator - this should raise UserError when disabled
        from viktor.errors import UserError

        with pytest.raises(UserError, match="Report generation is temporarily disabled"):
            original_method(self.controller, self.default_params)

    # ============================================================================================================
    # Error Handling Tests
    # ============================================================================================================

    @patch("app.bridge.controller.create_3d_model")
    @view_test_wrapper("get_3d_view")
    def test_get_3d_view_error_handling(self, mock_create_3d: MagicMock) -> None:
        """Test error handling in get_3d_view when 3D model creation fails."""
        # Arrange
        mock_create_3d.side_effect = Exception("3D model creation failed")

        # Access the original method directly
        original_method = self.controller.__class__.get_3d_view

        # Act & Assert
        with pytest.raises(Exception):
            original_method(self.controller, self.default_params)

    @view_test_wrapper("get_load_zones_view")
    def test_get_load_zones_view_invalid_bridge_segments(self) -> None:
        """Test get_load_zones_view when bridge segments are invalid."""
        # Arrange - create params with invalid bridge segments
        params_invalid = self.default_params.copy()
        params_invalid.bridge_segments_array = []  # Empty segments

        # Access the original method directly
        original_method = self.controller.__class__.get_load_zones_view

        # Act - call bypassing decorator
        result = original_method(self.controller, params_invalid)

        # Assert
        from viktor.views import PlotlyResult

        assert isinstance(result, PlotlyResult)

        # Should return error figure
        json_result = json.loads(result.figure)
        assert "layout" in json_result

    # ============================================================================================================
    # Data Validation Tests
    # ============================================================================================================

    def test_seed_data_loaded_correctly(self) -> None:
        """Test that seed data is loaded correctly for view testing."""
        # Test default params
        assert "info" in self.default_params
        assert "bridge_segments_array" in self.default_params
        assert "load_zones_data_array" in self.default_params

        # Test complex params
        assert "info" in self.complex_params
        assert "bridge_segments_array" in self.complex_params
        assert "load_zones_data_array" in self.complex_params

        # Verify structure for view method access
        assert hasattr(self.default_params.info, "bridge_objectnumm")
        assert hasattr(self.default_params.info, "bridge_name")
        assert hasattr(self.default_params.input.dimensions, "horizontal_section_loc")

    @view_test_wrapper("get_output_report")
    def test_download_report_execution(self) -> None:
        """Test actual execution of get_output_report."""
        # Access the original method directly
        original_method = self.controller.__class__.get_output_report

        # Act - call bypassing decorator - this should raise UserError when disabled
        from viktor.errors import UserError

        with pytest.raises(UserError, match="Report generation is temporarily disabled"):
            original_method(self.controller, self.default_params)


if __name__ == "__main__":
    unittest.main()
