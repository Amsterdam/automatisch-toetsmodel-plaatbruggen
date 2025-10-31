"""
Mapping module for IDEA RCS concrete and reinforcement materials.

This module provides mapping functions to convert material quality strings
from CSV files to IDEA RCS material enum values and create custom materials from CSV data.
"""

from viktor.external import idea_rcs


def get_idea_concrete_material(concrete_quality: str) -> idea_rcs.ConcreteMaterial:
    """
    Map concrete quality string to IDEA RCS ConcreteMaterial enum value.

    This function only handles modern Eurocode materials (C-class).
    For historical materials (K-class, B-class), use create_historical_concrete_material() instead.

    :param concrete_quality: Concrete quality string (e.g., "C30/37")
    :type concrete_quality: str
    :returns: IDEA RCS ConcreteMaterial enum value
    :rtype: idea_rcs.ConcreteMaterial
    :raises ValueError: If concrete quality is not supported or is a historical material
    """
    concrete_material_mapping = {
        # Modern Eurocode materials (C-class)
        "C12/15": idea_rcs.ConcreteMaterial.C12_15,
        "C16/20": idea_rcs.ConcreteMaterial.C16_20,
        "C20/25": idea_rcs.ConcreteMaterial.C20_25,
        "C25/30": idea_rcs.ConcreteMaterial.C25_30,
        "C30/37": idea_rcs.ConcreteMaterial.C30_37,
        "C35/45": idea_rcs.ConcreteMaterial.C35_45,
        "C40/50": idea_rcs.ConcreteMaterial.C40_50,
        "C45/55": idea_rcs.ConcreteMaterial.C45_55,
        "C50/60": idea_rcs.ConcreteMaterial.C50_60,
        "C55/67": idea_rcs.ConcreteMaterial.C55_67,
        "C60/75": idea_rcs.ConcreteMaterial.C60_75,
        "C70/85": idea_rcs.ConcreteMaterial.C70_85,
        "C80/95": idea_rcs.ConcreteMaterial.C80_95,
        "C90/105": idea_rcs.ConcreteMaterial.C90_105,
    }

    if concrete_quality not in concrete_material_mapping:
        # Check if it's a historical material
        if is_historical_material(concrete_quality):
            raise ValueError(
                f"Historical material '{concrete_quality}' detected. "
                f"Use create_historical_concrete_material() instead of get_idea_concrete_material()."
            )
        raise ValueError(
            f"Concrete quality '{concrete_quality}' is not supported. Available modern materials: {list(concrete_material_mapping.keys())}"
        )

    return concrete_material_mapping[concrete_quality]


def create_historical_concrete_material(model: idea_rcs.Model, concrete_quality: str, custom_name: str | None = None) -> idea_rcs.MatConcreteEc2:
    """
    Create an IDEA RCS concrete material from CSV data for historical materials.

    This function delegates to the material generator for the actual creation logic.

    :param model: IDEA RCS model instance
    :type model: idea_rcs.Model
    :param concrete_quality: Concrete quality string (e.g., "K150", "B25")
    :type concrete_quality: str
    :param custom_name: Optional custom name for the material
    :type custom_name: str
    :returns: Created IDEA RCS concrete material
    :rtype: idea_rcs.MatConcreteEc2
    :raises ValueError: If material is not supported or CSV data is invalid
    """
    # Import here to avoid circular imports
    from .idea_material_generator import create_idea_concrete_material

    if not is_historical_material(concrete_quality):
        raise ValueError(f"Material '{concrete_quality}' is not a historical material. Use get_idea_concrete_material() for modern materials.")

    return create_idea_concrete_material(model, concrete_quality, custom_name)


def create_concrete_material_for_idea(model: idea_rcs.Model, concrete_quality: str, custom_name: str | None = None) -> idea_rcs.MatConcreteEc2:
    """
    Unified function to create concrete materials for both modern and historical types.

    This is the recommended function to use in idea_interface.py as it handles both cases automatically.

    :param model: IDEA RCS model instance
    :type model: idea_rcs.Model
    :param concrete_quality: Concrete quality string (e.g., "C30/37", "K150", "B25")
    :type concrete_quality: str
    :param custom_name: Optional custom name for the material
    :type custom_name: str
    :returns: Created IDEA RCS concrete material
    :rtype: idea_rcs.MatConcreteEc2
    :raises ValueError: If material is not supported
    """
    if is_historical_material(concrete_quality):
        # Historical materials: create with CSV data
        return create_historical_concrete_material(model, concrete_quality, custom_name)
    # Modern materials: use standard enum
    try:
        base_material = get_idea_concrete_material(concrete_quality)
        return model.create_concrete_material(base_material, name=custom_name)
    except ValueError:
        raise ValueError(f"Concrete quality '{concrete_quality}' is not supported")


def is_historical_material(concrete_quality: str) -> bool:
    """
    Check if a concrete quality is a historical material that requires CSV data.

    Dynamically checks against materials loaded from CSV files.
    Accepts both old naming (without suffix) and new naming (with suffix).

    :param concrete_quality: Concrete quality string
    :type concrete_quality: str
    :returns: True if historical material, False otherwise
    :rtype: bool
    """
    # Get all supported materials
    all_materials = get_all_supported_materials()

    # Check if it's directly in the list (suffixed name)
    if all_materials.get(concrete_quality) == "historical":
        return True

    # Check if it's a base name by looking for any material that starts with this base name
    # This provides backward compatibility for old code using base names like "B45", "K150"
    for material_name, material_type in all_materials.items():
        if material_type == "historical" and material_name.startswith(concrete_quality + "_"):
            return True

    return False


def get_all_supported_materials() -> dict[str, str]:
    """
    Get all supported concrete materials with their types.

    Dynamically reads historical materials from CSV files, ensuring the list is always up-to-date.
    Modern materials are hardcoded as they are standard Eurocode materials.

    :returns: Dictionary mapping material names to types ('modern' or 'historical')
    :rtype: dict[str, str]
    """
    materials = {}

    # Modern materials (hardcoded - these are standard Eurocode materials)
    modern_materials = [
        "C12/15",
        "C16/20",
        "C20/25",
        "C25/30",
        "C30/37",
        "C35/45",
        "C40/50",
        "C45/55",
        "C50/60",
        "C55/67",
        "C60/75",
        "C70/85",
        "C80/95",
        "C90/105",
    ]
    for material in modern_materials:
        materials[material] = "modern"

    # Historical materials - read dynamically from CSV files
    try:
        from .constants.paths import IDEA_MATERIALS_PATH
        from .idea_material_generator import _get_csv_files_for_concrete

        csv_files = _get_csv_files_for_concrete("")  # Pass empty string (arg is ignored)
        for csv_file in csv_files:
            csv_path = IDEA_MATERIALS_PATH / csv_file
            if not csv_path.exists():
                continue

            # Read all material names from CSV
            with csv_path.open(encoding="utf-8") as f:
                lines = f.readlines()

                # Find the "Data" line
                data_start_idx = None
                for i, line in enumerate(lines):
                    if line.strip().startswith('"Data"'):
                        data_start_idx = i + 1
                        break

                if data_start_idx is None:
                    continue

                # Extract material names from data rows
                for line in lines[data_start_idx:]:
                    line = line.strip()
                    if not line:
                        continue

                    # Material name is the first field
                    parts = line.split(";")
                    if parts:
                        material_name = parts[0].strip('"')
                        if material_name:
                            # Only add the suffixed name from CSV
                            # Base names are NOT added to avoid showing duplicates in dropdowns
                            materials[material_name] = "historical"
    except Exception:
        # If CSV reading fails, return at least the modern materials
        pass

    return materials


def get_idea_reinforcement_material(reinforcement_type: str = "B500B") -> idea_rcs.ReinforcementMaterial:
    """
    Map modern reinforcement type string to IDEA RCS ReinforcementMaterial enum value.

    This function only handles modern Eurocode materials (B-class with letter suffix).
    For historical materials (FeB, HK, St.), use create_historical_reinforcement_material() instead.

    :param reinforcement_type: Reinforcement type string (e.g., "B500B")
    :type reinforcement_type: str
    :returns: IDEA RCS ReinforcementMaterial enum value
    :rtype: idea_rcs.ReinforcementMaterial
    :raises ValueError: If reinforcement type is not supported or is a historical material
    """
    reinforcement_material_mapping = {
        "B400A": idea_rcs.ReinforcementMaterial.B_400A,
        "B400B": idea_rcs.ReinforcementMaterial.B_400B,
        "B400C": idea_rcs.ReinforcementMaterial.B_400C,
        "B500A": idea_rcs.ReinforcementMaterial.B_500A,
        "B500B": idea_rcs.ReinforcementMaterial.B_500B,
        "B500C": idea_rcs.ReinforcementMaterial.B_500C,
        "B550A": idea_rcs.ReinforcementMaterial.B_550A,
        "B550B": idea_rcs.ReinforcementMaterial.B_550B,
        "B600A": idea_rcs.ReinforcementMaterial.B_600A,
        "B600B": idea_rcs.ReinforcementMaterial.B_600B,
        "B600C": idea_rcs.ReinforcementMaterial.B_600C,
    }

    if reinforcement_type not in reinforcement_material_mapping:
        # Check if it's a historical material
        if is_historical_reinforcement_material(reinforcement_type):
            raise ValueError(
                f"Historical material '{reinforcement_type}' detected. "
                f"Use create_historical_reinforcement_material() instead of get_idea_reinforcement_material()."
            )
        raise ValueError(
            f"Reinforcement type '{reinforcement_type}' is not supported. Available modern materials: {list(reinforcement_material_mapping.keys())}"
        )

    return reinforcement_material_mapping[reinforcement_type]


def create_historical_reinforcement_material(
    model: idea_rcs.Model,
    reinforcement_type: str,
    custom_name: str | None = None,
) -> idea_rcs.MatReinforcementEc2:
    """
    Create an IDEA RCS reinforcement material from CSV data for historical materials.

    This function delegates to the material generator for the actual creation logic.

    :param model: IDEA RCS model instance
    :type model: idea_rcs.Model
    :param reinforcement_type: Reinforcement type string (e.g., "FeB500 HWL, HK", "HK", "St. 37")
    :type reinforcement_type: str
    :param custom_name: Optional custom name for the material
    :type custom_name: str
    :returns: Created IDEA RCS reinforcement material
    :rtype: idea_rcs.MatReinforcementEc2
    :raises ValueError: If material is not supported or CSV data is invalid
    """
    # Import here to avoid circular imports
    from .idea_material_generator import create_idea_reinforcement_material

    if not is_historical_reinforcement_material(reinforcement_type):
        raise ValueError(
            f"Material '{reinforcement_type}' is not a historical reinforcement material. Use get_idea_reinforcement_material() for modern materials."
        )

    return create_idea_reinforcement_material(model, reinforcement_type, custom_name)


def create_reinforcement_material_for_idea(
    model: idea_rcs.Model,
    reinforcement_type: str,
    custom_name: str | None = None,
) -> idea_rcs.MatReinforcementEc2:
    """
    Unified function to create reinforcement materials for both modern and historical types.

    This is the recommended function to use in idea_interface.py as it handles both cases automatically.

    :param model: IDEA RCS model instance
    :type model: idea_rcs.Model
    :param reinforcement_type: Reinforcement type string (e.g., "B500B", "FeB500 HWL, HK", "HK", "St. 37")
    :type reinforcement_type: str
    :param custom_name: Optional custom name for the material
    :type custom_name: str
    :returns: Created IDEA RCS reinforcement material
    :rtype: idea_rcs.MatReinforcementEc2
    :raises ValueError: If material is not supported
    """
    if is_historical_reinforcement_material(reinforcement_type):
        # Historical materials: create with CSV data
        return create_historical_reinforcement_material(model, reinforcement_type, custom_name)
    # Modern materials: use standard enum
    try:
        base_material = get_idea_reinforcement_material(reinforcement_type)
        return model.create_reinforcement_material(base_material, name=custom_name)
    except ValueError:
        raise ValueError(f"Reinforcement type '{reinforcement_type}' is not supported")


def is_historical_reinforcement_material(reinforcement_type: str) -> bool:
    """
    Check if a reinforcement type is a historical material that requires CSV data.

    Dynamically checks against materials loaded from CSV files.
    Accepts both old naming (without suffix) and new naming (with suffix).

    :param reinforcement_type: Reinforcement type string
    :type reinforcement_type: str
    :returns: True if historical material, False otherwise
    :rtype: bool
    """
    # Get all supported materials
    all_materials = get_all_supported_reinforcement_materials()

    # Check if it's directly in the list (suffixed name)
    if all_materials.get(reinforcement_type) == "historical":
        return True

    # Check if it's a base name by looking for any material that starts with this base name + "_"
    # This provides backward compatibility for old code using base names like "QR22", "HK"
    # Use rsplit to handle names with spaces like "St. 37"
    for material_name, material_type in all_materials.items():
        if material_type == "historical":
            # Extract base name from suffixed material
            if "_" in material_name:
                base_name = material_name.rsplit("_", 1)[0]
                if base_name == reinforcement_type:
                    return True

    return False


def get_all_supported_reinforcement_materials() -> dict[str, str]:
    """
    Get all supported reinforcement materials with their types.

    Dynamically reads historical materials from CSV files, ensuring the list is always up-to-date.
    Modern materials are hardcoded as they are standard Eurocode materials.

    :returns: Dictionary mapping material names to types ('modern' or 'historical')
    :rtype: dict[str, str]
    """
    materials = {}

    # Modern materials (hardcoded - these are standard Eurocode materials)
    modern_materials = ["B400A", "B400B", "B400C", "B500A", "B500B", "B500C", "B550A", "B550B", "B600A", "B600B", "B600C"]
    for material in modern_materials:
        materials[material] = "modern"

    # Historical materials - read dynamically from CSV files
    try:
        from .constants.paths import IDEA_MATERIALS_PATH
        from .idea_material_generator import _get_csv_files_for_reinforcement

        csv_files = _get_csv_files_for_reinforcement()
        for csv_file in csv_files:
            csv_path = IDEA_MATERIALS_PATH / csv_file
            if not csv_path.exists():
                continue

            # Read all material names from CSV
            with csv_path.open(encoding="utf-8") as f:
                lines = f.readlines()

                # Find the "Data" line
                data_start_idx = None
                for i, line in enumerate(lines):
                    if line.strip().startswith('"Data"'):
                        data_start_idx = i + 1
                        break

                if data_start_idx is None:
                    continue

                # Extract material names from data rows
                for line in lines[data_start_idx:]:
                    line = line.strip()
                    if not line:
                        continue

                    # Material name is the first field
                    parts = line.split(";")
                    if parts:
                        material_name = parts[0].strip('"')
                        if material_name:
                            # Only add the suffixed name from CSV
                            # Base names are NOT added to avoid showing duplicates in dropdowns
                            materials[material_name] = "historical"
    except Exception:
        # If CSV reading fails, return at least the modern materials
        pass

    return materials

    return materials
