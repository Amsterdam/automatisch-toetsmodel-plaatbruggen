"""
Bridge controller - imports from modular controller structure.

This file exists for VIKTOR SDK compatibility. The actual implementation
is split across multiple mixin files in the controller/ subdirectory.
"""

from app.bridge.controller.base_controller import BridgeController

__all__ = ["BridgeController"]

