[Setup]
AppName=Mensajes Biblicos AutoPro
AppVersion=1.1.0
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
Source: "config_global.txt"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "version.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "compartido\*"; DestDir: "{app}\compartido"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "publicadores\*"; DestDir: "{app}\publicadores"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "mensajes\*"; DestDir: "{app}\mensajes"; Flags: onlyifdoesntexist recursesubdirs createallsubdirs

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
Filename: "{app}\WizardMensajes.exe"; Description: "Configurar Mensajes Biblicos"; Flags: nowait postinstall skipifsilent