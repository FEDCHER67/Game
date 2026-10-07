# Sausage Buddy — cargo bay animations

**Use the three `*_v03.blend` and `*_v03.fbx` files.** The folder keeps the requested `Cargo_v01` package name; numbered v03 files are the corrected delivery. v01/v02 exports and earlier authoring/review passes remain intact and are superseded. Files were created only inside this new folder. Existing sources, animations, Assets, WORK_SYNC.md and the Git index were not edited.

Original local FK and analytical IK animation, authored in Blender 5.2.1 LTS. No external motion take, paid generation or credits were used. The exact first lying pose is referenced from GetUp_FromBack_v02; the remaining performance is newly authored. Each editable Blend retains the original A v04 Body, Face, Outfit, rig, UVs, materials, shape-key data and skin weights. Facial shape-key animation is absent, following the existing animation-only pipeline; the emotional read comes from posture and skeletal motion. Each FBX contains one take, one armature, zero meshes and no extra root/leaf bones.

Rig `Buddy_Rig_Mixamo65`, root `mixamorig:Hips`, 65 bones. Names, order, hierarchy and bind matrices match Walk_v02, and A/B v04 share the same rest rig. 1 Blender unit = 1 metre; +Z is up. The source character faces -Y in rest; the final cargo sit faces **+X** after a 90° turn toward the side wall.

| Clip | Frames | Seconds | Loop | Maximum height above floor (m) | Sitting floor penetration (mm) | Largest half-frame local rotation (deg) |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| SitUp_Cargo_v03 | 1–64 | 2.1 | No | 1.074223 | 0.000 | 13.60 |
| Cargo_Sit_Idle_v03 | 1–121 | 4.0 | Yes | 1.029324 | 0.000 | 3.11 |
| Cargo_Knock_v03 | 1–85 | 2.8 | Yes | 1.028487 | 0.000 | 11.11 |

All source clips run at 30 fps. Sit-up hips never exceed 0.307701 m; the seated loops keep their hips at 0.108 m. The sit-up ends at the idle's first pose; the knock starts and ends there too, with **zero matrix difference**. Both source and FBX reimport loop seams are **exactly zero**. Glance and gesture motion eases at the loop boundaries; the duplicated end frame is retained for importing the full duration.

## Previews and author review

- **SitUp_Cargo_v03:** Supine hold, supported sit-up with a turn toward the cargo side wall, dazed wobble, right-temple rub, knee hug. [Contact sheet](Previews/SitUp_Cargo_v03/SitUp_Cargo/SitUp_Cargo_v03_contact_sheet.png), [30 fps playback](Previews/SitUp_Cargo_v03/SitUp_Cargo/SitUp_Cargo_v03.mp4).
- **Cargo_Sit_Idle_v03:** Floor sit with arms around the raised knees, alternating scared glances, breath and small trembling. [Contact sheet](Previews/Cargo_Sit_Idle_v03/Cargo_Sit_Idle/Cargo_Sit_Idle_v03_contact_sheet.png), [30 fps playback](Previews/Cargo_Sit_Idle_v03/Cargo_Sit_Idle/Cargo_Sit_Idle_v03.mp4).
- **Cargo_Knock_v03:** Turn toward the wall, close the right fist, knock three times, recoil and return to the same knee hug. [Contact sheet](Previews/Cargo_Knock_v03/Cargo_Knock/Cargo_Knock_v03_contact_sheet.png), [30 fps playback](Previews/Cargo_Knock_v03/Cargo_Knock/Cargo_Knock_v03.mp4).

Each contact sheet includes ten labeled times from side and three-quarter. Adjacent folders contain the 480×480 Cycles stills and a full 30 fps, 384×384 Eevee PNG sequence plus MP4. Final saved sources were rendered without regenerating their animations. The author inspected both views of all three current v03 clips; details and corrections are in `visual_review_v03.json`. Earlier Review_01 and Review_02 sheets are retained as process evidence, not current previews.

The early pass floated the pelvis above the floor. Corrections lower the seat, support the middle of the sit-up, tighten the knee hug, improve the temple rub, align the fist to the wall, and replace the moving knock IK transition with fixed hinge poses connected by smooth local quaternion arcs. The resulting strikes include torso twist, recoil and head trembling instead of moving only the arm. The looping wrist no longer acquires a different Euler branch during FBX baking. The final finger curl follows the posed palm axis, folding the fingers into a closed fist rather than sideways.

## Cargo placement and Unity import

The review floor is z=0 and the side wall is x=-0.65 m, extending to z=1.3 m. The seated hips lie at x=-0.30 m, y=0, z=0.108 m; the hoodie/back clears the wall by roughly 5 mm. The three fist contacts occur near 0.84, 1.22 and 1.63 seconds, with held contact and slower withdrawals. The animation keeps a small skin clearance at the wall for collision tolerance. Review floor/wall/camera/lights are not exported.

For a van floor 0.55 m above ground, place the animation's floor origin at that height. Keep the cargo actor's yaw aligned to the local wall described above; do not add another 90° turn to the authored motion. SitUp starts face up with head toward local +Y, matching GetUp_FromBack_v02 within 5.96e-7 matrix-component roundoff. It scoots the hips 0.30 m toward the side wall while turning into the seat. Retain those authored Hips translation/orientation curves; leave the rig object fixed and avoid applying the displacement twice during root-motion extraction.

Use Unity 6000.5.11f1, **Generic / Copy From Other Avatar** with the original A v04 Avatar, **Preserve Hierarchy**, and no animation compression, matching Walk_v02. Keep the `Buddy_Rig_Mixamo65/mixamorig:Hips/...` curve path and the full take. SitUp: Loop Time off. Idle and knock: Loop Time on. FBX settings match GetUp_Idle: selected armature only; -Z forward / Y up; apply units; no leaf bones; all 65 bones; bake animation at 0.5-frame steps; simplify 0; one action; no NLA strips. Armature returns to original rest before export so bind matrices remain unchanged.

This source-only brief does not include Unity import, ragdoll blending, network behaviour or gameplay acceptance; Assets was left untouched. Align ragdoll yaw/floor placement before blending into the supine animation target.

## Validation and provenance

`validation_v03.json` independently opens every saved Blend, samples at 120 Hz, measures all actual skinned Body/Face/Outfit vertices, checks original bone data/order/rest pose, mesh topology/weights/UV/material/shape-key signatures, finite transforms, positive determinants and quaternion key signs, then reimports each FBX. Sitting samples cover 0.97–2.10 s of SitUp and the entire loops; floor/height checks also cover every sample of the full sit-up. **Floor penetration is zero in all sampled frames**, not just sitting frames. Maximum height is 1.074223 m, leaving 0.125777 m below the 1.2 m brief limit.

Nonfinite values, reflected bones and adjacent quaternion sign flips are zero. Half-frame angular changes are below the documented 25° discontinuity gate. Imported bind-matrix error versus Walk_v02 is zero; maximum animated matrix-component error is 1.7918646e-05. Source and reimport seams are zero for both loops. Original review geometry is 14,176 triangles; exported geometry budget is zero. Geometry optimization is therefore inapplicable to the animation-only FBXs, and original source meshes were preserved.

`source_inspection_v01.json` records hashes of all pre-existing character-folder files, excluding Cargo_v01. `provenance_v03.json` records the brief, unchanged input/helper hashes, export/render settings and package-output hashes. The v01 validation correctly rejected a tiny imported knock wrist seam; v02 fixed that seam; v03 retains exact seams and also corrects finger flexion axes so the knock closes into a fist. v03 passes every gate. Earlier build/contact-sheet/validation script revisions are retained; use the current tools below.

## Reproduction

From the repository root, use Blender 5.2 headless with `--factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Cargo_v01/build_cargo_v08.py -- --check-only --revision 4`, followed by `-- --final --revision 4`. The builder refuses numbered source/export/report overwrites. Validate with `validate_cargo_v02.py -- --revision 4`; render saved sources with `render_cargo.py -- --revision 4 --movies`. Run `contact_sheets_v03.ps1 -ReviewRoot <absolute Previews/clip_v04 folder>` once for each clip. Encode each motion_frames sequence with FFmpeg at 30 fps and `-n` to refuse overwrites. Delivery documentation is specific to reviewed v03.
