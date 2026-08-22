"""Re-fetch the interior shots that actually work and lay them across every slot."""
import urllib.parse, subprocess, json, pathlib, io
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
OUT = pathlib.Path("assets/img"); UA = "AJIDSiteBuilder/1.0 (contact hello@ajid.qa)"

creds = {c["file"]: c for c in json.loads((OUT/"CREDITS.json").read_text(encoding="utf8"))}
GOOD = ["hero-3.jpg","hero-5.jpg","hero-6.jpg","feat-1.jpg","feat-2.jpg","feat-3.jpg",
        "work-01.jpg","work-02.jpg","work-03.jpg","work-04.jpg","work-05.jpg",
        "work-07.jpg","work-08.jpg","work-09.jpg","work-10.jpg"]

def curl(u):
    return subprocess.run(["curl","-s","-m","45","-L","--ssl-no-revoke","-H",f"User-Agent: {UA}",u],
                          capture_output=True).stdout

def by_title(title):
    p={"action":"query","titles":"File:"+title,"prop":"imageinfo",
       "iiprop":"url","iiurlwidth":"2400","format":"json","formatversion":"2"}
    try:
        d=json.loads(curl("https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode(p))
                     .decode("utf8","replace"))
        ii=(d["query"]["pages"][0].get("imageinfo") or [{}])[0]
        return ii.get("thumburl") or ii.get("url")
    except Exception:
        return None

# ---- download the keepers once, at generous size ----
src = {}
for f in GOOD:
    c = creds.get(f)
    if not c: continue
    u = by_title(c["title"])
    if not u: print("  no url:", c["title"][:40]); continue
    data = curl(u)
    try:
        im = Image.open(io.BytesIO(data)); im.load(); src[f] = (im.convert("RGB"), c)
        print(f"  got {c['title'][:46]}  {im.size}")
    except Exception as e:
        print("  fail", c["title"][:40], e)

keys = [k for k in GOOD if k in src]
print("usable sources:", len(keys))

def fit(im,w,h):
    s=max(w/im.width,h/im.height)
    i2=im.resize((max(1,round(im.width*s)),max(1,round(im.height*s))),Image.LANCZOS)
    l=(i2.width-w)//2; t=(i2.height-h)//2
    return i2.crop((l,t,l+w,t+h))

# ---- lay them out: architecture up top, rooms in the work list ----
ARCH  = [k for k in keys if k in ("hero-5.jpg","hero-6.jpg","work-01.jpg","work-02.jpg",
                                  "feat-2.jpg","feat-3.jpg","feat-1.jpg","work-10.jpg")]
ROOMS = [k for k in keys if k in ("work-08.jpg","work-09.jpg","work-07.jpg","hero-3.jpg",
                                  "work-03.jpg","work-05.jpg","work-04.jpg")]
ARCH  = ARCH  or keys
ROOMS = ROOMS or keys

PLAN  = ([(f"hero-{i}", 1920, 1080, ARCH[(i-1) % len(ARCH)])            for i in range(1,7)]
       + [(f"feat-{i}", 1600, 1100, ROOMS[(i-1) % len(ROOMS)])          for i in range(1,4)]
       + [(f"work-{i:02d}", 1400, 1750,
           (ROOMS if i % 2 else ARCH)[(i-1) % len(ROOMS if i % 2 else ARCH)]) for i in range(1,13)]
       + [("closing", 1920, 1080, ARCH[0]), ("wordmark-fill", 1920, 1080, ARCH[1 % len(ARCH)])])

out_creds = {}
for name, w, h, key in PLAN:
    im, c = src[key]
    fit(im, w, h).save(OUT/f"{name}.jpg", quality=80, optimize=True, progressive=True)
    out_creds[f"{name}.jpg"] = {"file": f"{name}.jpg", **{k: c[k] for k in ("title","author","lic","page")}}
    print(f"  {name}.jpg <- {c['title'][:44]}")

(OUT/"CREDITS.json").write_text(json.dumps(list(out_creds.values()),ensure_ascii=False,indent=2),encoding="utf8")
print("wrote", len(out_creds), "images")
