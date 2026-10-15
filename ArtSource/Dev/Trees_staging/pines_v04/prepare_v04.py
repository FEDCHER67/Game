from pathlib import Path
import hashlib,json
ROOT=Path(__file__).parent;GAME=ROOT.parents[3];OLD=ROOT.parent/'pines_v03'
for n in ['Models','Preview']:(ROOT/n).mkdir(exist_ok=True)
previous=json.loads((OLD/'protected_before_v03.json').read_text());protected={}
for p in [GAME/n for n in previous]+[p for p in OLD.rglob('*') if p.is_file()]:protected[str(p.relative_to(GAME))]=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
p=ROOT/'protected_before_v04.json';assert not p.exists();p.write_text(json.dumps(protected,indent=2))
binding=json.loads((OLD/'wind_bindings_v03.json').read_text());binding['status']='Pine v04 retains existing stiff shared Pine V19Wind materials; Blender-only approval candidate.'
(ROOT/'wind_bindings_v04.json').write_text(json.dumps(binding,indent=2))
render=(OLD/'render_preview_v03_02.py').read_text().replace('Cozy_Pines_v03_02.blend','Cozy_Pines_v04.blend').replace('validation_v03_02.json','validation_v04.json').replace("+'_v03_02_LOD0'","+'_v04_LOD0'").replace("'SM_Pine_A_v02_02_LOD0'","'SM_Pine_A_v03_02_LOD0'").replace("'PREVIEW_Pine_A_v02'","'PREVIEW_Pine_A_v03'").replace('Pines_lineup_v03_02','Pines_lineup_v04').replace('Pine_A_side_v03_02','Pine_A_side_v04').replace('Cozy_Pines_Preview_v03_02.blend','Cozy_Pines_Preview_v04.blend').replace('preview_manifest_v03_02.json','preview_manifest_v04.json')
(ROOT/'render_preview_v04.py').write_text(render)
validator=(ROOT.parent/'oaks_pines_v01/validate_roundtrip_v01.py').read_text().replace('validation_v01.json','validation_v04.json').replace('wind_bindings_v01.json','wind_bindings_v04.json').replace("+'_v01.fbx'","+'_v04.fbx'").replace('protected_before_v01.json','protected_before_v04.json').replace('fbx_roundtrip_v01.json','fbx_roundtrip_v04.json').replace('models=6,lods=18,capsuleRecipes=12','models=3,lods=9,capsuleRecipes=6').replace('tris<=7000','tris<=8000')
(ROOT/'validate_roundtrip_v04.py').write_text(validator)
print('Protected',len(protected),'files; staged unchanged wind bindings and v04 review/validation scripts.')
