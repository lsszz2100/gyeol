"""배포용 코드 묶음 만들기: packaging\\build_code 에 기계어 코드(*.pyd) + version.py + static + themes.json + 서명 파일.
원본 .py 는 넣지 않는다. build_installer.bat 과 make_release.py 가 호출."""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "build_code"
KEY = Path(__file__).resolve().parent / "signing_key.hex"   # 개인 서명 키(배포물에 넣지 않음)
_LOCAL_PY = HERE / "build_py.local.txt"   # Cython·setuptools가 설치된 빌드용 Python 3.12 경로 (저장소 밖)
BUILD_PY = Path(os.environ.get("GYEOL_BUILD_PY")
                or (_LOCAL_PY.read_text(encoding="utf-8").strip() if _LOCAL_PY.exists() else sys.executable))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))


def seed() -> bytes:
    from signing import check_key
    return check_key(KEY)


def compile_native():
    """코드를 기계어(.pyd)로 컴파일. 빌드용 환경(Cython + MSVC)에서 cy_build.py 실행."""
    py = BUILD_PY if BUILD_PY.exists() else Path(sys.executable)
    if subprocess.run([str(py), str(HERE / "cy_build.py"), str(OUT)]).returncode != 0:
        sys.exit("[오류] 코드 기계어 컴파일 실패")


def build() -> Path:
    from signing import sign
    s = seed()
    if not (ROOT / "core" / "server_local.py").exists():
        sys.exit("[오류] core/server_local.py(라이선스 서버 주소)가 없습니다")
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    compile_native()
    (OUT / "core").mkdir(exist_ok=True)
    shutil.copy(ROOT / "core" / "themes.json", OUT / "core" / "themes.json")
    shutil.copy(ROOT / "version.py", OUT / "version.py")
    shutil.copytree(ROOT / "static", OUT / "static", ignore=shutil.ignore_patterns("__pycache__"))
    files = {p.relative_to(OUT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(OUT.rglob("*")) if p.is_file()}
    data = json.dumps({"files": files}, ensure_ascii=False, indent=0, sort_keys=True).encode("utf-8")
    (OUT / "manifest.json").write_bytes(data)
    (OUT / "manifest.sig").write_text(sign(s, data).hex(), encoding="ascii")
    from core import sigcheck
    if not sigcheck.dir_ok(OUT):
        sys.exit("[오류] 코드 묶음 서명 확인 실패")
    return OUT


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    from version import APP_VERSION, REQUIRED_RUNTIME
    build()
    (HERE / "version.txt").write_text(APP_VERSION, encoding="ascii")
    (HERE / "runtime.txt").write_text(str(REQUIRED_RUNTIME), encoding="ascii")
    print(f"코드 묶음 완료: {OUT} (v{APP_VERSION})")
