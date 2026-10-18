"""Independent G38 validation, run against a saved blend in background Blender."""
import json
import math
import random
import sys
import types
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_measure as M
import g38_build_v03b as B
G=B.G;L=B.L
WORK=B.WORK
layout=json.loads((HERE.parent.parent/'Patient_v03/ORGANS_LAYOUT_v03.json').read_text(encoding='utf-8'))
T=Matrix(layout['table_rest_transform_rest_to_table_blender'])
cols=sorted([o for o in bpy.context.scene.objects if o.name.startswith('UCX_')],key=lambda o:o.name)
bones={o.name:o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('RIB_','STERNUM_'))}
anatomy={o.name:M.Mesh(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('ORGAN_','VESSELS_','DIAPHRAGM','AIRWAY_','SPINE_'))}
body=bpy.data.objects['REF_PatientBody_v02_rest'];body_mesh=M.Mesh(body)
temp=G.collection('G38_VALIDATION_ONLY')
posed,actualT=G.load_table_rest_body(temp);posed_mesh=M.Mesh(posed)
heads=[min(G.body_islands(o,with_size=True),key=lambda x:x[1])[0] for o in (body,posed)]

# Abdomen meshes are only appended into this disposable validation process.
abd=Path('C:/Dev/Game/ArtSource/Props/TABLE-ASTRA-001/v03/OperationAbdomen_v03.blend')
with bpy.data.libraries.load(str(abd),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.startswith(('ABDOMEN_','CORD_'))]
abd_obs=[]
for o in dst.objects:
    if o is not None and o.type=='MESH':
        p=o
        while p is not None:
            if p.name not in temp.objects:temp.objects.link(p)
            p=p.parent
        abd_obs.append(o)
bpy.context.view_layer.update()
abd_meshes={o.name:M.Mesh(o,T.inverted()) for o in abd_obs if o.name!='ABDOMEN_MASK'}

rows={o.name:M.mesh_health(o) for o in cols}
for n,row in rows.items():
    row['poses']={}
saved={tag:bpy.data.objects['RIBCAGE_HALF_'+tag].rotation_euler.copy() for tag in ('L','R')}
render_checks={}

for pose in ('closed','open35'):
    if pose=='open35':
        for tag,angle in [('L',35),('R',-35)]:bpy.data.objects['RIBCAGE_HALF_'+tag].rotation_euler.y=math.radians(angle)
        bpy.context.view_layer.update()
    bone_meshes={n:M.Mesh(o) for n,o in bones.items()}
    obstacles={**anatomy,**abd_meshes,'BODY_REST':body_mesh,'BODY_TABLE_REST':posed_mesh,**bone_meshes}
    for i,o in enumerate(cols):
        cm=M.Mesh(o);r={'organ_min_mm':1e9,'nearest_organ':None,'other_min_mm':1e9,'nearest_other':None,
                      'surface_intersections':[],'anatomical_containment':[]}
        for n,om in obstacles.items():
            if n==o.parent.name:continue
            d,cross=M.distance(cm,om)
            if d*1000<r['other_min_mm']:r['other_min_mm']=d*1000;r['nearest_other']=n
            if n in anatomy and n!='SPINE_THORACIC':
                if d*1000<r['organ_min_mm']:r['organ_min_mm']=d*1000;r['nearest_organ']=n
                if not cross and M.inside(om,cm.v.mean(axis=0)):r['anatomical_containment'].append(n)
            if cross:r['surface_intersections'].append(n)
            if n=='BODY_REST':r['body_rest_min_mm']=d*1000
            if n=='BODY_TABLE_REST':r['body_table_min_mm']=d*1000
        for key,h in zip(('head_rest','head_table'),heads):
            points=[Vector(p) for p in cm.v]
            r[key+'_inside_vertices']=L.inside_count(h,points)
            r[key+'_min_sample_mm']=min(h.find_nearest(p)[3] for p in points)*1000
        rows[o.name]['poses'][pose]=r
    render_checks[pose]={}
    for n,bm in bone_meshes.items():
        measurements={name:M.distance(bm,om)[0]*1000 for name,om in {**anatomy,**abd_meshes}.items()}
        render_checks[pose][n]={'distances_mm':measurements,'intersections':[name for name,d in measurements.items() if d==0]}
    print('[G38 VALIDATE]',pose,'finished',flush=True)

for tag in ('L','R'):bpy.data.objects['RIBCAGE_HALF_'+tag].rotation_euler=saved[tag]
bpy.context.view_layer.update()
col_meshes={o.name:M.Mesh(o) for o in cols}
gaps=[]
for tag in ('L','R'):
    count=max(int(n[-2:]) for n in bones if n.startswith('RIB_'+tag+'_'))
    for i in range(1,count):
        a=f'RIB_{tag}_{i:02d}';b=f'RIB_{tag}_{i+1:02d}';best=(math.inf,None,None)
        for ao in cols:
            if ao.parent.name!=a:continue
            for bo in cols:
                if bo.parent.name!=b:continue
                d,_=M.distance(col_meshes[ao.name],col_meshes[bo.name])
                if d<best[0]:best=(d,ao.name,bo.name)
        gaps.append({'a':a,'b':b,'clearance_mm':best[0]*1000,'parts':best[1:],'pass_8mm':best[0]>=.008})

# A continuous 8-mm sphere, seeded once; do not re-roll missed/undesirable rays.
table_meshes=[M.Mesh(o,T) for o in cols]
bb,owners=M.combined(table_meshes)
raw,raw_owners=M.combined(table_meshes+[M.Mesh(bpy.data.objects[n],T) for n in anatomy if n!='SPINE_THORACIC'])
allp=np.concatenate([m.v for m in table_meshes]);lo=allp.min(axis=0);hi=allp.max(axis=0)
rng=random.Random(38);probes=[]
for i in range(20):
    origin=[rng.uniform(float(lo[0]),float(hi[0])),rng.uniform(float(lo[1]),float(hi[1])),float(hi[2]+.15)]
    length=float(hi[2]-lo[2]+.30)
    filtered=M.sweep(bb,owners,origin,(0,0,-1),length)
    unfiltered=M.sweep(raw,raw_owners,origin,(0,0,-1),length)
    probes.append({'id':i+1,'origin_table_m':origin,'direction_table':[0,0,-1],
                   'length_m':length,'diameter_mm':8,'filtered':filtered,'unfiltered_bones_and_organs':unfiltered})

bone_health={n:M.mesh_health(o) for n,o in bones.items()}
report={'file':bpy.data.filepath,'distance_method':'triangle intersections + exact vertex-face / edge-edge minima, float64 segment math',
        'convex_tolerance_mm':.005,'colliders':rows,'bone_mesh_health':bone_health,'rib_gaps':gaps,
        'render_mesh_clearance':render_checks,
        'probe_seed':38,'probe_sampling':'uniform chest footprint in TABLE_REST, fixed top-camera direction (0,0,-1)',
        'probe_tests':probes,'table_transform_used':B.matrix(T),'actual_table_transform':B.matrix(actualT),
        'body_colliders':'No body/organ collider objects are present in this Blender source; Unity physics not run.',
        'summary':{'collider_count':len(cols),'all_convex':all(r['convex'] for r in rows.values()),
          'all_at_most_64_vertices':all(r['vertices']<=64 for r in rows.values()),
          'all_closed_triangulated':all(r['nonmanifold_edges']==0 and r['all_faces_triangles'] for r in rows.values()),
          'min_organ_clearance_closed_mm':min(r['poses']['closed']['organ_min_mm'] for r in rows.values()),
          'min_organ_clearance_open_mm':min(r['poses']['open35']['organ_min_mm'] for r in rows.values()),
          'all_rib_gaps_at_least_8mm':all(r['pass_8mm'] for r in gaps),
          'filtered_probes_pass':all(p['filtered'].get('status') is None and (p['filtered']['first_hit'] is None or p['filtered']['first_hit'].startswith(('UCX_RIB_','UCX_STERNUM_'))) for p in probes)}}
out=WORK/'validation_latest.json'
if '--out' in sys.argv:out=Path(sys.argv[sys.argv.index('--out')+1])
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('[G38 SUMMARY]',json.dumps(report['summary']),flush=True)
print('[G38 GAPS]',json.dumps(gaps),flush=True)
print('[G38 BODY]',[(n,r['poses']['closed']['surface_intersections']) for n,r in rows.items() if r['poses']['closed']['surface_intersections']],flush=True)
