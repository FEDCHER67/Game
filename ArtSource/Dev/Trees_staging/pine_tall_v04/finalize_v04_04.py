"""Publish the measured v04_03 geometry with consistent native-width metadata."""
import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).parent;output=ROOT/'Cozy_PineTall_v04_04.blend';assert not output.exists()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Cozy_PineTall_v04_03.blend'))
data=json.loads((ROOT/'validation_v04_03.json').read_text());identities=[]
def geometry(ob):return hashlib.sha256(repr(([tuple(v.co) for v in ob.data.vertices],[(tuple(p.vertices),p.material_index) for p in ob.data.polygons])).encode()).hexdigest()
for spec in data['variants']:
    actual=next(r['crownWidth'] for r in data['lods'] if r['id']==spec['id'] and r['lod']==0)
    spec['sourceCrownWidth']=spec['width'];spec['width']=actual
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):
        ob=bpy.data.objects[f'SM_{spec["id"]}_v04_LOD{lod}'];before=geometry(ob)
        ob.name=ob.name.replace('_v04_LOD','_v04_04_LOD');ob.data.name=ob.data.name.replace('_v04_LOD','_v04_04_LOD')
        ob['crown_width_m']=next(r['crownWidth'] for r in data['lods'] if r['id']==spec['id'] and r['lod']==lod)
        ob.hide_set(False);ob.select_set(True);assert before==geometry(ob)
        identities.append(dict(model=ob.name,sha256=before,geometryUnchangedFrom='v04_03'))
    bpy.context.view_layer.objects.active=bpy.data.objects[f'SM_{spec["id"]}_v04_04_LOD0']
    path=ROOT/'Models'/f'{spec["id"]}_v04_04.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for ob in bpy.context.selected_objects:ob.hide_set(True)
for ob in bpy.data.objects:
    if ob.name.startswith('COL_PineTall_'):ob.name=ob.name.replace('v04_03','v04_04')
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(ROOT/'validation_v04_04.json').write_text(json.dumps(data,indent=2))
for name in ('wind_bindings','protected_before','fullness_measurement'):
    (ROOT/f'{name}_v04_04.json').write_text((ROOT/f'{name}_v04_03.json').read_text())
recipe=json.loads((ROOT/'prefab_recipe_v04_03.json').read_text());recipe['sourceRevision']='v04_04'
for spec in recipe['variants']:spec['fbx']=spec['fbx'].replace('v04_03','v04_04')
(ROOT/'prefab_recipe_v04_04.json').write_text(json.dumps(recipe,indent=2))
(ROOT/'geometry_identity_v04_04.json').write_text(json.dumps(dict(status='PASS',rows=identities,renderSource='Preview/*_v04_03.png: identical geometry, materials, coordinates and normals; only native-width custom metadata and revision names updated.'),indent=2))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Cozy_PineTall_Preview_v04_03.blend'))
for ob in bpy.data.objects:
    if '_v04_LOD' in ob.name:ob.name=ob.name.replace('_v04_LOD','_v04_04_LOD')
    if '_v04_03' in ob.name:ob.name=ob.name.replace('_v04_03','_v04_04')
    if ob.type=='MESH' and 'PineTall' in ob.name and ('v04_04' in ob.name or ob.name.startswith('PREVIEW_PineTall_')):
        ob['crown_width_m']=max(max(v.co[k] for v in ob.data.vertices)-min(v.co[k] for v in ob.data.vertices) for k in (0,1))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Cozy_PineTall_Preview_v04_04.blend'))
print('FINAL_V04_04_PASS: identical geometry, corrected native-width metadata, three FBX and source/preview blends saved',flush=True)
