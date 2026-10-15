import bpy,bmesh,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/Dev/Game/ArtSource/Props/OPERATIONS_STAGE1_v02/Operations_PATIENT_draft01.blend')
o=bpy.data.objects['REF_PATIENT_NORMAL_Body']
bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();comps=[]
for v in bm.verts:
 if v.index in seen:continue
 todo=[v];idx=[];seen.add(v.index)
 while todo:
  vv=todo.pop();idx.append(vv.index)
  for e in vv.link_edges:
   w=e.other_vert(vv)
   if w.index not in seen:seen.add(w.index);todo.append(w)
 comps.append({'verts':len(idx),'bounds':[[min(bm.verts[i].co[j] for i in idx) for j in range(3)],[max(bm.verts[i].co[j] for i in idx) for j in range(3)]]})
print('COMPONENTS',json.dumps(comps))
for n in ['INC_KIDNEY_L','INC_KIDNEY_R','INC_LIVER','INCISION_KIDNEY_L_OPENING','INCISION_KIDNEY_R_OPENING','INCISION_LIVER_OPENING']:
 ob=bpy.data.objects[n];print(n,'WORLD',[list(row) for row in ob.matrix_world])
 if ob.type=='MESH':print('LOCAL_Z',min(v.co.z for v in ob.data.vertices),max(v.co.z for v in ob.data.vertices))
