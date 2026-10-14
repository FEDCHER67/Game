"""Run from C:/Dev/Game ONLY after acquiring G22's shared Unity lock and stopping Play.
Creates new G22 files only; never replaces existing paths. Source compilation is mandatory.
Unity import/compile, shader validation, scene build and actual captures follow separately.
"""
from pathlib import Path
import json,hashlib,subprocess,sys,uuid

root=Path(r'C:\Dev\Game')
stage=root/'ArtSource/Dev/Sky_staging'
lock=Path(r'C:\Users\Zeyo-ne\AppData\Local\Temp\claude\C--Dev\ea60d9e7-6c0b-4ef6-b304-3bbf5da8bf0f\scratchpad\unity.lock')
def require_lock():
    if not lock.is_file() or not lock.read_text().startswith('gpt-g22 '):raise SystemExit('BLOCKED: G22 does not own unity.lock')
require_lock()
target=root/'Assets/OnlyVolunteers/Sky/G22_v01'
if target.exists():raise SystemExit('BLOCKED: target already exists. Never replace a deliverable.')
subprocess.run([sys.executable,str(stage/'compile_staging_v01.py')],cwd=root,check=True)
sources=list(sorted((stage/'v01').rglob('*')))
for source in sources:
    if source.is_file() and source.suffix not in ('.cs','.shader','.asmdef','.md'):raise SystemExit('Unexpected package file: '+str(source))
require_lock()
manifest=[]
for source in sources:
    require_lock()
    destination=target/source.relative_to(stage/'v01')
    if source.is_dir():destination.mkdir(parents=True,exist_ok=True);continue
    destination.parent.mkdir(parents=True,exist_ok=True)
    data=source.read_bytes()
    with destination.open('xb') as stream:stream.write(data)
    manifest.append(dict(path=destination.relative_to(root).as_posix(),sha256=hashlib.sha256(data).hexdigest()))
# Unity owns metadata generation and will produce its normal import settings for each new asset.
with (stage/'installed_manifest_v01.json').open('x') as stream:json.dump(manifest,stream,indent=2)
print('NEW G22 FILES CREATED:',len(manifest))
