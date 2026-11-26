"""레이아웃 품질 검사: 스타일마다 대표 테마 하나로 덱을 렌더링해
슬라이드 밖으로 나간 요소, 카드 안에서 잘린 글자, 장식(번호·도형)과 겹친 글자를 찾는다.

Windows Python에서 실행:
  python.exe -X utf8 D:\\Rea\\kdesign\\tools\\qa_layout.py [덱번호들] [--shots] [--style swiss,...]
결과: _qa/report.json, --shots 이면 _qa/<style>/NN.png
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.template_compiler import compile_slide_deck, AVAILABLE_THEMES

OUT = ROOT / "_qa"

DETECT_JS = r"""
(i) => {
  const slides = [...document.querySelectorAll('.deck .slide')];
  slides.forEach((s, j) => {
    const on = j === i;
    s.classList.toggle('is-active', on);
    s.style.display = on ? '' : 'none';
    s.style.opacity = on ? '1' : '';
    s.style.transform = on ? 'none' : '';
  });
  document.querySelector('.deck').style.counterReset = 'sl ' + i;
  const s = slides[i];
  window.__gyeolFit(s);
  const fit = parseFloat(s.style.getPropertyValue('--fit') || '1');
  const issues = [];
  const sr = s.getBoundingClientRect();
  const name = el => (el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : '') + ' "' + (el.textContent || '').trim().slice(0, 24) + '"');
  const leafs = [...s.querySelectorAll('*')].filter(el => {
    if (el.closest('aside.notes') || el.matches('.g-footer,.g-logo')) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });
  // 1) 슬라이드 밖으로 나간 요소
  for (const el of leafs) {
    const r = el.getBoundingClientRect();
    const o = Math.max(sr.left - r.left, r.right - sr.right, sr.top - r.top, r.bottom - sr.bottom);
    if (o > 2) issues.push({type: 'out', el: name(el), px: Math.round(o)});
  }
  // 2) 잘린 상자(overflow 숨김 상태에서 내용이 더 큼)
  for (const el of leafs) {
    const cs = getComputedStyle(el);
    if (el.scrollHeight > el.clientHeight + 3 && cs.overflowY !== 'visible' && el.clientHeight > 0)
      issues.push({type: 'clip-y', el: name(el), px: el.scrollHeight - el.clientHeight});
    if (el.scrollWidth > el.clientWidth + 3 && cs.overflowX !== 'visible' && el.clientWidth > 0)
      issues.push({type: 'clip-x', el: name(el), px: el.scrollWidth - el.clientWidth});
  }
  // 3) 장식 가상요소와 글자 겹침
  const textEls = leafs.filter(el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));
  const textRects = [];
  for (const el of textEls) {
    const rg = document.createRange();
    for (const n of el.childNodes) {
      if (n.nodeType !== 3 || !n.textContent.trim()) continue;
      rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) if (r.width > 1) textRects.push({el, r});
    }
  }
  const pseudo = [];
  for (const p of ['::before', '::after']) {
    const cs = getComputedStyle(s, p);
    if (cs.content === 'none' || cs.display === 'none' || cs.position !== 'absolute') continue;
    const hasText = /^["'].*[^\s"'].*["']$/.test(cs.content) || cs.content.includes('counter');
    const bg = cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && parseFloat(cs.opacity) > .3;
    if (!hasText && !bg) continue;
    const W = sr.width, H = sr.height;
    const px = v => parseFloat(v);
    let w = px(cs.width), h = px(cs.height);
    let l = cs.left !== 'auto' ? px(cs.left) : W - px(cs.right) - w;
    let t = cs.top !== 'auto' ? px(cs.top) : H - px(cs.bottom) - h;
    if (cs.transform && cs.transform !== 'none') continue;  // 회전/이동된 장식은 생략
    pseudo.push({p, l: sr.left + l, t: sr.top + t, r: sr.left + l + w, b: sr.top + t + h, text: cs.content.slice(0, 30)});
  }
  for (const d of pseudo) {
    if (!(d.r - d.l > 0 && d.b - d.t > 0) || d.r - d.l > sr.width * .9) continue;
    for (const {el, r} of textRects) {
      const ox = Math.min(d.r, r.right) - Math.max(d.l, r.left), oy = Math.min(d.b, r.bottom) - Math.max(d.t, r.top);
      if (ox > 4 && oy > 4) { issues.push({type: 'deco', el: name(el), deco: d.p + ' ' + d.text}); break; }
    }
  }
  // 4) 같은 행 형제 요소가 겹침
  for (const el of leafs.filter(e => e.matches('.grid,.row'))) {
    const kids = [...el.children].filter(k => k.getBoundingClientRect().width > 0);
    for (let a = 0; a < kids.length; a++) for (let b = a + 1; b < kids.length; b++) {
      const A = kids[a].getBoundingClientRect(), B = kids[b].getBoundingClientRect();
      const ox = Math.min(A.right, B.right) - Math.max(A.left, B.left), oy = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top);
      if (ox > 4 && oy > 4) issues.push({type: 'overlap', el: name(kids[a]) + ' × ' + name(kids[b])});
    }
  }
  // 5) 글자가 상자 아래로 삐져나옴(overflow visible 인 카드)
  for (const c of leafs.filter(e => e.matches('.card'))) {
    const cr = c.getBoundingClientRect();
    for (const {el, r} of textRects) if (c.contains(el) && (r.bottom > cr.bottom + 2 || r.right > cr.right + 2))
      { issues.push({type: 'card-spill', el: name(el)}); break; }
  }
  const seen = new Set();
  return {title: s.dataset.title || '', fit, issues: issues.filter(x => { const k = x.type + x.el; if (seen.has(k)) return false; seen.add(k); return true; })};
}
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shots = "--shots" in sys.argv
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--style="):
            only = set(a.split("=", 1)[1].split(","))
    deck_ids = [int(a) for a in args] or [0, 1]
    hist = json.loads((ROOT / "data" / "history.json").read_text(encoding="utf-8"))
    extra = ROOT / "tools" / "qa_stress.html"
    decks = [hist[i]["slides_html"] for i in deck_ids if i < len(hist)]
    if extra.exists():
        decks.append(extra.read_text(encoding="utf-8"))
    slides_html = "\n\n".join(decks)

    reps = {}
    for t in AVAILABLE_THEMES:
        reps.setdefault(t["style"], t["id"])
    if only:
        reps = {k: v for k, v in reps.items() if k in only}

    from playwright.sync_api import sync_playwright
    OUT.mkdir(exist_ok=True)
    report = {}
    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        browser = None
        for ch in ("msedge", "chrome", None):
            try:
                browser = p.chromium.launch(channel=ch) if ch else p.chromium.launch()
                break
            except Exception:
                continue
        page = browser.new_page(viewport={"width": 1200, "height": 675})
        for style, tid in reps.items():
            html = compile_slide_deck(slides_html, theme_id=tid, font_id="theme", inline_all=True)
            f = Path(tmp) / f"{style}.html"
            f.write_text(html, encoding="utf-8")
            page.goto(f.as_uri(), wait_until="load")
            page.add_style_tag(content=".progress-bar,.notes-overlay,.overview{display:none!important}*{transition:none!important;animation-duration:0s!important;animation-delay:0s!important}")
            page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true")
            page.wait_for_timeout(600)
            n = page.evaluate("document.querySelectorAll('.deck .slide').length")
            res = []
            for i in range(n):
                r = page.evaluate(DETECT_JS, i)
                r["i"] = i + 1
                res.append(r)
                if shots:
                    d = OUT / style
                    d.mkdir(exist_ok=True)
                    page.wait_for_timeout(60)
                    page.screenshot(path=str(d / f"{i + 1:02d}.png"))
            report[style] = {"theme": tid, "slides": res}
            bad = sum(1 for r in res if r["issues"])
            print(f"{style:11s} {tid:24s} 문제 슬라이드 {bad}/{n}", flush=True)
        browser.close()
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
