"""
Tests for IDEA integration enum bridge pattern.

This module tests the enum bridge pattern that allows src/ layer to use enums
that resolve to SDK types when available, or string fallbacks when not.
"""

import pytest

from src.integrations.idea_integration.idea_enums import (
    BarSurface,
    ConcAggregateType,
    ConcCementClass,
    ConcDiagramType,
    ConcreteMaterial,
    ReinfDiagramType,
    ReinfFabrication,
    ReinforcementClass,
    ReinforcementMaterial,
    ReinfType,
)


class TestEnumBridgePattern:
    """Test the enum bridge pattern for SDK integration."""

    def test_reinforcement_class_enum_values(self) -> None:
        """Test ReinforcementClass enum has correct values."""
        # Test all enum members exist
        assert hasattr(ReinforcementClass, "A")
        assert hasattr(ReinforcementClass, "B")
        assert hasattr(ReinforcementClass, "C")

        # Test values are accessible
        assert ReinforcementClass.A.value is not None
        assert ReinforcementClass.B.value is not None
        assert ReinforcementClass.C.value is not None

    def test_bar_surface_enum_values(self) -> None:
        """Test BarSurface enum has correct values."""
        assert hasattr(BarSurface, "SMOOTH")
        assert hasattr(BarSurface, "RIBBED")

        assert BarSurface.SMOOTH.value is not None
        assert BarSurface.RIBBED.value is not None

    def test_reinf_diagram_type_enum_values(self) -> None:
        """Test ReinfDiagramType enum has correct values."""
        assert hasattr(ReinfDiagramType, "BILINEAR_NOT_INCLINED")
        assert hasattr(ReinfDiagramType, "BILINEAR_INCLINED")

        assert ReinfDiagramType.BILINEAR_NOT_INCLINED.value is not None
        assert ReinfDiagramType.BILINEAR_INCLINED.value is not None

    def test_reinf_type_enum_values(self) -> None:
        """Test ReinfType enum has correct values."""
        assert hasattr(ReinfType, "BARS")

        assert ReinfType.BARS.value is not None

    def test_reinf_fabrication_enum_values(self) -> None:
        """Test ReinfFabrication enum has correct values."""
        assert hasattr(ReinfFabrication, "HOT_ROLLED")

        assert ReinfFabrication.HOT_ROLLED.value is not None

    def test_conc_cement_class_enum_values(self) -> None:
        """Test ConcCementClass enum has correct values."""
        assert hasattr(ConcCementClass, "R")
        assert hasattr(ConcCementClass, "N")
        assert hasattr(ConcCementClass, "S")

        assert ConcCementClass.R.value is not None
        assert ConcCementClass.N.value is not None
        assert ConcCementClass.S.value is not None

    def test_conc_aggregate_type_enum_values(self) -> None:
        """Test ConcAggregateType enum has correct values."""
        assert hasattr(ConcAggregateType, "QUARTZITE")
        assert hasattr(ConcAggregateType, "LIMESTONE")
        assert hasattr(ConcAggregateType, "SANDSTONE")
        assert hasattr(ConcAggregateType, "BASALT")

        assert ConcAggregateType.QUARTZITE.value is not None
        assert ConcAggregateType.LIMESTONE.value is not None
        assert ConcAggregateType.SANDSTONE.value is not None
        assert ConcAggregateType.BASALT.value is not None

    def test_conc_diagram_type_enum_values(self) -> None:
        """Test ConcDiagramType enum has correct values."""
        assert hasattr(ConcDiagramType, "PARABOLIC")

        assert ConcDiagramType.PARABOLIC.value is not None

    def test_concrete_material_enum_values(self) -> None:
        """Test ConcreteMaterial enum has correct values."""
        # Test a few key concrete materials
        assert hasattr(ConcreteMaterial, "C12_15")
        assert hasattr(ConcreteMaterial, "C20_25")
        assert hasattr(ConcreteMaterial, "C25_30")
        assert hasattr(ConcreteMaterial, "C30_37")
        assert hasattr(ConcreteMaterial, "C35_45")
        assert hasattr(ConcreteMaterial, "C40_50")
        assert hasattr(ConcreteMaterial, "C45_55")
        assert hasattr(ConcreteMaterial, "C50_60")

        # Test values are accessible
        assert ConcreteMaterial.C12_15.value is not None
        assert ConcreteMaterial.C30_37.value is not None
        assert ConcreteMaterial.C50_60.value is not None

    def test_reinforcement_material_enum_values(self) -> None:
        """Test ReinforcementMaterial enum has correct values."""
        # Test key reinforcement materials
        assert hasattr(ReinforcementMaterial, "B_400A")
        assert hasattr(ReinforcementMaterial, "B_400B")
        assert hasattr(ReinforcementMaterial, "B_400C")
        assert hasattr(ReinforcementMaterial, "B_500A")
        assert hasattr(ReinforcementMaterial, "B_500B")
        assert hasattr(ReinforcementMaterial, "B_500C")

        # Test values are accessible
        assert ReinforcementMaterial.B_400A.value is not None
        assert ReinforcementMaterial.B_500B.value is not None
        assert ReinforcementMaterial.B_500C.value is not None

    def test_enum_value_types(self) -> None:
        """Test that enum values are either SDK objects or strings."""
        # Get a sample enum value
        value = ReinforcementClass.A.value

        # Value should be either an object (SDK enum) or a string (fallback)
        assert isinstance(value, (object, str))

        # Test that we can access the value attribute
        assert hasattr(ReinforcementClass.A, "value")

    def test_enums_can_be_compared(self) -> None:
        """Test that enum members can be compared."""
        assert ReinforcementClass.A == ReinforcementClass.A
        assert ReinforcementClass.A != ReinforcementClass.B

        assert ConcreteMaterial.C30_37 == ConcreteMaterial.C30_37
        assert ConcreteMaterial.C30_37 != ConcreteMaterial.C40_50

    def test_enum_iteration(self) -> None:
        """Test that we can iterate over enum members."""
        # Test a small enum
        bar_surfaces = list(BarSurface)
        assert len(bar_surfaces) == 2
        assert BarSurface.SMOOTH in bar_surfaces
        assert BarSurface.RIBBED in bar_surfaces

        # Test we can iterate over concrete materials
        concrete_materials = list(ConcreteMaterial)
        assert len(concrete_materials) > 0
        assert ConcreteMaterial.C30_37 in concrete_materials

    def test_enum_names(self) -> None:
        """Test that enum members have correct names."""
        assert ReinforcementClass.A.name == "A"
        assert ReinforcementClass.B.name == "B"
        assert ReinforcementClass.C.name == "C"

        assert ConcreteMaterial.C30_37.name == "C30_37"
        assert ReinforcementMaterial.B_500B.name == "B_500B"

    def test_enum_access_by_name(self) -> None:
        """Test that we can access enum members by name."""
        assert ReinforcementClass["A"] == ReinforcementClass.A
        assert ReinforcementClass["B"] == ReinforcementClass.B

        assert ConcreteMaterial["C30_37"] == ConcreteMaterial.C30_37
        assert ReinforcementMaterial["B_500B"] == ReinforcementMaterial.B_500B


class TestConcreteMaterialValues:
    """Test specific concrete material enum values."""

    def test_all_concrete_materials_exist(self) -> None:
        """Test that all expected concrete materials are defined."""
        expected_materials = [
            "C12_15",
            "C16_20",
            "C20_25",
            "C25_30",
            "C30_37",
            "C35_45",
            "C40_50",
            "C45_55",
            "C50_60",
            "C55_67",
            "C60_75",
            "C70_85",
            "C80_95",
            "C90_105",
        ]

        for material_name in expected_materials:
            assert hasattr(ConcreteMaterial, material_name), f"Missing concrete material: {material_name}"
            material = getattr(ConcreteMaterial, material_name)
            assert material.value is not None


class TestReinforcementMaterialValues:
    """Test specific reinforcement material enum values."""

    def test_all_reinforcement_materials_exist(self) -> None:
        """Test that all expected reinforcement materials are defined."""
        expected_materials = [
            "B_400A",
            "B_400B",
            "B_400C",
            "B_500A",
            "B_500B",
            "B_500C",
            "B_550A",
            "B_550B",
            "B_600A",
            "B_600B",
            "B_600C",
        ]

        for material_name in expected_materials:
            assert hasattr(ReinforcementMaterial, material_name), f"Missing reinforcement material: {material_name}"
            material = getattr(ReinforcementMaterial, material_name)
            assert material.value is not None


class TestEnumUsageInCode:
    """Test that enums can be used in typical code patterns."""

    def test_enum_in_dict_mapping(self) -> None:
        """Test using enums as dictionary keys and values."""
        # This is a common pattern in the codebase
        material_map = {
            "C30/37": ConcreteMaterial.C30_37,
            "C40/50": ConcreteMaterial.C40_50,
        }

        assert material_map["C30/37"] == ConcreteMaterial.C30_37
        assert material_map["C40/50"].value is not None

    def test_enum_in_function_parameter(self) -> None:
        """Test passing enums as function parameters."""

        def process_material(material: ConcreteMaterial) -> str:
            return f"Processing {material.name}"

        result = process_material(ConcreteMaterial.C30_37)
        assert result == "Processing C30_37"

    def test_enum_value_extraction(self) -> None:
        """Test extracting .value from enum for SDK usage."""
        # This is the key pattern for the builder
        material_enum = ConcreteMaterial.C30_37
        sdk_value = material_enum.value

        # Value should be usable (either SDK object or string)
        assert sdk_value is not None

    def test_enum_comparison_with_none(self) -> None:
        """Test comparing enum with None."""
        material = ConcreteMaterial.C30_37
        assert material is not None
        assert material != None  # noqa: E711


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
