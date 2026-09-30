# KIDNEY-ASTRA-001 — darker balanced cartoon color correction

## Current pass — 2026-09-29

This pass begins from the approved and previously recolored `KIDNEY-ASTRA-001.blend`. The immediately preceding blend, FBX, report, and previews are preserved in `Working/BeforeIntermediateColorPass/`; the earlier pre-cartoon version remains in `Working/BeforeCartoonPass/`. The shape was not rebuilt. The user requested a color between the preceding bright berry version and the older darker version, closer to the older one. The chosen body and tube colors are 60% of the earlier darker values plus 40% of the recent bright values in Blender linear RGB. This gives the pair a quieter warm berry-red body with muted rose tubes while retaining the cleaner cartoon palette and matte presentation.

| Material | Region | Linear RGB base color | Roughness | Specular IOR level |
| --- | --- | --- | ---: | ---: |
| `01 | Balanced warm berry kidney` | both kidney bodies | `(0.19710, 0.02395, 0.03260)` | 0.88 | 0.0 |
| `02 | Balanced muted rose ureter` | one descending tube per side | `(0.34700, 0.12940, 0.12200)` | 0.89 | 0.0 |

Both are solid-color Principled BSDF materials with diffuse roughness 0.68, metallic 0, coat 0, and sheen 0. Their colors are separate material regions within each integrated side mesh. The three broad near-neutral preview lights retain zero specular contribution. The six main previews and three detail/neutral views were rerendered; they show clear body/tube separation and broad diffuse shading without wet or plastic shine. No texture images are used. Unity shader conversion remains a game integration check.

## Geometry and export

**Geometry changes: none.** Exactly two stylized bean-shaped kidneys remain, with slight asymmetry, readable medial hilums, and exactly one simple descending tube from each. There is no central bundle, bladder, lower organ, adrenal cap, or cutaway. The two integrated side meshes total **18,209 vertices and 36,410 triangles**: left 9,194 vertices / 18,384 triangles, right 9,015 vertices / 18,026 triangles. Both retain `UV0`, identity transforms, and their prior material-region face assignments. A full geometry, transform, material-region, and UV fingerprint of the final blend matches the immediately preceding approved blend.

Blender 5.2.1 LTS reopened the final `KIDNEY-ASTRA-001.blend`. The final `KIDNEY-ASTRA-001.fbx` reimported with the same two mesh names, 18,209 vertices, 36,410 triangles, both `UV0` layers, both material names and colors, roughness 0.88/0.89, and zero specular IOR level. See `Working/intermediate_validation.json`. The export contains only the two game meshes; the preview studio is excluded.

## Review files

- `Previews/01_front_hero.png`
- `Previews/02_rear.png`
- `Previews/03_left_three_quarter.png`
- `Previews/04_right_three_quarter.png`
- `Previews/05_side.png`
- `Previews/06_closeup.png`
- Additional refreshed detail views: `06_kidney_surface_closeup.png`, `07_hilum_connection_closeup.png`, `08_full_pair_tubes.png`, and `09_neutral_sculpt.png`.
- Reproduction/validation scripts: `Working/intermediate_color_pass.py` and `Working/validate_intermediate_color.py`.

The final colored views were visually checked for the darker-leaning intermediate color, clean silhouette, tube readability, and matte finish. User visual approval remains pending. No commit or push was made.