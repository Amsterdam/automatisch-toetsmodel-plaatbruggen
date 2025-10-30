"""
SCIA integration package for defining and building bridge models.

This package contains the core, SDK-independent logic for constructing a SCIA Engineer bridge model.
It uses a builder pattern, defined by the `SciaModelBuilder` interface in `model/scia_model_interface.py`,
to remain decoupled from the VIKTOR SDK.

Modules:
- model/: Model building, geometry, and structural elements
- load_system/: Load cases, groups, combinations, generators, and load calculators
- results/: Results processing, visualization, and unit conversion
- scia_loads/: Load application (surface and point loads)
- constants/: Shared constants and configuration
- scia_enums.py: Shared enumerations
- types.py: Shared type definitions
- scia_loads_compat.py: Backward compatibility layer
"""
