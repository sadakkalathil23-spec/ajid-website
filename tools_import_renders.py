"""
Import the Studio Ajid renders from assets/incoming/ into their slots.

Mapped by hand rather than by orientation alone: the widest, most atmospheric
views carry the hero, one view of each space fronts the intro row, and the
portrait shots fill the timeline in room order.
"""
import pathlib, json, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ROOT = pathlib.Path(__file__).parent
SRC  = ROOT / "assets" / "incoming"
OUT  = ROOT / "assets" / "img"

def src(name):
    p = SRC / name
    if not p.exists():
        sys.exit(f"missing: {name}")
    return p

# ---- hero: the six widest views, opening on the full lounge ----------------
HERO = ["boss room02.jpg", "boss room.jpg", "meeting room01.jpg",
        "computer room_01.jpg", "meeting room03.jpg", "boss room03.jpg"]

# ---- intro row: one frame per space ----------------------------------------
FEATURE = ["boss room03.jpg", "computer room_01.jpg", "meeting room02.jpg"]

CLOSING  = "boss room02.jpg"
WORDMARK = "meeting room04.jpg"

# ---- timeline: portrait shots, grouped by space ----------------------------
WORK = ["boss room07.jpg", "boss room10.jpg", "boss room11.jpg",
        "computer room_03.jpg", "computer room_04.jpg",
        "meeting room05.jpg", "meeting room08.jpg",
        "meeting room09.jpg", "meeting room12.jpg"]

def fit(s, w, h, dst):
    with Image.open(s) as im:
        im = im.convert("RGB")
        k = max(w / im.width, h / im.height)
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
        l, t = (im.width - w) // 2, (im.height - h) // 2
        im.crop((l, t, l + w, t + h)).save(dst, quality=86, optimize=True, progressive=True)

for i, n in enumerate(HERO):
    fit(src(n), 1920, 1080, OUT / f"hero-{i+1}.jpg");  print(f"  hero-{i+1}      <- {n}")
for i, n in enumerate(FEATURE):
    fit(src(n), 1600, 1100, OUT / f"feat-{i+1}.jpg");  print(f"  feat-{i+1}      <- {n}")
fit(src(CLOSING),  1920, 1080, OUT / "closing.jpg");        print(f"  closing      <- {CLOSING}")
fit(src(WORDMARK), 1920, 1080, OUT / "wordmark-fill.jpg");  print(f"  wordmark     <- {WORDMARK}")
for i, n in enumerate(WORK):
    fit(src(n), 1400, 1750, OUT / f"work-{i+1:02d}.jpg");   print(f"  work-{i+1:02d}     <- {n}")

# the studio's own renders need no third-party attribution
(OUT / "CREDITS.json").write_text("[]", encoding="utf8")
print(f"\nimported {len(HERO)+len(FEATURE)+2+len(WORK)} images")
