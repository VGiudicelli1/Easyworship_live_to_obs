# Build et installation

> **État** : `packaging/` (spec PyInstaller, installeur Inno Setup, test de fumée) et `.github/workflows/release.yml` sont écrits. Seul le build Linux a été essayé en local ; les builds Windows/macOS et l'installeur n'ont **jamais tourné** (tests R-100…R-107 de `doc/recette.md`). Le workflow ne se déclenche que sur un tag `v*` ou à la main (onglet Actions, pour essayer sans publier).

## Publier une version
1. Mettre à jour la version dans `pyproject.toml` et `src/ew_to_obs/__init__.py`.
2. `git tag vX.Y.Z && git push origin vX.Y.Z` : tests, build, test de fumée sur les 3 systèmes, puis Release avec `ew_to_obs-setup-X.Y.Z.exe`, `ew_to_obs-X.Y.Z-macos.zip`, `ew_to_obs-X.Y.Z-linux.tar.gz`.
3. Build local : `pip install pyinstaller && pyinstaller packaging/ew_to_obs.spec --clean -y`, puis `python packaging/smoke.py dist/ew_to_obs/ew_to_obs`.


## État actuel
* `Makefile` : uniquement macOS, cible `dist/ew_to_txt.app` alors que la sortie PyInstaller s'appelle `ew_to_obs`, chemin `--paths lib/python3.8/site-packages` incompatible avec la CI en Python 3.12.
* CI GitHub Actions : sur Ubuntu, installe les dépendances, lance `make`, `ls build`. **Pas d'artefact, pas de test, pas d'installeur.**
* L'utilisateur doit recopier à la main `public/` dans l'application.
* `requirements.txt` contient des paquets macOS.

## Cible
Un utilisateur télécharge **un installeur** depuis la page *Releases* du dépôt, l'exécute, lance « Easyworship → OBS » depuis le menu Démarrer / Applications.

| Plateforme | Livrable | Outil |
|---|---|---|
| macOS (**usage actuel** : Mac d'OBS) | `ew_to_obs-X.Y.Z.dmg` (app `.app`) | PyInstaller + `create-dmg` |
| Windows (variante : PC d'EW, démarrage auto) | `ew_to_obs-setup-X.Y.Z.exe` | PyInstaller `--onedir` + **Inno Setup** |
| Linux | Archive `.tar.gz` (ou AppImage plus tard) | PyInstaller |

Objectif multiplateforme confirmé par le mainteneur : mêmes sources, matrice CI sur les trois OS. Priorité de livraison : macOS, puis Windows, puis Linux.

**Mode service** : `ew_to_obs --ci --host NOM --loglevel 2 2>> ew_logs.log` (sans fenêtre) ; modèles de démarrage automatique (launchd, systemd, tâche planifiée Windows) dans `packaging/autostart/`.

## Étapes

### 1. Structure du dépôt
```
src/ew_to_obs/        code (paquet)
src/ew_to_obs/public/ page web embarquée
tests/
packaging/windows/installer.iss
packaging/macos/…
pyproject.toml        dépendances + version unique
```
`pyproject.toml` remplace `requirements.in/.txt` et la version dupliquée dans `constants.py` (le tag Git fait foi).

### 2. Exécution en local (développeur)
```
python -m venv .venv
.venv/Scripts/activate        # ou source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m ew_to_obs
```

### 3. Build local
```
pyinstaller packaging/ew_to_obs.spec --clean -y     # produit dist/ew_to_obs/
iscc packaging/windows/installer.iss                # Windows : produit l'installeur
```
Le fichier `.spec` embarque `public/` via `datas=[("src/ew_to_obs/public", "ew_to_obs/public")]` et résout le chemin avec `importlib.resources` / `sys._MEIPASS` (plus de `os.chdir`).

### 4. CI/CD (GitHub Actions)
* Déclencheurs : `push`/`pull_request` → lint + tests + build de contrôle ; **tag `v*`** → build des installeurs + création d'une *Release* avec les artefacts.
* Matrice : `macos-latest`, `windows-latest`, `ubuntu-latest` ; Python 3.12.
* Étapes : checkout → setup-python → `pip install -e ".[dev]"` → `pytest` → PyInstaller → installeur → `actions/upload-artifact` → (tag) `softprops/action-gh-release`.

### 5. Installation côté utilisateur
1. Télécharger l'installeur depuis *Releases*.
2. Windows : SmartScreen peut avertir (exécutable non signé) → « Informations complémentaires » → « Exécuter quand même ». Documenter avec capture d'écran. Pare-feu : accepter la demande d'accès réseau privé au premier lancement (ou fournir une règle créée par l'installeur).
3. Premier lancement : choisir le PC EasyWorship (liste auto ou saisie du nom) → l'URL pour OBS s'affiche.
4. Dans OBS : *Sources → + → Navigateur* → coller l'URL (ex. `http://localhost:8000/?lines=4`) → largeur/hauteur = **le bandeau de sous-titres** (ex. 1920 × 360). Pour l'avoir sur toutes les scènes caméra : *Ajouter une source existante* dans chaque scène (une seule source navigateur, donc une seule connexion). Laisser la source active même hors scène : la page garde le texte à jour et l'affiche tout de suite au changement de scène.
5. Option « Démarrer avec le système » : Windows (dossier Démarrage), macOS (Éléments de connexion / LaunchAgent), Linux (autostart). Cas visé : application sur le PC Windows d'EW.
6. Prérequis côté EW : installer **Bonjour** sur le PC EW (sinon la télécommande EW ne s'active pas).

### 6. Mise à jour
Phase 1 : manuelle (télécharger la nouvelle version). Phase 2 (optionnel) : l'application interroge l'API GitHub *latest release* au démarrage et affiche « Nouvelle version disponible ».

### 7. Désinstallation et données
Désinstalleur Inno Setup ; la configuration utilisateur (`%APPDATA%\ew_to_obs`) est conservée (option pour la supprimer).

## Points de vigilance
* `--onefile` est plus lent au démarrage (extraction temporaire) et plus souvent détecté comme faux positif par les antivirus → préférer `--onedir`.
* Signature de code : coûteuse ; à envisager seulement si SmartScreen pose problème en pratique.
* Vérifier les *hidden imports* de PyInstaller (aiohttp, zeroconf) ; ajouter un **test de fumée** en CI qui lance l'exécutable construit en `--headless --selftest` et vérifie que `GET /` répond.
