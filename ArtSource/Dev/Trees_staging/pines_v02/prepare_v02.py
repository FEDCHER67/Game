from pathlib import Path
import hashlib,json
ROOT=Path(__file__).parent;GAME=ROOT.parents[3];OLD=ROOT.parent/'oaks_pines_v01'
for name in ['Models','Preview']: (ROOT/name).mkdir(exist_ok=True)
protected={}
previous=json.loads((OLD/'protected_before_v01.json').read_text())
for path in [GAME/n for n in previous]+[p for p in OLD.rglob('*') if p.is_file()]:
    protected[str(path.relative_to(GAME))]=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
path=ROOT/'protected_before_v02.json';assert not path.exists();path.write_text(json.dumps(protected,indent=2))
old=json.loads((OLD/'wind_bindings_v01.json').read_text())
bindings={k:old[k] for k in ['shader','shader_guid','shared_include']}
bindings['profiles']={'Pine':old['profiles']['Pine']}
bindings['material_remaps']={'Pine':{k:'../oaks_pines_v01/'+v.replace('\\','/') for k,v in old['material_remaps']['Pine'].items()}}
bindings['status']='Reuse the unchanged stiff Pine v01 shared V19Wind materials; no new shader or Unity import. World-height stiffness must scale at eventual integration.'
(ROOT/'wind_bindings_v02.json').write_text(json.dumps(bindings,indent=2))
print('Protected',len(protected),'existing files; unchanged pine material bindings recorded.')
