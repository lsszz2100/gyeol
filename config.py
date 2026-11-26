"""
결(GYEOL) - 설정 및 프로젝트 영구 보관 매니저
"""

import json
import os
import sys
import threading
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 실행 파일(Gyeol.exe)로 묶였을 때는 프로그램 내부 폴더가 아니라 exe 옆 data 폴더에 저장한다
if getattr(sys, "frozen", False):
    DATA_DIR = os.path.join(os.path.dirname(sys.executable), "data")
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

os.makedirs(DATA_DIR, exist_ok=True)

def _read_edition() -> str:
    """personal(기본) | retail(판매판). 환경변수 GYEOL_EDITION 또는 프로그램 폴더의 edition.json {"edition":"retail"}.
    판매판은 구독 로그인(CLI) AI를 막고 API 키 방식만 쓴다 (구독 계정을 판매 제품에 연결하는 것은 각사 정책상 불가)."""
    v = os.environ.get("GYEOL_EDITION", "").strip().lower()
    if not v:
        for d in {BASE_DIR, os.path.dirname(sys.executable)}:
            try:
                with open(os.path.join(d, "edition.json"), encoding="utf-8") as f:
                    v = str(json.load(f).get("edition", "")).strip().lower()
                break
            except Exception:
                continue
    return "retail" if v == "retail" else "personal"


EDITION = _read_edition()
IS_RETAIL = EDITION == "retail"

DEFAULT_CONFIG = {
    "provider": "gemini",
    "gemini_api_key": "",
    "gemini_model": "gemini-3.5-flash",
    "openai_api_key": "",
    "openai_model": "gpt-4o",
    "default_theme": "pitch-deck-vc",
    "default_font": "pretendard",
    "app_title": "결 GYEOL",
}


_IO_LOCK = threading.RLock()


def _write_json_atomic(path: str, data) -> None:
    """임시 파일에 다 쓴 뒤 바꿔치기한다. 쓰는 도중 꺼져도 기존 파일이 깨지지 않는다 (프로젝트 기록 전체가 사라지는 사고 방지)."""
    tmp = f"{path}.{os.getpid()}.tmp"
    with _IO_LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)


def load_config() -> Dict[str, Any]:
    """설정을 로드합니다."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = DEFAULT_CONFIG.copy()
                merged.update(data)
                gm = str(merged.get("gemini_model") or "")
                if not gm.startswith(("gemini-3.5", "gemini-3.6", "gemini-3.7", "gemini-3.8", "gemini-3.9", "gemini-4")):
                    merged["gemini_model"] = "gemini-3.5-flash"   # 무료 키는 3.5 이상만 (2.5 등 예전 저장값 교체)
                return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: Dict[str, Any]) -> None:
    """설정을 저장합니다."""
    _write_json_atomic(CONFIG_FILE, cfg)


def load_history() -> List[Dict[str, Any]]:
    """저장된 프로젝트 이력을 반환합니다. 파일이 깨져 있으면 .broken 으로 따로 보관하고 빈 목록으로 시작합니다."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            try:
                os.replace(HISTORY_FILE, HISTORY_FILE + ".broken")   # 다음 저장이 깨진 파일을 덮어써 흔적이 사라지지 않게
            except OSError:
                pass
    return []


def save_history(history: List[Dict[str, Any]]) -> None:
    _write_json_atomic(HISTORY_FILE, history)


def add_project_history(project: Dict[str, Any]) -> None:
    """새 프로젝트를 이력 최상단에 추가합니다."""
    with _IO_LOCK:
        history = load_history()
        # 중복 ID가 있으면 제거 후 추가
        history = [p for p in history if p.get("id") != project.get("id")]
        history.insert(0, project)
        # 최대 50개 유지
        save_history(history[:50])
