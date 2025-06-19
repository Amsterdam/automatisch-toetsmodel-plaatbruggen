"""
Test module for top view plot functionality.

This module contains tests for the build_top_view_figure function which creates
Plotly figures for top view visualization of bridge models.
"""

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import plotly.graph_objects as go

from src.geometry.top_view_plot import build_top_view_figure


class TestTopViewPlot(unittest.TestCase):
    """Test cases for top view plot generation functionality."""

    def _create_default_geometric_data(self) -> dict[str, Any]:
        """Helper to create a basic geometric data dictionary."""
        return {
            "zone_polygons": [],
            "bridge_lines": [],
            "zone_annotations": [],
            "dimension_texts": [],
            "cross_section_labels": [],
        }

    def test_build_top_view_figure_empty_data_no_warnings(self) -> None:
        """Test with empty geometric data and no validation warnings."""
        geo_data = self._create_default_geometric_data()
        fig = build_top_view_figure(geo_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0  # No traces expected
        assert len(fig.layout.annotations) == 1  # One north arrow annotation expected

        # Check basic layout properties
        assert fig.layout.title.text == "Bovenaanzicht (Top View)"
        assert fig.layout.xaxis.title.text == "Length (m)"
        assert fig.layout.yaxis.title.text == "Width (m)"
        assert not fig.layout.showlegend
        assert fig.layout.autosize
        assert fig.layout.hovermode == "closest"
        assert fig.layout.yaxis.scaleanchor == "x"
        assert fig.layout.yaxis.scaleratio == 1
        assert fig.layout.margin.l == 20
        assert fig.layout.margin.r == 20
        assert fig.layout.margin.t == 100
        assert fig.layout.margin.b == 20
        assert fig.layout.plot_bgcolor == "white"

    def test_build_top_view_figure_with_validation_warnings(self) -> None:
        """Test with validation warnings."""
        geo_data = self._create_default_geometric_data()
        warnings = ["Warning 1", "Another warning here."]
        fig = build_top_view_figure(geo_data, validation_messages=warnings)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0
        assert len(fig.layout.annotations) == 2  # North arrow + one consolidated warning annotation

        # Find the warning annotation (not the north arrow)
        warning_annotation = None
        for ann in fig.layout.annotations:
            if "Waarschuwing" in ann.text:
                warning_annotation = ann
                break

        assert warning_annotation is not None
        assert "<b>Waarschuwing (Belastingzones):</b> Warning 1" in warning_annotation.text
        assert "<b>Waarschuwing (Belastingzones):</b> Another warning here." in warning_annotation.text
        assert warning_annotation.font.color == "orangered"
        assert warning_annotation.font.size == 13

    def test_build_top_view_figure_with_zone_polygons(self) -> None:
        """Test figure creation with zone polygon data."""
        geo_data = self._create_default_geometric_data()
        geo_data["zone_polygons"] = [
            {"vertices": [[0, 0], [1, 0], [1, 1], [0, 1]], "color": "rgba(255,0,0,0.5)"},
            {
                "vertices": [[2, 2], [3, 2], [3, 3], [2, 3]],  # Polygon without color
            },
            {"vertices": []},  # Empty vertices, should be skipped
        ]
        fig = build_top_view_figure(geo_data)

        assert len(fig.data) == 2  # Two valid polygons
        polygon_trace_1 = fig.data[0]
        assert list(polygon_trace_1.x) == [0, 1, 1, 0, 0]
        assert list(polygon_trace_1.y) == [0, 0, 1, 1, 0]
        assert polygon_trace_1.fill == "toself"
        assert polygon_trace_1.fillcolor == "rgba(255,0,0,0.5)"
        assert polygon_trace_1.line.width == 0
        assert polygon_trace_1.hoverinfo == "skip"
        assert not polygon_trace_1.showlegend

        polygon_trace_2 = fig.data[1]
        assert list(polygon_trace_2.x) == [2, 3, 3, 2, 2]
        assert list(polygon_trace_2.y) == [2, 2, 3, 3, 2]
        assert polygon_trace_2.fillcolor == "rgba(128,128,128,0.1)"  # Default color

    def test_build_top_view_figure_with_bridge_lines(self) -> None:
        """Test figure creation with bridge line data."""
        geo_data = self._create_default_geometric_data()
        geo_data["bridge_lines"] = [
            {"start": [0, 0], "end": [10, 0], "name_hint": "Segment 0"},  # Added name_hint for clarity in test
            {"start": [0, 5], "end": [10, 5], "name_hint": "Segment 1"},
        ]
        fig = build_top_view_figure(geo_data)

        assert isinstance(fig, go.Figure)
        # We expect 2 traces from bridge_lines based on the input
        assert len(fig.data) == 2, "Incorrect number of data traces found for bridge lines."

        # --- Check Trace 0 ---
        trace_0_name = "Bridge Outline Segment 0"
        bridge_line_trace_0 = None
        for trace in fig.data:
            if hasattr(trace, "name") and trace.name == trace_0_name:
                bridge_line_trace_0 = trace
                break

        assert bridge_line_trace_0 is not None, f"Trace '{trace_0_name}' not found."
        assert bridge_line_trace_0 is not None  # for mypy

        assert bridge_line_trace_0.mode == "lines"
        expected_x_0 = [geo_data["bridge_lines"][0]["start"][0], geo_data["bridge_lines"][0]["end"][0]]
        expected_y_0 = [geo_data["bridge_lines"][0]["start"][1], geo_data["bridge_lines"][0]["end"][1]]
        assert list(bridge_line_trace_0.x) == expected_x_0
        assert list(bridge_line_trace_0.y) == expected_y_0
        assert bridge_line_trace_0.line.color == "blue"  # SUT uses blue
        assert bridge_line_trace_0.line.width == 2
        assert bridge_line_trace_0.hoverinfo == "none"
        assert not bridge_line_trace_0.showlegend

        # --- Check Trace 1 ---
        trace_1_name = "Bridge Outline Segment 1"
        bridge_line_trace_1 = None
        for trace in fig.data:
            if hasattr(trace, "name") and trace.name == trace_1_name:
                bridge_line_trace_1 = trace
                break

        assert bridge_line_trace_1 is not None, f"Trace '{trace_1_name}' not found."
        assert bridge_line_trace_1 is not None  # for mypy

        assert bridge_line_trace_1.mode == "lines"
        expected_x_1 = [geo_data["bridge_lines"][1]["start"][0], geo_data["bridge_lines"][1]["end"][0]]
        expected_y_1 = [geo_data["bridge_lines"][1]["start"][1], geo_data["bridge_lines"][1]["end"][1]]
        assert list(bridge_line_trace_1.x) == expected_x_1
        assert list(bridge_line_trace_1.y) == expected_y_1
        assert bridge_line_trace_1.line.color == "blue"
        assert bridge_line_trace_1.line.width == 2
        assert bridge_line_trace_1.hoverinfo == "none"
        assert not bridge_line_trace_1.showlegend

    def test_build_top_view_figure_with_zone_annotations(self) -> None:
        """Test figure creation with zone annotation data."""
        geo_data = self._create_default_geometric_data()
        geo_data["zone_annotations"] = [
            {"x": 1, "y": 2, "text": "Zone A"},
            {"x": 5, "y": 6, "text": "Zone B"},
        ]
        fig = build_top_view_figure(geo_data)

        assert len(fig.layout.annotations) == 3  # 2 zone annotations + 1 north arrow

        # Find zone annotations (not the north arrow)
        zone_annotations = [ann for ann in fig.layout.annotations if "<b>Zone" in ann.text]
        assert len(zone_annotations) == 2

        ann_1 = zone_annotations[0]
        assert ann_1.x == 1
        assert ann_1.y == 2
        assert ann_1.text == "<b>Zone A</b>"
        assert not ann_1.showarrow
        assert ann_1.font.size == 14
        assert ann_1.font.color == "DarkSlateGray"

    def test_build_top_view_figure_with_dimension_texts(self) -> None:
        """Test figure creation with dimension text data, covering different alignments."""
        geo_data = self._create_default_geometric_data()
        geo_data["dimension_texts"] = [
            {"x": 1, "y": 1, "text": "Default", "type": "width"},  # Default (left, middle)
            {"x": 2, "y": 2, "text": "Length", "type": "length"},  # (center, bottom)
            {"x": 3, "y": 3, "text": "Rotated 180", "textangle": 180},  # (right, middle)
            {"x": 4, "y": 4, "text": "Rotated 90", "textangle": 90},  # (center, middle)
            {"x": 5, "y": 5, "text": "Rotated -90", "textangle": -90},  # (center, middle)
            {"x": 6, "y": 6, "text": "Explicit Center", "align": "center", "xanchor": "center", "yanchor": "middle"},  # Explicit values
        ]
        fig = build_top_view_figure(geo_data)
        assert len(fig.layout.annotations) == 7  # 6 dimension texts + 1 north arrow

        # Filter out the north arrow annotation to get only dimension text annotations
        dim_annotations = [ann for ann in fig.layout.annotations if ann.text not in ["⥊"]]
        assert len(dim_annotations) == 6

        # Default (type: width)
        ann_default = next(a for a in dim_annotations if a.text == "<b>Default</b>")
        assert ann_default.align == "left"
        assert ann_default.xanchor == "left"
        assert ann_default.yanchor == "middle"

        ann_length = next(a for a in dim_annotations if a.text == "<b>Length</b>")
        assert ann_length.align == "center"
        assert ann_length.xanchor == "center"
        assert ann_length.yanchor == "bottom"

        # Rotated 180
        ann_rot180 = next(a for a in dim_annotations if a.text == "<b>Rotated 180</b>")
        assert ann_rot180.align == "right"
        assert ann_rot180.xanchor == "right"
        assert ann_rot180.yanchor == "middle"
        assert ann_rot180.textangle in (180, -180)

        # Rotated 90
        ann_rot90 = next(a for a in dim_annotations if a.text == "<b>Rotated 90</b>")
        assert ann_rot90.align == "center"
        assert ann_rot90.xanchor == "center"
        assert ann_rot90.yanchor == "middle"
        assert ann_rot90.textangle == 90

    @patch("src.geometry.top_view_plot.create_text_annotations_from_data")
    def test_build_top_view_figure_with_cross_section_labels(self, mock_create_text_annotations: MagicMock) -> None:
        """Test figure creation with cross section label data."""
        geo_data = self._create_default_geometric_data()
        cs_label_data = [{"x": 1, "y": 1, "text": "CS1"}]
        geo_data["cross_section_labels"] = cs_label_data

        mock_cs_annotations = [go.layout.Annotation(text="Mocked CS Anno")]
        mock_create_text_annotations.return_value = mock_cs_annotations

        fig = build_top_view_figure(geo_data)

        mock_create_text_annotations.assert_called_once_with(
            label_data=cs_label_data,
            font_size=15,
            font_color="black",
            align="center",
            xanchor="center",
            yanchor="bottom",
        )
        assert len(fig.layout.annotations) == 2  # 1 mocked CS annotation + 1 north arrow
        assert mock_cs_annotations[0] in fig.layout.annotations

    @patch("src.geometry.top_view_plot.create_text_annotations_from_data")
    def test_build_top_view_figure_with_all_data_types(self, mock_create_text_annotations: MagicMock) -> None:
        """Test with all data types present and a validation warning."""
        geo_data = {
            "zone_polygons": [{"vertices": [[0, 0], [1, 0], [0, 1]], "color": "red"}],
            "bridge_lines": [{"start": [0, 0], "end": [1, 0]}],
            "zone_annotations": [{"x": 0.5, "y": 0.5, "text": "Z1"}],
            "dimension_texts": [{"x": 1, "y": 1, "text": "Dim1", "type": "length"}],
            "cross_section_labels": [{"x": 2, "y": 2, "text": "CS-A"}],
        }
        warnings = ["Test Warning"]

        mock_cs_anno_instance = go.layout.Annotation(text="Mocked CS Anno for All Data")
        mock_create_text_annotations.return_value = [mock_cs_anno_instance]

        fig = build_top_view_figure(geo_data, validation_messages=warnings)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # 1 polygon + 1 line
        assert len(fig.layout.annotations) == 5  # zone, dim, cs, warning + north arrow

        # Check polygon trace
        assert list(fig.data[0].x) == [0, 1, 0, 0]
        assert fig.data[0].fillcolor == "red"

        # Check line trace
        assert list(fig.data[1].x) == [0, 1]

        # Check presence of annotations (order might vary, so check by content or type)
        texts = [ann.text for ann in fig.layout.annotations]
        assert "<b>Z1</b>" in texts
        assert "<b>Dim1</b>" in texts
        assert "Mocked CS Anno for All Data" in texts
        assert "<b>Waarschuwing (Belastingzones):</b> Test Warning" in texts
        assert "⥊" in texts  # North arrow

        mock_create_text_annotations.assert_called_once_with(
            label_data=geo_data["cross_section_labels"],
            font_size=15,  # Match args in build_top_view_figure
            font_color="black",
            align="center",
            xanchor="center",
            yanchor="bottom",
        )

    # Add more tests for zone polygons, bridge lines, zone annotations, dimension texts, cross section labels


if __name__ == "__main__":
    unittest.main()
