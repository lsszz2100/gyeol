"""서명 도구 (개발 PC 전용, 배포물에 넣지 않음). 검증 쪽은 core/sigcheck.py."""
import hashlib
import sys
from pathlib import Path

from core import ed25519 as e
from core import sigcheck


def _expand(seed: bytes):
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def _compress(P) -> bytes:
    zi = e._inv(P[2])
    x, y = P[0] * zi % e._p, P[1] * zi % e._p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def public_key(seed: bytes) -> bytes:
    return _compress(e._mul(_expand(seed)[0], e._G))


def sign(seed: bytes, msg: bytes) -> bytes:
    a, prefix = _expand(seed)
    A = _compress(e._mul(a, e._G))
    r = int.from_bytes(hashlib.sha512(prefix + msg).digest(), "little") % e._q
    Rs = _compress(e._mul(r, e._G))
    k = int.from_bytes(hashlib.sha512(Rs + A + msg).digest(), "little") % e._q
    return Rs + int.to_bytes((r + k * a) % e._q, 32, "little")


def sign_manifest(manifest: dict, seed: bytes) -> dict:
    return {**manifest, "sig": sign(seed, sigcheck.canonical(manifest)).hex()}


def check_key(path: Path) -> bytes:
    if not path.exists():
        sys.exit(f"[오류] 서명 키가 없습니다: {path} (이 키가 없으면 설치된 프로그램이 업데이트를 받지 못합니다)")
    seed = bytes.fromhex(path.read_text(encoding="ascii").strip())
    if public_key(seed).hex() != sigcheck.PUBLIC_KEY_HEX:
        sys.exit("[오류] 서명 키가 프로그램에 들어 있는 공개 키와 맞지 않습니다.")
    return seed
