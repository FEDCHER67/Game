import bpy,bmesh,json,sys
from pathlib import Path
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
root=R.ROOT;stats=json.loads((root/'selected_models_v01.json').read_text())
for p in stats:
 name=p['name']
 if name not in ['DUMP_TRUCK','CONTAINER_TRUCK','ASTRA_STATIC_VAN']:continue
 folder=Path(p['folder']);rev=p['revision'];original={'DUMP_TRUCK':1,'CONTAINER_TRUCK':3,'ASTRA_STATIC_VAN':2}[name]
 R.clean();bpy.ops.import_scene.fbx(filepath=str(folder/(name+f'_v{original:02}.fbx')));bpy.context.view_layer.update();o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD2'));verts=[list(o.matrix_world@v.co) for v in o.data.vertices]
 bpy.ops.wm.open_mainfile(filepath=str(folder/(name+f'_v{rev:02}.blend')));o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD2'));assert len(verts)==len(o.data.vertices)
 for v,co in zip(o.data.vertices,verts):v.co=co
 o.data.update();p['revision']=6
 lods=sorted([o for o in bpy.context.scene.objects if '_LOD' in o.name],key=lambda o:o.name);cols=[o for o in bpy.context.scene.objects if o.name.startswith('UCX')]
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'_v06.blend')))
 for group,suffix in [(lods,''),(cols,'_collisions')]:
  bpy.ops.object.select_all(action='DESELECT')
  for o in group:o.hide_set(False);o.select_set(True)
  bpy.context.view_layer.objects.active=group[0]
  bpy.ops.export_scene.fbx(filepath=str(folder/(name+suffix+'_v06.fbx')),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',bake_space_transform=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='RELATIVE')
 (folder/(name+'_collisions_v06.json')).write_text((folder/(name+f'_collisions_v{rev:02}.json')).read_text(),encoding='utf-8')
(root/'selected_models_v01.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
