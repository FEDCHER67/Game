# Pine_Tall v02 — denser small branch clumps

G23, 2026-10-15. Blender-only revision of Pine_Tall A/B/C v01_02 in response to Fedya's request for substantially denser small branches and more leaves.

## Result

Each existing LOD0 clump now contains **17 individual folded needle plates instead of 9 (+88.9%)**. Eight additional plates overlap the open areas inside each clump. No new main branches or crown tiers were added. Trunk, limbs, dead stubs and all six trunk capsule recipes/proxies remain unchanged. The foliage retains the previous world envelope and the LeafPine/LeafDark palette.

| Variant | Height / crown width | Clumps | Leaf plates before → after | LOD0 before → after | New LOD1 / LOD2 |
|---|---|---:|---:|---:|---:|
| A | 18.50 / 4.50 m | 65 | 585 → 1,105 | 6,410 → 7,320 | 4,304 / 2,744 |
| B | 20.00 / 4.90 m | 69 | 621 → 1,173 | 6,842 → 7,808 | 4,596 / 2,932 |
| C | 17.00 / 4.20 m | 63 | 567 → 1,071 | 6,194 → 7,076 | 4,158 / 2,650 |

To stay within the existing 8,000-triangle budget, the original plate outline and raised fold use six triangles with a closed underside. The new infill plates use four triangles as closed, pointed folded lances. All foliage is opaque closed geometry, not alpha-cutout cards. LOD1 retains 9 plates per clump; LOD2 retains 5, with slightly enlarged coverage.

The existing shared V19Wind stiff material settings and remaps remain in use. `wind_bindings_v02.json` references the original staged material assets without duplicating or changing them. `prefab_recipe_v02.json` preserves the previous LOD thresholds, capsule dimensions and instance-height-scaled shared shader.

## Deliverables

- `Cozy_PineTall_v02.blend` — source geometry, 9 LOD meshes and 6 capsule proxies.
- `Models/PineTall_A_v02.fbx`, `PineTall_B_v02.fbx`, `PineTall_C_v02.fbx` — 3 LODs each, metres, base pivot.
- `Cozy_PineTall_Preview_v02.blend` — Hamlet studio lighting and comparison layout.
- `C:/Dev/Game/Working/Reviews/Trees/pine_tall_v02.png` — common-scale lineup and same-camera before/after clump close-ups.
- `Preview/PineTall_A_crown_v02.png` — additional upper-crown close-up.
- Matching build, render, sheet and validation scripts/logs, plus the JSON validation and recipe files.

All previous Pine_Tall files and the previous preview sheet remain preserved. Approved umbrella pine, Forest fir and poplar sources are read-only comparison references.

## Verification

**PASS — Blender 5.2.1 LTS build and topology checks.**

Command from `C:/Dev/Game`:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v02/build_pine_tall_v02.py
```

Evidence: `build_attempt02_v02.log`, `validation_v02.json`. All 9 meshes have zero non-manifold edges, loose vertices or degenerate polygons; LOD0 stays below 8k triangles. Each woody mesh has the same canonical geometry hash as the previous deterministic build. Source generation preserves previous height/crown bounds. Source/export files refuse overwrite.

The first build attempt stopped before model/export creation because Blender's library loader replaced material-name list elements with Material objects. Fixed by using the returned Material objects directly. Initial diagnostic remains in `build_v02.log`; the successful run is `build_attempt02_v02.log`.

**PASS — exported FBX roundtrip.**

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v02/validate_roundtrip_v02.py
```

Evidence: `roundtrip_v02.log`, `fbx_roundtrip_v02.json`. Three FBX files reimported: all 9 LODs match counts and dimensions within 1 mm, base origins and unit scale, closed geometry, UVs and shared material remaps. Six capsule recipes valid. All 488 protected prior deliverables, tree assets and map scene files were hash-identical to the start of this revision.

**PASS — actual Blender renders and visual inspection.**

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python ArtSource/Dev/Trees_staging/pine_tall_v02/render_preview_v02.py
python ArtSource/Dev/Trees_staging/pine_tall_v02/make_sheet_v02.py
```

Evidence: `render_v02.log`, `preview_manifest_v02.json`, `sheet_manifest_v02.json`, rendered PNGs. Compared the new clumps with the v01_02 render at identical camera/lighting/scale: more overlapping plates, fuller small tufts, retained gaps between major branches and bare lower trunk. The final comparison sheet was visually inspected.

Blender MCP could not connect; used the documented local background-Blender fallback. No new package, renderer or material dependency.

**NOT RUN — Unity import, Play, wind motion and i10 placement.** This request is Blender-only. Unity, its lock and map scenes were not operated. No commits or review bridge. Visual approval of `pine_tall_v02.png` is the remaining step; placement still requires the lead's separate go.
