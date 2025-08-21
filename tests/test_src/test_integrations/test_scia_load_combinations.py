"""
Tests for SCIA load combinations module (table-driven pipeline).

These tests validate the pipeline that:
- Reads/filters a combination table
- Maps subjects to case series
- Creates combinations via the builder
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from app.bridge.parametrization import BridgeParametrization
from src.integrations.scia_integration.scia_load_combinations import create_all_load_combinations, create_load_combination
from src.integrations.scia_integration.scia_model_interface import SciaCombinationType


@pytest.fixture
def mock_builder() -> Mock:
    """Fixture to provide a mocked SciaModelBuilder."""
    return Mock()


class TestCreateLoadCombination:
    """Tests for the base load combination creation function."""

    def test_create_load_combination(self, mock_builder: Mock) -> None:
        """Test basic load combination creation."""
        mock_lc1 = Mock()
        mock_lc2 = Mock()
        factors = {mock_lc1: 1.5, mock_lc2: 1.0}
        create_load_combination(mock_builder, SciaCombinationType.EN_ULS_SET_B, "TestCombo", factors, "A test combo")

        mock_builder.create_load_combination.assert_called_once_with(
            name="TestCombo",
            combination_type=SciaCombinationType.EN_ULS_SET_B,
            load_case_factors=factors,
            description="A test combo",
        )

    def test_create_load_combination_default_description(self, mock_builder: Mock) -> None:
        """Test load combination creation with default description."""
        create_load_combination(mock_builder, SciaCombinationType.EN_SLS_CHAR, "DefaultDescCombo", {})
        mock_builder.create_load_combination.assert_called_once()
        assert mock_builder.create_load_combination.call_args[1]["description"] == "Load combination: DefaultDescCombo"


class TestCreateAllLoadCombinationsPipeline:
    """Tests for the table-driven pipeline in create_all_load_combinations."""

    @patch("src.integrations.scia_integration.scia_load_combinations.get_leading_action_positions")
    @patch("src.integrations.scia_integration.scia_load_combinations.get_project_scope")
    @patch("src.integrations.scia_integration.scia_load_combinations.prepare_combination_table")
    def test_uls_sls_fatigue_created_from_table(
        self,
        mock_prepare: Mock,
        mock_scope: Mock,
        mock_leading: Mock,
        params: BridgeParametrization,
        mock_builder: Mock,
    ) -> None:
        """Test that ULS, SLS, and fatigue combinations are created from table."""
        # Build a minimal table with one row per family
        combination_table = pd.DataFrame(
            data={
                "Permanent": [1.35, 1.00, 1.00],
                "Mensenmenigte": [1.50, 0.30, 0.00],
            },
            index=[
                "6.10a COMBO_ULS_A",
                "6.14b COMBO_SLS_B",
                "6.67 COMBO_FAT_A",
            ],
        )
        mock_prepare.return_value = combination_table
        mock_scope.return_value = ["Permanent", "Mensenmenigte"]
        mock_leading.return_value = [
            ("COMBO_ULS_A", "Permanent"),
            ("COMBO_SLS_B", "Permanent"),
            ("COMBO_FAT_A", "Permanent"),
        ]

        # Provide load cases per series mapping
        lc_sw = Mock(name="BG1001")
        lc_dead_1 = Mock(name="BG2001")
        lc_ped = Mock(name="BG5001")
        all_load_cases = {
            "self_weight": lc_sw,
            "dead_load_cases": {"asfalt": lc_dead_1},
            "pedestrian": lc_ped,
        }

        combinations = create_all_load_combinations(params, mock_builder, all_load_cases)

        # Expect 3 combinations created
        assert mock_builder.create_load_combination.call_count == 3
        assert len(combinations) == 3

        # Validate the first ULS call has expected type and includes mapped cases
        first_call_kwargs = mock_builder.create_load_combination.call_args_list[0].kwargs
        assert first_call_kwargs["combination_type"] == SciaCombinationType.ENVELOPE_ULTIMATE
        uls_factors = first_call_kwargs["load_case_factors"]
        # Permanent -> self_weight + dead_load_cases
        assert uls_factors[lc_sw] == 1.35
        assert uls_factors[lc_dead_1] == 1.35
        # Mensenmenigte -> pedestrian
        assert uls_factors[lc_ped] == 1.50

        # SLS and Fatigue should be serviceability envelope
        other_types = [c.kwargs["combination_type"] for c in mock_builder.create_load_combination.call_args_list[1:]]
        assert all(t == SciaCombinationType.ENVELOPE_SERVICEABILITY for t in other_types)

    @patch("src.integrations.scia_integration.scia_load_combinations.get_leading_action_positions")
    @patch("src.integrations.scia_integration.scia_load_combinations.get_project_scope")
    @patch("src.integrations.scia_integration.scia_load_combinations.prepare_combination_table")
    def test_no_rows_after_filter_returns_empty(
        self,
        mock_prepare: Mock,
        mock_scope: Mock,
        mock_leading: Mock,
        params: BridgeParametrization,
        mock_builder: Mock,
    ) -> None:
        """Test that empty result is returned when no rows remain after filtering."""
        # Table that will be filtered out by leading action rows
        combination_table = pd.DataFrame(
            data={"Permanent": [1.0]},
            index=["6.10a OTHER"],
        )
        mock_prepare.return_value = combination_table
        mock_scope.return_value = ["Permanent"]
        mock_leading.return_value = [("NON_MATCHING", "Permanent")]

        combinations = create_all_load_combinations(params, mock_builder, {"self_weight": Mock(), "dead_load_cases": {}})

        # No combinations created
        assert combinations == []
