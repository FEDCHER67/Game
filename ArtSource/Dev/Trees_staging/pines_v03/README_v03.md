# G23 — Pine v03: oval crown tiers

Blender approval candidate complete. The three tiers now have upper domes and rounded undersides built from overlapping opaque folded-frond clusters. All v02 trunk and branch geometry, lean, thickening, collider recipes and shared wind settings are preserved. Approved oaks are unchanged.

## Final files

- `Cozy_Pines_v03_02.blend`: final A/B/C models, LOD0/1/2, copied trunk capsule proxies, hidden oval guides and v02 references.
- `Models/Pine_A_v03_02.fbx`, `Models/Pine_B_v03_02.fbx`, `Models/Pine_C_v03_02.fbx`.
- `Cozy_Pines_Preview_v03_02.blend`: comparison studio.
- `C:/Dev/Game/Working/Reviews/Trees/pines_v03.png`: current placeholder | Pine v02 A | Pine v03 A/B/C | approved Oak A, with a true side-view close-up and all requested measurements.

The first v03 pass is retained as a diagnostic. Its upper tiers were too open in the render. Final v03_02 fills their interiors and increases overlap, preserving the same triangle counts and protected wood. Only v03_02 is the final selection.

## Dimensions and the tier-width assumption

All variants retain **12.986 m height and 6.861 m overall crown width**. Foliage spans **7.799–12.986 m**, the upper **39.9%** of the tree. Each tier is an individual flattened oval with a ragged leafy edge. There is no smooth crown blob or solid hidden crown shell.

To fit three separated lenses within the requested upper 35–40% of a 12.986 m tree, the upper tiers are narrower than the lower tier. Three tiers each 6.861 m wide and 1:3 in height/width would require at least 6.861 m of vertical space before gaps, exceeding that envelope. This candidate keeps the full width on the lower tier and tapers the upper two. This interpretation was stated during work and is visible in the sheet for Fedya's review.

| Tier | Width | Height | Height : width |
|---|---:|---:|---:|
| Lower | 6.861 m | 2.287 m | 1 : 3.00 |
| Middle / upper | 3.60–3.70 m | 1.250 m each | 1 : 2.88–2.96 |

Middle/upper widths swap in B. All tier envelopes have 0.20 m minimum vertical clearance, with small horizontal offsets. Local leafy edges and curved profiles make the visible gap vary across the silhouette. Existing branches remain visible in those gaps; some unchanged twig tips extend through the narrower upper foliage edges.

## Density and budgets

| Variant | Clusters v02 → v03 | LOD0 triangles | LOD1 triangles | LOD2 triangles |
|---|---:|---:|---:|---:|
| A | 42 → 72 | 6,852 | 3,654 | 2,374 |
| B | 50 → 76 | 7,268 | 3,878 | 2,534 |
| C | 42 → 72 | 7,428 | 4,230 | 2,374 |

Clusters are distributed above, below and within each oval. Each LOD0 cluster has 10–11 closed folded fronds. The same primitive used in approved v04 and Pine v02 is reused; no original builder is executed. The later LODs reduce fronds per cluster while retaining all tier envelopes and their gaps.

The bark polygons are copied directly from each corresponding v02_02 LOD, rather than reconstructed. Canonical geometry hashes match for all nine wood meshes. This preserves every trunk, root, main limb and smaller branch at exactly the same coordinates, including the approved +15% thickness and lean. The six capsule proxies and collider recipes are copied unchanged. The FBX files contain render LOD meshes; Unity components are deferred.

## Palette and wind

Unchanged Bark `#68503C`, LeafDark `#3A6E38`, LeafPine `#2C6042`. `wind_bindings_v03.json` reuses the existing staged Pine materials in `../oaks_pines_v01/WindMaterials/`, on `OnlyVolunteers/Wind/v02/GenericFoliage`, with response `0.028` and median-size flexible height `17.531229 m`. No material, shader or global wind setting was changed. Instance-height stiffness and actual motion remain for a separately authorized Unity integration.

## Verification

- **PASS — geometry, dimensions and budget:** `build_pines_v03_02.py`, `build_v03_02.log`, `validation_v03_02.json`. Nine LOD meshes have no nonmanifold edges, loose vertices or degenerate faces. Base pivots, height and crown width passed. All LOD0 counts are below 7,500 triangles. `woodChecks` records exact matching bark-geometry hashes for every LOD.
- **PASS — FBX round trip:** `validate_roundtrip_v03_02.py`, `roundtrip_v03_02.log`, `fbx_roundtrip_v03_02.json`. Three FBX files reimported into fresh Blender scenes; all nine meshes passed counts, dimensions to 1 mm, identity scale, base pivots, UV presence, closed topology and material remaps. Six capsule recipes passed validation.
- **PASS — preservation:** all 2,168 files in `protected_before_v03.json` retained their SHA-256 hashes, including prior oaks/pines, approved source assets and protected Unity files.
- **PASS — rendered inspection:** the final lineup and side view were visually inspected. The lineup uses the prior Hamlet studio lighting and 72 pixels per metre for every tree. The side close-up is orthographic at crown height, without looking up/down. The current placeholder is the same representative pine_a scaled to the map-family median; approved Oak A and Pine v02 A are unchanged references, not regenerated models.
- **NOT RUN — Unity:** no import, shader compile, wind animation, Play tests, scene edits or lock acquisition. No commits and no review bridge.

## Execution

Blender MCP could not connect, so the fallback was installed **Blender 5.2.1 LTS** in background processes. No live Blender scene was modified. Commands from `C:/Dev/Game`:

```powershell
python ArtSource/Dev/Trees_staging/pines_v03/prepare_v03.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v03/build_pines_v03.py
python ArtSource/Dev/Trees_staging/pines_v03/prepare_render_v03.py
python ArtSource/Dev/Trees_staging/pines_v03/refine_v03_02.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v03/build_pines_v03_02.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v03/validate_roundtrip_v03_02.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v03/render_preview_v03_02.py
python ArtSource/Dev/Trees_staging/pines_v03/make_sheet_v03.py
```

Generation refuses to overwrite existing numbered deliverables; use a new revision when regenerating. Render logs include non-fatal Blender deprecation/HIP-library warnings; accepted final renders and preview saves completed. The open item is **Fedya's visual approval**, particularly the narrower upper tiers needed to fit the requested oval proportions and height envelope.
