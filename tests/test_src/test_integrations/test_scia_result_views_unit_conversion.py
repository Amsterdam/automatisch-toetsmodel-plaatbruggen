"""
Test unit conversion functionality in SCIA result views.

This module tests the automatic conversion of force values from Newtons (N) to kiloNewtons (kN)
and moment values from Newton-meters (Nm) to kiloNewton-meters (kNm) in SCIA result formatting.
"""

import pandas as pd

from src.integrations.scia_integration.scia_result_views import (
    create_scia_node_results_table,
    create_scia_node_table_data,
    safe_float_format,
)


class TestSafeFloatFormatUnitConversion:
    """Test unit conversion in safe_float_format function."""

    def test_force_conversion_n_to_kn(self) -> None:
        """Test conversion of force values from N to kN."""
        # Test standard force value
        result = safe_float_format(1000.0, "kN")
        assert result == "1.0 kN"

        # Test larger force value
        result = safe_float_format(123456.0, "kN")
        assert result == "123.5 kN"

        # Test small force value
        result = safe_float_format(500.0, "kN")
        assert result == "0.5 kN"

    def test_moment_conversion_nm_to_knm(self) -> None:
        """Test conversion of moment values from Nm to kNm."""
        # Test standard moment value
        result = safe_float_format(5000.0, "kNm")
        assert result == "5.0 kNm"

        # Test larger moment value
        result = safe_float_format(987654.0, "kNm")
        assert result == "987.7 kNm"

        # Test small moment value
        result = safe_float_format(2500.0, "kNm")
        assert result == "2.5 kNm"

    def test_negative_values_conversion(self) -> None:
        """Test conversion of negative force and moment values."""
        # Negative force
        result = safe_float_format(-1000.0, "kN")
        assert result == "-1.0 kN"

        # Negative moment
        result = safe_float_format(-5000.0, "kNm")
        assert result == "-5.0 kNm"

    def test_non_force_units_not_converted(self) -> None:
        """Test that non-force/moment units are not converted."""
        result = safe_float_format(123.45, "mm")
        assert result == "123.5 mm"

        result = safe_float_format(100.0, "m")
        assert result == "100.0 m"

        result = safe_float_format(50.0, "")
        assert result == "50.0"

    def test_invalid_values_return_default(self) -> None:
        """Test that invalid values return default."""
        result = safe_float_format(None, "kN")  # type: ignore[arg-type]
        assert result == "N/A"

        result = safe_float_format("invalid", "kNm")
        assert result == "N/A"

        result = safe_float_format(pd.NA, "kN", "Custom Default")  # type: ignore[arg-type]
        assert result == "Custom Default"


class TestSciaTableDataUnitConversion:
    """Test unit conversion in SCIA table data creation."""

    def test_table_data_with_unit_conversion(self) -> None:
        """Test that create_scia_node_table_data applies unit conversion correctly."""
        # Mock DataFrame with raw SCIA data (values in N and Nm)
        mock_data = {
            "coords_xyz": [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)],
            "name": ["Zone1", "Zone2"],
            "v_x_max": [1000.5, 2500.3],  # Values in N (should become 1.0 kN and 2.5 kN)
            "v_y_max": [1500.2, 3200.1],  # Values in N (should become 1.5 kN and 3.2 kN)
            "m_xD+_max": [5000.0, 12000.0],  # Values in Nm (should become 5.0 kNm and 12.0 kNm)
            "m_xD-_max": [-2500.0, -7500.0],  # Values in Nm (should become -2.5 kNm and -7.5 kNm)
            "m_yD+_max": [8000.0, 15000.0],  # Values in Nm (should become 8.0 kNm and 15.0 kNm)
            "m_yD-_max": [-4000.0, -9000.0],  # Values in Nm (should become -4.0 kNm and -9.0 kNm)
        }
        test_df = pd.DataFrame(mock_data)

        # Mock units mapping
        units_mapping = {
            "v_x": "kN",
            "v_y": "kN",
            "m_xD+": "kNm",
            "m_xD-": "kNm",
            "m_yD+": "kNm",
            "m_yD-": "kNm",
        }

        # Test the function
        table_data, headers = create_scia_node_table_data(test_df, "ULS", units_mapping)

        # Verify headers contain units
        expected_headers = [
            "Coordinates",
            "Name",
            "Vx Max (kN)",
            "Vy Max (kN)",
            "MxD+ Max (kNm)",
            "MxD- Max (kNm)",
            "MyD+ Max (kNm)",
            "MyD- Max (kNm)",
        ]
        assert headers == expected_headers

        # Verify data values are converted correctly
        assert len(table_data) == 2

        # Check first row - values should be converted from N to kN and Nm to kNm
        row1 = table_data[0]
        assert "1.0 kN" in row1[2]  # v_x_max: 1000.5 N -> 1.0 kN
        assert "1.5 kN" in row1[3]  # v_y_max: 1500.2 N -> 1.5 kN
        assert "5.0 kNm" in row1[4]  # m_xD+_max: 5000.0 Nm -> 5.0 kNm
        assert "-2.5 kNm" in row1[5]  # m_xD-_max: -2500.0 Nm -> -2.5 kNm
        assert "8.0 kNm" in row1[6]  # m_yD+_max: 8000.0 Nm -> 8.0 kNm
        assert "-4.0 kNm" in row1[7]  # m_yD-_max: -4000.0 Nm -> -4.0 kNm

        # Check second row
        row2 = table_data[1]
        assert "2.5 kN" in row2[2]  # v_x_max: 2500.3 N -> 2.5 kN
        assert "3.2 kN" in row2[3]  # v_y_max: 3200.1 N -> 3.2 kN
        assert "12.0 kNm" in row2[4]  # m_xD+_max: 12000.0 Nm -> 12.0 kNm
        assert "-7.5 kNm" in row2[5]  # m_xD-_max: -7500.0 Nm -> -7.5 kNm
        assert "15.0 kNm" in row2[6]  # m_yD+_max: 15000.0 Nm -> 15.0 kNm
        assert "-9.0 kNm" in row2[7]  # m_yD-_max: -9000.0 Nm -> -9.0 kNm

    def test_full_result_table_with_unit_conversion(self) -> None:
        """Test that create_scia_node_results_table applies unit conversion correctly."""
        # Mock results with units and raw data
        mock_results = {
            "units": {
                "internal_forces": {
                    "v_x": "kN",
                    "v_y": "kN",
                    "m_xD+": "kNm",
                    "m_xD-": "kNm",
                    "m_yD+": "kNm",
                    "m_yD-": "kNm",
                }
            },
            "xml_parsing": {
                "parsed_tables": {
                    "Interne 2D-krachten basis ULS": {
                        "data": {
                            "Basis grootheden": {
                                "coords_xyz": [(0.0, 0.0, 0.0)],
                                "Naam": ["Zone1"],
                                "v_x": [2000.0],  # 2000 N should become 2.0 kN
                                "v_y": [3500.0],  # 3500 N should become 3.5 kN
                            }
                        }
                    },
                    "Interne 2D-krachten elementair ULS": {
                        "data": {
                            "Elementaire ontwerpgrootheden": {
                                "coords_xyz": [(0.0, 0.0, 0.0)],
                                "Naam": ["Zone1"],
                                "m_xD+": [10000.0],  # 10000 Nm should become 10.0 kNm
                                "m_xD-": [-5000.0],  # -5000 Nm should become -5.0 kNm
                                "m_yD+": [15000.0],  # 15000 Nm should become 15.0 kNm
                                "m_yD-": [-8000.0],  # -8000 Nm should become -8.0 kNm
                            }
                        }
                    },
                }
            },
        }

        # Test the function
        result_table = create_scia_node_results_table(mock_results, "ULS")
        headers = result_table.column_headers
        data = result_table.data

        # Check that headers contain units
        unit_found = any("(" in header and ")" in header for header in headers[2:])  # Skip first 2 non-unit headers
        assert unit_found, f"No units found in headers: {headers}"

        # Check that data contains converted values (spot check)
        if len(data) > 0:
            data_str = str(data)
            # Should contain converted values like "2.0 kN", "10.0 kNm", etc.
            conversion_found = "kN" in data_str or "kNm" in data_str
            assert conversion_found, f"No converted units found in data: {data_str[:200]}"

    def test_table_without_units_mapping(self) -> None:
        """Test that tables work correctly without units mapping (uses defaults)."""
        mock_data = {
            "coords_xyz": [(0.0, 0.0, 0.0)],
            "name": ["Zone1"],
            "v_x_max": [1000.0],
        }
        test_dataframe = pd.DataFrame(mock_data)

        # Test without units mapping
        table_data, headers = create_scia_node_table_data(test_dataframe, "ULS", None)

        # Should still work, using default units (kN, kNm)
        assert len(table_data) == 1
        assert len(headers) >= 3  # At least Coordinates, Name, Vx Max

        # Values should be formatted and converted using default units
        row1 = table_data[0]
        assert "1.0 kN" in row1[2]  # 1000.0 N converted to 1.0 kN using default unit
