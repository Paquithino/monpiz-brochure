"""Allunga in basso la foto delle pedule sulla neve: copertina-neve.jpg -> copertina-neve-estesa.jpg.

Sotto le suole c'erano solo pochi px di neve, così in copertina le scarpe toccavano il
bordo. La neve aggiunta è neve vera della stessa foto, ricomposta a tasselli ("image
quilting", Efros e Freeman): ogni tassello si sceglie, tra molti candidati presi dalle zone
di sola neve, quello che si raccorda meglio con quanto c'è già sopra e a sinistra, e si unisce
lungo il taglio di minimo errore. Niente neve inventata, niente bande lisce.
Uso (richiede opencv-python, non è una dipendenza del progetto):
    python scripts/estendi_neve.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

IMAGES = Path(__file__).resolve().parents[1] / "assets" / "images"
EXTRA = 150  # px di neve aggiunti in basso
BLOCK = 72  # lato dei tasselli
OVERLAP = 24  # sovrapposizione tra tasselli
CANDIDATES = 400  # tasselli provati per ogni posizione
# Zone di sola neve da cui si prendono i tasselli (x0, y0, x1, y1 in frazioni della foto)
SOURCES = [(0.0, 0.62, 0.30, 1.0), (0.78, 0.55, 1.0, 1.0)]
SEED = 7


def _min_cut(error: np.ndarray) -> np.ndarray:
    """Maschera 0/1 (1 = tassello nuovo) che taglia ``error`` (h x w) lungo il cammino
    verticale di costo minimo: a sinistra del taglio resta il vecchio, a destra il nuovo."""
    h, w = error.shape
    cost = error.copy()
    for y in range(1, h):
        left = np.r_[np.inf, cost[y - 1, :-1]]
        right = np.r_[cost[y - 1, 1:], np.inf]
        cost[y] += np.minimum(np.minimum(left, cost[y - 1]), right)
    mask = np.zeros((h, w), np.float32)
    x = int(np.argmin(cost[-1]))
    for y in range(h - 1, -1, -1):
        mask[y, x:] = 1
        if y:
            lo, hi = max(x - 1, 0), min(x + 2, w)
            x = lo + int(np.argmin(cost[y - 1, lo:hi]))
    return mask


def _candidates(img: np.ndarray, rng: np.random.Generator) -> list[np.ndarray]:
    h, w = img.shape[:2]
    blocks = []
    for _ in range(CANDIDATES):
        x0, y0, x1, y1 = SOURCES[rng.integers(len(SOURCES))]
        x = rng.integers(round(x0 * w), round(x1 * w) - BLOCK)
        y = rng.integers(round(y0 * h), round(y1 * h) - BLOCK)
        block = img[y : y + BLOCK, x : x + BLOCK]
        blocks.append(block[:, ::-1] if rng.random() < 0.5 else block)  # anche specchiati
    return blocks


def main() -> None:
    img = cv2.imread(str(IMAGES / "copertina-neve.jpg")).astype(np.float32)
    h, w = img.shape[:2]
    out = np.vstack([img, np.zeros((EXTRA, w, 3), np.float32)])
    rng = np.random.default_rng(SEED)
    pool = _candidates(img, rng)
    step = BLOCK - OVERLAP
    for top in range(h - OVERLAP, h + EXTRA, step):
        for left in range(0, w, step):
            bh, bw = min(BLOCK, out.shape[0] - top), min(BLOCK, w - left)
            target = out[top : top + bh, left : left + bw]
            known = np.zeros((bh, bw), bool)  # dove c'è già qualcosa: sopra e a sinistra
            known[: min(OVERLAP, bh)] = True
            if left:
                known[:, : min(OVERLAP, bw)] = True
            errors = [((b[:bh, :bw] - target) ** 2).sum(2)[known].sum() for b in pool]
            best = pool[int(np.argsort(errors)[rng.integers(3)])][:bh, :bw]  # uno tra i 3 migliori
            err = ((best - target) ** 2).sum(2)
            mask = np.ones((bh, bw), np.float32)
            if left:  # taglio verticale nella sovrapposizione a sinistra
                mask[:, :OVERLAP] = _min_cut(err[:, :OVERLAP])
            top_cut = _min_cut(err[: min(OVERLAP, bh)].T).T  # taglio orizzontale in alto
            mask[: min(OVERLAP, bh)] *= top_cut
            mask = cv2.GaussianBlur(mask, (0, 0), 1.5)[..., None]  # bordi del taglio morbidi
            out[top : top + bh, left : left + bw] = target * (1 - mask) + best * mask
    cv2.imwrite(
        str(IMAGES / "copertina-neve-estesa.jpg"),
        np.clip(out, 0, 255).astype(np.uint8),
        [cv2.IMWRITE_JPEG_QUALITY, 95],
    )


if __name__ == "__main__":
    main()
