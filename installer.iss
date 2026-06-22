; Inno Setup script for Lethe — the document de-identifier.
; Builds a per-user (no-admin) installer that wraps the portable bundle.
;
; Build:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
; Output: dist\Lethe-<ver>-Setup.exe
;
; Prereq: dist\DeIdentifier-Portable\ must exist (run build_portable.ps1 first).
; Silent deploy for IT:  Lethe-<ver>-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES

#define AppName "Lethe"
#define AppVer  "1.3.1"
#define Pub     "Meng Huey"

[Setup]
AppId={{8F3C2A14-7D9E-4B6A-9C21-DE1D0A11F001}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher={#Pub}
; Per-user install -> no administrator rights required:
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={localappdata}\Programs\Lethe
DisableProgramGroupPage=yes
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=Lethe-{#AppVer}-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
; ARP / uninstall metadata
VersionInfoVersion={#AppVer}
VersionInfoCompany={#Pub}
VersionInfoDescription={#AppName} setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Wrap the entire portable bundle (embedded Python + app + deps).
Source: "dist\DeIdentifier-Portable\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}";            Filename: "{app}\Launch De-identifier.bat"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#AppName}";  Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}";      Filename: "{app}\Launch De-identifier.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Launch De-identifier.bat"; Description: "Launch {#AppName} now"; \
  Flags: postinstall shellexec skipifsilent nowait

[UninstallDelete]
; Remove the bundled runtime (incl. .pyc caches the app regenerates at run time,
; which Inno doesn't track) and the OCR language models under data\tessdata (the
; bundled English one plus any the user downloaded — all re-downloadable, not
; user data). The downloaded spaCy detection models live under runtime\, so they
; go with it. The user's dictionary + vault under data\ are kept so a reinstall
; preserves them.
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\data\tessdata"
Type: filesandordirs; Name: "{app}\__pycache__"
