# Pampre — apprendre le vin en jouant

Site web pédagogique sur le vin, inspiré de **Duolingo** (parcours, XP, séries, badges) et de **GeoGuessr** (placer un vin sur une carte, score selon la distance). Public : débutant motivé, francophone. Langue du site, du contenu et des commentaires de code : **français**.

## État actuel (v2 : les 6 niveaux)

Fonctionnel de bout en bout :
- Accueil avec parcours en zigzag des 6 niveaux ; un niveau est verrouillé tant que le quiz du précédent n'est pas validé (seuil 80 %).
- **Les 6 niveaux sont complets** (détail dans `docs/programme.md`) : 1 Les bases, 2 Les cépages, 3 De la vigne au verre, 4 La France du vin, 5 Le vin dans le monde, 6 Déguster et marier. Soit 36 leçons, 17 jeux et 6 quiz de validation (15 à 18 questions, avec des révisions des niveaux précédents).
- **Carte libre**, deux fonds : **France** (174 lieux sur 5 paliers : région → sous-région → appellation → village → cru) et **Monde** (14 pays, 82 lieux sur 3 paliers : pays → région → appellation).
- **Carte du jour** : 5 lieux (France et monde) tirés d'après la date seule, donc les mêmes pour tous ; classement personnel sur le premier essai, résultat à copier pour se comparer entre amis.
- Motivation : XP, 7 rangs, 30 badges, série de jours, défi quotidien (révisions + erreurs récentes + une étiquette + un vin à placer, du monde un jour sur trois une fois le niveau 5 ouvert), graphique XP sur 7 jours, **classement personnel** (vue Défi : défis relevés, sans-faute, meilleure série, moyennes, meilleures cartes du jour). Aucun serveur, aucun compte.
- Jeu « Lis l'étiquette » : questions générées depuis 28 étiquettes (France et 7 pays).
- Glossaire (138 termes) en panneau latéral ; termes cliquables dans les leçons.
- Sauvegarde dans `localStorage`, export/import par code (base64 du JSON d'état) dans Profil.
- Thème clair/sombre (auto ou forcé).
- **Appli sur l'écran d'accueil** (PWA) : sur téléphone et tablette, bandeau d'invitation à l'accueil et section dans Profil ; bouton « Installer » natif sur Android (Chrome, Edge, Samsung Internet), mode d'emploi adapté au navigateur ailleurs (iOS, Firefox, applis Instagram/Facebook) ; jouable hors connexion. Doc : `docs/installer.md`.

Modules bonus (histoire, économie, cave, certifications) : cartes « Bientôt ».

## Lancer le projet

Le site charge son contenu avec `fetch()` : il faut un serveur HTTP (un double-clic sur `index.html` en `file://` ne marche pas).

```bash
python3 -m http.server 8765
# puis ouvrir http://localhost:8765/
```

Aucune dépendance, aucun build. Seules ressources externes : Google Fonts (Baloo 2, Nunito, Cormorant Garamond), avec polices de repli. L'installation sur l'écran d'accueil et le service worker demandent HTTPS (ou `localhost`).

## Arborescence

```
index.html                 Tout le code : CSS + JS (moteur). Aucun contenu pédagogique en dur.
manifest.webmanifest       Manifeste de l'appli (nom, couleurs, icônes, affichage plein écran)
sw.js                      Service worker « réseau d'abord » (hors connexion) ; changer CACHE pour vider les copies
icones/                    Icônes de l'appli (192, 512, maskable, apple-touch-icon) — générées
content/
  niveaux.json             Liste des 6 niveaux, modules bonus, rangs (seuils XP), badges, seuil de validation
  niveau-1.json … niveau-6.json   Leçons, jeux et quiz de chaque niveau
  etiquettes.json          Étiquettes de vrais vins pour le jeu « Lis l'étiquette »
  glossaire.json           Termes du glossaire
  carte-vins.json          Carte France : paliers, 13 régions, lieux à placer, villes repères
  carte-france.json        Contours des départements déjà projetés (chemins SVG) — généré
  carte-monde-vins.json    Carte Monde : paliers, 14 pays (zones), lieux à placer, villes repères
  carte-monde.json         Contours des pays déjà projetés (chemins SVG) — généré
tools/
  build-carte.py           Régénère carte-france.json depuis les GeoJSON de france-geojson
  build-monde.py           Régénère carte-monde.json depuis Natural Earth 1:50m (domaine public)
  build-icones.py          Régénère icones/ (Pépin sur fond crème) via Chromium
  test-parcours.py         Test Playwright : les 6 quiz, Carte libre, Carte du jour, défi, profil, glossaire
  valider-contenu.py       Validation des JSON de contenu (voir « Tests »)
  audit.py                 Audit visuel et fonctionnel multi-navigateurs (voir « Tests »)
  audit-checks.js, audit_fonctionnel.py, audit_webkit.py, audit-cadre.html, comparer-captures.py
audit/                     RAPPORT.md (bugs A-01…A-37 et leur statut), résumés et captures d'audit
docs/programme.md          Programme pédagogique : contenu des 6 niveaux et modules bonus
docs/installer.md          Ajouter Pampre à l'écran d'accueil : marche à suivre par appareil, fonctionnement
sources/                   Données brutes téléchargées pour les scripts build-* (non versionné)
```

**Règle d'or : séparer contenu et code.** Ajouter du contenu = éditer/ajouter des JSON. Ne toucher `index.html` que pour une nouvelle mécanique (nouveau type de question, nouvelle vue).

## Architecture de `index.html`

JS vanilla, sans framework, dans un seul `<script>`. Sections dans l'ordre :
1. **Utilitaires** : `esc`, `shuffle`, `h()` (HTML → élément), `seeded()` (aléatoire déterministe pour le défi du jour), dates.
2. **Icônes** `I` (SVG inline) et **mascotte** `mascot(mood)` — Pépin, une grappe (`happy` / `wow` / `sad`).
3. **Illustrations des leçons** `IL` : fonctions SVG indexées par nom (`raisin`, `fermentation`, `thermometre`…). Une carte de leçon les référence par `"illu"` ; la fonction reçoit la carte entière, ce qui permet des illustrations pilotées par le contenu (voir « Illustrations pilotées par la carte »). Clé inconnue → repli sur `raisin`. Aide `svgT(x, y, texte, {s, w, f, c, a})` pour les textes. Couleurs : variables CSS (`var(--ink)`, `var(--grape-btn)`…), jamais de couleur de texte en dur sur un fond de thème.
4. **Sauvegarde** : `freshState()`, `normaliser()` (redonne à chaque champ son type : sauvegarde abîmée, ancienne ou importée), `loadState()`, `save()` (clé `pampre-sauvegarde-v1`, tout en try/catch).
5. **Progression** : `gainXP()` (met aussi à jour la série), `award(badgeId)`, `checkBadges()`, `levelUnlocked()`, `rankOf()`.
6. **Toasts** (file d'attente, un à la fois, en haut de l'écran), **modale** de confirmation maison (`confirmBox`, Échap = Rester), confettis. `majCalques()` rend inerte tout ce qui est sous le calque du dessus (session, glossaire, modale) : à appeler à chaque ouverture ou fermeture de calque.
   **Appli sur l'écran d'accueil** : `appareil()` (iOS/Android, navigateur, appli intégrée, déjà installée), invite native gardée depuis `beforeinstallprompt`, `etapesInstall()` / `aideInstall()` (mode d'emploi), `installer()`, `panneauInstall()` (bandeau de l'accueil, masqué 14 jours par `ST.installPlusTard`), enregistrement de `sw.js`. Jamais proposé sur ordinateur.
7. **Texte enrichi** `rich()` et **glossaire** `openGlossary(terme)`.
8. **Étiquettes** : `renderLabel()`, gabarits `LBL_ORDER` par modèle, `genLabelQuestions(n)`.
9. **Carte** : projections (`proj` France, `projMonde`), **fonds** `FONDS.france` / `FONDS.monde` (`fondDe(id)` : géométrie, projection, cadrage, bornes de zoom, zones, lieux, paliers, couleurs), `MapView(host, { fond, … })`, `scoreMap(entry, …)` (le fond vient de `entry.fond`, France par défaut), `noterZone()` (badges Tour de France / Tour du monde).
10. **Moteur de questions** `Q[type]`.
11. **Runner de session** `runSession(steps, opts)` : barre de progression, bouton Vérifier, feuille de correction, écran de fin.
12. **Lancement des activités** : `startStep`, `startGame` (un jeu à questions fixes tire `tours` questions au hasard), `startQuiz`, `startDaily` (`buildDaily`).
13. **Vues** : `viewHome`, `viewCarte` (+ `mapSetup`, `mapRound`, `endMap` ; `carteDuJour()`, `finCarteDuJour()`), `viewDefi` (classement personnel : `statsDefi()`, `rangCarteJour()`), `viewProfil`. Navigation interne en mémoire (`go(view)`), pas de routage par URL.
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
    { "id": "bons-gestes", "titre": "…", "description": "…", "tours": 8, "badge": "gestes", "seuilBadge": 6, "questions": [ … ] }   // tours : nombre de questions tirées (toutes par défaut)
  ],
  "quiz": { "titre": "…", "questions": [ … ] }
}
```

Puis dans `niveaux.json`, mettre `"contenu": "content/niveau-N.json"` pour ce niveau.

`parcours` fixe l'ordre des nœuds ; chaque nœud se débloque quand le précédent est fait. Valeurs : id de leçon, `jeu:<id>`, `quiz`.

**Syntaxe du texte** des cartes : `**gras**`, `[[terme]]` ou `[[terme|forme affichée]]` (lien glossaire, la clé doit exister dans `glossaire.json`, insensible à la casse), `\n\n` = paragraphe, `\n` = retour à la ligne. Pas d'italique : un `*mot*` s'afficherait tel quel (le validateur le signale).

**Illustrations pilotées par la carte** (champs supplémentaires de la carte de leçon) :
- `"illu": "profil"` + `"profil": { "robe", "acidite", "tanins", "corps", "aromes", "garde" }` (entiers 0–5, axes facultatifs) : fiche d'un cépage.
- `"illu": "carte-region"` + `"region"`, `"lieux": ["Nom", ["Nom", "g", "Nom affiché"]…]`, `"villes"`, `"cadre": "lieux"` (facultatif, sinon toute la région), `"fond": "monde"` (facultatif) : mini-carte tracée avec les vrais contours ; les noms viennent de `carte-vins.json` ou `carte-monde-vins.json` ; le côté (`d`, `g`, `h`, `b`, `hd`, `hg`, `bd`, `bg`) est une préférence, les étiquettes se placent automatiquement sans se chevaucher.
- `"illu": "etages"` + `"etages": [["titre", "sous-titre"]…]` (5 au plus, du sommet à la base) : pyramide (classements, hiérarchies).

**Révisions** : chaque leçon et chaque quiz rappelle des notions des niveaux précédents (« révision du niveau N ») ; un renvoi vers un niveau futur (« on y reviendra au niveau 4 ») doit être tenu par ce niveau.

### Types de questions

| type | champs | rendu |
|---|---|---|
| `qcm` | `question`, `choix[]`, `bonne` (index) | boutons, touches 1-4 |
| `vf` | `question` (affirmation), `bonne` (bool) | Vrai / Faux |
| `ordre` | `question`, `items[]` **dans le bon ordre** | toucher les étapes dans l'ordre |
| `assoc` | `question`, `paires[[gauche, droite]]` | toucher à gauche puis à droite, paires colorées |
| `tri` | `question`, `categories[]`, `items[[texte, indexCatégorie]]` | glisser-déposer (pointer events) ou toucher puis colonne |
| `etiquette` | `etiquette` (id), `mode`: `"qcm"` (+ `choix`, `bonne`) ou `"toucher"` (+ `cible`) | étiquette dessinée ; en mode toucher, `cible` ∈ `millesime, appellation, producteur, degre, volume, classement, embouteillage, sucre, cepage, cuvee, mention, allergene, provenance` (toucher `mention` compte pour `appellation`) |
| `indices` | `question`, `indices[]` (autant que voulu), `choix[]`, `bonne` | dégustation à l'aveugle ; moins d'indices révélés = plus de points bonus |
| `carte` | `entry` (copie d'un lieu de `carte-vins.json`, ou de `carte-monde-vins.json` avec `"fond": "monde"`) | mini-carte dans la session ; réussi à partir de 3 000 points. Les coordonnées doivent être identiques à celles du fichier de carte (le validateur le vérifie) |

**Toutes** les questions ont une `explication`, affichée après chaque réponse, juste ou fausse. Le moteur affiche les choix dans l'ordre des données : **varier la position de la bonne réponse** (le validateur avertit si plus de la moitié sont au même rang). Les ids sont attribués au démarrage (`<idLeçon>-v<i>`, `<idJeu>-<i>`, `quiz<N>-<i>`) : ne pas réordonner les questions existantes sans raison, sinon la pile d'erreurs des joueurs pointe ailleurs.

### Étiquettes (`etiquettes.json`)

`id`, `modele` (`chateau`, `bourgogne`, `alsace`, `champagne`, `moderne`, `porto`, `jura`), `teinte` (`creme`, `vert`, `noir`, `or`, `bordeaux`, `rose`), `champs` (producteur, cuvee, classement, appellation, mention, cepage, sucre, millesime, embouteillage, degre, volume), `region` (id de région de la carte ou `"hors-france"` + `pays`, une valeur de `PAYS_VIN` dans le code), `style` (une valeur de `STYLES` dans le code), `cepages`, `note` (sert d'explication). « Contient des sulfites », le logo femme enceinte et la provenance sont ajoutés automatiquement. Le générateur alterne région / style / toucher.

### Carte (`carte-vins.json`)

- `paliers` : `id` 1–5, `echelleKm`, `plein` (rayon en km donnant 5 000 points).
- `regions` : `id`, `nom`, `deps` (codes départements, pour colorer et pour le « clic dans la région »), `ancres` ([lat, lon] de vignobles réels, pour le calcul de distance au palier 1), `fiche`, `debat?`.
- `vins` : `palier`, `vin`, `detail`, `region`, `lat`, `lon`.
- `villes` : repères affichables.

**Score** : `d` = distance haversine (km). Palier 1 : clic dans un département de la région → `d = 0`, sinon min(distance au point, distance aux ancres). Puis `score = round(5000 · exp(-max(0, d - plein) / echelleKm))`. Partie = 5 manches, 25 000 max.

**Projection** : équirectangulaire locale, `x = (lon - 2.5) · cos(46.5°) · 100`, `y = (46.5 - lat) · 100`. Identique dans `tools/build-carte.py` et `PROJ` dans `index.html` — à changer ensemble. Le clic dans une région utilise `SVGGeometryElement.isPointInFill`.

### Carte du monde (`carte-monde-vins.json`, `carte-monde.json`)

Même format que la carte France : `paliers` (1 Pays, 2 Région, 3 Appellation), `regions` = les pays (`deps` = codes ADM0 de Natural Earth, ex. `"ITA"`), `vins`, `villes`. Au palier Pays, toucher le bon pays rapporte le maximum. Lieux placés au centre de la localité d'après GeoNames ; chaque lieu doit tomber dans son pays au palier 1 (contrôlé par le validateur).

**Projection monde** : équirectangulaire, `x = lon · cos(35°) · 10`, `y = -lat · 10`. Identique dans `tools/build-monde.py` et `PROJ_MONDE` dans `index.html` — à changer ensemble. `build-monde.py` simplifie les contours (Douglas-Peucker), retire l'Antarctique et les petits territoires à plus de 30° de longitude du corps principal d'un pays (outre-mer français, île de Pâques, Hawaï, Chatham) pour que chaque pays reste cadrable.

**Carte du jour** : `carteDuJour(date)` tire, avec `seeded("carte-du-jour-" + date)`, un lieu France des paliers 1, 2, 3 et un lieu Monde des paliers 1, 2. Elle n'est identique pour tous que si tous ont la même version du contenu. Résultats dans `ST.carteJour[date] = { s: premier essai, m: meilleur, r: scores des manches }`.

## Design

- Direction validée : **mode Duolingo**, aux couleurs du vin. Boutons « 3D » (ombre basse pleine), nœuds ronds, feuille de correction verte/rouge qui monte du bas, mascotte.
- Tokens CSS dans `:root` (bordeaux `--grape`, or `--gold`, vert `--leaf`, crème `--bg`…), redéfinis pour le sombre dans `@media (prefers-color-scheme: dark)` **et** `:root[data-theme="dark"]` : toute nouvelle couleur doit exister dans les trois blocs.
- Contraste AA : les couleurs vives servent de fond ou de décor ; pour du **texte**, utiliser les jetons « encre » (`--grape-ink`, `--leaf-ink`, `--bad-ink`, `--gold-ink`, `--muted-ink`, `--flame-ink`) ; pour un **fond sous du texte**, `--grape-btn`, `--leaf-btn`, `--bad-btn` avec `--on-leaf`, `--on-bad`, `--on-gold`, `--on-plum`. Anneau de focus : `--focus`. Vérifier avec `tools/audit.py`.
- Les toasts s'affichent en haut ; sous 360 px plusieurs blocs passent sur une colonne ; zones tactiles ≥ 44 px (champs d'étiquette agrandis au doigt via `@media (pointer:coarse)`). Les étiquettes (`--lbl-*`) sont des objets « papier » identiques dans les deux thèmes.
- Polices : Baloo 2 (titres), Nunito (texte), Cormorant Garamond (étiquettes et noms de vins).
- Mobile d'abord (colonne de 680 px max, testée à 400 px). Respecter `prefers-reduced-motion`.

## Exigences de contenu (importantes)

- **Exactitude** : vraies appellations, vrais cépages, vrais producteurs emblématiques, chiffres réglementaires exacts (UE / INAO). Pas d'approximation. Si un point est **discuté entre experts**, le dire dans un champ `debat` plutôt que de trancher.
- Coordonnées de la carte : centre de la commune ou de la parcelle ; vérifier avant d'ajouter.
- Ton : chaleureux, un peu d'humour, jamais condescendant. Tutoiement.
- Leçons courtes : 5 min max, 4 à 6 cartes, au moins un vin réel cité en exemple par leçon.
- Questions variées (mélanger les types) ; quiz de validation de 15 à 18 questions couvrant toutes les leçons du niveau, dont 2 ou 3 révisions des niveaux précédents.
- Chiffres réglementaires et faits vérifiés sur des sources primaires (INAO, cahiers des charges, Légifrance, organismes officiels) avant d'écrire.
- Les questions des quiz ne doivent pas pouvoir être réussies sans avoir suivi les leçons, mais restent justes et non piégeuses.

## Tests

Installation (une fois) : `pip install playwright selenium pillow && playwright install chromium`. Pour WebKit (moteur de Safari) sous Linux sans le navigateur de Playwright : `apt install webkit2gtk-driver xvfb`, l'audit lance Xvfb tout seul.

```bash
python3 tools/valider-contenu.py          # à lancer après CHAQUE modification de content/*.json
python3 -m http.server 8765 &             # les scripts suivants le lancent eux-mêmes s'il manque
python3 tools/test-parcours.py            # parcours rapide : quiz complet, carte, défi, profil, glossaire
python3 tools/audit.py --fonctionnel --navigateurs chromium,webkit   # ~50 tests fonctionnels (≈ 2 min)
python3 tools/audit.py                    # audit visuel complet Chromium (≈ 35 min)
python3 tools/audit.py --ecrans lecon1,q-tri --largeurs 320,375 --themes clair,sombre-systeme   # ciblé
```

- **`tools/valider-contenu.py`** : JSON valides et conformes aux formats ci-dessus, `[[termes]]` et « voir » du glossaire, `illu` existantes (et leurs champs `profil`, `carte-region`, `etages`), astérisques isolés, étiquettes et `cible` présentes, pays des étiquettes, index `bonne` et leur répartition, catégories du tri, `tours` et `seuilBadge` atteignables, régions, vins du palier 1 dans leur région, questions `carte` identiques au fichier de carte, carte du monde (codes pays, lieux dans leur pays), identifiants en double, explications manquantes. Code de sortie 1 en cas d'erreur ; les ⚠ sont à relire (approximations connues de la carte, leçon sans encadré Exemple…).
- **`tools/test-parcours.py`** : répond juste aux six quiz à partir des données (y compris les questions carte, touchées à la position réelle, et les étiquettes), puis joue la Carte libre et la Carte du jour ; s'il affiche `WRONG`, une question ou son corrigé est incohérent.
- **`tools/audit.py`** (+ `tools/audit-checks.js`, exécuté dans la page) : parcourt 113 écrans (accueil, leçons carte par carte, chaque type de question avant / juste / faux, 19 étiquettes, fins de session, carte, défi, profil, glossaire, toasts, modale) × 6 largeurs (320 → 1920) × 4 thèmes (clair, sombre système, sombre forcé, clair forcé) × 5 états de joueur injectés dans `pampre-sauvegarde-v1`. Contrôles : défilement horizontal, texte qui déborde ou coupé, texte SVG hors du viewBox, contraste WCAG AA, contenu caché sous la barre d'onglets / la feuille de correction / un toast, zones tactiles (`--cibles-tactiles`). Sorties : `audit/resultats*.json` (bruts, non versionnés), `audit/resume*.md` (regroupés), `audit/captures/` (éléments fautifs entourés en rouge). Options utiles : `--navigateurs chromium,webkit`, `--sans-polices` (Google Fonts bloqué), `--mouvement-reduit`, `--captures toutes|cles|aucune`, `--suffixe nom` (garder une passe à côté d'une autre).
- **`tools/audit.py --fonctionnel`** (`tools/audit_fonctionnel.py`, `tools/audit_webkit.py`) : progression et XP, seuil de 80 %, badges, série avec horloge et fuseaux simulés, défi quotidien, glisser-déposer souris et tactile, carte (clic/glissé, zoom, pincement, scores recalculés, détection de région), clavier et focus, robustesse (sauvegardes corrompues, `localStorage` indisponible, contenu manquant, double clic). Résultats dans `audit/fonctionnel.json`.
- **`tools/comparer-captures.py AVANT APRES SORTIE`** : assemble deux captures côte à côte pour vérifier une correction.

Après une correction visuelle : relancer l'audit sur l'écran concerné (`--ecrans`) avec `--suffixe apres-X`, et comparer les captures. Le rapport d'audit initial et le suivi des corrections sont dans `audit/RAPPORT.md`.

## Prochaines étapes possibles

Les 6 niveaux du programme sont faits. Pistes :
1. **Modules bonus** (`docs/programme.md`) : histoire, économie, cave, certifications. Chacun peut suivre le format d'un niveau (`content/bonus-*.json`) et réutiliser les mêmes types de questions.
2. **Enrichir le contenu** : davantage de lieux sur les cartes (villages, crus, régions du monde), d'étiquettes, de vins pour « Sommelier à l'aveugle ».
3. **Moteur** : sons optionnels, révision espacée plus fine que la pile d'erreurs actuelle (60 ids max), filtre de difficulté dans la carte par région, mise en ligne statique en HTTPS (GitHub Pages ou Netlify, nécessaire pour l'installation sur l'écran d'accueil) avec aperçu de partage (balises Open Graph).
4. **Classement entre joueurs** : volontairement absent (choix : classement personnel sans serveur). Il demanderait un service hébergé, des comptes ou pseudos (données personnelles, RGPD, modération) et une protection contre la triche, les scores étant calculés dans le navigateur.

Note : au niveau 1, les bonnes réponses sont presque toutes en 2e position (avertissement du validateur) ; les rééquilibrer ne change ni les textes ni les identifiants.

## Limites connues

- Zones régionales de la carte = départements entiers (approximation signalée dans le jeu). Départements partagés : le Gard (Rhône et Languedoc), le Rhône (Beaujolais et Rhône, pour Côte-Rôtie et Condrieu), la Saône-et-Loire (Bourgogne et Beaujolais, pour Moulin-à-Vent). Un département partagé compte pour chaque région au clic et prend la couleur de la première qui le cite.
- Degré et millésime des étiquettes indicatifs ; mise en page redessinée (pas les vraies étiquettes).
- Sauvegarde et classement locaux à l'appareil (d'où l'export/import par code).
- Carte du monde simplifiée : quelques lieux côtiers ou insulaires (Oia à Santorin, Rías Baixas) tombent juste hors du contour ; sans effet au-delà du palier 1, où seul compte la distance.
- Fond de carte France : france-geojson (Grégoire David), données IGN, Licence Ouverte Etalab — mention à conserver. Fond Monde : Natural Earth (domaine public) ; localités : GeoNames (CC BY 4.0).
