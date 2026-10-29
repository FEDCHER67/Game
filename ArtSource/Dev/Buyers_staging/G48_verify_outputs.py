"""Inventory G48 deliverables plus retained standalone/Roslyn outputs; never modify gameplay."""
from pathlib import Path
import hashlib
import json

root=Path('C:/Dev/Game').resolve()
staging=root/'ArtSource/Dev/Buyers_staging'
before=json.loads((staging/'G48-before.json').read_text(encoding='utf-8'))
paths={root/p for p in [
    'Assets/OnlyVolunteers/Buyers/Core/BuyerCatalog.cs',
    'Assets/OnlyVolunteers/Buyers/Core/EconomyCatalog.cs',
    'Assets/OnlyVolunteers/Buyers/Core/EconomyCatalog.cs.meta',
    'Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json',
    'Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json.meta',
    'Assets/OnlyVolunteers/Buyers/Tests/EconomyDataTests.cs',
    'Assets/OnlyVolunteers/Buyers/Tests/EconomyDataTests.cs.meta',
    'docs/reports/ECONOMY_DATA_G48_RU.md',
]}
for p in staging.rglob('*'):
    if p.is_file() and (p.name.startswith('G48') or before.get(str(p.resolve()))!=hashlib.sha256(p.read_bytes()).hexdigest()): paths.add(p)

# The Roslyn helper uses shared Unity-generated project output paths. These four
# assemblies were compiled by G48; keep an explicit superset of their retained outputs.
assemblies=['OnlyVolunteers.Buyers.Core','OnlyVolunteers.Buyers.Tests','Assembly-CSharp','Assembly-CSharp-Editor']
for assembly in assemblies:
    for p in (root/'Temp/obj'/assembly).rglob('*'):
        if p.is_file(): paths.add(p)
    for p in (root/'Temp/bin/Debug').glob(assembly+'.*'):
        if p.is_file(): paths.add(p)

inventory=staging/'G48-files.txt'
verdict=staging/'G48-path-verification.json'
paths.update([inventory,verdict])
inventory.write_text('\n'.join(sorted(str(p.resolve()) for p in paths))+'\n',encoding='utf-8')
verdict.write_text('{}\n',encoding='utf-8')
failures=[str(p) for p in paths if not p.is_file() or not p.resolve().is_relative_to(root)]
assert not failures,failures
result={'result':'PASS','root':str(root),'files':len(paths),'all_exist':True,'all_under_requested_repo':True,
        'inventory':str(inventory),'note':'Includes retained generated standalone and shared Roslyn assembly output; Unity Library/Logs internals are generated editor caches, not authored deliverables.'}
verdict.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
