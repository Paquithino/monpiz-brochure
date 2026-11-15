"""Command line: ``build``, ``watch`` and ``check``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .builder import BuildOptions, build
from .content import load_brochure
from .errors import ContentError
from .watch import watch

DEFAULT_CONTENT = Path("content/brochure.yaml")
DEFAULT_ASSETS = Path("assets")
DEFAULT_OUTPUT = Path("dist/MonPiz-Brochure.pdf")
PREVIEW_OUTPUT = Path("dist/MonPiz-Brochure-anteprima.pdf")
PRINT_DPI = 300
PREVIEW_DPI = 150


def _add_content_args(command: argparse.ArgumentParser) -> None:
    command.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    command.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)


def _add_output_args(command: argparse.ArgumentParser, output: Path, dpi: int) -> None:
    command.add_argument("-o", "--output", type=Path, default=output)
    command.add_argument("--dpi", type=int, default=dpi, help=f"risoluzione delle foto (default {dpi})")
    command.add_argument("--marks", action="store_true", help="segni di taglio e di piega")
    command.add_argument("--guides", action="store_true", help="pieghe e area di sicurezza (solo bozza)")
    command.add_argument(
        "--swatch-preview",
        action="store_true",
        help="foto del materiale al posto del campione (solo schermo)",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="monpiz-brochure", description="Brochure pieghevole MonPiz")
    commands = parser.add_subparsers(dest="command", required=True)

    build_cmd = commands.add_parser("build", help="genera il PDF da stampa")
    _add_content_args(build_cmd)
    _add_output_args(build_cmd, DEFAULT_OUTPUT, PRINT_DPI)
    build_cmd.add_argument("--no-bleed", action="store_true", help="senza abbondanza: come apparirà rifilata")

    watch_cmd = commands.add_parser("watch", help="anteprima: rigenera il PDF a ogni modifica salvata")
    _add_content_args(watch_cmd)
    _add_output_args(watch_cmd, PREVIEW_OUTPUT, PREVIEW_DPI)
    watch_cmd.add_argument("--bleed", action="store_true", help="con abbondanza (default: già rifilata)")

    check_cmd = commands.add_parser("check", help="valida contenuti e immagini")
    _add_content_args(check_cmd)
    return parser


def _options(args: argparse.Namespace, *, bleed: bool) -> BuildOptions:
    return BuildOptions(
        content_file=args.content,
        assets_dir=args.assets,
        output=args.output,
        dpi=args.dpi,
        bleed=bleed,
        marks=args.marks,
        guides=args.guides,
        swatch_preview=args.swatch_preview,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            fmt = load_brochure(args.content, args.assets).format
            print(f"Contenuti validi. Formato chiuso {fmt.width_mm:g} x {fmt.height_mm:g} mm.")
            return 0
        if args.command == "watch":
            watch(_options(args, bleed=args.bleed))
            return 0
        result = build(_options(args, bleed=not args.no_bleed))
    except ContentError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # Ctrl+C ends the watch
        return 0

    (closed_w, closed_h), (open_w, open_h) = result.closed_size_mm, result.open_size_mm
    print(f"{result.output} ({result.size_bytes / 1_000_000:.1f} MB)")
    print(f"Chiuso {closed_w:g} x {closed_h:g} mm, aperto {open_w:g} x {open_h:g} mm, 2 facciate per lato.")
    for warning in result.warnings:
        print(f"Attenzione: {warning}", file=sys.stderr)
    return 0
