"""
Tests for SCIA load cases module.

Tests for load case creation functions using direct SCIA API.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_cases import (
    create_basic_permanent_load_cases,
    create_self_weight_load_case,
    create_tandem_load_case,
    create_wind_load_case,
)


class TestSelfWeightLoadCase:
    """Test self-weight load case creation using direct SCIA API."""

    @patch("src.integrations.scia_integration.scia_load_cases.scia")
    def test_create_self_weight_load_case_success(self, mock_scia: Mock) -> None:
        """Test successful self-weight load case creation."""
        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()

        mock_model.create_permanent_load_case.return_value = mock_load_case
        mock_scia.LoadCase.PermanentLoadType.SELF_WEIGHT = "SELF_WEIGHT_ENUM"

        result = create_self_weight_load_case(mock_model, mock_load_group)

        # Verify direct SCIA API call
        mock_model.create_permanent_load_case.assert_called_once_with(
            "BG01",
            "Eigen gewicht",
            mock_load_group,
            "SELF_WEIGHT_ENUM",
        )
        assert result is mock_load_case

    def test_create_self_weight_load_case_no_viktor(self) -> None:
        """Test self-weight load case creation without VIKTOR SDK."""
        mock_model = Mock()
        mock_load_group = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_self_weight_load_case(mock_model, mock_load_group)


class TestWindLoadCase:
    """Test wind load case creation."""

    @patch("src.integrations.scia_integration.scia_load_cases.create_load_case_complete")
    def test_create_wind_load_case_success(self, mock_create_case: Mock) -> None:
        """Test successful wind load case creation."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        result = create_wind_load_case(mock_model, mock_load_group)

        # Verify call to utility function with correct parameters
        mock_create_case.assert_called_once_with(
            model=mock_model,
            load_group=mock_load_group,
            case_name="Q2_Wind",
            description="Wind Load",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STATIC_WIND",
            duration="SHORT",
        )
        assert result is mock_load_case


class TestTandemLoadCase:
    """Test tandem load case creation."""

    @patch("src.integrations.scia_integration.scia_load_cases.create_load_case_complete")
    def test_create_tandem_load_case_theoretical_mode(self, mock_create_case: Mock) -> None:
        """Test tandem load case creation in theoretical mode."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        result = create_tandem_load_case(mock_model, mock_load_group, "TH6001", mode="theoretical")

        # Verify call with theoretical mode description
        mock_create_case.assert_called_once_with(
            model=mock_model,
            load_group=mock_load_group,
            case_name="TH6001",
            description="Tandem System - Theoretical Lane TH6001",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        assert result is mock_load_case

    @patch("src.integrations.scia_integration.scia_load_cases.create_load_case_complete")
    def test_create_tandem_load_case_eurocode_mode(self, mock_create_case: Mock) -> None:
        """Test tandem load case creation in eurocode mode."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        result = create_tandem_load_case(mock_model, mock_load_group, "BG6001", mode="eurocode")

        # Verify call with eurocode mode description
        mock_create_case.assert_called_once_with(
            model=mock_model,
            load_group=mock_load_group,
            case_name="BG6001",
            description="Load Model 1 - Tandem System BG6001",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        assert result is mock_load_case

    @patch("src.integrations.scia_integration.scia_load_cases.create_load_case_complete")
    def test_create_tandem_load_case_actual_mode(self, mock_create_case: Mock) -> None:
        """Test tandem load case creation in actual mode."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        result = create_tandem_load_case(mock_model, mock_load_group, "AC6001", mode="actual")

        # Verify call with actual mode description
        mock_create_case.assert_called_once_with(
            model=mock_model,
            load_group=mock_load_group,
            case_name="AC6001",
            description="Tandem System - Actual Lane AC6001",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        assert result is mock_load_case

    @patch("src.integrations.scia_integration.scia_load_cases.create_load_case_complete")
    def test_create_tandem_load_case_shiftable_mode(self, mock_create_case: Mock) -> None:
        """Test tandem load case creation in shiftable mode."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        result = create_tandem_load_case(mock_model, mock_load_group, "SF6001", mode="shiftable")

        # Verify call with shiftable mode description
        mock_create_case.assert_called_once_with(
            model=mock_model,
            load_group=mock_load_group,
            case_name="SF6001",
            description="Tandem System - Shiftable Position SF6001",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        assert result is mock_load_case

    @patch("src.integrations.scia_integration.scia_load_cases.create_load_case_complete")
    def test_create_tandem_load_case_unknown_mode(self, mock_create_case: Mock) -> None:
        """Test tandem load case creation with unknown mode (should use default)."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        result = create_tandem_load_case(mock_model, mock_load_group, "UN6001", mode="unknown")

        # Verify call with default description
        mock_create_case.assert_called_once_with(
            model=mock_model,
            load_group=mock_load_group,
            case_name="UN6001",
            description="Tandem System UN6001",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        assert result is mock_load_case

    @patch("src.integrations.scia_integration.scia_load_cases.create_load_case_complete")
    def test_create_tandem_load_case_default_mode(self, mock_create_case: Mock) -> None:
        """Test tandem load case creation with default mode."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        result = create_tandem_load_case(mock_model, mock_load_group, "BG6001")  # No mode specified

        # Verify call with theoretical mode (default)
        mock_create_case.assert_called_once_with(
            model=mock_model,
            load_group=mock_load_group,
            case_name="BG6001",
            description="Tandem System - Theoretical Lane BG6001",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        assert result is mock_load_case


class TestBasicPermanentLoadCases:
    """Test basic permanent load cases creation."""

    @patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case")
    def test_create_basic_permanent_load_cases_success(self, mock_create_self_weight: Mock) -> None:
        """Test successful creation of basic permanent load cases."""
        mock_model = Mock()
        mock_permanent_group = Mock()
        mock_self_weight_case = Mock()

        mock_create_self_weight.return_value = mock_self_weight_case

        result = create_basic_permanent_load_cases(mock_model, mock_permanent_group)

        # Verify self-weight case creation
        mock_create_self_weight.assert_called_once_with(mock_model, mock_permanent_group)

        # Verify return structure
        assert isinstance(result, dict)
        assert "self_weight" in result
        assert result["self_weight"] is mock_self_weight_case

    @patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case")
    def test_create_basic_permanent_load_cases_extensible(self, mock_create_self_weight: Mock) -> None:
        """Test that the function structure is extensible for future load cases."""
        mock_model = Mock()
        mock_permanent_group = Mock()
        mock_self_weight_case = Mock()

        mock_create_self_weight.return_value = mock_self_weight_case

        result = create_basic_permanent_load_cases(mock_model, mock_permanent_group)

        # Currently only self-weight, but structure allows for expansion
        expected_keys = {"self_weight"}
        assert set(result.keys()) == expected_keys

        # Future load cases could be added here:
        # - superimposed_dead_loads
        # - prestressing_loads
        # - construction_loads
        # etc.


class TestLoadCaseNamingConventions:
    """Test load case naming conventions match SCIA interface."""

    @patch("src.integrations.scia_integration.scia_load_cases.scia")
    def test_self_weight_naming_matches_scia_interface(self, mock_scia: Mock) -> None:
        """Test that self-weight load case name and description match SCIA interface."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()

        mock_model.create_permanent_load_case.return_value = mock_load_case
        mock_scia.LoadCase.PermanentLoadType.SELF_WEIGHT = "SELF_WEIGHT_ENUM"

        create_self_weight_load_case(mock_model, mock_load_group)

        # Verify exact naming from SCIA interface
        call_args = mock_model.create_permanent_load_case.call_args[0]
        assert call_args[0] == "BG01"  # Load case name
        assert call_args[1] == "Eigen gewicht"  # Description (Dutch)

    @patch("src.integrations.scia_integration.scia_load_cases.create_load_case_complete")
    def test_tandem_naming_pattern_consistency(self, mock_create_case: Mock) -> None:
        """Test that tandem load case naming is consistent."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_case.return_value = mock_load_case

        # Test different naming patterns
        test_cases = [
            ("TH6001", "theoretical"),
            ("BG6001", "eurocode"),
            ("AC6001", "actual"),
            ("SF6001", "shiftable"),
        ]

        for case_name, mode in test_cases:
            create_tandem_load_case(mock_model, mock_load_group, case_name, mode=mode)

        # Verify all calls used correct case names
        calls = mock_create_case.call_args_list
        assert len(calls) == 4

        for i, (expected_name, _) in enumerate(test_cases):
            call_kwargs = calls[i][1]
            assert call_kwargs["case_name"] == expected_name


if __name__ == "__main__":
    pytest.main([__file__])
