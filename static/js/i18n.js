/* 결 GYEOL — 화면 언어(한국어/영어).
   화면을 그리는 코드는 한국어 그대로 두고, 영어일 때 화면에 나타나는 문구를 이 사전으로 바꾼다.
   - 정확히 같은 문구 → 번역, {} 가 든 문구 → 틀(숫자·이름 자리) 맞춰 번역, " · " 로 이은 문구 → 조각마다 번역
   - 글 내용(슬라이드·대본·입력칸 값)은 건드리지 않는다: [contenteditable], textarea·input 값, [data-noi18n] 제외
   - 언어: <html data-ui-lang="ko|en|"> (서버가 설정값을 넣음, 비면 PC 언어로) */
(function () {
  "use strict";
  const pick = () => {
    const v = (document.documentElement.getAttribute("data-ui-lang") || "").toLowerCase();
    if (v === "ko" || v === "en") return v;
    return /^ko\b/i.test(navigator.language || "ko") ? "ko" : "en";
  };
  const LANG = pick();
  document.documentElement.setAttribute("data-ui-lang-resolved", LANG);
  if (LANG === "en") document.documentElement.lang = "en";

  // [한국어, 영어] — {} 는 숫자·이름 자리(순서대로). 순서가 바뀌면 {0}{1}로 적는다.
  const PAIRS = [
    // ── 머리글·메뉴 ──
    ["결 GYEOL · AI 프레젠테이션", "GYEOL · AI Presentation"],
    ["🖼 사진 찾는 중", "🖼 Finding photos"], ["🖼 사진 찾는 중 {}장", "🖼 Finding {} photos"],
    ["🎨 디자인 테마", "🎨 Themes"], ["📂 프로젝트", "📂 Projects"], ["🧩 슬라이드 설정", "🧩 Slide settings"],
    ["💾 내보내기 ▾", "💾 Export ▾"], ["파워포인트 · 편집 가능", "PowerPoint · editable"], ["글자 수정 가능 + 발표자 노트", "Editable text + speaker notes"],
    ["파워포인트 · 원본 그대로", "PowerPoint · exact"], ["디자인 100% 유지, 글자는 이미지", "Design kept 100%, text as images"],
    ["PDF 문서 (.pdf)", "PDF document (.pdf)"], ["인쇄·배포용, 한 장에 한 슬라이드", "For print and sharing, one slide per page"],
    ["HTML 파일 (.html)", "HTML file (.html)"], ["애니메이션·발표자 모드 그대로", "Keeps animations and presenter mode"],
    ["이미지 묶음 (.zip)", "Image set (.zip)"], ["슬라이드별 PNG 이미지", "One PNG per slide"],
    ["동영상 (.mp4)", "Video (.mp4)"], ["애니메이션·전환 그대로 1080p 영상 (몇 분 걸림)", "1080p video with animations and transitions (takes a few minutes)"],
    ["발표 대본 및 개요 (.md)", "Script and outline (.md)"], ["슬라이드별 핵심 요약 + 발표자 대본", "Key points per slide + speaker script"],
    ["발표 대본 전문 (.txt)", "Full script (.txt)"], ["리허설·프롬프터용 텍스트 전문", "Plain text for rehearsal or a teleprompter"],
    ["▶ 발표 시작", "▶ Present"], ["라이선스", "License"], ["나중에", "Later"], ["지금 업데이트", "Update now"],
    // ── 슬라이드 목록·도구 모음 ──
    ["슬라이드", "Slides"], ["0장", "0"], ["＋ 추가", "＋ Add"], ["AI로 고치기", "AI fix"], ["장표 추천", "Advisor"], ["전체 장표 점검", "Check all slides"],
    ["AI 검수", "AI review"], ["넣기 ▾", "Insert ▾"], ["무료 사진 검색", "Free photo search"], ["저작권 걱정 없는 사진", "Copyright-safe photos"],
    ["AI 그림 만들기", "Make an AI image"], ["원하는 장면을 글로 설명", "Describe the scene you want"], ["아이콘", "Icons"], ["200여 개 · 한글 검색", "200+ · search in Korean or English"],
    ["도형", "Shapes"], ["사각형·원·화살표·선", "Rectangles, circles, arrows, lines"], ["내 사진·그림 올리기", "Upload my picture"], ["PC에 있는 파일", "A file on this PC"],
    ["되돌리기", "Undo"], ["이 슬라이드 고치기", "Fix this slide"], ["뒤에 새 슬라이드 추가", "Add a slide after"], ["최신 자료 검색", "Search the web"],
    ["인터넷 · 10초 더 걸림", "Internet · takes 10s longer"], ["✨ 고치기", "✨ Fix"], ["발표자 대본", "Script"], ["전체 개요", "Overview"], ["발표자 모드", "Presenter"],
    ["전체화면", "Fullscreen"], ["클릭해서 고칠 수 있습니다", "Click to edit"],
    ["📎 내 자료", "📎 My files"], ["📋 가이드", "📋 Guide"], ["📋 가이드 ✓", "📋 Guide ✓"], ["✨ 슬라이드 만들기", "✨ Create slides"],
    ["🚀 IR 피치덱", "🚀 Pitch deck"], ["💼 사업 제안서", "💼 Business proposal"], ["📊 성과 보고서", "📊 Performance report"], ["💡 트렌드 세미나", "💡 Trend seminar"],
    ["⚙ 생성 옵션", "⚙ Options"],
    // ── 가이드 ──
    ["📋 가이드 맞춤 PPT", "📋 Guide-matched deck"], ["발주처의", "Paste a client's"], ["제안요청서(RFP)", "RFP"], [", 교수님의", ", a professor's"], ["과제 안내", "assignment brief"],
    [", 행사 측의", ", an event's"], ["발표 지침", "presentation guidelines"], [", 업체", " or a company's"], ["요청서", "request"],
    ["를 붙여 넣으세요. AI가 장수·목차 순서·항목별 꼭 넣을 내용·배점·키워드·그대로 넣을 문구·금지어·표지 정보를 뽑아 그대로 맞춰 만들고, 다 만든 뒤 지켰는지 확인해 드립니다. (주제 칸은 비워도 됩니다)",
      ". The AI extracts the slide count, section order, must-have content, scoring, keywords, exact phrases, banned words and cover details, writes to them, and checks the result. (The topic box can stay empty.)"],
    ["📂 가이드 파일 불러오기", "📂 Load a guide file"], ["지우기", "Clear"],
    // ── 생성 옵션 ──
    ["생성 옵션", "Options"], ["구성", "Structure"], ["분야", "Field"], ["자동 (주제에 맞춤)", "Auto (fit the topic)"], ["영업·세일즈 제안", "Sales proposal"],
    ["투자 유치(IR)", "Investor pitch (IR)"], ["사업 계획", "Business plan"], ["마케팅·홍보", "Marketing"], ["교육·강의", "Education / lecture"], ["업무·성과 보고", "Work / performance report"],
    ["연구·분석", "Research / analysis"], ["회사·서비스 소개", "Company / service intro"], ["행사·이벤트 기획", "Event planning"], ["본문 장수", "Body slides"],
    ["5장", "5"], ["6장", "6"], ["8장", "8"], ["10장", "10"], ["12장", "12"], ["15장", "15"], ["20장", "20"], ["25장", "25"],
    ["마무리 슬라이드", "Closing slide"], ["감사합니다", "Thank you"], ["질의응답(Q&A)", "Q&A"], ["넣지 않음", "None"], ["내용 밀도", "Text density"],
    ["간결하게", "Concise"], ["보통", "Normal"], ["자세하게", "Detailed"], ["목차 슬라이드", "Agenda slide"], ["표지 다음", "After the cover"], ["참고 자료 슬라이드", "Sources slide"],
    ["맨 뒤", "At the end"], ["슬라이드별 출처 표기", "Sources on each slide"], ["섹션 간지", "Section dividers"], ["인터넷", "Internet"], ["표·그래프·도형", "Tables, charts, shapes"],
    ["최소 (꼭 필요한 곳만)", "Minimal (only where needed)"], ["적극 (절반 이상 시각화)", "Rich (over half visual)"], ["인포그래픽", "Infographics"], ["쓰지 않음", "None"],
    ["조금 (1~2장)", "A few (1–2 slides)"], ["보통 (3분의 1)", "Normal (one third)"], ["많이 (절반 이상)", "Many (over half)"], ["디자인 분위기", "Design mood"],
    ["자동 (고른 테마에 맞춤)", "Auto (fit the theme)"], ["정돈된 에디토리얼 (격자·번호·표)", "Tidy editorial (grid, numbers, tables)"], ["차분한 여백 (미니멀)", "Calm whitespace (minimal)"],
    ["매거진 (읽는 구성)", "Magazine (reading layout)"], ["굵고 대담한 임팩트", "Bold impact"], ["사양서 (정확·표 중심)", "Spec sheet (precise, tables)"],
    ["카드뉴스 (짧은 한 메시지)", "Card news (one short message)"], ["고급스럽고 절제된", "Refined and restrained"], ["밝고 경쾌한", "Bright and lively"], ["기술·데이터 중심", "Tech and data"],
    ["그림 자동 넣기", "Auto visuals"], ["아이콘 + 사진", "Icons + photos"], ["사진 사용량", "Photos"], ["적게 (표지 + 1장)", "Few (cover + 1)"], ["보통 (3~4장)", "Normal (3–4)"],
    ["많이 (최대 10장)", "Many (up to 10)"], ["내용 · 말투", "Content · tone"], ["발표 목적", "Purpose"], ["현황 보고", "Status report"], ["제안·기획", "Proposal / plan"],
    ["설득·의사결정", "Persuade / decide"], ["홍보·소개", "Promote / introduce"], ["분석·연구 공유", "Share analysis"], ["청중", "Audience"], ["일반 청중", "General"],
    ["경영진", "Executives"], ["투자자", "Investors"], ["고객", "Customers"], ["공공기관·심사위원", "Public sector / judges"], ["학생·교육생", "Students"], ["문체", "Writing style"],
    ["보고서체 (~합니다)", "Formal report"], ["개조식 (명사형)", "Bullet style"], ["친근한 말투 (~해요)", "Friendly"], ["학술 발표체", "Academic"], ["언어", "Language"],
    ["한국어", "Korean"], ["한국어 + 영어 제목", "Korean + English titles"], ["영어", "English"], ["작성 안 함", "None"], ["짧게", "Short"], ["자세히", "Detailed"],
    ["표지 정보", "Cover details"], ["발표자", "Presenter"], ["소속", "Organization"], ["날짜", "Date"], ["추가 요청사항", "Extra requests"],
    ["속성", "Properties"], ["디자인 테마", "Themes"], ["전체", "All"], ["밝은", "Light"], ["어두운", "Dark"], ["📂 최근 프로젝트", "📂 Recent projects"],
    // ── 슬라이드 설정 ──
    ["슬라이드 번호 표시", "Show slide numbers"], ["표지에도 번호 표시", "Number the cover too"], ["아래쪽 진행 막대 표시", "Show progress bar"], ["전환 효과", "Transition"],
    ["밀어내기", "Push"], ["페이드", "Fade"], ["확대 (다가오기)", "Zoom in"], ["크게 밀어내기", "Big push"], ["닦아내기", "Wipe"], ["아래에서 덮기", "Cover from below"], ["없음", "None"],
    ["애니메이션", "Animation"], ["(발표·영상에서 제목→내용 순서로 등장)", "(title, then content, when presenting or in video)"], ["은은하게", "Subtle"], ["화려하게", "Lively"],
    ["바닥글 문구 (모든 슬라이드)", "Footer text (all slides)"], ["로고 이미지 (모든 슬라이드)", "Logo image (all slides)"], ["이미지 선택", "Choose image"], ["로고 위치", "Logo position"],
    ["오른쪽 위", "Top right"], ["왼쪽 위", "Top left"], ["오른쪽 아래", "Bottom right"], ["왼쪽 아래", "Bottom left"], ["서체", "Font"],
    ["🎨 디자인 테마 패널에서 바꿀 수 있습니다.", "Change it in the 🎨 Themes panel."],
    // ── 생성 중·저장 ──
    ["슬라이드를 만들고 있어요", "Making your slides"], ["최신 자료 검색 (인터넷)", "Searching the web"], ["슬라이드 구성 · 대본 작성", "Writing slides and script"], ["디자인 적용", "Applying design"],
    ["0초 경과 · 보통 30초~1분 걸립니다", "0s · usually 30s–1 min"], ["{}초 경과 · {} 걸립니다", "{}s · {}"], ["가이드 분석·확인까지 보통 1~3분", "usually 1–3 min with guide checks"], ["보통 30초~1분", "usually 30s–1 min"],
    ["저장 중…", "Saving…"], ["저장할 위치를 선택해 주세요.", "Choose where to save."], ["중지", "Stop"],
    // ── 종료 ──
    ["결을 종료할까요?", "Quit GYEOL?"], ["만들던 내용은 저장되어 있습니다.", "Your work is saved."], ["작업이 끝나면 자동으로 종료", "Quit when the task finishes"],
    ["트레이로 내려서 작업 마무리 후 종료", "Minimize to tray and quit when done"], ["종료", "Quit"], ["취소", "Cancel"],
    ["다음부터 묻지 않고 바로 종료 (작업 중일 때는 항상 물어봅니다)", "Quit without asking next time (still asks while a task is running)"],
    ["작업이 끝나면 자동으로 종료합니다", "Will quit when the task finishes"], ["작업이 끝나면 자동으로 종료합니다 — {}", "Will quit when the task finishes — {}"],
    ["작업이 끝나 곧 종료합니다", "Task done, quitting soon"], ["작업이 진행 중입니다", "A task is running"], ["이미 '작업이 끝나면 자동 종료'로 예약되어 있습니다.", "Already set to quit when the task finishes."],
    ["{}입니다. 끝날 때까지 기다렸다가 자동으로 종료할 수 있습니다.", "{} is running. GYEOL can wait and quit when it finishes."], ["바로 종료 (진행 중인 작업 중단)", "Quit now (stop the task)"],
    ["작업이 끝나면 자동으로 종료합니다. 창은 그대로 두셔도 됩니다.", "GYEOL will quit when the task finishes. You can leave the window open."], ["자동 종료를 취소했습니다.", "Auto-quit canceled."],
    ["트레이로 내리지 못했습니다.", "Could not minimize to tray."],
    // ── 첫 실행 ──
    ["결에 오신 것을 환영합니다 👋", "Welcome to GYEOL 👋"],
    ["슬라이드를 쓰는 AI를 연결하면 바로 시작할 수 있습니다. Google의 Gemini 키는 무료로 받을 수 있고, 1분이면 됩니다.", "Connect an AI to start writing slides. A Google Gemini key is free and takes a minute to get."],
    ["키 발급 페이지 열기 ↗", "Open the key page ↗"], ["Google 계정으로 로그인한 뒤", "Sign in with your Google account, press"], ["를 누르고 키를 복사합니다.", "and copy the key."],
    ["아래 칸에 붙여 넣습니다.", "Paste it in the box below."], ["나중에 하기", "Later"], ["연결하기", "Connect"], ["✅ 연결되었습니다. 첫 슬라이드를 만들어 볼까요?", "✅ Connected. Shall we make your first deck?"],
    ["예시를 누르면 바로 만들기 시작합니다. 1분쯤 걸립니다.", "Click an example to start. It takes about a minute."], ["📎 내 문서로 시작하기", "📎 Start from my document"], ["직접 입력할게요", "I'll type my own"],
    ["📊 업무 보고", "📊 Work report"], ["2026년 우리 팀 하반기 성과와 내년 계획 보고", "Our team's H2 2026 results and next year's plan"], ["🎓 교육 자료", "🎓 Training"],
    ["직장인을 위한 생성형 AI 활용법 입문 교육", "Intro to using generative AI at work"], ["🚀 제안서", "🚀 Proposal"], ["소상공인을 위한 예약 관리 앱 서비스 제안", "A booking app proposal for small businesses"],
    ["키를 붙여 넣어 주세요.", "Paste your key."], ["확인하는 중…", "Checking…"], ["연결을 확인하지 못했습니다. 다시 시도해 주세요.", "Could not verify the connection. Try again."],
    // ── 설정 ──
    ["⚙️ AI 설정", "⚙️ Settings"], ["AI 설정", "Settings"], ["AI 엔진", "AI engine"], ["Google Gemini (추천 · 최신 자료 검색 지원)", "Google Gemini (recommended · web research)"],
    ["OpenAI GPT (API 키)", "OpenAI GPT (API key)"], ["ChatGPT 구독 로그인 (Codex)", "ChatGPT subscription login (Codex)"], ["Claude 구독 로그인 (Claude Code)", "Claude subscription login (Claude Code)"],
    ["Gemini 구글 계정 로그인 (Gemini CLI)", "Gemini Google account login (Gemini CLI)"], ["AI 없이 샘플 템플릿", "Sample template (no AI)"], ["구독 로그인", "Subscription login"],
    ["확인 중…", "Checking…"], ["상태 새로고침", "Refresh status"], ["🔐 브라우저에서 로그인", "🔐 Sign in in the browser"], ["Gemini 모델", "Gemini model"],
    ["gemini-3.5-flash (추천 · 안 되면 3.6 → 3.7 → 3.8 순서로 자동 전환)", "gemini-3.5-flash (recommended · falls back to 3.6 → 3.7 → 3.8)"], ["gemini-3.5-flash-lite (가장 빠름)", "gemini-3.5-flash-lite (fastest)"],
    ["Gemini API 키", "Gemini API key"], ["사용할 수 없는 모델이면 다른 모델로 자동 전환됩니다. (새로 만든 키는 2.5 계열을 쓸 수 없습니다)", "If a model is unavailable, another is used automatically. (New keys can't use the 2.5 models.)"],
    ["OpenAI API 키", "OpenAI API key"], ["Pixabay API 키", "Pixabay API key"], ["(선택)", "(optional)"],
    ["pixabay.com 무료 가입 → API 문서 페이지에서 키 확인. 비워 두면 무료 사진 검색(Openverse)을 씁니다.", "Sign up free at pixabay.com and copy the key from the API docs page. If empty, free Openverse search is used."],
    ["저장", "Save"], ["화면 언어", "Display language"], ["설정을 저장했습니다.", "Settings saved."], ["서버와 통신하지 못했습니다.", "Could not reach the app server."],
    ["Google 계정 로그인 (Gemini)", "Google account login (Gemini)"], ["{} 구독 로그인", "{} subscription login"], ["쓸 수 없습니다.", "Not available."],
    ["❌ 프로그램이 설치되어 있지 않습니다", "❌ Not installed"], ["먼저 설치해 주세요 (명령 프롬프트에서): {}", "Install it first (in Command Prompt): {}"], ["✅ 연결됨{}", "✅ Connected{}"],
    ["이 구독 계정으로 슬라이드를 만들고 고칩니다. 별도 API 키는 필요 없습니다. 생성 속도는 Gemini보다 느릴 수 있고(1~3분), 최신 자료 검색은 쓸 수 없습니다.", "Slides are written with this subscription. No API key needed. It can be slower than Gemini (1–3 min) and can't search the web."],
    ["{} 로그인이 연결되었습니다.", "{} login connected."], ["⏳ 브라우저에서 로그인을 마쳐 주세요…", "⏳ Finish signing in in the browser…"], ["로그인이 필요합니다", "Sign-in required"],
    ["버튼을 누르면 기본 브라우저(크롬 등)에 로그인 창이 열립니다. 로그인을 마치면 이 화면이 자동으로 '연결됨'으로 바뀝니다.", "Press the button to open a sign-in page in your browser. When you finish, this changes to 'Connected'."],
    ["로그인 창을 열었습니다.", "Opened the sign-in page."], ["로그인을 시작하지 못했습니다.", "Could not start sign-in."],
    // ── 라이선스 ──
    ["🔑 라이선스", "🔑 License"], ["라이선스 키 (16자리)", "License key (16 characters)"],
    ["구매 후 받은 키를 넣어 주세요. 한 키는 한 번에 PC 한 대에서 쓸 수 있고, 다른 PC에서 넣으면 이전 PC는 자동으로 로그아웃됩니다.", "Enter the key you received. One key works on one PC at a time; entering it on another PC signs the old one out."],
    ["이 PC에서 로그아웃", "Sign out on this PC"], ["확인", "OK"], ["개발 실행", "Dev mode"], ["키 입력 필요", "Key needed"], ["무제한", "Unlimited"], ["{} 토큰", "{} tokens"], ["{} · {}일", "{} · {} days"],
    ["✓ 사용 중", "✓ Active"], ["· 키 {}", "· key {}"], ["사용 기한:", "Valid until:"], ["까지 (남은 {}일)", "({} days left)"], ["무기한", "No expiry"], ["사용 기간이 끝났습니다.", "Your license has expired."],
    ["연장하시려면 구매처로 문의해 주세요. 새 키를 받으셨다면 아래에 넣어 주세요.", "Contact the seller to renew. If you have a new key, enter it below."], ["사용이 중지된 라이선스입니다.", "This license is suspended."],
    ["구매처로 문의해 주세요.", "Please contact the seller."], ["라이선스를 확인하지 못했습니다.", "Could not verify the license."], ["인터넷 연결을 확인한 뒤 다시 확인을 눌러 주세요.", "Check your internet connection and press Retry."],
    ["결(GYEOL)을 사용하려면", "To use GYEOL you need a"], ["라이선스 키", "license key"], ["가 필요합니다.", "."],
    ["키를 넣기 전에도 화면은 둘러보실 수 있지만, 만들기·편집·내보내기는 키 확인 후에 됩니다.", "You can look around without a key, but creating, editing and exporting need a verified key."],
    ["다시 확인", "Retry"], ["다른 키로 바꾸기 (선택)", "Use a different key (optional)"], ["라이선스 키를 확인한 뒤에 사용할 수 있습니다.", "Available after the license key is verified."],
    ["이 PC에서 라이선스를 로그아웃할까요? 다시 쓰려면 키를 다시 넣어야 합니다.", "Sign this PC out of the license? You'll need to enter the key again to use it."],
    ["아직 사용할 수 없습니다.", "Not available yet."], ["확인 중 문제가 생겼습니다. 다시 시도해 주세요.", "Something went wrong while checking. Try again."],
    // ── 업데이트 ──
    ["버전 {}", "Version {}"], ["✅ v{}으로 업데이트되었습니다", "✅ Updated to v{}"], ["⚠️ 업데이트가 완료되지 않았습니다", "⚠️ The update did not finish"], ["⚠️ 업데이트 실패", "⚠️ Update failed"],
    ["업데이트 받는 중", "Downloading update"], ["업데이트 적용 중", "Applying update"], ["프로그램이 잠시 닫혔다가 자동으로 다시 시작됩니다.", "GYEOL will close and restart by itself."],
    ["새 버전 v{}", "New version v{}"], ["새 버전 v{} 배포됨", "New version v{} released"],
    ["소스로 실행 중이라 자동 설치는 하지 않습니다. 프로그램을 다시 실행하면 폴더의 최신 코드가 적용됩니다.", "Running from source, so nothing is installed automatically. Restart to use the latest code in the folder."],
    ["업데이트를 받으면 프로그램이 잠시 닫혔다가 자동으로 다시 시작됩니다. 만들던 내용은 저장되어 있습니다. 진행할까요?", "GYEOL will close and restart to update. Your work is saved. Continue?"],
    // ── 넣기(사진·그림·아이콘·도형) ──
    ["🔍 무료 사진", "🔍 Free photos"], ["🎨 AI 그림", "🎨 AI image"], ["⭐ 아이콘", "⭐ Icons"], ["◼ 도형", "◼ Shapes"], ["📁 내 파일", "📁 My files"], ["넣는 방식", "Placement"],
    ["오른쪽 절반을 사진으로", "Photo on the right half"], ["원하는 곳에 자유롭게", "Anywhere (free)"], ["검색", "Search"],
    ["저작권 표시 없이 상업적으로 쓸 수 있는 무료 사진(CC0·퍼블릭 도메인)만 찾습니다. 한글로 검색해도 됩니다.", "Finds only free photos you can use commercially without credit (CC0, public domain). Korean or English search works."],
    ["찾는 중… 처음 찾는 단어는 20초 정도 걸릴 수 있어요", "Searching… a new word can take about 20 seconds"], ["사진처럼", "Photo"], ["일러스트", "Illustration"], ["🎨 그림 만들기", "🎨 Generate"],
    ["무료 생성은 한 장에 20~40초 걸리고 화질이 낮을 수 있습니다. (유료 Gemini 키가 있으면 더 좋은 그림으로 만듭니다)", "Free generation takes 20–40s per image and may be low quality. (A paid Gemini key makes better images.)"],
    ["그림을 그리는 중… 최대 1분(ChatGPT 구독으로 그릴 때는 1~2분) 걸릴 수 있어요", "Drawing… up to 1 min (1–2 min with a ChatGPT subscription)"], ["이 그림 넣기", "Insert this image"], ["다시 만들기", "Try again"],
    ["도형 색은 넣은 뒤 위쪽 막대에서 테마 색으로 바꿀 수 있습니다.", "After inserting, change the shape color in the properties panel."], ["📁 사진·그림 파일 선택", "📁 Choose a picture file"], ["올리는 중…", "Uploading…"],
    ["사각형", "Rectangle"], ["둥근 사각형", "Rounded rectangle"], ["원", "Circle"], ["연한 강조 상자", "Soft highlight box"], ["선", "Line"], ["화살표", "Arrow"], ["삼각형", "Triangle"], ["별", "Star"],
    ["말풍선", "Speech bubble"], ["체크 원", "Check circle"], ["사진을 바꿨습니다.", "Photo replaced."], ["사진을 받지 못했습니다. 다른 사진을 골라 주세요.", "Could not download the photo. Pick another one."],
    ["사진 검색에 실패했습니다.", "Photo search failed."], ["ChatGPT 구독의 이미지 생성으로 그렸습니다.", "Drawn with ChatGPT subscription image generation."], ["그림을 만들지 못했습니다.", "Could not make the image."],
    ["아이콘을 불러오지 못했습니다.", "Could not load icons."], ["찾는 아이콘이 없습니다. 다른 말로 찾아 보세요.", "No icons found. Try another word."], ["20MB 이하 파일만 올릴 수 있습니다.", "Files must be 20 MB or smaller."],
    ["파일을 올리지 못했습니다.", "Could not upload the file."],
    // ── 제목·툴팁·안내 ──
    ["프레젠테이션 제목", "Presentation title"], ["클릭해서 제목 수정", "Click to rename"], ["AI가 고른 사진을 찾아서 해당 슬라이드에 넣는 중입니다. 계속 작업하셔도 됩니다.", "Finding the photos the AI chose and placing them. You can keep working."],
    ["현재 슬라이드 뒤에 AI로 새 슬라이드 추가", "Add a slide after this one with AI"], ["이전 슬라이드 (←)", "Previous slide (←)"], ["다음 슬라이드 (→)", "Next slide (→)"],
    ["이 슬라이드만 AI로 고치거나 다시 만들기", "Fix or rewrite only this slide with AI"], ["이 슬라이드에 어울리는 도식·도형·꾸밈·스타일을 추천합니다", "Suggests diagrams, shapes, decorations and styles for this slide"],
    ["모든 슬라이드를 화면으로 확인해 글자 넘침·겹침을 AI가 찾아서 고쳐 줍니다", "The AI looks at every slide and fixes overflowing or overlapping text"], ["사진·그림·아이콘·도형 넣기", "Insert photos, images, icons or shapes"],
    ["되돌리기 (Ctrl+Z)", "Undo (Ctrl+Z)"], ["이 슬라이드의 발표 대본 보기", "Show this slide's script"], ["모든 슬라이드를 한눈에 (O)", "All slides at a glance (O)"],
    ["대본·타이머·다음 슬라이드가 있는 발표자 창 (S)", "Presenter window with script, timer and next slide (S)"], ["전체화면 (F)", "Fullscreen (F)"],
    ["가지고 있는 문서·사진으로 발표 자료 만들기 (PDF, Word, 파워포인트, 한글, 엑셀, 텍스트, 사진). 파일 안의 사진도 꺼내서 어울리는 장에 넣습니다", "Make a deck from your documents and photos (PDF, Word, PowerPoint, HWPX, Excel, text, photos). Photos inside your files are placed on matching slides"],
    ["제안요청서·과제 안내·발표 지침 같은 가이드를 넣으면 요구 사항을 분석해 그대로 맞춘 PPT를 만듭니다", "Add an RFP, assignment brief or guidelines and the deck is written to match its requirements"],
    ["어떤 발표 자료를 만들까요? 예) 2026년 대한민국 고용 동향 보고서", "What should the deck be about? e.g. 2026 global EV market outlook"],
    ["예) 발표 10분, 15장 이내 1. 사업 개요 2. 추진 배경 3. 추진 전략(배점 30) 4. 추진 일정 5. 예산 6. 기대 효과 필수 키워드: 디지털 전환, ESG 표지에 기관명 ○○시청 표기", "e.g. 10-minute talk, up to 15 slides. 1. Overview 2. Background 3. Strategy (30 points) 4. Schedule 5. Budget 6. Expected impact. Required keywords: digital transformation, ESG. Put the agency name on the cover."],
    ["분야에 맞는 순서와 도식으로 구성합니다", "Uses an order and diagrams that fit the field"], ["표, 막대 그래프, 타임라인, 원형 게이지 같은 시각 요소를 얼마나 쓸지", "How much to use tables, bar charts, timelines and gauges"],
    ["화살표 프로세스, 깔때기, 피라미드, 순환, SWOT, 매트릭스, 허브, 벤 다이어그램 같은 도식을 얼마나 쓸지", "How much to use process arrows, funnels, pyramids, cycles, SWOT, matrices, hubs and Venn diagrams"],
    ["구성과 문장의 느낌. 색과 글꼴은 테마가 정합니다. 자동이면 고른 테마에 맞춥니다", "The feel of the layout and writing. Colors and fonts come from the theme. Auto follows the theme."],
    ["실제 무료 사진(Pixabay 등)을 몇 장이나 넣을지", "How many real free photos (Pixabay etc.) to use"], ["예) 홍길동 팀장", "e.g. Alex Kim, Team Lead"], ["예) 전략기획팀", "e.g. Strategy Team"], ["예) 2026년 10월", "e.g. October 2026"],
    ["예) 경쟁사 비교를 꼭 넣어 줘 / 숫자는 표로 정리해 줘", "e.g. Include a competitor comparison / Put numbers in a table"], ["테마 이름·스타일 검색", "Search themes or styles"], ["예) © 2026 회사명 · 대외비", "e.g. © 2026 Company · Confidential"],
    ["복사한 Gemini API 키 붙여 넣기", "Paste your Gemini API key"], ["Google AI Studio에서 발급받은 키", "Key from Google AI Studio"], ["넣으면 사진 검색이 빨라지고 사진이 더 좋아집니다", "Makes photo search faster and better"],
    ["예) 전기차 충전소 / 회의하는 직장인 / 반도체 공장", "e.g. EV charging station / office meeting / chip factory"], ["어떤 그림이 필요한가요? 예) 햇살이 드는 현대적인 사무실에서 노트북으로 일하는 모습", "What image do you need? e.g. someone working on a laptop in a sunny modern office"],
    ["아이콘 검색 (예: 성장, 사람, 돈, 공장, AI)", "Search icons (e.g. growth, people, money, factory, AI)"],
    // ── 목록·테마·내 자료 ──
    ["슬라이드 {}", "Slide {}"], ["{}번 슬라이드를 삭제했습니다.", "Deleted slide {}."], ["{}장", "{} slides"], ["발표자 대본 · {}. {}", "Script · {}. {}"],
    ["발표자 창을 열 수 없습니다. 팝업 차단을 해제해 주세요.", "Could not open the presenter window. Allow pop-ups."], ["'{}' 분위기에는 {}({}) 같은 테마가 어울립니다.", "For a '{}' mood, themes like {} ({}) fit well."],
    ["이 테마로 바꾸기", "Use this theme"], ["전체 {}", "All {}"], ["조건에 맞는 테마가 없습니다.", "No matching themes."], ["{}종", "{}"], ["테마 적용: {} · {}", "Theme applied: {} · {}"],
    ["최신 인터넷 조사도 함께 반영", "Also research the web"], ["자료로 어떤 발표를 만들까요? 비워 두면 핵심을 정리합니다 (예: 임원 보고용으로 요약)", "What deck should these files become? Leave empty to summarize the key points (e.g. an executive summary)"],
    ["문서는 5개까지 넣을 수 있습니다.", "You can add up to 5 documents."], ["사진 파일은 16장까지 넣을 수 있습니다.", "You can add up to 16 photo files."], ["{}: 20MB 이하 파일만 넣을 수 있습니다.", "{}: files must be 20 MB or smaller."],
    ["{}: 글자와 사진을 읽는 중입니다. 스캔 문서나 사진이 많으면 최대 1분 걸립니다.", "{}: reading text and photos. Scans or many photos can take up to a minute."], ["{}자", "{} chars"], ["(앞 20,000자만 사용)", "(first 20,000 characters used)"],
    ["20MB 이하 파일만 넣을 수 있습니다.", "Files must be 20 MB or smaller."], ["{} 내용을 가이드에 넣었습니다.", "Added {} to the guide."], ["파일을 읽지 못했습니다.", "Could not read the file."],
    ["(앞부분만 사용)", "(beginning only)"], ["(길어서 핵심만 요약해 사용)", "(long, so summarized)"], ["· 스캔 글자 읽음", "· scan read"], ["· 사진 {}장", "· {} photos"],
    ["가이드에서 발표 자료 요구 사항(장수·목차·키워드 등)을 찾지 못해, 가이드 내용을 참고 자료로 써서 만들었습니다.", "No deck requirements (slide count, sections, keywords) were found in the guide, so it was used as reference material."],
    ["분량", "Length"], ["구성 (가이드 순서)", "Sections (guide order)"], ["키워드", "Keywords"], ["그대로 넣을 문구", "Exact phrases"], ["금지어", "Banned words"],
    ["꼭 넣을 자료 — 직접 확인", "Required material — check yourself"], ["그 밖의 지침 — 직접 확인", "Other instructions — check yourself"], ["📋 가이드 반영 확인", "📋 Guide check"],
    ["✅ 확인할 수 있는 요구 사항은 모두 반영됐습니다.", "✅ Every checkable requirement is met."],
    ["만들고 싶은 발표 주제를 입력하거나 내 자료·가이드를 넣어 주세요.", "Type a topic, or add your files or a guide."], ["생성에 실패했습니다.", "Generation failed."],
    ["· 최신 자료 {}건 반영{}", "· {} web sources used{}"], [" (인터넷 조사)", " (web research)"], ["· 사진 {}장은 찾는 대로 넣습니다", "· {} photos will be added as they are found"], ["· 내 사진 {}/{}장 배치", "· {}/{} of your photos placed"],
    ["최신 자료 검색을 쓸 수 없어(네트워크 확인) AI가 알고 있는 내용으로 만들었습니다. 수치는 직접 확인해 주세요.", "Web search was unavailable (check your network), so the AI used what it knows. Please verify the numbers."],
    ["서버와 통신하지 못했습니다. 프로그램을 다시 실행해 주세요.", "Could not reach the app server. Restart GYEOL."],
    ["편집 가능한 파워포인트", "Editable PowerPoint"], ["파워포인트(이미지)", "PowerPoint (images)"], ["이미지 묶음", "Image set"], ["{}로 저장", "Save as {}"],
    ["저장할 위치를 선택해 주세요. 선택 후 변환에 10~30초 걸릴 수 있습니다.", "Choose where to save. Converting can take 10–30 seconds."], ["폴더 열기", "Open folder"], ["저장에 실패했습니다.", "Save failed."],
    // 옵션 요약 조각
    ["보고서체", "Formal"], ["개조식", "Bullets"], ["친근한", "Friendly"], ["학술", "Academic"], ["한영", "KO+EN"], ["에디토리얼", "Editorial"], ["차분한 여백", "Calm"], ["매거진", "Magazine"],
    ["대담한", "Bold"], ["사양서", "Spec"], ["카드뉴스", "Card news"], ["고급·절제", "Refined"], ["경쾌한", "Lively"], ["기술·데이터", "Tech/data"], ["본문 {}장", "{} body slides"], ["목차", "Agenda"],
    ["출처", "Sources"], ["최신 검색", "Web search"], ["아이콘·사진{}", "Icons & photos{}"], ["아이콘", "Icons"], ["표·그래프 적극", "Rich charts"], ["표·그래프 최소", "Minimal charts"], ["영업", "Sales"],
    ["사업계획", "Business plan"], ["마케팅", "Marketing"], ["교육", "Education"], ["보고", "Report"], ["연구", "Research"], ["회사소개", "Company intro"], ["행사", "Event"],
    ["인포그래픽 많이", "Many infographics"], ["인포그래픽 없음", "No infographics"], ["사진 적게", "Few photos"], ["사진 많이", "Many photos"],
    // 프로젝트
    ["불러오는 중…", "Loading…"], ["저장된 프로젝트가 없습니다.", "No saved projects."], ["{} · {}장 · {}", "{} · {} slides · {}"],
    // ── 속성 패널 ──
    ["강조색", "Accent"], ["보조색", "Secondary"], ["포인트색", "Highlight"], ["글자색", "Text color"], ["연한 배경색", "Soft background"], ["흰색", "White"], ["검은색", "Black"], ["(테마 서체)", "(theme font)"],
    ["● 고치는 중", "● Editing"], ["✓ 자동 저장됨", "✓ Saved"], ["저장 실패", "Save failed"], ["글자", "Text"], ["를 누르면 바로 고칠 수 있고, 여기에 글꼴·크기·색 옵션이 나옵니다.", " can be clicked and edited right away; font, size and color options appear here."],
    ["그림·도형", "Pictures and shapes"], ["을 누르면 끌어서 옮기고, 위치·크기·투명도를 바꿀 수 있습니다.", " can be clicked, dragged, and changed in position, size and opacity."],
    ["Enter 줄바꿈 · Esc 선택 해제 · Ctrl+Z 되돌리기", "Enter new line · Esc deselect · Ctrl+Z undo"], ["고친 내용은 자동으로 저장됩니다.", "Changes save automatically."],
    ["글자 (선택한 부분)", "Text (selection)"], ["글꼴", "Font"], ["크기 (px)", "Size (px)"], ["스타일", "Style"], ["정렬", "Align"], ["왼쪽", "Left"], ["가운데", "Center"], ["오른쪽", "Right"],
    ["줄 간격", "Line spacing"], ["서식 지우기", "Clear formatting"], ["선택 해제", "Deselect"], ["글자 일부를 드래그해 고르면 그 부분에만 적용됩니다.", "Drag across part of the text to apply only to that part."],
    ["사진 패널", "Photo panel"], ["그림", "Image"], ["위치 · 크기 (슬라이드 1600×900 기준)", "Position · size (on a 1600×900 slide)"], ["폭", "W"], ["높이", "H"],
    ["{} · 화살표 키로 1px, Shift+화살표로 10px 이동", "{} · arrows move 1px, Shift+arrows 10px"], ["투명도", "Opacity"], ["모서리", "Corners"], ["색", "Color"], ["앞으로", "Bring forward"], ["글자 뒤로", "Behind text"], ["복제", "Duplicate"], ["삭제", "Delete"],
    ["슬라이드 옆에 붙는 사진 자리입니다.", "The photo area beside the slide."], ["사진 바꾸기", "Replace photo"], ["Delete 삭제 · Esc 선택 해제", "Delete removes · Esc deselects"],
    ["원본 슬라이드를 찾지 못했습니다.", "Could not find the original slide."], ["수정한 위치를 찾지 못했습니다.", "Could not find the edited spot."], ["미리보기를 다시 불러옵니다.", "Reloading the preview."],
    ["자동 저장에 실패했습니다. 서버 연결을 확인해 주세요.", "Autosave failed. Check the connection to the app."], ["X", "X"], ["Y", "Y"],
    // ── AI 고치기 ──
    ["더 간결하게", "More concise"], ["더 자세하게", "More detail"], ["숫자를 그래프로", "Numbers as a chart"], ["카드형으로 정리", "As cards"], ["아이콘 넣기", "Add icons"], ["어울리는 사진 넣기", "Add a fitting photo"],
    ["제목을 더 강렬하게", "Punchier title"], ["다른 레이아웃으로", "Different layout"], ["쉬운 말로", "Simpler words"], ["사례 소개", "Case study"], ["핵심 요약", "Key summary"], ["비교 분석", "Comparison"],
    ["추진 일정(로드맵)", "Roadmap"], ["기대 효과", "Expected impact"], ["질의응답 대비 FAQ", "FAQ for Q&A"],
    ["{}번 슬라이드 「{}」를 고칩니다. 비워 두면 같은 내용으로 새로 만듭니다.", "Fixing slide {} “{}”. Leave empty to rewrite it with the same content."],
    ["{}번 슬라이드 「{}」 바로 뒤에 새 슬라이드를 넣습니다.", "Adding a new slide right after slide {} “{}”."],
    ["예) 3개 카드로 나눠 줘 / 숫자를 막대 그래프로 보여 줘 / 경쟁사 비교를 추가해 줘", "e.g. Split into 3 cards / Show the numbers as a bar chart / Add a competitor comparison"],
    ["어떤 내용의 슬라이드를 넣을까요? 예) 국내 도입 기업 사례 3가지", "What should the new slide cover? e.g. 3 companies that adopted it"],
    ["✨ 이 슬라이드 고치기", "✨ Fix this slide"], ["✨ 새 슬라이드 만들기", "✨ Make the slide"], ["새 슬라이드에 넣을 내용을 적어 주세요.", "Describe what the new slide should contain."],
    ["{}번 슬라이드를 AI로 고치는 중", "Fixing slide {} with AI"], ["새 슬라이드를 만드는 중", "Making the new slide"], ["최신 자료를 검색한 뒤 작성합니다. 보통 20~40초 걸립니다.", "Searches the web first. Usually 20–40 seconds."],
    ["보통 10~20초 걸립니다.", "Usually 10–20 seconds."], ["고쳤습니다. 마음에 안 들면 \"되돌리기\"를 누르거나 이어서 말해 주세요.", "Done. If you don't like it, press \"Undo\" or keep chatting."],
    ["고쳤습니다. 마음에 안 들면 \"되돌리기\"를 누르거나 이어서 말해 주세요.", "Done. If you don't like it, press \"Undo\" or keep chatting."], ["고치지 못했습니다. 다시 시도해 주세요.", "Could not fix it. Try again."],
    // ── 장표 추천 ──
    ["{}번 장표 추천", "Slide {} advice"], ["내용을 살펴보는 중…", "Reading the content…"], ["· 지금 구성:", "· current layout:"], ["이 장표는", "This looks like a"], ["장표로 보입니다{}", "slide{}"],
    ["어울리는 도식·구성", "Fitting layouts and diagrams"], ["표지·간지·마무리 장표는 도식보다 아래 꾸밈으로 분위기를 살리는 편이 좋습니다.", "Cover, divider and closing slides work better with the decorations below than with diagrams."],
    ["이 구성으로 바꾸기", "Use this layout"], ["어울리는 도형·꾸밈", "Fitting decorations"], ["얹기", "Add"], ["어울리는 디자인 스타일 (덱 전체에 적용)", "Fitting design styles (whole deck)"],
    ["{}번 슬라이드를 '{}'(으)로 바꾸는 중", "Changing slide {} to '{}'"], ["내용은 그대로 두고 구성만 바꿉니다. 보통 10~20초 걸립니다.", "Keeps the content and changes only the layout. Usually 10–20 seconds."],
    ["'{}' 구성으로 바꿨습니다.", "Changed to '{}'."], ["모든 장표를 살펴보는 중…", "Reviewing every slide…"], ["장표를 누르면 그 장으로 가서 자세한 추천을 봅니다.", "Click a slide to go there and see detailed advice."],
    // ── AI 검수 ──
    ["검수를 시작하지 못했습니다.", "Could not start the review."], ["AI가 슬라이드를 검수하는 중", "The AI is reviewing your slides"], ["화면으로 확인하고 문제가 있는 장만 고칩니다. 한 장에 5~15초 걸립니다.", "It looks at each slide and fixes only those with problems. 5–15 seconds per slide."],
    ["중지하는 중…", "Stopping…"], ["검수하지 못했습니다.", "Review failed."], ["{}번", "#{}"], ["· 아직 확인이 필요한 장: {}번", "· still needs a look: #{}"],
    ["{}장을 검수해 {} 슬라이드를 고쳤습니다.{}", "Reviewed {} slides and fixed {}.{}"], ["{}장을 검수했습니다. 확인이 필요한 장: {}번 (자동으로 고치지 못했습니다)", "Reviewed {} slides. Needs a look: #{} (could not fix automatically)"],
    ["{}장을 모두 검수했고 문제가 없습니다.", "Reviewed all {} slides. No problems found."],
    ["초기 데이터를 불러오지 못했습니다.", "Could not load the initial data."], ["샘플 프레젠테이션", "Sample presentation"], ["새 프레젠테이션", "New presentation"],
    // ── 서버 안내 ──
    ["알 수 없는 요청입니다.", "Unknown request."], ["되돌렸습니다.", "Undone."], ["슬라이드를 찾을 수 없습니다. 화면을 새로 고쳐 주세요.", "Slide not found. Refresh the screen."], ["수정 내용을 저장했습니다.", "Changes saved."],
    ["이미 검수하는 중입니다.", "A review is already running."], ["검수할 슬라이드가 없습니다.", "No slides to review."],
    ["AI 검수는 화면을 보는 Gemini 키가 필요합니다. ⚙️ 설정에서 Gemini 키를 입력해 주세요. (글쓰기 AI는 구독 로그인이어도 됩니다)", "AI review needs a Gemini key to look at the slides. Enter one in ⚙️ Settings. (The writing AI can still be a subscription login.)"],
    ["키가 너무 짧습니다. 복사한 키 전체를 붙여 넣어 주세요.", "The key is too short. Paste the whole key."], ["검색어를 영어로 바꾸지 못했습니다. 영어로 검색해 보세요. (예: meeting room)", "Could not translate the search. Try English (e.g. meeting room)."],
    ["검색 결과가 없습니다. 다른 단어로 찾아 보세요.", "No results. Try another word."], ["그림을 처리하지 못했습니다: {}", "Could not process the image: {}"], ["더 되돌릴 작업이 없습니다.", "Nothing more to undo."],
    ["넣었습니다. 끌어서 위치와 크기를 맞춰 보세요.", "Inserted. Drag to position and resize it."], ["처리 중 오류가 발생했습니다: {}", "An error occurred: {}"], ["검수 중 오류가 발생했습니다: {}", "An error occurred during review: {}"],
    ["허용되지 않은 접근입니다.", "Access denied."], ["키가 정상입니다.", "The key works."], ["Google 서버 응답 오류({})입니다. 잠시 뒤 다시 시도해 주세요.", "Google server error ({}). Try again shortly."],
    ["인터넷 연결을 확인한 뒤 다시 시도해 주세요.", "Check your internet connection and try again."], ["어떤 그림을 만들지 적어 주세요.", "Describe the image to make."], ["사진을 넣었습니다.", "Photo added."], ["사진을 뺐습니다.", "Photo removed."],
    ["검수하는 동안 다른 프로젝트를 열어서 결과를 반영하지 않았습니다.", "Another project was opened during the review, so the results were not applied."], ["보낸 내용이 너무 큽니다.", "The request is too large."],
    ["{}장의 슬라이드를 만들었습니다.", "Created {} slides."], ["인터넷 조사 결과를 가져오지 못해 AI가 알고 있는 내용으로 만들었습니다. 수치는 직접 확인해 주세요.", "Web research failed, so the AI used what it knows. Please verify the numbers."],
    ["{}로 저장했습니다.", "Saved as {}."], ["사용할 수 없는 키입니다. 복사가 빠졌거나 잘못된 키가 아닌지 확인해 주세요.", "This key can't be used. Check that it was copied completely and correctly."],
    ["넣을 개체 형식이 올바르지 않습니다.", "Invalid object."], ["대본을 저장했습니다.", "Script saved."], ["이 버전에서는 쓸 수 없습니다.", "Not available in this version."],
    ["가이드 맞춤은 AI가 필요합니다. ⚙️ 설정에서 AI 엔진을 골라 주세요.", "Guide matching needs an AI. Choose an AI engine in ⚙️ Settings."], ["프로젝트를 찾을 수 없습니다.", "Project not found."], ["슬라이드를 찾을 수 없습니다.", "Slide not found."],
    ["이 버전에서는 구독 로그인 방식을 쓸 수 없습니다. API 키 방식을 골라 주세요.", "Subscription login isn't available in this version. Choose an API key engine."], ["지원하지 않는 형식입니다.", "Unsupported format."],
    ["저장을 취소했습니다.", "Save canceled."], ["사진 파일을 찾을 수 없습니다.", "Photo file not found."], ["슬라이드를 삭제했습니다.", "Slide deleted."], ["생성 중 오류가 발생했습니다: {}", "An error occurred while generating: {}"],
    ["로고 이미지는 600KB 이하로 올려 주세요.", "Logo images must be 600 KB or smaller."], ["저장 중 오류가 발생했습니다: {}", "An error occurred while saving: {}"], ["슬라이드를 복제했습니다.", "Slide duplicated."],
    ["마지막 한 장은 삭제할 수 없습니다.", "The last slide can't be deleted."], ["{}번째로 옮겼습니다.", "Moved to position {}."], ["잘못된 선택입니다.", "Invalid choice."], ["{}번 슬라이드를 AI로 고쳤습니다.", "Fixed slide {} with AI."],
    ["{}번에 새 슬라이드를 추가했습니다.", "Added a new slide at {}."], ["알 수 없는 작업입니다.", "Unknown action."], ["Gemini 호출에 실패했습니다. ({})", "Gemini call failed. ({})"],
    ["AI 없이 샘플 템플릿 모드에서는 슬라이드를 AI로 고칠 수 없습니다. ⚙️ 설정에서 AI 엔진을 골라 주세요.", "Slides can't be fixed with AI in sample-template mode. Choose an AI engine in ⚙️ Settings."],
    ["응답이 비어 있습니다: {}", "Empty response: {}"], ["응답이 비어 있습니다.", "Empty response."], ["Gemini 서버가 지금 혼잡합니다. 1~2분 뒤에 다시 시도해 주세요.", "Gemini is busy right now. Try again in 1–2 minutes."],
    ["Gemini 사용 한도를 넘었습니다. 잠시 뒤 다시 시도하거나 ⚙️ 설정에서 다른 모델을 골라 주세요.", "Gemini quota exceeded. Try again later or pick another model in ⚙️ Settings."], ["인터넷 조사 결과를 가져오지 못했습니다. 네트워크를 확인해 주세요.", "Web research failed. Check your network."],
    ["API 키가 없습니다. 오른쪽 위 ⚙️ 설정에서 키를 입력해 주세요.", "No API key. Enter one in ⚙️ Settings (top right)."], ["AI 응답에서 슬라이드를 찾지 못했습니다. 다시 시도해 주세요.", "No slides found in the AI response. Try again."],
    ["스캔한 문서의 글자를 읽으려면 ⚙️ 설정에서 Gemini 키를 연결해 주세요.", "To read scanned documents, connect a Gemini key in ⚙️ Settings."], ["알 수 없는 AI 공급자: {}", "Unknown AI provider: {}"],
    ["Gemini API 키가 올바르지 않습니다. ⚙️ 설정에서 키를 확인해 주세요.", "The Gemini API key is invalid. Check it in ⚙️ Settings."], ["파일 안의 내용이 너무 큽니다.", "The file contents are too large."],
    ["Word 문서 형식이 아닙니다.", "Not a Word document."], ["한글 문서 형식이 아닙니다.", "Not an HWPX document."], ["엑셀 문서 형식이 아닙니다.", "Not an Excel document."], ["암호가 걸린 PDF입니다. 암호를 푼 뒤 다시 넣어 주세요.", "This PDF is password-protected. Remove the password and try again."],
    ["파일이 너무 큽니다 (20MB 이하만 가능).", "The file is too large (20 MB max)."], ["빈 파일입니다.", "The file is empty."], ["파일에서 읽을 수 있는 글자가 거의 없습니다.", "There is almost no readable text in the file."],
    ["파일이 손상되었거나 암호가 걸려 있습니다.", "The file is damaged or password-protected."], ["PDF 파일을 열 수 없습니다.", "Could not open the PDF."], ["파일을 읽는 중 문제가 생겼습니다: {}", "A problem occurred while reading the file: {}"],
    ["글자를 읽을 수 없는 PDF입니다 (사진으로 스캔한 문서). 글자가 있는 원본 파일을 넣어 주세요.", "This PDF has no readable text (it's a scan). Use the original file with text."],
    ["사진 속 글자를 읽으려면 ⚙️ 설정에서 Gemini 키를 연결해 주세요.", "To read text in photos, connect a Gemini key in ⚙️ Settings."], ["HWP는 바로 읽을 수 없습니다. 한글에서 'HWPX'로 저장하거나 PDF로 저장해 넣어 주세요.", "HWP can't be read directly. Save it as HWPX or PDF in Hangul and add that."],
    ["옛 형식({})은 읽을 수 없습니다. {}x 로 저장하거나 PDF로 저장해 넣어 주세요.", "The old format ({}) can't be read. Save it as {}x or PDF and add that."],
    ["지원하지 않는 파일입니다. PDF, Word, 파워포인트, 한글(HWPX), 엑셀, 텍스트, 사진(PNG·JPG) 파일을 넣어 주세요.", "Unsupported file. Use PDF, Word, PowerPoint, HWPX, Excel, text or photo (PNG, JPG) files."],
    ["Gemini가 그림을 돌려주지 않았습니다.", "Gemini returned no image."], ["이미지 데이터가 비어 있습니다.", "The image data is empty."], ["지원하지 않는 이미지 형식입니다. (JPG, PNG, WEBP, GIF, SVG)", "Unsupported image format. (JPG, PNG, WEBP, GIF, SVG)"],
    ["스크립트가 들어 있는 SVG는 넣을 수 없습니다.", "SVGs containing scripts can't be inserted."], ["이미지 파일을 읽지 못했습니다.", "Could not read the image file."], ["이미지가 너무 큽니다. 20MB 이하로 올려 주세요.", "The image is too large. Upload 20 MB or less."],
    ["잘못된 이미지 주소입니다.", "Invalid image URL."], ["무료 AI 그림 서버가 바쁩니다. 잠시 뒤 다시 시도해 주세요.", "The free AI image server is busy. Try again shortly."], ["이 이미지 주소는 열 수 없습니다. ({})", "This image URL can't be opened. ({})"],
    ["Pixabay 사진 검색에 실패했습니다. 잠시 뒤 다시 시도해 주세요.", "Pixabay search failed. Try again shortly."], ["Pixabay 키가 올바르지 않습니다. ⚙️ 설정에서 확인해 주세요.", "The Pixabay key is invalid. Check it in ⚙️ Settings."],
    ["사진 검색 서버가 응답하지 않습니다. 잠시 뒤 다시 시도해 주세요.", "The photo search server isn't responding. Try again shortly."], ["사진 검색 서버가 너무 느립니다. 잠시 뒤 다시 시도하거나 ⚙️ 설정에 Pixabay 키를 넣어 주세요.", "Photo search is too slow. Try again later or add a Pixabay key in ⚙️ Settings."],
    ["라이선스 서버 응답의 서명이 올바르지 않습니다.", "The license server's signature is invalid."], ["라이선스 서버 응답이 이 요청의 것이 아닙니다.", "The license server's reply doesn't match this request."],
    ["라이선스 키 16자리를 모두 입력해 주세요.", "Enter all 16 characters of the license key."], ["라이선스 키를 먼저 입력해 주세요.", "Enter the license key first."],
    ["라이선스 서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요. ({})", "Can't reach the license server. Check your internet connection. ({})"], ["라이선스 서버 응답 형식이 올바르지 않습니다.", "Invalid license server response."],
    ["라이선스 서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요.", "Can't reach the license server. Check your internet connection."], ["라이선스 서버 오류 (HTTP {})", "License server error (HTTP {})"],
    ["PDF를 만들 브라우저(Edge 또는 Chrome)를 찾지 못했습니다.", "No browser (Edge or Chrome) found to make the PDF."], ["PDF를 만들지 못했습니다.", "Could not make the PDF."], ["지원하지 않는 형식입니다: {}", "Unsupported format: {}"],
    ["PPTX 저장에 필요한 python-pptx가 없습니다. (pip install python-pptx)", "python-pptx is required for PPTX. (pip install python-pptx)"], ["PDF 변환 시간이 너무 오래 걸려 중단했습니다.", "PDF conversion took too long and was stopped."],
    ["PPTX/이미지 저장에 필요한 PyMuPDF가 없습니다. (pip install pymupdf)", "PyMuPDF is required for PPTX/image export. (pip install pymupdf)"],
    ["AI 검수는 Gemini 키로만 쓸 수 있습니다. ⚙️ 설정에서 AI 엔진을 Gemini로 골라 주세요.", "AI review only works with a Gemini key. Choose Gemini in ⚙️ Settings."],
    ["업데이트 정보의 서명이 올바르지 않아 무시합니다.", "Ignoring update info with an invalid signature."], ["업데이트 파일 이름이 올바르지 않습니다.", "Invalid update file name."],
    ["내려받은 파일의 무결성 검증(SHA256)에 실패했습니다. 다시 시도해 주세요.", "The download failed its integrity check (SHA256). Try again."], ["업데이트 파일 내용이 올바르지 않습니다.", "Invalid update file contents."], ["업데이트 파일 형식이 올바르지 않습니다.", "Invalid update file format."],
    ["영상 인코딩에 실패했습니다. ({})", "Video encoding failed. ({})"], ["영상 인코더를 찾지 못했습니다. 프로그램을 최신 전체 설치 파일로 다시 설치해 주세요. ({})", "Video encoder not found. Reinstall with the latest full installer. ({})"],
    ["슬라이드가 없습니다.", "No slides."], ["영상 조각을 합치지 못했습니다. ({})", "Could not join the video parts. ({})"], ["{}에서 답을 받지 못했습니다. (코드 {}) 다시 시도해 주세요.", "No reply from {}. (code {}) Try again."],
    ["ChatGPT 구독 (Codex CLI)", "ChatGPT subscription (Codex CLI)"], ["Claude 구독 (Claude Code CLI)", "Claude subscription (Claude Code CLI)"], ["Gemini 구글 계정 (Gemini CLI)", "Gemini Google account (Gemini CLI)"],
    ["알 수 없는 AI 공급자입니다.", "Unknown AI provider."], ["{} 프로그램이 설치되어 있지 않습니다. 설치 후 다시 눌러 주세요. (설치: {})", "{} is not installed. Install it and press again. (Install: {})"],
    ["브라우저에서 {} 로그인 창이 열립니다. 로그인을 마치면 자동으로 연결됩니다.", "A {} sign-in page opens in your browser. It connects automatically when you finish."],
    ["{} 프로그램이 설치되어 있지 않습니다. ⚙️ 설정에서 안내를 확인해 주세요. (설치: {})", "{} is not installed. See ⚙️ Settings. (Install: {})"], ["{} 로그인이 필요하거나 만료되었습니다. ⚙️ 설정에서 [로그인]을 눌러 주세요.", "{} sign-in is needed or expired. Press [Sign in] in ⚙️ Settings."],
    ["{} 구독의 사용 한도에 도달했습니다. 잠시 뒤 다시 시도해 주세요.", "{} subscription limit reached. Try again later."], ["ChatGPT(Codex) 프로그램이 설치되어 있지 않습니다.", "ChatGPT (Codex) is not installed."], ["ChatGPT에서 그림을 받지 못했습니다.", "No image came back from ChatGPT."],
    ["Gemini 창이 열립니다. 'Sign in with Google'(구글 로그인)을 고르면 브라우저가 열리고, 로그인을 마치면 그 창을 닫아 주세요. 자동으로 연결됩니다.", "A Gemini window opens. Choose 'Sign in with Google', finish in the browser, then close that window. It connects automatically."],
    ["{} 응답이 너무 오래 걸립니다. 잠시 뒤 다시 시도해 주세요.", "{} is taking too long. Try again shortly."], ["{} 프로그램을 실행하지 못했습니다: {}", "Could not run {}: {}"], ["ChatGPT 로그인이 필요하거나 만료되었습니다.", "ChatGPT sign-in is needed or expired."],
    ["ChatGPT 구독의 사용 한도에 도달했습니다.", "ChatGPT subscription limit reached."], ["이미 로그인 창이 열려 있습니다. 브라우저에서 로그인을 마쳐 주세요.", "A sign-in page is already open. Finish signing in in the browser."], ["ChatGPT 그림 생성이 너무 오래 걸립니다.", "ChatGPT image generation is taking too long."],
    ["Edge 또는 Chrome을 실행하지 못했습니다.", "Could not start Edge or Chrome."], ["편집 가능한 PPTX에는 playwright가 필요합니다. (pip install playwright)", "Editable PPTX needs playwright. (pip install playwright)"],
    ["첨부 자료: {}", "Attachment: {}"],
    ["최신 자료 {}건 반영{}", "{} web sources used{}"], ["사진 {}장은 찾는 대로 넣습니다", "{} photos will be added as they are found"], ["내 사진 {}/{}장 배치", "{}/{} of your photos placed"],
    ["사진 {}장", "{} photos"], ["스캔 글자 읽음", "scan read"], ["키 {}", "key {}"], ["아직 확인이 필요한 장: {}번", "still needs a look: #{}"], ["지금 구성:", "current layout:"], ["장표로 보입니다", "slide"],
    ["굵게 (Ctrl+B)", "Bold (Ctrl+B)"], ["빼기", "Remove"], ["기울임 (Ctrl+I)", "Italic (Ctrl+I)"], ["밑줄 (Ctrl+U)", "Underline (Ctrl+U)"], ["아래로", "Move down"], ["위로", "Move up"],
    ["이 글자에 준 서식을 모두 지웁니다", "Removes all formatting from this text"], ["작게", "Smaller"], ["크게", "Larger"], ["직접 고르기", "Pick a color"],
    // ── 서체 이름 ──
    ["테마 기본 서체", "Theme font"], ["슬라이드 기본 서체", "Theme font"], ["프리텐다드 (Pretendard)", "Pretendard"], ["G마켓 산스 (Gmarket Sans)", "Gmarket Sans"], ["스포카 한 산스 (Spoqa Han Sans)", "Spoqa Han Sans"],
    ["조선일보명조 (Chosunilbo Myungjo)", "Chosunilbo Myungjo"], ["나눔스퀘어 네오 (NanumSquare Neo)", "NanumSquare Neo"], ["배달의민족 주아 (BM Jua)", "BM Jua"],
  ];

  // 테마 스타일·분류
  const STYLE = [
    ["스위스 타이포", "Swiss type", "굵은 고딕, 상단 굵은 선, 큰 페이지 번호, 직각 카드", "Bold sans, heavy top rule, big page numbers, square cards"],
    ["스타트업 그라디언트", "Startup gradient", "모서리 그라디언트 빛, 점 달린 알약 키커, 부드러운 카드", "Corner gradient glow, dotted pill kicker, soft cards"],
    ["기업 보고서", "Corporate report", "상단 헤더 띠, 하단 정보 바, 왼쪽 강조선 카드", "Header band, footer info bar, left-accent cards"],
    ["젠 미니멀", "Zen minimal", "가는 서체, 세로선 하나, 강조 점 하나, 넓은 여백", "Thin type, one vertical line, one accent dot, wide margins"],
    ["터미널 코드", "Terminal code", "고정폭 서체, 주석형 키커, 대괄호 모서리 카드, 스캔라인", "Monospace, comment-style kicker, bracket-corner cards, scanlines"],
    ["네온 나이트", "Neon night", "네온 발광 글자와 테두리, 지평선 격자, 어두운 무대", "Neon glowing text and borders, horizon grid, dark stage"],
    ["에디토리얼 명조", "Editorial serif", "명조 제목, 이탤릭 영문 키커, 가는 이중선, 테두리 없는 칼럼", "Serif titles, italic kicker, thin double rules, borderless columns"],
    ["네오 브루탈", "Neo-brutalism", "검은 굵은 테두리, 딱딱한 그림자, 형광 하이라이트", "Thick black borders, hard shadows, neon highlights"],
    ["글래스 메시", "Glass mesh", "그라디언트 메시 배경, 반투명 유리 카드, 빛나는 제목", "Gradient mesh background, frosted glass cards, glowing titles"],
    ["블루프린트 도면", "Blueprint", "모눈 도면 배경, 점선 카드, 치수선, 도면 번호", "Grid-paper background, dashed cards, dimension lines, sheet numbers"],
    ["말랑 파스텔", "Soft pastel", "둥근 서체, 물방울 블롭 도형, 아주 둥근 카드", "Rounded type, blob shapes, very round cards"],
    ["카드뉴스 스티커", "Card-news sticker", "굵은 둥근 카드, 스티커 뱃지, 말풍선, 꽉 찬 색 배경", "Bold round cards, sticker badges, speech bubbles, solid color"],
    ["데이터 대시보드", "Data dashboard", "점 격자 배경, KPI 패널 카드, 상단 지표 바, 숫자 전용 서체", "Dot grid, KPI panel cards, top metric bar, numeric type"],
    ["노트 손글씨", "Notebook", "줄노트 배경, 손글씨 키커, 마스킹테이프 카드, 형광펜 강조", "Lined paper, handwritten kicker, washi-tape cards, highlighter"],
    ["신문 지면", "Newspaper", "제호형 헤더, 단 구분선, 명조 헤드라인, 흑백+한 가지 색", "Masthead header, column rules, serif headlines, mono + one color"],
    ["아트 포스터", "Art poster", "초대형 둥근 제목, 큰 원형 도형, 색면 분할", "Huge rounded titles, big circles, color-field blocks"],
    ["매거진 커버", "Magazine cover", "초굵은 제목, 외곽선 강조 글자, 배경 대형 번호 워터마크", "Ultra-bold titles, outlined text, big number watermark"],
    ["멤피스 팝", "Memphis pop", "삼각형·지그재그·점 패턴 도형, 컬러 오프셋 그림자", "Triangles, zigzags and dots, colored offset shadows"],
    ["레트로 윈도우", "Retro window", "옛날 운영체제 창 모양 카드, 픽셀풍 그림자, 바둑판 배경", "Old-OS window cards, pixel shadows, checkerboard"],
    ["Y2K 크롬", "Y2K chrome", "크롬 금속 글자, 별빛 반짝이, 둥근 알약 프레임", "Chrome metal text, sparkles, pill frames"],
    ["럭셔리 세리프", "Luxury serif", "가는 명조, 넓은 자간, 안쪽 금테 프레임, 중앙 정렬", "Thin serif, wide tracking, inner gold frame, centered"],
    ["한지 전통", "Hanji traditional", "한지 결 질감, 붓글씨 키커, 붉은 낙관 도장, 세로 여백선", "Hanji paper texture, brush kicker, red seal stamp, vertical margin line"],
  ];
  for (const [k, e, kd, ed] of STYLE) PAIRS.push([k, e], [kd, ed]);
  PAIRS.push(["모던·미니멀", "Modern / minimal"], ["다크·테크", "Dark / tech"], ["미디어·브랜드", "Media / brand"], ["크리에이티브", "Creative"], ["레트로", "Retro"], ["비즈니스", "Business"],
    ["금융·핀테크", "Finance / fintech"], ["AI·테크", "AI / tech"], ["테마·유니크", "Unique"], ["감성·파스텔", "Mood / pastel"], ["럭셔리·프리미엄", "Luxury / premium"], ["SaaS·스타트업", "SaaS / startup"],
    ["볼드·임팩트", "Bold / impact"], ["이펙트·질감", "Effects / texture"]);

  // 테마 이름 (한국어 이름 순서대로)
  const THEME_KO = "스위스 그리드|VC 피치 네이비|코퍼릿 블루|미니멀 화이트|도쿄 나이트|드라큘라 퍼플|에디토리얼 명조|네오 브루탈|글래스 블러|블루프린트 설계도|오로라|소프트 파스텔|카드뉴스 화이트|모카 다크|라떼 라이트|노르딕 아이스|선셋 웜톤|학술 논문|아틱 쿨|바우하우스|사이버펑크 네온|엔지니어링 화이트프린트|그루브 다크|일본식 여백|매거진 볼드|멤피스 팝|미드센추리|뉴스 브로드캐스트|레인보우 그라디언트|레트로 TV|로즈 파인|샤프 모노|솔라 라이트|터미널 그린|베이퍼웨이브|Y2K 크롬|에이전틱 다크|트래블 코랄|스프레드 블루|엔터프라이즈 블루|프리미엄 실버|앱 클린|파스텔 브라우저|아티스틱 캔버스|아틀리에 제로|벤토 그리드|옐로 트레이딩|모터 블루|모터스포츠 트라이컬러|볼드 블랙|로우 브루탈|하이퍼카 블루|카페 브라운|캘린더 모노|크리에이터 퍼플|네트워크 블루|클레이 오렌지|클레이 소프트|클레이모피즘|클린 라이트|옐로 데이터|코랄 테크|크립토 블루|컬러풀 팝|컴포넌트 다크|컨템퍼러리|코퍼릿 네이비|코스믹 스페이스|크리에이티브 믹스|코드 에디터 다크|대시보드 슬레이트|베이직 뉴트럴|커뮤니티 블러플|디더링 픽셀|두들 스케치|드라마틱 콘트라스트|러닝 그린|에디토리얼 클래식|엘레강스|보이스 모노|에너제틱|엔터프라이즈 그레이|모바일 모노|익스프레시브|판타지|레이싱 레드|디자인 툴 멀티컬러|플랫 디자인|딥 블루 캔버스|프렌들리|퓨처리스틱|코드 리포 다크|글래스모피즘 딥|그라디언트 웨이브|인프라 블랙|HUD 인터페이스|옐로 스마일|엔터프라이즈 블루 그리드|메신저 블루|종이 에디토리얼|딥 퍼플 거래소|슈퍼카 골드|레벨 그리드|프로덕트 다크|러닝 컬러|비디오 퍼플|러블리 그라디언트|럭셔리 골드|카드 오렌지|머티리얼|소셜 블루|미니멀|테크 미니멀|민트 문서|화이트보드 옐로|미션 컨트롤|선셋 오렌지|모던|포레스트 데이터|모노크롬|네오브루탈 팝|네온 사인|뉴모피즘|스포츠 블랙|GPU 그린|로컬 모노|AI 랩 모노|코드 터미널|아케이드|페이퍼|서치 틸|퍼스펙티브|핀보드 레드|콘솔 블루|애널리틱스 옐로|프리미엄|프로페셔널|퍼블리케이션|런처 레드 다크|리파인드|다이아몬드 옐로|모델 허브 다크|메일 모노 다크|레트로|네오뱅크|필름 AI 다크|콘텐츠 레드|모니터링 퍼플|컴포넌트 뉴트럴|커머스 그린|심플|스큐어모피즘|워크스페이스 오버진|슬릭|스페이스 블랙|스페이셔스|뮤직 그린|스토리텔링|페이먼트 퍼플|데이터베이스 그린|인박스 다크|일렉트릭 미니멀|블록 퍼즐|테크 매거진|AI 블루|모던 스타터|페스티벌|트레이딩 터미널|모빌리티 블랙|캘리그래피 에디토리얼|엣지 블랙|바이브런트|빈티지|텔레콤 레드|볼트 그린|웜 에디토리얼|터미널 그라디언트|미팅 블루|노코드 블루|메신저 그린|테크 와이드 매거진|송금 라임|딥 블랙|자동화 오렌지|8비트 오빗|비엔날레 옐로|블록 프레임|블루 프로페셔널|볼드 포스터|브로드사이드|캡슐 컬러|카르테시안 베이지|코발트 그리드|코랄 포스터|크리에이티브 모드|데이지 데이즈|트라이톤 에디토리얼|그로브 포레스트|롱 테이블|우드 매트|모노크롬 페이퍼|네오 그리드 볼드|피플스 플랫폼|핀 앤 페이퍼|핑크 스크립트|플레이풀 피치|로우 그리드|레트로 윈도우|레트로 진|사쿠라 크로마|스캐터브레인|시그널 네이비|소프트 에디토리얼|스텐실 태블릿|스튜디오 옐로|벨럼 나이트".split("|");
  const THEME_EN = "Swiss Grid|VC Pitch Navy|Corporate Blue|Minimal White|Tokyo Night|Dracula Purple|Editorial Serif|Neo Brutal|Glass Blur|Blueprint|Aurora|Soft Pastel|Card News White|Mocha Dark|Latte Light|Nordic Ice|Sunset Warm|Academic Paper|Arctic Cool|Bauhaus|Cyberpunk Neon|Engineering Whiteprint|Groove Dark|Japanese Whitespace|Magazine Bold|Memphis Pop|Mid-Century|News Broadcast|Rainbow Gradient|Retro TV|Rosé Pine|Sharp Mono|Solar Light|Terminal Green|Vaporwave|Y2K Chrome|Agentic Dark|Travel Coral|Spread Blue|Enterprise Blue|Premium Silver|App Clean|Pastel Browser|Artistic Canvas|Atelier Zero|Bento Grid|Yellow Trading|Motor Blue|Motorsport Tricolor|Bold Black|Raw Brutal|Hypercar Blue|Café Brown|Calendar Mono|Creator Purple|Network Blue|Clay Orange|Clay Soft|Claymorphism|Clean Light|Yellow Data|Coral Tech|Crypto Blue|Colorful Pop|Component Dark|Contemporary|Corporate Navy|Cosmic Space|Creative Mix|Code Editor Dark|Dashboard Slate|Basic Neutral|Community Blurple|Dithered Pixel|Doodle Sketch|Dramatic Contrast|Learning Green|Editorial Classic|Elegance|Voice Mono|Energetic|Enterprise Gray|Mobile Mono|Expressive|Fantasy|Racing Red|Design Tool Multicolor|Flat Design|Deep Blue Canvas|Friendly|Futuristic|Code Repo Dark|Glassmorphism Deep|Gradient Wave|Infra Black|HUD Interface|Yellow Smile|Enterprise Blue Grid|Messenger Blue|Paper Editorial|Deep Purple Exchange|Supercar Gold|Level Grid|Product Dark|Learning Color|Video Purple|Lovely Gradient|Luxury Gold|Card Orange|Material|Social Blue|Minimal|Tech Minimal|Mint Docs|Whiteboard Yellow|Mission Control|Sunset Orange|Modern|Forest Data|Monochrome|Neo-Brutal Pop|Neon Sign|Neumorphism|Sport Black|GPU Green|Local Mono|AI Lab Mono|Code Terminal|Arcade|Paper|Search Teal|Perspective|Pinboard Red|Console Blue|Analytics Yellow|Premium|Professional|Publication|Launcher Red Dark|Refined|Diamond Yellow|Model Hub Dark|Mail Mono Dark|Retro|Neobank|Film AI Dark|Content Red|Monitoring Purple|Component Neutral|Commerce Green|Simple|Skeuomorphism|Workspace Aubergine|Sleek|Space Black|Spacious|Music Green|Storytelling|Payment Purple|Database Green|Inbox Dark|Electric Minimal|Block Puzzle|Tech Magazine|AI Blue|Modern Starter|Festival|Trading Terminal|Mobility Black|Calligraphy Editorial|Edge Black|Vibrant|Vintage|Telecom Red|Volt Green|Warm Editorial|Terminal Gradient|Meeting Blue|No-Code Blue|Messenger Green|Tech Wide Magazine|Remit Lime|Deep Black|Automation Orange|8-Bit Orbit|Biennale Yellow|Block Frame|Blue Professional|Bold Poster|Broadside|Capsule Color|Cartesian Beige|Cobalt Grid|Coral Poster|Creative Mode|Daisy Days|Tritone Editorial|Grove Forest|Long Table|Wood Matte|Monochrome Paper|Neo Grid Bold|People's Platform|Pin & Paper|Pink Script|Playful Pitch|Raw Grid|Retro Window|Retro Jeans|Sakura Chroma|Scatterbrain|Signal Navy|Soft Editorial|Stencil Tablet|Studio Yellow|Vellum Night".split("|");
  THEME_KO.forEach((k, i) => THEME_EN[i] && PAIRS.push([k, THEME_EN[i]]));

  // 장표 추천: 구성·꾸밈·역할 이름과 이유
  PAIRS.push(
    ["핵심 지표 카드", "KPI cards"], ["큰 숫자 강조", "Big number"], ["좌우 2단", "Two columns"], ["A vs B 비교", "A vs B"], ["표", "Table"], ["타임라인", "Timeline"], ["원형 게이지", "Ring gauge"],
    ["화살표 프로세스", "Arrow process"], ["깔때기", "Funnel"], ["피라미드", "Pyramid"], ["계단형 성장", "Staircase growth"], ["순환", "Cycle"], ["2×2 매트릭스", "2×2 matrix"], ["허브", "Hub"],
    ["벤 다이어그램", "Venn diagram"], ["세로 막대 그래프", "Bar chart"], ["요금제 카드", "Pricing cards"], ["장단점 비교", "Pros and cons"], ["큰 번호 목록", "Big numbered list"], ["원형·도넛 차트", "Pie / donut chart"],
    ["선 그래프", "Line chart"], ["팀 소개", "Team"], ["아이콘 특징 그리드", "Icon feature grid"], ["섹션 구분", "Section divider"], ["후기·인용 카드", "Testimonial cards"], ["마일스톤 로드맵", "Milestone roadmap"],
    ["조직도", "Org chart"], ["연락처", "Contact"], ["사진 강조", "Photo focus"], ["육각형 벌집", "Hexagon grid"], ["진행률 원 여러 개", "Progress rings"], ["기기 목업", "Device mockup"], ["카드 나열", "Cards"],
    ["큰 배경 글자", "Big background word"], ["제목 뒤에 아주 큰 옅은 영문 단어를 깔아 표지·섹션을 힘 있게", "A huge faint word behind the title gives covers and sections punch"],
    ["라벨 제목", "Label title"], ["제목 단어를 색 블록 위에 올려 잡지 표지처럼", "Title words on color blocks, like a magazine cover"], ["세로 제목", "Vertical title"],
    ["제목을 왼쪽에 세로로 세워 여백을 살린 에디토리얼 구성", "An editorial layout with a vertical title on the left"], ["둥근 블롭 도형", "Blob shape"], ["부드러운 유기적 도형으로 친근하고 밝게", "Soft organic shapes for a friendly, bright feel"],
    ["테두리 제목 상자", "Framed title"], ["가는 테두리 상자 안에 제목을 넣어 사진·영상 위에서도 또렷하게", "A thin frame keeps the title clear over photos or video"], ["색 띠", "Color band"],
    ["슬라이드 한쪽에 굵은 색 띠를 둘러 구획을 나눔", "A bold color band on one side divides the slide"], ["원형 배지", "Round badge"], ["할인율·핵심 숫자를 둥근 배지에 담아 눈에 띄게", "Puts a discount or key number in a round badge"],
    ["점 격자", "Dot grid"], ["빈 구석에 점 격자 무늬로 리듬감", "A dot grid in an empty corner adds rhythm"], ["굵기 대비 제목", "Weight-contrast title"], ["앞말은 아주 얇게, 핵심어는 아주 굵게 — 세련된 발표 자료에서 흔한 제목 처리", "Very thin lead-in, very bold keyword — a common polished title style"],
    ["회사·주제 소개", "Company / topic intro"], ["화면 소개", "Screen showcase"], ["사례·작업물", "Case / portfolio"], ["표지", "Cover"], ["후기·인용", "Testimonial"], ["요금·상품", "Pricing / products"],
    ["시장·고객", "Market / customers"], ["일정·연혁", "Schedule / history"], ["절차·과정", "Process"], ["비교", "Comparison"], ["수치·성과", "Numbers / results"], ["목표·비전", "Goals / vision"],
    ["서비스·특징", "Service / features"], ["마무리", "Closing"], ["일반 내용", "General content"],
    ["연도 {}개가 이어져 추이를 보여 주기 좋음", "{} consecutive years — good for showing a trend"], ["해마다 커지는 값을 계단으로", "Values that grow each year, as steps"], ["연도별 사건을 로드맵으로", "Events by year, as a roadmap"],
    ["비율(%) 값이 {}개 — 구성비를 한눈에", "{} percentages — show the mix at a glance"], ["비율을 막대 길이로 비교", "Compare ratios by bar length"], ["숫자 하나가 핵심 — 크게 강조", "One number matters — make it big"],
    ["비율 하나를 게이지로", "One ratio as a gauge"], ["핵심 수치 {}개 — 지표 카드로", "{} key numbers — as KPI cards"], ["수치가 {}개로 많아 표가 읽기 쉬움", "{} numbers — a table reads easier"], ["여러 값을 막대로 비교", "Compare several values with bars"],
    ["순서를 나타내는 말이 있어 흐름 도식이 어울림", "Sequence words suggest a flow diagram"], ["단계를 번호로 이어 보여 줌", "Shows numbered steps in a row"], ["반복·순환되는 과정", "A repeating cycle"],
    ["단계마다 줄어드는 수치(유입→전환 등)", "Numbers that shrink each stage (visits → conversions)"], ["위아래 위계가 있는 개념", "Concepts with a hierarchy"], ["겹치는 지점이 핵심", "The overlap is the point"],
    ["두 기준으로 나눠 보면 명확", "Clearer split along two axes"], ["항목 {}개를 아이콘 그리드로", "{} items as an icon grid"], ["항목 {}개를 큰 번호로", "{} items as a big numbered list"],
    ["글이 많아 2단으로 나누면 덜 빽빽함", "Lots of text — two columns feel lighter"], ["투자·영업 자료의 시장 규모는 깔때기가 표준", "Market size in pitch and sales decks is usually a funnel"],
    ["'{}' 장표에 가장 잘 어울리는 구성", "Best layout for a '{}' slide"]);

  // ── 사전 만들기 ──
  const EXACT = new Map(), PATS = [];
  const norm = (s) => s.replace(/\s+/g, " ").trim();
  for (const [ko, en] of PAIRS) {
    if (ko.includes("{}")) {
      const parts = ko.split("{}").map((p) => p.replace(/[.*+?^$()|[\]\\]/g, "\\$&"));
      const shortUnit = /^\{\}.{1,2}$/.test(ko) || /^.{1,3}\{\}$/.test(ko);
      const re = new RegExp("^" + parts.join(shortUnit ? "([\\d,.]+)" : "(.+?)") + "$");
      PATS.push([re, en]);
    } else EXACT.set(norm(ko), en);
  }
  PATS.sort((a, b) => b[0].source.replace(/\(.*?\)/g, "").length - a[0].source.replace(/\(.*?\)/g, "").length);   // 글자가 많은(구체적인) 틀부터
  const KO = /[가-힣]/;
  function fill(en, groups) {
    let i = 0;
    return en.replace(/\{(\d?)\}/g, (_, n) => { const v = groups[n === "" ? i++ : +n]; return v == null ? "" : t(v); });
  }
  function t(s) {
    if (LANG !== "en" || !s || !KO.test(s)) return s;
    const k = norm(s);
    const hit = EXACT.get(k);
    if (hit != null) return hit;
    for (const [re, en] of PATS) { const m = k.match(re); if (m) return fill(en, m.slice(1)); }
    if (k.includes(" · ")) { const ps = k.split(" · "); const out = ps.map(t); if (out.some((x, i) => x !== ps[i])) return out.join(" · "); }
    const em = k.match(/^([^\s가-힣]+)\s+(.+)$/);   // 앞에 붙은 이모지·기호
    if (em) { const r = t(em[2]); if (r !== em[2]) return em[1] + " " + r; }
    return s;
  }

  // ── 화면 바꾸기 ──
  const SKIP = "script,style,textarea,[contenteditable],[data-noi18n],#notes-text";
  const ATTRS = ["title", "placeholder", "aria-label"];
  function doText(n) {
    const p = n.parentElement;
    if (!p || p.closest(SKIP)) return;
    const v = n.nodeValue;
    if (!KO.test(v)) return;
    const r = t(v);
    if (r !== v) n.nodeValue = v.replace(v.trim(), () => r);   // 바꿀 글의 $ 기호를 특수 문자로 읽지 않게
  }
  function doEl(el) {
    if (el.closest && el.closest(SKIP) && !el.matches("textarea")) return;
    for (const a of ATTRS) { const v = el.getAttribute && el.getAttribute(a); if (v && KO.test(v)) { const r = t(v); if (r !== v) el.setAttribute(a, r); } }
  }
  function walk(root) {
    if (root.nodeType === 3) return doText(root);
    if (root.nodeType !== 1) return;
    doEl(root);
    root.querySelectorAll("*").forEach(doEl);
    const it = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let n; while ((n = it.nextNode())) doText(n);
  }
  function start() {
    document.title = t(document.title);
    walk(document.body);
    new MutationObserver((ms) => {
      for (const m of ms) {
        if (m.type === "characterData") doText(m.target);
        else if (m.type === "attributes") doEl(m.target);
        else m.addedNodes.forEach(walk);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }
  if (LANG === "en") {
    for (const fn of ["alert", "confirm", "prompt"]) { const orig = window[fn].bind(window); window[fn] = (msg, ...a) => orig(t(String(msg ?? "")), ...a); }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
  }
  window.GYEOL_I18N = { lang: LANG, t };
})();
