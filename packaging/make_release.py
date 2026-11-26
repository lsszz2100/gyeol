"""릴리스 생성·업로드 (release.bat / release_full.bat 에서 호출)

  python packaging\\make_release.py code   # 바뀐 코드·화면만
  python packaging\\make_release.py full   # 전체 설치 파일 + 코드 (build_installer.bat 실행 후)
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from version import APP_VERSION, UPDATE_REPO, REQUIRED_RUNTIME

LAST_FULL = HERE / "last_full_release.txt"
# 마지막 전체 설치 파일 정보. 코드만 배포할 때도 이 설치 파일을 함께 올려야
# 아직 기반(runtime)이 낮은 고객이 '전체 설치 파일'로 따라올 수 있다 (업데이트는 최신 릴리스 파일만 봄)
LAST_SETUP = HERE / "last_full_setup.json"


def carried_setup():
    """현재 기반 번호와 같은 마지막 전체 설치 파일 (manifest 항목, 로컬 경로). 없으면 (None, None)."""
    try:
        info = json.loads(LAST_SETUP.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    setup = HERE / "output" / info.get("name", "")
    if int(info.get("runtime", 0)) != REQUIRED_RUNTIME or not setup.is_file():
        return None, None
    if setup.stat().st_size != info.get("size") or sha256(setup) != info.get("sha256"):
        sys.exit(f"[오류] {setup.name} 이(가) 마지막 전체 배포 때와 다릅니다. 같은 파일을 두거나 release_full.bat 으로 배포하세요.")
    return {k: info[k] for k in ("name", "sha256", "size")}, setup


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def gh_exe() -> str:
    found = shutil.which("gh")
    if found:
        return found
    pat = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages", "GitHub.cli_*", "bin", "gh.exe")
    hits = glob.glob(pat)
    if not hits:
        sys.exit("[오류] GitHub CLI(gh)를 찾을 수 없습니다. winget install GitHub.cli 후 gh auth login")
    return hits[0]


def main(kind: str):
    if kind not in ("code", "full"):
        sys.exit("사용법: make_release.py code|full")
    if not UPDATE_REPO:
        sys.exit("[오류] version.py 의 UPDATE_REPO 가 비어 있습니다.")
    gh = gh_exe()
    # 같은 버전 재배포 방지 (버전을 올리지 않고 실행한 경우)
    if subprocess.run([gh, "release", "view", f"v{APP_VERSION}", "--repo", UPDATE_REPO],
                      capture_output=True).returncode == 0:
        sys.exit(f"[오류] v{APP_VERSION} 은(는) 이미 배포되어 있습니다. version.py 의 APP_VERSION 을 올려 주세요.")

    print("[묶음] 코드·화면 묶음 만들기 + 서명...")
    import make_code
    import signing
    seed = make_code.seed()
    compiled = make_code.build()
    print("[점검] 배포 전 자동 점검...")
    if subprocess.run([sys.executable, str(HERE / "smoke_test.py")]).returncode != 0:
        sys.exit("[중단] 점검에 실패해 배포하지 않았습니다. 오류를 고친 뒤 다시 실행하세요.")

    out = HERE / "output" / f"release-{APP_VERSION}"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    code_name = f"Gyeol-code-{APP_VERSION}.zip"
    code_zip = out / code_name
    with zipfile.ZipFile(code_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(compiled.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(compiled).as_posix())
    files = [code_zip]

    notes_file = HERE / "release_notes.txt"
    notes = notes_file.read_text(encoding="utf-8").strip() if notes_file.exists() else f"GYEOL {APP_VERSION}"
    manifest = {
        "version": APP_VERSION,
        "runtime": REQUIRED_RUNTIME,
        "notes": notes,
        "code": {"name": code_name, "sha256": sha256(code_zip), "size": code_zip.stat().st_size},
        "setup": None,
    }
    if kind == "full":
        setup = HERE / "output" / f"Gyeol-Setup-{APP_VERSION}.exe"
        if not setup.exists():
            sys.exit(f"[오류] 설치 파일이 없습니다: {setup} (build_installer.bat 먼저 실행)")
        digest = sha256(setup)
        manifest["setup"] = {"name": setup.name, "sha256": digest, "size": setup.stat().st_size}
        files.append(setup)
        LAST_SETUP.write_text(json.dumps({**manifest["setup"], "runtime": REQUIRED_RUNTIME}, indent=2), encoding="utf-8")
    else:
        carry, setup = carried_setup()
        if carry:
            manifest["setup"] = carry
            files.append(setup)
            print(f"[포함] 기반이 낮은 고객용 전체 설치 파일 {setup.name} 도 함께 올립니다.")
        elif REQUIRED_RUNTIME > 1:
            print("[주의] 현재 기반용 전체 설치 파일 정보가 없어, 기반이 낮은 고객은 이 버전을 받지 못합니다.")

    # 개발자 서명 (설치된 프로그램이 이 서명을 확인한 뒤에만 업데이트)
    manifest = signing.sign_manifest(manifest, seed)
    (out / "update.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    files.append(out / "update.json")

    body = notes
    if kind == "code":
        last = LAST_FULL.read_text(encoding="utf-8").strip() if LAST_FULL.exists() else ""
        body += ("\n\n※ 이 버전은 바뀐 코드만 담은 업데이트입니다. 설치된 프로그램에서 [업데이트]를 누르면 몇 초 만에 적용됩니다."
                 + (f"\n※ 처음 설치하실 분은 설치 파일을 여기서 받으세요: {last}" if last else ""))
    notes_tmp = out / "notes.md"
    notes_tmp.write_text(body, encoding="utf-8")

    print(f"[배포] v{APP_VERSION} ({'바뀐 코드만' if kind == 'code' else '전체 설치 파일'}) 업로드: "
          + ", ".join(f"{f.name} ({round(f.stat().st_size / 1048576, 2)}MB)" for f in files))
    r = subprocess.run([gh, "release", "create", f"v{APP_VERSION}", *map(str, files), "--repo", UPDATE_REPO,
                        "--title", f"GYEOL {APP_VERSION}", "--notes-file", str(notes_tmp), "--latest"])
    if r.returncode != 0:
        sys.exit("[실패] GitHub 업로드 실패")
    url = f"https://github.com/{UPDATE_REPO}/releases/tag/v{APP_VERSION}"
    if kind == "full":
        LAST_FULL.write_text(url, encoding="utf-8")
    print(f"배포 완료: {url}")
    notify_running_app()
    print("다른 PC의 설치된 프로그램은 시작 시, 3분마다, 창을 다시 볼 때 새 버전을 확인해 업데이트 알림을 표시합니다.")


def notify_running_app():
    """GitHub에 새 버전이 보이면(보통 1분 이내) 이 PC에서 켜져 있는 프로그램에 바로 확인시켜
    10분 주기를 기다리지 않고 업데이트 알림이 뜨게 한다."""
    import time
    import urllib.request
    manifest_url = f"https://github.com/{UPDATE_REPO}/releases/latest/download/update.json"
    print("[알림] GitHub 반영 대기 중 (보통 1분 이내)...", flush=True)
    for _ in range(36):
        try:
            with urllib.request.urlopen(urllib.request.Request(manifest_url, headers={"Cache-Control": "no-cache"}),
                                        timeout=15) as r:
                if json.loads(r.read().decode("utf-8")).get("version") == APP_VERSION:
                    break
        except Exception:
            pass
        time.sleep(5)
    else:
        print("[알림] 3분 안에 GitHub 반영을 확인하지 못했습니다. 프로그램이 10분 안에 스스로 확인합니다.")
        return
    sent = False
    for inst in (ROOT / "data" / "instance.json",):
        try:
            info = json.loads(inst.read_text(encoding="utf-8"))
            port = int(info["port"])
            origin = f"http://127.0.0.1:{port}"
            req = urllib.request.Request(f"{origin}/api/update/check", data=b"{}", method="POST",
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                st = json.loads(r.read().decode("utf-8"))
            print(f"[알림] 켜져 있는 프로그램(v{st.get('current')})에 새 버전 v{st.get('latest')} 알림 표시 요청 완료")
            sent = True
        except Exception:
            continue
    if not sent:
        print("[알림] 이 PC에 켜져 있는 프로그램이 없습니다. 다음에 켤 때 바로 업데이트 알림이 뜹니다.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "code")
