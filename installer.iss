; Inno Setup script for StarPing
; Build: iscc installer.iss (Inno Setup 6+)
; Produces: dist/StarPing-Setup.exe

#define AppName "StarPing"
#define AppPublisher "AnarchyGames.org"
#define AppURL "https://anarchygames.org"
#define AppExeName "StarPing.exe"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{B7F2E8A4-6C5E-4A8B-9D3F-STARPING0001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=StarPing-Setup
Compression=lzma2/ultra
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; PyInstaller output — entire StarPing/ directory
Source: "dist\StarPing\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Chromium bundle — staged by the GH Actions build step into chromium_stage/
; This unpacks to %LOCALAPPDATA%\ms-playwright\ so Playwright finds it on first run.
Source: "chromium_stage\*"; DestDir: "{localappdata}\ms-playwright"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
