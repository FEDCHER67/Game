# Map W85 build — progress (agent CL-MAP85, branch map-v76-local, local commits only)

Source: Vadim's 2D map v85 (`ArtSource/References/Map/World_v85`, commit cf2050ee) + prompt `docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md`.
W76 (scene, builder, data) untouched; everything W85 is new.

## Done (21.10)
1. Data pipeline `Tools/MapV85` (s01, s02 roads from v85 vectors + joins/entries, s03 relief with roles, s04_* districts, s05 trees by zones,
   s06 materials + building-type slots, s06b details by rules, s07 splat) -> `Assets/OnlyVolunteers/Map/W85Build/Data/v01`.
   Fixed `common.post` = exact inverse of the raster post-shift (v76 was up to ~6 m off in the shift bands).
2. Builder `W85Build/Editor/W85Builder.cs` (menu OnlyVolunteers/Map/W85 Build) + `W85Look.cs` (i10 look stack) ->
   `Scenes/Map/Map_W85_Build_v01.unity` (build 143 s). Roof test: 349 buildings, 0 failing (ridge rays 5359, sweeps 1592).
   WaterData: River 474 areas, Lake 3, Pond 1, Bog 1, Sea 1 (+ pools). V19 palette field off in W85 material copies.
3. Play scene `Scenes/Map/Map_W85_Play_v01.unity` via `W85PlayIntegrator` (G43): capture/ops from i10, base 2 at grandpa's hut,
   own editor save slot; crowd in 7 districts with Vadim's NPC types (G44 phase 2).
4. Perf (editor, Game view, same spots): crowd distance culling 76->84 fps (meadow N of Construction), 110->119 (Hamlet), 151->172 (Downtown).
   Grass: draw distance 60/50/40 m + fade, density falloff, CPU chunk frustum/horizon culling, quality High/Med/Low/Off; grass cost ~0 fps now.
5. Smoke: compiles, map loads, player walks (18 m in 4 s), capture of a Hamlet NPC records district + type, no Console errors.
6. Reports: `docs/reports/MAP_W85_FIXED_BY_LOGIC.md`, `docs/reports/MAP_W85_FOR_VADIM.md`.

## Left
- Texture sample (one house / one street): waiting for Fedya's pick; hook ready — `Data/v01/texture_sample_v85.json`
  {"buildings": {"<id>": {"walls": "<mat path>", "roof": "<mat path>"}}} or a slot's "texture_test" in materials_v85.json, then rebuild.
- Vadim's answers (FOR_VADIM 1-18); low grass tufts / flowers; heavy NPC types have no LODs (BAD_ALTGIRL 99k tris).
