"""Read-only inspection of the approved v03 source. Run in background Blender."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import organs_v03_lib as L

def bounds(ob):
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return [[min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)]]

bpy.context.view_layer.update()
objects = list(bpy.context.scene.objects)
print('SCENE', bpy.data.filepath, 'units', bpy.context.scene.unit_settings.scale_length, flush=True)
for o in objects:
    print('OBJECT', o.name, o.type, o.parent.name if o.parent else None,
          tuple(o.location), tuple(o.rotation_euler), tuple(o.scale),
          len(o.data.vertices) if o.type == 'MESH' else '', flush=True)

meshes = {o.name:o for o in objects if o.type=='MESH'}
bvhs = {n:L.bvh_of([o])[0] for n,o in meshes.items()}
ribs = [n for n in meshes if n.startswith(('RIB_', 'STERNUM_'))]
others = [n for n in meshes if n not in ribs and n!='SPINE_THORACIC']
audit = {}
for n in ribs:
    pts = [meshes[n].matrix_world @ v.co for v in meshes[n].data.vertices]
    rows = []
    for m in others:
        overlap = len(bvhs[n].overlap(bvhs[m]))
        ds = [bvhs[m].find_nearest(p)[3] for p in pts]
        rows.append({'name':m, 'triangle_crossings':overlap, 'sample_min_mm':round(min(ds)*1000,4)})
    audit[n]={'bounds':bounds(meshes[n]), 'nearest':sorted(rows,key=lambda r:r['sample_min_mm'])[:4],
              'crossings':[r for r in rows if r['triangle_crossings']]}
    print('FIT', n, json.dumps(audit[n]), flush=True)
out = Path('C:/Dev/Game/Working/Reviews/Operations/organs_v03/G38_work')
out.mkdir(exist_ok=True)
(out/'source_audit_v03.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
