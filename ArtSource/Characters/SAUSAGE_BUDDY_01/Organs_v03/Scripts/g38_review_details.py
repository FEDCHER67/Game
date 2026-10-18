"""Disposable Blender renders: collision overlays and fixed-neck trim study."""
import sys,types,math
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
R=types.ModuleType('g38_review_helpers');R.__file__=str(HERE/'render_review_v03.py')
src=Path(R.__file__).read_text(encoding='utf-8');exec(compile(src[:src.rfind('\nmain()')],R.__file__,'exec'),R.__dict__)
R.OUT=Path(sys.argv[sys.argv.index('--out')+1]) if '--out' in sys.argv else B.REVIEW/'G38_tiles';R.OUT.mkdir(exist_ok=True);R.ONLY=None
sc=bpy.context.scene;cam=R.setup()
for o in sc.objects:
    if o.type not in ('CAMERA','LIGHT'):o.hide_render=True
bone=[o for o in sc.objects if o.name.startswith(('RIB_','STERNUM_','SPINE_'))]
ghost=R.flat_mat('G38_review_ghost_bone',(.77,.83,.85),alpha=.30)
for o in bone:
    o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(ghost);o.hide_render=False
wiremat=R.flat_mat('G38_review_wire',(.015,.25,.10),rough=.35)
wires=[]
for o in list(sc.objects):
    if not o.name.startswith('UCX_'):continue
    cu=bpy.data.curves.new(o.name+'_review_wire','CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=.00015;cu.bevel_resolution=0
    for edge in o.data.edges:
        sp=cu.splines.new('POLY');sp.points.add(1)
        for p,idx in zip(sp.points,edge.vertices):p.co=(*(o.matrix_world@o.data.vertices[idx].co),1)
    wo=bpy.data.objects.new(cu.name,cu);sc.collection.objects.link(wo);cu.materials.append(wiremat);wires.append(wo)
R.shoot(cam,'20_colliders_front',(0,-.8,1.09),(0,0,1.09),ortho=.34,res=(1200,1000))
R.shoot(cam,'21_colliders_side',(.8,-.015,1.09),(0,-.015,1.09),ortho=.285,res=(1200,1000))
for o in bone+wires:o.hide_render=True
# Exact fixed head/neck island, displayed translucent only in this disposable scene.
body=bpy.data.objects['REF_PatientBody_v02_rest'];bm=bmesh.new();bm.from_mesh(body.data)
seen=set();components=[]
for v in bm.verts:
    if v in seen:continue
    comp={v};stack=[v];seen.add(v)
    while stack:
        p=stack.pop()
        for e in p.link_edges:
            q=e.other_vert(p)
            if q not in seen:seen.add(q);comp.add(q);stack.append(q)
    if len(comp)>400:components.append(comp)
head=min(components,key=len)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v not in head],context='VERTS')
me=bpy.data.meshes.new('G38_review_fixed_head');bm.to_mesh(me);bm.free()
headob=bpy.data.objects.new(me.name,me);sc.collection.objects.link(headob);headob.matrix_world=body.matrix_world
me.materials.append(R.flat_mat('G38_review_fixed_head_material',(.55,.24,.12),alpha=.22))
original=B.OUT/'Organs_v03.blend'
sterns,_=R.append(original,lambda n:n.startswith('STERNUM_'))
source_sterns=list(sterns.values())
for o in source_sterns:o.hide_render=False
R.shoot(cam,'22_neck_before_front',(0,-.55,1.135),(0,-.06,1.135),ortho=.185,res=(900,900))
R.shoot(cam,'23_neck_before_side',(.55,-.075,1.135),(0,-.075,1.135),ortho=.185,res=(900,900))
for o in source_sterns:o.hide_render=True
# Authorised upper-end trim study only; do not save it into the deliverable.
for o in source_sterns:
    new=o.copy();new.data=o.data.copy();sc.collection.objects.link(new);new.hide_render=False
    mesh=bmesh.new();mesh.from_mesh(new.data)
    mw=new.matrix_world.copy();inv=mw.inverted()
    for v in mesh.verts:v.co=mw@v.co
    B.clip_halfspace(mesh,Vector((0,0,1.094)),Vector((0,0,-1)))
    for v in mesh.verts:v.co=inv@v.co
    mesh.to_mesh(new.data);mesh.free()
R.shoot(cam,'24_neck_trim_study_front',(0,-.55,1.135),(0,-.06,1.135),ortho=.185,res=(900,900))
R.shoot(cam,'25_neck_trim_study_side',(.55,-.075,1.135),(0,-.075,1.135),ortho=.185,res=(900,900))
print('G38_DETAIL_RENDERS_DONE',flush=True)
