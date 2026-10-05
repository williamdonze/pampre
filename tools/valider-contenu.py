#!/usr/bin/env python3
"""Valide le contenu de Pampre (content/*.json) contre les règles de CLAUDE.md.

Usage : python3 tools/valider-contenu.py        (code de sortie 1 s'il y a des erreurs)

Vérifie : JSON valides et conformes aux formats ; liens [[terme]] et « voir » du glossaire ;
illustrations (illu) existantes dans index.html ; étiquettes référencées et champs ciblés ;
index « bonne » dans les bornes ; catégories du tri ; régions de la carte ; vins du palier 1
dans leur région (même test que le jeu : départements de la région) ; identifiants en double ;
explications manquantes. Les avertissements (⚠) signalent ce qui mérite une relecture humaine.
"""
import json, math, re, sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
C = RACINE / "content"
erreurs, avertissements = [], []
def err(lieu, msg): erreurs.append(f"{lieu} : {msg}")
def avert(lieu, msg): avertissements.append(f"{lieu} : {msg}")

def charger(nom):
    try:
        return json.loads((C / nom).read_text(encoding="utf-8"))
    except FileNotFoundError:
        err(nom, "fichier manquant"); return None
    except json.JSONDecodeError as e:
        err(nom, f"JSON invalide ({e})"); return None

# --- ce que le code sait afficher (lu dans index.html, pour rester synchronisé) ---
HTML = (RACINE / "index.html").read_text(encoding="utf-8")
def bloc(debut):
    i = HTML.index(debut); j = HTML.index("\n};", i); return HTML[i:j]
ILLUS = set(re.findall(r'^\s*"?([\w-]+)"?\s*:\s*\(\)\s*=>', bloc("const IL = {"), re.M))
ICONES = set(re.findall(r'(\w+)\s*:\s*I\.\w+', re.search(r"const ICON_BY_NAME = \{([^}]*)\}", HTML).group(1)))
MODELES = set(re.findall(r'^\s*(\w+)\s*:\s*\[', bloc("const LBL_ORDER = {"), re.M))
STYLES = json.loads(re.search(r"const STYLES = (\[[^\]]*\]);", HTML).group(1))
COULEURS_REGIONS = set(re.findall(r'"?([\w-]+)"?\s*:\s*"#', re.search(r"const REGION_COLORS = \{([^}]*)\}", HTML).group(1)))
PAYS_PROPOSES = json.loads(re.search(r'question:"De quel pays vient ce vin \?", choix:shuffle\((\[[^\]]*\])\)', HTML).group(1))
TEINTES = {"creme", "vert", "noir", "or", "bordeaux", "rose"}
CIBLES = {"millesime", "appellation", "producteur", "degre", "volume", "classement", "embouteillage", "sucre", "cepage", "cuvee", "mention", "allergene", "provenance"}
CHAMPS = {"producteur", "cuvee", "classement", "appellation", "mention", "cepage", "sucre", "millesime", "embouteillage", "degre", "volume"}
TYPES = {"qcm", "vf", "ordre", "assoc", "tri", "etiquette", "indices", "carte"}

niveaux = charger("niveaux.json"); gloss = charger("glossaire.json"); etiq = charger("etiquettes.json")
carte = charger("carte-vins.json"); france = charger("carte-france.json")
TERMES = {k.lower(): k for k in (gloss or {}).get("termes", {})}
ETIQ = {e["id"]: e for e in (etiq or {}).get("etiquettes", [])}
REGIONS = {r["id"]: r for r in (carte or {}).get("regions", [])}
BADGES = {b["id"] for b in (niveaux or {}).get("badges", [])}

# --- texte enrichi ---
def verifier_texte(lieu, t, enrichi=True):
    if not isinstance(t, str) or not t.strip():
        err(lieu, "texte vide ou absent"); return
    if t.count("**") % 2: err(lieu, "nombre impair de ** (gras non fermé)")
    if t.count("[[") != t.count("]]"): err(lieu, "[[ et ]] déséquilibrés")
    for m in re.finditer(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", t):
        if not enrichi: err(lieu, f"[[{m.group(1)}]] dans un champ qui n'est pas mis en forme : s'affichera tel quel"); continue
        if m.group(1).lower() not in TERMES: err(lieu, f"terme de glossaire inconnu : [[{m.group(1)}]]")
    if not enrichi and "**" in t: err(lieu, "** dans un champ qui n'est pas mis en forme : s'affichera tel quel")

# --- questions ---
def verifier_question(lieu, q):
    t = q.get("type")
    if t not in TYPES: err(lieu, f"type inconnu : {t}"); return
    if not q.get("explication") and t != "carte": err(lieu, "explication manquante")
    elif q.get("explication"): verifier_texte(lieu + ".explication", q["explication"], enrichi=False)
    if t != "carte": verifier_texte(lieu + ".question", q.get("question"), enrichi=False)
    if t in ("qcm", "indices") or (t == "etiquette" and q.get("mode") == "qcm"):
        ch = q.get("choix") or []
        if len(ch) < 2: err(lieu, "moins de 2 choix")
        if len(ch) > 4: avert(lieu, f"{len(ch)} choix : seules les touches 1 à 4 fonctionnent")
        if len(set(ch)) != len(ch): err(lieu, "choix en double (la correction compare les textes)")
        if not isinstance(q.get("bonne"), int) or not 0 <= q["bonne"] < len(ch): err(lieu, f"index bonne={q.get('bonne')} hors des bornes (0 à {len(ch)-1})")
    if t == "vf" and not isinstance(q.get("bonne"), bool): err(lieu, "vf : bonne doit valoir true ou false")
    if t == "ordre":
        it = q.get("items") or []
        if len(it) < 2: err(lieu, "ordre : moins de 2 étapes")
        if len(set(it)) != len(it): err(lieu, "ordre : étapes en double")
    if t == "assoc":
        p = q.get("paires") or []
        if len(p) < 2 or any(len(x) != 2 for x in p): err(lieu, "assoc : paires mal formées")
        if len({x[0] for x in p}) != len(p) or len({x[1] for x in p}) != len(p): err(lieu, "assoc : texte en double d'un côté")
        if len(p) > 6: avert(lieu, "assoc : plus de 6 paires, les couleurs se répètent")
    if t == "tri":
        cats = q.get("categories") or []
        for txt, c in q.get("items") or []:
            if not isinstance(c, int) or not 0 <= c < len(cats): err(lieu, f"tri : « {txt} » vise la catégorie {c} inexistante")
        if len({x[0] for x in q.get("items") or []}) != len(q.get("items") or []): err(lieu, "tri : étiquettes en double")
        vides = set(range(len(cats))) - {c for _, c in q.get("items") or []}
        if vides: avert(lieu, f"tri : catégorie(s) sans aucun élément : {[cats[i] for i in vides]}")
    if t == "etiquette":
        e = ETIQ.get(q.get("etiquette"))
        if not e: err(lieu, f"étiquette inconnue : {q.get('etiquette')}"); return
        if q.get("mode") == "toucher":
            c = q.get("cible")
            if c not in CIBLES: err(lieu, f"cible inconnue : {c}")
            elif c not in ("allergene", "provenance") and not e["champs"].get(c): err(lieu, f"la cible « {c} » n'existe pas sur l'étiquette {e['id']}")
        elif q.get("mode") != "qcm": err(lieu, f"mode inconnu : {q.get('mode')}")
    if t == "indices" and not q.get("indices"): err(lieu, "indices : liste vide")

# --- niveaux.json ---
if niveaux:
    s = niveaux.get("seuilValidation")
    if not isinstance(s, (int, float)) or not 0 < s <= 1: err("niveaux.json", f"seuilValidation invalide : {s}")
    ids = [n.get("id") for n in niveaux.get("niveaux", [])]
    if ids != list(range(1, len(ids) + 1)): err("niveaux.json", f"ids de niveaux non consécutifs : {ids}")
    for n in niveaux.get("niveaux", []):
        for k in ("titre", "sousTitre", "objectif", "icone"):
            if not n.get(k): err(f"niveau {n.get('id')}", f"champ {k} manquant")
        if n.get("icone") not in ICONES: err(f"niveau {n.get('id')}", f"icône inconnue : {n.get('icone')}")
        if n.get("contenu") and not (RACINE / n["contenu"]).exists(): err(f"niveau {n['id']}", f"fichier {n['contenu']} introuvable")
    if len(ids) > 6: err("niveaux.json", "plus de 6 niveaux : unitColors (index.html) n'a que 6 couleurs")
    xps = [r["xp"] for r in niveaux.get("rangs", [])]
    if xps != sorted(xps) or (xps and xps[0] != 0): err("niveaux.json", f"rangs : seuils XP non croissants ou ne commençant pas à 0 : {xps}")
    seen = set()
    for b in niveaux.get("badges", []):
        if b["id"] in seen: err("badges", f"id en double : {b['id']}")
        seen.add(b["id"])
        if b.get("icone") not in ICONES: err(f"badge {b['id']}", f"icône inconnue : {b.get('icone')}")
    utilises = set(re.findall(r'award\("([\w-]+)"\)', HTML)) | {"niveau-1"}
    for b in BADGES - utilises:
        if not b.startswith("niveau-") and b not in {"lecteur", "gestes"}: avert(f"badge {b}", "jamais attribué par le code")
    for b in utilises - BADGES: err(f"badge {b}", "attribué par le code mais absent de niveaux.json")

# --- niveaux détaillés ---
ids_globaux = {}
def unique(id_, lieu):
    if id_ in ids_globaux: err(lieu, f"identifiant en double « {id_} » (déjà dans {ids_globaux[id_]})")
    ids_globaux[id_] = lieu
for n in (niveaux or {}).get("niveaux", []):
    if not n.get("contenu"): continue
    L = charger(Path(n["contenu"]).name)
    if not L: continue
    nom = Path(n["contenu"]).name
    if L.get("id") != n["id"]: err(nom, f"id {L.get('id')} ≠ {n['id']} déclaré dans niveaux.json")
    lecons = {l["id"]: l for l in L.get("lecons", [])}
    jeux = {g["id"]: g for g in L.get("jeux", [])}
    for step in L.get("parcours", []):
        if step == "quiz": continue
        if step.startswith("jeu:"):
            if step[4:] not in jeux: err(nom, f"parcours : jeu inconnu {step}")
        elif step not in lecons: err(nom, f"parcours : leçon inconnue {step}")
    for l in L.get("lecons", []):
        unique(l["id"], f"{nom} leçon")
        lieu = f"{nom} › {l['id']}"
        if not l.get("titre"): err(lieu, "titre manquant")
        if not isinstance(l.get("duree"), (int, float)) or l["duree"] > 5: err(lieu, f"durée {l.get('duree')} min (5 max)")
        if f"{l['id']}" not in L.get("parcours", []): avert(lieu, "leçon absente du parcours")
        cartes = l.get("cartes", [])
        if not 4 <= len(cartes) <= 6: avert(lieu, f"{len(cartes)} cartes (4 à 6 attendues)")
        if not any(c.get("exemple") for c in cartes): avert(lieu, "aucun vin réel cité en exemple dans la leçon")
        for i, c in enumerate(cartes):
            lc = f"{lieu} carte {i+1}"
            if not c.get("titre"): err(lc, "titre manquant")
            if c.get("illu") not in ILLUS: err(lc, f"illustration inconnue : {c.get('illu')} (repli sur « raisin »)")
            verifier_texte(lc + ".texte", c.get("texte"))
            for k in ("astuce", "debat"):
                if k in c: verifier_texte(f"{lc}.{k}", c[k])
            if "exemple" in c:
                if not c["exemple"].get("vin") or not c["exemple"].get("detail"): err(lc, "exemple incomplet (vin, detail)")
                for k in ("vin", "detail"): verifier_texte(f"{lc}.exemple.{k}", c["exemple"].get(k, "x"), enrichi=False)
        if len(l.get("verif", [])) != 2: avert(lieu, f"{len(l.get('verif', []))} questions de vérification (2 attendues)")
        for i, q in enumerate(l.get("verif", [])): verifier_question(f"{lieu} verif {i}", q)
    for g in L.get("jeux", []):
        unique(g["id"], f"{nom} jeu"); lieu = f"{nom} › jeu {g['id']}"
        if g.get("badge") and g["badge"] not in BADGES: err(lieu, f"badge inconnu : {g['badge']}")
        if g.get("generateur") == "etiquettes":
            if g.get("tours", 10) > len(ETIQ): err(lieu, f"{g.get('tours')} tours pour {len(ETIQ)} étiquettes")
            if g.get("seuilBadge", 0) > g.get("tours", 10): err(lieu, "seuilBadge supérieur au nombre de tours")
        else:
            qs = g.get("questions") or []
            if not qs: err(lieu, "ni générateur ni questions")
            if g.get("seuilBadge", 0) > len(qs): err(lieu, f"seuilBadge {g['seuilBadge']} > {len(qs)} questions : badge inatteignable")
            for i, q in enumerate(qs): verifier_question(f"{lieu} q{i}", q)
    qz = L.get("quiz", {}).get("questions", [])
    if not 12 <= len(qz) <= 18: avert(f"{nom} › quiz", f"{len(qz)} questions (≈ 15 attendues)")
    types = {q.get("type") for q in qz}
    if len(types) < 4: avert(f"{nom} › quiz", f"peu de types différents : {types}")
    for i, q in enumerate(qz): verifier_question(f"{nom} › quiz q{i}", q)

# --- glossaire ---
if gloss:
    vus = {}
    for k, v in gloss["termes"].items():
        if k.lower() in vus: err(f"glossaire › {k}", f"doublon (insensible à la casse) avec « {vus[k.lower()]} »")
        vus[k.lower()] = k
        if not v.get("def"): err(f"glossaire › {k}", "définition manquante")
        if not 1 <= v.get("niveau", 1) <= 6: err(f"glossaire › {k}", f"niveau {v.get('niveau')} hors 1–6")
        for r in v.get("voir") or []:
            if r.lower() not in TERMES: err(f"glossaire › {k}", f"« voir » vers un terme inconnu : {r}")
            elif r.lower() == k.lower(): err(f"glossaire › {k}", "renvoie vers lui-même")

# --- étiquettes ---
if etiq:
    vus = set()
    for e in etiq["etiquettes"]:
        lieu = f"etiquettes › {e.get('id')}"
        if e["id"] in vus: err(lieu, "id en double")
        vus.add(e["id"])
        if e.get("modele") not in MODELES: err(lieu, f"modèle inconnu : {e.get('modele')}")
        if e.get("teinte") not in TEINTES: err(lieu, f"teinte inconnue : {e.get('teinte')}")
        for k in e.get("champs", {}):
            if k not in CHAMPS: err(lieu, f"champ inconnu : {k}")
        for k in ("producteur", "appellation", "degre", "volume"):
            if not e.get("champs", {}).get(k): err(lieu, f"champ obligatoire absent : {k}")
        if e.get("region") == "hors-france":
            if not e.get("pays"): err(lieu, "hors-france sans pays")
            elif e["pays"] not in PAYS_PROPOSES: err(lieu, f"pays « {e['pays']} » absent des choix proposés par le jeu {PAYS_PROPOSES} : question insoluble")
            elif e["pays"][0].lower() in "aeiouéèêh": avert(lieu, f"« Produit du {e['pays']} » : élision attendue (« d'{e['pays']} »)")
        elif e.get("region") not in REGIONS: err(lieu, f"région inconnue : {e.get('region')}")
        if e.get("style") not in STYLES: err(lieu, f"style hors de STYLES : {e.get('style')}")
        for k in ("cepages", "note"):
            if not e.get(k): err(lieu, f"{k} manquant")
        if e.get("modele") and e.get("modele") in MODELES:
            ordre = re.search(rf"^\s*{e['modele']}\s*:\s*\[([^\]]*)\]", bloc("const LBL_ORDER = {"), re.M).group(1)
            affiches = set(re.findall(r'"(\w+)"', ordre)) | {"degre", "volume"}
            for k in e.get("champs", {}):
                if k not in affiches: err(lieu, f"le champ « {k} » n'est pas affiché par le modèle {e['modele']} (il ne pourra pas être touché)")

# --- carte ---
def anneaux(d):
    for seg in re.findall(r"M([^MZ]+)Z", d):
        pts = [tuple(map(float, p.split(","))) for p in seg.split()]
        if len(pts) >= 3: yield pts
def dedans(x, y, d):
    inside = False
    for pts in anneaux(d):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: inside = not inside
    return inside
COS = math.cos(math.radians(46.5))
proj = lambda lat, lon: ((lon - 2.5) * COS * 100, (46.5 - lat) * 100)
def km(a, b):
    r = math.pi / 180; x = math.sin((b[0]-a[0])*r/2)**2 + math.cos(a[0]*r)*math.cos(b[0]*r)*math.sin((b[1]-a[1])*r/2)**2
    return 2 * 6371 * math.asin(math.sqrt(x))
def departement(lat, lon):
    x, y = proj(lat, lon)
    return [c for c, v in france["deps"].items() if dedans(x, y, v["d"])]

if carte and france:
    ids = [p["id"] for p in carte["paliers"]]
    if ids != [1, 2, 3, 4, 5]: err("carte-vins › paliers", f"ids {ids} (1 à 5 attendus)")
    for p in carte["paliers"]:
        if not (p.get("echelleKm", 0) > 0 and p.get("plein", -1) >= 0): err(f"palier {p.get('id')}", "echelleKm/plein invalides")
        n = sum(1 for v in carte["vins"] if v["palier"] == p["id"])
        if n < 5: err(f"palier {p['id']}", f"seulement {n} vins : une partie compte 5 manches")
    attribution = {}
    for r in carte["regions"]:
        if r["id"] not in COULEURS_REGIONS: err(f"région {r['id']}", "pas de couleur dans REGION_COLORS (index.html)")
        for d in r["deps"]:
            if d not in france["deps"]: err(f"région {r['id']}", f"département {d} absent du fond de carte")
            attribution.setdefault(d, []).append(r["id"])
        for a in r["ancres"]:
            if not (41 <= a[0] <= 51.2 and -5.5 <= a[1] <= 9.7): err(f"région {r['id']}", f"ancre hors de France : {a}")
        if not r.get("fiche"): err(f"région {r['id']}", "fiche manquante")
    for d, rs in attribution.items():
        if len(rs) > 1: avert(f"département {d}", f"partagé entre {rs} : la coloration et le clic « dans la région » le donnent à {rs[0]}")
    vus = {}
    for i, v in enumerate(carte["vins"]):
        lieu = f"carte-vins › vins[{i}] « {v.get('vin')} » (palier {v.get('palier')})"
        if v.get("region") not in REGIONS: err(lieu, f"région inconnue : {v.get('region')}"); continue
        if v.get("palier") not in ids: err(lieu, "palier inconnu")
        if not (isinstance(v.get("lat"), (int, float)) and isinstance(v.get("lon"), (int, float))): err(lieu, "coordonnées manquantes"); continue
        k = (v["palier"], v["vin"])
        if k in vus: err(lieu, "vin en double dans le même palier")
        vus[k] = i
        deps = departement(v["lat"], v["lon"])
        if not deps: err(lieu, f"le point ({v['lat']}, {v['lon']}) tombe hors du fond de carte (mer ?)"); continue
        reg = REGIONS[v["region"]]
        dans_deps = any(d in reg["deps"] for d in deps)
        compte = any(attribution.get(d, [None])[0] == v["region"] for d in deps)
        if v["palier"] == 1 and not compte:
            dmin = min(km(a, (v["lat"], v["lon"])) for a in reg["ancres"])
            (err if dmin > 15 else avert)(lieu, f"hors de sa région dans le jeu : département {deps} " + ("non rattaché à la région" if not dans_deps else f"attribué à {attribution[deps[0]][0]}") + f" ; ancre la plus proche à {dmin:.1f} km (tolérance pleine : {carte['paliers'][0]['plein']} km)")
        elif not dans_deps:
            avert(lieu, f"département {deps} hors des départements de la région {v['region']} {reg['deps']}")
    for v in carte.get("villes", []):
        if not departement(v["lat"], v["lon"]): err(f"ville {v['nom']}", "hors du fond de carte")

print(f"Contenu vérifié : {len(ILLUS)} illustrations, {len(TERMES)} termes, {len(ETIQ)} étiquettes, {len(REGIONS)} régions, {len((carte or {}).get('vins', []))} vins.")
for e in erreurs: print("✗", e)
for a in avertissements: print("⚠", a)
print(f"\n{len(erreurs)} erreur(s), {len(avertissements)} avertissement(s).")
sys.exit(1 if erreurs else 0)
