"""Tests fonctionnels de Pampre, lancés par `python3 tools/audit.py --fonctionnel`.

Chaque test renvoie (statut, détail) avec statut ∈ {OK, BUG, INFO} et peut prendre des
captures de preuve dans audit/captures/preuve-*.png. Résultats : audit/fonctionnel.json.
Navigateur : Chromium (Playwright). Quelques tests sont rejoués sous WebKit (WebKitGTK)
avec --navigateurs chromium,webkit.
"""
import datetime, json, math, os, re, time, traceback
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
URL = "http://localhost:8765/"
CHECKS_JS = (RACINE / "tools" / "audit-checks.js").read_text(encoding="utf-8")
CAP = RACINE / "audit" / "captures"
KEY = "pampre-sauvegarde-v1"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
RESULTATS = []


def T(nom):
    def deco(f):
        f.nom = nom; TESTS.append(f); return f
    return deco
TESTS = []


class App:
    """Une page Pampre fraîche, avec un état de joueur et une heure éventuellement imposée."""
    def __init__(self, b, st=None, w=375, h=667, heure=None, tz="Europe/Paris", touch=False, init="", scheme="light", routes=None, reduced=False):
        self.ctx = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, timezone_id=tz, locale="fr-FR", color_scheme=scheme,
                                 reduced_motion="reduce" if reduced else "no-preference")
        if routes:
            for pat, fn in routes: self.ctx.route(pat, fn)
        seed = f"localStorage.setItem('{KEY}', {json.dumps(json.dumps(st))});" if st is not None else ""
        self.ctx.add_init_script("if(!sessionStorage.getItem('i')){sessionStorage.setItem('i',1);try{localStorage.clear();" + seed + "}catch(e){}}" + init)
        self.p = self.ctx.new_page(); self.errs = []
        self.p.on("pageerror", lambda e: self.errs.append(str(e)))
        self.p.on("console", lambda m: m.type == "error" and "favicon" not in m.text and "404" not in m.text and self.errs.append(m.text))
        if heure: self.p.clock.set_fixed_time(heure)
        self.p.goto(URL)
        self.p.wait_for_function("document.getElementById('topbar') || /pu être chargé/.test(document.body.textContent)", timeout=15000)
        self.p.evaluate(CHECKS_JS); self.p.evaluate("AUDIT.hook()")
    def js(self, code, arg=None):
        return self.p.evaluate(f"async (arg) => {{ {code} }}", arg)
    def st(self):
        return self.p.evaluate("JSON.parse(JSON.stringify(ST))")
    def toasts(self):
        return self.p.evaluate("[...document.querySelectorAll('.toast')].map(t=>t.textContent)")
    def shot(self, nom, full=False):
        self.p.screenshot(path=str(CAP / f"preuve-{nom}.png"), full_page=full); return f"captures/preuve-{nom}.png"
    def close(self):
        self.ctx.close()


def etat(**kw):
    base = {"v": 1, "xp": 0, "streak": {"count": 0, "last": None}, "days": {}, "done": {}, "quiz": {}, "games": {}, "badges": {},
            "mistakes": [], "daily": {}, "map": {"games": 0, "best": {}, "regions": {}}, "gloss": {}, "theme": None}
    base.update(kw); return base

def capter_toasts(app):
    """Enregistre tous les toasts créés (même ceux en file d'attente)."""
    app.js("window.__toasts = []; const o = toast; window.toast = (i, t, s) => { __toasts.push(t); return o(i, t, s); };")


# ===================================================================== progression
@T("Progression : déblocage des nœuds dans l'ordre")
def t_noeuds(b):
    a = App(b)
    etat0 = a.p.evaluate("[...document.querySelectorAll('.unit:first-of-type .node')].map(n => n.disabled)")
    a.js("startStep(1,'n1-l1')"); r = a.js("return await AUDIT.playThrough(true)"); a.p.click("[data-done]")
    etat1 = a.p.evaluate("[...document.querySelectorAll('.node')].slice(0,7).map(n => n.disabled)")
    a.close()
    ok = etat0[:7] == [False] + [True]*6 and etat1[:7] == [False, False] + [True]*5
    return ("OK" if ok else "BUG"), f"avant : {etat0[:7]}, après leçon 1 : {etat1[:7]} (disabled)"

@T("Progression : XP d'une leçon (première fois puis révision)")
def t_xp_lecon(b):
    a = App(b); capter_toasts(a)
    a.js("startStep(1,'n1-l1')"); a.js("return await AUDIT.playThrough(true)"); x1 = a.st()["xp"]; a.p.click("[data-done]")
    a.js("startStep(1,'n1-l1')"); a.js("return await AUDIT.playThrough(true)"); x2 = a.st()["xp"]; a.p.click("[data-done]")
    badges = [t for t in a.p.evaluate("__toasts") if t.startswith("Badge")]
    a.close()
    ok = x1 == 15 + 2*2 and x2 - x1 == 5 + 2*2 and badges.count("Badge débloqué : Premier verre") == 1
    return ("OK" if ok else "BUG"), f"1re fois +{x1} XP (attendu 19), révision +{x2-x1} (attendu 9), toasts de badge : {badges}"

@T("Progression : seuil de 80 % au quiz (11/15 refusé, 12/15 accepté)")
def t_seuil(b):
    out = []
    for n_bon in (11, 12):
        a = App(b, etat(done={k: "2026-01-01" for k in ["n1-l1", "n1-l2", "n1-l3", "jeu:lis-etiquette", "n1-l4", "jeu:bons-gestes"]}))
        a.js("startQuiz(1)")
        a.js(f"let k = 0; return await AUDIT.playThrough(() => k++ < {n_bon})")
        st = a.st(); a.p.click("[data-done]")
        lock2 = a.p.evaluate("document.querySelectorAll('.unit')[1].classList.contains('locked')")
        note = a.p.evaluate("document.querySelectorAll('.unit')[1].textContent")
        if n_bon == 12: a.shot("niveau2-debloque-vide")
        out.append((n_bon, st["quiz"].get("1"), lock2, "préparation" in note))
        a.close()
    ok = out[0][1]["passed"] is False and out[0][2] and out[1][1]["passed"] is True and not out[1][2] and out[1][3]
    return ("OK" if ok else "BUG"), f"{out}"

@T("Progression : bonus de 40 XP du quiz une seule fois ; badges une seule fois")
def t_quiz_xp(b):
    a = App(b, etat(done={k: "2026-01-01" for k in ["n1-l1", "n1-l2", "n1-l3", "jeu:lis-etiquette", "n1-l4", "jeu:bons-gestes"]})); capter_toasts(a)
    a.js("startQuiz(1)"); a.js("return await AUDIT.playThrough(true)"); x1 = a.st()["xp"]; a.p.click("[data-done]")
    a.js("startQuiz(1)"); a.js("return await AUDIT.playThrough(true)"); x2 = a.st()["xp"] - x1; a.p.click("[data-done]")
    badges = [t for t in a.p.evaluate("__toasts") if t.startswith("Badge")]
    a.close()
    # 15 bonnes réponses × 5 + bonus d'indices (1 indice vu → 3 points × 2) + 40
    ok = x1 == 75 + 6 + 40 and x2 == 75 + 6 and len(badges) == len(set(badges))
    return ("OK" if ok else "BUG"), f"1er passage +{x1} XP (attendu 121), 2e +{x2} (attendu 81) ; badges : {badges}"

@T("Progression : rang qui change au bon seuil")
def t_rang(b):
    a = App(b, etat(xp=99)); capter_toasts(a)
    a.js("gainXP(1)"); t = a.p.evaluate("__toasts"); chip = a.p.evaluate("document.querySelector('.rank-chip').textContent")
    a.close()
    return ("OK" if any("Nouveau rang : Amateur" in x for x in t) and chip == "Amateur" else "BUG"), f"toasts {t}, rang affiché {chip}"

@T("Progression : badge « Lecteur d'étiquettes » à 8/10")
def t_lecteur(b):
    res = []
    for n in (7, 8):
        a = App(b, etat(done={"n1-l1": "x", "n1-l2": "x", "n1-l3": "x"}))
        a.js("startGame(1,'lis-etiquette')"); a.js(f"let k = 0; return await AUDIT.playThrough(() => k++ < {n})")
        res.append((n, "lecteur" in a.st()["badges"])); a.close()
    return ("OK" if res == [(7, False), (8, True)] else "BUG"), str(res)

@T("Progression : badge « Lexicophile » (20 définitions) via « Voir aussi »")
def t_lexique(b):
    a = App(b)
    a.js("Object.keys(D.glossaire.termes).slice(0,19).forEach(k => ST.gloss[k] = 1); save();")
    a.js("openGlossary()"); a.p.wait_for_timeout(200)
    # 20e définition ouverte depuis un lien « Voir aussi » du glossaire
    a.js("const k = Object.keys(D.glossaire.termes).find(k => !ST.gloss[k] && [...document.querySelectorAll('.see .gl')].some(b => b.dataset.term === k)); window.__k = k; [...document.querySelectorAll('.see .gl')].find(b => b.dataset.term === k).click();")
    n = a.p.evaluate("Object.keys(ST.gloss).length"); badge = a.p.evaluate("!!ST.badges.lexique")
    a.close()
    return ("OK" if n >= 20 and badge else "BUG"), f"{n} définitions consultées, badge attribué : {badge} (le clic « Voir aussi » enregistre le mot mais n'appelle pas checkBadges)"


# ===================================================================== série
def jour_paris(y, m, d, hh=12, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=datetime.timezone(datetime.timedelta(hours=0))).isoformat()

@T("Série : même jour, lendemain, trou de 2 jours, minuit, changements d'heure")
def t_serie(b):
    cas = [
        ("même jour", "2026-05-10", 3, "2026-05-10T18:00:00+02:00", 3),
        ("lendemain", "2026-05-10", 3, "2026-05-11T09:00:00+02:00", 4),
        ("trou de 2 jours", "2026-05-10", 3, "2026-05-13T09:00:00+02:00", 1),
        ("juste après minuit", "2026-05-10", 3, "2026-05-11T00:01:00+02:00", 4),
        ("passage à l'heure d'été (29/03)", "2026-03-28", 5, "2026-03-29T12:00:00+02:00", 6),
        ("passage à l'heure d'hiver (25/10)", "2026-10-25", 5, "2026-10-26T00:30:00+01:00", 6),
    ]
    lignes = []; ok = True
    for nom, last, count, heure, attendu in cas:
        a = App(b, etat(xp=50, streak={"count": count, "last": last}), heure=heure)
        a.js("gainXP(1)"); s = a.st()["streak"]["count"]; a.close()
        lignes.append(f"{nom} : {s} (attendu {attendu})"); ok &= s == attendu
    return ("OK" if ok else "BUG"), " ; ".join(lignes)

@T("Série : affichage (flamme grisée à 0, série perdue après 2 jours)")
def t_serie_aff(b):
    a = App(b, etat(xp=50, streak={"count": 9, "last": "2026-05-10"}), heure="2026-05-12T10:00:00+02:00")
    off = a.p.evaluate("document.querySelector('.stat.flame').className"); val = a.p.evaluate("document.querySelector('.stat.flame').textContent")
    bulle = a.p.evaluate("document.querySelector('.bubble').textContent"); a.shot("serie-perdue")
    a.close()
    return ("OK" if "off" in off and val.strip() == "0" else "BUG"), f"classe « {off} », valeur « {val} », bulle « {bulle} »"

@T("Série : voyage vers l'ouest (fuseau horaire qui recule d'un jour)")
def t_serie_tz(b):
    # série enregistrée le 6 octobre à Auckland ; le même instant à Los Angeles est encore le 5
    a = App(b, etat(xp=50, streak={"count": 10, "last": "2026-10-06"}), heure="2026-10-05T20:00:00-07:00", tz="America/Los_Angeles")
    avant = a.p.evaluate("streakNow()"); a.js("gainXP(1)"); apres = a.st()["streak"]
    a.close()
    return ("OK" if apres["count"] >= 10 else "BUG"), f"série affichée avant : {avant} ; après un gain d'XP : {apres} (la série de 10 jours retombe à 1 car le dernier jour enregistré est « dans le futur »)"


# ===================================================================== défi quotidien
@T("Défi : mêmes questions toute la journée")
def t_defi_stable(b):
    a = App(b, etat(done={"n1-l1": "x", "n1-l2": "x", "n1-l3": "x", "n1-l4": "x"}), heure="2026-05-10T08:00:00+02:00")
    d1 = a.p.evaluate("buildDaily().map(q => q.id)")
    d2 = a.p.evaluate("buildDaily().map(q => q.id)")
    a.close()
    diff = [(x, y) for x, y in zip(d1, d2) if x != y]
    return ("OK" if not diff else "BUG"), f"1er tirage {d1} ; 2e tirage (même jour) {d2} ; différences : {diff}"

@T("Défi : questions différentes le lendemain, sans doublon")
def t_defi_lendemain(b):
    a = App(b, etat(done={"n1-l1": "x", "n1-l2": "x", "n1-l3": "x", "n1-l4": "x"}), heure="2026-05-10T08:00:00+02:00")
    d1 = a.p.evaluate("buildDaily().map(q => q.id)"); a.close()
    a = App(b, etat(done={"n1-l1": "x", "n1-l2": "x", "n1-l3": "x", "n1-l4": "x"}), heure="2026-05-11T08:00:00+02:00")
    d2 = a.p.evaluate("buildDaily().map(q => q.id)")
    a.close()
    doublons = []
    for jour in range(1, 15):
        a = App(b, etat(done={"n1-l1": "x", "n1-l2": "x", "n1-l3": "x", "n1-l4": "x"}, mistakes=["n1-l1-v0", "quiz1-3", "quiz1-4"]), heure=f"2026-06-{jour:02d}T10:00:00+02:00")
        ids = a.p.evaluate("buildDaily().map(q => q.id)"); a.close()
        if len(set(ids)) != len(ids): doublons.append(ids)
    return ("OK" if d1[:4] != d2[:4] and not doublons else "BUG"), f"10/05 {d1[:4]} · 11/05 {d2[:4]} · doublons : {doublons[:2]}"

@T("Défi : nouveau joueur, et bonus de 30 XP une seule fois par jour")
def t_defi_bonus(b):
    a = App(b, heure="2026-05-10T08:00:00+02:00")
    a.js("startDaily()"); a.p.wait_for_timeout(200)
    qs = a.p.evaluate("buildDaily().map(q => q.id)")
    r1 = a.js("return await AUDIT.playThrough(true)")
    # la dernière question est une carte : on clique le vrai point
    def finir():
        while a.p.evaluate("!!document.querySelector('.session [data-check]') && window.__curQ?.type === 'carte'"):
            x, y = a.p.evaluate("(() => { const s = document.querySelector('.session .map-box svg'); s.scrollIntoView({block:'center'}); const e = __curQ.entry; const [x,y] = proj(e.lat, e.lon); const pt = s.createSVGPoint(); pt.x = x; pt.y = y; const q = pt.matrixTransform(s.getScreenCTM()); return [q.x, q.y]; })()")
            a.p.mouse.click(x, y); a.p.click("[data-check]"); a.p.click(".sheet [data-cont]")
            a.js("return await AUDIT.playThrough(true)")
    finir(); x1 = a.st()["xp"]; a.shot("defi-fin"); a.p.click("[data-done]")
    a.js("startDaily()"); a.js("return await AUDIT.playThrough(true)"); finir(); x2 = a.st()["xp"] - x1; a.p.click("[data-done]")
    errs = a.errs; a.close()
    ok = x1 == 6*4 + 30 and x2 == 6*4 and not errs
    return ("OK" if ok else "BUG"), f"questions : {qs} ; 1er défi +{x1} XP (attendu 54), 2e +{x2} (attendu 24) ; erreurs JS : {errs}"


# ===================================================================== tri (glisser-déposer)
def ouvrir_tri(a):
    a.js("runSession([{kind:'q', q:LEVELS[1].jeux[1].questions[0]}], {title:'t', onEnd:() => ({})})"); a.p.wait_for_timeout(300)

def centre(a, sel, i=0):
    return a.p.evaluate("([s, i]) => { const r = document.querySelectorAll(s)[i].getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }", [sel, i])

@T("Tri : glisser-déposer à la souris, dépôt hors colonne, reprise d'une étiquette placée")
def t_tri_souris(b):
    a = App(b, w=400, h=800); ouvrir_tri(a); m = a.p.mouse
    def drag(src, dst):
        m.move(*src); m.down(); m.move(src[0] + 10, src[1] + 10, steps=3); m.move(*dst, steps=8); m.up(); a.p.wait_for_timeout(80)
    drag(centre(a, ".pool .chip", 0), centre(a, ".cat", 2)); placed = a.p.evaluate("document.querySelectorAll('.cat .chip').length")
    drag(centre(a, ".pool .chip", 0), (200, 760)); after_out = a.p.evaluate("[document.querySelectorAll('.cat .chip').length, document.querySelectorAll('.pool .chip').length, [...document.querySelectorAll('.pool .chip')].map(c=>c.style.opacity)]")
    drag(centre(a, ".cat .chip", 0), centre(a, ".cat", 0)); moved = a.p.evaluate("document.querySelector('.cat[data-cat=\"0\"]').querySelectorAll('.chip').length")
    ghosts = a.p.evaluate("document.querySelectorAll('.drag-ghost').length")
    a.close()
    ok = placed == 1 and after_out[0] == 1 and moved == 1 and ghosts == 0
    return ("OK" if ok else "BUG"), f"placé : {placed} ; après dépôt hors colonne : {after_out} ; déplacé vers colonne 0 : {moved} ; fantômes restants : {ghosts}"

@T("Tri : glisser-déposer au toucher (écran tactile émulé)")
def t_tri_toucher(b):
    a = App(b, w=400, h=800, touch=True); ouvrir_tri(a)
    cdp = a.ctx.new_cdp_session(a.p)
    def touch(kind, x, y): cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y}]})
    sx, sy = centre(a, ".pool .chip", 0); dx, dy = centre(a, ".cat", 1)
    touch("touchStart", sx, sy)
    for i in range(1, 11): touch("touchMove", sx + (dx - sx) * i / 10, sy + (dy - sy) * i / 10)
    touch("touchEnd", dx, dy); a.p.wait_for_timeout(150)
    placed = a.p.evaluate("document.querySelectorAll('.cat .chip').length")
    # toucher puis toucher la colonne
    a.p.tap(".pool .chip >> nth=0"); a.p.tap(".cat >> nth=3", position={"x": 20, "y": 20}); a.p.wait_for_timeout(100)
    placed2 = a.p.evaluate("document.querySelectorAll('.cat .chip').length")
    a.close()
    return ("OK" if placed == 1 and placed2 == 2 else "BUG"), f"après glisser tactile : {placed} placée(s) ; après toucher-toucher : {placed2}"

@T("Tri : écouteurs globaux retirés après avoir quitté par le X")
def t_tri_ecouteurs(b):
    a = App(b); cdp = a.ctx.new_cdp_session(a.p)
    def n():
        obj = cdp.send("Runtime.evaluate", {"expression": "window"})["result"]["objectId"]
        ls = cdp.send("DOMDebugger.getEventListeners", {"objectId": obj})["listeners"]
        return sum(1 for l in ls if l["type"] in ("pointermove", "pointerup"))
    n0 = n(); ouvrir_tri(a); n1 = n()
    a.p.click("[data-quit]"); a.p.click(".modal [data-a=ok]"); a.p.wait_for_timeout(100); n2 = n()
    # fin normale (Vérifier → Continuer) : le nettoyage est appelé
    ouvrir_tri(a); a.js("AUDIT.answer(true)"); a.p.click("[data-check]"); a.p.click(".sheet [data-cont]"); a.p.wait_for_timeout(100); n3 = n()
    ov = a.p.evaluate("document.body.style.overflow")
    a.close()
    return ("OK" if n2 == n0 else "BUG"), f"écouteurs pointermove/pointerup sur window : avant {n0}, pendant {n1}, après X {n2}, après une fin normale {n3 - (n2 - n0)} (+{n2-n0} restés du X)"

@T("Tri : utilisable au clavier (question résolue sans souris)")
def t_tri_clavier(b):
    a = App(b); ouvrir_tri(a)
    q = a.p.evaluate("LEVELS[1].jeux[1].questions[0]")
    a.p.focus(".pool .chip >> nth=0")
    for _ in range(len(q["items"])):
        txt = a.p.evaluate("document.activeElement.textContent")
        cat = next(c for t, c in q["items"] if t == txt)
        a.p.keyboard.press("Enter")                                  # sélectionne → le focus passe sur la 1re colonne
        if not a.p.evaluate("document.activeElement.classList.contains('cat')"): break
        for _ in range(30):
            if a.p.evaluate(f"document.activeElement.dataset.cat === '{cat}'"): break
            a.p.keyboard.press("Tab")
        a.p.keyboard.press("Enter")                                  # range → le focus revient sur la réserve
    pret = a.p.evaluate("!document.querySelector('[data-check]').disabled")
    a.p.focus("[data-check]"); a.p.keyboard.press("Enter"); a.p.wait_for_timeout(100)
    ok = a.p.evaluate("!!document.querySelector('.sheet.ok')")
    a.close()
    return ("OK" if pret and ok else "BUG"), f"toutes les étiquettes rangées au clavier : {pret} ; réponse juste : {ok}"


# ===================================================================== association / ordre
@T("Association : changer d'avis, défaire une paire, toutes les combinaisons de clics")
def t_assoc(b):
    a = App(b); a.js("runSession([{kind:'q', q:LEVELS[1].jeux[1].questions[1]}], {title:'t', onEnd:() => ({})})"); a.p.wait_for_timeout(200)
    L = lambda i: a.p.click(f".l .chip[data-l='{i}']"); R = lambda i: a.p.click(f".r .chip[data-r='{i}']")
    pairs = lambda: a.p.evaluate("[document.querySelectorAll('.l .chip[data-pair]').length, document.querySelectorAll('.r .chip[data-pair]').length, document.querySelector('[data-check]').disabled]")
    R(0); s1 = pairs()          # L0 présélectionné → paire L0-R0
    R(0); s2 = pairs()          # re-toucher R0 : la paire passe à L1 (sélectionné automatiquement)
    L(2); R(1); L(2); s3 = pairs()   # paire L2-R1 puis re-toucher L2 la défait
    R(3); s4 = pairs()           # L2 sélectionné → L2-R3
    L(0); R(3); s5 = pairs()     # voler R3 pour L0 : L2 perd sa paire
    for i in range(4): L(i); R(i)
    s6 = pairs(); errs = a.errs; a.close()
    ok = s1[:2] == [1, 1] and s2[:2] == [1, 1] and s3[:2] == [1, 1] and s4[:2] == [2, 2] and s5[:2] == [2, 2] and s6 == [4, 4, False] and not errs
    return ("OK" if ok else "BUG"), f"états successifs (paires gauche, droite, Vérifier désactivé) : {[s1, s2, s3, s4, s5, s6]} ; erreurs {errs}"

@T("Remise en ordre : ajouter, retirer, réordonner")
def t_ordre(b):
    a = App(b); a.js("runSession([{kind:'q', q:LEVELS[1].lecons[3].verif[0]}], {title:'t', onEnd:() => ({})})"); a.p.wait_for_timeout(200)
    for i in range(5): a.p.click(f".pool .chip[data-in='{i}']")
    full = a.p.evaluate("!document.querySelector('[data-check]').disabled")
    a.p.click(".slots .chip[data-out='1']"); a.p.click(".slots .chip[data-out='0']")
    mid = a.p.evaluate("[document.querySelectorAll('.slots .chip').length, document.querySelector('[data-check]').disabled, document.querySelectorAll('.pool .chip.used').length]")
    a.js("const b = [...document.querySelectorAll('.pool .chip')].find(c => !c.classList.contains('used')); b.click(); document.querySelector(`.pool .chip[data-in='${b.dataset.in}']`).click();")  # double clic sur la même étape
    dup = a.p.evaluate("document.querySelectorAll('.slots .chip').length")
    errs = a.errs; a.close()
    return ("OK" if full and mid == [3, True, 3] and dup == 4 and not errs else "BUG"), f"complet→Vérifier actif {full} ; après 2 retraits {mid} ; double clic {dup} étapes"


# ===================================================================== carte
def ouvrir_carte(a, tier=1):
    a.js("go('carte')"); a.p.click(f".tier[data-t='{tier}']"); a.p.click("text=Lancer une partie"); a.p.wait_for_timeout(300)

def pt_ecran(a, lat, lon):
    return a.p.evaluate("([la, lo]) => { const s = document.querySelector('.map-box > svg'); const [x, y] = proj(la, lo); const pt = s.createSVGPoint(); pt.x = x; pt.y = y; const q = pt.matrixTransform(s.getScreenCTM()); return [q.x, q.y]; }", [lat, lon])

@T("Carte : un clic n'est pas un déplacement et inversement")
def t_carte_clic(b):
    a = App(b, w=400, h=900); ouvrir_carte(a); m = a.p.mouse
    vb0 = a.p.evaluate("document.querySelector('.map-box svg').getAttribute('viewBox')")
    m.move(200, 400); m.down(); m.move(203, 402); m.up()                       # petit tremblement : c'est un clic
    g1 = a.p.evaluate("!document.querySelector('main .btn.leaf').disabled")
    a.js("render()"); a.p.wait_for_timeout(100)
    m.move(200, 400); m.down(); m.move(260, 440, steps=10); m.up()             # vrai glissé : pas d'épingle
    g2 = a.p.evaluate("!document.querySelector('main .btn.leaf').disabled"); vb2 = a.p.evaluate("document.querySelector('.map-box svg').getAttribute('viewBox')")
    a.close()
    return ("OK" if g1 and not g2 and vb2 != vb0 else "BUG"), f"clic (3 px de tremblement) → épingle {g1} ; glissé de 70 px → épingle {g2}, carte déplacée {vb2 != vb0}"

@T("Carte : molette, boutons + / − / recentrer et limites de zoom")
def t_carte_zoom(b):
    a = App(b, w=400, h=900); ouvrir_carte(a)
    w = lambda: a.p.evaluate("+document.querySelector('.map-box svg').getAttribute('viewBox').split(' ')[2]")
    w0 = w(); a.p.mouse.move(200, 400)
    for _ in range(60): a.p.mouse.wheel(0, -200)
    a.p.wait_for_timeout(100); wmin = w()
    for _ in range(60): a.p.mouse.wheel(0, 200)
    a.p.wait_for_timeout(100); wmax = w()
    a.p.click("[data-z=fit]"); wfit = w(); a.p.click("[data-z=in]"); win = w(); a.p.click("[data-z=out]"); wout = w()
    pin = a.p.evaluate("!document.querySelector('main .btn.leaf').disabled")
    vb = a.p.evaluate("document.querySelector('.map-box svg').getAttribute('viewBox')")
    a.p.click("[data-z=fit]")
    for _ in range(60): a.p.mouse.wheel(0, 200)
    a.shot("carte-dezoom-max")
    a.close()
    return ("OK" if wmin == 6 and wmax == 1500 and abs(wfit - w0) < 1e-6 and not pin else "BUG"), f"largeur vue : départ {w0}, min {wmin}, max {wmax}, recentrer {wfit}, +{win}, −{wout} ; épingle posée par les boutons : {pin} ; au dézoom maximal la France ne fait plus que {round(1100/1500*100)} % de la boîte et peut sortir du cadre ({vb})"

@T("Carte : pincement à deux doigts")
def t_carte_pinch(b):
    a = App(b, w=400, h=900, touch=True); ouvrir_carte(a); cdp = a.ctx.new_cdp_session(a.p)
    r = a.p.evaluate("(() => { const r = document.querySelector('.map-box').getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; })()")
    w0 = a.p.evaluate("+document.querySelector('.map-box svg').getAttribute('viewBox').split(' ')[2]")
    pts = lambda d: [{"x": r[0] - d, "y": r[1], "id": 1}, {"x": r[0] + d, "y": r[1], "id": 2}]
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": pts(20)})
    for d in range(25, 121, 5): cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": pts(d)})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); a.p.wait_for_timeout(100)
    w1 = a.p.evaluate("+document.querySelector('.map-box svg').getAttribute('viewBox').split(' ')[2]")
    pin = a.p.evaluate("!document.querySelector('main .btn.leaf').disabled")
    a.close()
    return ("OK" if w1 < w0 / 3 and not pin else "BUG"), f"largeur vue {w0} → {w1} (écart des doigts ×6) ; épingle posée par erreur : {pin}"

@T("Carte : taille des épingles, villes et distance selon le zoom et l'écran")
def t_carte_tailles(b):
    res = []
    for w in (320, 1280):
        a = App(b, w=w, h=900); ouvrir_carte(a, 3)
        e = a.p.evaluate("MAPGAME.rounds[0]"); x, y = pt_ecran(a, e["lat"] + .3, e["lon"] + .3); a.p.mouse.click(x, y)
        a.p.click("text=Valider ma position"); a.p.wait_for_timeout(900)
        for z in ("fit", "in"):
            a.p.click(f"[data-z={z}]"); a.p.wait_for_timeout(150)
            m = a.p.evaluate("(() => { const h = el => { const r = el?.getBoundingClientRect(); return r ? Math.round(r.height) : null; }; return { epingle: h(document.querySelector('.g-marks g')), ville: h(document.querySelector('.city text')), distance: h(document.querySelector('.map-dist')) }; })()")
            res.append((w, z, m))
        a.close()
    hs = [r[2]["epingle"] for r in res]
    return ("OK" if max(hs) - min(hs) <= 3 else "BUG"), f"hauteurs en px (épingle / texte de ville / distance) : {res}"

@T("Carte : scores calculés à la main")
def t_carte_scores(b):
    a = App(b, w=400, h=900); ouvrir_carte(a)
    data = json.loads((RACINE / "content" / "carte-vins.json").read_text())
    P = {p["id"]: p for p in data["paliers"]}
    def km(p, q):
        r = math.pi / 180; x = math.sin((q[0]-p[0])*r/2)**2 + math.cos(p[0]*r)*math.cos(q[0]*r)*math.sin((q[1]-p[1])*r/2)**2
        return 2 * 6371 * math.asin(math.sqrt(x))
    cas = [("Sancerre", 3, (47.332, 2.836 + .1)), ("Romanée-Conti", 5, (47.1585 + .01, 4.9505)), ("Château Latour", 5, (45.18 + .05, -0.746)),
           ("Aÿ", 4, (49.054, 4.004 + .3)), ("Pauillac", 3, (44.84, -0.58)), ("Hermitage", 3, (45.072, 4.84))]
    lignes = []; ok = True
    for nom, palier, g in cas:
        e = next(v for v in data["vins"] if v["vin"] == nom and v["palier"] == palier)
        d = km((e["lat"], e["lon"]), g); att = round(5000 * math.exp(-max(0, d - P[palier]["plein"]) / P[palier]["echelleKm"]))
        s = a.p.evaluate("([e, g]) => scoreMap(e, g, null)", [e, list(g)])
        lignes.append(f"{nom} (p{palier}) à {d:.2f} km : {s['score']} vs {att} à la main"); ok &= s["score"] == att
    a.close()
    return ("OK" if ok else "BUG"), " ; ".join(lignes)

@T("Carte : détection « dans la région » (Corse, côtes, frontière de département)")
def t_carte_region(b):
    a = App(b, w=400, h=900); ouvrir_carte(a)
    cas = [("corse", 42.698, 9.363, True), ("corse", 41.92, 8.74, True), ("corse", 42.0, 9.0, True), ("languedoc-roussillon", 42.483, 3.129, True),
           ("provence", 43.215, 5.538, True), ("bordeaux", 45.55, -1.06, True), ("bordeaux", 45.2, -1.3, False), ("beaujolais", 45.764, 4.836, True),
           ("rhone", 45.489, 4.81, True), ("languedoc-roussillon", 43.84, 4.36, True), ("alsace", 48.573, 7.752, True), ("champagne", 48.857, 2.352, False)]
    lignes = []; ok = True
    for reg, la, lo, att in cas:
        r = a.p.evaluate("([la, lo, reg]) => { const svg = document.querySelector('.map-box > svg'); const host = document.createElement('div'); const mv = MapView(host, {}); document.body.appendChild(host); const v = mv.inRegion([la, lo], reg); host.remove(); return v; }", [la, lo, reg])
        lignes.append(f"{reg} ({la}, {lo}) → {r}" + ("" if r == att else f" ✗ attendu {att}")); ok &= r == att
    a.close()
    return ("OK" if ok else "BUG"), " ; ".join(lignes)

@T("Carte : changer d'onglet en pleine partie, puis revenir")
def t_carte_onglet(b):
    a = App(b, w=400, h=900); ouvrir_carte(a)
    e = a.p.evaluate("MAPGAME.rounds[0]"); x, y = pt_ecran(a, e["lat"], e["lon"]); a.p.mouse.click(x, y)
    a.p.click(".tab[data-go=home]"); a.p.click(".tab[data-go=carte]"); a.p.wait_for_timeout(200)
    garde = a.p.evaluate("[MAPGAME.i, !document.querySelector('main .btn.leaf').disabled]")
    x, y = pt_ecran(a, e["lat"], e["lon"]); a.p.mouse.click(x, y); a.p.click("text=Valider ma position"); a.p.wait_for_timeout(300)
    a.p.click(".tab[data-go=defi]"); a.p.click(".tab[data-go=carte]"); a.p.wait_for_timeout(200)
    apres = a.p.evaluate("[MAPGAME.i, MAPGAME.scores.length, document.querySelector('.round-meta').textContent]")
    # onglet du navigateur masqué puis visible
    a.p.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    errs = a.errs; a.close()
    return ("INFO" if not errs else "BUG"), f"après aller-retour avant validation : manche {garde[0]+1}, épingle conservée {garde[1]} ; après aller-retour pendant la révélation : manche {apres[0]+1}, {apres[1]} score(s), « {apres[2]} » (la révélation est sautée) ; erreurs {errs}"


# ===================================================================== clavier, focus
@T("Clavier : touches 1-4 et Entrée dans une session")
def t_clavier(b):
    a = App(b); a.js("startQuiz(1)"); a.p.wait_for_timeout(200)
    a.p.keyboard.press("2"); sel = a.p.evaluate("document.querySelector('.choice[aria-pressed=true]')?.dataset.i")
    a.p.keyboard.press("Enter"); sheet = a.p.evaluate("!!document.querySelector('.sheet')")
    a.p.keyboard.press("Enter"); nxt = a.p.evaluate("[!document.querySelector('.sheet'), document.querySelector('.qkind').textContent]")
    a.p.keyboard.press("1"); a.p.keyboard.press("Enter"); a.p.keyboard.press("Enter")
    q3 = a.p.evaluate("document.querySelector('.qtitle').textContent")
    a.close()
    return ("OK" if sel == "1" and sheet and nxt[0] else "BUG"), f"touche 2 → choix {sel} ; Entrée → feuille {sheet} ; Entrée → question suivante {nxt} ; 3e question « {q3} »"

@T("Clavier : piège de focus (session, modale, glossaire) et retour du focus")
def t_focus(b):
    a = App(b)
    def sorties(racine, n=16):
        out = []
        for _ in range(n):
            a.p.keyboard.press("Tab")
            f = a.p.evaluate(f"(() => {{ const e = document.activeElement; return [!!e.closest('{racine}'), e.tagName, (e.textContent || '').trim().slice(0, 20)]; }})()")
            if not f[0] and f[1] != "BODY": out.append(f[1:])   # BODY = passage vers l'interface du navigateur, normal
        return out
    a.js("startQuiz(1)"); a.p.wait_for_timeout(200); s1 = sorties(".session")
    a.p.click("[data-quit]"); s2 = sorties(".modal"); a.p.click(".modal [data-a=no]")
    retour = a.p.evaluate("document.activeElement.matches('[data-quit]')")
    a.p.evaluate("closeSession(); render()"); a.p.focus(".tab[data-go=glossaire]"); a.p.keyboard.press("Enter"); a.p.wait_for_timeout(200)
    s3 = sorties(".drawer"); a.p.keyboard.press("Escape"); a.p.wait_for_timeout(100)
    retour2 = a.p.evaluate("document.activeElement.dataset.go")
    a.close()
    ok = not s1 and not s2 and not s3 and retour and retour2 == "glossaire"
    return ("OK" if ok else "BUG"), f"éléments atteints hors du calque : session {s1[:3]}, modale {s2[:3]}, glossaire {s3[:3]} ; focus rendu au X après « Rester » : {retour} ; focus rendu à l'onglet Lexique après Échap : {retour2 == 'glossaire'}"

@T("Clavier : Échap ferme le glossaire et la modale, sans écouteurs qui s'accumulent")
def t_echap(b):
    a = App(b); cdp = a.ctx.new_cdp_session(a.p)
    def n():
        obj = cdp.send("Runtime.evaluate", {"expression": "document"})["result"]["objectId"]
        return sum(1 for l in cdp.send("DOMDebugger.getEventListeners", {"objectId": obj})["listeners"] if l["type"] == "keydown")
    n0 = n()
    for _ in range(3): a.js("openGlossary()"); a.p.click(".drawer [data-close]")      # fermé à la souris
    n1 = n()
    a.js("openGlossary()"); a.p.wait_for_timeout(200); a.p.keyboard.press("Escape")
    g = a.p.evaluate("!document.querySelector('.drawer')")
    a.js("startQuiz(1)"); a.p.click("[data-quit]"); a.p.keyboard.press("Escape"); a.p.wait_for_timeout(50)
    m = a.p.evaluate("[!document.querySelector('.modal'), !!document.querySelector('.session')]")
    n2 = n(); a.close()
    ok = g and m == [True, True] and n1 == n0 and n2 == n0
    return ("OK" if ok else "BUG"), f"glossaire fermé par Échap : {g} ; modale fermée par Échap (session conservée) : {m} ; écouteurs keydown sur document : {n0} au départ, {n1} après 3 glossaires fermés à la souris, {n2} à la fin"


@T("Clavier : étiquette en mode « toucher » utilisable au clavier")
def t_etiq_clavier(b):
    a = App(b); a.js("runSession([{kind:'q', q:LEVELS[1].lecons[2].verif[0]}], {title:'t', onEnd:() => ({})})"); a.p.wait_for_timeout(200)
    f = a.p.evaluate("[...document.querySelectorAll('.lbl .ch')].map(c => c.tabIndex)")
    # Tab jusqu'au millésime, Entrée pour le choisir, Entrée pour vérifier
    for _ in range(25):
        if a.p.evaluate("document.activeElement.dataset?.champ === 'millesime'"): break
        a.p.keyboard.press("Tab")
    a.p.keyboard.press("Enter"); sel = a.p.evaluate("document.querySelector('.ch.sel')?.dataset.champ")
    sheet_tot = a.p.evaluate("!!document.querySelector('.sheet')")
    a.p.focus("[data-check]"); a.p.keyboard.press("Enter"); a.p.wait_for_timeout(100)
    ok = a.p.evaluate("!!document.querySelector('.sheet.ok')")
    a.close()
    return ("OK" if sel == "millesime" and not sheet_tot and ok else "BUG"), f"tabIndex des champs : {f} ; Entrée sélectionne « {sel} » sans vérifier trop tôt ({not sheet_tot}) ; réponse juste : {ok}"


# ===================================================================== robustesse
@T("Robustesse : localStorage indisponible (navigation privée stricte)")
def t_ls(b):
    a = App(b, init="Object.defineProperty(window, 'localStorage', { get(){ throw new DOMException('refusé', 'SecurityError'); } });")
    ok = a.p.evaluate("!!document.querySelector('.home-hero')"); a.js("startStep(1,'n1-l1')"); r = a.js("return await AUDIT.playThrough(true)")
    errs = a.errs; a.close()
    return ("OK" if ok and r == "fin" and not errs else "BUG"), f"accueil affiché {ok}, leçon jouable {r}, erreurs {errs}"

@T("Robustesse : sauvegardes corrompues ou anciennes")
def t_corrompu(b):
    cas = {"pas du JSON": "{xp:", "null": "null", "tableau": "[]", "xp texte": '{"xp":"beaucoup"}', "streak null": '{"xp":10,"streak":null}',
           "map sans regions (ancienne version)": '{"xp":10,"map":{"games":2}}', "quiz null": '{"xp":10,"quiz":null}', "mistakes objet": '{"xp":10,"mistakes":{}}'}
    lignes = []; bug = False
    for nom, raw in cas.items():
        a = App(b, init=f"try{{if(!sessionStorage.getItem('j')){{sessionStorage.setItem('j',1);localStorage.setItem('{KEY}', {json.dumps(raw)});location.reload();}}}}catch(e){{}}")
        a.p.wait_for_timeout(300)
        home = a.p.evaluate("!!document.querySelector('.home-hero')")
        try:
            a.js("go('profil')"); a.js("go('home')"); a.js("startStep(1,'n1-l1')"); r = a.js("return await AUDIT.playThrough(true)")
        except Exception as e: r = "exception : " + str(e).split("\n")[0][:80]
        errs = a.errs[:1]
        if errs or not home or r != "fin": bug = True
        lignes.append(f"{nom} → accueil {home}, leçon {r}{', erreur : ' + errs[0][:90] if errs else ''}")
        if nom == "streak null": a.shot("sauvegarde-corrompue")
        a.close()
    return ("BUG" if bug else "OK"), " ; ".join(lignes)

@T("Robustesse : fichier de contenu manquant ou invalide")
def t_contenu(b):
    out = []
    for nom, fn in [("404", lambda r: r.fulfill(status=404, body="")), ("JSON invalide", lambda r: r.fulfill(status=200, body="{ pas du json", content_type="application/json"))]:
        a = App(b, routes=[("**/content/glossaire.json", fn)])
        t = a.p.evaluate("document.body.innerText"); a.shot(f"contenu-{'manquant' if nom == '404' else 'invalide'}")
        out.append(f"{nom} : « {' '.join(t.split())[:160]} »"); a.close()
    return "INFO", " ; ".join(out)

@T("Robustesse : double clic rapide sur Continuer / Vérifier")
def t_double(b):
    a = App(b); a.js("startStep(1,'n1-l1')"); a.p.wait_for_timeout(200)
    a.p.dblclick("[data-next]"); a.p.wait_for_timeout(100)
    titre = a.p.evaluate("document.querySelector('.lcard h2').textContent")
    a.close()
    a = App(b); a.js("startQuiz(1)"); a.p.wait_for_timeout(200); a.p.click(".choice >> nth=1")
    a.p.dblclick("[data-check]"); a.p.wait_for_timeout(400)
    etat_q = a.p.evaluate("[!!document.querySelector('.sheet'), document.querySelector('.qtitle')?.textContent]")
    a.close()
    return ("OK" if titre == "Que trouve-t-on dans un grain ?" else "BUG"), f"double clic sur Continuer (carte 1) → carte affichée « {titre} » (attendu : carte 2 « Que trouve-t-on dans un grain ? ») ; double clic sur Vérifier → feuille visible {etat_q[0]}"

@T("Robustesse : défilement de la page bloqué pendant la session et rétabli après")
def t_scroll(b):
    a = App(b); r = []
    a.js("startStep(1,'n1-l1')"); r.append(a.p.evaluate("document.body.style.overflow"))
    a.p.click("[data-quit]"); a.p.click(".modal [data-a=ok]"); r.append(a.p.evaluate("document.body.style.overflow"))
    a.js("startStep(1,'n1-l1')"); a.js("return await AUDIT.playThrough(true)"); a.p.click("[data-done]"); r.append(a.p.evaluate("document.body.style.overflow"))
    a.js("openGlossary()"); a.p.mouse.move(50, 300); y0 = a.p.evaluate("scrollY"); a.p.mouse.wheel(0, 800); a.p.wait_for_timeout(200); y1 = a.p.evaluate("scrollY")
    a.close()
    return ("OK" if r == ["hidden", "", ""] and y1 == y0 else "BUG"), f"overflow du body : pendant {r[0]!r}, après X {r[1]!r}, après fin {r[2]!r} ; glossaire ouvert : défilement de la page derrière {y0} → {y1}"

@T("Robustesse : quitter une session, message fidèle ; X de l'écran de fin")
def t_quitter(b):
    a = App(b); a.js("startQuiz(1)"); a.p.wait_for_timeout(100); a.js("AUDIT.answer(false)"); a.p.click("[data-check]")
    a.p.click(".sheet [data-cont]"); a.p.click("[data-quit]"); msg = a.p.evaluate("document.querySelector('.modal p').textContent")
    a.p.click(".modal [data-a=ok]"); st = a.st()
    a.js("startStep(1,'n1-l1')"); a.js("return await AUDIT.playThrough(true)"); a.p.click("[data-quit]"); a.p.wait_for_timeout(100)
    fin = a.p.evaluate("[!!document.querySelector('.modal'), !!document.querySelector('.session')]")
    a.close()
    ok = st["mistakes"] == ["quiz1-0"] and st["xp"] == 0 and "erreurs restent" in msg and fin == [False, False]
    return ("OK" if ok else "BUG"), f"message : « {msg} » ; après avoir quitté : XP {st['xp']}, pile {st['mistakes']} ; X sur l'écran de fin → modale {fin[0]}, session encore ouverte {fin[1]}"


# ===================================================================== profil, glossaire, divers
@T("Profil : export puis import, code invalide, tout effacer")
def t_profil(b):
    a = App(b, etat(xp=420, quiz={"1": {"best": 87, "passed": True}}, theme="dark")); a.js("go('profil')")
    code = a.p.evaluate("document.querySelector('#save-out').value")
    a.js("ST = freshState(); save(); render();")
    a.js("go('profil')"); a.p.fill("#save-in", code); a.p.click("[data-a=import]"); xp = a.st()["xp"]
    a.js("go('profil')"); a.p.fill("#save-in", code[:-10]); a.p.click("[data-a=import]"); msg = a.p.evaluate("document.querySelector('#save-msg').textContent")
    a.p.fill("#save-in", "eyJ4cCI6NX0="); a.p.click("[data-a=import]"); xp_min = a.st()["xp"]
    a.js("go('profil')"); th0 = a.p.evaluate("document.documentElement.dataset.theme")
    a.p.click("[data-a=reset]"); a.p.click(".modal [data-a=ok]"); th1 = a.p.evaluate("[document.documentElement.dataset.theme, ST.theme]")
    a.shot("effacer-theme"); a.close()
    return ("OK" if xp == 420 and "pas valide" in msg and th1[0] is None else "BUG"), f"import → {xp} XP ; code tronqué → « {msg} » ; code minimal {{xp:5}} accepté → {xp_min} XP ; thème avant effacement {th0!r}, après : data-theme={th1[0]!r} alors que ST.theme={th1[1]!r}"

@T("Profil : « Tout effacer » avec un thème forcé")
def t_effacer_theme(b):
    a = App(b, etat(xp=42)); a.js("go('profil')"); a.p.click("[data-th=dark]")
    th0 = a.p.evaluate("document.documentElement.dataset.theme")
    a.p.click("[data-a=reset]"); a.p.click(".modal [data-a=ok]"); a.p.wait_for_timeout(100)
    th1 = a.p.evaluate("[document.documentElement.dataset.theme ?? null, ST.theme, document.querySelector('[data-th][aria-pressed=true]').textContent]")
    a.shot("effacer-theme"); a.close()
    return ("OK" if th1[0] is None else "BUG"), f"avant : data-theme={th0!r} ; après « Tout effacer » : data-theme={th1[0]!r}, ST.theme={th1[1]!r}, bouton actif « {th1[2]} » (l'appli reste sombre alors que le réglage affiché est Auto)"

@T("Glossaire : recherche avec et sans accents, majuscules, « Voir aussi »")
def t_glossaire(b):
    a = App(b); a.js("openGlossary()"); a.p.wait_for_timeout(100)
    def n(q): a.p.fill("#gl-search", q); return a.p.evaluate("document.querySelectorAll('#gl-list .term').length")
    r = {q: n(q) for q in ["élevage", "elevage", "ELEVAGE", "aop", "moût", "mout", "œil", "zzz"]}
    a.p.fill("#gl-search", ""); a.p.click(".term .see .gl >> nth=0"); a.p.wait_for_timeout(500)
    foc = a.p.evaluate("document.querySelector('.term.focus h3')?.textContent")
    a.close()
    ok = r["élevage"] == r["elevage"] == r["ELEVAGE"] >= 1 and r["mout"] == r["moût"] >= 1 and r["zzz"] == 0 and foc
    return ("OK" if ok else "BUG"), f"résultats {r} ; « Voir aussi » met en avant « {foc} »"

@T("Toasts : plusieurs à la suite")
def t_toasts(b):
    a = App(b); a.js("toast(I.star,'Un','a'); toast(I.star,'Deux','b'); toast(I.star,'Trois','c')")
    vus = []
    for _ in range(9):
        vus.append(a.p.evaluate("[...document.querySelectorAll('.toast')].map(t => t.firstElementChild.nextSibling?.textContent || t.textContent)")); a.p.wait_for_timeout(900)
    a.close()
    seq = [v for v in vus if v]
    return "INFO", f"un toast à la fois, 2,4 s chacun : {seq} — 3 toasts mettent 7,2 s à s'afficher"

@T("Étiquettes : provenance des vins étrangers")
def t_provenance(b):
    a = App(b); a.js("runSession([{kind:'q', q:{type:'etiquette', etiquette:'taylors', mode:'toucher', cible:'provenance', question:'Touche la provenance.', explication:'x'}}], {title:'t', onEnd:() => ({})})")
    a.p.wait_for_timeout(200); lbl = a.p.evaluate("document.querySelector('.ch-provenance').textContent")
    a.js("AUDIT.answer(false)"); a.p.click("[data-check]"); rep = a.p.evaluate("document.querySelector('.sheet .answer').textContent")
    a.shot("provenance-portugal"); a.close()
    return ("OK" if "Portugal" in rep else "BUG"), f"étiquette : « {lbl} » ; correction affichée : « {rep} »"

@T("Mouvement réduit : rien ne reste invisible")
def t_reduced(b):
    a = App(b, reduced=True); a.js("startStep(1,'n1-l1')"); a.p.wait_for_timeout(100)
    op = a.p.evaluate("getComputedStyle(document.querySelector('.lcard')).opacity")
    a.js("confetti()"); conf = a.p.evaluate("[...document.querySelectorAll('.confetti i')].filter(i => i.getBoundingClientRect().bottom > 0).length")
    a.js("toast(I.star,'t','s')"); t = a.p.evaluate("getComputedStyle(document.querySelector('.toast')).opacity")
    smooth = "behavior:\"smooth\"" in (RACINE / "index.html").read_text()
    a.close()
    return ("OK" if op == "1" and t == "1" else "BUG"), f"carte de leçon opacité {op}, toast {t}, confettis visibles {conf} ; scrollIntoView smooth codé en dur (non soumis à prefers-reduced-motion) : {smooth}"

@T("Accessibilité : régions live et noms des boutons")
def t_a11y(b):
    a = App(b, etat(xp=64, streak={"count": 1, "last": datetime.date.today().isoformat()}))
    live = a.p.evaluate("document.getElementById('app').getAttribute('aria-live')")
    noms = a.p.evaluate("[...document.querySelectorAll('#stats button')].map(b => [b.textContent.trim(), b.getAttribute('aria-label'), b.title])")
    lang_title = a.p.evaluate("[document.title, document.querySelector('title').parentElement.tagName]")
    a.close()
    return "INFO", f"#app aria-live={live!r} (toute l'appli est relue à chaque rendu) ; boutons de stats (texte, aria-label, title) : {noms} ; <title> placé dans {lang_title[1]}"


def main(args):
    from playwright.sync_api import sync_playwright
    CAP.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": CHROME} if os.path.exists(CHROME) else {}))
        for t in TESTS:
            if args.ecrans and not any(f.lower() in t.nom.lower() for f in args.ecrans.split(",")): continue
            t0 = time.time()
            try: st, det = t(b)
            except Exception as e: st, det = "ERREUR", f"{e.__class__.__name__}: {str(e)[:300]}"
            RESULTATS.append({"test": t.nom, "statut": st, "detail": det, "navigateur": "chromium"})
            print(f"[{st:<6}] {t.nom} ({time.time()-t0:.1f} s)\n         {det}", flush=True)
        b.close()
    if "webkit" in args.navigateurs:
        import audit_webkit
        RESULTATS.extend(audit_webkit.main())
    (RACINE / "audit" / "fonctionnel.json").write_text(json.dumps(RESULTATS, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(1 for r in RESULTATS if r["statut"] in ("BUG", "ERREUR"))
    print(f"\n{len(RESULTATS)} tests, {n} en échec → audit/fonctionnel.json")
    return 1 if n else 0
