import sys,json
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
import g38_measure as M
result={}
for o in bpy.context.scene.objects:
    if not o.name.startswith('BREAK_'):continue
    mesh=M.Mesh(o.parent);p=o.matrix_world.translation;q,n,ix,d=mesh.bvh.find_nearest(p)
    result[o.name]={'position_rest_m':list(p),'surface_distance_mm':d*1000,'inside':M.inside(mesh,p),
      'nearest_surface_rest_m':list(q),'parent':o.parent.name}
out=Path(sys.argv[sys.argv.index('--out')+1]) if '--out' in sys.argv else B.WORK/'break_check.json'
out.write_text(json.dumps(result,indent=2));print(result,flush=True)
