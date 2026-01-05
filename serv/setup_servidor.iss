; ============================================================================
; INNO SETUP SCRIPT - INSTALADOR DO SERVIDOR
; ============================================================================
; Gera um instalador executável (.exe) profissional
; Requer: Inno Setup Compiler (https://jrsoftware.org/isdl.php)
; ============================================================================

#define MyAppName "Print Monitor Server"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Sistema de Monitoramento"
#define MyAppURL "http://localhost:5002"
#define MyAppExeName "servidor.py"
#define MyAppId "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\PrintMonitor\Server
DefaultGroupName=Print Monitor
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=dist
OutputBaseFilename=PrintMonitorServer_Setup
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1
Name: "firewall"; Description: "Configurar Firewall do Windows"; GroupDescription: "Configurações"; Flags: checkedonce
Name: "service"; Description: "Instalar como Serviço do Windows"; GroupDescription: "Configurações"; Flags: unchecked

[Files]
Source: "servidor.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "modules\*"; DestDir: "{app}\modules"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion; DestName: "requirements.txt"
Source: "instalar_servidor.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "instalar_servidor.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\servidor.py"""; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\servidor.py"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\servidor.py"""; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\instalar_servidor.ps1"" -SkipDependencies -ConfigureFirewall"; StatusMsg: "Configurando servidor..."; Flags: runhidden; Tasks: firewall
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\instalar_servidor.ps1"" -SkipDependencies -InstallService"; StatusMsg: "Instalando serviço..."; Flags: runhidden; Tasks: service
Filename: "python.exe"; Parameters: """{app}\servidor.py"""; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\backups"
Type: files; Name: "{app}\print_events.db"

[Code]
function InitializeSetup(): Boolean;
var
  PythonPath: String;
  PythonFound: Boolean;
begin
  Result := True;
  PythonFound := False;
  
  // Verifica se Python está instalado
  if RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.11\InstallPath', '', PythonPath) then
    PythonFound := True
  else if RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.10\InstallPath', '', PythonPath) then
    PythonFound := True
  else if RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.9\InstallPath', '', PythonPath) then
    PythonFound := True
  else if RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.8\InstallPath', '', PythonPath) then
    PythonFound := True;
  
  if not PythonFound then
  begin
    if MsgBox('Python não foi detectado no sistema.' + #13#10 + #13#10 +
              'Deseja continuar mesmo assim?', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;

function FileExistsCheck(FileName: String): Boolean;
begin
  Result := FileExists(ExpandConstant(FileName));
end;

