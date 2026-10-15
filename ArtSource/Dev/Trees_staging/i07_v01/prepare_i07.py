"""Copy only Fedya's 12 approved FBXs and the existing shared wind materials."""
from pathlib import Path
import hashlib,json,shutil
root=Path('C:/Dev/Game')
source=root/'ArtSource/Dev/Trees_staging/v04'
dest=root/'Assets/OnlyVolunteers/Art/Trees/Leafy_v04'
manifest=[]
for family in ('Apple','Poplar','Palm','Bush'):
    revision='v04_04' if family=='Poplar' else 'v04_03'
    for letter in 'ABC':
        name=f'{family}_{letter}_{revision}.fbx'
        a=source/'Models'/name;b=dest/'Models'/name
        assert not b.exists(),b
        b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
        manifest.append({'source':str(a),'target':str(b),'sha256':hashlib.sha256(a.read_bytes()).hexdigest()})
for a in sorted((source/'WindMaterials').glob('*_v04_03.mat*')):
    b=dest/'Materials'/a.name
    assert not b.exists(),b
    b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
    manifest.append({'source':str(a),'target':str(b),'sha256':hashlib.sha256(a.read_bytes()).hexdigest()})
(root/'Working/Reviews/Trees/i07/import_manifest.json').write_text(json.dumps(manifest,indent=2))
print('Copied',len(manifest),'files; exactly 12 approved FBXs and 16 material/meta pairs.')
