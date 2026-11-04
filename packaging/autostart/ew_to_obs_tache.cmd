@echo off
rem Démarrage automatique Windows : tâche planifiée « au démarrage du PC » (avant toute session).
rem À lancer UNE fois, depuis la racine du dépôt, dans une invite de commandes ADMINISTRATEUR,
rem après l'installation (venv + « --saveconf », voir README). Retirer :
rem   schtasks /Delete /TN "Easyworship vers OBS" /F
setlocal
set "REPO=%~dp0..\.."
pushd "%REPO%" & set "REPO=%CD%" & popd
set "CONF=%APPDATA%\ew_to_obs"
rem Le venv s'appelle .venv ou venv (le dossier venv\ du dépôt contient aussi les requirements) ;
rem un autre nom peut être donné en argument : ew_to_obs_tache.cmd mon_venv
set "VENV=%~1"
if "%VENV%"=="" if exist "%REPO%\.venv\Scripts\python.exe" set "VENV=.venv"
if "%VENV%"=="" if exist "%REPO%\venv\Scripts\python.exe" set "VENV=venv"
if not exist "%REPO%\%VENV%\Scripts\python.exe" (echo Aucun venv trouve dans %REPO% ^(.venv, venv^) & exit /b 1)
if not exist "%CONF%\config.json" (echo Lancer d'abord --saveconf : %CONF%\config.json absent & exit /b 1)
rem La tâche tourne sous SYSTEM : on lui donne explicitement le dossier de config de CET utilisateur
rem (identité d'appairage et PC EW déjà enregistrés).
schtasks /Create /TN "Easyworship vers OBS" /SC ONSTART /RU SYSTEM /RL HIGHEST /F /TR "cmd /c cd /d \"%REPO%\" && %VENV%\Scripts\python.exe -m ew_to_obs --headless --serve --config-dir \"%CONF%\" 2>> \"%CONF%\ew_logs.log\""
if errorlevel 1 (echo Échec : administrateur ? & exit /b 1)
echo Tâche créée. Test immédiat : schtasks /Run /TN "Easyworship vers OBS"
