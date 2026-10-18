"""Actual Blender wireframe renders in a disposable process; never save scene."""
import sys,types,math
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
R=types.ModuleType('g38_render');R.__file__=str(HERE/'render_review_v03.py')
src=Path(R.__file__).read_text(encoding='utf-8');exec(compile(src[:src.rfind('\nmain()')],R.__file__,'exec'),R.__dict__)
R.OUT=B.REVIEW/'G38_v03d_tiles';R.OUT.mkdir(exist_ok=True);R.ONLY=None
sc=bpy.context.scene;cam=R.setup()
for o in sc.objects:
    if o.type not in ('CAMERA','LIGHT'):o.hide_render=True
bones=[o for o in sc.objects if o.name.startswith(('RIB_','STERNUM_','SPINE_'))]
ghost=R.flat_mat('G38_v03d_review_bone',(.77,.83,.85),alpha=.30)
for o in bones:
    o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(ghost);o.hide_render=False
wiremat=R.flat_mat('G38_v03d_wire',(.015,.25,.10),rough=.35)
for o in list(sc.objects):
    if not o.name.startswith('UCX_'):continue
    cu=bpy.data.curves.new(o.name+'_wire','CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=.00010;cu.bevel_resolution=0
    for edge in o.data.edges:
        sp=cu.splines.new('POLY');sp.points.add(1)
        for p,idx in zip(sp.points,edge.vertices):p.co=(*o.data.vertices[idx].co,1)
    wo=bpy.data.objects.new(cu.name,cu);sc.collection.objects.link(wo);wo.parent=o.parent
    wo.matrix_parent_inverse=Matrix.Identity(4);wo.matrix_basis=Matrix.Identity(4);cu.materials.append(wiremat)
R.shoot(cam,'20_colliders_front',(0,-.8,1.09),(0,0,1.09),ortho=.34,res=(1200,1000))
R.shoot(cam,'21_colliders_side',(.8,-.015,1.09),(0,-.015,1.09),ortho=.285,res=(1200,1000))
for tag,angle in [('L',35),('R',-35)]:bpy.data.objects['RIBCAGE_HALF_'+tag].rotation_euler.y=math.radians(angle)
bpy.context.view_layer.update()
R.shoot(cam,'22_colliders_open35_front',(0,-.8,1.09),(0,0,1.09),ortho=.49,res=(1200,1000))
R.shoot(cam,'23_colliders_open35_side',(.8,-.015,1.09),(0,-.015,1.09),ortho=.35,res=(1200,1000))
print('V03D_WIREFRAME_RENDERS_DONE',flush=True)
