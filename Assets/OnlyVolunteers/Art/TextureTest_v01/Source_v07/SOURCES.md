# TextureTest v07 (Map W86 texture samples, 2026-10-22): texture sources

All textures here are made by `Working/Reviews/MapW86_Textures_2026-10-22/tools/gen_textures_v07.py`.
Downloaded sets: ambientCG, licence **CC0 1.0** (https://docs.ambientcg.com/license/), 1K-JPG, downloaded 22.10.2026 by agent A4.
Originals (Color / NormalGL / Roughness / Opacity / Metalness only) are kept in `ArtSource/Textures/ambientCG_2026-10-22/` (own SOURCES.md there).
Two sets come from the earlier download `ArtSource/Textures/ambientCG_2026-10-21/` (CC0, lead, 21.10.2026).

Adaptation to the One-Armed Robber look: grain removed (median + light blur), low-frequency grime removed (high-pass),
contrast compressed toward a painted mean; neutral luminance where the colour comes from the material / vertex tint,
hue kept (but cleaned) for wood, OSB and sandstone. Normal maps = ambientCG NormalGL (strength set in the material) or
own (computed from a height field).

| Output (`Source_v07/`) | Source | Real size of one tile | Adaptation |
|---|---|---|---|
| T7_travertine_panels_albedo / _normal | ambientCG Travertine009 (https://ambientcg.com/view?id=Travertine009) | 2.4 m | luminance 42 %, 2 x 2 repeat, own stack-bond panel joints 1.2 x 0.6 m, +-3 % per panel |
| T7_concrete_smooth_albedo / _normal | ambientCG Concrete046 | 2.4 m | luminance 32 %, blotches removed |
| T7_panel_smooth_albedo / _normal | ambientCG Concrete046 | 2.4 m | as above + own open joints (panels 1.2 x 2.4 m) |
| T7_concrete_boardformed_albedo / _normal | ambientCG Concrete045 | 2.0 m | luminance 55 % |
| T7_concrete_formwork_albedo / _normal | ambientCG Concrete031 | 2.4 m | luminance 50 %, brightened |
| T7_concrete_aggregate_albedo | ambientCG Concrete040 | 1.4 m | luminance 50 % |
| T7_slab_granite_warm_albedo | ambientCG Granite001A | 2.0 m (4 slabs 1 x 1 m) | grain 32 %, slabs rotated, joints barely visible (-9 %) |
| T7_slab_granite_grey_albedo | ambientCG Granite002A | 2.0 m | same |
| T7_slab_limestone_albedo | ambientCG Travertine009 | 2.0 m | same |
| T7_slab_normal | own | 2.0 m | joint grooves |
| T7_stone_grain_albedo | ambientCG Granite002A | 1.0 m | grain 50 % (bands, coping, caps; tinted) |
| T7_pool_mosaic_albedo / _normal | ambientCG Tiles132A | 1.5 m | tiles neutral (tinted per variant), light grout |
| T7_setts_granite_albedo / _normal | ambientCG PavingStones070 | 1.15 m | moss removed, luminance 60 % |
| T7_setts_sandstone_albedo / _normal | ambientCG PavingStones146 | 1.2 m | colour kept, cleaned, saturation 75 % |
| T7_rubble_grey_albedo / _normal | ambientCG Bricks113A (2026-10-21 set) | 2.2 m | luminance 55 % |
| T7_rubble_warm_albedo / _normal | ambientCG Bricks106A (2026-10-21 set) | 2.2 m | colour kept, cleaned, saturation 70 % |
| T7_asphalt_light_albedo | ambientCG Asphalt031 | 3.0 m | grain calmed, luminance 35 % |
| T7_rustic_ashlar_albedo / _normal | own blocks + ambientCG Granite002A grain | 2.4 m | rusticated blocks 1.2 x 0.6 m, chamfered joints |
| T7_metal_trapez_albedo / _normal | ambientCG CorrugatedSteel007A | 1.5 m | neutral, soft rib shading baked (-10 %) |
| T7_metal_wave_albedo / _normal | ambientCG CorrugatedSteel005 | 1.2 m | galvanised streaks calmed, rib shading |
| T7_chainlink_rgba | ambientCG Fence003 (opacity) | 0.8 m | wire colour from the material, alpha clip |
| T7_mesh_weld_rgba | ambientCG Fence008A (opacity) | 2.4 m | same |
| T7_shutter_albedo / _normal | own | 2.0 m | roller-shutter slats 0.1 m |
| T7_planks_scaffold_albedo / _normal | ambientCG Planks021 | 1.4 m | colour kept, cleaned |
| T7_planks_weathered_albedo / _normal | ambientCG Planks012 | 1.6 m | luminance 60 % (fence colour from the material) |
| T7_wood_teak_albedo | ambientCG Wood089 | 1.2 m | colour kept, cleaned |
| T7_wood_larch_albedo | ambientCG Wood087 | 1.2 m | colour kept, cleaned |
| T7_osb_albedo | ambientCG Chipboard004 | 1.22 m | colour kept, contrast 55 % |
| T7_brick_roman_albedo / _normal | own long-format brick + ambientCG Bricks085 tone / normal | 1.2 m | clean bricks 30 x 7.5 cm, light mortar |
| T7_container_atlas_albedo / _normal | own | atlas 2048 x 1024 | ISO container side (11 trapezoid ribs per 3 m), door end, blind end; neutral, tinted |
| T7_office_glass_atlas_albedo | own | 4 x 4 cells | office glass: sky gradient, glare, blinds / ceiling lights / plants |
| T7_net_rgba | own | 1.0 m | scaffold safety net knit, alpha-blended |

Project textures referenced read-only by the v07 materials (not copied, importers untouched): TL_meadow, StyleKit 1b dirt,
3a brick, 3d cinder, 4d flat roof, Source_v03 Plaster001 (D4 plaster), Built_v04 asphalt A5d12 and sidewalk S1;
water materials W85_water_flow and Sea_trial_calm_v09.
