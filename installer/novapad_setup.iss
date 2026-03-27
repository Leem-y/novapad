; novapad_setup.iss  –  Inno Setup 6 installer for NovaPad
; Build: "C:\Users\liams\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\novapad_setup.iss
;
; ── Change version here only ──────────────────────────────────────────────────
#define AppVersion "3.1.3"
; ─────────────────────────────────────────────────────────────────────────────

[Setup]
AppName=NovaPad
AppVersion={#AppVersion}
AppVerName=NovaPad {#AppVersion}
AppPublisher=NovaPad
AppPublisherURL=https://github.com/Leem-y/novapad
AppSupportURL=https://github.com/Leem-y/novapad/issues
AppUpdatesURL=https://github.com/Leem-y/novapad/releases
AppCopyright=Copyright (C) 2024-2026 NovaPad
AppMutex=NovaPadSingleInstanceMutex

DefaultDirName={autopf}\NovaPad
DefaultGroupName=NovaPad
AllowNoIcons=yes
DisableProgramGroupPage=yes

OutputDir=Output
OutputBaseFilename=NovaPad_Setup_{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible

; Close any running NovaPad before upgrading
CloseApplications=yes
CloseApplicationsFilter=NovaPad.exe
RestartApplications=no

UninstallDisplayName=NovaPad {#AppVersion}
UninstallDisplayIcon={app}\NovaPad.exe
SetupIconFile=..\assets\novapad.ico

; Windows file-properties version info
VersionInfoVersion={#AppVersion}
VersionInfoCompany=NovaPad
VersionInfoDescription=NovaPad Installer
VersionInfoProductName=NovaPad
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── Tasks ─────────────────────────────────────────────────────────────────────
[Tasks]

; Shortcuts
Name: "desktopicon";  Description: "Create a &desktop shortcut";     GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "startupicon";  Description: "Launch NovaPad at &Windows startup"; GroupDescription: "Shortcuts:"; Flags: unchecked

; PATH
Name: "addtopath";    Description: "Add NovaPad to &PATH  (run ""novapad"" from any terminal)"; GroupDescription: "System:"; Flags: unchecked

; Context menu
Name: "ctx_files";    Description: """&Open with NovaPad"" on files";         GroupDescription: "Explorer context menu:"
Name: "ctx_folders";  Description: """Open &folder with NovaPad"" on folders"; GroupDescription: "Explorer context menu:"; Flags: unchecked

; ── File associations (all unchecked — user opts in) ─────────────────────────

; Text & documents
Name: "assoc_txt";   Description: ".txt  — plain text";            GroupDescription: "Associate file types  (Text & documents):"; Flags: unchecked
Name: "assoc_md";    Description: ".md   — Markdown";              GroupDescription: "Associate file types  (Text & documents):"; Flags: unchecked
Name: "assoc_csv";   Description: ".csv  — comma-separated values";GroupDescription: "Associate file types  (Text & documents):"; Flags: unchecked
Name: "assoc_log";   Description: ".log  — log files";             GroupDescription: "Associate file types  (Text & documents):"; Flags: unchecked

; Config & data
Name: "assoc_json";  Description: ".json — JSON";                  GroupDescription: "Associate file types  (Config & data):"; Flags: unchecked
Name: "assoc_yaml";  Description: ".yaml / .yml — YAML";           GroupDescription: "Associate file types  (Config & data):"; Flags: unchecked
Name: "assoc_toml";  Description: ".toml — TOML";                  GroupDescription: "Associate file types  (Config & data):"; Flags: unchecked
Name: "assoc_ini";   Description: ".ini  — INI config";            GroupDescription: "Associate file types  (Config & data):"; Flags: unchecked
Name: "assoc_xml";   Description: ".xml  — XML";                   GroupDescription: "Associate file types  (Config & data):"; Flags: unchecked
Name: "assoc_sql";   Description: ".sql  — SQL scripts";           GroupDescription: "Associate file types  (Config & data):"; Flags: unchecked

; Web
Name: "assoc_html";  Description: ".html / .htm — HTML";           GroupDescription: "Associate file types  (Web):"; Flags: unchecked
Name: "assoc_css";   Description: ".css  — stylesheets";           GroupDescription: "Associate file types  (Web):"; Flags: unchecked
Name: "assoc_js";    Description: ".js   — JavaScript";            GroupDescription: "Associate file types  (Web):"; Flags: unchecked
Name: "assoc_ts";    Description: ".ts   — TypeScript";            GroupDescription: "Associate file types  (Web):"; Flags: unchecked
Name: "assoc_jsx";   Description: ".jsx / .tsx — React";           GroupDescription: "Associate file types  (Web):"; Flags: unchecked

; Code
Name: "assoc_py";    Description: ".py   — Python";                GroupDescription: "Associate file types  (Code):"; Flags: unchecked
Name: "assoc_sh";    Description: ".sh / .bash — shell scripts";   GroupDescription: "Associate file types  (Code):"; Flags: unchecked
Name: "assoc_bat";   Description: ".bat / .cmd — batch files";     GroupDescription: "Associate file types  (Code):"; Flags: unchecked
Name: "assoc_ps1";   Description: ".ps1  — PowerShell";            GroupDescription: "Associate file types  (Code):"; Flags: unchecked
Name: "assoc_c";     Description: ".c / .h — C/C++ source";        GroupDescription: "Associate file types  (Code):"; Flags: unchecked
Name: "assoc_go";    Description: ".go   — Go";                    GroupDescription: "Associate file types  (Code):"; Flags: unchecked
Name: "assoc_rs";    Description: ".rs   — Rust";                  GroupDescription: "Associate file types  (Code):"; Flags: unchecked
Name: "assoc_php";   Description: ".php  — PHP";                   GroupDescription: "Associate file types  (Code):"; Flags: unchecked
Name: "assoc_rb";    Description: ".rb   — Ruby";                  GroupDescription: "Associate file types  (Code):"; Flags: unchecked

; ── Files ─────────────────────────────────────────────────────────────────────
[Files]
Source: "{#SourcePath}\..\dist\NovaPad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Shortcuts ─────────────────────────────────────────────────────────────────
[Icons]
Name: "{autoprograms}\NovaPad"; Filename: "{app}\NovaPad.exe"
Name: "{autodesktop}\NovaPad";  Filename: "{app}\NovaPad.exe"; Tasks: desktopicon
Name: "{userstartup}\NovaPad";  Filename: "{app}\NovaPad.exe"; Tasks: startupicon

; ── Registry ──────────────────────────────────────────────────────────────────
[Registry]

; App Paths — lets "Start → Run → NovaPad" work
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\NovaPad.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\NovaPad.exe"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\NovaPad.exe"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Flags: uninsdeletekey

; ProgID
Root: HKA; Subkey: "Software\Classes\NovaPad.TextFile";                           ValueType: string; ValueName: "";             ValueData: "Text File";                   Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\NovaPad.TextFile\DefaultIcon";               ValueType: string; ValueName: "";             ValueData: "{app}\NovaPad.exe,0";          Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\NovaPad.TextFile\shell\open\command";        ValueType: string; ValueName: "";             ValueData: """{app}\NovaPad.exe"" ""%1"""; Flags: uninsdeletekey

; ── File associations ─────────────────────────────────────────────────────────

; .txt
Root: HKA; Subkey: "Software\Classes\.txt\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.txt";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_txt
; .md
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.md";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_md
; .csv
Root: HKA; Subkey: "Software\Classes\.csv\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.csv";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_csv
; .log
Root: HKA; Subkey: "Software\Classes\.log\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.log";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_log
; .json
Root: HKA; Subkey: "Software\Classes\.json\OpenWithProgids";ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.json";                ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_json
; .yaml
Root: HKA; Subkey: "Software\Classes\.yaml\OpenWithProgids";ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.yaml";                ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_yaml
Root: HKA; Subkey: "Software\Classes\.yml\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.yml";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_yaml
; .toml
Root: HKA; Subkey: "Software\Classes\.toml\OpenWithProgids";ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.toml";                ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_toml
; .ini
Root: HKA; Subkey: "Software\Classes\.ini\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.ini";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_ini
; .xml
Root: HKA; Subkey: "Software\Classes\.xml\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.xml";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_xml
; .sql
Root: HKA; Subkey: "Software\Classes\.sql\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.sql";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_sql
; .html / .htm
Root: HKA; Subkey: "Software\Classes\.html\OpenWithProgids";ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.html";                ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_html
Root: HKA; Subkey: "Software\Classes\.htm\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.htm";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_html
; .css
Root: HKA; Subkey: "Software\Classes\.css\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.css";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_css
; .js
Root: HKA; Subkey: "Software\Classes\.js\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.js";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_js
; .ts
Root: HKA; Subkey: "Software\Classes\.ts\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.ts";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_ts
; .jsx / .tsx
Root: HKA; Subkey: "Software\Classes\.jsx\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.jsx";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_jsx
Root: HKA; Subkey: "Software\Classes\.tsx\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.tsx";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_jsx
; .py
Root: HKA; Subkey: "Software\Classes\.py\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.py";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_py
; .sh / .bash
Root: HKA; Subkey: "Software\Classes\.sh\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.sh";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_sh
Root: HKA; Subkey: "Software\Classes\.bash\OpenWithProgids";ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.bash";                ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_sh
; .bat / .cmd
Root: HKA; Subkey: "Software\Classes\.bat\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.bat";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_bat
Root: HKA; Subkey: "Software\Classes\.cmd\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.cmd";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_bat
; .ps1
Root: HKA; Subkey: "Software\Classes\.ps1\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.ps1";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_ps1
; .c / .h / .cpp
Root: HKA; Subkey: "Software\Classes\.c\OpenWithProgids";   ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.c";                   ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_c
Root: HKA; Subkey: "Software\Classes\.h\OpenWithProgids";   ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.h";                   ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_c
Root: HKA; Subkey: "Software\Classes\.cpp\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.cpp";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_c
; .go
Root: HKA; Subkey: "Software\Classes\.go\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.go";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_go
; .rs
Root: HKA; Subkey: "Software\Classes\.rs\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.rs";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_rs
; .php
Root: HKA; Subkey: "Software\Classes\.php\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.php";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_php
; .rb
Root: HKA; Subkey: "Software\Classes\.rb\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.rb";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_rb

; ── Explorer context menus ────────────────────────────────────────────────────

; "Open with NovaPad" on any file
Root: HKA; Subkey: "Software\Classes\*\shell\NovaPad";         ValueType: string; ValueName: "";     ValueData: "Open with NovaPad";           Flags: uninsdeletekey; Tasks: ctx_files
Root: HKA; Subkey: "Software\Classes\*\shell\NovaPad";         ValueType: string; ValueName: "Icon"; ValueData: "{app}\NovaPad.exe,0";          Flags: uninsdeletekey; Tasks: ctx_files
Root: HKA; Subkey: "Software\Classes\*\shell\NovaPad\command"; ValueType: string; ValueName: "";     ValueData: """{app}\NovaPad.exe"" ""%1"""; Flags: uninsdeletekey; Tasks: ctx_files

; "Open folder with NovaPad" on directories
Root: HKA; Subkey: "Software\Classes\Directory\shell\NovaPad";                    ValueType: string; ValueName: "";     ValueData: "Open Folder with NovaPad";    Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\shell\NovaPad";                    ValueType: string; ValueName: "Icon"; ValueData: "{app}\NovaPad.exe,0";          Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\shell\NovaPad\command";            ValueType: string; ValueName: "";     ValueData: """{app}\NovaPad.exe"" ""%V"""; Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\NovaPad";         ValueType: string; ValueName: "";     ValueData: "Open Folder with NovaPad";    Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\NovaPad";         ValueType: string; ValueName: "Icon"; ValueData: "{app}\NovaPad.exe,0";          Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\NovaPad\command"; ValueType: string; ValueName: "";     ValueData: """{app}\NovaPad.exe"" ""%V"""; Flags: uninsdeletekey; Tasks: ctx_folders

; ── Run ───────────────────────────────────────────────────────────────────────
[Run]
Filename: "{app}\NovaPad.exe"; Description: "Launch NovaPad now"; Flags: nowait postinstall skipifsilent runasoriginaluser

; ── Cleanup on uninstall ──────────────────────────────────────────────────────
[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\NovaPad"

; ── Code ──────────────────────────────────────────────────────────────────────
[Code]

{ ── PATH helper ─────────────────────────────────────────────────────────────── }
function NeedsAddPath(AppDir: string): Boolean;
var
  EnvPath: string;
begin
  if not RegQueryStringValue(HKA, 'Environment', 'Path', EnvPath) then
    EnvPath := '';
  Result := Pos(';' + Uppercase(AppDir) + ';',
                ';' + Uppercase(EnvPath) + ';') = 0;
end;

procedure AddToPath(AppDir: string);
var
  EnvPath: string;
begin
  if not RegQueryStringValue(HKA, 'Environment', 'Path', EnvPath) then
    EnvPath := '';
  if Pos(';' + Uppercase(AppDir) + ';',
         ';' + Uppercase(EnvPath) + ';') = 0 then
  begin
    if (EnvPath <> '') and (EnvPath[Length(EnvPath)] <> ';') then
      EnvPath := EnvPath + ';';
    RegWriteStringValue(HKA, 'Environment', 'Path', EnvPath + AppDir);
  end;
end;

procedure RemoveFromPath(AppDir: string);
var
  EnvPath, NewPath, Entry: string;
  Parts: TStringList;
  i: Integer;
begin
  if not RegQueryStringValue(HKA, 'Environment', 'Path', EnvPath) then Exit;
  Parts := TStringList.Create;
  Parts.Delimiter     := ';';
  Parts.DelimitedText := EnvPath;
  NewPath := '';
  for i := 0 to Parts.Count - 1 do
  begin
    Entry := Trim(Parts[i]);
    if CompareText(Entry, AppDir) <> 0 then
    begin
      if NewPath <> '' then NewPath := NewPath + ';';
      NewPath := NewPath + Entry;
    end;
  end;
  Parts.Free;
  RegWriteStringValue(HKA, 'Environment', 'Path', NewPath);
end;

{ Apply PATH on install }
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('addtopath') then
      AddToPath(ExpandConstant('{app}'));
    { Notify Windows that the environment changed }
    if WizardIsTaskSelected('addtopath') then
      RegWriteStringValue(HKCU, 'Environment', '_NovaPadPathAdded', '1');
  end;
end;

{ Remove PATH on uninstall }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RemoveFromPath(ExpandConstant('{app}'));
end;

{ Broadcast WM_SETTINGCHANGE so terminals pick up the new PATH immediately }
procedure DeinitializeSetup();
var
  Env: string;
begin
  Env := 'Environment';
  SendBroadcastMessage($001A, 0, CastStringToInteger(Env));
end;
