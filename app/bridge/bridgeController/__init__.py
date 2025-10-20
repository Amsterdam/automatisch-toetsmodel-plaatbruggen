"""
Controller components for Bridge entity using component-based architecture.

This package contains the component implementations for the BridgeController.
The actual BridgeController class definition is in app/bridge/controller.py
(parent directory) to satisfy VIKTOR's introspection requirements.

Individual components:
- controller_utils.py - Utility methods for other components
- info_views.py - Map views and info displays
- geometry_views.py - 3D and 2D visualization views
- scia_integration.py - SCIA Engineer integration
- idea_integration.py - IDEA StatiCa RCS integration
- optimization.py - UC optimization functionality
- report_views.py - PDF report generation
"""

# Note: We don't re-export BridgeController here to avoid circular imports.
# Import from app.bridge.controller directly instead.
