import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
r=R.ROOT;stats=json.loads((r/'selected_models_v01.json').read_text())
for p in stats:
 name=p['name']
 if name not in ['DUMP_TRUCK','CONTAINER_TRUCK','PANEL_VAN']:continue
 folder=Path(p['folder']);rev=p['revision'];bpy.ops.wm.open_mainfile(filepath=str(folder/(name+f'_v{rev:02}.blend')));lods=sorted([o for o in bpy.context.scene.objects if '_LOD' in o.name],key=lambda o:o.name)
 for o in lods:
  bm=bmesh.new();bm.from_mesh(o.data)
  if name!='PANEL_VAN':
   pending=set(bm.verts)
   while pending:
    seed=pending.pop();comp={seed};stack=[seed]
    while stack:
     for e in stack.pop().link_edges:
      for n in e.verts:
       if n in pending:pending.remove(n);comp.add(n);stack.append(n)
    lo=Vector([min(v.co[i] for v in comp) for i in range(3)]);hi=Vector([max(v.co[i] for v in comp) for i in range(3)]);d=hi-lo;c=(hi+lo)/2
    if .8<c.x<1.4 and hi.z<1.1 and .7<d.y<1.1 and .7<d.z<1.1 and abs(d.y-d.z)<.15:
     for v in comp:v.co.x=2*c.x-v.co.x
   bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
  else:
   uv=bm.loops.layers.uv.active
   for f in bm.faces:
    c=f.calc_center_median()
    if c.y< -2.1 and .85<c.z<1.06 and .45<abs(c.x)<.95:
     for l in f.loops:l[uv].uv=((9%8+.5)/8,1-(9//8+.5)/4)
    elif c.y< -2.27 and c.z<.85 and abs(c.x)>.5:
     for l in f.loops:l[uv].uv=((6%8+.5)/8,1-(6//8+.5)/4)
  bm.to_mesh(o.data);bm.free()
 p['revision']=7
 for i,o in enumerate(lods):o.hide_render=i!=0;o.hide_set(i!=0)
 cols=[o for o in bpy.context.scene.objects if o.name.startswith('UCX')]
 for c in cols:c.hide_render=True;c.hide_set(True)
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'_v07.blend')))
 for group,suffix in [(lods,''),(cols,'_collisions')]:
  bpy.ops.object.select_all(action='DESELECT')
  for o in group:o.hide_set(False);o.select_set(True)
  bpy.context.view_layer.objects.active=group[0]
  bpy.ops.export_scene.fbx(filepath=str(folder/(name+suffix+'_v07.fbx')),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',bake_space_transform=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='RELATIVE')
 (folder/(name+'_collisions_v07.json')).write_text((folder/(name+f'_collisions_v{rev:02}.json')).read_text(),encoding='utf-8')
(r/'selected_models_v01.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
