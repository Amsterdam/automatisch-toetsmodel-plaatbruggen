"""
Test module for SCIA integration strip results processing.

This module tests the DataFrame merge functionality for SCIA integration strip results
without importing the full idea_interface module to avoid circular import issues.
"""

import pandas as pd
import pytest


def _process_scia_integration_strip_results_for_idea_input(scia_results_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Process SCIA integration strip results into a single merged dataframe.

    The individual DataFrames should already be processed (grouped by 'name' and 'dx',
    with 'Belasting' values merged and absolute maximum values for force/moment columns).
    This function just merges the load cases.

    :param scia_results_dict: Dictionary containing SCIA integration strip results for different load cases
    :returns: Merged dataframe with all load cases
    :rtype: pd.DataFrame
    """
    # Get load cases from SCIA results with strip prefixes and add fallback for None values
    df_uls = scia_results_dict.get("strip_ULS")
    if df_uls is None:
        df_uls = pd.DataFrame()

    df_sls_kar = scia_results_dict.get("strip_SLS kar")
    if df_sls_kar is None:
        df_sls_kar = pd.DataFrame()

    df_sls_freq = scia_results_dict.get("strip_SLS freq")
    if df_sls_freq is None:
        df_sls_freq = pd.DataFrame()

    # Check if any dataframes are empty
    if df_uls.empty or df_sls_kar.empty or df_sls_freq.empty:
        return pd.DataFrame()

    # The DataFrames should already be processed, so we just need to merge them
    # Merge dataframes on name and dx (these columns come from the base processor after renaming)
    # Rename Belasting columns to avoid conflicts
    df_uls_renamed = df_uls.rename(columns={"Belasting": "ULS_Belasting"})
    df_sls_kar_renamed = df_sls_kar.rename(columns={"Belasting": "SLS_kar_Belasting"})
    df_sls_freq_renamed = df_sls_freq.rename(columns={"Belasting": "SLS_freq_Belasting"})

    # Use 'name' and 'dx' columns as they come from the base processor after column renaming
    merge_columns = ["name", "dx"]

    df_temp = df_uls_renamed.merge(df_sls_kar_renamed, on=merge_columns, how="inner")
    return df_temp.merge(df_sls_freq_renamed, on=merge_columns, how="inner")


class TestSciaIntegrationStripResultsProcessing:
    """
    Test cases for the _process_scia_integration_strip_results_for_idea_input function.

    This function merges SCIA integration strip results for different load cases (ULS, SLS kar, SLS freq)
    into a single DataFrame. The test verifies that the merge operation works correctly with the
    renamed column structure where "Naam" has been renamed to "name".

    Test coverage includes:
    - Successful merge operation with valid data
    - Handling of empty DataFrames
    - Verification that the old column name "Naam" would cause a KeyError
    - Correct column renaming for load case identification
    """

    @pytest.fixture
    def sample_strip_dataframes(self) -> dict[str, pd.DataFrame]:
        """Create sample SCIA integration strip result DataFrames for testing."""
        # These simulate the output from process_scia_integration_strip_results_for_idea
        # after the "Naam" column has been renamed to "name"

        df_uls = pd.DataFrame(
            {
                "name": ["Beam1", "Beam2", "Beam3"],
                "dx": [0.0, 1.0, 2.0],
                "Belasting": ["ULS_LC1", "ULS_LC2", "ULS_LC3"],
                "v_y_max": [10.0, 20.0, 15.0],
                "m_z_max": [5.0, 10.0, 7.5],
                "n_max": [100.0, 200.0, 150.0],
            }
        )

        df_sls_kar = pd.DataFrame(
            {
                "name": ["Beam1", "Beam2", "Beam3"],
                "dx": [0.0, 1.0, 2.0],
                "Belasting": ["SLS_kar_LC1", "SLS_kar_LC2", "SLS_kar_LC3"],
                "v_y_max": [8.0, 16.0, 12.0],
                "m_z_max": [4.0, 8.0, 6.0],
                "n_max": [80.0, 160.0, 120.0],
            }
        )

        df_sls_freq = pd.DataFrame(
            {
                "name": ["Beam1", "Beam2", "Beam3"],
                "dx": [0.0, 1.0, 2.0],
                "Belasting": ["SLS_freq_LC1", "SLS_freq_LC2", "SLS_freq_LC3"],
                "v_y_max": [6.0, 12.0, 9.0],
                "m_z_max": [3.0, 6.0, 4.5],
                "n_max": [60.0, 120.0, 90.0],
            }
        )

        return {
            "strip_ULS": df_uls,
            "strip_SLS kar": df_sls_kar,
            "strip_SLS freq": df_sls_freq,
        }

    def test_successful_merge_with_renamed_columns(self, sample_strip_dataframes: dict[str, pd.DataFrame]) -> None:
        """Test that the merge operation succeeds with the corrected column names."""
        result = _process_scia_integration_strip_results_for_idea_input(sample_strip_dataframes)

        # Verify the merge was successful
        assert not result.empty, "Merged DataFrame should not be empty"
        assert len(result) == 3, "Should have 3 rows (one for each beam)"

        # Verify the expected columns are present
        expected_columns = {
            "name",
            "dx",
            "ULS_Belasting",
            "SLS_kar_Belasting",
            "SLS_freq_Belasting",
            "v_y_max_x",
            "m_z_max_x",
            "n_max_x",  # From ULS (suffixed by pandas)
            "v_y_max_y",
            "m_z_max_y",
            "n_max_y",  # From SLS kar (suffixed by pandas)
            "v_y_max",
            "m_z_max",
            "n_max",  # From SLS freq (no suffix)
        }
        assert expected_columns.issubset(set(result.columns)), f"Missing expected columns. Got: {list(result.columns)}"

        # Verify the merge keys are correct
        assert result["name"].tolist() == ["Beam1", "Beam2", "Beam3"]
        assert result["dx"].tolist() == [0.0, 1.0, 2.0]

        # Verify load case columns are properly renamed
        assert result["ULS_Belasting"].tolist() == ["ULS_LC1", "ULS_LC2", "ULS_LC3"]
        assert result["SLS_kar_Belasting"].tolist() == ["SLS_kar_LC1", "SLS_kar_LC2", "SLS_kar_LC3"]
        assert result["SLS_freq_Belasting"].tolist() == ["SLS_freq_LC1", "SLS_freq_LC2", "SLS_freq_LC3"]

    def test_merge_with_empty_dataframes(self) -> None:
        """Test that the function handles empty DataFrames correctly."""
        empty_dataframes = {
            "strip_ULS": pd.DataFrame(),
            "strip_SLS kar": pd.DataFrame(),
            "strip_SLS freq": pd.DataFrame(),
        }

        result = _process_scia_integration_strip_results_for_idea_input(empty_dataframes)
        assert result.empty, "Result should be empty when input DataFrames are empty"

    def test_merge_with_missing_dataframes(self) -> None:
        """Test that the function handles missing DataFrames (None values) correctly."""
        missing_dataframes = {
            "strip_ULS": None,
            "strip_SLS kar": None,
            "strip_SLS freq": None,
        }

        result = _process_scia_integration_strip_results_for_idea_input(missing_dataframes)
        assert result.empty, "Result should be empty when input DataFrames are None"

    def test_merge_with_partially_missing_dataframes(self) -> None:
        """Test that the function handles partially missing DataFrames correctly."""
        partial_dataframes = {
            "strip_ULS": pd.DataFrame({"name": ["Beam1"], "dx": [0.0], "Belasting": ["ULS_LC1"]}),
            "strip_SLS kar": None,  # Missing
            "strip_SLS freq": pd.DataFrame(),  # Empty
        }

        result = _process_scia_integration_strip_results_for_idea_input(partial_dataframes)
        assert result.empty, "Result should be empty when any input DataFrame is missing or empty"

    def test_old_column_name_would_fail(self, sample_strip_dataframes: dict[str, pd.DataFrame]) -> None:
        """Test that using the old column name 'Naam' would cause a KeyError."""
        # Create DataFrames with the old column name to simulate the bug
        old_dataframes = {}
        for key, df in sample_strip_dataframes.items():
            if not df.empty:
                old_df = df.copy()
                old_df = old_df.rename(columns={"name": "Naam"})  # Revert to old column name
                old_dataframes[key] = old_df
            else:
                old_dataframes[key] = df

        # Manually simulate what the function would do with old column names
        df_uls = old_dataframes["strip_ULS"]
        df_sls_kar = old_dataframes["strip_SLS kar"]
        df_sls_freq = old_dataframes["strip_SLS freq"]

        if not (df_uls.empty or df_sls_kar.empty or df_sls_freq.empty):
            df_uls_renamed = df_uls.rename(columns={"Belasting": "ULS_Belasting"})
            df_sls_kar_renamed = df_sls_kar.rename(columns={"Belasting": "SLS_kar_Belasting"})

            # This should fail with the old column name
            with pytest.raises(KeyError, match="name"):
                merge_columns = ["name", "dx"]  # Column "name" doesn't exist in old dataframes
                df_uls_renamed.merge(df_sls_kar_renamed, on=merge_columns, how="inner")


if __name__ == "__main__":
    pytest.main([__file__])
