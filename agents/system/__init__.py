"""System-focused agent namespace."""

from agents.system.ghost_browser import GhostBrowserAgent
from agents.system.stealth_controller import StealthControllerAgent
from agents.system.vision_overlord import VisionOverlordAgent

__all__ = [
    "VisionOverlordAgent",
    "StealthControllerAgent",
    "GhostBrowserAgent",
]

