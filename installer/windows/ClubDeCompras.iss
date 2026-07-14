#ifndef MyAppVersion
  #error MyAppVersion must be passed by the build script from app/version.py
#endif

#define MyAppName "Bella Vita - Club de Compras"
#define MyAppPublisher "Bella Vita"
#define MyAppExeName "Club de Compras.exe"
#define MyAppDirName "Bella Vita\Club de Compras"

[Setup]
AppId={{F7B2E78C-77A7-4E56-91A4-8D7F76C0C101}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppDirName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename=BellaVita_ClubDeCompras_Setup_{#MyAppVersion}
SetupIconFile=..\..\assets\icons\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
CloseApplications=yes
RestartApplications=no
InfoAfterFile=datos_conservados.txt

[Files]
Source: "..\..\dist\Club de Compras\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Bella Vita - Club de Compras"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Los datos locales en %LOCALAPPDATA%\ClubCompras se conservan para actualizaciones o reinstalaciones.
