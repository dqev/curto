"""Binary (compiled TTF) weight builder for Curto Serif.

Unlike the Glyphs-source route (``curto_embolden.add_weights``), this operates on
the *compiled* Regular TTF.  It applies the same topology-preserving point
offset to the quadratic outlines, so every generated master keeps an identical
point structure and the masters can be fed straight to ``varLib`` to build the
variable font.

This route is required for the variable font: fontmake's per-instance cu2qu step
re-splits curves differently at every weight, so the interpolated static TTFs
are *not* point-compatible with each other.
"""

import argparse
import os

from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    SourceDescriptor,
)
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.varLib import build as varlib_build

from curto_embolden import HOLE, KMAX, RATIO, embolden_points

BASE = 400
WEIGHTS = [400, 500, 600, 700]
STYLES = {
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
}
DESCENDER_GLYPHS = ("p", "q", "y")


def style_name(weight, italic=False):
    base = STYLES[weight]
    if not italic:
        return base
    return "Italic" if weight == BASE else f"{base} Italic"


def file_stem(weight, italic=False):
    base = STYLES[weight]
    if not italic:
        return f"CurtoSerif-{base}"
    return f"CurtoSerif-{base}Italic" if weight != BASE else "CurtoSerif-Italic"


def derive_metrics(font):
    """(baseline, x-height, cap-height, descender) used by the vertical remap."""
    os2 = font["OS/2"]
    base = 0
    if "x" in font.getGlyphOrder():
        g = font["glyf"]["x"]
        if g.numberOfContours > 0:
            base = min(base, g.yMin)
    lows = []
    for name in DESCENDER_GLYPHS:
        if name in font.getGlyphOrder():
            g = font["glyf"][name]
            if g.numberOfContours > 0:
                lows.append(g.yMin)
    desc = min(lows) if lows else os2.sTypoDescender
    return (base, os2.sxHeight, os2.sCapHeight, desc)


def embolden_glyph(g, amount, metrics, kmax=KMAX, ratio=RATIO, hole=HOLE):
    if g.numberOfContours <= 0:
        return
    a = kmax * (amount - BASE)
    b = ratio * a
    if a <= 1e-6:
        return
    coords = list(g.coordinates)
    starts = [0] + list(g.endPtsOfContours[:-1])
    ends = list(g.endPtsOfContours)
    for s, e in zip(starts, ends):
        idx = list(range(s, e + 1))
        pts = [tuple(coords[i]) for i in idx]
        new = embolden_points(pts, a, b, *metrics, ccw_outer=False)
        for k, i in enumerate(idx):
            coords[i] = new[k]
    g.coordinates = GlyphCoordinates([(int(round(x)), int(round(y))) for x, y in coords])


def embolden_ttf(src, dst, weight, metrics=None, kmax=KMAX, ratio=RATIO, hole=HOLE):
    """Write a heavier master derived from the 400 ``src`` TTF."""
    font = TTFont(src)
    if metrics is None:
        metrics = derive_metrics(font)
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    a = kmax * (weight - BASE)
    for name in font.getGlyphOrder():
        embolden_glyph(glyf[name], weight, metrics, kmax, ratio, hole)
        aw, lsb = hmtx[name]
        if aw > 0:
            hmtx[name] = (int(round(aw + 2 * a)), lsb)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    font.save(dst)
    return dst, metrics


def build_vf(master_paths, dst, family="Curto Serif", style="Regular"):
    """Build a single-axis (wght) variable font from quadratic masters."""
    ds = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.name = "Weight"
    axis.tag = "wght"
    axis.minimum = BASE
    axis.maximum = 700
    axis.default = BASE
    ds.addAxis(axis)
    for w, path in sorted(master_paths.items()):
        src = SourceDescriptor()
        src.path = os.path.abspath(path)
        src.location = {"Weight": w}
        src.familyName = family
        src.styleName = STYLES[w]
        ds.addSource(src)
    vf, _, _ = varlib_build(ds)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    vf.save(dst)
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("regular_ttf", help="compiled 400 master TTF")
    ap.add_argument("out_dir")
    ap.add_argument("--italic", action="store_true")
    args = ap.parse_args()

    metrics = None
    for w in WEIGHTS:
        stem = file_stem(w, args.italic)
        dst = os.path.join(args.out_dir, stem + ".ttf")
        if w == BASE:
            metrics = derive_metrics(TTFont(args.regular_ttf))
            TTFont(args.regular_ttf).save(dst)
            print(f"w{w} -> {dst}  metrics={metrics}")
            continue
        _, metrics = embolden_ttf(args.regular_ttf, dst, w, metrics)
        print(f"w{w} -> {dst}")


if __name__ == "__main__":
    main()
