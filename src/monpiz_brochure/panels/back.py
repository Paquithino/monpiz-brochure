"""Back cover: how to reach MonPiz, a QR code to the lookbook, the signature."""

from __future__ import annotations

from dataclasses import dataclass

from ..contacts import contact
from ..format import mm
from ..geometry import Box, columns
from ..models import Back
from ..surface import Align, Surface
from .base import RenderContext, draw_heading, draw_logo, logo_height

TEXT_WIDTH = 0.56  # share of the panel width for the title and text
TITLE_TO_TEXT = 20.0
QR_SIDE = mm(22.0)
QR_LABEL_GAP = 7.0  # label baseline above the QR code
BAND_TO_RULE = 12.0  # bottom of the contacts band -> footer rule
CONTACT_ROW = 27.0  # label baseline -> next label baseline
LABEL_TO_VALUE = 10.5
FOOTER_RULE = 19.0  # rule above the bottom baseline
LOGO_WIDTH = mm(20.0)
LOGO_DROP = 2.0  # the script letters sit slightly below the footer baseline


@dataclass(frozen=True, slots=True)
class BackPanel:
    back: Back

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        m, right = g.margin, surface.width - g.margin
        surface.fill(p.paper)

        text_width = surface.width * TEXT_WIDTH
        last = draw_heading(
            surface, ctx, m, m + 6, text_width, self.back.eyebrow, self.back.title, self.back.title_italic
        )
        if self.back.text:
            surface.paragraph(self.back.text, m, last + TITLE_TO_TEXT, text_width, t.text)

        # Bottom band, above the footer rule: contacts on two columns, QR code on the right.
        bottom = surface.height - m
        rule = bottom - FOOTER_RULE
        band_bottom = rule - BAND_TO_RULE
        contacts_right = right
        if self.back.qr:
            qr = Box(right - QR_SIDE, band_bottom - QR_SIDE, QR_SIDE, QR_SIDE)
            surface.qr(self.back.qr.url, qr, p.ink)
            surface.text(self.back.qr.label, qr.right, qr.top - QR_LABEL_GAP, t.label, Align.RIGHT)
            contacts_right = qr.x - 2 * g.gutter

        cells = columns(m, contacts_right, 2, g.gutter)
        items = [contact(raw) for raw in self.back.contacts]
        rows = (len(items) + 1) // 2
        first_label = band_bottom - LABEL_TO_VALUE - (rows - 1) * CONTACT_ROW
        for index, item in enumerate(items):
            x, width = cells[index % 2]
            baseline = first_label + (index // 2) * CONTACT_ROW
            surface.text(item.label, x, baseline, t.label)
            value_width = surface.text(item.text, x, baseline + LABEL_TO_VALUE, t.value)
            if item.href:
                surface.link(item.href, Box(x, baseline + 2, min(value_width, width), LABEL_TO_VALUE + 2))

        surface.hline(m, right, rule, p.rule)
        if self.back.footer:
            surface.text(self.back.footer, m, bottom, t.small)
        logo_top = bottom + LOGO_DROP - logo_height(ctx, LOGO_WIDTH)
        draw_logo(surface, ctx, right - LOGO_WIDTH, logo_top, LOGO_WIDTH, None)
