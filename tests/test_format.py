import pytest

from monpiz_brochure.format import FoldFormat, mm
from monpiz_brochure.geometry import Box


def test_mm_to_points() -> None:
    assert mm(25.4) == pytest.approx(72.0)


def test_open_sheet_is_panels_side_by_side() -> None:
    fmt = FoldFormat(panel_width_mm=170, height_mm=120)
    assert fmt.open_size_mm == (340, 120)
    assert fmt.width == pytest.approx(mm(340))
    assert fmt.panel_box(1) == Box(mm(170), 0.0, mm(170), mm(120))
    assert fmt.folds() == [pytest.approx(mm(170))]


def test_panel_out_of_range() -> None:
    with pytest.raises(IndexError):
        FoldFormat(170, 120).panel_box(2)


@pytest.mark.parametrize("args", [(170, 120, 1), (0, 120, 2), (170, 120, 2, -1)])
def test_invalid_formats(args: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        FoldFormat(*args)  # type: ignore[arg-type]
