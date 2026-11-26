"""배포 전 자동 점검: 배포용 코드 묶음(build_code)으로 서버를 띄워 화면 스크립트 오류가 없는지 확인. 실패하면 배포 중단."""
import os
import sys
import threading
from pathlib import Path

CODE = str(Path(__file__).resolve().parent / "build_code")
sys.path.insert(0, CODE)
sys.dont_write_bytecode = True


def main():
    import app
    if not str(app.__file__).endswith(".pyd"):
        sys.exit(f"  ❌ 배포 코드가 아니라 원본을 불러왔습니다: {app.__file__}")
    app.LICENSE_BYPASS = True   # 시험 프로세스 안에서만 (환경 변수로는 켜지지 않는다)
    import desktop
    port = desktop.pick_port(0)
    app.set_allowed_port(port)
    srv = app.ThreadedHTTPServer(("127.0.0.1", port), app.KDesignHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, channel="msedge")
        p = b.new_page()
        p.on("pageerror", lambda e: errors.append(f"스크립트 오류: {e}"))
        p.goto(f"http://127.0.0.1:{port}/?k={app.API_TOKEN}", wait_until="domcontentloaded")
        p.wait_for_timeout(2500)
        for sel in ("#update-bar", "#btn-license"):
            if not p.locator(sel).count():
                errors.append(f"화면 요소 없음: {sel}")
        st = p.evaluate("fetch('/api/update/status').then(r=>r.json())")
        from version import APP_VERSION
        if st.get("current") != APP_VERSION:
            errors.append(f"버전 이상: {st.get('current')}")
        b.close()
    srv.shutdown()
    if errors:
        print("  ❌ 점검 실패:\n   - " + "\n   - ".join(errors))
        sys.exit(1)
    print("  ✔ 대시보드 점검 통과")


if __name__ == "__main__":
    main()
