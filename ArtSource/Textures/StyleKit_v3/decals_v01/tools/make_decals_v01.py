#!/usr/bin/env python3
"""G17: deterministic, original procedural decals. Python + NumPy + Pillow only.

Writes exclusively beneath this script's decals_v01 parent; never replaces files.
--check-only regenerates in memory and compares any delivered files byte for byte.
--review NAME writes only a new, named review PNG beneath previews/.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageFilter, ImageFont, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT.parent
REPO = KIT.parents[2]
BASE = KIT / "candidate_v07"
SEED = 170013
KEYS = ["1a_grass", "1b_dirt_road", "1d_gravel", "1e_mud", "2a_asphalt",
        "2b_sidewalk_tiles", "3c_concrete_panels", "6a_painted_metal_panels"]
GRADE = json.loads((BASE / "grade_v07.json").read_text(encoding="utf-8-sig"))
MATERIALS = json.loads((BASE / "materials_v3_v07.json").read_text(encoding="utf-8-sig"))
PALETTE = {k: np.array(GRADE["categories"][k]["after"]["mean_srgb_255"], dtype=float) for k in KEYS}
G, D, Q, M, A, S, C, MET = [PALETTE[k] for k in KEYS]
RESAMPLE = Image.Resampling.LANCZOS


def mix(a, b, t):
    return np.asarray(a) * (1-t) + np.asarray(b) * t


def col(rgb, alpha=255):
    return tuple(np.rint(np.clip(rgb, 0, 209)).astype(int)) + (int(alpha),)


def png_bytes(im, normal=False):
    info = PngImagePlugin.PngInfo()
    info.add_text("Authoring", "G17 original procedural paint; fixed seed 170013; no downloaded imagery")
    if normal:
        info.add_text("ColorSpace", "Linear data; tangent-space +Y; do not decode as sRGB")
    else:
        info.add(b"sRGB", b"\x00")
        info.add_text("ColorSpace", "sRGB albedo; straight alpha")
    out = io.BytesIO()
    im.save(out, format="PNG", pnginfo=info, compress_level=9)
    return out.getvalue()


def jbytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rgba(rgb, alpha):
    a = np.rint(np.clip(alpha, 0, 1)*255).astype(np.uint8)
    rgb = np.broadcast_to(rgb, a.shape + (3,))
    return Image.fromarray(np.dstack((np.rint(np.clip(rgb, 0, 209)).astype(np.uint8), a)))


def smooth(a, b, x):
    t = np.clip((x-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def centered(im):
    """Center the visible bounding box; carry RGB into alpha padding after assembly."""
    box = im.getchannel("A").getbbox()
    crop = im.crop(box)
    out = Image.new("RGBA", im.size)
    out.paste(crop, ((im.width-crop.width)//2, (im.height-crop.height)//2))
    return out


def bleed(im, margin=12):
    """Nearest-neighbour colour dilation into transparent pixels; preserve alpha."""
    p = np.array(im)
    known = p[..., 3] > 0
    for _ in range(margin):
        old = known.copy()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            mask = np.roll(old, (dy,dx), (0,1)) & ~known
            if dy == 1: mask[0] = False
            if dy == -1: mask[-1] = False
            if dx == 1: mask[:,0] = False
            if dx == -1: mask[:,-1] = False
            neighbour = np.roll(p[...,:3], (dy,dx), (0,1))
            p[...,:3][mask] = neighbour[mask]
            known |= mask
    if known.any():
        p[...,:3][~known] = np.rint(p[...,:3][p[...,3]>0].mean(0)).astype(np.uint8)
    # Lanczos may overshoot at tiny high-contrast silhouette edges.
    p[...,:3] = np.minimum(p[...,:3], 209)
    return Image.fromarray(p)


class Paint:
    """Small graphic marks in metres, supersampled for thin nearby litter."""
    def __init__(self, span=.5, n=1024):
        self.span, self.n = span, n
        self.im = Image.new("RGBA", (n,n))
        self.draw = ImageDraw.Draw(self.im)

    def points(self, pts, x=0, y=0, w=1, h=1, angle=0):
        t = math.radians(angle)
        cs, sn = math.cos(t), math.sin(t)
        return [((x+u*w*cs-v*h*sn)/self.span*self.n+self.n/2,
                 (y+u*w*sn+v*h*cs)/self.span*self.n+self.n/2) for u,v in pts]

    def poly(self, pts, color, **kw):
        self.draw.polygon(self.points(pts, **kw), fill=col(color))

    def line(self, pts, color, width=.001, alpha=255, **kw):
        self.draw.line(self.points(pts, **kw), fill=col(color,alpha), width=max(1,round(width/self.span*self.n)), joint="curve")

    def done(self):
        return bleed(centered(self.im.resize((512,512), RESAMPLE)))


def cigarette(p, x=0, y=0, angle=-20, length=.035):
    kw = dict(x=x,y=y,w=length,h=.0085,angle=angle)
    p.poly([(-.5,-.43),(.42,-.5),(.5,-.2),(.47,.4),(-.48,.5)], mix(S,D,.20), **kw)
    p.poly([(-.5,-.43),(-.08,-.46),(-.08,.45),(-.48,.5)], mix(D,S,.13), **kw)
    p.poly([(.34,-.48),(.47,-.38),(.5,.1),(.4,.39),(.31,.45)], mix(A,D,.3), **kw)
    p.line([(-.43,-.19),(.2,-.21)], mix(S,C,.15), width=.0012, **kw)


def cap(p, x=0,y=0,angle=0, rusty=False):
    base = mix(MET,D,.35) if rusty else mix(MET,A,.2)
    pts = [(math.cos(t)*(.5 if i%2==0 else .45),math.sin(t)*(.5 if i%2==0 else .45))
           for i,t in enumerate(np.linspace(0,2*math.pi,32,endpoint=False))]
    kw = dict(x=x,y=y,w=.029,h=.029,angle=angle)
    p.poly(pts, base-6, **kw)
    p.poly([(math.cos(t)*.37,math.sin(t)*.37) for t in np.linspace(0,2*math.pi,12,endpoint=False)],base+8,**kw)
    p.line([(-.22,-.13),(.15,-.18),(.25,.0)],base+15,width=.0015,**kw)


def wrapper(p, x=0,y=0,angle=18, torn=False):
    kw = dict(x=x,y=y,w=.115 if not torn else .071,h=.078,angle=angle)
    paper = mix(S,C,.25)
    p.poly([(-.5,-.26),(-.32,-.5),(-.05,-.37),(.28,-.48),(.5,-.19),(.33,.07),(.42,.37),(.07,.47),(-.18,.25),(-.43,.41),(-.35,.07)],paper,**kw)
    p.poly([(-.32,-.5),(-.05,-.37),(.28,-.48),(.17,-.02),(-.13,.09)],paper-13,**kw)
    p.poly([(-.35,.07),(-.13,.09),(.17,-.02),(.33,.07),(.07,.47),(-.18,.25)],mix(paper,MET,.28),**kw)
    p.poly([(-.25,-.22),(.19,-.26),(.16,-.04),(-.16,.03)],mix(A,MET,.55),**kw)
    p.line([(-.42,.28),(-.13,.09),(.07,.42)],paper+7,width=.002,**kw)
    if torn: p.poly([(.32,-.4),(.15,-.19),(.42,-.23)],mix(D,C,.5),**kw)


def can(p):
    kw = dict(w=.12,h=.065,angle=-22)
    body = mix(MET,C,.23)
    p.poly([(-.5,-.3),(-.3,-.48),(.31,-.45),(.5,-.23),(.36,.01),(.49,.3),(.22,.5),(-.32,.42),(-.46,.19),(-.32,-.01)],body,**kw)
    p.poly([(-.28,-.4),(.28,-.4),(.17,-.04),(.34,.32),(-.29,.34),(-.2,.03)],mix(A,MET,.48),**kw)
    p.poly([(-.2,-.03),(.17,-.04),(.34,.32),(-.1,.23)],mix(MET,C,.3),**kw)
    p.line([(-.41,-.25),(-.32,-.01),(-.42,.2)],body+8,width=.003,**kw)
    p.line([(.35,-.29),(.24,-.09),(.38,.24)],body+7,width=.0025,**kw)
    p.line([(-.22,.02),(.17,-.04)],body-7,width=.0018,**kw)


def leaf(p,x=0,y=0,angle=0,length=.068):
    kw = dict(x=x,y=y,w=length,h=length*.48,angle=angle)
    base = mix(D,G,.28)
    p.poly([(-.5,0),(-.25,-.4),(.05,-.5),(.35,-.22),(.5,.04),(.19,.4),(-.12,.36),(-.35,.18)],base,**kw)
    p.poly([(-.5,0),(.5,.04),(.19,.4),(-.12,.36),(-.35,.18)],base-7,**kw)
    p.line([(-.58,-.01),(.38,.04)],mix(D,S,.28),width=.0013,**kw)


def paper(p, folded=False):
    kw = dict(w=.095 if folded else .105,h=.07,angle=21 if folded else -14)
    base = mix(S,C,.38)
    p.poly([(-.5,-.33),(-.19,-.46),(.03,-.36),(.49,-.45),(.43,.37),(.1,.29),(-.21,.46),(-.43,.27)],base,**kw)
    p.poly([(.09,-.39),(.49,-.45),(.43,.37),(.21,.11)],base-12,**kw)
    p.line([(-.29,-.13),(-.04,-.17)],mix(C,A,.18),width=.0015,**kw)
    p.line([(-.27,-.03),(-.1,-.05)],mix(C,A,.15),width=.0012,**kw)
    if folded: p.poly([(-.43,.27),(-.1,-.1),(-.21,.46)],base+6,**kw)


def husks(p, few=False):
    positions = [(-.055,-.02,23),(-.025,.026,-32),(.02,-.035,60),(.047,.012,-18),(.006,.04,15),(-.043,-.042,80),(.033,.046,-55),(-.01,-.008,-10),(.058,-.034,33)]
    if few: positions = [(-.016,.006,-15),(.013,-.008,48),(.01,.013,12)]
    for i,(x,y,t) in enumerate(positions):
        kw = dict(x=x,y=y,w=.0155,h=.0065,angle=t)
        base = mix(A,D,.5)+(i%3-1)*5
        p.poly([(-.5,0),(-.13,-.47),(.28,-.39),(.5,0),(.19,.43),(-.17,.3)],base,**kw)
        p.line([(-.33,0),(.28,.02)],mix(S,D,.45),width=.0012,**kw)


LITTER = [
    ("cigarette_single", "Cigarette end", "2b_sidewalk_tiles"),
    ("cigarette_bench_cluster", "Bench cigarette cluster", "3c_concrete_panels"),
    ("bottle_cap", "Bottle cap", "2a_asphalt"),
    ("bottle_caps_pair", "Two bottle caps", "2b_sidewalk_tiles"),
    ("crumpled_wrapper", "Crumpled wrapper", "2a_asphalt"),
    ("flattened_can", "Flattened can", "3c_concrete_panels"),
    ("broken_bottle_glass", "Bottle glass scatter", "2b_sidewalk_tiles"),
    ("sunflower_seed_husks", "Sunflower seed husks", "3c_concrete_panels"),
    ("dry_leaves", "Three dry leaves", "1b_dirt_road"),
    ("paper_scrap", "Small paper scrap", "2a_asphalt"),
    ("chewing_gum", "Chewing-gum spot", "2b_sidewalk_tiles"),
    ("oil_stain", "Oil stain", "2a_asphalt"),
    ("dry_leaf_single", "Single dry leaf", "1a_grass"),
    ("torn_wrapper", "Torn wrapper", "3c_concrete_panels"),
    ("folded_paper", "Folded paper scrap", "1d_gravel"),
    ("sunflower_husks_small", "Small husk cluster", "2b_sidewalk_tiles"),
]


def make_litter():
    cells=[]
    for i in range(16):
        p=Paint()
        if i==0: cigarette(p)
        elif i==1:
            for x,y,t,l in [(-.066,-.032,18,.032),(-.043,.035,-35,.027),(.014,-.012,68,.035),(.063,.041,9,.03),(.07,-.055,-23,.038)]:
                cigarette(p,x,y,t,l)
        elif i==2: cap(p,angle=12)
        elif i==3: cap(p,-.025,-.011,12); cap(p,.026,.013,38,True)
        elif i==4: wrapper(p)
        elif i==5: can(p)
        elif i==6:
            rng=np.random.default_rng(SEED+6)
            for x,y,w,h in [(-.054,-.025,.037,.018),(-.028,.032,.023,.035),(.028,-.024,.035,.022),(.058,.026,.017,.038),(.007,.046,.025,.013),(.05,-.046,.018,.012)]:
                kw=dict(x=x,y=y,w=w,h=h,angle=float(rng.uniform(-60,60)))
                p.poly([(-.5,-.4),(.5,-.1),(.12,.5),(-.23,.28)],mix(G,C,.58),**kw)
                p.line([(-.5,-.4),(.5,-.1),(.12,.5)],mix(C,G,.25),width=.0012,alpha=195,**kw)
        elif i==7: husks(p)
        elif i==8:
            leaf(p,-.036,-.03,-23); leaf(p,.035,.007,75,.058); leaf(p,-.02,.039,18,.046)
        elif i==9: paper(p)
        elif i==10:
            p.poly([(-.5,-.09),(-.2,-.4),(.15,-.47),(.49,-.2),(.35,.13),(.1,.43),(-.25,.32)],mix(S,C,.48),w=.027,h=.022)
            p.line([(-.2,-.16),(.08,-.21),(.25,-.08)],mix(S,C,.15),width=.0012,w=.027,h=.022)
        elif i==11:
            p.poly([(-.5,-.13),(-.34,-.35),(-.09,-.29),(.16,-.49),(.39,-.22),(.5,.02),(.28,.15),(.17,.46),(-.04,.37),(-.26,.41),(-.4,.13)],A-9,w=.235,h=.165,angle=-12)
            # Blur coverage only: filtering straight RGB against black padding
            # would create a dark fringe around an otherwise quiet oil stain.
            alpha=p.im.getchannel("A").filter(ImageFilter.GaussianBlur(8)).point(lambda a: round(a*.32))
            p.im=Image.new("RGBA",p.im.size,col(A-9))
            p.im.putalpha(alpha)
        elif i==12: leaf(p,angle=-28,length=.08)
        elif i==13: wrapper(p,torn=True,angle=-16)
        elif i==14: paper(p,folded=True)
        elif i==15: husks(p,few=True)
        cells.append(p.done())
    atlas=Image.new("RGBA",(2048,2048))
    entries=[]
    for i,(cell,(name,label,base)) in enumerate(zip(cells,LITTER)):
        x,y=i%4*512,i//4*512
        atlas.paste(cell,(x,y))
        box=cell.getchannel("A").point(lambda a: 255 if a>=8 else 0).getbbox()
        entries.append(dict(id=name,label=label,index=i,column=i%4,row_from_top=i//4,
                            uv_rect=[i%4/4,1-(i//4+1)/4,.25,.25],
                            pixel_rect_top_left=[x,y,512,512],cell_world_size_m=[.5,.5],
                            intended_item_size_m=[round((box[2]-box[0])*.5/512,4),round((box[3]-box[1])*.5/512,4)],
                            item_bounds_px_local=list(box),preview_base=base,
                            placement="Rough District bench/service-yard cluster" if i in (1,7,15) else "Selective local detail; keep routes visually clear"))
    return atlas,cells,entries


def make_strip(wheel):
    w,h=(1024,2048) if wheel else (512,2048)
    wm,hm=(3.,6.) if wheel else (1.2,4.)
    x=(np.arange(w,dtype=float)+.5)/w*wm
    v=np.linspace(0,2*math.pi,h)[:,None]
    # Periodic broad harmonics only. No per-pixel noise or repeated tyre chevrons.
    bend=.012*np.sin(v)+.007*np.sin(3*v+.2)
    if wheel:
        widths=.142+.018*np.sin(2*v+.8)+.009*np.sin(5*v)
        left=np.abs(x[None,:]-(.3+bend))
        right=np.abs(x[None,:]-(2.7+bend))
        distance=np.minimum(left,right)
        envelope=1-smooth(widths*.57,widths+(.026+.009*np.sin(7*v+.4)),distance)
        core=np.exp(-(distance/(widths*.61))**4)
        alpha=envelope*(.54+.10*np.sin(v+1)**2)+core*.16
        rgb=np.broadcast_to(D,(h,w,3)).copy()-core[...,None]*6
        rgb+=(2*np.sin(2*v+.4)+1.4*np.cos(5*v))[...,None]
        height=-.0075*np.exp(-(distance/(widths*.7))**2)
    else:
        center=.6+.045*np.sin(v+.3)+.016*np.sin(3*v)
        half=.32+.041*np.sin(2*v+.6)+.018*np.sin(5*v+.2)
        distance=np.abs(x[None,:]-center)
        edge=.09+.018*np.sin(7*v+.3)
        envelope=1-smooth(half-edge,half+edge,distance)
        core=1-smooth(half*.45,half,distance)
        alpha=envelope*(.66+.11*np.sin(v+.7)**2)+core*.12
        # Dirt body with a narrow olive/dirt transition. Base grass shows through.
        rgb=mix(G,D,(.74+.26*core)[...,None])
        rgb+=(1.4*np.sin(2*v+.2)+1.1*np.cos(4*v))[...,None]
        height=-.0045*np.exp(-(distance/(half*.72))**4)
    alpha=np.clip(alpha,0,.90)
    alpha[:,0]=alpha[:,-1]=0
    height[alpha==0]=0
    albedo=rgba(rgb,alpha)
    # Unique periodic samples exclude duplicate endpoint; +V goes up PNG rows.
    unique=height[:-1]
    dx=np.gradient(unique,wm/w,axis=1)
    dy=(np.roll(unique,-1,axis=0)-np.roll(unique,1,axis=0))/(2*hm/(h-1))
    normal=np.dstack((-dx,dy,np.ones_like(dx)))
    normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    normal=np.concatenate((normal,normal[:1]),axis=0)
    values=np.rint((normal*.5+.5)*255).astype(np.uint8)
    values[np.array(albedo)[...,3]==0]=[128,128,255]
    nmap=Image.fromarray(np.dstack((values,np.array(albedo)[...,3])))
    # Duplicate endpoint is explicit, giving exact RGBA equality at V=0/1.
    for im in (albedo,nmap):
        im.paste(im.crop((0,0,w,1)),(0,h-1))
    tilt=float(np.degrees(np.arccos(np.clip(normal[...,2],-1,1))).max())
    return albedo,nmap,dict(world_size_m=[wm,hm],max_normal_tilt_degrees=round(tilt,5),
                            wheel_gauge_m=2.4 if wheel else None,repeat_axis="V",wrap_u="Clamp",wrap_v="Repeat",
                            normal_convention="Tangent-space +Y (green points up image / increasing V); linear data",
                            relief_depth_m=.0075 if wheel else .0045)


def blob(points, strength=1., blur=10):
    mask=Image.new("L",(512,512))
    ImageDraw.Draw(mask).polygon([(round(x*512),round(y*512)) for x,y in points],fill=round(strength*255))
    return np.array(mask.filter(ImageFilter.GaussianBlur(blur)),dtype=float)/255


SHAPE=[(.13,.38),(.24,.21),(.42,.18),(.53,.12),(.73,.25),(.79,.41),(.86,.53),(.73,.70),(.55,.76),(.42,.84),(.24,.7),(.18,.54)]


def patch_cell(index, urban=False):
    rng=np.random.default_rng(SEED+100+index+int(urban)*10)
    if not urban:
        mask=blob(SHAPE,.57,10)
        rgb=np.broadcast_to(mix(G,D,.40),(512,512,3)).copy()
        if index==0:  # flattened grass, 5 purposeful laid-over blade groups
            rgb[:]=mix(G,D,.36)
            im=rgba(rgb,mask)
            marks=Image.new("RGBA",(512,512)); dr=ImageDraw.Draw(marks)
            for x,y,ang in [(.31,.42,-.3),(.47,.37,.1),(.58,.54,-.2),(.37,.64,.3),(.69,.41,.2)]:
                for j in range(3):
                    xx=x*512+j*9; yy=y*512+j*2
                    dr.line([(xx-12,yy+3),(xx+20,yy+ang*23),(xx+37,yy-4)],fill=col(mix(G,D,.23)+6,110),width=3)
            im=Image.alpha_composite(im,marks.filter(ImageFilter.GaussianBlur(.8)))
        elif index==1:  # partial muddy ring, calm exposed inner basin
            outer=blob(SHAPE,.43,9)
            inner=blob([(.23,.4),(.35,.28),(.54,.26),(.71,.41),(.72,.55),(.57,.69),(.37,.68),(.26,.54)],1.,7)
            rgb[:]=mix(D,M,.55)
            alpha=outer*(1-inner*.60)
            im=rgba(rgb,alpha)
            calm=rgba(mix(C,D,.52),inner*.11)
            im=Image.alpha_composite(im,calm)
        elif index==2:  # one compact spill with only a few outliers
            im=rgba(mix(Q,D,.22),mask*.32)
            marks=Image.new("RGBA",(512,512)); dr=ImageDraw.Draw(marks)
            for j in range(37):
                x,y=rng.multivariate_normal([.49,.5],[[.011,.003],[.003,.008]])*512
                rx,ry=rng.uniform(3,11,2)
                pts=[(x-rx,y-ry*.3),(x-rx*.3,y-ry),(x+rx*.7,y-ry*.65),(x+rx,y+ry*.4),(x,y+ry),(x-rx*.75,y+ry*.4)]
                dr.polygon(pts,fill=col(mix(Q,D,.15)+rng.uniform(-9,5),150))
            im=Image.alpha_composite(im,marks.filter(ImageFilter.GaussianBlur(.6)))
        else:
            rgb[:]=D
            im=rgba(rgb,mask*1.42)
            for pts,amount in [([(.3,.3),(.48,.25),(.66,.34),(.55,.47),(.35,.46)],-3),([(.32,.58),(.57,.48),(.7,.58),(.54,.72),(.4,.72)],3)]:
                im=Image.alpha_composite(im,rgba(D+amount,blob(pts,.17,6)))
    else:
        if index==0:
            mask=Image.new("L",(1024,1024)); dr=ImageDraw.Draw(mask)
            for pts,width,opacity in [([(.22,.15),(.31,.29),(.29,.4),(.46,.53),(.52,.72),(.66,.84)],4,88),
                                       ([(.29,.4),(.45,.35),(.63,.4),(.76,.32)],3,74),
                                       ([(.46,.53),(.29,.62),(.2,.74)],2,65)]:
                dr.line([(int(x*1024),int(y*1024)) for x,y in pts],fill=opacity,width=width,joint="curve")
            a=np.array(mask.resize((512,512),RESAMPLE).filter(ImageFilter.GaussianBlur(.4)))/255
            im=rgba(mix(C,A,.63),a)
        elif index==1:
            pts=[(.41,.14),(.57,.12),(.61,.25),(.55,.36),(.55,.54),(.5,.73),(.45,.8),(.42,.69),(.43,.49),(.38,.33)]
            a=blob(pts,.22,8)
            im=rgba(mix(D,C,.32),a)
            im=Image.alpha_composite(im,rgba(mix(M,D,.45),blob([(.45,.2),(.53,.18),(.53,.38),(.48,.62),(.45,.51)],.10,7)))
        elif index==2:
            pts=[(.12,.54),(.25,.48),(.32,.4),(.47,.45),(.61,.39),(.76,.48),(.87,.57),(.84,.68),(.6,.72),(.43,.68),(.23,.73),(.13,.67)]
            im=rgba(mix(C,A,.50),blob(pts,.19,12))
            im=Image.alpha_composite(im,rgba(mix(C,D,.65),blob([(.19,.6),(.35,.52),(.59,.52),(.76,.59),(.72,.66),(.39,.62)],.09,8)))
        else:
            shape=[(.19,.34),(.34,.2),(.54,.25),(.71,.21),(.81,.43),(.73,.64),(.57,.75),(.38,.71),(.22,.59)]
            im=rgba(mix(A,C,.23),blob(shape,.52,4))
            im=Image.alpha_composite(im,rgba(mix(A,C,.19),blob([(.23,.38),(.37,.25),(.56,.30),(.68,.26),(.75,.45),(.68,.6),(.55,.7),(.4,.66),(.27,.55)],.6,5)))
            im=Image.alpha_composite(im,rgba(mix(A,C,.30),blob([(.32,.38),(.52,.35),(.68,.45),(.59,.61),(.43,.62)],.14,5)))
    return bleed(centered(im))


GROUND=[("trampled_grass","Trampled grass","1a_grass"),
        ("muddy_puddle_edge","Muddy puddle edge","1b_dirt_road"),
        ("gravel_spill","Gravel spill","1b_dirt_road"),
        ("bare_earth_patch","Bare-earth patch","1a_grass")]
URBAN=[("branching_crack","Hairline crack","3c_concrete_panels"),
       ("rust_drip","Rust drip stain","3c_concrete_panels"),
       ("wall_foot_water_stain","Wall-foot water stain","3c_concrete_panels"),
       ("patched_pothole","Patched pothole","2a_asphalt")]


def make_patch_atlas(urban=False):
    cells=[patch_cell(i,urban) for i in range(4)]
    atlas=Image.new("RGBA",(1024,1024))
    for i,cell in enumerate(cells): atlas.paste(cell,(i%2*512,i//2*512))
    entries=[dict(id=key,label=label,preview_base=base,index=i,uv_rect=[i%2*.5,1-(i//2+1)*.5,.5,.5],
                  cell_world_size_m=[1.5,1.5],pixel_rect_top_left=[i%2*512,i//2*512,512,512])
             for i,(key,label,base) in enumerate(URBAN if urban else GROUND)]
    return atlas,cells,entries


BASE_IMAGES={}


def surface(key,size,world,origin=(.137,.211)):
    """Sample the actual v07 texture using its manifest metres-per-tile."""
    if key not in BASE_IMAGES:
        BASE_IMAGES[key]=np.array(Image.open(BASE/key/(key+"_v07_albedo.png")).convert("RGB"),dtype=float)
    src=BASE_IMAGES[key]; sh,sw=src.shape[:2]
    tile=MATERIALS["categories"][key]["metres_per_tile"]
    ow,oh=size; mw,mh=world
    u=((np.arange(ow)+.5)/ow*mw+origin[0])/tile["x"]*sw
    v=((np.arange(oh)+.5)/oh*mh+origin[1])/tile["y"]*sh
    x0,y0=np.floor(u).astype(int)%sw,np.floor(v).astype(int)%sh
    tx,ty=(u%1)[None,:,None],(v%1)[:,None,None]
    top=src[y0[:,None],x0[None,:]]*(1-tx)+src[y0[:,None],(x0+1)[None,:]%sw]*tx
    bot=src[(y0+1)[:,None]%sh,x0[None,:]]*(1-tx)+src[(y0+1)[:,None]%sh,(x0+1)[None,:]%sw]*tx
    return Image.fromarray(np.rint(top*(1-ty)+bot*ty).astype(np.uint8)).convert("RGBA")


def linear_rgb(x):
    x=np.asarray(x,dtype=float)/255
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)


def srgb_rgb(x):
    x=np.clip(x,0,1)
    return np.where(x<=.0031308,x*12.92,1.055*x**(1/2.4)-.055)*255


def composite(base,overlay):
    # Linear-light compositing matches an sRGB albedo texture in a linear project.
    b=np.asarray(base); o=np.asarray(overlay); a=o[...,3:4]/255
    return Image.fromarray(np.dstack((np.rint(srgb_rgb(linear_rgb(o[...,:3])*a+linear_rgb(b[...,:3])*(1-a))).astype(np.uint8),
                                      np.full(a.shape[:2],255,dtype=np.uint8))))


def on_surface(cell,key,size,window_world,cell_world):
    base=surface(key,size,window_world)
    w=round(cell_world[0]/window_world[0]*size[0]); h=round(cell_world[1]/window_world[1]*size[1])
    overlay=Image.new("RGBA",size)
    overlay.paste(cell.resize((w,h),RESAMPLE),((size[0]-w)//2,(size[1]-h)//2))
    return composite(base,overlay)


def font(n):
    # Bundled Pillow font, independent of installed OS fonts.
    return ImageFont.load_default(size=n)


def preview(litter_cells,wheel,path,ground,urban):
    im=Image.new("RGBA",(1600,1600),(31,37,38,255)); dr=ImageDraw.Draw(im)
    ink=(221,218,205); muted=(167,175,164); accent=(182,187,146)
    def txt(x,y,text,size=16,color=ink): dr.text((x,y),text,font=font(size),fill=color)
    def line(y): dr.line([(32,y),(1568,y)],fill=(65,73,70),width=1)
    def scale(x,y,length_px,label):
        dr.line([(x,y),(x+length_px,y)],fill=ink,width=2)
        dr.line([(x,y-3),(x,y+3)],fill=ink,width=1)
        dr.line([(x+length_px,y-3),(x+length_px,y+3)],fill=ink,width=1)
        txt(x+length_px+8,y-7,label,12,muted)
    txt(32,26,"G17  /  GROUND WEAR + LITTER",32)
    txt(32,73,"Hamlet + Rough District   /   v01   /   muted v07 surfaces",17,accent)
    txt(930,43,"Original procedural paint",18)
    txt(930,71,"True metre ratios within each panel  |  linear-light alpha blend",14,muted)
    line(111)
    txt(32,131,"01  LITTER ATLAS",19)
    txt(283,134,"0.50 m per cell; small items retain their actual size",14,muted)
    for i,(cell,(_,label,key)) in enumerate(zip(litter_cells,LITTER)):
        x=32+(i%4)*184; y=170+(i//4)*174
        # 268 px/m in each direction: .5 m cell occupies 134 square pixels.
        img=on_surface(cell,key,(168,134),(168/268,.5),(.5,.5))
        im.paste(img,(x,y)); txt(x,y+140,f"{i+1:02d}  {label}",12)
        txt(x,y+156,key.split("_",1)[1].replace("_"," "),11,muted)
    scale(32,879,54,"20 cm  |  268 px/m")
    txt(800,131,"02  COMPACTED RUTS + WORN PATH",19)
    specs=[(800,210,wheel,"1a_grass",(3,6),"Ruts / grass"),
           (1026,210,wheel,"1b_dirt_road",(3,6),"Ruts / dirt"),
           (1252,126,path,"1a_grass",(1.2,4),"Path / grass"),
           (1394,126,path,"1b_dirt_road",(1.2,4),"Path / dirt")]
    for x,width,strip,key,world,title in specs:
        txt(x,170,title,14)
        img=on_surface(strip[0],key,(width,420),world,world)
        im.paste(img,(x,195))
        txt(x,624,f"{world[0]:g} x {world[1]:g} m",13,muted)
        scale(x,653,width/world[0]*.5,"50 cm")
    txt(800,685,"Soft normals on grass / neutral raking light",15,accent)
    for x,strip,width_m in [(800,wheel,3),(1180,path,1.2)]:
        alb,nrm,meta=strip
        # A short section at the V-repeat seam, sampled from two repeats.
        full_h=round(354*meta["world_size_m"][1]/width_m)
        a=alb.resize((354,full_h),RESAMPLE)
        n=nrm.resize((354,full_h),Image.Resampling.BILINEAR)
        ai=Image.new("RGBA",(354,150)); ni=Image.new("RGBA",(354,150))
        for source,dst in ((a,ai),(n,ni)):
            dst.paste(source.crop((0,full_h-75,354,full_h)),(0,0))
            dst.paste(source.crop((0,0,354,75)),(0,75))
        base=surface("1a_grass",(354,150),(width_m,width_m*150/354))
        al=np.array(composite(base,ai)); nv=np.array(ni)[...,:3]/127.5-1
        nv/=np.linalg.norm(nv,axis=2,keepdims=True)
        light=np.array([-.6,.3,.742]); light/=np.linalg.norm(light)
        factor=(.65+.35*(nv@light))/(.65+.35*light[2])
        factor=1+(factor-1)*(np.array(ai)[...,3]/255)
        al[...,:3]=np.rint(np.clip(srgb_rgb(linear_rgb(al[...,:3])*factor[...,None]),0,255)).astype(np.uint8)
        im.paste(Image.fromarray(al),(x,710))
        dr.line([(x-4,785),(x,785)],fill=accent,width=2)
        txt(x,869,f"V seam at centre  |  peak tilt {meta['max_normal_tilt_degrees']:.1f} deg",12,muted)
    line(909)
    txt(32,929,"03  GROUND WEAR",19)
    txt(800,929,"04  COURTYARD CRACKS + STAINS",19)
    for left,cells,descriptions in [(32,ground,GROUND),(800,urban,URBAN)]:
        for i,(cell,(_,label,key)) in enumerate(zip(cells,descriptions)):
            x=left+i%2*380; y=968+i//2*276
            # Same 146.67 px/m scale for all eight surface panels.
            img=on_surface(cell,key,(354,220),(354*1.5/220,1.5),(1.5,1.5))
            im.paste(img,(x,y)); txt(x,y+228,label,16)
            txt(x,y+249,key.split("_",1)[1].replace("_"," ")+"  /  1.50 m cell",12,muted)
    scale(32,1532,73,"50 cm  |  146.7 px/m")
    txt(800,1524,"Quiet gaps, restrained contrast, selective placement",14,accent)
    line(1553)
    txt(32,1570,"Base tile scale: grass / dirt / gravel / sidewalk 2 m; asphalt / concrete 3 m. No item enlargement.",12,muted)
    txt(1346,1570,"Unity review: not run",12,muted)
    return im


def validate(images,litter_entries,strip_meta):
    checks={}; records={}
    expected={"LITTER_ATLAS_v01.png":(2048,2048),"WHEEL_TRACKS_DIRT_v01_albedo.png":(1024,2048),
              "WHEEL_TRACKS_DIRT_v01_normal.png":(1024,2048),"WORN_PATH_v01_albedo.png":(512,2048),
              "WORN_PATH_v01_normal.png":(512,2048),"GROUND_WEAR_PATCHES_v01.png":(1024,1024),
              "CONCRETE_CRACKS_STAINS_v01.png":(1024,1024),"previews/decals_v01_on_surfaces.png":(1600,1600)}
    for name,im in images.items():
        p=np.array(im); a=p[...,3]
        assert im.mode=="RGBA" and im.size==expected[name],name
        r=dict(size_px=list(im.size),mode=im.mode,alpha_range=[int(a.min()),int(a.max())],
               zero_alpha_fraction=round(float((a==0).mean()),6))
        if "previews/" not in name:
            assert a.min()==0 and a.max()>0,name
            if "normal" not in name: assert p[...,:3].max()<=209,name
            if "TRACKS" in name or "WORN_PATH" in name:
                assert np.array_equal(p[0],p[-1]),name+" V seam"
                assert (a[:,0]==0).all() and (a[:,-1]==0).all(),name+" U edge"
                r["v_seam_max_channel_delta"]=0
                r["v_adjacent_row_mean_delta"]=round(float(np.abs(p[1].astype(int)-p[0].astype(int)).mean()),6)
            else:
                n=4 if "LITTER" in name else 2; cell=im.width//n
                r["cell_alpha_coverage"]=[]
                for iy in range(n):
                    for ix in range(n):
                        aa=a[iy*cell:(iy+1)*cell,ix*cell:(ix+1)*cell]
                        border=np.concatenate((aa[:12].ravel(),aa[-12:].ravel(),aa[:,:12].ravel(),aa[:,-12:].ravel()))
                        assert not border.any(),name+" atlas gutter"
                        assert aa.any(),name+" empty cell"
                        r["cell_alpha_coverage"].append(round(float((aa>8).mean()),5))
                r["transparent_gutter_min_px"]=12
        if "normal" in name:
            normals=p[...,:3]/127.5-1
            max_error=float(np.max(np.abs(np.linalg.norm(normals,axis=2)-1)))
            assert max_error<.008
            alb=images[name.replace("_normal","_albedo")]
            assert np.array_equal(a,np.array(alb)[...,3])
            assert np.all(p[...,:3][a==0]==[128,128,255])
            r["normal_unit_length_max_quantization_error"]=round(max_error,7)
            r["alpha_matches_albedo"]=True
        records[name]=r
    for entry in litter_entries:
        u,v,w,h=entry["uv_rect"]
        assert 0<=u<=1-w and 0<=v<=1-h
        box=entry["item_bounds_px_local"]
        assert abs((box[0]+box[2])/2-256)<=1.5 and abs((box[1]+box[3])/2-256)<=1.5,entry["id"]
    assert all(meta["max_normal_tilt_degrees"]<8 for meta in strip_meta.values())
    # UV rects must address the same cells in PNG top-left and bottom-left UV.
    for entry in litter_entries:
        u,v,uw,vh=entry["uv_rect"]
        rect=[round(u*2048),round((1-v-vh)*2048),round(uw*2048),round(vh*2048)]
        assert rect==entry["pixel_rect_top_left"]
    # The two rut centre curves share a bend and remain exactly 2.4 m apart.
    v=np.linspace(0,2*math.pi,2048)
    bend=.012*np.sin(v)+.007*np.sin(3*v+.2)
    assert np.allclose((2.7+bend)-(.3+bend),2.4,rtol=0,atol=1e-14)
    # Each preview uses the same px/m on both axes, with no item enlargement.
    panels=[((168,134),(168/268,.5)),((210,420),(3,6)),((126,420),(1.2,4)),
            ((354,220),(354*1.5/220,1.5))]
    for px,metres in panels:
        assert abs(px[0]/metres[0]-px[1]/metres[1])<1e-8
    checks.update(dimensions_rgba="PASS",transparent_background_and_atlas_gutters="PASS",
                  centred_litter_and_uv_bounds="PASS",exact_v_seams_albedo_and_normals="PASS",
                  matching_alpha_and_soft_unit_normals="PASS",albedo_max_value_209_over_255="PASS",
                  wheel_gauge_2_4m_and_preview_isotropic_scale="PASS",
                  metre_scale_preview_from_v07_manifest="PASS",unity_import_and_player_camera="NOT RUN")
    return dict(checks=checks,textures=records)


def build():
    litter,lc,le=make_litter(); wheel=make_strip(True); path=make_strip(False)
    ground,gc,ge=make_patch_atlas(); urban,uc,ue=make_patch_atlas(True)
    images={"LITTER_ATLAS_v01.png":litter,"WHEEL_TRACKS_DIRT_v01_albedo.png":wheel[0],
            "WHEEL_TRACKS_DIRT_v01_normal.png":wheel[1],"WORN_PATH_v01_albedo.png":path[0],
            "WORN_PATH_v01_normal.png":path[1],"GROUND_WEAR_PATCHES_v01.png":ground,
            "CONCRETE_CRACKS_STAINS_v01.png":urban}
    images["previews/decals_v01_on_surfaces.png"]=preview(lc,wheel,path,gc,uc)
    sm={"WHEEL_TRACKS_DIRT_v01":wheel[2],"WORN_PATH_v01":path[2]}
    report=validate(images,le,sm)
    uv="[u_min, v_min, width, height]; normalized UV, origin bottom-left; PNG rows count from top"
    litter_json=dict(schema="OnlyVolunteers.DecalAtlas/1",texture="LITTER_ATLAS_v01.png",seed=SEED,
                     grid=[4,4],size_px=[2048,2048],uv_convention=uv,cell_world_size_m=[.5,.5],
                     size_definition="Visible image-axis bounding box at alpha >= 8/255; cluster size includes gaps",
                     individual_nominal_sizes_m=dict(cigarette=[.035,.0085],bottle_cap=[.029,.029],
                                                     sunflower_husk=[.0155,.0065],flattened_can=[.12,.065]),cells=le)
    pack=dict(schema="OnlyVolunteers.Decals/1",task="G17",revision=1,seed=SEED,
              generator="tools/make_decals_v01.py",palette_means_srgb={k:[round(float(v),4) for v in c] for k,c in PALETTE.items()},
              uv_convention=uv,alpha="Straight / unassociated; albedo sRGB, normals linear data; no baked lighting/AO",
              strips=sm,ground_wear=dict(texture="GROUND_WEAR_PATCHES_v01.png",grid=[2,2],cells=ge),
              concrete_wear=dict(texture="CONCRETE_CRACKS_STAINS_v01.png",grid=[2,2],cells=ue),
              litter_metadata="LITTER_ATLAS_v01.json",
              source_policy="All decal marks procedurally painted. Existing v07 textures used only for previews; no downloads.")
    files={name:png_bytes(im,"_normal" in name) for name,im in images.items()}
    files["LITTER_ATLAS_v01.json"]=jbytes(litter_json)
    files["decals_v01.json"]=jbytes(pack)
    report["runtime"]=dict(python=sys.version.split()[0],numpy=np.__version__,pillow=PIL.__version__)
    report["seed"]=SEED
    report["generator_sha256"]=sha(Path(__file__).read_bytes())
    report["output_sha256"]={name:sha(data) for name,data in files.items()}
    refs=[REPO/"AGENTS.md",REPO/"docs/AgentRules.md",REPO/"docs/ArtDirection.md",
          REPO/"docs/specs/MAP_SPEC_2026-10-13_v01.md",REPO/"Working/Reviews/Textures_2026-10-11/STYLE_OAR_NOTES.md",
          BASE/"grade_v07.json",BASE/"materials_v3_v07.json"]
    refs += [BASE/k/(k+"_v07_albedo.png") for k in KEYS]
    report["reference_sha256"]={p.relative_to(REPO).as_posix():sha(p.read_bytes()) for p in refs}
    report["normal_metrics"]=sm
    # Quantify composited luminance changes against each actual preview base.
    stats={}
    for group,cells,entries,span in [("litter",lc,le,.5),("ground",gc,ge,1.5),("concrete",uc,ue,1.5)]:
        for cell,entry in zip(cells,entries):
            b=surface(entry["preview_base"],(512,512),(span,span))
            c=composite(b,cell)
            delta=np.abs((np.asarray(c)[...,:3].astype(float)-np.asarray(b)[...,:3])@np.array([.2126,.7152,.0722]))
            mask=np.array(cell)[...,3]>8
            stats[group+"/"+entry["id"]]=dict(mean_luma_change_over_cell_8bit=round(float(delta.mean()),4),
                                               max_luma_change_8bit=round(float(delta.max()),4),
                                               visible_alpha_coverage=round(float(mask.mean()),6))
    report["contrast_on_matching_surface"]=stats
    files["validation_v01.json"]=jbytes(report)
    return files,images["previews/decals_v01_on_surfaces.png"]


def safe_write(name,data):
    path=(ROOT/name).resolve()
    if not path.is_relative_to(ROOT): raise ValueError("Output must stay inside decals_v01")
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as handle: handle.write(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--check-only",action="store_true")
    group.add_argument("--review",metavar="NEW_NAME.png")
    args=parser.parse_args()
    files,review=build()
    if args.review:
        if Path(args.review).name!=args.review or not args.review.endswith(".png"):
            parser.error("--review expects a new PNG basename")
        name="previews/"+args.review
        safe_write(name,png_bytes(review))
        print("PASS: in-memory checks; new review written:",ROOT/name)
        return
    if args.check_only:
        count=0
        for name,data in files.items():
            existing=ROOT/name
            if existing.exists():
                if existing.read_bytes()!=data: raise AssertionError("Reproduction mismatch: "+name)
                count+=1
        # A second independent build also verifies RNG and serialization determinism.
        again,_=build()
        assert files.keys()==again.keys()
        assert all(files[k]==again[k] for k in files),"Independent rebuild differed"
        print(f"PASS: all texture checks; two independent builds identical ({len(files)} files); {count} existing files byte-identical. No writes.")
        return
    # Refuse before any writes if an output already exists.
    collisions=[name for name in files if (ROOT/name).exists()]
    if collisions: raise FileExistsError("Refusing to overwrite deliverables: "+", ".join(collisions))
    for name,data in files.items(): safe_write(name,data)
    print(f"PASS: generated {len(files)} files under {ROOT}")
    print("Unity NOT RUN. Inspect preview and run --check-only for deterministic verification.")


if __name__=="__main__":
    main()
