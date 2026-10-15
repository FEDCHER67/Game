from pathlib import Path
import hashlib,json
ROOT=Path(__file__).parent;GAME=ROOT.parents[3];OLD=ROOT.parent/'pines_v02'
for name in ['Models','Preview']:(ROOT/name).mkdir(exist_ok=True)
previous=json.loads((OLD/'protected_before_v02.json').read_text());protected={}
for path in [GAME/n for n in previous]+[p for p in OLD.rglob('*') if p.is_file()]:
    protected[str(path.relative_to(GAME))]=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
out=ROOT/'protected_before_v03.json';assert not out.exists();out.write_text(json.dumps(protected,indent=2))
binding=json.loads((OLD/'wind_bindings_v02.json').read_text());binding['status']='Pine v03 reuses unchanged stiff Pine materials and shared V19Wind. Blender only; Unity verification deferred.'
(ROOT/'wind_bindings_v03.json').write_text(json.dumps(binding,indent=2))
print('Protected',len(protected),'files; shared wind bindings unchanged.')
