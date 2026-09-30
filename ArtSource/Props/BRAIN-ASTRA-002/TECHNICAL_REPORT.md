# BRAIN-ASTRA-002 — colorful cartoon organ-family pass

## Source and scope

The approved `BRAIN-ASTRA-002.blend` was the working source for this pass. Its prior blend, FBX, report, and previews were copied to `Working/BeforeCartoonFamilyPass/`. The original supplied source remains `Working/Tripo/pink brain 3d model.fbx`; it was not reimported or used to rebuild the asset. `BRAIN-ASTRA-001` was not used. The approved `LUNGS-ASTRA-001` finish guided the brighter, clean color and dry matte response.

## Visual changes

- Kept the approved rounded silhouette, large gyri, distinguishable front and rear, and short depth-oriented brain stem. No sculpting, new anatomy, separate cerebellum, or veins were added.
- Changed the main body from muted peach pink to a more colorful warm cartoon peach-pink. It remains intentionally pinker than the lungs and is distinct from the heart's true red.
- Assigned a second, slightly deeper coral-rose material to 211 existing lower stem polygons. The color boundary sits under the brain mass; it does not make the stem a separate object or alter geometry.
- Changed the three broad preview lights to near-neutral white, warm-white, and cool-white. Direct light specular remains disabled. The six final renders were visually checked for color, fold readability, stem visibility, and a dry surface.

| Material | Region | Linear RGB base color | Roughness | Specular IOR level |
| --- | --- | --- | ---: | ---: |
| `01 | Cartoon warm peach-pink brain` | main brain mass; 4,659 polygons | `(0.660, 0.190, 0.230)` | 0.86 | 0.0 |
| `02 | Matte deeper coral-rose stem` | lower stem; 211 polygons | `(0.540, 0.140, 0.165)` | 0.87 | 0.0 |

Both are solid-color Principled BSDF materials with diffuse roughness 0.68 and metallic, coat, and sheen set to zero. There are no image textures. Color was increased without adding gloss; the previews show broad diffuse form light without a sharp or wet highlight. These are Blender material values; appearance after Unity shader conversion remains a game integration check.

## Geometry and topology

**Geometry changes: none.** The asset remains one smooth-shaded game mesh with **4,138 vertices, 4,870 polygons, and 8,296 triangles**. Its bounds are approximately `0.1563 × 0.1599 × 0.1546 m`, with identity object transforms and the front facing Blender `-Y`. A geometry and transform fingerprint of the final blend exactly matches the pre-pass blend, excluding intentional material assignments.

The inherited mesh has **2 boundary edges and 24 nonmanifold edges** in both pre-pass and final versions. They cause no visible defect in the six views, so no topology surgery was performed. No degenerate faces or non-finite vertex coordinates were found. The mesh is not claimed to be watertight.

## Deliverables and validation

- Canonical source: `BRAIN-ASTRA-002.blend`.
- Game mesh export: `BRAIN-ASTRA-002.fbx`; only the brain mesh is exported, excluding studio lights and camera.
- Six 1000 × 1000 renders: `Previews/01_front_hero.png`, `02_rear.png`, `03_left_three_quarter.png`, `04_right_three_quarter.png`, `05_side.png`, and `06_closeup.png`. Older preview filenames are kept as refreshed compatibility copies.
- Reproduction and validation: `Working/cartoon_family_pass.py`, `Working/validate_cartoon_family.py`, and `Working/cartoon_validation.json`.

Blender 5.2.1 LTS reopened the final `.blend` successfully. The exported FBX reimported successfully with one mesh, the same 4,138 vertices and 8,296 triangles, identical bounds and inherited topology counts, and both material names, face assignments, base colors, and roughness values. Front/rear distinction, large folds, and the compact stem remain visible in the final renders. User visual approval is pending. No commit or push was made.