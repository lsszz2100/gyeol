"""슬라이드 한 장 단위 편집: 나누기/합치기, 안전 정리, 대본 바꾸기."""
import html as _html
import re

SECTION_RE = re.compile(r"<section\b[^>]*class=\"[^\"]*\bslide\b[^\"]*\"[^>]*>.*?</section>", re.S | re.I)
NOTES_RE = re.compile(r"<aside\b[^>]*class=\"[^\"]*\bnotes\b[^\"]*\"[^>]*>.*?</aside>", re.S | re.I)


def split_slides(slides_html: str) -> list:
    return [s.strip() for s in SECTION_RE.findall(slides_html or "")]


def join_slides(slides: list) -> str:
    return "\n\n".join(slides)


def sanitize_section(sec: str) -> str:
    """사용자·AI가 보낸 슬라이드 HTML을 한 장짜리 <section>으로 정리하고 위험한 요소를 걷어낸다."""
    m = SECTION_RE.search(sec or "")
    if not m:
        raise ValueError("슬라이드 형식이 올바르지 않습니다.")
    s = m.group(0)
    s = re.sub(r"<(script|style|iframe|object)\b.*?</\1\s*>", "", s, flags=re.S | re.I)
    s = re.sub(r"<(script|style|iframe|object|embed|link|meta)\b[^>]*>", "", s, flags=re.I)
    s = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", s, flags=re.I)
    s = re.sub(r"(href|src)\s*=\s*([\"'])\s*javascript:[^\"']*\2", r'\1="#"', s, flags=re.I)
    s = re.sub(r"\s(contenteditable|spellcheck|data-ep|data-fit-fs|data-gobj|draggable)(=\"[^\"]*\")?", "", s, flags=re.I)
    s = re.sub(r"\s*<span class=\"__gh\"[^>]*></span>", "", s).replace(" __gsel", "")
    # 슬라이드 설정(바닥글·로고)은 미리보기 때 붙는 것이므로 저장본에서는 뺀다
    s = re.sub(r"<div class=\"g-footer\">.*?</div>", "", s, flags=re.S)
    s = re.sub(r"<img class=\"g-logo\"[^>]*>", "", s)
    return s


def set_notes(sec: str, text: str) -> str:
    text = (text or "").strip()
    sec = NOTES_RE.sub("", sec)
    if not text:
        return sec
    body = _html.escape(text).replace("\n", "<br>")
    return re.sub(r"</section>\s*$", f"  <aside class=\"notes\">{body}</aside>\n</section>", sec.rstrip())


def title_of(sec: str) -> str:
    m = re.search(r'data-title="([^"]*)"', sec)
    return _html.unescape(m.group(1)) if m else ""


def refresh_toc(slides: list, make_toc) -> list:
    """목차 슬라이드(data-kind="toc")가 있으면 현재 슬라이드 제목으로 다시 만든다."""
    ti = next((i for i, s in enumerate(slides) if 'data-kind="toc"' in s), -1)
    if ti < 0:
        return slides
    titles = []
    for i, s in enumerate(slides):
        if i == 0 or i == ti or re.search(r'data-kind="(toc|divider|closing)"', s):
            continue
        t = title_of(s).strip()
        if t and t not in ("참고 자료", "Sources", "References"):
            titles.append(t)
    lang = "en" if 'data-title="Contents"' in slides[ti] else "ko"
    new = make_toc(titles, lang)
    if new:
        slides[ti] = new
    return slides
