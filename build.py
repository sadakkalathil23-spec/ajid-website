#!/usr/bin/env python3
"""
AJID site builder.

Reads content/site.json and writes index.html (English) and ar/index.html (Arabic).
Everything editable — colours, copy, images, projects — lives in the JSON,
so the admin panel only ever has to touch that one file and re-run this.

    python build.py
"""
import json, re, pathlib, html, sys

ROOT = pathlib.Path(__file__).parent
import hashlib
# While the site is circulating as a private review link, keep it out of
# search results. Set to False before the public launch and rebuild.
REVIEW_MODE = True
REVIEW_META = ('<meta name="robots" content="noindex,nofollow">'
               if REVIEW_MODE else '')

CSS_V = hashlib.md5((pathlib.Path(__file__).parent / "css" / "main.css").read_bytes()).hexdigest()[:8]
JS_V  = hashlib.md5((pathlib.Path(__file__).parent / "js" / "main.js").read_bytes()).hexdigest()[:8]
CONTENT = ROOT / "content" / "site.json"


# --------------------------------------------------------------------------
# Logo artwork — pulled straight from the brand SVG masters so the site can
# never drift from the supplied identity files.
# --------------------------------------------------------------------------
def svg_inner(name: str) -> str:
    """Return the drawable contents of one of the brand logo SVGs."""
    raw = (ROOT / "assets" / "logo" / name).read_text(encoding="utf8")
    return raw.split(">", 2)[2].rsplit("</svg>", 1)[0].strip()


def latin_letters() -> str:
    """AJID wordmark, split into four letters ordered left-to-right for stagger."""
    raw = svg_inner("Logo-46.svg")
    shapes = re.findall(r"<(?:path|polygon)\b[^>]*/>", raw)
    # leftmost x of each glyph in the source artwork (measured via getBBox)
    order = {"M316.74": 0, "M408.71": 1, "659.41 472.23": 2, "M831.2": 3}
    def rank(s):
        for key, idx in order.items():
            if key in s:
                return idx
        return 99
    out = []
    for i, shape in enumerate(sorted(shapes, key=rank)):
        out.append(shape.replace("<path ", f'<path class="ltr" style="--i:{i}" ')
                        .replace("<polygon ", f'<polygon class="ltr" style="--i:{i}" '))
    return "\n            ".join(out)


def arabic_wordmark() -> str:
    """عجيد wordmark: one body stroke plus three dots that settle in after it."""
    raw = svg_inner("Logo-44.svg")
    shapes = re.findall(r"<path\b[^>]*/>", raw)
    # the body is by far the longest path; the rest are the dots
    body = max(shapes, key=len)
    dots = [s for s in shapes if s is not body]
    out = [body.replace("<path ", '<path class="ar-body" ')]
    for i, d in enumerate(dots):
        out.append(d.replace("<path ", f'<path class="ar-dot" style="--i:{i}" '))
    return "\n            ".join(out)


MARK_LATIN   = latin_letters()
MARK_ARABIC  = arabic_wordmark()
MARK_ADOT    = svg_inner("Logo-41.svg")
MARK_OCTAGON = svg_inner("Logo-39.svg")

VB_LATIN  = "182.44 472.22 715.08 135.55"   # tight bbox of the AJID wordmark
VB_ARABIC = "182.44 475.77 715.08 128.46"   # tight bbox of عجيد — same x-range,
                                            # so the two stack in exact alignment


# --------------------------------------------------------------------------
# Fragments
# --------------------------------------------------------------------------
def figure(img, alt, caption, cls="fig-wide", w=1600, h=1100):
    return f'''<figure class="fig {cls}">
      <div class="reveal-image" data-reveal><img src="{img}" alt="{alt}" width="{w}" height="{h}" loading="lazy" decoding="async"></div>
      <figcaption>{caption}</figcaption>
    </figure>'''


def work_rows(items):
    rows = []
    for it in items:
        soon = ' data-soon="1"' if it.get("soon") else ""
        rows.append(
            f'<a class="work__item" href="#"{soon} data-img="{it["img"]}">'
            f'<span class="work__num">{it["num"]}</span>'
            f'<span class="work__name">{it["name"]}</span>'
            f'<span class="work__meta">{it["meta"]}</span></a>')
    return "\n    ".join(rows)


def value_rows(items):
    rows = []
    for v in items:
        rows.append(f'''<div class="value">
      <span class="value__num">{v["num"]}</span>
      <h3 class="value__name" data-split="chars" data-reveal>{v["name"]}</h3>
      <span class="value__ar">{v["alt"]}</span>
      <p class="value__txt reveal-up" data-reveal>{v["text"]}</p>
    </div>''')
    return "\n    ".join(rows)



SEP = chr(10) + "      "   # indentation between generated blocks


def timeline_entries(items):
    """Collage down a centre spine:
    blocks run 31-56% of the viewport and cross the centre line freely. Each
    entry carries its own start column, span and aspect, so the rhythm is
    editable without touching code. Every block stops by column 12, leaving a
    clear quarter of the page on its right for the name to land in."""
    out = []
    for it in items:
        start_col = int(it.get("start", 1))
        span      = int(it.get("span", 6))
        side = "tl__item--l" if start_col + span <= 9 else "tl__item--r"
        out.append(
            f'<div class="tl__entry" data-reveal>'
            f'<span class="tl__dot" aria-hidden="true"></span>'
            f'<a class="tl__item {side}" href="#" data-img="{it["img"]}" '
            f'style="--col:{start_col}/span {span};--ar:{it.get("ar","4/3")};--labw:{it.get("labw",50)}%">'
            f'<span class="tl__fig">'
            f'<img src="{it["img"]}" alt="{it["name"]}" '
            f'loading="lazy" decoding="async"></span>'
            f'<span class="tl__label"><span class="tl__name">{it["name"]}</span></span>'
            f'</a>'
            f'</div>')
    return SEP.join(out)


def intro_images(cfg, t):
    """Three equal images across the full width, sharing one top edge."""
    out = []
    for i, f in enumerate(t["features"][:3]):
        out.append(
            f'<figure class="fig c-4" style="--ar:{f.get("w",3)}/{f.get("h",4)}">'
            f'<span class="reveal-image" data-reveal>'
            f'<img src="{cfg["images"]["feature"][i]}" alt="{f["alt"]}" '
            f'width="{f.get("w",1400)}" height="{f.get("h",1866)}" loading="lazy" decoding="async"></span>'
            f'<figcaption>{f["caption"]}</figcaption></figure>')
    return SEP.join(out)


def fill_mark(cfg, uid, which):
    """A wordmark whose letters are a window onto a photograph."""
    tex = cfg["images"].get("wordmarkFillLat" if which == "lat" else "wordmarkFillAr")           or cfg["images"].get("wordmarkFill", "/assets/img/hero-1.jpg")
    if which == "lat":
        vb, shapes = VB_LATIN, MARK_LATIN
        x, y, w, h = "182.44", "472.22", "715.08", "135.55"
    else:
        vb, shapes = VB_ARABIC, MARK_ARABIC
        x, y, w, h = "182.44", "475.77", "715.08", "128.46"
    # The photograph is cut to twice the wordmark's height and parked half a
    # height above it, so it can slide a full height downward and still cover
    # the letters at both ends of that travel
    # (viewBox 211 tall, image 422 tall at y=-211, translating 0..211).
    yy = float(y) - float(h)
    hh = float(h) * 2
    # The clip lives on a STATIC <g>, never on the moving image: an element's
    # clip-path is resolved in that element's own user space, so clipping the
    # image directly would drag the letter shapes along with the slide and
    # carry them straight out of the viewBox.
    return (f'<svg viewBox="{vb}" role="presentation" aria-hidden="true">'
            f'<defs><clipPath id="fm-{uid}">{shapes}</clipPath></defs>'
            f'<g clip-path="url(#fm-{uid})">'
            f'<image href="{tex}" x="{x}" y="{yy:.2f}" width="{w}" height="{hh:.2f}" '
            f'preserveAspectRatio="xMidYMid slice" style="--fmh:{h}"></image>'
            f'</g></svg>')


# --------------------------------------------------------------------------
# Page template
# --------------------------------------------------------------------------

def relativise(markup, base):
    """GitHub Pages serves a project repo from /repo-name/, so root-absolute
    paths would resolve against the domain root and 404. Rewrite them relative
    to the page's own depth: base is "" at the root, "../" one level down.
    Leaves protocol-relative and absolute URLs alone."""
    def sub(m):
        attr, path = m.group(1), m.group(2)
        if path == "/":
            return f'{attr}="{base or "./"}"'
        return f'{attr}="{base}{path.lstrip("/")}"'
    markup = re.sub(r'(href|src|content)="(/(?!/)[^"]*)"', sub, markup)
    # the hero frames travel as a JSON array in a <script>, not as an
    # attribute, so they need the same treatment or they 404 off-root
    def sub_json(m):
        return '"' + base + m.group(1).lstrip('/') + '"'
    return re.sub(r'"(/assets/[^"]*)"', sub_json, markup)


def render(cfg, key):
    t   = cfg[key]
    th  = cfg["theme"]
    im  = cfg["images"]
    ct  = cfg["contact"]
    nav = t["nav"]
    ft  = t["footer"]



    studio_lines = "".join(f"<li>{l}</li>" for l in ft["studioLines"])

    # theme is emitted as a tiny inline style block so the very first paint is
    # already in brand colour — no flash, no extra request.
    theme_css = (
        f":root{{--bg:{th['background']};--ink:{th['foreground']};"
        f"--heading:{th['heading']};--accent:{th['accent']};"
        f"--invert-bg:{th['invertBg']};--invert-fg:{th['invertFg']};"
        f"--hero-ink:{th['heroInk']};"
        f"--hero-nav-ink:{th.get('heroNavInk', th['heroInk'])};"
        f"--fs-nav:{th.get('navSize', 'clamp(14px,1.15vw,30px)')}}}")

    return f'''<!doctype html>
<html lang="{t["lang"]}" dir="{t["dir"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{t["title"]}</title>
<meta name="description" content="{t["metaDescription"]}">
<meta name="theme-color" content="{th["background"]}">
{REVIEW_META}
<link rel="canonical" href="{t["selfHref"]}">
<link rel="alternate" hreflang="en" href="/">
<link rel="alternate" hreflang="ar" href="/ar/">

<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/HayyakumAllah-Light.woff2" crossorigin>
<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/HayyakumAllah-Medium.woff2" crossorigin>
<link rel="preload" as="image" href="{im["hero"][0]}" fetchpriority="high">
<link rel="stylesheet" href="/css/main.css?v={CSS_V}">
<style id="theme">{theme_css}</style>
<link rel="icon" href="/assets/logo/favicon.svg" type="image/svg+xml">

<meta property="og:title" content="{t["title"]}">
<meta property="og:description" content="{t["ogDescription"]}">
<meta property="og:type" content="website">
<script>
document.documentElement.classList.add('js');
/* live theme overrides from the admin panel, applied before first paint */
try{{var o=JSON.parse(localStorage.getItem('ajid.theme')||'null');
if(o)for(var k in o)document.documentElement.style.setProperty(k,o[k]);}}catch(e){{}}
</script>
</head>
<body data-lang="{t["lang"]}">

<div id="loader">
  <div class="mark"><svg viewBox="330 340 400 400" aria-hidden="true">{MARK_OCTAGON}</svg></div>
  <div class="bar" id="loaderBar"></div>
</div>
<script>
/* The curtain is position:fixed over the whole page. main.js normally lifts it,
   but if that script ever fails to run -- an unsupported feature on an older
   phone, a blocked request -- the visitor would be left staring at a blank
   page. This runs inline, independent of main.js, so that cannot happen. */
setTimeout(function(){{var l=document.getElementById('loader');
  if(l&&l.className.indexOf('done')<0)l.className+=' done';}},4000);
</script>

<!-- navigation lives in the hero only; no persistent masthead -->

<div id="drawer" aria-hidden="true">
  <nav class="items" aria-label="{nav["mobile"]}">
    <a href="#studio">{nav["studio"]}</a>
    <a href="#work">{nav["work"]}</a>
    <a href="#collections">{nav["collections"]}</a>
    <a href="#contact">{nav["contact"]}</a>
    <a href="{t["altHref"]}" lang="{t["altLang"]}">{t["altLabel"]}</a>
  </nav>
  <div class="meta"><span>{ft["drawerPlace"]}</span><span>{ft["drawerEst"]}</span></div>
</div>

<main>

<!-- ============================ HERO ============================ -->
<section class="hero" id="hero">
  <div class="hero__sticky">

    <div class="hero__media">
      <div class="hero__scaler" id="heroScaler">
        <canvas class="hero__canvas" id="heroCanvas"></canvas>
      </div>
      <div class="hero__veil"></div>
    </div>

    <div class="hero__ui">

      <!-- English wordmark, top -->
      <div class="px">
        <h1 class="hero__mark hero__mark--lat" id="markLat">
          <span class="sr-only">{t["hero"]["srTitle"]}</span>
          <svg viewBox="{VB_LATIN}" role="presentation" aria-hidden="true">
            {MARK_LATIN}
          </svg>
        </h1>
      </div>

      <!-- centre rule + utility row -->
      <div class="hero__mid">
        <div class="rule reveal-fade" data-reveal></div>
        <nav class="hero__nav" aria-label="{nav["primary"]}">
          <span class="is-here desktop-only">{nav["homeLabel"]}</span>
          <button class="hero-menu hero__menu-only" id="heroMenu" aria-controls="drawer" aria-expanded="false">{nav["menu"]}</button>
          <a class="desktop-only" href="#work">{nav["work"]}</a>
          <a class="desktop-only" href="#studio">{nav["studio"]}</a>
          <a class="desktop-only" href="#contact">{nav["contact"]}</a>
          <a href="{t["altHref"]}" lang="{t["altLang"]}" hreflang="{t["altLang"]}">{t["altLabel"]}</a>
        </nav>
      </div>

      <!-- Arabic wordmark, bottom. The scroll cue sits ABOVE the wordmark on
           its own row so the two can never sit on top of one another. -->
      <div class="px hero__bottom">
        <span class="scrollcue" aria-hidden="true">{t["hero"]["scroll"]}</span>

        <div class="hero__mark hero__mark--ar" id="markAr">
          <svg viewBox="{VB_ARABIC}" role="presentation" aria-hidden="true">
            {MARK_ARABIC}
          </svg>
        </div>

        <div class="hero__foot">
          <p class="hero__tag reveal-up" data-reveal>{t["hero"]["tagline"]}</p>
        </div>
      </div>

    </div>
  </div>
</section>

<!-- ===================== S1 · opening statement ===================== -->
<section class="px pt-6" id="studio">
  <div class="divider reveal-divider" data-reveal></div>
  <p class="para-lg mt-8" data-split="lines" data-reveal>{t["opening"]}</p>
</section>

<!-- ===================== S2 · intro note + image row ===================== -->
<section class="px pt-45">
  <div class="grid-default">
    <p class="c9-4 note note--bold reveal-up" data-reveal>{t["intro"]["body"]}</p>
  </div>
  <div class="grid-default" style="margin-top:clamp(14px,1.7vw,28px)">
    {intro_images(cfg, t)}
  </div>
  <div class="divider reveal-divider mt-6" data-reveal></div>
</section>

<!-- ===================== S3 - work timeline ===================== -->
<section class="px" id="work">
  <div class="tl" data-reveal>
    <div class="tl__spine"></div>
    <span class="tl__tip" aria-hidden="true"><span class="tl__cube"><span class="tl__face"><svg viewBox="370 380 350 300">{MARK_OCTAGON}</svg></span><span class="tl__face"><svg viewBox="370 380 350 300">{MARK_OCTAGON}</svg></span><span class="tl__face"><svg viewBox="370 380 350 300">{MARK_OCTAGON}</svg></span><span class="tl__face"><svg viewBox="370 380 350 300">{MARK_OCTAGON}</svg></span></span></span>
    <h2 class="tl__title" data-split="words" data-reveal>{t["workSection"]["eyebrow"]}</h2>
    {timeline_entries(t["work"])}
  </div>
  <div class="divider reveal-divider" data-reveal></div>
</section>

<!-- ===================== S4 · chapter one ===================== -->
<section class="px pt-6 pb-40">
  <h2 class="display mb-28" data-split="words" data-reveal>{t["chapter1"]["heading"].replace(chr(10), "<br>")}</h2>
  <div class="grid-default">
    <figure class="fig c1-5">
      <div class="reveal-image" data-reveal>
        <img src="{im["chapter1"]}" alt="" width="1600" height="1100" loading="lazy" decoding="async">
      </div>
    </figure>
    <div class="c7-6">
      <p class="para-mid reveal-up" data-reveal>{t["chapter1"]["body"]}</p>
    </div>
    <div class="c1-4 mt-36">
      <p class="note--sm reveal-up" data-reveal>{t["chapter1"]["note"].replace(chr(10), "<br>")}</p>
      <p class="note--sm mt-6 reveal-up" data-reveal><a href="#contact">{t["chapter1"]["noteLink"]}</a></p>
    </div>
  </div>
</section>

<!-- ===================== S5 · chapter two ===================== -->
<section class="px" id="values">
  <div class="divider reveal-divider mb-6" data-reveal></div>
  <h2 class="display mb-32" data-split="words" data-reveal>{t["chapter2"]["heading"]}</h2>
  <div class="grid-default mb-6">
    <p class="c10-3 note--sm reveal-up" data-reveal style="margin-bottom:clamp(30px,5vw,80px)">{t["chapter2"]["note"]}</p>
    <blockquote class="c-12 para-lg" data-split="lines" data-reveal
      style="margin-bottom:clamp(40px,9vw,180px)">{t["chapter2"]["quote"]}</blockquote>
    <p class="c-12 note--sm reveal-up" data-reveal
      style="margin-top:calc(-1*clamp(30px,7vw,140px));margin-bottom:clamp(40px,7vw,120px)">{t["chapter2"]["quoteSource"]}</p>
    <div class="c-5">
      <p class="para-mid reveal-up" data-reveal>{t["chapter2"]["body"]}</p>
    </div>
    <figure class="fig c-7">
      <div class="reveal-image" data-reveal>
        <img src="{im["chapter2"]}" alt="" width="1600" height="1100" loading="lazy" decoding="async">
      </div>
      <figcaption>{t["chapter2"]["caption"]}</figcaption>
    </figure>
  </div>
  <div class="divider reveal-divider mb-6" data-reveal></div>
</section>

<!-- ===================== S6 · chapter three ===================== -->
<section class="px pt-6" id="collections">
  <div class="grid-default">
    <div class="c-6">
      <p class="para-mid reveal-up" data-reveal>{t["chapter3"]["body"]}</p>
    </div>
    <p class="c10-3 note--sm reveal-up" data-reveal>{t["chapter3"]["note1"]}</p>
    <p class="c10-3 mt-36 note--sm reveal-up" data-reveal
      style="margin-bottom:clamp(18px,2vw,30px)">{t["chapter3"]["note2"]}</p>
  </div>
</section>

<!-- ===================== S7 - closing image + statement ===================== -->
<section class="px" style="padding-bottom:clamp(18px,2vw,30px)">
  <figure class="closing" data-reveal>
    <img src="{im["closing"]}" alt="" width="1920" height="1080" loading="lazy" decoding="async">
    <figcaption>{t["closing"]["caption"]}</figcaption>
  </figure>
  <p class="closing-line" data-split="lines" data-reveal>{t["closingStatement"]}</p>
</section>

</main>

<footer class="px" id="contact">
  <div class="divider reveal-divider" data-reveal></div>
  <div class="foot-bar">
    <span class="col">
      <a href="mailto:{ct["email"]}">{ct["email"]}</a>
      <span>{ft["credit"]}</span>
    </span>
    <span class="col col--end">
      <a href="#">{ft["privacy"]}</a>
    </span>
  </div>
  <div class="foot-marks">
    <div class="foot-mark foot-mark--lat">{fill_mark(cfg, key + "-lat", "lat")}</div>
    <div class="foot-mark foot-mark--ar">{fill_mark(cfg, key + "-ar", "ar")}</div>
  </div>
  <div class="foot-bar" style="opacity:.6">
    <span>{ft["rights"]}</span>
    <span>{ft["place"]}</span>
  </div>
</footer>

<div id="preview" aria-hidden="true"></div>

<script>window.AJID_HERO = {json.dumps(im["hero"])};</script>
<script src="/js/main.js?v={JS_V}" defer></script>
</body>
</html>
'''


def main():
    cfg = json.loads(CONTENT.read_text(encoding="utf8"))
    (ROOT / "index.html").write_text(relativise(render(cfg, "en"), ""), encoding="utf8")
    ar = ROOT / "ar"
    ar.mkdir(exist_ok=True)
    (ar / "index.html").write_text(relativise(render(cfg, "ar"), "../"), encoding="utf8")
    print("built  index.html")
    print("built  ar/index.html")


if __name__ == "__main__":
    main()
