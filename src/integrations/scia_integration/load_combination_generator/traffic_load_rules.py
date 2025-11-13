"""
Rules for valid traffic load combinations.

This module defines the rules that determine which traffic loads can be
combined together and which combinations are physically impossible or
not allowed by code.
"""

from src.integrations.scia_integration.types import LoadConfiguration

from .models import LoadMetadata, TrafficLoadCombination


class TrafficLoadRules:
    """
    Rules engine for validating and filtering traffic load combinations.

    This class encapsulates all the logic for determining which traffic loads
    can be combined together based on configuration, position, and lane constraints.
    """

    @staticmethod
    def _get_traffic_configurations(loads: list[LoadMetadata]) -> list[LoadConfiguration]:
        """
        Extract traffic configurations from loads, excluding NONE.

        :param loads: List of load metadata
        :type loads: list[LoadMetadata]
        :returns: List of traffic configurations (excluding NONE)
        :rtype: list[LoadConfiguration]
        """
        return [load.configuration for load in loads if load.has_configuration() and load.configuration != LoadConfiguration.NONE]

    @staticmethod
    def can_combine_configurations(config_a: LoadConfiguration, config_b: LoadConfiguration) -> bool:
        """
        Check if two configurations can be combined.

        Traffic loads from different configurations (A, B, C, D) represent mutually
        exclusive positioning scenarios and cannot occur simultaneously.

        :param config_a: First configuration
        :type config_a: LoadConfiguration
        :param config_b: Second configuration
        :type config_b: LoadConfiguration
        :returns: True if configurations can be combined, False otherwise
        :rtype: bool
        """
        # NONE configuration can combine with anything (non-traffic loads)
        if LoadConfiguration.NONE in (config_a, config_b):
            return True
        # Otherwise, must be the same configuration
        return config_a == config_b

    @staticmethod
    def can_combine_tandem_loads(load_a: LoadMetadata, load_b: LoadMetadata) -> bool:
        """
        Check if two tandem loads can be combined.

        Rules:
        1. Must be from the same configuration
        2. Must be on different notional lanes
        3. Should not overlap spatially (same position on different lanes is OK)

        :param load_a: First tandem load metadata
        :type load_a: LoadMetadata
        :param load_b: Second tandem load metadata
        :type load_b: LoadMetadata
        :returns: True if tandem loads can be combined, False otherwise
        :rtype: bool
        """
        # Must be same configuration
        if not TrafficLoadRules.can_combine_configurations(load_a.configuration, load_b.configuration):
            return False

        # Must be on different lanes
        # Same position on different lanes is OK per Eurocode
        # (traffic loads can occur simultaneously on different lanes)
        return not (load_a.notional_lane is not None and load_b.notional_lane is not None and load_a.notional_lane == load_b.notional_lane)

    @staticmethod
    def can_combine_udl_with_tandem(udl: LoadMetadata, tandem: LoadMetadata) -> bool:
        """
        Check if a UDL load can be combined with a tandem load.

        Rules:
        1. Must be from the same configuration
        2. UDL and tandem should represent compatible loading scenarios

        :param udl: UDL load metadata
        :type udl: LoadMetadata
        :param tandem: Tandem load metadata
        :type tandem: LoadMetadata
        :returns: True if loads can be combined, False otherwise
        :rtype: bool
        """
        # Must be same configuration
        return TrafficLoadRules.can_combine_configurations(udl.configuration, tandem.configuration)

    @staticmethod
    def validate_lane_uniqueness(loads: list[LoadMetadata]) -> bool:
        """
        Validate that each notional lane appears at most once.

        A valid combination can have at most one tandem load per notional lane.

        :param loads: List of load metadata to validate
        :type loads: list[LoadMetadata]
        :returns: True if each lane appears at most once, False otherwise
        :rtype: bool
        """
        lanes_used = set()
        for load in loads:
            if load.notional_lane is not None:
                if load.notional_lane in lanes_used:
                    return False
                lanes_used.add(load.notional_lane)
        return True

    @staticmethod
    def validate_configuration_consistency(loads: list[LoadMetadata]) -> bool:
        """
        Validate that all traffic loads share the same configuration.

        Traffic loads must all be from configuration A, B, or C - not mixed.

        :param loads: List of load metadata to validate
        :type loads: list[LoadMetadata]
        :returns: True if configurations are consistent, False otherwise
        :rtype: bool
        """
        traffic_configs = TrafficLoadRules._get_traffic_configurations(loads)

        if not traffic_configs:
            return True  # No traffic loads with configuration

        # All traffic loads must have the same configuration
        return len(set(traffic_configs)) <= 1

    @staticmethod
    def get_configuration_from_loads(loads: list[LoadMetadata]) -> LoadConfiguration:
        """
        Get the configuration from a list of loads.

        Returns the common configuration if all traffic loads share one,
        otherwise returns NONE.

        Prerequisites:
            - Should be called after validate_configuration_consistency() to ensure
            all loads share the same configuration (A, B, C, D).
            - Configuration D has specific rules and is handled separately in
            certain scenarios

        Behavior:
            - If multiple different configurations exist, returns the first one.
            This should not occur if validate_configuration_consistency() was
            called first.
            - Returns NONE if no traffic loads with configuration are found.

        :param loads: List of load metadata
        :type loads: list[LoadMetadata]
        :returns: Common configuration or NONE
        :rtype: LoadConfiguration
        """
        traffic_configs = TrafficLoadRules._get_traffic_configurations(loads)

        if not traffic_configs:
            return LoadConfiguration.NONE

        # Get the first configuration (all should be the same if valid)
        return traffic_configs[0]

    @staticmethod
    def validate_combination(combination: TrafficLoadCombination, load_metadata: dict[str, LoadMetadata]) -> tuple[bool, list[str]]:
        """
        Validate a complete traffic load combination.

        Checks all rules and returns validation status with any error messages.

        :param combination: Combination to validate
        :type combination: TrafficLoadCombination
        :param load_metadata: Dictionary mapping load case names to metadata
        :type load_metadata: dict[str, LoadMetadata]
        :returns: Tuple of (is_valid, list_of_errors)
        :rtype: tuple[bool, list[str]]
        """
        errors = []

        # Get metadata for all loads in combination
        loads = []
        for load_name in combination.get_all_load_cases():
            if load_name in load_metadata:
                loads.append(load_metadata[load_name])
            else:
                errors.append(f"Load case {load_name} not found in metadata")

        if not loads:
            errors.append("Combination has no valid loads")
            return False, errors

        # Check configuration consistency
        if not TrafficLoadRules.validate_configuration_consistency(loads):
            errors.append("Mixed configurations detected (A, B, C cannot be combined)")

        # Check lane uniqueness for tandem loads
        if not TrafficLoadRules.validate_lane_uniqueness(loads):
            errors.append("Multiple tandem loads on the same notional lane")

        # Verify configuration matches combination's declared configuration
        actual_config = TrafficLoadRules.get_configuration_from_loads(loads)
        if actual_config not in (LoadConfiguration.NONE, combination.configuration):
            errors.append(f"Combination config mismatch: declared {combination.configuration}, actual {actual_config}")

        return len(errors) == 0, errors

    @staticmethod
    def is_valid_combination_set(loads: list[LoadMetadata]) -> bool:
        """
        Quick check if a set of loads forms a valid combination.

        :param loads: List of load metadata to check
        :type loads: list[LoadMetadata]
        :returns: True if valid combination, False otherwise
        :rtype: bool
        """
        return TrafficLoadRules.validate_configuration_consistency(loads) and TrafficLoadRules.validate_lane_uniqueness(loads)
