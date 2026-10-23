# Plan de migration vers l'application unique

Chaque étape est livrable séparément et se termine par une application qui fonctionne.

| # | Étape | Résultat vérifiable | Source réutilisée |
|---|---|---|---|
| 0 | Branche d'intégration depuis `main`; importer `dev` (EW) et la page `public/` de `version2`. Nettoyer le `.gitignore` | Arborescence cible, CI verte (lint + tests vides) | `dev`, `version2` |
| 1 | `ew_client` asynchrone + `LiveState`; corriger `Slide.isNull`, diapo vide, reconnexion | Tests `pytest` sur trames rejouées ; CLI `--headless` qui imprime les changements de diapo | `ew_api.py`, `storage.py` |
| 2 | `web_server` aiohttp : HTTP statique + WebSocket + état courant à la connexion ; page sans CDN | Test automatique : un client WS reçoit l'état ; page vue dans OBS | `output_web.py`, `public/` |
| 3 | `config` (JSON) + `client_id` généré + hôte mémorisé | Redémarrage = même hôte, aucune saisie | nouveau |
| 4 | `discovery` : résolution du nom à chaque connexion + recherche mDNS | Changement d'IP DHCP sans intervention (test sur site) | nouveau |
| 5 | `ui` Tkinter minimale (voir `spec/interfaces.md`) | Opérateur non technique réussit sans aide | `interface.py` v1 |
| 6 | Packaging Windows (PyInstaller + Inno Setup, variante PC d'EW) et release par tag | Installeur téléchargeable, installation sur PC vierge | `Makefile`, CI |
| 7 | Packaging macOS (cible actuelle) et Linux (archive) | `.dmg` / archive | `Makefile` |
| 7bis | Démarrage automatique par OS (option) | Redémarrage session = app lancée | nouveau |
| 8 | Essai réel pendant un culte, correction | Critères de réussite de `spec/metier.md` | — |
| 9 | Documentation utilisateur (captures), README, versions EW/OBS testées | README à jour | — |
| 10 | Ménage de dépôt : fusion dans `main`, tags `v1.0.0` / `v2.0.0-abandonné`, suppression de `link_flows`, `dev`/`version1` | Branches propres | — |

## Ordre recommandé et justification
1 → 2 → 3 donne tout de suite la valeur principale (EW → OBS sans fichier intermédiaire), testable en `--headless`, avant tout travail d'interface. Le packaging (6) est mis tôt car c'est le point faible historique ; on le fait tourner dès qu'il y a un exécutable minimal.

## Questions ouvertes (bloquantes pour certaines étapes)
**Réponses du mainteneur (2e échange)** : multiplateforme Mac/Windows/Linux (usage Mac, Windows envisagé en démarrage auto sur le PC d'EW) ; OBS sur Mac, EW sur Windows, applications sur le Mac ; EW 7 ; export fichier / crédits / filtre probablement abandonnés ; capture de trames à faire dès l'accès à EW. Prérequis : Bonjour sur le PC EW.

Restent ouvertes :
1. ~~Capture de trames réelles~~ : **3 captures faites le 2026-10-23** (voir `doc/protocole_easyworship.md` §7 à §9, fixtures `tests/fixtures/`) : lecture des diapos, appairage, mode contrôle, révocation. Reste une 4e capture pour : diapo **sans texte** (images seules), coupure réseau / redémarrage d'EW / reconnexion après révocation (`--reconnect`), diapo modifiée en direct, attente prolongée sans réponse à la demande d'appairage, logo/noir/clear (vus dans la 1re capture).
2. ~~Version exacte d'EW 7~~ : **7.4.1.9**.
3. Démarrage automatique : à la demande, étape 7bis (après la v1 de l'installeur).
4. Rendu souhaité dans OBS (fond semi-transparent actuel, police, position) : personnalisable par paramètres d'URL ?
