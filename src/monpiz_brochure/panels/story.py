"""Inside right: how MonPiz was born, beside the network of stores.

The story photo is shown whole, never cropped. When there is room, the first
paragraphs run across the column and the last one sits beside the photo,
that pair anchored to the bottom margin; with larger type (or a smaller
panel) all the text comes first and the photo, cropped per its focus and zoom, fills
the room left below across the whole column.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..geometry import Box
from ..models import Retailers, Story
from ..surface import Surface
from ..theme import TextStyle
from .base import RenderContext, draw_block_heading, draw_photo, split_halves
from .retailers import draw_retailers

TITLE_TO_TEXT = 20.0
PARAGRAPH_GAP = 6.0
PHOTO_MAX_SHARE = 0.46  # the photo grows to fill the room, up to this share of the column width
TEXT_TO_PHOTO = 16.0  # last paragraph above -> top of the photo
PHOTO_GAP = 12.0  # photo -> paragraph beside it
MIN_PHOTO_HEIGHT = 50.0  # below this the photo is left out rather than shown as a stamp


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
        """Last paragraph beside the photo when it fits; otherwise all the text first, the photo below."""
        sp, s = ctx.theme.space, self.story
        heading = draw_block_heading(surface, ctx, box.x, box.top + 6, box.width, s.eyebrow, s.title)
        first = heading + sp(TITLE_TO_TEXT)
        if s.photo is None:
            self._paragraphs(surface, ctx, s.paragraphs, box, first)
            return

        px_w, px_h = ctx.images.size(s.photo.path)
        if s.photo_layout == "beside" and len(s.paragraphs) > 1:
            last = self._measure(surface, ctx, s.paragraphs[:-1], box.width, first)
            width = min(box.width * PHOTO_MAX_SHARE, (box.bottom - last - sp(TEXT_TO_PHOTO)) * px_w / px_h)
            photo = Box(box.x, box.bottom - width * px_h / px_w, width, width * px_h / px_w)
            x = photo.right + PHOTO_GAP
            beside = surface.lines(s.paragraphs[-1], self._body(ctx), box.right - x)
            beside_top = box.bottom - (len(beside) - 1) * self._body(ctx).leading - self._body(ctx).size
            if beside_top >= last + sp(TEXT_TO_PHOTO) and photo.height >= MIN_PHOTO_HEIGHT:
                self._paragraphs(surface, ctx, s.paragraphs[:-1], box, first)
                surface.image(ctx.images.fitted(s.photo.path, photo.width, photo.height), photo)
                surface.paragraph(
                    s.paragraphs[-1],
                    x,
                    box.bottom - (len(beside) - 1) * self._body(ctx).leading,
                    box.right - x,
                    self._body(ctx),
                )
                return

        # Larger type or smaller panel: all the text first, then the photo across the whole
        # column, filling the room down to the bottom margin (cropped per its focus/zoom).
        last = self._paragraphs(surface, ctx, s.paragraphs, box, first)
        top = last + sp(TEXT_TO_PHOTO)
        if box.bottom - top >= MIN_PHOTO_HEIGHT:
            draw_photo(surface, ctx, s.photo, Box(box.x, top, box.width, box.bottom - top))

    def _body(self, ctx: RenderContext) -> TextStyle:
        return ctx.theme.type.text.scaled(self.story.text_scale)

    def _paragraphs(
        self, surface: Surface, ctx: RenderContext, paragraphs: list[str], box: Box, baseline: float
    ) -> float:
        """Draw full-width paragraphs from ``baseline``; returns the last baseline."""
        last = baseline
        for paragraph in paragraphs:
            last = surface.paragraph(paragraph, box.x, baseline, box.width, self._body(ctx))
            baseline = last + self._body(ctx).leading + ctx.theme.space(PARAGRAPH_GAP)
        return last

    def _measure(
        self, surface: Surface, ctx: RenderContext, paragraphs: list[str], width: float, baseline: float
    ) -> float:
        """Last baseline :meth:`_paragraphs` would reach, without drawing."""
        last = baseline
        for paragraph in paragraphs:
            last = (
                baseline
                + (len(surface.lines(paragraph, self._body(ctx), width)) - 1) * self._body(ctx).leading
            )
            baseline = last + self._body(ctx).leading + ctx.theme.space(PARAGRAPH_GAP)
        return last
