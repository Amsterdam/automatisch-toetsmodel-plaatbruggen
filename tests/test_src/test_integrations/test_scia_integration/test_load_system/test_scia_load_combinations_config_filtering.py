"""
Tests for configuration-based filtering in SCIA load combinations.

This module tests that load combinations correctly filter traffic loads by
configuration (A, B, C) to prevent invalid mixing.
"""

import unittest
from unittest.mock import MagicMock

from src.integrations.scia_integration.load_combination_generator.models import LoadConfiguration
from src.integrations.scia_integration.load_system.scia_load_combinations import (
    _add_series_to_factors_generic,
    _extract_configuration_from_description,
    _get_case_description,
)


class TestConfigurationExtraction(unittest.TestCase):
    """Test configuration extraction from load case descriptions."""

    def test_extract_config_a(self) -> None:
        """Test extraction of configuration A."""
        descriptions = [
            "Traffic load - Conf. A - RS 1",
            "UDL - Config. A - Span 1",
            "Tandem - conf. a - Position 5.0m",
        ]
        for desc in descriptions:
            with self.subTest(desc=desc):
                self.assertEqual(_extract_configuration_from_description(desc), LoadConfiguration.CONF_A)

    def test_extract_config_b(self) -> None:
        """Test extraction of configuration B."""
        descriptions = [
            "Traffic load - Conf. B - RS 2",
            "UDL - Config. B - Span 2",
            "Tandem - conf. b - Position 10.0m",
        ]
        for desc in descriptions:
            with self.subTest(desc=desc):
                self.assertEqual(_extract_configuration_from_description(desc), LoadConfiguration.CONF_B)

    def test_extract_config_c(self) -> None:
        """Test extraction of configuration C."""
        descriptions = [
            "Traffic load - Conf. C - RS 3",
            "UDL - Config. C - Span 3",
            "Tandem - conf. c - Position 15.0m",
        ]
        for desc in descriptions:
            with self.subTest(desc=desc):
                self.assertEqual(_extract_configuration_from_description(desc), LoadConfiguration.CONF_C)

    def test_extract_config_d(self) -> None:
        """Test extraction of configuration D."""
        descriptions = [
            "rs 1 - Conf. D - x = 5.0 m",
            "rs 2 - Config. D - x = 10.0 m",  # rs 2 = 200 kN (middle load)
            "rs 3 - conf. d - x = 15.0 m",  # rs 3 = 100 kN (lowest load)
        ]
        for desc in descriptions:
            with self.subTest(desc=desc):
                self.assertEqual(_extract_configuration_from_description(desc), LoadConfiguration.CONF_D)

    def test_extract_config_none(self) -> None:
        """Test extraction of no configuration (non-traffic loads)."""
        descriptions = [
            "Self weight",
            "Dead load - Asphalt",
            "Temperature - Summer",
            "Pedestrian load",
        ]
        for desc in descriptions:
            with self.subTest(desc=desc):
                self.assertEqual(_extract_configuration_from_description(desc), LoadConfiguration.NONE)


class TestCaseDescriptionRetrieval(unittest.TestCase):
    """Test retrieval of description from load case objects."""

    def test_get_description_from_lowercase_attr(self) -> None:
        """Test getting description from 'description' attribute."""
        mock_case = MagicMock()
        mock_case.description = "Test description"
        self.assertEqual(_get_case_description(mock_case), "Test description")

    def test_get_description_from_uppercase_attr(self) -> None:
        """Test getting description from 'Description' attribute."""
        mock_case = MagicMock()
        delattr(mock_case, "description")
        mock_case.Description = "Test Description"
        self.assertEqual(_get_case_description(mock_case), "Test Description")

    def test_get_description_no_attr(self) -> None:
        """Test getting description when no description attribute exists."""
        mock_case = MagicMock(spec=[])
        self.assertEqual(_get_case_description(mock_case), "")


class TestConfigurationFiltering(unittest.TestCase):
    """Test filtering of load cases by configuration."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create mock load cases with different configurations
        self.case_a1 = MagicMock()
        self.case_a1.description = "Tandem - Conf. A - RS 1 - x = 5.0m"

        self.case_a2 = MagicMock()
        self.case_a2.description = "Tandem - Conf. A - RS 2 - x = 5.0m"

        self.case_b1 = MagicMock()
        self.case_b1.description = "Tandem - Conf. B - RS 1 - x = 5.0m"

        self.case_c1 = MagicMock()
        self.case_c1.description = "Tandem - Conf. C - RS 1 - x = 5.0m"

        self.case_none = MagicMock()
        self.case_none.description = "Permanent load"

        # Create mock all_load_cases dictionary
        self.all_load_cases = {
            "tandem_cases": {
                "tandem_a1": self.case_a1,
                "tandem_a2": self.case_a2,
                "tandem_b1": self.case_b1,
                "tandem_c1": self.case_c1,
            }
        }

    def test_filter_config_a(self) -> None:
        """Test filtering for configuration A."""
        result: dict = {}
        _add_series_to_factors_generic(
            self.all_load_cases,
            series_key="tandem_cases",
            factor=1.5,
            out=result,
            configuration=LoadConfiguration.CONF_A,
        )

        # Should only include Config A cases
        self.assertIn(self.case_a1, result)
        self.assertIn(self.case_a2, result)
        self.assertNotIn(self.case_b1, result)
        self.assertNotIn(self.case_c1, result)
        self.assertEqual(len(result), 2)

    def test_filter_config_b(self) -> None:
        """Test filtering for configuration B."""
        result: dict = {}
        _add_series_to_factors_generic(
            self.all_load_cases,
            series_key="tandem_cases",
            factor=1.5,
            out=result,
            configuration=LoadConfiguration.CONF_B,
        )

        # Should only include Config B cases
        self.assertNotIn(self.case_a1, result)
        self.assertNotIn(self.case_a2, result)
        self.assertIn(self.case_b1, result)
        self.assertNotIn(self.case_c1, result)
        self.assertEqual(len(result), 1)

    def test_filter_config_c(self) -> None:
        """Test filtering for configuration C."""
        result: dict = {}
        _add_series_to_factors_generic(
            self.all_load_cases,
            series_key="tandem_cases",
            factor=1.5,
            out=result,
            configuration=LoadConfiguration.CONF_C,
        )

        # Should only include Config C cases
        self.assertNotIn(self.case_a1, result)
        self.assertNotIn(self.case_a2, result)
        self.assertNotIn(self.case_b1, result)
        self.assertIn(self.case_c1, result)
        self.assertEqual(len(result), 1)

    def test_no_filter_when_config_none(self) -> None:
        """Test that no filtering occurs when configuration is None."""
        result: dict = {}
        _add_series_to_factors_generic(self.all_load_cases, series_key="tandem_cases", factor=1.5, out=result, configuration=None)

        # Should include all cases
        self.assertIn(self.case_a1, result)
        self.assertIn(self.case_a2, result)
        self.assertIn(self.case_b1, result)
        self.assertIn(self.case_c1, result)
        self.assertEqual(len(result), 4)

    def test_skip_backward_compatibility_aliases(self) -> None:
        """Test that backward compatibility aliases are skipped."""
        all_cases_with_aliases = {
            "tandem_cases": {
                "rs_1": self.case_a1,  # Should be skipped
                "rs_2": self.case_a2,  # Should be skipped
                "tandem_a1": self.case_a1,  # Should be included
            }
        }

        result: dict = {}
        _add_series_to_factors_generic(
            all_cases_with_aliases,
            series_key="tandem_cases",
            factor=1.5,
            out=result,
            configuration=LoadConfiguration.CONF_A,
        )

        # Should only include the non-alias case once
        self.assertEqual(len(result), 1)
        self.assertIn(self.case_a1, result)

    def test_correct_factor_applied(self) -> None:
        """Test that the correct factor is applied to filtered cases."""
        result: dict = {}
        _add_series_to_factors_generic(
            self.all_load_cases,
            series_key="tandem_cases",
            factor=1.35,
            out=result,
            configuration=LoadConfiguration.CONF_A,
        )

        # Check that the factor is correctly applied
        self.assertEqual(result[self.case_a1], 1.35)
        self.assertEqual(result[self.case_a2], 1.35)


class TestIntegrationWithNonTrafficLoads(unittest.TestCase):
    """Test that non-traffic loads are not filtered by configuration."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.permanent_case = MagicMock()
        self.permanent_case.description = "Self weight"

        self.temp_case = MagicMock()
        self.temp_case.description = "Temperature - Summer"

        self.all_load_cases = {
            "standard_cases": {"self_weight": self.permanent_case},
            "temperature_cases": {"summer": self.temp_case},
        }

    def test_permanent_loads_not_filtered(self) -> None:
        """Test that permanent loads are included regardless of configuration."""
        for config in [LoadConfiguration.CONF_A, LoadConfiguration.CONF_B, LoadConfiguration.CONF_C, None]:
            with self.subTest(config=config):
                result: dict = {}
                _add_series_to_factors_generic(self.all_load_cases, series_key="standard_cases", factor=1.2, out=result, configuration=config)

                # Permanent loads should always be included (when config=None)
                if config is None:
                    self.assertIn(self.permanent_case, result)
                else:
                    # When config is specified, permanent loads have no config so they're excluded
                    self.assertNotIn(self.permanent_case, result)


class TestTrafficLoadDetection(unittest.TestCase):
    """Test detection of whether combinations have traffic loads."""

    def test_combination_with_traffic_loads(self) -> None:
        """Test that combinations with TS or UDL are detected correctly."""
        import pandas as pd

        from src.integrations.scia_integration.load_system.scia_load_combinations import _create_combinations_from_df
        from src.integrations.scia_integration.scia_enums import LoadCombinationType

        # Create mock builder
        mock_builder = MagicMock()
        mock_builder.create_load_combination = MagicMock(side_effect=lambda **kwargs: MagicMock(**kwargs))

        # Create test data with traffic loads
        df_with_traffic = pd.DataFrame(
            {
                "Permanent": [1.2],
                "TS - rs 1": [1.5],  # Has traffic loads
                "UDL - Main": [1.5],  # Has traffic loads
            },
            index=["6.10a LC1"],
        )

        # Create mock load cases
        mock_perm = MagicMock()
        mock_perm.description = "Permanent load"

        mock_tandem_a = MagicMock()
        mock_tandem_a.description = "Tandem - Conf. A - RS 1"

        mock_tandem_b = MagicMock()
        mock_tandem_b.description = "Tandem - Conf. B - RS 1"

        mock_tandem_c = MagicMock()
        mock_tandem_c.description = "Tandem - Conf. C - RS 1"

        mock_tandem_d = MagicMock()
        mock_tandem_d.description = "Tandem - Conf. D - RS 1"

        mock_udl_a = MagicMock()
        mock_udl_a.description = "UDL - Conf. A - Span 1"

        mock_udl_b = MagicMock()
        mock_udl_b.description = "UDL - Conf. B - Span 1"

        mock_udl_c = MagicMock()
        mock_udl_c.description = "UDL - Conf. C - Span 1"

        all_load_cases = {
            "self_weight": mock_perm,
            "tandem_rs1_cases": {
                "tandem_a": mock_tandem_a,
                "tandem_b": mock_tandem_b,
                "tandem_c": mock_tandem_c,
                "tandem_d": mock_tandem_d,
            },
            "udl_main_cases": {
                "udl_a": mock_udl_a,
                "udl_b": mock_udl_b,
                "udl_c": mock_udl_c,
            },
        }

        # Call function
        results = _create_combinations_from_df(
            builder=mock_builder,
            df=df_with_traffic,
            combination_type=LoadCombinationType.ENVELOPE_ULTIMATE,
            desc_prefix="ULS",
            all_load_cases=all_load_cases,
        )

        # Should create 4 combinations (one per config A, B, C, D)
        self.assertEqual(len(results), 4)

        # Check that combinations have config suffix
        call_args_list = mock_builder.create_load_combination.call_args_list
        names = [call.kwargs["name"] for call in call_args_list]
        self.assertIn("6.10a LC1 - Config A", names)
        self.assertIn("6.10a LC1 - Config B", names)
        self.assertIn("6.10a LC1 - Config C", names)
        self.assertIn("6.10a LC1 - Config D", names)

    def test_combination_without_traffic_loads(self) -> None:
        """Test that combinations without TS or UDL are created only once."""
        import pandas as pd

        from src.integrations.scia_integration.load_system.scia_load_combinations import _create_combinations_from_df
        from src.integrations.scia_integration.scia_enums import LoadCombinationType

        # Create mock builder
        mock_builder = MagicMock()
        mock_builder.create_load_combination = MagicMock(side_effect=lambda **kwargs: MagicMock(**kwargs))

        # Create test data WITHOUT traffic loads
        df_no_traffic = pd.DataFrame(
            {
                "Permanent": [1.2],
                "TS": [0.0],  # Zero - no traffic
                "UDL": [0.0],  # Zero - no traffic
                "Temperatuur": [0.6],
            },
            index=["6.10a Perm"],
        )

        # Create mock load cases
        mock_perm = MagicMock()
        mock_perm.description = "Permanent load"

        mock_temp = MagicMock()
        mock_temp.description = "Temperature - Summer"

        all_load_cases = {"self_weight": mock_perm, "temperature_cases": {"summer": mock_temp}}

        # Call function
        results = _create_combinations_from_df(
            builder=mock_builder,
            df=df_no_traffic,
            combination_type=LoadCombinationType.ENVELOPE_ULTIMATE,
            desc_prefix="ULS",
            all_load_cases=all_load_cases,
        )

        # Should create only 1 combination (no config suffix)
        self.assertEqual(len(results), 1)

        # Check that combination has no config suffix
        call_args = mock_builder.create_load_combination.call_args_list[0]
        self.assertEqual(call_args.kwargs["name"], "6.10a Perm")
        self.assertNotIn("Config", call_args.kwargs["name"])

    def test_mixed_combinations(self) -> None:
        """Test a DataFrame with both traffic and non-traffic combinations."""
        import pandas as pd

        from src.integrations.scia_integration.load_system.scia_load_combinations import _create_combinations_from_df
        from src.integrations.scia_integration.scia_enums import LoadCombinationType

        # Create mock builder
        mock_builder = MagicMock()
        mock_builder.create_load_combination = MagicMock(side_effect=lambda **kwargs: MagicMock(**kwargs))

        # Create test data with BOTH types
        df_mixed = pd.DataFrame(
            {
                "Permanent": [1.2, 1.2, 1.2],
                "TS - rs 1": [1.5, 0.0, 1.5],  # Row 1: has traffic, Row 2: no traffic, Row 3: has traffic
                "UDL - Main": [1.5, 0.0, 0.0],
            },
            index=["6.10a LC1", "6.10a Perm", "6.10a gr3"],
        )

        # Create mock load cases
        mock_perm = MagicMock()
        mock_perm.description = "Permanent load"

        mock_tandem_a = MagicMock()
        mock_tandem_a.description = "Tandem - Conf. A - RS 1"

        mock_tandem_b = MagicMock()
        mock_tandem_b.description = "Tandem - Conf. B - RS 1"

        mock_tandem_c = MagicMock()
        mock_tandem_c.description = "Tandem - Conf. C - RS 1"

        mock_tandem_d = MagicMock()
        mock_tandem_d.description = "Tandem - Conf. D - RS 1"

        mock_udl_a = MagicMock()
        mock_udl_a.description = "UDL - Conf. A - Span 1"

        mock_udl_b = MagicMock()
        mock_udl_b.description = "UDL - Conf. B - Span 1"

        mock_udl_c = MagicMock()
        mock_udl_c.description = "UDL - Conf. C - Span 1"

        all_load_cases = {
            "self_weight": mock_perm,
            "tandem_rs1_cases": {
                "tandem_a": mock_tandem_a,
                "tandem_b": mock_tandem_b,
                "tandem_c": mock_tandem_c,
                "tandem_d": mock_tandem_d,
            },
            "udl_main_cases": {
                "udl_a": mock_udl_a,
                "udl_b": mock_udl_b,
                "udl_c": mock_udl_c,
            },
        }

        # Call function
        results = _create_combinations_from_df(
            builder=mock_builder,
            df=df_mixed,
            combination_type=LoadCombinationType.ENVELOPE_ULTIMATE,
            desc_prefix="ULS",
            all_load_cases=all_load_cases,
        )

        # Should create: 4 (LC1) + 1 (Perm) + 4 (gr3) = 9 combinations
        self.assertEqual(len(results), 9)

        # Check names
        call_args_list = mock_builder.create_load_combination.call_args_list
        names = [call.kwargs["name"] for call in call_args_list]

        # LC1 should have 4 versions (A, B, C, D)
        self.assertIn("6.10a LC1 - Config A", names)
        self.assertIn("6.10a LC1 - Config B", names)
        self.assertIn("6.10a LC1 - Config C", names)
        self.assertIn("6.10a LC1 - Config D", names)

        # Perm should have 1 version (no suffix)
        self.assertIn("6.10a Perm", names)
        self.assertEqual(sum(1 for n in names if n == "6.10a Perm"), 1)

        # gr3 should have 4 versions (A, B, C, D)
        self.assertIn("6.10a gr3 - Config A", names)
        self.assertIn("6.10a gr3 - Config B", names)
        self.assertIn("6.10a gr3 - Config C", names)
        self.assertIn("6.10a gr3 - Config D", names)


class TestConfigDSpecialHandling(unittest.TestCase):
    """Test that Config D tandems combine with Config C UDLs."""

    def test_config_d_tandems_with_config_c_udls(self) -> None:
        """Test that Config D combination includes Config D tandems and Config C UDLs."""
        import pandas as pd

        from src.integrations.scia_integration.load_system.scia_load_combinations import _create_combinations_from_df
        from src.integrations.scia_integration.scia_enums import LoadCombinationType

        # Create mock builder
        mock_builder = MagicMock()
        created_combinations = []

        def track_combination(**kwargs) -> MagicMock:
            created_combinations.append(kwargs)
            return MagicMock(**kwargs)

        mock_builder.create_load_combination = MagicMock(side_effect=track_combination)

        # Create test data with traffic loads
        df_with_traffic = pd.DataFrame(
            {
                "Permanent": [1.2],
                "TS - rs 1": [1.5],
                "UDL - Main": [1.5],
            },
            index=["6.10a LC1"],
        )

        # Create mock load cases
        mock_perm = MagicMock()
        mock_perm.description = "Permanent load"

        mock_tandem_c = MagicMock()
        mock_tandem_c.description = "Tandem - Conf. C - RS 1"

        mock_tandem_d = MagicMock()
        mock_tandem_d.description = "Tandem - Conf. D - RS 1"

        mock_udl_c = MagicMock()
        mock_udl_c.description = "UDL - Conf. C - Span 1"

        all_load_cases = {
            "self_weight": mock_perm,
            "tandem_rs1_cases": {
                "tandem_c": mock_tandem_c,
                "tandem_d": mock_tandem_d,
            },
            "udl_main_cases": {
                "udl_c": mock_udl_c,
            },
        }

        # Call function
        _create_combinations_from_df(
            builder=mock_builder,
            df=df_with_traffic,
            combination_type=LoadCombinationType.ENVELOPE_ULTIMATE,
            desc_prefix="ULS",
            all_load_cases=all_load_cases,
        )

        # Find the Config D combination
        config_d_combo = next(c for c in created_combinations if "Config D" in c["name"])

        # Check that Config D combination has:
        # - Config D tandems
        # - Config C UDLs (not Config D UDLs)
        # - Permanent loads
        load_cases_in_combo = config_d_combo["load_case_factors"]

        self.assertIn(mock_tandem_d, load_cases_in_combo)  # Config D tandem
        self.assertIn(mock_udl_c, load_cases_in_combo)  # Config C UDL
        self.assertIn(mock_perm, load_cases_in_combo)  # Permanent
        self.assertNotIn(mock_tandem_c, load_cases_in_combo)  # NOT Config C tandem


if __name__ == "__main__":
    unittest.main()
