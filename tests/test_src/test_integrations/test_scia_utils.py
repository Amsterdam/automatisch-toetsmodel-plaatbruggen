"""
Tests for SCIA utils load framework.

These tests verify the load framework functions for creating load groups, cases,
combinations, and surface loads using the SCIA SDK.
"""

from unittest.mock import Mock, patch

import pytest


class TestSCIAAvailabilityCheck:
    """Test SCIA availability checking."""

    @patch("src.integrations.scia_utils.scia", None)
    def test_check_scia_availability_unavailable(self) -> None:
        """Test SCIA availability check when SCIA is not available."""
        from src.integrations.scia_utils import _check_scia_availability

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            _check_scia_availability()

    @patch("src.integrations.scia_utils.scia")
    @pytest.mark.usefixtures("_mock_scia")
    def test_check_scia_availability_available(self) -> None:
        """Test SCIA availability check when SCIA is available."""
        from src.integrations.scia_utils import _check_scia_availability

        # Should not raise exception
        _check_scia_availability()


class TestLoadGroupCreation:
    """Test load group creation functions."""

    @patch("src.integrations.scia_utils.scia")
    def test_create_load_group_by_type_permanent(self, mock_scia: Mock) -> None:
        """Test creating permanent load group."""
        from src.integrations.scia_utils import create_load_group_by_type

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_model.create_load_group.return_value = mock_load_group

        # Mock SCIA enums
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CAT_A = "CAT_A_ENUM"

        result = create_load_group_by_type(mock_model, "PERMANENT", "LG_Dead")

        # Verify calls
        mock_model.create_load_group.assert_called_once_with("LG_Dead", "PERMANENT_ENUM", "STANDARD_ENUM", "CAT_A_ENUM")
        assert result is mock_load_group

    @patch("src.integrations.scia_utils.scia")
    def test_create_load_group_by_type_variable(self, mock_scia: Mock) -> None:
        """Test creating variable load group."""
        from src.integrations.scia_utils import create_load_group_by_type

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_model.create_load_group.return_value = mock_load_group

        # Mock SCIA enums
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.EXCLUSIVE = "EXCLUSIVE_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CAT_A = "CAT_A_ENUM"

        result = create_load_group_by_type(mock_model, "VARIABLE", "LG_Traffic", "EXCLUSIVE")

        # Verify calls
        mock_model.create_load_group.assert_called_once_with("LG_Traffic", "VARIABLE_ENUM", "EXCLUSIVE_ENUM", "CAT_A_ENUM")
        assert result is mock_load_group

    @patch("src.integrations.scia_utils.scia")
    @pytest.mark.usefixtures("_mock_scia")
    def test_create_load_group_by_type_invalid_option(self) -> None:
        """Test error handling for invalid load option."""
        from src.integrations.scia_utils import create_load_group_by_type

        mock_model = Mock()

        with pytest.raises(KeyError):
            create_load_group_by_type(mock_model, "INVALID", "LG_Test")

    @patch("src.integrations.scia_utils.scia", None)
    def test_create_load_group_by_type_no_scia(self) -> None:
        """Test load group creation without SCIA SDK."""
        from src.integrations.scia_utils import create_load_group_by_type

        mock_model = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_load_group_by_type(mock_model, "PERMANENT", "LG_Test")


class TestLoadCaseCreation:
    """Test load case creation functions."""

    @patch("src.integrations.scia_utils.scia")
    def test_create_load_case_complete_permanent(self, mock_scia: Mock) -> None:
        """Test creating permanent load case."""
        from src.integrations.scia_utils import create_load_case_complete

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_model.create_permanent_load_case.return_value = mock_load_case

        # Mock SCIA enums
        mock_scia.LoadCase.PermanentLoadType.STANDARD = "STANDARD_ENUM"

        result = create_load_case_complete(mock_model, mock_load_group, "G1", "Dead load", "PERMANENT")

        # Verify calls
        mock_model.create_permanent_load_case.assert_called_once_with("G1", "Dead load", mock_load_group, "STANDARD_ENUM")
        assert result is mock_load_case

    @patch("src.integrations.scia_utils.scia")
    def test_create_load_case_complete_variable(self, mock_scia: Mock) -> None:
        """Test creating variable load case."""
        from src.integrations.scia_utils import create_load_case_complete

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_model.create_variable_load_case.return_value = mock_load_case

        # Mock SCIA enums
        mock_scia.LoadCase.VariableLoadType.STATIC = "STATIC_ENUM"
        mock_scia.LoadCase.Specification.STATIC_WIND = "WIND_ENUM"
        mock_scia.LoadCase.Duration.MEDIUM = "MEDIUM_ENUM"

        result = create_load_case_complete(
            mock_model, mock_load_group, "Q1", "Wind load", "VARIABLE", variable_type="STATIC", specification="STATIC_WIND", duration="MEDIUM"
        )

        # Verify calls
        mock_model.create_variable_load_case.assert_called_once_with("Q1", "Wind load", mock_load_group, "STATIC_ENUM", "WIND_ENUM", "MEDIUM_ENUM")
        assert result is mock_load_case

    @patch("src.integrations.scia_utils.scia")
    @pytest.mark.usefixtures("_mock_scia")
    def test_create_load_case_complete_invalid_type(self) -> None:
        """Test error handling for invalid case type."""
        from src.integrations.scia_utils import create_load_case_complete

        mock_model = Mock()
        mock_load_group = Mock()

        with pytest.raises(ValueError, match="Invalid case_type 'INVALID'"):
            create_load_case_complete(mock_model, mock_load_group, "X1", "Invalid", "INVALID")

    @patch("src.integrations.scia_utils.scia")
    def test_create_load_case_complete_default_parameters(self, mock_scia: Mock) -> None:
        """Test load case creation with default parameters."""
        from src.integrations.scia_utils import create_load_case_complete

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_model.create_variable_load_case.return_value = mock_load_case

        # Mock SCIA enums with defaults
        mock_scia.LoadCase.VariableLoadType.STATIC = "STATIC_ENUM"
        mock_scia.LoadCase.Specification.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadCase.Duration.SHORT = "SHORT_ENUM"

        result = create_load_case_complete(mock_model, mock_load_group, "Q1", "Variable load", "VARIABLE")

        # Verify defaults are used
        mock_model.create_variable_load_case.assert_called_once_with(
            "Q1", "Variable load", mock_load_group, "STATIC_ENUM", "STANDARD_ENUM", "SHORT_ENUM"
        )
        assert result is mock_load_case


class TestLoadCombinationCreation:
    """Test load combination creation functions."""

    @patch("src.integrations.scia_utils.scia")
    def test_create_load_combination_by_type_uls(self, mock_scia: Mock) -> None:
        """Test creating ULS load combination."""
        from src.integrations.scia_utils import create_load_combination_by_type

        # Setup mocks
        mock_model = Mock()
        mock_load_case_1 = Mock()
        mock_load_case_2 = Mock()
        mock_combination = Mock()
        mock_model.create_load_combination.return_value = mock_combination

        # Mock SCIA enums
        mock_scia.LoadCombination.Type.EN_ULS_SET_B = "ULS_ENUM"

        load_cases = {mock_load_case_1: 1.35, mock_load_case_2: 1.5}
        result = create_load_combination_by_type(mock_model, "ULS", "ULS_Combo", load_cases, "Test combination")

        # Verify calls
        mock_model.create_load_combination.assert_called_once_with("ULS_Combo", "ULS_ENUM", load_cases, description="Test combination")
        assert result is mock_combination

    @patch("src.integrations.scia_utils.scia")
    def test_create_load_combination_by_type_sls(self, mock_scia: Mock) -> None:
        """Test creating SLS load combination."""
        from src.integrations.scia_utils import create_load_combination_by_type

        # Setup mocks
        mock_model = Mock()
        mock_load_case = Mock()
        mock_combination = Mock()
        mock_model.create_load_combination.return_value = mock_combination

        # Mock SCIA enums
        mock_scia.LoadCombination.Type.EN_SLS_CHAR = "SLS_ENUM"

        load_cases = {mock_load_case: 1.0}
        result = create_load_combination_by_type(mock_model, "SLS_CHAR", "SLS_Combo", load_cases)

        # Verify default description is generated
        mock_model.create_load_combination.assert_called_once_with("SLS_Combo", "SLS_ENUM", load_cases, description="Load combination: SLS_Combo")
        assert result is mock_combination

    @patch("src.integrations.scia_utils.scia")
    @pytest.mark.usefixtures("_mock_scia")
    def test_create_load_combination_by_type_invalid(self) -> None:
        """Test error handling for invalid combination type."""
        from src.integrations.scia_utils import create_load_combination_by_type

        mock_model = Mock()
        mock_load_case = Mock()

        with pytest.raises(ValueError, match="Invalid combination_type 'INVALID'"):
            create_load_combination_by_type(mock_model, "INVALID", "Test", {mock_load_case: 1.0})

    @patch("src.integrations.scia_utils.scia")
    def test_create_load_combination_by_type_all_types(self, mock_scia: Mock) -> None:
        """Test that all combination types are supported."""
        from src.integrations.scia_utils import create_load_combination_by_type

        # Setup mocks
        mock_model = Mock()
        mock_load_case = Mock()
        mock_combination = Mock()
        mock_model.create_load_combination.return_value = mock_combination

        # Mock all SCIA enums
        combination_types = [
            "ULS",
            "ULS_SET_B",
            "ULS_SET_C",
            "ENVELOPE_ULS",
            "LINEAR_ULS",
            "SLS",
            "SLS_CHAR",
            "SLS_FREQ",
            "SLS_QUASI",
            "ENVELOPE_SLS",
            "LINEAR_SLS",
            "ACCIDENTAL",
            "ACCIDENTAL_1",
            "ACCIDENTAL_2",
            "SEISMIC",
        ]

        for combo_type in combination_types:
            mock_scia.LoadCombination.Type.__dict__[combo_type.replace("_", "_")] = f"{combo_type}_ENUM"

        # Test each combination type
        for combo_type in combination_types:
            result = create_load_combination_by_type(mock_model, combo_type, f"Combo_{combo_type}", {mock_load_case: 1.0})
            assert result is mock_combination


class TestPatchSurfaceLoadCreation:
    """Test patch surface load creation functions."""

    @patch("src.integrations.scia_utils.scia")
    def test_create_patch_surface_load_success(self, mock_scia: Mock) -> None:
        """Test successful patch surface load creation."""
        from src.integrations.scia_utils import create_patch_surface_load

        # Setup mocks
        mock_model = Mock()
        mock_load_case = Mock()
        mock_surface_load = Mock()
        mock_model.create_free_surface_load.return_value = mock_surface_load

        # Mock SCIA enums
        mock_scia.FreeSurfaceLoad.Direction.Z = "Z_ENUM"
        mock_scia.FreeSurfaceLoad.Distribution.UNIFORM = "UNIFORM_ENUM"

        # Test data: 2x2 meter square
        corner_points = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 2.0, 0.0), (0.0, 2.0, 0.0)]
        load_value = 1000.0  # N/m²

        result = create_patch_surface_load(mock_model, mock_load_case, corner_points, load_value, "TestLoad")

        # Verify calls
        expected_xy_points = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
        expected_total_load = 1000.0 * 4.0  # 4 m² * 1000 N/m² = 4000 N

        mock_model.create_free_surface_load.assert_called_once_with(
            name="TestLoad",
            load_case=mock_load_case,
            direction="Z_ENUM",
            q1=expected_total_load,
            points=expected_xy_points,
            distribution="UNIFORM_ENUM",
        )
        assert result is mock_surface_load

    @patch("src.integrations.scia_utils.scia")
    @pytest.mark.usefixtures("_mock_scia")
    def test_create_patch_surface_load_invalid_points(self) -> None:
        """Test error handling for invalid number of points."""
        from src.integrations.scia_utils import create_patch_surface_load

        mock_model = Mock()
        mock_load_case = Mock()

        # Test with 3 points (should be 4)
        corner_points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]

        with pytest.raises(ValueError, match="Exactly 4 corner points required, got 3"):
            create_patch_surface_load(mock_model, mock_load_case, corner_points, 1000.0)

    @patch("src.integrations.scia_utils.scia")
    def test_create_patch_surface_load_area_calculation(self, mock_scia: Mock) -> None:
        """Test area calculation for different polygon shapes."""
        from src.integrations.scia_utils import create_patch_surface_load

        # Setup mocks
        mock_model = Mock()
        mock_load_case = Mock()
        mock_surface_load = Mock()
        mock_model.create_free_surface_load.return_value = mock_surface_load

        # Mock SCIA enums
        mock_scia.FreeSurfaceLoad.Direction.Z = "Z_ENUM"
        mock_scia.FreeSurfaceLoad.Distribution.UNIFORM = "UNIFORM_ENUM"

        # Test with triangle-like shape (but still 4 points)
        # Points forming a trapezoid: base 4m, top 2m, height 3m
        corner_points = [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (3.0, 3.0, 0.0), (1.0, 3.0, 0.0)]
        load_value = 500.0  # N/m²

        create_patch_surface_load(mock_model, mock_load_case, corner_points, load_value)

        # Calculate expected area using shoelace formula
        # Area = 0.5 * |sum of (x_i * y_i+1 - x_i+1 * y_i)|
        # For trapezoid: (0,0), (4,0), (3,3), (1,3)
        # Area = 0.5 * |0*0 - 4*0 + 4*3 - 3*0 + 3*3 - 1*3 + 1*0 - 0*3|
        # Area = 0.5 * |0 + 12 + 9 - 3 + 0| = 0.5 * 18 = 9 m²
        expected_total_load = 500.0 * 9.0  # 9 m² * 500 N/m² = 4500 N

        # Verify the total load calculation
        call_args = mock_model.create_free_surface_load.call_args
        assert call_args[1]["q1"] == expected_total_load

    @patch("src.integrations.scia_utils.scia", None)
    def test_create_patch_surface_load_no_scia(self) -> None:
        """Test patch surface load creation without SCIA SDK."""
        from src.integrations.scia_utils import create_patch_surface_load

        mock_model = Mock()
        mock_load_case = Mock()
        corner_points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_patch_surface_load(mock_model, mock_load_case, corner_points, 1000.0)


class TestLegacyFunction:
    """Test legacy function for backwards compatibility."""

    @patch("src.integrations.scia_utils.create_load_group_by_type")
    @patch("src.integrations.scia_utils.create_load_case_complete")
    def test_create_load_case_with_name_default(self, mock_create_case: Mock, mock_create_group: Mock) -> None:
        """Test legacy function with default parameters."""
        from src.integrations.scia_utils import create_load_case_with_name

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_group.return_value = mock_load_group
        mock_create_case.return_value = mock_load_case

        result = create_load_case_with_name(mock_model, "TestCase")

        # Verify calls
        mock_create_group.assert_called_once_with(mock_model, "VARIABLE", "LG_TestCase")
        mock_create_case.assert_called_once_with(mock_model, mock_load_group, "TestCase", "VARIABLE load case: TestCase", "VARIABLE")
        assert result is mock_load_case

    @patch("src.integrations.scia_utils.create_load_group_by_type")
    @patch("src.integrations.scia_utils.create_load_case_complete")
    def test_create_load_case_with_name_permanent(self, mock_create_case: Mock, mock_create_group: Mock) -> None:
        """Test legacy function with permanent load type."""
        from src.integrations.scia_utils import create_load_case_with_name

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_create_group.return_value = mock_load_group
        mock_create_case.return_value = mock_load_case

        result = create_load_case_with_name(mock_model, "DeadLoad", "PERMANENT")

        # Verify calls
        mock_create_group.assert_called_once_with(mock_model, "PERMANENT", "LG_DeadLoad")
        mock_create_case.assert_called_once_with(mock_model, mock_load_group, "DeadLoad", "PERMANENT load case: DeadLoad", "PERMANENT")
        assert result is mock_load_case


class TestPolygonAreaCalculation:
    """Test polygon area calculation using shoelace formula."""

    def test_polygon_area_rectangle(self) -> None:
        """Test area calculation for rectangle."""
        from src.integrations.scia_utils import create_patch_surface_load

        # Extract the polygon_area function from the module
        # We'll test it indirectly through the patch surface load function
        # by checking the total load calculation

        # Mock everything except the area calculation
        with patch("src.integrations.scia_utils.scia") as mock_scia:
            mock_model = Mock()
            mock_load_case = Mock()
            mock_surface_load = Mock()
            mock_model.create_free_surface_load.return_value = mock_surface_load

            # Mock SCIA enums
            mock_scia.FreeSurfaceLoad.Direction.Z = "Z_ENUM"
            mock_scia.FreeSurfaceLoad.Distribution.UNIFORM = "UNIFORM_ENUM"

            # 3x4 rectangle
            corner_points = [(0.0, 0.0, 0.0), (3.0, 0.0, 0.0), (3.0, 4.0, 0.0), (0.0, 4.0, 0.0)]
            load_value = 100.0  # N/m²

            create_patch_surface_load(mock_model, mock_load_case, corner_points, load_value)

            # Expected area = 3 * 4 = 12 m²
            # Expected total load = 100 * 12 = 1200 N
            call_args = mock_model.create_free_surface_load.call_args
            assert call_args[1]["q1"] == 1200.0

    def test_polygon_area_triangle_approximation(self) -> None:
        """Test area calculation for triangle-like shape."""
        from src.integrations.scia_utils import create_patch_surface_load

        with patch("src.integrations.scia_utils.scia") as mock_scia:
            mock_model = Mock()
            mock_load_case = Mock()
            mock_surface_load = Mock()
            mock_model.create_free_surface_load.return_value = mock_surface_load

            # Mock SCIA enums
            mock_scia.FreeSurfaceLoad.Direction.Z = "Z_ENUM"
            mock_scia.FreeSurfaceLoad.Distribution.UNIFORM = "UNIFORM_ENUM"

            # Triangle with one very small side (approximating triangle)
            corner_points = [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (2.0, 3.0, 0.0), (2.0, 3.0, 0.0)]
            load_value = 200.0  # N/m²

            create_patch_surface_load(mock_model, mock_load_case, corner_points, load_value)

            # This is a degenerate quadrilateral (triangle with doubled point)
            # Area calculation should still work
            call_args = mock_model.create_free_surface_load.call_args
            total_load = call_args[1]["q1"]
            assert total_load > 0  # Should have positive area

    def test_polygon_area_zero_area(self) -> None:
        """Test area calculation for degenerate polygon."""
        from src.integrations.scia_utils import create_patch_surface_load

        with patch("src.integrations.scia_utils.scia") as mock_scia:
            mock_model = Mock()
            mock_load_case = Mock()
            mock_surface_load = Mock()
            mock_model.create_free_surface_load.return_value = mock_surface_load

            # Mock SCIA enums
            mock_scia.FreeSurfaceLoad.Direction.Z = "Z_ENUM"
            mock_scia.FreeSurfaceLoad.Distribution.UNIFORM = "UNIFORM_ENUM"

            # All points on same line (zero area)
            corner_points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (3.0, 0.0, 0.0)]
            load_value = 1000.0  # N/m²

            create_patch_surface_load(mock_model, mock_load_case, corner_points, load_value)

            # Expected area = 0, so total load = 0
            call_args = mock_model.create_free_surface_load.call_args
            assert call_args[1]["q1"] == 0.0


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple functions."""

    @patch("src.integrations.scia_utils.scia")
    def test_complete_load_workflow(self, mock_scia: Mock) -> None:
        """Test complete workflow: group -> case -> combination -> load."""
        from src.integrations.scia_utils import (
            create_load_case_complete,
            create_load_combination_by_type,
            create_load_group_by_type,
            create_patch_surface_load,
        )

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()
        mock_combination = Mock()
        mock_surface_load = Mock()

        mock_model.create_load_group.return_value = mock_load_group
        mock_model.create_permanent_load_case.return_value = mock_load_case
        mock_model.create_load_combination.return_value = mock_combination
        mock_model.create_free_surface_load.return_value = mock_surface_load

        # Mock all required SCIA enums
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CAT_A = "CAT_A_ENUM"
        mock_scia.LoadCase.PermanentLoadType.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadCombination.Type.EN_ULS_SET_B = "ULS_ENUM"
        mock_scia.FreeSurfaceLoad.Direction.Z = "Z_ENUM"
        mock_scia.FreeSurfaceLoad.Distribution.UNIFORM = "UNIFORM_ENUM"

        # Execute complete workflow
        # Step 1: Create load group
        load_group = create_load_group_by_type(mock_model, "PERMANENT", "LG_Dead")
        assert load_group is mock_load_group

        # Step 2: Create load case
        load_case = create_load_case_complete(mock_model, load_group, "G1", "Dead load", "PERMANENT")
        assert load_case is mock_load_case

        # Step 3: Create load combination
        combination = create_load_combination_by_type(mock_model, "ULS", "ULS_Dead", {load_case: 1.35})
        assert combination is mock_combination

        # Step 4: Apply load
        corner_points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
        surface_load = create_patch_surface_load(mock_model, load_case, corner_points, 5000.0, "DeadLoad")
        assert surface_load is mock_surface_load

        # Verify all functions were called
        mock_model.create_load_group.assert_called_once()
        mock_model.create_permanent_load_case.assert_called_once()
        mock_model.create_load_combination.assert_called_once()
        mock_model.create_free_surface_load.assert_called_once()

    @patch("src.integrations.scia_utils.scia")
    def test_multiple_load_cases_same_group(self, mock_scia: Mock) -> None:
        """Test creating multiple load cases in same group."""
        from src.integrations.scia_utils import create_load_case_complete, create_load_group_by_type

        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case_1 = Mock()
        mock_load_case_2 = Mock()

        mock_model.create_load_group.return_value = mock_load_group
        mock_model.create_variable_load_case.side_effect = [mock_load_case_1, mock_load_case_2]

        # Mock required SCIA enums
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CAT_A = "CAT_A_ENUM"
        mock_scia.LoadCase.VariableLoadType.STATIC = "STATIC_ENUM"
        mock_scia.LoadCase.Specification.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadCase.Duration.SHORT = "SHORT_ENUM"

        # Create one load group
        load_group = create_load_group_by_type(mock_model, "VARIABLE", "LG_Traffic")

        # Create multiple load cases in same group
        create_load_case_complete(mock_model, load_group, "Q1_LM1", "Load Model 1", "VARIABLE")
        create_load_case_complete(mock_model, load_group, "Q2_LM2", "Load Model 2", "VARIABLE")

        # Verify both cases use same group
        assert mock_model.create_variable_load_case.call_count == 2
        call_args_1 = mock_model.create_variable_load_case.call_args_list[0]
        call_args_2 = mock_model.create_variable_load_case.call_args_list[1]

        assert call_args_1[0][2] is mock_load_group  # Same group
        assert call_args_2[0][2] is mock_load_group  # Same group
        assert call_args_1[0][0] == "Q1_LM1"  # Different names
        assert call_args_2[0][0] == "Q2_LM2"  # Different names


if __name__ == "__main__":
    pytest.main([__file__])
