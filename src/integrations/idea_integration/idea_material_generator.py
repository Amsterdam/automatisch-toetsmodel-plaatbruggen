"""
IDEA material generator module.

This module provides functions to create IDEA RCS concrete and reinforcement materials from CSV data.
"""

from pathlib import Path
from typing import Any

from viktor.external import idea_rcs

from src.integrations.idea_integration.constants.formatting import STRAIN_CONVERSION_FACTOR
from src.integrations.idea_integration.constants.materials import (
    DEFAULT_CONCRETE_UNIT_MASS,
    DEFAULT_EPSUK,
    DEFAULT_FTK_TO_FYK_RATIO,
    DEFAULT_REINFORCEMENT_CLASS,
    DEFAULT_STEEL_UNIT_MASS,
    DEFAULT_STONE_DIAMETER,
    DEFAULT_YOUNGS_MODULUS,
)
from src.integrations.idea_integration.constants.paths import IDEA_MATERIALS_PATH
from src.integrations.idea_integration.constants.units import MM_TO_M_IDEA


def _get_material_name_with_suffix(base_material_name: str, material_type: str) -> str | None:
    """
    Try to find the suffixed material name in the combined CSV based on the base name.

    This function implements a mapping from old material names (without suffix)
    to new material names (with suffix) for backward compatibility.

    :param base_material_name: Original material name without suffix (e.g., "B25", "QR22")
    :type base_material_name: str
    :param material_type: Type of material ("concrete" or "reinforcement")
    :type material_type: str
    :returns: Material name with suffix if found, None otherwise
    :rtype: str | None
    """
    if material_type == "concrete":
        # Concrete materials mapping
        concrete_mapping = {
            # GBV 1940 materials
            "K150": "K150_GBV1940",
            "K200": "K200_GBV1940",
            "K250": "K250_GBV1940",
            # GBV 1962 materials
            "K160": "K160_GBV1962",
            "K225": "K225_GBV1962",
            "K300": "K300_GBV1962",
            "K400": "K400_GBV1962",
            "K450": "K450_GBV1962",
            # NEN 6720 materials
            "B25": "B25_NEN6720",
            "B35": "B35_NEN6720",
            "B45": "B45_NEN6720",
            "B55": "B55_NEN6720",
            "B65": "B65_NEN6720",
            # VB 74+84 materials
            "B12,5": "B12,5_VB7484",
            "B17,5": "B17,5_VB7484",
            "B22,5": "B22,5_VB7484",
            "B30": "B30_VB7484",
            "B37,5": "B37,5_VB7484",
            "B52,5": "B52,5_VB7484",
            "B60": "B60_VB7484",
        }
        return concrete_mapping.get(base_material_name)

    if material_type == "reinforcement":
        # Reinforcement materials mapping
        reinforcement_mapping = {
            # GBV 1940 materials
            "St. 37": "St. 37_GBV1940",
            "HK": "HK_GBV1940",  # Note: "HK" appears in GBV 1940 but not in our CSV list
            # GBV 1950 materials
            "QR22": "QR22_GBV1950",  # Prefer 1950 over 1962
            "QR24": "QR24_GBV1950",  # Prefer 1950 over 1962
            "QR30": "QR30_GBV1950",
            "QR36": "QR36_GBV1950",
            "QR42": "QR42_GBV1950",
            # GBV 1962 materials (unique ones)
            "QR32": "QR32_GBV1962",
            "QR40": "QR40_GBV1962",
            "QR48": "QR48_GBV1962",
            # NEN 6720 materials
            "FeB500 HWL, HK": "FeB500 HWL, HK_NEN6720",
            "FeB400 HWL, HK": "FeB400 HWL, HK_NEN6720",
            "FeB220 HWL": "FeB220 HWL_NEN6720",
            # VB 74+84 materials
            "FeB220 HW": "FeB220 HW_VB7484",
            "FeB400 HW": "FeB400 HW_VB7484",
            "FeB500 HW": "FeB500 HW_VB7484",
        }
        return reinforcement_mapping.get(base_material_name)

    return None


def _parse_csv_header_and_data_start(lines: list[str]) -> tuple[list[str], int]:
    """
    Parse CSV lines to extract header columns and find data start index.

    :param lines: Lines from the CSV file
    :type lines: list[str]
    :returns: Tuple of (column_names, data_start_index)
    :rtype: tuple[list[str], int]
    :raises ValueError: If CSV format is invalid
    """
    header_line = None
    data_start_idx = None

    for i, line in enumerate(lines):
        if line.strip().startswith('"Header"'):
            header_line = line.strip()
        elif line.strip().startswith('"Data"'):
            data_start_idx = i + 1
            break

    if header_line is None or data_start_idx is None:
        raise ValueError("Invalid CSV format: missing Header or Data markers")

    # Parse header to get column names
    header_parts = header_line.split(";")
    column_names = [part.strip('"') for part in header_parts]

    return column_names, data_start_idx


def _process_csv_row(row_data: dict[str, str]) -> dict[str, Any]:
    """
    Process a single CSV row, converting values to appropriate types.

    :param row_data: Raw row data from CSV
    :type row_data: dict[str, str]
    :returns: Processed row data with converted types
    :rtype: dict[str, Any]
    """
    material_data: dict[str, Any] = {}
    for key, value in row_data.items():
        clean_key = key.strip('"')
        clean_value = value.strip('"')

        # Try to convert to float for numeric values
        if clean_value and clean_value != "boolean":
            try:
                material_data[clean_key] = float(clean_value.replace(",", "."))
            except ValueError:
                material_data[clean_key] = clean_value
        else:
            material_data[clean_key] = clean_value

    return material_data


def _parse_csv_for_material(csv_path: Path, material_name: str) -> dict[str, Any]:
    """
    Parse a CSV file to find material data for a specific material.

    :param csv_path: Path to the CSV file
    :type csv_path: Path
    :param material_name: Name of the material to find
    :type material_name: str
    :returns: Dictionary containing material properties from CSV
    :rtype: dict[str, Any]
    :raises ValueError: If material is not found or CSV format is invalid
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        with open(csv_path, encoding="utf-8") as file:
            lines = file.readlines()

            column_names, data_start_idx = _parse_csv_header_and_data_start(lines)

            # Process data rows
            for raw_line in lines[data_start_idx:]:
                line = raw_line.strip()
                if not line:
                    continue

                # Split the line and create a dictionary
                data_parts = line.split(";")
                if len(data_parts) != len(column_names):
                    continue

                row = dict(zip(column_names, data_parts))

                # Remove quotes from material name and compare
                csv_material_name = row.get(column_names[0], "").strip('"')
                if csv_material_name == material_name:
                    return _process_csv_row(row)

    except UnicodeDecodeError as e:
        raise ValueError(f"Error reading CSV file {csv_path}: {e}")
    except Exception as e:
        raise ValueError(f"Error parsing CSV file {csv_path}: {e}")

    raise ValueError(f"Material '{material_name}' not found in {csv_path}")


def _get_csv_files_for_reinforcement() -> list[str]:
    """
    Get the list of CSV files to check for reinforcement materials.

    :returns: List of CSV filenames for reinforcement materials
    :rtype: list[str]
    """
    return ["Reinforcement_All.csv"]


def _get_csv_files_for_concrete(material_prefix: str) -> list[str]:  # noqa: ARG001
    """
    Get the list of CSV files to check for concrete materials.

    :param material_prefix: First character of the material name (kept for backward compatibility)
    :type material_prefix: str
    :returns: List of CSV filenames to check
    :rtype: list[str]
    """
    return ["Concrete_All.csv"]


def get_reinforcement_material_from_csv(material_name: str) -> dict[str, Any]:
    """
    Read reinforcement material properties from the combined CSV file.

    Supports both old material names (without suffix) and new material names (with suffix).

    :param material_name: Name of the reinforcement material (e.g., "FeB500 HWL, HK", "QR22", "St. 37")
                         Can be with or without suffix (e.g., "QR22" or "QR22_GBV1950")
    :type material_name: str
    :returns: Dictionary containing material properties from CSV
    :rtype: dict[str, Any]
    :raises FileNotFoundError: If no appropriate CSV file is found
    :raises ValueError: If the material is not found in any CSV file
    """
    # Base path to CSV files
    csv_base_path = IDEA_MATERIALS_PATH
    csv_files_to_check = _get_csv_files_for_reinforcement()

    # Try with the exact name first
    for filename in csv_files_to_check:
        csv_path = csv_base_path / filename

        try:
            return _parse_csv_for_material(csv_path, material_name)
        except (FileNotFoundError, ValueError):
            continue

    # If not found, try to map old name to new name with suffix
    suffixed_name = _get_material_name_with_suffix(material_name, "reinforcement")
    if suffixed_name and suffixed_name != material_name:
        for filename in csv_files_to_check:
            csv_path = csv_base_path / filename

            try:
                return _parse_csv_for_material(csv_path, suffixed_name)
            except (FileNotFoundError, ValueError):
                continue

    raise ValueError(f"Reinforcement material '{material_name}' not found in any CSV file")


def create_idea_reinforcement_material(model: idea_rcs.Model, material_name: str, custom_name: str | None = None) -> idea_rcs.MatReinforcementEc2:
    """
    Create an IDEA RCS reinforcement material from CSV data.

    Note: This function is now primarily used internally.
    For general use, prefer create_reinforcement_material_for_idea() from idea_material_mapping.

    :param model: IDEA RCS model instance
    :type model: idea_rcs.Model
    :param material_name: Name of the reinforcement material (e.g., "FeB500 HWL, HK", "HK", "St. 37")
    :type material_name: str
    :param custom_name: Optional custom name for the material in IDEA
    :type custom_name: Optional[str]
    :returns: Created IDEA RCS reinforcement material
    :rtype: idea_rcs.MatReinforcementEc2
    :raises ValueError: If material is not supported or CSV data is invalid
    """
    # For modern Eurocode materials, use built-in IDEA materials
    if material_name.startswith("B") and len(material_name) >= 4 and material_name[1:4].isdigit():
        # Import here to avoid circular imports
        from .idea_material_mapping import get_idea_reinforcement_material

        try:
            base_material = get_idea_reinforcement_material(material_name)
            return model.create_reinforcement_material(base_material, name=custom_name)
        except ValueError:
            raise ValueError(f"Eurocode material '{material_name}' is not supported by IDEA RCS")

    # For historical materials, read from CSV
    try:
        material_data = get_reinforcement_material_from_csv(material_name)
    except (FileNotFoundError, ValueError) as e:
        raise ValueError(f"Cannot create reinforcement material '{material_name}': {e}")

    # Extract required parameters from CSV data
    try:
        # Required parameters for create_reinforcement_material
        fyk = material_data["Fyk"]  # Characteristic yield strength
        unit_mass = material_data.get("UnitMass", DEFAULT_STEEL_UNIT_MASS)  # Unit mass in kg/m³

        # Optional parameters with defaults
        e_modulus = material_data.get("E", DEFAULT_YOUNGS_MODULUS)  # Young's modulus in MPa
        ftk = material_data.get("Ftk", fyk * DEFAULT_FTK_TO_FYK_RATIO)  # Tensile strength (default ratio * fyk)
        ftk_by_fyk = ftk / fyk  # Calculate the ratio for API
        epsuk = material_data.get("Epsuk", DEFAULT_EPSUK)  # Ultimate strain (already in 1e-4 units for API)

        # Map reinforcement class from CSV
        class_value = material_data.get("Class", DEFAULT_REINFORCEMENT_CLASS)
        reinforcement_class_map = {
            "A": idea_rcs.ReinfClass.A,
            "B": idea_rcs.ReinfClass.B,
            "C": idea_rcs.ReinfClass.C,
        }
        reinforcement_class = reinforcement_class_map.get(class_value, idea_rcs.ReinfClass.B)

        # Map bar surface from CSV
        bar_surface_value = material_data.get("BarSurface", "Ribbed")
        bar_surface_map = {
            "Smooth": idea_rcs.BarSurface.SMOOTH,
            "Ribbed": idea_rcs.BarSurface.RIBBED,
        }
        bar_surface = bar_surface_map.get(bar_surface_value, idea_rcs.BarSurface.RIBBED)

        # Map diagram type from CSV
        diagram_type_value = material_data.get("DiagramType", "BilinerWithOutAnInclinedTopBranch")
        diagram_type_map = {
            "BilinerWithOutAnInclinedTopBranch": idea_rcs.ReinfDiagramType.BILINEAR_NOT_INCLINED,
            "BilinearWithInclinedTopBranch": idea_rcs.ReinfDiagramType.BILINEAR_INCLINED,
        }
        diagram_type = diagram_type_map.get(diagram_type_value, idea_rcs.ReinfDiagramType.BILINEAR_NOT_INCLINED)

        # Use a default base material (we'll override the properties)
        # For historical materials, we'll use B500B as a starting point
        base_material = idea_rcs.ReinforcementMaterial.B_500B

        # Create the material
        material_display_name = custom_name or f"{material_name} (Historical)"

        reinforcement_material = model.create_reinforcement_material(
            base_material=base_material,
            name=material_display_name,
            unit_mass=unit_mass,
            e_modulus=e_modulus,
            fyk=fyk,
            ftk_by_fyk=ftk_by_fyk,
            epsuk=epsuk,
            type_=idea_rcs.ReinfType.BARS,
            bar_surface=bar_surface,
            class_=reinforcement_class,
            fabrication=idea_rcs.ReinfFabrication.HOT_ROLLED,
            diagram_type=diagram_type,
        )

    except KeyError as e:
        raise ValueError(f"Required parameter {e} not found in CSV data for reinforcement material '{material_name}'")
    except Exception as e:
        raise ValueError(f"Error creating IDEA reinforcement material for '{material_name}': {e}")
    else:
        return reinforcement_material


def get_concrete_material_from_csv(material_name: str) -> dict[str, Any]:
    """
    Read concrete material properties from the combined CSV file.

    Supports both old material names (without suffix) and new material names (with suffix).

    :param material_name: Name of the concrete material (e.g., "K150", "C30/37", "B25")
                         Can be with or without suffix (e.g., "B25" or "B25_NEN6720")
    :type material_name: str
    :returns: Dictionary containing material properties from CSV
    :rtype: dict[str, Any]
    :raises FileNotFoundError: If no appropriate CSV file is found
    :raises ValueError: If the material is not found in any CSV file
    """
    # Determine material prefix
    material_prefix = material_name[0]

    if material_prefix == "C":
        raise ValueError(f"Modern Eurocode material '{material_name}' should use IDEA RCS built-in materials, not CSV data")

    # Base path to CSV files
    csv_base_path = IDEA_MATERIALS_PATH
    csv_files_to_check = _get_csv_files_for_concrete(material_prefix)

    # Try with the exact name first
    for filename in csv_files_to_check:
        csv_path = csv_base_path / filename

        try:
            return _parse_csv_for_material(csv_path, material_name)
        except (FileNotFoundError, ValueError):
            continue

    # If not found, try to map old name to new name with suffix
    suffixed_name = _get_material_name_with_suffix(material_name, "concrete")
    if suffixed_name and suffixed_name != material_name:
        for filename in csv_files_to_check:
            csv_path = csv_base_path / filename

            try:
                return _parse_csv_for_material(csv_path, suffixed_name)
            except (FileNotFoundError, ValueError):
                continue

    raise ValueError(f"Material '{material_name}' not found in any CSV file")


def create_idea_concrete_material(model: idea_rcs.Model, material_name: str, custom_name: str | None = None) -> idea_rcs.MatConcreteEc2:
    """
    Create an IDEA RCS concrete material from CSV data.

    Note: This function is now primarily used internally.
    For general use, prefer create_concrete_material_for_idea() from idea_material_mapping.

    :param model: IDEA RCS model instance
    :type model: idea_rcs.Model
    :param material_name: Name of the concrete material (e.g., "K150", "C30/37", "B25")
    :type material_name: str
    :param custom_name: Optional custom name for the material in IDEA
    :type custom_name: Optional[str]
    :returns: Created IDEA RCS concrete material
    :rtype: idea_rcs.MatConcreteEc2
    :raises ValueError: If material is not supported or CSV data is invalid
    """
    # For modern Eurocode materials, use built-in IDEA materials
    if material_name.startswith("C"):
        # Import here to avoid circular imports
        from .idea_material_mapping import get_idea_concrete_material

        try:
            base_material = get_idea_concrete_material(material_name)
            return model.create_concrete_material(base_material, name=custom_name)
        except ValueError:
            raise ValueError(f"Eurocode material '{material_name}' is not supported by IDEA RCS")

    # For historical materials, read from CSV
    try:
        material_data = get_concrete_material_from_csv(material_name)
    except (FileNotFoundError, ValueError) as e:
        raise ValueError(f"Cannot create material '{material_name}': {e}")

    # Extract required parameters from CSV data
    try:
        # Required parameters for create_concrete_material
        fck = material_data["Fck"]  # Characteristic compressive strength
        unit_mass = material_data.get("UnitMass", DEFAULT_CONCRETE_UNIT_MASS)  # Unit mass in kg/m³

        # Optional parameters with defaults
        stone_diameter = material_data.get("StoneDiameter", DEFAULT_STONE_DIAMETER) / MM_TO_M_IDEA  # Convert mm to m
        cement_class_value = material_data.get("CementClass", 1)
        aggregate_type_value = material_data.get("AggregateType", 0)

        # Map cement class (integer to enum)
        cement_class_map = {
            0: idea_rcs.ConcCementClass.S,
            1: idea_rcs.ConcCementClass.R,
            2: idea_rcs.ConcCementClass.N,
        }
        cement_class = cement_class_map.get(int(cement_class_value), idea_rcs.ConcCementClass.R)

        # Map aggregate type (integer to enum)
        aggregate_type_map = {
            0: idea_rcs.ConcAggregateType.QUARTZITE,
            1: idea_rcs.ConcAggregateType.LIMESTONE,
            2: idea_rcs.ConcAggregateType.SANDSTONE,
            3: idea_rcs.ConcAggregateType.BASALT,
        }
        aggregate_type = aggregate_type_map.get(int(aggregate_type_value), idea_rcs.ConcAggregateType.QUARTZITE)

        # Use a default base material (we'll override the properties)
        # For historical materials, we'll use C20/25 as a starting point
        base_material = idea_rcs.ConcreteMaterial.C20_25

        # Create dependent parameters from CSV data if available
        dep_params = None
        if all(
            key in material_data
            for key in ["Ecm", "Epsc1", "Epsc2", "Epsc3", "Epscu1", "Epscu2", "Epscu3", "Fctm", "Fctk_0_05", "Fctk_0_95", "NFactor", "Fcm"]
        ):
            dep_params = idea_rcs.ConcDependentParams(
                E_cm=material_data["Ecm"],
                eps_c1=material_data["Epsc1"] * STRAIN_CONVERSION_FACTOR,  # Convert from 1e-4 to actual strain
                eps_c2=material_data["Epsc2"] * STRAIN_CONVERSION_FACTOR,
                eps_c3=material_data["Epsc3"] * STRAIN_CONVERSION_FACTOR,
                eps_cu1=material_data["Epscu1"] * STRAIN_CONVERSION_FACTOR,
                eps_cu2=material_data["Epscu2"] * STRAIN_CONVERSION_FACTOR,
                eps_cu3=material_data["Epscu3"] * STRAIN_CONVERSION_FACTOR,
                F_ctm=material_data["Fctm"],
                F_ctk_0_05=material_data["Fctk_0_05"],
                F_ctk_0_95=material_data["Fctk_0_95"],
                n_factor=material_data["NFactor"],
                F_cm=material_data["Fcm"],
            )

        # Create the material
        material_display_name = custom_name or f"{material_name} (Historical)"

        concrete_material = model.create_concrete_material(
            base_material=base_material,
            name=material_display_name,
            unit_mass=unit_mass,
            fck=fck,
            stone_diameter=stone_diameter,
            cement_class=cement_class,
            aggregate_type=aggregate_type,
            diagram_type=idea_rcs.ConcDiagramType.PARABOLIC,
            silica_fume=False,
            plain_concrete_diagram=False,
            dep_params=dep_params,
        )

    except KeyError as e:
        raise ValueError(f"Required parameter {e} not found in CSV data for material '{material_name}'")
    except Exception as e:
        raise ValueError(f"Error creating IDEA material for '{material_name}': {e}")
    else:
        return concrete_material
