"""외부 주소를 읽을 때의 안전장치 (SSRF 방지).

검색 결과·사용자가 넣은 이미지 주소처럼 '누가 정했는지 모르는' 주소는 이 PC 안(127.0.0.1)이나
같은 공유기 안의 기기(192.168.x.x, 10.x.x.x)로 향할 수 있다. 사설·루프백·링크로컬 주소와
http/https 가 아닌 주소는 막고, 중간에 다른 주소로 넘기는(redirect) 경우도 같은 검사를 한다.
"""
import ipaddress
import socket
import urllib.parse
import urllib.request


class BlockedURL(Exception):
    pass


def check_url(url: str) -> str:
    u = urllib.parse.urlparse(url or "")
    if u.scheme not in ("http", "https") or not u.hostname:
        raise BlockedURL("http/https 주소만 쓸 수 있습니다.")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError:
        raise BlockedURL("주소를 찾을 수 없습니다.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise BlockedURL("내부 네트워크 주소는 열 수 없습니다.")
    return url


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SafeRedirect)


def urlopen(req, timeout: float = 15):
    """urllib.request.urlopen 과 같지만 주소·리디렉션을 먼저 검사한다."""
    url = req.full_url if isinstance(req, urllib.request.Request) else req
    check_url(url)
    return _OPENER.open(req, timeout=timeout)
