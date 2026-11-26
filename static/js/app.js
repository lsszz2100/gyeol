/**
 * 결(GYEOL) - 편집 화면 스크립트
 * 왼쪽 슬라이드 목록 · 가운데 미리보기/조작/대본 · 오른쪽 테마 갤러리 · 하단 AI 생성
 */
document.addEventListener("DOMContentLoaded", () => {
  const $ = (id) => document.getElementById(id);

  const state = {
    project: null,
    themes: [],
    fonts: [],
    slides: [],
    idx: 0,
    presetId: "pitch-deck",
    styleFilter: "all",
    tone: "all",
    search: "",
    opts: {},
  };

  const frame = $("preview-frame");
  const deck = () => { try { return frame.contentWindow.__deck || null; } catch (e) { return null; } };

  // ───────────────── 공통 ─────────────────
  let toastTimer;
  function toast(msg, isErr, action) {
    const t = $("toast");
    t.textContent = msg;
    if (action) {
      const b = document.createElement("button");
      b.textContent = action.label;
      b.onclick = action.run;
      t.appendChild(b);
    }
    t.classList.toggle("err", !!isErr);
    t.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("on"), isErr ? 6000 : action ? 8000 : 3000);
  }
  async function api(path, body) {
    const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
    const res = await fetch(path, opt);
    const data = await res.json();
    if (res.status === 403 && data && data.license_required) {
      showLicense(data, true);   // 호출한 곳은 ok:false + message 로 안내만 띄움
    }
    return data;
  }

  // ───────────────── 첫 실행 안내 ─────────────────
  const WELCOME_EXAMPLES = [
    ["📊 업무 보고", "business-proposal", "2026년 우리 팀 하반기 성과와 내년 계획 보고"],
    ["🎓 교육 자료", "tech-sharing", "직장인을 위한 생성형 AI 활용법 입문 교육"],
    ["🚀 제안서", "pitch-deck", "소상공인을 위한 예약 관리 앱 서비스 제안"],
  ];
  let welcomeChecked = false;
  function renderWelcomeExamples() {
  $("welcome-examples").innerHTML = WELCOME_EXAMPLES.map((x, i) =>
    `<button class="btn" data-ex="${i}" style="text-align:left;padding:10px 12px"><b>${esc(x[0])}</b> &nbsp;${esc(x[2])}</button>`).join("");
  $("welcome-examples").querySelectorAll("[data-ex]").forEach((b) => b.onclick = () => {
    const x = WELCOME_EXAMPLES[+b.dataset.ex];
    $("welcome-modal").classList.remove("open");
    state.presetId = x[1];
    $("prompt-input").value = x[2];
    generate();
  });
  }
  function closeWelcome() {
    $("welcome-modal").classList.remove("open");
    api("/api/config", { welcome_done: true });
  }
  async function maybeWelcome() {
    if (welcomeChecked) return;
    if (!lic || (!lic.usable && !lic.dev_bypass)) return;   // 라이선스를 넣은 뒤에 다시 호출됨
    welcomeChecked = true;
    const c = (await api("/api/config")).config || {};
    if (c.welcome_done || c.gemini_api_key || c.provider !== "gemini") return;
    renderWelcomeExamples();
    $("welcome-modal").classList.add("open");
  }
  function welcomeMsg(text, ok) {
    const m = $("welcome-msg");
    m.textContent = text; m.style.color = ok ? "#16a34a" : "#dc2626";
  }
  $("welcome-open").onclick = () => api("/api/open_key_page", {});
  $("welcome-skip").onclick = closeWelcome;
  $("welcome-test").onclick = async () => {
    const key = $("welcome-key").value.trim();
    if (!key) { welcomeMsg("키를 붙여 넣어 주세요."); $("welcome-key").focus(); return; }
    const b = $("welcome-test");
    b.disabled = true; welcomeMsg("확인하는 중…", true);
    try {
      const r = await api("/api/test_key", { key });
      if (!r.ok) { welcomeMsg(r.message); return; }
      await api("/api/config", { gemini_api_key: key, provider: "gemini", welcome_done: true });
      $("welcome-step1").style.display = "none";
      $("welcome-step2").style.display = "";
    } catch (e) { welcomeMsg("연결을 확인하지 못했습니다. 다시 시도해 주세요."); }
    finally { b.disabled = false; }
  };
  $("welcome-key").addEventListener("keydown", (e) => { if (e.key === "Enter") $("welcome-test").click(); });
  $("welcome-src").onclick = () => { $("welcome-modal").classList.remove("open"); $("src-file").click(); };
  $("welcome-own").onclick = () => { $("welcome-modal").classList.remove("open"); $("prompt-input").focus(); };

  // ───────────────── 종료 확인 (X 버튼) ─────────────────
  // 작업이 없으면 "종료할까요?", 작업 중이면 진행 내용을 보여 주고 '끝나면 자동 종료'를 고를 수 있다
  let autoQuitTimer = 0;
  function renderAutoQuit(on, items) {
    const bar = $("autoquit-bar");
    bar.style.display = on ? "flex" : "none";
    if (on) $("autoquit-text").textContent = items && items.length ? `작업이 끝나면 자동으로 종료합니다 — ${items.join(" · ")}` : "작업이 끝나 곧 종료합니다";
    clearTimeout(autoQuitTimer);
    if (on) autoQuitTimer = setTimeout(pollAutoQuit, 2000);
  }
  async function pollAutoQuit() {
    try { const r = await api("/api/busy"); if (r) renderAutoQuit(!!r.auto_quit, r.items); } catch (e) { autoQuitTimer = setTimeout(pollAutoQuit, 3000); }
  }
  window.openCloseDialog = async () => {
    let st = { busy: false, items: [], auto_quit: false };
    try { st = (await api("/api/busy")) || st; } catch (e) {}
    const busy = !!st.busy;
    $("close-title").textContent = busy ? "작업이 진행 중입니다" : "결을 종료할까요?";
    $("close-text").textContent = st.auto_quit ? "이미 '작업이 끝나면 자동 종료'로 예약되어 있습니다."
      : busy ? `${(st.items || []).join(" · ") || "작업"}입니다. 끝날 때까지 기다렸다가 자동으로 종료할 수 있습니다.`
      : "만들던 내용은 저장되어 있습니다.";
    $("close-idle").style.display = busy && !st.auto_quit ? "" : "none";
    $("close-tray").style.display = busy ? "" : "none";
    $("close-now").textContent = busy ? "바로 종료 (진행 중인 작업 중단)" : "종료";
    $("close-now").style.color = busy ? "#dc2626" : "";
    $("close-remember-row").style.display = busy ? "none" : "flex";
    $("close-remember").checked = false;
    $("close-modal").classList.add("open");
  };
  $("close-cancel").onclick = () => $("close-modal").classList.remove("open");
  $("close-now").onclick = () => api("/api/app/close", { mode: "quit", remember: $("close-remember").checked });
  $("close-idle").onclick = async () => {
    $("close-modal").classList.remove("open");
    const r = await api("/api/app/close", { mode: "when_idle" });
    if (r && r.ok) { renderAutoQuit(true, []); pollAutoQuit(); toast("작업이 끝나면 자동으로 종료합니다. 창은 그대로 두셔도 됩니다."); }
  };
  $("autoquit-cancel").onclick = async () => { await api("/api/app/close", { mode: "cancel_auto" }); renderAutoQuit(false); toast("자동 종료를 취소했습니다."); };
  $("close-tray").onclick = async () => {
    $("close-modal").classList.remove("open");
    const r = await api("/api/app/close", { mode: "tray" });
    if (r.ok === false) toast(r.message || "트레이로 내리지 못했습니다.", true);
  };

  // ───────────────── 업데이트 ─────────────────
  let updateHidden = "";
  function renderUpdate(s) {
    const bar = $("update-bar"), title = $("update-title"), text = $("update-text");
    const go = $("update-go"), later = $("update-later");
    $("app-version").textContent = `버전 ${s.current}`;
    const show = (t, d, canGo, canLater) => {
      title.textContent = t; text.textContent = d; text.title = d;
      go.style.display = canGo ? "" : "none"; later.style.display = canLater ? "" : "none";
      bar.style.display = "flex";
    };
    const ju = s.just_updated;
    if (ju) {
      show(ju.ok ? `✅ v${ju.to}으로 업데이트되었습니다` : "⚠️ 업데이트가 완료되지 않았습니다", (ju.notes || "").replace(/\n+/g, " · "), false, true);
      later.textContent = "확인";
      later.onclick = async () => { renderUpdate(await api("/api/update/ack", {})); later.textContent = "나중에"; };
    } else if (s.state === "error") {
      show("⚠️ 업데이트 실패", s.error, true, true);
    } else if (s.state === "downloading") {
      show("업데이트 받는 중", `${s.progress}% (${s.downloaded_mb}/${s.total_mb}MB)`, false, false);
    } else if (s.state === "verifying" || s.state === "installing") {
      show("업데이트 적용 중", "프로그램이 잠시 닫혔다가 자동으로 다시 시작됩니다.", false, false);
      if (s.state === "installing") setTimeout(() => window.close(), 2500);   // 브라우저 창으로 연 경우에도 닫힌다
    } else if (s.available && s.can_install && updateHidden !== s.latest) {
      show(`새 버전 v${s.latest}`, (s.notes || "").replace(/\n+/g, " · "), true, true);
      later.onclick = () => { updateHidden = s.latest; $("update-bar").style.display = "none"; };
    } else if (s.available && !s.can_install && updateHidden !== s.latest) {
      // 소스로 직접 실행 중이면 자동 설치는 못 하지만, 새 버전이 나온 것은 알려 준다
      show(`새 버전 v${s.latest} 배포됨`, "소스로 실행 중이라 자동 설치는 하지 않습니다. 프로그램을 다시 실행하면 폴더의 최신 코드가 적용됩니다.", false, true);
      later.onclick = () => { updateHidden = s.latest; $("update-bar").style.display = "none"; };
    } else {
      bar.style.display = "none";
    }
    return s;
  }
  async function pollUpdate(fresh) {
    try {
      const s = renderUpdate(await api("/api/update/status" + (fresh === true ? "?fresh=1" : "")));
      setTimeout(pollUpdate, ["downloading", "verifying", "installing"].includes(s.state) ? 1000 : 30000);
    } catch (e) { setTimeout(pollUpdate, 30000); }
  }
  // 창을 다시 보거나 앞으로 가져오면 바로 새 버전을 확인한다 (기다리지 않고 알림)
  let focusPoll = 0;
  const focusCheck = () => { if (document.visibilityState === "hidden" || Date.now() - focusPoll < 15000) return; focusPoll = Date.now(); api("/api/update/status?fresh=1").then(renderUpdate).catch(() => {}); };
  window.addEventListener("focus", focusCheck);
  document.addEventListener("visibilitychange", focusCheck);
  $("update-go").onclick = async () => {
    if (!confirm("업데이트를 받으면 프로그램이 잠시 닫혔다가 자동으로 다시 시작됩니다.\n만들던 내용은 저장되어 있습니다. 진행할까요?")) return;
    const r = await api("/api/update/install", {});
    if (r.ok === false) { alert(r.message); return; }
    renderUpdate(r);
    setTimeout(pollUpdate, 800);
  };
  setTimeout(pollUpdate, 500);
  setTimeout(pollAutoQuit, 1200);   // 새로고침해도 '자동 종료 예약' 표시를 이어 보여 준다

  // ───────────────── 라이선스 ─────────────────
  let lic = null;
  function fmtDate(ts) { const d = new Date(ts * 1000); return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`; }
  function renderLicense(st) {
    lic = st || {};
    const L = lic.license || {};
    const chip = $("lic-chip");
    if (lic.dev_bypass && !lic.has_key) chip.textContent = "개발 실행";
    else if (!lic.usable) chip.textContent = "키 입력 필요";
    else {
      const tk = L.unlimited ? "무제한" : `${Number(L.tokens_left || 0).toLocaleString()} 토큰`;
      chip.textContent = L.expires_at ? `${tk} · ${lic.days_left}일` : tk;
    }
    $("btn-license").classList.toggle("on", !lic.usable && !lic.dev_bypass);
    let html;
    if (lic.usable && lic.has_key) {
      html = `<b style="color:#16a34a">✓ 사용 중</b> · 키 ${esc(lic.key_hint)}<br>` +
        (L.expires_at ? `사용 기한: <b>${fmtDate(L.expires_at)}</b>까지 (남은 ${lic.days_left}일)` : `사용 기한: <b>무기한</b>`);
    } else if (lic.has_key && L.expired) {
      html = `<b style="color:#dc2626">사용 기간이 끝났습니다.</b><br>연장하시려면 구매처로 문의해 주세요. 새 키를 받으셨다면 아래에 넣어 주세요.`;
    } else if (lic.has_key && L.status === "revoked") {
      html = `<b style="color:#dc2626">사용이 중지된 라이선스입니다.</b><br>구매처로 문의해 주세요.`;
    } else if (lic.has_key) {
      html = `<b>라이선스를 확인하지 못했습니다.</b><br>인터넷 연결을 확인한 뒤 다시 확인을 눌러 주세요.`;
    } else {
      html = `결(GYEOL)을 사용하려면 <b>라이선스 키</b>가 필요합니다.<br>키를 넣기 전에도 화면은 둘러보실 수 있지만, 만들기·편집·내보내기는 키 확인 후에 됩니다.`;
    }
    if (lic.error && !(lic.usable && lic.has_key)) html += `<div style="margin-top:6px;color:#b45309">${esc(lic.error)}</div>`;
    $("lic-status").innerHTML = html;
    $("btn-lic-logout").style.display = lic.has_key ? "" : "none";
    $("btn-lic-activate").textContent = lic.has_key && !lic.usable ? "다시 확인" : "확인";
    $("lic-input-wrap").querySelector("label").textContent = lic.usable && lic.has_key ? "다른 키로 바꾸기 (선택)" : "라이선스 키 (16자리)";
  }
  // 라이선스가 없으면 입력 창을 닫을 수 없고 뒤 화면도 보이지 않게 가린다
  function lockScreen() {
    const locked = !(lic && (lic.usable || lic.dev_bypass));
    const m = $("license-modal");
    m.style.background = locked ? "#14112a" : "";
    $("btn-close-license").style.display = locked ? "none" : "";
    if (locked) m.classList.add("open");
    return locked;
  }
  function showLicense(st, blocked) {
    if (st) renderLicense(st);
    lockScreen();
    $("lic-msg").style.display = "none";
    if (blocked) { $("lic-msg").textContent = "라이선스 키를 확인한 뒤에 사용할 수 있습니다."; $("lic-msg").style.display = ""; }
    $("license-modal").classList.add("open");
    setTimeout(() => $("lic-key").focus(), 50);
  }
  async function loadLicense() {
    try { renderLicense(await (await fetch("/api/license")).json()); } catch (e) { /* 다음 확인 때 다시 */ }
    return lic;
  }
  const esc = (s) => String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ───────────────── 슬라이드 파싱 / 목록 ─────────────────
  function parseSlides(html) {
    const doc = new DOMParser().parseFromString(`<div>${html || ""}</div>`, "text/html");
    return Array.from(doc.querySelectorAll("section.slide, .slide")).map((s, i) => {
      const note = s.querySelector("aside.notes, .notes, .speaker-notes");
      const h = s.querySelector("h1, h2, h3");
      return {
        title: s.getAttribute("data-title") || (h ? h.textContent.trim() : `슬라이드 ${i + 1}`),
        notes: note ? note.innerHTML.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/[ \t]+/g, " ").replace(/ *\n */g, "\n").trim() : "",
      };
    });
  }

  let dragFrom = -1;
  function renderSlideList() {
    const list = $("slide-list");
    const stamp = Date.now();
    list.innerHTML = "";
    state.slides.forEach((s, i) => {
      const item = document.createElement("div");
      item.className = "thumb-item" + (i === state.idx ? " active" : "");
      item.innerHTML = `<div class="thumb-num">${i + 1}</div>
        <div class="thumb-box"><iframe tabindex="-1" data-src="/preview?preview=${i + 1}&thumb=1&t=${stamp}"></iframe>
        <div class="thumb-cap">${esc(s.title)}</div>
        <div class="thumb-acts">
          <button data-a="up" title="위로">↑</button><button data-a="down" title="아래로">↓</button>
          <button data-a="dup" title="복제">⧉</button><button data-a="del" class="del" title="삭제">✕</button>
        </div></div>`;
      item.addEventListener("click", (e) => {
        const b = e.target.closest("[data-a]");
        if (!b) { goTo(i); return; }
        e.stopPropagation();
        const a = b.dataset.a;
        if (a === "up" && i > 0) slideOp("move", { idx: i, to: i - 1 });
        else if (a === "down" && i < state.slides.length - 1) slideOp("move", { idx: i, to: i + 1 });
        else if (a === "dup") slideOp("duplicate", { idx: i });
        else if (a === "del") slideOp("delete", { idx: i }, `${i + 1}번 슬라이드를 삭제했습니다.`);
      });
      item.draggable = true;
      item.addEventListener("dragstart", (e) => { dragFrom = i; item.classList.add("drag"); e.dataTransfer.effectAllowed = "move"; });
      item.addEventListener("dragend", () => { dragFrom = -1; document.querySelectorAll(".thumb-item").forEach((x) => x.classList.remove("drag", "drop-before", "drop-after")); });
      item.addEventListener("dragover", (e) => {
        if (dragFrom < 0) return;
        e.preventDefault();
        const r = item.getBoundingClientRect(), after = e.clientY > r.top + r.height / 2;
        document.querySelectorAll(".thumb-item").forEach((x) => x.classList.remove("drop-before", "drop-after"));
        item.classList.add(after ? "drop-after" : "drop-before");
      });
      item.addEventListener("drop", (e) => {
        e.preventDefault();
        if (dragFrom < 0) return;
        const r = item.getBoundingClientRect(), after = e.clientY > r.top + r.height / 2;
        let to = i + (after ? 1 : 0);
        if (dragFrom < to) to -= 1;
        const from = dragFrom;
        dragFrom = -1;
        if (to !== from) slideOp("move", { idx: from, to });
      });
      list.appendChild(item);
    });
    $("slide-total").textContent = `${state.slides.length}장`;
    requestAnimationFrame(scaleSlideThumbs);
    // 썸네일은 같은 화면 스레드를 함께 쓰므로 한꺼번에 띄우면 본 화면까지 느려진다.
    // 지금 보는 슬라이드 가까운 것부터 2개씩 차례로 불러온다.
    const frames = [...list.querySelectorAll("iframe[data-src]")];
    const order = frames.map((f, i) => [Math.abs(i - state.idx), f]).sort((a, b) => a[0] - b[0]).map((x) => x[1]);
    frameQueue.reset("slides", order);
  }

  // iframe 미리보기를 정해진 개수씩 차례로 불러오는 대기열 (슬라이드 목록·테마 창 공용)
  const frameQueue = (() => {
    const lanes = {};
    function pump(name) {
      const ln = lanes[name];
      while (ln.active < ln.limit && ln.items.length) {
        const f = ln.items.shift();
        if (!f.isConnected || !f.dataset.src) continue;
        ln.active++;
        let done = false;
        const fin = () => { if (done) return; done = true; ln.active--; pump(name); };
        f.addEventListener("load", fin, { once: true });
        f.addEventListener("error", fin, { once: true });
        setTimeout(fin, 4000);   // 멈춘 미리보기가 줄 전체를 막지 않게
        f.src = f.dataset.src;
        delete f.dataset.src;
      }
    }
    return {
      reset(name, items, limit = 2) { lanes[name] = { items: items.slice(), active: 0, limit }; pump(name); },
      add(name, f, limit = 3) { if (!lanes[name]) lanes[name] = { items: [], active: 0, limit }; lanes[name].items.push(f); pump(name); },
    };
  })();
  function scaleSlideThumbs() {
    document.querySelectorAll(".thumb-box").forEach((box) => {
      const f = box.querySelector("iframe");
      if (f) f.style.transform = `scale(${box.clientWidth / 1280})`;
    });
  }
  window.addEventListener("resize", () => { scaleSlideThumbs(); scaleThemeThumbs(); });

  function markActive() {
    document.querySelectorAll(".thumb-item").forEach((el, i) => el.classList.toggle("active", i === state.idx));
    const active = document.querySelectorAll(".thumb-item")[state.idx];
    if (active) active.scrollIntoView({ block: "nearest", behavior: "smooth" });
    $("slide-count").textContent = `${state.slides.length ? state.idx + 1 : 0} / ${state.slides.length}`;
    const s = state.slides[state.idx];
    $("notes-title").textContent = s ? `발표자 대본 · ${state.idx + 1}. ${s.title}` : "발표자 대본";
    $("notes-text").textContent = s && s.notes ? s.notes : "";
    if ($("ai-pop").classList.contains("open")) updateAiTarget();
  }

  // 미리보기 iframe이 슬라이드를 넘기면 알려줌
  window.addEventListener("message", (e) => {
    if (e.data && e.data.type === "deck-go" && e.source === frame.contentWindow) {
      state.idx = e.data.idx;
      markActive();
    }
  });

  function goTo(i) {
    if (editing) { finishEdit(true); }
    i = Math.max(0, Math.min(state.slides.length - 1, i));
    state.idx = i;
    const d = deck();
    if (d) d.go(i);
    markActive();
    if ($("ai-pop").classList.contains("open") && typeof updateAiTarget === "function") updateAiTarget();   // 열려 있는 AI 창이 이 슬라이드의 대화를 보이게
  }

  function reloadPreview(keepIdx = true) {
    const n = keepIdx ? state.idx + 1 : 1;
    if (!keepIdx) state.idx = 0;
    frame.src = `/preview?t=${Date.now()}#/${n}`;
  }

  function applyProject(p, keepIdx = false) {
    if (editing) stopEditUi();
    state.project = p;
    $("project-title").value = p.title || "";
    state.slides = parseSlides(p.slides_html);
    if (!keepIdx || state.idx >= state.slides.length) state.idx = 0;
    $("font-select").value = p.font || "theme";
    reloadPreview(true);
    renderSlideList();
    markActive();
    markActiveTheme();
  }

  // ───────────────── 조작 버튼 ─────────────────
  $("btn-prev").onclick = () => goTo(state.idx - 1);
  $("btn-next").onclick = () => goTo(state.idx + 1);
  $("btn-notes").onclick = () => {
    const open = $("notes-pane").classList.toggle("open");
    $("btn-notes").classList.toggle("on", open);
  };
  $("btn-overview").onclick = () => { const d = deck(); if (d) d.toggleOverview(); frame.focus(); };
  $("btn-fullscreen").onclick = () => fullscreenStage();
  $("btn-present").onclick = () => { goTo(0); fullscreenStage(); };
  $("btn-presenter").onclick = () => {
    const d = deck();
    if (!d) return;
    const w = window.open("", "gyeol-presenter", "width=1280,height=820,menubar=no,toolbar=no");
    if (!w) { toast("발표자 창을 열 수 없습니다. 팝업 차단을 해제해 주세요.", true); return; }
    d.openPresenter(w);
  };
  function fullscreenStage() {
    const el = document.querySelector(".slide-stage");
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req) req.call(el).then(() => frame.focus()).catch(() => { const d = deck(); if (d) d.fullscreen(); });
  }

  document.addEventListener("keydown", (e) => {
    const tag = (document.activeElement && document.activeElement.tagName) || "";
    const inField = /INPUT|TEXTAREA|SELECT/.test(tag) || (document.activeElement && document.activeElement.isContentEditable);
    if (!inField && (e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === "z" || e.key === "Z")) { e.preventDefault(); undo(); return; }
    if (e.key === "Escape") { $("ai-pop").classList.remove("open"); $("media-modal").classList.remove("open"); }
    // 편집 중 선택한 그림·도형: 키보드 초점이 바깥 화면에 있어도 삭제·이동되게
    if (editing && editing.sel && !inField) {
      if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); objAction("del"); return; }
      if (e.key === "Escape") { editing.select(null); return; }
      if (e.key.startsWith("Arrow") && editing.sel.classList.contains("g-obj")) {
        e.preventDefault();
        const o = editing.sel, d = e.shiftKey ? 10 : 1, n = (v) => parseFloat(v) || 0;
        if (e.key === "ArrowLeft") o.style.left = n(o.style.left) - d + "px";
        if (e.key === "ArrowRight") o.style.left = n(o.style.left) + d + "px";
        if (e.key === "ArrowUp") o.style.top = n(o.style.top) - d + "px";
        if (e.key === "ArrowDown") o.style.top = n(o.style.top) + d + "px";
        return;
      }
    }
    if (inField || editing || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "e" || e.key === "E") { startEdit(); e.preventDefault(); return; }
    if (e.key === "ArrowRight" || e.key === "PageDown") { goTo(state.idx + 1); e.preventDefault(); }
    else if (e.key === "ArrowLeft" || e.key === "PageUp") { goTo(state.idx - 1); e.preventDefault(); }
    else if (e.key === "Home") goTo(0);
    else if (e.key === "End") goTo(state.slides.length - 1);
    else if (e.key === "o" || e.key === "O") $("btn-overview").click();
    else if (e.key === "s" || e.key === "S") $("btn-presenter").click();
    else if (e.key === "f" || e.key === "F") fullscreenStage();
  });

  // 제목 수정
  $("project-title").addEventListener("change", () => updateStyle({ title: $("project-title").value.trim() }));

  // ───────────────── 분위기 ↔ 테마 연결 ─────────────────
  // 분위기를 고르면 어울리는 스타일의 테마를 추천한다. 분위기가 '자동'이면 고른 테마의 스타일을 따라간다(생성할 때 서버가 정함)
  function moodOfStyle(style) {
    for (const [m, sts] of Object.entries(state.moodStyles || {})) if (sts.includes(style)) return m;
    return "";
  }
  function suggestThemeForMood() {
    const m = state.opts.mood;
    if (!m || m === "auto") return;
    const styles = (state.moodStyles || {})[m] || [];
    const cur = state.themes.find((t) => t.id === (state.project && state.project.theme));
    if (!styles.length || (cur && styles.includes(cur.style))) return;   // 이미 어울리는 테마
    const pool = state.themes.filter((t) => styles.includes(t.style));
    const pick = pool.find((t) => !cur || !!t.dark === !!cur.dark) || pool[0];   // 지금 테마와 밝기가 같은 것을 우선
    if (!pick) return;
    toast(`'${MOOD_LABEL[m]}' 분위기에는 ${pick.name}(${pick.style_label}) 같은 테마가 어울립니다.`, false,
      { label: "이 테마로 바꾸기", run: () => updateStyle({ theme: pick.id }) });
  }

  // ───────────────── 테마 갤러리 ─────────────────
  function renderStyleChips() {
    const styles = [];
    state.themes.forEach((t) => { if (!styles.find((s) => s.id === t.style)) styles.push({ id: t.style, label: t.style_label, desc: t.style_desc }); });
    const box = $("style-chips");
    box.innerHTML = "";
    [{ id: "all", label: `전체 ${state.themes.length}`, desc: "" }, ...styles].forEach((s) => {
      const c = document.createElement("span");
      c.className = "chip" + (state.styleFilter === s.id ? " on" : "");
      c.textContent = s.label;
      c.onclick = () => {
        state.styleFilter = s.id;
        const mm = moodOfStyle(s.id);
        $("style-desc").textContent = s.desc ? `${s.label} — ${s.desc}${mm ? ` · 어울리는 분위기: ${MOOD_LABEL[mm]}` : ""}` : "";
        renderStyleChips();
        renderThemeGrid();
      };
      box.appendChild(c);
    });
  }

  const thumbObserver = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (!en.isIntersecting) return;
      const box = en.target;
      if (!box.querySelector("iframe")) {
        const f = document.createElement("iframe");
        f.tabIndex = -1;
        f.dataset.src = `/theme_preview?theme=${encodeURIComponent(box.dataset.theme)}&font=${encodeURIComponent($("font-select").value || "theme")}`;
        f.style.transform = `scale(${box.clientWidth / 1280})`;
        f.onload = () => { box.querySelector(".sw") && box.querySelector(".sw").remove(); };
        box.appendChild(f);
        frameQueue.add("themes", f, 3);
      }
      thumbObserver.unobserve(box);
    });
  }, { root: null, rootMargin: "200px" });

  function scaleThemeThumbs() {
    document.querySelectorAll(".t-thumb iframe").forEach((f) => { f.style.transform = `scale(${f.parentElement.clientWidth / 1280})`; });
  }

  function filteredThemes() {
    const q = state.search.trim().toLowerCase();
    return state.themes.filter((t) =>
      (state.styleFilter === "all" || t.style === state.styleFilter) &&
      (state.tone === "all" || (state.tone === "dark") === !!t.dark) &&
      (!q || `${t.name} ${t.style_label} ${t.category}`.toLowerCase().includes(q)));
  }

  function renderThemeGrid() {
    const grid = $("theme-grid");
    const list = filteredThemes();
    grid.innerHTML = list.length ? "" : `<div class="empty">조건에 맞는 테마가 없습니다.</div>`;
    list.forEach((t) => {
      const card = document.createElement("div");
      card.className = "t-card";
      card.dataset.theme = t.id;
      card.innerHTML = `<div class="t-thumb" data-theme="${esc(t.id)}" style="--tb:${esc(t.bg)}">
          <div class="sw"><i style="background:${esc(t.accent)}"></i><i style="background:${esc(t.accent2)}"></i><i style="background:${esc(t.text)}"></i></div>
        </div>
        <div class="t-name">${esc(t.name)}</div><div class="t-style">${esc(t.style_label)}</div>`;
      card.onclick = () => updateStyle({ theme: t.id });
      grid.appendChild(card);
      thumbObserver.observe(card.querySelector(".t-thumb"));
    });
    $("theme-total").textContent = `${list.length}종`;
    markActiveTheme();
  }

  function markActiveTheme() {
    const cur = state.project && state.project.theme;
    document.querySelectorAll(".t-card").forEach((c) => c.classList.toggle("active", c.dataset.theme === cur));
  }

  $("theme-search").addEventListener("input", (e) => { state.search = e.target.value; renderThemeGrid(); });
  document.querySelectorAll("#tone-seg button").forEach((b) => b.onclick = () => {
    state.tone = b.dataset.tone;
    document.querySelectorAll("#tone-seg button").forEach((x) => x.classList.toggle("on", x === b));
    renderThemeGrid();
  });
  $("font-select").addEventListener("change", () => { updateStyle({ font: $("font-select").value }); renderThemeGrid(); });

  function toggleThemes(force) {
    const open = $("theme-panel").classList.toggle("open", force);
    $("btn-themes").classList.toggle("on", open);
    if (open && !$("theme-grid").children.length) renderThemeGrid();
    setTimeout(() => { scaleSlideThumbs(); scaleThemeThumbs(); }, 300);
  }
  $("btn-themes").onclick = () => toggleThemes();
  $("btn-close-themes").onclick = () => toggleThemes(false);

  async function updateStyle(patch) {
    const res = await api("/api/update_style", patch);
    if (!res.ok && res.message) toast(res.message, true);
    if (res.ok) {
      applyProject(res.project, true);
      if (patch.theme) {
        const t = state.themes.find((x) => x.id === patch.theme);
        if (t) toast(`테마 적용: ${t.name} · ${t.style_label}`);
      }
    }
  }

  // ───────────────── AI 생성 ─────────────────
  document.querySelectorAll(".dock .chip").forEach((chip) => chip.onclick = () => {
    $("prompt-input").value = chip.dataset.prompt;
    state.presetId = chip.dataset.preset || "pitch-deck";
    autoGrow();
    $("prompt-input").focus();
  });
  const autoGrow = () => { const p = $("prompt-input"); p.style.height = "auto"; p.style.height = Math.min(p.scrollHeight, 90) + "px"; };
  $("prompt-input").addEventListener("input", autoGrow);
  $("prompt-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); generate(); }
  });
  $("btn-generate").onclick = generate;

  function setStep(id, cls) { const el = $(id); el.classList.remove("run", "done"); if (cls) el.classList.add(cls); }

  // ───────────────── 내 자료로 만들기 ─────────────────
  let sourceFiles = [];   // [{name, text, chars, truncated}] 글자만 보관, 파일은 저장하지 않음
  let sourceResearch = false;
  function renderSources() {
    const box = $("src-list");
    box.style.display = sourceFiles.length ? "flex" : "none";
    box.innerHTML = sourceFiles.map((f, i) => `<span class="chip" style="cursor:default">📄 ${esc(f.name)} · ${f.chars.toLocaleString()}자${f.truncated ? " (앞부분만 사용)" : f.long ? " (길어서 핵심만 요약해 사용)" : ""}${f.ocr ? " · 스캔 글자 읽음" : ""}
      <a href="#" data-src-del="${i}" title="빼기" style="margin-left:4px;text-decoration:none">✕</a></span>`).join("") +
      (sourceFiles.length ? `<label style="display:inline-flex;gap:4px;align-items:center;margin-left:4px"><input type="checkbox" id="src-research"${sourceResearch ? " checked" : ""}> 최신 인터넷 조사도 함께 반영</label>` : "");
    box.querySelectorAll("[data-src-del]").forEach((a) => a.onclick = (e) => { e.preventDefault(); sourceFiles.splice(+a.dataset.srcDel, 1); renderSources(); });
    const c = $("src-research");
    if (c) c.onchange = () => { sourceResearch = c.checked; };
    $("prompt-input").placeholder = sourceFiles.length ? "자료로 어떤 발표를 만들까요? 비워 두면 핵심을 정리합니다 (예: 임원 보고용으로 요약)"
      : "어떤 발표 자료를 만들까요? 예) 2026년 대한민국 고용 동향 보고서";
  }
  async function addSources(files) {
    for (const f of files) {
      if (sourceFiles.length >= 5) { toast("자료는 5개까지 넣을 수 있습니다.", true); break; }
      if (f.size > 20 * 1024 * 1024) { toast(`${f.name}: 20MB 이하 파일만 넣을 수 있습니다.`, true); continue; }
      const data = await new Promise((ok, no) => {
        const r = new FileReader();
        r.onload = () => ok(String(r.result).split(",")[1] || "");
        r.onerror = no;
        r.readAsDataURL(f);
      });
      $("btn-src").disabled = true;
      if (/\.(pdf|png|jpe?g|webp)$/i.test(f.name)) toast(`${f.name}: 글자가 없는 스캔 문서면 AI가 읽느라 최대 1분 걸립니다.`, false);
      try {
        const res = await api("/api/read_source", { name: f.name, data });
        if (!res.ok) toast(`${f.name}: ${res.message}`, true);
        else sourceFiles.push(res);
      } finally { $("btn-src").disabled = false; }
    }
    renderSources();
  }
  $("btn-src").onclick = () => $("src-file").click();
  $("src-file").onchange = async (e) => { await addSources([...e.target.files]); e.target.value = ""; };
  const dock = document.querySelector(".dock");
  dock.addEventListener("dragover", (e) => e.preventDefault());
  dock.addEventListener("drop", (e) => { e.preventDefault(); if (e.dataTransfer.files.length) addSources([...e.dataTransfer.files]); });

  async function generate() {
    const prompt = $("prompt-input").value.trim();
    const hasSrc = sourceFiles.length > 0;
    if (!prompt && !hasSrc) { toast("만들고 싶은 발표 주제를 입력하거나 내 자료를 넣어 주세요.", true); $("prompt-input").focus(); return; }
    const research = hasSrc ? sourceResearch : !!state.opts.research;
    $("opts-pop").classList.remove("open");

    $("btn-generate").disabled = true;
    $("loading").classList.add("on");
    $("step-research").style.display = research ? "" : "none";
    setStep("step-research", research ? "run" : null);
    setStep("step-write", research ? null : "run");
    setStep("step-design", null);
    const t0 = Date.now();
    const timer = setInterval(() => {
      const sec = Math.round((Date.now() - t0) / 1000);
      $("loading-time").textContent = `${sec}초 경과 · 보통 30초~1분 걸립니다`;
      if (research && sec === 15) { setStep("step-research", "done"); setStep("step-write", "run"); }
    }, 1000);

    try {
      const res = await api("/api/generate", {
        prompt, title: "", preset_id: state.presetId,
        theme: (state.project && state.project.theme) || "pitch-deck-vc",
        font: $("font-select").value || "theme",
        opts: { ...state.opts, research },
        material: sourceFiles.map((f) => ({ name: f.name, text: f.text })),
      });
      if (!res.ok) { toast(res.message || "생성에 실패했습니다.", true); return; }
      setStep("step-research", "done"); setStep("step-write", "done"); setStep("step-design", "done");
      state.idx = 0;
      applyProject(res.project, false);
      const extra = res.research_used ? ` · 최신 자료 ${res.source_count}건 반영${res.research_how === "web" ? " (인터넷 조사)" : ""}` : "";
      const ph = res.photos_pending ? ` · 사진 ${res.photos_pending}장은 찾는 대로 넣습니다` : "";
      toast(`${res.message}${extra}${ph}`);
      if (res.research_failed) setTimeout(() => toast(res.research_note || "최신 자료 검색을 쓸 수 없어(네트워크 확인) AI가 알고 있는 내용으로 만들었습니다. 수치는 직접 확인해 주세요.", true), 1800);
      if (res.photos_pending) watchPhotos(res.project.id);
    } catch (e) {
      toast("서버와 통신하지 못했습니다. 프로그램을 다시 실행해 주세요.", true);
    } finally {
      clearInterval(timer);
      $("loading").classList.remove("on");
      $("btn-generate").disabled = false;
    }
  }

  // 생성 뒤 사진이 하나씩 들어오면 미리보기를 새로 고친다 (글자 편집 중에는 끝날 때까지 미룸)
  let photoTimer = null;
  function watchPhotos(pid) {
    clearInterval(photoTimer);
    let seenRev = -1, dirty = false;
    const badge = $("photo-badge");
    const tick = async () => {
      let st;
      try { st = await api("/api/photo_status"); } catch (e) { return; }
      if (!state.project || state.project.id !== pid || st.pid !== pid) { stop(); return; }
      if (badge) { badge.textContent = `🖼 사진 찾는 중 ${st.pending}장`; badge.style.display = st.pending ? "" : "none"; }
      if (seenRev < 0) seenRev = st.rev;
      else if (st.rev !== seenRev) { dirty = true; seenRev = st.rev; }
      if (dirty && !editing) {
        dirty = false;
        try { const r = await api("/api/active_project"); if (r.project && r.project.id === pid) applyProject(r.project, true); } catch (e) {}
      }
      if (!st.pending && !dirty) { stop(); }
    };
    const stop = () => { clearInterval(photoTimer); photoTimer = null; if (badge) badge.style.display = "none"; };
    photoTimer = setInterval(tick, 3000);
    tick();
  }

  // ───────────────── 내보내기 (저장 위치 선택) ─────────────────
  const exportMenu = $("export-menu");
  $("btn-export").onclick = (e) => { e.stopPropagation(); exportMenu.classList.toggle("open"); };
  document.addEventListener("click", (e) => {
    if (!exportMenu.contains(e.target)) exportMenu.classList.remove("open");
    if (!$("opts-pop").contains(e.target) && e.target !== $("btn-opts")) $("opts-pop").classList.remove("open");
  });
  const FMT_LABEL = { pptx: "편집 가능한 파워포인트", pptx_img: "파워포인트(이미지)", pdf: "PDF", html: "HTML", png: "이미지 묶음" };
  exportMenu.querySelectorAll("button").forEach((b) => b.onclick = async () => {
    exportMenu.classList.remove("open");
    const fmt = b.dataset.fmt;
    $("busy-text").textContent = `${FMT_LABEL[fmt]}로 저장`;
    $("busy-sub").textContent = "저장할 위치를 선택해 주세요. 선택 후 변환에 10~30초 걸릴 수 있습니다.";
    $("busy").classList.add("on");
    try {
      const r = await api("/api/export", { format: fmt });
      if (r.ok) toast(`${r.message} · ${r.path}`, false, { label: "폴더 열기", run: () => api("/api/reveal", { path: r.path }) });
      else if (!r.cancelled) toast(r.message || "저장에 실패했습니다.", true);
    } catch (e) { toast("저장에 실패했습니다.", true); }
    finally { $("busy").classList.remove("on"); }
  });

  // ───────────────── 생성 옵션 ─────────────────
  const OPT_TEXT = {
    closing: { thanks: "감사합니다", qna: "Q&A", none: "" },
    tone: { formal: "보고서체", concise: "개조식", friendly: "친근한", academic: "학술" },
    language: { ko: "", en: "영어", ko_en: "한영" },
  };
  const MOOD_LABEL = { swiss: "에디토리얼", quiet: "차분한 여백", magazine: "매거진", bold: "대담한", spec: "사양서", cardnews: "카드뉴스", luxury: "고급·절제", playful: "경쾌한", tech: "기술·데이터" };
  function optsSummary() {
    const o = state.opts, parts = [`본문 ${o.slide_count}장`];
    if (o.toc) parts.push("목차");
    if (o.sources) parts.push("출처");
    if (o.research) parts.push("최신 검색");
    if (o.visuals === "photos") parts.push(`아이콘·사진${{ few: "(적게)", many: "(많이)" }[o.photo_level] || ""}`); else if (o.visuals !== "none") parts.push("아이콘");
    const mood = MOOD_LABEL[o.mood]; if (mood) parts.push(mood);
    if (o.elements === "rich") parts.push("표·그래프 적극"); else if (o.elements === "minimal") parts.push("표·그래프 최소");
    const FIELD_LABEL = { sales: "영업", ir: "IR", plan: "사업계획", marketing: "마케팅", edu: "교육", report: "보고", research: "연구", company: "회사소개", event: "행사" };
    if (FIELD_LABEL[o.field]) parts.unshift(FIELD_LABEL[o.field]);
    if (o.infographic === "many") parts.push("인포그래픽 많이"); else if (o.infographic === "none") parts.push("인포그래픽 없음");
    const row = $("photo-level-row"); if (row) row.style.display = o.visuals === "photos" ? "" : "none";   // 사진을 쓸 때만 사용량 선택
    if (OPT_TEXT.closing[o.closing]) parts.push(OPT_TEXT.closing[o.closing]);
    parts.push(OPT_TEXT.tone[o.tone] || "");
    if (OPT_TEXT.language[o.language]) parts.push(OPT_TEXT.language[o.language]);
    $("opts-summary").textContent = parts.filter(Boolean).join(" · ");
  }
  function bindOpts() {
    document.querySelectorAll("[data-o]").forEach((el) => {
      const k = el.dataset.o, v = state.opts[k];
      if (el.type === "checkbox") el.checked = !!v; else el.value = v == null ? "" : v;
      el.onchange = el.oninput = () => {
        state.opts[k] = el.type === "checkbox" ? el.checked : (k === "slide_count" ? parseInt(el.value, 10) : el.value);
        optsSummary();
        if (k === "mood") suggestThemeForMood();
      };
    });
    optsSummary();
  }
  $("btn-opts").onclick = (e) => { e.stopPropagation(); $("opts-pop").classList.toggle("open"); };
  $("btn-opts-close").onclick = () => $("opts-pop").classList.remove("open");

  // ───────────────── 슬라이드 표시 설정 ─────────────────
  const DISP_DEFAULT = { numbers: true, cover_number: false, progress: true, footer: "", logo: "", logo_pos: "tr", transition: "slide", motion: "subtle" };
  function bindDisplay() {
    const d = Object.assign({}, DISP_DEFAULT, (state.project && state.project.display) || {});
    document.querySelectorAll("[data-d]").forEach((el) => {
      const k = el.dataset.d;
      if (el.type === "checkbox") el.checked = !!d[k]; else el.value = d[k] || "";
    });
    $("logo-img").src = d.logo || "";
    $("logo-img").style.display = d.logo ? "" : "none";
  }
  document.querySelectorAll("[data-d]").forEach((el) => {
    el.addEventListener("change", () => {
      updateStyle({ display: { [el.dataset.d]: el.type === "checkbox" ? el.checked : el.value } });
    });
  });
  $("btn-display").onclick = () => {
    bindDisplay();
    $("drawer-history").classList.remove("open");
    $("btn-display").classList.toggle("on", $("drawer-display").classList.toggle("open"));
  };
  $("btn-close-display").onclick = () => { $("drawer-display").classList.remove("open"); $("btn-display").classList.remove("on"); };
  $("btn-logo").onclick = () => $("logo-file").click();
  $("btn-logo-clear").onclick = () => updateStyle({ display: { logo: "" } }).then(bindDisplay);
  $("logo-file").onchange = () => {
    const f = $("logo-file").files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = () => {
      const img = new Image();
      img.onload = async () => {
        // 너무 큰 이미지는 높이 160px로 줄여서 저장
        const sc = Math.min(1, 160 / img.height);
        const c = Object.assign(document.createElement("canvas"), { width: Math.round(img.width * sc), height: Math.round(img.height * sc) });
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        const data = f.type === "image/svg+xml" && rd.result.length < 200000 ? rd.result : c.toDataURL("image/png");
        await updateStyle({ display: { logo: data } });
        bindDisplay();
      };
      img.src = rd.result;
    };
    rd.readAsDataURL(f);
    $("logo-file").value = "";
  };

  // ───────────────── 프로젝트 목록 ─────────────────
  $("btn-history").onclick = async () => {
    const d = $("drawer-history");
    $("drawer-display").classList.remove("open"); $("btn-display").classList.remove("on");
    if (d.classList.toggle("open")) {
      const list = $("history-list");
      list.innerHTML = `<div class="empty">불러오는 중…</div>`;
      const data = await api("/api/history");
      const items = data.history || [];
      list.innerHTML = items.length ? "" : `<div class="empty">저장된 프로젝트가 없습니다.</div>`;
      items.forEach((p) => {
        const n = (p.slides_html || "").split('class="slide"').length - 1;
        const el = document.createElement("div");
        el.className = "proj";
        el.innerHTML = `<b>${esc(p.title)}</b><span>${esc(p.created_at || "")} · ${n}장 · ${esc(p.prompt || "")}</span>`;
        el.onclick = async () => {
          const r = await api("/api/load_project", { id: p.id });
          if (r.ok) { state.idx = 0; applyProject(r.project, false); d.classList.remove("open"); }
          else toast(r.message, true);
        };
        list.appendChild(el);
      });
    }
  };
  $("btn-close-history").onclick = () => $("drawer-history").classList.remove("open");

  // ───────────────── 설정 ─────────────────
  const modal = $("settings-modal");
  // 구독 로그인(공식 CLI): 로그인 버튼 → 기본 브라우저(크롬 등)에서 로그인 → 상태가 '연결됨'이 되면 바로 사용
  let cliTimer = null, cliProvider = "";
  const CLI_NAME = { codex_cli: "ChatGPT", claude_cli: "Claude", gemini_cli: "Google(Gemini)" };
  async function refreshCli() {
    const pv = $("cfg-provider").value;
    const box = $("cli-box");
    cliProvider = pv;
    if (!CLI_NAME[pv]) { box.style.display = "none"; clearInterval(cliTimer); cliTimer = null; return; }
    box.style.display = "";
    $("cli-title").textContent = pv === "gemini_cli" ? "Google 계정 로그인 (Gemini)" : `${CLI_NAME[pv]} 구독 로그인`;
    $("cli-state").textContent = "확인 중…"; $("cli-state").style.color = "#6b7280"; $("cli-help").textContent = "";   // 이전 공급자의 상태가 남아 보이지 않게
    $("btn-cli-login").disabled = true;
    let st;
    try { st = await api(`/api/cli/status?provider=${pv}`); } catch (e) { return; }
    if (pv !== cliProvider) return;
    const stEl = $("cli-state"), help = $("cli-help"), btn = $("btn-cli-login");
    if (!st.ok) { stEl.textContent = st.message || "쓸 수 없습니다."; stEl.style.color = "#b3261e"; btn.disabled = true; return; }
    btn.disabled = !st.installed;
    if (!st.installed) {
      stEl.textContent = "❌ 프로그램이 설치되어 있지 않습니다"; stEl.style.color = "#b3261e";
      help.textContent = `먼저 설치해 주세요 (명령 프롬프트에서): ${st.install}`;
    } else if (st.logged_in) {
      stEl.textContent = `✅ 연결됨${st.detail ? " · " + st.detail : ""}`; stEl.style.color = "#1a7f4b";
      help.textContent = "이 구독 계정으로 슬라이드를 만들고 고칩니다. 별도 API 키는 필요 없습니다. 생성 속도는 Gemini보다 느릴 수 있고(1~3분), 최신 자료 검색은 쓸 수 없습니다.";
      if (cliTimer) { clearInterval(cliTimer); cliTimer = null; toast(`${CLI_NAME[pv]} 로그인이 연결되었습니다.`); }
    } else {
      stEl.textContent = st.logging_in ? "⏳ 브라우저에서 로그인을 마쳐 주세요…" : "로그인이 필요합니다"; stEl.style.color = "#b45309";
      help.textContent = "버튼을 누르면 기본 브라우저(크롬 등)에 로그인 창이 열립니다. 로그인을 마치면 이 화면이 자동으로 '연결됨'으로 바뀝니다.";
    }
  }
  $("cfg-provider").addEventListener("change", refreshCli);
  $("btn-cli-refresh").onclick = refreshCli;
  $("btn-cli-login").onclick = async () => {
    const r = await api("/api/cli/login", { provider: $("cfg-provider").value });
    toast(r.message || (r.ok ? "로그인 창을 열었습니다." : "로그인을 시작하지 못했습니다."), !r.ok);
    if (r.ok) { clearInterval(cliTimer); let n = 0; cliTimer = setInterval(() => { if (++n > 60 || !modal.classList.contains("open")) { clearInterval(cliTimer); cliTimer = null; return; } refreshCli(); }, 3000); }
    refreshCli();
  };
  $("btn-settings").onclick = async () => {
    const { config: c = {}, edition } = await api("/api/config");
    document.querySelectorAll("#cfg-provider option[data-cli]").forEach((o) => { o.hidden = o.disabled = edition === "retail"; });   // 판매판은 구독 로그인 숨김
    $("cfg-provider").value = c.provider || "gemini";
    refreshCli();
    { const gm = c.gemini_model || "";   // 2.5 등 예전 모델 저장값은 3.5로 보여 준다(무료 키는 3.5 이상만)
      const ok = [...$("cfg-gemini-model").options].some((o) => o.value === gm);
      $("cfg-gemini-model").value = ok ? gm : "gemini-3.5-flash"; }
    $("cfg-gemini-key").value = c.gemini_api_key || "";
    $("cfg-openai-key").value = c.openai_api_key || "";
    $("cfg-pixabay-key").value = c.pixabay_api_key || "";
    modal.classList.add("open");
  };
  $("btn-close-settings").onclick = $("btn-cancel-settings").onclick = () => { modal.classList.remove("open"); clearInterval(cliTimer); cliTimer = null; };
  $("btn-save-settings").onclick = async () => {
    await api("/api/config", {
      provider: $("cfg-provider").value,
      gemini_model: $("cfg-gemini-model").value,
      gemini_api_key: $("cfg-gemini-key").value.trim(),
      openai_api_key: $("cfg-openai-key").value.trim(),
      pixabay_api_key: $("cfg-pixabay-key").value.trim(),
    });
    modal.classList.remove("open");
    clearInterval(cliTimer); cliTimer = null;
    toast("설정을 저장했습니다.");
  };

  // ───────────────── 슬라이드 한 장 편집 ─────────────────
  async function slideOp(op, body, okMsg) {
    let res;
    try { res = await api("/api/slide_op", Object.assign({ op }, body)); }
    catch (e) { toast("서버와 통신하지 못했습니다.", true); return null; }
    if (!res.ok) { if (res.message) toast(res.message, true); return res; }
    $("btn-undo").disabled = !res.can_undo;
    if (!["replace", "notes", "ai_edit", "set_photo", "add_obj"].includes(op)) aiChat = {};   // 순서·개수가 바뀌면 대화 기록 번호가 어긋나므로 비운다
    if (res.project) {
      // 글자·대본 저장은 그 사이 다른 슬라이드로 옮겨 갔을 수 있으므로 현재 위치를 유지
      if (op !== "replace" && op !== "notes") state.idx = res.idx || 0;
      applyProject(res.project, true);
    }
    const msg = okMsg || res.message;
    if (msg) toast(msg, false, op !== "undo" ? { label: "되돌리기", run: undo } : null);
    return res;
  }
  function undo() { if (!$("btn-undo").disabled) slideOp("undo", {}); }
  $("btn-undo").onclick = undo;

  // 대본 고치기
  $("notes-text").addEventListener("blur", () => {
    const s = state.slides[state.idx];
    if (!s) return;
    const text = $("notes-text").innerText.trim();
    if (text !== (s.notes || "").trim()) slideOp("notes", { idx: state.idx, text });
  });
  $("notes-text").addEventListener("keydown", (e) => { if (e.key === "Escape") { markActive(); $("notes-text").blur(); } });

  // ── 편집 모드: 글자 직접 수정 + 그림·도형 옮기기/크기/삭제 (미리보기 iframe 안에서) ──
  let editing = null;
  const EDIT_CSS = `[data-ep]{outline:2px dashed transparent;outline-offset:5px;border-radius:3px;cursor:text;transition:outline-color .12s}
    [data-ep]:hover{outline-color:rgba(124,58,237,.55)}
    [data-ep]:focus{outline:2px solid #7c3aed;background:rgba(124,58,237,.07)}
    [data-gobj]{cursor:move;user-select:none;-webkit-user-select:none}
    [data-gobj] img{-webkit-user-drag:none;user-select:none;pointer-events:none}
    [data-gobj]:hover{outline:2px dashed rgba(124,58,237,.6);outline-offset:2px}
    .__gsel{outline:3px solid #7c3aed!important;outline-offset:2px}
    .g-photo.__gsel{outline-offset:-3px}
    .__gh{position:absolute;width:22px;height:22px;background:#fff;border:3px solid #7c3aed;border-radius:50%;z-index:99;line-height:0}
    .__gh[data-h=nw]{left:-11px;top:-11px;cursor:nwse-resize}.__gh[data-h=ne]{right:-11px;top:-11px;cursor:nesw-resize}
    .__gh[data-h=sw]{left:-11px;bottom:-11px;cursor:nesw-resize}.__gh[data-h=se]{right:-11px;bottom:-11px;cursor:nwse-resize}`;
  const OBJ_COLORS = [["var(--accent)", "강조색"], ["var(--accent-2)", "보조색"], ["var(--accent-3)", "포인트색"], ["var(--text-1)", "글자색"], ["var(--surface-2)", "연한 배경색"]];
  function hasOwnText(el) { return Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim()); }
  function frameSlide(i) {
    let doc;
    try { doc = frame.contentDocument; } catch (e) { doc = null; }
    return doc ? doc.querySelectorAll(".deck .slide")[i] : null;
  }
  function liveObjs(sec) { return Array.from(sec.querySelectorAll(":scope > .g-obj, :scope > .g-photo")); }
  function cleanObj(el) {
    const c = el.cloneNode(true);
    c.querySelectorAll(".__gh").forEach((h) => h.remove());
    c.classList.remove("__gsel");
    c.removeAttribute("data-gobj");
    c.querySelectorAll("img").forEach((im) => im.removeAttribute("draggable"));
    if (!c.getAttribute("class")) c.removeAttribute("class");
    return c.outerHTML.replace(/\s(contenteditable|spellcheck|data-ep)="[^"]*"/g, "");
  }
  function objSnapshot(sec) { return (sec.classList.contains("with-photo") ? "P|" : "-|") + liveObjs(sec).map(cleanObj).join(""); }

  function startEdit(selectLast) {
    if (editing) return;
    const sec = frameSlide(state.idx);
    if (!sec) { toast("미리보기가 아직 준비되지 않았습니다. 잠시 뒤 다시 눌러 주세요.", true); return; }
    const doc = sec.ownerDocument, win = doc.defaultView;
    $("ai-pop").classList.remove("open");
    const els = [];
    (function walk(el, path) {
      Array.from(el.children).forEach((c, i) => {
        if (c.matches("aside, .notes, .g-footer, .g-logo, .g-obj, .g-photo, .g-ico, br, img, svg")) return;
        const p = path.concat(i);
        if (hasOwnText(c)) { c.setAttribute("data-ep", p.join(".")); c.contentEditable = "true"; c.spellcheck = false; els.push(c); }
        else walk(c, p);
      });
    })(sec, []);
    let st = doc.getElementById("__gyeol_edit_css");
    if (!st) { st = doc.createElement("style"); st.id = "__gyeol_edit_css"; st.textContent = EDIT_CSS; doc.head.appendChild(st); }
    const ed = { idx: state.idx, sec, els, orig: els.map((el) => el.innerHTML), paths: els.map((el) => el.dataset.ep), win, doc, sel: null, objOrig: objSnapshot(sec) };
    editing = ed;
    liveObjs(sec).forEach((o) => { o.setAttribute("data-gobj", ""); o.querySelectorAll("img").forEach((im) => im.setAttribute("draggable", "false")); });

    const scale = () => sec.getBoundingClientRect().width / sec.offsetWidth || 1;
    const num = (v) => parseFloat(v) || 0;
    function select(o) {
      if (ed.sel === o) return;
      if (ed.sel) { ed.sel.classList.remove("__gsel"); ed.sel.querySelectorAll(".__gh").forEach((h) => h.remove()); }
      ed.sel = o;
      if (o) {
        o.classList.add("__gsel");
        if (o.classList.contains("g-obj")) ["nw", "ne", "sw", "se"].forEach((h) => { const d = doc.createElement("span"); d.className = "__gh"; d.dataset.h = h; o.appendChild(d); });
        if (doc.activeElement && doc.activeElement.blur) doc.activeElement.blur();
      }
      showObjTools(o);
    }
    ed.select = select;
    ed.onDown = (e) => {
      const o = e.target.closest && e.target.closest("[data-gobj]");
      if (!o) { if (!(e.target.closest && e.target.closest("[data-ep]"))) select(null); else if (ed.sel) select(null); return; }
      e.preventDefault();
      select(o);
      if (!o.classList.contains("g-obj")) return;  // 사진 패널은 옮기지 않는다
      const k = scale(), h = e.target.dataset && e.target.dataset.h;
      const s0 = { x: e.clientX, y: e.clientY, l: num(o.style.left), t: num(o.style.top), w: o.offsetWidth, h: o.offsetHeight };
      const keepRatio = !!o.querySelector("img") || o.classList.contains("ico") || o.dataset.ratio === "1";
      const move = (ev) => {
        const dx = (ev.clientX - s0.x) / k, dy = (ev.clientY - s0.y) / k;
        if (!h) { o.style.left = Math.round(s0.l + dx) + "px"; o.style.top = Math.round(s0.t + dy) + "px"; return; }
        let w = s0.w + (h.includes("e") ? dx : -dx), hh = s0.h + (h.includes("s") ? dy : -dy);
        if (keepRatio !== ev.shiftKey) { const r = s0.w / s0.h; if (Math.abs(dx) > Math.abs(dy)) hh = w / r; else w = hh * r; }
        w = Math.max(24, w); hh = Math.max(o.dataset.line ? 4 : 24, hh);
        o.style.width = Math.round(w) + "px"; o.style.height = Math.round(hh) + "px";
        if (h.includes("w")) o.style.left = Math.round(s0.l + s0.w - w) + "px";
        if (h.includes("n")) o.style.top = Math.round(s0.t + s0.h - hh) + "px";
      };
      const up = () => { doc.removeEventListener("mousemove", move); doc.removeEventListener("mouseup", up); };
      doc.addEventListener("mousemove", move);
      doc.addEventListener("mouseup", up);
    };
    ed.onKey = (e) => {
      const inText = e.target.closest && e.target.closest("[data-ep]");
      if (!inText && ed.sel) {
        e.stopPropagation();
        if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); objAction("del"); return; }
        if (e.key === "Escape") { e.preventDefault(); select(null); return; }
        if (e.key.startsWith("Arrow") && ed.sel.classList.contains("g-obj")) {
          e.preventDefault();
          const d = e.shiftKey ? 10 : 1, o = ed.sel;
          if (e.key === "ArrowLeft") o.style.left = num(o.style.left) - d + "px";
          if (e.key === "ArrowRight") o.style.left = num(o.style.left) + d + "px";
          if (e.key === "ArrowUp") o.style.top = num(o.style.top) - d + "px";
          if (e.key === "ArrowDown") o.style.top = num(o.style.top) + d + "px";
          return;
        }
      }
      if (!inText) { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); finishEdit(false); } else e.stopPropagation(); return; }
      e.stopPropagation();  // 미리보기의 슬라이드 넘김 단축키가 먹지 않게
      if (e.key === "Enter") { e.preventDefault(); doc.execCommand("insertLineBreak"); }
      else if (e.key === "Escape") { e.preventDefault(); finishEdit(false); }
      else if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) { e.preventDefault(); finishEdit(true); }
    };
    ed.onPaste = (e) => {
      if (!e.target.closest || !e.target.closest("[data-ep]")) return;
      e.preventDefault();
      doc.execCommand("insertText", false, (e.clipboardData || win.clipboardData).getData("text/plain"));
    };
    win.addEventListener("keydown", ed.onKey, true);
    doc.addEventListener("paste", ed.onPaste, true);
    doc.addEventListener("mousedown", ed.onDown, true);
    $("edit-banner").classList.add("on");
    $("slide-stage").classList.add("editing");
    $("btn-edit").classList.add("on");
    $("btn-edit").textContent = "✔ 수정 마치기";
    const objs = liveObjs(sec);
    if (selectLast && objs.length) { select(objs[objs.length - 1]); try { frame.focus(); } catch (e) {} }
    else if (els.length) els[0].focus();
    else showObjTools(null);
  }

  function showObjTools(o) {
    const on = !!o;
    $("obj-tools").classList.toggle("on", on);
    $("edit-hint").style.display = on ? "none" : "";
    $("edit-sub").textContent = on ? (o.classList.contains("g-obj") ? "끌어서 이동 · 모서리로 크기 · Delete 삭제" : "사진 패널") : "Enter 줄바꿈 · Esc 취소";
    if (!on) return;
    const isObj = o.classList.contains("g-obj");
    const colorable = isObj && !o.querySelector("img");
    $("obj-colors").innerHTML = colorable ? OBJ_COLORS.map(([v, n]) => `<button class="sw" title="${n}" data-c="${v}"></button>`).join("") : "";
    // 색 견본은 미리보기의 실제 테마 색으로 칠한다
    const cs = editing && editing.win.getComputedStyle(editing.sec);
    $("obj-colors").querySelectorAll(".sw").forEach((b) => {
      const name = b.dataset.c.slice(4, -1);
      b.style.background = (cs && cs.getPropertyValue(name).trim()) || "#999";
      b.onclick = () => { o.style.color = b.dataset.c; };
    });
    document.querySelector('#obj-tools [data-o="front"]').style.display = isObj ? "" : "none";
    document.querySelector('#obj-tools [data-o="back"]').style.display = isObj ? "" : "none";
    document.querySelector('#obj-tools [data-o="swap"]').style.display = isObj && !o.querySelector("img") ? "none" : "";
  }
  function objAction(a) {
    const ed = editing;
    if (!ed || !ed.sel) return;
    const o = ed.sel;
    if (a === "del") {
      ed.select(null);
      if (o.classList.contains("g-photo")) ed.sec.classList.remove("with-photo");
      o.remove();
      if (ed.win.__gyeolFit) ed.win.__gyeolFit(ed.sec);
    } else if (a === "front") { o.classList.remove("back"); ed.sec.appendChild(o); }
    else if (a === "back") { o.classList.add("back"); }
    else if (a === "swap") { openMedia(o.classList.contains("g-photo") ? "search" : "search", { swap: o }); }
  }
  document.querySelectorAll("#obj-tools [data-o]").forEach((b) => b.onclick = () => objAction(b.dataset.o));

  function stopEditUi() {
    const ed = editing;
    editing = null;
    $("edit-banner").classList.remove("on");
    $("slide-stage").classList.remove("editing");
    $("btn-edit").classList.remove("on");
    $("btn-edit").textContent = "✏️ 편집";
    showObjTools(null);
    if (ed) {
      try {
        ed.win.removeEventListener("keydown", ed.onKey, true);
        ed.doc.removeEventListener("paste", ed.onPaste, true);
        ed.doc.removeEventListener("mousedown", ed.onDown, true);
      } catch (e) {}
    }
    return ed;
  }
  function cleanInline(h) {
    return h.replace(/\s(contenteditable|spellcheck|data-ep|data-fit-fs)="[^"]*"/g, "").replace(/(<br>\s*)+$/, "").trim();
  }
  function finishEdit(save) {
    const ed = stopEditUi();
    if (!ed) return;
    if (ed.sel) ed.select(null);
    ed.sec.querySelectorAll("[data-fit-fs]").forEach((el) => { el.style.fontSize = el.dataset.fitFs; el.removeAttribute("data-fit-fs"); });
    const changed = ed.els.map((el, k) => ({ el, k })).filter(({ el, k }) => el.innerHTML !== ed.orig[k]);
    const objNow = objSnapshot(ed.sec);
    const objChanged = objNow !== ed.objOrig;
    ed.els.forEach((el) => { el.removeAttribute("contenteditable"); el.removeAttribute("data-ep"); el.removeAttribute("spellcheck"); });
    if (!save) { if (changed.length || objChanged) reloadPreview(true); return; }
    if (!changed.length && !objChanged) { liveObjs(ed.sec).forEach((o) => o.removeAttribute("data-gobj")); return; }
    // 원본 HTML에서 같은 위치의 요소를 찾아 글자만 바꿔 넣는다 (경로는 편집 시작 때 기록)
    const tpl = document.createElement("template");
    tpl.innerHTML = state.project.slides_html || "";
    const src = tpl.content.querySelectorAll("section.slide")[ed.idx];
    if (!src) { toast("원본 슬라이드를 찾지 못했습니다.", true); reloadPreview(true); return; }
    for (const { el, k } of changed) {
      let node = src;
      for (const n of ed.paths[k].split(".")) node = node && node.children[+n];
      if (!node || node.tagName !== el.tagName) { toast("수정한 위치를 찾지 못했습니다. 다시 시도해 주세요.", true); reloadPreview(true); return; }
      node.innerHTML = cleanInline(el.innerHTML);
    }
    if (objChanged) {
      src.querySelectorAll(":scope > .g-obj, :scope > .g-photo").forEach((n) => n.remove());
      const live = liveObjs(ed.sec);
      const notes = src.querySelector(":scope > aside.notes");
      const holder = document.createElement("template");
      live.forEach((o) => {
        holder.innerHTML = cleanObj(o);
        const n = holder.content.firstElementChild;
        if (n.classList.contains("g-photo")) src.prepend(n); else src.insertBefore(n, notes);
      });
      src.classList.toggle("with-photo", live.some((o) => o.classList.contains("g-photo")));
    }
    slideOp("replace", { idx: ed.idx, html: src.outerHTML }, "수정 내용을 저장했습니다.");
  }
  $("btn-edit").onclick = () => (editing ? finishEdit(true) : startEdit());
  $("btn-edit-save").onclick = () => finishEdit(true);
  $("btn-edit-cancel").onclick = () => finishEdit(false);

  // 미리보기가 새로 뜬 뒤에 할 일 (예: 방금 넣은 그림 선택)
  function afterPreview(fn) {
    const h = () => {
      frame.removeEventListener("load", h);
      const d = frame.contentDocument;
      (d && d.fonts ? d.fonts.ready : Promise.resolve()).then(() => setTimeout(fn, 250));
    };
    frame.addEventListener("load", h);
  }

  // ───────────────── 그림·사진·아이콘·도형 넣기 ─────────────────
  const SHAPES = [
    { n: "사각형", h: '<span class="g-fill"></span>', w: 360, hh: 220 },
    { n: "둥근 사각형", h: '<span class="g-fill" style="border-radius:28px"></span>', w: 360, hh: 220 },
    { n: "원", h: '<span class="g-fill" style="border-radius:50%"></span>', w: 240, hh: 240, ratio: 1 },
    { n: "연한 강조 상자", h: '<span class="g-fill" style="border-radius:20px;opacity:.14"></span>', w: 620, hh: 260 },
    { n: "선", h: '<svg viewBox="0 0 100 10" preserveAspectRatio="none"><line x1="0" y1="5" x2="100" y2="5" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/></svg>', w: 420, hh: 12, line: 1 },
    { n: "화살표", h: '<svg viewBox="0 0 100 40" preserveAspectRatio="none"><polygon points="0,12 70,12 70,0 100,20 70,40 70,28 0,28" fill="currentColor"/></svg>', w: 260, hh: 104 },
    { n: "삼각형", h: '<svg viewBox="0 0 100 100" preserveAspectRatio="none"><polygon points="50,0 100,100 0,100" fill="currentColor"/></svg>', w: 220, hh: 200 },
    { n: "별", h: '<svg viewBox="0 0 100 100"><polygon points="50,4 62,38 98,38 69,60 80,95 50,74 20,95 31,60 2,38 38,38" fill="currentColor"/></svg>', w: 200, hh: 200, ratio: 1 },
    { n: "말풍선", h: '<svg viewBox="0 0 100 80" preserveAspectRatio="none"><path d="M10 0h80a10 10 0 0 1 10 10v44a10 10 0 0 1-10 10H40L22 80l4-16H10A10 10 0 0 1 0 54V10A10 10 0 0 1 10 0z" fill="currentColor"/></svg>', w: 360, hh: 260 },
    { n: "체크 원", h: '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="currentColor"/><path d="M28 52l15 15 30-32" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/></svg>', w: 140, hh: 140, ratio: 1 },
  ];
  let mmTab = "search", mmSwap = null, aiImgUrl = "", iconData = null;
  function openMedia(tab, o) {
    if (!state.slides.length) return;
    mmSwap = (o && o.swap) || null;
    $("insert-menu").classList.remove("open");
    setMmTab(tab);
    $("media-modal").classList.add("open");
    const f = { search: "ps-q", ai: "ai-img-prompt", icon: "ic-q" }[tab];
    if (f) setTimeout(() => $(f).focus(), 50);
  }
  function setMmTab(t) {
    mmTab = t;
    document.querySelectorAll("#mm-tabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === t));
    document.querySelectorAll(".mm-body").forEach((b) => b.classList.toggle("on", b.dataset.t === t));
    $("mm-place").style.display = (["search", "ai", "file"].includes(t) && !mmSwap) ? "" : "none";
    if (t === "icon") renderIcons();
    if (t === "shape" && !$("sh-grid").children.length) renderShapes();
  }
  document.querySelectorAll("#mm-tabs button").forEach((b) => b.onclick = () => setMmTab(b.dataset.t));
  $("btn-mm-close").onclick = () => $("media-modal").classList.remove("open");
  $("btn-insert").onclick = (e) => { e.stopPropagation(); $("insert-menu").classList.toggle("open"); };
  document.querySelectorAll("#insert-menu button").forEach((b) => b.onclick = () => openMedia(b.dataset.t));
  document.addEventListener("click", (e) => { if (!$("insert-menu").contains(e.target) && e.target !== $("btn-insert")) $("insert-menu").classList.remove("open"); });
  const placeMode = () => (document.querySelector('input[name="mm-place"]:checked') || {}).value || "panel";

  function imgSize(url) {
    return new Promise((res) => { const im = new Image(); im.onload = () => res([im.naturalWidth || 4, im.naturalHeight || 3]); im.onerror = () => res([4, 3]); im.src = url; });
  }
  async function insertObjHtml(inner, w, h, cls, extraAttr) {
    // 슬라이드 오른쪽 가운데쯤에 넣고, 바로 편집 모드로 들어가 선택해 둔다
    const left = Math.max(40, 1600 - 120 - w), top = Math.max(40, Math.round((900 - h) / 2));
    const html = `<div class="g-obj${cls ? " " + cls : ""}"${extraAttr || ""} style="left:${left}px;top:${top}px;width:${Math.round(w)}px;height:${Math.round(h)}px;color:var(--accent)">${inner}</div>`;
    if (editing) finishEdit(true);
    $("media-modal").classList.remove("open");
    const r = await slideOp("add_obj", { idx: state.idx, html });
    if (r && r.ok) afterPreview(() => startEdit(true));
  }
  async function placeImage(url) {
    if (mmSwap) {
      const o = mmSwap;
      mmSwap = null;
      const im = o.querySelector("img");
      if (im) im.src = url;
      $("media-modal").classList.remove("open");
      toast("사진을 바꿨습니다. 저장을 눌러 마무리하세요.");
      return;
    }
    if (placeMode() === "panel") {
      if (editing) finishEdit(true);
      $("media-modal").classList.remove("open");
      await slideOp("set_photo", { idx: state.idx, url });
      return;
    }
    const [nw, nh] = await imgSize(url);
    const w = 560, h = Math.round(w * nh / nw);
    insertObjHtml(`<img src="${url}" alt="">`, w, Math.min(h, 760), "round");
  }

  // 무료 사진 검색
  async function photoSearch() {
    const q = $("ps-q").value.trim();
    if (!q) { $("ps-q").focus(); return; }
    $("ps-busy").classList.add("on");
    $("ps-grid").innerHTML = "";
    try {
      const r = await api("/api/photo_search", { q });
      if (!r.ok) { toast(r.message, true); return; }
      if (!r.items.length) { $("ps-grid").innerHTML = `<div class="empty">${esc(r.message || "결과가 없습니다.")}</div>`; return; }
      r.items.forEach((it) => {
        const d = document.createElement("div");
        d.className = "ph";
        d.innerHTML = `<img loading="lazy" src="${esc(it.thumb)}" alt=""><span>${esc(it.title || it.source)}</span>`;
        d.onclick = async () => {
          $("ps-busy").classList.add("on");
          const f = await api("/api/media_fetch", { url: it.url });
          $("ps-busy").classList.remove("on");
          if (!f.ok) { toast(f.message || "사진을 받지 못했습니다. 다른 사진을 골라 주세요.", true); return; }
          placeImage(f.url);
        };
        $("ps-grid").appendChild(d);
      });
    } catch (e) { toast("사진 검색에 실패했습니다.", true); }
    finally { $("ps-busy").classList.remove("on"); }
  }
  $("ps-go").onclick = photoSearch;
  $("ps-q").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.isComposing) photoSearch(); });

  // AI 그림
  let aiImgStyle = "photo";
  document.querySelectorAll("#ai-img-style button").forEach((b) => b.onclick = () => {
    aiImgStyle = b.dataset.s;
    document.querySelectorAll("#ai-img-style button").forEach((x) => x.classList.toggle("on", x === b));
  });
  async function aiImage() {
    const prompt = $("ai-img-prompt").value.trim();
    if (!prompt) { $("ai-img-prompt").focus(); return; }
    $("ai-img-busy").classList.add("on"); $("ai-img-go").disabled = true;
    $("ai-img-actions").style.display = "none";
    try {
      const r = await api("/api/ai_image", { prompt, style: aiImgStyle });
      if (!r.ok) { toast(r.message, true); return; }
      aiImgUrl = r.url;
      if (r.by === "chatgpt") toast("ChatGPT 구독의 이미지 생성으로 그렸습니다.");
      $("ai-img-prev").src = r.url; $("ai-img-prev").style.display = "block";
      $("ai-img-actions").style.display = "flex";
    } catch (e) { toast("그림을 만들지 못했습니다.", true); }
    finally { $("ai-img-busy").classList.remove("on"); $("ai-img-go").disabled = false; }
  }
  $("ai-img-go").onclick = aiImage;
  $("ai-img-again").onclick = aiImage;
  $("ai-img-use").onclick = () => { if (aiImgUrl) placeImage(aiImgUrl); };

  // 아이콘
  async function renderIcons() {
    if (!iconData) {
      try { iconData = await (await fetch("/static/icons/icons.json")).json(); } catch (e) { toast("아이콘을 불러오지 못했습니다.", true); return; }
    }
    const q = $("ic-q").value.trim().toLowerCase();
    let list = iconData.curated.filter((c) => !q || c.k.toLowerCase().includes(q) || c.n.includes(q)).map((c) => ({ n: c.n, k: c.k.split(" ")[0] }));
    if (q && /[a-z]/.test(q)) {
      const have = new Set(list.map((x) => x.n));
      Object.keys(iconData.icons).filter((n) => n.includes(q) && !have.has(n)).slice(0, 150).forEach((n) => list.push({ n, k: n }));
    }
    const svg = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${iconData.icons[n]}</svg>`;
    $("ic-grid").innerHTML = list.length ? list.slice(0, 260).map((x) => `<div class="ic" data-n="${esc(x.n)}" title="${esc(x.n)}">${svg(x.n)}<span>${esc(x.k)}</span></div>`).join("")
      : `<div class="empty">찾는 아이콘이 없습니다. 다른 말로 찾아 보세요.</div>`;
    $("ic-grid").querySelectorAll(".ic").forEach((d) => d.onclick = () => insertObjHtml(svg(d.dataset.n), 140, 140, "ico", ` data-icon="${esc(d.dataset.n)}"`));
  }
  $("ic-q").addEventListener("input", renderIcons);

  // 도형
  function renderShapes() {
    $("sh-grid").innerHTML = SHAPES.map((s, i) => `<div class="sh" data-i="${i}"><div class="pv">${s.h}</div>${esc(s.n)}</div>`).join("");
    $("sh-grid").querySelectorAll(".pv .g-fill").forEach((f) => { f.style.background = "currentColor"; });
    $("sh-grid").querySelectorAll(".sh").forEach((d) => d.onclick = () => {
      const s = SHAPES[+d.dataset.i];
      insertObjHtml(s.h, s.w, s.hh, "shape", (s.ratio ? ' data-ratio="1"' : "") + (s.line ? ' data-line="1"' : ""));
    });
  }

  // 내 파일 올리기
  $("file-pick").onclick = () => $("file-input").click();
  $("file-input").onchange = () => {
    const f = $("file-input").files[0];
    $("file-input").value = "";
    if (!f) return;
    if (f.size > 20 * 1024 * 1024) { toast("20MB 이하 파일만 올릴 수 있습니다.", true); return; }
    const rd = new FileReader();
    rd.onload = async () => {
      $("file-busy").classList.add("on");
      try {
        const r = await api("/api/media_upload", { data_url: rd.result });
        if (!r.ok) { toast(r.message, true); return; }
        placeImage(r.url);
      } catch (e) { toast("파일을 올리지 못했습니다.", true); }
      finally { $("file-busy").classList.remove("on"); }
    };
    rd.readAsDataURL(f);
  };

  // ── AI로 이 슬라이드 고치기 / 새 슬라이드 추가 ──
  const AI_CHIPS = {
    edit: ["다시 만들기", "더 간결하게", "더 자세하게", "숫자를 그래프로", "카드형으로 정리", "아이콘 넣기", "어울리는 사진 넣기", "제목을 더 강렬하게", "다른 레이아웃으로", "쉬운 말로"],
    insert: ["사례 소개", "핵심 요약", "비교 분석", "추진 일정(로드맵)", "기대 효과", "질의응답 대비 FAQ"],
  };
  let aiMode = "edit";
  // 슬라이드별 대화 기록 (같은 슬라이드를 연달아 고칠 때 "더 짧게", "아까처럼" 같은 말을 알아듣게 함)
  let aiChat = {};
  const chatKey = () => `${state.project ? state.project.id : ""}:${state.idx}`;
  function renderAiLog() {
    const box = $("ai-log");
    const list = aiMode === "edit" ? (aiChat[chatKey()] || []) : [];
    box.classList.toggle("has", list.length > 0);
    box.innerHTML = list.map((m) => `<div class="msg ${m.role}">${esc(m.text)}</div>`).join("");
    box.scrollTop = box.scrollHeight;
  }
  function pushChat(role, text) {
    const k = chatKey();
    (aiChat[k] = aiChat[k] || []).push({ role, text });
    aiChat[k] = aiChat[k].slice(-20);
    renderAiLog();
  }
  function updateAiTarget() {
    const s = state.slides[state.idx];
    const n = state.idx + 1;
    $("ai-target").textContent = aiMode === "edit"
      ? `${n}번 슬라이드 「${s ? s.title : ""}」를 고칩니다. 비워 두면 같은 내용으로 새로 만듭니다.`
      : `${n}번 슬라이드 「${s ? s.title : ""}」 바로 뒤에 새 슬라이드를 넣습니다.`;
    $("ai-text").placeholder = aiMode === "edit"
      ? "예) 3개 카드로 나눠 줘 / 숫자를 막대 그래프로 보여 줘 / 경쟁사 비교를 추가해 줘"
      : "어떤 내용의 슬라이드를 넣을까요? 예) 국내 도입 기업 사례 3가지";
    $("btn-ai-run").textContent = aiMode === "edit" ? "✨ 이 슬라이드 고치기" : "✨ 새 슬라이드 만들기";
    renderAiLog();
  }
  function setAiMode(m) {
    aiMode = m;
    document.querySelectorAll("#ai-mode button").forEach((b) => b.classList.toggle("on", b.dataset.m === m));
    $("ai-chips").innerHTML = AI_CHIPS[m].map((c) => `<span class="chip">${esc(c)}</span>`).join("");
    $("ai-chips").querySelectorAll(".chip").forEach((c) => c.onclick = () => {
      const t = $("ai-text"), v = c.textContent;
      t.value = t.value.trim() ? `${t.value.trim()}, ${v}` : v;
      t.focus();
    });
    updateAiTarget();
  }
  function openAi(m) {
    if (editing) finishEdit(true);
    setAiMode(m);
    $("ai-pop").classList.add("open");
    $("ai-text").focus();
  }
  document.querySelectorAll("#ai-mode button").forEach((b) => b.onclick = () => setAiMode(b.dataset.m));
  $("btn-ai-slide").onclick = (e) => { e.stopPropagation(); $("ai-pop").classList.contains("open") ? $("ai-pop").classList.remove("open") : openAi("edit"); };
  $("btn-add-slide").onclick = (e) => { e.stopPropagation(); openAi("insert"); };
  $("btn-ai-close").onclick = () => $("ai-pop").classList.remove("open");
  $("ai-pop").addEventListener("click", (e) => e.stopPropagation());
  document.addEventListener("click", () => $("ai-pop").classList.remove("open"));
  $("ai-text").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); runAi(); }
  });
  $("btn-ai-run").onclick = runAi;
  async function runAi() {
    let instruction = $("ai-text").value.trim();
    if (instruction === "다시 만들기") instruction = "";
    if (aiMode === "insert" && !instruction) { toast("새 슬라이드에 넣을 내용을 적어 주세요.", true); $("ai-text").focus(); return; }
    const research = $("ai-research").checked;
    const idx = state.idx;
    const chatMode = aiMode === "edit";
    const history = chatMode ? (aiChat[chatKey()] || []).filter((m) => m.role !== "err") : [];
    if (chatMode) { pushChat("user", instruction || "다시 만들기"); $("ai-text").value = ""; }
    else $("ai-pop").classList.remove("open");
    $("busy-text").textContent = aiMode === "edit" ? `${idx + 1}번 슬라이드를 AI로 고치는 중` : "새 슬라이드를 만드는 중";
    $("busy-sub").textContent = research ? "최신 자료를 검색한 뒤 작성합니다. 보통 20~40초 걸립니다." : "보통 10~20초 걸립니다.";
    $("busy").classList.add("on");
    try {
      const r = await slideOp(aiMode === "edit" ? "ai_edit" : "ai_insert", { idx, instruction, research, history }, chatMode ? "" : undefined);
      if (!chatMode) { if (r && r.ok) $("ai-text").value = ""; }
      else if (r && r.ok) pushChat("ai", r.reply || "고쳤습니다. 마음에 안 들면 \"되돌리기\"를 누르거나 이어서 말해 주세요.");
      else pushChat("err", (r && r.message) || "고치지 못했습니다. 다시 시도해 주세요.");
    } finally {
      $("busy").classList.remove("on");
      if (chatMode) { $("ai-text").focus(); }
    }
  }

  // 장표 추천: 이 슬라이드에 어울리는 구성·꾸밈·스타일 (계산은 서버에서 바로, 적용은 AI 고치기로)
  function advClose() { $("adv-pop").classList.remove("open"); $("btn-advise").classList.remove("on"); }
  async function advShow() {
    if (editing) finishEdit(true);
    $("ai-pop").classList.remove("open");
    $("adv-pop").classList.add("open"); $("btn-advise").classList.add("on");
    $("adv-title").textContent = `${state.idx + 1}번 장표 추천`;
    $("adv-body").innerHTML = '<div class="adv-meta">내용을 살펴보는 중…</div>';
    let r;
    try { r = await api("/api/advise", { idx: state.idx }); } catch (e) { r = { ok: false, message: "서버와 통신하지 못했습니다." }; }
    if (!r.ok) { $("adv-body").innerHTML = `<div class="adv-meta">${esc(r.message || "추천하지 못했습니다.")}</div>`; return; }
    const cur = r.current_name ? ` · 지금 구성: <b>${esc(r.current_name)}</b>` : "";
    let h = `<div class="adv-meta">이 장표는 <b>${esc(r.role_ko)}</b> 장표로 보입니다${cur}</div>`;
    h += '<div class="adv-sec">어울리는 도식·구성</div><div class="adv-cards">';
    if (!r.layouts.length) h += '<div class="adv-meta" style="grid-column:1/-1">표지·간지·마무리 장표는 도식보다 아래 꾸밈으로 분위기를 살리는 편이 좋습니다.</div>';
    h += r.layouts.map((l, i) => `<div class="adv-card${i === 0 ? " first" : ""}"><b>${i === 0 ? "추천 · " : ""}${esc(l.name)}</b><small>${esc(l.why)}</small>`
      + `<button class="btn" data-ins="${esc(l.instruction)}" data-name="${esc(l.name)}">이 구성으로 바꾸기</button></div>`).join("");
    h += '</div><div class="adv-sec">어울리는 도형·꾸밈</div><div class="adv-cards">';
    h += r.decor.map((d) => `<div class="adv-card"><b>${esc(d.name)}</b><small>${esc(d.why)}</small>`
      + `<button class="btn" data-ins="${esc(d.instruction + " 다른 내용과 구성은 그대로 두세요.")}" data-name="${esc(d.name)}">얹기</button></div>`).join("");
    h += "</div>";
    if ((r.styles || []).length) {
      h += '<div class="adv-sec">어울리는 디자인 스타일 (덱 전체에 적용)</div><div class="adv-styles">';
      h += r.styles.map((st) => st.themes.map((t) => `<button class="btn" data-theme="${esc(t.id)}">${esc(st.label)} · ${esc(t.name)}</button>`).slice(0, 2).join("")).join("");
      h += "</div>";
    }
    $("adv-body").innerHTML = h;
  }
  async function advApply(instruction, name) {
    advClose();
    const idx = state.idx;
    $("busy-text").textContent = `${idx + 1}번 슬라이드를 '${name}'(으)로 바꾸는 중`;
    $("busy-sub").textContent = "내용은 그대로 두고 구성만 바꿉니다. 보통 10~20초 걸립니다.";
    $("busy").classList.add("on");
    try { await slideOp("ai_edit", { idx, instruction: instruction + " 글의 내용·수치·대본은 바꾸지 마세요.", research: false, history: [] }, `'${name}' 구성으로 바꿨습니다.`); }
    finally { $("busy").classList.remove("on"); }
  }
  async function advAll() {
    $("adv-title").textContent = "전체 장표 점검";
    $("adv-body").innerHTML = '<div class="adv-meta">모든 장표를 살펴보는 중…</div>';
    const r = await api("/api/advise", { all: true });
    if (!r.ok) { $("adv-body").innerHTML = `<div class="adv-meta">${esc(r.message || "점검하지 못했습니다.")}</div>`; return; }
    const reps = r.slides.filter((x) => x.repeat).length;
    let h = `<div class="adv-meta">장표를 누르면 그 장으로 가서 자세한 추천을 봅니다.${reps ? ` <span class="rep">같은 구성이 연달아 나오는 곳 ${reps}곳</span>` : ""}</div><div class="adv-list">`;
    h += r.slides.map((x) => `<div data-go="${x.idx}"><b>${x.idx + 1}</b><span>${esc(x.role_ko)}</span>`
      + `<span style="color:var(--ink-2)">${x.current_name ? esc(x.current_name) : "일반 구성"}</span>${x.repeat ? '<span class="rep">반복</span>' : ""}`
      + `<span class="spacer" style="flex:1"></span>${x.top ? `→ ${esc(x.top.name)}` : ""}</div>`).join("");
    $("adv-body").innerHTML = h + "</div>";
  }
  $("btn-advise").onclick = (e) => { e.stopPropagation(); $("adv-pop").classList.contains("open") ? advClose() : advShow(); };
  $("btn-adv-close").onclick = advClose;
  $("btn-adv-all").onclick = advAll;
  $("adv-pop").addEventListener("click", (e) => {
    e.stopPropagation();
    const b = e.target.closest("button[data-ins]");
    if (b) return advApply(b.dataset.ins, b.dataset.name);
    const t = e.target.closest("button[data-theme]");
    if (t) return updateStyle({ theme: t.dataset.theme });
    const g = e.target.closest("[data-go]");
    if (g) { goTo(+g.dataset.go); advShow(); }
  });
  document.addEventListener("click", advClose);

  // AI 검수: 모든 슬라이드를 화면으로 찍어 문제를 찾고 AI가 고친다 (끝날 때까지 상태를 확인)
  let reviewTimer = null;
  $("btn-review").onclick = async () => {
    if (reviewTimer) return;
    if (editing) finishEdit(true);
    let r;
    try { r = await api("/api/review_start", {}); } catch (e) { toast("서버와 통신하지 못했습니다.", true); return; }
    if (!r.ok) { toast(r.message || "검수를 시작하지 못했습니다.", true); return; }
    $("busy-text").textContent = "AI가 슬라이드를 검수하는 중";
    $("busy-sub").textContent = "화면으로 확인하고 문제가 있는 장만 고칩니다. 한 장에 5~15초 걸립니다.";
    $("busy-stop").style.display = "";
    $("busy-stop").onclick = () => { api("/api/review_stop", {}); $("busy-sub").textContent = "중지하는 중…"; };
    $("busy").classList.add("on");
    const tick = async () => {
      let st;
      try { st = await api("/api/review_status"); } catch (e) { return; }
      if (st.running) { $("busy-sub").textContent = `${st.msg} (${st.done}/${st.total})`; return; }
      clearInterval(reviewTimer); reviewTimer = null;
      $("busy").classList.remove("on"); $("busy-stop").style.display = "none";
      const res = st.result || {};
      if (!res.ok) { toast(res.message || "검수하지 못했습니다.", true); return; }
      if (res.fixed && res.fixed.length) {
        try { const pr = await api("/api/active_project"); if (pr.project) { state.idx = res.fixed[0].i; applyProject(pr.project, true); $("btn-undo").disabled = false; } } catch (e) {}
        const list = res.fixed.map((f) => `${f.i + 1}번`).join(", ");
        const left = res.left && res.left.length ? ` · 아직 확인이 필요한 장: ${res.left.map((i) => i + 1).join(", ")}번` : "";
        toast(`${res.checked}장을 검수해 ${list} 슬라이드를 고쳤습니다.${left}`, false, { label: "되돌리기", run: undo });
      } else if (res.left && res.left.length) {
        toast(`${res.checked}장을 검수했습니다. 확인이 필요한 장: ${res.left.map((i) => i + 1).join(", ")}번 (자동으로 고치지 못했습니다)`, false);
      } else {
        toast(`${res.checked}장을 모두 검수했고 문제가 없습니다.`, false);
      }
    };
    reviewTimer = setInterval(tick, 2000);
  };

  // 라이선스 창
  $("btn-license").onclick = () => showLicense(null, false);
  $("btn-close-license").onclick = () => { if (!lockScreen()) $("license-modal").classList.remove("open"); };
  $("lic-key").addEventListener("input", (e) => {
    const raw = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 16);
    e.target.value = raw.replace(/(.{4})(?=.)/g, "$1 ");
  });
  $("lic-key").addEventListener("keydown", (e) => { if (e.key === "Enter") $("btn-lic-activate").click(); });
  $("btn-lic-activate").onclick = async () => {
    const key = $("lic-key").value.replace(/\s/g, "");
    const btn = $("btn-lic-activate");
    btn.disabled = true; $("lic-msg").style.display = "none";
    try {
      let r;
      if (!key && lic && lic.usable && lic.has_key) { $("license-modal").classList.remove("open"); return; }
      if (!key && lic && lic.has_key) {
        r = await (await fetch("/api/license?force=1")).json();
        renderLicense(r);
        if (!r.usable) { $("lic-msg").textContent = r.error || "아직 사용할 수 없습니다."; $("lic-msg").style.display = ""; return; }
      } else {
        r = await api("/api/license_activate", { key });
        renderLicense(r);
        if (!r.ok) { $("lic-msg").textContent = r.msg; $("lic-msg").style.display = ""; return; }
      }
      $("lic-key").value = "";
      $("license-modal").classList.remove("open");
      location.reload();   // 잠겨 있던 화면 데이터를 다시 불러온다
    } catch (e) {
      $("lic-msg").textContent = "확인 중 문제가 생겼습니다. 다시 시도해 주세요."; $("lic-msg").style.display = "";
    } finally { btn.disabled = false; }
  };
  $("btn-lic-logout").onclick = async () => {
    if (!confirm("이 PC에서 라이선스를 로그아웃할까요?\n다시 쓰려면 키를 다시 넣어야 합니다.")) return;
    renderLicense(await api("/api/license_logout", {}));
    location.reload();
  };
  setInterval(async () => {
    const before = lic && lic.usable;
    await loadLicense();
    if (before && lic && !lic.usable) location.reload();
  }, 5 * 60 * 1000);

  // ───────────────── 시작 ─────────────────
  (async function init() {
    // 라이선스 확인이 끝나기 전에는 어떤 데이터도 요청하지 않는다
    const st = await loadLicense();
    if (!st || (!st.usable && !st.dev_bypass)) { showLicense(null, false); lockScreen(); return; }
    maybeWelcome();
    try {
      const [th, fo, ac, cf] = await Promise.all([api("/api/themes"), api("/api/fonts"), api("/api/active_project"), api("/api/config")]);
      state.opts = Object.assign({ elements: "normal", photo_level: "normal", mood: "auto", field: "auto", infographic: "normal" }, cf.gen_opts || {});
      if (!state.opts.elements) state.opts.elements = state.opts.charts === false ? "minimal" : "normal";   // 예전 '차트 적극 활용' 설정을 이어받음
      bindOpts();
      state.themes = th.themes || [];
      state.moodStyles = th.mood_styles || {};
      state.fonts = fo.fonts || [];
      $("font-select").innerHTML = state.fonts.map((f) => `<option value="${esc(f.id)}">${esc(f.name)}</option>`).join("");
      renderStyleChips();
      if (ac.project) applyProject(ac.project, false);
    } catch (e) {
      toast("초기 데이터를 불러오지 못했습니다.", true);
    }
  })();
});
