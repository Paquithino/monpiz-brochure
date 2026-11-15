"""Content schema of the brochure.

Strict like the lookbook's: unknown keys are rejected, so a typo in the
YAML fails loudly instead of silently disappearing from the print.
Image paths are relative to the assets directory; :mod:`content` checks
that they exist.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .format import FoldFormat

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Unit = Annotated[float, Field(ge=0.0, le=1.0)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Meta(_Model):
    title: Text
    author: Text
    subject: str = ""


class Format(_Model):
    """Closed size of the brochure, in millimetres, as quoted by the printer."""

    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    panels: int = Field(2, ge=2, le=2)  # the layout is designed for two panels per side
    bleed_mm: float = Field(3.0, ge=0)
    type_scale: float = Field(1.0, ge=0.7, le=1.6)  # 1.2 = every text 20% larger

    def fold_format(self) -> FoldFormat:
        return FoldFormat(self.width_mm, self.height_mm, self.panels, self.bleed_mm)


class Photo(_Model):
    """A photo cropped to its slot.

    ``focus`` says which part survives the crop; ``zoom`` (1 = as wide as
    possible) moves in closer, e.g. to lose the frame of a photographed print.
    """

    path: Path
    focus_x: Unit = 0.5
    focus_y: Unit = 0.5
    zoom: float = Field(1.0, ge=1.0, le=4.0)

    @property
    def focus(self) -> tuple[float, float]:
        return self.focus_x, self.focus_y


class Cover(_Model):
    """Either one ``photo`` or a ``mosaic`` of studio shots on paper, in staggered rows.

    A photo is laid out per ``photo_layout``: ``band`` keeps it whole above a
    paper band carrying the text (nothing covers the shoes), ``full`` takes the
    whole page, darkened at the bottom under light text.
    """

    photo: Photo | None = None
    photo_layout: Literal["band", "full"] = "band"
    mosaic: list[Path] = Field(default_factory=list)  # studio shots on a light backdrop, in order
    title: Text
    claim: Text
    label: str = ""  # small line in the corner: "Made in Montebelluna, Italia"

    @model_validator(mode="after")
    def _one_background(self) -> Cover:
        if (self.photo is None) == (not self.mosaic):
            raise ValueError("serve `photo` oppure `mosaic` (uno dei due)")
        return self


class Swatch(_Model):
    """A real material sample, glued by hand into its printed frame."""

    name: Text
    text: Text
    preview: Path | None = None  # photo of the material, shown with ``--swatch-preview``


class Materials(_Model):
    eyebrow: Text
    title: Text
    swatch_width_mm: float = Field(30.0, gt=0)  # size of every sample
    swatch_height_mm: float = Field(20.0, gt=0)
    items: list[Swatch] = Field(min_length=1, max_length=4)  # one row


class Story(_Model):
    eyebrow: Text
    title: Text
    paragraphs: list[Text] = Field(min_length=1, max_length=3)
    photo: Photo | None = None  # fills the room left under the text


class Detail(_Model):
    name: Text
    description: Text
    image: Path  # round cut-out on a transparent background


class Details(_Model):
    eyebrow: Text
    title: Text
    items: list[Detail] = Field(min_length=1, max_length=4)  # one row


_TOWN = re.compile(r"\b\d{5}\s+(.+?)(?:,?\s+[A-Z]{2})?$")


class Store(_Model):
    """A retailer, in the same format as the lookbook's ``retailers.yaml``."""

    name: Text
    address: Text
    phone: Text | None = None
    shop: Text | None = None
    at: tuple[float, float] | None = None  # (latitude, longitude), to place the store on the map

    @property
    def town(self) -> str:
        match = _TOWN.search(self.address)
        return match.group(1) if match else self.address.split(",")[-1].strip()


class Region(_Model):
    region: Text
    stores: list[Store] = Field(min_length=1)


class MapLabel(_Model):
    name: Text
    at: tuple[float, float]  # (latitude, longitude)


class RetailersMap(_Model):
    """Area drawn on the map; stores outside it are mentioned under it ("Anche in: ...")."""

    north: float = 47.05
    south: float = 44.75
    west: float = 9.2
    east: float = 14.1
    labels: list[MapLabel] = Field(default_factory=list)

    def contains(self, at: tuple[float, float]) -> bool:
        lat, lon = at
        return self.south <= lat <= self.north and self.west <= lon <= self.east


class Retailers(_Model):
    eyebrow: Text
    title: Text  # "{count}" becomes the number of stores
    text: str = ""
    map: RetailersMap = Field(default_factory=RetailersMap)
    regions: list[Region] = Field(min_length=1)

    @property
    def count(self) -> int:
        return sum(len(region.stores) for region in self.regions)

    @property
    def heading(self) -> str:
        return self.title.replace("{count}", str(self.count))


class QrCode(_Model):
    url: Text
    label: Text


class Back(_Model):
    eyebrow: Text
    title: Text
    title_italic: str = ""
    text: str = ""
    contacts: list[Text] = Field(min_length=1, max_length=4)
    qr: QrCode | None = None
    footer: str = ""


class Identity(_Model):
    logo: Path  # transparent PNG; tinted to a single colour where needed


class Brochure(_Model):
    meta: Meta
    format: Format
    identity: Identity
    cover: Cover
    back: Back
    materials: Materials
    story: Story
    details: Details
    retailers: Retailers

    def asset_paths(self) -> Iterator[Path]:
        yield self.identity.logo
        if self.cover.photo:
            yield self.cover.photo.path
        yield from self.cover.mosaic
        if self.story.photo:
            yield self.story.photo.path
        for swatch in self.materials.items:
            if swatch.preview:
                yield swatch.preview
        for item in self.details.items:
            yield item.image
