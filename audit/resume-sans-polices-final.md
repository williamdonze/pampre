# Résumé automatique de l'audit

95 constats bruts, 5 groupes.

## contraste-desactive

- `div.session > div.s-foot > div.wrap > button.btn.leaf` « Vérifier » — 3.49:1 < 4.5 (#7a6469 sur #d9cdc3, 16px gras) — ×84 · chromium · largeurs [320, 375, 1280] · thèmes ['clair'] · écrans : etiquette-00, etiquette-01, etiquette-02, etiquette-03, etiquette-04, etiquette-05 … (+22) · [capture](captures/chromium-q-qcm-avant-320-clair-sans-polices-final.png)
- `main.wrap > div.seg > button` « Monde · bientôt » — 2.16:1 < 4.5 (#a79492 sur #ebddd0, 13px gras) — ×3 · chromium · largeurs [320, 375, 1280] · thèmes ['clair'] · écrans : carte-reglages · [capture](captures/chromium-carte-reglages-320-clair-sans-polices-final.png)

## scenario-echoue

- `` «  » — Page.evaluate: TypeError: Cannot read properties of undefined (reading 'quiz')
    at eval (eval at evaluate (:311:30), <anonymous>:1:59)
    at eval (eval at evaluate (:311:30), <anonymous>:1:136)
    at eval (<anonymous>)
    at UtilityScript.evaluate (<anonymous>:311:30)
    at UtilityScript.<ano — ×2 · chromium · largeurs [320] · thèmes ['clair'] · écrans : q-etiquette-qcm-juste, q-tri2-avant

## svg-texte-coupe

- `#s-main > article.lcard > div.illu svg text` « clavelin » — texte 166→227 × 57→73, viewBox 0 0 220 150 — ×3 · chromium · largeurs [320, 375, 1280] · thèmes ['clair'] · écrans : lecon2-carte6 · [capture](captures/chromium-lecon2-carte6-320-clair-sans-polices-final.png)
- `#s-main > article.lcard > div.illu svg text` « 70 % d'humidité » — texte 132→233 × 78→91, viewBox 0 0 220 150 — ×3 · chromium · largeurs [320, 375, 1280] · thèmes ['clair'] · écrans : lecon4-carte5 · [capture](captures/chromium-lecon4-carte5-320-clair-sans-polices-final.png)
