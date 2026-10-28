# Sausage Buddy: Forest set (Forest_v01), batch 1

Original procedural keyframe animation for the forest junkie NPC (`FOREST_OD_JUNKIE`). It uses the rig
`Buddy_Rig_Mixamo65` (65 bones), which is identical to A v04: same order, and the rest matrices differ by 0.
Built on the Crowd_v01 pipeline. `crowd_core`, `acting_core`, `build_crowd` and `validate_crowd` are imported
read-only; nothing outside this folder was changed. The previews are rendered on the junkie meshes.

| Clip | Frames | s | Loop | Start | End | Events (s) |
| --- | --- | --- | --- | --- | --- | --- |
| `Junkie_Walk` | 1-73 | 2.4 | yes | junkie_walk | junkie_walk | FootL 0.0, FootR 0.6, Stumble 1.2, Catch 1.62 |
| `Inject` | 1-241 | 8.0 | - | idle | high_lie | SyringeShow 1.16, Inject 3.48, Sit 5.66, SyringeDrop 7.18 |
| `High_Lie_Loop` | 1-241 | 8.0 | yes | high_lie | high_lie | - |

- **Junkie_Walk**: in place on a treadmill, authored at **0.8 m/s** (playback speed = ground speed / 0.8). It is a
  soft-kneed shuffle with the toes out; the feet skim 4-7 mm above the floor in the swing. The hunched torso sways
  behind the pelvis on a spring, and the head lolls with lag. The arms are pendulums ("ropes").
  - 0-1.2 s: he nods off while walking (head sinks, eyes close).
  - 1.2 s: the left foot hooks across in front of the right.
  - He snaps awake (Surprised), lurches forward-right and does a backward arm windmill.
  - 1.62 s: the right foot flings out wide and catches him; his knees buckle.
  - He gives a "huh?" look down at his feet and shuffles on.
- **Inject**: He sways, then digs in the hoodie pocket and pulls out the syringe. He holds it up in front of his
  eyes and squints. The left index finger flicks it twice. He chops the palm-up left forearm twice, then aims. The
  needle goes in from his right, across the forearm, and the thumb pushes. He freezes. Then he pulls it out, the
  head tips back in bliss and he wobbles. His knees buckle in two stages, and he drops into a squat. He plops onto
  his butt with the legs flying up, then they slap down and he bounces. He sways seated, then slowly tips back. The
  arms fly out and the hand opens, so the syringe flies off and lands on the floor. Thud, head bonk, starfish.
  Cartoon, no blood: the syringe's blood fill mesh is hidden.
- **High_Lie_Loop**: starfish on the back, palms up on the floor. He breathes with the belly and rolls his head.
  He does two dreaming-dog kicks with the right leg, with a body jolt. Then both arms paddle in the air
  (breaststroke). He gives a slow goofy wave at the sky and the left foot twitches. Last, a lazy swat at a fly
  that misses, and a giggle.

Contracts: `idle` = A v04 Idle frame 1; `junkie_walk` = walk frame 1; `high_lie` = the lying base. Lying is
behind the root, head toward +Y, hips 0.29 m high and 0.40 m behind; hands are about 0.6 m to each side.

**Chaining to a get-up.** The closest existing clip is `GetUp_Idle_v01/GetUp_FromBack_v02`. It is also supine with
the head toward +Y, and its frame-1 hips are 0.307 m high, against 0.29 m here. The differences are the arms
(starfish here, by the sides there), the legs (spread, feet flopped out), and the head (turned 16 degrees). A
cross-fade of about 0.5 s should read. A `High_Lie_Exit` (batch 2) would fold the arms and legs in first.
`validate_forest.py` reports the exact numbers in `high_lie_vs_getup_from_back_v02`; it was not run, see below.

## Syringe (existing prop, attached in previews only)

- Prop: `SYRINGE-ASTRA-001.fbx`, on `mixamorig:RightHand`. The hand frame is the Blender pose-bone frame: +Y toward
  the fingers, +X thumb side, +Z palm.
- Grip ("dart" grip, needle past the fingertips): position (0.012, 0.215, 0.045) m and rotation (w,x,y,z)
  (0.7660, 0.6428, 0, 0), i.e. +80 degrees about hand X.
- Unity guess: localPosition (-0.012, 0.215, 0.045). Set it once with a gizmo, because the prop FBX has its own axis
  conversion.
- Timing: visible from `SyringeShow`. The plunger (`CTRL_PlungerTravel_Z`) goes 0 -> -0.048 over 3.48-3.86 s. At
  `SyringeDrop` it becomes a world prop on the floor next to the right hand.
- All of this is in `forest_manifest_v01.json` and `Inject_v01_authoring.json`, with face hints (Blink, Worried,
  Surprised, Happy) for `GreyboxFace.Set`.

## Files and commands

`clips_forest.py` holds the clips, the contracts and `ForestRig`. `ForestRig` adds hand orientation for the needle,
a late left-arm solve, and lying feet that sit on the floor. The other files:

- `build_forest.py`: final build, manifest, and review renders on the junkie mesh.
- `validate_forest.py`: the 18 Crowd checks plus the junkie-floor and get-up comparison.
- `make_previews_forest.py`: grid, mp4, gif and sheet.

```
blender -b --factory-startup --python build_forest.py -- --clip all --final
blender -b --factory-startup --python build_forest.py -- --clip all --manifest <abs>\forest_manifest_v01.json
blender -b --factory-startup --python build_forest.py -- --clip all --review <abs dir> --saved <this folder> --every 2 --seq --views three_quarter --res 480
python make_previews_forest.py gif <dir>\Inject\three_quarter <out>.gif --fps 15 --src-fps 15   (--loop-clip for loops)
blender -b --factory-startup --python validate_forest.py -- --out <abs>\validation_forest_v01.json
```

## Status (honest)

The owner asked for a light check only, so the full validation report and the MP4s were **not** produced. What was
checked:

- **Build**: all start/end contract gaps are 5e-4, which is float noise (the seams are keyed exactly).
- **Key steps** (limit 25 degrees):
  - Junkie_Walk: max 23.6 degrees.
  - High_Lie_Loop: max 20.8 degrees.
  - Inject: max **28.1 degrees** at 7.27 s (LeftForeArm, the arms slapping onto the floor at the thud). That is
    over the Crowd limit. Fix in a v02 if it shows.
- **Walk on a scratch build**: validated earlier with the 18 checks. Only planted slide failed (1.8 mm at
  toe-off), and it was fixed afterwards. The delivered walk was not re-validated.
- **Visual**: review renders at every 3rd frame, plus the GIF frames. No visible foot sliding, floor sinking, IK
  flips or popping. The lying body is on the floor, with the hands about 1 cm above it.

Rendered on the junkie meshes; the floor contact was solved on the A v04 meshes, whose hood and shoes differ
slightly. Not seen in Unity.

## v02 (owner review of v01: "too complex, too Disney") — current

`clips_forest_v02.py` and `build_forest_v02.py` rebuild the set in the style of Flee_Run, JumpOut and Cop_Trip:

- a few big key poses with 2-4 frame snaps and clear holds;
- one arm action at a time, with no layered micro-acting;
- **face snaps** keyed as 0 -> 1 in 1-2 frames.

The v01 files are kept as they were.

| Clip | Frames | s | Loop | Start / end | Beats |
| --- | --- | --- | --- | --- | --- |
| `Junkie_Walk_v02` | 1-37 | 1.2 | yes | junkie_walk_v02 | 2 steps at 0.6 m/s. Bent knees, big side-to-side rock, arms hanging, head lolling. The eyes droop shut and the head sinks, then at 0.83 s (event SnapAwake) he SNAPS awake: Surprised, head up, shoulders jolt. |
| `Inject_v02` | 1-106 | 3.5 | - | idle / high_lie_v02 | 0.13 syringe out (Happy), 1.03 left arm out, 1.33 JAB (Surprised snap, body jolt, event Inject), 1.83 bliss (Happy + Blink 0.5), 2.47 falls straight back stiff as a plank, 2.93 THUD (SyringeDrop), arms and feet flop out |
| `High_Lie_Loop_v02` | 1-106 | 3.5 | yes | high_lie_v02 | lies still with a half-asleep grin and dozes off; 1.43 right leg twitch (eyes snap half open); 2.4 left arm floats up, 2.97 flops down |

- **high_lie_v02**: the plank fall lands further back than v01's starfish. The hips are ~0.84 m behind the root and
  the head top ~1.8 m; the feet stay at the root. The hands lie palm-up on the floor at shoulder level.
- **Face track**: listed per clip in `forest_manifest_v02.json` as `face_track` = [time s, shape, weight] at each
  key, linear in between, for GreyboxFace. It is also keyed in the .blend as `<Clip>_Face` on the Face shape keys,
  after the FBX export, so the FBX stays one armature take.
- **Syringe**: same grip as v01.

**Checks (light, per owner):** all three build, and every seam lands exactly. One look at the GIF frames shows no
foot slide, no sinking and no flips. One pop is fixed: the left arm on the floor jumped at 1.7 s in the lie loop.
The big key steps are the intended snaps:

- Inject: 35 degrees at the bliss arm drop.
- High_Lie_Loop: 41 degrees at the 3-frame arm flop.

No validation report and no MP4s. GIFs: `C:\Users\chern_0eqkb03\VolunteersBuilds\forest_anims_v02\`.
