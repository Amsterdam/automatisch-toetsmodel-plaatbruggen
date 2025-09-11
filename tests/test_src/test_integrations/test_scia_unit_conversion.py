"""
Test the centralized SCIA unit conversion system.

This module tests the new SciaUnitConverter class and ensures that
units mapping and value conversion stay in sync.
"""

from typing import Any

import pytest

from src.integrations.scia_integration.scia_unit_conversion import (
    SciaUnitConverter,
    UnitConversion,
    build_units_mapping,
    safe_float_format,
)


class TestUnitConversion:
    """Test the UnitConversion dataclass."""

    def test_unit_conversion_creation(self) -> None:
        """Test creating a UnitConversion object."""
        conversion = UnitConversion("kN", 1 / 1000, "N")

        assert conversion.display_unit == "kN"
        assert conversion.conversion_factor == 0.001
        assert conversion.raw_unit == "N"

    def test_unit_conversion_defaults(self) -> None:
        """Test UnitConversion with default raw_unit."""
        conversion = UnitConversion("kNm", 1 / 1000)

        assert conversion.display_unit == "kNm"
        assert conversion.conversion_factor == 0.001
        assert conversion.raw_unit == ""


class TestSciaUnitConverter:
    """Test the SciaUnitConverter class."""

    def test_1d_converter_creation(self) -> None:
        """Test creating a 1D converter."""
        converter = SciaUnitConverter("1D")

        assert converter.element_type == "1D"
        assert converter.get_display_unit("Vy") == "kN"
        assert converter.get_display_unit("Mx") == "kNm"

    def test_2d_converter_creation(self) -> None:
        """Test creating a 2D converter."""
        converter = SciaUnitConverter("2D")

        assert converter.element_type == "2D"
        assert converter.get_display_unit("v_x") == "kN/m"
        assert converter.get_display_unit("m_x") == "kNm/m"

    def test_value_conversion_1d(self) -> None:
        """Test value conversion for 1D elements."""
        converter = SciaUnitConverter("1D")

        # Test force conversion (N to kN)
        assert converter.convert_value(1000.0, "Vy") == 1.0
        assert converter.convert_value(500.0, "N") == 0.5

        # Test moment conversion (Nm to kNm)
        assert converter.convert_value(5000.0, "Mx") == 5.0
        assert converter.convert_value(2500.0, "Mxd+") == 2.5

    def test_value_conversion_2d(self) -> None:
        """Test value conversion for 2D elements."""
        converter = SciaUnitConverter("2D")

        # Test force conversion (N/m to kN/m)
        assert converter.convert_value(1000.0, "v_x") == 1.0
        assert converter.convert_value(500.0, "n_x") == 0.5

        # Test moment conversion (Nm/m to kNm/m)
        assert converter.convert_value(5000.0, "m_x") == 5.0
        assert converter.convert_value(2500.0, "m_xD+") == 2.5

    def test_format_value_with_unit(self) -> None:
        """Test formatting values with units."""
        converter = SciaUnitConverter("1D")

        # Test force formatting
        result = converter.format_value_with_unit(1000.0, "Vy")
        assert result == "1.0 kN"

        # Test moment formatting
        result = converter.format_value_with_unit(5000.0, "Mx", decimals=2)
        assert result == "5.00 kNm"

        # Test invalid value
        result = converter.format_value_with_unit("invalid", "Vy")
        assert result == "N/A"

        # Test custom default
        result = converter.format_value_with_unit(None, "Vy", default="--")  # type: ignore[arg-type]
        assert result == "--"

    def test_units_mapping(self) -> None:
        """Test getting units mapping."""
        converter_1d = SciaUnitConverter("1D")
        units_1d = converter_1d.get_units_mapping()

        assert units_1d["Vy"] == "kN"
        assert units_1d["Mx"] == "kNm"
        assert units_1d["Mxd+"] == "kNm"

        converter_2d = SciaUnitConverter("2D")
        units_2d = converter_2d.get_units_mapping()

        assert units_2d["v_x"] == "kN/m"
        assert units_2d["m_x"] == "kNm/m"
        assert units_2d["Vy"] == "kN/m"  # Standard naming for 2D

    def test_create_for_table_type(self) -> None:
        """Test creating converter based on table type."""
        # Test 2D table detection
        converter_2d = SciaUnitConverter.create_for_table_type("Internal Forces 2D")
        assert converter_2d.element_type == "2D"

        converter_2d_lower = SciaUnitConverter.create_for_table_type("internal forces 2d")
        assert converter_2d_lower.element_type == "2D"

        # Test 1D table detection
        converter_1d = SciaUnitConverter.create_for_table_type("Internal Forces 1D")
        assert converter_1d.element_type == "1D"

        # Test unknown table defaults to 1D
        converter_unknown = SciaUnitConverter.create_for_table_type("Unknown Table")
        assert converter_unknown.element_type == "1D"

        # Test None table defaults to 1D
        converter_none = SciaUnitConverter.create_for_table_type(None)
        assert converter_none.element_type == "1D"

    def test_fallback_units(self) -> None:
        """Test fallback unit detection for unknown components."""
        converter = SciaUnitConverter("1D")

        # Test moment-like component name
        assert converter.get_display_unit("unknown_moment") == "kNm"
        assert converter.get_display_unit("some_M_value") == "kNm"

        # Test force-like component name
        assert converter.get_display_unit("unknown_force") == "kN"
        assert converter.get_display_unit("some_V_value") == "kN"

        # Test 2D fallbacks
        converter_2d = SciaUnitConverter("2D")
        assert converter_2d.get_display_unit("unknown_moment") == "kNm/m"
        assert converter_2d.get_display_unit("unknown_force") == "kN/m"

    def test_conversion_error_handling(self) -> None:
        """Test error handling in value conversion."""
        converter = SciaUnitConverter("1D")

        # Test invalid value types
        with pytest.raises(ValueError, match="Cannot convert value"):
            converter.convert_value("invalid", "Vy")

        with pytest.raises(ValueError, match="Cannot convert value"):
            converter.convert_value(None, "Vy")  # type: ignore[arg-type]


class TestCentralizedBuildUnitsMapping:
    """Test the centralized build_units_mapping function."""

    def test_2d_table_units_mapping(self) -> None:
        """Test units mapping for 2D table."""
        results = {"internal_forces": {"table_name": "Internal Forces 2D"}}
        units = build_units_mapping(results)

        assert units["internal_forces"]["Vy"] == "kN/m"
        assert units["internal_forces"]["m_x"] == "kNm/m"
        assert units["internal_forces"]["Mxd+"] == "kNm/m"

    def test_1d_table_units_mapping(self) -> None:
        """Test units mapping for 1D table."""
        results = {"internal_forces": {"table_name": "Internal Forces 1D"}}
        units = build_units_mapping(results)

        assert units["internal_forces"]["Vy"] == "kN"
        assert units["internal_forces"]["Mx"] == "kNm"
        assert units["internal_forces"]["Mxd+"] == "kNm"

    def test_unknown_table_defaults_to_1d(self) -> None:
        """Test that unknown table types default to 1D."""
        results = {"internal_forces": {"table_name": "Unknown Table"}}
        units = build_units_mapping(results)

        assert units["internal_forces"]["Vy"] == "kN"
        assert units["internal_forces"]["Mx"] == "kNm"

    def test_missing_internal_forces(self) -> None:
        """Test behavior with missing internal forces."""
        results: dict[str, Any] = {}
        units = build_units_mapping(results)

        # Should default to 1D
        assert units["internal_forces"]["Vy"] == "kN"
        assert units["internal_forces"]["Mx"] == "kNm"


class TestBackwardCompatibility:
    """Test backward compatibility of the centralized system."""

    def test_safe_float_format_compatibility(self) -> None:
        """Test that safe_float_format maintains backward compatibility."""
        # Test force conversion
        result = safe_float_format(1000.0, "kN")
        assert result == "1.0 kN"

        # Test moment conversion
        result = safe_float_format(5000.0, "kNm")
        assert result == "5.0 kNm"

        # Test non-force units (should not be converted)
        result = safe_float_format(123.45, "mm")
        assert result == "123.5 mm"

        # Test error cases
        result = safe_float_format(None, "kN")  # type: ignore[arg-type]
        assert result == "N/A"

        result = safe_float_format("invalid", "kNm", "CUSTOM")
        assert result == "CUSTOM"

    def test_per_meter_units_conversion(self) -> None:
        """Test conversion of per-meter units."""
        # Test kN/m conversion
        result = safe_float_format(2000.0, "kN/m")
        assert result == "2.0 kN/m"

        # Test kNm/m conversion
        result = safe_float_format(8000.0, "kNm/m")
        assert result == "8.0 kNm/m"


class TestIntegrationConsistency:
    """Test that the centralized system provides consistent results."""

    def test_units_and_conversion_consistency_1d(self) -> None:
        """Test that units mapping and conversion are consistent for 1D."""
        converter = SciaUnitConverter("1D")

        # Test a force component
        unit = converter.get_display_unit("Vy")
        converted_value = converter.convert_value(1000.0, "Vy")
        formatted = converter.format_value_with_unit(1000.0, "Vy")

        assert unit == "kN"
        assert converted_value == 1.0
        assert formatted == "1.0 kN"

        # Test a moment component
        unit = converter.get_display_unit("Mx")
        converted_value = converter.convert_value(5000.0, "Mx")
        formatted = converter.format_value_with_unit(5000.0, "Mx")

        assert unit == "kNm"
        assert converted_value == 5.0
        assert formatted == "5.0 kNm"

    def test_units_and_conversion_consistency_2d(self) -> None:
        """Test that units mapping and conversion are consistent for 2D."""
        converter = SciaUnitConverter("2D")

        # Test a force component
        unit = converter.get_display_unit("v_x")
        converted_value = converter.convert_value(1000.0, "v_x")
        formatted = converter.format_value_with_unit(1000.0, "v_x")

        assert unit == "kN/m"
        assert converted_value == 1.0
        assert formatted == "1.0 kN/m"

        # Test a moment component
        unit = converter.get_display_unit("m_x")
        converted_value = converter.convert_value(5000.0, "m_x")
        formatted = converter.format_value_with_unit(5000.0, "m_x")

        assert unit == "kNm/m"
        assert converted_value == 5.0
        assert formatted == "5.0 kNm/m"

    def test_build_units_mapping_consistency(self) -> None:
        """Test that build_units_mapping provides consistent results."""
        # Test 2D mapping
        results_2d = {"internal_forces": {"table_name": "Internal Forces 2D"}}
        units_2d = build_units_mapping(results_2d)
        converter_2d = SciaUnitConverter.create_for_table_type("Internal Forces 2D")
        converter_units_2d = converter_2d.get_units_mapping()

        # Key components should match
        for component in ["v_x", "m_x", "Vy", "Mxd+"]:
            assert units_2d["internal_forces"][component] == converter_units_2d[component]

        # Test 1D mapping
        results_1d = {"internal_forces": {"table_name": "Internal Forces 1D"}}
        units_1d = build_units_mapping(results_1d)
        converter_1d = SciaUnitConverter.create_for_table_type("Internal Forces 1D")
        converter_units_1d = converter_1d.get_units_mapping()

        # Key components should match
        for component in ["Vy", "Mx", "Mxd+"]:
            assert units_1d["internal_forces"][component] == converter_units_1d[component]
