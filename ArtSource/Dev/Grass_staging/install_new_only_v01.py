"""Copy a fully compiled G24 set only while G24 owns the shared lock.
Call between AssetDatabase.StartAssetEditing()/StopAssetEditing() via the existing bridge.
"""
from pathlib import Path
import datetime, subprocess, shutil, sys, hashlib, json
ROOT=Path(r'C:\Dev\Game')
STAGE=ROOT/'ArtSource/Dev/Grass_staging'
LOCK=Path(r'C:\Users\Zeyo-ne\AppData\Local\Temp\claude\C--Dev\ea60d9e7-6c0b-4ef6-b304-3bbf5da8bf0f\scratchpad\unity.lock')
def check():
    content=LOCK.read_text().strip().split()
    assert content[0].upper()=='G24','G24 does not own Unity'
    age=datetime.datetime.now().timestamp()-LOCK.stat().st_mtime
    assert age<1200,'Refresh G24 lock before importing'
check()
subprocess.run([sys.executable,str(STAGE/'compile_staging_v01.py')],cwd=ROOT,check=True)
pairs=[(STAGE/'v01/ThirdParty',ROOT/'Assets/OnlyVolunteers/ThirdParty/GrassInstancer_MB'),(STAGE/'v01/Grass',ROOT/'Assets/OnlyVolunteers/Map/Grass')]
for source,target in pairs:assert not target.exists(),f'Refusing existing destination {target}'
check()
manifest=[]
for source,target in pairs:
    shutil.copytree(source,target)
    for p in target.rglob('*'):
        if p.is_file():manifest.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(STAGE/'evidence/import_manifest_v01.json').write_text(json.dumps(manifest,indent=2))
print('G24 import copied complete compiled set; release the Editor import pause now.')
