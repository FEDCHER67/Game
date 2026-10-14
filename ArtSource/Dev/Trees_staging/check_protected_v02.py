from pathlib import Path
import hashlib
import json

root = Path(r'C:\Dev\Game')
stage = root/'ArtSource/Dev/Trees_staging'
before = json.loads((stage/'protected_before_v02.json').read_text(encoding='utf-8'))
changed = []
for name, expected in before.items():
    path = root/name
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'MISSING'
    if actual != expected:
        changed.append({'path':name, 'before':expected, 'after':actual})
result = {'checked_files':len(before), 'changed':changed, 'passed':not changed}
output = root/'Working/Reviews/Trees/protected_files_v02.json'
if output.exists():
    raise RuntimeError('Refusing to overwrite verification evidence')
output.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
