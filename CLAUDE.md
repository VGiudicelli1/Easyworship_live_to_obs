# Instructions pour Claude

Projet : afficher dans OBS (source navigateur) le texte de la diapo en direct d'EasyWorship. Voir `README.md` puis `spec/`.

## Langue
Documentation, commentaires et messages de commit en **français** ; identifiants du code en anglais.

## Où trouver quoi
* Besoin : `spec/metier.md` · retours : `spec/user_feedback.md` · architecture : `spec/technique.md` · interfaces : `spec/interfaces.md`
* Options et choix : `STRATEGIES.md` · protocole EW : `doc/protocole_easyworship.md` · build : `doc/build_et_installation.md`
* Code historique (hors `main`) : branches `dev`/`version1` (client EW, **à réutiliser**), `version2` (page web `public/` à réutiliser, moteur widgets **à abandonner**), `link_flows` (ignorer).

## Règles
* Une seule application, volontairement basique. **Ne pas** réintroduire de moteur générique « widgets/flux/connecteurs ».
* Cibles : **macOS, Windows, Linux** (même code ; ne pas utiliser d'API spécifique à un OS sans repli).
* Topologie actuelle : EW sur un PC Windows, OBS **et l'application** sur un Mac. Variante envisagée : application sur le PC Windows d'EW, en démarrage automatique.
* EW exige **Bonjour** sur son PC pour activer la télécommande (protocole exploité) ; ne pas le contourner.
* L'application est en **lecture seule** vis-à-vis d'EasyWorship.
* Le protocole EW est non documenté : toute modification de `ew_client` doit être couverte par un test sur trames rejouées. Ne pas inventer de messages.
* Aucune dépendance réseau externe à l'exécution (pas de CDN).
* Pas d'écriture dans le dossier d'installation ; config et logs dans le dossier utilisateur de l'OS.
* Pas d'IP en dur ; `client_id` (`uid`) généré **une fois par installation** et conservé dans la config : EW répond `notPaired` à un `uid` neuf et attend l'acceptation de l'opérateur sur le PC EW (`doc/protocole_easyworship.md` §8). L'appairage est durable ; sa révocation dans EW ferme la connexion TCP sans message (§9) → reconnexion automatique. Le champ `permissions` (mode contrôle d'EW) est ignoré. Version d'EW testée : 7.4.1.9.
* Fixture de référence : `tests/fixtures/ew_session_reelle_anonymisee.jsonl` (capture réelle anonymisée) ; constats dans `doc/protocole_easyworship.md` §7. Clé de détection d'une diapo : `(pres_rowid, slide_rowid)`, pas `imagehash`. Les identifiants arrivent en **chaînes**.
* Ne pas pousser sur une autre branche que celle de la tâche ; ne pas créer de PR sans demande.

## Commandes (cible, une fois le code en place)
* Tests : `pytest` · Lint : `ruff check .` · Lancer : `python -m ew_to_obs --headless`
* Build : voir `doc/build_et_installation.md`

## Questions ouvertes
Voir `doc/plan_de_migration.md` (questions restantes : cas non capturés, persistance de l'appairage, fonctions optionnelles).
