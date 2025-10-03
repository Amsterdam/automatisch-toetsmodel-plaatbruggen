"""
Bridge Controller - Backward Compatibility Module.

This module maintains backward compatibility with existing imports.
The actual controller implementation has been refactored into a mixin
architecture located in app/bridge/controller/.

All functionality has been preserved and organized into focused mixins:
- controller_utils.py: Helper methods and error handling
- info_views.py: Bridge location map and load combinations
- geometry_views.py: 3D model and 2D section views
- scia_integration.py: SCIA Engineer analysis integration
- idea_integration.py: IDEA StatiCa RCS integration
- report_views.py: PDF report generation
- base_controller.py: Main controller combining all mixins

Migration Guide:
    Old: from app.bridge.controller import BridgeController
    New: from app.bridge.controller import BridgeController  # Still works!

The refactoring provides:
- 94% reduction in main controller size (1974 → ~100 lines)
- Better code organization and maintainability
- Easier testing (each mixin independently testable)
- Clear separation of concerns
- Parallel development capability

For implementation details, see:
- app/bridge/controller/__init__.py
- app/bridge/controller/base_controller.py
"""

# Re-export BridgeController for backward compatibility
from app.bridge.controller import BridgeController

__all__ = ["BridgeController"]
