"""
Test module for horizontal section geometry functionality.

This module contains tests for creating horizontal section views and related geometry operations.
"""

import math
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import plotly.graph_objects as go
import trimesh  # Likely needed for mocks or type hints
from munch import Munch  # type: ignore[import-untyped]

from src.geometry.horizontal_section import create_horizontal_section_annotations, create_horizontal_section_view

# model_creator functions (create_3d_model, create_cross_section) will be mocked from their original module
# trimesh will be mocked where needed


class TestHorizontalSection(unittest.TestCase):
    """Test cases for horizontal section geometry creation."""

    def _create_mock_segment_param(  # noqa: PLR0913
        self,
        length: float = 10.0,
        bz1: float = 2.0,
        bz2: float = 3.0,
        bz3: float = 2.5,
        dz: float = 0.5,
        dz_2: float = 0.6,
    ) -> Munch:
        return Munch({"l": length, "bz1": bz1, "bz2": bz2, "bz3": bz3, "dz": dz, "dz_2": dz_2})

    def _create_default_params_for_annotations(self, num_segments: int = 1, horizontal_section_loc: float = -1.0) -> Munch:
        # horizontal_section_loc < 0 means all zones (1,2,3) are considered for annotations
        # horizontal_section_loc >= 0 means only_zone2 = True
        segments = [
            self._create_mock_segment_param(length=10.0 + i * 5, bz1=1.0 + i * 0.1, bz2=2.0 + i * 0.1, bz3=1.0 + i * 0.1) for i in range(num_segments)
        ]

        return Munch({"bridge_segments_array": segments, "input": Munch({"dimensions": Munch({"horizontal_section_loc": horizontal_section_loc})})})

    def test_create_horizontal_section_annotations_all_zones(self) -> None:
        """Test annotations when all zones (1,2,3) should be present."""
        params = self._create_default_params_for_annotations(num_segments=2, horizontal_section_loc=-1.0)  # only_zone2 = False
        all_y_mock = [-2.0, 0, 2.0]  # Mock y-range for min/max calculations

        annotations = create_horizontal_section_annotations(params, all_y_mock)

        # Calculate expected annotation counts for 2 segments
        num_segments = len(params.bridge_segments_array)
        num_segment_parts = num_segments - 1 if num_segments > 1 else 1  # Parts between D-points

        expected_d_labels = num_segments  # D1, D2
        expected_z_labels = 3 * num_segment_parts  # Z1, Z2, Z3 for each segment part
        expected_len_dims = num_segment_parts  # Length dimensions for segment parts
        expected_width_dims = 3 * num_segments  # bz1, bz2, bz3 for each D-point
        total_expected_annotations = expected_d_labels + expected_z_labels + expected_len_dims + expected_width_dims

        assert len(annotations) == total_expected_annotations

        # Verify key annotations are present and positioned correctly
        seg0 = params.bridge_segments_array[0]

        # Calculate D-point x-coordinates (cumulative lengths)
        d_point_x_coords = []
        current_sum = 0.0
        for k_seg in range(num_segments):
            current_sum += params.bridge_segments_array[k_seg].l
            d_point_x_coords.append(current_sum)

        # Verify D1 label
        d1_label = next(ann for ann in annotations if ann.text == "<b>D-1</b>")
        assert math.isclose(d1_label.x, d_point_x_coords[0])
        assert math.isclose(d1_label.y, max(all_y_mock) + 0.5)

        # Verify D2 label
        d2_label = next(ann for ann in annotations if ann.text == "<b>D-2</b>")
        assert math.isclose(d2_label.x, d_point_x_coords[1])
        assert math.isclose(d2_label.y, max(all_y_mock) + 0.5)

        # Verify zone center calculations for segment parts
        l_values = [p.l for p in params.bridge_segments_array]
        zone_center_x_actual = [d_point_x_coords[0] + l_values[1] / 2]  # Center of segment between D1 and D2

        # Verify Z1-1 label (Zone 1 of first segment part)
        z1_1_label = next(ann for ann in annotations if ann.text == "<b>Z1-1</b>")
        assert math.isclose(z1_1_label.x, zone_center_x_actual[0])
        assert math.isclose(z1_1_label.y, seg0.bz2 / 2 + seg0.bz1 / 2)

        # Verify length dimension for segment part
        len_label = next(ann for ann in annotations if f"l = {l_values[1]}m" in ann.text)
        assert math.isclose(len_label.x, zone_center_x_actual[0])

        # Verify width annotation for bz1 at D1
        width_bz1_d1 = next(ann for ann in annotations if f"b = {seg0.bz1}m" in ann.text and ann.y == (seg0.bz2 / 2 + seg0.bz1 / 2))
        assert math.isclose(width_bz1_d1.x, d_point_x_coords[0] - 1)

    def test_create_horizontal_section_annotations_only_zone2(self) -> None:
        """Test annotations when only_zone2 is True."""
        params = self._create_default_params_for_annotations(num_segments=1, horizontal_section_loc=0.5)  # only_zone2 = True
        all_y_mock = [-1.0, 0, 1.0]
        annotations = create_horizontal_section_annotations(params, all_y_mock)

        # Calculate expected counts for single segment with only zone2
        num_segments = len(params.bridge_segments_array)
        expected_d_labels = num_segments  # D1
        expected_z_labels = 0  # No segment parts between D-points with single segment
        expected_len_dims = 0  # No segment parts to measure
        expected_width_dims = 1 * num_segments  # Only bz2 for D1
        total_expected_annotations = expected_d_labels + expected_z_labels + expected_len_dims + expected_width_dims

        assert len(annotations) == total_expected_annotations

        # Verify only zone2 annotations are present
        assert not any("Z1-" in ann.text for ann in annotations)
        assert not any("Z3-" in ann.text for ann in annotations)
        assert not any("Z2-" in ann.text for ann in annotations)  # No Z2 labels due to single segment

        # Verify only bz2 width annotations are present
        seg0 = params.bridge_segments_array[0]
        assert any(f"b = {seg0.bz2}m" in ann.text for ann in annotations)
        assert not any(f"b = {seg0.bz1}m" in ann.text for ann in annotations)
        assert not any(f"b = {seg0.bz3}m" in ann.text for ann in annotations)

    @patch("src.geometry.horizontal_section.create_3d_model")
    @patch("src.geometry.horizontal_section.trimesh")  # Patch trimesh module used in horizontal_section
    @patch("src.geometry.horizontal_section.create_cross_section")  # This is from model_creator
    @patch("src.geometry.horizontal_section.create_horizontal_section_annotations")
    def test_create_horizontal_section_view_basic_flow(
        self,
        mock_create_horizontal_annotations: MagicMock,
        mock_model_creator_create_cross_section: MagicMock,
        mock_trimesh_module: MagicMock,
        mock_create_3d_model: MagicMock,
    ) -> None:
        """Test basic flow of create_horizontal_section_view with mocks."""
        params = Munch(
            {
                "bridge_segments_array": [  # Minimal data for create_3d_model mock
                    self._create_mock_segment_param(length=10)
                ],
                "input": Munch({"dimensions": Munch({"horizontal_section_loc": 0.5})}),  # For annotations call
            }
        )
        section_loc_z_val = 0.5

        # Mock create_3d_model
        mock_3d_scene = MagicMock()
        mock_3d_geometry_collection = MagicMock()
        mock_3d_geometry_collection.values.return_value = [MagicMock(spec=trimesh.Trimesh)]
        mock_3d_scene.geometry = mock_3d_geometry_collection
        mock_create_3d_model.return_value = mock_3d_scene

        # Mock trimesh.util.concatenate (call 1 for 3D)
        mock_combined_3d_mesh = MagicMock(spec=trimesh.Trimesh)

        # Mock model_creator.create_cross_section
        mock_2d_scene_from_cs = MagicMock(spec=trimesh.Scene)
        mock_2d_geometry_collection_cs = MagicMock()
        mock_2d_geometry_collection_cs.values.return_value = [MagicMock(spec=trimesh.Trimesh)]
        mock_2d_scene_from_cs.geometry = mock_2d_geometry_collection_cs
        mock_model_creator_create_cross_section.return_value = mock_2d_scene_from_cs

        # Mock trimesh.util.concatenate (call 2 for 2D)
        mock_combined_2d_mesh = MagicMock(spec=trimesh.Trimesh)
        mock_combined_2d_mesh.vertices = np.array([[0, 0, 0], [1, 1, 0], [1, 0, 0]])  # x, y, (z ignored for 2d plot)
        mock_entity1 = MagicMock()
        mock_entity1.points = [0, 1, 2]
        mock_combined_2d_mesh.entities = [mock_entity1]
        mock_trimesh_module.util.concatenate.side_effect = [mock_combined_3d_mesh, mock_combined_2d_mesh]

        # Mock create_horizontal_section_annotations
        mock_annotation_list = [go.layout.Annotation(text="Mock Annotation")]
        mock_create_horizontal_annotations.return_value = mock_annotation_list

        # Act
        fig = create_horizontal_section_view(params, section_loc_z_val)

        # Assertions
        mock_create_3d_model.assert_called_once_with(params, axes=False)
        assert mock_trimesh_module.util.concatenate.call_count == 2
        mock_trimesh_module.util.concatenate.assert_any_call(mock_3d_geometry_collection.values())

        expected_plane_origin = [0, 0, section_loc_z_val]
        expected_plane_normal = [0, 0, 1]
        mock_model_creator_create_cross_section.assert_called_once_with(
            mock_combined_3d_mesh, expected_plane_origin, expected_plane_normal, axes=False
        )
        mock_trimesh_module.util.concatenate.assert_any_call(mock_2d_geometry_collection_cs.values())

        # Check traces from entities (plot uses x and y from vertices array)
        assert len(fig.data) == 1  # From mock_combined_2d_mesh.entities
        trace0 = fig.data[0]
        assert list(trace0.x) == [0, 1, 1]  # Vertices[points][0]
        assert list(trace0.y) == [0, 1, 0]  # Vertices[points][1]
        assert trace0.line.color == "black"

        # Check call to annotation function
        all_y_from_mock_mesh = [0, 1, 0]  # vertices[:, 1]
        mock_create_horizontal_annotations.assert_called_once_with(params, all_y_from_mock_mesh)
        assert fig.layout.annotations == tuple(mock_annotation_list)

        # Check layout
        assert fig.layout.title.text == "Horizontale doorsnede (Horizontal Section)"
        assert fig.layout.xaxis.title.text == "X-as - Lengte [m]"
        assert fig.layout.yaxis.title.text == "Y-as - Breedte [m]"
        assert fig.layout.yaxis.scaleanchor == "x"
        assert fig.layout.yaxis.scaleratio == 1
        assert not fig.layout.showlegend


if __name__ == "__main__":
    unittest.main()
