"""The details row: round photo, name and description of each part of the shoe.

Not a panel of its own: it sits under the material samples (see :mod:`materials`).
Each detail has its photo on the left and the words beside it, so four of
them fit across a panel without shrinking the text.
"""

from __future__ import annotations

from ..format import mm
from ..geometry import Box, columns
from ..models import Details
from ..surface import Surface
from .base import BLOCK_EYEBROW_TO_TITLE, RenderContext, draw_block_heading

IMAGE = mm(14.0)  # diameter of the round photos
HEADING_TO_ROW = 14.0  # last title baseline -> top of the photos
IMAGE_TO_NAME = 10.0
NAME_TO_TEXT = 10.0
TEXT_LINES = 2  # room kept for the longest description


def details_height(ctx: RenderContext, details: Details) -> float:
    """Height of the block, from its top to the last description baseline."""
    t = ctx.theme.type
    heading = 6 + BLOCK_EYEBROW_TO_TITLE + (len(details.title.splitlines()) - 1) * t.heading.leading
    return (
        heading + HEADING_TO_ROW + IMAGE + IMAGE_TO_NAME + NAME_TO_TEXT + (TEXT_LINES - 1) * t.small.leading
    )


def draw_details(surface: Surface, ctx: RenderContext, box: Box, details: Details) -> None:
    t, g = ctx.theme.type, ctx.theme.grid
    last = draw_block_heading(surface, ctx, box.x, box.top + 6, box.width, details.eyebrow, details.title)
    top = last + HEADING_TO_ROW
    for item, (x, width) in zip(details.items, columns(box.x, box.right, 4, g.gutter), strict=False):
        surface.image(ctx.images.fitted(item.image, IMAGE, IMAGE), Box(x, top, IMAGE, IMAGE))
        name = top + IMAGE + IMAGE_TO_NAME
        surface.text(item.name, x, name, t.item)
        surface.paragraph(item.description, x, name + NAME_TO_TEXT, width, t.small)
