# G12 — visual review of v01 meshes / review02 previews

Reviewed saved pixels, not only render completion: all four first-pass images, all four final review02 images, and the identical-camera bare townhouse comparison. All final facade cameras are at 1.75 m above ground; the scale reference is a non-living 1.75 m box.

The final files are the four `*_review02.png` previews listed in `README_Review02.md`. Both earlier images and the master/FBX exports remain intact. A second preview build compared all 33 geometry hashes to `validation_v01.json` before rendering; the geometry and material roles did not change.

## What reads well

| Preview | Observation |
| --- | --- |
| `01_all_modules_lineup_review02.png` | All 33 silhouettes are visible at one physical scale, with names and actual tris / budget above them. Frames have deep white edges and pronounced sills; cornices have a real section; the canopy has visible braces; the fire escape shows solid treads, two stringers, rails and the upper landing. The scale box is separate from the meshes. |
| `02_townhouse_eye_3q_review02.png` | The same cream cuboid becomes a three-storey town house through projected sills, belts, quoins, cornices and the balcony slab/rails. The glass recess and white frames cast readable shadows. The porch opening is clear, and the yellow gas run stops at the entrance. Deliberate shutters and the single balcony avoid filling every bay with an accent. |
| `03_panel_block_eye_3q_review02.png` | Five floors read from the 2.8 m rhythm, panel seams and stacked 3 m balconies. Glazed enclosures have opaque lower aprons and clear large panes rather than all-blue balcony walls. The short side remains blank, per the bible. The canopy, AC and downpipe provide street-level depth. |
| `04_shop_eye_3q_review02.png` | Broad cobalt/chalk awning stripes, a physical blank signboard and deep window borders make a small shop legible. The closed side shutter has large real ribs. The eaves use true convex corner modules after the first-pass overlap was removed. |

The bare townhouse comparison has the same camera, light, box and roof slab. Its nearly featureless walls provide direct evidence of how much the added geometry changes the read. The style is deliberately brighter and more pastel than the reference game to preserve STYLE_BIBLE_v2b's palette. Broad forms, low polygon counts, thick members and selective weighted chamfers provide the requested chunky reference direction. This is an artistic judgment from the renders, not a numerical claim of reference matching. Reference direction was checked against the game's [official Lundenburg Liquors screenshot](https://store.steampowered.com/news/app/2551020/view/3952538742051710478).

## Remaining weak points / practical limits

- AC fan, drain funnel and chimney flue are symbolic capped shapes. Their internals are intentionally simple under the 80/40-triangle budgets; very close inspection will reveal that simplification.
- The plain flat roof masses and small parapet-cap corner joins are less developed than the facades. Roof equipment is clearer in the lineup than from eye level, where much of it is naturally hidden behind the roof line. The panel block's blank end is intentional rather than missing window placement.
- The strict budgets use selective one-segment front/profile chamfers and weighted normals. Rail bars and hidden caps remain square; the kit does not apply two-segment rounding to every edge.
- Surfaces are palette colours only. ProcTexture materials and any new tiled/world-space UV mapping remain a later step; UV0 currently selects palette cells. Blank signs contain no production text.
- Windows are recessed relative to their trim face, not cut through the host wall. The glass remains outside the solid box so the modules can be applied without Boolean work.
- The staircase is a static one-floor module, not a tested walkable prefab. Unity material remapping, collider setup and scene placement have not been performed in this ArtSource-only task.

## Evidence

`validation_v01.json`: 33 modules, 2,872 total triangles, every per-module check passed. Exact requested outer window sizes and straight/vertical module pitches are included. Closed topology, outward winding, palette-cell UVs, eight ordered role slots, no degeneracy, origin/applied transforms and deterministic double builds pass.

`export_audit_v01_01.json`: every FBX reimport passed, including triangle counts, metre bounds within 1 mm, root pivot at origin, custom normals, palette UV preservation, all eight material slots, and absence of animation/armatures. The master has exactly the 33 module meshes, metre units and a packed palette image.

No existing deliverable was replaced; no shared STYLE_KIT_v2 file, style bible, Unity asset or WORK_SYNC.md was edited. No commits or staging were performed. Subjective acceptance remains with Fedya and the project owners.
