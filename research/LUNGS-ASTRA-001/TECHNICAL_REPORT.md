# LUNGS-ASTRA-001 — second art and breathing pass

## Result and files

The second pass was made from the existing `LUNGS-ASTRA-001.blend`. The lungs were **not rebuilt from the Tripo FBX**. The six original mesh parts, skin weights, and three-bone rig remain the base of this asset. The work changes the colour system, the timing and amplitude of the breathing clips, and the colour treatment of one rear relief fused into the left lobe.

- `LUNGS-ASTRA-001.blend`: finished asset, preview studio, three gameplay actions, and the Blender-only GOOD → BAD demo action.
- `LUNGS-ASTRA-001.fbx`: six game meshes, rig, materials, embedded rear-branch texture, and **only** the three gameplay clips.
- `Textures/Rear_Vessel_Paint.png`: editable external copy of the 1024 × 1024 rear colour mask; the same image is packed in the blend and embedded in the FBX.
- `Previews/01_front_hero.png` through `06_closeup.png`: six updated exterior views at 1000 × 1000.
- `Previews/07_static.png`, `08_good_compressed.png`, `09_good_expanded.png`, `10_bad_compressed.png`, `11_bad_expanded.png`: state proof at 1000 × 1000.
- `Previews/12_good_to_bad_transition.gif`: 75 rendered frames played over 5.0 seconds, showing acceleration from GOOD toward BAD. This is a review demonstration, not a gameplay clip.
- `Working/BeforeSecondPass/`: copies of the prior blend, FBX, documentation, and renders made before this revision. Scripts and validation JSON are in `Working/`.

## Art direction and materials

This lungs asset is the proposed first example of the brighter, cartoon organ direction. The heart, kidneys, brain, and liver were not changed. The existing lobe silhouette and tracheal entry remain recognizable. The new colours are clean and more distinct under the same broad studio lighting; the material response remains dry and soft matte.

| Material | Use | Linear RGB base colour | Roughness |
| --- | --- | --- | ---: |
| `01 | Cartoon coral lung` | right lobe | `(0.780, 0.180, 0.180)` warm coral pink-red | 0.84 |
| `01B | Cartoon coral with rear burgundy` | left lobe; UV colour mask for its fused rear branch | coral base `(0.780, 0.180, 0.180)`; painted berry `(0.320, 0.045, 0.087)` | 0.84 |
| `02 | Soft pink airway` | trachea and central bronchial stem | `(0.780, 0.360, 0.430)` light cartoon pink | 0.85 |
| `03 | Berry burgundy vessels` | separate front and rear surface branch meshes | `(0.320, 0.045, 0.087)` berry burgundy | 0.86 |

All four materials have metallic 0, coat 0, sheen 0, diffuse roughness 0.68, and specular IOR level 0. The three preview lights have direct specular contribution 0. The ambient fill was increased slightly to keep the brighter colours legible without adding gloss. Visual review of the front, rear, side, closeup, and animation frames found no wet, clear-coated, or sharp-highlight response.

The left rear branch is part of the supplied left-lobe topology. Direct polygon material assignment caused visibly jagged colour blocks; an added tube produced duplicate branch silhouettes. Both trial methods were discarded. A UV colour mask now follows the existing relief without changing its vertices or triangle count. The separate front and right-rear branch islands continue to use the burgundy material directly. The painted rear relief is a visual exception to the separate-mesh material layout; its colour and roughness still match the burgundy system. Review this treatment in `02_rear.png` and `05_side.png`.

## Measured donor motion

The donor archive `Working/DonorAnimation/lungs_motion_donor.zip` contains a nested ZIP and one FBX. Blender 5.2.1 imported the FBX with **30 fps** (`fps_base` 1.0). Sampling the donor `Bone.003` scale for every frame found one expansion peak and identical scale at each clip's beginning and end. Thus each action range represents one full breath, not multiple cycles.

| Donor action | Range | Peak frame | Frame intervals | Period | Frequency | Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Armature|good` | 1–79 | 36 | 78 | **2.600 s** | **0.384615 Hz** | 23.08 breaths/min |
| `Armature|bad` | 1–37 | 14 | 36 | **1.200 s** | **0.833333 Hz** | 50.00 breaths/min |

The donor's two shape keys (`bad_80`, `fin_bad`) remain at value 0 in both actions; its visible breathing is bone driven. There is no separate donor STATIC action. The donor also references an unavailable external normal map. None of its geometry, bones, shape keys, keyframes, or textures entered this asset. See `PROVENANCE.md`.

The previous report assumed the donor was 24 fps. That assumption was incorrect and is superseded by this measurement. The frequency midpoint target for our GOOD is `(0.384615 + 0.833333) / 2 = 0.608974 Hz`.

## Final gameplay breathing

The existing left and right lobe bones were retained and their actions replaced. The central airway remains largely static, with its lower junction blended into the lobe bones. The scene is now 30 fps. Smooth clamped Bezier scale curves provide visible expansion and contraction; the first and last poses match for looping. GOOD and BAD both contract slightly below the neutral STATIC size, making compressed and expanded frames visually distinct. BAD has a faster rise and greater but controlled amplitude.

| Gameplay state | FBX action | Frame range | Period | Frequency | Rate |
| --- | --- | --- | ---: | ---: | ---: |
| STATIC | `STATIC` | 1–2 | held pose | 0 | 0 |
| GOOD | `BREATH_GOOD` | 1–50 | **1.6333 s** | **0.612245 Hz** | 36.73 breaths/min |
| BAD | `BREATH_BAD` | 1–25 | **0.8000 s** | **1.250000 Hz** | 75.00 breaths/min |

GOOD differs from the donor-frequency midpoint by about 0.54%; BAD is exactly 1.5 × donor BAD frequency. BAD is about 2.04 × our GOOD frequency. The lobe-bone X-scale ranges are 0.985–1.130 for GOOD and 0.975–1.170 for BAD, with smaller vertical/depth ranges. The evaluated full-asset width changes from **0.218307 to 0.233638 m** for GOOD and **0.217249 to 0.237867 m** for BAD. The first and last evaluated widths match exactly in the saved blend and in the reimported FBX.

`Preview_GOOD_to_BAD_Transition` is a 150-frame Blender-only action that ramps breathing frequency and amplitude over approximately 5 seconds. The saved blend opens on this demo at frame 1, ready to play. It was created after the gameplay FBX export and is **absent** from the final FBX. Unity can later crossfade between the two clean looping gameplay clips; the demonstration is a visual proposal for that transition rather than Unity runtime logic.

## Geometry and technical validation

| Mesh | Vertices | Triangles |
| --- | ---: | ---: |
| Left lobe | 1,522 | 2,775 |
| Right lobe | 996 | 1,988 |
| Central airway | 1,218 | 2,410 |
| Left front branch | 515 | 769 |
| Right front branch | 505 | 754 |
| Right rear branch | 517 | 771 |
| **Total** | **5,273** | **9,467** |

The saved blend reopened in Blender 5.2.1 LTS. The FBX reimported with the same six mesh names, vertex and triangle counts, three-bone rig, skinning, materials, left-lobe UV map, and 1024 × 1024 rear-branch image. The image was present as packed FBX data on reimport. The FBX contained exactly `STATIC`, `BREATH_GOOD`, and `BREATH_BAD` actions with the intended ranges; the Blender-only transition action was absent. Imported action names acquire Blender's FBX rig prefix, but retain the state suffixes.

Every frame of all three gameplay actions was sampled in both the blend and reimported FBX. STATIC had zero width change. Both breathing actions had one expected peak, finite evaluated vertices, and zero first-to-last width error. Sampled min/max widths matched between source and FBX within floating-point rounding. `Working/second_pass_validation.json` records the comparison and reports `PASS`.

Unity import, shader appearance under actual game lighting, and subjective breathing feel still require project integration and user visual acceptance. No commit or push was made.
