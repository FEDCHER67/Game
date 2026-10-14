# G23b — Forest conifers v03, Blender approval stage

The current candidate is **v03_04**. Earlier numbered iterations are retained; none was overwritten. This Forest-only brief supersedes the previous G23 v02 integration plan. Do not run the old v02 installer. The golden broadleaf trial is dropped, and Rough District bare trees remain unchanged.

## Deliverables

- `Forest_FrondTrees_v03_04.blend` — editable source, four variants, three LODs each, linked common-scale preview instances, and named trunk capsule proxies in `COL_Collision`.
- `Models/Forest_{Spruce_A,Spruce_B,Fir,Young}_v03_04.fbx` — metres, base pivots, applied scale; three model LODs per FBX. Collider definitions are in the source and validation JSON, not mixed into render-mesh exports.
- `Textures/Forest_NeedleFrond_v03_03.png` — original 2048×512 RGBA needle painting, created analytically by `paint_frond_v03_03.py`. It is intentionally reused by the fourth model iteration.
- `Previews/forest_lineup_v03_04.png` and `forest_fronds_closeup_v03_04.png` — actual Blender renders.
- `C:/Dev/Game/Working/Reviews/Trees/forest_trees_v03_vs_cozy.png` — requested 2400×1800 internal comparison sheet: reference on the left; four models at one scale and actual crown close-up on the right.
- `forest_validation_v03_04.json`, `fbx_roundtrip_v03_04.json` — measured source and independent FBX-reimport evidence.
- `Shaders/TreeSway_v03.shader` and `.hlsl` — unimported continuation of the v02 sway shader, with additional per-frond tip weighting.

## Construction and budgets

Chosen method: **separate curved, double-sided alpha-clipped cards**. Each card has its own disconnected mesh island and tapered needle cutout. Opposite-winding reverse faces are included in the counts below. No solid tier/skirt meshes, COZY models, reference textures or downloaded art are used.

| Variant | Height | Crown span | LOD0 | LOD1 | LOD2 | LOD0 fronds |
|---|---:|---:|---:|---:|---:|---:|
| Spruce A | 9.0 m | 5.76 m | 5,262 | 2,098 | 462 | 259 |
| Spruce B | 8.0 m | 5.52 m | 5,262 | 2,098 | 462 | 259 |
| Fir | 7.5 m | 5.10 m | 4,870 | 1,926 | 444 | 239 |
| Young | 6.0 m | 3.54 m | 3,400 | 1,386 | 366 | 164 |

LOD1 is approximately 40% of LOD0; LOD2 is 8.8–10.8%. Crown span / height is 0.59–0.69. Base trunk radii are 0.264 / 0.284 / 0.254 / 0.184 m. The corresponding upright capsule heights are 3.2 / 3.2 / 3.15 / 2.52 m. Branch tiers, lean, azimuths and frond fans differ between variants. Fir fronds are wider and droop less; the two spruces differ in silhouette and droop.

Forest colours derive from existing `V19_MP_Leaf_Pine`, `V19_MP_Leaf_Dark` and `V19_MP_Bark` materials in `Palette19/Test_v02/Vegetation`. Three related greens are #244D35, #2C6042 and #4B7845, with ±4% per-frond material variation. Blender lighting uses the Forest's muted overcast direction from `V19PaletteP2.cs` (horizon #A1ADA7, sun #D2DED9) and the t=0.5 district palette. The preview is an approximation of that light, not a Unity colour-grade verification.

## Wind and later Unity integration

UV0.x runs from 0 at each frond root to 1 at its tip; trunk UV0.x is zero. The staged v03 shader adds a squared tip term to the existing slow height-weighted gust, preserving per-instance phase and a pinned base. Forward, shadow, depth and depth-normal passes use the same deformation. URP fog, ZWrite and alpha-test variants are retained.

After visual approval, frond materials must bind the supplied RGBA texture, enable `_ALPHATEST_ON`, set `_AlphaClip=1` and `_Cutoff=0.5`, and enable GPU instancing. Set `_TreeShape` per model using its height and radius. The shader has **not** been imported, compiled or render-tested in Unity. Shadow/depth alpha clipping, fog and wind still require the later authorized Unity step.

## Verification and scope

Blender generation and renders succeeded. All 12 FBX LOD meshes independently reimport with the expected triangle counts, exact 6/7.5/8/9 m heights, measured crown spans, base at zero, and UV tip masks in [0,1]. No zero-area triangles were found. Card borders are intentional open boundaries, and reverse sheets are deliberate coincident geometry for two-sided rendering.

The reference was viewed at its original URL: https://distantlands.space/images/cozy-case-study/cozy_4.jpg. Only the requested internal comparison-sheet capture contains its displayed pixels. No COZY/Distant Lands source file was downloaded, copied into the art source, or embedded in Blender/FBX. All tree geometry and needle texture are original.

The Unity acquire process was cancelled by the lead before G23 received the lock. No Unity tools, Assets imports, map builds, global settings changes, commits or review bridge were performed. Stop here for Fedya's visual decision.
