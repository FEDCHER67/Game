# G18 / v19 pilot baseline

Step A completed on 13 October 2026 in `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v17_Play.unity`. Geometry measurements use the frozen v18 plan, as requested; scene measurements use the supplied v17 Play scene and 46 BEFORE captures. These are different revisions and are identified explicitly below.

## Reproducible evidence

- `Working/Reviews/Map_v19_Pilots/routes_before_g18_v03.json` and `.txt`: authoritative full 15-route Play run, `V19PilotTools.StartRoutes("Assets/OnlyVolunteers/Scenes/Map/Map_Look_v17_Play.unity", "before_g18_v03")`.
- `Working/Reviews/Map_v19_Pilots/measure_baseline_g18_v01.py`: read-only v18 measurements. Run from the repository root with `python -B Working/Reviews/Map_v19_Pilots/measure_baseline_g18_v01.py`. Outputs are exclusive-create; existing evidence is preserved.
- `baseline_dimensions_g18_v01.json` and `baseline_{buildings,plots,gaps,roads}_g18_v01.csv` in that directory: complete inventory, dimensions, pair identities, route geometry and source findings.
- `review_poses_v19.json`, `routes_v19.json`, `before_*.png`, `contact_before_{h,r,k,t}.jpg`: supplied camera and route definitions and unchanged visual baseline.
- `baseline_integrity_g18_v01.json`: initial SHA-256 manifest of 185 protected/source files. The v18 source plan SHA-256 is `6f7414e0698a7f0c28d0ac1bf9a5ea430bfe7255b54036470804e9d547729d6a`.

The helper now waits for EnteredPlayMode, a normal frame and initialized KCC before stepping. It rejects reused output labels and cancels a run if its scene changes. The v03 run returned zero Console errors. Unity emitted native temporary-allocation lifetime warnings during stepping; these are retained as a limitation, not suppressed. Neither run-in-background setting was changed.

Earlier evidence remains available but is invalid for comparison: v01 stepped before KCC/vehicle audio initialization and all walking distances were zero; v02 was interrupted by a human invoking a legacy v18 build menu. The lead restored that accidental build. Before v03, v17 was opened without saving the other scene, assets were refreshed, and git showed no changes under `Assets/OnlyVolunteers/Map/Look`, `Assets/OnlyVolunteers/Scenes/Map` or `ProjectSettings`.

## Route measurements

Stock empty scene van: mass 1800 kg, motor 1250 Nm, maximum 105 km/h, brake 4200, steering 34/11 degrees, anti-roll 9000, upgrades E0/B0/H0. The scripted driver targets 45 km/h. Crowd and police roots are disabled only during the repeatable run. Walking uses the actual KCC with 4.7025 m/s stable movement speed.

| Route | Result | Time s | Reference line m | Travel m | Maximum deviation m | Failure |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| v01 road B02 to B03 | ARRIVED | 59.7 | 526.9 | 510.8 | 1.9 | — |
| v02 road bridge to B03 | ARRIVED | 31.0 | 248.8 | 239.7 | 1.9 | — |
| v03 cut bridge to B03 | FAILED | 10.3 | 166.4 | 16.4 | 0.4 | Stuck near (441,572); probe reports terrain, cause not independently isolated |
| v04 road B03 to bridge | ARRIVED | 29.6 | 248.8 | 239.8 | 1.9 | — |
| v05 cut B03 to bridge | FAILED | 12.3 | 166.4 | 32.9 | 0.3 | Stuck near (557,556); probe reports terrain, cause not independently isolated |
| v06 road B02 to bridge | ARRIVED | 31.0 | 264.1 | 253.2 | 1.9 | — |
| v07 cut B02 to bridge | ARRIVED | 25.7 | 259.5 | 254.6 | 1.2 | Cut is 5.3 s / 17.1% faster than v06 |
| v08 Rough drive | ARRIVED | 46.3 | 410.5 | 396.6 | 1.9 | — |
| v09 Hamlet loop | ARRIVED | 24.3 | 184.4 | 177.5 | 1.7 | — |
| v10 Hamlet south | ARRIVED | 13.4 | 120.2 | 116.1 | 0.2 | — |
| w01 walking cut | ARRIVED | 27.4 | 129.4 | 128.3 | 0.0 | — |
| w02 Hamlet meadow | FAILED | 6.2 | 56.0 | 10.2 | 0.0 | B_02_house_18/Collider near (300,499.2) |
| w03 B02 door | ARRIVED | 3.7 | 18.2 | 17.1 | 0.0 | — |
| w04 B03 yard | FAILED | 4.4 | 19.8 | 6.8 | 0.0 | B_04_west_base_house/Collider near (589.8,557.6); expected pass |
| w05 road to Rough north | FAILED | 8.7 | 35.7 | 13.2 | 1.7 | B_04_v17_garages_003/Collider near (554.3,640.5) |

All seven required road routes arrive. No route tips: the greatest measured roll is 3.4 degrees and pitch 9.3 degrees. The driver follows a fixed polyline and does not replan around obstacles, so detour attempts are NOT RUN. Deviation is reported instead. Shorter measured travel than reference length reflects corner cutting and arrival tolerance, not a negative detour. Failed-route times are time to failure, never successful travel times.

The chassis probe reports slightly negative clearance on every road (minimum -0.12 m). Its inferred bottom is -0.08 m relative to the van root and has not been calibrated to wheel suspension/contact geometry. This flag alone does not establish persistent grounding; actual driving arrived with no prolonged stop on every road. Physical grounding acceptance remains open.

## Dimensions and spacing in v18

Neighbour pairs are the union of each object's two nearest neighbours by footprint-edge distance. Unique unordered pairs are frozen now for like-for-like after measurements. Houses are the 16 whole-plot units in v18's Hamlet shift metadata; blocks are 22 panel/base blocks, excluding the synthetic blind-alley closure. The full pilot-labelled inventory contains 174 building records, including common-land records outside the pilot bounds; these are not a licence to move common-land buildings.

| Measure | Hamlet | Rough District |
| --- | ---: | ---: |
| House / block neighbour pairs | 18 | 28 |
| Mean edge gap m | 36.255 | 7.432 |
| Maximum edge gap m | 76.845 | 26.824 |
| District area m² | 54,604.680 | 39,131.520 |
| Building union clipped to district m² | 2,820.153 | 11,695.742 |
| Built-up share | 5.165% | 29.888% |
| Largest building-free circle diameter m | 85.696 | 41.302 |
| Circle centre x,z | 175.476,416.478 | 673.714,595.949 |

Hamlet plot-edge gaps: 20 pairs, mean 13.848 m, maximum 47.647 m. The largest house gap is between `02_B05` and `02_v18_plot_02_house`; the largest block gap is between `04_west_base_house` and `04_west_middle`.

The 16 houses have side lengths from 6.144 to 9.594 m and height 2.8 m. Plot areas range from 353.061 to 1459.600 m²; B02's separate yard is 1494.200 m². The base building is 26.4 × 15.8 × 2.8 m; the church is 20.6 × 18.4 × 6.4 m. Rough block envelopes range from a 6.6 m short dimension to a 45.4 m long dimension, with 14 m height. See the CSVs for every footprint, plot and road.

The building-free circle subtracts only building footprints from the district polygon and uses Shapely's maximum inscribed circle with 0.05 m tolerance. Roads, gardens, water and vegetation are not subtracted. It measures building spacing, not meaningless lawn or visual acceptance. The inherited v18 report's empty-lawn diameters (18.794 m Hamlet, 18.970 m Rough) use a different obstacle definition and have not been remeasured here. Its gap pairs and footprint-area method also differ; values must not be mixed.

Twelve Hamlet `functional_sites` duplicate polygons are stale relative to their authoritative `structures` records in v18. The v19 generator must synchronize these pilot duplicates when moving whole units.

## Built v17 road grades and baseline issues

`V19PilotTools.RoadGrades("v17", "hamlet_bypass", "hamlet_rough_e", "04_drive", "DECK_bridge_north")` measures the built sampler surface. Maximum grade over 6 m: bypass 0.0%, east link 15.7%, Rough drive 0.1%, bridge 0.0%. East link's 95th percentile 2 m grade is 15.2%, cross slope 4.8%. This exceeds 8% in the supplied v17 scene even though the later v18 data report passes its own terrain model. v19 needs a fresh built-scene check.

Open baseline defects: broad Hamlet meadows and long road views in supplied captures; B02 shortcut faster than road; blocked B03 walking access; two other walking probes blocked; east road grade above 8%; uncalibrated chassis probe. Performance is NOT RUN by the brief. Baseline collection is PASS; these are measured starting conditions, not acceptance of the existing layout.
