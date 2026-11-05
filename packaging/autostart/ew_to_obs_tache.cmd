@echo off
rem Démarrage automatique Windows : tâche planifiée « au démarrage du PC » (avant toute session).
rem À lancer depuis une invite de commandes ADMINISTRATEUR, après « --saveconf » (voir README).
rem   ew_to_obs_tache.cmd [nom_du_venv]        (par défaut : .venv puis venv)
rem Retirer : schtasks /Delete /TN "Easyworship vers OBS" /F
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ew_to_obs_tache.ps1" %*
