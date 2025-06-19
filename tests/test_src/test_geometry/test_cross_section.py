"""
Test module for cross-section geometry functionality.

This module contains tests for creating cross-section views and related geometry operations.
"""

import math
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import plotly.graph_objects as go
import trimesh
from munch import Munch  # type: ignore[import-untyped]

from src.geometry.cross_section import create_cross_section_annotations, create_cross_section_view

# Remove the specific module import if it's no longer needed for patch.object


# Helper to create a default segment for params
def _create_segment_data(  # noqa: PLR0913
    length: float = 10.0,
    bz1: float = 2.0,
    bz2: float = 3.0,
    bz3: float = 2.5,
    dz: float = 0.5,
    dz_2: float = 0.6,
) -> Munch:
    """Create test segment data with default values."""
    return Munch(
        {
            "l": length,  # Keep 'l' for data structure compatibility
            "bz1": bz1,
            "bz2": bz2,
            "bz3": bz3,
            "dz": dz,
            "dz_2": dz_2,
        }
    )


class TestCreateCrossSectionAnnotations(unittest.TestCase):
    """Test cases for cross-section annotation creation."""

    def test_empty_segments_array_returns_empty_list(self) -> None:
        """Test create_cross_section_annotations returns empty list for empty segments."""
        # Arrange
        params = Munch({"bridge_segments_array": [], "input": Munch({"dimensions": Munch({"cross_section_loc": 5.0})})})
        all_z = [-1.0, 0.0]

        # Act
        annotations = create_cross_section_annotations(params, all_z)

        # Assert
        assert annotations == []

    def test_segment_index_determination_single_segment(self) -> None:
        """Test correct segment index determination with single segment."""
        # Arrange
        segment1 = _create_segment_data(length=20.0)
        params = Munch({"bridge_segments_array": [segment1], "input": Munch({"dimensions": Munch({"cross_section_loc": 10.0})})})
        all_z = [-0.5, 0.5]

        # Act: We are primarily testing the internal segment_index calculation implicitly
        # by checking the annotation text which includes the segment_index.
        annotations = create_cross_section_annotations(params, all_z)

        # Assert
        assert len(annotations) == 9  # 3 zone + 3 width + 3 height
        # Check one zone label for correct segment index (should be 0)
        zone1_label = next(a for a in annotations if a.x == (segment1.bz2 / 2 + segment1.bz1 / 2) and "Z1" in a.text)
        assert "Z1-0" in zone1_label.text

    def test_segment_index_determination_multiple_segments(self) -> None:
        """Test segment index determination with multiple segments."""
        # Arrange
        segment1 = _create_segment_data(length=10.0, bz1=2, bz2=3, bz3=2, dz=0.5, dz_2=0.6)
        segment2 = _create_segment_data(length=15.0, bz1=2.5, bz2=3.5, bz3=2.5, dz=0.55, dz_2=0.65)
        params = Munch(
            {
                "bridge_segments_array": [segment1, segment2],
                "input": Munch(dimensions=Munch(cross_section_loc=12.0)),  # Should be in segment 2 (index 1)
            }
        )
        all_z = [-1.0, 1.0]

        # Act
        annotations = create_cross_section_annotations(params, all_z)

        # Assert
        assert len(annotations) == 9
        # Check zone label for segment index 1
        # segment2.bz2 / 2 + segment2.bz1 / 2
        expected_x_for_z1_s1 = segment2.bz2 / 2 + segment2.bz1 / 2
        zone1_label_s1 = next(a for a in annotations if a.x == expected_x_for_z1_s1 and "Z1" in a.text)
        assert "Z1-1" in zone1_label_s1.text
        # Check width annotation for segment 1 data
        width_z1_s1 = next(a for a in annotations if a.x == expected_x_for_z1_s1 and "b =" in a.text)
        assert f"b = {segment2.bz1}m" in width_z1_s1.text

    def test_segment_index_at_boundary(self) -> None:
        """Test segment index determination when location is at segment boundary."""
        # Arrange
        segment1 = _create_segment_data(length=10.0)
        segment2 = _create_segment_data(length=10.0)
        params = Munch(
            {
                "bridge_segments_array": [segment1, segment2],
                "input": Munch(dimensions=Munch(cross_section_loc=10.0)),  # Exactly at end of segment1
            }
        )
        all_z = [-1.0, 0.0]
        # Act
        annotations = create_cross_section_annotations(params, all_z)
        # Assert: Function logic (<= cumulative_length) means it picks the first segment whose end includes the point.
        # So, for loc = 10.0, and l_values_cumulative = [10.0, 20.0], it picks segment_index = 0.
        zone1_label = next(a for a in annotations if "Z1" in a.text)
        assert "Z1-0" in zone1_label.text

    def test_segment_index_loc_beyond_last_segment(self) -> None:
        """Test segment index determination when location is beyond the last segment."""
        # Arrange
        segment1 = _create_segment_data(length=10.0)
        params = Munch(
            {
                "bridge_segments_array": [segment1],
                "input": Munch(dimensions=Munch(cross_section_loc=100.0)),  # Way beyond
            }
        )
        all_z = [-1.0, 0.0]
        # Act
        annotations = create_cross_section_annotations(params, all_z)
        # Assert: Should still pick the last available segment_index (0 in this case)
        zone1_label = next(a for a in annotations if "Z1" in a.text)
        assert "Z1-0" in zone1_label.text

    def test_basic_annotation_properties_zone_labels(self) -> None:
        """Test basic annotation properties for zone labels in cross section."""
        # Arrange
        seg_data = _create_segment_data(length=10, bz1=2, bz2=4, bz3=2, dz=0.5, dz_2=0.6)
        params = Munch({"bridge_segments_array": [seg_data], "input": Munch(dimensions=Munch(cross_section_loc=5.0))})
        all_z = [-1.0, 0.0]
        # Act
        annotations = create_cross_section_annotations(params, all_z)
        # Assert
        # Zone 1 Label (Z1-0)
        ann_z1 = next(a for a in annotations if a.text == "<b>Z1-0</b>")
        assert math.isclose(ann_z1.x, seg_data.bz2 / 2 + seg_data.bz1 / 2)  # (4/2 + 2/2) = 3
        assert math.isclose(ann_z1.y, -seg_data.dz / 2)  # -0.5 / 2 = -0.25
        assert ann_z1.font.size == 12
        assert ann_z1.font.color == "black"
        assert ann_z1.xanchor == "center"
        assert ann_z1.yanchor == "middle"
        assert not ann_z1.showarrow

        # Zone 2 Label (Z2-0)
        ann_z2 = next(a for a in annotations if a.text == "<b>Z2-0</b>")
        assert math.isclose(ann_z2.x, 0)
        assert math.isclose(ann_z2.y, -seg_data.dz + seg_data.dz_2 / 2)  # -0.5 + 0.6/2 = -0.2

        # Zone 3 Label (Z3-0)
        ann_z3 = next(a for a in annotations if a.text == "<b>Z3-0</b>")
        assert math.isclose(ann_z3.x, -seg_data.bz2 / 2 - seg_data.bz3 / 2)  # -(4/2) - (2/2) = -3
        assert math.isclose(ann_z3.y, -seg_data.dz / 2)  # -0.25

    def test_basic_annotation_properties_width_labels(self) -> None:
        """Test basic annotation properties for width labels in cross section."""
        # Arrange
        seg_data = _create_segment_data(length=10, bz1=2.2, bz2=3.3, bz3=4.4, dz=0.5, dz_2=0.6)
        params = Munch({"bridge_segments_array": [seg_data], "input": Munch(dimensions=Munch(cross_section_loc=5.0))})
        min_z_val = -2.0
        all_z = [min_z_val, 0.0, 1.0]
        # Act
        annotations = create_cross_section_annotations(params, all_z)
        # Assert
        # Width Zone 1 (bz1)
        ann_w1 = next(a for a in annotations if a.text == f"<b>b = {seg_data.bz1}m</b>")
        assert math.isclose(ann_w1.x, seg_data.bz2 / 2 + seg_data.bz1 / 2)
        assert math.isclose(ann_w1.y, min_z_val - 1.0)
        assert ann_w1.font.color == "green"

        # Width Zone 2 (bz2)
        ann_w2 = next(a for a in annotations if a.text == f"<b>b = {seg_data.bz2}m</b>")
        assert math.isclose(ann_w2.x, 0)
        assert math.isclose(ann_w2.y, min_z_val - 1.0)

        # Width Zone 3 (bz3)
        ann_w3 = next(a for a in annotations if a.text == f"<b>b = {seg_data.bz3}m</b>")
        assert math.isclose(ann_w3.x, -seg_data.bz2 / 2 - seg_data.bz3 / 2)
        assert math.isclose(ann_w3.y, min_z_val - 1.0)

    def test_basic_annotation_properties_height_labels(self) -> None:
        """Test basic annotation properties for height labels in cross section."""
        # Arrange
        seg_data = _create_segment_data(length=10, bz1=2, bz2=4, bz3=2, dz=0.5, dz_2=0.6)
        params = Munch({"bridge_segments_array": [seg_data], "input": Munch(dimensions=Munch(cross_section_loc=5.0))})
        all_z = [-1.0, 0.0]
        # Act
        annotations = create_cross_section_annotations(params, all_z)
        # Assert

        # Expected x locations for height annotations
        expected_x_h1 = seg_data.bz2 / 2
        expected_x_h2 = -seg_data.bz2 / 2
        expected_x_h3 = -seg_data.bz2 / 2 - seg_data.bz3

        # Height Zone 1 (dz)
        ann_h1 = next(a for a in annotations if a.text == f"<b>h = {seg_data.dz}m</b>" and abs(a.x - expected_x_h1) < 1e-9)
        assert math.isclose(ann_h1.x, expected_x_h1)
        assert math.isclose(ann_h1.y, -seg_data.dz / 2)
        assert ann_h1.font.color == "blue"
        assert ann_h1.textangle == -90
        assert ann_h1.xanchor == "right"

        # Height Zone 2 (dz_2)
        ann_h2 = next(a for a in annotations if a.text == f"<b>h = {seg_data.dz_2}m</b>" and abs(a.x - expected_x_h2) < 1e-9)
        assert math.isclose(ann_h2.x, expected_x_h2)
        assert math.isclose(ann_h2.y, -seg_data.dz + seg_data.dz_2 / 2)

        # Height Zone 3 (dz)
        ann_h3 = next(a for a in annotations if a.text == f"<b>h = {seg_data.dz}m</b>" and abs(a.x - expected_x_h3) < 1e-9)
        assert math.isclose(ann_h3.x, expected_x_h3)
        assert math.isclose(ann_h3.y, -seg_data.dz / 2)

    def test_input_params_as_dict(self) -> None:
        """Test that the function handles params as dict (gets converted to Munch internally)."""
        # Test that it handles params as dict (gets converted to Munch internally)
        segment1_dict = {"l": 10.0, "bz1": 2.0, "bz2": 3.0, "bz3": 2.5, "dz": 0.5, "dz_2": 0.6}
        params_dict = {"bridge_segments_array": [segment1_dict], "input": {"dimensions": {"cross_section_loc": 5.0}}}
        all_z = [-0.5, 0.5]
        annotations = create_cross_section_annotations(params_dict, all_z)
        assert len(annotations) == 9
        # Check if one of the calculations is correct, implying Munch conversion worked.
        ann_z1 = next(a for a in annotations if a.text == "<b>Z1-0</b>")
        expected_x_z1 = segment1_dict["bz2"] / 2 + segment1_dict["bz1"] / 2
        assert math.isclose(ann_z1.x, expected_x_z1)


class TestCreateCrossSectionView(unittest.TestCase):
    """Test suite for the `create_cross_section_view` function."""

    def _create_default_params(self, bridge_segments_array: list[Any] | None = None, cross_section_loc: float = 0.0) -> Munch:
        """Helper to create a basic params Munch object."""
        if bridge_segments_array is None:
            bridge_segments_array = [
                _create_segment_data(10, 1, 2, 1, 0.5, 0.3),
                _create_segment_data(15, 1.2, 2.2, 1.2, 0.6, 0.35),
            ]
        return Munch(
            bridge_segments_array=bridge_segments_array,
            input=Munch(dimensions=Munch(cross_section_loc=cross_section_loc)),
            model_settings=Munch(
                bridge_layout=Munch(num_longitudinal_segments=len(bridge_segments_array)),
                materials=Munch(main_material="C30/37"),  # Example, adjust as needed
                # Add other model_settings if create_3d_model depends on them
            ),
        )

    @patch("src.geometry.cross_section.create_3d_model")
    @patch("src.geometry.cross_section.create_cross_section")
    @patch("src.geometry.cross_section.create_cross_section_annotations")
    @patch("src.geometry.cross_section.trimesh")
    def test_create_cross_section_view_basic_functionality(
        self,
        mock_trimesh_module: MagicMock,
        mock_create_annotations: MagicMock,
        mock_create_cross_section_func: MagicMock,
        mock_create_3d_model: MagicMock,
    ) -> None:
        """Test basic functionality of create_cross_section_view."""
        params = self._create_default_params(cross_section_loc=5.0)
        section_loc = 5.0

        # Mock create_3d_model to return a scene with geometry
        mock_3d_scene = MagicMock()
        mock_3d_geometry = MagicMock()
        mock_3d_geometry.values.return_value = [MagicMock(spec=trimesh.Trimesh)]
        mock_3d_scene.geometry = mock_3d_geometry
        mock_create_3d_model.return_value = mock_3d_scene

        # Mock trimesh.util.concatenate for the first call (3D scene)
        mock_combined_mesh = MagicMock(spec=trimesh.Trimesh)
        mock_trimesh_module.util.concatenate.return_value = mock_combined_mesh

        # Mock create_cross_section to return a 2D scene
        mock_2d_scene = MagicMock()
        mock_2d_geometry = MagicMock()
        mock_2d_geometry.values.return_value = [MagicMock(spec=trimesh.Trimesh)]
        mock_2d_scene.geometry = mock_2d_geometry
        mock_create_cross_section_func.return_value = mock_2d_scene

        # Mock the second trimesh.util.concatenate call (2D scene)
        mock_2d_combined_mesh = MagicMock(spec=trimesh.Trimesh)
        # Set up side_effect for multiple concatenate calls
        mock_trimesh_module.util.concatenate.side_effect = [mock_combined_mesh, mock_2d_combined_mesh]

        # Mock the 2D mesh properties
        mock_2d_combined_mesh.vertices = np.array([[0, 0, 0], [1, 0, 1], [0, 1, 1]])
        mock_2d_combined_mesh.entities = [
            MagicMock(points=[0, 1]),
            MagicMock(points=[1, 2]),
        ]

        # Mock annotations
        mock_annotations = [go.layout.Annotation(text="Test Annotation")]
        mock_create_annotations.return_value = mock_annotations

        fig = create_cross_section_view(params, section_loc)

        # Verify function calls
        mock_create_3d_model.assert_called_once_with(params, axes=False)
        mock_trimesh_module.util.concatenate.assert_any_call(list(mock_3d_geometry.values()))

        # Verify create_cross_section was called with correct parameters
        mock_create_cross_section_func.assert_called_once_with(mock_combined_mesh, [section_loc, 0, 0], [1, 0, 0], axes=False)

        # Verify second concatenate call
        assert mock_trimesh_module.util.concatenate.call_count == 2
        mock_trimesh_module.util.concatenate.assert_any_call(list(mock_2d_geometry.values()))

        # Verify annotations were created and added
        mock_create_annotations.assert_called_once()
        args, kwargs = mock_create_annotations.call_args
        assert args[0] == params
        # args[1] should be all_z coordinates

        # Verify the returned figure
        assert isinstance(fig, go.Figure)
        assert fig.layout.annotations == tuple(mock_annotations)
        assert fig.layout.title.text == "Dwarsdoorsnede (Cross Section)"

    @patch("src.geometry.cross_section.create_3d_model")
    @patch("src.geometry.cross_section.create_cross_section")
    @patch("src.geometry.cross_section.create_cross_section_annotations")
    @patch("src.geometry.cross_section.trimesh")
    def test_create_cross_section_view_with_annotations(
        self,
        mock_trimesh_module: MagicMock,
        mock_create_annotations: MagicMock,
        mock_create_cross_section_func: MagicMock,
        mock_create_3d_model: MagicMock,
    ) -> None:
        """Test that annotations are correctly created and added to the figure."""
        params = self._create_default_params(cross_section_loc=10.0)
        section_loc = 10.0

        # Mock create_3d_model
        mock_3d_scene = MagicMock()
        mock_3d_geometry = MagicMock()
        mock_3d_geometry.values.return_value = [MagicMock(spec=trimesh.Trimesh)]
        mock_3d_scene.geometry = mock_3d_geometry
        mock_create_3d_model.return_value = mock_3d_scene

        # Mock trimesh concatenate
        mock_combined_mesh = MagicMock(spec=trimesh.Trimesh)
        mock_2d_combined_mesh = MagicMock(spec=trimesh.Trimesh)
        mock_trimesh_module.util.concatenate.side_effect = [mock_combined_mesh, mock_2d_combined_mesh]

        # Mock create_cross_section
        mock_2d_scene = MagicMock()
        mock_2d_geometry = MagicMock()
        mock_2d_geometry.values.return_value = [MagicMock(spec=trimesh.Trimesh)]
        mock_2d_scene.geometry = mock_2d_geometry
        mock_create_cross_section_func.return_value = mock_2d_scene

        # Mock the 2D mesh with specific Z coordinates for annotation testing
        mock_2d_combined_mesh.vertices = np.array(
            [
                [0, 0, 0.0],  # Point 0: z=0.0
                [1, 1, 1.5],  # Point 1: z=1.5
                [0, 2, 2.0],  # Point 2: z=2.0
            ]
        )
        mock_2d_combined_mesh.entities = [MagicMock(points=[0, 1, 2])]

        # Mock annotations with specific content
        expected_annotations = [
            go.layout.Annotation(text="Zone 1", x=0.5, y=1.0),
            go.layout.Annotation(text="Zone 2", x=1.0, y=1.5),
        ]
        mock_create_annotations.return_value = expected_annotations

        fig = create_cross_section_view(params, section_loc)

        # Verify create_cross_section_annotations was called with correct all_z
        mock_create_annotations.assert_called_once()
        args, kwargs = mock_create_annotations.call_args
        assert args[0] == params

        # Verify all_z contains the Z coordinates from the mesh vertices
        all_z = args[1]
        expected_z_coords = [0.0, 1.5, 2.0]  # Z coordinates from points 0, 1, 2
        assert sorted(all_z) == sorted(expected_z_coords)

        # Verify annotations were added to the figure
        assert fig.layout.annotations == tuple(expected_annotations)

        # Verify the figure structure
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # Should have trace data


if __name__ == "__main__":
    unittest.main()
