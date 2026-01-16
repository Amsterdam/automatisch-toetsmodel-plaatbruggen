# ruff: noqa: PD901
"""
Test module for SCIA to IDEA mapping functionality.

This module tests the end-to-end mapping of SCIA integration strip results
to IDEA StatiCa format:
- Complete transformation pipeline
- Integration with both strip and CS results
- Force/moment column mapping validation
- Zone name normalization
- Error handling for missing data
- Format consistency checks

Tests cover:
- Full pipeline from SCIA envelope to IDEA format
- X-direction and Y-direction force mappings
- Zone identifier normalization (Z1-1 → 1-1)
- Required column validation
- Empty and missing data handling
- Multiple zones and limit states
"""

from typing import Any

import pandas as pd
import pytest

from src.integrations.scia_integration.results.scia_integration_strips_to_idea import (
    _map_strip_forces_to_idea_format,
    process_integration_strips_for_idea,
)


class TestProcessIntegrationStripsForIdea:
    """Tests for the main processing pipeline."""

    @pytest.fixture
    def scia_results_with_strips(self) -> dict[str, Any]:
        """Create SCIA results with integration strip envelope data."""
        envelope_df = pd.DataFrame(
            {
                "zone": ["Z1-1", "Z1-1", "Z2-1", "Z2-1"],
                "direction": ["x", "y", "x", "y"],
                "limit_state": ["ULS", "ULS", "SLSfreq", "SLSfreq"],
                "filtered_for": ["max_N", "max_N", "max_V_z", "max_V_y"],
                "dx": [0.5, 0.6, 0.7, 0.8],
                "load_case": ["LC1", "LC2", "LC3", "LC4"],
                "N": [100.0, 110.0, 120.0, 130.0],
                "V_y": [10.0, 15.0, 12.0, 20.0],
                "V_z": [5.0, 8.0, 14.0, 9.0],
                "M_x": [20.0, 25.0, 30.0, 35.0],
                "M_y": [30.0, 40.0, 45.0, 50.0],
                "M_z": [40.0, 50.0, 60.0, 70.0],
            }
        )

        return {
            "integration_strips": {
                "tables": {},
                "envelope": envelope_df,
            }
        }

    def test_basic_processing_success(self, scia_results_with_strips: dict[str, Any]) -> None:
        """Test successful processing of integration strip data."""
        result = process_integration_strips_for_idea(scia_results_with_strips)

        assert not result.empty, "Result should not be empty"
        assert "N" in result.columns
        assert "Qz" in result.columns
        assert "My" in result.columns

    def test_zone_normalization(self, scia_results_with_strips: dict[str, Any]) -> None:
        """Test that zone names are normalized (Z1-1 → 1-1)."""
        result = process_integration_strips_for_idea(scia_results_with_strips)

        # Check that zones no longer have 'Z' prefix
        zones = result["zone"].unique()
        assert all(not zone.startswith("Z") for zone in zones), "Zones should not have 'Z' prefix"
        assert "1-1" in zones
        assert "2-1" in zones

    def test_required_columns_preserved(self, scia_results_with_strips: dict[str, Any]) -> None:
        """Test that all required columns are present in output."""
        result = process_integration_strips_for_idea(scia_results_with_strips)

        required_cols = ["zone", "direction", "filtered_for", "limit_state", "N", "Qz", "My", "load_case", "dx"]

        for col in required_cols:
            assert col in result.columns, f"Missing required column: {col}"

    def test_missing_integration_strips_raises_error(self) -> None:
        """Test that missing integration_strips data raises ValueError."""
        results_no_strips: dict[str, dict[str, Any]] = {"other_data": {}}

        with pytest.raises(ValueError, match="Integration strips data not found"):
            process_integration_strips_for_idea(results_no_strips)

    def test_empty_envelope_returns_empty(self) -> None:
        """Test that empty envelope DataFrame returns empty result."""
        results_empty_envelope = {"integration_strips": {"tables": {}, "envelope": pd.DataFrame()}}

        result = process_integration_strips_for_idea(results_empty_envelope)
        assert result.empty


class TestForceMapping:
    """Tests for force/moment mapping from SCIA to IDEA format."""

    @pytest.fixture
    def x_direction_strips(self) -> pd.DataFrame:
        """Create X-direction integration strip data."""
        return pd.DataFrame(
            {
                "zone": ["Z1-1", "Z1-1"],
                "direction": ["x", "x"],
                "limit_state": ["ULS", "SLSfreq"],
                "filtered_for": ["max_N", "max_V_z"],
                "dx": [0.5, 0.6],
                "load_case": ["LC1", "LC2"],
                "N": [100.0, 90.0],
                "V_y": [10.0, 9.0],  # Should NOT be used for X-direction
                "V_z": [15.0, 18.0],  # Should map to Qz
                "M_x": [20.0, 22.0],  # Should map to My
                "M_y": [30.0, 33.0],  # Should NOT be used for X-direction
                "M_z": [40.0, 44.0],
            }
        )

    @pytest.fixture
    def y_direction_strips(self) -> pd.DataFrame:
        """Create Y-direction integration strip data."""
        return pd.DataFrame(
            {
                "zone": ["Z2-1", "Z2-1"],
                "direction": ["y", "y"],
                "limit_state": ["ULS", "SLSfreq"],
                "filtered_for": ["max_N", "max_V_y"],
                "dx": [0.7, 0.8],
                "load_case": ["LC3", "LC4"],
                "N": [120.0, 110.0],
                "V_y": [25.0, 28.0],  # Not used for Y-direction
                "V_z": [12.0, 11.0],  # Should map to Qz for Y-direction
                "M_x": [35.0, 38.0],  # Not used for Y-direction
                "M_y": [45.0, 48.0],  # Should map to My
                "M_z": [55.0, 58.0],
            }
        )

    def test_x_direction_force_mapping(self, x_direction_strips: pd.DataFrame) -> None:
        """Test that X-direction strips map V_z → Qz and M_x → My."""
        result = _map_strip_forces_to_idea_format(x_direction_strips)

        # Check first row
        assert result.loc[0, "Qz"] == 15.0, "V_z should map to Qz for X-direction"
        assert result.loc[0, "My"] == 20.0, "M_x should map to My for X-direction"
        assert result.loc[0, "N"] == 100.0, "N should be preserved"

        # Check second row
        assert result.loc[1, "Qz"] == 18.0
        assert result.loc[1, "My"] == 22.0

    def test_y_direction_force_mapping(self, y_direction_strips: pd.DataFrame) -> None:
        """Test that Y-direction strips map V_z → Qz and M_y → My."""
        result = _map_strip_forces_to_idea_format(y_direction_strips)

        # Check first row
        assert result.loc[0, "Qz"] == 12.0, "V_z should map to Qz for Y-direction"
        assert result.loc[0, "My"] == 45.0, "M_y should map to My for Y-direction"
        assert result.loc[0, "N"] == 120.0, "N should be preserved"

        # Check second row
        assert result.loc[1, "Qz"] == 11.0
        assert result.loc[1, "My"] == 48.0

    def test_mixed_directions_mapping(self, x_direction_strips: pd.DataFrame, y_direction_strips: pd.DataFrame) -> None:
        """Test mapping with both X and Y direction strips."""
        mixed_df = pd.concat([x_direction_strips, y_direction_strips], ignore_index=True)
        result = _map_strip_forces_to_idea_format(mixed_df)

        # Check X-direction (first two rows)
        assert result.loc[0, "direction"] == "x"
        assert result.loc[0, "Qz"] == 15.0  # From V_z
        assert result.loc[0, "My"] == 20.0  # From M_x

        # Check Y-direction (last two rows)
        y_row_idx = len(x_direction_strips)
        assert result.loc[y_row_idx, "direction"] == "y"
        assert result.loc[y_row_idx, "Qz"] == 12.0  # From V_z
        assert result.loc[y_row_idx, "My"] == 45.0  # From M_y


class TestZoneNormalization:
    """Tests for zone name normalization."""

    def test_zone_prefix_removal(self) -> None:
        """Test that 'Z' prefix is removed from zone identifiers."""
        df = pd.DataFrame(
            {
                "zone": ["Z1-1", "Z2-3", "Z3-5"],
                "direction": ["x", "x", "x"],
                "limit_state": ["ULS", "ULS", "ULS"],
                "filtered_for": ["max_N", "max_N", "max_N"],
                "N": [100.0, 110.0, 120.0],
                "V_z": [10.0, 11.0, 12.0],
                "M_x": [20.0, 22.0, 24.0],
            }
        )

        result = _map_strip_forces_to_idea_format(df)

        assert result.loc[0, "zone"] == "1-1"
        assert result.loc[1, "zone"] == "2-3"
        assert result.loc[2, "zone"] == "3-5"

    def test_zone_already_normalized(self) -> None:
        """Test that zones without 'Z' prefix are not affected."""
        df = pd.DataFrame(
            {
                "zone": ["1-1", "2-1"],
                "direction": ["x", "y"],
                "limit_state": ["ULS", "ULS"],
                "filtered_for": ["max_N", "max_N"],
                "N": [100.0, 110.0],
                "V_z": [10.0, 11.0],
                "V_y": [12.0, 13.0],
                "M_x": [20.0, 22.0],
                "M_y": [30.0, 33.0],
            }
        )

        result = _map_strip_forces_to_idea_format(df)

        assert result.loc[0, "zone"] == "1-1"
        assert result.loc[1, "zone"] == "2-1"


class TestMultiZoneAndLimitState:
    """Tests for processing multiple zones and limit states."""

    @pytest.fixture
    def multi_zone_data(self) -> pd.DataFrame:
        """Create data with multiple zones and limit states."""
        return pd.DataFrame(
            {
                "zone": ["Z1-1", "Z1-1", "Z2-1", "Z2-1", "Z1-2", "Z1-2"],
                "direction": ["x", "x", "y", "y", "x", "y"],
                "limit_state": ["ULS", "SLSfreq", "ULS", "SLSfreq", "ULS", "SLSfreq"],
                "filtered_for": ["max_N", "max_V_z", "max_V_y", "min_M_y", "max_N", "max_N"],
                "dx": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                "load_case": ["LC1", "LC2", "LC3", "LC4", "LC5", "LC6"],
                "N": [100.0, 95.0, 110.0, 105.0, 120.0, 115.0],
                "V_y": [10.0, 9.0, 15.0, 14.0, 11.0, 16.0],
                "V_z": [5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
                "M_x": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0],
                "M_y": [30.0, 31.0, 35.0, 36.0, 37.0, 38.0],
            }
        )

    def test_all_zones_processed(self, multi_zone_data: pd.DataFrame) -> None:
        """Test that all zones are processed correctly."""
        result = _map_strip_forces_to_idea_format(multi_zone_data)

        zones = result["zone"].unique()
        # After normalization
        expected_zones = {"1-1", "2-1", "1-2"}
        assert set(zones) == expected_zones

    def test_all_limit_states_preserved(self, multi_zone_data: pd.DataFrame) -> None:
        """Test that both ULS and SLS freq limit states are preserved."""
        result = _map_strip_forces_to_idea_format(multi_zone_data)

        limit_states = set(result["limit_state"])
        assert limit_states == {"ULS", "SLSfreq"}

        # Check counts
        uls_count = len(result[result["limit_state"] == "ULS"])
        sls_count = len(result[result["limit_state"] == "SLSfreq"])

        assert uls_count == 3
        assert sls_count == 3

    def test_filtered_for_values_preserved(self, multi_zone_data: pd.DataFrame) -> None:
        """Test that filtered_for values are preserved."""
        result = _map_strip_forces_to_idea_format(multi_zone_data)

        expected_filtered_for = {"max_N", "max_V_z", "max_V_y", "min_M_y"}
        actual_filtered_for = set(result["filtered_for"])

        assert expected_filtered_for == actual_filtered_for


class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases."""

    def test_empty_dataframe_returns_empty(self) -> None:
        """Test that empty DataFrame returns empty result."""
        empty_df = pd.DataFrame()
        result = _map_strip_forces_to_idea_format(empty_df)

        assert result.empty

    def test_missing_force_columns(self) -> None:
        """Test handling when force columns are missing."""
        df = pd.DataFrame(
            {
                "zone": ["Z1-1"],
                "direction": ["x"],
                "limit_state": ["ULS"],
                "filtered_for": ["max_N"],
                "N": [100.0],
                # Missing V_z, M_x columns
            }
        )

        # Should not raise error, but Qz and My will be 0
        result = _map_strip_forces_to_idea_format(df)
        assert not result.empty
        assert "Qz" in result.columns
        assert "My" in result.columns

    def test_missing_required_columns_raises_error(self) -> None:
        """Test that missing required columns raises ValueError."""
        incomplete_results = {
            "integration_strips": {
                "envelope": pd.DataFrame(
                    {
                        "zone": ["Z1-1"],
                        "N": [100.0],
                        # Missing: direction, limit_state, filtered_for
                    }
                )
            }
        }

        with pytest.raises(ValueError, match="Missing required columns"):
            process_integration_strips_for_idea(incomplete_results)

    def test_zero_forces(self) -> None:
        """Test handling of zero force values."""
        df = pd.DataFrame(
            {
                "zone": ["Z1-1"],
                "direction": ["x"],
                "limit_state": ["ULS"],
                "filtered_for": ["max_N"],
                "N": [0.0],
                "V_z": [0.0],
                "M_x": [0.0],
            }
        )

        result = _map_strip_forces_to_idea_format(df)

        assert result.loc[0, "N"] == 0.0
        assert result.loc[0, "Qz"] == 0.0
        assert result.loc[0, "My"] == 0.0

    def test_negative_forces(self) -> None:
        """Test handling of negative force values."""
        df = pd.DataFrame(
            {
                "zone": ["Z1-1", "Z1-1"],
                "direction": ["x", "y"],
                "limit_state": ["ULS", "ULS"],
                "filtered_for": ["min_N", "min_V_y"],
                "N": [-100.0, -110.0],
                "V_z": [-15.0, -12.0],
                "V_y": [-10.0, -25.0],
                "M_x": [-20.0, -22.0],
                "M_y": [-30.0, -45.0],
            }
        )

        result = _map_strip_forces_to_idea_format(df)

        # X-direction negative values
        assert result.loc[0, "N"] == -100.0
        assert result.loc[0, "Qz"] == -15.0  # From V_z
        assert result.loc[0, "My"] == -20.0  # From M_x

        # Y-direction negative values
        assert result.loc[1, "N"] == -110.0
        assert result.loc[1, "Qz"] == -12.0  # From V_z
        assert result.loc[1, "My"] == -45.0  # From M_y


class TestDataIntegrity:
    """Tests for ensuring data integrity throughout transformation."""

    def test_row_count_preserved(self) -> None:
        """Test that number of rows is preserved through transformation."""
        df = pd.DataFrame(
            {
                "zone": ["Z1-1", "Z1-1", "Z2-1"],
                "direction": ["x", "y", "x"],
                "limit_state": ["ULS", "ULS", "SLSfreq"],
                "filtered_for": ["max_N", "max_N", "max_V_z"],
                "N": [100.0, 110.0, 120.0],
                "V_y": [10.0, 15.0, 12.0],
                "V_z": [5.0, 8.0, 14.0],
                "M_x": [20.0, 25.0, 30.0],
                "M_y": [30.0, 40.0, 45.0],
            }
        )

        result = _map_strip_forces_to_idea_format(df)
        assert len(result) == len(df), "Row count should be preserved"

    def test_load_case_preserved(self) -> None:
        """Test that load case names are preserved."""
        df = pd.DataFrame(
            {
                "zone": ["Z1-1", "Z2-1"],
                "direction": ["x", "y"],
                "limit_state": ["ULS", "SLSfreq"],
                "filtered_for": ["max_N", "max_V_y"],
                "load_case": ["Eigengewicht_Max", "Nuttige_Belasting_Min"],
                "N": [100.0, 110.0],
                "V_z": [10.0, 12.0],
                "V_y": [8.0, 15.0],
                "M_x": [20.0, 25.0],
                "M_y": [30.0, 35.0],
            }
        )

        result = _map_strip_forces_to_idea_format(df)

        assert result.loc[0, "load_case"] == "Eigengewicht_Max"
        assert result.loc[1, "load_case"] == "Nuttige_Belasting_Min"

    def test_dx_position_preserved(self) -> None:
        """Test that dx position values are preserved."""
        df = pd.DataFrame(
            {
                "zone": ["Z1-1", "Z2-1"],
                "direction": ["x", "y"],
                "limit_state": ["ULS", "ULS"],
                "filtered_for": ["max_N", "max_V_y"],
                "dx": [2.5, 7.8],
                "N": [100.0, 110.0],
                "V_z": [10.0, 12.0],
                "V_y": [8.0, 15.0],
                "M_x": [20.0, 25.0],
                "M_y": [30.0, 35.0],
            }
        )

        result = _map_strip_forces_to_idea_format(df)

        assert result.loc[0, "dx"] == 2.5
        assert result.loc[1, "dx"] == 7.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
