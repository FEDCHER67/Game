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

## Texture sample (texture test v04, approved by Fedya 21.10) — applied
- `Data/v01/texture_sample_v85.json` + builder step "texture sample" (copies from TextureTest_Houses_v04 with their own Built_v04 materials):
  H5a log house (scheme a) at (230, 562) replacing 02-H01; R2c khrushchevka section = east 25.6 m of H13 at (835, 743) (west part stays W85);
  D4 street face with G-D glazing, north side of Hnw x 825-868 (replaces 05-B029..B032); N-R3 night light on the 5 urban lamps within 45 m
  of R2c / D4 (only these on the night rig). Towers untouched (T4 in progress). Fog +18 % not applied map-wide yet.
- Shots: w85_sample_H5a / R2c / D4 / R2c_night.png. Hamlet yard clutter without an asset is no longer drawn as grey boxes (pilot-kit props where they exist).

## v04 look rollout + fixes (21.10, Fedya: "раскатывай")
- `W85Build/Editor/W85Rollout.cs` (partial W85Builder): H5 log houses on all 24 Hamlet houses (HH_House_v03 fitted to the footprint,
  trim a/b/c + dark roof tints per house), R2c on all 27 khrushchevkas (any length / floors, arches), D4 on all 122 Downtown blocks
  (faces from the plan: street / party / yard), shared Built_v04 materials only (+6 HH roof tints). Single-house samples removed;
  `texture_sample_v85.json` keeps only T4 (twins on the Water-axis plaza, podium fitted, mesh colliders, LOD).
- Third tower (05-B018 round glass tower + podium) -> 8-floor corner block (`Tools/MapV85/s04z_owner_decisions.py`); glass offices 8 floors.
- N-R3 on all 142 urban lamps (flicker + shadowed spot, `W85LampShadowBudget`: 8 nearest spots cast shadows); no lamps in the Hamlet.
- Fog x1.08 map-wide (W85Look). Floating roofs: kit porch roof was placed 2.3 m up -> on the ground; `W85FloatCheck` over map + play
  scene (0 floaters; regression-checked against the old bug). Grandpa yard props (`Art/Props/GrandpaYard_v01`) at base 2.
- Build 174 s; roof test 321 buildings, 0 failing; play smoke: no new errors, 123 fps at the base-2 spawn (editor).
- Shots: w85_v04_hamlet / rough / downtown.png, w85_t4_plaza / distance.png, w85_base2_yard.png.
- Depends on Art/TextureTest_v01/Built_v04 (approved, do not rebuild TT v04: new GUIDs would break the W85 references).

## Left
- Vadim's answers (FOR_VADIM 1-18); Construction / Port / Beach / Elite / Quiet Valley / Tramduro keep the earlier approved materials
  (no v04 code for them); low grass tufts / flowers; NPC type LODs.
