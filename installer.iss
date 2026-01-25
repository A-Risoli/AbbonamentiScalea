; Inno Setup Script for AbbonamentiScalea
; Sistema Abbonamenti Città di Scalea
;
; To compile this script:
; 1. Install Inno Setup: https://jrsoftware.org/isinfo.php
; 2. Run: iscc installer.iss
; 3. Output will be in installer_output/

#define MyAppName "AbbonamentiScalea"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Comune di Scalea"
#define MyAppExeName "AbbonamentiScalea.exe"
#define MyAppAssocName MyAppName + " Database"
#define MyAppAssocExt ".abbdb"

[Setup]
; Basic app information
AppId={{E5A3F8D2-9B4C-4A1E-8F2D-3C5B6A7E9D1F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppPublisher}\{#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer_output
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Windows version requirements
MinVersion=10.0.17763
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Uninstall
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files (assuming --onedir build)
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: If using --onefile build, change to:
; Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up application data (optional - remove if you want to preserve user data)
; Type: filesandordirs; Name: "{userappdata}\AbbonamentiScalea"

[Code]
// Custom installation wizard text (Italian)
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Optional: perform post-installation tasks
  end;
end;

function InitializeUninstall(): Boolean;
var
  Response: Integer;
begin
  Response := MsgBox('Vuoi conservare i dati degli abbonamenti?' + #13#10 + 
                     'Se selezioni "Sì", il database in %APPDATA%\AbbonamentiScalea verrà mantenuto.',
                     mbConfirmation, MB_YESNO);
  Result := True;
  
  if Response = IDNO then
  begin
    // User wants to delete data - uncomment UninstallDelete section above
  end;
end;
