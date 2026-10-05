#!/usr/bin/env python3
"""Audit de Pampre : parcourt toute l'appli dans plusieurs navigateurs, largeurs, thèmes et
états de joueur, lance des vérifications automatiques et prend des captures.

Usage (depuis la racine du projet) :
    python3 tools/audit.py                      # audit visuel Chromium, captures clés
    python3 tools/audit.py --navigateurs chromium,webkit
    python3 tools/audit.py --ecrans accueil,carte --largeurs 320,375
    python3 tools/audit.py --captures toutes    # une capture par configuration (lourd)
    python3 tools/audit.py --sans-polices       # bloque Google Fonts
    python3 tools/audit.py --mouvement-reduit   # prefers-reduced-motion: reduce
    python3 tools/audit.py --fonctionnel        # tests fonctionnels (progression, série, défi…)

Sorties : audit/captures/*.png, audit/resultats.json (tous les constats), audit/resume.md.

Navigateurs : Chromium et Firefox via Playwright ; WebKit via Playwright si son navigateur
est installé, sinon via WebKitGTK (paquet webkit2gtk-driver + Selenium, sous Xvfb),
dans une iframe à la largeur voulue (tools/audit-cadre.html).
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
URL = "http://localhost:8765/"
CHECKS_JS = (RACINE / "tools" / "audit-checks.js").read_text(encoding="utf-8")
SAVE_KEY = "pampre-sauvegarde-v1"

LARGEURS = [320, 375, 400, 768, 1280, 1920]
HAUTEURS = {320: 568, 375: 667, 400: 800, 768: 1024, 1280: 800, 1920: 1080}
# thème : (prefers-color-scheme du système, data-theme forcé)
THEMES = {"clair": ("light", None), "sombre-systeme": ("dark", None), "sombre-force": ("light", "dark"), "clair-force": ("dark", "light")}


# ------------------------------------------------------------------ états du joueur
def jour(delta=0):
    return (datetime.date.today() + datetime.timedelta(days=delta)).isoformat()

def etat(nom):
    t = jour()
    base = {"v": 1, "xp": 0, "streak": {"count": 0, "last": None}, "days": {}, "done": {}, "quiz": {}, "games": {}, "badges": {},
            "mistakes": [], "daily": {}, "map": {"games": 0, "best": {}, "regions": {}}, "gloss": {}, "theme": None}
    if nom == "nouveau":
        return None
    if nom == "milieu":
        base.update(xp=64, streak={"count": 1, "last": t}, days={t: 64}, done={"n1-l1": t, "n1-l2": t}, badges={"premier-verre": t},
                    mistakes=["n1-l2-v0"])
    elif nom == "valide":
        done = {k: t for k in ["n1-l1", "n1-l2", "n1-l3", "jeu:lis-etiquette", "n1-l4", "jeu:bons-gestes"]}
        base.update(xp=420, streak={"count": 4, "last": t}, days={jour(-i): 60 + 20 * i for i in range(4)}, done=done,
                    quiz={"1": {"best": 87, "passed": True}}, games={"lis-etiquette": 8, "bons-gestes": 6},
                    badges={b: t for b in ["premier-verre", "niveau-1", "serie-3", "lecteur", "gestes"]})
    elif nom == "veteran":
        badges = ["premier-verre", "lecteur", "gestes", "niveau-1", "sans-faute", "serie-3", "serie-7", "serie-30", "explorateur",
                  "oeil-de-lynx", "tour-de-france", "expert-carte", "lexique", "defi"]
        regions = ["bordeaux", "bourgogne", "beaujolais", "champagne", "alsace", "loire", "rhone", "languedoc-roussillon", "provence",
                   "sud-ouest", "jura", "savoie", "corse"]
        done = {k: t for k in ["n1-l1", "n1-l2", "n1-l3", "jeu:lis-etiquette", "n1-l4", "jeu:bons-gestes"]}
        base.update(xp=123456, streak={"count": 365, "last": t}, days={jour(-i): 1000 + 937 * i for i in range(7)}, done=done,
                    quiz={"1": {"best": 100, "passed": True}}, games={"lis-etiquette": 10, "bons-gestes": 6},
                    badges={b: t for b in badges}, daily={jour(-i): 6 for i in range(1, 30)},
                    map={"games": 4242, "best": {"1": 25000, "2": 24890, "3": 23456, "4": 21000, "5": 19999}, "regions": {r: 1 for r in regions}, "lastTier": 5},
                    gloss={"acidité": 1})
    elif nom == "erreurs":
        ids = [f"n1-l{l}-v{i}" for l in range(1, 5) for i in range(2)] + [f"bons-gestes-{i}" for i in range(6)] + [f"quiz1-{i}" for i in range(15)]
        ids += [f"ancien-{i}" for i in range(60 - len(ids))]   # ids d'une ancienne version du contenu
        base.update(xp=180, streak={"count": 2, "last": jour(-1)}, done={"n1-l1": t, "n1-l2": t, "n1-l3": t}, mistakes=ids)
    return base


# ------------------------------------------------------------------ écrans
# Chaque écran : état du joueur + étapes JS. "wait:ms" attend, "pick:..." place l'épingle de la carte.
def q_js(expr):
    """Ouvre une session d'une seule question (expression JS donnant l'objet question)."""
    return f"runSession([{{kind:'q', q:{expr}}}], {{title:'Audit', onEnd:() => ({{title:'Fin', xp:0}})}})"

QUIZ = "LEVELS[1].quiz.questions"
GESTES = "LEVELS[1].jeux[1].questions"
TYPES = {   # un exemple réel de chaque type (le plus long quand il y a le choix)
    "qcm": f"{QUIZ}[11]", "vf": f"{QUIZ}[12]", "ordre": f"LEVELS[1].lecons[3].verif[0]", "assoc": f"{GESTES}[1]",
    "tri": f"{GESTES}[0]", "tri2": f"{QUIZ}[9]", "etiquette-qcm": f"{QUIZ}[14]", "etiquette-toucher": f"{QUIZ}[6]", "indices": f"{QUIZ}[10]",
}

def ecrans():
    E = []
    def add(nom, st, *steps, groupe="vue", ciblee=True):
        E.append({"nom": nom, "etat": st, "steps": list(steps), "groupe": groupe})
    # vues principales, pour chaque état de joueur
    for st in ["nouveau", "milieu", "valide", "veteran", "erreurs"]:
        add(f"accueil-{st}", st, "go('home')")
        add(f"profil-{st}", st, "go('profil')")
        add(f"defi-{st}", st, "go('defi')")
    add("carte-reglages", "milieu", "go('carte')")
    for t in range(1, 6):
        add(f"carte-palier{t}-manche", "milieu", "go('carte')", f"document.querySelector('.tier[data-t=\"{t}\"]').click()",
            "[...document.querySelectorAll('main .btn')].find(b=>/Lancer/.test(b.textContent)).click()", "wait:300")
        add(f"carte-palier{t}-revelation", "milieu", "go('carte')", f"document.querySelector('.tier[data-t=\"{t}\"]').click()",
            "[...document.querySelectorAll('main .btn')].find(b=>/Lancer/.test(b.textContent)).click()", "wait:300", "pick:verite+30", "wait:200",
            "[...document.querySelectorAll('main .btn')].find(b=>/Valider/.test(b.textContent)).click()", "wait:900")
    add("carte-bilan", "milieu", "go('carte')", "[...document.querySelectorAll('main .btn')].find(b=>/Lancer/.test(b.textContent)).click()", "wait:300",
        *(["pick:verite+60", "wait:100", "[...document.querySelectorAll('main .btn')].find(b=>/Valider/.test(b.textContent)).click()", "wait:300",
           "[...document.querySelectorAll('main .btn')].find(b=>/suivante|bilan/.test(b.textContent)).click()", "wait:300"] * 5), "wait:500")
    add("carte-abandon", "milieu", "go('carte')", "[...document.querySelectorAll('main .btn')].find(b=>/Lancer/.test(b.textContent)).click()", "wait:300",
        "document.querySelector('main .linkbtn').click()", "wait:300")
    add("profil-import-ok", "milieu", "go('profil')", f"document.querySelector('#save-in').value = btoa(unescape(encodeURIComponent(JSON.stringify({json.dumps(etat('valide'))}))))",
        "document.querySelector('[data-a=import]').click()", "wait:200")
    add("profil-import-ko", "milieu", "go('profil')", "document.querySelector('#save-in').value = 'pas un code'", "document.querySelector('[data-a=import]').click()", "wait:100")
    add("profil-effacer", "milieu", "go('profil')", "document.querySelector('[data-a=reset]').click()", "wait:300")
    add("glossaire", "milieu", "openGlossary()", "wait:300")
    add("glossaire-recherche-sans-accent", "milieu", "openGlossary()", "wait:200", "(e=>{e.value='elevage';e.dispatchEvent(new Event('input'))})(document.querySelector('#gl-search'))", "wait:100")
    add("glossaire-recherche-vide", "milieu", "openGlossary()", "wait:200", "(e=>{e.value='zzzz';e.dispatchEvent(new Event('input'))})(document.querySelector('#gl-search'))", "wait:100")
    add("glossaire-voir-aussi", "milieu", "openGlossary('AOP')", "wait:300", "document.querySelector('.term.focus .see .gl').click()", "wait:600")
    # leçons, carte par carte (+ les 2 questions de vérification)
    for li in range(4):
        nb = [5, 6, 5, 5][li]
        for c in range(nb):
            add(f"lecon{li+1}-carte{c+1}", "milieu", f"startStep(1, LEVELS[1].lecons[{li}].id)", "wait:100",
                *(["document.querySelector('.session [data-next]').click()", "wait:60"] * c), "wait:450", groupe="session")
    # chaque type de question : avant, juste, faux
    for nom, expr in TYPES.items():
        add(f"q-{nom}-avant", "milieu", q_js(expr), "wait:450", groupe="session")
        add(f"q-{nom}-juste", "milieu", q_js(expr), "wait:200", "AUDIT.answer(true)", "document.querySelector('[data-check]').click()", "wait:450", groupe="session")
        add(f"q-{nom}-faux", "milieu", q_js(expr), "wait:200", "AUDIT.answer(false)", "document.querySelector('[data-check]').click()", "wait:450", groupe="session")
    add("q-carte-avant", "milieu", q_js("{type:'carte', id:'map-x', question:'Où est produit ce vin ? Touche la carte.', entry:D.carteVins.vins[22], explication:''}"), "wait:450", groupe="session")
    add("q-carte-faux", "milieu", q_js("{type:'carte', id:'map-x', question:'Où est produit ce vin ? Touche la carte.', entry:D.carteVins.vins[22], explication:''}"), "wait:300",
        "pick:paris", "wait:100", "document.querySelector('[data-check]').click()", "wait:800", groupe="session")
    # feuille de correction avec une explication très longue
    add("feuille-longue", "milieu", q_js(f"Object.assign({{}}, {QUIZ}[11], {{explication: ({QUIZ}[14].explication + ' ').repeat(4)}})"), "wait:100",
        "AUDIT.answer(false)", "document.querySelector('[data-check]').click()", "wait:450", groupe="session")
    # les 19 étiquettes
    E.extend({"nom": f"etiquette-{i:02d}", "etat": "milieu", "groupe": "etiquette", "steps": [
        q_js(f"{{type:'etiquette', etiquette:D.etiquettes.etiquettes[{i}].id, mode:'toucher', cible:'millesime', question:'Touche le millésime.', explication:'x'}}"), "wait:400"]}
        for i in range(19))
    # fins de session
    add("fin-lecon", "milieu", "startStep(1,'n1-l4')", "wait:100", "await AUDIT.playThrough(true)", "wait:600", groupe="session")
    add("fin-jeu", "valide", "startGame(1,'bons-gestes')", "wait:100", "await AUDIT.playThrough(i => i % 2 == 0)", "wait:600", groupe="session")
    add("fin-quiz-reussi", "milieu", "startQuiz(1)", "wait:100", "await AUDIT.playThrough(true)", "wait:700", groupe="session")
    add("fin-quiz-rate", "milieu", "startQuiz(1)", "wait:100", "await AUDIT.playThrough(false)", "wait:700", groupe="session")
    add("defi-session", "nouveau", "startDaily()", "wait:400", groupe="session")
    add("toasts-pendant-question", "milieu", q_js(f"{QUIZ}[11]"), "wait:100", "AUDIT.answer(true)",
        "toast(I.flame,'Série de 2 jours !','Reviens demain.');toast(I.star,'Nouveau rang : Amateur','100 XP');toast(I.medal,'Badge débloqué : Premier verre','Terminer ta première leçon')", "wait:300", groupe="session")
    add("modale-quitter", "milieu", q_js(f"{QUIZ}[0]"), "wait:100", "document.querySelector('[data-quit]').click()", "wait:350", groupe="session")
    add("confettis", "valide", "go('home')", "confetti()", "wait:900")
    return E


# ------------------------------------------------------------------ pilotes de navigateur
class PW:
    """Chromium / Firefox / WebKit via Playwright."""
    def __init__(self, nom, args):
        from playwright.sync_api import sync_playwright
        self.nom = nom; self.pw = sync_playwright().start()
        kw = {}
        if nom == "chromium" and os.path.exists("/opt/pw-browsers/chromium-1194/chrome-linux/chrome") and not args.chromium_bundle:
            kw["executable_path"] = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        self.b = getattr(self.pw, nom).launch(**kw)
        self.args = args; self.page = None; self.errs = []

    def ouvrir(self, st, w, scheme, touch=False):
        if self.page: self.page.context.close()
        ctx = self.b.new_context(viewport={"width": w, "height": HAUTEURS.get(w, 800)}, color_scheme=scheme, has_touch=touch, is_mobile=False,
                                 reduced_motion="reduce" if self.args.mouvement_reduit else "no-preference", locale="fr-FR", timezone_id="Europe/Paris")
        if self.args.sans_polices:
            ctx.route(re.compile(r"https://fonts\.(googleapis|gstatic)\.com/.*"), lambda r: r.abort())
        init = f"try{{localStorage.clear();" + (f"localStorage.setItem('{SAVE_KEY}', {json.dumps(json.dumps(st))});" if st else "") + "}catch(e){}"
        ctx.add_init_script("if (!sessionStorage.getItem('audit-init')) { sessionStorage.setItem('audit-init','1');" + init + "}")
        self.page = ctx.new_page(); self.errs = []
        self.page.on("pageerror", lambda e: self.errs.append(f"exception : {e}"))
        self.page.on("console", lambda m: m.type == "error" and self.errs.append(f"console : {m.text}"))
        self.page.goto(URL); self.page.wait_for_function("document.getElementById('topbar') || /pu être chargé/.test(document.body.textContent)", timeout=15000)
        self.page.evaluate(CHECKS_JS); self.page.evaluate("AUDIT.hook()")
        try: self.page.evaluate("document.fonts.ready")
        except Exception: pass

    def js(self, code):
        return self.page.evaluate(f"(async () => {{ {code} }})()")
    def taille(self, w):
        self.page.set_viewport_size({"width": w, "height": HAUTEURS.get(w, 800)})
    def theme(self, scheme, force):
        self.page.emulate_media(color_scheme=scheme)
        self.js(f"document.documentElement.{'setAttribute' if force else 'removeAttribute'}('data-theme'{', ' + json.dumps(force) if force else ''})")
    def clic(self, x, y):
        self.page.mouse.click(x, y)
    def capture(self, chemin, page_entiere=False):
        self.page.screenshot(path=str(chemin), full_page=page_entiere)
    def fermer(self):
        try: self.b.close(); self.pw.stop()
        except Exception: pass


class WK:
    """WebKitGTK (moteur de Safari) via WebKitWebDriver + Selenium, appli dans une iframe."""
    def __init__(self, nom, args, scheme="light"):
        self.nom = nom; self.args = args; self.scheme = scheme; self.errs = []; self.d = None
        if not os.environ.get("DISPLAY"):
            subprocess.Popen(["Xvfb", ":99", "-screen", "0", "2200x1400x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
            os.environ["DISPLAY"] = ":99"
        self._start()

    def _start(self):
        from selenium import webdriver
        from selenium.webdriver.webkitgtk.options import Options
        if self.d:
            try: self.d.quit()
            except Exception: pass
        if self.scheme == "dark": os.environ["GTK_THEME"] = "Adwaita:dark"
        else: os.environ.pop("GTK_THEME", None)
        self.d = webdriver.WebKitGTK(options=Options()); self.d.set_window_size(2000, 1300); self.d.set_script_timeout(60)
        self.d.get(URL + "tools/audit-cadre.html"); self.w = 375

    def ouvrir(self, st, w, scheme, touch=False):
        if scheme != self.scheme: self.scheme = scheme; self._start()
        d = self.d; d.switch_to.default_content()
        init = "localStorage.clear();" + (f"localStorage.setItem('{SAVE_KEY}', {json.dumps(json.dumps(st))});" if st else "")
        d.execute_script(init + f"const f=document.getElementById('app'); f.width={w}; f.height={HAUTEURS.get(w, 800)}; f.src='about:blank'; f.src='{URL}index.html?'+Date.now();")
        self.w = w; time.sleep(.3)
        d.switch_to.frame(d.find_element("id", "app"))
        for _ in range(60):
            if d.execute_script("return !!(document.getElementById('topbar') || /pu être chargé/.test(document.body && document.body.textContent))"): break
            time.sleep(.1)
        # iOS affiche des barres de défilement superposées : on masque celles de WebKitGTK qui mangent 15 px
        d.execute_script("const st = document.createElement('style'); st.textContent = '::-webkit-scrollbar{width:0;height:0}'; document.head.appendChild(st);")
        d.execute_script(CHECKS_JS + "; AUDIT.hook(); window.__errs = []; addEventListener('error', e => __errs.push('exception : ' + e.message)); addEventListener('unhandledrejection', e => __errs.push('promesse : ' + e.reason));")
        d.execute_async_script("document.fonts.ready.then(() => arguments[0]())")

    @property
    def errs(self):
        try: return self.d.execute_script("return window.__errs || []")
        except Exception: return []
    @errs.setter
    def errs(self, v): pass

    def js(self, code):
        return self.d.execute_async_script(f"const __cb = arguments[arguments.length-1]; (async () => {{ {code} }})().then(__cb, e => __cb('ERREUR ' + e))")
    def taille(self, w):
        d = self.d; d.switch_to.default_content(); d.execute_script(f"const f=document.getElementById('app'); f.width={w}; f.height={HAUTEURS.get(w, 800)};")
        self.w = w; d.switch_to.frame(d.find_element("id", "app")); time.sleep(.15)
    def theme(self, scheme, force):
        if scheme != self.scheme:  # changer le thème système demande de relancer WebKit : on recharge l'état courant
            raise RuntimeError("theme-systeme")
        self.js(f"document.documentElement.{'setAttribute' if force else 'removeAttribute'}('data-theme'{', ' + json.dumps(force) if force else ''})")
    def clic(self, x, y):
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        a = ActionBuilder(self.d); a.pointer_action.move_to_location(int(x), int(y)).click(); a.perform()
    def capture(self, chemin, page_entiere=False):
        # la capture d'élément d'une iframe sort noire sous Xvfb : on capture la fenêtre et on recadre
        from PIL import Image
        import io
        d = self.d; d.switch_to.default_content()
        im = Image.open(io.BytesIO(d.get_screenshot_as_png())); im.crop((0, 0, self.w, HAUTEURS.get(self.w, 800))).save(str(chemin))
        d.switch_to.frame(d.find_element("id", "app"))
    def fermer(self):
        try: self.d.quit()
        except Exception: pass


# ------------------------------------------------------------------ exécution
def jouer_etape(drv, step):
    if step.startswith("wait:"):
        time.sleep(int(step[5:]) / 1000); return
    if step.startswith("pick:"):
        cible = step[5:]
        # point écran de la vérité (+ décalage en px) ou d'une ville
        js = """const svg = document.querySelector('.session .map-box > svg') || document.querySelector('.map-box > svg');
          let lat, lon; const C = %s;
          if (C === 'paris') { lat = 48.857; lon = 2.352; } else { const e = window.__curQ?.entry || MAPGAME.rounds[MAPGAME.i]; lat = e.lat; lon = e.lon; }
          const [x, y] = proj(lat, lon); const pt = svg.createSVGPoint(); pt.x = x; pt.y = y; const q = pt.matrixTransform(svg.getScreenCTM());
          svg.scrollIntoView({block:'center'}); await new Promise(r => setTimeout(r, 50));
          const q2 = pt.matrixTransform(svg.getScreenCTM()); return [q2.x, q2.y];""" % json.dumps(cible.split("+")[0])
        x, y = drv.js(js)
        dx = int(cible.split("+")[1]) if "+" in cible else 0
        drv.clic(x + dx, y + dx * .6); return
    r = drv.js(step if step.startswith("await") or step.startswith("return") else f"return ({step});" if "\n" not in step and ";" not in step.strip().rstrip(";") else step)
    if isinstance(r, str) and r.startswith("ERREUR"):
        raise RuntimeError(f"{step[:60]} → {r}")


def preparer(drv, ecran, w, scheme):
    drv.ouvrir(etat(ecran["etat"]), w, scheme)
    for s in ecran["steps"]:
        jouer_etape(drv, s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--navigateurs", default="chromium")
    ap.add_argument("--largeurs", default=",".join(map(str, LARGEURS)))
    ap.add_argument("--themes", default=",".join(THEMES))
    ap.add_argument("--ecrans", default="", help="filtre : préfixes de noms d'écrans séparés par des virgules")
    ap.add_argument("--captures", choices=["cles", "toutes", "aucune"], default="cles")
    ap.add_argument("--cibles-tactiles", action="store_true", help="vérifie aussi les zones tactiles (< 44 px)")
    ap.add_argument("--sans-polices", action="store_true")
    ap.add_argument("--mouvement-reduit", action="store_true")
    ap.add_argument("--chromium-bundle", action="store_true", help="utilise le Chromium de Playwright plutôt que /opt/pw-browsers")
    ap.add_argument("--sortie", default="audit")
    ap.add_argument("--suffixe", default="", help="suffixe des fichiers resultats/resume (passes complémentaires)")
    ap.add_argument("--fonctionnel", action="store_true", help="lance les tests fonctionnels (tools/audit_fonctionnel.py)")
    args = ap.parse_args()

    serveur = None
    try: urllib.request.urlopen(URL, timeout=2)
    except Exception:
        serveur = subprocess.Popen([sys.executable, "-m", "http.server", "8765"], cwd=RACINE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)

    if args.fonctionnel:
        sys.path.insert(0, str(RACINE / "tools"))
        import audit_fonctionnel
        code = audit_fonctionnel.main(args)
        if serveur: serveur.terminate()
        sys.exit(code)

    out = RACINE / args.sortie; cap = out / "captures"; cap.mkdir(parents=True, exist_ok=True)
    largeurs = [int(x) for x in args.largeurs.split(",")]; themes = args.themes.split(",")
    filtres = [f for f in args.ecrans.split(",") if f]
    liste = [e for e in ecrans() if not filtres or any(e["nom"].startswith(f) for f in filtres)]
    suffixe = ("-sans-polices" if args.sans_polices else "") + ("-mouvement-reduit" if args.mouvement_reduit else "") + (f"-{args.suffixe}" if args.suffixe else "")
    resultats = []; erreurs_js = []; deja = set()

    for nav in args.navigateurs.split(","):
        # un passage par thème système (WebKitGTK doit être relancé pour changer de thème système)
        for scheme in ["light", "dark"]:
            ths = [t for t in themes if THEMES[t][0] == scheme]
            if not ths: continue
            drv = WK(nav, args, scheme) if nav == "webkit" and not _pw_webkit_ok() else PW(nav, args)
            print(f"== {nav} · système {scheme} · {len(liste)} écrans", flush=True)
            for ecran in liste:
                try:
                    preparer(drv, ecran, largeurs[0], scheme)
                except Exception as e:
                    resultats.append({"navigateur": nav, "ecran": ecran["nom"], "largeur": largeurs[0], "theme": ths[0], "check": "scenario-echoue", "sel": "", "text": "", "detail": str(e)[:300]})
                    print(f"  ! {ecran['nom']} : {str(e)[:200]}", flush=True); continue
                for w in largeurs:
                    drv.taille(w); time.sleep(.25)
                    for th in ths:
                        drv.theme(*THEMES[th]); time.sleep(.12)
                        try:
                            res = drv.js(f"return await AUDIT.run({{targets:{'true' if args.cibles_tactiles and w <= 768 else 'false'}}})")
                        except Exception as e:
                            res = [{"check": "audit-echoue", "sel": "", "text": "", "detail": str(e)[:200]}]
                        if isinstance(res, str): res = [{"check": "audit-echoue", "sel": "", "text": "", "detail": res[:300]}]
                        cle_cap = (ecran["groupe"] == "vue" and (w, th) in [(375, "clair"), (375, "sombre-systeme"), (320, "clair"), (1280, "clair")]) or \
                                  (ecran["groupe"] != "vue" and (w, th) in [(375, "clair"), (320, "sombre-systeme")])
                        nouveau = False
                        for r in res:
                            r.update(navigateur=nav, ecran=ecran["nom"], largeur=w, theme=th); resultats.append(r)
                            k = (nav, r["check"], r.get("sel"), r.get("text"))
                            if k not in deja: deja.add(k); nouveau = True
                        nom = f"{nav}-{ecran['nom']}-{w}-{th}{suffixe}.png"
                        if args.captures == "toutes" or (args.captures == "cles" and (cle_cap or nouveau)):
                            if nouveau and not cle_cap:  # entoure les éléments fautifs
                                drv.js("""document.querySelectorAll('*').forEach(e => { const s = AUDIT.sig(e); if (%s.includes(s)) e.style.outline = '3px solid red'; })""" % json.dumps([r.get("sel") for r in res]))
                            try: drv.capture(cap / nom, page_entiere=(ecran["groupe"] == "vue" and isinstance(drv, PW)))
                            except Exception as e: print("  capture impossible", nom, e)
                            if nouveau and not cle_cap:
                                drv.js("document.querySelectorAll('[style*=\"outline\"]').forEach(e => e.style.outline = '')")
                        for r in res:
                            r["capture"] = f"captures/{nom}" if (cap / nom).exists() else ""
                errs = list(drv.errs)
                for e in errs:
                    if args.sans_polices and "fonts.g" in e or "ERR_FAILED" in e and args.sans_polices: continue
                    erreurs_js.append({"navigateur": nav, "ecran": ecran["nom"], "erreur": e})
                print(f"  {ecran['nom']:<36} {sum(1 for r in resultats if r['ecran'] == ecran['nom'] and r['navigateur'] == nav):>4} constats", flush=True)
            drv.fermer()

    for e in erreurs_js:
        resultats.append({"navigateur": e["navigateur"], "ecran": e["ecran"], "largeur": 0, "theme": "", "check": "erreur-js", "sel": "", "text": "", "detail": e["erreur"]})
    nom_res = f"resultats{suffixe}.json"
    (out / nom_res).write_text(json.dumps(resultats, ensure_ascii=False, indent=1), encoding="utf-8")
    ecrire_resume(resultats, out / f"resume{suffixe}.md")
    print(f"\n{len(resultats)} constats bruts → {out / nom_res} ; résumé → {out / f'resume{suffixe}.md'}")
    if serveur: serveur.terminate()


def _pw_webkit_ok():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return os.path.exists(p.webkit.executable_path)
    except Exception:
        return False


def ecrire_resume(resultats, chemin):
    """Regroupe les constats identiques (même vérification, même élément, même texte)."""
    groupes = {}
    for r in resultats:
        k = (r["check"], r.get("sel", ""), r.get("text", ""))
        g = groupes.setdefault(k, {"n": 0, "ecrans": set(), "largeurs": set(), "themes": set(), "navs": set(), "detail": r.get("detail", ""), "capture": ""})
        g["n"] += 1; g["ecrans"].add(r["ecran"]); g["largeurs"].add(r.get("largeur")); g["themes"].add(r.get("theme")); g["navs"].add(r["navigateur"])
        if not g["capture"] and r.get("capture"): g["capture"] = r["capture"]
    lignes = ["# Résumé automatique de l'audit", "", f"{len(resultats)} constats bruts, {len(groupes)} groupes.", ""]
    for chk in sorted({k[0] for k in groupes}):
        lignes += [f"## {chk}", ""]
        for (c, sel, text), g in sorted(groupes.items(), key=lambda x: -x[1]["n"]):
            if c != chk: continue
            ecr = sorted(g["ecrans"]); ecr_s = ", ".join(ecr[:6]) + (f" … (+{len(ecr)-6})" if len(ecr) > 6 else "")
            lignes.append(f"- `{sel}` « {text} » — {g['detail']} — ×{g['n']} · {'/'.join(sorted(g['navs']))} · largeurs {sorted(x for x in g['largeurs'] if x)} · thèmes {sorted(t for t in g['themes'] if t)} · écrans : {ecr_s}" + (f" · [capture]({g['capture']})" if g["capture"] else ""))
        lignes.append("")
    chemin.write_text("\n".join(lignes), encoding="utf-8")


if __name__ == "__main__":
    main()
