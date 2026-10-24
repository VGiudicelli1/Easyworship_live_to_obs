# Démarrage automatique en arrière-plan (sans fenêtre)

Commande de service : `ew_to_obs --ci --host NOM_DU_PC_EW --loglevel 2 2>> ew_logs.log`
(équivaut à `--headless --serve` ; le PC EW est mémorisé, `--host` n'est utile qu'au 1er lancement ;
le journal détaillé est aussi dans le dossier de configuration, `ew_to_obs.log`).

**Fichiers jamais essayés en réel** (recette R-108 à R-110) : adapter les chemins.

* **macOS** : `ew_to_obs.launchd.plist` → `~/Library/LaunchAgents/io.github.ew-to-obs.plist`, puis
  `launchctl load ~/Library/LaunchAgents/io.github.ew-to-obs.plist`.
* **Windows** : `ew_to_obs_tache.cmd` (tâche planifiée à l'ouverture de session, sans fenêtre).
* **Linux** : `ew_to_obs.service` → `~/.config/systemd/user/`, puis
  `systemctl --user enable --now ew_to_obs`.
