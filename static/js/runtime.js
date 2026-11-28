(function () {
  'use strict';

  const ANIMS = ['fade-up','fade-down','fade-left','fade-right','rise-in','drop-in',
    'zoom-pop','blur-in','glitch-in','typewriter','neon-glow','shimmer-sweep',
    'gradient-flow','stagger-list','counter-up','path-draw','parallax-tilt',
    'card-flip-3d','cube-rotate-3d','page-turn-3d','perspective-zoom',
    'marquee-scroll','kenburns','confetti-burst','spotlight','morph-shape','ripple-reveal'];

  function ready(fn){ if(document.readyState!='loading')fn(); else document.addEventListener('DOMContentLoaded',fn);}

  function getPreviewIdx() {
    const m = /[?&]preview=(\d+)/.exec(location.search || '');
    return m ? parseInt(m[1], 10) - 1 : -1;
  }

  ready(function () {
    const deck = document.querySelector('.deck');
    if (!deck) return;
    const slides = Array.from(deck.querySelectorAll('.slide'));

    /* ===== 데이터 차트(원형·도넛·선): AI는 숫자만 적고 그림은 여기서 정확하게 그린다 ===== */
    function chartColors(n){   // 테마 변수로 지정 → 테마를 바꾸면 색도 따라 바뀜
      const base = ['var(--accent)', 'var(--accent-2)', 'var(--accent-3)'];
      const out = [];
      for (let i = 0; i < n; i++) out.push(i < 3 ? base[i] : `color-mix(in srgb, ${base[i % 3]} ${100 - 35 * Math.floor(i / 3)}%, var(--surface-2))`);
      return out;
    }
    const nums = s => (s || '').split(',').map(x => parseFloat(x.replace(/[^\d.\-]/g, ''))).filter(x => isFinite(x));
    const labs = s => (s || '').split(',').map(x => x.trim());
    const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
    function renderCharts(root){
      root.querySelectorAll('.pie[data-values]').forEach(el => {
        const v = nums(el.dataset.values), L = labs(el.dataset.labels), unit = el.dataset.unit || '%';
        const sum = v.reduce((a, b) => a + b, 0) || 1, col = chartColors(v.length), R = 150, C = 2 * Math.PI * R;
        let acc = 0, segs = '';
        v.forEach((x, i) => { const len = x / sum * C; segs += `<circle class="pie-seg" r="${R}" cx="200" cy="200" fill="none" style="stroke:${col[i]}" stroke-width="${el.classList.contains('solid') ? 300 : 70}" stroke-dasharray="${len} ${C - len}" stroke-dashoffset="${-acc}" transform="rotate(-90 200 200)"/>`; acc += len; });
        const center = el.dataset.center ? `<div class="pie-center">${esc(el.dataset.center)}</div>` : '';
        const legend = v.map((x, i) => `<li><i style="background:${col[i]}"></i><span>${esc(L[i] || '')}</span><b>${esc(x)}${esc(unit)}</b></li>`).join('');
        el.innerHTML = `<div class="pie-fig"><svg viewBox="0 0 400 400">${segs}</svg>${center}</div><ul class="pie-legend">${legend}</ul>`;
        el.setAttribute('data-done', '1');
      });
      root.querySelectorAll('.lc[data-values]').forEach(el => {
        const v = nums(el.dataset.values), L = labs(el.dataset.labels), unit = el.dataset.unit || '';
        if (v.length < 2) return;
        const W = Math.round(el.clientWidth / (parseFloat(getComputedStyle(el).zoom) || 1)) || 1200, H = 420, pad = 50, max = Math.max(...v), min = Math.min(0, ...v);
        const x = i => pad + i * (W - 2 * pad) / (v.length - 1), y = val => H - 40 - (val - min) / ((max - min) || 1) * (H - 110);
        const pts = v.map((val, i) => `${x(i)},${y(val)}`).join(' ');
        const grid = [0, .25, .5, .75, 1].map(k => `<line x1="${pad}" x2="${W - pad}" y1="${H - 40 - k * (H - 110)}" y2="${H - 40 - k * (H - 110)}" class="lc-grid"/>`).join('');
        const dots = v.map((val, i) => `<circle cx="${x(i)}" cy="${y(val)}" r="9" class="lc-dot${i === v.length - 1 ? ' hi' : ''}"/>`).join('');
        const tags = v.map((val, i) => `<span class="lc-val${i === v.length - 1 ? ' hi' : ''}" style="left:${x(i) / W * 100}%;top:${(y(val) - 22) / H * 100}%">${esc(val.toLocaleString('ko-KR'))}${esc(unit)}</span>` +
          `<span class="lc-lab" style="left:${x(i) / W * 100}%">${esc(L[i] || '')}</span>`).join('');
        el.innerHTML = `<svg viewBox="0 0 ${W} ${H}">${grid}<polygon class="lc-area" points="${pad},${H - 40} ${pts} ${W - pad},${H - 40}"/><polyline class="lc-line" points="${pts}"/>${dots}</svg>${tags}`;
        el.setAttribute('data-done', '1');
      });
    }
    try { renderCharts(deck); } catch(e) {}
    window.__gyeolCharts = renderCharts;
    if (!slides.length) return;

    /* 1600×900 고정 캔버스를 창 크기에 맞춰 축소/확대 (파워포인트처럼) */
    function fitDeck() {
      const sc = Math.min(window.innerWidth / 1600, window.innerHeight / 900);
      deck.style.transform = 'scale(' + sc + ')';
      deck.style.left = Math.max(0, (window.innerWidth - 1600 * sc) / 2) + 'px';
      deck.style.top = Math.max(0, (window.innerHeight - 900 * sc) / 2) + 'px';
    }
    fitDeck();
    window.addEventListener('resize', fitDeck);

    /* 내용이 슬라이드 밖으로 넘치면 그 슬라이드만 자동 축소 */
    /* 장식 도형(::before/::after)은 빼고 실제 내용 상자만 잰다 */
    function contentBox(s) {
      const k = s.getBoundingClientRect().width / s.offsetWidth || 1;  // 창 크기에 맞춘 배율 제거
      let t = Infinity, b = -Infinity, l = Infinity, r = -Infinity;
      for (const el of s.children) {
        if (el.matches('aside.notes,.notes,.g-footer,.g-logo')) continue;
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.position === 'absolute' || cs.position === 'fixed') continue;
        const q = el.getBoundingClientRect();
        if (!q.width && !q.height) continue;
        const mt = parseFloat(cs.marginTop) || 0, mb = parseFloat(cs.marginBottom) || 0;
        t = Math.min(t, q.top - Math.max(0, mt) * k); b = Math.max(b, q.bottom + Math.max(0, mb) * k);
        l = Math.min(l, q.left); r = Math.max(r, q.right);
      }
      return t === Infinity ? null : { h: (b - t) / k, w: (r - l) / k };
    }
    /* 좁은 칸의 큰 숫자(KPI)가 두 줄로 깨지면 한 줄에 들어갈 때까지 글자를 줄인다 */
    function fitBigText(s) {
      s.querySelectorAll('[data-fit-fs]').forEach(el => { el.style.fontSize = el.dataset.fitFs; el.removeAttribute('data-fit-fs'); });
      s.querySelectorAll('.card div, .card b, .card strong, .card span, .grid > div > div').forEach(el => {
        if (el.children.length && !el.querySelector(':scope > span, :scope > small, :scope > sup')) return;
        if (el.querySelector('br')) return;
        const cs = getComputedStyle(el);
        const fs = parseFloat(cs.fontSize);
        if (fs < 36 || cs.display === 'inline') return;
        const lh = parseFloat(cs.lineHeight) || fs * 1.15;
        if (el.offsetHeight < lh * 1.6) return;
        el.dataset.fitFs = el.style.fontSize || '';
        let f = fs;
        while (f > fs * 0.55) {
          f *= 0.94;
          el.style.fontSize = f.toFixed(1) + 'px';
          const nl = parseFloat(getComputedStyle(el).lineHeight) || f * 1.15;
          if (el.offsetHeight < nl * 1.6) break;
        }
      });
    }
    function fitContent(s) {
      if (!s || getComputedStyle(s).display === 'none') return;
      s.style.removeProperty('--fit');
      fitBigText(s);
      const cs = getComputedStyle(s);
      const availH = s.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      const availW = s.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      const box = contentBox(s);
      if (!box || availH <= 0) return;
      const over = Math.max(box.h / availH, box.w / availW);
      if (over > 1.005) { s.style.setProperty('--fit', Math.max(0.6, 0.99 / over).toFixed(3)); return; }
      // 내용이 슬라이드를 덜 채우면 넘치지 않는 범위에서 키운다 (표지·인용·간지처럼 일부러 비운 슬라이드는 제외)
      if (box.h / availH < 0.72 && s.querySelector('.card, .grid, ul, ol, table, .steps')) {
        for (const k of [1.3, 1.22, 1.15, 1.08]) {
          s.style.setProperty('--fit', k);
          fitBigText(s);
          const b = contentBox(s);
          if (b && b.h / availH <= 0.9 && b.w / availW <= 1.0) return;
        }
        s.style.removeProperty('--fit');
        fitBigText(s);
      }
    }
    function fitAll() { slides.forEach(fitContent); }
    window.__gyeolFit = fitContent;
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitAll);
    window.addEventListener('load', fitAll);

    const previewOnlyIdx = getPreviewIdx();
    const isPreviewMode = previewOnlyIdx >= 0 && previewOnlyIdx < slides.length;

    if (isPreviewMode) {
      function showSlide(i) {
        deck.style.counterReset = 'sl ' + i;  // 숨긴 슬라이드는 번호를 세지 않으므로 직접 맞춤
        slides.forEach((s, j) => {
          const active = (j === i);
          s.classList.toggle('is-active', active);
          s.style.display = active ? '' : 'none';
          if (active) {
            s.style.opacity = '1';
            s.style.transform = 'none';
            s.style.pointerEvents = 'auto';
          }
        });
      }
      showSlide(previewOnlyIdx);
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(function(){ fitContent(slides[previewOnlyIdx]); });

      const hideSel = '.progress-bar, .notes-overlay, .overview, .notes, aside.notes, .speaker-notes';
      document.querySelectorAll(hideSel).forEach(el => { el.style.display = 'none'; });
      document.documentElement.setAttribute('data-preview', '1');
      document.body.setAttribute('data-preview', '1');

      function getPreviewThemeBase() {
        const base = document.documentElement.getAttribute('data-theme-base');
        if (base) return base;
        const tl = document.getElementById('theme-link');
        if (tl) {
          const raw = tl.getAttribute('href') || '';
          const ls = raw.lastIndexOf('/');
          if (ls >= 0) return raw.substring(0, ls + 1);
        }
        return 'assets/themes/';
      }
      const previewThemeBase = getPreviewThemeBase();

      window.addEventListener('message', function(e) {
        if (!e.data) return;
        if (e.data.type === 'preview-goto') {
          const n = parseInt(e.data.idx, 10);
          if (n >= 0 && n < slides.length) showSlide(n);
        } else if (e.data.type === 'preview-theme' && e.data.name) {
          let link = document.getElementById('theme-link');
          if (!link) {
            link = document.createElement('link');
            link.rel = 'stylesheet';
            link.id = 'theme-link';
            document.head.appendChild(link);
          }
          link.href = previewThemeBase + e.data.name + '.css';
          document.documentElement.setAttribute('data-theme', e.data.name);
        }
      });

      try { window.parent && window.parent.postMessage({ type: 'preview-ready' }, '*'); } catch(e) {}
      return;
    }

    let idx = 0;
    const total = slides.length;

    const CHANNEL_NAME = 'gyeol-presenter-' + location.pathname;
    let bc;
    try { bc = new BroadcastChannel(CHANNEL_NAME); } catch(e) { bc = null; }

    const isPresenterWindow = false;

    let bar = document.querySelector('.progress-bar');
    if (!bar) {
      bar = document.createElement('div');
      bar.className = 'progress-bar';
      bar.innerHTML = '<span></span>';
      document.body.appendChild(bar);
    }
    const barFill = bar.querySelector('span');

    let notes = document.querySelector('.notes-overlay');
    if (!notes) {
      notes = document.createElement('div');
      notes.className = 'notes-overlay';
      document.body.appendChild(notes);
    }

    let overview = document.querySelector('.overview');
    if (!overview) {
      overview = document.createElement('div');
      overview.className = 'overview';
      slides.forEach((s, i) => {
        const t = document.createElement('div');
        t.className = 'thumb';

        t.style.padding = '0 0 56.25% 0';
        t.style.height = '0';
        t.style.position = 'relative';
        t.style.overflow = 'hidden';

        const title = s.getAttribute('data-title') ||
          (s.querySelector('h1,h2,h3')||{}).textContent || ('Slide '+(i+1));

        const mini = document.createElement('div');
        mini.className = 'mini-slide';
        mini.style.position = 'absolute';
        mini.style.top = '0';
        mini.style.left = '0';
        mini.style.width = '1600px';
        mini.style.height = '900px';
        mini.style.transformOrigin = 'top left';
        mini.style.pointerEvents = 'none';
        mini.style.background = 'var(--bg)';

        const clone = s.cloneNode(true);
        clone.className = 'slide is-active';
        clone.style.position = 'absolute';
        clone.style.inset = '0';
        clone.style.transform = 'none';
        clone.style.opacity = '1';
        clone.style.padding = '72px 96px';

        mini.appendChild(clone);
        t.appendChild(mini);

        const overlay = document.createElement('div');
        overlay.style.position = 'absolute';
        overlay.style.inset = '0';
        overlay.style.background = 'linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, transparent 40%, transparent 60%, rgba(0,0,0,0.8) 100%)';
        overlay.style.color = '#fff';
        overlay.style.zIndex = '10';
        overlay.style.pointerEvents = 'none';

        const n = document.createElement('div');
        n.className = 'n';
        n.textContent = i + 1;
        n.style.position = 'absolute';
        n.style.top = '12px';
        n.style.left = '16px';
        n.style.fontWeight = '700';
        n.style.fontSize = '16px';
        n.style.color = '#fff';
        n.style.textShadow = '0 1px 4px rgba(0,0,0,0.8)';

        const text = document.createElement('div');
        text.className = 't';
        text.textContent = title.trim().slice(0,80);
        text.style.position = 'absolute';
        text.style.bottom = '12px';
        text.style.left = '16px';
        text.style.right = '16px';
        text.style.fontWeight = '600';
        text.style.fontSize = '14px';
        text.style.color = '#fff';
        text.style.textShadow = '0 1px 4px rgba(0,0,0,0.8)';

        overlay.appendChild(n);
        overlay.appendChild(text);
        t.appendChild(overlay);

        t.addEventListener('click', () => { go(i); toggleOverview(false); });
        overview.appendChild(t);
      });
      document.body.appendChild(overview);
    }

    /* ===== 자동 애니메이션 ===== */
    function motionLevel(){
      if (window.__noMotion || document.documentElement.getAttribute('data-preview')) return '';
      return (getComputedStyle(document.documentElement).getPropertyValue('--gyeol-motion') || '').trim().replace(/["']/g,'');
    }
    const MOTION_BOX = '.grid,.chev,.funnel,.pyramid,.stair,.swot,.mx,.hub,.pricing,.pc,.numlist,.tl,.stack,.vbars,.cycle,.venn,.team,.feat,.voice,.ms,.org,.org-row,.contact,.agenda,tbody,ul,ol,.row';
    let motionBase = 0, motionEnd = 0; const counters = [];
    function playMotion(slide){
      const lv = motionLevel();
      slide.getAnimations({subtree:true}).forEach(a => { if (a.id === 'gm') a.cancel(); });
      if (!lv || lv === 'none') return;
      const rich = lv === 'rich';
      const ease = 'cubic-bezier(.2,.7,.2,1)';
      let t = rich ? 120 : 60;
      const step = rich ? 130 : 80;
      motionBase = performance.now(); counters.length = 0; motionEnd = 0;
      const run = (el, kf, dur, delay, easing) => { const a = el.animate(kf, {duration: dur, delay: delay, easing: easing || ease, fill: 'both'}); a.id = 'gm'; motionEnd = Math.max(motionEnd, delay + dur); };
      const fadeUp = (el, d) => run(el, [{opacity:0, translate:'0 ' + (rich ? 34 : 18) + 'px'}, {opacity:1, translate:'0 0'}], rich ? 700 : 520, d);
      // 1) 머리글
      const head = [...slide.children].filter(el => el.matches('.kicker,h1,h2,h3,.h1,.h2,.lede,p') && !el.matches('.notes'));
      head.forEach(el => {
        const n = (el.textContent || '').trim().length;
        // 화려하게: 짧은 제목은 한 글자씩 드러나고, 긴 제목은 왼쪽부터 닦아내듯
        if (rich && el.matches('h1,h2,.h1,.h2') && n && n <= 28) run(el, [{opacity:1, clipPath:'inset(0 100% 0 0)'}, {opacity:1, clipPath:'inset(0 0 0 0)'}], Math.max(500, n * 55), t, `steps(${n}, end)`);
        else if (rich && el.matches('h1,h2,.h1,.h2')) run(el, [{opacity:0, clipPath:'inset(0 100% 0 0)'}, {opacity:1, clipPath:'inset(0 0 0 0)'}], 800, t);
        else fadeUp(el, t);
        t += step;
      });
      // 꾸밈: 큰 배경 글자는 천천히 번지고, 블롭·배지는 커지며 등장
      slide.querySelectorAll(':scope>.ghost').forEach(el => run(el, [{opacity:0, letterSpacing:'.2em'}, {opacity:1, letterSpacing:'-.04em'}], rich ? 1400 : 900, 0));
      slide.querySelectorAll(':scope>.blob,.badge').forEach(el => run(el, [{opacity:0, scale:'.5'}, {opacity:1, scale:'1'}], 800, 100));
      slide.querySelectorAll(':scope>.sect>b').forEach(el => run(el, [{opacity:0, translate:'-60px 0'}, {opacity:1, translate:'0 0'}], 700, 0));
      // 2) 내용 묶음: 바깥 묶음만 골라 그 안의 항목을 차례로
      const boxes = [...slide.querySelectorAll(MOTION_BOX)].filter(b => !b.closest('aside') && !b.parentElement.closest(MOTION_BOX));
      boxes.forEach(box => {
        let items = [...box.children].filter(c => !c.matches('aside,script,style'));
        if (box.matches('.row') && items.length < 2) items = [box];
        items.forEach(el => {
          if (el.matches('.vb')) run(el, [{opacity:0, scale:'1 0', transformOrigin:'50% 100%'}, {opacity:1, scale:'1 1', transformOrigin:'50% 100%'}], 700, t);
          else if (el.matches('.st')) run(el, [{opacity:0, scale:'1 .2', transformOrigin:'50% 100%'}, {opacity:1, scale:'1 1', transformOrigin:'50% 100%'}], 650, t);
          else if (el.matches('.fn-row')) run(el, [{opacity:0, scale:'.3 1'}, {opacity:1, scale:'1 1'}], 600, t);
          else if (el.matches('.chev-item')) run(el, [{opacity:0, translate:'-40px 0'}, {opacity:1, translate:'0 0'}], 560, t);
          else if (el.matches('.cy-node,.cy-core,.hub-core,.vn,.vn-mid,.tm,.org-top,.org-node')) run(el, [{opacity:0, scale:'.6'}, {opacity:1, scale:'1'}], 600, t);
          else if (el.matches('.mi')) run(el, [{opacity:0, translate:'0 ' + (el.matches(':nth-child(even)') ? '-30px' : '30px')}, {opacity:1, translate:'0 0'}], 600, t);
          else if (el.matches('.ft,.ct,.ag')) run(el, [{opacity:0, translate:'-30px 0'}, {opacity:1, translate:'0 0'}], 520, t);
          else if (rich) run(el, [{opacity:0, translate:'0 40px', scale:'.96'}, {opacity:1, translate:'0 0', scale:'1'}], 700, t);
          else fadeUp(el, t);
          t += step;
        });
      });
      // 3) 따로 놓인 요소(사진·그림·남은 블록)
      [...slide.children].filter(el => !head.includes(el) && !boxes.includes(el) && !el.matches('aside,.notes,script,style,.g-footer,.g-logo') && !el.querySelector(MOTION_BOX))
        .forEach(el => { if (el.matches('.g-photo')) run(el, [{opacity:0, scale:'1.06'}, {opacity:1, scale:'1'}], 900, 0); else { fadeUp(el, t); t += step; } });
      // 데이터 차트: 원형 조각이 차례로 그려지고, 선 그래프는 왼쪽부터 그려짐
      slide.querySelectorAll('.pie-seg').forEach((c, i) => {
        const da = c.getAttribute('stroke-dasharray').split(' ').map(parseFloat);
        run(c, [{strokeDasharray: `0 ${da[0] + da[1]}`}, {strokeDasharray: `${da[0]} ${da[1]}`}], 700, Math.min(t, 700) + i * 160);
      });
      slide.querySelectorAll('.lc-line').forEach(l => {
        const len = l.getTotalLength ? l.getTotalLength() : 2000;
        run(l, [{strokeDasharray: `${len}`, strokeDashoffset: `${len}`}, {strokeDasharray: `${len}`, strokeDashoffset: '0'}], rich ? 1500 : 1100, Math.min(t, 700));
      });
      slide.querySelectorAll('.lc-area').forEach(a => run(a, [{opacity: 0}, {opacity: 1}], 900, Math.min(t, 700) + 600));
      // 4) 원형 게이지 차오름
      slide.querySelectorAll('.ring').forEach(r => {
        const p = parseFloat(getComputedStyle(r).getPropertyValue('--p')) || 0;
        run(r, [{'--p': 0}, {'--p': p}], 1100, Math.min(t, 900));
      });
      // 5) 큰 숫자 세기(글자 48px 이상, 숫자만 있는 요소)
      slide.querySelectorAll('b,div,span,strong,h3').forEach(el => {
        if (el.children.length || el.closest('aside')) return;
        const txt = (el.textContent || '').trim();
        const m = /^([^\d\-]*)(-?[\d,]+(?:\.\d+)?)(.*)$/.exec(txt);
        if (!m || txt.length > 14 || parseFloat(getComputedStyle(el).fontSize) < 48) return;
        const target = parseFloat(m[2].replace(/,/g, '')); if (!isFinite(target) || target === 0) return;
        const dec = (m[2].split('.')[1] || '').length, comma = m[2].includes(',');
        const fmt = v => { let s = v.toFixed(dec); if (comma) s = Number(s).toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec}); return m[1] + s + m[3]; };
        const delay = Math.min(t, 600), dur = rich ? 1400 : 1000;
        el.textContent = fmt(0);
        counters.push({el, delay, dur, target, fmt, txt});
        motionEnd = Math.max(motionEnd, delay + dur);
      });
      if (counters.length) requestAnimationFrame(updateCounters);
    }
    // 숫자 세기는 공통 시계로 갱신 → 영상 녹화 때 원하는 시점으로 맞출 수 있다
    function motionClock(){ return window.__vclock != null ? window.__vclock : performance.now() - motionBase; }
    function updateCounters(){
      const now = motionClock(); let live = false;
      counters.forEach(c => {
        const k = Math.max(0, Math.min(1, (now - c.delay) / c.dur));
        c.el.textContent = k >= 1 ? c.txt : c.fmt(c.target * (1 - Math.pow(1 - k, 3)));
        if (k < 1) live = true;
      });
      if (live && window.__vclock == null) requestAnimationFrame(updateCounters);
    }
    window.__gyeolMotion = playMotion;
    // 영상 녹화용: 현재 화면의 모든 애니메이션(전환·등장·숫자)을 ms 시점으로 맞춘다
    window.__gyeolSeek = function(ms){
      window.__vclock = ms;
      document.getAnimations().forEach(a => { try { a.pause(); a.currentTime = ms; } catch(e) {} });
      updateCounters();
      return motionEnd;
    };
    window.__gyeolMotionEnd = () => motionEnd;

    function go(n, fromRemote){
      n = Math.max(0, Math.min(total-1, n));
      slides.forEach((s,i) => {
        s.classList.toggle('is-active', i===n);
        s.classList.toggle('is-prev', i<n);
      });
      idx = n;
      barFill.style.width = ((n+1)/total*100)+'%';
      const numEl = document.querySelector('.slide-number');
      if (numEl) { numEl.setAttribute('data-current', n+1); numEl.setAttribute('data-total', total); }

      const note = slides[n].querySelector('.notes, aside.notes, .speaker-notes');
      notes.innerHTML = note ? note.innerHTML : '';

      const hashTarget = '#/'+(n+1);
      if (location.hash !== hashTarget && !isPresenterWindow) {
        history.replaceState(null,'', hashTarget);
      }

      slides[n].querySelectorAll('[data-anim]').forEach(el => {
        const a = el.getAttribute('data-anim');
        el.classList.remove('anim-'+a);
        void el.offsetWidth;
        el.classList.add('anim-'+a);
      });

      slides[n].querySelectorAll('.counter').forEach(el => {
        const target = parseFloat(el.getAttribute('data-to')||el.textContent);
        const dur = parseInt(el.getAttribute('data-dur')||'1200',10);
        const start = performance.now();
        const from = 0;
        function tick(now){
          const t = Math.min(1,(now-start)/dur);
          const v = from + (target-from)*(1-Math.pow(1-t,3));
          el.textContent = (target % 1 === 0) ? Math.round(v) : v.toFixed(1);
          if (t<1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      });

      // 자동 애니메이션(표시 설정 '애니메이션'): 제목 → 내용 순서로 등장, 막대·게이지·숫자는 차오름
      try { playMotion(slides[n]); } catch(e) {}

      // 편집 화면(부모 창)에 현재 슬라이드 알림
      try { if (window.parent !== window) window.parent.postMessage({ type: 'deck-go', idx: n, total: total }, '*'); } catch(e) {}

      if (!fromRemote && bc) {
        bc.postMessage({ type: 'go', idx: n });
      }
    }

    if (bc) {
      bc.onmessage = function(e) {
        if (!e.data) return;
        if (e.data.type === 'go' && typeof e.data.idx === 'number') {
          go(e.data.idx, true);
        } else if (e.data.type === 'theme' && e.data.name) {

          const i = themes.indexOf(e.data.name);
          if (i >= 0) themeIdx = i;
          applyTheme(e.data.name);
        }
      };
    }

    function toggleNotes(force){ notes.classList.toggle('open', force!==undefined?force:!notes.classList.contains('open')); }
    function toggleOverview(force){
      const isOpen = force!==undefined ? force : !overview.classList.contains('open');
      overview.classList.toggle('open', isOpen);
      if (isOpen) {
        requestAnimationFrame(() => {
          const thumbs = overview.querySelectorAll('.thumb');
          if (thumbs.length) {
            const scale = thumbs[0].clientWidth / 1600;
            overview.querySelectorAll('.mini-slide').forEach(m => {
              m.style.transform = 'scale(' + scale + ')';
            });
          }
        });
      }
    }

    /* Opens a new window with 4 draggable, resizable cards:
     *   CURRENT  — iframe(?preview=N)   pixel-perfect preview of current slide
     *   NEXT     — iframe(?preview=N+1) pixel-perfect preview of next slide
     *   SCRIPT   — large speaker notes (발표 대본)
     *   TIMER    — elapsed timer + page counter + controls
     * Cards remember position/size in localStorage.
     * Two windows sync via BroadcastChannel.
     */
    let presenterWin = null;
    /* 발표자 창 문구: 결 화면이 영어이거나(앱 안), 내보낸 슬라이드에 한글이 없으면 영어로 */
    const PRESENTER_EN = [
      ['현재 슬라이드', 'Current slide'], ['다음 슬라이드', 'Next slide'], ['발표 대본 (Speaker Notes)', 'Speaker notes'], ['발표 타이머', 'Timer'],
      ['<span class="label">슬라이드</span>', '<span class="label">Slide</span>'], ['← 이전', '← Prev'], ['다음 →', 'Next →'], ['⏱ 초기화', '⏱ Reset'],
      ['슬라이드 이동', 'Move slides'], ['타이머 초기화', 'Reset timer'], ['<kbd>Esc</kbd> 닫기', '<kbd>Esc</kbd> Close'],
      ['카드 상단 드래그로 이동 · 우측 하단 핸들로 크기 조절', 'Drag a card header to move · drag the corner to resize'], ['레이아웃 초기화', 'Reset layout'],
      ['(이 슬라이드에는 작성된 발표 대본이 없습니다)', '(No speaker notes for this slide)'], ['기본 카드 레이아웃으로 초기화하시겠습니까?', 'Reset to the default card layout?']
    ];
    function presenterEnglish() {
      try { const v = window.top.document.documentElement.getAttribute('data-ui-lang-resolved'); if (v) return v === 'en'; } catch (e) {}
      const d = document.querySelector('.deck');
      return !!d && !/[가-힣]/.test(d.textContent || '');
    }

    function openPresenterWindow(preopened) {
      if (preopened && presenterWin && !presenterWin.closed && preopened !== presenterWin) { try { preopened.close(); } catch(e) {} }
      if (presenterWin && !presenterWin.closed) {
        presenterWin.focus();
        return;
      }

      const deckUrl = location.protocol + '//' + location.host + location.pathname;

      const slideMeta = slides.map((s, i) => {
        const note = s.querySelector('.notes, aside.notes, .speaker-notes');
        return {
          title: s.getAttribute('data-title') ||
            (s.querySelector('h1,h2,h3')||{}).textContent || ('Slide '+(i+1)),
          notes: note ? note.innerHTML : ''
        };
      });

      const currentTheme = root.getAttribute('data-theme') || (themes[themeIdx] || '');
      let presenterHTML = buildPresenterHTML(deckUrl, slideMeta, total, idx, CHANNEL_NAME, currentTheme);
      if (presenterEnglish()) for (const [ko, en] of PRESENTER_EN) presenterHTML = presenterHTML.split(ko).join(en);

      presenterWin = preopened || window.open('', 'gyeol-presenter', 'width=1280,height=820,menubar=no,toolbar=no');
      if (!presenterWin) {
        alert(presenterEnglish() ? 'Allow pop-up windows in your browser to use presenter mode.' : '발표자 모드를 사용하려면 브라우저의 팝업 창을 허용해 주세요.');
        return;
      }
      presenterWin.document.open();
      presenterWin.document.write(presenterHTML);
      presenterWin.document.close();
    }

    function buildPresenterHTML(deckUrl, slideMeta, total, startIdx, channelName, currentTheme) {
      const metaJSON = JSON.stringify(slideMeta);
      const deckUrlJSON = JSON.stringify(deckUrl);
      const channelJSON = JSON.stringify(channelName);
      const themeJSON = JSON.stringify(currentTheme || '');
      const storageKey = 'gyeol-presenter:' + location.pathname;

      return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Presenter View</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    width: 100%; height: 100%; overflow: hidden;
    background: #1a1d24;
    background-image:
      radial-gradient(circle at 20% 30%, rgba(88,166,255,.04), transparent 50%),
      radial-gradient(circle at 80% 70%, rgba(188,140,255,.04), transparent 50%);
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", sans-serif;
  }
  /* Stage: positioned area where cards live */
  #stage { position: absolute; inset: 0; overflow: hidden; }

  /* Magnetic card */
  .pcard {
    position: absolute;
    background: #0d1117;
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.02);
    display: flex; flex-direction: column;
    overflow: hidden;
    min-width: 180px; min-height: 100px;
    transition: box-shadow .2s, border-color .2s;
  }
  .pcard.dragging { box-shadow: 0 16px 48px rgba(0,0,0,.6), 0 0 0 2px rgba(88,166,255,.5); border-color: #58a6ff; transition: none; z-index: 9999; }
  .pcard.resizing { box-shadow: 0 16px 48px rgba(0,0,0,.6), 0 0 0 2px rgba(63,185,80,.5); border-color: #3fb950; transition: none; z-index: 9999; }
  .pcard:hover { border-color: rgba(88,166,255,.3); }

  /* Card header (drag handle) */
  .pcard-head {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 12px;
    background: rgba(255,255,255,.04);
    border-bottom: 1px solid rgba(255,255,255,.06);
    cursor: move;
    user-select: none;
    flex-shrink: 0;
  }
  .pcard-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--dot-color, #58a6ff); flex-shrink: 0; }
  .pcard-title {
    font-size: 11px; letter-spacing: .15em; text-transform: uppercase;
    font-weight: 700; color: #8b949e; flex: 1;
  }
  .pcard-meta { font-size: 11px; color: #6e7681; }

  /* Card body */
  .pcard-body { flex: 1; position: relative; overflow: hidden; min-height: 0; }

  /* Preview cards (CURRENT/NEXT) — iframe-based pixel-perfect render */
  .pcard-preview .pcard-body { background: #000; }
  .pcard-preview iframe {
    position: absolute; top: 0; left: 0;
    width: 1920px; height: 1080px;
    border: none;
    transform-origin: top left;
    pointer-events: none;
    background: transparent;
  }
  .pcard-preview .preview-end {
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    color: #484f58; font-size: 14px; letter-spacing: .12em;
  }

  /* Notes card */
  .pcard-notes .pcard-body {
    padding: 14px 18px;
    overflow-y: auto;
    font-size: 18px; line-height: 1.75;
    color: #d0d7de;
    font-family: "Noto Sans SC", -apple-system, sans-serif;
  }
  .pcard-notes .pcard-body p { margin: 0 0 .7em 0; }
  .pcard-notes .pcard-body strong { color: #f0883e; }
  .pcard-notes .pcard-body em { color: #58a6ff; font-style: normal; }
  .pcard-notes .pcard-body code {
    font-family: "SF Mono", monospace; font-size: .9em;
    background: rgba(255,255,255,.08); padding: 1px 6px; border-radius: 4px;
  }
  .pcard-notes .empty { color: #484f58; font-style: italic; }

  /* Timer card */
  .pcard-timer .pcard-body {
    display: flex; flex-direction: column; gap: 14px;
    padding: 18px 20px; justify-content: center;
  }
  .timer-display {
    font-family: "SF Mono", "JetBrains Mono", monospace;
    font-size: 42px; font-weight: 700;
    color: #3fb950;
    letter-spacing: .04em;
    line-height: 1;
  }
  .timer-row {
    display: flex; align-items: center; gap: 12px;
    font-size: 14px; color: #8b949e;
  }
  .timer-row .label { font-size: 10px; letter-spacing: .15em; text-transform: uppercase; color: #6e7681; }
  .timer-row .val { color: #e6edf3; font-weight: 600; font-family: "SF Mono", monospace; }
  .timer-controls { display: flex; gap: 8px; flex-wrap: wrap; }
  .timer-btn {
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.1);
    color: #e6edf3;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    font-family: inherit;
  }
  .timer-btn:hover { background: rgba(88,166,255,.15); border-color: #58a6ff; }
  .timer-btn:active { transform: translateY(1px); }

  /* Resize handle */
  .pcard-resize {
    position: absolute; right: 0; bottom: 0;
    width: 18px; height: 18px;
    cursor: nwse-resize;
    background: linear-gradient(135deg, transparent 50%, rgba(255,255,255,.25) 50%, rgba(255,255,255,.25) 60%, transparent 60%, transparent 70%, rgba(255,255,255,.25) 70%, rgba(255,255,255,.25) 80%, transparent 80%);
    z-index: 5;
  }
  .pcard-resize:hover { background: linear-gradient(135deg, transparent 50%, #58a6ff 50%, #58a6ff 60%, transparent 60%, transparent 70%, #58a6ff 70%, #58a6ff 80%, transparent 80%); }

  /* Bottom hint bar */
  .hint-bar {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: rgba(0,0,0,.6);
    backdrop-filter: blur(10px);
    border-top: 1px solid rgba(255,255,255,.08);
    padding: 6px 16px;
    font-size: 11px; color: #8b949e;
    display: flex; gap: 18px; align-items: center;
    z-index: 1000;
  }
  .hint-bar kbd {
    background: rgba(255,255,255,.08);
    padding: 1px 6px; border-radius: 3px;
    font-family: "SF Mono", monospace;
    font-size: 10px;
    border: 1px solid rgba(255,255,255,.1);
    color: #e6edf3;
  }
  .hint-bar .reset-layout {
    margin-left: auto;
    background: transparent; border: 1px solid rgba(255,255,255,.15);
    color: #8b949e; padding: 3px 10px; border-radius: 4px;
    font-size: 11px; cursor: pointer; font-family: inherit;
  }
  .hint-bar .reset-layout:hover { background: rgba(248,81,73,.15); border-color: #f85149; color: #f85149; }

  body.is-dragging-card * { user-select: none !important; }
  body.is-dragging-card iframe { pointer-events: none !important; }
</style>
</head>
<body>

<div id="stage">
  <div class="pcard pcard-preview" id="card-cur" style="--dot-color:#58a6ff">
    <div class="pcard-head" data-drag>
      <span class="pcard-dot"></span>
      <span class="pcard-title">현재 슬라이드</span>
      <span class="pcard-meta" id="cur-meta">—</span>
    </div>
    <div class="pcard-body"><iframe id="iframe-cur"></iframe></div>
    <div class="pcard-resize" data-resize></div>
  </div>

  <div class="pcard pcard-preview" id="card-nxt" style="--dot-color:#bc8cff">
    <div class="pcard-head" data-drag>
      <span class="pcard-dot"></span>
      <span class="pcard-title">다음 슬라이드</span>
      <span class="pcard-meta" id="nxt-meta">—</span>
    </div>
    <div class="pcard-body"><iframe id="iframe-nxt"></iframe></div>
    <div class="pcard-resize" data-resize></div>
  </div>

  <div class="pcard pcard-notes" id="card-notes" style="--dot-color:#f0883e">
    <div class="pcard-head" data-drag>
      <span class="pcard-dot"></span>
      <span class="pcard-title">발표 대본 (Speaker Notes)</span>
    </div>
    <div class="pcard-body" id="notes-body"></div>
    <div class="pcard-resize" data-resize></div>
  </div>

  <div class="pcard pcard-timer" id="card-timer" style="--dot-color:#3fb950">
    <div class="pcard-head" data-drag>
      <span class="pcard-dot"></span>
      <span class="pcard-title">발표 타이머</span>
    </div>
    <div class="pcard-body">
      <div class="timer-display" id="timer-display">00:00</div>
      <div class="timer-row">
        <span class="label">슬라이드</span>
        <span class="val" id="timer-count">1 / ${total}</span>
      </div>
      <div class="timer-controls">
        <button class="timer-btn" id="btn-prev">← 이전</button>
        <button class="timer-btn" id="btn-next">다음 →</button>
        <button class="timer-btn" id="btn-reset">⏱ 초기화</button>
      </div>
    </div>
    <div class="pcard-resize" data-resize></div>
  </div>
</div>

<div class="hint-bar">
  <span><kbd>← →</kbd> 슬라이드 이동</span>
  <span><kbd>R</kbd> 타이머 초기화</span>
  <span><kbd>Esc</kbd> 닫기</span>
  <span style="color:#6e7681">카드 상단 드래그로 이동 · 우측 하단 핸들로 크기 조절</span>
  <button class="reset-layout" id="reset-layout">레이아웃 초기화</button>
</div>

<script>
(function(){
  var slideMeta = ${metaJSON};
  var total = ${total};
  var idx = ${startIdx};
  var deckUrl = ${deckUrlJSON};
  var STORAGE_KEY = ${JSON.stringify(storageKey)};
  var bc;
  try { bc = new BroadcastChannel(${channelJSON}); } catch(e) {}

  var iframeCur = document.getElementById('iframe-cur');
  var iframeNxt = document.getElementById('iframe-nxt');
  var notesBody = document.getElementById('notes-body');
  var curMeta = document.getElementById('cur-meta');
  var nxtMeta = document.getElementById('nxt-meta');
  var timerDisplay = document.getElementById('timer-display');
  var timerCount = document.getElementById('timer-count');

  /* ===== Default card layout ===== */
  function defaultLayout() {
    var w = window.innerWidth;
    var h = window.innerHeight - 36; /* leave room for hint bar */
    return {
      'card-cur':   { x: 16,        y: 16,            w: Math.round(w*0.55) - 24, h: Math.round(h*0.62) - 16 },
      'card-nxt':   { x: Math.round(w*0.55) + 8, y: 16, w: w - Math.round(w*0.55) - 24, h: Math.round(h*0.42) - 16 },
      'card-notes': { x: Math.round(w*0.55) + 8, y: Math.round(h*0.42) + 8, w: w - Math.round(w*0.55) - 24, h: h - Math.round(h*0.42) - 16 },
      'card-timer': { x: 16,        y: Math.round(h*0.62) + 8, w: Math.round(w*0.55) - 24, h: h - Math.round(h*0.62) - 16 }
    };
  }

  /* ===== Apply / save / restore layout ===== */
  function applyLayout(layout) {
    Object.keys(layout).forEach(function(id){
      var el = document.getElementById(id);
      var l = layout[id];
      if (el && l) {
        el.style.left = l.x + 'px';
        el.style.top = l.y + 'px';
        el.style.width = l.w + 'px';
        el.style.height = l.h + 'px';
      }
    });
    rescaleAll();
  }
  function readLayout() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch(e) {}
    return defaultLayout();
  }
  function saveLayout() {
    var layout = {};
    ['card-cur','card-nxt','card-notes','card-timer'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) {
        layout[id] = {
          x: parseInt(el.style.left,10) || 0,
          y: parseInt(el.style.top,10) || 0,
          w: parseInt(el.style.width,10) || 300,
          h: parseInt(el.style.height,10) || 200
        };
      }
    });
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(layout)); } catch(e) {}
  }

  /* ===== iframe rescale to fit card body ===== */
  function rescaleIframe(iframe) {
    if (!iframe || iframe.style.display === 'none') return;
    var body = iframe.parentElement;
    var cw = body.clientWidth, ch = body.clientHeight;
    if (!cw || !ch) return;
    var s = Math.min(cw / 1920, ch / 1080);
    iframe.style.transform = 'scale(' + s + ')';
    /* Center the scaled iframe in the body */
    var sw = 1920 * s, sh = 1080 * s;
    iframe.style.left = Math.max(0, (cw - sw) / 2) + 'px';
    iframe.style.top = Math.max(0, (ch - sh) / 2) + 'px';
  }
  function rescaleAll() {
    rescaleIframe(iframeCur);
    rescaleIframe(iframeNxt);
  }
  window.addEventListener('resize', rescaleAll);

  /* ===== Drag (move card by header) ===== */
  document.querySelectorAll('[data-drag]').forEach(function(handle){
    handle.addEventListener('mousedown', function(e){
      if (e.button !== 0) return;
      var card = handle.closest('.pcard');
      if (!card) return;
      e.preventDefault();
      card.classList.add('dragging');
      document.body.classList.add('is-dragging-card');
      var startX = e.clientX, startY = e.clientY;
      var startL = parseInt(card.style.left,10) || 0;
      var startT = parseInt(card.style.top,10)  || 0;
      function onMove(ev){
        var nx = Math.max(0, Math.min(window.innerWidth - 100, startL + ev.clientX - startX));
        var ny = Math.max(0, Math.min(window.innerHeight - 50, startT + ev.clientY - startY));
        card.style.left = nx + 'px';
        card.style.top = ny + 'px';
      }
      function onUp(){
        card.classList.remove('dragging');
        document.body.classList.remove('is-dragging-card');
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        saveLayout();
      }
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  });

  /* ===== Resize (drag bottom-right corner) ===== */
  document.querySelectorAll('[data-resize]').forEach(function(handle){
    handle.addEventListener('mousedown', function(e){
      if (e.button !== 0) return;
      var card = handle.closest('.pcard');
      if (!card) return;
      e.preventDefault(); e.stopPropagation();
      card.classList.add('resizing');
      document.body.classList.add('is-dragging-card');
      var startX = e.clientX, startY = e.clientY;
      var startW = parseInt(card.style.width,10)  || card.offsetWidth;
      var startH = parseInt(card.style.height,10) || card.offsetHeight;
      function onMove(ev){
        var nw = Math.max(180, startW + ev.clientX - startX);
        var nh = Math.max(100, startH + ev.clientY - startY);
        card.style.width = nw + 'px';
        card.style.height = nh + 'px';
        if (card.querySelector('iframe')) rescaleIframe(card.querySelector('iframe'));
      }
      function onUp(){
        card.classList.remove('resizing');
        document.body.classList.remove('is-dragging-card');
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        rescaleAll();
        saveLayout();
      }
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  });

  /* ===== Preview iframe ready tracking =====
   * Each iframe loads the deck ONCE with ?preview=1 on init. Subsequent
   * slide changes are sent via postMessage('preview-goto') so the iframe
   * just toggles visibility of a different .slide — no reload, no flicker.
   */
  var iframeReady = { cur: false, nxt: false };
  var currentTheme = ${themeJSON};
  window.addEventListener('message', function(e) {
    if (!e.data || e.data.type !== 'preview-ready') return;
    var iframe = null;
    if (e.source === iframeCur.contentWindow) {
      iframeReady.cur = true;
      iframe = iframeCur;
      postPreviewGoto(iframeCur, idx);
    } else if (e.source === iframeNxt.contentWindow) {
      iframeReady.nxt = true;
      iframe = iframeNxt;
      postPreviewGoto(iframeNxt, idx + 1 < total ? idx + 1 : idx);
    }
    /* Sync current theme to the iframe */
    if (iframe && currentTheme) {
      try { iframe.contentWindow.postMessage({ type: 'preview-theme', name: currentTheme }, '*'); } catch(err) {}
    }
    if (iframe) rescaleIframe(iframe);
  });

  function postPreviewGoto(iframe, n) {
    try {
      iframe.contentWindow.postMessage({ type: 'preview-goto', idx: n }, '*');
    } catch(e) {}
  }

  /* ===== Update content =====
   * Smooth (no-reload) navigation: send postMessage to iframes instead of
   * resetting src. Iframes stay loaded, just switch visible .slide.
   */
  function update(n) {
    n = Math.max(0, Math.min(total - 1, n));
    idx = n;

    /* Current preview — postMessage (smooth) */
    if (iframeReady.cur) postPreviewGoto(iframeCur, n);
    curMeta.textContent = (n + 1) + '/' + total;

    /* Next preview */
    if (n + 1 < total) {
      iframeNxt.style.display = '';
      var endEl = document.querySelector('#card-nxt .preview-end');
      if (endEl) endEl.remove();
      if (iframeReady.nxt) postPreviewGoto(iframeNxt, n + 1);
      nxtMeta.textContent = (n + 2) + '/' + total;
    } else {
      iframeNxt.style.display = 'none';
      var body = document.querySelector('#card-nxt .pcard-body');
      if (body && !body.querySelector('.preview-end')) {
        var end = document.createElement('div');
        end.className = 'preview-end';
        end.textContent = '— END OF DECK —';
        body.appendChild(end);
      }
      nxtMeta.textContent = 'END';
    }

    /* Notes */
    var note = slideMeta[n].notes;
    notesBody.innerHTML = note || '<span class="empty">(이 슬라이드에는 작성된 발표 대본이 없습니다)</span>';

    /* Timer count */
    timerCount.textContent = (n + 1) + ' / ' + total;
  }

  /* ===== Timer ===== */
  var tStart = Date.now();
  setInterval(function(){
    var s = Math.floor((Date.now() - tStart) / 1000);
    var mm = String(Math.floor(s/60)).padStart(2,'0');
    var ss = String(s%60).padStart(2,'0');
    timerDisplay.textContent = mm + ':' + ss;
  }, 1000);
  function resetTimer(){ tStart = Date.now(); timerDisplay.textContent = '00:00'; }

  /* ===== BroadcastChannel sync ===== */
  if (bc) {
    bc.onmessage = function(e){
      if (!e.data) return;
      if (e.data.type === 'go') update(e.data.idx);
      else if (e.data.type === 'theme' && e.data.name) {
        currentTheme = e.data.name;
        /* Forward theme change to preview iframes */
        [iframeCur, iframeNxt].forEach(function(iframe){
          try {
            iframe.contentWindow.postMessage({ type: 'preview-theme', name: e.data.name }, '*');
          } catch(err) {}
        });
      }
    };
  }
  function go(n) {
    update(n);
    if (bc) bc.postMessage({ type: 'go', idx: idx });
  }

  /* ===== Buttons ===== */
  document.getElementById('btn-prev').addEventListener('click', function(){ go(idx - 1); });
  document.getElementById('btn-next').addEventListener('click', function(){ go(idx + 1); });
  document.getElementById('btn-reset').addEventListener('click', resetTimer);
  document.getElementById('reset-layout').addEventListener('click', function(){
    if (confirm('기본 카드 레이아웃으로 초기화하시겠습니까?')) {
      try { localStorage.removeItem(STORAGE_KEY); } catch(e){}
      applyLayout(defaultLayout());
    }
  });

  /* ===== Keyboard ===== */
  document.addEventListener('keydown', function(e){
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    switch(e.key) {
      case 'ArrowRight': case ' ': case 'PageDown': go(idx + 1); e.preventDefault(); break;
      case 'ArrowLeft':  case 'PageUp':   go(idx - 1); e.preventDefault(); break;
      case 'Home': go(0); break;
      case 'End':  go(total - 1); break;
      case 'r': case 'R': resetTimer(); break;
      case 'Escape': window.close(); break;
    }
  });

  /* ===== Iframe load → rescale (catches initial size) ===== */
  iframeCur.addEventListener('load', function(){ rescaleIframe(iframeCur); });
  iframeNxt.addEventListener('load', function(){ rescaleIframe(iframeNxt); });

  /* ===== Init =====
   * Load each iframe ONCE with the deck file. After they post
   * 'preview-ready', all subsequent navigation is via postMessage
   * (smooth, no reload, no flicker).
   */
  applyLayout(readLayout());
  iframeCur.src = deckUrl + '?preview=' + (idx + 1);
  if (idx + 1 < total) iframeNxt.src = deckUrl + '?preview=' + (idx + 2);
  /* Initialize notes/timer/count without touching iframes */
  notesBody.innerHTML = slideMeta[idx].notes || '<span class="empty">(이 슬라이드에는 작성된 발표 대본이 없습니다)</span>';
  curMeta.textContent = (idx + 1) + '/' + total;
  nxtMeta.textContent = (idx + 2) + '/' + total;
  timerCount.textContent = (idx + 1) + ' / ' + total;
})();
</` + `script>
</body></html>`;
    }

    function fullscreen(){ const el=document.documentElement;
      if (!document.fullscreenElement) el.requestFullscreen&&el.requestFullscreen();
      else document.exitFullscreen&&document.exitFullscreen();
    }

    const root = document.documentElement;
    const themesAttr = root.getAttribute('data-themes') || document.body.getAttribute('data-themes');
    const themes = themesAttr ? themesAttr.split(',').map(s=>s.trim()).filter(Boolean) : [];
    let themeIdx = 0;

    let themeBase = root.getAttribute('data-theme-base');
    if (!themeBase) {
      const existingLink = document.getElementById('theme-link');
      if (existingLink) {

        const rawHref = existingLink.getAttribute('href') || '';
        const lastSlash = rawHref.lastIndexOf('/');
        themeBase = lastSlash >= 0 ? rawHref.substring(0, lastSlash + 1) : 'assets/themes/';
      } else {
        themeBase = 'assets/themes/';
      }
    }

    function applyTheme(name) {
      let link = document.getElementById('theme-link');
      if (!link) {
        link = document.createElement('link');
        link.rel = 'stylesheet';
        link.id = 'theme-link';
        document.head.appendChild(link);
      }
      link.href = themeBase + name + '.css';
      root.setAttribute('data-theme', name);
      const ind = document.querySelector('.theme-indicator');
      if (ind) ind.textContent = name;
    }
    function cycleTheme(fromRemote){
      if (!themes.length) return;
      themeIdx = (themeIdx+1) % themes.length;
      const name = themes[themeIdx];
      applyTheme(name);

      if (!fromRemote && bc) bc.postMessage({ type: 'theme', name: name });
    }

    let animIdx = 0;
    function cycleAnim(){
      animIdx = (animIdx+1) % ANIMS.length;
      const a = ANIMS[animIdx];
      const target = slides[idx].querySelector('[data-anim-target]') || slides[idx];
      ANIMS.forEach(x => target.classList.remove('anim-'+x));
      void target.offsetWidth;
      target.classList.add('anim-'+a);
      target.setAttribute('data-anim', a);
      const ind = document.querySelector('.anim-indicator');
      if (ind) ind.textContent = a;
    }

    document.addEventListener('keydown', function (e) {
      if (e.metaKey||e.ctrlKey||e.altKey) return;
      switch (e.key) {
        case 'ArrowRight': case ' ': case 'PageDown': case 'Enter': go(idx+1); e.preventDefault(); break;
        case 'ArrowLeft': case 'PageUp': case 'Backspace': go(idx-1); e.preventDefault(); break;
        case 'Home': go(0); break;
        case 'End': go(total-1); break;
        case 'f': case 'F': fullscreen(); break;
        case 's': case 'S': openPresenterWindow(); break;
        case 'n': case 'N': toggleNotes(); break;
        case 'o': case 'O': toggleOverview(); break;
        case 't': case 'T': cycleTheme(); break;
        case 'a': case 'A': cycleAnim(); break;
        case 'Escape': toggleOverview(false); toggleNotes(false); break;
      }
    });

    // 편집 화면에서 직접 조작할 수 있는 API
    window.__deck = {
      go: function(n){ go(n); }, next: function(){ go(idx+1); }, prev: function(){ go(idx-1); },
      get idx(){ return idx; }, total: total,
      toggleNotes: toggleNotes, toggleOverview: toggleOverview, fullscreen: fullscreen,
      openPresenter: function(win){ openPresenterWindow(win); }
    };

    function fromHash(){
      const m = /^#\/(\d+)/.exec(location.hash||'');
      if (m) go(Math.max(0, parseInt(m[1],10)-1));
    }
    window.addEventListener('hashchange', fromHash);
    fromHash();
    go(idx);
  });
})();
