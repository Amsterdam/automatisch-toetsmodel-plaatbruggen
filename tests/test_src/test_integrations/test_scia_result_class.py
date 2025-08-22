"""
Tests for SCIA result class creation functions.

This module tests the creation and filtering of SCIA result classes using dummy objects and mocks.
"""

from unittest.mock import Mock

import pandas as pd

from src.integrations.scia_integration import scia_result_classes


class DummyLoadCombination:
    """Dummy class to simulate a load combination object for result class tests."""

    def __init__(self, index: str) -> None:
        """Initialize with an index string."""
        self.index = index


class DummySciaModelBuilder:
    """Dummy class to simulate the SCIA model builder for result class tests."""

    def create_result_class(self, name: str, combinations: list, nonlinear_combinations: list | None = None) -> dict:
        """
        Create a dummy result class dictionary.

        :param name: Name of the result class.
        :type name: str
        :param combinations: List of load combinations.
        :type combinations: list
        :param nonlinear_combinations: List of nonlinear combinations (optional).
        :type nonlinear_combinations: list or None
        :returns: Dictionary representing the result class.
        :rtype: dict
        """
        return {
            "name": name,
            "combinations": combinations,
            "nonlinear_combinations": nonlinear_combinations,
        }


def make_test_df_and_list() -> tuple[pd.DataFrame, list[DummyLoadCombination]]:
    """
    Helper to create a test DataFrame and corresponding filter list for result class tests.

    :returns: Tuple of DataFrame and list of DummyLoadCombination objects.
    :rtype: tuple[pd.DataFrame, list[DummyLoadCombination]]
    """
    indices = ["6.10a Perm", "6.10a gr1a", "6.14b Perm", "6.15b gr1a", "6.16b gr2", "6.67 Perm", "6.69 gr1a"]
    test_df = pd.DataFrame(index=indices)
    filter_list = [DummyLoadCombination(idx) for idx in indices]
    return test_df, filter_list


class TestResultClassFiltering:
    """Tests for filtering load combinations for result classes."""

    def test_filter_list_by_df_index(self) -> None:
        """Test filtering of load combinations by prefix using filter_list_by_df_index."""
        test_df, filter_list = make_test_df_and_list()
        # Test for 6.14b
        result = scia_result_classes.filter_list_by_df_index(test_df, filter_list, ["6.14b"])
        assert len(result) == 1
        assert result[0].index == "6.14b Perm"
        # Test for 6.15b and 6.16b
        result = scia_result_classes.filter_list_by_df_index(test_df, filter_list, ["6.15b", "6.16b"])
        assert len(result) == 2
        assert result[0].index == "6.15b gr1a"
        assert result[1].index == "6.16b gr2"
        # Test for 6.10a
        result = scia_result_classes.filter_list_by_df_index(test_df, filter_list, ["6.10a"])
        assert len(result) == 2
        assert result[0].index == "6.10a Perm"
        assert result[1].index == "6.10a gr1a"


class TestResultClassCreation:
    """Tests for creating individual and all SCIA result classes."""

    def test_create_uls_result_class_from_table(self) -> None:
        """Test creation of ULS result class using create_uls_result_class_from_table."""
        test_df, filter_list = make_test_df_and_list()
        builder = DummySciaModelBuilder()
        params = Mock()
        scia_result_classes.load_combination_table_without_rounding = lambda _: test_df  # type: ignore[assignment]
        result = scia_result_classes.create_uls_result_class_from_table(params, builder, filter_list)  # type: ignore[arg-type]
        assert result[0]["name"] == "ULS"
        assert len(result[0]["combinations"]) == 2
        assert result[0]["combinations"][0].index == "6.10a Perm"

    def test_create_sls_kar_result_class_from_table(self) -> None:
        """Test creation of SLS characteristic result class using create_sls_kar_result_class_from_table."""
        test_df, filter_list = make_test_df_and_list()
        builder = DummySciaModelBuilder()
        params = Mock()
        scia_result_classes.load_combination_table_without_rounding = lambda _: test_df  # type: ignore[assignment]
        result = scia_result_classes.create_sls_kar_result_class_from_table(params, builder, filter_list)  # type: ignore[arg-type]
        assert result[0]["name"] == "SLS kar"
        assert len(result[0]["combinations"]) == 1
        assert result[0]["combinations"][0].index == "6.14b Perm"

    def test_create_sls_freq_result_class_from_table(self) -> None:
        """Test creation of SLS frequent result class using create_sls_freq_result_class_from_table."""
        test_df, filter_list = make_test_df_and_list()
        builder = DummySciaModelBuilder()
        params = Mock()
        scia_result_classes.load_combination_table_without_rounding = lambda _: test_df  # type: ignore[assignment]
        result = scia_result_classes.create_sls_freq_result_class_from_table(params, builder, filter_list)  # type: ignore[arg-type]
        assert result[0]["name"] == "SLS freq"
        assert len(result[0]["combinations"]) == 1
        assert result[0]["combinations"][0].index == "6.15b gr1a"

    def test_create_sls_qp_result_class_from_table(self) -> None:
        """Test creation of SLS quasi-permanent result class using create_sls_qp_result_class_from_table."""
        test_df, filter_list = make_test_df_and_list()
        builder = DummySciaModelBuilder()
        params = Mock()
        scia_result_classes.load_combination_table_without_rounding = lambda _: test_df  # type: ignore[assignment]
        result = scia_result_classes.create_sls_qp_result_class_from_table(params, builder, filter_list)  # type: ignore[arg-type]
        assert result[0]["name"] == "SLS qp"
        assert len(result[0]["combinations"]) == 1
        assert result[0]["combinations"][0].index == "6.16b gr2"

    def test_create_fat_result_class_from_table(self) -> None:
        """Test creation of fatigue result class using create_fat_result_class_from_table."""
        test_df, filter_list = make_test_df_and_list()
        builder = DummySciaModelBuilder()
        params = Mock()
        scia_result_classes.load_combination_table_without_rounding = lambda _: test_df  # type: ignore[assignment]
        result = scia_result_classes.create_fat_result_class_from_table(params, builder, filter_list)  # type: ignore[arg-type]
        assert result[0]["name"] == "FAT"
        assert len(result[0]["combinations"]) == 2
        assert result[0]["combinations"][0].index == "6.67 Perm"
        assert result[0]["combinations"][1].index == "6.69 gr1a"

    def test_create_all_result_classes(self) -> None:
        """Test creation of all result classes together using create_all_result_classes."""
        test_df, filter_list = make_test_df_and_list()
        builder = DummySciaModelBuilder()
        params = Mock()
        scia_result_classes.load_combination_table_without_rounding = lambda _: test_df  # type: ignore[assignment]
        result = scia_result_classes.create_all_result_classes(params, builder, filter_list)  # type: ignore[arg-type]
        names = [r["name"] for r in result]
        assert names == ["ULS", "SLS kar", "SLS freq", "SLS qp", "FAT"]
        assert len(result) == 5
