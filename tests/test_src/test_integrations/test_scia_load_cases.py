"""
Tests for SCIA load cases module.

Tests for load case creation functions using a mocked SciaModelBuilder.
"""

from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_cases import (
    create_all_load_cases,
    create_dead_load_cases,
    create_pedestrian_load_case,
    create_self_weight_load_case,
    create_service_vehicle_load_cases,
    create_tandem_rs_load_cases,
    create_temperature_load_cases,
    create_udl_traffic_load_cases,
    create_unintended_vehicle_load_cases,
)


@pytest.fixture
def mock_builder() -> Mock:
    """Fixture to provide a mocked SciaModelBuilder."""
    return Mock()


class TestStandardLoadCases:
    """Tests for creating standard load case definitions."""

    def test_create_self_weight_load_case(self, mock_builder: Mock) -> None:
        """Test the successful creation of a self-weight load case."""
        create_self_weight_load_case(mock_builder)
        mock_builder.create_load_case.assert_called_once_with(
            name="BG1001",
            description="Eigen gewicht",
            group_name="LG1000 - Permanent",
            case_type="PERMANENT",
            permanent_type="SELF_WEIGHT",
            variable_type=None,
            specification=None,
            duration=None,
        )

    def test_create_dead_load_cases(self, mock_builder: Mock) -> None:
        """Test creation of dead load cases."""
        create_dead_load_cases(mock_builder)
        assert mock_builder.create_load_case.call_count == 5
        mock_builder.create_load_case.assert_any_call(
            name="BG2001",
            description="Permanente belasting - Asfalt",
            group_name="LG2000 - Rustende belasting",
            case_type="PERMANENT",
            permanent_type="STANDARD",
            variable_type=None,
            specification=None,
            duration=None,
        )

    def test_create_temperature_load_cases(self, mock_builder: Mock) -> None:
        """Test creation of temperature load case definitions."""
        create_temperature_load_cases(mock_builder)
        assert mock_builder.create_load_case.call_count == 4
        mock_builder.create_load_case.assert_any_call(
            name="BG3001",
            description="Temperatuur, dek - Temp combi 1",
            group_name="LG3000 - Temperatuur",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="TEMPERATURE",
            duration="LONG",
            permanent_type=None,
        )

    def test_create_udl_traffic_load_cases(self, mock_builder: Mock) -> None:
        """Test creation of UDL traffic load case definitions."""
        create_udl_traffic_load_cases(mock_builder)
        assert mock_builder.create_load_case.call_count == 3
        mock_builder.create_load_case.assert_any_call(
            name="BG4001",
            description="Verkeer, dek - LM1 UDL RS 1",
            group_name="LG4000 - UDL",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
            permanent_type=None,
        )

    def test_create_pedestrian_load_case(self, mock_builder: Mock) -> None:
        """Test creation of pedestrian load case definition."""
        create_pedestrian_load_case(mock_builder)
        mock_builder.create_load_case.assert_called_once()

    @patch("src.integrations.scia_integration.scia_load_cases.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.scia_load_cases.tandem_system_sequencer")
    def test_create_service_vehicle_load_cases(self, mock_sequencer: Mock, mock_extract: Mock, mock_builder: Mock) -> None:
        """Test creation of service vehicle load case definitions with dynamic X positions."""
        # Setup mocks - extract_bridge_dimensions returns BridgeDimensions dataclass
        from src.integrations.scia_integration.scia_load_generators import BridgeDimensions

        mock_extract.return_value = BridgeDimensions(
            total_length=50.0, total_width=20.0, thickness=0.5, zone1_width=7.0, zone2_width=6.0, zone3_width=7.0, first_segment_thickness=0.5
        )
        mock_sequencer.return_value = [2.5, 25.0, 47.5]  # 3 X positions
        mock_params = Mock()

        cases = create_service_vehicle_load_cases(mock_builder, mock_params)

        # Should create 6 cases: 3 positions × 2 edges (y_plus, y_minus)
        assert mock_builder.create_load_case.call_count == 6
        assert len(cases) == 6

        # Check keys follow pattern
        expected_keys = ["y_plus_x2.5", "y_plus_x25.0", "y_plus_x47.5", "y_minus_x2.5", "y_minus_x25.0", "y_minus_x47.5"]
        assert list(cases.keys()) == expected_keys

        # Check first y_plus case
        mock_builder.create_load_case.assert_any_call(
            name="BG6001",
            description="Verkeer, dienstvoertuig - y+ - x = 2.5 m",
            group_name="LG6000 - Dienstvoertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )

        # Check first y_minus case
        mock_builder.create_load_case.assert_any_call(
            name="BG6004",
            description="Verkeer, dienstvoertuig - y- - x = 2.5 m",
            group_name="LG6000 - Dienstvoertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )

    @patch("src.integrations.scia_integration.scia_load_cases.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.scia_load_cases.tandem_system_sequencer")
    @patch("src.integrations.scia_integration.scia_load_cases.tandem_system_sequencer_single_axis")
    @patch("src.integrations.scia_integration.scia_load_cases.tandem_system_sequencer_single_axis_rotated")
    def test_create_unintended_vehicle_load_cases(
        self, mock_sequencer_rotated: Mock, mock_sequencer_single: Mock, mock_sequencer: Mock, mock_extract: Mock, mock_builder: Mock
    ) -> None:
        """Test creation of unintended vehicle load case definitions for standard and Amsterdam vehicles."""
        # Setup mocks - extract_bridge_dimensions returns BridgeDimensions dataclass
        from src.integrations.scia_integration.scia_load_generators import BridgeDimensions

        mock_extract.return_value = BridgeDimensions(
            total_length=50.0, total_width=20.0, thickness=0.5, zone1_width=7.0, zone2_width=6.0, zone3_width=7.0, first_segment_thickness=0.5
        )
        # Set up all sequencers to return the same test positions
        test_positions = [2.5, 25.0, 47.5]  # 3 X positions
        mock_sequencer.return_value = test_positions
        mock_sequencer_single.return_value = test_positions
        mock_sequencer_rotated.return_value = test_positions
        mock_params = Mock()

        cases = create_unintended_vehicle_load_cases(mock_builder, mock_params)

        # Verify sequencers were called correctly
        mock_sequencer.assert_called_once_with(50.0, 0.5, length_vehicle=1.2)  # Standard vehicle
        mock_sequencer_single.assert_called_once_with(50.0, 0.5)  # Amsterdam vehicle
        mock_sequencer_rotated.assert_called_once_with(50.0, 0.5, length_vehicle=2.0)  # Amsterdam vehicle rotated

        # Should create:
        # - Standard vehicle: 3 positions × 2 edges × 2 directions = 12 cases
        # - Amsterdam vehicle: 3 positions × 2 edges = 6 cases
        # - Amsterdam vehicle rotated: 3 positions × 2 edges = 6 cases
        # Total: 24 cases
        assert mock_builder.create_load_case.call_count == 24
        assert len(cases) == 24

        # Check keys follow expected pattern
        expected_standard_keys = [
            "rs_1_x2.5_forward",
            "rs_1_x25.0_forward",
            "rs_1_x47.5_forward",
            "rs_1_x2.5_reverse",
            "rs_1_x25.0_reverse",
            "rs_1_x47.5_reverse",
            "rs_3_x2.5_forward",
            "rs_3_x25.0_forward",
            "rs_3_x47.5_forward",
            "rs_3_x2.5_reverse",
            "rs_3_x25.0_reverse",
            "rs_3_x47.5_reverse",
        ]
        expected_amsterdam_keys = [f"rs_1_x{pos}_amsterdam" for pos in [2.5, 25.0, 47.5]] + [f"rs_3_x{pos}_amsterdam" for pos in [2.5, 25.0, 47.5]]
        expected_amsterdam_rotated_keys = [f"rs_1_x{pos}_amsterdam_rotated" for pos in [2.5, 25.0, 47.5]] + [
            f"rs_3_x{pos}_amsterdam_rotated" for pos in [2.5, 25.0, 47.5]
        ]
        expected_keys = expected_standard_keys + expected_amsterdam_keys + expected_amsterdam_rotated_keys
        assert sorted(cases.keys()) == sorted(expected_keys)

        # Check first RS1 forward case
        mock_builder.create_load_case.assert_any_call(
            name="BG7001",
            description="Verkeer, onbedoeld voertuig - RS 1 forward - x = 2.5 m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )

        # Check first RS1 reverse case
        mock_builder.create_load_case.assert_any_call(
            name="BG7004",
            description="Verkeer, onbedoeld voertuig - RS 1 reverse - x = 2.5 m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )


class TestTandemLoadCases:
    """Tests for creating tandem RS load case definitions."""

    @pytest.fixture
    def mock_objects(self) -> Generator[tuple[Mock, Mock], None, None]:
        """Provide mock objects for testing."""
        with patch("src.integrations.scia_integration.scia_load_cases.tandem_system_sequencer") as mock_sequencer:
            mock_sequencer.return_value = [10.0, 25.0, 49.5]
            yield mock_sequencer, Mock()

    @pytest.mark.parametrize(
        ("rs", "group", "prefix", "expected_count"),
        [(1, "LG8000 - TS rijstrook 1", "BG8", 3), (2, "LG9000 - TS rijstrook 2", "BG9", 3), (3, "LG10000 - TS rijstrook 3", "BG10", 6)],
    )
    def test_create_tandem_rs_load_cases(self, mock_objects: tuple[Mock, Mock], rs: int, group: str, prefix: str, expected_count: int) -> None:
        """Test creation of tandem RS load case definitions for different RS values."""
        mock_sequencer, mock_builder = mock_objects
        length_bridgedeck = 50.0
        thickness_bridgedeck = 0.5

        cases = create_tandem_rs_load_cases(mock_builder, rs, length_bridgedeck, thickness_bridgedeck)

        assert len(cases) == expected_count
        assert mock_builder.create_load_case.call_count == expected_count

        # Check the call for the first load case
        expected_name = f"{prefix}001"

        # The function calls builder.create_load_case directly, not the create_load_case helper
        mock_builder.create_load_case.assert_any_call(
            name=expected_name,
            description=f"Verkeer, dek - LM1 TS RS {rs} - x = 10 m" if rs != 3 else "Verkeer, dek - LM1 TS RS 3 (configuratie 1) - x = 10 m",
            group_name=group,
            case_type="VARIABLE",
            permanent_type=None,  # Function explicitly passes this
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )

    def test_invalid_rs_raises_value_error(self, mock_builder: Mock) -> None:
        """Test that invalid RS value raises ValueError."""
        with pytest.raises(ValueError, match="RS must be 1, 2, or 3"):
            create_tandem_rs_load_cases(mock_builder, 4, 50.0, 0.5)


class TestCreateAllLoadCases:
    """Tests for the main function creating all load cases."""

    @patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases")
    @patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases")
    @patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases")
    @patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases")
    @patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases")
    @patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case")
    def test_create_all_load_cases_calls_helpers(  # noqa: PLR0913
        self, mock_sw: Mock, mock_dead: Mock, mock_unintended: Mock, mock_service: Mock, mock_tandem: Mock, mock_tram_track: Mock
    ) -> None:
        """Test that all individual creation functions are called."""
        builder = Mock()
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        create_all_load_cases(builder, params)

        mock_sw.assert_called_once_with(builder)
        mock_dead.assert_called_once_with(builder)
        mock_service.assert_called_once_with(builder, params)
        mock_unintended.assert_called_once_with(builder, params)
        mock_tandem.assert_called_once_with(builder, params)
        mock_tram_track.assert_called_once_with(builder, params)

    def test_create_all_load_cases_structure(self) -> None:
        """Test that the function returns the expected dictionary structure."""
        builder = Mock()
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        # We patch here because we don't care about the return values, just the structure
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case"),
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases"),
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases"),
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases"),
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case"),
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases"),
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases"),
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases"),
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases"),
        ):
            all_cases = create_all_load_cases(builder, params)

        expected_keys = [
            "self_weight",
            "dead_load_cases",
            "temperature_cases",
            "udl_traffic_cases",
            "pedestrian",
            "service_vehicle_cases",
            "unintended_vehicle_cases",
            "tandem_cases",
            "tram_track_tandem_cases",
        ]
        assert list(all_cases.keys()) == expected_keys


class TestConditionalLoadCaseCreation:
    """Tests for conditional load case creation based on user selection."""

    def test_create_all_load_cases_with_all_enabled(self, mock_builder: Mock) -> None:
        """Test create_all_load_cases when all load types are enabled (default behavior)."""
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        # Mock the table with all load types enabled
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": True, "load_type": "Permanent", "load_case_count": 5},
            {"include": True, "load_type": "Temperatuur", "load_case_count": 4},
            {"include": True, "load_type": "UDL", "load_case_count": 3},
            {"include": True, "load_type": "Voetgangers", "load_case_count": 1},
            {"include": True, "load_type": "Dienstvoertuig", "load_case_count": 20},
            {"include": True, "load_type": "Onbedoeld voertuig", "load_case_count": 50},
            {"include": True, "load_type": "TS", "load_case_count": 30},
        ]

        # We patch here because we don't care about the return values, just the structure
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            all_cases = create_all_load_cases(mock_builder, params)

        # All functions should be called
        mock_self_weight.assert_called_once_with(mock_builder)
        mock_dead_loads.assert_called_once_with(mock_builder)
        mock_temperature.assert_called_once_with(mock_builder)
        mock_udl.assert_called_once_with(mock_builder)
        mock_pedestrian.assert_called_once_with(mock_builder)
        mock_service.assert_called_once_with(mock_builder, params)
        mock_unintended.assert_called_once_with(mock_builder, params)
        mock_tandem.assert_called_once_with(mock_builder, params)
        mock_tram_track.assert_called_once_with(mock_builder, params)

        # All expected keys should be present
        expected_keys = [
            "self_weight",
            "dead_load_cases",
            "temperature_cases",
            "udl_traffic_cases",
            "pedestrian",
            "service_vehicle_cases",
            "unintended_vehicle_cases",
            "tandem_cases",
            "tram_track_tandem_cases",
        ]
        assert list(all_cases.keys()) == expected_keys

    def test_create_all_load_cases_with_some_disabled(self, mock_builder: Mock) -> None:
        """Test create_all_load_cases when some load types are disabled."""
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        # Mock the table with some load types disabled
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": False, "load_type": "Permanent", "load_case_count": 5},  # Disabled
            {"include": True, "load_type": "Temperatuur", "load_case_count": 4},
            {"include": False, "load_type": "UDL", "load_case_count": 3},  # Disabled
            {"include": True, "load_type": "Voetgangers", "load_case_count": 1},
            {"include": False, "load_type": "Dienstvoertuig", "load_case_count": 20},  # Disabled
            {"include": True, "load_type": "Onbedoeld voertuig", "load_case_count": 50},
            {"include": False, "load_type": "TS", "load_case_count": 30},  # Disabled
        ]

        # We patch here because we don't care about the return values, just the structure
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            all_cases = create_all_load_cases(mock_builder, params)

        # Only enabled functions should be called
        mock_self_weight.assert_called_once_with(mock_builder)
        mock_dead_loads.assert_not_called()  # Disabled
        mock_temperature.assert_called_once_with(mock_builder)
        mock_udl.assert_not_called()  # Disabled
        mock_pedestrian.assert_called_once_with(mock_builder)
        mock_service.assert_not_called()  # Disabled
        mock_unintended.assert_called_once_with(mock_builder, params)
        mock_tandem.assert_not_called()  # Disabled
        mock_tram_track.assert_not_called()  # Disabled (TS includes tram track)

        # Only enabled keys should be present
        expected_keys = [
            "self_weight",
            "temperature_cases",
            "pedestrian",
            "unintended_vehicle_cases",
        ]
        assert list(all_cases.keys()) == expected_keys

    def test_create_all_load_cases_with_missing_table(self, mock_builder: Mock) -> None:
        """Test create_all_load_cases when params object doesn't have load case selection table (defaults to True)."""
        params = Mock()
        # Mock bridge_segments_array to be a list
        params.bridge_segments_array = [{"width": 10.0, "thickness": 0.5}]
        # Don't set load_case_selection_table - should default to all enabled

        # We patch here because we don't care about the return values, just the structure
        with (
            patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case") as mock_self_weight,
            patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases") as mock_dead_loads,
            patch("src.integrations.scia_integration.scia_load_cases.create_temperature_load_cases") as mock_temperature,
            patch("src.integrations.scia_integration.scia_load_cases.create_udl_traffic_load_cases") as mock_udl,
            patch("src.integrations.scia_integration.scia_load_cases.create_pedestrian_load_case") as mock_pedestrian,
            patch("src.integrations.scia_integration.scia_load_cases.create_service_vehicle_load_cases") as mock_service,
            patch("src.integrations.scia_integration.scia_load_cases.create_unintended_vehicle_load_cases") as mock_unintended,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases") as mock_tandem,
            patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tram_track_tandem_load_cases") as mock_tram_track,
        ):
            all_cases = create_all_load_cases(mock_builder, params)

        # All functions should be called (default behavior)
        mock_self_weight.assert_called_once_with(mock_builder)
        mock_dead_loads.assert_called_once_with(mock_builder)
        mock_temperature.assert_called_once_with(mock_builder)
        mock_udl.assert_called_once_with(mock_builder)
        mock_pedestrian.assert_called_once_with(mock_builder)
        mock_service.assert_called_once_with(mock_builder, params)
        mock_unintended.assert_called_once_with(mock_builder, params)
        mock_tandem.assert_called_once_with(mock_builder, params)
        mock_tram_track.assert_called_once_with(mock_builder, params)

        # All expected keys should be present
        expected_keys = [
            "self_weight",
            "dead_load_cases",
            "temperature_cases",
            "udl_traffic_cases",
            "pedestrian",
            "service_vehicle_cases",
            "unintended_vehicle_cases",
            "tandem_cases",
            "tram_track_tandem_cases",
        ]
        assert list(all_cases.keys()) == expected_keys
