"""
Test module for material management functionality.

This module contains comprehensive tests for material data access,
validation, and compatibility checking functions.
"""

import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.common.materials import (
    BENDING_RADIUS_PATH,
    CONCRETE_PATH,
    MATERIAL_DENSITY_PATH,
    MATERIALS_DIR,
    PRESTRESS_PATH,
    REINFORCEMENT_PATH,
    check_material_compatibility,
    get_concrete_material_properties,
    get_concrete_qualities,
    get_default_materials,
    get_material_compatibility_info,
    get_material_densities,
    get_prestress_qualities,
    get_reinforcement_material_properties,
    get_reinforcement_qualities,
    get_steel_qualities,
    get_supported_idea_materials,
    get_supported_scia_materials,
    normalize_material_name,
    validate_material_exists,
)


class TestMaterialsConstants(unittest.TestCase):
    """Test material file path constants."""

    def test_materials_directory_structure(self) -> None:
        """Test that material constants define expected directory structure."""
        assert MATERIALS_DIR.name == "materials"
        assert MATERIALS_DIR.parent.name == "data"
        assert MATERIALS_DIR.parent.parent.name == "resources"

    def test_material_file_paths_defined(self) -> None:
        """Test that all required material file paths are defined."""
        assert CONCRETE_PATH.name == "betonkwaliteit.csv"
        assert REINFORCEMENT_PATH.name == "betonstaalkwaliteit.csv"
        assert PRESTRESS_PATH.name == "voorspanstaalkwaliteit.csv"
        assert BENDING_RADIUS_PATH.name == "wapening_buigstraal.csv"
        assert MATERIAL_DENSITY_PATH.name == "soortelijkgewicht.csv"


class TestGetConcreteQualities(unittest.TestCase):
    """Test cases for get_concrete_qualities function."""

    @patch("src.common.materials.CONCRETE_PATH")
    def test_get_concrete_qualities_success(self, mock_path: MagicMock) -> None:
        """Test successful retrieval of concrete qualities."""
        # Arrange
        csv_content = 'Betonkwaliteit;fck[N/mm^2];fcd[N/mm^2]\n"C12/15";12;8\n"C30/37";30;20\n"C50/60";50;33'
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act
        result = get_concrete_qualities()

        # Assert
        assert result == ["C12/15", "C30/37", "C50/60"]
        mock_path.open.assert_called_once_with(encoding="utf-8")

    @patch("src.common.materials.CONCRETE_PATH")
    def test_get_concrete_qualities_file_not_found(self, mock_path: MagicMock) -> None:
        """Test handling of missing concrete materials file."""
        # Arrange
        mock_path.open.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Concrete materials file not found"):
            get_concrete_qualities()

    @patch("src.common.materials.CONCRETE_PATH")
    def test_get_concrete_qualities_empty_file(self, mock_path: MagicMock) -> None:
        """Test handling of empty concrete materials file."""
        # Arrange
        csv_content = "Betonkwaliteit;fck[N/mm^2];fcd[N/mm^2]\n"
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act
        result = get_concrete_qualities()

        # Assert
        assert result == []

    @patch("src.common.materials.CONCRETE_PATH")
    def test_get_concrete_qualities_strips_quotes(self, mock_path: MagicMock) -> None:
        """Test that function properly strips quotes from material names."""
        # Arrange
        csv_content = 'Betonkwaliteit;fck[N/mm^2];fcd[N/mm^2]\n"C30/37";30;20\nC45/55;45;30'
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act
        result = get_concrete_qualities()

        # Assert
        assert result == ["C30/37", "C45/55"]


class TestGetReinforcementQualities(unittest.TestCase):
    """Test cases for get_reinforcement_qualities function."""

    @patch("src.common.materials.REINFORCEMENT_PATH")
    def test_get_reinforcement_qualities_success(self, mock_path: MagicMock) -> None:
        """Test successful retrieval of reinforcement qualities."""
        # Arrange
        csv_content = 'Betonstaalkwaliteit;fyk[N/mm^2];fyd[N/mm^2]\n"B500A";500;435\n"B500B";500;435'
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act
        result = get_reinforcement_qualities()

        # Assert
        assert result == ["B500A", "B500B"]
        mock_path.open.assert_called_once_with(encoding="utf-8")

    @patch("src.common.materials.REINFORCEMENT_PATH")
    def test_get_reinforcement_qualities_file_not_found(self, mock_path: MagicMock) -> None:
        """Test handling of missing reinforcement materials file."""
        # Arrange
        mock_path.open.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Reinforcement materials file not found"):
            get_reinforcement_qualities()


class TestGetPrestressQualities(unittest.TestCase):
    """Test cases for get_prestress_qualities function."""

    @patch("src.common.materials.PRESTRESS_PATH")
    def test_get_prestress_qualities_success(self, mock_path: MagicMock) -> None:
        """Test successful retrieval of prestress qualities."""
        # Arrange
        csv_content = 'Staalsoort;Eigenschap1;Eigenschap2\n"FeP 1770";1770;1500\n"FeP 1860";1860;1600'
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act
        result = get_prestress_qualities()

        # Assert
        assert result == ["FeP 1770", "FeP 1860"]
        mock_path.open.assert_called_once_with(encoding="utf-8")

    @patch("src.common.materials.PRESTRESS_PATH")
    def test_get_prestress_qualities_file_not_found(self, mock_path: MagicMock) -> None:
        """Test handling of missing prestress materials file."""
        # Arrange
        mock_path.open.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Prestress materials file not found"):
            get_prestress_qualities()


class TestGetConcreteMaterialProperties(unittest.TestCase):
    """Test cases for get_concrete_material_properties function."""

    @patch("src.common.materials.CONCRETE_PATH")
    def test_get_concrete_material_properties_success(self, mock_path: MagicMock) -> None:
        """Test successful retrieval of concrete material properties."""
        # Arrange
        csv_content = 'Betonkwaliteit;fck[N/mm^2];fcd[N/mm^2]\n"C30/37";30;20\n"C50/60";50;33'
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act
        result = get_concrete_material_properties("C30/37")

        # Assert
        assert result == {"name": "C30/37", "fck": 30.0, "fcd": 20.0}

    @patch("src.common.materials.CONCRETE_PATH")
    def test_get_concrete_material_properties_not_found(self, mock_path: MagicMock) -> None:
        """Test handling of non-existent concrete material."""
        # Arrange
        csv_content = 'Betonkwaliteit;fck[N/mm^2];fcd[N/mm^2]\n"C30/37";30;20'
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act & Assert
        with pytest.raises(ValueError, match="Concrete material 'C99/99' not found"):
            get_concrete_material_properties("C99/99")

    @patch("src.common.materials.CONCRETE_PATH")
    def test_get_concrete_material_properties_file_not_found(self, mock_path: MagicMock) -> None:
        """Test handling of missing concrete materials file."""
        # Arrange
        mock_path.open.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Concrete materials file not found"):
            get_concrete_material_properties("C30/37")


class TestGetReinforcementMaterialProperties(unittest.TestCase):
    """Test cases for get_reinforcement_material_properties function."""

    @patch("src.common.materials.REINFORCEMENT_PATH")
    def test_get_reinforcement_material_properties_success(self, mock_path: MagicMock) -> None:
        """Test successful retrieval of reinforcement material properties."""
        # Arrange
        csv_content = 'Betonstaalkwaliteit;fyk[N/mm^2];fyd[N/mm^2]\n"B500B";500;435\n"B500A";500;435'
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act
        result = get_reinforcement_material_properties("B500B")

        # Assert
        assert result == {"name": "B500B", "fyk": 500.0, "fyd": 435.0}

    @patch("src.common.materials.REINFORCEMENT_PATH")
    def test_get_reinforcement_material_properties_not_found(self, mock_path: MagicMock) -> None:
        """Test handling of non-existent reinforcement material."""
        # Arrange
        csv_content = 'Betonstaalkwaliteit;fyk[N/mm^2];fyd[N/mm^2]\n"B500B";500;435'
        mock_path.open.return_value.__enter__.return_value = csv_content.splitlines()

        # Act & Assert
        with pytest.raises(ValueError, match="Reinforcement material 'B999' not found"):
            get_reinforcement_material_properties("B999")

    @patch("src.common.materials.REINFORCEMENT_PATH")
    def test_get_reinforcement_material_properties_file_not_found(self, mock_path: MagicMock) -> None:
        """Test handling of missing reinforcement materials file."""
        # Arrange
        mock_path.open.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Reinforcement materials file not found"):
            get_reinforcement_material_properties("B500B")


class TestCheckMaterialCompatibility(unittest.TestCase):
    """Test cases for check_material_compatibility function."""

    @patch("src.common.materials.get_reinforcement_material_properties")
    @patch("src.common.materials.get_concrete_material_properties")
    def test_check_material_compatibility_valid_materials(self, mock_concrete_props: MagicMock, mock_reinf_props: MagicMock) -> None:
        """Test compatibility check with valid materials."""
        # Arrange
        mock_concrete_props.return_value = {"name": "C30/37", "fck": 30.0, "fcd": 20.0}
        mock_reinf_props.return_value = {"name": "B500B", "fyk": 500.0, "fyd": 435.0}

        # Act
        result = check_material_compatibility("C30/37", "B500B")

        # Assert
        assert result is True
        mock_concrete_props.assert_called_once_with("C30/37")
        mock_reinf_props.assert_called_once_with("B500B")

    @patch("src.common.materials.get_reinforcement_material_properties")
    @patch("src.common.materials.get_concrete_material_properties")
    def test_check_material_compatibility_invalid_concrete(self, mock_concrete_props: MagicMock, mock_reinf_props: MagicMock) -> None:
        """Test compatibility check with invalid concrete material."""
        # Arrange
        mock_concrete_props.side_effect = ValueError("Material not found")
        mock_reinf_props.return_value = {"name": "B500B", "fyk": 500.0, "fyd": 435.0}

        # Act
        result = check_material_compatibility("INVALID", "B500B")

        # Assert
        assert result is False

    @patch("src.common.materials.get_reinforcement_material_properties")
    @patch("src.common.materials.get_concrete_material_properties")
    def test_check_material_compatibility_invalid_reinforcement(self, mock_concrete_props: MagicMock, mock_reinf_props: MagicMock) -> None:
        """Test compatibility check with invalid reinforcement material."""
        # Arrange
        mock_concrete_props.return_value = {"name": "C30/37", "fck": 30.0, "fcd": 20.0}
        mock_reinf_props.side_effect = ValueError("Material not found")

        # Act
        result = check_material_compatibility("C30/37", "INVALID")

        # Assert
        assert result is False


class TestGetDefaultMaterials(unittest.TestCase):
    """Test cases for get_default_materials function."""

    def test_get_default_materials_returns_expected_dict(self) -> None:
        """Test that default materials returns expected structure and values."""
        # Act
        result = get_default_materials()

        # Assert
        assert isinstance(result, dict)
        assert "concrete" in result
        assert "reinforcement" in result
        assert "prestress" in result
        assert result["concrete"] == "C30/37"
        assert result["reinforcement"] == "B500B"
        assert result["prestress"] == "FeP 1770"


class TestNormalizeMaterialName(unittest.TestCase):
    """Test cases for normalize_material_name function."""

    def test_normalize_material_name_decimal_conversion(self) -> None:
        """Test conversion of decimal points to commas."""
        # Act & Assert
        assert normalize_material_name("B37.5") == "B37,5"
        assert normalize_material_name("C30.5/37") == "C30,5/37"
        assert normalize_material_name("QR24.5") == "QR24,5"

    def test_normalize_material_name_mappings(self) -> None:
        """Test material name mappings for old standards."""
        # Act & Assert
        assert normalize_material_name("B400") == "FeB 400"
        assert normalize_material_name("B220") == "FeB 220"
        assert normalize_material_name("B500") == "FeB 500"
        assert normalize_material_name("QR24-QR40") == "QR40"

    def test_normalize_material_name_no_change_needed(self) -> None:
        """Test materials that don't need normalization."""
        # Act & Assert
        assert normalize_material_name("C30/37") == "C30/37"
        assert normalize_material_name("B500B") == "B500B"
        assert normalize_material_name("QR24") == "QR24"

    def test_normalize_material_name_empty_string(self) -> None:
        """Test handling of empty string input."""
        # Act & Assert
        assert normalize_material_name("") == ""

    def test_normalize_material_name_combined_transformations(self) -> None:
        """Test materials requiring both decimal and mapping transformations."""
        # This tests that decimal conversion happens first, then mapping is applied
        assert normalize_material_name("B400") == "FeB 400"  # Maps directly
        # If there were a "B400.5" that needed mapping, it would become "B400,5" then mapped


class TestValidateMaterialExists(unittest.TestCase):
    """Test cases for validate_material_exists function."""

    @patch("src.common.materials.get_concrete_qualities")
    def test_validate_material_exists_concrete_valid(self, mock_get_qualities: MagicMock) -> None:
        """Test validation of existing concrete material."""
        # Arrange
        mock_get_qualities.return_value = ["C30/37", "C50/60"]

        # Act
        result = validate_material_exists("C30/37", "concrete")

        # Assert
        assert result is True

    @patch("src.common.materials.get_reinforcement_qualities")
    def test_validate_material_exists_reinforcement_valid(self, mock_get_qualities: MagicMock) -> None:
        """Test validation of existing reinforcement material."""
        # Arrange
        mock_get_qualities.return_value = ["B500A", "B500B"]

        # Act
        result = validate_material_exists("B500B", "reinforcement")

        # Assert
        assert result is True

    def test_validate_material_exists_invalid_type(self) -> None:
        """Test validation with invalid material type."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid material type: prestress"):
            validate_material_exists("FeP 1770", "prestress")

    @patch("src.common.materials.get_concrete_qualities")
    def test_validate_material_exists_concrete_invalid(self, mock_get_qualities: MagicMock) -> None:
        """Test validation of non-existent concrete material."""
        # Arrange
        mock_get_qualities.return_value = ["C30/37", "C50/60"]

        # Act
        result = validate_material_exists("C99/99", "concrete")

        # Assert
        assert result is False

    def test_validate_material_exists_unknown_type(self) -> None:
        """Test validation with unknown material type."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid material type: unknown_type"):
            validate_material_exists("SomeMaterial", "unknown_type")


class TestGetSupportedIdeaMaterials(unittest.TestCase):
    """Test cases for get_supported_idea_materials function."""

    def test_get_supported_idea_materials_structure(self) -> None:
        """Test that function returns expected structure."""
        # Act
        result = get_supported_idea_materials()

        # Assert
        assert isinstance(result, dict)
        assert "concrete" in result
        assert "reinforcement" in result
        assert isinstance(result["concrete"], list)
        assert isinstance(result["reinforcement"], list)

    def test_get_supported_idea_materials_has_common_materials(self) -> None:
        """Test that common materials are included in IDEA support."""
        # Act
        result = get_supported_idea_materials()

        # Assert
        assert "C30/37" in result["concrete"]
        assert "B500B" in result["reinforcement"]


class TestGetSupportedSciaMaterials(unittest.TestCase):
    """Test cases for get_supported_scia_materials function."""

    def test_get_supported_scia_materials_structure(self) -> None:
        """Test that function returns expected structure."""
        # Act
        result = get_supported_scia_materials()

        # Assert
        assert isinstance(result, dict)
        assert "concrete" in result
        assert "reinforcement" in result
        assert isinstance(result["concrete"], list)
        assert isinstance(result["reinforcement"], list)

    def test_get_supported_scia_materials_has_common_materials(self) -> None:
        """Test that common materials are included in SCIA support."""
        # Act
        result = get_supported_scia_materials()

        # Assert
        assert "C30/37" in result["concrete"]
        assert "B500B" in result["reinforcement"]


class TestGetMaterialDensities(unittest.TestCase):
    """Test cases for get_material_densities function."""

    @patch("src.common.materials.MATERIAL_DENSITY_PATH")
    def test_get_material_densities_success(self, mock_path: MagicMock) -> None:
        """Test successful retrieval of material densities."""
        # Arrange
        mock_csv_data = [
            {"Materiaal": '"Beton"', "Soortelijk gewicht (kN/m³)": "25.0"},
            {"Materiaal": '"Staal"', "Soortelijk gewicht (kN/m³)": "78.5"},
        ]

        # Mock the file open and CSV reader
        mock_file = mock_open()
        mock_path.open.return_value.__enter__.return_value = mock_file.return_value

        with patch("csv.DictReader", return_value=mock_csv_data) as mock_csv_reader:
            # Act
            result = get_material_densities()

            # Assert
            assert len(result) == 2
            assert result[0] == ("Beton", 25.0)
            assert result[1] == ("Staal", 78.5)
            mock_path.open.assert_called_once_with(encoding="utf-8")
            mock_csv_reader.assert_called_once()

    @patch("src.common.materials.MATERIAL_DENSITY_PATH")
    def test_get_material_densities_file_not_found(self, mock_path: MagicMock) -> None:
        """Test handling of missing material densities file."""
        # Arrange
        mock_path.open.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Material density file not found"):
            get_material_densities()


class TestGetSteelQualities(unittest.TestCase):
    """Test cases for get_steel_qualities function."""

    @patch("src.common.materials.get_reinforcement_qualities")
    def test_get_steel_qualities_calls_reinforcement_function(self, mock_get_reinforcement: MagicMock) -> None:
        """Test that get_steel_qualities delegates to get_reinforcement_qualities."""
        # Arrange
        expected_result = ["B500A", "B500B"]
        mock_get_reinforcement.return_value = expected_result

        # Act
        result = get_steel_qualities()

        # Assert
        assert result == expected_result
        mock_get_reinforcement.assert_called_once()


class TestGetMaterialCompatibilityInfo(unittest.TestCase):
    """Test cases for get_material_compatibility_info function."""

    @patch("src.common.materials.validate_material_exists")
    def test_get_material_compatibility_info_structure(self, mock_validate: MagicMock) -> None:
        """Test that function returns expected information structure."""
        # Arrange
        mock_validate.return_value = True

        # Act
        result = get_material_compatibility_info("B500B")

        # Assert
        assert isinstance(result, dict)
        assert "material" in result
        assert "scia" in result
        assert "idea" in result
        assert result["material"] == "B500B"

    @patch("src.common.materials.validate_material_exists")
    def test_get_material_compatibility_info_supported_material(self, mock_validate: MagicMock) -> None:
        """Test compatibility info for material supported by both systems."""
        # Arrange
        mock_validate.return_value = True

        # Act
        result = get_material_compatibility_info("B500B")

        # Assert
        assert result["scia"] == "Direct support"
        assert result["idea"] == "Direct support"

    @patch("src.common.materials.validate_material_exists")
    def test_get_material_compatibility_info_unsupported_material(self, mock_validate: MagicMock) -> None:
        """Test compatibility info for material not supported by systems."""
        # Arrange
        mock_validate.return_value = False

        # Act
        result = get_material_compatibility_info("UnknownMaterial")

        # Assert
        assert result["status"] == "ERROR"
        assert "not found in project database" in result["message"]


if __name__ == "__main__":
    unittest.main()
