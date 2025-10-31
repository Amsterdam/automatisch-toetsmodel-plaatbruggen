"""
Test cases for QR reinforcement materials from GBV 1950 and 1962.

This test module ensures that the QR materials from both CSV files
are properly integrated into the IDEA material mapping system.
"""

import pytest

from src.integrations.idea_integration.idea_material_generator import get_reinforcement_material_from_csv
from src.integrations.idea_integration.idea_material_mapping import (
    get_all_supported_reinforcement_materials,
    is_historical_reinforcement_material,
)


class TestQRReinforcementMaterials:
    """Test cases for QR reinforcement materials from GBV CSV files."""

    @pytest.mark.parametrize("material", ["QR22", "QR24", "QR30", "QR36", "QR42"])
    def test_gbv_1950_materials_recognized_as_historical(self, material: str) -> None:
        """Test that GBV 1950 QR materials are recognized as historical."""
        assert is_historical_reinforcement_material(material), f"QR material {material} from GBV 1950 should be historical"

    @pytest.mark.parametrize("material", ["QR32", "QR40", "QR48"])
    def test_gbv_1962_materials_recognized_as_historical(self, material: str) -> None:
        """Test that GBV 1962 QR materials are recognized as historical."""
        assert is_historical_reinforcement_material(material), f"QR material {material} from GBV 1962 should be historical"

    @pytest.mark.parametrize(
        ("material", "expected_fyk"),
        [
            ("QR22", 220.0),
            ("QR24", 240.0),
            ("QR30", 300.0),
            ("QR36", 360.0),
            ("QR42", 420.0),
            ("QR32", 320.0),
            ("QR40", 400.0),
            ("QR48", 480.0),
        ],
    )
    def test_qr_materials_can_be_loaded_from_csv(self, material: str, expected_fyk: float) -> None:
        """Test that QR materials can be loaded from CSV with correct properties."""
        material_data = get_reinforcement_material_from_csv(material)

        assert isinstance(material_data, dict), f"Material data for {material} should be a dictionary"
        assert "Fyk" in material_data, f"Material {material} should have Fyk property"
        assert material_data["Fyk"] == expected_fyk, f"Material {material} should have Fyk={expected_fyk} MPa"

    def test_qr_materials_included_in_supported_materials(self) -> None:
        """Test that all QR materials (with suffixes) are included in the supported materials list."""
        all_materials = get_all_supported_reinforcement_materials()

        # Test suffixed materials (as they appear in CSV)
        gbv_1950_materials = ["QR22_GBV1950", "QR24_GBV1950", "QR30_GBV1950", "QR36_GBV1950", "QR42_GBV1950"]
        gbv_1962_materials = ["QR32_GBV1962", "QR40_GBV1962", "QR48_GBV1962"]

        for material in gbv_1950_materials + gbv_1962_materials:
            assert material in all_materials, f"QR material {material} should be in supported materials list"
            assert all_materials[material] == "historical", f"QR material {material} should be marked as historical"

    def test_total_historical_material_count(self) -> None:
        """Test that the total number of historical materials includes all suffixed materials from CSV."""
        all_materials = get_all_supported_reinforcement_materials()
        historical_materials = [name for name, mat_type in all_materials.items() if mat_type == "historical"]

        # Should have exactly 18 historical materials (from Reinforcement_All.csv)
        assert len(historical_materials) == 18, f"Should have exactly 18 historical materials, got {len(historical_materials)}"

        # Verify specific QR materials are present (suffixed versions only)
        qr_materials = [mat for mat in historical_materials if mat.startswith("QR")]
        # Should have 10 QR materials with suffixes: 5 from GBV1950 + 5 from GBV1962 (QR22 and QR24 appear in both)
        assert len(qr_materials) == 10, f"Should have exactly 10 QR materials (with suffixes), got {len(qr_materials)}: {qr_materials}"

        # Check that suffixed QR materials are present (not base names)
        suffixed_qr_materials = [
            # GBV 1950
            "QR22_GBV1950",
            "QR24_GBV1950",
            "QR30_GBV1950",
            "QR36_GBV1950",
            "QR42_GBV1950",
            # GBV 1962 (QR22 and QR24 also appear here)
            "QR22_GBV1962",
            "QR24_GBV1962",
            "QR32_GBV1962",
            "QR40_GBV1962",
            "QR48_GBV1962",
        ]
        for material in suffixed_qr_materials:
            assert material in all_materials, f"Suffixed QR material {material} should be in supported materials"
