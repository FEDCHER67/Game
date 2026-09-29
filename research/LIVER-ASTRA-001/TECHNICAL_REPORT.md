# LIVER-ASTRA-001 — colorful cartoon organ-family pass

## Source and scope

This pass started from the existing approved/current `LIVER-ASTRA-001.blend`; it did not rebuild the liver. The pre-pass blend, FBX, report, and previews are preserved under `Working/BeforeCartoonFamilyPass/`. The asset's underlying simplified exterior silhouette was previously adapted from Faqihcuk's liver body, with ElliotSS used only as a broad color reference; details and required attribution are in `PROVENANCE.md`. Neither source archive was reimported for this pass. The approved `LUNGS-ASTRA-001` finish guided the brighter, clean cartoon color and dry material response.

## Art changes

- Preserved the single strong readable liver mass, dominant and tapered lobes, smooth exterior, and existing depth. No gallbladder, vessels, ducts, cutaway, internal anatomy, or new secondary geometry was added.
- Changed the main body from muted brown-red to a richer, clean warm reddish-brown with a terracotta/wine-red character. The liver remains deeper and warmer than the coral lungs, distinct from the true-red heart, pink brain, and berry kidneys.
- Kept one uniform body material because this approved design has no intentional secondary object to separate. No texture, painted anatomy, or surface noise was introduced.
- Changed the studio light tints to near-neutral broad sources, with direct light specular disabled, to make color comparison with the other updated organs easier. The final previews show soft diffuse form light without a wet or polished hotspot.

| Material | Linear RGB base color | Roughness | Specular IOR level | Other response |
| --- | --- | ---: | ---: | --- |
| `01 | Matte warm cartoon terracotta liver` | `(0.275, 0.044, 0.033)` | 0.87 | 0.0 | diffuse roughness 0.68; metallic, coat, sheen 0 |

These are Blender Principled BSDF values. Unity shader conversion and in-game lighting remain integration checks.

## Geometry and export

**Geometry changes: none.** One closed, smooth-shaded game mesh remains, with **7,002 vertices, 9,865 polygons, and 14,000 triangles**. `UV0` and object transforms are unchanged. Approximate bounds remain `0.204384 × 0.066107 × 0.152384 m`; the front faces Blender `-Y`. The final blend has zero boundary edges, zero nonmanifold edges, zero degenerate faces, and finite vertex coordinates. An exact geometry, transform, polygon-material-region, and UV fingerprint matches the pre-pass blend.

Blender 5.2.1 LTS reopened the final `LIVER-ASTRA-001.blend` successfully. `LIVER-ASTRA-001.fbx` reimported with one mesh, the same name, 7,002 vertices, 14,000 triangles, smooth shading, dimensions, `UV0`, topology counts, material name, base color, roughness 0.87, and zero specular IOR level. The FBX contains only the game mesh, not the studio camera or lights. Detailed read-back data is in `Working/cartoon_validation.json`.

## Review deliverables

- `LIVER-ASTRA-001.blend` and `LIVER-ASTRA-001.fbx`.
- Six 1000 × 1000 required views: `Previews/01_front_hero.png`, `02_rear.png`, `03_left_three_quarter.png`, `04_right_three_quarter.png`, `05_side.png`, and `06_closeup.png`.
- Supplemental updated views: `06_surface_closeup.png` (compatibility copy), `07_bottom_or_underside.png`, and `08_neutral_sculpt.png`.
- Reproduction and validation: `Working/cartoon_family_pass.py` and `Working/validate_cartoon_family.py`.

The colored views were visually checked for preserved silhouette, rich warm cartoon color, and matte finish. Subjective visual approval remains with the user. No commit or push was made.