r"""자동 업데이트 (core/updater.py)

- 코드 업데이트(기본): 코드·화면 묶음(zip)만 받아 %LOCALAPPDATA%\\Gyeol\\appcode\\<버전> 에 풀고 다시 시작
  → launcher.py 가 서명을 확인하고 더 새 코드를 불러온다.
- 전체 업데이트: 라이브러리(기반 번호)가 바뀐 경우에만 설치 파일을 받아 무인 설치.
update.json 은 packaging\\make_release.py 가 만들어 GitHub 릴리스에 올린다.
"""
import os
import re
import json
import time
import hashlib
import logging
import threading
import subprocess
import sys
import shutil
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional

import version
from version import APP_VERSION, UPDATE_REPO

DISPLAY_VERSION = APP_VERSION
IS_FROZEN = bool(getattr(sys, "frozen", False))
UPDATE_BASE = getattr(version, "UPDATE_BASE", "https://github.com")   # 서명된 시험 코드만 바꿀 수 있다
USER_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Gyeol"

logger = logging.getLogger("kdesign.updater")

UPDATE_DIR = USER_DIR / "updates"
CODE_ROOT = USER_DIR / "appcode"


def _installed_runtime() -> int:
    """설치된 기반(런타임) 번호. 개발 실행이면 무한대로 취급."""
    if not IS_FROZEN:
        return 10 ** 6
    try:
        return int((Path(sys._MEIPASS) / "runtime.txt").read_text(encoding="ascii").strip())
    except Exception:
        return 0
CHECK_INTERVAL_SEC = 3 * 60    # 3분마다 새 버전 확인 (다운로드 주소 방식이라 조회 제한 없음, 파일은 수백 바이트)
MIN_RECHECK_SEC = 30            # 창을 다시 볼 때의 즉시 확인은 30초에 한 번까지만
_UA = {"User-Agent": f"Gyeol/{APP_VERSION}", "Accept": "application/vnd.github+json"}

_lock = threading.Lock()
STATE = {
    "current": APP_VERSION,
    "display": DISPLAY_VERSION,     # 화면 표시 버전
    "latest_display": None,
    "latest": None,          # 최신 버전 문자열
    "available": False,      # 새 버전 있음
    "notes": "",
    "label": "",             # 안내 제목 (예: '라이선스 업데이트'). 비어 있으면 '새 버전 vX
    "state": "idle",         # 진행 상태: idle | checking | downloading | verifying | installing | error
    "progress": 0,           # 다운로드 %
    "downloaded_mb": 0.0,
    "total_mb": 0.0,
    "error": "",
    "can_install": IS_FROZEN and bool(UPDATE_REPO),   # 개발 실행에서는 설치 불가
    "checked_at": None,
    "kind": None,            # code(바뀐 코드만) | full(전체 설치 파일)
    "size_mb": 0.0,
    "just_updated": None,    # 방금 업데이트로 재시작된 경우 {"from":…, "to":…, "notes":…}
}
_release: dict = {}


def _ver(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def notes_label(body: str) -> str:
    """릴리스 본문 첫 줄이 버전 제목이 아니면 안내 제목으로 사용 (예: '라이선스 업데이트')."""
    first = (body or "").replace("\r\n", "\n").split("\n")[0].strip()
    if first and len(first) <= 30 and not re.match(r"^(GYEOL|결)\b", first) and not first.startswith("-"):
        return first
    return ""


def clean_notes(body: str) -> str:
    """릴리스 본문에서 첫 줄 제목(GYEOL x.y.z)과 빈 줄 정리 → 사용자에게 보여줄 변경 내용."""
    lines = [l.rstrip() for l in (body or "").replace("\r\n", "\n").split("\n")]
    if lines and (re.match(r"^\s*(GYEOL|결)\s+v?[\d.]+\s*$", lines[0]) or notes_label(body)):
        lines = lines[1:]
    text = "\n".join(lines).strip()
    return text[:1500] or "변경 내용이 등록되지 않았습니다."


PENDING_FILE = UPDATE_DIR / "pending.json"     # 업데이트 설치 직전에 기록 → 재시작 후 완료 안내
LAST_RUN_FILE = USER_DIR / "last_version.txt"  # 마지막으로 실행된 버전 (구버전 업데이트도 감지)


def detect_just_updated():
    """시작 시 호출: 업데이트 직후 재시작이면 완료 안내 정보를 STATE['just_updated']에 담는다."""
    info = None
    try:
        if PENDING_FILE.exists():
            p = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
            ok = _ver(APP_VERSION) >= _ver(p.get("to", "0"))
            info = {"from": p.get("from"), "to": APP_VERSION, "notes": p.get("notes", ""), "ok": ok,
                    "expected": p.get("to"), "from_display": p.get("from_display") or p.get("from")}
            PENDING_FILE.unlink(missing_ok=True)
        elif LAST_RUN_FILE.exists():
            last = LAST_RUN_FILE.read_text(encoding="utf-8").strip()
            if last and _ver(APP_VERSION) > _ver(last):
                info = {"from": last, "to": APP_VERSION, "notes": "", "ok": True, "expected": APP_VERSION}
        LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_RUN_FILE.write_text(APP_VERSION, encoding="utf-8")
    except Exception as e:
        logger.debug(f"업데이트 완료 감지 실패: {e}")
    if info:
        if info["ok"]:
            logger.info(f"✅ v{info['from']} → v{APP_VERSION} 업데이트 완료, 자동으로 다시 시작되었습니다.")
        else:
            logger.warning(f"⚠️ v{info['expected']} 업데이트가 완료되지 않았습니다 (현재 v{APP_VERSION}).")
        _set(just_updated=info)
        if info["ok"] and not info["notes"] and UPDATE_REPO:
            # 구버전에서 업데이트된 경우 변경 내용을 GitHub에서 가져옴
            def fetch():
                try:
                    req = urllib.request.Request(
                        f"https://api.github.com/repos/{UPDATE_REPO}/releases/tags/v{APP_VERSION}", headers=_UA)
                    with urllib.request.urlopen(req, timeout=10) as r:
                        info["notes"] = clean_notes(json.loads(r.read().decode("utf-8")).get("body", ""))
                    _set(just_updated=dict(info))
                except Exception:
                    pass
            threading.Thread(target=fetch, daemon=True).start()


def ack_just_updated():
    _set(just_updated=None)


def _set(**kw):
    with _lock:
        STATE.update(kw)


def status() -> dict:
    with _lock:
        return dict(STATE)


def status_fresh() -> dict:
    """창을 다시 열어 보거나 앞으로 가져올 때: 마지막 확인이 30초 넘었으면 지금 바로 확인."""
    last = STATE.get("_checked_ts") or 0
    if UPDATE_REPO and time.time() - last > MIN_RECHECK_SEC:
        check()
    return status()


def _get_json(url: str):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def _manifest_from_cdn():
    """GitHub 다운로드 주소로 최신 update.json 조회 (API 시간당 60회 제한과 무관)."""
    m = _get_json(f"{UPDATE_BASE}/{UPDATE_REPO}/releases/latest/download/update.json")
    base = f"{UPDATE_BASE}/{UPDATE_REPO}/releases/download/v{m['version']}/"
    assets = {}
    for key in ("code", "setup"):
        a = m.get(key)
        if a:
            assets[a["name"]] = {"name": a["name"], "browser_download_url": base + a["name"], "size": a.get("size", 0)}
    return m, assets, m.get("notes", "")


def _manifest_from_api():
    rel = _get_json(f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest")
    assets = {a["name"]: a for a in rel.get("assets", [])}
    m = _get_json(assets["update.json"]["browser_download_url"]) if "update.json" in assets else None
    return m, assets, (m or {}).get("notes") or rel.get("body", "")


def check(force: bool = False) -> dict:
    """최신 릴리스의 update.json 확인. 실패해도 프로그램 사용에는 영향 없음."""
    if not UPDATE_REPO:
        return status()
    if STATE["state"] in ("downloading", "verifying", "installing"):
        return status()
    _set(state="checking", error="")
    try:
        try:
            manifest, assets, notes = _manifest_from_cdn()
        except Exception as e:
            logger.debug(f"다운로드 주소 조회 실패({e}) → API로 재시도")
            manifest, assets, notes = _manifest_from_api()
        # 개발자 서명이 맞는 업데이트 정보만 신뢰 (배포 저장소가 털려도 가짜 업데이트 차단)
        from core import sigcheck
        if manifest is not None and not sigcheck.verify_manifest(manifest):
            raise RuntimeError("업데이트 정보의 서명이 올바르지 않아 무시합니다.")
        latest = (manifest or {}).get("version")
        newer = bool(latest) and _ver(latest) > _ver(APP_VERSION) and manifest is not None
        kind, pick = None, None
        if newer:
            code, setup = manifest.get("code"), manifest.get("setup")
            # 기반이 그대로면 바뀐 코드만, 기반이 바뀌었으면 전체 설치 파일
            if code and int(manifest.get("runtime", 1)) <= _installed_runtime() and code["name"] in assets:
                kind, pick = "code", code
            elif setup and setup["name"] in assets:
                kind, pick = "full", setup
            else:
                newer = False
        _release.clear()
        if newer:
            if not re.fullmatch(r"Gyeol-(?:code|Setup)-[\d.]+\.(?:zip|exe)", pick["name"]):
                raise RuntimeError("업데이트 파일 이름이 올바르지 않습니다.")
            a = assets[pick["name"]]
            _release.update(kind=kind, url=a["browser_download_url"], name=a["name"],
                            size=a.get("size") or pick.get("size", 0), sha256=pick["sha256"].lower(), version=latest)
        _set(latest=latest or None, available=newer, kind=kind,
             size_mb=round(_release.get("size", 0) / 1048576, 2) if newer else 0.0,
             notes=clean_notes(notes) if newer else "",
             label=notes_label(notes) if newer else "",
             latest_display=(manifest or {}).get("display_version") or latest,
             state="idle", checked_at=time.strftime("%Y-%m-%d %H:%M"), _checked_ts=time.time())
        if newer:
            logger.info(f"🔔 새 버전 {latest} 이(가) 있습니다. (현재 {APP_VERSION}, "
                        f"{'바뀐 코드만' if kind == 'code' else '전체 설치 파일'} {STATE['size_mb']}MB)")
    except Exception as e:
        _set(state="idle", error="", checked_at=time.strftime("%Y-%m-%d %H:%M"))
        logger.info(f"업데이트 확인 건너뜀: {e}")
    return status()


def start_background_checks():
    def loop():
        while True:
            check()
            time.sleep(CHECK_INTERVAL_SEC)
    threading.Thread(target=loop, daemon=True).start()


def _download(url: str, dest, total: int):
    req = urllib.request.Request(url, headers={"User-Agent": _UA["User-Agent"], "Accept": "application/octet-stream"})
    done = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or total or 0)
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            _set(progress=int(done * 100 / total) if total else 0,
                 downloaded_mb=round(done / 1048576, 1), total_mb=round(total / 1048576, 1))


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().lower()


def _restart_self():
    """코드 업데이트 후 같은 EXE를 새로 실행 (이전 프로세스 종료를 기다렸다가 시작)."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([sys.executable, "--wait-pid", str(os.getpid())], creationflags=flags, close_fds=True)


def install(shutdown_app) -> Optional[str]:
    """다운로드·검증 후 적용하고 shutdown_app()으로 현재 프로그램을 종료(→ 자동 재시작). 오류 시 메시지 반환."""
    if not STATE["can_install"]:
        return "개발 실행에서는 업데이트를 설치할 수 없습니다. 설치형 프로그램에서 사용하세요."
    if not _release:
        return "설치할 새 버전이 없습니다."
    if STATE["state"] in ("downloading", "verifying", "installing"):
        return None

    def run():
        try:
            r = dict(_release)
            ver, kind = r["version"], r["kind"]
            UPDATE_DIR.mkdir(parents=True, exist_ok=True)
            dest = UPDATE_DIR / r["name"]
            _set(state="downloading", progress=0, error="")
            logger.info(f"⬇ 업데이트 v{ver} 다운로드 시작 ({'바뀐 코드' if kind == 'code' else '전체 설치 파일'}, {round(r['size'] / 1048576, 2)}MB)")
            _download(r["url"], dest, r["size"])

            _set(state="verifying")
            if _sha256(dest) != r["sha256"]:
                dest.unlink(missing_ok=True)
                raise RuntimeError("내려받은 파일의 무결성 검증(SHA256)에 실패했습니다. 다시 시도해 주세요.")

            if kind == "code":
                # 새 코드 폴더에 풀고 검사한 뒤 current.txt 전환 (실패 시 기존 코드 그대로)
                target = CODE_ROOT / ver
                tmp = CODE_ROOT / f".{ver}.tmp"
                shutil.rmtree(tmp, ignore_errors=True)
                with zipfile.ZipFile(dest) as z:
                    for n in z.namelist():
                        if n.startswith("/") or ".." in Path(n).parts:
                            raise RuntimeError("업데이트 파일 형식이 올바르지 않습니다.")
                    z.extractall(tmp)
                if not any(tmp.glob("app.*.pyd")) or f'"{ver}"' not in (tmp / "version.py").read_text(encoding="utf-8") \
                        or not _manifest_ok(tmp):
                    shutil.rmtree(tmp, ignore_errors=True)
                    raise RuntimeError("업데이트 파일 내용이 올바르지 않습니다.")
                shutil.rmtree(target, ignore_errors=True)
                tmp.rename(target)
                (CODE_ROOT / "current.txt").write_text(ver, encoding="utf-8")
                dest.unlink(missing_ok=True)

            _set(state="installing", progress=100)
            logger.info(f"✔ 검증 완료 → v{ver} 적용. 프로그램이 잠시 닫혔다가 자동으로 다시 시작됩니다.")
            PENDING_FILE.write_text(json.dumps({"from": APP_VERSION, "to": ver, "notes": STATE.get("notes", ""),
                                                "from_display": DISPLAY_VERSION},
                                               ensure_ascii=False), encoding="utf-8")
            time.sleep(3)  # '잠시 닫혔다가 자동으로 다시 시작됩니다' 안내를 읽을 시간
            if kind == "code":
                _restart_self()
            else:
                # /SILENT: 질문 없이 설치 진행 창만 표시, /UPDATE: 설치 후 새 버전 자동 실행 (installer.iss)
                flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                subprocess.Popen([str(dest), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/UPDATE"],
                                 creationflags=flags, close_fds=True)
                time.sleep(1)
            shutdown_app()
        except Exception as e:
            logger.error(f"❌ 업데이트 실패: {e}")
            _set(state="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return None


def _manifest_ok(d) -> bool:
    """받은 코드 폴더의 서명된 파일 목록·지문 확인 (시작 프로그램과 같은 규칙)."""
    from core import sigcheck
    return sigcheck.dir_ok(d)


def cleanup_old_downloads():
    """설치가 끝난 이전 업데이트 파일·이전 코드 폴더 정리 (현재 버전 이하, 현재 사용 중 폴더 제외)."""
    try:
        cur = os.environ.get("GYEOL_CODE_DIR", "")
        for d in CODE_ROOT.glob("*"):
            if d.is_dir() and re.fullmatch(r"[\d.]+", d.name) and _ver(d.name) < _ver(APP_VERSION) and str(d) != cur:
                shutil.rmtree(d, ignore_errors=True)
    except Exception:
        pass
    try:
        for p in UPDATE_DIR.glob("Gyeol-Setup-*.exe"):
            m = re.search(r"Setup-([\d.]+)\.exe$", p.name)
            if m and _ver(m.group(1)) <= _ver(APP_VERSION):
                p.unlink(missing_ok=True)
    except Exception:
        pass
