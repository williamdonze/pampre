# Installer Pampre sur l'écran d'accueil

Pampre peut s'ajouter à l'écran d'accueil d'un téléphone ou d'une tablette : une icône (Pépin), l'ouverture en plein écran sans barre d'adresse, et le jeu reste disponible hors connexion une fois les pages visitées. Rien à télécharger depuis un store ; la progression est la même que dans le navigateur.

> Condition : le site doit être servi en **HTTPS** (GitHub Pages, Netlify… ou `localhost` pour tester). En `http://` sur une autre adresse, iOS ajoute un simple raccourci et Android ne propose pas l'installation.

## iPhone et iPad

| Navigateur | Marche à suivre |
|---|---|
| **Safari** | Bouton **Partager** (carré avec une flèche vers le haut ; en bas sur iPhone, en haut sur iPad ; sur iOS 26, parfois dans le menu **⋯**) → **Sur l'écran d'accueil** → **Ajouter**. |
| **Chrome, Edge, Firefox** (iOS 16.4 ou plus) | Bouton **Partager** (dans Chrome : à droite de la barre d'adresse ; ailleurs : dans le menu) → **Sur l'écran d'accueil** → **Ajouter**. Avant iOS 16.4, seul Safari le permet. |

Pas de bouton « Installer » possible : Apple ne permet pas à un site de déclencher l'ajout lui-même. Pampre affiche donc le mode d'emploi.

## Android

| Navigateur | Marche à suivre |
|---|---|
| **Chrome, Edge** | Bouton **Installer** de Pampre (fenêtre native du système). Sinon : menu **⋮** (Chrome, en haut à droite) ou **≡** (Edge, en bas) → **Ajouter à l'écran d'accueil** / **Installer l'application**. |
| **Samsung Internet** | Bouton **Installer** de Pampre, ou menu **≡** (en bas à droite) → **Ajouter la page à** → **Écran d'accueil**. |
| **Firefox** | Menu **⋮** → **Ajouter à l'écran d'accueil** (ou **Installer**). |
| **Opera** | Menu **⋮** → **Ajouter à…** → **Écran d'accueil**. |

## Navigateurs intégrés aux applis

Instagram, Facebook, Messenger, TikTok… ouvrent les liens dans leur propre navigateur, qui ne sait pas ajouter un site à l'écran d'accueil. Il faut d'abord ouvrir la page dans Safari ou Chrome (menu **⋯** → **Ouvrir dans le navigateur**). Pampre le détecte et l'explique.

## Ordinateur

Rien n'est proposé sur ordinateur (choix délibéré). Chrome et Edge permettent quand même d'installer le site via l'icône d'installation de la barre d'adresse.

## Dans le site

- **Accueil** : un bandeau « Pampre comme une appli », sur téléphone et tablette uniquement, à partir de la première leçon terminée (premiers XP). La croix le masque 14 jours.
- **Profil** : section « Appli sur l'écran d'accueil », toujours présente sur mobile ; indique « C'est fait » quand Pampre est ouvert depuis l'icône.
- Bouton **Installer** (fenêtre native) quand le navigateur le permet (Chrome, Edge, Samsung Internet sur Android), sinon **Comment faire ?** ouvre les étapes adaptées au navigateur détecté, avec un rappel pour les autres appareils.

## Côté technique

- `manifest.webmanifest` : nom, couleurs, icônes, affichage `standalone`.
- `icones/` : icônes générées par `tools/build-icones.py` (Pépin sur fond crème ; version `maskable` avec marge pour les découpes d'Android ; `apple-touch-icon.png` pour iOS).
- `sw.js` : service worker « réseau d'abord » : le contenu est toujours le plus récent en ligne, la dernière version vue sert hors connexion. Changer `CACHE` dans `sw.js` pour vider les anciennes copies.
- `index.html` : section « appli sur l'écran d'accueil » (`appareil()`, `etapesInstall()`, `aideInstall()`, `installer()`, `panneauInstall()`) ; balises `apple-mobile-web-app-*` et `theme-color` dans `<head>`.
