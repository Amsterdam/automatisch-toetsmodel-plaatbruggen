"""
SCIA integration package for defining and building bridge models.

This package contains the core, SDK-independent logic for constructing a SCIA Engineer bridge model.
It uses a builder pattern, defined by the `SciaModelBuilder` interface in `scia_model_interface.py`,
to remain decoupled from the VIKTOR SDK.

Modules:
- scia_model: Orchestrates the entire model creation process.
- scia_bridge_geometry: Extracts and calculates pure geometry data from bridge parameters.
- scia_load_group: Creates standard load groups.
- scia_load_cases: Creates standard and dynamic load cases.
- scia_loads: Creates surface loads for traffic systems.
- scia_loads_helper: Provides helper functions for load case logic and manipulation.
- scia_load_combinations: Creates standard load combinations.
- scia_supports: Creates line supports for the bridge deck.
- scia_model_interface: Defines the `SciaModelBuilder` interface and common enumerations.
"""
