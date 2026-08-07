#ifndef MyAppVersion
  #define MyAppVersion "0.6.0"
#endif

#define MyAppName "Interly"
#define MyAppPublisher "Interlink Global Technologies"
#define MyAppExeName "interly.exe"

[Setup]
AppId={{6CB4E41F-F5A4-4F9D-B05F-C0565EBD99E7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/interlinkglobal/Interly
AppSupportURL=https://github.com/interlinkglobal/Interly/issues
DefaultDirName={localappdata}\Programs\Interly
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=InterlySetup-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\interly.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\interlink.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Interly"; Filename: "{app}\{#MyAppExeName}"

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Interly"; \
    Flags: nowait postinstall skipifsilent

[Code]
function NeedsAddPath(Param: string): Boolean;
var
  CurrentPath: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', CurrentPath) then
    CurrentPath := '';
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(CurrentPath) + ';') = 0;
end;

procedure RemoveAppPath;
var
  CurrentPath: string;
  AppPath: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', CurrentPath) then
    exit;
  AppPath := ExpandConstant('{app}');
  StringChangeEx(CurrentPath, ';' + AppPath, '', True);
  StringChangeEx(CurrentPath, AppPath + ';', '', True);
  if CompareText(CurrentPath, AppPath) = 0 then
    CurrentPath := '';
  RegWriteExpandStringValue(HKCU, 'Environment', 'Path', CurrentPath);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RemoveAppPath;
end;
