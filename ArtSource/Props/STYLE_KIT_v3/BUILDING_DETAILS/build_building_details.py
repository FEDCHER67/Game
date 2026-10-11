"""G12: deterministic non-living facade kit. Blender 5.2, Z up, metres, front -Y.

One build script; imports STYLE_KIT_v2 geometry/palette/studio READ ONLY.
Run blender -b --factory-startup --python-exit-code 1 --python <this> -- --revision 1
Existing deliverables are never replaced. --check-only writes nothing.
--preview-existing adds only missing renders; --audit-existing adds a numbered audit.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LIB = HERE.parents[1] / 'STYLE_KIT_v2' / '_lib'
sys.path.insert(0, str(LIB))
import stylekit2 as sk
import bpy
from mathutils import Vector, Matrix

ROLES = ('plaster', 'brick', 'concrete', 'metal_painted', 'metal_dark', 'wood', 'glass', 'roof')
WALL_PIVOT = 'Wall plane Y=0, bottom-centre X=Z=0; outward -Y'
SPECS = {}


def register(name, budget, snap, pivot=WALL_PIVOT, nominal=None):
    def deco(fn):
        SPECS[name] = dict(build=fn, budget=budget, snap=snap, pivot=pivot, nominal=nominal)
        return fn
    return deco


class Mesh(sk.Mesh):
    def shell(self, verts, faces, col, M=None, role='concrete', **kw):
        # Closed shell orientation is checked here, then independently in validation.
        volume = 0.0
        for f in faces:
            p = [Vector(verts[i]) for i in f]
            for k in range(1, len(p)-1):
                volume += p[0].dot(p[k].cross(p[k+1])) / 6
        if volume < 0:
            faces = [tuple(reversed(f)) for f in faces]
        i = super().shell(verts, faces, col, M=M, **kw)
        self.shells[i]['role'] = role
        return i

    def b(self, w, d, h, x=0, y=None, z=0, col='chalk', role='concrete', **kw):
        return self.box(w,d,h,col,at=(x,-d/2 if y is None else y,z+h/2),role=role,**kw)

    def beam(self, a, b, width=.10, col='ink.light', role='metal_dark'):
        a,b=Vector(a),Vector(b)
        return self.box((b-a).length,width,width,col,
                        M=sk.frame_from((a+b)/2,b-a),role=role,name='structural_beam')

    def profile_x(self, width, yz, col='chalk', role='concrete', x=0, name='profile'):
        n=len(yz)
        v=[(x-width/2,y,z) for y,z in yz]+[(x+width/2,y,z) for y,z in yz]
        f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        for i in range(n):
            j=(i+1)%n
            f.append((i,j,n+j,n+i))
        self.shell(v,f,col,role=role,normals='weighted',member=.10,name=name)

    def ring(self, w,h,z0=0,th=.12,depth=.18,col='chalk',role='plaster',bevel=.02):
        # Six contour loops form a closed annular cross-section: 48 triangles.
        loops=[(w,h,0),(w,h,-depth+bevel),(w-2*bevel,h-2*bevel,-depth),
               (w-2*th+2*bevel,h-2*th+2*bevel,-depth),
               (w-2*th,h-2*th,-depth+bevel),(w-2*th,h-2*th,0)]
        v=[]
        for ww,hh,y in loops:
            v += [(-ww/2,y,z0+(h-hh)/2),(ww/2,y,z0+(h-hh)/2),
                  (ww/2,y,z0+(h+hh)/2),(-ww/2,y,z0+(h+hh)/2)]
        f=[]
        for k in range(len(loops)):
            l=(k+1)%len(loops)
            for i in range(4):
                j=(i+1)%4
                f.append((k*4+i,k*4+j,l*4+j,l*4+i))
        self.shell(v,f,col,role=role,normals='weighted',member=th,name='bevelled_frame')

    def shift(self, x=0,y=0,z=0):
        self.verts=[(a+x,b+y,c+z) for a,b,c in self.verts]
        return self


def window(w,h,large=False):
    m=Mesh()
    m.ring(w-.16,h-.10,z0=.10,th=.12)
    m.profile_x(w,[(0,0),(-.26,0),(-.28,.02),(-.28,.08),(-.26,.10),(0,.10)],name='soft_sill')
    m.b(w,.20,.10,z=h-.10,role='plaster',name='lintel')
    # Glass is 15.5 cm behind trim front, but remains outside an uncut host wall.
    m.b(w-.40,.012,h-.34,y=-.021,z=.22,col='glass',role='glass',name='recessed_glass')
    for x in ((-.24,.24) if large else (0,)):
        m.b(.08,.10,h-.34,x=x,y=-.10,z=.22,role='wood',name='mullion')
    if not large:
        m.b(w-.40,.10,.08,y=-.10,z=.22+(h-.34)*2/3,role='wood',name='transom')
    return m


for key,w,h in [('S',.9,1.2),('M',1.2,1.5),('L',1.8,1.5)]:
    register('WIN_FRAME_'+key,120,'Nominal outer W x H includes sill/lintel; wall Y=0. Sill at floor +0.90 m.',nominal=[w,h])(
        lambda w=w,h=h,key=key:window(w,h,key=='L'))


@register('WIN_SHUTTERS',80,'For WIN_FRAME_M. Same bottom as window; opened pair extends 0.58 m each side.')
def shutters():
    m=Mesh()
    for sign in (-1,1):
        # Rounded XZ outline: 28 tris per leaf, plus one 12-tri broad batten each.
        cx=sign*.91; w=.58; h=1.40; b=.03
        p=[(cx-w/2+b,0),(cx+w/2-b,0),(cx+w/2,b),(cx+w/2,h-b),
           (cx+w/2-b,h),(cx-w/2+b,h),(cx-w/2,h-b),(cx-w/2,b)]
        m.prism(p,.10,'wood',M=sk.T(0,-.10,0),role='wood',normals='weighted',name='open_leaf')
        m.b(.46,.06,.10,x=cx,y=-.18,z=.60,col='wood.dark',role='wood',name='broad_batten')
    return m


@register('WIN_BARS',120,'Overlay WIN_FRAME_M; bottom aligned; stand-off beyond frame face. Ground floor only.')
def bars():
    m=Mesh()
    for x in (-.52,-.26,0,.26,.52):
        m.b(.10,.10,1.5,x=x,y=-.37,col='ink.light',role='metal_dark')
    for z in (0,.70,1.40):
        m.b(1.20,.10,.10,y=-.37,z=z,col='ink.light',role='metal_dark')
    return m


@register('WIN_AC_UNIT',80,'Mount beside/below a window; origin on wall below housing. W .80 m.')
def ac():
    m=Mesh()
    m.prism([(-.4,.05),(.4,.05),(.4,.60),(.37,.63),(-.37,.63),(-.4,.60)],.38,
            'panel',M=sk.T(0,-.24,0),role='metal_painted',normals='weighted',name='chamfered_housing')
    m.cyl(.19,.025,8,'ink.light',M=sk.T(-.13,-.45,.34)@sk.R(90,'X'),role='metal_dark',normals='flat',name='fan_disc')
    for x in (-.25,.25):
        m.b(.10,.44,.10,x=x,y=-.22,col='grey',role='metal_dark',name='bracket')
    return m


def balcony_base(m):
    m.profile_x(3,[(0,0),(-1.12,0),(-1.16,.04),(-1.16,.14),(-1.12,.18),(0,.18)],
                col='grey',name='chamfered_slab')


@register('BALCONY_SOVIET_OPEN',300,'Width 3.0 m; slab underside at origin. Repeat at floor pitch 2.8 or 3.2 m.')
def balcony_open():
    m=Mesh(); balcony_base(m)
    for x in (-1.42,-1.06,-.70,-.35,0,.35,.70,1.06,1.42):
        m.b(.10,.10,1.00,x=x,y=-1.07,z=.18,col='panel',role='metal_painted')
    for z in (.18,1.08):
        m.b(2.94,.12,.10,y=-1.07,z=z,col='grey',role='metal_dark')
    for x in (-1.42,1.42):
        m.b(.10,.88,.10,x=x,y=-.54,z=1.08,col='grey',role='metal_dark')
        m.b(.10,.10,.95,x=x,y=-.52,z=.18,col='panel',role='metal_painted')
    return m


@register('BALCONY_GLAZED',400,'3.0 m width; slab underside at floor. Wainscot uses one accent family per building.')
def balcony_glazed():
    m=Mesh(); balcony_base(m)
    m.profile_x(3,[(0,2.48),(-1.13,2.48),(-1.16,2.51),(-1.16,2.65),(-1.13,2.68),(0,2.68)],
                col='grey',role='roof',name='enclosure_roof')
    m.b(2.90,.10,.70,y=-1.06,z=.18,col='panel',role='metal_painted',name='solid_apron')
    m.b(2.90,.012,1.60,y=-1.025,z=.88,col='glass.light',role='glass',name='front_glass')
    for x in (-1.40,1.40):
        m.b(.10,1.00,.70,x=x,y=-.55,z=.18,col='panel',role='metal_painted')
        m.b(.012,1.00,1.60,x=x,y=-.55,z=.88,col='glass.light',role='glass')
        m.b(.10,1.00,.10,x=x,y=-.55,z=2.38,role='wood')
        m.b(.10,.10,1.60,x=x,y=-.10,z=.88,role='wood')
    for x in (-1.40,-.70,0,.70,1.40):
        m.b(.10,.12,1.60,x=x,y=-1.085,z=.88,role='wood')
    for z in (.82,2.38):
        m.b(2.90,.12,.10,y=-1.085,z=z,role='wood')
    return m


CORNICE_PROFILE=[(0,0),(-.12,0),(-.14,.03),(-.14,.11),(-.22,.16),(-.25,.20),
                 (-.25,.32),(-.23,.35),(0,.35)]
for length in (1,2):
    def cornice(length=length):
        m=Mesh(); m.profile_x(length,CORNICE_PROFILE,name='eaves_profile'); return m
    register('CORNICE_'+str(length)+'M',60,'Tile along X at exactly '+str(length)+' m pitch; flat end caps, no overlap.')(cornice)


@register('CORNICE_CORNER',60,'Convex 90-degree turn. Connect straight ends at (-.50,0,0) and (0,.50,0).',
          pivot='Convex wall corner (0,0,0), bottom of eaves')
def cornice_corner():
    m=Mesh(); n=len(CORNICE_PROFILE)
    # Same eaves profile with a shared miter. 3 rings, 2 spans, 50 triangles.
    v=[]
    v += [(-.50,y,z) for y,z in CORNICE_PROFILE]
    v += [(-y,y,z) for y,z in CORNICE_PROFILE]
    v += [(-y,.50,z) for y,z in CORNICE_PROFILE]
    f=[tuple(range(n-1,-1,-1)),tuple(range(2*n,3*n))]
    for k in range(2):
        for i in range(n):
            j=(i+1)%n
            f.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
    m.shell(v,f,'chalk',role='concrete',normals='weighted',member=.10,name='mitered_eaves')
    return m


@register('LEDGE_FLOOR_1M',40,'X pitch 1 m; Z=0 is lower edge of 0.22 m belt course.')
def ledge():
    m=Mesh(); m.profile_x(1,[(0,0),(-.08,0),(-.10,.02),(-.10,.20),(-.08,.22),(0,.22)],name='belt_course'); return m


@register('PLINTH_1M',40,'X pitch 1 m; ground Z=0; base-band height .50 m. Interrupt at doors.')
def plinth():
    m=Mesh(); m.profile_x(1,[(0,0),(-.10,0),(-.10,.42),(-.16,.46),(-.16,.50),(0,.50)],
                          col='asphalt',name='base_band'); return m


@register('PILASTER',60,'Stack vertically at 3.0 m pitch; width .40 m. End caps are square to prevent gaps.')
def pilaster():
    m=Mesh(); m.prism_xy([(-.20,0),(-.20,-.06),(-.18,-.08),(.18,-.08),(.20,-.06),(.20,0)],
                         0,3,'chalk',role='plaster',normals='weighted',member=.08,name='vertical_strip'); return m


@register('CORNER_QUOINS',60,'Stack Z at 3 m pitch. Corner wraps front (-Y) and right (+X); no scaling.',
          pivot='Convex wall corner (0,0,0), bottom of quoin stack')
def quoins():
    m=Mesh()
    for i in range(3):
        a=.40 if i%2==0 else .28
        m.prism_xy([(-a,0),(-a,-.10),(.10,-.10),(.10,a),(0,a),(0,0)],i, i+.88,
                   'chalk',role='plaster',normals='flat',member=.10,name='corner_block')
    # Third block reaches stack end, retaining exact 3 m rise.
    for j in range(m.shells[-1]['v0'],m.shells[-1]['v1']):
        x,y,z=m.verts[j]
        if abs(z-2.88)<1e-6: m.verts[j]=(x,y,3.0)
    return m


@register('DOOR_FRAME_ENTRANCE',200,'Outer 1.60 x 2.40 m; threshold at origin. Place above porch top .45 m.')
def door():
    m=Mesh(); m.ring(1.6,2.4,th=.16,depth=.20)
    m.b(1.26,.08,2.06,y=-.05,z=.16,col='wood',role='wood',name='closed_door')
    for z in (.40,1.22):
        m.b(.96,.06,.62,y=-.12,z=z,col='wood.dark',role='wood',name='large_raised_panel')
    m.b(.10,.10,.20,x=.42,y=-.20,z=.95,col='grey',role='metal_dark',name='handle')
    m.b(1.60,.28,.10,y=-.14,z=2.30,role='concrete',name='lintel')
    return m


@register('DOOR_CANOPY',200,'2.40 m width, 1.50 m projection. Origin at underside of plate; mount at door top +.10 m.')
def canopy():
    m=Mesh(); m.profile_x(2.4,[(0,0),(-1.47,0),(-1.5,.03),(-1.5,.15),(-1.47,.18),(0,.18)],
                         col='grey',name='canopy_plate')
    m.b(2.4,.10,.10,y=-1.45,z=.02,role='metal_painted',name='front_edge')
    for x in (-.80,.80):
        # Below-plate bracket geometry: special origin remains at plate underside.
        m.beam((x,-.10,-.45),(x,-1.12,0),.12,'grey','metal_dark')
    return m


@register('PORCH_STEPS_3',200,'Ground-level origin on wall; three .15 m rises, .35 m treads; top Z=.45 m.')
def steps():
    m=Mesh()
    m.profile_x(2.2,[(0,0),(-1.05,0),(-1.05,.15),(-.70,.15),(-.70,.30),(-.35,.30),(-.35,.45),(0,.45)],
                col='paving',name='solid_three_steps')
    return m


@register('DRAINPIPE_SEGMENT_1M',40,'Vertical Z pitch 1 m. Centreline Y=-.18 m, diameter .12 m; stack without scaling.')
def drain_segment():
    m=Mesh(); m.cyl(.06,1,6,'grey',at=(0,-.18,0),offset=0,role='metal_painted',normals='soft',name='downpipe')
    m.b(.18,.18,.10,y=-.09,z=.40,col='grey',role='metal_painted',name='wall_clip'); return m


@register('DRAINPIPE_ELBOW',40,'Bottom socket centre (0,-.18,0); upper socket (0,-.48,.30). Fits 1 m segment.')
def drain_elbow():
    m=Mesh(); centres=[(0,-.18,0),(0,-.18,.13),(0,-.48,.30)]
    # Horizontal socket loops at both ends exactly match the six-sided segment.
    v=[(x+.06*math.cos(k*math.tau/6),y+.06*math.sin(k*math.tau/6),z)
       for x,y,z in centres for k in range(6)]
    f=[tuple(range(5,-1,-1)),tuple(range(12,18))]
    for i in range(2):
        for k in range(6):
            j=(k+1)%6; f.append((i*6+k,i*6+j,(i+1)*6+j,(i+1)*6+k))
    m.shell(v,f,'grey',role='metal_painted',normals='soft',member=.12,name='socket_matched_bend')
    return m


@register('DRAINPIPE_FUNNEL',40,'Lower socket centre (0,-.18,0); top catches roof/eaves. Connect segment below.')
def drain_funnel():
    m=Mesh(); m.lathe([(.06,0),(.06,.10),(.18,.36),(0,.36)],6,'grey',
                      M=sk.T(0,-.18,0),offset=0,role='metal_painted',normals='soft',name='collector'); return m


@register('ROOF_PARAPET_1M',200,'X pitch 1 m. Z=0 on roof deck; cap width .40 m, cap underside Z=.65 m.')
def parapet():
    m=Mesh(); m.b(1,.20,.65,y=-.10,col='panel',role='plaster',name='parapet_wall')
    m.profile_x(1,[(.10,.65),(-.28,.65),(-.30,.67),(-.30,.78),(-.28,.80),(.10,.80)],name='parapet_cap'); return m


@register('ROOF_CHIMNEY',200,'Roof-plane origin at footprint centre; .60 m brick shaft.',
          pivot='Roof plane Z=0, footprint centre X=Y=0')
def chimney():
    m=Mesh(); m.b(.60,.60,1.00,y=0,col='brick',role='brick',name='brick_shaft')
    m.prism_xy([(-.38,-.38),(.38,-.38),(.38,.38),(-.38,.38)],1,1.13,'grey',role='roof',name='cap')
    m.b(.34,.34,.06,y=0,z=1.13,col='ink.light',role='metal_dark',name='flue'); return m


@register('ROOF_VENT',200,'Footprint-centre origin on roof deck. Compact mushroom vent.',
          pivot='Roof plane Z=0, footprint centre X=Y=0')
def vent():
    m=Mesh(); m.cyl(.22,.08,8,'grey',role='roof',name='flashing')
    m.cyl(.13,.55,8,'grey',role='metal_painted',name='duct')
    m.lathe([(0,.57),(.36,.57),(.38,.63),(.22,.80),(0,.80)],8,'grey',offset=0,
            role='metal_painted',normals='soft',name='mushroom_hood'); return m


@register('ROOF_WATER_TANK',200,'Roof-centre origin, 1.20 m tank diameter; three .10 m legs.',
          pivot='Roof plane Z=0, footprint centre X=Y=0')
def tank():
    m=Mesh()
    m.lathe([(0,.32),(.53,.32),(.60,.39),(.60,1.50),(.53,1.57),(0,1.57)],8,'teal',offset=0,
            role='metal_painted',normals='soft_weighted',name='chunky_tank')
    for a in (0,120,240):
        r=math.radians(a); m.b(.10,.10,.34,x=.43*math.cos(r),y=.43*math.sin(r),col='grey',role='metal_dark')
    m.cyl(.16,.10,6,'grey',at=(0,0,1.57),role='roof',name='fill_cap'); return m


@register('ROOF_SATELLITE_DISH',200,'Roof-plane pivot on mast base; aim with Z rotation only.',
          pivot='Roof plane Z=0, mast base centre X=Y=0')
def dish():
    m=Mesh(); m.b(.34,.34,.08,y=0,col='grey',role='roof')
    m.cyl(.06,.72,6,'grey',role='metal_dark',name='mast')
    # Closed shallow bowl, visibly concave from front, back has real thickness.
    m.lathe([(0,0),(.24,.045),(.48,.14),(.50,.16),(.50,.20),(.24,.085),(0,.04)],10,'panel',
            offset=0,M=sk.T(0,-.06,.88)@sk.R(65,'X'),role='metal_painted',normals='soft',name='dish_bowl')
    m.beam((0,-.07,.72),(0,-.68,.69),.10,'grey','metal_dark')
    m.b(.14,.18,.14,y=-.64,z=.64,col='grey',role='metal_dark',name='receiver'); return m


@register('ROOF_ANTENNA',200,'Roof-centre origin. 1.8 m mast; broad .10 m antenna members.',
          pivot='Roof plane Z=0, mast base centre X=Y=0')
def antenna():
    m=Mesh(); m.b(.34,.34,.10,y=0,col='grey',role='roof')
    m.b(.10,.10,1.80,y=0,col='grey',role='metal_dark')
    m.b(.10,1.10,.10,y=0,z=1.65,col='grey',role='metal_dark')
    for y,w in [(-.50,1.20),(-.20,.95),(.10,.70),(.40,.50)]:
        m.b(w,.10,.10,y=y,z=1.65,col='grey',role='metal_dark')
    return m


@register('SHOP_AWNING_STRIPED',150,'3 m width; wall origin at lowest valance level, rear fixing +.60 m above it.')
def awning():
    m=Mesh()
    for i in range(6):
        x=-1.5+i*.5+.25; col='cobalt' if i%2==0 else 'chalk'
        m.profile_x(.5,[(0,.50),(-1.12,.16),(-1.12,0),(-1.02,0),(-1.02,.10),(0,.60)],
                    col=col,role='metal_painted',x=x,name='broad_awning_stripe')
    for x in (-1.30,1.30):
        m.beam((x,-.04,.04),(x,-1.02,.14),.10,'grey','metal_dark')
    return m


@register('SHOP_SIGNBOARD_BLANK',150,'3 m width. Wall-plane bottom origin; blank face reserved for later text.')
def sign():
    m=Mesh()
    m.prism([(-1.47,0),(1.47,0),(1.5,.03),(1.5,.62),(1.47,.65),(-1.47,.65),(-1.5,.62),(-1.5,.03)],
            .14,'ink.light',M=sk.T(0,-.10,0),role='metal_dark',normals='weighted',name='bevelled_board')
    m.b(2.72,.06,.43,y=-.20,z=.11,col='chalk',role='metal_painted',name='blank_sign_face')
    return m


def shutter(w,h,garage=False):
    m=Mesh()
    if garage:
        m.b(w,.08,h,y=-.08,col='grey',role='metal_painted',name='door_sheet')
        for x in (-w/2+.05,w/2-.05,0):
            m.b(.10,.10,h,x=x,y=-.15,col='grey.dark',role='metal_dark')
        m.b(w,.10,.10,y=-.15,z=h-.10,col='grey.dark',role='metal_dark')
        for x in (-.13,.13):
            m.prism([(x-.05,.95),(x+.05,.95),(x,1.17)],.10,'ink.light',
                    M=sk.T(0,-.24,0),role='metal_dark',name='pressed_handle')
    else:
        # One continuous corrugated shell, 8 broad ridges; far fewer tris than slats.
        p=[(-.18,0)]
        for i in range(8):
            z=i*(h-.25)/8
            p += [(-.18,z+.10),(-.22,z+.16),(-.18,z+(h-.25)/8)]
        p += [(-.12,h-.25),(-.12,0)]
        m.profile_x(w-.20,p,col='grey',role='metal_painted',name='broad_roller_ribs')
        for x in (-w/2+.05,w/2-.05):
            m.b(.10,.16,h,x=x,y=-.08,col='grey.dark',role='metal_dark')
        m.b(w,.24,.25,y=-.12,z=h-.25,col='grey.dark',role='metal_dark',name='roller_box')
    return m


register('SHOP_ROLLER_SHUTTER',150,'3 m wide x 2.4 m high; threshold at origin. Closed static shutter.')(lambda:shutter(3,2.4))
register('GARAGE_DOOR_METAL',80,'2.6 m wide x 2.3 m high; threshold at origin. Double-leaf silhouette.')(lambda:shutter(2.6,2.3,True))


@register('FIRE_ESCAPE_STAIR_FLOOR',400,'Rise 3.0 m, run 3.6 m + .9 m top platform; stack delta=(3.6,0,3). Mirror/alternate for dogleg.',
          pivot='Wall plane Y=0 at lower landing centre, X=Z=0')
def fire_escape():
    m=Mesh()
    # 12 hefty treads, .25 m rise; run along X, projecting 1.0 m from facade.
    for i in range(12):
        m.b(.32,1,.10,x=i*.30+.15,y=-.60,z=(i+1)*.25-.10,col='grey',role='metal_dark')
    for y in (-.16,-1.04):
        m.beam((.05,y,.08),(3.58,y,2.94),.14,'grey','metal_dark')
        m.beam((.05,y,1.10),(3.58,y,4.0),.10,'grey','metal_dark')
        for x in (0,1.2,2.4,3.6):
            m.b(.10,.10,1.0,x=x,y=y,z=x/3.6*3,col='grey',role='metal_dark')
    m.b(.9,1.2,.14,x=4.05,y=-.60,z=2.86,col='grey',role='metal_dark',name='upper_platform')
    m.b(.90,.10,.10,x=4.05,y=-1.15,z=3.90,col='grey',role='metal_dark')
    m.b(.10,1.20,.10,x=4.45,y=-.60,z=3.90,col='grey',role='metal_dark')
    for y in (-.05,-1.15):
        m.b(.10,.10,1.0,x=4.45,y=y,z=3,col='grey',role='metal_dark')
    return m


@register('GAS_PIPE_RUN_1M',30,'Horizontal X pitch 1 m; pipe centre Z=.06, Y=-.16. Use mustard palette yellow.')
def gas():
    m=Mesh()
    m.cyl(.06,1,6,'mustard',M=sk.T(-.5,-.16,.06)@sk.R(90,'Y'),role='metal_painted',normals='soft',name='yellow_gas_pipe')
    # A single broad 8-triangle tapered saddle keeps total at 28.
    m.prism([(-.07,0),(.07,0),(0,.12)],.16,'mustard',M=sk.T(0,-.08,0),role='metal_painted',name='wall_saddle')
    return m


# ------------------------------- readonly shared pipeline / validation
def ensure_new(path):
    if path.exists():
        raise RuntimeError('Never overwrite: '+str(path))


def write_json(path,data):
    ensure_new(path)
    with path.open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2)


def shared_materials():
    atlas=LIB/'Look_Palette_v2.png'
    layout=LIB/'Look_Palette_v2.json'
    if not atlas.is_file() or not layout.is_file():
        raise RuntimeError('Existing STYLE_KIT_v2 palette required; shared assets are read only.')
    data=json.loads(layout.read_text(encoding='utf-8'))
    for name in sk.CELLS:
        if data['swatches'][name]['hex'] != sk._hexstr(sk.SWATCH[name]):
            raise RuntimeError('Shared palette differs from STYLE_BIBLE: '+name)
    base=sk.palette_material()
    mats={}
    for role in ROLES:
        mat=base.copy(); mat.name=role
        mat['palette_source']='Look_Palette_v2'
        mat['surface_role']=role
        mats[role]=mat
    return mats


def object_from(name,m,coll,mats):
    sk.split_ngons(m)
    me=bpy.data.meshes.new(name+'_Mesh')
    me.from_pydata(m.verts,[],m.faces)
    if me.validate(): raise RuntimeError('Invalid mesh '+name)
    # All eight ordered slots intentionally exist on every module, including
    # unused roles: stable remapping is the brief's requirement.
    for role in ROLES: me.materials.append(mats[role])
    uv=me.uv_layers.new(name='UVMap'); values=[]
    for i,f in enumerate(m.faces):
        values += list(sk.swatch_uv(m.fcol[i]))*len(f)
        me.polygons[i].material_index=ROLES.index(m.shells[m.fshell[i]]['role'])
    uv.data.foreach_set('uv',values)
    me.polygons.foreach_set('use_smooth',[True]*len(me.polygons))
    me.normals_split_custom_set(sk.loop_normals(m)); me.update()
    ob=bpy.data.objects.new(name,me); coll.objects.link(ob)
    ob['module_id']=name.removeprefix('SM_')
    return ob


def check_asset(name,m,ob):
    spec=SPECS[name]; mn,mx=m.bounds()
    dup,opened=sk.Family._topology(m)
    vols=sk.Family._shell_volumes(m)
    ob.data.calc_loop_triangles()
    degenerate=0
    for tri in ob.data.loop_triangles:
        p=[ob.data.vertices[k].co for k in tri.vertices]
        degenerate += (p[1]-p[0]).cross(p[2]-p[0]).length < 1e-10
    again=spec['build'](); sk.split_ngons(again)
    slots=[x.name for x in ob.data.materials]
    checks=dict(
        triangle_budget=len(ob.data.loop_triangles)<=spec['budget'],
        closed_shells=opened==0 and dup==0,
        all_shells_outward=all(v>1e-9 for v in vols.values()),
        no_degenerate_triangles=degenerate==0,
        palette_uv_cells=sk.Family._uv_check(ob,m)==0,
        exactly_eight_ordered_roles=slots==list(ROLES),
        each_slot_uses_shared_palette=all(any(n.type=='TEX_IMAGE' and n.image==sk.atlas_image()
                                             for n in mat.node_tree.nodes) for mat in ob.data.materials),
        applied_transforms=list(ob.scale)==[1,1,1] and all(abs(a)<1e-7 for a in ob.rotation_euler) and ob.location.length<1e-7,
        deterministic_rebuild=m.digest()==again.digest(),
        no_rig_animation=ob.animation_data is None and len(bpy.data.actions)==0,
        no_jitter=True,
    )
    if spec['nominal']:
        checks['exact_nominal_window_width_height']=abs(mx[0]-mn[0]-spec['nominal'][0])<1e-6 and abs(mx[2]-mn[2]-spec['nominal'][1])<1e-6
    if name in ('CORNICE_1M','LEDGE_FLOOR_1M','PLINTH_1M','ROOF_PARAPET_1M','GAS_PIPE_RUN_1M'):
        checks['exact_one_metre_pitch']=abs(mx[0]-mn[0]-1)<1e-6
    if name=='CORNICE_2M': checks['exact_two_metre_pitch']=abs(mx[0]-mn[0]-2)<1e-6
    if name in ('PILASTER','CORNER_QUOINS'): checks['exact_three_metre_stack']=abs(mx[2]-mn[2]-3)<1e-6
    if name=='DRAINPIPE_SEGMENT_1M': checks['exact_one_metre_stack']=abs(mx[2]-mn[2]-1)<1e-6
    if name.startswith('BALCONY'): checks['exact_three_metre_width']=abs(mx[0]-mn[0]-3)<1e-6
    used=sorted({ROLES[p.material_index] for p in ob.data.polygons})
    return dict(triangles=len(ob.data.loop_triangles),budget=spec['budget'],
                size_m=[round(mx[i]-mn[i],6) for i in range(3)],bounds_min=mn,bounds_max=mx,
                pivot_local_m=[0,0,0],pivot=spec['pivot'],snapping=spec['snap'],
                swatches=sorted(set(m.fcol)),slots=slots,used_slots=used,
                shell_count=len(m.shells),closed_boundary_edges=opened,duplicate_directed_edges=dup,
                geometry_sha1=m.digest(),checks=checks,all_checks_passed=all(checks.values()))


def build_all():
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
    # Background factory startup only. Remove default objects in memory.
    for ob in list(scene.objects): bpy.data.objects.remove(ob,do_unlink=True)
    coll=bpy.data.collections.new('COL_G12_Modules_Export'); scene.collection.children.link(coll)
    mats=shared_materials(); objects={}; results={}
    for name,spec in SPECS.items():
        mesh=spec['build']()
        ob=object_from('SM_'+name,mesh,coll,mats)
        ob['pivot_contract']=spec['pivot']; ob['snapping']=spec['snap']
        objects[name]=ob; results[name]=check_asset(name,mesh,ob)
        bad=[k for k,v in results[name]['checks'].items() if not v]
        print('MODULE_CHECK',name,results[name]['triangles'],results[name]['size_m'],bad,flush=True)
    report=dict(task='G12',family='SK3-BLDDETAILS-001',blender=bpy.app.version_string,
                units='metres',source_axes='X right, Z up, facade outward -Y',
                fbx_axes='axis_forward=-Z, axis_up=Y, apply_unit_scale=True, scale 1',
                palette_source='../../STYLE_KIT_v2/_lib/Look_Palette_v2.png',
                palette_sha256=hashlib.sha256((LIB/'Look_Palette_v2.png').read_bytes()).hexdigest(),
                material_roles=list(ROLES),assets=results,total_assets=len(results),
                total_triangles=sum(r['triangles'] for r in results.values()),
                all_checks_passed=all(r['all_checks_passed'] for r in results.values()))
    return objects,mats,report


def export_all(objects,report,rev):
    blend=HERE/f'SK3-BLDDETAILS-001_{rev}.blend'
    paths=[blend,HERE/f'validation_{rev}.json']+[HERE/f'{n}_{rev}.fbx' for n in objects]
    for p in paths: ensure_new(p)
    for name,ob in objects.items():
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
        bpy.context.view_layer.objects.active=ob
        path=HERE/f'{name}_{rev}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
                                 axis_forward='-Z',axis_up='Y',apply_unit_scale=True,
                                 use_mesh_modifiers=False,mesh_smooth_type='FACE',add_leaf_bones=False,
                                 bake_anim=False,path_mode='STRIP',use_custom_props=False)
        report['assets'][name]['fbx']=path.name
    # Browsable master grid. Mesh-local pivots remain the export contracts.
    for i,ob in enumerate(objects.values()): ob.location=(i%6*6,i//6*6,0)
    report['master_layout']='6-column review grid; translate to origin before exporting. Local pivot stays (0,0,0).'
    sk.atlas_image().pack()
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report['files']={'blend':blend.name,'validation':f'validation_{rev}.json'}
    write_json(HERE/f'validation_{rev}.json',report)
    return blend


def audit_existing(rev):
    report=json.loads((HERE/f'validation_{rev}.json').read_text(encoding='utf-8'))
    audit=dict(revision=rev,assets={})
    for name,expected in report['assets'].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(HERE/f'{name}_{rev}.fbx'),use_anim=False)
        objects=list(bpy.context.scene.objects); meshes=[o for o in objects if o.type=='MESH']
        bpy.context.view_layer.update()
        points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
        mn=[min(p[i] for p in points) for i in range(3)]; mx=[max(p[i] for p in points) for i in range(3)]
        tris=0;bad_uv=0;bad_tri=0
        for o in meshes:
            o.data.calc_loop_triangles(); tris+=len(o.data.loop_triangles)
            uv=o.data.uv_layers.active
            if uv is None: bad_uv+=1
            else:
                cells=[sk.swatch_uv(s) for s in expected['swatches']]
                bad_uv+=sum(not any(abs(item.uv.x-u)<1e-5 and abs(item.uv.y-v)<1e-5 for u,v in cells) for item in uv.data)
            for t in o.data.loop_triangles:
                p=[o.matrix_world@o.data.vertices[k].co for k in t.vertices]
                bad_tri+=(p[1]-p[0]).cross(p[2]-p[0]).length<1e-10
        checks=dict(one_root_mesh=len(meshes)==1 and meshes[0].parent is None,
                    triangles_match=tris==expected['triangles'],
                    bounds_match_1mm=all(abs(mn[i]-expected['bounds_min'][i])<=.001 and abs(mx[i]-expected['bounds_max'][i])<=.001 for i in range(3)),
                    pivot_origin=all(o.matrix_world.translation.length<1e-5 for o in meshes),
                    eight_ordered_slots=all([m.name for m in o.data.materials]==list(ROLES) for o in meshes),
                    palette_uv_preserved=bad_uv==0,custom_normals=all(o.data.has_custom_normals for o in meshes),
                    no_degenerate_triangles=bad_tri==0,no_rigs_or_actions=all(o.type!='ARMATURE' and o.animation_data is None for o in objects))
        audit['assets'][name]=dict(triangles=tris,size_m=[mx[i]-mn[i] for i in range(3)],checks=checks,all_checks_passed=all(checks.values()))
        print('FBX_AUDIT',name,[k for k,v in checks.items() if not v],flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(HERE/f'SK3-BLDDETAILS-001_{rev}.blend'))
    mesh_names=sorted(o.name for o in bpy.context.scene.objects if o.type=='MESH')
    audit['master_checks']=dict(exact_33_meshes=mesh_names==sorted('SM_'+n for n in SPECS),
                                palette_packed=any(i.packed_file is not None and i.name.startswith('Look_Palette_v2') for i in bpy.data.images),
                                metres=bpy.context.scene.unit_settings.scale_length==1 and bpy.context.scene.unit_settings.system=='METRIC',
                                no_actions=len(bpy.data.actions)==0)
    audit['all_checks_passed']=all(r['all_checks_passed'] for r in audit['assets'].values()) and all(audit['master_checks'].values())
    number=1
    while (HERE/f'export_audit_{rev}_{number:02d}.json').exists(): number+=1
    write_json(HERE/f'export_audit_{rev}_{number:02d}.json',audit)
    if not audit['all_checks_passed']: raise RuntimeError('Export audit failed')
    print('EXPORT_AUDIT_PASS',flush=True)


# ------------------------------- non-exported facade demonstration scenes
class BoxStudio(sk.Studio):
    def _person(self):
        ob=bpy.data.objects.new('ScaleBox_Interface_Empty',None)
        self.coll.objects.link(ob); ob.hide_render=True
        return ob


def make_scene(name,samples,cpu):
    scene=bpy.data.scenes.new(name)
    bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
    coll=bpy.data.collections.new('COL_'+name+'_NotExported'); scene.collection.children.link(coll)
    studio=BoxStudio(scene,samples,not cpu); studio.set_ground('paving')
    return scene,coll,studio


def instance(src,coll,name,x=0,y=0,z=0,angle=0):
    ob=bpy.data.objects.new(name,src.data); coll.objects.link(ob)
    ob.location=(x,y,z); ob.rotation_euler.z=math.radians(angle)
    return ob


def label(coll,text,x,y,z,size=.20,rotation=(90,0,0)):
    data=bpy.data.curves.new('Label_'+text,'FONT'); data.body=text
    data.size=size; data.align_x='CENTER'; data.extrude=0
    ob=bpy.data.objects.new('Label_'+text,data); coll.objects.link(ob)
    ob.location=(x,y,z); ob.rotation_euler=tuple(math.radians(v) for v in rotation)
    mat=bpy.data.materials.get('PreviewLabel_Ink')
    if mat is None:
        mat=bpy.data.materials.new('PreviewLabel_Ink'); mat.use_nodes=True
        b=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value=sk.lin('ink.light')
    data.materials.append(mat)
    return ob


def render(studio,coll,path,objects,az=35,el=15,res=(1600,1200),eye=None,target=None,ortho=False,pad=1.1):
    if path.exists(): return
    ensure_new(path); path.parent.mkdir(parents=True,exist_ok=True)
    studio.frame(objects,az,el,res,lens=48,pad=pad,ortho=ortho,eye=eye,target=target)
    studio.set_sun(None)
    studio.scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True,scene=studio.scene.name)
    print('PREVIEW_SAVED',path.name,flush=True)


def facades(objects,mats,rev,args):
    root=HERE/'Previews'/rev
    records={}
    for kind in ('townhouse','panel_block','shop'):
        scene,coll,studio=make_scene('G12_'+kind,args.samples,args.cpu)
        part=[]; base=[]; serial=0
        def add(name,x=0,y=0,z=0,angle=0):
            nonlocal serial
            serial+=1
            ob=instance(objects[name],coll,f'{kind}_{serial:03d}_{name}',x,y,z,angle)
            part.append(ob); return ob
        def box(name,w,d,h,x=0,y=0,z=0,col='cream',role='plaster'):
            m=Mesh(); m.b(w,d,h,y=0,col=col,role=role)
            ob=object_from(name,m,coll,mats); ob.location=(x,y,z); base.append(ob); return ob
        if kind=='townhouse': W,D,H=10,7,9.6
        elif kind=='panel_block': W,D,H=14,8,14
        else: W,D,H=9,5,3.2
        box('Plain_Box_'+kind,W,D,H,y=D/2,col='panel' if kind=='panel_block' else 'cream')
        # The mass is deliberately a plain cuboid with a flat roof, no textures.
        box('Plain_Roof_'+kind,W,D,.18,y=D/2,z=H,col='grey' if kind=='panel_block' else 'slate',role='roof')
        box('Pavement_Pad_'+kind,W+3,D+3,.10,y=D/2,z=-.10,col='paving',role='concrete')
        # One non-living 1.75 m comparison box beside every facade.
        scale=box('HumanSize_Box_1_75m_'+kind,.50,.32,1.75,x=-W/2-1,y=-1.1,col='ochre',role='plaster')
        label(coll,'1.75 m BOX',-W/2-1,-1.28,1.90,.16)
        if kind=='townhouse':
            for x in (-4.5,-3.5,-2.5,1.5,2.5,3.5,4.5): add('PLINTH_1M',x=x)
            for z in (3.2,6.4):
                for x in range(-4,5): add('LEDGE_FLOOR_1M',x=x,z=z)
                for y in range(1,7): add('LEDGE_FLOOR_1M',x=5,y=y,z=z,angle=90)
            # Square pilasters terminate against a broad roof cornice.
            for x in (-4.80,4.80):
                for z in (.5,3.5,6.5): add('PILASTER',x=x,z=z)
            for z in (.5,3.5,6.5): add('CORNER_QUOINS',x=5,z=z)
            for f in range(3):
                for x in (-3.2,0,3.2):
                    if f==0 and x==0: continue
                    add('WIN_FRAME_M',x=x,z=f*3.2+.9)
                for y in (2,5): add('WIN_FRAME_S',x=5,y=y,z=f*3.2+.9,angle=90)
            add('WIN_SHUTTERS',x=-3.2,z=4.1)
            add('WIN_BARS',x=3.2,z=.9)
            add('BALCONY_SOVIET_OPEN',x=0,z=6.4)
            add('PORCH_STEPS_3',x=-.50)
            add('DOOR_FRAME_ENTRANCE',x=-.50,z=.45)
            add('DOOR_CANOPY',x=-.50,z=2.95)
            # Front run [-4.5,4.5], bounded by two half-metre corner sockets.
            for x in range(-4,5): add('CORNICE_1M',x=x,z=H-.35)
            add('CORNICE_CORNER',x=5,z=H-.35)
            add('CORNICE_CORNER',x=-5,z=H-.35,angle=-90)
            add('CORNICE_CORNER',x=5,y=7,z=H-.35,angle=90)
            for y in (1,2,3,4,5,6): add('CORNICE_1M',x=5,y=y,z=H-.35,angle=90)
            add('ROOF_CHIMNEY',x=-2.8,y=4.7,z=H+.18)
            add('ROOF_ANTENNA',x=2.6,y=4.5,z=H+.18)
            for z in range(9): add('DRAINPIPE_SEGMENT_1M',x=-4.45,z=z+.30)
            add('DRAINPIPE_FUNNEL',x=-4.45,z=9.30)
            for x in (-4,-3,-2,1,2,3,4): add('GAS_PIPE_RUN_1M',x=x,z=.62)
        elif kind=='panel_block':
            # Regular 3.6 m window bays, 2.8 m floor pitch, blank short end.
            for x in (-6.5,-5.5,-4.5,-3.5,-2.5,2.5,3.5,4.5,5.5,6.5): add('PLINTH_1M',x=x)
            for f in range(5):
                for x in (-5.4,-1.8,1.8,5.4): add('WIN_FRAME_L',x=x,z=f*2.8+.85)
                if f>0:
                    for x in (-5.4,5.4): add('BALCONY_GLAZED' if f==3 else 'BALCONY_SOVIET_OPEN',x=x,z=f*2.8)
            # Preview-only thin seams are geometry on the host box, not extra kit assets.
            for z in (2.8,5.6,8.4,11.2):
                box('Panel_Seam_H_'+str(z),W,.025,.03,y=-.018,z=z,col='panel.dark')
            for x in (-3.6,0,3.6):
                box('Panel_Seam_V_'+str(x),.03,.025,H,x=x,y=-.018,col='panel.dark')
            for x in (-6.5,-5.5,-4.5,-3.5,-2.5,-1.5,-.5,.5,1.5,2.5,3.5,4.5,5.5,6.5): add('ROOF_PARAPET_1M',x=x,z=H+.18)
            for y in (.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5): add('ROOF_PARAPET_1M',x=W/2,y=y,z=H+.18,angle=90)
            add('PORCH_STEPS_3',x=0); add('DOOR_FRAME_ENTRANCE',z=.45); add('DOOR_CANOPY',z=2.95)
            add('WIN_AC_UNIT',x=-2.9,z=3.9)
            for z in range(14): add('DRAINPIPE_SEGMENT_1M',x=6.95,z=z)
            add('DRAINPIPE_FUNNEL',x=6.95,z=14)
            add('ROOF_VENT',x=-2.0,y=3,z=H+.18)
            add('ROOF_SATELLITE_DISH',x=3.0,y=1.0,z=H+.18)
        else:
            for x in (-4,-3,-2,2,3,4): add('PLINTH_1M',x=x)
            add('DOOR_FRAME_ENTRANCE',x=-.30)
            for x in (-2.65,2.3): add('WIN_FRAME_L',x=x,z=.65)
            add('SHOP_AWNING_STRIPED',x=2.3,z=2.08)
            add('SHOP_SIGNBOARD_BLANK',x=2.3,z=2.66)
            # Closed roller shutter on side wall shows its shape without occluding the storefront.
            add('SHOP_ROLLER_SHUTTER',x=4.5,y=2.4,z=0,angle=90)
            for x in (-3.5,-2.5,-1.5,-.5,.5,1.5,2.5,3.5): add('CORNICE_1M',x=x,z=H-.35)
            add('CORNICE_CORNER',x=4.5,z=H-.35)
            add('CORNICE_CORNER',x=-4.5,z=H-.35,angle=-90)
            add('CORNICE_CORNER',x=4.5,y=5,z=H-.35,angle=90)
            for y in (1,2,3,4): add('CORNICE_1M',x=4.5,y=y,z=H-.35,angle=90)
            for z in range(3): add('DRAINPIPE_SEGMENT_1M',x=-4.2,z=z)
            add('DRAINPIPE_FUNNEL',x=-4.2,z=3)
            add('ROOF_VENT',x=-2,y=3,z=H+.18)
        bpy.context.view_layer.update()
        filename={'townhouse':'02_townhouse_eye_3q.png','panel_block':'03_panel_block_eye_3q.png','shop':'04_shop_eye_3q.png'}[kind]
        if args.review_previews: filename=filename.replace('.png','_review02.png')
        target=(0,D*.28,H*.49)
        render(studio,coll,root/filename,base+part,az=35,el=12,res=(1800,1600),eye=1.75,target=target,pad=1.06)
        records[kind]=dict(preview=filename,height_m=H,storeys=3 if kind=='townhouse' else 5 if kind=='panel_block' else 1,
                           eye_z_m=1.75,camera=list(studio.cam.location),plain_box_dimensions=[W,D,H],module_instances=len(part))
        # Concrete before/after evidence with the identical eye-level camera and light.
        for o in part: o.hide_render=True
        path=root/filename.replace('eye_3q','plain_box_same_camera')
        if not path.exists():
            ensure_new(path); scene.render.filepath=str(path); bpy.ops.render.render(write_still=True,scene=scene.name)
        for o in part: o.hide_render=False
    return records


def lineup(objects,mats,rev,args):
    scene,coll,studio=make_scene('G12_All_Module_Lineup',args.samples,args.cpu)
    view=[]
    # Wall gallery: six columns, all assets on their own wall-plane panels.
    # Rows are offset vertically for a readable true 3D line-up, rather than occluded ranks.
    for i,(name,src) in enumerate(objects.items()):
        col=i%6; row=i//6
        x=(col-2.5)*5.6; z=(5-row)*5.0+.45
        src.data.calc_loop_triangles()
        dz=(4.10-src.dimensions.z)/2
        if name=='DOOR_CANOPY': dz+=.55
        inst=instance(src,coll,'Lineup_'+name,x-2.20 if name=='FIRE_ESCAPE_STAIR_FLOOR' else x,0,z+dz)
        view.append(inst)
        m=Mesh(); m.b(5.35,.08,4.70,y=.06,col='panel' if row%2 else 'cream',role='plaster')
        panel=object_from('Preview_Wall_'+name,m,coll,mats); panel.location=(x,.12,z-.20); view.append(panel)
        label(coll,name,x,-.08,z+4.30,.18)
        label(coll,str(len(src.data.loop_triangles))+' / '+str(SPECS[name]['budget'])+' TRIS',x,-.08,z+4.05,.14)
    m=Mesh(); m.b(.50,.32,1.75,y=0,col='ochre',role='plaster')
    scale=object_from('HumanSize_Box_1_75m',m,coll,mats); scale.location=(13.9,-.3,.45); view.append(scale)
    label(coll,'1.75 m SCALE BOX',13.9,-.50,.24,.18)
    fname='01_all_modules_lineup_review02.png' if args.review_previews else '01_all_modules_lineup.png'
    render(studio,coll,HERE/'Previews'/rev/fname,view,az=12,el=6,
           res=(4000,3300),ortho=True,pad=1.035)
    return dict(module_count=len(objects),scale_box_m=[.50,.32,1.75],preview=fname)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--revision',type=int,default=1)
    parser.add_argument('--samples',type=int,default=32)
    parser.add_argument('--cpu',action='store_true')
    parser.add_argument('--no-render',action='store_true')
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--preview-existing',action='store_true')
    parser.add_argument('--audit-existing',action='store_true')
    parser.add_argument('--review-previews',action='store_true',help='New review02 files; no geometry changes')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.review_previews and not args.preview_existing:
        raise RuntimeError('--review-previews requires --preview-existing')
    if args.revision<1: raise RuntimeError('Positive revision required')
    rev=f'v{args.revision:02d}'
    if args.audit_existing: audit_existing(rev); return
    if not args.check_only and not args.preview_existing:
        for p in [HERE/f'SK3-BLDDETAILS-001_{rev}.blend',HERE/f'validation_{rev}.json']+[HERE/f'{n}_{rev}.fbx' for n in SPECS]: ensure_new(p)
    objects,mats,report=build_all()
    if not report['all_checks_passed']: raise RuntimeError('Geometry gate failed; no deliverables exported.')
    print('ALL_33_GEOMETRY_PASS',report['total_triangles'],flush=True)
    if args.check_only: return
    if args.preview_existing:
        saved=json.loads((HERE/f'validation_{rev}.json').read_text(encoding='utf-8'))
        if any(saved['assets'][n]['geometry_sha1']!=r['geometry_sha1'] for n,r in report['assets'].items()):
            raise RuntimeError('Existing revision geometry differs; new revision required.')
    else: export_all(objects,report,rev)
    if not args.no_render:
        line=lineup(objects,mats,rev,args)
        examples=facades(objects,mats,rev,args)
        path=HERE/f'preview_manifest_{rev}_review02.json' if args.review_previews else HERE/f'preview_manifest_{rev}.json'
        if not path.exists(): write_json(path,dict(lineup=line,facades=examples))
        # Separate preview-only project: the master contains only the 33 export meshes.
        preview_blend=HERE/f'SK3-BLDDETAILS-001_Demos_{rev}_review02.blend' if args.review_previews else HERE/f'SK3-BLDDETAILS-001_Demos_{rev}.blend'
        if not preview_blend.exists():
            ensure_new(preview_blend); bpy.ops.wm.save_as_mainfile(filepath=str(preview_blend))


if __name__=='__main__': main()
