; UnifAI Guard — Enterprise Windows Installer (Inno Setup 6)
; Build: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\UnifAI_Guard.iss

#define MyAppName "UnifAI Guard"
#define MyAppVersion "1.5.6"
#define MyAppPublisher "UnifAI"
#define MyAppURL "https://unifaiv2.dev-yp.com"
#define MyAppExeName "UnifAI_Guard.exe"

[Setup]
AppId={{8F3C2A91-6B4E-4D2F-9A71-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\UnifAI\Guard
DefaultGroupName=UnifAI Guard
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=UnifAI_Guard_Setup
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
CloseApplications=force
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "autostart"; Description: "Start UnifAI Guard automatically at Windows login (recommended)"; Flags: checkedonce

[Files]
Source: "staging\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\UnifAI Guard"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall UnifAI Guard"; Filename: "{uninstallexe}"
Name: "{userdesktop}\UnifAI Guard"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Registry]
; Permanent autostart for current user (HKCU) — required so PAC/proxy apply to the logged-in user
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "UnifAI_Guard"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start UnifAI Guard now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM {#MyAppExeName} >nul 2>&1"; Flags: runhidden; RunOnceId: "StopGuard"

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\UnifAI\Guard"
Type: files; Name: "{app}\unifai_guard.log"
Type: files; Name: "{app}\proxy.pac"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
  ExePath: String;
begin
  Result := True;
  ExePath := ExpandConstant('{app}\{#MyAppExeName}');
  if FileExists(ExePath) then
  begin
    if Exec(ExePath, '--uninstall-prompt', ExpandConstant('{app}'), SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode <> 0 then
      begin
        if ResultCode <> 3 then
          MsgBox('Uninstall rejected. Check the company uninstall key in Browser AI → Setup.', mbError, MB_OK);
        Result := False;
      end;
    end
    else
    begin
      MsgBox('Could not run Guard uninstall check. Aborting.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
