"""Collider-only revision of the accepted v03c. Run in background Blender."""
import json, math, sys, types
from pathlib import Path
import bpy, bmesh, numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
import g38_measure as M
W=B.WORK
dest=Path(sys.argv[sys.argv.index('--candidate')+1]) if '--candidate' in sys.argv else W/'colliders_v03d_01.blend'
report_path=dest.with_suffix('.json')
assert Path(bpy.data.filepath).name=='Organs_v03c.blend'
assert not dest.exists() and not report_path.exists()
bpy.context.view_layer.update()
frozen={o.name:B.snapshot(o) for o in bpy.context.scene.objects if not o.name.startswith('UCX_')}
custom={o.name:repr(dict(o.items())) for o in bpy.context.scene.objects if not o.name.startswith('UCX_')}
anatomy={o.name:M.Mesh(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('ORGAN_','VESSELS_','DIAPHRAGM','AIRWAY_'))}
for o in list(bpy.context.scene.objects):
    if o.name.startswith('UCX_'):bpy.data.objects.remove(o,do_unlink=True)
collection=bpy.data.collections.new('COL_Collision_v03d');bpy.context.scene.collection.children.link(collection)

def bm_mesh(bm):
    verts,faces=B.hull_data(bm)
    return types.SimpleNamespace(v=np.array(verts,dtype=float),t=np.array(faces,dtype=int))

def estimate_outside(bm,bone,spacing=.002):
    best=0.
    for p in M.surface_samples(bm_mesh(bm),spacing):
        d=bone.bvh.find_nearest(Vector(p))[3]
        if d>best+1e-6 and not M.inside(bone,p):best=d
    return best

def partition(costs,count,last):
    # Minimise the largest outward bulge, then total squared bulge.
    states={(0,0):(0.,0.,[])}
    for k in range(1,count+1):
        for end in range(1,last+1):
            options=[]
            for start in range(max(0,end-5),end):
                old=states.get((k-1,start))
                if old is None:continue
                value=costs[start,end]
                options.append((max(old[0],value),old[1]+value*value,old[2]+[(start,end)]))
            if options:states[k,end]=min(options,key=lambda r:(r[0],r[1]))
    return states[count,last]

build={}
for name in sorted(frozen):
    if not name.startswith('RIB_'):continue
    ob=bpy.data.objects[name];bone=M.Mesh(ob);inv=ob.matrix_world.inverted();tag=name.split('_')[1]
    assert len(ob.data.vertices)==320
    rings=[[ob.matrix_world@v.co for v in ob.data.vertices[k*10:(k+1)*10]] for k in range(32)]
    costs={}
    for a in range(31):
        for z in range(a+1,min(a+5,31)+1):
            bm=B.make_hull([p for k in range(a,z+1) for p in rings[k]])
            costs[a,z]=estimate_outside(bm,bone);bm.free()
    score,total,ranges=partition(costs,10,31)
    print('PARTITION',name,[(a,z,round(costs[a,z]*1000,3)) for a,z in ranges],flush=True)
    rows=[]
    for i,(a,z) in enumerate(ranges,1):
        bm=B.make_hull([p for k in range(a,z+1) for p in rings[k]])
        # Only UCX vertices are shaved. Both hinge poses participate in cuts.
        cuts,unresolved=B.trim_to_obstacles(bm,tag,{n:m.bvh for n,m in anatomy.items()},margin=.00315)
        part=B.create_collision(f'UCX_{name}_{i:02d}',ob,bm,inv,collection,0 if a<24 else 1)
        rows.append({'name':part.name,'first_ring':a,'last_ring':z,'coarse_max_outside_mm':costs[a,z]*1000,'cuts':cuts,'unresolved_cuts':unresolved,'vertices':len(part.data.vertices)})
    build[name]={'parts':rows,'coarse_max_outside_mm':score*1000}

for tag in ('L','R'):
    ob=bpy.data.objects['STERNUM_'+tag];inv=ob.matrix_world.inverted()
    lo,hi=B.world_bounds([ob]);rows=[];count=8
    for i in range(count):
        bm=bmesh.new();bm.from_mesh(ob.data)
        for v in bm.verts:v.co=ob.matrix_world@v.co
        B.clip_halfspace(bm,Vector((0,0,lo[2]+(hi[2]-lo[2])*i/count)),Vector((0,0,1)))
        B.clip_halfspace(bm,Vector((0,0,lo[2]+(hi[2]-lo[2])*(i+1)/count)),Vector((0,0,-1)))
        hull=B.make_hull([v.co for v in bm.verts]);bm.free()
        B.clip_halfspace(hull,Vector((.0002 if tag=='L' else -.0002,0,0)),Vector((1 if tag=='L' else -1,0,0)))
        cuts,unresolved=B.trim_to_obstacles(hull,tag,{n:m.bvh for n,m in anatomy.items()},margin=.00315)
        part=B.create_collision(f'UCX_{ob.name}_{i+1:02d}',ob,hull,inv,collection)
        rows.append({'name':part.name,'cuts':cuts,'unresolved_cuts':unresolved,'vertices':len(part.data.vertices)})
    build[ob.name]={'parts':rows}
bpy.context.view_layer.update()
after={o.name:B.snapshot(o) for o in bpy.context.scene.objects if not o.name.startswith('UCX_')}
assert frozen==after
assert custom=={o.name:repr(dict(o.items())) for o in bpy.context.scene.objects if not o.name.startswith('UCX_')}
report={'source':bpy.data.filepath,'candidate':str(dest),'render_and_non_ucx_objects_exact':True,
 'before':frozen,'after':after,'objects':build,'organ_cut_margin_mm':3.15,
 'body_neck_policy':'Accepted information only; no body/neck cuts or pass gates.'}
report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
print('COLLIDER_BUILD_DONE',str(dest),flush=True)
