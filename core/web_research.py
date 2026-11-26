"""키 없이 쓰는 무료 웹 조사 (조사 모드).

구글 뉴스 RSS + DuckDuckGo HTML + 위키백과 API 로 자료를 모으고, 상위 몇 개 페이지는 본문까지 읽어
'[최신 조사 자료]' 에 넣을 글과 출처 목록을 만든다. AI(Gemini·구독 CLI)와 무관하게 동작해서
구글 검색 연동이 막힌 무료 키나 구독 로그인 방식에서도 최신 자료를 쓸 수 있다.
짧은 시간에 요청을 몰아 보내지 않도록 요청 수를 작게 유지한다.
"""
import html as _html
import logging
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from core import netguard
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

logger = logging.getLogger("web_research")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_NEWS = 8          # 뉴스 제목·요약
MAX_WEB = 6           # 일반 검색 결과
MAX_PAGES = 3         # 본문까지 읽을 페이지 수
PAGE_CHARS = 2500     # 페이지당 본문 글자 수
TOTAL_CHARS = 14000   # 조사 자료 전체 상한
TIMEOUT = 12


def _get(url: str, timeout: int = TIMEOUT, limit: int = 600_000) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko,en;q=0.8"})
    with netguard.urlopen(req, timeout=timeout) as r:   # 검색 결과 주소가 내부망을 가리켜도 열지 않는다
        return r.read(limit)


def _decode(raw: bytes, content_type_hint: str = "") -> str:
    m = re.search(rb'charset=["\']?([A-Za-z0-9_-]+)', raw[:3000], re.I)
    for enc in ([m.group(1).decode("ascii", "ignore")] if m else []) + ["utf-8", "cp949"]:
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")


def _strip(s: str) -> str:
    s = re.sub(r"<(script|style|noscript|svg|nav|footer|header|aside|form)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t ]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def google_news(query: str, n: int = MAX_NEWS) -> list:
    """구글 뉴스 RSS. [{title, uri, snippet, date, source}]"""
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
    root = ET.fromstring(_get(url))
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src = (it.findtext("source") or "").strip()
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3]
        date = ""
        try:
            date = parsedate_to_datetime(it.findtext("pubDate") or "").strftime("%Y-%m-%d")
        except Exception:
            pass
        out.append({"title": title, "uri": (it.findtext("link") or "").strip(),
                    "snippet": "", "date": date, "source": src})
        if len(out) >= n:
            break
    return out


def duckduckgo(query: str, n: int = MAX_WEB) -> list:
    """DuckDuckGo HTML 검색. [{title, uri, snippet}]"""
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query, "kl": "kr-kr"})
    page = _decode(_get(url))
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)',
                         page, re.S):
        href, title, rest = m.group(1), _strip(m.group(2)), m.group(3)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        link = urllib.parse.unquote(q["uddg"][0]) if "uddg" in q else href
        if link.startswith("//"):
            link = "https:" + link
        if not link.startswith("http") or "duckduckgo.com/y.js" in link:
            continue
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.S)
        out.append({"title": title, "uri": link, "snippet": _strip(sn.group(1)) if sn else ""})
        if len(out) >= n:
            break
    return out


def wikipedia(query: str, n: int = 2) -> list:
    """한국어 위키백과 앞부분 요약. [{title, uri, snippet}]"""
    url = "https://ko.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": query, "gsrlimit": n, "prop": "extracts",
        "exintro": 1, "explaintext": 1, "exlimit": n, "format": "json", "formatversion": 2})
    import json
    data = json.loads(_get(url))
    out = []
    for p in sorted((data.get("query") or {}).get("pages") or [], key=lambda p: p.get("index", 0)):
        text = (p.get("extract") or "").strip()
        title = p["title"].replace(" ", "")
        if text and len(title) >= 2 and title in query.replace(" ", ""):   # 주제에 이름이 나온 문서만(엉뚱한 검색 결과 제외)
            out.append({"title": p["title"], "uri": "https://ko.wikipedia.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_")),
                        "snippet": text[:700]})
    return out


def page_text(url: str, chars: int = PAGE_CHARS) -> str:
    """페이지 본문 추출(간단 방식). 실패하면 빈 글."""
    try:
        raw = _get(url, timeout=10, limit=900_000)
    except Exception:
        return ""
    page = _decode(raw)
    m = re.search(r"<article\b.*?</article>", page, re.S | re.I)
    body = _strip(m.group(0) if m else page)
    lines = [ln.strip() for ln in body.split("\n") if len(ln.strip()) >= 40]   # 메뉴·짧은 줄 제외
    return " ".join(lines)[:chars]


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception as e:
        logger.warning(f"조사 실패 {fn.__name__}: {e}")
        return []


def _clean_query(topic: str) -> str:
    q = re.sub(r"\s+", " ", topic or "").strip()
    return q[:80]


def research(topic: str, today: str = "") -> dict:
    """주제로 웹을 조사해 {text, sources, ok} 를 돌려준다. 아무것도 못 모으면 text 가 빈 글."""
    q = _clean_query(topic)
    if not q:
        return {"text": "", "sources": [], "ok": False}
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_news, f_web, f_wiki = ex.submit(_safe, google_news, q), ex.submit(_safe, duckduckgo, q), ex.submit(_safe, wikipedia, q)
        news, web, wiki = f_news.result(), f_web.result(), f_wiki.result()

    # 본문을 읽을 페이지: 일반 검색 결과 위주(뉴스 링크는 구글 리디렉션이라 본문 추출이 어렵다)
    targets = [w for w in web if "wikipedia.org" not in w["uri"]][:MAX_PAGES]
    with ThreadPoolExecutor(max_workers=3) as ex:
        bodies = list(ex.map(lambda w: page_text(w["uri"]), targets))

    lines, sources = [], []
    if today:
        lines.append(f"(수집일 {today}. 아래는 인터넷 검색으로 모은 자료이며 기사 날짜·출처를 함께 적었다. 공공기관·언론·연구기관 수치를 우선하고, 개인 블로그 수치는 교차 확인되는 것만 쓴다.)")
    if news:
        lines.append("\n■ 최근 뉴스 (제목 · 날짜 · 매체)")
        for it in news:
            lines.append(f"- {it['title']} ({it['date'] or '날짜 미상'}, {it['source'] or '매체 미상'})")
            sources.append({"title": f"{it['title']} — {it['source']}".strip(" —"), "uri": it["uri"]})
    for it, body in zip(targets, bodies):
        lines.append(f"\n■ {it['title']} ({it['uri']})")
        lines.append(body or it["snippet"])
        sources.append({"title": it["title"], "uri": it["uri"]})
    for it in web:
        if it in targets or not it["snippet"]:
            continue
        lines.append(f"\n■ {it['title']} ({it['uri']})\n{it['snippet']}")
        sources.append({"title": it["title"], "uri": it["uri"]})
    for it in wiki:
        lines.append(f"\n■ 위키백과 · {it['title']}\n{it['snippet']}")
        sources.append({"title": f"위키백과: {it['title']}", "uri": it["uri"]})
    text = "\n".join(lines).strip()
    if len(text) > TOTAL_CHARS:
        text = text[:TOTAL_CHARS].rsplit("\n", 1)[0]
    ok = bool(news or web or wiki)
    logger.info(f"웹 조사: 뉴스 {len(news)} · 검색 {len(web)} · 본문 {sum(1 for b in bodies if b)} · 위키 {len(wiki)}")
    # 출처가 너무 많으면 슬라이드 맨 뒤 '참고 자료'가 길어지므로 8개로 제한
    sources.sort(key=lambda x: "news.google.com" in x["uri"])   # 구글 뉴스 중계 주소는 뒤로
    return {"text": text if ok else "", "sources": sources[:8], "ok": ok}
