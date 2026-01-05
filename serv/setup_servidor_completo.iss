; ============================================================================
; INNO SETUP SCRIPT - INSTALADOR DO SERVIDOR (VERSÃO COMPLETA)
; ============================================================================
; Gera um instalador executável (.exe) profissional com todas as funcionalidades
; Requer: Inno Setup Compiler 6.0+ (https://jrsoftware.org/isdl.php)
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
VersionInfoDescription=Servidor de Monitoramento de Impressões
VersionInfoCopyright=Copyright (C) 2024
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Components]
Name: "server"; Description: "Servidor Principal"; Types: full compact custom; Flags: fixed
Name: "modules"; Description: "Módulos do Sistema"; Types: full compact custom; Flags: fixed
Name: "templates"; Description: "Templates Web"; Types: full compact custom; Flags: fixed
Name: "static"; Description: "Arquivos Estáticos (CSS/JS)"; Types: full compact custom; Flags: fixed
Name: "tools"; Description: "Ferramentas Administrativas"; Types: full
Name: "docs"; Description: "Documentação"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1
Name: "firewall"; Description: "Configurar Firewall do Windows"; GroupDescription: "Configurações"; Flags: checkedonce
Name: "service"; Description: "Instalar como Serviço do Windows"; GroupDescription: "Configurações"; Flags: unchecked
Name: "installdeps"; Description: "Instalar dependências Python automaticamente"; GroupDescription: "Configurações"; Flags: checkedonce
Name: "launch"; Description: "Iniciar {#MyAppName} após instalação"; GroupDescription: "Opções"; Flags: unchecked
Name: "telemetry"; Description: "Enviar métricas de uso (opcional)"; GroupDescription: "Opções"; Flags: unchecked

[Files]
Source: "servidor.py"; DestDir: "{app}"; Flags: ignoreversion; Components: server
Source: "modules\*"; DestDir: "{app}\modules"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: modules
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: templates
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: static
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion; DestName: "requirements.txt"; Components: server
Source: "instalar_servidor.ps1"; DestDir: "{app}"; Flags: ignoreversion; Components: tools
Source: "instalar_servidor.py"; DestDir: "{app}"; Flags: ignoreversion; Components: tools
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: docs; Check: FileExistsCheck(ExpandConstant('{src}\README.md'))

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\servidor.py"""; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\servidor.py"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "python.exe"; Parameters: """{app}\servidor.py"""; WorkingDir: "{app}"; Tasks: quicklaunchicon
Name: "{group}\Abrir Pasta de Instalação"; Filename: "{app}"; Components: tools
Name: "{group}\Ver Logs"; Filename: "notepad.exe"; Parameters: "{code:GetLogPath}"; Components: tools
Name: "{group}\Abrir no Navegador"; Filename: "http://localhost:{code:GetServerPort}"; Components: tools
Name: "{group}\Diagnóstico do Sistema"; Filename: "{code:GetAppPath}\diagnostico.bat"; Components: tools
Name: "{group}\Documentação"; Filename: "{code:GetAppPath}\README.md"; Components: docs

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""if (Test-Path '{code:GetAppPath}\print_events.db') {{ Copy-Item '{code:GetAppPath}\print_events.db' '{code:GetAppPath}\backups\print_events.db.backup.' + (Get-Date -Format 'yyyyMMdd-HHmmss') + ' -Force }}"""; StatusMsg: "Fazendo backup do banco de dados..."; Flags: runhidden; Check: IsUpgrade
Filename: "python.exe"; Parameters: "-m pip install --upgrade pip --quiet"; StatusMsg: "Atualizando pip..."; Flags: runhidden; Tasks: installdeps; Check: PythonInstalled
Filename: "python.exe"; Parameters: "-m pip install -r ""{code:GetAppPath}\requirements.txt"""; StatusMsg: "Instalando dependências Python..."; Flags: runhidden; Tasks: installdeps; Check: PythonInstalled
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{code:GetAppPath}\instalar_servidor.ps1"" -SkipDependencies -ConfigureFirewall -Port {code:GetServerPort}"; StatusMsg: "Configurando firewall..."; Flags: runhidden; Tasks: firewall
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{code:GetAppPath}\instalar_servidor.ps1"" -SkipDependencies -InstallService -Port {code:GetServerPort}"; StatusMsg: "Instalando serviço do Windows..."; Flags: runhidden; Tasks: service
Filename: "python.exe"; Parameters: """{code:GetAppPath}\servidor.py"""; WorkingDir: "{code:GetAppPath}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent; Tasks: launch

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-Command ""Stop-Service -Name PrintMonitorServer -ErrorAction SilentlyContinue; Remove-Service -Name PrintMonitorServer -ErrorAction SilentlyContinue"""; Flags: runhidden; Check: IsServiceInstalled
Filename: "powershell.exe"; Parameters: "-Command ""Stop-Process -Name python -ErrorAction SilentlyContinue -Force"""; Flags: runhidden; Check: IsProcessRunning

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\backups"
Type: files; Name: "{app}\print_events.db"; Check: not KeepDatabaseOnUninstall

[Code]
var
  ConfigPage: TInputQueryWizardPage;
  AdvancedPage: TInputQueryWizardPage;
  ServerPort: String;
  ServerHost: String;
  LogLevel: String;
  MaxLogSize: String;
  PythonPath: String;
  PythonVersion: String;
  RequirementsMet: Boolean;
  PreviousVersion: String;
  InstallMode: String;
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
  Result := ExpandConstant('{app}\logs\servidor.log');
  if not FileExists(Result) then
    Result := ExpandConstant('{app}\logs');
end;

function GetServerPort(Param: String): String;
begin
  Result := ServerPort;
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
begin
  Result := 4 * 1024 * 1024 * 1024; // Assume 4GB se não conseguir obter
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
  
  if (OSVersion.Major < 10) or ((OSVersion.Major = 10) and (OSVersion.Build < 17763)) then
  begin
    ErrorMsg := ErrorMsg + '• Windows 10 (Build 17763+) ou superior é necessário' + #13#10;
    Result := False;
  end;
  
  GetSpaceOnDisk64('C:', FreeSpace, TotalSpace);
  if FreeSpace < 1000 * 1024 * 1024 then
  begin
    ErrorMsg := ErrorMsg + '• Espaço em disco insuficiente (mínimo 1 GB)' + #13#10;
    Result := False;
  end;
  
  RAM := GetTotalPhysicalMemory;
  if RAM < 4 * 1024 * 1024 * 1024 then
  begin
    if ErrorMsg <> '' then
      ErrorMsg := ErrorMsg + #13#10;
    ErrorMsg := ErrorMsg + '⚠️ RAM insuficiente (recomendado: 4 GB mínimo)' + #13#10;
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
  
  if not CheckSystemRequirements() then
  begin
    Result := False;
    Exit;
  end;
  
  if not FindPythonInstallation() then
  begin
    ErrorMsg := ErrorMsg + '• Python 3.8+ não encontrado' + #13#10;
    RequirementsMet := False;
  end;
  
  if not CheckDiskSpace(1000) then
  begin
    ErrorMsg := ErrorMsg + '• Espaço em disco insuficiente (mínimo 1 GB)' + #13#10;
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

function IsPortInUse(Port: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('netstat.exe', '-an | findstr :' + IntToStr(Port), '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode = 0);
end;

// ============================================================================
// BACKUP E RESTAURAÇÃO
// ============================================================================

procedure BackupDatabase();
var
  DBPath: String;
  BackupPath: String;
  Timestamp: String;
begin
  DBPath := ExpandConstant('{app}\print_events.db');
  if FileExists(DBPath) then
  begin
    Timestamp := GetDateTimeString('yyyymmdd-hhnnss', '', '');
    BackupPath := ExpandConstant('{app}\backups\print_events.db.backup.' + Timestamp);
    ForceDirectories(ExpandConstant('{app}\backups'));
    FileCopy(DBPath, BackupPath, False);
    LogInstallation('Backup do banco de dados criado: ' + BackupPath);
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
    FileSeek(LogHandle, 0, 2);
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
  InfoContent.Add('Porta do Servidor: ' + ServerPort);
  
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
    'title Diagnostico Print Monitor Server' + #13#10 +
    'echo ========================================' + #13#10 +
    'echo   DIAGNOSTICO DO SISTEMA' + #13#10 +
    'echo ========================================' + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando Python...' + #13#10 +
    'python --version' + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando processo do servidor...' + #13#10 +
    'tasklist | findstr python' + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando porta ' + ServerPort + '...' + #13#10 +
    'netstat -an | findstr :' + ServerPort + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando arquivos...' + #13#10 +
    'if exist "' + ExpandConstant('{app}') + '\servidor.py" (echo servidor.py: OK) else (echo servidor.py: NAO ENCONTRADO)' + #13#10 +
    'if exist "' + ExpandConstant('{app}') + '\print_events.db" (echo print_events.db: OK) else (echo print_events.db: NAO ENCONTRADO)' + #13#10 +
    'echo.' + #13#10 +
    'echo Verificando firewall...' + #13#10 +
    'netsh advfirewall firewall show rule name="Print Monitor Server" | findstr "Print Monitor"' + #13#10 +
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
  DetermineInstallMode();
  
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
    'Configuração do Servidor', 'Configure o servidor web',
    'Por favor, configure os parâmetros do servidor:');
  
  ConfigPage.Add('Porta do Servidor (padrão: 5002):', False);
  ConfigPage.Add('Host (0.0.0.0 para todas as interfaces):', False);
  
  if InstallMode = 'upgrade' then
  begin
    ConfigPage.Values[0] := '5002';
    ConfigPage.Values[1] := '0.0.0.0';
  end
  else
  begin
    ConfigPage.Values[0] := '5002';
    ConfigPage.Values[1] := '0.0.0.0';
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
begin
  Result := True;
  
  if CurPageID = ConfigPage.ID then
  begin
    ErrorMsg := '';
    
    // Valida Porta
    if ConfigPage.Values[0] = '' then
      ErrorMsg := ErrorMsg + '• Porta do servidor é obrigatória' + #13#10
    else if not ValidatePort(ConfigPage.Values[0]) then
      ErrorMsg := ErrorMsg + '• Porta inválida (deve ser entre 1 e 65535)' + #13#10
    else
    begin
      PortNum := StrToIntDef(ConfigPage.Values[0], -1);
      if IsPortInUse(PortNum) then
      begin
        if MsgBox('A porta ' + ConfigPage.Values[0] + ' já está em uso.' + #13#10 + #13#10 +
                  'Deseja continuar mesmo assim?', mbConfirmation, MB_YESNO) = IDNO then
        begin
          Result := False;
          Exit;
        end;
      end;
    end;
    
    // Valida Host
    if ConfigPage.Values[1] = '' then
      ConfigPage.Values[1] := '0.0.0.0';
    
    if ErrorMsg <> '' then
    begin
      MsgBox('Por favor, corrija os seguintes erros:' + #13#10 + #13#10 + ErrorMsg, mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    // Salva configurações
    ServerPort := ConfigPage.Values[0];
    ServerHost := ConfigPage.Values[1];
    
    if AdvancedPage <> nil then
    begin
      LogLevel := AdvancedPage.Values[0];
      MaxLogSize := AdvancedPage.Values[1];
    end;
    
    // Mostra resumo
    if MsgBox('Resumo da configuração:' + #13#10 + #13#10 +
              'Porta do Servidor: ' + ServerPort + #13#10 +
              'Host: ' + ServerHost + #13#10 +
              'URL de Acesso: http://localhost:' + ServerPort + #13#10 + #13#10 +
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
      BackupDatabase();
    end;
  end
  else if CurStep = ssPostInstall then
  begin
    LogInstallation('Instalação concluída. Criando ferramentas...');
    CreateDiagnosticScript();
    CollectSystemInfo();
    
    if WizardIsTaskSelected('telemetry') then
    begin
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
      'O servidor está disponível em:' + #13#10 +
      'http://localhost:' + ServerPort + #13#10 + #13#10 +
      'Você pode acessar através do navegador ou' + #13#10 +
      'usar o atalho "Abrir no Navegador" no menu Iniciar.' + #13#10 + #13#10 +
      'Clique em "Concluir" para finalizar.';
  end;
end;

// ============================================================================
// DESINSTALAÇÃO
// ============================================================================

function InitializeUninstall(): Boolean;
begin
  if MsgBox('Tem certeza que deseja desinstalar o {#MyAppName}?' + #13#10 + #13#10 +
            'Todos os arquivos serão removidos.' + #13#10 + #13#10 +
            'Deseja manter o banco de dados?', mbConfirmation, MB_YESNO) = IDYES then
  begin
    // Marca para manter banco de dados
    RegWriteStringValue(HKLM, 'SOFTWARE\PrintMonitor\Server', 'KeepDatabase', '1');
  end;
  
  Result := True;
end;

function KeepDatabaseOnUninstall(): Boolean;
var
  KeepDB: String;
begin
  Result := False;
  if RegQueryStringValue(HKLM, 'SOFTWARE\PrintMonitor\Server', 'KeepDatabase', KeepDB) then
    Result := (KeepDB = '1');
end;

function IsProcessRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('tasklist.exe', '/FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq servidor.py*"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode = 0);
end;

function IsServiceInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('sc.exe', 'query PrintMonitorServer', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode = 0);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if IsProcessRunning() then
    begin
      Exec('taskkill.exe', '/F /IM python.exe /FI "WINDOWTITLE eq servidor.py*"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;

