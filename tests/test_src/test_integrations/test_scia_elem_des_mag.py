"""
Tests for SCIA elementary design magnitudes calculations.

This module tests the functions in src.integrations.scia_integration.results.scia_elem_des_mag
using real data from SCIA analysis results.
"""

import pytest

from src.integrations.scia_integration.results.scia_elem_des_mag import (
    mxd_minus,
    mxd_plus,
    myd_minus,
    myd_plus,
    nxd,
    nyd,
)


class TestSciaElemDesMagWithRealData:
    """Test cases for SCIA elementary design magnitude calculations using real SCIA data.
    
    Test data from element 7 at position (1.630, 2.000, 0.000) for span_1_x_sec_2_3.
    """

    @pytest.fixture
    def test_cases(self):
        """Provide test case data from SCIA analysis results.
        
        Returns:
            List of dictionaries containing:
            - load_case: Name of the load case
            - mx, my, mxy: Moment values in kNm/m
            - vx, vy: Shear forces in kN/m
            - nx, ny, nxy: Normal and shear forces in kN/m
            - Expected output values: mxd_plus, mxd_minus, myd_plus, myd_minus, nxd, nyd
        """
        return [
            {
                "load_case": "6.10b gr1a - Config A/170",
                "mx": -39.39,
                "my": -15.35,
                "mxy": 4.99,
                "vx": 80.87,
                "vy": 7.16,
                "nx": 1302.67,
                "ny": 268.27,
                "nxy": -178.57,
                "expected_mxd_plus": -62.14,
                "expected_mxd_minus": 19.25,
                "expected_myd_plus": -25.82,
                "expected_myd_minus": 5.56,
                "expected_nxd": 1823.56,
                "expected_nyd": 452.68,
            },
            {
                "load_case": "6.10b gr1a - Config A/171",
                "mx": -20.65,
                "my": -8.13,
                "mxy": 0.95,
                "vx": 78.47,
                "vy": 5.26,
                "nx": 372.92,
                "ny": 100.80,
                "nxy": -83.49,
                "expected_mxd_plus": -64.16,
                "expected_mxd_minus": 42.55,
                "expected_myd_plus": -25.63,
                "expected_myd_minus": 16.55,
                "expected_nxd": 782.93,
                "expected_nyd": 194.66,
            },
            {
                "load_case": "6.10b gr1a - Config A/172",
                "mx": 26.58,
                "my": 18.20,
                "mxy": -19.41,
                "vx": 67.18,
                "vy": -6.51,
                "nx": -1330.07,
                "ny": -173.07,
                "nxy": 155.27,
                "expected_mxd_plus": -7.80,
                "expected_mxd_minus": 46.79,
                "expected_myd_plus": -7.22,
                "expected_myd_minus": 40.40,
                "expected_nxd": 166.60,
                "expected_nyd": -144.47,
            },
            {
                "load_case": "6.10b gr1a - Config A/173",
                "mx": -32.76,
                "my": -9.02,
                "mxy": 3.32,
                "vx": 78.61,
                "vy": 6.53,
                "nx": 2010.66,
                "ny": 312.13,
                "nxy": -242.41,
                "expected_mxd_plus": -56.63,
                "expected_mxd_minus": 22.02,
                "expected_myd_plus": -22.33,
                "expected_myd_minus": 10.09,
                "expected_nxd": 2424.75,
                "expected_nyd": 562.27,
            },
            {
                "load_case": "6.10b gr1a - Config A/174",
                "mx": -21.61,
                "my": -10.59,
                "mxy": -3.07,
                "vx": 73.98,
                "vy": 4.45,
                "nx": 877.94,
                "ny": 213.35,
                "nxy": -121.73,
                "expected_mxd_plus": -47.08,
                "expected_mxd_minus": 24.79,
                "expected_myd_plus": -20.54,
                "expected_myd_minus": 8.82,
                "expected_nxd": 1154.52,
                "expected_nyd": 337.71,
            },
            {
                "load_case": "6.10b gr1a - Config A/175",
                "mx": -54.56,
                "my": -20.32,
                "mxy": 8.09,
                "vx": 82.03,
                "vy": 9.62,
                "nx": 1562.73,
                "ny": 203.39,
                "nxy": -180.84,
                "expected_mxd_plus": -62.64,
                "expected_mxd_minus": 0.48,
                "expected_myd_plus": -28.40,
                "expected_myd_minus": 0.00,
                "expected_nxd": 1743.57,
                "expected_nyd": 384.23,
            },
            {
                "load_case": "6.10b gr1a - Config A/176",
                "mx": -4.01,
                "my": -6.34,
                "mxy": -8.73,
                "vx": 70.67,
                "vy": 2.19,
                "nx": -465.02,
                "ny": -6.06,
                "nxy": 60.90,
                "expected_mxd_plus": -37.44,
                "expected_mxd_minus": 37.63,
                "expected_myd_plus": -24.29,
                "expected_myd_minus": 22.50,
                "expected_nxd": 546.79,
                "expected_nyd": 61.31,
            },
            {
                "load_case": "6.10b gr1a - Config A/177",
                "mx": -55.61,
                "my": -20.39,
                "mxy": 9.59,
                "vx": 83.80,
                "vy": 10.33,
                "nx": 1562.73,
                "ny": 203.39,
                "nxy": -180.84,
                "expected_mxd_plus": -65.21,
                "expected_mxd_minus": 0.91,
                "expected_myd_plus": -29.98,
                "expected_myd_minus": 0.22,
                "expected_nxd": 1743.57,
                "expected_nyd": 384.23,
            },
            {
                "load_case": "6.10b gr1a - Config A/178",
                "mx": 36.01,
                "my": 26.00,
                "mxy": -22.11,
                "vx": 64.43,
                "vy": -8.51,
                "nx": -727.26,
                "ny": -131.06,
                "nxy": 100.91,
                "expected_mxd_plus": -5.23,
                "expected_mxd_minus": 60.74,
                "expected_myd_plus": -7.61,
                "expected_myd_minus": 50.72,
                "expected_nxd": 150.21,
                "expected_nyd": -115.23,
            },
            {
                "load_case": "6.10b gr1a - Config A/179",
                "mx": -3.64,
                "my": 5.62,
                "mxy": -5.99,
                "vx": 73.63,
                "vy": 0.05,
                "nx": 418.52,
                "ny": -45.83,
                "nxy": -39.66,
                "expected_mxd_plus": -30.12,
                "expected_mxd_minus": 31.67,
                "expected_myd_plus": -9.97,
                "expected_myd_minus": 21.72,
                "expected_nxd": 1479.47,
                "expected_nyd": 112.83,
            },
        ]

    def test_all_load_cases_comprehensive(self, test_cases):
        """Test all design magnitude calculations for all load cases against expected SCIA results."""
        for case in test_cases:
            load_case = case["load_case"]
            
            # Calculate all design magnitudes
            mxd_plus_result = mxd_plus(case["mx"], case["my"], case["mxy"])
            mxd_minus_result = mxd_minus(case["mx"], case["my"], case["mxy"])
            myd_plus_result = myd_plus(case["mx"], case["my"], case["mxy"])
            myd_minus_result = myd_minus(case["mx"], case["my"], case["mxy"])
            nxd_result = nxd(case["nx"], case["ny"], case["nxy"])
            nyd_result = nyd(case["nx"], case["ny"], case["nxy"])
            
            # Verify against expected results
            assert mxd_plus_result == pytest.approx(case["expected_mxd_plus"], abs=0.02), \
                f"{load_case}: mxd_plus expected {case['expected_mxd_plus']}, got {mxd_plus_result}"
            
            assert mxd_minus_result == pytest.approx(case["expected_mxd_minus"], abs=0.02), \
                f"{load_case}: mxd_minus expected {case['expected_mxd_minus']}, got {mxd_minus_result}"
            
            assert myd_plus_result == pytest.approx(case["expected_myd_plus"], abs=0.02), \
                f"{load_case}: myd_plus expected {case['expected_myd_plus']}, got {myd_plus_result}"
            
            assert myd_minus_result == pytest.approx(case["expected_myd_minus"], abs=0.02), \
                f"{load_case}: myd_minus expected {case['expected_myd_minus']}, got {myd_minus_result}"
            
            assert nxd_result == pytest.approx(case["expected_nxd"], abs=0.02), \
                f"{load_case}: nxd expected {case['expected_nxd']}, got {nxd_result}"
            
            assert nyd_result == pytest.approx(case["expected_nyd"], abs=0.02), \
                f"{load_case}: nyd expected {case['expected_nyd']}, got {nyd_result}"

    def test_config_a_170_load_case(self, test_cases):
        """Test Config A/170 load case calculations."""
        case = test_cases[0]
        
        assert mxd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(-62.14, abs=0.02)
        assert mxd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(19.25, abs=0.02)
        assert myd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(-25.82, abs=0.02)
        assert myd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(5.56, abs=0.02)
        assert nxd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(1823.56, abs=0.02)
        assert nyd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(452.68, abs=0.02)

    def test_config_a_171_load_case(self, test_cases):
        """Test Config A/171 load case calculations."""
        case = test_cases[1]
        
        assert mxd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(-64.16, abs=0.02)
        assert mxd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(42.55, abs=0.02)
        assert myd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(-25.63, abs=0.02)
        assert myd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(16.55, abs=0.02)
        assert nxd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(782.93, abs=0.02)
        assert nyd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(194.66, abs=0.02)

    def test_config_a_172_load_case(self, test_cases):
        """Test Config A/172 load case calculations."""
        case = test_cases[2]
        
        assert mxd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(-7.80, abs=0.02)
        assert mxd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(46.79, abs=0.02)
        assert myd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(-7.22, abs=0.02)
        assert myd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(40.40, abs=0.02)
        assert nxd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(166.60, abs=0.02)
        assert nyd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(-144.47, abs=0.02)


class TestSciaElemDesMagEdgeCases:
    """Test edge cases and boundary conditions for elementary design magnitude calculations."""

    def test_mxd_plus_zero_values(self):
        """Test mxd_plus with all zero values."""
        result = mxd_plus(0.0, 0.0, 0.0)
        assert result == 0.0

    def test_mxd_minus_zero_my(self):
        """Test mxd_minus with zero my to check division protection."""
        result = mxd_minus(-10.0, 0.0, 5.0)
        # mx <= my: -10 <= 0 is True
        # my <= |mxy|: 0 <= 5 is True
        # Condition (1): -mx + |mxy| = 10 + 5 = 15
        assert result == 15.0

    def test_myd_plus_zero_mx(self):
        """Test myd_plus with zero mx to check division protection."""
        result = myd_plus(0.0, -10.0, 5.0)
        # mx <= my: 0 <= -10 is False
        # mx > my and my >= -|mxy|: -10 >= -5 is False
        # mx > my and my < -|mxy|: -10 < -5 is True
        # Condition (4): 0
        assert result == 0.0

    def test_myd_minus_zero_mx(self):
        """Test myd_minus with zero mx to check division protection."""
        result = myd_minus(0.0, 10.0, 5.0)
        # mx <= my: 0 <= 10 is True
        # my <= |mxy|: 10 <= 5 is False
        # my > |mxy|: 10 > 5 is True
        # Condition (3): 0
        assert result == 0.0

    def test_nxd_zero_ny(self):
        """Test nxd with zero ny to check division protection."""
        result = nxd(10.0, 0.0, 5.0)
        # nx > ny: 10 > 0
        # ny >= -|nxy|: 0 >= -5 is True
        # Condition (2): nx + |nxy| = 10 + 5 = 15
        assert result == 15.0

    def test_nyd_zero_nx(self):
        """Test nyd with zero nx to check division protection."""
        result = nyd(0.0, -10.0, 5.0)
        # nx <= ny: 0 <= -10 is False
        # nx > ny and ny >= -|nxy|: -10 >= -5 is False
        # nx > ny and ny < -|nxy|: -10 < -5 is True
        # Condition (4): 0
        assert result == 0.0

    def test_negative_moments(self):
        """Test all functions with negative moment values."""
        mx, my, mxy = -50.0, -30.0, -20.0
        
        mxd_plus_result = mxd_plus(mx, my, mxy)
        mxd_minus_result = mxd_minus(mx, my, mxy)
        myd_plus_result = myd_plus(mx, my, mxy)
        myd_minus_result = myd_minus(mx, my, mxy)
        
        # All results should be numbers (not NaN or inf)
        assert isinstance(mxd_plus_result, (int, float))
        assert isinstance(mxd_minus_result, (int, float))
        assert isinstance(myd_plus_result, (int, float))
        assert isinstance(myd_minus_result, (int, float))

    def test_positive_forces(self):
        """Test force functions with positive force values."""
        nx, ny, nxy = 100.0, 50.0, 30.0
        
        nxd_result = nxd(nx, ny, nxy)
        nyd_result = nyd(nx, ny, nxy)
        
        # Both should return positive values
        assert nxd_result > 0
        assert nyd_result > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

