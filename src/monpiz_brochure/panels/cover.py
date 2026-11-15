"""Front cover: the logo, a title and the claim, over one of two backgrounds.

- ``photo`` with ``photo_layout: band``: the photo across the top, edge to
  edge, over a paper band with the text, so nothing covers the shoes;
- ``photo`` with ``photo_layout: full``: a full-bleed photo darkened at the
  bottom, light text on it;
- ``mosaic``: one studio shot per model in staggered rows on paper, like a
  catalogue flat lay, every shoe whole; text and logo below.

The text is laid out first, from the bottom up, so the mosaic knows how
much room is left above it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ContentError
from ..format import mm
from ..geometry import Box, brick_slots
from ..models import Cover
from ..surface import Align, Surface, text_width
from ..theme import TextStyle
from .base import RenderContext, draw_logo, draw_photo, logo_height

LOGO_WIDTH = mm(34.0)
CLAIM_WIDTH = 0.52  # share of the panel width
TITLE_TO_CLAIM = 17.0  # last title baseline -> first claim baseline

LOGO_TO_LABEL = 9.0  # mosaic cover: logo bottom -> label cap height

# Mosaic: bricks of 4 + 3 + 4 slots above the text
MOSAIC_COLUMNS = 4
MOSAIC_ROWS = 3
TILE_RATIO = 1.45  # width / height of a slot: most shots show a boot and its sole side by side
CLEAR_MARGIN = mm(4.0)  # free space kept around the logo and the text


@dataclass(frozen=True, slots=True)
class _Text:
    title: list[tuple[str, float]]  # (line, baseline)
    claim: list[tuple[str, float]]
    title_style: TextStyle
    claim_style: TextStyle
    label: TextStyle

    def zone(self, surface: Surface, margin: float) -> Box:
        """Area of the title and claim, from the top of the title to the bottom edge."""
        top = self.title[0][1] - self.title_style.size - CLEAR_MARGIN
        widest = max(text_width(line, style) for lines, style in self._blocks() for line, _ in lines)
        return Box(0, top, margin + widest + CLEAR_MARGIN, surface.height - top)

    def _blocks(self) -> list[tuple[list[tuple[str, float]], TextStyle]]:
        return [(self.title, self.title_style), (self.claim, self.claim_style)]

    def draw(self, surface: Surface, margin: float) -> None:
        for lines, style in self._blocks():
            for line, baseline in lines:
                surface.text(line, margin, baseline, style)


@dataclass(frozen=True, slots=True)
class CoverPanel:
    cover: Cover

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, m = ctx.theme.palette, ctx.theme.grid.margin
        dark = self.cover.photo is not None and self.cover.photo_layout == "full"
        text = self._layout(surface, ctx, dark)
        logo = self._logo_box(surface, ctx, text, dark)
        if dark and self.cover.photo is not None:
            draw_photo(surface, ctx, self.cover.photo, surface.box, scrim=p.forest)
        elif self.cover.photo is not None:  # band: photo on top, text on paper below it
            surface.fill(p.paper)
            band_top = min(text.zone(surface, m).top, logo.top) - CLEAR_MARGIN
            draw_photo(surface, ctx, self.cover.photo, Box(0, 0, surface.width, band_top))
        else:
            self._draw_mosaic(
                surface, ctx, top=m, bottom=min(text.zone(surface, m).top, logo.top) - CLEAR_MARGIN
            )
        draw_logo(surface, ctx, logo.x, logo.top, logo.width, p.on_dark if dark else None)
        text.draw(surface, m)
        if self.cover.label:
            surface.text(self.cover.label, surface.width - m, surface.height - m, text.label, Align.RIGHT)

    def _layout(self, surface: Surface, ctx: RenderContext, dark: bool) -> _Text:
        """Title and claim lines with their baselines, built from the bottom margin up."""
        p, t, m = ctx.theme.palette, ctx.theme.type, ctx.theme.grid.margin
        title_style = t.cover_title if dark else t.cover_title.with_color(p.ink)
        claim_style = t.claim if dark else t.claim.with_color(p.body)
        label = t.label.with_color(p.on_dark_accent if dark else p.accent)

        bottom = surface.height - m
        # Without a full-page photo, logo and label sit bottom right, beside the text: keep clear of them.
        corner = 0.0 if dark else max(LOGO_WIDTH, text_width(self.cover.label, label)) + CLEAR_MARGIN
        claim_width = min(surface.width * CLAIM_WIDTH, surface.width - 2 * m - corner)
        claim_lines = surface.lines(self.cover.claim, claim_style, claim_width)
        claim_top = bottom - (len(claim_lines) - 1) * claim_style.leading
        title_width = surface.width - 2 * m - (0.0 if dark else LOGO_WIDTH + CLEAR_MARGIN)
        title_lines = surface.lines(self.cover.title, title_style, title_width)
        title_top = claim_top - ctx.theme.space(TITLE_TO_CLAIM) - (len(title_lines) - 1) * title_style.leading
        return _Text(
            title=[(line, title_top + i * title_style.leading) for i, line in enumerate(title_lines)],
            claim=[(line, claim_top + i * claim_style.leading) for i, line in enumerate(claim_lines)],
            title_style=title_style,
            claim_style=claim_style,
            label=label,
        )

    def _logo_box(self, surface: Surface, ctx: RenderContext, text: _Text, dark: bool) -> Box:
        """Top left over a full-page photo; otherwise bottom right, above the label, in the text band."""
        m, height = ctx.theme.grid.margin, logo_height(ctx, LOGO_WIDTH)
        if dark:
            return Box(m, m, LOGO_WIDTH, height)
        bottom = surface.height - m
        if self.cover.label:
            bottom -= text.label.size + LOGO_TO_LABEL
        return Box(surface.width - m - LOGO_WIDTH, bottom - height, LOGO_WIDTH, height)

    def _draw_mosaic(self, surface: Surface, ctx: RenderContext, top: float, bottom: float) -> None:
        """One shot per slot between ``top`` and ``bottom``, every shoe whole, inside the margins."""
        p, m = ctx.theme.palette, ctx.theme.grid.margin
        page = surface.bled(surface.box)  # the image carries the paper colour into the bleed
        room = Box(m, top, surface.width - 2 * m, bottom - top)
        slots = brick_slots(room, MOSAIC_COLUMNS, MOSAIC_ROWS, TILE_RATIO)
        shots = self.cover.mosaic
        if len(shots) > len(slots):
            raise ContentError(
                f"La copertina ha posto per {len(slots)} foto, nel mosaico ce ne sono {len(shots)}."
            )
        placed = [
            (shot, Box(slot.x - page.x, slot.top - page.top, slot.width, slot.height))
            for shot, slot in zip(shots, slots, strict=False)
        ]
        surface.image(ctx.images.mosaic(placed, page.width, page.height, p.paper), page)
