"""내 자료로 만들기: 첨부 파일에서 글자만 뽑아 슬라이드 생성의 근거로 쓴다 (core/sources.py).
지원: PDF, Word(.docx), 파워포인트(.pptx), 한글(.hwpx), 엑셀(.xlsx), 텍스트(.txt .md .csv), 사진(.png .jpg .webp).
글자가 없는 스캔 PDF·사진은 AI(Gemini 비전)가 글자를 읽고, 아주 긴 문서는 생성할 때 AI가 핵심만 요약한다.
파일은 저장하지 않고 글자만 메모리에서 쓴다."""
import base64
import csv
import io
import os
import re
import xml.etree.ElementTree as ET
import zipfile

MAX_BYTES = 20 * 1024 * 1024     # 파일 1개
MAX_CHARS = 300000               # 파일 1개에서 읽어 두는 글자 수 (길면 생성할 때 AI가 핵심만 요약)
TOTAL_CHARS = 400000             # 전체 읽어 두는 글자 수
DIRECT_CHARS = 80000             # 이 이하면 원문 그대로 AI에 넘기고, 넘으면 요약해서 넘긴다
CHUNK_CHARS = 20000              # 요약할 때 한 번에 읽는 글자 수
OCR_MAX_PAGES = 30               # 스캔 문서에서 글자를 읽어 낼 최대 쪽수
OCR_BATCH = 5                    # 한 번에 AI에 보여 주는 쪽수
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
MAX_ZIP_ENTRY = 80 * 1024 * 1024 # 압축을 푼 XML 1개 크기 (압축 폭탄 방지)


class SourceError(Exception):
    """사용자에게 그대로 보여 줄 오류."""


def _xml_text(data: bytes, para_tags: tuple) -> str:
    """XML에서 글자만 추출. para_tags 로 끝나는 요소마다 줄을 바꾼다."""
    lines, cur = [], []
    for ev, el in ET.iterparse(io.BytesIO(data), events=("end",)):
        tag = el.tag.rsplit("}", 1)[-1]
        if tag in ("t", "T"):
            cur.append(el.text or "")
        elif tag == "tab":
            cur.append(" ")
        if tag in para_tags:
            if "".join(cur).strip():
                lines.append("".join(cur).strip())
            cur = []
            el.clear()
    if "".join(cur).strip():
        lines.append("".join(cur).strip())
    return "\n".join(lines)


def _zip_read(z: zipfile.ZipFile, name: str) -> bytes:
    if z.getinfo(name).file_size > MAX_ZIP_ENTRY:
        raise SourceError("파일 안의 내용이 너무 큽니다.")
    return z.read(name)


def _open_zip(data: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise SourceError("파일이 손상되었거나 암호가 걸려 있습니다.")


def _docx(data):
    z = _open_zip(data)
    if "word/document.xml" not in z.namelist():
        raise SourceError("Word 문서 형식이 아닙니다.")
    return _xml_text(_zip_read(z, "word/document.xml"), ("p",))


def _hwpx(data):
    z = _open_zip(data)
    secs = sorted((n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n)),
                  key=lambda n: int(re.search(r"\d+", n).group()))
    if not secs:
        raise SourceError("한글 문서 형식이 아닙니다.")
    return "\n".join(_xml_text(_zip_read(z, n), ("p",)) for n in secs)


def _xlsx(data):
    z = _open_zip(data)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for ev, el in ET.iterparse(io.BytesIO(_zip_read(z, "xl/sharedStrings.xml")), events=("end",)):
            if el.tag.rsplit("}", 1)[-1] == "si":
                shared.append("".join(x.text or "" for x in el.iter() if x.tag.rsplit("}", 1)[-1] == "t"))
                el.clear()
    sheets = sorted((n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)),
                    key=lambda n: int(re.search(r"\d+", n.rsplit("/", 1)[1]).group()))
    if not sheets:
        raise SourceError("엑셀 문서 형식이 아닙니다.")
    out = []
    for n, name in enumerate(sheets, 1):
        out.append(f"[시트 {n}]")
        for ev, row in ET.iterparse(io.BytesIO(_zip_read(z, name)), events=("end",)):
            if row.tag.rsplit("}", 1)[-1] != "row":
                continue
            cells = []
            for c in row:
                v = next((x.text for x in c.iter() if x.tag.rsplit("}", 1)[-1] in ("v", "t") and x.text), "")
                if c.get("t") == "s" and v.isdigit() and int(v) < len(shared):
                    v = shared[int(v)]
                cells.append(v)
            if any(cells):
                out.append("\t".join(cells))
            row.clear()
    return "\n".join(out)


def _pptx(data):
    from pptx import Presentation
    try:
        prs = Presentation(io.BytesIO(data))
    except Exception:
        raise SourceError("파일이 손상되었거나 암호가 걸려 있습니다.")
    out = []
    for i, s in enumerate(prs.slides, 1):
        lines = []
        for sh in s.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                lines.append(sh.text_frame.text.strip())
            if getattr(sh, "has_table", False) and sh.has_table:
                for r in sh.table.rows:
                    lines.append("\t".join(c.text.strip() for c in r.cells))
        if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip():
            lines.append("(발표자 노트) " + s.notes_slide.notes_text_frame.text.strip())
        if lines:
            out.append(f"[슬라이드 {i}]\n" + "\n".join(lines))
    return "\n\n".join(out)


def _pdf(data):
    import pymupdf as fitz
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        raise SourceError("PDF 파일을 열 수 없습니다.")
    if doc.needs_pass:
        raise SourceError("암호가 걸린 PDF입니다. 암호를 푼 뒤 다시 넣어 주세요.")
    return "\n\n".join(p.get_text().strip() for p in doc), doc.page_count


def _pdf_page_images(data, limit=OCR_MAX_PAGES):
    """스캔한 PDF의 쪽을 사진(JPEG)으로 만든다 → [(바이트, 'image/jpeg')…], 전체 쪽수."""
    import pymupdf as fitz
    doc = fitz.open(stream=data, filetype="pdf")
    out = []
    for i in range(min(limit, doc.page_count)):
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(1.8, 1.8))
        out.append((pix.tobytes("jpeg", jpg_quality=78), "image/jpeg"))
    return out, doc.page_count


def _ocr_images(images: list, ocr) -> str:
    """사진 여러 장을 OCR_BATCH 장씩 AI에 보여 글자를 읽어 낸다. ocr(images)->글자."""
    parts = []
    for i in range(0, len(images), OCR_BATCH):
        parts.append((ocr(images[i:i + OCR_BATCH]) or "").strip())
    return "\n\n".join(p for p in parts if p)


def _text(data):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "ignore")


def read_file(name: str, b64: str, ocr=None) -> dict:
    """{'name', 'text', 'chars', 'truncated', 'ocr', 'long'} 반환. 읽을 수 없으면 SourceError.
    ocr(images)->글자 가 있으면 스캔한 PDF·사진 파일의 글자를 AI로 읽어 낸다 (없으면 안내 문구로 거절)."""
    name = os.path.basename(str(name or "")).strip()[:120] or "자료"
    ext = os.path.splitext(name)[1].lower()
    if len(b64 or "") > MAX_BYTES * 1.4:
        raise SourceError("파일이 너무 큽니다 (20MB 이하만 가능).")
    try:
        data = base64.b64decode(b64 or "", validate=True)
    except Exception:
        raise SourceError("파일을 읽지 못했습니다.")
    if not data:
        raise SourceError("빈 파일입니다.")
    if len(data) > MAX_BYTES:
        raise SourceError("파일이 너무 큽니다 (20MB 이하만 가능).")
    pages = 0
    used_ocr = False
    try:
        if ext in IMAGE_EXTS:
            if not ocr:
                raise SourceError("사진 속 글자를 읽으려면 ⚙️ 설정에서 Gemini 키를 연결해 주세요.")
            mime = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"
            text, used_ocr = _ocr_images([(data, mime)], ocr), True
        elif ext == ".pdf":
            text, pages = _pdf(data)
            if len(re.sub(r"\s", "", text)) < 30 and pages and ocr:   # 글자가 없는 스캔 PDF → AI가 사진으로 읽는다
                imgs, _n = _pdf_page_images(data)
                text, used_ocr = _ocr_images(imgs, ocr), True
                if pages > OCR_MAX_PAGES:
                    text += f"\n\n(스캔 문서라 앞의 {OCR_MAX_PAGES}쪽만 읽었습니다)"
        elif ext == ".docx":
            text = _docx(data)
        elif ext == ".hwpx":
            text = _hwpx(data)
        elif ext == ".pptx":
            text = _pptx(data)
        elif ext == ".xlsx":
            text = _xlsx(data)
        elif ext in (".txt", ".md", ".csv", ".tsv"):
            text = _text(data)
        elif ext == ".hwp":
            raise SourceError("HWP는 바로 읽을 수 없습니다. 한글에서 'HWPX'로 저장하거나 PDF로 저장해 넣어 주세요.")
        elif ext in (".doc", ".ppt", ".xls"):
            raise SourceError(f"옛 형식({ext})은 읽을 수 없습니다. {ext}x 로 저장하거나 PDF로 저장해 넣어 주세요.")
        else:
            raise SourceError("지원하지 않는 파일입니다. PDF, Word, 파워포인트, 한글(HWPX), 엑셀, 텍스트, 사진(PNG·JPG) 파일을 넣어 주세요.")
    except SourceError:
        raise
    except Exception as e:
        raise SourceError(f"파일을 읽는 중 문제가 생겼습니다: {e}")
    text = re.sub(r"[ \t]+\n", "\n", text.replace("\r\n", "\n"))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(re.sub(r"\s", "", text)) < 30:
        if ext == ".pdf" and pages:
            raise SourceError("글자를 읽을 수 없는 PDF입니다 (사진으로 스캔한 문서). 글자가 있는 원본 파일을 넣어 주세요.")
        raise SourceError("파일에서 읽을 수 있는 글자가 거의 없습니다.")
    return {"name": name, "text": text[:MAX_CHARS], "chars": len(text), "truncated": len(text) > MAX_CHARS,
            "ocr": used_ocr, "long": len(text) > DIRECT_CHARS}


def _chunks(text: str, size: int = CHUNK_CHARS) -> list:
    """문단 경계에서 size 글자 안팎으로 나눈다."""
    out, cur, n = [], [], 0
    for para in re.split(r"\n{2,}|\n", text):
        if n + len(para) > size and cur:
            out.append("\n".join(cur)); cur, n = [], 0
        while len(para) > size:       # 줄바꿈 없이 아주 긴 덩어리
            out.append(para[:size]); para = para[size:]
        cur.append(para); n += len(para) + 1
    if cur:
        out.append("\n".join(cur))
    return out


def condense(name: str, text: str, budget: int, summarize) -> str:
    """긴 문서를 문서 순서대로 나눠 조각마다 핵심만 뽑아 budget 글자 안팎으로 줄인다.
    summarize(조각, 목표글자, 파일명, 번호, 전체수)->요약. 일부 조각이 실패하면 그 조각은 앞부분만 쓴다."""
    from concurrent.futures import ThreadPoolExecutor
    chunks = _chunks(text)
    each = max(600, budget // max(1, len(chunks)))

    def one(a):
        i, c = a
        try:
            r = (summarize(c, each, name, i + 1, len(chunks)) or "").strip()
            if r:
                return r
        except Exception as e:
            from logging import getLogger
            getLogger("kdesign.sources").warning(f"{name} {i + 1}/{len(chunks)} 요약 실패, 앞부분만 사용: {e}")
        return c[:each]
    with ThreadPoolExecutor(max_workers=3) as ex:
        parts = list(ex.map(one, enumerate(chunks)))
    return "\n\n".join(f"[{i + 1}/{len(parts)}부분] {p}" for i, p in enumerate(parts))


def build_material(items: list, summarize=None) -> tuple:
    """화면이 보낸 [{name, text}] → (AI에 줄 자료 글, 파일 이름 목록).
    전체가 DIRECT_CHARS 이하면 원문 그대로, 넘으면 summarize 로 파일마다 핵심만 줄여서 넘긴다
    (summarize 가 없으면 앞부분만 잘라 쓴다)."""
    clean = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        name, text = str(it.get("name") or "자료")[:120], str(it.get("text") or "")[:MAX_CHARS]
        if text.strip():
            clean.append((name, text))
    total = sum(len(t) for _, t in clean)
    parts, names = [], []
    left = TOTAL_CHARS
    for name, text in clean:
        if left <= 0:
            break
        text = text[:left]
        left -= len(text)
        if total > DIRECT_CHARS:
            share = max(4000, DIRECT_CHARS * len(text) // max(1, total))
            if len(text) > share:
                text = condense(name, text, share, summarize) if summarize else text[:share]
        names.append(name)
        parts.append(f"--- 파일: {name} ---\n{text}")
    return "\n\n".join(parts), names
