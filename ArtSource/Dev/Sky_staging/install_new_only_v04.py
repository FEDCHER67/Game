"""Import a complete v04 source set only while unity_lock.ps1 grants G22 ownership."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path('C:/Dev/Game');stage=root/'ArtSource/Dev/Sky_staging';source=stage/'v04'
target=root/'Assets/OnlyVolunteers/Sky/G22_v04'
lock=Path('C:/Users/Zeyo-ne/AppData/Local/Temp/claude/C--Dev/ea60d9e7-6c0b-4ef6-b304-3bbf5da8bf0f/scratchpad/unity.lock')
def require_lock():
    owner=lock.read_text().split()[0].upper().removeprefix('GPT-') if lock.is_file() else ''
    if owner!='G22':raise SystemExit('BLOCKED: acquire G22 ownership with unity_lock.ps1 first')
require_lock()
if target.exists():raise SystemExit('Destination exists; refusing to replace a deliverable')
subprocess.run([sys.executable,str(stage/'compile_staging_v04.py')],cwd=root,check=True)
sources=[p for p in sorted(source.rglob('*')) if p.is_file()]
if any(p.suffix not in ('.cs','.shader','.asmdef','.md') for p in sources):raise SystemExit('Unexpected package file')
require_lock();manifest=[]
for path in sources:
    require_lock();dest=target/path.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True)
    data=path.read_bytes()
    with dest.open('xb') as f:f.write(data)
    manifest.append({'path':dest.relative_to(root).as_posix(),'sha256':hashlib.sha256(data).hexdigest()})
with (stage/'installed_manifest_v04.json').open('x') as f:json.dump(manifest,f,indent=2)
print('Imported complete source set:',len(manifest),'new files. Unity owns metadata generation.')
