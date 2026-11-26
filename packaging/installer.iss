#ifndef Suffix
  #define Suffix ""
#endif
; 결(GYEOL) 설치 프로그램 (Inno Setup 6)
; packaging\build_installer.bat 이 PyInstaller 빌드 후 호출. 결과: packaging\output\Gyeol-Setup-<버전>.exe
#define AppName "결 GYEOL"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef DistDir
  #define DistDir "..\dist\Gyeol"
#endif
#define AppExe "Gyeol.exe"

[Setup]
AppId={{3618B333-71CA-45FC-BD81-5B077307DADB}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=GYEOL
; 관리자 권한 없이 사용자 계정에 설치 (UAC 창 없음). 프로젝트·설정은 설치 폴더의 data, 라이선스는 %LOCALAPPDATA%\Gyeol
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\Gyeol
DisableDirPage=yes
DisableProgramGroupPage=yes
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=Gyeol-Setup-{#AppVersion}{#Suffix}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
LZMANumBlockThreads=8
LZMAUseSeparateProcess=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "data\*"
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedsWebView2

[InstallDelete]
; 이전 버전 라이브러리 정리 (프로젝트·설정이 든 data 폴더는 그대로)
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Microsoft Edge WebView2 런타임 설치 중..."; Flags: waituntilterminated; Check: NeedsWebView2
Filename: "{app}\{#AppExe}"; Description: "{#AppName} 실행"; Flags: nowait postinstall skipifsilent
; 프로그램 안 [업데이트]로 무인 설치(/UPDATE)된 경우 설치 후 자동 실행
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: IsUpdate

[Messages]
korean.WinVersionTooLowError=이 프로그램은 Windows 10 이상(64비트)에서만 실행됩니다.

[Code]
function IsUpdate: Boolean;
var I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/UPDATE') = 0 then
      Result := True;
end;

const
  WebView2Key = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasWebView2Version(Root: Integer; SubKey: String): Boolean;
var
  V: String;
begin
  Result := RegQueryStringValue(Root, SubKey, 'pv', V) and (V <> '') and (V <> '0.0.0.0');
end;

function NeedsWebView2: Boolean;
begin
  Result := not (HasWebView2Version(HKLM, 'SOFTWARE\WOW6432Node\' + WebView2Key) or
                 HasWebView2Version(HKLM, 'SOFTWARE\' + WebView2Key) or
                 HasWebView2Version(HKCU, 'Software\' + WebView2Key));
end;

// 제거할 때 프로젝트·설정(API 키)·라이선스 정보도 지울지 묻기
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) then
    if MsgBox('만든 프레젠테이션 기록, 설정(API 키), 라이선스 정보도 모두 삭제할까요?' + #13#10 + #13#10 +
              '다시 설치해서 계속 사용하려면 [아니요]를 누르세요.' + #13#10 +
              '(내보내기로 저장한 PPTX·PDF 파일은 지워지지 않습니다)', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      DelTree(ExpandConstant('{app}\data'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\Gyeol'), True, True, True);
      RemoveDir(ExpandConstant('{app}'));
    end;
end;
