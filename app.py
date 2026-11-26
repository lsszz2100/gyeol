#!/usr/bin/env python3
"""
결(GYEOL) - 한국어 AI 프레젠테이션 제작 프로그램 메인 서버
"""

import json
import logging
import mimetypes
import os
import hashlib
import hmac
import re
import secrets
import sys
import threading
import time
import urllib.parse
from concurrent.futures import as_completed
from http.cookies import SimpleCookie
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime

from config import load_config, save_config, load_history, save_history, add_project_history
from core.template_compiler import (
    canon_theme,
    AVAILABLE_THEMES,
    AVAILABLE_FONTS,
    THEME_IDS,
    compile_slide_deck,
)
from core.korean_presets import get_all_presets, get_preset_by_id
from ai_engine import resolve_opts, mood_styles, generate_presentation_slides, rewrite_slide, to_english, AIGenerationError, DEFAULT_OPTS, ocr_images, summarize_chunk
import desktop
import config as config_mod
from core import cli_llm
CLI_PROVIDERS = tuple(cli_llm.PROVIDERS)
from core import exporter, save_dialog, slide_ops, media, licensing, updater, sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kdesign.server")

# 라이선스 없이도 되는 요청 (설정·라이선스 입력). 나머지 POST(생성·편집·내보내기 등)는 라이선스 필요
LICENSE_FREE = {"/api/license_activate", "/api/license_logout", "/api/update/check", "/api/update/install",
                "/api/update/ack", "/api/focus", "/api/app/close"}
# 라이선스 없이 볼 수 있는 화면: 라이선스 입력 화면을 그리는 데 필요한 것만 (프로젝트·설정·사진·미리보기는 전부 차단)
LICENSE_FREE_GET = {"/", "/index.html", "/favicon.ico", "/api/ping", "/api/license", "/api/update/status", "/api/busy"}
# 이 프로그램의 창만 접속할 수 있게 실행마다 새로 만드는 비밀값 (쿠키). 없으면 다른 웹사이트가 이 PC의 서버에서
# API 키·프로젝트를 읽어 갈 수 있다
API_TOKEN = secrets.token_urlsafe(32)
TOKEN_COOKIE = "gyeol_session"
ALLOWED_HOSTS = set()
FONT_IDS = {f["id"] for f in AVAILABLE_FONTS}
# /api/config 로 화면이 저장할 수 있는 설정 항목
CLIENT_CFG_KEYS = {"provider", "gemini_api_key", "gemini_model", "openai_api_key", "openai_model", "pixabay_api_key",
                   "default_theme", "default_font", "welcome_done"}
# 첨부 자료 파일 1개 20MB (base64) + 여유
MAX_BODY = 32 * 1024 * 1024
# 라이선스 검사 생략은 어떤 환경 변수·설정으로도 켤 수 없다 (설치본에서 코드를 꺼내 실행해도 마찬가지).
# 자동 시험(packaging/smoke_test.py, tools/)만 시험 프로세스 안에서 이 값을 직접 바꾼다.
LICENSE_BYPASS = False


def _license_view(force: bool = False) -> dict:
    licensing.start_background()
    st = licensing.refresh(force=force)
    if LICENSE_BYPASS:
        st = dict(st, usable=True, dev_bypass=True)
    return st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

THEME_SAMPLE = """<section class="slide" data-title="미리보기">
  <span class="kicker">2026 · 결 디자인 테마</span>
  <h1 class="h1 mt-s">생각에 결을 더하는<br><span class="gradient-text">프레젠테이션</span></h1>
  <div class="grid g3 mt-l">
    <div class="card"><div style="font-size:52px;font-weight:800">72%</div><p class="dim">핵심 지표</p></div>
    <div class="card"><div style="font-size:52px;font-weight:800">3.4배</div><p class="dim">성장률</p></div>
    <div class="card"><div style="font-size:52px;font-weight:800">1위</div><p class="dim">시장 점유</p></div>
  </div>
</section>"""


def _initial_project():
    """최근 작업을 이어서 열고, 없으면 샘플을 보여줍니다."""
    hist = load_history()
    if hist:
        p = hist[0]
        return {"id": p.get("id"), "title": p.get("title", "새 프레젠테이션"), "theme": canon_theme(p.get("theme", "")),
                "font": p.get("font", "theme"), "slides_html": p.get("slides_html", ""),
                "display": p.get("display") or {}, "updated_at": datetime.now().isoformat()}
    return {"id": "sample", "title": "샘플 프레젠테이션", "theme": "pitch-deck-vc", "font": "theme",
            "slides_html": get_preset_by_id("pitch-deck")["sample_html"], "display": {},
            "updated_at": datetime.now().isoformat()}


# 현재 메모리 상의 활성 프로젝트
ACTIVE_PROJECT = _initial_project()
# 슬라이드 편집 되돌리기용 (프로젝트를 바꾸면 비운다)
UNDO = []
UNDO_MAX = 40


def _persist_active():
    """테마/폰트/제목 변경을 저장된 프로젝트에도 반영합니다."""
    hist = load_history()
    for h in hist:
        if h.get("id") == ACTIVE_PROJECT.get("id"):
            h.update({k: ACTIVE_PROJECT.get(k) for k in ("title", "theme", "font", "display", "slides_html")})
            save_history(hist)
            break
    else:
        # 샘플처럼 목록에 없던 프로젝트를 고치면 새 프로젝트로 저장한다
        if ACTIVE_PROJECT.get("slides_html"):
            if ACTIVE_PROJECT.get("id") in (None, "", "sample"):
                ACTIVE_PROJECT["id"] = f"proj-{int(datetime.now().timestamp())}"
            add_project_history({
                "id": ACTIVE_PROJECT["id"], "title": ACTIVE_PROJECT.get("title", ""), "prompt": "",
                "theme": ACTIVE_PROJECT.get("theme"), "font": ACTIVE_PROJECT.get("font"),
                "display": ACTIVE_PROJECT.get("display") or {}, "preset_id": "pitch-deck",
                "slides_html": ACTIVE_PROJECT["slides_html"], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })


# 생성 뒤 사진을 하나씩 채워 넣는 작업 상태 (화면이 /api/photo_status로 확인)
PHOTO_STATE = {"pid": "", "pending": 0, "rev": 0}
PHOTO_LOCK = threading.Lock()


def _fill_photos(pid: str, jobs: dict):
    """미리 시작한 사진 찾기가 끝나는 대로 해당 슬라이드에 사진을 넣고 저장한다."""
    fut_q = {f: q for q, f in jobs.items()}

    def put(q, url):
        with PHOTO_LOCK:
            if ACTIVE_PROJECT.get("id") == pid:
                ACTIVE_PROJECT["slides_html"] = media.apply_photo(ACTIVE_PROJECT.get("slides_html", ""), q, url)
                for i, (h, ix) in enumerate(UNDO):  # 되돌리기해도 사진이 사라지지 않게
                    UNDO[i] = (media.apply_photo(h, q, url), ix)
                _persist_active()
            else:  # 그 사이 다른 프로젝트를 열었으면 저장된 쪽만 고친다
                hist = load_history()
                for h in hist:
                    if h.get("id") == pid:
                        h["slides_html"] = media.apply_photo(h.get("slides_html", ""), q, url)
                        save_history(hist)
                        break
            PHOTO_STATE["pending"] = max(0, PHOTO_STATE["pending"] - 1)
            PHOTO_STATE["rev"] += 1

    done = set()
    try:
        for f in as_completed(fut_q, timeout=240):
            q = fut_q[f]
            done.add(q)
            try:
                url = f.result()
            except Exception:
                url = ""
            logger.info(f"사진 {'넣음' if url else '못 찾음'}: {q}")
            put(q, url)
    except Exception:
        logger.warning("사진 채우기 시간 초과, 남은 사진 표시는 지웁니다.")
    for q in jobs:
        if q not in done:
            put(q, "")


def _ai_cfg():
    cfg = load_config()
    media.set_pixabay_key(cfg.get("pixabay_api_key", ""))
    provider = cfg.get("provider", "gemini")
    if provider in CLI_PROVIDERS and config_mod.IS_RETAIL:
        provider = "gemini"   # 판매판은 구독 로그인(CLI)을 쓰지 않는다
    media.set_vision_key(cfg.get("gemini_api_key", ""))
    if provider in CLI_PROVIDERS:
        key, model = "", ""   # 구독 로그인: 키 없음 (각 CLI가 로그인 정보를 관리)
    else:
        key = cfg.get("gemini_api_key") if provider == "gemini" else cfg.get("openai_api_key")
        model = cfg.get("gemini_model") if provider == "gemini" else cfg.get("openai_model")
    return cfg, provider, key, model


def _gemini_aux():
    """사진 판별·글자 읽기·검수처럼 Gemini 비전이 필요한 보조 기능용 (글쓰기 AI가 구독 로그인이어도 Gemini 키가 있으면 쓴다)."""
    cfg = load_config()
    return cfg.get("gemini_api_key", ""), cfg.get("gemini_model", "")


def _media_api(path: str, req: dict) -> dict:
    try:
        if path == "/api/media_upload":
            return {"ok": True, "url": media.save_data_url(req.get("data_url", ""))}
        if path == "/api/media_fetch":
            return {"ok": True, "url": media.fetch_url(req.get("url", ""))}
        cfg, provider, key, model = _ai_cfg()
        if path == "/api/photo_search":
            gk, gm = _gemini_aux()
            q = req.get("q", "") if media.PIXABAY_KEY[0] else to_english(req.get("q", ""), "gemini", gk, gm)
            q, items = media.search_photos_smart(q, 30)
            msg = ""
            if not items:
                msg = ("검색어를 영어로 바꾸지 못했습니다. 영어로 검색해 보세요. (예: meeting room)"
                       if re.search(r"[가-힣]", q) else "검색 결과가 없습니다. 다른 단어로 찾아 보세요.")
            return {"ok": True, "query": q, "items": items, "message": msg}
        if path == "/api/ai_image":
            prompt = (req.get("prompt") or "").strip()
            if not prompt:
                return {"ok": False, "message": "어떤 그림을 만들지 적어 주세요."}
            gk2, gm2 = _gemini_aux()
            eng = to_english(prompt, "gemini", gk2, gm2)
            gkey = cfg.get("gemini_api_key", "")
            maker = None
            # 개인판에서 AI 엔진을 'ChatGPT 구독'으로 쓰고 있으면 그 구독의 이미지 생성으로 먼저 그린다(1~2분)
            if cfg.get("provider") == "codex_cli" and not config_mod.IS_RETAIL and cli_llm.status("codex_cli").get("logged_in"):
                maker = cli_llm.generate_image
            return {"ok": True, "url": media.ai_image(eng, gkey, req.get("style", "photo"), maker=maker),
                    "by": "chatgpt" if maker else ""}
    except media.MediaError as e:
        return {"ok": False, "message": str(e)}
    except Exception as e:
        logger.exception("그림 처리 오류")
        return {"ok": False, "message": f"그림을 처리하지 못했습니다: {e}"}
    return {"ok": False, "message": "알 수 없는 요청입니다."}


def _slide_op(req: dict) -> dict:
    """op: replace | notes | delete | duplicate | move | ai_edit | ai_insert | undo"""
    op = req.get("op")
    slides = slide_ops.split_slides(ACTIVE_PROJECT.get("slides_html", ""))
    try:
        idx = int(req.get("idx", 0))
    except (TypeError, ValueError):
        idx = 0
    if op == "undo":
        if not UNDO:
            return {"ok": False, "message": "더 되돌릴 작업이 없습니다."}
        prev_html, prev_idx = UNDO.pop()
        ACTIVE_PROJECT["slides_html"] = prev_html
        ACTIVE_PROJECT["updated_at"] = datetime.now().isoformat()
        _persist_active()
        return {"ok": True, "project": ACTIVE_PROJECT, "idx": prev_idx, "message": "되돌렸습니다.", "can_undo": bool(UNDO)}
    if not slides or not (0 <= idx < len(slides)):
        return {"ok": False, "message": "슬라이드를 찾을 수 없습니다. 화면을 새로 고쳐 주세요."}

    new_idx, msg, reply = idx, "", ""
    try:
        if op == "replace":
            slides[idx] = slide_ops.sanitize_section(req.get("html", ""))
            msg = "수정 내용을 저장했습니다."
        elif op == "add_obj":
            obj = req.get("html", "")
            if not re.match(r'\s*<div class="g-obj[ "]', obj):
                return {"ok": False, "message": "넣을 개체 형식이 올바르지 않습니다."}
            sec = slides[idx]
            m = re.search(r"\s*<aside\b[^>]*class=\"[^\"]*notes", sec)
            pos = m.start() if m else sec.rstrip().rfind("</section>")
            slides[idx] = slide_ops.sanitize_section(sec[:pos] + "\n  " + obj.strip() + sec[pos:])
            msg = "넣었습니다. 끌어서 위치와 크기를 맞춰 보세요."
        elif op == "set_photo":
            url = req.get("url", "")
            if url and not (re.fullmatch(r"/media/[0-9a-f]{20}\.(jpg|png|webp|gif|svg)", url) and media.media_path(url[len("/media/"):])):
                return {"ok": False, "message": "사진 파일을 찾을 수 없습니다."}
            sec = re.sub(r'\s*<figure class="g-photo">.*?</figure>', "", slides[idx], flags=re.S)
            sec = re.sub(r'(<section\b[^>]*class=")([^"]*)"', lambda mm: mm.group(1) + re.sub(r"\s*\bwith-photo\b", "", mm.group(2)) + '"', sec, count=1)
            if url:
                sec = re.sub(r'(<section\b[^>]*class=")([^"]*)"', lambda mm: f'{mm.group(1)}{mm.group(2)} with-photo"', sec, count=1)
                sec = re.sub(r"(<section\b[^>]*>)", lambda mm: mm.group(1) + f'\n  <figure class="g-photo"><img src="{url}" alt=""></figure>', sec, count=1)
            slides[idx] = slide_ops.sanitize_section(sec)
            msg = "사진을 넣었습니다." if url else "사진을 뺐습니다."
        elif op == "notes":
            slides[idx] = slide_ops.set_notes(slides[idx], req.get("text", ""))
            msg = "대본을 저장했습니다."
        elif op == "delete":
            if len(slides) <= 1:
                return {"ok": False, "message": "마지막 한 장은 삭제할 수 없습니다."}
            slides.pop(idx)
            new_idx, msg = min(idx, len(slides) - 1), "슬라이드를 삭제했습니다."
        elif op == "duplicate":
            slides.insert(idx + 1, slides[idx])
            new_idx, msg = idx + 1, "슬라이드를 복제했습니다."
        elif op == "move":
            to = max(0, min(len(slides) - 1, int(req.get("to", idx))))
            if to == idx:
                return {"ok": True, "project": ACTIVE_PROJECT, "idx": idx, "can_undo": bool(UNDO)}
            slides.insert(to, slides.pop(idx))
            new_idx, msg = to, f"{to + 1}번째로 옮겼습니다."
        elif op in ("ai_edit", "ai_insert"):
            cfg, provider, key, model = _ai_cfg()
            mode = "edit" if op == "ai_edit" else "insert"
            logger.info(f"AI 슬라이드 {'수정' if mode == 'edit' else '추가'}: {idx + 1}번 · {str(req.get('instruction', ''))[:40]}")
            res = rewrite_slide(mode, slides, idx, req.get("instruction", ""), ACTIVE_PROJECT.get("title", ""),
                                provider=provider, api_key=key, model=model,
                                opts=resolve_opts(cfg.get("gen_opts") or {}, ACTIVE_PROJECT.get("theme", "")),
                                use_research=bool(req.get("research")),
                                history=req.get("history") if isinstance(req.get("history"), list) else None)
            sec = slide_ops.sanitize_section(res["html"])
            if mode == "edit":
                slides[idx], msg = sec, f"{idx + 1}번 슬라이드를 AI로 고쳤습니다."
                reply = res.get("reply", "")
            else:
                slides.insert(idx + 1, sec)
                new_idx, msg = idx + 1, f"{idx + 2}번에 새 슬라이드를 추가했습니다."
        else:
            return {"ok": False, "message": "알 수 없는 작업입니다."}
    except AIGenerationError as e:
        return {"ok": False, "message": str(e)}
    except ValueError as e:
        return {"ok": False, "message": str(e)}
    except Exception as e:
        logger.exception("슬라이드 편집 오류")
        return {"ok": False, "message": f"처리 중 오류가 발생했습니다: {e}"}

    if op in ("delete", "duplicate", "move", "ai_edit", "ai_insert"):
        from ai_engine import _toc_slide
        slides = slide_ops.refresh_toc(slides, _toc_slide)
    UNDO.append((ACTIVE_PROJECT.get("slides_html", ""), idx))
    del UNDO[:-UNDO_MAX]
    ACTIVE_PROJECT["slides_html"] = slide_ops.join_slides(slides)
    ACTIVE_PROJECT["updated_at"] = datetime.now().isoformat()
    _persist_active()
    return {"ok": True, "project": ACTIVE_PROJECT, "idx": new_idx, "message": msg, "can_undo": True, "reply": reply}


# ───────────────── AI 시각 검수 (화면을 찍어 문제를 찾고 AI가 고침) ─────────────────
REVIEW_STATE = {"running": False, "done": 0, "total": 0, "msg": "", "result": None, "pid": "", "rev": 0}
REVIEW_STOP = threading.Event()


def _review_job(pid: str, slides: list, title: str, theme: str, font: str, display, provider: str, key: str, model: str):
    from core import slide_review

    def compile_fn(sl):
        return compile_slide_deck(slides_html=slide_ops.join_slides(sl), title=title, theme_id=theme,
                                  font_id=font, inline_all=True, display=display)

    def progress(done, total, msg):
        REVIEW_STATE.update(done=done, total=total, msg=msg)

    result = {"ok": False, "message": ""}
    try:
        with BUSY:
            out = slide_review.review_deck(slides, title, compile_fn, provider, key, model,
                                           sanitize=slide_ops.sanitize_section, progress=progress, should_stop=REVIEW_STOP.is_set)
        with PHOTO_LOCK:
            if ACTIVE_PROJECT.get("id") != pid:
                result = {"ok": False, "message": "검수하는 동안 다른 프로젝트를 열어서 결과를 반영하지 않았습니다."}
            else:
                now = slide_ops.split_slides(ACTIVE_PROJECT.get("slides_html", ""))
                new, applied = list(now), []
                for f in out["fixed"]:
                    i = f["i"]
                    # 검수 중 사용자가 그 슬라이드를 고쳤다면 건드리지 않는다
                    if i < len(now) and i < len(slides) and now[i] == slides[i]:
                        new[i] = out["slides"][i]
                        applied.append(f)
                if applied:
                    from ai_engine import _toc_slide
                    new = slide_ops.refresh_toc(new, _toc_slide)
                    UNDO.append((ACTIVE_PROJECT.get("slides_html", ""), 0))
                    del UNDO[:-UNDO_MAX]
                    ACTIVE_PROJECT["slides_html"] = slide_ops.join_slides(new)
                    ACTIVE_PROJECT["updated_at"] = datetime.now().isoformat()
                    _persist_active()
                result = {"ok": True, "checked": out["checked"], "fixed": applied, "left": out["left"]}
    except AIGenerationError as e:
        result = {"ok": False, "message": str(e)}
    except Exception as e:
        logger.exception("AI 검수 오류")
        result = {"ok": False, "message": str(e) if isinstance(e, RuntimeError) else f"검수 중 오류가 발생했습니다: {e}"}
    REVIEW_STATE.update(running=False, result=result, rev=REVIEW_STATE["rev"] + 1)


def _review_start() -> dict:
    if REVIEW_STATE["running"]:
        return {"ok": False, "message": "이미 검수하는 중입니다."}
    slides = slide_ops.split_slides(ACTIVE_PROJECT.get("slides_html", ""))
    if not slides:
        return {"ok": False, "message": "검수할 슬라이드가 없습니다."}
    key, model = _gemini_aux()
    provider = "gemini"
    if not key:
        return {"ok": False, "message": "AI 검수는 화면을 보는 Gemini 키가 필요합니다. ⚙️ 설정에서 Gemini 키를 입력해 주세요. (글쓰기 AI는 구독 로그인이어도 됩니다)"}
    REVIEW_STOP.clear()
    pid = ACTIVE_PROJECT.get("id")
    REVIEW_STATE.update(running=True, done=0, total=len(slides), msg="준비 중", result=None, pid=pid)
    logger.info(f"AI 검수 시작: {len(slides)}장")
    threading.Thread(target=_review_job, daemon=True, args=(
        pid, slides, ACTIVE_PROJECT.get("title", "") or "결 프레젠테이션", ACTIVE_PROJECT.get("theme"),
        ACTIVE_PROJECT.get("font"), ACTIVE_PROJECT.get("display"), provider, key, model)).start()
    return {"ok": True}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    request_queue_size = 128  # 썸네일 여러 장이 동시에 요청해도 연결이 거부되지 않게


def set_allowed_port(port: int):
    ALLOWED_HOSTS.clear()
    ALLOWED_HOSTS.update({f"127.0.0.1:{port}", f"localhost:{port}"})



# 미리보기 HTML 재사용: 슬라이드 목록 썸네일 20장이 저마다 덱 전체를 다시 만들던 것을
# 덱이 바뀌지 않았으면 한 번 만든 결과를 돌려준다. 썸네일은 해당 장만 내용을 넣고
# 나머지 장은 빈 틀만 남겨(번호 계산용) 사진·글자를 매번 그리지 않게 한다.
_PREVIEW_CACHE = {}
_PREVIEW_LOCK = threading.Lock()


def _preview_key() -> str:
    p = ACTIVE_PROJECT
    raw = json.dumps([p.get("slides_html", ""), p.get("title", ""), p.get("theme", ""), p.get("font", ""),
                      p.get("display")], ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _top_sections(html_str: str):
    """최상위 <section>...</section> 구간들의 (시작, 끝) 위치."""
    out, depth, start = [], 0, -1
    for m in re.finditer(r"<section\b[^>]*>|</section\s*>", html_str, re.I):
        if m.group(0)[1] != "/":
            if depth == 0:
                start = m.start()
            depth += 1
        elif depth:
            depth -= 1
            if depth == 0:
                out.append((start, m.end()))
    return out


def _thumb_slides(html_str: str, keep_no: int) -> str:
    secs = _top_sections(html_str)
    if not (1 <= keep_no <= len(secs)):
        return html_str
    parts, last = [], 0
    for i, (a, b) in enumerate(secs, 1):
        parts.append(html_str[last:a])
        seg = html_str[a:b]
        if i != keep_no:
            open_tag = re.match(r"<section\b[^>]*>", seg, re.I).group(0)
            seg = open_tag + "</section>"
        parts.append(seg)
        last = b
    parts.append(html_str[last:])
    return "".join(parts)


def _preview_html(thumb: int = 0) -> str:
    key = (_preview_key(), thumb)
    with _PREVIEW_LOCK:
        hit = _PREVIEW_CACHE.get(key)
    if hit is not None:
        return hit
    p = ACTIVE_PROJECT
    slides = p["slides_html"]
    if thumb:
        slides = _thumb_slides(slides, thumb)
    compiled = compile_slide_deck(slides_html=slides, title=p["title"], theme_id=p["theme"],
                                  font_id=p["font"], inline_all=False, display=p.get("display"))
    with _PREVIEW_LOCK:
        if len(_PREVIEW_CACHE) > 400:
            _PREVIEW_CACHE.clear()
        _PREVIEW_CACHE[key] = compiled
    return compiled


_THEME_PREVIEW_CACHE = {}


def _theme_preview_html(theme: str, font: str) -> str:
    key = (theme, font)
    hit = _THEME_PREVIEW_CACHE.get(key)
    if hit is None:
        hit = compile_slide_deck(slides_html=THEME_SAMPLE, title="theme", theme_id=theme,
                                 font_id=font, inline_all=False)
        hit = hit.replace("</head>", "<style>.progress-bar{display:none!important}</style></head>")
        if len(_THEME_PREVIEW_CACHE) > 600:
            _THEME_PREVIEW_CACHE.clear()
        _THEME_PREVIEW_CACHE[key] = hit
    return hit

class KDesignHandler(BaseHTTPRequestHandler):
    def _cookie_token(self) -> str:
        c = SimpleCookie()
        try:
            c.load(self.headers.get("Cookie", ""))
        except Exception:
            return ""
        return c[TOKEN_COOKIE].value if TOKEN_COOKIE in c else ""

    def _token_ok(self, extra: str = "") -> bool:
        return any(t and hmac.compare_digest(t, API_TOKEN) for t in (self.headers.get("X-Gyeol-Token", ""), self._cookie_token(), extra))

    def _origin_ok(self) -> bool:
        """다른 사이트에서 온 요청·DNS 리바인딩 차단."""
        if ALLOWED_HOSTS and self.headers.get("Host", "") not in ALLOWED_HOSTS:
            return False
        origin = self.headers.get("Origin")
        if origin and origin.replace("http://", "", 1) not in ALLOWED_HOSTS:
            return False
        return self.headers.get("Sec-Fetch-Site", "same-origin") in ("same-origin", "none")

    def _deny(self):
        self._send_json(403, {"ok": False, "message": "허용되지 않은 접근입니다."})

    def _license_ok(self) -> bool:
        return LICENSE_BYPASS or licensing.is_usable()

    def _license_block(self):
        st = licensing.status()
        self._send_json(403, {**st, "ok": False, "license_required": True,
                              "message": "라이선스 키를 확인한 뒤에 사용할 수 있습니다."})

    def log_message(self, format, *args):
        # 정적 파일 GET 요청은 로그에서 축약하여 터미널을 깔끔하게 유지
        if self.path.startswith("/static/"):
            return
        super().log_message(format, *args)

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionError, OSError):
            pass  # 연결이 끊긴 요청은 조용히 무시

    def _send_html(self, status_code: int, html_str: str):
        body = html_str.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: str, cache: str = ""):
        if not os.path.isfile(file_path):
            self.send_error(404, "File Not Found")
            return
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
        if file_path.endswith(".css"):
            mime_type = "text/css; charset=utf-8"
        elif file_path.endswith(".js"):
            mime_type = "application/javascript; charset=utf-8"

        try:
            st = os.stat(file_path)
            etag = f'"{int(st.st_mtime_ns):x}-{st.st_size:x}"'
            if cache == "immutable":      # 내용 해시가 파일 이름인 사진: 바뀌지 않으므로 오래 보관
                cc = "private, max-age=31536000, immutable"
            elif cache == "short":        # CSS·JS·아이콘: 잠깐은 그대로 쓰고, 그 뒤엔 바뀌었는지만 확인
                cc = "private, max-age=600"
            else:
                cc = "no-cache"
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", cc)
                self.end_headers()
                return
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", cc)
            self.send_header("ETag", etag)
            self.end_headers()
            self.wfile.write(content)
        except (ConnectionError, OSError):
            pass  # 브라우저가 요청을 취소한 경우 (썸네일 새로고침 등)
        except Exception as e:
            logger.error(f"파일 전송 실패: {file_path} - {e}")
            self.send_error(500, "Internal Server Error")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if not self._origin_ok():
            return self._deny()
        if path == "/api/ping":
            self._send_json(200, {"app": "Gyeol"})   # 실행 중인지 확인만 (정보 없음)
            return
        key = urllib.parse.parse_qs(parsed.query).get("k", [""])[0]
        if path == "/" and key and self._token_ok(key):
            # 프로그램 창이 처음 열릴 때 비밀값을 쿠키로 옮기고 주소에서 지운다
            self.send_response(302)
            self.send_header("Set-Cookie", f"{TOKEN_COOKIE}={API_TOKEN}; Path=/; HttpOnly; SameSite=Strict")
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if not self._token_ok():
            return self._deny()
        if not (path in LICENSE_FREE_GET or path.startswith("/static/")) and not self._license_ok():
            return self._license_block()

        if path == "/api/busy":   # 종료 창이 '지금 하는 작업'을 보여 주려고 조회
            self._send_json(200, {"busy": is_busy(), "items": busy_items(), "auto_quit": desktop.is_auto_quit()})
            return

        if path == "/api/update/status":
            fresh = urllib.parse.parse_qs(parsed.query).get("fresh", [""])[0] == "1"
            st = updater.status_fresh() if fresh else updater.status()
            self._send_json(200, {k: v for k, v in st.items() if not k.startswith("_")})
            return

        # 1. 메인 웹 대시보드
        if path == "/" or path == "/index.html":
            index_path = os.path.join(STATIC_DIR, "index.html")
            self._send_file(index_path)
            return

        # 2. 정적 파일 호스팅 (/static/...)
        if path.startswith("/static/"):
            rel_path = urllib.parse.unquote(path[len("/static/"):]).lstrip("/\\")
            file_path = os.path.realpath(os.path.join(STATIC_DIR, rel_path))
            if not file_path.startswith(os.path.realpath(STATIC_DIR) + os.sep):
                return self._deny()
            self._send_file(file_path, cache="short")
            return

        # 3. 실시간 프리뷰 렌더링용 엔드포인트 (/preview)
        if path == "/preview" or path.startswith("/preview"):
            q = urllib.parse.parse_qs(parsed.query)
            thumb = 0
            if (q.get("thumb") or [""])[0] == "1":
                try:
                    thumb = int((q.get("preview") or ["0"])[0])
                except ValueError:
                    thumb = 0
            self._send_html(200, _preview_html(thumb))
            return

        # 3-1. 테마 갤러리 썸네일용 미리보기 (/theme_preview?theme=...)
        if path == "/theme_preview":
            q = urllib.parse.parse_qs(parsed.query)
            self._send_html(200, _theme_preview_html((q.get("theme") or ["pitch-deck-vc"])[0],
                                                     (q.get("font") or ["theme"])[0]))
            return

        # 3-2. 슬라이드에 넣은 사진 (data/media)
        if path.startswith("/media/"):
            fp = media.media_path(path[len("/media/"):])
            if fp:
                self._send_file(fp, cache="immutable")
            else:
                self.send_error(404, "Not Found")
            return

        if path == "/favicon.ico":
            self._send_file(os.path.join(STATIC_DIR, "img", "app.ico"))
            return

        # 4. API 엔드포인트들
        if path == "/api/ping":
            self._send_json(200, {"ok": True, "app": "Gyeol"})
            return

        if path == "/api/cli/status":
            pv = urllib.parse.parse_qs(parsed.query).get("provider", [""])[0]
            if config_mod.IS_RETAIL or pv not in CLI_PROVIDERS:
                self._send_json(403 if config_mod.IS_RETAIL else 200, {"ok": False, "message": "이 버전에서는 쓸 수 없습니다."})
                return
            self._send_json(200, {"ok": True, **cli_llm.status(pv)})
            return

        if path == "/api/photo_status":
            self._send_json(200, dict(PHOTO_STATE))
            return

        if path == "/api/review_status":
            self._send_json(200, dict(REVIEW_STATE))
            return

        if path == "/api/presets":
            self._send_json(200, {"presets": get_all_presets()})
            return

        if path == "/api/themes":
            self._send_json(200, {"themes": AVAILABLE_THEMES, "mood_styles": mood_styles()})
            return

        if path == "/api/fonts":
            self._send_json(200, {"fonts": AVAILABLE_FONTS})
            return

        if path == "/api/config":
            cfg = load_config()
            self._send_json(200, {"config": cfg, "gen_opts": dict(DEFAULT_OPTS, **(cfg.get("gen_opts") or {})), "edition": config_mod.EDITION})
            return

        if path == "/api/history":
            self._send_json(200, {"history": load_history()})
            return

        if path == "/api/active_project":
            self._send_json(200, {"project": ACTIVE_PROJECT})
            return

        if path == "/api/license":
            self._send_json(200, _license_view(force="force=1" in (parsed.query or "")))
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        if not self._origin_ok() or not self._token_ok() or "application/json" not in self.headers.get("Content-Type", ""):
            self.close_connection = True
            return self._deny()
        if content_len > MAX_BODY:
            self.close_connection = True
            self._send_json(413, {"ok": False, "message": "보낸 내용이 너무 큽니다."})
            return
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        # 0. 라이선스
        if path == "/api/license_activate":
            try:
                st = licensing.activate(str(req_data.get("key", "")))
                self._send_json(200, {"ok": True, **st})
            except (licensing.LicenseError, ConnectionError) as e:
                self._send_json(200, {"ok": False, "msg": str(e), **licensing.status()})
            return
        if path == "/api/license_logout":
            self._send_json(200, {"ok": True, **licensing.logout()})
            return
        licensing.start_background()
        if path not in LICENSE_FREE and not self._license_ok():
            return self._license_block()

        if path == "/api/focus":
            desktop.focus_window()
            self._send_json(200, {"ok": True})
            return
        if path == "/api/app/close":
            mode = req_data.get("mode")
            if mode == "tray":
                ok = desktop.hide_to_tray()
                self._send_json(200 if ok else 500, {"ok": ok, "message": "" if ok else "트레이 아이콘을 만들 수 없습니다."})
            elif mode == "when_idle":   # 창은 두고, 작업이 끝나면 자동 종료
                desktop.schedule_quit_when_idle()
                self._send_json(200, {"ok": True, "auto_quit": True})
            elif mode == "cancel_auto":
                desktop.cancel_auto_quit()
                self._send_json(200, {"ok": True, "auto_quit": False})
            elif mode == "quit":
                if req_data.get("remember") and not is_busy():   # '다음부터 묻지 않기' (작업 중일 때는 항상 물어본다)
                    cfg = load_config(); cfg["skip_exit_confirm"] = True; save_config(cfg)
                self._send_json(200, {"ok": True})
                threading.Thread(target=desktop.quit_window, daemon=True).start()
            else:
                self._send_json(400, {"ok": False, "message": "잘못된 선택입니다."})
            return

        if path == "/api/update/ack":
            updater.ack_just_updated()
            self._send_json(200, updater.status())
            return
        if path == "/api/update/check":
            self._send_json(200, updater.check(force=True))
            return
        if path == "/api/update/install":
            err = updater.install(shutdown_app)
            self._send_json(400 if err else 200, {"ok": not err, "message": err or "", **updater.status()})
            return

        if path == "/api/open_key_page":
            import webbrowser
            webbrowser.open("https://aistudio.google.com/apikey")   # 정해진 주소만 연다
            self._send_json(200, {"ok": True})
            return

        if path == "/api/test_key":
            self._send_json(200, _test_gemini_key(str(req_data.get("key") or "").strip()))
            return

        if path == "/api/read_source":
            cfg_, provider_, key_, model_ = _ai_cfg()
            gkey = cfg_.get("gemini_api_key", "")   # 스캔 문서·사진은 Gemini 비전으로 읽는다
            ocr = (lambda imgs: ocr_images(imgs, gkey, cfg_.get("gemini_model", ""))) if gkey else None
            try:
                with BUSY:
                    res = sources.read_file(req_data.get("name"), req_data.get("data"), ocr=ocr)
                self._send_json(200, {"ok": True, **res})
            except sources.SourceError as e:
                self._send_json(200, {"ok": False, "message": str(e)})
            except AIGenerationError as e:
                self._send_json(200, {"ok": False, "message": str(e)})
            return

        # 1. AI 슬라이드 생성 요청 (/api/generate)
        if path == "/api/generate":
            prompt = req_data.get("prompt", "").strip()
            preset_id = req_data.get("preset_id", "pitch-deck")
            theme = req_data.get("theme", "pitch-deck-vc")
            font = req_data.get("font", "theme")
            title = req_data.get("title", "").strip()
            if not title or title in ("새 프레젠테이션", "새로운 프레젠테이션", "샘플 프레젠테이션"):
                title = prompt[:40] or "새 프레젠테이션"

            cfg = load_config()
            provider = req_data.get("provider") or cfg.get("provider", "gemini")
            if provider in CLI_PROVIDERS and config_mod.IS_RETAIL:
                provider = "gemini"   # 판매판은 구독 로그인을 쓰지 않는다
            api_key = req_data.get("api_key") or (
                cfg.get("gemini_api_key") if provider == "gemini" else cfg.get("openai_api_key")
            )
            model = req_data.get("model") or (
                cfg.get("gemini_model") if provider == "gemini" else cfg.get("openai_model")
            )
            if provider in CLI_PROVIDERS:
                api_key, model = "", ""

            media.set_pixabay_key(cfg.get("pixabay_api_key", ""))
            media.set_vision_key(cfg.get("gemini_api_key", ""))
            opts = req_data.get("opts") or {}
            gm = model if provider == "gemini" else cfg.get("gemini_model", "")
            summ = (lambda c, t, n, i, tot: summarize_chunk(c, t, n, i, tot, cfg.get("gemini_api_key", ""), gm)) if cfg.get("gemini_api_key") else None
            with BUSY:   # 긴 문서는 여기서 조각별로 요약하느라 시간이 걸린다
                material, material_names = sources.build_material(req_data.get("material") or [], summarize=summ)
            if material_names and not req_data.get("prompt", "").strip():
                title = os.path.splitext(material_names[0])[0][:40]
            if not material_names:   # 자료 첨부 때의 조사 끔은 이번 생성에만 적용
                cfg["gen_opts"] = opts  # 다음 실행 때 같은 옵션으로 시작
                save_config(cfg)
            logger.info(f"AI 슬라이드 생성 시작 - 주제: {prompt[:40]} (제공자: {provider})")
            # 토큰: 서버의 서명된 승인이 있어야 생성한다. 실패하면 돌려준다
            rid, done = "", False
            if provider != "fallback" and not LICENSE_BYPASS:
                try:
                    rid = licensing.reserve()
                except licensing.LicenseError as e:
                    self._send_json(200, {"ok": False, "message": str(e)})
                    return
            try:
                with BUSY:
                    result = generate_presentation_slides(
                        prompt=prompt, provider=provider, api_key=api_key, model=model, preset_id=preset_id,
                        slide_count=int(opts.get("slide_count") or 10),
                        use_research=bool(opts.get("research", True)),
                        opts=resolve_opts(opts, theme), defer_photos=True, material=material, material_names=material_names,
                    )
                done = True
            except AIGenerationError as e:
                self._send_json(200, {"ok": False, "message": str(e)})
                return
            except Exception as e:
                logger.exception("슬라이드 생성 오류")
                self._send_json(200, {"ok": False, "message": f"생성 중 오류가 발생했습니다: {e}"})
                return
            finally:
                if rid and not done:
                    licensing.refund(rid)

            pid = f"proj-{int(datetime.now().timestamp())}"
            UNDO.clear()
            display = ACTIVE_PROJECT.get("display") or {}
            ACTIVE_PROJECT.update({"id": pid, "title": title, "theme": theme, "font": font, "display": display,
                                   "slides_html": result["html"], "updated_at": datetime.now().isoformat()})
            add_project_history({
                "id": pid, "title": title, "prompt": prompt, "theme": theme, "font": font, "display": display,
                "preset_id": preset_id, "slides_html": result["html"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            jobs = result.get("photo_jobs") or {}
            with PHOTO_LOCK:
                PHOTO_STATE.update({"pid": pid, "pending": len(jobs), "rev": PHOTO_STATE["rev"] + 1})
            if jobs:
                threading.Thread(target=_fill_photos, args=(pid, jobs), daemon=True).start()
            logger.info(f"생성 완료: {result['slide_count']}장, 모델 {result['model']}, 출처 {len(result['sources'])}개, 사진 {len(jobs)}장 찾는 중")
            self._send_json(200, {
                "ok": True,
                "message": f"{result['slide_count']}장의 슬라이드를 만들었습니다.",
                "slide_count": result["slide_count"], "model": result["model"],
                "research_used": result["research_used"], "source_count": len(result["sources"]),
                "research_failed": bool(result.get("research_failed")),
                "research_how": result.get("research_how", ""),
                "research_note": "인터넷 조사 결과를 가져오지 못해 AI가 알고 있는 내용으로 만들었습니다. 수치는 직접 확인해 주세요.",
                "photos_pending": len(jobs), "project": ACTIVE_PROJECT,
            })
            return

        # 1-1. 저장된 프로젝트 열기 (/api/load_project)
        if path == "/api/load_project":
            pid = req_data.get("id")
            p = next((h for h in load_history() if h.get("id") == pid), None)
            if not p:
                self._send_json(200, {"ok": False, "message": "프로젝트를 찾을 수 없습니다."})
                return
            UNDO.clear()
            ACTIVE_PROJECT.update({"id": p["id"], "title": p.get("title", ""), "theme": canon_theme(p.get("theme", "")),
                                   "font": p.get("font", "theme"), "slides_html": p.get("slides_html", ""),
                                   "display": p.get("display") or {}, "updated_at": datetime.now().isoformat()})
            self._send_json(200, {"ok": True, "project": ACTIVE_PROJECT})
            return

        # 1-2. 슬라이드 한 장 편집 (/api/slide_op)
        if path == "/api/slide_op":
            with PHOTO_LOCK:  # 뒤에서 사진을 넣는 작업과 동시에 고치지 않게
                res = _slide_op(req_data)
            self._send_json(200, res)
            return

        # 구독 로그인 시작 (/api/cli/login) — 공식 CLI가 기본 브라우저(크롬 등)를 열어 로그인
        if path == "/api/cli/login":
            pv = req_data.get("provider")
            if config_mod.IS_RETAIL or pv not in CLI_PROVIDERS:
                self._send_json(403, {"ok": False, "message": "이 버전에서는 쓸 수 없습니다."})
                return
            try:
                self._send_json(200, cli_llm.start_login(pv))
            except cli_llm.CliError as e:
                self._send_json(200, {"ok": False, "message": str(e)})
            return

        # 1-2b. AI 시각 검수 (/api/review_start, /api/review_stop)
        if path == "/api/review_start":
            self._send_json(200, _review_start())
            return
        if path == "/api/review_stop":
            REVIEW_STOP.set()
            self._send_json(200, {"ok": True})
            return

        # 1-3. 그림·사진 (/api/media_upload, /api/photo_search, /api/media_fetch, /api/ai_image)
        if path in ("/api/media_upload", "/api/photo_search", "/api/media_fetch", "/api/ai_image"):
            self._send_json(200, _media_api(path, req_data))
            return

        # 2. 테마 및 폰트 즉시 변경 반영 (/api/update_style)
        if path == "/api/update_style":
            theme = req_data.get("theme")
            font = req_data.get("font")
            title = req_data.get("title")
            if isinstance(theme, str) and theme in THEME_IDS:
                ACTIVE_PROJECT["theme"] = theme
            if isinstance(font, str) and (font == "theme" or font in FONT_IDS):
                ACTIVE_PROJECT["font"] = font
            if isinstance(title, str) and title.strip():
                ACTIVE_PROJECT["title"] = title.strip()[:120]
            disp = req_data.get("display")
            if isinstance(disp, dict):
                if len(str(disp.get("logo") or "")) > 900_000:
                    self._send_json(200, {"ok": False, "message": "로고 이미지는 600KB 이하로 올려 주세요."})
                    return
                merged = dict(ACTIVE_PROJECT.get("display") or {})
                merged.update(disp)
                ACTIVE_PROJECT["display"] = merged
            ACTIVE_PROJECT["updated_at"] = datetime.now().isoformat()
            _persist_active()

            self._send_json(200, {"ok": True, "project": ACTIVE_PROJECT})
            return

        # 3. 설정 저장 (/api/config)
        if path == "/api/config":
            cfg = load_config()
            if config_mod.IS_RETAIL and req_data.get("provider") in CLI_PROVIDERS:
                self._send_json(200, {"ok": False, "message": "이 버전에서는 구독 로그인 방식을 쓸 수 없습니다. API 키 방식을 골라 주세요."})
                return
            # 화면이 바꿀 수 있는 항목만 받는다 (임의 키를 설정 파일에 써넣지 못하게). 값은 글자·불리언만, 길이 제한
            for k, v in req_data.items():
                if k in CLIENT_CFG_KEYS and (isinstance(v, bool) or (isinstance(v, str) and len(v) <= 400)):
                    cfg[k] = v
            save_config(cfg)
            self._send_json(200, {"ok": True, "config": cfg})
            return

        # 4. 내보내기 (/api/export) — 저장 위치를 고른 뒤 HTML/PDF/PPTX/PNG로 저장
        if path in ("/api/export", "/api/export_html"):
            fmt = (req_data.get("format") or "html").lower()
            if fmt not in exporter.FORMATS:
                self._send_json(200, {"ok": False, "message": "지원하지 않는 형식입니다."})
                return
            label, ext = exporter.FORMATS[fmt]
            title = ACTIVE_PROJECT.get("title") or "결_프레젠테이션"
            safe_name = re.sub(r'[\\/:*?"<>|]+', "_", title).strip() or "결_프레젠테이션"
            cfg = load_config()
            out_path = save_dialog.ask_save_path(safe_name + ext, label, ext, cfg.get("export_dir", ""))
            if not out_path:
                self._send_json(200, {"ok": False, "cancelled": True, "message": "저장을 취소했습니다."})
                return
            deck_html = compile_slide_deck(
                slides_html=ACTIVE_PROJECT["slides_html"], title=title, theme_id=ACTIVE_PROJECT["theme"],
                font_id=ACTIVE_PROJECT["font"], inline_all=True, display=ACTIVE_PROJECT.get("display"),
            )
            try:
                with BUSY:
                    exporter.export(fmt, deck_html, ACTIVE_PROJECT["slides_html"], out_path, title)
            except exporter.ExportError as e:
                self._send_json(200, {"ok": False, "message": str(e)})
                return
            except Exception as e:
                logger.exception("내보내기 실패")
                self._send_json(200, {"ok": False, "message": f"저장 중 오류가 발생했습니다: {e}"})
                return
            cfg["export_dir"] = os.path.dirname(out_path)
            save_config(cfg)
            logger.info(f"내보내기 완료: {out_path}")
            self._send_json(200, {"ok": True, "path": out_path, "message": f"{label}로 저장했습니다."})
            return

        # 5. 저장한 파일 위치 열기 (/api/reveal)
        if path == "/api/reveal":
            p = req_data.get("path") or ""
            if p and os.path.exists(p):
                save_dialog.reveal_in_folder(p)
            self._send_json(200, {"ok": True})
            return

        self.send_error(404, "Not Found")


class _Busy:
    """진행 중인 작업 수 (X 버튼 안내, 트레이 자동 종료에 사용)."""
    def __init__(self):
        self.n, self.lock = 0, threading.Lock()

    def __enter__(self):
        with self.lock:
            self.n += 1

    def __exit__(self, *a):
        with self.lock:
            self.n -= 1


BUSY = _Busy()


def busy_items() -> list:
    """지금 진행 중인 작업을 사람이 읽을 말로 (종료 창에 보여 준다)."""
    items = []
    if BUSY.n > 0:
        items.append("슬라이드 생성·수정·검수 중")
    if PHOTO_STATE.get("pending", 0) > 0:
        items.append(f"사진 {PHOTO_STATE['pending']}장 찾는 중")
    if updater.status()["state"] in ("downloading", "verifying", "installing"):
        items.append("업데이트 받는 중")
    return items


def skip_exit_confirm() -> bool:
    try:
        return bool(load_config().get("skip_exit_confirm"))
    except Exception:
        return False


def is_busy() -> bool:
    return BUSY.n > 0 or PHOTO_STATE.get("pending", 0) > 0 or updater.status()["state"] in ("downloading", "verifying", "installing")


def _test_gemini_key(key: str) -> dict:
    """모델 목록 조회로 키 확인 (생성 한도를 쓰지 않음)."""
    import urllib.error
    import urllib.request
    if len(key) < 20:
        return {"ok": False, "message": "키가 너무 짧습니다. 복사한 키 전체를 붙여 넣어 주세요."}
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1",
                                 headers={"x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=15):
            return {"ok": True, "message": "키가 정상입니다."}
    except urllib.error.HTTPError as e:
        if e.code in (400, 401, 403):
            return {"ok": False, "message": "사용할 수 없는 키입니다. 복사가 빠졌거나 잘못된 키가 아닌지 확인해 주세요."}
        return {"ok": False, "message": f"Google 서버 응답 오류({e.code})입니다. 잠시 뒤 다시 시도해 주세요."}
    except Exception:
        return {"ok": False, "message": "인터넷 연결을 확인한 뒤 다시 시도해 주세요."}


def shutdown_app():
    """업데이트 적용: 안내를 마친 뒤 프로그램 종료 (새 프로세스가 이어서 시작)."""
    desktop.stop_tray()
    desktop.clear_instance()
    os._exit(0)


def main():
    # 1. 이미 실행 중인 인스턴스가 있는지 확인
    # 창을 하나만 쓴다: 두 번째 실행은 기존 창을 앞으로 가져오고 끝난다 (업데이트 때 창이 남지 않게)
    existing_port = desktop.find_running_instance()
    if existing_port:
        logger.info("이미 실행 중입니다. 기존 창을 앞으로 가져옵니다.")
        desktop.activate_instance(existing_port)
        return

    # 2. 포트 결정 및 바인딩
    port = desktop.pick_port(9090)
    server_address = ("127.0.0.1", port)
    httpd = ThreadedHTTPServer(server_address, KDesignHandler)
    set_allowed_port(port)
    url = f"http://127.0.0.1:{port}/?k={API_TOKEN}"

    desktop.write_instance(port, API_TOKEN)
    licensing.start_background()
    updater.detect_just_updated()
    updater.cleanup_old_downloads()
    if getattr(sys, "frozen", False):
        updater.start_background_checks()
    logger.info("=" * 60)
    logger.info(f"결(GYEOL) 구동 완료 (포트 {port})")
    logger.info("=" * 60)

    # 3. 백엔드 HTTP 서버 백그라운드 스레드 구동
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    # 4. 데스크톱 프로그램 창 띄우기
    try:
        if desktop.run_desktop_window(url, is_busy, skip_exit_confirm) == "window":
            return   # 프로그램 창을 닫으면 종료
        while server_thread.is_alive():   # 브라우저로 연 경우
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("프로그램을 종료합니다.")
    finally:
        desktop.clear_instance()
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()   # exe에서 하위 프로세스가 프로그램 전체를 다시 띄우지 않게
    main()
