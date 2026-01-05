; ============================================================================
; INNO SETUP SCRIPT - INSTALADOR DO AGENTE
; ============================================================================
; Gera um instalador executável (.exe) profissional
; Requer: Inno Setup Compiler (https://jrsoftware.org/isdl.php)
; ============================================================================

#define MyAppName "Print Monitor Agent"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Sistema de Monitoramento"
#define MyAppURL "http://localhost:5002"
#define MyAppExeName "agente.py"
#define MyAppId "B2C3D4E5-F6A7-8901-BCDE-F23456789012"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\PrintMonitor\Agent
DefaultGroupName=Print Monitor
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=dist
OutputBaseFilename=PrintMonitorAgent_Setup
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
Name: "autostart"; Description: "Iniciar automaticamente com o Windows"; GroupDescription: "Configurações"; Flags: checkedonce
Name: "installdeps"; Description: "Instalar dependências Python automaticamente"; GroupDescription: "Configurações"; Flags: checkedonce
Name: "testconnection"; Description: "Testar conexão com servidor antes de instalar"; GroupDescription: "Configurações"; Flags: checkedonce

[Files]
Source: "agente.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json.example"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExistsCheck(ExpandConstant('{src}\config.json.example'))
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion; DestName: "requirements.txt"; Check: not FileExistsCheck(ExpandConstant('{src}\requirements.txt'))
Source: "instalar_agente.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "instalar_agente.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\agente.py"""; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\agente.py"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\agente.py"""; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""if (Test-Path '{code:GetAppPath}\config.json') {{ Copy-Item '{code:GetAppPath}\config.json' '{code:GetAppPath}\config.json.backup' -Force }}"""; StatusMsg: "Fazendo backup de configuração..."; Flags: runhidden; Check: IsUpgrade
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""if (-not (Test-Path '{code:GetAppPath}\config.json')) {{ Copy-Item '{code:GetAppPath}\config.json.example' '{code:GetAppPath}\config.json' -Force }}"""; StatusMsg: "Criando arquivo de configuração..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""$config = Get-Content '{code:GetAppPath}\config.json' | ConvertFrom-Json; $config.server_url = '{code:GetServerURL}'; $config.check_interval = {code:GetCheckInterval}; $config.retry_interval = {code:GetRetryInterval}; $config | ConvertTo-Json -Depth 10 | Set-Content '{code:GetAppPath}\config.json'"""; StatusMsg: "Aplicando configurações..."; Flags: runhidden; AfterInstall: SaveConfig
Filename: "python.exe"; Parameters: "-m pip install --upgrade pip --quiet"; StatusMsg: "Atualizando pip..."; Flags: runhidden; Tasks: installdeps; Check: PythonInstalled
Filename: "python.exe"; Parameters: "-m pip install -r ""{code:GetAppPath}\requirements.txt"""; StatusMsg: "Instalando dependências Python..."; Flags: runhidden; Tasks: installdeps; Check: PythonInstalled
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{code:GetAppPath}\instalar_agente.ps1"" -ServerURL ""{code:GetServerURL}"" -SkipDependencies -CreateTask"; StatusMsg: "Configurando agente e criando tarefa agendada..."; Flags: runhidden; Tasks: autostart
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{code:GetAppPath}\instalar_agente.ps1"" -ServerURL ""{code:GetServerURL}"" -SkipDependencies -CreateTask:$false"; StatusMsg: "Configurando agente..."; Flags: runhidden; Check: not WizardIsTaskSelected('autostart')
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""$result = Test-NetConnection -ComputerName '{code:GetServerIP}' -Port {code:GetServerPort} -InformationLevel Quiet -WarningAction SilentlyContinue; if (-not $result) {{ Write-Host 'AVISO: Não foi possível conectar ao servidor. Verifique se está rodando.' }}"""; StatusMsg: "Testando conexão com servidor..."; Flags: runhidden; Tasks: testconnection; AfterInstall: SaveConfig; Check: WizardIsTaskSelected('testconnection')

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-Command ""Unregister-ScheduledTask -TaskName PrintMonitorAgent -Confirm:$false -ErrorAction SilentlyContinue"""; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\event_queue.db"
Type: files; Name: "{app}\agent_state.json"

[Code]
var
  ConfigPage: TInputQueryWizardPage;
  ServerIP: String;
  ServerPort: String;
  ServerURL: String;
  CheckInterval: String;
  RetryInterval: String;
  PythonPath: String;
  PythonVersion: String;
  RequirementsMet: Boolean;

function FindPythonInstallation(): Boolean;
var
  Versions: TArrayOfString;
  I: Integer;
  RegPath: String;
begin
  Result := False;
  SetArrayLength(Versions, 4);
  Versions[0] := '3.11';
  Versions[1] := '3.10';
  Versions[2] := '3.9';
  Versions[3] := '3.8';
  
  for I := 0 to GetArrayLength(Versions) - 1 do
  begin
    RegPath := 'SOFTWARE\Python\PythonCore\' + Versions[I] + '\InstallPath';
    if RegQueryStringValue(HKLM, RegPath, '', PythonPath) then
    begin
      PythonVersion := Versions[I];
      Result := True;
      Break;
    end;
  end;
end;

function CheckDiskSpace(RequiredMB: Integer): Boolean;
var
  FreeSpace: Int64;
  TotalSpace: Int64;
  Drive: String;
begin
  // Usa C: como padrão, pois {app} ainda não foi inicializado
  Drive := 'C:';
  if GetSpaceOnDisk64(Drive, FreeSpace, TotalSpace) then
    Result := (FreeSpace >= RequiredMB * 1024 * 1024)
  else
    Result := True; // Se não conseguir verificar, assume que há espaço
end;

function TestInternetConnection(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  // Tenta pingar um servidor conhecido
  if Exec('ping.exe', '-n 1 -w 1000 8.8.8.8', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := (ResultCode = 0);
  end;
end;

function CheckRequirements(): Boolean;
var
  ErrorMsg: String;
begin
  Result := True;
  ErrorMsg := '';
  RequirementsMet := True;
  
  // Verifica Python
  if not FindPythonInstallation() then
  begin
    ErrorMsg := ErrorMsg + '• Python 3.8+ não encontrado' + #13#10;
    RequirementsMet := False;
  end;
  
  // Verifica espaço em disco (100 MB)
  if not CheckDiskSpace(100) then
  begin
    ErrorMsg := ErrorMsg + '• Espaço em disco insuficiente (mínimo 100 MB)' + #13#10;
    RequirementsMet := False;
  end;
  
  if ErrorMsg <> '' then
  begin
    ErrorMsg := 'Os seguintes requisitos não foram atendidos:' + #13#10 + #13#10 + ErrorMsg;
    if MsgBox(ErrorMsg + #13#10 + 'Deseja continuar mesmo assim?', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := CheckRequirements();
end;

function PythonInstalled(): Boolean;
begin
  Result := RequirementsMet and (PythonPath <> '');
end;

procedure InitializeWizard;
begin
  // Página de configuração do servidor
  ConfigPage := CreateInputQueryPage(wpWelcome,
    'Configuração do Servidor', 'Configure a conexão com o servidor',
    'Por favor, configure os parâmetros de conexão:');
  
  // Campos de configuração
  ConfigPage.Add('IP do Servidor:', False);
  ConfigPage.Add('Porta do Servidor:', False);
  ConfigPage.Add('Intervalo de Verificação (segundos):', False);
  ConfigPage.Add('Intervalo de Retry (segundos):', False);
  
  // Valores padrão
  ConfigPage.Values[0] := '192.168.1.27';
  ConfigPage.Values[1] := '5002';
  ConfigPage.Values[2] := '5';
  ConfigPage.Values[3] := '30';
end;

function ValidateIP(IP: String): Boolean;
var
  Parts: TArrayOfString;
  I, Num, DotPos, StartPos: Integer;
  Part: String;
begin
  Result := False;
  if IP = '' then Exit;
  
  // Divide o IP em partes manualmente
  SetArrayLength(Parts, 4);
  StartPos := 1;
  I := 0;
  
  while (StartPos <= Length(IP)) and (I < 4) do
  begin
    DotPos := Pos('.', Copy(IP, StartPos, Length(IP) - StartPos + 1));
    if DotPos = 0 then
    begin
      // Última parte
      Part := Copy(IP, StartPos, Length(IP) - StartPos + 1);
      Parts[I] := Part;
      I := I + 1;
      Break;
    end
    else
    begin
      Part := Copy(IP, StartPos, DotPos - 1);
      Parts[I] := Part;
      I := I + 1;
      StartPos := StartPos + DotPos;
    end;
  end;
  
  if I <> 4 then Exit;
  
  // Valida cada parte
  for I := 0 to 3 do
  begin
    Num := StrToIntDef(Parts[I], -1);
    if Num = -1 then Exit; // Conversão falhou
    if (Num < 0) or (Num > 255) then Exit;
  end;
  
  Result := True;
end;

function ValidatePort(Port: String): Boolean;
var
  Num: Integer;
begin
  Result := False;
  if Port = '' then Exit;
  Num := StrToIntDef(Port, -1);
  if Num = -1 then Exit; // Conversão falhou
  if (Num < 1) or (Num > 65535) then Exit;
  Result := True;
end;

function ValidateInterval(Interval: String): Boolean;
var
  Num: Integer;
begin
  Result := False;
  if Interval = '' then Exit;
  Num := StrToIntDef(Interval, -1);
  if Num = -1 then Exit; // Conversão falhou
  if Num < 1 then Exit;
  Result := True;
end;

function BuildServerURL(IP, Port: String): String;
begin
  Result := 'http://' + IP + ':' + Port + '/api/print_events';
end;

function GetServerURL(Param: String): String;
begin
  Result := ServerURL;
end;

function GetCheckInterval(Param: String): String;
begin
  Result := CheckInterval;
end;

function GetRetryInterval(Param: String): String;
begin
  Result := RetryInterval;
end;

function GetServerIP(Param: String): String;
begin
  Result := ServerIP;
end;

function GetServerPort(Param: String): String;
begin
  Result := ServerPort;
end;

function IsUpgrade(): Boolean;
begin
  Result := RegKeyExists(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1');
end;

function FileExistsCheck(FileName: String): Boolean;
begin
  Result := FileExists(ExpandConstant(FileName));
end;

function TestServerConnection(IP, Port: String): Boolean;
var
  ResultCode: Integer;
  TestCmd: String;
begin
  Result := False;
  TestCmd := '-Command "try { $conn = Test-NetConnection -ComputerName ' + IP + ' -Port ' + Port + ' -InformationLevel Quiet -WarningAction SilentlyContinue; exit $conn } catch { exit 1 }"';
  
  if Exec('powershell.exe', TestCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := (ResultCode = 0);
  end;
end;

procedure SaveConfig;
begin
  ServerIP := ConfigPage.Values[0];
  ServerPort := ConfigPage.Values[1];
  CheckInterval := ConfigPage.Values[2];
  RetryInterval := ConfigPage.Values[3];
  ServerURL := BuildServerURL(ServerIP, ServerPort);
end;

function GetAppPath(Param: String): String;
begin
  // Retorna o caminho do app, ou string vazia se ainda não inicializado
  try
    Result := ExpandConstant('{app}');
  except
    Result := '';
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ErrorMsg: String;
begin
  Result := True;
  
  if CurPageID = ConfigPage.ID then
  begin
    ErrorMsg := '';
    
    // Valida IP
    if ConfigPage.Values[0] = '' then
      ErrorMsg := ErrorMsg + '• IP do servidor é obrigatório' + #13#10
    else if not ValidateIP(ConfigPage.Values[0]) then
      ErrorMsg := ErrorMsg + '• IP do servidor inválido (formato: 192.168.1.1)' + #13#10;
    
    // Valida Porta
    if ConfigPage.Values[1] = '' then
      ErrorMsg := ErrorMsg + '• Porta do servidor é obrigatória' + #13#10
    else if not ValidatePort(ConfigPage.Values[1]) then
      ErrorMsg := ErrorMsg + '• Porta inválida (deve ser entre 1 e 65535)' + #13#10;
    
    // Valida Intervalo de Verificação
    if ConfigPage.Values[2] = '' then
      ErrorMsg := ErrorMsg + '• Intervalo de verificação é obrigatório' + #13#10
    else if not ValidateInterval(ConfigPage.Values[2]) then
      ErrorMsg := ErrorMsg + '• Intervalo de verificação inválido (deve ser maior que 0)' + #13#10;
    
    // Valida Intervalo de Retry
    if ConfigPage.Values[3] = '' then
      ErrorMsg := ErrorMsg + '• Intervalo de retry é obrigatório' + #13#10
    else if not ValidateInterval(ConfigPage.Values[3]) then
      ErrorMsg := ErrorMsg + '• Intervalo de retry inválido (deve ser maior que 0)' + #13#10;
    
    if ErrorMsg <> '' then
    begin
      MsgBox('Por favor, corrija os seguintes erros:' + #13#10 + #13#10 + ErrorMsg, mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    // Salva configurações
    SaveConfig;
    
    // Testa conexão se solicitado
    if WizardIsTaskSelected('testconnection') then
    begin
      if not TestServerConnection(ServerIP, ServerPort) then
      begin
        if MsgBox('Não foi possível conectar ao servidor:' + #13#10 +
                  'IP: ' + ServerIP + #13#10 +
                  'Porta: ' + ServerPort + #13#10 + #13#10 +
                  'Possíveis causas:' + #13#10 +
                  '• Servidor não está rodando' + #13#10 +
                  '• Firewall bloqueando conexão' + #13#10 +
                  '• IP ou porta incorretos' + #13#10 + #13#10 +
                  'Deseja continuar mesmo assim?', mbConfirmation, MB_YESNO) = IDNO then
        begin
          Result := False;
          Exit;
        end;
      end else
      begin
        MsgBox('✅ Conexão com servidor bem-sucedida!', mbInformation, MB_OK);
      end;
    end;
    
    // Mostra resumo
    if MsgBox('Resumo da configuração:' + #13#10 + #13#10 +
              'IP do Servidor: ' + ServerIP + #13#10 +
              'Porta: ' + ServerPort + #13#10 +
              'URL Completa: ' + ServerURL + #13#10 +
              'Intervalo de Verificação: ' + CheckInterval + ' segundos' + #13#10 +
              'Intervalo de Retry: ' + RetryInterval + ' segundos' + #13#10 + #13#10 +
              'Deseja continuar com a instalação?', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;

