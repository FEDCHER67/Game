# Idle_Knock_v03 — handoff (stop point 2026-10-07)

The work stopped at the lead's request so the set can move to cloud Claude sessions. Everything below can be regenerated deterministically from the A v04 rig, or from the JSON export of it (no Git LFS needed). Two independent runs, one through the .blend and one through the JSON, gave byte-identical authored traces.

## 1. State per clip

| Clip | State | What still looks wrong / next step |
| --- | --- | --- |
| **Idle_Stand_v03** (4.0 s loop) | **Delivered**: `.blend` + `.fbx` + authoring JSON + `validation_Idle_Stand_v03.json` (21/21) + MP4 side/three-quarter (3 loops each) + contact sheet. Three review passes are in `Previews/Review_01..03`. | Not yet seen by Fedya. It is intentionally calm (it is the default idle). If he finds it too plain, add one small characterful beat (a short sniff/chin-lift or a lazy shoulder roll around 3.0 s) as **Idle_Stand_v04**; keep amplitudes moderate. The finger curl (max 0.16) is almost invisible. Judge the head drift and blink dip at the gameplay camera distance in Unity. |
| **Idle_Bored_v03** (planned 6.0 s loop) | Not started. Design in §7. | Author it in `clips_standing.py`, reusing `StandRig`. |
| **Cargo_Sit_Idle_v04** (planned 4.5 s loop) | Not started. Design in §7. | Author it first: Cargo_Knock and SitUp_Cargo depend on its frame 1. New module `clips_cargo.py`. |
| **Cargo_Knock_v03b** (planned 3.3 s loop) | Not started. Design in §7. | Must start and end on **Cargo_Sit_Idle_v04 frame 1** (not GPT's v03). |
| **SitUp_Cargo_v04** (planned 2.4 s) | Not started. Design in §7. | First frame = GetUp_FromBack_v02 frame 1; last frame = Cargo_Sit_Idle_v04 frame 1. |

## 2. Files in this folder

| File | Role |
| --- | --- |
| `acting_core.py` | Core library (shared by all clips). See the item list below the table. |
| `clips_standing.py` | Standing clips. `StandRig.body()` does the FK, solves the pelvis height from the support leg, and runs the planted-foot leg IK. Contains Idle_Stand (`stand_channels` / `stand_pose`) and the `CLIPS` registry. |
| `build_v03.py` | Driver: author → key → review render / trace / final save + FBX export. It imports `clips_cargo.py` if that file exists. |
| `validate_v03.py` | Independent validation of the saved Blend and FBX, for standing and cargo clips (§3). |
| `make_sheets.py`, `plot_trace.py` | Pillow tools for review grids, GPT-style contact sheets and joint-trace plots (mm vs time). |
| `export_rig_json.py`, `rebuild_rig_from_json.py`, `rig_Buddy_Mixamo65_A_v04.json` | LFS-free rig, contract poses and skinned A mesh proxy (§4). |
| `Idle_Stand_v03.*`, `validation_Idle_Stand_v03.json`, `Previews/Idle_Stand_v03/` | The delivered clip. |
| `Previews/Review_01..03/` | Iteration evidence for Idle_Stand: traces, key poses, a grid, and the r3 candidate MP4 with front, side and three-quarter views. |
| `provenance_v03.json` | sha256 of the inputs (unchanged) and of every package file at this stop point. |

`acting_core.py` provides:
- source loading (A v04 .blend, or the JSON when the .blend files are LFS pointers);
- FK deltas `Buddy.fk`;
- roll-preserving two-bone IK `chain_info` / `solve_chain`;
- finger curl;
- the Hermite `Curve` (Steffen tangents, `'flat'`, explicit or broken tangents, periodic);
- `pnoise` periodic noise;
- `spring_periodic` follow-through;
- exact-seam keying `key_action(canonical=...)`;
- FBX export with the GPT/Walk_v02 settings;
- the review studio and cameras.

## 3. Commands

Run from the repository root. `blender` = Blender 5.2.x; locally that is `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"`. `PKG = ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Idle_Knock_v03`. Clip keys: `Idle_Stand`, `Idle_Bored`, `Cargo_Sit_Idle`, `Cargo_Knock`, `SitUp_Cargo`. Stems: `Idle_Stand_v03`, `Idle_Bored_v03`, `Cargo_Sit_Idle_v04`, `Cargo_Knock_v03b`, `SitUp_Cargo_v04`.

```
# fastest review: joint traces (offset from frame 1 in mm vs time), then plot
blender -b --factory-startup --python $PKG/build_v03.py -- --clip Idle_Stand --trace /tmp/t.json
python $PKG/plot_trace.py /tmp/t.json /tmp/t.png [--points HeadTop_End,Hips,LeftHand,...]

# review renders (in memory, nothing saved): every 2nd frame or chosen times; views side,three_quarter,front
blender -b --factory-startup --python $PKG/build_v03.py -- --clip Idle_Stand --review 1 --out /tmp/rev --every 2 --res 320
blender -b --factory-startup --python $PKG/build_v03.py -- --clip Idle_Stand --review 1 --out /tmp/keys --times 0,0.95,2.26 --res 420
python $PKG/make_sheets.py grid /tmp/rev /tmp/rev.png --cols 11 --size 165 --title "..." --views front,side

# final deliverable (refuses to overwrite; use --dest <dir> for a dry run elsewhere)
blender -b --factory-startup --python $PKG/build_v03.py -- --clip Idle_Stand --final

# validate saved files (cargo clips: validate together with Cargo_Sit_Idle so its frame 1 is the reference)
blender -b --factory-startup --python $PKG/validate_v03.py -- --clips Idle_Stand --out $PKG/validation_Idle_Stand_v03.json
blender -b --factory-startup --python $PKG/validate_v03.py -- --clips Cargo_Sit_Idle,Cargo_Knock,SitUp_Cargo --out $PKG/validation_cargo_v04.json

# final previews from the SAVED .blend (no re-authoring)
blender -b --factory-startup --python $PKG/build_v03.py -- --clip Idle_Stand --from-saved --every 1 --res 480 --seq --views side,three_quarter --out /tmp/frames
blender -b --factory-startup --python $PKG/build_v03.py -- --clip Idle_Stand --from-saved --res 480 --views side,three_quarter --times 0,0.45,0.95,1.55,2.18,2.26,2.4,2.95,3.45,4.0 --out $PKG/Previews/Idle_Stand_v03/stills
#   loops: delete the duplicated last frame (s<N>.png) first, then show 3 loops; one-shots: no -stream_loop
ffmpeg -n -stream_loop 2 -framerate 30 -i /tmp/frames/side/s%04d.png -c:v libx264 -pix_fmt yuv420p -crf 17 -movflags +faststart $PKG/Previews/Idle_Stand_v03/Idle_Stand_v03_side_loop_x3.mp4
python $PKG/make_sheets.py contact $PKG/Previews/Idle_Stand_v03/stills $PKG/Previews/Idle_Stand_v03/Idle_Stand_v03_contact_sheet.png --title Idle_Stand_v03

# rig JSON (already exported; re-export only to a new name) and LFS-free rebuild
blender -b --factory-startup --python $PKG/export_rig_json.py -- --out <new>.json
blender -b --factory-startup --python $PKG/rebuild_rig_from_json.py -- [--save /tmp/buddy_rebuilt.blend]
```

Cameras live in `VIEWS_STAND` / `VIEWS_CARGO` in `build_v03.py`. The cargo review stage adds the floor, the wall plane x = -0.65 and an orange 1.2 m marker line on the wall. Cargo clips must set `'stage': 'cargo'` in their registry entry.

## 4. Rig sources and working without Git LFS

- Read-only sources: `SAUSAGE_BUDDY_A_v04.blend` (rig `Buddy_Rig_Mixamo65`, 65 bones, root `mixamorig:Hips`, meshes Body/Face/Outfit, action `Idle`). `SAUSAGE_BUDDY_B_v04.blend` has an identical rest rig. `Animations/GetUp_Idle_v01/GetUp_FromBack_v02.blend` frame 1 is the supine contract. `Animations/Locomotion_v01/Walk_v02.fbx` is the bind and bone-order reference. Their sha256 hashes are in `provenance_v03.json`.
- `.blend`, `.fbx`, `.png` and `.mp4` are Git LFS. `.py` and `.json` are not.
- `rig_Buddy_Mixamo65_A_v04.json` (608 KB) contains:
  - bones (file order, head/tail/roll/flags, full-precision `matrix_local`);
  - the raw Idle frame-1 and supine frame-1 values;
  - the A v04 meshes (vertices, faces, flat material colours, vertex-group weights).
- `acting_core.Buddy` switches to the JSON automatically when the .blend sources are LFS pointers (or when `BUDDY_RIG_JSON=1`). Verified locally:
  - rest, Idle, supine and authored poses are identical (error 0.0);
  - the skinned mesh is within 2.4e-7 m;
  - an FBX exported through the JSON path matches Walk_v02 bone order, hierarchy and bind matrices (error 0.0).
- `validate_v03.py` falls back to the JSON bind matrices when `Walk_v02.fbx` is an LFS pointer.
- The walk animator's `Animations/Locomotion_v02/rig_Buddy_Mixamo65.json` appeared during this session. Its bone block is bit-identical to this package's (max difference 0), so either file can be used for the skeleton. This package keeps its single file because it also carries the two contract poses and the skinned mesh proxy that the floor/wall/height checks and previews need.

## 5. Contracts

- 30 fps, metres, +Z up, character faces -Y, left = +X.
- Half-frame keys (60 Hz), linear. FBX baked at 0.5-frame steps. One take, armature only, 65 bones in the original order. Bind matrices equal to Walk_v02.
- **Idle_Stand / Idle_Bored:** frame 1 and the duplicated last frame are keyed with the exact raw A v04 `Idle` frame-1 values (validator: start/end contract error 0, seam 0). The Idle frame-1 legs are fully straight; see gotcha §8.1.
- **Cargo_Sit_Idle_v04:** a seamless loop. Its frame 1 is the **cargo sit contract**: the start and end of Cargo_Knock_v03b and the end of SitUp_Cargo_v04. Key those endpoints with the identical raw values (compute them once in `clips_cargo.py` and pass them as `canonical`).
- **SitUp_Cargo_v04:** frame 1 = exact raw GetUp_FromBack_v02 frame-1 values (neutral supine, head toward +Y, **hips start height 0.3070 m**, ragdoll-compatible, same contract as the get-ups). Hold it for the first ~4 frames for the ragdoll blend. Last frame = the cargo sit contract. Not a loop.
- **Cargo stage (review only, not exported):**
  - floor z = 0; side wall plane x = -0.65 (`acting_core.WALL_X`);
  - total mesh height ≤ **1.2 m** at every sample;
  - no floor or wall penetration (skinned mesh, 120 Hz).
- **Planned layout**, GPT's accepted stage, which keeps the reference Fedya liked:
  - the seated hips are at about (-0.30, 0, 0.108), facing +X with the back to the wall;
  - the big hood (protruding ~0.30 m behind the neck) is what touches the wall;
  - the van's rear **doors are assumed toward -Y**, which is his right when seated.
  Document the layout in the README so Unity can place the van to match.

## 6. Acceptance criteria

All clips share these criteria:
- Funny, readable cartoon acting with holds and snaps, overlapping action and clear silhouettes. Dumb comic "sausage people" in a black-humour co-op game, but not silly-clown.
- Exact loop seams.
- Contracts as in §5.
- No NaN or reflected bones, no adjacent quaternion sign flips, key-to-key rotation < 25°.
- FBX reimport: bone order and hierarchy match, bind error < 1e-4, animated matrix error < 1.5e-4, reimported seam < 1e-5 (achieved: 0.0), one take, armature only.
- Each deliverable ships: `.blend` + `.fbx`, the scripts, a README (EN + short RU summary), a validation JSON, MP4 previews (side + three-quarter) and a contact sheet.
- Never overwrite: new revisions get new numbered names. No Assets/ edits, no commits, no WORK_SYNC.md edits.
- Render the previews and **look at them**, iterating at least twice.

Additional criteria per clip:

- **Standing clips:** standing support error ≤ 1 mm, planted-foot slide ≤ 1 mm (the validator measures both), no sole penetration.
  - **Idle_Stand:** 3–5 s; alive breathing, subtle weight shifts, a blink-like head settle, relaxed arms.
  - **Idle_Bored:** 4–6 s. Required beats: a big sigh with the shoulders, looking around, a scratch (belly or back of the head), and a watch check or a pebble kick.
- **Cargo_Sit_Idle_v04:** 4–5 s; hugging the knees, trembling, panicky glances at the doors, a gulp.
- **Cargo_Knock_v03b:** 2.5–3.5 s; desperate comic banging. He turns, bangs with **both** fists, perhaps presses his cheek to the wall to listen, then slumps back.
- **SitUp_Cargo_v04:** ~1.8–2.4 s; waking up groggy and comic. Beats: a dazed head shake, rubbing the bump, realising where he is, then a panic glance. He ends sitting with the knees up and the back to the wall.

## 7. Planned designs (not yet authored)

**Cargo_Sit_Idle_v04 (4.5 s = 135 frames, loop)**

Base pose (frame 1):
- He sits as in the layout above; the knees are up, with the feet flat about 0.45–0.5 m in front of the hips.
- The arms wrap the shins and the fingers grip (curl about 0.5).
- The shoulders are shrugged (scared turtle) and the head is low, peeking over the knees. Keep the face readable from the front/three-quarter cameras.

Beats:
- 0–0.6 s: shallow fast breathing and trembling.
- 0.6–0.75 s: a SNAP glance at the doors (head yaw about 50° to his right; the chest follows 25%; the shoulders jolt up).
- 0.75–1.45 s: he holds the stare, trembling more, and shrinks back against the wall (the wall limits the lean).
- 1.45–1.7 s: a slow, reluctant turn back.
- 1.7–2.2 s: a GULP. The chin tucks, the head dips, and the shoulders rise and drop. The arms squeeze the knees.
- 2.2–2.9 s: one or two small anxious rocks on the butt (the feet stay planted).
- 2.9–3.1 s: a double-take at the doors (30°, then 55°) with a short hold.
- 3.1–3.6 s: he turns back and sinks lower behind the knees.
- 3.6–4.5 s: he settles into frame 1.

Trembling: `pnoise` with integer cycles per loop (about 30–41 cycles in 4.5 s, i.e. 6.7–9.1 Hz), 0.4–0.7° on the spine, neck, head and hands. It is zero at the seam.

**Cargo_Knock_v03b (3.3 s = 99 frames, loop on the sit contract)**

- 0–0.2 s: anticipation. A surge: he squashes down and his head snaps toward the wall over his right shoulder.
- 0.2–0.53 s: the turn. He releases the knees and swivels on the butt about 70–90° to his **right** (toward -Y). The knees fall to his left, into a side-sit, while the feet pivot roughly in place. The chest twists further, to about 150° in total, so it faces the wall about 30° off-square.
- 0.53–1.53 s: pounding.
  - Alternating hammer-fists (L R L R, about 6 Hz alternation), with a body bounce and a head shake on each hit.
  - Then both fists rise (anticipation, keep them ≤ ~1.1 m), a double-fist slam, and a short hold.
  - The fist contact is at x = -0.65 + 2–3 mm, z ≈ 0.5–0.8. Place it by evaluating the skinned mesh and shifting the IK target.
- 1.53–2.27 s: listening. The palms go flat on the wall and he presses his cheek or ear to it, frozen with a tiny tremble.
- 2.27–2.87 s: the slump. He deflates and swivels back; the legs come back up.
- 2.87–3.3 s: a sad sigh into the exact knee hug.
- Staging: turning toward -Y lets cameras on the -Y side see his face while he pounds. Put the knock's three-quarter camera on the -Y side, for example (2.0, -4.0, 1.6), never behind the wall.
- Alternative if the swivel reads badly: a corner layout with a second wall at his side. This adds a placement constraint for Unity, so ask the lead first.

**SitUp_Cargo_v04 (2.4 s = 72 frames, one-shot)**

- 0–0.13 s: hold the exact supine contract. Note that this pose rests on the hood, with the legs about 0.26 m above the floor; let the legs drop and bend right after the hold.
- 0.13–0.40 s: he stirs groggily. The head rolls, a hand twitches, and the knees bend up as the feet slide to the butt on the floor.
- 0.40–0.80 s: a heavy sit-up. The hands push on the floor. The giant head **lags, then flops forward**: overlapping action, and the key comic beat.
- 0.80–1.15 s: a dazed "brrr" head shake (3 decaying shakes, ±25° yaw plus roll).
- 1.15–1.50 s: he rubs the bump. The right hand goes to the top or back of the head in small circles; the head tilts into the hand with a wince, and the shoulders hunch.
- 1.50–1.70 s: realisation. The hand freezes, he takes a slow look, then a SNAP panic glance at the doors (-Y, which is still in front of him here).
- 1.70–2.10 s: a scramble. He turns 90° to his **left** (to face +X) and scoots the hips 0.30 m toward -X with heel pushes and hands, until the hood bumps the wall (a small squash).
- 2.10–2.40 s: he curls into the knee hug, landing exactly on the sit contract.
- Keep the mesh ≤ 1.2 m and ≥ the floor at every sample. A per-frame skinned-mesh lift, like GPT's `floor_safe`, is a safety net only.
- An alternative layout was considered and rejected: facing -Y with the wall at +Y avoids the 90° turn, but needs a ~0.65 m scoot back, because the supine head top reaches y ≈ +0.97.

**Idle_Bored_v03 (6.0 s = 180 frames, loop on Idle frame 1)**

- 0–0.25 s: neutral.
- 0.25–1.3 s: "anybody coming?" The head and chest look about 40° right (fast in, ease out) and hold with a drift. Then they sweep about 45° left, dipping in the middle of the arc, and hold.
- 1.35–2.4 s: a watch check.
  - The left forearm snaps up horizontal in front of the chest, wrist at about (0.05, -0.25, 1.05). Use arm IK with `StandRig.arm`.
  - The head pitches down to look, holds, does a double take (pulls back, then leans in), and gives two quick wrist shakes.
- 2.4–3.7 s: the BIG SIGH.
  - The arm drops during a huge inhale: a clavicle shrug of about 15–20° **with an Arm counter-rotation**, and the head tips back.
  - Hold at the top.
  - Then a hard exhale: the shoulders drop, the spine slumps, and the knees unlock (the hips drop about 3 cm). The hip pops to his right with the left knee bent.
  - The arms dangle with pendulum follow-through (`spring_periodic`), and the head sags and bounces.
- 3.7–5.2 s: a lazy scratch of the back of the head with the right hand. Put the IK target in the Head bone's frame, scratch at about 4 Hz with the wrist and forearm, and tilt the head into the hand.
- 5.2–6.0 s: he straightens and settles, with the knees locked ≥ 0.3 s before the seam.
- Pebble-kick alternative to the watch: add the lifted foot's time window to `FOOT_FREE` in `validate_v03.py`, and make the foot path end on its exact base matrix.

## 8. Technique notes and gotchas

1. **Straight Idle legs.**
   - In Idle frame 1 the knee is exactly straight (hip–ankle distance = l1 + l2), so the knee's forward offset grows like sqrt(leg shortening).
   - Hold the knees locked for ≥ 0.15 s on both sides of the seam (the `'flat'` zero keys in `soft`).
   - Feed the leg-affecting weight channel through `w^3/(w^2+e^2)`.
   - Never raise the pelvis above the support-leg solve. The review 1 trace showed a V-shaped knee pop at the seam before this fix.
2. **Shrugs.** A clavicle shrug rotates the whole hanging arm about the clavicle's inner end: about 4 cm of outward hand swing per 5°. Counter-rotate `Arm` (Left: +, Right: -, about Y).
3. **IK.**
   - The reach clamp has no epsilon, so straight base limbs are reproduced exactly.
   - `chain_info` / `solve_chain` carry the base bone roll through the pole plane, so the base is reproduced to 1e-7.
   - Bent base chains (arms, the seated legs) derive their own pole from the base elbow or knee.
4. **FK deltas** are expressed in the base pose's world axes, carried by the parent ("relative to the parent"). For the seated set, pass `cf=R(Z,90)` to `Buddy.fk` to author in the character frame. Sign conventions are documented at the top of `clips_standing.py`.
5. **Exact seams.**
   - Key the canonical raw values at frame 1 and the last frame (`key_action(canonical=...)`); it asserts the quaternion sign continuity.
   - Make the curves periodic and zero at the seam. `spring_periodic` gives zero-at-seam follow-through.
6. **Review order:** traces first (`--trace` + `plot_trace.py`: amplitudes, arcs and the seam in mm), then key-pose renders, then full MP4s. Small thumbnails are useless for idles.
7. **File formats.**
   - The .blend sources are zstd-compressed (magic `28 B5 2F FD`, not `BLENDER`). LFS pointers start with `version https://git-lfs`.
   - Import with `sys.dont_write_bytecode = True` so no `__pycache__` appears in the source folders.
8. **Hands.** Pinky bones are non-deforming (mitten: three fingers + thumb). `Buddy.curl` uses the palm axis that GPT verified.
9. **No face animation in the FBX** (animation-only FBX). The acting must read from the body; blinks and expressions belong to the game's face script.
10. **Registering new clips.** `clips_cargo.py` does not exist yet; `build_v03.py` imports it if present. Register clips with the same dict shape as `clips_standing.CLIPS` (`T`, `loop`, `stage`, `setup`, `pose`, `canonical`, `stats`, `beats`). Stems are in `build_v03.STEMS` and `validate_v03.STEMS`.
