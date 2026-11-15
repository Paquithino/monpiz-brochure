"""The retailers block: a dot map of the stores under the Dolomite skyline.

A smaller cousin of the lookbook's retailers page: same data, same map, no
store list (it would not be legible at this size). Region names would cover
the dots at this scale, so the regions are listed under the map with their
number of stores instead. The map keeps the true proportions of the area
(up here a degree of longitude is shorter than one of latitude).
"""

from __future__ import annotations

import math
from collections.abc import Callable

from ..geometry import Box, spread
from ..models import Retailers
from ..mountain import SKYLINE, place
from ..surface import Surface, text_width
from .base import RenderContext, draw_block_heading

HEADING_TO_SKYLINE = 18.0  # last title baseline -> top of the skyline
SKYLINE_HEIGHT = 0.16  # share of the map height
SKYLINE_GAP = 4.0  # skyline -> northernmost stores
DOT_RADIUS = 1.9
DOT_HALO = 0.7  # paper-coloured ring around each dot
DOT_SPACING = 1.2  # minimum gap between two dots (halos included)
MAX_STRETCH = 1.35  # vertical stretch allowed over the true proportions
CITY_OFFSET = (3.4, 2.2)
MAP_TO_REGIONS = 16.0  # map bottom -> first baseline of the region list
REGIONS_TO_FOOTER = 4.0  # extra space between the region list and the closing line
REGION_SEPARATOR = "  ·  "


def draw_retailers(surface: Surface, ctx: RenderContext, box: Box, retailers: Retailers) -> None:
    p, t = ctx.theme.palette, ctx.theme.type
    last = draw_block_heading(
        surface, ctx, box.x, box.top + 6, box.width, retailers.eyebrow, retailers.heading
    )

    # Bottom up: the closing line on the margin, the region list above it, the map in the rest.
    region_style = t.label.with_color(p.muted)
    regions = _region_lines(retailers, lambda line: text_width(line, region_style), box.width)
    regions_last = box.bottom - (t.small.leading + REGIONS_TO_FOOTER if retailers.text else 0.0)
    regions_first = regions_last - (len(regions) - 1) * region_style.leading
    room_top = last + HEADING_TO_SKYLINE
    area = _map_box(retailers, Box(box.x, room_top, box.width, regions_first - MAP_TO_REGIONS - room_top))

    sky_height = area.height * SKYLINE_HEIGHT
    skyline = place(SKYLINE, area.x, area.top - sky_height - SKYLINE_GAP, area.width, sky_height)
    surface.polyline(skyline, p.rule, 0.6)
    m = retailers.map

    def point(at: tuple[float, float]) -> tuple[float, float]:
        lat, lon = at
        return (
            area.x + (lon - m.west) / (m.east - m.west) * area.width,
            area.top + (m.north - lat) / (m.north - m.south) * area.height,
        )

    stores = [
        point(s.at) for r in retailers.regions for s in r.stores if s.at is not None and m.contains(s.at)
    ]
    dots = spread(stores, 2 * (DOT_RADIUS + DOT_HALO) + DOT_SPACING)
    for centre in dots:
        surface.dot(centre, DOT_RADIUS + DOT_HALO, p.paper)
        surface.dot(centre, DOT_RADIUS, p.accent)
    for city in m.labels:
        cx, cy = point(city.at)
        width = text_width(city.name, t.city)
        surface.text(city.name, *_label_position(cx, cy, width, t.city.size, dots), t.city)

    for index, line in enumerate(regions):
        surface.text(line, box.x, regions_first + index * region_style.leading, region_style)
    if retailers.text:
        surface.text(retailers.text, box.x, box.bottom, t.small)


def _label_position(
    x: float, y: float, width: float, size: float, dots: list[tuple[float, float]]
) -> tuple[float, float]:
    """Left end and baseline for a town name at (``x``, ``y``): right of the point, else
    left, above or below, whichever covers the fewest store dots (right wins a tie)."""
    dx, dy = CITY_OFFSET
    candidates = [
        (x + dx, y + dy),  # right
        (x - dx - width, y + dy),  # left
        (x - width / 2, y - dx),  # above
        (x - width / 2, y + dx + size),  # below
    ]
    reach = DOT_RADIUS + DOT_HALO

    def covered(left: float, baseline: float) -> int:
        return sum(
            left - reach <= px <= left + width + reach and baseline - size - reach <= py <= baseline + reach
            for px, py in dots
        )

    return min(candidates, key=lambda c: covered(*c))


def _region_lines(retailers: Retailers, measure: Callable[[str], float], width: float) -> list[str]:
    """'Veneto · Trentino-Alto Adige · ...' wrapped between regions, never inside a name."""
    lines: list[str] = []
    for region in retailers.regions:
        candidate = f"{lines[-1]}{REGION_SEPARATOR}{region.region}" if lines else region.region
        if lines and measure(candidate) <= width:
            lines[-1] = candidate
        else:
            lines.append(region.region)
    return lines


def _map_box(retailers: Retailers, room: Box) -> Box:
    """The map box in ``room`` (skyline included, centred): as large as possible,
    with the area's true proportions stretched vertically by at most ``MAX_STRETCH``."""
    m = retailers.map
    middle = math.radians((m.north + m.south) / 2)
    ratio = (m.east - m.west) * math.cos(middle) / (m.north - m.south)  # true width / height
    usable = (room.height - SKYLINE_GAP) / (1 + SKYLINE_HEIGHT)  # tallest map that fits
    width = min(room.width, usable * ratio * MAX_STRETCH)
    height = min(usable, width / ratio * MAX_STRETCH)
    sky = height * SKYLINE_HEIGHT + SKYLINE_GAP
    top = room.top + sky + (room.height - sky - height) / 2
    return Box(room.x + (room.width - width) / 2, top, width, height)
