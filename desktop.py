"""
결(GYEOL) - 데스크톱 프로그램 실행 모듈 (desktop.py)
웹 브라우저 탭 대신 주소창/메뉴바가 전혀 없는 독립된 데스크톱 프로그램 창(WebView2 / Edge App Mode)으로 구동합니다.
"""

import os
import json
import time
import socket
import logging
import threading
import subprocess
import urllib.request
from pathlib import Path

logger = logging.getLogger("kdesign.desktop")

APP_TITLE = "결 GYEOL · AI 프레젠테이션"
APP_SIGNATURE = "Gyeol"
BASE_DIR = Path(__file__).parent.resolve()
from config import DATA_DIR as _DATA_DIR
DATA_DIR = Path(_DATA_DIR)
INSTANCE_FILE = DATA_DIR / "instance.json"
ICON_FILE = BASE_DIR / "static" / "img" / "app.ico"


def pick_port(preferred: int = 9090) -> int:
    """사용 가능한 포트를 선택합니다."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return 9090


def find_running_instance():
    """이미 실행 중인 결(GYEOL) 인스턴스가 있는지 확인합니다."""
    if not INSTANCE_FILE.exists():
        return None
    try:
        data = json.loads(INSTANCE_FILE.read_text(encoding="utf-8"))
        port = int(data.get("port", 0))
        if not port:
            return None
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/ping", headers={"Host": f"127.0.0.1:{port}"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("app") == APP_SIGNATURE:
                return port
    except Exception:
        pass
    return None


def activate_instance(port: int) -> bool:
    """이미 실행 중인 프로그램의 창을 앞으로 가져옵니다."""
    try:
        token = json.loads(INSTANCE_FILE.read_text(encoding="utf-8")).get("token", "")
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/focus", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json", "X-Gyeol-Token": token})
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


def write_instance(port: int, token: str = ""):
    """현재 실행 포트와 PID를 기록합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INSTANCE_FILE.write_text(
        json.dumps({"port": port, "pid": os.getpid(), "app": APP_SIGNATURE, "token": token}),
        encoding="utf-8"
    )


def clear_instance():
    """인스턴스 파일을 정리합니다."""
    try:
        if INSTANCE_FILE.exists():
            data = json.loads(INSTANCE_FILE.read_text(encoding="utf-8"))
            if data.get("pid") == os.getpid():
                INSTANCE_FILE.unlink()
    except Exception:
        pass


def launch_edge_app_mode(url: str, title: str = APP_TITLE):
    """
    Windows 10/11에 기본 내장된 Microsoft Edge를 '앱 모드(--app)'로 실행합니다.
    주소창, 탭, 북마크바 없이 순수 독립 데스크톱 프로그램 창 형태로 구동됩니다.
    """
    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        "msedge.exe",
    ]
    
    # 크롬 폴백
    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        "chrome.exe",
    ]

    for exe in edge_paths + chrome_paths:
        try:
            cmd = f'start "" "{exe}" --app="{url}" --window-size=1440,920 --window-position=center'
            subprocess.Popen(cmd, shell=True)
            logger.info(f"독립 프로그램 창(App Mode) 구동 성공: {exe}")
            return True
        except Exception:
            continue

    return False


def _set_windows_app_id():
    """작업 표시줄에 파이썬 아이콘 대신 프로그램 아이콘이 뜨도록 앱 ID를 지정합니다."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Gyeol.AIPresentation")
    except Exception:
        pass


def _apply_window_icon(title: str):
    """창 왼쪽 위/작업 표시줄 아이콘을 결 로고로 바꿉니다 (Windows)."""
    if os.name != "nt" or not ICON_FILE.exists():
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        hwnd = None
        for _ in range(50):
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                break
            time.sleep(0.1)
        if not hwnd:
            return
        IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x80
        big = user32.LoadImageW(None, str(ICON_FILE), IMAGE_ICON, 256, 256, LR_LOADFROMFILE)
        small = user32.LoadImageW(None, str(ICON_FILE), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if big:
            user32.SendMessageW(hwnd, WM_SETICON, 1, big)
        if small:
            user32.SendMessageW(hwnd, WM_SETICON, 0, small)
    except Exception as e:
        logger.info(f"창 아이콘 설정 실패: {e}")


# ── 프로그램 창 · 트레이 ──
_window = None
_tray = None
_is_busy = lambda: False
_skip_confirm = lambda: False   # '다음부터 묻지 않기'를 골랐는지 (작업 중일 때는 상관없이 항상 묻는다)
_allow_close = False
_auto_quit = False
_quit_thread = None


def is_auto_quit() -> bool:
    return _auto_quit


def focus_window():
    """창을 앞으로 (트레이에 숨어 있었다면 다시 표시하고 자동 종료는 취소)."""
    global _auto_quit
    _auto_quit = False
    stop_tray()
    if _window:
        try:
            _window.restore()
            _window.show()
            _window.on_top = True
            _window.on_top = False
        except Exception:
            pass


def stop_tray():
    global _tray
    icon, _tray = _tray, None
    if icon:
        try:
            icon.stop()
        except Exception:
            pass


def quit_window():
    """바로 종료."""
    global _allow_close, _auto_quit
    _allow_close, _auto_quit = True, False
    stop_tray()
    try:
        _window.destroy()
    except Exception:
        clear_instance()
        os._exit(0)


def _on_closing():
    """X 버튼: 종료 확인 창을 화면 안에 띄운다. 작업이 없고 '묻지 않기'를 골랐으면 바로 닫는다."""
    if _allow_close:
        return True
    try:
        if not _is_busy() and _skip_confirm():
            return True
    except Exception:
        pass
    threading.Thread(target=_ask_close, daemon=True).start()
    return False


def _ask_close():
    try:
        _window.evaluate_js("window.openCloseDialog && window.openCloseDialog()")
    except Exception as e:
        logger.warning(f"종료 창 표시 실패: {e}")


def hide_to_tray() -> bool:
    """창을 숨기고 트레이 아이콘 표시. 진행 중인 작업이 끝나면 자동 종료."""
    global _tray, _auto_quit
    try:
        import pystray
        from PIL import Image
        image = Image.open(ICON_FILE)
    except Exception as e:
        logger.warning(f"트레이 아이콘을 쓸 수 없습니다: {e}")
        return False
    _auto_quit = True
    _tray = pystray.Icon(APP_SIGNATURE, image, "결 GYEOL - 작업 진행 중 (끝나면 자동 종료)", menu=pystray.Menu(
        pystray.MenuItem("창 열기", lambda: focus_window(), default=True),
        pystray.MenuItem("지금 종료 (작업 중단)", lambda: quit_window()),
    ))
    _tray.run_detached()
    try:
        _window.hide()
    except Exception:
        pass
    _start_idle_watch()
    return True


def _start_idle_watch():
    global _quit_thread
    if _quit_thread and _quit_thread.is_alive():
        return
    _quit_thread = threading.Thread(target=_quit_when_idle, daemon=True)
    _quit_thread.start()


def schedule_quit_when_idle():
    """창은 그대로 둔 채, 진행 중인 작업이 모두 끝나면 자동 종료한다."""
    global _auto_quit
    _auto_quit = True
    _start_idle_watch()


def cancel_auto_quit():
    global _auto_quit
    _auto_quit = False


def _quit_when_idle():
    idle_count = 0
    while _auto_quit:
        idle_count = idle_count + 1 if not _is_busy() else 0
        if idle_count >= 2:   # 작업 사이의 짧은 틈에 꺼지지 않도록 2번 연속 한가할 때만
            try:
                if _tray:
                    _tray.notify("작업이 끝나 프로그램을 종료합니다.", "결 GYEOL")
            except Exception:
                pass
            time.sleep(2)
            if _auto_quit and not _is_busy():
                quit_window()
                return
            idle_count = 0
        time.sleep(2)


def run_desktop_window(url: str, is_busy=None, skip_confirm=None) -> str:
    """1순위 pywebview 창 ('window' 반환, 창을 닫으면 돌아옴) / 2순위 Edge 앱 모드 / 3순위 기본 브라우저."""
    global _window, _is_busy, _skip_confirm
    if is_busy:
        _is_busy = is_busy
    if skip_confirm:
        _skip_confirm = skip_confirm
    try:
        import webview
        _window = webview.create_window(title=APP_TITLE, url=url, width=1440, height=920, min_size=(1024, 680),
                                        text_select=True, confirm_close=False)
        storage_path = str(DATA_DIR / "webview")
        try:
            from core import save_dialog
            save_dialog.WINDOW = _window  # 저장 위치 선택 창에 사용
        except Exception:
            pass
        _set_windows_app_id()
        _window.events.closing += _on_closing
        _window.events.shown += lambda: threading.Thread(target=_apply_window_icon, args=(APP_TITLE,), daemon=True).start()
        webview.start(gui="edgechromium", private_mode=False, storage_path=storage_path, icon=str(ICON_FILE))
        return "window"
    except Exception as e:
        _window = None
        logger.info(f"프로그램 창을 열지 못했습니다({e}). 앱 모드로 전환합니다.")
    if os.name == "nt" and launch_edge_app_mode(url):
        return "app"
    import webbrowser
    webbrowser.open(url)
    return "browser"
