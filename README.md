# Pampre

Apprendre le vin en jouant : parcours en 6 niveaux façon Duolingo, jeux d'étiquettes, quiz et carte des vignobles façon GeoGuessr.

## Lancer

```bash
python3 -m http.server 8765
```

Puis ouvrir http://localhost:8765/ dans un navigateur. (Un simple double-clic sur `index.html` ne suffit pas : le contenu est chargé depuis le dossier `content/`.)

## Sur téléphone

Une fois le site en ligne en HTTPS, Pampre s'ajoute à l'écran d'accueil comme une appli (plein écran, hors connexion) : voir [docs/installer.md](docs/installer.md).

## Dans un LMS (SCORM)

`python3 tools/build-scorm.py` fabrique `dist/pampre-scorm2004.zip`, à importer dans 360Learning ou un autre LMS : voir [docs/scorm-360learning.md](docs/scorm-360learning.md).

## Continuer avec Claude Code

Ouvre ce dossier dans Claude Code : le fichier `CLAUDE.md` lui explique tout le projet (architecture, formats de contenu, exigences de qualité, prochaines étapes). Exemple de demande :

> Lis CLAUDE.md et docs/programme.md, puis crée le niveau 2 « Les cépages » sur le modèle du niveau 1.
