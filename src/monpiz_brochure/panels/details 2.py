"""The details row: round photo, name and description of each part of the shoe.

Not a panel of its own: it sits under the material samples (see :mod:`materials`).
Gaps between lines of text grow with the theme's type scale.
"""

from __future__ import annotations

from ..format import mm
from ..geometry import Box, columns
from ..models import Details
from ..surface import Surface
from .base import BLOCK_EYEBROW_TO_TITLE, RenderContext, draw_block_heading

IMAGE = mm(14.0)  # diameter of the round photos, at type scale 1
HEADING_TO_ROW = 14.0  # last title baseline -> top of the photos
IMAGE_TO_NAME = 10.0
NAME_TO_TEXT = 10.0


def _image(ctx: RenderContext) -> float:
    return IMAGE * ctx.theme.scale


def _text_lines(surface: Surface, ctx: RenderContext, details: Details, width: float) -> int:
    t, g = ctx.theme.type, ctx.theme.grid
    cell = columns(0, width, 4, g.gutter)[0][1]
    return max(len(surface.lines(item.description, t.small, cell)) for item in details.items)


def details_height(surface: Surface, ctx: RenderContext, details: Details, width: float) -> float:
    """Height of the block, from its top to the last description baseline."""
    t, s = ctx.theme.type, ctx.theme.space
    heading = (
        6
        + s(BLOCK_EYEBROW_TO_TITLE)
        + (len(surface.lines(details.title, t.heading, width)) - 1) * t.heading.leading
    )
    lines = _text_lines(surface, ctx, details, width)
    return (
        heading
        + s(HEADING_TO_ROW)
        + _image(ctx)
        + s(IMAGE_TO_NAME)
        + s(NAME_TO_TEXT)
        + (lines - 1) * t.small.leading
    )


def draw_details(surface: Surface, ctx: RenderContext, box: Box, details: Details) -> None:
    t, g, s = ctx.theme.type, ctx.theme.grid, ctx.theme.space
    last = draw_block_heading(surface, ctx, box.x, box.top + 6, box.width, details.eyebrow, details.title)
    top = last + s(HEADING_TO_ROW)
    side = _image(ctx)
    for item, (x, width) in zip(details.items, columns(box.x, box.right, 4, g.gutter), strict=False):
        surface.image(ctx.images.fitted(item.image, side, side), Box(x, top, side, side))
        name = top + side + s(IMAGE_TO_NAME)
        surface.text(item.name, x, name, t.item)
        surface.paragraph(item.description, x, name + s(NAME_TO_TEXT), width, t.small)
