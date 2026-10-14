# G24 — tall grass / Unity Grass Instancer v01

Date: 14 October 2026, Europe/Moscow. Worker: G24. Project: `C:/Dev/Game`. Brief: `C:/Users/Zeyo-ne/.ai-bridge/app_briefs/G24_grass_instancer.md`.

**Work in progress: download, licence, unchanged-source integrity and staged C# compilation PASS. Unity integration, GPU verification, captures and frame-time measurements are pending the shared lock. This document will be completed with actual evidence before review.**

## Source and licence

- Repository: https://github.com/MangoButtermilch/Unity-Grass-Instancer
- Pinned commit: `f5983739d6159dbad115950e9ac349a1dd44e78e`.
- Licence: MIT, copyright (c) 2022 MangoButtermilch. The pinned LICENSE was read and checked. Full notice is retained in both the source and staged port.
- Untouched source: `ArtSource/ThirdParty/MangoButtermilch_GrassInstancer/v01/source/`.
- Download archive: `ArtSource/ThirdParty/MangoButtermilch_GrassInstancer/v01/upstream_f5983739d6159dbad115950e9ac349a1dd44e78e.zip`.
- Archive SHA256: `5284359f66b4d1e27490103d90a0b67b504e8d80f587a612e7ac47199e44a7ed`.
- `PROVENANCE.md` includes URL, commit, date and the complete MIT text. Integrity check compared all 234 extracted files against the archive: zero mismatches. Evidence: `ArtSource/Dev/Grass_staging/evidence/upstream_integrity_v01.json`.
- No downloaded code was executed. No upstream models, textures, images or showcase assets are included in the runtime port. The 3-triangle blade is original project geometry.

## Selected approach and scoped implementation

Approach **3 — frustum culling + chunking** is the foundation. This finite map needs authored district placement; infinite regeneration is unnecessary. The port retains the source-buffer/chunk-buffer/visible-append/indirect-count design, with 16 m chunks and a compact 32-byte blade record plus 4-byte visible ID. GPU work uses one 64-thread group per chunk. It corrects the source's corner-only frustum test and extra-instance loop endpoint, adds conservative bounds and exact tail checks, and removes synchronous gameplay GPU readbacks.

Occlusion culling is **disabled**. Approach 5 samples only four chunk corners at depth mip 0 and its README lists mip levels and shadow-cascade artifacts as unfinished work. It was inspected but not imported. Frustum/distance culling is the selected scoped solution; no unmeasured occlusion benefit is claimed.

The shader uses `Graphics.RenderMeshIndirect` and `UnityIndirect.cginc`. Grass material properties are intentionally outside `UnityPerMaterial`, so only the grass shader opts out of SRP Batcher. Per-camera property blocks and buffers keep the render data independent. No global URP/SRP setting change is required or authorized. References: [Unity indirect rendering API](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Graphics.RenderMeshIndirect.html), [Unity SRP Batcher incompatibility guidance](https://docs.unity3d.com/6000.0/Documentation/Manual/SRPBatcher-Incompatible.html).

The additional tall layer does not edit the terrain's FreeStylized Grass 01 texture, TerrainData detail maps or existing short tufts. It receives main-light shadows and URP fog. Matching opaque depth and depth-normal passes are included for the map's depth-based atmosphere. Grass does not cast shadows. Actual G18g horizon integration remains to be verified after the map handoff.

## Files

Complete staged import set under `ArtSource/Dev/Grass_staging/v01/`:

| Source | Intended destination / purpose |
| --- | --- |
| `ThirdParty/ChunkedGrassRenderer24.cs` | `Assets/OnlyVolunteers/ThirdParty/GrassInstancer_MB/`; adapted chunked indirect renderer and GPU buffer ownership |
| `ThirdParty/GrassVisibility24.compute` | Same; conservative chunk and blade frustum/distance culling |
| `ThirdParty/TallGrass24.shader` | Same; broad blade gradient, travelling gusts, patches, light/fog/depth |
| `ThirdParty/LICENSE.txt`, `PORT_NOTES.md` | MIT notice and exact adaptation/source map |
| `Grass/GrassPatchData24.cs` | `Assets/OnlyVolunteers/Map/Grass/`; immutable editor-baked placement |
| `Grass/GrassPerformance24.cs` | Same; explicitly started temporary Play benchmark, not a saved scene component |
| `Grass/Editor/GrassPlacement24.cs` | New-only mesh/material/data and scene revision creation |
| `Grass/Editor/GrassExclusion24.cs` | Actual hard geometry, building footprints and paved-yard masks, based on the existing project's low-grass rasterizer |
| `Grass/Editor/GrassReview24.cs` | Matched before/after captures and benchmark entry point |
| `Grass/Editor/GrassVerification24.cs` | GPU boundary regression, shader/SRP status and placement audit |

Additional staging-only helpers: `compile_staging_v01.py`, `install_new_only_v01.py`, `make_review_sheet_v01.py`, `README_v01.md`, and `evidence/`. Runtime Assets are not installed until G24 owns the lock and Unity import is paused for the complete set.

## Settings and assumptions

- Blade geometry: 3 triangles, broad base, tapered middle/tip, random yaw; width 0.085–0.15 m.
- Tall meadow height: 0.50–0.90 m. Roadside: 0.10–0.25 m with reduced density. Trimmed lawns: 0.12–0.24 m. Rough: 0.22–0.48 m; Beach: 0.28–0.55 m.
- 0.5 m candidate grid with jitter and small blade groups. Approximately 20 m irregular macro patches plus smaller open pockets; deterministic hash seed logic. Fields are not covered uniformly.
- 16 m chunks; 150 m view distance, smoothly reducing height during the final 20 m into the retained low layer.
- Wind: direction `(0.84, 0.54)`, strength 0.24, speed 1.25; a travelling main wave modulates gusts, with a smaller cross-ripple. Root position remains fixed.
- Palette uses the actual v19 district `t` values through its existing continuous blend field, rather than an independent district palette. Rough clumps are yellow-grey and dunes are muted straw-green.
- Confirmed map IDs: `village` = Hamlet, `fields` = Quiet Valley, `transition` = construction district, `residential` = Rough District, `old_town` = Downtown. Quiet Valley/Elite interiors use trimmed grass; tall edges occupy their outer 18 m. Downtown uses park-grass splats only. Forest uses meadow splats outside baked tree canopy cells. Construction, Port and island use sparse density.
- The placement uses actual road/water/retaining geometry, actual relocated building footprints, and plan paving/yard polygons. A dilated 0.5 m mask produces a 1 m clearance field. Roadside trimming applies within 4.5 m of a hard surface. Water, steep terrain above 34 degrees and submerged/low shoreline points are rejected.
- Dry sand above the water threshold is treated as eligible dune ground. This is an explicit interpretation in the absence of a dedicated dune-grass mask.
- Purely local visual rendering; no physics or network behavior. Optional player/van bending is omitted to prioritize integration and verification.
- Existing deliverables and `.meta` identities are preserved. Scene integration will create new numbered revisions. No commits, Git staging, pushes, deletions, WORK_SYNC edits, ProjectSettings edits or background-setting changes are authorized.

## Verification so far

| Check | Status / evidence |
| --- | --- |
| Fixed-commit download and MIT check | PASS; provenance and integrity evidence above |
| Extracted source unchanged | PASS; all 234 files match the archive |
| C# runtime and editor staging compile | PASS; `python ArtSource/Dev/Grass_staging/compile_staging_v01.py`; pinned Unity 6000.5.11f1 / URP 17.5.0 references; `evidence/compile_v02.txt`. One reference-version warning CS1701, no C# errors |
| Unity import / GPU shader compilation | NOT RUN — awaiting shared Unity lock |
| GPU culling boundary regression | NOT RUN — prepared in `GrassVerification24.GpuCulling` |
| Full placement and chunk audit | NOT RUN — requires baked scene |
| Global SRP Batcher still enabled / grass opt-out | NOT RUN in Unity; protected disk hashes recorded |
| Five before/after capture pairs and six wind frames | NOT RUN — no generated/fake evidence |
| Hamlet and between-districts frame-time comparison | NOT RUN — no invented frame-time or count values |
| G24 review bridge | NOT RUN — required after Unity work |

## Remaining work

Acquire Unity, verify the current map/aerial revision, import the complete staged set, compile shaders, bake and audit the layer, inspect the five required views, measure live Play frames and culling, save the new scenes, restore the initial scene, release the lock and run the review bridge. Any review fix requests will receive at most two fix rounds.
