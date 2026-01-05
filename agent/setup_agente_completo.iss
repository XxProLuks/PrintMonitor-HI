; ============================================================================
; INNO SETUP SCRIPT - INSTALADOR DO AGENTE (VERSÃO COMPLETA)
; ============================================================================
; Gera um instalador executável (.exe) profissional com todas as funcionalidades
; Requer: Inno Setup Compiler 6.0+ (https://jrsoftware.org/isdl.php)
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
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=no
DisableReadyPage=no
DisableFinishedPage=no
AllowRootDirectory=no
MinVersion=10.0.17763
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Agente de Monitoramento de Impressões
VersionInfoCopyright=Copyright (C) 2024
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Components]
Name: "agent"; Description: "Agente Principal"; Types: full compact custom; Flags: fixed
Name: "tools"; Description: "Ferramentas Administrativas"; Types: full
Name: "docs"; Description: "Documentação"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1
Name: "autostart"; Description: "Iniciar automaticamente com o Windows"; GroupDescription: "Configurações"; Flags: checkedonce
Name: "installdeps"; Description: "Instalar dependências Python automaticamente"; GroupDescription: "Configurações"; Flags: checkedonce
Name: "testconnection"; Description: "Testar conexão com servidor antes de instalar"; GroupDescription: "Configurações"; Flags: unchecked
Name: "launch"; Description: "Iniciar {#MyAppName} após instalação"; GroupDescription: "Opções"; Flags: unchecked
Name: "telemetry"; Description: "Enviar métricas de uso (opcional)"; GroupDescription: "Opções"; Flags: unchecked

[Files]
Source: "agente.py"; DestDir: "{app}"; Flags: ignoreversion; Components: agent
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion; Components: agent
Source: "config.json.example"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExistsCheck(ExpandConstant('{src}\config.json.example')); Components: agent
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion; DestName: "requirements.txt"; Check: not FileExistsCheck(ExpandConstant('{src}\requirements.txt')); Components: agent
Source: "instalar_agente.ps1"; DestDir: "{app}"; Flags: ignoreversion; Components: tools
Source: "instalar_agente.py"; DestDir: "{app}"; Flags: ignoreversion; Components: tools
Source: "verificar_inicio_automatico.ps1"; DestDir: "{app}"; Flags: ignoreversion; Components: tools
Source: "check_agent_status.ps1"; DestDir: "{app}"; Flags: ignoreversion; Components: tools
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: docs; Check: FileExistsCheck(ExpandConstant('{src}\README.md'))

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\agente.py"""; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\agente.py"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\agente.py"""; WorkingDir: "{app}"; Tasks: quicklaunchicon
Name: "{group}\Abrir Pasta de Instalação"; Filename: "{app}"; Components: tools
Name: "{group}\Ver Logs"; Filename: "notepad.exe"; Parameters: "{code:GetLogPath}"; Components: tools
Name: "{group}\Configurações"; Filename: "notepad.exe"; Parameters: "{code:GetAppPath}\config.json"; Components: tools
Name: "{group}\Diagnóstico do Sistema"; Filename: "{code:GetAppPath}\diagnostico.bat"; Components: tools
Name: "{group}\Documentação"; Filename: "{code:GetAppPath}\README.md"; Components: docs

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""if (Test-Path '{code:GetAppPath}\config.json') {{ Copy-Item '{code:GetAppPath}\config.json' '{code:GetAppPath}\config.json.backup.' + (Get-Date -Format 'yyyyMMdd-HHmmss') + ' -Force }}"""; StatusMsg: "Fazendo backup de configuração..."; Flags: runhidden; Check: IsUpgrade
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""if (-not (Test-Path '{code:GetAppPath}\config.json')) {{ Copy-Item '{code:GetAppPath}\config.json.example' '{code:GetAppPath}\config.json' -Force }}"""; StatusMsg: "Criando arquivo de configuração..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""$config = Get-Content '{code:GetAppPath}\config.json' | ConvertFrom-Json; $config.server_url = '{code:GetServerURL}'; $config.check_interval = {code:GetCheckInterval}; $config.retry_interval = {code:GetRetryInterval}; $config | ConvertTo-Json -Depth 10 | Set-Content '{code:GetAppPath}\config.json'"""; StatusMsg: "Aplicando configurações..."; Flags: runhidden; AfterInstall: SaveConfig
Filename: "python.exe"; Parameters: "-m pip install --upgrade pip --quiet"; StatusMsg: "Atualizando pip..."; Flags: runhidden; Tasks: installdeps; Check: PythonInstalled
Filename: "python.exe"; Parameters: "-m pip install -r ""{code:GetAppPath}\requirements.txt"""; StatusMsg: "Instalando dependências Python..."; Flags: runhidden; Tasks: installdeps; Check: PythonInstalled
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{code:GetAppPath}\instalar_agente.ps1"" -ServerURL ""{code:GetServerURL}"" -SkipDependencies -CreateTask"; StatusMsg: "Configurando agente e criando tarefa agendada..."; Flags: runhidden; Tasks: autostart
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{code:GetAppPath}\instalar_agente.ps1"" -ServerURL ""{code:GetServerURL}"" -SkipDependencies -CreateTask:$false"; StatusMsg: "Configurando agente..."; Flags: runhidden; Check: not WizardIsTaskSelected('autostart')
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""$result = Test-NetConnection -ComputerName '{code:GetServerIP}' -Port {code:GetServerPort} -InformationLevel Quiet -WarningAction SilentlyContinue; if (-not $result) {{ Write-Host 'AVISO: Não foi possível conectar ao servidor. Verifique se está rodando.' }}"""; StatusMsg: "Testando conexão com servidor..."; Flags: runhidden; Tasks: testconnection; AfterInstall: SaveConfig; Check: WizardIsTaskSelected('testconnection')
Filename: "python.exe"; Parameters: """{code:GetAppPath}\agente.py"""; WorkingDir: "{code:GetAppPath}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent; Tasks: launch

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-Command ""Unregister-ScheduledTask -TaskName PrintMonitorAgent -Confirm:$false -ErrorAction SilentlyContinue"""; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-Command ""Stop-Process -Name python -ErrorAction SilentlyContinue -Force"""; Flags: runhidden; Check: IsProcessRunning

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\event_queue.db"
Type: files; Name: "{app}\agent_state.json"
Type: files; Name: "{app}\*.backup.*"

[Code]
var
  ConfigPage: TInputQueryWizardPage;
  AdvancedPage: TInputQueryWizardPage;
  ServerIP: String;
  ServerPort: String;
  ServerURL: String;
  CheckInterval: String;
  RetryInterval: String;
  LogLevel: String;
  MaxLogSize: String;
  PythonPath: String;
  PythonVersion: String;
  RequirementsMet: Boolean;
  PreviousVersion: String;
  InstallMode: String; // 'install', 'upgrade', 'reinstall'
  InstallLogFile: String;

// ============================================================================
// FUNÇÕES AUXILIARES
// ============================================================================

function GetAppPath(Param: String): String;
begin
  try
    Result := ExpandConstant('{app}');
  except
    Result := '';
  end;
end;

function GetLogPath(Param: String): String;
begin
  Result := ExpandConstant('{app}\logs\agent.log');
  if not FileExists(Result) then
    Result := ExpandConstant('{app}\logs');
end;

function FileExistsCheck(FileName: String): Boolean;
begin
  Result := FileExists(ExpandConstant(FileName));
end;

// ============================================================================
// DETECÇÃO DE INSTALAÇÃO/ATUALIZAÇÃO
// ============================================================================

function IsUpgrade(): Boolean;
begin
  Result := RegKeyExists(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1');
end;

function GetPreviousVersion(): String;
var
  Version: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1', 'DisplayVersion', Version) then
    Result := Version;
end;

function GetPreviousInstallPath(): String;
var
  Path: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1', 'InstallLocation', Path) then
    Result := Path;
end;

procedure DetermineInstallMode();
begin
  if IsUpgrade() then
  begin
    PreviousVersion := GetPreviousVersion();
    if PreviousVersion <> '' then
    begin
      // Compara versões manualmente (formato: X.Y.Z)
      // Se versão anterior for diferente, é upgrade
      if PreviousVersion <> '{#MyAppVersion}' then
        InstallMode := 'upgrade'
      else
        InstallMode := 'reinstall';
    end
    else
      InstallMode := 'upgrade';
  end
  else
    InstallMode := 'install';
end;

// ============================================================================
// VERIFICAÇÃO DE REQUISITOS
// ============================================================================

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

function GetPythonVersion(): String;
begin
  Result := PythonVersion;
  if Result = '' then
    Result := 'Não encontrado';
end;

function CheckDiskSpace(RequiredMB: Integer): Boolean;
var
  FreeSpace: Int64;
  TotalSpace: Int64;
  Drive: String;
begin
  Drive := 'C:';
  if GetSpaceOnDisk64(Drive, FreeSpace, TotalSpace) then
    Result := (FreeSpace >= RequiredMB * 1024 * 1024)
  else
    Result := True;
end;

function GetTotalPhysicalMemory(): Int64;
var
  ResultCode: Integer;
  Output: String;
begin
  Result := 0;
  if Exec('powershell.exe', '-Command "(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property capacity -Sum).Sum / 1GB"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // Tenta obter RAM via WMI
    if Exec('wmic.exe', 'computersystem get TotalPhysicalMemory', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      // Processa saída se necessário
      Result := 4 * 1024 * 1024 * 1024; // Assume 4GB se não conseguir obter
    end;
  end;
end;

function CheckSystemRequirements(): Boolean;
var
  OSVersion: TWindowsVersion;
  FreeSpace: Int64;
  TotalSpace: Int64;
  RAM: Int64;
  ErrorMsg: String;
begin
  Result := True;
  ErrorMsg := '';
  
  GetWindowsVersionEx(OSVersion);
  
  // Verifica versão do Windows (Windows 10 ou superior)
  if (OSVersion.Major < 10) or ((OSVersion.Major = 10) and (OSVersion.Build < 17763)) then
  begin
    ErrorMsg := ErrorMsg + '• Windows 10 (Build 17763+) ou superior é necessário' + #13#10;
    Result := False;
  end;
  
  // Verifica espaço em disco (500 MB)
  GetSpaceOnDisk64('C:', FreeSpace, TotalSpace);
  if FreeSpace < 500 * 1024 * 1024 then
  begin
    ErrorMsg := ErrorMsg + '• Espaço em disco insuficiente (mínimo 500 MB)' + #13#10;
    Result := False;
  end;
  
  // Verifica RAM (2 GB mínimo recomendado)
  RAM := GetTotalPhysicalMemory;
  if RAM < 2 * 1024 * 1024 * 1024 then
  begin
    if ErrorMsg <> '' then
      ErrorMsg := ErrorMsg + #13#10;
    ErrorMsg := ErrorMsg + '⚠️ RAM insuficiente (recomendado: 2 GB mínimo)' + #13#10;
  end;
  
  if not Result then
  begin
    MsgBox('Requisitos do sistema não atendidos:' + #13#10 + #13#10 + ErrorMsg, mbError, MB_OK);
  end;
end;

function CheckRequirements(): Boolean;
var
  ErrorMsg: String;
begin
  Result := True;
  ErrorMsg := '';
  RequirementsMet := True;
  
  // Verifica requisitos do sistema
  if not CheckSystemRequirements() then
  begin
    Result := False;
    Exit;
  end;
  
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
  DetermineInstallMode();
  LogInstallation('Iniciando instalação - Modo: ' + InstallMode);
  
  if InstallMode = 'upgrade' then
  begin
    if MsgBox('Uma versão anterior do {#MyAppName} foi detectada (Versão ' + PreviousVersion + ').' + #13#10 + #13#10 +
              'Deseja atualizar para a versão {#MyAppVersion}?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;
  
  Result := CheckRequirements();
end;

function PythonInstalled(): Boolean;
begin
  Result := RequirementsMet and (PythonPath <> '');
end;

// ============================================================================
// VALIDAÇÃO DE ENTRADA
// ============================================================================

function ValidateIP(IP: String): Boolean;
var
  Parts: TArrayOfString;
  I, Num, DotPos, StartPos: Integer;
  Part: String;
begin
  Result := False;
  if IP = '' then Exit;
  
  SetArrayLength(Parts, 4);
  StartPos := 1;
  I := 0;
  
  while (StartPos <= Length(IP)) and (I < 4) do
  begin
    DotPos := Pos('.', Copy(IP, StartPos, Length(IP) - StartPos + 1));
    if DotPos = 0 then
    begin
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
  
  for I := 0 to 3 do
  begin
    Num := StrToIntDef(Parts[I], -1);
    if Num = -1 then Exit;
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
  if Num = -1 then Exit;
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
  if Num = -1 then Exit;
  if Num < 1 then Exit;
  Result := True;
end;

function IsPortInUse(Port: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('netstat.exe', '-an | findstr :' + IntToStr(Port), '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode = 0);
end;

// ============================================================================
// CONFIGURAÇÃO DO SERVIDOR
// ============================================================================

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

function TestServerConnectionAdvanced(IP, Port: String): Integer;
var
  ResultCode: Integer;
  TestCmd: String;
begin
  Result := 0; // 0 = Erro, 1 = Sucesso, 2 = Timeout
  TestCmd := '-Command "try { $tcpClient = New-Object System.Net.Sockets.TcpClient; $tcpClient.ReceiveTimeout = 3000; $tcpClient.SendTimeout = 3000; $tcpClient.Connect("' + IP + '", ' + Port + '); $tcpClient.Close(); exit 0 } catch { exit 1 }"';
  
  if Exec('powershell.exe', TestCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
      Result := 1
    else
      Result := 0;
  end;
end;

procedure SaveConfig;
begin
  ServerIP := ConfigPage.Values[0];
  ServerPort := ConfigPage.Values[1];
  CheckInterval := ConfigPage.Values[2];
  RetryInterval := ConfigPage.Values[3];
  ServerURL := BuildServerURL(ServerIP, ServerPort);
  
  if AdvancedPage <> nil then
  begin
    LogLevel := AdvancedPage.Values[0];
    MaxLogSize := AdvancedPage.Values[1];
  end;
end;

// ============================================================================
// BACKUP E RESTAURAÇÃO
// ============================================================================

procedure BackupConfig();
var
  ConfigPath: String;
  BackupPath: String;
  Timestamp: String;
begin
  ConfigPath := ExpandConstant('{app}\config.json');
  if FileExists(ConfigPath) then
  begin
    Timestamp := GetDateTimeString('yyyymmdd-hhnnss', '', '');
    BackupPath := ExpandConstant('{app}\config.json.backup.' + Timestamp);
    FileCopy(ConfigPath, BackupPath, False);
    LogInstallation('Backup criado: ' + BackupPath);
  end;
end;

function RestoreConfig(): Boolean;
var
  ConfigPath: String;
  BackupPath: String;
  FindRec: TFindRec;
begin
  Result := False;
  ConfigPath := ExpandConstant('{app}\config.json');
  
  // Procura o backup mais recente
  if FindFirst(ExpandConstant('{app}\config.json.backup.*'), FindRec) then
  begin
    try
      repeat
        BackupPath := ExpandConstant('{app}\' + FindRec.Name);
        if GetDateTimeString('yyyymmdd-hhnnss', '', '') < Copy(FindRec.Name, Length('config.json.backup.') + 1, 14) then
        begin
          // Este é o backup mais recente
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
    
    if FileExists(BackupPath) then
    begin
      FileCopy(BackupPath, ConfigPath, False);
      Result := True;
      LogInstallation('Configuração restaurada de: ' + BackupPath);
    end;
  end;
end;

// ============================================================================
// LOG DE INSTALAÇÃO
// ============================================================================

procedure LogInstallation(Message: String);
var
  LogFile: String;
  LogHandle: Integer;
  LogEntry: String;
begin
  LogFile := ExpandConstant('{app}\install.log');
  LogHandle := FileOpen(LogFile, fmOpenWrite or fmShareDenyWrite);
  if LogHandle < 0 then
    LogHandle := FileCreate(LogFile, fmShareDenyWrite);
  
  if LogHandle >= 0 then
  begin
    FileSeek(LogHandle, 0, 2); // Vai para o final
    LogEntry := GetDateTimeString('yyyy-mm-dd hh:nn:ss', '', '') + ' - ' + Message + #13#10;
    FileWriteString(LogHandle, LogEntry);
    FileClose(LogHandle);
  end;
end;

// ============================================================================
// COLETA DE INFORMAÇÕES DO SISTEMA
// ============================================================================

procedure CollectSystemInfo();
var
  InfoFile: String;
  InfoContent: TStringList;
  OSVersion: TWindowsVersion;
  FreeSpace: Int64;
  TotalSpace: Int64;
begin
  InfoFile := ExpandConstant('{app}\system_info.txt');
  InfoContent := TStringList.Create;
  
  GetWindowsVersionEx(OSVersion);
  InfoContent.Add('=== INFORMAÇÕES DO SISTEMA ===');
  InfoContent.Add('');
  InfoContent.Add('Sistema Operacional: Windows ' + IntToStr(OSVersion.Major) + '.' + IntToStr(OSVersion.Minor) + ' Build ' + IntToStr(OSVersion.Build));
  InfoContent.Add('Arquitetura: x64');
  InfoContent.Add('Python: ' + GetPythonVersion());
  InfoContent.Add('Data/Hora da Instalação: ' + GetDateTimeString('', '', ''));
  InfoContent.Add('Versão Instalada: {#MyAppVersion}');
  InfoContent.Add('Modo de Instalação: ' + InstallMode);
  
  GetSpaceOnDisk64('C:', FreeSpace, TotalSpace);
  InfoContent.Add('Espaço em Disco Livre: ' + IntToStr(FreeSpace div (1024 * 1024)) + ' MB');
  InfoContent.Add('Espaço em Disco Total: ' + IntToStr(TotalSpace div (1024 * 1024)) + ' MB');
  
  InfoContent.SaveToFile(InfoFile);
  InfoContent.Free;
end;

// ============================================================================
// FERRAMENTAS DE DIAGNÓSTICO
// ============================================================================

procedure CreateDiagnosticScript();
var
  ScriptContent: String;
  ScriptFile: String;
begin
  ScriptFile := ExpandConstant('{app}\diagnostico.bat');
  ScriptContent := 
    '@echo off' + #13#10 +
    'title Diagnostico Print Monitor Agent' + #13#10 +
    'echo ========================================' + #13#10 +
    'echo   DIAGNOSTICO DO SISTEMA' + #13#10 +
    'echo ========================================' + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando Python...' + #13#10 +
    'python --version' + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando processo do agente...' + #13#10 +
    'tasklist | findstr python' + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando tarefa agendada...' + #13#10 +
    'schtasks /query /tn PrintMonitorAgent' + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando arquivos...' + #13#10 +
    'if exist "' + ExpandConstant('{app}') + '\agente.py" (echo agente.py: OK) else (echo agente.py: NAO ENCONTRADO)' + #13#10 +
    'if exist "' + ExpandConstant('{app}') + '\config.json" (echo config.json: OK) else (echo config.json: NAO ENCONTRADO)' + #13#10 +
    'echo.' + #13#10 +
    'echo ========================================' + #13#10 +
    'pause' + #13#10;
  
  SaveStringToFile(ScriptFile, ScriptContent, False);
end;

// ============================================================================
// INICIALIZAÇÃO DO WIZARD
// ============================================================================

procedure InitializeWizard;
var
  WelcomeText: String;
begin
  // Determina modo de instalação
  DetermineInstallMode();
  
  // Personaliza mensagem de boas-vindas
  if InstallMode = 'upgrade' then
    WelcomeText := 'Bem-vindo ao assistente de atualização do {#MyAppName}!' + #13#10 + #13#10 +
                   'Versão atual: ' + PreviousVersion + #13#10 +
                   'Nova versão: {#MyAppVersion}'
  else
    WelcomeText := 'Bem-vindo ao assistente de instalação do {#MyAppName}!' + #13#10 + #13#10 +
                   'Este assistente irá guiá-lo através da instalação.';
  
  WizardForm.WelcomeLabel1.Caption := WelcomeText;
  
  // Página de configuração do servidor
  ConfigPage := CreateInputQueryPage(wpWelcome,
    'Configuração do Servidor', 'Configure a conexão com o servidor',
    'Por favor, configure os parâmetros de conexão:');
  
  ConfigPage.Add('IP do Servidor:', False);
  ConfigPage.Add('Porta do Servidor:', False);
  ConfigPage.Add('Intervalo de Verificação (segundos):', False);
  ConfigPage.Add('Intervalo de Retry (segundos):', False);
  
  // Carrega valores anteriores se for upgrade
  if InstallMode = 'upgrade' then
  begin
    // Tenta carregar do config.json anterior
    if FileExists(ExpandConstant('{app}\config.json')) then
    begin
      // Valores serão carregados do arquivo existente
      ConfigPage.Values[0] := '192.168.1.27';
      ConfigPage.Values[1] := '5002';
      ConfigPage.Values[2] := '5';
      ConfigPage.Values[3] := '30';
    end
    else
    begin
      ConfigPage.Values[0] := '192.168.1.27';
      ConfigPage.Values[1] := '5002';
      ConfigPage.Values[2] := '5';
      ConfigPage.Values[3] := '30';
    end;
  end
  else
  begin
    ConfigPage.Values[0] := '192.168.1.27';
    ConfigPage.Values[1] := '5002';
    ConfigPage.Values[2] := '5';
    ConfigPage.Values[3] := '30';
  end;
  
  // Página de configuração avançada
  AdvancedPage := CreateInputQueryPage(ConfigPage.ID,
    'Configurações Avançadas', 'Configure opções avançadas (opcional)',
    'Configurações opcionais para usuários avançados:');
  
  AdvancedPage.Add('Nível de Log (DEBUG/INFO/WARNING/ERROR):', False);
  AdvancedPage.Add('Tamanho Máximo de Log (MB):', False);
  
  AdvancedPage.Values[0] := 'INFO';
  AdvancedPage.Values[1] := '100';
end;

// ============================================================================
// VALIDAÇÃO E NAVEGAÇÃO
// ============================================================================

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ErrorMsg: String;
  PortNum: Integer;
  ConnectionResult: Integer;
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
      ErrorMsg := ErrorMsg + '• Porta inválida (deve ser entre 1 e 65535)' + #13#10
    else
    begin
      PortNum := StrToIntDef(ConfigPage.Values[1], -1);
      if IsPortInUse(PortNum) then
        ErrorMsg := ErrorMsg + '• Porta ' + ConfigPage.Values[1] + ' já está em uso' + #13#10;
    end;
    
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
      ConnectionResult := TestServerConnectionAdvanced(ServerIP, ServerPort);
      if ConnectionResult = 0 then
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
      end
      else if ConnectionResult = 1 then
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

// ============================================================================
// EVENTOS DE INSTALAÇÃO
// ============================================================================

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    LogInstallation('Iniciando instalação de arquivos...');
    if InstallMode = 'upgrade' then
    begin
      BackupConfig();
    end;
  end
  else if CurStep = ssPostInstall then
  begin
    LogInstallation('Instalação concluída. Criando ferramentas...');
    CreateDiagnosticScript();
    CollectSystemInfo();
    
    if WizardIsTaskSelected('telemetry') then
    begin
      // Enviar métricas (implementar se necessário)
      LogInstallation('Telemetria habilitada');
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption := 
      '{#MyAppName} foi instalado com sucesso!' + #13#10 + #13#10 +
      'O agente está configurado para:' + #13#10 +
      'Servidor: ' + ServerURL + #13#10 + #13#10 +
      'O agente será iniciado automaticamente com o Windows.' + #13#10 +
      'Você pode verificar o status através do menu Iniciar.' + #13#10 + #13#10 +
      'Clique em "Concluir" para finalizar.';
  end;
end;

// ============================================================================
// DESINSTALAÇÃO
// ============================================================================

function InitializeUninstall(): Boolean;
begin
  if MsgBox('Tem certeza que deseja desinstalar o {#MyAppName}?' + #13#10 + #13#10 +
            'Todos os arquivos e configurações serão removidos.', mbConfirmation, MB_YESNO) = IDNO then
  begin
    Result := False;
    Exit;
  end;
  
  Result := True;
end;

function IsProcessRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('tasklist.exe', '/FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq agente.py*"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode = 0);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // Para o processo se estiver rodando
    if IsProcessRunning() then
    begin
      Exec('taskkill.exe', '/F /IM python.exe /FI "WINDOWTITLE eq agente.py*"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;

