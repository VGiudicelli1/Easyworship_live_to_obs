# Notice d'installation

Application « EW vers OBS » : elle lit la diapo en direct d'**EasyWorship** (EW) et la rend disponible, sous forme de page web, pour une **Source navigateur** d'**OBS** (sous-titres des chants sur les scènes caméra).

> Durée : 15 à 20 minutes la première fois. À faire sur le PC qui exécutera l'application.

## 1. Choisir où installer l'application

| Cas | L'application tourne sur… | Adresse à mettre dans OBS | Démarrage |
|---|---|---|---|
| **A. PC d'EasyWorship** (recommandé) | le PC Windows d'EW | `http://NOM_DU_PC_EW:8000/` | automatique au démarrage du PC (§4) |
| **B. Mac d'OBS** | le Mac qui exécute OBS | `http://localhost:8000/` | à la main (fenêtre) ou service (§5) |

Une seule application suffit : elle sert la page à tout le réseau local, donc OBS peut être sur une autre machine. **Ne l'installez pas aux deux endroits.**

## 2. Prérequis

* **EasyWorship 7** (testé : 7.4.1.9) avec la *télécommande* possible. EW exige que **Bonjour** (Apple) soit installé sur son PC.
* **Python 3.12 ou plus récent** (python.org). Windows : cocher « Add python.exe to PATH » à l'installation. Mac : le Python de python.org (il contient Tkinter, nécessaire à la fenêtre).
* **Git** pour récupérer le code.
* **OBS** avec les *Sources navigateur* (incluses).
* Les deux machines sur le **même réseau local**.

## 3. Installer l'application (Windows, cas A)

Dans une invite de commandes (`cmd`) :

```
git clone https://github.com/vgiudicelli1/easyworship_live_to_obs
cd easyworship_live_to_obs
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
pip install -r venv/requirements.txt
pip install -e . --no-deps
```

* Dans **PowerShell**, l'activation (`Activate.ps1`) peut être refusée (« exécution de scripts désactivée »). Utiliser `cmd`, ou appeler Python directement : `.venv\Scripts\python -m pip install …`, ou autoriser les scripts pour son compte : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
* Si `py -3.12` n'existe pas, utiliser la version installée (`py -3.13`, `py -3.15`…).

### Enregistrer la configuration

```
python -m ew_to_obs --host localhost --serve --loglevel 2 --saveconf
```

Remplacer `localhost` par le nom du PC d'EW si l'application n'est pas sur ce PC (cas B). Cette commande **n'ouvre rien et ne se connecte pas** : elle enregistre le PC, l'identité de la télécommande et les options dans `%APPDATA%\ew_to_obs\config.json`.

### Premier lancement et appairage (une seule fois)

```
python -m ew_to_obs --headless
```

1. EasyWorship affiche une demande pour la télécommande **« ew2obs (NOM_DE_LA_MACHINE) »** : **l'accepter**.
2. Le terminal indique la connexion. Passer une diapo dans EW pour vérifier.
3. Ouvrir `http://NOM_DU_PC:8000/?demo=1` dans un navigateur : le texte de démonstration doit s'afficher.
4. Arrêter avec **Ctrl+C**.

L'appairage est durable : il n'est demandé qu'une fois, tant que le dossier de configuration est conservé.

## 4. Démarrage automatique (Windows)

Dans une invite de commandes **administrateur**, depuis le dossier du dépôt :

```
packaging\autostart\ew_to_obs_tache.cmd
```

Cela crée la tâche planifiée **« Easyworship vers OBS »** : lancée **au démarrage du PC** (sans ouvrir de session), batterie autorisée, sans limite de durée, relancée automatiquement en cas d'arrêt. Le script la démarre aussitôt et affiche son état ; on peut le relancer sans danger (il remplace la tâche). Si le venv porte un autre nom : `ew_to_obs_tache.cmd NOM_DU_VENV`.

Vérifications :

* `schtasks /Query /TN "Easyworship vers OBS"` : état « En cours ».
* Journal : `%APPDATA%\ew_to_obs\ew_to_obs.log` (voir [notice d'utilisation](notice_utilisation.md#6-dépannage)).
* Redémarrer le PC **avant** d'ouvrir EW : au lancement d'EW, le texte doit suivre sans rien démarrer à la main.

Arrêter ou retirer : `schtasks /End /TN "Easyworship vers OBS"` puis `schtasks /Delete /TN "Easyworship vers OBS" /F`.

## 5. Installer sur Mac (cas B) ou Linux

Même procédure, avec `source .venv/bin/activate` et `python3.12`. Puis :

```
python -m ew_to_obs                  # ouvre la fenêtre : saisir le nom du PC EW, « Appliquer »
```

La fenêtre mémorise le PC. Pour un service sans fenêtre au démarrage : modèles `launchd` (Mac) et `systemd` (Linux) dans [`packaging/autostart/`](../packaging/autostart/README.md) (non validés en réel). Si Tkinter manque : Python de python.org, ou `brew install python-tk` (Mac) / `sudo apt install python3-tk` (Linux) ; sinon utiliser `--headless`.

## 6. Configurer OBS

Voir la [notice d'utilisation](notice_utilisation.md#2-dans-obs) : une source *Navigateur* avec l'adresse `http://NOM_DU_PC_EW:8000/?lines=4`.

## 7. Pare-feu et réseau

* Au premier lancement, Windows peut demander d'autoriser l'accès au **réseau privé** : accepter, sinon OBS ne voit pas la page (port **8000**).
* Si le **nom** du PC ne se résout pas depuis le Mac, utiliser son **adresse IP** (`ipconfig` → ligne IPv4) dans OBS.
* L'application n'a **aucune authentification** : réseau de confiance seulement. Pour limiter à la machine : `--web-bind 127.0.0.1 --saveconf`.
* L'application est en **lecture seule** vis-à-vis d'EasyWorship : elle n'envoie aucune commande.

## 8. Mettre à jour

```
cd easyworship_live_to_obs
git pull
.venv\Scripts\python -m pip install -r venv/requirements.txt
```
Puis redémarrer l'application : `schtasks /End /TN "Easyworship vers OBS"` puis `schtasks /Run /TN "Easyworship vers OBS"` (ou redémarrer le PC). La configuration et l'appairage sont conservés (ils sont dans `%APPDATA%\ew_to_obs`, pas dans le dépôt).

## 9. Désinstaller

1. Supprimer la tâche : `schtasks /Delete /TN "Easyworship vers OBS" /F`.
2. Supprimer le dossier du dépôt.
3. Optionnel : supprimer `%APPDATA%\ew_to_obs` (**perd l'appairage** : EW redemandera d'accepter la télécommande) et retirer « ew2obs (…) » des télécommandes d'EW.

## 10. Exécutable et installeur (non validés)

`packaging/` contient une spécification PyInstaller, un installeur Inno Setup et un workflow de publication (`.github/workflows/release.yml`, déclenché par un tag `vX.Y.Z`). Ils **n'ont pas été essayés en réel** : l'installation à partir des sources ci-dessus est la procédure de référence. Détails : [build_et_installation.md](build_et_installation.md).
