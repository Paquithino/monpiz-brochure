"""Shared panel infrastructure: render context, panel protocol, common blocks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from reportlab.lib.colors import Color, HexColor

from ..geometry import Box
from ..images import ImageLibrary
from ..models import Photo
from ..surface import Surface
from ..theme import Theme

MIN_PRINT_DPI = 240.0  # below this a photo may print soft
GUIDE_COLOR = HexColor("#E6007E")  # process magenta: unmistakably not part of the design
EYEBROW_TO_TITLE = 25.0  # eyebrow baseline -> first title baseline
BLOCK_EYEBROW_TO_TITLE = 20.0


@dataclass(slots=True)
class RenderContext:
    theme: Theme
    images: ImageLibrary
    logo: Path
    guides: bool = False  # proofing marks inside the panels (e.g. where the swatch goes)
    swatch_preview: bool = False  # a photo of the material where the real sample will be glued
    warnings: list[str] = field(default_factory=list)


class Panel(Protocol):
    def draw(self, surface: Surface, ctx: RenderContext) -> None: ...


def draw_photo(
    surface: Surface, ctx: RenderContext, photo: Photo, box: Box, *, scrim: Color | None = None
) -> None:
    """``photo`` filling ``box``; sides on a trim edge run into the bleed."""
    target = surface.bled(box)
    dpi = ctx.images.effective_dpi(photo.path, target.width, target.height, photo.zoom)
    if dpi < MIN_PRINT_DPI:
        ctx.warnings.append(
            f"{photo.path}: stampata a {dpi:.0f} dpi (consigliati almeno {MIN_PRINT_DPI:.0f})"
        )
    image = ctx.images.cover(
        photo.path, target.width, target.height, focus=photo.focus, zoom=photo.zoom, scrim=scrim
    )
    surface.image(image, target)


def logo_height(ctx: RenderContext, width: float) -> float:
    px_w, px_h = ctx.images.size(ctx.logo)
    return width * px_h / px_w


def draw_logo(
    surface: Surface, ctx: RenderContext, x: float, top: float, width: float, color: Color | None
) -> float:
    """The logo, ``width`` points wide: original colours, or flat ``color``. Returns its height."""
    height = logo_height(ctx, width)
    image = (
        ctx.images.fitted(ctx.logo, width, height)
        if color is None
        else ctx.images.tinted(ctx.logo, color, width, height)
    )
    surface.image(image, Box(x, top, width, height))
    return height


def draw_heading(
    surface: Surface,
    ctx: RenderContext,
    x: float,
    baseline: float,
    width: float,
    eyebrow: str,
    title: str,
    title_italic: str = "",
) -> float:
    """Eyebrow, title and an optional italic line under it. Returns the last baseline."""
    t = ctx.theme.type
    surface.text(eyebrow, x, baseline, t.eyebrow)
    last = surface.paragraph(title, x, baseline + EYEBROW_TO_TITLE, width, t.title)
    if title_italic:
        last = surface.paragraph(title_italic, x, last + t.title.leading, width, t.title_italic)
    return last


def draw_block_heading(
    surface: Surface, ctx: RenderContext, x: float, baseline: float, width: float, eyebrow: str, title: str
) -> float:
    """Smaller eyebrow + title, for a block sharing the panel with another. Returns the last baseline."""
    t = ctx.theme.type
    surface.text(eyebrow, x, baseline, t.eyebrow)
    return surface.paragraph(title, x, baseline + BLOCK_EYEBROW_TO_TITLE, width, t.heading)


SPLIT_GAP = 17.0  # each half -> the hairline in the middle (6 mm)


def split_halves(surface: Surface, ctx: RenderContext) -> tuple[Box, Box]:
    """The content area cut in two by a vertical hairline: (left, right) boxes."""
    p, m = ctx.theme.palette, ctx.theme.grid.margin
    inner = Box(m, m, surface.width - 2 * m, surface.height - 2 * m)
    middle = inner.x + inner.width / 2
    surface.vline(middle, inner.top, inner.bottom, p.rule)
    left = Box(inner.x, inner.top, middle - SPLIT_GAP - inner.x, inner.height)
    right = Box(middle + SPLIT_GAP, inner.top, inner.right - middle - SPLIT_GAP, inner.height)
    return left, right
