"""Expand a single-master Curto Glyphs source into the 400-700 multi-master one.

This produced the sources currently committed at ``sources/CurtoSerif.glyphs`` and
``sources/CurtoSerif-Italic.glyphs``. Kept for reproducibility: run it against a
checkout of the original single-master sources.

    python make_sources.py <single>.glyphs <multi>.glyphs [--italic] [--version 1.001]
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glyphsLib import dump, load  # noqa: E402

import curto_embolden  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--italic", action="store_true")
    ap.add_argument("--version", default="1.001")
    args = ap.parse_args()

    font = load(args.infile)
    if len(font.masters) > 1:
        raise SystemExit(f"{args.infile} already has {len(font.masters)} masters; nothing to do")

    curto_embolden.add_weights(font, is_italic=args.italic)

    major, _, minor = args.version.partition(".")
    font.versionMajor = int(major)
    font.versionMinor = int(minor)
    with open(args.outfile, "w") as fp:
        dump(font, fp)
    print("wrote", args.outfile, "with", len(font.masters), "masters")


if __name__ == "__main__":
    main()
