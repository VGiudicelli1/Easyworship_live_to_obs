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
* Aucune dépendance réseau externe à l'exécution (pas de CDN). La page affiche le texte en **texte brut** (`textContent`, jamais `innerHTML`) ; serveur web sur `127.0.0.1` par défaut. Tout changement de `public/` doit rester couvert par `tests/test_page.py` (Chromium via Playwright, ignoré s'il est absent).
* Pas d'écriture dans le dossier d'installation ; config et logs dans le dossier utilisateur de l'OS.
* Pas d'IP en dur ; `client_id` (`uid`) généré **une fois par installation** et conservé dans la config : EW répond `notPaired` à un `uid` neuf et attend l'acceptation de l'opérateur sur le PC EW (`doc/protocole_easyworship.md` §8). L'appairage est durable ; sa révocation dans EW ferme la connexion TCP sans message (§9) → reconnexion automatique. Le champ `permissions` (mode contrôle d'EW) est ignoré. Version d'EW testée : 7.4.1.9.
* Fixture de référence : `tests/fixtures/ew_session_reelle_anonymisee.jsonl` (capture réelle anonymisée) ; constats dans `doc/protocole_easyworship.md` §7. Diapo en direct = `(pres_rowid, slide_rowid)` du dernier `status`, **jamais `imagehash`** (diapos vides identiques). Règle d'émission : recalculer `(visible, texte)` à chaque message et ne diffuser que s'il change ; texte vide valide ; nouveau `liverev` ⇒ tout recharger ; ignorer `permissions`, `schedulerev`, `rectype` (`spec/technique.md`, `doc/protocole_easyworship.md` §10). Les identifiants arrivent en **chaînes**. Le port d'EW change à chaque lancement d'EW : redécouvrir à **chaque** tentative de connexion. Cache des diapos vidé à chaque nouveau `liverev` (identifiants des chants négatifs et éphémères). Rien en direct = `imagehash` vide. Perte de connexion > 2 s (`lost_grace_seconds`) ⇒ `visible=false` ; en dessous, garder le texte (pas de clignotement, §11 et `spec/technique.md`). Aucun champ « port EW » dans l'interface. Nom résolu en IPv4 seule + `last_ip` mémorisée (§14). Texte = toujours `content` (diapo avec média + texte : le texte est diffusé ; média seul : texte vide ; ni média ni compte à rebours transmis) ; texte brut sans mise en forme ; décoder l'UTF-8 avec remplacement. Réseau : **IPv4 d'abord** (l'IPv6 ne répond jamais côté EW), requêtes mDNS parallèles, délais courts par adresse, jamais cumulés (`doc/protocole_easyworship.md` §12).
* Ne pas pousser sur une autre branche que celle de la tâche ; ne pas créer de PR sans demande.
* **Crédits GitHub Actions limités** (consigne du mainteneur, qui a d'autres projets) : **peu de push**. Travailler et valider en local (`ruff`, `pytest`, tests navigateur), regrouper en un seul push par lot de travail terminé, jamais un push par petite correction. La CI ne tourne que sur PR, sur `main` et à la demande (voir `.github/workflows/tests.yml`).

## Commandes
* Installer : `pip install -e ".[dev]"` · Tests : `python -m pytest` · Lint : `ruff check src tests && ruff format --check src tests`
* Lancer le client seul : `python -m ew_to_obs --host NOM_OU_IP` (une ligne JSON par changement d'état) ; avec la page pour OBS : ajouter `--serve` (`--web-port`, `--web-bind`)
* Code : `src/ew_to_obs/` (`protocol`, `live`, `discovery`, `client`, `web`, `public/`) ; tests : `tests/` (fixtures réelles anonymisées dans `tests/fixtures/`, faux EW dans `tests/fake_ew.py`). `tools/ew_capture.py` reste un outil autonome (code mDNS volontairement dupliqué).
* Build : voir `doc/build_et_installation.md`

## Questions ouvertes
Voir `doc/plan_de_migration.md` (questions restantes : cas non capturés, persistance de l'appairage, fonctions optionnelles).
