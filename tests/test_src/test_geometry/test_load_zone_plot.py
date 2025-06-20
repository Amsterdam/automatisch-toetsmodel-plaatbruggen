"""
Test module for load zone plotting functionality.

This module contains tests for creating plotly visualizations of load zones
including 3D geometry views and related plotting operations.
"""

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import plotly.graph_objects as go
from munch import Munch  # type: ignore[import-untyped]

from src.geometry.load_zone_geometry import LoadZoneDataRow  # For constructing test data
from src.geometry.load_zone_plot import (
    DEFAULT_PLOTLY_COLORS,
    DEFAULT_ZONE_APPEARANCE_MAP,
    # TypedDicts - will be used for constructing test data
    BridgeBaseGeometry,
    PlotPresentationDetails,
    ZoneBoundaryLineStyle,
    ZonePlottingGeometry,
    ZoneStylingDefaults,
    build_load_zones_figure,
    create_zone_boundary_line_traces,
    create_zone_fill_trace,
    create_zone_main_label_annotation,
    create_zone_width_annotations,  # Assuming this will be fully tested
    get_zone_appearance_properties,
)


class TestLoadZonePlotHelpers(unittest.TestCase):
    """Test cases for helper functions in load zone plotting module."""

    def test_get_zone_appearance_properties_default(self) -> None:
        """Test get_zone_appearance_properties returns default colors for unknown zone types."""
        props = get_zone_appearance_properties("UnknownType", 0)
        assert props["line_color"] == DEFAULT_PLOTLY_COLORS[0]
        assert props["fill_color"].startswith("rgba")
        assert props["pattern_shape"] == ""

    def test_get_zone_appearance_properties_known_type(self) -> None:
        """Test get_zone_appearance_properties returns correct colors for known zone types."""
        props = get_zone_appearance_properties("Voetgangers", 0)
        assert props["line_color"] == DEFAULT_ZONE_APPEARANCE_MAP["Voetgangers"]["line_color"]
        assert props["fill_color"] == DEFAULT_ZONE_APPEARANCE_MAP["Voetgangers"]["fill_color"]
        assert props["pattern_shape"] == DEFAULT_ZONE_APPEARANCE_MAP["Voetgangers"]["pattern_shape"]

    def test_get_zone_appearance_properties_exceeding_limits(self) -> None:
        """Test get_zone_appearance_properties returns warning colors when exceeding limits."""
        props = get_zone_appearance_properties("AnyType", 0, is_exceeding_limits=True)
        assert props["line_color"] == "red"
        assert props["fill_color"] == "rgba(255, 0, 0, 0.3)"
        assert props["pattern_shape"] == "x"

    def test_create_zone_fill_trace_valid_data(self) -> None:
        """Test create_zone_fill_trace creates valid trace with proper pattern properties."""
        trace = create_zone_fill_trace(
            x_coords=[0, 1, 1, 0],
            y_coords_top=[1, 1, 1, 1],
            y_coords_bottom=[0, 0, 0, 0],
            appearance_props={"fill_color": "blue", "pattern_shape": "+", "pattern_fgcolor": "red", "pattern_solidity": 0.5},
        )
        assert trace is not None
        assert trace is not None  # for mypy
        assert trace.fillpattern.shape == "+"
        assert trace.fillpattern.fgcolor == "red"
        assert trace.fillpattern.solidity == 0.5

    def test_create_zone_fill_trace_empty_data(self) -> None:
        """Test create_zone_fill_trace with empty input data."""
        trace = create_zone_fill_trace([], [], [], {})
        assert trace is None

    def test_create_zone_boundary_line_traces_first_zone(self) -> None:
        """Test create_zone_boundary_line_traces for the first zone."""
        geometry = ZonePlottingGeometry(x_coords=[0, 1], y_coords_top=[1, 1], y_coords_bottom=[0, 0])
        style = ZoneBoundaryLineStyle(line_color="green", sbs_line_thickness=1, sbs_offset=0.1, absolute_edge_thickness=3)

        traces = create_zone_boundary_line_traces(0, 3, geometry, style)  # zone_idx=0, num_load_zones=3

        assert len(traces) == 2
        # Top line should be thick (absolute edge)
        assert traces[0].line.width == 3
        assert list(traces[0].y) == [1, 1]  # y_coords_top
        # Bottom line should be offset upward by sbs_offset
        assert traces[1].line.width == 1
        assert list(traces[1].y) == [0 + 0.1, 0 + 0.1]  # y + sbs_offset

    def test_create_zone_boundary_line_traces_middle_zone(self) -> None:
        """Test create_zone_boundary_line_traces for a middle zone."""
        geometry = ZonePlottingGeometry(x_coords=[0, 1], y_coords_top=[2, 2], y_coords_bottom=[1, 1])
        style = ZoneBoundaryLineStyle(line_color="blue", sbs_line_thickness=1, sbs_offset=0.1, absolute_edge_thickness=3)

        traces = create_zone_boundary_line_traces(1, 3, geometry, style)  # zone_idx=1, num_load_zones=3

        assert len(traces) == 2
        # Both lines should use sbs thickness for middle zones
        assert traces[0].line.width == 1
        assert list(traces[0].y) == [1.9, 1.9]  # y_coords_top - sbs_offset: [2-0.1, 2-0.1]
        assert traces[1].line.width == 1
        assert list(traces[1].y) == [1.1, 1.1]  # y_coords_bottom + sbs_offset: [1+0.1, 1+0.1]

    def test_create_zone_boundary_line_traces_last_zone(self) -> None:
        """Test create_zone_boundary_line_traces for the last zone."""
        geometry = ZonePlottingGeometry(x_coords=[0, 1], y_coords_top=[3, 3], y_coords_bottom=[2, 2])
        style = ZoneBoundaryLineStyle(line_color="purple", sbs_line_thickness=1, sbs_offset=0.1, absolute_edge_thickness=3)

        traces = create_zone_boundary_line_traces(2, 3, geometry, style)  # zone_idx=2, num_load_zones=3 (last zone)

        assert len(traces) == 2
        # Top line should be thin with offset (not first zone, so uses sbs_line_thickness)
        assert traces[0].line.width == 1
        assert list(traces[0].y) == [2.9, 2.9]  # y_coords_top - sbs_offset: [3-0.1, 3-0.1]
        # Bottom line should be thick (absolute edge) for last zone
        assert traces[1].line.width == 3
        assert list(traces[1].y) == [2, 2]  # y_coords_bottom (no offset for last zone)

    def test_create_zone_main_label_annotation(self) -> None:
        """Test create_zone_main_label_annotation with basic parameters."""
        geometry = ZonePlottingGeometry(x_coords=[0, 10, 20], y_coords_top=[5, 5, 5], y_coords_bottom=[4, 4, 4])
        annotation = create_zone_main_label_annotation(0, "TestZone", geometry, x_offset=1.0)

        assert annotation.x == 21.0  # Last x coordinate + x_offset: 20 + 1.0 = 21.0
        assert annotation.y == 4.5  # Mid-point between top and bottom: (5+4)/2 = 4.5
        assert annotation.text == "<b>bz1</b>: <i>TestZone</i>"

    def test_create_zone_width_annotations_basic(self) -> None:
        """Test create_zone_width_annotations with basic parameters."""
        zone_param_data = self._create_dummy_load_zone_data_row(d_widths=[2.0, 2.5, 3.0])
        geometry = ZonePlottingGeometry(x_coords=[0, 2, 4.5, 7.5], y_coords_top=[1, 1, 1, 1], y_coords_bottom=[0, 0, 0, 0])

        annotations = create_zone_width_annotations(
            zone_param_data,
            geometry,
            num_defined_d_points=4,  # Matches x_coords length
            zone_idx=0,
            num_load_zones=3,
        )

        # Should have annotations for d1_width (2.0), d2_width (2.5), and d3_width (3.0)
        assert len(annotations) == 3

        # First annotation: d1_width
        ann_d1 = annotations[0]
        assert ann_d1.x == 0  # x_coords[0]
        assert ann_d1.y == 0.5  # (y_coords_top[0] + y_coords_bottom[0]) / 2: (1+0)/2 = 0.5
        assert ann_d1.text == "2.00m"

        # Second annotation: d2_width
        ann_d2 = annotations[1]
        assert ann_d2.x == 2  # x_coords[1]
        assert ann_d2.y == 0.5  # (y_coords_top[1] + y_coords_bottom[1]) / 2: (1+0)/2 = 0.5
        assert ann_d2.text == "2.50m"

    def test_create_zone_width_annotations_last_zone_uses_calculated_width(self) -> None:
        """Test that the last zone uses calculated width instead of parameter width."""
        # For the last zone, display_width should be the calculated current_zone_calculated_width
        zone_param_data = self._create_dummy_load_zone_data_row(d_widths=[2.0, 2.0])  # Params might suggest 2.0
        geometry = ZonePlottingGeometry(x_coords=[0, 2], y_coords_top=[1, 1], y_coords_bottom=[0.2, 0.2])

        annotations = create_zone_width_annotations(
            zone_param_data,
            geometry,
            num_defined_d_points=2,
            zone_idx=1,  # Last zone (zone_idx=1, num_load_zones=2)
            num_load_zones=2,
        )

        # For last zone, should use calculated width (1-0.2=0.8), not param width (2.0)
        assert len(annotations) == 2
        assert annotations[1].text == "0.80m"  # Calculated width at d2

    def test_create_zone_width_annotations_empty_if_widths_too_small(self) -> None:
        """Test that no annotations are created when zone widths are too small."""
        zone_param_data = self._create_dummy_load_zone_data_row(d_widths=[0.001, 0.002])
        geometry = ZonePlottingGeometry(x_coords=[0, 1], y_coords_top=[1, 1], y_coords_bottom=[0.999, 0.998])

        annotations = create_zone_width_annotations(
            zone_param_data,
            geometry,
            num_defined_d_points=2,
            zone_idx=0,
            num_load_zones=2,
        )

        # Width differences are too small (< 0.01m), so no annotations should be created
        assert len(annotations) == 0

    def _create_dummy_load_zone_data_row(self, d_widths: list[float]) -> LoadZoneDataRow:
        """Creates a LoadZoneDataRow-like dictionary for testing width annotations."""
        row_dict: dict[str, Any] = {
            "zone_type": "Dummy",  # zone_type not used by create_zone_width_annotations
            # Add new pavement fields
            "pavement_thickness": 0.05,  # Default 5cm
            "pavement_material": "Asfalt",  # Default material
        }
        for i, width in enumerate(d_widths):
            row_dict[f"d{i + 1}_width"] = width  # Store raw float, not Munch(value=width)
        # Fill remaining up to 15 with 0.0 if not provided
        for i in range(len(d_widths) + 1, 16):
            row_dict[f"d{i}_width"] = 0.0
        return row_dict  # type: ignore[return-value]


class TestBuildLoadZonesFigure(unittest.TestCase):
    """Tests for the main build_load_zones_figure function."""

    def _create_minimal_load_zone_data_row(self, zone_type: str = "Auto", d_widths: list[float] | None = None) -> LoadZoneDataRow:
        if d_widths is None:
            # Ensure d_widths matches num_defined_d_points in BridgeBaseGeometry for simplicity
            d_widths = [1.0, 1.1, 1.2, 1.3, 1.4]  # 5 widths by default

        row_dict = {
            "zone_type": Munch(value=zone_type),
            "d1_width": d_widths[0] if len(d_widths) > 0 else 0.0,
            "d2_width": d_widths[1] if len(d_widths) > 1 else 0.0,
            "d3_width": d_widths[2] if len(d_widths) > 2 else 0.0,
            "d4_width": d_widths[3] if len(d_widths) > 3 else 0.0,
            "d5_width": d_widths[4] if len(d_widths) > 4 else 0.0,
            # Add the missing y_coords_top_current_zone field that build_load_zones_figure expects
            "y_coords_top_current_zone": [1.0] * len(d_widths),  # Mock top coordinates
            # Add the missing zone_widths_per_d field that build_load_zones_figure expects
            "zone_widths_per_d": d_widths[:],  # Copy of d_widths list
            # Add new pavement fields
            "pavement_thickness": 0.05,  # Default 5cm
            "pavement_material": "Asfalt",  # Default material
        }

        # Add d6 to d15 as 0.0
        for i in range(6, 16):
            row_dict[f"d{i}_width"] = 0.0

        # This step is more for type checking during test writing;
        # the function itself will receive a list of such dictionaries (or Munch objects)
        return row_dict  # type: ignore[return-value]

    def _get_default_bridge_base_geometry(self, num_d_points: int = 5) -> BridgeBaseGeometry:
        # y_coords_bridge_bottom_edge should be list[list[float]], e.g., [[y_min, y_max], ...]
        # Let's assume y_min_bridge_at_d_point = -5.0 and y_max_bridge_at_d_point = 5.0 for testing
        y_min_val = -5.0
        y_max_val = 5.0  # This would be from y_coords_bridge_top_edge generally
        return BridgeBaseGeometry(
            x_coords_d_points=list(np.linspace(0, 20, num_d_points)),
            y_coords_bridge_top_edge=[y_max_val] * num_d_points,  # Consistent with y_max_val. This is a list[float]
            y_coords_bridge_bottom_edge=[[y_min_val, y_max_val] for _ in range(num_d_points)],  # This is list[list[float]]
            num_defined_d_points=num_d_points,
        )

    def _get_default_styling_defaults(self) -> ZoneStylingDefaults:
        return ZoneStylingDefaults(
            zone_appearance_map=DEFAULT_ZONE_APPEARANCE_MAP,
            default_plotly_colors=DEFAULT_PLOTLY_COLORS,
        )

    def _get_default_presentation_details(self) -> PlotPresentationDetails:
        return PlotPresentationDetails(
            base_traces=None,
            validation_messages=None,
            figure_title="Test Load Zones Plot",
        )

    @patch("src.geometry.load_zone_plot.calculate_zone_bottom_y_coords")
    @patch("src.geometry.load_zone_plot.get_zone_appearance_properties")
    @patch("src.geometry.load_zone_plot.create_zone_fill_trace")
    @patch("src.geometry.load_zone_plot.create_zone_boundary_line_traces")
    @patch("src.geometry.load_zone_plot.create_zone_main_label_annotation")
    @patch("src.geometry.load_zone_plot.create_zone_width_annotations")
    def test_build_load_zones_figure_single_zone_no_warnings(  # noqa: PLR0913
        self,
        mock_create_width_annots: MagicMock,
        mock_create_main_label: MagicMock,
        mock_create_boundary_lines: MagicMock,
        mock_create_fill_trace: MagicMock,
        mock_get_appearance: MagicMock,
        mock_calculate_bottom_y: MagicMock,
    ) -> None:
        """Test with a single load zone and no validation warnings."""
        num_d_points = 3
        bridge_geom = self._get_default_bridge_base_geometry(num_d_points=num_d_points)

        # Mock return values for helpers
        # y_coords_top_of_current_zone and y_coords_bottom_of_current_zone are list[float]
        def debug_mock(
            _zone_idx: int,
            _num_load_zones: int,
            num_defined_d_points: int,
            _y_coords_top: list[float],
            _y_bridge_bottom: list[list[float]],
            _zone_params: Any,  # noqa: ANN401
        ) -> list[float]:
            return [0.0] * num_defined_d_points  # Return list[float], not tuple

        mock_calculate_bottom_y.side_effect = debug_mock
        mock_get_appearance.return_value = {"line_color": "blue", "fill_color": "lightblue", "pattern_shape": ""}
        mock_create_fill_trace.return_value = go.Scatter(name="mock_fill_trace")
        mock_create_boundary_lines.return_value = [go.Scatter(name="mock_boundary_trace")]
        mock_create_main_label.return_value = go.layout.Annotation(text="mock_label")
        mock_create_width_annots.return_value = [go.layout.Annotation(text="mock_width_annot")]

        zone_data_row = self._create_minimal_load_zone_data_row(d_widths=[2.0] * num_d_points)
        load_zones_data = [zone_data_row]

        styling = self._get_default_styling_defaults()
        presentation = self._get_default_presentation_details()

        fig = build_load_zones_figure(load_zones_data, bridge_geom, styling, presentation)

        assert isinstance(fig, go.Figure)

        # Check calls to mocks
        mock_calculate_bottom_y.assert_called_once()
        mock_get_appearance.assert_called_once()
        mock_create_fill_trace.assert_called_once()
        mock_create_boundary_lines.assert_called_once()
        mock_create_main_label.assert_called_once()
        mock_create_width_annots.assert_called_once()

        # Check figure content based on mocks
        assert len(fig.data) == 2  # fill + boundary
        assert mock_create_fill_trace.return_value in fig.data
        assert mock_create_boundary_lines.return_value[0] in fig.data

        assert len(fig.layout.annotations) == 2  # main label + width annot
        assert mock_create_main_label.return_value in fig.layout.annotations
        assert mock_create_width_annots.return_value[0] in fig.layout.annotations

        # Check layout
        assert fig.layout.title.text == presentation["figure_title"]
        # ... other layout checks as needed

    @patch("src.geometry.load_zone_plot.calculate_zone_bottom_y_coords")
    @patch("src.geometry.load_zone_plot.get_zone_appearance_properties")
    @patch("src.geometry.load_zone_plot.create_zone_fill_trace")
    @patch("src.geometry.load_zone_plot.create_zone_boundary_line_traces")
    @patch("src.geometry.load_zone_plot.create_zone_main_label_annotation")
    @patch("src.geometry.load_zone_plot.create_zone_width_annotations")
    def test_build_load_zones_figure_with_validation_and_base_traces(  # noqa: PLR0913
        self,
        mock_create_width_annots: MagicMock,
        mock_create_main_label: MagicMock,
        mock_create_boundary_lines: MagicMock,
        mock_create_fill_trace: MagicMock,
        mock_get_appearance: MagicMock,
        mock_calculate_bottom_y: MagicMock,
    ) -> None:
        """Test with validation messages and base traces."""
        num_d_points = 1
        bridge_geom = self._get_default_bridge_base_geometry(num_d_points=num_d_points)

        mock_calculate_bottom_y.return_value = [0.0] * num_d_points  # y_bottom as list[float]
        mock_get_appearance.return_value = {"line_color": "blue", "fill_color": "lightblue", "pattern_shape": ""}
        mock_create_fill_trace.return_value = go.Scatter(name="fill")
        mock_create_boundary_lines.return_value = [go.Scatter(name="boundary")]
        mock_create_main_label.return_value = go.layout.Annotation(text="label")
        mock_create_width_annots.return_value = [go.layout.Annotation(text="width")]

        load_zones_data = [self._create_minimal_load_zone_data_row(d_widths=[1.0] * num_d_points)]
        styling = self._get_default_styling_defaults()

        base_trace1 = go.Scatter(x=[0], y=[0], name="base1")
        validation_msg = ["Warning!"]
        presentation = PlotPresentationDetails(
            base_traces=[base_trace1],
            validation_messages=validation_msg,
            figure_title="Test With Extras",
        )

        fig = build_load_zones_figure(load_zones_data, bridge_geom, styling, presentation)

        assert base_trace1 in fig.data
        assert len(fig.data) == 3  # 1 base + 1 fill + 1 boundary

        assert len(fig.layout.annotations) == 3  # label, width, validation
        validation_annotation = next(ann for ann in fig.layout.annotations if "Waarschuwing:" in ann.text)
        assert validation_annotation is not None
        assert validation_msg[0] in validation_annotation.text
        assert fig.layout.margin.b == 150  # Check margin update due to validation message


if __name__ == "__main__":
    unittest.main()
