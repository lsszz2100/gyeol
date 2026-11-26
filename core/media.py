"""그림·사진·아이콘 처리
- 이미지 파일은 data/media/<해시>.<확장자> 로 저장하고 슬라이드에는 /media/파일명 으로 넣는다.
- 사진 검색: Openverse (CC0·퍼블릭 도메인만 → 출처 표기 없이 상업적 사용 가능)
- AI 그림: Gemini 이미지 모델(유료 키) → 안 되면 Pollinations 무료 생성
- 아이콘: static/icons/icons.json
"""
import base64
import hashlib
import html as _html
import io
import json
import logging
import os
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from core import netguard
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

logger = logging.getLogger("kdesign.media")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from config import DATA_DIR as _DATA_DIR
MEDIA_DIR = os.path.join(_DATA_DIR, "media")
ICONS_FILE = os.path.join(BASE_DIR, "static", "icons", "icons.json")
os.makedirs(MEDIA_DIR, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GyeolPresentation/1.0"}
EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "image/svg+xml": ".svg"}
MAX_SIDE = 1920


class MediaError(Exception):
    pass


# ───────────────────────── 저장 ─────────────────────────
def _optimize(data: bytes, mime: str) -> tuple:
    """너무 큰 사진은 긴 변 1920px JPEG로 줄인다. (투명 PNG는 PNG 유지)"""
    if mime in ("image/svg+xml", "image/gif"):
        return data, mime
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im.load()
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        if max(im.size) > MAX_SIDE:
            im.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        if has_alpha:
            im.convert("RGBA").save(out, "PNG", optimize=True)
            return out.getvalue(), "image/png"
        im.convert("RGB").save(out, "JPEG", quality=86, optimize=True, progressive=True)
        return out.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning(f"이미지 최적화 생략: {e}")
        return data, mime


def save_bytes(data: bytes, mime: str) -> str:
    if not data or len(data) < 200:
        raise MediaError("이미지 데이터가 비어 있습니다.")
    if mime not in EXT:
        raise MediaError("지원하지 않는 이미지 형식입니다. (JPG, PNG, WEBP, GIF, SVG)")
    if mime == "image/svg+xml" and re.search(rb"<script|on\w+\s*=", data, re.I):
        raise MediaError("스크립트가 들어 있는 SVG는 넣을 수 없습니다.")
    data, mime = _optimize(data, mime)
    name = hashlib.sha1(data).hexdigest()[:20] + EXT[mime]
    path = os.path.join(MEDIA_DIR, name)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
    return "/media/" + name


def save_data_url(data_url: str) -> str:
    m = re.match(r"data:(image/[\w+.-]+);base64,(.+)$", data_url or "", re.S)
    if not m:
        raise MediaError("이미지 파일을 읽지 못했습니다.")
    if len(m.group(2)) > 30_000_000:
        raise MediaError("이미지가 너무 큽니다. 20MB 이하로 올려 주세요.")
    return save_bytes(base64.b64decode(m.group(2)), m.group(1))


def fetch_url(url: str, timeout: int = 25) -> str:
    if not re.match(r"https?://", url or ""):
        raise MediaError("잘못된 이미지 주소입니다.")
    req = urllib.request.Request(url, headers=UA)
    try:
        r_ctx = netguard.urlopen(req, timeout=timeout)
    except netguard.BlockedURL as e:
        raise MediaError(f"이 이미지 주소는 열 수 없습니다. ({e})")
    with r_ctx as r:
        mime = (r.headers.get_content_type() or "").lower()
        data = r.read(25_000_000)
    if mime not in EXT:
        mime = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else mime
    return save_bytes(data, mime)


def media_path(name: str) -> str:
    name = os.path.basename(name or "")
    p = os.path.join(MEDIA_DIR, name)
    return p if re.fullmatch(r"[0-9a-f]{20}\.(jpg|png|webp|gif|svg)", name) and os.path.isfile(p) else ""


def inline_media(html_str: str) -> str:
    """내보내기용: /media/파일 을 data URI로 바꿔 파일 하나로 동작하게 한다."""
    cache = {}

    def rep(m):
        name = m.group(2)
        if name not in cache:
            p = media_path(name)
            if not p:
                cache[name] = m.group(0)
            else:
                ext = os.path.splitext(name)[1]
                mime = {v: k for k, v in EXT.items()}[ext]
                with open(p, "rb") as f:
                    cache[name] = f"{m.group(1)}data:{mime};base64,{base64.b64encode(f.read()).decode()}"
        return cache[name]
    return re.sub(r"""((?:src=|url\()["']?)/media/([0-9a-f]{20}\.\w+)""", rep, html_str)


# ───────────────────────── 사진 검색 (Openverse) ─────────────────────────
PIXABAY_KEY = [""]  # 설정에 Pixabay 키가 있으면 app.py가 넣어 준다


def set_pixabay_key(key: str):
    PIXABAY_KEY[0] = (key or "").strip()


def _search_pixabay(q: str, count: int, wide: bool) -> list:
    params = {"key": PIXABAY_KEY[0], "q": q[:100], "image_type": "photo", "per_page": max(3, min(count, 60)),
              "safesearch": "true", "lang": "ko" if re.search(r"[가-힣]", q) else "en"}
    if wide:
        params["orientation"] = "horizontal"
    url = "https://pixabay.com/api/?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (400, 401, 403):
            raise MediaError("Pixabay 키가 올바르지 않습니다. ⚙️ 설정에서 확인해 주세요.")
        raise MediaError("Pixabay 사진 검색에 실패했습니다. 잠시 뒤 다시 시도해 주세요.")
    return [{"thumb": h.get("webformatURL"), "url": h.get("largeImageURL") or h.get("webformatURL"),
             "w": h.get("imageWidth", 0), "h": h.get("imageHeight", 0), "title": h.get("tags", ""),
             "source": "pixabay", "tags": [t.strip() for t in (h.get("tags") or "").split(",")]}
            for h in data.get("hits", [])]


def search_photos(query: str, count: int = 24, wide: bool = False) -> list:
    """출처 표기 없이 상업적으로 쓸 수 있는 사진만 검색. 반환: [{thumb, url, w, h, title, source, tags}]
    Pixabay 키가 있으면 Pixabay(빠름), 없으면 Openverse(CC0·퍼블릭 도메인, 처음 찾는 단어는 10~30초)"""
    q = (query or "").strip()
    if not q:
        return []
    if PIXABAY_KEY[0]:
        return _search_pixabay(q, count, wide)
    # Openverse가 느린 때가 많아 Wikimedia도 함께 찾는다. 한쪽이 먼저 나오면 다른 쪽은 조금만 기다린다
    ex = ThreadPoolExecutor(max_workers=2)
    f_ov, f_wm = ex.submit(_search_openverse, q, count, wide), ex.submit(_search_wikimedia, q, count)
    ex.shutdown(wait=False)
    wiki = []
    try:
        wiki = f_wm.result(timeout=20)
    except Exception:
        pass
    try:
        ov = f_ov.result(timeout=FREE_EXTRA_WAIT if wiki else 65)
    except FutureTimeout:
        ov = []
    except MediaError:
        if not wiki:
            raise
        ov = []
    return ov + [c for c in wiki if not wide or c["w"] >= c["h"]]


def _search_wikimedia(q: str, count: int) -> list:
    """Wikimedia Commons의 CC0·퍼블릭 도메인 사진 (출처 표기가 필요한 CC BY 등은 뺀다)."""
    params = {"action": "query", "generator": "search", "gsrsearch": f"{q} filetype:bitmap", "gsrnamespace": 6,
              "gsrlimit": min(count, 20), "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1280,
              "iiextmetadatafilter": "LicenseShortName", "format": "json"}
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
        pages = json.loads(r.read().decode("utf-8")).get("query", {}).get("pages", {})
    out = []
    for p in sorted(pages.values(), key=lambda x: x.get("index", 0)):
        ii = (p.get("imageinfo") or [{}])[0]
        lic = ((ii.get("extmetadata") or {}).get("LicenseShortName") or {}).get("value", "").lower()
        if not ("cc0" in lic or "public domain" in lic or lic.startswith("pd")):
            continue
        if ii.get("mime") not in ("image/jpeg", "image/png") or (ii.get("width") or 0) < 640:
            continue
        title = re.sub(r"[_\-]+", " ", re.sub(r"^File:|\.\w+$", "", p.get("title", "")))
        src = ii.get("thumburl") or ii.get("url")
        out.append({"thumb": src, "url": src, "w": ii.get("width") or 0, "h": ii.get("height") or 0,
                    "title": title[:80], "source": "wikimedia", "tags": []})
    return out


def _search_openverse(q: str, count: int, wide: bool) -> list:
    params = {"q": q, "license": "cc0,pdm", "page_size": min(count, 20), "mature": "false", "category": "photograph"}
    if wide:
        params["aspect_ratio"] = "wide"
    url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(params)
    data = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            raise MediaError("사진 검색 서버가 응답하지 않습니다. 잠시 뒤 다시 시도해 주세요.")
        except Exception:
            raise MediaError("사진 검색 서버가 너무 느립니다. 잠시 뒤 다시 시도하거나 ⚙️ 설정에 Pixabay 키를 넣어 주세요.")
    out = []
    for r in (data or {}).get("results", []):
        w, h = r.get("width") or 0, r.get("height") or 0
        if w and w < 640:
            continue
        out.append({"thumb": r.get("thumbnail") or r.get("url"), "url": r.get("url"), "w": w, "h": h,
                    "title": (r.get("title") or "")[:80], "source": r.get("source") or "",
                    "tags": [t.get("name", "") for t in (r.get("tags") or [])][:30]})
    # 현대적인 사진이 많은 출처, 높은 해상도, 가로 사진을 앞에
    pref = {"pixabay": 0, "rawpixel": 0, "stocksnap": 0, "flickr": 1, "nappy": 0}
    out.sort(key=lambda x: (pref.get(x["source"], 2), -(1 if x["w"] >= 1200 else 0), -(1 if x["w"] >= x["h"] else 0)))
    return out


def _shorter_queries(q: str) -> list:
    words = q.split()
    cands = [q, " ".join(words[:3]), " ".join(words[:2]), " ".join(words[-2:]), words[-1] if words else ""]
    seen, out = set(), []
    for c in cands:
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def search_photos_smart(query: str, count: int = 24, wide: bool = False) -> tuple:
    """결과가 없으면 검색어를 줄여 가며 다시 찾는다. 반환: (실제 검색어, 결과)"""
    for q in _shorter_queries(query):
        items = search_photos(q, count, wide)
        if items:
            return q, items
    return query, []


STOP = {"the", "and", "with", "for", "of", "in", "on", "at", "a", "an", "to", "photo", "image", "picture", "modern"}


def _stem(w: str) -> str:
    """charging·chargers·charge → charg 처럼 끝만 다른 단어를 같게 본다 (앞 5글자 비교는 elect=election 같은 오탐이 났음)"""
    for suf in ("ings", "ing", "ers", "er", "ies", "es", "ed", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def _query_words(query: str) -> list:
    return [w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 2 and w not in STOP]


def _hits(c: dict, query: str) -> int:
    """사진 제목·태그에 검색어 단어가 몇 개 들어 있는지 (단어 단위)"""
    text = (c.get("title", "") + " " + " ".join(c.get("tags", []))).lower()
    have = {_stem(w) for w in re.findall(r"[a-z]+", text)}
    return sum(1 for w in _query_words(query) if _stem(w) in have)


def _relevant(c: dict, query: str) -> bool:
    """AI가 사진을 볼 수 없을 때의 거르기: 3단어까지는 모두, 그 이상은 하나 빼고 다 맞아야 사용"""
    words = _query_words(query)
    if not words:
        return True
    return _hits(c, query) >= (len(words) if len(words) <= 3 else len(words) - 1)


# ───────────────────────── AI가 사진을 직접 보고 고르기 ─────────────────────────
# 태그는 엉터리가 많다 (electric bike 태그가 붙은 장애인 스쿠터, hospital corridor 태그의 앉은 남자 등).
# Gemini 키가 있으면 후보 몇 장의 작은 그림을 보여 주고 정말 그 장면인 것만 고르게 한다.
VISION_KEY = [""]  # 설정의 Gemini 키 (app.py가 넣어 준다). 없으면 글자 비교만 한다
VISION_MODELS = ("gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest")  # 무료 키는 lite가 자주 429
VISION_CANDS = 4


def set_vision_key(key: str):
    VISION_KEY[0] = (key or "").strip()


def _thumb_jpeg(url: str) -> bytes:
    with netguard.urlopen(urllib.request.Request(url, headers=UA), timeout=10) as r:
        data = r.read(4_000_000)
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((384, 384))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=80)
    return out.getvalue()


def _vision_pick(subject: str, cands: list):
    """후보 중 subject 장면을 분명히 보여 주는 사진의 번호(0부터)를 돌려준다.
    맞는 사진이 없으면 -1, AI 확인을 못 했으면 None (호출한 쪽이 글자 비교로 대신)."""
    key = VISION_KEY[0]
    if not key or not cands:
        return None
    with ThreadPoolExecutor(max_workers=len(cands)) as ex:
        thumbs = list(ex.map(lambda c: _safe(_thumb_jpeg, c.get("thumb") or c.get("url")), cands))
    shown = [(i, t) for i, t in enumerate(thumbs) if t]
    if not shown:
        return None
    parts = [{"text": (
        f'A presentation slide needs a photo of: "{subject}".\n'
        f"Below are {len(shown)} candidate photos, numbered 1 to {len(shown)}.\n"
        "Pick the photo that most clearly shows that subject as its main content. Be strict: a different kind of "
        "object (e.g. a mobility scooter instead of a bicycle, a phone without any payment for 'mobile payment'), "
        "a scene where an unrelated person is the main subject, a drawing, a document scan, or a blurry/very old "
        "photo does NOT match. Also reject advertisements, banners, posters, screenshots, product cutouts on a plain "
        "background, and photos with prominent text, logos or watermarks. Small differences in details are fine.\n"
        'Answer only JSON: {"best": <number>} or {"best": 0} if none clearly matches.')}]
    for n, (_, t) in enumerate(shown, 1):
        parts += [{"text": f"Photo {n}:"}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(t).decode()}}]
    res = _vision_json(key, parts, 64, lambda d: int(d.get("best", 0)))
    if res is None:
        return None
    return shown[res - 1][0] if 1 <= res <= len(shown) else -1


def _vision_json(key: str, parts: list, max_tokens: int, parse):
    """Gemini에 그림과 질문을 보내 JSON 답을 parse(dict)로 읽는다. 모든 모델이 실패하면 None."""
    payload = {"contents": [{"role": "user", "parts": parts}],
               "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens, "responseMimeType": "application/json",
                                    "thinkingConfig": {"thinkingBudget": 0}}}
    for model in VISION_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                res = json.loads(r.read().decode("utf-8"))
            text = "".join(p.get("text", "") for p in res["candidates"][0]["content"]["parts"])
            return parse(json.loads(text))
        except Exception as e:
            logger.info(f"그림 AI 확인 실패({model}): {str(e)[:80]}")
    return None


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None


_ov_sem = threading.Semaphore(4)  # Openverse 동시 요청 수 제한 (몰리면 다 같이 느려진다)
AI_HEDGE = 15  # 검색이 이 시간 안에 끝나지 않으면 AI 그림도 같이 준비한다
FREE_EXTRA_WAIT = 12  # Wikimedia 결과가 있으면 Openverse는 이만큼만 더 기다린다
SEARCH_WAIT = 40  # 검색으로 맞는 사진을 찾을 때까지 기다리는 최대 시간 (화면은 기다리지 않음)


class _Skip(Exception):
    pass


def _relevant_search(q: str) -> list:
    with _ov_sem:
        return [c for c in search_photos(q, 20, wide=True) if _relevant(c, q) and c.get("source") != "wikimedia"]


def _ranked_search(q: str) -> list:
    """AI 확인용 후보: 검색어 단어가 하나라도 맞는 사진을 많이 맞는 순으로 (같으면 검색 순서 유지)"""
    with _ov_sem:
        items = search_photos(q, 20, wide=True)
    scored = [(_hits(c, q), i, c) for i, c in enumerate(items)]
    return [c for h, i, c in sorted(scored, key=lambda x: (-x[0], x[1])) if h > 0]


def _search_and_fetch(qs: list) -> str:
    """긴 검색어부터 차례로 찾아 맞는 사진을 내려받는다. 없으면 ''.
    Gemini 키가 있으면 AI가 후보를 직접 보고 원래 검색어(qs[0]) 장면인지 확인한 사진만 쓴다."""
    subject = qs[0] if qs else ""
    for q in qs:
        try:
            if VISION_KEY[0]:
                ranked = _ranked_search(q)
                pick = _vision_pick(subject, ranked[:VISION_CANDS]) if ranked else -1
                if pick is None:  # AI 확인을 못 함 → 글자 비교로 (태그 없는 Wikimedia는 AI 확인 없이 쓰지 않음)
                    cands = [c for c in ranked if _relevant(c, q) and c.get("source") != "wikimedia"]
                elif pick < 0:
                    logger.info(f"사진 AI 확인: '{subject}' 맞는 사진 없음 (검색어 {q})")
                    continue
                else:
                    cands = [ranked[pick]]
            else:
                cands = _relevant_search(q)
        except Exception as e:
            logger.info(f"자동 사진 검색 실패({q}): {str(e)[:80]}")
            return ""
        for c in cands[:3]:
            try:
                return fetch_url(c["url"], timeout=15)
            except Exception:
                continue
    return ""


def auto_photo(query: str, allow_ai: bool = True) -> str:
    """키워드에 맞는 무료 사진을 찾아 저장하고 /media 주소를 돌려준다.
    검색이 실패하거나 AI_HEDGE초 안에 끝나지 않으면 AI 그림도 준비한다(무료 서버는 45초에 1장).
    AI 그림은 차례를 기다리는 사이 검색으로 사진을 찾으면 만들지 않는다. 모두 실패하면 ''."""
    words = query.split()
    qs = list(dict.fromkeys([query, " ".join(words[:3]), " ".join(words[:2])]))
    found, searched = threading.Event(), threading.Event()

    def _search():
        try:
            url = _search_and_fetch(qs)
            if url:
                found.set()
            return url
        finally:
            searched.set()

    ex = ThreadPoolExecutor(max_workers=2)
    f_search = ex.submit(_search)
    f_ai = None
    if allow_ai:
        def _ai():
            # 검색이 실패했거나 AI_HEDGE초가 지나도 못 찾았을 때만 무료 한도를 쓴다
            searched.wait(AI_HEDGE)
            if found.is_set():
                raise _Skip()
            return ai_image(query, "", "photo", skip=found.is_set)
        f_ai = ex.submit(_ai)
    ex.shutdown(wait=False)
    try:
        url = f_search.result(timeout=SEARCH_WAIT)
    except Exception:
        url = ""
    if url:
        return url
    if f_ai:
        try:
            return f_ai.result(timeout=200)
        except _Skip:
            pass  # 늦게나마 검색으로 찾았다
        except Exception as e:
            logger.warning(f"자동 AI 그림 실패({query}): {e}")
    if f_search.done():
        try:
            return f_search.result() or ""
        except Exception:
            pass
    return ""


class PhotoPrefetch:
    """슬라이드를 쓰는 도중에 data-photo 키워드가 나오면 바로 사진 찾기를 시작한다."""

    def __init__(self, max_photos: int = 4):
        self.max = max_photos
        self.ex = ThreadPoolExecutor(max_workers=max_photos)
        self.futs = {}

    def feed(self, text: str):
        for tag in re.findall(r"<section\b[^>]*>", text):
            m = re.search(r'data-photo="([^"]+)"', tag)
            if m and len(self.futs) < self.max:
                q = _html.unescape(m.group(1))
                if q not in self.futs:
                    self.futs[q] = self.ex.submit(auto_photo, q)

    def get(self, q: str):
        return self.futs.get(q)

    def ensure(self, qs: list) -> dict:
        """qs 각각에 대해 사진 찾기가 돌고 있게 하고 {검색어: future}를 돌려준다."""
        for q in qs:
            if q not in self.futs:
                self.futs[q] = self.ex.submit(auto_photo, q)
        return {q: self.futs[q] for q in qs}


# ───────────────────────── AI 그림 ─────────────────────────
POLL_GAP = 46  # 무료 한도: IP당 45초에 1장 (2026-10 확인)
_poll_lock = threading.Lock()
_poll_next = [0.0]
_poll_waiting = [0]  # 무료 서버 차례를 기다리는 요청 수


def _gemini_image(api_key: str, prompt: str) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}}
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    for c in d.get("candidates") or []:
        for p in (c.get("content") or {}).get("parts") or []:
            inl = p.get("inlineData") or p.get("inline_data")
            if inl and inl.get("data"):
                return base64.b64decode(inl["data"])
    raise MediaError("Gemini가 그림을 돌려주지 않았습니다.")


def _take_poll_slot(skip=None):
    """무료 AI 그림 서버 차례를 기다린다(한 번에 한 장, 끝난 뒤 POLL_GAP초 간격).
    기다리는 동안 skip()이 참이 되면 차례를 잡지 않고 빠진다."""
    with _poll_lock:
        _poll_waiting[0] += 1
    try:
        while True:
            with _poll_lock:
                wait = _poll_next[0] - time.time()
                if wait <= 0:
                    if skip and skip():
                        raise _Skip()
                    _poll_next[0] = time.time() + 600  # 진행 중에는 다른 요청이 못 들어오게
                    return
            if skip and skip():
                raise _Skip()
            time.sleep(min(wait, 0.5))
    finally:
        with _poll_lock:
            _poll_waiting[0] -= 1


def _release_poll_slot(gap: float):
    with _poll_lock:
        _poll_next[0] = time.time() + gap


def _pollinations(prompt: str, w: int = 1280, h: int = 720, skip=None) -> bytes:
    crop = 0.08  # 무료 생성은 아래쪽에 로고가 찍혀서 더 길게 만든 뒤 잘라낸다
    gen_h = int(round(h / (1 - crop)))
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width={w}&height={gen_h}&nologo=true&seed={random.randint(1, 999999)}&model=flux")
    data = None
    for attempt in range(4):
        _take_poll_slot(skip)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                data = r.read()
            _release_poll_slot(POLL_GAP)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:400]
            m = re.search(r"[Rr]etry after (\d+)\s*s", body)
            _release_poll_slot(int(m.group(1)) + 1 if m else POLL_GAP)
            if e.code in (402, 429, 503) and attempt < 3:  # 503 = 무료 서버 전체가 붐빔 (Retry after 10s)
                continue
            raise MediaError("무료 AI 그림 서버가 바쁩니다. 잠시 뒤 다시 시도해 주세요.")
        except Exception:
            _release_poll_slot(POLL_GAP)
            raise
    if data is None:
        raise MediaError("무료 AI 그림 서버가 바쁩니다. 잠시 뒤 다시 시도해 주세요.")
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    iw, ih = im.size
    im = im.crop((0, 0, iw, int(ih * (1 - crop))))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=90)
    return out.getvalue()


# ── AI 그림 속 글자 없애기 ──
# 생성 모델은 "No text"라고 해도 간판·화면·옷에 엉터리 글자나 로고 비슷한 것을 그려 넣곤 한다.
# Gemini 키가 있으면 그림을 보여 주고 주인공·글자 위치를 받아서, 주인공을 살린 채 글자만 잘라낼 수 있으면 자르고
# 아니면 한 번 다시 만든다. 그래도 남으면 글자가 가장 적은 그림의 작은 글자만 흐리게 한다.
TEXT_RETRIES = 1  # 다시 만드는 횟수 (무료 서버는 한 번에 46초가 더 걸려서 다른 그림이 기다리는 중이면 건너뛴다)
TEXT_MIN_KEEP = 0.5  # 잘라낸 뒤 남아야 하는 넓이 비율
BLUR_MAX_AREA = 0.02  # 이보다 넓은 글자는 흐리면 뿌연 얼룩이 더 눈에 띄어서 그대로 둔다


def _find_text(data: bytes):
    """(주인공 상자 또는 None, 글자 상자 목록). 상자는 (y0, x0, y1, x1) 0~1 비율. 확인을 못 했으면 None."""
    key = VISION_KEY[0]
    if not key:
        return None
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    # 그림을 먼저, Gemini가 익숙한 box_2d 형식으로 물어야 위치가 정확하다 (다른 형식은 엉뚱한 곳을 짚었다)
    parts = [{"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
             {"text": (
                 "1) Detect the main subject of the image. 2) Detect every piece of visible text in the image: "
                 "letters, words, numbers, logos, watermarks, and garbled pseudo-text on signs, screens, labels, "
                 "products or clothing. Ignore patterns that are not writing.\n"
                 'Output JSON: {"subject": {"box_2d": [ymin, xmin, ymax, xmax]}, "text": [{"box_2d": [ymin, xmin, '
                 'ymax, xmax]}, ...]} normalized to 0-1000, at most 8 text entries, "text": [] if there is no text.')}]

    def box(b):
        y0, x0, y1, x1 = (min(max(float(v) / 1000, 0.0), 1.0) for v in b[:4])
        return (y0, x0, y1, x1) if y1 > y0 and x1 > x0 else None

    def parse(d):
        subj = d.get("subject") or {}
        subj = box(subj.get("box_2d") or []) if isinstance(subj, dict) and subj.get("box_2d") else None
        texts = [box(e.get("box_2d") or []) for e in d.get("text") or [] if isinstance(e, dict) and e.get("box_2d")]
        return subj, [b for b in texts if b]
    return _vision_json(key, parts, 512, parse)


def _text_area(boxes: list) -> float:
    return sum((y1 - y0) * (x1 - x0) for y0, x0, y1, x1 in boxes)


def _crop_out_text(data: bytes, boxes: list, subject=None):
    """주인공을 품고 글자 상자는 모두 피하는 가장 넓은 가로형 영역으로 자른다. 너무 많이 잘려야 하면 None."""
    if not boxes or len(boxes) > 4:
        return None
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    W, H = im.size
    m = 0.02  # 글자 둘레 여유
    boxes = [(max(y0 - m, 0), max(x0 - m, 0), min(y1 + m, 1), min(x1 + m, 1)) for y0, x0, y1, x1 in boxes]
    if subject:  # 주인공 상자는 넉넉하게 잡히는 편이라 둘레 10%까지는 잘려도 된다
        sy0, sx0, sy1, sx1 = subject
        dy, dx = (sy1 - sy0) * 0.1, (sx1 - sx0) * 0.1
        subject = (sy0 + dy, sx0 + dx, sy1 - dy, sx1 - dx)
    best = None

    def holds(y0, x0, y1, x1):
        return not subject or (y0 <= subject[0] and x0 <= subject[1] and y1 >= subject[2] and x1 >= subject[3])

    def walk(i, r):
        nonlocal best
        y0, x0, y1, x1 = r
        if y1 <= y0 or x1 <= x0 or not holds(*r):
            return
        if i == len(boxes):
            w, h = (x1 - x0) * W, (y1 - y0) * H
            cy, cx = ((subject[0] + subject[2]) / 2, (subject[1] + subject[3]) / 2) if subject else \
                ((y0 + y1) / 2, (x0 + x1) / 2)
            if w / h > 2.0:  # 너무 길쭉하면 주인공을 가운데에 두고 2:1로
                nw = h * 2.0 / W
                nx0 = min(max(cx - nw / 2, x0), x1 - nw)
                x0, x1 = nx0, nx0 + nw
            elif w / h < 1.2:  # 슬라이드 사진 칸에 쓰기엔 너무 세로형이면 1.2:1로
                nh = w / 1.2 / H
                ny0 = min(max(cy - nh / 2, y0), y1 - nh)
                y0, y1 = ny0, ny0 + nh
            area = (x1 - x0) * (y1 - y0)
            if area >= TEXT_MIN_KEEP and holds(y0, x0, y1, x1) and (best is None or area > best[0]):
                best = (area, (x0, y0, x1, y1))
            return
        b0, a0, b1, a1 = boxes[i]
        walk(i + 1, (y0, x0, min(y1, b0), x1))  # 글자 위쪽만 남기기
        walk(i + 1, (max(y0, b1), x0, y1, x1))  # 아래쪽
        walk(i + 1, (y0, x0, y1, min(x1, a0)))  # 왼쪽
        walk(i + 1, (y0, max(x0, a1), y1, x1))  # 오른쪽

    walk(0, (0.0, 0.0, 1.0, 1.0))
    if not best:
        return None
    x0, y0, x1, y1 = best[1]
    im = im.crop((round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=90)
    return out.getvalue()


def _blur_text(data: bytes, boxes: list) -> bytes:
    """잘라낼 수도, 다시 만들 수도 없을 때 마지막 수단으로 작은 글자 부분만 흐리게 한다.
    상자 안만 따로 흐리면 회색 네모가 되므로, 그림 전체를 흐린 판을 경계가 부드러운 마스크로 겹친다."""
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.open(io.BytesIO(data)).convert("RGB")
    W, H = im.size
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    short = min(min((y1 - y0) * H, (x1 - x0) * W) for y0, x0, y1, x1 in boxes)
    pad = max(4, int(short * 0.3))
    for y0, x0, y1, x1 in boxes:
        d.rectangle((x0 * W - pad, y0 * H - pad, x1 * W + pad, y1 * H + pad), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(pad))
    blurred = im.filter(ImageFilter.GaussianBlur(min(20, max(4, short / 3))))
    im = Image.composite(blurred, im, mask)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=90)
    return out.getvalue()


def _make_image(full: str, api_key: str, skip=None, maker=None) -> tuple:
    """(그림, 형식, 무료 서버로 만들었는지). maker 가 있으면(ChatGPT 구독 그림 등) 먼저 쓴다."""
    if maker:
        try:
            data = maker(full)
            mime = "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
            return data, mime, False
        except Exception as e:
            logger.info(f"구독 그림 생성 실패, 다른 방법으로 전환: {str(e)[:100]}")
    if api_key:
        try:
            return _gemini_image(api_key, full), "image/png", False
        except Exception as e:
            logger.info(f"Gemini 그림 생성 불가, 무료 생성으로 전환: {str(e)[:100]}")
    return _pollinations(full, skip=skip), "image/jpeg", True


def ai_image(prompt: str, api_key: str = "", style: str = "photo", skip=None, maker=None) -> str:
    styles = {"photo": "professional photograph, natural light, high detail",
              "illust": "clean flat vector illustration, soft colors, minimal",
              "3d": "soft 3D render, clay style, studio lighting, minimal background"}
    full = (f"{prompt}. {styles.get(style, styles['photo'])}. Unbranded objects, blank surfaces, no signage, "
            "no captions. No text, no letters, no numbers, no watermark, no logo.")
    best = None  # 지금까지 글자가 가장 적은 (글자 넓이, 그림, 형식, 글자 상자)
    for attempt in range(TEXT_RETRIES + 1):
        try:
            data, mime, free = _make_image(full, api_key, skip, maker if attempt == 0 else None)
        except _Skip:
            raise  # 그사이 검색으로 사진을 찾았다
        except Exception:
            if best:  # 다시 만들기가 실패하면 앞서 만든 그림으로 마무리
                break
            raise
        found = _find_text(data)
        if found is None or not found[1]:  # 글자 없음, 또는 키가 없어 확인 못 함
            return save_bytes(data, mime)
        subject, boxes = found
        cropped = _crop_out_text(data, boxes, subject)
        if cropped:
            logger.info(f"AI 그림 글자 {len(boxes)}곳을 잘라냄({prompt[:40]})")
            return save_bytes(cropped, "image/jpeg")
        logger.info(f"AI 그림에 글자 {len(boxes)}곳({prompt[:40]}), 시도 {attempt + 1}")
        if best is None or _text_area(boxes) < best[0]:
            best = (_text_area(boxes), data, mime, boxes)
        if free and _poll_waiting[0]:  # 다른 그림이 무료 서버 차례를 기다리면 다시 만들지 않는다
            break
    area, data, mime, boxes = best
    if area <= BLUR_MAX_AREA:
        logger.info(f"AI 그림 글자를 흐리게 처리({prompt[:40]})")
        return save_bytes(_blur_text(data, boxes), "image/jpeg")
    return save_bytes(data, mime)


# ───────────────────────── 아이콘 ─────────────────────────
_icons = None


def icons() -> dict:
    global _icons
    if _icons is None:
        with open(ICONS_FILE, encoding="utf-8") as f:
            _icons = json.load(f)
    return _icons


def icon_svg(name: str) -> str:
    body = icons()["icons"].get(name)
    if not body:
        return ""
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>')


def curated_icon_names() -> list:
    return [c["n"] for c in icons()["curated"]]


def expand_icons(html_str: str) -> str:
    """AI가 쓴 <i data-icon="이름"></i> 를 실제 SVG 아이콘으로 바꾼다. 모르는 이름은 지운다."""
    def rep(m):
        svg = icon_svg(m.group(1).strip())
        return f'<span class="g-ico" data-icon="{_html.escape(m.group(1).strip())}">{svg}</span>' if svg else ""
    return re.sub(r'<i\b[^>]*data-icon="([^"]+)"[^>]*>\s*</i>', rep, html_str)


def apply_photo(slides_html: str, q: str, url: str) -> str:
    """data-photo="q" 표시가 달린 슬라이드에 사진(url)을 오른쪽 사진 패널로 넣는다.
    url이 비어 있으면 표시만 지운다. 표시가 없으면(삭제·수정된 장) 그대로 둔다."""
    for tag in re.findall(r"<section\b[^>]*>", slides_html):
        m = re.search(r'data-photo="([^"]+)"', tag)
        if not m or _html.unescape(m.group(1)) != q:
            continue
        new_tag = re.sub(r'\sdata-photo="[^"]*"', "", tag)
        if url:
            new_tag = re.sub(r'class="([^"]*)"', lambda mm: f'class="{mm.group(1)} with-photo"', new_tag, count=1)
            new_tag += f'\n  <figure class="g-photo"><img src="{url}" alt="{_html.escape(q)}"></figure>'
        return slides_html.replace(tag, new_tag, 1)
    return slides_html


def strip_photo_marks(slides_html: str, keep=()) -> str:
    """keep에 없는 data-photo 표시를 지운다."""
    def rep(m):
        return m.group(0) if _html.unescape(m.group(1)) in keep else ""
    return re.sub(r'\sdata-photo="([^"]*)"', rep, slides_html)


def photo_queries(slides_html: str, max_photos: int = 4) -> list:
    out = []
    for tag in re.findall(r"<section\b[^>]*>", slides_html):
        m = re.search(r'data-photo="([^"]+)"', tag)
        if m:
            q = _html.unescape(m.group(1))
            if q not in out and len(out) < max_photos:
                out.append(q)
    return out


def resolve_photos(slides_html: str, max_photos: int = 4, prefetch: "PhotoPrefetch" = None) -> str:
    """data-photo="영문 키워드" 가 달린 슬라이드에 사진을 찾아 넣는다 (다 찾을 때까지 기다림).
    prefetch가 있으면 미리 시작한 사진 찾기 결과를 그대로 쓴다."""
    qs = photo_queries(slides_html, max_photos)
    if not qs:
        return slides_html
    ex = ThreadPoolExecutor(max_workers=max_photos)
    futs = [(prefetch.get(q) if prefetch else None) or ex.submit(auto_photo, q) for q in qs]
    deadline = time.time() + 60  # 사진 때문에 생성이 너무 길어지지 않게
    for q, f in zip(qs, futs):
        try:
            url = f.result(timeout=max(1, deadline - time.time()))
        except Exception:
            url = ""
        slides_html = apply_photo(slides_html, q, url)
    ex.shutdown(wait=False, cancel_futures=True)
    return strip_photo_marks(slides_html)
