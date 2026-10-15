from pathlib import Path
ROOT=Path(__file__).parent
source=(ROOT/'validate_roundtrip_v01.py').read_text()
source=source.replace('validation_v01.json','validation_candidates_v01_02.json')
source=source.replace("spec['id']+'_v01.fbx'","spec['id']+'_'+spec['revision']+'.fbx'")
source=source.replace('fbx_roundtrip_v01.json','fbx_roundtrip_v01_02.json')
exec(compile(source,str(__file__),'exec'))
