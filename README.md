# MonPiz Brochure

Generatore della brochure pieghevole MonPiz di presentazione per i nuovi clienti, in PDF da
stampa. Stessa impostazione del [lookbook](https://github.com/Paquithino/monpiz-lookbook):
i contenuti (testi, foto, formato) stanno in `content/brochure.yaml`, il codice si occupa
solo dell'impaginazione. Palette e caratteri (Fraunces, Inter) sono quelli del lookbook.

```bash
pip install -e ".[dev]"
monpiz-brochure build                         # dist/MonPiz-Brochure.pdf, 300 dpi, con abbondanza
monpiz-brochure build --marks                 # con segni di taglio e di piega
monpiz-brochure build --guides -o dist/bozza.pdf   # pieghe e area di sicurezza in magenta (solo bozza)
monpiz-brochure build --no-bleed --dpi 150 -o dist/MonPiz-Brochure-web.pdf
monpiz-brochure check                         # valida contenuti e immagini
monpiz-brochure watch                         # anteprima live: rigenera a ogni salvataggio (150 dpi)
monpiz-brochure watch --guides --swatch-preview   # con pieghe, margini e il campione simulato
```

### Anteprima live

`monpiz-brochure watch` controlla `content/`, `assets/` e il codice in `src/` e rigenera
`dist/MonPiz-Brochure-anteprima.pdf` (già rifilato, 150 dpi) a ogni file salvato; in caso
di errore lo mostra e resta in ascolto. Aperto in VS Code con l'estensione *vscode-pdf*
(affiancato al codice), il PDF si ricarica da solo. Ogni rebuild gira in un processo
Python nuovo, così anche le modifiche al codice hanno effetto senza riavviare il watch.

## Formato

Pieghevole a **2 ante (4 facciate)**, una piega centrale:

| | Larghezza | Altezza |
|---|---|---|
| Chiuso | 170 mm | 120 mm |
| Aperto (file di stampa, al rifilo) | 340 mm | 120 mm |
| Con abbondanza (3 mm per lato) | 346 mm | 126 mm |

Il formato si cambia in `content/brochure.yaml` (`format.width_mm`, `height_mm`,
`bleed_mm`): tutto il layout si ricalcola. Alcune tipografie chiedono 5 mm di abbondanza
invece di 3.

Il PDF ha **due pagine**, una per lato del foglio, già imposte per la stampa fronte/retro:

```
pagina 1, esterno:  [ retro: contatti, QR             | copertina: mosaico, logo, claim ]
pagina 2, interno:  [ 4 campioni di pelle + dettagli  | storia + rete di negozi      ]
```

### La copertina

Due stili, scelti in `cover` nel YAML:

- `mosaic`: le foto di studio dei modelli (scarpa + suola su fondo grigio chiaro, le
  `*_Spaiate` del lookbook), una per modello, a file sfalsate su fondo carta, come un flat lay
  da catalogo. Ogni foto viene ritagliata attorno alle scarpe, il fondo diventa bianco e
  sparisce nella carta (fusione Moltiplica, calcolata in Python: nel PDF finisce
  un'unica immagine, senza trasparenze). Le scarpe lasciano libero lo spazio di logo,
  titolo e claim e restano sempre intere (4 + 3 + 4 posti; logo in basso a destra). Le foto si
  dispongono nell'ordine della lista, riga per riga.
- `photo`: una foto a tutta pagina scurita in basso, con testi chiari.

### I campioni di pelle

Sull'anta interna sinistra ci sono quattro riquadri (filetto con angoli) in cui incollare
a mano i campioni veri: Pelle Dakar, Pelle Martellata, Suede e Cavallino (`materials` nel
YAML, fino a 4). La misura dei campioni si imposta in `swatch_width_mm` /
`swatch_height_mm` (default 30 × 20 mm); ogni riquadro stampato è 2 mm più largo per lato,
così un'applicazione non perfetta resta comunque ordinata. Dentro i riquadri non si
stampa niente oltre al colore carta.

- `--guides` mostra in magenta il contorno esatto di ogni campione;
- `--swatch-preview` mette al loro posto le foto dei materiali (`preview`), per le
  anteprime a schermo: non usarlo per il file da stampa.

### La rete di negozi

L'anta interna destra riprende la mappa a punti del lookbook. I negozi stanno in
`content/retailers.yaml`, **lo stesso formato del lookbook**: per aggiornarli basta
copiare quel file. Il titolo `Una rete di {count} negozi.` si aggiorna da solo.

## Struttura

```
content/brochure.yaml   formato, copertina, retro, materiali, dettagli, storia, rivenditori
content/retailers.yaml  negozi per regione (copiato dal lookbook)
assets/                 fonts/ (OFL) e images/
src/monpiz_brochure/
  format.py             formato pieghevole: ante, pieghe, abbondanza (mm -> pt)
  models.py             schema dei contenuti (Pydantic, chiavi sconosciute rifiutate)
  content.py            caricamento YAML + verifica che ogni immagine esista
  theme.py              design token: palette, stili di testo, margini
  geometry.py           funzioni di layout pure (box, colonne, ritaglio, a capo)
  surface.py            primitive di disegno per un'anta; abbondanza solo sui bordi esterni
  images.py             ritaglio, sfumatura scura, tinta del logo, mosaico, ricampionamento
  mountain.py           lo skyline dolomitico del lookbook, sopra la mappa
  panels/               una classe per anta, più i blocchi dettagli e mappa rivenditori
  builder.py            imposizione delle ante sui due lati, TrimBox/BleedBox, segni
  cli.py                comandi build e check
```

Ogni anta disegna in coordinate proprie e viene ritagliata sulla sua area: una foto non
può mai scavalcare la piega. Sui bordi esterni del foglio, invece, sfondi e foto
proseguono da soli nell'abbondanza.

## Foto

Ogni foto ha `path` e, facoltativi, `focus_x`/`focus_y` (quale parte resta dopo il
ritaglio, da 0 a 1) e `zoom` (≥ 1, per avvicinarsi). Se una foto risulta stampata sotto
i 240 dpi, `build` lo segnala.
