# Sausage Buddy: escape and police set (Escape_Police_v01)

Sixteen clips for the van escape and the police, on the shared Buddy rig `Buddy_Rig_Mixamo65` (65 bones). The police are sausage people too, so they use the same rig.

**What is in git:** only text. That is the deterministic build scripts, the validator, the preview script, the validation report, the per-clip authoring reports and a Unity manifest. The `.blend`, `.fbx`, MP4 and PNG files are **not committed**; regenerate them with the commands in [Building locally](#building-locally). Two builds from the same scripts give bit-identical keyframes (checked with action digests, listed in `clips_manifest_v01.json`).

**Provenance:** original procedural/keyframe animation by Claude (cloud session, 2026-10-07): FK deltas plus hinge IK, written as Python for Blender 5.2 (`pip install bpy`). No mocap, downloaded motion, paid generation or credits. The only inputs are the Idle_Knock_v03 package's `acting_core.py`, `rebuild_rig_from_json.py` and `rig_Buddy_Mixamo65_A_v04.json` (imported, not copied). No other package, no Assets/ file and no WORK_SYNC.md was touched.

## Clips

| Clip | Frames | s | Loop | What it does | Validation |
| --- | --- | --- | --- | --- | --- |
| **Escape_Scramble_Start** | 1–25 | 0.80 | no | From the cargo knee-hug sit: a SNAP glance at the open doors, a frozen tremble, then a panicky hop-turn of 90° to his right onto hands and knees. Ends exactly on Escape_Scramble frame 1. | 20/20 |
| **Escape_Scramble** | 1–16 | 0.50 | yes | Frantic hands-and-knees scramble toward the door (−Y) under the 1.2 m roof. Palms and knees ride the van floor at 1.2 m/s with no sliding. The pelvis height and roll are solved from the planted knees. The body is almost horizontal with a lizard wriggle, the head is bent back like a periscope and glancing, and the feet flick up behind. Mesh top is 0.955 m. | 20/20 |
| **JumpOut** | 1–35 | 1.133 | no | From the crawl on the van floor (+0.55 m): a frog hop onto the sill, a crouched peek at the drop (gulp), then he steps off. Arms flail and he tucks into a cannonball until the van has slid behind him, then falls 0.55 m. He lands on the left foot (event `Land` 0.567 s) with a 9 cm squash, stumbles forward, and runs. Ends exactly on Flee_Run frame 1. | 19/20 (FBX note below) |
| **Flee_Run** *(bonus)* | 1–18 | 0.567 | yes | Civilian panic run that JumpOut lands into. Upright, arms flapping up in front with open hands, head thrown back, 3.2 m/s. | 20/20 |
| **Struggle_Carried** | 1–49 | 1.60 | yes | Additive-friendly struggle while carried. Tuck-and-piston bicycle kicks (2.5 Hz, legs in antiphase), torso wriggle/squirm/arch, arms flailing and shoving, head thrashing. **Frame 1 = Idle frame 1 exactly** (the additive reference pose). Every channel is a whole-cycle wave that only *passes through* Idle at the seam; there is no hold. Hips never translate. | 20/20 |
| **Hit_React_Front** | 1–25 | 0.80 | no | Belly hit, "OOF": snaps into a fold, butt shoots back 5 cm, arms fly forward then hug the belly, the head whips down after the chest, wobble, recover. Idle → Idle. | 20/20 |
| **Hit_React_Back** | 1–24 | 0.767 | no | Kicked in the butt: hips shoot forward 6–8 cm, back arches, arms fly back with spread fingers, the head lags then whips, then he rubs the sore butt. Idle → Idle. | 20/20 |
| **Hit_React_Head** | 1–28 | 0.90 | no | Bonk: the head jams down into shrugged shoulders (turtle), knees buckle 9 cm, jazz hands, then both hands clutch the sides of the head (IK riding the head) through a dizzy wobble. Idle → Idle. | 20/20 |
| **Stagger** | 1–43 | 1.40 | no | Dazed stagger with six real steps: he stumbles out to his right, crosses over, lurches forward with a windmill, and shuffles back onto the exact Idle foot spots. The head circles dizzily. Idle → Idle. | 20/20 |
| **Cop_Run** | 1–19 | 0.60 | yes | Heavy, determined run at 3.0 m/s. He charges head-down with hunched shoulders and pumping fists. The landing squash folds the chest and the head nod lags 2 frames. Heel strike, heel peel about the toe hinge, toes stay flat. | 20/20 |
| **Cop_Run_Fat** | 1–18 | 0.567 | yes | Fat-cop variant: a funny waddle at 1.8 m/s. Short choppy toe-out steps on a wide track, the whole body tips over each stance foot like a penguin (±10°), belly-first posture, arms held out and flapping for balance, head bobbles with a lag. | 20/20 |
| **Cop_Punch** | 1–31 | 1.00 | no | Telegraphed haymaker. 0.08–0.30 s: big wind-up (body twists 42° away, leans back, fist cocked up by the ear, left index finger points at the target), then a straining quiver. 0.32–0.45 s: the punch snaps out at constant speed. **Event `Hit` at 0.45 s (frame 14.5)**, the end of the 0.45 s telegraph. Follow-through, then back to Idle. | 20/20 |
| **Cop_Aim_Raise** | 1–16 | 0.50 | no | Idle → two-handed pistol pose (no prop) with a 4% overshoot. Ends exactly on Cop_Aim frame 1. | 20/20 |
| **Cop_Aim** | 1–61 | 2.00 | yes | Pistol hold loop: elbows soft, knees bent, head tilted to sight with one eye. He breathes, the aim drifts slowly, and at 1.0–1.3 s there is a nervous re-grip with a squint. Trigger finger kept straight. Upper-body friendly. | 20/20 |
| **Cop_Trip** | 1–23 | 0.733 | no | Starts exactly on Cop_Run frame 1. The right toe snags under him and is dragged back with the street, the arms windmill, the head snaps up ("uh-oh"). He takes a long stumble step and dives. **The end pose is the ragdoll hand-off**: body pitched 76°, arms reaching forward to brace, both feet already off the street and trailing up behind, still moving forward and down (event `Ragdoll` at the last frame). | 20/20 |
| **Cop_ShakeFist** | 1–67 | 2.20 | no | The van escapes: he gathers rage, thrusts the right fist up overhead, out to the side, and shakes it at 4.6 Hz. The body bounces, the left hand goes on the hip, the head jabs (yelling). He stamps the left foot (back on its exact Idle spot), gives one last big thrust, deflates with a "no-no" head shake, and settles into Idle. | 20/20 |

All clips run at 30 fps. Every length is a whole number of frames; the build asserts it. A loop's last frame duplicates frame 1.

## Contracts and conventions

- Rig: `Buddy_Rig_Mixamo65`, root `mixamorig:Hips`, 65 bones in the original order. Bind matrices come from the A v04 rig, read from `Idle_Knock_v03/rig_Buddy_Mixamo65_A_v04.json` when the LFS `.blend` files are absent. Character faces −Y, his left is +X, Z is up, metres.
- Keys: every half frame (60 Hz), quaternion, linear. FBX: armature only, one take `Buddy_Rig_Mixamo65|<Clip>_v01`, the GPT/Walk_v02 export settings (rest pose before export, bake step 0.5, simplify 0, −Z forward / Y up, no leaf bones).
- **Exact contract frames:**
  - Idle frame 1 for the hits, Stagger, Punch, ShakeFist, Cop_Aim_Raise start and Struggle_Carried.
  - Cop_Run frame 1 for the Cop_Trip start; Cop_Aim frame 1 for the Cop_Aim_Raise end.
  - Escape_Scramble frame 1 for the Escape_Scramble_Start end and, raised +0.55 m, for the JumpOut start.
  - Flee_Run frame 1 for the JumpOut end.
  - Each is keyed with the identical raw values (validator contract error ≤ 2e-7).
- **In place.** Locomotion runs on a ground that slides toward +Y. Every planted sole pivot, knee and palm rides that ground exactly, so in game the root moves at the authored speed:

  | Clip | Authored speed (m/s) |
  | --- | --- |
  | Cop_Run | 3.0 |
  | Cop_Run_Fat | 1.8 |
  | Flee_Run | 3.2 |
  | Escape_Scramble | 1.2 |
  | JumpOut | 1.2 on the van floor, then 3.2 from 0.1 s after take-off |
  | Cop_Trip | 3.0 |

  Play the clips at `speed / authored speed`.
- Mid-clip hip excursions:
  - Escape_Scramble_Start moves the hips from the sit spot (−0.30, 0) onto the root.
  - JumpOut stays over the root.
  - Cop_Trip's hips advance 0.36 m in the dive (the ragdoll takes over from there).
  - Stagger wanders up to 13 cm and comes home.
- **Van layout (cargo clips).**
  - The van floor is z = 0 for Escape_Scramble and Escape_Scramble_Start, with a mesh height limit of 1.2 m: maximum 0.955 m in the loop, 1.134 m in the start.
  - The doors are toward −Y. That is to the sitter's right, as planned in Idle_Knock_v03 HANDOFF §5.
  - The sit spot is hips (−0.30, 0, 0.117), facing +X with the back to the wall at x = −0.65.
- **JumpOut root** = street level below the door; frame 1 is the crawl pose raised by the van floor height (0.55 m). When triggering it, drop the root to the street under the sill (or start it at the sill edge and let the clip carry the body down).
- **Escape_Scramble_Start start pose is provisional.** Cargo_Sit_Idle_v04 (the planned sit contract) has not been authored yet. This clip starts on my own stand-in for it: `clips_escape.sit_pose`, built from the planned layout. When v04 exists, replace frame 1 with its exact raw values (`ss_canonical` in `clips_escape.py`) and rebuild as Escape_Scramble_Start_v02. Until then, crossfade about 0.15 s from the sit idle.
- **Struggle_Carried as an additive layer:** use Unity's "Additive Reference Pose" at frame 0 (= Idle frame 1). Hips rotate a little (±8°) but never translate.
- **Cop_Aim / Cop_Aim_Raise:** the feet stay on the Idle spots with soft knees, so they also work on an UpperBody mask (AvatarMask by transform paths) while running.

## Validation (`validation_v01.json`)

`validate_ep_v01.py` reopens every **saved** `.blend` (not the authoring code) and samples it at 120 Hz on the skinned meshes (Body, Face, Outfit). It then reimports each FBX.

| Clip | Frames | Floor penetration (mm) | Contact slide per 1/120 s (mm) | Largest key step (°) | Loop seam | FBX animated error |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Escape_Scramble_Start | 24 | 0.00 | 1.28 | 21.7 | – | 2.2e-5 |
| Escape_Scramble | 15 | 0.00 | 0.00 | 21.2 | 0.0 | 1.9e-5 |
| JumpOut | 34 | 1.38 | 1.40 | 24.9 | – | **2.8e-4** |
| Flee_Run | 17 | 0.75 | 1.09 | 14.6 | 0.0 | 1.3e-4 |
| Struggle_Carried | 48 | (held in the air) | – | 16.5 | 0.0 | 2.0e-5 |
| Hit_React_Front | 24 | 1.19 | 0.09 | 20.1 | – | 1.9e-5 |
| Hit_React_Back | 23 | 0.68 | 0.18 | 15.6 | – | 1.8e-5 |
| Hit_React_Head | 27 | 1.49 | 0.05 | 20.5 | – | 1.8e-5 |
| Stagger | 42 | 0.52 | 1.52 | 22.5 | – | 1.9e-5 |
| Cop_Run | 18 | 0.62 | 1.31 | 15.2 | 0.0 | 1.8e-5 |
| Cop_Run_Fat | 17 | 0.24 | 0.69 | 9.6 | 0.0 | 4.7e-5 |
| Cop_Punch | 30 | 0.81 | 0.27 | 22.2 | – | 4.8e-5 |
| Cop_Aim_Raise | 15 | 0.14 | 0.02 | 13.4 | – | 1.8e-5 |
| Cop_Aim | 60 | 0.00 | 0.00 | 10.2 | 0.0 | 1.8e-5 |
| Cop_Trip | 22 | 1.12 | 1.30 | 20.9 | – | 7.0e-5 |
| Cop_ShakeFist | 66 | 0.73 | 0.11 | 16.6 | – | 2.0e-5 |

The validator checks, per clip:
- 30 fps; 65 bones in rig order; no NaN or reflected bones;
- no adjacent quaternion sign flips; largest key-to-key rotation < 25°;
- exact loop seam;
- start/end contracts < 1e-5;
- floor penetration ≤ 2 mm and contact slide ≤ 2 mm (in the ground frame, any vertex within 2 mm of the floor at two consecutive 120 Hz samples);
- the cargo 1.2 m limit;
- FBX: bone order and hierarchy equal to the rig, bind error < 1e-4, animated matrix error < 1.5e-4, one take, armature only, reimported seam < 1e-5.

All 16 clips are within these limits except one:
- **JumpOut, FBX animated error (open, 19/20).** One sample (frame 12.5, the left shoulder chain just after take-off) reimports 0.28 mm off, against the 0.15 mm limit. The .blend is fine there: no gimbal, small Euler angles. It looks like a quirk of the FBX exporter's bake (maybe Euler/float32), but I have not found the cause. 0.28 mm is invisible, but the check stays red until someone finds it.

Not a defect, but worth knowing:
- **Penetration readings.** The ≤ 1.5 mm values are the shoes' rest-sole offset and between-key interpolation. The source mesh itself sits 1 mm under z = 0 at rest.
- **Escape_Scramble_Start butt roll.** The 1.3 mm contact slide is the butt rolling as he presses back against the wall.

## Review log (I rendered and looked at every clip; at least 3 passes each)

Renders were Workbench (side, three-quarter, front, plus a door view for the cargo clips), from grids every 1–2 frames and from key-time stills. The final pass used MP4 and contact sheets rendered from the saved `.blend` files. In the list below, "fixed" means the next pass confirmed it.

- **Shared rig fixes, found while reviewing:**
  - *180° shin flips (heel kicked up behind).* The pole-projected IK lost the bend plane whenever the shin pointed along the pole. I replaced it with hinge-axis IK (`Body.solve`).
  - *Thigh roll at Idle.* With the default knee splay the thighs rolled 7° away from Idle. Fixed by building the base frames with the same splay (Idle now reproduces to 1e-7).
  - *Heel peel sinking the toes 9 mm and sliding them.* The pivot was a ground point instead of the toe hinge. Now it peels about the ToeBase joint.
  - *Loop pop between the last two frames of every run.* The landing pulse wasn't periodic over the step. Fixed with a wrapped phase.
  - *Seams and ends off-cycle.* Several lengths weren't whole frames; snapped, and the build now asserts it.
  - *Stretched bones in the blended transitions.* World-space pose blends key rotations only, so the saved clip differed from what was authored; the validator caught 240 mm floor penetration. Replaced with `rigid_blend`: blended rotations rebuilt by FK, legs by IK, floor guard.
- **Cop_Run.** Pass 1: read as a light jog, with flat compression and no hunch. Pass 2: head-down charge, 4.5 cm landing squash, hunched shoulders, bigger fist pump. Pass 3 (MP4): reads heavy and determined.
- **Cop_Run_Fat.** Pass 1: just a walk with the arms out, and the feet over-reached 3.7 cm. Pass 2: short choppy toe-out steps, a ±10° penguin tilt over each stance foot, arms flapping for balance, the head bobble countering the tilt. Pass 3: the waddle reads from the front.
- **Cop_Punch.**
  - Pass 1: the wind-up was too small to read as a telegraph, and in front and three-quarter views the arm was foreshortened.
  - Pass 2: an IK cock-back flipped the elbow when the fist passed the shoulder.
  - Pass 3: FK haymaker cock (fist up by the ear, body twisted 42°, pointing finger), then a constant-speed IK strike reaching full extension exactly at 0.45 s.
- **Cop_Aim / Cop_Aim_Raise.** Pass 1: the arms over-reached by 7 cm. Pass 2: the arms were too bent, reading like holding a phone. Pass 3: about 96% reach, elbows soft, reads as a two-hand pistol pose from the side.
- **Cop_ShakeFist.** Pass 1: reads (overhead fist, hand on hip, stamp). Pass 2: the frame-1 contract was off because of a constant arm twist. Pass 3: the fist covered the face in three-quarter view, so it moved out to the side.
- **Cop_Trip.** Pass 1: the trip and dive read well, but the stance foot over-reached 20 cm in the dive and the toe dug in during the snag. Pass 2: the left foot pushes off into the dive and the snag toe rides 11 mm up. Pass 3: windmill and blend slowed under the 25° step limit.
- **Hit reacts.**
  - Front: reads in pass 1 (fold, belly hug).
  - Back: reads in pass 1 (arch, butt rub).
  - Head: the hands only reached the shoulders (the arms are 0.44 m long), so I switched them to IK clutching the sides of the head, riding the head's wobble.
  - Frame-1 thumbs and thighs were off Idle; fixed.
- **Stagger.** Reads in pass 1. Two knee pops followed, fixed in turn: first the straight-knee pop (soft knees mid-clip), then a pelvis jump at each foot lift-off (lifted feet stay in the pelvis solve).
- **Struggle_Carried.** Pass 1: read as walking in place. Pass 2: tuck-and-piston kicks, but the antiphase leg kicked backward because the seam offset made the bump negative. Pass 3: a notch at the seam instead of the offset; reads as frantic kicking and flailing.
- **Escape_Scramble.**
  - Pass 1: the palms over-reached 8 cm and the knees hovered.
  - Pass 2: a pelvis roll solve plus anticipation of the next knee's landing, with no pop.
  - Pass 3: the swing knee swung out sideways when passing under the hip; the knee track moved 5 cm back.
  - Pass 4: the palm touchdown dipped 5 mm; the wrist height was adjusted.
- **JumpOut.**
  - Pass 1: the legs passed through the van floor in flight.
  - Pass 2: a faster ground ramp after take-off, a cannonball tuck and the trailing foot kept forward.
  - Pass 3: the frog hop dragged the feet and the arm throw was 35°/half-frame. Fixed with blends in the moving floor frame, foot rotation relative to the shin, a floor guard, and slower arms.
- **Escape_Scramble_Start.**
  - Pass 1: the butt dipped when leaning back, and the hands over-reached during the door glance.
  - Pass 2: knee flips while the feet swung from in front to behind (several attempts).
  - Final: the hips rise first, the feet unroll relative to the shins while lifted, a floor guard, and the spine pitches forward early so the head stays under 1.2 m.
  - It reads as a compact panicky hop-turn rather than a careful kneel. That is OK for v01; a v02 could add a hand plant at the door side.

**Still to judge in Unity:**
- the speed scaling of the in-place clips on the real capsule;
- JumpOut's drop alignment with the actual sill height;
- the Escape_Scramble_Start sit pose against the real Cargo_Sit_Idle once it exists;
- the Cop_Trip → ragdoll hand-off velocity;
- whether Struggle_Carried reads as an additive layer on a held pose.

## Files

| File | Role |
| --- | --- |
| `ep_core.py` | Whole-body poser on Idle frame 1, built on Idle_Knock_v03's `acting_core`. Provides hinge IK, sole pivots (heel / toe hinge / toe tip), the run-leg gait with ground-riding stance, the standing helper with the pelvis support solve, the FK arm/spine/head helpers, keyed IK paths, rigid pose blending and the review stage. |
| `clips_police.py` | Cop_Run, Cop_Run_Fat, Flee_Run, Cop_Punch, Cop_ShakeFist, Cop_Aim_Raise, Cop_Aim, Cop_Trip. |
| `clips_escape.py` | Hit reacts, Stagger, Struggle_Carried, Escape_Scramble, JumpOut, Escape_Scramble_Start (and the provisional cargo sit pose). |
| `build_ep_v01.py` | Driver: `--metrics`, `--review`, `--trace`, `--final --dest`. Never overwrites. |
| `validate_ep_v01.py` | Independent validation of the saved `.blend` and `.fbx` (refuses to overwrite its report). |
| `make_previews_ep_v01.py` | MP4 (loops ×3) and contact sheets from the saved `.blend` files. |
| `validation_v01.json` | Validator report for the delivered build. |
| `authoring/<Clip>_v01_authoring.json` | Beats, contracts, events, ground speed, IK overreach, hips first/last. |
| `clips_manifest_v01.json` | For the Unity installer: file, take, frames, loop, events (s and frame), contracts, ground speed, suggested use, action digest. |
| `provenance_v01.json` | sha256 of the inputs and of every package file. |

## Building locally

Run from the repository root. The scripts work with the `bpy` module (`pip install bpy`, Python 3.13) or with Blender 5.2.x. With Blender, prefix the commands with `blender -b --factory-startup --python <script> --` (the preview script needs Pillow and `ffmpeg`, so run it with a Python that has `bpy` and Pillow). Without Git LFS, `acting_core` uses the rig JSON automatically. With the LFS A v04 `.blend` present it uses that file, and the results are identical.

```
PKG=ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Escape_Police_v01
OUT=<empty folder>, e.g. ../ep_build

python $PKG/build_ep_v01.py --clip all --final --dest $OUT            # 16 x .blend/.fbx/_authoring.json, ~20 s
python $PKG/validate_ep_v01.py --dir $OUT --out $OUT/validation.json   # ~25 s
python $PKG/make_previews_ep_v01.py --dir $OUT --out $OUT/Previews    # MP4 + contact sheets, ~8 min (Workbench, 360 px)

# while authoring: numbers only, or review renders (Workbench grid per view)
python $PKG/build_ep_v01.py --clip Cop_Punch --metrics
python $PKG/build_ep_v01.py --clip Cop_Punch --review /tmp/rev --times 0.3,0.45 --views front,three_quarter_r --res 420
```

On a headless Linux machine, rendering needs EGL (for example `apt install libegl1 libgl1-mesa-dri`). Building and validating do not.

Unity import, as Walk_v02 / Idle_Knock_v03 (not done here):
- Generic, Copy From Other Avatar (A v04), **Preserve Hierarchy**, Anim. Compression Off, Resample Curves on.
- Loop Time on for the loops, over the full take including the duplicated last frame; Loop Pose off.
- Events from `clips_manifest_v01.json`: `Hit`, `Land`, `Ragdoll`.

## v02 fixes (2026-10-11): police clips

New revisions of three police clips, authored in `clips_police_v02.py` (it imports `ep_core` / `clips_police`, which stay unchanged) and built with `build_ep_v02.py`. The v01 files are untouched. Validation (`validation_v02_police.json`, saved files, 120 Hz): **20/20 for all three**.

| Clip | Frames | s | Floor pen. (mm) | Slide / 1/120 s (mm) | Largest key step (°) | Loop seam | FBX animated error |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| Cop_Run_Fat_v02 | 1–17 | 0.533 | 0.57 | 0.75 | 10.5 | 0.0 | 2.3e-5 |
| Cop_Punch_v02 | 1–37 | 1.20 | 0.57 | 0.72 | 22.0 (pointing finger) | – | 3.6e-5 |
| Cop_ShakeFist_v02 | 1–67 | 2.20 | 0.73 | 0.12 | 20.2 | – | 1.9e-5 |

- **Cop_Run_Fat_v02.** v01 read as a brisk walk. Now it is a heavy waddle *run*. **Ground speed 2.2 m/s** (v01: 1.8; play at speed / 2.2).
  - Gait: a 16-frame cycle with short toe-out strides (17°) on a wide track. The swing foot circles outward.
  - Each foot: heel lands at 0.000 / 0.267 s, toe-off at 0.213 / 0.480 s. That leaves 0.053 s of near-flight per step, with both feet off the street.
  - Bounce: he lands while still falling, and the hips sink 7.2 cm in 0.08 s (deep knee bend). Hip height ranges 0.618–0.712 m.
  - Belly bounce: the chest folds 14° forward and down 0.025 s after each landing (peak ~0.11 s), then rebounds past upright (~0.21 s).
  - Head: the giant head nods 2–3 frames behind the chest (peak ~0.18 s) and whips back up through the next landing.
  - Waddle: the whole body rocks over the stance foot (pelvis 9° + spine 8°, pelvis sway ±6.5 cm). The head counter-tilts 0.09 s late.
  - Arms: out 36° (wider when forward) and pumping ±40° with a 1.5-frame lag. They flop down on every landing.
- **Cop_Punch_v02.** v01 had no body weight behind the strike. The **`Hit` event is unchanged at 0.45 s (frame 14.5)**, at full extension, and the 0.45 s telegraph is kept. The clip is now 1.2 s.
  - 0.00–0.07: the weight shifts onto the left foot.
  - 0.07–0.21: the right foot steps 22 cm back (toe out 20°). The weight goes back onto it: hips 12 cm back, body twisted 45° away, leaning back. The front toes lift.
  - 0.10–0.33: haymaker cock with the pointing finger, then the straining quiver (as v01).
  - 0.33–0.45, the strike drives off the back leg:
    - the back heel peels 38° about the toe hinge;
    - the hips and chest rotate into it, with the chest leading;
    - the weight goes onto the bent front knee, and the head goes forward.
  - 0.45–0.60, follow-through:
    - the chest keeps twisting to +44°;
    - the fist carries past the target and across;
    - he topples onto the front ball, and the left arm flies out.
  - 0.48–0.66: the back foot is pulled off the street and swings forward to catch him **on its exact Idle spot** (no sliding while planted).
  - 0.66–0.90: teeter. 1.0–1.1: a small "hmph" nod. Idle frame 1 at 1.20.
- **Cop_ShakeFist_v02.** In v01, at ~0.77 s and ~1.57 s, the fist swung behind or into the head in the three-quarter view.
  - The right arm is now an explicit IK path in the chest frame. The hand follows the forearm, and the elbow points out and down.
  - That keeps the fist raised **out to the side and in front of the face**: it stays visible from the side camera too.
  - The last wind-up pulls the fist *down in front* (it used to go back behind the head) before the final thrust.
  - Everything else is the v01 acting (gather, thrust, 4.6 Hz shake, hand on hip, stamp, deflate, no-no head shake).
  - Measured on the saved files every 1/120 s, right fist versus the head and hood vertices:

    | | Min 3D distance | Fist hidden behind the head (3/4 camera) |
    | --- | --- | --- |
    | v01 | 79.5 mm at 1.55 s | up to 99 % (screen gap 0 mm) |
    | v02 | 86.8 mm at 1.52 s, to the hoodie collar during the pull-down | 0 % at every sample; ≥ 79 mm screen gap in the shake |
- **Pop scan** (worst accelerations): Run_Fat 182 m/s², all periodic hand and head motion. Punch 440 / 413 m/s² on the right hand at the strike launch (0.35 s) and the Hit (0.45 s), both intended. ShakeFist 227 m/s² at the stamp jolt (1.17 s).
- **Files:**
  - `clips_police_v02.py`;
  - `Cop_Run_Fat_v02` / `Cop_Punch_v02` / `Cop_ShakeFist_v02`: `.blend`, `.fbx` and `_authoring.json` each;
  - `validation_v02_police.json`;
  - `Previews/v02/<Clip>_v02_{side,three_quarter}.mp4`, `<Clip>_v02_contact_sheet.png`, frames in `Previews/v02/_frames/<Clip>/`.

По-русски: толстый коп теперь именно бежит, а не идёт быстрым шагом: тяжёлое приседание на каждом шаге, «живот» и голова догоняют с запозданием, переваливается с ноги на ногу; скорость 2,2 м/с. В ударе вес идёт за кулаком: шаг назад на замахе, толчок задней ногой, после удара его заносит, и задняя нога ловит его ровно на месте Idle (Hit по-прежнему 0,45 с). В ShakeFist кулак больше не уходит за голову: он поднят сбоку и перед лицом и виден с обеих камер. Все три клипа проходят валидатор 20/20.

## v02 fixes (2026-10-11): escape clips

New revisions of four escape clips, authored in `clips_escape_v02.py` (it imports `ep_core` / `clips_escape` / `clips_police`, which stay unchanged) and built with `build_ep_v02.py`. The v01 files are untouched. Validation (`validation_v02_escape.json`, saved files, 120 Hz): **20/20 for all four**.

| Clip | Frames | s | Floor pen. (mm) | Slide / 1/120 s (mm) | Largest key step (°) | FBX animated error | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Escape_Scramble_Start_v02 | 1–31 | 1.00 | 0.14 | 1.00 | 21.9 | 1.9e-5 | mesh top 1.019 m (limit 1.2) |
| JumpOut_v02 | 1–35 | 1.133 | 1.38 | 1.40 | 24.7 | **9.5e-5** (v01: 2.8e-4) | `Land` 0.567 s, unchanged |
| Hit_React_Front_v02 | 1–34 | 1.10 | 1.92 | 0.33 | 21.5 | 1.9e-5 | |
| Stagger_v02 | 1–49 | 1.60 | 0.69 | 0.13 | 23.3 | 1.9e-5 | |

- **Escape_Scramble_Start_v02 (redo).** v01 started on a provisional sit pose and floated ~0.15 s in its hop-turn.
  - **Frame 1 = the frozen cargo sit contract**: the exact raw values of `Idle_Knock_v03/Cargo_Sit_Contract_v04.json` (sha256 `37a1e77d…af7e`, full hash in the authoring JSON), hips (−0.357, 0, 0.114). The script reads it from `../Idle_Knock_v03/` or `$CARGO_SIT_CONTRACT`. Start error 8e-7 vs `Cargo_Sit_Idle_v04.blend` frame 1. **Last frame = Escape_Scramble_v01 frame 1** (end error 7e-7).
  - The contract rebuilds exactly with `ep_core.Body.pose` except the legs: the cargo IK rolls thighs and shins 6.85° about their own axes versus ep_core's hinge IK. That twist is applied on top and fades out while the legs swing (it never moves a joint).
  - Beats: 0.09–0.15 SNAP glance (head ~55° to the doors, shoulders jolt); 0.15–0.32 frozen stare with a tremble; 0.27–0.50 the right hand lets go and slaps the floor on the doors side while the trunk bows over it and the butt rocks forward on the sit bones and lifts; 0.42–0.61 the left hand reaches across and plants; 0.49–0.82 knees up, heels kick up behind, the folded legs drop round the outside, the left knee lands at 0.82; the pelvis swivels ~94° round the right palm with the head kept on the doors; 0.65–0.73 the right palm hops onto its crawl spot; 0.74–0.97 the left hand steps onto its crawl frame-1 spot.
  - **The last 0.1 s is Escape_Scramble itself** (crawl time −0.1…0) carried so the van floor stands still: the body already moves toward the doors at 1.2 m/s, so the hand-off to the crawl and the moving capsule has no velocity jump.
  - **Floor contact at every 120 Hz sample** (checked on the saved file): butt + feet, right palm, left palm, left knee, then the left palm. Planted palms and the knee are pressed onto the floor by a skinned-mesh contact solve (the crawl's own contacts hover ~1 cm); swinging feet keep ≥ 1.2 cm at the keys.
  - The few in-air samples of the slap's wrist, the palm re-plant and the leg swing that turned faster than 22° per half frame are smoothed locally (`limit_rotation_steps`, copied from the cargo package); planted limbs and the contract ends are never touched.
- **JumpOut_v02 (fix).**
  - **The pop at 0.30–0.33 s is gone.** The hips, spine and head unfolded ~80° in 0.04 s after the peek. Now each unfolds in one long ease, the head first (0.30–0.47), then the spine (0.31–0.48) and the hips (0.32–0.49). The gulp (head dip at 0.30, a sharp shoulder jolt at 0.283) and the arms swinging back read first, and the toe push starts at 0.285. Frog hop, flight, the `Land` event (0.567 s), stumble and run are v01; both contracts unchanged (start 1.6e-7, end 0).
  - **FBX error root cause.** The exporter writes each bone's parent-relative rotation, rest included, as XYZ Euler computed in float32. For the shoulders that rotation sits at Euler Y = ±90° *exactly* at rest, which is fine (Blender takes the well-conditioned gimbal branch). A few hundredths of a degree off 90°, with |cos Y| between ~1e-6 and ~1e-3, the X/Z split loses precision. v01 started the shoulder blend toward the run with an ease-in at 0.38 s. The first sample after it (frame 12.5) had Y = 90.0034° (cos Y = 6e-5), and the left shoulder chain reimported 0.28 mm off.
  - **Fix:** the gulp adds a shoulder hunch (protraction) with a sharp onset exactly on a sample (0 at 0.283 s, ~9° one sample later). A pure shrug keeps Y at 90°; the protraction carries the shoulders decisively off the band and fades into the Flee_Run shoulders through the landing blend. The build reports any sample in the band (`shoulder_gimbal_band_samples`): only the inherited Flee_Run swing remains (|cos Y| = 1.3e-3, 9.5e-5 error).
- **Hit_React_Front_v02 (polish).** A much bigger "OOF". 0.00–0.05: the pelvis bows, the butt shoots back 10.5 cm, knees buckle 11.5 cm, the chest snaps forward. 0.05–0.15: the big head tips back on the impact, then whips down past the chest (chest ~70° down, head drooping); the arms fly out, then clutch the belly. 0.15–0.50: held fold with two wheezes (chest heaves, shoulder hitches, head bobs). 0.50–0.98: slow groggy recovery with a woozy sway, head last. Idle → Idle, 1.10 s.
- **Stagger_v02 (polish).** Wobblier and dazed, 1.60 s, Idle → Idle. The pelvis leads and the feet catch up: seven steps. 0.16–0.34 right foot out to his right (lean 17°, knees 9 cm). 0.36–0.54 left crosses over in front. 0.50–0.72 forward lurch, chest 20° down, right foot catches 32 cm ahead. 0.80–1.06 near-fall backward: arms windmill, knees buckle 12 cm, the left foot saves it out to his left. 1.06–1.44 shuffles home onto the exact Idle spots. A bigger dizzy head circle (1.5 Hz) and arms flapping for balance throughout. Planted feet do not slide (0.13 mm).
- **Pop scan** (worst accelerations, saved files, v02 vs v01): JumpOut **394** (head top 0.30 s) vs **1746**; Escape_Scramble_Start 435 (left toes as the leg opens into the kneel, 0.78 s) vs 317; Hit_React_Front 382 (head top at the impact, intended) vs 316; Stagger 315 (hands, windmill) vs 274.
- **Files:**
  - `clips_escape_v02.py`;
  - `Escape_Scramble_Start_v02` / `JumpOut_v02` / `Hit_React_Front_v02` / `Stagger_v02`: `.blend`, `.fbx` and `_authoring.json` each;
  - `validation_v02_escape.json`;
  - `Previews/v02/<Clip>_v02_{side,three_quarter}.mp4`, `<Clip>_v02_contact_sheet.png`, frames in `Previews/v02/_frames/<Clip>/`.
- Build the cargo clip with the contract reachable: `CARGO_SIT_CONTRACT=<path to Cargo_Sit_Contract_v04.json>` until the packages are merged.

По-русски: Escape_Scramble_Start теперь начинается ровно с настоящего сидения Cargo_Sit_Idle_v04 и всё время касается пола: резкий взгляд на двери, замер, шлепок правой ладонью, разворот на руках, колени под себя, и последние 0,1 с — уже сам Escape_Scramble. В JumpOut убран рывок на 0,30–0,33 с (разгиб растянут, голова ведёт), а ошибка FBX была из-за плеч у самого «гимбала» Эйлера (Y ≈ 90°) — исправлено резким стартом сутулости в «глотке». Hit_React_Front сгибается гораздо сильнее и медленно приходит в себя, Stagger шатается сильнее, с почти-падением назад; все четыре 20/20.

## Кратко по-русски

Пакет Escape_Police_v01: 16 клипов на общем риге Buddy (полицейские — тоже сосиски).

- **Побег.** Escape_Scramble_Start (из сидения в кузове: резкий взгляд на двери, затем рывок на четвереньки). Escape_Scramble (паническое ползание к двери, цикл 0,5 с, ниже 1,2 м). JumpOut (прыжок лягушкой на порог, взгляд вниз, падение «бомбочкой» на улицу, приземление и сразу бег). Бонус: Flee_Run — панический бег, в который приземляется JumpOut.
- **Носят на руках.** Struggle_Carried — брыкается и извивается, аддитивный цикл; кадр 1 = Idle.
- **Удары.** Hit_React_Front / Back / Head и Stagger — шатается с шагами.
- **Полиция.** Cop_Run (тяжёлый бег), Cop_Run_Fat (толстяк вразвалку, как пингвин), Cop_Punch (замах ровно 0,45 с, событие Hit), Cop_Aim_Raise + Cop_Aim (пистолет двумя руками, без пропа), Cop_Trip (спотыкается и ныряет вперёд; последний кадр — передача в регдолл), Cop_ShakeFist (грозит кулаком уезжающему фургону, топает ногой).

Всё в 30 fps, на месте. Опорные стопы, колени и ладони не скользят: в тесте не больше 1,5 мм за шаг выборки 1/120 с; швы циклов точные.

Валидатор проверяет сохранённые файлы. 15 из 16 клипов проходят 20/20. У JumpOut одна точка FBX отличается на 0,28 мм при пороге 0,15 мм: причина не найдена, на вид незаметно, но проверка красная.

Начальная поза Escape_Scramble_Start — временная замена ещё не сделанного Cargo_Sit_Idle_v04. В git лежат только скрипты и JSON; .blend/.fbx/превью собираются командами выше (около 20 с, превью около 8 мин).
