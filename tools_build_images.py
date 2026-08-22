"""
Rebuild every site image from assets/incoming/.

One render per slot -- nothing is used twice. Output is WebP, quality stepped
down until each file clears 300 KB. Re-run this any time a render is replaced
in assets/incoming/ under the same filename.

    python tools_build_images.py && python build.py
"""
import pathlib, json, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ROOT = pathlib.Path(__file__).parent
SRC  = ROOT / "assets" / "incoming"
OUT  = ROOT / "assets" / "img"
CAP  = 300 * 1024          # never exceed this
FLOOR = 250 * 1024         # and do not fall below it -- quality over savings

HERO = ["boss room02.png", "meeting room01.jpg", "computer room_01.png",
        "meeting room03.jpg", "boss room.jpg"]
FEATURE = [("meeting room12.jpg", "bottom"),      # brass inlay sits at the foot
           ("boss room07.jpg",    "center"),
           ("computer room_03.jpg","center")]
WORK = [("boss room03.jpg",     (4, 3)),  ("boss room10.jpg",      (3, 4)),
        ("meeting room02.jpg",  (16, 9)), ("computer room_04.jpg", (3, 4)),
        ("meeting room04.jpg",  (16,10)), ("meeting room05.jpg",   (3, 4)),
        ("meeting room08.jpg",  (3, 4)),  ("meeting room09.jpg",   (3, 4)),
        ("boss room11.jpg",     (3, 4))]
CLOSING  = ("meeting room11.jpg", (16, 9))
WORDMARK = "ChatGPT Image Aug 20, 2026, 03_16_20 PM (1).png"

SRC_W = {}

def crop(name, ar, anchor="center", maxw=1900):
    f = SRC / name
    if not f.exists():
        sys.exit(f"missing source: {name}")
    with Image.open(f) as im:
        im = im.convert("RGB"); t = ar[0] / ar[1]; w, h = im.size
        if w / h > t:
            nw = round(h * t); l = (w - nw) // 2
            im = im.crop((l, 0, l + nw, h))
        else:
            nh = round(w / t)
            y = h - nh if anchor == "bottom" else (0 if anchor == "top" else (h - nh) // 2)
            im = im.crop((0, y, w, y + nh))
        SRC_W[name] = im.width
        ow = min(maxw, im.width)
        return im.resize((ow, round(im.height * ow / im.width)), Image.LANCZOS)

def save(im, name, src_w=None):
    """Land the file between FLOOR and CAP.

    Every attempt is resampled ONCE from the original crop -- never from a
    previous attempt and never by re-reading an encoded WebP, so no pass
    inherits another pass's compression artefacts.
    """
    dst   = OUT / name
    cap_w = src_w or im.width
    width = im.width
    chosen = None
    for _ in range(8):
        work = im if width == im.width else im.resize(
            (width, round(im.height * width / im.width)), Image.LANCZOS)
        chosen = None
        for q in (96, 92, 88, 84, 80, 74, 68, 62, 56, 50):
            work.save(dst, "WEBP", quality=q, method=6)
            if dst.stat().st_size <= CAP:
                chosen = (q, dst.stat().st_size)
                break
        if chosen is None:                          # too heavy even at q50
            width = int(width * 0.85)
            continue
        if chosen[1] >= FLOOR or width >= cap_w:
            return chosen
        grow = min(int(width * 1.18), cap_w)        # under the floor: add pixels
        if grow <= width:
            return chosen
        width = grow
    return chosen


used, log = [], []
for i, n in enumerate(HERO):
    q, s = save(crop(n, (16, 9)), f"hero-{i+1}.webp", SRC_W.get(n)); used.append(n)
    log.append((f"hero-{i+1}.webp", n, q, s))
feat_dims = []
for i, (n, a) in enumerate(FEATURE):
    im = crop(n, (3, 4), a, maxw=1400)
    q, s = save(im, f"feat-{i+1}.webp", SRC_W.get(n)); used.append(n); feat_dims.append(im.size)
    log.append((f"feat-{i+1}.webp", n, q, s))
for i, (n, ar) in enumerate(WORK):
    q, s = save(crop(n, ar), f"work-{i+1:02d}.webp", SRC_W.get(n)); used.append(n)
    log.append((f"work-{i+1:02d}.webp", n, q, s))
q, s = save(crop(*CLOSING), "closing.webp", SRC_W.get(CLOSING[0])); used.append(CLOSING[0])
log.append(("closing.webp", CLOSING[0], q, s))

# the footer lockup: one wall split so the two marks read as continuous
AL, AA = 5.276, 5.567
with Image.open(SRC / WORDMARK) as wm:
    wm = wm.convert("RGB"); W, H = wm.size
    cut = int(W * AL / (AL + AA))
    for half, ar, nm in ((wm.crop((0,0,cut,H)), AL, "wordmark-fill-lat.webp"),
                         (wm.crop((cut,0,W,H)), AA, "wordmark-fill-ar.webp")):
        w, h = half.size
        if w/h > ar: nw=int(h*ar); half = half.crop(((w-nw)//2,0,(w-nw)//2+nw,h))
        else:        nh=int(w/ar); half = half.crop((0,(h-nh)//2,w,(h-nh)//2+nh))
        ow = min(2400, half.width)
        q, s = save(half.resize((ow, int(ow/ar)), Image.LANCZOS), nm)
        log.append((nm, WORDMARK[:22]+"…", q, s))

dupes = [n for n in set(used) if used.count(n) > 1]
print(f"{'output':<24}{'source':<26}{'q':>4}{'KB':>7}")
for o, s_, q_, sz in log:
    print(f"{o:<24}{s_:<26}{q_:>4}{sz//1024:>7}")
print(f"\n{len(used)} renders, {len(set(used))} unique -> "
      f"{'REPEATS: '+', '.join(dupes) if dupes else 'no repeats'}")
print(f"largest file {max(l[3] for l in log)//1024} KB (cap {CAP//1024} KB)")

# keep the feature aspect ratios in sync with what was actually written
cfg = ROOT / "content" / "site.json"
d = json.loads(cfg.read_text(encoding="utf8"))
for lang in ("en", "ar"):
    for i, (w, h) in enumerate(feat_dims):
        d[lang]["features"][i]["w"], d[lang]["features"][i]["h"] = w, h
cfg.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf8")
print("feature dimensions synced to site.json")
