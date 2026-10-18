"""Compare every non-UCX object in both delivered FBX files with accepted v03c."""
import json,sys
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
results={}
for kind,relative in [('inbody','Organs_InBody_{version}.fbx'),('ribcage','FBX/RIBCAGE_{version}.fbx')]:
    snapshots={}
    for version in ('v03c','v03d'):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(B.OUT/relative.format(version=version)),use_custom_props=True)
        bpy.context.view_layer.update()
        snapshots[version]={o.name:{'snapshot':B.snapshot(o),'custom_properties':repr(dict(o.items()))} for o in bpy.context.scene.objects if not o.name.startswith('UCX_')}
    a=snapshots['v03c'];b=snapshots['v03d'];rows={n:{'before':a.get(n),'after':b.get(n),'exact':a.get(n)==b.get(n)} for n in sorted(set(a)|set(b))}
    results[kind]={'objects':rows,'all_non_ucx_exact':all(r['exact'] for r in rows.values())}
    print('FBX_VISUAL_PRESERVATION',kind,len(rows),results[kind]['all_non_ucx_exact'],flush=True)
(B.WORK/'fbx_visual_preservation_v03d.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
