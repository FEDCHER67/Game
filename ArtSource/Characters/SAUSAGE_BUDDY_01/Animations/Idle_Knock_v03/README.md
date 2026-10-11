# Sausage Buddy — idles and cargo-bay set (Idle_Knock_v03 package)

**State 2026-10-07 (cloud session, branch `claude/anim-idle-cargo-v04-f9ijlq`):** all five clips are authored and validated. See `HANDOFF.md` for the commands, contracts, technique notes and what still needs Fedya's eye.

| Clip | Length | Loop | Validation | Files (built locally, see "Building") |
| --- | --- | --- | --- | --- |
| Idle_Stand_v03 | 4.0 s, f1–121 | yes | 21/21 (`validation_Idle_Stand_v03.json`) | delivered earlier, unchanged |
| **Cargo_Sit_Idle_v04** | 4.5 s, f1–136 | yes | 21/21 (`validation_cargo_v04.json`) | `.blend`, `.fbx`, `_authoring.json` |
| **Cargo_Knock_v03b** | 3.3 s, f1–100 | yes (on the sit contract) | 21/21 (`validation_cargo_v04.json`) | `.blend`, `.fbx`, `_authoring.json` |
| **SitUp_Cargo_v04** | 2.4 s, f1–73 | no | 21/21 (`validation_cargo_v04.json`) | `.blend`, `.fbx`, `_authoring.json` |
| **Idle_Bored_v03** | 6.0 s, f1–181 | yes | 21/21 (`validation_Idle_Bored_v03.json`) | `.blend`, `.fbx`, `_authoring.json` |

Original local animation: FK deltas on a base pose plus analytic two-bone IK, authored as Python and run headless through Blender 5.2 (`pip install bpy` 5.2.2 in the cloud, using the LFS-free rig JSON). No mocap, downloaded motion, paid generation or credits. Only this folder was written; the A/B v04 sources, the GPT packages, `Assets/` and `WORK_SYNC.md` were not touched.

**Binaries are not in Git for this round.** The cloud session cannot push LFS objects, so the `.blend`, `.fbx`, `.png` and `.mp4` outputs are rebuilt locally from the scripts (bit-for-bit deterministic, see "Building"). The validation JSONs in the repo were produced from exactly those builds.

## The cargo stage (for Unity placement)

- Floor z = 0; side wall plane **x = −0.65** (`acting_core.WALL_X`); height limit **1.2 m** above the floor.
- Seated, he faces **+X** with his back (the big hood) to the wall. Contract hips: **(−0.357, 0, 0.114)** m; the hood touches the wall with 3 mm clearance (`Cargo_Sit_Contract_v04.json` holds the raw values and this layout).
- The van's rear **doors are toward −Y**: his right while seated. All glances, the knock swivel and the sit-up panic look go that way.
- Place the van so its side wall is the plane x = −0.65 in the animation's space and the floor is z = 0; do not add another 90° turn. The sit-up's Hips curve carries the 90° turn and the ~0.36 m scoot toward the wall; leave root motion off.

## Cargo_Sit_Idle_v04 — scared sitting loop (4.5 s)

Base pose (frame 1 = the **cargo sit contract**): knees up, feet flat 0.47 m in front of the hips, both hands wrapped round the shins (finger curl 0.5), pelvis tipped back 16°, spine curled forward, shoulders shrugged, head low over the knees, face readable from the front.

- 0.0–0.6 s: shallow panicky breathing (9 breaths per loop) and trembling (periodic noise, 31/37/41 cycles per loop = 6.9–9.1 Hz, 0.4–0.7°, zero at the seam).
- 0.42–0.56 s: a tiny anticipation (head 4° the other way), then **0.56–0.75 s a SNAP glance at the doors** (57° with overshoot, the chest follows 25 % through a lagging spring, the shoulders jolt up).
- 0.75–1.45 s: he stares, trembles harder and **shrinks back into the wall**. The lean is stopped by the wall itself: a contact solve tips the spine just enough to keep the hood on the wall (up to 5°), so it reads as pressing, not as a hard stop.
- 1.45–1.85 s: a slow, reluctant turn back with a small overshoot.
- 1.72–2.2 s: **GULP**: chin tuck, head dip, shoulders up and down, the arms squeeze the knees (curl 0.75, hands pulled inward).
- 2.2–2.95 s: two anxious rocks on the butt (6.5° and 5.5° forward; the wall stops the back swing; the feet stay planted).
- 2.85–3.22 s: **double-take** at the doors: 31°, a 2-frame hold, then 60° with overshoot and a hold.
- 3.22–3.6 s: turns back and **sinks lower behind the knees**; 3.6–4.5 s settles into frame 1.

## Cargo_Knock_v03b — desperate banging (3.3 s, loops on the sit contract)

- 0.0–0.2 s: anticipation: a squash and the head **snaps toward the wall** over his right shoulder.
- 0.17–0.5 s: the swivel: he **turns ~80° to his right on the butt**, lurching ~16 cm off the wall so his right shoulder clears it (he stays ~9 cm out while pounding; the lean brings his face to the wall); the knees fall to his left into a side-sit while the feet skid round a hair (8 mm) off the floor; the chest twists a further 92° (172° in total, ~8° off square, chosen so the right arm never has to pass through the wall). The arms let go of the knees and rise.
- 0.55–1.45 s: **pounding**. He leans in until his face touches the wall, his head turned ~40° toward the doors (yelling for help, readable from the −Y cameras). Alternating hammer-fists L 0.62, R 0.78, L 0.94, R 1.10 s (6.25 Hz alternation) with a body bounce and a head shake on every hit; each fist is stopped on the wall by a mesh contact solve (**2.5 mm** from the wall plane on every hit; the other fist is wound up 3–10 cm off the wall). Then **both fists rise (1.12–1.26 s, whole mesh ≤ 1.06 m) and SLAM together at 1.40 s**, held a beat.
- 1.47–2.24 s: **listening**: palms flat on the wall, a strong lean in with the head tipped so the ear/cheek presses on the wall (the contact solve stops it on the wall), frozen apart from a tiny tremble.
- 2.22–2.95 s: the slump: he deflates, the fists come off the wall through a guard in front of the chest and drop back to the knees while he swivels back.
- 2.85–3.3 s: a sad sigh (shoulders up, then down) into the exact knee hug.

## SitUp_Cargo_v04 — wakes up in the van (2.4 s, one-shot)

- 0.0–0.13 s (frames 1–4.9): **exact supine hold** = GetUp_FromBack_v02 frame 1 (raw values; ragdoll-compatible, head toward +Y). **hipsStart = (0, 0, 0.3070) m.**
- 0.13–0.42 s: groggy stir: the head rolls, the legs drop and bend, the feet slide up to the butt on the floor (the body is floor-fitted every sample, so the lifted-on-the-hood supine pose settles onto the floor instead of floating).
- 0.40–0.80 s: a heavy sit-up pushing on the floor with both palms; **the giant head lags back, then flops forward past the pose and bounces** (0.68–1.0 s).
- 0.80–1.15 s: dazed "brrr" head shake, 3 decaying shakes (±22° yaw with roll).
- 0.94–1.55 s: **rubs the bump** on the right side of his head in small 4 Hz circles; the head tilts into the hand with a wince and the shoulders hunch.
- 1.48–1.70 s: the hand freezes, a slow look up, then a **SNAP panic glance at the doors** (in front of him here).
- 1.68–2.06 s: **scramble**: he turns 90° to his left (to face +X) and scoots toward the wall in two heel pushes; the hood bumps the wall (a small squash, the wall stops the scoot) .
- 1.86–2.40 s: curls into the knee hug and lands exactly on the sit contract.
- Events for the game: **SatUp** (upright, sitting on the floor) at frame 25 (0.80 s, fraction 0.33); **Seated/Stable** in the van pose from frame 70 (2.30 s, fraction 0.96). There is no standing capsule event: he ends sitting.

## Idle_Bored_v03 — bored standing loop (6.0 s, on Idle frame 1)

- 0.25–1.3 s: "anybody coming?": looks 42° right (fast in, overshoot, drifting hold), then sweeps 46° left dipping mid-arc, and holds.
- 1.30–2.4 s: **watch check**: the left forearm snaps up across the chest (wrist at (0.05, −0.25, 1.05)), the head drops to look, a double take (pull back, lean in) and two quick wrist shakes.
- 2.4–3.7 s: the **BIG SIGH**: a huge inhale (24° clavicle shrug with arm counter-rotation, chest up, head tipped back 13°), a hold, then a hard exhale: shoulders drop below neutral, the spine slumps, the knees unlock (hips drop ~3 cm), the hip pops to his right with the left knee bent, the arms dangle on pendulum springs, the head sags and bounces.
- 3.66–5.24 s: **lazy scratch** of the back of his head with the right hand (target in the Head frame, 4 Hz scratching, the head tilts into it, finger curl pulses).
- 5.2–6.0 s: straightens and settles; the knees are locked for 0.35 s before the seam.
- The feet never leave their Idle frame-1 matrices (slide 0.17 mm, support error 0.14 mm). The pebble kick was not used (the watch check is the required beat).

## Validation (independent: opens the saved `.blend`, samples at 120 Hz, reimports the FBX)

| | Sit_Idle_v04 | Knock_v03b | SitUp_v04 | Bored_v03 |
| --- | --- | --- | --- | --- |
| Checks | 21/21 | 21/21 | 21/21 | 21/21 |
| Source loop seam | 0.0 | 0.0 | (one-shot) | 0.0 |
| Start contract error | 0.0 (sit) | 1.0e-6 (sit) | 5.4e-7 (supine) | 0.0 (Idle) |
| End contract error | 0.0 (sit) | 1.0e-6 (sit) | 6.6e-7 (sit) | 0.0 (Idle) |
| Largest key-to-key rotation | 17.1° | 22.9° | 20.7° | 21.3° |
| Quaternion sign flips / NaN / reflected | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Max mesh height (≤ 1.2 m) | 1.019 m | 1.053 m | 1.059 m | — |
| Min mesh z (floor) | +0.02 mm | +0.01 mm | +0.01 mm | sole pen. 0.14 mm |
| Min mesh x (wall −0.65) | −0.6485 | −0.6490 | −0.6486 | — |
| FBX bind / animated error | 1.7e-5 / 1.6e-5 | 1.7e-5 / 1.8e-5 | 1.7e-5 / 1.8e-5 | 1.7e-5 / 1.9e-5 |
| FBX reimported seam | 0.0 | 3.0e-7 | — | 0.0 |

All 65 bones in the original order, rig and mesh data unchanged, one take, armature only. The 1e-6-level start/end contract errors are float32 evaluation noise: the knock and sit-up key the identical raw values from `Cargo_Sit_Contract_v04.json` (the validator threshold is 1e-5). The FBX bind reference is the rig JSON in an LFS-less checkout (its stored `matrix_local` values; 1.7e-5 is the rebuilt-armature roundoff, under the 1e-4 gate).

## Review passes (what I looked at and fixed)

I rendered every clip myself, in a fast numpy/Pillow rasteriser of the skinned mesh (`quicklook.py`, every frame) for motion and in Eevee for the final previews, and looked at frame strips, key poses and dense close-ups, plus per-bone rotation-step scans and contact scans.

1. **Pass 1 (motion, every frame, all four clips).**
   - Knock: the first version ran the arm IK with poles fixed in the van while the body twisted 150°: 180° elbow and knee flips, a 72° upper-arm pop and a full 360° arm twist over the loop. Fixed with flip-free IK frames (`solve_chain2`), body-relative poles, a rotation-space blend between the knee-hug arm and the wall arm, hemisphere-consistent blending so the arm goes out and back by the same path, and a soft reach clamp (a locked elbow snaps open like the straight Idle knees).
   - Knock: the fists stopped 2–9 cm short of the wall because the huge head reaches the wall first; the right arm swept through the wall during the swivel. Fixed with lower/wider contacts beside the head, a lean-in limited by the head contact, a short lurch off the wall during the swivel, elbows kept off the wall, and the swivel finishing nearer square. Every hit now lands at 2.5 mm.
   - Knock: from the −Y cameras he pounded in pure profile or with his back turned. The head now turns ~40° toward the doors while pounding.
   - Sit-up: switching the arms between FK and IK popped by up to 133°; now FK↔IK is a rotation blend. The bump rub was on the back of the head, hidden from every camera; moved to the side/top of the head.
   - Sit idle: the shrink-back drove the hood 2.8 cm into the wall; the wall contact solve now limits the lean.
   - Bored: 87° FK/IK pops when the watch arm and the scratch arm switch on; now blended.
2. **Pass 2 (personality at gameplay distance).** Bigger sigh (shrug 18→24°, head back 8→13°) and a wider hip pop; bigger anxious rocks (4→6.5°); the sit-up head lags longer and flops further (34→42°); anticipation before the sit idle's snap glance; the knock face toward the doors.
3. **Pass 3 (final Eevee previews from the saved `.blend`).** See "Final review" below.

## Final review (Eevee previews from the saved files)

Rendered with the package's own preview path (`build_v03.py --from-saved --every 1 --res 480 --seq`, owner's grey studio, cargo wall + 1.2 m line), side and three-quarter, every frame. Then MP4s (loops shown 3× with the duplicated end frame dropped) and the 10-still contact sheets (`make_sheets.py contact`). They are not in Git (LFS): rebuild them with the commands in HANDOFF §3. They were shared in the session that made this PR.

- **SitUp_Cargo_v04:** Reads in both views. You see the supine contract, the legs dropping, and the head lagging back while the torso comes up (clearest in three-quarter at 0.6 s). He rubs the side of his head, snaps a panic look at the doors, then the turn and the two-push scoot. The hood bumps the wall and he curls into the hug. The forward head flop reads less from the frontal doors-side camera than from three-quarter.
- **Cargo_Knock_v03b:** Reads well from the doors-side (−Y) camera. The fist cocks during the swivel, he pounds with his face at the wall, raises both fists overhead, slams, listens with his ear on the wall, then slumps back into the hug. **Open point:** from the handoff's three-quarter camera at (2, −4, 1.6) the pounding is seen mostly from behind his head and hood, and the fists are partly hidden. If Fedya wants the hits readable from that side, options: a corner layout (HANDOFF §7 alternative, needs a Unity placement decision), or a knock that bangs sideways with the near arm. Ask before changing the stage.
- **Cargo_Sit_Idle_v04:** The doors-side camera catches his face on every glance (0.67, 2.93, 3.07 s). The gulp dips his head (1.97 s) and he sinks behind his knees (3.53 s). The three loops in the MP4 run through the seam without a hitch. The trembling is subtle at 480 px, as specified (0.4–0.7°).
- **Idle_Bored_v03:** The look-around, the watch snap with the double take, the big inhale with the head thrown back (2.93 s), the deflated slump with bent knees and the hip out (3.33 s), and the lazy scratch (the elbow up reads in three-quarter; from the +X side camera the right hand is on the far side). The knees lock again before the seam, and the loop is clean.

## Building (local, Windows, Blender 5.2)

From the repository root, `PKG = ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Idle_Knock_v03`, `blender = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"`:

```
blender -b --factory-startup --python %PKG%/build_v03.py -- --clip Cargo_Sit_Idle --final
blender -b --factory-startup --python %PKG%/build_v03.py -- --clip Cargo_Knock --final
blender -b --factory-startup --python %PKG%/build_v03.py -- --clip SitUp_Cargo --final
blender -b --factory-startup --python %PKG%/build_v03.py -- --clip Idle_Bored --final
```

Each writes `<stem>.blend`, `<stem>.fbx` and `<stem>_authoring.json` and refuses to overwrite. The cargo clips read the frozen contract from `Cargo_Sit_Contract_v04.json`. The knock build takes ~3 minutes (two pre-passes over the clip). To compare with the committed validation, run the validator into a new name (it refuses to overwrite):

```
blender -b --factory-startup --python %PKG%/validate_v03.py -- --clips Cargo_Sit_Idle,Cargo_Knock,SitUp_Cargo --out %PKG%/validation_cargo_v04_local.json
blender -b --factory-startup --python %PKG%/validate_v03.py -- --clips Idle_Bored --out %PKG%/validation_Idle_Bored_v03_local.json
```

The committed validation used the rig JSON (`rig_source: json`, no LFS). With the real `.blend` sources the scripts read the A v04 file directly; the handoff verified both paths give identical poses. Previews: see `HANDOFF.md` §3 (`--from-saved`, `--seq`, ffmpeg, `make_sheets.py contact`). In a GPU-less session use `pip install bpy` and run the same scripts with `python` instead of `blender -b --python`; Eevee needs `libegl1` + Mesa there.

## Unity import

Same settings as Walk_v02 and the GPT packages: Unity 6000.5.11f1, **Generic**, **Copy From Other Avatar** (A v04 avatar), **Preserve Hierarchy**, no animation compression; keep the `Buddy_Rig_Mixamo65/mixamorig:Hips/...` paths. Loop Time **on** for Cargo_Sit_Idle_v04, Cargo_Knock_v03b and Idle_Bored_v03 (over the full take, including the duplicated end frame); **off** for SitUp_Cargo_v04. Takes are `Buddy_Rig_Mixamo65|<stem>`. FBX: selected armature only, −Z forward / Y up, apply units, no leaf bones, 65 bones, baked at 0.5-frame steps, simplify 0, one action. No face animation (animation-only FBX); good blink/expression moments for the face script: sit idle 0.66 s and 3.03 s (glances), 1.98 s (gulp); knock 1.40 s (slam), 1.7 s (listening); sit-up 0.8 s (dazed), 1.64 s (panic); bored 2.95 s (sigh), 4.3 s (scratch). Unity import, ragdoll blending and in-game acceptance are not claimed.

## Краткое резюме (RU)

Сделаны все четыре оставшихся клипа, каждый прошёл проверку 21/21.
- **Cargo_Sit_Idle_v04** (4,5 с, цикл): сидит в кузове, обхватив колени, дрожит, резко косится на двери (направо), вжимается в стенку, сглатывает, раскачивается, делает «двойной взгляд» и прячется за колени. Кадр 1 — общий «контракт сидения» для стука и пробуждения (`Cargo_Sit_Contract_v04.json`).
- **Cargo_Knock_v03b** (3,3 с, цикл): разворачивается на попе вправо, колотит в стенку двумя кулаками поочерёдно (каждый удар ровно касается стены, 2,5 мм), поднимает оба кулака и бьёт с размаху, потом прижимается ухом к стене и слушает, сдувается и возвращается в ту же позу.
- **SitUp_Cargo_v04** (2,4 с): первый кадр — точная поза лёжа из GetUp_FromBack_v02 (hipsStart 0,307 м, совместимо с рэгдоллом), вялое шевеление, тяжёлый подъём с отстающей и падающей вперёд головой, «брр»-тряска, потирает шишку, паника, поворот и отползание к стенке, обхват коленей.
- **Idle_Bored_v03** (6 с, цикл): оглядывается, смотрит на «часы» с двойным взглядом и трясёт запястьем, огромный вздох с осадкой, лениво чешет затылок.
Высота ≤ 1,06 м (лимит 1,2), пол и стенка не пересекаются, швы цикла точные, кости и порядок те же. Бинарные файлы (.blend/.fbx/превью) в этот раз не в Git — собираются локально скриптами (команды выше).

## Fixes round 2026-10-11: Idle_Stand_v04, Cargo_Sit_Idle_v05, SitUp_Cargo_v05

New revisions (the older clips, scripts and `Cargo_Sit_Contract_v04.json` are unchanged). Code: `clips_standing_v04.py` (Idle_Stand_v04) and `clips_cargo_v05.py` (Cargo_Sit_Idle_v05, SitUp_Cargo_v05), built with `build_v05.py --clip <stem> --final` and checked with `validate_v05.py`. All three: **21/21** in `validation_v05_stand_sit_situp.json` (rig JSON path, bind reference = rig JSON; FBX bind error 1.6e-5, animated error ≤ 2.2e-5, 65 bones in order, one take, no sign flips / NaN / reflected bones).

### Idle_Stand_v04: default standing idle, alive (5.0 s loop, f1–151, on the exact Idle frame 1)

- 0.00–0.25: knees locked at the seam (exact Idle frame 1), bottom of the exhale.
- 0.20–1.10: first breath in (11° clavicle shrug with arm counter-rotation, chest lifts, head rises); 0.25–0.45 anticipation push onto the left leg.
- 0.45–1.30: **weight sways onto his right leg** with overshoot and settle: hips 6.5 cm over, pelvis tips 7°, the **left knee unlocks and bends forward-in** (~9 cm), the support knee softens a little; the chest and the arms lag on springs.
- 1.00–1.88: **look to his left** (toward the side camera): a small dip the other way, snap to 41° with overshoot, curious head cock, drifting hold; the chest follows ~30 % on a lagging spring.
- 1.88–2.76: sweep to his right dipping mid-arc (blink-like), −35° overshoot, hold; 2.2–3.2 second, deeper breath.
- 2.72–3.36: weight back through the middle and a little onto the left leg; head back to centre.
- 2.98–3.38: **fidget**: the left shoulder dips (anticipation), the elbow folds and the hand comes up close to the body to the left cheek.
- 3.38–3.84: **scratches the left cheek** with the fingertips (6 Hz strokes; a head-surface contact solve keeps the fingertips 1.4 mm off the skin, never inside); the head tilts 10° and dips into the hand, the shoulder hunches.
- 3.84–4.28: the hand drops down beside the body (IK path, pendulum follow-through), then a sniff (head lifts 3.96–4.28); long exhale.
- 4.30–5.00: settles; knees locked from 4.60 s into the seam (0.40 s before, 0.25 s after it; HANDOFF 8.1).
- Validation: seam 0.0, contract error 8e-7 (float noise of the raw Idle values, gate 1e-5), largest key step 19.6°, sole penetration 0.10 mm, support error 0.10 mm, planted-foot slide 0.12 mm. Pop scan: top 79 m/s² (the hand rising to the face), median 0.1.

### Cargo_Sit_Idle_v05: scared sitting loop, stronger (4.5 s loop, f1–136, exact cargo sit contract at both ends)

- 0.00–0.47: panicky breathing (9 per loop) and a **visible shiver**: periodic noise (31/37/41 cycles per loop, zero at the seam) of 1.1–1.9° on spine, neck and head, 2.6° shoulder jitter, 5.5 mm hand jitter (head-top shiver about twice v04, hands about 4×); 0.36–0.47 anticipation (head 6° the other way).
- 0.47–0.64: **SNAP glance at the doors** (63° with overshoot, face to the −Y camera), shoulder jolt, chest follows on a lagging spring.
- 0.60–0.90: **SHRINK**: shoulders up to the ears (+24° shrug), head pulled down between them (neck forward, head pitched back to keep watching), pelvis rolls under so the back presses into the wall (wall contact solve, up to 2.3° lean correction, hood 1.5 mm off the wall), knees squeezed together, feet dragged in 6.5 cm (small lift).
- 0.90–1.40: frozen stare, shivering hardest. 1.40–1.88: slow reluctant turn back with a small overshoot.
- 1.80–2.20: GULP (chin tuck, head dip, shoulder bob, arms squeeze).
- 2.10–2.98: **two big anxious rocks** (12° and 11° forward, v04: 6.5/5.5°); the wall stops the back swings; the giant head lags and nods after each.
- 2.95–3.36: **double-take**: 33°, a 2-frame hold, SNAP 65° with overshoot, hold, shrinks again. 3.36–3.72: turns back and sinks lower behind the knees.
- 3.70–4.50: settles; the feet slide back out into the exact contract.
- Validation: seam 0.0, start/end contract error 0.0, largest key step 14.0°, mesh height ≤ 1.019 m, floor +0.02 mm, wall clearance 1.45 mm. Pop scan: top 92 m/s² (double-take jolt), median 1.1.

### SitUp_Cargo_v05: wakes up in the van, bigger flop, unrushed scramble (3.0 s one-shot, f1–91)

- 0.00–0.15 (frames 1–5.5): **exact supine hold** = GetUp_FromBack_v02 frame 1 (raw values, hipsStart 0.3070 m) for the ragdoll blend.
- 0.15–0.44: groggy stir: head rolls, the legs drop and bend, feet slide to the butt.
- 0.42–0.84: heavy sit-up on both palms; **the giant head lags back** (−54°, chin to the ceiling).
- 0.81–1.37: **the head FLOPS forward past the pose** (+42°, chin on the chest), bounces back up (−13°), flops again (+20°), settles.
- 1.06–1.48: dazed wobble (the head circles, decaying). 1.40–1.70: quick "brrr" shake (2.5 shakes).
- 1.44–1.99: rubs the bump on the right side of his head, wincing.
- 1.96–2.20: the hand freezes, slow look up, **SNAP panic glance** at the doors; the palms slam down on the floor.
- 2.14–2.76: **scramble, 0.62 s** (v04: ~0.3 s): turns 90° to his left and scoots 0.36 m to the wall in **three heel + palm pushes** (2.17, 2.37, 2.58 s). Feet and palms are planted on the floor during each push while the butt slides; between pushes they hop to the next plant.
- 2.66–2.90: the hood bumps the wall (squash and rebound). 2.56–3.00: curls into the knee hug, landing exactly on the cargo sit contract.
- **Events: SatUp** at frame 27 (0.867 s, fraction 0.289); **Seated/Stable** from frame 88 (2.90 s, fraction 0.967). Also in `SitUp_Cargo_v05_authoring.json` (`authoring_stats.events`).
- Validation: start (supine) error 5e-7, end (sit) error 7e-7, hips first height 0.3070 m, largest key step 21.8°, mesh height ≤ 1.033 m, floor +0.01 mm, wall clearance 1.45 mm. Pop scan: top 370 m/s² on HeadTop_End at 0.82/0.95/1.02 s = the intended flop whip and bounce (v04 flop: 256), median 2.1.

### Review passes

1. Pass 1 (traces, key poses, every-frame Eevee renders, side + three-quarter): Idle_Stand: the scratch arm swung straight out in front on the way up and down (FK↔IK blend far apart) → the elbow now leads with an inward forearm fold and the release is an IK path; a knee notch at 0.45 s reduced. Sit idle: the rock-lag sign was reversed (the head slammed face-down onto the knees) → fixed; three quick rocks read weakly → two big rocks. Sit-up: the flop put the face into the knees (63° → 42°); the feet slid during the scramble → planted per push.
2. Pass 2 (validator + pop scan on dry builds): sit-up key steps of 52° and a 0.5 mm floor dip (hands following the knees, IK reach snaps, fast slam) → palm plants with a soft reach and longer blends, a 1.2 mm scramble floor margin; Idle_Stand: a 240 m/s² hand jerk at the release (FK/IK blend + contact switch) → contact-corrected target and an IK-carried release (now 75 m/s²); the sniff moved after the hand leaves. Sit idle shrink pushed further (shoulders 17° → 24°).
3. Pass 3 (Eevee previews from the saved files): all beats read from both cameras; loop seams pixel-identical.
- Still to judge in Unity: the stand fidget plays every 5 s (it may want a random-offset start); the sit idle's feet drag in/out once per loop; the sit-up flop is a deliberate whip.

Files: `Idle_Stand_v04.*`, `Cargo_Sit_Idle_v05.*`, `SitUp_Cargo_v05.*` (`.blend`, `.fbx`, `_authoring.json`), `validation_v05_stand_sit_situp.json`, `Previews/<stem>/` (frames side + three-quarter, all N+1 frames; MP4s: loops shown 3× without the duplicated end frame, the sit-up once; 10-still contact sheet). Unity import as above (Loop Time on for the two loops, off for the sit-up).

Кратко (RU):
- **Idle_Stand_v04** (5 с, цикл): заметное дыхание (плечи и грудь), перенос веса на правую ногу с согнутым левым коленом, огляд влево-вправо с отставанием корпуса, почёсывание щеки левой рукой и шмыг носом. Колени прямые у шва цикла, ступни не скользят.
- **Cargo_Sit_Idle_v05** (4,5 с, цикл): видимая дрожь, резкие взгляды на двери, сильное «сжатие» (плечи к ушам, голова вниз, колени вместе, ноги подтянуты), два больших раскачивания; кадр 1 — тот же контракт сидения.
- **SitUp_Cargo_v05** (3 с): большая «болтанка» головы (отставание назад, падение вперёд, отскок, покачивание), разворот к стенке за 0,6 с тремя толчками пятками и ладонями. События: SatUp — кадр 27, Seated/Stable — с кадра 88.

## Fixes round 2026-10-11: Cargo_Knock_v04

New revision of Cargo_Knock_v03b (v03b and its files are unchanged): **3.5 s loop, f1–106, the exact cargo sit contract at both ends** (raw values from `Cargo_Sit_Contract_v04.json` keyed through `canonical`). Code: `clips_knock_v04.py` (imports the `clips_cargo` machinery, never edits it), built with `build_v05.py --clip Cargo_Knock_v04 --final`, checked with `validate_v05.py`: **21/21** in `validation_Cargo_Knock_v04.json`.

**Staging change.** v03b swivelled ~80° and twisted the chest ~92° more to face the wall, so from the doors-side cameras the fists were hidden behind the giant head and hood (it looked like he pressed his face to the wall). v04 spins ~88° to his right on the butt and scoots 24 cm off the wall: he **faces the doors (−Y, the review cameras)**, the wall is at his right side and his legs fold to his left. The near (right) arm bangs **sideways**: the elbow stays out at shoulder height, the forearm tips in over the head (the wind-up) and swings out upright like a wiper, so the pinky side of the fist meets the wall. That arc lies in the side camera's image plane; the face and both fists stay visible from the side and three-quarter cameras during every hit.

Beats:
- 0.00–0.30: anticipation: a startled inhale (shoulders up, head up and turned over his right shoulder), then a squash.
- 0.17–0.62: spins ~88° right on the butt (counter-move, overshoot, settle) and scoots off the wall; the feet skid round 7 mm off the floor; the arms let go of the knees.
- 0.40–0.71: wind-up 1 (the big one): right forearm tipped in over the head, body leaning 24° away, head pulled back. The left fist pumps in front of his belly through all the bangs.
- 0.80: **BANG 1**; the body whips toward the wall, follows through and rebounds; the giant head lags on a spring and wobbles.
- 0.85–1.09: recoil and wind-up 2 → 1.167 **BANG 2**, a short bounce off the wall, 1.333 **BANG 3** (BANG … BANG-BANG).
- 1.36–1.66: the fist opens into a palm flat on the wall at shoulder height, he leans in until his head is on the wall (body contact solve), face still to the cameras, left index raised ("wait…").
- 1.66–2.04: listening hold, frozen with a tiny tremble (hopeful silence).
- 2.04–2.40: frustrated mega wind-up: both fists up, body coiled 34° away, head thrown back; hold.
- 2.50: **SLAM**: right fist on the wall, left fist on his own knee; head jolt, held beat.
- 2.55–3.03: deflate: the fist slides down the wall, the arm drops off it and hangs, the head droops, the shoulders sag.
- 2.86–3.50: spins back with the head leading, a sad sigh, lands in the exact knee hug.

**Hit times (sound and face scripts).** The right fist first touches the wall (≤ 3 mm, measured on the skinned mesh of the saved file) at **0.783 s (frame 24.5), 1.150 s (35.5), 1.333 s (41) and 2.483 s (75.5)**; the nominal impacts (fist stuck on the wall, body follow-through) are 0.80 / 1.167 / 1.333 / 2.50 s, and the left fist hits his knee at 2.50 s (frame 76). The hand is on the wall 0.78–0.90, 1.15–1.25, 1.33–2.15 (BANG 3 into the listening palm) and 2.48–2.92 s (slam and slide; during the follow-through 2.53–2.62 it floats up to 6 mm off). Face-script moments: the listening silence 1.66–2.04 s (hopeful), the mega wind-up 2.30–2.40 (angry yell), the slam 2.50, the droop 2.85. The same numbers are in `Cargo_Knock_v04_authoring.json` (`authoring_stats`).

**Validation** (rig JSON path, bind reference = rig JSON): start/end contract error 6.0e-7 (float noise, gate 1e-5), source seam 0.0, FBX reimported seam 1.5e-7, largest key-to-key rotation 22.6°, 0 sign flips / NaN / reflected bones, mesh height ≤ 1.059 m, floor +0.02 mm, wall clearance 0.68 mm (min x −0.6493), FBX bind error 1.6e-5, animated error 1.9e-5, 65 bones in order, one take, armature only. Fist contacts 2.5 mm from the wall. Pop scan: top 321 m/s² (HeadTop_End at the BANG-BANG), all top values on hits or the slam swing, median 1.8.

**New technique.** `SitRig4` (a subclass) adds the sleeve cuff to the fist's wall-contact set and solves the contact with a bracketed regula falsi, re-aligning the fist with the forearm after every re-solve; the v03b loop shifted by the full excess, overshot by 1.5 cm and twisted the hand 36°. Contact points are frozen per hit in the van frame, so the fist does not slide while it is stuck. Strike ease-ins use exponents < 1.5 and every contact sits on a key. The body lean is fastest at the contact and follows through (head-top pops 577 → 321 m/s²). Elbow hints stay well off the reach line (two bend-plane flips found and fixed). The post-pass `_post` runs `limit_rotation_steps` plus a validator emulation that checks every 120 Hz in-between sample on the skinned mesh (wall, floor, 1.2 m) and swings an arm only where it would graze the wall. Neither had anything to fix in the final build. The v03b 4 mm arm margin is not used, so the hits stay at 2.5 mm.

**Review passes.**
1. Fast every-frame numpy renders and traces:
   - The hit read as a reach and slide: the fist met the wall at 0.8 m and slid 23 cm down. Fixed with the elbow-pivot wiper bang.
   - The elbow was 3.7 cm inside the wall: the elbow now goes forward and out.
   - The guard path crossed his mouth: the guard is now lateral.
   - The listening palm sat by his cheek: it is now lower and further forward.
   - The "wait" hand was an open palm: it is now a raised index.
2. Eevee pass 1 (every 2nd frame, side and three-quarter):
   - The mega wind-up was barely bigger than wind-up 1: 34° lean, head thrown back, both fists higher.
   - The slam hold was static and the hand rose in front of the face on the way back: two-stage deflate (slide, then drop), with the guard blend off at the end.
3. Eevee pass 2:
   - The anticipation was too subtle: inhale plus squash.
   - The deflate was weak: the head drops 28°, the shoulders sag and the fist slides lower.
4. Final previews from the saved file: every beat reads in both comparison cameras and the loop seam is continuous. Also checked `three_quarter_cargo` (reads) and `front`: from +X he is in profile after the swivel, so the bangs read less there, a consequence of this staging.

Files: `clips_knock_v04.py`; `Cargo_Knock_v04.blend`, `.fbx`, `_authoring.json`; `validation_Cargo_Knock_v04.json`; `Previews/Cargo_Knock_v04/`. The previews are the frames for side and three-quarter (all 106), MP4s with 3 loops without the duplicated end frame, and a 10-still contact sheet. Unity import as above (Loop Time on).

Кратко (RU):
- **Cargo_Knock_v04** (3,5 с, цикл, контракт сидения на обоих концах): разворачивается на попе вправо **лицом к дверям** (к камерам), стенка справа, колотит в неё сбоку правым кулаком: большой замах, БАМ… БАМ-БАМ; потом прижимается головой к стене и слушает, подняв палец («тихо…»); огромный замах двумя кулаками и СЛЭМ (правый — в стену, левый — по своей коленке); сдувается и возвращается в обхват коленей.
- Лицо и оба кулака видны с боковой и трёхчетвертной камер. Удары: 0,78 / 1,15 / 1,33 / 2,48 с. Проверка 21/21.
