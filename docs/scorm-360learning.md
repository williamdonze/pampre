# Pampre dans un LMS (SCORM 2004) — 360Learning

Pampre s'exporte en **paquet SCORM 2004 (4e édition)**, un seul module (SCO) qui contient tout le jeu : les 6 niveaux, les cartes, le défi du jour, le glossaire. L'apprenant joue comme sur le site ; le LMS reçoit sa progression, son score et sa réussite.

## Fabriquer le paquet

```bash
python3 tools/build-scorm.py                 # réussite = les 6 niveaux validés (quiz ≥ 80 %)
python3 tools/build-scorm.py --niveaux 3     # réussite dès les niveaux 1 à 3 validés
python3 tools/test-scorm.py                  # vérifie le paquet dans un faux LMS
```

Résultat : `dist/pampre-scorm2004.zip` (≈ 0,6 Mo, fichiers à la racine du zip, comme l'exige 360Learning). Il contient le jeu, le contenu, l'adaptateur `scorm.js` et les polices en local : **aucune ressource externe**, utile derrière un pare-feu d'entreprise. Pas d'invitation à installer l'appli ni de service worker dans le paquet.

À refaire après chaque modification du contenu, puis réimporter le zip (voir « Mettre à jour »).

## Importer dans 360Learning

1. Créer un cours en **important un fichier eLearning** (le zip tel quel, sans le décompresser).
2. Dans les réglages du suivi, choisir le rapport **Réussi / Échoué** (« Passed/Failed ») : c'est ce que Pampre envoie. 360Learning recommande ce réglage pour éviter qu'un module reste bloqué à 50 %.
3. Facultatif : exiger un score minimum (le score envoyé est en pourcentage, voir ci-dessous).
4. Tester avec un compte apprenant avant de publier (ou sur [SCORM Cloud](https://cloud.scorm.com), gratuit, qui affiche tous les échanges).

360Learning accepte SCORM 1.2, 2004 (2e à 4e éd.) et cmi5. On a choisi 2004 pour la taille de sauvegarde : 64 000 caractères contre 4 096 en SCORM 1.2, que la progression de Pampre dépasserait en quelques semaines.

## Ce que Pampre envoie au LMS

| Donnée SCORM | Valeur |
|---|---|
| `cmi.completion_status` | `incomplete`, puis `completed` quand les niveaux requis sont validés |
| `cmi.success_status` | `passed` au même moment (jamais `failed` : on peut toujours repasser un quiz) |
| `cmi.score.raw` / `scaled` | moyenne des meilleurs résultats aux quiz des niveaux requis, en % (0 pour un niveau pas encore tenté) ; ne baisse jamais |
| `cmi.progress_measure` | part des étapes faites (leçons, jeux, quiz) sur les niveaux requis ; 1 une fois réussi |
| `cmi.objectives.n` | un objectif par niveau (`niveau-1`…) : score et réussite de son quiz |
| `cmi.suspend_data` | toute la progression (XP, série, badges, défis…), rechargée au lancement suivant |
| `cmi.exit` / `cmi.session_time` | `suspend` (reprise possible) et durée de la session |

La réussite est transmise immédiatement ; les autres sauvegardes sont regroupées (au plus une toutes les 3 secondes) et envoyées à la fermeture. Une fois « terminé + réussi », le statut ne revient jamais en arrière, même si l'apprenant clique sur « Tout effacer ».

## Mettre à jour le paquet

Selon la documentation de 360Learning, quand on remplace le fichier d'un cours, la progression (`cmi.suspend_data`) des apprenants **qui n'ont pas terminé** est effacée. Pampre garde aussi une copie locale par apprenant dans le navigateur (clé `pampre-scorm-<identifiant>`) : sur le même appareil et le même navigateur, la progression est retrouvée. Sur un autre appareil, elle repart de zéro. Mieux vaut donc mettre à jour rarement, ou prévenir les apprenants (ils peuvent aussi copier leur code de sauvegarde dans Profil avant la mise à jour).

## Limites

- Les XP, la série, les badges et le classement restent personnels à chaque apprenant : il n'y a pas de classement entre collègues (le LMS ne le permet pas en SCORM).
- Au-delà de 64 000 caractères (plus d'un an de jeu quotidien), l'historique le plus ancien des jours, défis et cartes du jour est retiré ; XP, niveaux et badges sont conservés.
- La Carte du jour est la même pour tous les apprenants qui ont la même version du paquet.
- Mentions de sources du fond de carte (france-geojson / IGN, Natural Earth, GeoNames) et licence des polices (SIL OFL) : incluses dans le paquet.
