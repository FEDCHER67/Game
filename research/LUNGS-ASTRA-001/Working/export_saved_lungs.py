import bpy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
asset_col=bpy.data.collections['LUNGS-ASTRA-001 | Game Assembly']
rig=asset_col.objects['Lungs_Breath_Rig']
parts=[o for o in asset_col.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for obj in asset_col.objects:obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'LUNGS-ASTRA-001.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE',use_mesh_modifiers=True,
    add_leaf_bones=False,use_armature_deform_only=True,bake_anim=True,bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,bake_anim_use_all_actions=True,bake_anim_step=1.0,
    bake_anim_simplify_factor=0.0,path_mode='STRIP')
metrics={'parts':{o.name:{'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)} for o in parts},
         'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},
         'materials':{m.name:{'color':list(m.diffuse_color),'roughness':m.roughness} for m in bpy.data.materials}}
with open(ROOT/'Working'/'build_metrics.json','w') as f:json.dump(metrics,f,indent=2)
print('EXPORT_METRICS',json.dumps(metrics))
