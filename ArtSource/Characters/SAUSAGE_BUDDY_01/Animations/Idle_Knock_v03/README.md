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
