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
| 6 | Packaging Windows (PyInstaller + Inno Setup) et release par tag | Installeur téléchargeable, installation sur PC vierge | `Makefile`, CI |
| 7 | Packaging macOS (si besoin) | `.dmg` | `Makefile` |
| 8 | Essai réel pendant un culte, correction | Critères de réussite de `spec/metier.md` | — |
| 9 | Documentation utilisateur (captures), README, versions EW/OBS testées | README à jour | — |
| 10 | Ménage de dépôt : fusion dans `main`, tags `v1.0.0` / `v2.0.0-abandonné`, suppression de `link_flows`, `dev`/`version1` | Branches propres | — |

## Ordre recommandé et justification
1 → 2 → 3 donne tout de suite la valeur principale (EW → OBS sans fichier intermédiaire), testable en `--headless`, avant tout travail d'interface. Le packaging (6) est mis tôt car c'est le point faible historique ; on le fait tourner dès qu'il y a un exécutable minimal.

## Questions ouvertes (bloquantes pour certaines étapes)
1. OS cibles (étape 6–7) ?
2. OBS sur le même PC qu'EW (adresse d'écoute, pare-feu) ?
3. Version(s) d'EasyWorship utilisée(s) ?
4. Conserver l'export fichier, la règle « crédits », le filtre de présentations ?
5. Accès à une capture de trames réelles d'EW, ou possibilité d'en faire une ?
6. Rendu souhaité dans OBS (fond semi-transparent actuel, police, position) : personnalisable par paramètres d'URL ?
