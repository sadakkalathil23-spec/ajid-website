"""Generates brand-toned architectural placeholder imagery for AJID.
Abstract light/shadow studies in the brand palette - meant to be swapped for real photography."""
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import random, math, os

NAVY=(6,18,41); BROWN=(88,44,0); BEIGE=(213,207,198); GRAY=(130,130,130); BURG=(77,22,21); MIST=(116,135,150)

def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

def grad(w,h,top,bot,ang=0.0):
    im=Image.new("RGB",(w,h))
    d=ImageDraw.Draw(im)
    for y in range(h): d.line([(0,y),(w,y)],fill=lerp(top,bot,y/h))
    if ang: im=im.rotate(ang,resample=Image.BICUBIC,expand=False)
    return im

def light_patch(w,h,cx,cy,rx,ry,color,strength,blur):
    l=Image.new("L",(w,h),0)
    ImageDraw.Draw(l).ellipse([cx-rx,cy-ry,cx+rx,cy+ry],fill=int(255*strength))
    l=l.filter(ImageFilter.GaussianBlur(blur))
    return Image.new("RGB",(w,h),color), l

def grain(im,amt=9):
    w,h=im.size
    n=Image.effect_noise((w,h),amt).convert("L").convert("RGB")
    return ImageChops.overlay(im, n).point(lambda p:p) if False else Image.blend(im,ImageChops.add(im,n,scale=1.6,offset=-40),0.35)

def vignette(im,strength=0.55):
    w,h=im.size
    m=Image.new("L",(w,h),0)
    ImageDraw.Draw(m).ellipse([-w*0.28,-h*0.28,w*1.28,h*1.28],fill=255)
    m=m.filter(ImageFilter.GaussianBlur(min(w,h)*0.16))
    dark=Image.new("RGB",(w,h),(0,0,0))
    return Image.composite(im,Image.blend(im,dark,strength),m)

def compose(w,h,base_top,base_bot,shadow_col,light_col,seed,n_bars=6,mode="columns"):
    rnd=random.Random(seed)
    im=grad(w,h,base_top,base_bot)
    # warm light patch
    src,msk=light_patch(w,h,w*rnd.uniform(.25,.75),h*rnd.uniform(.15,.5),
                        w*rnd.uniform(.35,.6),h*rnd.uniform(.35,.6),light_col,rnd.uniform(.5,.8),min(w,h)*0.18)
    im=Image.composite(src,im,msk)
    # hard-edged architectural shadow geometry on its own layer
    sh=Image.new("L",(w,h),0); sd=ImageDraw.Draw(sh)
    if mode=="columns":
        # tapered columns echoing the AJID pattern motif
        cw=w/(n_bars*1.9); gap=cw*0.9; x=rnd.uniform(-cw,0); waist=cw*0.20
        while x<w:
            if rnd.random()<0.72:
                top=h*rnd.uniform(-.15,.12); bot=h*rnd.uniform(.88,1.2); tp=(bot-top)*0.17
                sd.polygon([(x,top),(x+cw,top),(x+cw-waist,top+tp),(x+cw-waist,bot-tp),(x+cw,bot),(x,bot),
                            (x+waist,bot-tp),(x+waist,top+tp)],fill=rnd.randint(120,220))
            x+=cw+gap*rnd.uniform(.5,1.4)
    elif mode=="vault":
        # sweeping shell curves
        for i in range(n_bars):
            yo=h*(i/n_bars)*1.1-h*.1; amp=h*rnd.uniform(.06,.16); th=h*rnd.uniform(.03,.09)
            pts=[(xx,yo+math.sin(xx/w*math.pi*rnd.uniform(.7,1.6)+i)*amp) for xx in range(0,w+20,20)]
            pts+= [(xx,yo+th+math.sin(xx/w*math.pi*rnd.uniform(.7,1.6)+i)*amp) for xx in range(w+20,-20,-20)]
            sd.polygon(pts,fill=rnd.randint(90,190))
    else: # planes
        for i in range(n_bars):
            x0=rnd.uniform(-w*.2,w); y0=rnd.uniform(-h*.2,h)
            sd.polygon([(x0,y0),(x0+w*rnd.uniform(.2,.7),y0-h*rnd.uniform(.05,.3)),
                        (x0+w*rnd.uniform(.2,.7),y0+h*rnd.uniform(.3,.9)),(x0,y0+h*rnd.uniform(.3,.9))],
                       fill=rnd.randint(70,170))
    sh=sh.filter(ImageFilter.GaussianBlur(min(w,h)*0.004))
    im=Image.composite(Image.new("RGB",(w,h),shadow_col),im,sh)
    im=im.filter(ImageFilter.GaussianBlur(0.6))
    im=vignette(im,0.5)
    im=grain(im,8)
    return im

PALETTES=[
    (lerp(BEIGE,BROWN,.15), lerp(BROWN,NAVY,.35), lerp(BROWN,NAVY,.55), lerp(BEIGE,(255,240,215),.5)),
    (lerp(BEIGE,GRAY,.25),  lerp(NAVY,GRAY,.30),  NAVY,                 lerp(BEIGE,(255,248,232),.6)),
    (lerp(BEIGE,BROWN,.05), lerp(BROWN,BEIGE,.25),BROWN,                (255,236,205)),
    (lerp(MIST,BEIGE,.45),  lerp(NAVY,MIST,.45),  NAVY,                 lerp(BEIGE,(255,252,242),.7)),
    (lerp(BEIGE,BURG,.10),  lerp(BURG,NAVY,.35),  BURG,                 lerp(BEIGE,(255,238,214),.55)),
    (lerp(GRAY,BEIGE,.55),  lerp(GRAY,NAVY,.45),  lerp(NAVY,GRAY,.25),  (250,244,230)),
]
MODES=["columns","vault","planes"]
os.makedirs("assets/img",exist_ok=True)
specs=[("hero-%d"%i,1920,1080) for i in range(1,7)]+[("work-%02d"%i,1200,1500) for i in range(1,13)]+[("feat-%d"%i,1600,1100) for i in range(1,4)]
for idx,(name,w,h) in enumerate(specs):
    bt,bb,sc,lc=PALETTES[idx%len(PALETTES)]
    im=compose(w,h,bt,bb,sc,lc,seed=1000+idx*7,n_bars=random.Random(idx).randint(4,9),mode=MODES[idx%3])
    im.save(f"assets/img/{name}.jpg",quality=76,optimize=True,progressive=True)
    # small blurred LQIP for instant paint
    im.resize((24,int(24*h/w))).save(f"assets/img/{name}-lqip.jpg",quality=40)
    print(name,w,h,os.path.getsize(f"assets/img/{name}.jpg")//1024,"KB")
