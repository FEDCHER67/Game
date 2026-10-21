# TextureTest v01 / v02: texture and material sources

No third-party online textures were downloaded for these tests. Everything below is project-own: made by our scripts, the StyleKit, or GPT for this project. The "made by" column says where each texture comes from.

| Texture (used for) | File | Made by | Licence |
|---|---|---|---|
| Logs, 0.24 m courses (Hamlet house walls) | `Source_v02/TT_logs_v02_albedo.png` | `ArtSource/Props/HAMLET_HOUSE_v01/gen_hamlet_textures_v01.py` | own, original |
| Vertical boards, paintable (gables, shutters, doors) | `Source_v02/TT_boards_vertical_v02_albedo.png` | same script | own, original |
| Brick SK 3a v07 (plinths, Downtown brick) | `Art/StyleKit_v3/Textures/3a_brick/` | StyleKit_v3 | project-own |
| Plaster SK 3b v01 / v07 (Downtown plaster, stone trims) | `Art/StyleKit_v3/Textures/3b_plaster_stucco/` | StyleKit_v3 | project-own |
| Boards SK 5a v07 (porch, deck) | `Art/StyleKit_v3/Textures/5a_wood_planks_fences/` | StyleKit_v3 | project-own |
| Corrugated metal SK 4c v07 (red metal roof of house B) | `Art/StyleKit_v3/Textures/4c_corrugated_metal/` | StyleKit_v3 | project-own |
| Wavy slate S-4 (Hamlet roof) | `Art/Map/Textures/roofs/roof_slate_wavy_mask.png` | project map textures | project-own |
| KH2 panel with small tiles (Rough R2 / R2b) | `Built*/Textures/KH2_panel_small_tiles_albedo.png` | `Working/Reviews/Textures_2026-10-17/gen_rough_soviet_v01.py` | own, original |
| KH window / door / streak atlas | `Built*/Textures/KH_windows_atlas_v01.png` | `.../gen_own_textures_v01.py` | own, original |
| FacadeTrim, Fabric red / green / blue, Downtown GPT facades | `Built*/Textures/` | GPT for the project (`gpt_missing_v02_2026-10-18`, `TEXTURE_MANIFEST.json`) | project-own |
| Asphalt A5d12, sidewalk S1 | `Built*/Textures/` | `gen_street_asphalt_v01.py`, `gen_paving_v01.py` | own, original |
| Meadow, worn grass, dirt SK 1b, old asphalt SK 2a (test ground) | `Art/Map/Textures/Detail/`, `Art/StyleKit_v3/Textures/` | existing project assets | project-own (origin not re-checked in this test) |

Approved materials reused unchanged: V19 brick / stucco v07 / concrete / boards / logs / corrugated / clay tiles (`Map/LookV3/Palette19/Test_v02/Materials/`), wavy slate (`Map/Look/Materials/Look_mat_roof_sheet__5B6D6A.mat`), flat bitumen roof (`Map/LookV3/Materials/V3S_4d_flat_bitumen_roof.mat`).

New materials exist only in `Built/` (v01) and `Built_v02/` (v02). The `*_v02` house materials are URP Lit, because the FBX UVs are 1 UV = 1 m and the house has no vertex colours.

## v03: ambientCG (CC0 1.0)

The lead downloaded these on 21.10.2026 with Fedya's OK; originals and their own SOURCES.md are in `ArtSource/Textures/ambientCG_2026-10-21/`. Licence: CC0 1.0 (https://docs.ambientcg.com/license/). Only the adapted results are copied into `Source_v03/`, all at 1024 px.

| ambientCG set | Used for | Adapted files (`Source_v03/`) | Adaptation |
|---|---|---|---|
| Plaster001 (https://ambientcg.com/view?id=Plaster001) | Downtown plaster (D4) | `TT_acg_Plaster001_neutral_albedo.png`, `TT_acg_Plaster001_normal.png` | Luminance only, normalised to 0.86 with 45 % of the original contrast. Colour per building comes from the material (vertex tint). Normal map at 0.35. |
| Facade001 (https://ambientcg.com/view?id=Facade001) | Tower curtain-wall glass (T1 / G-T) | `TT_acg_Facade001_glass_albedo.png`, `TT_acg_Facade001_glass_metal_smooth.png`, `TT_acg_Facade001_normal.png` | Neutral grey panel-tone variation (55 % contrast). Dark-blue tint comes from the material. Metallic = 0.6 × metalness; smoothness = 0.97 − 0.3 × roughness. Normal map at 0.45. One tile = 16 × 10 panels = 22.54 × 18 m, which is 8 tower facets × 5 floors. |

The other nine downloaded sets (Facade002/006/009, PaintedPlaster006/017, Bricks106A/113A, Logs001, WoodSiding008) were reviewed and are not used. Bricks106A/113A are stone blocks rather than brick; Logs001 is a firewood stack; the others were not needed for this pass.

## v04 (round 4)

| Texture (used for) | File | Made by | Licence |
|---|---|---|---|
| Weathered corrugated roof sheets (Hamlet roofs, tinted dark grey / dark rust / dark green-grey per house) | `Source_v04/TT_roof_corrugated_weathered_v01_albedo.png` | `ArtSource/Props/HAMLET_HOUSE_v01/gen_hamlet_textures_v02.py` | own, original |

Dubai references for the T2 tower massing. These are links only: no photos were downloaded or committed.
- Burj Khalifa: spiralling setbacks, tapering. https://www.som.com/projects/burj-khalifa/
- Jumeirah Emirates Towers: a pair of unequal height with sloped, jagged tops. https://en.wikipedia.org/wiki/Emirates_Towers
- Almas Tower: two offset volumes on one core. https://www.skyscrapercenter.com/dubai/almas-tower/298
- Address Sky View: twins of unequal height with a sky bridge. https://www.skyscrapercenter.com/complex/895
- Cayan Tower: 90° twist, 1.2° per floor (not used). https://en.wikipedia.org/wiki/Cayan_Tower
