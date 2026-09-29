# BRAIN-ASTRA-001 technical report

## Deliverables

- `BRAIN-ASTRA-001.blend`: editable Blender 5.2 source with two game meshes and a separate, unexported studio collection.
- `BRAIN-ASTRA-001.fbx`: game mesh export, with no cameras or lights.
- `Working/build_brain_astra.py`: deterministic geometry, material, studio, render, and export builder.
- `Working/validate_brain_astra.py`: independent reopen and FBX round-trip checks.
- `PROVENANCE.md`: original-construction and visual-reference record.
- `Previews/01_front_hero.png`, `02_rear.png`, `03_left_three_quarter.png`, `04_right_three_quarter.png`, `05_side.png`, `06_top.png`, `07_fold_closeup.png`, `08_underside_cleanup.png`, `09_neutral_sculpt.png`.

## Art construction

The asset contains two readable cerebral hemispheres, with a narrow top sagittal fissure and softly meeting lower masses. Each closed ovoid is shaped with low-frequency asymmetry. Twenty main irregular sulci per side, three additional crown valleys, four broad outer-side valleys, and shorter lateral branches displace the mesh inward; broad shoulders around the paths round the intervening gyri. The paths terminate independently rather than forming concentric rings. The lower closure is broad and compact, with no stem, stalk, brainstem, cerebellum, stand, or dangling anatomy. Both meshes have `UV0`. The neutral preview isolates the sculpt from color.

The heart's actual Blender scene was inspected as the primary finish reference, followed by the approved kidney scene. The heart myocardium uses roughness `0.53`, specular IOR level `0.452`, coat `0.066`, and subsurface `0.078`. This brain is intentionally drier: muted warm dusty rose linear base color `(0.39, 0.155, 0.16)`, Principled roughness `0.79`, specular IOR level `0.035`, subsurface weight `0.015`, diffuse roughness `0.65`, and zero metal/coat/sheen. The kidney's rougher, suppressed-specular finish was the secondary guide. There is **one shared material**, no texture maps, and no external file dependencies.

The family dark blue-gray world color is `(0.0165, 0.0235, 0.0365)` at `0.48` strength. The three diffuse disk lights retain the heart's palette: key energy `1.86`, size `0.201`, color `(1.000, 0.987, 0.977)`, position `(-0.15, -0.13, 0.20)`; rim `1.31`, `0.146`, `(0.735, 0.823, 1.000)`, `(0.08, 0.16, 0.16)`; warm fill `0.775`, `0.147`, `(1.000, 0.817, 0.703)`, `(0.18, -0.07, 0.055)`. Their specular factors are zero. The rear preview alone enables a diffuse disk fill at `(0.02, 0.22, 0.08)`, energy `0.9`, size `0.18`; the underside preview alone enables one at `(0, -0.12, -0.18)`, energy `1.5`, size `0.20`. Both use zero specular factor and remain disabled in the saved source.

Blender scene uses meters, Cycles at `96` samples for final renders, AgX with neutral look, an orthographic review camera framed on the front hero (`0.215` scale), and opaque dark studio backgrounds. The source has **8 objects**: two game meshes, one camera, and five lights. The neutral sculpt is a render-only material override applied after source save and FBX export. FBX export completed and includes only the two game meshes, their `UV0` layers, and the shared material; no studio objects were exported.

## Validation

Blender 5.2.1 LTS reopened the saved `.blend` and imported the FBX into an empty scene. Both formats contain exactly two meshes and one shared material, totaling **20,948 vertices and 41,888 triangles**. Each source and imported mesh has zero boundary edges, zero nonmanifold edges, zero degenerate faces, positive signed volume (outward normals), and `UV0`. Source and FBX geometry counts match. Source material override is unset, the review camera opens at `(0.067, -0.300, 0.105)` with `0.215` orthographic scale, and the rear and underside fills are disabled in the saved scene. Both lowest mesh coordinates remain above `-0.039 m`; the side and underside previews show a compact lower closure without a stalk. The crown folds are deliberately broader and softer than the front folds; their final strength requires human visual acceptance in game lighting.

Run `blender --background --factory-startup --python Working/validate_brain_astra.py` from the asset directory to repeat the source reopen and FBX round-trip checks. Final previews were viewed at full resolution, including neutral sculpt, fold closeup, side profile, and underside.

## Scope

Blender and FBX checks cover the local asset. Unity import, game lighting, runtime performance, and subjective visual acceptance require in-project/human review. No commit or push was performed as part of this asset work.
