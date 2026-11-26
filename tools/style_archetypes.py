"""스타일 언어(아키타입) 정의.

색은 각 테마의 팔레트 토큰(--bg, --accent, --text-1 …)을 그대로 쓰고,
폰트·배경·장식 도형·카드·제목 처리·페이지 번호는 스타일마다 완전히 다르게 만든다.
모든 서체는 상업적 사용이 무료인 Google Fonts(OFL) 한글 서체.
"""

GF = "https://fonts.googleapis.com/css2?family={}&display=swap"

# 공통: 장식 레이어를 콘텐츠 뒤에 깔기 위한 기본 구조 + 슬라이드 번호 카운터
COMMON = """
.deck{counter-reset:sl}
.slide{counter-increment:sl;isolation:isolate}
.slide::before,.slide::after{pointer-events:none}
"""

STYLES = {
    "swiss": {
        "label": "스위스 타이포",
        "desc": "굵은 고딕, 상단 굵은 선, 큰 페이지 번호, 직각 카드",
        "fonts": ["IBM+Plex+Sans+KR:wght@400;600;700"],
        "display": "'Pretendard Variable',Pretendard,sans-serif", "body": "'IBM Plex Sans KR',sans-serif",
        "css": """
.slide{justify-content:flex-start;padding-top:120px;border-top:14px solid var(--accent)}
.slide::after{content:counter(sl,decimal-leading-zero);position:absolute;top:34px;right:64px;font:800 64px/1 var(--font-display);color:var(--text-1);letter-spacing:-.04em}
.slide::before{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,color-mix(in srgb,var(--text-1) 6%,transparent) 1px,transparent 1px) 0 0/calc(100%/12) 100%}
.h1,h1.title{font-weight:900;font-size:84px;letter-spacing:-.05em;line-height:.98}
.h2,h2.title{font-weight:800;letter-spacing:-.045em}
.kicker{color:var(--text-1);font-weight:700;letter-spacing:.02em;text-transform:none;font-size:18px}
.kicker::before{content:"■ ";color:var(--accent)}
.card{border-radius:0;box-shadow:none;border:0;border-top:4px solid var(--text-1);background:transparent;padding:20px 0 0}
.pill{border-radius:0;background:var(--text-1);color:var(--bg);border:0;font-weight:700}
.divider-accent{width:120px;height:8px;border-radius:0}
""",
    },
    "editorial": {
        "label": "에디토리얼 명조",
        "desc": "명조 제목, 이탤릭 영문 키커, 가는 이중선, 테두리 없는 칼럼",
        "fonts": ["Nanum+Myeongjo:wght@400;700;800", "Playfair+Display:ital,wght@1,400;1,600"],
        "display": "'Nanum Myeongjo',serif", "body": "'Pretendard Variable',Pretendard,sans-serif",
        "css": """
.slide{padding:96px 140px}
.slide::before{content:"";position:absolute;inset:36px 56px;z-index:-1;border-top:3px double var(--text-1);border-bottom:1px solid var(--text-1)}
.slide::after{content:"— " counter(sl) " —";position:absolute;bottom:46px;left:0;right:0;text-align:center;font:italic 400 18px 'Playfair Display',serif;color:var(--text-3)}
.h1,h1.title{font-weight:800;font-size:78px;letter-spacing:-.03em;line-height:1.15}
.h2,h2.title{font-weight:700;letter-spacing:-.025em;line-height:1.2}
.kicker{font:italic 600 22px 'Playfair Display',serif;text-transform:none;letter-spacing:0;color:var(--accent)}
.lede{font-family:var(--font-display);font-weight:400;font-size:24px}
.card{background:transparent;border:0;border-left:1px solid var(--border-strong);border-radius:0;box-shadow:none;padding:6px 0 6px 26px}
.card h4,.card h3{font-family:var(--font-display);font-weight:800}
.pill{border-radius:0;background:transparent;border:0;border-bottom:1px solid currentColor;padding:2px 0;font-style:italic}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent);font-style:italic}
""",
    },
    "brutal": {
        "label": "네오 브루탈",
        "desc": "검은 굵은 테두리, 딱딱한 그림자, 형광 하이라이트",
        "fonts": ["Black+Han+Sans", "Gothic+A1:wght@500;700;900"],
        "display": "'Black Han Sans',sans-serif", "body": "'Gothic A1',sans-serif",
        "css": """
.slide{border:6px solid var(--text-1);margin:0}
.slide::after{content:counter(sl);position:absolute;top:28px;right:28px;width:64px;height:64px;display:grid;place-items:center;background:var(--accent);color:var(--bg);border:4px solid var(--text-1);box-shadow:6px 6px 0 var(--text-1);font:400 30px var(--font-display)}
.h1,h1.title{font-weight:400;font-size:90px;line-height:1.02;letter-spacing:-.01em}
.h2,h2.title{font-weight:400;font-size:60px}
.kicker{display:inline-block;align-self:flex-start;background:var(--text-1);color:var(--bg);padding:6px 14px;font-weight:900;letter-spacing:.06em}
.card{border:4px solid var(--text-1);border-radius:0;box-shadow:10px 10px 0 var(--text-1);background:var(--surface)}
.card:nth-child(2n){background:var(--accent-2);color:var(--text-1)}
.pill{border:3px solid var(--text-1);border-radius:0;background:var(--accent);color:var(--bg);font-weight:900;box-shadow:4px 4px 0 var(--text-1);transform:rotate(-2deg)}
.gradient-text{background:var(--accent);-webkit-text-fill-color:var(--text-1);color:var(--text-1);padding:0 10px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.divider-accent{height:10px;width:160px;border:3px solid var(--text-1);border-radius:0}
""",
    },
    "poster": {
        "label": "아트 포스터",
        "desc": "초대형 둥근 제목, 큰 원형 도형, 색면 분할",
        "fonts": ["Bagel+Fat+One", "Gowun+Dodum"],
        "display": "'Bagel Fat One',sans-serif", "body": "'Gowun Dodum',sans-serif",
        "css": """
.slide::before{content:"";position:absolute;z-index:-1;width:670px;height:670px;border-radius:50%;background:var(--accent);right:-151px;bottom:-194px}
.slide:has(.h2,.grid,.stack,.card,ul)::before{width:340px;height:340px;right:-150px;bottom:-170px}
.slide::after{content:counter(sl,decimal-leading-zero);position:absolute;z-index:-1;left:60px;bottom:28px;font:400 120px/1 var(--font-display);color:transparent;-webkit-text-stroke:2px var(--text-1);opacity:.35}
.h1,h1.title{font-weight:400;font-size:104px;line-height:.98;letter-spacing:-.02em}
.h2,h2.title{font-weight:400;font-size:64px;line-height:1.05}
.kicker{font-family:var(--font-display);font-weight:400;font-size:20px;color:var(--accent-2)}
.card{border-radius:40px;border:0;box-shadow:none;background:var(--surface-2)}
.pill{background:var(--text-1);color:var(--bg);border:0;padding:8px 18px;font-size:15px}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
""",
    },
    "glass": {
        "label": "글래스 메시",
        "desc": "그라디언트 메시 배경, 반투명 유리 카드, 빛나는 제목",
        "fonts": ["Gothic+A1:wght@300;500;800"],
        "display": "'Pretendard Variable',Pretendard,sans-serif", "body": "'Gothic A1',sans-serif",
        "css": """
.slide::before{content:"";position:absolute;inset:-20%;z-index:-1;filter:blur(60px);opacity:.55;
  background:radial-gradient(closest-side at 20% 25%,var(--accent),transparent),radial-gradient(closest-side at 80% 70%,var(--accent-2),transparent),radial-gradient(closest-side at 65% 15%,var(--accent-3),transparent)}
.slide::after{content:counter(sl,decimal-leading-zero);position:absolute;bottom:32px;right:48px;font:500 14px var(--font-sans);padding:6px 14px;border-radius:99px;background:color-mix(in srgb,var(--surface) 40%,transparent);backdrop-filter:blur(10px);border:1px solid var(--border)}
.h1,h1.title{font-weight:800;letter-spacing:-.04em}
.kicker{display:inline-block;align-self:flex-start;padding:6px 14px;border-radius:99px;background:color-mix(in srgb,var(--surface) 35%,transparent);backdrop-filter:blur(10px);border:1px solid var(--border);text-transform:none;letter-spacing:.02em}
.card{background:color-mix(in srgb,var(--surface) 45%,transparent);backdrop-filter:blur(18px) saturate(140%);border:1px solid color-mix(in srgb,var(--text-1) 14%,transparent);border-radius:28px}
.pill{background:color-mix(in srgb,var(--surface) 40%,transparent);backdrop-filter:blur(8px)}
""",
    },
    "terminal": {
        "label": "터미널 코드",
        "desc": "고정폭 서체, 주석형 키커, 대괄호 모서리 카드, 스캔라인",
        "fonts": ["Nanum+Gothic+Coding:wght@400;700", "JetBrains+Mono:wght@400;700"],
        "display": "'JetBrains Mono','Nanum Gothic Coding',monospace", "body": "'Nanum Gothic Coding',monospace",
        "css": """
.slide::before{content:"";position:absolute;inset:0;z-index:-1;background:repeating-linear-gradient(0deg,transparent 0 3px,color-mix(in srgb,var(--text-1) 4%,transparent) 3px 4px)}
.slide::after{content:"[" counter(sl,decimal-leading-zero) "] ▮";position:absolute;bottom:28px;right:40px;font:700 16px var(--font-display);color:var(--accent);animation:k-blink 1.1s steps(1) infinite}
@keyframes k-blink{50%{opacity:.35}}
.h1,h1.title,.h2,h2.title{font-family:'Nanum Gothic Coding',monospace;font-weight:700;letter-spacing:-.02em}
.h1::before,h1.title::before{content:"$ ";color:var(--accent)}
.kicker{font-family:var(--font-display);text-transform:none;letter-spacing:0}
.kicker::before{content:"// ";opacity:.7}
.card{border-radius:0;box-shadow:none;border:1px dashed var(--border-strong);background:transparent;
  background-image:linear-gradient(var(--accent),var(--accent)),linear-gradient(var(--accent),var(--accent)),linear-gradient(var(--accent),var(--accent)),linear-gradient(var(--accent),var(--accent));
  background-size:18px 2px,2px 18px,18px 2px,2px 18px;background-position:0 0,0 0,100% 100%,100% 100%;background-repeat:no-repeat}
.pill{border-radius:0;font-family:var(--font-display)}
.pill::before{content:"#"}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
""",
    },
    "notebook": {
        "label": "노트 손글씨",
        "desc": "줄노트 배경, 손글씨 키커, 마스킹테이프 카드, 형광펜 강조",
        "fonts": ["Gowun+Dodum", "Nanum+Pen+Script", "Do+Hyeon"],
        "display": "'Do Hyeon',sans-serif", "body": "'Gowun Dodum',sans-serif",
        "css": """
.slide::before{content:"";position:absolute;inset:0;z-index:-1;background:repeating-linear-gradient(180deg,transparent 0 47px,color-mix(in srgb,var(--accent-2) 30%,transparent) 47px 48px),linear-gradient(90deg,transparent 110px,color-mix(in srgb,var(--bad) 45%,transparent) 110px 112px,transparent 112px)}
.slide{padding-left:150px}
.slide::after{content:"p." counter(sl);position:absolute;bottom:26px;right:50px;font:400 34px 'Nanum Pen Script',cursive;color:var(--text-2)}
.h1,h1.title,.h2,h2.title{font-weight:400}
.kicker{font:400 34px 'Nanum Pen Script',cursive;text-transform:none;letter-spacing:0;color:var(--accent)}
.card{border-radius:4px;box-shadow:0 8px 18px rgba(0,0,0,.08);transform:rotate(-1deg);overflow:visible}
.card:nth-child(2n){transform:rotate(1.2deg)}
.card::before{content:"";position:absolute;top:-14px;left:50%;width:110px;height:28px;transform:translateX(-50%) rotate(-3deg);background:color-mix(in srgb,var(--accent) 45%,transparent)}
.gradient-text{background:linear-gradient(transparent 55%,color-mix(in srgb,var(--accent) 55%,transparent) 55%);-webkit-text-fill-color:var(--text-1);color:var(--text-1)}
.pill{font:400 22px 'Nanum Pen Script',cursive;border-style:dashed}
""",
    },
    "pastel": {
        "label": "말랑 파스텔",
        "desc": "둥근 서체, 물방울 블롭 도형, 아주 둥근 카드",
        "fonts": ["Jua", "Gowun+Dodum"],
        "display": "'Jua',sans-serif", "body": "'Gowun Dodum','Jua',sans-serif",
        "css": """
.slide::before{content:"";position:absolute;z-index:-1;width:497px;height:432px;right:-65px;top:-86px;background:var(--accent-2);opacity:.45;border-radius:58% 42% 63% 37%/45% 55% 45% 55%}
.slide{padding-bottom:110px}
.slide:has(.grid,.stack,.card,ul)::before{width:340px;height:296px;right:-120px;top:-130px}
.slide::after{content:counter(sl);position:absolute;z-index:-1;left:-70px;bottom:-90px;width:250px;height:250px;display:flex;align-items:flex-start;justify-content:flex-end;padding:44px 64px 0 0;font:400 40px var(--font-display);color:var(--text-1);background:var(--accent-3);opacity:.6;border-radius:44% 56% 38% 62%/58% 39% 61% 42%}
.h1,h1.title,.h2,h2.title{font-weight:400}
.kicker{font-family:var(--font-display);font-weight:400;text-transform:none;letter-spacing:0;font-size:22px}
.card{border-radius:36px;border:0;box-shadow:0 14px 0 color-mix(in srgb,var(--accent) 25%,transparent)}
.pill{font-family:var(--font-display);background:var(--accent);color:var(--bg);border:0;padding:6px 16px;font-size:16px}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
""",
    },
    "luxury": {
        "label": "럭셔리 세리프",
        "desc": "가는 명조, 넓은 자간, 안쪽 금테 프레임, 중앙 정렬",
        "fonts": ["Gowun+Batang:wght@400;700", "Cormorant+Garamond:ital,wght@0,500;1,500"],
        "display": "'Gowun Batang',serif", "body": "'Gowun Batang',serif",
        "css": """
.slide{text-align:center;align-items:center;padding:110px 160px}
.slide::before{content:"";position:absolute;inset:34px;z-index:-1;border:1px solid var(--accent);outline:1px solid color-mix(in srgb,var(--accent) 45%,transparent);outline-offset:-10px}
.slide.with-photo{padding-right:calc(40% + 40px)}
.g-photo{top:45px;bottom:45px;right:45px;width:calc(40% - 45px)}
.slide::after{content:counter(sl,upper-roman);position:absolute;bottom:52px;left:0;right:0;font:italic 500 20px 'Cormorant Garamond',serif;letter-spacing:.3em;color:var(--accent)}
.h1,h1.title{font-weight:400;font-size:70px;letter-spacing:.02em;line-height:1.3}
.h2,h2.title{font-weight:400;letter-spacing:.02em;line-height:1.3}
.kicker{font:italic 500 20px 'Cormorant Garamond',serif;letter-spacing:.4em;color:var(--accent)}
.lede{margin-left:auto;margin-right:auto}
.row{justify-content:center}
.slide>:is(.grid,.stack,ul,ol){align-self:stretch}
.slide ul,.slide ol{text-align:left}
.card ul,.card ol{display:inline-block;margin-left:auto;margin-right:auto}
.stack .row{justify-content:space-between}
.card{background:transparent;border:0;border-top:1px solid var(--accent);border-radius:0;box-shadow:none;padding:28px 18px 8px}
.pill{background:transparent;border:1px solid var(--accent);color:var(--accent);border-radius:0;letter-spacing:.2em}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
.divider-accent{margin:0 auto;height:1px;width:80px}
""",
    },
    "report": {
        "label": "기업 보고서",
        "desc": "상단 헤더 띠, 하단 정보 바, 왼쪽 강조선 카드",
        "fonts": ["IBM+Plex+Sans+KR:wght@400;500;700"],
        "display": "'IBM Plex Sans KR',sans-serif", "body": "'IBM Plex Sans KR',sans-serif",
        "css": """
.slide{padding:110px 90px 90px}
.slide::before{content:"";position:absolute;left:0;right:0;top:0;height:58px;z-index:-1;background:var(--accent);box-shadow:0 4px 0 var(--accent-2)}
.slide::after{content:"PAGE " counter(sl,decimal-leading-zero);position:absolute;left:90px;right:90px;bottom:28px;padding-top:12px;border-top:1px solid var(--border-strong);font:500 13px var(--font-sans);letter-spacing:.14em;color:var(--text-3);text-align:right}
.h1,h1.title{font-weight:700;font-size:66px;letter-spacing:-.03em}
.h2,h2.title{font-weight:700;font-size:46px;letter-spacing:-.03em}
.slide>.kicker{position:absolute;top:18px;left:90px;color:var(--bg);font-size:15px;letter-spacing:.12em}
.card{border-radius:4px;border:1px solid var(--border);border-left:6px solid var(--accent);box-shadow:none}
.pill{border-radius:4px}
""",
    },
    "magazine": {
        "label": "매거진 커버",
        "desc": "초굵은 제목, 외곽선 강조 글자, 배경 대형 번호 워터마크",
        "fonts": ["Gasoek+One", "Gothic+A1:wght@400;700"],
        "display": "'Gasoek One',sans-serif", "body": "'Gothic A1',sans-serif",
        "css": """
.slide::before{content:counter(sl,decimal-leading-zero);position:absolute;z-index:-1;right:-30px;top:50%;transform:translateY(-50%);font:400 520px/1 var(--font-display);color:var(--accent);opacity:.12;letter-spacing:-.06em}
.slide::after{content:"";position:absolute;left:96px;top:56px;width:48px;height:48px;background:var(--accent);border-radius:50%}
.h1,h1.title{font-weight:400;font-size:100px;line-height:1;letter-spacing:-.03em}
.h2,h2.title{font-weight:400;font-size:62px;line-height:1.05}
.gradient-text{background:none;color:transparent;-webkit-text-fill-color:transparent;-webkit-text-stroke:2.5px var(--accent)}
.kicker{font-weight:700;letter-spacing:.3em;color:var(--text-1);margin-top:30px}
.card{border-radius:0;border:0;border-top:10px solid var(--accent);box-shadow:none;background:var(--surface-2)}
.pill{border-radius:0;background:var(--accent);color:var(--bg);border:0;font-weight:700}
""",
    },
    "memphis": {
        "label": "멤피스 팝",
        "desc": "삼각형·지그재그·점 패턴 도형, 컬러 오프셋 그림자",
        "fonts": ["Do+Hyeon", "Sunflower:wght@300;500;700"],
        "display": "'Do Hyeon',sans-serif", "body": "'Sunflower',sans-serif",
        "css": """
.slide::before{content:"";position:absolute;inset:0;z-index:-1;
  background:radial-gradient(circle,var(--accent-2) 3px,transparent 3.5px) 85% 12%/26px 26px no-repeat,
  conic-gradient(from 210deg at 50% 0,transparent 0 120deg,var(--accent) 120deg 240deg,transparent 240deg) 92% 78%/120px 104px no-repeat,
  radial-gradient(circle,color-mix(in srgb,var(--accent-2) 70%,transparent) 2.5px,transparent 3px) 0 0/30px 30px;
  -webkit-mask:linear-gradient(90deg,transparent 55%,#000 75%);mask:linear-gradient(90deg,transparent 55%,#000 75%)}
.slide::after{content:"";position:absolute;left:70px;bottom:44px;width:220px;height:22px;z-index:-1;
  background:linear-gradient(135deg,var(--accent-3) 25%,transparent 25%) -11px 0/22px 22px,linear-gradient(225deg,var(--accent-3) 25%,transparent 25%) -11px 0/22px 22px}
.h1,h1.title,.h2,h2.title{font-weight:400}
.h1,h1.title{font-size:92px;line-height:1.02}
.kicker{font-family:var(--font-display);font-weight:400;font-size:24px;text-transform:none;letter-spacing:0}
.card{border:3px solid var(--text-1);border-radius:14px;box-shadow:8px 8px 0 var(--accent)}
.card:nth-child(3n+2){box-shadow:8px 8px 0 var(--accent-2)}
.card:nth-child(3n){box-shadow:8px 8px 0 var(--accent-3)}
.pill{border:2px solid var(--text-1);font-family:var(--font-display);font-size:16px}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent);text-shadow:4px 4px 0 var(--accent-2)}
""",
    },
    "y2k": {
        "label": "Y2K 크롬",
        "desc": "크롬 금속 글자, 별빛 반짝이, 둥근 알약 프레임",
        "fonts": ["Orbit", "Black+Han+Sans"],
        "display": "'Black Han Sans','Orbit',sans-serif", "body": "'Orbit',sans-serif",
        "css": """
.slide::before{content:"✦";position:absolute;z-index:-1;right:80px;top:50px;font-size:130px;line-height:1;color:var(--accent);text-shadow:-110px 70px 0 var(--accent-2),40px 150px 0 var(--accent-3)}
.slide::after{content:counter(sl,decimal-leading-zero);position:absolute;right:48px;bottom:34px;padding:8px 22px;border-radius:99px;border:2px solid var(--text-1);font:400 18px var(--font-sans);background:linear-gradient(180deg,var(--surface),var(--surface-2))}
.h1,h1.title,.h2,h2.title{font-weight:400}
.h1,h1.title{font-size:84px;letter-spacing:-.01em}
.h1,h1.title,.gradient-text{background:linear-gradient(180deg,var(--text-1) 0%,var(--text-3) 46%,var(--text-1) 54%,var(--accent) 100%);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.kicker{font-family:var(--font-sans);text-transform:none;letter-spacing:.2em}
.card{border-radius:999px;padding:28px 40px;border:2px solid var(--text-1);background:linear-gradient(180deg,var(--surface),var(--surface-2))}
.grid .card{border-radius:30px}
.pill{border:2px solid var(--text-1)}
""",
    },
    "zen": {
        "label": "젠 미니멀",
        "desc": "가는 서체, 세로선 하나, 강조 점 하나, 넓은 여백",
        "fonts": ["Gowun+Dodum", "Noto+Serif+KR:wght@300;500"],
        "display": "'Noto Serif KR',serif", "body": "'Gowun Dodum',sans-serif",
        "css": """
.slide{padding:120px 200px}
.slide::before{content:"";position:absolute;z-index:-1;left:120px;top:120px;bottom:120px;width:1px;background:var(--text-3)}
.slide::after{content:"";position:absolute;right:140px;top:120px;width:22px;height:22px;border-radius:50%;background:var(--accent)}
.h1,h1.title{font-weight:300;font-size:64px;letter-spacing:-.01em;line-height:1.35}
.h2,h2.title{font-weight:300;font-size:46px;line-height:1.35}
.kicker{color:var(--text-3);letter-spacing:.5em;font-weight:400;font-size:13px}
.lede{font-size:20px}
.card{border:0;box-shadow:none;background:transparent;padding:0 0 0 0;border-radius:0}
.card h4{font-family:var(--font-display);font-weight:500}
.pill{background:transparent;border:0;color:var(--text-3);padding:0;letter-spacing:.2em}
.pill::before{content:"· ";color:var(--accent)}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
""",
    },
    "dashboard": {
        "label": "데이터 대시보드",
        "desc": "점 격자 배경, KPI 패널 카드, 상단 지표 바, 숫자 전용 서체",
        "fonts": ["IBM+Plex+Sans+KR:wght@400;600;700", "Space+Grotesk:wght@500;700"],
        "display": "'Space Grotesk','IBM Plex Sans KR',sans-serif", "body": "'IBM Plex Sans KR',sans-serif",
        "css": """
.slide::before{content:"";position:absolute;inset:0;z-index:-1;background:radial-gradient(color-mix(in srgb,var(--text-1) 14%,transparent) 1px,transparent 1.5px) 0 0/22px 22px}
.slide::after{content:"● LIVE  ·  " counter(sl,decimal-leading-zero);position:absolute;top:30px;right:44px;font:600 13px var(--font-display);letter-spacing:.14em;color:var(--good)}
.h1,h1.title,.h2,h2.title{font-family:'IBM Plex Sans KR',sans-serif;font-weight:700;letter-spacing:-.03em}
.kicker{font-family:var(--font-display);letter-spacing:.18em}
.card{border-radius:12px;border:1px solid var(--border-strong);box-shadow:none;background:var(--surface);padding-top:34px}
.card::before{content:"";position:absolute;left:0;top:0;right:0;height:5px;background:linear-gradient(90deg,var(--accent) 62%,var(--surface-2) 62%)}
.card:nth-child(2n)::before{background:linear-gradient(90deg,var(--accent-2) 38%,var(--surface-2) 38%)}
.pill{border-radius:6px;font-family:var(--font-display)}
""",
    },
    "window": {
        "label": "레트로 윈도우",
        "desc": "옛날 운영체제 창 모양 카드, 픽셀풍 그림자, 바둑판 배경",
        "fonts": ["Orbit", "Gothic+A1:wght@500;800"],
        "display": "'Orbit',sans-serif", "body": "'Gothic A1',sans-serif",
        "css": """
.slide::before{content:"";position:absolute;inset:0;z-index:-1;background:conic-gradient(var(--surface-2) 25%,transparent 0 50%,var(--surface-2) 0 75%,transparent 0) 0 0/40px 40px;opacity:.6}
.slide::after{content:"▶ " counter(sl) ".PPT";position:absolute;left:0;right:0;bottom:0;padding:10px 24px;background:var(--surface-2);border-top:3px solid var(--text-1);font:400 16px var(--font-display)}
.h1,h1.title,.h2,h2.title{font-weight:400}
.kicker{font-family:var(--font-display);text-transform:none;letter-spacing:.04em}
.card{border-radius:0;border:3px solid var(--text-1);box-shadow:6px 6px 0 var(--text-1);padding-top:56px;background:var(--surface)}
.card::before{content:"● ● ●";position:absolute;left:0;right:0;top:0;height:34px;padding:0 12px;display:flex;align-items:center;justify-content:flex-end;letter-spacing:4px;font-size:12px;color:var(--bg);background:var(--accent);border-bottom:3px solid var(--text-1)}
.pill{border-radius:0;border:2px solid var(--text-1);box-shadow:3px 3px 0 var(--text-1);font-family:var(--font-display)}
.gradient-text{background:linear-gradient(transparent 12%,var(--accent) 12%,var(--accent) 92%,transparent 92%);-webkit-text-fill-color:var(--bg);color:var(--bg);padding:0 8px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
div.gradient-text,p.gradient-text{background:var(--accent);padding:6px 20px 10px}
""",
    },
    "blueprint": {
        "label": "블루프린트 도면",
        "desc": "모눈 도면 배경, 점선 카드, 치수선, 도면 번호",
        "fonts": ["Nanum+Gothic+Coding:wght@400;700", "Black+Han+Sans"],
        "display": "'Black Han Sans',sans-serif", "body": "'Nanum Gothic Coding',monospace",
        "css": """
.slide::before{content:"";position:absolute;inset:0;z-index:-1;background:
  linear-gradient(color-mix(in srgb,var(--text-1) 16%,transparent) 1px,transparent 1px) 0 0/100px 100px,
  linear-gradient(90deg,color-mix(in srgb,var(--text-1) 16%,transparent) 1px,transparent 1px) 0 0/100px 100px,
  linear-gradient(color-mix(in srgb,var(--text-1) 7%,transparent) 1px,transparent 1px) 0 0/20px 20px,
  linear-gradient(90deg,color-mix(in srgb,var(--text-1) 7%,transparent) 1px,transparent 1px) 0 0/20px 20px}
.slide::after{content:"DWG No. K-" counter(sl,decimal-leading-zero);position:absolute;right:40px;bottom:30px;padding:10px 18px;border:2px solid var(--text-1);font:700 14px 'Nanum Gothic Coding',monospace;background:var(--bg)}
.h1,h1.title,.h2,h2.title{font-weight:400;letter-spacing:.01em}
.kicker{font-family:'Nanum Gothic Coding',monospace;letter-spacing:.1em}
.kicker::after{content:"";display:inline-block;width:140px;height:1px;margin-left:12px;vertical-align:middle;background:currentColor}
.card{border:2px dashed var(--text-2);border-radius:0;box-shadow:none;background:color-mix(in srgb,var(--bg) 70%,transparent)}
.pill{border-radius:0;border-style:dashed}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
""",
    },
    "startup": {
        "label": "스타트업 그라디언트",
        "desc": "모서리 그라디언트 빛, 점 달린 알약 키커, 부드러운 카드",
        "fonts": ["Gothic+A1:wght@400;600;800;900"],
        "display": "'Gothic A1',sans-serif", "body": "'Pretendard Variable',Pretendard,sans-serif",
        "css": """
.slide::before{content:"";position:absolute;z-index:-1;width:864px;height:864px;right:-302px;top:-367px;border-radius:50%;background:conic-gradient(from 90deg,var(--accent),var(--accent-2),var(--accent-3),var(--accent));filter:blur(80px);opacity:.38}
.slide::after{content:counter(sl,decimal-leading-zero);position:absolute;left:96px;bottom:34px;font:800 14px var(--font-display);color:var(--text-3);letter-spacing:.2em}
.h1,h1.title{font-weight:900;letter-spacing:-.05em}
.h2,h2.title{font-weight:800;letter-spacing:-.045em}
.kicker{display:inline-flex;align-items:center;gap:8px;align-self:flex-start;padding:6px 14px 6px 10px;border-radius:99px;border:1px solid var(--border-strong);text-transform:none;letter-spacing:0;font-weight:600}
.kicker::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px color-mix(in srgb,var(--accent) 25%,transparent)}
.card{border-radius:22px}
""",
    },
    "newspaper": {
        "label": "신문 지면",
        "desc": "제호형 헤더, 단 구분선, 명조 헤드라인, 흑백+한 가지 색",
        "fonts": ["Nanum+Myeongjo:wght@700;800", "Noto+Serif+KR:wght@400;600"],
        "display": "'Nanum Myeongjo',serif", "body": "'Noto Serif KR',serif",
        "css": """
.slide{padding:140px 96px 80px}
.slide::before{content:"THE DAILY  ·  제 " counter(sl) " 면";position:absolute;left:96px;right:96px;top:44px;padding:10px 0;border-top:4px solid var(--text-1);border-bottom:1px solid var(--text-1);font:800 20px var(--font-display);letter-spacing:.2em;text-align:center}
.h1,h1.title{font-weight:800;font-size:76px;line-height:1.12;letter-spacing:-.03em}
.h2,h2.title{font-weight:800;line-height:1.18}
.kicker{color:var(--accent);font-weight:600;letter-spacing:.1em}
.lede{font-family:var(--font-sans);column-count:2;column-gap:40px;column-rule:1px solid var(--border-strong);max-width:none}
.grid .lede,.card .lede,.center .lede{column-count:1}
.grid{gap:0}
.card{border:0;border-radius:0;box-shadow:none;background:transparent;border-right:1px solid var(--border-strong);padding:0 24px}
.card:last-child{border-right:0}
.pill{border-radius:0;background:transparent;border:1px solid var(--text-1);color:var(--text-1)}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
""",
    },
    "hanji": {
        "label": "한지 전통",
        "desc": "한지 결 질감, 붓글씨 키커, 붉은 낙관 도장, 세로 여백선",
        "fonts": ["Song+Myung", "Nanum+Brush+Script", "Gowun+Batang"],
        "display": "'Song Myung',serif", "body": "'Gowun Batang',serif",
        "css": """
.slide::before{content:"";position:absolute;inset:0;z-index:-1;opacity:.5;background:
  repeating-linear-gradient(97deg,transparent 0 9px,color-mix(in srgb,var(--text-1) 4%,transparent) 9px 10px),
  repeating-linear-gradient(7deg,transparent 0 13px,color-mix(in srgb,var(--text-1) 3%,transparent) 13px 14px)}
.slide::after{content:counter(sl);position:absolute;right:80px;bottom:60px;width:74px;height:74px;display:grid;place-items:center;border:4px double var(--bg);outline:3px solid var(--bad);background:var(--bad);color:var(--bg);font:400 32px var(--font-display);transform:rotate(-6deg);border-radius:6px}
.h1,h1.title,.h2,h2.title{font-weight:400;letter-spacing:.02em}
.h1,h1.title{font-size:80px;line-height:1.2}
.kicker{font:400 40px 'Nanum Brush Script',cursive;text-transform:none;letter-spacing:0;color:var(--accent)}
.card{background:color-mix(in srgb,var(--surface) 70%,transparent);border:0;border-radius:2px;border-top:2px solid var(--text-1);border-bottom:2px solid var(--text-1);box-shadow:none}
.pill{border-radius:2px;background:var(--bad);color:var(--bg);border:0}
.gradient-text{background:none;-webkit-text-fill-color:var(--bad);color:var(--bad)}
""",
    },
    "neon": {
        "label": "네온 나이트",
        "desc": "네온 발광 글자와 테두리, 지평선 격자, 어두운 무대",
        "fonts": ["Black+Han+Sans", "Gothic+A1:wght@400;700"],
        "display": "'Black Han Sans',sans-serif", "body": "'Gothic A1',sans-serif",
        "dark_only": True,
        "css": """
.slide::before{content:"";position:absolute;left:-20%;right:-20%;bottom:-10%;height:45%;z-index:-1;transform:perspective(400px) rotateX(62deg);transform-origin:bottom;opacity:.5;
  background:linear-gradient(var(--accent) 2px,transparent 2px) 0 0/100% 48px,linear-gradient(90deg,var(--accent) 2px,transparent 2px) 0 0/64px 100%;
  -webkit-mask:linear-gradient(transparent,#000);mask:linear-gradient(transparent,#000)}
.slide::after{content:counter(sl,decimal-leading-zero);position:absolute;top:30px;right:44px;font:400 30px var(--font-display);color:var(--accent-2);text-shadow:0 0 10px var(--accent-2),0 0 26px var(--accent-2)}
.h1,h1.title,.h2,h2.title{font-weight:400;text-shadow:0 0 14px color-mix(in srgb,var(--accent) 80%,transparent),0 0 40px color-mix(in srgb,var(--accent) 50%,transparent)}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
.kicker{color:var(--accent-2);text-shadow:0 0 8px var(--accent-2)}
.card{background:color-mix(in srgb,var(--bg) 75%,transparent);border:2px solid var(--accent);border-radius:14px;box-shadow:0 0 18px color-mix(in srgb,var(--accent) 55%,transparent),inset 0 0 18px color-mix(in srgb,var(--accent) 25%,transparent)}
.pill{border-color:var(--accent-2);color:var(--accent-2);background:transparent;box-shadow:0 0 10px color-mix(in srgb,var(--accent-2) 60%,transparent)}
""",
    },
    "cardnews": {
        "label": "카드뉴스 스티커",
        "desc": "굵은 둥근 카드, 스티커 뱃지, 말풍선, 꽉 찬 색 배경",
        "fonts": ["Dongle:wght@400;700", "Jua"],
        "display": "'Jua',sans-serif", "body": "'Jua',sans-serif",
        "css": """
.deck,.slide{background:var(--accent)}
.slide{padding:72px 120px}
.slide::before{content:"";position:absolute;inset:40px;z-index:-1;background:var(--bg);border-radius:44px;border:4px solid var(--text-1);box-shadow:12px 12px 0 var(--text-1)}
.slide.with-photo{padding-right:calc(40% + 40px)}
.g-photo{top:44px;bottom:44px;right:44px;width:calc(40% - 44px);border-radius:0 40px 40px 0}
.slide::after{content:counter(sl) "/";position:absolute;top:20px;right:30px;width:96px;height:96px;display:grid;place-items:center;border-radius:50%;background:var(--accent-2);border:4px solid var(--text-1);font:400 30px var(--font-display);transform:rotate(12deg);color:var(--text-1)}
.h1,h1.title,.h2,h2.title{font-weight:400}
.lede{font-size:26px}
.kicker{display:inline-block;align-self:flex-start;background:var(--text-1);color:var(--bg);padding:8px 20px;border-radius:24px 24px 24px 4px;font-family:var(--font-display);font-weight:400;text-transform:none;letter-spacing:0;font-size:20px}
.card{border:3px solid var(--text-1);border-radius:26px;box-shadow:6px 6px 0 var(--text-1)}
.pill{border:3px solid var(--text-1);background:var(--accent-2);color:var(--text-1);font-size:17px;transform:rotate(-3deg)}
.gradient-text{background:none;-webkit-text-fill-color:var(--accent);color:var(--accent)}
""",
    },
}
