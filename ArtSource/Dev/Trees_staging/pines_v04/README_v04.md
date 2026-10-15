# G23 — Pine v04: connected, ragged crowns

Blender approval candidate complete. A/B/C retain three dominant oval lobes, now joined by smaller needle sprigs on short twigs. Lobe outlines are lumpy and offset; cluster sizes, tilt and projection lengths vary more. Broader upper lobes reduce the taper of v03. The original trunks, roots, limbs, lean and +15% thickness remain unchanged.

## Deliverables

- `Cozy_Pines_v04.blend`: final A/B/C models, three LODs each, copied trunk capsule proxies, hidden lobe guides and v03 source references.
- `Models/Pine_A_v04.fbx`, `Models/Pine_B_v04.fbx`, `Models/Pine_C_v04.fbx`.
- `Cozy_Pines_Preview_v04.blend`: the comparison studio.
- `C:/Dev/Game/Working/Reviews/Trees/pines_v04.png`: current placeholder | Pine v03 A | Pine v04 A/B/C | approved Oak A, with a side-view close-up and triangle counts.
- Build, validation, rendering and sheet scripts plus their logs are included in this folder. The top-view inspection render is `Preview/Pines_topcheck_v04.png`.

No earlier numbered deliverable was overwritten. Approved Oak A/B/C were not rebuilt or re-exported.

## Crown changes

Each tree has **12 bridging sprig clusters on 12 short new twigs**, staggered in height and azimuth between the dominant lobes. Sprigs overlap the adjacent lobe foliage; the remaining openings are uneven pockets instead of continuous horizontal bands. These additions are smaller foliage connections, not new large tiers.

Each tree also has **three larger edge tufts**. The main clusters vary in scale and tilt, with asymmetric radial lobes, varied elevations, and differently offset upper masses. The foliage is no longer projected onto a uniform ellipsoid shell. Main upper-lobe widths are approximately **5.16–5.74 m**, versus 3.60–3.70 m in v03, with different offsets in A/B/C. Local folded-frond edges and pockets remain visible.

The overall envelope remains **12.986 m high × 6.861 m wide**. All foliage is within **7.792–12.986 m**, the upper **40%**. Capsule recipes and the stiff shared Pine material bindings are unchanged. All original bark polygons were copied directly from the corresponding v03_02 LOD; geometry hashes verify their exact preservation. The only added wood is the 12 sprig-support twigs, rooted at points on existing bark surfaces. LOD0 twig lengths range from **0.16 to 0.96 m** across A/B/C.

## Counts and budgets

| Variant | Clusters v03 → v04 | LOD0 triangles | LOD1 triangles | LOD2 triangles |
|---|---:|---:|---:|---:|
| A | 72 → 87 | 7,788 | 4,206 | 2,806 |
| B | 76 → 91 | 7,596 | 4,430 | 2,966 |
| C | 72 → 87 | 7,788 | 4,206 | 2,806 |

Cluster totals include the three main lobe populations, 12 bridge sprigs and three larger tufts. Main-cluster frond counts were redistributed to make room for the connections within the 8,000-triangle LOD0 limit. LOD1/2 preserve every lobe, bridging cluster and tuft, reducing individual fronds while increasing their coverage. All foliage is closed, opaque folded geometry; there is no alpha-card or hidden smooth crown blob.

## Materials, colliders and units

Existing palette: Bark `#68503C`, LeafDark `#3A6E38`, LeafPine `#2C6042`. `wind_bindings_v04.json` points to the unchanged Pine materials in `../oaks_pines_v01/WindMaterials/` on `OnlyVolunteers/Wind/v02/GenericFoliage` and the existing shared V19Wind include. Response remains `0.028`, flexible height `17.531229 m` at this median size. No shader, material or global gust setting was modified.

Models use metres, identity scale and ground pivots. Each FBX includes LOD0/1/2 render meshes. Six capsule proxies are in the native blend and their unchanged recipes are in `validation_v04.json`; Unity components and actual wind testing remain deferred.

## Verification

- **PASS — build, topology, dimensions and budget:** `build_pines_v04.py`, `build_v04.log`, `validation_v04.json`. All nine meshes passed the budget, zero nonmanifold/loose/degenerate geometry checks, base pivots, height and crown width. `woodChecks` records identical original bark-face hashes and separately counts the added twig triangles.
- **PASS — FBX round trip:** `validate_roundtrip_v04.py`, `roundtrip_v04.log`, `fbx_roundtrip_v04.json`. Three FBX files imported into fresh Blender scenes. All nine LOD meshes passed counts, dimensions to 1 mm, identity scale, base pivots, UV presence, closed topology and material mappings. All six capsule recipes passed.
- **PASS — preservation:** all **2,209** files recorded in `protected_before_v04.json` retained their SHA-256 hashes, including earlier model revisions, approved oaks and protected Unity files.
- **PASS — visual inspection:** final lineup, true side view and a top view of all three variants were inspected. The side view shows foliage bridges and irregular pockets; the top view shows uneven, asymmetric outlines and varied tuft projection. Subjective acceptance remains Fedya's decision.
- **NOT RUN — Unity:** no import, shader compile, wind-motion check, Play test, scene write or lock acquisition. No commits or review bridge.

The sheet uses the unchanged Hamlet studio light and a common orthographic lineup scale of 72 pixels per metre. Pine v03 A and approved Oak A are unchanged references; the current placeholder is the same pine_a geometry scaled to the map-family median. The side close-up is enlarged and labelled. These are Blender previews, not in-game captures.

## Execution

Blender MCP was unavailable. Installed **Blender 5.2.1 LTS** ran in background processes; the live Blender scene was not modified. Commands from `C:/Dev/Game`:

```powershell
python ArtSource/Dev/Trees_staging/pines_v04/prepare_v04.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v04/build_pines_v04.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v04/validate_roundtrip_v04.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v04/render_preview_v04.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python ArtSource/Dev/Trees_staging/pines_v04/render_topcheck_v04.py
python ArtSource/Dev/Trees_staging/pines_v04/make_sheet_v04.py
```

Model/export/render generation refuses to overwrite existing deliverables. Increment revisions before regenerating. Render logs contain non-fatal Blender deprecation/HIP-library warnings; renders and saved previews completed successfully.

**Open:** Fedya's approval of `pines_v04.png`. Integration has not started.
