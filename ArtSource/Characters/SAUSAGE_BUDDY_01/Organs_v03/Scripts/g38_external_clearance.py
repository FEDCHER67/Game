"""Supplementary external-collider minima and fixed-head section evidence."""
import json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
import g38_measure as M
revision=sys.argv[sys.argv.index('--revision')+1] if '--revision' in sys.argv else 'v03b'
v=json.loads((B.WORK/('validation_four_final.json' if revision=='v03c' else 'validation_final.json')).read_text());cols=[o for o in bpy.context.scene.objects if o.name.startswith('UCX_')]
out={}
for pose in ('closed','open35'):
    for tag,angle in [('L',35),('R',-35)]:bpy.data.objects['RIBCAGE_HALF_'+tag].rotation_euler.y=math.radians(angle if pose=='open35' else 0)
    bpy.context.view_layer.update();meshes={o.name:M.Mesh(o) for o in cols};rows={}
    for o in cols:
        original=v['colliders'][o.name]['poses'][pose];best=original['other_min_mm']/1000;name=original['nearest_other']
        if best>0:
            for other in cols:
                if other.parent==o.parent:continue
                d,_=M.distance(meshes[o.name],meshes[other.name],upper=best)
                if d<best:best=d;name=other.name
        rows[o.name]={'min_external_mesh_mm':best*1000,'nearest_external_mesh':name}
    out[pose]=rows
for tag in ('L','R'):bpy.data.objects['RIBCAGE_HALF_'+tag].rotation_euler.y=0
bpy.context.view_layer.update()
tmp=B.G.collection('G38_TEMP_HEAD_EVIDENCE');posed,T=B.G.load_table_rest_body(tmp)
heads=[min(B.G.body_islands(o,with_size=True),key=lambda x:x[1])[0] for o in (bpy.data.objects['REF_PatientBody_v02_rest'],posed)]
sections=[]
for tag in ('L','R'):
    lo,hi=map(Vector,B.world_bounds([bpy.data.objects['STERNUM_'+tag]]))
    xy_radius=math.hypot((hi.x-lo.x)/2,(hi.y-lo.y)/2)
    for z in (1.178,1.165,1.15,1.135,1.12,1.105):
        center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,z))
        rows=[]
        for name,h in zip(('REST','TABLE_REST'),heads):
            d=h.find_nearest(center)[3];inside=bool(B.L.inside_count(h,[center]))
            rows.append({'pose':name,'center_inside':inside,'center_boundary_distance_mm':d*1000,
              'section_entirely_inside_proved':inside and d>xy_radius,'lower_inside_depth_bound_mm':(d-xy_radius)*1000 if inside else None})
        sections.append({'sternum':'STERNUM_'+tag,'z_m':z,'section_radius_mm':xy_radius*1000,'checks':rows})
out['sternum_existing_bounds_cross_sections']=sections
(B.WORK/f'external_clearance_{revision}.json').write_text(json.dumps(out,indent=2));print('EXTERNAL_CLEARANCE_DONE',flush=True)
