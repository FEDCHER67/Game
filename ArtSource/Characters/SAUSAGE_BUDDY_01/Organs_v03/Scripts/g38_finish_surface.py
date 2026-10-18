"""Repair the joined render surface, preserving collision and source transforms."""
import sys,json
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
import g38_measure as M
work=B.WORK
construction=json.loads((work/'construction_latest.json').read_text())
lo,hi=map(Vector,construction['before_bounds'])
if '--adjust-left4' in sys.argv:
    part=bpy.data.objects['UCX_RIB_L_04_02'];inv=part.matrix_world.inverted()
    for v in part.data.vertices:
        p=part.matrix_world@v.co;p.x=hi.x+(p.x-hi.x)*.94;v.co=inv@p
    part.data.update()
for ob in sorted([o for o in bpy.context.scene.objects if o.name.startswith('RIB_')],key=lambda o:o.name):
    parts=sorted([o for o in bpy.context.scene.objects if o.name.startswith('UCX_') and o.parent==ob],key=lambda o:o.name)
    print('PART_GAPS',ob.name,[M.distance(M.Mesh(a),M.Mesh(b))[0]*1000 for a,b in zip(parts,parts[1:])],flush=True)
    mats=list(ob.data.materials)
    verts=[];faces=[];indices=[]
    for part in parts:
        off=len(verts);verts.extend(v.co[:] for v in part.data.vertices)
        faces.extend([off+i for i in p.vertices] for p in part.data.polygons)
        indices.extend([part['part_material_index']]*len(part.data.polygons))
    me=bpy.data.meshes.new(ob.name+'_v03b_surface');me.from_pydata(verts,[],faces);me.update()
    for m in mats:me.materials.append(m)
    for p,i in zip(me.polygons,indices):p.material_index=i
    surface=BVHTree.FromPolygons(verts,faces)
    ob.data=me
    mod=ob.modifiers.new('G38_voxel_union','REMESH');mod.mode='VOXEL';mod.voxel_size=.0004;mod.use_smooth_shade=True
    if hasattr(mod,'use_remove_disconnected'):mod.use_remove_disconnected=False
    with bpy.context.temp_override(object=ob,active_object=ob,selected_objects=[ob]):bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.data.materials.clear()
    for m in mats:ob.data.materials.append(m)
    for p in ob.data.polygons:
        center=sum((ob.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
        p.material_index=indices[surface.find_nearest(center)[2]]
    B.L.decimate_object(ob,480/B.L.tris(ob))
    inv=ob.matrix_world.inverted()
    for v in ob.data.vertices:
        p=ob.matrix_world@v.co
        for i in range(3):p[i]=max(lo[i],min(hi[i],p[i]))
        v.co=inv@p
    for p in ob.data.polygons:p.use_smooth=True
    ob.data.update()
    bm=bmesh.new();bm.from_mesh(ob.data);ob['mass_kg']=round(abs(bm.calc_volume(signed=True))*1100,4);bm.free()
    h=M.mesh_health(ob);print('SURFACE',ob.name,h,flush=True)
    assert h['nonmanifold_edges']==0 and h['components']==1
    construction['build'][ob.name]['mass_kg']=ob['mass_kg']
ribverts=[(o,v,o.matrix_world@v.co) for o in bpy.context.scene.objects if o.name.startswith('RIB_') for v in o.data.vertices]
for axis in range(3):
    for target in (lo[axis],hi[axis]):
        ob,v,p=min(ribverts,key=lambda row:abs(row[2][axis]-target))
        if abs(p[axis]-target)<.0001:
            p[axis]=target;v.co=ob.matrix_world.inverted()@p
construction['after_bounds']=B.world_bounds([o for o in bpy.context.scene.objects if o.name.startswith(('RIB_','STERNUM_'))])
construction['rib_sternum_triangles']=sum(B.L.tris(o) for o in bpy.context.scene.objects if o.name.startswith(('RIB_','STERNUM_')))
(work/'construction_final.json').write_text(json.dumps(construction,indent=2))
dest=work/'ribcage_candidate19.blend';assert not dest.exists()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
