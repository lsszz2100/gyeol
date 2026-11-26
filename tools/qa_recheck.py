"""_qa/batch 에 저장된 슬라이드를 현재 CSS·runtime 으로 다시 렌더링해 레이아웃을 검사 (AI 호출 없음)."""
import json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from qa_layout import DETECT_JS
from core.template_compiler import compile_slide_deck
OUT = ROOT / "_qa" / "batch"
rep = json.loads((OUT / "report.json").read_text(encoding="utf-8"))
from playwright.sync_api import sync_playwright
tot = bad = grown = 0
with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
    br = pw.chromium.launch(channel="msedge"); page = br.new_page(viewport={"width": 1200, "height": 675})
    for k, r in sorted(rep.items(), key=lambda x: int(x[0])):
        d = OUT / f"{int(k):02d}"; f = d / "slides.html"
        if not f.exists():
            continue
        html = compile_slide_deck(f.read_text(encoding="utf-8"), theme_id=r["theme"], font_id="theme", inline_all=True)
        p = Path(tmp) / f"{k}.html"; p.write_text(html, encoding="utf-8")
        page.goto(p.as_uri(), wait_until="load")
        page.add_style_tag(content=".progress-bar,.notes-overlay,.overview{display:none!important}*{transition:none!important;animation:none!important}")
        page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true"); page.wait_for_timeout(500)
        n = page.evaluate("document.querySelectorAll('.deck .slide').length"); issues = []
        for i in range(n):
            x = page.evaluate(DETECT_JS, i); tot += 1
            grown += x["fit"] > 1
            page.wait_for_timeout(40); page.screenshot(path=str(d / f"{i + 1:02d}.png"))
            if x["issues"]:
                bad += 1; issues.append((i + 1, round(x["fit"], 2), x["issues"][:3]))
        print(k, r["style"], n, "문제", issues, flush=True)
    br.close()
print("전체", tot, "문제", bad, "확대", grown)
