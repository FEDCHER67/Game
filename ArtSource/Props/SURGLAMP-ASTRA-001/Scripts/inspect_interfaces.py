import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\surglamp_tripo_base.fbx')
o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);parts=[]
while remaining:
 vs={remaining.pop()};stack=list(vs)
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);vs.add(w);stack.append(w)
 parts.append(vs)
parts.sort(key=len,reverse=True);main,head=parts[:2]
out={'shaft_slices':[]}
for z in [.06,.08,.12,.2,.4,.6,.8,.845,.86]:
 vs=[v for v in main if abs(v.co.z-z)<.02]
 out['shaft_slices'].append({'z':z,'n':len(vs),'mean':[sum(v.co[i] for v in vs)/len(vs) for i in range(3)] if vs else None,'x_range':[min(v.co.x for v in vs),max(v.co.x for v in vs)] if vs else None,'y_range':[min(v.co.y for v in vs),max(v.co.y for v in vs)] if vs else None})
pts=np.array([v.co[:] for v in head]);centre=pts.mean(axis=0);evals,axes=np.linalg.eigh(np.cov(pts.T));n=axes[:,0];n*=1 if n[1]<0 else -1;pr=(pts-centre)@n
faces={f for v in head for f in v.link_faces};out['head_axis']=n.tolist();out['head_center']=centre.tolist();out['head_depth_range']=[float(pr.min()),float(pr.max())]
out['largest_head_faces']=[{'area':f.calc_area(),'center':list(f.calc_center_median()),'normal':list(f.normal),'axis_dot':float(np.array(f.normal[:])@n),'projection':float((np.array(f.calc_center_median()[:])-centre)@n)} for f in sorted(faces,key=lambda f:f.calc_area(),reverse=True)[:15]]
(ROOT/'Validation/source_interfaces.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
