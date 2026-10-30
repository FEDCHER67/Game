# Map W85 vs Vadim's wishes — audit (21.10.2026)

Checked against `WISHES.md` (same folder). Build checked: pipeline `Tools/MapV85/` (s03_terrain.py = relief, s02_network.py = roads), data
`Assets/OnlyVolunteers/Map/W85Build/Data/v01/`, builder `Assets/OnlyVolunteers/Map/W85Build/Editor/`, reports `docs/reports/MAP_W85_*.md`,
`docs/reports/FEDYA_TO_VADIM_W85_2026-10-21.md`, `Working/Reviews/Map_W85_build/PROGRESS.md`.
Measurements were taken on `Tools/MapV85/out_v01/height_1m.npy` (the 1 m grid that s03 resamples into `Heightmap_v85_2049_r16.bytes`; spot check at base 2: npy 4.311 m, RAW 4.310 m), plus `roads_v85.json` road heights and the district JSONs. Slopes are on the 1 m grid. No Unity, nothing edited.

Verdicts: **OK** / **DEVIATION** / **MISSING** / **UNKNOWN** (needs an in-game look). Counts are at the end.

## 0. Root cause of the "cake cliff" in Fedya's screenshot (Hamlet, near base 2)

The wall is not a pad edge or a road cut. It comes from a **hard rectangular mask in the river-gorge step** of `s03_terrain.py` (lines 266–273):

```python
near = sm(1 - (d_riv - 9.0) / 150.0) ** 1.4          # "wide gentle rise towards the gorge rims"
riv_zone = (ys > 80) & (ys < 770) & (xs > 430) & (xs < 700) & (padw < 0.5)   # boolean rectangle + binary pad mask
h = np.where(land & ~mt & riv_zone, np.maximum(h, h * (1 - near) + bank * near), h)
```

`bank = bed_line + depth` is 7–24 m. Within 150 m of the river the ground is raised towards that height, but **only inside the rectangle
x 430–700, y 80–770**. The raise stops dead at the rectangle edge, which leaves a 1-pixel vertical step:

| Rectangle edge | Length with a step > 2 m | Max step | Where |
|---|---|---|---|
| x = 430 (west) | 388 m (y 289–768) | **10.3 m** (mean 4.8) | **east edge of the Hamlet**, parallel to the asphalt `hamlet_bypass` |
| y = 770 (north) | 137 m (x 464–601) | 19.1 m | foot of the NW ridge |
| x = 700 (east) | 113 m (y 95–320) | 5.5 m | Quiet Valley / Downtown SW |
| y = 80 (south) | 85 m (x 475–693) | 7.5 m | Quiet Valley coast |

Profile at y = 500: x 428 → 4.6 m, x 430 → **9.7 m**, x 460 → 11.2 m (bypass), river bed x 480 → 2.3 m. The asphalt `hamlet_bypass` (x ≈ 461–465) runs along the raised shelf at 8–13 m. The Hamlet's own dirt streets `02-R-main` and `02-R-north` (village_main, 5.4 m) run east at ~4.6–5 m and climb a **4.4 m / 5.2 m step within one metre** to reach the bypass. Dirt roads are splat-only (`W85Builder.cs` l.548), so nothing hides it. Shed `02-S-v18_shed_02_ground_09_4` stands across the wall (4.7–8.4 m under its footprint), and the bus stop `02-U-STOP` sits on the upper shelf. The face is textured by `s07_splat.py` l.112 (rock where slope > 36°) with planar terrain UVs, so the texture stretches.

The same binary mask (`padw < 0.5`) also turns the **Quiet Valley lab yard (base 5) into a pit**. The pad is flat at 3.85 m, while the ground just outside its edges is raised to 7–8 m. That gives vertical 3–4 m steps on three sides (y = 220.8, y = 283.6, x = 630.4).

**Wishes broken:** R15 ("без резких стен и ступеней"), R17 (no "cake"), R7 (soft ravines), R14 (the gorge should be cut *into* the ground, not into a 150 m-wide raised terrace), D2d (Hamlet without a seam), R19 (buildings fitted to the ground), J1 (street joins without a height step), N17.

**Other code paths that make steep "cake" faces (smaller):**
- *Road corridor* (s03 l.348–374). Bank reach = `dz / slope_k` with `slope_k` 0.45 for normal roads (average 1:2.2 ≈ 24°; the smoothstep peak is ×1.5 ≈ 34°), 0.30 for the serpentine and 0.9 for the Elite stone road. Reach is capped at 70 m, and `dz` comes from a Gaussian-smoothed difference, so it is underestimated at local peaks. The corridor is applied *after* pads and terraces, so it cuts them.
- *Per-road profiles* (s03 l.315–336). Each road is profiled on its own from `sm6` with an 82 m moving average and a grade clamp, and join heights are not shared. Height steps at joins are listed under J1.
- *Pads before the big relief*. Construction rings are 26 m wide; Downtown and Rough pads blend over 40 m into a hill B that was already placed. Edge faces are listed under R17.

## 1. Relief

| # | Verdict | Evidence |
|---|---|---|
| R1 harmoniously uneven | **DEVIATION** | The composition exists (13 designed features with roles, `terrain_v85.json` `relief`), but it is broken by hard steps: land slope p99 = **61.1°** outside mountains and rocks (`terrain_v85.json` `land_slope_deg_p99`); ~720 m of 1-pixel walls (section 0). |
| R2 more unevenness | OK (data) / UNKNOWN (look) | Micro + swell on all land (s03 l.98–100). But 204 closed depressions are filled flat (R8). |
| R3 like v19 | UNKNOWN | No side-by-side comparison with v19 was made. |
| R4 every hill has a role | OK | `RELIEF` list s03 l.60–74 (separators H1/H2/H3/H4, viewpoint H2/H10, meadow bumps H5–H7, gullies G11–G13) + `relief_scheme_v85.png`. |
| R5 micro 0.3–1.5 m | OK | `0.55·fbm(9 m) + 0.75·fbm(23 m)` ≈ ±1.3 m, swell ±1.6 m at 120 m (s03 l.98–100). |
| R6 separators 3–8 (10–12) m | OK | Hills 2.5–9 m (RELIEF). |
| R7 soft ravines 2–6 m, grassy bottom | **DEVIATION** | Only 3 gullies (−2.5…−3.5 m). The river channel is carved over 6 m (`chan`, l.272): 8–11 m drops at 70–83° (bank slope 83° next to `hamlet_bypass` at (492, 558), 73° at `hamlet_main_link`). No streams. |
| R8 pits 1–3 m allowed (only traps banned) | **DEVIATION** | Priority flood fills **every** closed land depression deeper than 0.6 m (l.391–400, `traps_filled` 204), whether or not the van could drive out. It also removes the Hamlet dip and gully ends. |
| R9 hill B 50 m barrier, tunnel | OK | Peak 50.6 m; crest heights 50 / 50 / 30 / 22 (pass) / 36 / 41 m; tunnel cover 14.9 m. |
| R10 VIEW B ~+46 m | **DEVIATION** | Hill B is lowered by 62 % around the serpentine (`pass_k`, l.152–153). The serpentine's highest point is **22.9 m** (roads_v85 heights; `view_B_road` 21.4 m). Vadim asked for lower *walls*, not a lower hill. This was only asked afterwards as FOR_VADIM Q17. |
| R11 Elite 44 m, uneven plateau, villa terraces | **DEVIATION** | Peak 44.9 m and terraces 40 / 41.5 / 42.5 / 44 m are right. But the stone-road corridor (`slope_k` 0.9, reach up to 70 m) applied *after* the terraces drags the plateau inside the fence down to 21.5 m. Ground under the villas: **V03 range 15.4 m (28.2–41.5)**, V04 13.0 m, V01 7.4 m, guard booth 4.1 m. The villas will hang over the cut. |
| R12 NW ridge 92–95 → 56 m | OK | `nw_ridge` 95.0; `top = 92 − 36·sm((x−470)/102)` (l.116). Foothill pines/screes: UNKNOWN. |
| R13 right ridge ~30 m | OK | `right_ridge` 31.0. |
| R14 river gorge 6–13 m, land bridges, waterfall | **DEVIATION** | The depth formula 6–13 m and the land bridges are right. But the gorge is made by *raising* a 150 m shoulder band inside a hard rectangle (section 0). The channel walls are smooth vertical earth with stretched rock splat and no rock meshes. |
| R15 natural forms, no walls/steps | **DEVIATION** | Section 0; 1-pixel steps up to 10.3 m (Hamlet) and 19.1 m (NW). |
| R16 Rough = Downtown, Construction +8 | OK | Pads 5.0 / 5.0; Construction pad 12.72 m = base 4.72 + 8. |
| R17 soft pad edges, no cake | **DEVIATION** | QV lab pit (section 0). Construction ring 26 m → banks p95 29°, max 33° all around (a plateau look). Downtown edge under hill B / tunnel portal (x 878–961, y 484–515): >40° over ~730 m², drops 15–17 m. Elite west flank: a straight N–S face x 1306–1315, y 276–355. Port: see J10. |
| R18 yards/plazas level | **DEVIATION** (partly OK) | Rough pad only 72 m² > 15° out of 71,928 m² (OK). Port yard: the road passes at 7.9 → 2.8 m inside a 2.5 m pad. Rough pad: 2.26 m step at the serpentine start (x 939–951, y 674–679). Lab yard: ramps 3.8–6.6 m. |
| R19 nothing floats / buried | **DEVIATION** | Ground range under footprints > 1.5 m: Elite V03 15.4, V04 13.0, V01 7.4, booth 4.1; beach cabana 5.2; Hamlet shed 3.7 (on the wall); Downtown 05-B002 3.6; Construction workshop 2.7; KPP 2.7 m. `W85FloatCheck` covers roofs and porches only, not ground fit. |
| R20 40–100 m nature, no tables | UNKNOWN (+ DEVIATION at the Hamlet) | The river shoulder makes an artificial 150 m-wide terrace with a straight edge along the Hamlet. Elsewhere this needs an in-game look. |
| R21 Rough flat | OK | Flat 5.0 pad (the "slight unevenness for looks" is absent — minor). |
| R22 Hamlet bumps +1.5…+3.8, dip −1.4 | **MISSING** | s03 Hamlet block (l.216–237) only flattens plots and fields. Layout v06 has no `terrain`; v04 had `02-TR-north_fold` +3.8, `central_rise` +2.6, `east_rise` +3.4. `hamlet_v85.json` `pad_note` claims bumps "in 3D only", but nothing builds them. |
| R23 Elite = hill, not a cliff | **DEVIATION** | Superellipse `rho⁴` (l.161) gives a rounded-square hill with straight flanks: flank slope p50 35°, p90 52°, max 87°. |
| R24 Tramduro mounds/rocks | UNKNOWN | `tramduro_v85.json` `pad_note` says helipad +3 / palace +2 / rocks 5–10, but s03 only flattens the yard. The builder lifts zone meshes (`baseH + lift`, W85Builder l.1496), so the mesh may float over flat ground. |
| R25 forest no beach exit | OK | `forest_v85.json` checks `roads_reach_beach: false`; H4 hill 6 m. |
| R26 steppe + invisible wall | OK | `W85Builder.cs` l.987–1010 InvisibleWall; steppe rises (s03 l.298–299). |
| R27 not pressing mountains | UNKNOWN | — |
| R28 VIEW B: no cut, berm 1–1.5 m, 12 %, view | **DEVIATION** (partly OK) | No 15 m cut: OK. Berm 1.25 m both sides (l.376–379): OK, but no stones, and it is suppressed within 25 m of the viewpoint. Grade 12.0 %: OK. Achieved by lowering the hill (R10). 2.26 m height step at the ring join. Bank slope 71° at (952, 665). |
| R29 grades ≤ 8 % (12 / 12.5–15) | OK | `road_grades`: max 8.0; serpentine 12.0; Elite 12.4. |
| R30 gentle cut/fill slopes | **DEVIATION** | `slope_k` 0.45 → ~24° average, ~34° peak by design. Measured max bank slopes: hamlet_main_link 73°, to_quiet_valley 65°, port_road 58°, main_hamlet_downtown 56°, elite_stone_road 84°, cornice 83° (the last is a cliff by design). |
| R31 no van traps | UNKNOWN | Closed depressions are filled. The QV lab pit (exit only via the spur) and the Hamlet step are obstacles, not traps. Needs a drive. |
| R32 off-road slower than road | UNKNOWN | No road vs off-road timing recorded. |
| R33 drive-test every hill | **MISSING** | PROGRESS.md smoke test = "player walks 18 m"; no van runs over the relief. |
| R34 relief scheme to Vadim BEFORE the build | **MISSING** | `relief_scheme_v85.png` is generated by s03 `preview()` but only mentioned to Vadim after the build (MAP_W85_FOR_VADIM.md). There are no 4–6 ground/van shots (only `w85_viewB_pass.png`) and no "yes". |
| R35 picturesque by relief | UNKNOWN | — |
| R36 uneven beach | UNKNOWN | The beach ramp is a smooth formula (l.91–95); no dune relief in s03. |

## 2. Roads and joins

| # | Verdict | Evidence |
|---|---|---|
| J1 no height step at joins | **DEVIATION** | Each road is profiled alone (l.315–336); meshes use their own heights (W85Builder l.549–556). Steps at joins: serpentine_view_b ↔ rough_ring **2.26 m**, rough_ring ↔ rough_to_port 1.39, rough_to_port ↔ port_road 1.31, valley_lab_spur ↔ to_quiet_valley 0.86, hamlet_bypass ↔ hamlet_to_rough 0.65, port_road ↔ bridge 0.53, tunnel_north_approach ↔ ring 0.52 m. Hamlet dirt streets meet the bypass over the 4–5 m wall. |
| J2 right-angle joins | OK (data) | s02 snaps ends to the axis with a ~15 m straight approach (s02 header). Visual: UNKNOWN. |
| J3 no dangling ends | OK | s02 `ends`; hamlet checks `dangling_street_ends: []`. |
| J4 no road through a fence | OK | QV `dirt_road_fence_crossings: 0`, `nw_corner_intact: true`, asphalt crossings inside gates; Rough KPP road through a 7.6 m gate. |
| J5 widths | OK | `common.WIDTH`; Downtown `facade_to_facade_m` 22.0; alleys 5.6. |
| J6 markings / ruts | OK | Dirt = splat ruts (W85Builder l.548); markings only on asphalt. |
| J7 Downtown entries | OK | `dt_entry` heights fixed at 5.06 m (s03 l.323–324); FIXED_BY_LOGIC §9. |
| J8 bridges | OK | QV bridge with rails; Tramduro `bridge` kind on piers (pier step 20.9 m). |
| J9 junction screenshots + drives | **MISSING** | None in the reports or Working/Reviews/Map_W85_build. |
| J10 port road smooth, no step | **DEVIATION** | `port_road` descends 12.1 → 2.5 m at 8 %; inside the 2.5 m port pad it is still 7.9–2.8 m. The result is a ~5 m embankment across the yard (pad edge band slopes max 86°, p95 54°) and a 1.31 m step at its west join. |
| J11 Hamlet → Rough, no Construction → Rough | OK | Roads list (`hamlet_to_rough` over the land bridge y 572). |
| J12 loops / no long straights | UNKNOWN | Downtown `see_through_m` has W–E straights of 486 m (S1, B) — inherited from the plan. |
| J13 tunnel approaches | OK | Approaches 22 m (N) / 37 m (S). |
| J14 stitch ends ≤ 3 m | OK | s02 `snap_ends()`. |

## 3. Districts

| # | Verdict | Evidence |
|---|---|---|
| D1 forest | OK | 1 swamp, 1 lake, wagon 24×3.2 at the rails, no beach road (forest checks). |
| D2a 24 houses + hut | OK | `hamlet_v85.json` counts: houses 24, base2_hut 1. |
| D2b fields 32×26 / 40×26 flat | OK | `02-A-FIELD1` [32, 26], `02-A-FIELD2` [40, 26]; flattened with a 10 m blend. |
| D2c church, square, … | OK | Hamlet zones and buildings (plaza, cemetery, orchard, pig_pen, pond, fishing_platform). |
| D2d Hamlet without a seam | **DEVIATION** | No plate or border: OK. But a straight 388 m earth wall up to 10 m runs along the Hamlet's east edge (section 0). |
| D2e no fences/wires/barn/shop | OK | Hamlet checks: fences_between_houses 0, wires 0, kolkhoz_barn 0, shop 0. |
| D2f grandpa's yard as i09 | OK / UNKNOWN | FIXED_BY_LOGIC §26; GRANDPA_YARD_v01 props; exact i09 layout still open (v10 §12). |
| D3a one fence, 19 m gate | OK | `03-fence`, `03-gate-main`; FIXED_BY_LOGIC §13. |
| D3b A 24×14 + crane, B 20×12 | OK | `03-04-A` 24.0×14.0, `03-05-B` 20.0×12.0. |
| D3c cabins, 3 m gaps | OK | `cabin_gaps_m` 3.0. |
| D3d bright, fuel station asked | OK | FOR_VADIM Q4 (fuel station off). Lighting: UNKNOWN. |
| D4a denser | OK | Plan v52 data. |
| D4b stepped W–E via A4/A5 | **DEVIATION** (open) | Arches are 13–14 m openings (the whole gap between blocks), not ~6–7 m arches under a continuous house (FOR_VADIM Q9; ROUGH_LEGEND §1.1). |
| D4c S–N closed, garage drives | OK / UNKNOWN | `straight_S_to_N_open_x_ranges` [[183, 183]] — a zero-width line; needs an in-game look. |
| D4d box 40×33 | OK | FIXED_BY_LOGIC §11. |
| D4e north fence straight + KPP | **DEVIATION** (open) | District fence and state fence 20–30 m apart = double fence (FOR_VADIM Q7); also breaks N10. |
| D4f dry grass, ruts; ring asphalt | OK / open | The east side of the "П" road is missing on v85 (FOR_VADIM Q6). |
| D5a 22 m streets, no hill→beach sightline | OK | `facade_to_facade_m` 22.0; N–S see-through max 191.8 m (AX). |
| D5b all built up | OK | 3 small `unbuilt_block_pockets` (NEX 750 m² filled). |
| D5c alleys | OK | NW1 / NC1 / SW2 / SW4 at 5.6 m. |
| D5d houses +1 floor, brighter | OK / UNKNOWN | D4 rollout; Fedya's texture choice (see S1). |
| D5e trees only in squares | OK | `in_downtown_outside_squares` 0. |
| D6 port | **DEVIATION** | See J10. |
| D7a semi-ring to east gate | OK | `07-gate-east` is the only way in; road grade 12.4 %. |
| D7b offset ~9 m from fence | **DEVIATION** | `road_to_fence_min_m` 4.5 (v09 asked for 9 m; v10 dropped the number). |
| D7c FBI + 4 villas on +40…+44 | **DEVIATION** | Terraces right, but villas stand on 7–15 m uneven ground (R11). FBI size open (Q3). |
| D7d no beach exit, ruts, palms 11 m | OK | `foot_palm_gaps_m` 10.3–11.8; ruts along the foot; `downtown_house_gap_m` 19.5. |
| D8a–d Quiet Valley | OK (layout) / **DEVIATION** (relief) | Fence 1.0 m, NW corner intact, dirt road ≥ 6.8 m from the fence. The base-5 lab yard is a pit with 3–4 m vertical walls (section 0). |
| D9a white sand | OK | `09-sand` `#F7F2E0`. |
| D9b 2 towers | OK | Beach props: lifeguard_tower 2. |
| D9c pier from the waterline | OK | `pier_start_on_coast: true`. |
| D9d palm rows 11 m | OK | `min_palm_spacing_m` 10.95. |
| D9e van lanes free | OK | Umbrella sets ≥ 1.84 m from the strip; palms ≥ 5.2 m from the track. |
| D10 Tramduro | OK / UNKNOWN | Real bridge; mounds R24 unknown. |
| D11 north border | OK | KPP, sliding gate and button are Rough data; invisible wall built; no sea cliff. |

## 4. Vegetation, details, surfaces, light, gameplay, process

| # | Verdict | Evidence |
|---|---|---|
| V1 trees by zones and rules | OK | `vegetation_v85.json` checks: min_road_edge 2.3 m, in_water 0, Downtown outside squares 0; `min_facade_m` 1.0 (< 3 m; may be front-garden trees — check). |
| V2 details by rules | OK (data) / UNKNOWN | `details_v85.json` counts; no Hamlet lamps (Fedya 21.10). |
| V3 colliders / GripAnchors | UNKNOWN | — |
| V4 palms not overlapping | OK | 10.95 m minimum. |
| S1 textures agreed with Vadim | **DEVIATION** | Approved by Fedya's sheets (FEDYA_TO_VADIM: «утверждено Федей листами»), not sent to Vadim for "yes" (v10 §13 step 2). |
| S2 smooth transitions | OK (edges) / **DEVIATION** (steep faces) | Zone edge blend 1.5–3 m. Rock layer at slope > 36° (s07 l.112) with planar terrain UVs stretches on the walls from section 0. |
| S3 dry grass → meadow 40–80 m | OK | FIXED_BY_LOGIC §3. |
| S4 water v05 / calm_v09 | OK | `water_v85.json` sea material `Sea_trial_calm_v09`. |
| S5 OAR style | UNKNOWN | — |
| L1 light/fog by district | UNKNOWN | i10 look copied onto **W76** district rectangles (W85Look l.20–30), not refitted to v85. |
| L2 tunnel glare | OK | `W76Atmosphere.GlareOnly` kept (W85Look l.72–75). |
| L3 cheap / PC_RPAsset | UNKNOWN | — |
| G1–G3 | UNKNOWN | — |
| G4 dimensions | **DEVIATION** | Base 4 yard 26 × 7.5 m (< 12–15 m to turn; FOR_VADIM Q11); football-box gate strip 4 m (Q8). |
| G5 roads fastest | UNKNOWN | — |
| N1 no rounded squares | **DEVIATION** (minor) | Elite hill = superellipse ⁴; river-shoulder rectangle edges visible as straight walls. |
| N10 no double fences | **DEVIATION** (open) | Rough north (Q7). |
| N17 no walls/steps/cake | **DEVIATION** | Section 0, R17, J1. |
| other N items | OK / UNKNOWN | Covered by checks above (trees, parking, canal, logos, paid assets). |
| P1 plan + mismatch list first | **DEVIATION** | The mismatch list (FOR_VADIM, 18 questions) was sent after the build, together with it. |
| P2 textures with Vadim | **DEVIATION** | = S1. |
| P3 relief approval | **MISSING** | = R34. |
| P4 per-district top view / drive / FPS | partly OK | Top-view checks `Tools/MapV85/out_v01/check_*.png`; FPS at 3 spots; no van drives per district. |
| P5 fixed-by-logic report | OK | `docs/reports/MAP_W85_FIXED_BY_LOGIC.md`. |
| P6 variants for gameplay changes | OK | FOR_VADIM Q1–Q18 with options. |
| P7 new numbers, free assets | OK | Data v01, CC0 ambientCG only. |
| P8 checked from player/van camera | **MISSING** | No van-camera evidence for the relief and joins. |

**Verdict counts** (112 rows above; a row with DEVIATION or MISSING anywhere counts as that): OK 54, OK in data but needs an in-game look 7, DEVIATION 31, MISSING 6, UNKNOWN 14.

## 5. Top problems Vadim will notice (ranked) — with the concrete fix (no code edited)

1. **Straight 3–10 m earth wall along the Hamlet's east edge (Fedya's screenshot), plus 3 more straight walls (NW foot up to 19 m, QV and coast up to 7.5 m)** — 720 m in total.
   Fix in `s03_terrain.py` `main()`, river block l.266–273: drop the boolean rectangle `riv_zone` and the binary `padw < 0.5` exclusion.
   - Use a soft weight instead: `zone_w = sm((xs-400)/60)*sm((730-xs)/60)*sm((ys-50)/60)*sm((800-ys)/60)*(1-ndimage.gaussian_filter(padw,8))`, and blend `near *= zone_w`.
   - Better: cut the gorge **into** natural ground. Shrink the shoulder raise (`near` reach 150 → ≤ 60 m, bank ≤ ground + 2–3 m) and lower the bed instead, so the Hamlet streets meet the bypass at grade.
2. **Base 5 lab yard sunk 3–4 m with vertical walls on 3 sides.** Same cause and fix as #1. Alternatively, run the `quiet_valley_lab` `pad()` call (l.212–215) after the river block, with `hh=None` and a 30–40 m blend.
3. **Elite villas hang over a road cut of up to 15 m; the plateau inside the fence is dragged down to 21 m.**
   - In the road block (l.348–374), add a protect mask (Elite fence polygon, villa plots, all pads): `road_w *= 1 - protect_soft`.
   - For `stone_serpentine`, cap `reach` at ~10–12 m and use the parapet as a retaining wall (`W85Builder.Parapet`) instead of a 70 m earth cut.
   - Re-apply the villa terraces (l.170–174) after the roads.
   - Restore the v09 ~9 m fence offset in `s04_elite.py`.
4. **Height steps at road joins (up to 2.26 m at the VIEW B serpentine / Rough ring; 1.3–1.4 m on the Rough → port road).** In the road profiling (l.307–337), profile in rank order (ring/rural asphalt → serpentine → drives → dirt). Pin every end listed in `roads_v85.json` `joins_snapped` to the parent road's height at the join, as a fixed index like `dt_entry`, then re-clamp the grade. Hamlet dirt streets get the same treatment once #1 is fixed.
5. **~5 m road embankment across the port yard; ramps inside the Rough and lab pads.** In the road profiling, fix every road sample that lies inside a pad polygon to the pad height (extend the `fixed` index list beyond `dt_entry`). Let the 8 % clamp build the ramp outside the pad. Or pass the pad heights as `heights_abs` for those spans.
6. **Steep road banks (design ~34° peak, measured 56–84°).** In l.349 set `slope_k` 0.45 → 0.25 for rural asphalt and dirt, 0.30 → 0.22 for the serpentine. Raise the `reach` cap 70 → 120 m (l.369). Compute `dz` with `ndimage.maximum_filter` instead of `gaussian_filter` (l.368). Where a bank still exceeds ~30°, place rock outcrops or retaining walls (s06b / builder) instead of bare earth.
7. **VIEW B is at ~22 m instead of ~46 m — the hill itself was lowered.** Reduce the `pass_k` factor (l.153) from 0.62 to ~0.2–0.25. Run the serpentine on a bench with ≤ 2 m cut on the uphill side and the 1–1.5 m outer berm (l.376–379; add stones in s06b). Show Vadim the two options as pictures (this is FOR_VADIM Q17).
8. **Hamlet has no designed relief (bumps +1.5…+3.8 m, dip −1.4 m).** In the s03 Hamlet block (before the plot flattening, l.216), add the 4–5 `terrain_feature` polygons from `HAMLET_LAYOUT_v04.json` (world = layout + (70, 0)), with a 10 m blend and slopes 4–12°. Exclude them from the trap filler.
9. **Over-flattening by the trap filler (204 depressions filled, including designed dips and gully ends).** In l.391–400, fill only depressions deeper than ~1.5 m whose spill path is steeper than ~15° (the van can't get out). Exempt `RELIEF` gullies and Hamlet dips.
10. **Construction sits on a "cake" plateau (26 m rings, banks ~30° all round).** In the Construction block (l.175–187), widen the rings 26 → 50–70 m with noise on `d_out`, and make them asymmetric: gentle towards the main road and the gate, steeper only behind the site. Keep edge slopes ≤ 15–20°.
11. **Elite hill is a rounded square with 35–52° flanks.** At l.161, use exponent 2–2.5, perturb `rho` with fbm, and make the slopes asymmetric: gentler on the north where the road climbs, rocky toward the sea. This also removes the straight west face at x ≈ 1310.
12. **Stretched textures on every steep face.** Once the geometry is fixed: a triplanar rock layer in the terrain material (W85Look / `TerrainMaterial`) or rock meshes on faces > 35° (v10 §3.1 "каменные выходы на крутых местах"). The s07 l.112 threshold alone only recolours.
13. **The Hamlet → river transition and the land bridge at the bypass look artificial (straight shelf, buildings across it).** After #1, re-run s03 and check that the shed `02-S-…_09_4` and the bus stop `02-U-STOP` sit on ≤ 1.5 m ground range. Add a generic ground-fit check (footprint height range > 1.5 m → error) next to `W85FloatCheck`.
14. **Process gaps Vadim asked for explicitly:**
    - no relief scheme with 4–6 ground/van shots before the build (§3.3 / §13 step 3);
    - textures approved by Fedya, not Vadim (§13 step 2);
    - no van drive over hills and joins, no junction screenshots (§3.2, §6).

    Fix: after #1–#7, send `relief_scheme_v86` + 6 ground shots + junction top shots, and record van drive times (road vs off-road).
15. **Open district deviations that stay wrong until Vadim answers:**
    - Rough double north fence (Q7);
    - arches A4/A5 13–14 m wide instead of ~6–7 m arches (Q9);
    - missing east side of the "П" road (Q6);
    - base 4 yard only 7.5 m deep (Q11).

    Propose the option that matches the specs (Q7 → 3, Q9 → 2, Q6 → 1, Q11 → 2) as the default in `s04z_owner_decisions.py`.
