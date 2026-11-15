"""Thin drawing layer over the ReportLab canvas, one panel at a time.

Coordinates are relative to the panel (origin top-left, y downwards), so a
panel module reads like its layout spec wherever it ends up on the sheet.

Bleed works as in the lookbook, with one difference: a panel has two kinds
of vertical edge. An edge on the outside of the sheet is a *trim* edge, and
anything touching it is pushed into the bleed; an edge on a fold is shared
with the next panel and nothing may cross it. The builder clips every panel
to its own area, so a photo can never spill over the fold.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from .geometry import Box, wrap_text
from .theme import TextStyle

EDGE_TOLERANCE = 0.5  # pt: a box this close to an edge counts as touching it


class Align(StrEnum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


def _shown(text: str, style: TextStyle) -> str:
    return text.upper() if style.uppercase else text


def text_width(text: str, style: TextStyle) -> float:
    """Advance width of ``text`` rendered in ``style``, tracking included."""
    shown = _shown(text, style)
    return float(stringWidth(shown, style.font, style.size)) + style.tracking * max(len(shown) - 1, 0)


class Surface:
    def __init__(
        self,
        canvas: Canvas,
        width: float,
        height: float,
        *,
        bleed: float = 0.0,
        trim_left: bool = False,
        trim_right: bool = False,
    ) -> None:
        self._canvas = canvas
        self.width = width
        self.height = height
        self._bleed = bleed
        self._trim_left = trim_left
        self._trim_right = trim_right

    @property
    def folds(self) -> tuple[bool, bool]:
        """Whether the left and right edges are folds (shared with a neighbour), not trim edges."""
        return not self._trim_left, not self._trim_right

    @property
    def box(self) -> Box:
        return Box(0.0, 0.0, self.width, self.height)

    def _y(self, top: float) -> float:
        return self.height - top

    def bled(self, box: Box) -> Box:
        """``box`` with every side touching a trim edge pushed out into the bleed.

        Top and bottom are always trim edges; left and right only on the
        outer panels of the sheet.
        """
        b, tol = self._bleed, EDGE_TOLERANCE
        if not b:
            return box
        left = box.x - b if self._trim_left and box.x <= tol else box.x
        right = box.right + b if self._trim_right and box.right >= self.width - tol else box.right
        top = box.top - b if box.top <= tol else box.top
        bottom = box.bottom + b if box.bottom >= self.height - tol else box.bottom
        return Box(left, top, right - left, bottom - top)

    def clip(self) -> None:
        """Clip what follows to the panel, bleed included where it is a trim edge."""
        area = self.bled(self.box)
        path = self._canvas.beginPath()
        path.rect(area.x, self._y(area.bottom), area.width, area.height)
        self._canvas.clipPath(path, stroke=0, fill=0)

    # -- shapes -------------------------------------------------------------

    def fill(self, color: Color) -> None:
        self.rect(self.box, fill=color)

    def rect(
        self,
        box: Box,
        *,
        fill: Color | None = None,
        stroke: Color | None = None,
        width: float = 0.5,
        dash: tuple[float, float] | None = None,
    ) -> None:
        c = self._canvas
        c.saveState()
        if dash:
            c.setDash(*dash)
        if fill is not None:
            c.setFillColor(fill)
            if stroke is None:
                box = self.bled(box)
        if stroke is not None:
            c.setStrokeColor(stroke)
            c.setLineWidth(width)
        c.rect(
            box.x,
            self._y(box.bottom),
            box.width,
            box.height,
            fill=int(fill is not None),
            stroke=int(stroke is not None),
        )
        c.restoreState()

    def hline(self, x0: float, x1: float, top: float, color: Color, width: float = 0.5) -> None:
        c = self._canvas
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.line(x0, self._y(top), x1, self._y(top))
        c.restoreState()

    def polyline(self, points: Sequence[tuple[float, float]], color: Color, width: float) -> None:
        """Stroke an open polyline with round joins and caps."""
        if len(points) < 2:
            return
        c = self._canvas
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.setLineJoin(1)
        c.setLineCap(1)
        path = c.beginPath()
        (x, y), *rest = points
        path.moveTo(x, self._y(y))
        for x, y in rest:
            path.lineTo(x, self._y(y))
        c.drawPath(path, stroke=1, fill=0)
        c.restoreState()

    def vline(self, x: float, top: float, bottom: float, color: Color, width: float = 0.5) -> None:
        c = self._canvas
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.line(x, self._y(top), x, self._y(bottom))
        c.restoreState()

    def dot(self, centre: tuple[float, float], radius: float, color: Color) -> None:
        c = self._canvas
        c.saveState()
        c.setFillColor(color)
        c.circle(centre[0], self._y(centre[1]), radius, stroke=0, fill=1)
        c.restoreState()

    # -- images -------------------------------------------------------------

    def image(self, image: ImageReader, box: Box) -> None:
        """Draw ``image`` stretched to ``box``: callers prepare it at the right ratio."""
        self._canvas.drawImage(image, box.x, self._y(box.bottom), box.width, box.height, mask="auto")

    def qr(self, url: str, box: Box, color: Color) -> None:
        """A square QR code for ``url``, filling ``box`` (quiet zone excluded)."""
        widget = QrCodeWidget(url, barLevel="M", barFillColor=color, barStrokeColor=color, barBorder=0)
        x0, y0, x1, y1 = widget.getBounds()
        side = min(box.width, box.height)
        drawing = Drawing(side, side, transform=[side / (x1 - x0), 0, 0, side / (y1 - y0), 0, 0])
        drawing.add(widget)
        renderPDF.draw(drawing, self._canvas, box.x, self._y(box.top + side))
        self.link(url, Box(box.x, box.top, side, side))

    def link(self, url: str, box: Box) -> None:
        """Make ``box`` clickable in PDF viewers (harmless in print)."""
        rect = (box.x, self._y(box.bottom), box.right, self._y(box.top))
        self._canvas.linkURL(url, rect, relative=1, thickness=0)

    # -- text ---------------------------------------------------------------

    def text(
        self, text: str, x: float, baseline: float, style: TextStyle, align: Align = Align.LEFT
    ) -> float:
        """Draw one line; ``x`` is its left edge, centre or right edge per ``align``. Returns its width."""
        width = text_width(text, style)
        left = x - {Align.LEFT: 0.0, Align.CENTER: width / 2, Align.RIGHT: width}[align]
        t = self._canvas.beginText(left, self._y(baseline))
        t.setFont(style.font, style.size)
        t.setFillColor(style.color)
        t.setCharSpace(style.tracking)
        t.textOut(_shown(text, style))
        self._canvas.drawText(t)
        return width

    def lines(self, text: str, style: TextStyle, width: float) -> list[str]:
        return wrap_text(_shown(text, style), lambda s: text_width(s, style), width)

    def paragraph(self, text: str, x: float, baseline: float, width: float, style: TextStyle) -> float:
        """Draw wrapped, left-aligned text from ``baseline``; returns the last baseline."""
        lines = self.lines(text, style, width)
        for index, line in enumerate(lines):
            self.text(line, x, baseline + index * style.leading, style)
        return baseline + (len(lines) - 1) * style.leading
