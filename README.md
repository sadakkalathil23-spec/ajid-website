# AJID — Interior Design Studio

Bilingual (English / Arabic) website for AJID, Doha. Built from the supplied
Brand Guidelines 2026: Hayyakum Allah typeface, the six-colour brand palette,
and the real logo artwork.

---

## Run it

```bash
python server.py
```

| URL | What |
|---|---|
| `http://localhost:3020/` | English site |
| `http://localhost:3020/ar/` | Arabic site (RTL) |
| `http://localhost:3020/admin.html` | **Site Manager** — edit everything |

No build tools, no npm, no dependencies. Python 3 only.

---

## Editing the site

Open **`http://localhost:3020/admin.html`**. Four tabs:

- **Colours** — background, body text, headings, accent, the dark blocks
  (quote / footer / menu) and the hero. Click a brand swatch or use the colour
  picker. The preview on the right updates instantly.
- **English** / **العربية** — every word on each page, section by section,
  in the order they appear. Projects can be added, reordered and deleted.
- **Images** — hero sequence, intro row, chapter images, closing image, plus
  contact details. **Upload…** copies the file into `assets/img/` and points
  the site at it.

Press **Save & Publish**. That writes `content/site.json`, regenerates both
HTML pages, and reloads the preview. A timestamped backup of the previous
version is kept in `content/backups/`.

**Export / Import** move the whole site config as a single JSON file.

---

## How it fits together

```
content/site.json     <- single source of truth (all copy, colours, images)
build.py              <- renders index.html + ar/index.html from that JSON
server.py             <- serves the site, saves from the admin panel, rebuilds
admin.html            <- the Site Manager UI
css/main.css          <- design system + layout + animation
js/main.js            <- scroll, hero canvas, reveals (no libraries)
assets/
  fonts/              <- Hayyakum Allah, converted to WOFF2 (~43 KB each)
  logo/               <- the supplied brand SVG masters
  pattern/tile.svg    <- seamless tile built from the brand pattern motif
  img/                <- placeholder imagery — replace with real photography
```

`build.py` reads the logo geometry straight out of `assets/logo/*.svg`, so the
site can never drift from the supplied identity files.

---

## Page structure

1. **Hero** — 250vh sticky runway. Images cross-fade on a canvas and scale from
   1.4 to 1 as you scroll. English **AJID** on top, Arabic **عجيد** below, with
   the nav spread along the centre rule (a dot marks the current page).
2. **Opening statement** — line-by-line reveal.
3. **Intro note + three-image row.**
4. **Work** — chronological timeline. A year sits on the centre spine with a dot
   beneath it; the project image hangs off one side. Widths vary in 16ths so it
   reads as a collage, not a grid of equal tiles. On mobile the spine stays put:
   years to its left, images to its right.
5. **Chapter one** — large word-revealed heading, image, side note.
6. **Chapter two** — heading, pull quote, paragraph, image.
7. **Chapter three** — closing notes.
8. **Closing** — full-width image, then the closing statement.
9. **Footer** — contact row, then the giant **AJID / عجيد** wordmark with a
   photograph showing through the letterforms, then the rights row.

Each project row in the admin panel exposes its year, which side of the spine it
sits on, how wide it is, and its image shape — so the collage rhythm is yours to
tune without touching code.

## Motion

- **Opening:** the hero image starts as a small window in the middle of a dark
  screen and opens out to full bleed while the wordmark letters arrive.
- **Work timeline:** the centre spine draws downward with scroll, and each year
  lights up at the moment the tip of the line reaches it — one connected move.
- Per-letter reveal on the AJID wordmark; the Arabic wipes in along its reading
  direction with the three dots settling after.
- Word / line / character splitting on headings and paragraphs.
- `clip-path` image reveals with gentle parallax.
- Dividers draw out horizontally.
- Smooth scrolling on pointer devices (interpolates native scroll, so the
  sticky hero keeps working).
- Everything is disabled under `prefers-reduced-motion`.

## Performance

- Only the first hero frame blocks the loader; the rest load on idle.
- Project preview thumbnails are created on first hover, not up front.
- Fonts are WOFF2 with a metric-matched fallback, so the swap does not shift
  layout. Two weights are preloaded.
- Static HTML — nothing is rendered client-side.

---

## Notes

- **Placeholder photography.** `assets/img/` holds real interior and
  architecture photographs pulled from Wikimedia Commons under free licences
  (CC0 / public domain / CC BY / CC BY-SA). They stand in for AJID's own shoots.
  `assets/img/CREDITS.json` records the source, author and licence of every
  file, and `/credits.html` renders that as a page linked from the footer.
  **CC BY and CC BY-SA require attribution**, so keep that page up for as long
  as those images are in use — once the studio's own photography replaces them,
  delete the page and the footer link. Re-run `python tools_fetch_photos.py` to
  pull a fresh set.
- **Arabic** is never split character-by-character (that would break the
  connected script) — it animates by word instead.
- The Arabic pages keep the English wordmark on top and Arabic below, matching
  the logo lockup order.
