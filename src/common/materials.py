"""
Centralized material management system for bridge analysis.

This module provides unified access to all material data from CSV files,
ensuring consistency across SCIA, IDEA StatiCa, and other integrations.
"""

import csv
from pathlib import Path
from typing import Any

# Material data paths
MATERIALS_DIR = Path(__file__).parent.parent.parent / "resources" / "data" / "materials"
CONCRETE_PATH = MATERIALS_DIR / "betonkwaliteit.csv"
REINFORCEMENT_PATH = MATERIALS_DIR / "betonstaalkwaliteit.csv"
PRESTRESS_PATH = MATERIALS_DIR / "voorspanstaalkwaliteit.csv"
BENDING_RADIUS_PATH = MATERIALS_DIR / "wapening_buigstraal.csv"


def get_concrete_qualities() -> list[str]:
    """
    Get list of available concrete qualities from the CSV file.

    :returns: List of concrete quality names (e.g., ["C12/15", "C30/37", ...])
    :rtype: list[str]
    :raises FileNotFoundError: If concrete materials CSV not found
    """
    try:
        with CONCRETE_PATH.open(encoding="utf-8") as f:
            csv_reader = csv.DictReader(f, delimiter=";")
            return [row["Betonkwaliteit"].strip('"') for row in csv_reader]
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Concrete materials file not found: {CONCRETE_PATH}") from e


def get_reinforcement_qualities() -> list[str]:
    """
    Get list of available reinforcement steel qualities from the CSV file.

    :returns: List of steel quality names (e.g., ["B500A", "B500B", ...])
    :rtype: list[str]
    :raises FileNotFoundError: If reinforcement materials CSV not found
    """
    try:
        with REINFORCEMENT_PATH.open(encoding="utf-8") as f:
            csv_reader = csv.DictReader(f, delimiter=";")
            return [row["Betonstaalkwaliteit"].strip('"') for row in csv_reader]
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Reinforcement materials file not found: {REINFORCEMENT_PATH}") from e


def get_prestress_qualities() -> list[str]:
    """
    Get list of available prestressing steel qualities from the CSV file.

    :returns: List of prestress steel quality names
    :rtype: list[str]
    :raises FileNotFoundError: If prestress materials CSV not found
    """
    try:
        with PRESTRESS_PATH.open(encoding="utf-8") as f:
            csv_reader = csv.DictReader(f, delimiter=";")
            return [row["Staalsoort"].strip('"') for row in csv_reader]
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Prestress materials file not found: {PRESTRESS_PATH}") from e


def get_concrete_material_properties(material_name: str) -> dict[str, Any]:
    """
    Get detailed properties for a specific concrete material.

    :param material_name: Concrete material name (e.g., "C30/37")
    :type material_name: str
    :returns: Dictionary with material properties (fck, fcd, etc.)
    :rtype: dict[str, Any]
    :raises ValueError: If material not found
    """
    try:
        with CONCRETE_PATH.open(encoding="utf-8") as f:
            csv_reader = csv.DictReader(f, delimiter=";")
            for row in csv_reader:
                if row["Betonkwaliteit"].strip('"') == material_name:
                    return {
                        "name": material_name,
                        "fck": float(row["fck[N/mm^2]"]),
                        "fcd": float(row["fcd[N/mm^2]"]),
                    }
        raise ValueError(f"Concrete material '{material_name}' not found in material database")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Concrete materials file not found: {CONCRETE_PATH}") from e


def get_reinforcement_material_properties(material_name: str) -> dict[str, Any]:
    """
    Get detailed properties for a specific reinforcement material.

    :param material_name: Reinforcement material name (e.g., "B500B")
    :type material_name: str
    :returns: Dictionary with material properties (fyk, fyd, etc.)
    :rtype: dict[str, Any]
    :raises ValueError: If material not found
    """
    try:
        with REINFORCEMENT_PATH.open(encoding="utf-8") as f:
            csv_reader = csv.DictReader(f, delimiter=";")
            for row in csv_reader:
                if row["Betonstaalkwaliteit"].strip('"') == material_name:
                    return {
                        "name": material_name,
                        "fyk": float(row["fyk[N/mm^2]"]),
                        "fyd": float(row["fyd[N/mm^2]"]),
                    }
        raise ValueError(f"Reinforcement material '{material_name}' not found in material database")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Reinforcement materials file not found: {REINFORCEMENT_PATH}") from e


def check_material_compatibility(concrete: str, reinforcement: str) -> bool:
    """
    Check if concrete and reinforcement materials are compatible.

    :param concrete: Concrete grade (e.g., "C30/37")
    :type concrete: str
    :param reinforcement: Reinforcement material (e.g., "B500B")
    :type reinforcement: str
    :returns: True if materials are compatible
    :rtype: bool
    :raises ValueError: If material names are invalid
    """
    try:
        # Check if both materials exist in the system
        get_concrete_material_properties(concrete)
        get_reinforcement_material_properties(reinforcement)

        # Add compatibility logic here if needed
        # For now, just verify both materials exist
    except ValueError:
        return False
    else:
        return True


def get_default_materials() -> dict[str, str]:
    """
    Get default material recommendations for bridge analysis.

    :returns: Dictionary with default concrete and reinforcement materials
    :rtype: dict[str, str]
    """
    return {
        "concrete": "C30/37",
        "reinforcement": "B500B",
        "prestress": "FeP 1770",  # if needed
    }


def normalize_material_name(material_name: str) -> str:
    """
    Normalize material names to handle decimal separator differences and common name variations.

    Converts decimal points to commas to match CSV database format.
    Also handles common material name variations and old bridge material specifications.
    This handles localization issues where user input uses '.' but CSV uses ','.

    :param material_name: Material name to normalize (e.g., "B37.5", "B400", "QR24")
    :type material_name: str
    :returns: Normalized material name (e.g., "B37,5", "FeB 400", "QR24")
    :rtype: str
    """
    # First handle decimal separator conversion
    normalized = material_name.replace(".", ",")

    # Handle common material name variations for old bridge materials
    # Map user-friendly names to exact CSV database names
    name_mappings = {
        # Old DIN/German steel grades -> FeB equivalents in CSV
        "B400": "FeB 400",
        "B220": "FeB 220",
        "B500": "FeB 500",
        # Handle range specifications for old bridges
        # QR24-QR40 could be interpreted as QR40 (higher strength)
        "QR24-QR40": "QR40",
        # Old bridge steels are already in CSV with exact names:
        # QR22, QR24, QR30, QR32, QR36, QR40, QR42, QR48
        # QRn32, QRn36, QRn40, QRn42, QRn48, QRn54
        # These don't need mapping as they exist exactly as specified
    }

    # Apply mapping if exact match found
    if normalized in name_mappings:
        return name_mappings[normalized]

    return normalized


def validate_material_exists(material_name: str, material_type: str) -> bool:
    """
    Check if a material exists in the project database.

    Handles decimal separator normalization to support both "B37.5" and "B37,5" formats.

    :param material_name: Material name to check
    :type material_name: str
    :param material_type: Type of material ("concrete" or "reinforcement")
    :type material_type: str
    :returns: True if material exists in database
    :rtype: bool
    :raises ValueError: If material_type is invalid
    """
    # Normalize material name to handle decimal separator differences
    normalized_name = normalize_material_name(material_name)

    if material_type == "concrete":
        available_materials = get_concrete_qualities()
        return normalized_name in available_materials or material_name in available_materials
    if material_type == "reinforcement":
        available_materials = get_reinforcement_qualities()
        return normalized_name in available_materials or material_name in available_materials
    raise ValueError(f"Invalid material type: {material_type}. Must be 'concrete' or 'reinforcement'")


def get_supported_idea_materials() -> dict[str, list[str]]:
    """
    Get materials from our database that are also supported by IDEA StatiCa.

    This filters our complete material database to only include materials
    that have equivalent enums in the IDEA StatiCa SDK.

    :returns: Dictionary with concrete and reinforcement materials supported by IDEA
    :rtype: dict[str, list[str]]
    """
    # Standard Eurocode materials that IDEA StatiCa typically supports
    idea_concrete_materials = ["C12/15", "C16/20", "C20/25", "C25/30", "C30/37", "C35/45", "C40/50", "C45/55", "C50/60"]

    # Only include reinforcement materials that exist in our CSV database
    # B400A and B400B don't exist in betonstaalkwaliteit.csv, so removed
    idea_reinforcement_materials = ["B500A", "B500B", "B500C"]

    # Filter to only materials that exist in our database
    available_concrete = get_concrete_qualities()
    available_reinforcement = get_reinforcement_qualities()

    supported_concrete = [mat for mat in idea_concrete_materials if mat in available_concrete]
    supported_reinforcement = [mat for mat in idea_reinforcement_materials if mat in available_reinforcement]

    return {"concrete": supported_concrete, "reinforcement": supported_reinforcement}


def get_supported_scia_materials() -> dict[str, list[str]]:
    """
    Get materials from our database that are also supported by SCIA Engineer.

    SCIA Engineer supports more materials since it uses string-based material names
    Include both modern Eurocode materials and common older materials from CSV

    :returns: Dictionary with concrete materials supported by SCIA
    :rtype: dict[str, list[str]]
    """
    # SCIA Engineer supports more materials since it uses string-based material names
    # Include both modern Eurocode materials and common older materials from CSV
    scia_concrete_materials = [
        # Modern Eurocode materials
        "C12/15",
        "C16/20",
        "C20/25",
        "C25/30",
        "C30/37",
        "C35/45",
        "C40/50",
        "C45/55",
        "C50/60",
        "C53/65",
        "C55/67",
        "C60/75",
        "C70/85",
        "C80/95",
        "C90/105",
        # Older materials that exist in CSV and SCIA can handle
        "K150",
        "K160",
        "K200",
        "K225",
        "K250",
        "K300",
        "K400",
        "K450",
        "K500",
        "K600",
        "B12,5",
        "B17,5",
        "B22,5",
        "B30",
        "B35",
        "B37,5",
        "B45",
        "B52,5",
        "B55",
        "B60",
        "B65",
    ]

    # SCIA can handle most reinforcement materials as strings
    # Include old bridge materials that exist in our CSV database
    scia_reinforcement_materials = [
        # Modern Eurocode materials
        "B500A",
        "B500B",
        "B500C",
        # Older materials from CSV that SCIA can handle
        "FeB 220",
        "FeB 400",
        "FeB 500",
        "QR22",
        "QR24",
        "QR30",
        "QR32",
        "QR36",
        "QR40",
        "QR42",
        "QR48",
        "QRn32",
        "QRn36",
        "QRn40",
        "QRn42",
        "QRn48",
        "QRn54",
        # Add other old materials that might be used
        "1. B",
        "HK",
        "St. 37",
        "St. 52",
        "Speciaal st. 36",
        "Speciaal st. 48",
    ]

    # Filter to only materials that exist in our database
    available_concrete = get_concrete_qualities()
    available_reinforcement = get_reinforcement_qualities()

    supported_concrete = [mat for mat in scia_concrete_materials if mat in available_concrete]
    supported_reinforcement = [mat for mat in scia_reinforcement_materials if mat in available_reinforcement]

    return {"concrete": supported_concrete, "reinforcement": supported_reinforcement}


# Legacy compatibility functions (to be deprecated)
def get_steel_qualities() -> list[str]:
    """
    Legacy function for backward compatibility.

    :deprecated: Use get_reinforcement_qualities() instead
    :returns: List of steel quality names
    :rtype: list[str]
    """
    return get_reinforcement_qualities()


def get_material_compatibility_info(material_name: str) -> dict[str, str]:
    """
    Get compatibility information for a specific material across integrations.

    Returns status for SCIA Engineer and IDEA StatiCa integrations, including
    any automatic mappings that will be applied.

    :param material_name: Material name to check
    :type material_name: str
    :returns: Dictionary with compatibility status for each integration
    :rtype: dict[str, str]
    """
    # Normalize material name first
    normalized_name = normalize_material_name(material_name)

    # Check if material exists in project database
    if not validate_material_exists(material_name, "reinforcement"):
        return {
            "status": "ERROR",
            "message": f"Material '{material_name}' not found in project database",
            "scia": "Not supported - material not in database",
            "idea": "Not supported - material not in database",
        }

    # Check SCIA compatibility (more permissive)
    scia_supported = get_supported_scia_materials()["reinforcement"]
    scia_status = "Direct support" if normalized_name in scia_supported else "Not supported"

    # Check IDEA compatibility (only modern materials)
    idea_supported = get_supported_idea_materials()["reinforcement"]
    if normalized_name in idea_supported:
        idea_status = "Direct support"
    else:
        # Simple strength-based mapping for common materials
        strength_mapping = {
            "QR22": "B500A",
            "QR24": "B500A",
            "QR30": "B500B",
            "QR40": "B500B",
            "FeB 400": "B500B",
            "QR48": "B500C",
            "FeB 500": "B500C",
        }
        equivalent = strength_mapping.get(normalized_name, "B500B")
        idea_status = f"Auto-mapped to {equivalent}"

    return {
        "material": material_name,
        "normalized": normalized_name,
        "scia": scia_status,
        "idea": idea_status,
        "recommendation": (
            "Use B500A, B500B, or B500C for full compatibility with both integrations"
            if normalized_name not in idea_supported
            else "Fully compatible with both integrations"
        ),
    }
