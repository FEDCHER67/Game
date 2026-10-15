import bpy, json, os
from mathutils import Vector
ROOT='C:/Dev/Game/ArtSource'
files={
 'table':'Props/TABLE-ASTRA-001/TABLE-ASTRA-001.blend',
 'npc':'Characters/NPC_BASE_01/NPC_BASE_01_v09.blend',
 'syringe':'Props/SYRINGE-ASTRA-001/SYRINGE-ASTRA-001.blend',
 'scalpel':'Props/SCALPEL-ASTRA-001/SCALPEL-ASTRA-001.blend',
 'knife':'Props/SCALPEL-ASTRA-001/Variants/Tier0/KNIFE-TIER0-ASTRA-001.blend',
 'kidney':'Props/KIDNEY-ASTRA-001/KIDNEY-ASTRA-001_recolour_v01.blend',
 'liver':'Props/LIVER-ASTRA-001/LIVER-ASTRA-001_recolour_v01.blend',
}
result={}
for key,path in files.items():
 bpy.ops.wm.open_mainfile(filepath=ROOT+'/'+path)
 obs=[]
 for o in bpy.context.scene.objects:
  if o.type not in {'MESH','ARMATURE','EMPTY'}: continue
  bb=[o.matrix_world@Vector(v) for v in o.bound_box]
  info={'name':o.name,'type':o.type,'loc':list(o.location),'rot':list(o.rotation_euler),'scale':list(o.scale),'parent':o.parent.name if o.parent else None,'min':[min(v[i] for v in bb) for i in range(3)],'max':[max(v[i] for v in bb) for i in range(3)],'hidden':o.hide_render}
  if o.type=='MESH':
   o.data.calc_loop_triangles(); info.update(tris=len(o.data.loop_triangles),mats=[m.name if m else None for m in o.data.materials])
  if o.type=='ARMATURE': info['bones']={b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for b in o.data.bones}
  obs.append(info)
 mats={}
 for m in bpy.data.materials:
  p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if m.use_nodes else None
  mats[m.name]={'color':list(p.inputs['Base Color'].default_value) if p else list(m.diffuse_color),'rough':p.inputs['Roughness'].default_value if p else 0.8,'metal':p.inputs['Metallic'].default_value if p else 0,'images':[n.image.filepath for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []}
 result[key]={'path':ROOT+'/'+path,'objects':obs,'materials':mats,'unit':bpy.context.scene.unit_settings.scale_length}
out=ROOT+'/Props/OPERATIONS_STAGE1_v01/source_inspection_v01.json'
with open(out,'w') as f: json.dump(result,f,indent=2)
print('INSPECTION_SAVED',out)
