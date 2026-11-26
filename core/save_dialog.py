"""저장 위치 선택 창 (pywebview 창이 있으면 그 대화상자, 없으면 tkinter)."""
import os
import threading

WINDOW = None          # desktop.py 가 pywebview 창을 만들면 여기에 넣는다
_lock = threading.Lock()


def ask_save_path(default_name: str, label: str, ext: str, initial_dir: str = ""):
    """사용자가 고른 저장 경로를 돌려준다. 취소하면 None."""
    test_dir = os.environ.get("GYEOL_TEST_SAVE_DIR")   # 자동 시험용: 창 없이 이 폴더에 저장
    if test_dir and os.path.isdir(test_dir):
        return os.path.join(test_dir, default_name)
    initial_dir = initial_dir if initial_dir and os.path.isdir(initial_dir) else os.path.join(os.path.expanduser("~"), "Documents")
    with _lock:
        if WINDOW is not None:
            try:
                import webview
                kind = getattr(getattr(webview, "FileDialog", None), "SAVE", None) or webview.SAVE_DIALOG
                res = WINDOW.create_file_dialog(kind, directory=initial_dir, save_filename=default_name,
                                                file_types=(f"{label} (*{ext})",))
                if not res:
                    return None
                path = res if isinstance(res, str) else res[0]
                return path if path.lower().endswith(ext) else path + ext
            except Exception:
                pass
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            path = filedialog.asksaveasfilename(parent=root, title="저장할 위치 선택", initialdir=initial_dir,
                                                initialfile=default_name, defaultextension=ext,
                                                filetypes=[(label, f"*{ext}"), ("모든 파일", "*.*")])
        finally:
            root.destroy()
        return path or None


def reveal_in_folder(path: str) -> None:
    import subprocess
    if os.name == "nt":
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(path)])
