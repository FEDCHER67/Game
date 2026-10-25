import bpy,bmesh,json,sys
from pathlib import Path
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
root=R.ROOT;stats=json.loads((root/'selected_models_v01.json').read_text())
for p in stats:
 if p['name'] not in ['DUMP_TRUCK','CONTAINER_TRUCK','ASTRA_STATIC_VAN']:continue
 name=p['name'];folder=Path(p['folder']);old=p['revision'];R.clean();bpy.ops.import_scene.fbx(filepath=str(folder/(name+f'_v{old:02}.fbx')));o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD2'));uv=o.data.uv_layers.active
 verts=[list(v.co) for v in o.data.vertices];faces=[list(f.vertices) for f in o.data.polygons];uvs=[[list(uv.data[li].uv) for li in f.loop_indices] for f in o.data.polygons]
 bpy.ops.wm.open_mainfile(filepath=str(folder/(name+f'_v{old:02}.blend')));o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD2'));mat=o.data.materials[0]
 me=bpy.data.meshes.new(o.data.name+'_FBX_Canonical');me.from_pydata(verts,[],faces);me.update();me.materials.append(mat);layer=me.uv_layers.new()
 for f,us in zip(me.polygons,uvs):
  for li,u in zip(f.loop_indices,us):layer.data[li].uv=u
 o.data=me
 lods=sorted([o for o in bpy.context.scene.objects if '_LOD' in o.name],key=lambda o:o.name);cols=[o for o in bpy.context.scene.objects if o.name.startswith('UCX')]
 p['revision']=4;p['lod_triangles']=[R.tris([o]) for o in lods]
 p['geometry_audit']=[]
 for o in lods:
  bm=bmesh.new();bm.from_mesh(o.data);p['geometry_audit'].append({'name':o.name,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces),'scale':list(o.scale),'location':list(o.location)});bm.free()
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'_v04.blend')))
 for group,suffix in [(lods,''),(cols,'_collisions')]:
  bpy.ops.object.select_all(action='DESELECT')
  for o in group:o.hide_set(False);o.select_set(True)
  bpy.context.view_layer.objects.active=group[0]
  bpy.ops.export_scene.fbx(filepath=str(folder/(name+suffix+'_v04.fbx')),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',bake_space_transform=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='RELATIVE')
 (folder/(name+'_collisions_v04.json')).write_text((folder/(name+f'_collisions_v{old:02}.json')).read_text(),encoding='utf-8')
(root/'selected_models_v01.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
