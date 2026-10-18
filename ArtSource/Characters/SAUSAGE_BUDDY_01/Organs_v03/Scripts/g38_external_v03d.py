"""Read-only nearest external-mesh distances, including other UCX compounds."""
import json,sys,math
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
import g38_measure as M
V=json.loads((B.WORK/'validation_v03d_01.json').read_text())
cols=[o for o in bpy.context.scene.objects if o.name.startswith('UCX_')];out={}
for pose in ('closed','open35'):
    for tag,angle in [('L',35),('R',-35)]:bpy.data.objects['RIBCAGE_HALF_'+tag].rotation_euler.y=math.radians(angle if pose=='open35' else 0)
    bpy.context.view_layer.update();meshes={o.name:M.Mesh(o) for o in cols};rows={}
    for o in cols:
        r=V['colliders'][o.name]['poses'][pose];best=r['other_min_mm']/1000;name=r['nearest_other']
        if best>0:
            for other in cols:
                if other.parent==o.parent:continue
                d,_=M.distance(meshes[o.name],meshes[other.name],upper=best)
                if d<best:best=d;name=other.name
        rows[o.name]={'min_external_mesh_mm':best*1000,'nearest_external_mesh':name}
    out[pose]=rows
(B.WORK/'external_clearance_v03d.json').write_text(json.dumps(out,indent=2))
print('EXTERNAL_V03D_DONE',flush=True)
