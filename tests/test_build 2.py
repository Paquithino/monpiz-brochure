"""End-to-end: the real content validates and renders a two-page PDF."""

import re
from pathlib import Path

import pytest

from monpiz_brochure.builder import BuildOptions, build
from monpiz_brochure.contacts import contact
from monpiz_brochure.content import load_brochure
from monpiz_brochure.errors import ContentError

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "brochure.yaml"
ASSETS = ROOT / "assets"


def test_content_is_valid() -> None:
    brochure = load_brochure(CONTENT, ASSETS)
    assert brochure.format.panels == 2


def test_missing_image_is_reported(tmp_path: Path) -> None:
    broken = tmp_path / "brochure.yaml"
    (tmp_path / "retailers.yaml").write_bytes((CONTENT.parent / "retailers.yaml").read_bytes())
    broken.write_text(CONTENT.read_text(encoding="utf-8").replace("images/logo.png", "images/nope.png"))
    with pytest.raises(ContentError, match=re.escape("images/nope.png")):
        load_brochure(broken, ASSETS)


def test_build_writes_two_sides(tmp_path: Path) -> None:
    output = tmp_path / "brochure.pdf"
    result = build(BuildOptions(CONTENT, ASSETS, output, dpi=72, marks=True))
    data = output.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(re.findall(rb"/Type /Page\b", data)) == 2
    assert b"/TrimBox" in data and b"/BleedBox" in data
    assert result.open_size_mm == (2 * result.closed_size_mm[0], result.closed_size_mm[1])


@pytest.mark.parametrize(
    ("raw", "label", "text"),
    [
        ("monpiz@monpiz.it", "Email", "monpiz@monpiz.it"),
        ("+39 376 066 9500", "Telefono e WhatsApp", "+39 376 066 9500"),
        ("instagram.com/monpiz_official", "Instagram", "@monpiz_official"),
        ("www.monpiz.it", "Sito", "monpiz.it"),
    ],
)
def test_contacts_are_recognised(raw: str, label: str, text: str) -> None:
    found = contact(raw)
    assert (found.label, found.text) == (label, text)


def test_retailers_title_counts_the_stores() -> None:
    retailers = load_brochure(CONTENT, ASSETS).retailers
    assert retailers.count == sum(len(region.stores) for region in retailers.regions)
    assert retailers.heading == retailers.title.replace("{count}", str(retailers.count))
    assert "{count}" not in retailers.heading


def test_swatch_preview_and_guides_render(tmp_path: Path) -> None:
    output = tmp_path / "anteprima.pdf"
    build(BuildOptions(CONTENT, ASSETS, output, dpi=72, bleed=False, guides=True, swatch_preview=True))
    assert output.stat().st_size > 0
