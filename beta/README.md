# Curto Serif — 1.001 beta (multiple weights + variable)

This folder is a **self-contained beta**. Nothing here touches the shipped
`src/` sources or the `CurtoSerif-1.000` release.

## What's inside

| Path | Contents |
| --- | --- |
| `sources/` | Multi-master Glyphs sources (four masters, `wght` 400–700) for Roman and Italic |
| `scripts/` | Build pipeline (see *Rebuilding*) |
| `fonts/ttf/` | 8 static TTFs + two variable TTFs (`CurtoSerif[wght].ttf`, `CurtoSerif-Italic[wght].ttf`) |
| `fonts/otf/` | 8 static OTFs |
| `fonts/webfonts/` | WOFF2 for every TTF, including the variable fonts |
| `curto.css` | Web stylesheet (static faces + variable faces) |
| `CurtoSerif-1.001-beta.zip` | Download bundle (fonts, CSS, license) |

## Weights

Regular 400 · Medium 500 · SemiBold 600 · Bold 700,
each in Roman and Italic, plus a continuous `wght` axis (400–700) in both
variable fonts.

## Install

**Desktop** — install the `.otf` (or `.ttf`) files.
- macOS: double-click → *Install Font*.
- Windows: right-click → *Install*.

**Web** — link the stylesheet and use `font-weight` 400–900:

```html
<link rel="stylesheet" href="curto.css">
<h1 style='font-family:"Curto Serif";font-weight:800'>Heavy headline</h1>
<p style='font-family:"Curto Serif";font-style:italic;font-weight:500'>Medium italic</p>
```

## How the weights were made

The Regular (400) master is the only drawn master. The heavier masters are
produced by **topology-preserving point offsetting** (see
`scripts/curto_embolden.py`), which keeps every contour point-identical so the
result can be interpolated:

- a contour's points are pushed outward along their angle bisectors
  (`a = KMAX · (weight − 400)` horizontally, `b = RATIO · a` vertically);
- counters grow by a smaller factor (`HOLE`) so they stay open at Bold;
- a piecewise-linear vertical remap re-pins the baseline, x-height, cap-height
  and descender;
- sidebearings grow by `2a`, component offsets shift by `a`, anchors follow.

Two build routes exist:

1. **Sources / OTF** — `fontmake` interpolates the six masters in the Glyphs
   source and compiles them.
2. **TTF / variable** — the compiled 400 TTF is emboldened directly
   (`scripts/embolden_ttf.py`) and `varLib` assembles the variable font. The
   compiled route is required for the variable font because `fontmake`'s
   per-instance cu2qu step re-splits curves differently at each weight, so the
   interpolated static TTFs are not point-compatible with one another.

## Rebuilding

From the repository root:

```sh
.venv/bin/python beta/scripts/build_family.py
```

Writes the TTFs, OTFs and WOFF2 into `beta/fonts/` (scratch files go to
`beta/build/`). `beta/scripts/make_sources.py` documents how the committed
multi-master sources were generated from the original single-master sources.

## License

SIL Open Font License 1.1 — see `../OFL.txt`.
