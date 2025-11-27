"""
Coordinate transformation and geometry utilities for SCIA integration.

This module provides pure utility functions for coordinate transformations,
zone geometry extraction, and load format conversions without circular dependencies.
"""

from math import radians, tan
from typing import Any, Protocol

from src.integrations.scia_integration.types import LoadType


class BridgeGeometryData(Protocol):
    """Protocol for bridge geometry data structure."""

    x_coords_d_points: list[float]
    y_bridge_bottom_at_d_points: list[float]
    y_top_structural_edge_at_d_points: list[float]


def convert_wheel_coordinates_to_3d(wheel_2d: list[list[float]]) -> list[tuple[float, float, float]]:
    """
    Convert 2D wheel coordinates to 3D coordinates for SCIA.

    :param wheel_2d: List of 2D wheel coordinates [[x1, y1], [x2, y2], ...]
    :returns: List of 3D coordinates [(x1, y1, 0), (x2, y2, 0), ...]
    """
    return [(x, y, 0.0) for x, y in wheel_2d]


def align_bridge_coordinates_to_scia(coords: list[tuple[float, float, float]], bridge_center_y: float = 0.0) -> list[tuple[float, float, float]]:
    """
    Align bridge coordinates to SCIA coordinate system.

    :param coords: List of 3D coordinates
    :param bridge_center_y: Y-coordinate of bridge center line
    :returns: List of aligned coordinates
    """
    return [(x, y + bridge_center_y, z) for x, y, z in coords]


def convert_loads_to_scia_format(load_data: list[dict[str, Any]], load_type: LoadType | str = LoadType.TANDEM) -> list[dict[str, Any]]:
    """
    Convert load data to SCIA-compatible format.

    :param load_data: Raw load data from generate_tandem_loads() or generate_udl_loads()
    :param load_type: Type of loads to convert (TANDEM or UDL)
    :returns: SCIA-formatted load cases
    :raises ValueError: When load_type is unsupported
    """
    # Convert string to enum if needed
    if isinstance(load_type, str):
        try:
            load_type = LoadType(load_type)
        except ValueError:
            raise ValueError(f"Invalid load_type '{load_type}'. Use 'tandem' or 'udl'") from None

    if load_type == LoadType.TANDEM:
        return _convert_tandem_to_scia(load_data)
    if load_type == LoadType.UDL:
        return _convert_udl_to_scia(load_data)
    raise ValueError(f"Unsupported load type: {load_type}")


def _convert_tandem_to_scia(load_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tandem load data to SCIA-compatible format."""
    scia_cases = []

    for tandem in load_data:
        patch_loads = []

        # New structure: wheels and load are directly on the tandem dict
        if "wheels" in tandem:
            # New structure: each tandem dict has wheels directly
            for wheel_2d in tandem.get("wheels", []):
                # Convert 2D wheel coordinates to 3D (add z=0)
                wheel_3d = convert_wheel_coordinates_to_3d(wheel_2d)
                aligned_coords = align_bridge_coordinates_to_scia(wheel_3d)

                patch_loads.append(
                    {
                        "corners": aligned_coords,
                        "load_value": tandem.get("load", 0.0),
                    }
                )
        else:
            # Legacy structure: loads array with nested wheels (for backward compatibility)
            for load in tandem.get("loads", []):
                for wheel_2d in load.get("wheels", []):
                    # Convert 2D wheel coordinates to 3D (add z=0)
                    wheel_3d = convert_wheel_coordinates_to_3d(wheel_2d)
                    aligned_coords = align_bridge_coordinates_to_scia(wheel_3d)

                    patch_loads.append(
                        {
                            "corners": aligned_coords,
                            "load_value": load.get("load", 0.0),
                        }
                    )

        scia_cases.append(
            {
                "load_case": tandem["load_case"],
                "patch_loads": patch_loads,
            }
        )

    return scia_cases


def _convert_udl_to_scia(load_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert UDL load data to SCIA-compatible format."""
    scia_cases = []

    for udl_load in load_data:
        # UDL loads already have polygon coordinates
        polygon_coords = udl_load.get("polygon", [])
        load_value = udl_load.get("load_value", 0.0)

        # Align coordinates to SCIA coordinate system
        aligned_coords = align_bridge_coordinates_to_scia(polygon_coords)

        patch_loads = [
            {
                "corners": aligned_coords,
                "load_value": load_value,
            }
        ]

        scia_cases.append(
            {
                "load_case": udl_load["load_case"],
                "patch_loads": patch_loads,
            }
        )

    return scia_cases


def extract_zone_boundaries(params: Any) -> dict[str, dict[str, float]]:  # noqa: ANN401
    """
    Extract zone boundaries for each segment.

    :param params: Bridge parameters
    :returns: Dictionary with zone boundaries per segment
    :raises IndexError: When no bridge segments are provided
    """
    if not params.bridge_segments_array:
        raise IndexError("No bridge segments provided")

    boundaries = {}

    for i, segment in enumerate(params.bridge_segments_array):
        segment_id = f"segment_{i + 1}"

        # Calculate zone boundaries from center line
        # Zone layout: Zone 3 | Zone 2 | Zone 1
        z1_left = segment.bz1 + segment.bz2 / 2
        z1_right = segment.bz2 / 2
        z3_left = -segment.bz2 / 2
        z3_right = -segment.bz3 - segment.bz2 / 2

        boundaries[segment_id] = {
            "z1_left": z1_left,
            "z1_right": z1_right,
            "z3_left": z3_left,
            "z3_right": z3_right,
        }

    return boundaries


# ------------------------------
# Deck zone geometry (between D-lines)
# ------------------------------


def get_bridge_deck_zone_coordinates(params: object) -> dict[str, list[list[float]]]:
    """
    Get coordinates of bridge deck zones spanning between segment boundaries.

    This function loops through ``bridge_segments_array`` starting from the second segment
    and creates zone polygons that span from the previous segment to the current segment.
    Each zone (zone_1, zone_2, zone_3) is defined by 4 corner coordinates forming a
    quadrilateral that transitions between different segment widths.

    :param params: Bridge parameters containing ``bridge_segments_array``
    :returns: Dictionary with zone names (zone_1_{n}, zone_2_{n}, zone_3_{n}) as keys
              and list of 4 corner coordinates [[x, y, z], ...] as values
    :raises IndexError: When no bridge segments are provided
    """
    bridge_segments = getattr(params, "bridge_segments_array", None)
    if not bridge_segments:
        raise IndexError("No bridge segments provided")

    zone_coordinates: dict[str, list[list[float]]] = {}
    cumulative_length = 0.0

    for segment_idx, segment in enumerate(bridge_segments[1:], start=1):
        x_start = cumulative_length
        cumulative_length += getattr(segment, "l", 0.0)
        x_end = cumulative_length

        # Current segment boundaries (Zone layout: Z3 | Z2 | Z1)
        z1_y_plus = segment.bz1 + segment.bz2 / 2
        z1_y_minus = segment.bz2 / 2
        z3_y_plus = -segment.bz2 / 2
        z3_y_minus = -segment.bz3 - segment.bz2 / 2

        prev_segment = bridge_segments[segment_idx - 1]
        prev_z1_y_plus = prev_segment.bz1 + prev_segment.bz2 / 2
        prev_z1_y_minus = prev_segment.bz2 / 2
        prev_z3_y_plus = -prev_segment.bz2 / 2

        z_coord = 0.0
        zone_num = segment_idx

        zone1_name = f"zone_1_{zone_num}"
        zone1_corners = [
            [x_start, prev_z1_y_plus, z_coord],
            [x_end, z1_y_plus, z_coord],
            [x_end, z1_y_minus, z_coord],
            [x_start, prev_z1_y_minus, z_coord],
        ]
        zone_coordinates[zone1_name] = zone1_corners

        zone2_name = f"zone_2_{zone_num}"
        zone2_corners = [
            [x_start, prev_z1_y_minus, z_coord],
            [x_end, z1_y_minus, z_coord],
            [x_end, z3_y_plus, z_coord],
            [x_start, prev_z3_y_plus, z_coord],
        ]
        zone_coordinates[zone2_name] = zone2_corners

        zone3_name = f"zone_3_{zone_num}"
        zone3_corners = [
            [x_start, prev_z3_y_plus, z_coord],
            [x_end, z3_y_plus, z_coord],
            [x_end, z3_y_minus, z_coord],
            [x_start, -prev_segment.bz3 - prev_segment.bz2 / 2, z_coord],
        ]
        zone_coordinates[zone3_name] = zone3_corners

    return zone_coordinates


def get_bridge_deck_zone_materials_and_thickness(params: object) -> dict[str, dict[str, Any]]:
    """
    Extract material and thickness information for bridge deck zones.

    This function loops through ``bridge_segments_array`` starting from the second segment
    and creates material/thickness data for zones that span from the previous segment
    to the current segment. Each zone (zone_1, zone_2, zone_3) gets material and
    individual D-line thickness properties from both segments. Uses the same zone naming
    convention as ``get_bridge_deck_zone_coordinates``.

    :param params: Bridge parameters containing ``bridge_segments_array``
    :returns: Dictionary with zone names as keys and material/thickness data as values
    :raises IndexError: When no bridge segments are provided
    """
    bridge_segments = getattr(params, "bridge_segments_array", None)
    if not bridge_segments:
        raise IndexError("No bridge segments provided")

    material_attr = getattr(params, "concrete_strength_class", None)
    applied_material = material_attr if isinstance(material_attr, str) and material_attr else "C40/50"
    zone_materials_thickness: dict[str, dict[str, Any]] = {}

    def _as_float(value: float | str | None) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    for segment_idx, segment in enumerate(bridge_segments[1:], start=1):
        zone_num = segment_idx
        prev_segment = bridge_segments[segment_idx - 1]

        prev_thickness_primary = _as_float(getattr(prev_segment, "dz", 0.0))
        curr_thickness_primary = _as_float(getattr(segment, "dz", 0.0))
        prev_thickness_secondary = _as_float(getattr(prev_segment, "dz_2", 0.0))
        curr_thickness_secondary = _as_float(getattr(segment, "dz_2", 0.0))
        distance_between_d_lines = getattr(segment, "l", 0.0)

        zone1_name = f"zone_1_{zone_num}"
        zone_materials_thickness[zone1_name] = {
            "material": applied_material,
            "thickness_start_d_line": prev_thickness_primary,
            "thickness_end_d_line": curr_thickness_primary,
            "distance_between_d_lines": distance_between_d_lines,
        }

        zone2_name = f"zone_2_{zone_num}"
        # Zone 2 uses the secondary (dz_2) thickness directly for dispersion calculations
        zone_materials_thickness[zone2_name] = {
            "material": applied_material,
            "thickness_start_d_line": prev_thickness_secondary,
            "thickness_end_d_line": curr_thickness_secondary,
            "distance_between_d_lines": distance_between_d_lines,
        }

        zone3_name = f"zone_3_{zone_num}"
        zone_materials_thickness[zone3_name] = {
            "material": applied_material,
            "thickness_start_d_line": prev_thickness_primary,
            "thickness_end_d_line": curr_thickness_primary,
            "distance_between_d_lines": distance_between_d_lines,
        }

    return zone_materials_thickness


# ------------------------------
# Load zone geometry (within deck zones)
# ------------------------------


def get_bridge_load_zone_coordinates(params: object) -> dict[str, list[list[float]]]:  # noqa: C901
    """
    Get coordinates of bridge load zones spanning between segment boundaries.

    This function creates load zone polygons based on the ``load_zones_data_array`` that span
    from one segment to the next. Each load zone uses the d{n}_width values to define its
    width at each D-point. Each zone is defined by 4 corner coordinates forming a
    quadrilateral that transitions between different zone widths across segments.

    :param params: Bridge parameters containing ``bridge_segments_array`` and ``load_zones_data_array``
    :returns: Dictionary with load zone names as keys and list of 4 corner coordinates [[x, y, z], ...]
    :raises IndexError: When no bridge segments or load zones are provided
    """
    bridge_segments = getattr(params, "bridge_segments_array", None)
    if not bridge_segments:
        raise IndexError("No bridge segments provided")
    load_zones = getattr(params, "load_zones_data_array", None)
    if not load_zones:
        raise IndexError("No bridge load zones provided")

    load_zone_coordinates: dict[str, list[list[float]]] = {}
    cumulative_length = 0.0

    for segment_idx, segment in enumerate(bridge_segments[1:], start=1):
        x_start = cumulative_length
        cumulative_length += getattr(segment, "l", 0.0)
        x_end = cumulative_length
        z_coord = 0.0

        prev_d_point = segment_idx
        curr_d_point = segment_idx + 1

        prev_segment = bridge_segments[segment_idx - 1]
        curr_segment = segment

        prev_y_max = prev_segment.bz1 + prev_segment.bz2 / 2
        curr_y_max = curr_segment.bz1 + curr_segment.bz2 / 2
        prev_y_min = -prev_segment.bz3 - prev_segment.bz2 / 2
        curr_y_min = -curr_segment.bz3 - curr_segment.bz2 / 2

        prev_y_pos = prev_y_max
        curr_y_pos = curr_y_max

        for zone_idx, load_zone in enumerate(load_zones):
            zone_name = f"load_zone_{zone_idx + 1}_{segment_idx}"
            is_last_zone = zone_idx == len(load_zones) - 1

            def _get_width_for_d(load_zone_obj: object, d_point: int, *, use_next_if_penultimate: bool = False) -> float:
                try:
                    wad = getattr(load_zone_obj, "width_at_d")
                    if isinstance(wad, (list, tuple)) and 1 <= d_point <= len(wad):
                        index = d_point - 1
                        if use_next_if_penultimate and index == len(wad) - 2:
                            index = min(index + 1, len(wad) - 1)
                        value = wad[index]
                        return float(value) if value is not None else 0.0
                except Exception:
                    pass
                value = getattr(load_zone_obj, f"d{d_point}_width", 0.0)
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0

            if is_last_zone:
                prev_width = prev_y_pos - prev_y_min
                curr_width = curr_y_pos - curr_y_min
            elif zone_idx == 1:
                prev_width = _get_width_for_d(load_zone, prev_d_point, use_next_if_penultimate=True)
                curr_width = _get_width_for_d(load_zone, curr_d_point, use_next_if_penultimate=True)
            else:
                prev_width = _get_width_for_d(load_zone, prev_d_point, use_next_if_penultimate=False)
                curr_width = _get_width_for_d(load_zone, curr_d_point, use_next_if_penultimate=False)

            prev_y_start = prev_y_pos
            prev_y_end = prev_y_pos - prev_width
            curr_y_start = curr_y_pos
            curr_y_end = curr_y_pos - curr_width

            zone_corners = [
                [x_start, prev_y_start, z_coord],
                [x_end, curr_y_start, z_coord],
                [x_end, curr_y_end, z_coord],
                [x_start, prev_y_end, z_coord],
            ]
            load_zone_coordinates[zone_name] = zone_corners

            prev_y_pos -= prev_width
            curr_y_pos -= curr_width

    return load_zone_coordinates


def get_bridge_load_zone_materials_and_thickness(params: object) -> dict[str, dict[str, Any]]:
    """
    Extract material and thickness information for bridge load zones.

    This function creates material/thickness data for load zones that span from one segment
    to the next. Each load zone gets material from its own pavement properties and thickness.

    :param params: Bridge parameters containing ``bridge_segments_array`` and ``load_zones_data_array``
    :returns: Dictionary with load zone names as keys and dict containing material and thickness info as values
    :raises IndexError: When no bridge segments or load zones are provided
    """
    bridge_segments = getattr(params, "bridge_segments_array", None)
    if not bridge_segments:
        raise IndexError("No bridge segments provided")
    load_zones = getattr(params, "load_zones_data_array", None)
    if not load_zones:
        raise IndexError("No bridge load zones provided")

    load_zone_materials_thickness: dict[str, dict[str, Any]] = {}

    for segment_idx in range(1, len(bridge_segments)):
        for zone_idx, load_zone in enumerate(load_zones):
            zone_name = f"load_zone_{zone_idx + 1}_{segment_idx}"

            # Extract pavement material and thickness from load zone data
            pavement_material = getattr(load_zone, "pavement_material", None)
            pavement_thickness = getattr(load_zone, "pavement_thickness", None)

            load_zone_materials_thickness[zone_name] = {
                "material": pavement_material,
                "thickness": pavement_thickness,
            }

    return load_zone_materials_thickness


# ------------------------------
# Point-in-polygon helper and property queries at coordinate
# ------------------------------


def _point_in_polygon(point_x: float, point_y: float, polygon_corners: list[list[float]]) -> bool:  # noqa: C901
    """
    Check if a point is inside a polygon using ray casting algorithm.

    :param point_x: X coordinate of the point
    :param point_y: Y coordinate of the point
    :param polygon_corners: List of polygon corner coordinates [[x, y, z], ...]
    :returns: True if point is inside polygon, False otherwise
    :rtype: bool
    """
    n = len(polygon_corners)
    inside = False

    def _point_on_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float, eps: float = 1e-9) -> bool:  # noqa: PLR0913
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) < eps and abs(dy) < eps:
            return abs(px - x1) < eps and abs(py - y1) < eps
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy) if (dx * dx + dy * dy) > eps else 0.0
        if t < -eps or t > 1.0 + eps:
            return False
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return abs(px - proj_x) < eps and abs(py - proj_y) < eps

    for vx, vy, _ in polygon_corners:
        if abs(point_x - vx) < 1e-9 and abs(point_y - vy) < 1e-9:
            return True

    for i in range(n):
        x1, y1 = polygon_corners[i][0], polygon_corners[i][1]
        x2, y2 = polygon_corners[(i + 1) % n][0], polygon_corners[(i + 1) % n][1]
        if _point_on_segment(point_x, point_y, x1, y1, x2, y2):
            return True

    p1x, p1y = polygon_corners[0][0], polygon_corners[0][1]
    for i in range(1, n + 1):
        p2x, p2y = polygon_corners[i % n][0], polygon_corners[i % n][1]
        if min(p1y, p2y) < point_y <= max(p1y, p2y) or abs(point_y - min(p1y, p2y)) < 1e-9:
            xinters = (point_y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x if p1y != p2y else p1x
            if point_x <= xinters or abs(point_x - xinters) < 1e-9:
                inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def get_deck_mat_and_thick_at_coord(params: object, coord: tuple[float, float, float] | list[float]) -> tuple[Any, float | None]:
    """
    Get the deck zone material and interpolated thickness at the given coordinate.

    :param params: Bridge parameters containing ``bridge_segments_array``
    :param coord: 3D coordinate (x, y, z) to search for (z-coordinate is ignored)
    :returns: Tuple of (material, interpolated_thickness) or (None, None) if not found
    :raises IndexError: When no bridge segments are provided
    :raises ValueError: When coord is not in the expected format
    """
    bridge_segments = getattr(params, "bridge_segments_array", None)
    if not bridge_segments:
        raise IndexError("No bridge segments provided")
    if not (isinstance(coord, (tuple, list)) and len(coord) == 3):
        raise ValueError("Coordinate must be a tuple or list of 3 values (x, y, z)")

    x, y, _ = coord
    deck_zones_coords = get_bridge_deck_zone_coordinates(params)
    deck_zones_materials = get_bridge_deck_zone_materials_and_thickness(params)

    for zone_name, zone_corners in deck_zones_coords.items():
        if _point_in_polygon(float(x), float(y), zone_corners):
            zone_data = deck_zones_materials[zone_name]
            x_start = zone_corners[0][0]
            x_end = zone_corners[1][0]
            thickness_start = zone_data["thickness_start_d_line"]
            thickness_end = zone_data["thickness_end_d_line"]
            if x_end != x_start:
                interpolation_factor = (float(x) - x_start) / (x_end - x_start)
                interpolation_factor = max(0.0, min(1.0, interpolation_factor))
            else:
                interpolation_factor = 0.0
            interpolated_thickness = thickness_start + interpolation_factor * (thickness_end - thickness_start)
            return (zone_data["material"], interpolated_thickness)

    return (None, None)


def get_load_mat_and_thick_at_coord(params: object, coord: tuple[float, float, float] | list[float]) -> tuple[Any, float | None]:
    """
    Get the load zone material and thickness at the given coordinate.

    :param params: Bridge parameters containing ``bridge_segments_array`` and ``load_zones_data_array``
    :param coord: 3D coordinate (x, y, z) to search for (z-coordinate is ignored)
    :returns: Tuple of (material, thickness) or (None, None) if not found
    :raises IndexError: When no bridge segments or load zones are provided
    :raises ValueError: When coord is not in the expected format
    """
    bridge_segments = getattr(params, "bridge_segments_array", None)
    if not bridge_segments:
        raise IndexError("No bridge segments provided")
    load_zones = getattr(params, "load_zones_data_array", None)
    if not load_zones:
        raise IndexError("No bridge load zones provided")
    if not (isinstance(coord, (tuple, list)) and len(coord) == 3):
        raise ValueError("Coordinate must be a tuple or list of 3 values (x, y, z)")

    x, y, _ = coord
    load_zones_coords = get_bridge_load_zone_coordinates(params)
    load_zones_materials = get_bridge_load_zone_materials_and_thickness(params)

    for zone_name, zone_corners in load_zones_coords.items():
        if _point_in_polygon(float(x), float(y), zone_corners):
            return (
                load_zones_materials[zone_name]["material"],
                load_zones_materials[zone_name]["thickness"],
            )

    return (None, None)


def move_polygon_to_bridge_boundaries(  # noqa: C901
    corner_points: list[tuple[float, float, float]], bridge_geom_data: BridgeGeometryData
) -> list[tuple[float, float, float]]:
    """
    Align a polygon with bridge deck boundaries without shrinking its surface.

    :param corner_points: List of 3D corner points [(x, y, z), ...]
    :param bridge_geom_data: Bridge geometry data containing boundary information
    :returns: Corner points translated (only in Y) so patches touch deck edges without clipping
    """
    if not corner_points:
        return corner_points

    # Extract bridge boundaries
    if not hasattr(bridge_geom_data, "x_coords_d_points"):
        return corner_points  # Return original if no geometry data

    # Get Y boundaries from bridge geometry
    y_min = bridge_geom_data.y_bridge_bottom_at_d_points[0]
    y_max = bridge_geom_data.y_top_structural_edge_at_d_points[0]

    y_values = [point[1] for point in corner_points]
    current_min = min(y_values)
    current_max = max(y_values)

    def _calculate_y_shift() -> float:
        """
        Determine how far the polygon must be translated in Y so it borders the deck edge
        without altering its size. Positive shift moves the polygon upwards (towards +Y).
        """
        if current_min >= y_min and current_max <= y_max:
            return 0.0
        if current_min < y_min and current_max <= y_max:
            return y_min - current_min
        if current_max > y_max and current_min >= y_min:
            return y_max - current_max

        # Polygon exceeds both edges; align centers to minimize truncation.
        polygon_mid = (current_min + current_max) / 2.0
        deck_mid = (y_min + y_max) / 2.0
        return deck_mid - polygon_mid

    y_shift = _calculate_y_shift()

    adjusted_points: list[tuple[float, float, float]] = []
    for x_coord, y_coord, z_coord in corner_points:
        new_y = y_coord + y_shift
        # Safety clamp to prevent floating point drift outside deck boundaries.
        if new_y < y_min:
            new_y = y_min
        elif new_y > y_max:
            new_y = y_max
        adjusted_points.append((x_coord, new_y, z_coord))

    return adjusted_points


def _get_material_dispersion_angle(material: str) -> int | None:
    """
    Get the dispersion angle for a given material.

    :param material: Material name
    :returns: Dispersion angle in degrees, or None if material not found
    """
    material_dispersion_angles: dict[str, int] = {
        "beton": 45,
        "asfalt": 45,
        "klinkers": 45,
        "grind": 35,
        "tegels": 45,
    }
    mat_str = str(material)
    starts_with_kbc_and_digit = len(mat_str) > 1 and mat_str[0] in "KBC" and mat_str[1].isdigit()
    if starts_with_kbc_and_digit or "Beton" in mat_str:
        return material_dispersion_angles["beton"]

    for key, value in material_dispersion_angles.items():
        if key.lower() in mat_str.lower():
            return value
    return None


def _calculate_dispersion_from_thickness(material: str | None, thickness: float | None) -> float | None:
    """
    Calculate horizontal dispersion distance based on material and thickness.

    :param material: Material name
    :param thickness: Thickness of the layer
    :returns: Horizontal dispersion distance, or None if invalid inputs
    """
    if material is None or thickness is None:
        return None

    angle_deg = _get_material_dispersion_angle(material)
    if angle_deg is not None:
        angle_rad = radians(angle_deg)
        return thickness * tan(angle_rad)
    return None


def _normalize_material_string(material: str | None) -> str | None:
    """
    Normalize material string for dispersion calculation.

    :param material: Material input (string or None)
    :returns: Normalized string or None
    """
    if material is None:
        return None
    return material if isinstance(material, str) else str(material)


def _interpolate_thickness_at_x(
    x: float,
    x_start: float,
    x_end: float,
    thickness_start: float,
    thickness_end: float,
) -> float:
    """
    Interpolate thickness at a given x-coordinate.

    :param x: X-coordinate for interpolation
    :param x_start: Starting x-coordinate
    :param x_end: Ending x-coordinate
    :param thickness_start: Thickness at start
    :param thickness_end: Thickness at end
    :returns: Interpolated thickness value
    """
    if x_end != x_start:
        interpolation_factor = (float(x) - x_start) / (x_end - x_start)
        interpolation_factor = max(0.0, min(1.0, interpolation_factor))
    else:
        interpolation_factor = 0.0
    return thickness_start + interpolation_factor * (thickness_end - thickness_start)


def _collect_deck_zone_dispersions(
    params: object,
    x: float,
    y: float,
) -> list[float]:
    """
    Collect dispersion values from all matching deck zones.

    :param params: Bridge parameters
    :param x: X-coordinate
    :param y: Y-coordinate
    :returns: List of dispersion values for matching deck zones
    """
    deck_zones_coords = get_bridge_deck_zone_coordinates(params)
    deck_zones_materials = get_bridge_deck_zone_materials_and_thickness(params)

    deck_dispersions = []
    for zone_name, zone_corners in deck_zones_coords.items():
        if _point_in_polygon(float(x), float(y), zone_corners):
            zone_data = deck_zones_materials[zone_name]
            x_start = zone_corners[0][0]
            x_end = zone_corners[1][0]
            thickness_start = zone_data["thickness_start_d_line"]
            thickness_end = zone_data["thickness_end_d_line"]

            interpolated_thickness = _interpolate_thickness_at_x(x, x_start, x_end, thickness_start, thickness_end)
            material = _normalize_material_string(zone_data["material"])
            dispersion = _calculate_dispersion_from_thickness(material, interpolated_thickness)

            if dispersion is not None:
                deck_dispersions.append(dispersion)

    return deck_dispersions if deck_dispersions else [0.0]


def _collect_load_zone_dispersions(
    params: object,
    x: float,
    y: float,
) -> list[float]:
    """
    Collect dispersion values from all matching load zones.

    :param params: Bridge parameters
    :param x: X-coordinate
    :param y: Y-coordinate
    :returns: List of dispersion values for matching load zones
    """
    load_zones_coords = get_bridge_load_zone_coordinates(params)
    load_zones_materials = get_bridge_load_zone_materials_and_thickness(params)

    load_dispersions = []
    for zone_name, zone_corners in load_zones_coords.items():
        if _point_in_polygon(float(x), float(y), zone_corners):
            material = _normalize_material_string(load_zones_materials[zone_name]["material"])
            thickness = load_zones_materials[zone_name]["thickness"]
            dispersion = _calculate_dispersion_from_thickness(material, thickness)

            if dispersion is not None:
                load_dispersions.append(dispersion)

    return load_dispersions if load_dispersions else [0.0]


def get_dispersion_at_coord(
    params: object,
    coord: tuple[float, float, float] | tuple[int, int, int] | list[float] | list[int],
) -> dict[str, list[float]]:
    """
    Calculate horizontal dispersion distances for deck and load zones at a coordinate.

    The function checks both deck and load zones at the specified coordinate and returns
    all matching horizontal dispersion distances for each zone type.

    When a coordinate is on the boundary between multiple zones (edge case),
    all dispersion values from matching zones are returned.

    :param params: Bridge parameters
    :param coord: 3D coordinate as a tuple (x, y, z) or list
    :returns: Dictionary with keys 'deck_zone' and 'load_zone', values are lists of horizontal dispersion distances
    :rtype: dict[str, list[float]]
    """
    if isinstance(coord, (list, tuple)) and len(coord) == 3:
        coord_f: tuple[float, float, float] = (float(coord[0]), float(coord[1]), float(coord[2]))
    else:
        coord_f = (0.0, 0.0, 0.0)

    x, y, _ = coord_f

    # Collect dispersion values for all matching zones
    deck_dispersions = _collect_deck_zone_dispersions(params, x, y)
    load_dispersions = _collect_load_zone_dispersions(params, x, y)

    return {"deck_zone": deck_dispersions, "load_zone": load_dispersions}
