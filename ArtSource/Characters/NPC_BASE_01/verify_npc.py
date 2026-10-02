"""Validate the current unrigged model and FBX, including rebuilt topology."""
import bpy, bmesh, json, math, argparse, sys, re
from pathlib import Path
folder=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='Validate an unrigged NPC revision; default is the latest unrigged revision.')
parser.add_argument('--revision',type=int)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
versions=[int(m.group(1)) for p in folder.glob('NPC_BASE_01_v*.blend') if (m:=re.fullmatch(r'NPC_BASE_01_v(\d+)\.blend',p.name))]
versions=[v for v in versions if (r:=folder/f'validation_v{v:02d}.json').exists() and json.loads(r.read_text()).get('bones')==0]
revision=args.revision if args.revision is not None else max(versions,default=0)
if revision<2:parser.error('No numbered revision found; build the model first or provide --revision N.')
stem=f'NPC_BASE_01_v{revision:02d}'
report_path=folder/f'validation_v{revision:02d}.json'
report=json.loads(report_path.read_text())
if report.get('bones')!=0:parser.error('This revision has a rig. Use verify_rig.py -- --revision N.')
bpy.ops.wm.open_mainfile(filepath=str(folder/f'{stem}.blend'))
assert bpy.context.scene.get('npc_asset_revision')==stem==report['revision']
meshes=[o for o in bpy.data.collections['NPC_BASE_01'].objects if o.type=='MESH']
assert len(meshes)==6 and report['total_triangles']<17000
assert not bpy.data.armatures
assert all(not o.vertex_groups and not o.modifiers for o in meshes)
assert all(o.data.uv_layers for o in meshes)
assert all(k.value==0 for k in bpy.data.objects['Face_Expressions'].data.shape_keys.key_blocks)
surface={}
for obj in meshes:
 obj.data.calc_loop_triangles()
 assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
 assert all(t.area>1e-12 for t in obj.data.loop_triangles),obj.name
 if obj.name in ['Outfit_TShirt','Outfit_Shorts','Body_Base']:
  bm=bmesh.new();bm.from_mesh(obj.data)
  assert all(len(e.link_faces) in (1,2) for e in bm.edges),obj.name
  assert all(e.is_contiguous for e in bm.edges if len(e.link_faces)==2),obj.name
  remaining={v for e in bm.edges if e.is_boundary for v in e.verts};loops=0
  while remaining:
   loops+=1;stack=[remaining.pop()]
   while stack:
    v=stack.pop();edges=[e for e in v.link_edges if e.is_boundary]
    assert len(edges)==2
    for e in edges:
     other=e.other_vert(v)
     if other in remaining:remaining.remove(other);stack.append(other)
  assert loops=={'Outfit_TShirt':4,'Outfit_Shorts':3,'Body_Base':0}[obj.name],(obj.name,loops)
  remaining=set(bm.verts);components=0
  while remaining:
   components+=1;stack=[remaining.pop()]
   while stack:
    v=stack.pop()
    for e in v.link_edges:
     other=e.other_vert(v)
     if other in remaining:remaining.remove(other);stack.append(other)
  if obj.name!='Body_Base':assert components==1
  surface[obj.name]={'opening_loops':loops,'components':components,'consistent_winding':True}
  bm.free()
body=bpy.data.objects['Body_Base']
legs=[v.co for v in body.data.vertices if .24<v.co.z<.59]
assert legs and all(abs(math.hypot(abs(v.x)-.089,v.y)-.037)<1e-5 for v in legs)
neck=[v.co for v in body.data.vertices if 1.25<v.co.z<1.38]
assert neck and all(abs(math.hypot(v.x,v.y)-.12)<1e-5 for v in neck)
report['source_reopen']='PASS: no armature, skinning or vertex groups; UVs, neutral face, finite nondegenerate geometry'
report['surface_topology']=surface
report['requested_forms']='PASS: cylindrical legs and circular constant-radius head/neck'

# Check triangle crossings in the static source, not just manifold connectivity.
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
def geometry(obj):
 obj.data.calc_loop_triangles()
 vertices=[v.co.copy() for v in obj.data.vertices]
 tris=[tuple(t.vertices) for t in obj.data.loop_triangles]
 return vertices,tris,BVHTree.FromPolygons(vertices,tris,all_triangles=True)
def crosses(a,b):
 for source,target in [(a,b),(b,a)]:
  for i in range(3):
   start=source[i];delta=source[(i+1)%3]-start
   hit=intersect_ray_tri(*target,delta,start,True)
   if hit is not None and delta.length_squared>1e-16:
    t=(hit-start).dot(delta)/delta.length_squared
    if 1e-5<t<1-1e-5:return True
 return False
names=['Body_Base','Outfit_TShirt','Outfit_Shorts']
geo={name:geometry(bpy.data.objects[name]) for name in names}
checks={}
for name_a,name_b in [('Body_Base','Outfit_TShirt'),('Body_Base','Outfit_Shorts'),('Outfit_TShirt','Outfit_Shorts'),('Outfit_TShirt','Outfit_TShirt'),('Outfit_Shorts','Outfit_Shorts')]:
 va,ta,ba=geo[name_a];vb,tb,bb=geo[name_b];hits=[]
 for i,j in ba.overlap(bb):
  if name_a==name_b and (i>=j or set(ta[i])&set(tb[j])):continue
  a=[va[k] for k in ta[i]];b=[vb[k] for k in tb[j]]
  if crosses(a,b):hits.append([round(sum(p[k] for p in a+b)/6,4) for k in range(3)])
 checks[name_a+' / '+name_b]=len(hits)
 if hits:print('SURFACE_CROSSINGS',name_a,name_b,len(hits),hits[:12])
assert not any(checks.values()),checks
report['static_surface_crossings']=checks
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(folder/f'{stem}.fbx'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert len(meshes)==6 and not bpy.data.armatures
keys=set();triangles=0;points=[]
for obj in meshes:
 assert not obj.vertex_groups and not obj.modifiers
 obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
 points.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
 if obj.data.shape_keys:keys.update(k.name for k in obj.data.shape_keys.key_blocks)
assert {'Blink','Happy','Worried','Surprised'}.issubset(keys)
assert triangles==report['total_triangles']
dimensions=[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]
assert abs(dimensions[2]-1.742)<.01
report['fbx_roundtrip']={'status':'PASS','meshes':6,'bones':0,'triangles':triangles,'dimensions_m':dimensions,'shape_keys':sorted(keys)}
report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VALIDATION_PASS '+json.dumps(report))
