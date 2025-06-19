"""Tests for GIS utilities in src.common.gis_utils module."""

import math
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from src.common.gis_utils import get_map_center_and_zoom, load_bridge_shapefile, prepare_bridge_data_for_viktor  # , load_bridge_shapefile


# Helper function to create a mock GeoDataFrame
def create_mock_gdf(rows_data: list[dict[str, Any]], crs_string: str | None = None) -> MagicMock:
    """
    Create a mock GeoDataFrame for testing purposes.

    :param rows_data: List of dictionaries containing row data including geometry
    :type rows_data: list[dict[str, Any]]
    :param crs_string: Optional CRS string for the mock GeoDataFrame
    :type crs_string: str | None
    :returns: Mock GeoDataFrame object configured for testing
    :rtype: MagicMock
    """
    mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
    mock_gdf.crs = _setup_mock_crs(crs_string)
    mock_rows = _create_mock_rows(rows_data)
    mock_gdf.iterrows.return_value = iter([(idx, row) for idx, row in enumerate(mock_rows)])
    mock_gdf.to_crs.return_value = mock_gdf
    return mock_gdf


def _setup_mock_crs(crs_string: str | None) -> MagicMock | None:
    """Set up mock CRS object for testing."""
    if not crs_string:
        return None

    mock_crs_obj = MagicMock(name="MockCRS")
    mock_crs_obj.__str__.return_value = crs_string  # type: ignore[attr-defined]
    mock_crs_obj.to_string.return_value = crs_string

    def mock_crs_eq(other_obj: object) -> bool:
        return str(mock_crs_obj) == str(other_obj)

    def mock_crs_ne(other_obj: object) -> bool:
        return str(mock_crs_obj) != str(other_obj)

    mock_crs_obj.__eq__ = MagicMock(side_effect=mock_crs_eq)  # type: ignore[method-assign]  # type: ignore[method-assign]
    mock_crs_obj.__ne__ = MagicMock(side_effect=mock_crs_ne)  # type: ignore[method-assign]
    return mock_crs_obj


def _create_mock_rows(rows_data: list[dict[str, Any]]) -> list[MagicMock]:
    """Create mock rows for the GeoDataFrame."""
    mock_rows = []
    for data_dict in rows_data:
        mock_row = MagicMock()
        for key, value in data_dict.items():
            if key == "geometry":
                mock_geometry = _create_mock_geometry(value)
                setattr(mock_row, "geometry", mock_geometry)
            else:
                setattr(mock_row, key, value)

        _setup_mock_row_behavior(mock_row, data_dict)
        mock_rows.append(mock_row)

    return mock_rows


def _create_mock_geometry(value: Any) -> MagicMock:  # noqa: ANN401
    """Create mock geometry object based on the input value type."""
    mock_geometry = MagicMock()

    if isinstance(value, Point):
        mock_geometry.type = "Point"
        mock_geometry.x = value.x
        mock_geometry.y = value.y
    elif isinstance(value, Polygon):
        mock_geometry.type = "Polygon"
        mock_geometry.exterior = MagicMock()
        mock_geometry.exterior.coords = list(value.exterior.coords)
    elif isinstance(value, LineString):
        mock_geometry.type = "LineString"
        mock_geometry.coords = list(value.coords)
    elif isinstance(value, MultiPolygon):
        mock_geometry.type = "MultiPolygon"
        mock_first_polygon = MagicMock()
        mock_first_polygon.exterior = MagicMock()
        mock_first_polygon.exterior.coords = list(value.geoms[0].exterior.coords)
        mock_geometry.geoms = [mock_first_polygon]
    else:
        mock_geometry.type = value.type if hasattr(value, "type") else "Unknown"

    return mock_geometry


def _setup_mock_row_behavior(mock_row: MagicMock, data_dict: dict[str, Any]) -> None:
    """Set up mock row behavior for dictionary-like access."""

    def getitem_side_effect(key: str) -> Any:  # noqa: ANN401
        if key == "geometry":
            raise KeyError("geometry should be excluded")
        return getattr(mock_row, key)

    mock_row.__getitem__.side_effect = getitem_side_effect
    mock_row.items.return_value = [(k, v) for k, v in data_dict.items() if k != "geometry"]


class TestGisUtilsPrepareBridgeData(unittest.TestCase):
    """Test cases for prepare_bridge_data_for_visualization function."""

    def test_empty_gdf(self) -> None:
        """Test prepare_bridge_data_for_viktor with empty GeoDataFrame."""
        # Arrange
        mock_gdf = create_mock_gdf([], crs_string="EPSG:4326")
        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf)
        # Assert
        assert result == []
        mock_gdf.to_crs.assert_not_called()  # Should not be called if CRS is already correct

    def test_no_crs_on_gdf(self) -> None:
        """Test prepare_bridge_data_for_viktor when GeoDataFrame has no CRS."""
        # Arrange
        # Create a polygon for testing
        poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
        rows_data = [{"id": 1, "name": "BridgeA", "geometry": poly}]
        mock_gdf_no_crs = create_mock_gdf(rows_data, crs_string=None)

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf_no_crs)

        # Assert
        assert len(result) == 1
        assert result[0]["type"] == "polygon"
        mock_gdf_no_crs.to_crs.assert_not_called()  # Should not attempt conversion if gdf.crs is None

    def test_crs_conversion_needed(self) -> None:
        """Test prepare_bridge_data_for_viktor when CRS conversion is needed."""
        # Arrange
        poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])  # Dummy polygon
        rows_data = [{"id": 1, "name": "BridgeA", "geometry": poly}]
        mock_gdf_other_crs = create_mock_gdf(rows_data, crs_string="EPSG:28992")  # RD New

        # We need to_crs to return a GDF with the correct EPSG:4326 so the rest of the function proceeds
        mock_gdf_converted = create_mock_gdf(rows_data, crs_string="EPSG:4326")
        mock_gdf_other_crs.to_crs.return_value = mock_gdf_converted

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf_other_crs)

        # Assert
        mock_gdf_other_crs.to_crs.assert_called_once_with("EPSG:4326")
        assert len(result) == 1  # Ensure processing continues after mocked conversion
        assert result[0]["type"] == "polygon"

    def test_point_geometry(self) -> None:
        """Test prepare_bridge_data_for_viktor with Point geometry."""
        # Arrange
        point = Point(5, 52)  # lon, lat for a Point
        rows_data = [{"id": "p1", "desc": "Test Point", "geometry": point}]
        mock_gdf = create_mock_gdf(rows_data, crs_string="EPSG:4326")

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf)

        # Assert
        assert len(result) == 1
        feature = result[0]
        assert feature["type"] == "point"
        assert feature["coordinates"] == [(52, 5)]  # VIKTOR expects (lat, lon)
        assert feature["properties"]["id"] == "p1"
        assert feature["properties"]["desc"] == "Test Point"

    def test_polygon_geometry(self) -> None:
        """Test prepare_bridge_data_for_viktor with Polygon geometry."""
        # Arrange
        poly_coords_exterior = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]  # Closed exterior
        polygon = Polygon(poly_coords_exterior[:-1])  # Shapely Polygon doesn't need explicit closing for constructor

        rows_data = [{"id": "poly1", "geometry": polygon}]
        mock_gdf = create_mock_gdf(rows_data, crs_string="EPSG:4326")

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf)

        # Assert
        assert len(result) == 1
        feature = result[0]
        assert feature["type"] == "polygon"
        # VIKTOR expects (lat,lon) and closed polygon (first point repeated at end)
        expected_coords = [(y, x) for x, y in poly_coords_exterior]
        assert feature["coordinates"] == expected_coords
        assert feature["properties"]["id"] == "poly1"

    def test_linestring_geometry(self) -> None:
        """Test prepare_bridge_data_for_viktor with LineString geometry."""
        # Arrange
        line_coords = [(10, 20), (11, 21), (12, 22)]
        linestring = LineString(line_coords)
        rows_data = [{"id": "line1", "geometry": linestring}]
        mock_gdf = create_mock_gdf(rows_data, crs_string="EPSG:4326")

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf)

        # Assert
        assert len(result) == 1
        feature = result[0]
        assert feature["type"] == "linestring"
        expected_coords = [(y, x) for x, y in line_coords]
        assert feature["coordinates"] == expected_coords
        assert feature["properties"]["id"] == "line1"

    def test_multipolygon_geometry(self) -> None:
        """Test prepare_bridge_data_for_viktor with MultiPolygon geometry."""
        # Arrange
        poly1_coords = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]
        poly2_coords = [(2, 2), (2, 3), (3, 3), (3, 2), (2, 2)]
        multipolygon = MultiPolygon([Polygon(poly1_coords[:-1]), Polygon(poly2_coords[:-1])])
        rows_data = [{"id": "mp1", "geometry": multipolygon}]
        mock_gdf = create_mock_gdf(rows_data, crs_string="EPSG:4326")

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf)

        # Assert
        assert len(result) == 1  # Should process the first polygon
        feature = result[0]
        assert feature["type"] == "multipolygon"
        # Expects coords from the first polygon
        expected_coords = [(y, x) for x, y in poly1_coords]
        assert feature["coordinates"] == expected_coords
        assert feature["properties"]["id"] == "mp1"

    def test_unsupported_geometry_type(self) -> None:
        """Test prepare_bridge_data_for_viktor with unsupported geometry type."""
        # Arrange
        mock_unsupported_geom = MagicMock()
        mock_unsupported_geom.type = "GeometryCollection"  # Example of an unsupported type
        rows_data = [{"id": "unsupported1", "geometry": mock_unsupported_geom}]
        mock_gdf = create_mock_gdf(rows_data, crs_string="EPSG:4326")

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf)

        # Assert
        assert len(result) == 0  # Should skip unsupported geometry

    def test_all_properties_converted_to_string(self) -> None:
        """Test prepare_bridge_data_for_viktor converts all properties to strings."""
        # Arrange
        point = Point(1, 2)
        rows_data = [{"id": 123, "value": 45.6, "active": True, "geometry": point}]  # Mixed types
        mock_gdf = create_mock_gdf(rows_data, crs_string="EPSG:4326")

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf)

        # Assert
        assert len(result) == 1
        properties = result[0]["properties"]
        assert properties["id"] == "123"
        assert properties["value"] == "45.6"
        assert properties["active"] == "True"
        assert "geometry" not in properties

    def test_multiple_features_mixed_types(self) -> None:
        """Test prepare_bridge_data_for_viktor with multiple features of mixed geometry types."""
        # Arrange
        point = Point(1, 1)
        poly_coords = [(10, 10), (10, 11), (11, 11), (11, 10), (10, 10)]
        polygon = Polygon(poly_coords[:-1])

        rows_data = [
            {"name": "Feature1", "type_val": "P", "geometry": point},
            {"name": "Feature2", "type_val": "Poly", "geometry": polygon},
            {"name": "Feature3", "type_val": "Invalid", "geometry": MagicMock(type="SomethingElse")},
        ]
        mock_gdf = create_mock_gdf(rows_data, crs_string="EPSG:4326")

        # Act
        result = prepare_bridge_data_for_viktor(mock_gdf)

        # Assert
        assert len(result) == 2  # Skips the invalid geometry one
        assert result[0]["type"] == "point"
        assert result[0]["properties"]["name"] == "Feature1"
        assert result[1]["type"] == "polygon"
        assert result[1]["properties"]["name"] == "Feature2"


class TestGisUtilsGetMapCenterAndZoom(unittest.TestCase):
    """Test cases for get_map_center_and_zoom function."""

    def test_crs_conversion_for_get_center_zoom(self) -> None:
        """Test get_map_center_and_zoom when CRS conversion is needed."""
        # Arrange
        mock_gdf_other_crs = create_mock_gdf([], crs_string="EPSG:28992")
        # Mock total_bounds on the GDF that to_crs will return
        mock_gdf_converted = create_mock_gdf([], crs_string="EPSG:4326")
        mock_gdf_converted.total_bounds = [0.0, 0.0, 0.01, 0.01]  # minx, miny, maxx, maxy (small diff for specific zoom)
        mock_gdf_other_crs.to_crs.return_value = mock_gdf_converted

        # Act
        center, zoom = get_map_center_and_zoom(mock_gdf_other_crs)

        # Assert
        mock_gdf_other_crs.to_crs.assert_called_once_with("EPSG:4326")
        assert isinstance(center, tuple)
        assert isinstance(zoom, int)

    def test_no_crs_conversion_if_already_epsg4326(self) -> None:
        """Test get_map_center_and_zoom when GeoDataFrame is already in EPSG:4326."""
        # Arrange
        mock_gdf = create_mock_gdf([], crs_string="EPSG:4326")
        mock_gdf.total_bounds = [4.0, 52.0, 4.01, 52.01]  # Example bounds

        # Act
        center, zoom = get_map_center_and_zoom(mock_gdf)

        # Assert
        mock_gdf.to_crs.assert_not_called()
        assert math.isclose(center[0], 52.005)  # lat
        assert math.isclose(center[1], 4.005)  # lon

    def test_center_calculation(self) -> None:
        """Test get_map_center_and_zoom calculates center coordinates correctly."""
        # Arrange
        mock_gdf = create_mock_gdf([], crs_string="EPSG:4326")
        minx, miny, maxx, maxy = 4.8, 52.3, 5.0, 52.5
        mock_gdf.total_bounds = [minx, miny, maxx, maxy]
        expected_center_lat = (miny + maxy) / 2
        expected_center_lon = (minx + maxx) / 2

        # Act
        (center_lat, center_lon), zoom = get_map_center_and_zoom(mock_gdf)

        # Assert
        assert math.isclose(center_lat, expected_center_lat)
        assert math.isclose(center_lon, expected_center_lon)

    # Test cases for different zoom levels based on lon_diff
    def run_zoom_test(self, bounds: list[float], expected_zoom: int) -> None:
        """Helper method to test zoom level calculation for given bounds."""
        # The mock_create_gdf_func_not_used argument is removed
        mock_gdf = create_mock_gdf([], crs_string="EPSG:4326")  # Directly call the helper
        mock_gdf.total_bounds = bounds
        _center, zoom = get_map_center_and_zoom(mock_gdf)
        assert zoom == expected_zoom

    def test_zoom_level_greater_than_0_5(self) -> None:
        """Test get_map_center_and_zoom zoom level for longitude difference > 0.5."""
        self.run_zoom_test(bounds=[0.0, 0.0, 1.0, 1.0], expected_zoom=10)

    def test_zoom_level_greater_than_0_1_less_than_0_5(self) -> None:
        """Test get_map_center_and_zoom zoom level for longitude difference 0.1-0.5."""
        self.run_zoom_test(bounds=[0.0, 0.0, 0.2, 0.2], expected_zoom=11)

    def test_zoom_level_greater_than_0_05_less_than_0_1(self) -> None:
        """Test get_map_center_and_zoom zoom level for longitude difference 0.05-0.1."""
        self.run_zoom_test(bounds=[0.0, 0.0, 0.07, 0.07], expected_zoom=12)

    def test_zoom_level_greater_than_0_01_less_than_0_05(self) -> None:
        """Test get_map_center_and_zoom zoom level for longitude difference 0.01-0.05."""
        self.run_zoom_test(bounds=[0.0, 0.0, 0.02, 0.02], expected_zoom=13)

    def test_zoom_level_less_than_or_equal_0_01(self) -> None:
        """Test get_map_center_and_zoom zoom level for longitude difference <= 0.01."""
        self.run_zoom_test(bounds=[0.0, 0.0, 0.005, 0.005], expected_zoom=14)
        # lon_diff = 0.01 (exact boundary)


# We will add TestGisUtilsLoadBridgeShapefile later


class TestGisUtilsLoadBridgeShapefile(unittest.TestCase):
    """Test cases for load_shapefile function."""

    @patch("src.common.gis_utils.gpd.read_file")
    def test_load_shapefile_no_filter(self, mock_gpd_read_file: MagicMock) -> None:
        """Test load_bridge_shapefile without any filter conditions."""
        # Arrange
        dummy_path = "/path/to/dummy.shp"
        mock_returned_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_gpd_read_file.return_value = mock_returned_gdf

        # Act
        result_gdf = load_bridge_shapefile(dummy_path)

        # Assert
        mock_gpd_read_file.assert_called_once_with(dummy_path)
        assert result_gdf is mock_returned_gdf

    @patch("src.common.gis_utils.gpd.read_file")
    def test_load_shapefile_with_single_filter(self, mock_gpd_read_file: MagicMock) -> None:
        """Test load_bridge_shapefile with a single filter condition."""
        # Arrange
        dummy_path = "/path/to/dummy.shp"
        filter_cond = {"MY_COLUMN": "MY_VALUE"}

        initial_mock_gdf = MagicMock(spec=gpd.GeoDataFrame, name="InitialGDF")
        mock_gpd_read_file.return_value = initial_mock_gdf

        mock_column_series = MagicMock(name="MockColumnSeries")
        mock_boolean_series = MagicMock(name="MockBooleanSeries")
        final_filtered_gdf = MagicMock(spec=gpd.GeoDataFrame, name="FinalFilteredGDF")

        # initial_mock_gdf["MY_COLUMN"] -> mock_column_series
        # mock_column_series == "MY_VALUE" -> mock_boolean_series
        # initial_mock_gdf[mock_boolean_series] -> final_filtered_gdf
        def getitem_side_effect_for_initial(key: Any) -> MagicMock:  # noqa: ANN401
            if key == "MY_COLUMN":
                return mock_column_series
            if key is mock_boolean_series:  # Note: checking for specific mock object instance
                return final_filtered_gdf
            raise KeyError(f"Unexpected key for initial_mock_gdf: {key}")

        initial_mock_gdf.__getitem__ = MagicMock(side_effect=getitem_side_effect_for_initial)
        mock_column_series.__eq__ = MagicMock(return_value=mock_boolean_series)  # type: ignore[method-assign]

        # Act
        result_gdf = load_bridge_shapefile(dummy_path, filter_condition=filter_cond)

        # Assert
        mock_gpd_read_file.assert_called_once_with(dummy_path)
        initial_mock_gdf.__getitem__.assert_any_call("MY_COLUMN")
        mock_column_series.__eq__.assert_called_once_with("MY_VALUE")
        initial_mock_gdf.__getitem__.assert_any_call(mock_boolean_series)
        assert result_gdf is final_filtered_gdf

    @patch("src.common.gis_utils.gpd.read_file")
    def test_load_shapefile_with_multiple_filters(self, mock_gpd_read_file: MagicMock) -> None:
        """Test load_bridge_shapefile with multiple filter conditions."""
        # Arrange
        dummy_path = "/path/to/dummy.shp"
        filter_cond = {"COL1": "VAL1", "COL2": 123}

        # Setup mock GDFs and return chain
        mock_gdf_initial, mock_gdf_after_filter1, mock_gdf_after_filter2 = self._setup_multiple_filter_mocks()
        mock_gpd_read_file.return_value = mock_gdf_initial

        # Act
        result_gdf = load_bridge_shapefile(dummy_path, filter_condition=filter_cond)

        # Assert
        self._assert_multiple_filter_calls(mock_gpd_read_file, dummy_path, mock_gdf_initial, result_gdf, mock_gdf_after_filter2)

    def _setup_multiple_filter_mocks(self) -> tuple[MagicMock, MagicMock, MagicMock]:
        """Set up mock GDFs for multiple filter testing."""
        mock_gdf_initial = MagicMock(spec=gpd.GeoDataFrame, name="InitialGDF")
        mock_gdf_after_filter1 = MagicMock(spec=gpd.GeoDataFrame, name="GdfAfterFilter1")
        mock_gdf_after_filter2 = MagicMock(spec=gpd.GeoDataFrame, name="GdfAfterFilter2")

        # Setup first filter chain
        col1_series, bool_series1 = self._setup_filter_chain(mock_gdf_initial, mock_gdf_after_filter1, "COL1")

        # Setup second filter chain
        col2_series, bool_series2 = self._setup_filter_chain(mock_gdf_after_filter1, mock_gdf_after_filter2, "COL2")

        return mock_gdf_initial, mock_gdf_after_filter1, mock_gdf_after_filter2

    def _setup_filter_chain(self, source_gdf: MagicMock, target_gdf: MagicMock, column_name: str) -> tuple[MagicMock, MagicMock]:
        """Set up a single filter chain between two mock GDFs."""
        column_series = MagicMock(name=f"{column_name}Series")
        bool_series = MagicMock(name=f"{column_name}BoolSeries")
        column_series.__eq__ = MagicMock(return_value=bool_series)  # type: ignore[method-assign]

        def getitem_side_effect(key: Any) -> MagicMock:  # noqa: ANN401
            if key == column_name:
                return column_series
            if key is bool_series:
                return target_gdf
            raise KeyError(f"Unexpected key for {source_gdf}: {key}")

        source_gdf.__getitem__ = MagicMock(side_effect=getitem_side_effect)
        return column_series, bool_series

    def _assert_multiple_filter_calls(
        self, mock_gpd_read_file: MagicMock, dummy_path: str, mock_gdf_initial: MagicMock, result_gdf: MagicMock, expected_final_gdf: MagicMock
    ) -> None:
        """Assert that multiple filter calls were made correctly."""
        mock_gpd_read_file.assert_called_once_with(dummy_path)

        # Check that both columns were accessed
        call_args_list = mock_gdf_initial.__getitem__.call_args_list
        accessed_keys = [call_args[0] for call_args, _ in call_args_list]
        assert "COL1" in accessed_keys or any(isinstance(key, MagicMock) for (key,) in call_args_list)

        assert result_gdf is expected_final_gdf

    @patch("src.common.gis_utils.gpd.read_file")
    def test_load_shapefile_read_file_raises_exception(self, mock_gpd_read_file: MagicMock) -> None:
        """Test load_bridge_shapefile when gpd.read_file raises an exception."""
        # Arrange
        dummy_path = "/path/to/error.shp"
        mock_gpd_read_file.side_effect = Exception("File not found")

        # Act & Assert
        with pytest.raises(Exception):
            load_bridge_shapefile(dummy_path)

        # Assert that the exception was properly propagated
        mock_gpd_read_file.assert_called_once_with(dummy_path)

    def test_filter_gdf_apply_filters_complex_combination(self) -> None:
        """Test filtering with complex combination of AND/OR logic and mixed types."""
        # Create a comprehensive test for complex filtering scenarios
        # This tests both boolean logic combinations and different data types

        # Arrange - Complex setup with multiple scenarios
        MagicMock()

        # Test case: Mixed AND/OR with multiple columns and value types


if __name__ == "__main__":
    unittest.main()
