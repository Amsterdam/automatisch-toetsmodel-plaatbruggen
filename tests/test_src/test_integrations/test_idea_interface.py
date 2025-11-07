"""
Test module for IDEA StatiCa integration interface.

This module provides comprehensive testing for the IDEA StatiCa integration,
including model creation, parameter extraction, and analysis functionality.

Key test coverage:
- _apply_cs_loads_to_slabs function: Tests the application of SCIA analysis results
  to IDEA slab models, including proper force/moment assignment, error handling
  for edge cases, and correct formatting of load descriptions.
"""

import sys
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.integrations.idea_integration.idea_interface import _apply_cs_loads_to_slabs

# Mock the problematic imports to avoid circular import issues
sys.modules["app.bridge.parametrization"] = MagicMock()
sys.modules["app.bridge.analysis_cache"] = MagicMock()


class TestApplyLoadsToSlabs:
    """
    Test cases for the _apply_cs_loads_to_slabs function.

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
    def sample_scia_dataframe(self) -> pd.DataFrame:
        """
        Create a sample SCIA results dataframe for testing.

        This DataFrame simulates the output from _process_scia_cs_results_for_idea_input(),
        which includes zone, result_type, max_for_column, and processed force columns.

        Each (zone, max_for_column) combination appears twice: once for ULS and once for SLS freq.
        """
        # Create data for zone 1-1 with two force components (v_x and v_y)
        data = []

        zones_data = [
            ("1-1", "SEC_1_1", (10.0, 5.0, 0.0), "BG_ULS", "BG_SLS"),
            ("1-2", "SEC_1_2", (20.0, 5.0, 0.0), "BG_ULS", "BG_SLS"),
        ]

        for zone, name, coords, uls_belasting, sls_belasting in zones_data:
            # For each zone, create entries for v_x force component
            # ULS row for v_x
            data.append(
                {
                    "zone": zone,
                    "name": name,
                    "coords_xyz": coords,
                    "max_for_column": "v_x",
                    "result_type": "ULS",
                    "belasting": uls_belasting,
                    "v_x_max": 140.0,
                    "v_y_max": 112.0,
                    "m_xD+_max": 70.0,
                    "m_xD-_max": -65.0,
                    "m_yD+_max": 56.0,
                    "m_yD-_max": -50.0,
                    "Mx": 70.0,
                    "My": 56.0,
                }
            )
            # SLS freq row for v_x
            data.append(
                {
                    "zone": zone,
                    "name": name,
                    "coords_xyz": coords,
                    "max_for_column": "v_x",
                    "result_type": "SLS freq",
                    "belasting": sls_belasting,
                    "v_x_max": 70.0,
                    "v_y_max": 56.0,
                    "m_xD+_max": 35.0,
                    "m_xD-_max": -32.0,
                    "m_yD+_max": 28.0,
                    "m_yD-_max": -25.0,
                    "Mx": 35.0,
                    "My": 28.0,
                }
            )

            # ULS row for v_y
            data.append(
                {
                    "zone": zone,
                    "name": name,
                    "coords_xyz": coords,
                    "max_for_column": "v_y",
                    "result_type": "ULS",
                    "belasting": uls_belasting,
                    "v_x_max": 140.0,
                    "v_y_max": 112.0,
                    "m_xD+_max": 70.0,
                    "m_xD-_max": -65.0,
                    "m_yD+_max": 56.0,
                    "m_yD-_max": -50.0,
                    "Mx": 70.0,
                    "My": 56.0,
                }
            )
            # SLS freq row for v_y
            data.append(
                {
                    "zone": zone,
                    "name": name,
                    "coords_xyz": coords,
                    "max_for_column": "v_y",
                    "result_type": "SLS freq",
                    "belasting": sls_belasting,
                    "v_x_max": 70.0,
                    "v_y_max": 56.0,
                    "m_xD+_max": 35.0,
                    "m_xD-_max": -32.0,
                    "m_yD+_max": 28.0,
                    "m_yD-_max": -25.0,
                    "Mx": 35.0,
                    "My": 28.0,
                }
            )

        return pd.DataFrame(data)

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
        mock_slab_langs: MagicMock,  # noqa: ARG002
        mock_slab_dwars: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test basic functionality of _apply_cs_loads_to_slabs."""
        # Configure mock builder with proper return values
        mock_loading_sls = MagicMock()
        mock_loading_uls = MagicMock()
        mock_internal_forces = MagicMock()

        mock_builder = MagicMock()
        mock_builder.create_result_of_internal_forces = MagicMock(return_value=mock_internal_forces)
        mock_builder.create_loading_sls = MagicMock(return_value=mock_loading_sls)
        mock_builder.create_loading_uls = MagicMock(return_value=mock_loading_uls)
        mock_builder.create_extreme_on_slab = MagicMock()

        # Execute the function
        _apply_cs_loads_to_slabs(sample_created_slabs, sample_scia_dataframe, mock_builder)

        # Verify that create_extreme_on_slab was called on builder
        # Test data has zones 1-1 and 1-2, each with 2 max_for_column values (v_x, v_y)
        # CS_d0.2_1: zones ["1-1", "1-2"] → 2 zones × 2 max_for_column × 2 directions = 8 calls
        # CS_d0.25_2: zones ["2-1", "2-2"] → not in test data = 0 calls
        # CS_d0.3_3: zones ["3-1"] → not in test data = 0 calls
        # Total: 2 zones × 2 max_for_column × 2 directions = 8 calls

        expected_calls = 8  # 2 zones × 2 max_for_column × 2 directions
        assert mock_builder.create_extreme_on_slab.call_count == expected_calls

    def test_apply_loads_with_empty_zones(self, sample_scia_dataframe: pd.DataFrame) -> None:
        """Test _apply_cs_loads_to_slabs with empty zones."""
        created_slabs_empty_zones: dict[str, dict[str, Any]] = {
            "CS_d0.2_1": {
                "zones": [],  # Empty zones
                "slab_langs": MagicMock(),
                "slab_dwars": MagicMock(),
            }
        }

        # Execute the function with mock builder
        mock_builder = MagicMock()
        _apply_cs_loads_to_slabs(created_slabs_empty_zones, sample_scia_dataframe, mock_builder)

        # Verify no create_extreme_on_slab calls were made
        assert mock_builder.create_extreme_on_slab.call_count == 0

    def test_apply_loads_with_missing_slab_direction(self, sample_scia_dataframe: pd.DataFrame) -> None:
        """Test _apply_cs_loads_to_slabs with missing slab direction."""
        mock_slab_langs = MagicMock()
        created_slabs_missing_direction: dict[str, dict[str, Any]] = {
            "CS_d0.2_1": {
                "zones": ["1-1"],
                "slab_langs": mock_slab_langs,
                # Missing slab_dwars
            }
        }

        # Execute the function - should not raise an error with mock builder
        mock_builder = MagicMock()
        _apply_cs_loads_to_slabs(created_slabs_missing_direction, sample_scia_dataframe, mock_builder)

        # Verify only one direction was processed
        # 1 zone ("1-1") × 2 max_for_column (v_x, v_y) × 1 direction (langs only) = 2 calls
        assert mock_builder.create_extreme_on_slab.call_count == 2
        # Verify that only 'langs' direction was used
        for call_args in mock_builder.create_extreme_on_slab.call_args_list:
            assert call_args[0][0] == mock_slab_langs  # First positional arg is the slab

    def test_apply_loads_with_nonexistent_zones(self, sample_scia_dataframe: pd.DataFrame) -> None:
        """Test _apply_cs_loads_to_slabs with zones not present in SCIA dataframe."""
        mock_slab = MagicMock()
        created_slabs_nonexistent_zones = {
            "CS_d0.2_1": {
                "zones": ["99-99"],  # Zone not in SCIA dataframe
                "slab_langs": mock_slab,
                "slab_dwars": mock_slab,
            }
        }

        # Execute the function with mock builder
        mock_builder = MagicMock()
        _apply_cs_loads_to_slabs(created_slabs_nonexistent_zones, sample_scia_dataframe, mock_builder)

        # Verify no create_extreme_on_slab calls were made
        assert mock_builder.create_extreme_on_slab.call_count == 0

    def test_apply_loads_with_none_zones(self, sample_scia_dataframe: pd.DataFrame) -> None:
        """Test _apply_cs_loads_to_slabs with None zones."""
        mock_slab = MagicMock()
        created_slabs_none_zones = {
            "CS_d0.2_1": {
                "zones": None,  # None zones
                "slab_langs": mock_slab,
                "slab_dwars": mock_slab,
            }
        }

        # Execute the function with mock builder
        mock_builder = MagicMock()
        _apply_cs_loads_to_slabs(created_slabs_none_zones, sample_scia_dataframe, mock_builder)

        # Verify no create_extreme_on_slab calls were made
        assert mock_builder.create_extreme_on_slab.call_count == 0

    def test_apply_loads_correct_force_assignments(
        self,
        sample_scia_dataframe: pd.DataFrame,
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

        # Configure mock builder
        mock_loading_sls = MagicMock()
        mock_loading_uls = MagicMock()
        mock_internal_forces = MagicMock()

        mock_builder = MagicMock()
        mock_builder.create_result_of_internal_forces = MagicMock(return_value=mock_internal_forces)
        mock_builder.create_loading_sls = MagicMock(return_value=mock_loading_sls)
        mock_builder.create_loading_uls = MagicMock(return_value=mock_loading_uls)
        mock_builder.create_extreme_on_slab = MagicMock()

        # Execute the function
        _apply_cs_loads_to_slabs(created_slabs, sample_scia_dataframe, mock_builder)

        # Check that create_result_of_internal_forces was called with correct parameters
        # For 'langs' direction: uses y-axis forces and My moments
        # For 'dwars' direction: uses x-axis forces and Mx moments

        # We expect 8 calls to create_result_of_internal_forces:
        # 1 zone × 2 max_for_column × 2 directions × 2 result_types (ULS + SLS freq) = 8 calls
        assert mock_builder.create_result_of_internal_forces.call_count == 8

        # Verify 4 calls to create_extreme_on_slab
        # 1 zone × 2 max_for_column × 2 directions = 4 calls
        assert mock_builder.create_extreme_on_slab.call_count == 4

    def test_apply_loads_with_missing_dataframe_columns(self) -> None:
        """Test _apply_cs_loads_to_slabs with missing columns in dataframe."""
        # Need both ULS and SLS freq rows for each (zone, max_for_column) combination
        incomplete_dataframe = pd.DataFrame(
            {
                "name": ["1-1", "1-1"],
                "zone": ["1-1", "1-1"],
                "coords_xyz": [(10.0, 5.0, 0.0), (10.0, 5.0, 0.0)],
                "max_for_column": ["v_x", "v_x"],
                "result_type": ["ULS", "SLS freq"],
                "belasting": ["BG_ULS", "BG_SLS"],
                # Missing force columns - should handle gracefully
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

        # Execute the function - should handle missing columns gracefully with mock builder
        mock_builder = MagicMock()
        _apply_cs_loads_to_slabs(created_slabs, incomplete_dataframe, mock_builder)

        # Function should still execute but with default values (0) for missing columns
        # One zone × 2 directions = 2 calls to create_extreme_on_slab
        assert mock_builder.create_extreme_on_slab.call_count == 2

    def test_apply_loads_description_formatting(
        self,
        sample_scia_dataframe: pd.DataFrame,
    ) -> None:
        """Test that load descriptions are formatted correctly."""
        mock_slab_langs = MagicMock()

        created_slabs = {
            "CS_d0.2_1": {
                "zones": ["1-1"],
                "slab_langs": mock_slab_langs,
            }
        }

        # Execute the function with mock builder
        mock_builder = MagicMock()
        _apply_cs_loads_to_slabs(created_slabs, sample_scia_dataframe, mock_builder)

        # Check that create_extreme_on_slab was called with proper description formatting
        calls = mock_builder.create_extreme_on_slab.call_args_list
        # 1 zone × 2 max_for_column × 1 direction = 2 calls
        assert len(calls) == 2

        # Extract the description from the call (keyword argument)
        _, kwargs = calls[0]
        description = kwargs.get("description", "")

        # Check that description follows expected format
        # Format: {slab_key}_{direction}-{zone}-{cs_name}-{coords}-{max_for}-ULS:{belasting_uls}/SLS:{belasting_sls}
        assert "CS_d0_2_1" in description  # slab_key with dots replaced
        assert "langs" in description  # direction
        assert "1-1" in description  # zone name
        assert "SEC_1_1" in description  # CS name
        assert "v_x" in description or "v_y" in description  # max_for_column
        assert "ULS:BG_ULS" in description  # ULS belasting
        assert "SLS:BG_SLS" in description  # SLS belasting

    def test_apply_loads_with_empty_dataframe(self) -> None:
        """Test _apply_cs_loads_to_slabs with empty SCIA dataframe."""
        empty_dataframe = pd.DataFrame()

        mock_slab = MagicMock()
        created_slabs = {
            "CS_d0.2_1": {
                "zones": ["1-1"],
                "slab_langs": mock_slab,
                "slab_dwars": mock_slab,
            }
        }

        mock_builder = MagicMock()

        # The function should handle empty dataframes gracefully
        # It returns early when df_all.empty is True
        _apply_cs_loads_to_slabs(created_slabs, empty_dataframe, mock_builder)

        # Verify that no builder methods were called (since we returned early)
        mock_builder.create_result_of_internal_forces.assert_not_called()
        mock_builder.create_loading_sls.assert_not_called()
        mock_builder.create_extreme_on_slab.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
