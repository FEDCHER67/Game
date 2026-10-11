# HAND_PROPS — small NPC props for STYLE_KIT_v2

Six static, low-poly props for the Sausage Buddy crowd animations. The master is `SK2-HANDPROPS-001_v01.blend`; each prop has its own `_v01.fbx`. There are no armatures, animation tracks, photo textures, or vertex-colour materials. The A v04 Sausage Buddy appears only in the scale preview and is not saved in the master or exported.

## Assets and placement

Sizes below are real-world metres in semantic order. The FBX files are **+Y up**, with applied metric units and scale 1. Their object origins are the grip points. Blender source geometry is Z up and uses the BEACH kit's `axis_forward='-Z'`, `axis_up='Y'` conversion. “Forward” below is the natural long direction in the exported FBX, not a camera instruction. All references to `RightHand` and `LeftHand` mean the exact rig bone names `mixamorig:RightHand` and `mixamorig:LeftHand`.

| ID | Tris / max | Size | Pivot at origin | Exported local axes | Suggested attach bone | Crowd clip |
| --- | ---: | --- | --- | --- | --- | --- |
| `PROP_CIGARETTE` | 56 / 60 | length 0.085, Ø 0.008 | On centreline, 1/3 of the length from the filter end | +X from filter toward ash; +Y up | `mixamorig:RightHand` | `SmokeCorner_Enter`, `SmokeCorner_Loop`, `SmokeCorner_Exit` (hand pose implies it) |
| `PROP_LIGHTER` | 100 / 120 | H 0.065 × W 0.025 × D 0.012 | Geometric centre | +Y from base to metal top; +Z toward the thumb wheel | `mixamorig:RightHand` | Optional in `SmokeCorner_Enter`; no prop mesh is authored in the clip |
| `PROP_PHONE` | 136 / 200 | H 0.150 × W 0.072 × D 0.009 | Middle of the right long side | +Y from bottom to top; +Z out of screen; +X toward grip side | `mixamorig:RightHand` | `PhoneTalk_Enter`, `PhoneTalk_Loop`, `PhoneTalk_Exit` (right palm pose implies it) |
| `PROP_COFFEE_CUP` | 284 / 300 | H 0.120, Ø lid 0.080 | Centre of cardboard sleeve, 0.0555 m above base | +Y toward lid; radial X/Z | `mixamorig:RightHand` | Optional after `KioskBuy` event `Take`; existing clip does not author a cup hold |
| `PROP_SHOPPING_BAG` | 192 / 400 | W 0.300 × D 0.150 × H 0.380 including handles | Middle of the two loop handles at their top | +Y up toward handle arches; +Z out of front/logo face | `mixamorig:LeftHand` | No existing clip authors a bag hold; candidate is `ShopQueue_Loop` after a hand-pose check |
| `PROP_BEACH_TOWEL` | 36 / 60 | L 1.700 × W 0.800 × T 0.010 | Centre of the bottom face | −Z along towel length toward its far end; +Y face up | None; place at floor level | `BeachLie_Enter`, `BeachLie_Loop`, `BeachLie_Exit`; place behind NPC root per Crowd_v01 README §3 |

The cigarette has four specified zones, each mapped to an existing palette cell: `ochre` filter, `chalk` paper, `terracotta` ember, `grey` ash. This is the only prop using four colour families because the requested four zones cannot be expressed with three. The lighter uses `cobalt` plastic, `grey` metal, and `ink` wheel. The phone uses `ink` body and `slate` screen. The cup uses `chalk`, `ochre`, and `panel`; the bag uses `teal` and `chalk`; the towel has four broad alternating `cobalt` and `chalk` faces. Folds and corner facets are deliberate templates, with no random displacement.

## Build and validation

Run from the repository root with Blender 5.2:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v2/HAND_PROPS/build_hand_props.py -- --revision 1 --samples 32 --cpu
```

The builder refuses to replace an existing `.blend`, FBX, JSON, or preview. For a changed model, use a **new** `--revision N`. To rebuild and validate the same deterministic geometry without writing files, run with `--revision 1 --check-only --no-render`. `--preview-existing` adds only new corrected preview filenames after comparing all six geometry hashes with the saved validation. `--audit-existing --no-render` reimports all FBXs and inspects the master, writing a new numbered audit. No mode writes outside `HAND_PROPS/`.

The build uses the BEACH kit's shared `_lib/stylekit2.py` mesh/UV/material/studio code without modifying it. Its single material is `Look_Palette_v2`, using `../_lib/Look_Palette_v2.png` and `../_lib/Look_Palette_v2.json`; the master packs the image. UV0 points to palette-cell centres. FBX settings match BEACH: selection of one mesh, mesh only, `axis_forward=-Z`, `axis_up=Y`, `apply_unit_scale=True`, `use_mesh_modifiers=False`, `mesh_smooth_type=FACE`, `bake_anim=False`, `path_mode=STRIP`. Each FBX has one root mesh, one material and custom normals. For Unity, use the existing Style Kit palette remap, Scale Factor 1, Bake Axis Conversion on, imported normals, and no animation or collider.

`validation_v01.json` records triangle counts, dimensions in Blender XYZ, swatches, UV-cell checks, manifold/winding checks, exact-size checks, and geometry SHA1. The deterministic builder creates each mesh twice and compares hashes. `export_audit_v01_02.json` independently reimported all six FBXs: triangle counts, bounds within the BEACH kit's 1 mm tolerance, origin, palette UVs, normals, and no rig/animation passed. The master contains exactly the six props and a packed palette image. Both reports have `all_checks_passed: true`.

## Previews

Use `Previews/v01/02_lineup_with_Sausage_Buddy.png` for scale and `Previews/v01/02_PROP_<NAME>.png` for each close-up. The lineup uses the real `ArtSource/Characters/SAUSAGE_BUDDY_01/SAUSAGE_BUDDY_A_v04.fbx` as a non-exported reference. The previews use the BEACH studio's 45-degree sun, three-colour ambient, Standard view transform, and Cycles rendering. The earlier `00_`/`01_` preview files show the master-layout meshes behind the intended subjects; they remain untouched because revisions are never overwritten. The first half-millimetre export audit likewise remains as `export_audit_v01.json`; it compared against three-decimal report bounds and is superseded by the passing 1 mm `export_audit_v01_02.json`.

The proposed placements for lighter, cup, and bag require animator review. The crowd clips currently imply only the cigarette and phone in the hands; the towel is a world prop. None of these FBXs has been placed or tested in Unity.
