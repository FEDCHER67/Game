# Sausage Buddy patient — operating-table animations (Operation_v01)

Eight clips for the operations stage-1 patient on the gurney TABLE-ASTRA-001 v02 (`OperatingTableAstra_v02.prefab`). Original local FK and analytical IK animation, authored in Blender 5.2.1 LTS by the animation agent (CL-ANIM) on 2026-10-15/16. No external motion take, paid generation or credits were used. That agent was stopped right after the Unity import; this README was written afterwards by CL-FINAL from the saved authoring files, `validation_op_v01.json` and the Unity import, without re-authoring anything.

Rig `Buddy_Rig_Mixamo65`, root `mixamorig:Hips`, 65 bones, bound to `Patient_v01/SAUSAGE_BUDDY_PATIENT_v01` (names, order, hierarchy and bind matrices match). 1 Blender unit = 1 metre, +Z up, 30 fps, keys on half frames (60 Hz) with linear interpolation. Each `.blend` keeps the PATIENT Body/Face/Shorts meshes for review; each FBX holds one take, one armature, zero meshes. Face blend shapes are not animated: gameplay drives `Blink`, `Worried`, `Surprised`, `Happy` itself.

## Frames and placement

- The rig object sits at **PatientRest** = table `T(0, 0, 0.66) · Rz(180°)`: head toward armature +Y, face +Z, the patient's **left = armature +X**. The pad top is at armature z ≈ 0.
- Unity: PatientRest is the table child at `(0, 0.66, 0)`, Euler `(0, 180, 0)`. A point in armature space maps to Unity root-local `(-x, z, -y)`, and to table-local `(x, z, y)`.
- All table clips start from (Awake, Struggle, Panic, ShockDeath) or loop on (Asleep, Dead) poses derived from `Patient_TableRest` (ArtSource/Props/TABLE-ASTRA-001/v02). The hips stay at table height 0.771 m; nothing is root motion.
- **EscapeFall** moves the hips 1.5 m off the table relative to PatientRest (end hips table-local `(1.5, 0.119, -0.36)` in Unity, i.e. over the patient's left side). **KnockedOut** is stored relative to its own floor root, placed under those end hips: PatientRest-local root offset `(-1.5, -0.66, 0.36)` (Unity). EscapeFall's last pose equals KnockedOut's first pose across that offset (error 2.4e-7).

## Clips

| Clip | Frames | Seconds | Loop | What it shows |
| --- | --- | ---: | --- | --- |
| Op_Lie_Awake_v01 | 1–121 | 4.0 | Yes | Awake on the table, nervous: looks at the doctor and away, nervous fists and finger drumming, a gulp, a short head lift; breathing (3 breaths per loop). Starts and ends exactly in TABLE_REST. |
| Op_Lie_Asleep_v01 | 1–151 | 5.0 | Yes | Anaesthetised: head lolled toward the table camera, slow deep breathing, one hand twitch and one foot twitch per loop. |
| Op_Struggle_v01 | 1–76 | 2.5 | Yes | Strapped and fighting it: head lifts and looks at the belly, chest heaves, alternating arm and leg yanks against closed straps. Starts/ends in TABLE_REST. |
| Op_Panic_v01 | 1–61 | 2.0 | Yes | Waking up mid-operation: a stronger, faster struggle with a horrified stare at his belly, whipping head, alternating yanks. Starts/ends in TABLE_REST. |
| Op_ShockDeath_v01 | 1–61 | 2.0 | No | Rigid electrified arch with tremor (0.04–0.6 s), bounce, two twitches, then rolls limp into the Dead pose (from 1.8 s, exactly Dead's pose). |
| Op_Dead_v01 | 1–61 | 2.0 | Yes | Static limp pose on the table: head rolled toward the camera, arms slack, feet flopped out. |
| Op_EscapeFall_v01 | 1–91 | 3.0 | No | Unrestrained escape: realises the straps are open, panic sit-up with knees tucked, spins on his butt toward his left edge while scooting toward the foot end, swings his legs off between the open torso and leg straps, stands, stumbles and splats prone on the floor (impact ≈ 2.0 s). |
| Op_KnockedOut_v01 | 1–121 | 4.0 | Yes | Prone splat on the floor, face turned toward the table's foot end, slow breathing (2 per loop), one leg twitch. |

Contact sheets (ten labelled times, two views) and 30 fps playback MP4s are in `Previews/<clip>/`; the 480×480 Cycles stills and the Eevee frame sequences are next to them. Table clips use the `side` and `three_quarter` views; EscapeFall and KnockedOut use `left` and `left_three_quarter`.

## Validation

`validation_op_v01.json` (by `validate_op_v01.py`) opens every saved `.blend`, samples at 120 Hz and skins Body/Face/Shorts with Blender's own Armature modifier against the TABLE-ASTRA-001 v02 geometry (pad, frame, rails, handle, wheels, casters, braces, strap anchors, the five straps closed or open as each clip assumes, and the instrument stand at the old TrayAnchor), then reimports each FBX. **All 8 clips pass every check (20–23 per clip).**

| Clip | Checks | Max key step (°) | Min pad gap (mm) | Closed-strap penetration (mm) | Notes |
| --- | --- | ---: | ---: | --- | --- |
| Lie_Awake | 22/22 | 18.5 | 0.51 | 0 | forearms move ≤ 2.1 cm at the strap points |
| Lie_Asleep | 21/21 | 8.7 | 0.83 | 0 | |
| Struggle | 23/23 | 15.6 | 0.55 | 0 (leg R grazes, 0.0) | strap points move ≤ 3.1 cm |
| Panic | 23/23 | 22.6 | 0.46 | leg L 3.0, leg R 4.7, torso 1.7 | under the 8 mm soft-strap tolerance; strap points ≤ 4.0 cm |
| ShockDeath | 20/20 | 17.9 | 0.41 | torso 1.7 | ends exactly on Dead (error 0) |
| Dead | 21/21 | 0.0 | 0.97 | 0 | |
| EscapeFall | 20/20 | 22.4 | 0.55 | – (straps open) | lowest vertex 0.0 m (floor) |
| KnockedOut | 21/21 | 8.7 | – (on the floor) | – | lowest vertex 0.001 m |

Thresholds: key step < 25° per half frame, pad gap ≥ 0, strap penetration ≤ 8 mm, strap-point drift ≤ 4 cm, FBX bind error ≤ 1e-4, FBX animated matrix error ≤ 5e-3 (worst 2.3e-3 on Awake: FBX stores Euler float32 and the clavicles sit at the Euler gimbal in TABLE_REST, ≤ 3 mm at the hands), seams exact. Nonfinite values, reflected bones and quaternion sign flips are zero everywhere.

## Unity import (checked 2026-10-16)

Files: `Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Animations/Op_*_v01.fbx`. All eight are **Generic, Copy From Other Avatar = `SAUSAGE_BUDDY_A_v04Avatar`** (from `SAUSAGE_BUDDY_A_v04.fbx`), **Anim. Compression Off**, Preserve Hierarchy on, Import Animation on, one clip each (`Op_Lie_Awake`, …), 660 curve bindings, lengths 4.0/5.0/2.5/2.0/2.0/2.0/3.0/4.0 s. Loop Time is **on** for Awake, Asleep, Struggle, Panic, Dead and KnockedOut and **off** for ShockDeath and EscapeFall. Root transform locks are off; the patient Animator has Apply Root Motion off, so the authored Hips curves place the body.

In Unity the source EscapeFall dips at most 1.9 mm below the floor between keys (Unity's Euler-curve interpolation; 0.0 in Blender).

### v03 mirrored escape (Unity only)

Since v03 the instrument stand and the opened torso strap lie on the patient's **left** (table +X, the far side from the table camera), exactly where Op_EscapeFall_v01 leaves the table: a flat-opened torso strap meets the stepping legs (273 vertex contacts from 1.43 s). The escape therefore uses left/right mirrored copies, generated in Unity by `Assets/OnlyVolunteers/Operation/Stage1/Editor/OperationClipMirrorV03.cs` (menu *OnlyVolunteers → Operation → Mirror patient escape clips (v03)*; never overwrites):

- `Animations/Op_EscapeFall_Mirror_v01.anim` (3.0 s, no loop) and `Animations/Op_KnockedOut_Mirror_v01.anim` (4.0 s, loop), 60 Hz linear keys.
- Method: sample at 60 Hz, reflect every bone across the model's YZ plane and swap Left/Right bones, with a per-bone rest correction (the bind pose is symmetric to 0.001 mm).
- Checked: bone positions equal the reflected source within 2.7 mm (fast frames, resampling); mirrored EscapeFall end = mirrored KnockedOut start across the root offset `(+1.5, -0.66, 0.36)` with 0.000 mm / 0.000°; KnockedOut loop seam 0.000 mm; zero contacts with the opened straps, stand, frame, handle, wheels and anchors over the whole escape.

The source FBX/blend files are unchanged; the original (left-side) clips remain imported and can be swapped back in the controller if the stand ever returns to the camera side.

## Controller contract

`Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Patient_Operation.controller`, int `OpState` + trigger `ShockDeath`:

| OpState | State | Clip |
| ---: | --- | --- |
| 0 | TableAwake | Op_Lie_Awake |
| 1 | TableAsleep | Op_Lie_Asleep |
| 2 | Struggle | Op_Struggle |
| 3 | Panic | Op_Panic |
| 4 | Dead | Op_Dead |
| 5 | EscapeFall | Op_EscapeFall_Mirror_v01 |
| 6 | KnockedOut (default) | Op_KnockedOut_Mirror_v01 |
| trigger | ShockDeath → Dead | Op_ShockDeath, then Op_Dead at its end (exit time 1, no blend: the poses are identical) |

Crossfades are 0.25 s between states, 0.1 s into EscapeFall and into ShockDeath, and 0 s from EscapeFall to KnockedOut (the gameplay snaps that switch in the same frame as the root jump).

## Reproduction

From the repository root, Blender 5.2 headless:
- author and save one clip: `blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Operation_v01/build_op_v01.py -- --clip Awake --final` (clips: Awake, Asleep, Struggle, Panic, ShockDeath, Dead, EscapeFall, KnockedOut; refuses to overwrite);
- review renders of the saved file: `... build_op_v01.py -- --clip Awake --from-saved --out <dir> --seq`;
- validate: `blender -b --factory-startup --python .../validate_op_v01.py -- --clips Awake,Asleep,Struggle,Panic,ShockDeath,Dead,EscapeFall,KnockedOut` (refuses to overwrite its report);
- contact sheets: `python make_sheets_op.py <stills_dir> <out.png> --title T --views side,three_quarter`.

`op_core.py` holds the frames, table/stand staging and FK/IK helpers (it imports `../Idle_Knock_v03/acting_core.py` read-only); `op_clips.py` holds the per-clip channels, beats and contracts. Each clip's `*_authoring.json` records its frame range, sampling, rig placement and contact-solve statistics.
