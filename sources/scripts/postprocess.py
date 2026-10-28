"""Apply family metadata to gftools builder output and regenerate WOFF2."""

import argparse
import os
import sys

from fontTools.ttLib.woff2 import compress

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fix_names  # noqa: E402

STATIC_STYLES = {
    "CurtoSerif-Regular": (400, False),
    "CurtoSerif-Medium": (500, False),
    "CurtoSerif-SemiBold": (600, False),
    "CurtoSerif-Bold": (700, False),
    "CurtoSerif-Italic": (400, True),
    "CurtoSerif-MediumItalic": (500, True),
    "CurtoSerif-SemiBoldItalic": (600, True),
    "CurtoSerif-BoldItalic": (700, True),
}

VARIABLE_FONTS = {
    "CurtoSerif[wght].ttf": False,
    "CurtoSerif-Italic[wght].ttf": True,
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(here))

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fonts-dir", default=os.path.join(repo, "fonts"))
    ap.add_argument("--version", default="1.001")
    args = ap.parse_args()

    fonts = os.path.abspath(args.fonts_dir)
    webfonts = os.path.join(fonts, "webfonts")
    os.makedirs(webfonts, exist_ok=True)

    for stem, (weight, italic) in STATIC_STYLES.items():
        for extension in ("ttf", "otf"):
            path = os.path.join(fonts, extension, f"{stem}.{extension}")
            if os.path.exists(path):
                fix_names.fix_static(path, weight, italic, args.version, out=path)
        ttf = os.path.join(fonts, "ttf", f"{stem}.ttf")
        if os.path.exists(ttf):
            compress(ttf, os.path.join(webfonts, f"{stem}.woff2"))

    for filename, italic in VARIABLE_FONTS.items():
        path = os.path.join(fonts, "variable", filename)
        if not os.path.exists(path):
            continue
        fix_names.fix_variable(path, italic, args.version, out=path)
        compress(path, os.path.join(webfonts, filename.replace(".ttf", ".woff2")))

    print("Postprocessed fonts in", fonts)


if __name__ == "__main__":
    main()
