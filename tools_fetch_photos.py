"""Fetch freely-licensed interior/architecture photography from Wikimedia Commons
to stand in for AJID's own shoots. Records attribution for every file."""
import urllib.parse, subprocess, json, pathlib, io, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

OUT = pathlib.Path("assets/img")
OUT.mkdir(parents=True, exist_ok=True)
UA = "AJIDSiteBuilder/1.0 (placeholder sourcing; contact hello@ajid.qa)"

OK_LIC = ("cc0", "public domain", "cc by", "cc-by", "attribution")

QUERIES = [
    "minimalist interior architecture room",
    "brick vault ceiling interior",
    "modern living room interior design",
    "concrete interior architecture light",
    "hotel lobby interior design",
    "wooden interior architecture detail",
    "arched interior corridor architecture",
    "islamic architecture interior arches",
]

def curl(url):
    r = subprocess.run(["curl","-s","-m","40","-L","--ssl-no-revoke","-H",f"User-Agent: {UA}",url],
                       capture_output=True)          # bytes, no console decoding
    return r.stdout

def search(q, limit=8):
    p = {"action":"query","generator":"search","gsrsearch":q,"gsrnamespace":"6",
         "gsrlimit":str(limit),"prop":"imageinfo","iiprop":"url|extmetadata",
         "iiurlwidth":"2000","format":"json","formatversion":"2"}
    raw = curl("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p))
    try:
        return json.loads(raw.decode("utf8", "replace")).get("query", {}).get("pages", [])
    except Exception:
        return []

def usable(page):
    ii = (page.get("imageinfo") or [{}])[0]
    md = ii.get("extmetadata", {})
    lic = (md.get("LicenseShortName", {}).get("value", "") or "").lower()
    if not any(k in lic for k in OK_LIC):
        return None
    url = ii.get("thumburl") or ii.get("url")
    if not url:
        return None
    return {
        "title":  page.get("title", "").replace("File:", ""),
        "author": md.get("Artist", {}).get("value", "").replace("<span>", "")[:160],
        "lic":    md.get("LicenseShortName", {}).get("value", ""),
        "page":   ii.get("descriptionurl", ""),
        "url":    url,
    }

# ---- gather candidates -----------------------------------------------------
cands, seen = [], set()
for q in QUERIES:
    for pg in search(q):
        c = usable(pg)
        if c and c["title"] not in seen:
            seen.add(c["title"]); cands.append(c)
    print(f"  after '{q[:34]}': {len(cands)} candidates", flush=True)

print("total candidates:", len(cands))

# ---- download + fit --------------------------------------------------------
def grab(c):
    data = curl(c["url"])
    if len(data) < 20000:
        return None
    try:
        im = Image.open(io.BytesIO(data)); im.load()
        return im.convert("RGB")
    except Exception:
        return None

def fit(im, w, h):
    """cover-crop to exactly w x h"""
    s = max(w / im.width, h / im.height)
    im2 = im.resize((max(1,round(im.width*s)), max(1,round(im.height*s))), Image.LANCZOS)
    l = (im2.width - w) // 2; t = (im2.height - h) // 2
    return im2.crop((l, t, l + w, t + h))

TARGETS = ([("hero-%d" % i, 1920, 1080) for i in range(1, 7)]
         + [("feat-%d" % i, 1600, 1100) for i in range(1, 4)]
         + [("work-%02d" % i, 1400, 1750) for i in range(1, 13)])

credits, ti = [], 0
for c in cands:
    if ti >= len(TARGETS):
        break
    im = grab(c)
    if im is None or min(im.size) < 700:
        continue
    name, w, h = TARGETS[ti]
    fit(im, w, h).save(OUT / f"{name}.jpg", quality=80, optimize=True, progressive=True)
    credits.append({"file": f"{name}.jpg", **{k: c[k] for k in ("title","author","lic","page")}})
    print(f"  {name}.jpg  <- {c['title'][:44]}  [{c['lic']}]", flush=True)
    ti += 1

pathlib.Path("assets/img/CREDITS.json").write_text(
    json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf8")
print(f"\nsaved {ti} images + CREDITS.json")
