"""One class per panel of the brochure; details and retailers are blocks inside them."""

from .back import BackPanel
from .base import Panel, RenderContext
from .cover import CoverPanel
from .materials import MaterialsPanel
from .story import StoryPanel

__all__ = ["BackPanel", "CoverPanel", "MaterialsPanel", "Panel", "RenderContext", "StoryPanel"]
