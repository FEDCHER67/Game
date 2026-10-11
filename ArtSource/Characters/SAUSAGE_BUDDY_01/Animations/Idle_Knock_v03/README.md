# Sausage Buddy — idles and cargo-bay set (Idle_Knock_v03 package)

**State at the 2026-10-07 stop point:** one clip is delivered, four are designed but not authored. See `HANDOFF.md` for the full status, commands, contracts and the planned designs.

| Clip | Status | Files |
| --- | --- | --- |
| Idle_Stand_v03 | **Delivered** (validated 21/21, previews) | `Idle_Stand_v03.blend`, `Idle_Stand_v03.fbx`, `Idle_Stand_v03_authoring.json`, `validation_Idle_Stand_v03.json`, `Previews/Idle_Stand_v03/` |
| Idle_Bored_v03 | Not started (design in HANDOFF) | — |
| Cargo_Sit_Idle_v04 | Not started (design in HANDOFF) | — |
| Cargo_Knock_v03b | Not started (design in HANDOFF) | — |
| SitUp_Cargo_v04 | Not started (design in HANDOFF) | — |

Original local animation: FK deltas on a base pose plus roll-preserving analytic two-bone IK, authored as Python in Blender 5.2.1 LTS. No mocap, downloaded motion, paid generation or credits. Only this folder was written; the A/B v04 sources, the GPT packages, Assets/ and WORK_SYNC.md were not touched (input hashes in `provenance_v03.json`).

## Idle_Stand_v03 — default standing idle

Replaces GPT's Idle_Variant_B role ("he just stands"). 4.0 s loop, frames 1–121 at 30 fps; frame 121 duplicates frame 1.

- **0.0–0.45 s:** the knees stay locked for 0.45 s around the loop seam, then unlock; the first inhale starts.
- **0.3–1.55 s:** weight moves onto the **left** leg with an overshoot and settle. The hips shift 44 mm left and drop up to 10 mm. The free right knee relaxes forward by 68 mm, while the support knee bends by 33 mm. The chest and arms lag the shift (periodic damped springs), then catch up.
- **1.35–2.2 s:** the gaze drifts about 10° to his right and a little down (spacing out).
- **2.2–2.6 s:** a blink-like head settle: a quick dip, an overshoot up, then the head snaps home.
- **2.4–3.45 s:** a second, deeper breath lifts the shoulders about 13 mm. The weight returns home with a small counter-swing.
- **3.45–4.0 s:** the pose settles exactly onto the original A v04 `Idle` frame 1.

Contract: frame 1 and frame 121 are keyed with the **exact raw `Idle` frame-1 values**. The matrix error against Idle frame 1 is 0.0, as is the source loop seam. Every channel is periodic and zero at the seam, so the motion flows through the loop point. The feet stay on their exact Idle frame-1 matrices, so they cannot slide. The pelvis height is solved so the support leg never over-extends.

Validation (`validation_Idle_Stand_v03.json`) samples the saved Blend at 120 Hz:

| Check | Result |
| --- | --- |
| Sole penetration and support ground error | 0.0065 mm |
| Planted-foot slide | 0.008 mm |
| Largest key-to-key rotation | 1.17° |
| Quaternion sign flips, NaN, reflected bones | 0 |
| 65 bones, original order, rig/mesh data | Unchanged |

FBX reimport, compared with Walk_v02:

| Check | Result |
| --- | --- |
| Bone order and hierarchy | Equal |
| Bind-matrix error | 0.0 |
| Animated matrix error | 1.79e-5 |
| Reimported seam | 0.0 |
| Content | One take, armature only |

Previews, rendered from the saved Blend in the owner's grey studio:
- `Previews/Idle_Stand_v03/Idle_Stand_v03_side_loop_x3.mp4`
- `Previews/Idle_Stand_v03/Idle_Stand_v03_three_quarter_loop_x3.mp4`

Each MP4 plays three loops back to back so the seam can be judged. `Idle_Stand_v03_contact_sheet.png` shows ten labelled times per view. Review evidence for the three iterations is in `Previews/Review_01..03` (traces, key poses, and the candidate MP4 with front, side and three-quarter views).

Facial shape keys are not animated, matching the existing animation-only FBX pipeline. The face script in the game can add blinks, for example at the 2.26 s head dip.

## Unity import

Use the same settings as Walk_v02 and the GPT packages:
- Unity 6000.5.11f1, **Generic**, **Copy From Other Avatar** (A v04 avatar), **Preserve Hierarchy**, no animation compression.
- Keep the `Buddy_Rig_Mixamo65/mixamorig:Hips/...` paths.
- Turn **Loop Time on** over the full take, including the duplicated end frame.
- The FBX take is `Buddy_Rig_Mixamo65|Idle_Stand_v03`.

The FBX was exported with: selected armature only, -Z forward / Y up, apply units, no leaf bones, all 65 bones, bake at 0.5-frame steps, simplify 0, one action, no NLA. Unity import and in-game acceptance are not claimed.

## Краткое резюме (RU)

Готов один клип — **Idle_Stand_v03**, обычная стойка (4 с, цикл). Персонаж дышит, переносит вес на левую ногу; правое колено расслабляется, руки догоняют движение тела с запаздыванием. Взгляд уплывает вправо, затем голова «моргает» кивком и возвращается. Цикл начинается и кончается точно на кадре 1 исходного Idle. Стопы не скользят (0,008 мм), проверка пройдена 21/21, превью — сбоку и в три четверти.

Остальные четыре клипа спроектированы, но ещё не сделаны: скучающая стойка, испуганное сидение в кузове, стук в стенку, пробуждение в кузове. Работа остановлена по просьбе ведущего. План и команды — в `HANDOFF.md`.
