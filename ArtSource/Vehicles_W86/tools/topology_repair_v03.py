import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Vehicles_W86')

def repair(me):
 bm=bmesh.new();bm.from_mesh(me)
 bad=[f for f in bm.faces if f.calc_area()<1e-10]
 if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
 # Partition coincident closed shells by vertex fans instead of welding their contacts into 4-face edges.
 bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table();bm.normal_update()
 uv=bm.loops.layers.uv.active;verts=[];faceverts={};fuv={}
 for f in bm.faces:
  if uv:fuv[f.index]=[tuple(l[uv].uv) for l in f.loops]
 for v in bm.verts:
  pending=set(v.link_faces)
  while pending:
   seed=pending.pop();fan={seed};stack=[seed]
   while stack:
    f=stack.pop()
    for e in f.edges:
     if v in e.verts and len(e.link_faces)==2:
      for nf in e.link_faces:
       if nf in pending:pending.remove(nf);fan.add(nf);stack.append(nf)
   idx=len(verts);verts.append(tuple(v.co))
   for f in fan:faceverts[(f.index,v.index)]=idx
 faces=[[faceverts[(f.index,v.index)] for v in f.verts] for f in bm.faces];oldidx=[f.index for f in bm.faces]
 bm.free();new=bpy.data.meshes.new(me.name+'_Repaired');new.from_pydata(verts,[],faces);new.update();new.materials.append(me.materials[0]);layer=new.uv_layers.new()
 for f,oi in zip(new.polygons,oldidx):
  for k,li in enumerate(f.loop_indices):layer.data[li].uv=fuv[oi][k]
 # Any remaining short boundary loop is an original small source defect; close it with the local face palette.
 bm=bmesh.new();bm.from_mesh(new);boundary=[e for e in bm.edges if e.is_boundary]
 if boundary:
  res=bmesh.ops.holes_fill(bm,edges=boundary,sides=8)
  uv=bm.loops.layers.uv.active
  for f in res.get('faces',[]):
   near=next((nf for e in f.edges for nf in e.link_faces if nf!=f and nf not in res.get('faces',[])),None)
   if near and uv:
    u=near.loops[0][uv].uv.copy()
    for l in f.loops:l[uv].uv=u
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(new);bm.free();return new

if __name__=='__main__':
 for p in json.loads((ROOT/'selected_models_v01.json').read_text()):
  rev=2 if p['name']=='ASTRA_STATIC_VAN' else 1
  bpy.ops.wm.open_mainfile(filepath=str(Path(p['folder'])/(p['name']+f'_v{rev:02}.blend')))
  o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD0'));o.data=repair(o.data);bm=bmesh.new();bm.from_mesh(o.data);print('REPAIR',p['name'],len(bm.faces),sum(e.is_boundary for e in bm.edges),sum(not e.is_manifold for e in bm.edges),sum(f.calc_area()<1e-10 for f in bm.faces));bm.free()
