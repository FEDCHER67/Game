# Sausage Buddy — Crowd activity set (Crowd_v01)

Original keyframe/procedural animation for the crowd NPCs (rig `Buddy_Rig_Mixamo65`, 65 bones). No external motion
was used. Authored 2026-10-07 by a cloud Claude session (branch `cloud/anim-crowd-v01`).

**Only text is committed** (scripts, JSON, this README). The `.blend` / `.fbx` deliverables and the preview MP4s are
regenerated deterministically by the scripts below (cloud sessions cannot push binaries). Every number in this file
comes from `validation_crowd_v01.json` / `crowd_manifest_v01.json`, produced by the same commands.

## 1. Clips

30 fps, frame 1 to N+1. Loops: last frame == first frame exactly (Unity: Loop Time on, Loop Pose off).
In place: the root never moves; transitions that need it move the feet or the pelvis inside the clip and the clip
says where the prop must be (section 3).

| Clip | Frames | s | Loop | Starts on | Ends on | What it is |
| --- | --- | --- | --- | --- | --- | --- |
| `BenchSit_Enter` | 1–61 | 2.0 | – | idle | bench_sit | glance back, fold and reach back onto the seat, **plop** (event `Sit` 1.12 s), head lags back, bounce, hands to the thighs |
| `BenchSit_Loop` | 1–211 | 7.0 | yes | bench_sit | bench_sit | look left/right, big **yawn-stretch** with arms overhead, arms flop on the thighs, nervous **knee jiggle** with drumming fingers, belly scratch, "nu, ladno" knee slap |
| `BenchSit_Exit` | 1–52 | 1.7 | – | bench_sit | idle | hands to the knees, nose over the toes, push up, back stretch with hands on the lower back |
| `BeachLie_Enter` | 1–88 | 2.9 | – | idle | beach_lie | look at the towel, squat, sit down on the hands (plop), sigh at the sky, lie back, hands behind the head, cross the leg |
| `BeachLie_Loop` | 1–211 | 7.0 | yes | beach_lie | beach_lie | breathing belly, crossed foot bobs to music with a head sway, face turns to the sun, **a fly: two swats**, happy wiggle |
| `BeachLie_Exit` | 1–91 | 3.0 | – | beach_lie | idle | uncross, crunch up, rock forward into a squat, stand, brush the sand off the butt |
| `ShopQueue_Loop` | 1–181 | 6.0 | yes | idle | idle | lean out to **peek past the queue**, crane, snap back, **big impatient sigh**, hand on hip + toe taps (event `Tap` ×3), glare back down the queue |
| `SmokeCorner_Enter` | 1–58 | 1.9 | – | idle | smoke | hands cupped at the lips, two lighter flicks, first drag, exhale aside |
| `SmokeCorner_Loop` | 1–181 | 6.0 | yes | smoke | smoke | drag (chest fills), chin up, long exhale aside, look at the ash + three thumb taps, look around, "sup" chin-up, quick second puff |
| `SmokeCorner_Exit` | 1–73 | 2.4 | – | smoke | idle | last look, **flick the butt away** (event `Flick`), step on it (event `Step`), twist it out on the ball of the foot with the hips, step back |
| `PhoneTalk_Enter` | 1–40 | 1.3 | – | idle | phone | hand into the hoodie pocket, glance at the screen, phone to the ear "allo?" |
| `PhoneTalk_Loop` | 1–211 | 7.0 | yes | phone | phone | "da… da…" nods, **"CHTO?!" recoil** with the free hand flung open, three argument chops, turns away with a hand on the hip, eye-roll, laugh with a hand on the belly |
| `PhoneTalk_Exit` | 1–43 | 1.4 | – | phone | idle | phone down, stares at the screen (hung up?), into the pocket |
| `BusWait_Loop` | 1–196 | 6.5 | yes | idle | idle | snap look up the road (his left) with the **left hand shading the eyes**, **up on tiptoes** peering, drops with a huff, heel-toe rocking, "maybe from the right?", shrug-sigh |
| `BarDoor_Enter` | 1–46 | 1.5 | – | idle | lean | glance back at the wall, dip, **flop back onto the wall** (head whips), right foot up onto the wall, hands into the pocket |
| `BarDoor_Loop` | 1–211 | 7.0 | yes | lean | lean | watches a passer-by + "sup" chin-up, **blissful back scratch on the wall**, slow look the other way, heel taps the wall to music |
| `BarDoor_Exit` | 1–40 | 1.3 | – | lean | idle | gather, push off with the shoulders, foot down, forward overshoot, hands out |
| `KioskBuy` | 1–139 | 4.6 | – | idle | idle | lean in, **point "that one"** (two jabs), rummage in the hoodie pocket, pay (event `Pay`), take it (event `Take`), tuck it in, **happy double bounce on the toes**, glance where he goes next |
| `Chat_Loop` | 1–241 | 8.0 | yes | idle | idle | 4 s talking (right-hand beats, "and THEN!" both hands open, point "you know?") then 4 s listening (hand to chin, two nods, **laughs: head back, doubles over, thigh slap**) |
| `Chat_Loop_Mirror` | 1–241 | 8.0 | yes | idle | idle | exact mirror image of `Chat_Loop` (L/R swapped). Play it on the partner at normalized time +0.5, so one talks while the other listens |
| `Flee_Panic_Run` | 1–11 | 0.333 | yes | flee_run | flee_run | in-place panic run, **both arms flailing above the head** (one shake per step, alternating, floppy wrists), head thrown back, knees driving, flight phase; authored at **4.5 m/s** (`GreyboxNpc.FleeSpeed`) |

Contract poses (frame-1/last-frame poses that chain exactly; raw keyed values are identical):
`idle` = A v04 Idle frame 1; `bench_sit`, `beach_lie`, `smoke`, `phone`, `lean` = the base pose of the matching loop;
`flee_run` = run frame 1. `ShopQueue`, `BusWait`, `Chat` and `KioskBuy` start and end on Idle frame 1, so they need no
transitions.

Why `Chat_Loop_Mirror` is a separate clip: Unity's import Mirror option works for Humanoid only, and the Buddy clips
are Generic, so the mirror is baked (`crowd_core.mirror_params` swaps the L/R parameters on the same Idle base, so the
mirrored clip still starts and ends on the exact Idle frame 1).

## 2. Validation (`validation_crowd_v01.json`)

`validate_crowd.py` opens every saved `.blend`, samples at 120 Hz and re-imports every `.fbx`.

| Clip | Checks | Seam | Max key step | Sole pen. (keys / 120 Hz) | Planted slide (keys / 120 Hz) | Lowest body vertex | Props | FBX anim. err |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ShopQueue_Loop` | 18/18 | 0.0 | 8.4° | 0.00 / 0.18 mm | 0.55 / 0.55 mm | +77.0 mm | – | 1.8e-05 |
| `BusWait_Loop` | 18/18 | 0.0 | 20.5° | 0.00 / 0.49 mm | 0.45 / 0.70 mm | +76.7 mm | – | 1.8e-05 |
| `Chat_Loop` | 18/18 | 0.0 | 12.0° | 0.00 / 0.10 mm | 0.00 / 0.01 mm | +75.3 mm | – | 1.9e-05 |
| `KioskBuy` | 18/18 | – | 14.4° | 0.00 / 0.26 mm | 0.67 / 0.67 mm | +78.7 mm | – | 1.9e-05 |
| `Chat_Loop_Mirror` | 18/18 | 0.0 | 12.0° | 0.00 / 0.10 mm | 0.00 / 0.01 mm | +75.3 mm | – | 1.9e-05 |
| `SmokeCorner_Enter` | 18/18 | – | 20.8° | 0.00 / 0.03 mm | 0.00 / 0.00 mm | +81.1 mm | – | 1.9e-05 |
| `SmokeCorner_Loop` | 18/18 | 0.0 | 10.8° | 0.00 / 0.13 mm | 0.00 / 0.01 mm | +79.4 mm | – | 1.9e-05 |
| `SmokeCorner_Exit` | 18/18 | – | 17.4° | 0.00 / 1.32 mm | 0.99 / 0.99 mm | +78.0 mm | – | 1.8e-05 |
| `PhoneTalk_Enter` | 18/18 | – | 22.2° | 0.00 / 0.07 mm | 0.00 / 0.00 mm | +81.6 mm | – | 1.8e-05 |
| `PhoneTalk_Loop` | 18/18 | 0.0 | 14.1° | 0.00 / 0.05 mm | 0.00 / 0.01 mm | +79.2 mm | – | 1.8e-05 |
| `PhoneTalk_Exit` | 18/18 | – | 17.5° | 0.00 / 0.01 mm | 0.00 / 0.00 mm | +81.6 mm | – | 1.9e-05 |
| `BarDoor_Enter` | 18/18 | – | 18.8° | 0.00 / 0.23 mm | 0.00 / 0.02 mm | +76.9 mm | 0.1 mm | 1.8e-05 |
| `BarDoor_Loop` | 18/18 | 0.0 | 4.3° | 0.00 / 0.11 mm | 0.00 / 0.01 mm | +72.0 mm | 0.0 mm | 1.8e-05 |
| `BarDoor_Exit` | 18/18 | – | 16.8° | 0.00 / 0.36 mm | 0.00 / 0.02 mm | +76.0 mm | 0.0 mm | 1.8e-05 |
| `BenchSit_Enter` | 18/18 | – | 19.4° | 0.00 / 0.33 mm | 0.00 / 0.14 mm | +72.1 mm | 2.8 mm | 1.8e-05 |
| `BenchSit_Loop` | 18/18 | 0.0 | 20.9° | 0.00 / 0.03 mm | 0.61 / 0.61 mm | +83.7 mm | 0.1 mm | 1.8e-05 |
| `BenchSit_Exit` | 18/18 | – | 8.5° | 0.00 / 0.35 mm | 0.00 / 0.12 mm | +70.8 mm | 0.1 mm | 1.8e-05 |
| `BeachLie_Enter` | 18/18 | – | 19.9° | 0.00 / 0.17 mm | 0.51 / 0.61 mm | -9.2 mm | – | 1.9e-05 |
| `BeachLie_Loop` | 18/18 | 0.0 | 16.4° | 0.00 / 0.00 mm | 0.00 / 0.01 mm | +4.0 mm | – | 1.8e-05 |
| `BeachLie_Exit` | 18/18 | – | 19.3° | 0.00 / 0.78 mm | 0.00 / 3.05 mm | +3.9 mm | – | 1.9e-05 |
| `Flee_Panic_Run` | 18/18 | 0.0 | 22.0° | 0.00 / 1.59 mm | 0.11 / 0.77 mm | +85.7 mm | – | 1.8e-05 |

Contract chains (max world-matrix difference between every clip end that claims the pose): `idle` 0, `smoke` 0, `phone` 0, `lean` 0, `bench_sit` 0, `beach_lie` 0, `flee_run` 0. Overall: **PASS**.

18 checks per clip: fps, 65 bones in rig order, rig/mesh data unchanged, one action, finite, no reflection, no quaternion
sign flips, key step < 25°, seam, sole penetration, planted slide, body vs floor, props, FBX bones/hierarchy, FBX bind,
FBX animated error < 1.5e-4, one take + armature only, FBX seam.

**Keys vs 120 Hz.** Foot contact is judged on the keyed half-frames (the authored data). Between keys the leg chain is
interpolated linearly, so during the fastest body moves a planted foot can wander slightly: up to 1.6 mm into the floor
(the run's toe pads at touchdown, the support toe in SmokeCorner_Exit's big weight shift) and 3.1 mm of heel-skin creep in
the deepest squat of BeachLie_Exit. These in-between values are in the `subframe_120hz` block of the report; they are
below what reads at gameplay distance and Unity interpolates the same keys the same way. `BeachLie_Enter`'s lowest
vertex (−9.2 mm) is a fingertip of a palm planted on the towel (design limit 1 cm).

Notes on the checks:
- **Planted feet**: net horizontal drift of every sole vertex touching the floor (z < 2 mm) since it touched down, in
  the ground frame (the run uses a 4.5 m/s treadmill frame). Heel lifts bend the shoe at the toe joint, so the **toe pad
  stays exactly in place** while the heel peels; while the shoe is bent, only the toe pad counts as planted. Feet that
  step on purpose are listed as `feet_free` windows in the clip registry (stepping on the cigarette, the foot on the wall,
  crossing/uncrossing the legs and the small foot scoots on the towel). Toe taps (heel planted) and the knee jiggle
  (toes planted) are checked like any planted foot.
- **Sole penetration**: the A v04 rest sole is 1.0 mm below z = 0, so ≤ 1.1 mm passes.
- **Body vs floor**: lowest non-sole vertex ≥ −1 cm (the design limit in `NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md` §5.3).
- **Props**: bench seat/backrest and the BarDoor wall: no vertex more than 5 mm inside.
- **FBX**: 65 bones, order + hierarchy + bind matrices equal to the rig JSON (`Walk_v02.fbx` when it is a real file),
  one take, armature only, re-imported world matrices within 1.5e-4 of the blend, re-imported seams.

## 3. Unity hook-up and placement contract

Import like `Walk_v02` (`Assets/OnlyVolunteers/Characters/SausageBuddy/Animations/Walk_v02.fbx.meta`): Generic, Copy From
Other Avatar = A v04 avatar, **Preserve Hierarchy on**, Optimize Game Objects off, Anim. Compression Off, Resample Curves
on; one take per file `Buddy_Rig_Mixamo65|<Clip>`, first frame 0, last frame N; Loop Time on for loops; Root Transform
Position (Y) based upon Original. `applyRootMotion` stays false. Events (seconds) are in `crowd_manifest_v01.json`.

Placement relative to the NPC root (feet origin on the floor; the character faces −Y in Blender = Unity +Z):

| Activity | Prop placement |
| --- | --- |
| BenchSit | seat top **0.45 m**, seat front edge **0.10 m behind** the root, seat to 0.68 m; backrest from 0.70 m behind (the big hood needs the room). The root stays on the floor in front of the bench; the feet keep their Idle spots. Replaces the "sink 0.35 m" hack in `CrowdWalker.ApplyPose`. |
| BeachLie | towel/sand at floor level; the body lies **behind** the root (hips ~0.42 m, head top ~1.3 m behind). Needs a free 0.9 × 2.2 m patch from 0.45 m in front of the root. Replaces the "tip over" hack. |
| BarDoor | wall plane **0.36 m behind** the root; the hood touches it and the right sole rests on it. |
| KioskBuy | counter in front: front edge 0.42 m ahead of the root, top 1.0 m. |
| Chat | two NPCs face each other **1.15 m** apart: `Chat_Loop` on one, `Chat_Loop_Mirror` at normalized time +0.5 on the other. |
| ShopQueue / BusWait / SmokeCorner / PhoneTalk | free standing; cigarette and phone are implied by the hand (parent a prop to `mixamorig:RightHand` if wanted: the cigarette sits between index and middle finger, the phone in the right palm). |
| Flee_Panic_Run | in place; playback speed = ground speed / 4.5. Unlike `Panic_Run_Loop` (GreyboxBuddySetup), this is a variant with the arms over the head. |

Suggested Animator use (design doc §5.4): the Activity sub-machine plays `<Activity>_Enter` → `<Activity>_Loop` (loop
until the dwell ends) → `<Activity>_Exit` → locomotion. `CrowdWalker.StartActivity/EndActivityNow` currently only toggles
Idle and a mesh offset; the hook-up is the lead's job.

## 4. How it is built

| File | Role |
| --- | --- |
| `crowd_core.py` | Parametric pose rig on top of `../Idle_Knock_v03/acting_core.py` (shared library, unchanged): flat parameter dict → pose (all 0 = Idle frame 1); pelvis/spine/neck/head FK, arms FK + IK (minimal-roll, keeps the FK twist, targets can ride a bone: phone at the ear, hands in the pocket, palms flat on a support), legs IK with a hinge-axis knee pole (cannot flip), foot roll about the toe joint (heel up) or the heel (toe up), toe flatten, ball twist; mesh contact solver (seat, towel, wall) on the skinned mesh; mirror; `Track`/`FitTrack` pose-to-pose curves (keys auto-fit the FK arm to IK targets so IK hand-offs never whip). |
| `clips_stand.py` | ShopQueue, BusWait, Chat (+ mirror), KioskBuy. |
| `clips_props.py` | SmokeCorner, PhoneTalk, BarDoor (Enter/Loop/Exit) and their contract poses. |
| `clips_floor.py` | BenchSit, BeachLie (Enter/Loop/Exit), bench/towel geometry and contracts. |
| `clips_run.py` | Flee_Panic_Run. |
| `clips_crowd.py` | Registry: clips, contracts, placement. |
| `build_crowd.py` | Author → key (half-frame, linear, exact contract values at both ends) → review renders / `--final` save + FBX / `--manifest`. |
| `validate_crowd.py` | Independent checks of the saved files (section 2). |
| `make_previews.py` | Review grids and MP4s from rendered frames. |
| `crowd_manifest_v01.json` | Clip list, frames, loop flags, contracts, events, placement. |
| `validation_crowd_v01.json` | The validation report of the files built by the commands below. |

Rig input: `SAUSAGE_BUDDY_A_v04.blend` (read-only) or, when the `.blend` files are Git LFS pointers, the plain-JSON export
`../Idle_Knock_v03/rig_Buddy_Mixamo65_A_v04.json` (rig + Idle frame 1 + skinned A mesh); `acting_core` switches
automatically. Nothing outside `Crowd_v01` is written.

### Commands (from this folder)

Blender 5.2 (`blender -b --factory-startup --python <script> -- <args>`) or the PyPI module (`pip install bpy`, then
`python <script> <args>`) both work; the cloud session used `bpy` 5.2.2 from PyPI, Cycles CPU for renders.

```
# final deliverables: <Clip>_v01.blend / .fbx / _authoring.json for all 21 clips (refuses to overwrite)
python build_crowd.py --clip all --final
python build_crowd.py --clip all --manifest crowd_manifest_v01.json      # (already committed)
python validate_crowd.py --out validation_crowd_v01.json                # (already committed; refuses to overwrite)

# review frames (nothing saved in the package); views side, three_quarter, front
python build_crowd.py --clip BenchSit_Loop --review /tmp/rev --every 2 --res 320
python make_previews.py grid /tmp/rev /tmp/BenchSit_Loop.png --cols 12 --size 150 --title BenchSit_Loop

# preview MP4s: every frame, then 3 loops for loop clips
python build_crowd.py --clip BenchSit_Loop --review /tmp/f/BenchSit_Loop --every 1 --seq --views side,three_quarter --res 480
python make_previews.py mp4 /tmp/f/BenchSit_Loop Previews/BenchSit_Loop_v01 --loops 3
```

A full `--final` build of the 21 clips plus validation takes a few minutes on 4 CPU cores (no GPU needed).

## 5. Review log (what I looked at and what I fixed)

Every clip was rendered (Cycles CPU, flat-colour JSON mesh proxy, side + three-quarter, Chat with its mirrored
partner, run on a 4.5 m/s treadmill floor) and looked at in three passes: pass 1 every 3rd frame of all 21 clips,
pass 2 every 2nd frame of the 12 clips changed in pass 1, pass 3 every frame of all clips (MP4, 3 loops for loops) plus
a 10-frame strip per clip. Before pass 1 the key poses were blocked on pose sheets (hand on hip, phone at the ear,
cigarette hold and drag, brow shade, watch, point, bench sit, beach lie, wall lean) and checked from front/side/¾.

| Pass | Clip | What I saw | Fix |
| --- | --- | --- | --- |
| 0 | all | smoker's free arm read as a boxer guard; wall lean not touching the wall; beach lie floating on the hood with the "crossed" leg in the air | IK forearm across the belly; wall contact solve; pelvis pitch −64° so butt **and** hood touch the towel; ankle solved onto the left knee |
| 0 | all | technical: arm/leg roll flips at IK hand-offs and when the thigh points along the knee pole; summing instead of overriding pose snippets (arms at 240°); a stale action overriding mesh contact solves; floating IK targets sweeping in from the origin | minimal-roll IK in the elbow plane, hinge-axis knee pole, override semantics, FK auto-fit to IK targets at keys, target hold rules (all in `crowd_core.py`) |
| 1 | ShopQueue | peek and sigh too shy at crowd distance | ~1.3× lean/slump |
| 1 | BusWait | hand landed on top of the head instead of shading the eyes (right hand cannot reach the brow while he looks left) | shade with the **left** hand, head-relative brow target |
| 1 | KioskBuy | after paying he just stood there | happy double bounce on the toes; review counter made a slab |
| 1 | Chat | review cameras cropped the partner | chat cameras |
| 1 | SmokeCorner_Exit | the twist-out was a foot-only wiggle | hips and chest join the twist, arms out for balance |
| 1 | BarDoor_Enter | the "flop back onto the wall" was invisible | forward dip anticipation + head whip on impact |
| 1 | BarDoor_Loop | back scratch invisible (1.8 cm) | 3.2 cm rub, hip roll, blissful chin-up |
| 1 | BenchSit_Enter | glance back at the bench too small | bigger glance with chest and hips |
| 1 | BenchSit_Loop | **yawn arched the torso ~45° through the backrest** | arch reduced, the stretch goes into the arms; backrest check added to the validator |
| 1 | BenchSit_Exit | rise popped between 0.9 and 1.0 s | in-between key, spread rise |
| 1 | BeachLie_Exit | forward rock folded ~70° (face-plant) | squat lean |
| 1 | BeachLie_Loop | foot bob to music invisible | bigger bob + head sway |
| 1 | PhoneTalk ×3, SmokeCorner_Enter/Loop, BarDoor_Exit, BeachLie_Enter, Flee_Panic_Run | read as intended | – |
| 2 | BusWait | left-hand brow shade reads as peering under the hand | – |
| 2 | BenchSit_Loop | yawn now a clean overhead stretch against the backrest | – |
| 2 | KioskBuy | review wall prop blocked the ¾ camera | removed (counter only) |
| 3 | all | full-rate check: no pops, seams invisible, enter → loop → exit chains continuous | – |
| validation | all | heel lifts slid the toe pad ~1.2 cm (toes counter-rotated about a joint 4.2 cm above the floor); shoe crease sank on tiptoes; planted palms dug the fingers 9–15 cm into the towel; hood 12 cm through the bench backrest; bench feet 2 cm apart without a step; beach foot scoot 6 cm; BarDoor foot 4.6 cm into the wall; heel pivot 1 mm above the real heel | heel lifts now pivot at the toe joint (toe pad exactly planted); `ik*.flat` palm-flat contacts; backrest 0.70 m; feet kept; scoot removed (ankle re-solved); foot flush; heel pivot at the real sole |

Pass-3 notes on the look: the sausage reads best from the front/¾; side views of the standing loops are calm by design
(crowd idles must not distract), the comic beats are the snaps (peek, "CHTO?!", flop, plop, swat, flick, thigh slap).
The run is a fast churn (10 frames per two steps) with a short flight; arms shake one beat per step above the head.

## 6. Known limits / next steps

1. **Not seen in Unity yet.** Import with the settings in section 3 and check at gameplay distance (lead).
2. Rendered with the flat-colour JSON mesh proxy (no textures/face); final previews with the LFS A v04 source are for a
   local session: `python build_crowd.py --clip X --review ...` picks the real `.blend` automatically when it is present.
3. No face animation in the FBX (by design); eyes/blinks/expressions belong to the face script (`GreyboxFace.Set`).
4. Props are implied: a cigarette/phone mesh can be parented to `mixamorig:RightHand`.
5. `Flee_Panic_Run` is authored at 4.5 m/s; at much lower playback multipliers the flight phase gets floaty.
6. Sub-frame contact values listed in section 2 (≤ 1.6 mm sole, 3.1 mm heel-skin creep in one squat) — fix by denser
   keys only if they ever show in game.
7. B variant: the rig is identical (verified by the earlier packages); B's outfit was not used for contact checks.
8. Next revisions must be new files (`*_v02`); never overwrite v01.

## Кратко по-русски

Набор «толпы» для сосисочных NPC (21 клип, 30 fps, всё на месте): сесть на скамейку / сидеть с ёрзаньем (зевок с
потягиванием, дёргает коленкой, чешет пузо, хлопает по коленям) / встать; лечь на полотенце (руки за голову, нога на
ноге, качает ступнёй под музыку, отмахивается от мухи) / встать и отряхнуть зад; очередь (выглядывает из-за спин, тяжко
вздыхает, рука в бок, стучит носком, зыркает назад); курилка (прикурить, затяжка-выдох в сторону, стряхнуть пепел,
щелчком выбросить бычок и растоптать); разговор по телефону («ЧТО?!», спорит, закатывает глаза, ржёт); остановка
(козырёк ладонью, на цыпочках, качается с пятки на носок); бар (плюхается спиной на стену, нога на стену, чешет спину
о стену); киоск (тычет «вот это», роется в кармане, платит, радостно подпрыгивает); болтовня вдвоём (Chat_Loop +
зеркальный Chat_Loop_Mirror со сдвигом на полцикла: один говорит — другой слушает и ржёт до хлопка по ляжке);
бег в панике с руками над головой (4,5 м/с). Все переходы стыкуются точно (ошибка 0), петли бесшовные, стопы не
скользят, проверка пройдена (`validation_crowd_v01.json`, 21/21). В репозитории только скрипты и JSON: `.blend/.fbx`
собираются командой `python build_crowd.py --clip all --final`. Размещение пропов для Unity — в разделе 3, в Unity
ещё не проверялось.
