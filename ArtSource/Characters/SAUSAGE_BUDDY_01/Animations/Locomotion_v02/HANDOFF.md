# Sausage Buddy Walk: handoff (Locomotion_v02), 2026-10-07

Re-authored walk replacing GPT's `Locomotion_v01/Walk_v02` (Fedya: «переделай сам ходьбу»).
Stopped on request at a logical point. **`Walk_v03` is iteration 1 of the new walk.** It is usable and
validated. It has one known 1.3 mm contact defect and has had one visual review pass (stills and contact
sheet), not the planned 2-3 motion iterations. The next revision must be **`Walk_v04`**: never overwrite v03.

> **Update 2026-10-10: `Walk_v04` (iteration 2) is done; see `README.md`.** It fixes items 1-4 of section 4
> (marching knee, crouch, indistinct up, 1.3 mm skim -> 0.73 mm, all validation checks pass), with 3 render
> review passes and close-ups of hand/belly and the shoe bend (item 5). Same timing, in place, exact loop, same
> 65 bones, same FBX/Unity settings. Built in the cloud without LFS, so only text was committed:
> `walk_v04_motion.py`, `build_walk_v04.py` (use it instead of `build_walk_v03.py` in section 6),
> `review_meshes_v04.py` (no-LFS review meshes), `review_sheet_v04.py`, `build_report_v04.json`,
> `validation_v04_jsonmode.json`. `Walk_v04.blend/.fbx`, blend-mode `validation_v04.json` and the previews must be
> built locally with the README commands. Still open: real-time look at the MP4s, items 6-8, Unity (step 5 of section 5).
> The next revision is `Walk_v05`.

## 1. Files in this folder

| File | What |
| --- | --- |
| `walk_v04_motion.py`, `build_walk_v04.py` | **Walk_v04** motion and build (current). `README.md` lists the changes, numbers and review passes. |
| `review_meshes_v04.py`, `review_sheet_v04.py` | No-LFS review meshes (procedural A/B v04 rebuild, shoes verified against `shoe_soles_v04.json`) and Pillow review sheets/onion skins. |
| `walk_v03_motion.py` | **The motion design (v03).** All parameters at the top; pure maths, no file I/O. |
| `build_walk_v03.py` | Builds the action and saves a blend. `--source blend` (A v04 .blend, keeps meshes) or `--source json` (no LFS). |
| `export_walk_v03.py` | Blend -> animation-only FBX (same settings as Walk_v02; rest-pose bind). |
| `validate_walk_v03.py` | Writes `validation_<rev>.json` (checks in section 4). `--source blend` or `--source json`. |
| `render_walk_v03.py` | Review frames (side, three-quarter, front) on a treadmill checker floor that moves at 1.5 m/s. Needs the meshes, so it needs the LFS A v04 blend. |
| `make_previews_v03.py` | System Python + Pillow + ffmpeg: MP4s (30 fps, 6 loops) and contact sheet. |
| `export_rig_json.py` | Produced the two JSON files below from the A/B v04 blends (already run; refuses to overwrite). |
| `rig_Buddy_Mixamo65.json` | Skeleton as text: 65 bones in parent-first order with name, parent, edit head/tail/roll, flags, rest `matrix_local`; armature object transform; source hashes; FBX export settings. |
| `rebuild_rig_from_json.py` | Rebuilds the armature in bpy from that JSON (`build()`); standalone run checks the rest matrices. |
| `shoe_soles_v04.json` | Both shoes of A and B (Outfit vertices below 0.10 m) with skin weights. Used for the sole-hull rolls and for no-LFS contact validation. |
| `Walk_v03.blend` / `Walk_v03.fbx` | Iteration 1 deliverable (blend keeps the A v04 meshes for review). |
| `validation_v03.json` | Full validation (blend mode, real skinned meshes A and B). `validation_v03_jsonmode.json`: same via the no-LFS path. |
| `build_report_v03.json` | Design diagnostics: leg reach, knee range, sole hull chains, per-frame phase table. |
| `Previews/Walk_v03_side.mp4`, `_threequarter.mp4`, `_side_threequarter.mp4`, `_contact_sheet.png` | Review media. `Previews/frames_v03/` holds the 40 source PNGs (19 MB, regenerable; optional to commit). |
| `*.log` | Console output of the runs above. |

Read-only inputs (never modified): `../../SAUSAGE_BUDDY_A_v04.blend/.fbx`, `../../SAUSAGE_BUDDY_B_v04.blend/.fbx`
(Git LFS), and helper modules `../../buddy_anim.py` (`pose_from_joints`), `../../buddy_rig.py` (`key_frames`,
`ordered`, `fcurves_of`), `../../buddy_render.py` + `../../buddy_geo.py` (studio for renders). These helpers are plain text in git.
Scripts set `sys.dont_write_bytecode`, so no `__pycache__` is written into the character folder.

## 2. What v03 does (changes vs GPT's v02, and why)

Timing kept identical to v02 so it is a drop-in replacement. Frames 1-21 at 30 fps, frame 21 == frame 1,
loop 0.6667 s, 1.5 m/s, stride 1.0 m (two 0.5 m steps). Left heel strike at frame 1, right at frame 11.

| | v02 (GPT) | v03 |
| --- | --- | --- |
| Feet | flat the whole stance; 6 cm lift | heel strike with toe up 24 deg, forefoot slap within 1.4 frames, heel peel from 30 % of the cycle with the **shoe bending at the ball** (ToeBase planted, 42 deg), roll over the toe tip (13 deg), C1 lift-off; toe-out 7 deg |
| Contact maths | ankle on a line | every contact phase is a pure rotation about a ground point that travels with the ground. Pivots = convex hull of the real sole vertices (`shoe_soles_v04.json`), so planted soles don't slide or sink |
| Bob | 5 cm sine | 5.8 cm key-curve bob: quick drop into **down** 1.6 frames after contact, springy rise, hang at **up** (hips 0.734-0.792 m, rest 0.82) |
| Hips | yaw 3 deg | lateral sway +/-2.2 cm over the support foot, swing-side drop 4.5 deg, yaw 6 deg, forward tilt on the down |
| Legs | near straight | bent-knee cartoon stance (knee 29-52 deg), knee lift at passing (up to 95 deg), hinge IK with one shared thigh/shin axis (no knee twist), max reach 96.9 % |
| Torso/head | tiny sines | chest counter-yaw 5.5 deg and counter-roll 3.2 deg against the pelvis, sausage-body fold 2.6 deg after the down (1.2-frame lag); head nod 4 deg lagging 2.6 frames, chin up 4 deg, bobble roll lag 2 frames |
| Arms | +/-18 deg, stiff hands | +/-25 deg swing in a slightly inward plane, elbow 18-32 deg (bends more forward), forearm and hand each lag 1.6 frames (loose wrists), wrist flex 12 deg, relaxed finger curl, shoulders shrug/roll with lag |

Every channel is a periodic key curve: cubic Hermite with flat tangents on extremes, like auto-clamped keys.
Curves are keyed on contact/down/passing/up phases, not plain sines (`Loop` in `walk_v03_motion.py`).
Keys are written every half frame (41 per curve), quaternion, linear, like v02. The action digest
`b5bf1d88ac63...cbbbf62` is identical across reruns and across `--source blend` / `--source json`.

## 3. Validation of v03 (`validation_v03.json`)

| Check | Result |
| --- | --- |
| A/B v04 sources unchanged (sha256) | pass |
| One take `Walk`, frames 1-21; FBX take `Buddy_Rig_Mixamo65\|Walk` | pass |
| Keys finite, quaternion sign flips | pass, 0 flips; largest step 9.95 deg per half frame (LeftFoot slap) |
| Loop seam | frame 21 == frame 1 exactly (0.0); seam velocity jump 0.026 < largest interior change 0.108 |
| Penetration (lowest vertex, A and B, 120 Hz) | -0.52 mm (limit 1 mm; source rest sole is -1.0 mm) |
| Support sole height error in stance | 0.52 mm |
| Support slide (ground-frame drift of touching sole vertices inside stance) | 0.72 mm at 120 Hz (0.47 on keys, 0.92 at 240 Hz) |
| **Touchdown/lift-off skim** (same drift including runs crossing into the swing) | **1.31 mm: FAIL (target <= 1 mm)** |
| FBX bones vs Walk_v02.fbx | 65 bones, names/parents/order identical, bind matrices identical (0.0); 1.6e-5 vs original A FBX |
| FBX pose vs blend | 1.1e-3 max component (RightShoulder at f17, ~0.06 deg Euler conversion), tolerance 2e-3 |
| Python skinning vs Blender meshes | identical to ~3e-9 m, so the no-LFS contact check is trustworthy |

The failing skim comes from the toe tip at lift-off (frame ~12.7). The swing joins the stance C1-tangentially,
so the tip leaves the floor with ~zero vertical speed. Linear interpolation between the half-frame keys
12.5 and 13.0 then moves it 1.3 mm while it is still < 1 mm above the floor. It is invisible at game scale but it is
the one open validation item.

## 4. What still looks wrong / not yet reviewed

Judged from the contact sheet and a low-res filmstrip only. The MP4s were rendered but not yet reviewed critically for timing.
1. Knee lift at passing is high (knee 95 deg, `SWING_LIFT` 7.5 cm) and reads a bit "marching". Try 0.05-0.06.
2. Stance stays crouched (stance knee never straighter than 29 deg). Can read "sneaky" rather than bouncy.
   Try `BOB_CENTER` -0.045 and a straighter up pose, watching reach (now 96.9 % at the up).
3. **Up** is not distinct enough from **passing** in side view. Shift the `BOB_KEYS` top a bit later/higher, plus a stronger toe push.
4. The touchdown/lift-off skim above.
5. Forward-swinging hand vs hoodie belly/pocket not inspected close up. Shoe bend at the ball (42 + 13 deg) not
   inspected for skinning pinch.
6. Head nod/bobble and hood follow-through only seen in stills.
7. Side-view treadmill checker is visually busy; lower its contrast for final previews.
8. Not yet imported into Unity. README.md (EN + RU summary) and a v02-vs-v04 comparison sheet are still to do.

## 5. Planned next (iteration 2 -> Walk_v04)

1. In `Foot.swing()` add small vertical velocities at the ends, e.g. `LIFT_VZ` +0.3 m/s added to `dlift0`
   and `LAND_VZ` -0.3 m/s to `dland1` (scaled by `D`). The toe pops off and the heel plants with a tiny
   accent, which removes the skim. If not enough, add quarter-frame keys around `T_OFF` and the strike.
2. Tune items 1-3 of section 4, review the MP4 at 30 fps and at 0.5x and 1.4x speed (Unity plays speed/1.5).
   Iterate at least twice on anything stiff or twitchy.
3. Close-up renders of hand vs belly and of the shoe bend. Fix by `ARM_OUT_FWD`/`ARM_CROSS`, `BALL_END`.
4. Build/export/validate v04 (all checks green), render previews, write README.md with a Russian summary.
5. Lead: Unity import and in-game check.

## 6. Commands

Windows (local, Git Bash), from this folder:
```
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
"$BL" -b --factory-startup --python build_walk_v04.py -- --out Walk_v04.blend --report build_report_v04.json
"$BL" -b --factory-startup --python export_walk_v03.py -- --blend Walk_v04.blend --fbx Walk_v04.fbx
"$BL" -b --factory-startup --python validate_walk_v03.py -- --rev v04
"$BL" -b --factory-startup --python render_walk_v03.py -- --blend Walk_v04.blend --out Previews/frames_v04 --samples 16 --res 640 720
python make_previews_v03.py --frames Previews/frames_v04 --stem Walk_v04
```
Cloud without Git LFS (Blender 5.2.x on PATH). Only `.py` and `.json` files are needed:
```
blender -b --factory-startup --python build_walk_v04.py -- --source json --out Walk_v04.blend
blender -b --factory-startup --python export_walk_v03.py -- --blend Walk_v04.blend --fbx Walk_v04.fbx
blender -b --factory-startup --python validate_walk_v03.py -- --rev v04 --source json
blender -b --factory-startup --python rebuild_rig_from_json.py            # optional: rig self-check
```
Verified on 2026-10-07 in a scratch tree with LFS pointer stubs instead of the blends/FBX: same action digest,
FBX exported, identical contact metrics; source-hash and Walk_v02.fbx comparisons report `skipped`/fall
back to the rig JSON. Renders are not possible without the LFS meshes. Use the numbers, or ask the lead to render locally.
All scripts refuse to overwrite existing outputs; pass new `--out`/`--rev` names.

## 7. Conventions to keep

- Rig `Buddy_Rig_Mixamo65`, 65 bones, root `mixamorig:Hips`, faces -Y, left = +X, Z up, metres. A and B
  share the skeleton (verified identical). Do not modify A/B v04 sources.
- In place: no net horizontal root motion (hips mean x/y = 0, forward range 0). Lateral sway and vertical bob
  on `mixamorig:Hips` are fine: prefabs have Apply Root Motion off and no root-motion bone.
- 30 fps; cycle 0.6-0.75 s (now 20 frames); stride = 1.5 m/s x cycle; frame N+1 duplicates frame 1 exactly.
- Single take `Walk`; FBX animation-only, rest pose as bind pose, settings as in `export_walk_v03.py`.
- Unity import (copy from `Assets/OnlyVolunteers/Characters/SausageBuddy/Animations/Walk_v02.fbx.meta`):
  Generic, Copy From Other Avatar = A v04 avatar (guid `c9bf60023bda34f4ea85893f556f7edf`), **Preserve
  Hierarchy on**, Optimize Game Objects off, Anim. Compression Off, Resample Curves on; clip `Walk`,
  take `Buddy_Rig_Mixamo65|Walk`, first frame 0, last frame N (20), Loop Time on, Loop Pose off, Root
  Transform Position (Y) based upon Original. Controller `SausageBuddy_Greybox.controller` (guid
  `d8645f8f609119a47864f840421a0401`) state `Walk`. CrowdWalker/GreyboxNpc/GreyboxWalker play it at ground speed / 1.5.
- New revisions get new numbers (`Walk_v04`, ...), with matching validation, previews and logs.

## 8. Acceptance criteria

- Look: funny, bouncy cartoon walk with personality for dumb comic sausage NPCs, readable and not clownish.
  Clear contact/down/passing/up, bouncy bob with slight hip sway, overlapping arms with loose wrists, small head
  nod, spine follow-through, clean plants, snappy but not twitchy, seamless loop. Fedya approves from the MP4s
  and in game.
- Numbers (`validate_walk_v03.py`, all green): exact seam; no NaN/flips; penetration, support height error,
  support slide and touchdown/lift-off skim each <= 1 mm for A and B; FBX bones identical to Walk_v02.fbx
  (65, root Hips); one take; FBX pose matches blend; sources unchanged.
- Unity: imports with the settings above, no missing curve paths on both prefabs, CrowdWalker at ~1.5 m/s
  looks planted.

## Кратко по-русски

Ходьба переделана заново (итерация 1 = `Walk_v03`). Добавлены удар пяткой с поднятым носком, перекат через
носок со сгибом кеда, пружинистый «баунс» (вниз после контакта, зависание вверху), покачивание таза, руки с
захлёстом и расслабленными кистями, кивок головы и инерция «тела-сосиски». Опорная стопа не скользит (0,72 мм), петля
точная, кости совпадают с Walk_v02. Осталось: убрать касание носком 1,3 мм при отрыве, немного снизить подъём
колена и «присед», ещё 2 итерации по видео, затем Unity. Всё собирается из текстовых JSON без LFS (раздел 6).
