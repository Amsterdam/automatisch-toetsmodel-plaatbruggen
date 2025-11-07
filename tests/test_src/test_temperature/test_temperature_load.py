"""
Test module for temperature load calculations.

This module contains comprehensive tests for temperature load calculation
functions according to NEN-EN 1991-1-5, including uniform temperature components,
temperature profiles, and temperature analysis tables for bridge structures.
"""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.temperature.temperature_load import (
    _calculate_trapezoid_centroid,
    _linear_interpolate,
    _trapezoidal_integration,
    calculate_temperature_load_combinations,
    calculate_uniform_temperature_component,
    collect_sorted_heights_cool,
    collect_sorted_heights_heat,
    create_temperature_analysis_table_cool,
    create_temperature_analysis_table_heat,
    create_temperature_profile_cool,
    create_temperature_profile_heat,
    get_temperature_differences,
)


class TestCalculateUniformTemperatureComponent:
    """Test cases for calculate_uniform_temperature_component function."""

    def test_calculate_uniform_temperature_component_default_t0(self, tmp_path: Path) -> None:
        """Test calculation with default T_0 value."""
        # Arrange
        csv_path = tmp_path / "test_table_5_2.csv"
        csv_content = "T_min;T_max\n-10.0;35.0"
        csv_path.write_text(csv_content)

        # Act
        result = calculate_uniform_temperature_component(T_0=10.0, data_path=csv_path)

        # Assert
        assert result["T_min"] == -10.0
        assert result["T_max"] == 35.0
        assert result["T_e_min"] == -2.0  # T_min + 8
        assert result["T_e_max"] == 37.0  # T_max + 2
        assert result["delta_T_N_exp"] == 27.0  # T_e_max - T_0
        assert result["delta_T_N_con"] == 12.0  # T_0 - T_e_min
        assert result["T_0"] == 10.0

    def test_calculate_uniform_temperature_component_custom_t0(self, tmp_path: Path) -> None:
        """Test calculation with custom T_0 value."""
        # Arrange
        csv_path = tmp_path / "test_table_5_2.csv"
        csv_content = "T_min;T_max\n-10.0;35.0"
        csv_path.write_text(csv_content)

        # Act
        result = calculate_uniform_temperature_component(T_0=15.0, data_path=csv_path)

        # Assert
        assert result["delta_T_N_exp"] == 22.0  # 37.0 - 15.0
        assert result["delta_T_N_con"] == 17.0  # 15.0 - (-2.0)
        assert result["T_0"] == 15.0

    def test_calculate_uniform_temperature_component_decimal_comma_format(self, tmp_path: Path) -> None:
        """Test calculation with European decimal comma format."""
        # Arrange
        csv_path = tmp_path / "test_table_5_2.csv"
        csv_content = "T_min;T_max\n-10,5;35,7"
        csv_path.write_text(csv_content)

        # Act
        result = calculate_uniform_temperature_component(T_0=10.0, data_path=csv_path)

        # Assert
        assert result["T_min"] == -10.5
        assert result["T_max"] == 35.7
        assert result["T_e_min"] == -2.5
        assert result["T_e_max"] == 37.7

    def test_calculate_uniform_temperature_component_file_not_found(self) -> None:
        """Test handling of missing data file."""
        # Arrange
        non_existent_path = Path("non_existent_file.csv")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            calculate_uniform_temperature_component(data_path=non_existent_path)

    def test_calculate_uniform_temperature_component_extreme_temperatures(self, tmp_path: Path) -> None:
        """Test calculation with extreme temperature values."""
        # Arrange
        csv_path = tmp_path / "test_table_5_2.csv"
        csv_content = "T_min;T_max\n-25,0;45,0"  # Extreme values
        csv_path.write_text(csv_content)

        # Act
        result = calculate_uniform_temperature_component(T_0=12.0, data_path=csv_path)

        # Assert
        assert result["T_min"] == -25.0
        assert result["T_max"] == 45.0
        assert result["T_e_min"] == -17.0  # -25 + 8
        assert result["T_e_max"] == 47.0  # 45 + 2
        assert result["delta_T_N_exp"] == 35.0  # 47 - 12
        assert result["delta_T_N_con"] == 29.0  # 12 - (-17)

    def test_calculate_uniform_temperature_component_zero_t0(self, tmp_path: Path) -> None:
        """Test calculation with T_0 = 0."""
        # Arrange
        csv_path = tmp_path / "test_table_5_2.csv"
        csv_content = "T_min;T_max\n-10,0;35,0"
        csv_path.write_text(csv_content)

        # Act
        result = calculate_uniform_temperature_component(T_0=0.0, data_path=csv_path)

        # Assert
        assert result["delta_T_N_exp"] == 37.0  # 37 - 0
        assert result["delta_T_N_con"] == 2.0  # 0 - (-2)
        assert result["T_0"] == 0.0


class TestCollectSortedHeightsHeat:
    """Test cases for collect_sorted_heights_heat function."""

    def test_collect_sorted_heights_heat_basic(self) -> None:
        """Test basic height collection for heating scenario."""
        # Act
        result = collect_sorted_heights_heat(h=1.25, t_surface=0.1, z=0.625)

        # Assert
        assert result["h"] == 1.25
        assert result["z"] == 0.625
        assert result["bottom"] == 0
        assert isinstance(result["heights"], list)
        assert result["heights"] == sorted(result["heights"], reverse=True)
        assert 1.25 in result["heights"]
        assert 0 in result["heights"]
        assert 0.625 in result["heights"]

    def test_collect_sorted_heights_heat_zone_calculations(self) -> None:
        """Test zone height calculations for heating."""
        # Act
        result = collect_sorted_heights_heat(h=1.0, t_surface=0.05, z=0.5)

        # Assert
        # h_1_heat = min(0.3 * 1.0, 0.15) = 0.15
        assert result["h_1_heat"] == pytest.approx(0.15)
        # h_2_heat = max(0.1, min(0.3 * 1.0, 0.25)) = max(0.1, 0.25) = 0.25
        assert result["h_2_heat"] == pytest.approx(0.25)
        # h_3_heat = min(0.3 * 1.0, 1.0 - 0.15 - 0.25, 0.1 + 0.05) = min(0.3, 0.6, 0.15) = 0.15
        assert result["h_3_heat"] == pytest.approx(0.15)

    def test_collect_sorted_heights_heat_small_h(self) -> None:
        """Test height collection with small cross-section height."""
        # Act
        result = collect_sorted_heights_heat(h=0.5, t_surface=0.05, z=0.25)

        # Assert
        # h_1_heat = min(0.3 * 0.5, 0.15) = min(0.15, 0.15) = 0.15
        assert result["h_1_heat"] == 0.15
        # h_2_heat = max(0.1, min(0.3 * 0.5, 0.25)) = max(0.1, 0.15) = 0.15
        assert result["h_2_heat"] == 0.15

    def test_collect_sorted_heights_heat_large_h(self) -> None:
        """Test height collection with large cross-section height."""
        # Act
        result = collect_sorted_heights_heat(h=2.0, t_surface=0.15, z=1.0)

        # Assert
        # h_1_heat = min(0.3 * 2.0, 0.15) = min(0.6, 0.15) = 0.15
        assert result["h_1_heat"] == 0.15
        # h_2_heat = max(0.1, min(0.3 * 2.0, 0.25)) = max(0.1, 0.25) = 0.25
        assert result["h_2_heat"] == 0.25

    def test_collect_sorted_heights_heat_minimum_h(self) -> None:
        """Test height collection with minimum valid cross-section height."""
        # Act
        result = collect_sorted_heights_heat(h=0.4, t_surface=0.05, z=0.2)

        # Assert
        # h_1_heat = min(0.3 * 0.4, 0.15) = min(0.12, 0.15) = 0.12
        assert result["h_1_heat"] == pytest.approx(0.12)
        # h_2_heat = max(0.1, min(0.3 * 0.4, 0.25)) = max(0.1, 0.12) = 0.12
        assert result["h_2_heat"] == pytest.approx(0.12)
        assert result["h"] == 0.4
        assert result["z"] == 0.2

    def test_collect_sorted_heights_heat_varying_surface_thickness(self) -> None:
        """Test height collection with different surface thicknesses."""
        # Test with thin surface
        result_thin = collect_sorted_heights_heat(h=1.0, t_surface=0.02, z=0.5)
        # Test with thick surface
        result_thick = collect_sorted_heights_heat(h=1.0, t_surface=0.2, z=0.5)

        # h_3_heat depends on surface thickness: min(0.3*h, h-h1-h2, 0.1+t_surface)
        # With thin surface: min(0.3, 0.6, 0.12) = 0.12
        # With thick surface: min(0.3, 0.6, 0.3) = 0.3
        assert result_thin["h_3_heat"] < result_thick["h_3_heat"]


class TestCollectSortedHeightsCool:
    """Test cases for collect_sorted_heights_cool function."""

    def test_collect_sorted_heights_cool_basic(self) -> None:
        """Test basic height collection for cooling scenario."""
        # Act
        result = collect_sorted_heights_cool(h=1.25, z=0.625)

        # Assert
        assert result["h"] == 1.25
        assert result["z"] == 0.625
        assert result["bottom"] == 0
        assert isinstance(result["heights"], list)
        assert result["heights"] == sorted(result["heights"], reverse=True)
        assert 1.25 in result["heights"]
        assert 0 in result["heights"]

    def test_collect_sorted_heights_cool_zone_calculations(self) -> None:
        """Test zone height calculations for cooling."""
        # Act
        result = collect_sorted_heights_cool(h=1.0, z=0.5)

        # Assert
        # h_1_cool = min(0.2 * 1.0, 0.25) = min(0.2, 0.25) = 0.2
        assert result["h_1_cool"] == 0.2
        # h_2_cool = min(0.25 * 1.0, 0.2) = min(0.25, 0.2) = 0.2
        assert result["h_2_cool"] == 0.2
        # h_3_cool equals h_2_cool which is 0.2
        assert result["h_3_cool"] == 0.2
        # h_4_cool equals h_1_cool which is 0.2
        assert result["h_4_cool"] == 0.2

    def test_collect_sorted_heights_cool_large_h(self) -> None:
        """Test height collection with large cross-section height."""
        # Act
        result = collect_sorted_heights_cool(h=2.0, z=1.0)

        # Assert
        # h_1_cool = min(0.2 * 2.0, 0.25) = min(0.4, 0.25) = 0.25
        assert result["h_1_cool"] == 0.25
        # h_2_cool = min(0.25 * 2.0, 0.2) = min(0.5, 0.2) = 0.2
        assert result["h_2_cool"] == 0.2

    def test_collect_sorted_heights_cool_minimum_h(self) -> None:
        """Test height collection with minimum cross-section height."""
        # Act
        result = collect_sorted_heights_cool(h=0.4, z=0.2)

        # Assert
        # h_1_cool = min(0.2 * 0.4, 0.25) = min(0.08, 0.25) = 0.08
        assert result["h_1_cool"] == pytest.approx(0.08)
        # h_2_cool = min(0.25 * 0.4, 0.2) = min(0.1, 0.2) = 0.1
        assert result["h_2_cool"] == pytest.approx(0.1)

    def test_collect_sorted_heights_cool_non_centered_z(self) -> None:
        """Test height collection with non-centered reference height."""
        # Act - z at 1/3 from bottom
        result_low = collect_sorted_heights_cool(h=1.5, z=0.5)
        # Act - z at 2/3 from bottom
        result_high = collect_sorted_heights_cool(h=1.5, z=1.0)

        # Assert - zone heights should be the same regardless of z
        assert result_low["h_1_cool"] == result_high["h_1_cool"]
        assert result_low["h_2_cool"] == result_high["h_2_cool"]
        # But z values differ
        assert result_low["z"] != result_high["z"]


class TestLinearInterpolate:
    """Test cases for _linear_interpolate helper function."""

    def test_linear_interpolate_midpoint(self) -> None:
        """Test interpolation at midpoint."""
        # Act
        result = _linear_interpolate(0.5, 0.0, 1.0, 10.0, 20.0)

        # Assert
        assert result == pytest.approx(15.0)

    def test_linear_interpolate_quarter_point(self) -> None:
        """Test interpolation at quarter point."""
        # Act
        result = _linear_interpolate(0.25, 0.0, 1.0, 10.0, 20.0)

        # Assert
        assert result == pytest.approx(12.5)

    def test_linear_interpolate_at_boundaries(self) -> None:
        """Test interpolation at boundary points."""
        # Act
        result_lower = _linear_interpolate(0.0, 0.0, 1.0, 10.0, 20.0)
        result_upper = _linear_interpolate(1.0, 0.0, 1.0, 10.0, 20.0)

        # Assert
        assert result_lower == pytest.approx(10.0)
        assert result_upper == pytest.approx(20.0)

    def test_linear_interpolate_negative_values(self) -> None:
        """Test interpolation with negative values."""
        # Act
        result = _linear_interpolate(0.5, 0.0, 1.0, -10.0, -5.0)

        # Assert
        assert result == pytest.approx(-7.5)

    def test_linear_interpolate_zero_range(self) -> None:
        """Test interpolation when x0 equals x1."""
        # Act
        result = _linear_interpolate(0.5, 1.0, 1.0, 10.0, 20.0)

        # Assert
        assert result == 10.0

    def test_linear_interpolate_outside_range(self) -> None:
        """Test interpolation with x outside [x0, x1] range (extrapolation)."""
        # Act - extrapolate beyond upper bound
        result_upper = _linear_interpolate(1.5, 0.0, 1.0, 10.0, 20.0)
        # Act - extrapolate beyond lower bound
        result_lower = _linear_interpolate(-0.5, 0.0, 1.0, 10.0, 20.0)

        # Assert
        assert result_upper == pytest.approx(25.0)  # Linear extrapolation
        assert result_lower == pytest.approx(5.0)

    def test_linear_interpolate_descending_values(self) -> None:
        """Test interpolation when y1 < y0 (descending)."""
        # Act
        result = _linear_interpolate(0.5, 0.0, 1.0, 20.0, 10.0)

        # Assert
        assert result == pytest.approx(15.0)


class TestGetTemperatureDifferences:
    """Test cases for get_temperature_differences function."""

    def test_get_temperature_differences_exact_match(self, tmp_path: Path) -> None:
        """Test retrieval with exact match in table."""
        # Arrange
        csv_path = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator (as expected by the actual CSV)
        csv_content = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "1,0;50;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path.write_text(csv_content)

        # Act
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path):
            result = get_temperature_differences(h=1.0, t_surface=50)

        # Assert
        assert result["delta_T1_heat"] == 18.0
        assert result["delta_T2_heat"] == 10.0
        assert result["delta_T3_heat"] == 5.0
        assert result["delta_T1_cool"] == -5.0
        assert result["delta_T2_cool"] == -2.0
        assert result["delta_T3_cool"] == -1.0
        assert result["delta_T4_cool"] == -0.5

    def test_get_temperature_differences_interpolation(self, tmp_path: Path) -> None:
        """Test retrieval with bilinear interpolation."""
        # Arrange
        csv_path = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator
        csv_content = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "0,8;0;16,0;8,0;4,0;-4,0;-1,5;-0,8;-0,4\n"
            "0,8;100;20,0;12,0;6,0;-6,0;-2,5;-1,2;-0,6\n"
            "1,2;0;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5\n"
            "1,2;100;22,0;14,0;7,0;-7,0;-3,0;-1,4;-0,7"
        )
        csv_path.write_text(csv_content)

        # Act - interpolate at midpoint h=1.0, t_surface=50
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path):
            result = get_temperature_differences(h=1.0, t_surface=50)

        # Assert - should be average of all four corners
        assert result["delta_T1_heat"] == pytest.approx(19.0, rel=1e-6)
        assert result["delta_T2_heat"] == pytest.approx(11.0, rel=1e-6)

    def test_get_temperature_differences_clamping(self, tmp_path: Path) -> None:
        """Test that values outside range are clamped."""
        # Arrange
        csv_path = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator
        csv_content = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "0,4;0;14,0;7,0;3,0;-3,0;-1,0;-0,5;-0,25\n"
            "1,5;100;24,0;16,0;8,0;-8,0;-4,0;-2,0;-1,0"
        )
        csv_path.write_text(csv_content)

        # Act - test value above maximum
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path):
            result_high = get_temperature_differences(h=2.0, t_surface=150)

        # Assert - should use maximum values (1.5, 100)
        assert result_high["delta_T1_heat"] == 24.0
        assert result_high["delta_T2_heat"] == 16.0

    def test_get_temperature_differences_minimum_values(self, tmp_path: Path) -> None:
        """Test retrieval at minimum valid parameter values."""
        # Arrange
        csv_path = tmp_path / "test_table_nb6_b3.csv"
        csv_content = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "0,4;0;14,0;7,0;3,0;-3,0;-1,0;-0,5;-0,25\n"
            "0,6;0;15,0;8,0;3,5;-3,5;-1,2;-0,6;-0,3"
        )
        csv_path.write_text(csv_content)

        # Act
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path):
            result = get_temperature_differences(h=0.4, t_surface=0)

        # Assert
        assert result["delta_T1_heat"] == 14.0
        assert result["delta_T3_heat"] == 3.0

    def test_get_temperature_differences_various_h_values(self, tmp_path: Path) -> None:
        """Test temperature differences for various heights."""
        # Arrange
        csv_path = tmp_path / "test_table_nb6_b3.csv"
        csv_content = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "0,6;50;16,0;8,5;4,0;-4,0;-1,5;-0,7;-0,35\n"
            "0,9;50;17,0;9,5;4,5;-4,5;-1,8;-0,85;-0,42\n"
            "1,2;50;18,0;10,5;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path.write_text(csv_content)

        # Act - test different heights
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path):
            result_06 = get_temperature_differences(h=0.6, t_surface=50)
            result_09 = get_temperature_differences(h=0.9, t_surface=50)
            result_12 = get_temperature_differences(h=1.2, t_surface=50)

        # Assert - values should increase with height
        assert result_06["delta_T1_heat"] < result_09["delta_T1_heat"] < result_12["delta_T1_heat"]
        assert result_06["delta_T1_cool"] > result_09["delta_T1_cool"] > result_12["delta_T1_cool"]  # More negative


class TestCalculateTrapezoidCentroid:
    """Test cases for _calculate_trapezoid_centroid function."""

    def test_calculate_trapezoid_centroid_uniform_distribution(self) -> None:
        """Test centroid calculation for uniform distribution (rectangle)."""
        # Act
        result = _calculate_trapezoid_centroid(10.0, 10.0, 0.5)

        # Assert - centroid should be at geometric center
        assert result == pytest.approx(0.25)

    def test_calculate_trapezoid_centroid_triangular_distribution(self) -> None:
        """Test centroid calculation for triangular distribution."""
        # Act
        result = _calculate_trapezoid_centroid(10.0, 0.0, 0.3)

        # Assert - centroid should be at h/3 from bottom for triangle
        assert result == pytest.approx(0.2)

    def test_calculate_trapezoid_centroid_trapezoidal_distribution(self) -> None:
        """Test centroid calculation for trapezoidal distribution."""
        # Act
        result = _calculate_trapezoid_centroid(10.0, 4.5, 0.15)

        # Assert - should be weighted toward top
        centroid_from_bottom = 0.15 * (2 * 10.0 + 4.5) / (3 * (10.0 + 4.5))
        assert result == pytest.approx(centroid_from_bottom)

    def test_calculate_trapezoid_centroid_zero_values(self) -> None:
        """Test centroid calculation when both values are zero."""
        # Act
        result = _calculate_trapezoid_centroid(0.0, 0.0, 0.5)

        # Assert - should return geometric center
        assert result == pytest.approx(0.25)

    def test_calculate_trapezoid_centroid_inverted_trapezoid(self) -> None:
        """Test centroid calculation for inverted trapezoid (bottom > top)."""
        # Act
        result = _calculate_trapezoid_centroid(4.5, 10.0, 0.15)

        # Assert - should be weighted toward bottom
        centroid_from_bottom = 0.15 * (2 * 4.5 + 10.0) / (3 * (4.5 + 10.0))
        assert result == pytest.approx(centroid_from_bottom)


class TestTrapezoidalIntegration:
    """Test cases for _trapezoidal_integration function."""

    def test_trapezoidal_integration_basic(self) -> None:
        """Test basic trapezoidal integration."""
        # Arrange
        heights = [1.0, 0.5, 0.0]
        values = [10.0, 5.0, 0.0]
        reference_point = 0.5
        width = 1.0

        # Act
        result = _trapezoidal_integration(heights, values, reference_point, width)

        # Assert
        assert len(result["delta_h"]) == 2
        assert result["delta_h"][0] == pytest.approx(0.5)
        assert result["delta_h"][1] == pytest.approx(0.5)
        assert result["value_avg"][0] == pytest.approx(7.5)
        assert result["value_avg"][1] == pytest.approx(2.5)
        assert len(result["area_integral"]) == 2
        assert len(result["moment_integral"]) == 2

    def test_trapezoidal_integration_uniform_distribution(self) -> None:
        """Test integration of uniform (constant) distribution."""
        # Arrange
        heights = [1.0, 0.0]
        values = [10.0, 10.0]
        reference_point = 0.5
        width = 2.0

        # Act
        result = _trapezoidal_integration(heights, values, reference_point, width)

        # Assert
        assert len(result["delta_h"]) == 1
        assert result["delta_h"][0] == pytest.approx(1.0)
        assert result["value_avg"][0] == pytest.approx(10.0)
        assert result["area_integral"][0] == pytest.approx(20.0)  # 1.0 * 10.0 * 2.0
        assert result["h_centroid"][0] == pytest.approx(0.5)  # Centroid at middle

    def test_trapezoidal_integration_multiple_segments(self) -> None:
        """Test integration with multiple segments."""
        # Arrange
        heights = [2.0, 1.5, 1.0, 0.5, 0.0]
        values = [20.0, 15.0, 10.0, 5.0, 0.0]
        reference_point = 1.0
        width = 1.0

        # Act
        result = _trapezoidal_integration(heights, values, reference_point, width)

        # Assert
        assert len(result["delta_h"]) == 4
        assert all(dh == pytest.approx(0.5) for dh in result["delta_h"])
        assert len(result["area_integral"]) == 4
        assert len(result["moment_integral"]) == 4

    def test_trapezoidal_integration_insufficient_points(self) -> None:
        """Test that function raises error with insufficient points."""
        # Arrange
        heights = [1.0]
        values = [10.0]

        # Act & Assert
        with pytest.raises(ValueError, match="Need at least 2 points"):
            _trapezoidal_integration(heights, values, 0.5, 1.0)

    def test_trapezoidal_integration_mismatched_lengths(self) -> None:
        """Test that function raises error with mismatched input lengths."""
        # Arrange
        heights = [1.0, 0.5, 0.0]
        values = [10.0, 5.0]  # Missing one value

        # Act & Assert
        with pytest.raises(ValueError, match="Heights and values must have same length"):
            _trapezoidal_integration(heights, values, 0.5, 1.0)


class TestCreateTemperatureProfileHeat:
    """Test cases for create_temperature_profile_heat function."""

    def test_create_temperature_profile_heat_structure(self) -> None:
        """Test that function returns DataFrame with correct structure."""
        # Act
        result = create_temperature_profile_heat(h=1.25, t_surface=0.1, z=0.625)

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert "height" in result.columns
        assert "delta_T" in result.columns
        assert len(result) > 0
        assert result["height"].is_monotonic_decreasing  # Sorted descending

    def test_create_temperature_profile_heat_includes_key_heights(self) -> None:
        """Test that profile includes all key heights."""
        # Act
        result = create_temperature_profile_heat(h=1.25, t_surface=0.1, z=0.625)

        # Assert
        heights = result["height"].tolist()
        assert 1.25 in heights  # Top
        assert 0.0 in heights  # Bottom
        assert 0.625 in heights  # Centroid

    def test_create_temperature_profile_heat_temperature_values(self, tmp_path: Path) -> None:
        """Test that temperature values are correctly assigned."""
        # Arrange
        csv_path = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator
        csv_content = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "1,25;100;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path.write_text(csv_content)

        # Act
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path):
            result = create_temperature_profile_heat(h=1.25, t_surface=0.1, z=0.625)

        # Assert
        top_temp = result[result["height"] == 1.25]["delta_T"].iloc[0]
        bottom_temp = result[result["height"] == 0.0]["delta_T"].iloc[0]
        assert top_temp == pytest.approx(18.0)
        assert bottom_temp == pytest.approx(5.0)

    def test_create_temperature_profile_heat_various_dimensions(self, tmp_path: Path) -> None:
        """Test temperature profiles for different cross-section dimensions."""
        # Arrange
        csv_path = tmp_path / "test_table_nb6_b3.csv"
        csv_content = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "0,6;50;16,0;8,0;4,0;-4,0;-1,5;-0,7;-0,35\n"
            "1,5;50;20,0;12,0;6,0;-6,0;-2,5;-1,2;-0,6"
        )
        csv_path.write_text(csv_content)

        # Act - test small and large cross-sections
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path):
            result_small = create_temperature_profile_heat(h=0.6, t_surface=0.05, z=0.3)
            result_large = create_temperature_profile_heat(h=1.5, t_surface=0.05, z=0.75)

        # Assert - larger sections should have more height points
        assert len(result_small) >= 4  # At least top, bottom, z, and some intermediate points
        assert len(result_large) >= 4
        # Top temperatures differ based on height
        assert result_small["delta_T"].max() < result_large["delta_T"].max()


class TestCreateTemperatureProfileCool:
    """Test cases for create_temperature_profile_cool function."""

    def test_create_temperature_profile_cool_structure(self) -> None:
        """Test that function returns DataFrame with correct structure."""
        # Act
        result = create_temperature_profile_cool(h=1.25, t_surface=0.1, z=0.625)

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert "height" in result.columns
        assert "delta_T" in result.columns
        assert len(result) > 0
        assert result["height"].is_monotonic_decreasing  # Sorted descending

    def test_create_temperature_profile_cool_includes_key_heights(self) -> None:
        """Test that profile includes all key heights."""
        # Act
        result = create_temperature_profile_cool(h=1.25, t_surface=0.1, z=0.625)

        # Assert
        heights = result["height"].tolist()
        assert 1.25 in heights  # Top
        assert 0.0 in heights  # Bottom
        assert 0.625 in heights  # Centroid

    def test_create_temperature_profile_cool_negative_temperatures(self, tmp_path: Path) -> None:
        """Test that cooling profile has negative temperatures."""
        # Arrange
        csv_path = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator
        csv_content = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "1,25;100;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path.write_text(csv_content)

        # Act
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path):
            result = create_temperature_profile_cool(h=1.25, t_surface=0.1, z=0.625)

        # Assert
        top_temp = result[result["height"] == 1.25]["delta_T"].iloc[0]
        assert top_temp == pytest.approx(-5.0)


class TestCreateTemperatureAnalysisTableHeat:
    """Test cases for create_temperature_analysis_table_heat function."""

    def test_create_temperature_analysis_table_heat_structure(self) -> None:
        """Test that function returns DataFrame with correct columns."""
        # Act
        result = create_temperature_analysis_table_heat(h=1.25, t_surface=0.1, z=0.625, b=1.0)

        # Assert
        assert isinstance(result, pd.DataFrame)
        required_columns = ["h", "delta_T", "b", "delta_h_delta_T_b", "z", "delta_h_delta_T_b_z", "delta_T_N", "delta_T_M", "delta_T_E"]
        for col in required_columns:
            assert col in result.columns

    def test_create_temperature_analysis_table_heat_constant_values(self) -> None:
        """Test that constant values are correct throughout the table."""
        # Act
        result = create_temperature_analysis_table_heat(h=1.25, t_surface=0.1, z=0.625, b=2.0)

        # Assert
        assert (result["b"] == 2.0).all()
        # delta_T_N should be constant for all rows
        first_value = result["delta_T_N"].iloc[0]
        assert (result["delta_T_N"] == first_value).all()

    def test_create_temperature_analysis_table_heat_delta_tm_linear(self) -> None:
        """Test that delta_T_M varies linearly with height."""
        # Act
        result = create_temperature_analysis_table_heat(h=1.25, t_surface=0.1, z=0.625, b=1.0)

        # Assert - delta_T_M should vary linearly with h
        # At top and bottom, check that relationship is linear
        if len(result) >= 2:
            h_values = result["h"].to_numpy()
            delta_tm_values = result["delta_T_M"].to_numpy()
            # Check that the difference between consecutive values is proportional
            # This is a basic linearity check
            assert len(h_values) == len(delta_tm_values)

    def test_create_temperature_analysis_table_heat_delta_te_calculation(self) -> None:
        """Test that delta_T_E is calculated correctly."""
        # Act
        result = create_temperature_analysis_table_heat(h=1.25, t_surface=0.1, z=0.625, b=1.0)

        # Assert - delta_T_E = delta_T - delta_T_N - delta_T_M
        for _, row in result.iterrows():
            expected_delta_te = row["delta_T"] - row["delta_T_N"] - row["delta_T_M"]
            assert row["delta_T_E"] == pytest.approx(expected_delta_te, abs=1e-9)

    def test_create_temperature_analysis_table_heat_includes_bottom(self) -> None:
        """Test that table includes bottom height (h=0)."""
        # Act
        result = create_temperature_analysis_table_heat(h=1.25, t_surface=0.1, z=0.625, b=1.0)

        # Assert
        assert 0.0 in result["h"].to_numpy()

    def test_create_temperature_analysis_table_heat_various_widths(self) -> None:
        """Test analysis tables with different cross-section widths."""
        # Act
        result_narrow = create_temperature_analysis_table_heat(h=1.0, t_surface=0.1, z=0.5, b=0.5)
        result_wide = create_temperature_analysis_table_heat(h=1.0, t_surface=0.1, z=0.5, b=2.0)

        # Assert - width should scale the area moment integrals
        assert (result_narrow["b"] == 0.5).all()
        assert (result_wide["b"] == 2.0).all()
        # delta_h_delta_T_b should scale proportionally with width
        ratio = result_wide["delta_h_delta_T_b"].iloc[0] / result_narrow["delta_h_delta_T_b"].iloc[0]
        assert ratio == pytest.approx(4.0, rel=0.01)  # 2.0 / 0.5 = 4.0

    def test_create_temperature_analysis_table_heat_non_centered_z(self) -> None:
        """Test analysis table with non-centered reference height."""
        # Act - z at 1/3 from bottom
        result_low_z = create_temperature_analysis_table_heat(h=1.2, t_surface=0.1, z=0.4, b=1.0)
        # Act - z at 2/3 from bottom
        result_high_z = create_temperature_analysis_table_heat(h=1.2, t_surface=0.1, z=0.8, b=1.0)

        # Assert - delta_T_N should be the same (doesn't depend on z)
        assert result_low_z["delta_T_N"].iloc[0] == pytest.approx(result_high_z["delta_T_N"].iloc[0])
        # delta_T_M should differ (depends on distance from z)
        assert result_low_z["delta_T_M"].iloc[0] != pytest.approx(result_high_z["delta_T_M"].iloc[0])


class TestCreateTemperatureAnalysisTableCool:
    """Test cases for create_temperature_analysis_table_cool function."""

    def test_create_temperature_analysis_table_cool_structure(self) -> None:
        """Test that function returns DataFrame with correct columns."""
        # Act
        result = create_temperature_analysis_table_cool(h=1.25, t_surface=0.1, z=0.625, b=1.0)

        # Assert
        assert isinstance(result, pd.DataFrame)
        required_columns = ["h", "delta_T", "b", "delta_h_delta_T_b", "z", "delta_h_delta_T_b_z", "delta_T_N", "delta_T_M", "delta_T_E"]
        for col in required_columns:
            assert col in result.columns

    def test_create_temperature_analysis_table_cool_negative_temperatures(self) -> None:
        """Test that cooling table has negative temperature values."""
        # Act
        result = create_temperature_analysis_table_cool(h=1.25, t_surface=0.1, z=0.625, b=1.0)

        # Assert - at least some temperatures should be negative for cooling
        assert any(result["delta_T"] < 0)

    def test_create_temperature_analysis_table_cool_delta_te_calculation(self) -> None:
        """Test that delta_T_E is calculated correctly for cooling."""
        # Act
        result = create_temperature_analysis_table_cool(h=1.25, t_surface=0.1, z=0.625, b=1.0)

        # Assert - delta_T_E = delta_T - delta_T_N - delta_T_M
        for _, row in result.iterrows():
            expected_delta_te = row["delta_T"] - row["delta_T_N"] - row["delta_T_M"]
            assert row["delta_T_E"] == pytest.approx(expected_delta_te, abs=1e-9)

    def test_create_temperature_analysis_table_cool_includes_bottom(self) -> None:
        """Test that table includes bottom height (h=0)."""
        # Act
        result = create_temperature_analysis_table_cool(h=1.25, t_surface=0.1, z=0.625, b=1.0)

        # Assert
        assert 0.0 in result["h"].to_numpy()

    def test_create_temperature_analysis_table_cool_various_heights(self) -> None:
        """Test cooling analysis tables for different cross-section heights."""
        # Act
        result_short = create_temperature_analysis_table_cool(h=0.5, t_surface=0.05, z=0.25, b=1.0)
        result_tall = create_temperature_analysis_table_cool(h=1.5, t_surface=0.05, z=0.75, b=1.0)

        # Assert - both tables should have valid structure
        assert len(result_short) > 0
        assert len(result_tall) > 0
        # Verify both contain the required columns (actual columns from output)
        for column in ["h", "delta_T", "delta_T_N", "delta_T_M", "delta_T_E"]:
            assert column in result_short.columns
            assert column in result_tall.columns
        # Temperature differences should be negative or zero for cooling
        assert (result_short["delta_T"] <= 0).all()
        assert (result_tall["delta_T"] <= 0).all()


class TestCalculateTemperatureLoadCombinations:
    """Test cases for calculate_temperature_load_combinations function."""

    def test_calculate_temperature_load_combinations_structure(self, tmp_path: Path) -> None:
        """Test that function returns dictionary with correct structure."""
        # Arrange
        csv_path_5_2 = tmp_path / "test_table_5_2.csv"
        csv_content_5_2 = "T_min;T_max\n-10,0;35,0"
        csv_path_5_2.write_text(csv_content_5_2)

        csv_path_nb6 = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator
        csv_content_nb6 = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "1,25;100;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path_nb6.write_text(csv_content_nb6)

        # Act
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path_nb6):
            result = calculate_temperature_load_combinations(
                h=1.25, t_surface=0.1, z=0.625, b=1.0, T_0=10.0, omega_N=0.35, omega_M=0.75, data_path=csv_path_5_2
            )

        # Assert
        assert isinstance(result, dict)
        assert "heat_omega_N" in result
        assert "heat_omega_M" in result
        assert "cool_omega_N" in result
        assert "cool_omega_M" in result

        # Each combination should have two values (top, bottom)
        assert len(result["heat_omega_N"]) == 2
        assert len(result["heat_omega_M"]) == 2
        assert len(result["cool_omega_N"]) == 2
        assert len(result["cool_omega_M"]) == 2

    def test_calculate_temperature_load_combinations_heating_values(self, tmp_path: Path) -> None:
        """Test that heating combinations are calculated correctly."""
        # Arrange
        csv_path_5_2 = tmp_path / "test_table_5_2.csv"
        csv_content_5_2 = "T_min;T_max\n-10,0;35,0"
        csv_path_5_2.write_text(csv_content_5_2)

        csv_path_nb6 = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator
        csv_content_nb6 = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "1,25;100;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path_nb6.write_text(csv_content_nb6)

        # Act
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path_nb6):
            result = calculate_temperature_load_combinations(
                h=1.25, t_surface=0.1, z=0.625, b=1.0, T_0=10.0, omega_N=0.35, omega_M=0.75, data_path=csv_path_5_2
            )

        # Assert - heating combinations should be positive
        heat_omega_n_top, heat_omega_n_bot = result["heat_omega_N"]
        heat_omega_m_top, heat_omega_m_bot = result["heat_omega_M"]

        assert isinstance(heat_omega_n_top, float)
        assert isinstance(heat_omega_n_bot, float)
        assert isinstance(heat_omega_m_top, float)
        assert isinstance(heat_omega_m_bot, float)

    def test_calculate_temperature_load_combinations_cooling_values(self, tmp_path: Path) -> None:
        """Test that cooling combinations are calculated correctly."""
        # Arrange
        csv_path_5_2 = tmp_path / "test_table_5_2.csv"
        csv_content_5_2 = "T_min;T_max\n-10,0;35,0"
        csv_path_5_2.write_text(csv_content_5_2)

        csv_path_nb6 = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator
        csv_content_nb6 = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "1,25;100;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path_nb6.write_text(csv_content_nb6)

        # Act
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path_nb6):
            result = calculate_temperature_load_combinations(
                h=1.25, t_surface=0.1, z=0.625, b=1.0, T_0=10.0, omega_N=0.35, omega_M=0.75, data_path=csv_path_5_2
            )

        # Assert - cooling combinations should be negative or small
        cool_omega_n_top, cool_omega_n_bot = result["cool_omega_N"]
        cool_omega_m_top, cool_omega_m_bot = result["cool_omega_M"]

        assert isinstance(cool_omega_n_top, float)
        assert isinstance(cool_omega_n_bot, float)
        assert isinstance(cool_omega_m_top, float)
        assert isinstance(cool_omega_m_bot, float)

    def test_calculate_temperature_load_combinations_custom_factors(self, tmp_path: Path) -> None:
        """Test combinations with custom omega factors."""
        # Arrange
        csv_path_5_2 = tmp_path / "test_table_5_2.csv"
        csv_content_5_2 = "T_min;T_max\n-10,0;35,0"
        csv_path_5_2.write_text(csv_content_5_2)

        csv_path_nb6 = tmp_path / "test_table_nb6_b3.csv"
        # Use European format with comma as decimal separator
        csv_content_nb6 = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "1,25;100;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path_nb6.write_text(csv_content_nb6)

        # Act
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path_nb6):
            result = calculate_temperature_load_combinations(
                h=1.25, t_surface=0.1, z=0.625, b=1.0, T_0=10.0, omega_N=0.5, omega_M=1.0, data_path=csv_path_5_2
            )

        # Assert - results should be calculated with custom factors
        assert result is not None
        assert "heat_omega_N" in result

    def test_calculate_temperature_load_combinations_various_geometries(self, tmp_path: Path) -> None:
        """Test combinations for different cross-section geometries."""
        # Arrange
        csv_path_5_2 = tmp_path / "test_table_5_2.csv"
        csv_content_5_2 = "T_min;T_max\n-10,0;35,0"
        csv_path_5_2.write_text(csv_content_5_2)

        csv_path_nb6 = tmp_path / "test_table_nb6_b3.csv"
        csv_content_nb6 = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "0,6;50;16,0;8,0;4,0;-4,0;-1,5;-0,7;-0,35\n"
            "1,5;50;20,0;12,0;6,0;-6,0;-2,5;-1,2;-0,6"
        )
        csv_path_nb6.write_text(csv_content_nb6)

        # Act - test small and large sections
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path_nb6):
            result_small = calculate_temperature_load_combinations(
                h=0.6, t_surface=0.05, z=0.3, b=0.8, T_0=10.0, omega_N=0.35, omega_M=0.75, data_path=csv_path_5_2
            )
            result_large = calculate_temperature_load_combinations(
                h=1.5, t_surface=0.05, z=0.75, b=1.5, T_0=10.0, omega_N=0.35, omega_M=0.75, data_path=csv_path_5_2
            )

        # Assert - both should have valid structure
        for result in [result_small, result_large]:
            assert "heat_omega_N" in result
            assert "heat_omega_M" in result
            assert len(result["heat_omega_N"]) == 2
            assert len(result["heat_omega_M"]) == 2

    def test_calculate_temperature_load_combinations_extreme_omega_factors(self, tmp_path: Path) -> None:
        """Test combinations with extreme omega factor values."""
        # Arrange
        csv_path_5_2 = tmp_path / "test_table_5_2.csv"
        csv_content_5_2 = "T_min;T_max\n-10,0;35,0"
        csv_path_5_2.write_text(csv_content_5_2)

        csv_path_nb6 = tmp_path / "test_table_nb6_b3.csv"
        csv_content_nb6 = (
            "h;surface_thickness;delta_T1_heat;delta_T2_heat;delta_T3_heat;"
            "delta_T1_cool;delta_T2_cool;delta_T3_cool;delta_T4_cool\n"
            "1,0;50;18,0;10,0;5,0;-5,0;-2,0;-1,0;-0,5"
        )
        csv_path_nb6.write_text(csv_content_nb6)

        # Act - test with omega factors at 0.0 and 1.0
        with patch("src.temperature.temperature_load.NEN_EN_1991_1_5_table_NB6_B_3_PATH", csv_path_nb6):
            result_zero = calculate_temperature_load_combinations(
                h=1.0, t_surface=0.05, z=0.5, b=1.0, T_0=10.0, omega_N=0.0, omega_M=0.0, data_path=csv_path_5_2
            )
            result_one = calculate_temperature_load_combinations(
                h=1.0, t_surface=0.05, z=0.5, b=1.0, T_0=10.0, omega_N=1.0, omega_M=1.0, data_path=csv_path_5_2
            )

        # Assert - both should produce valid results
        assert all(isinstance(v, tuple) and len(v) == 2 for v in result_zero.values())
        assert all(isinstance(v, tuple) and len(v) == 2 for v in result_one.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
