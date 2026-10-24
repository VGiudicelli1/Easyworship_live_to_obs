@echo off
rem Tâche planifiée Windows : démarre l'application sans fenêtre à l'ouverture de session.
rem Adapter le chemin et le nom du PC EW. Supprimer : schtasks /Delete /TN "Easyworship vers OBS" /F
schtasks /Create /TN "Easyworship vers OBS" /SC ONLOGON /RL LIMITED /F /TR "cmd /c \"\"%LOCALAPPDATA%\Programs\Easyworship vers OBS\ew_to_obs.exe\" --ci --host NOM_DU_PC_EW.local --loglevel 2 2>> %APPDATA%\ew_to_obs\ew_logs.log\""
