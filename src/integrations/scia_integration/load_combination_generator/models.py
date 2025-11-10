"""
Data models for load combination generation.

This module defines the data structures used to represent load metadata,
combination rules, and generated combinations.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LoadConfiguration(str, Enum):
    """
    Load configuration types for traffic loads.

    Traffic loads are generated in different configurations to represent
    different positioning scenarios on the bridge.

    Note: Configuration D is used for the second half of the BG10000 series
    where notional lanes 2 and 3 are switched compared to Configuration C.
    Config D tandems combine with Config C UDLs.
    """

    CONF_A = "A"
    CONF_B = "B"
    CONF_C = "C"
    CONF_D = "D"  # Second half of BG10000 series (lanes 2/3 switched)
    NONE = "None"  # For non-traffic loads


class LoadCategory(str, Enum):
    """
    High-level load categories.

    Used to determine which loads can be combined and which rules apply.
    """

    PERMANENT = "permanent"
    TRAFFIC_UDL = "traffic_udl"
    TRAFFIC_TANDEM = "traffic_tandem"
    TEMPERATURE = "temperature"
    PEDESTRIAN = "pedestrian"
    SERVICE_VEHICLE = "service_vehicle"
    UNINTENDED_VEHICLE = "unintended_vehicle"
    TRAM = "tram"


class LoadMetadata(BaseModel):
    """
    Metadata describing a load case for combination generation.

    This model extracts and stores all relevant information from a load case
    that's needed to determine valid combinations.
    """

    load_case_name: str = Field(description="SCIA load case name (e.g., BG4001, BG8001)")
    category: LoadCategory = Field(description="High-level load category")
    configuration: LoadConfiguration = Field(default=LoadConfiguration.NONE, description="Configuration (A, B, C) for traffic loads")
    notional_lane: int | None = Field(default=None, description="Notional lane number (1, 2, 3) for tandem loads")
    position_x: float | None = Field(default=None, description="X-position on bridge for tandem loads (meters)")
    span_index: int | None = Field(default=None, description="Span index for UDL loads")
    title: str = Field(default="", description="Human-readable title/description")
    load_group_name: str | None = Field(default=None, description="SCIA load group name")

    model_config = {"validate_assignment": True}

    @field_validator("notional_lane")
    @classmethod
    def validate_notional_lane(cls, value: int | None) -> int | None:
        """
        Validate notional lane number.

        :param value: Lane number to validate
        :type value: int | None
        :returns: Validated lane number
        :rtype: int | None
        :raises ValueError: If lane number is invalid
        """
        if value is not None and value not in [1, 2, 3]:
            raise ValueError(f"Notional lane must be 1, 2, or 3, got {value}")
        return value

    def is_traffic_load(self) -> bool:
        """
        Check if this is a traffic load (UDL or tandem).

        :returns: True if traffic load, False otherwise
        :rtype: bool
        """
        return self.category in [LoadCategory.TRAFFIC_UDL, LoadCategory.TRAFFIC_TANDEM]

    def has_configuration(self) -> bool:
        """
        Check if this load has a configuration (A, B, C).

        :returns: True if load has a configuration, False otherwise
        :rtype: bool
        """
        return self.configuration != LoadConfiguration.NONE

    def get_lane_key(self) -> str:
        """
        Get a unique key for the notional lane.

        Used to ensure only one tandem per lane in a combination.

        :returns: Lane key string (e.g., "RS1", "RS2")
        :rtype: str
        """
        if self.notional_lane is None:
            return "NO_LANE"
        return f"RS{self.notional_lane}"


class TrafficLoadCombination(BaseModel):
    """
    A valid combination of traffic loads.

    Represents a set of load cases that can physically occur together
    and share the same configuration.
    """

    combination_id: str = Field(description="Unique identifier for this combination")
    configuration: LoadConfiguration = Field(description="Configuration this combination belongs to")
    load_case_names: list[str] = Field(default_factory=list, description="List of load case names in this combination")
    udl_loads: list[str] = Field(default_factory=list, description="UDL load case names")
    tandem_loads: dict[str, str] = Field(default_factory=dict, description="Tandem loads by lane (e.g., {'RS1': 'BG8001', 'RS2': 'BG9001'})")
    description: str = Field(default="", description="Human-readable description")

    model_config = {"validate_assignment": True}

    def get_all_load_cases(self) -> list[str]:
        """
        Get all load case names in this combination.

        :returns: List of all load case names
        :rtype: list[str]
        """
        return self.udl_loads + list(self.tandem_loads.values())

    def get_lane_count(self) -> int:
        """
        Get the number of notional lanes with tandem loads.

        :returns: Number of active lanes
        :rtype: int
        """
        return len(self.tandem_loads)


class CombinationConstraints(BaseModel):
    """
    Constraints and rules for combination generation.

    Defines the rules that must be satisfied for a combination to be valid.
    """

    max_lanes: int = Field(default=3, description="Maximum number of notional lanes on bridge")
    allow_mixed_configurations: bool = Field(default=False, description="Whether to allow mixing configurations (should be False for traffic loads)")
    require_udl_with_tandem: bool = Field(default=False, description="Whether UDL must always accompany tandem loads")
    min_tandem_spacing: float | None = Field(default=None, description="Minimum spacing between tandem loads in meters (if applicable)")

    model_config = {"validate_assignment": True}


class CombinationGenerationResult(BaseModel):
    """
    Result of combination generation process.

    Contains the generated combinations and metadata about the generation process.
    """

    combinations: list[TrafficLoadCombination] = Field(default_factory=list, description="List of valid traffic load combinations")
    total_count: int = Field(default=0, description="Total number of combinations generated")
    by_configuration: dict[str, int] = Field(default_factory=dict, description="Count of combinations per configuration")
    load_metadata: dict[str, LoadMetadata] = Field(default_factory=dict, description="Metadata for all processed loads")
    warnings: list[str] = Field(default_factory=list, description="Warnings generated during processing")
    statistics: dict[str, Any] = Field(default_factory=dict, description="Additional statistics")

    model_config = {"validate_assignment": True}

    def get_combinations_for_config(self, config: LoadConfiguration) -> list[TrafficLoadCombination]:
        """
        Get all combinations for a specific configuration.

        :param config: Configuration to filter by
        :type config: LoadConfiguration
        :returns: List of combinations for that configuration
        :rtype: list[TrafficLoadCombination]
        """
        return [comb for comb in self.combinations if comb.configuration == config]
