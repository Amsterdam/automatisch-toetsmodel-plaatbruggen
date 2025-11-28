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
    """
    Test cases for SCIA elementary design magnitude calculations using real SCIA data.

    Test data from element 2101 at position (6.175, 0.250, 0.000) for span_1_x_sec_11_10.
    """

    @pytest.fixture
    def test_cases(self):
        """
        Provide test case data from SCIA analysis results.

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
                "load_case": "6.10a Perm/1",
                "mx": 132.85,
                "my": 20.95,
                "mxy": 0.06,
                "vx": -4.38,
                "vy": -0.43,
                "nx": 0.00,
                "ny": 0.00,
                "nxy": 0.00,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 132.91,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 21.02,
                "expected_nxd": 0.00,
                "expected_nyd": 0.00,
            },
            {
                "load_case": "6.10a gr1a - Config A/2",
                "mx": 293.77,
                "my": 50.90,
                "mxy": -3.91,
                "vx": -6.70,
                "vy": -23.98,
                "nx": -1207.83,
                "ny": -45.85,
                "nxy": -2.08,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 297.68,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 54.81,
                "expected_nxd": 0.00,
                "expected_nyd": -45.85,
            },
            {
                "load_case": "6.10a gr1a - Config A/3",
                "mx": 100.52,
                "my": -4.70,
                "mxy": -0.10,
                "vx": -4.66,
                "vy": 0.64,
                "nx": 1182.32,
                "ny": 44.89,
                "nxy": 2.04,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 100.52,
                "expected_myd_plus": -4.70,
                "expected_myd_minus": 0.00,
                "expected_nxd": 1184.36,
                "expected_nyd": 46.93,
            },
            {
                "load_case": "6.10a gr1a - Config A/4",
                "mx": 225.75,
                "my": 85.96,
                "mxy": 0.45,
                "vx": -4.15,
                "vy": -3.52,
                "nx": -1207.83,
                "ny": -45.85,
                "nxy": -2.08,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 226.20,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 86.40,
                "expected_nxd": 0.00,
                "expected_nyd": -45.85,
            },
            {
                "load_case": "6.10a gr1a - Config A/5",
                "mx": 168.54,
                "my": -39.76,
                "mxy": -4.46,
                "vx": -7.20,
                "vy": -19.82,
                "nx": 1182.32,
                "ny": 44.89,
                "nxy": 2.04,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 169.04,
                "expected_myd_plus": -39.87,
                "expected_myd_minus": 0.00,
                "expected_nxd": 1184.36,
                "expected_nyd": 46.93,
            },
            {
                "load_case": "6.10a gr1a - Config A/6",
                "mx": 263.28,
                "my": 64.61,
                "mxy": 9.29,
                "vx": -1.07,
                "vy": -14.13,
                "nx": -1207.83,
                "ny": -45.85,
                "nxy": -2.08,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 272.57,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 73.90,
                "expected_nxd": 0.00,
                "expected_nyd": -45.85,
            },
            {
                "load_case": "6.10a gr1a - Config A/7",
                "mx": 147.81,
                "my": -30.23,
                "mxy": -13.63,
                "vx": -10.53,
                "vy": -12.75,
                "nx": 1182.32,
                "ny": 44.89,
                "nxy": 2.04,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 153.97,
                "expected_myd_plus": -31.49,
                "expected_myd_minus": 0.00,
                "expected_nxd": 1184.36,
                "expected_nyd": 46.93,
            },
            {
                "load_case": "6.10a gr1a - Config A/8",
                "mx": 250.36,
                "my": 62.46,
                "mxy": 9.28,
                "vx": -0.64,
                "vy": -14.08,
                "nx": -1207.83,
                "ny": -45.85,
                "nxy": -2.08,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 259.64,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 71.74,
                "expected_nxd": 0.00,
                "expected_nyd": -45.85,
            },
            {
                "load_case": "6.10a gr1a - Config A/9",
                "mx": 168.13,
                "my": -31.30,
                "mxy": -13.21,
                "vx": -11.06,
                "vy": -15.23,
                "nx": 1182.32,
                "ny": 44.89,
                "nxy": 2.04,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 173.71,
                "expected_myd_plus": -32.34,
                "expected_myd_minus": 0.00,
                "expected_nxd": 1184.36,
                "expected_nyd": 46.93,
            },
            {
                "load_case": "6.10a gr1a - Config A/10",
                "mx": 108.60,
                "my": 1.71,
                "mxy": -0.06,
                "vx": -4.59,
                "vy": 0.37,
                "nx": 3083.17,
                "ny": 117.05,
                "nxy": 5.32,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 108.66,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 1.77,
                "expected_nxd": 3088.50,
                "expected_nyd": 122.37,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/151",
                "mx": 154.91,
                "my": 106.67,
                "mxy": -11.52,
                "vx": -20.24,
                "vy": 9.06,
                "nx": -1665.38,
                "ny": -332.63,
                "nxy": 94.52,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 166.43,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 118.19,
                "expected_nxd": 0.00,
                "expected_nyd": -327.26,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/294",
                "mx": -15.66,
                "my": -37.87,
                "mxy": 2.06,
                "vx": -38.81,
                "vy": -4.92,
                "nx": 1630.21,
                "ny": 325.60,
                "nxy": -92.52,
                "expected_mxd_plus": -17.72,
                "expected_mxd_minus": 0.00,
                "expected_myd_plus": -39.93,
                "expected_myd_minus": 0.00,
                "expected_nxd": 1722.73,
                "expected_nyd": 418.13,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/295",
                "mx": -0.19,
                "my": -26.85,
                "mxy": 1.00,
                "vx": -40.49,
                "vy": -3.98,
                "nx": 4251.14,
                "ny": 849.08,
                "nxy": -241.28,
                "expected_mxd_plus": -1.18,
                "expected_mxd_minus": 0.00,
                "expected_myd_plus": -27.85,
                "expected_myd_minus": 0.00,
                "expected_nxd": 4492.42,
                "expected_nyd": 1090.36,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/296",
                "mx": 121.68,
                "my": 80.55,
                "mxy": -8.86,
                "vx": -20.63,
                "vy": 6.83,
                "nx": -3716.69,
                "ny": -742.33,
                "nxy": 210.94,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 130.54,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 89.41,
                "expected_nxd": 0.00,
                "expected_nyd": -730.36,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/188",
                "mx": -0.15,
                "my": -26.96,
                "mxy": 0.90,
                "vx": -40.54,
                "vy": -3.99,
                "nx": 4251.14,
                "ny": 849.08,
                "nxy": -241.28,
                "expected_mxd_plus": -1.05,
                "expected_mxd_minus": 0.00,
                "expected_myd_plus": -27.86,
                "expected_myd_minus": 0.00,
                "expected_nxd": 4492.42,
                "expected_nyd": 1090.36,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/189",
                "mx": 126.94,
                "my": 81.15,
                "mxy": -10.56,
                "vx": -25.78,
                "vy": 5.31,
                "nx": -3716.69,
                "ny": -742.33,
                "nxy": 210.94,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 137.50,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 91.71,
                "expected_nxd": 0.00,
                "expected_nyd": -730.36,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/297",
                "mx": 126.90,
                "my": 81.26,
                "mxy": -10.46,
                "vx": -25.73,
                "vy": 5.32,
                "nx": -3716.69,
                "ny": -742.33,
                "nxy": 210.94,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 137.36,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 91.72,
                "expected_nxd": 0.00,
                "expected_nyd": -730.36,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/161",
                "mx": 155.03,
                "my": 106.82,
                "mxy": -11.54,
                "vx": -20.33,
                "vy": 8.94,
                "nx": -1665.38,
                "ny": -332.63,
                "nxy": 94.52,
                "expected_mxd_plus": 0.00,
                "expected_mxd_minus": 166.57,
                "expected_myd_plus": 0.00,
                "expected_myd_minus": 118.36,
                "expected_nxd": 0.00,
                "expected_nyd": -327.26,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/182",
                "mx": -15.78,
                "my": -38.02,
                "mxy": 2.08,
                "vx": -38.72,
                "vy": -4.80,
                "nx": 1630.21,
                "ny": 325.60,
                "nxy": -92.52,
                "expected_mxd_plus": -17.85,
                "expected_mxd_minus": 0.00,
                "expected_myd_plus": -40.10,
                "expected_myd_minus": 0.00,
                "expected_nxd": 1722.73,
                "expected_nyd": 418.13,
            },
            {
                "load_case": "6.15b Temp gr1 - Config D/190",
                "mx": -3.48,
                "my": -27.56,
                "mxy": 0.97,
                "vx": -37.29,
                "vy": -3.90,
                "nx": 4251.14,
                "ny": 849.08,
                "nxy": -241.28,
                "expected_mxd_plus": -4.44,
                "expected_mxd_minus": 0.00,
                "expected_myd_plus": -28.52,
                "expected_myd_minus": 0.00,
                "expected_nxd": 4492.42,
                "expected_nyd": 1090.36,
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
            assert mxd_plus_result == pytest.approx(case["expected_mxd_plus"], abs=0.02), (
                f"{load_case}: mxd_plus expected {case['expected_mxd_plus']}, got {mxd_plus_result}"
            )

            assert mxd_minus_result == pytest.approx(case["expected_mxd_minus"], abs=0.02), (
                f"{load_case}: mxd_minus expected {case['expected_mxd_minus']}, got {mxd_minus_result}"
            )

            assert myd_plus_result == pytest.approx(case["expected_myd_plus"], abs=0.02), (
                f"{load_case}: myd_plus expected {case['expected_myd_plus']}, got {myd_plus_result}"
            )

            assert myd_minus_result == pytest.approx(case["expected_myd_minus"], abs=0.02), (
                f"{load_case}: myd_minus expected {case['expected_myd_minus']}, got {myd_minus_result}"
            )

            assert nxd_result == pytest.approx(case["expected_nxd"], abs=0.02), f"{load_case}: nxd expected {case['expected_nxd']}, got {nxd_result}"

            assert nyd_result == pytest.approx(case["expected_nyd"], abs=0.02), f"{load_case}: nyd expected {case['expected_nyd']}, got {nyd_result}"

    def test_config_a_perm_1(self, test_cases):
        """Test 6.10a Perm/1 load case calculations."""
        case = test_cases[0]

        assert mxd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(0.00, abs=0.02)
        assert mxd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(132.91, abs=0.02)
        assert myd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(0.00, abs=0.02)
        assert myd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(21.02, abs=0.02)
        assert nxd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(0.00, abs=0.02)
        assert nyd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(0.00, abs=0.02)

    def test_config_a_2(self, test_cases):
        """Test 6.10a gr1a - Config A/2 load case calculations."""
        case = test_cases[1]

        assert mxd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(0.00, abs=0.02)
        assert mxd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(297.68, abs=0.02)
        assert myd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(0.00, abs=0.02)
        assert myd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(54.81, abs=0.02)
        assert nxd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(0.00, abs=0.02)
        assert nyd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(-45.85, abs=0.02)

    def test_config_a_3(self, test_cases):
        """Test 6.10a gr1a - Config A/3 load case calculations."""
        case = test_cases[2]

        assert mxd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(0.00, abs=0.02)
        assert mxd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(100.52, abs=0.02)
        assert myd_plus(case["mx"], case["my"], case["mxy"]) == pytest.approx(-4.70, abs=0.02)
        assert myd_minus(case["mx"], case["my"], case["mxy"]) == pytest.approx(0.00, abs=0.02)
        assert nxd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(1184.36, abs=0.02)
        assert nyd(case["nx"], case["ny"], case["nxy"]) == pytest.approx(46.93, abs=0.02)


class TestSciaElemDesMagEdgeCases:
    """Test edge cases and boundary conditions for elementary design magnitude calculations."""

    def test_mxd_plus_zero_values(self):
        """Test mxd_plus with all zero values."""
        result = mxd_plus(0.0, 0.0, 0.0)
        assert result == 0.0

    def test_mxd_minus_zero_my(self):
        """Test mxd_minus with zero my to check division protection."""
        result = mxd_minus(-10.0, 0.0, 5.0)
        # my = 0 is not < 0, so use: max(mx + |mxy|, 0)
        # max(-10 + 5, 0) = max(-5, 0) = 0
        assert result == 0.0

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
        # myd_minus always uses: max(my + |mxy|, 0)
        # max(10 + 5, 0) = 15
        assert result == 15.0

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
        # nx = 0 is not > 0, so use: min(ny, 0)
        # min(-10, 0) = -10
        assert result == -10.0

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
