"""
Test module for common plotting utilities.

This module contains tests for creating plotly annotations, structural polygon traces,
and bridge outline traces used across the application.
"""

import unittest
from typing import Any

import plotly.graph_objects as go

from src.common.plot_utils import create_bridge_outline_traces, create_structural_polygons_traces, create_text_annotations_from_data


class TestPlotUtilsCreateTextAnnotations(unittest.TestCase):
    """Test cases for create_text_annotations function."""

    def test_empty_label_data(self) -> None:
        """Test create_text_annotations with empty input data."""
        # Arrange
        label_data: list[dict[str, Any]] = []
        # Act
        annotations = create_text_annotations_from_data(label_data)
        # Assert
        assert len(annotations) == 0
        assert isinstance(annotations, list)

    def test_single_annotation_defaults(self) -> None:
        """Test create_text_annotations with single annotation using default styling."""
        # Arrange
        label_data = [{"text": "Test1", "x": 10, "y": 20}]
        # Act
        annotations = create_text_annotations_from_data(label_data)
        # Assert
        assert len(annotations) == 1
        ann = annotations[0]
        assert isinstance(ann, go.layout.Annotation)
        assert ann.text == "<b>Test1</b>"
        assert ann.x == 10
        assert ann.y == 20
        assert ann.font.size == 12
        assert ann.font.color == "black"
        assert ann.xanchor == "center"
        assert ann.yanchor == "bottom"
        assert not ann.showarrow

    def test_multiple_annotations(self) -> None:
        """Test create_text_annotations with multiple annotations."""
        # Arrange
        label_data = [
            {"text": "TestA", "x": 1, "y": 2},
            {"text": "TestB", "x": 3, "y": 4},
        ]
        # Act
        annotations = create_text_annotations_from_data(label_data)
        # Assert
        assert len(annotations) == 2
        assert annotations[0].text == "<b>TestA</b>"
        assert annotations[0].x == 1
        assert annotations[1].text == "<b>TestB</b>"
        assert annotations[1].y == 4

    def test_overridden_optional_arguments(self) -> None:
        """Test create_text_annotations with overridden optional styling arguments."""
        # Arrange
        label_data = [{"text": "Override", "x": 5, "y": 15}]
        font_size = 16
        font_color = "red"
        xanchor = "left"
        yanchor = "top"
        showarrow = True
        text_prefix = "<i>"
        text_suffix = "</i>"
        # Act
        annotations = create_text_annotations_from_data(
            label_data,
            font_size=font_size,
            font_color=font_color,
            xanchor=xanchor,
            yanchor=yanchor,
            showarrow=showarrow,
            text_prefix=text_prefix,
            text_suffix=text_suffix,
        )
        # Assert
        assert len(annotations) == 1
        ann = annotations[0]
        assert ann.text == "<i>Override</i>"
        assert ann.font.size == font_size
        assert ann.font.color == font_color
        assert ann.xanchor == xanchor
        assert ann.yanchor == yanchor
        assert ann.showarrow == showarrow

    def test_kwargs_passthrough(self) -> None:
        """Test create_text_annotations passes through additional kwargs correctly."""
        # Arrange
        label_data = [{"text": "Kwargs", "x": 1, "y": 1}]

        # Act
        annotations = create_text_annotations_from_data(label_data, bordercolor="red", font_color="black")

        # Assert
        ann = annotations[0]
        assert ann.bordercolor == "red"
        assert ann.font.color == "black"

    def test_mixed_default_and_overridden_kwargs(self) -> None:
        """Test create_text_annotations with mix of default and overridden arguments."""
        # Arrange
        label_data = [{"text": "Mixed", "x": 0, "y": 0}]
        # Override one default, pass one kwarg
        # Act
        annotations = create_text_annotations_from_data(label_data, font_size=20, arrowwidth=2)
        # Assert
        ann = annotations[0]
        assert ann.font.size == 20  # Overridden
        assert ann.font.color == "black"  # Default
        assert ann.arrowwidth == 2  # Kwarg
        assert ann.xanchor == "center"  # Default


class TestPlotUtilsCreateStructuralPolygonsTraces(unittest.TestCase):
    """Test cases for create_structural_polygons_traces function."""

    def test_empty_polygons_data(self) -> None:
        """Test create_structural_polygons_traces with empty input data."""
        # Arrange
        zone_polygons_data: list[dict[str, Any]] = []
        # Act
        traces = create_structural_polygons_traces(zone_polygons_data)
        # Assert
        assert len(traces) == 0

    def test_polygon_no_vertices_key(self) -> None:
        """Test create_structural_polygons_traces with polygon missing vertices key."""
        # Arrange
        zone_polygons_data = [{"color": "blue"}]  # No 'vertices' key
        # Act
        traces = create_structural_polygons_traces(zone_polygons_data)
        # Assert
        assert len(traces) == 0

    def test_polygon_empty_vertices_list(self) -> None:
        """Test create_structural_polygons_traces with empty vertices list."""
        # Arrange
        zone_polygons_data: list[dict[str, Any]] = [{"vertices": []}]
        # Act
        traces = create_structural_polygons_traces(zone_polygons_data)
        # Assert
        assert len(traces) == 0

    def test_polygon_insufficient_vertices(self) -> None:
        """Test create_structural_polygons_traces with insufficient vertices (less than 3)."""
        # Arrange
        zone_polygons_data = [{"vertices": [[0, 0], [1, 1]]}]  # Only 2 vertices
        # Act
        traces = create_structural_polygons_traces(zone_polygons_data)
        # Assert
        assert len(traces) == 0

    def test_single_valid_polygon_default_color(self) -> None:
        """Test create_structural_polygons_traces with single valid polygon using default color."""
        # Arrange
        vertices = [[0, 0], [1, 0], [0, 1]]
        zone_polygons_data = [{"vertices": vertices}]
        expected_x = [0, 1, 0, 0]  # Closed polygon
        expected_y = [0, 0, 1, 0]  # Closed polygon
        default_fill_color = "rgba(220,220,220,0.4)"
        default_line_color = "rgba(100, 100, 100, 0.5)"
        default_line_width = 0.5

        # Act
        traces = create_structural_polygons_traces(zone_polygons_data)

        # Assert
        assert len(traces) == 1
        trace = traces[0]
        assert isinstance(trace, go.Scatter)
        assert list(trace.x) == expected_x
        assert list(trace.y) == expected_y
        assert trace.mode == "lines"
        assert trace.fill == "toself"
        assert trace.fillcolor == default_fill_color
        assert trace.line.width == default_line_width
        assert trace.line.color == default_line_color
        assert trace.hoverinfo == "skip"
        assert not trace.showlegend

    def test_single_valid_polygon_specified_color(self) -> None:
        """Test create_structural_polygons_traces with single valid polygon using specified color."""
        # Arrange
        vertices = [[0, 0], [1, 1], [0, 1]]
        specified_color = "rgba(0,0,255,0.5)"  # Blueish
        zone_polygons_data = [{"vertices": vertices, "color": specified_color}]
        expected_x = [0, 1, 0, 0]
        expected_y = [0, 1, 1, 0]

        # Act
        traces = create_structural_polygons_traces(zone_polygons_data)

        # Assert
        assert len(traces) == 1
        trace = traces[0]
        assert trace.fillcolor == specified_color
        assert list(trace.x) == expected_x
        assert list(trace.y) == expected_y

    def test_multiple_polygons_mixed_validity_and_color(self) -> None:
        """Test create_structural_polygons_traces with multiple polygons of mixed validity and colors."""
        # Arrange
        zone_polygons_data: list[dict[str, Any]] = [
            {"vertices": [[0, 0], [1, 0], [0, 1]]},  # Valid, default color
            {"vertices": [[10, 10], [11, 10]]},  # Invalid (2 points)
            {"vertices": [[5, 5], [6, 5], [6, 6], [5, 6]], "color": "red"},  # Valid, red color
            {"vertices": []},  # Invalid (empty vertices)
        ]

        # Act
        traces = create_structural_polygons_traces(zone_polygons_data)

        # Assert
        assert len(traces) == 2  # Expecting only 2 valid traces

        # Check first valid trace (default color)
        trace1 = traces[0]
        assert trace1.fillcolor == "rgba(220,220,220,0.4)"
        assert list(trace1.x) == [0, 1, 0, 0]

        # Check second valid trace (red color)
        trace2 = traces[1]
        assert trace2.fillcolor == "red"
        assert list(trace2.x) == [5, 6, 6, 5, 5]


class TestPlotUtilsCreateBridgeOutlineTraces(unittest.TestCase):
    """Test cases for create_bridge_outline_traces function."""

    def test_empty_lines_data(self) -> None:
        """Test create_bridge_outline_traces with empty lines data."""
        # Arrange
        bridge_lines_data: list[dict[str, Any]] = []
        # Act
        traces = create_bridge_outline_traces(bridge_lines_data)
        # Assert
        assert len(traces) == 0
        assert isinstance(traces, list)

    def test_line_missing_start_or_end_key(self) -> None:
        """Test create_bridge_outline_traces with lines missing start or end keys."""
        # Arrange
        bridge_lines_data = [
            {"end": [1, 1]},  # Missing start
            {"start": [0, 0]},  # Missing end
        ]
        # Act
        traces = create_bridge_outline_traces(bridge_lines_data)
        # Assert
        assert len(traces) == 0

    def test_line_start_or_end_is_none(self) -> None:
        """Test create_bridge_outline_traces with lines where start or end is None."""
        # Arrange
        bridge_lines_data = [{"start": None, "end": [1, 1]}, {"start": [0, 0], "end": None}]
        # Act
        traces = create_bridge_outline_traces(bridge_lines_data)
        # Assert
        assert len(traces) == 0

    def test_single_valid_line_defaults(self) -> None:
        """Test create_bridge_outline_traces with single valid line using default styling."""
        # Arrange
        start_point = [0, 0]
        end_point = [10, 5]
        bridge_lines_data = [{"start": start_point, "end": end_point}]
        expected_x = [start_point[0], end_point[0]]
        expected_y = [start_point[1], end_point[1]]
        default_color = "grey"
        default_width = 1

        # Act
        traces = create_bridge_outline_traces(bridge_lines_data)

        # Assert
        assert len(traces) == 1
        trace = traces[0]
        assert isinstance(trace, go.Scatter)
        assert list(trace.x) == expected_x
        assert list(trace.y) == expected_y
        assert trace.mode == "lines"
        assert trace.line.color == default_color
        assert trace.line.width == default_width
        assert trace.hoverinfo == "none"
        assert not trace.showlegend

    def test_single_valid_line_specified_color_width(self) -> None:
        """Test create_bridge_outline_traces with single valid line using specified color and width."""
        # Arrange
        start_point = [1, 2]
        end_point = [3, 4]
        specified_color = "blue"
        specified_width = 3
        bridge_lines_data = [{"start": start_point, "end": end_point, "color": specified_color, "width": specified_width}]
        expected_x = [start_point[0], end_point[0]]
        expected_y = [start_point[1], end_point[1]]

        # Act
        traces = create_bridge_outline_traces(bridge_lines_data)

        # Assert
        assert len(traces) == 1
        trace = traces[0]
        assert list(trace.x) == expected_x
        assert list(trace.y) == expected_y
        assert trace.line.color == specified_color
        assert trace.line.width == specified_width

    def test_multiple_lines_mixed_validity(self) -> None:
        """Test create_bridge_outline_traces with multiple lines of mixed validity."""
        # Arrange
        bridge_lines_data: list[dict[str, Any]] = [
            {"start": [0, 0], "end": [1, 1]},  # Valid, default
            {"start": [2, 2]},  # Invalid, missing end
            {"start": [3, 3], "end": [4, 4], "color": "red", "width": 2},  # Valid, specified
            {"start": None, "end": [5, 5]},  # Invalid, start is None
        ]

        # Act
        traces = create_bridge_outline_traces(bridge_lines_data)

        # Assert
        assert len(traces) == 2  # Expecting 2 valid traces

        # Check first valid trace (default color/width)
        trace1 = traces[0]
        assert trace1.line.color == "grey"
        assert trace1.line.width == 1
        assert list(trace1.x) == [0, 1]

        # Check second valid trace (specified color/width)
        trace2 = traces[1]
        assert trace2.line.color == "red"
        assert trace2.line.width == 2
        assert list(trace2.x) == [3, 4]
