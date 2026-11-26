"""AI 시각 검수: 슬라이드를 실제 화면 그대로 찍어 글자 넘침·잘림·겹침 같은 문제를 찾고,
문제가 있는 슬라이드는 AI(Gemini 비전)에게 화면과 함께 보여 줘 고친다.

흐름
 1) 덱을 1600×900으로 렌더링해 슬라이드마다 (a) 코드로 잰 문제 목록 (b) 화면 사진을 얻는다 (inspect)
 2) 작은 사진 여러 장을 한 번에 AI에게 보여 문제가 있어 보이는 장만 가려낸다 (triage) — 무료 키의 하루 호출 한도를 아끼려는 것
 3) 코드가 찾았거나 AI가 가려낸 장만, 사진·문제 목록·현재 HTML을 주고 "문제없음(OK)" 또는 "고친 슬라이드"를 받는다 (review_slide)
 4) 고친 덱을 다시 렌더링해 문제가 줄어든 것만 채택하고 나빠진 것은 원래대로 되돌린다 (review_deck)
사실·수치는 바꾸지 않고 줄이기·나누기·배치 바꾸기로만 고치게 한다.
"""
import logging
import re
import tempfile
from pathlib import Path

logger = logging.getLogger("kdesign.review")

W, H = 1600, 900
TRIAGE_BATCH = 6   # 한 번에 훑어보는 슬라이드 수

# 슬라이드 하나를 골라 코드로 문제를 잰다 (tools/qa_layout.py 와 같은 검사)
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
  // 6) 너무 작은 글자(화면에 보이는 크기 기준 14px 미만, 8자 이상 글줄)
  for (const el of textEls) {
    const own = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (own.length < 8) continue;
    const px = parseFloat(getComputedStyle(el).fontSize) * fit;
    if (px < 14) issues.push({type: 'small', el: name(el), px: Math.round(px)});
  }
  const seen = new Set();
  return {title: s.dataset.title || '', fit, issues: issues.filter(x => { const k = x.type + x.el; if (seen.has(k)) return false; seen.add(k); return true; })};
}
"""

PREP_CSS = ".progress-bar,.notes-overlay,.overview{display:none!important}*{transition:none!important;animation-duration:0s!important;animation-delay:0s!important}"


def inspect(deck_html: str, indices=None) -> list:
    """슬라이드마다 {"i", "title", "issues", "jpg"} 를 돌려준다. indices가 있으면 그 번호(0부터)만."""
    from playwright.sync_api import sync_playwright
    from core.pptx_editable import _launch
    out = []
    with tempfile.TemporaryDirectory(prefix="gyeol_review_") as tmp:
        f = Path(tmp) / "deck.html"
        f.write_text(deck_html, encoding="utf-8")
        with sync_playwright() as p:
            browser = _launch(p)
            page = browser.new_page(viewport={"width": W, "height": H})
            page.add_init_script("window.__noMotion=true")   # 화면을 찍을 때는 애니메이션 없이
            page.goto(f.as_uri(), wait_until="load")
            page.add_style_tag(content=PREP_CSS)
            page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true")
            page.wait_for_timeout(700)
            n = page.evaluate("document.querySelectorAll('.deck .slide').length")
            for i in (range(n) if indices is None else [x for x in indices if 0 <= x < n]):
                r = page.evaluate(DETECT_JS, i)
                page.wait_for_timeout(80)
                shot = page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H}, type="jpeg", quality=82)
                out.append({"i": i, "title": r.get("title", ""), "issues": r.get("issues", []), "jpg": shot})
            browser.close()
    return out


def _plain(sec: str) -> str:
    """슬라이드의 보이는 글자만 (대본 제외)."""
    import html as _h
    t = re.sub(r"<aside\b.*?</aside>", " ", sec or "", flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", "", _h.unescape(t))


def issue_lines(issues: list) -> str:
    names = {"out": "슬라이드 밖으로 나감", "clip-y": "세로로 잘림", "clip-x": "가로로 잘림", "deco": "장식과 글자가 겹침",
             "overlap": "옆 요소와 겹침", "card-spill": "카드 밖으로 글자가 삐져나옴", "small": "글자가 너무 작음(14px 미만, 읽기 어려움 — 내용을 줄이거나 장을 나눠 크기를 키울 것)"}
    lines = []
    for it in issues[:8]:
        extra = f" ({it['px']}px)" if it.get("px") else ""
        lines.append(f"- {names.get(it['type'], it['type'])}: {it.get('el', '')}{extra}")
    return "\n".join(lines) or "- (코드로 잰 문제는 없음. 화면만 보고 판단)"


def _prompt(deck_title: str, flow: str, cur_html: str, issues: list, hint: str = "") -> str:
    from ai_engine import SYSTEM_PROMPT, _today_str
    return f"""{SYSTEM_PROMPT}
[오늘 날짜] {_today_str()}

[발표 제목] {deck_title}
[발표 전체 흐름]
{flow}

[작업] 첨부한 사진은 아래 [현재 슬라이드]를 1600×900 화면에 그대로 그린 모습이다. 발표 슬라이드로서 문제가 있는지 눈으로 검수한다.
찾을 것은 '객관적 결함'뿐이다: ① 글자·카드·표가 잘리거나 슬라이드 밖으로 나감 ② 글자끼리·글자와 도형이 겹쳐 읽기 어려움
③ 글자가 배경과 너무 비슷해 읽을 수 없음 ④ 사진·그림이 깨졌거나 글자를 가림 ⑤ 줄바꿈 때문에 한두 글자만 따로 남음.
다음은 결함이 아니므로 절대 고치지 않는다: 표지·목차·간지·질의응답·인용 슬라이드의 넉넉한 여백, 왼쪽 정렬, 한쪽이 비어 보이는 구성,
글자 크기·색의 취향(읽을 수 있으면 그대로), 장식과 레이아웃 취향. 애매하면 OK 라고 답한다. 대부분의 슬라이드는 OK 다.
[코드로 잰 문제]
{issue_lines(issues)}
[훑어볼 때 눈에 띈 문제 후보] {hint or '(없음)'}

[답변 형식] 반드시 아래 둘 중 하나로만 답한다.
1) 문제가 없으면 한 줄로: OK
2) 문제가 있으면 첫 줄에 `문제: ` 뒤에 무엇이 문제인지 한 문장, 그다음 줄부터 고친 <section class="slide"> 블록 딱 하나.
[고치는 규칙]
- 사실·수치·출처·대본(<aside class="notes">)은 그대로 둔다. 새 수치를 만들지 않는다.
- 기존 문장을 줄이거나 합치고, 카드·불릿 개수를 줄이거나, 배치(그리드 열 수)를 바꿔서 고친다. 내용을 빼야 하면 덜 중요한 것부터 뺀다.
- '(축약)', '…등' 같은 줄였다는 표시나 임시 문구를 덧붙이지 않는다. 줄인 문장도 그 자체로 완결된 문장이어야 한다.
- 원래 슬라이드에 없던 새 주장·새 문장·새 수치를 쓰지 않는다. 남기는 문구는 원래 표현을 최대한 그대로 쓴다.
- data-kind, data-title, 사진(<figure class="g-photo">)과 with-photo 클래스는 유지한다.
- 문제가 없는 슬라이드는 절대 건드리지 말고 OK 만 답한다. 결함을 못 찾았으면서 보기 좋게 바꾸려 하지 않는다.
- 새 문장·새 문구를 덧붙이지 않는다. 글자는 줄이거나 그대로 두기만 한다.

[현재 슬라이드]
{cur_html}
"""


def _small(jpg: bytes) -> bytes:
    """훑어보기용으로 사진을 줄인다 (토큰 절약). 줄이지 못하면 원본."""
    try:
        import pymupdf as fitz
        pix = fitz.Pixmap(jpg)
        return fitz.Pixmap(pix, 800, 450).tobytes("jpeg", jpg_quality=70)
    except Exception:
        return jpg


def triage(batch: list, deck_title: str, api_key: str, model: str) -> dict:
    """batch: [(슬라이드 번호(1부터), jpg)…] → {번호: 문제 한 문장}. 문제가 없으면 빈 dict."""
    import json
    from ai_engine import _gemini_with_fallback, DEFAULT_GEMINI_MODEL
    nums = [n for n, _ in batch]
    text = (f"발표 「{deck_title}」의 슬라이드 {len(batch)}장을 1600×900 화면 그대로 찍은 사진이다. 사진 순서는 슬라이드 번호 {nums} 이다.\n"
            "아래 '객관적 결함'이 있는 장만 가려낸다: ① 글자·카드·표가 잘리거나 슬라이드 밖으로 나감 ② 글자끼리·글자와 도형이 겹쳐 읽기 어려움 "
            "③ 글자가 배경과 너무 비슷해 읽을 수 없음 ④ 사진·그림이 깨졌거나 글자를 가림 ⑤ 줄바꿈 때문에 한두 글자만 따로 남음.\n"
            "다음은 결함이 아니다: 표지·목차·간지·질의응답·인용 슬라이드의 넉넉한 여백, 왼쪽 정렬, 한쪽이 비어 보이는 구성, 글자 크기·색 취향. "
            "조금이라도 애매하면 문제로 보지 않는다. 대부분의 덱은 결함이 없다.\n"
            '문제 있는 장만 JSON 배열로 답한다. 예: [{"n": 3, "problem": "오른쪽 카드 글자가 잘림"}]. 문제가 없으면 [] 만 답한다. 설명은 쓰지 않는다.')
    out = _gemini_with_fallback(api_key, model or DEFAULT_GEMINI_MODEL, text, max_tokens=1024, timeout=90,
                                images=[(_small(j), "image/jpeg") for _, j in batch])
    m = re.search(r"\[.*\]", out.get("text") or "", re.S)
    found = {}
    if m:
        try:
            for it in json.loads(m.group(0)):
                if isinstance(it, dict) and it.get("n") in nums:
                    found[int(it["n"])] = str(it.get("problem", "")).strip()[:100] or "문제 있음"
        except Exception:
            pass
    return found


def review_slide(slides: list, idx: int, jpg: bytes, issues: list, deck_title: str, provider: str, api_key: str, model: str, hint: str = "") -> dict:
    """AI에게 한 장을 검수시킨다. 반환 {"ok": True} 또는 {"ok": False, "reason": 문제, "html": 고친 section, "model": 모델}."""
    from ai_engine import _compact_for_ai, _gemini_with_fallback, _clean_generated_html, _slide_text, DEFAULT_GEMINI_MODEL
    flow = []
    for i, sh in enumerate(slides):
        m = re.search(r'data-title="([^"]*)"', sh)
        flow.append(f"{i + 1}. {m.group(1) if m else _slide_text(sh, 30)}" + ("  ◀ 검수할 슬라이드" if i == idx else ""))
    cur, kept = _compact_for_ai(slides[idx])
    text = _prompt(deck_title, "\n".join(flow), cur, issues, hint)
    out = _gemini_with_fallback(api_key, model or DEFAULT_GEMINI_MODEL, text, max_tokens=8192, timeout=120,
                                images=[(jpg, "image/jpeg")])
    raw = (out.get("text") or "").strip()
    secs = re.findall(r"<section\b[^>]*class=\"[^\"]*\bslide\b[^\"]*\"[^>]*>.*?</section>", _clean_generated_html(raw), re.S | re.I)
    if not secs:
        return {"ok": True}  # OK 이거나 형식이 맞지 않으면 건드리지 않는다
    fixed = secs[0].strip()
    if kept:
        fixed = re.sub(r"(\s*<aside\b|\s*</section>\s*$)", lambda m: "\n  " + "\n  ".join(kept) + m.group(1), fixed, count=1)
    reason = ""
    m = re.search(r"문제\s*[:：]\s*(.+)", raw)
    if m:
        reason = m.group(1).strip()[:120]
    return {"ok": False, "reason": reason, "html": fixed, "model": out.get("model", "")}


def review_deck(slides: list, deck_title: str, compile_fn, provider: str, api_key: str, model: str,
                sanitize, progress=None, should_stop=None) -> dict:
    """덱 전체를 검수해 고친 슬라이드 목록을 돌려준다.
    compile_fn(slides)->덱 HTML. sanitize(section)->정리된 section. progress(done, total, msg).
    반환 {"slides": 새 목록, "fixed": [{"i","reason"}], "left": [남은 문제 슬라이드 번호], "checked": n}"""
    if provider != "gemini":
        raise RuntimeError("AI 검수는 Gemini 키로만 쓸 수 있습니다. ⚙️ 설정에서 AI 엔진을 Gemini로 골라 주세요.")
    note = progress or (lambda *a: None)
    stop = should_stop or (lambda: False)
    cur = list(slides)
    total = len(cur)
    note(0, total, "슬라이드를 화면으로 그리는 중")
    first = inspect(compile_fn(cur))
    base_issues = {r["i"]: len(r["issues"]) for r in first}
    # 1단계: 여러 장을 한 번에 훑어 문제 후보를 가린다 (코드가 이미 찾은 장은 바로 후보)
    hints = {r["i"]: "" for r in first if r["issues"]}
    steps = -(-len(first) // TRIAGE_BATCH)
    for k in range(0, len(first), TRIAGE_BATCH):
        if stop():
            break
        note(0, total, f"슬라이드를 훑어보는 중 ({k // TRIAGE_BATCH + 1}/{steps})")
        batch = first[k:k + TRIAGE_BATCH]
        try:
            for n, why in triage([(r["i"] + 1, r["jpg"]) for r in batch], deck_title, api_key, model).items():
                hints[n - 1] = why
        except Exception as e:
            from ai_engine import AIGenerationError
            if isinstance(e, AIGenerationError) and ("한도" in str(e) or "키" in str(e)):
                raise
            logger.warning(f"훑어보기 실패, 코드가 찾은 문제만 처리: {e}")
    cand = [r for r in first if r["i"] in hints]
    fixed = {}
    done = 0
    for r in cand:
        if stop():
            break
        i = r["i"]
        note(done, len(cand), f"{i + 1}번 슬라이드 고치는 중")
        try:
            res = review_slide(cur, i, r["jpg"], r["issues"], deck_title, provider, api_key, model, hints.get(i, ""))
        except Exception as e:
            from ai_engine import AIGenerationError
            if isinstance(e, AIGenerationError) and ("한도" in str(e) or "키" in str(e)):
                raise
            logger.warning(f"{i + 1}번 검수 실패, 건너뜀: {e}")
            res = {"ok": True}
        done += 1
        if res["ok"]:
            continue
        try:
            cur[i] = sanitize(res["html"])
            fixed[i] = res.get("reason", "")
        except Exception as e:
            logger.warning(f"{i + 1}번 고친 결과가 올바르지 않아 버림: {e}")
    if not fixed:
        left = [r["i"] for r in first if r["issues"]]
        return {"slides": cur, "fixed": [], "left": left, "checked": total}

    # 새 글자가 늘어난 수정은 AI가 내용을 지어낸 것이므로 버린다 (줄이거나 그대로인 수정만 인정)
    for i in sorted(fixed):
        a_, b_ = _plain(slides[i]), _plain(cur[i])
        if len(b_) > len(a_) * 1.08 + 6:
            logger.info(f"{i + 1}번: 고친 뒤 글자가 늘어(지어낸 것으로 보고) 원래대로 되돌림 ({len(a_)}→{len(b_)})")
            cur[i] = slides[i]
            fixed.pop(i)
    if not fixed:
        return {"slides": cur, "fixed": [], "left": [r["i"] for r in first if r["issues"]], "checked": total}
    # 고친 결과를 다시 그려 코드로 잰 문제가 나빠진 것은 원래대로 되돌린다
    note(len(cand), len(cand), "고친 슬라이드를 다시 확인하는 중")
    after = {r["i"]: r for r in inspect(compile_fn(cur), sorted(fixed))}
    for i in sorted(fixed):
        if len(after[i]["issues"]) > base_issues.get(i, 0):
            logger.info(f"{i + 1}번: 고친 뒤 문제가 늘어 원래대로 되돌림")
            cur[i] = slides[i]
            fixed.pop(i)
    left = [i for i in sorted(after) if i in fixed and after[i]["issues"]] + \
           [r["i"] for r in first if r["issues"] and r["i"] not in fixed]
    return {"slides": cur, "fixed": [{"i": i, "reason": fixed[i]} for i in sorted(fixed)], "left": sorted(set(left)), "checked": total}
