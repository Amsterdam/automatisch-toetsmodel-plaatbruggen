"""
Tests for SCIA load group definitions.

This module tests the creation of SCIA load group definitions.
"""

from unittest.mock import Mock, patch

from src.integrations.scia_integration.scia_load_group import (
    create_basic_load_groups,
    create_permanent_load_group,
    create_traffic_load_group,
    create_wind_load_group,
)


class TestPermanentLoadGroup:
    """Tests for creating the permanent load group definition."""

    def test_create_permanent_load_group(self) -> None:
        """Test the successful creation of a permanent load group definition."""
        definition = create_permanent_load_group()
        assert definition.name == "LG1"
        assert definition.load_option == "PERMANENT"
        assert definition.relation == "STANDARD"
        assert definition.load_type == "CAT_G"

    def test_create_permanent_load_group_return_type(self) -> None:
        """Verify that the function returns a LoadGroupDefinition."""
        from src.integrations.scia_integration.scia_definitions import (
            LoadGroupDefinition,
        )

        definition = create_permanent_load_group()
        assert isinstance(definition, LoadGroupDefinition)


class TestTrafficLoadGroup:
    """Tests for creating the traffic load group definition."""

    def test_create_traffic_load_group(self) -> None:
        """Test the successful creation of a traffic load group definition."""
        definition = create_traffic_load_group()
        assert definition.name == "LG2"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "STANDARD"
        assert definition.load_type == "VARIABLE_LOADS"

    def test_create_traffic_load_group_return_type(self) -> None:
        """Verify that the function returns a LoadGroupDefinition."""
        from src.integrations.scia_integration.scia_definitions import (
            LoadGroupDefinition,
        )

        definition = create_traffic_load_group()
        assert isinstance(definition, LoadGroupDefinition)


class TestWindLoadGroup:
    """Tests for creating the wind load group definition."""

    def test_create_wind_load_group(self) -> None:
        """Test the successful creation of a wind load group definition."""
        definition = create_wind_load_group()
        assert definition.name == "LG3"
        assert definition.load_option == "VARIABLE"
        assert definition.relation == "STANDARD"
        assert definition.load_type == "VARIABLE_LOADS"

    def test_create_wind_load_group_return_type(self) -> None:
        """Verify that the function returns a LoadGroupDefinition."""
        from src.integrations.scia_integration.scia_definitions import (
            LoadGroupDefinition,
        )

        definition = create_wind_load_group()
        assert isinstance(definition, LoadGroupDefinition)


class TestBasicLoadGroups:
    """Tests for the helper function that creates all basic load groups."""

    @patch("src.integrations.scia_integration.scia_load_group.create_permanent_load_group")
    @patch("src.integrations.scia_integration.scia_load_group.create_traffic_load_group")
    @patch("src.integrations.scia_integration.scia_load_group.create_wind_load_group")
    def test_create_basic_load_groups(
        self,
        mock_create_wind: Mock,
        mock_create_traffic: Mock,
        mock_create_permanent: Mock,
    ) -> None:
        """Test that all basic load group creation functions are called."""
        # Setup mocks for the individual creation functions
        mock_permanent_def = Mock()
        mock_traffic_def = Mock()
        mock_wind_def = Mock()
        mock_create_permanent.return_value = mock_permanent_def
        mock_create_traffic.return_value = mock_traffic_def
        mock_create_wind.return_value = mock_wind_def

        # Execute the function
        definitions = create_basic_load_groups()

        # Verify that each creation function was called exactly once
        mock_create_permanent.assert_called_once()
        mock_create_traffic.assert_called_once()
        mock_create_wind.assert_called_once()

        # Verify that the returned dictionary contains the correct definitions
        assert definitions["permanent"] is mock_permanent_def
        assert definitions["traffic"] is mock_traffic_def
        assert definitions["wind"] is mock_wind_def
        assert len(definitions) == 3

    def test_create_basic_load_groups_return_structure(self) -> None:
        """Test that the function returns the expected dictionary structure."""
        definitions = create_basic_load_groups()

        # Check for correct keys
        assert "permanent" in definitions
        assert "traffic" in definitions
        assert "wind" in definitions

        # Check that values are of the correct type
        from src.integrations.scia_integration.scia_definitions import (
            LoadGroupDefinition,
        )

        assert isinstance(definitions["permanent"], LoadGroupDefinition)
        assert isinstance(definitions["traffic"], LoadGroupDefinition)
        assert isinstance(definitions["wind"], LoadGroupDefinition)
