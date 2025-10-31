"""Tests for IDEA StatiCa integration Pydantic models."""

import unittest

import pytest
from pydantic import ValidationError

from src.data_models.idea_models import ReinforcementConfigData


class TestReinforcementConfigData(unittest.TestCase):
    """Test cases for ReinforcementConfigData Pydantic model."""

    def test_valid_reinforcement_config_creation(self) -> None:
        """Test creating valid reinforcement configuration."""
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0, "zone2": 200.0},
            main_reinf_diameters={"zone1": 12.0, "zone2": 16.0},
            reinf_heights={"zone1": 50.0, "zone2": 75.0},
            extra_reinf_diameter={"zone1": 8.0},
            extra_reinf_ctc_distances={"zone1": 300.0},
            has_extra_reinforcement=True,
            rebar_config={"material": "steel", "grade": "B500B", "cover": 40.0},
        )

        assert config.main_reinf_ctc_distances == {"zone1": 150.0, "zone2": 200.0}
        assert config.main_reinf_diameters == {"zone1": 12.0, "zone2": 16.0}
        assert config.reinf_heights == {"zone1": 50.0, "zone2": 75.0}
        assert config.extra_reinf_diameter == {"zone1": 8.0}
        assert config.extra_reinf_ctc_distances == {"zone1": 300.0}
        assert config.has_extra_reinforcement is True
        assert config.rebar_config == {"material": "steel", "grade": "B500B", "cover": 40.0}

    def test_reinforcement_diameter_validation(self) -> None:
        """Test reinforcement diameter validation."""
        # Valid diameters
        valid_diameters = [6, 8, 10, 12, 14, 16, 20, 25, 32, 40]

        for diameter in valid_diameters:
            config = ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": float(diameter)},
                reinf_heights={"zone1": 50.0},
                extra_reinf_diameter={},
                extra_reinf_ctc_distances={},
                has_extra_reinforcement=False,
                rebar_config={},
            )
            assert config.main_reinf_diameters["zone1"] == diameter

        # Invalid diameters
        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": 5.0},  # Too small
                reinf_heights={"zone1": 50.0},
                extra_reinf_diameter={},
                extra_reinf_ctc_distances={},
                has_extra_reinforcement=False,
                rebar_config={},
            )

        error = exc_info.value
        assert "Reinforcement diameter 5.0mm in zone 'zone1' is not standard" in str(error)

        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": 50.0},  # Too large
                reinf_heights={"zone1": 50.0},
                extra_reinf_diameter={},
                extra_reinf_ctc_distances={},
                has_extra_reinforcement=False,
                rebar_config={},
            )

        error = exc_info.value
        assert "Reinforcement diameter 50.0mm in zone 'zone1' is not standard" in str(error)

        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": 15.0},  # Non-standard size
                reinf_heights={"zone1": 50.0},
                extra_reinf_diameter={},
                extra_reinf_ctc_distances={},
                has_extra_reinforcement=False,
                rebar_config={},
            )

        error = exc_info.value
        assert "Reinforcement diameter 15.0mm in zone 'zone1' is not standard" in str(error)

    def test_ctc_distance_validation(self) -> None:
        """Test center-to-center distance validation."""
        # Valid distances
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 100.0},  # Valid distance
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": 50.0},
            extra_reinf_ctc_distances={"zone1": 250.0},  # Valid distance
            extra_reinf_diameter={"zone1": 8.0},
            has_extra_reinforcement=True,
            rebar_config={},
        )
        assert config.main_reinf_ctc_distances["zone1"] == 100.0
        assert config.extra_reinf_ctc_distances["zone1"] == 250.0

        # Distance too small
        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 30.0},  # Too small
                main_reinf_diameters={"zone1": 12.0},
                reinf_heights={"zone1": 50.0},
                extra_reinf_ctc_distances={},
                extra_reinf_diameter={},
                has_extra_reinforcement=False,
                rebar_config={},
            )

        error = exc_info.value
        assert "Center-to-center distance 30.0mm in zone 'zone1' is too small" in str(error)

        # Distance too large
        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 600.0},  # Too large
                main_reinf_diameters={"zone1": 12.0},
                reinf_heights={"zone1": 50.0},
                extra_reinf_ctc_distances={},
                extra_reinf_diameter={},
                has_extra_reinforcement=False,
                rebar_config={},
            )

        error = exc_info.value
        assert "Center-to-center distance 600.0mm in zone 'zone1' is too large" in str(error)

    def test_reinforcement_height_validation(self) -> None:
        """Test reinforcement height validation."""
        # Valid heights
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0},
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": 100.0},  # Valid height
            extra_reinf_diameter={},
            extra_reinf_ctc_distances={},
            has_extra_reinforcement=False,
            rebar_config={},
        )
        assert config.reinf_heights["zone1"] == 100.0

        # Negative height is allowed (represents position below reference point)
        config_negative = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0},
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": -10.0},  # Negative is valid
            extra_reinf_diameter={},
            extra_reinf_ctc_distances={},
            has_extra_reinforcement=False,
            rebar_config={},
        )
        assert config_negative.reinf_heights["zone1"] == -10.0

        # Unrealistically low height
        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": 12.0},
                reinf_heights={"zone1": -2500.0},  # Below minimum
                extra_reinf_diameter={},
                extra_reinf_ctc_distances={},
                has_extra_reinforcement=False,
                rebar_config={},
            )

        error = exc_info.value
        assert "unrealistically low" in str(error)

        # Unrealistic height
        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": 12.0},
                reinf_heights={"zone1": 3000.0},  # Too large
                extra_reinf_diameter={},
                extra_reinf_ctc_distances={},
                has_extra_reinforcement=False,
                rebar_config={},
            )

        error = exc_info.value
        assert "Reinforcement height 3000.0mm in zone 'zone1' is unrealistic" in str(error)

    def test_extra_reinforcement_consistency_validation(self) -> None:
        """Test extra reinforcement consistency validation."""
        # Valid: extra reinforcement enabled with data
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0},
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": 50.0},
            extra_reinf_diameter={"zone1": 8.0},  # Has data
            extra_reinf_ctc_distances={"zone1": 300.0},  # Has data
            has_extra_reinforcement=True,
            rebar_config={},
        )
        assert config.has_extra_reinforcement is True

        # Valid: extra reinforcement disabled with no data
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0},
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": 50.0},
            extra_reinf_diameter={},  # No data
            extra_reinf_ctc_distances={},  # No data
            has_extra_reinforcement=False,
            rebar_config={},
        )
        assert config.has_extra_reinforcement is False

        # Invalid: extra reinforcement enabled but no diameter data
        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": 12.0},
                reinf_heights={"zone1": 50.0},
                extra_reinf_diameter={},  # Empty!
                extra_reinf_ctc_distances={"zone1": 300.0},
                has_extra_reinforcement=True,  # Enabled
                rebar_config={},
            )

        error = exc_info.value
        assert "Extra reinforcement is enabled but extra_reinf_diameter is empty" in str(error)

        # Invalid: extra reinforcement enabled but no distance data
        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": 12.0},
                reinf_heights={"zone1": 50.0},
                extra_reinf_diameter={"zone1": 8.0},
                extra_reinf_ctc_distances={},  # Empty!
                has_extra_reinforcement=True,  # Enabled
                rebar_config={},
            )

        error = exc_info.value
        assert "Extra reinforcement is enabled but extra_reinf_ctc_distances is empty" in str(error)

    def test_rebar_config_validation(self) -> None:
        """Test rebar configuration validation."""
        # Valid rebar config
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0},
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": 50.0},
            extra_reinf_diameter={},
            extra_reinf_ctc_distances={},
            has_extra_reinforcement=False,
            rebar_config={"material": "steel", "grade": "B500B", "cover": 40.0},
        )
        assert config.rebar_config["grade"] == "B500B"

        # Empty rebar config (valid)
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0},
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": 50.0},
            extra_reinf_diameter={},
            extra_reinf_ctc_distances={},
            has_extra_reinforcement=False,
            rebar_config={},  # Empty is valid
        )
        assert config.rebar_config == {}

        # Invalid grade
        with pytest.raises(ValidationError) as exc_info:
            ReinforcementConfigData(
                main_reinf_ctc_distances={"zone1": 150.0},
                main_reinf_diameters={"zone1": 12.0},
                reinf_heights={"zone1": 50.0},
                extra_reinf_diameter={},
                extra_reinf_ctc_distances={},
                has_extra_reinforcement=False,
                rebar_config={
                    "material": "steel",
                    "grade": "B400A",  # Invalid grade
                    "cover": 40.0,
                },
            )

        error = exc_info.value
        assert "Invalid reinforcement grade 'B400A'" in str(error)

        # Flexible config - missing keys are allowed (for IDEA integration compatibility)
        # IDEA integration uses different keys (heeft_bijlegwapening, zone_number) so strict validation removed
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0},
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": 50.0},
            extra_reinf_diameter={},
            extra_reinf_ctc_distances={},
            has_extra_reinforcement=False,
            rebar_config={
                "material": "steel"
                # Missing "grade" and "cover" - allowed for flexible structure
            },
        )
        assert config.rebar_config["material"] == "steel"

    def test_realistic_scenarios(self) -> None:
        """Test realistic reinforcement scenarios."""
        # Typical bridge reinforcement
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"main_span": 200.0, "side_span": 150.0},
            main_reinf_diameters={"main_span": 16.0, "side_span": 12.0},
            reinf_heights={"main_span": 100.0, "side_span": 75.0},
            extra_reinf_diameter={"main_span": 10.0},
            extra_reinf_ctc_distances={"main_span": 400.0},
            has_extra_reinforcement=True,
            rebar_config={"material": "steel", "grade": "B500B", "cover": 50.0},
        )

        assert config.main_reinf_diameters["main_span"] == 16.0
        assert config.main_reinf_ctc_distances["main_span"] == 200.0
        assert config.has_extra_reinforcement is True

        # Simple reinforcement without extra
        config = ReinforcementConfigData(
            main_reinf_ctc_distances={"zone1": 150.0},
            main_reinf_diameters={"zone1": 12.0},
            reinf_heights={"zone1": 50.0},
            extra_reinf_diameter={},
            extra_reinf_ctc_distances={},
            has_extra_reinforcement=False,
            rebar_config={},
        )

        assert config.has_extra_reinforcement is False
        assert config.extra_reinf_diameter == {}
