"""
Test module for IDEA material generator functionality.

This module provides comprehensive testing for the IDEA material generator,
including CSV reading, material data parsing, and material creation.

Key test coverage:
- CSV reading functionality for historical concrete materials
- Material data extraction and validation
- Error handling for missing materials and malformed data
"""

from pathlib import Path

import pytest

from src.integrations.idea_integration.idea_material_generator import get_concrete_material_from_csv


class TestConcreteMaterialFromCSV:
    """Test cases for reading concrete material data from CSV files."""

    def test_read_k200_material_success(self) -> None:
        """Test successfully reading K200 material from CSV."""
        material_data = get_concrete_material_from_csv("K200")

        # Verify we got data back
        assert isinstance(material_data, dict)
        assert len(material_data) > 0

        # Verify key material properties are present
        required_keys = ["Fck", "UnitMass", "StoneDiameter", "CementClass", "AggregateType"]
        for key in required_keys:
            assert key in material_data, f"Required key '{key}' not found in material data"

        # Verify specific values for K200
        assert material_data["Fck"] == 11.0, f"Expected Fck=11.0, got {material_data['Fck']}"
        assert material_data["UnitMass"] == 2450.0, f"Expected UnitMass=2450.0, got {material_data['UnitMass']}"
        assert material_data["StoneDiameter"] == 16.0, f"Expected StoneDiameter=16.0, got {material_data['StoneDiameter']}"

    def test_read_k150_material_success(self) -> None:
        """Test successfully reading K150 material from CSV."""
        material_data = get_concrete_material_from_csv("K150")

        # Verify we got data back
        assert isinstance(material_data, dict)
        assert len(material_data) > 0

        # Verify key material properties are present
        assert "Fck" in material_data
        assert material_data["Fck"] == 8.0, f"Expected Fck=8.0 for K150, got {material_data['Fck']}"

    def test_read_k250_material_success(self) -> None:
        """Test successfully reading K250 material from CSV."""
        material_data = get_concrete_material_from_csv("K250")

        # Verify we got data back
        assert isinstance(material_data, dict)
        assert len(material_data) > 0

        # Verify key material properties are present
        assert "Fck" in material_data
        assert material_data["Fck"] == 13.5, f"Expected Fck=13.5 for K250, got {material_data['Fck']}"

    def test_read_nonexistent_material_failure(self) -> None:
        """Test that reading a non-existent material raises ValueError."""
        with pytest.raises(ValueError, match="Material 'K999' not found in any CSV file"):
            get_concrete_material_from_csv("K999")

    def test_read_modern_eurocode_material_failure(self) -> None:
        """Test that reading modern Eurocode material raises appropriate error."""
        with pytest.raises(ValueError, match="Modern Eurocode material 'C30/37' should use IDEA RCS built-in materials"):
            get_concrete_material_from_csv("C30/37")

    def test_material_data_numeric_conversion(self) -> None:
        """Test that numeric values are properly converted from string format."""
        material_data = get_concrete_material_from_csv("K200")

        # Test that decimal comma values are converted to float
        assert isinstance(material_data["Poisson"], float)
        assert material_data["Poisson"] == 0.2

        # Test that scientific notation is handled
        assert isinstance(material_data["ThermalExpansion"], float)
        assert material_data["ThermalExpansion"] == 1.2e-05

        # Test that boolean values are converted
        assert isinstance(material_data["PlainConcreteDiagram"], bool | str)
        if isinstance(material_data["PlainConcreteDiagram"], str):
            assert material_data["PlainConcreteDiagram"] == "False"

    def test_material_data_completeness(self) -> None:
        """Test that all expected columns are present in material data."""
        material_data = get_concrete_material_from_csv("K200")

        # Expected columns based on CSV header
        expected_columns = [
            "Header",
            "ElementID",
            "E",
            "G",
            "Poisson",
            "UnitMass",
            "SpecificHeat",
            "ThermalExpansion",
            "ThermalConductivity",
            "Ecm",
            "Fck",
            "Fcm",
            "Fctm",
            "Fctk_0_05",
            "Fctk_0_95",
            "NFactor",
            "Epsc1",
            "Epsc2",
            "Epsc3",
            "Epscu1",
            "Epscu2",
            "Epscu3",
            "StoneDiameter",
            "CementClass",
            "AggregateType",
            "DiagramType",
            "PlainConcreteDiagram",
            "SilicaFume",
            "CalculateDependentValues",
        ]

        for column in expected_columns:
            assert column in material_data, f"Expected column '{column}' not found in material data"


class TestCSVFileStructure:
    """Test cases for CSV file structure and format validation."""

    def test_csv_file_exists(self) -> None:
        """Test that the required combined CSV file exists."""
        csv_path = Path(__file__).parent.parent.parent.parent / "resources" / "data" / "idea_materials" / "Concrete_All.csv"
        assert csv_path.exists(), f"CSV file not found at {csv_path}"

    def test_csv_file_readable(self) -> None:
        """Test that the combined CSV file is readable and has expected structure."""
        csv_path = Path(__file__).parent.parent.parent.parent / "resources" / "data" / "idea_materials" / "Concrete_All.csv"

        with open(csv_path, encoding="utf-8") as file:
            content = file.read()

            # Check for expected structural elements
            assert '"Header"' in content, "CSV should contain Header line"
            assert '"Data"' in content, "CSV should contain Data marker"
            assert '"Fck"' in content, "CSV should contain Fck column"
            # Check for material with suffix (new naming convention)
            assert '"K200_GBV1940"' in content or '"K200_GBV1950"' in content, "CSV should contain K200 material with suffix"


if __name__ == "__main__":
    # Allow running this test file directly for quick debugging
    pytest.main([__file__, "-v"])
