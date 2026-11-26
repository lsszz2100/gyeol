(function(){
  'use strict';

  const FX_LIST = [
    '_util',
    'particle-burst','confetti-cannon','firework','starfield','matrix-rain',
    'knowledge-graph','neural-net','constellation','orbit-ring','galaxy-swirl',
    'word-cascade','letter-explode','chain-react','magnetic-field','data-stream',
    'gradient-blob','sparkle-trail','shockwave','typewriter-multi','counter-explosion'
  ];

  const myScript = document.currentScript || (function(){
    const all = document.getElementsByTagName('script');
    for (const s of all){ if (s.src && s.src.indexOf('fx-runtime.js')>-1) return s; }
    return null;
  })();
  const base = myScript ? myScript.src.replace(/fx-runtime\.js.*$/, 'fx/') : 'assets/animations/fx/';

  let loaded = 0;
  // 효과(data-fx)를 쓰는 슬라이드가 없으면 효과 스크립트 21개를 아예 불러오지 않는다 (썸네일이 많을 때 서버 과부하 방지)
  const total = document.querySelector('[data-fx]') ? FX_LIST.length : 0;
  const ready = new Promise((resolve) => {
    if (!total) return resolve();
    FX_LIST.forEach((name) => {
      const s = document.createElement('script');
      s.src = base + name + '.js';
      s.async = false;
      s.onload = s.onerror = () => { if (++loaded >= total) resolve(); };
      document.head.appendChild(s);
    });
  });

  window.__gfxActive = window.__gfxActive || new Map();

  function initFxIn(root){
    if (!window.GFX) return;
    const els = root.querySelectorAll('[data-fx]');
    els.forEach((el) => {
      if (window.__gfxActive.has(el)) return;
      const name = el.getAttribute('data-fx');
      const fn = window.GFX[name];
      if (typeof fn !== 'function') return;
      try {
        const handle = fn(el, {}) || { stop(){} };
        window.__gfxActive.set(el, handle);
      } catch(e){ console.warn('[gfx]', name, e); }
    });
  }

  function stopFxIn(root){
    const els = root.querySelectorAll('[data-fx]');
    els.forEach((el) => {
      const h = window.__gfxActive.get(el);
      if (h && typeof h.stop === 'function'){
        try{ h.stop(); }catch(e){}
      }
      window.__gfxActive.delete(el);
    });
  }

  function reinitFxIn(root){
    stopFxIn(root);
    initFxIn(root);
  }
  window.__gfxReinit = reinitFxIn;

  function boot(){
    ready.then(() => {
      const active = document.querySelector('.slide.is-active') || document.querySelector('.slide');
      if (active) initFxIn(active);

      const slides = document.querySelectorAll('.slide');
      slides.forEach((sl) => {
        const mo = new MutationObserver((muts) => {
          for (const m of muts){
            if (m.attributeName === 'class'){
              if (sl.classList.contains('is-active')) initFxIn(sl);
              else stopFxIn(sl);
            }
          }
        });
        mo.observe(sl, { attributes: true, attributeFilter: ['class'] });
      });
    });
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
