# Current state — 2026-10-01

3D first-person co-op prototype in Unity 6000.5.11f1 / URP / FishNet + Tugboat. PRODUCT.md now contains the structured working specification; the detailed canon has a navigation note and retains its substantive sections.

## What remains

- KCC movement with sprint, crouch, air control, bunnyhop and long jump. Planar movement speeds reduced by 5% in TASK-000001; subjective feel acceptance pending.
- Shared force solver/profile, local object grabbing, server-owned network physics.
- The newer cooperative prop code from local commit 892d7ca was consolidated from FEDYA_PROPS into the main project. It supports up to FOUR holders on generic props, request/hold IDs, target sequence checks and disconnect/timeout release. This is not the canon's finished THREE-holder NPC capture mechanic.
- TASK-000013 restores the accepted solo table-follow changes from 54aacff on this baseline: the grabbed table point follows horizontal camera heading at fixed height, four wheel contacts use a low-friction material, and the solo profile uses 850 N / 10 m/s limits. The existing multi-holder profile remains 450 N / 6 m/s. TASK-000001 movement constants remain in place.
- Three useful test scenes: ControllerTest (movement), PhysicsInteractionTest (local grabbing), NetworkTest (co-op, cubes, table and scalpel). NetworkTest is the only build scene.
- Player_01 art prototype under Assets/OnlyVolunteers/Art; seven prop prototypes under ArtSource/Props: brain v2, kidney, liver, lungs, cash, scalpel and table. Only table/scalpel are integrated as network props.
- Additional heart and syringe authoring sources were restored by Fedya's explicit backup/restore request; neither was imported into Unity. Heart provenance restrictions remain in its PROVENANCE.md. Existing seven prop exports/previews and used mesh/material data match the saved source versions; unused scalpel materials removed by the cleanup remain removed.

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

Current NPC deliverables: ArtSource/Characters/NPC_BASE_01/NPC_BASE_01_v06.blend and matching _v06.fbx, with Previews/v06 and validation_v06.json (TASK-000012, 2026-10-02). This is a local repair of saved v05, retaining the design, proportions, lower body, hands and 65-bone Mixamo hierarchy. The whole sausage head, ears, nose, face and collar rim now bind rigidly to Spine2. Human Neck/Head tracks no longer bend this volume or pull its clothing apart; independent head turns relative to the chest are intentionally absent. The circular collar is tightened and shoulder-top weights are redistributed for raised arms. The mouth uses paired polygon strips in front of the skin instead of an intersecting concave ngon; all four facial keys remain. 16,458 triangles, six meshes, seven materials and both Run Look Back variants (68 frames / 30 fps) remain. All 68 frames and six diagnostic poses passed head/face/collar rigidity and shirt-crossing checks; animated FBX round-trip passed. No additional Mixamo clips were available; diagnostic poses do not claim universal clip acceptance. New takes must retain the existing skinning; rig_npc.py has --rigid-sausage to apply the same binding when using the older generator. v05 is the previous rigged revision and v03 the unrigged historical source. Every new deliverable must use a distinct numbered filename. No Unity integration, Avatar/Animator or ragdoll yet.

The user chose Blender prop creation as Fedya's separate workstream. See WORK_SYNC.md for task handoffs and docs/TEAM_WORKFLOW.md for sequential work on main and manual publication by Vadim. NPC_BASE_01 has clean clothing, straight legs, a circular constant-width head/neck and full hands with three rounded fingers plus a thumb. Four geometric facial shape keys remain alongside the new skeleton. TASK-000009 explicitly ends the earlier rigging deferral and establishes Mixamo as the source of ready-made animations. Visual acceptance remains with Vadim. Future visual variants share the body and change clothing/headwear; body variations remain deferred. Broad visual direction is moderate low-poly, clean rounded forms, simple materials, soft inexpensive daylight and a compact readable city. Exact architecture, palette, character design and rendering budgets remain open; see PRODUCT.md and canon section 149. Three rough references are preserved in ArtSource/References. Unity productName is VOLUNTEERS ONLY. Movement tuning differs from the tested consolidated baseline as recorded in TASK-000001; serialized whitespace was normalized for the newly tracked assets.
