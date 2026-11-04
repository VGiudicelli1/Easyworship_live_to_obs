# Tâche planifiée Windows « au démarrage du PC » (appelée par ew_to_obs_tache.cmd).
param([string]$Venv = "")
$ErrorActionPreference = "Stop"
$name = "Easyworship vers OBS"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $Venv) {
    foreach ($candidate in ".venv", "venv") {
        if (Test-Path (Join-Path $repo "$candidate\Scripts\python.exe")) { $Venv = $candidate; break }
    }
}
$python = Join-Path $repo "$Venv\Scripts\python.exe"
if (-not $Venv -or -not (Test-Path $python)) { throw "Aucun venv trouve dans $repo (.venv, venv)" }
$conf = Join-Path $env:APPDATA "ew_to_obs"
if (-not (Test-Path (Join-Path $conf "config.json"))) {
    throw "Lancer d'abord --saveconf : $conf\config.json est absent"
}

# Python direct (pas de cmd) ; la tâche tourne sous SYSTEM, donc on donne explicitement le dossier de
# configuration de CET utilisateur. Le journal est $conf\ew_to_obs.log (écrit par l'application).
$action = New-ScheduledTaskAction -Execute $python -WorkingDirectory $repo `
    -Argument "-m ew_to_obs --headless --serve --config-dir `"$conf`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
# Un service permanent : batterie autorisée, aucune limite de durée (72 h par défaut sinon),
# relance automatique si le processus s'arrête.
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable -MultipleInstances IgnoreNew

Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Principal $principal `
    -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $name
Start-Sleep -Seconds 5
$info = Get-ScheduledTaskInfo -TaskName $name
Write-Host ("Tache '{0}' creee et lancee. Etat : {1} ; dernier resultat : {2}" -f `
    $name, (Get-ScheduledTask -TaskName $name).State, $info.LastTaskResult)
Write-Host "Journal : $conf\ew_to_obs.log"
Get-Content (Join-Path $conf "ew_to_obs.log") -Tail 8 -ErrorAction SilentlyContinue
