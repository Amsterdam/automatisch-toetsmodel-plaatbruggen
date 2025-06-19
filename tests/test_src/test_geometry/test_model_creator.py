"""
Test module for 3D model creation functionality.

This module contains tests for creating 3D models, axes, cross-sections,
and related geometry operations using trimesh.
"""

import math
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import trimesh  # For type hints and potentially direct use in complex mocks
from munch import Munch  # type: ignore[import-untyped]

from src.geometry.model_creator import (
    BridgeSegmentDimensions,  # For test data construction
    LoadZoneGeometryData,  # For type hints in assertions
    create_2d_top_view,  # Added for future tests
    create_3d_model,  # Added for future tests
    create_axes,
    create_black_dot,
    create_box,
    create_cross_section,
    prepare_load_zone_geometry_data,  # Added for future tests
)


class TestModelCreator(unittest.TestCase):
    """Test cases for 3D model creation and geometry generation."""

    def test_create_box(self) -> None:
        """Test the create_box function with basic parameters."""
        vertices = np.array(
            [
                [0, 0, 0],  # bottom-left-front
                [1, 0, 0],  # bottom-right-front
                [1, 1, 0],  # bottom-right-back
                [0, 1, 0],  # bottom-left-back
                [0, 0, 1],  # top-left-front
                [1, 0, 1],  # top-right-front
                [1, 1, 1],  # top-right-back
                [0, 1, 1],  # top-left-back
            ]
        )
        color = [100, 100, 100, 255]
        box_mesh = create_box(vertices, color)

        assert isinstance(box_mesh, trimesh.Trimesh)
        assert np.array_equal(box_mesh.vertices, vertices)
        # Expected 12 faces (2 triangles per side * 6 sides)
        assert len(box_mesh.faces) == 12
        assert all(np.array_equal(fc, color) for fc in box_mesh.visual.face_colors)

    def test_create_axes(self) -> None:
        """Test the create_axes function to verify axis creation and properties."""
        scene = create_axes(length=1.0, radius=0.02)
        assert isinstance(scene, trimesh.Scene)

        # The scene should contain exactly 3 geometries (X, Y, Z axes)
        assert len(scene.geometry) == 3

        # Track which axes we've found
        found_axes = {"X": False, "Y": False, "Z": False}

        # Check each geometry in the scene
        for geom_name, geometry in scene.geometry.items():
            assert isinstance(geometry, trimesh.Trimesh), f"Geometry {geom_name} should be a Trimesh"

            # Get the color of this geometry
            if hasattr(geometry.visual, "main_color"):
                main_color = geometry.visual.main_color
            elif hasattr(geometry.visual, "face_colors") and len(geometry.visual.face_colors) > 0:
                # Use the first face color if main_color is not available
                main_color = geometry.visual.face_colors[0]
            else:
                continue  # Skip if we can't determine color

            # Identify axis by color (assuming X=red, Y=green, Z=blue)
            red = [255, 0, 0, 255]
            green = [0, 255, 0, 255]
            blue = [0, 0, 255, 255]

            tolerance = 1e-6
            if np.allclose(main_color, red, atol=tolerance):
                found_axes["X"] = True
                # Basic sanity check: X-axis should extend primarily along X
                bounds = geometry.bounds
                x_extent = bounds[1, 0] - bounds[0, 0]  # max_x - min_x
                assert x_extent > 0.9, f"X-axis should have significant extent along X, got {x_extent}"
            elif np.allclose(main_color, green, atol=tolerance):
                found_axes["Y"] = True
                # Basic sanity check: Y-axis should extend primarily along Y
                bounds = geometry.bounds
                y_extent = bounds[1, 1] - bounds[0, 1]  # max_y - min_y
                assert y_extent > 0.9, f"Y-axis should have significant extent along Y, got {y_extent}"
            elif np.allclose(main_color, blue, atol=tolerance):
                found_axes["Z"] = True
                # Basic sanity check: Z-axis should extend primarily along Z
                bounds = geometry.bounds
                z_extent = bounds[1, 2] - bounds[0, 2]  # max_z - min_z
                assert z_extent > 0.9, f"Z-axis should have significant extent along Z, got {z_extent}"

        # Verify all axes were found
        assert found_axes["X"], "X-axis (red, length 1.0, radius 0.02) not found or properties incorrect"
        assert found_axes["Y"], "Y-axis (green, length 1.0, radius 0.02) not found or properties incorrect"
        assert found_axes["Z"], "Z-axis (blue, length 1.0, radius 0.02) not found or properties incorrect"

    def test_create_black_dot(self) -> None:
        """Test the create_black_dot function to verify dot creation and properties."""
        test_radius = 0.25
        dot_mesh = create_black_dot(radius=test_radius)
        assert isinstance(dot_mesh, trimesh.Trimesh)  # Icosphere returns a Trimesh

        # Check if it resembles a sphere of the given radius by checking its bounding sphere
        # Trimesh objects have a bounding_sphere attribute which is a (center, radius) tuple
        # However, this is for the already created mesh. Icosphere is an approximation.
        # A simpler check might be that it's convex and its extents are around 2*radius.
        assert dot_mesh.is_convex
        assert math.isclose(np.max(dot_mesh.bounding_box.extents), 2 * test_radius, abs_tol=test_radius * 0.1)  # Allow some tolerance
        assert math.isclose(np.min(dot_mesh.bounding_box.extents), 2 * test_radius, abs_tol=test_radius * 0.1)

        # Check position (should be at origin by default from icosphere)
        expected_center = np.array([0, 0, 0], dtype=float)
        actual_center = dot_mesh.centroid  # Use centroid for Trimesh objects

        np.testing.assert_array_almost_equal(actual_center, expected_center, decimal=5)

        # Check color
        assert hasattr(dot_mesh, "visual")
        assert hasattr(dot_mesh.visual, "face_colors")
        # Color is set to black [0,0,0,255]
        expected_color = np.array([0, 0, 0, 255], dtype=np.uint8)
        # All face colors should be black
        assert np.all(dot_mesh.visual.face_colors == expected_color)

    @patch("src.geometry.model_creator.create_axes")
    def test_create_cross_section(self, mock_create_axes: MagicMock) -> None:
        """Test creating a cross-section from a simple mesh."""
        # Arrange
        box_to_slice = trimesh.creation.box(extents=(2, 2, 2))
        plane_origin = [0, 0, 0]
        plane_normal = [0, 0, 1]

        # Mock create_axes to return a mock scene with a graph attribute
        mock_axes_scene = MagicMock(spec=trimesh.Scene)
        mock_axes_scene.graph = MagicMock()
        mock_axes_scene.graph.to_edgelist.return_value = []  # Simulate no edges for simplicity
        mock_axes_scene.geometry = {}  # No actual geometry needed for this part of the mock
        mock_create_axes.return_value = mock_axes_scene

        # Act
        section_scene = create_cross_section(box_to_slice, plane_origin, plane_normal, axes=True)

        # Assert
        assert isinstance(section_scene, trimesh.Scene)
        assert len(section_scene.geometry) > 0, "No geometry found in section scene"

        # Verify we have section geometry beyond just axes
        non_axis_geometries = [name for name in section_scene.geometry if not (name.startswith(("axis_", "arrow_")))]
        assert len(non_axis_geometries) >= 1, "No section geometry found beyond axes"

        # Verify the section geometry is a valid Path3D with expected properties
        section_geom = section_scene.geometry[non_axis_geometries[0]]
        assert isinstance(section_geom, trimesh.path.Path3D)
        assert len(section_geom.vertices) >= 4
        assert section_geom.is_closed  # Cross-section of a box should be closed

    def test_prepare_load_zone_geometry_data(self) -> None:
        """Test the preparation of geometric data for load zone visualization."""
        # Test with two segments
        # Segment 1 (D1): length 0 (start), bz1=1, bz2=2, bz3=1 (total width 4)
        # Segment 2 (D2): length 10 from D1, bz1=1.5, bz2=2.5, bz3=1.5 (total width 5.5)
        bridge_dims_array = [
            BridgeSegmentDimensions(bz1=1.0, bz2=2.0, bz3=1.0, segment_length=0),  # First segment, length is effectively to itself
            BridgeSegmentDimensions(bz1=1.5, bz2=2.5, bz3=1.5, segment_length=10.0),
        ]
        label_y_offset = 2.0

        result_data = prepare_load_zone_geometry_data(bridge_dims_array, label_y_offset=label_y_offset)

        assert isinstance(result_data, LoadZoneGeometryData)
        assert result_data.num_defined_d_points == 2

        assert list(result_data.x_coords_d_points) == [0.0, 10.0]

        # total_widths_at_d_points: [1+2+1=4, 1.5+2.5+1.5=5.5]
        assert list(result_data.total_widths_at_d_points) == [4.0, 5.5]

        # y_top_structural_edge_at_d_points: [4/2=2, 5.5/2=2.75]
        assert list(result_data.y_top_structural_edge_at_d_points) == [2.0, 2.75]

        # y_bridge_bottom_at_d_points: [-4/2=-2, -5.5/2=-2.75]
        assert list(result_data.y_bridge_bottom_at_d_points) == [-2.0, -2.75]

        # d_point_label_data
        assert len(result_data.d_point_label_data) == 2
        # Label D1
        label_d1 = result_data.d_point_label_data[0]
        assert label_d1.text == "D1"
        assert label_d1.x == 0.0  # x_coord of D1
        assert label_d1.y == 2.0 + label_y_offset  # y_top_edge_d1 + offset
        # Label D2
        label_d2 = result_data.d_point_label_data[1]
        assert label_d2.text == "D2"
        assert label_d2.x == 10.0  # x_coord of D2
        assert label_d2.y == 2.75 + label_y_offset  # y_top_edge_d2 + offset

    def test_prepare_load_zone_geometry_data_single_segment(self) -> None:
        """Test with a single bridge segment."""
        bridge_dims_array = [BridgeSegmentDimensions(bz1=1, bz2=2, bz3=1, segment_length=0)]
        label_y_offset = 1.0
        result_data = prepare_load_zone_geometry_data(bridge_dims_array, label_y_offset)

        assert result_data.num_defined_d_points == 1
        assert list(result_data.x_coords_d_points) == [0.0]
        assert list(result_data.total_widths_at_d_points) == [4.0]
        assert list(result_data.y_top_structural_edge_at_d_points) == [2.0]
        assert list(result_data.y_bridge_bottom_at_d_points) == [-2.0]
        assert len(result_data.d_point_label_data) == 1
        assert result_data.d_point_label_data[0].text == "D1"
        assert result_data.d_point_label_data[0].x == 0.0
        assert result_data.d_point_label_data[0].y == 2.0 + label_y_offset

    def _create_mock_bridge_segment_param(  # noqa: PLR0913
        self,
        length: float = 10.0,
        bz1: float = 1.0,
        bz2: float = 2.0,
        bz3: float = 1.0,
        dz: float = 0.5,
        dz_2: float = 0.6,
        **kwargs: Any,  # noqa: ANN401
    ) -> Munch:
        """Helper to create a single bridge segment Munch object for params."""
        segment = Munch(
            {
                "l": length,  # Keep 'l' for the data structure but use 'length' as parameter name
                "bz1": bz1,
                "bz2": bz2,
                "bz3": bz3,
                "dz": dz,
                "dz_2": dz_2,
            }
        )
        segment.update(kwargs)  # Add any additional fields
        return segment

    def _create_mock_load_zone_param(self, zone_type: str = "Voetgangers", **d_widths: Any) -> Munch:  # noqa: ANN401
        """Helper to create a single load zone Munch object for params."""
        zone = Munch({"zone_type": Munch(value=zone_type)})
        for i in range(1, 16):
            zone[f"d{i}_width"] = Munch(value=d_widths.get(f"d{i}_width", 0.0))
        return zone

    def _create_mock_viktor_params_for_top_view(self, num_bridge_segments: int = 1) -> Munch:
        """Creates mock VIKTOR params for create_2d_top_view tests."""
        params = Munch()
        # Bridge Segments
        params.bridge_segments_array = []
        for i in range(num_bridge_segments):
            # Each segment defines its length and zone dimensions
            params.bridge_segments_array.append(self._create_mock_bridge_segment_param(l=10.0 + i * 2, bz1=1, bz2=2, bz3=1))

        # Basic input structure required by create_2d_top_view
        params.input = Munch({"dimensions": Munch({})})
        return params

    def test_create_2d_top_view_simple_case(self) -> None:
        """Test create_2d_top_view with a single bridge segment (should produce NO zone polygons)."""
        params = self._create_mock_viktor_params_for_top_view(num_bridge_segments=1)
        top_view_data = create_2d_top_view(params)

        # For 1 bridge segment, num_cross_sections = 1.
        # The loop for zone_polygons is range(num_cross_sections - 1), which is range(0).
        # So, 0 zone polygons are expected.
        assert len(top_view_data["zone_polygons"]) == 0

        # Bridge lines, D-labels etc. should still be generated for the single segment.
        assert len(top_view_data["bridge_lines"]) >= 0  # Might have transverse lines for D1
        assert len(top_view_data["cross_section_labels"]) == 1  # D1 label
        assert top_view_data["cross_section_labels"][0]["text"] == "D1"

    def test_create_2d_top_view_two_segments_makes_polygons(self) -> None:
        """Test create_2d_top_view with two bridge segments (should produce zone polygons for one segment part)."""
        params = self._create_mock_viktor_params_for_top_view(num_bridge_segments=2)
        top_view_data = create_2d_top_view(params)

        # For 2 bridge segments, num_cross_sections = 2.
        # The loop for zone_polygons is range(num_cross_sections - 1) = range(1). Iterates once.
        # This one iteration creates 3 polygons (Zone1, Zone2, Zone3) for the segment part.
        assert len(top_view_data["zone_polygons"]) == 3

        # Check structure of the first polygon (e.g., Zone 1 of the first segment part)
        assert isinstance(top_view_data["zone_polygons"][0], dict)
        assert "vertices" in top_view_data["zone_polygons"][0]
        assert isinstance(top_view_data["zone_polygons"][0]["vertices"], list)
        assert len(top_view_data["zone_polygons"][0]["vertices"]) > 0
        assert isinstance(top_view_data["zone_polygons"][0]["vertices"][0], list)  # list of [x,y]
        assert len(top_view_data["zone_polygons"][0]["vertices"][0]) == 2

    @patch("src.geometry.model_creator.create_box")
    @patch("src.geometry.model_creator.create_axes")
    @patch("src.geometry.model_creator.create_section_planes")
    @patch("src.geometry.model_creator.create_rebars")
    def test_create_3d_model_with_axes_and_planes(
        self,
        mock_create_rebars: MagicMock,
        mock_create_section_planes: MagicMock,
        mock_create_axes: MagicMock,
        mock_create_box: MagicMock,
    ) -> None:
        """Test create_3d_model with axes and section planes enabled."""
        # Setup mocks - create_box should return a mesh-like object
        mock_box_mesh = MagicMock()
        mock_box_mesh.faces = np.array([[0, 1, 2], [1, 2, 3]])  # Mock faces as numpy array
        mock_box_mesh.vertices = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]])  # Mock vertices as numpy array
        mock_box_mesh.visual = MagicMock()
        mock_box_mesh.visual.face_colors = []
        mock_box_mesh.visual.vertex_colors = []
        mock_create_box.return_value = mock_box_mesh

        # Setup scene mocks
        mock_rebars_scene_instance = MagicMock()
        mock_axes_scene_instance = MagicMock()
        mock_planes_scene_instance = MagicMock()
        mock_create_rebars.return_value = mock_rebars_scene_instance
        mock_create_axes.return_value = mock_axes_scene_instance
        mock_create_section_planes.return_value = mock_planes_scene_instance

        params = Munch(
            {
                "bridge_segments_array": [
                    self._create_mock_bridge_segment_param(l=10, bz1=1, bz2=2, bz3=1),
                    self._create_mock_bridge_segment_param(l=12, bz1=1.2, bz2=2.2, bz3=1.2),
                ],
                "model_settings": Munch({"bridge_layout": Munch({"num_longitudinal_segments": 2}), "materials": Munch({"main_material": "C30/37"})}),
                "input": Munch({"dimensions": Munch({"toggle_sections": True})}),
            }
        )

        # Act
        create_3d_model(params, axes=True, section_planes=True)

        # Assertions
        # Verify that create_box was called (3 times for 3 zones)
        assert mock_create_box.call_count == 3

        # Verify that create_rebars was called
        mock_create_rebars.assert_called_once_with(params, color=[0, 0, 0, 255])

        # Verify that create_axes was called (axes=True)
        mock_create_axes.assert_called_once()

        # Verify that create_section_planes was called (section_planes=True and toggle_sections=True)
        mock_create_section_planes.assert_called_once_with(params)


if __name__ == "__main__":
    unittest.main()
