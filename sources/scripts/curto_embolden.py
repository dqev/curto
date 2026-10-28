"""Curto Serif weight-builder.

Topology-preserving point offsetting is used to synthesise heavier weights from
the Regular (400) master.  Because every generated master keeps the exact same
contour/point structure as the source, the results stay interpolation-compatible
and can be used to build a variable font.

The offset amount grows linearly with the weight value:

    a = KMAX * (weight - 400)        horizontal overshoot (em units)
    b = RATIO * a                    vertical overshoot

Outer contours grow by (a, b); counters (holes) grow by (HOLE * a, HOLE * b),
which keeps the counters from closing up at Black.  A piecewise-linear vertical
remap re-pins the baseline, x-height, cap-height and descender so the heavier
weights keep the same alignment zones as the source.

``add_weights`` expands a single-master Glyphs source into a 400-700 multi-master
source; ``embolden_points`` is the primitive used for the generated masters.
"""

import copy
import math

from glyphsLib import classes as gs
from glyphsLib.types import Point, Transform

BASE = 400
WEIGHTS = {
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
}
WEIGHT_CLASS = dict(WEIGHTS)

KMAX = 0.075
RATIO = 0.5
HOLE = 0.55


def signed_area(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _unit(vx, vy):
    L = math.hypot(vx, vy)
    if L < 1e-9:
        return None
    return vx / L, vy / L


def _offset_point(P, A, B, r, ccw_outer=False):
    def nrm(dx, dy):
        u = _unit(dx, dy)
        if u is None:
            return None
        tx, ty = u
        if ccw_outer:
            return ty, -tx
        return -ty, tx

    n1 = nrm(P[0] - A[0], P[1] - A[1])
    n2 = nrm(B[0] - P[0], B[1] - P[1])
    if n1 is None and n2 is None:
        return P[0], P[1]
    if n1 is None:
        n1 = n2
    if n2 is None:
        n2 = n1
    mx, my = (n1[0] + n2[0]) / 2.0, (n1[1] + n2[1]) / 2.0
    mu = _unit(mx, my)
    if mu is None:
        return P[0] + n1[0] * r, P[1] + n1[1] * r
    if n1[0] * n2[0] + n1[1] * n2[1] > 0.9995:
        return P[0] + n1[0] * r, P[1] + n1[1] * r
    ax, ay = A[0] + n1[0] * r, A[1] + n1[1] * r
    bx, by = P[0] + n2[0] * r, P[1] + n2[1] * r
    d1x, d1y = P[0] - A[0], P[1] - A[1]
    d2x, d2y = B[0] - P[0], B[1] - P[1]
    den = d1x * d2y - d1y * d2x
    if abs(den) < 1e-6:
        return P[0] + mu[0] * r, P[1] + mu[1] * r
    s = ((bx - ax) * d2y - (by - ay) * d2x) / den
    qx, qy = ax + s * d1x, ay + s * d1y
    if math.hypot(qx - P[0], qy - P[1]) > 2.6 * r:
        return P[0] + mu[0] * r, P[1] + mu[1] * r
    return qx, qy


def _remap_factory(b, base, xh, cap, desc):
    pairs = [(desc - b, desc), (base - b, base), (xh + b, xh), (cap + b, cap)]

    def f(y):
        if y <= pairs[0][0]:
            (x0, y0), (x1, y1) = pairs[0], pairs[1]
        elif y >= pairs[-1][0]:
            (x0, y0), (x1, y1) = pairs[-2], pairs[-1]
        else:
            for (x0, y0), (x1, y1) in zip(pairs, pairs[1:]):
                if x0 <= y <= x1:
                    break
        if x1 == x0:
            return y1
        return y0 + (y - x0) * (y1 - y0) / (x1 - x0)

    return f


def embolden_points(pts, a, b, base, xh, cap, desc, remap=True, ccw_outer=False):
    """Offset a closed contour of ``(x, y)`` tuples outward by ``a`` / ``b``.

    ``ccw_outer`` selects the winding convention: True for Glyphs/cubic sources
    (outer contours are counter-clockwise), False for built TTF outlines (outer
    contours are clockwise).
    """
    if a <= 1e-9:
        return pts
    ar = signed_area(pts)
    if abs(ar) < 1e-6:
        return pts
    outer = (ar > 0) if ccw_outer else (ar < 0)
    da = a if outer else a * HOLE
    db = b if outer else b * HOLE
    k = a / b if b else 1.0
    n = len(pts)
    ys = [p[1] for p in pts]
    ymin, ymax = min(ys), max(ys)
    do_remap = remap and not (ymax < base - 1 or ymin > cap + 1)
    rf = _remap_factory(b, base, xh, cap, desc) if do_remap else None
    out = []
    for i, (x, y) in enumerate(pts):
        ax, ay = pts[(i - 1) % n]
        bx, by = pts[(i + 1) % n]
        P = (x, y * k)
        A = (ax, ay * k)
        B = (bx, by * k)
        qx, qy = _offset_point(P, A, B, da, ccw_outer)
        nx = qx + da
        ny = qy / k
        if rf is not None:
            ny = rf(ny)
        out.append((nx, ny))
    return out


def _layer_points(path):
    return [(n.position.x, n.position.y) for n in path.nodes]


def _set_layer_points(path, pts):
    for node, (x, y) in zip(path.nodes, pts):
        node.position = type(node.position)(int(round(x)), int(round(y)))


def clone_layer(src, new_id, new_name):
    nl = gs.GSLayer()
    nl.layerId = new_id
    nl.associatedMasterId = new_id
    nl.name = new_name
    nl.width = src.width
    if hasattr(src, "attributes"):
        nl.attributes = copy.deepcopy(src.attributes)
    for p in src.paths:
        np = gs.GSPath()
        np.closed = p.closed
        np.attributes = copy.deepcopy(p.attributes)
        np.nodes = [
            gs.GSNode(
                position=Point(n.position.x, n.position.y),
                type=n.type,
                smooth=n.smooth,
                name=n.name,
            )
            for n in p.nodes
        ]
        nl.paths.append(np)
    for c in src.components:
        nc = gs.GSComponent()
        nc.componentName = c.componentName
        nc.transform = copy.copy(c.transform)
        nc.alignment = c.alignment
        nc.anchor = c.anchor
        nc.name = c.name
        nl.components.append(nc)
    for a in src.anchors:
        nl.anchors.append(gs.GSAnchor(name=a.name, position=Point(a.position.x, a.position.y)))
    return nl


def embolden_layer(layer, amount, metrics):
    a = KMAX * (amount - BASE)
    b = RATIO * a
    if a <= 1e-9:
        return
    areas = []
    for path in layer.paths:
        if path.closed:
            areas.append(abs(signed_area(_layer_points(path))))
    ccw_outer = False
    if areas:
        biggest = max(range(len(areas)), key=lambda i: areas[i])
        picked = [p for p in layer.paths if p.closed][biggest]
        ccw_outer = signed_area(_layer_points(picked)) > 0
    for path in layer.paths:
        if not path.closed:
            continue
        pts = _layer_points(path)
        pts = embolden_points(pts, a, b, *metrics, ccw_outer=ccw_outer)
        _set_layer_points(path, pts)
    for comp in layer.components:
        t = comp.transform
        v = list(t.value) if hasattr(t, "value") else list(t)
        comp.transform = Transform(v[0], v[1], v[2], v[3], v[4] + a, v[5])
    for anchor in layer.anchors:
        anchor.position = type(anchor.position)(anchor.position.x + a, anchor.position.y)
    if layer.width and layer.width > 0:
        layer.width = layer.width + 2 * a


def _master_metrics(font):
    m = font.masters[0]
    xh = m.xHeight
    cap = m.capHeight
    base = 0
    desc = m.descender
    for g in font.glyphs:
        if g.name == "x":
            for p in g.layers[m.id].paths:
                base = min(base, min(n.position.y for n in p.nodes))
    return (base, xh, cap, desc)


def add_weights(font, is_italic=False):
    """Expand ``font`` (single 400 master) into a 400-700 multi-master font."""
    m0 = font.masters[0]
    metrics = _master_metrics(font)

    font.axes = [a for a in font.axes if a.axisTag == "wght"]
    m0.axes = [BASE]
    m0.weight = WEIGHT_CLASS[BASE]
    base_id = m0.id

    new_masters = []
    for w in sorted(WEIGHTS):
        if w == BASE:
            continue
        nm = gs.GSFontMaster()
        nm.id = f"m{w}"
        nm.weight = WEIGHT_CLASS[w]
        nm.width = m0.width
        nm.axes = [w]
        nm.visible = m0.visible
        nm._customParameters = copy.deepcopy(list(m0._customParameters))
        nm.metrics = copy.deepcopy(list(m0.metrics))
        nm.guides = copy.deepcopy(list(m0.guides))
        nm.stems = list(m0.stems)
        nm._userData = copy.deepcopy(m0._userData)
        nm.alignmentZones = copy.deepcopy(m0.alignmentZones)
        font.masters.append(nm)
        new_masters.append((w, nm))

    for g in font.glyphs:
        src = g.layers[base_id]
        for w, nm in new_masters:
            nl = clone_layer(src, nm.id, nm.name)
            embolden_layer(nl, w, metrics)
            g.layers.append(nl)

    kerning = getattr(font, "kerning", {})
    if kerning:
        base_kern = kerning.get(base_id, {})
        for w, nm in new_masters:
            factor = 1.0 + 0.12 * (w - BASE) / (700 - BASE)
            newk = {}
            for left, rights in base_kern.items():
                newk[left] = {}
                for right, val in rights.items():
                    newk[left][right] = int(round(val * factor)) if isinstance(val, int) else val
            kerning[nm.id] = newk

    inst = list(font.instances)
    for i in inst:
        i.axes = [BASE]
        i.isItalic = is_italic
        i.name = "Italic" if is_italic else "Regular"
    for w in sorted(WEIGHTS):
        if w == BASE:
            continue
        i = gs.GSInstance()
        i.weight = WEIGHT_CLASS[w]
        i.name = f"{WEIGHTS[w]} Italic" if is_italic else WEIGHTS[w]
        i.axes = [w]
        i.isBold = w == 700
        i.isItalic = is_italic
        inst.append(i)
    font.instances = inst
    return font
