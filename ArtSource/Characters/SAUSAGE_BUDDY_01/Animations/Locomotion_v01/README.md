# Sausage Buddy — Walk

**Current deliverables: `Walk_v02.blend` and `Walk_v02.fbx`.**

Original walk authored locally using analytical two-bone IK and quaternion keys. No downloaded motion, Mixamo source take, external generation, or paid service was used. The editable blend retains the original A v04 Body, Face and Outfit geometry and weights. A/B v04 have identical skeletons. Source hashes are recorded in `source_inspection.json`; they remain unchanged.

- Rig object: `Buddy_Rig_Mixamo65`; root bone: `mixamorig:Hips`; 65 bones.
- Blender action: `Walk`. FBX take: `Buddy_Rig_Mixamo65|Walk`.
- Frames 1–21 at 30 fps. Frame 21 duplicates frame 1. Loop duration: 20/30 s.
- Nominal forward pace: **1.5 m/s**. Two 0.5 m steps per cycle; 1 m stride.
- Each foot has 55% stance, giving 10% double support. Planted feet move backward at 1.5 m/s in character space. Swing uses 6 cm sole clearance; arms counter-swing by 18 degrees. Root has 5 cm vertical motion and no horizontal motion.
- Animation-only FBX, no meshes, no extra takes, no extra bones. Original names, hierarchy, rest matrices, topology and weights are preserved.

## Unity import

Use Generic and the A v04 avatar via Copy From Other Avatar. Enable **Preserve Hierarchy** so paths retain `Buddy_Rig_Mixamo65/mixamorig:Hips/...`. Loop the full take; locomotion playback multiplier is actual ground speed / 1.5. The parent integration checks runtime transitions and both character variants.

## Evidence

`Previews/Walk_v02.mp4` shows six cycles at the authored speed, side and three-quarter views. The GIF loops one cycle; `Walk_v02_contact_sheet.png` shows the contact, support, passing and late swing poses. These renders use the same authored animation in v01 and v02; v02 changes FBX bind-pose export only.

`validation_v02.json` measures the saved source at 120 Hz and reimports the FBX:

| Check | Result |
| --- | --- |
| Frame 1/21 seam | Exact matrix match |
| Max stance sole error / penetration | 0.525 mm |
| Max stance backward speed error | 0.0153 m/s |
| Max swing sole clearance | 60 mm |
| Horizontal hips range | Below 0.000002 mm |
| Source A/B blend and FBX hashes | Unchanged |
| A original mesh, topology, weights and rest pose | Exact match |
| Imported FBX hierarchy | Exact match with original character FBX |
| Imported bind matrix component difference | At most 0.0000162 |
| Imported animated world matrix component difference | At most 0.0000177 |

v01 is retained as the first review revision. Its animation is identical, but the unskinned FBX inherited the first walk pose as its default bind pose. v02 resets the rig to the original rest pose before baking Walk; use v02 for integration.

## Reproduction

Run `build_walk.py` in Blender 5.2 background with `-- --final --revision 3` (or a new unused revision). Existing numbered blend and FBX files are never overwritten. `render_walk.py` reproduces the review frames from v01's identical animation. `validate_walk.py -- --v02` checks the current deliverable. The original source files are read-only inputs.
