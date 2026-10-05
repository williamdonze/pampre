"""Tests fonctionnels rejoués sous WebKit (moteur de Safari), via WebKitGTK.

Lancé par `python3 tools/audit.py --fonctionnel --navigateurs chromium,webkit`.
Couvre ce qui dépend du moteur : détection « dans la région » (isPointInFill), clic et
glissé sur la carte, glisser-déposer du tri, recherche sans accents, parcours complet
d'une leçon et du quiz sans erreur JS.
"""
import json, time
from types import SimpleNamespace
import audit

def main():
    out = []
    def res(nom, ok, det):
        st = "OK" if ok is True else ("INFO" if ok is None else "BUG"); out.append({"test": nom, "statut": st, "detail": det, "navigateur": "webkit"})
        print(f"[{st:<6}] WebKit · {nom}\n         {det}", flush=True)
    args = SimpleNamespace(sans_polices=False, mouvement_reduit=False, chromium_bundle=False)
    d = audit.WK("webkit", args, "light")
    try:
        d.ouvrir(None, 400, "light")
        cas = [("corse", 42.698, 9.363, True), ("corse", 42.0, 9.0, True), ("languedoc-roussillon", 42.483, 3.129, True), ("provence", 43.215, 5.538, True),
               ("bordeaux", 45.55, -1.06, True), ("bordeaux", 45.2, -1.3, False), ("alsace", 48.573, 7.752, True), ("champagne", 48.857, 2.352, False)]
        r = d.js("const out = []; const host = document.createElement('div'); document.body.appendChild(host); const mv = MapView(host, {}); for (const [reg, la, lo] of " + json.dumps([[c[0], c[1], c[2]] for c in cas]) + ") out.push(mv.inRegion([la, lo], reg)); host.remove(); return out;")
        ok = isinstance(r, list) and all(x == c[3] for x, c in zip(r, cas))
        res("isPointInFill : détection « dans la région »", ok, " ; ".join(f"{c[0]} ({c[1]}, {c[2]}) → {x}" for x, c in zip(r if isinstance(r, list) else [], cas)) or str(r))

        d.js("go('carte'); document.querySelector('.tier[data-t=\"1\"]').click(); [...document.querySelectorAll('main .btn')].find(b => /Lancer/.test(b.textContent)).click();")
        time.sleep(.4)
        x, y = d.js("const s = document.querySelector('.map-box svg'); s.scrollIntoView({block:'center'}); await new Promise(r => setTimeout(r, 100)); const r = s.getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2];")
        d.clic(x, y); time.sleep(.2)
        pin = d.js("return !document.querySelector('main .btn.leaf').disabled")
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        vb0 = d.js("return document.querySelector('.map-box svg').getAttribute('viewBox')")
        a = ActionBuilder(d.d); p = a.pointer_action
        p.move_to_location(int(x), int(y)).pointer_down()
        for i in range(1, 11): p.move_to_location(int(x) + 6 * i, int(y) + 3 * i)
        p.pointer_up(); a.perform(); time.sleep(.2)
        vb1 = d.js("return document.querySelector('.map-box svg').getAttribute('viewBox')")
        res("Carte : clic place l'épingle, glissé déplace la carte", pin and vb1 != vb0, f"épingle après clic : {pin} ; viewBox {vb0} → {vb1}")

        d.ouvrir(None, 400, "light")
        d.js("runSession([{kind:'q', q:LEVELS[1].jeux[1].questions[0]}], {title:'t', onEnd:() => ({})})"); time.sleep(.3)
        (sx, sy), (tx, ty) = d.js("const c = e => { const r = e.getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }; return [c(document.querySelector('.pool .chip')), c(document.querySelectorAll('.cat')[2])];")
        a = ActionBuilder(d.d); p = a.pointer_action; p.move_to_location(int(sx), int(sy)).pointer_down()
        for i in range(1, 13): p.move_to_location(int(sx + (tx - sx) * i / 12), int(sy + (ty - sy) * i / 12))
        p.pointer_up(); a.perform(); time.sleep(.2)
        n = d.js("return [document.querySelectorAll('.cat .chip').length, document.querySelectorAll('.drag-ghost').length]")
        res("Tri : glisser-déposer à la souris", n == [1, 0], f"étiquettes placées / fantômes restants : {n}")

        d.ouvrir(None, 400, "light")
        r = d.js("openGlossary(); const f = q => { const s = document.querySelector('#gl-search'); s.value = q; s.dispatchEvent(new Event('input')); return document.querySelectorAll('#gl-list .term').length; }; return [f('élevage'), f('elevage'), f('mout'), f('zzz')];")
        res("Glossaire : recherche sans accents (\\p{Diacritic})", isinstance(r, list) and r[0] == r[1] >= 1 and r[2] >= 1 and r[3] == 0, f"résultats élevage/elevage/mout/zzz : {r}")

        d.ouvrir(None, 375, "light")
        r1 = d.js("startStep(1,'n1-l1'); return await AUDIT.playThrough(true)"); d.js("document.querySelector('[data-done]').click()")
        r2 = d.js("startQuiz(1); return await AUDIT.playThrough(true)"); d.js("document.querySelector('[data-done]').click()")
        errs = d.errs
        res("Parcours complet d'une leçon et du quiz", r1 == "fin" and r2 == "fin" and not errs, f"leçon : {r1}, quiz : {r2}, erreurs JS : {errs}")
        ua = d.js("return navigator.userAgent")
        res("Moteur testé", None, ua)
    finally:
        d.fermer()
    return out
