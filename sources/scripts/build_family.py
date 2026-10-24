"""Build the complete Curto Serif family (400-900, Roman + Italic).

Outputs, all written into ``fonts/``:

    ttf/       4 static TTFs (quadratic) per face
    variable/  CurtoSerif[wght].ttf and CurtoSerif-Italic[wght].ttf
    otf/       4 static OTFs (cubic) per face
    webfonts/  WOFF2 for every TTF (statics + variable)

Pipeline (per face, Roman then Italic):

  1. fontmake builds the six interpolated OTFs straight from the multi-master
     Glyphs source.
  2. fontmake builds the Regular TTF, which becomes the binary base.
  3. The 500-900 masters are synthesised from the base TTF by topology-preserving
     point offsetting (``embolden_ttf``), guaranteeing point compatibility.
  4. ``varLib`` assembles those six quadratic masters into the wght variable font.
  5. ``fix_names`` rewrites naming/OS2/head/fvar/STAT on every artefact, and
     WOFF2 is generated from the finished TTFs.
"""

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import embolden_ttf as binbuild  # noqa: E402
import fix_names  # noqa: E402

WEIGHTS = binbuild.WEIGHTS
STYLES = binbuild.STYLES
BASE = binbuild.BASE


def run(cmd, **kw):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def build_otfs(fontmake, source, out_dir, work):
    os.makedirs(out_dir, exist_ok=True)
    run([
        *fontmake, "-g", source, "-i", "-o", "otf",
        "--filter", "...",
        "--filter", "FlattenComponentsFilter",
        "--filter", "DecomposeTransformedComponentsFilter",
        "--output-dir", out_dir,
        "--master-dir", os.path.join(work, "master_ufo"),
        "--instance-dir", os.path.join(work, "instance_ufo"),
    ])


def build_base_ttf(fontmake, source, out_dir, work):
    os.makedirs(out_dir, exist_ok=True)
    run([
        *fontmake, "-g", source, "-i", "-o", "ttf",
        "--filter", "...",
        "--filter", "FlattenComponentsFilter",
        "--filter", "DecomposeTransformedComponentsFilter",
        "--output-dir", out_dir,
        "--master-dir", os.path.join(work, "master_ufo"),
        "--instance-dir", os.path.join(work, "instance_ufo"),
    ])


def otf_src_name(weight, italic):
    if italic and weight == BASE:
        return "CurtoSerif-Italic.otf"
    return f"CurtoSerif-{STYLES[weight]}.otf"


def woff2(src, dst):
    from fontTools.ttLib.woff2 import compress

    compress(src, dst)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    sources_default = os.path.dirname(here)
    repo = os.path.dirname(sources_default)

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources-dir", default=sources_default)
    ap.add_argument("--fonts-dir", default=os.path.join(repo, "fonts"))
    ap.add_argument("--version", default="1.001")
    ap.add_argument("--build-dir", default=None)
    ap.add_argument("--skip-otf", action="store_true")
    ap.add_argument("--skip-vf", action="store_true")
    args = ap.parse_args()

    sources = os.path.abspath(args.sources_dir)
    fonts = os.path.abspath(args.fonts_dir)
    build = args.build_dir or os.path.join(repo, "build")
    fontmake = [sys.executable, "-m", "fontmake"]

    for sub in ("otf", "ttf", "variable", "webfonts"):
        os.makedirs(os.path.join(fonts, sub), exist_ok=True)

    faces = [
        {"name": "roman", "glyphs": os.path.join(sources, "Curto.glyphs"), "italic": False},
        {"name": "italic", "glyphs": os.path.join(sources, "Curto_Italic.glyphs"), "italic": True},
    ]

    for face in faces:
        italic = face["italic"]
        work = os.path.join(build, face["name"])
        otf_out = os.path.join(work, "otf")
        ttf_out = os.path.join(work, "ttf-src")
        bin_out = os.path.join(work, "masters")

        if not args.skip_otf:
            build_otfs(fontmake, face["glyphs"], otf_out, work)
        build_base_ttf(fontmake, face["glyphs"], ttf_out, work)

        base_src = os.path.join(ttf_out, "CurtoSerif-Italic.ttf" if italic else "CurtoSerif-Regular.ttf")

        # 3. binary masters + statics
        metrics = None
        masters = {}
        for w in WEIGHTS:
            dst = os.path.join(bin_out, binbuild.file_stem(w, italic) + ".ttf")
            if w == BASE:
                metrics = binbuild.derive_metrics(binbuild.TTFont(base_src))
                os.makedirs(bin_out, exist_ok=True)
                shutil.copyfile(base_src, dst)
            else:
                _, metrics = binbuild.embolden_ttf(base_src, dst, w, metrics)
            masters[w] = dst

        # 4. variable font
        vf_path = None
        if not args.skip_vf:
            vf_path = os.path.join(bin_out, ("CurtoSerif-Italic[wght].ttf" if italic else "CurtoSerif[wght].ttf"))
            binbuild.build_vf(masters, vf_path, style="Italic" if italic else "Regular")

        # 5. fix names, copy into src/fonts, derive woff2
        for w in WEIGHTS:
            stem = binbuild.file_stem(w, italic)
            dst = os.path.join(fonts, "ttf", stem + ".ttf")
            fix_names.fix_static(masters[w], w, italic, args.version, dst)
            woff2(dst, os.path.join(fonts, "webfonts", stem + ".woff2"))

            if not args.skip_otf:
                src_otf = os.path.join(otf_out, otf_src_name(w, italic))
                dst_otf = os.path.join(fonts, "otf", stem + ".otf")
                fix_names.fix_static(src_otf, w, italic, args.version, dst_otf)

        if vf_path:
            dst_vf = os.path.join(fonts, "variable", os.path.basename(vf_path))
            fix_names.fix_variable(vf_path, italic, args.version, dst_vf)
            woff2(dst_vf, os.path.join(fonts, "webfonts", os.path.basename(vf_path).replace(".ttf", ".woff2")))

    print("\nDone. Artefacts written to", fonts)


if __name__ == "__main__":
    main()
