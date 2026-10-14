"""Independent saved-master audit of JSON collider box surfaces and walkway samples."""
import sys, json
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import bpy
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
from build_pilot_kit import write_json, next_path, cmatrix, corners

report=json.loads((HERE/'validation_v01.json').read_text(encoding='utf8'))
bpy.ops.wm.open_mainfile(filepath=str(HERE/'SK3-PILOT-001_v01.blend'))
result=dict(source='Saved SK3-PILOT-001_v01.blend and validation_v01.json; module-local mesh vertices',assets={})
for name,r in report['assets'].items():
    ob=bpy.data.objects['SM_'+name]; me=ob.data
    tree=BVHTree.FromPolygons([v.co for v in me.vertices],[list(p.vertices) for p in me.polygons],all_triangles=False)
    checked=0; worst=0; misses=[]
    for c in r['colliders']:
        if not c.get('supports_standing'): continue
        M=cmatrix(c); normal=M.to_3x3()@Vector((0,0,1))
        if normal.z<.99: continue
        for x in (-.38,0,.38):
            for y in (-.38,0,.38):
                point=M@Vector((c['size_m'][0]*x,c['size_m'][1]*y,c['size_m'][2]/2))
                # Nearest point detects the exact authored surface even where
                # component end caps touch another component; no collider AABB.
                hit=tree.find_nearest(point,.002)
                checked+=1
                if hit[0] is None: misses.append(c['id']); continue
                err=(hit[0]-point).length; worst=max(worst,err)
                if err>.001: misses.append(c['id'])
    result['assets'][name]=dict(standable_samples_checked=checked,max_surface_error_m=worst,missed_proxy_ids=sorted(set(misses)),all_checks_passed=not misses)
    print('SURFACE_AUDIT',name,checked,worst,sorted(set(misses)),flush=True)
result['all_checks_passed']=all(v['all_checks_passed'] for v in result['assets'].values())
result['total_samples']=sum(v['standable_samples_checked'] for v in result['assets'].values())
result['max_surface_error_m']=max(v['max_surface_error_m'] for v in result['assets'].values())
write_json(next_path('collision_surface_audit','v01','json'),result)
if not result['all_checks_passed']: raise RuntimeError('Independent surface audit failed')
