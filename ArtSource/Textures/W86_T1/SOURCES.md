# W86 texture agent T1 - sources (2026-10-22)

All downloaded sets are **CC0 1.0** (ambientCG, https://docs.ambientcg.com/license/ - public domain, commercial use, no attribution
required). Format: 1K-JPG zip from `https://ambientcg.com/get?file=<ID>_1K-JPG.zip`; kept Color, NormalGL, Roughness, Opacity,
Metalness and the preview PNG only. Folder: `ambientCG/<ID>/`. (12 more sets were downloaded for the comparison and deleted unused.)

| ID | page | used for |
|---|---|---|
| WoodSiding005 | https://ambientcg.com/view?id=WoodSiding005 | T1_boards_red (wagon teplushka) |
| WoodSiding007 | https://ambientcg.com/view?id=WoodSiding007 | T1_boards_green, T1_boards_dark (sheds) |
| WoodSiding009 | https://ambientcg.com/view?id=WoodSiding009 | T1_siding_cream (hut c) |
| Planks023A | https://ambientcg.com/view?id=Planks023A | T1_boards_grey / whitewash / green_chipped |
| Planks037A | https://ambientcg.com/view?id=Planks037A | T1_boards_tar |
| Planks037B | https://ambientcg.com/view?id=Planks037B | T1_boards_warm |
| Bark007 | https://ambientcg.com/view?id=Bark007 | T1_bark_birch |
| Bark012 | https://ambientcg.com/view?id=Bark012 | T1_bark_brown |
| ThatchedRoof001A | https://ambientcg.com/view?id=ThatchedRoof001A | T1_haybale_* (straw wrap) |
| Ground048 | https://ambientcg.com/view?id=Ground048 | T1_bank_mud, T1_field_plowed_c |
| Ground103 | https://ambientcg.com/view?id=Ground103 | T1_field_plowed_b, stubble soil |
| Gravel023 | https://ambientcg.com/view?id=Gravel023 | T1_ballast_grey / brown |
| Rocks022 | https://ambientcg.com/view?id=Rocks022 | T1_bank_pebbles, gabion stones |
| PaintedMetal004 | https://ambientcg.com/view?id=PaintedMetal004 | T1_painted_metal (neutral), steel plates |
| PaintedMetal006 | https://ambientcg.com/view?id=PaintedMetal006 | T1_metal_green / grey / blue_rust |
| Rust009 | https://ambientcg.com/view?id=Rust009 | rust colour in rust_sheet, galv_rust, garage doors |
| CorrugatedSteel002 | https://ambientcg.com/view?id=CorrugatedSteel002 | T1_rust_sheet (profiled sheet ribs) |
| Tiles036 | https://ambientcg.com/view?id=Tiles036 | T1_tile_facade (Soviet shop) |
| Tiles107 | https://ambientcg.com/view?id=Tiles107 | T1_tiles_white, tunnel tiles |
| Bricks094 | https://ambientcg.com/view?id=Bricks094 | T1_brick_red (church b, water tower shaft) |
| Concrete034 | https://ambientcg.com/view?id=Concrete034 | plaster_grey, concrete_light, panel_p5, bridge, slabs, PO-2, tunnel |
| Concrete019 | https://ambientcg.com/view?id=Concrete019 | T1_shotcrete |
| RoofingTiles002 | https://ambientcg.com/view?id=RoofingTiles002 | T1_shingle_wood (wooden church roof) |
| PaintedPlaster015 | https://ambientcg.com/view?id=PaintedPlaster015 | T1_plaster_whitewash |

Reused (already in the repo, CC0, see `ArtSource/Textures/ambientCG_2026-10-22/SOURCES.md`): Wood087 (logs, debarked log),
CorrugatedSteel005 (galv_rust), Asphalt031 (roof_tar grain), Granite002A (ashlar_granite).
Project textures referenced read-only: KH3 / KH4 brick (TextureTest Built_v04), TL_worn_grass (steppe macro base), GPT atlases
RoadMarks / RoadWear / StreetUtility / OilTar / WaterFX_shore_foam (`Working/Reviews/Textures_2026-10-17/gpt_missing_v02_2026-10-18`,
cleaned copies `T1_gpt_*_clean_rgba.png`).

Font for sign words / road letters: **Oswald** (SIL Open Font License 1.1), `fonts/Oswald.ttf` + `fonts/OFL_Oswald.txt`, from
https://github.com/google/fonts/tree/main/ofl/oswald . Only generic words (POLICE, TAXI, GAS, DINER, VANS, GARAGE, OPEN 24, BUS, P, H, 24), no brands.

Own procedural (no source): logs wall, log ends, standing seam, steel plates, PO-2 rhombus / ribbed panels, P-5 panels, tunnel
tile / segments layouts, yard slabs, mosaic, chain-link (thin / thick), duckweed, foam strip / ring / spray, field furrows / stubble,
steppe macro, hay spiral, garage door atlas, road marks / wear atlases, neon hearts, danger plate, hazard / barrier stripes, grille, flag cloth.

Generator: `tools/gen_textures_t1.py` -> `Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Textures/` (1024 px; 2048 for door / decal atlases).
Adaptation to the One-Armed Robber look: median + light blur (grain off), high-pass (grime off), contrast compressed toward a painted
mean, colour from luminance (recolour) or cleaned hue; normals NormalGL softened or own from height.
