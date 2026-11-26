"""프로그램 코드를 Cython + MSVC 로 기계어(.pyd)로 컴파일 (make_code.py 가 빌드 환경 Python 으로 호출)."""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TMP = HERE / ".compile-tmp"


def main(out: Path):
    from Cython.Build import cythonize
    from Cython.Compiler import Options
    from setuptools import Extension
    from setuptools.dist import Distribution
    Options.docstrings = False
    Options.emit_code_comments = False
    shutil.rmtree(TMP, ignore_errors=True)
    src = TMP / "src"
    (src / "core").mkdir(parents=True)
    exts = []
    for m in ("app", "ai_engine", "config", "desktop"):
        shutil.copy2(ROOT / f"{m}.py", src / f"{m}.py")
        exts.append(Extension(m, [str(src / f"{m}.py")]))
    for p in sorted((ROOT / "core").glob("*.py")):
        shutil.copy2(p, src / "core" / p.name)
        exts.append(Extension(f"core.{p.stem}", [str(src / "core" / p.name)]))
    mods = cythonize(exts, quiet=True, nthreads=0, build_dir=str(TMP / "c"),
                     compiler_directives={"language_level": 3, "annotation_typing": False, "binding": True,
                                          "embedsignature": False, "always_allow_keywords": True})
    dist = Distribution({"name": "gyeol", "ext_modules": mods})
    cmd = dist.get_command_obj("build_ext")
    cmd.build_lib, cmd.build_temp, cmd.inplace = str(out), str(TMP / "obj"), False
    cmd.ensure_finalized()
    cmd.run()
    built = len(list(out.rglob("*.pyd")))
    if built != len(exts):
        sys.exit(f"[오류] 컴파일된 파일 수가 다릅니다: {built}/{len(exts)}")
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"  기계어 컴파일 완료: {built}개")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
