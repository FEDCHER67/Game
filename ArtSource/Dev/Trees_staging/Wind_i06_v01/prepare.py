from pathlib import Path
import hashlib, json, shutil
root=Path('C:/Dev/Game')
e=root/'Working/Reviews/Wind/trees_i06'
if not (e/'protected_before.json').exists():
    files={root/s for s in (e/'base_dependencies.txt').read_text().splitlines()}
    files.update((root/'ProjectSettings').glob('*'))
    files.update((root/'Assets/OnlyVolunteers/Map/Wind/v01').rglob('*'))
    files={f for f in files if f.is_file()}
    files.update(Path(str(f)+'.meta') for f in list(files) if Path(str(f)+'.meta').exists())
    hashes={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)}
    (e/'protected_before.json').write_text(json.dumps(hashes,indent=2))
    print('Protected',len(hashes),'files')
stage=root/'ArtSource/Dev/Trees_staging/Wind_i06_v01'
(stage/'Shaders').mkdir(exist_ok=True)
s=(root/'Assets/OnlyVolunteers/Map/Wind/v01/Shaders/GenericFoliageWind_v01.shader').read_text()
s=s.replace('OnlyVolunteers/Wind/v01/GenericFoliage','OnlyVolunteers/Wind/v02/GenericFoliage')
s=s.replace('#include "V19Wind.hlsl"','#include "Assets/OnlyVolunteers/Map/Wind/v01/Shaders/V19Wind.hlsl"')
s=s.replace('"Queue"="AlphaTest"','"Queue"="AlphaTest" "DisableBatching"="True"')
(stage/'Shaders/GenericFoliageWind_v02.shader').write_text(s)
if '--import' in __import__('sys').argv:
    dest=root/'Assets/OnlyVolunteers/Map/Wind/Trees_v01'
    for sub in ['Shaders','Runtime','Editor']:
        (dest/sub).mkdir(parents=True,exist_ok=True)
        for f in (stage/sub).glob('*'):
            if f.is_file():shutil.copyfile(f,dest/sub/f.name)
