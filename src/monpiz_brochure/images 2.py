"""Image preparation: cropping, scrims, tinting and resampling.

Every image is cropped to the exact ratio of its slot and resampled to the
output resolution, so ReportLab only places pixels and the PDF stays light.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader

from .geometry import Box, contain, cover_crop

POINTS_PER_INCH = 72.0
# Studio shots (shoes on a light grey backdrop), for the cover mosaic
BACKDROP_PROBE = 0.1  # share of width and height of the top corners sampled for the backdrop
BACKDROP_WHITE = 0.95  # the backdrop's grey * this becomes pure white
SUBJECT_LEVEL = 190  # after whitening, darker pixels belong to the shoes
SUBJECT_MARGIN = 0.04  # around the shoes, share of the shot's size
FEATHER = 0.12  # borders fade to white over this share of the shorter side


def _rgb(color: Color) -> tuple[int, int, int]:
    r, g, b = (round(channel * 255) for channel in color.rgb())
    return r, g, b


class ImageLibrary:
    def __init__(self, assets_dir: Path, dpi: int, jpeg_quality: int = 90) -> None:
        if dpi <= 0:
            raise ValueError("dpi must be positive")
        self._assets_dir = assets_dir
        self._dpi = dpi
        self._jpeg_quality = jpeg_quality

    def size(self, path: Path) -> tuple[int, int]:
        """Pixel size of an asset, without decoding it."""
        with Image.open(self._assets_dir / path) as image:
            return image.size

    def cover(
        self,
        path: Path,
        width_pt: float,
        height_pt: float,
        *,
        focus: tuple[float, float] = (0.5, 0.5),
        zoom: float = 1.0,
        scrim: Color | None = None,
        scrim_from: float = 0.45,
        scrim_strength: float = 0.85,
    ) -> ImageReader:
        """The photo cropped to fill a ``width_pt`` x ``height_pt`` slot (CSS ``object-fit: cover``).

        ``scrim`` darkens the photo towards that colour from ``scrim_from``
        (share of the height) down to the bottom edge, where it reaches
        ``scrim_strength``: light text stays legible on any photo. Baking it
        into the pixels prints more reliably than a transparent overlay.
        """
        with Image.open(self._assets_dir / path) as source:
            photo = source.convert("RGB")
        crop = cover_crop(photo.width, photo.height, width_pt / height_pt, *focus, zoom=zoom)
        photo = self._resample(photo.crop(crop), width_pt, height_pt)
        if scrim is not None:
            photo = _with_scrim(photo, _rgb(scrim), scrim_from, scrim_strength)
        return self._encode(photo)

    def fitted(self, path: Path, width_pt: float, height_pt: float) -> ImageReader:
        """The whole image (transparency kept), resampled for the slot."""
        with Image.open(self._assets_dir / path) as image:
            return self._encode(self._resample(image.copy(), width_pt, height_pt))

    def tinted(self, path: Path, color: Color, width_pt: float, height_pt: float) -> ImageReader:
        """A flat ``color`` silhouette of a transparent image (the logo on dark photos)."""
        with Image.open(self._assets_dir / path) as image:
            alpha = self._resample(image.convert("RGBA"), width_pt, height_pt).getchannel("A")
        tinted = Image.new("RGBA", alpha.size, (*_rgb(color), 255))
        tinted.putalpha(alpha)
        return self._encode(tinted)

    def mosaic(
        self, tiles: Sequence[tuple[Path, Box]], width_pt: float, height_pt: float, paper: Color
    ) -> ImageReader:
        """Studio shots laid out on a sheet of ``paper`` colour, as one image.

        Each shot is cropped around the shoes, its backdrop turned white and its
        borders feathered, then blended in multiply mode: the white disappears
        into the paper and only the shoes and their soft shadows remain. Tile
        boxes are in points from the image's top-left corner and may run past
        its edges. Compositing here, rather than with PDF transparency, keeps
        the print file simple for the printer's RIP.
        """
        px = self._dpi / POINTS_PER_INCH
        size = (round(width_pt * px), round(height_pt * px))
        shots = Image.new("RGB", size, (255, 255, 255))
        for path, tile in tiles:
            with Image.open(self._assets_dir / path) as source:
                source.thumbnail((round(tile.width * px * 1.6),) * 2)  # no need to process 6000 px
                shot = studio_shot(source)
            fitted = contain(shot.width, shot.height, tile)
            shot = shot.resize(
                (max(1, round(fitted.width * px)), max(1, round(fitted.height * px))),
                Image.Resampling.LANCZOS,
            )
            x, y = round(fitted.x * px), round(fitted.top * px)
            visible = (max(x, 0), max(y, 0), min(x + shot.width, size[0]), min(y + shot.height, size[1]))
            if visible[0] >= visible[2] or visible[1] >= visible[3]:
                continue
            part = shot.crop((visible[0] - x, visible[1] - y, visible[2] - x, visible[3] - y))
            shots.paste(ImageChops.multiply(shots.crop(visible), part), visible[:2])
        return self._encode(ImageChops.multiply(Image.new("RGB", size, _rgb(paper)), shots))

    def effective_dpi(self, path: Path, width_pt: float, height_pt: float, zoom: float = 1.0) -> float:
        """Resolution a photo prints at when it covers the slot: below ~240 it may look soft."""
        px_w, px_h = self.size(path)
        scale = max(width_pt / px_w, height_pt / px_h) * zoom  # points per source pixel, after the crop
        return POINTS_PER_INCH / scale

    def _resample(self, image: Image.Image, width_pt: float, height_pt: float) -> Image.Image:
        """Downscale to the output DPI; never upscale (it would only add bytes)."""
        target = (
            max(1, round(width_pt / POINTS_PER_INCH * self._dpi)),
            max(1, round(height_pt / POINTS_PER_INCH * self._dpi)),
        )
        if target[0] >= image.width or target[1] >= image.height:
            return image
        return image.resize(target, Image.Resampling.LANCZOS, reducing_gap=3.0)

    def _encode(self, image: Image.Image) -> ImageReader:
        buffer = io.BytesIO()
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            image.save(buffer, format="PNG", optimize=True)
        else:
            image.convert("RGB").save(buffer, format="JPEG", quality=self._jpeg_quality, optimize=True)
        buffer.seek(0)
        return ImageReader(buffer)


def _with_scrim(photo: Image.Image, rgb: tuple[int, int, int], start: float, strength: float) -> Image.Image:
    """``photo`` blended towards ``rgb`` with a vertical ramp (eased, so no visible band)."""
    height = photo.height
    first = round(height * start)
    ramp = [
        0 if y < first else round(255 * strength * ((y - first) / max(height - first, 1)) ** 1.6)
        for y in range(height)
    ]
    mask = Image.new("L", (1, height))
    mask.putdata(ramp)
    mask = mask.resize(photo.size)
    return Image.composite(Image.new("RGB", photo.size, rgb), photo, mask)


def studio_shot(source: Image.Image) -> Image.Image:
    """A shot on a light backdrop, cropped around the shoes, backdrop white, borders feathered."""
    photo = source.convert("RGB")
    grey = photo.convert("L")
    w, h = photo.size
    pw, ph = round(w * BACKDROP_PROBE), round(h * BACKDROP_PROBE)
    corners = [grey.crop((0, 0, pw, ph)), grey.crop((w - pw, 0, w, ph))]
    backdrop = sum(ImageStat.Stat(corner).median[0] for corner in corners) / len(corners)
    white_point = max(backdrop * BACKDROP_WHITE, 1.0)
    photo = photo.point(lambda v: min(255, round(v * 255 / white_point)))

    subject = photo.convert("L").point(lambda v: 255 if v < SUBJECT_LEVEL else 0)
    box = subject.filter(ImageFilter.MaxFilter(9)).getbbox() or (0, 0, w, h)
    pad = round(max(w, h) * SUBJECT_MARGIN)
    photo = photo.crop(
        (max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, w), min(box[3] + pad, h))
    )

    band = max(1, round(min(photo.size) * FEATHER))
    mask = ImageChops.multiply(
        _edge_ramp(photo.width, band).resize(photo.size),
        _edge_ramp(photo.height, band).transpose(Image.Transpose.ROTATE_90).resize(photo.size),
    )
    return Image.composite(photo, Image.new("RGB", photo.size, (255, 255, 255)), mask)


def _edge_ramp(length: int, band: int) -> Image.Image:
    """A ``length`` x 1 mask: 0 at both ends, rising smoothly (smoothstep) to 255 over ``band`` px."""

    def level(i: int) -> int:
        t = min(1.0, min(i, length - 1 - i) / band)
        return round(255 * t * t * (3 - 2 * t))

    ramp = Image.new("L", (length, 1))
    ramp.putdata([level(i) for i in range(length)])
    return ramp
