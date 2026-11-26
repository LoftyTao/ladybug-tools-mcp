; Ladybug Tools MCP Windows x64 Offline Installer (Inno Setup 6)

#ifndef MyAppVersion
  #define MyAppVersion "1.3.0"
#endif
#ifndef StagingDir
  #define StagingDir "..\..\build\windows-offline-staging"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist\windows-offline"
#endif

[Setup]
AppId={{8F6D7E52-3A91-4B8F-9A4E-2B5D7E4E1234}
AppName=Ladybug Tools MCP
AppVersion={#MyAppVersion}
AppVerName=Ladybug Tools MCP {#MyAppVersion}
AppPublisher=Ladybug Tools MCP Contributors
AppPublisherURL=https://github.com/LoftyTao/ladybug-tools-mcp
DefaultDirName={code:GetDefaultInstallDir}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
WizardStyle=modern
LicenseFile={#StagingDir}\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename=lbt-mcp-{#MyAppVersion}-win-x64-setup
Compression=lzma2/normal
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\bin\lbt-mcp.exe
ChangesEnvironment=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "installurbanopt"; Description: "Install optional URBANopt 1.4.0-rc1 offline extension pack (detected beside installer)"; Check: HasSiblingUrbanoptPack; Flags: unchecked

[Files]
Source: "{#StagingDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
Filename: "{app}\bin\lbt-mcp.exe"; Parameters: "runtime sync --home ""{app}"" --gardens ""{code:GetGardensDir}"""; StatusMsg: "Configuring Ladybug Tools MCP runtimes..."; Flags: runhidden waituntilterminated
Filename: "{app}\bin\lbt-mcp.exe"; Parameters: "pack install ""{code:GetSiblingUrbanoptPack}"" --home ""{app}"" --force"; Tasks: installurbanopt; Check: HasSiblingUrbanoptPack; StatusMsg: "Installing optional URBANopt offline extension pack..."; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: files; Name: "{app}\runtimes\ironbug\1.26.1\OpenStudio.dll"
Type: files; Name: "{app}\runtimes\ironbug\1.26.1\openstudiolib.dll"
Type: files; Name: "{app}\runtimes\ironbug\1.26.1\openstudio_csharp.dll"
Type: files; Name: "{app}\runtimes\ironbug\1.26.1\openstudio_model_csharp.dll"
Type: files; Name: "{app}\runtimes\ironbug\1.26.1\openstudio_translators_csharp.dll"
Type: filesandordirs; Name: "{app}\config"
Type: filesandordirs; Name: "{app}\packs"
Type: filesandordirs; Name: "{app}\tmp"
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\runtimes"
Type: dirifempty; Name: "{app}"

[Code]
var
  GardensDirPage: TInputDirWizardPage;
  CachedUrbanoptPackPath: string;
  UrbanoptPackScanned: Boolean;

function IsAsciiSpaceFree(const S: string): Boolean;
var
  I: Integer;
  Code: Integer;
begin
  Result := Length(S) > 0;
  for I := 1 to Length(S) do
  begin
    Code := Ord(S[I]);
    if (Code <= 32) or (Code >= 127) then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

function NormalizeDirForCompare(const S: string): string;
var
  Clean: string;
begin
  Clean := Trim(S);
  StringChangeEx(Clean, '/', '\', True);
  Clean := RemoveBackslashUnlessRoot(Clean);
  Result := Lowercase(AddBackslash(Clean));
end;

function PathsOverlap(const PathA, PathB: string): Boolean;
var
  NormA, NormB: string;
begin
  NormA := NormalizeDirForCompare(PathA);
  NormB := NormalizeDirForCompare(PathB);
  if (NormA = '') or (NormB = '') then
  begin
    Result := False;
    Exit;
  end;
  Result := (NormA = NormB) or (Pos(NormA, NormB) = 1) or (Pos(NormB, NormA) = 1);
end;

function GetDefaultInstallDir(Param: string): string;
var
  LocalAppCandidate: string;
begin
  LocalAppCandidate := AddBackslash(ExpandConstant('{localappdata}')) + 'lbt-mcp';
  if IsAsciiSpaceFree(LocalAppCandidate) then
    Result := LocalAppCandidate
  else
    Result := 'C:\lbt-mcp';
end;

function GetDefaultGardensRoot(): string;
var
  ParamGardens: string;
  UserProf: string;
begin
  ParamGardens := Trim(ExpandConstant('{param:GARDENS|}'));
  if ParamGardens <> '' then
  begin
    Result := ParamGardens;
    Exit;
  end;
  UserProf := Trim(GetEnv('USERPROFILE'));
  if UserProf <> '' then
    Result := AddBackslash(UserProf) + 'Gardens'
  else
    Result := AddBackslash(ExpandConstant('{userdocs}')) + 'Gardens';
end;

function FindSiblingUrbanoptPack(): string;
var
  SourceDir: string;
  FindRec: TFindRec;
begin
  if UrbanoptPackScanned then
  begin
    Result := CachedUrbanoptPackPath;
    Exit;
  end;
  UrbanoptPackScanned := True;
  CachedUrbanoptPackPath := '';
  SourceDir := ExtractFileDir(ExpandConstant('{srcexe}'));
  if FindFirst(AddBackslash(SourceDir) + 'lbt-mcp-*-win-x64-urbanopt.lbtpack', FindRec) then
  begin
    try
      if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) = 0 then
        CachedUrbanoptPackPath := AddBackslash(SourceDir) + FindRec.Name;
    finally
      FindClose(FindRec);
    end;
  end;
  Result := CachedUrbanoptPackPath;
end;

function HasSiblingUrbanoptPack(): Boolean;
begin
  Result := FindSiblingUrbanoptPack() <> '';
end;

function GetSiblingUrbanoptPack(Param: string): string;
begin
  Result := FindSiblingUrbanoptPack();
end;

function GetGardensDir(Param: string): string;
begin
  if Assigned(GardensDirPage) and (Trim(GardensDirPage.Values[0]) <> '') then
    Result := RemoveBackslashUnlessRoot(Trim(GardensDirPage.Values[0]))
  else
    Result := RemoveBackslashUnlessRoot(GetDefaultGardensRoot());
end;

procedure InitializeWizard();
begin
  UrbanoptPackScanned := False;
  CachedUrbanoptPackPath := '';
  GardensDirPage := CreateInputDirPage(
    wpSelectDir,
    'Select Gardens Directory',
    'Where should Ladybug Tools MCP store your project Gardens?',
    'Project Gardens (models, simulation runs, weather files) are stored outside the application directory so they are preserved across upgrades and uninstalls.',
    False,
    'Gardens'
  );
  GardensDirPage.Add('Gardens folder:');
  GardensDirPage.Values[0] := GetDefaultGardensRoot();
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  AppDir: string;
  GardensDir: string;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    AppDir := Trim(WizardDirValue);
    if not IsAsciiSpaceFree(AppDir) then
    begin
      if SuppressibleMsgBox(
        'The selected runtime installation folder contains spaces or non-ASCII characters:' + #13#10 +
        AppDir + #13#10#13#10 +
        'OpenStudio, EnergyPlus, Radiance, and Ruby tools can fail under paths containing spaces or non-ASCII characters. ' +
        'Use a pure ASCII path without spaces (such as C:\lbt-mcp) unless you accept this risk.' + #13#10#13#10 +
        'Continue with this folder anyway?',
        mbConfirmation,
        MB_YESNO,
        IDYES
      ) <> IDYES then
      begin
        Result := False;
        Exit;
      end;
    end;
  end
  else if Assigned(GardensDirPage) and (CurPageID = GardensDirPage.ID) then
  begin
    GardensDir := Trim(GardensDirPage.Values[0]);
    if GardensDir = '' then
    begin
      SuppressibleMsgBox('Please choose a valid Gardens directory.', mbError, MB_OK, IDOK);
      Result := False;
      Exit;
    end;
    if PathsOverlap(WizardDirValue, GardensDir) then
    begin
      SuppressibleMsgBox(
        'The Gardens directory must be outside the application runtime directory (' + WizardDirValue + ') so your project models are preserved across upgrades and uninstalls.',
        mbError,
        MB_OK,
        IDOK
      );
      Result := False;
      Exit;
    end;
  end;
end;
