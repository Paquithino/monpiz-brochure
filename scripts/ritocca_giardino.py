"""Ritocco della foto di copertina: assets/images/giardino-originale.jpg -> giardino.jpg.

1. toglie il gambo secco davanti alla scarpa beige, come col timbro clone: lungo
   il gambo copia i pixel di poco più a destra (velluto, pelle o prato a seconda
   dell'altezza), con bordi sfumati. L'inpainting automatico lasciava una scia sfocata;
2. porta i colori verso quelli del post Instagram (giardino-riferimento-colori.jpg):
   ogni canale R, G, B prende la distribuzione dei toni del riferimento
   (histogram matching), poi si mescola con l'originale e si smorza un po' la
   saturazione, come nel post (cielo rosato, luce dorata, jeans meno accesi).

Il riferimento è un'altra inquadratura della stessa scena, non un ritaglio
dell'originale: per questo si copiano le distribuzioni dei toni, non i pixel.
Uso (richiede opencv-python e scikit-image, non sono dipendenze del progetto):
    python scripts/ritocca_giardino.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from skimage.exposure import match_histograms

IMAGES = Path(__file__).resolve().parents[1] / "assets" / "images"
STEM = [(510, 515), (518, 600), (528, 680), (540, 740), (555, 790), (575, 860), (585, 910)]  # px, originale
STEM_WIDTH = 20
# Da quanti px più a destra si copia, per fasce di altezza (y finale, spostamento):
# lontano dalla testa del fiore, che è larga; poco sopra i ganci, per non duplicarli.
CLONE_BANDS = [(560, 80), (720, 34), (790, 20), (10_000, 34)]
FEATHER = 9  # px di sfumatura del bordo
STEM_HEAD = ((502, 512), (34, 22))  # centro, semiassi dell'ellisse
STRENGTH = 0.8  # 1 = toni del riferimento, 0 = originale
SATURATION = 0.85


def remove_stem(image: np.ndarray) -> np.ndarray:
    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.polylines(mask, [np.array(STEM, np.int32)], False, 255, STEM_WIDTH)
    cv2.ellipse(mask, STEM_HEAD[0], STEM_HEAD[1], 0, 0, 360, 255, -1)
    # Allargata prima di sfumarla: la sfumatura cade fuori dal gambo, che resta coperto al 100%.
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * FEATHER + 1,) * 2))
    alpha = cv2.GaussianBlur(mask, (0, 0), FEATHER / 2).astype(np.float32)[..., None] / 255
    source = np.empty_like(image)  # per ogni fascia, i pixel di destra portati sopra il gambo
    top = 0
    for bottom, offset in CLONE_BANDS:
        source[top:bottom] = np.roll(image, -offset, axis=1)[top:bottom]
        top = bottom
    return (image * (1 - alpha) + source * alpha).astype(np.uint8)


def match_colours(image: np.ndarray, reference: np.ndarray, strength: float) -> np.ndarray:
    matched = match_histograms(image, reference, channel_axis=-1).astype(np.float32)
    mixed = np.clip(image + (matched - image) * strength, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(mixed, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= SATURATION
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def main() -> None:
    original = cv2.imread(str(IMAGES / "giardino-originale.jpg"))
    reference = cv2.imread(str(IMAGES / "giardino-riferimento-colori.jpg"))
    result = match_colours(remove_stem(original), reference, STRENGTH)
    cv2.imwrite(str(IMAGES / "giardino.jpg"), result, [cv2.IMWRITE_JPEG_QUALITY, 95])


if __name__ == "__main__":
    main()
