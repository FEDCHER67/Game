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

If CC0 sets (ambientCG, Poly Haven) are added later, record each one here: asset ID, URL, licence (CC0), the date it was downloaded, and how it was adapted (palette, contrast, scale).
