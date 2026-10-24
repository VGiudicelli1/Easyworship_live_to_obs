; Inno Setup : iscc /DAppVersion=1.2.3 packaging\windows\installer.iss
; Entrée : dist\ew_to_obs\ (PyInstaller --onedir). Sortie : dist\ew_to_obs-setup-X.Y.Z.exe
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F1B4C52-3C2D-4B7E-9E55-0E7A2D1F9A31}
AppName=Easyworship vers OBS
AppVersion={#AppVersion}
DefaultDirName={autopf}\Easyworship vers OBS
DefaultGroupName=Easyworship vers OBS
OutputDir=..\..\dist
OutputBaseFilename=ew_to_obs-setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\ew_to_obs.exe

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "autostart"; Description: "Démarrer avec Windows"; Flags: unchecked

[Files]
Source: "..\..\dist\ew_to_obs\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Easyworship vers OBS"; Filename: "{app}\ew_to_obs.exe"
Name: "{userstartup}\Easyworship vers OBS"; Filename: "{app}\ew_to_obs.exe"; Tasks: autostart

[Run]
Filename: "{app}\ew_to_obs.exe"; Description: "Lancer Easyworship vers OBS"; Flags: nowait postinstall skipifsilent

; La configuration (%APPDATA%\ew_to_obs, dont l'identité d'appairage) est conservée à la
; désinstallation : réinstaller ne redemande pas d'accepter la télécommande dans EW.
