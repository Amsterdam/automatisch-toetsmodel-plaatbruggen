"""Utilities for loading seed files for testing."""

import json
from pathlib import Path
from typing import Any

from munch import Munch  # type: ignore[import-untyped]


def get_test_data_dir() -> Path:
    """Get the path to the test_data directory."""
    return Path(__file__).parent


def dict_to_munch(data: dict | list | Any) -> Munch | list | Any:  # noqa: ANN401
    """
    Recursively convert dictionaries to Munch objects for attribute access.

    Args:
        data: Data to convert (dict, list, or other)

    Returns:
        Converted data with dicts as Munch objects

    """
    if isinstance(data, dict):
        munch_obj = Munch()
        for key, value in data.items():
            munch_obj[key] = dict_to_munch(value)
        return munch_obj
    if isinstance(data, list):
        return [dict_to_munch(item) for item in data]
    return data


def load_seed_file(filename: str) -> Munch:
    """
    Load a seed file and return it as a Munch object for easy attribute access.

    Args:
        filename: Name of the seed file (e.g., 'bridge_default_params.json')

    Returns:
        Munch object containing the seed data

    Raises:
        FileNotFoundError: If the seed file doesn't exist
        json.JSONDecodeError: If the seed file contains invalid JSON

    """
    seed_path = get_test_data_dir() / filename

    if not seed_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_path}")

    with open(seed_path, encoding="utf-8") as file:
        data = json.load(file)

    return dict_to_munch(data)


def load_bridge_default_params() -> Munch:
    """Load the default bridge parameters seed file."""
    return load_seed_file("bridge_default_params.json")


def load_bridge_complex_params() -> Munch:
    """Load the complex bridge parameters seed file."""
    return load_seed_file("bridge_complex_params.json")


def load_overview_bridges_default_params() -> Munch:
    """Load the default overview bridges parameters seed file."""
    return load_seed_file("overview_bridges_default_params.json")


def create_mocked_entity_list(count: int = 3) -> list[dict[str, Any]]:
    """
    Create a list of mocked entity data for testing.

    Args:
        count: Number of entities to create

    Returns:
        List of dictionaries representing bridge entities

    """
    return [
        {
            "OBJECTNUMM": f"BRIDGE-{i:03d}",
            "OBJECTNAAM": f"Test Bridge {i}",
            "geometry": f"Mock geometry data for bridge {i}",
        }
        for i in range(1, count + 1)
    ]
