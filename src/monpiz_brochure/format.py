"""Physical format of the folded brochure.

The brochure is one sheet folded into ``panels`` equal panels. Each side of
the sheet is a PDF page as wide as the open brochure; panel ``0`` is the
leftmost one *as that side is seen*. Sizes are given in millimetres (as the
printer quotes them) and exposed in PostScript points for drawing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Box

POINTS_PER_MM = 72.0 / 25.4


def mm(value: float) -> float:
    """Millimetres to points."""
    return value * POINTS_PER_MM


@dataclass(frozen=True, slots=True)
class FoldFormat:
    panel_width_mm: float
    height_mm: float
    panels: int = 2
    bleed_mm: float = 3.0

    def __post_init__(self) -> None:
        if self.panels < 2:
            raise ValueError("a folded brochure has at least two panels")
        if min(self.panel_width_mm, self.height_mm) <= 0 or self.bleed_mm < 0:
            raise ValueError("sizes must be positive")

    @property
    def panel_width(self) -> float:
        return mm(self.panel_width_mm)

    @property
    def height(self) -> float:
        return mm(self.height_mm)

    @property
    def width(self) -> float:
        """Width of the open sheet (trimmed)."""
        return self.panel_width * self.panels

    @property
    def bleed(self) -> float:
        return mm(self.bleed_mm)

    @property
    def open_size_mm(self) -> tuple[float, float]:
        return self.panel_width_mm * self.panels, self.height_mm

    def panel_box(self, index: int) -> Box:
        """Trimmed box of panel ``index`` on the open sheet."""
        if not 0 <= index < self.panels:
            raise IndexError(f"panel {index} out of range 0..{self.panels - 1}")
        return Box(index * self.panel_width, 0.0, self.panel_width, self.height)

    def folds(self) -> list[float]:
        """x of every fold line on the open sheet."""
        return [index * self.panel_width for index in range(1, self.panels)]
