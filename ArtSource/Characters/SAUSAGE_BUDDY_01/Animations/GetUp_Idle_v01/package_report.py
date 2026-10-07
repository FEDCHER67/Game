"""Finalize English delivery documentation from measured validation, without overwrite."""
from pathlib import Path
import json,hashlib,datetime
HERE=Path(__file__).resolve().parent;SRC=HERE.parent.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
v=json.loads((HERE/'validation_v02.json').read_text(encoding='utf-8'))
assert v['pass'],'Cannot package failed validation'
assert not (HERE/'README.md').exists() and not (HERE/'provenance_v02.json').exists()
descriptions={
    'GetUp_FromBack':'Neutral supine start; sit up, dazed head wobble, palm brace, tuck into a crouch, push to standing and settle.',
    'GetUp_FromBelly':'Neutral prone start; place palms, push chest up, gather knees, half-kneel, stand with a dazed sway and settle.',
    'Idle_Variant_A':'Bored weight transfer, small breath and two sideways looks.',
    'Idle_Variant_B':'Three impatient right-foot taps, then a right-temple scratch and relaxed return.'}
rows=[];links=[]
for stem,r in v['clips'].items():
    name=stem[:-4];path=HERE/'Previews'/stem/name/(stem+'_contact_sheet.png');assert path.exists(),path
    rows.append(f"| {stem} | 1–{r['frames'][1]} | {r['duration_s']:.1f} | {'Yes' if r['loop'] else 'No'} | {r['standing_max_sole_penetration_m']*1000:.3f} | {r['standing_support_max_ground_error_m']*1000:.3f} | {r['max_quaternion_key_step_deg']:.2f} |")
    links.append(f"- **{stem}:** {descriptions[name]} [Contact sheet](Previews/{stem}/{name}/{stem}_contact_sheet.png); side and three-quarter PNGs are in the adjacent folders.")
maxpose=max(r['fbx_reimport']['max_animated_world_matrix_error'] for r in v['clips'].values())
maxidle=max(r['idle_end_matrix_error'] for r in v['clips'].values())
maxseam=max(r['fbx_reimport']['loop_seam_max_matrix_component_error'] for r in v['clips'].values() if r['loop'])
text=f'''# Sausage Buddy — get-ups and idle variants

**Current deliverables: the four `*_v02.blend` and `*_v02.fbx` files in this folder.** v01 files are retained as the initial review revision; use v02. No input model, existing animation, Unity asset, WORK_SYNC.md or Git index was changed by this task.

Original local animation, authored in Blender 5.2.1 LTS using character-frame joint rotations and analytical two-bone IK. No downloaded/mocap take, paid generator or external motion was used. Each editable Blend contains the unchanged original A v04 Body, Face and Outfit with one skeletal action. Each FBX is animation-only, with one take, zero meshes, no extra root or leaf bones. Facial shape-key tracks are deliberately absent, matching Walk_v02.

Rig: `Buddy_Rig_Mixamo65`; root bone: `mixamorig:Hips`; 65 bones. Character faces Blender -Y, +X is left, +Z is up; 1 unit = 1 metre. Bone order, names, hierarchy and imported bind matrices match Walk_v02. A/B v04 have identical rest rigs. Original A/B Blend/FBX and Walk_v02 hashes remain unchanged.

| Clip | Frames | Seconds | Loop | Standing penetration (mm) | Support sole error (mm) | Largest half-frame local rotation (deg) |
| --- | --- | ---: | --- | ---: | ---: | ---: |
{chr(10).join(rows)}

All clips run at 30 fps. The get-ups end at the existing Idle frame-1 pose (maximum matrix component difference {maxidle:.8g}, floating-point conversion). Both idles start at that same pose; their last frames duplicate their first with **exact matrix equality**. They also ease their motion to zero at the seam. Imported FBX loop seam error is at most {maxseam:.8g}.

Get-ups have zero net horizontal hips displacement, and the maximum horizontal range across both is {max(max(r['hips_horizontal_range_m']) for r in v['clips'].values() if not r['loop'])*1000:.6f} mm (floating-point noise). Vertical recovery is authored in the Hips curves. Idle A transfers weight through {max(v['clips']['Idle_Variant_A_v02']['hips_horizontal_range_m'])*1000:.2f} mm horizontally; B through {max(v['clips']['Idle_Variant_B_v02']['hips_horizontal_range_m'])*1000:.2f} mm. Neither travels forward, and both return to their starting hips position.

## Visual review

{chr(10).join(links)}

Each contact sheet contains ten labeled times from the side and the same ten from three-quarter. The author inspected both views of every current clip. Early review sheets/logs are retained as provenance. Corrections include whole-body lying orientation, horizontal bracing palms, a continuous IK hinge-plane roll, an eased lying/standing arm transition, and a joint-authored scratch arc that avoids an IK singularity. No reviewed model revision was overwritten.

## Unity import and recovery alignment

Use Unity 6000.5.11f1, **Generic**, **Copy From Other Avatar** with the original A v04 avatar, **Preserve Hierarchy**, no animation compression. Preserve the `Buddy_Rig_Mixamo65/mixamorig:Hips/...` curve path. Match Walk_v02's unit/axis settings. FBX takes are named `Buddy_Rig_Mixamo65|<clip>` (Blender's reimport may prepend the rig name again).

Get-ups: Loop Time off; retain authored Hips height and orientation curves. Idles: Loop Time on over the full take, including the duplicate end frame. The rig object stays fixed at the original floor origin; no extra root-motion node is added. Decide Animator root-motion extraction during integration so it does not apply the recovery height twice.

The first frames are held briefly for blending from ragdoll. Back starts face up with the head toward local +Y; belly starts face down with the head toward local -Y. Align the actor's yaw and floor placement to that lying direction before the ragdoll-to-animation blend. The final pose faces local -Y. First hips heights: back {v['clips']['GetUp_FromBack_v02']['first_hips_height_m']:.4f} m; belly {v['clips']['GetUp_FromBelly_v02']['first_hips_height_m']:.4f} m. These poses are animation targets, not a guarantee of contact on arbitrary terrain.

This source-only task did not import or modify Assets. Unity import, ragdoll blending, network behaviour and player acceptance remain integration checks; Blender previews are not proof of those outcomes.

## Validation and provenance

`validation_v02.json` samples every clip at 120 Hz, measures actual skinned shoe vertices, checks exact source rig/mesh/topology/weights, Idle alignment, finite transforms, positive bone determinants and continuous quaternion key signs, and reimports each FBX. Standing samples cover 1.7 s through the end of each recovery and the full idles; B's lifted tapping foot is excluded from support-ground-error measurements but included in penetration measurements. Feet and floor-stage body clearance are also reported over the entire get-ups. The rapid cartoon sit-to-crouch motion is retained; all half-frame angular steps are below the documented 25-degree discontinuity gate.

FBX imported animated world-matrix component error is at most {maxpose:.8g}; bind-matrix difference from Walk_v02 is zero. Nonfinite components, mirrored bone samples and adjacent quaternion sign flips: zero. Measurement thresholds and scope are explicit in `validate_getups.py`; the original v01 partial validation predates the strengthened angular gate and is superseded.

Across the full get-ups, including lying/transition contact, the largest all-mesh floor penetration is {max(r['all_mesh_max_floor_penetration_m'] for r in v['clips'].values() if not r['loop'])*1000:.3f} mm. This occurs outside the standing interval; standing shoe results are listed separately above.

`source_inspection_v01.json` records the exact Idle reference, source hashes, 14,176 original review-mesh triangles and identity mesh scales. Exported geometry budget is zero triangles; geometry/material/UV optimization does not apply to these animation-only FBXs, and the original skinned meshes were preserved. `provenance_v02.json` records input, script, deliverable and preview hashes.

## Reproduction

From this folder, run Blender 5.2 headless with `--factory-startup --python build_getups.py -- --check-only --revision 3`, then `-- --final --preview --revision 3` for a new, unused revision. The script refuses to overwrite numbered Blends, FBXs, authoring reports or PNGs. Use `validate_getups.py -- --revision 3` for source/reimport checks. Create contact sheets with `contact_sheets.ps1 -ReviewRoot <absolute Previews/clip_v03 folder>`. Original v04 sources are read-only inputs. Documentation finalization is specific to this delivery's v02 validation.
'''
(HERE/'README.md').write_text(text,encoding='utf-8')
files={str(p.relative_to(HERE)).replace('\\','/'):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and (
    p.name.endswith(('_v02.blend','_v02.fbx')) or ('Previews' in p.parts and '_v02' in str(p)) and p.suffix=='.png' or
    p.name in ('build_getups.py','validate_getups.py','inspect_getups.py','inspect_motion.py','contact_sheets.ps1','package_report.py','README.md','validation_v02.json'))}
provenance={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'brief_path':r'C:\Users\Zeyo-ne\.ai-bridge\req_buddy_getups.md',
    'brief_sha256':sha(Path(r'C:\Users\Zeyo-ne\.ai-bridge\req_buddy_getups.md')),
    'authoring':'Original local FK/analytical IK; no external motion, generation service or paid credits',
    'blender':'5.2.1 LTS (9e2066aef7ef)','current_revision':'v02','first_review_revision_retained':'v01',
    'source_hashes':json.loads((HERE/'source_inspection_v01.json').read_text(encoding='utf-8'))['source_sha256'],
    'readonly_helpers':{n:sha(SRC/n) for n in ('buddy_anim.py','buddy_rig.py','buddy_render.py','buddy_geo.py')},
    'export_settings':{'fps':30,'types':['ARMATURE'],'selection_only':True,'leaf_bones':False,'deform_only':False,
        'all_actions':True,'nla_strips':False,'step_frames':.5,'simplify_factor':0,'forward':'-Z','up':'Y','apply_unit_scale':True,
        'original_rest_pose_before_export':True,'meshes_exported':0,'actions_per_export':1},
    'render_settings':{'engine':'Cycles','samples':12,'denoising':True,'resolution':[480,480],'views':['side','three_quarter'],
        'view_transform':'Standard','exposure':-.85},'outputs_sha256':files,'unity_import_or_playtest_performed':False,
    'visual_review':'Both views and the contact sheet of each v02 inspected by the author before delivery'}
(HERE/'provenance_v02.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
print('PACKAGE_DOCUMENTED',len(files),'hashed outputs')
