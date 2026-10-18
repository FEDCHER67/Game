# Organs layout v02: anatomical organ placement, Patient v02 markers, OperationAbdomen_v02

**Date:** 2026-10-18.
**Agent:** Claude worker (Blender only, background CLI).
**Not touched:** Unity was not opened, and no `Assets/`, code, v01 files or skeleton were changed. Nothing was committed.

**Goal (Fedya):** organ sizes, organ positions and the operation opening should be believably anatomical for Buddy's body. The style stays cartoon Sausage Buddy: no gore and no blood pools.

**Review sheet:** `Working/Reviews/Operations/organs_v02/organs_layout_v02_sheet.png`. It shows:
- before/after against v04, using the same operation camera crop and the v04 close-up;
- edge and interior close-ups;
- a 3/4 view;
- a sagittal and an axial cross-section;
- the key numbers.

The individual renders `01`…`09` are in the same folder.

## 1. Files

| File | What |
|---|---|
| `ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v02/build_patient_v02.py` | Opens `Patient_v01/SAUSAGE_BUDDY_PATIENT_v01.blend` (read only). Replaces the three INC markers, adds 3 new ones, computes the TABLE_REST frame and writes the outputs below. Holds the whole layout (single source of truth). |
| `…/Patient_v02/SAUSAGE_BUDDY_PATIENT_v02.blend` / `.fbx` | Same Body, Face, Shorts, rig (65 bones) and skin weights as v01; a SHA-1 of vertices, weights and bone matrices is checked before and after. Only the markers differ. The FBX uses the v01 export settings. |
| `…/Patient_v02/ORGANS_LAYOUT_v02.json` | Organ placement for the gameplay agent. Per organ: centre, axes, quaternion, depth under the skin, real and Buddy sizes, model scale and centre offset, pull. For the kidneys also cords (start/end in rest, table-Blender, table-Unity and marker-local Unity/Blender). Also the opening, the guide, the liver loop and the great vessels. |
| `…/Patient_v02/build_report_SAUSAGE_BUDDY_PATIENT_v02.json` | Unchanged-hash proof, table-mapping check (v01 markers reproduce at 0.0 mm), marker list. |
| `ArtSource/Props/TABLE-ASTRA-001/v02/Scripts/build_abdomen_v02.py` | Builds the opening asset from the layout JSON, sampling the skin of the TABLE_REST body. |
| `ArtSource/Props/TABLE-ASTRA-001/v02/OperationAbdomen_v02.blend` / `.fbx` | The cavity/opening asset (§4). |
| `…/v02/OperationAbdomen_v02_Gradient.png` | 4×256 sRGB gradient: the cut layers, then the cavity wall from light to dark. Base map of `MAT_Abdomen_Interior_v02`. |
| `…/v02/OperationAbdomen_v02_validation.json` | Tri counts; flap height above the skin −0.7…+5.4 mm; floor 15.2 cm deep; ≥ 4.85 cm of body behind the floor; vessels sit on the floor (−2.9…+1.6 mm). |
| `…/v02/Scripts/render_organs_v02.py` | Review renders (Eevee): `blender -b Patient_TableRest_v01.blend --python render_organs_v02.py -- --out <dir>`. |

Rebuild order:
1. `build_patient_v02.py` (run on the v01 .blend);
2. `build_abdomen_v02.py` (`--factory-startup`);
3. `render_organs_v02.py`.

All three refuse to overwrite their outputs.

## 2. Scale: real vs Buddy

Buddy's torso compared with an adult:

| Measure | Buddy | Adult | Ratio |
|---|---|---|---|
| Width at the waist | 0.333 m | ~0.30 m | ×1.11 |
| Depth (belly −0.116 … back +0.096) | 0.212 m | ~0.22 m | ×0.96 |
| Axilla to crotch | 0.34 m | ~0.51 m | ×0.67 (short cartoon trunk) |

**Size rule.** One size factor for every organ, **×0.9** (the geometric mean of width and height is 0.86, rounded up for readability), so the liver-to-kidney proportions stay real.

**Position rule.** Positions follow scaled landmarks:
- costal margin z ≈ 0.99;
- xiphoid ≈ 1.07;
- L1–L2 ≈ 0.97;
- shorts waistband 0.80.

| Organ | Real (cm) | Buddy target (cm) | Source model → recommended scale | Result (cm) |
|---|---|---|---|---|
| Liver (W × H × D) | 25 × 15 × 8 | 22.5 × 13.5 × 7.2 | LIVER recolour 20.5 × 15.3 × 6.6 → **(1.08, 1.08, 0.88)** on model (X, Y, Z); height squashed | 22.1 × 13.5 × 7.2 |
| Kidney (H × W × D) | 11 × 6 × 3 | 9.9 × 5.4 × 2.7 | KIDNEY recolour bean 11.1 × 6.6 × 4.3 → **uniform 0.9** | 10.0 × 5.9 × 3.8 (the model is a chunky bean; kept) |

## 3. Layout and markers

**Patient rest frame:** metres, Z up, the patient faces −Y, the patient's left = +X.

**Marker axes:**
- +Z = skin normal, out of the body; this is also the pull direction.
- +Y = toward the head. For the kidneys, +Y is the organ's long axis (upper pole).
- +X = patient's left (Blender). For the liver, +X is its long axis, toward the left lobe.

All markers are bone-parented to `mixamorig:Spine`, as in v01.

| Marker | Rest position | Depth under skin (along −Z) | Table-local Unity position | Notes |
|---|---|---|---|---|
| `INC_LIVER` (organ centre) | (−0.030, −0.052, 1.032) | 5.8 cm | (−0.030, 0.823, 0.212) | Upper right abdomen; dome z 1.10, right edge x −0.14 (1.5 cm inside the flank). Long axis +X, left lobe raised 8°. Front face ~2.6 cm under the skin; the lower part is visible in the opening and the right lobe is tucked under the right rib edge/rim. |
| `INC_KIDNEY_L` (organ centre) | (+0.080, +0.010, 0.975) | 10.4 cm | (0.080, 0.761, 0.155) | Deep at the back wall, in a gutter beside the spine ridge. The upper pole is tilted 15° toward the spine and 10° back. Z is tilted ~17° laterally (skin normal), so the front face turns slightly outward and the hilum faces forward-medial, as in a real kidney. |
| `INC_KIDNEY_R` (organ centre) | (−0.080, +0.010, 0.955) | 10.4 cm | (−0.080, 0.761, 0.135) | 2 cm lower than the left (the liver is above it). Its upper ~2 cm sits under the liver's lower edge in the top view; this is anatomical and leaves most of the kidney visible. |
| `INC_ABDOMEN` (new) | (0, −0.1174, 0.960), on the skin | 0 | (0, 0.889, 0.140) | Centre of the opening and of the guide; origin of OperationAbdomen_v02. |
| `GUIDE_BELLY_START` (new) | (0, −0.106, 1.082) | 0 | (0, 0.877, 0.262) | Head end of the midline cut (on the skin). |
| `GUIDE_BELLY_END` (new) | (0, −0.108, 0.840) | 0 | (0, 0.879, 0.020) | Pubic end, 4 cm above the waistband. Guide length **0.242 m**. |

The JSON also gives TABLE_REST rotations as table-Unity quaternions.

**Cords: two per kidney, from the hilum to the great vessel on the spine** (renal artery above, renal vein below):
- The left kidney's cords end on the aorta (red, x +0.014). The right kidney's end on the vena cava (purple, x −0.016). This is a cartoon simplification.
- Length ≈ 4.0–4.3 cm. The cords lie deep, medial to each kidney, on the floor, so the top camera sees them beside the kidney without clicking through it. This is the "cut from below/behind" mechanic.
- The kidney model's own short descending tube reads as the ureter (decoration only).

Marker-local cord coordinates, **Unity sign convention** (Unity marker-local X = patient's RIGHT, i.e. Blender X negated; Y and Z are the same):

| Cord | Start (hilum) | End (great vessel) | Radius |
|---|---|---|---|
| L A (artery) | (0.0237, 0.004, 0.006) | (0.0594, 0.0192, −0.0055) | 5.0 mm |
| L B (vein) | (0.0237, −0.012, 0.006) | (0.0648, −0.0082, −0.0065) | 6.0 mm |
| R A (artery) | (−0.0236, 0.004, 0.006) | (−0.0540, 0.0178, −0.0149) | 5.0 mm |
| R B (vein) | (−0.0236, −0.012, 0.006) | (−0.0590, −0.0097, −0.0154) | 6.0 mm |

Snip point = cord midpoint. The A and B midpoints are about 2 cm apart.

**Liver loop** (marker-local of INC_LIVER):
- centre: Unity (−0.012, −0.004, 0.045), Blender (+0.012, −0.004, 0.045);
- radii **(0.085, 0.056)**;
- plane 4.5 cm above the liver centre, about 1 cm above its front face.

It rings the part of the liver inside the opening (see sheet tile 3).

**Pull:** along marker +Z. Exit distance (centre to above the skin + 3 cm): kidney **0.147 m**, liver **0.124 m**. The current `pullDistance` of 0.2 is enough.

**Organ model → marker:**
- Blender: rotate Euler X −90°, so model up (+Z) → marker +Y and model front (−Y) → marker +Z. Scale as in §2. First translate by −`model_centre_offset`, which puts the kidney bean centre (not the pair or tube) at the marker.
- **Kidney mesh choice.** The KIDNEY model names its pair from the viewer. Its `R_Kidney` mesh (Blender +X, hilum toward −X) is the anatomical **patient-left** kidney, and `L_Kidney` is the patient-right kidney.
- Bean centre offsets: R mesh (0.0702, 0, −0.0008); L mesh (−0.0713, 0, 0.0012).

## 4. OperationAbdomen_v02 (the cavity)

**Origin and axes** = `INC_ABDOMEN` (+Z out of the body, +Y head, +X patient's left in Blender). Parent every object to `INC_ABDOMEN` with zero local position and rotation and scale 1. In the file they sit at the TABLE_REST pose in table-local space, like OperationIncisions_v01.

| Object | Tris | Material(s) | Purpose |
|---|---|---|---|
| `ABDOMEN_OPENING` | 7,296 | `Buddy_Skin` (flaps), `MAT_Abdomen_Interior_v02` (everything inside the cut) | See below. |
| `ABDOMEN_MASK` | 126 | `MAT_Abdomen_StencilMask_v02` (never visible) | Flat lid 1.5 mm above the skin, 3 mm under the flap edge. Used as the stencil writer that hides the belly skin inside the hole. |
| `ABDOMEN_VESSELS` | 1,840 | `MAT_Vessel_Artery_v02`, `MAT_Vessel_Vein_v02` | Aorta (r 8.5 mm) and vena cava (r 10 mm) on the spine ridge. |
| `ABDOMEN_INTESTINES` | 4,560 | `MAT_Abdomen_Bowel_v02` | One meandering small-bowel tube (r 1.1 cm) in the lower belly, mostly tucked under the pubic rim. Decoration, no interaction. Can be decimated to about half. |
| `CORD_KIDNEY_L/R_A/B` | 336 each | artery / vein | Optional reference cords at the JSON positions. Gameplay can use them or build its own. |

**What `ABDOMEN_OPENING` contains:**
- **The opening.** A lens-shaped opening, like a retracted midline laparotomy: 24 × 28 cm, with a natural ±2–3 mm wobble and a slightly jagged cut line.
- **No rounded rim.** Instead there are thin pulled-back skin flaps (lifted up to 5–8 mm, more at the sides, tucked 0.7 mm into the skin). Their custom normals blend into the body's normals, so there is no shading seam.
- **The cut face.** A sharp cut edge, then a cut face showing the layers: dermis pink line, cream fat band (~6 mm), pale fascia line, dark-red muscle.
- **The cavity.** A glossy pink peritoneal wall with a slight undercut, getting darker with depth down to a maroon back wall, 15.2 cm deep at the kidney gutters. The soft spine ridge rises 3.5 cm on the midline. The floor rises toward the flanks, the diaphragm and the pelvis.

**Unity material values** (sRGB colours are stored as custom properties on each material):

| Material | Base | Smoothness |
|---|---|---|
| Interior | `OperationAbdomen_v02_Gradient.png` (uses UV0) | 0.70 |
| Bowel | #E58F85 | 0.70 |
| Artery | #CC2933 | 0.68 |
| Vein | #855CA8 | 0.68 |

For flaps, use the patient's skin material.

**References.** Web, ideas only; nothing was downloaded or copied.
- **Surgeon Simulator** (Bossa, MCV/DEVELOP "making of"): organs read like classroom anatomy models, and the torso opening was designed for gameplay first. Hence clean, smooth, model-like organs and one generous opening.
- **Trauma Center** series (reviews and Hardcore Gaming 101): stylised rather than visceral, clean lines, colour-coded organs and vessels for quick reading. Hence red artery / purple vein coding and readable glossy colours.
- **Surgical anatomy texts** (StatPearls "Laparotomy", Geekymedics abdominal incisions, Lecturio): the midline layer order (skin → subcutaneous fat → Scarpa's fascia → linea alba/muscle → transversalis fascia → preperitoneal fat → peritoneum), the midline laparotomy and retractors holding the edges. Hence the lens shape, the layered cut face and the pulled-back flaps instead of a rounded rim.

## 5. Inventory and in-body sizes (recommendations)

**In-body** (`OperationPresentation.Fit` uses the largest bounds dimension, including the kidney's tube):

| Organ | Fit largest | Same as | `organHalfSize` (x, y) |
|---|---|---|---|
| Kidney | **0.146 m** | uniform 0.9 of the source | (0.030, 0.050) |
| Liver | **0.221 m** | width at scale 1.08; then multiply the model's up axis by 0.88/1.08 = 0.815 | (0.110, 0.068) |

Set `organLift = 0`, because the markers are now organ centres.

**World items:**
- `worldModelSize` today is 0.45 for both. Recommended: kidney **0.15**, liver **0.22**, the same as in the body.
- Tray: `organItemScale` **0.7**, giving kidney 0.105 and liver 0.155. This fits the 0.165 m slot pitch and fixes the v04 liver overhang.
- If items read too small when dropped in the world, use ×1.15 at most (kidney 0.17, liver 0.25) and keep the tray at 0.7.

## 6. Unity integration checklist (gameplay agent)

1. **Patient model.**
   - Point the patient prefab at `SAUSAGE_BUDDY_PATIENT_v02.fbx`. The rig, clips and avatar are unchanged.
   - Add `INC_ABDOMEN`, `GUIDE_BELLY_START` and `GUIDE_BELLY_END` to the anchors (markers 3–5).
   - The INC_* markers now sit at organ centres, 5–10 cm inside the body. Re-check everything that assumed they were on the skin.
2. **Opening placement.**
   - `OperationAbdomen.ZonePose`: use the `INC_ABDOMEN` pose instead of "kidney midpoint + `abdomenOffset`". The midpoint is now 13 cm deep. Set `abdomenOffset = (0, 0)`.
   - Replace the generated `Oval`/`Ring` visuals with an instance of `OperationAbdomen_v02.fbx` parented to `INC_ABDOMEN` at identity. Enable it when `zoneOpened`; keep the 0.3 s pop on the opening only.
3. **Stencil, required for the depth.**
   - Render `ABDOMEN_MASK` first: queue Geometry−1, ColorMask 0, ZWrite Off, Stencil Ref 1, Comp Always, Pass Replace.
   - The patient's **skin material** (Body only, not the flaps) tests Stencil NotEqual 1.
   - The cavity, organs, vessels and bowel render normally.
   - Without the stencil the belly skin covers the cavity and the deep organs. (In URP: a Render Objects feature, or two small shader variants.)
4. **Guide line (big cut).**
   - Midline from `GUIDE_BELLY_START` to `GUIDE_BELLY_END`, `abdomenCutLength = 0.242`.
   - It lies on the skin: abdomen-local start (0, +0.122, −0.008), end (0, −0.120, −0.013). Draw the dashes at local z ≈ +0.008 above that.
   - Keep `cutTolerance` 0.05 and `neatTolerance` 0.02.
   - `abdomenHalfSize = (0.122, 0.138)`, e.g. for probes and framing.
5. **Liver.**
   - Model at the INC_LIVER marker: big right lobe toward the patient's right (screen left in the top camera), broad front face toward marker +Z, scale per §5.
   - `TurnLiverFaceUp` and `LiverModelScale` should then be deleted. Keep the imported FBX root rotation instead of forcing `localRotation = identity`; with identity the model shows its raw Blender axes, which is why v04 saw the liver edge-on.
6. **Liver loop.**
   - `liverLoopRadius = (0.085, 0.056)`.
   - Add a loop-centre offset of (−0.012, −0.004) in Unity marker-local.
   - `LoopHeight = 0.045`.
   - Band: `Tolerance` = min(0.05, 0.6 × 0.056) = 0.034.
7. **Kidneys.**
   - In `KeepOneKidney`, swap the side test, so the patient-left marker keeps the source's `R_Kidney` mesh (Blender +X = Unity −X) and the hilum faces the spine.
   - Centre on the bean, not the bean plus tube.
8. **Kidney cords.**
   - Replace the shared-abdomen branch of `OperationState.Cord` with the JSON values from §3 (attach = hilum start, rim = great-vessel end). Cord 0 = artery, cord 1 = vein.
   - Lower `cordHitRadius` from 0.045 to about **0.010**: the two snip points are about 2 cm apart, and the old radius covers both.
   - Snipping is still the scalpel 0.3 s hold. Cords are only reachable inside the opening.
9. **Pull.** Kidneys come up along marker +Z out of a ~10 cm deep position; the exit is about 0.15 m. Raise the organ through the stencil hole. The liver exit is about 0.12 m.
10. **Visual checks after integration** (top camera, 1080p):
    - The liver covers the upper-left of the opening.
    - The right kidney's top is partly under it.
    - Both kidneys are visible in the gutters, with vessels on the spine ridge.
    - The bowel sits in the bottom of the opening.
    - No belly skin is visible inside the rim.
    - Breathing clips: the flaps follow the Spine bone, as the v01 markers did.

## 7. Verification and limits

**Verified:**
- v02 Body, Face and Shorts vertices, weights and bones are byte-identical to v01 (hash).
- Reimporting `SAUSAGE_BUDDY_PATIENT_v02.fbx` gives 65 bones and the 6 markers parented to `mixamorig:Spine` at the intended positions.
- `OperationAbdomen_v02.fbx` reimports with 8 meshes and custom normals.
- The TABLE_REST mapping reproduces the v01 markers at 0.0 mm.
- Renders were reviewed: the op camera matches the v04 camera (Unity `cameraPosition` and FOV 50 converted).

**Limits and open points:**
- The review hole in the body is a Blender boolean. The real game needs the stencil (§6.3); this is not tested in Unity.
- The review lighting is Eevee, not URP. The deep floor may read darker in game; if so, lighten the bottom of the gradient PNG.
- The organ orientation in Unity depends on the FBX import rotation (§6.5). Verify visually.
- Organ hit volumes, camera zoom and cord radius need a play test by Fedya.
- The kidney model is thicker than a real kidney (3.8 cm vs 2.7 cm), and the liver is squashed in height; both are cartoon choices.
- The intestine tube could be decimated; the opening is 7.3k tris.
