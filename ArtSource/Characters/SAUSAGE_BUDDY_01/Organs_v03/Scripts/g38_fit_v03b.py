"""Two-sided surface-fit certificates for the saved compound colliders."""
import json
import sys
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_measure as M

cols=sorted([o for o in bpy.context.scene.objects if o.name.startswith('UCX_')],key=lambda o:o.name)
bones={o.parent.name:o.parent for o in cols}
bone_meshes={n:M.Mesh(o) for n,o in bones.items()}
col_meshes={o.name:M.Mesh(o) for o in cols}
outside={}
for ob in cols:
    col=col_meshes[ob.name];bone=bone_meshes[ob.parent.name]
    spacing=.001;best=0.0;where=None;samples=0
    for p in M.surface_samples(col,spacing):
        q,n,index,d=bone.bvh.find_nearest(Vector(p));samples+=1
        if d>best+1e-7 and not M.inside(bone,p):best=d;where=p.tolist()
    if best<.002 and best+spacing>.002:
        spacing=.00025;best=0.0;samples=0
        for p in M.surface_samples(col,spacing):
            q,n,index,d=bone.bvh.find_nearest(Vector(p));samples+=1
            if d>best+1e-7 and not M.inside(bone,p):best=d;where=p.tolist()
    outside[ob.name]={'sample_max_outside_mm':best*1000,'certified_upper_outside_mm':(best+spacing)*1000,
                      'grid_cover_radius_mm':spacing*1000,'samples':samples,'worst_sample_rest_m':where,
                      'pass_2mm':best+spacing<=.002}
    print('[G38 FIT]',ob.name,round(best*1000,4),'upper',round((best+spacing)*1000,4),flush=True)

coverage={}
for name,bone in bone_meshes.items():
    points=np.array(list(M.surface_samples(bone,.0005)))
    inside_any=np.zeros(len(points),dtype=bool)
    own=[col_meshes[o.name] for o in cols if o.parent.name==name]
    for c in own:
        norms=[];origins=[]
        for t in c.t:
            a,b,d=c.v[t];n=np.cross(b-a,d-a);n/=max(np.linalg.norm(n),1e-30);norms.append(n);origins.append(a)
        norms=np.array(norms);offset=np.einsum('ij,ij->i',np.array(origins),norms)
        for start in range(0,len(points),10000):
            block=points[start:start+10000]
            inside_any[start:start+10000]|=np.all(block@norms.T-offset<=.000005,axis=1)
    best=0.0;where=None
    for p in points[~inside_any]:
        d=min(c.bvh.find_nearest(Vector(p))[3] for c in own)
        if d>best:best=d;where=p.tolist()
    cover=.0005
    if best+cover>.001:
        cover=.0002;best=0.0
        refined=np.array(list(M.surface_samples(bone,cover)))
        contained=np.zeros(len(refined),dtype=bool)
        for c in own:
            norms=[];origins=[]
            for t in c.t:
                a,b,d=c.v[t];n=np.cross(b-a,d-a);n/=max(np.linalg.norm(n),1e-30);norms.append(n);origins.append(a)
            norms=np.array(norms);offset=np.einsum('ij,ij->i',np.array(origins),norms)
            for start in range(0,len(refined),10000):
                contained[start:start+10000]|=np.all(refined[start:start+10000]@norms.T-offset<=.000005,axis=1)
        for p in refined[~contained]:
            d=min(c.bvh.find_nearest(Vector(p))[3] for c in own)
            if d>best:best=d;where=p.tolist()
    coverage[name]={'sample_max_uncovered_mm':best*1000,'certified_upper_uncovered_mm':(best+cover+.00001)*1000,
                    'grid_cover_radius_mm':cover*1000,'samples_initial':len(points),'worst_sample_rest_m':where,
                    'pass_1mm':best+cover+.00001<=.001}
    print('[G38 COVERAGE]',name,round(best*1000,4),'upper',round((best+cover+.00001)*1000,4),flush=True)

out=Path('C:/Dev/Game/Working/Reviews/Operations/organs_v03/G38_work/fit_latest.json')
if '--out' in sys.argv:out=Path(sys.argv[sys.argv.index('--out')+1])
report={'file':bpy.data.filepath,'method':'Barycentric triangle grids; outside-distance-to-solid and distance-to-compound are 1-Lipschitz. Maximum sample plus grid cell diameter is a conservative bound. Internal compound caps are excluded by solid containment.',
        'outside':outside,'coverage':coverage,
        'summary':{'outside_2mm_pass':all(r['pass_2mm'] for r in outside.values()),
                   'coverage_1mm_pass':all(r['pass_1mm'] for r in coverage.values()),
                   'maximum_outside_bound_mm':max(r['certified_upper_outside_mm'] for r in outside.values()),
                   'maximum_uncovered_bound_mm':max(r['certified_upper_uncovered_mm'] for r in coverage.values())}}
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('[G38 FIT SUMMARY]',json.dumps(report['summary']),flush=True)
