# Sausage Buddy — GetUp v03 (FromBack, FromBelly)

Two comic, groggy get-ups for the Sausage Buddy NPC (`Buddy_Rig_Mixamo65`, 65 bones). Both start from a held
lying pose that the ragdoll blends into, and both end exactly on Idle frame 1. They replace GPT's v02 get-ups,
which Fedya rejected. The planned beats are in `HANDOFF.md` and `getup_choreo_v03.py`. This README covers what was
built, the numbers, how to rebuild everything, and what the review passes found.

> **Binaries are not in git.** This cloud pass could not push Git LFS objects, so the `.blend`, `.fbx`, MP4 and
> PNG deliverables are **regenerated locally** from the scripts here (deterministic, see *Build*). The committed
> `validation_v03.json`, `*_authoring.json` and `getup_manifest_v03.json` come from exactly those builds.

## Clips

| | GetUp_FromBack_v03 | GetUp_FromBelly_v03 |
| --- | --- | --- |
| Frames / fps / length | 1–85 / 30 / 2.80 s | 1–85 / 30 / 2.80 s |
| Start pose | supine, head → local **+Y**, butt + hood on the floor, head resting on the hood, palms down | prone, head → local **−Y**, right cheek on the floor, push-up hands beside the chest |
| Start hold (identical frames) | 5 frames (1–6) | 6 frames (1–7) |
| **hipsStart** (root space) | **(0, 0, 0.1429) m** | **(0, 0, 0.2015) m** |
| **Stable** (stays true to the end) | frame **67.25** → fraction **0.80** (2.24 s) | frame **61.0** → fraction **0.73** (2.03 s) |
| End | Idle frame 1, matrix error 4.4e-7 | Idle frame 1, matrix error 4.4e-7 |
| Hips net horizontal drift | 0 (max excursion 0.24 m, stepped back) | 0 (max excursion 0.30 m, all fours over the knees) |
| Standing soles (after Stable) | penetration 0.14 mm, support error 2.0 mm | penetration 0.23 mm, support error 2.3 mm |
| Whole skinned mesh under the floor (all frames, 120 Hz) | 2.7 mm max (hands, a quarter-frame) | 0.58 mm max |
| Max local rotation per half frame | 23.7° (RightArm, windmill) | 23.6° (RightArm, windmill) |
| FBX reimport world-matrix error | 1.0e-4 | 1.9e-5 |
| Body above 1.2 m (van cargo height) from | f66.25 | f60.75 |

Frame numbers in this README are 0-based clip frames (Blender frame = clip frame + 1), as in the beat sheets.
Neither clip uses root motion (`applyRootMotion = false`). Both are in place and keep the bone list identical.
The 1.2 m van limit belongs to the cargo clips. The get-ups end standing at 1.75 m, so the row only shows how
long the lying/sitting part stays below the cargo height.

### Performances (what plays)

**FromBack (2.8 s).**
- **f0–5:** held supine start.
- **f5–14:** groggy peek. The head peels off the hood to look at the feet ("huh?") and the left knee twitches.
- **f14–17:** anticipation. He drops back a little, the hands leave the floor and the shoulders load.
- **f17–24:** sit-up snap. The arms are thrown at the feet and the heels pop up as a counterweight and slap down
  at f22. The spine over-curls, so he folds face-first into his knees for a beat. The head lags, then whips.
- **f24–30:** settles into a slump with the hands landing on the thighs.
- **f29–48:** dizzy circle of the neck, head and upper spine.
- **f42–52:** "brr" head shake (±36°, 5 Hz, decaying) with a shoulder shrug.
- **f47–56:** gathers: the feet slide in, the soles flatten, the hands plant behind the hips and he leans back.
- **f56–65:** pushes off and rocks forward into a deep squat, swinging the arms forward.
- **f65–69:** stands up too fast, head last.
- **f69–77:** head-rush stagger backward. The arms windmill and the right foot steps back to its Idle spot.
- **f76–84:** the left foot steps back, a small head wobble, and he settles into Idle.

**FromBelly (2.8 s).**
- **f0–6:** held prone start.
- **f6–16:** noodle-arm push-up. The chest rises on trembling arms (a 9 Hz bob drives the IK elbows) while the
  head hangs.
- **f16–19:** the arms buckle and the chest flops.
- **f19–30:** a determined second push, then the hips shift back over the knees to all fours.
- **f29–39:** one slow head circle.
- **f37–47:** whole-body wet-dog shake. The head leads and the spine and pelvis follow with lag.
- **f46–57:** kneels up and swings the right foot forward to its Idle spot (half kneel). Both hands land on the
  right knee.
- **f57–65:** pushes up on the knee to stand while the left foot swings in from behind, head last.
- **f65–78:** forward teeter onto the toes with backward-windmilling arms, then rocks back onto the heels, all in
  place.
- **f78–84:** settles into Idle.

## Fixes requested in the handoff

- **Floating head in the belly start (2.8 cm).** Neck bend 10° → 14°. The cheek now rests on the floor (head
  0.0 mm, chest/hood 0.8 mm). hipsStart changed from 0.2007 to 0.2015 m.
- **Planted-hand clearance.** The old fixed `h = 0.008` was measured on rigid hand points. That missed the
  mixed-weight wrist/cuff vertices (7 mm under the floor in the supine start) and made the prone hands float
  8 mm. New `plantL/plantR` channels in `getup_lib_v03.Clip._plant_hands()` correct the IK target height until
  the lowest **deformed** hand vertex is exactly `HAND_CLEAR = 1 mm` above the floor. A partial plant weight
  blends the correction, so hands arrive and leave smoothly. Both start poses now have both palms at 1.0 mm.
  Releases lift the hand target before IK hands over to FK, so the arm can't swing through the floor.

## Framework changes (getup_lib_v03.py)

- `plantL/plantR` + `HAND_CLEAR`: mesh-measured planted hands (above).
- Soft IK reach for the arms (`ARM_SOFT = 0.08`). Near full extension the effective distance approaches the
  reach limit exponentially. This removed elbow snaps of 30–50° per half frame when hands reach for a knee or
  release. Legs are unchanged, so Idle is still rebuilt exactly.
- `build_getups_v03.py` exposes `build()`. It also gains `--outdir` (final exports anywhere, e.g. a scratch
  folder) and `--engine workbench|eevee` for `--review` contact sheets.
- `getup_choreo_v03.py`: `Keys` pose-to-pose helper (per-channel keys, so overlap is keyed explicitly), `E()`
  eased keys, the two performances, procedural layers (dizzy circles, brr shake, tremor, wet-dog shake,
  windmills), and `READY = True`.

## Review passes (rendered and looked at; Workbench, side + three-quarter, checker floor)

Each pass: contact sheets of the frames from both cameras, an onion skin, plus numeric motion checks (per-frame
speeds of hips/head/hands/feet, per-bone rotation per half frame, per-region floor heights at every half frame).

1. **Blocking, every 2nd frame.**
   - *FromBack:* hands went 6 cm through the floor in the squat (the arm swing passed straight down).
     `handOnKnee` was interpolating from frame 0, so it dragged the planted hands toward the knees; the
     correction then pushed them 1 m down. The head lift raised half the torso.
   - *FromBelly:* the push-up barely lifted the chest. On all fours the head was buried in the floor, which
     propped the hips up 6 cm and hid the dizzy circle. At f50 the torso swung upright, then folded back over
     the knee.
   - *Fixed:* arm swing re-timed through a wider path; `handOnKnee` keyed only around the thigh landing; head lift
     reduced to a peek; deeper push (pelvis 64°, arched spine); head carried level on all fours; kneel-up goes
     straight into the lean over the knee.
2. **Motion, every frame.**
   - Rotation spikes above 25° per half frame at the IK↔FK hand-offs (31°) and on the knee push (41–52°, IK
     clamp snaps).
   - The authored hip height disagreed with the knee-grounded solve: a 14 cm hip jump in one frame at f59→60.
   - The left knee snapped straight on touchdown (the foot finished flattening at contact).
   - The head shake was too subtle.
   - *Fixed:* soft IK on the arms; longer IK↔FK blends; FK hands matched to the knee contact orientation; hips
     re-pathed through the solved height; foot flattened before contact; bigger shake/circle amplitudes. All
     steps now ≤ 23.7°.
3. **Motion, every frame, after the fixes.**
   - *FromBelly:* the shake reads clearly from the three-quarter view, the kneel-up flows into the knee push, and
     the teeter/rock-back reads.
   - *Validator:* a 1.9 mm sole dip between half-frame keys during the snap rise (FromBack f66.75–68.25), and the
     belly start hold leaked one frame. During the push the torso-only floor solve dipped the thighs, and the
     smoothed lift bled back into the hold.
   - *Fixed:* a 2 mm contact margin for those three frames; the belly is grounded on torso and legs while lying.
     Both clips pass every check.

Still subjective, to judge in the real look and in Unity:
- the comic fold into the knees at f22–25 (FromBack) is deliberate but strong;
- the slumped sit (f29–47) moves only the head, neck and spine;
- the hands on the knees/thighs are targeted at the knee joint plus an offset, not at the trouser surface, so
  check the contact in the textured EEVEE render;
- Unity playtests with the real ragdoll blend are still needed.

These renders use the flat-colour proxy mesh (no textures). The final previews should be rendered from the LFS
source with `--engine eevee`.

## Build (deterministic)

Blender 5.2 (or `python -m pip install bpy` → bpy 5.2.2 on Python 3.13), run from this folder.

```
# With the Git LFS source (SAUSAGE_BUDDY_A_v04.blend present):
blender -b --factory-startup --python build_getups_v03.py -- --clip all --final            # .blend/.fbx/_authoring.json here
blender -b --factory-startup --python validate_getups_v03.py --                            # -> validation_v03.json
blender -b --factory-startup --python make_manifest_v03.py                                 # -> getup_manifest_v03.json
blender -b --factory-startup --python render_previews_v03.py -- --clip all --engine eevee   # Previews/<clip>_v03/: MP4 side + 3/4, sheets, onion skins

# Without Git LFS (cloud): rebuild the rig + skinned proxy from JSON first and point the scripts at it
blender -b --factory-startup --python rebuild_rig_from_json_v03.py -- --out <scratch>/buddy_rebuilt.blend --with-proxy --idle-action
export GETUP_SOURCE_BLEND=<scratch>/buddy_rebuilt.blend
blender -b --factory-startup --python build_getups_v03.py -- --clip all --final --outdir <scratch>/final
blender -b --factory-startup --python validate_getups_v03.py -- --dir <scratch>/final --out <scratch>/validation_v03.json
blender -b --factory-startup --python render_previews_v03.py -- --clip all --engine workbench --out <scratch>/prev

# Quick review sheets while authoring (every frame, small)
blender -b --factory-startup --python build_getups_v03.py -- --clip back --review <scratch>/rev --every 1 --res 200 --cols 17
```

All writers refuse to overwrite existing numbered files. The committed JSON was produced by the cloud (no-LFS)
route. The rebuilt rig matches the A v04 source to 5e-8 (handoff measurement), so a local LFS build gives the same
animation. The FBX bake used the Walk_v02/GPT export call: armature only, bake step 0.5, simplify 0, −Z forward,
Y up, no leaf bones.

## Files

| File | Role |
| --- | --- |
| `getup_choreo_v03.py` | Start poses (with the fixes), beat sheets, the two performances, procedural layers. |
| `getup_lib_v03.py` | Framework: FK/IK, curves, floor solver, mesh-measured hand plant, soft arm IK, keying. |
| `build_getups_v03.py` | Build / metrics / `--review` / guarded `--final` export (`--outdir`). |
| `render_previews_v03.py` | MP4s (side + three-quarter), labelled contact sheets, onion skins; EEVEE or Workbench. |
| `validate_getups_v03.py` | 120 Hz validation of the saved .blend + FBX reimport → `validation_v03.json`. |
| `make_manifest_v03.py` | Clip manifest → `getup_manifest_v03.json` (hipsStart, Stable, beats, ragdoll notes). |
| `validation_v03.json`, `GetUp_From*_v03_authoring.json`, `getup_manifest_v03.json` | Committed reports from this build. |
| `rebuild_rig_from_json_v03.py`, `rig_Buddy_Mixamo65.json`, `mesh_proxy_Buddy_A_v04.json`, `export_rig_json_v03.py` | No-LFS rig route (unchanged). |

The bone list was checked against `rig_Buddy_Mixamo65.json`: 65 bones with identical names, order, parents and
rest pose (A v04 = GPT v02 FBX = Walk_v02). The v02 FBX itself is an LFS pointer in the cloud. A local run of the
validator also compares against it automatically (`--ref-fbx`).

---

## Кратко по-русски

Два новых подъёма Сосиски — **GetUp_FromBack_v03** и **GetUp_FromBelly_v03**, по 2,8 с (30 fps, кадры 1–85). Оба
начинаются с удерживаемой лёжа позы для бленда из рэгдолла и заканчиваются ровно на Idle frame 1.

- **Со спины:** очухивается, тупо смотрит на ноги, рывком садится и складывается лицом в колени. Потом
  кружится голова и он трясёт ей «брр». Дальше упирается руками сзади, перекатывается в присед, встаёт слишком
  резко, от прилива крови отшатывается назад с «мельницей» руками и шагами возвращается в Idle.
- **С живота:** отжимается на руках-макаронинах, которые подламываются. Со второй попытки встаёт на
  четвереньки, кружит головой и отряхивается всем телом, как мокрая собака. Потом полуприсед с руками на правом
  колене, встаёт, качается вперёд на носках с «мельницей», откатывается на пятки и замирает в Idle.

**Цифры:**

| | Со спины | С живота |
| --- | --- | --- |
| hipsStart | (0, 0, 0,1429) м | (0, 0, 0,2015) м |
| Stable | 0,80 (кадр 67,25) | 0,73 (кадр 61) |

Обе анимации на месте (смещение бёдер 0), кости те же 65. Валидация пройдена (`validation_v03.json`).

**Исправлено:** голова в старте с живота больше не висит на 2,8 см, щека лежит на полу. Ладони теперь ставятся
по реальному деформированному мешу — ровно 1 мм над полом, без провалов запястий.

Бинарники (.blend/.fbx/MP4) в git не попали (LFS заблокирован в облаке). Они детерминированно собираются
командами из раздела *Build*. Нужны живой просмотр в EEVEE и проверка в Unity.
