"""
Load combination generator for SCIA models.

This module provides utilities for generating valid load combinations that respect
configuration constraints and prevent physically impossible load scenarios.

Key features:
- Configuration-based grouping (A, B, C)
- Prevention of overlapping tandem loads
- Ensures only one tandem per notional lane per combination
- Matches UDL and tandem loads by configuration
"""

from .combination_generator import TrafficLoadCombinationGenerator
from .models import LoadMetadata, TrafficLoadCombination
from .traffic_load_rules import TrafficLoadRules

__all__ = [
    "LoadMetadata",
    "TrafficLoadCombination",
    "TrafficLoadCombinationGenerator",
    "TrafficLoadRules",
]
