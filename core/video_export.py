"""
결(GYEOL) - 발표를 동영상(MP4)으로 내보내기

슬라이드마다 등장 애니메이션·전환 효과를 그대로 재생한 모습을 1920×1080 영상으로 만든다.
화면을 실시간으로 녹화하지 않고, 모든 애니메이션을 멈춘 뒤 시간을 한 프레임(1/30초)씩 넘기며 찍는다
(window.__gyeolSeek). 그래서 PC가 느려도 끊김 없이 일정한 영상이 나온다.
영상 인코딩은 imageio-ffmpeg 에 들어 있는 ffmpeg 로 한다.
"""

import base64
import logging
import math
import re
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("gyeol.video")

FPS = 30
CHROME_CSS = """
.progress-bar,.notes-overlay,.overview,.deck-header,.deck-footer,.slide-number-ui{display:none!important}
.notes,aside.notes{display:none!important}
"""


class VideoError(Exception):
    pass


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        raise VideoError(f"영상 인코더를 찾지 못했습니다. 프로그램을 최신 전체 설치 파일로 다시 설치해 주세요. ({e})")


def _hold_ms(chars: int) -> int:
    """애니메이션이 끝난 뒤 머무는 시간: 글이 많을수록 길게 (2.5~6초)."""
    return int(min(6000, max(2500, 1800 + chars * 25)))


_SLIDE_INFO_JS = """(i) => {
    window.__vclock = 0;
    window.__deck.go(i);
    const s = document.querySelectorAll('.deck .slide')[i];
    void getComputedStyle(s).opacity;
    const end = window.__gyeolSeek(0) || 0;
    const trans = Math.max(0, ...document.getAnimations().filter(a => !a.id).map(a => {
        const t = a.effect && a.effect.getComputedTiming ? a.effect.getComputedTiming() : null;
        return t && isFinite(t.endTime) ? t.endTime : 0; }));
    const text = (s.innerText || '').replace(/\\s+/g, '').length;
    return {end, trans, text};
}"""


def _encoder(ff: str, fps: int, out: str) -> subprocess.Popen:
    cmd = [ff, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
           "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-r", str(fps), out]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _render_segment(src_uri: str, slides: list, ff: str, fps: int, out: str, done_cb) -> int:
    """slides 범위를 한 브라우저로 찍어 out(mp4 조각)으로 만든다. 첫 장 앞 장면은 앞 슬라이드에서 넘어오는 전환."""
    from playwright.sync_api import sync_playwright
    from core.pptx_editable import _launch, W, H
    proc = _encoder(ff, fps, out)
    frames = 0
    try:
        with sync_playwright() as p:
            browser = _launch(p)
            page = browser.new_page(viewport={"width": W, "height": H})
            page.goto(src_uri, wait_until="load")
            page.add_style_tag(content=CHROME_CSS)
            page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true")
            page.wait_for_timeout(500)
            cdp = page.context.new_cdp_session(page)   # 화면 캡처를 직접 요청(Playwright 스크린샷보다 빠름)
            if slides[0] > 0:   # 앞 장을 끝난 상태로 두고 시작해야 전환이 이어진다
                page.evaluate("(i) => { window.__vclock = 0; window.__deck.go(i); window.__gyeolSeek(600000); }", slides[0] - 1)
            for i in slides:
                info = page.evaluate(_SLIDE_INFO_JS, i)
                dur = max(info["end"], info["trans"]) + _hold_ms(int(info["text"]))
                for f in range(int(math.ceil(dur / 1000 * fps))):
                    cdp.send("Runtime.evaluate", {"expression": f"window.__gyeolSeek({f * 1000 / fps})"})
                    shot = cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 92, "optimizeForSpeed": True,
                                                               "clip": {"x": 0, "y": 0, "width": W, "height": H, "scale": 1}})
                    proc.stdin.write(base64.b64decode(shot["data"]))
                    frames += 1
                done_cb()
            browser.close()
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
        rc = proc.wait(timeout=600)
    if rc != 0:
        raise VideoError(f"영상 인코딩에 실패했습니다. ({err[-200:]})")
    return frames


def export_video(deck_html: str, out_path: str, fps: int = FPS, on_progress=None, workers: int = 0) -> str:
    """여러 브라우저가 슬라이드 묶음을 나눠 동시에 찍고, 조각 영상을 이어 붙인다."""
    import os
    import threading
    out_path = str(out_path)
    ff = _ffmpeg()
    with tempfile.TemporaryDirectory(prefix="gyeol_video_") as tmp:
        src = Path(tmp) / "deck.html"
        src.write_text(deck_html, encoding="utf-8")
        total = len(re.findall(r'<section\b[^>]*class="[^"]*\bslide\b', deck_html))
        if not total:
            raise VideoError("슬라이드가 없습니다.")
        n = workers or max(1, min(3, (os.cpu_count() or 2) // 2, total))
        chunks = [list(range(total))[k * total // n:(k + 1) * total // n] for k in range(n)]
        chunks = [c for c in chunks if c]
        lock, done = threading.Lock(), [0]

        def tick():
            with lock:
                done[0] += 1
                d = done[0]
            if on_progress:
                try:
                    on_progress(d, total)
                except Exception:
                    pass

        results, errors = [0] * len(chunks), []

        def work(k):
            try:
                results[k] = _render_segment(src.resolve().as_uri(), chunks[k], ff, fps, str(Path(tmp) / f"part{k}.mp4"), tick)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=work, args=(k,), daemon=True) for k in range(len(chunks))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if errors:
            e = errors[0]
            raise e if isinstance(e, VideoError) else VideoError(f"영상을 만들지 못했습니다: {e}")
        lst = Path(tmp) / "list.txt"
        lst.write_text("".join(f"file 'part{k}.mp4'\n" for k in range(len(chunks))), encoding="utf-8")
        r = subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                            "-movflags", "+faststart", out_path], capture_output=True, cwd=tmp,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            raise VideoError(f"영상 조각을 합치지 못했습니다. ({r.stderr.decode('utf-8', 'ignore')[-200:]})")
    frames = sum(results)
    logger.info(f"영상 내보내기 완료: {frames}프레임 ({frames / fps:.1f}초, 동시 {len(chunks)}개) → {out_path}")
    return out_path
