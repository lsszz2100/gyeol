"""라이선스 (core/licensing.py)

- 프로그램을 쓰려면 16자리 라이선스 키가 필요하다. 키 확인은 라이선스 서버가 맡는다.
- 서버 응답은 Ed25519 서명 + 요청마다 새 nonce 로 확인 → 가짜 서버·재전송 응답 차단
- 한 키는 한 번에 PC 한 대. PC 번호(세션)는 Windows 기기 고유값으로 만들어서,
  설치 폴더나 사용자 폴더를 다른 PC로 복사해도 그 PC에서는 다른 번호가 된다.
- 키·확인 결과는 exe 폴더가 아니라 사용자 폴더(%LOCALAPPDATA%\\Gyeol)에 보관
- 서버에 잠시 연결이 안 되면 마지막 확인 결과(서명 포함)를 3일까지 사용
"""
import hashlib
import json
import logging
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from core import ed25519

logger = logging.getLogger("gyeol.license")

COST_PER_DECK = 100     # 슬라이드 1회 생성 (서버 src/index.js 와 같아야 함)
try:        # 서버 주소는 저장소 밖 파일(core/server_local.py)에서 빌드 때 함께 컴파일
    from core.server_local import SERVER
except ImportError:
    SERVER = os.environ.get("GYEOL_LICENSE_SERVER", "")
SERVER_PUBLIC_HEX = "7fc88399cd06cbe8fe189e33370605d452bc96fda32c133dcbbab094f87af63e"
REFRESH_SEC = 30 * 60
OFFLINE_GRACE_SEC = 3 * 86400

_base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
_test_dir = "" if getattr(sys, "frozen", False) else os.environ.get("GYEOL_LICENSE_DIR")   # 설치본에서는 시험용 폴더 지정 불가
LIC_DIR = Path(_test_dir or os.path.join(_base, "Gyeol"))
KEY_FILE = LIC_DIR / "license_key.txt"
CACHE_FILE = LIC_DIR / "license_cache.json"
SALT_FILE = LIC_DIR / "license_id.txt"

_lock = threading.RLock()
_state = {"license": None, "checked_at": 0.0, "error": ""}
_started = False


class LicenseError(RuntimeError):
    pass


def norm_key(key: str) -> str:
    return "".join(ch for ch in str(key or "").upper() if ch.isalnum())


def fmt_key(key: str) -> str:
    k = norm_key(key)
    return " ".join(k[i:i + 4] for i in range(0, len(k), 4))


def _write(path: Path, text: str):
    LIC_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _load_key() -> str:
    return norm_key(_read(KEY_FILE))


def _save_key(key: str):
    if key:
        _write(KEY_FILE, key)
    else:
        KEY_FILE.unlink(missing_ok=True)


# ── PC 번호 ──
def _machine_id() -> str:
    if os.name == "nt":
        try:
            import winreg
            flags = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, flags) as k:
                return str(winreg.QueryValueEx(k, "MachineGuid")[0])
        except Exception:
            pass
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        v = _read(Path(p))
        if v:
            return v
    return "unknown"


def _session() -> str:
    salt = _read(SALT_FILE)
    if len(salt) != 32:
        salt = secrets.token_hex(16)
        try:
            _write(SALT_FILE, salt)
        except Exception:
            pass
    return hashlib.sha256(f"gyeol:{_machine_id()}:{salt}".encode()).hexdigest()[:32]


# ── 서버 호출 ──
def _verify_env(env: dict) -> dict:
    data, sig = env["data"], env["sig"]
    if not ed25519.verify(bytes.fromhex(SERVER_PUBLIC_HEX), data.encode("utf-8"), bytes.fromhex(sig)):
        raise LicenseError("라이선스 서버 응답의 서명이 올바르지 않습니다.")
    return json.loads(data)


def _call(body: dict, timeout: float = 15, path: str = "/v1/check") -> dict:
    nonce = secrets.token_hex(16)
    req = urllib.request.Request(
        SERVER + path, data=json.dumps({**body, "nonce": nonce, "session": _session()}).encode("utf-8"),
        method="POST", headers={"Content-Type": "application/json", "User-Agent": "Gyeol"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        if e.code not in (200, 429):
            raise LicenseError(f"라이선스 서버 오류 (HTTP {e.code})")
    except Exception as e:
        raise ConnectionError(f"라이선스 서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요. ({e})")
    try:
        env = json.loads(raw)
        out = _verify_env(env)
    except LicenseError:
        raise
    except Exception:
        raise LicenseError("라이선스 서버 응답 형식이 올바르지 않습니다.")
    if out.get("nonce") != nonce:
        raise LicenseError("라이선스 서버 응답이 이 요청의 것이 아닙니다.")
    out["_env"] = env
    return out


def _remember(resp: dict):
    lic = resp.get("license")
    if lic is None:
        return
    with _lock:
        _state.update(license=lic, checked_at=float(resp.get("server_time") or time.time()), error="")
    if resp.get("ok"):
        try:
            # 서버 서명이 붙은 원본 그대로 저장 → 파일을 고치면 불러올 때 서명 확인에서 걸림
            _write(CACHE_FILE, json.dumps(resp["_env"]))
        except Exception:
            pass
    else:
        CACHE_FILE.unlink(missing_ok=True)


def _load_cache():
    try:
        out = _verify_env(json.loads(_read(CACHE_FILE)))
        # 이 PC의 번호로 받은 결과만 인정 (다른 PC에서 복사해 온 파일은 무시)
        if out.get("ok") and out.get("session") == _session() and out.get("license"):
            with _lock:
                if not _state["license"]:
                    _state.update(license=out["license"], checked_at=float(out.get("server_time", 0)))
    except Exception:
        pass


def _logout_local(msg: str = ""):
    _save_key("")
    CACHE_FILE.unlink(missing_ok=True)
    with _lock:
        _state.update(license=None, checked_at=0.0, error=msg)


# ── 공개 함수 ──
def activate(key: str) -> dict:
    """키 확인 후 사용 가능하면 저장 (이 PC로 로그인, 다른 PC는 로그아웃)."""
    k = norm_key(key)
    if len(k) != 16:
        raise LicenseError("라이선스 키 16자리를 모두 입력해 주세요.")
    resp = _call({"key": k, "take_over": True})
    if not resp.get("ok"):
        raise LicenseError(resp.get("msg") or "사용할 수 없는 라이선스입니다.")
    _save_key(k)
    _remember(resp)
    logger.info(f"라이선스 확인 완료 (…{k[-4:]})")
    return status()


def logout() -> dict:
    _logout_local("")
    return status()


def refresh(force: bool = False) -> dict:
    """서버에서 최신 상태 확인. 연결 실패 시 마지막 결과 유지."""
    key = _load_key()
    if not key:
        return status()
    with _lock:
        fresh = _state["license"] and time.time() - _state["checked_at"] < REFRESH_SEC
    if fresh and not force:
        return status()
    try:
        resp = _call({"key": key})
        if resp.get("code") in ("invalid", "session_moved"):
            _logout_local(resp.get("msg") or "라이선스를 다시 입력해 주세요.")
            logger.warning(f"라이선스 로그아웃: {resp.get('msg')}")
            return status()
        _remember(resp)
        if not resp.get("ok"):
            with _lock:
                _state["error"] = resp.get("msg") or ""
    except (ConnectionError, LicenseError) as e:
        with _lock:
            _state["error"] = str(e)
    return status()


def status() -> dict:
    key = _load_key()
    with _lock:
        lic = _state["license"]
        age = time.time() - _state["checked_at"]
        err = _state["error"]
    usable = bool(key and lic and lic.get("usable") and age < OFFLINE_GRACE_SEC)
    if lic and lic.get("expires_at") and lic["expires_at"] <= time.time():
        usable = False
    days_left = None
    if lic and lic.get("expires_at"):
        days_left = max(0, int((lic["expires_at"] - time.time()) // 86400))
    return {"has_key": bool(key), "key_hint": f"…{key[-4:]}" if key else "", "usable": usable,
            "error": err, "license": lic, "days_left": days_left, "cost_per_deck": COST_PER_DECK}


def is_usable() -> bool:
    return status()["usable"]


def reserve() -> str:
    """생성 시작 전 서버에서 토큰 선차감. 저장된 결과로는 통과할 수 없고 서버의 서명된 승인이 있어야 한다."""
    key = _load_key()
    if not key:
        raise LicenseError("라이선스 키를 먼저 입력해 주세요.")
    rid = secrets.token_hex(16)
    try:
        resp = _call({"key": key, "request_id": rid}, path="/v1/reserve")
    except ConnectionError:
        raise LicenseError("라이선스 서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요.")
    if resp.get("code") in ("invalid", "session_moved"):
        _logout_local(resp.get("msg") or "라이선스를 다시 입력해 주세요.")
    else:
        _remember(resp)
    if not resp.get("ok"):
        raise LicenseError(resp.get("msg") or "라이선스를 확인할 수 없습니다.")
    return rid


def refund(request_id: str):
    """생성이 실패하면 선차감한 토큰 환불 (1시간 이내, 하루 5회까지)."""
    if not request_id:
        return
    try:
        resp = _call({"key": _load_key(), "request_id": request_id}, path="/v1/refund")
        _remember(resp)
        logger.info("토큰을 돌려받았습니다." if resp.get("ok") else f"토큰 환불 불가: {resp.get('msg')}")
    except Exception as e:
        logger.warning(f"토큰 환불 실패: {e}")


def start_background():
    """시작 시 캐시 불러오기 + 30분마다 상태 확인."""
    global _started
    if _started:
        return
    _started = True
    _load_cache()

    def loop():
        while True:
            try:
                refresh(force=True)
            except Exception:
                pass
            time.sleep(REFRESH_SEC)
    threading.Thread(target=loop, daemon=True, name="license").start()
