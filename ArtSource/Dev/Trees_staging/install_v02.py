"""G23 import transaction. Run only while this worker owns the overnight Unity lock.
StartAssetEditing must already be held by the live editor. Unity creates new .meta files.
"""
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime, timezone

ROOT = Path(r'C:\Dev\Game')
STAGE = ROOT / 'ArtSource/Dev/Trees_staging'
LOCK = Path(r'C:\Users\Zeyo-ne\AppData\Local\Temp\claude\C--Dev\ea60d9e7-6c0b-4ef6-b304-3bbf5da8bf0f\scratchpad\unity.lock')
DEST = ROOT / 'Assets/OnlyVolunteers/Art/Trees/v02'
lock_text = LOCK.read_text(encoding='utf-8-sig').strip()
if not lock_text.lower().startswith('g23 '):
    raise RuntimeError('G23 does not own the Unity lock: ' + lock_text)
if DEST.exists():
    raise RuntimeError('Never overwrite an existing tree revision: ' + str(DEST))

edits = {
 'Assets/OnlyVolunteers/Map/LookV3/Editor/V3Terrain.cs': [
  ('td.SetTreeInstances(instances.ToArray(), true);', 'td.SetTreeInstances(instances.ToArray(), true);\n            V19TreesCozyV02.ApplyToTerrain(td,new Vector3(t.x0,0,t.y0),MapLookBuilderV3.Current);')],
 'Assets/OnlyVolunteers/Map/LookV3/Editor/V19Happykeys.cs': [
  ('static GameObject Prefab(string id)=>AssetDatabase.LoadAssetAtPath<GameObject>(Assets+"/Prefabs/"+id+"_v19.prefab");',
   'static GameObject Prefab(string id)=>V19TreesCozyV02.Resolve(AssetDatabase.LoadAssetAtPath<GameObject>(Assets+"/Prefabs/"+id+"_v19.prefab"), "v19");')],
 'Assets/OnlyVolunteers/Map/LookV3/Editor/V19FinalGeometry.cs': [
  ('terrain.terrainData=td;terrain.GetComponent<TerrainCollider>().terrainData=td;',
   'td=V19TreesCozyV02.ResolveTerrainCopy(td,terrain.transform.position,"v19");\n            terrain.terrainData=td;terrain.GetComponent<TerrainCollider>().terrainData=td;')],
 'Assets/OnlyVolunteers/Map/LookV3/Editor/V19FullPalette.cs': [
  ('td.SetTreeInstances(trees,false);EditorUtility.SetDirty(td);', 'td.SetTreeInstances(trees,false);bool treesChanged=V19TreesCozyV02.ApplyToTerrain(td,terrain.transform.position,"v19");EditorUtility.SetDirty(td);'),
  ('prototypesUnchanged=true,instanceAppearanceUnchanged=true', 'prototypesUnchanged=!treesChanged,instanceAppearanceUnchanged=!treesChanged')]
}
ready = {}
for name, replacements in edits.items():
    data = (ROOT / name).read_bytes()
    for old, new in replacements:
        if data.count(old.encode()) != 1:
            raise RuntimeError('Builder changed; review before patching ' + name + ': ' + old)
        data = data.replace(old.encode(), new.encode())
    ready[name] = data

protected = []
for folder in [
 'ArtSource/ThirdParty/happykeys_rocks_dead_trees/v01',
 'Assets/OnlyVolunteers/ThirdParty/happykeys_rocks_dead_trees/v01',
 'Assets/OnlyVolunteers/Art/Map/Prefabs/TREES',
 'Assets/OnlyVolunteers/Art/Map/Prefabs/Meshes',
 'Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v02',
 'ProjectSettings']:
    protected += [p for p in (ROOT / folder).rglob('*') if p.is_file()]
protected += [ROOT/'Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v02/Prefabs/LEAFLESS_TERRAIN_v03.prefab']
protected += [p for p in (ROOT/'Assets/OnlyVolunteers/Map/LookV3/Palette19').rglob('Terrain*.asset') if p.is_file()]
protected += [p for p in (ROOT/'Assets/OnlyVolunteers/Scenes/Map').glob('*') if p.is_file()]
fingerprints = {str(p.relative_to(ROOT)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
(STAGE/'protected_before_v02.json').write_text(json.dumps(fingerprints, indent=2), encoding='utf-8')
changes = []
for name, data in ready.items():
    old = (ROOT/name).read_bytes()
    changes.append({'path':name, 'before_sha256':hashlib.sha256(old).hexdigest(), 'after_sha256':hashlib.sha256(data).hexdigest()})

shutil.copytree(STAGE/'v02', DEST)
for name, data in ready.items():
    (ROOT/name).write_bytes(data)
(STAGE/'install_v02.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(), 'builder_edits':changes, 'copied_set':str(DEST)}, indent=2), encoding='utf-8')
print('Imported complete staged set and scoped tree-selection hooks in four builder files. No map rebuild.')
