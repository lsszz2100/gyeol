"""구독 로그인으로 쓰는 AI (core/cli_llm.py)
 - ChatGPT 구독: 공식 Codex CLI(`codex`), Claude 구독: 공식 Claude Code CLI(`claude`),
   Gemini 구글 계정: 공식 Gemini CLI(`gemini`, 결 전용 폴더)를 그대로 실행한다.
 - API 키를 받지 않는다. 사용자가 [로그인]을 누르면 각 CLI의 공식 로그인(`codex login`, `claude auth login`)이
   기본 브라우저(크롬 등)를 열고, 로그인이 끝나면 그 계정으로 바로 쓴다. 로그인 정보는 각 CLI가 관리한다(결은 보관하지 않음).
 - 글(HTML)만 만들게 한다: 작업 폴더는 빈 임시 폴더, Codex는 읽기 전용, Claude는 도구를 모두 끈다.
※ 판매판(edition=retail)에서는 쓰지 않는다 (app.py 가 막는다).
"""
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time

logger = logging.getLogger("kdesign.cli")

PROVIDERS = {
    "codex_cli": {"cmd": "codex", "label": "ChatGPT 구독 (Codex CLI)", "install": "npm install -g @openai/codex",
                  "site": "ChatGPT"},
    "claude_cli": {"cmd": "claude", "label": "Claude 구독 (Claude Code CLI)", "install": "npm install -g @anthropic-ai/claude-code",
                   "site": "Claude"},
    "gemini_cli": {"cmd": "gemini", "label": "Gemini 구글 계정 (Gemini CLI)", "install": "npm install -g @google/gemini-cli",
                   "site": "Google"},
}
# Gemini CLI는 사용자 폴더(USERPROFILE)\.gemini 에 설정·로그인을 둔다. 이 PC의 기존 Gemini CLI 설정(API 키 방식 등)을
# 바꾸지 않도록 결 전용 폴더를 사용자 폴더로 지정해 실행한다.
GEMINI_HOME = os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "Gyeol", "gemini_home")


def _gemini_env() -> dict:
    gdir = os.path.join(GEMINI_HOME, ".gemini")
    os.makedirs(gdir, exist_ok=True)
    sp = os.path.join(gdir, "settings.json")
    if not os.path.isfile(sp):
        import json as _json
        with open(sp, "w", encoding="utf-8") as f:
            _json.dump({"security": {"auth": {"selectedType": "oauth-personal"}},
                        "general": {"disableAutoUpdate": True}, "ui": {"theme": "Default"}}, f)
    env = dict(os.environ)
    env["USERPROFILE"] = GEMINI_HOME
    env["HOME"] = GEMINI_HOME
    env.pop("GEMINI_API_KEY", None)
    env.pop("GOOGLE_API_KEY", None)
    return env


def _gemini_account() -> str:
    """로그인돼 있으면 계정(메일) 또는 '로그인됨', 아니면 ''."""
    gdir = os.path.join(GEMINI_HOME, ".gemini")
    if not os.path.isfile(os.path.join(gdir, "oauth_creds.json")):
        return ""
    try:
        import json as _json
        with open(os.path.join(gdir, "google_accounts.json"), encoding="utf-8") as f:
            return _json.load(f).get("active") or "로그인됨"
    except Exception:
        return "로그인됨"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
RUN_TIMEOUT = 600
_login_procs = {}
_lock = threading.Lock()


class CliError(Exception):
    """사용자에게 그대로 보여 줄 오류."""


def _find(cmd: str) -> str:
    p = shutil.which(cmd)
    if p:
        return p
    for base in (os.path.join(os.environ.get("APPDATA", ""), "npm"), os.path.join(os.path.expanduser("~"), ".local", "bin"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "claude")):
        for ext in (".cmd", ".exe", ""):
            f = os.path.join(base, cmd + ext)
            if os.path.isfile(f):
                return f
    return ""


def _run(args: list, timeout: int = 30, input_text: str = None, cwd: str = None, env: dict = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, input=input_text, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, cwd=cwd or tempfile.gettempdir(), creationflags=NO_WINDOW, env=env)


def _info(provider: str) -> dict:
    if provider not in PROVIDERS:
        raise CliError("알 수 없는 AI 공급자입니다.")
    return PROVIDERS[provider]


def status(provider: str) -> dict:
    """{'installed', 'logged_in', 'label', 'install', 'detail'}"""
    info = _info(provider)
    out = {"installed": False, "logged_in": False, "label": info["label"], "install": info["install"], "detail": "",
           "logging_in": _is_logging_in(provider)}
    exe = _find(info["cmd"])
    if not exe:
        return out
    out["installed"] = True
    try:
        if provider == "gemini_cli":
            acct = _gemini_account()
            out["logged_in"] = bool(acct)
            out["detail"] = acct
        elif provider == "codex_cli":
            r = _run([exe, "login", "status"], 25)
            txt = ((r.stdout or "") + (r.stderr or "")).strip()
            out["logged_in"] = r.returncode == 0 and "logged in" in txt.lower()
            out["detail"] = txt.splitlines()[0][:80] if txt else ""
        else:
            r = _run([exe, "auth", "status"], 25)
            import json
            try:
                d = json.loads(r.stdout or "{}")
            except Exception:
                d = {}
            out["logged_in"] = bool(d.get("loggedIn"))
            out["detail"] = d.get("email") or d.get("authMethod") or ""
    except Exception as e:
        out["detail"] = f"확인 실패: {str(e)[:60]}"
    return out


def _is_logging_in(provider: str) -> bool:
    p = _login_procs.get(provider)
    return bool(p and p[0].poll() is None and time.time() - p[1] < 600)


def start_login(provider: str) -> dict:
    """공식 로그인 시작: 기본 브라우저가 열려 로그인 화면이 나온다. 끝나면 status 가 logged_in 이 된다."""
    info = _info(provider)
    exe = _find(info["cmd"])
    if not exe:
        raise CliError(f"{info['site']} 프로그램이 설치되어 있지 않습니다. 설치 후 다시 눌러 주세요. (설치: {info['install']})")
    with _lock:
        if _is_logging_in(provider):
            return {"ok": True, "message": "이미 로그인 창이 열려 있습니다. 브라우저에서 로그인을 마쳐 주세요."}
        if provider == "gemini_cli":
            # Gemini CLI는 로그인 명령이 없다 → 결 전용 폴더로 대화형 창을 띄우면 구글 로그인 창(브라우저)이 열린다.
            # 로그인을 마치면 그 창은 닫아도 된다(로그인 정보는 결 전용 폴더에 남음).
            proc = subprocess.Popen(["cmd.exe", "/c", "title Gemini 로그인 (결) - 로그인 후 이 창을 닫으세요 && " +
                                     subprocess.list2cmdline([exe])],
                                    cwd=GEMINI_HOME if os.path.isdir(GEMINI_HOME) else tempfile.gettempdir(),
                                    env=_gemini_env(), creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
        else:
            args = [exe, "login"] if provider == "codex_cli" else [exe, "auth", "login", "--claudeai"]
            proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    cwd=tempfile.gettempdir(), creationflags=NO_WINDOW)
        _login_procs[provider] = (proc, time.time())
    if provider == "gemini_cli":
        return {"ok": True, "message": "Gemini 창이 열립니다. 'Sign in with Google'(구글 로그인)을 고르면 브라우저가 열리고, "
                                       "로그인을 마치면 그 창을 닫아 주세요. 자동으로 연결됩니다."}
    return {"ok": True, "message": f"브라우저에서 {info['site']} 로그인 창이 열립니다. 로그인을 마치면 자동으로 연결됩니다."}


def complete(provider: str, prompt: str, model: str = "", timeout: int = RUN_TIMEOUT) -> str:
    """프롬프트를 보내고 답(글)을 돌려준다. 실패하면 CliError."""
    info = _info(provider)
    exe = _find(info["cmd"])
    if not exe:
        raise CliError(f"{info['site']} 프로그램이 설치되어 있지 않습니다. ⚙️ 설정에서 안내를 확인해 주세요. (설치: {info['install']})")
    tmp = tempfile.mkdtemp(prefix="gyeol_cli_")
    try:
        if provider == "codex_cli":
            outf = os.path.join(tmp, "answer.txt")
            args = [exe, "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "-s", "read-only",
                    "-C", tmp, "-o", outf, "-c", 'model_reasoning_effort="low"']
            if model:
                args += ["-m", model]
            args.append("-")
            r = _run(args, timeout, prompt, tmp)
            text = ""
            if os.path.isfile(outf):
                with open(outf, encoding="utf-8", errors="replace") as f:
                    text = f.read().strip()
            err = (r.stderr or "")
        elif provider == "gemini_cli":
            # 읽기 전용(plan) 모드·빈 임시 폴더에서 글만 받는다. 프롬프트는 stdin 으로
            args = [exe, "-p", " ", "-o", "text", "--approval-mode", "plan", "--skip-trust", "-e", "none"]
            if model:
                args += ["-m", model]
            r = _run(args, timeout, prompt, tmp, env=_gemini_env())
            text = (r.stdout or "").strip()
            err = (r.stderr or "")
        else:
            args = [exe, "-p", "--output-format", "text", "--no-session-persistence", "--tools", "",
                    "--strict-mcp-config", "--disable-slash-commands"]
            if model:
                args += ["--model", model]
            r = _run(args, timeout, prompt, tmp)
            text = (r.stdout or "").strip()
            err = (r.stderr or "")
    except subprocess.TimeoutExpired:
        raise CliError(f"{info['site']} 응답이 너무 오래 걸립니다. 잠시 뒤 다시 시도해 주세요.")
    except OSError as e:
        raise CliError(f"{info['site']} 프로그램을 실행하지 못했습니다: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if text and r.returncode == 0:
        return text
    low = (err + (r.stdout or "")).lower()
    if any(k in low for k in ("not logged in", "please run /login", "401", "unauthorized", "login required", "sign in", "auth")):
        raise CliError(f"{info['site']} 로그인이 필요하거나 만료되었습니다. ⚙️ 설정에서 [로그인]을 눌러 주세요.")
    if any(k in low for k in ("usage limit", "rate limit", "quota", "limit reached", "too many")):
        raise CliError(f"{info['site']} 구독의 사용 한도에 도달했습니다. 잠시 뒤 다시 시도해 주세요.")
    logger.warning(f"{provider} 실패 rc={r.returncode}: {err[-300:]}")
    raise CliError(f"{info['site']}에서 답을 받지 못했습니다. (코드 {r.returncode}) 다시 시도해 주세요.")


def generate_image(prompt: str, timeout: int = 360) -> bytes:
    """ChatGPT 구독(Codex CLI)의 이미지 생성 도구로 그림 한 장을 만들어 PNG 바이트로 돌려준다(1~2분)."""
    info = _info("codex_cli")
    exe = _find(info["cmd"])
    if not exe:
        raise CliError("ChatGPT(Codex) 프로그램이 설치되어 있지 않습니다.")
    tmp = tempfile.mkdtemp(prefix="gyeol_img_")
    try:
        ask = ("Use your image generation tool to create exactly one image and save it as image.png in the current "
               "directory. Landscape 3:2 (1536x1024). Do not create or modify any other files. Reply DONE when finished.\n\n"
               f"Image description: {prompt}")
        args = [exe, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "workspace-write", "-C", tmp, "-"]
        try:
            r = _run(args, timeout, ask, tmp)
        except subprocess.TimeoutExpired:
            raise CliError("ChatGPT 그림 생성이 너무 오래 걸립니다.")
        pngs = sorted((f for f in os.listdir(tmp) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))),
                      key=lambda f: os.path.getsize(os.path.join(tmp, f)), reverse=True)
        if pngs:
            with open(os.path.join(tmp, pngs[0]), "rb") as f:
                return f.read()
        low = ((r.stderr or "") + (r.stdout or "")).lower()
        if any(k in low for k in ("not logged in", "401", "unauthorized", "login")):
            raise CliError("ChatGPT 로그인이 필요하거나 만료되었습니다.")
        if any(k in low for k in ("usage limit", "rate limit", "quota", "limit reached")):
            raise CliError("ChatGPT 구독의 사용 한도에 도달했습니다.")
        raise CliError("ChatGPT에서 그림을 받지 못했습니다.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
