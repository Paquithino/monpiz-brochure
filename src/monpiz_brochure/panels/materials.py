"""Inside left: real samples of the leathers to touch, then the details of the build.

Top: a row of printed frames, one per material, each a little larger than
its sample so that hand gluing need not be perfect. Nothing is printed inside
a frame but the paper colour; ``--guides`` shows the exact sample outline in
magenta, ``--swatch-preview`` a photo of the material (screen previews only).

Bottom, below a hairline: the details row (see :mod:`details`).
"""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib.colors import Color

from ..format import mm
from ..geometry import Box, columns
from ..models import Details, Materials
from ..surface import Surface
from .base import GUIDE_COLOR, RenderContext, draw_block_heading
from .details import details_height, draw_details

FRAME_MARGIN = mm(2.0)  # frame around each sample, per side
CORNER = mm(2.5)  # length of the corner ticks
HEADING_TO_FRAMES = 14.0  # last title baseline -> top of the frames
FRAME_TO_NAME = 13.0
NAME_TO_TEXT = 10.0
RULE_GAP = 16.0  # hairline -> blocks above and below


@dataclass(frozen=True, slots=True)
class MaterialsPanel:
    materials: Materials
    details: Details

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, m = ctx.theme.palette, ctx.theme.grid.margin
        surface.fill(p.paper)
        right, bottom = surface.width - m, surface.height - m
        details_top = bottom - details_height(ctx, self.details)
        draw_details(surface, ctx, Box(m, details_top, right - m, bottom - details_top), self.details)
        rule = details_top - RULE_GAP
        surface.hline(m, right, rule, p.rule)
        self._draw_materials(surface, ctx, Box(m, m, right - m, rule - RULE_GAP - m))

    def _draw_materials(self, surface: Surface, ctx: RenderContext, box: Box) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        mat = self.materials
        last = draw_block_heading(surface, ctx, box.x, box.top + 6, box.width, mat.eyebrow, mat.title)

        sample_w, sample_h = mm(mat.swatch_width_mm), mm(mat.swatch_height_mm)
        frame_w, frame_h = sample_w + 2 * FRAME_MARGIN, sample_h + 2 * FRAME_MARGIN
        top = last + HEADING_TO_FRAMES
        for swatch, (x, width) in zip(mat.items, columns(box.x, box.right, 4, g.gutter), strict=False):
            frame = Box(x, top, min(frame_w, width), frame_h)
            sample = frame.inset(FRAME_MARGIN)
            if ctx.swatch_preview and swatch.preview:
                surface.image(ctx.images.cover(swatch.preview, sample.width, sample.height), sample)
            _draw_frame(surface, frame, p.accent)
            if ctx.guides:
                surface.rect(sample, stroke=GUIDE_COLOR, width=0.4, dash=(3, 2))
            name = frame.bottom + FRAME_TO_NAME
            surface.text(swatch.name, x, name, t.item)
            surface.paragraph(swatch.text, x, name + NAME_TO_TEXT, width, t.small)


def _draw_frame(surface: Surface, frame: Box, color: Color) -> None:
    """Hairline frame with heavier corner ticks, like a passe-partout."""
    surface.rect(frame, stroke=color, width=0.35)
    for x, dx in ((frame.x, 1), (frame.right, -1)):
        for y, dy in ((frame.top, 1), (frame.bottom, -1)):
            surface.polyline([(x + dx * CORNER, y), (x, y), (x, y + dy * CORNER)], color, 1.0)
