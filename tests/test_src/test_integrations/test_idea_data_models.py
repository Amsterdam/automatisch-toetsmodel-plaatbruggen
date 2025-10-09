"""
Tests for IDEA integration data models.

This module tests the dataclasses used for IDEA integration that replace
direct BridgeParametrization dependencies in the src/ layer.
"""

from unittest.mock import MagicMock

import pytest

from src.integrations.idea_integration.idea_data_models import (
    BridgeGeometryConfig,
    BridgeIdeaInputData,
    ReinforcementZoneConfig,
    extract_bridge_idea_input_data,
)


class TestReinforcementZoneConfig:
    """Test ReinforcementZoneConfig dataclass."""

    def test_valid_reinforcement_zone_creation(self) -> None:
        """Test creating a valid reinforcement zone configuration."""
        config = ReinforcementZoneConfig(
            zone_number="1",
            hoofdwapening_langs_boven_diameter=16.0,
            hoofdwapening_langs_boven_hart_op_hart=150.0,
            hoofdwapening_langs_onder_diameter=20.0,
            hoofdwapening_langs_onder_hart_op_hart=150.0,
            hoofdwapening_dwars_boven_diameter=12.0,
            hoofdwapening_dwars_boven_hart_op_hart=200.0,
            hoofdwapening_dwars_onder_diameter=12.0,
            hoofdwapening_dwars_onder_hart_op_hart=200.0,
            heeft_bijlegwapening=True,
            bijlegwapening_langs_boven_diameter=10.0,
            bijlegwapening_langs_onder_diameter=10.0,
            bijlegwapening_dwars_boven_diameter=8.0,
            bijlegwapening_dwars_onder_diameter=8.0,
        )

        assert config.zone_number == "1"
        assert config.hoofdwapening_langs_boven_diameter == 16.0
        assert config.heeft_bijlegwapening is True
        assert config.bijlegwapening_langs_boven_diameter == 10.0

    def test_reinforcement_zone_without_extra_reinforcement(self) -> None:
        """Test reinforcement zone without additional reinforcement."""
        config = ReinforcementZoneConfig(
            zone_number="2",
            hoofdwapening_langs_boven_diameter=12.0,
            hoofdwapening_langs_boven_hart_op_hart=200.0,
            hoofdwapening_langs_onder_diameter=16.0,
            hoofdwapening_langs_onder_hart_op_hart=200.0,
            hoofdwapening_dwars_boven_diameter=10.0,
            hoofdwapening_dwars_boven_hart_op_hart=250.0,
            hoofdwapening_dwars_onder_diameter=10.0,
            hoofdwapening_dwars_onder_hart_op_hart=250.0,
            heeft_bijlegwapening=False,
            bijlegwapening_langs_boven_diameter=0.0,
            bijlegwapening_langs_onder_diameter=0.0,
            bijlegwapening_dwars_boven_diameter=0.0,
            bijlegwapening_dwars_onder_diameter=0.0,
        )

        assert config.heeft_bijlegwapening is False
        assert config.bijlegwapening_langs_boven_diameter == 0.0

    def test_reinforcement_zone_field_access(self) -> None:
        """Test that fields can be accessed as attributes."""
        config = ReinforcementZoneConfig(
            zone_number="3",
            hoofdwapening_langs_boven_diameter=16.0,
            hoofdwapening_langs_boven_hart_op_hart=150.0,
            hoofdwapening_langs_onder_diameter=20.0,
            hoofdwapening_langs_onder_hart_op_hart=150.0,
            hoofdwapening_dwars_boven_diameter=12.0,
            hoofdwapening_dwars_boven_hart_op_hart=200.0,
            hoofdwapening_dwars_onder_diameter=12.0,
            hoofdwapening_dwars_onder_hart_op_hart=200.0,
            heeft_bijlegwapening=False,
            bijlegwapening_langs_boven_diameter=0.0,
            bijlegwapening_langs_onder_diameter=0.0,
            bijlegwapening_dwars_boven_diameter=0.0,
            bijlegwapening_dwars_onder_diameter=0.0,
        )

        # Test direct attribute access (not dict-like)
        assert hasattr(config, "zone_number")
        assert hasattr(config, "hoofdwapening_langs_boven_diameter")
        assert hasattr(config, "heeft_bijlegwapening")


class TestBridgeGeometryConfig:
    """Test BridgeGeometryConfig dataclass."""

    def test_valid_geometry_config_creation(self) -> None:
        """Test creating a valid bridge geometry configuration."""
        config = BridgeGeometryConfig(
            dekking_boven=40.0,
            dekking_onder=50.0,
            langswapening_buiten=True,
        )

        assert config.dekking_boven == 40.0
        assert config.dekking_onder == 50.0
        assert config.langswapening_buiten is True

    def test_geometry_config_with_false_langswapening(self) -> None:
        """Test geometry configuration with langswapening_buiten as False."""
        config = BridgeGeometryConfig(
            dekking_boven=35.0,
            dekking_onder=45.0,
            langswapening_buiten=False,
        )

        assert config.langswapening_buiten is False


class TestBridgeIdeaInputData:
    """Test BridgeIdeaInputData dataclass."""

    def test_valid_bridge_input_data_creation(self) -> None:
        """Test creating valid bridge input data."""
        # Create sample reinforcement zones
        zones = [
            ReinforcementZoneConfig(
                zone_number="1",
                hoofdwapening_langs_boven_diameter=16.0,
                hoofdwapening_langs_boven_hart_op_hart=150.0,
                hoofdwapening_langs_onder_diameter=20.0,
                hoofdwapening_langs_onder_hart_op_hart=150.0,
                hoofdwapening_dwars_boven_diameter=12.0,
                hoofdwapening_dwars_boven_hart_op_hart=200.0,
                hoofdwapening_dwars_onder_diameter=12.0,
                hoofdwapening_dwars_onder_hart_op_hart=200.0,
                heeft_bijlegwapening=False,
                bijlegwapening_langs_boven_diameter=0.0,
                bijlegwapening_langs_onder_diameter=0.0,
                bijlegwapening_dwars_boven_diameter=0.0,
                bijlegwapening_dwars_onder_diameter=0.0,
            )
        ]

        geometry_config = BridgeGeometryConfig(
            dekking_boven=40.0,
            dekking_onder=50.0,
            langswapening_buiten=True,
        )

        bridge_segments = [
            {"bz1": 5.0, "bz2": 1.0, "bz3": 5.0, "dz": 0.3, "l": 10.0},
            {"bz1": 5.0, "bz2": 1.0, "bz3": 5.0, "dz": 0.4, "l": 12.0},
        ]

        input_data = BridgeIdeaInputData(
            entity_id=123,
            bridge_name="Test Bridge",
            concrete_strength_class="C30/37",
            steel_quality="B500B",
            reinforcement_zones=zones,
            geometry_config=geometry_config,
            bridge_segments=bridge_segments,
        )

        assert input_data.bridge_name == "Test Bridge"
        assert input_data.concrete_strength_class == "C30/37"
        assert input_data.steel_quality == "B500B"
        assert len(input_data.reinforcement_zones) == 1
        assert input_data.geometry_config.dekking_boven == 40.0
        assert len(input_data.bridge_segments) == 2

    def test_bridge_input_data_field_access(self) -> None:
        """Test field access on bridge input data."""
        zones = [
            ReinforcementZoneConfig(
                zone_number="1",
                hoofdwapening_langs_boven_diameter=16.0,
                hoofdwapening_langs_boven_hart_op_hart=150.0,
                hoofdwapening_langs_onder_diameter=20.0,
                hoofdwapening_langs_onder_hart_op_hart=150.0,
                hoofdwapening_dwars_boven_diameter=12.0,
                hoofdwapening_dwars_boven_hart_op_hart=200.0,
                hoofdwapening_dwars_onder_diameter=12.0,
                hoofdwapening_dwars_onder_hart_op_hart=200.0,
                heeft_bijlegwapening=False,
                bijlegwapening_langs_boven_diameter=0.0,
                bijlegwapening_langs_onder_diameter=0.0,
                bijlegwapening_dwars_boven_diameter=0.0,
                bijlegwapening_dwars_onder_diameter=0.0,
            )
        ]

        geometry_config = BridgeGeometryConfig(
            dekking_boven=40.0,
            dekking_onder=50.0,
            langswapening_buiten=True,
        )

        input_data = BridgeIdeaInputData(
            entity_id=123,
            bridge_name="Test",
            concrete_strength_class="C30/37",
            steel_quality="B500B",
            reinforcement_zones=zones,
            geometry_config=geometry_config,
            bridge_segments=[],
        )

        # Test attribute access
        assert hasattr(input_data, "bridge_name")
        assert hasattr(input_data, "concrete_strength_class")
        assert hasattr(input_data, "steel_quality")
        assert hasattr(input_data, "reinforcement_zones")
        assert hasattr(input_data, "geometry_config")
        assert hasattr(input_data, "bridge_segments")


class TestExtractBridgeIdeaInputData:
    """Test the extract_bridge_idea_input_data function."""

    def test_extract_from_params(self) -> None:
        """Test extracting input data from BridgeParametrization mock."""
        # Create a mock BridgeParametrization object
        mock_params = MagicMock()
        # Note: extract function uses getattr with bridge_objectnumm (double m)
        mock_params.info.bridge_objectnumm = "BR-12345"
        mock_params.concrete_strength_class = "C30/37"
        mock_params.input.geometrie_wapening.staalsoort = "B500B"

        # Mock reinforcement zones array - use MagicMock to support getattr()
        mock_zone = MagicMock()
        mock_zone.zone_number = "1"
        mock_zone.hoofdwapening_langs_boven_diameter = 16.0
        mock_zone.hoofdwapening_langs_boven_hart_op_hart = 150.0
        mock_zone.hoofdwapening_langs_onder_diameter = 20.0
        mock_zone.hoofdwapening_langs_onder_hart_op_hart = 150.0
        mock_zone.hoofdwapening_dwars_boven_diameter = 12.0
        mock_zone.hoofdwapening_dwars_boven_hart_op_hart = 200.0
        mock_zone.hoofdwapening_dwars_onder_diameter = 12.0
        mock_zone.hoofdwapening_dwars_onder_hart_op_hart = 200.0
        mock_zone.heeft_bijlegwapening = False
        mock_zone.bijlegwapening_langs_boven_diameter = 0.0
        mock_zone.bijlegwapening_langs_onder_diameter = 0.0
        mock_zone.bijlegwapening_dwars_boven_diameter = 0.0
        mock_zone.bijlegwapening_dwars_onder_diameter = 0.0

        mock_params.reinforcement_zones_array = [mock_zone]

        # Mock geometry config
        mock_params.input.geometrie_wapening.dekking_boven = 40.0
        mock_params.input.geometrie_wapening.dekking_onder = 50.0
        mock_params.input.geometrie_wapening.langswapening_buiten = True

        # Mock bridge segments - list of dict-like objects
        mock_segment = {"bz1": 5.0, "bz2": 1.0, "bz3": 5.0, "dz": 0.3, "l": 10.0}
        mock_params.bridge_segments_array = [mock_segment]

        # Extract data
        input_data = extract_bridge_idea_input_data(mock_params)

        # Verify extraction
        assert isinstance(input_data, BridgeIdeaInputData)
        assert input_data.entity_id == 0  # Default value
        assert input_data.bridge_name == "BR-12345"
        assert input_data.concrete_strength_class == "C30/37"
        assert input_data.steel_quality == "B500B"
        assert len(input_data.reinforcement_zones) == 1
        assert input_data.reinforcement_zones[0].zone_number == "1"
        assert input_data.geometry_config.dekking_boven == 40.0
        assert len(input_data.bridge_segments) == 1

    def test_extract_with_missing_optional_fields(self) -> None:
        """Test extraction handles missing optional fields gracefully."""
        mock_params = MagicMock()

        # Mock minimum required fields
        # Note: uses bridge_objectnumm (double m), getattr with None fallback
        mock_params.info.bridge_objectnumm = None  # Missing
        mock_params.concrete_strength_class = "C30/37"
        mock_params.input.geometrie_wapening.staalsoort = "B500B"
        mock_params.reinforcement_zones_array = []
        mock_params.input.geometrie_wapening.dekking_boven = 40.0
        mock_params.input.geometrie_wapening.dekking_onder = 50.0
        mock_params.input.geometrie_wapening.langswapening_buiten = True
        mock_params.bridge_segments_array = []

        # Extract data
        input_data = extract_bridge_idea_input_data(mock_params)

        # Verify extraction with defaults
        assert isinstance(input_data, BridgeIdeaInputData)
        assert input_data.entity_id == 0  # Default
        assert input_data.bridge_name == "Unnamed Bridge"  # Default
        assert input_data.concrete_strength_class == "C30/37"
        assert len(input_data.reinforcement_zones) == 0
        assert len(input_data.bridge_segments) == 0

    def test_extract_multiple_reinforcement_zones(self) -> None:
        """Test extraction with multiple reinforcement zones."""
        mock_params = MagicMock()
        mock_params.info.bridge_objectnumm = "BR-67890"  # Note: double m
        mock_params.concrete_strength_class = "C40/50"
        mock_params.input.geometrie_wapening.staalsoort = "B500B"

        # Create multiple zones as MagicMock objects to support getattr()
        mock_zones = []
        for i in range(1, 4):
            mock_zone = MagicMock()
            mock_zone.zone_number = str(i)
            mock_zone.hoofdwapening_langs_boven_diameter = 12.0 + i * 2
            mock_zone.hoofdwapening_langs_boven_hart_op_hart = 150.0
            mock_zone.hoofdwapening_langs_onder_diameter = 16.0 + i * 2
            mock_zone.hoofdwapening_langs_onder_hart_op_hart = 150.0
            mock_zone.hoofdwapening_dwars_boven_diameter = 10.0
            mock_zone.hoofdwapening_dwars_boven_hart_op_hart = 200.0
            mock_zone.hoofdwapening_dwars_onder_diameter = 10.0
            mock_zone.hoofdwapening_dwars_onder_hart_op_hart = 200.0
            mock_zone.heeft_bijlegwapening = False
            mock_zone.bijlegwapening_langs_boven_diameter = 0.0
            mock_zone.bijlegwapening_langs_onder_diameter = 0.0
            mock_zone.bijlegwapening_dwars_boven_diameter = 0.0
            mock_zone.bijlegwapening_dwars_onder_diameter = 0.0
            mock_zones.append(mock_zone)

        mock_params.reinforcement_zones_array = mock_zones

        mock_params.input.geometrie_wapening.dekking_boven = 40.0
        mock_params.input.geometrie_wapening.dekking_onder = 50.0
        mock_params.input.geometrie_wapening.langswapening_buiten = True
        mock_params.bridge_segments_array = []

        # Extract data
        input_data = extract_bridge_idea_input_data(mock_params)

        # Verify multiple zones were extracted
        assert len(input_data.reinforcement_zones) == 3
        assert input_data.reinforcement_zones[0].zone_number == "1"
        assert input_data.reinforcement_zones[1].zone_number == "2"
        assert input_data.reinforcement_zones[2].zone_number == "3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
