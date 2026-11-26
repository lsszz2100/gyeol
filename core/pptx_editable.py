"""
결(GYEOL) - 글자 편집이 가능한 PPTX 만들기

1) 설치된 Edge(없으면 Chrome)로 슬라이드를 1600×900 그대로 띄운다.
2) 슬라이드마다 글자 덩어리의 위치·크기·색·굵기·정렬을 읽는다.
3) 글자만 투명하게 숨긴 상태로 배경(도형·카드·장식·그래프)을 이미지로 찍는다.
4) PPTX 슬라이드에 배경 이미지를 깔고, 그 위 같은 위치에 텍스트 상자를 만든다.
   → 디자인은 그대로, 글자는 PowerPoint에서 바로 고칠 수 있다.
5) 사진 패널(.g-photo)과 직접 넣은 그림(.g-obj img)은 배경에서 빼고 따로 그림 개체로 넣는다.
   → PowerPoint에서 사진을 골라 옮기거나 [그림 바꾸기]를 할 수 있다.
"""

import io
import os
import re
import tempfile
from pathlib import Path

W, H = 1600, 900                 # 슬라이드 설계 크기(px)
EMU_PER_PX = 12192000 / W        # 16:9 기본 PPT 폭 13.333in
PT_PER_PX = 960 / W              # 13.333인치 × 72pt

# 웹 서체 → PowerPoint에서 보일 서체 (받는 사람 PC에도 있는 Windows 기본 서체)
SERIF_HINTS = ("myeongjo", "batang", "serif", "song myung", "noto serif", "playfair", "cormorant", "chosun")
MONO_HINTS = ("mono", "coding", "consolas")

EXTRACT_JS = r"""
() => {
  const deck = document.querySelector('.deck');
  const slide = document.querySelector('.slide.is-active');
  if (!slide) return [];
  const root = getComputedStyle(document.documentElement);
  const accent = root.getPropertyValue('--accent').trim();
  const blocks = [];
  const BLOCKY = /^(block|flex|grid|list-item|table|table-cell|inline-block|inline-flex|flow-root)$/;

  function zoomOf(el) { let z = 1; for (let e = el; e && e !== document.body; e = e.parentElement) { const v = parseFloat(getComputedStyle(e).zoom); if (v && v !== 1) z *= v; } return z; }
  function visible(el) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  function textColor(el) {
    const cs = getComputedStyle(el);
    const fill = cs.webkitTextFillColor;
    const clip = cs.webkitBackgroundClip || cs.backgroundClip;
    const transparentFill = fill && /rgba\(.*,\s*0\)$|transparent/.test(fill);
    if (transparentFill) {
      if (clip === 'text') return accent || cs.color;          // 그라디언트 글자 → 강조색
      const stroke = cs.webkitTextStrokeColor;                   // 외곽선 글자 → 선 색
      if (stroke && !/rgba\(.*,\s*0\)$/.test(stroke)) return stroke;
      return accent || cs.color;
    }
    return (fill && fill !== cs.color && !/currentcolor/i.test(fill)) ? fill : cs.color;
  }
  function runStyle(el, z) {
    const cs = getComputedStyle(el);
    return { color: textColor(el), size: parseFloat(cs.fontSize) * z, weight: parseInt(cs.fontWeight, 10) || 400,
             italic: cs.fontStyle === 'italic', family: cs.fontFamily, upper: cs.textTransform === 'uppercase',
             underline: /underline/.test(cs.textDecorationLine) };
  }
  function pseudoText(el, which) {
    const ps = getComputedStyle(el, which);
    const c = ps.content;
    if (!c || c === 'none' || c === 'normal' || ps.position === 'absolute' || ps.position === 'fixed') return '';
    const m = /^"(.*)"$/.exec(c);
    return m ? m[1] : '';
  }
  const isBlockChild = (n) => n.nodeType === 1 && BLOCKY.test(getComputedStyle(n).display);

  function collectRuns(el, z, runs, isRoot) {
    const pre = pseudoText(el, '::before');
    if (pre) runs.push(Object.assign({ text: pre }, runStyle(el, z)));
    if (el.tagName === 'LI' && isRoot) runs.push(Object.assign({ text: '• ' }, runStyle(el, z)));
    for (const n of el.childNodes) {
      if (n.nodeType === 3) {
        const t = n.textContent.replace(/\s+/g, ' ');
        if (t.trim() || (t === ' ' && runs.length)) runs.push(Object.assign({ text: t }, runStyle(el, z)));
      } else if (n.nodeType === 1) {
        if (n.tagName === 'BR') { runs.push({ br: true }); continue; }
        if (n.matches('aside.notes, .notes, script, style, img, svg, canvas')) continue;
        if (!visible(n) || isBlockChild(n)) continue;           // 블록 자식은 따로 처리
        collectRuns(n, z, runs, false);
      }
    }
    const post = pseudoText(el, '::after');
    if (post) runs.push(Object.assign({ text: post }, runStyle(el, z)));
  }

  const all = slide.querySelectorAll('*');
  const marked = [];
  for (const el of all) {
    if (el.closest('aside.notes, .notes, script, style, svg')) continue;
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    // 인라인 요소는 부모 덩어리에 포함된다
    if (!BLOCKY.test(cs.display)) continue;
    const hasText = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim())
      || Array.from(el.children).some(c => !isBlockChild(c) && c.tagName !== 'BR' && c.textContent.trim() && !c.matches('aside.notes,.notes'));
    if (!hasText) continue;
    const z = zoomOf(el);
    const runs = [];
    collectRuns(el, z, runs, true);
    while (runs.length && runs[runs.length - 1].br) runs.pop();
    if (!runs.some(r => r.text && r.text.trim())) continue;
    // 실제 글자가 차지하는 영역(Range)과 요소 영역을 함께 본다
    const rect = el.getBoundingClientRect();
    const range = document.createRange(); range.selectNodeContents(el);
    const tr = range.getBoundingClientRect();
    const pl = parseFloat(cs.paddingLeft) * z, pr = parseFloat(cs.paddingRight) * z, pt = parseFloat(cs.paddingTop) * z;
    const d = deck.getBoundingClientRect();
    const left = rect.left + pl - d.left, width = rect.width - pl - pr;
    const top = (tr.height ? tr.top : rect.top + pt) - d.top;
    const height = tr.height || rect.height;
    const lh = parseFloat(cs.lineHeight);
    blocks.push({
      x: left, y: top, w: width, h: height,
      align: cs.textAlign, lineHeight: isNaN(lh) ? 1.3 : lh / parseFloat(cs.fontSize),
      ls: parseFloat(cs.letterSpacing) || 0,
      runs: runs,
    });
    marked.push(el);
  }
  // 배경 촬영용: 글자만 투명하게
  for (const el of marked) el.classList.add('__gyeol_hide');
  for (const el of slide.querySelectorAll('.__gyeol_hide, .__gyeol_hide *')) {
    const cs = getComputedStyle(el);
    if ((cs.webkitBackgroundClip || cs.backgroundClip) === 'text') el.style.setProperty('background', 'none', 'important');
  }
  return blocks;
}
"""

# 사진·그림 위치를 읽고 배경 촬영에서 숨긴다
IMAGES_JS = r"""
() => {
  const deck = document.querySelector('.deck');
  const slide = document.querySelector('.slide.is-active');
  if (!slide) return [];
  const d = deck.getBoundingClientRect();
  const out = [];
  for (const img of slide.querySelectorAll('.g-photo img, .g-obj > img')) {
    const r = img.getBoundingClientRect();
    const cs = getComputedStyle(img);
    if (!r.width || !r.height || cs.display === 'none' || cs.visibility === 'hidden') continue;
    const holder = img.closest('.g-photo, .g-obj');
    const hs = getComputedStyle(holder);
    const rad = Math.max(parseFloat(cs.borderTopLeftRadius) || 0, parseFloat(hs.borderTopLeftRadius) || 0,
                         parseFloat(cs.borderTopRightRadius) || 0, parseFloat(hs.borderTopRightRadius) || 0);
    const circle = /50%/.test(cs.borderTopLeftRadius) || /50%/.test(hs.borderTopLeftRadius);
    // 바깥 상자가 잘라내는 경우(액자형 사진 패널) 보이는 영역만
    const hr = holder.getBoundingClientRect();
    const x1 = Math.max(r.left, hr.left), y1 = Math.max(r.top, hr.top);
    const x2 = Math.min(r.right, hr.right), y2 = Math.min(r.bottom, hr.bottom);
    if (x2 <= x1 || y2 <= y1) continue;
    out.push({ src: img.currentSrc || img.src, x: x1 - d.left, y: y1 - d.top, w: x2 - x1, h: y2 - y1,
               nw: img.naturalWidth, nh: img.naturalHeight, fit: cs.objectFit,
               radius: rad, circle: circle, opacity: parseFloat(cs.opacity) * parseFloat(hs.opacity),
               photo: !!img.closest('.g-photo') });
    img.classList.add('__gyeol_img');
  }
  return out;
}
"""

HIDE_CSS = """
.slide{transition:none!important}
*,*::before,*::after{animation:none!important;transition:none!important}
[class*="anim-"],.anim-stagger-list>*{opacity:1!important}
.progress-bar,.notes-overlay,.overview{display:none!important}
.__gyeol_hide,.__gyeol_hide *{color:transparent!important;-webkit-text-fill-color:transparent!important;
  text-shadow:none!important;-webkit-text-stroke-color:transparent!important;text-decoration-color:transparent!important}
.__gyeol_hide li::marker,.__gyeol_hide::marker{color:transparent!important}
.__gyeol_img{visibility:hidden!important}
"""


def _parse_color(c: str):
    """'rgb(1,2,3)' / 'rgba(1,2,3,.5)' / '#abc' → ((r,g,b), alpha)"""
    c = (c or "").strip()
    m = re.match(r"rgba?\(([^)]+)\)", c)
    if m:
        parts = [p.strip() for p in m.group(1).replace("/", ",").split(",")]
        r, g, b = (int(float(p)) for p in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return (r, g, b), a
    m = re.match(r"#([0-9a-fA-F]{3,8})$", c)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h[:3])
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)), 1.0
    return (17, 17, 17), 1.0


def _font_for(family: str, weight: int) -> str:
    f = (family or "").lower()
    if any(k in f for k in MONO_HINTS):
        return "Consolas"
    if any(k in f for k in SERIF_HINTS):
        return "바탕"
    return "맑은 고딕"


def _set_run_font(run, name: str):
    """영문(latin)과 한글(ea) 서체를 따로 지정. 고정폭 서체는 한글이 없어 한글만 맑은 고딕으로."""
    from pptx.oxml.ns import qn
    rPr = run._r.get_or_add_rPr()
    ea_name = "맑은 고딕" if name == "Consolas" else name
    for tag in ("a:latin", "a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", ea_name if tag == "a:ea" else name)


def _set_alpha(run, alpha: float):
    if alpha >= 0.99:
        return
    from pptx.oxml.ns import qn
    fill = run._r.get_or_add_rPr().find(qn("a:solidFill"))
    if fill is not None and len(fill):
        clr = fill[0]
        a = clr.makeelement(qn("a:alpha"), {"val": str(int(max(0.05, alpha) * 100000))})
        clr.append(a)


def _add_textbox(slide, b: dict):
    from pptx.util import Emu, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE

    runs = b["runs"]
    sizes = [r["size"] for r in runs if r.get("text")]
    max_size = max(sizes) if sizes else 20
    # PowerPoint 서체가 웹 서체보다 넓을 수 있어 폭에 여유를 준다
    slack = max(12, b["w"] * 0.08)
    x = max(0, b["x"] - (slack / 2 if b["align"] == "center" else slack if b["align"] in ("right", "end") else 0))
    w = min(W - x, b["w"] + slack)
    y = max(0, b["y"] - max_size * 0.12)
    h = max(b["h"], max_size * 1.2)
    tb = slide.shapes.add_textbox(Emu(int(x * EMU_PER_PX)), Emu(int(y * EMU_PER_PX)),
                                  Emu(int(w * EMU_PER_PX)), Emu(int(h * EMU_PER_PX)))
    tf = tb.text_frame
    # 한 줄짜리 글자는 줄바꿈하지 않게(PowerPoint 서체가 더 넓어도 잘리지 않음)
    one_line = not any(r.get("br") for r in runs) and b["h"] <= max_size * (b.get("lineHeight") or 1.3) * 1.45
    tf.word_wrap = not one_line
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.alignment = {"center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT, "end": PP_ALIGN.RIGHT,
                   "justify": PP_ALIGN.JUSTIFY}.get(b["align"], PP_ALIGN.LEFT)
    p.line_spacing = max(0.8, min(2.2, b.get("lineHeight") or 1.3))
    first = True
    for r in runs:
        if r.get("br"):
            p.add_line_break()
            continue
        text = r["text"]
        if first:
            text = text.lstrip()
            first = False
        if r.get("upper"):
            text = text.upper()
        if not text:
            continue
        run = p.add_run()
        run.text = text
        f = run.font
        f.size = Pt(round(r["size"] * PT_PER_PX * 2) / 2)
        f.bold = r["weight"] >= 600
        f.italic = bool(r.get("italic"))
        f.underline = bool(r.get("underline"))
        (cr, cg, cb), alpha = _parse_color(r["color"])
        f.color.rgb = RGBColor(cr, cg, cb)
        _set_alpha(run, alpha)
        _set_run_font(run, _font_for(r.get("family", ""), r["weight"]))
    return tb


def _image_bytes(src: str) -> bytes:
    """data URI·로컬 파일·인터넷 주소에서 그림 원본을 읽는다."""
    import base64
    import urllib.parse
    import urllib.request
    if src.startswith("data:"):
        head, _, data = src.partition(",")
        return base64.b64decode(data) if ";base64" in head else urllib.parse.unquote_to_bytes(data)
    if src.startswith("file:"):
        from urllib.request import url2pathname
        return Path(url2pathname(urllib.parse.urlparse(src).path)).read_bytes()
    with urllib.request.urlopen(urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
        return r.read()


def _to_png_if_needed(data: bytes) -> bytes:
    """PowerPoint가 못 읽는 형식(webp 등)은 PNG로 바꾼다."""
    if data[:4] == b"RIFF" or data[:5] in (b"<?xml", b"<svg ") or data.lstrip()[:4] == b"<svg":
        from PIL import Image
        try:
            im = Image.open(io.BytesIO(data))
            buf = io.BytesIO()
            im.save(buf, "PNG")
            return buf.getvalue()
        except Exception:
            return b""
    return data


def _add_image(slide, im: dict) -> bool:
    from pptx.util import Emu
    from pptx.enum.shapes import MSO_SHAPE
    try:
        data = _to_png_if_needed(_image_bytes(im["src"]))
    except Exception:
        return False
    if not data:
        return False
    x, y, w, h = im["x"], im["y"], im["w"], im["h"]
    pic = slide.shapes.add_picture(io.BytesIO(data), Emu(int(x * EMU_PER_PX)), Emu(int(y * EMU_PER_PX)),
                                   Emu(int(w * EMU_PER_PX)), Emu(int(h * EMU_PER_PX)))
    # object-fit: cover → 비율을 지키며 넘치는 쪽을 잘라낸다 (PowerPoint [자르기]로 다시 조절 가능)
    nw, nh = im.get("nw") or 0, im.get("nh") or 0
    if im.get("fit") == "cover" and nw and nh and w and h:
        ia, ba = nw / nh, w / h
        if ia > ba:
            c = (1 - ba / ia) / 2
            pic.crop_left = pic.crop_right = c
        elif ia < ba:
            c = (1 - ia / ba) / 2
            pic.crop_top = pic.crop_bottom = c
    try:
        if im.get("circle"):
            pic.auto_shape_type = MSO_SHAPE.OVAL
        elif (im.get("radius") or 0) > 2:
            pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
            pic.adjustments[0] = min(0.5, im["radius"] / max(1, min(w, h)))
    except Exception:
        pass
    pic.name = "사진" if im.get("photo") else "그림"
    return True


def _launch(p):
    for ch in ("msedge", "chrome", None):
        try:
            return p.chromium.launch(channel=ch) if ch else p.chromium.launch()
        except Exception:
            continue
    raise RuntimeError("Edge 또는 Chrome을 실행하지 못했습니다.")


def _paste_crops(page, slide, items):
    """원본을 못 읽은 그림은 화면에서 그 부분만 찍어 같은 자리에 넣는다."""
    from pptx.util import Emu
    for im in items:
        try:
            png = page.screenshot(clip={"x": im["x"], "y": im["y"], "width": im["w"], "height": im["h"]})
            slide.shapes.add_picture(io.BytesIO(png), Emu(int(im["x"] * EMU_PER_PX)), Emu(int(im["y"] * EMU_PER_PX)),
                                     Emu(int(im["w"] * EMU_PER_PX)), Emu(int(im["h"] * EMU_PER_PX)))
        except Exception:
            continue


def slide_pngs(deck_html: str, scale: float = 1.0) -> list:
    """슬라이드마다 화면을 그대로 찍은 PNG 목록 (원본 그대로 PPTX·이미지 묶음용).
    PDF를 거치면 그라데이션 글자 둘레에 상자 선이 생기는 문제가 있어 직접 찍는다."""
    from playwright.sync_api import sync_playwright
    out = []
    with tempfile.TemporaryDirectory(prefix="gyeol_png_") as tmp:
        src = Path(tmp) / "deck.html"
        src.write_text(deck_html, encoding="utf-8")
        with sync_playwright() as p:
            browser = _launch(p)
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
            page.add_init_script("window.__noMotion=true")   # 화면을 찍을 때는 애니메이션 없이
            page.goto(src.resolve().as_uri(), wait_until="load")
            page.add_style_tag(content=HIDE_CSS)
            page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true")
            page.wait_for_timeout(800)
            total = page.evaluate("document.querySelectorAll('.deck .slide').length")
            for i in range(total):
                page.evaluate(f"window.__deck && window.__deck.go({i})")
                page.wait_for_timeout(250)
                out.append(page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H}))
            browser.close()
    return out


def build_editable_pptx(deck_html: str, out_path: str, notes: list, title: str = "") -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("편집 가능한 PPTX에는 playwright가 필요합니다. (pip install playwright)")
    from pptx import Presentation
    from pptx.util import Emu

    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    motion, transition = deck_motion(deck_html)
    blank = prs.slide_layouts[6]

    with tempfile.TemporaryDirectory(prefix="gyeol_pptx_") as tmp:
        src = Path(tmp) / "deck.html"
        src.write_text(deck_html, encoding="utf-8")
        with sync_playwright() as p:
            browser = _launch(p)
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1.5)
            page.add_init_script("window.__noMotion=true")   # 화면을 찍을 때는 애니메이션 없이
            page.goto(src.resolve().as_uri(), wait_until="load")
            page.add_style_tag(content=HIDE_CSS)
            page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true")
            page.wait_for_timeout(800)
            total = page.evaluate("document.querySelectorAll('.deck .slide').length")
            for i in range(total):
                page.evaluate(f"window.__deck && window.__deck.go({i})")
                page.wait_for_timeout(250)
                images = page.evaluate(IMAGES_JS)
                blocks = page.evaluate(EXTRACT_JS)
                png = page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H})

                s = prs.slides.add_slide(blank)
                s.shapes.add_picture(io.BytesIO(png), 0, 0, width=prs.slide_width, height=prs.slide_height)
                failed = [im for im in images if not _add_image(s, im)]
                if failed:  # 원본을 못 읽은 그림은 배경 사진에 다시 찍어 넣는다
                    page.evaluate("document.querySelectorAll('.__gyeol_img').forEach(e=>e.classList.remove('__gyeol_img'))")
                    _paste_crops(page, s, failed)
                page.evaluate("document.querySelectorAll('.__gyeol_img').forEach(e=>e.classList.remove('__gyeol_img'))")
                page.evaluate("document.querySelectorAll('.__gyeol_hide').forEach(e=>e.classList.remove('__gyeol_hide'))")
                for b in blocks:
                    try:
                        _add_textbox(s, b)
                    except Exception:
                        continue
                if i < len(notes) and notes[i]:
                    s.notes_slide.notes_text_frame.text = notes[i]
                try:
                    add_slide_motion(s, motion, transition)
                except Exception:
                    pass
            browser.close()
    if title:
        prs.core_properties.title = title
    prs.save(out_path)
    return len(prs.slides)


# ───────── PowerPoint 애니메이션·전환 (표시 설정의 '애니메이션'·'전환 효과'를 그대로 옮김) ─────────
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def deck_motion(deck_html: str) -> tuple:
    """덱 HTML에서 (애니메이션 단계, 전환 종류)를 읽는다."""
    m = re.search(r"--gyeol-motion:(\w+)", deck_html or "")
    motion = m.group(1) if m else "subtle"
    if ".slide{transition:none!important" in deck_html:
        tr = "none"
    elif "transform:scale(1.08)" in deck_html:
        tr = "zoom"
    elif ".slide{transform:none!important}" in deck_html:
        tr = "fade"
    else:
        tr = "push"
    return motion, tr


def add_slide_motion(slide, motion: str = "subtle", transition: str = "push"):
    """배경(첫 개체)을 뺀 개체가 슬라이드 시작과 함께 위→아래 순서로 차례로 나타나게 하고, 전환 효과를 넣는다."""
    from lxml import etree
    sld = slide._element
    for old in sld.findall(f"{{{P_NS}}}transition") + sld.findall(f"{{{P_NS}}}timing"):
        sld.remove(old)
    tr_xml = {"push": '<p:push dir="u"/>', "fade": '<p:fade/>', "zoom": '<p:zoom/>'}.get(transition)
    anchor = sld.find(f"{{{P_NS}}}clrMapOvr")
    pos = list(sld).index(anchor) + 1 if anchor is not None else len(sld)
    if tr_xml:
        sld.insert(pos, etree.fromstring(f'<p:transition xmlns:p="{P_NS}" spd="med">{tr_xml}</p:transition>'))
        pos += 1
    if motion == "none":
        return
    shapes = list(slide.shapes)[1:]
    shapes.sort(key=lambda sh: (int(sh.top or 0) // 40, int(sh.left or 0)))   # 대략 위에서 아래, 왼쪽에서 오른쪽
    if not shapes:
        return
    step, dur = (180, 600) if motion == "rich" else (110, 450)
    ids = iter(range(3, 100000))
    pars = []
    for k, sh in enumerate(shapes[:60]):
        a, b, c, d = next(ids), next(ids), next(ids), next(ids)
        sid = sh.shape_id
        rise = ""
        if motion == "rich":   # 떠오르기(Float In): 페이드 + 아래에서 위로 살짝 이동
            e1, e2 = next(ids), next(ids)
            rise = (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{e1}" dur="{dur}" fill="hold"/><p:tgtEl><p:spTgt spid="{sid}"/></p:tgtEl>'
                    f'<p:attrNameLst><p:attrName>ppt_x</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst><p:tav tm="0"><p:val><p:strVal val="#ppt_x"/></p:val></p:tav>'
                    f'<p:tav tm="100000"><p:val><p:strVal val="#ppt_x"/></p:val></p:tav></p:tavLst></p:anim>'
                    f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{e2}" dur="{dur}" fill="hold"/><p:tgtEl><p:spTgt spid="{sid}"/></p:tgtEl>'
                    f'<p:attrNameLst><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst><p:tav tm="0"><p:val><p:strVal val="#ppt_y+.06"/></p:val></p:tav>'
                    f'<p:tav tm="100000"><p:val><p:strVal val="#ppt_y"/></p:val></p:tav></p:tavLst></p:anim>')
        preset = "47" if motion == "rich" else "10"
        pars.append(
            f'<p:par><p:cTn id="{a}" fill="hold"><p:stCondLst><p:cond delay="{k * step}"/></p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="{b}" presetID="{preset}" presetClass="entr" presetSubtype="0" fill="hold" nodeType="withEffect">'
            f'<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:set><p:cBhvr><p:cTn id="{c}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            f'<p:tgtEl><p:spTgt spid="{sid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>'
            f'</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
            f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{d}" dur="{dur}"/>'
            f'<p:tgtEl><p:spTgt spid="{sid}"/></p:tgtEl></p:cBhvr></p:animEffect>{rise}'
            f'</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
    timing = (f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
              f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
              f'<p:par><p:cTn id="{next(ids)}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
              f'<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>{"".join(pars)}'
              f'</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>'
              f'<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
              f'<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
              f'</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')
    sld.insert(pos, etree.fromstring(timing))
