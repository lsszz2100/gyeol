"""실사용 품질 검수: 다양한 주제·옵션·스타일로 실제 생성 → 레이아웃·내용·내보내기 자동 점검 (Windows Python).
  python -X utf8 tools\\qa_batch.py [시작번호] [끝번호]     결과: _qa/batch/report.json, _qa/batch/NN/*.png, sheet_NN.jpg
데이터는 임시 폴더를 쓰고(실제 프로젝트 영향 없음), 라이선스 검사는 개발 실행 옵션으로 건너뛴다."""
import json, os, re, shutil, sys, tempfile, threading, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "_qa" / "batch"; OUT.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp(prefix="gyeol_qa_"))
os.environ["GYEOL_TEST_SAVE_DIR"] = str(TMP / "saved")
(TMP / "saved").mkdir()
real = json.loads((ROOT / "data" / "config.json").read_text(encoding="utf-8"))
(TMP / "config.json").write_text(json.dumps({k: real.get(k, "") for k in ("provider", "gemini_api_key", "gemini_model", "pixabay_api_key")}), encoding="utf-8")
import config
config.DATA_DIR, config.CONFIG_FILE, config.HISTORY_FILE = str(TMP), str(TMP / "config.json"), str(TMP / "history.json")
import app, desktop
app.LICENSE_BYPASS = True   # 시험 프로세스 안에서만
from qa_layout import DETECT_JS
from core.template_compiler import compile_slide_deck, AVAILABLE_THEMES

def theme(style):
    return next(t["id"] for t in AVAILABLE_THEMES if t["style"] == style)

S = [  # 주제, 프리셋, 스타일, 옵션
 ("2027년 우리 회사 신입사원 온보딩 교육 계획", "business-proposal", "report", dict(purpose="education", audience="general", tone="friendly", visuals="icons", slide_count=10)),
 ("중소기업을 위한 생성형 AI 도입 제안서", "business-proposal", "swiss", dict(purpose="proposal", audience="executive", tone="formal", visuals="photos", slide_count=12)),
 ("친환경 포장재 스타트업 시드 투자 유치", "pitch-deck", "startup", dict(purpose="persuasion", audience="investor", tone="concise", visuals="photos", slide_count=12, density="light")),
 ("초등학교 5학년 태양계 과학 수업", "tech-sharing", "memphis", dict(purpose="education", audience="student", tone="friendly", visuals="photos", slide_count=8, density="light")),
 ("대학원 세미나: 트랜스포머 모델의 어텐션 메커니즘", "tech-sharing", "blueprint", dict(purpose="analysis", tone="academic", visuals="none", slide_count=12, density="dense", footnotes=True)),
 ("이번 주 마케팅팀 주간 업무 보고", "weekly-report", "dashboard", dict(purpose="report", audience="executive", tone="concise", visuals="none", slide_count=6, research=False)),
 ("동네 카페 신메뉴 겨울 시즌 홍보", "business-proposal", "cardnews", dict(purpose="promotion", audience="customer", tone="friendly", visuals="photos", slide_count=7, density="light")),
 ("지방자치단체 청년 주거 지원 정책 제안", "business-proposal", "newspaper", dict(purpose="proposal", audience="public", tone="formal", visuals="icons", slide_count=14, dividers=True)),
 ("병원 환자 안전 사고 예방 교육", "tech-sharing", "zen", dict(purpose="education", tone="formal", visuals="icons", slide_count=10)),
 ("2026년 글로벌 반도체 시장 분석", "tech-sharing", "terminal", dict(purpose="analysis", audience="executive", tone="concise", visuals="none", slide_count=15, density="dense", charts=True)),
 ("결혼식 식전 영상용 우리 둘의 이야기", "business-proposal", "pastel", dict(purpose="promotion", tone="friendly", visuals="photos", slide_count=6, research=False, toc=False, sources=False, density="light")),
 ("Remote Work Productivity Best Practices", "tech-sharing", "editorial", dict(purpose="report", tone="concise", visuals="photos", slide_count=8, language="en")),
 ("전통 한지의 역사와 현대적 활용", "tech-sharing", "hanji", dict(purpose="education", tone="formal", visuals="photos", slide_count=9)),
 ("프리미엄 위스키 브랜드 런칭 전략", "business-proposal", "luxury", dict(purpose="proposal", audience="executive", tone="formal", visuals="photos", slide_count=10)),
 ("게임 개발사 신작 인디게임 소개", "pitch-deck", "neon", dict(purpose="promotion", audience="customer", tone="friendly", visuals="photos", slide_count=8)),
 ("고등학교 동아리 축제 기획안", "business-proposal", "y2k", dict(purpose="proposal", audience="student", tone="friendly", visuals="icons", slide_count=7, density="light")),
 ("개인 재무 관리 기초: 사회초년생 편", "tech-sharing", "notebook", dict(purpose="education", audience="general", tone="friendly", visuals="icons", slide_count=10, charts=True)),
 ("물류센터 자동화 도입 효과 분석 보고서", "weekly-report", "window", dict(purpose="report", audience="executive", tone="formal", visuals="photos", slide_count=11)),
 ("사내 해커톤 결과 발표", "tech-sharing", "brutal", dict(purpose="report", tone="concise", visuals="icons", slide_count=6, density="light", closing="qna", notes="detailed", presenter="홍길동", org="플랫폼팀", date="2026-11-01")),
 ("포용적 디자인 트렌드", "tech-sharing", "magazine", dict(purpose="analysis", tone="formal", visuals="photos", slide_count=9, density="normal")),
]

def req(port, path, body=None, timeout=300):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers={"Content-Type": "application/json", "X-Gyeol-Token": app.API_TOKEN})
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return json.loads(f.read().decode("utf-8"))

CONTENT_JS = r"""
() => {
  const out = {broken: [], leftovers: [], icons: 0, thin: []};
  document.querySelectorAll('.deck .slide').forEach((s, i) => {
    s.querySelectorAll('img').forEach(im => { if (!im.complete || !im.naturalWidth) out.broken.push(i + 1); });
    out.icons += s.querySelectorAll('i[data-icon]').length;
    const clone = s.cloneNode(true); clone.querySelectorAll('aside.notes').forEach(n => n.remove());
    const t = (clone.innerText || clone.textContent || '').trim();
    const m = t.match(/undefined|null\b|NaN|\{\{|\}\}|<[a-z/]|\[사진|data-photo|```|TODO/g);
    if (m) out.leftovers.push([i + 1, m.slice(0, 3)]);
    if (t.length < 8 && !s.querySelector('img,svg,canvas')) out.thin.push(i + 1);
  });
  return out;
}"""

def main():
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else len(S)
    port = desktop.pick_port(9311)
    srv = app.ThreadedHTTPServer(("127.0.0.1", port), app.KDesignHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    report_file = OUT / "report.json"
    report = json.loads(report_file.read_text(encoding="utf-8")) if report_file.exists() else {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="msedge")
        page = br.new_page(viewport={"width": 1200, "height": 675})
        for n in range(a, b):
            topic, preset, style, opts = S[n]
            tid = theme(style); r = {"topic": topic, "style": style, "theme": tid, "opts": opts}
            print(f"\n[{n:02d}] {topic} / {style}", flush=True)
            t0 = time.time()
            try:
                g = req(port, "/api/generate", {"prompt": topic, "preset_id": preset, "theme": tid, "font": "theme", "title": topic, "opts": opts}, 300)
            except Exception as e:
                g = {"ok": False, "message": f"요청 실패: {e}"}
            r["gen_sec"] = round(time.time() - t0, 1); r["ok"] = bool(g.get("ok")); r["message"] = g.get("message", "")
            if not g.get("ok"):
                print("  실패:", r["message"], flush=True); report[str(n)] = r
                report_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"); time.sleep(20); continue
            r.update(slides=g["slide_count"], want=opts.get("slide_count"), sources=g.get("source_count"), photos_pending=g.get("photos_pending"), model=g.get("model"))
            t1 = time.time()
            while time.time() - t1 < 260 and req(port, "/api/photo_status")["pending"] > 0:
                time.sleep(3)
            r["photo_sec"] = round(time.time() - t1, 1); r["photos_left"] = req(port, "/api/photo_status")["pending"]
            proj = req(port, "/api/active_project"); proj = proj.get("project", proj)
            html = compile_slide_deck(proj["slides_html"], theme_id=tid, font_id="theme", inline_all=True)
            d = OUT / f"{n:02d}"; shutil.rmtree(d, ignore_errors=True); d.mkdir()
            f = TMP / f"d{n}.html"; f.write_text(html, encoding="utf-8")
            (d / "slides.html").write_text(proj["slides_html"], encoding="utf-8")
            page.goto(f.as_uri(), wait_until="load")
            page.add_style_tag(content=".progress-bar,.notes-overlay,.overview{display:none!important}*{transition:none!important;animation:none!important}")
            page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true"); page.wait_for_timeout(700)
            r["content"] = page.evaluate(CONTENT_JS)
            m = page.evaluate("document.querySelectorAll('.deck .slide').length"); res = []
            for i in range(m):
                x = page.evaluate(DETECT_JS, i); x["i"] = i + 1; res.append(x)
                page.wait_for_timeout(50); page.screenshot(path=str(d / f"{i + 1:02d}.png"))
            r["layout"] = [x for x in res if x["issues"]]; r["fit_low"] = [(x["i"], round(x["fit"], 2)) for x in res if x["fit"] < .8]
            t2 = time.time()
            try:
                e = req(port, "/api/export", {"format": "pptx"}, 180); r["pptx"] = bool(e.get("ok")); r["pptx_msg"] = e.get("message", "")
            except Exception as e2:
                r["pptx"] = False; r["pptx_msg"] = str(e2)
            r["pptx_sec"] = round(time.time() - t2, 1)
            report[str(n)] = r
            report_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {g['slide_count']}장 {r['gen_sec']}s 사진{r['photo_sec']}s(남음 {r['photos_left']}) 레이아웃 {len(r['layout'])} 내용 {r['content']['broken']}{r['content']['leftovers']}{r['content']['thin']} pptx {r['pptx']}", flush=True)
            time.sleep(8)
        br.close()
    srv.shutdown()
    shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    main()
