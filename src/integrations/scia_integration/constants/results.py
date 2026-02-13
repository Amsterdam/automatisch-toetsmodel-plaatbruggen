"""
Constants for SCIA result table processing.

This module contains constants for table types, column names, table name patterns,
and other result processing-related values used throughout SCIA result handling.
"""

from typing import Literal

# CS (Cross Section) table types
CS_TABLE_TYPE_ULS: Literal["ULS"] = "ULS"
CS_TABLE_TYPE_SLS_FREQ: Literal["SLS freq"] = "SLS freq"

# All CS table types as a tuple (immutable list)
CS_TABLE_TYPES: tuple[Literal["ULS"], Literal["SLS freq"]] = (
    CS_TABLE_TYPE_ULS,
    CS_TABLE_TYPE_SLS_FREQ,
)

# SCIA table name patterns for CS tables
# Note: Section on plane results are in the same tables as regular 2D forces
CS_BASIS_TABLE_PATTERN = "Interne 2D-krachten basis {table_type}"
CS_ELEMENTAIRE_TABLE_PATTERN = "Interne 2D-krachten elementair {table_type}"

# CS force/moment column names
CS_SHEAR_FORCE_COLUMNS: tuple[Literal["v_x"], Literal["v_y"]] = ("v_x", "v_y")
CS_MOMENT_COLUMNS: tuple[Literal["m_xD+"], Literal["m_xD-"], Literal["m_yD+"], Literal["m_yD-"]] = (
    "m_xD+",
    "m_xD-",
    "m_yD+",
    "m_yD-",
)
CS_NORMAL_FORCE_COLUMNS: tuple[Literal["n_xD"], Literal["n_yD"]] = ("n_xD", "n_yD")
CS_FORCE_MOMENT_COLUMNS: tuple[
    Literal["v_x"],
    Literal["v_y"],
    Literal["m_xD+"],
    Literal["m_xD-"],
    Literal["m_yD+"],
    Literal["m_yD-"],
    Literal["n_xD"],
    Literal["n_yD"],
] = (*CS_SHEAR_FORCE_COLUMNS, *CS_MOMENT_COLUMNS, *CS_NORMAL_FORCE_COLUMNS)

# Error message constants
MAX_ERROR_MESSAGE_LENGTH = 100  # Maximum length for error message truncation
