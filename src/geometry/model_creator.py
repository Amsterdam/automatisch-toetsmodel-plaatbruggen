"""
Provides functions for creating 3D geometric models, including boxes, axes,
and cross-sections, using the `trimesh` library. It also includes functionality for
generating a 3D representation of a bridge deck based on input parameters.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import trimesh
from munch import Munch  # type: ignore[import-untyped]


# Function to create a box by specifying its vertices and faces
def create_box(vertices: np.ndarray, color: list) -> trimesh.Trimesh:
    """
    Create a box mesh from specified vertices.

    Args:
        vertices (np.ndarray): Array of 8 vertices (corners of the box) as [x, y, z].
        color (list): RGBA color for the box (single color).

    Returns:
        trimesh.Trimesh: A trimesh object representing the box.

    """
    # Define faces using vertex indices (triangles)
    faces = np.array(
        [
            # Bottom face
            [0, 1, 2],
            [0, 2, 3],
            # Top face
            [4, 5, 6],
            [4, 6, 7],
            # Front face
            [0, 1, 5],
            [0, 5, 4],
            # Back face
            [3, 2, 6],
            [3, 6, 7],
            # Left face
            [0, 3, 7],
            [0, 7, 4],
            # Right face
            [1, 2, 6],
            [1, 6, 5],
        ]
    )
    # Create the mesh
    box_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

    # Assign the same color to all faces
    box_mesh.visual.face_colors = np.array([color] * len(box_mesh.faces))
    return box_mesh


# Helper functions to create rebars and reinforcement meshes
def parse_zone_number(zone_numbers: list[str] | str) -> list[tuple[int, int]]:
    """
    Parse zone numbers into a list of (position, segment) tuples.

    Args:
        zone_numbers: Either a single zone number string or a list of zone number strings
                    in the format "X-Y" where X is the position (1,2,3) and Y is the segment number.

    Returns:
        A list of tuples where each tuple contains (position, segment_index).
        Position is 1, 2, or 3, and segment_index is 0-based.

    """
    if isinstance(zone_numbers, str):
        zone_numbers = [zone_numbers]

    result = []
    for zone in zone_numbers:
        pos, seg = map(int, zone.split("-"))
        if 1 <= pos <= 3 and seg > 0:  # Validate position and segment
            result.append((pos, seg - 1))  # Convert to 0-based segment index
    return result


def create_rebars(params: Munch, color: list) -> trimesh.Trimesh:  # noqa: C901, PLR0915, PLR0912
    """Create a mesh representing rebars based on specified parameters."""

    def get_zone_dimensions(position: int, segment_idx: int) -> dict:
        """Get geometric dimensions for a zone based on its position and segment."""
        segment_data = bridge_segments_array[segment_idx]
        next_segment_data = bridge_segments_array[segment_idx + 1]

        # Get the zone widths at the start and end of the segment
        bz = getattr(segment_data, f"bz{position}")
        bz_next = getattr(next_segment_data, f"bz{position}")

        # For position 2 (middle zone), use bz2 for both height and width
        if position == 2:
            height_start = segment_data.bz2
            height_end = next_segment_data.bz2
        else:
            height_start = bz
            height_end = bz_next

        return {"bz": bz, "bz_next": bz_next, "height_start": height_start, "height_end": height_end, "length": next_segment_data.l}

    def get_zone_parameters(zone_entry: Munch) -> dict:
        """Get all parameters for a specific zone."""
        params = {
            "zone_number": zone_entry.zone_number,
            # Main reinforcement parameters
            "diam_long_bottom": zone_entry.hoofdwapening_langs_onder_diameter / 1000,
            "hoh_long_bottom": zone_entry.hoofdwapening_langs_onder_hart_op_hart / 1000,
            "diam_long_top": zone_entry.hoofdwapening_langs_boven_diameter / 1000,
            "hoh_long_top": zone_entry.hoofdwapening_langs_boven_hart_op_hart / 1000,
            "diam_shear_top": zone_entry.hoofdwapening_dwars_boven_diameter / 1000,
            "hoh_shear_top": zone_entry.hoofdwapening_dwars_boven_hart_op_hart / 1000,
            "diam_shear_bottom": zone_entry.hoofdwapening_dwars_onder_diameter / 1000,
            "hoh_shear_bottom": zone_entry.hoofdwapening_dwars_onder_hart_op_hart / 1000,
        }

        # Add additional reinforcement parameters if present
        if zone_entry.heeft_bijlegwapening:
            params.update(
                {
                    "heeft_bijlegwapening": True,
                    "bijleg_diam_long_bottom": zone_entry.bijlegwapening_langs_onder_diameter / 1000,
                    "bijleg_hoh_long_bottom": zone_entry.hoofdwapening_langs_onder_hart_op_hart / 1000,  # Same as main reinforcement
                    "bijleg_diam_long_top": zone_entry.bijlegwapening_langs_boven_diameter / 1000,
                    "bijleg_hoh_long_top": zone_entry.hoofdwapening_langs_boven_hart_op_hart / 1000,  # Same as main reinforcement
                    "bijleg_diam_shear_bottom": zone_entry.bijlegwapening_dwars_onder_diameter / 1000,
                    "bijleg_hoh_shear_bottom": zone_entry.hoofdwapening_dwars_onder_hart_op_hart / 1000,  # Same as main reinforcement
                    "bijleg_diam_shear_top": zone_entry.bijlegwapening_dwars_boven_diameter / 1000,
                    "bijleg_hoh_shear_top": zone_entry.hoofdwapening_dwars_boven_hart_op_hart / 1000,  # Same as main reinforcement
                }
            )

        return params

    def get_cumulative_distance(segment_idx: int) -> float:
        """Calculate the cumulative distance to the start of a segment."""
        total_distance = 0.0
        for i in range(segment_idx):
            # The l parameter in each segment defines the distance to the next segment
            total_distance += bridge_segments_array[i + 1].l
        return total_distance

    def calculate_effective_widths(zone_params: dict, zone_dims: dict) -> dict:
        """Calculate effective widths for rebar placement."""
        return {
            "long_bottom": float(zone_dims["bz"]) - 2 * dekking_onder - zone_params["diam_long_bottom"],
            "long_top": float(zone_dims["bz"]) - 2 * dekking_boven - zone_params["diam_long_top"],
            "shear_bottom": zone_dims["length"] - 2 * dekking_onder - zone_params["diam_shear_bottom"],
            "shear_top": zone_dims["length"] - 2 * dekking_boven - zone_params["diam_shear_top"],
        }

    def calculate_z_positions(is_middle_zone: bool, zone_params: dict) -> dict:
        """Calculate z positions for reinforcement based on configuration."""
        pos = {}
        if langswapening_buiten:
            # Bottom configuration - longitudinal outside, shear inside
            pos["long_bottom"] = z_position_bottom + dekking_onder + 0.5 * zone_params["diam_long_bottom"]
            pos["shear_bottom"] = pos["long_bottom"] + 0.5 * (zone_params["diam_long_bottom"] + zone_params["diam_shear_bottom"])

            # Top configuration - longitudinal outside, shear inside
            if is_middle_zone:
                pos["long_top"] = z_position_top - (dekking_boven + 0.5 * zone_params["diam_long_top"])
            else:
                pos["long_top"] = -(dekking_boven + 0.5 * zone_params["diam_long_top"])
            pos["shear_top"] = pos["long_top"] - 0.5 * (zone_params["diam_long_top"] + zone_params["diam_shear_top"])
        else:
            # Bottom configuration - shear outside, longitudinal inside
            pos["shear_bottom"] = z_position_bottom + dekking_onder + 0.5 * zone_params["diam_shear_bottom"]
            pos["long_bottom"] = pos["shear_bottom"] + 0.5 * (zone_params["diam_shear_bottom"] + zone_params["diam_long_bottom"])

            # Top configuration - shear outside, longitudinal inside
            if is_middle_zone:
                pos["shear_top"] = z_position_top - (dekking_boven + 0.5 * zone_params["diam_shear_top"])
            else:
                pos["shear_top"] = -(dekking_boven + 0.5 * zone_params["diam_shear_top"])
            pos["long_top"] = pos["shear_top"] - 0.5 * (zone_params["diam_shear_top"] + zone_params["diam_long_top"])

        return pos

    def calculate_y_offset(position: int, segment_idx: int) -> float:
        """Calculate y offset for a zone."""
        bz2 = bridge_segments_array[segment_idx].bz2
        zone_dim = get_zone_dimensions(position, segment_idx)

        if position == 1:  # Left zone
            return bz2 / 2 + zone_dim["bz"] / 2
        if position == 3:  # Right zone
            return -(bz2 / 2 + zone_dim["bz"] / 2)
        return 0  # Middle zone

    def calculate_rebar_positions(width: float, hoh: float, y_offset: float = 0) -> list[float]:
        """Calculate positions for longitudinal reinforcement."""
        n_rebars = int(width / hoh)  # Round down to ensure minimum hoh is maintained
        if n_rebars < 1:
            return []

        actual_hoh = width / n_rebars
        positions = []

        if n_rebars % 2 == 0:  # Even number of rebars
            for i in range(n_rebars // 2):
                offset = (i + 0.5) * actual_hoh
                positions.extend([-offset, offset])
        else:  # Odd number of rebars
            positions = [0]  # Center rebar
            for i in range(1, (n_rebars + 1) // 2):
                offset = i * actual_hoh
                positions.extend([-offset, offset])

        positions.sort()
        return [pos + y_offset for pos in positions]

    def calculate_bijleg_positions(positions: list[float], y_offset: float = 0) -> list[float]:
        """Calculate positions for bijlegwapening (additional reinforcement) by finding midpoints between main reinforcement."""
        if len(positions) < 2:
            return []

        # Calculate midpoint between each pair of consecutive positions
        bijleg_positions = []
        for i in range(len(positions) - 1):
            midpoint = (positions[i] + positions[i + 1]) / 2.0
            bijleg_positions.append(midpoint)

        # Add y_offset to all positions
        return [pos + y_offset for pos in bijleg_positions]

    def get_shear_positions(width_eff: float, hoh: float, diameter_shear: float) -> list[float]:
        """Calculate positions for shear reinforcement."""
        n_rebars = int(width_eff / hoh)
        if n_rebars < 1:
            return []

        actual_hoh = width_eff / n_rebars
        start_offset = min(dekking_boven, dekking_onder) + 0.5 * diameter_shear
        mid_x = width_eff / 2 + start_offset
        positions = []

        if n_rebars % 2 == 0:
            for i in range(n_rebars // 2):
                x_offset = (i + 0.5) * actual_hoh
                positions.extend([mid_x - x_offset, mid_x + x_offset])
        else:
            positions = [mid_x]
            for i in range(1, (n_rebars + 1) // 2):
                x_offset = i * actual_hoh
                positions.extend([mid_x - x_offset, mid_x + x_offset])

        positions.sort()
        return positions

    def create_rebar_meshes(  # noqa: PLR0913
        positions: list[float],
        z_position: float,
        diameter: float,
        segment_length: float,
        x_offset: float,
        height_start: float | None = None,
        height_end: float | None = None,
    ) -> None:
        """Create and position longitudinal rebar meshes."""
        if height_start is None:
            height_start = diameter
        if height_end is None:
            height_end = diameter

        for y_pos in positions:
            # Create a cylinder that spans the segment length
            rebar = trimesh.creation.cylinder(radius=diameter / 2, height=segment_length, sections=16)

            # Rotate to align with X axis
            rebar.apply_transform(trimesh.transformations.rotation_matrix(angle=np.pi / 2, direction=[0, 1, 0]))

            # Position the rebar with the cumulative x_offset
            rebar_copy = rebar.copy()
            rebar_copy.apply_translation([x_offset + segment_length / 2, y_pos, z_position])
            rebar_copy.visual.face_colors = color
            rebar_scene.add_geometry(rebar_copy)

    def create_shear_rebars(  # noqa: PLR0913
        x_positions: list[float],
        y_offset: float,
        height: float,
        rebar_diameter: float,  # New parameter for single diameter
        z_position: float,  # New parameter for single z-position
        x_offset: float,
        height_start: float | None = None,
        height_end: float | None = None,
    ) -> None:
        """
        Create and position shear rebars for a zone at specified height.

        Args:
            x_positions: List of x-coordinates for rebar placement
            y_offset: Offset in y direction for the rebars
            height: Base height for the rebars
            rebar_diameter: Diameter of the rebar
            z_position: Z-coordinate for rebar placement
            x_offset: Global x-offset for segment positioning
            height_start: Starting height for variable height rebars (optional)
            height_end: Ending height for variable height rebars (optional)

        """
        if height_start is None:
            height_start = height
        if height_end is None:
            height_end = height

        for relative_x_pos in x_positions:
            # Add the cumulative x_offset to position the rebar in the correct segment
            x_pos = x_offset + relative_x_pos

            interpolation_factor = x_positions.index(relative_x_pos) / (len(x_positions) - 1) if len(x_positions) > 1 else 0.5
            height_at_x = height_start + (height_end - height_start) * interpolation_factor

            # Create shear rebar
            shear_rebar = trimesh.creation.cylinder(radius=rebar_diameter / 2, height=height_at_x, sections=16)

            # Rotate to align vertically
            rotation_matrix = trimesh.transformations.rotation_matrix(angle=np.pi / 2, direction=[1, 0, 0])
            shear_rebar.apply_transform(rotation_matrix)

            # Position the rebar with the cumulative x_offset
            shear_rebar.apply_translation([x_pos, y_offset, z_position])

            # Set colors and add to scene
            shear_rebar.visual.face_colors = color
            rebar_scene.add_geometry(shear_rebar)

    # Initialize parameters
    bridge_segments_array = params.bridge_segments_array
    reinforcement_zones_array = params.reinforcement_zones_array
    langswapening_buiten = params.input.geometrie_wapening.langswapening_buiten
    dekking_onder = params.input.geometrie_wapening.dekking_onder / 1000
    dekking_boven = params.input.geometrie_wapening.dekking_boven / 1000
    z_position_bottom = -params.bridge_segments_array[0].dz
    z_position_top = params.bridge_segments_array[0].dz_2 - params.bridge_segments_array[0].dz
    rebar_scene = trimesh.Scene()

    # Process each reinforcement configuration
    for config_entry in reinforcement_zones_array:
        # Get all zones where this configuration should be applied
        zone_tuples = parse_zone_number(config_entry.zone_number)

        # Get parameters for this configuration
        zone_params = get_zone_parameters(config_entry)

        # Apply configuration to each zone
        for position, segment_idx in zone_tuples:
            # Get dimensions for this specific zone
            zone_dims = get_zone_dimensions(position, segment_idx)

            # Calculate the cumulative distance to this segment
            x_offset = get_cumulative_distance(segment_idx)

            # Calculate widths, positions and offsets
            effective_widths = calculate_effective_widths(zone_params, zone_dims)
            z_positions = calculate_z_positions(position == 2, zone_params)
            y_offset = calculate_y_offset(position, segment_idx)

            # Create longitudinal bottom reinforcement
            bottom_positions = calculate_rebar_positions(effective_widths["long_bottom"], zone_params["hoh_long_bottom"], y_offset)
            create_rebar_meshes(
                bottom_positions,
                z_positions["long_bottom"],
                zone_params["diam_long_bottom"],
                zone_dims["length"],
                x_offset,
                zone_dims["height_start"],
                zone_dims["height_end"],
            )

            # Create longitudinal top reinforcement
            top_positions = calculate_rebar_positions(effective_widths["long_top"], zone_params["hoh_long_top"], y_offset)
            create_rebar_meshes(
                top_positions,
                z_positions["long_top"],
                zone_params["diam_long_top"],
                zone_dims["length"],
                x_offset,
                zone_dims["height_start"],
                zone_dims["height_end"],
            )
            # Create bottom shear reinforcement
            if zone_params.get("hoh_shear_bottom") and zone_params.get("diam_shear_bottom"):
                shear_positions_bottom = get_shear_positions(
                    effective_widths["shear_bottom"], zone_params["hoh_shear_bottom"], zone_params["diam_shear_bottom"]
                )
                create_shear_rebars(
                    shear_positions_bottom,
                    y_offset,
                    zone_dims["bz"],
                    zone_params["diam_shear_bottom"],
                    z_positions["shear_bottom"],
                    x_offset,
                    zone_dims["height_start"],
                    zone_dims["height_end"],
                )

            # Create top shear reinforcement
            if zone_params.get("hoh_shear_top") and zone_params.get("diam_shear_top"):
                shear_positions_top = get_shear_positions(effective_widths["shear_top"], zone_params["hoh_shear_top"], zone_params["diam_shear_top"])
                create_shear_rebars(
                    shear_positions_top,
                    y_offset,
                    zone_dims["bz"],
                    zone_params["diam_shear_top"],
                    z_positions["shear_top"],
                    x_offset,
                    zone_dims["height_start"],
                    zone_dims["height_end"],
                )

            # Create bottom shear reinforcement
            if zone_params.get("hoh_shear_bottom") and zone_params.get("diam_shear_bottom"):
                shear_positions_bottom = get_shear_positions(
                    effective_widths["shear_bottom"], zone_params["hoh_shear_bottom"], zone_params["diam_shear_bottom"]
                )
                create_shear_rebars(
                    shear_positions_bottom,
                    y_offset,
                    zone_dims["bz"],
                    zone_params["diam_shear_bottom"],
                    z_positions["shear_bottom"],
                    x_offset,
                    zone_dims["height_start"],
                    zone_dims["height_end"],
                )

            # Create top shear reinforcement
            if zone_params.get("hoh_shear_top") and zone_params.get("diam_shear_top"):
                shear_positions_top = get_shear_positions(effective_widths["shear_top"], zone_params["hoh_shear_top"], zone_params["diam_shear_top"])
                create_shear_rebars(
                    shear_positions_top,
                    y_offset,
                    zone_dims["bz"],
                    zone_params["diam_shear_top"],
                    z_positions["shear_top"],
                    x_offset,
                    zone_dims["height_start"],
                    zone_dims["height_end"],
                )

            # Create bijlegwapening (additional reinforcement) if enabled
            if zone_params.get("heeft_bijlegwapening"):
                # Bottom longitudinal additional reinforcement
                bijleg_positions_bottom = calculate_bijleg_positions(bottom_positions)
                if bijleg_positions_bottom:
                    create_rebar_meshes(
                        bijleg_positions_bottom,
                        z_positions["long_bottom"],
                        zone_params["bijleg_diam_long_bottom"],
                        zone_dims["length"],
                        x_offset,
                        zone_dims["height_start"],
                        zone_dims["height_end"],
                    )

                # Top longitudinal additional reinforcement
                bijleg_positions_top = calculate_bijleg_positions(top_positions)
                if bijleg_positions_top:
                    create_rebar_meshes(
                        bijleg_positions_top,
                        z_positions["long_top"],
                        zone_params["bijleg_diam_long_top"],
                        zone_dims["length"],
                        x_offset,
                        zone_dims["height_start"],
                        zone_dims["height_end"],
                    )

                # Bottom transverse additional reinforcement
                if zone_params.get("hoh_shear_bottom") and zone_params.get("bijleg_diam_shear_bottom"):
                    bijleg_shear_positions_bottom = calculate_bijleg_positions(shear_positions_bottom)
                    if bijleg_shear_positions_bottom:
                        create_shear_rebars(
                            bijleg_shear_positions_bottom,
                            y_offset,
                            zone_dims["bz"],
                            zone_params["bijleg_diam_shear_bottom"],
                            z_positions["shear_bottom"],
                            x_offset,
                            zone_dims["height_start"],
                            zone_dims["height_end"],
                        )

                # Top transverse additional reinforcement
                if zone_params.get("hoh_shear_top") and zone_params.get("bijleg_diam_shear_top"):
                    bijleg_shear_positions_top = calculate_bijleg_positions(shear_positions_top)
                    if bijleg_shear_positions_top:
                        create_shear_rebars(
                            bijleg_shear_positions_top,
                            y_offset,
                            zone_dims["bz"],
                            zone_params["bijleg_diam_shear_top"],
                            z_positions["shear_top"],
                            x_offset,
                            zone_dims["height_start"],
                            zone_dims["height_end"],
                        )

    return rebar_scene  # type: ignore[return-value]  # Scene is functionally compatible with Trimesh in this context


# Function to create the X, Y, and Z axes
def create_axes(length: float = 5.0, radius: float = 0.05) -> trimesh.Scene:
    """
    Create X, Y, Z axes as cylinders or lines at the origin.

    Args:
        length (float): Length of the axes.
        radius (float): Radius of the cylinder representing each axis.

    Returns:
        trimesh.Scene: A scene containing the axes as colored cylinders.

    """
    # Create cylinder meshes for each axis
    x_axis = trimesh.creation.cylinder(radius=radius, height=length, sections=20)
    y_axis = trimesh.creation.cylinder(radius=radius, height=length, sections=20)
    z_axis = trimesh.creation.cylinder(radius=radius, height=length, sections=20)

    # Rotate cylinders to align with their respective axes
    x_axis.vertices = (
        trimesh.transformations.rotation_matrix(angle=np.pi / 2, direction=[0, 1, 0], point=[0, 0, 0])
        .dot(np.hstack((x_axis.vertices, np.ones((x_axis.vertices.shape[0], 1)))).T)
        .T[:, :3]
    )
    y_axis.vertices = (
        trimesh.transformations.rotation_matrix(angle=np.pi / 2, direction=[1, 0, 0], point=[0, 0, 0])
        .dot(np.hstack((y_axis.vertices, np.ones((y_axis.vertices.shape[0], 1)))).T)
        .T[:, :3]
    )

    # Translate cylinders to align with the origin and direction of each axis
    x_axis.apply_translation([length / 2, 0, 0])  # Translate along X-axis
    y_axis.apply_translation([0, length / 2, 0])  # Translate along Y-axis
    z_axis.apply_translation([0, 0, length / 2])  # Translate along Z-axis

    # Apply colors to the axes
    x_axis.visual.face_colors = [255, 0, 0, 255]  # Red for X-axis
    y_axis.visual.face_colors = [0, 255, 0, 255]  # Green for Y-axis
    z_axis.visual.face_colors = [0, 0, 255, 255]  # Blue for Z-axis

    # Combine axes into a single scene
    return trimesh.Scene([x_axis, y_axis, z_axis])


# Function to create a black dot at the origin
def create_black_dot(radius: float = 0.2) -> trimesh.Trimesh:
    """
    Create a black sphere (dot) at the origin.

    Args:
        radius (float): Radius of the sphere.

    Returns:
        trimesh.Trimesh: A sphere mesh representing the black dot.

    """
    # Create a sphere mesh and assign black color
    dot = trimesh.creation.icosphere(radius=radius)
    dot.visual.face_colors = [0, 0, 0, 255]  # Black color
    return dot


def create_cross_section(mesh: trimesh.Trimesh, plane_origin: list | np.ndarray, plane_normal: list | np.ndarray, axes: bool = True) -> trimesh.Scene:
    """
    Create a cross-section of a 3D mesh by slicing it with a plane.

    Args:
        mesh (trimesh.Trimesh): The 3D mesh to slice.
        plane_origin (list or np.ndarray): A point on the slicing plane [x, y, z].
        plane_normal (list or np.ndarray): The normal vector of the slicing plane [nx, ny, nz].
        axes (bool, optional): Whether to include coordinate axes and origin point in the scene. Defaults to True.

    Returns:
        trimesh.path.Path3D: A 3D path representing the cross-section.

    """
    # Ensure the plane origin and normal are numpy arrays
    plane_origin = np.array(plane_origin)
    plane_normal = np.array(plane_normal)

    # Slice the mesh with the specified plane
    cross_section = mesh.section(plane_origin=plane_origin, plane_normal=plane_normal)

    combined_scene_2d = trimesh.Scene(cross_section)

    if axes:
        # Add the X, Y, Z axes to the scene
        axes_scene = create_axes()
        combined_scene_2d.add_geometry(axes_scene)

        # Add the black dot at the origin to the scene
        black_dot = create_black_dot(radius=0.1)
        combined_scene_2d.add_geometry(black_dot)

    return combined_scene_2d


def create_section_planes(params: dict | Munch) -> trimesh.Scene:
    """
    Creates transparent grey planes representing the horizontal, longitudinal and cross sections.

    Args:
        params (dict | Munch): Input parameters containing section locations and bridge dimensions.

    Returns:
        trimesh.Scene: Scene containing the three section planes.

    """
    # Get section locations from params
    h_loc = params.input.dimensions.horizontal_section_loc
    l_loc = params.input.dimensions.longitudinal_section_loc
    c_loc = params.input.dimensions.cross_section_loc

    # Calculate model bounds based on bridge dimensions
    original_length = sum(segment.l for segment in params.bridge_segments_array)

    max_width_z1 = max(segment.bz1 for segment in params.bridge_segments_array)
    max_width_z2 = max(segment.bz2 for segment in params.bridge_segments_array)
    max_width_z3 = max(segment.bz3 for segment in params.bridge_segments_array)

    original_width = max_width_z1 + max_width_z2 + max_width_z3

    max_hight_dz_2 = max(segment.dz_2 for segment in params.bridge_segments_array)

    # Add some padding to bounds
    padding = 5
    length = original_length + padding
    max_width = original_width + padding
    max_height = max_hight_dz_2 + padding

    # Create planes with appropriate dimensions and positions
    # Planes start at -padding/2 and extend to original_length + padding/2
    horizontal_plane = trimesh.creation.box(extents=[length, max_width, 0.01])
    horizontal_plane.apply_translation([original_length / 2, -padding / 2, h_loc])

    longitudinal_plane = trimesh.creation.box(extents=[length, 0.01, max_height])
    longitudinal_plane.apply_translation([original_length / 2, l_loc, -padding / 2])

    cross_plane = trimesh.creation.box(extents=[0.01, max_width, max_height])
    cross_plane.apply_translation([c_loc, -padding / 2, -padding / 2])

    # Set transparent grey color for all planes and use PBRMaterial with alphaMode='BLEND'
    grey_color = [128, 128, 128, 150]  # RGBA with alpha=30 for higher transparency (less visible)
    from trimesh.visual.material import PBRMaterial

    material = PBRMaterial(baseColorFactor=[128 / 255, 128 / 255, 128 / 255, 150 / 255], alphaMode="BLEND")
    for plane in [horizontal_plane, longitudinal_plane, cross_plane]:
        plane.visual.face_colors = grey_color
        plane.visual.material = material

    # Add planes to scene
    scene = trimesh.Scene()
    scene.add_geometry(horizontal_plane)
    scene.add_geometry(longitudinal_plane)
    scene.add_geometry(cross_plane)

    return scene


def create_3d_model(params: (dict | Munch), axes: bool = True, section_planes: bool = False) -> trimesh.Scene:
    """
    Generates a 3D representation of a bridge deck based on input parameters.

    Args:
        params (dict | Munch): Input parameters containing bridge dimensions and properties.
            - params.bridge_segments_array: A list of dictionaries, where each dictionary
              defines the dimensions and properties of a sub-zone. Each dictionary should
              include keys such as 'l', 'bz1', 'bz2', 'bz3', 'dz', and 'dze'.
        axes (bool, optional): Whether to include coordinate axes and origin point in the scene. Defaults to True.
        section_planes (bool, optional): Whether to include transparent section planes in the scene. Defaults to False.

    Returns:
        trimesh.Scene: A 3D scene containing the bridge deck model, including sub-zone boxes,
        axes, a black dot at the origin, and optionally section planes.

    """
    # Determine the number of sub-zones based on input dimensions
    dynamic_arrays = len(params.bridge_segments_array)

    if not params.bridge_segments_array:
        # If there are no segments, return an empty scene
        # NOTE: Empty scene is the expected behavior for no segments
        return trimesh.Scene()

    # Generate a dynamic color list for the sub-zones
    clist = list(range(0, 255, int(float(255 / dynamic_arrays))))
    clist.insert(0, 0)

    # Initialize an empty scene for the 3D model
    combined_scene = trimesh.Scene()

    # Iterate through each sub-zone to create 3D boxes
    for dynamic_array in range(1, dynamic_arrays):
        # Calculate cumulative length for the current sub-zone
        num_dicts_to_sum = dynamic_array
        l_sum = sum(item["l"] for item in params.bridge_segments_array[:num_dicts_to_sum])

        # Define dimensions for the previous and current zones
        ## D n-1
        d0l = l_sum
        # Zone 1
        z1d0l = params.bridge_segments_array[dynamic_array - 1].bz1 + params.bridge_segments_array[dynamic_array - 1].bz2 / 2
        z1d0r = params.bridge_segments_array[dynamic_array - 1].bz2 / 2
        z1d0t = 0
        z1d0b = -params.bridge_segments_array[dynamic_array - 1].dz
        # Zone 2
        z2d0l = params.bridge_segments_array[dynamic_array - 1].bz2 / 2
        z2d0r = -params.bridge_segments_array[dynamic_array - 1].bz2 / 2
        z2d0t = params.bridge_segments_array[dynamic_array - 1].dz_2 - params.bridge_segments_array[dynamic_array - 1].dz
        z2d0b = -params.bridge_segments_array[dynamic_array - 1].dz
        # Zone 3
        z3d0l = -params.bridge_segments_array[dynamic_array - 1].bz2 / 2
        z3d0r = -params.bridge_segments_array[dynamic_array - 1].bz3 - params.bridge_segments_array[dynamic_array - 1].bz2 / 2
        z3d0t = 0
        z3d0b = -params.bridge_segments_array[dynamic_array - 1].dz

        ## D
        # Zone 1
        d1l = params.bridge_segments_array[dynamic_array].l + l_sum
        z1d1l = params.bridge_segments_array[dynamic_array].bz1 + params.bridge_segments_array[dynamic_array].bz2 / 2
        z1d1r = params.bridge_segments_array[dynamic_array].bz2 / 2
        z1d1t = 0
        z1d1b = -params.bridge_segments_array[dynamic_array].dz
        # Zone 2
        z2d1l = params.bridge_segments_array[dynamic_array].bz2 / 2
        z2d1r = -params.bridge_segments_array[dynamic_array].bz2 / 2
        z2d1t = params.bridge_segments_array[dynamic_array].dz_2 - params.bridge_segments_array[dynamic_array].dz
        z2d1b = -params.bridge_segments_array[dynamic_array].dz
        # Zone 3
        z3d1l = -params.bridge_segments_array[dynamic_array].bz2 / 2
        z3d1r = -params.bridge_segments_array[dynamic_array].bz3 - params.bridge_segments_array[dynamic_array].bz2 / 2
        z3d1t = 0
        z3d1b = -params.bridge_segments_array[dynamic_array].dz

        # Specify the vertices for each box
        boxes_vertices = [
            # Box 1 (at origin in Y-axis)
            np.array(
                [
                    [d0l, z1d0r, z1d0b],  # Vertex 0: Bottom-front-left -- D-1
                    [d1l, z1d1r, z1d1b],  # Vertex 1: Bottom-front-right
                    [d1l, z1d1l, z1d1b],  # Vertex 2: Bottom-back-right
                    [d0l, z1d0l, z1d0b],  # Vertex 3: Bottom-back-left -- D-1
                    [d0l, z1d0r, z1d0t],  # Vertex 4: Top-front-left -- D-1
                    [d1l, z1d1r, z1d1t],  # Vertex 5: Top-front-right
                    [d1l, z1d1l, z1d1t],  # Vertex 6: Top-back-right
                    [d0l, z1d0l, z1d0t],  # Vertex 7: Top-back-left -- D-1
                ]
            ),
            # Box 2
            np.array(
                [
                    [d0l, z2d0r, z2d0b],  # Vertex 0: Bottom-front-left -- D-1
                    [d1l, z2d1r, z2d1b],  # Vertex 1: Bottom-front-right
                    [d1l, z2d1l, z2d1b],  # Vertex 2: Bottom-back-right
                    [d0l, z2d0l, z2d0b],  # Vertex 3: Bottom-back-left -- D-1
                    [d0l, z2d0r, z2d0t],  # Vertex 4: Top-front-left -- D-1
                    [d1l, z2d1r, z2d1t],  # Vertex 5: Top-front-right
                    [d1l, z2d1l, z2d1t],  # Vertex 6: Top-back-right
                    [d0l, z2d0l, z2d0t],  # Vertex 7: Top-back-left -- D-1
                ]
            ),
            # Box 3
            np.array(
                [
                    [d0l, z3d0r, z3d0b],  # Vertex 0: Bottom-front-left -- D-1
                    [d1l, z3d1r, z3d1b],  # Vertex 1: Bottom-front-right
                    [d1l, z3d1l, z3d1b],  # Vertex 2: Bottom-back-right
                    [d0l, z3d0l, z3d0b],  # Vertex 3: Bottom-back-left -- D-1
                    [d0l, z3d0r, z3d0t],  # Vertex 4: Top-front-left -- D-1
                    [d1l, z3d1r, z3d1t],  # Vertex 5: Top-front-right
                    [d1l, z3d1l, z3d1t],  # Vertex 6: Top-back-right
                    [d0l, z3d0l, z3d0t],  # Vertex 7: Top-back-left -- D-1
                ]
            ),
        ]

        # Define colors for each box in RGBA format
        box_colors = [
            [255, clist[dynamic_array], clist[dynamic_array], 255],  # Box 1: Red with varying intensity
            [clist[dynamic_array], clist[dynamic_array], 255, 255],  # Box 2: Blue with varying intensity
            [clist[dynamic_array], 255, clist[dynamic_array], 255],  # Box 3: Green with varying intensity
        ]

        # Create and add individual box meshes with assigned colors
        for vertices, color in zip(boxes_vertices, box_colors):
            box_mesh = create_box(vertices, color)
            # Convert color to uint8 numpy array and ensure it's applied consistently
            color_array = np.array(color, dtype=np.uint8)
            box_mesh.visual.face_colors = color_array
            box_mesh.visual.vertex_colors = color_array
            # Process mesh before adding
            box_mesh.process()  # Merges duplicate vertices
            box_mesh.fix_normals()  # Ensures consistent face orientation
            # Add directly to scene
            combined_scene.add_geometry(box_mesh)

    if axes:
        # Add the X, Y, Z axes to the scene
        axes_scene = create_axes()
        combined_scene.add_geometry(axes_scene)

        # Add the black dot at the origin to the scene
        black_dot = create_black_dot(radius=0.1)
        combined_scene.add_geometry(black_dot)

    rebars_scene = create_rebars(params, color=[0, 0, 0, 255])  # Call the function to create rebars
    combined_scene.add_geometry(rebars_scene)  # Add the rebars to the scene

    # Add transparent section planes to visualize where the 2D sections will be taken
    # These planes help users understand the location of horizontal, longitudinal, and cross sections
    if params.input.dimensions.toggle_sections and section_planes:
        section_planes_scene = create_section_planes(params)
        combined_scene.add_geometry(section_planes_scene)

    return combined_scene


def create_2d_top_view(viktor_params: Munch) -> dict:  # noqa: C901, PLR0912, PLR0915
    """
    Creates a 2D representation of the bridge top view, including lines, zone labels,
    and dimension lines with parameter values.

    Args:
        viktor_params (Munch): The VIKTOR parametrization object.
            - viktor_params.bridge_segments_array: List of Munch objects for each cross-section (this is the dynamic array).

    Returns:
        dict: A dictionary with "bridge_lines", "zone_annotations",
              "dimension_texts", and "cross_section_labels".

    """
    # Access the dynamic array data, which VIKTOR makes available
    # directly using the 'name' attribute given in the DynamicArray definition.
    try:
        segments_data = viktor_params.bridge_segments_array
        if segments_data is None:  # It might exist but be None if not filled
            segments_data = []
    except AttributeError:
        return {
            "bridge_lines": [],
            "zone_annotations": [],
            "dimension_texts": [],
            "cross_section_labels": [],
            "zone_polygons": [],
        }

    # Further ensure segments_data is a list, as DynamicArray can sometimes evaluate to None initially
    if not isinstance(segments_data, list):
        segments_data = []

    num_cross_sections = len(segments_data)

    if num_cross_sections < 1:  # Allow single cross-section for width dimensions
        return {
            "bridge_lines": [],
            "zone_annotations": [],
            "dimension_texts": [],
            "cross_section_labels": [],
            "zone_polygons": [],
        }

    bridge_lines = []
    zone_annotations = []
    dimension_texts_data = []
    cross_section_labels_data = []
    zone_polygons_data = []  # New list for zone background polygons
    current_x = 0.0
    # Determine max bridge height for positioning labels later
    max_y_top_outer = 0
    if segments_data:
        max_y_top_outer = max(seg.bz1 + seg.bz2 / 2.0 for seg in segments_data)
    label_y_offset = 0.5  # Reduced offset above the highest point for D labels

    def interpolate(y_start: float, y_end: float, factor: float = 0.5) -> float:
        return y_start + (y_end - y_start) * factor

    # --- Process Segments (for bridge lines, l-dimensions, and zone annotations) ---
    if num_cross_sections >= 2:
        for i in range(num_cross_sections - 1):
            seg_start_data = segments_data[i]
            seg_end_data = segments_data[i + 1]
            segment_length = seg_end_data.l
            next_x = current_x + segment_length
            bz1_start, bz2_start, bz3_start = seg_start_data.bz1, seg_start_data.bz2, seg_start_data.bz3
            half_bz2_start = bz2_start / 2.0
            y_top_outer_start = half_bz2_start + bz1_start
            y_top_inner_start = half_bz2_start
            y_bottom_inner_start = -half_bz2_start
            y_bottom_outer_start = -half_bz2_start - bz3_start
            bz1_end, bz2_end, bz3_end = seg_end_data.bz1, seg_end_data.bz2, seg_end_data.bz3
            half_bz2_end = bz2_end / 2.0
            y_top_outer_end = half_bz2_end + bz1_end
            y_top_inner_end = half_bz2_end
            y_bottom_inner_end = -half_bz2_end
            y_bottom_outer_end = -half_bz2_end - bz3_end
            segment_number = i + 1

            # Bridge Lines (copied from your previous version for completeness in this snippet)
            bridge_lines.append({"start": [current_x, y_top_outer_start], "end": [next_x, y_top_outer_end]})
            bridge_lines.append({"start": [current_x, y_top_inner_start], "end": [next_x, y_top_inner_end]})
            bridge_lines.append({"start": [current_x, y_bottom_inner_start], "end": [next_x, y_bottom_inner_end]})
            bridge_lines.append({"start": [current_x, y_bottom_outer_start], "end": [next_x, y_bottom_outer_end]})

            # --- Zone Background Polygons ---
            # Zone 1 Polygon (Red)
            zone1_vertices = [[current_x, y_top_inner_start], [next_x, y_top_inner_end], [next_x, y_top_outer_end], [current_x, y_top_outer_start]]
            zone_polygons_data.append(
                {
                    "zone_id": f"1-{segment_number}",
                    "vertices": zone1_vertices,
                    "color": "rgba(255, 0, 0, 0.15)",  # Light Red
                }
            )

            # Zone 2 Polygon (Blue) - only if it exists
            if bz2_start > 0 or bz2_end > 0:
                zone2_vertices = [
                    [current_x, y_bottom_inner_start],
                    [next_x, y_bottom_inner_end],
                    [next_x, y_top_inner_end],
                    [current_x, y_top_inner_start],
                ]
                zone_polygons_data.append(
                    {
                        "zone_id": f"2-{segment_number}",
                        "vertices": zone2_vertices,
                        "color": "rgba(0, 0, 255, 0.15)",  # Light Blue
                    }
                )

            # Zone 3 Polygon (Green)
            zone3_vertices = [
                [current_x, y_bottom_outer_start],
                [next_x, y_bottom_outer_end],
                [next_x, y_bottom_inner_end],
                [current_x, y_bottom_inner_start],
            ]
            zone_polygons_data.append(
                {
                    "zone_id": f"3-{segment_number}",
                    "vertices": zone3_vertices,
                    "color": "rgba(0, 255, 0, 0.15)",  # Light Green
                }
            )
            # --- End Zone Polygons ---

            # Zone Annotations (copied from your previous version for completeness)
            x_mid_segment = current_x + segment_length / 2.0
            y_top_outer_mid = interpolate(y_top_outer_start, y_top_outer_end)
            y_top_inner_mid = interpolate(y_top_inner_start, y_top_inner_end)
            y_bottom_inner_mid = interpolate(y_bottom_inner_start, y_bottom_inner_end)
            y_bottom_outer_mid = interpolate(y_bottom_outer_start, y_bottom_outer_end)
            y_mid_z1 = (y_top_outer_mid + y_top_inner_mid) / 2.0
            zone_annotations.append({"text": f"1-{segment_number}", "x": x_mid_segment, "y": y_mid_z1})
            if bz2_start > 0 or bz2_end > 0:
                y_mid_z2 = (y_top_inner_mid + y_bottom_inner_mid) / 2.0
                zone_annotations.append({"text": f"2-{segment_number}", "x": x_mid_segment, "y": y_mid_z2})
            y_mid_z3 = (y_bottom_inner_mid + y_bottom_outer_mid) / 2.0
            zone_annotations.append({"text": f"3-{segment_number}", "x": x_mid_segment, "y": y_mid_z3})

            # L-Dimension Text for this segment
            # Position it below the segment, aligned with its center
            l_text_y_offset = 1.0
            y_pos_for_l_text = min(y_bottom_outer_start, y_bottom_outer_end) - l_text_y_offset
            dimension_texts_data.append(
                {"text": f"l = {segment_length}m", "x": current_x + segment_length / 2.0, "y": y_pos_for_l_text, "type": "length", "textangle": 0}
            )

            current_x = next_x

    # --- Process Cross-Sections (for transverse bridge lines and bz-dimensions texts) ---
    cumulative_x = 0.0
    for j in range(num_cross_sections):
        cs_data = segments_data[j]
        if j > 0:
            cumulative_x += cs_data.l  # Use l from the current section for positioning the section line

        cs_x = cumulative_x  # This is the x-coordinate of the j-th cross-section line

        bz1, bz2, bz3 = cs_data.bz1, cs_data.bz2, cs_data.bz3
        half_bz2 = bz2 / 2.0
        y_top_outer = half_bz2 + bz1
        y_top_inner = half_bz2
        y_bottom_inner = -half_bz2
        y_bottom_outer = -half_bz2 - bz3

        # Transverse Bridge Lines for this cross-section (copied from previous version)
        bridge_lines.append({"start": [cs_x, y_top_outer], "end": [cs_x, y_top_inner]})
        bridge_lines.append({"start": [cs_x, y_bottom_inner], "end": [cs_x, y_bottom_outer]})
        if bz2 > 0:
            bridge_lines.append({"start": [cs_x, y_top_inner], "end": [cs_x, y_bottom_inner]})

        # BZ Dimension Texts for this cross-section
        text_x_offset = 0.75  # Increased offset to move text further left
        cross_section_number = j + 1  # 1-based index for labeling

        # bz1 text
        dimension_texts_data.append(
            {
                "text": f"bz 1-{cross_section_number}= {bz1}m",
                "x": cs_x - text_x_offset,
                "y": (y_top_inner + y_top_outer) / 2.0,
                "type": "width",
                "textangle": -90,
                "align": "center",
            }
        )

        # bz2 text
        if bz2 > 0:
            dimension_texts_data.append(
                {
                    "text": f"bz 2-{cross_section_number}= {bz2}m",
                    "x": cs_x - text_x_offset,
                    "y": (y_bottom_inner + y_top_inner) / 2.0,
                    "type": "width",
                    "textangle": -90,
                    "align": "center",
                }
            )

        # bz3 text
        dimension_texts_data.append(
            {
                "text": f"bz 3-{cross_section_number}= {bz3}m",
                "x": cs_x - text_x_offset,
                "y": (y_bottom_outer + y_bottom_inner) / 2.0,
                "type": "width",
                "textangle": -90,
                "align": "center",
            }
        )

        # Add D1, D2 labels above the cross-section line
        label_y_pos = max_y_top_outer + label_y_offset
        cross_section_labels_data.append({"text": f"D{cross_section_number}", "x": cs_x, "y": label_y_pos, "type": "cross_section_label"})

    return {
        "bridge_lines": bridge_lines,
        "zone_annotations": zone_annotations,
        "dimension_texts": dimension_texts_data,
        "cross_section_labels": cross_section_labels_data,
        "zone_polygons": zone_polygons_data,
    }


# Define dataclasses for structured data
@dataclass
class BridgeSegmentDimensions:
    """Represents the dimensions of a single bridge segment cross-section."""

    bz1: float
    bz2: float
    bz3: float
    segment_length: float  # Length to previous segment (0 for the first segment)
    # Add is_first_segment if it becomes necessary for validation logic here


@dataclass
class DPointLabel:
    """Represents the data for a D-point label."""

    text: str
    x: float
    y: float


@dataclass
class LoadZoneGeometryData:
    """Holds calculated geometric data for load zone visualization."""

    x_coords_d_points: list[float]
    y_top_structural_edge_at_d_points: list[float]
    total_widths_at_d_points: list[float]
    y_bridge_bottom_at_d_points: list[float]
    num_defined_d_points: int
    d_point_label_data: list[DPointLabel]


def prepare_load_zone_geometry_data(
    bridge_dimensions_array: Sequence[BridgeSegmentDimensions],
    label_y_offset: float = 1.5,  # Exposed parameter with default
) -> LoadZoneGeometryData:
    """
    Calculates geometric data needed for load zone visualization based on bridge segments.

    Args:
        bridge_dimensions_array: A sequence of BridgeSegmentDimensions objects.
        label_y_offset: Vertical offset for D-point labels from the top structural edge.

    Returns:
        A LoadZoneGeometryData object containing calculated lists and counts.

    Raises:
        ValueError: If segment dimensions (bz1, bz2, bz3, l) are invalid.

    """
    num_defined_d_points = len(bridge_dimensions_array)

    if num_defined_d_points == 0:
        return LoadZoneGeometryData([], [], [], [], 0, [])

    # Input Validation
    for i, segment_data in enumerate(bridge_dimensions_array):
        if not (segment_data.bz1 >= 0 and segment_data.bz2 >= 0 and segment_data.bz3 >= 0):
            raise ValueError(
                f"Bridge segment {i + 1} (D{i + 1}) dimensions (bz1, bz2, bz3) must be non-negative. "
                f"Got bz1={segment_data.bz1}, bz2={segment_data.bz2}, bz3={segment_data.bz3}"
            )
        # Length 'l' must be positive for segments after the first one.
        # For the first segment (i=0), 'l' is often 0 or not used for positioning based on previous.
        if i > 0 and not (segment_data.segment_length > 0):
            raise ValueError(f"Length 'l' for bridge segment {i + 1} (D{i + 1}) must be positive. Got l={segment_data.segment_length}")

    x_coords_d_points = []
    y_top_structural_edge_at_d_points = []
    total_widths_at_d_points = []
    d_point_label_data: list[DPointLabel] = []  # Explicitly typed list
    current_x = 0.0
    # label_y_offset is now a parameter

    for i in range(num_defined_d_points):
        segment_params = bridge_dimensions_array[i]
        if i == 0:
            x_coords_d_points.append(current_x)  # D1 is at x = 0
        else:
            # Subsequent D-points are positioned by adding the length 'l' of the *current* segment,
            # which represents the length *from the previous* D-point to this one.
            current_x += segment_params.segment_length
            x_coords_d_points.append(current_x)

        # Guarding for bz2 < 0 is implicitly handled by the validation above (bz2 >= 0).
        # If bz2 is 0, y_top calculation is still valid.
        y_top = segment_params.bz1 + (segment_params.bz2 / 2.0)
        y_top_structural_edge_at_d_points.append(y_top)

        current_total_width_at_di = segment_params.bz1 + segment_params.bz2 + segment_params.bz3
        total_widths_at_d_points.append(current_total_width_at_di)

        d_point_label_data.append(DPointLabel(text=f"D{i + 1}", x=x_coords_d_points[i], y=y_top + label_y_offset))

    y_bridge_bottom_at_d_points = [
        y_top_structural_edge_at_d_points[d_idx] - total_widths_at_d_points[d_idx] for d_idx in range(num_defined_d_points)
    ]

    return LoadZoneGeometryData(
        x_coords_d_points=x_coords_d_points,
        y_top_structural_edge_at_d_points=y_top_structural_edge_at_d_points,
        total_widths_at_d_points=total_widths_at_d_points,
        y_bridge_bottom_at_d_points=y_bridge_bottom_at_d_points,
        num_defined_d_points=num_defined_d_points,
        d_point_label_data=d_point_label_data,
    )


def calculate_bijleg_positions(positions: list[float], y_offset: float = 0) -> list[float]:
    """Calculate positions for additional reinforcement by finding midpoints between main reinforcement."""
    if len(positions) < 2:
        return []

    # Calculate midpoint between each pair of consecutive positions
    bijleg_positions = []
    for i in range(len(positions) - 1):
        midpoint = (positions[i] + positions[i + 1]) / 2.0
        bijleg_positions.append(midpoint)

    # Add y_offset to all positions
    return [pos + y_offset for pos in bijleg_positions]
