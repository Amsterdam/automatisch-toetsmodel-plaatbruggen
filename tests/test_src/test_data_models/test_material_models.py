"""Tests for material Pydantic models."""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.data_models.material_models import MaterialConfig


class TestMaterialConfig(unittest.TestCase):
    """Test cases for MaterialConfig Pydantic model."""

    @patch("src.data_models.material_models.get_prestress_qualities")
    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_valid_config_creation(self, mock_concrete: MagicMock, mock_reinforcement: MagicMock, mock_prestress: MagicMock) -> None:
        """Test creating valid material configuration."""
        # Arrange
        mock_concrete.return_value = ["C30/37", "C50/60"]
        mock_reinforcement.return_value = ["B500A", "B500B"]
        mock_prestress.return_value = ["FeP 1770", "FeP 1860"]

        valid_data = {"concrete_type": "C30/37", "reinforcement_type": "B500B", "prestress_type": "FeP 1770"}

        # Act
        config = MaterialConfig(**valid_data)

        # Assert
        assert config.concrete_type == "C30/37"
        assert config.reinforcement_type == "B500B"
        assert config.prestress_type == "FeP 1770"

    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_valid_config_without_prestress(self, mock_concrete: MagicMock, mock_reinforcement: MagicMock) -> None:
        """Test creating valid material configuration without prestressing steel."""
        # Arrange
        mock_concrete.return_value = ["C30/37", "C50/60"]
        mock_reinforcement.return_value = ["B500A", "B500B"]

        valid_data = {"concrete_type": "C30/37", "reinforcement_type": "B500B"}

        # Act
        config = MaterialConfig(**valid_data)

        # Assert
        assert config.concrete_type == "C30/37"
        assert config.reinforcement_type == "B500B"
        assert config.prestress_type is None

    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_from_params_dict_method(self, mock_concrete: MagicMock, mock_reinforcement: MagicMock) -> None:
        """Test creating config from VIKTOR params structure."""
        # Arrange
        mock_concrete.return_value = ["C30/37", "C50/60"]
        mock_reinforcement.return_value = ["B500A", "B500B"]

        params = {"concrete_type": "C30/37", "reinforcement_type": "B500B", "prestress_type": None}

        # Act
        config = MaterialConfig.from_params_dict(params)

        # Assert
        assert config.concrete_type == "C30/37"
        assert config.reinforcement_type == "B500B"
        assert config.prestress_type is None

    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_invalid_concrete_type_rejected(self, mock_concrete: MagicMock) -> None:
        """Test that invalid concrete types are rejected."""
        # Arrange
        mock_concrete.return_value = ["C30/37", "C50/60"]

        invalid_data = {
            "concrete_type": "C99/99",  # Invalid
            "reinforcement_type": "B500B",
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            MaterialConfig(**invalid_data)

        error = exc_info.value
        assert "concrete_type" in str(error)
        assert "not found in database" in str(error)

    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_invalid_reinforcement_type_rejected(self, mock_concrete: MagicMock, mock_reinforcement: MagicMock) -> None:
        """Test that invalid reinforcement types are rejected."""
        # Arrange
        mock_concrete.return_value = ["C30/37", "C50/60"]
        mock_reinforcement.return_value = ["B500A", "B500B"]

        invalid_data = {
            "concrete_type": "C30/37",
            "reinforcement_type": "B999",  # Invalid
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            MaterialConfig(**invalid_data)

        error = exc_info.value
        assert "reinforcement_type" in str(error)
        assert "not found in database" in str(error)

    @patch("src.data_models.material_models.get_prestress_qualities")
    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_invalid_prestress_type_rejected(self, mock_concrete: MagicMock, mock_reinforcement: MagicMock, mock_prestress: MagicMock) -> None:
        """Test that invalid prestressing steel types are rejected."""
        # Arrange
        mock_concrete.return_value = ["C30/37", "C50/60"]
        mock_reinforcement.return_value = ["B500A", "B500B"]
        mock_prestress.return_value = ["FeP 1770", "FeP 1860"]

        invalid_data = {
            "concrete_type": "C30/37",
            "reinforcement_type": "B500B",
            "prestress_type": "FeP 9999",  # Invalid
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            MaterialConfig(**invalid_data)

        error = exc_info.value
        assert "prestress_type" in str(error)
        assert "not found in database" in str(error)

    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_concrete_validation_shows_available_options(self, mock_concrete: MagicMock) -> None:
        """Test that concrete validation error shows available options."""
        # Arrange
        mock_concrete.return_value = ["C12/15", "C16/20", "C20/25", "C25/30", "C30/37", "C35/45"]

        invalid_data = {"concrete_type": "C99/99", "reinforcement_type": "B500B"}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            MaterialConfig(**invalid_data)

        error_message = str(exc_info.value)
        assert "Available: C12/15, C16/20, C20/25, C25/30, C30/37..." in error_message

    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_reinforcement_validation_shows_available_options(self, mock_concrete: MagicMock, mock_reinforcement: MagicMock) -> None:
        """Test that reinforcement validation error shows available options."""
        # Arrange
        mock_concrete.return_value = ["C30/37"]
        mock_reinforcement.return_value = ["B500A", "B500B", "B500C", "FeB 400", "FeB 500"]

        invalid_data = {"concrete_type": "C30/37", "reinforcement_type": "B999"}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            MaterialConfig(**invalid_data)

        error_message = str(exc_info.value)
        assert "Available: B500A, B500B, B500C, FeB 400, FeB 500..." in error_message

    @patch("src.data_models.material_models.get_prestress_qualities")
    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_prestress_validation_shows_available_options(
        self, mock_concrete: MagicMock, mock_reinforcement: MagicMock, mock_prestress: MagicMock
    ) -> None:
        """Test that prestress validation error shows available options."""
        # Arrange
        mock_concrete.return_value = ["C30/37"]
        mock_reinforcement.return_value = ["B500B"]
        mock_prestress.return_value = ["FeP 1770", "FeP 1860", "FeP 1960"]

        invalid_data = {"concrete_type": "C30/37", "reinforcement_type": "B500B", "prestress_type": "FeP 9999"}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            MaterialConfig(**invalid_data)

        error_message = str(exc_info.value)
        assert "Available: FeP 1770, FeP 1860, FeP 1960..." in error_message

    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_missing_required_fields_rejected(self, mock_concrete: MagicMock, mock_reinforcement: MagicMock) -> None:
        """Test that missing required fields are rejected."""
        # Arrange
        mock_concrete.return_value = ["C30/37"]
        mock_reinforcement.return_value = ["B500B"]

        # Act & Assert - Missing concrete_type
        with pytest.raises(ValidationError) as exc_info:
            MaterialConfig(reinforcement_type="B500B", prestress_type=None)  # type: ignore[call-arg]
        assert "concrete_type" in str(exc_info.value)

        # Act & Assert - Missing reinforcement_type
        with pytest.raises(ValidationError) as exc_info:
            MaterialConfig(concrete_type="C30/37", prestress_type=None)  # type: ignore[call-arg]
        assert "reinforcement_type" in str(exc_info.value)

    @patch("src.data_models.material_models.get_reinforcement_qualities")
    @patch("src.data_models.material_models.get_concrete_qualities")
    def test_validate_assignment_enabled(self, mock_concrete: MagicMock, mock_reinforcement: MagicMock) -> None:
        """Test that validate_assignment is enabled for runtime validation."""
        # Arrange
        mock_concrete.return_value = ["C30/37", "C50/60"]
        mock_reinforcement.return_value = ["B500A", "B500B"]

        config = MaterialConfig(concrete_type="C30/37", reinforcement_type="B500B", prestress_type=None)

        # Act & Assert - Should validate on assignment
        with pytest.raises(ValidationError):
            config.concrete_type = "C99/99"  # Invalid concrete type


if __name__ == "__main__":
    unittest.main()
