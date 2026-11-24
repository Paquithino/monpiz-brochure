"""Sviluppo naturale della foto di copertina dal RAW: raw/P1170014.tiff -> copertina-giardino.jpg.

Il RAW Panasonic (.RW2) si converte prima in TIFF a 16 bit, a piena risoluzione, nella
cartella raw/ (fuori da assets e ignorata da git: il TIFF pesa 80 MB):
    magick P1170014.RW2 -depth 16 raw/P1170014.tiff

Solo correzioni da camera oscura. L'erba davanti alle scarpe non si toglie qui: provate
inpainting e timbro clone automatici, la pelle ricostruita si distingue sempre. Va fatto a mano.
1. raddrizza l'orizzonte (TILT) e ritaglia i bordi vuoti;
2. più luce, bilanciamento del bianco un filo più caldo; alte luci compresse, non bruciate;
3. curva dei toni morbida: ombre aperte, un filo di contrasto;
   più una schiarita locale e sfumata sulle scarpe in suede a sinistra (DODGE);
4. vividezza: più colore dove è spento (prato, jeans, pelle), poco dove è già vivo;
5. nitidezza leggera per la stampa.
Uso (richiede opencv-python, non è una dipendenza del progetto):
    python scripts/sviluppa_copertina.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "assets" / "images"
RAW_DIR = ROOT / "raw"

TILT = -1.6  # gradi: l'orizzonte scendeva verso sinistra
WARMTH = (0.95, 1.0, 1.04)  # moltiplicatori B, G, R
EXPOSURE = 1.22  # più luminosa
HIGHLIGHTS = 0.35  # quanto comprimere le alte luci, per non bruciare cielo e pelo bianco
SHADOWS = 0.12  # apertura delle ombre: il suede scuro mostra la sua grana
CONTRAST = 0.12
VIBRANCE = 0.30  # satura di più i colori spenti (prato, jeans, pelle) e poco quelli già vivi
SHARPEN = (1.2, 0.45)  # raggio in px, intensità
# "Schiarita" da camera oscura sulle scarpe in suede a sinistra, che sono in ombra:
# un'ellisse molto sfumata (centro e semiassi in % della foto) che alza solo ombre e toni medi.
DODGE = ((24.0, 62.0), (20.0, 17.0))
DODGE_STRENGTH = 0.35


def straighten(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), TILT, 1.0)
    turned = cv2.warpAffine(img, rot, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    t = abs(np.radians(TILT))  # il rettangolo più grande senza bordi riflessi
    cw, ch = int(w - h * np.tan(t) - 4), int(h - w * np.tan(t) - 4)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    return turned[y0 : y0 + ch, x0 : x0 + cw]


def develop(img: np.ndarray) -> np.ndarray:
    img = img * np.array(WARMTH, np.float32) * EXPOSURE
    knee = 1 - HIGHLIGHTS  # sopra il ginocchio le luci si avvicinano al bianco senza bruciare
    img = np.where(img > knee, knee + (1 - knee) * np.tanh((img - knee) / (1 - knee)), img)
    lab = cv2.cvtColor(np.clip(img, 0, 1).astype(np.float32), cv2.COLOR_BGR2LAB)
    lum = lab[..., 0] / 100
    lum = lum + SHADOWS * lum * (1 - lum) ** 2 * 4  # ombre più aperte
    lum = lum + CONTRAST * (lum - 0.5) * (1 - np.abs(2 * lum - 1))  # S morbida, estremi intatti
    lum = np.clip(lum, 0, 1)
    h, w = lum.shape
    (cx, cy), (rx, ry) = DODGE
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d2 = ((xx / w * 100 - cx) / rx) ** 2 + ((yy / h * 100 - cy) / ry) ** 2
    dodge = DODGE_STRENGTH * np.exp(-d2 * 1.5)  # sfumata: nessun bordo visibile
    lum = lum + dodge * lum * (1 - lum) ** 1.5  # sale nelle ombre, quasi nulla nelle luci
    lab[..., 0] = np.clip(lum, 0, 1) * 100
    chroma = np.hypot(lab[..., 1], lab[..., 2])
    lab[..., 1:] *= (1 + VIBRANCE * np.clip(1 - chroma / 40, 0, 1))[..., None]
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    radius, amount = SHARPEN
    return img + (img - cv2.GaussianBlur(img, (0, 0), radius)) * amount


def main() -> None:
    raw = cv2.imread(str(RAW_DIR / "P1170014.tiff"), cv2.IMREAD_UNCHANGED)
    img = develop(straighten(raw).astype(np.float32) / 65535)
    out = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    cv2.imwrite(str(IMAGES / "copertina-giardino.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, 95])


if __name__ == "__main__":
    main()
