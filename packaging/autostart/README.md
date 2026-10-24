# Démarrage automatique en arrière-plan (sans fenêtre)

Usage retenu : **installation à partir des sources** (`git clone`, `.venv`, `pip install -r venv/requirements.txt`),
une fois `python -m ew_to_obs --host NOM --serve --loglevel 2 --saveconf` passé (enregistre la configuration sans
démarrer), puis lancement au démarrage de la machine par : `python -m ew_to_obs --headless --serve`.

**Fichiers jamais essayés en réel** (recette R-108 à R-111) : adapter les chemins.

* **Windows** (PC d'EW) : `ew_to_obs_tache.cmd`, en administrateur, depuis le dépôt : crée la tâche planifiée
  « au démarrage du PC ». Les erreurs vont dans `%APPDATA%\ew_to_obs\ew_logs.log`.
* **macOS** : `ew_to_obs.launchd.plist` (exécutable PyInstaller ; pour les sources, remplacer le programme par
  `…/.venv/bin/python -m ew_to_obs --headless --serve`) → `~/Library/LaunchAgents/io.github.ew-to-obs.plist`,
  puis `launchctl load …`.
* **Linux** : `ew_to_obs.service` → `~/.config/systemd/user/`, puis `systemctl --user enable --now ew_to_obs`
  (ou `@reboot cd DÉPÔT && .venv/bin/python -m ew_to_obs --headless --serve` dans la crontab).
