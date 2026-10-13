# Art direction — current (consolidated 2026-10-13)

The single entry point for how VOLUNTEERS ONLY should look **now**. It consolidates the sources below and does not replace them. Where they disagree, this order wins:

1. Fedya's decisions of 2026-10-11/12, the "art direction v3": textures, the One-Armed Robber reference, district themes, the muted grade, density and scale.
2. `Working/Reviews/Textures_2026-10-11/STYLE_OAR_NOTES.md`: the distilled One-Armed Robber (OAR) look. Its tags: [OBS] seen in OAR, [GUESS] a GPT extrapolation, [CL] Claude's addition.
3. `docs/art/STYLE_BIBLE_v2.md` (v2b, Russian). Still the law for shape language, scale, budgets, trims and placement. **Its §3 rule "flat palette plus 5 pattern maps only" is replaced by v3 textures.** Its bright palette is superseded by the v07 grade.
4. `ArtSource/Textures/StyleKit_v3/candidate_v07/grade_v07.json`: the muted texture grade (candidate, revision 7).
5. `docs/WORLD_MAP_3D_BRIEF.md` §3–§4 (Vadim's district vibes) and the kit READMEs in `ArtSource/Props/STYLE_KIT_v3/`.
6. Current code: `Assets/OnlyVolunteers/Map/LookV3/Editor/V3Lighting.cs` (the v17+ light, used by v17 and v18 builds).

A STYLE_BIBLE_v3 does not exist yet. When it is written, it supersedes this file. "Open:" marks undecided points.

## 1. One line

Stylised low-poly with modelled 3D detail, quiet painted textures and a muted, slightly dark daylight in the One-Armed Robber gamut. It shows a lived-in post-Soviet courtyard district beside an American downtown. It is **not** neural "slop": no boxes with stretched textures, no photo grime, no noise.

## 2. Shape language

- **Silhouette first.** A grey-on-white render must name the type at 50 m and the category at 100 m (bible §4.1), judged from the 3/4 fly-cam and the game camera.
- **Chunky.** Visible thickness is ≥ 0.06 m for parts shorter than 1 m and ≥ 0.10 m for longer ones; lamp posts are ≥ 0.16 m. Proportions are slightly squat (§4.2).
- **Three levels of detail only:** mass → secondary forms (roof, canopy, balcony) → accents ≥ 0.2 m (pipe, sign, shutter). There is no fourth level: no bolts, no scratches (§4.3).
- **One deliberate asymmetry per object type**, built into the template. Vertex jitter is 0 everywhere (§3.5, §4.4).
- **Hard surfaces have flat faces.** Bevels: one segment of 2–4 cm on props, 6–10 cm on large props. Props the player stands next to get two segments plus weighted normals (the Tripo "plumpness").
- **Organic forms** use smoothed normals inside each lobe. A visible facet must be at least 1/8 of the silhouette width: no "crumpled paper".
- **Architecture reads as geometry, not texture** (OAR §5; Vadim: "everything 3D with protrusions"): frames, sills, cornices, parapets, pilasters, balconies, drainpipes, canopies, roof equipment. Facade detail is modelled from the kits, never baked into the wall texture.
- **No outline shader and no banded toon shading.** Dark edges come from material borders, recesses and shadows (OAR §4).

## 3. Palette: the muted v07 grade

Fedya rejected the bright v16 look on 2026-10-11 ("the earlier darker look was better"). The target is the OAR gamut: roughly −25 % saturation and −15 % value against the v2 swatches. The v07 grade applies this to every v3 albedo:
- an initial ×0.75 saturation and ×0.85 value;
- then a uniform HSV correction to a per-category target mean;
- every pixel ends at value ≤ 0.82, with tonal correlation to the source > 0.98.

| Category | v2 mean → v07 mean | Category | v2 mean → v07 mean |
|---|---|---|---|
| 1a grass | `#8CBC5E` → `#6F804D` (olive) | 3d cinder blocks | `#C9CDCA` → `#AEABA6` |
| 1b dirt road | `#AB825B` → `#91775E` | 4a clay roof tiles | `#D37A55` → `#A2634B` |
| 1c beach sand | `#F1DEAC` → `#C2B698` | 4b slate / 4c corrugated | `#63799A` → `#56677F` |
| 1d gravel | `#B5B9BE` → `#9C9EA1` | 4d flat bitumen roof | `#4A5058` → `#3E4247` |
| 1e mud | `#815740` → `#6E5344` | 5a planks / 5b logs | `#9C6E4A` → `#856450` |
| 2a asphalt | `#7E838A` → `#5F666C` | 6a/6b metal | `#A3A6AB` → `#8E9396` |
| 2b/2c sidewalk, cobble | `#DED2BD` → `#BDB5A8` | 7b tree bark | `#9C6E4A` → `#846450` |
| 3a brick | `#AE5544` → `#8C4F42` | 3c concrete panels | `#C8CCC9` → `#ADABA6` |
| 3b plaster/stucco | `#EEDCB8` → `#B8AD98` | | |

Colour relationships (OAR §3):
- warm tan and cream architecture;
- cool neutral roads and infrastructure;
- muted brick reds and blue industrial panels;
- few strong accents, placed on chosen objects (doors, awnings, balconies, signs, vehicles), never as high-frequency variation.

Bible rules that still hold:
- one accent per building (plus the door colour);
- accents ≤ 6 % of the frame; near-black ≤ 2 %;
- a pitched roof differs from its wall by |ΔL\*| ≥ 15;
- the canopy is darker than the ground beneath it;
- the green ladder: meadow < lawn < leaf < conifer;
- one colour system for everything, including first-person props and vehicles.

Open:
- v07 is a **candidate outside Assets**, pending Fedya's visual acceptance (its Unity test was not run).
- The bible's accent hexes (`red #D9473A`, `mustard #E0A830`, `teal #3F9196`, `cobalt #3E6FB8` and the others) have no muted equivalents yet.
- Water: the bible's bright `#2E98D6` against muted blue-grey. G14 v02 already uses a muted, metre-depth palette.

## 4. Materials and textures

- **Base:** the ProcTexture family (CC0) plus FreeStylized "Grass 01" (final grass, Fedya) and ambientCG slate. We paint the flat bitumen roof and the logs ourselves (G13 procedural). All textures are recoloured to their category's palette swatch; **the palette stays the colour authority**.
- **The OAR painting recipe:**
  - big surfaces get one base colour with sparse tonal variation;
  - reduce fine noise and contrast by about 50–70 %;
  - add 3–5 large angular patches in nearby tones per tile;
  - wear is selective and graphic, not on every edge;
  - joints are thin (shared real-world brick, plank and slab scale), never deep dark grooves.
- **Shader:** URP Lit. Normal strength is low. Never bake black AO into albedo. Convert roughness to smoothness; never plug roughness in raw.
- **Smoothness:** defaults about 0.05 and metallic 0. Glass 0.35 with reflections. Metal accents 0.30/0.10. Emission (neon, lamps) only on an `ink` backing board.
- **Kits** (BUILDING_DETAILS, BUILDING_DETAILS_US) currently carry palette-atlas UVs in ordered role slots: `plaster, brick, concrete, metal_painted, metal_dark, wood, glass, roof`; the US kit adds canvas, accent and emissive. Replace by role when textures arrive. Tiled textures need world-space or triplanar mapping or new UVs; collapsed palette UVs give the wrong scale.
- **Water:** Uber Stylized Water v02 (MIT derivative) with:
  - two scrolling ripple normals;
  - a depth gradient from shallow to deep;
  - a soft shore-foam band;
  - Fresnel sky reflection;
  - procedural caustics in the shallows only.
  "Water must be beautiful" (Fedya).
- **Vegetation:** simple silhouettes, few colour groups; terrain grass stays quieter than plant meshes. Grass = a quiet ground texture with a large colour mask plus low-poly tuft meshes.
- **Forbidden:** photo grime, streaks, moss, puddles, cracks, uniform dirt, dense small-wave noise, glowing cyan tracers.

## 5. Lighting, fog, post (v17+, `V3Lighting.ApplyV17`)

| Setting | Value |
|---|---|
| Sun | 37° elevation, azimuth 225° (SW), `#FFE3BE` × 1.05, soft shadows, strength 0.85 |
| Ambient (trilight) | sky `#8E9DB4`, equator `#9C9C95`, ground `#6B6458` |
| Fog | linear, 60 → 400 m, colour `#B4BCC0` = horizon haze; far clip 460 m |
| Shadows | distance 90 m (`PC_RPAsset_StyleV17`) |
| Sky | gradient panorama: zenith `#4E6C93` → `#6F8BAD` → `#A3B3C1` → fog colour at the horizon |
| Post (`Look_PostFX_v17`) | ACES; post-exposure +0.15; contrast +8; saturation −15; white balance +8 warm; bloom 0.15 at threshold 1.2 (emissives only) |
| Reflections | skybox, intensity 0.8 |

Principles:
- Set up the daylight before judging textures.
- Readability comes from shaped shadows, not from removing them.
- Fog separates distant buildings and supports the sightline goal; it must not hide bad models.
- No film grain, chromatic aberration, depth of field or motion blur.
- Night (bible §9.4) is direction only, after the day look is accepted.

Open:
- The bible's v2 profile (45° sun, no tonemapping, palette = screen) and its calibration prefab assume the bright palette. With v07 plus ACES, the calibration targets need redefining.

## 6. Districts: architecture themes

**04 Rough District = post-Soviet** ("Norilsk courtyards"; Base 3):
- five-storey panel and brick khrushchyovkas around courtyards, arches, dead-end alleys, rows of metal garages;
- modelled panel seams, balconies glazed in different ways (some open with junk), concrete entrance canopies, steps, basement windows, drainpipes, satellite dishes, ribbed garage doors;
- age is shown **by form**: dark plinths, blank numbered end walls, bins, cramped yards, a crooked lamp. Never by streaks.
- Kit: `STYLE_KIT_v3/BUILDING_DETAILS` (33 modules, 2,872 tris total; Fedya: "all great").

**05 Downtown = American, stylised NYC** (Base 4; refs `REF_downtown_city_01–04`):
- brick walk-ups with black fire escapes and wooden roof water tanks;
- beige and ochre mid-rises; a round blue glass tower; glass offices; a colonnaded stone building; brick lofts with saw-tooth roofs;
- at street level: stoops, awnings, cast-iron storefronts, blade and neon signs, painted wall ads, rooftop billboards;
- dark asphalt with crisp white markings, bold zebras, hydrants.
- Kit: `STYLE_KIT_v3/BUILDING_DETAILS_US` (23 modules, 3,884 tris; built in the cloud, binaries rebuilt locally).

**Shared rules:**
- One texture family across districts. Districts differ by geometry kit and palette recipe, not by texture style (OAR §5).
- The only fence between districts is the stylised Elite fence.
- Game scale (v17 decision): storey 2.8 m (old town 3.2 m); Downtown 2–6 floors with ≤ 2 landmarks of 9–12 floors; no facade run > 24 m; lots 8–20 m; panel blocks ≤ 48 m; plazas ≤ 40 × 40 m.
- Fixed sizes: human 1.75 m, door 2.1–2.4 m, sill 0.9 m.

Open:
- The themes of 01 Forest, 02 Hamlet, 03 Construction, 06 Port, 07 Elite, 08 Quiet Valley, 09 Beach and 10 Tramduro were proposed by the lead and await Fedya.
- How worn Rough District is, and how much texture the village wood, Elite plaster and water get, are for Vadim and Fedya on the hero samples (3D brief §4).

## 7. Storytelling and readability

- **Density and occlusion:**
  - you must not see the whole map from one point;
  - median sightline ≤ 45 m inside districts;
  - yards are filled as "rooms" (trees, fences, garages, sheds);
  - forest belts, hills and dachas separate districts;
  - the van must not look microscopic next to buildings.
- **Props cluster around functions** (entrances, counters, work areas, the den, the 24h shop) and keep routes and sightlines clear. Litter only where people leave it: butts and cans by the bench, bags by the containers. No random clutter, no laundry lines.
- **Wear by form and placement:** a broken bench slat, an open garage, a lamp tilted ≤ 6°, rust as a colour fill, never as streaks.
- **District legible in one second** from walls, roofs, accent and tree species, without labels. One hero landmark per view breaks the roofline.
- **Interactives** must read by shape, icon or hint, not only by colour (brief §13). Lamps, railings and fence posts double as NPC GripAnchor points (canon).
- **Trees are scattered randomly** (Fedya 2026-10-12; this overrides the bible's §10.1 street rows).
- Few parked cars, which never narrow main roads.
- Small objects (scarecrows, garages, fences at houses) fill places where buildings cannot be densified harmoniously.
- Signs: simple graphic art on a clearly framed board; text only from the sign atlas.

## 8. Low-poly budgets

Map content (bible §4) and FPS-facing gameplay content (brief §12) are different bands. These are starting budgets, adjusted by screen size and measurement; never ruin an important silhouette or the hands to hit a number.

| Class | Triangles (LOD0) | Notes |
|---|---|---|
| Facade detail module | 20–460 (kit budgets) | windows ≤ 120, balcony ≤ 400, storefront ≤ 460 |
| Grass tuft / flower patch | ≤ 40 / ≤ 120 | GPU instancing, cut-off at 60 m |
| Bush / hedge module | ≤ 300 / ≤ 160 | |
| Trees | spruce ≤ 320, poplar ≤ 450, pine ≤ 650, linden ≤ 700, birch and apple ≤ 800, palm ≤ 900 | LOD1 at 40–60 % beyond 60 m |
| Street furniture (bench, bin, sign, lamp) | ≤ 800; ≤ 1,500 next to the player | |
| Fence module 2 m / garage | ≤ 400 / ≤ 1,500 | |
| Map car (parked) | ≤ 3,000 | |
| House ≤ 3 floors / functional / panel block / tower | ≤ 3,500 / ≤ 7,000 / ≤ 14,000 / ≤ 12,000 | landmark ≤ 4,000; church or water tower ≤ 9,000 |
| Ordinary gameplay prop | 300–1,500 | brief §12 |
| Tool in hand (first person) | 1,000–4,000 | Tripo props reduced to about 500–1,000 (taser 560) |
| NPC / patient (near LOD) | 6,000–15,000 | Buddy BASE 11,576; pool types about 14.2–14.5k |
| Van | 8,000–20,000 | |

**Textures:**
- tiled ground and wall sets: 1024² (the v3 originals are 1K);
- ordinary props: 512–1024; prop atlas 1024 (Tripo props);
- larger sizes only with a visible gain;
- the palette atlas is 256² with Point filter, Clamp, no mips and no compression.
- No forced normal map or unique PBR set per item.

**Materials:**
- simple props have 1–2 materials and ≤ 3 swatches (base + accent + metal or wood);
- kits have the fixed ordered role slots (8 in BUILDING_DETAILS, 11 in BUILDING_DETAILS_US);
- procedural buildings get one URP Lit material per key + swatch (SRP Batcher).

Count materials, draw calls, transparency, shadows and physics as well as triangles.

## 9. Blender → Unity export rules

Taken from the STYLE_KIT_v3 READMEs (shared with BEACH and HAND_PROPS) and brief §12.

1. **Units and axes:** metres, Blender X right and Z up; outward from a facade is −Y. Apply all transforms: unit scale, no rotation, no negative scale.
2. **Pivots:**
   - wall modules: wall plane Y = 0, bottom-centre;
   - roof equipment: roof plane Z = 0, footprint centre;
   - corners: the convex corner;
   - doors: on the hinge; wheels: on the axle.
   Movable parts are separate objects.
3. **FBX export:** selected single mesh, `object_types={'MESH'}`, `axis_forward='-Z'`, `axis_up='Y'`, `apply_unit_scale=True`, `global_scale=1`, `use_mesh_modifiers=False`, `mesh_smooth_type='FACE'`, `add_leaf_bones=False`, `bake_anim=False` (static), `path_mode='STRIP'`, `use_custom_props=False`. Characters and rigs use their own builders (Mixamo 65-bone names unchanged).
4. **Unity import:** Scale Factor 1, Bake Axis Conversion on, import normals, tangents none (unless normal-mapped), no animation for static meshes, no generated collider. Colliders are simple or compound and authored separately. Remap material slots by role.
5. **Determinism:**
   - builders are Python scripts with a fixed seed;
   - `--check-only` validates in memory;
   - every export has a `validation_vNN.json` (bounds within 1 mm, origin, slots, custom normals, no degenerate triangles) and a re-import audit `export_audit_vNN_XX.json`.
   Judge the rendered preview, not just the absence of Python errors.
6. **Revisions:** never overwrite. A new geometry means a new `_vNN`; builders refuse to replace files. Keep the source `.blend` and the script. Keep `.meta` files and never change a GUID on regeneration.
7. **Check in Unity** after import: URP materials, shadows, LOD transitions and the view from the game camera. Not while Fedya is playtesting.

## 10. Open questions (summary)

1. Accept v07 as the grade, and derive muted accents and water colours.
2. Themes for the remaining 8 districts.
3. Rough District wear level, and the texture amount for wood, plaster and water (Vadim and Fedya, hero samples).
4. Recalibrate the bible's light calibration for v07 plus ACES, or retire it.
5. Write STYLE_BIBLE_v3 (machine-readable palette JSON) to replace bible §2–§3 and this summary.
6. Bible §15 questions 1–7 (old-town towers, roof shares, spruce/pine mix, palms, sun direction, grass amount, hamlet shutters) are unanswered in the repo.
