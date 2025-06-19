"""
Test module for longitudinal section geometry functionality.

This module contains tests for creating longitudinal section views and related geometry operations.
"""

import math
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import plotly.graph_objects as go
import trimesh
from munch import Munch  # type: ignore[import-untyped]

from src.geometry.longitudinal_section import create_longitudinal_section

# We'll need to mock functions from model_creator and trimesh


class TestLongitudinalSection(unittest.TestCase):
    """Test cases for longitudinal section geometry creation."""

    def _create_mock_segment_data(  # noqa: PLR0913
        self,
        length: float = 10.0,
        bz1: float = 2.0,
        bz2: float = 3.0,
        bz3: float = 2.5,
        dz: float = 0.5,
        dz_2: float = 0.6,
    ) -> Munch:
        return Munch(
            {
                "l": length,  # Keep 'l' for the data structure but use 'length' as parameter name
                "bz1": bz1,
                "bz2": bz2,
                "bz3": bz3,
                "dz": dz,
                "dz_2": dz_2,
            }
        )

    def _create_default_params(self, num_segments: int = 1, section_loc_y: float = 0.0) -> Munch:
        segments = [self._create_mock_segment_data(length=10 + i, dz=0.5 + i * 0.1, dz_2=0.6 + i * 0.1) for i in range(num_segments)]
        return Munch(
            {
                "bridge_segments_array": segments,
                "input": Munch({"dimensions": Munch({"longitudinal_section_loc": Munch({"y": section_loc_y})})}),
            }
        )

    @patch("src.geometry.longitudinal_section.create_3d_model")
    @patch("src.geometry.longitudinal_section.trimesh")  # Patch the whole trimesh module used in longitudinal_section
    @patch("src.geometry.longitudinal_section.create_cross_section")
    def test_create_longitudinal_section_basic_flow(
        self, mock_create_cross_section: MagicMock, mock_trimesh_module: MagicMock, mock_create_3d_model: MagicMock
    ) -> None:
        """Test the basic flow, mock calls, and some output aspects."""
        params = self._create_default_params(num_segments=2, section_loc_y=1.0)
        section_loc_y_val = 1.0

        # --- Mock create_3d_model ---
        mock_3d_scene = MagicMock()
        mock_3d_geometry_collection = MagicMock()  # Simulate scene.geometry
        mock_3d_geometry_collection.values.return_value = [MagicMock(spec=trimesh.Trimesh)]  # Simulate list of meshes
        mock_3d_scene.geometry = mock_3d_geometry_collection
        mock_create_3d_model.return_value = mock_3d_scene

        # --- Mock trimesh.util.concatenate (first call for 3D) ---
        mock_combined_3d_mesh = MagicMock(spec=trimesh.Trimesh)
        # We need to configure the return value of mock_trimesh_module.util.concatenate
        # It will be called twice. The first time for the 3D model, second for 2D.

        # --- Mock create_cross_section ---
        mock_2d_scene = MagicMock()  # This is what create_cross_section returns
        mock_2d_geometry_collection = MagicMock()
        mock_2d_geometry_collection.values.return_value = [MagicMock(spec=trimesh.Trimesh)]
        mock_2d_scene.geometry = mock_2d_geometry_collection
        mock_create_cross_section.return_value = mock_2d_scene

        # --- Mock trimesh.util.concatenate (second call for 2D) ---
        mock_combined_2d_mesh = MagicMock(spec=trimesh.Trimesh)
        # Mock its vertices and entities as the function uses these directly
        mock_combined_2d_mesh.vertices = np.array(
            [
                [0, 0, 0],
                [10, 0, 0],  # Entity 1 (bottom line segment 1)
                [0, 0, 0.5],
                [10, 0, 0.5],  # Entity 2 (top line segment 1)
                [10, 0, 0],
                [21, 0, 0],  # Entity 3 (bottom line segment 2, l=11)
                [10, 0, 0.6],
                [21, 0, 0.6],  # Entity 4 (top line segment 2, dz=0.6)
            ]
        )
        # Mock entities (Path2D or Path3D objects typically)
        # For simplicity, mock them as objects with a 'points' attribute (list of vertex indices)
        mock_entity1 = MagicMock()
        mock_entity1.points = [0, 1]
        mock_entity2 = MagicMock()
        mock_entity2.points = [2, 3]
        mock_entity3 = MagicMock()
        mock_entity3.points = [4, 5]
        mock_entity4 = MagicMock()
        mock_entity4.points = [6, 7]
        mock_combined_2d_mesh.entities = [mock_entity1, mock_entity2, mock_entity3, mock_entity4]

        # Set up side_effect for concatenate to return different meshes on subsequent calls
        mock_trimesh_module.util.concatenate.side_effect = [mock_combined_3d_mesh, mock_combined_2d_mesh]

        # --- Act ---
        fig = create_longitudinal_section(params, section_loc_y_val)

        # --- Assertions ---
        # Check mock calls
        mock_create_3d_model.assert_called_once_with(params, axes=False)
        assert mock_trimesh_module.util.concatenate.call_count == 2
        mock_trimesh_module.util.concatenate.assert_any_call(mock_3d_geometry_collection.values())

        expected_plane_origin = [0, section_loc_y_val, 0]
        expected_plane_normal = [0, 1, 0]
        mock_create_cross_section.assert_called_once_with(mock_combined_3d_mesh, expected_plane_origin, expected_plane_normal, axes=False)
        mock_trimesh_module.util.concatenate.assert_any_call(mock_2d_geometry_collection.values())

        # Check figure data (traces from entities)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == len(mock_combined_2d_mesh.entities)  # One trace per entity
        # Example check for the first trace (entity1)
        trace0 = fig.data[0]
        assert list(trace0.x) == [mock_combined_2d_mesh.vertices[0][0], mock_combined_2d_mesh.vertices[1][0]]  # x-coords of points 0,1
        assert list(trace0.y) == [mock_combined_2d_mesh.vertices[0][2], mock_combined_2d_mesh.vertices[1][2]]  # z-coords of points 0,1 (y in plot)
        assert trace0.line.color == "black"

        # Check annotations (complex part, needs more detailed setup for params and expected values)
        # For now, check that some annotations are present
        assert len(fig.layout.annotations) > 0

        # Check layout
        assert fig.layout.title.text == "Langsdoorsnede (Longitudinal Section)"
        assert fig.layout.xaxis.title.text == "X-as - Lengte [m]"
        assert fig.layout.yaxis.title.text == "Z-as - Hoogte [m]"
        assert fig.layout.yaxis.scaleanchor == "x"
        assert fig.layout.yaxis.scaleratio == 1
        assert not fig.layout.showlegend

    @patch("src.geometry.longitudinal_section.create_3d_model")
    @patch("src.geometry.longitudinal_section.trimesh")
    @patch("src.geometry.longitudinal_section.create_cross_section")
    def test_create_longitudinal_section_annotations_detailed(
        self, mock_create_cross_section: MagicMock, mock_trimesh_module: MagicMock, mock_create_3d_model: MagicMock
    ) -> None:
        """Test annotation creation in detail."""
        # --- Setup Params ---
        # Segment 1: l=10, bz2=4, dz=0.5, dz_2=0.8
        # Segment 2: l=12, bz2=4, dz=0.6, dz_2=0.9
        # Section loc will be 0, which is within bz2 of segment 1 (zone 2)
        params = Munch(
            {
                "bridge_segments_array": [
                    self._create_mock_segment_data(length=10, bz1=2, bz2=4, bz3=2, dz=0.5, dz_2=0.8),
                    self._create_mock_segment_data(length=12, bz1=2, bz2=4, bz3=2, dz=0.6, dz_2=0.9),
                ]
            }
        )
        section_loc_y_val = 0.0  # For zone_nr calculation

        # --- Mocks (similar to basic_flow, but focus on 2D mesh output for annotations) ---
        mock_create_3d_model.return_value = MagicMock()  # Simplified, as its output is just passed through
        mock_combined_3d_mesh = MagicMock(spec=trimesh.Trimesh)

        mock_2d_scene = MagicMock()
        mock_2d_geometry_collection = MagicMock()
        mock_2d_geometry_collection.values.return_value = [MagicMock(spec=trimesh.Trimesh)]
        mock_2d_scene.geometry = mock_2d_geometry_collection
        mock_create_cross_section.return_value = mock_2d_scene

        mock_combined_2d_mesh = MagicMock(spec=trimesh.Trimesh)
        # vertices: x, y(ignored), z(becomes y in plot)
        # For annotations, we mostly care about all_x and all_z ranges, and specific D-point x values
        # And the max z for D-label y-positioning.
        mock_combined_2d_mesh.vertices = np.array(
            [
                [0, 0, -0.5],
                [10, 0, -0.5],  # Seg1 bottom (indices 0, 1)
                [0, 0, 0.0],
                [10, 0, 0.0],  # Seg1 top (indices 2, 3) (dz=0.5, so top is at 0 if bottom is -0.5)
                [10, 0, -0.6],
                [22, 0, -0.6],  # Seg2 bottom (indices 4, 5) (l_cumulative=10, l=12 -> 22)
                [10, 0, 0.0],
                [22, 0, 0.0],  # Seg2 top (indices 6, 7) (dz=0.6, so top is at 0 if bottom is -0.6)
            ]
        )
        # Define entities to cover all mock vertices to ensure SUT processes them for all_z
        mock_entity_s1_bottom = MagicMock()
        mock_entity_s1_bottom.points = [0, 1]
        mock_entity_s1_top = MagicMock()
        mock_entity_s1_top.points = [2, 3]
        mock_entity_s2_bottom = MagicMock()
        mock_entity_s2_bottom.points = [4, 5]
        mock_entity_s2_top = MagicMock()
        mock_entity_s2_top.points = [6, 7]
        mock_combined_2d_mesh.entities = [mock_entity_s1_bottom, mock_entity_s1_top, mock_entity_s2_bottom, mock_entity_s2_top]
        mock_trimesh_module.util.concatenate.side_effect = [mock_combined_3d_mesh, mock_combined_2d_mesh]

        # --- Act ---
        fig = create_longitudinal_section(params, section_loc_y_val)

        # --- Assert Annotations ---
        annotations = fig.layout.annotations
        # Expected values from params
        segments = params.bridge_segments_array
        l_values = [s.l for s in segments]
        l_cumulative = np.cumsum(l_values).tolist()

        # Calculate min_z_plot and max_z_plot based on the entities the SUT will process
        sut_processed_z_coords = [
            mock_combined_2d_mesh.vertices[ent_idx][2] for entity in mock_combined_2d_mesh.entities for ent_idx in entity.points
        ]

        max_z_plot = max(sut_processed_z_coords) if sut_processed_z_coords else 0.0  # Should be 0.0
        min_z_plot = min(sut_processed_z_coords) if sut_processed_z_coords else 0.0  # Should be -0.6

        # Heights based on logic in SUT
        # SUT's max(all_z) will be 0.0, so this branch is taken:
        h_values_output = [seg.dz for seg in segments]
        h_center_y_calc = [-h / 2 for h in h_values_output]

        # 1. D-labels (Cross-section labels)
        # Expected: D-1 at x=10, D-2 at x=22
        d_labels_texts = {f"<b>D-{i + 1}</b>": l_cum for i, l_cum in enumerate(l_cumulative)}
        found_d_labels = 0
        for ann in annotations:
            if ann.text in d_labels_texts:
                assert ann.x == d_labels_texts[ann.text]
                assert ann.y == max_z_plot + 0.5
                assert ann.font == go.layout.Annotation(font={"size": 15, "color": "black"}).font
                found_d_labels += 1
        assert found_d_labels == len(segments), "Incorrect number of D-labels"

        # 2. Zone labels
        # zone_nr = 2 (since section_loc_y_val = 0 is between -bz2/2 and bz2/2 of segment 0)
        # Expected: Z2-1 at x = 10 + 12/2 = 16 (center of segment 2, which is index 1)
        # y = h_center_y_calc[1] = -segments[1].dz / 2 = -0.6 / 2 = -0.3
        expected_zone_label_text = "<b>Z2-1</b>"
        ann_z2_1 = next((a for a in annotations if a.text == expected_zone_label_text), None)
        assert ann_z2_1 is not None, f"Zone label {expected_zone_label_text} not found"
        if ann_z2_1:
            assert ann_z2_1.x == l_cumulative[0] + l_values[1] / 2  # x-center of 2nd segment
            assert ann_z2_1.y == h_center_y_calc[1]

        # 3. Length dimensions
        # For segment 2 (index 1): l = 12, x_center = 16
        # SUT y = min(all_z) - 1.0. With corrected all_z, min(all_z) = -0.6. So y = -1.6
        expected_len_text_s2 = f"<b>l = {segments[1].l}m</b>"
        ann_len_s2 = next((a for a in annotations if a.text == expected_len_text_s2), None)
        assert ann_len_s2 is not None, f"Length annotation {expected_len_text_s2} not found"
        if ann_len_s2:
            assert ann_len_s2.x == l_cumulative[0] + l_values[1] / 2
            assert math.isclose(ann_len_s2.y, min_z_plot - 1.0)  # Uses corrected min_z_plot
            assert ann_len_s2.font.color == "red"

        # 4. Height dimensions
        # Seg 1 (idx 0): h=0.5, x=10-0.5=9.5, y = h_center_y_calc[0] = -0.25
        # Seg 2 (idx 1): h=0.6, x=22-0.5=21.5, y = h_center_y_calc[1] = -0.3
        expected_h_text_s1 = f"<b>h = {segments[0].dz}m</b>"
        ann_h_s1 = next((a for a in annotations if a.text == expected_h_text_s1), None)
        assert ann_h_s1 is not None, f"Height annotation {expected_h_text_s1} not found"
        if ann_h_s1:
            assert ann_h_s1.x == l_cumulative[0] - 0.5
            assert ann_h_s1.y == h_center_y_calc[0]
            assert ann_h_s1.font.color == "blue"
            assert ann_h_s1.textangle == -90

        expected_h_text_s2 = f"<b>h = {segments[1].dz}m</b>"
        ann_h_s2 = next((a for a in annotations if a.text == expected_h_text_s2), None)
        assert ann_h_s2 is not None, f"Height annotation {expected_h_text_s2} not found"
        if ann_h_s2:
            assert ann_h_s2.x == l_cumulative[1] - 0.5
            assert ann_h_s2.y == h_center_y_calc[1]


if __name__ == "__main__":
    unittest.main()
