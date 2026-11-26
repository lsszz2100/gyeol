(function(){
  window.GFX = window.GFX || {};
  window.GFX['typewriter-multi'] = function(el){
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    const lines = [
      (el.getAttribute('data-fx-line1') || '> initializing knowledge graph...'),
      (el.getAttribute('data-fx-line2') || '> loading 28 concept nodes'),
      (el.getAttribute('data-fx-line3') || '> agent ready. awaiting prompt_'),
    ];
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;gap:14px;padding:32px 48px;font:600 22px ui-monospace,Menlo,monospace;color:var(--text-1,#e7e7ef);';
    el.appendChild(wrap);
    const rows = lines.map((txt) => {
      const row = document.createElement('div');
      row.style.cssText = 'white-space:pre;display:flex;align-items:center;';
      const span = document.createElement('span'); span.textContent = '';
      const cur = document.createElement('span');
      cur.textContent = '\u2588';
      cur.style.cssText = 'display:inline-block;margin-left:2px;color:var(--accent,#22d3ee);animation:gfxBlink 1s steps(2) infinite;';
      row.appendChild(span); row.appendChild(cur);
      wrap.appendChild(row);
      return {row, span, txt, i:0};
    });

    if (!document.getElementById('gfx-blink-kf')){
      const st = document.createElement('style');
      st.id = 'gfx-blink-kf';
      st.textContent = '@keyframes gfxBlink{50%{opacity:0}}';
      document.head.appendChild(st);
    }
    let stopped = false;
    const speeds = [55, 70, 45];
    rows.forEach((r, idx) => {
      const tick = () => {
        if (stopped) return;
        if (r.i < r.txt.length){
          r.span.textContent += r.txt[r.i++];
          setTimeout(tick, speeds[idx]);
        } else {
          setTimeout(() => {
            if (stopped) return;
            r.i = 0; r.span.textContent = '';
            tick();
          }, 2200);
        }
      };
      setTimeout(tick, idx*400);
    });
    return { stop(){ stopped = true; if (wrap.parentNode) wrap.parentNode.removeChild(wrap); } };
  };
})();
