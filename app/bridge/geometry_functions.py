"""Functions for geometry calculations in the Bridge application."""

import csv

from app.constants import REINFORCEMENT_PATH


def get_steel_qualities() -> list[str]:
    """
    Get list of available steel qualities from the CSV file.

    Returns:
        list: List of steel quality names

    """
    csv_path = REINFORCEMENT_PATH

    with open(csv_path) as f:
        csv_reader = csv.DictReader(f, delimiter=";")
        return [row["Betonstaalkwaliteit"].strip('"') for row in csv_reader]
