import bpy,json
from pathlib import Path
ROOT=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Cozy_Oaks_v01_02.blend'))
with bpy.data.libraries.load(str(ROOT/'Cozy_Oaks_Pines_v01.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.startswith('SM_Pine_') or n.startswith('COL_Pine_')]
for ob in dst.objects:
    bpy.data.collections['COL_Collision' if ob.name.startswith('COL_') else 'COL_Geo'].objects.link(ob)
    ob.hide_render=True;ob.hide_set(True)
original=json.loads((ROOT/'validation_v01.json').read_text());oak=json.loads((ROOT/'validation_v01_02.json').read_text())
for row in oak['variants']:row['revision']='v01_02'
for row in original['variants']:row['revision']='v01'
final={**original,'variants':oak['variants']+[s for s in original['variants'] if s['family']=='Pine'],
       'lods':oak['lods']+[s for s in original['lods'] if s['id'].startswith('Pine')],
       'candidate':'Oak v01_02 crown refinement + unchanged Pine v01'}
(ROOT/'validation_candidates_v01_02.json').write_text(json.dumps(final,indent=2))
out=ROOT/'Cozy_Oaks_Pines_v01_02.blend';assert not out.exists();bpy.ops.wm.save_as_mainfile(filepath=str(out))
script=(ROOT/'render_preview_v01.py').read_text().replace('Cozy_Oaks_Pines_v01.blend','Cozy_Oaks_Pines_v01_02.blend').replace('validation_v01.json','validation_candidates_v01_02.json')
script=script.replace("'SM_'+s['id']+'_v01_LOD0'","'SM_'+s['id']+'_'+s['revision']+'_LOD0'")
script=script.replace('_lineup_v01','_lineup_v01_02').replace('_detail_v01','_detail_v01_02').replace('Approved_style_scale_v01','Approved_style_scale_v01_02').replace('preview_manifest_v01.json','preview_manifest_v01_02.json').replace('Cozy_Oaks_Pines_Preview_v01.blend','Cozy_Oaks_Pines_Preview_v01_02.blend')
out=ROOT/'render_preview_v01_02.py';assert not out.exists();out.write_text(script)
print('COMBINED_CANDIDATES_READY',flush=True)
