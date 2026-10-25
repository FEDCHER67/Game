import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
ROOT=R.ROOT;stats=json.loads((ROOT/'selected_models_v01.json').read_text())
CELLS={'chrome':8,'lamp':9,'white':4,'trim':6,'orange':12,'sand':13,'container':14}
def setuv(bm,f,key):
 uv=bm.loops.layers.uv.active;i=CELLS[key];v=((i%8+.5)/8,1-(i//8+.5)/4)
 for l in f.loops:l[uv].uv=v
for p in stats:
 name=p['name']
 if name not in ['DUMP_TRUCK','CONTAINER_TRUCK','PANEL_VAN']:continue
 folder=Path(p['folder']);rev=p['revision'];bpy.ops.wm.open_mainfile(filepath=str(folder/(name+f'_v{rev:02}.blend')))
 lods=sorted([o for o in bpy.context.scene.objects if '_LOD' in o.name],key=lambda o:o.name)
 for o in lods:
  bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update()
  if name!='PANEL_VAN':
   pending=set(bm.verts)
   while pending:
    seed=pending.pop();comp={seed};stack=[seed]
    while stack:
     for e in stack.pop().link_edges:
      for n in e.verts:
       if n in pending:pending.remove(n);comp.add(n);stack.append(n)
    lo=Vector([min(v.co[i] for v in comp) for i in range(3)]);hi=Vector([max(v.co[i] for v in comp) for i in range(3)]);d=hi-lo;c=(hi+lo)/2
    if .8<abs(c.x)<1.4 and hi.z<1.1 and .7<d.y<1.1 and .7<d.z<1.1 and abs(d.y-d.z)<.15:
     for f in {f for v in comp for f in v.link_faces}:
      fc=f.calc_center_median();rad=math.sqrt(((fc.y-c.y)/(d.y/2))**2+((fc.z-c.z)/(d.z/2))**2)
      if rad<.68 and abs(f.normal.x)>.5:setuv(bm,f,'chrome')
  for f in bm.faces:
   c=f.calc_center_median()
   if name=='CONTAINER_TRUCK' and c.y>-4.1 and c.z>1.4:setuv(bm,f,'container')
   elif name=='DUMP_TRUCK':
    if c.y>-1.7 and c.z>1.2:setuv(bm,f,'orange' if abs(c.x)>1.1 or c.z<1.45 or c.y>3.8 or c.y< -1.5 else 'sand')
    if .7<abs(c.x)<1.15 and -1.5<c.y<-.4 and c.z<1.0:setuv(bm,f,'chrome')
   elif name=='PANEL_VAN':
    if c.y< -2.1 and .58<c.z<.9 and .35<abs(c.x)<.95:setuv(bm,f,'lamp')
    elif c.y< -2.25 and c.z<.55 and abs(c.x)<.5:setuv(bm,f,'white')
    elif (c.y< -2.27 or c.y>2.4) and c.z<.75:setuv(bm,f,'trim')
  bm.to_mesh(o.data);bm.free()
 for i,o in enumerate(lods):o.hide_render=i!=0;o.hide_set(i!=0)
 cols=[o for o in bpy.context.scene.objects if o.name.startswith('UCX')]
 for c in cols:c.hide_render=True;c.hide_set(True)
 p['revision']=5;bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'_v05.blend')))
 for group,suffix in [(lods,''),(cols,'_collisions')]:
  bpy.ops.object.select_all(action='DESELECT')
  for o in group:o.hide_set(False);o.select_set(True)
  bpy.context.view_layer.objects.active=group[0]
  bpy.ops.export_scene.fbx(filepath=str(folder/(name+suffix+'_v05.fbx')),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',bake_space_transform=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='RELATIVE')
 (folder/(name+'_collisions_v05.json')).write_text((folder/(name+f'_collisions_v{rev:02}.json')).read_text(),encoding='utf-8')
(ROOT/'selected_models_v01.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')

