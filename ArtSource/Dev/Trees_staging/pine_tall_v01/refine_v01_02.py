from pathlib import Path
import hashlib,json
r=Path(__file__).parent
protected={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file() and ('v01' in p.name) and p.name!='refine_v01_02.py'}
(r/'internal_v01_preserved_v01_02.json').write_text(json.dumps(protected,indent=2))
s=(r/'build_pine_tall_v01.py').read_text()
s=s.replace('Cozy_PineTall_v01.blend','Cozy_PineTall_v01_02.blend').replace('_v01_LOD{lod}','_v01_02_LOD{lod}').replace('_v01.fbx','_v01_02.fbx').replace('_Trunk_{ci+1}_v01','_Trunk_{ci+1}_v01_02').replace('validation_v01.json','validation_v01_02.json')
s=s.replace('arms=[3,4,3,4,3,3,3,2]','arms=[3,3,2,3,3,2,3,2,3,2]').replace('arms=[4,3,4,3,4,3,3,3]','arms=[3,3,3,3,3,3,3,3,2,2]').replace('arms=[3,3,4,3,3,4,2,2]','arms=[2,3,3,2,3,3,2,3,2,2]')
s=s.replace('levels=[.375,.46,.545,.63,.715,.79,.865,.93]','levels=[.375,.438,.505,.567,.628,.694,.755,.817,.879,.937]')
s=s.replace('rng.uniform(-.37,.37)','rng.uniform(-.48,.48)')
s=s.replace("scale=rng.uniform(.80,1.13)*(1-.40*max(0,(q-.62)/.38))","scale=rng.uniform(.93,1.28)*(1-.32*max(0,(q-.62)/.38))")
s=s.replace("if tier<5 and j==s['variant']%n:","if j==s['variant']%n:")
s=s.replace("ep=tip+side*w*.08+Vector((0,0,-.22))","ep=mid.lerp(tip,.50)+side*w*.07+Vector((0,0,rng.uniform(-.43,.38)))")
s=s.replace("size=scale*.72","size=scale*.90")
s=s.replace('for k in range(11):','for k in range(9):')
s=s.replace('up*math.sin(a)*.72','up*math.sin(a)*1.03').replace('cr.uniform(-.12,.12)*size+axis','cr.uniform(-.24,.24)*size+axis')
s=s.replace('cr.uniform(.72,1.12)*size','cr.uniform(.78,1.18)*size')
p=r/'build_pine_tall_v01_02.py';assert not p.exists();p.write_text(s)
s=(r/'render_preview_v01.py').read_text().replace('Cozy_PineTall_v01.blend','Cozy_PineTall_v01_02.blend').replace('_v01_LOD0','_v01_02_LOD0').replace('PineTall_lineup_v01','PineTall_lineup_v01_02').replace('PineTall_A_clumps_stubs_v01','PineTall_A_clumps_stubs_v01_02').replace('PineTall_A_crown_v01','PineTall_A_crown_v01_02').replace('Cozy_PineTall_Preview_v01.blend','Cozy_PineTall_Preview_v01_02.blend').replace('preview_manifest_v01.json','preview_manifest_v01_02.json')
p=r/'render_preview_v01_02.py';assert not p.exists();p.write_text(s)
s=(r/'validate_roundtrip_v01.py').read_text().replace('validation_v01.json','validation_v01_02.json').replace('_v01.fbx','_v01_02.fbx').replace('fbx_roundtrip_v01.json','fbx_roundtrip_v01_02.json')
p=r/'validate_roundtrip_v01_02.py';assert not p.exists();p.write_text(s)
print('New numbered refinement scripts prepared; first build preserved.')
