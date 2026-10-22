# Instructions pour Claude

Projet : afficher dans OBS (source navigateur) le texte de la diapo en direct d'EasyWorship. Voir `readme.md` puis `spec/`.

## Langue
Documentation, commentaires et messages de commit en **français** ; identifiants du code en anglais.

## Où trouver quoi
* Besoin : `spec/metier.md` · retours : `spec/user_feedback.md` · architecture : `spec/technique.md` · interfaces : `spec/interfaces.md`
* Options et choix : `strategies.md` · protocole EW : `doc/protocole_easyworship.md` · build : `doc/build_et_installation.md`
* Code historique (hors `main`) : branches `dev`/`version1` (client EW, **à réutiliser**), `version2` (page web `public/` à réutiliser, moteur widgets **à abandonner**), `link_flows` (ignorer).

## Règles
* Une seule application, volontairement basique. **Ne pas** réintroduire de moteur générique « widgets/flux/connecteurs ».
* L'application est en **lecture seule** vis-à-vis d'EasyWorship.
* Le protocole EW est non documenté : toute modification de `ew_client` doit être couverte par un test sur trames rejouées. Ne pas inventer de messages.
* Aucune dépendance réseau externe à l'exécution (pas de CDN).
* Pas d'écriture dans le dossier d'installation ; config et logs dans le dossier utilisateur de l'OS.
* Pas d'IP en dur ; `client_id` généré par installation.
* Ne pas pousser sur une autre branche que celle de la tâche ; ne pas créer de PR sans demande.

## Commandes (cible, une fois le code en place)
* Tests : `pytest` · Lint : `ruff check .` · Lancer : `python -m ew_to_obs --headless`
* Build : voir `doc/build_et_installation.md`

## Questions ouvertes
Voir `doc/plan_de_migration.md` (OS cibles, OBS sur le même PC, versions d'EW, fonctions à conserver).

> Note : Claude Code lit `CLAUDE.md` (en majuscules) sur les systèmes sensibles à la casse ; ce fichier est nommé `claude.md` à la demande du mainteneur.
