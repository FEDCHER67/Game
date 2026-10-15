"""G23 Pine_Tall: original sparse mountain-pine geometry, Blender approval stage only."""
import bpy,bmesh,ast,math,random,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;BLEND=ROOT/'Cozy_PineTall_v01.blend'
assert not BLEND.exists(),'Preserve previous deliverable; number a new revision'
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
def coll(n,parent=None):
    c=bpy.data.collections.new(n);(parent.children if parent else scene.collection.children).link(c);return c
project=coll('COL_Project');geo=coll('COL_Geo',project);refs=coll('COL_Reference',project);collision=coll('COL_Collision',project);preview=coll('COL_Preview',project)
def linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
def rgba(h):return tuple(linear(int(h[i:i+2],16)/255) for i in (1,3,5))+(1,)
PALETTE={'Bark':'#76503E','LeafDark':'#3A6E38','LeafPine':'#2C6042'}
MATS=[]
for name,color in PALETTE.items():
    m=bpy.data.materials.new('MAT_'+name+'_pine_tall_v01');m.use_nodes=True;m.diffuse_color=rgba(color)
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=rgba(color);bs.inputs['Roughness'].default_value=.84;MATS.append(m)
tree=ast.parse((ROOT.parent/'v04/build_leafy_v04_03.py').read_text());helper=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
exec(compile(ast.Module(body=[helper],type_ignores=[]),'approved_folded_frond_mesh_helper','exec'))
SPECS=[dict(id='PineTall_A',family='PineTall',variant=0,height=18.5,width=4.5,seed=235101,lean=[.22,-.12],arms=[3,4,3,4,3,3,3,2],stubs=5),
       dict(id='PineTall_B',family='PineTall',variant=1,height=20,width=4.9,seed=235238,lean=[-.40,.18],arms=[4,3,4,3,4,3,3,3],stubs=7),
       dict(id='PineTall_C',family='PineTall',variant=2,height=17,width=4.2,seed=235375,lean=[.30,.24],arms=[3,3,4,3,3,4,2,2],stubs=4)]

def build(s,lod):
    rng=random.Random(s['seed']);h=s['height'];w=s['width'];b=Mesh();base_radius=[.26,.29,.245][s['variant']];lean=Vector((*s['lean'],0))
    def trunk(z):return Vector((0,0,z))+lean*(z/h)+Vector((.055*math.sin(z/h*math.pi),.025*math.sin(z/h*math.tau),0))
    b.tube([trunk(h*k/10) for k in range(11)],[base_radius*(1-k/10)**.9+.018 for k in range(11)],(9,7,5)[lod])
    for k in range(5):
        a=k*math.tau/5+.45;start=Vector((math.cos(a)*base_radius*1.7,math.sin(a)*base_radius*1.7,.025));end=trunk(h*.035)
        b.tube([start,start.lerp(end,.5),end],[base_radius*.17,base_radius*.33,base_radius*.58],(5,4,3)[lod])
    stubs=[]
    for k in range(s['stubs']):
        q=.14+.19*(k+.5)/s['stubs'];a=k*2.399+s['variant']*.8;start=trunk(h*q);direction=Vector((math.cos(a),math.sin(a),rng.uniform(-.35,.15))).normalized();length=rng.uniform(.28,.65)
        mid=start+direction*length*.7;end=start+direction*length+Vector((0,0,.055));radius=base_radius*rng.uniform(.20,.31)
        b.tube([start,mid,end],[radius,radius*.58,.018],(5,4,3)[lod]);stubs.append(dict(base=list(start),tip=list(end)))
    clumps=[];branches=[]
    levels=[.375,.46,.545,.63,.715,.79,.865,.93]
    for tier,(q,n) in enumerate(zip(levels,s['arms'])):
        phase=tier*1.27+s['variant']*.61
        for j in range(n):
            a=j*math.tau/n+phase+rng.uniform(-.35,.35);z=h*q+rng.uniform(-.37,.37)
            outward=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0));start=trunk(z)
            taper=max(.14,1-(q-.37)/.72);length=w*.34*taper*rng.uniform(.72,1.13)
            # Exposed horizontal branch, mildly sagging elbow and a lifted terminal twig.
            mid=start+outward*length*.55+Vector((0,0,-.16*(1-q)))
            tip=start+outward*length+Vector((0,0,rng.uniform(.08,.33)))
            br=base_radius*(.30*(1-q)+.12);b.tube([start,mid,tip],[br,br*.64,.022],(5,4,3)[lod]);branches.append(dict(tier=tier,base=list(start),tip=list(tip)))
            scale=rng.uniform(.80,1.13)*(1-.40*max(0,(q-.62)/.38))
            clumps.append(dict(center=tip+outward*.12,direction=(outward+Vector((0,0,.45))).normalized(),size=scale,seed=s['seed']+len(clumps)*73))
            end=mid.lerp(tip,.7)+side*rng.choice([-1,1])*w*.09*scale+Vector((0,0,rng.uniform(-.02,.22)))
            b.tube([mid,end.lerp(mid,.35)+Vector((0,0,.08)),end],[br*.55,.025,.009],(4,3,3)[lod])
            clumps.append(dict(center=end,direction=(outward+side*.4+Vector((0,0,.4))).normalized(),size=scale*.88,seed=s['seed']+len(clumps)*73))
            if tier<5 and j==s['variant']%n:
                ep=tip+side*w*.08+Vector((0,0,-.22));b.tube([tip,ep],[.025,.008],3)
                clumps.append(dict(center=ep,direction=(outward-side*.5+Vector((0,0,.2))).normalized(),size=scale*.72,seed=s['seed']+len(clumps)*73))
    for q,size in [(.96,.48),(.985,.35),(1,.21)]:clumps.append(dict(center=trunk(h*q),direction=Vector((0,0,1)),size=size,seed=s['seed']+len(clumps)*73))
    for c in clumps:
        cr=random.Random(c['seed']);axis=c['direction'];side=axis.cross(Vector((0,1,0))).normalized();up=axis.cross(side).normalized();size=c['size']
        for k in range(11):
            a=k*2.399+cr.uniform(-.35,.35);direction=(axis*cr.uniform(.35,.90)+side*math.cos(a)+up*math.sin(a)*.72).normalized()
            center=c['center']+side*cr.uniform(-.12,.12)*size+up*cr.uniform(-.12,.12)*size+axis*cr.uniform(-.15,.17)*size
            length=cr.uniform(.72,1.12)*size;width=length*cr.uniform(.28,.43);roll=cr.uniform(-.65,.65);mat=2 if cr.random()<.80 else 1
            if k%(1,2,3)[lod]:continue
            b.leaf(center-direction*length*.43,direction,length*(1,1.12,1.24)[lod],width*(1,1.18,1.34)[lod],roll,mat,shape='palm')
    # Base pivot and intended world envelope, derived consistently for each LOD.
    ids={i for f,m in zip(b.f,b.m) if m>0 for i in f};extent=max(max(b.v[i][k] for i in ids)-min(b.v[i][k] for i in ids) for k in (0,1))
    xy=w/extent;low=min(p[2] for p in b.v);high=max(p[2] for p in b.v);zs=h/(high-low)
    def mapped(p):return Vector((p[0]*xy,p[1]*xy,(p[2]-low)*zs))
    b.v=[tuple(mapped(p)) for p in b.v]
    caps=[]
    for lo,hi,rad in [(0,.34,base_radius+.018),(.34,.76,base_radius*.72)]:
        a=mapped(trunk(h*lo));z=mapped(trunk(h*hi));axis=(z-a).normalized();center=(a+z)/2;radius=rad*xy
        caps.append(dict(type='Capsule',radius_m=radius,height_m=(z-a).length+2*radius,center_Blender=list(center),axis_Blender=list(axis),center_Unity=[center.x,center.z,center.y],axis_Unity=[axis.x,axis.z,axis.y]))
    meta=dict(clusters=len(clumps),mainBranches=len(branches),deadStubs=len(stubs),bareTrunkFraction=.34,colliders=caps,xyNormalization=xy,zNormalization=zs)
    return b,meta

models={};rows=[]
for s in SPECS:
    col=coll('COL_'+s['id'],geo)
    for lod in range(3):
        b,meta=build(s,lod);ob=b.object(f'SM_{s["id"]}_v01_LOD{lod}',col);models[s['id'],lod]=ob;ob.hide_render=True;ob.hide_set(True)
        ob['height_m']=s['height'];ob['crown_width_m']=s['width'];ob['wind']='Existing shared GenericFoliageScaled / stiff material settings; no per-model code'
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not v.link_edges for v in bm.verts);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons);assert tris<=8000 and bad==loose==deg==0,(s['id'],lod,tris,bad,loose,deg)
        dims=[max(v.co[k] for v in ob.data.vertices)-min(v.co[k] for v in ob.data.vertices) for k in range(3)]
        assert abs(min(v.co.z for v in ob.data.vertices))<.001 and abs(dims[2]-s['height'])<.001
        rows.append(dict(id=s['id'],lod=lod,triangles=tris,height=s['height'],crownWidth=s['width'],dimensions=dims,nonmanifold=bad,loose=loose,degenerate=deg,clusters=meta['clusters'],mainBranches=meta['mainBranches'],deadStubs=meta['deadStubs'],materials=[m.name for m in ob.data.materials]))
        if lod==0:s.update(meta)
        print('VALIDATED',s['id'],'LOD',lod,tris,'triangles',flush=True)
    # Visible wire capsule proxies accompany exact Unity primitive recipes (not exported as render geometry).
    for ci,cap in enumerate(s['colliders']):
        radius=cap['radius_m'];half=cap['height_m']/2-radius;mb=Mesh();points=[];radii=[]
        for j in range(1,6):
            angle=-math.pi/2+j*math.pi/10;points.append((0,0,-half+radius*math.sin(angle)));radii.append(radius*math.cos(angle))
        for j in range(5):
            angle=j*math.pi/10;points.append((0,0,half+radius*math.sin(angle)));radii.append(radius*math.cos(angle))
        mb.tube(points,radii,12);proxy=mb.object(f'COL_{s["id"]}_Trunk_{ci+1}_v01',collision);proxy.location=cap['center_Blender'];proxy.rotation_mode='QUATERNION';proxy.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(cap['axis_Blender']));proxy.display_type='WIRE';proxy.hide_render=True;proxy.hide_set(True)
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[s['id'],lod].hide_set(False);models[s['id'],lod].select_set(True)
    bpy.context.view_layer.objects.active=models[s['id'],0];path=ROOT/'Models'/f'{s["id"]}_v01.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[s['id'],lod].hide_set(True)
scene['Status']='Pine_Tall v01: approval candidate, no map placement';scene['Reference']='ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png'
(ROOT/'validation_v01.json').write_text(json.dumps(dict(variants=SPECS,lods=rows,palette=PALETTE,units='metres',reference=scene['Reference'],windShader='OnlyVolunteers/Wind/v03/GenericFoliageScaled',stage='Blender only; await Fedya approval'),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));print('PINE_TALL_V01_COMPLETE',flush=True)
