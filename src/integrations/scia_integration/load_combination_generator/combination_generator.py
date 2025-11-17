"""
Traffic load combination generator.

This module provides the main logic for generating valid traffic load combinations
based on configuration constraints and combination rules.
"""

import re
from collections import defaultdict
from itertools import combinations, product
from typing import Any

from src.integrations.scia_integration.types import LoadCategory, LoadConfiguration

from .models import (
    CombinationGenerationResult,
    LoadMetadata,
    TrafficLoadCombination,
    extract_configuration_from_string,
)


class TrafficLoadCombinationGenerator:
    """
    Generator for valid traffic load combinations.

    This class analyzes load cases, extracts metadata, and generates all valid
    combinations that respect configuration and positioning constraints.
    """

    def __init__(self) -> None:
        """
        Initialize the combination generator.

        The generator uses default combination rules and does not require
        external configuration.
        """

    def extract_metadata_from_load_cases(self, all_load_cases: dict[str, Any]) -> dict[str, LoadMetadata]:
        """
        Extract metadata from SCIA load case structure.

        Parses load case names, titles, and structure to extract configuration,
        lane, position, and other metadata needed for combination generation.

        :param all_load_cases: Nested dictionary of load cases from create_all_load_cases
        :type all_load_cases: dict[str, Any]
        :returns: Dictionary mapping load case names to metadata
        :rtype: dict[str, LoadMetadata]
        """
        metadata: dict[str, LoadMetadata] = {}

        # Process UDL traffic loads - now split into three categories
        # Combine all UDL cases from the three dictionaries
        all_udl_cases = {}
        for udl_key in ["udl_main_cases", "udl_other_cases", "udl_rest_cases"]:
            if udl_key in all_load_cases and isinstance(all_load_cases[udl_key], dict):
                all_udl_cases.update(all_load_cases[udl_key])

        # Also check for old structure for backward compatibility
        if "udl_traffic_cases" in all_load_cases:
            if isinstance(all_load_cases["udl_traffic_cases"], dict):
                all_udl_cases.update(all_load_cases["udl_traffic_cases"])

        if all_udl_cases:
            for key, load_case in all_udl_cases.items():
                # Skip backward compatibility aliases (rs_1, rs_2, rs_3)
                if key in ["rs_1", "rs_2", "rs_3"]:
                    continue

                load_name = self._get_load_case_name(load_case, key)
                title = self._get_load_case_description(load_case)
                config = extract_configuration_from_string(title)
                span_idx = self._extract_span_index_from_title(title)

                metadata[load_name] = LoadMetadata(
                    load_case_name=load_name,
                    category=LoadCategory.TRAFFIC_UDL,
                    configuration=config,
                    span_index=span_idx,
                    title=title,
                    load_group_name=self._get_udl_group_name(config),
                )

        # Process tandem system loads
        if "tandem_cases" in all_load_cases:
            tandem_cases = all_load_cases["tandem_cases"]
            if isinstance(tandem_cases, dict):
                for key, load_case in tandem_cases.items():
                    load_name = self._get_load_case_name(load_case, key)
                    title = self._get_load_case_description(load_case)
                    config = extract_configuration_from_string(title)
                    lane = self._extract_lane_from_title(title)
                    position_x = self._extract_position_from_title(title)

                    metadata[load_name] = LoadMetadata(
                        load_case_name=load_name,
                        category=LoadCategory.TRAFFIC_TANDEM,
                        configuration=config,
                        notional_lane=lane,
                        position_x=position_x,
                        title=title,
                        load_group_name=self._get_tandem_group_name(lane),
                    )

        return metadata

    def generate_traffic_combinations(self, load_metadata: dict[str, LoadMetadata]) -> CombinationGenerationResult:
        """
        Generate all valid traffic load combinations.

        Creates combinations that respect configuration constraints and lane rules.

        :param load_metadata: Dictionary of load metadata
        :type load_metadata: dict[str, LoadMetadata]
        :returns: Generated combinations and statistics
        :rtype: CombinationGenerationResult
        """
        result = CombinationGenerationResult(load_metadata=load_metadata)

        # Group loads by configuration
        loads_by_config = self._group_by_configuration(load_metadata)

        # Generate combinations for each configuration separately
        for config, loads in loads_by_config.items():
            if config == LoadConfiguration.NONE:
                continue  # Skip non-traffic loads

            config_combinations = self._generate_combinations_for_config(config, loads)
            result.combinations.extend(config_combinations)
            result.by_configuration[config.value] = len(config_combinations)

        result.total_count = len(result.combinations)
        result.statistics = self._calculate_statistics(result)

        return result

    def _generate_combinations_for_config(self, config: LoadConfiguration, loads: list[LoadMetadata]) -> list[TrafficLoadCombination]:  # noqa: C901
        """
        Generate all valid combinations for a single configuration.

        Handles edge cases:
        - Only UDL loads selected (no tandems)
        - Only tandem loads selected (no UDLs)
        - Neither selected (returns empty list)
        - Both selected (full combinations)

        :param config: Configuration to generate combinations for
        :type config: LoadConfiguration
        :param loads: List of loads in this configuration
        :type loads: list[LoadMetadata]
        :returns: List of valid combinations
        :rtype: list[TrafficLoadCombination]
        """
        combinations_list: list[TrafficLoadCombination] = []

        # Separate UDL and tandem loads
        udl_loads = [load for load in loads if load.category == LoadCategory.TRAFFIC_UDL]
        tandem_loads = [load for load in loads if load.category == LoadCategory.TRAFFIC_TANDEM]

        # Edge case: No loads selected at all
        if not udl_loads and not tandem_loads:
            return []

        # Group tandem loads by lane
        tandems_by_lane = self._group_tandem_by_lane(tandem_loads)

        # Generate tandem combinations (one per lane, all possible combinations)
        tandem_combinations = self._generate_tandem_combinations(tandems_by_lane)

        combination_id = 1

        # Case 1: Only UDL loads (no tandems)
        if udl_loads and not tandem_loads:
            # Generate all non-empty UDL combinations
            for udl_count in range(1, len(udl_loads) + 1):
                for udl_subset in combinations(udl_loads, udl_count):
                    combo = TrafficLoadCombination(
                        combination_id=f"TRAFFIC_{config.value}_UDL_{combination_id:04d}",
                        configuration=config,
                        udl_loads=[load.load_case_name for load in udl_subset],
                        tandem_loads={},
                        description=self._create_udl_only_description(config, list(udl_subset)),
                    )
                    combinations_list.append(combo)
                    combination_id += 1

        # Case 2: Only tandem loads (no UDLs)
        elif tandem_loads and not udl_loads:
            # Generate tandem-only combinations
            for tandem_combo in tandem_combinations:
                combo = TrafficLoadCombination(
                    combination_id=f"TRAFFIC_{config.value}_TANDEM_{combination_id:04d}",
                    configuration=config,
                    udl_loads=[],
                    tandem_loads=tandem_combo,
                    description=self._create_tandem_only_description(config, tandem_combo),
                )
                combinations_list.append(combo)
                combination_id += 1

        # Case 3: Both UDL and tandem loads present
        else:
            # Generate combinations with tandems + optional UDL
            for tandem_combo in tandem_combinations:
                # UDL loads can be added individually or not at all
                # Generate all subsets of UDL loads (including empty set)
                for udl_count in range(len(udl_loads) + 1):
                    for udl_subset in combinations(udl_loads, udl_count):
                        combo = TrafficLoadCombination(
                            combination_id=f"TRAFFIC_{config.value}_{combination_id:04d}",
                            configuration=config,
                            udl_loads=[load.load_case_name for load in udl_subset],
                            tandem_loads=tandem_combo,
                            description=self._create_combination_description(config, list(udl_subset), tandem_combo),
                        )
                        combinations_list.append(combo)
                        combination_id += 1

            # Also generate UDL-only combinations (without any tandems)
            for udl_count in range(1, len(udl_loads) + 1):
                for udl_subset in combinations(udl_loads, udl_count):
                    combo = TrafficLoadCombination(
                        combination_id=f"TRAFFIC_{config.value}_UDL_{combination_id:04d}",
                        configuration=config,
                        udl_loads=[load.load_case_name for load in udl_subset],
                        tandem_loads={},
                        description=self._create_udl_only_description(config, list(udl_subset)),
                    )
                    combinations_list.append(combo)
                    combination_id += 1

        return combinations_list

    def _generate_tandem_combinations(self, tandems_by_lane: dict[int, list[LoadMetadata]]) -> list[dict[str, str]]:
        """
        Generate all valid tandem load combinations.

        For each lane, pick one tandem position, combine across lanes.

        :param tandems_by_lane: Tandem loads grouped by lane number
        :type tandems_by_lane: dict[int, list[LoadMetadata]]
        :returns: List of tandem combinations (lane -> load_case_name)
        :rtype: list[dict[str, str]]
        """
        if not tandems_by_lane:
            return [{}]  # Empty combination

        # Get all lanes that have tandem loads
        lanes = sorted(tandems_by_lane.keys())

        # Generate all combinations: one tandem per lane
        # For each lane, we can choose any of its tandem positions
        lane_options = [tandems_by_lane[lane] for lane in lanes]

        combinations_list = []
        for tandem_tuple in product(*lane_options):
            combo_dict = {}
            for tandem_load in tandem_tuple:
                lane_key = tandem_load.get_lane_key()
                combo_dict[lane_key] = tandem_load.load_case_name
            combinations_list.append(combo_dict)

        return combinations_list

    def _group_by_configuration(self, load_metadata: dict[str, LoadMetadata]) -> dict[LoadConfiguration, list[LoadMetadata]]:
        """
        Group loads by configuration.

        :param load_metadata: Dictionary of load metadata
        :type load_metadata: dict[str, LoadMetadata]
        :returns: Loads grouped by configuration
        :rtype: dict[LoadConfiguration, list[LoadMetadata]]
        """
        groups: dict[LoadConfiguration, list[LoadMetadata]] = defaultdict(list)
        for load in load_metadata.values():
            if load.is_traffic_load():
                groups[load.configuration].append(load)
        return dict(groups)

    def _group_tandem_by_lane(self, tandem_loads: list[LoadMetadata]) -> dict[int, list[LoadMetadata]]:
        """
        Group tandem loads by notional lane.

        :param tandem_loads: List of tandem load metadata
        :type tandem_loads: list[LoadMetadata]
        :returns: Tandem loads grouped by lane number
        :rtype: dict[int, list[LoadMetadata]]
        """
        groups: dict[int, list[LoadMetadata]] = defaultdict(list)
        for load in tandem_loads:
            if load.notional_lane is not None:
                groups[load.notional_lane].append(load)
        return dict(groups)

    # ===== Helper methods for metadata extraction =====

    @staticmethod
    def _get_load_case_name(load_case: Any, fallback_key: str) -> str:  # noqa: ANN401
        """Get the load case name from a load case object."""
        if hasattr(load_case, "name"):
            return str(load_case.name)
        if hasattr(load_case, "Name"):
            return str(load_case.Name)
        return fallback_key

    @staticmethod
    def _get_load_case_description(load_case: Any) -> str:  # noqa: ANN401
        """Get the description/title from a load case object."""
        if hasattr(load_case, "description"):
            return str(load_case.description)
        if hasattr(load_case, "Description"):
            return str(load_case.Description)
        return ""

    @staticmethod
    def _extract_lane_from_title(title: str) -> int | None:
        """
        Extract notional lane number (1, 2, 3) from title.

        Looks for patterns like "rs 1", "RS 2", "lane 3".
        """
        # Try "rs X" pattern
        match = re.search(r"rs\s*(\d)", title, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Try "lane X" pattern
        match = re.search(r"lane\s*(\d)", title, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    @staticmethod
    def _extract_position_from_title(title: str) -> float | None:
        """
        Extract X position from title.

        Looks for patterns like "x = 2.5 m", "x=5.0m", "position 10.5".
        """
        # Try "x = X.X m" pattern
        match = re.search(r"x\s*=\s*([\d.]+)\s*m?", title, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return None

    @staticmethod
    def _extract_span_index_from_title(title: str) -> int | None:
        """
        Extract span index from title.

        Looks for patterns like "Span 1", "span 2".
        """
        match = re.search(r"span\s*(\d+)", title, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _get_udl_group_name(config: LoadConfiguration) -> str:
        """Get the load group name for UDL loads based on configuration."""
        if config == LoadConfiguration.CONF_A:
            return "LG4000 - UDL - conf. A"
        if config == LoadConfiguration.CONF_B:
            return "LG4001 - UDL - conf. B"
        if config == LoadConfiguration.CONF_C:
            return "LG4002 - UDL - conf. C"
        return "LG4000 - UDL - conf. A"  # Default

    @staticmethod
    def _get_tandem_group_name(lane: int | None) -> str:
        """Get the load group name for tandem loads based on lane."""
        if lane == 1:
            return "LG8000 - TS rijstrook 1"
        if lane == 2:
            return "LG9000 - TS rijstrook 2"
        if lane == 3:
            return "LG10000 - TS rijstrook 3"
        return "LG8000 - TS rijstrook 1"  # Default

    @staticmethod
    def _create_combination_description(config: LoadConfiguration, udl_loads: list[LoadMetadata], tandem_combo: dict[str, str]) -> str:
        """Create a human-readable description for a combination."""
        parts = [f"Config {config.value}:"]

        if udl_loads:
            parts.append(f"{len(udl_loads)} UDL")

        if tandem_combo:
            lanes = sorted([int(key[2:]) for key in tandem_combo])
            parts.append(f"TS lanes {','.join(map(str, lanes))}")

        return " ".join(parts)

    @staticmethod
    def _create_udl_only_description(config: LoadConfiguration, udl_loads: list[LoadMetadata]) -> str:
        """Create a description for UDL-only combination."""
        return f"Config {config.value}: {len(udl_loads)} UDL only"

    @staticmethod
    def _create_tandem_only_description(config: LoadConfiguration, tandem_combo: dict[str, str]) -> str:
        """
        Create a description for tandem-only combination.

        :param config: Configuration of the combination
        :type config: LoadConfiguration
        :param tandem_combo: Tandem loads by lane (e.g., {'RS1': 'BG8001', 'RS2': 'BG9001'})
        :type tandem_combo: dict[str, str]
        :returns: Human-readable description
        :rtype: str
        """
        if not tandem_combo:
            return f"Config {config.value}: No loads"

        lanes = sorted([int(key[2:]) for key in tandem_combo])
        return f"Config {config.value}: TS lanes {','.join(map(str, lanes))} only"

    @staticmethod
    def _calculate_statistics(result: CombinationGenerationResult) -> dict[str, Any]:
        """Calculate statistics about generated combinations."""
        stats = {
            "total_combinations": result.total_count,
            "by_configuration": result.by_configuration,
            "avg_loads_per_combination": 0.0,
            "combinations_with_tandem": 0,
            "combinations_udl_only": 0,
        }

        if result.combinations:
            total_loads = sum(len(combo.get_all_load_cases()) for combo in result.combinations)
            stats["avg_loads_per_combination"] = total_loads / len(result.combinations)
            stats["combinations_with_tandem"] = sum(1 for combo in result.combinations if combo.tandem_loads)
            stats["combinations_udl_only"] = sum(1 for combo in result.combinations if not combo.tandem_loads)

        return stats
