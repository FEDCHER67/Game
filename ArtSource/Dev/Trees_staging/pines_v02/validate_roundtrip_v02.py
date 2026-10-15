from pathlib import Path
ROOT=Path(__file__).parent
code=(ROOT.parent/'oaks_pines_v01/validate_roundtrip_v01.py').read_text()
code=code.replace('validation_v01.json','validation_v02.json').replace('wind_bindings_v01.json','wind_bindings_v02.json').replace("+'_v01.fbx'","+'_v02.fbx'").replace('protected_before_v01.json','protected_before_v02.json').replace('fbx_roundtrip_v01.json','fbx_roundtrip_v02.json').replace('models=6,lods=18,capsuleRecipes=12','models=3,lods=9,capsuleRecipes=6')
exec(compile(code,str(ROOT/'validate_roundtrip_v02.py'),'exec'))
