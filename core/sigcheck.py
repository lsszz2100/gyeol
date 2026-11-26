"""업데이트 서명 확인: 개발자 키로 서명된 update.json·코드 묶음만 설치한다.
배포 저장소 계정이 털려도 서명 없는 가짜 업데이트는 설치되지 않는다.
개인 키는 packaging\\signing_key.hex (배포물에 넣지 않음)."""
import hashlib
import json
from pathlib import Path

from core import ed25519

PUBLIC_KEY_HEX = "568e930a87cf5af8e8e223fa8eb80c910e2b3cc91f7f8a3575b304a9f1ed95ce"
SKIP = {"manifest.json", "manifest.sig"}


def canonical(manifest: dict) -> bytes:
    body = {k: v for k, v in manifest.items() if k != "sig"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def verify_manifest(manifest: dict) -> bool:
    try:
        return isinstance(manifest, dict) and ed25519.verify(bytes.fromhex(PUBLIC_KEY_HEX), canonical(manifest),
                                                              bytes.fromhex(manifest.get("sig", "")))
    except Exception:
        return False


def file_list(d: Path) -> list:
    """코드 폴더 안 파일의 상대 경로 (서명 파일·캐시 제외)."""
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*")
                  if p.is_file() and p.name not in SKIP and "__pycache__" not in p.parts)


def dir_ok(d: Path) -> bool:
    """코드 폴더의 파일 목록과 지문이 서명과 정확히 같은지 (바뀐·빠진·모르는 파일 모두 거부)."""
    try:
        data = (d / "manifest.json").read_bytes()
        sig = bytes.fromhex((d / "manifest.sig").read_text(encoding="ascii").strip())
        if not ed25519.verify(bytes.fromhex(PUBLIC_KEY_HEX), data, sig):
            return False
        files = json.loads(data)["files"]
        return file_list(d) == sorted(files) and all(
            hashlib.sha256((d / n).read_bytes()).hexdigest() == h for n, h in files.items())
    except Exception:
        return False
