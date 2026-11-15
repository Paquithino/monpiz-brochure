"""Pure layout helpers, independent of ReportLab and therefore unit-testable.

Same conventions as the lookbook: origin at the top-left corner, y growing
downwards, units in points.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    top: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    def inset(self, dx: float, dy: float | None = None) -> Box:
        dy = dx if dy is None else dy
        return Box(self.x + dx, self.top + dy, self.width - 2 * dx, self.height - 2 * dy)


def contain(src_w: float, src_h: float, box: Box) -> Box:
    """Largest box with the source's proportions that fits ``box``, centred in it."""
    scale = min(box.width / src_w, box.height / src_h)
    width, height = src_w * scale, src_h * scale
    return Box(box.x + (box.width - width) / 2, box.top + (box.height - height) / 2, width, height)


def columns(left: float, right: float, count: int, gutter: float) -> list[tuple[float, float]]:
    """``count`` equal columns between ``left`` and ``right``: (x, width) each."""
    width = (right - left - (count - 1) * gutter) / count
    return [(left + index * (width + gutter), width) for index in range(count)]


def cover_crop(
    src_w: int,
    src_h: int,
    target_ratio: float,
    focus_x: float = 0.5,
    focus_y: float = 0.5,
    zoom: float = 1.0,
) -> tuple[int, int, int, int]:
    """Pixel crop (left, top, right, bottom) giving ``target_ratio`` (width/height).

    At ``zoom`` 1 the crop keeps the full extent along one axis; ``zoom`` > 1
    tightens it (1.2 = 20% closer). The leftover margin is distributed by
    ``focus_x`` / ``focus_y``: 0 keeps the left or top edge, 1 the right or bottom.
    """
    if zoom < 1.0:
        raise ValueError("zoom must be at least 1")
    if src_w / src_h > target_ratio:
        width, height = src_h * target_ratio, float(src_h)
    else:
        width, height = float(src_w), src_w / target_ratio
    width, height = round(width / zoom), round(height / zoom)
    left = round((src_w - width) * focus_x)
    top = round((src_h - height) * focus_y)
    return left, top, left + width, top + height


def wrap_text(text: str, measure: Callable[[str], float], width: float) -> list[str]:
    """Greedy word wrap; explicit newlines are kept, long words are never broken."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if current and measure(candidate) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def spread(
    points: list[tuple[float, float]], min_distance: float, iterations: int = 80
) -> list[tuple[float, float]]:
    """``points`` nudged apart until no two are closer than ``min_distance``.

    Each round, every pair that is too close is pushed apart along the line
    joining them, half the shortfall each; coincident points split
    horizontally. Points already far enough apart never move, so on a map
    only the crowded clusters change, and only by the little they need.
    """
    moved = [list(point) for point in points]
    for _ in range(iterations):
        clear = True
        for i in range(len(moved)):
            for j in range(i + 1, len(moved)):
                dx = moved[j][0] - moved[i][0]
                dy = moved[j][1] - moved[i][1]
                distance = math.hypot(dx, dy)
                if distance >= min_distance:
                    continue
                clear = False
                ux, uy = (dx / distance, dy / distance) if distance else (1.0, 0.0)
                push = (min_distance - distance) / 2
                moved[i][0] -= ux * push
                moved[i][1] -= uy * push
                moved[j][0] += ux * push
                moved[j][1] += uy * push
        if clear:
            break
    return [(x, y) for x, y in moved]


def overlap(a: Box, b: Box) -> float:
    """Area shared by two boxes (0 when they do not touch)."""
    width = min(a.right, b.right) - max(a.x, b.x)
    height = min(a.bottom, b.bottom) - max(a.top, b.top)
    return max(width, 0.0) * max(height, 0.0)


def brick_slots(
    area: Box,
    columns: int,
    rows: int,
    ratio: float,
    *,
    fill: float = 0.86,
    keep_clear: Sequence[Box] = (),
) -> list[Box]:
    """Slots in rows shifted by half a column at every row, like bricks, all inside ``area``.

    Even rows have ``columns`` slots, odd rows ``columns - 1``, centred between
    those above. Each slot has proportions ``ratio`` (width / height) and takes
    at most ``fill`` of its cell, the rest is air. Slots touching a
    ``keep_clear`` box are left out: that is where the logo or the text goes.
    Order: row by row, left to right.
    """
    pitch_x, pitch_y = area.width / columns, area.height / rows
    width = min(pitch_x * fill, pitch_y * fill * ratio)
    height = width / ratio
    slots: list[Box] = []
    for row in range(rows):
        offset = 0.5 if row % 2 == 0 else 1.0
        count = columns if row % 2 == 0 else columns - 1
        cy = area.top + (row + 0.5) * pitch_y
        for column in range(count):
            cx = area.x + (column + offset) * pitch_x
            slot = Box(cx - width / 2, cy - height / 2, width, height)
            if not any(overlap(slot, zone) for zone in keep_clear):
                slots.append(slot)
    return slots
