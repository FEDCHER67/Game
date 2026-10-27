import bpy,json,sys
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Dev\Game\ArtSource\Vehicles_W86')
for p in json.loads((root/'picks_v01.json').read_text()):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 if p['source'].endswith('.blend'):
  with bpy.data.libraries.load(p['source'],link=False) as (a,b):b.objects=a.objects
  for o in b.objects:
   if o and o.type=='MESH':bpy.context.collection.objects.link(o)
 else:bpy.ops.wm.obj_import(filepath=p['source'])
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 lo=Vector(tuple(min(v[i] for v in pts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in pts) for i in range(3)))
 print('INSPECT',p['name'],'objects',len(obs),'tri',sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in obs),'bbox',list(hi-lo),'mats',[(m.name,list(m.diffuse_color)) for o in obs for m in o.data.materials])
