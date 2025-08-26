"""
SCIA Force Envelope Extraction Module.

This module extracts maximum and minimum force values from SCIA analysis results,
along with the complete force state and location context for each extreme value.
"""

import contextlib
from typing import Any


def _initialize_envelopes() -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Initialize the envelope structure for all bridge sections and force components."""
    force_components = ["N", "Vy", "Vz", "Myd+", "Myd-", "Mxd+", "Mxd-"]
    bridge_sections = ["Z1_1", "Z2_1", "Z3_1"]

    envelopes = {}
    for section in bridge_sections:
        envelopes[section] = {
            component: {
                "max": {"value": float("-inf"), "forces": {}, "location": "", "combination": "", "element_id": ""},
                "min": {"value": float("inf"), "forces": {}, "location": "", "combination": "", "element_id": ""},
            }
            for component in force_components
        }
    return envelopes


def _extract_internal_forces_data(results: dict[str, Any]) -> dict[str, Any] | None:
    """Extract internal forces data from SCIA results."""
    xml_parsing = results.get("xml_parsing", {})
    if not isinstance(xml_parsing, dict):
        return None

    parsed_tables = xml_parsing.get("parsed_tables", {})

    # Try different internal forces table names
    for table_name in ["Interne 2D-krachten basis", "Interne 2D-krachten elementair", "Internal forces"]:
        table_data = parsed_tables.get(table_name, {})
        if table_data.get("status") == "success":
            return table_data.get("data", {})

    return None


def _extract_rows_from_internal_forces(internal_forces_data: dict[str, Any]) -> list[Any] | None:
    """Extract rows from internal forces data, handling various nested structures."""
    # Process force data rows - handle nested structure
    rows = None

    if hasattr(internal_forces_data, "rows"):
        rows = internal_forces_data.rows
    elif isinstance(internal_forces_data, dict) and "rows" in internal_forces_data:
        rows = internal_forces_data["rows"]
    elif isinstance(internal_forces_data, dict):
        # Try to find rows in nested structures
        for value in internal_forces_data.values():
            if hasattr(value, "rows"):
                rows = value.rows
                break
            if isinstance(value, dict) and "rows" in value:
                rows = value["rows"]
                break

    return rows


def _extract_column_data_from_internal_forces(internal_forces_data: dict[str, Any]) -> dict[str, Any] | None:
    """Extract column-based data structure from internal forces."""
    for value in internal_forces_data.values():
        if isinstance(value, dict) and any(force_field in value for force_field in ["m_x", "m_y", "v_x", "v_y", "n_x", "n_y"]):
            return value
    return None


def _process_force_data_rows(
    rows: list[Any], envelopes: dict[str, dict[str, dict[str, dict[str, Any]]]], combination_mapping: dict[str, str]
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Process force data rows and update envelopes with max/min values."""
    force_components = ["N", "Vy", "Vz", "Myd+", "Myd-", "Mxd+", "Mxd-"]

    for row in rows:
        # Extract force values and metadata
        force_values = _extract_force_values_from_row(row)
        if not force_values:
            continue

        metadata = _extract_row_metadata(row, combination_mapping)

        # Determine bridge section from metadata
        section = metadata["location"]
        if section not in envelopes:
            # If section not recognized, skip this row
            continue

        # Update envelopes for each force component in this section
        for component in force_components:
            if component in force_values:
                value = force_values[component]

                # Check for new maximum
                if value > envelopes[section][component]["max"]["value"]:
                    envelopes[section][component]["max"] = {
                        "value": value,
                        "forces": force_values.copy(),
                        "location": metadata["location"],
                        "combination": metadata["combination"],
                        "element_id": metadata["element_id"],
                    }

                # Check for new minimum
                if value < envelopes[section][component]["min"]["value"]:
                    envelopes[section][component]["min"] = {
                        "value": value,
                        "forces": force_values.copy(),
                        "location": metadata["location"],
                        "combination": metadata["combination"],
                        "element_id": metadata["element_id"],
                    }

    return envelopes


def extract_force_envelopes(results: dict[str, Any]) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """
    Extract force envelopes (max/min values with context) from SCIA analysis results.

    For each bridge section and force component, finds:
    - Maximum value + complete force state + location + load combination
    - Minimum value + complete force state + location + load combination

    :param results: SCIA analysis results dictionary
    :return: Force envelopes dictionary with structure:
        {
            "Z1_1": {
                "N": {
                    "max": {"value": float, "forces": dict, "location": str, "combination": str, "element_id": str},
                    "min": {"value": float, "forces": dict, "location": str, "combination": str, "element_id": str}
                },
                "Vy": { ... },
                # ... etc for all force components
            },
            "Z2_1": { ... },
            "Z3_1": { ... }
        }
    """
    # Initialize envelope structure
    envelopes = _initialize_envelopes()

    # Extract internal forces data
    internal_forces_data = _extract_internal_forces_data(results)
    if not internal_forces_data:
        return envelopes

    # Process force data rows - handle nested structure
    rows = _extract_rows_from_internal_forces(internal_forces_data)

    if rows is None:
        # Try to handle column-based data structure
        column_data = _extract_column_data_from_internal_forces(internal_forces_data)
        if column_data is None:
            return envelopes

        # Convert column data to row-like structure for processing
        rows = _convert_columns_to_rows(column_data)

    # Extract load combination mapping from result classes
    combination_mapping = _extract_combination_mapping(results)

    # Process force data rows and update envelopes
    return _process_force_data_rows(rows, envelopes, combination_mapping)


def _convert_columns_to_rows(column_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert column-based data structure to row-based structure.

    Input: {'m_x': [val1, val2, ...], 'm_y': [val1, val2, ...], 'Naam': [name1, name2, ...]}
    Output: [{'m_x': val1, 'm_y': val1, 'Naam': name1}, {'m_x': val2, 'm_y': val2, 'Naam': name2}, ...]
    """
    if not column_data:
        return []

    # Get the length of data (assume all columns have same length)
    first_column = next(iter(column_data.values()))
    if not isinstance(first_column, (list, tuple)):
        # If it's not a list/tuple, treat as single value
        return [column_data]

    num_rows = len(first_column)
    print(f"DEBUG: Converting {num_rows} rows from {len(column_data)} columns")  # noqa: T201

    rows = []
    for i in range(num_rows):
        row = {}
        for column_name, column_values in column_data.items():
            if isinstance(column_values, (list, tuple)) and i < len(column_values):
                row[column_name] = column_values[i]
            else:
                row[column_name] = column_values  # Single value
        rows.append(row)

    return rows


def _extract_single_force_value(get_row_value_func: Any, row: Any, field_name: str) -> float | None:  # noqa: ANN401
    """Extract a single force value from a row, handling conversion errors."""
    val = get_row_value_func(row, field_name)
    if val is not None and val != "":
        with contextlib.suppress(ValueError, TypeError):
            return float(val)
    return None


def _extract_normal_forces(get_row_value_func: Any, row: Any) -> dict[str, float]:  # noqa: ANN401
    """Extract normal forces (N) from a row."""
    force_values = {}

    # Try different normal force fields and use the dominant one
    n_values = []
    for field in ["n_x", "n_y", "n_xy", "n_xD", "n_yD", "n_cD"]:
        val = _extract_single_force_value(get_row_value_func, row, field)
        if val is not None:
            n_values.append(abs(val))

    if n_values:
        force_values["N"] = max(n_values)

    return force_values


def _extract_shear_forces(get_row_value_func: Any, row: Any) -> dict[str, float]:  # noqa: ANN401
    """Extract shear forces (Vy, Vz) from a row."""
    force_values = {}

    # Vy = v_y (shear force in Y direction)
    val = _extract_single_force_value(get_row_value_func, row, "v_y")
    if val is not None:
        force_values["Vy"] = val

    # Vz = v_x (shear force in X direction, mapped to Vz for consistency)
    val = _extract_single_force_value(get_row_value_func, row, "v_x")
    if val is not None:
        force_values["Vz"] = val

    return force_values


def _extract_moment_forces(get_row_value_func: Any, row: Any) -> dict[str, float]:  # noqa: ANN401, C901
    """Extract moment forces (Mxd+, Mxd-, Myd+, Myd-) from a row."""
    force_values = {}

    # Mxd+ and Mxd- (design moments in X direction)
    val = _extract_single_force_value(get_row_value_func, row, "m_xD+")
    if val is not None:
        force_values["Mxd+"] = val
    else:
        val = _extract_single_force_value(get_row_value_func, row, "m_x")
        if val is not None:
            force_values["Mxd+"] = max(0, val)  # Positive part

    val = _extract_single_force_value(get_row_value_func, row, "m_xD-")
    if val is not None:
        force_values["Mxd-"] = val
    elif "Mxd+" not in force_values:
        val = _extract_single_force_value(get_row_value_func, row, "m_x")
        if val is not None:
            force_values["Mxd-"] = abs(min(0, val))  # Negative part (as positive)

    # Myd+ and Myd- (design moments in Y direction)
    val = _extract_single_force_value(get_row_value_func, row, "m_yD+")
    if val is not None:
        force_values["Myd+"] = val
    else:
        val = _extract_single_force_value(get_row_value_func, row, "m_y")
        if val is not None:
            force_values["Myd+"] = max(0, val)  # Positive part

    val = _extract_single_force_value(get_row_value_func, row, "m_yD-")
    if val is not None:
        force_values["Myd-"] = val
    elif "Myd+" not in force_values:
        val = _extract_single_force_value(get_row_value_func, row, "m_y")
        if val is not None:
            force_values["Myd-"] = abs(min(0, val))  # Negative part (as positive)

    return force_values


def _extract_force_values_from_row(row: Any) -> dict[str, float]:  # noqa: ANN401, C901, PLR0912, PLR0915
    """
    Extract force values from a SCIA results row.

    Maps SCIA field names to standardized force component names based on actual XML structure.
    Uses both basic quantities (m_x, m_y, v_x, v_y, n_x, n_y) and design quantities (m_xD+, m_xD-, etc.)
    """
    force_values = {}

    try:
        # Debug: Check what fields are actually available
        available_force_fields = []
        for field in ["n_x", "n_y", "n_xy", "n_xD", "n_yD", "n_cD", "v_x", "v_y", "m_x", "m_y", "m_xD+", "m_xD-", "m_yD+", "m_yD-"]:
            if hasattr(row, field):
                val = getattr(row, field)
                available_force_fields.append(f"{field}={val}")

        # Helper function to get value from row (handles both dict and object)
        def get_row_value(row_obj: Any, field_name: str) -> Any:  # noqa: ANN401
            if isinstance(row_obj, dict):
                return row_obj.get(field_name)
            return getattr(row_obj, field_name, None)

        # Extract normal forces (use dominant component from n_x, n_y, n_xy)
        n_values = []
        for field in ["n_x", "n_y", "n_xy", "n_xD", "n_yD", "n_cD"]:
            val = get_row_value(row, field)
            if val is not None and val != "":
                try:
                    n_values.append(float(val))
                except (ValueError, TypeError):
                    continue
        if n_values:
            force_values["N"] = max(n_values, key=abs)  # Use component with largest magnitude

        # Extract shear forces
        # Vy = v_y (shear force in Y direction)
        val = get_row_value(row, "v_y")
        if val is not None and val != "":
            with contextlib.suppress(ValueError, TypeError):
                force_values["Vy"] = float(val)

        # Vz = v_x (shear force in X direction, mapped to Vz for consistency)
        val = get_row_value(row, "v_x")
        if val is not None and val != "":
            with contextlib.suppress(ValueError, TypeError):
                force_values["Vz"] = float(val)

        # Extract moments - try design quantities first, then basic quantities
        # Mxd+ and Mxd- (design moments in X direction)
        val = get_row_value(row, "m_xD+")
        if val is not None and val != "":
            with contextlib.suppress(ValueError, TypeError):
                force_values["Mxd+"] = float(val)
        else:
            val = get_row_value(row, "m_x")
            if val is not None and val != "":
                try:
                    moment_x = float(val)
                    force_values["Mxd+"] = max(0, moment_x)  # Positive part
                except (ValueError, TypeError):
                    pass

        val = get_row_value(row, "m_xD-")
        if val is not None and val != "":
            with contextlib.suppress(ValueError, TypeError):
                force_values["Mxd-"] = float(val)
        elif "Mxd+" not in force_values:
            val = get_row_value(row, "m_x")
            if val is not None and val != "":
                try:
                    moment_x = float(val)
                    force_values["Mxd-"] = min(0, moment_x)  # Negative part
                except (ValueError, TypeError):
                    pass

        # Myd+ and Myd- (design moments in Y direction)
        val = get_row_value(row, "m_yD+")
        if val is not None and val != "":
            with contextlib.suppress(ValueError, TypeError):
                force_values["Myd+"] = float(val)
        else:
            val = get_row_value(row, "m_y")
            if val is not None and val != "":
                try:
                    moment_y = float(val)
                    force_values["Myd+"] = max(0, moment_y)  # Positive part
                except (ValueError, TypeError):
                    pass

        val = get_row_value(row, "m_yD-")
        if val is not None and val != "":
            with contextlib.suppress(ValueError, TypeError):
                force_values["Myd-"] = float(val)
        elif "Myd+" not in force_values:
            val = get_row_value(row, "m_y")
            if val is not None and val != "":
                try:
                    moment_y = float(val)
                    force_values["Myd-"] = min(0, moment_y)  # Negative part
                except (ValueError, TypeError):
                    pass

    except (ValueError, TypeError, AttributeError):
        # Skip rows with invalid data
        pass

    # Debug: Show what was found (only for first few rows)
    if len(available_force_fields) > 0 and not force_values:
        # Only show debug for rows that have fields but no extracted values
        pass  # Will be logged by calling function

    return force_values


def _extract_row_metadata(row: Any, combination_mapping: dict[str, str]) -> dict[str, str]:  # noqa: ANN401, C901, PLR0912
    """Extract metadata (location, combination, element) from a SCIA results row."""
    metadata = {"location": "Unknown", "combination": "Unknown", "element_id": "Unknown"}

    # Helper function to get value from row (handles both dict and object)
    def get_row_value(row_obj: Any, field_name: str) -> Any:  # noqa: ANN401
        if isinstance(row_obj, dict):
            return row_obj.get(field_name)
        return getattr(row_obj, field_name, None)

    try:
        # Extract element/location information
        element_name = (
            get_row_value(row, "element_name")
            or get_row_value(row, "element_id")
            or get_row_value(row, "plate_name")
            or get_row_value(row, "Naam")  # Dutch name field
            or "Unknown"
        )
        metadata["element_id"] = str(element_name)

        # Extract location/zone information
        location = get_row_value(row, "location") or get_row_value(row, "zone")

        if location:
            metadata["location"] = str(location)
        else:
            # Try to derive location from element name or coordinates
            element_name_str = str(element_name)
            if "Z1" in element_name_str:
                metadata["location"] = "Z1_1"
            elif "Z2" in element_name_str:
                metadata["location"] = "Z2_1"
            elif "Z3" in element_name_str:
                metadata["location"] = "Z3_1"
            else:
                # Try to derive from coordinates if available
                x_coord = get_row_value(row, "x")
                if x_coord is not None:
                    try:
                        x_val = float(x_coord)
                        # Rough mapping based on X coordinate (adjust as needed)
                        if x_val < 10:
                            metadata["location"] = "Z1_1"
                        elif x_val < 20:
                            metadata["location"] = "Z2_1"
                        else:
                            metadata["location"] = "Z3_1"
                    except (ValueError, TypeError):
                        metadata["location"] = "Z1_1"  # Default fallback
                else:
                    metadata["location"] = "Z1_1"  # Default fallback

        # Extract load combination information
        combination_id = (
            get_row_value(row, "load_combination")
            or get_row_value(row, "load_case")
            or get_row_value(row, "combination_id")
            or get_row_value(row, "Belasting")
        )  # Dutch load field

        if combination_id is not None:
            combination_id = str(combination_id)
            # Try to map ID to combination name
            metadata["combination"] = combination_mapping.get(combination_id, combination_id)

    except (AttributeError, TypeError):
        pass

    return metadata


def _extract_combination_mapping(results: dict[str, Any]) -> dict[str, str]:
    """
    Extract mapping from combination IDs to combination names from result classes.

    Uses the result class data we successfully parsed to create ID -> name mapping.
    """
    mapping: dict[str, str] = {}

    xml_parsing = results.get("xml_parsing", {})
    if not isinstance(xml_parsing, dict):
        return mapping

    parsed_tables = xml_parsing.get("parsed_tables", {})

    # Extract combinations from all result classes
    for table_name, table_data in parsed_tables.items():
        if "Resultaatklasses" in table_name and table_data.get("status") == "success":
            data = table_data.get("data", {})
            if isinstance(data, dict) and "load_combinations" in data:
                combinations = data["load_combinations"]
                for combo in combinations:
                    combo_id = combo.get("id", "")
                    combo_name = combo.get("name", "")
                    if combo_id and combo_name:
                        mapping[combo_id] = combo_name

    return mapping


def get_force_envelope_summary(envelopes: dict[str, dict[str, dict[str, dict[str, Any]]]]) -> dict[str, Any]:
    """
    Generate a summary of the force envelopes for easy overview.

    :param envelopes: Force envelopes dictionary from extract_force_envelopes() (per section)
    :return: Summary dictionary with key statistics
    """
    summary: dict[str, Any] = {"total_sections": len(envelopes), "sections": {}, "critical_locations": {}, "critical_combinations": {}}

    location_counts: dict[str, int] = {}
    combination_counts: dict[str, int] = {}

    for section, section_envelopes in envelopes.items():
        section_summary: dict[str, Any] = {"components": {}, "total_components": len(section_envelopes)}

        for component, envelope in section_envelopes.items():
            max_data = envelope["max"]
            min_data = envelope["min"]

            # Component summary for this section
            section_summary["components"][component] = {
                "max_value": max_data["value"],
                "min_value": min_data["value"],
                "range": max_data["value"] - min_data["value"] if max_data["value"] != float("-inf") and min_data["value"] != float("inf") else 0,
                "max_location": max_data["location"],
                "min_location": min_data["location"],
                "max_combination": max_data["combination"],
                "min_combination": min_data["combination"],
            }

            # Count critical locations and combinations (only for valid data)
            if max_data["value"] != float("-inf") and min_data["value"] != float("inf"):
                for extreme in [max_data, min_data]:
                    location = extreme["location"]
                    combination = extreme["combination"]

                    location_counts[location] = location_counts.get(location, 0) + 1
                    combination_counts[combination] = combination_counts.get(combination, 0) + 1

        summary["sections"][section] = section_summary

    # Most critical locations and combinations across all sections
    summary["critical_locations"] = dict(sorted(location_counts.items(), key=lambda x: x[1], reverse=True))
    summary["critical_combinations"] = dict(sorted(combination_counts.items(), key=lambda x: x[1], reverse=True))

    return summary


def format_force_envelope_report(envelopes: dict[str, dict[str, dict[str, Any]]]) -> str:
    """
    Format force envelopes into a readable text report.

    :param envelopes: Force envelopes dictionary from extract_force_envelopes()
    :return: Formatted text report
    """
    lines = []
    lines.append("SCIA FORCE ENVELOPE ANALYSIS")
    lines.append("=" * 50)
    lines.append("")

    for component, envelope in envelopes.items():
        lines.append(f"{component} Force Envelope:")
        lines.append("-" * 30)

        # Maximum
        max_data = envelope["max"]
        lines.append(f"  Maximum: {max_data['value']:.2f}")
        lines.append(f"    Location: {max_data['location']}")
        lines.append(f"    Combination: {max_data['combination']}")
        lines.append(f"    Element: {max_data['element_id']}")
        lines.append("    Complete Force State:")
        for force_name, force_value in max_data["forces"].items():
            lines.append(f"      {force_name}: {force_value:.2f}")

        lines.append("")

        # Minimum
        min_data = envelope["min"]
        lines.append(f"  Minimum: {min_data['value']:.2f}")
        lines.append(f"    Location: {min_data['location']}")
        lines.append(f"    Combination: {min_data['combination']}")
        lines.append(f"    Element: {min_data['element_id']}")
        lines.append("    Complete Force State:")
        for force_name, force_value in min_data["forces"].items():
            lines.append(f"      {force_name}: {force_value:.2f}")

        lines.append("")
        lines.append("")

    return "\n".join(lines)
