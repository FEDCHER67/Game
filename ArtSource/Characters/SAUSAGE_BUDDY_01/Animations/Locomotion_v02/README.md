# Sausage Buddy Walk: Locomotion_v02 (Walk_v03 -> Walk_v04)

`Walk_v04` is iteration 2 of the re-authored walk (see `HANDOFF.md` for the full design and contracts).
It fixes the four open items of v03: marching knee lift, crouched stance, indistinct up pose and the
1.3 mm toe skim. Timing is unchanged: 20 frames at 30 fps (frame 21 == frame 1), 1.5 m/s, 1.0 m stride,
in place, left heel strike f1, right f11. Bone list, FBX settings and Unity import settings are unchanged.

Authored and reviewed in a cloud sandbox without Git LFS, so **only text is committed**: the `.blend`, `.fbx`
and previews are regenerated locally by the scripts below (deterministic).

## What changed (v03 -> v04)

All edits are in `walk_v04_motion.py` (copy of `walk_v03_motion.py`; v03 files are untouched).

| Problem in v03 | Cause found | v04 change |
| --- | --- | --- |
| Toe skim 1.31 mm at lift-off | Swing left the floor tangentially (zero vertical speed), half-frame linear keys dragged the tip | `LIFT_VZ` +0.30 m/s and `LAND_VZ` -0.30 m/s added to the swing end tangents: the toe pops off, the heel plants with a tiny accent |
| Marching knee at passing (swing knee 95 deg) | Not mainly `SWING_LIFT`: the swing inherited the full toe-roll velocity, so the foot whipped on to 77 deg pitch (shoe hanging vertical) and the ankle rose 14 cm | New `SWING_CARRY_Z` = `SWING_CARRY_PITCH` = 0.4 damp that hand-over; `SWING_LIFT` 0.075 -> 0.020 m, peak later `(2.4, 2.0)`; `SWING_TOE` 8 -> 4 deg |
| Crouched stance (knee never < 29 deg; 50 deg at contact) | Hips 5.7 cm below rest and lowest around contact | `BOB_CENTER` -0.057 -> -0.042 m, `BOB_HALF` 0.030 -> 0.033 m; contact carried high (key +0.35) and the body squashes into the down afterwards |
| Up not distinct from passing | Passing key +0.30 was already near the top | `BOB_KEYS` passing -0.05 at 0.46, up +1.0 later at 0.78; heel peels earlier (`T_HEEL_OFF` 0.30 -> 0.27) for a stronger push |

`BALL_END` was tried at 45 deg and set back to 42 (see review pass 3).

## Numbers (`build_report_v04.json`, `validation_v04_jsonmode.json`)

| | v03 | v04 |
| --- | --- | --- |
| Stance knee at contact / down / passing / up | 50 / 50 / 38 / 29 deg | 35 / 45 / 35 / 19 deg |
| Swing knee max | 94.6 deg | 79.4 deg |
| Max leg reach | 96.9 % | 98.7 % (at the up; knee still 19 deg, no pop) |
| Hips height (rest 0.82 m) | 0.734-0.792 m | 0.745-0.811 m (bob 6.6 cm, sway +/-2.2 cm) |
| Touchdown/lift-off skim | **1.31 mm FAIL** | **0.73 mm pass** |
| Support slide / sole height error / lowest vertex | 0.72 / 0.52 / -0.52 mm | 0.73 / 0.68 / -0.68 mm |
| Largest rotation step per half frame | 9.95 deg (LeftFoot) | 8.47 deg (LeftLeg) |
| Loop seam | 0.0 exact | 0.0 exact; seam velocity jump 0.039 < interior 0.108 |
| FBX | 65 bones, 1 take | 65 bones, root Hips, names/parents identical to the rig JSON, 1 take `Walk` 1-21, pose vs blend 3.9e-4 |

`all_pass: true` (A and B share the shoe soles; `sources_unchanged` is `skipped` in the no-LFS run).
The validator was run in JSON mode (Python skinning of `shoe_soles_v04.json`). Run blend mode locally
(section "Build locally") to write `validation_v04.json` against the real A/B meshes and `Walk_v02.fbx`.

Reproducibility: with `pip install bpy` (5.2.2) the v03 build reproduces the committed v03 metrics to
1e-8 m (skim 1.297 vs 1.305 mm comes from bpy-vs-Blender float rounding). The action digest differs at bit level from
the Windows Blender build, so compare the v04 digest only between runs of the same Blender.
v04 digest with bpy 5.2.2: `e97bf9b964a8...ea94b3a5`.

## Review passes (what I looked at and fixed)

Renders: `review_meshes_v04.py` regenerates the A v04 Body/Face/Outfit with the character's own procedural
builders and weights (crowd LOD) on the JSON rig. Its shoes match `shoe_soles_v04.json` exactly (0.0 m, 0.0 weight
error), so contact in the renders is the real one. Cycles 8 spp, 480x540, side / three-quarter / front on the
moving checker floor; sheets and onion skins via `review_sheet_v04.py`.

1. **Baseline v03 + skim fix (a0/a1).** Side sheet confirmed the handoff notes: at f6-f8 the swing knee rises near
   hip height with the shin tucked (march), the stance knee never straightens, f8-f10 is the same height as passing.
   After the tangent accents the skim fell to the slide value (0.72 mm). First bob change (higher centre, later up)
   made the up read at f8-f9, but the stance leg reached 99.2 % and the swing knee was still 91 deg.
2. **Swing hand-over (a2-a5).** Sampled the swing path: the ankle peaked 14 cm above rest with the foot at 77 deg
   pitch, inherited from the toe roll. Damping the carried velocity (0.4) plus a smaller, later lift brought the shoe
   from "hanging vertical" (f5-f6) to a low, relaxed trail, and passing (f6-f7) reads as a walk. Contact was still
   crouched (45 deg) by geometry (0.5 m step, 0.685 m leg), so the contact is now carried high and the body squashes
   into the down: knee 35 deg at contact, reach back under 98.7 %.
3. **Timing and close-ups (a6/final).** Frame-by-frame the hips fell 5 cm in ~2 frames after contact and stopped
   dead (a thud). Down moved to 0.20 with contact key 0.35: the drop now eases in and out over f1-f3, and the largest
   rotation step fell from 9.7 to 8.3 deg. Close-ups: forward hand clears the hoodie belly and pocket in both arm
   directions (f6, f16); the shoe bend at lift-off (f11-f13) showed a small notch at the lace top with 45 deg, so
   `BALL_END` went back to 42. Front view: head dips on the downs (f3/f13), rises on the ups (f9/f19), hip sway reads,
   no knock-knee.

Known, not fixed here: a small crease at the hoodie side seam under the arm in front close-ups (mesh/skin, also in
v03); MP4s were checked as frame sequences only (no real-time playback in the sandbox), so speed feel at 0.5x/1.4x
and in-game playback still need a human look; Unity import not done.

## Build locally

Windows (Git Bash, Blender 5.2), from this folder. Scripts refuse to overwrite outputs.
```
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
"$BL" -b --factory-startup --python build_walk_v04.py -- --out Walk_v04.blend --report build_report_v04_local.json
"$BL" -b --factory-startup --python export_walk_v03.py -- --blend Walk_v04.blend --fbx Walk_v04.fbx
"$BL" -b --factory-startup --python validate_walk_v03.py -- --rev v04
"$BL" -b --factory-startup --python render_walk_v03.py -- --blend Walk_v04.blend --out Previews/frames_v04 --samples 16 --res 640 720 --views side,threequarter,front
python make_previews_v03.py --frames Previews/frames_v04 --stem Walk_v04 --poses "1:Contact L,3:Down,6:Passing,9:Up,11:Contact R,13:Down,16:Passing,19:Up"
```
Without LFS (Linux/cloud, `pip install bpy`; `python3 script.py -- args` works the same as `blender -b --python`):
```
python3 build_walk_v04.py -- --source json --out Walk_v04.blend --report build_report_v04_local.json
python3 export_walk_v03.py -- --blend Walk_v04.blend --fbx Walk_v04.fbx
python3 validate_walk_v03.py -- --rev v04 --source json --out validation_v04_local.json
python3 review_meshes_v04.py -- --blend Walk_v04.blend --out Walk_v04_review.blend
python3 render_walk_v03.py -- --blend Walk_v04_review.blend --out Previews/frames_v04 --samples 8 --res 480 540 --views side,threequarter,front
python3 review_sheet_v04.py --frames Previews/frames_v04 --view side --crop 60 40 420 540 --out side_sheet.png
```
Note: `build_walk_v04.py --source blend` already keeps the real A v04 meshes, so `review_meshes_v04.py` is only
needed for the JSON path.

## Кратко по-русски

`Walk_v04` — вторая итерация ходьбы. Тайминг и контракты прежние: 20 кадров, 30 fps, 1,5 м/с, шаг 1,0 м,
на месте, точная петля, те же 65 костей.
- Убран «маршевый» подъём колена: маховая нога больше не наследует полную скорость переката через носок
  (кед раньше висел вертикально, щиколотка поднималась на 14 см). Колено в махе 79° вместо 95°.
- Меньше «приседа»: таз выше, на контакте нога почти прямая (35° вместо 50°), в позе «вверх» 19°.
- Поза «вверх» отчётливая: самая высокая точка позже, после пасса, пятка отрывается раньше (толчок носком).
- После контакта тело мягко «проседает» в «даун» за 2 кадра, без удара.
- Касание носком 1,3 мм исправлено: носок отрывается, а пятка ставится с небольшой вертикальной скоростью.
  Теперь 0,73 мм, все проверки зелёные.

В облаке не было LFS, поэтому в git только скрипты и JSON. `.blend`, `.fbx` и превью собираются локально
командами выше. Осталось: посмотреть MP4 вживую (0,5x и 1,4x), импорт в Unity и проверка в игре.
