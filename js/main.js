/* ==========================================================================
   AJID — site behaviour
   No dependencies. ~7KB unminified.
   ========================================================================== */
(() => {
  'use strict';

  const RTL    = document.documentElement.dir === 'rtl';
  const REDUCE = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const clamp = (v, a, b) => v < a ? a : v > b ? b : v;

  /* ------------------------------------------------------------------ *
   * 0. Always open at the top of the hero
   *    The hero's rule and nav are driven by scroll progress, so a browser
   *    restoring the previous offset lands mid-animation -- the centre line
   *    comes back collapsed and the menu half-faded. Switching language is a
   *    normal navigation, so it inherits the same restored offset.
   * ------------------------------------------------------------------ */
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  if (!location.hash) {
    scrollTo(0, 0);
    addEventListener('load', () => { if (!location.hash) scrollTo(0, 0); }, { once: true });
  }

  /* ------------------------------------------------------------------ *
   * 1. Text splitting — wraps chars / words / lines in reveal masks
   * ------------------------------------------------------------------ */
  /* Collect the words of an element while remembering which inline tags each
     one sits inside, so splitting cannot flatten <strong>/<em>/<a>. */
  function tokenize(root) {
    const out = [];
    let gap = false;          // did real whitespace precede the next word?
    (function walk(node, fmt) {
      for (const n of node.childNodes) {
        if (n.nodeType === 3) {
          const re = /\s+|\S+/g;
          let m;
          while ((m = re.exec(n.textContent)) !== null) {
            if (/^\s/.test(m[0])) gap = true;
            else { out.push({ w: m[0], fmt, gap: gap && out.length > 0 }); gap = false; }
          }
        } else if (n.nodeType === 1) {
          walk(n, fmt.concat([n.tagName.toLowerCase()]));
        }
      }
    })(root, []);
    return out;
  }

  /* Rebuild one word inside the inline tags it originally lived in. */
  function wordNode(tok) {
    let node = document.createTextNode(tok.w);
    for (let i = tok.fmt.length - 1; i >= 0; i--) {
      const e = document.createElement(tok.fmt[i]);
      e.appendChild(node);
      node = e;
    }
    return node;
  }

  function split(el, mode) {
    if (el.dataset.split$ === 'done') return;

    // formatting-preserving path for line splitting
    if (mode === 'lines') {
      const toks = tokenize(el);
      el.textContent = '';
      const probes = toks.map((t, i) => {
        if (i && t.gap) el.appendChild(document.createTextNode(' '));
        const s = document.createElement('span');
        s.style.display = 'inline-block';
        s.appendChild(wordNode(t));
        el.appendChild(s);
        return s;
      });
      const rows = [];
      let top = null;
      probes.forEach((p, i) => {
        const t = Math.round(p.offsetTop);
        if (top === null || Math.abs(t - top) > 4) { rows.push([]); top = t; }
        rows[rows.length - 1].push(toks[i]);
      });
      el.textContent = '';
      rows.forEach((words, n) => {
        const m = document.createElement('span');
        m.className = 'line-mask';
        m.style.display = 'block';
        const l = document.createElement('span');
        l.className = 'line';
        l.style.setProperty('--i', n);
        words.forEach((t, k) => {
          // only re-insert a space where one genuinely existed, so punctuation
          // that follows a <strong> run stays glued to the word before it
          if (k && t.gap) l.appendChild(document.createTextNode(' '));
          l.appendChild(wordNode(t));
        });
        m.appendChild(l);
        el.appendChild(m);
      });
      el.dataset.split$ = 'done';
      return;
    }

    const text = el.textContent.replace(/\s+/g, ' ').trim();
    el.textContent = '';
    let i = 0;

    if (mode === 'chars') {
      for (const word of text.split(' ')) {
        const w = document.createElement('span');
        w.style.display = 'inline-block';
        w.style.whiteSpace = 'nowrap';
        for (const ch of [...word]) {
          const m = document.createElement('span');
          m.className = 'char-mask';
          const c = document.createElement('span');
          c.className = 'char';
          c.style.setProperty('--i', i++);
          c.textContent = ch;
          m.appendChild(c);
          w.appendChild(m);
        }
        el.appendChild(w);
        el.appendChild(document.createTextNode(' '));
      }
    } else if (mode === 'words') {
      for (const word of text.split(' ')) {
        const m = document.createElement('span');
        m.className = 'word-mask';
        const w = document.createElement('span');
        w.className = 'word';
        w.style.setProperty('--i', i++);
        w.textContent = word;
        m.appendChild(w);
        el.appendChild(m);
        el.appendChild(document.createTextNode(' '));
      }
    } else { /* lines — measure first, then group */
      const probes = [];
      for (const word of text.split(' ')) {
        const s = document.createElement('span');
        s.style.display = 'inline-block';
        s.textContent = word;
        el.appendChild(s);
        el.appendChild(document.createTextNode(' '));
        probes.push(s);
      }
      const rows = [];
      let top = null;
      for (const p of probes) {
        const t = Math.round(p.offsetTop);
        if (top === null || Math.abs(t - top) > 4) { rows.push([]); top = t; }
        rows[rows.length - 1].push(p.textContent);
      }
      el.textContent = '';
      rows.forEach((words, n) => {
        const m = document.createElement('span');
        m.className = 'line-mask';
        m.style.display = 'block';
        const l = document.createElement('span');
        l.className = 'line';
        l.style.setProperty('--i', n);
        l.textContent = words.join(' ');
        m.appendChild(l);
        el.appendChild(m);
      });
    }
    el.dataset.split$ = 'done';
  }

  $$('[data-split]').forEach(el => {
    const m = el.dataset.split;
    // Arabic must stay as connected script — never split its characters
    split(el, (RTL && m === 'chars') ? 'words' : m);
    el.classList.add(m === 'lines' ? 'reveal-lines' : m === 'words' ? 'reveal-words' : 'reveal-chars');
  });

  /* ------------------------------------------------------------------ *
   * 2. Reveal on enter
   * ------------------------------------------------------------------ */
  const revealEls = $$('[data-reveal]');
  const revealVisible = () => {
    const vh = innerHeight || document.documentElement.clientHeight;
    for (const el of revealEls) {
      if (el.classList.contains('is-in')) continue;
      const r = el.getBoundingClientRect();
      if (r.top <= vh * 0.94 && r.bottom >= 0) el.classList.add('is-in');
    }
  };
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
      }
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0 });
    revealEls.forEach(el => io.observe(el));
  } else {
    /* Safari before 12.1 has no IntersectionObserver. Content is more
       important than entrance animation, so reveal it immediately. */
    revealEls.forEach(el => el.classList.add('is-in'));
  }
  /* WebKit can postpone IntersectionObserver callbacks for elements whose
     children start fully clipped. Keep a cheap geometry fallback so Safari
     never leaves an image or heading permanently hidden. */
  addEventListener('scroll', revealVisible, { passive: true });
  addEventListener('resize', revealVisible, { passive: true });
  addEventListener('pageshow', revealVisible);
  addEventListener('load', revealVisible);
  revealVisible();

  /* ------------------------------------------------------------------ *
   * 3. Hero — canvas cross-fade + scroll-driven scale
   * ------------------------------------------------------------------ */
  const heroSection = $('#hero');
  const canvas      = $('#heroCanvas');
  const scaler      = $('#heroScaler');
  const markLat     = $('#markLat');
  const markAr      = $('#markAr');
  const heroMid     = $('.hero__mid');
  const heroFoot    = $('.hero__foot');
  // hero frames come from content/site.json via the build step
  const SRC = (window.AJID_HERO && window.AJID_HERO.length)
    ? window.AJID_HERO
    : ['assets/img/hero-1.jpg'];

  const frames = [];
  let loaded = 0, ctx = null, dpr = 1;

  function fit() {
    if (!canvas) return;
    dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width  = Math.round(canvas.clientWidth  * dpr);
    canvas.height = Math.round(canvas.clientHeight * dpr);
    draw();
  }

  /* cover-fit draw of one image at a given alpha */
  function paint(img, alpha) {
    if (!img || !img.complete || !img.naturalWidth) return;
    const cw = canvas.width, ch = canvas.height;
    const s  = Math.max(cw / img.naturalWidth, ch / img.naturalHeight);
    const w  = img.naturalWidth * s, h = img.naturalHeight * s;
    ctx.globalAlpha = alpha;
    ctx.drawImage(img, (cw - w) / 2, (ch - h) / 2, w, h);
  }

  let heroP = 0; // 0..1 progress through the hero runway

  const ready = img => img && img.complete && img.naturalWidth > 0;

  /* nearest already-decoded frame at or before i, so a frame that is still in
     flight never blanks the hero */
  function nearest(i) {
    for (let k = i; k >= 0; k--) if (ready(frames[k])) return frames[k];
    for (let k = i + 1; k < SRC.length; k++) if (ready(frames[k])) return frames[k];
    return null;
  }

  function draw() {
    if (!ctx) return;
    const n = SRC.length;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (n < 2) { paint(nearest(0), 1); ctx.globalAlpha = 1; return; }

    // spread the frames across the runway with soft cross-fades
    const pos  = heroP * (n - 1);
    const i    = clamp(Math.floor(pos), 0, n - 2);
    const t    = clamp(pos - i, 0, 1);
    const ease = t * t * (3 - 2 * t);

    const a = nearest(i), b = ready(frames[i + 1]) ? frames[i + 1] : null;
    paint(a, 1);
    if (b && ease > 0) paint(b, ease);
    ctx.globalAlpha = 1;
  }

  /* ------------------------------------------------------------------ *
   * 4. Loader — gated on the first hero frame only (fast first paint)
   * ------------------------------------------------------------------ */
  const loader = $('#loader'), bar = $('#loaderBar');
  function bump() {
    loaded++;
    if (bar) bar.style.width = Math.round(loaded / SRC.length * 100) + '%';
  }
  function dismiss() {
    if (!loader || loader.classList.contains('done')) return;
    loader.classList.add('done');
    document.body.classList.add('ready');
    // first frame: the image window opens out from the middle of the dark
    // screen while the wordmark letters arrive behind it.
    // Driven by timers, not rAF — a tab that loads in the background has its
    // frame callbacks suspended, and the hero must not be stuck shut.
    document.body.classList.add('hero-open');
    setTimeout(() => { const el = $('#markLat'); if (el) el.classList.add('is-in'); }, 340);
    setTimeout(() => { const el = $('#markAr'); if (el) el.classList.add('is-in'); }, 620);
  }

  function loadFrame(idx) {
    const img = new Image();
    img.decoding = 'async';
    if (idx === 0) img.fetchPriority = 'high';
    img.onload = img.onerror = () => {
      bump();
      if (idx === 0) { fit(); dismiss(); }
      draw();
    };
    img.src = SRC[idx];
    frames[idx] = img;
  }

  // first frame is what the visitor actually sees — everything else can wait
  loadFrame(0);
  const idle = window.requestIdleCallback || (fn => setTimeout(fn, 400));
  addEventListener('load', () => idle(() => {
    for (let i = 1; i < SRC.length; i++) loadFrame(i);
  }), { once: true });

  if (canvas) { ctx = canvas.getContext('2d', { alpha: false }); fit(); }
  addEventListener('resize', fit, { passive: true });
  // safety net: never let the curtain trap the page
  setTimeout(dismiss, 2500);
  addEventListener('load', dismiss);

  /* ------------------------------------------------------------------ *
   * 5. Scroll loop — hero scale, masthead theme
   * ------------------------------------------------------------------ */
  const masthead = $('#masthead');
  let ticking = false;

  /* the timeline spine draws downward as you scroll, and each year lights up
     at the moment the tip of the line reaches it — one connected movement */
  const tlEl    = $('.tl');
  const tlSpine = tlEl && $('.tl__spine', tlEl);
  const tlItems = tlEl ? $$('.tl__entry', tlEl) : [];

  const tlFigs   = tlEl ? $$('.tl__fig img', tlEl) : [];
  const tlLabels = tlEl ? $$('.tl__label', tlEl)   : [];

  // Reveals clip their image to zero visible area until scrolled to, and Chrome
  // will not lazy-load an image inside a fully clipped box -- it stays blank
  // forever. Affects every reveal on the page, not just the collage. So we
  // decide loading ourselves: promote each image to eager well before it is
  // needed, observing an ancestor that is never clipped. Still deferred, just
  // deterministic.
  (function primeLazyImages() {
    const imgs = $$('img[loading="lazy"]');
    if (!imgs.length) return;
    /* Changing a clipped image from lazy to eager only after it approaches the
       viewport is unreliable in WebKit. Promote it immediately; the files are
       compressed and this is preferable to a permanently blank portfolio. */
    imgs.forEach(i => { i.loading = 'eager'; });
    const host = img => img.closest('.tl__entry, .fig, figure, .closing') ||
                        img.parentElement || img;
    if (!('IntersectionObserver' in window)) {
      imgs.forEach(i => { i.loading = 'eager'; });
      return;
    }
    const io = new IntersectionObserver((entries, obs) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        e.target.querySelectorAll('img[loading="lazy"]')
                .forEach(i => { i.loading = 'eager'; });
        obs.unobserve(e.target);
      }
    }, { rootMargin: '1400px 0px 1400px 0px', threshold: 0 });
    new Set(imgs.map(host)).forEach(h => io.observe(h));

    // Belt and braces: whatever the observer does or does not catch, nothing is
    // allowed to sit unloaded once the page is idle. A clipped lazy image that
    // Chrome has already deferred will otherwise stay blank forever.
    const sweep = () => $$('img[loading="lazy"]').forEach(i => { i.loading = 'eager'; });
    if (document.readyState === 'complete') setTimeout(sweep, 1500);
    else addEventListener('load', () => setTimeout(sweep, 1500));
  })();

  /* ------------------------------------------------------------------ *
   * Footer wordmark: the letters stay put, the photograph inside slides.
   * Progress runs from the moment the wordmark's top touches the bottom of
   * the viewport until it has risen by its own height -- exactly the mapping
   * spec'd so the travel reaches 0 at top = innerHeight and caps one full
   * wordmark-height later.
   * ------------------------------------------------------------------ */
  const footMarks = $$('.foot-mark svg');

  function drawFootMarks() {
    if (REDUCE || !footMarks.length) return;
    const vh = innerHeight;
    for (const svg of footMarks) {
      const r = svg.getBoundingClientRect();
      if (r.bottom < -200 || r.top > vh + 200) continue;
      const p = clamp((vh - r.top) / Math.max(r.height, 1), 0, 1);
      svg.style.setProperty('--fp', p.toFixed(4));
    }
  }

  function drawSpine() {
    if (!tlEl || !tlSpine) return;
    const r   = tlEl.getBoundingClientRect();
    const tip = innerHeight * 0.58;                       // where the tip rides
    const p   = clamp((tip - r.top) / Math.max(r.height, 1), 0, 1);
    // one value drives the line's scaleY, the box's position, and its spin
    tlEl.style.setProperty('--draw', p.toFixed(4));
    // a slow turn: one and a half revolutions over the whole section
    if (!REDUCE) tlEl.style.setProperty('--spin', (p * 540).toFixed(1) + 'deg');

    // each entry's dot lights up as the tip of the line reaches it
    const tipY = r.top + p * r.height;
    for (const e of tlItems) {
      if (e.classList.contains('is-in')) continue;
      if (e.getBoundingClientRect().top <= tipY) e.classList.add('is-in');
    }

    if (REDUCE) return;
    const vh = innerHeight;
    // Each frame opens its own mask as it rises through the viewport, and the
    // picture inside slides down to meet it. One progress value drives both.
    for (const img of tlFigs) {
      const fig = img.parentElement;
      const b = fig.getBoundingClientRect();
      if (b.bottom < -400 || b.top > vh + 400) continue;
      const p = clamp((vh - b.top) / (vh * 0.75), 0, 1);
      fig.style.setProperty('--rp', p.toFixed(4));
    }
    for (const lab of tlLabels) {
      const b = lab.getBoundingClientRect();
      if (b.bottom < -300 || b.top > vh + 300) continue;
      const q = (b.top + b.height / 2 - vh / 2) / (vh / 2 + b.height / 2);
      // labels drift against the images, which is what reads as depth
      lab.style.setProperty('--ly', (q * 54).toFixed(2) + 'px');
    }
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      if (heroSection) {
        const r   = heroSection.getBoundingClientRect();
        const run = Math.max(r.height - innerHeight, 1);
        heroP = clamp(-r.top / run, 0, 1);
        if (scaler) scaler.style.transform = 'scale(' + (1.4 - 0.4 * heroP).toFixed(4) + ')';

        /* the two wordmarks part company: English travels off to the left,
           Arabic to the right, while the centre rule closes toward its middle.
           Smoothstepped so the movement eases out of rest rather than
           starting at full speed the instant the wheel turns. */
        if (!REDUCE) {
          const t = clamp(heroP / 0.55, 0, 1);
          const e = (t * t * (3 - 2 * t)).toFixed(4);
          markLat && markLat.style.setProperty('--exit', e);
          markAr  && markAr.style.setProperty('--exit', e);
          heroMid && heroMid.style.setProperty('--exit', e);
          heroFoot && heroFoot.style.setProperty('--exit', e);
        }
        draw();
      }
      drawSpine();
      drawFootMarks();
      // masthead flips to navy ink once the sand body scrolls under it
      if (masthead) {
        const past = heroSection
          ? heroSection.getBoundingClientRect().bottom <= 80
          : scrollY > 80;
        masthead.classList.toggle('on-light', past);
      }
    });
  }
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ------------------------------------------------------------------ *
   * 6. Work list — floating cursor preview
   * ------------------------------------------------------------------ */
  const preview = $('#preview');
  const items   = $$('.work__item');
  if (preview && items.length && matchMedia('(hover:hover)').matches) {
    const imgs = new Map();
    let tx = 0, ty = 0, cx = 0, cy = 0, active = false, raf = 0;

    // created on demand — hovering row 7 should not cost the other eleven
    const ensure = src => {
      if (!src) return null;
      let im = imgs.get(src);
      if (!im) {
        im = new Image();
        im.alt = '';
        im.decoding = 'async';
        im.src = src;
        preview.appendChild(im);
        imgs.set(src, im);
      }
      return im;
    };

    const loop = () => {
      cx += (tx - cx) * 0.14;
      cy += (ty - cy) * 0.14;
      preview.style.transform =
        `translate3d(${cx.toFixed(1)}px, ${cy.toFixed(1)}px, 0) translate(-50%,-50%) scale(${active ? 1 : 0.92})`;
      raf = (active || Math.abs(tx - cx) > 0.5) ? requestAnimationFrame(loop) : 0;
    };

    addEventListener('pointermove', e => {
      tx = e.clientX; ty = e.clientY;
      if (!raf) { cx = cx || tx; cy = cy || ty; raf = requestAnimationFrame(loop); }
    }, { passive: true });

    items.forEach(it => {
      it.addEventListener('pointerenter', () => {
        active = true;
        preview.classList.add('on');
        const im = ensure(it.dataset.img);
        imgs.forEach(x => x.classList.remove('show'));
        // let a freshly-created image lay out before fading it in
        if (im) requestAnimationFrame(() => im.classList.add('show'));
        if (!raf) raf = requestAnimationFrame(loop);
      });
      it.addEventListener('pointerleave', () => {
        active = false;
        preview.classList.remove('on');
      });
    });
  }

  /* ------------------------------------------------------------------ *
   * 7. Mobile drawer
   * ------------------------------------------------------------------ */
  const drawer = $('#drawer');
  const toggles = [$('#navToggle'), $('#heroMenu')].filter(Boolean);
  let open = false;
  function setDrawer(state) {
    open = state;
    if (drawer) {
      drawer.classList.toggle('open', open);
      drawer.setAttribute('aria-hidden', String(!open));
    }
    document.body.style.overflow = open ? 'hidden' : '';
    toggles.forEach(t => {
      t.setAttribute('aria-expanded', String(open));
      t.textContent = open ? (RTL ? 'إغلاق' : 'Close') : (RTL ? 'القائمة' : 'Menu');
    });
  }
  toggles.forEach(t => t.addEventListener('click', () => setDrawer(!open)));
  $$('#drawer a').forEach(a => a.addEventListener('click', () => setDrawer(false)));
  addEventListener('keydown', e => { if (e.key === 'Escape' && open) setDrawer(false); });

  /* ------------------------------------------------------------------ *
   * 8. Marquee — duplicate the track so the loop is seamless
   * ------------------------------------------------------------------ */
  const mq = $('#marquee');
  if (mq && !REDUCE) mq.innerHTML += mq.innerHTML;

  /* ------------------------------------------------------------------ *
   * 9. Smooth scroll
   *    Interpolates the *native* scroll position rather than transforming a
   *    wrapper, so position:sticky (the whole hero) keeps working. Pointer
   *    devices only — touch already has good momentum of its own.
   * ------------------------------------------------------------------ */
  const fine = matchMedia('(hover:hover) and (pointer:fine)').matches;
  if (fine && !REDUCE) {
    let target = scrollY, current = scrollY, running = false, lock = false;

    const maxScroll = () =>
      Math.max(0, document.documentElement.scrollHeight - innerHeight);

    const tick = () => {
      current += (target - current) * 0.11;
      if (Math.abs(target - current) < 0.4) { current = target; running = false; }
      lock = true;
      scrollTo(0, current);
      lock = false;
      onScroll();
      if (running) requestAnimationFrame(tick);
    };

    addEventListener('wheel', e => {
      if (e.ctrlKey || open) return;            // pinch-zoom / drawer open
      e.preventDefault();
      target = clamp(target + e.deltaY * (e.deltaMode === 1 ? 18 : 1), 0, maxScroll());
      if (!running) { running = true; requestAnimationFrame(tick); }
    }, { passive: false });

    // keep in sync when something else moves the page (keyboard, anchors, resize)
    addEventListener('scroll', () => { if (!lock && !running) target = current = scrollY; },
                     { passive: true });
    addEventListener('resize', () => { target = current = scrollY; }, { passive: true });
  }

  /* ------------------------------------------------------------------ *
   * 10. Gentle parallax on figure images
   * ------------------------------------------------------------------ */
  const parallax = $$('.fig .reveal-image > img');
  if (parallax.length && !REDUCE) {
    let pRaf = 0;
    const run = () => {
      pRaf = 0;
      const vh = innerHeight;
      for (const img of parallax) {
        const r = img.getBoundingClientRect();
        if (r.bottom < -200 || r.top > vh + 200) continue;
        // -1 .. 1 across the viewport
        const p = (r.top + r.height / 2 - vh / 2) / (vh / 2 + r.height / 2);
        img.style.setProperty('--py', (p * -18).toFixed(2) + 'px');
      }
    };
    addEventListener('scroll', () => { if (!pRaf) pRaf = requestAnimationFrame(run); },
                     { passive: true });
    run();
  }

  /* ------------------------------------------------------------------ *
   * 11. Anchor scrolling that respects the fixed masthead
   * ------------------------------------------------------------------ */
  $$('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const id = a.getAttribute('href');
      if (id.length < 2) return;
      const t = document.getElementById(id.slice(1));
      if (!t) return;
      e.preventDefault();
      scrollTo({ top: t.getBoundingClientRect().top + scrollY - 10, behavior: REDUCE ? 'auto' : 'smooth' });
    });
  });
})();
