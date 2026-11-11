"""Inside right: how MonPiz was born, beside the network of stores.

The story photo is shown whole, never cropped: the first paragraphs run
across the column, the last one sits beside the photo, and that pair is
anchored to the bottom margin so it lines up with the retailers footer.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..geometry import Box
from ..models import Retailers, Story
from ..surface import Surface
from .base import RenderContext, draw_block_heading, split_halves
from .retailers import draw_retailers

TITLE_TO_TEXT = 20.0
PARAGRAPH_GAP = 6.0
PHOTO_MAX_SHARE = 0.46  # the photo grows to fill the room, up to this share of the column width
TEXT_TO_PHOTO = 16.0  # last paragraph above -> top of the photo
PHOTO_GAP = 12.0  # photo -> paragraph beside it


@dataclass(frozen=True, slots=True)
class StoryPanel:
    story: Story
    retailers: Retailers

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        surface.fill(ctx.theme.palette.paper)
        left, right = split_halves(surface, ctx)
        self._draw_story(surface, ctx, left)
        draw_retailers(surface, ctx, right, self.retailers)

    def _draw_story(self, surface: Surface, ctx: RenderContext, box: Box) -> None:
        t, s = ctx.theme.type, self.story
        last = draw_block_heading(surface, ctx, box.x, box.top + 6, box.width, s.eyebrow, s.title)
        paragraphs = list(s.paragraphs)
        beside = paragraphs.pop() if s.photo and len(paragraphs) > 1 else None

        baseline = last + TITLE_TO_TEXT
        for paragraph in paragraphs:
            last = surface.paragraph(paragraph, box.x, baseline, box.width, t.text)
            baseline = last + t.text.leading + PARAGRAPH_GAP
        if not s.photo:
            return

        # The whole photo at the bottom left, as large as the room allows, its last paragraph beside it.
        px_w, px_h = ctx.images.size(s.photo.path)
        room = box.bottom - (last + TEXT_TO_PHOTO)
        width = min(box.width * PHOTO_MAX_SHARE, room * px_w / px_h)
        height = width * px_h / px_w
        photo = Box(box.x, box.bottom - height, width, height)
        surface.image(ctx.images.fitted(s.photo.path, width, height), photo)
        if beside:
            x = photo.right + PHOTO_GAP
            lines = surface.lines(beside, t.text, box.right - x)
            first = box.bottom - (len(lines) - 1) * t.text.leading
            surface.paragraph(beside, x, first, box.right - x, t.text)
