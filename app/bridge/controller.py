"""
Controller for the individual Bridge entity.

This module serves as the main entry point for VIKTOR to discover the BridgeController.
The actual implementation uses a mixin architecture for better organization and
maintainability, with mixins located in the app/bridge/controller/ subfolder.
"""

# Import the actual controller from the mixin-based architecture
from app.bridge.controller.base_controller import BridgeController

# Re-export for VIKTOR to discover
__all__ = ["BridgeController"]

