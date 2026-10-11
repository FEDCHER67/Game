import bpy,bmesh,math,json,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\PAN-ASTRA-001')
OUT=ROOT/'PAN_ASTRA_001_v03.blend'
assert not OUT.exists()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\pan_tripo_base.fbx')
handle=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=handle
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
handle.data.calc_loop_triangles();source_tri=len(handle.data.loop_triangles)
raw=handle.copy();raw.data=handle.data.copy();raw.name='Tripo_original_reference'
reference=bpy.data.collections.new('REFERENCE_Tripo_source_not_exported');bpy.context.scene.collection.children.link(reference);reference.objects.link(raw);reference.hide_render=True;reference.hide_viewport=True
# Preserve the source grip and its through hole. Close only the cut casting base.
bm=bmesh.new();bm.from_mesh(handle.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,.60),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
boundary=[e for e in bm.edges if e.is_boundary];bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(handle.data);bm.free()
handle.data.calc_loop_triangles();m=handle.modifiers.new('Grip_budget','DECIMATE');m.ratio=140/len(handle.data.loop_triangles);bpy.ops.object.modifier_apply(modifier=m.name)
for v in handle.data.vertices:v.co*=.46
grip_hi=max(v.co.z for v in handle.data.vertices)
for v in handle.data.vertices:v.co.z=.276+(v.co.z-.276)*(.46-.276)/(grip_hi-.276)
for v in raw.data.vertices:v.co*=.46
# A rotational profile: every ring has constant Y; rim and floor are parallel.
# 45mm usable depth, 50mm exterior depth, with a 5mm thick floor.
bm=bmesh.new();loops=[];n=24;zc=.145
profile=[(.125,.025),(.140,.025),(.145,.016),(.145,-.025),(.136,-.025),(.120,.020)]
for radius,y in profile:
 loops.append([bm.verts.new((radius*math.cos(k*2*math.pi/n),y,zc+radius*math.sin(k*2*math.pi/n))) for k in range(n)])
for a,b in zip(loops,loops[1:]):
 for k in range(n):bm.faces.new((a[k],a[(k+1)%n],b[(k+1)%n],b[k]))
dent_source=(-.0368,.1082);floor_reports=[]
for outer,baseline in [(loops[0],.025),(loops[-1],.020)]:
 cx,cz=dent_source;prev=sorted(outer,key=lambda v:math.atan2(v.co.z-cz,v.co.x-cx));start=math.atan2(prev[0].co.z-cz,prev[0].co.x-cx)
 prev_angles=[math.atan2(v.co.z-cz,v.co.x-cx)-start for v in prev]
 for radius,depth in [(.040,0),(.021,.0045)]:
  angles=[k*2*math.pi/12 for k in range(12)]
  loop=[bm.verts.new((cx+radius*math.cos(ang+start),baseline+depth,cz+radius*math.sin(ang+start))) for ang in angles]
  i=j=0
  while i<len(prev) or j<len(loop):
   ai=prev_angles[i+1] if i+1<len(prev) else 2*math.pi;aj=angles[j+1] if j+1<len(loop) else 2*math.pi
   if i<len(prev) and (j==len(loop) or ai<=aj):bm.faces.new((prev[i%len(prev)],prev[(i+1)%len(prev)],loop[j%len(loop)]));i+=1
   else:bm.faces.new((prev[i%len(prev)],loop[(j+1)%len(loop)],loop[j%len(loop)]));j+=1
  prev=loop;prev_angles=angles
 centre=bm.verts.new((cx,baseline+.008,cz))
 for k in range(len(prev)):bm.faces.new((prev[k],prev[(k+1)%len(prev)],centre))
 floor_reports.append({'baseline_y':baseline,'dent_depth_m':.008})
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));mesh=bpy.data.meshes.new('Regular_rotational_bowl');bm.to_mesh(mesh);bm.free()
obj=bpy.data.objects.new('Item_Pan',mesh);bpy.context.scene.collection.objects.link(obj)
for o in bpy.context.selected_objects:o.select_set(False)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
m=obj.modifiers.new('Join_source_grip','BOOLEAN');m.operation='UNION';m.solver='EXACT';m.object=handle;bpy.ops.object.modifier_apply(modifier=m.name)
bpy.data.objects.remove(handle,do_unlink=True)
me=obj.data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
me.calc_loop_triangles();restored_tri=len(me.loop_triangles);scale=1.;lo=0.
print('V03_GEOMETRY_TRIANGLES',restored_tri)
# Reuse the verified material/export/render/validation stage from v02.
s=(ROOT/'Scripts/polish_v02.py').read_text();s=s[s.index('me.update();bpy.context.view_layer.update()'):]
s=s.replace('_v02','_v03').replace('.027*scale*.8','.008').replace('source mesh; floor fan replacement by connected local rings, front-left dent and corresponding exterior bulge restored; local decimation outside protected dent loops; depth compressed20percent','source grip retained; regular circular rotational bowl with constant depth and coplanar rim; matching local interior dent/exterior bulge')
exec(compile(s,str(ROOT/'Scripts/build_cup_v03.py'),'exec'))
