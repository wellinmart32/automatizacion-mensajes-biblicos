[Setup]
AppName=Mensajes Biblicos AutoPro
AppVersion=1.4.0
AppPublisher=AutomaPro
AppPublisherURL=https://automapro.com
DefaultDirName={userdocs}\AutomaPro\MensajesBiblicos
DefaultGroupName=AutomaPro\MensajesBiblicos
OutputDir=installer_output
OutputBaseFilename=InstaladorMensajesBiblicos
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el Escritorio"; GroupDescription: "Iconos adicionales:"

[Files]
Source: "dist\MensajesBiblicos.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\ConfiguradorMensajes.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\OracionesWhatsApp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\WizardMensajes.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\PanelControl.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\ExtractorPredicaciones.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\GestorMensajes.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\GestorTareasMensajes.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config_global.ejemplo.txt"; DestDir: "{app}"; DestName: "config_global.txt"; Flags: onlyifdoesntexist
Source: "version.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "compartido\*"; DestDir: "{app}\compartido"; Excludes: "__pycache__"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "publicadores\*"; DestDir: "{app}\publicadores"; Excludes: "__pycache__"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "mensajes\*"; DestDir: "{app}\mensajes"; Flags: onlyifdoesntexist recursesubdirs createallsubdirs; Check: EsInstalacionNueva

[InstallDelete]
Type: files; Name: "{app}\publicadores\publicador_facebook_enlaces.py"
Type: filesandordirs; Name: "{app}\compartido\__pycache__"
Type: filesandordirs; Name: "{app}\publicadores\__pycache__"

[Dirs]
Name: "{app}\mensajes"
Name: "{app}\perfiles"

[Icons]
Name: "{autoprograms}\Mensajes Biblicos\Mensajes Biblicos"; Filename: "{app}\MensajesBiblicos.exe"
Name: "{autoprograms}\Mensajes Biblicos\Panel de Control"; Filename: "{app}\PanelControl.exe"
Name: "{autoprograms}\Mensajes Biblicos\Configurador"; Filename: "{app}\ConfiguradorMensajes.exe"
Name: "{autodesktop}\Mensajes Biblicos"; Filename: "{app}\MensajesBiblicos.exe"; Tasks: desktopicon
Name: "{autodesktop}\Panel de Control MB"; Filename: "{app}\PanelControl.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\WizardMensajes.exe"; Description: "Configurar Mensajes Biblicos"; Flags: nowait postinstall skipifsilent; Check: EsInstalacionNueva

[Code]
var
  InstalacionNueva: Boolean;

// Se evalúa antes de copiar archivos: si ya hay configuración, es una actualización y no se tocan los datos del cliente
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    InstalacionNueva := not FileExists(ExpandConstant('{app}\config_global.txt'));
end;

function EsInstalacionNueva: Boolean;
begin
  Result := InstalacionNueva;
end;