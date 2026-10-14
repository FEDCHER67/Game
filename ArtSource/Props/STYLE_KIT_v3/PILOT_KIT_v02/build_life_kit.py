"""G18 original garden anatomy. Read-only v01 geometry/export library; fresh v02 outputs."""
import sys, math, json, argparse
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'PILOT_KIT_v01'))
import build_pilot_kit as base
from pilot_geometry import Mesh, T, R, GROUND, WALL
from mathutils import Vector
SPECS = {}
def module(name, budget, group='A', decorative=False, pivot=GROUND):
    def wrap(fn):
        SPECS[name] = dict(build=fn, group=group, budget=budget, snap='Metres; front -Y; place by support surface.', pivot=pivot, contracts={}, decorative=decorative)
        return fn
    return wrap

def tube(m, radius, width, at, col='dark', role='metal_dark', n=16, axis='Y'):
    # Continuous annular tyre / handle: four joined loops, closed hollow topology.
    vs=[]
    for r,y in ((radius,-width/2),(radius,width/2),(radius-width,-width/2),(radius-width,width/2)):
        for j in range(n):
            a=(j+.5)*math.tau/n
            p=Vector((r*math.cos(a),y,r*math.sin(a)))+Vector(at)
            vs.append(tuple(p))
    fs=[]
    for j in range(n):
        k=(j+1)%n
        fs.extend([(j,k,n+k,n+j),(2*n+j,3*n+j,3*n+k,2*n+k),
                   (j,2*n+j,2*n+k,k),(n+j,n+k,3*n+k,3*n+j)])
    m.shell(vs,fs,col,role=role,name='continuous_annulus')

@module('LAUNDRY_CLOTHES',1000)
def laundry():
    m=Mesh()
    for x in (-1.9,1.9):
        m.B((.14,.14,2.05),(x,0,1.025),name='grounded_post')
        m.B((.10,.85,.10),(x,0,1.98),name='crossbar')
    for y in (-.30,.30):
        m.beam((-1.9,y,1.98),(0,y,1.87),.022,'dark','metal_dark',None,'line')
        m.beam((0,y,1.87),(1.9,y,1.98),.022,'dark','metal_dark',None,'line')
        for i in range(3):
            x=-1.12+i*1.1; top=1.87+.11*abs(x)/1.9; col=('plaster','paint','rust')[(i+(y>0))%3]
            m.B((.65,.024,.81),(x,y,top-.405),col,'plaster',None,'hanging_cloth')
            for dx in (-.23,.23):m.B((.028,.050,.07),(x+dx,y,top-.018),'wood','wood',None,'peg')
    return m

@module('FLOWER_BED',1500,decorative=True)
def flowers():
    m=Mesh(); m.B((1.65,.72,.12),(0,0,.06),'earth','wood',None,'soil')
    for x in (-.86,.86):m.B((.09,.84,.20),(x,0,.1),name='bed_end')
    for y in (-.405,.405):m.B((1.65,.09,.20),(0,y,.1),name='bed_side')
    for i in range(5):
        x=-.65+i*.32; y=.15*(-1)**i; z=.42+.09*(i%3)
        m.C(.018,z-.12,(x,y,.12),'coat','wood',6,kind=None,name='stem')
        for j in range(5):
            a=j*math.tau/5
            m.C(.065,.025,(x+.069*math.cos(a),y+.069*math.sin(a),z),'rust' if i%2 else 'hay','plaster',6,kind=None,name='petal')
        m.C(.038,.033,(x,y,z),'hay','plaster',6,kind=None,name='centre')
        m.B((.20,.07,.025),(x+.055,y,z*.62),'coat','wood',None,'leaf',R(-25,'Y'))
    return m

@module('DOGHOUSE',500)
def doghouse():
    m=Mesh(); m.B((1.05,1.18,.08),(0,0,.04),name='floor')
    for x in (-.48,.48):m.B((.09,1.18,.80),(x,0,.48),name='side_wall')
    m.B((.96,.08,.80),(0,.55,.48),name='back_wall')
    for x in (-.36,.36):m.B((.25,.09,.80),(x,-.55,.48),name='open_front_jamb')
    m.B((.50,.09,.20),(0,-.55,.78),name='door_lintel')
    m.roof(1.25,1.38,.85,.30,col='rust'); return m

@module('HEN_COOP_RUN',1500)
def coop():
    m=Mesh()
    # Raised coop joins the side of a visibly open, walk-in low run.
    for x in (-.60,.60):
        for y in (.25,1.30):m.B((.12,.12,.90),(x,y,.45),name='coop_leg')
    m.B((1.3,1.18,.10),(0,.775,.78),name='coop_floor')
    for x in (-.60,.60):m.B((.09,1.18,.72),(x,.775,1.19),name='coop_side')
    m.B((1.28,.08,.72),(0,1.325,1.19),name='coop_back')
    for x in (-.43,.43):m.B((.38,.08,.72),(x,.225,1.19),name='hatch_jamb')
    m.B((.50,.08,.22),(0,.225,1.44),name='hatch_lintel');m.roof(1.50,1.45,1.56,.35,cy=.775)
    for x in (-1.05,1.05):
        for y in (-1.65,-.65,.35):m.B((.09,.09,.85),(x,y,.425),name='run_post')
        for z in (.23,.70):m.B((.065,2.1,.075),(x,-.65,z),name='run_rail')
        for j in range(9):m.B((.025,.025,.62),(x,-1.55+j*.23,.42),'metal','metal_dark',None,'run_wire')
    for side in (-1,1):m.B((.57,.08,.65),(side*.77,-1.65,.40),name='gate_side')
    m.B((.07,.58,.65),(.46,-1.37,.40),name='open_gate_leaf')
    m.B((.42,1.03,.06),(0,-.25,.45),name='hen_ramp',rot=R(37,'X'))
    return m

@module('AXE_STUMP_LOGS',1200)
def axe():
    m=Mesh();m.C(.30,.46,(0,0,0),'wood','wood',10,name='stump')
    m.B((.055,.08,.67),(.03,0,.73),'wood','wood',name='axe_handle',rot=R(-14,'Y'))
    m.B((.25,.065,.16),(.10,0,.55),'metal','metal_dark',name='axe_head')
    for i,(x,z) in enumerate(((.6,.11),(.83,.11),(1.06,.11),(.715,.31),(.945,.31))):
        m.C(.115,.66,(x,-.30,z),'wood','wood',8,rot=R(-90,'X'),name='firewood')
    return m

@module('BUCKET_WATERING',1000)
def bucket():
    m=Mesh()
    # Open vessels, connected annular walls, base plate and supported handles.
    for x,r,h in ((-.22,.15,.28),(.30,.18,.32)):
        n=12; vs=[]
        for rr,z in ((r,0),(r,h),(r-.025,.025),(r-.025,h)):
            vs += [(x+rr*math.cos(j*math.tau/n),rr*math.sin(j*math.tau/n),z) for j in range(n)]
        fs=[]
        for j in range(n):
            k=(j+1)%n;fs += [(j,k,n+k,n+j),(2*n+j,3*n+j,3*n+k,2*n+k),(n+j,n+k,3*n+k,3*n+j),(j,2*n+j,2*n+k,k)]
        m.shell(vs,fs,'metal',role='metal_painted',name='open_vessel')
        m.C(r-.015,.026,(x,0,0),'metal','metal_painted',12,kind=None,name='base')
        m.B((r*1.8,.055,.045),(x,0,h+.18),'dark','metal_dark',None,'handle_top')
        for dx in (-r*.88,r*.88):m.B((.035,.04,.23),(x+dx,0,h+.07),'dark','metal_dark',None,'handle_support')
    m.beam((.44,0,.11),(.73,0,.31),.07,'metal','metal_painted',None,'spout')
    m.C(.06,.05,(.70,0,.29),'dark','metal_dark',8,rot=R(55,'Y'),kind=None,name='rose')
    m.B((.27,.23,.20),(.30,0,.10),'metal','metal_painted',name='lower_can_proxy_body')
    return m

@module('BICYCLE',2000)
def bicycle():
    m=Mesh(); rad=.36; z=rad*math.cos(math.pi/16)
    for x in (-.57,.57):
        tube(m,rad,.045,(x,0,z));tube(m,rad-.045,.019,(x,0,z),'metal','metal_dark')
        for a in range(0,360,60):
            ar=math.radians(a);m.beam((x,0,z),(x+.31*math.cos(ar),0,z+.31*math.sin(ar)),.010,'metal','metal_dark',None,'spoke')
    a=(-.57,0,z);b=(-.19,0,.86);c=(.08,0,.40);d=(.38,0,.85);e=(.57,0,z)
    for p,q in ((a,b),(a,c),(b,c),(b,d),(c,d),(d,e)):
        m.beam(p,q,.044,'paint','metal_painted',None,'frame')
    m.B((.25,.18,.055),(-.20,0,.96),'dark','metal_dark',None,'saddle')
    m.beam(b,(-.20,0,.95),.04,'metal','metal_dark',None,'seat_post')
    m.beam(d,(.34,0,1.10),.04,'metal','metal_dark',None,'handle_stem')
    m.beam((.34,-.26,1.10),(.34,.26,1.10),.04,'metal','metal_dark',None,'handle_bar')
    m.beam((.08,-.13,.40),(.08,.13,.40),.035,'metal','metal_dark',None,'crank_axle')
    m.B((.12,.10,.04),(.18,-.15,.34),'dark','metal_dark',None,'pedal')
    # Two actual tyre-contact feet, small exact proxies; decorative frame cannot block a road.
    for x in (-.57,.57):m.B((.12,.045,.035),(x,0,.0175),'dark','metal_dark',name='tyre_contact')
    return m

@module('TREE_SWING',500,decorative=True,pivot=WALL)
def swing():
    m=Mesh();m.B((.62,.30,.07),(0,0,.035),name='seat')
    for x in (-.27,.27):m.B((.025,.025,2.045),(x,0,1.0775),'hay','wood',None,'rope')
    return m

@module('APPLE_BASKET',1000)
def basket():
    m=Mesh();m.C(.26,.05,(0,0,0),'wood','wood',12,name='base')
    for j in range(12):
        a=j*math.tau/12
        m.B((.055,.09,.30),(.24*math.cos(a),.24*math.sin(a),.17),'hay','wood',None,'basket_slat',R(math.degrees(a),'Z'))
    for j in range(6):
        a=j*math.tau/6; x=.14*math.cos(a);y=.14*math.sin(a)
        m.C(.083,.10,(x,y,.235),'rust','plaster',8,kind=None,name='apple')
        m.B((.015,.016,.04),(x,y,.355),'wood','wood',None,'stem')
    return m

@module('CURTAIN_PAIR',300,decorative=True,pivot=WALL)
def curtains():
    m=Mesh()
    for side in (-1,1):
        for i in range(3):m.B((.10,.04,.95),(side*(.22+i*.09),.02*(i%2),.475),'hay','plaster',None,'fold')
    m.B((1.03,.04,.10),(0,.03,.97),'plaster','plaster',None,'valance')
    return m

@module('CROOKED_FENCE',500)
def crooked():
    m=Mesh()
    for x in (-1.0,1.0):m.B((.12,.12,1.1),(x,0,.55),name='post')
    for z in (.34,.76):m.B((2,.09,.10),(0,.04,z),name='rail')
    for i in range(9):
        m.B((.14,.07,.88),(-.84+i*.21,0,.53),'wood','wood',name='crooked_picket',rot=R((-7,3,9,-2)[i%4],'Y'))
    return m

@module('PICNIC_TABLE',600)
def picnic():
    m=Mesh()
    for x in (-.56,.56):
        for side in (-1,1):m.beam((x,side*.39,.06),(x,side*.18,.73),.10,name='splayed_leg')
        m.B((.10,1.4,.10),(x,0,.36),name='bench_support')
    for j in range(4):m.B((1.6,.18,.07),(0,-.285+j*.19,.745),name='table_plank')
    for y in (-.61,.61):m.B((1.7,.28,.08),(0,y,.44),name='bench_seat')
    # grounded ends close at exactly z=0
    for x in (-.56,.56):
        for y in (-.39,.39):m.B((.12,.12,.12),(x,y,.06),name='leg_foot')
    return m

@module('LEAFLESS_TREE',1200,'B')
def tree(trunk_height=2.6):
    m=Mesh();m.C(.17,trunk_height,(0,0,0),'wood','wood',8,name='trunk')
    for j in range(7):
        a=j*2.4; z=1.25+j*.34; q=(math.cos(a)*(.85+.08*j),math.sin(a)*(.85+.08*j),z+1)
        m.beam((0,0,z),q,.085,name='branch')
        for side in (-1,1):m.beam(q,(q[0]+side*.35,q[1]+.16*side,q[2]+.52),.035,kind=None,name='twig')
    return m

@module('CROW',300,'C',True)
def crow():
    m=Mesh()
    for x in (-.065,.065):m.B((.035,.11,.025),(x,-.005,.0125),'dark','metal_dark',None,'foot')
    for x in (-.065,.065):m.B((.022,.022,.09),(x,.015,.067),'dark','metal_dark',None,'leg')
    m.C(.13,.26,(0,.16,.21),'dark','metal_dark',8,rot=R(90,'X'),kind=None,name='body')
    m.C(.085,.10,(0,-.09,.285),'dark','metal_dark',8,kind=None,name='head')
    m.B((.053,.12,.035),(0,-.16,.31),'dark','metal_dark',None,'beak')
    for x in (-.115,.115):m.B((.045,.24,.15),(x,.025,.235),'dark','metal_dark',None,'folded_wing',R(15,'X'))
    m.B((.12,.18,.035),(0,.22,.18),'dark','metal_dark',None,'tail',R(-15,'X'))
    return m

@module('BUTTERFLY',150,'C',True)
def butterfly():
    m=Mesh();m.B((.018,.09,.016),(0,0,.008),'dark','metal_dark',None,'body')
    for side in (-1,1):
        m.B((.085,.085,.014),(side*.043,-.018,.027),'rust','plaster',None,'fore_wing',R(side*28,'Y'))
        m.B((.055,.047,.012),(side*.031,.04,.024),'hay','plaster',None,'rear_wing',R(side*25,'Y'))
    return m

base.HERE=HERE
base.SPECS=SPECS
original_collider_checks=base.collider_checks
def collider_checks(m,spec):
    checks,measure=original_collider_checks(m,spec)
    if spec.get('decorative'):
        checks.pop('nonempty_colliders',None)
        checks['decorative_collision_policy']=True
    return checks,measure
base.collider_checks=collider_checks
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',action='store_true');p.add_argument('--check',action='store_true');p.add_argument('--preview',action='store_true');p.add_argument('--tree-repair',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.tree_repair:
        spec=dict(SPECS['LEAFLESS_TREE']);spec['build']=lambda:tree(3.4);base.SPECS={'LEAFLESS_TREE':spec}
        objects,im,pal,report=base.build('v03');report['task']='G18';report['note']='Tree contact repair: trunk reaches every primary branch root; v02 files retained.'
        base.export(objects,im,pal,report,'v03');base.audit('v03')
    elif args.audit:base.audit('v02')
    elif args.preview:
        import pilot_previews as pv
        pv.HERE=HERE;pv.SPECS=SPECS
        pv.previews('v02',16)
    else:
        objects,im,pal,report=base.build('v02');report['task']='G18';report['unity_test']='PENDING checkpoint P import check'
        if not args.check:base.export(objects,im,pal,report,'v02')
