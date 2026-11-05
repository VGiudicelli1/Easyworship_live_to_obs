# Analyse des branches

État au 2026-10-22. Auteur unique : Vincent Giudicelli.

## Vue d'ensemble

```
main ── e1dced0 README ── LICENSE ── README (2024-06-02)
          └─ (dev / version1) 0cac927 … 6bfcf09 ── (2024-06-02 → 06-13, v1 EW→fichier)
                └─ 65d89c7 → 4194087 … 0b225c6 (2024-11-05 → 11-30, refonte v2)
                        ├─ version2   : 249fa02 « update css navigator » (2024-12-13)
                        └─ link_flows : e3766ff, a35de2d, 5590f2e (2024-12-01)
```

| Branche | Tête | Date | Commits propres | Rôle |
|---|---|---|---|---|
| `main` | `39102c2` | 2024-06-02 | 5 | README + licence MIT. Statut affiché : « In development, not operational » (obsolète) |
| `dev` | `6bfcf09` | 2024-06-13 | +14 depuis main | v1 : application EW → texte |
| `version1` | `6bfcf09` | 2024-06-13 | = `dev` | Étiquette de la v1 (même commit que `dev`) |
| `version2` | `249fa02` | 2024-12-13 | +16 depuis `dev` | v2 : widgets/flux + sortie web, build PyInstaller |
| `link_flows` | `5590f2e` | 2024-12-01 | 3 depuis le tronc v2 (version2 en a 1 de plus) | Expérimentation : tracé des liens entre widgets, tests |

Aucune branche n'a été fusionnée dans `main` : **`main` ne contient aucun code**.

## `main`
Seulement `README.md` et `LICENSE.txt` (MIT). Mentionne l'inspiration **ew2vm** (Michael Norton) et l'avertissement sur l'API non documentée.

## `dev` / `version1` — « EW → fichier texte »
Historique : 2024-06-02 → 06-13.

* `src/ew_api.py` (416 lignes) : client du protocole EW (voir `protocole_easyworship.md`), refactoré en POO depuis ew2vm.
* `src/storage.py` : état (`Slide`, `Storage`).
* `src/logger.py` : `LoggerSlideContentToTxt` écrit la diapo dans `ew_out.txt`.
* `src/interface.py` / `main.py` : fenêtre Tkinter (hôte, port, chemin de sortie, Start/Stop/Quit). Valeurs par défaut en dur, `load/save` vides.
* `src/test.py`, `test2.py` : brouillons.
* CI : Python 3.8, `pyinstaller -F`, `ls build`. Dépendances : `dnspython`, `pyinstaller 5.0.1`, `pillow`, `datetime` (inutile, c'est stdlib).
* Message de commit du 06-13 : « *Real test: OK* » → **testée avec succès sur un vrai EW**. C'est la seule version validée en conditions réelles.

## `version2` — « widgets / flux »
Historique : 2024-11-05 → 12-13. Refonte complète (`src_v1/` conserve l'ancien code).

* Idée : chaque brique est un *Widget* (entrée / sortie / transformation) avec options, paramètres, état (STOP/BUSY/RUN/ERROR) ; les widgets sont reliés par des *Flows* (valeur texte + callbacks).
* Implémenté : `Input_File` (watchdog sur un fichier), `Output_File`, `Output_Web` (serveur `eventlet` + `socketio`, sert `public/`), `Widget_Test`.
* Non implémenté (voir `todo.txt`) : entrée EW, ajout/suppression de composants, liaison des flux dans l'UI, sauvegarde/rappel, gestion d'erreurs, tests.
* Interface Tkinter : canvas déplaçable + panneau latéral du widget sélectionné.
* Page web : texte centré, police maximale via dichotomie, fond semi-transparent.
* Build : `Makefile` macOS, `main_imports_pyinstaller.py` (hidden imports eventlet/dnspython), CI Python 3.12.
* **Ne communique pas avec EW** : il faut lancer l'ancienne app v1 pour produire le fichier, d'où le retour utilisateur F1.

## `link_flows`
`version2` au commit `0b225c6` + :
* `e3766ff` tests (`widget_test.py`), `a35de2d` CSS, `5590f2e` « draw liflows » : `i_Flow` dessine des segments rouges sur le canvas, `Widget.set_selected`, `get_UID`.
* Divergente de `version2` (qui a un commit CSS de plus). Rien de réutilisable pour la cible.

## Recommandation
* **Réutiliser** de `dev` : `ew_api.py`, `storage.py` (corrigés, voir `spec/technique.md`).
* **Réutiliser** de `version2` : `public/` (page + dichotomie), idée de la sortie web, logique d'arrêt propre, `Makefile`/CI comme point de départ du build.
* **Abandonner** : tout le moteur widget/flux/canvas, `eventlet`, `socket.io`, `watchdog`.
* **Ménage** : une fois le code cible en place, intégrer dans `main`, supprimer `link_flows`, conserver `version1`/`version2` comme **tags** (`v1.0.0`, `v2.0.0-abandonné`) au lieu de branches.
* `dev` et `version1` pointent sur le même commit : supprimer l'un des deux.
