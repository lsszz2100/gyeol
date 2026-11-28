"""내 자료로 만들기: 첨부 파일에서 글자만 뽑아 슬라이드 생성의 근거로 쓴다 (core/sources.py).
지원: PDF, Word(.docx), 파워포인트(.pptx), 한글(.hwpx), 엑셀(.xlsx), 텍스트(.txt .md .csv), 사진(.png .jpg .webp).
글자가 없는 스캔 PDF·사진은 AI(Gemini 비전)가 글자를 읽고, 아주 긴 문서는 생성할 때 AI가 핵심만 요약한다.
파일 자체는 저장하지 않는다. 파일 안의 사진(또는 사진 파일 자체)은 쓸 만한 것만 골라 내 사진 보관함(media)에 저장해
슬라이드 생성 때 AI가 내용에 맞는 장에 배치한다."""
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
IMG_PER_FILE = 12                # 파일 1개에서 꺼내는 사진 최대 장수
IMG_MIN_SIDE = 220               # 짧은 변이 이보다 작으면 아이콘·장식으로 보고 뺀다
IMG_MIN_AREA = 120_000           # 넓이(px)가 이보다 작으면 뺀다
IMG_MAX_RATIO = 3.2              # 가로세로 비율이 이보다 크면 줄무늬·띠 장식으로 보고 뺀다
IMG_MAX_BYTES = 15 * 1024 * 1024
IMG_MAX_PIXELS = 40_000_000      # 펼치면 이보다 큰 그림은 건너뛴다 (메모리 폭주 방지)
IMG_SCAN_LIMIT = 60              # 파일 1개에서 살펴보는 그림 최대 개수
PDF_FULLPAGE = 0.8               # PDF 쪽 넓이의 이만큼 이상을 덮는 그림은 스캔한 쪽으로 보고 뺀다
ZIP_MEDIA_RE = re.compile(r"(word/media|ppt/media|xl/media|BinData|Contents/BinData)/[^/]+\.(png|jpe?g|webp|gif|bmp|tiff?)$", re.I)


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


def _usable_image(data: bytes):
    """쓸 만한 사진이면 (바이트, mime, 폭, 높이), 아이콘·장식·깨진 그림이면 None.
    BMP·TIFF 같은 형식은 PNG로 바꾼다."""
    if not data or len(data) > IMG_MAX_BYTES:
        return None
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))   # 여기서는 머리 정보만 읽는다
        w, h = im.size
        if w * h > IMG_MAX_PIXELS:
            return None
        im.load()
    except Exception:
        return None
    if min(w, h) < IMG_MIN_SIDE or w * h < IMG_MIN_AREA or max(w, h) / max(1, min(w, h)) > IMG_MAX_RATIO:
        return None
    try:   # 한 가지 색으로 거의 채워진 그림(빈 배경·선)은 뺀다
        small = im.convert("L").resize((32, 32))
        lo, hi = small.getextrema()
        if hi - lo < 18:
            return None
    except Exception:
        pass
    fmt = (im.format or "").upper()
    mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(fmt)
    if not mime:   # GIF·BMP·TIFF 등 → PNG
        out = io.BytesIO()
        im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").save(out, "PNG")
        data, mime = out.getvalue(), "image/png"
    return data, mime, w, h


def _zip_images(data: bytes) -> list:
    """Word·파워포인트·한글(HWPX)·엑셀 안의 사진 → [(바이트, 자리 설명)] (문서 순서대로)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return []
    names = [n for n in z.namelist() if ZIP_MEDIA_RE.search(n)]
    names.sort(key=lambda n: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", n)])
    names = names[:IMG_SCAN_LIMIT]
    out = []
    for n in names:
        try:
            if z.getinfo(n).file_size > IMG_MAX_BYTES:
                continue
            out.append((z.read(n), ""))
        except Exception:
            continue
    return out


def _pptx_images(data: bytes) -> list:
    """파워포인트는 사진이 들어 있는 슬라이드의 제목을 자리 설명으로 붙인다."""
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        prs = Presentation(io.BytesIO(data))
    except Exception:
        return _zip_images(data)
    out, seen = [], set()

    def walk(shapes, where):
        for sh in shapes:
            if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                walk(sh.shapes, where)
            elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    blob = sh.image.blob
                except Exception:
                    continue
                if blob[:64] in seen or len(out) >= IMG_SCAN_LIMIT:
                    continue
                seen.add(blob[:64])
                out.append((blob, where))
    for i, s in enumerate(prs.slides, 1):
        title = ""
        try:
            if s.shapes.title is not None:
                title = s.shapes.title.text_frame.text.strip()
        except Exception:
            pass
        walk(s.shapes, f"원본 {i}번 슬라이드" + (f" '{title[:40]}'" if title else ""))
    return out


def _pdf_images(data: bytes) -> list:
    """PDF에 들어 있는 사진 → [(바이트, 'n쪽')]"""
    import pymupdf as fitz
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        return []
    out, seen = [], set()
    for pno in range(min(doc.page_count, 200)):
        page = doc[pno]
        page_area = abs(page.rect) or 1
        for info in page.get_images(full=True):
            xref, w, h = info[0], info[2], info[3]
            if xref in seen:
                continue
            seen.add(xref)
            if w * h > IMG_MAX_PIXELS or len(seen) > IMG_SCAN_LIMIT * 3:
                continue
            try:
                if any(abs(r) / page_area >= PDF_FULLPAGE for r in page.get_image_rects(xref)):
                    continue   # 쪽 전체를 덮는 그림 = 스캔한 쪽 또는 배경
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:     # CMYK → RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width < IMG_MIN_SIDE or pix.height < IMG_MIN_SIDE:
                    continue
                out.append((pix.tobytes("png"), f"원본 {pno + 1}쪽"))
            except Exception:
                continue
            if len(out) >= IMG_PER_FILE * 3:
                return out
    return out


def extract_images(name: str, data: bytes) -> list:
    """파일에서 쓸 만한 사진만 골라 [{'data','mime','w','h','where'}] (최대 IMG_PER_FILE장, 같은 사진은 한 번만)."""
    ext = os.path.splitext(name)[1].lower()
    if ext in IMAGE_EXTS:
        raw = [(data, "")]
    elif ext == ".pptx":
        raw = _pptx_images(data)
    elif ext in (".docx", ".hwpx", ".xlsx"):
        raw = _zip_images(data)
    elif ext == ".pdf":
        raw = _pdf_images(data)
    else:
        return []
    import hashlib
    out, seen = [], set()
    for blob, where in raw:
        ok = _usable_image(blob)
        if not ok:
            continue
        b, mime, w, h = ok
        hsh = hashlib.sha1(b).hexdigest()
        if hsh in seen:
            continue
        seen.add(hsh)
        out.append({"data": b, "mime": mime, "w": w, "h": h, "where": where})
        if len(out) >= IMG_PER_FILE:
            break
    return out


def read_file(name: str, b64: str, ocr=None, save_image=None, describe=None) -> dict:
    """{'name', 'text', 'chars', 'truncated', 'ocr', 'long', 'images'} 반환. 읽을 수 없으면 SourceError.
    ocr(images)->글자 가 있으면 스캔한 PDF·사진 파일의 글자를 AI로 읽어 낸다.
    save_image(바이트, mime)->'/media/…' 가 있으면 파일 안의 쓸 만한 사진을 저장해 images 로 돌려준다.
    describe([(바이트, mime)…])->[설명…] 가 있으면 사진마다 한 줄 설명을 붙인다 (AI가 어울리는 장을 고를 때 씀).
    사진 파일은 글자가 없어도 사진으로 받는다."""
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
    images = []
    if save_image:
        try:
            images = _save_images(name, data, save_image, describe)
        except Exception as e:
            from logging import getLogger
            getLogger("kdesign.sources").warning(f"{name}: 사진 꺼내기 실패, 글자만 사용: {e}")
    try:
        if ext in IMAGE_EXTS:
            mime = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"
            if images:   # 사진 자체를 쓴다. 사진 속 글자가 있으면 덤으로 읽어 둔다
                text = ""
                if ocr:
                    try:
                        text, used_ocr = _ocr_images([(data, mime)], ocr), True
                    except Exception:
                        text = ""
                if len(re.sub(r"\s", "", text)) < 30:   # 사진 속 글자가 거의 없으면 사진으로만 쓴다
                    text = ""
                return {"name": name, "text": text[:MAX_CHARS], "chars": len(text), "truncated": False,
                        "ocr": bool(text) and used_ocr, "long": False, "images": images, "photo_only": not text}
            if not ocr:
                raise SourceError("사진 속 글자를 읽으려면 ⚙️ 설정에서 Gemini 키를 연결해 주세요.")
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
        if images:   # 글자는 거의 없지만 사진이 있는 파일 → 사진만 쓴다
            return {"name": name, "text": "", "chars": 0, "truncated": False, "ocr": False, "long": False,
                    "images": images, "photo_only": True}
        if ext == ".pdf" and pages:
            raise SourceError("글자를 읽을 수 없는 PDF입니다 (사진으로 스캔한 문서). 글자가 있는 원본 파일을 넣어 주세요.")
        raise SourceError("파일에서 읽을 수 있는 글자가 거의 없습니다.")
    return {"name": name, "text": text[:MAX_CHARS], "chars": len(text), "truncated": len(text) > MAX_CHARS,
            "ocr": used_ocr, "long": len(text) > DIRECT_CHARS, "images": images}


def _save_images(name: str, data: bytes, save_image, describe=None) -> list:
    """파일 안의 쓸 만한 사진을 저장하고 [{'url','desc','w','h'}] 를 돌려준다."""
    found = extract_images(name, data)
    if not found:
        return []
    descs = []
    if describe:
        try:
            descs = describe([(f["data"], f["mime"]) for f in found]) or []
        except Exception as e:
            from logging import getLogger
            getLogger("kdesign.sources").info(f"{name}: 사진 설명 실패, 자리 정보만 사용: {e}")
    base = os.path.splitext(name)[0][:40]
    out = []
    for i, f in enumerate(found):
        try:
            url = save_image(f["data"], f["mime"])
        except Exception:
            continue
        d = (descs[i] if i < len(descs) else "") or ""
        d = re.sub(r"\s+", " ", str(d)).strip()[:120]
        where = f["where"] or (f"「{base}」 사진" if len(found) == 1 else f"「{base}」 {i + 1}번째 사진")
        out.append({"url": url, "desc": d, "where": where[:80], "w": f["w"], "h": f["h"]})
    return out


MAX_USER_IMAGES = 16   # 한 번 생성에 쓰는 내 사진 최대 장수


def clean_images(items: list, exists) -> list:
    """화면이 보낸 내 사진 목록을 검사한다 → [{'url','desc','where','w','h'}]. exists(url)->bool 로 실제 파일 확인."""
    out, seen = [], set()
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        url = str(it.get("url") or "")
        if url in seen or not re.fullmatch(r"/media/[0-9a-f]{20}\.(jpg|png|webp|gif)", url) or not exists(url):
            continue
        seen.add(url)
        try:
            w, h = int(it.get("w") or 0), int(it.get("h") or 0)
        except (TypeError, ValueError):
            w = h = 0
        out.append({"url": url, "desc": re.sub(r"\s+", " ", str(it.get("desc") or "")).strip()[:120],
                    "where": re.sub(r"\s+", " ", str(it.get("where") or "")).strip()[:80], "w": w, "h": h})
        if len(out) >= MAX_USER_IMAGES:
            break
    return out


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
