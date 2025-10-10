"""Tests for cache parameter extraction and configuration."""

import unittest

from munch import Munch  # type: ignore[import-untyped]

from app.bridge.cache_parameters import (
    IDEA_ONLY_PARAMETERS,
    SHARED_PARAMETERS,
    extract_parameters_for_analysis,
    get_cache_parameters_for_analysis,
)
from src.common.constants.technical import AnalysisType


class TestParameterGroupDefinitions(unittest.TestCase):
    """Test parameter group definitions and structure."""

    def test_shared_parameters_structure(self) -> None:
        """Test that SHARED_PARAMETERS has expected structure."""
        assert isinstance(SHARED_PARAMETERS, list)
        assert len(SHARED_PARAMETERS) > 0

        # Check that all groups have required keys
        for group in SHARED_PARAMETERS:
            assert "name" in group
            assert "paths" in group
            assert isinstance(group["name"], str)
            assert isinstance(group["paths"], list)

    def test_shared_parameters_expected_groups(self) -> None:
        """Test that SHARED_PARAMETERS contains expected parameter groups."""
        group_names = [group["name"] for group in SHARED_PARAMETERS]

        # Check for expected groups
        assert "bridge_segments" in group_names
        assert "load_zones" in group_names
        assert "load_combinations" in group_names
        assert "materials" in group_names

    def test_idea_only_parameters_structure(self) -> None:
        """Test that IDEA_ONLY_PARAMETERS has expected structure."""
        assert isinstance(IDEA_ONLY_PARAMETERS, list)
        assert len(IDEA_ONLY_PARAMETERS) > 0

        # Check that all groups have required keys
        for group in IDEA_ONLY_PARAMETERS:
            assert "name" in group
            assert "paths" in group
            assert isinstance(group["name"], str)
            assert isinstance(group["paths"], list)

    def test_idea_only_parameters_expected_groups(self) -> None:
        """Test that IDEA_ONLY_PARAMETERS contains expected parameter groups."""
        group_names = [group["name"] for group in IDEA_ONLY_PARAMETERS]

        # Check for expected IDEA-specific groups
        assert "reinforcement_zones" in group_names
        assert "reinforcement_geometry" in group_names

    def test_get_cache_parameters_for_scia(self) -> None:
        """Test getting parameter groups for SCIA analysis."""
        param_groups = get_cache_parameters_for_analysis(AnalysisType.SCIA)

        assert isinstance(param_groups, list)
        group_names = [group["name"] for group in param_groups]

        # SCIA should only have SHARED_PARAMETERS
        assert "bridge_segments" in group_names
        assert "load_zones" in group_names
        assert "load_combinations" in group_names
        assert "materials" in group_names

        # SCIA should NOT have IDEA-specific parameters
        assert "reinforcement_zones" not in group_names
        assert "reinforcement_geometry" not in group_names

    def test_get_cache_parameters_for_idea(self) -> None:
        """Test getting parameter groups for IDEA analysis."""
        param_groups = get_cache_parameters_for_analysis(AnalysisType.IDEA)

        assert isinstance(param_groups, list)
        group_names = [group["name"] for group in param_groups]

        # IDEA should have both SHARED and IDEA_ONLY parameters
        assert "bridge_segments" in group_names
        assert "load_zones" in group_names
        assert "load_combinations" in group_names
        assert "materials" in group_names
        assert "reinforcement_zones" in group_names
        assert "reinforcement_geometry" in group_names


class TestParameterExtraction(unittest.TestCase):
    """Test parameter extraction logic."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a mock params object with typical structure
        # Note: Arrays need to be lists of Munch objects for getattr to work
        self.mock_params = Munch(
            {
                "bridge_segments_array": [
                    Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0, "dz": 1.0, "dz_2": 1.2, "is_first_segment": True, "is_support": False}),
                    Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0, "dz": 1.0, "dz_2": 1.2, "is_first_segment": False, "is_support": True}),
                ],
                "load_zones_data_array": [
                    Munch(
                        {
                            "zone_type": "Rijbaan",
                            "pavement_thickness": 0.1,
                            "pavement_material": "Asfalt",
                            "d1_width": 1.0,
                            "d2_width": 2.0,
                            "d3_width": 0.0,
                        }
                    ),
                    Munch(
                        {
                            "zone_type": "Fietspad",
                            "pavement_thickness": 0.05,
                            "pavement_material": "Asfalt",
                            "d1_width": 1.5,
                            "d2_width": 0.0,
                            "d3_width": 0.0,
                        }
                    ),
                ],
                "cc_class": "CC2",
                "design_code": "NEN 8700 verbouw",
                "berekeningsniveau": "Theoretische wegindeling",
                "signage": "Geen signalering",
                "reinforcement_zones_array": [
                    Munch({"zone_number": 1, "hoofdwapening_langs_boven_diameter": 16, "hoofdwapening_langs_boven_hart_op_hart": 150}),
                ],
            }
        )

    def test_extract_parameters_for_scia(self) -> None:
        """Test extracting parameters for SCIA analysis."""
        extracted = extract_parameters_for_analysis(self.mock_params, AnalysisType.SCIA)

        assert isinstance(extracted, dict)

        # Check that bridge segments are extracted (as dict of arrays)
        assert "bridge_segments" in extracted
        segments = extracted["bridge_segments"]
        assert "bz1" in segments
        assert segments["bz1"] == [3.5, 3.5]  # Array of values from all segments
        assert segments["l"] == [20.0, 20.0]

        # Check that load zones are extracted (as dict of arrays)
        assert "load_zones" in extracted
        zones = extracted["load_zones"]
        assert "zone_type" in zones
        assert zones["zone_type"] == ["Rijbaan", "Fietspad"]

        # Check that load combinations are extracted
        assert "load_combinations" in extracted
        assert extracted["load_combinations"]["cc_class"] == "CC2"
        assert extracted["load_combinations"]["design_code"] == "NEN 8700 verbouw"

        # SCIA should NOT extract reinforcement parameters
        assert "reinforcement_zones" not in extracted

    def test_extract_parameters_for_idea(self) -> None:
        """Test extracting parameters for IDEA analysis."""
        extracted = extract_parameters_for_analysis(self.mock_params, AnalysisType.IDEA)

        assert isinstance(extracted, dict)

        # Check that shared parameters are extracted (same as SCIA)
        assert "bridge_segments" in extracted
        assert "load_zones" in extracted
        assert "load_combinations" in extracted

        # Check that IDEA-specific reinforcement parameters are extracted (as dict of arrays)
        assert "reinforcement_zones" in extracted
        reinforcement = extracted["reinforcement_zones"]
        assert "zone_number" in reinforcement
        assert reinforcement["zone_number"] == [1]  # Array with one zone
        assert reinforcement["hoofdwapening_langs_boven_diameter"] == [16]

    def test_array_path_extraction(self) -> None:
        """Test extraction of array paths with wildcard syntax."""
        extracted = extract_parameters_for_analysis(self.mock_params, AnalysisType.SCIA)

        # Check that array fields are extracted correctly (as dict of field arrays)
        segments = extracted["bridge_segments"]

        # The structure is {field_name: [value1, value2, ...]}
        assert "bz1" in segments
        assert "bz2" in segments
        assert "bz3" in segments
        assert "l" in segments

        # Each field should have 2 values (one per segment)
        assert len(segments["bz1"]) == 2
        assert len(segments["l"]) == 2

    def test_nested_path_extraction(self) -> None:
        """Test extraction of nested paths."""
        extracted = extract_parameters_for_analysis(self.mock_params, AnalysisType.SCIA)

        # Check that direct top-level fields are extracted
        load_combs = extracted["load_combinations"]
        assert "cc_class" in load_combs
        assert load_combs["cc_class"] == "CC2"

    def test_missing_attributes_return_defaults(self) -> None:
        """Test that missing attributes are handled gracefully."""
        # Create params without some expected fields
        minimal_params = Munch(
            {
                "bridge_segments_array": [
                    {"bz1": 3.5, "bz2": 7.0},  # Missing many fields
                ],
            }
        )

        extracted = extract_parameters_for_analysis(minimal_params, AnalysisType.SCIA)

        # Should not raise errors, should have defaults/None for missing fields
        assert "bridge_segments" in extracted
        assert len(extracted["bridge_segments"]) > 0

    def test_empty_arrays_handled_correctly(self) -> None:
        """Test that empty arrays are handled correctly."""
        empty_params = Munch(
            {
                "bridge_segments_array": [],
                "load_zones_data_array": [],
            }
        )

        extracted = extract_parameters_for_analysis(empty_params, AnalysisType.SCIA)

        # Should handle empty arrays gracefully (returns dict with empty arrays for each field)
        assert "bridge_segments" in extracted
        segments = extracted["bridge_segments"]
        # Each field should have an empty array
        for field_values in segments.values():
            assert field_values == []

    def test_all_d_width_fields_extracted(self) -> None:
        """Test that all 15 d{i}_width fields are extracted correctly."""
        # Create params with multiple d_width fields
        params_with_widths = Munch(
            {
                "load_zones_data_array": [
                    Munch(
                        {
                            "zone_type": "Rijbaan",
                            "d1_width": 1.0,
                            "d2_width": 2.0,
                            "d3_width": 3.0,
                            "d4_width": 4.0,
                            "d5_width": 5.0,
                            "d6_width": 0.0,  # Some can be zero
                            "d7_width": 0.0,
                            "d8_width": 0.0,
                            "d9_width": 0.0,
                            "d10_width": 0.0,
                            "d11_width": 0.0,
                            "d12_width": 0.0,
                            "d13_width": 0.0,
                            "d14_width": 0.0,
                            "d15_width": 0.0,
                        }
                    ),
                ],
            }
        )

        extracted = extract_parameters_for_analysis(params_with_widths, AnalysisType.SCIA)

        # Check that all d_width fields are extracted (as arrays)
        load_zones = extracted["load_zones"]
        for i in range(1, 16):
            field_name = f"d{i}_width"
            assert field_name in load_zones, f"Missing {field_name}"
            # Each field should have an array with one value
            assert len(load_zones[field_name]) == 1
            if i <= 5:
                assert load_zones[field_name][0] == float(i)
            else:
                assert load_zones[field_name][0] == 0.0


class TestParameterExtractionEdgeCases(unittest.TestCase):
    """Test edge cases in parameter extraction."""

    def test_params_without_required_attributes(self) -> None:
        """Test extraction when params object is missing required attributes."""
        # Create completely empty params
        empty_params = Munch({})

        # Should not raise errors
        extracted = extract_parameters_for_analysis(empty_params, AnalysisType.SCIA)

        assert isinstance(extracted, dict)
        # Should have empty/default values for all groups
        assert "bridge_segments" in extracted
        assert "load_zones" in extracted

    def test_malformed_array_structures(self) -> None:
        """Test handling of malformed array structures."""
        # Non-list arrays
        malformed_params = Munch(
            {
                "bridge_segments_array": "not a list",
                "load_zones_data_array": 123,
            }
        )

        # Should handle gracefully without crashing
        extracted = extract_parameters_for_analysis(malformed_params, AnalysisType.SCIA)

        assert isinstance(extracted, dict)

    def test_very_large_arrays(self) -> None:
        """Test performance with large arrays."""
        # Create params with many segments
        large_params = Munch(
            {
                "bridge_segments_array": [Munch({"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0}) for _ in range(100)],
            }
        )

        # Should complete without performance issues
        extracted = extract_parameters_for_analysis(large_params, AnalysisType.SCIA)

        assert "bridge_segments" in extracted
        # Check that arrays have 100 elements
        segments = extracted["bridge_segments"]
        assert len(segments["bz1"]) == 100
        assert len(segments["l"]) == 100

    def test_special_characters_in_values(self) -> None:
        """Test handling of special characters in parameter values."""
        params_with_special_chars = Munch(
            {
                "cc_class": "CC2 (special)",
                "design_code": "NEN 8700 / verbouw",
                "bridge_segments_array": [
                    {"bz1": 3.5, "bz2": 7.0, "bz3": 3.5, "l": 20.0},
                ],
            }
        )

        extracted = extract_parameters_for_analysis(params_with_special_chars, AnalysisType.SCIA)

        # Should preserve special characters
        assert extracted["load_combinations"]["cc_class"] == "CC2 (special)"
        assert extracted["load_combinations"]["design_code"] == "NEN 8700 / verbouw"


if __name__ == "__main__":
    unittest.main()
