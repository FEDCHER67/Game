# Cooperative physics grip feel pass (2026-09-29)

## Outcome

One Sol 6 Medium line implemented the pass. `NetworkGrabber` now preserves the actual hit distance and assigns a monotonically increasing target sequence within each hold. `NetworkPhysicsBody` rejects reordered/stale target packets, prevalidates holders, and applies bounded relative-velocity damping for two or more holders. The existing solo solver remains in use for one holder. The table now has a dedicated profile (k=900 N/m, damping ratio 1, 450 N per holder, linear cap 6 m/s, angular cap 3 rad/s); cube and scalpel profiles were left untouched.

An opt-in two-client moving-table smoke measured mean contact error 2.051→1.303 m near t=9.7 s and 2.338→1.231 m near t=10.7 s compared with the prechange build. Both grips acquired with logged initial gap 0; release progressed 2→1→0. An opposing-pull run kept table mean speed at roughly 0–0.001 m/s and rejected stale sequence-1 packets. Isolated Unity 6000.5.11f1 player build passed with zero errors; executable `C:/Dev/GameBuilds/CoopFeelCandidate/VolunteersOnlyCoopFeel.exe`, logs under `C:/Dev/CoopTrialValidation/` (`build-feel-final.log`, `host-feel-baseline.log`, `host-feel-final-moving.log`, `host-feel-opposed.log`). `git diff --check` passed. Independent Sol 6 High final review: **PASS, no blocking finding**. DeepSeek MAX QA was unavailable and is not claimed.

The smoke probe directly moves test targets, so its zero-gap log validates server acquisition but does not exercise the normal player's camera-based target after grant. The two-human feel trial, a focused cube/scalpel runtime check, and subjective acceptance remain. The user has a `PLAYTEST.txt` beside the build. No commit or push.

## Objective

The initial FishNet server-authoritative implementation already allows up to four independent holders and passed localhost 1→2→1→0 plus disconnect smoke. User now wants the joint handling to feel closer to R.E.P.O. and **Pummel Party** (the corrected title). The objective is a **testable feel pass**, not an attempt to reproduce proprietary code or claim identical physics. R.E.P.O. is the direct reference for careful group transport of physics objects; Pummel Party is a broader party-game reference for immediate and readable interaction, not evidence of any specific shared-grab algorithm.

## Agent plan

TASK SUMMARY: fix avoidable snap/lag when two players lift, steer and carry one heavy prop; keep a small scalpel responsive.

LINE COUNT: one Sol 6 Medium implementation line after the current scalpel Unity prefab integration completes.

LINE A OWNS: `Assets/OnlyVolunteers/Network/Scripts/NetworkGrabber.cs`, `NetworkPhysicsBody.cs`, narrowly scoped `GrabPhysicsSolver.cs` changes if required, dedicated table/scalpel grab profiles and focused smoke/measurement tooling. Coordinate profile asset ownership with the preceding scalpel integration line; no concurrent edits of the same files.

ACCEPTANCE: second grip attaches at its current hit distance without a sudden pull; two aligned moving targets drag a 50 kg gurney with materially less measured steady-state lag than the present solver; opposite inputs balance instead of launching; each grip retains independent force; packet reordering, timeout, release and disconnect cannot restore stale targets or remove a partner's hold. Cubes retain accepted solo feel. Unity isolated build + host/client smoke pass, followed by independent Sol 6 High review and later two-human user trial.

SHARED DO-NOT-TOUCH: player KCC and movement, table caster rig geometry, existing human-made power plan/HDR, unrelated dirty files, third-party Packages, commits/pushes. Main Editor has preexisting PackageCache CS0619, so keep `Packages/manifest.json` untouched and use `C:/Dev/CoopTrialValidation` for Unity compilation/build.

INTEGRATION PLAN: use the already finished scene/build with gurney and scalpel. Compare objective logs before and after; retain the server as sole Rigidbody authority. Show local speculative grab feedback only if needed after physical behavior works, and avoid adding a second local rigidbody simulation. No DeepSeek MAX is callable here; log unavailable instead of claiming it passed. Separate Sol 6 High final review is required.

## Architecture finding and initial tuning

The current target initializes at a fixed 2.25 m in `NetworkGrabber` even if a second player grabbed closer. The solver damps the **absolute** point velocity. With the 50 kg cart, `k=220 N/m` and damping ratio 1, damping is about `210 N·s/m`; steady movement at 2 m/s implies roughly 1.9 m positional lag before other effects. Existing smoke used static targets and did not reveal this.

Proposed minimal pass: preserve actual hit distance and initially use the hit point; reject out-of-order unreliable updates within a hold using a monotonically increasing sequence. Validate all holders before calculating effective `N`; apply each independent spring at its own contact point with damping against a bounded, filtered target velocity: `F_i = clamp(k*error + 2*zeta*sqrt(k*m/N)*(targetVelocity - pointVelocity), perHolderMaxForce)`. Limit target velocity, stop extrapolating when packets pause and keep the existing 0.8 s target timeout. Try a 50 ms filter. The initial table profile trial used k≈450 N/m and 350 N per holder; measured lag remained high, so the final candidate uses k=900 N/m and 450 N per holder, with 6 m/s linear and 3 rad/s angular caps. These are candidate settings for user feel testing, not accepted final balance. At 50 kg one player's cap remains below weight (~490 N), whereas two have a combined ceiling of 900 N. Leave the cube's old solo profile as a baseline. Scalpel has its own lighter profile from its prefab line.

Source basis for the physics design: [Unity AddForceAtPosition](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Rigidbody.AddForceAtPosition.html) (force at a contact point also creates torque), [Unity GetPointVelocity](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Rigidbody.GetPointVelocity.html) (includes rotational motion at that point), [Unity configurable joint drive](https://docs.unity.com/en-us/engine/6000.0/manual/physics-section/physics-overview/joints-section/create-configurable-joint/configurable-joints-driving-forces) (spring and relative velocity damping). [R.E.P.O.'s developer store page](https://store.steampowered.com/app/3241660/REPO/) verifies team transport of fully physics-based heavy and fragile objects; it does **not** specify their internal code or physics constants. [Pummel Party's developer store page](https://store.steampowered.com/app/880940/Pummel_Party/) establishes the 4–8 player party-game context but publishes no shared-grab implementation details.
