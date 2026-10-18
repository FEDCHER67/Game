"""Refine an inconclusive coarse outside bound without changing geometry."""
import json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_measure as M
W=Path('C:/Dev/Game/Working/Reviews/Operations/organs_v03/G38_work')
src=Path(sys.argv[sys.argv.index('--input')+1]) if '--input' in sys.argv else W/'fit_v03d_01.json'
dst=Path(sys.argv[sys.argv.index('--out')+1]) if '--out' in sys.argv else W/'fit_v03d_final.json'
assert not dst.exists()
report=json.loads(src.read_text())
for name,row in report['outside'].items():
    if row['pass_2mm']:continue
    ob=bpy.data.objects[name];bone=M.Mesh(ob.parent);col=M.Mesh(ob)
    stack=[(col.v[t],0) for t in col.t];upper=0.;sample_max=0.;count=0;leaves=0;deepest=0;worst=None
    # Distance to a closed solid is 1-Lipschitz. The farthest triangle vertex
    # from its centroid bounds every point in the entire triangle.
    while stack:
        tri,depth=stack.pop();center=tri.mean(axis=0)
        d=bone.bvh.find_nearest(Vector(center))[3]
        if M.inside(bone,center):d=0.
        radius=float(np.linalg.norm(tri-center,axis=1).max());bound=d+radius+1e-5
        count+=1;deepest=max(deepest,depth)
        if d>sample_max:sample_max=d;worst=center.tolist()
        if bound<=.001999 or radius<.000005 or depth>=28:
            upper=max(upper,bound);leaves+=1;continue
        edge=max(((0,1),(1,2),(2,0)),key=lambda ij:np.linalg.norm(tri[ij[0]]-tri[ij[1]]))
        a,b=edge;c=3-a-b;mid=(tri[a]+tri[b])/2
        stack.extend([(np.array([tri[a],mid,tri[c]]),depth+1),(np.array([mid,tri[b],tri[c]]),depth+1)])
    row['coarse_measurement']=dict(row)
    row.update(sample_max_outside_mm=sample_max*1000,certified_upper_outside_mm=upper*1000,
      samples=count,worst_sample_rest_m=worst,pass_2mm=upper<=.002,
      method='Adaptive longest-edge subdivision, centroid distance-to-solid + enclosing radius + 0.01 mm numeric allowance.',
      adaptive_leaves=leaves,maximum_depth=deepest)
    row.pop('grid_cover_radius_mm',None)
    print('REFINED',name,'samples',count,'max_sample_mm',sample_max*1000,'bound_mm',upper*1000,flush=True)
report['summary']['outside_2mm_pass']=all(r['pass_2mm'] for r in report['outside'].values())
report['summary']['maximum_outside_bound_mm']=max(r['certified_upper_outside_mm'] for r in report['outside'].values())
report['refinement_source']=str(src)
dst.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FIT_FINAL',report['summary'],flush=True)
