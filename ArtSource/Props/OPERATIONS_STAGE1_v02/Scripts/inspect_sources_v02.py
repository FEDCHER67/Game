import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
OUT=Path('C:/Dev/Game/ArtSource/Props/OPERATIONS_STAGE1_v02')
ROOT=Path('C:/Dev/Game/ArtSource')
paths={'patient':ROOT/'Characters/SAUSAGE_BUDDY_01/Patient_v01/SAUSAGE_BUDDY_PATIENT_v01.blend','table':ROOT/'Props/TABLE-ASTRA-001/TABLE-ASTRA-001.blend'}
result={}
for key,path in paths.items():
 bpy.ops.wm.open_mainfile(filepath=str(path))
 obs=[]
 for o in bpy.context.scene.objects:
  if o.type not in {'MESH','ARMATURE'} and not o.name.startswith('INC_'):continue
  rec={'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'hide_render':o.hide_render,'scale':list(o.scale)}
  if o.type=='MESH':
   o.data.calc_loop_triangles(); rec['triangles']=len(o.data.loop_triangles);rec['materials']=[m.name if m else None for m in o.data.materials]
   rec['rest_bounds']=[[min(v.co[i] for v in o.data.vertices) for i in range(3)],[max(v.co[i] for v in o.data.vertices) for i in range(3)]]
  elif o.type=='ARMATURE':rec['bones']={b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for b in o.data.bones}
  else:rec.update(world_matrix=[list(r) for r in o.matrix_world],parent_bone=o.parent_bone)
  obs.append(rec)
 mats={}
 for m in bpy.data.materials:
  p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if m.use_nodes else None
  mats[m.name]={'color':list(p.inputs['Base Color'].default_value) if p else list(m.diffuse_color),'roughness':p.inputs['Roughness'].default_value if p else .8}
 result[key]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'objects':obs,'materials':mats}
(OUT/'source_inspection_v02.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:{'objects':[{'name':o['name'],'type':o['type'],'bounds':o.get('rest_bounds'),'mats':o.get('materials')} for o in v['objects']]} for k,v in result.items()},indent=2))
