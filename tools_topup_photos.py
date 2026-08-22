"""Refill specific image slots with better interior shots, rejecting document scans."""
import urllib.parse, subprocess, json, pathlib, io, re
from PIL import Image, ImageStat
Image.MAX_IMAGE_PIXELS = None

OUT = pathlib.Path("assets/img"); UA = "AJIDSiteBuilder/1.0 (contact hello@ajid.qa)"
OK_LIC = ("cc0", "public domain", "cc by", "cc-by", "attribution")

def curl(u):
    return subprocess.run(["curl","-s","-m","40","-L","--ssl-no-revoke","-H",f"User-Agent: {UA}",u],
                          capture_output=True).stdout

def search(q, limit=14):
    p={"action":"query","generator":"search","gsrsearch":q,"gsrnamespace":"6","gsrlimit":str(limit),
       "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":"2000",
       "format":"json","formatversion":"2"}
    try:
        return json.loads(curl("https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode(p))
                          .decode("utf8","replace")).get("query",{}).get("pages",[])
    except Exception:
        return []

BAD_TITLE = re.compile(
    r"\(IA |\.pdf$|\.djvu|news|gazette|magazine|journal|newspaper|"
    r"readings|sketches|annual report|catalogue|almanac|bulletin|proceedings|"
    r"minutes|volume|vol|page \d", re.I)


def is_photo(im):
    """Reject scanned paper: near-white, near-grey, very low colour."""
    rgb = im.convert("RGB")
    st  = ImageStat.Stat(rgb)
    mean = sum(st.mean)/3
    hsv = ImageStat.Stat(rgb.convert("HSV"))
    sat = hsv.mean[1]
    if mean > 165 and sat < 42:            # paper / print scan
        return False
    if sat < 16:                            # essentially colourless
        return False
    if st.stddev and sum(st.stddev)/3 < 22: # flat / featureless
        return False
    return True

QUERIES = [
 "Luxury Living Room Interior Design",
 "Interior Design in Kolkata",
 "modern apartment interior photograph",
 "villa interior design photograph",
 "restaurant interior design photograph",
 "lobby interior architecture photograph",
 "vaulted brick ceiling photograph",
 "courtyard arches architecture photograph",
 "mosque interior arches photograph",
 "museum interior gallery photograph",
]

seen = set()
for p in (OUT/"CREDITS.json").exists() and json.loads((OUT/"CREDITS.json").read_text(encoding="utf8")) or []:
    seen.add(p["title"])

cands=[]
for q in QUERIES:
    for pg in search(q):
        ii=(pg.get("imageinfo") or [{}])[0]
        md=ii.get("extmetadata",{})
        lic=(md.get("LicenseShortName",{}).get("value","") or "").lower()
        title=pg.get("title","").replace("File:","")
        if title in seen or not any(k in lic for k in OK_LIC): continue
        if BAD_TITLE.search(title): continue
        url=ii.get("thumburl") or ii.get("url")
        if not url: continue
        seen.add(title)
        cands.append({"title":title,"lic":md.get("LicenseShortName",{}).get("value",""),
                      "author":md.get("Artist",{}).get("value","")[:160],
                      "page":ii.get("descriptionurl",""),"url":url})
print("candidates:",len(cands))

SLOTS=[("hero-1",1920,1080),("hero-2",1920,1080),("hero-4",1920,1080),
       ("work-06",1400,1750),("work-11",1400,1750),("work-12",1400,1750)]

def fit(im,w,h):
    s=max(w/im.width,h/im.height)
    im2=im.resize((round(im.width*s),round(im.height*s)),Image.LANCZOS)
    l=(im2.width-w)//2; t=(im2.height-h)//2
    return im2.crop((l,t,l+w,t+h))

creds=json.loads((OUT/"CREDITS.json").read_text(encoding="utf8"))
creds={c["file"]:c for c in creds}
si=0
for c in cands:
    if si>=len(SLOTS): break
    data=curl(c["url"])
    if len(data)<25000: continue
    try:
        im=Image.open(io.BytesIO(data)); im.load(); im=im.convert("RGB")
    except Exception: continue
    if min(im.size)<800 or not is_photo(im): 
        print("  skip (scan/flat/small):",c["title"][:40]); continue
    name,w,h=SLOTS[si]
    fit(im,w,h).save(OUT/f"{name}.jpg",quality=80,optimize=True,progressive=True)
    creds[f"{name}.jpg"]={"file":f"{name}.jpg",**{k:c[k] for k in ("title","author","lic","page")}}
    print(f"  {name}.jpg <- {c['title'][:44]} [{c['lic']}]")
    si+=1

(OUT/"CREDITS.json").write_text(json.dumps(list(creds.values()),ensure_ascii=False,indent=2),encoding="utf8")
print("refilled",si,"slots")
