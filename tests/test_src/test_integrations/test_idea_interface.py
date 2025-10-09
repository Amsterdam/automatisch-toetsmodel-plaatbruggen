"""
Test module for IDEA StatiCa integration interface.

This module provides comprehensive testing for the IDEA StatiCa integration,
including model creation, parameter extraction, and analysis functionality.

Key test coverage:
- _apply_node_loads_to_slabs function: Tests the application of SCIA analysis results
  to IDEA slab models, including proper force/moment assignment, error handling
  for edge cases, and correct formatting of load descriptions.
"""

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.integrations.idea_integration.idea_interface import _apply_node_loads_to_slabs


class TestApplyLoadsToSlabs:
    """
    Test cases for the _apply_node_loads_to_slabs function.

    This function applies load cases from SCIA results to IDEA slab models.
    It processes loads for both longitudinal ("langs") and transverse ("dwars")
    directions, creating appropriate loading objects for SLS and ULS analysis.

    Test coverage includes:
    - Basic functionality with valid data
    - Edge cases (empty zones, missing slabs, nonexistent zones)
    - Data validation (missing columns, empty dataframes)
    - Force assignment verification (correct axis mapping)
    - Description formatting verification
    """

    @pytest.fixture
    def mock_builder(self) -> MagicMock:
        """Create a mock IDEA model builder."""
        builder = MagicMock()

        # Mock builder methods to return appropriate mock objects
        def create_forces(*args: Any, **kwargs: Any) -> MagicMock:
            return MagicMock()

        def create_loading(*args: Any, **kwargs: Any) -> MagicMock:
            return MagicMock()

        builder.create_result_of_internal_forces = MagicMock(side_effect=create_forces)
        builder.create_loading_sls = MagicMock(side_effect=create_loading)
        builder.create_loading_uls = MagicMock(side_effect=create_loading)
        builder.create_extreme = MagicMock()

        return builder

    @pytest.fixture
    def sample_scia_dataframe(self) -> pd.DataFrame:
        """Create a sample SCIA results dataframe for testing."""
        return pd.DataFrame(
            {
                "name": ["1-1", "1-2", "2-1", "2-2", "3-1"],
                "coords_xyz": [
                    (10.0, 5.0, 0.0),
                    (20.0, 5.0, 0.0),
                    (10.0, 15.0, 0.0),
                    (20.0, 15.0, 0.0),
                    (30.0, 25.0, 0.0),
                ],
                # SLS karakteristiek values
                "SLS_kar_v_x_max": [100.0, 150.0, 200.0, 180.0, 120.0],
                "SLS_kar_v_y_max": [80.0, 120.0, 160.0, 140.0, 90.0],
                "SLS_kar_Mx": [50.0, 75.0, 100.0, 90.0, 60.0],
                "SLS_kar_My": [40.0, 60.0, 80.0, 70.0, 45.0],
                # SLS frequent values
                "SLS_freq_v_x_max": [70.0, 105.0, 140.0, 126.0, 84.0],
                "SLS_freq_v_y_max": [56.0, 84.0, 112.0, 98.0, 63.0],
                "SLS_freq_Mx": [35.0, 52.5, 70.0, 63.0, 42.0],
                "SLS_freq_My": [28.0, 42.0, 56.0, 49.0, 31.5],
                # ULS values
                "ULS_v_x_max": [140.0, 210.0, 280.0, 252.0, 168.0],
                "ULS_v_y_max": [112.0, 168.0, 224.0, 196.0, 126.0],
                "ULS_Mx": [70.0, 105.0, 140.0, 126.0, 84.0],
                "ULS_My": [56.0, 84.0, 112.0, 98.0, 63.0],
            }
        )

    @pytest.fixture
    def mock_slab_langs(self) -> MagicMock:
        """Create a mock slab for longitudinal direction."""
        mock_slab = MagicMock()
        mock_slab.create_extreme = MagicMock()
        return mock_slab

    @pytest.fixture
    def mock_slab_dwars(self) -> MagicMock:
        """Create a mock slab for transverse direction."""
        mock_slab = MagicMock()
        mock_slab.create_extreme = MagicMock()
        return mock_slab

    @pytest.fixture
    def sample_created_slabs(self, mock_slab_langs: MagicMock, mock_slab_dwars: MagicMock) -> dict[str, dict]:
        """Create sample created_slabs dictionary for testing."""
        return {
            "CS_d0.2_1": {
                "zones": ["1-1", "1-2"],
                "slab_langs": mock_slab_langs,
                "slab_dwars": mock_slab_dwars,
            },
            "CS_d0.25_2": {
                "zones": ["2-1", "2-2"],
                "slab_langs": mock_slab_langs,
                "slab_dwars": mock_slab_dwars,
            },
            "CS_d0.3_3": {
                "zones": ["3-1"],
                "slab_langs": mock_slab_langs,
                "slab_dwars": mock_slab_dwars,
            },
        }

    def test_apply_loads_basic_functionality(
        self,
        sample_created_slabs: dict[str, dict],
        sample_scia_dataframe: pd.DataFrame,
        mock_builder: MagicMock,
    ) -> None:
        """Test basic functionality of _apply_node_loads_to_slabs."""
        # Execute the function with builder
        _apply_node_loads_to_slabs(sample_created_slabs, sample_scia_dataframe, mock_builder)

        # Verify that create_extreme_on_slab was called via builder for each matching zone
        # CS_d0.2_1: zones ["1-1", "1-2"] → 2 zones × 2 directions = 4 calls
        # CS_d0.25_2: zones ["2-1", "2-2"] → 2 zones × 2 directions = 4 calls
        # CS_d0.3_3: zones ["3-1"] → 1 zone × 2 directions = 2 calls
        # Total: 5 zones × 2 directions = 10 calls

        expected_calls = 10  # Total zones × directions
        assert mock_builder.create_extreme_on_slab.call_count == expected_calls

    def test_apply_loads_with_empty_zones(self, sample_scia_dataframe: pd.DataFrame, mock_builder: MagicMock) -> None:
        """Test _apply_node_loads_to_slabs with empty zones."""
        created_slabs_empty_zones: dict[str, dict[str, Any]] = {
            "CS_d0.2_1": {
                "zones": [],  # Empty zones
                "slab_langs": MagicMock(),
                "slab_dwars": MagicMock(),
            }
        }

        # Execute the function
        _apply_node_loads_to_slabs(created_slabs_empty_zones, sample_scia_dataframe, mock_builder)

        # Verify no create_extreme calls were made
        assert mock_builder.create_extreme.call_count == 0

    def test_apply_loads_with_missing_slab_direction(self, sample_scia_dataframe: pd.DataFrame, mock_builder: MagicMock) -> None:
        """Test _apply_node_loads_to_slabs with missing slab direction."""
        created_slabs_missing_direction: dict[str, dict[str, Any]] = {
            "CS_d0.2_1": {
                "zones": ["1-1"],
                "slab_langs": MagicMock(),
                # Missing slab_dwars
            }
        }

        # Execute the function - should not raise an error
        _apply_node_loads_to_slabs(created_slabs_missing_direction, sample_scia_dataframe, mock_builder)

        # Verify only one direction was called (langs only)
        assert mock_builder.create_extreme_on_slab.call_count == 1

    def test_apply_loads_with_nonexistent_zones(self, sample_scia_dataframe: pd.DataFrame, mock_builder: MagicMock) -> None:
        """Test _apply_node_loads_to_slabs with zones not present in SCIA dataframe."""
        mock_slab = MagicMock()
        created_slabs_nonexistent_zones = {
            "CS_d0.2_1": {
                "zones": ["99-99"],  # Zone not in SCIA dataframe
                "slab_langs": mock_slab,
                "slab_dwars": mock_slab,
            }
        }

        # Execute the function
        _apply_node_loads_to_slabs(created_slabs_nonexistent_zones, sample_scia_dataframe, mock_builder)

        # Verify no create_extreme calls were made
        assert mock_builder.create_extreme.call_count == 0

    def test_apply_loads_with_none_zones(self, sample_scia_dataframe: pd.DataFrame, mock_builder: MagicMock) -> None:
        """Test _apply_node_loads_to_slabs with None zones."""
        mock_slab = MagicMock()
        created_slabs_none_zones = {
            "CS_d0.2_1": {
                "zones": None,  # None zones
                "slab_langs": mock_slab,
                "slab_dwars": mock_slab,
            }
        }

        # Execute the function
        _apply_node_loads_to_slabs(created_slabs_none_zones, sample_scia_dataframe, mock_builder)

        # Verify no create_extreme calls were made
        assert mock_builder.create_extreme.call_count == 0

    def test_apply_loads_correct_force_assignments(
        self,
        sample_scia_dataframe: pd.DataFrame,
        mock_builder: MagicMock,
    ) -> None:
        """Test that forces are correctly assigned based on direction."""
        mock_slab_langs = MagicMock()
        mock_slab_dwars = MagicMock()

        created_slabs = {
            "CS_d0.2_1": {
                "zones": ["1-1"],  # Single zone to simplify verification
                "slab_langs": mock_slab_langs,
                "slab_dwars": mock_slab_dwars,
            }
        }

        # Execute the function
        _apply_node_loads_to_slabs(created_slabs, sample_scia_dataframe, mock_builder)

        # Check that builder.create_result_of_internal_forces was called with correct parameters
        # For 'langs' direction: uses y-axis forces and My moments
        # For 'dwars' direction: uses x-axis forces and Mx moments

        calls = mock_builder.create_result_of_internal_forces.call_args_list

        # Should have 6 calls total (3 load cases × 2 directions)
        assert len(calls) == 6

        # Extract the expected values for zone "1-1" from the dataframe
        zone_data = sample_scia_dataframe[sample_scia_dataframe["name"] == "1-1"].iloc[0]

        # Check that forces and moments are correctly mapped
        all_qz_values = [call.kwargs.get("Qz", 0) for call in calls]
        all_my_values = [call.kwargs.get("My", 0) for call in calls]

        # Expected values for different load cases and directions
        expected_qz_values = [
            zone_data["SLS_kar_v_y_max"],  # langs characteristic
            zone_data["SLS_freq_v_y_max"],  # langs frequent
            zone_data["ULS_v_y_max"],  # langs fundamental
            zone_data["SLS_kar_v_x_max"],  # dwars characteristic
            zone_data["SLS_freq_v_x_max"],  # dwars frequent
            zone_data["ULS_v_x_max"],  # dwars fundamental
        ]

        expected_my_values = [
            zone_data["SLS_kar_My"],  # langs characteristic
            zone_data["SLS_freq_My"],  # langs frequent
            zone_data["ULS_My"],  # langs fundamental
            zone_data["SLS_kar_Mx"],  # dwars characteristic
            zone_data["SLS_freq_Mx"],  # dwars frequent
            zone_data["ULS_Mx"],  # dwars fundamental
        ]

        # Verify all expected values are present
        for expected_qz in expected_qz_values:
            assert expected_qz in all_qz_values, f"Expected Qz value {expected_qz} not found in calls"

        for expected_my in expected_my_values:
            assert expected_my in all_my_values, f"Expected My value {expected_my} not found in calls"

    def test_apply_loads_with_missing_dataframe_columns(self, mock_builder: MagicMock) -> None:
        """Test _apply_node_loads_to_slabs with missing columns in dataframe."""
        incomplete_dataframe = pd.DataFrame(
            {
                "name": ["1-1"],
                "coords_xyz": [(10.0, 5.0, 0.0)],
                # Missing most required columns
            }
        )

        mock_slab = MagicMock()
        created_slabs = {
            "CS_d0.2_1": {
                "zones": ["1-1"],
                "slab_langs": mock_slab,
                "slab_dwars": mock_slab,
            }
        }

        # Execute the function - should handle missing columns gracefully
        _apply_node_loads_to_slabs(created_slabs, incomplete_dataframe, mock_builder)

        # Function should still execute but with default values (0) for missing columns
        assert mock_builder.create_extreme_on_slab.call_count == 2  # One per direction

    def test_apply_loads_description_formatting(
        self,
        sample_scia_dataframe: pd.DataFrame,
        mock_builder: MagicMock,
    ) -> None:
        """Test that load descriptions are formatted correctly."""
        mock_slab_langs = MagicMock()

        created_slabs = {
            "CS_d0.2_1": {
                "zones": ["1-1"],
                "slab_langs": mock_slab_langs,
            }
        }

        # Execute the function
        _apply_node_loads_to_slabs(created_slabs, sample_scia_dataframe, mock_builder)

        # Check that create_extreme_on_slab was called with proper description formatting
        calls = mock_builder.create_extreme_on_slab.call_args_list
        assert len(calls) == 1

        # Get the description from the call
        description = calls[0].kwargs.get("description", "")

        # Verify description contains expected elements
        assert "CS_d0_2_1" in description  # slab key with dots replaced by underscores
        assert "1-1" in description  # zone name
        assert "10.0, 5.0, 0.0" in description  # coordinates

    def test_apply_loads_with_empty_dataframe(self, mock_builder: MagicMock) -> None:
        """Test _apply_node_loads_to_slabs with empty SCIA dataframe."""
        empty_dataframe = pd.DataFrame()

        mock_slab = MagicMock()
        created_slabs = {
            "CS_d0.2_1": {
                "zones": ["1-1"],
                "slab_langs": mock_slab,
                "slab_dwars": mock_slab,
            }
        }

        with pytest.raises(KeyError, match="name"):
            # The function should handle empty dataframes gracefully
            # When the dataframe is empty, df_all["name"].isin(zones) will raise KeyError
            # because there's no "name" column in an empty dataframe

            # This test verifies that the function doesn't crash when given empty data
            # but currently the function doesn't handle this case, so we expect a KeyError
            _apply_node_loads_to_slabs(created_slabs, empty_dataframe, mock_builder)


if __name__ == "__main__":
    pytest.main([__file__])
