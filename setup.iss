[Setup]
AppName=Генератор КП
AppVersion=1.0
DefaultDirName={userpf}\GeneratorKP
DefaultGroupName=Генератор КП
OutputDir=installer
OutputBaseFilename=GeneratorKP_Setup
Compression=lzma
SolidCompression=yes
UninstallDisplayName=Генератор КП
PrivilegesRequired=lowest

[Files]
Source: "app.py"; DestDir: "{app}"
Source: "run.bat"; DestDir: "{app}"
Source: "run_silent.vbs"; DestDir: "{app}"
Source: "requirements.txt"; DestDir: "{app}"
Source: "data\*"; DestDir: "{app}\data"

[Icons]
Name: "{commondesktop}\Генератор КП"; Filename: "wscript.exe"; Parameters: """{app}\run_silent.vbs"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 12

[Run]
Filename: "{cmd}"; Parameters: "/c pip install -r ""{app}\requirements.txt"""; Description: "Установка библиотек"; Flags: runhidden waituntilterminated
Filename: "wscript.exe"; Parameters: """{app}\run_silent.vbs"""; Description: "Запустить Генератор КП"; Flags: nowait postinstall skipifsilent