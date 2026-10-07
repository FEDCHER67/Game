# GetUp v03 — handoff (2026-10-07, local Claude animator → cloud sessions)

Task: re-author the Sausage Buddy get-ups **GetUp_FromBack_v03** and **GetUp_FromBelly_v03** (Fedya rejected GPT's v02:
«переделай сам подъём со спины, подъём с живота»). Funny, dizzy, cartoon get-ups with personality (a dumb comic sausage
person waking from a knock-out), readable silhouettes, not silly-clown. Stopped at the lead's request at a logical point.

## State in one paragraph

The authoring framework is written and verified; the two **lying start poses** (the ragdoll-blend contract) are authored,
grounded on the real meshes and reviewed in renders; the **performances are not authored yet** (`make_back()` /
`make_belly()` return a 6-frame hold of the start pose). No `.blend`/`.fbx` deliverable exists; `--final` is guarded by
`getup_choreo_v03.READY = False`. Detailed beat sheets for both clips are in `getup_choreo_v03.py` (`BEATS_BACK`,
`BEATS_BELLY`) and summarised below. A plain-JSON rig + skinned mesh proxy lets the pipeline run without Git LFS
(verified: identical metrics to 1 µm).

## Files (all new, all in this folder)

| File | Role |
| --- | --- |
| `getup_lib_v03.py` | Framework: `Rig` (opens the source, Idle frame 1, mesh tables), local rest-frame FK, hinge-plane two-bone IK, `Track`/`QTrack`/`Step` curves, `Clip` (params + procedural layers, floor solver `solve()`, `key()`), review render helpers. |
| `getup_choreo_v03.py` | Channel reference (docstring), `BEATS_BACK`/`BEATS_BELLY` beat sheets, `start_back()`/`start_belly()` (verified), stub `make_back()`/`make_belly()`, `READY` flag. |
| `build_getups_v03.py` | CLI: solve + key + metrics (hipsStart, per-part floor heights, Stable estimate), `--review` renders, guarded `--final` export (GPT/Walk_v02 FBX settings, refuses overwrite). |
| `export_rig_json_v03.py` | Wrote the two JSON files below from the A v04 source (refuses overwrite). |
| `rig_Buddy_Mixamo65.json` | 65 bones in file order (name, parent, head, tail, roll, length, matrix_local, deform/connect/inherit flags), DFS order, armature object transform, **Idle frame-1 pose** (basis quaternions + hips location + armature matrices), rigid hand/shoe contact points, source SHA-256s. 100 KB. |
| `mesh_proxy_Buddy_A_v04.json` | Body/Face/Outfit rest vertices, polygons, material slots (flat base colours), vertex-group weights. No UVs/textures/shape keys. 483 KB. |
| `rebuild_rig_from_json_v03.py` | Recreates the armature (+ `--with-proxy` skinned meshes, + `--idle-action` one-key `Idle` action) into a new .blend. |
| `Previews/WIP_StartPoses_v03_review02.png` | Review render of the two verified start poses (side + three-quarter). WIP, not a deliverable preview. |

The Walk animator's `Locomotion_v02/rig_Buddy_Mixamo65.json` did not exist when this was written; reuse whichever exists
(both come from the same unmodified A v04 rig).

## Rig source files used (read-only, unmodified; SHA-256 match GPT's `provenance_v02.json`)

- `ArtSource/Characters/SAUSAGE_BUDDY_01/SAUSAGE_BUDDY_A_v04.blend` — `8ce9b86c1a2665893a9749cb234af48fb8b792c427e9491a2af75a4fb1c20653` (Git LFS). Armature `Buddy_Rig_Mixamo65`, 65 bones, root `mixamorig:Hips`, faces −Y, +X = character left, Z up, metres; meshes Body/Face/Outfit; action `Idle` (frame 1 = end pose).
- `SAUSAGE_BUDDY_B_v04.blend` — `e2d501f4…c051`; identical rest rig (not opened by this package).
- `buddy_rig.py` (`9cbccdaa…be25`): `ordered()`, `key_frames()`, `fcurves_of()`. `buddy_render.py` (`0625ec99…2cc51`) + `buddy_geo.py` (`af3140a9…6ace`): review studio. Imported with byte-code writing disabled.
- Bone-list reference for validation: `GetUp_Idle_v01/GetUp_FromBack_v02.fbx` / `GetUp_FromBelly_v02.fbx` (and Walk_v02).

## Commands

Blender: `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"` (cloud: any Blender 5.2 `blender`). Run from this folder.

```
# Review build (current stub = start-pose hold); stills of every 2nd frame, side + three-quarter
blender -b --factory-startup --python build_getups_v03.py -- --clip all --review <scratch>/rev03 --every 2 --res 320
# Final export once READY=True (writes GetUp_From{Back,Belly}_v03.blend/.fbx/_authoring.json; refuses overwrite)
blender -b --factory-startup --python build_getups_v03.py -- --clip all --final --revision 3

# Without Git LFS (cloud): rebuild a source from JSON, then point the framework at it
blender -b --factory-startup --python rebuild_rig_from_json_v03.py -- --out <scratch>/buddy_rebuilt.blend --with-proxy --idle-action
GETUP_SOURCE_BLEND=<scratch>/buddy_rebuilt.blend blender -b --factory-startup --python build_getups_v03.py -- --clip all --review <scratch>/rev
```

Verified 2026-10-07: rebuilt rest matrices max error 5.0e-8, rebuilt Idle 2.2e-7, builder Idle reconstruction 2.1e-7;
build metrics on the rebuilt proxy equal the real source (hipsStart 0.142909 vs 0.142908 m; belly 0.200700 vs 0.200701 m).
The proxy has flat colours only, so cloud renders are silhouette/motion reviews; final previews should be rendered
from the LFS source. Not yet written (next steps): `validate_getups_v03.py`, `render_previews_v03.py`,
`make_sheets_v03.py`, `README.md`, `getup_manifest_v03.json`.

## Framework notes (read before authoring)

- Rotations are **local, in the parent's rest-frame axes**, pre-multiplied onto Idle frame 1: `bend +` = forward
  flexion, `side +` = toward the character's left, `twist +` = turn left. They mean the same lying or standing.
  All channels are listed in the `getup_choreo_v03.py` docstring. All offsets 0 + Idle targets = Idle frame 1.
- Hips: `RZ(yaw) @ RX(pitch) @ RY(lean) @ RZ(twist)`; pitch −90 supine, +90 prone; twist = roll about the body axis.
- Arm FK `(fwd, out, twist)` is an absolute swing re-based on Idle `(4, 16, 0)`; elbow hinge about the upper arm's
  rest Z (Idle 14°). IK and FK are slerp-blended per bone by `ikL/ikR`. Legs are always IK.
- IK targets are `(x, y, h)`: `h` = height of the hand's/shoe's lowest rigid point above z=0 for the given world
  orientation, so planted contacts are exact. **Planted hands need h ≈ 0.008** (mixed-weight wrist/cuff vertices
  otherwise go 7 mm under). `handOnKnee*` targets a solved knee (legs are built before arms).
- `Track` is monotone cubic (never overshoots; extrema and end keys ease). Author anticipation/overshoot as keys.
  `QTrack` slerps quaternion keys on a monotone timing curve. `Step` for `ground_set`.
- Floor solver (`Clip.solve`): `ground` weight blends the hips height toward "regions in `ground_set` touch z=0"
  (lying/sitting: `('torso',)`; kneeling: `('legL','legR')`), then lifts the hips wherever torso/arms/legs would
  penetrate; the lift is max-filtered + blurred (never undercuts, never pops). Hands/feet contacts come from targets.
  Mesh evaluation costs ~1 ms, so a full clip solves in seconds.
- `key()` keys every half frame (LINEAR, as the existing pipeline) and forces the last frame to the exact Idle
  matrices. Procedural layers (`Clip.layers`) add offsets per channel: use them for the dizzy circle, shake, tremor.

## Contracts to keep

1. **First frame = neutral lying pose, held** (≥ 5 frames) for the 0.35 s ragdoll blend (Neck/Head 0.5 s); the first
   motion after the hold must be slow. **Back**: supine, face up, **head toward local +Y**, feet −Y, arms along the
   sides, palms down. **Belly**: prone, face down, **head toward local −Y**, hands beside the chest ready to push.
2. **hipsStart** (first-frame Hips position, root space) reported in README + manifest. Current verified start poses:
   **back (0, 0, 0.1429) m, belly (0, 0, 0.2007) m** (GPT v02: 0.3070 / 0.2401). The back value is now realistic
   because the pelvis is tilted (pitch −67) so butt **and** hood touch the floor; GPT's flat pitch −90 floated the body
   on the hood (the hood bulges 0.17 m behind Spine2).
3. **Stable** event: frame and fraction where the standing capsule may turn on (upright over the root, feet down);
   design target ~0.70; planned ~0.75–0.85. `metrics()` estimates it (hips z > 0.6, |hips xy| < 0.35 m, spine within 35°
   of vertical, holding to the end) — confirm by eye.
4. **Ends exactly on Idle frame 1** (matrix error < 1e-5; `key()` forces the last frame).
5. **In place**: hips start and end at x = y = 0 (net horizontal drift 0); mid-clip excursions allowed (the plan uses
   ≤ 0.27 m and steps back); `applyRootMotion` stays false.
6. **30 fps**, frames 1…N+1, duration 2.0–2.8 s; one action per file named `GetUp_FromBack_v03` / `GetUp_FromBelly_v03`;
   armature-only FBX with the Walk_v02/GPT export call (rest pose before export, bake step 0.5, simplify 0, −Z forward,
   Y up, no leaf bones); no face curves; never overwrite a numbered file.

## Acceptance criteria

- Reads as funny, dizzy, groggy cartoon get-ups with personality; strong silhouette per beat; weight and momentum
  (push-offs, overlapping spine/arm follow-through); cartoon timing with holds and snaps. Must be clearly better
  than v02 (rigid planks, nose/hood-balanced starts, teleport-like sit-to-crouch, straight vertical stand-up).
- Standing feet: penetration ≤ 1 mm, support error ≤ 5 mm; no hand/knee/body through the floor (design limit 1 cm, aim
  ≤ 2 mm); hips net horizontal drift 0; end = Idle frame 1.
- Bone list, order and hierarchy identical to GPT's v02 FBX (and Walk_v02); bind error 0; no NaN, no reflected bones,
  no adjacent quaternion sign flips; max half-frame local rotation < 25° (shakes/windmills must respect it); FBX
  reimport world-matrix error < 1.5e-4; exactly one action; armature-only FBX.
- Package: `.blend` + `.fbx` per clip, scripts, `validation_v03.json`, MP4 previews side + three-quarter, contact
  sheets, README in English + short Russian summary, manifest with hipsStart and Stable. Render and **look**;
  iterate at least twice on stiffness.

## Planned performances (from `getup_choreo_v03.py`, not keyed yet)

**FromBack, 84 frames (2.8 s):** hold 0–5 → groggy head lift, looks at the feet 5–14 → anticipation 14–17 → sit-up
snap 17–24 (pelvis −67→−8, spine curls past vertical, arms thrown at the feet, heels pop up and slap down, head lags then
whips) → settle, hands land on the thighs 24–30 → **dizzy circle** of head/neck/upper spine 30–46 → **"brr" head shake**
(±30° at 5 Hz, shoulders shrug) 42–51 → gather (feet to y −0.27, soles flat, hands behind the hips, lean back) 48–56 →
rock forward over the feet into a deep squat, arms swing for momentum 56–64 → rise too fast, head last 63–71 →
**head-rush backward stagger**: arms windmill, right foot steps back to its Idle spot 70–77 → left foot steps back,
hips return to (0,0), settle into Idle 76–84.

**FromBelly, 84 frames (2.8 s):** hold 0–6 → **noodle-arm push-up** with trembling arms 6–16 → arms buckle, chest flops
16–19 → second push, hips shift back over the knees to all fours 19–30 → **dizzy head circle, then a whole-body
wet-dog shake** 30–46 → kneel up, right foot to its Idle spot (half kneel), hands on the right knee 46–57 → stand,
left foot swings forward to Idle 57–67 → **forward teeter on the toes with windmilling arms**, rock back onto the heels
(in place) 66–78 → settle into Idle 78–84.

Feasibility notes measured on this rig: arms are short (shoulder→wrist 0.44 m, palm-flat wrist height 0.032 m), so
seated hands only reach the floor behind the hips with a ~30° lean back, and squat hands need a ≥ 65° forward lean;
thigh 0.37 m, shin 0.315 m, ankle 0.115 m, Idle hips 0.8211 m; hood weighted to Spine2.

## What still looks wrong / open items

- Performances unauthored (the whole job). Start with blocking at the beat frames, review every 2nd frame from both
  views, then splines/overlap, then the procedural layers.
- Belly start: head 2.8 cm above the floor (add ~5° neck flexion). Back start: head rests 2.4 cm up on the hood
  (intended "pillow"), hands 1–3 mm above the floor (fine).
- Validation, preview rendering, contact sheets, README/manifest scripts still to write; model them on
  `GetUp_Idle_v01/validate_getups.py`, `Previews/render_mp4_v02.py`, `contact_sheets.ps1` (+ bone-list identity vs the
  v02 FBX, hand/knee floor checks, hipsStart/Stable reporting). Review renders so far went to a local scratch folder,
  not the repo.
