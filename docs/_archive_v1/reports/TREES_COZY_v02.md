# G23 — COZY tree revisions v02

Status: staged implementation complete; Unity integration, live validation, captures and review bridge pending the overnight editor queue. This is a working report, not a completion claim.

## Scope and reference

Fedya's latest clarification takes precedence over the original instruction to leave leafy tree modelling out of scope. G23 creates separate conifer and broadleaf trial models; it never edits existing leafy source models or Vadim's work. The original happykeys bare-tree geometry is preserved.

Reference: https://distantlands.space/images/cozy-case-study/cozy_4.jpg. Studied visually in a browser; no reference image, model, material or other website file was copied into the project. Observed cues: shorter exposed warm trunks, layered asymmetric teal conifer boughs, drooping pointed tips, irregular golden broadleaf lobes, restrained natural motion.

## Changes

- `ArtSource/Dev/Trees_staging/Source/Trees_Cozy_v02.blend`: original G23 geometry, two conifer shapes and two broadleaf trial shapes, each with two LODs. The neighbouring build script, preview and validation files document the source work.
- `ArtSource/Dev/Trees_staging/v02/`: complete Unity import set containing four FBXs, URP sway shader/include, authoring/review tools, v19 revision resolver and a test-scene-only instancing probe.
- `ArtSource/ThirdParty/happykeys_rocks_dead_trees/v02/README_v02.md`: source revision/provenance note; v01 assets remain intact.
- Planned runtime output: `Assets/OnlyVolunteers/Art/Trees/v02/` with 24 separate prefab revisions, new materials/meshes and the imported code/model set.
- Planned scene: `Assets/OnlyVolunteers/Scenes/Dev/Trees_Test.unity`.
- Four narrowly scoped builder hooks: `V3Terrain.cs`, `V19Happykeys.cs`, `V19FullPalette.cs`, `V19FinalGeometry.cs`, under `Assets/OnlyVolunteers/Map/LookV3/Editor/`. They select revisions after placement and isolate the final terrain cache in a new numbered asset. No v19 build is run by G23.

Height is 0.78 times the corresponding previous tree. Bare trees use the affine visual transform `(1.25, 0.78, 1.25)` and matched analytic colliders. New crown variants measure the original visual basal trunk, enlarge its radius by 1.25 and fit new trunk capsules to it. Their crown envelope retains the authored silhouette: maximum horizontal span / revised height is 0.52/0.47 for conifers A/B and 0.72/0.68 for broadleaf trial A/B. Crown widths are independent of trunk thickening. All collider transforms have unit scale. Leafy variants retain a root CapsuleCollider for native Terrain collision; happykeys retains direct-child analytic capsules for G18's explicit proxy builder.

Conifer LOD0/LOD1 budgets are 972/320 triangles; broadleaf trial budgets are 704/260 triangles. Each uses three solid colour material slots. Branch and crown volumes intentionally overlap; these stylised game meshes are not manufacturing solids. No texture downloads or paid generation services were used. Happykeys retains its existing recorded CC0 provenance; G23's new crown geometry is original work.

## Selection and rollback

`V19TreesCozyV02.V19Revision` is the master switch (`CozyV02` / `Original`). Independent switches default to true:

| Switch | Selection |
| --- | --- |
| `ForestConifers` | Pine/spruce family within the existing `forest` district rectangle |
| `BetweenDistrictBroadleafTrial` | Deciduous trees outside all existing district rectangles |
| `RoughBareTrees` | The happykeys bare-tree family, plus the prepared legacy leafless revision |

Assumption: the existing `V19PaletteTest.Districts()` rectangles define district interiors; all remaining land is the requested between-district trial area. Palms, hedges, bushes, grass and district garden trees stay original. Set only `BetweenDistrictBroadleafTrial = false` to reject the golden trial while keeping forest and Rough improvements. Set `V19Revision = Original` to restore all prior tree selections. Selection leaves instance positions, rotations, colour, width and height scale factors unchanged; the generic builder continues computing those factors from original prefab height, so it does not cancel the 0.78 reduction.

## Wind

The URP 17.5 shader uses the same deformation in forward, shadow, depth and depth-normal passes. Forward lighting uses the stock URP fog include and fog-aware Lit fragment. Forward and depth passes have ZWrite On, so G18's depth-based aerial perspective can include trees. The bottom 4% is pinned. Height weighting is quadratic, with extra radial branch-tip weighting. A slow main wave is modulated by a slower gust; a phase derived from each instance's world origin prevents synchronized motion. The amplitude bound is 1.298% of nominal revised tree height. No per-tree Update or material instance is required.

All realtime passes support GPU instancing, and generated materials enable it. Object-space coordinates are retained by disabling static/dynamic batching for the shader. Mesh culling bounds are padded. Lighting normals remain at rest for this subtle motion, and baked Meta lighting is also at rest. These are deliberate cost limits.

## Verification

| Check | Status | Evidence / limits |
| --- | --- | --- |
| Blender generation and FBX reimport | PASS | `ArtSource/Dev/Trees_staging/Source/model_validation_v02.json`, `fbx_roundtrip_v02.txt`; all eight exported LODs round-trip to 1m normalized height |
| Staged C# compilation | PASS | Unity 6000.5.11f1's Roslyn compiler with current Unity references; `compile_v02.rsp` and `compile_v02.txt` |
| Full editor source with proposed builder hooks | PASS | `compile_builder_v02.rsp`; zero errors, two existing `V19PaletteTest.cs` obsolete API warnings |
| Live Unity shader/editor compilation | NOT RUN | Waiting for exclusive Unity lock |
| Dimensions, colliders, spatial selection and rollback | NOT RUN | Staged validation tool ready; must run in Unity |
| Play-mode GPU instancing and wind | NOT RUN | Isolated test scene/probe ready; includes native Terrain conifer/broadleaf trunk raycasts and a 16-instance explicit GPU draw |
| Separate group stills and three wind frames per group | NOT RUN | To be saved in `Working/Reviews/Trees/` from Unity |
| URP fog and depth-buffer occlusion | NOT RUN | Isolated per-family fog-off/on renders and a direct DepthOnly-pass occlusion test are staged; no global URP or project-setting edits |
| Protected original assets, map scenes and settings | NOT RUN | Installer/checker ready to compare hashes around G23's exclusive editor step |
| Overnight Claude review | NOT RUN | Run after live verification and report finalization |

## Note for G18 — lead to relay

Use the v19-only switches in `V19TreesCozyV02.cs` when producing the next approved v19 scene revision. Forest conifers, common-land golden broadleaf trial and Rough bare trees are independent. Keep original tree scale calculations: the new prefabs already contain the shortening. The final geometry hook clones the old terrain cache to a new numbered terrain asset when selection changes.

Regenerate `V19_Happykeys_TrunkProxies` from the selected bare-tree prefabs. The existing final pass only creates that root when absent; reusing old scene proxies would retain old collider dimensions. The same regeneration is needed when rolling back. G23 has not rebuilt or saved a map scene and has not sent a message to G18; this note is for lead relay.

Fedya still needs to judge the forest silhouette and decide whether the golden broadleaf trial should remain enabled. Automated checks and reviewer approval do not replace that visual decision.
