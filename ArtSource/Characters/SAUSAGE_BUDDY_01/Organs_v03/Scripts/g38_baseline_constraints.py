"""Baseline feasibility checks, read-only v03 scene, no source writes."""
import json
import math
import sys
import types
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
G=types.ModuleType('v03_build_readonly'); G.__file__=str(HERE/'build_organs_v03.py')
src=Path(G.__file__).read_text(encoding='utf-8');exec(compile(src[:src.rfind('\nmain()')],G.__file__,'exec'),G.__dict__)
L=G.L
ref=bpy.data.objects['REF_PatientBody_v02_rest']
isl=G.body_islands(ref,with_size=True)
print('BODY_ISLANDS', [k for b,k in isl],flush=True)
for n in ['STERNUM_L','STERNUM_R','RIB_L_01','RIB_L_03','RIB_L_05']:
    ob=bpy.data.objects[n]; pts=G.surface_points(ob)
    for b,k in isl:
        inside=[(b.find_nearest(p)[3],list(p)) for p in pts if L.inside_count(b,[p])]
        print(n,k,'inside',len(inside),'max_depth',max(inside,default=None),flush=True)
coll=G.collection('G38_TEMP_REFERENCE')
posed,T=G.load_table_rest_body(coll)
isl2=G.body_islands(posed,with_size=True)
print('POSED_ISLANDS',[k for b,k in isl2],flush=True)
for n in ['STERNUM_L','STERNUM_R','RIB_L_01','RIB_L_03','RIB_L_05']:
    ob=bpy.data.objects[n];pts=G.surface_points(ob)
    for b,k in isl2:
        inside=[(b.find_nearest(p)[3],list(p)) for p in pts if L.inside_count(b,[p])]
        print('TABLE',n,k,'inside',len(inside),'max_depth',max(inside,default=None),flush=True)
for tag,angle in [('L',35),('R',-35)]:
    h=bpy.data.objects['RIBCAGE_HALF_'+tag];h.rotation_euler.y=math.radians(angle)
bpy.context.view_layer.update()
obs={n:L.bvh_of([bpy.data.objects[n]])[0] for n in ['ORGAN_LUNG_L','ORGAN_LUNG_R','ORGAN_HEART']}
for o in bpy.context.scene.objects:
    if o.name.startswith(('RIB_','STERNUM_')):
        b=L.bvh_of([o])[0]
        for n,bb in obs.items():
            ov=b.overlap(bb)
            if ov:print('OPEN_CROSS',o.name,n,len(ov),flush=True)
print('BASELINE_DONE',flush=True)
