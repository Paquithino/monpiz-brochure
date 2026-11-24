"""Assembles the panels and renders the print PDF.

The PDF has one page per side of the sheet, as wide as the open brochure:

    page 1, outside:  [ back cover | front cover ]
    page 2, inside:   [ leather samples + details | story + stores ]

Printed front and back and folded once in the middle, the front cover is
what the customer sees first. Every page is the trimmed sheet plus a bleed,
declared as TrimBox and BleedBox for the printer's preflight; ``marks`` adds
crop and fold marks in a slug around it, ``guides`` draws the folds and the
safe area on top of the artwork, for proofing on screen only.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

from . import __version__
from .content import load_brochure
from .fonts import register_fonts
from .format import FoldFormat
from .images import ImageLibrary
from .models import Brochure
from .panels import BackPanel, CoverPanel, MaterialsPanel, Panel, RenderContext, StoryPanel
from .panels.base import GUIDE_COLOR
from .surface import Surface
from .theme import Font, Theme, default_theme

SLUG = 24.0  # room outside the bleed for crop and fold marks
MARK_LENGTH = 14.0
MARK_GAP = 3.0  # marks stop short of the bleed
MARK_WIDTH = 0.3


@dataclass(frozen=True, slots=True)
class BuildOptions:
    content_file: Path
    assets_dir: Path
    output: Path
    dpi: int = 300
    bleed: bool = True
    marks: bool = False
    guides: bool = False
    swatch_preview: bool = False  # a photo where the real leather sample will be glued


@dataclass(frozen=True, slots=True)
class BuildResult:
    output: Path
    size_bytes: int
    open_size_mm: tuple[float, float]
    closed_size_mm: tuple[float, float]
    warnings: tuple[str, ...]


def sides(brochure: Brochure) -> list[tuple[str, Sequence[Panel]]]:
    """The two sides of the sheet, each with its panels from left to right."""
    return [
        ("Esterno", (BackPanel(brochure.back), CoverPanel(brochure.cover))),
        (
            "Interno",
            (
                MaterialsPanel(brochure.materials, brochure.details),
                StoryPanel(brochure.story, brochure.retailers),
            ),
        ),
    ]


def render(brochure: Brochure, options: BuildOptions, theme: Theme | None = None) -> list[str]:
    """Write the PDF to ``options.output``; returns the print warnings (e.g. low-resolution photos)."""
    theme = theme or default_theme(brochure.format.type_scale)
    register_fonts(options.assets_dir / "fonts")
    ctx = RenderContext(
        theme,
        ImageLibrary(options.assets_dir, options.dpi),
        brochure.identity.logo,
        guides=options.guides,
        swatch_preview=options.swatch_preview,
    )
    fmt = brochure.format.fold_format()

    bleed = fmt.bleed if options.bleed else 0.0
    margin = bleed + (SLUG if options.marks else 0.0)  # trim edge -> page edge
    trim = (margin, margin, margin + fmt.width, margin + fmt.height)
    partial = options.output.with_name(f".{options.output.name}.{os.getpid()}.partial")
    options.output.parent.mkdir(parents=True, exist_ok=True)

    canvas = Canvas(
        str(partial),
        pagesize=(fmt.width + 2 * margin, fmt.height + 2 * margin),
        invariant=True,
        initialFontName=Font.SANS.value,  # avoids a stray, non-embedded Helvetica
        trimBox=trim,
        bleedBox=(trim[0] - bleed, trim[1] - bleed, trim[2] + bleed, trim[3] + bleed),
    )
    canvas.setTitle(brochure.meta.title)
    canvas.setAuthor(brochure.meta.author)
    canvas.setSubject(brochure.meta.subject)
    canvas.setCreator(f"monpiz-brochure {__version__}")

    try:
        for name, panels in sides(brochure):
            canvas.bookmarkPage(name)
            canvas.addOutlineEntry(name, name)  # "Esterno" / "Interno" in the viewer's sidebar
            for index, panel in enumerate(panels):
                box = fmt.panel_box(index)
                canvas.saveState()
                canvas.translate(margin + box.x, margin)
                surface = Surface(
                    canvas,
                    box.width,
                    box.height,
                    bleed=bleed,
                    trim_left=index == 0,
                    trim_right=index == len(panels) - 1,
                )
                surface.clip()
                panel.draw(surface, ctx)
                canvas.restoreState()
            if options.guides:
                _draw_guides(canvas, fmt, margin, theme.grid.margin)
            if options.marks:
                _draw_marks(canvas, fmt, trim, bleed)
            canvas.showPage()
        canvas.save()
        partial.replace(options.output)
    finally:
        partial.unlink(missing_ok=True)
    return ctx.warnings


def build(options: BuildOptions) -> BuildResult:
    brochure = load_brochure(options.content_file, options.assets_dir)
    warnings = render(brochure, options)
    fmt = brochure.format
    return BuildResult(
        output=options.output,
        size_bytes=options.output.stat().st_size,
        open_size_mm=fmt.fold_format().open_size_mm,
        closed_size_mm=(fmt.width_mm, fmt.height_mm),
        warnings=tuple(dict.fromkeys(warnings)),  # one warning per photo, in order
    )


def _draw_marks(
    canvas: Canvas, fmt: FoldFormat, trim: tuple[float, float, float, float], bleed: float
) -> None:
    """Crop marks at the corners, dashed fold marks above and below every fold."""
    left, bottom, right, top = trim
    start, end = bleed + MARK_GAP, bleed + MARK_GAP + MARK_LENGTH
    canvas.saveState()
    canvas.setStrokeColorCMYK(1, 1, 1, 1)  # registration black: shows on every plate
    canvas.setLineWidth(MARK_WIDTH)
    for x, dx in ((left, -1), (right, 1)):
        for y, dy in ((bottom, -1), (top, 1)):
            canvas.line(x + dx * start, y, x + dx * end, y)
            canvas.line(x, y + dy * start, x, y + dy * end)
    canvas.setDash(2, 2)
    for fold in fmt.folds():
        x = left + fold
        canvas.line(x, bottom - start, x, bottom - end)
        canvas.line(x, top + start, x, top + end)
    canvas.restoreState()


def _draw_guides(canvas: Canvas, fmt: FoldFormat, origin: float, safe: float) -> None:
    """Folds (dashed), trim and safe area of every panel: proofing only, never for print."""
    canvas.saveState()
    canvas.translate(origin, origin)
    canvas.setStrokeColor(GUIDE_COLOR)
    canvas.setLineWidth(0.4)
    canvas.rect(0, 0, fmt.width, fmt.height)
    for index in range(fmt.panels):
        box = fmt.panel_box(index).inset(safe)
        canvas.rect(box.x, box.top, box.width, box.height)  # symmetric inset: top/bottom flip is moot
    canvas.setDash(4, 3)
    for fold in fmt.folds():
        canvas.line(fold, 0, fold, fmt.height)
    canvas.restoreState()
