#!/usr/bin/env python3
"""Fabrique le paquet SCORM 2004 (4e édition) de Pampre pour un LMS (testé pour 360Learning) :
dist/pampre-scorm2004.zip, fichiers à la racine du zip (pas de dossier intermédiaire).

  python3 tools/build-scorm.py                 # « terminé / réussi » quand les 6 niveaux sont validés
  python3 tools/build-scorm.py --niveaux 3     # … dès les niveaux 1 à 3 validés

Le paquet contient index.html (adapté), content/, scorm.js (adaptateur, voir scorm/scorm.js),
les polices en local (polices/, aucune ressource externe) et imsmanifest.xml. Pas de service worker
ni d'invitation à installer l'appli. Les polices Google Fonts sont téléchargées une fois dans sources/polices/.
À relancer après chaque modification du contenu, puis réimporter le zip dans le LMS.
"""
import argparse, datetime, glob, json, os, re, subprocess, sys, urllib.request, zipfile
from xml.sax.saxutils import escape

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RACINE)
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--niveaux", type=int, default=6, choices=range(1, 7), help="niveaux à valider pour réussir (1 à N), 6 par défaut")
ap.add_argument("--sortie", default="dist/pampre-scorm2004.zip")
args = ap.parse_args()

# ---- polices en local (Google Fonts → woff2, sous-ensembles latin et latin-ext seulement) ----
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36"   # pour obtenir du woff2
html = open("index.html", encoding="utf-8").read()
m = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/css2\?[^"]+)">', html)
assert m, "lien Google Fonts introuvable dans index.html"
cache = "sources/polices"; os.makedirs(cache, exist_ok=True)
def telecharger(url, dest):
    if not os.path.exists(dest):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f: f.write(r.read())
    return dest
css = open(telecharger(m.group(1).replace("&amp;", "&"), f"{cache}/google.css"), encoding="utf-8").read()
blocs = re.findall(r"/\* ([\w-]+) \*/\s*(@font-face\s*\{[^}]+\})", css)
polices, css_local = {}, []
for sous_ensemble, bloc in blocs:
    if sous_ensemble not in ("latin", "latin-ext"): continue
    url = re.search(r"url\((https://[^)]+\.woff2)\)", bloc).group(1)
    nom = polices.setdefault(url, f"p{len(polices) + 1:02d}.woff2")
    telecharger(url, f"{cache}/{nom}")
    css_local.append(f"/* {sous_ensemble} */\n" + bloc.replace(url, nom))
assert polices, "aucune police latin trouvée dans la feuille Google Fonts"
css_local = "/* Baloo 2, Nunito, Cormorant Garamond — SIL Open Font License 1.1 (Google Fonts) */\n" + "\n".join(css_local) + "\n"

# ---- index.html adapté au LMS ----
def remplacer(txt, avant, apres, n=1):
    assert txt.count(avant) == n, f"motif attendu {n} fois dans index.html : {avant[:70]}"
    return txt.replace(avant, apres)
html = re.sub(r'<link rel="preconnect" href="https://fonts\.(googleapis|gstatic)\.com"( crossorigin)?>\n', "", html)
html = remplacer(html, m.group(0), '<link rel="stylesheet" href="polices/polices.css">')
html = re.sub(r'<link rel="(manifest|apple-touch-icon)" href="[^"]+">\n', "", html)
html = remplacer(html, "<body>\n", "<body>\n<script src=\"scorm.js\"></script>\n")
html = remplacer(html, 'if (!LMS && "serviceWorker" in navigator', 'if (false && "serviceWorker" in navigator')   # pas de service worker dans le paquet
assert "fonts.googleapis" not in html and "fonts.gstatic" not in html

scorm_js = open("scorm/scorm.js", encoding="utf-8").read()
scorm_js = remplacer(scorm_js, "const CONFIG = { niveauxRequis: 6 };", f"const CONFIG = {{ niveauxRequis: {args.niveaux} }};")

# ---- fichiers du paquet ----
contenu = sorted(glob.glob("content/*.json"))
niveaux = json.load(open("content/niveaux.json", encoding="utf-8"))
for n in niveaux["niveaux"]:
    if n.get("contenu"): assert n["contenu"] in contenu, n["contenu"]
fichiers = {"index.html": html.encode(), "scorm.js": scorm_js.encode(), "polices/polices.css": css_local.encode()}
for f in contenu: fichiers[f] = open(f, "rb").read()
for url, nom in polices.items(): fichiers[f"polices/{nom}"] = open(f"{cache}/{nom}", "rb").read()

try: version = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "local"
except Exception: version = "local"
jour = datetime.date.today().isoformat()
titre = "Pampre — apprendre le vin en jouant"
reussite = "les 6 niveaux validés" if args.niveaux == 6 else f"niveaux 1 à {args.niveaux} validés"
manifeste = f'''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="pampre-vin" version="{jour}"
  xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3"
  xmlns:adlseq="http://www.adlnet.org/xsd/adlseq_v1p3"
  xmlns:adlnav="http://www.adlnet.org/xsd/adlnav_v1p3"
  xmlns:imsss="http://www.imsglobal.org/xsd/imsss">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>2004 4th Edition</schemaversion>
  </metadata>
  <!-- version {escape(version)} du {jour} ; réussite : {escape(reussite)} -->
  <organizations default="pampre-org">
    <organization identifier="pampre-org">
      <title>{escape(titre)}</title>
      <item identifier="pampre-item" identifierref="pampre-res">
        <title>{escape(titre)}</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="pampre-res" type="webcontent" adlcp:scormType="sco" href="index.html">
{chr(10).join(f'      <file href="{escape(f)}"/>' for f in fichiers)}
    </resource>
  </resources>
</manifest>
'''
fichiers = {"imsmanifest.xml": manifeste.encode(), **fichiers}

os.makedirs(os.path.dirname(args.sortie) or ".", exist_ok=True)
with zipfile.ZipFile(args.sortie, "w", zipfile.ZIP_DEFLATED) as z:
    for nom, data in fichiers.items(): z.writestr(nom, data)
taille = os.path.getsize(args.sortie)
print(f"{args.sortie} : {len(fichiers)} fichiers, {taille / 1e6:.1f} Mo (version {version}, réussite : {reussite})")
