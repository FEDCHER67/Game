"""Compare unchanged objects in existing v03 and new v03b FBX imports."""
import json,sys
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
revision=sys.argv[sys.argv.index('--revision')+1] if '--revision' in sys.argv else 'v03b'
data={}
for version in ('v03',revision):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(B.OUT/f'Organs_InBody_{version}.fbx'),use_custom_props=True)
    bpy.context.view_layer.update()
    data[version]={o.name:B.snapshot(o) for o in bpy.context.scene.objects if not o.name.startswith(('RIB_','UCX_','BREAK_'))}
rows={n:{'before':v,'after':data[revision].get(n),'exact':v==data[revision].get(n)} for n,v in data['v03'].items()}
report={'objects':rows,'all_unchanged_nonrib_exact':all(r['exact'] for r in rows.values())}
(B.WORK/f'fbx_nonrib_preservation_{revision}.json').write_text(json.dumps(report,indent=2))
print('FBX_NONRIB_MISMATCHES',[n for n,r in rows.items() if not r['exact']],flush=True)
print('BASELINE_RIGHT_LUNG_TRIS',data['v03']['ORGAN_LUNG_R']['triangles'],flush=True)
