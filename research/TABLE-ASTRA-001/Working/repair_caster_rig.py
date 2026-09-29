import bpy,json,sys
from pathlib import Path
R=Path(r'C:\Dev\Game-main\research\TABLE-ASTRA-001')
sys.path.insert(0,str(R/'Working'))
from caster_geometry import rebuild_casters
bpy.ops.wm.open_mainfile(filepath=str(R/'TABLE-ASTRA-001.blend'))
bpy.context.preferences.filepaths.save_version=0
root=bpy.data.objects['RIG_Table_Root']
geo=bpy.data.collections['TABLE_ASTRA_Geometry']
rig=bpy.data.collections['TABLE_ASTRA_Rig']
forks,wheels,report=rebuild_casters(root,geo,rig,bpy.data.materials['MAT_Frame_MatteGraphite'],bpy.data.materials['MAT_Wheels_DarkRubber'])
(R/'Working'/'caster_geometry_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.object.select_all(action='DESELECT')
for o in list(geo.objects)+list(rig.objects):o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=str(R/'TABLE-ASTRA-001.fbx'),use_selection=True,
    object_types={'MESH','EMPTY'},add_leaf_bones=False,bake_anim=False,apply_scale_options='FBX_SCALE_UNITS')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'TABLE-ASTRA-001.blend'))
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_percentage=100
scene.render.filepath=str(R/'MotionPreview'/'repaired_static.png')
bpy.ops.render.render(write_still=True)
print('Rebuilt four physically placed trailing caster modules')
