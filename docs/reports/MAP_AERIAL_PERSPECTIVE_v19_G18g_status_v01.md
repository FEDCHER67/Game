# G18g — aerial perspective, dependency handoff

2026-10-14. **BLOCKED / IMPLEMENTATION NOT STARTED.** G18g follows completion of the current G18 Hamlet fix round. That round is not complete because Unity cannot get past its startup warning after the safe standard-user restart. See `docs/reports/MAP_PILOT_v19_PROGRESS_review_v02.md` for the exact state, completed route evidence and staged orchard correction.

Brief: `C:/Users/Zeyo-ne/.ai-bridge/app_briefs/G18g_aerial_perspective.md`.

No G18g shader, runtime component, material, scene or review image was generated. `aerial_perspective_v01.jpg` does not yet exist; no old palette sheet is represented as aerial-perspective evidence. No compile, render or Play check for G18g has run.

After G18 is validated, resume with a new numbered v19-only implementation:

1. Capture the three requested long-view baselines on the accepted G18 scene: Hamlet hill toward Downtown; north bridge along the river; Rough edge looking out.
2. Add one cleanly exposed district horizon colour, blended with the same 40–80 m weights, shared by sky and haze and available for G22's later day/night control.
3. Preserve the approved palette and Rough v05 / Forest v03 atmosphere. Clear districts keep the first 25–35 m clear and gameplay objects within 40 m crisp; approximately 50% haze at 150–200 m, nearly complete at 350–450 m. Port targets approximately 100 m for 50% haze. Modulate low ground gently; preserve distant-hill dissolution.
4. Implement a camera/scene-scoped URP path without ProjectSettings writes or global pipeline asset mutation. The existing V05 temporary pipeline override must not be reused as-is under the updated protocol. Inspect the installed URP render-graph APIs and validate the actual renderer.
5. Check terrain, buildings, trees, grass, props, water, custom transparencies and particles. A depth fog pass affecting only opaque surfaces is insufficient for this brief.
6. Render the usual poses and the three matched long views; assemble the requested `Working/Reviews/Map_v19_Pilots/aerial_perspective_v01.jpg`. Inspect actual near contrast, distant lightening/desaturation, horizon matching, map-edge concealment and border blending.
7. Produce the verified report, stop Play, save the scene, release with the helper, and run the bridge with `-Task G18g`. Maximum two fix rounds.

G18's cancelled v17/v18 comparisons remain cancelled. G18g's three before/after aerial views are a separate explicit requirement and remain required. Trees stay in their current approved G18 form; G23 owns the separate proportions/wind work.

No ProjectSettings, runInBackground, global URP asset, source asset or window geometry was changed for G18g. No sound download or commit occurred. This report is submitted to the bridge only to document the blocked dependency; it is not a completion claim.
