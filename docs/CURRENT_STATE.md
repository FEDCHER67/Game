# Current state — 2026-09-30

3D first-person co-op prototype in Unity 6000.5.11f1 / URP / FishNet + Tugboat. PRODUCT.md now contains the structured working specification; the detailed canon has a navigation note and retains its substantive sections.

## What remains

- KCC movement with sprint, crouch, air control, bunnyhop and long jump. Planar movement speeds reduced by 5% in TASK-000001; subjective feel acceptance pending.
- Shared force solver/profile, local object grabbing, server-owned network physics.
- The newer cooperative prop code from local commit 892d7ca was consolidated from FEDYA_PROPS into the main project. It supports up to FOUR holders on generic props, request/hold IDs, target sequence checks and disconnect/timeout release. This is not the canon's finished THREE-holder NPC capture mechanic.
- Three useful test scenes: ControllerTest (movement), PhysicsInteractionTest (local grabbing), NetworkTest (co-op, cubes, table and scalpel). NetworkTest is the only build scene.
- Player_01 art prototype under Assets/OnlyVolunteers/Art; seven prop prototypes under ArtSource/Props: brain v2, kidney, liver, lungs, cash, scalpel and table. Only table/scalpel are integrated as network props.

## Assessment

The movement motor and separation of force calculation from networking are worth retaining. NetworkSession currently mixes connection lifecycle, test spawns and debug UI; split those responsibilities when extending the playable slice. Local and network grabs still differ in hold-distance and multi-holder behavior. The table wheel controller assumes an upright planar surface; it is not a general solution for tumbling objects.

Art remains subject to the upcoming style review. Existing asset reports describe historical checks; removed Working paths in those reports are not current dependencies. No NPC resistance, GripAnchor system, van capture loop, living city, laboratory economy or save system exists yet.

## Cleanup

Removed obsolete agent machinery, three temporary worktrees and the duplicate FEDYA_PROPS checkout, old builds, recovery scenes, unused KCC demos, the superseded physics playground, stale tasks/design documents, old art build intermediates and brain v1. No backups created. Active Unity caches are generated working data and remain while the editor is open. Git history remains intact. Publication of the cleaned team baseline is recorded in Git history.

## Next decisions

1. Agree on a small visual target: one adult NPC, a street fragment, one prop and the van.
2. Review the retained movement, grab and network code against explicit acceptance criteria, including two-machine latency and disconnect behavior.
3. Build NPC + VAN FUN TEST: body grab points -> up to three holders -> resistance -> environmental grips -> physical loading -> closed doors.
4. Add the first business loop only after the capture scene is enjoyable in solo and co-op.

## Verification after cleanup

Unity compilation and a Windows development build succeeded with zero errors. Five warnings remain: four obsolete API warnings in development probes and one KCC serialization warning. All three test scenes and six game prefabs loaded without missing scripts.

Two separate localhost build processes connected, simultaneously held and moved NetworkTableAstra, rejected stale target sequence packets and released back to zero holders. This is not two-PC latency or subjective feel acceptance. Four-player/disconnect/reconnect cases were not rerun.

A final optional removal batch was blocked by automatic policy review without a detailed reason. The retained files are the isolated-project table validation runner/report and older cash/scalpel/table handoff/proposal notes. The runner still expects its separate validation project; do not run it in the main Editor. The principal cleanup and consolidation described above completed before that block.

## Shared development baseline

The user chose Blender prop creation as Fedya's separate workstream. See WORK_SYNC.md for task handoffs and docs/TEAM_WORKFLOW.md for sequential work on main and manual publication by Vadim. Character production is deferred; the supplied image is only a rough direction, with simple shapes and strongly expressive, simple faces. Broad visual direction is now established: moderate low-poly, clean rounded forms, simple materials, soft inexpensive daylight and a compact readable city. Exact architecture, palette, character design and rendering budgets remain open; see PRODUCT.md and canon section 149. Three rough references are preserved in ArtSource/References; no scene or model has been approved from them. Unity productName is now VOLUNTEERS ONLY. Movement tuning differs from the tested consolidated baseline as recorded in TASK-000001; serialized whitespace was normalized for the newly tracked assets.
