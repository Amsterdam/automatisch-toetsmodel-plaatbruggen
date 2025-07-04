"""
Tests for SCIA utilities module.

Tests for utility functions that support SCIA integration including load creation,
XML generation, analysis setup, and workflow orchestration.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_cases import (
    create_load_case_complete,
)
from src.integrations.scia_integration.scia_load_combinations import (
    create_load_combination_by_type,
)
from src.integrations.scia_integration.scia_loads import (
    create_patch_surface_load,
)
from src.integrations.scia_integration.scia_utils import (
    create_load_group_by_type,
    create_scia_analysis_from_template,
    generate_bridge_xml_files,
    generate_xml_from_model,
    setup_bridge_analysis,
)


class TestLoadCaseUtilities:
    """Test load case creation utilities."""

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_create_load_case_complete_permanent_case(self, mock_scia: Mock) -> None:
        """Test creating complete permanent load case."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()

        mock_model.create_permanent_load_case.return_value = mock_load_case
        mock_scia.LoadCase.PermanentLoadType.SELF_WEIGHT = "SELF_WEIGHT_ENUM"

        result = create_load_case_complete(
            model=mock_model,
            load_group=mock_load_group,
            case_name="BG01",
            description="Test permanent case",
            case_type="PERMANENT",
            permanent_type="SELF_WEIGHT",
        )

        # Verify permanent load case creation
        mock_model.create_permanent_load_case.assert_called_once_with(
            "BG01",
            "Test permanent case",
            mock_load_group,
            "SELF_WEIGHT_ENUM",
        )
        assert result is mock_load_case

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_create_load_case_complete_variable_case(self, mock_scia: Mock) -> None:
        """Test creating complete variable load case."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()

        mock_model.create_variable_load_case.return_value = mock_load_case
        mock_scia.LoadCase.VariableLoadType.STATIC = "STATIC_ENUM"
        mock_scia.LoadCase.VariableLoadSpecification.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadCase.VariableLoadDuration.SHORT = "SHORT_ENUM"

        result = create_load_case_complete(
            model=mock_model,
            load_group=mock_load_group,
            case_name="Q1",
            description="Test variable case",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )

        # Verify variable load case creation
        mock_model.create_variable_load_case.assert_called_once_with(
            "Q1",
            "Test variable case",
            mock_load_group,
            "STATIC_ENUM",
            "STANDARD_ENUM",
            "SHORT_ENUM",
        )
        assert result is mock_load_case

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_create_load_case_complete_invalid_case_type(self) -> None:
        """Test error handling for invalid case type."""
        mock_model = Mock()
        mock_load_group = Mock()

        with pytest.raises(ValueError, match="Unsupported case_type: INVALID"):
            create_load_case_complete(
                model=mock_model,
                load_group=mock_load_group,
                case_name="TEST",
                description="Test case",
                case_type="INVALID",
            )

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_create_load_case_complete_missing_permanent_type(self) -> None:
        """Test error handling for missing permanent type."""
        mock_model = Mock()
        mock_load_group = Mock()

        with pytest.raises(ValueError, match="permanent_type is required"):
            create_load_case_complete(
                model=mock_model,
                load_group=mock_load_group,
                case_name="BG01",
                description="Test case",
                case_type="PERMANENT",
            )

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_create_load_case_complete_missing_variable_params(self) -> None:
        """Test error handling for missing variable parameters."""
        mock_model = Mock()
        mock_load_group = Mock()

        with pytest.raises(ValueError, match="variable_type, specification, and duration are required"):
            create_load_case_complete(
                model=mock_model,
                load_group=mock_load_group,
                case_name="Q1",
                description="Test case",
                case_type="VARIABLE",
                variable_type="STATIC",
                # Missing specification and duration
            )

    def test_create_load_case_complete_no_viktor(self) -> None:
        """Test load case creation without VIKTOR SDK."""
        mock_model = Mock()
        mock_load_group = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_load_case_complete(
                model=mock_model,
                load_group=mock_load_group,
                case_name="BG01",
                description="Test case",
                case_type="PERMANENT",
                permanent_type="SELF_WEIGHT",
            )


class TestLoadGroupUtilities:
    """Test load group creation utilities."""

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_create_load_group_by_type_permanent(self, mock_scia: Mock) -> None:
        """Test creating permanent load group by type."""
        mock_model = Mock()
        mock_load_group = Mock()

        mock_model.create_load_group.return_value = mock_load_group
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"

        result = create_load_group_by_type(mock_model, "PERMANENT", "LG_Test")

        # Verify permanent load group creation
        mock_model.create_load_group.assert_called_once_with(
            "LG_Test",
            "PERMANENT_ENUM",
            "STANDARD_ENUM",
            "CONSTRUCTION_LOADS_ENUM",
        )
        assert result is mock_load_group

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_create_load_group_by_type_variable(self, mock_scia: Mock) -> None:
        """Test creating variable load group by type."""
        mock_model = Mock()
        mock_load_group = Mock()

        mock_model.create_load_group.return_value = mock_load_group
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.LIVE_LOADS = "LIVE_LOADS_ENUM"

        result = create_load_group_by_type(mock_model, "VARIABLE", "LG_Test")

        # Verify variable load group creation
        mock_model.create_load_group.assert_called_once_with(
            "LG_Test",
            "VARIABLE_ENUM",
            "STANDARD_ENUM",
            "LIVE_LOADS_ENUM",
        )
        assert result is mock_load_group

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_create_load_group_by_type_invalid_type(self) -> None:
        """Test error handling for invalid load group type."""
        mock_model = Mock()

        with pytest.raises(ValueError, match="Unsupported load_type: INVALID"):
            create_load_group_by_type(mock_model, "INVALID", "LG_Test")

    def test_create_load_group_by_type_no_viktor(self) -> None:
        """Test load group creation without VIKTOR SDK."""
        mock_model = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_load_group_by_type(mock_model, "PERMANENT", "LG_Test")


class TestLoadCombinationUtilities:
    """Test load combination creation functions."""

    @patch("src.integrations.scia_integration.scia_load_combinations.scia")
    def test_create_load_combination_by_type_uls(self, mock_scia: Mock) -> None:
        """Test successful load combination creation."""
        mock_model = Mock()
        mock_combination = Mock()
        mock_load_case = Mock()

        mock_model.create_load_combination.return_value = mock_combination
        mock_scia.LoadCombination.Type.EN_ULS_SET_B = "ULS_ENUM"

        # Test with load case dictionary
        load_cases = {mock_load_case: 1.35}

        result = create_load_combination_by_type(
            model=mock_model,
            combination_type="ULS",
            combination_name="ULS01",
            load_cases=load_cases,
            description="Test combination",
        )

        # Verify combination creation
        mock_model.create_load_combination.assert_called_once_with(
            "ULS01",
            "ULS_ENUM",
            load_cases,
            description="Test combination",
        )
        assert result is mock_combination

    @patch("src.integrations.scia_integration.scia_load_combinations.scia")
    def test_create_load_combination_with_cases_multiple_cases(self, mock_scia: Mock) -> None:
        """Test load combination creation with multiple cases."""
        mock_model = Mock()
        mock_combination = Mock()
        mock_load_case_1 = Mock()
        mock_load_case_2 = Mock()

        mock_model.create_load_combination.return_value = mock_combination
        mock_model.load_cases = {"BG01": mock_load_case_1, "Q1": mock_load_case_2}
        mock_scia.LoadCombination.CombiType.ULS_PERMANENT_VARIABLE = "ULS_PERMANENT_VARIABLE_ENUM"

        create_load_combination_by_type(
            model=mock_model,
            combination_name="ULS02",
            description="Test combination",
            combination_type="ULS_PERMANENT_VARIABLE",
            load_cases={"BG01": 1.35, "Q1": 1.5},
        )

        # Verify combination creation
        mock_model.create_load_combination.assert_called_once_with(
            "ULS02",
            "Test combination",
            "ULS_PERMANENT_VARIABLE_ENUM",
        )

        # Verify load case additions
        expected_calls = [
            ((mock_load_case_1, 1.35),),
            ((mock_load_case_2, 1.5),),
        ]
        actual_calls = mock_combination.add_load_case.call_args_list
        assert len(actual_calls) == 2
        for expected, actual in zip(expected_calls, actual_calls):
            assert actual[0] == expected

    @patch("src.integrations.scia_integration.scia_load_combinations.scia")
    def test_create_load_combination_with_cases_mismatched_lengths(self) -> None:
        """Test error handling for mismatched case names and factors."""
        mock_model = Mock()

        with pytest.raises(ValueError, match="load_case_names and load_case_factors must have the same length"):
            create_load_combination_by_type(
                model=mock_model,
                combination_name="ULS01",
                description="Test combination",
                combination_type="ULS_PERMANENT",
                load_cases={"BG01": 1.35},  # Missing Q1 case
            )

    @patch("src.integrations.scia_integration.scia_load_combinations.scia")
    def test_create_load_combination_with_cases_missing_case(self, mock_scia: Mock) -> None:
        """Test error handling for missing load case."""
        mock_model = Mock()
        mock_combination = Mock()

        mock_model.create_load_combination.return_value = mock_combination
        mock_model.load_cases = {"BG01": Mock()}  # Missing Q1
        mock_scia.LoadCombination.CombiType.ULS_PERMANENT = "ULS_PERMANENT_ENUM"

        with pytest.raises(ValueError, match="Load case 'Q1' not found in model"):
            create_load_combination_by_type(
                model=mock_model,
                combination_name="ULS01",
                description="Test combination",
                combination_type="ULS_PERMANENT",
                load_cases={"BG01": 1.35, "Q1": 1.5},
            )

    @patch("src.integrations.scia_integration.scia_load_combinations.scia")
    def test_create_load_combination_with_cases_empty_cases(self, mock_scia: Mock) -> None:
        """Test load combination creation with empty case list."""
        mock_model = Mock()
        mock_combination = Mock()

        mock_model.create_load_combination.return_value = mock_combination
        mock_model.load_cases = {}
        mock_scia.LoadCombination.CombiType.ULS_PERMANENT = "ULS_PERMANENT_ENUM"

        result = create_load_combination_by_type(
            model=mock_model,
            combination_name="ULS01",
            description="Test combination",
            combination_type="ULS_PERMANENT",
            load_cases={},
        )

        # Should create combination but not add any cases
        mock_model.create_load_combination.assert_called_once()
        mock_combination.add_load_case.assert_not_called()
        assert result is mock_combination

    def test_create_load_combination_with_cases_no_viktor(self) -> None:
        """Test load combination creation without VIKTOR SDK."""
        mock_model = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_load_combination_by_type(
                model=mock_model,
                combination_name="ULS01",
                description="Test combination",
                combination_type="ULS_PERMANENT",
                load_cases={"BG01": 1.35},
            )


class TestUtilityErrorHandling:
    """Test error handling across utility functions."""

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_scia_api_error_propagation(self, mock_scia: Mock) -> None:
        """Test that SCIA API errors are properly propagated."""
        mock_model = Mock()
        mock_model.create_load_group.side_effect = Exception("SCIA API error")

        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"

        with pytest.raises(Exception, match="SCIA API error"):
            create_load_group_by_type(mock_model, "PERMANENT", "LG_Test")

    def test_none_model_handling(self) -> None:
        """Test error handling when model is None."""
        with pytest.raises(AttributeError):
            create_load_group_by_type(None, "PERMANENT", "LG_Test")  # type: ignore[arg-type]

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_empty_string_parameters(self, mock_scia: Mock) -> None:
        """Test handling of empty string parameters."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_model.create_load_group.return_value = mock_load_group

        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"

        # Should still work with empty string (SCIA API will handle validation)
        result = create_load_group_by_type(mock_model, "PERMANENT", "")
        assert result is mock_load_group


class TestUtilityIntegration:
    """Test integration between utility functions."""

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_load_group_to_load_case_workflow(self, mock_scia: Mock) -> None:
        """Test typical workflow from load group to load case creation."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_load_case = Mock()

        # Setup mocks
        mock_model.create_load_group.return_value = mock_load_group
        mock_model.create_permanent_load_case.return_value = mock_load_case

        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"
        mock_scia.LoadCase.PermanentLoadType.SELF_WEIGHT = "SELF_WEIGHT_ENUM"

        # Create load group
        load_group = create_load_group_by_type(mock_model, "PERMANENT", "LG1")

        # Create load case using the group
        load_case = create_load_case_complete(
            model=mock_model,
            load_group=load_group,
            case_name="BG01",
            description="Self weight",
            case_type="PERMANENT",
            permanent_type="SELF_WEIGHT",
        )

        # Verify workflow
        assert load_group is mock_load_group
        assert load_case is mock_load_case
        mock_model.create_permanent_load_case.assert_called_once_with(
            "BG01",
            "Self weight",
            mock_load_group,
            "SELF_WEIGHT_ENUM",
        )


class TestPatchSurfaceLoad:
    """Test patch surface load creation."""

    @patch("src.integrations.scia_integration.scia_loads.scia")
    def test_create_patch_surface_load_success(self, mock_scia: Mock) -> None:
        """Test successful patch surface load creation."""
        mock_model = Mock()
        mock_load_case = Mock()
        mock_surface_load = Mock()

        mock_model.create_free_surface_load.return_value = mock_surface_load
        mock_scia.FreeSurfaceLoad.Direction.Z = "Z_DIRECTION"
        mock_scia.FreeSurfaceLoad.Distribution.UNIFORM = "UNIFORM_DIST"

        corner_points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
        load_value = 1000.0

        result = create_patch_surface_load(mock_model, mock_load_case, corner_points, load_value, "TestLoad")

        # Verify surface load creation
        mock_model.create_free_surface_load.assert_called_once_with(
            name="TestLoad",
            load_case=mock_load_case,
            direction="Z_DIRECTION",
            q1=1000.0,  # Total load = load_value * area (1.0 for 1x1 square)
            points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
            distribution="UNIFORM_DIST",
        )
        assert result is mock_surface_load

    def test_create_patch_surface_load_invalid_corners(self) -> None:
        """Test error handling for invalid corner count."""
        mock_model = Mock()
        mock_load_case = Mock()

        # Only 3 corners instead of 4
        corner_points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]

        with pytest.raises(ValueError, match="Exactly 4 corner points required"):
            create_patch_surface_load(mock_model, mock_load_case, corner_points, 1000.0)

    def test_create_patch_surface_load_no_viktor(self) -> None:
        """Test patch surface load creation without VIKTOR SDK."""
        mock_model = Mock()
        mock_load_case = Mock()
        corner_points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_patch_surface_load(mock_model, mock_load_case, corner_points, 1000.0)


# =============================================================================
# XML GENERATION AND ANALYSIS SETUP TESTS
# =============================================================================


class TestXMLGeneration:
    """Test XML and definition file generation."""

    @patch("src.integrations.scia_integration.scia_utils.scia")
    def test_generate_xml_from_model_success(self) -> None:
        """Test successful XML generation from SCIA model."""
        # Setup mock model
        mock_model = Mock()
        mock_xml = Mock()
        mock_def = Mock()
        mock_model.generate_xml_input.return_value = (mock_xml, mock_def)

        result = generate_xml_from_model(mock_model)

        # Verify calls
        mock_model.generate_xml_input.assert_called_once()
        assert result == (mock_xml, mock_def)

    def test_generate_xml_from_model_no_viktor(self) -> None:
        """Test XML generation without VIKTOR SDK."""
        mock_model = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            generate_xml_from_model(mock_model)


class TestTemplateHandling:
    """Test SCIA template handling."""

    def test_create_scia_analysis_missing_template(self) -> None:
        """Test that FileNotFoundError is raised for missing template."""
        mock_xml_file = Mock()
        mock_def_file = Mock()
        missing_template_path = Path("/nonexistent/template.esa")

        with pytest.raises(FileNotFoundError, match="SCIA template file not found"):
            create_scia_analysis_from_template(mock_xml_file, mock_def_file, missing_template_path)

    def test_create_scia_analysis_no_viktor(self) -> None:
        """Test SCIA analysis creation without VIKTOR SDK."""
        mock_xml_file = Mock()
        mock_def_file = Mock()
        template_path = Path("dummy.esa")

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_scia_analysis_from_template(mock_xml_file, mock_def_file, template_path)

    @patch("src.integrations.scia_integration.scia_utils.scia")
    @patch("src.integrations.scia_integration.scia_utils.File")
    def test_create_scia_analysis_success(self, mock_file_class: Mock, mock_scia: Mock) -> None:
        """Test successful SCIA analysis creation."""
        mock_xml_file = Mock()
        mock_def_file = Mock()
        mock_template_file = Mock()
        mock_analysis = Mock()

        mock_file_class.from_path.return_value = mock_template_file
        mock_scia.SciaAnalysis.return_value = mock_analysis

        # Create existing template path
        template_path = Path(__file__).parent / "test_template.esa"
        template_path.touch()  # Create empty file

        try:
            result = create_scia_analysis_from_template(mock_xml_file, mock_def_file, template_path)

            # Verify calls
            mock_file_class.from_path.assert_called_once_with(template_path)
            mock_scia.SciaAnalysis.assert_called_once_with(mock_xml_file, mock_def_file, mock_template_file)
            assert result is mock_analysis

        finally:
            # Cleanup
            if template_path.exists():
                template_path.unlink()


class TestBridgeXMLWorkflow:
    """Test bridge XML generation workflow functions."""

    @patch("src.integrations.scia_integration.scia_utils.create_complete_bridge_model")
    @patch("src.integrations.scia_integration.scia_utils.generate_xml_from_model")
    def test_generate_bridge_xml_files_success(self, mock_generate_xml: Mock, mock_create_model: Mock) -> None:
        """Test successful bridge XML file generation."""
        # Setup mocks
        mock_model = Mock()
        mock_xml = Mock()
        mock_def = Mock()
        mock_params = Mock()

        mock_create_model.return_value = mock_model
        mock_generate_xml.return_value = (mock_xml, mock_def)

        result = generate_bridge_xml_files(mock_params)

        # Verify workflow
        mock_create_model.assert_called_once_with(mock_params)
        mock_generate_xml.assert_called_once_with(mock_model)

        assert result == (mock_xml, mock_def)

    @patch("src.integrations.scia_integration.scia_utils.generate_bridge_xml_files")
    @patch("src.integrations.scia_integration.scia_utils.create_scia_analysis_from_template")
    def test_setup_bridge_analysis_success(self, mock_create_analysis: Mock, mock_generate_xml: Mock) -> None:
        """Test complete bridge analysis setup."""
        # Setup mocks
        mock_params = Mock()
        mock_template_path = Path("template.esa")
        mock_xml = Mock()
        mock_def = Mock()
        mock_analysis = Mock()

        mock_generate_xml.return_value = (mock_xml, mock_def)
        mock_create_analysis.return_value = mock_analysis

        result = setup_bridge_analysis(mock_params, mock_template_path)

        # Verify workflow
        mock_generate_xml.assert_called_once_with(mock_params)
        mock_create_analysis.assert_called_once_with(mock_xml, mock_def, mock_template_path)

        xml_file, def_file, scia_analysis = result
        assert xml_file is mock_xml
        assert def_file is mock_def
        assert scia_analysis is mock_analysis


class TestBackwardsCompatibility:
    """Test backwards compatibility aliases."""

    @patch("src.integrations.scia_integration.scia_utils.setup_bridge_analysis")
    def test_create_bridge_scia_analysis_alias(self, mock_setup: Mock) -> None:
        """Test that create_bridge_scia_analysis is an alias for setup_bridge_analysis."""
        from src.integrations.scia_integration.scia_utils import create_bridge_scia_analysis

        mock_params = Mock()
        mock_template = Path("test.esa")
        mock_result = Mock()
        mock_setup.return_value = mock_result

        result = create_bridge_scia_analysis(mock_params, mock_template)

        mock_setup.assert_called_once_with(mock_params, mock_template)
        assert result is mock_result

    @patch("src.integrations.scia_integration.scia_utils.generate_bridge_xml_files")
    def test_create_simple_bridge_analysis_alias(self, mock_generate: Mock) -> None:
        """Test that create_simple_bridge_analysis is an alias for generate_bridge_xml_files."""
        from src.integrations.scia_integration.scia_utils import create_simple_bridge_analysis

        mock_params = Mock()
        mock_result = Mock()
        mock_generate.return_value = mock_result

        result = create_simple_bridge_analysis(mock_params)

        mock_generate.assert_called_once_with(mock_params)
        assert result is mock_result


class TestAnalysisWorkflowIntegration:
    """Test complete analysis workflow integration."""

    @patch("src.integrations.scia_integration.scia_utils.create_complete_bridge_model")
    @patch("src.integrations.scia_integration.scia_utils.generate_xml_from_model")
    @patch("src.integrations.scia_integration.scia_utils.create_scia_analysis_from_template")
    def test_complete_workflow_integration(self, mock_create_analysis: Mock, mock_generate_xml: Mock, mock_create_model: Mock) -> None:
        """Test complete workflow from parameters to analysis object."""
        # Setup mocks
        mock_params = Mock()
        mock_template_path = Path("template.esa")
        mock_model = Mock()
        mock_xml = Mock()
        mock_def = Mock()
        mock_analysis = Mock()

        mock_create_model.return_value = mock_model
        mock_generate_xml.return_value = (mock_xml, mock_def)
        mock_create_analysis.return_value = mock_analysis

        # Execute complete workflow
        xml_file, def_file, scia_analysis = setup_bridge_analysis(mock_params, mock_template_path)

        # Verify complete workflow chain
        mock_create_model.assert_called_once_with(mock_params)
        mock_generate_xml.assert_called_once_with(mock_model)
        mock_create_analysis.assert_called_once_with(mock_xml, mock_def, mock_template_path)

        assert xml_file is mock_xml
        assert def_file is mock_def
        assert scia_analysis is mock_analysis

    @patch("src.integrations.scia_integration.scia_utils.create_complete_bridge_model")
    def test_workflow_error_propagation(self, mock_create_model: Mock) -> None:
        """Test that errors in workflow are properly propagated."""
        mock_params = Mock()
        mock_create_model.side_effect = Exception("Model creation failed")

        with pytest.raises(Exception, match="Model creation failed"):
            generate_bridge_xml_files(mock_params)


if __name__ == "__main__":
    pytest.main([__file__])
