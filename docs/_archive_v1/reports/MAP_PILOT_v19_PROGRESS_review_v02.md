# G18 — Hamlet fix round 1, current handoff

2026-10-14. **BLOCKED, not complete.** This numbered report supersedes the completion/status claims in `MAP_PILOT_v19_PROGRESS.md` for the current round. That older report and its images describe the previous build and remain historical evidence.

## Current editor blocker

After the limit interruption, no Unity instance was running or connected to unity-mcp. Reopening the installed Unity 6000.5.11f1 for `C:/Dev/Game` reached **Administrator Privileges Detected**. Selecting **Restart as Standard User** relaunched Unity but returned to the same warning. The replacement Unity process is 13880. MCP still has zero editor instances. No scene is loaded through the bridge; Play is not running. No new scene save or build occurred during this continuation.

The warning says that elevated project scripts can modify protected system areas and offers **Restart as Standard User** or **Ignore Warning**. Ignore Warning was not selected. This is the precise remaining external action: open this project in a functioning standard-user Unity editor, or have the human resolve that startup warning. No request for input was sent, following the updated no-questions protocol.

Computer-use guidance followed: `C:/Users/Zeyo-ne/.codex/plugins/cache/openai-bundled/computer-use/26.1007.71326/docs/guidance.md`, "Do not act on security or privacy permission requests." Its confirmation policy also treats third-party warnings as requiring approval. The safe standard-user restart did not resolve the state. No OS or app security setting was changed, and no warning-bypass command-line switch was used.

## Work already built and measured

Current saved Look and Play scenes use source **build_v07**, generated **Map_Look_v19_build009**, **Palette19/Full_v07**, and **Full_v07/Finish_v03/Terrain_finish_v03.asset**. The final Greybox still requires the round-1 rebuild. Police is `police_v19_build_v08.asset`; crowd is `crowd_v19_build_v07.json`; ambience is `Ambience_v19_full_v07.asset`; water is `Water_v19_build_v07.asset`.

`Working/Reviews/Map_v19_Pilots/data_round1_geometry_v02.json` records:

| Current v19 metric | Value |
| --- | ---: |
| Existing buildings moved / additional buildings | 62 / 12 (10 garages, 2 barns) |
| Changed roads | 18 |
| Hamlet house two-nearest footprint-gap mean / maximum | 17.934 / 25.334 m |
| Hamlet largest building-free circle diameter | 40.901 m |
| Hamlet area / building coverage | 31,273.5 m² / 9.715% |
| Household plots | 16, combined 6,028.762 m² |
| Shortened Hamlet loop centreline | 92.056 m |
| Rough block gap mean / maximum | 6.217 / 19.252 m |
| Rough largest building-free circle diameter | 33.287 m |

No changed existing building dimensions, nonpilot building moves, new building overlaps or plot overlaps were found in that audit. An existing 3.112 m² `02_B03` / `02_h_north` overlap remains recorded. The road graph has one component; the pedestrian source subset has five, including old decorative beach footbridges outside the pilots. Crowd planning validation passes: 100 points, 20 routes, 110 connections, one exported component, zero blocked segments or illegal crossings.

The two new Hamlet view hills are at (267,408), height 7.8 m, and (325,417), height 6.5 m. Their earlier positions caused excessive southern-road grade and were corrected. The full final grade/seam audit has not yet been rerun. Do not use `road_grades_round1_v01.txt`, which predates that correction, as final acceptance.

Eighteen hay instances were relocated to clear revised roads, paths and building footprints. Rough k03 now has the laundry/bench/bin group; k09 has five garden beds and a bench. Draft `draft_r1b_k03_walk_pitch.png` and `draft_r1b_k09_walk_north_edge.png` show these changes, but the full final same-pose capture set remains outstanding.

## Completed route run and remaining failure

The run finished before this continuation and is preserved as `routes_round1_g18_v02.json/.txt`, using `routes_v19_round1_v02.json`, in `Working/Reviews/Map_v19_Pilots/`. Actual Unity KCC/van frames were used. **19 of 20 expected outcomes were achieved.**

| Check | Evidence / result | Status |
| --- | --- | --- |
| Seven street routes | All arrive; shortened v09 loop 17.5 s / 137 m; zero frames below two grounded wheels | PASS |
| Three direct van cuts | v03, v05, v07 are blocked by terrain/rocks/trunks/building or fence obstacles as intended | PASS for expected block |
| Four replacement walking routes | w01 31.5 s / 146.5 m; w02 13.6 s / 63.7 m; w04 10.8 s / 50.0 m; w05 7.2 s / 33.2 m | PASS |
| B02 door walk | 3.7 s / 17.1 m | PASS |
| Four supplementary foot passages | Orchard, road berm, Rough west and playground gate all arrive | PASS |
| Orchard van passage | Stops near (234,456), after 106 of 117 m, 41.7 s / 101 m travel | FAIL |
| New orchard candidate | Staged only, see below | NOT RUN |
| Clinic initialization | `clinic_round1_v01.txt`: loop, registry, station, dropoff, runner and inventory all present | PASS for initialization only |
| Final round-1 grades, scene/seam audit, ordinary 600-frame smoke | Requires connected editor | BLOCKED |
| New round-1 review renders and sheets | Requires connected editor | BLOCKED |

The old frozen walking lines w01/w02/w04/w05 are **SUPERSEDED**, not unresolved route failures. Their replacements use physically measured walk clearance. w05 ends at the garage courtyard edge (575,647); its old endpoint lies in the relocated garage. This endpoint change is explicit.

The orchard van stop has no forward obstacle reported by the simplified probe, so contact with the nearby relocated hay is a hypothesis pending side/rear collision inspection. Hay `02_v18_hay_18_2` now sits at (232.878,454.0441), close to the failed turn. No source obstacle was removed merely to turn the test green.

## Staged continuation

`prepare_orchard_resume_v01.py` generated `routes_v19_round1_v03_candidate.json` and `orchard_resume_candidate_v01.json` outside Assets. Only the orchard van tail changes: (212,456) → (218,461) → (230,464) → (239,464) → (244,457) → (241.6344,448.8869). It goes farther north before turning around the relocated hay. Its nearest 2D building footprint is 14.55 m away. This checks buildings only; fences, hay bounds, terrain and the van's swept body still need Unity. The candidate explicitly says **NOT RUN**, and is not accepted as a completed fix.

Resume precisely:

1. Acquire with `powershell -NoProfile -File C:/Users/Zeyo-ne/.ai-bridge/unity_lock.ps1 -Cmd acquire -Id G18` after Unity starts normally; open the saved `Map_Look_v19_Play.unity`.
2. Run `V19PilotTools.StartRoutes("Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play.unity", "round1_orchard_g18_v03", "p_van_hamlet_orchard_passage", "routes_v19_round1_v03_candidate.json")`. If it stops again, inspect actual side/rear contacts; do not mark a 2D clearance check as a physical pass.
3. Finish current terrain/grade/seam/scene checks, ordinary-scene smoke, and the final Greybox revision. Preserve approved palette, happykeys and cancelled G23 tree scope.
4. Capture all 46 usual poses with `after_r1_`, atmosphere with `palette_r1_v05_`, and nature with `nature_r1_`. Run `make_v19_review_sheets_v02.py`; inspect resulting images. The composer and `final_integrity_g18_round1_v01.py` are prepared but were not run without their required final renders.
5. Publish a new complete numbered report; release the lock; rerun the G18 bridge. This is still fix round 1, not an accepted completion.
6. Then implement G18g, including its explicitly requested three aerial before/after views. G18 itself remains v19-only; do not reinstate cancelled v17/v18 comparisons even if the old bridge brief asks for them.

## Preservation and limits

No Assets, scenes, source models, ProjectSettings or URP assets were written during this continuation. `git diff --stat -- ProjectSettings` was empty. Neither run-in-background setting was touched. No windows were minimised, moved or resized. The only UI action was the Unity warning's standard-user restart. No commit, staging, push, deletion, download or WORK_SYNC edit occurred.

The existing V05 fog component uses a temporary pipeline override and has an old settings-restoration path. This predates the updated prohibition on ProjectSettings/global pipeline changes. Do not invoke that path blindly during resumption. G18g must use a scene/camera-scoped pass without altering the global URP asset or settings. Its current behavior is a technical item to resolve, not a new permission to modify settings.

Earlier natural-collision evidence remains in the round-0 report. Full carried-NPC entrance tests, every architectural traversal, listening acceptance and the complete catch/load/operate/save loop remain NOT RUN. Final visual approval remains Fedya's.

The lock is released through the helper before the review bridge. G18 is not marked done because further Unity work is required. The saved build remains on disk; the editor is stopped at its startup dialog. The report is submitted to the bridge as a blocked handoff, not a finished task.
