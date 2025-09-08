"""
Unit conversion utilities for SCIA results.

This module provides a centralized way to handle both unit mapping and value conversion
to ensure they stay in sync.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class UnitConversion:
    """
    Represents a unit conversion with both the display unit and conversion factor.

    :param display_unit: The unit string to display (e.g., "kN", "kNm")
    :param conversion_factor: Factor to convert from raw SCIA units (N->kN = 1/1000)
    :param raw_unit: The original unit from SCIA (for documentation)
    """

    display_unit: str
    conversion_factor: float
    raw_unit: str = ""


class SciaUnitConverter:
    """
    Centralized unit conversion system for SCIA results.

    This class keeps unit mapping and value conversion together to ensure consistency.
    All SCIA force values come as N (Newtons) and moments as Nm (Newton-meters).
    We convert them to kN and kNm for better readability.
    """

    # Define conversions for 2D plate elements (forces/moments per unit length)
    _CONVERSIONS_2D = {
        # Bending moments per unit length (2D plates) - from Nm to kNm
        "m_x": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "m_y": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "m_xy": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        # Shear forces per unit length (2D plates) - from N to kN
        "v_x": UnitConversion("kN/m", 1 / 1000, "N/m"),
        "v_y": UnitConversion("kN/m", 1 / 1000, "N/m"),
        # Membrane forces per unit length (2D plates) - from N to kN
        "n_x": UnitConversion("kN/m", 1 / 1000, "N/m"),
        "n_y": UnitConversion("kN/m", 1 / 1000, "N/m"),
        "n_xy": UnitConversion("kN/m", 1 / 1000, "N/m"),
        # Envelope components for 2D plates - from Nm to kNm
        "m_xD+": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "m_xD-": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "m_yD+": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "m_yD-": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "m_cD+": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "m_cD-": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        # Envelope components for 2D plates - from N to kN
        "n_xD": UnitConversion("kN/m", 1 / 1000, "N/m"),
        "n_yD": UnitConversion("kN/m", 1 / 1000, "N/m"),
        "n_cD": UnitConversion("kN/m", 1 / 1000, "N/m"),
        # Standard naming conventions used downstream
        "N": UnitConversion("kN/m", 1 / 1000, "N/m"),
        "Vy": UnitConversion("kN/m", 1 / 1000, "N/m"),
        "Vz": UnitConversion("kN/m", 1 / 1000, "N/m"),
        "Mxd+": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "Mxd-": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "Myd+": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
        "Myd-": UnitConversion("kNm/m", 1 / 1000, "Nm/m"),
    }

    # Define conversions for 1D beam elements (absolute forces/moments)
    _CONVERSIONS_1D = {
        # Standard 1D beam forces - from N to kN
        "N": UnitConversion("kN", 1 / 1000, "N"),
        "Vy": UnitConversion("kN", 1 / 1000, "N"),
        "Vz": UnitConversion("kN", 1 / 1000, "N"),
        # Standard 1D beam moments - from Nm to kNm
        "Mx": UnitConversion("kNm", 1 / 1000, "Nm"),
        "My": UnitConversion("kNm", 1 / 1000, "Nm"),
        "Mz": UnitConversion("kNm", 1 / 1000, "Nm"),
        # Envelope-style moment keys
        "Mxd+": UnitConversion("kNm", 1 / 1000, "Nm"),
        "Mxd-": UnitConversion("kNm", 1 / 1000, "Nm"),
        "Myd+": UnitConversion("kNm", 1 / 1000, "Nm"),
        "Myd-": UnitConversion("kNm", 1 / 1000, "Nm"),
    }

    def __init__(self, element_type: str = "1D") -> None:
        """
        Initialize the converter for a specific element type.

        :param element_type: "1D" for beam elements, "2D" for plate elements
        """
        if element_type == "2D":
            self.conversions = self._CONVERSIONS_2D.copy()
        else:
            self.conversions = self._CONVERSIONS_1D.copy()

        self.element_type = element_type

    def get_display_unit(self, force_component: str) -> str:
        """
        Get the display unit for a force component.

        :param force_component: Name of the force component (e.g., "Vy", "Mxd+")
        :returns: Display unit string (e.g., "kN", "kNm")
        """
        conversion = self.conversions.get(force_component)
        if conversion:
            return conversion.display_unit

        # Fallback - try to guess based on component name
        # Check for moment indicators first (more specific)
        if any(moment_key in force_component.lower() for moment_key in ["m_", "mx", "my", "mz", "moment"]):
            return "kNm/m" if self.element_type == "2D" else "kNm"
        # Default to force units
        return "kN/m" if self.element_type == "2D" else "kN"

    def convert_value(self, value: Any, force_component: str) -> float:
        """
        Convert a value from raw SCIA units to display units.

        :param value: Raw value from SCIA (in N or Nm)
        :param force_component: Name of the force component
        :returns: Converted value for display
        :raises ValueError: If value cannot be converted to float
        """
        try:
            float_value = float(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert value '{value}' to float") from e

        conversion = self.conversions.get(force_component)
        if conversion:
            return float_value * conversion.conversion_factor

        # Fallback - assume force/moment conversion based on component name
        # Check for moment indicators first (more specific)
        if any(moment_key in force_component.lower() for moment_key in ["m_", "mx", "my", "mz", "moment"]):
            return float_value / 1000.0  # Nm to kNm
        # Default to force conversion
        return float_value / 1000.0  # N to kN

    def format_value_with_unit(self, value: Any, force_component: str, decimals: int = 1, default: str = "N/A") -> str:
        """
        Convert and format a value with its unit.

        :param value: Raw value from SCIA
        :param force_component: Name of the force component
        :param decimals: Number of decimal places
        :param default: Default string if conversion fails
        :returns: Formatted string with converted value and unit
        """
        try:
            converted_value = self.convert_value(value, force_component)
            unit = self.get_display_unit(force_component)
            return f"{converted_value:.{decimals}f} {unit}"
        except (ValueError, TypeError):
            return default

    def get_units_mapping(self) -> dict[str, str]:
        """
        Get a mapping of force components to their display units.

        :returns: Dictionary mapping component names to unit strings
        """
        return {component: conversion.display_unit for component, conversion in self.conversions.items()}

    @classmethod
    def create_for_table_type(cls, table_name: str | None) -> "SciaUnitConverter":
        """
        Create a converter based on the SCIA table type.

        :param table_name: Name of the SCIA table (used to determine 1D vs 2D)
        :returns: Configured SciaUnitConverter instance
        """
        # Heuristic: consider any table name containing "2D" as plate forces; "1D" as beam forces
        if isinstance(table_name, str) and ("2D" in table_name or "2d" in table_name.lower()):
            return cls("2D")
        # Default to 1D for beam forces or unknown table types
        return cls("1D")


def build_units_mapping(results: dict[str, Any]) -> dict[str, dict[str, str]]:
    """
    Build a units mapping for SCIA results using the centralized converter.

    This function maintains backward compatibility with the existing interface
    while using the new centralized conversion system.

    :param results: The complete results dictionary from extract_analysis_results
    :returns: Mapping from category -> { result_component: unit_string }
    """
    # Determine table type from internal forces
    internal_forces_entry = results.get("internal_forces")
    table_name = None
    if isinstance(internal_forces_entry, dict):
        table_name = internal_forces_entry.get("table_name")

    # Create converter for the detected table type
    converter = SciaUnitConverter.create_for_table_type(table_name)

    # Build the units mapping
    units = {
        "internal_forces": converter.get_units_mapping(),
    }

    return units


# Backward compatibility functions
def safe_float_format(value: Any, unit: str = "", default: str = "N/A") -> str:
    """
    Safely format a value as a float with unit conversion.

    This function maintains backward compatibility while using the new conversion system.
    For new code, prefer using SciaUnitConverter.format_value_with_unit() directly.

    :param value: Value to format
    :param unit: Target unit (e.g., "kN", "kNm")
    :param default: Default value if formatting fails
    :returns: Formatted string with unit or default value
    """
    try:
        if value is None:
            return default

        # Try to import pandas for isna check, fallback if not available
        try:
            import pandas as pd

            if pd.isna(value):
                return default
        except ImportError:
            pass

        float_value = float(value)

        # Apply unit conversion based on target unit
        if unit == "kN" or unit == "kN/m":
            # Convert from N to kN
            float_value = float_value / 1000.0
        elif unit == "kNm" or unit == "kNm/m":
            # Convert from Nm to kNm
            float_value = float_value / 1000.0

        unit_suffix = f" {unit}" if unit else ""
        return f"{float_value:.1f}{unit_suffix}"
    except (ValueError, TypeError):
        return default
