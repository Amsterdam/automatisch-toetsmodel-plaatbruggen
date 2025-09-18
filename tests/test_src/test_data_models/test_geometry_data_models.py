"""Tests for geometry data Pydantic models."""

import unittest

import pytest
from pydantic import ValidationError

from src.data_models.geometry_data_models import DPointLabelData, LoadZoneGeometryData


class TestDPointLabelData(unittest.TestCase):
    """Test cases for DPointLabelData Pydantic model."""

    def test_valid_label_creation(self) -> None:
        """Test creating valid D-point label data."""
        label = DPointLabelData(text="D1", x=0.0, y=2.5)

        assert label.text == "D1"
        assert label.x == 0.0
        assert label.y == 2.5

    def test_label_text_validation(self) -> None:
        """Test label text validation."""
        # Valid labels
        valid_labels = ["D1", "D2", "Point1", "A-1", "B_2"]

        for text in valid_labels:
            label = DPointLabelData(text=text, x=0.0, y=2.5)
            assert label.text == text.strip()

        # Empty text
        with pytest.raises(ValidationError) as exc_info:
            DPointLabelData(text="", x=0.0, y=2.5)

        error = exc_info.value
        assert "text" in str(error)
        assert "at least 1 character" in str(error)

        # Whitespace only
        with pytest.raises(ValidationError) as exc_info:
            DPointLabelData(text="   ", x=0.0, y=2.5)

        error = exc_info.value
        assert "text" in str(error)
        assert "whitespace only" in str(error)

        # Invalid characters
        with pytest.raises(ValidationError) as exc_info:
            DPointLabelData(text="D@1", x=0.0, y=2.5)  # @ not allowed

        error = exc_info.value
        assert "text" in str(error)
        assert "letters, numbers, dots, hyphens, and underscores" in str(error)

        # Text too long
        with pytest.raises(ValidationError) as exc_info:
            DPointLabelData(text="VeryLongLabelName", x=0.0, y=2.5)  # Too long

        error = exc_info.value
        assert "text" in str(error)
        assert "at most 10 characters" in str(error)

    def test_coordinate_validation(self) -> None:
        """Test coordinate validation."""
        # Valid coordinates
        label = DPointLabelData(text="D1", x=100.0, y=-50.0)
        assert label.x == 100.0
        assert label.y == -50.0

        # Unrealistic coordinates
        with pytest.raises(ValidationError) as exc_info:
            DPointLabelData(text="D1", x=15000.0, y=2.5)  # X too large

        error = exc_info.value
        assert "x" in str(error)
        assert "unrealistic" in str(error)

        with pytest.raises(ValidationError) as exc_info:
            DPointLabelData(text="D1", x=0.0, y=-15000.0)  # Y too small

        error = exc_info.value
        assert "y" in str(error)
        assert "unrealistic" in str(error)


class TestLoadZoneGeometryData(unittest.TestCase):
    """Test cases for LoadZoneGeometryData Pydantic model."""

    def test_valid_geometry_data_creation(self) -> None:
        """Test creating valid load zone geometry data."""
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 5.0, 10.0],
            y_top_structural_edge_at_d_points=[2.0, 2.5, 3.0],
            total_widths_at_d_points=[12.0, 12.0, 12.0],
            y_bridge_bottom_at_d_points=[1.0, 1.2, 1.4],
            num_defined_d_points=3,
            d_point_label_data=[
                DPointLabelData(text="D1", x=0.0, y=2.0),
                DPointLabelData(text="D2", x=5.0, y=2.5),
                DPointLabelData(text="D3", x=10.0, y=3.0),
            ],
        )

        assert geometry.x_coords_d_points == [0.0, 5.0, 10.0]
        assert geometry.y_top_structural_edge_at_d_points == [2.0, 2.5, 3.0]
        assert geometry.total_widths_at_d_points == [12.0, 12.0, 12.0]
        assert geometry.y_bridge_bottom_at_d_points == [1.0, 1.2, 1.4]
        assert geometry.num_defined_d_points == 3
        assert len(geometry.d_point_label_data) == 3

    def test_empty_geometry_data_valid(self) -> None:
        """Test that empty geometry data is valid."""
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[],
            y_top_structural_edge_at_d_points=[],
            total_widths_at_d_points=[],
            y_bridge_bottom_at_d_points=[],
            num_defined_d_points=0,
            d_point_label_data=[],
        )

        assert geometry.num_defined_d_points == 0
        assert len(geometry.x_coords_d_points) == 0

    def test_x_coords_ascending_validation(self) -> None:
        """Test X coordinates ascending validation."""
        # Valid ascending coordinates
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 5.0, 10.0],  # Ascending
            y_top_structural_edge_at_d_points=[2.0, 2.5, 3.0],
            total_widths_at_d_points=[12.0, 12.0, 12.0],
            y_bridge_bottom_at_d_points=[1.0, 1.2, 1.4],
            num_defined_d_points=3,
            d_point_label_data=[
                DPointLabelData(text="D1", x=0.0, y=2.0),
                DPointLabelData(text="D2", x=5.0, y=2.5),
                DPointLabelData(text="D3", x=10.0, y=3.0),
            ],
        )
        assert geometry.x_coords_d_points == [0.0, 5.0, 10.0]

        # Duplicate coordinates
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneGeometryData(
                x_coords_d_points=[0.0, 5.0, 5.0],  # Duplicate
                y_top_structural_edge_at_d_points=[2.0, 2.5, 3.0],
                total_widths_at_d_points=[12.0, 12.0, 12.0],
                y_bridge_bottom_at_d_points=[1.0, 1.2, 1.4],
                num_defined_d_points=3,
                d_point_label_data=[
                    DPointLabelData(text="D1", x=0.0, y=2.0),
                    DPointLabelData(text="D2", x=5.0, y=2.5),
                    DPointLabelData(text="D3", x=5.0, y=3.0),
                ],
            )

        error = exc_info.value
        assert "x_coords_d_points" in str(error)
        assert "unique" in str(error)

        # Non-ascending coordinates
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneGeometryData(
                x_coords_d_points=[0.0, 10.0, 5.0],  # Not ascending
                y_top_structural_edge_at_d_points=[2.0, 2.5, 3.0],
                total_widths_at_d_points=[12.0, 12.0, 12.0],
                y_bridge_bottom_at_d_points=[1.0, 1.2, 1.4],
                num_defined_d_points=3,
                d_point_label_data=[
                    DPointLabelData(text="D1", x=0.0, y=2.0),
                    DPointLabelData(text="D2", x=10.0, y=2.5),
                    DPointLabelData(text="D3", x=5.0, y=3.0),
                ],
            )

        error = exc_info.value
        assert "x_coords_d_points" in str(error)
        assert "ascending order" in str(error)

    def test_coordinate_length_matching_validation(self) -> None:
        """Test coordinate length matching validation."""
        # Valid matching lengths
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 5.0],
            y_top_structural_edge_at_d_points=[2.0, 2.5],  # Length 2
            total_widths_at_d_points=[12.0, 12.0],  # Length 2
            y_bridge_bottom_at_d_points=[1.0, 1.2],  # Length 2
            num_defined_d_points=2,
            d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0), DPointLabelData(text="D2", x=5.0, y=2.5)],
        )
        assert len(geometry.y_top_structural_edge_at_d_points) == 2

        # Mismatched lengths
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneGeometryData(
                x_coords_d_points=[0.0, 5.0],  # Length 2
                y_top_structural_edge_at_d_points=[2.0],  # Length 1!
                total_widths_at_d_points=[12.0, 12.0],
                y_bridge_bottom_at_d_points=[1.0, 1.2],
                num_defined_d_points=2,
                d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0), DPointLabelData(text="D2", x=5.0, y=2.5)],
            )

        error = exc_info.value
        assert "y_top_structural_edge_at_d_points" in str(error)
        assert "doesn't match x_coords_d_points length" in str(error)

    def test_top_above_bottom_validation(self) -> None:
        """Test top edge above bottom edge validation."""
        # Valid: top above bottom
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 5.0],
            y_top_structural_edge_at_d_points=[2.0, 2.5],  # Above bottom
            total_widths_at_d_points=[12.0, 12.0],
            y_bridge_bottom_at_d_points=[1.0, 1.2],  # Below top
            num_defined_d_points=2,
            d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0), DPointLabelData(text="D2", x=5.0, y=2.5)],
        )
        assert geometry.y_top_structural_edge_at_d_points[0] > geometry.y_bridge_bottom_at_d_points[0]

        # Invalid: top below bottom
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneGeometryData(
                x_coords_d_points=[0.0, 5.0],
                y_top_structural_edge_at_d_points=[1.0, 1.2],  # Below bottom!
                total_widths_at_d_points=[12.0, 12.0],
                y_bridge_bottom_at_d_points=[2.0, 2.5],  # Above top!
                num_defined_d_points=2,
                d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=1.0), DPointLabelData(text="D2", x=5.0, y=1.2)],
            )

        error = exc_info.value
        assert "Top edge coordinate" in str(error)
        assert "below bottom edge coordinate" in str(error)

    def test_width_validation(self) -> None:
        """Test width validation."""
        # Valid widths
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 5.0],
            y_top_structural_edge_at_d_points=[2.0, 2.5],
            total_widths_at_d_points=[12.0, 15.0],  # Positive widths
            y_bridge_bottom_at_d_points=[1.0, 1.2],
            num_defined_d_points=2,
            d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0), DPointLabelData(text="D2", x=5.0, y=2.5)],
        )
        assert geometry.total_widths_at_d_points == [12.0, 15.0]

        # Invalid widths
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneGeometryData(
                x_coords_d_points=[0.0, 5.0],
                y_top_structural_edge_at_d_points=[2.0, 2.5],
                total_widths_at_d_points=[12.0, 0.0],  # Zero width!
                y_bridge_bottom_at_d_points=[1.0, 1.2],
                num_defined_d_points=2,
                d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0), DPointLabelData(text="D2", x=5.0, y=2.5)],
            )

        error = exc_info.value
        assert "total_widths_at_d_points" in str(error)
        assert "must be positive" in str(error)

    def test_d_points_count_validation(self) -> None:
        """Test D-points count validation."""
        # Valid count
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 5.0],  # Length 2
            y_top_structural_edge_at_d_points=[2.0, 2.5],
            total_widths_at_d_points=[12.0, 12.0],
            y_bridge_bottom_at_d_points=[1.0, 1.2],
            num_defined_d_points=2,  # Matches length
            d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0), DPointLabelData(text="D2", x=5.0, y=2.5)],
        )
        assert geometry.num_defined_d_points == 2

        # Invalid count
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneGeometryData(
                x_coords_d_points=[0.0, 5.0],  # Length 2
                y_top_structural_edge_at_d_points=[2.0, 2.5],
                total_widths_at_d_points=[12.0, 12.0],
                y_bridge_bottom_at_d_points=[1.0, 1.2],
                num_defined_d_points=3,  # Doesn't match length!
                d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0), DPointLabelData(text="D2", x=5.0, y=2.5)],
            )

        error = exc_info.value
        assert "num_defined_d_points" in str(error)
        assert "doesn't match actual data length" in str(error)

    def test_label_data_count_validation(self) -> None:
        """Test label data count validation."""
        # Valid count
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 5.0],
            y_top_structural_edge_at_d_points=[2.0, 2.5],
            total_widths_at_d_points=[12.0, 12.0],
            y_bridge_bottom_at_d_points=[1.0, 1.2],
            num_defined_d_points=2,
            d_point_label_data=[
                DPointLabelData(text="D1", x=0.0, y=2.0),
                DPointLabelData(text="D2", x=5.0, y=2.5),
            ],  # Length 2, matches num_defined_d_points
        )
        assert len(geometry.d_point_label_data) == 2

        # Invalid count
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneGeometryData(
                x_coords_d_points=[0.0, 5.0],
                y_top_structural_edge_at_d_points=[2.0, 2.5],
                total_widths_at_d_points=[12.0, 12.0],
                y_bridge_bottom_at_d_points=[1.0, 1.2],
                num_defined_d_points=2,
                d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0)],  # Length 1, doesn't match num_defined_d_points=2
            )

        error = exc_info.value
        assert "Label data count" in str(error)
        assert "doesn't match num_defined_d_points" in str(error)

    def test_coordinate_range_validation(self) -> None:
        """Test coordinate range validation."""
        # Valid coordinates
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[100.0, 200.0],  # Valid range
            y_top_structural_edge_at_d_points=[50.0, 60.0],
            total_widths_at_d_points=[12.0, 12.0],
            y_bridge_bottom_at_d_points=[40.0, 45.0],
            num_defined_d_points=2,
            d_point_label_data=[DPointLabelData(text="D1", x=100.0, y=50.0), DPointLabelData(text="D2", x=200.0, y=60.0)],
        )
        assert geometry.x_coords_d_points == [100.0, 200.0]

        # Unrealistic coordinates
        with pytest.raises(ValidationError) as exc_info:
            LoadZoneGeometryData(
                x_coords_d_points=[2000.0, 3000.0],  # Too large
                y_top_structural_edge_at_d_points=[50.0, 60.0],
                total_widths_at_d_points=[12.0, 12.0],
                y_bridge_bottom_at_d_points=[40.0, 45.0],
                num_defined_d_points=2,
                d_point_label_data=[DPointLabelData(text="D1", x=2000.0, y=50.0), DPointLabelData(text="D2", x=3000.0, y=60.0)],
            )

        error = exc_info.value
        assert "Coordinate 2000.0 at index 0 is unrealistic" in str(error)

    def test_realistic_scenarios(self) -> None:
        """Test realistic bridge geometry scenarios."""
        # Typical bridge with 3 D-points
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0, 25.0, 50.0],  # 50m bridge
            y_top_structural_edge_at_d_points=[2.0, 2.5, 3.0],  # Sloping deck
            total_widths_at_d_points=[12.0, 12.0, 12.0],  # Constant width
            y_bridge_bottom_at_d_points=[1.0, 1.2, 1.4],  # Sloping bottom
            num_defined_d_points=3,
            d_point_label_data=[
                DPointLabelData(text="D1", x=0.0, y=2.0),
                DPointLabelData(text="D2", x=25.0, y=2.5),
                DPointLabelData(text="D3", x=50.0, y=3.0),
            ],
        )

        assert geometry.num_defined_d_points == 3
        assert len(geometry.x_coords_d_points) == 3
        assert geometry.x_coords_d_points[0] < geometry.x_coords_d_points[1] < geometry.x_coords_d_points[2]

        # Single span bridge
        geometry = LoadZoneGeometryData(
            x_coords_d_points=[0.0],
            y_top_structural_edge_at_d_points=[2.0],
            total_widths_at_d_points=[10.0],
            y_bridge_bottom_at_d_points=[1.0],
            num_defined_d_points=1,
            d_point_label_data=[DPointLabelData(text="D1", x=0.0, y=2.0)],
        )

        assert geometry.num_defined_d_points == 1
        assert len(geometry.d_point_label_data) == 1
