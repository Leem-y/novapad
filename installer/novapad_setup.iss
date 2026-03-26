; novapad_setup.iss -- Inno Setup 6 installer for NovaPad
; Build: "C:\Users\4eos\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\novapad_setup.iss

[Setup]
AppName=NovaPad
AppVersion=3.0.0
AppVerName=NovaPad 3.0.0
AppPublisher=NovaPad
DefaultDirName={autopf}\NovaPad
DefaultGroupName=NovaPad
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=NovaPad_Setup_3.0.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
MinVersion=10.0
UninstallDisplayName=NovaPad 3.0.0
UninstallDisplayIcon={app}\NovaPad.exe
SetupIconFile=..\assets\novapad.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "assoc_txt";   Description: "Associate .txt  files";  GroupDescription: "File associations:"; Flags: unchecked
Name: "assoc_md";    Description: "Associate .md   files";  GroupDescription: "File associations:"; Flags: unchecked
Name: "assoc_json";  Description: "Associate .json files";  GroupDescription: "File associations:"; Flags: unchecked
Name: "assoc_py";    Description: "Associate .py   files";  GroupDescription: "File associations:"; Flags: unchecked
Name: "assoc_js";    Description: "Associate .js   files";  GroupDescription: "File associations:"; Flags: unchecked
Name: "assoc_html";  Description: "Associate .html files";  GroupDescription: "File associations:"; Flags: unchecked
Name: "assoc_css";   Description: "Associate .css  files";  GroupDescription: "File associations:"; Flags: unchecked
Name: "assoc_log";   Description: "Associate .log  files";  GroupDescription: "File associations:"; Flags: unchecked
Name: "ctx_files";   Description: """Open with NovaPad"" in file context menu";   GroupDescription: "Windows Explorer:"
Name: "ctx_folders"; Description: """Open folder with NovaPad"" in folder context menu"; GroupDescription: "Windows Explorer:"; Flags: unchecked

[Files]
Source: "{#SourcePath}\..\dist\NovaPad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NovaPad";           Filename: "{app}\NovaPad.exe"
Name: "{group}\Uninstall NovaPad"; Filename: "{uninstallexe}"
Name: "{autodesktop}\NovaPad";     Filename: "{app}\NovaPad.exe"; Tasks: desktopicon

[Registry]
; App Paths (lets Windows find NovaPad.exe by name)
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\NovaPad.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\NovaPad.exe"; Flags: uninsdeletekey

; ProgID definition
Root: HKA; Subkey: "Software\Classes\NovaPad.TextFile";                           ValueType: string; ValueName: "";             ValueData: "Text File";               Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\NovaPad.TextFile\DefaultIcon";               ValueType: string; ValueName: "";             ValueData: "{app}\NovaPad.exe,0";      Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\NovaPad.TextFile\shell\open\command";        ValueType: string; ValueName: "";             ValueData: """{app}\NovaPad.exe"" ""%1"""; Flags: uninsdeletekey

; File associations (only when user ticked the task)
Root: HKA; Subkey: "Software\Classes\.txt\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.txt";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_txt

Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids";   ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.md";                   ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_md

Root: HKA; Subkey: "Software\Classes\.json\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.json";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_json

Root: HKA; Subkey: "Software\Classes\.py\OpenWithProgids";   ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.py";                   ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_py

Root: HKA; Subkey: "Software\Classes\.js\OpenWithProgids";   ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.js";                   ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_js

Root: HKA; Subkey: "Software\Classes\.html\OpenWithProgids"; ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.html";                 ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_html

Root: HKA; Subkey: "Software\Classes\.css\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.css";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_css

Root: HKA; Subkey: "Software\Classes\.log\OpenWithProgids";  ValueType: string; ValueName: "NovaPad.TextFile"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.log";                  ValueType: string; ValueName: "";                ValueData: "NovaPad.TextFile"; Flags: uninsdeletevalue; Tasks: assoc_log

; "Open with NovaPad" on files
Root: HKA; Subkey: "Software\Classes\*\shell\NovaPad";          ValueType: string; ValueName: "";     ValueData: "Open with NovaPad";        Flags: uninsdeletekey; Tasks: ctx_files
Root: HKA; Subkey: "Software\Classes\*\shell\NovaPad";          ValueType: string; ValueName: "Icon"; ValueData: "{app}\NovaPad.exe,0";      Flags: uninsdeletekey; Tasks: ctx_files
Root: HKA; Subkey: "Software\Classes\*\shell\NovaPad\command";  ValueType: string; ValueName: "";     ValueData: """{app}\NovaPad.exe"" ""%1"""; Flags: uninsdeletekey; Tasks: ctx_files

; "Open folder with NovaPad"
Root: HKA; Subkey: "Software\Classes\Directory\shell\NovaPad";          ValueType: string; ValueName: "";     ValueData: "Open Folder with NovaPad"; Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\shell\NovaPad";          ValueType: string; ValueName: "Icon"; ValueData: "{app}\NovaPad.exe,0";      Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\shell\NovaPad\command";  ValueType: string; ValueName: "";     ValueData: """{app}\NovaPad.exe"" ""%V"""; Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\NovaPad";         ValueType: string; ValueName: "";     ValueData: "Open Folder with NovaPad"; Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\NovaPad";         ValueType: string; ValueName: "Icon"; ValueData: "{app}\NovaPad.exe,0";      Flags: uninsdeletekey; Tasks: ctx_folders
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\NovaPad\command"; ValueType: string; ValueName: "";     ValueData: """{app}\NovaPad.exe"" ""%V"""; Flags: uninsdeletekey; Tasks: ctx_folders

[Run]
Filename: "{app}\NovaPad.exe"; Description: "Launch NovaPad now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\NovaPad"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
