#!/usr/bin/env python3
"""Teste le paquet SCORM 2004 dans un faux LMS (API_1484_11 simulée dans la page parente, comme 360Learning).

  python3 tools/test-scorm.py

Construit le paquet (tools/build-scorm.py), le décompresse dans un dossier temporaire servi sur le port 8766,
puis vérifie : initialisation, aucune ressource externe ni invitation à installer, reprise de la progression,
terminaison (cmi.exit, durée), statut « terminé + réussi », score, objectifs, pas de retour en arrière,
taille de cmi.suspend_data, réglage --niveaux, et fonctionnement hors LMS.
"""
import json, os, re, subprocess, sys, tempfile, threading, zipfile, functools, http.server
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'   # Chromium préinstallé (environnement cloud), sinon celui de Playwright
PORT = 8766

FAUX_LMS = """<!doctype html><meta charset="utf-8"><title>Faux LMS</title><link rel="icon" href="data:,">
<style>body{margin:0}iframe{border:0;width:100vw;height:100vh}</style>
<script>
// Données « côté serveur » : gardées dans le localStorage du faux LMS (clé faux-lms) à chaque Commit.
let donnees = JSON.parse(localStorage.getItem("faux-lms") || "{}");
window.journal = [];
const ok = "true";
window.API_1484_11 = {
  Initialize(){ journal.push(["Initialize"]); donnees["cmi.learner_id"] ??= "apprenant-42"; return ok; },
  GetValue(k){ return donnees[k] ?? ""; },
  SetValue(k, v){ journal.push(["SetValue", k, v.length > 80 ? v.length + " car." : v]);
    if (k === "cmi.suspend_data" && v.length > 64000) return "false";
    donnees[k] = v; return ok; },
  Commit(){ journal.push(["Commit"]); localStorage.setItem("faux-lms", JSON.stringify(donnees)); return ok; },
  Terminate(){ journal.push(["Terminate"]); localStorage.setItem("faux-lms", JSON.stringify(donnees)); return ok; },
  GetLastError(){ return "0"; }, GetErrorString(){ return ""; }, GetDiagnostic(){ return ""; }
};
window.donneesLMS = () => donnees;
</script>
<iframe src="pkg/index.html" title="Pampre"></iframe>"""

def construire(dest, niveaux):
    z = os.path.join(dest, f"pampre-{niveaux}.zip")
    subprocess.run([sys.executable, "tools/build-scorm.py", "--niveaux", str(niveaux), "--sortie", z], cwd=RACINE, check=True, capture_output=True)
    pkg = os.path.join(dest, f"lms{niveaux}", "pkg")
    with zipfile.ZipFile(z) as f:
        noms = f.namelist()
        assert "imsmanifest.xml" in noms and "index.html" in noms and not any(n.startswith("/") or n.split("/")[0] in ("pampre", "dist") for n in noms), "fichiers à la racine du zip"
        f.extractall(pkg)
    open(os.path.join(dest, f"lms{niveaux}", "lms.html"), "w").write(FAUX_LMS)

problemes = []
def verifier(cond, msg):
    print(("ok    " if cond else "ÉCHEC ") + msg)
    if not cond: problemes.append(msg)

with tempfile.TemporaryDirectory() as tmp:
    construire(tmp, 6); construire(tmp, 2)
    class Silencieux(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Silencieux, directory=tmp))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}"

    with sync_playwright() as p:
        nav = p.chromium.launch(**({'executable_path': CHROME} if os.path.exists(CHROME) else {}))
        iphone = dict(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",
                      viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        ctx = nav.new_context(**iphone); page = ctx.new_page()
        externes, erreurs = [], []
        page.on("request", lambda r: not r.url.startswith(base) and not r.url.startswith("data:") and externes.append(r.url))
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.on("console", lambda m: m.type == "error" and erreurs.append(m.text))

        def lancer(url=f"{base}/lms6/lms.html"):
            page.goto(url)
            fr = page.frame(url=re.compile(r"pkg/index\.html"))
            fr.wait_for_selector(".unit")
            return fr
        d = lambda: page.evaluate("donneesLMS()")
        journal = lambda: page.evaluate("journal")

        # 1. premier lancement
        fr = lancer()
        verifier(journal()[0] == ["Initialize"], "Initialize appelé en premier")
        verifier(d().get("cmi.completion_status") == "incomplete", "statut « incomplete » au premier lancement")
        verifier(fr.evaluate("!!window.LMS && LMS.cle") == "pampre-scorm-apprenant-42", "copie locale propre à l'apprenant")
        fr.evaluate("gainXP(15)")
        donnees = d()
        verifier(json.loads(donnees.get("cmi.suspend_data", "{}")).get("xp") == 15, "XP enregistrés dans cmi.suspend_data")
        verifier(fr.locator(".daily.installer").count() == 0, "pas de bandeau d'installation (iPhone, XP > 0)")
        fr.locator(".tab[data-go=profil]").click()
        verifier(fr.locator("text=Appli sur l'écran d'accueil").count() == 0, "pas de section d'installation dans Profil")
        verifier(fr.evaluate("navigator.serviceWorker.getRegistration().then(r => !r)"), "aucun service worker")
        verifier(fr.evaluate("Promise.all(['Nunito', 'Baloo 2', 'Cormorant Garamond'].map(f => document.fonts.load(`700 16px \"${f}\"`))).then(r => r.every(l => l.length > 0))"), "polices chargées depuis le paquet")
        page.wait_for_timeout(3500)
        verifier(["Commit"] in journal(), "Commit regroupé quelques secondes après la sauvegarde")

        # 2. fermeture puis reprise
        page.goto("about:blank")
        fr = lancer()
        ancien = json.loads(page.evaluate("localStorage.getItem('faux-lms')"))
        verifier(ancien.get("cmi.exit") == "suspend" and re.fullmatch(r"PT\d+H\d+M\d+S", ancien.get("cmi.session_time", "")), "Terminate : cmi.exit = suspend, durée de session")
        verifier(fr.evaluate("ST.xp") == 15, "progression reprise au lancement suivant")

        # 3. niveaux validés → terminé, réussi, score
        fr.evaluate("for (let n = 1; n <= 5; n++) ST.quiz[n] = { best: 90, passed: true }; save()")
        verifier(d().get("cmi.completion_status") == "incomplete", "5 niveaux sur 6 : encore « incomplete »")
        verifier(d().get("cmi.score.raw") == "75", f"score = moyenne des meilleurs quiz (450/6 = 75) : {d().get('cmi.score.raw')}")
        n_commits = journal().count(["Commit"])
        fr.evaluate("ST.quiz[6] = { best: 84, passed: true }; save()")
        donnees = d()
        verifier(donnees.get("cmi.completion_status") == "completed" and donnees.get("cmi.success_status") == "passed", "6 niveaux : « completed » + « passed »")
        verifier(donnees.get("cmi.score.raw") == "89" and donnees.get("cmi.score.scaled") == "0.8900" and donnees.get("cmi.progress_measure") == "1", "score 89 %, score.scaled 0.89, progression 1")
        verifier(journal().count(["Commit"]) == n_commits + 1, "réussite transmise tout de suite (Commit immédiat)")
        verifier([donnees.get(f"cmi.objectives.{i}.id") for i in range(6)] == [f"niveau-{n}" for n in range(1, 7)] and donnees.get("cmi.objectives.5.success_status") == "passed", "un objectif par niveau")

        # 4. « Tout effacer » : pas de retour en arrière côté LMS
        fr.evaluate("ST = freshState(); save()")
        donnees = d()
        verifier(donnees.get("cmi.completion_status") == "completed" and donnees.get("cmi.score.raw") == "89", "après « Tout effacer » : toujours terminé, score conservé")

        # 5. très long historique : cmi.suspend_data tient dans 64 000 caractères
        fr.evaluate("""() => { ST.xp = 99999; for (let i = 0; i < 1500; i++) { const j = todayStr(new Date(Date.now() - i * 864e5));
          ST.days[j] = 40; ST.daily[j] = 6; ST.carteJour[j] = { s: 17345, m: 21000, r: [5000, 4210, 3120, 2500, 4999] }; } save(); }""")
        sd = d().get("cmi.suspend_data", "")
        garde = json.loads(sd) if sd else {}
        verifier(0 < len(sd) <= 64000 and garde.get("xp") == 99999 and fr.evaluate("todayStr()") in garde.get("daily", {}),
                 f"historique de 1 500 jours compacté à {len(sd)} caractères (XP et jours récents gardés)")

        verifier(not externes, f"aucune requête externe {externes[:3]}")
        verifier(not erreurs, f"aucune erreur JS {erreurs[:3]}")
        ctx.close()

        # 6. réglage --niveaux 2
        ctx = nav.new_context(); page = ctx.new_page()
        fr = lancer(f"{base}/lms2/lms.html")
        fr.evaluate("ST.quiz[1] = { best: 80, passed: true }; ST.quiz[2] = { best: 100, passed: true }; save()")
        verifier(d().get("cmi.completion_status") == "completed" and d().get("cmi.score.raw") == "90", "--niveaux 2 : réussi avec les niveaux 1 et 2 (score 90)")
        ctx.close()

        # 7. paquet ouvert hors LMS : le jeu fonctionne normalement
        ctx = nav.new_context(); page = ctx.new_page()
        page.goto(f"{base}/lms6/pkg/index.html"); page.wait_for_selector(".unit")
        verifier(page.evaluate("window.LMS === undefined && LMS === null"), "hors LMS : pas d'adaptateur actif, jeu normal")
        ctx.close()
        nav.close()
    srv.shutdown()

print(f"\n{len(problemes)} problème(s)" if problemes else "\nok")
sys.exit(1 if problemes else 0)
