"""설치형 EXE 시작점 (launcher.py) — 기반(런타임)에 고정되는 유일한 코드

- 기반: Python·라이브러리 (설치 프로그램으로만 교체)
- 프로그램: 코드(*.pyc)와 화면(static) 묶음. 설치본은 _internal\\appcode, 업데이트본은
  %LOCALAPPDATA%\\Gyeol\\appcode\\<버전> 에 두고, 서명이 맞으면 더 새 버전을 불러온다.
라이브러리·표준 모듈은 코드가 밖에 있어 자동으로 묶이지 않으므로 아래 _deps 에 적어 빌드에 포함시킨다.
"""
import hashlib
import json
import multiprocessing
import os
import re
import shutil
import sys
import time
from pathlib import Path

# ── 위조 방지: 코드 폴더의 파일 목록(manifest.json)이 개발자 서명과 맞고, 모든 파일 지문이 같아야 실행 ──
# (확인 코드는 바꿔치기할 수 있는 코드 폴더가 아니라 실행 파일 안에 있음)
_PUB = bytes.fromhex("568e930a87cf5af8e8e223fa8eb80c910e2b3cc91f7f8a3575b304a9f1ed95ce")
_p = 2 ** 255 - 19
_q = 2 ** 252 + 27742317777372353535851937790883648493
_d = -121665 * pow(121666, _p - 2, _p) % _p
_I = pow(2, (_p - 1) // 4, _p)


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F, G * H, F * G, E * H)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _xr(y, sign):
    if y >= _p:
        return None
    x2 = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p:
        x = x * _I % _p
    if (x * x - x2) % _p:
        return None
    return _p - x if (x & 1) != sign else x


def _pt(b):
    y = int.from_bytes(b, "little")
    s, y = y >> 255, y & ((1 << 255) - 1)
    x = _xr(y, s)
    return None if x is None else (x, y, 1, x * y % _p)


_gy = 4 * pow(5, _p - 2, _p) % _p
_G = (_xr(_gy, 0), _gy, 1, _xr(_gy, 0) * _gy % _p)


def _verify(msg: bytes, sig: bytes) -> bool:
    if len(sig) != 64:
        return False
    A, R = _pt(_PUB), _pt(sig[:32])
    s = int.from_bytes(sig[32:], "little")
    if not A or not R or s >= _q:
        return False
    h = int.from_bytes(hashlib.sha512(sig[:32] + _PUB + msg).digest(), "little") % _q
    P, Q = _mul(s, _G), _add(R, _mul(h, A))
    return (P[0] * Q[2] - Q[0] * P[2]) % _p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % _p == 0


def _intact(d: Path) -> bool:
    """서명된 파일 목록과 실제 파일이 정확히 같은지 (바뀐 파일·빠진 파일·모르는 파일 모두 거부)."""
    try:
        data = (d / "manifest.json").read_bytes()
        if not _verify(data, bytes.fromhex((d / "manifest.sig").read_text(encoding="ascii").strip())):
            return False
        files = json.loads(data)["files"]
        for cache in list(d.rglob("__pycache__")):
            shutil.rmtree(cache, ignore_errors=True)
        present = sorted(p.relative_to(d).as_posix() for p in d.rglob("*")
                         if p.is_file() and p.name not in ("manifest.json", "manifest.sig"))
        if present != sorted(files):
            return False
        return all(hashlib.sha256((d / n).read_bytes()).hexdigest() == h for n, h in files.items())
    except Exception:
        return False


def _fail(msg: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, msg, "결 GYEOL", 0x10 | 0x40000)
    except Exception:
        print(msg)
    sys.exit(1)


def _ver(text: str):
    m = re.search(r'APP_VERSION\s*=\s*"([\d.]+)"', text or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)


def _user_code_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Gyeol" / "appcode"


def _bad_list() -> set:
    """시작하다 실패한 코드 업데이트 목록 (이 목록의 버전은 건너뛰고 설치된 기본 코드로 실행)."""
    return set(_read(_user_code_root() / "bad.txt").split())


def _code_dir() -> Path:
    bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "appcode"
    if not _intact(bundled):
        _fail("프로그램 파일이 손상되었거나 변조되었습니다.\n프로그램을 다시 설치해 주세요.")
    best, best_ver = bundled, _ver(_read(bundled / "version.py"))
    user = _user_code_root()
    try:
        name = (user / "current.txt").read_text(encoding="utf-8").strip()
        cand = user / name
        cand_ver = _ver(_read(cand / "version.py"))
        # 설치 프로그램으로 더 새 기본본이 깔리면 그쪽을 사용 (오래된 코드 업데이트가 덮어쓰지 않게)
        # 받아 둔 코드 업데이트도 서명·지문이 맞을 때만 사용 (아니면 설치된 기본 코드로 실행)
        if cand_ver > best_ver and name not in _bad_list() and _intact(cand):
            best = cand
    except Exception:
        pass
    return best


def _mark_bad_and_restart(code: Path, err: BaseException):
    """받아 둔 코드 업데이트가 시작조차 못 하면 그 버전을 '실패'로 적고 설치된 기본 코드로 다시 시작."""
    import traceback
    root = _user_code_root()
    try:
        bad = _bad_list() | {code.name}
        (root / "bad.txt").write_text("\n".join(sorted(bad)), encoding="utf-8")
        (root / "launcher_error.txt").write_text(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} {code.name}\n" + "".join(traceback.format_exception(err)), encoding="utf-8")
    except Exception:
        _fail("프로그램 업데이트 파일을 불러오지 못했습니다.\n프로그램을 다시 설치해 주세요.")
    import subprocess
    args = [a for a in sys.argv[1:]]
    if "--wait-pid" in args:
        i = args.index("--wait-pid")
        del args[i:i + 2]
    exe = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.abspath(__file__)]
    subprocess.Popen(exe + args + ["--wait-pid", str(os.getpid())], close_fds=True)
    sys.exit(0)


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _wait_previous(argv):
    """코드 업데이트 후 재시작: 이전 프로세스가 완전히 종료될 때까지 대기 (--wait-pid <pid>)."""
    if "--wait-pid" not in argv:
        return
    try:
        pid = int(argv[argv.index("--wait-pid") + 1])
    except Exception:
        return
    import ctypes
    SYNCHRONIZE = 0x00100000
    h = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if h:
        ctypes.windll.kernel32.WaitForSingleObject(h, 20000)
        ctypes.windll.kernel32.CloseHandle(h)
    time.sleep(0.5)


def _setup_log():
    """콘솔 없는 exe는 sys.stderr 가 None 이라 기록하는 코드가 멈출 수 있다 → 로그 파일로 (문의 때 원인 확인용)."""
    if sys.stderr is not None and sys.stdout is not None:
        return
    try:
        root = _user_code_root().parent
        root.mkdir(parents=True, exist_ok=True)
        log = root / "app.log"
        if log.exists() and log.stat().st_size > 2_000_000:
            log.replace(root / "app.old.log")
        f = open(log, "a", encoding="utf-8", buffering=1)
    except Exception:
        f = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = sys.stdout or f
    sys.stderr = sys.stderr or f


def main():
    multiprocessing.freeze_support()   # 하위 프로세스가 프로그램 전체를 다시 띄우지 않게
    _setup_log()
    _wait_previous(sys.argv)
    sys.dont_write_bytecode = True   # 코드 폴더에 캐시 파일을 만들지 않음 (위조 확인 대상 밖의 파일 방지)
    code = _code_dir()
    sys.path.insert(0, str(code))
    os.environ["GYEOL_CODE_DIR"] = str(code)
    bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "appcode"
    try:
        import app
    except Exception as e:
        if code == bundled:
            raise
        _mark_bad_and_restart(code, e)
    app.main()


def _deps():
    """빌드 때만 읽힌다 (실행되지 않음). 코드 업데이트가 새 표준 모듈을 써도 되도록 넉넉히 포함."""
    import argparse, asyncio, base64, bisect, calendar, codecs, collections, concurrent.futures, contextlib, copy
    import csv, ctypes, dataclasses, datetime, decimal, difflib, email, encodings, enum, fnmatch, fractions
    import functools, getpass, glob, gzip, hmac, html, html.parser, http.client, http.cookies, http.server
    import inspect, io, itertools, locale, logging.handlers, math, mimetypes, operator, pickle, platform, queue
    import random, secrets, shlex, signal, socket, socketserver, sqlite3, ssl, statistics, string, struct
    import subprocess, tempfile, textwrap, threading, tkinter, tkinter.filedialog, traceback, typing, unicodedata
    import urllib.error, urllib.parse, urllib.request, uuid, webbrowser, winreg, xml.dom.minidom, xml.etree.ElementTree
    import zipfile, zlib
    import fitz, pymupdf, playwright.sync_api, pptx, PIL.Image, PIL.ImageDraw, PIL.ImageFilter, webview
    import pystray, pystray._win32


if __name__ == "__main__":
    main()
