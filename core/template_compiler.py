"""
결(GYEOL) - 템플릿 컴파일러 및 단일 파일 번들러
HTML PPT 슬라이드, 테마, 한국어 폰트, 애니메이션, 발표자 모드 런타임을 하나로 통합합니다.
"""

import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CSS_DIR = os.path.join(STATIC_DIR, "css")
JS_DIR = os.path.join(STATIC_DIR, "js")
THEMES_DIR = os.path.join(CSS_DIR, "themes")

import hashlib
import json as _json

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "themes.json"), encoding="utf-8") as _f:
    AVAILABLE_THEMES = _json.load(_f)
THEME_IDS = {t["id"] for t in AVAILABLE_THEMES}
THEME_STYLE = {t["id"]: t.get("style", "") for t in AVAILABLE_THEMES}
try:        # 예전 버전에서 저장한 테마 이름 → 지금 테마 (이름의 해시로 찾음)
    with open(os.path.join(_HERE, "theme_legacy.json"), encoding="utf-8") as _f:
        _LEGACY = _json.load(_f)
except (OSError, ValueError):
    _LEGACY = {}


def canon_theme(theme_id: str, default: str = "pitch-deck-vc") -> str:
    """저장된 테마 이름을 지금 테마 이름으로. 없는 테마면 default."""
    if theme_id in THEME_IDS:
        return theme_id
    return _LEGACY.get(hashlib.sha1(str(theme_id or "").encode()).hexdigest()[:12], default)

# 스타일별 슬라이드 번호가 들어 있는 가상 요소와 '번호 끄기' 처리
NUM_OFF = {
    "magazine": "::before{display:none!important}",
    "newspaper": "::before{content:'THE DAILY'!important}",
    "dashboard": "::after{content:'● LIVE'!important}",
    "window": "::after{content:'▶ PRESENTATION'!important}",
    "memphis": None, "zen": None,
}

DEFAULT_DISPLAY = {"numbers": True, "cover_number": False, "progress": True, "footer": "",
                   "logo": "", "logo_pos": "tr", "transition": "slide", "motion": "subtle"}


def display_css_html(theme_id: str, display: dict):
    """표시 설정을 CSS와 각 슬라이드에 넣을 HTML 조각으로 바꾼다."""
    d = dict(DEFAULT_DISPLAY, **(display or {}))
    style = THEME_STYLE.get(theme_id, "")
    off = NUM_OFF.get(style, "::after{display:none!important}")
    css = []
    if off:
        if not d["numbers"]:
            css.append(".slide" + off)
        elif not d["cover_number"]:
            css.append(".slide:first-of-type" + off)
    if not d["progress"]:
        css.append(".progress-bar{display:none!important}")
    if d["transition"] == "none":
        css.append(".slide{transition:none!important;transform:none!important}")
    elif d["transition"] == "fade":
        css.append(".slide{transform:none!important}")
    elif d["transition"] == "zoom":   # 확대(플라이스루): 다음 장이 앞으로 다가오며 나타남
        css.append(".slide{transform:scale(1.08)}.slide.is-active{transform:scale(1)}.slide.is-prev{transform:scale(.92)}"
                   ".slide{transition:opacity .6s var(--ease),transform .6s var(--ease)}")
    elif d["transition"] == "wipe":   # 닦아내기: 다음 장이 왼쪽부터 드러남
        css.append(".slide{transform:none;clip-path:inset(0 100% 0 0);transition:clip-path .7s var(--ease),opacity .01s}"
                   ".slide.is-active{clip-path:inset(0 0 0 0)}.slide.is-prev{clip-path:inset(0 0 0 0);opacity:1;z-index:1}")
    elif d["transition"] == "cover":  # 덮기: 다음 장이 아래에서 올라와 덮음
        css.append(".slide{transform:translateY(100%);transition:transform .7s var(--ease),opacity .01s}"
                   ".slide.is-active{transform:none}.slide.is-prev{transform:none;opacity:1;z-index:1}")
    elif d["transition"] == "push":   # 밀어내기(크게): 앞 장을 옆으로 밀어냄
        css.append(".slide{transform:translateX(100%);opacity:1;transition:transform .7s var(--ease)}"
                   ".slide.is-active{transform:none}.slide.is-prev{transform:translateX(-100%)}")
    css.append(":root{--gyeol-motion:%s}" % ({"none": "none", "rich": "rich"}.get(d.get("motion"), "subtle")))
    css.append(".g-footer{position:absolute;left:0;right:0;bottom:22px;text-align:center;font-size:14px;letter-spacing:.06em;color:var(--text-3);z-index:3;pointer-events:none}")
    pos = {"tl": "top:30px;left:40px", "tr": "top:30px;right:40px", "bl": "bottom:30px;left:40px", "br": "bottom:30px;right:40px"}
    css.append(".g-logo{position:absolute;%s;height:44px;max-width:220px;object-fit:contain;z-index:4;pointer-events:none}" % pos.get(d["logo_pos"], pos["tr"]))
    snippet = ""
    if d["footer"]:
        import html as _h
        snippet += f'<div class="g-footer">{_h.escape(str(d["footer"])[:80])}</div>'
    logo = str(d.get("logo") or "")
    if logo.startswith("data:image/"):
        snippet += f'<img class="g-logo" src="{logo}" alt="">'
    return "\n".join(css), snippet

# 한국어 폰트 옵션
AVAILABLE_FONTS = [
    {"id": "theme", "name": "테마 기본 서체", "family": "", "desc": "테마마다 어울리는 서체를 자동 적용"},
    {"id": "pretendard", "name": "프리텐다드 (Pretendard)", "family": "'Pretendard Variable', Pretendard, sans-serif", "desc": "가독성 1위 대한민국 표준 고딕"},
    {"id": "gmarket", "name": "G마켓 산스 (Gmarket Sans)", "family": "'GmarketSansBold', 'Pretendard Variable', sans-serif", "desc": "강렬하고 트렌디한 헤드라인/타이틀"},
    {"id": "spoqa", "name": "스포카 한 산스 (Spoqa Han Sans)", "family": "'Spoqa Han Sans Neo', sans-serif", "desc": "숫자/데이터/지표 정렬에 최적화"},
    {"id": "chosun", "name": "조선일보명조 (Chosunilbo Myungjo)", "family": "'Chosunilbo_myungjo', serif", "desc": "신뢰감 있는 클래식 에디토리얼 명조"},
    {"id": "nanum_neo", "name": "나눔스퀘어 네오 (NanumSquare Neo)", "family": "'NanumSquareNeo-Variable', sans-serif", "desc": "모던하고 직선적인 IT/스타트업체"},
    {"id": "jua", "name": "배달의민족 주아 (BM Jua)", "family": "'BMJUA', sans-serif", "desc": "친근하고 귀여운 카드뉴스/캐주얼 포인트"},
]


def get_theme_css(theme_id: str) -> str:
    """테마 CSS 파일 내용을 반환합니다."""
    theme_file = os.path.join(THEMES_DIR, f"{theme_id}.css")
    if os.path.exists(theme_file):
        with open(theme_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def compile_slide_deck(
    slides_html: str,
    title: str = "결 프레젠테이션",
    theme_id: str = "swiss-grid",
    font_id: str = "pretendard",
    inline_all: bool = False,
    extra_css: str = "",
    display: dict = None,
) -> str:
    """
    슬라이드 HTML과 런타임, 스타일을 병합하여 완전한 프레젠테이션 HTML을 생성합니다.
    inline_all=True 시 인터넷 연결 없이 오프라인 단일 파일로 동작하도록 모든 CSS/JS를 인라인 삽입합니다.
    """
    # 폰트 패밀리 결정
    theme_id = canon_theme(theme_id)
    disp_css, disp_html = display_css_html(theme_id, display)
    extra_css = (extra_css or "") + "\n" + disp_css
    if disp_html:
        slides_html = slides_html.replace("</section>", disp_html + "</section>")
    selected_font = next((f for f in AVAILABLE_FONTS if f["id"] == font_id), AVAILABLE_FONTS[0])
    font_family = selected_font["family"]
    font_override_css = ""
    if font_family:  # '테마 기본 서체'가 아니면 사용자가 고른 서체로 덮어쓰기
        font_override_css = f":root{{--font-sans:{font_family};--font-display:{font_family};}}"

    if inline_all:
        # 모든 정적 에셋 파일 인라인 로드
        with open(os.path.join(CSS_DIR, "fonts.css"), "r", encoding="utf-8") as f:
            fonts_css = f.read()
        with open(os.path.join(CSS_DIR, "base.css"), "r", encoding="utf-8") as f:
            base_css = f.read()
        with open(os.path.join(CSS_DIR, "animations.css"), "r", encoding="utf-8") as f:
            anims_css = f.read()
        theme_css = get_theme_css(theme_id)
        with open(os.path.join(CSS_DIR, "readability.css"), "r", encoding="utf-8") as f:
            theme_css += "\n" + f.read()          # 한글 가독성 안전장치는 테마 뒤에
        with open(os.path.join(JS_DIR, "runtime.js"), "r", encoding="utf-8") as f:
            runtime_js = f.read()
        with open(os.path.join(JS_DIR, "fx", "fx-runtime.js"), "r", encoding="utf-8") as f:
            fx_runtime_js = f.read()

        merged = "\n".join([fonts_css, base_css, anims_css, theme_css, font_override_css, extra_css])
        # @import 는 스타일 맨 앞에 있어야 동작하므로 위로 끌어올린다
        imports = re.findall(r"@import\s+url\([^)]*\)\s*;", merged)
        merged = re.sub(r"@import\s+url\([^)]*\)\s*;", "", merged)
        imports = [i for i in imports if "./fonts.css" not in i]
        head_styles = "<style>\n" + "\n".join(dict.fromkeys(imports)) + "\n" + merged + "\n</style>"
        body_scripts = f"""
        <script>
        {runtime_js}
        </script>
        <script>
        {fx_runtime_js}
        </script>
        """
    else:
        # 서버 호스팅용 링크 태그 사용
        head_styles = f"""
        <link rel="stylesheet" href="/static/css/fonts.css">
        <link rel="stylesheet" href="/static/css/base.css">
        <link rel="stylesheet" href="/static/css/animations.css">
        <link rel="stylesheet" id="theme-link" href="/static/css/themes/{theme_id}.css">
        <link rel="stylesheet" href="/static/css/readability.css">
        <style>
        {font_override_css}
        {extra_css}
        </style>
        """

        body_scripts = """
        <script src="/static/js/runtime.js"></script>
        <script src="/static/js/fx/fx-runtime.js"></script>
        """

    # 슬라이드 컨텐츠 래핑
    # 사용자가 이미 <div class="deck">을 전달했는지 확인
    if "<div class=\"deck\">" not in slides_html:
        slides_body = f'<div class="deck">\n{slides_html}\n</div>'
    else:
        slides_body = slides_html

    compiled_html = f"""<!DOCTYPE html>
<html lang="ko" data-theme="{theme_id}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {head_styles}
</head>
<body class="k-design-body">
    {slides_body}
    {body_scripts}
</body>
</html>"""

    if inline_all:
        # 사진은 data/media 에 따로 저장돼 있으므로 내보낼 때 파일 안에 넣는다
        from core.media import inline_media
        compiled_html = inline_media(compiled_html)
    return compiled_html
