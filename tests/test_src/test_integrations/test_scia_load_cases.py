"""
Tests for SCIA load cases module.

Tests for load case creation functions using a mocked SciaModelBuilder.
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_integration.scia_load_cases import (
    create_all_load_cases,
    create_dead_load_cases,
    create_dynamic_tandem_load_cases,
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
            group_name="LG1000",
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
            group_name="LG2000",
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
            group_name="LG3000",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="TEMPERATURE",
            duration="LONG",
            permanent_type=None,
        )

    def test_create_udl_traffic_load_cases(self, mock_builder: Mock) -> None:
        """Test creation of UDL traffic load case definitions."""
        create_udl_traffic_load_cases(mock_builder)
        assert mock_builder.create_load_case.call_count == 4
        mock_builder.create_load_case.assert_any_call(
            name="BG4001",
            description="Verkeer, dek - LM1 UDL RS 1",
            group_name="LG4000",
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

    def test_create_service_vehicle_load_cases(self, mock_builder: Mock) -> None:
        """Test creation of service vehicle load case definitions."""
        create_service_vehicle_load_cases(mock_builder)
        assert mock_builder.create_load_case.call_count == 3

    def test_create_unintended_vehicle_load_cases(self, mock_builder: Mock) -> None:
        """Test creation of unintended vehicle load case definitions."""
        create_unintended_vehicle_load_cases(mock_builder)
        assert mock_builder.create_load_case.call_count == 3


class TestTandemLoadCases:
    """Tests for creating tandem RS load case definitions."""

    @patch("src.integrations.scia_integration.scia_load_cases.tandem_system_sequencer")
    @pytest.mark.parametrize(("rs", "group", "prefix"), [(1, "LG8000", "BG8000"), (2, "LG9000", "BG9000"), (3, "LG10000", "BG10000")])
    def test_create_tandem_rs_load_cases(self, mock_sequencer: Mock, mock_builder: Mock, rs: int, group: str, prefix: str) -> None:
        """Test creation of tandem RS load case definitions for different RS values."""
        mock_sequencer.return_value = [10.0, 25.0, 49.5]
        length_bridgedeck = 50.0
        thickness_bridgedeck = 0.5

        cases = create_tandem_rs_load_cases(mock_builder, rs, length_bridgedeck, thickness_bridgedeck)

        assert len(cases) == 3
        assert mock_builder.create_load_case.call_count == 3

        # Check the call for the first load case
        mock_builder.create_load_case.assert_any_call(
            name=f"{prefix}001",
            description=f"Verkeer, dek - LM1 TS RS {rs} - x = 10 m",
            group_name=group,
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )

    def test_invalid_rs_raises_value_error(self, mock_builder: Mock) -> None:
        """Test that invalid RS value raises ValueError."""
        with pytest.raises(ValueError, match="RS must be 1, 2, or 3"):
            create_tandem_rs_load_cases(mock_builder, 4, 50.0, 0.5)

    @patch("src.integrations.scia_integration.scia_load_cases.extract_tandem_parameters_from_bridge")
    @patch("src.integrations.scia_integration.scia_load_cases.generate_theoretical_lane_positions")
    @patch("src.integrations.scia_integration.scia_load_cases.create_tandem_rs_load_cases")
    def test_create_dynamic_tandem_load_cases(
        self, mock_create_rs: Mock, mock_generate_lanes: Mock, mock_extract_params: Mock, mock_builder: Mock
    ) -> None:
        """Test the creation of dynamic tandem load cases."""
        mock_params = Mock()
        mock_extract_params.return_value = {
            "length_bridgedeck": 50.0,
            "thickness_bridgedeck": 0.5,
            "width_bridgedeck": 12.0,
        }
        mock_generate_lanes.return_value = [1.5, 4.5, 7.5, 10.5]  # 4 lanes, but should be capped at 3

        create_dynamic_tandem_load_cases(mock_builder, mock_params)

        assert mock_create_rs.call_count == 3  # Called for RS 1, 2, and 3
        mock_create_rs.assert_any_call(mock_builder, 1, 50.0, 0.5)
        mock_create_rs.assert_any_call(mock_builder, 2, 50.0, 0.5)
        mock_create_rs.assert_any_call(mock_builder, 3, 50.0, 0.5)


@patch("src.integrations.scia_integration.scia_load_cases.create_self_weight_load_case")
@patch("src.integrations.scia_integration.scia_load_cases.create_dead_load_cases")
@patch("src.integrations.scia_integration.scia_load_cases.create_dynamic_tandem_load_cases")
class TestCreateAllLoadCases:
    """Tests for the main function creating all load cases."""

    @pytest.mark.usefixtures("mock_tandem", "mock_dead", "mock_sw")
    def test_create_all_load_cases_structure(self) -> None:
        """Test that the function returns the expected dictionary structure."""
        builder = Mock()
        params = Mock()
        all_cases = create_all_load_cases(builder, params)

        expected_keys = [
            "standard_cases",
            "dead_load_cases",
            "temperature_cases",
            "udl_traffic_cases",
            "service_vehicle_cases",
            "unintended_vehicle_cases",
            "tandem_cases",
        ]
        assert list(all_cases.keys()) == expected_keys
        assert "self_weight" in all_cases["standard_cases"]
        assert "pedestrian" in all_cases["standard_cases"]

    def test_create_all_load_cases_calls_helpers(self, mock_tandem: Mock, mock_dead: Mock, mock_sw: Mock) -> None:
        """Test that all individual creation functions are called."""
        builder = Mock()
        params = Mock()
        create_all_load_cases(builder, params)

        mock_sw.assert_called_once_with(builder)
        mock_dead.assert_called_once_with(builder)
        mock_tandem.assert_called_once_with(builder, params)
