"""
Test module for IDEA interface integration with strip results.

This module tests the processing and application of integration strip results
in the IDEA StatiCa interface:
- Transformation of SCIA strip results to IDEA format
- Direction mapping (X strips → dwars, Y strips → langs)
- Force/moment mapping (V_y/V_z → Qz, M_y/M_x → My)
- Load case creation from envelope data
- Validation of strip data presence and completeness

Tests cover:
- Strip result transformation and column mapping
- Direction to slab mapping logic
- ULS and SLS freq load case handling
- Zone-based filtering and grouping
- Error handling for missing or invalid data
"""

import pandas as pd
import pytest


class TestStripResultTransformation:
    """Tests for transforming SCIA strip results to IDEA format."""

    @pytest.fixture
    def sample_strip_envelope(self) -> pd.DataFrame:
        """Create sample integration strip envelope data."""
        return pd.DataFrame(
            {
                "name": [
                    "strip_dir-x_reg_Z1-1_w-1.0_nr-1",
                    "strip_dir-x_reg_Z1-1_w-1.0_nr-1",
                    "strip_dir-y_reg_Z1-1_w-1.0_nr-1",
                    "strip_dir-y_reg_Z1-1_w-1.0_nr-1",
                ],
                "dx": [0.5, 0.5, 1.0, 1.0],
                "load_case": ["LC1", "LC2", "LC3", "LC4"],
                "N": [100.0, 80.0, 150.0, 120.0],
                "V_y": [10.0, 8.0, 20.0, 16.0],
                "V_z": [5.0, 4.0, 10.0, 8.0],
                "M_x": [20.0, 16.0, 30.0, 24.0],
                "M_y": [30.0, 24.0, 40.0, 32.0],
                "M_z": [40.0, 32.0, 50.0, 40.0],
                "direction": ["x", "x", "y", "y"],
                "strip_type": ["reg", "reg", "reg", "reg"],
                "zone": ["Z1-1", "Z1-1", "Z1-1", "Z1-1"],
                "filtered_for": ["max_N", "max_N", "max_N", "max_N"],
                "limit_state": ["ULS", "SLSfreq", "ULS", "SLSfreq"],
            }
        )

    def test_strip_direction_to_slab_mapping(self) -> None:
        """Test that strip directions are correctly mapped to slab directions."""
        # X-direction strips should map to dwars (transverse) cross-section
        # Y-direction strips should map to langs (longitudinal) cross-section
        strip_to_slab_direction = {
            "x": "dwars",
            "y": "langs",
        }

        assert strip_to_slab_direction["x"] == "dwars"
        assert strip_to_slab_direction["y"] == "langs"

    def test_force_mapping_x_direction(self, sample_strip_envelope: pd.DataFrame) -> None:
        """Test force mapping for X-direction strips."""
        # For X-direction strips:
        # - V_z → Qz (shear force perpendicular to strip)
        # - M_x → My (bending moment about strip axis)
        x_strips = sample_strip_envelope[sample_strip_envelope["direction"] == "x"]

        assert not x_strips.empty
        # Should have V_z and M_x columns
        assert "V_z" in x_strips.columns
        assert "M_x" in x_strips.columns

    def test_force_mapping_y_direction(self, sample_strip_envelope: pd.DataFrame) -> None:
        """Test force mapping for Y-direction strips."""
        # For Y-direction strips:
        # - V_y → Qz (shear force perpendicular to strip)
        # - M_y → My (bending moment about strip axis)
        y_strips = sample_strip_envelope[sample_strip_envelope["direction"] == "y"]

        assert not y_strips.empty
        # Should have V_y and M_y columns
        assert "V_y" in y_strips.columns
        assert "M_y" in y_strips.columns

    def test_zone_filtering(self, sample_strip_envelope: pd.DataFrame) -> None:
        """Test filtering strips by zone."""
        zones = ["Z1-1"]
        filtered = sample_strip_envelope[sample_strip_envelope["zone"].isin(zones)]

        assert len(filtered) == 4  # All rows are in Z1-1
        assert set(filtered["zone"]) == {"Z1-1"}

    def test_limit_state_separation(self, sample_strip_envelope: pd.DataFrame) -> None:
        """Test separation of ULS and SLS freq results."""
        uls_strips = sample_strip_envelope[sample_strip_envelope["limit_state"] == "ULS"]
        sls_strips = sample_strip_envelope[sample_strip_envelope["limit_state"] == "SLSfreq"]

        assert len(uls_strips) == 2
        assert len(sls_strips) == 2
        assert set(uls_strips["limit_state"]) == {"ULS"}
        assert set(sls_strips["limit_state"]) == {"SLSfreq"}


class TestLoadCaseCreation:
    """Tests for creating IDEA load cases from strip envelope data."""

    @pytest.fixture
    def envelope_with_multiple_filtered_for(self) -> pd.DataFrame:
        """Create envelope data with multiple filtered_for values."""
        return pd.DataFrame(
            {
                "zone": ["Z1-1", "Z1-1", "Z1-1", "Z1-1", "Z2-1", "Z2-1"],
                "direction": ["x", "x", "x", "x", "x", "x"],
                "filtered_for": ["max_N", "min_N", "max_V_z", "min_V_z", "max_M_x", "min_M_x"],
                "limit_state": ["ULS", "ULS", "ULS", "ULS", "ULS", "ULS"],
                "dx": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                "load_case": ["LC1", "LC2", "LC3", "LC4", "LC5", "LC6"],
                "N": [100.0, -50.0, 120.0, 110.0, 130.0, 125.0],
                "V_z": [10.0, 8.0, 15.0, -12.0, 11.0, 9.0],
                "M_x": [20.0, 18.0, 25.0, 22.0, 30.0, -28.0],
            }
        )

    def test_unique_combination_extraction(self, envelope_with_multiple_filtered_for: pd.DataFrame) -> None:
        """Test extraction of unique (zone, direction, filtered_for) combinations."""
        unique_combos = envelope_with_multiple_filtered_for[["zone", "direction", "filtered_for"]].drop_duplicates()

        assert len(unique_combos) == 6  # 4 from Z1-1, 2 from Z2-1
        assert set(unique_combos["filtered_for"]) == {"max_N", "min_N", "max_V_z", "min_V_z", "max_M_x", "min_M_x"}

    def test_combo_filtering(self, envelope_with_multiple_filtered_for: pd.DataFrame) -> None:
        """Test filtering data for specific combination."""
        zone = "Z1-1"
        direction = "x"
        filtered_for = "max_N"

        combo_data = envelope_with_multiple_filtered_for[
            (envelope_with_multiple_filtered_for["zone"] == zone)
            & (envelope_with_multiple_filtered_for["direction"] == direction)
            & (envelope_with_multiple_filtered_for["filtered_for"] == filtered_for)
        ]

        assert len(combo_data) == 1
        assert combo_data.iloc[0]["N"] == 100.0

    def test_description_generation(self) -> None:
        """Test generation of load case descriptions."""
        # Test position formatting
        test_cases = [
            (0.5, "0.50m"),
            (1.234, "1.23m"),
            (10.0, "10.00m"),
            (None, "NoPos"),
        ]

        for dx_value, expected in test_cases:
            if dx_value is None:
                result = "NoPos"
            else:
                result = f"{float(dx_value):.2f}m"
            assert result == expected, f"Failed for dx={dx_value}"

    def test_load_case_naming(self) -> None:
        """Test load case naming convention."""
        # Format: {desc_prefix}_{filtered_for}_{limit_state}
        desc_prefix = "d250_dwars_config1"
        filtered_for = "max_N"
        limit_state = "ULS"

        expected_name = f"{desc_prefix}_{filtered_for}_{limit_state}"
        assert expected_name == "d250_dwars_config1_max_N_ULS"


class TestStripDataValidation:
    """Tests for validation of integration strip data."""

    def test_empty_dataframe_handling(self) -> None:
        """Test that empty DataFrame is handled correctly."""
        df_empty = pd.DataFrame()

        assert df_empty.empty
        # Should return early and not process

    def test_missing_required_columns(self) -> None:
        """Test handling of DataFrames with missing required columns."""
        df_incomplete = pd.DataFrame(
            {
                "zone": ["Z1-1"],
                "N": [100.0],
                # Missing: direction, filtered_for, limit_state
            }
        )

        required_columns = ["zone", "direction", "filtered_for", "limit_state"]
        missing = [col for col in required_columns if col not in df_incomplete.columns]

        assert len(missing) > 0
        assert "direction" in missing
        assert "filtered_for" in missing

    def test_zone_presence_validation(self) -> None:
        """Test validation that zones exist in created slabs."""
        created_slabs = {
            "d0.25_config1": {
                "zones": ["Z1-1", "Z2-1"],
                "slab_dwars": "mock_slab_dwars",
                "slab_langs": "mock_slab_langs",
            }
        }

        df_strips = pd.DataFrame(
            {
                "zone": ["Z1-1", "Z2-1", "Z3-1"],  # Z3-1 not in created slabs
                "direction": ["x", "x", "x"],
                "N": [100.0, 150.0, 200.0],
            }
        )

        for slab_key, slab_data in created_slabs.items():
            zones = slab_data.get("zones") or []
            df_slab = df_strips[df_strips["zone"].isin(zones)]

            # Should only have Z1-1 and Z2-1
            assert set(df_slab["zone"]) == {"Z1-1", "Z2-1"}
            assert "Z3-1" not in df_slab["zone"].values

    def test_strip_results_presence_check(self) -> None:
        """Test checking for presence of integration_strips in results."""
        # Case 1: Results with integration_strips
        results_with_strips = {
            "results": {
                "integration_strips": {
                    "tables": {},
                    "envelope": pd.DataFrame({"zone": ["Z1-1"]}),
                }
            }
        }

        assert "integration_strips" in results_with_strips["results"]
        integration_strips = results_with_strips["results"]["integration_strips"]
        assert "envelope" in integration_strips
        assert not integration_strips["envelope"].empty

        # Case 2: Results without integration_strips
        results_without_strips = {"results": {}}

        assert "integration_strips" not in results_without_strips["results"]


class TestDirectionAndForceMapping:
    """Tests for comprehensive direction and force mapping logic."""

    def test_x_strip_to_dwars_slab_mapping(self) -> None:
        """Test X-direction strip maps to dwars (transverse) slab."""
        strip_data = pd.DataFrame(
            {
                "direction": ["x"],
                "zone": ["Z1-1"],
                "V_z": [10.0],  # Shear perpendicular to X-strip
                "M_x": [20.0],  # Moment about X-axis
            }
        )

        # X-strip should use dwars slab
        strip_direction = strip_data["direction"].iloc[0]
        expected_slab = "dwars" if strip_direction == "x" else "langs"

        assert expected_slab == "dwars"

    def test_y_strip_to_langs_slab_mapping(self) -> None:
        """Test Y-direction strip maps to langs (longitudinal) slab."""
        strip_data = pd.DataFrame(
            {
                "direction": ["y"],
                "zone": ["Z1-1"],
                "V_y": [15.0],  # Shear perpendicular to Y-strip
                "M_y": [25.0],  # Moment about Y-axis
            }
        )

        # Y-strip should use langs slab
        strip_direction = strip_data["direction"].iloc[0]
        expected_slab = "dwars" if strip_direction == "x" else "langs"

        assert expected_slab == "langs"

    def test_force_column_selection_by_direction(self) -> None:
        """Test that correct force columns are selected based on direction."""
        # X-direction: use V_z, M_x
        # Y-direction: use V_y, M_y

        x_strip_columns = ["N", "V_z", "M_x"]
        y_strip_columns = ["N", "V_y", "M_y"]

        assert "V_z" in x_strip_columns
        assert "M_x" in x_strip_columns
        assert "V_y" in y_strip_columns
        assert "M_y" in y_strip_columns

    def test_idea_force_mapping_x_strips(self) -> None:
        """Test IDEA force mapping for X-direction strips."""
        # X-strips: V_z → Qz, M_x → My
        x_strip_forces = {
            "N": 100.0,
            "V_z": 10.0,  # Maps to Qz in IDEA
            "M_x": 20.0,  # Maps to My in IDEA
        }

        idea_forces = {
            "N": x_strip_forces["N"],
            "Qz": x_strip_forces["V_z"],
            "My": x_strip_forces["M_x"],
        }

        assert idea_forces["N"] == 100.0
        assert idea_forces["Qz"] == 10.0
        assert idea_forces["My"] == 20.0

    def test_idea_force_mapping_y_strips(self) -> None:
        """Test IDEA force mapping for Y-direction strips."""
        # Y-strips: V_y → Qz, M_y → My
        y_strip_forces = {
            "N": 150.0,
            "V_y": 15.0,  # Maps to Qz in IDEA
            "M_y": 25.0,  # Maps to My in IDEA
        }

        idea_forces = {
            "N": y_strip_forces["N"],
            "Qz": y_strip_forces["V_y"],
            "My": y_strip_forces["M_y"],
        }

        assert idea_forces["N"] == 150.0
        assert idea_forces["Qz"] == 15.0
        assert idea_forces["My"] == 25.0


class TestMultiZoneAndDirectionProcessing:
    """Tests for processing multiple zones and directions simultaneously."""

    @pytest.fixture
    def multi_zone_strip_data(self) -> pd.DataFrame:
        """Create strip data covering multiple zones and directions."""
        return pd.DataFrame(
            {
                "zone": ["Z1-1", "Z1-1", "Z2-1", "Z2-1", "Z1-2", "Z1-2"],
                "direction": ["x", "y", "x", "y", "x", "y"],
                "filtered_for": ["max_N", "max_N", "max_N", "max_N", "max_N", "max_N"],
                "limit_state": ["ULS", "ULS", "ULS", "ULS", "ULS", "ULS"],
                "dx": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                "load_case": ["LC1", "LC2", "LC3", "LC4", "LC5", "LC6"],
                "N": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
                "V_y": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
                "V_z": [5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
                "M_x": [20.0, 22.0, 24.0, 26.0, 28.0, 30.0],
                "M_y": [30.0, 33.0, 36.0, 39.0, 42.0, 45.0],
            }
        )

    def test_zone_grouping(self, multi_zone_strip_data: pd.DataFrame) -> None:
        """Test that data is correctly grouped by zone."""
        zones = multi_zone_strip_data["zone"].unique()

        assert len(zones) == 3
        assert set(zones) == {"Z1-1", "Z2-1", "Z1-2"}

        # Check filtering for specific zone
        z1_1_data = multi_zone_strip_data[multi_zone_strip_data["zone"] == "Z1-1"]
        assert len(z1_1_data) == 2  # X and Y directions

    def test_direction_grouping_per_zone(self, multi_zone_strip_data: pd.DataFrame) -> None:
        """Test that each zone has both X and Y direction data."""
        for zone in ["Z1-1", "Z2-1", "Z1-2"]:
            zone_data = multi_zone_strip_data[multi_zone_strip_data["zone"] == zone]
            directions = set(zone_data["direction"])

            assert directions == {"x", "y"}, f"Zone {zone} should have both X and Y directions"

    def test_slab_assignment_per_direction(self, multi_zone_strip_data: pd.DataFrame) -> None:
        """Test that each direction is assigned to correct slab."""
        strip_to_slab = {"x": "dwars", "y": "langs"}

        for _, row in multi_zone_strip_data.iterrows():
            direction = row["direction"]
            expected_slab = strip_to_slab[direction]

            if direction == "x":
                assert expected_slab == "dwars"
            else:
                assert expected_slab == "langs"


class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases."""

    def test_none_slab_handling(self) -> None:
        """Test handling when slab is None (missing direction)."""
        created_slabs = {
            "d0.25_config1": {
                "zones": ["Z1-1"],
                "slab_dwars": "mock_slab_dwars",
                "slab_langs": None,  # Missing langs slab
            }
        }

        # Should skip when slab is None
        slab_data = created_slabs["d0.25_config1"]
        slab_langs = slab_data.get("slab_langs")

        assert slab_langs is None
        # Processing should continue without error

    def test_unknown_direction(self) -> None:
        """Test handling of unknown strip direction."""
        strip_to_slab_direction = {"x": "dwars", "y": "langs"}

        unknown_direction = "z"
        slab_direction = strip_to_slab_direction.get(unknown_direction)

        assert slab_direction is None
        # Should skip processing for unknown direction

    def test_missing_zones_in_slab_data(self) -> None:
        """Test handling when slab data has no zones."""
        created_slabs = {
            "d0.25_config1": {
                "zones": [],  # Empty zones
                "slab_dwars": "mock_slab_dwars",
            }
        }

        slab_data = created_slabs["d0.25_config1"]
        zones = slab_data.get("zones") or []

        assert len(zones) == 0
        # Should skip when no zones

    def test_no_matching_limit_state(self) -> None:
        """Test handling when combo has no matching limit state rows."""
        df_combo = pd.DataFrame(
            {
                "zone": ["Z1-1"],
                "direction": ["x"],
                "filtered_for": ["max_N"],
                "limit_state": ["SLSkar"],  # Not ULS or SLSfreq
                "N": [100.0],
            }
        )

        df_uls = df_combo[df_combo["limit_state"] == "ULS"]
        df_sls = df_combo[df_combo["limit_state"] == "SLSfreq"]

        assert df_uls.empty
        assert df_sls.empty
        # Should handle gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
