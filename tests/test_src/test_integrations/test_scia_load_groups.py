"""
Tests for SCIA load groups module.

Tests for load group creation functions using direct SCIA API.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_group import (
    create_permanent_load_group,
    create_traffic_load_group,
    create_wind_load_group,
)


class TestPermanentLoadGroup:
    """Test permanent load group creation using direct SCIA API."""

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_create_permanent_load_group_success(self, mock_scia: Mock) -> None:
        """Test successful permanent load group creation."""
        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()

        mock_model.create_load_group.return_value = mock_load_group
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"

        result = create_permanent_load_group(mock_model)

        # Verify direct SCIA API call
        mock_model.create_load_group.assert_called_once_with(
            "LG1",
            "PERMANENT_ENUM",
            "STANDARD_ENUM",
            "CONSTRUCTION_LOADS_ENUM",
        )
        assert result is mock_load_group

    def test_create_permanent_load_group_no_viktor(self) -> None:
        """Test permanent load group creation without VIKTOR SDK."""
        mock_model = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_permanent_load_group(mock_model)


class TestTrafficLoadGroup:
    """Test traffic load group creation using direct SCIA API."""

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_create_traffic_load_group_success(self, mock_scia: Mock) -> None:
        """Test successful traffic load group creation."""
        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()

        mock_model.create_load_group.return_value = mock_load_group
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.LIVE_LOADS = "LIVE_LOADS_ENUM"

        result = create_traffic_load_group(mock_model)

        # Verify direct SCIA API call
        mock_model.create_load_group.assert_called_once_with(
            "LG2",
            "VARIABLE_ENUM",
            "STANDARD_ENUM",
            "LIVE_LOADS_ENUM",
        )
        assert result is mock_load_group

    def test_create_traffic_load_group_no_viktor(self) -> None:
        """Test traffic load group creation without VIKTOR SDK."""
        mock_model = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_traffic_load_group(mock_model)


class TestWindLoadGroup:
    """Test wind load group creation using direct SCIA API."""

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_create_wind_load_group_success(self, mock_scia: Mock) -> None:
        """Test successful wind load group creation."""
        # Setup mocks
        mock_model = Mock()
        mock_load_group = Mock()

        mock_model.create_load_group.return_value = mock_load_group
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.WIND_LOADS = "WIND_LOADS_ENUM"

        result = create_wind_load_group(mock_model)

        # Verify direct SCIA API call
        mock_model.create_load_group.assert_called_once_with(
            "LG3",
            "VARIABLE_ENUM",
            "STANDARD_ENUM",
            "WIND_LOADS_ENUM",
        )
        assert result is mock_load_group

    def test_create_wind_load_group_no_viktor(self) -> None:
        """Test wind load group creation without VIKTOR SDK."""
        mock_model = Mock()

        with pytest.raises(ImportError, match="VIKTOR SCIA module not available"):
            create_wind_load_group(mock_model)


class TestLoadGroupNamingConventions:
    """Test load group naming conventions match SCIA interface."""

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_load_group_names_match_scia_interface(self, mock_scia: Mock) -> None:
        """Test that load group names match SCIA interface exactly."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_model.create_load_group.return_value = mock_load_group

        # Setup enum mocks
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.LIVE_LOADS = "LIVE_LOADS_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.WIND_LOADS = "WIND_LOADS_ENUM"

        # Test each load group naming
        create_permanent_load_group(mock_model)
        create_traffic_load_group(mock_model)
        create_wind_load_group(mock_model)

        # Verify names match SCIA interface
        calls = mock_model.create_load_group.call_args_list
        assert len(calls) == 3

        # Check names
        assert calls[0][0][0] == "LG1"  # Permanent
        assert calls[1][0][0] == "LG2"  # Traffic
        assert calls[2][0][0] == "LG3"  # Wind

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_load_group_types_match_scia_interface(self, mock_scia: Mock) -> None:
        """Test that load group types match SCIA interface exactly."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_model.create_load_group.return_value = mock_load_group

        # Setup enum mocks
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.LIVE_LOADS = "LIVE_LOADS_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.WIND_LOADS = "WIND_LOADS_ENUM"

        # Test each load group type
        create_permanent_load_group(mock_model)
        create_traffic_load_group(mock_model)
        create_wind_load_group(mock_model)

        # Verify types match SCIA interface
        calls = mock_model.create_load_group.call_args_list
        assert len(calls) == 3

        # Check load options
        assert calls[0][0][1] == "PERMANENT_ENUM"  # Permanent
        assert calls[1][0][1] == "VARIABLE_ENUM"  # Traffic
        assert calls[2][0][1] == "VARIABLE_ENUM"  # Wind

        # Check load type options
        assert calls[0][0][3] == "CONSTRUCTION_LOADS_ENUM"  # Permanent
        assert calls[1][0][3] == "LIVE_LOADS_ENUM"  # Traffic
        assert calls[2][0][3] == "WIND_LOADS_ENUM"  # Wind

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_all_load_groups_use_standard_relation(self, mock_scia: Mock) -> None:
        """Test that all load groups use standard relation option."""
        mock_model = Mock()
        mock_load_group = Mock()
        mock_model.create_load_group.return_value = mock_load_group

        # Setup enum mocks
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.LIVE_LOADS = "LIVE_LOADS_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.WIND_LOADS = "WIND_LOADS_ENUM"

        # Test each load group
        create_permanent_load_group(mock_model)
        create_traffic_load_group(mock_model)
        create_wind_load_group(mock_model)

        # Verify all use standard relation
        calls = mock_model.create_load_group.call_args_list
        assert len(calls) == 3

        for call in calls:
            assert call[0][2] == "STANDARD_ENUM"  # RelationOption.STANDARD


class TestLoadGroupIntegration:
    """Test load group integration with SCIA model."""

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_load_group_creation_workflow(self, mock_scia: Mock) -> None:
        """Test typical workflow of creating all load groups."""
        mock_model = Mock()
        mock_permanent_group = Mock()
        mock_traffic_group = Mock()
        mock_wind_group = Mock()

        mock_model.create_load_group.side_effect = [
            mock_permanent_group,
            mock_traffic_group,
            mock_wind_group,
        ]

        # Setup enum mocks
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.LoadOption.VARIABLE = "VARIABLE_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.LIVE_LOADS = "LIVE_LOADS_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.WIND_LOADS = "WIND_LOADS_ENUM"

        # Create load groups in typical workflow order
        permanent_group = create_permanent_load_group(mock_model)
        traffic_group = create_traffic_load_group(mock_model)
        wind_group = create_wind_load_group(mock_model)

        # Verify correct groups returned
        assert permanent_group is mock_permanent_group
        assert traffic_group is mock_traffic_group
        assert wind_group is mock_wind_group

        # Verify creation order and parameters
        assert mock_model.create_load_group.call_count == 3

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_load_group_reuse_and_independence(self, mock_scia: Mock) -> None:
        """Test that load groups can be created independently and reused."""
        mock_model = Mock()
        mock_load_group = Mock()

        mock_model.create_load_group.return_value = mock_load_group
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"

        # Create same load group multiple times
        group1 = create_permanent_load_group(mock_model)
        group2 = create_permanent_load_group(mock_model)

        # Each call should create a new group (no internal state)
        assert group1 is mock_load_group
        assert group2 is mock_load_group
        assert mock_model.create_load_group.call_count == 2

        # Verify same parameters used
        calls = mock_model.create_load_group.call_args_list
        assert calls[0] == calls[1]  # Same parameters for both calls


class TestLoadGroupErrorHandling:
    """Test load group error handling."""

    @patch("src.integrations.scia_integration.scia_load_group.scia")
    def test_load_group_creation_error_propagation(self, mock_scia: Mock) -> None:
        """Test that SCIA API errors are properly propagated."""
        mock_model = Mock()
        mock_model.create_load_group.side_effect = Exception("SCIA API error")

        # Setup enum mocks
        mock_scia.LoadGroup.LoadOption.PERMANENT = "PERMANENT_ENUM"
        mock_scia.LoadGroup.RelationOption.STANDARD = "STANDARD_ENUM"
        mock_scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS = "CONSTRUCTION_LOADS_ENUM"

        # Should propagate SCIA API error
        with pytest.raises(Exception, match="SCIA API error"):
            create_permanent_load_group(mock_model)

    def test_load_group_creation_with_none_model(self) -> None:
        """Test error handling when model is None."""
        with pytest.raises(AttributeError):
            create_permanent_load_group(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    pytest.main([__file__])
