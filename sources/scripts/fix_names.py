"""Normalise name/OS2/head/fvar/STAT metadata for the Curto Serif family.

fontmake's naming is driven by the Glyphs instance names and produces a mix of
legacy and typographic families (and drops the ``Italic`` suffix from PostScript
names).  This module rewrites the naming of every shipped font consistently:

    nameID 1/16  Curto Serif
    nameID 2/17  Regular | Medium | SemiBold | Bold | ExtraBold | Black (+ " Italic")
    nameID 4     Curto Serif <style>
    nameID 6     CurtoSerif-<style>          (no spaces)
    nameID 5     Version <version>
    nameID 3     <version>;NONE;<ps name>
"""

import argparse

from axisregistry import build_fvar_instances, build_name_table, build_stat
from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram

WEIGHTS = [400, 500, 600, 700]
STYLES = {
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
}
WIN = (3, 1, 0x409)
MAC = (1, 0, 0)

FAMILY = "Curto Serif"
COPYRIGHT = "Copyright 2026 The Curto Serif Project Authors (https://github.com/dqev/curto)"
LICENSE = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at: https://openfontlicense.org"
)
LICENSE_URL = "https://openfontlicense.org"
VENDOR_ID = "DQCU"


def style_name(weight, italic=False):
    base = STYLES[weight]
    if not italic:
        return base
    return "Italic" if weight == 400 else f"{base} Italic"


def ps_style(weight, italic=False):
    base = STYLES[weight]
    if not italic:
        return base
    return "Italic" if weight == 400 else f"{base}Italic"


def set_name(font, nid, value):
    """Set every encoding of ``nid`` to ``value``; add one if absent."""
    name = font["name"]
    found = False
    for rec in name.names:
        if rec.nameID == nid:
            rec.string = value
            found = True
    if not found:
        name.setName(value, nid, *WIN)
        name.setName(value, nid, *MAC)


def add_name(font, value):
    """Return the name ID for ``value``, adding a record if needed."""
    name = font["name"]
    for rec in name.names:
        if rec.platformID == WIN[0] and rec.platEncID == WIN[1] and rec.langID == WIN[2]:
            if rec.toUnicode() == value:
                return rec.nameID
    nid = 256
    existing = {r.nameID for r in name.names}
    while nid in existing:
        nid += 1
    name.setName(value, nid, *WIN)
    name.setName(value, nid, *MAC)
    return nid


def _add_stat(font, italic, weight=None):
    weight_values = []
    for w in ([weight] if weight is not None else WEIGHTS):
        value = {"value": w, "name": STYLES[w]}
        if w == 400:
            value.update({"flags": 0x2, "linkedValue": 700})
        weight_values.append(value)
    ital_values = (
        [{"value": 1, "name": "Italic", "flags": 0x0}]
        if italic
        else [{"value": 0, "name": "Roman", "flags": 0x2, "linkedValue": 1}]
    )
    buildStatTable(
        font,
        [
            {"tag": "wght", "name": "Weight", "ordering": 0, "values": weight_values},
            {"tag": "ital", "name": "Italic", "ordering": 1, "values": ital_values},
        ],
        elidedFallbackName="Italic" if italic else "Regular",
    )


def _add_unhinted_tables(font):
    if "glyf" not in font or "fpgm" in font or ("gasp" in font and "prep" in font):
        return
    gasp = newTable("gasp")
    gasp.gaspRange = {0xFFFF: 15}
    program = ttProgram.Program()
    program.fromAssembly(["PUSHW[]", "511", "SCANCTRL[]", "PUSHB[]", "4", "SCANTYPE[]"])
    prep = newTable("prep")
    prep.program = program
    font["gasp"] = gasp
    font["prep"] = prep


def _set_metadata(font, weight):
    os2 = font["OS/2"]
    os2.fsType = 0
    os2.achVendID = VENDOR_ID
    os2.panose.bFamilyType = 2
    os2.panose.bSerifStyle = 2
    os2.panose.bProportion = 3
    os2.panose.bWeight = 5 if weight == 400 else 6 if weight == 500 else 7 if weight == 600 else 8
    font["post"].isFixedPitch = 0
    font["hhea"].ascent = 936
    font["hhea"].descent = -264
    font["hhea"].lineGap = 0
    os2.sTypoAscender = 936
    os2.sTypoDescender = -264
    os2.sTypoLineGap = 0
    os2.usWinAscent = 936
    os2.usWinDescent = 282
    os2.fsSelection |= 0x80
    set_name(font, 0, COPYRIGHT)
    set_name(font, 13, LICENSE)
    set_name(font, 14, LICENSE_URL)
    _add_unhinted_tables(font)


def _set_flags(font, weight, italic, regular):
    os2 = font["OS/2"]
    head = font["head"]
    os2.usWeightClass = weight
    os2.usWidthClass = 5

    fs = os2.fsSelection
    fs &= ~0x21  # clear ITALIC (0x01) and BOLD (0x20)
    if italic:
        fs |= 0x01
    if weight >= 700:
        fs |= 0x20
    fs &= ~0x40  # clear REGULAR
    if regular:
        fs |= 0x40
    os2.fsSelection = fs

    mac = head.macStyle
    mac &= ~0x03
    if weight >= 700:
        mac |= 0x01
    if italic:
        mac |= 0x02
    head.macStyle = mac


def fix_static(path, weight, italic=False, version="1.001", out=None):
    font = TTFont(path)
    style = style_name(weight, italic)
    set_name(font, 1, FAMILY)
    set_name(font, 2, style)
    set_name(font, 16, FAMILY)
    set_name(font, 17, style)
    build_name_table(font, family_name=FAMILY, style_name=style)
    _add_stat(font, italic, weight)
    ps = font["name"].getDebugName(6)
    set_name(font, 3, f"{version};NONE;{ps}")
    set_name(font, 5, f"Version {version}")
    if "CFF " in font:
        font["CFF "].cff.fontNames = [ps]
    font["head"].fontRevision = float(version)
    _set_metadata(font, weight)
    font.save(out or path)
    return out or path


def fix_variable(path, italic=False, version="1.001", out=None):
    font = TTFont(path)
    style = "Italic" if italic else "Regular"
    set_name(font, 1, FAMILY)
    set_name(font, 2, style)
    set_name(font, 16, FAMILY)
    set_name(font, 17, style)
    build_name_table(font, family_name=FAMILY, style_name=style)
    build_fvar_instances(font)
    build_stat(font)
    _add_stat(font, italic)
    ps = font["name"].getDebugName(6)
    set_name(font, 3, f"{version};NONE;{ps}")
    set_name(font, 5, f"Version {version}")
    font["head"].fontRevision = float(version)
    _set_metadata(font, 400)
    font.save(out or path)
    return out or path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--weight", type=int)
    ap.add_argument("--italic", action="store_true")
    ap.add_argument("--variable", action="store_true")
    ap.add_argument("--version", default="1.001")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    if args.variable:
        print(fix_variable(args.path, args.italic, args.version, args.out))
    else:
        if args.weight is None:
            ap.error("--weight is required for static fonts")
        print(fix_static(args.path, args.weight, args.italic, args.version, args.out))


if __name__ == "__main__":
    main()
