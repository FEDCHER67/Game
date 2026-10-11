"""Add review meshes to a walk blend built with --source json (no Git LFS needed).

Blender 5.2 background (or `pip install bpy` + python):
  blender -b --factory-startup --python review_meshes_v04.py -- --blend Walk_v04.blend --out Walk_v04_review.blend [--variant A]

The cloud has no LFS copy of SAUSAGE_BUDDY_A_v04.blend, so the meshes are regenerated with the
character's own procedural builders (buddy_body / buddy_clothes, 'crowd' LOD = the v04 NPC budget)
and skinned to the rig in the walk blend with their procedural weights. The script checks the result
against shoe_soles_v04.json (shoe vertices and weights exported from the real A/B v04 blends) and
prints the deviation, so a review render can be trusted for contact. Review only: never exported.
"""
from pathlib import Path
import sys
import json
import argparse
sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
CHAR = HERE.parent.parent
sys.path.insert(0, str(CHAR))
import buddy_geo as G           # noqa: E402
import buddy_body as B          # noqa: E402
import buddy_clothes as C       # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--blend', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--variant', choices=('A', 'B'), default='A')
args = ap.parse_args(argv)
OUT = Path(args.out)
assert not OUT.exists(), f'Refusing to overwrite {OUT}'

bpy.ops.wm.open_mainfile(filepath=args.blend)
scene = bpy.context.scene
rig = bpy.data.objects['Buddy_Rig_Mixamo65']
action = rig.animation_data.action
rig.data.pose_position = 'REST'
col = bpy.data.collections.new('SausageBuddy_Review')
scene.collection.children.link(col)
G.COLLECTION = col
G.LOD = G.LODS['crowd']

skin = G.mat('Buddy_Skin', (236, 152, 106), 0.5, sss=0.12)
nose = G.mat('Buddy_Skin_Nose', (226, 128, 94), 0.45, sss=0.12)
inner = G.mat('Buddy_Skin_Inner', (204, 112, 80), 0.6)
body = B.build_body(skin, nose, inner)
face = B.build_face([G.mat('Buddy_Eye_White', (247, 247, 243), 0.2), G.mat('Buddy_Eye_Rim', (150, 92, 70), 0.5),
                     G.mat('Buddy_Pupil', (16, 14, 14), 0.12), G.mat('Buddy_Eye_Shine', (255, 255, 255), 0.1),
                     G.mat('Buddy_Brow', (86, 54, 40), 0.7), G.mat('Buddy_Mouth', (74, 36, 30), 0.6)])
garments = C.variant_a(body) if args.variant == 'A' else C.variant_b(body, face)
outfit = garments[0]
G.join(outfit, garments[1:])
outfit.name = 'Outfit'
outfit.data.name = 'Outfit'
for o in (body, face, outfit):
    o.parent = rig
    o.matrix_parent_inverse.identity()
    o.modifiers.new('Armature', 'ARMATURE').object = rig
    if o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks:
            k.value = 0.0

# Check against the real v04 shoes: nearest regenerated vertex for every exported sole vertex.
soles = json.loads((HERE / 'shoe_soles_v04.json').read_text())[args.variant]['soles']
names = {g.index: g.name for g in outfit.vertex_groups}
mine = [(outfit.matrix_world @ v.co, {names[g.group]: g.weight for g in v.groups if g.weight > 1e-4})
        for v in outfit.data.vertices if (outfit.matrix_world @ v.co).z < 0.10]
pos_err = w_err = 0.0
for side in ('Left', 'Right'):
    for v in soles[side]:
        co = Vector(v['co'])
        p, w = min(mine, key=lambda m: (m[0] - co).length)
        pos_err = max(pos_err, (p - co).length)
        keys = set(w) | set(v['w'])
        tot_a, tot_b = sum(w.values()) or 1.0, sum(v['w'].values()) or 1.0
        w_err = max(w_err, max(abs(w.get(k, 0.0) / tot_a - v['w'].get(k, 0.0) / tot_b) for k in keys))
print('REVIEW_MESH_SHOE_MATCH', json.dumps({'variant': args.variant, 'max_position_error_m': pos_err,
                                            'max_weight_error': w_err,
                                            'vertices': {k: len(o.data.vertices) for k, o in
                                                         (('Body', body), ('Face', face), ('Outfit', outfit))}}), flush=True)

rig.data.pose_position = 'POSE'
rig.animation_data.action = action
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print('REVIEW_BLEND_READY', OUT, flush=True)
