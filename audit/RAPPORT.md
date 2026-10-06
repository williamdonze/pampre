# Audit de Pampre : rapport

Date : 5 octobre 2026 · Version auditée : commit `439e910` (import initial).

**Mise à jour après corrections** : les 37 bugs sont corrigés (un commit par bug, identifiant dans le message). Chaque bug porte son statut ci-dessous ; bilan chiffré en section 7, comparaisons avant/après dans `audit/captures/avant-apres-A-*.png`. Le contenu pédagogique n'a pas été modifié (section 4 : à ta décision).

## 1. Méthode

**Outillage (réutilisable, dans `tools/`)**

| Outil | Rôle |
|---|---|
| `tools/audit.py` | Parcourt 113 écrans × 6 largeurs × 4 thèmes × 5 états de joueur, lance des contrôles automatiques et prend les captures dans `audit/captures/`. Options `--navigateurs`, `--sans-polices`, `--mouvement-reduit`, `--cibles-tactiles`, `--fonctionnel`. |
| `tools/audit-checks.js` | Contrôles exécutés dans la page : défilement horizontal, texte qui déborde ou est coupé, élément hors écran, texte SVG hors du viewBox, contraste WCAG AA (texte HTML et SVG, fonds composés), zones tactiles < 44 px, contenu caché sous la barre d'onglets, la feuille de correction ou un toast. |
| `tools/audit_fonctionnel.py` | 43 tests fonctionnels (progression, série avec horloge simulée, défi, glisser-déposer souris et tactile, carte, clavier, robustesse). |
| `tools/audit_webkit.py` | Tests rejoués sous WebKit. |
| `tools/valider-contenu.py` | Validation des JSON de contenu (section 4). |
| `tools/audit-cadre.html` | Cadre utilisé sous WebKit, dont la fenêtre ne descend pas sous 447 px : l'appli y est chargée dans une iframe à la largeur voulue. |

**Navigateurs**
- **Chromium** 140 (Playwright) : matrice complète, soit 16 515 constats bruts dans `audit/resultats.json`, résumé dans `audit/resume.md`.
- **WebKit** (WebKitGTK 2.52, le moteur de Safari, piloté par WebKitWebDriver sous Xvfb) : matrice sur 320 / 375 / 768 / 1280 px et les 4 thèmes, résultats dans `audit/webkit/`, plus 5 tests fonctionnels.
- **Firefox** : non testé, voir section 6.

**Matrice**
- Largeurs : 320, 375, 400, 768, 1280 et 1920 px.
- Thèmes : clair, sombre système, sombre forcé, clair forcé (sur un système sombre).
- États de joueur injectés dans `pampre-sauvegarde-v1` :
  - nouveau joueur ;
  - milieu du niveau 1 ;
  - niveau 1 validé ;
  - vétéran (123 456 XP, 365 jours de série, tous les badges) ;
  - pile d'erreurs pleine (60 ids).
- Passes complémentaires :
  - Google Fonts bloqué (`resultats-sans-polices.json`) ;
  - toasts (`resultats-toasts.json`) ;
  - paysage 667 × 375 ;
  - `prefers-reduced-motion`.

**Lecture des captures**
- Les captures `chromium-<écran>-<largeur>-<thème>.png` sont les captures clés.
- Quand un contrôle trouve un défaut nouveau, les éléments fautifs sont **entourés en rouge** sur la capture.
- Les captures `preuve-*.png` viennent des tests fonctionnels.
- Les captures « page entière » de Chromium dessinent la barre du haut et la barre d'onglets au milieu de la page : c'est un artefact de la capture, pas un bug.

**Relancer**
```bash
python3 tools/audit.py                          # matrice visuelle Chromium (≈ 35 min)
python3 tools/audit.py --navigateurs webkit     # WebKit
python3 tools/audit.py --fonctionnel --navigateurs chromium,webkit
python3 tools/valider-contenu.py
```

---

## 2. Bugs

Gravité :
- **bloquant** : on ne peut pas progresser ;
- **majeur** : visible et gênant ;
- **mineur** ;
- **cosmétique**.

Sauf mention contraire, « tous navigateurs » veut dire Chromium **et** WebKit.

### A-01 · Une sauvegarde mal formée bloque l'appli pour toujours — **bloquant**
- **Statut** : ✅ corrigé — commit `2620d1e`. Avant/après : [A-01](captures/avant-apres-A-01.png). Test : « Robustesse : sauvegardes corrompues ou anciennes » (8 cas).
- **Où** : démarrage, puis tous les écrans. Toutes largeurs, tous thèmes, tous navigateurs.
- **Reproduire** :
  1. Profil › Importer le code d'un objet `{"xp":10,"streak":null}` (base64), ou de `{"xp":10,"quiz":null}`. Le seul contrôle de l'import est « `xp` est un nombre ».
  2. Recharger la page.
- **Attendu** : le code est refusé, ou les champs manquants sont réparés.
- **Observé** : exception `Cannot read properties of null (reading 'last')`. L'appli reste sur « On débouche les bouteilles… » à chaque visite. Le joueur ne peut s'en sortir qu'en effaçant les données du site.
- **Variantes** :
  - un `map` sans `regions` (forme d'une version antérieure) fait planter la fin de **chaque** leçon (`checkBadges`) ;
  - un `mistakes` qui n'est pas un tableau bloque la session.
- **Capture** : [preuve-sauvegarde-corrompue.png](captures/preuve-sauvegarde-corrompue.png).
- **Cause** :
  - `index.html` › `loadState()` fusionne avec `Object.assign` (fusion superficielle, sans vérifier les types) ;
  - l'import (`viewProfil`, `data-a="import"`) ne valide que `xp` ;
  - aucune garde dans `boot()` / `render()`.
- **Correctif proposé** :
  - une fonction `normaliser(obj)` qui part de `freshState()`, fusionne champ par champ et remplace tout champ du mauvais type (objet, tableau, nombre) ;
  - l'utiliser dans `loadState()` et à l'import ;
  - entourer le premier `render()` d'un `try/catch` qui propose « Réinitialiser ».

### A-02 · La feuille de correction cache la fin de la question corrigée, sans pouvoir défiler — **majeur**
- **Statut** : ✅ corrigé — commit `4f07629`. La feuille réserve sa hauteur sous la question ; tout se fait défiler. Avant/après : [A-02](captures/avant-apres-A-02.png)
- **Où** : toute session, après « Vérifier ».
  - qcm et indices : 4ᵉ choix ;
  - tri : colonnes du bas ;
  - association : dernières paires ;
  - étiquette : pied de l'étiquette ;
  - carte.
  - Toutes largeurs (avec explication longue, même à 1280 px), tous thèmes, tous navigateurs ; le pire est à 320 px, où la feuille couvre ~55 % de l'écran.
- **Reproduire** : quiz › question 12 « Quelle est la différence entre carafer et décanter ? », répondre, Vérifier. Ou jeu « Les bons gestes » › tri des températures, se tromper.
- **Attendu** : on peut voir toute la correction en couleur (la bonne réponse en vert, ses erreurs en rouge, « Pauillac → 16 à 18 °C »…).
- **Observé** :
  - la feuille est en `position:fixed` par-dessus le bas de la question ;
  - `.s-body` n'a que 28 px de marge basse, donc même en défilant au maximum, des éléments restent dessous ;
  - le contrôle `masque-par-feuille` trouve 158 cas sur 15 écrans de question.
- **Captures** : [tri à 320 px](captures/chromium-q-tri-faux-320-clair.png) · [qcm à 375 px](captures/chromium-q-qcm-juste-375-clair.png) · [association](captures/chromium-q-assoc-faux-375-clair.png) · [carte](captures/chromium-q-carte-faux-375-clair.png).
- **Cause** : `index.html` › CSS `.sheet` (fixed) + `.s-body .wrap{padding-block:12px 28px}` ; `runSession` › `verify()` ne réserve pas la place de la feuille.
- **Correctif proposé** : à l'ouverture de la feuille, donner à `.s-body` une marge basse égale à sa hauteur (mesurée, ou suivie avec un `ResizeObserver`), puis faire défiler pour garder la question visible. La feuille garde son animation et son style.

### A-03 · Thème sombre : la correction (« Pas tout à fait », bonne réponse, choix faux ou justes) est presque illisible — **majeur**
- **Statut** : ✅ corrigé — commit `98c8483`. Jetons --leaf-ink / --bad-ink : 7,8:1 et 7,0:1 en sombre. Avant/après : [A-03](captures/avant-apres-A-03.png)
- **Où** : feuille de correction, `.choice.ok/.ko`, `.chip.ok/.ko`, réponses du tri et de l'association. Sombre système et sombre forcé, toutes largeurs, tous navigateurs.
- **Reproduire** : Profil › Apparence › Sombre, puis répondre faux à une question.
- **Attendu** : contraste ≥ 4,5:1 (≥ 3:1 pour le titre de 24 px).
- **Observé** :

  | Élément | Couleurs | Contraste |
  |---|---|---|
  | Titre « Pas tout à fait » et bonne réponse | `#A9372F` sur `#3C1A18` | 2,42:1 |
  | Réponses justes (`--leaf-deep` sur `--leaf-soft`) | `#4F8A12` sur `#1F3014` | 3,34:1 |

- **Capture** : [chromium-q-qcm-faux-320-sombre-systeme.png](captures/chromium-q-qcm-faux-320-sombre-systeme.png).
- **Cause** : dans les blocs sombres de `:root`, `--bad-deep` et `--leaf-deep` servent à la fois d'ombre de bouton (foncée) et de couleur de texte.
- **Correctif proposé** :
  - ajouter deux jetons de texte, `--bad-ink` et `--leaf-ink`, dans les trois blocs de thème ;
  - en clair, ils valent les couleurs actuelles ; en sombre, ce sont des teintes claires de la même famille, par exemple `#FF8F86` et `#9BE05A` ;
  - les utiliser pour le texte de `.sheet`, `.choice.ok/.ko` et `.chip.ok/.ko`.

### A-04 · La bulle « Commencer / Continuer » recouvre le libellé du nœud précédent — **majeur**
- **Statut** : ✅ corrigé — commit `48eb83a`. Avant/après : [A-04](captures/avant-apres-A-04.png)
- **Où** : accueil, nœud en cours dès qu'il y a un nœud au-dessus. 320, 375 et 768 px mesurés (recouvrement ≈ 3 000 px²), tous thèmes, tous navigateurs.
- **Reproduire** : terminer les leçons 1 et 2, puis revenir à l'accueil.
- **Attendu** : « Les couleurs et les styles · 5 min » lisible.
- **Observé** : la deuxième ligne du libellé et la durée sont cachées sous la bulle « CONTINUER ».
- **Capture** : [preuve-bulle-continuer.png](captures/preuve-bulle-continuer.png).
- **Cause** : CSS `.node-wrap .start{position:absolute;top:-44px}` alors que `.path{gap:18px}`. La bulle déborde dans l'espace du nœud précédent.
- **Correctif proposé** : réserver la place de la bulle sur le nœud courant (`.node-wrap:has(.start){margin-top:34px}`, ou une classe ajoutée en JS).

### A-05 · Le tri (« Classe ») est inutilisable au clavier — **majeur** (accessibilité)
- **Statut** : ✅ corrigé — commit `ff3f30e`. Avant/après : [A-05](captures/avant-apres-A-05.png). Test : « Tri : utilisable au clavier (question résolue sans souris) ».
- **Où** : questions de type `tri` (quiz q10, jeu « Les bons gestes » q1 et q6). Tous navigateurs.
- **Reproduire** : Tab jusqu'à une étiquette, Entrée.
- **Attendu** : l'étiquette est sélectionnée, puis on choisit une colonne au clavier.
- **Observé** :
  - Entrée ne sélectionne rien : la sélection ne se fait qu'au `pointerdown`/`pointerup`, et le `click` ignore les puces ;
  - les colonnes `.cat` sont des `div` non focusables ;
  - un joueur au clavier ne peut pas valider le quiz du niveau 1.
- **Preuve** : test « Tri : utilisable au clavier » dans `audit/fonctionnel.json`.
- **Cause** : `index.html` › `Q.tri` (écouteurs `pointerdown` + `click` qui `return` sur `.chip`).
- **Correctif proposé** :
  - dans le `click`, traiter les clics clavier (`e.detail === 0`) comme un toucher ;
  - rendre les colonnes focusables (`tabindex="0"`, `role="button"`, Entrée/Espace) ;
  - garder le glisser-déposer tel quel.

### A-06 · « Touche l'étiquette » est inutilisable au clavier — **majeur** (accessibilité)
- **Statut** : ✅ corrigé — commit `24f01a3`. Avant/après : [A-06](captures/avant-apres-A-06.png). Test : « Clavier : étiquette en mode toucher utilisable au clavier ».
- **Où** : questions `etiquette` en mode `toucher` :
  - vérification de la leçon 3 ;
  - quiz q7 ;
  - un tiers des tours du jeu « Lis l'étiquette » ;
  - défi.
- **Observé** : les champs sont des `<span>` (tabIndex −1). Aucun moyen de répondre sans souris ni écran tactile.
- **Preuve** : test « Clavier : étiquette en mode toucher » (`audit/fonctionnel.json`).
- **Cause** : `renderLabel()` produit des `span.ch`.
- **Correctif proposé** : en mode `tap`, ajouter `tabindex="0" role="button"` et gérer Entrée/Espace sur `.ch`, ou rendre les champs en `<button>` stylés pareil. L'aspect « papier » ne change pas.

### A-07 · Champs d'étiquette trop petits au toucher — **majeur** (mobile)
- **Statut** : ✅ corrigé — commit `cbbc036`. Au doigt, hauteur touchable ≥ 44 px pour les 176 champs (mesurée) ; rendu souris inchangé. Avant/après : [A-07](captures/avant-apres-A-07.png)
- **Où** : mode `toucher`, toutes les étiquettes. Jusqu'à 768 px, tous navigateurs.
- **Observé** : hauteurs mesurées et voisins collés (2 px d'écart), donc mauvais champ touché fréquent au doigt :

  | Champ | Taille |
  |---|---|
  | allergène | 113 × 15 px |
  | provenance | 98 × 15 px |
  | volume | 37 × 18 px |
  | degré | 61 × 18 px |
  | mention | 18 px de haut |
  | embouteillage | 15 px de haut |
  | millésime | 60 × 33 px |

- **Capture** : [etiquette-01 à 320 px, champs entourés](captures/chromium-etiquette-01-320-clair.png).
- **Cause** : `.lbl-foot .ch` (11–13 px, padding 1 px).
- **Correctif proposé** : en mode `.lbl.tap` seulement, agrandir la zone sensible sans changer le dessin : `.lbl.tap .ch{position:relative}` + `::after` avec `inset:-8px -4px`, et plus d'espace entre les éléments du pied (`gap:8px 10px`).

### A-08 · Contrastes insuffisants sur les boutons d'action et les chiffres clés — **majeur**
- **Statut** : ✅ corrigé — commit `7bcc4be`. Jetons --leaf-btn, --bad-btn, --on-*, --gold-ink, --flame-ink. Vert des boutons : #458200 en clair (au lieu de #58A700). Avant/après : [A-08-clair](captures/avant-apres-A-08-clair.png) · [A-08-sombre](captures/avant-apres-A-08-sombre.png)
- **Où** : tous navigateurs, toutes largeurs. Seuil AA : 4,5:1, ou 3:1 au-delà de 24 px (18,7 px en gras).
- **Thème sombre, encore plus bas** :

  | Élément | Couleurs | Contraste |
  |---|---|---|
  | Boutons verts « Vérifier », « Continuer » | blanc sur `#79C82A` | **2,08:1** |
  | Boutons rouges (« Quitter », « Abandonner »…) | blanc sur `#F06A60` | 3,03:1 |
  | Fin de session : « XP gagnés » | blanc sur `#F0B83A` | 1,81:1 |
  | Fin de session : « Réussite » | — | 2,08:1 |

- **Thème clair** :

  | Élément | Couleurs | Contraste |
  |---|---|---|
  | Boutons verts « Vérifier », « Continuer » | blanc sur `#58A700` | 3,02:1 |
  | Boutons rouges « Continuer », « Quitter », « Tout effacer » | blanc sur `#E0473E` | 4,09:1 |
  | Fin de session : étiquettes « XP GAGNÉS » | blanc sur `#E3A41D` | 2,19:1 |
  | Fin de session : étiquettes « RÉUSSITE » | blanc sur `--leaf` | 3,02:1 |
  | Fin de session : chiffres « +19 » | or sur crème | 2,02:1 |
  | Fin de session : chiffres « 100 % » | vert sur crème | 2,79:1 |
  | Barre du haut : série | `#E8730C` | 2,81:1 |
  | Barre du haut : série à 0 | grisée | 2,82:1 |
  | Barre du haut : XP | `#A87308` | 3,78:1 |
  | Titre « Bon à savoir » | — | 3,59:1 |
  | « Si tu réponds maintenant : 3 points bonus » | — | 3,78:1 |
  | Badges non obtenus (opacité 0,55) : description | — | 2,25:1 |
  | Badges non obtenus : nom | — | 3,87:1 |
  | Couleur de la 3ᵉ paire d'association | blanc sur `#C77A12` (calculé) | 3,4:1 |
  | En-tête du niveau 4 (même `#C77A12`), une fois débloqué | — | — |

- **Captures** : [fin de leçon](captures/chromium-fin-lecon-375-clair.png) · [feuille verte](captures/chromium-q-qcm-juste-375-clair.png) · [badges](captures/chromium-profil-nouveau-375-clair.png) · [indices](captures/chromium-q-indices-avant-375-clair.png).
- **Cause** : jetons `--leaf`, `--bad`, `--gold`, `--gold-deep` utilisés comme fond de texte blanc ou comme couleur de texte (dans les deux thèmes ; en sombre, ces jetons sont plus clairs, donc le blanc ressort encore moins) ; `.badge.off{opacity:.55}` ; `PAIR_COLORS`, `unitColors`.
- **Correctif proposé** (sans changer la palette perçue) :
  - assombrir légèrement les fonds de boutons : vert vers `#468A00`, rouge vers `#C9372E` ;
  - texte foncé `#3a2600` sur l'or, comme `.btn.gold` le fait déjà ;
  - chiffres de fin en `--gold-deep` et `--leaf-deep` ;
  - badges éteints en niveaux de gris plutôt qu'en opacité ;
  - `#C77A12` remplacé par `#A9630A` ;
  - en sombre, garder les fonds vifs mais écrire en foncé dessus (`#14210A` sur le vert, `#2A0F0C` sur le rouge, `#3a2600` sur l'or).

  Le vert Duolingo est un choix de marque : **à arbitrer avec toi**.

### A-09 · Thème sombre : bordeaux clair sur fonds sombres et en-têtes, sous le seuil — **mineur**
- **Statut** : ✅ corrigé — commit `7483c98`. Étendu aux textes des illustrations et à l'or des étiquettes. Plus aucun texte HTML ou SVG sous AA sur les 113 écrans (hors boutons désactivés). Avant/après : [A-09-etiquette](captures/avant-apres-A-09-etiquette.png) · [A-09](captures/avant-apres-A-09.png)
- **Où** : sombre système et forcé, tous navigateurs.

  | Élément | Contraste |
  |---|---|
  | Onglet actif, palier choisi, puce de rang, choix sélectionné (`#D24A73` sur `#3A1B26`) | 3,64:1 |
  | Boutons fantômes (← , Rester, Indice suivant, Changer de niveau) | 3,99:1 |
  | `<strong>` et termes de glossaire dans les leçons | 4,41:1 |
  | Texte blanc sur les boutons bordeaux | 4,23:1 |
  | « Niveau 1 · Découverte » et objectif dans l'en-tête bordeaux | 3,48:1 et 3,81:1 |
  | Étiquette « Indice 1 » (blanc sur `#A991D6`) | 2,72:1 |
  | Titres des colonnes du tri | 3,79:1 |
  | « Bon à savoir » (`#B07C0E` sur `#3A2E14`) | 3,63:1 |
  | `<strong>` dans un encadré doré | 3,14:1 |

- **Capture** : [accueil sombre](captures/chromium-accueil-milieu-375-sombre-systeme.png).
- **Cause** : `--grape` sombre `#D24A73` utilisé à la fois comme fond et comme texte.
- **Correctif proposé** : en sombre, un `--grape` texte un peu plus clair (≈ `#E8668D`) et un fond de bouton un peu plus foncé (≈ `#B83560`) ; `.clue .n` en `--plum-soft` / `--plum`.

### A-10 · Textes coupés dans les illustrations SVG — **majeur** (contenu pédagogique tronqué)
- **Statut** : ✅ corrigé — commits `6f1535a`, `850cbe1`. Libellés sur plusieurs lignes, taille d'origine conservée ; vérifié avec et sans Google Fonts. Avant/après : [A-10-etiquette](captures/avant-apres-A-10-etiquette.png) · [A-10](captures/avant-apres-A-10.png)
- **Où** : toutes largeurs, tous thèmes, tous navigateurs.
  - Leçon 1, carte 2 (`raisin-coupe`) : « Peau : couleur, arômes, tanins », « Pulpe : eau, sucres, acides », « Pépins : tanins durs » sont coupés après ~8 caractères (texte de x = 162 à 300 dans un viewBox de 220).
  - Leçon 3, carte 1 (`etiquette-anatomie`) : « …roducteur », « …ppellation », « degré, vol… ».
  - Leçon 1, carte 5 (`amphore`) : « −6000 » touche le bord.
  - Leçon 2, carte 4 (`botrytis`) : « l'eau s'évapore, » et « le sucre reste » sont coupés.
  - Leçon 2, carte 5 (`mutage`) : « le sucre reste ».
  - Défi, graphique XP : la valeur au-dessus de la barre la plus haute sort du cadre (y = −3).
- **Captures** : [raisin-coupe](captures/chromium-lecon1-carte2-375-clair.png) · [anatomie de l'étiquette](captures/chromium-lecon3-carte1-375-clair.png) · [amphore](captures/chromium-lecon1-carte5-375-clair.png) · [botrytis](captures/chromium-lecon2-carte4-375-clair.png) · [graphique du défi](captures/chromium-defi-veteran-375-clair.png).
- **Cause** : `index.html` › `IL[...]` (coordonnées et viewBox) ; `viewDefi` (`y = 108 − hauteur`).
- **Correctif proposé** :
  - élargir les viewBox concernés (par exemple `0 0 320 150` pour `raisin-coupe`), ou passer les libellés sur deux lignes ;
  - dans le graphique, borner `y ≥ 12`.

  Aucune modification du dessin lui-même.

### A-11 · Les toasts recouvrent le contenu (choix, statistiques de fin) — **mineur**
- **Statut** : ✅ corrigé — commits `e2b4fdb`, `8195bd6`. Toasts affichés en haut, sur toutes les vues. Avant/après : [A-11-carte](captures/avant-apres-A-11-carte.png) · [A-11](captures/avant-apres-A-11.png)
- **Où** : sessions et écrans de fin, 320 et 375 px surtout, tous navigateurs.
- **Observé** :
  - pendant une question, un toast recouvre le 4ᵉ choix (288 × 45 px) ;
  - à la fin du quiz réussi, « Nouveau rang » recouvre « XP gagnés » et « Réussite » ;
  - les toasts passent un par un, 2,4 s chacun : 3 toasts = 7,2 s de masquage.
- **Captures** : [pendant une question](captures/chromium-toasts-pendant-question-375-clair.png) · [fin de quiz](captures/chromium-fin-quiz-reussi-320-clair.png).
- **Cause** : `.toasts{position:fixed;bottom:calc(96px + …)}`, prévu pour la barre d'onglets, mais aussi utilisé pendant les sessions.
- **Correctif proposé** : pendant une session, afficher les toasts en haut, sous la barre de progression (classe sur `body`), et raccourcir la file (2 s, ou toasts groupés).

### A-12 · Barre du haut qui déborde à 320 px avec beaucoup d'XP — **mineur**
- **Statut** : ✅ corrigé — commit `a5229e3`. Avant/après : [A-12](captures/avant-apres-A-12.png)
- **Où** : toutes les vues, 320 px, joueur vétéran (365 jours, 123 456 XP), tous navigateurs.
- **Observé** :
  - défilement horizontal de toute la page : 1,4 px avec les polices Google, 35 px avec les polices de repli ;
  - le compteur d'XP sort de l'écran.
- **Captures** : [sans polices](captures/chromium-accueil-veteran-320-clair-sans-polices.png).
- **Cause** : `.topbar .wrap` (flex sans réduction possible) ; `renderTop()` affiche le nombre complet.
- **Correctif proposé** : format court au-delà de 10 000 (« 123 k »), `min-width:0` sur `.stats`, et masquer le texte « Pampre » de la marque sous 360 px.

### A-13 · Écran de fin : le bouton Continuer sort de l'écran avec les polices de repli — **mineur**
- **Statut** : ✅ corrigé — commit `bb6c158`. Avant/après : [A-13](captures/avant-apres-A-13.png)
- **Où** : fins de jeu et de quiz raté (boutons « Réessayer » + « Continuer »), 320 px, Google Fonts indisponible.
- **Observé** : « Continuer » est coupé à droite (x jusqu'à 328 px) ; « 100 % » passe sur deux lignes dans la case Réussite.
- **Capture** : [fin de jeu sans polices](captures/chromium-fin-jeu-320-clair-sans-polices.png).
- **Cause** : `.s-foot .btn{flex:1}` + `.btn.ghost{flex:0 0 auto}` avec `letter-spacing` et majuscules ; `.es span` à 24 px.
- **Correctif proposé** : `.s-foot .btn{min-width:0}`, autoriser le retour à la ligne (`white-space:normal`) ou réduire le padding sous 360 px ; `white-space:nowrap` pour les chiffres.

### A-14 · Carte libre : « Appellation » déborde de sa case — **mineur**
- **Statut** : ✅ corrigé — commit `537e782`. Avant/après : [A-14](captures/avant-apres-A-14.png)
- **Où** : réglages de la carte, 320, 375 et 400 px, tous thèmes. Encore pire sans polices (80 px dans 49 px).
- **Observé** : « Appellatio » est coupé par la case voisine.
- **Capture** : [carte-reglages à 320 px](captures/chromium-carte-reglages-320-clair.png).
- **Cause** : `.tiers{grid-template-columns:repeat(5,minmax(0,1fr))}` + `.tier{font-size:12px}`.
- **Correctif proposé** : `font-size:11px` et `hyphens:auto` sous 420 px, ou un trait d'union conditionnel dans l'affichage (le JSON ne change pas).

### A-15 · Téléphone en paysage : la carte prend plus que l'écran et capte tous les gestes — **mineur**
- **Statut** : ✅ corrigé — commit `e6594d6`. Avant/après : [A-15](captures/avant-apres-A-15.png)
- **Où** : Carte libre et question « carte », 667 × 375.
- **Observé** :
  - la carte fait 635 × 635 px pour 375 px de haut ;
  - comme elle bloque le défilement tactile (`touch-action:none`), atteindre « Valider ma position » oblige à viser les 16 px de marge ;
  - la feuille de correction occupe 55 % de l'écran.
- **Captures** : [carte en paysage](captures/preuve-paysage-carte.png) · [feuille en paysage](captures/preuve-paysage-feuille.png).
- **Cause** : `.map-box{aspect-ratio:1/1}` sans hauteur maximale.
- **Correctif proposé** : `max-height: calc(100dvh - 200px)` sur `.map-box`, avec `width:auto` et `margin-inline:auto`.

### A-16 · Double toucher rapide sur « Continuer » : une carte de leçon est sautée — **mineur**
- **Statut** : ✅ corrigé — commits `0f64821`, `0de9dd6`. Ignore le 2ᵉ clic d'un double clic (event.detail > 1) et, au doigt, un 2ᵉ toucher < 350 ms. Comportement réel d'iOS Safari non vérifiable ici. Test : « Robustesse : double clic rapide » (souris et doigt).
- **Où** : leçons, tous navigateurs.
- **Reproduire** : double-cliquer « Continuer » sur la carte 1 de la leçon 1.
- **Attendu** : carte 2. **Observé** : carte 3, « La fermentation, cœur du miracle ».
- **Preuve** : test « Robustesse : double clic » (`audit/fonctionnel.json`).
- **Cause** : `runSession` › `show()` recrée un bouton « Continuer » au même endroit, et le second clic l'active.
- **Correctif proposé** : ignorer les clics pendant ~350 ms après chaque `show()` (horodatage), ou ignorer `e.detail > 1`.

### A-17 · Pas de piège de focus dans les sessions, la modale et le glossaire — **mineur** (accessibilité)
- **Statut** : ✅ corrigé — commit `fd7852a`. Test : « Clavier : piège de focus (session, modale, glossaire) ».
- **Où** : tous les calques déclarés `aria-modal="true"`.
- **Observé** :
  - Tab sort de la session et atteint « Pampre », les compteurs et les onglets, invisibles derrière ;
  - le focus n'est pas rendu à l'élément d'origine à la fermeture ;
  - la page derrière le glossaire défile (0 → 800 px à la molette).
- **Preuve** : test « Clavier : focus visible et piège de focus ».
- **Cause** : `runSession`, `confirmBox`, `openGlossary`.
- **Correctif proposé** : poser `inert` sur `#app`, `#topbar` et `.tabbar` tant qu'un calque est ouvert, puis rendre le focus à l'élément d'origine.

### A-18 · Défi du jour : l'étiquette change à chaque lancement — **mineur**
- **Statut** : ✅ corrigé — commit `d6588a4`. Test : « Défi : mêmes questions toute la journée ».
- **Où** : défi du jour.
- **Observé** : deux tirages le même jour donnent `gen-region-guigal`, puis `gen-region-tempier`. Les 4 questions de révision et la carte restent stables.
- **Preuve** : test « Défi : mêmes questions toute la journée ».
- **Cause** : `buildDaily()` appelle `genLabelQuestions(1)`, qui utilise `Math.random` au lieu du générateur `rnd` du jour.
- **Correctif proposé** : passer `rnd` en paramètre à `genLabelQuestions` (et à ses `shuffle` / `pick`).

### A-19 · Le badge « Lexicophile » n'est pas donné quand le 20ᵉ mot est ouvert via « Voir aussi » — **mineur**
- **Statut** : ✅ corrigé — commit `9b89fab`. Test : « Progression : badge Lexicophile via Voir aussi ».
- **Preuve** : test dédié (20 mots enregistrés, pas de badge).
- **Cause** : `openGlossary` › écouteur du tiroir : `ST.gloss[k] = 1; save();` sans `checkBadges()`.
- **Correctif proposé** : appeler `checkBadges()`.

### A-20 · « Ce que tu as fait ne sera pas enregistré » est faux — **mineur**
- **Statut** : ✅ corrigé — commit `1e4f7c8`. Choix fait : les erreurs restent enregistrées (utile au défi) ; le message le dit désormais. Avant/après : [A-20](captures/avant-apres-A-20.png)
- **Observé** :
  - en quittant une session par le X, les erreurs sont **déjà** dans la pile d'erreurs (`quiz1-0` après une mauvaise réponse) ;
  - le X reste visible sur l'écran de fin et affiche le même avertissement alors que tout est déjà enregistré.
- **Capture** : [modale](captures/chromium-modale-quitter-375-clair.png).
- **Cause** : `runSession` › `verify()` sauvegarde `ST.mistakes` immédiatement ; le bouton `data-quit` n'est pas masqué dans `finish()`.
- **Correctif proposé** : soit garder les erreurs en mémoire jusqu'à `finish()`, soit reformuler le message (« Ta progression dans cette session sera perdue ; tes erreurs restent à revoir »). Masquer le X sur l'écran de fin.

### A-21 · Correction erronée pour la provenance d'un vin étranger — **mineur**
- **Statut** : ✅ corrigé — commit `03bfb05`. Avant/après : [A-21](captures/avant-apres-A-21.png). Test : « Étiquettes : provenance des vins étrangers ».
- **Reproduire** : étiquette Taylor's (porto), mode toucher, cible provenance, répondre faux.
- **Observé** : l'étiquette affiche « Produit du Portugal », mais la correction dit « Bonne réponse : Produit de France ».
- **Capture** : [preuve-provenance-portugal.png](captures/preuve-provenance-portugal.png).
- **Cause** : `Q.etiquette` › `check()`, valeur codée en dur `"Produit de France"`.
- **Correctif proposé** : réutiliser le texte calculé par `renderLabel` (fonction commune). Le même code produirait « Produit du Italie » ou « Produit du Espagne » si on ajoutait ces pays : prévoir « d'Italie », « d'Espagne ».

### A-22 · « Tout effacer » laisse le thème sombre forcé alors que le réglage affiché est « Auto » — **mineur**
- **Statut** : ✅ corrigé — commit `7fbd9b1`. Avant/après : [A-22](captures/avant-apres-A-22.png). Test : « Profil : Tout effacer avec un thème forcé ».
- **Capture** : [preuve-effacer-theme.png](captures/preuve-effacer-theme.png) (`data-theme="dark"` alors que `ST.theme` vaut `null`).
- **Cause** : `viewProfil` › reset : `applyTheme()` n'est pas appelé.
- **Correctif proposé** : appeler `applyTheme()` après `ST = freshState()`.

### A-23 · Échap ne ferme pas la modale de confirmation — **mineur**
- **Statut** : ✅ corrigé — commit `9a93abf`. Test : « Clavier : Échap ferme le glossaire et la modale ».
- **Où** : « Quitter la session ? », « Abandonner ? », « Tout effacer ? ».
- **Cause** : `confirmBox` n'écoute pas le clavier.
- **Correctif proposé** : Échap = « Rester ». Par la même occasion, retirer l'écouteur Échap du glossaire quand on le ferme par clic : aujourd'hui les écouteurs s'accumulent.

### A-24 · Les écouteurs globaux du tri restent actifs après avoir quitté par le X — **mineur**
- **Statut** : ✅ corrigé — commit `f91d27f`. Test : « Tri : écouteurs globaux retirés après le X ».
- **Preuve** : écouteurs `pointermove` et `pointerup` sur `window` : 1 avant, 3 pendant, 3 après le X. Seule une fin normale les retire.
- **Cause** : `closeSession()` n'appelle pas `current.cleanup()`.
- **Correctif proposé** : `runSession` expose son nettoyage, et `closeSession` l'appelle.

### A-25 · Série remise à 1 quand on voyage vers l'ouest — **mineur**
- **Statut** : ✅ corrigé — commit `2a5cada`. Test : « Série : voyage vers l'ouest ».
- **Reproduire** : dernier jour enregistré le 6 octobre (Auckland), puis on joue le 5 octobre heure de Los Angeles.
- **Observé** : la série de 10 jours retombe à 1.
- **Cause** : `gainXP()` ne traite pas `dayDiff < 0`.
- **Correctif proposé** : si `dayDiff(s.last, t) <= 0`, ne rien changer.

### A-26 · Changer d'onglet pendant une manche de carte — **mineur**
- **Statut** : ✅ corrigé — commit `ce74767`. Test : « Carte : changer d'onglet en pleine partie » ([capture](captures/preuve-carte-retour-onglet.png)).
- **Observé** :
  - avant validation, l'épingle posée est perdue ;
  - **pendant la révélation**, le retour sur l'onglet saute directement à la manche suivante : on perd le score affiché, la fiche et le débat.
- **Preuve** : test « Carte : changer d'onglet » (manche 2 affichée directement).
- **Cause** : `mapRound()` traite `G.revealed` comme « passer à la suivante ».
- **Correctif proposé** : mémoriser `guess` et le résultat dans `MAPGAME`, et réafficher la révélation au retour.

### A-27 · Zones tactiles < 44 × 44 px hors étiquettes — **mineur**
- **Statut** : ✅ corrigé — commits `575e946`, `a29a788`. Avant/après : [A-27](captures/avant-apres-A-27.png)
- **Où** : largeurs ≤ 768 px.

  | Élément | Taille |
  |---|---|
  | Bouton X des sessions et du glossaire | 42 × 42 |
  | Zoom carte (+, −, recentrer) | 40 × 40 |
  | Boutons Auto / Clair / Sombre et France / Monde | 32 px de haut |
  | Cases « Villes repères » et « Couleurs des régions » | 24 px de haut |
  | Compteurs de la barre du haut | 31 px |
  | Boutons « small » (Jouer, Copier, Importer, Indice suivant) | 38 px |
  | « Abandonner la partie » | 32 px |
  | Puces placées dans une colonne de tri | 38 px |

- **Cause** : CSS `.iconbtn`, `.map-zoom button`, `.seg button`, `.toggles label`, `.stat`, `.btn.small`, `.linkbtn`, `.cat .chip`.
- **Correctif proposé** : `min-height:44px` (et `min-width`) sur ces éléments, sans changer leur apparence (padding ou zone sensible étendue).

### A-28 · Carte : villes repères coupées au bord, Ajaccio en mer — **cosmétique**
- **Statut** : ✅ corrigé — commit `093f5b1`. Libellés à gauche près du bord droit. Le point d'Ajaccio garde ses vraies coordonnées (0,2 km du contour simplifié). Avant/après : [A-28](captures/avant-apres-A-28.png)
- **Observé** : au zoom initial, « Strasbourg » et « Ajaccio » sont coupés par le bord droit. Le point d'Ajaccio tombe en mer sur le fond simplifié (aussi signalé par le validateur).
- **Capture** : [carte au zoom initial](captures/preuve-carte-dezoom-max.png).
- **Cause** : `drawOverlays()` écrit toujours le libellé à droite du point ; `FRANCE_VB` trop serré à droite ; `carte-vins.json` › `villes` › Ajaccio (41.919, 8.739).
- **Correctif proposé** : libellé à gauche pour les villes proches du bord est (`text-anchor:end`), et élargir légèrement `FRANCE_VB`. Les coordonnées d'Ajaccio sont à ajuster **avec ton accord** (donnée).

### A-29 · Zones régionales : Côte-Rôtie, Condrieu, Ampuis et Romanèche-Thorins hors de leur région — **mineur** (données / approximation)
- **Statut** : ✅ corrigé — commit `dc4585e`. **Changement de données à valider** : `carte-vins.json`, régions Rhône (+69) et Beaujolais (+71). Avant/après : [A-29](captures/avant-apres-A-29.png)
- **Observé** :
  - Côte-Rôtie, Condrieu et Ampuis sont dans le Rhône (69), département rattaché au Beaujolais ; Romanèche-Thorins est en Saône-et-Loire (71), rattachée à la Bourgogne ;
  - au palier 1, « Côte-Rôtie La Mouline » placée pile au bon endroit affiche « 1 km » au lieu de « dans la région ! » (score plein grâce aux ancres) ;
  - la surbrillance exclut le lieu réel ;
  - un clic sur Lyon compte « dans la région » pour le Beaujolais.
- **Preuve** : `tools/valider-contenu.py` et le test « Carte : détection dans la région ».
- **Cause** : `carte-vins.json` › `regions[].deps` (limite connue, signalée dans CLAUDE.md).
- **Correctif proposé** : à décider avec toi. Soit des zones infra-départementales, soit accepter un département partagé dans `inRegion` (tester toutes les régions qui listent le département).

### A-30 · Accessibilité : régions live et noms des boutons — **mineur**
- **Statut** : ✅ corrigé — commit `6f2c912`. Avant/après : [A-30](captures/avant-apres-A-30.png). Test : « Accessibilité : régions live et noms des boutons ».
- **Observé** :
  - `#app` porte `aria-live="polite"` : un lecteur d'écran relit toute la vue à chaque `render()` ;
  - les compteurs de la barre du haut s'annoncent « 1, bouton », « 64, bouton » (le `title` n'est qu'une description) ;
  - l'anneau de focus doré `#E3A41D` sur la crème contraste à 2:1 (le minimum est 3:1 pour un indicateur de focus).
- **Cause** : `index.html` (`<div id="app" aria-live>`, `renderTop()`, `:focus-visible`).
- **Correctif proposé** :
  - retirer `aria-live` de `#app` (les toasts ont déjà `role="status"`) ;
  - ajouter `aria-label="Série : 1 jour"` et `aria-label="64 XP"` ;
  - utiliser un anneau `--grape-deep` en clair.

### A-31 · Message d'erreur de chargement technique et en anglais — **cosmétique**
- **Statut** : ✅ corrigé — commit `7c110bf`. Avant/après : [A-31](captures/avant-apres-A-31.png)
- **Observé** :
  - « Expected property name or '}' in JSON at position 2… » pour un JSON invalide ;
  - « content/glossaire.json : 404 » pour un fichier absent ;
  - pas de bouton « Réessayer ».

  Le message s'affiche proprement, en revanche.
- **Captures** : [JSON invalide](captures/preuve-contenu-invalide.png) · [fichier manquant](captures/preuve-contenu-manquant.png).
- **Cause** : `boot()` affiche `err.message` brut.
- **Correctif proposé** : message français (« Le fichier … est introuvable / mal formé »), détail technique replié, et bouton « Réessayer ».

### A-32 · Titres coupés sur le trait d'union — **cosmétique**
- **Statut** : ✅ corrigé — commit `e252b84`. Avant/après : [A-32](captures/avant-apres-A-32.png)
- **Observé** : « Que trouve-t- / on dans un grain ? » (leçon 1, carte 2) à 375 px.
- **Capture** : [lecon1-carte2](captures/chromium-lecon1-carte2-375-clair.png).
- **Cause** : `text-wrap:balance` + coupure autorisée après le trait d'union.
- **Correctif proposé** : dans `rich()` et les titres, remplacer `-t-` par des traits d'union insécables (U+2011) à l'affichage, sans toucher au JSON.

### A-33 · Compteur de session figé après la réponse — **cosmétique**
- **Statut** : ✅ corrigé — commit `fab0766`. Test : mesure du compteur et de la barre (reprises comprises).
- **Observé** :
  - « 0/1 » et la barre de progression ne bougent qu'au clic sur Continuer ;
  - pendant les reprises d'une leçon, le compteur reste à « 2/2 » alors qu'il reste une question.
- **Cause** : `runSession` › `progress()` appelé seulement dans `show()`.
- **Correctif proposé** : appeler `progress()` dans `verify()`, et afficher « reprise » pour les questions remises en file.

### A-34 · `<title>` et feuilles de style dans `<body>`, favicon absent — **cosmétique**
- **Statut** : ✅ corrigé — commit `43e7c97`. Test : aucune erreur de console sur tous les parcours.
- **Observé** :
  - `<title>`, le `<link>` Google Fonts et le CSS principal sont dans `<body>` (HTML invalide, même si les navigateurs s'en accommodent) ;
  - `GET /favicon.ico` en 404 (seule erreur de console de tout l'audit).
- **Correctif proposé** : déplacer ces balises dans `<head>` ; ajouter un favicon SVG inline (`<link rel="icon" href="data:image/svg+xml,…">`) reprenant le logo.

### A-35 · Défi du jour à 320 px : texte écrasé — **cosmétique**
- **Statut** : ✅ corrigé — commit `f867565`. Avant/après : [A-35](captures/avant-apres-A-35.png)
- **Observé** : sur l'accueil, la carte « Défi du jour » laisse ~140 px au texte, qui passe sur 5 lignes, avec « Défi / du jour » sur deux lignes.
- **Capture** : [accueil à 320 px](captures/chromium-accueil-nouveau-320-clair.png).
- **Correctif proposé** : sous 360 px, placer le bouton « Jouer » sous le texte (`flex-wrap:wrap`).

### A-36 · Polices de repli : « Certifications » déborde de sa carte bonus — **cosmétique**
- **Statut** : ✅ corrigé — commit `fb3017a`. Avant/après : [A-36](captures/avant-apres-A-36.png)
- **Observé** : 128 px de contenu dans 106 px, à 320 px.
- **Capture** : [accueil sans polices](captures/chromium-accueil-milieu-320-clair-sans-polices.png).
- **Correctif proposé** : `overflow-wrap:anywhere` / `hyphens:auto` sur `.bonus b`.

### A-37 · Mouvement réduit : défilements animés conservés — **cosmétique**
- **Statut** : ✅ corrigé — commit `783cb9e`. Test : « Mouvement réduit : rien ne reste invisible ».
- **Observé** : tout reste visible avec `prefers-reduced-motion` (vérifié : opacité 1, confettis invisibles). En revanche, `scrollIntoView({behavior:"smooth"})` (révélation de la carte, glossaire) reste animé.
- **Correctif proposé** : `behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'`.

---

### Annexe WebKit (moteur de Safari)

Matrice WebKit : 113 écrans × 320 / 375 / 768 / 1280 px × 4 thèmes, soit 6 834 constats bruts dans `audit/webkit/resultats.json`, résumé dans `audit/webkit/resume.md`, captures dans `audit/webkit/captures/`.

**Retrouvés à l'identique sous WebKit**
- A-02 : feuille de correction ([capture](captures/preuve-webkit-feuille.png)).
- A-03, A-08, A-09 : mêmes paires de couleurs et mêmes rapports.
- A-04 : bulle « Continuer », recouvrement de 3 255 px² ([capture](captures/preuve-webkit-bulle-continuer.png)).
- A-10 : SVG coupés.
- A-12 : débordement de 2 px à 320 px.
- A-14 : « Appellation ».
- Tests fonctionnels (`isPointInFill`, carte, glisser-déposer, recherche, parcours complet) : **aucune erreur JS et aucun bug propre à WebKit**.

**Non contrôlés sous WebKit**
- Les toasts (A-11) : la passe WebKit a démarré avant l'ajout du contrôle géométrique des toasts.
- Les zones tactiles : même CSS que sous Chromium.

**Précaution de lecture** : les résultats bruts WebKit contiennent des paires de contraste aberrantes (texte `#2A161C` sur fond sombre, ~1:1). Ce sont des mesures prises pendant la transition CSS des fonds (`.choice{transition:background .12s}`) juste après le changement de thème, que WebKit exécute plus lentement. Ce ne sont pas des bugs, et ces paires ne sont pas retenues.

## 3. Ce qui a été vérifié et fonctionne

- **Progression** :
  - déblocage des nœuds dans l'ordre ;
  - seuil exact de 80 % (11/15 refusé, 12/15 accepté), niveau 2 débloqué avec son parcours ([capture](captures/preuve-niveau2-debloque.png)) ;
  - XP de leçon (19 puis 9), bonus de quiz de 40 XP une seule fois ;
  - chaque badge une seule fois ;
  - « Lecteur d'étiquettes » à 8/10 et pas à 7 ;
  - changement de rang à 100 XP.
- **Série** : même jour, lendemain, trou de 2 jours, 00 h 01, passages à l'heure d'été (29/03) et d'hiver (25/10), flamme grisée à 0.
- **Défi** :
  - questions différentes le lendemain, aucun doublon sur 14 jours ;
  - fonctionne pour un nouveau joueur ;
  - bonus de 30 XP une seule fois par jour.
- **Glisser-déposer** (Chromium souris et tactile émulé, WebKit souris) : dépôt hors colonne, reprise d'une étiquette placée, toucher puis toucher.
- **Association et remise en ordre** : toutes les combinaisons testées, aucune erreur.
- **Carte** :
  - clic ≠ glissé (seuil de 6 px) ;
  - molette, pincement, + / − / recentrer ;
  - limites de zoom (largeur de vue de 6 à 1 500) ;
  - taille constante des épingles (31 px), des villes (15 px) et de la distance (24 px) à tout zoom et toute largeur ;
  - 6 scores recalculés à la main, identiques ;
  - `isPointInFill` correct sous Chromium **et** WebKit (Corse, côtes, frontières).
- **Clavier** : touches 1–4 et Entrée, Échap dans le glossaire.
- **Robustesse** :
  - `localStorage` qui lève une exception : l'appli marche sans sauvegarde ;
  - défilement bloqué pendant la session et rétabli après (fin normale et X).
- **Profil** : export → import aller-retour, code tronqué refusé avec un message clair.
- **Glossaire** : recherche avec ou sans accents, majuscules, « Voir aussi ».
- **Divers** : aucune erreur JS sur tous les parcours, hormis le favicon (A-34) ; WebKit : leçon et quiz complets sans erreur.

---

## 4. Données et contenu (`tools/valider-contenu.py`)

Résultat : **1 erreur, 7 avertissements.**

| Vérification | Résultat |
|---|---|
| JSON valides, schémas (niveaux, leçons, questions, étiquettes, glossaire, carte) | conformes |
| `[[termes]]` du texte et « voir » du glossaire | tous trouvés |
| `illu` existantes dans `IL` | toutes trouvées (20) |
| Étiquettes référencées et `cible` présentes sur l'étiquette | conformes |
| Index `bonne`, catégories du tri, régions, identifiants uniques, explications | conformes |
| **Ville repère Ajaccio hors du fond de carte** | ✗ erreur (voir A-28) |
| Vins hors des départements de leur région : Côte-Rôtie (palier 1 et 3), Condrieu, Ampuis, Romanèche-Thorins | ⚠ (voir A-29) |
| Gard partagé entre Rhône et Languedoc | ⚠ limite connue |
| Leçon 4 « Les bons gestes » : aucun encadré **Exemple** (CLAUDE.md exige un vin réel cité en exemple par leçon) | ⚠ |

### Incohérences de contenu (non corrigées, à ta décision)

**C-01**
- Jeu « Les bons gestes », tri des températures : **Meursault** est rangé à « 12 à 14 °C ».
- La leçon 4 enseigne « Grands blancs (Meursault, Hermitage blanc) : 10 à 13 °C ».
- Un joueur qui a bien suivi la leçon peut hésiter, voire se tromper.

**C-02**
- Le glossaire classe « cépage » au niveau 2 et « climat » au niveau 4, mais les deux mots sont cliquables dès le niveau 1 : le tiroir affiche « Niveau 2 ».
- CLAUDE.md annonce 54 termes, il y en a 53.

### Affirmations factuelles qui me paraissent douteuses (non corrigées, à vérifier)

1. **Vin de France « créée en 2010 »** (leçon 3 et glossaire) : la catégorie date de la réforme de l'OCM vin entrée en vigueur le 1ᵉʳ août 2009. 2010 se trouve aussi dans certaines sources, à vérifier.
2. **Glossaire, « méthode traditionnelle »** : « En Champagne, on dit méthode champenoise ; le terme est réservé à cette région ». Depuis 1994, la mention « méthode champenoise » est interdite sur les étiquettes, y compris pour les autres régions, et les champenois ne l'emploient plus sur l'étiquette. La formulation laisse croire à un usage courant et autorisé en Champagne.
3. **Rosé par assemblage** : la leçon 2 et le quiz q13 disent « seule grande exception : le champagne rosé ». Il me semble que la dérogation européenne vise plus largement certains vins effervescents ou certaines AOP. Nuance à vérifier.
4. **Porto « entre 19 et 22 % vol »** (glossaire) : certains portos blancs légers peuvent descendre à 16,5 % vol.
5. **Mas de Daumas Gassac, « IGP Pays d'Hérault »** (étiquette, carte, quiz q15) : le domaine étiquette, à ma connaissance, en IGP Saint-Guilhem-le-Désert depuis les années 2010. À vérifier sur une étiquette récente.
6. **« Ajaccio, Domaine Comte Abbatucci »** (carte, palier 1) : une grande partie des vins du domaine sort en Vin de France ; l'appellation Ajaccio comme étiquette principale est discutable.
7. **Vouvray « ne produit que du chenin blanc »** (étiquette Huet) : le cahier des charges a longtemps admis un cépage accessoire (orbois / menu pineau). À vérifier dans la version en vigueur.
8. **Coordonnée de Jurançon** (palier 3) : (43.30, −0.45) tombe à ~5 km du centre de la commune (≈ 43.288, −0.386). La tolérance pleine du palier est de 3 km, donc un joueur qui vise le village perd des points.
9. **Niellucciu « génétiquement identique au sangiovese »** (étiquette Arena) : c'est l'opinion majoritaire, mais elle est débattue. Un champ `debat` serait plus prudent que l'affirmation.
10. **« Chignin-Bergeron : le nom de cru suffit à indiquer le cépage, une vraie exception en France »** : d'autres dénominations se lisent comme un cépage (Muscat de Beaumes-de-Venise, Alsace + cépage…). « Exception » est peut-être fort.

---

## 5. Récapitulatif

| Gravité | Nombre | Identifiants | Statut |
|---|---:|---|---|
| Bloquant | 1 | A-01 | ✅ corrigé |
| Majeur | 8 | A-02, A-03, A-04, A-05, A-06, A-07, A-08, A-10 | ✅ corrigés |
| Mineur | 20 | A-09, A-11, A-12, A-13, A-14, A-15, A-16, A-17, A-18, A-19, A-20, A-21, A-22, A-23, A-24, A-25, A-26, A-27, A-29, A-30 | ✅ corrigés |
| Cosmétique | 8 | A-28, A-31, A-32, A-33, A-34, A-35, A-36, A-37 | ✅ corrigés |
| **Total** | **37** | Plus 2 incohérences de contenu (C-01, C-02) et 10 affirmations factuelles à vérifier | 37 / 37 ; contenu non modifié |

Navigateurs : tous les bugs ci-dessus se reproduisent sous Chromium. Ceux qui ne dépendent que du code ou du CSS (tous sauf les variantes « polices de repli » d'A-12, A-13 et A-36) ont été retrouvés sous WebKit, voir l'annexe WebKit ci-dessous.

---

## 6. Ce que je n'ai PAS pu tester

| Quoi | Pourquoi |
|---|---|
| **Firefox** | Le réseau de cet environnement refuse `cdn.playwright.dev`, `download.mozilla.org`, `packages.mozilla.org` et le PPA Mozilla (403). Ubuntu 24.04 ne fournit Firefox qu'en snap, inutilisable ici. Commande prête : `python3 tools/audit.py --navigateurs firefox` après `playwright install firefox`. |
| **Safari iOS réel** | WebKitGTK partage le moteur de rendu et de JS, mais pas le comportement d'iOS : zones sûres (`env(safe-area-inset-*)`, encoche), barre d'adresse qui change `100vh`, rebond du défilement, barres de défilement superposées (émulées en masquant celles de GTK), zoom au focus des champs < 16 px, appui long. À vérifier sur un iPhone. |
| **Tactile sous WebKit** | WebKitWebDriver ne sait pas émuler le toucher : le glisser-déposer tactile et le pincement n'ont été testés que sous Chromium (Chrome DevTools Protocol). Sous WebKit : souris uniquement. |
| **Polices bloquées sous WebKit** | Pas d'interception réseau avec WebKitWebDriver : test fait sous Chromium uniquement. |
| **Lecteurs d'écran réels** (VoiceOver, NVDA, TalkBack) | Rien d'installable ici. Les constats d'accessibilité (A-05, A-06, A-17, A-30) viennent de l'arbre DOM et du clavier. |
| **Copier dans le presse-papiers** | L'API Clipboard demande une permission utilisateur absente en mode sans tête ; seul le repli (sélection du texte) a été vu. |
| **Zoom du navigateur à 200 % et grande taille de texte** | Non couvert par la matrice. |
| **Performances, mémoire, batterie, vrais appareils** | Hors de portée d'un conteneur. |
| **Vérification factuelle sur sources** | Les doutes de la section 4 viennent de mes connaissances, sans consultation de sources (INAO, règlements UE). À confirmer avant toute correction. |

---

## 7. Bilan après corrections

**37 bugs sur 37 corrigés.** Un commit par bug (plus quelques compléments marqués « suite »), l'identifiant figurant dans chaque message.

| Gravité | Corrigés |
|---|---|
| Bloquant | 1 / 1 |
| Majeur | 8 / 8 |
| Mineur | 20 / 20 |
| Cosmétique | 8 / 8 |

**Audit relancé en entier** (fichiers `*-final*`) :

| Passe | Avant | Après |
|---|---|---|
| Chromium, 113 écrans × 6 largeurs × 4 thèmes (`audit/resume-final.md`) | 16 515 constats bruts | 4 341, voir le détail ci-dessous |
| WebKit, 113 écrans × 3 largeurs × 4 thèmes (`audit/webkit/resume-final.md`) | 6 834 | 993, voir ci-dessous |
| Polices bloquées, Chromium (`audit/resume-sans-polices-final.md`, puis `resume-sans-polices-final-c.md` après le complément `850cbe1`) | 473 | 0 hors boutons désactivés |
| Tests fonctionnels, Chromium + WebKit (`audit/fonctionnel.json`) | 16 en échec sur 42 | **49 / 49 OK** (tests durcis ou ajoutés pour les corrections) |
| `tools/test-parcours.py` | — | OK (quiz entier juste, 12 captures, aucune erreur) |
| `tools/valider-contenu.py` | 1 erreur, 7 avertissements | 0 erreur, 5 avertissements attendus |

**Détail des constats restants, tous expliqués**
- **Défilement horizontal, texte coupé, élément hors écran, texte SVG coupé, contenu caché par la feuille de correction ou la barre d'onglets** : 0, dans les deux navigateurs, avec et sans Google Fonts.
- **Contraste**
  - Chromium : 5 constats, tous dans le scénario artificiel « toasts pendant une question », à 768 px en sombre forcé.
  - WebKit : 332 constats.
  - Tous mesurent des fonds intermédiaires de transition CSS juste après le changement de thème. L'audit coupe désormais les transitions pendant la mesure : relancé sous WebKit sur les écrans concernés et dans les 4 thèmes, il ne trouve **plus aucun** défaut (`audit/webkit/resume-final-sans-transition.md`).
- **Boutons désactivés** (`contraste-desactive`) : exemptés par les WCAG (Vérifier grisé, Monde · bientôt).
- **Zones tactiles**
  - Les constats restants sous Chromium concernent les champs d'étiquette et les étiquettes rangées du tri, qui ne s'agrandissent qu'au doigt (`pointer: coarse`, choix de design pour ne pas changer le rendu à la souris). Mesurés dans un contexte tactile : 0 cible sous 44 px.
  - Les liens de glossaire en ligne sont exemptés (exception « inline » des WCAG).
- **Toasts** : ils s'affichent désormais en haut (A-11) et peuvent recouvrir quelques secondes le titre de la page, par exemple après un import. Ils laissent passer les clics. C'est le compromis retenu pour ne jamais masquer un bouton d'action ni les résultats.

**Choix faits pendant les corrections, à valider**
1. **Vert des boutons** (A-08) : `#458200` en clair, au lieu de `#58A700`. Le vert vif reste pour la barre de progression, les bordures et la mascotte. En sombre, le vert vif est conservé avec un texte foncé dessus.
2. **Données de carte** (A-29) : dans `content/carte-vins.json`, le Rhône (69) est ajouté à la région Rhône et la Saône-et-Loire (71) au Beaujolais. Ce ne sont pas des textes pédagogiques, mais ce sont des données : ce changement est à confirmer.
3. **Pile d'erreurs** (A-20) : les erreurs restent enregistrées quand on quitte une session ; seul le message a changé.
4. **Ajaccio** (A-28) : le point garde ses vraies coordonnées. Il tombe à 0,2 km du contour simplifié de la côte.

**Non modifié, à ta décision** : les incohérences de contenu C-01 (Meursault à 12–14 °C dans le jeu, 10–13 °C dans la leçon) et C-02, ainsi que les 10 affirmations factuelles de la section 4. La leçon 4 n'a toujours pas d'encadré Exemple.

**Limites inchangées** : voir la section 6 (Firefox non testé ; iOS réel, dont le comportement du double toucher d'A-16 ; lecteurs d'écran réels).
