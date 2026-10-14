# G24 integration handoff

Completed 2026-10-14. Follow `docs/reports/GRASS_INSTANCER_v02.md`, not the earlier staging README's scene/review procedure.

Final scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i02_grass.unity`.
Final dataset: `Assets/OnlyVolunteers/Map/Grass/Baked_v04/GrassData_v04.asset`.
Review: `Working/Reviews/Grass/grass_v01.jpg`.

The renderer was added directly to i01 without a map rebuild. Staging source matches imported code. Diagnostic bakes v01–v03 remain preserved; the scene references v04 only. Initial sea-triangle exclusion was corrected to preserve dry land under the sea mesh. Physical paved meshes remain authoritative even where the plan labels overlapping parks.

GPU culling, full placement audit, live frame-time comparison, ordinary Play, walking/van routes, shader/SRP checks and protected-file integrity passed. See the report for measured values and limits.

Current protocol: release Unity and stop. Do not run the review bridge or acquire again until the lead gives another turn.
