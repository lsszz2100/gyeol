"""
결(GYEOL) - 내보내기: HTML / PDF / PPTX / PNG(zip)

- PDF  : Windows에 기본 설치된 Edge(없으면 Chrome)의 헤드리스 인쇄 기능으로 만든다.
- PPTX : PDF를 고해상도 이미지로 바꿔 슬라이드마다 한 장씩 넣고, 발표자 대본은 슬라이드 노트에 넣는다.
- PNG  : 슬라이드별 이미지를 zip으로 묶는다.
"""

import html as _html
import io
import os
import re
import shutil
import logging
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("gyeol.export")

FORMATS = {
    "html": ("HTML 파일", ".html"),
    "pdf": ("PDF 문서", ".pdf"),
    "pptx": ("파워포인트(편집 가능)", ".pptx"),
    "pptx_img": ("파워포인트(이미지)", ".pptx"),
    "png": ("이미지 묶음(PNG)", ".zip"),
    "mp4": ("동영상(MP4)", ".mp4"),
    "md": ("발표 대본 및 개요(Markdown)", ".md"),
    "txt": ("발표자 대본 텍스트", ".txt"),
}


class ExportError(Exception):
    pass


def find_browser() -> str:
    cands = [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    ]
    for c in cands:
        p = os.path.expandvars(c)
        if os.path.isfile(p):
            return p
    for name in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    raise ExportError("PDF를 만들 브라우저(Edge 또는 Chrome)를 찾지 못했습니다.")


def slide_notes(slides_html: str) -> list:
    """슬라이드 순서대로 발표자 대본 텍스트를 뽑는다."""
    out = []
    for sec in re.findall(r"<section\b[^>]*\bslide\b[^>]*>(.*?)</section>", slides_html, re.S | re.I):
        m = re.search(r"<aside[^>]*class=\"[^\"]*notes[^\"]*\"[^>]*>(.*?)</aside>", sec, re.S | re.I)
        txt = re.sub(r"<[^>]+>", " ", m.group(1)) if m else ""
        out.append(re.sub(r"\s+", " ", _html.unescape(txt)).strip())
    return out


def html_to_pdf(deck_html: str, pdf_path: str, timeout: int = 180) -> None:
    browser = find_browser()
    with tempfile.TemporaryDirectory(prefix="gyeol_") as tmp:
        src = Path(tmp) / "deck.html"
        src.write_text(deck_html, encoding="utf-8")
        profile = Path(tmp) / "profile"
        cmd = [
            browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            f"--user-data-dir={profile}", "--no-pdf-header-footer", "--print-to-pdf-no-header",
            "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
            f"--print-to-pdf={pdf_path}", src.resolve().as_uri(),
        ]
        flags = 0x08000000 if os.name == "nt" else 0  # 콘솔 창 숨김
        try:
            subprocess.run(cmd, timeout=timeout, capture_output=True, creationflags=flags)
        except subprocess.TimeoutExpired:
            raise ExportError("PDF 변환 시간이 너무 오래 걸려 중단했습니다.")
    if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) < 1000:
        raise ExportError("PDF를 만들지 못했습니다.")


def _pdf_pages_png(pdf_path: str, zoom: float = 1.2) -> list:
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            raise ExportError("PPTX/이미지 저장에 필요한 PyMuPDF가 없습니다. (pip install pymupdf)")
    pages = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pages.append(page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False).tobytes("png"))
    return pages


def _slide_images(deck_html: str, pdf_path_fn, zoom: float) -> list:
    """슬라이드 이미지: 브라우저로 직접 찍고, 안 되면 PDF를 그림으로 바꾼다."""
    try:
        from core.pptx_editable import slide_pngs
        pages = slide_pngs(deck_html)
        if pages:
            return pages
    except Exception as e:
        logger.warning(f"슬라이드 직접 촬영 실패, PDF 변환으로 대신합니다: {e}")
    return _pdf_pages_png(pdf_path_fn(), zoom=zoom)


def images_to_pptx(pages: list, pptx_path: str, notes: list, title: str = "", transition: str = "") -> None:
    try:
        from pptx import Presentation
        from pptx.util import Emu
    except ImportError:
        raise ExportError("PPTX 저장에 필요한 python-pptx가 없습니다. (pip install python-pptx)")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)  # 16:9 비율
    blank = prs.slide_layouts[6]
    for i, png in enumerate(pages):
        s = prs.slides.add_slide(blank)
        s.shapes.add_picture(io.BytesIO(png), 0, 0, width=prs.slide_width, height=prs.slide_height)
        if i < len(notes) and notes[i]:
            s.notes_slide.notes_text_frame.text = notes[i]
        if transition:   # 이미지 한 장짜리라 개체 애니메이션은 없고 슬라이드 전환만 넣는다
            try:
                from core.pptx_editable import add_slide_motion
                add_slide_motion(s, "none", transition)
            except Exception:
                pass
    if title:
        prs.core_properties.title = title
    prs.save(pptx_path)


def images_to_zip(pages: list, zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for i, png in enumerate(pages, 1):
            z.writestr(f"slide_{i:02d}.png", png)


def slide_deck_to_markdown(slides_html: str, title: str = "") -> str:
    """슬라이드 HTML 전체를 분석하여 구조화된 마크다운 개요 및 발표자 대본 문서로 변환한다."""
    sections = re.findall(r"<section\b([^>]*)>(.*?)</section>", slides_html, re.S | re.I)
    doc_title = title.strip() or "프레젠테이션 발표 개요 및 대본"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    md_lines = [
        f"# {doc_title}",
        "",
        f"- **생성 일시**: {now_str}",
        f"- **총 슬라이드 수**: {len(sections)}장",
        "",
        "---",
        "",
        "## 📋 목차 (Table of Contents)",
        "",
    ]

    parsed_slides = []
    for idx, (attrs, body) in enumerate(sections, 1):
        m_title = re.search(r'data-title="([^"]+)"', attrs, re.I)
        stitle = m_title.group(1).strip() if m_title else ""
        if not stitle:
            m_h = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", body, re.S | re.I)
            stitle = re.sub(r"<[^>]+>", " ", m_h.group(1)).strip() if m_h else f"슬라이드 {idx}"
        stitle = _html.unescape(re.sub(r"\s+", " ", stitle))

        m_notes = re.search(r"<aside[^>]*class=\"[^\"]*notes[^\"]*\"[^>]*>(.*?)</aside>", body, re.S | re.I)
        notes_txt = re.sub(r"<[^>]+>", " ", m_notes.group(1)) if m_notes else ""
        notes_clean = re.sub(r"\s+", " ", _html.unescape(notes_txt)).strip()

        m_kicker = re.search(r'<span[^>]*class="[^"]*kicker[^"]*"[^>]*>(.*?)</span>', body, re.S | re.I)
        kicker_txt = re.sub(r"<[^>]+>", "", m_kicker.group(1)).strip() if m_kicker else ""

        points = []
        for li in re.findall(r"<li\b[^>]*>(.*?)</li>", body, re.S | re.I):
            pt = re.sub(r"<[^>]+>", " ", li).strip()
            if pt:
                points.append(_html.unescape(re.sub(r"\s+", " ", pt)))
        for ch4 in re.findall(r"<h4\b[^>]*>(.*?)</h4>(?:\s*<p[^>]*>(.*?)</p>)?", body, re.S | re.I):
            head_txt = _html.unescape(re.sub(r"<[^>]+>", " ", ch4[0])).strip()
            desc_txt = _html.unescape(re.sub(r"<[^>]+>", " ", ch4[1])).strip() if ch4[1] else ""
            if head_txt:
                points.append(f"{head_txt}: {desc_txt}" if desc_txt else head_txt)

        if not points:
            for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S | re.I):
                pt = re.sub(r"<[^>]+>", " ", p).strip()
                if pt and len(pt) > 5 and "notes" not in pt:
                    points.append(_html.unescape(re.sub(r"\s+", " ", pt)))

        parsed_slides.append({
            "idx": idx,
            "title": stitle,
            "kicker": kicker_txt,
            "points": points[:6],
            "notes": notes_clean
        })
        md_lines.append(f"{idx}. [{stitle}](#slide-{idx})")

    md_lines.extend(["", "---", ""])

    for s in parsed_slides:
        idx = s["idx"]
        md_lines.append(f'<a id="slide-{idx}"></a>')
        header_kicker = f" *({s['kicker']})*" if s['kicker'] else ""
        md_lines.append(f"## [슬라이드 {idx:02d}] {s['title']}{header_kicker}")
        md_lines.append("")
        if s["points"]:
            md_lines.append("### 📌 핵심 내용 요약")
            for pt in s["points"]:
                md_lines.append(f"- {pt}")
            md_lines.append("")

        md_lines.append("### 🎙️ 발표자 대본 (Speaker Script)")
        if s["notes"]:
            md_lines.append(f"> {s['notes']}")
        else:
            md_lines.append("> *(대본 없음)*")
        md_lines.extend(["", "---", ""])

    return "\n".join(md_lines)


def slide_deck_to_txt(slides_html: str, title: str = "") -> str:
    """발표 연습 및 프롬프터용 순수 발표자 대본 텍스트 전문을 생성한다."""
    sections = re.findall(r"<section\b([^>]*)>(.*?)</section>", slides_html, re.S | re.I)
    doc_title = title.strip() or "프레젠테이션 발표 대본 전문"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "============================================================",
        f" {doc_title} - 발표자 대본 전문",
        f" 작성일시: {now_str} (총 {len(sections)}장)",
        "============================================================",
        "",
    ]
    for idx, (attrs, body) in enumerate(sections, 1):
        m_title = re.search(r'data-title="([^"]+)"', attrs, re.I)
        stitle = m_title.group(1).strip() if m_title else ""
        if not stitle:
            m_h = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", body, re.S | re.I)
            stitle = re.sub(r"<[^>]+>", " ", m_h.group(1)).strip() if m_h else f"슬라이드 {idx}"
        stitle = _html.unescape(re.sub(r"\s+", " ", stitle))

        m_notes = re.search(r"<aside[^>]*class=\"[^\"]*notes[^\"]*\"[^>]*>(.*?)</aside>", body, re.S | re.I)
        notes_txt = re.sub(r"<[^>]+>", " ", m_notes.group(1)) if m_notes else ""
        notes_clean = re.sub(r"\s+", " ", _html.unescape(notes_txt)).strip()

        lines.append(f"[슬라이드 {idx:02d}. {stitle}]")
        lines.append(notes_clean if notes_clean else "(대본 없음)")
        lines.append("")
    return "\n".join(lines)


def export(fmt: str, deck_html: str, slides_html: str, out_path: str, title: str = "") -> str:
    fmt = fmt.lower()
    if fmt not in FORMATS:
        raise ExportError(f"지원하지 않는 형식입니다: {fmt}")
    out_path = str(out_path)
    if fmt in ("html", "pdf", "pptx", "pptx_img", "png", "mp4"):
        # 다른 PC·인터넷 없는 곳에서도 만든 그대로 보이도록 실제로 쓰인 웹폰트를 파일 안에 넣는다
        from core.font_embed import embed_fonts
        deck_html = embed_fonts(deck_html)
    if fmt == "html":
        Path(out_path).write_text(deck_html, encoding="utf-8")
        return out_path
    if fmt == "md":
        Path(out_path).write_text(slide_deck_to_markdown(slides_html, title), encoding="utf-8")
        return out_path
    if fmt == "txt":
        Path(out_path).write_text(slide_deck_to_txt(slides_html, title), encoding="utf-8")
        return out_path
    if fmt == "mp4":
        from core.video_export import export_video, VideoError
        try:
            export_video(deck_html, out_path)
        except VideoError as e:
            raise ExportError(str(e))
        return out_path
    if fmt == "pdf":
        html_to_pdf(deck_html, out_path)
        return out_path
    if fmt == "pptx":
        from core.pptx_editable import build_editable_pptx
        try:
            build_editable_pptx(deck_html, out_path, slide_notes(slides_html), title)
        except RuntimeError as e:
            raise ExportError(str(e))
        return out_path
    with tempfile.TemporaryDirectory(prefix="gyeol_pdf_") as tmp:
        def make_pdf():
            pdf = os.path.join(tmp, "deck.pdf")
            html_to_pdf(deck_html, pdf)
            return pdf
        pages = _slide_images(deck_html, make_pdf, zoom=1.2)
        if fmt == "pptx_img":
            from core.pptx_editable import deck_motion
            images_to_pptx(pages, out_path, slide_notes(slides_html), title, deck_motion(deck_html)[1])
        else:
            images_to_zip(pages, out_path)
    return out_path
