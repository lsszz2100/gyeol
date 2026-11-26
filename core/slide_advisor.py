"""장표 추천: 슬라이드 내용을 읽고 어울리는 도식(레이아웃)·도형·꾸밈·스타일을 골라 준다.
AI 없이 바로 계산한다. 점수 = 내용 신호(숫자·연도·단계·비교어 등) + 장표 종류별 기본 선호."""
import json
import os
import re
from html.parser import HTMLParser

_HERE = os.path.dirname(os.path.abspath(__file__))

# 코드: (이름, 이 레이아웃임을 알아보는 class, 고칠 때 AI에게 줄 지시)
LAYOUTS = {
    "kpi": ("핵심 지표 카드", "", "핵심 지표(KPI) 카드 3~4개(③) 구성으로 바꿔 주세요. 숫자는 크게, 지표 이름과 기준 시점은 작게."),
    "bignum": ("큰 숫자 강조", "", "가장 중요한 숫자 하나를 크게 강조하는 구성(④)으로 바꿔 주세요."),
    "split": ("좌우 2단", "", "왼쪽 설명, 오른쪽 요점 목록의 좌우 2단(⑤) 구성으로 바꿔 주세요."),
    "versus": ("A vs B 비교", "", "이전·이후 또는 A·B를 나란히 비교하는 구성(⑥)으로 바꿔 주세요."),
    "table": ("표", "tbl", "항목과 수치를 표(⑪)로 정리해 주세요. 숫자 열은 오른쪽 정렬."),
    "timeline": ("타임라인", "tl", "번호 원과 연결선이 있는 타임라인(⑫)으로 바꿔 주세요."),
    "ring": ("원형 게이지", "ring", "비율 하나를 원형 게이지(⑬)로 강조해 주세요."),
    "chev": ("화살표 프로세스", "chev", "순서가 보이는 화살표 프로세스(⑭)로 바꿔 주세요."),
    "funnel": ("깔때기", "funnel", "단계마다 줄어드는 깔때기(⑮)로 바꿔 주세요."),
    "pyramid": ("피라미드", "pyramid", "위가 가장 중요한 피라미드(⑯)로 바꿔 주세요."),
    "stair": ("계단형 성장", "stair", "해마다 커지는 계단형 성장(⑰)으로 바꿔 주세요."),
    "cycle": ("순환", "cycle", "반복되는 과정을 순환 도식(⑱)으로 바꿔 주세요."),
    "swot": ("SWOT", "swot", "SWOT 4칸(⑲)으로 정리해 주세요."),
    "matrix": ("2×2 매트릭스", "mx", "두 기준으로 나눈 2×2 매트릭스(⑳)로 바꿔 주세요."),
    "hub": ("허브", "hub", "가운데 핵심과 주변 요소를 잇는 허브(㉑)로 바꿔 주세요."),
    "venn": ("벤 다이어그램", "venn", "겹치는 지점을 보여 주는 벤 다이어그램(㉒)으로 바꿔 주세요."),
    "vbars": ("세로 막대 그래프", "vbars", "값을 세로 막대 그래프(㉓)로 보여 주세요."),
    "pricing": ("요금제 카드", "pricing", "상품 구성을 요금제 카드(㉔)로 바꿔 주세요. 금액은 지어내지 말 것."),
    "procon": ("장단점 비교", "pc", "장점·단점 비교(㉕)로 정리해 주세요."),
    "numlist": ("큰 번호 목록", "numlist", "핵심 포인트를 큰 번호 목록(㉖)으로 바꿔 주세요."),
    "pie": ("원형·도넛 차트", "pie", "구성비를 원형·도넛 차트(㉗)로 보여 주세요."),
    "line": ("선 그래프", "lc", "시간에 따른 추이를 선 그래프(㉘)로 보여 주세요."),
    "team": ("팀 소개", "team", "사람마다 원형 사진 자리·이름·역할이 있는 팀 소개(㉙)로 바꿔 주세요."),
    "icons": ("아이콘 특징 그리드", "feat", "특징마다 아이콘·짧은 제목·한 줄 설명이 있는 아이콘 그리드(㉚)로 바꿔 주세요."),
    "section": ("섹션 구분", "sect", "큰 번호와 섹션 제목만 있는 섹션 구분 장표(㉛)로 바꿔 주세요."),
    "quote": ("후기·인용 카드", "voice", "고객 후기·인용 카드(㉜)로 바꿔 주세요. 실제 자료에 없는 인물·후기는 지어내지 말 것."),
    "milestone": ("마일스톤 로드맵", "ms", "가로선 위아래로 번갈아 놓이는 마일스톤 로드맵(㉝)으로 바꿔 주세요."),
    "org": ("조직도", "org", "위에서 아래로 내려가는 조직도(㉞)로 바꿔 주세요."),
    "contact": ("연락처", "contact", "연락 수단을 아이콘과 함께 정리한 연락처(㉟) 장표로 바꿔 주세요."),
    "agenda": ("목차", "agenda", "번호가 큰 목차(㊱) 장표로 바꿔 주세요."),
    "photo": ("사진 강조", "with-photo", "사진을 크게 두고 글을 짧게 줄인 사진 강조 구성으로 바꿔 주세요."),
    "hex": ("육각형 벌집", "hexes", "요소들을 육각형 벌집(㊲)으로 바꿔 주세요."),
    "rings": ("진행률 원 여러 개", "rings", "비율들을 진행률 원 여러 개(㊳)로 보여 주세요."),
    "mockup": ("기기 목업", "mock-phone", "앱·웹 화면을 휴대폰 또는 노트북 목업(㊴)에 담아 보여 주세요."),
    "cards": ("카드 나열", "card", "핵심 내용을 카드 3개로 정리해 주세요."),     # 맨 끝: 다른 구성 안의 카드보다 나중에 판별
}

# 꾸밈(도형·장식) 추천: 코드 → (이름, 설명, 적용 지시)
DECOR = {
    "ghost": ("큰 배경 글자", "제목 뒤에 아주 큰 옅은 영문 단어를 깔아 표지·섹션을 힘 있게",
              "제목 뒤에 큰 배경 글자(<span class=\"ghost\">핵심 영단어</span>)를 넣어 주세요."),
    "tag": ("라벨 제목", "제목 단어를 색 블록 위에 올려 잡지 표지처럼",
            "제목의 핵심 단어를 라벨 블록(<span class=\"tag-hl\">단어</span>)으로 강조해 주세요."),
    "vtitle": ("세로 제목", "제목을 왼쪽에 세로로 세워 여백을 살린 에디토리얼 구성",
               "왼쪽에 세로 제목(<div class=\"vtitle\">짧은 영문·한글 제목</div>)을 두는 구성으로 바꿔 주세요."),
    "blob": ("둥근 블롭 도형", "부드러운 유기적 도형으로 친근하고 밝게",
             "슬라이드 구석에 블롭 장식(<i class=\"blob\"></i>)을 하나 넣어 주세요."),
    "frame": ("테두리 제목 상자", "가는 테두리 상자 안에 제목을 넣어 사진·영상 위에서도 또렷하게",
              "제목을 가는 테두리 상자(<div class=\"frame-title\">…</div>) 안에 넣어 주세요."),
    "band": ("색 띠", "슬라이드 한쪽에 굵은 색 띠를 둘러 구획을 나눔",
             "슬라이드 한쪽에 색 띠(<i class=\"band\"></i>)를 넣어 주세요."),
    "badge": ("원형 배지", "할인율·핵심 숫자를 둥근 배지에 담아 눈에 띄게",
              "가장 중요한 숫자를 원형 배지(<div class=\"badge\"><b>숫자</b><span>설명</span></div>)에 담아 주세요."),
    "dots": ("점 격자", "빈 구석에 점 격자 무늬로 리듬감",
             "빈 구석에 점 격자 장식(<i class=\"dots\"></i>)을 넣어 주세요."),
    "thin": ("굵기 대비 제목", "앞말은 아주 얇게, 핵심어는 아주 굵게 — 세련된 발표 자료에서 흔한 제목 처리",
             "제목 앞부분을 <span class=\"thin\">얇은 글자</span>로 두고 핵심어만 굵게 해 주세요."),
}

# 장표 종류: 제목·글에서 찾는 말
ROLE_WORDS = [
    ("cover", r"^$"),
    ("agenda", r"목차|차례|순서|agenda|contents"),
    ("team", r"팀|구성원|멤버|조직|대표|임원|담당자|강사 소개|founder|team"),
    ("contact", r"문의|연락처|연락|오시는 길|주소|이메일|전화|contact"),
    ("quote", r"후기|추천사|인용|고객의 (소리|말)|testimonial|review|말씀"),
    ("pricing", r"요금|가격|플랜|패키지|구독|상품 구성|견적"),
    ("swot", r"swot|강점|약점|기회|위협"),
    ("market", r"시장 규모|tam|sam|som|시장|고객층|타깃|경쟁사|점유율"),
    ("timeline", r"연혁|로드맵|일정|마일스톤|history|roadmap|분기별|계획표|\b20\d\d\b.*\b20\d\d\b"),
    ("process", r"절차|단계|과정|프로세스|방법|순서대로|step|진행 방식|흐름"),
    ("compare", r"비교|대비|vs|이전|이후|전후|차이|before|after|장점|단점|찬반"),
    ("stats", r"\d+(\.\d+)?\s?(%|퍼센트|배|억|만|조|원|명|건|개|위|점)|성장|증가|감소|실적|성과|지표|통계"),
    ("mission", r"미션|비전|핵심 가치|목표|가치|철학"),
    ("mockup", r"앱 화면|웹사이트|홈페이지 화면|모바일 앱|화면 구성|ui|사용 화면"),
    ("portfolio", r"포트폴리오|사례|프로젝트 실적|작업물|갤러리"),
    ("about", r"회사 소개|기업 소개|우리는|about|who we are|소개합니다|설립"),
    ("service", r"서비스|기능|특징|장점|제품|솔루션|혜택|구성 요소"),
    ("section", r"^(part|chapter|섹션|\d{1,2}\s*(장|부))"),
    ("thanks", r"감사합니다|q\s*&\s*a|질의응답|마치며|thank"),
]

BODY_ROLES = ("swot", "pricing", "quote", "timeline", "process", "compare", "market", "mission")

# 장표 종류별 기본 선호 (advisor_data.json이 있으면 덮어씀)
ROLE_PRIOR = {
    "agenda": {"agenda": 3, "numlist": 2},
    "team": {"team": 4, "org": 2},
    "contact": {"contact": 4},
    "quote": {"quote": 4},
    "pricing": {"pricing": 4, "table": 1.5},
    "swot": {"swot": 4, "matrix": 1.5},
    "market": {"funnel": 2.5, "pie": 2, "matrix": 1.5, "venn": 1.2},
    "timeline": {"milestone": 3, "timeline": 2.5, "stair": 1.5},
    "process": {"chev": 3, "timeline": 2, "cycle": 1.2, "numlist": 1},
    "compare": {"versus": 3, "procon": 2.5, "table": 2},
    "stats": {"kpi": 2.5, "bignum": 2, "vbars": 2, "pie": 1.5, "line": 1.5, "ring": 1.2, "table": 1},
    "mission": {"pyramid": 2.5, "hub": 2, "bignum": 1},
    "service": {"icons": 3, "numlist": 1.5, "hub": 1.2},
    "section": {"section": 4},
    "thanks": {"section": 1.5, "contact": 1.5},
    "other": {"split": 1.5, "numlist": 1.2, "icons": 1, "photo": 1},
    "cover": {},
}
NO_DIAGRAM = ("cover", "section", "thanks")      # 표지·간지·마무리는 도식 대신 꾸밈을 추천

ROLE_DECOR = {
    "cover": ["ghost", "tag", "vtitle", "frame", "blob"],
    "section": ["ghost", "band", "vtitle"],
    "stats": ["badge", "dots"],
    "quote": ["band", "dots"],
    "team": ["blob", "dots"],
    "thanks": ["ghost", "frame"],
    "service": ["dots", "blob"],
    "other": ["dots", "band"],
}

ROLE_KO = {"about": "회사·주제 소개", "mockup": "화면 소개", "portfolio": "사례·작업물", "cover": "표지", "agenda": "목차", "team": "팀 소개", "contact": "연락처", "quote": "후기·인용",
           "pricing": "요금·상품", "swot": "SWOT", "market": "시장·고객", "timeline": "일정·연혁", "process": "절차·과정",
           "compare": "비교", "stats": "수치·성과", "mission": "목표·비전", "service": "서비스·특징",
           "section": "섹션 구분", "thanks": "마무리", "other": "일반 내용"}

# 분야·장표 종류별 어울리는 테마 스타일 (style_archetypes의 스타일 이름)
STYLE_BY_FIELD = {
    "auto": ["swiss", "startup", "editorial"],
    "sales": ["startup", "report", "swiss"], "ir": ["swiss", "startup", "dashboard"],
    "plan": ["report", "swiss", "editorial"], "marketing": ["magazine", "memphis", "cardnews"],
    "edu": ["notebook", "pastel", "cardnews"], "report": ["report", "dashboard", "swiss"],
    "research": ["editorial", "swiss", "blueprint"], "company": ["startup", "luxury", "magazine"],
    "event": ["poster", "neon", "memphis"],
}


def _load_prior():
    p = os.path.join(_HERE, "advisor_data.json")
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        for r, m in (d.get("role_prior") or {}).items():
            ROLE_PRIOR.setdefault(r, {}).update(m)
        for r, m in (d.get("role_decor") or {}).items():
            ROLE_DECOR[r] = m
    except (OSError, ValueError):
        pass


_load_prior()


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title, self.body, self.classes, self.items, self._in = "", [], set(), 0, []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for c in (a.get("class") or "").split():
            self.classes.add(c)
        if tag == "aside":
            self.skip += 1
        if tag in ("li", "tr") or any(c in (a.get("class") or "").split() for c in
                                      ("card", "tl-item", "chev-item", "fn-row", "nl", "hub-item", "st", "cy-node")):
            self.items += 1
        self._in.append(tag)

    def handle_endtag(self, tag):
        if tag == "aside":
            self.skip = max(0, self.skip - 1)
        if self._in:
            self._in.pop()

    def handle_data(self, data):
        if self.skip:
            return
        t = data.strip()
        if not t:
            return
        if self._in and self._in[-1] in ("h1", "h2") and not self.title:
            self.title = t
        else:
            self.body.append(t)


def read_slide(html: str) -> dict:
    p = _Text()
    try:
        p.feed(html or "")
    except Exception:
        pass
    body = " ".join(p.body)
    return {"title": p.title, "body": body, "classes": p.classes, "items": p.items}


def slide_role(info: dict, idx: int = -1, total: int = 0) -> str:
    if idx == 0:
        return "cover"
    words = dict(ROLE_WORDS)
    title = info["title"].lower()
    hay = f"{title} {info['body'][:600]}".lower()
    if total and idx == total - 1 and re.search(words["thanks"], hay):
        return "thanks"
    for name, rx in ROLE_WORDS[1:]:          # 제목에 있으면 가장 확실
        if re.search(rx, title):
            return name
    for name in BODY_ROLES:                  # 본문은 뚜렷한 말이 있을 때만
        if len(re.findall(words[name], hay)) >= (1 if name in ("swot", "pricing", "quote") else 2):
            return name
    if len(re.findall(words["stats"], hay)) >= 3:
        return "stats"
    if re.search(words["service"], hay):
        return "service"
    return "other"


def current_layout(info: dict) -> str:
    for code, (_, cls, _) in LAYOUTS.items():
        if cls and cls in info["classes"]:
            return code
    return ""


def _signals(info: dict) -> dict:
    t = f"{info['title']} {info['body']}"
    return {
        "pct": len(re.findall(r"\d+(\.\d+)?\s?%", t)),
        "nums": len(re.findall(r"\d[\d,.]*\s?(%|배|억|만|조|원|명|건|개|점|위|달러|\$)", t)),
        "years": len(set(re.findall(r"\b(19|20)\d\d\b", t))),
        "steps": len(re.findall(r"단계|step|먼저|다음|마지막|이후|→|①|②|③", t, re.I)),
        "cycle": bool(re.search(r"반복|순환|선순환|사이클|cycle|피드백", t, re.I)),
        "decline": bool(re.search(r"유입|전환|문의|계약|구매|tam|sam|som|깔때기", t, re.I)),
        "hier": bool(re.search(r"최상위|기반|토대|핵심 가치|비전|목표|상위|하위", t)),
        "overlap": bool(re.search(r"교집합|겹치|공통|만나는", t)),
        "two_axis": bool(re.search(r"사분면|우선순위|가로축|세로축|[xy]축|2\s?[x×]\s?2|긴급도|중요도와|난이도와|영향도와", t, re.I)),
        "items": info["items"],
        "chars": len(t),
    }


def recommend(html: str, idx: int = -1, total: int = 0, field: str = "auto", style: str = "") -> dict:
    """한 장 추천. 반환: role, current, layouts[{code,name,why,instruction}], decor[], styles[]"""
    info = read_slide(html)
    role = slide_role(info, idx, total)
    cur = current_layout(info)
    s = _signals(info)
    score = dict(ROLE_PRIOR.get(role, ROLE_PRIOR["other"]))
    score.pop("cards", None)
    why = {}
    if role in NO_DIAGRAM:
        s = dict(s, years=0, pct=0, nums=0, steps=0, cycle=False, decline=False, hier=False, overlap=False,
                 two_axis=False, items=0, chars=0)

    def add(code, v, reason):
        score[code] = score.get(code, 0) + v
        why.setdefault(code, reason)

    if s["years"] >= 3:
        add("line", 2, f"연도 {s['years']}개가 이어져 추이를 보여 주기 좋음")
        add("stair", 1.5, "해마다 커지는 값을 계단으로")
        add("milestone", 1.2, "연도별 사건을 로드맵으로")
    if s["pct"] >= 2:
        add("pie", 1.8, f"비율(%) 값이 {s['pct']}개 — 구성비를 한눈에")
        add("vbars", 1.2, "비율을 막대 길이로 비교")
    if s["pct"] == 1 or (s["nums"] == 1 and len(info["body"]) < 160):
        add("bignum", 2, "숫자 하나가 핵심 — 크게 강조")
        add("ring", 1.5, "비율 하나를 게이지로")
    if 3 <= s["nums"] <= 4:
        add("kpi", 2, f"핵심 수치 {s['nums']}개 — 지표 카드로")
    if s["nums"] >= 5:
        add("table", 2, f"수치가 {s['nums']}개로 많아 표가 읽기 쉬움")
        add("vbars", 1, "여러 값을 막대로 비교")
    if s["steps"] >= 2:
        add("chev", 2, "순서를 나타내는 말이 있어 흐름 도식이 어울림")
        add("timeline", 1.2, "단계를 번호로 이어 보여 줌")
    if s["cycle"]:
        add("cycle", 3, "반복·순환되는 과정")
    if s["decline"]:
        add("funnel", 2.5, "단계마다 줄어드는 수치(유입→전환 등)")
    if s["hier"]:
        add("pyramid", 2, "위아래 위계가 있는 개념")
    if s["overlap"]:
        add("venn", 3, "겹치는 지점이 핵심")
    if s["two_axis"]:
        add("matrix", 2.5, "두 기준으로 나눠 보면 명확")
    if 3 <= s["items"] <= 6 and role in ("service", "other", "mission"):
        add("icons", 1.2, f"항목 {s['items']}개를 아이콘 그리드로")
        add("numlist", 1, f"항목 {s['items']}개를 큰 번호로")
    if s["chars"] > 700:
        add("split", 1.5, "글이 많아 2단으로 나누면 덜 빽빽함")
    if field in ("ir", "sales") and role == "market":
        add("funnel", 1, "투자·영업 자료의 시장 규모는 깔때기가 표준")

    base_why = f"'{ROLE_KO.get(role, role)}' 장표에 가장 잘 어울리는 구성"
    if cur:
        score.pop(cur, None)
    ranked = sorted(score.items(), key=lambda x: -x[1])[:4]
    layouts = [{"code": c, "name": LAYOUTS[c][0], "why": why.get(c, base_why), "instruction": LAYOUTS[c][2],
                "score": round(v, 1)} for c, v in ranked if c in LAYOUTS and v > 0]
    decor = [{"code": d, "name": DECOR[d][0], "why": DECOR[d][1], "instruction": DECOR[d][2]}
             for d in ROLE_DECOR.get(role, ROLE_DECOR["other"])[:3]]
    styles = STYLE_BY_FIELD.get(field) or STYLE_BY_FIELD["auto"]
    return {"role": role, "role_ko": ROLE_KO.get(role, role), "current": cur,
            "current_name": LAYOUTS[cur][0] if cur else "", "layouts": layouts, "decor": decor, "styles": styles}


def recommend_deck(slides: list, field: str = "auto") -> list:
    """덱 전체: 장마다 첫 번째 추천과, 같은 구성이 연달아 반복되는 곳 표시."""
    out, prev = [], ""
    for i, h in enumerate(slides):
        r = recommend(h, i, len(slides), field)
        r["repeat"] = bool(r["current"] and r["current"] == prev)
        prev = r["current"]
        out.append(r)
    return out
