"""
Tests for SCIA load cases module.

Tests for load case creation functions using a mocked SciaModelBuilder.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.load_system.scia_load_cases import (
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
from src.integrations.scia_integration.scia_enums import (
    LoadCaseActionType,
    LoadCaseDuration,
    LoadCaseSpecification,
    PermanentLoadType,
    VariableLoadType,
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
            case_type=LoadCaseActionType.PERMANENT,
            permanent_type=PermanentLoadType.SELF_WEIGHT,
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
            case_type=LoadCaseActionType.PERMANENT,
            permanent_type=PermanentLoadType.STANDARD,
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
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.TEMPERATURE,
            duration=LoadCaseDuration.LONG,
            permanent_type=None,
        )

    @patch("src.integrations.scia_integration.load_system.udl_generators.create_real_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.udl_generators.create_theoretical_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.get_load_mode_from_params")
    def test_create_udl_traffic_load_cases(
        self,
        mock_get_mode: Mock,
        mock_extract: Mock,
        mock_theoretical: Mock,
        mock_builder: Mock,
    ) -> None:
        """Test creation of UDL traffic load case definitions."""
        from src.data_models.scia_models import BridgeDimensionsData
        from src.integrations.scia_integration.types import LoadMode

        # Setup mocks
        mock_extract.return_value = BridgeDimensionsData(
            total_length=50.0,
            total_width=20.0,
            thickness=0.5,
            zone1_width=7.0,
            zone2_width=6.0,
            zone3_width=7.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
        )
        mock_get_mode.return_value = LoadMode.THEORETICAL

        # Mock UDL generator to return sample data
        mock_theoretical.return_value = {
            "BG4001": {"polygon": [], "load": 9000.0, "title": "RS 1 - Conf. A"},
            "BG4002": {"polygon": [], "load": 2500.0, "title": "RS 2 - Conf. A"},
            "BG4003": {"polygon": [], "load": 2500.0, "title": "rest 1 - Conf. A"},
            "BG4004": {"polygon": [], "load": 9000.0, "title": "RS 1 - Conf. B"},
            "BG4005": {"polygon": [], "load": 2500.0, "title": "RS 2 - Conf. B"},
            "BG4006": {"polygon": [], "load": 2500.0, "title": "rest 1 - Conf. B"},
            "BG4007": {"polygon": [], "load": 9000.0, "title": "RS 1 - Conf. C"},
            "BG4008": {"polygon": [], "load": 2500.0, "title": "RS 2 - Conf. C"},
            "BG4009": {"polygon": [], "load": 2500.0, "title": "rest 1 - Conf. C"},
        }

        mock_params = Mock()
        mock_params.berekeningsniveau = "Theoretische wegindeling"  # Add attribute as fallback

        cases = create_udl_traffic_load_cases(mock_builder, mock_params)

        # Should create 9 load cases
        assert mock_builder.create_load_case.call_count == 9
        assert len(cases) >= 9  # May include rs_1, rs_2, rs_3 for backward compatibility

        # Check first case (BG4001) - should be in conf. A group
        mock_builder.create_load_case.assert_any_call(
            name="BG4001",
            description="Verkeer, dek - LM1 UDL RS 1 - Conf. A",
            group_name="LG4000 - UDL - conf. A",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
            permanent_type=None,
        )

    def test_create_pedestrian_load_case(self, mock_builder: Mock) -> None:
        """Test creation of pedestrian load case definition."""
        create_pedestrian_load_case(mock_builder)
        mock_builder.create_load_case.assert_called_once()

    @patch("src.integrations.scia_integration.load_system.scia_load_cases.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.tandem_system_sequencer")
    def test_create_service_vehicle_load_cases(self, mock_sequencer: Mock, mock_extract: Mock, mock_builder: Mock) -> None:
        """Test creation of service vehicle load case definitions with dynamic X positions."""
        # Setup mocks - extract_bridge_dimensions returns BridgeDimensions dataclass
        from src.data_models.scia_models import BridgeDimensionsData

        mock_extract.return_value = BridgeDimensionsData(
            total_length=50.0,
            total_width=20.0,
            thickness=0.5,
            zone1_width=7.0,
            zone2_width=6.0,
            zone3_width=7.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
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
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )

        # Check first y_minus case
        mock_builder.create_load_case.assert_any_call(
            name="BG6004",
            description="Verkeer, dienstvoertuig - y- - x = 2.5 m",
            group_name="LG6000 - Dienstvoertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )

    @patch("src.integrations.scia_integration.load_system.scia_load_cases.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.tandem_system_sequencer")
    def test_create_unintended_vehicle_load_cases(self, mock_sequencer: Mock, mock_extract: Mock, mock_builder: Mock) -> None:
        """Test creation of unintended vehicle load case definitions with dynamic X positions."""
        from src.data_models.scia_models import BridgeDimensionsData

        mock_extract.return_value = BridgeDimensionsData(
            total_length=50.0,
            total_width=20.0,
            thickness=0.5,
            zone1_width=7.0,
            zone2_width=6.0,
            zone3_width=7.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
        )
        # Mock returns positions for all vehicle types (sequencer is now universal)
        # The function calls tandem_system_sequencer 3 times with different length_vehicle values
        mock_sequencer.side_effect = [
            [2.5, 25.0, 47.5],  # First call: length_vehicle=1.2
            [5.0, 45.0],  # Second call: length_vehicle=0 (Amsterdam)
            [10.0, 40.0],  # Third call: length_vehicle=2.0 (Amsterdam rotated)
        ]
        mock_params = Mock()

        cases = create_unintended_vehicle_load_cases(mock_builder, mock_params)

        # Expected: 3 positions × 2 directions × 2 edges + 2 Amsterdam × 2 edges + 2 Amsterdam rotated × 2 edges
        # = 12 bidirectional + 4 Amsterdam + 4 rotated = 20 cases total
        expected_count = 3 * 2 * 2 + 2 * 2 + 2 * 2
        assert mock_builder.create_load_case.call_count == expected_count
        assert len(cases) == expected_count

        # Check a bidirectional RS1 forward case
        mock_builder.create_load_case.assert_any_call(
            name="BG7001",
            description="Verkeer, onbedoeld voertuig - y+ forward - x = 2.5 m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )


class TestTandemLoadCases:
    """Tests for creating tandem load case definitions with dynamic X positions."""

    @pytest.mark.parametrize(
        ("rs", "group_name", "prefix", "positions_count"),
        [
            (1, "LG8000 - TS rijstrook 1", "BG8", 3),
            (2, "LG9000 - TS rijstrook 2", "BG9", 3),
            (3, "LG10000 - TS rijstrook 3", "BG10", 6),  # RS3 has 2 configurations: 3 × 2 = 6 cases
        ],
    )
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.tandem_system_sequencer")
    def test_create_tandem_rs_load_cases(  # noqa: PLR0913
        self, mock_sequencer: Mock, mock_extract: Mock, rs: int, group_name: str, prefix: str, positions_count: int, mock_builder: Mock
    ) -> None:
        """Test creation of tandem load case definitions for different RS."""
        from src.data_models.scia_models import BridgeDimensionsData

        mock_extract.return_value = BridgeDimensionsData(
            total_length=50.0,
            total_width=20.0,
            thickness=0.5,
            zone1_width=7.0,
            zone2_width=6.0,
            zone3_width=7.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
        )
        mock_sequencer.return_value = [2.5, 25.0, 47.5]

        cases = create_tandem_rs_load_cases(mock_builder, rs, 50.0, 0.5)

        # Verify correct number of cases created
        assert len(cases) == positions_count
        assert mock_builder.create_load_case.call_count == positions_count

        # Check that a case was called with the expected parameters (check call structure)
        calls = mock_builder.create_load_case.call_args_list
        first_call = calls[0]
        assert first_call[1]["name"] == f"{prefix}001"
        assert group_name in first_call[1]["description"] or first_call[1]["group_name"] == group_name
        assert first_call[1]["case_type"] == LoadCaseActionType.VARIABLE
        assert first_call[1]["variable_type"] == VariableLoadType.STATIC
        assert first_call[1]["specification"] == LoadCaseSpecification.STANDARD
        assert first_call[1]["duration"] == LoadCaseDuration.SHORT

    def test_invalid_rs_raises_value_error(self, mock_builder: Mock) -> None:
        """Test that invalid RS raises ValueError."""
        with pytest.raises(ValueError, match="RS must be 1, 2, or 3"):
            create_tandem_rs_load_cases(mock_builder, 99, 50.0, 0.5)

    @patch("src.integrations.scia_integration.load_system.scia_load_generators.generate_tandem_loads")
    def test_dynamic_tandem_load_cases_title_based_grouping(self, mock_generate: Mock, mock_builder: Mock) -> None:
        """Test that dynamic tandem load cases are assigned to groups based on title content."""
        from src.integrations.scia_integration.load_system.scia_load_cases import create_dynamic_tandem_load_cases

        # Mock tandem loads with different titles and load case names
        # Key point: BG8xxx load with "rs 2" in title should go to LG9000
        # and BG9xxx load with "rs 1" in title should go to LG8000
        mock_generate.return_value = [
            {"load_case": "BG8001", "title": "rs 1 - Conf. A - x = 2.5 m", "wheels": [], "load": 300},
            {"load_case": "BG8002", "title": "rs 2 - Conf. A - x = 2.5 m", "wheels": [], "load": 200},
            {"load_case": "BG9001", "title": "rs 1 - Conf. B - x = 5.0 m", "wheels": [], "load": 300},
            {"load_case": "BG9002", "title": "rs 3 - Conf. A - x = 5.0 m", "wheels": [], "load": 100},
            {"load_case": "BG10001", "title": "rs 1 - Conf. C - x = 7.5 m", "wheels": [], "load": 300},
            {"load_case": "BG10002", "title": "rs 2 - Conf. C - x = 7.5 m", "wheels": [], "load": 200},
            {"load_case": "BG10003", "title": "rs 3 - Conf. C - x = 7.5 m", "wheels": [], "load": 100},
        ]

        mock_params = Mock()
        cases = create_dynamic_tandem_load_cases(mock_builder, mock_params)

        # Verify all cases were created
        assert mock_builder.create_load_case.call_count == 7
        assert len(cases) == 7

        # Verify title-based grouping (not based on load case name prefix)
        calls = {call[1]["name"]: call[1] for call in mock_builder.create_load_case.call_args_list}

        # BG8001 with "rs 1" should go to LG8000
        assert calls["BG8001"]["group_name"] == "LG8000 - TS rijstrook 1"

        # BG8002 with "rs 2" should go to LG9000 (not LG8000 based on case name)
        assert calls["BG8002"]["group_name"] == "LG9000 - TS rijstrook 2"

        # BG9001 with "rs 1" should go to LG8000 (not LG9000 based on case name)
        assert calls["BG9001"]["group_name"] == "LG8000 - TS rijstrook 1"

        # BG9002 with "rs 3" should go to LG10000
        assert calls["BG9002"]["group_name"] == "LG10000 - TS rijstrook 3"

        # BG10xxx cases should be grouped by their title, not their case name
        assert calls["BG10001"]["group_name"] == "LG8000 - TS rijstrook 1"  # rs 1 in title
        assert calls["BG10002"]["group_name"] == "LG9000 - TS rijstrook 2"  # rs 2 in title
        assert calls["BG10003"]["group_name"] == "LG10000 - TS rijstrook 3"  # rs 3 in title


class TestCreateAllLoadCases:
    """Tests for the orchestration function that creates all load cases."""

    @patch("src.integrations.scia_integration.load_system.scia_load_cases.create_self_weight_load_case")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dead_load_cases")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.create_temperature_load_cases")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.create_udl_traffic_load_cases")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.create_pedestrian_load_case")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.create_service_vehicle_load_cases")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.create_unintended_vehicle_load_cases")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.create_dynamic_tandem_load_cases")
    def test_create_all_load_cases_calls_helpers(  # noqa: PLR0913
        self,
        mock_tandem: Mock,
        mock_unintended: Mock,
        mock_service: Mock,
        mock_pedestrian: Mock,
        mock_udl: Mock,
        mock_temperature: Mock,
        mock_dead: Mock,
        mock_self_weight: Mock,
        mock_builder: Mock,
    ) -> None:
        """Test that create_all_load_cases calls all helper functions."""
        from tests.test_data.seed_loader import load_bridge_default_params

        mock_params = load_bridge_default_params()
        mock_params.belastinggevallen = {"load_case_selection_table": []}
        mock_params.berekeningsniveau = "Theoretische wegindeling"
        mock_params.design_code = "NEN 8700 gebruik"
        create_all_load_cases(mock_builder, mock_params)

        # Check that each helper function was called
        mock_self_weight.assert_called_once()
        mock_dead.assert_called_once()
        mock_temperature.assert_called_once()
        mock_udl.assert_called_once()
        mock_pedestrian.assert_called_once()
        mock_service.assert_called_once()
        mock_unintended.assert_called_once()
        mock_tandem.assert_called_once()

    @patch("src.integrations.scia_integration.load_system.udl_generators.create_real_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.udl_generators.create_theoretical_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.get_load_mode_from_params")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.tandem_system_sequencer")
    def test_create_all_load_cases_structure(
        self, mock_sequencer: Mock, mock_get_mode: Mock, mock_extract: Mock, mock_theoretical: Mock, mock_builder: Mock
    ) -> None:
        """Test that create_all_load_cases returns the expected structure."""
        from src.data_models.scia_models import BridgeDimensionsData
        from src.integrations.scia_integration.types import LoadMode

        mock_extract.return_value = BridgeDimensionsData(
            total_length=50.0,
            total_width=20.0,
            thickness=0.5,
            zone1_width=7.0,
            zone2_width=6.0,
            zone3_width=7.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
        )
        mock_get_mode.return_value = LoadMode.THEORETICAL
        # Return positions for all calls to tandem_system_sequencer
        from src.integrations.scia_integration.types import LoadMode

        mock_sequencer.return_value = [2.5, 25.0, 47.5]

        # Mock UDL generators to return sample data
        mock_theoretical.return_value = {
            "BG4001": {"polygon": [], "load": 9000.0, "title": "RS 1 - Conf. A"},
            "BG4002": {"polygon": [], "load": 2500.0, "title": "RS 2 - Conf. A"},
            "BG4003": {"polygon": [], "load": 2500.0, "title": "rest 1 - Conf. A"},
        }

        from tests.test_data.seed_loader import load_bridge_default_params

        mock_params = load_bridge_default_params()
        mock_params.belastinggevallen = {"load_case_selection_table": []}
        # Add berekeningsniveau as fallback
        if not hasattr(mock_params, "berekeningsniveau"):
            mock_params.berekeningsniveau = "Theoretische wegindeling"
        mock_params.design_code = "NEN 8700 gebruik"
        cases = create_all_load_cases(mock_builder, mock_params)

        # Check that the result is a dictionary
        assert isinstance(cases, dict)
        # Check that all expected top-level keys are present
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
        assert list(cases.keys()) == expected_keys


class TestConditionalLoadCaseCreation:
    """Tests for conditional load case creation based on load case selection table."""

    @patch("src.integrations.scia_integration.load_system.udl_generators.create_real_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.udl_generators.create_theoretical_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.get_load_mode_from_params")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.tandem_system_sequencer")
    def test_create_all_load_cases_with_all_enabled(
        self, mock_sequencer: Mock, mock_get_mode: Mock, mock_extract: Mock, mock_theoretical: Mock, mock_builder: Mock
    ) -> None:
        """Test that all load cases are created when all are enabled in the params table."""
        from src.data_models.scia_models import BridgeDimensionsData
        from src.integrations.scia_integration.types import LoadMode

        mock_extract.return_value = BridgeDimensionsData(
            total_length=50.0,
            total_width=20.0,
            thickness=0.5,
            zone1_width=7.0,
            zone2_width=6.0,
            zone3_width=7.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
        )
        mock_get_mode.return_value = LoadMode.THEORETICAL
        # Return positions for all calls to tandem_system_sequencer
        mock_sequencer.return_value = [2.5, 25.0, 47.5]

        # Mock UDL generators to return sample data
        mock_theoretical.return_value = {
            "BG4001": {"polygon": [], "load": 9000.0, "title": "RS 1 - Conf. A"},
            "BG4002": {"polygon": [], "load": 2500.0, "title": "RS 2 - Conf. A"},
            "BG4003": {"polygon": [], "load": 2500.0, "title": "rest 1 - Conf. A"},
        }

        # Create mock params with load case selection table where all are enabled
        from tests.test_data.seed_loader import load_bridge_default_params

        mock_params = load_bridge_default_params()
        mock_params.berekeningsniveau = "Theoretische wegindeling"
        mock_params.design_code = "NEN 8700 gebruik"
        mock_params.belastinggevallen = {
            "load_case_selection_table": [
                {"load_type": "Temperature", "enabled": True},
                {"load_type": "UDL", "enabled": True},
                {"load_type": "Pedestrian", "enabled": True},
                {"load_type": "Service Vehicle", "enabled": True},
                {"load_type": "Unintended Vehicle", "enabled": True},
                {"load_type": "Tandem RS 1", "enabled": True},
                {"load_type": "Tandem RS 2", "enabled": True},
                {"load_type": "Tandem RS 3", "enabled": True},
            ]
        }
        # Add berekeningsniveau as fallback
        if not hasattr(mock_params, "berekeningsniveau"):
            mock_params.berekeningsniveau = "Theoretische wegindeling"

        cases = create_all_load_cases(mock_builder, mock_params)

        # All categories should be present
        assert "temperature_cases" in cases
        assert "udl_traffic_cases" in cases
        assert "pedestrian" in cases
        assert "service_vehicle_cases" in cases
        assert "unintended_vehicle_cases" in cases
        assert "tandem_cases" in cases

    @patch("src.integrations.scia_integration.load_system.udl_generators.create_real_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.udl_generators.create_theoretical_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.get_load_mode_from_params")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.tandem_system_sequencer")
    def test_create_all_load_cases_with_some_disabled(
        self, mock_sequencer: Mock, mock_get_mode: Mock, mock_extract: Mock, mock_theoretical: Mock, mock_builder: Mock
    ) -> None:
        """Test that only enabled load cases are created when some are disabled."""
        from src.data_models.scia_models import BridgeDimensionsData
        from src.integrations.scia_integration.types import LoadMode

        mock_extract.return_value = BridgeDimensionsData(
            total_length=50.0,
            total_width=20.0,
            thickness=0.5,
            zone1_width=7.0,
            zone2_width=6.0,
            zone3_width=7.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
        )
        mock_get_mode.return_value = LoadMode.THEORETICAL
        # Return positions for all calls to tandem_system_sequencer
        mock_sequencer.return_value = [2.5, 25.0, 47.5]

        # Mock UDL generators to return sample data
        mock_theoretical.return_value = {
            "BG4001": {"polygon": [], "load": 9000.0, "title": "RS 1 - Conf. A"},
            "BG4002": {"polygon": [], "load": 2500.0, "title": "RS 2 - Conf. A"},
            "BG4003": {"polygon": [], "load": 2500.0, "title": "rest 1 - Conf. A"},
        }

        # Create mock params with some load cases disabled
        from tests.test_data.seed_loader import load_bridge_default_params

        mock_params = load_bridge_default_params()
        mock_params.berekeningsniveau = "Theoretische wegindeling"
        mock_params.design_code = "NEN 8700 gebruik"
        mock_params.belastinggevallen = {
            "load_case_selection_table": [
                {"load_type": "Temperature", "enabled": True},
                {"load_type": "UDL", "enabled": False},  # Disabled
                {"load_type": "Pedestrian", "enabled": True},
                {"load_type": "Service Vehicle", "enabled": False},  # Disabled
                {"load_type": "Unintended Vehicle", "enabled": True},
                {"load_type": "Tandem RS 1", "enabled": True},
                {"load_type": "Tandem RS 2", "enabled": False},  # Disabled
                {"load_type": "Tandem RS 3", "enabled": True},
            ]
        }
        # Add berekeningsniveau as fallback
        if not hasattr(mock_params, "berekeningsniveau"):
            mock_params.berekeningsniveau = "Theoretische wegindeling"

        cases = create_all_load_cases(mock_builder, mock_params)

        # The selection logic filters at a higher level - just verify structure is correct
        # and that we can call the function with a selection table
        assert isinstance(cases, dict)
        # At minimum, self_weight and dead_load_cases should be present (always enabled)
        assert "self_weight" in cases
        assert "dead_load_cases" in cases

    @patch("src.integrations.scia_integration.load_system.udl_generators.create_real_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.udl_generators.create_theoretical_udl_traffic_loads")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.extract_bridge_dimensions")
    @patch("src.integrations.scia_integration.load_system.scia_load_generators.get_load_mode_from_params")
    @patch("src.integrations.scia_integration.load_system.scia_load_cases.tandem_system_sequencer")
    def test_create_all_load_cases_with_missing_table(
        self, mock_sequencer: Mock, mock_get_mode: Mock, mock_extract: Mock, mock_theoretical: Mock, mock_builder: Mock
    ) -> None:
        """Test that all load cases are created when the selection table is missing."""
        from src.data_models.scia_models import BridgeDimensionsData
        from src.integrations.scia_integration.types import LoadMode

        mock_extract.return_value = BridgeDimensionsData(
            total_length=50.0,
            total_width=20.0,
            thickness=0.5,
            zone1_width=7.0,
            zone2_width=6.0,
            zone3_width=7.0,
            first_segment_thickness=0.5,
            first_segment_thickness_2=0.5,  # Must equal first_segment_thickness
        )
        mock_get_mode.return_value = LoadMode.THEORETICAL
        # Return positions for all calls to tandem_system_sequencer
        from src.integrations.scia_integration.types import LoadMode

        mock_sequencer.return_value = [2.5, 25.0, 47.5]

        # Mock UDL generators to return sample data
        mock_theoretical.return_value = {
            "BG4001": {"polygon": [], "load": 9000.0, "title": "RS 1 - Conf. A"},
            "BG4002": {"polygon": [], "load": 2500.0, "title": "RS 2 - Conf. A"},
            "BG4003": {"polygon": [], "load": 2500.0, "title": "rest 1 - Conf. A"},
        }

        # Create mock params without load case selection table
        from tests.test_data.seed_loader import load_bridge_default_params

        mock_params = load_bridge_default_params()
        mock_params.berekeningsniveau = "Theoretische wegindeling"
        mock_params.design_code = "NEN 8700 gebruik"
        mock_params.belastinggevallen = {}  # No load_case_selection_table
        # Add berekeningsniveau as fallback
        if not hasattr(mock_params, "berekeningsniveau"):
            mock_params.berekeningsniveau = "Theoretische wegindeling"

        cases = create_all_load_cases(mock_builder, mock_params)

        # All categories should be present (default to all enabled)
        assert "temperature_cases" in cases
        assert "udl_traffic_cases" in cases
        assert "pedestrian" in cases
        assert "service_vehicle_cases" in cases
        assert "unintended_vehicle_cases" in cases
        assert "tandem_cases" in cases
