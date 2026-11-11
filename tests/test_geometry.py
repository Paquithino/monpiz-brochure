import pytest

from monpiz_brochure.geometry import Box, brick_slots, columns, cover_crop, overlap, spread, wrap_text


def test_cover_crop_wide_source_keeps_full_height() -> None:
    assert cover_crop(2000, 1000, 1.0) == (500, 0, 1500, 1000)


def test_cover_crop_focus_moves_the_window() -> None:
    assert cover_crop(2000, 1000, 1.0, focus_x=0.0) == (0, 0, 1000, 1000)
    assert cover_crop(1000, 2000, 1.0, focus_y=1.0) == (0, 1000, 1000, 2000)


def test_cover_crop_zoom_tightens_around_the_focus() -> None:
    assert cover_crop(1000, 1000, 1.0, zoom=2.0) == (250, 250, 750, 750)
    assert cover_crop(1000, 1000, 1.0, focus_x=1.0, focus_y=0.0, zoom=2.0) == (500, 0, 1000, 500)


def test_cover_crop_rejects_zoom_out() -> None:
    with pytest.raises(ValueError):
        cover_crop(1000, 1000, 1.0, zoom=0.5)


def test_columns_split_the_width() -> None:
    assert columns(0, 100, 2, 10) == [(0, 45), (55, 45)]


def test_wrap_keeps_newlines_and_long_words() -> None:
    measure = len
    assert wrap_text("aa bb cc", lambda s: float(measure(s)), 5) == ["aa bb", "cc"]
    assert wrap_text("uno\ndue", lambda s: float(measure(s)), 50) == ["uno", "due"]
    assert wrap_text("lunghissima", lambda s: float(measure(s)), 3) == ["lunghissima"]


def test_spread_separates_crowded_points_only() -> None:
    far = (100.0, 100.0)
    moved = spread([(0.0, 0.0), (1.0, 0.0), far], 4.0)
    assert moved[2] == far
    assert moved[1][0] - moved[0][0] == pytest.approx(4.0)
    assert spread([(5.0, 5.0), (5.0, 5.0)], 2.0) == [(4.0, 5.0), (6.0, 5.0)]


def test_brick_slots_stay_inside_and_avoid_clear_zones() -> None:
    area = Box(0, 0, 400, 300)
    slots = brick_slots(area, 4, 3, 1.5)
    assert len(slots) == 4 + 3 + 4
    assert all(s.x >= 0 and s.top >= 0 and s.right <= 400 and s.bottom <= 300 for s in slots)
    assert {round(s.x + s.width / 2) for s in slots[4:7]} == {100, 200, 300}  # odd row: between the others
    logo = Box(0, 0, 90, 90)
    kept = brick_slots(area, 4, 3, 1.5, keep_clear=[logo])
    assert len(kept) == len(slots) - 1 and all(overlap(s, logo) == 0 for s in kept)
