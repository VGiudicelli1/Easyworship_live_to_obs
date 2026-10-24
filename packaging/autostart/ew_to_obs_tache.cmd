@echo off
rem Démarrage automatique Windows : tâche planifiée « au démarrage du PC » (avant toute session).
rem À lancer UNE fois, depuis la racine du dépôt, dans une invite de commandes ADMINISTRATEUR,
rem après l'installation (venv + « --saveconf », voir README). Retirer :
rem   schtasks /Delete /TN "Easyworship vers OBS" /F
setlocal
set "REPO=%~dp0..\.."
pushd "%REPO%" & set "REPO=%CD%" & popd
set "CONF=%APPDATA%\ew_to_obs"
if not exist "%REPO%\.venv\Scripts\python.exe" (echo .venv introuvable dans %REPO% & exit /b 1)
if not exist "%CONF%\config.json" (echo Lancer d'abord --saveconf : %CONF%\config.json absent & exit /b 1)
rem La tâche tourne sous SYSTEM : on lui donne explicitement le dossier de config de CET utilisateur
rem (identité d'appairage et PC EW déjà enregistrés).
schtasks /Create /TN "Easyworship vers OBS" /SC ONSTART /RU SYSTEM /RL HIGHEST /F /TR "cmd /c cd /d \"%REPO%\" && .venv\Scripts\python.exe -m ew_to_obs --headless --serve --config-dir \"%CONF%\" 2>> \"%CONF%\ew_logs.log\""
if errorlevel 1 (echo Échec : administrateur ? & exit /b 1)
echo Tâche créée. Test immédiat : schtasks /Run /TN "Easyworship vers OBS"
