# Map plan R01 v19 — G18 stage 1

Source: frozen v18. Pilot layout, road chain and dependent graphs change. Full-map palette/sky and the G19 happykeys rock clusters are explicitly approved additions. Human, van and building dimensions are unchanged. Rough District and fade-zone bare/deciduous trees use approved CC0 happykeys T01-T03 with the supplied cold recolour and capsule proxies; trees elsewhere retain their previous models/materials.

## Spacing

| Measure | v18 | v19 |
| --- | ---: | ---: |
| House current two-neighbour mean gap (m) | 36.26 | 28.50 |
| House current two-neighbour max gap (m) | 76.84 | 50.76 |
| House frozen v18 pairs mean / max (m) | 36.26 / 76.84 | 31.78 / 56.07 |
| Block current two-neighbour mean gap (m) | 7.43 | 6.22 |
| Block current two-neighbour max gap (m) | 26.82 | 19.25 |
| Block frozen v18 pairs mean / max (m) | 7.43 / 26.82 | 6.49 / 19.25 |
| village: area_m2 | 54604.68 | 47268.00 |
| village: built_up_pct | 5.16 | 6.03 |
| village: building_free_circle_diameter_m | 85.70 | 86.05 |
| residential: area_m2 | 39131.52 | 39131.52 |
| residential: built_up_pct | 29.89 | 30.59 |
| residential: building_free_circle_diameter_m | 41.30 | 33.29 |
| 16 household plot area (m²) | 13386.46 | 7392.65 |

Gaps are footprint-edge distances. Current neighbours are the union of each building’s two nearest neighbours in each revision. Frozen pairs keep the v18 pairs for an honest displacement comparison. The empty circle is building-only, so an orchard, working field or relief can remain inside it; it is not a claim that those places are empty lawns.

## Places and traversal

The Hamlet has three household groups, an orchard workyard, hay field, north allotment and B02 loading area. The southern housing loop is shortened; the Forest connector retains its fixed endpoint. The Rough District gains ten garage shells, a garage court, service yard, east parking and a calm playground. Road bends are rounded. The three named passages preserve readable alternatives to the direct meadow cuts.

## Terrain and new fields

`v19_pilots` carries scope boxes, hills (metres, finite cosine supports), connected ravines (depth/half-width/station spacing), calm activity polygons, PILOT_KIT module placements (ground anchor/yaw), natural solid props, decal strips and explicit passages with van access. `tree_placement_changes` is a complete before/after instance list. `height_offset_m` is a design target; the Unity height model gives road and building access priority. All achieved heights and road grades require the Unity validation report.

The height field uses explicit positive/negative hills and fitted road cuttings. Existing road/building/yard constraints retain calm access surfaces. `v19_pilots.happykeys` records the CC0 source, tree replacement rule and deterministic natural rock clusters across the map. Every rock cluster excludes roads, paths, buildings, water, fence lines and gameplay points. R01 stays decorative; all other rocks use the manifest proxies. Source FBXs and the v07 textures remain unchanged.

## Every moved building

| Building | dx (m) | dz (m) |
| --- | ---: | ---: |
| 02_B05 | 12.250 | 2.812 |
| 02_old_shed_1 | 12.580 | 5.276 |
| 02_B06 | -8.682 | -13.445 |
| 02_old_shed_2 | -7.742 | -10.482 |
| 02_B07 | -13.165 | 3.657 |
| 02_old_shed_3 | -19.364 | 2.879 |
| 02_B08 | -2.386 | 23.875 |
| 02_old_shed_4 | 1.168 | 32.284 |
| 02_v18_shed_02_ground_05_4 | 0.242 | 26.613 |
| 02_B09 | -9.193 | 8.000 |
| 02_old_shed_5 | -17.528 | 5.694 |
| 02_v18_shed_02_ground_06_4 | -9.598 | 8.959 |
| 02_B10 | 7.879 | 26.187 |
| 02_old_shed_6 | 11.015 | 34.220 |
| 02_v18_shed_02_ground_07_4 | 5.709 | 33.862 |
| 02_B11 | -0.313 | 35.050 |
| 02_old_shed_7 | 3.290 | 34.100 |
| 02_v18_shed_02_ground_08_4 | -2.611 | 36.689 |
| 02_B12 | -1.902 | 17.758 |
| 02_old_shed_8 | 1.032 | 26.554 |
| 02_v18_shed_02_ground_09_4 | -10.213 | 26.467 |
| 02_house_18 | -15.947 | -4.726 |
| 02_shed_18 | -18.675 | -3.387 |
| 02_house_19 | -1.534 | 26.658 |
| 02_shed_19 | -1.223 | 26.378 |
| 02_house_21 | -15.020 | -26.408 |
| 02_shed_21 | -16.160 | -27.000 |
| 02_house_20 | -18.724 | 1.436 |
| 02_shed_20 | -21.136 | -0.200 |
| 02_v18_plot_01_house | -13.515 | 49.868 |
| 02_v18_plot_01_shed | -11.093 | 48.488 |
| 02_v18_plot_02_house | 44.703 | 40.871 |
| 02_v18_plot_02_shed | 50.880 | 39.170 |
| 02_v18_plot_03_house | -12.615 | -0.293 |
| 02_v18_plot_03_shed | -12.615 | -0.293 |
| 02_v18_plot_04_house | -20.175 | -1.139 |
| 02_v18_plot_04_shed | -19.878 | -0.712 |
| 04_den | -8.000 | 0.000 |
| 04_northwest_court | 5.000 | -3.000 |
| 04_northwest_south_wing | 5.000 | -3.000 |
| 04_west_north | -3.000 | -3.000 |
| 04_north_horizontal | 0.000 | -6.000 |
| 04_north_horizontal_s2 | 0.000 | -6.000 |
| 04_west_arch_court | 2.000 | 0.000 |
| 04_west_middle | -3.000 | -7.000 |
| 04_west_middle_s2 | -3.000 | -7.000 |
| 04_center_south | 3.000 | 0.000 |
| 04_center_south_s2 | 3.000 | 0.000 |
| 04_quiet_court | -6.000 | -2.000 |
| 04_quiet_annex | -6.000 | -2.000 |
| 04_far_east_north | -6.000 | -2.000 |
| 04_far_east_north_s2 | -6.000 | -2.000 |
| 04_east_inner_south | -14.000 | 0.000 |
| 04_east_inner_south_s2 | -14.000 | 0.000 |
| 04_east_crossbar | -14.000 | -0.000 |
| 04_southeast_court | -14.000 | 0.000 |
| 04_far_east_south | -14.000 | 0.000 |
| 04_blind_alley_closed_end | -14.000 | 0.000 |
| 04_garage_32 | -17.760 | 68.850 |
| 04_v17_transformer_008 | -14.000 | 0.000 |
| 04_v18_shed_006_0 | 2.000 | 0.000 |
| 04_v18_shed_006_1 | 2.000 | 0.000 |

## Every changed street

| Street | v18 length (m) | v19 length (m) |
| --- | ---: | ---: |
| hamlet_bypass | 243.88 | 243.36 |
| hamlet_rough_e | 138.37 | 140.32 |
| 02_h_south | 120.20 | 120.00 |
| 02_h_north | 162.02 | 166.36 |
| 02_h_loop | 202.63 | 160.13 |
| 02_h_field09 | 29.03 | 39.12 |
| 02_h_d11 | 23.22 | 9.15 |
| 02_h_d12 | 18.22 | 26.50 |
| 02_h_d13 | 25.84 | 5.45 |
| 02_h_d14 | 4.80 | 4.76 |
| 02_h_d17 | 12.00 | 20.47 |
| 02_h_d16 | 6.20 | 22.03 |
| 02_h_d15 | 4.20 | 10.38 |
| 02_h_d_tower | 29.80 | 39.94 |
| 02_h_d18 | 13.40 | 8.76 |
| 02_h_d19 | 7.04 | 15.23 |
| 02_h_d20 | 7.77 | 5.66 |
| 02_h_d21 | 44.01 | 19.41 |

## Every changed point

| Point | v18 position | v19 position | v19 access road |
| --- | --- | --- | --- |
| D02_POI_09 | [172.0, 405.8] | [172.0, 405.8] | 02_h_field09 |
| D02_POI_03 | [262.2, 559.0] | [262.2, 559.0] | 02_h_d12 |
| D02_POI_10 | [162.2, 567.2] | [174.4497, 570.0118] | 02_h_main |
| D02_POI_11 | [209.0, 587.8] | [200.3184, 574.3548] | 02_h_d11 |
| D02_POI_12 | [273.939, 579.346] | [260.7742, 583.003] | 02_h_d12 |
| D02_POI_13 | [263.256, 456.959] | [260.8705, 480.8344] | 02_h_d13 |
| D02_POI_14 | [333.0, 463.8] | [325.428, 471.014] | 02_h_d14 |
| D02_POI_15 | [249.6, 418.4] | [257.4794, 444.5872] | 02_h_d15 |
| D02_POI_16 | [295.0, 408.6] | [294.6873, 443.6495] | 02_h_d16 |
| D02_POI_17 | [346.0, 426.0] | [344.0976, 443.7581] | 02_h_d17 |
| D02_POI_06 | [196.6, 462.0] | [196.6, 462.0] | 02_h_field09 |
| D04_POI_05 | [687.2, 621.6] | [679.2, 621.6] | 04_drive |
| D04_POI_09 | [580.6, 668.2] | [585.6, 665.2] | 04_drive |
| D04_POI_11 | [593.8, 626.8] | [595.8, 626.8] | 04_drive |
| D04_POI_12 | [758.8, 664.8] | [752.8, 662.8] | 04_drive |
| D04_POI_13 | [758.8, 588.4] | [744.8, 588.4] | 04_drive |
| D04_POI_14 | [736.4, 606.0] | [722.4, 606.0] | 04_drive |
| WATER_TOWER | [338.4, 517.8] | [338.4, 517.8] | 02_h_d_tower |
| P07 | [687.2, 621.6] | [679.2, 621.6] | 04_drive |

## Graph changes and checks

The complete exact records for every added, removed and changed road/pedestrian edge are in `MAP_PLAN_R01_v19_CHANGES.json`, alongside all point records, road polylines, building translations and metrics. Nodes are stable coordinate hashes; splitting a moved street can change several edges. Existing disconnected beach footbridge components are retained.

- road_graph: 255 added, 319 removed, 6 changed; 1 components.
- pedestrian_graph: 417 added, 371 removed, 0 changed; 5 components.

Geometry checks: {"new_building_overlaps": [], "plot_overlaps": [], "moved_buildings": 62, "changed_roads": 18}.

Python road-profile check: {"hamlet_bypass": 0.0011, "main_bridge_construction": 0.0, "main_construction_city": 5.4076, "main_city_elite": 4.0624, "construction_rough": 0.0, "rough_city_east": 7.9549, "rough_port": 0.0, "hamlet_rough_e": 7.589, "construction_valley": 0.0, "forest_valley": 7.5174, "forest_main": 0.08, "hamlet_forest": 0.0, "02_h_main": 0.0, "02_h_south": 0.0, "02_h_north": 0.0004, "02_h_base": 0.0, "02_h_loop": 0.0, "02_h_field09": 0.0, "02_h_church": 0.0, "02_h_d11": 0.0, "02_h_d12": 0.0, "02_h_d13": 0.0, "02_h_d14": 0.0, "02_h_d17": 0.0, "02_h_d16": 0.0142, "02_h_d15": 0.0, "02_h_d_tower": 0.0, "02_h_d18": 0.0, "02_h_d19": 0.0, "02_h_d20": 0.0, "02_h_d21": 0.0, "05_N": 0.0243, "05_W": 0.0, "05_S": 0.0, "05_E": 0.0, "05_B": 0.0, "05_Va": 0.0, "05_Va2": 0.0, "05_Vb": 0.0, "05_Vc": 0.0401, "05_AX": 0.0, "05_Vd": 0.0, "05_L1": 0.0, "05_L2": 0.0, "05_L3": 0.0, "05_Hsw": 0.0, "05_Hse": 0.0, "05_Hse2": 0.0, "03_R1": 0.0, "03_R2": 0.0, "03_R3": 0.0, "03_track_1": 0.0, "03_track_2": 0.0, "01_road_1": 0.4221, "01_road_2": 0.2508, "01_road_3": 0.0, "01_road_4": 0.0, "04_drive": 0.0997, "06_port_road": 0.0, "07_drive": 7.6618, "07_spur_01": 7.3058, "07_spur_02": 8.005, "07_spur_03": 4.4525, "08_main": 0.0, "08_lab_road": 0.0, "10_main": 0.0, "10_palace": 0.0, "10_palace_oval": 0.0, "DECK_bridge_main": 0.0, "DECK_bridge_valley": 0.0, "DECK_bridge_north": 0.3139, "DECK_bridge_tramduro": 0.0, "trail_waterfall": 0.0025, "trail_mountain": 6.861, "promenade_bay": 0.0, "08_footpath_loop": 0.0007, "DECK_footbridge_beach_1": 0.0, "DECK_footbridge_beach_2": 0.0, "DECK_footbridge_beach_3": 0.0, "DECK_footbridge_canal_mouth": 0.0, "09_path_2": 0.0, "09_path_4": 0.0597, "09_path_6": 0.0, "09_path_8": 0.0, "09_path_10": 0.0, "09_path_12": 0.0}. This is the numerical port, not a replacement for Unity wheel/ground checks.

Unity build, screenshots, route comparison, collisions, missing sounds and per-spec acceptance are recorded separately in `docs/reports/MAP_PILOT_v19_PROGRESS.md`. Performance is NOT RUN by request.
