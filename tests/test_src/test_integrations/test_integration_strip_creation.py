# ruff: noqa: PD901
"""
Test module for integration strip creation and processing.

This module tests the core functionality of integration strip extraction and processing:
- Extraction of integration strip tables from SCIA XML results
- Parsing of strip names (zone, direction, type)
- Width correction for force/moment values
- Envelope generation (min/max values per zone/direction/limit state)
- Processing pipeline integration

Tests cover:
- Individual table extraction
- Strip name parsing with various formats
- Width correction calculation accuracy
- Envelope generation for all force/moment components
- Edge cases and error handling
"""

from typing import Any

import pandas as pd
import pytest

from src.integrations.scia_integration.results.scia_integration_strips_processor import (
    FORCE_MOMENT_COLUMNS,
    INTEGRATION_STRIP_TABLES,
    STRIP_COLUMN_MAPPING,
    add_parsed_columns_to_dataframe,
    extract_all_integration_strip_tables,
    extract_integration_strip_table,
    parse_strip_name,
    process_all_integration_strips,
    process_integration_strip_envelopes,
)


class TestIntegrationStripExtraction:
    """Tests for extracting integration strip tables from SCIA results."""

    @pytest.fixture
    def mock_scia_results_with_strips(self) -> dict[str, Any]:
        """Create mock SCIA results with integration strip tables."""
        return {
            "xml_parsing": {
                "parsed_tables": {
                    "ULS_x_reg": {
                        "data": {
                            "p0": {
                                "Naam": ["strip_dir-x_reg_Z1-1_w-1.0_nr-1", "strip_dir-x_reg_Z1-1_w-1.0_nr-1"],
                                "dx": [0.0, 1.0],
                                "Belasting": ["LC1", "LC2"],
                                "N": [100.0, 150.0],
                                "V_y": [10.0, 15.0],
                                "V_z": [5.0, 7.5],
                                "M_x": [20.0, 25.0],
                                "M_y": [30.0, 35.0],
                                "M_z": [40.0, 45.0],
                            }
                        }
                    },
                    "ULS_y_reg": {
                        "data": {
                            "p0": {
                                "Naam": ["strip_dir-y_reg_Z2-1_w-1.0_nr-1"],
                                "dx": [0.5],
                                "Belasting": ["LC3"],
                                "N": [200.0],
                                "V_y": [20.0],
                                "V_z": [10.0],
                                "M_x": [30.0],
                                "M_y": [40.0],
                                "M_z": [50.0],
                            }
                        }
                    },
                    "SLSfreq_x_reg": {
                        "data": {
                            "p0": {
                                "Naam": ["strip_dir-x_reg_Z1-1_w-1.0_nr-1"],
                                "dx": [0.0],
                                "Belasting": ["LC4"],
                                "N": [80.0],
                                "V_y": [8.0],
                                "V_z": [4.0],
                                "M_x": [16.0],
                                "M_y": [24.0],
                                "M_z": [32.0],
                            }
                        }
                    },
                }
            }
        }

    def test_extract_single_table_success(self, mock_scia_results_with_strips: dict[str, Any]) -> None:
        """Test successful extraction of a single integration strip table."""
        df = extract_integration_strip_table(mock_scia_results_with_strips, "ULS_x_reg")

        assert not df.empty, "Extracted DataFrame should not be empty"
        assert len(df) == 2, "Should extract 2 rows from ULS_x_reg"
        assert "name" in df.columns, "Column 'Naam' should be renamed to 'name'"
        assert "load_case" in df.columns, "Column 'Belasting' should be renamed to 'load_case'"
        assert df["name"].iloc[0] == "strip_dir-x_reg_Z1-1_w-1.0_nr-1"
        assert df["N"].iloc[0] == 100.0

    def test_extract_table_missing_table(self, mock_scia_results_with_strips: dict[str, Any]) -> None:
        """Test extraction when table is missing returns empty DataFrame."""
        df = extract_integration_strip_table(mock_scia_results_with_strips, "NonExistentTable")

        assert df.empty, "Should return empty DataFrame for missing table"

    def test_extract_table_no_xml_parsing(self) -> None:
        """Test extraction when xml_parsing is missing."""
        results: dict[str, dict[str, Any]] = {"some_other_data": {}}
        df = extract_integration_strip_table(results, "ULS_x_reg")

        assert df.empty, "Should return empty DataFrame when xml_parsing is missing"

    def test_extract_all_tables(self, mock_scia_results_with_strips: dict[str, Any]) -> None:
        """Test extraction of all integration strip tables."""
        all_tables = extract_all_integration_strip_tables(mock_scia_results_with_strips)

        assert len(all_tables) == len(INTEGRATION_STRIP_TABLES), "Should extract all table types"
        assert "ULS_x_reg" in all_tables
        assert "ULS_y_reg" in all_tables
        assert "SLSfreq_x_reg" in all_tables
        assert not all_tables["ULS_x_reg"].empty
        assert all_tables["ULS_x_sup"].empty  # Not in mock data

    def test_column_mapping(self, mock_scia_results_with_strips: dict[str, Any]) -> None:
        """Test that all expected columns are renamed correctly."""
        df = extract_integration_strip_table(mock_scia_results_with_strips, "ULS_x_reg")

        for old_col, new_col in STRIP_COLUMN_MAPPING.items():
            if old_col in ["Naam", "Belasting"]:  # These are in our mock data
                assert new_col in df.columns, f"Column {old_col} should be renamed to {new_col}"


class TestStripNameParsing:
    """Tests for parsing integration strip names."""

    def test_parse_complete_strip_name(self) -> None:
        """Test parsing a complete strip name with all components."""
        strip_name = "strip_dir-x_reg_Z1-1_w-1.0_nr-1"
        parsed = parse_strip_name(strip_name)

        assert parsed["direction"] == "x"
        assert parsed["strip_type"] == "reg"
        assert parsed["zone"] == "Z1-1"
        assert parsed["width"] == "1.0"
        assert parsed["number"] == "1"

    def test_parse_support_strip(self) -> None:
        """Test parsing support strip type."""
        strip_name = "strip_dir-y_sup_Z2-3_w-0.5_nr-2"
        parsed = parse_strip_name(strip_name)

        assert parsed["direction"] == "y"
        assert parsed["strip_type"] == "sup"
        assert parsed["zone"] == "Z2-3"
        assert parsed["width"] == "0.5"
        assert parsed["number"] == "2"

    def test_parse_different_zone_formats(self) -> None:
        """Test parsing different zone identifier formats."""
        test_cases = [
            ("strip_dir-x_reg_Z1-1_w-1.0_nr-1", "Z1-1"),
            ("strip_dir-x_reg_Z2-5_w-1.0_nr-1", "Z2-5"),
            ("strip_dir-y_sup_Z3-10_w-1.0_nr-1", "Z3-10"),
        ]

        for strip_name, expected_zone in test_cases:
            parsed = parse_strip_name(strip_name)
            assert parsed["zone"] == expected_zone, f"Failed to parse zone from {strip_name}"

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string returns empty dict."""
        parsed = parse_strip_name("")

        assert parsed["direction"] == ""
        assert parsed["strip_type"] == ""
        assert parsed["zone"] == ""

    def test_parse_invalid_strip_name(self) -> None:
        """Test parsing malformed strip name returns empty values."""
        parsed = parse_strip_name("invalid_strip_name_format")

        # Should return empty dict values without raising errors
        assert isinstance(parsed, dict)
        assert all(v == "" for v in parsed.values())

    def test_parse_none_input(self) -> None:
        """Test parsing None input returns empty dict."""
        parsed = parse_strip_name(None)  # type: ignore[arg-type]

        assert all(v == "" for v in parsed.values())


class TestWidthCorrection:
    """Tests for width correction of force/moment values."""

    @pytest.fixture
    def strip_data_with_varying_widths(self) -> pd.DataFrame:
        """Create DataFrame with strips of different widths."""
        return pd.DataFrame(
            {
                "name": [
                    "strip_dir-x_reg_Z1-1_w-1.0_nr-1",
                    "strip_dir-x_reg_Z1-1_w-2.0_nr-2",
                    "strip_dir-x_reg_Z1-1_w-0.5_nr-3",
                ],
                "dx": [0.0, 0.0, 0.0],
                "load_case": ["LC1", "LC1", "LC1"],
                "N": [100.0, 200.0, 50.0],
                "V_y": [10.0, 20.0, 5.0],
                "M_z": [50.0, 100.0, 25.0],
            }
        )

    def test_width_correction_applied(self, strip_data_with_varying_widths: pd.DataFrame) -> None:
        """Test that width correction is applied for strips with width != 1.0."""
        df = add_parsed_columns_to_dataframe(strip_data_with_varying_widths)

        # Width 1.0: should not be corrected
        assert not df.loc[0, "corrected"]  # type: ignore[call-overload]
        assert df.loc[0, "N"] == 100.0  # type: ignore[call-overload]

        # Width 2.0: should be divided by 2
        assert df.loc[1, "corrected"]  # type: ignore[call-overload]
        assert df.loc[1, "N"] == 100.0  # type: ignore[call-overload]  # 200 / 2
        assert df.loc[1, "V_y"] == 10.0  # type: ignore[call-overload]  # 20 / 2
        assert df.loc[1, "M_z"] == 50.0  # type: ignore[call-overload]  # 100 / 2

        # Width 0.5: should be divided by 0.5 (multiplied by 2)
        assert df.loc[2, "corrected"]  # type: ignore[call-overload]
        assert df.loc[2, "N"] == 100.0  # type: ignore[call-overload]  # 50 / 0.5
        assert df.loc[2, "V_y"] == 10.0  # type: ignore[call-overload]  # 5 / 0.5

    def test_all_force_moment_columns_corrected(self) -> None:
        """Test that all force/moment columns are corrected."""
        df = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_w-2.0_nr-1"],
                "dx": [0.0],
                "load_case": ["LC1"],
                "N": [200.0],
                "V_y": [20.0],
                "V_z": [40.0],
                "M_x": [60.0],
                "M_y": [80.0],
                "M_z": [100.0],
            }
        )

        # Store original values before correction
        original_values = {col: float(df[col].iloc[0]) for col in FORCE_MOMENT_COLUMNS}

        df_corrected = add_parsed_columns_to_dataframe(df)

        for col in FORCE_MOMENT_COLUMNS:
            actual_value = float(df_corrected[col].iloc[0])
            expected_value = original_values[col] / 2.0
            assert abs(actual_value - expected_value) < 0.01, f"Column {col} not corrected properly: expected {expected_value}, got {actual_value}"

    def test_parsed_columns_added(self, strip_data_with_varying_widths: pd.DataFrame) -> None:
        """Test that parsed columns are added correctly."""
        df = add_parsed_columns_to_dataframe(strip_data_with_varying_widths)

        assert "direction" in df.columns
        assert "strip_type" in df.columns
        assert "zone" in df.columns
        assert "strip_width" in df.columns
        assert "strip_number" in df.columns

        assert df["direction"].iloc[0] == "x"
        assert df["strip_type"].iloc[0] == "reg"
        assert df["zone"].iloc[0] == "Z1-1"

    def test_empty_dataframe_handling(self) -> None:
        """Test that empty DataFrame is handled gracefully."""
        df = pd.DataFrame()
        result = add_parsed_columns_to_dataframe(df)

        assert result.empty


class TestEnvelopeGeneration:
    """Tests for generating force/moment envelopes from integration strips."""

    @pytest.fixture
    def sample_strip_tables(self) -> dict[str, pd.DataFrame]:
        """Create sample integration strip tables for envelope testing."""
        # ULS x-direction regular strips
        df_uls_x_reg = pd.DataFrame(
            {
                "name": [
                    "strip_dir-x_reg_Z1-1_w-1.0_nr-1",
                    "strip_dir-x_reg_Z1-1_w-1.0_nr-1",
                    "strip_dir-x_reg_Z1-1_w-1.0_nr-1",
                ],
                "dx": [0.0, 0.5, 1.0],
                "load_case": ["LC1", "LC2", "LC3"],
                "N": [100.0, 150.0, 120.0],  # max at LC2
                "V_y": [10.0, -15.0, 12.0],  # min at LC2, max at LC3
                "V_z": [5.0, 7.5, 6.0],
                "M_x": [20.0, 25.0, 22.0],
                "M_y": [30.0, 35.0, 32.0],
                "M_z": [40.0, -50.0, 45.0],  # min at LC2, max at LC3
            }
        )

        # ULS x-direction support strips
        df_uls_x_sup = pd.DataFrame(
            {
                "name": ["strip_dir-x_sup_Z1-1_w-1.0_nr-1"],
                "dx": [0.0],
                "load_case": ["LC_sup"],
                "N": [200.0],  # Higher than reg strips - should become max
                "V_y": [0.0],  # Should not be used for shear (only reg)
                "V_z": [0.0],
                "M_x": [50.0],
                "M_y": [60.0],
                "M_z": [70.0],
            }
        )

        # SLS freq x-direction regular strips
        df_sls_x_reg = pd.DataFrame(
            {
                "name": ["strip_dir-x_reg_Z1-1_w-1.0_nr-1"],
                "dx": [0.0],
                "load_case": ["LC_sls"],
                "N": [80.0],
                "V_y": [8.0],
                "V_z": [4.0],
                "M_x": [16.0],
                "M_y": [24.0],
                "M_z": [32.0],
            }
        )

        return {
            "ULS_x_reg": df_uls_x_reg,
            "ULS_x_sup": df_uls_x_sup,
            "ULS_y_reg": pd.DataFrame(),
            "ULS_y_sup": pd.DataFrame(),
            "SLSfreq_x_reg": df_sls_x_reg,
            "SLSfreq_x_sup": pd.DataFrame(),
            "SLSfreq_y_reg": pd.DataFrame(),
            "SLSfreq_y_sup": pd.DataFrame(),
        }

    def test_envelope_generation_basic(self, sample_strip_tables: dict[str, pd.DataFrame]) -> None:
        """Test basic envelope generation with min/max values."""
        df_envelope = process_integration_strip_envelopes(sample_strip_tables)

        assert not df_envelope.empty, "Envelope DataFrame should not be empty"
        assert "filtered_for" in df_envelope.columns
        assert "limit_state" in df_envelope.columns
        assert "zone" in df_envelope.columns

    def test_envelope_normal_force_includes_support_strips(self, sample_strip_tables: dict[str, pd.DataFrame]) -> None:
        """Test that normal force envelope includes both reg and sup strips."""
        df_envelope = process_integration_strip_envelopes(sample_strip_tables)

        # Find max N for ULS in zone Z1-1
        max_n_rows = df_envelope[(df_envelope["filtered_for"] == "max_N") & (df_envelope["limit_state"] == "ULS") & (df_envelope["zone"] == "Z1-1")]

        assert not max_n_rows.empty, "Should have max_N envelope"
        # Should use support strip value (200.0) as it's higher
        assert max_n_rows.iloc[0]["N"] == 200.0

    def test_envelope_shear_excludes_support_strips(self, sample_strip_tables: dict[str, pd.DataFrame]) -> None:
        """Test that shear force envelope only uses reg strips."""
        df_envelope = process_integration_strip_envelopes(sample_strip_tables)

        # Find max V_y for ULS
        max_vy_rows = df_envelope[(df_envelope["filtered_for"] == "max_V_y") & (df_envelope["limit_state"] == "ULS")]

        assert not max_vy_rows.empty, "Should have max_V_y envelope"
        # Should be 12.0 from LC3 (not from support strip)
        assert max_vy_rows.iloc[0]["V_y"] == 12.0
        assert max_vy_rows.iloc[0]["load_case"] == "LC3"

    def test_envelope_min_and_max_values(self, sample_strip_tables: dict[str, pd.DataFrame]) -> None:
        """Test that both min and max envelopes are created."""
        df_envelope = process_integration_strip_envelopes(sample_strip_tables)

        # Check for both min and max of M_z
        mz_envelopes = df_envelope[df_envelope["filtered_for"].str.contains("M_z")]

        min_mz = mz_envelopes[mz_envelopes["filtered_for"] == "min_M_z"]
        max_mz = mz_envelopes[mz_envelopes["filtered_for"] == "max_M_z"]

        assert not min_mz.empty, "Should have min_M_z envelope"
        assert not max_mz.empty, "Should have max_M_z envelope"

        # Verify values
        assert min_mz[min_mz["limit_state"] == "ULS"].iloc[0]["M_z"] == -50.0
        assert max_mz[max_mz["limit_state"] == "ULS"].iloc[0]["M_z"] == 70.0  # From support strip

    def test_envelope_separate_limit_states(self, sample_strip_tables: dict[str, pd.DataFrame]) -> None:
        """Test that ULS and SLS freq envelopes are separate."""
        df_envelope = process_integration_strip_envelopes(sample_strip_tables)

        uls_rows = df_envelope[df_envelope["limit_state"] == "ULS"]
        sls_rows = df_envelope[df_envelope["limit_state"] == "SLSfreq"]

        assert not uls_rows.empty, "Should have ULS envelopes"
        assert not sls_rows.empty, "Should have SLS freq envelopes"

    def test_envelope_empty_tables(self) -> None:
        """Test envelope generation with all empty tables."""
        empty_tables = {key: pd.DataFrame() for key in INTEGRATION_STRIP_TABLES}
        df_envelope = process_integration_strip_envelopes(empty_tables)

        assert df_envelope.empty, "Should return empty DataFrame for empty input"

    def test_envelope_preserves_metadata(self, sample_strip_tables: dict[str, pd.DataFrame]) -> None:
        """Test that envelope preserves load case and position info."""
        df_envelope = process_integration_strip_envelopes(sample_strip_tables)

        # Check that load_case and dx are preserved
        assert "load_case" in df_envelope.columns
        assert "dx" in df_envelope.columns

        # Verify a specific envelope has correct metadata
        max_n = df_envelope[(df_envelope["filtered_for"] == "max_N") & (df_envelope["limit_state"] == "ULS")].iloc[0]
        assert pd.notna(max_n["load_case"])
        assert pd.notna(max_n["dx"])


class TestCompleteProcessing:
    """Tests for the complete integration strip processing pipeline."""

    @pytest.fixture
    def complete_scia_results(self) -> dict[str, Any]:
        """Create complete mock SCIA results with multiple strip types."""
        return {
            "xml_parsing": {
                "parsed_tables": {
                    "ULS_x_reg": {
                        "data": {
                            "p0": {
                                "Naam": [
                                    "strip_dir-x_reg_Z1-1_w-1.0_nr-1",
                                    "strip_dir-x_reg_Z2-1_w-2.0_nr-1",
                                ],
                                "dx": [0.0, 0.0],
                                "Belasting": ["LC1", "LC2"],
                                "N": [100.0, 400.0],  # Second value should be corrected to 200.0
                                "V_y": [10.0, 40.0],
                                "V_z": [5.0, 20.0],
                                "M_x": [20.0, 80.0],
                                "M_y": [30.0, 120.0],
                                "M_z": [40.0, 160.0],
                            }
                        }
                    },
                    "SLSfreq_x_reg": {
                        "data": {
                            "p0": {
                                "Naam": ["strip_dir-x_reg_Z1-1_w-1.0_nr-1"],
                                "dx": [0.0],
                                "Belasting": ["LC3"],
                                "N": [80.0],
                                "V_y": [8.0],
                                "V_z": [4.0],
                                "M_x": [16.0],
                                "M_y": [24.0],
                                "M_z": [32.0],
                            }
                        }
                    },
                }
            }
        }

    def test_process_all_integration_strips(self, complete_scia_results: dict[str, Any]) -> None:
        """Test complete processing pipeline."""
        result = process_all_integration_strips(complete_scia_results)

        assert "tables" in result
        assert "envelope" in result

        # Check tables are processed
        assert "ULS_x_reg" in result["tables"]
        df_uls = result["tables"]["ULS_x_reg"]
        assert not df_uls.empty
        assert "zone" in df_uls.columns  # Parsed columns added
        assert "direction" in df_uls.columns

        # Check envelope is created
        assert not result["envelope"].empty
        assert "filtered_for" in result["envelope"].columns

    def test_width_correction_in_pipeline(self, complete_scia_results: dict[str, Any]) -> None:
        """Test that width correction is applied in the pipeline."""
        result = process_all_integration_strips(complete_scia_results)

        df_uls = result["tables"]["ULS_x_reg"]

        # First row has width 1.0 - no correction
        assert not df_uls.loc[0, "corrected"]  # type: ignore[call-overload]
        assert df_uls.loc[0, "N"] == 100.0  # type: ignore[call-overload]

        # Second row has width 2.0 - should be corrected
        assert df_uls.loc[1, "corrected"]  # type: ignore[call-overload]
        assert df_uls.loc[1, "N"] == 200.0  # type: ignore[call-overload]  # 400 / 2

    def test_empty_results_handling(self) -> None:
        """Test handling of empty or missing SCIA results."""
        empty_results: dict[str, Any] = {}
        result = process_all_integration_strips(empty_results)

        assert "tables" in result
        assert "envelope" in result
        assert result["envelope"].empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
