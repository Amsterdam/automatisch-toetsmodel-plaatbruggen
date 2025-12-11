"""
Test unit conversion and width correction for integration strip results.

This module tests:
1. Unit conversion from N to kN and Nm to kNm
2. Width correction for strips with width != 1.0 m
3. Correction indicator column
"""

import pandas as pd
import pytest

from src.integrations.scia_integration.results.scia_integration_strips_processor import (
    add_parsed_columns_to_dataframe,
    parse_strip_name,
)
from src.integrations.scia_integration.results.scia_integration_strips_views import (
    _format_integration_strip_table_data,
)


class TestStripNameParsing:
    """Test parsing of integration strip names."""

    def test_parse_strip_name_complete(self) -> None:
        """Test parsing a complete strip name."""
        strip_name = "strip_dir-x_reg_Z1-1_w-1.0_nr-1"
        result = parse_strip_name(strip_name)

        assert result["direction"] == "x"
        assert result["strip_type"] == "reg"
        assert result["zone"] == "Z1-1"
        assert result["width"] == "1.0"
        assert result["number"] == "1"

    def test_parse_strip_name_width_not_one(self) -> None:
        """Test parsing strip name with width != 1.0."""
        strip_name = "strip_dir-y_sup_Z2-3_w-2.5_nr-5"
        result = parse_strip_name(strip_name)

        assert result["direction"] == "y"
        assert result["strip_type"] == "sup"
        assert result["zone"] == "Z2-3"
        assert result["width"] == "2.5"
        assert result["number"] == "5"

    def test_parse_strip_name_partial(self) -> None:
        """Test parsing incomplete strip name."""
        strip_name = "strip_dir-x_Z1-1"
        result = parse_strip_name(strip_name)

        assert result["direction"] == "x"
        assert result["zone"] == "Z1-1"
        assert result["strip_type"] == ""
        assert result["width"] == ""
        assert result["number"] == ""


class TestWidthCorrection:
    """Test width correction for integration strips."""

    def test_width_correction_applied(self) -> None:
        """Test that width correction is applied when width != 1.0."""
        # Create test dataframe with width = 2.0
        df = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_w-2.0_nr-1"],
                "dx": [0.5],
                "load_case": ["LC1"],
                "N": [2000.0],  # N
                "V_y": [4000.0],  # N
                "V_z": [6000.0],  # N
                "M_x": [8000.0],  # Nm
                "M_y": [10000.0],  # Nm
                "M_z": [12000.0],  # Nm
            }
        )

        # Apply parsing and correction
        df = add_parsed_columns_to_dataframe(df)

        # Check that corrected flag is set
        assert df.at[0, "corrected"]

        # Check that values are divided by width (2.0)
        assert df.at[0, "N"] == pytest.approx(1000.0)
        assert df.at[0, "V_y"] == pytest.approx(2000.0)
        assert df.at[0, "V_z"] == pytest.approx(3000.0)
        assert df.at[0, "M_x"] == pytest.approx(4000.0)
        assert df.at[0, "M_y"] == pytest.approx(5000.0)
        assert df.at[0, "M_z"] == pytest.approx(6000.0)

    def test_width_correction_not_applied_for_width_one(self) -> None:
        """Test that width correction is NOT applied when width = 1.0."""
        # Create test dataframe with width = 1.0
        df = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_w-1.0_nr-1"],
                "dx": [0.5],
                "load_case": ["LC1"],
                "N": [2000.0],
                "V_y": [4000.0],
                "V_z": [6000.0],
                "M_x": [8000.0],
                "M_y": [10000.0],
                "M_z": [12000.0],
            }
        )

        # Apply parsing and correction
        df = add_parsed_columns_to_dataframe(df)

        # Check that corrected flag is NOT set
        assert not df.at[0, "corrected"]

        # Check that values are NOT changed
        assert df.at[0, "N"] == pytest.approx(2000.0)
        assert df.at[0, "V_y"] == pytest.approx(4000.0)
        assert df.at[0, "V_z"] == pytest.approx(6000.0)
        assert df.at[0, "M_x"] == pytest.approx(8000.0)
        assert df.at[0, "M_y"] == pytest.approx(10000.0)
        assert df.at[0, "M_z"] == pytest.approx(12000.0)

    def test_width_correction_with_missing_width(self) -> None:
        """Test that no correction is applied when width is missing."""
        # Create test dataframe without width in name
        df = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_nr-1"],
                "dx": [0.5],
                "load_case": ["LC1"],
                "N": [2000.0],
                "V_y": [4000.0],
                "V_z": [6000.0],
            }
        )

        # Apply parsing and correction
        df = add_parsed_columns_to_dataframe(df)

        # Check that corrected flag is NOT set
        assert not df.at[0, "corrected"]

        # Check that values are NOT changed
        assert df.at[0, "N"] == pytest.approx(2000.0)
        assert df.at[0, "V_y"] == pytest.approx(4000.0)


class TestUnitConversionInViews:
    """Test unit conversion in view formatting."""

    def test_format_with_unit_conversion_and_correction(self) -> None:
        """Test that formatting applies both unit conversion and shows correction status."""
        # Create test dataframe with width correction applied
        df = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_w-2.0_nr-1"],
                "dx": [0.5],
                "load_case": ["LC1"],
                "N": [1000.0],  # Already corrected, in N
                "V_y": [2000.0],  # Already corrected, in N
                "V_z": [3000.0],  # Already corrected, in N
                "M_x": [4000.0],  # Already corrected, in Nm
                "M_y": [5000.0],  # Already corrected, in Nm
                "M_z": [6000.0],  # Already corrected, in Nm
                "corrected": [True],
                "zone": ["Z1-1"],
                "direction": ["x"],
                "strip_type": ["reg"],
                "strip_number": ["1"],
            }
        )

        # Format for display
        data = _format_integration_strip_table_data(df)

        # Check that we have one row
        assert len(data) == 1
        row = data[0]

        # Check unit conversion: N to kN (divide by 1000)
        assert row[3] == "1.00"  # N: 1000 N -> 1.00 kN
        assert row[4] == "2.00"  # V_y: 2000 N -> 2.00 kN
        assert row[5] == "3.00"  # V_z: 3000 N -> 3.00 kN

        # Check unit conversion: Nm to kNm (divide by 1000)
        assert row[6] == "4.00"  # M_x: 4000 Nm -> 4.00 kNm
        assert row[7] == "5.00"  # M_y: 5000 Nm -> 5.00 kNm
        assert row[8] == "6.00"  # M_z: 6000 Nm -> 6.00 kNm

        # Check correction indicator
        assert row[9] == "Ja"

    def test_format_without_correction(self) -> None:
        """Test formatting for strips without width correction."""
        # Create test dataframe without correction
        df = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_w-1.0_nr-1"],
                "dx": [0.5],
                "load_case": ["LC1"],
                "N": [1000.0],
                "V_y": [2000.0],
                "V_z": [3000.0],
                "M_x": [4000.0],
                "M_y": [5000.0],
                "M_z": [6000.0],
                "corrected": [False],
                "zone": ["Z1-1"],
                "direction": ["x"],
                "strip_type": ["reg"],
                "strip_number": ["1"],
            }
        )

        # Format for display
        data = _format_integration_strip_table_data(df)

        # Check correction indicator
        assert data[0][9] == "Nee"

    def test_format_empty_dataframe(self) -> None:
        """Test formatting an empty dataframe."""
        df = pd.DataFrame()
        data = _format_integration_strip_table_data(df)

        # Should return "No data" message
        assert len(data) == 1
        assert data[0][0] == "Geen data"

    def test_large_values_unit_conversion(self) -> None:
        """Test unit conversion with large values."""
        # Create test dataframe with large values
        df = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_w-1.0_nr-1"],
                "dx": [0.5],
                "load_case": ["LC1"],
                "N": [1000000.0],  # 1000 kN
                "V_y": [500000.0],  # 500 kN
                "V_z": [0.0],
                "M_x": [2000000.0],  # 2000 kNm
                "M_y": [0.0],
                "M_z": [0.0],
                "corrected": [False],
                "zone": ["Z1-1"],
                "direction": ["x"],
                "strip_type": ["reg"],
                "strip_number": ["1"],
            }
        )

        # Format for display
        data = _format_integration_strip_table_data(df)

        # Check unit conversion
        assert data[0][3] == "1000.00"  # 1000000 N -> 1000.00 kN
        assert data[0][4] == "500.00"  # 500000 N -> 500.00 kN
        assert data[0][6] == "2000.00"  # 2000000 Nm -> 2000.00 kNm


class TestIntegratedWorkflow:
    """Test the complete workflow from parsing to formatting."""

    def test_complete_workflow_with_width_correction(self) -> None:
        """Test complete workflow: parse name, apply correction, format with unit conversion."""
        # Create raw dataframe as it would come from SCIA
        df = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_w-2.0_nr-1"],
                "dx": [1.0],
                "load_case": ["ULS_LC1"],
                "N": [4000.0],  # N - total over 2.0m width
                "V_y": [8000.0],  # N - total over 2.0m width
                "V_z": [12000.0],  # N - total over 2.0m width
                "M_x": [16000.0],  # Nm - total over 2.0m width
                "M_y": [20000.0],  # Nm - total over 2.0m width
                "M_z": [24000.0],  # Nm - total over 2.0m width
            }
        )

        # Step 1: Apply parsing and width correction
        df = add_parsed_columns_to_dataframe(df)

        # Verify correction was applied (divide by 2.0)
        assert df.at[0, "corrected"]
        assert df.at[0, "N"] == pytest.approx(2000.0)  # 4000 / 2.0
        assert df.at[0, "M_x"] == pytest.approx(8000.0)  # 16000 / 2.0

        # Step 2: Format for display (with unit conversion)
        data = _format_integration_strip_table_data(df)

        # Verify unit conversion was applied (divide by 1000)
        assert data[0][3] == "2.00"  # 2000 N -> 2.00 kN
        assert data[0][4] == "4.00"  # 4000 N -> 4.00 kN (8000 / 2 / 1000)
        assert data[0][5] == "6.00"  # 6000 N -> 6.00 kN (12000 / 2 / 1000)
        assert data[0][6] == "8.00"  # 8000 Nm -> 8.00 kNm (16000 / 2 / 1000)
        assert data[0][7] == "10.00"  # 10000 Nm -> 10.00 kNm (20000 / 2 / 1000)
        assert data[0][8] == "12.00"  # 12000 Nm -> 12.00 kNm (24000 / 2 / 1000)

        # Verify correction indicator
        assert data[0][9] == "Ja"
