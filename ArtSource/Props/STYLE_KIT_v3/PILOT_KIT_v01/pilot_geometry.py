"""G16 original deterministic geometry. Read-only dependency: G12 / STYLE_KIT_v2.
All coordinates and collider transforms are Blender local XYZ in metres.
"""
import sys, math
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'BUILDING_DETAILS'))
import build_building_details as g12
sk = g12.sk
from mathutils import Vector, Matrix
T, R = sk.T, sk.R
ROLES = g12.ROLES
GROUND = 'Ground Z=0, footprint centre X=Y=0; front -Y'
WALL = g12.WALL_PIVOT
SPECS = {}

def register(name, group, budget, snap, pivot=GROUND, **contracts):
    def wrap(fn):
        SPECS[name] = dict(build=fn, group=group, budget=budget, snap=snap, pivot=pivot, contracts=contracts)
        return fn
    return wrap

class Mesh(g12.Mesh):
    def __init__(self):
        super().__init__()
        self.colliders = []
        self.parts = []
        self.M = Matrix.Identity(4)

    def proxy(self, size, matrix, kind, sid, name, exact='visible_box', top=False):
        q = matrix.to_quaternion()
        c = dict(id=f'COL_{len(self.colliders):03d}', name=name, shape='box', classification=kind,
                 center_m=list(matrix.translation), size_m=list(size), rotation_quaternion_xyzw=[q.x,q.y,q.z,q.w],
                 source_shell=sid, match=exact, supports_standing=(kind=='walkable' or top))
        if kind=='walkable' or top:
            c['top_surface'] = dict(center_m=list(matrix @ Vector((0,0,size[2]/2))),
                normal=list(matrix.to_3x3() @ Vector((0,0,1))), extent_xy_m=list(size[:2]))
        self.colliders.append(c)

    def B(self, size, at, col='wood', role='wood', kind='solid', name='member', rot=None, top=False):
        M = self.M @ T(*at) @ (rot if rot is not None else Matrix.Identity(4))
        sid = self.box(*size,col,M=M,role=role,name=name)
        self.parts.append(dict(shell=sid,primitive='box',size=list(size),matrix=[list(r) for r in M],name=name))
        if kind: self.proxy(size,M,kind,sid,name,top=top)
        return sid

    def beam(self, a,b,width=.12,col='wood',role='wood',kind='solid',name='beam'):
        a,b=Vector(a),Vector(b)
        M=sk.frame_from((a+b)/2,b-a)
        return self.B(((b-a).length,width,width),(0,0,0),col,role,kind,name,rot=M)

    def C(self,r,length,at,col='wood',role='wood',n=8,rot=None,kind='solid',name='octagonal_member'):
        # Every regular even-sided prism is EXACTLY the union of n/2 inscribed
        # rectangles joining opposite edges. No capsule padding or oversized AABB.
        M=self.M @ T(*at) @ (rot if rot is not None else Matrix.Identity(4))
        sid=self.cyl(r,length,n,col,M=M,role=role,normals='flat',name=name,offset=math.pi/n)
        self.parts.append(dict(shell=sid,primitive='regular_prism',radius=r,length=length,sides=n,
                               matrix=[list(row) for row in M],name=name))
        if kind:
            for k in range(n//2):
                Q=M @ R(k*360/n,'Z') @ T(0,0,length/2)
                self.proxy((2*r*math.cos(math.pi/n),2*r*math.sin(math.pi/n),length),Q,kind,sid,name,
                           exact='exact_union_regular_prism')
        return sid

    def accent(self, poly, depth, at, col='wood',role='wood',name='carved_trim'):
        return self.prism(poly,depth,col,M=self.M@T(*at),role=role,name=name,normals='weighted')

    def roof(self,w,d,eave,rise,cy=0,holes=(),col='roof',panels=1):
        # Roof sheets are thick oriented boxes; omitted sheets leave real holes.
        length=math.hypot(w/2,rise); angle=math.degrees(math.atan2(rise,w/2))
        for side in (-1,1):
            for j in range(panels):
                if (side,j) in holes: continue
                self.B((length,d/panels,.10),(side*w/4,cy-d/2+(j+.5)*d/panels,eave+rise/2),
                       col,'roof','solid','pitched_roof_panel',R(side*angle,'Y'))

@register('SCARECROW','A',800,'Front -Y. Post foot on ground; 1.90 m overall. Coat sleeve and hem deliberately uneven.')
def scarecrow():
    m=Mesh()
    m.B((.14,.14,1.70),(0,0,.85),name='cross_post')
    m.B((1.28,.12,.12),(0,0,1.38),name='cross_arm')
    m.B((.50,.27,.64),(0,-.045,1.15),'coat','metal_painted',name='old_coat_body')
    m.B((.24,.29,.17),(-.14,-.045,.79),'coat','metal_painted',name='uneven_coat_hem')
    for side in (-1,1):
        m.B((.43,.26,.25),(side*.40,-.04,1.36),'coat','metal_painted',name='coat_sleeve',rot=R(side*8,'Y'))
    m.C(.19,.35,(0,-.02,1.55),'hay','wood',name='sack_head')
    m.B((.12,.06,.20),(.09,-.205,1.70),'earth','wood',None,'sack_patch')
    m.B((.14,.10,.28),(-.10,-.20,1.08),'hay','wood',None,'coat_patch')
    return m

@register('MAILBOX_RURAL','A',500,'Post foot at origin. Mouth/front -Y; mount beside gate outside clear opening.')
def mailbox():
    m=Mesh(); m.B((.16,.16,1.02),(0,0,.51),name='post')
    m.B((.48,.62,.35),(0,-.06,1.18),'paint','metal_painted',name='box_body')
    m.B((.54,.68,.08),(0,-.06,1.395),'metal','metal_painted',name='lid')
    m.B((.34,.065,.09),(0,-.402,1.23),'dark','metal_dark',None,'letter_slot')
    m.B((.075,.14,.26),(.28,.06,1.38),'rust','metal_painted',name='raised_flag')
    return m

@register('CART_WOODEN','A',1500,'Two wheels and one forward shaft. Bed top Z=.72 m. Front/shaft -Y.')
def cart():
    m=Mesh(); wz=.44*math.cos(math.pi/8)
    for i in range(5): m.B((.235,1.50,.12),(-.48+i*.24,.18,.66),kind='walkable',name='bed_plank')
    for x in (-.59,.59):
        for z in (.87,1.10): m.B((.10,1.50,.18),(x,.18,z),name='side_board')
        for y in (-.52,.86): m.B((.12,.12,.55),(x,y,.945),name='bed_stake')
    for z in (.87,1.10): m.B((1.08,.10,.18),(0,.88,z),name='tailboard')
    m.C(.08,1.65,(-.825,.27,wz),'dark','metal_dark',rot=R(90,'Y'),name='axle')
    for x in (-.79,.79):
        m.C(.44,.14,(x-.07,.27,wz),'wood','wood',rot=R(90,'Y'),name='wheel')
        m.C(.13,.18,(x-.09,.27,wz),'metal','metal_dark',rot=R(90,'Y'),name='wheel_hub')
        for a in (0,60,120): m.B((.07,.65,.09),(x-.078,.27,wz),'earth','wood',None,'wheel_spoke',R(a,'X'))
    m.beam((0,-.50,.55),(0,-1.65,.29),.14,name='single_draw_shaft')
    m.B((.40,.16,.14),(0,-1.60,.28),name='shaft_handle')
    return m

@register('WOODPILE','A',1200,'Overall envelope 2.0 x .8 x 1.4 m. Logs face -Y; open sides.',nominal=[2,.8,1.4])
def woodpile():
    m=Mesh()
    for x in (-.84,.84): m.B((.12,.66,.10),(x,0,.05),name='ground_skid')
    for row in range(4):
        for j in range(6-row%2):
            x=-.72+row%2*.14+j*.285
            m.C(.15,.61,(x,.305,.24+row*.25),'wood','wood',rot=R(90,'X'),name='stacked_log')
            m.C(.105,.012,(x,-.308,.24+row*.25),'hay','wood',n=6,rot=R(90,'X'),kind=None,name='cut_log_end')
    for x in (-.91,.91): m.B((.12,.12,1.25),(x,.28,.625),name='roof_post')
    m.B((2,.8,.10),(0,0,1.35),'roof','roof',name='shelter_roof')
    return m

def ruin(w,d,h):
    m=Mesh()
    for x in (-w/2+.10,w/2-.10):
        for y in (-d/2+.10,d/2-.10): m.B((.20,.20,h),(x,y,h/2),name='structural_post')
    for side in (-1,1):
        for j in range(7):
            hh=h*(.48 if side==-1 and j in (1,2) else .78 if j==4 else 1)
            if side==1 and j==1: continue
            m.B((.12,d/7-.022,hh),(side*(w/2-.06),-d/2+(j+.5)*d/7,hh/2),name='partial_wall_board')
    for j in range(9):
        hh=h*(.74 if j in (3,4) else 1)
        m.B((w/9-.025,.12,hh),(-w/2+(j+.5)*w/9,d/2-.06,hh/2),name='back_wall_board')
    # Wide front opening. No whole-shed bounding box collision.
    m.B((w,.16,.18),(0,-d/2+.08,h-.09),name='front_header')
    m.roof(w+.22,d+.24,h,.62 if w<4 else .95,holes={(-1,1),(-1,2),(1,3)},panels=5)
    m.beam((-w/2+.15,-d/2+.12,.2),(-w/2+.15,d/2-.12,h-.2),.12,name='exposed_wall_brace')
    return m

@register('SHED_RUINED','A',1800,'3 x 2.6 m wall footprint; clear front opening. Broken walls and three missing roof panels; no invisible hull.')
def shed(): return ruin(3,2.6,2.1)

@register('BARN_RUINED','A',3000,'5 x 4 m wall footprint; open front, partial walls and holed pitched roof. Ground origin.')
def barn(): return ruin(5,4,3.0)

@register('TRACTOR_BROKEN','A',3000,'Length 3.20 m along Y; front -Y. Missing front-right wheel, visible axle and grounded support block.',nominal_y=3.2)
def tractor():
    m=Mesh()
    m.B((.85,2.72,.30),(0,-.05,.68),'rust','metal_painted',name='chassis')
    m.B((.88,1.25,.73),(0,-.72,1.18),'rust','metal_painted',name='engine_hood')
    m.B((1.04,.18,.20),(0,-1.51,.64),'dark','metal_dark',name='front_bumper')
    m.B((.72,.07,.49),(0,-1.385,1.17),'dark','metal_dark',None,'radiator')
    for x in (-.22,0,.22): m.B((.08,.08,.42),(x,-1.425,1.17),'metal','metal_painted',None,'grille_rib')
    for x in (-.72,.72):
        m.C(.64,.32,(x-.16,.92,.64*math.cos(math.pi/8)),'dark','metal_dark',rot=R(90,'Y'),name='rear_tire')
        m.C(.29,.34,(x-.17,.92,.64*math.cos(math.pi/8)),'rust','metal_painted',rot=R(90,'Y'),name='rear_hub')
        m.B((.48,1.28,.10),(x,.92,1.27),'rust','metal_painted',name='rear_fender')
    m.C(.34,.20,(-.78,-1.06,.34*math.cos(math.pi/8)),'dark','metal_dark',rot=R(90,'Y'),name='front_left_tire')
    m.C(.14,.22,(-.79,-1.06,.34*math.cos(math.pi/8)),'metal','metal_painted',rot=R(90,'Y'),name='front_hub')
    m.C(.08,1.46,(-.73,-1.06,.36),'dark','metal_dark',rot=R(90,'Y'),name='exposed_front_axle')
    m.B((.30,.38,.29),(.48,-1.05,.145),name='support_block')
    m.B((.56,.56,.14),(0,.70,1.09),'dark','metal_dark',name='seat')
    m.B((.56,.12,.40),(0,.94,1.32),'dark','metal_dark',name='seat_back')
    m.beam((0,.28,.94),(0,.03,1.55),.10,'dark','metal_dark',name='steering_column')
    m.C(.23,.08,(0,-.04,1.53),'dark','metal_dark',rot=R(28,'X'),name='steering_wheel')
    m.B((.12,.12,.85),(-.25,-.84,1.97),'dark','metal_dark',name='exhaust')
    m.B((.28,.36,.10),(-.57,.05,.72),'metal','metal_dark','walkable','access_step')
    m.B((.30,.16,.18),(0,1.52,.61),'dark','metal_dark',name='rear_hitch')
    return m

@register('HAY_BALE_ROUND','A',500,'Axis X, flat octagonal ground contact; 1.4 m long. Broad bands, no fine straw noise.')
def bale_round():
    m=Mesh(); r=.66; z=r*math.cos(math.pi/8)
    pos=-.7
    for j,length in enumerate((.30,.07,.66,.07,.30)):
        m.C(r,length,(pos,0,z),'earth' if j%2 else 'hay','wood',rot=R(90,'Y'),name='bale_binding' if j%2 else 'round_bale')
        pos+=length
    # Inset end discs and broad binding bands read without unique textures.
    for x in (-.72,.70): m.C(.48,.02,(x,0,z),'earth','wood',rot=R(90,'Y'),name='compressed_end')
    return m

@register('HAY_BALE_SQUARE','A',300,'1.1 x .65 x .60 m core. Top standable; broad two-band silhouette.')
def bale_square():
    m=Mesh(); m.B((1.1,.65,.60),(0,0,.30),'hay','wood','walkable','bale_body')
    for x in (-.30,.30):
        m.B((.07,.67,.04),(x,0,.58),'earth','wood',None,'binding_top')
        for y in (-.33,.33): m.B((.07,.035,.58),(x,y,.29),'earth','wood',None,'binding_side')
    return m

def rural_window(w,h):
    m=Mesh()
    m.B((w,.28,.10),(0,-.14,.05),'wood','wood','walkable','sill')
    for x in (-w/2+.065,w/2-.065): m.B((.13,.18,h-.20),(x,-.09,h/2),'wood','wood',name='trim_jamb')
    m.B((w,.20,.10),(0,-.10,h-.05),'wood','wood',name='lintel')
    m.B((w-.26,.02,h-.30),(0,-.025,h/2-.025),'glass','glass',name='recessed_glass')
    m.B((.06,.09,h-.30),(0,-.07,h/2-.025),'wood','wood',name='mullion')
    # Two broad notches form the nalichnik crown; no tiny carved noise.
    m.accent([(-w/2+.04,0),(-w*.22,.08),(0,.025),(w*.22,.08),(w/2-.04,0)],.06,
             (0,-.23,h-.13),'plaster','wood','carved_nalichnik')
    return m

for suffix,w,h in [('090x120',.9,1.2),('120x140',1.2,1.4)]:
    register('WIN_FRAME_RURAL_'+suffix,'B',120,'Outer W/H includes nalichnik and sill; sill bottom at floor +.90. Glass front Y=-.035, trim front Y=-.18.',WALL,nominal_xz=[w,h])(
        lambda w=w,h=h:rural_window(w,h))

@register('WIN_SHUTTERS_RURAL','B',300,'Open pair for WIN_FRAME_RURAL_120x140; same wall pivot and bottom. Centre opening 1.20 m.',WALL)
def shutters():
    m=Mesh()
    for side in (-1,1):
        for j in range(3): m.B((.18,.10,1.22),(side*.91+(j-1)*.19,-.08,.70),'wood','wood',name='shutter_board')
        for z in (.28,1.10): m.B((.55,.08,.10),(side*.91,-.17,z),'earth','wood',name='shutter_batten')
        m.beam((side*.91-.22,-.18,.34),(side*.91+.22,-.18,1.02),.07,'earth','wood',name='shutter_brace')
    return m

@register('DOOR_FRAME_RURAL','B',320,'Door leaf 1.0 x 2.1 m; front Y=+.12, true 12 cm wall recess. Cut host opening 1.0 x 2.1 m, depth >=.20 m. Closed static leaf.',WALL,
          wall_cutout=dict(width_m=1,height_m=2.1,depth_m=.20),door_recess_m=.12)
def door():
    m=Mesh()
    for x in (-.57,.57): m.B((.14,.32,2.24),(x,.04,1.12),'wood','wood',name='reveal_jamb')
    m.B((1,.32,.14),(0,.04,2.17),'wood','wood',name='header')
    m.B((1,.08,2.1),(0,.16,1.05),'wood','wood',name='recessed_door_leaf')
    m.B((1,.38,.06),(0,.01,.03),'earth','wood','walkable','threshold')
    for z in (.62,1.60): m.B((.76,.035,.58),(0,.1025,z),'earth','wood',None,'door_panel')
    m.B((.08,.10,.24),(.35,.065,1.06),'metal','metal_dark',None,'handle')
    return m

@register('PORCH_RURAL','B',1500,'Wall Y=0. Three .15 m risers and .32 m treads; platform 1.50 x 1.10 m, top Z=.45. Door sits at Z=.45. Two roof posts.',WALL,
          standable_platform=dict(x=[-.75,.75],y=[-1.10,0],top_z=.45),step_rise_m=.15)
def porch():
    m=Mesh(); m.B((1.50,1.10,.15),(0,-.55,.375),kind='walkable',name='platform')
    for i in range(3): m.B((1.50,.32,.15*(i+1)),(0,-1.90+.32*i,.075*(i+1)),kind='walkable',name=f'step_{i+1}')
    for x in (-.86,.86):
        m.B((.16,.16,2.55),(x,-1.04,1.275),name='roof_post')
        m.B((.12,.12,1.05),(x,-.08,.975),name='rear_rail_post')
        for z in (.88,1.45): m.B((.12,1.04,.10),(x,-.54,z),name='side_rail')
        m.B((.14,1.16,.12),(x,-.55,.12),name='platform_leg_runner')
    m.roof(2.05,1.48,2.55,.42,cy=-.64)
    return m

@register('PLINTH_STONE_1M','B',180,'Exact X pitch 1 m; flat capped ends X=+/- .50. Bottom Z=0, top .60; interrupt at doors.',WALL,tile_pitch_m=1)
def plinth():
    m=Mesh(); m.B((1,.20,.60),(0,-.10,.30),'earth','concrete',name='continuous_base')
    for row in range(3):
        for j in range(3):
            m.B((1/3-.015,.04,.18),(-1/3+j/3,-.215,.10+row*.20),'concrete' if (row+j)%3 else 'stone','concrete',None,'broad_stone_face')
    return m

@register('EAVE_FASCIA_1M','B',80,'Exact X pitch 1 m, capped ends; board bottom at roof eave elevation.',WALL,tile_pitch_m=1)
def fascia():
    m=Mesh(); m.B((1,.14,.24),(0,-.07,.12),name='fascia_board')
    m.B((1,.20,.06),(0,-.10,.25),'earth','wood',name='upper_lip')
    return m

@register('GABLE_VENT','B',200,'Wall plane; mount in gable with bottom at desired elevation. Opaque back prevents wall flicker.',WALL)
def vent():
    m=Mesh(); m.B((.58,.06,.42),(0,-.03,.21),'dark','metal_dark',name='vent_back')
    for x in (-.32,.32): m.B((.08,.14,.58),(x,-.07,.29),name='side_frame')
    for z in (.04,.54): m.B((.58,.14,.08),(0,-.07,z),name='horizontal_frame')
    for z in (.16,.29,.42): m.B((.54,.16,.06),(0,-.11,z),name='vent_louver',rot=R(18,'X'))
    return m

@register('CHIMNEY_BRICK_RURAL','B',400,'Roof-plane origin Z=0. Four flue walls leave real opening; cap/rim supports standing.',
          'Roof plane Z=0, footprint centre X=Y=0')
def chimney():
    m=Mesh()
    for x in (-.23,.23): m.B((.14,.60,1.25),(x,0,.625),'brick','brick',name='flue_side')
    for y in (-.23,.23): m.B((.32,.14,1.25),(0,y,.625),'brick','brick',name='flue_front_back')
    for x in (-.29,.29): m.B((.16,.74,.12),(x,0,1.28),'concrete','concrete','walkable','rim_side')
    for y in (-.29,.29): m.B((.42,.16,.12),(0,y,1.28),'concrete','concrete','walkable','rim_front_back')
    for z in (.34,.69,1.04): m.B((.61,.05,.06),(0,-.305,z),'rust','brick',None,'broad_brick_course')
    return m

def fence(m,w,h,solid=False):
    count=10 if solid else 9
    bw=w/count if solid else .14
    for j in range(count):
        x=-w/2+(j+.5)*w/count
        # Flat picket crowns are usable. One shorter board is deliberate asymmetry.
        hh=h if solid or j!=1 else h-.12
        m.B((bw,.10,hh),(x,-.055,hh/2),'wood','wood','solid','fence_board',top=True)
    for z in (.28,h-.22): m.B((w,.12,.12),(0,.045,z),'earth','wood','solid','fence_rail',top=True)

@register('FENCE_PICKET_2M','C',400,'X pitch 2 m between end sockets +/-1. Separate POST on sockets. Flat picket tops, height 1.20 m; solid boards, open gaps.',tile_pitch_m=2)
def picket():
    m=Mesh(); fence(m,2,1.2); return m

@register('POST','C',100,'Picket fence socket post. Centre on joints or gate outside; 0.18 m square, top 1.30 m.')
def post():
    m=Mesh(); m.B((.18,.18,1.30),(0,0,.65),name='picket_post',top=True)
    m.B((.24,.24,.08),(0,0,1.30),'earth','wood',name='post_cap',top=True)
    return m

@register('GATE_PICKET','C',400,'Open 90 degrees toward -Y, hinge X=-.56. Clear passage X=[-.50,.50], 1.00 m. Posts included. No collider across opening.',
          opening=dict(x=[-.50,.50],y=[-.30,.30],z=[0,1.20],clear_width_m=1.0))
def gate_picket():
    m=Mesh()
    for x in (-.65,.65): m.B((.18,.18,1.30),(x,0,.65),name='gate_post',top=True)
    m.M=T(-.61,0,0)@R(-90,'Z')@T(.50,0,0)
    fence(m,1,1.2)
    m.M=Matrix.Identity(4)
    return m

@register('FENCE_BOARD_2M','C',400,'Solid 2 m board panel, 1.8 m high. Exact X pitch 2 m; integrated back posts remain inside ends.',tile_pitch_m=2)
def board():
    m=Mesh(); fence(m,2,1.8,True)
    for x in (-.88,.88): m.B((.18,.18,1.8),(x,.16,.90),name='board_post',top=True)
    return m

@register('GATE_DOUBLE','C',600,'Two leaves opened 90 degrees toward -Y. Included posts; clear 3.00 m passage X=[-1.5,1.5]. Static open gate, no opening collider.',
          opening=dict(x=[-1.5,1.5],y=[-.30,.30],z=[0,1.8],clear_width_m=3.0))
def gate_double():
    m=Mesh()
    for side in (-1,1):
        m.M=Matrix.Identity(4)
        m.B((.22,.22,1.92),(side*1.83,0,.96),name='gate_post',top=True)
        m.M=T(side*1.72,0,0)@R(side*90,'Z')@T(-side*.75,0,0)
        fence(m,1.50,1.8,True)
        m.beam((-.63,.14,.20),(.63,.14,1.58),.12,name='leaf_brace')
    m.M=Matrix.Identity(4)
    return m

@register('RETAINING_EDGE_TIMBER_1M','C',180,'Exact X pitch 1 m; height .60 m, flat continuous .40 m-deep top. Place along raised soil boundary.',tile_pitch_m=1,
          standable_platform=dict(x=[-.5,.5],y=[-.2,.2],top_z=.60))
def retain_timber():
    m=Mesh()
    for j in range(3): m.B((1,.40,.20),(0,0,.10+.20*j),'wood' if j!=1 else 'earth','wood','walkable','stacked_timber')
    return m

@register('RETAINING_EDGE_STONE_1M','C',200,'Exact X pitch 1 m; height .60 m. Flat .46 m-deep cap spans the full tile, no end protrusions.',tile_pitch_m=1,
          standable_platform=dict(x=[-.5,.5],y=[-.23,.23],top_z=.60))
def retain_stone():
    m=Mesh(); m.B((1,.40,.48),(0,0,.24),'concrete','concrete',name='stone_body')
    m.B((1,.46,.12),(0,0,.54),'stone','concrete','walkable','continuous_cap')
    for j in range(3): m.B((.30,.025,.20),(-.33+j*.33,-.2025,.23),'earth','concrete',None,'stone_relief')
    return m

@register('GARDEN_BED_2M','C',500,'Outer size 2.0 x 1.0 m. Border top .30 m, soil top .23 m. Sparse planting leaves paths visible.')
def garden():
    m=Mesh()
    for y in (-.45,.45): m.B((2,.10,.30),(0,y,.15),kind='walkable',name='bed_long_border')
    for x in (-.95,.95): m.B((.10,.80,.30),(x,0,.15),kind='walkable',name='bed_end_border')
    m.B((1.8,.80,.23),(0,0,.115),'earth','wood','walkable','soil')
    for j in range(4):
        for y in (-.20,.20):
            for a in (-28,28):
                m.B((.22,.08,.07),(-.63+j*.42,y,.30),'olive','wood',None,'crop_leaf',R(a,'Y'))
    return m

@register('WELL_RURAL','C',1000,'Open 0.8 m square shaft. Four log walls and rim have individual collision; roof posts and crank are solid. No invisible lid.')
def well():
    m=Mesh()
    for row in range(4):
        for y in (-.50,.50): m.B((1.20,.20,.20),(0,y,.10+row*.20),name='well_log')
        for x in (-.50,.50): m.B((.20,.80,.20),(x,0,.10+row*.20),name='well_return_log')
    for y in (-.52,.52): m.B((1.28,.24,.10),(0,y,.85),kind='walkable',name='well_rim')
    for x in (-.52,.52): m.B((.24,.80,.10),(x,0,.85),kind='walkable',name='well_rim_return')
    for x in (-.75,.75): m.B((.16,.16,2.10),(x,0,1.05),name='roof_post')
    m.C(.14,1.70,(-.85,0,1.30),'wood','wood',rot=R(90,'Y'),name='winch_drum')
    m.B((.10,.10,.42),(.91,0,1.10),'metal','metal_dark',name='crank_arm')
    m.B((.30,.10,.10),(1.01,0,.92),'wood','wood',name='crank_handle')
    m.roof(1.95,1.50,2.10,.43)
    return m

@register('OUTHOUSE','C',1000,'1.3 x 1.2 m footprint, closed static front -Y. Broad crescent-like vent relief; no animation.')
def outhouse():
    m=Mesh()
    for x in (-.60,.60): m.B((.10,1.20,2.10),(x,0,1.05),name='side_wall')
    m.B((1.10,.10,2.10),(0,.55,1.05),name='back_wall')
    for x in (-.49,.49): m.B((.22,.10,2.10),(x,-.55,1.05),name='front_jamb')
    m.B((.76,.10,1.93),(0,-.57,.965),'earth','wood',name='door')
    m.B((.76,.10,.17),(0,-.55,2.015),name='front_header')
    m.B((1.42,1.40,.12),(0,0,2.17),'roof','roof',name='shed_roof',rot=R(-6,'X'))
    for x in (-.34,0,.34): m.B((.065,.035,1.78),(x,-.637,.91),name='door_plank_relief',kind=None)
    m.accent([(-.12,0),(-.17,.10),(-.10,.25),(.09,.30),(-.015,.16),(.03,.04)],.025,(.05,-.651,1.41),'dark','metal_dark','crescent_vent')
    m.B((.08,.10,.23),(.25,-.68,.99),'metal','metal_dark',None,'handle')
    return m

def garage(ajar=False):
    m=Mesh()
    for x in (-1.57,1.57): m.B((.14,.24,2.50),(x,-.08,1.25),'metal','metal_dark',name='door_jamb')
    m.B((3,.24,.14),(0,-.08,2.43),'metal','metal_dark',name='door_header')
    for side in (-1,1):
        # Both leaves are present. Right leaf opens 58 degrees; left remains closed.
        angle=58 if ajar and side==1 else 0
        m.M=T(side*1.5,-.10,0)@R(angle,'Z')@T(-side*.75,0,0)
        m.B((1.48,.08,2.30),(0,0,1.15),'paint','metal_painted',name='garage_leaf')
        for x in (-.52,-.17,.18,.53): m.B((.07,.08,2.16),(x,-.07,1.15),'metal','metal_painted',name='pressed_vertical_rib')
        m.B((.10,.10,.25),(-side*.55,-.12,1.08),'dark','metal_dark',name='leaf_handle')
    m.M=Matrix.Identity(4)
    return m

@register('GARAGE_DOOR_METAL_3M','D',400,'Wall plane Y=0; clear frame width 3 m, opening height 2.36 m. Two closed static leaves. Host wall cut-out required.',WALL,
          wall_cutout=dict(width_m=3,height_m=2.36,depth_m=.25))
def garage_closed(): return garage(False)

@register('GARAGE_DOOR_METAL_3M_AJAR','D',400,'Same frame as closed. Right leaf 58 degrees outward; collision rotates with leaf. Approx .68 m access at door plane; not van-width.',WALL,
          wall_cutout=dict(width_m=3,height_m=2.36,depth_m=.25))
def garage_ajar(): return garage(True)

@register('GARAGE_ROW_ROOF_EDGE_1M','D',100,'Exact X pitch 1 m. Origin is bottom of edge at garage roof elevation. Flat capped ends.',WALL,tile_pitch_m=1)
def garage_roof():
    m=Mesh(); m.B((1,.28,.24),(0,-.14,.12),'metal','metal_painted',name='fascia')
    m.B((1,.38,.08),(0,-.19,.28),'roof','roof','walkable','roof_edge_cap')
    return m

@register('DUMPSTER_ENCLOSURE','D',400,'Outer 4 x 2 m; wall height 1.5 m. Front -Y has 3.6 m clear opening. No front wall/collision.',nominal=[4,2,1.5])
def enclosure():
    m=Mesh()
    for x in (-1.9,1.9): m.B((.20,2,1.5),(x,0,.75),'concrete','concrete','walkable','slab_side_wall')
    m.B((3.60,.20,1.5),(0,.90,.75),'concrete','concrete','walkable','slab_back_wall')
    for x in (-1.18,0,1.18): m.B((.08,.04,1.30),(x,.785,.70),'stone','concrete',None,'slab_joint')
    return m

@register('BENCH_SOVIET','D',800,'Seat top .46 m, length 1.8 m. Chunky concrete ends, wooden slats and one shortened back slat.')
def bench():
    m=Mesh()
    for x in (-.67,.67):
        m.B((.20,.55,.40),(x,0,.20),'concrete','concrete',name='concrete_leg')
        m.B((.12,.12,.48),(x,.21,.66),'metal','metal_dark',name='back_support')
    for y in (-.20,0,.20): m.B((1.80,.19,.08),(0,y,.42),'wood','wood','walkable','seat_slat')
    for i,z in enumerate((.68,.89)): m.B((1.8 if i==0 else 1.60,.10,.16),(-.10 if i else 0,.25,z),'wood','wood',name='back_slat')
    return m

@register('LAUNDRY_POLE_PAIR','D',200,'Pair centres X=+/-1.6 m, span 3.2 m. Bare courtyard T-poles only; no laundry or lines, per ArtDirection.md.')
def laundry():
    m=Mesh()
    for x in (-1.6,1.6):
        m.B((.26,.26,.16),(x,0,.08),'concrete','concrete',name='foot')
        m.B((.16,.16,2.18),(x,0,1.09),'metal','metal_painted',name='T_post')
        m.B((.16,1.15,.12),(x,0,2.18),'metal','metal_painted',name='crossbar')
    return m

@register('CONCRETE_LEDGE_1M','D',100,'Exact X pitch 1 m; top Z=.45, .60 m deep and continuous. Ground centre origin.',tile_pitch_m=1,
          standable_platform=dict(x=[-.5,.5],y=[-.3,.3],top_z=.45))
def concrete_ledge():
    m=Mesh(); m.B((1,.60,.45),(0,0,.225),'concrete','concrete','walkable','ledge_body')
    m.B((1,.025,.10),(0,-.3125,.10),'stone','concrete',None,'base_band')
    return m

@register('BASEMENT_ENTRANCE','D',1200,'Wall Y=0, pavement Z=0. Descend toward +Y: six .18 m risers, .30 m treads; landing top -1.08. Cut terrain X=[-.84,.84], Y=[-2.60,0], depth 1.20; cut basement doorway.',WALL,
          excavation=dict(x=[-.84,.84],y=[-2.60,0],z=[-1.20,0]),step_rise_m=.18,
          standable_platform=dict(x=[-.6,.6],y=[-.60,0],top_z=-1.08))
def basement():
    m=Mesh()
    m.B((1.2,.20,.12),(0,-2.50,-.06),'concrete','concrete','walkable','pavement_lip')
    for i in range(6):
        top=-.18*(i+1)
        m.B((1.2,.30,.12),(0,-2.25+i*.30,top-.06),'concrete','concrete','walkable',f'down_step_{i+1}')
    m.B((1.2,.60,.12),(0,-.30,-1.14),'concrete','concrete','walkable','lower_landing')
    for x in (-.72,.72):
        m.B((.24,2.60,1.30),(x,-1.30,-.55),'concrete','concrete',name='retaining_cheek')
        for y in (-2.45,-1.25,-.14): m.B((.10,.10,.90),(x,y,.55),'metal','metal_dark',name='guard_post')
        m.B((.10,2.45,.10),(x,-1.30,.99),'metal','metal_dark',name='guard_rail')
        m.beam((x,-2.39,.70),(x,-.66,-.38),.10,'metal','metal_dark',name='descending_handrail')
    m.B((1.85,1.20,.12),(0,-.50,1.53),'roof','roof',name='small_canopy')
    for x in (-.77,.77): m.beam((x,-.06,1.48),(x,-.90,.99),.10,'metal','metal_dark',name='canopy_bracket')
    return m

@register('METAL_STAIR_EXTERNAL','D',1800,'Wall plane Y=0, lower entrance X=0 at ground. Flight rises +X: 14 risers .20 m, run .28 m each; top landing X=[3.92,5.02], top Z=2.80. Clear tread width 1.20 m; rails outside.',
          'Wall Y=0 at lower flight start X=Z=0; outward -Y',step_rise_m=.20,step_run_m=.28,
          standable_platform=dict(x=[3.92,5.02],y=[-1.40,-.20],top_z=2.8))
def metal_stair():
    m=Mesh()
    for i in range(14): m.B((.28,1.20,.08),((i+.5)*.28,-.80,(i+1)*.20-.04),'metal','metal_dark','walkable',f'tread_{i+1:02d}')
    m.B((1.10,1.20,.12),(4.47,-.80,2.74),'metal','metal_dark','walkable','upper_landing')
    for y in (-1.51,-.09):
        m.beam((.06,y,.09),(3.92,y,2.68),.14,'dark','metal_dark',name='stringer')
        for i in (0,4,8,13):
            x=(i+.5)*.28; base=(i+1)*.20
            m.B((.10,.10,1),(x,y,base+.50),'metal','metal_dark',name='rail_post')
        m.beam((.14,y,1.20),(3.78,y,3.80),.10,'metal','metal_dark',name='flight_handrail')
        m.B((1.24,.10,.10),(4.40,y,3.80),'metal','metal_dark',name='landing_side_rail')
        m.B((.12,.12,3.80),(4.94,y,1.90),'metal','metal_dark',name='landing_support')
    # Landing exit remains open at +X. Rail returns only along sides.
    return m
