#!/usr/bin/env python3
"""Régénère content/carte-monde.json (contours des pays, déjà projetés) depuis Natural Earth.

Source : Natural Earth 1:50m, Admin 0 – Countries (domaine public), à placer dans
sources/ne_50m_admin_0_countries.geojson :
  curl -o sources/ne_50m_admin_0_countries.geojson \\
    https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson

Projection : équirectangulaire, x = lon · cos(35°) · 10, y = -lat · 10.
Identique à PROJ_MONDE dans index.html : à changer ensemble.
"""
import json, math

K, COS = 10.0, math.cos(math.radians(35))
TOL = 0.5          # tolérance de simplification (unités projetées ; 1 unité = 0,1° de latitude ≈ 11 km)
AIRE_MIN = 0.15    # on écarte les îlots plus petits (unités²), sauf le plus grand anneau de chaque pays
EXCLUS = {"ATA"}   # Antarctique

def P(lon, lat): return (lon * COS * K, -lat * K)

def dp(pts, tol):
    """Douglas-Peucker (itératif)"""
    if len(pts) < 3: return pts
    garde = [False] * len(pts); garde[0] = garde[-1] = True
    pile = [(0, len(pts) - 1)]
    while pile:
        a, b = pile.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]; dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy)
        dmax, imax = 0, None
        for i in range(a + 1, b):
            x, y = pts[i]; d = abs(dy * (x - x1) - dx * (y - y1)) / L if L > 1e-6 else math.hypot(x - x1, y - y1)   # anneau fermé : extrémités confondues
            if d > dmax: dmax, imax = d, i
        if imax is not None and dmax > tol:
            garde[imax] = True; pile += [(a, imax), (imax, b)]
    return [p for p, g in zip(pts, garde) if g]

def aire(pts): return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2

def anneaux(g):
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    return [[P(lon, lat) for lon, lat in r] for poly in polys for r in poly]

src = json.load(open("sources/ne_50m_admin_0_countries.geojson"))
pays = {}
for f in src["features"]:
    pr = f["properties"]; code = pr["ADM0_A3"]
    if code in EXCLUS: continue
    rs = [dp(r, TOL) for r in anneaux(f["geometry"])]
    rs = [r for r in rs if len(r) >= 4]
    if not rs: continue
    plus_grand = max(rs, key=aire)
    cx = lambda r: sum(x for x, _ in r) / len(r)
    # territoires lointains (outre-mer français, îles Chatham, Aléoutiennes…) : écartés s'ils sont à plus de 30° de longitude
    # du corps principal et petits, sinon le cadre du pays s'étire sur la moitié du monde. Madère, les Canaries, l'Alaska restent.
    A = aire(plus_grand)
    rs = [r for r in rs if r is plus_grand or (aire(r) >= AIRE_MIN and (abs(cx(r) - cx(plus_grand)) < 30 * COS * K or aire(r) >= .2 * A))]
    d = "".join("M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in r[:-1]) + "Z" for r in rs)
    pays[code] = {"n": pr.get("NAME_FR") or pr["NAME"], "d": d}

out = {"source": "Contours : Natural Earth (domaine public)", "proj": {"k": K, "cos": COS}, "pays": pays}
json.dump(out, open("content/carte-monde.json", "w"), ensure_ascii=False, separators=(",", ":"))
print(len(pays), "pays,", round(len(json.dumps(out, ensure_ascii=False)) / 1024), "Ko")
