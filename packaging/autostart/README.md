# Démarrage automatique en arrière-plan (sans fenêtre)

Usage retenu : **installation à partir des sources** (voir [doc/notice_installation.md](../../doc/notice_installation.md)). Une fois `python -m ew_to_obs --host NOM --serve --loglevel 2 --saveconf` passé (enregistre la configuration sans démarrer), le démarrage de la machine lance : `python -m ew_to_obs --headless --serve`.

* **Windows** (PC d'EW) — **validé en réel** : `ew_to_obs_tache.cmd`, depuis le dépôt, dans une invite **administrateur** (venv `.venv` ou `venv` détecté, ou son nom en argument). Il crée la tâche planifiée « Easyworship vers OBS » **au démarrage du PC** via PowerShell (batterie autorisée, sans limite de durée, relance automatique), la lance aussitôt et affiche son état. Journal : `%APPDATA%\ew_to_obs\ew_to_obs.log`. Reste à vérifier : redémarrage complet (recette R-112).
* **macOS** — *non validé* : `ew_to_obs.launchd.plist` (remplacer `NOM` et les chemins) → `~/Library/LaunchAgents/io.github.ew-to-obs.plist`, puis `launchctl load ~/Library/LaunchAgents/io.github.ew-to-obs.plist`.
* **Linux** — *non validé* : `ew_to_obs.service` → `~/.config/systemd/user/`, puis `systemctl --user enable --now ew_to_obs` (ou `@reboot cd DÉPÔT && .venv/bin/python -m ew_to_obs --headless --serve` dans la crontab).
