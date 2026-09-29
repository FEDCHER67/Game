# Two-player prop trial in NetworkTest

## Goal and status (2026-09-29)

User explicitly approved the scalpel **concept** and table **caster-motion video**, and requested a two-person trial in the existing `Assets/OnlyVolunteers/Scenes/NetworkTest.unity` movement/cube physics scene. Improve simultaneous player interaction with one physics body first. Add finished scalpel and gurney there for the user to test with a friend when home. Return to the prop queue after the trial attempt.

The table's Blender/FBX and caster kinematics are approved by the user. `NetworkTableAstra.prefab` is registered and referenced by `NetworkTest`. An isolated Unity 6000.5.11f1 build passed a two-process localhost co-grab smoke test: holder counts 1 → 2 → 1 → 0, including a client-disconnect release. Independent Sol 6 High review passed this scope; a real two-human table/caster trial remains. The four scalpel Tripo PNGs were generated in ordinary FEDCHER ChatGPT High, saved with hashes in `Source/TripoViews/Rev01/VIEW_MANIFEST.md`, and reattached to that ordinary chat. The user personally approved the exact set.

The tier-2 scalpel is now finished in Blender (1,508 faces, 0.17 m, two matte meshes) and integrated into `NetworkTest` as an independent 0.1 kg network prop with its own light grab profile. Isolated Unity import/build passed with zero errors; `C:/Dev/GameBuilds/ScalpelAstraTrial/VolunteersOnlyScalpelTrial.exe` launched as host and spawned 8 cubes, the table and the scalpel. Logs: `C:/Dev/CoopTrialValidation/build-scalpel-player.log`, `host-scalpel-smoke.log`. Visual game feel and two-human testing remain. A separate measured co-grab feel pass is in progress under `tasks/COOP-GRAB-FEEL.md`.

**Tripo credit gate:** Before clicking Create on every future generation, visually verify that the button says exactly **100 credits**. A four-file batch was incorrectly interpreted by Tripo as four separate models and cost **400 credits** (balance 1495 → 1095) on 2026-09-29. This was the orchestrator's error. Never repeat it. No further Tripo spend for this scalpel. All four input PNGs were cleared from the Tripo form after generation and the empty input was visually verified. Use the already generated first result, whose source FBX is in `research/SCALPEL-ASTRA-001/Working/Tripo/`.

## Agent plan

TASK SUMMARY: server-authoritative cooperative grab and prop trial.

LINE COUNT: 1 gameplay implementation line. A second implementation line is unnecessary because grab and scene integration are dependent.

LINE A: Sol 6 Medium owns `Assets/OnlyVolunteers/Network/Scripts/NetworkPhysicsBody.cs` and `NetworkGrabber.cs`, plus narrowly scoped validation files. Acceptance: two players independently hold the same body; each contributes force and torque at their own point; release/disconnect/timeout of one retains the other; stale RPCs cannot affect a new grip; no client authority transfer; solo behavior and accepted player movement preserved.

SHARED DO-NOT-TOUCH: accepted KCC movement and player prefab, unrelated dirty files, third-party Packages, power plans/HDR, art sources outside this prop task. No commit or push.

INTEGRATION PLAN: after line QA, orchestrator adds network gurney/scalpel prefabs and spawn entries to the existing NetworkSession allowlist and NetworkTest scene. Gurney uses a yaw-only Rigidbody on flat test floor so its planar caster rig remains valid. Scalpel gets its own modest mass/physics profile. Check real localhost host/client processes, then user runs real two-human feel test. DeepSeek MAX QA is unavailable in this environment; do not label it PASS. Request independent Sol 6 High review of final scope and report limitations.

## Astra High architecture assessment

User authorized Astra High for this unusually coupled FishNet + physics problem. Read-only review found FishNet 4.7.3 server-authoritative bodies, an exclusive `holder` gate in `NetworkPhysicsBody.TryAcquire`, eight session cube spawns, and server allowlisting in `NetworkSession.IsAllowedBody`. Recommended bounded per-holder records, distinct local grab points/targets, one server fixed-step force aggregation, per-holder collision/timeout cleanup and grab-generation identity on RPCs. Existing table caster disables on tilt beyond roughly 0.81°, so first trial must keep the table upright on flat ground. See architecture agent handoff in the originating Codex thread.

## Next

1. Finish the measured co-grab feel pass on the table, scalpel and cubes, then independent Sol 6 High final review. The baseline two-client moving-table contact error rose past 2 m, so static hold-count smoke alone is insufficient.
2. Rebuild isolated Unity, verify moving host/client behavior with both props, update `Documents/CodexTransfer-2026-09-29/START_HERE.md`, and hand off a playable trial to the user and friend for feel testing. Full game Unity batch mode still fails on unrelated PackageCache CS0619 errors, so keep its manifest untouched and use `C:/Dev/CoopTrialValidation` for import/build validation.
