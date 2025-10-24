"""
Plotting constants for visualization styling.

These constants define default colors, line styles, and appearance
properties used across plotting modules.
"""

from typing import Any

from plotly.colors import qualitative as qual_colors

# Default color scheme from Plotly
DEFAULT_PLOTLY_COLORS = qual_colors.Plotly

# Load zone appearance styling by zone type
DEFAULT_ZONE_APPEARANCE_MAP: dict[str, dict[str, Any]] = {
    "Voetgangers": {
        "line_color": "silver",
        "pattern_shape": "+",
        "pattern_fgcolor": "silver",
        "fill_color": "rgba(192,192,192,0.2)",
        "pattern_solidity": 0.5,
    },
    "Fietsers": {
        "line_color": "crimson",
        "pattern_shape": "",
        "fill_color": "rgba(220,20,60,0.3)",
    },
    "Auto": {
        "line_color": "darkslategrey",
        "pattern_shape": "",
        "fill_color": "rgba(47,79,79,0.15)",
    },
    "Tram": {
        "line_color": "blue",
        "pattern_shape": "",
        "fill_color": "rgba(0,0,255,0.15)",
    },
    "Berm": {
        "line_color": "goldenrod",
        "pattern_shape": "x",
        "pattern_fgcolor": "darkgoldenrod",
        "fill_color": "rgba(255, 255, 0, 0.3)",
        "pattern_solidity": 0.5,
    },
}

# Zone boundary line styling constants
ZONE_BOUNDARY_SBS_LINE_THICKNESS = 0.7  # Shared boundary line thickness
ZONE_BOUNDARY_SBS_OFFSET = 0.003  # Small offset for shared boundary lines
ZONE_BOUNDARY_ABSOLUTE_EDGE_THICKNESS = 1.5  # Outer edge line thickness
