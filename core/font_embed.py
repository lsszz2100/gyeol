"""
결(GYEOL) - 내보내기 폰트 포함

내보낸 파일을 인터넷이 없거나 폰트가 없는 PC에서 열어도 만든 그대로 보이도록,
덱이 쓰는 웹폰트를 파일 안에 넣는다.

1. 외부 폰트 CSS(@import)를 받아 스타일 안에 펼친다.
2. 브라우저로 모든 슬라이드를 한 번씩 그려서, 실제로 내려받은 폰트 조각만 기록한다.
   (한글 웹폰트는 글자 범위별로 100여 조각으로 나뉘어 있어 전부 넣으면 수십 MB가 된다)
3. 쓰인 조각은 data: 주소로 바꿔 넣고, 쓰이지 않은 조각의 @font-face 는 뺀다.

폰트를 받지 못하면(인터넷 끊김 등) 원래 HTML을 그대로 돌려준다.
"""

import base64
import logging
import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger("gyeol.fonts")

# 구글 폰트는 브라우저 종류에 따라 다른 CSS를 준다 → woff2·글자 범위 조각을 받도록 최신 크롬으로 요청
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
IMPORT_RE = re.compile(r"@import\s+url\(\s*['\"]?(https?://[^'\")\s]+)['\"]?\s*\)\s*[^;]*;", re.I)
FONT_FACE_RE = re.compile(r"@font-face\s*\{[^{}]*\}", re.I)
URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")
FONT_MIME = {"woff2": "font/woff2", "woff": "font/woff", "ttf": "font/ttf", "otf": "font/otf"}
_CSS_CACHE = {}


def _fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _absolutize(css: str, base: str) -> str:
    """CSS 안의 상대 주소(url(./x.woff2))를 절대 주소로."""
    def fix(m):
        u = m.group(1).strip()
        if u.startswith(("data:", "http://", "https://", "#")):
            return m.group(0)
        return f"url('{urllib.parse.urljoin(base, u)}')"
    return URL_RE.sub(fix, css)


def _expand_imports(css: str, depth: int = 0) -> str:
    """@import url(https://...) 를 받아온 CSS 본문으로 바꾼다 (중첩 import 포함)."""
    if depth > 3:
        return css

    def rep(m):
        url = m.group(1)
        if url not in _CSS_CACHE:
            try:
                _CSS_CACHE[url] = _absolutize(_fetch(url).decode("utf-8", "replace"), url)
            except Exception as e:
                logger.warning(f"폰트 CSS를 받지 못했습니다: {url} ({e})")
                return m.group(0)   # 못 받으면 원래 import 를 남긴다(인터넷이 되면 동작)
        return _expand_imports(_CSS_CACHE[url], depth + 1)
    return IMPORT_RE.sub(rep, css)


def _font_ext(url: str) -> str:
    m = re.search(r"\.(woff2|woff|ttf|otf)(?:[?#]|$)", url, re.I)
    return m.group(1).lower() if m else "woff2"


def embed_fonts(deck_html: str, timeout_ms: int = 25000) -> str:
    """deck_html(inline_all=True 로 만든 HTML) 안에 실제로 쓰인 웹폰트를 넣어 돌려준다."""
    import urllib.parse  # noqa: F401  (_absolutize 에서 사용)
    try:
        html = re.sub(r"<style>(.*?)</style>", lambda m: "<style>" + _expand_imports(m.group(1)) + "</style>",
                      deck_html, flags=re.S)
    except Exception as e:
        logger.warning(f"폰트 CSS 펼치기 실패: {e}")
        return deck_html

    used = {}   # 폰트 주소 → 바이트 (브라우저가 실제로 받은 것만)
    try:
        from playwright.sync_api import sync_playwright
        from core.pptx_editable import _launch, W, H
        with tempfile.TemporaryDirectory(prefix="gyeol_font_") as tmp:
            src = Path(tmp) / "deck.html"
            src.write_text(html, encoding="utf-8")
            with sync_playwright() as p:
                browser = _launch(p)
                page = browser.new_page(viewport={"width": W, "height": H})
                page.add_init_script("window.__noMotion=true")   # 화면을 찍을 때는 애니메이션 없이

                def on_resp(resp):
                    try:
                        if resp.request.resource_type == "font" and resp.ok:
                            used[resp.url] = resp.body()
                    except Exception:
                        pass
                page.on("response", on_resp)
                page.goto(src.resolve().as_uri(), wait_until="load", timeout=timeout_ms)
                page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true")
                total = page.evaluate("document.querySelectorAll('.deck .slide').length") or 0
                for i in range(total):   # 슬라이드마다 그려야 그 장에 쓰인 글자 조각을 받는다
                    page.evaluate(f"window.__deck && window.__deck.go({i})")
                    page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true")
                    page.wait_for_timeout(120)
                page.wait_for_timeout(400)
                browser.close()
    except Exception as e:
        logger.warning(f"폰트 조사 실패, 인터넷 폰트 주소를 그대로 둡니다: {e}")
        return html

    if not used:
        return html

    def rewrite_face(m):
        block = m.group(0)
        urls = [u.strip() for u in URL_RE.findall(block)]
        remote = [u for u in urls if u.startswith(("http://", "https://"))]
        if not remote:
            return block           # 로컬·data 폰트는 그대로
        hit = [u for u in remote if u in used]
        if not hit:
            return ""              # 이 문서에서 쓰이지 않은 글자 조각 → 뺀다
        u = hit[0]
        data = base64.b64encode(used[u]).decode("ascii")
        ext = _font_ext(u)
        new_src = f"src: url(data:{FONT_MIME.get(ext, 'font/woff2')};base64,{data}) format('{'woff2' if ext == 'woff2' else ext}');"
        # 압축된 CSS는 src 뒤에 ';' 없이 '}' 로 끝나기도 한다
        return re.sub(r"src\s*:[^;}]*;?", new_src, block, count=1)

    out = re.sub(r"<style>(.*?)</style>", lambda m: "<style>" + FONT_FACE_RE.sub(rewrite_face, m.group(1)) + "</style>",
                 html, flags=re.S)
    import os as _os
    if _os.environ.get("GYEOL_FONT_DEBUG"):
        for u, b in used.items():
            logger.info(f"  {'IN ' if ('base64' in out and u not in out) else '?? '}{len(b)//1024:5d}KB {u[:120]}")
        left = re.findall(r"url\(\s*['\"]?(https?://[^'\")]+)", out)
        logger.info(f"  남은 외부 주소 {len(left)}개: {left[:6]}")
    logger.info(f"내보내기에 폰트 {len(used)}개 조각 포함 ({sum(len(b) for b in used.values()) // 1024} KB)")
    return out
