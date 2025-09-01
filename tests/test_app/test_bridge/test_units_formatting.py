"""Tests for units formatting in bridge controller."""

import unittest

from app.bridge.controller import BridgeController


class TestUnitsFormatting(unittest.TestCase):
    """Test units formatting in the bridge controller."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = BridgeController()

    def test_format_complete_force_state_with_units(self) -> None:
        """Test that _format_complete_force_state correctly applies units."""
        forces = {
            "Vy": 12.3,
            "Myd+": 5.0,
            "N": 100.5,
        }
        units_mapping = {
            "Vy": "kN/m",
            "Myd+": "kNm/m",
            "N": "kN/m",
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that units are properly appended
        assert "Vy=12 kN/m" in result
        assert "My+=5 kNm/m" in result
        assert "N=100 kN/m" in result

    def test_format_complete_force_state_without_units(self) -> None:
        """Test that _format_complete_force_state works without units mapping."""
        forces = {
            "Vy": 12.3,
            "Myd+": 5.0,
        }

        result = self.controller._format_complete_force_state(forces, None)

        # Check that values are shown without units
        assert "Vy=12" in result
        assert "My+=5" in result
        # Should not have trailing spaces
        assert " |" not in result or not result.endswith(" ")

    def test_format_complete_force_state_empty_units_mapping(self) -> None:
        """Test that _format_complete_force_state works with empty units mapping."""
        forces = {
            "Vy": 12.3,
            "Myd+": 5.0,
        }
        units_mapping: dict[str, str] = {}

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that values are shown without units
        assert "Vy=12" in result
        assert "My+=5" in result

    def test_format_complete_force_state_partial_units_mapping(self) -> None:
        """Test that _format_complete_force_state handles partial units mapping."""
        forces = {
            "Vy": 12.3,
            "Myd+": 5.0,
            "N": 100.5,
        }
        units_mapping = {
            "Vy": "kN/m",
            # Missing Myd+ and N units
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that only Vy has units, others don't
        assert "Vy=12 kN/m" in result
        assert "My+=5" in result
        assert "N=100" in result
        # Check that units are not added where they shouldn't be
        assert "My+=5 kNm" not in result  # No unit for Myd+
        assert "N=100 kN" not in result  # No unit for N

    def test_format_complete_force_state_filters_small_values(self) -> None:
        """Test that _format_complete_force_state filters out small values."""
        forces = {
            "Vy": 12.3,  # Should be included
            "Myd+": 0.05,  # Should be filtered (< 0.1)
            "N": 0.0,  # Should be filtered
            "Vz": -0.08,  # Should be filtered (abs < 0.1)
            "Mxd+": 150.0,  # Should be included
        }
        units_mapping = {
            "Vy": "kN",
            "Myd+": "kNm",
            "N": "kN",
            "Vz": "kN",
            "Mxd+": "kNm",
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that only significant values are included
        assert "Vy=12 kN" in result
        assert "Mx+=150 kNm" in result

        # Check that small values are filtered out
        assert "My+" not in result
        assert "N=" not in result
        assert "Vz=" not in result

    def test_format_complete_force_state_all_small_values(self) -> None:
        """Test that _format_complete_force_state returns 'All ≈ 0' for all small values."""
        forces = {
            "Vy": 0.05,
            "Myd+": 0.02,
            "N": 0.0,
        }
        units_mapping = {
            "Vy": "kN",
            "Myd+": "kNm",
            "N": "kN",
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        assert result == "All ≈ 0"

    def test_format_complete_force_state_all_force_components(self) -> None:
        """Test that _format_complete_force_state handles all expected force components."""
        forces = {
            "N": 100.0,
            "Vy": 50.0,
            "Vz": 25.0,
            "Mxd+": 200.0,
            "Mxd-": -150.0,
            "Myd+": 300.0,
            "Myd-": -250.0,
        }
        units_mapping = {
            "N": "kN",
            "Vy": "kN",
            "Vz": "kN",
            "Mxd+": "kNm",
            "Mxd-": "kNm",
            "Myd+": "kNm",
            "Myd-": "kNm",
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that all components are included with correct labels
        assert "N=100 kN" in result
        assert "Vy=50 kN" in result
        assert "Vz=25 kN" in result
        assert "Mx+=200 kNm" in result
        assert "Mx-=-150 kNm" in result  # Note: negative value preserved
        assert "My+=300 kNm" in result
        assert "My-=-250 kNm" in result  # Note: negative value preserved

    def test_format_complete_force_state_2d_plate_units(self) -> None:
        """Test that _format_complete_force_state works with 2D plate units."""
        forces = {
            "N": 50.0,
            "Vy": 25.0,
            "Myd+": 100.0,
        }
        units_mapping = {
            "N": "kN/m",  # 2D plate units
            "Vy": "kN/m",
            "Myd+": "kNm/m",
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that 2D units are properly applied
        assert "N=50 kN/m" in result
        assert "Vy=25 kN/m" in result
        assert "My+=100 kNm/m" in result

    def test_format_complete_force_state_mixed_units(self) -> None:
        """Test that _format_complete_force_state handles mixed unit types."""
        forces = {
            "N": 50.0,
            "Vy": 25.0,
            "Myd+": 100.0,
        }
        units_mapping = {
            "N": "kN",  # 1D unit
            "Vy": "kN/m",  # 2D unit
            "Myd+": "kNm/m",  # 2D unit
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that mixed units are properly applied
        assert "N=50 kN" in result
        assert "Vy=25 kN/m" in result
        assert "My+=100 kNm/m" in result

    def test_format_complete_force_state_rounding(self) -> None:
        """Test that _format_complete_force_state properly rounds values."""
        forces = {
            "N": 123.456,
            "Vy": 78.912,
            "Myd+": 45.678,
        }
        units_mapping = {
            "N": "kN",
            "Vy": "kN",
            "Myd+": "kNm",
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that values are rounded to integers
        assert "N=123 kN" in result
        assert "Vy=79 kN" in result
        assert "My+=46 kNm" in result

    def test_format_complete_force_state_separator(self) -> None:
        """Test that _format_complete_force_state uses correct separator."""
        forces = {
            "N": 100.0,
            "Vy": 50.0,
            "Myd+": 200.0,
        }
        units_mapping = {
            "N": "kN",
            "Vy": "kN",
            "Myd+": "kNm",
        }

        result = self.controller._format_complete_force_state(forces, units_mapping)

        # Check that components are separated by " | "
        parts = result.split(" | ")
        assert len(parts) == 3
        assert "N=100 kN" in parts
        assert "Vy=50 kN" in parts
        assert "My+=200 kNm" in parts


if __name__ == "__main__":
    unittest.main()
