"""Original analytic needle painting, no source/reference image sampled."""
from PIL import Image,ImageDraw
from pathlib import Path
import math,random
root=Path(__file__).parent/'Textures';root.mkdir(exist_ok=True)
path=root/'Forest_NeedleFrond_v03_03.png'
if path.exists():raise RuntimeError('Do not overwrite painted revision')
scale=2;W,H=2048*scale,512*scale
im=Image.new('RGBA',(W,H),(44,96,66,0));d=ImageDraw.Draw(im)
rng=random.Random(230303)
dark=(36,77,53);mid=(44,96,66);light=(75,120,69)
def mix(a,b,t):return tuple(round(x+(y-x)*t) for x,y in zip(a,b))
def col(t,k=1):
    c=mix(dark,mid,min(t*2,1)) if t<.55 else mix(mid,light,(t-.55)/.45)
    return tuple(min(255,round(x*k)) for x in c)+(255,)
# Fine tapering central spine.
spine=[(0,H*.5),(W*.10,H*.48),(W*.82,H*.493),(W*.995,H*.50),(W*.82,H*.506),(W*.10,H*.52)]
d.polygon(spine,fill=col(.35))
# Independently tapered needles, swept forward along both edges; all colours from Forest greens.
for side in (-1,1):
    for i in range(42):
        t=.035+i*.0208+rng.uniform(-.006,.006)
        rootx=W*t;rooty=H*.5
        envelope=(math.sin(math.pi*(t*.91+.045))**.70)*(1-t)**.28
        length=H*.46*envelope*rng.uniform(.82,1.07)
        tipx=min(W*.99,rootx+W*(.045+.035*t)*rng.uniform(.75,1.2))
        tipy=rooty+side*length
        base=W*rng.uniform(.0065,.011)
        bendx=rootx+(tipx-rootx)*.45
        bendy=rooty+(tipy-rooty)*.72
        d.polygon([(rootx-base,rooty),(bendx-base*.50,bendy),(tipx,tipy),
                   (bendx+base*.36,bendy-side*H*.025),(rootx+base,rooty)],fill=col(t,rng.uniform(.94,1.06)))
        # A thin light edge distinguishes overlapping needles under soft Forest light.
        d.line([(rootx,rooty),(bendx,bendy),(tipx,tipy)],fill=col(min(.99,t+.18),1.02),width=2*scale)
im.resize((2048,512),Image.Resampling.LANCZOS).save(path)
print(path)
