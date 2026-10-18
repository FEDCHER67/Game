"""Independent FBX roundtrip in an expendable background Blender process."""
import json,sys
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
revision=sys.argv[sys.argv.index('--revision')+1] if '--revision' in sys.argv else 'v03b'
ep=B.WORK/f'fbx_expected_{revision}.json'
if not ep.exists():ep=B.WORK/'fbx_expected.json'
expected=json.loads(ep.read_text());results={}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(B.OUT/'Organs_InBody_v03.fbx'),use_custom_props=True)
baseline={o.name:B.L.tris(o) for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('RIB_')}
for key,path in [('inbody',B.OUT/f'Organs_InBody_{revision}.fbx'),('ribcage',B.OUT/f'FBX/RIBCAGE_{revision}.fbx')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),use_custom_props=True)
    bpy.context.view_layer.update();rows={}
    for name,e in expected[key].items():
        ob=bpy.data.objects.get(name)
        if ob is None:rows[name]={'pass':False,'error':'missing'};continue
        bounds=B.world_bounds([ob]);err=max(abs(bounds[i][j]-e['bounds'][i][j])*1000 for i in range(2) for j in range(3))
        expected_tris=baseline.get(name,e['triangles'])
        rows[name]={'bounds_error_mm':err,'triangle_count':B.L.tris(ob),'blend_triangle_count':e['triangles'],'expected_imported_triangle_count':expected_tris,'parent':ob.parent.name if ob.parent else None,
                    'pass':err<.02 and B.L.tris(ob)==expected_tris and (ob.parent.name if ob.parent else None)==e['parent']}
    breaks=[o.name for o in bpy.context.scene.objects if o.name.startswith('BREAK_')]
    ucx=[o.name for o in bpy.context.scene.objects if o.name.startswith('UCX_')]
    props={o.name:float(o.get('mass_kg',-1)) for o in bpy.context.scene.objects if o.name.startswith(('RIB_','STERNUM_'))}
    results[key]={'path':str(path),'objects':rows,'break_count':len(breaks),'ucx_count':len(ucx),'mass_hints':props,
       'pass':all(r['pass'] for r in rows.values()) and len(breaks)==len(props) and len(ucx)==sum(n.startswith('UCX_') for n in expected[key]) and all(v>0 for v in props.values())}
(B.WORK/f'fbx_roundtrip_{revision}.json').write_text(json.dumps(results,indent=2));print('G38_FBX_ROUNDTRIP',[(k,r['pass']) for k,r in results.items()],flush=True)
