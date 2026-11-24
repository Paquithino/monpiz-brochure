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

from ..errors import ContentError
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
MIN_RULE_GAP = 12.0  # hairline -> blocks above and below, at least


@dataclass(frozen=True, slots=True)
class MaterialsPanel:
    materials: Materials
    details: Details

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        """Materials from the top margin, details down to the bottom one, the hairline
        halfway through the space left between them."""
        p, m = ctx.theme.palette, ctx.theme.grid.margin
        surface.fill(p.paper)
        inner = Box(m, m, surface.width - 2 * m, surface.height - 2 * m)
        materials_bottom = self._draw_materials(surface, ctx, inner)
        details_top = inner.bottom - details_height(surface, ctx, self.details, inner.width)
        if details_top - materials_bottom < 2 * ctx.theme.space(MIN_RULE_GAP):
            raise ContentError(
                "I campioni sono troppo alti per questo formato: riduci "
                "`materials.swatch_height_mm` o `format.type_scale`."
            )
        rule = (materials_bottom + details_top) / 2
        surface.hline(inner.x, inner.right, rule, p.rule)
        draw_details(
            surface, ctx, Box(inner.x, details_top, inner.width, inner.bottom - details_top), self.details
        )

    def _draw_materials(self, surface: Surface, ctx: RenderContext, box: Box) -> float:
        """Heading, frames, names and texts from ``box.top``; returns the last baseline."""
        p, t, g, s = ctx.theme.palette, ctx.theme.type, ctx.theme.grid, ctx.theme.space
        mat = self.materials
        last = draw_block_heading(surface, ctx, box.x, box.top + 6, box.width, mat.eyebrow, mat.title)

        cells = columns(box.x, box.right, 4, g.gutter)
        frame_w = mm(mat.swatch_width_mm) + 2 * FRAME_MARGIN
        frame_h = mm(mat.swatch_height_mm) + 2 * FRAME_MARGIN
        if frame_w > cells[0][1] + 0.5:
            widest = (cells[0][1] - 2 * FRAME_MARGIN) / mm(1)
            raise ContentError(
                f"Campioni larghi {mat.swatch_width_mm:g} mm: in questo formato ci stanno "
                f"al massimo {widest:.0f} mm (`materials.swatch_width_mm`)."
            )

        top = last + s(HEADING_TO_FRAMES)
        bottom = top
        for swatch, (x, width) in zip(mat.items, cells, strict=False):
            frame = Box(x, top, frame_w, frame_h)
            sample = frame.inset(FRAME_MARGIN)
            if ctx.swatch_preview and swatch.preview:
                surface.image(ctx.images.cover(swatch.preview, sample.width, sample.height), sample)
            _draw_frame(surface, frame, p.accent)
            if ctx.guides:
                surface.rect(sample, stroke=GUIDE_COLOR, width=0.4, dash=(3, 2))
            name = frame.bottom + s(FRAME_TO_NAME)
            surface.text(swatch.name, x, name, t.item)
            bottom = max(bottom, surface.paragraph(swatch.text, x, name + s(NAME_TO_TEXT), width, t.small))
        return bottom


def _draw_frame(surface: Surface, frame: Box, color: Color) -> None:
    """Hairline frame with heavier corner ticks, like a passe-partout."""
    surface.rect(frame, stroke=color, width=0.35)
    for x, dx in ((frame.x, 1), (frame.right, -1)):
        for y, dy in ((frame.top, 1), (frame.bottom, -1)):
            surface.polyline([(x + dx * CORNER, y), (x, y), (x, y + dy * CORNER)], color, 1.0)
