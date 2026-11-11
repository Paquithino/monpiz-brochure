"""Design tokens: palette, typography and panel grid.

The palette and the typefaces are the lookbook's, so the two pieces read as
one family; the type sizes are re-scaled for a panel a quarter the size of
an A4 page. All measurements are in points.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from reportlab.lib.colors import Color, HexColor

from .format import mm


class Font(StrEnum):
    """Font names as registered in ReportLab (see :mod:`fonts`)."""

    DISPLAY = "Fraunces-Display"
    DISPLAY_ITALIC = "Fraunces-DisplayItalic"
    SERIF = "Fraunces-Text"
    SANS = "Inter-Regular"


@dataclass(frozen=True, slots=True)
class Palette:
    ink: Color
    body: Color
    muted: Color
    accent: Color
    paper: Color
    rule: Color
    forest: Color
    on_dark: Color
    on_dark_muted: Color
    on_dark_accent: Color


@dataclass(frozen=True, slots=True)
class TextStyle:
    font: Font
    size: float
    leading: float
    color: Color
    tracking: float = 0.0
    uppercase: bool = False

    def with_color(self, color: Color) -> TextStyle:
        return replace(self, color=color)


@dataclass(frozen=True, slots=True)
class Typography:
    eyebrow: TextStyle  # spaced capitals above a title
    title: TextStyle  # panel titles
    title_italic: TextStyle  # second line of a title, for contrast
    heading: TextStyle  # titles of half-panel blocks
    cover_title: TextStyle
    claim: TextStyle  # serif sentence on the cover
    text: TextStyle  # running text
    item: TextStyle  # name of a detail
    small: TextStyle  # description of a detail, footer lines
    label: TextStyle  # small spaced capitals: contact keys, captions
    value: TextStyle  # contact values
    city: TextStyle  # town names on the map


@dataclass(frozen=True, slots=True)
class Grid:
    """Geometry shared by every panel."""

    margin: float = mm(9.0)  # trim edge -> content, also on the fold side
    gutter: float = mm(4.0)


@dataclass(frozen=True, slots=True)
class Theme:
    palette: Palette
    type: Typography
    grid: Grid


def default_theme() -> Theme:
    p = Palette(
        ink=HexColor("#24291F"),
        body=HexColor("#4B5245"),
        muted=HexColor("#6A6E5E"),
        accent=HexColor("#6D6F2E"),
        paper=HexColor("#EFECE2"),
        rule=HexColor("#CFC9B6"),
        forest=HexColor("#24291F"),
        on_dark=HexColor("#FFFDF8"),
        on_dark_muted=HexColor("#E2E0C6"),
        on_dark_accent=HexColor("#CDD08A"),
    )
    t = Typography(
        eyebrow=TextStyle(Font.SANS, 6.2, 8.0, p.accent, tracking=1.7, uppercase=True),
        title=TextStyle(Font.DISPLAY, 21.0, 22.5, p.ink),
        title_italic=TextStyle(Font.DISPLAY_ITALIC, 21.0, 22.5, p.accent),
        heading=TextStyle(Font.DISPLAY, 16.0, 18.0, p.ink),
        cover_title=TextStyle(Font.DISPLAY, 30.0, 30.0, p.on_dark),
        claim=TextStyle(Font.SERIF, 9.2, 12.6, p.on_dark_muted),
        text=TextStyle(Font.SANS, 7.4, 11.4, p.body),
        item=TextStyle(Font.SERIF, 9.0, 11.0, p.ink),
        small=TextStyle(Font.SANS, 6.3, 8.6, p.muted),
        label=TextStyle(Font.SANS, 5.4, 7.0, p.accent, tracking=1.4, uppercase=True),
        value=TextStyle(Font.SANS, 7.6, 10.0, p.ink),
        city=TextStyle(Font.SERIF, 6.2, 7.5, p.ink),
    )
    return Theme(palette=p, type=t, grid=Grid())
