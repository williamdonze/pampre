# Pampre — apprendre le vin en jouant

Site web pédagogique sur le vin, inspiré de **Duolingo** (parcours, XP, séries, badges) et de **GeoGuessr** (placer un vin sur une carte, score selon la distance). Public : débutant motivé, francophone. Langue du site, du contenu et des commentaires de code : **français**.

## État actuel (v1)

Fonctionnel de bout en bout :
- Accueil avec parcours en zigzag des 6 niveaux ; un niveau est verrouillé tant que le quiz du précédent n'est pas validé (seuil 80 %).
- **Niveau 1 « Les bases » complet** : 4 leçons, jeu « Lis l'étiquette » (questions générées depuis 19 étiquettes), jeu « Les bons gestes », quiz de validation (15 questions).
- **Carte libre** (France) : 117 vins/lieux sur 5 paliers de difficulté (région → sous-région → appellation → village → cru).
- Motivation : XP, 7 rangs, 14 badges, série de jours, défi quotidien (révisions + erreurs récentes + une étiquette + une carte), graphique XP sur 7 jours.
- Glossaire (54 termes) en panneau latéral ; termes cliquables dans les leçons.
- Sauvegarde dans `localStorage`, export/import par code (base64 du JSON d'état) dans Profil.
- Thème clair/sombre (auto ou forcé).

Niveaux 2 à 6 : déclarés dans `content/niveaux.json` avec `"contenu": null` → affichés « en préparation » une fois débloqués. Modules bonus : cartes « Bientôt ».

## Lancer le projet

Le site charge son contenu avec `fetch()` : il faut un serveur HTTP (un double-clic sur `index.html` en `file://` ne marche pas).

```bash
python3 -m http.server 8765
# puis ouvrir http://localhost:8765/
```

Aucune dépendance, aucun build. Seules ressources externes : Google Fonts (Baloo 2, Nunito, Cormorant Garamond), avec polices de repli.

## Arborescence

```
index.html                 Tout le code : CSS + JS (moteur). Aucun contenu pédagogique en dur.
content/
  niveaux.json             Liste des 6 niveaux, modules bonus, rangs (seuils XP), badges, seuil de validation
  niveau-1.json            Leçons, jeux et quiz du niveau 1
  etiquettes.json          Étiquettes de vrais vins pour le jeu « Lis l'étiquette »
  glossaire.json           Termes du glossaire
  carte-vins.json          Paliers de la carte, 13 régions, vins/lieux à placer, villes repères
  carte-france.json        Contours des départements déjà projetés (chemins SVG) — généré
tools/
  build-carte.py           Régénère carte-france.json depuis les GeoJSON de france-geojson
  test-parcours.py         Test Playwright : quiz complet, partie de carte, défi, profil, glossaire
docs/programme.md          Programme pédagogique complet (référence pour les niveaux à venir)
```

**Règle d'or : séparer contenu et code.** Ajouter du contenu = éditer/ajouter des JSON. Ne toucher `index.html` que pour une nouvelle mécanique (nouveau type de question, nouvelle vue).

## Architecture de `index.html`

JS vanilla, sans framework, dans un seul `<script>`. Sections dans l'ordre :
1. **Utilitaires** : `esc`, `shuffle`, `h()` (HTML → élément), `seeded()` (aléatoire déterministe pour le défi du jour), dates.
2. **Icônes** `I` (SVG inline) et **mascotte** `mascot(mood)` — Pépin, une grappe (`happy` / `wow` / `sad`).
3. **Illustrations des leçons** `IL` : fonctions SVG indexées par nom (`raisin`, `fermentation`, `thermometre`…). Une carte de leçon les référence par `"illu"`. Clé inconnue → repli sur `raisin`.
4. **Sauvegarde** : `freshState()`, `loadState()`, `save()` (clé `pampre-sauvegarde-v1`, tout en try/catch).
5. **Progression** : `gainXP()` (met aussi à jour la série), `award(badgeId)`, `checkBadges()`, `levelUnlocked()`, `rankOf()`.
6. **Toasts** (file d'attente, un à la fois) et **modale** de confirmation maison (`confirmBox`), confettis.
7. **Texte enrichi** `rich()` et **glossaire** `openGlossary(terme)`.
8. **Étiquettes** : `renderLabel()`, gabarits `LBL_ORDER` par modèle, `genLabelQuestions(n)`.
9. **Carte** : projection, `MapView()`, `scoreMap()`.
10. **Moteur de questions** `Q[type]`.
11. **Runner de session** `runSession(steps, opts)` : barre de progression, bouton Vérifier, feuille de correction, écran de fin.
12. **Lancement des activités** : `startStep`, `startGame`, `startQuiz`, `startDaily`.
13. **Vues** : `viewHome`, `viewCarte` (+ `mapSetup`, `mapRound`, `endMap`), `viewDefi`, `viewProfil`. Navigation interne en mémoire (`go(view)`), pas de routage par URL.
14. **Démarrage** `boot()` : charge tous les JSON, attribue des identifiants stables aux questions, rend la vue.

### Contrat d'un type de question

`Q.monType = (q, onChange) => ({ el, ready(), check(), key?, cleanup? })`
- `el` : élément DOM à insérer ; appeler `onChange()` quand l'état de réponse change.
- `ready()` : `true` quand le bouton Vérifier peut s'activer.
- `check()` : verrouille l'interaction, marque visuellement juste/faux, renvoie `{ ok, answer, bonus?, extra? }` (`answer` = texte de la bonne réponse affiché si faux).
- `key(i)` optionnel : raccourci clavier 1–4. `cleanup()` optionnel : retirer les écouteurs globaux.
- Ajouter le libellé du type dans `kindName` de `runSession`.

## Formats de contenu

### Niveau (`content/niveau-N.json`)

```jsonc
{
  "id": 1,
  "titre": "Les bases",
  "parcours": ["n1-l1", "n1-l2", "n1-l3", "jeu:lis-etiquette", "n1-l4", "jeu:bons-gestes", "quiz"],
  "lecons": [{
    "id": "n1-l1", "titre": "…", "duree": 4,            // minutes, 5 max
    "cartes": [{
      "titre": "…", "illu": "raisin",                   // clé de IL
      "texte": "…",                                     // voir syntaxe ci-dessous
      "exemple": { "vin": "Château d'Yquem, Sauternes", "detail": "…" },   // optionnel
      "astuce": "…",                                    // optionnel, encadré doré « Bon à savoir »
      "debat": "…"                                      // optionnel, encadré « Débat d'experts »
    }],
    "verif": [ /* 2 questions de vérification ; les ratées reviennent une fois en fin de leçon */ ]
  }],
  "jeux": [
    { "id": "lis-etiquette", "titre": "…", "description": "…", "generateur": "etiquettes", "tours": 10, "badge": "lecteur", "seuilBadge": 8 },
    { "id": "bons-gestes", "titre": "…", "description": "…", "badge": "gestes", "seuilBadge": 6, "questions": [ … ] }
  ],
  "quiz": { "titre": "…", "questions": [ … ] }
}
```

Puis dans `niveaux.json`, mettre `"contenu": "content/niveau-N.json"` pour ce niveau.

`parcours` fixe l'ordre des nœuds ; chaque nœud se débloque quand le précédent est fait. Valeurs : id de leçon, `jeu:<id>`, `quiz`.

**Syntaxe du texte** des cartes : `**gras**`, `[[terme]]` ou `[[terme|forme affichée]]` (lien glossaire, la clé doit exister dans `glossaire.json`, insensible à la casse), `\n\n` = paragraphe, `\n` = retour à la ligne.

### Types de questions

| type | champs | rendu |
|---|---|---|
| `qcm` | `question`, `choix[]`, `bonne` (index) | boutons, touches 1-4 |
| `vf` | `question` (affirmation), `bonne` (bool) | Vrai / Faux |
| `ordre` | `question`, `items[]` **dans le bon ordre** | toucher les étapes dans l'ordre |
| `assoc` | `question`, `paires[[gauche, droite]]` | toucher à gauche puis à droite, paires colorées |
| `tri` | `question`, `categories[]`, `items[[texte, indexCatégorie]]` | glisser-déposer (pointer events) ou toucher puis colonne |
| `etiquette` | `etiquette` (id), `mode`: `"qcm"` (+ `choix`, `bonne`) ou `"toucher"` (+ `cible`) | étiquette dessinée ; en mode toucher, `cible` ∈ `millesime, appellation, producteur, degre, volume, classement, embouteillage, sucre, cepage, cuvee, mention, allergene, provenance` (toucher `mention` compte pour `appellation`) |
| `indices` | `question`, `indices[]`, `choix[]`, `bonne` | dégustation à l'aveugle ; moins d'indices révélés = plus de points bonus |
| `carte` | `entry` (objet de `carte-vins.json`) | mini-carte dans la session (utilisé par le défi quotidien) |

**Toutes** les questions ont une `explication`, affichée après chaque réponse, juste ou fausse. Les ids sont attribués au démarrage (`<idLeçon>-v<i>`, `<idJeu>-<i>`, `quiz<N>-<i>`) : ne pas réordonner les questions existantes sans raison, sinon la pile d'erreurs des joueurs pointe ailleurs.

### Étiquettes (`etiquettes.json`)

`id`, `modele` (`chateau`, `bourgogne`, `alsace`, `champagne`, `moderne`, `porto`, `jura`), `teinte` (`creme`, `vert`, `noir`, `or`, `bordeaux`, `rose`), `champs` (producteur, cuvee, classement, appellation, mention, cepage, sucre, millesime, embouteillage, degre, volume), `region` (id de région de la carte ou `"hors-france"` + `pays`), `style` (une valeur de `STYLES` dans le code), `cepages`, `note` (sert d'explication). « Contient des sulfites », le logo femme enceinte et la provenance sont ajoutés automatiquement. Le générateur alterne région / style / toucher.

### Carte (`carte-vins.json`)

- `paliers` : `id` 1–5, `echelleKm`, `plein` (rayon en km donnant 5 000 points).
- `regions` : `id`, `nom`, `deps` (codes départements, pour colorer et pour le « clic dans la région »), `ancres` ([lat, lon] de vignobles réels, pour le calcul de distance au palier 1), `fiche`, `debat?`.
- `vins` : `palier`, `vin`, `detail`, `region`, `lat`, `lon`.
- `villes` : repères affichables.

**Score** : `d` = distance haversine (km). Palier 1 : clic dans un département de la région → `d = 0`, sinon min(distance au point, distance aux ancres). Puis `score = round(5000 · exp(-max(0, d - plein) / echelleKm))`. Partie = 5 manches, 25 000 max.

**Projection** : équirectangulaire locale, `x = (lon - 2.5) · cos(46.5°) · 100`, `y = (46.5 - lat) · 100`. Identique dans `tools/build-carte.py` et `PROJ` dans `index.html` — à changer ensemble. Le clic dans une région utilise `SVGGeometryElement.isPointInFill`.

## Design

- Direction validée : **mode Duolingo**, aux couleurs du vin. Boutons « 3D » (ombre basse pleine), nœuds ronds, feuille de correction verte/rouge qui monte du bas, mascotte.
- Tokens CSS dans `:root` (bordeaux `--grape`, or `--gold`, vert `--leaf`, crème `--bg`…), redéfinis pour le sombre dans `@media (prefers-color-scheme: dark)` **et** `:root[data-theme="dark"]` : toute nouvelle couleur doit exister dans les trois blocs. Les étiquettes (`--lbl-*`) sont des objets « papier » identiques dans les deux thèmes.
- Polices : Baloo 2 (titres), Nunito (texte), Cormorant Garamond (étiquettes et noms de vins).
- Mobile d'abord (colonne de 680 px max, testée à 400 px). Respecter `prefers-reduced-motion`.

## Exigences de contenu (importantes)

- **Exactitude** : vraies appellations, vrais cépages, vrais producteurs emblématiques, chiffres réglementaires exacts (UE / INAO). Pas d'approximation. Si un point est **discuté entre experts**, le dire dans un champ `debat` plutôt que de trancher.
- Coordonnées de la carte : centre de la commune ou de la parcelle ; vérifier avant d'ajouter.
- Ton : chaleureux, un peu d'humour, jamais condescendant. Tutoiement.
- Leçons courtes : 5 min max, 4 à 6 cartes, au moins un vin réel cité en exemple par leçon.
- Questions variées (mélanger les types) ; quiz de validation ≈ 15 questions couvrant toutes les leçons du niveau.
- Les questions des quiz ne doivent pas pouvoir être réussies sans avoir suivi les leçons, mais restent justes et non piégeuses.

## Tester

```bash
python3 -m http.server 8765 &
pip install playwright && playwright install chromium
python3 tools/test-parcours.py     # captures d'écran dans captures/
```

Le test répond correctement à tout le quiz à partir des données : s'il affiche `WRONG`, une question ou son corrigé est incohérent. Après un ajout de contenu, vérifier aussi que tous les `[[termes]]` existent dans le glossaire et que chaque JSON est valide.

## Prochaines étapes prévues

Un niveau à la fois, en enrichissant le contenu à chaque fois (voir `docs/programme.md`) :
1. **Niveau 2 — Les cépages** : profils (arômes, acidité, tanins, corps), mono-cépage vs assemblage. Jeux : « Quel cépage ? » depuis une description aromatique (type `indices` ou `qcm`) ; associer cépage et région sur la carte (nouveau mode de carte possible : placer le berceau d'un cépage).
2. **Niveau 3 — De la vigne au verre** : terroir, climats, vinifications, effervescence, élevage, bio/biodynamie/nature. Jeux : remise en ordre des étapes, « climat chaud ou froid ? ».
3. **Niveau 4 — France** : système des appellations, les 13 régions une par une, hiérarchies (rive gauche/droite, climats bourguignons). S'appuie sur la Carte libre existante ; enrichir `carte-vins.json` (davantage d'appellations, villages, crus).
4. **Niveau 5 — Monde** : activer le bouton « Monde » de la Carte libre (fond de carte mondial à générer, ex. Natural Earth, même principe que `build-carte.py` avec une autre projection), classifications DOCG, DOCa, Prädikat… Défi quotidien avec classement (nécessiterait un stockage partagé).
5. **Niveau 6 — Dégustation et accords** : jeu « Sommelier à l'aveugle » (type `indices`, déjà prêt).
6. **Modules bonus** : histoire, économie, cave, certifications.

Idées d'amélioration du moteur : sons optionnels, révision espacée plus fine que la pile d'erreurs actuelle (60 ids max), filtre de difficulté dans la carte par région.

## Limites connues

- Zones régionales de la carte = départements entiers (approximation signalée dans le jeu). Le Gard est rattaché au Rhône et au Languedoc.
- Degré et millésime des étiquettes indicatifs ; mise en page redessinée (pas les vraies étiquettes).
- Sauvegarde locale à l'appareil (d'où l'export/import par code).
- Fond de carte : france-geojson (Grégoire David), données IGN, Licence Ouverte Etalab — mention à conserver.
