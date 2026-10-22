# Types_opt_v02: invisible LOD0 cuts and a crowd LOD chain for the Sausage Buddy NPC types

`build_types_opt_v02.py` takes the 38 current `Types_opt_v01` meshes as input. Its docstring has the method and all the settings. Inputs from `Types_opt_v01` and from `Types/` are never modified, and outputs are never overwritten. Each type gives `SAUSAGE_BUDDY_<TYPE>_vNN_opt_v02.{blend,fbx}` plus `reports/<TYPE>.json`, which records every step and every LOD round. The merged report is `opt_report_opt_v02.json`. The check script is `verify_opt_v02.py`: 38/38 pass. It compares the rig (65 bones, rest), the 26 actions, the vertex groups, the material slots and the used materials, the shape keys, the absence of UVs, at most 4 influences, no unweighted vertex, the Face vertices and shape-key offsets against opt_v01, and the bounds; it runs on both the .blend and the FBX. `render_compare_opt_v02.py` makes the sheets in `Working/Reviews/Integration_W86_2026-10-22/npc_opt_v02_sheet_*.jpg`: `_00_overview` plus one sheet per type.

## LOD0: what could be cut without anyone seeing it

The baseline is opt_v01, which had already removed the hidden Body/Outfit faces over 17 poses and decimated the garments within 1.5 mm.

**Applied**
- **Face interior: -14.9k tris (~400 per type).**
  - What goes: the eye-ball backs and the lid and shine shells inside the head. These faces are covered in all 13 clips (sampled every 15 frames, together with their *_Face shape-key tracks), at every shape key at 1, and at Blink + each expression.
  - Why the shading is unchanged: the Face has no custom normals, so a hidden face stays wherever removing it would turn a visible vertex normal by more than 1°, including any pair of shape keys at 1. This keeps about 350 tris per type.
  - The cut is Head-rigid, so it also holds in ragdoll poses.

**Measured, not applied, or almost nothing to gain**
- **Head skin under the eyes: 28 tris in total.**
- **Small rigid parts: 16 tris in total.**
  - Hair twists, dreads, beads and chains cannot be cut. Dropping 10 % of a twist's triangles already turns its shading up to 13°, against a limit of 1.5°.
  - Open parts (socks), skinned parts and layered decals were tried. Each showed a 1 px change on the review renders, so they are excluded.
- **Zero-area slivers: 1,067 tris.** These are only counted, not removed. Removing them changed the bevel shading of the OLD_COURIER backpack and the POLICE radio.
- **Shoe-sole undersides: kept.** They are seen in Panic_Run from behind, in TripFall and in PlayDead.
- **Body: not cut.** The hands and the head make up most of it. The head has no collinear rows to drop: its rows are 8 cm apart.
- **Normal-map bake: not done.** The types have no UVs and use flat colour materials, so a bake would add UVs, textures and a different shading model.

**Result:** LOD0 is 2.5 % lighter (593k → 578k), not 10–12k per type. The LOD chain below is what lowers the cost at distance.

**Visual check at 1.5 m:**
- Setup: Eevee, single-sided, FOV 60 at 1080p density; front, back and side; two frames: Panic_Run_Loop 5 with Surprised, and TripFall 30 with Blink + Worried.
- Result: 36 types differ from opt_v01 by 0 pixels (above 6 %).
- The two exceptions:
  - OLD_KAREN: 7 px, max 32/255, on a pearl.
  - BAD_GIRL: 2 px, max 20/255, on the lid edge in Blink + Worried.

## LOD1 / LOD2 (crowd: 15–40 m / beyond 40 m)

- **Method:**
  - Each LOD0 object is collapsed with edit-mode decimate, which keeps the Face shape keys and interpolates the weights.
  - The targets are 45 % (LOD1) and 20 % (LOD2) of LOD0.
  - Kept: garment hems with 2 rings around them (LOD1) or the hem only (LOD2), and one polygon per material.
- **Error limits against LOD0:**
  - Where they are checked: in 9 poses, or for the Face in 6 shape-key states.
  - LOD1: p99 8 mm, max 16 mm (0.5 px / 1 px at 15 m).
  - LOD2: p99 20 mm, max 43 mm (1 px at 40 m).
  - Open edges get half of these limits.
  - Vertices over the limit are locked and the collapse is redone, so the final counts land above the targets.
- **Normals:** taken from the source surface, per vertex.
- **Result:** every LOD of the 38 types is within its limits. On screen, the switch changes a few dozen to about 250 pixels at 15 m, and fewer at 40 m (see the per-type sheets).

| Type | Rev | opt_v01 | LOD0 | LOD1 | LOD2 | Face interior | Head skin | Small parts |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| BAD_ALTGIRL | v14 | 41,549 | 41,457 | 18,982 (46 %) | 8,390 (20 %) | 84 | 2 | 6 |
| OLD_RAPPER | v01 | 21,903 | 21,726 | 10,041 (46 %) | 6,167 (28 %) | 177 | 0 | 0 |
| HAMLET_GRANNY | v07 | 19,424 | 19,098 | 10,084 (53 %) | 6,888 (36 %) | 326 | 0 | 0 |
| VIP_SPEEDSTER | v01 | 19,398 | 19,073 | 8,745 (46 %) | 4,198 (22 %) | 325 | 0 | 0 |
| VIP_BEASTMAN | v01 | 19,303 | 18,847 | 9,016 (48 %) | 4,117 (22 %) | 456 | 0 | 0 |
| OLD_STREAMER | v09 | 18,041 | 17,659 | 11,076 (63 %) | 6,185 (35 %) | 380 | 2 | 0 |
| CONSTR_ARAB | v05 | 17,887 | 17,479 | 9,440 (54 %) | 5,083 (29 %) | 406 | 2 | 0 |
| OLD_KAREN | v06 | 17,332 | 16,866 | 9,533 (57 %) | 4,730 (28 %) | 456 | 0 | 10 |
| ARMY_SOLDIER | v01 | 16,884 | 16,440 | 7,533 (46 %) | 4,037 (25 %) | 444 | 0 | 0 |
| BAD_GIRL | v07 | 16,734 | 16,301 | 8,001 (49 %) | 3,806 (23 %) | 427 | 6 | 0 |
| HAMLET_HUNTER_GRANDPA | v01 | 16,664 | 16,347 | 8,594 (53 %) | 6,055 (37 %) | 317 | 0 | 0 |
| CONSTR_INDIAN | v08 | 15,892 | 15,436 | 7,812 (51 %) | 4,633 (30 %) | 456 | 0 | 0 |
| CONSTR_MEXICAN | v05 | 15,621 | 15,229 | 7,572 (50 %) | 5,054 (33 %) | 392 | 0 | 0 |
| POLICE_FAT | v02 | 14,858 | 14,466 | 6,327 (44 %) | 3,128 (22 %) | 392 | 0 | 0 |
| OLD_BUSINESSMAN | v03 | 14,816 | 14,424 | 7,588 (53 %) | 4,077 (28 %) | 392 | 0 | 0 |
| PROM_FOREMAN | v04 | 14,771 | 14,323 | 7,993 (56 %) | 4,613 (32 %) | 448 | 0 | 0 |
| BAD_BOMZHIHA | v02 | 14,694 | 14,238 | 7,308 (51 %) | 4,174 (29 %) | 456 | 0 | 0 |
| HAMLET_MUZHIK | v01 | 14,454 | 13,988 | 7,051 (50 %) | 3,392 (24 %) | 466 | 0 | 0 |
| HAMLET_BOXERS_GRANDPA | v05 | 14,397 | 13,939 | 6,755 (48 %) | 3,585 (26 %) | 456 | 2 | 0 |
| BAD_RAPPER | v10 | 14,312 | 13,904 | 7,261 (52 %) | 4,220 (30 %) | 408 | 0 | 0 |
| VIP_BLINDFOLD | v01 | 14,094 | 13,906 | 7,516 (54 %) | 3,063 (22 %) | 188 | 0 | 0 |
| TRAMDURO | v01 | 13,994 | 13,597 | 6,780 (50 %) | 2,904 (21 %) | 395 | 2 | 0 |
| BAD_HUSTLER | v04 | 13,985 | 13,601 | 6,355 (47 %) | 3,749 (28 %) | 384 | 0 | 0 |
| BAD_BOMZH | v01 | 13,894 | 13,476 | 6,267 (47 %) | 3,475 (26 %) | 416 | 2 | 0 |
| CONSTR_AFROAMERICAN | v05 | 13,769 | 13,371 | 6,185 (46 %) | 2,941 (22 %) | 398 | 0 | 0 |
| PROM_SAILOR | v03 | 13,386 | 12,988 | 7,384 (57 %) | 4,094 (32 %) | 398 | 0 | 0 |
| HAMLET_SHEPHERD | v06 | 13,360 | 12,913 | 6,003 (46 %) | 3,069 (24 %) | 447 | 0 | 0 |
| OLD_POPKING | v01 | 13,064 | 12,636 | 7,222 (57 %) | 3,561 (28 %) | 424 | 4 | 0 |
| CONSTR_UZBEK | v05 | 12,868 | 12,551 | 5,803 (46 %) | 2,726 (22 %) | 317 | 0 | 0 |
| BAD_VAPER | v02 | 12,807 | 12,403 | 6,210 (50 %) | 3,148 (25 %) | 404 | 0 | 0 |
| POLICE_THIN | v02 | 12,768 | 12,346 | 5,498 (45 %) | 2,991 (24 %) | 416 | 6 | 0 |
| FBI_AGENT | v01 | 12,668 | 12,300 | 6,282 (51 %) | 3,152 (26 %) | 368 | 0 | 0 |
| FOREST_STASHER | v03 | 12,540 | 12,084 | 7,141 (59 %) | 3,978 (33 %) | 456 | 0 | 0 |
| FOREST_OD_JUNKIE | v01 | 12,469 | 12,013 | 6,117 (51 %) | 4,135 (34 %) | 456 | 0 | 0 |
| OLD_STUDENT | v08 | 12,393 | 11,937 | 6,114 (51 %) | 3,683 (31 %) | 456 | 0 | 0 |
| OLD_OFFICE | v04 | 12,243 | 11,851 | 5,498 (46 %) | 2,805 (24 %) | 392 | 0 | 0 |
| OLD_COURIER | v05 | 12,086 | 11,630 | 6,000 (52 %) | 4,116 (35 %) | 456 | 0 | 0 |
| BAD_GOPNIK | v05 | 11,805 | 11,355 | 6,630 (58 %) | 3,378 (30 %) | 450 | 0 | 0 |
| **Total** | | **593,127** | **578,198** | **291,717** (50 %) | **157,500** (27 %) | 14,885 | 28 | 16 |

The LOD columns show the share of LOD0. BAD_ALTGIRL (VIP-only) and OLD_STREAMER (multi-colour dreads, whose colour bands hold the LOD) are the heavy outliers.

## Names, and what changes for the Unity importer (to be done by the Unity agent)

- **.blend:** LOD0 keeps the opt_v01 object names (`Body`, `Face`, `Outfit`, `Props_*`). LOD1 and LOD2 are `<name>_LOD1` / `<name>_LOD2` in the collections `LOD1` / `LOD2`, hidden. All of them are skinned to the same `Buddy_Rig_Mixamo65`.
- **FBX (one per type):** follows Unity's LOD import convention, `<name>_LOD0` / `_LOD1` / `_LOD2`, with the Idle clip only and the export options of opt_v01. FBX import into Blender re-checked: OK.
- **Importer changes:**
  - `NpcTypesImportV01`: set `OptDir` to `Types_opt_v02` and `OptTag` to `opt_v02`.
  - `ApplyOptimized` / `UpdatePrefab`: map prefab renderer `X` to `X_LOD0`, so the prefab keeps the names `Body`/`Face`/`Outfit`/`Props_*`. Add the `X_LOD1` / `X_LOD2` SkinnedMeshRenderers with the same bones and root bone, plus a `LODGroup` on the root. Suggested screen heights, for a 1.75 m type at FOV 60: LOD0 > 0.10 (15 m), LOD1 > 0.037 (40 m), LOD2 down to ~0.01, then culled.
- **Code that finds renderers by name:**
  - `GreyboxFace` only drives `Face`; it should drive all `Face_LOD*` with the same blend-shape names.
  - `CaptureTableBridge.SpawnTrash` would copy the hat from every LOD; it must skip `*_LOD1/2`.
  - `NpcHeldProps` must hide or drop all `Props_*Hand*` LODs.
  - `KeepAppearance` and `OperationPatientRig` use exact names and stay on LOD0.
- **The 10 pool types without an opt_v01:** done afterwards, see the addendum below.

## Addendum: the 10 pool types opt_v01 left alone (input = Vadim's source revision)

Approved after the first 38. `POOL_SOURCE` in the build script; the same pipeline and the same checks: `verify_opt_v02.py` passes 10/10 (48/48 in all), comparing against the source .blend/.fbx.

**LOD0 gets only the Face-interior cut (step 1).** The other cuts were tried and switched off (`SOURCE_HIDDEN = False`) because each changed 6–3,000 px per type in the 1.5 m renders. These meshes have no custom normals yet, so re-normalising them after a cut shows.
- opt_v01's hidden-face removal on Body+Outfit: HAMLET_BODYBUILDER strap tops.
- The same removal on the Body only.
- The head skin under the eyes.
- Small parts.

**Visual check:** 9 types differ from the source by 0 px. BEACH_CORN shows 249 px of z-fighting flicker on the coplanar stripe decals of its shorts, whose Outfit is byte-identical to the source.

**Sheet:** `npc_opt_v02_sheet_01_overview_10_source_types.jpg`.

| Type | Rev | Source | LOD0 | LOD1 | LOD2 | Face interior |
|---|---|---:|---:|---:|---:|---:|
| BEACH_CORN | v03 | 14,924 | 14,468 | 6,654 (46 %) | 3,154 (22 %) | 456 |
| BAD_DRUNK | v04 | 14,266 | 13,810 | 6,378 (46 %) | 3,030 (22 %) | 456 |
| BEACH_CASTLE | v01 | 13,976 | 13,520 | 6,232 (46 %) | 3,001 (22 %) | 456 |
| BEACH_DETECTOR | v03 | 13,828 | 13,372 | 6,166 (46 %) | 2,929 (22 %) | 456 |
| BEACH_NUDIST | v01 | 13,276 | 12,820 | 5,895 (46 %) | 2,708 (21 %) | 456 |
| BEACH_BURIED | v01 | 12,680 | 12,224 | 5,616 (46 %) | 2,672 (22 %) | 456 |
| BEACH_LIFEGUARD | v03 | 12,626 | 12,170 | 5,912 (49 %) | 2,893 (24 %) | 456 |
| OLD_FITNESS | v05 | 11,840 | 11,384 | 5,276 (46 %) | 2,351 (21 %) | 456 |
| HAMLET_BODYBUILDER | v04 | 11,494 | 11,038 | 5,090 (46 %) | 2,259 (20 %) | 456 |
| BEACH_SUNBURN | v02 | 10,786 | 10,330 | 4,760 (46 %) | 2,192 (21 %) | 456 |
| **Total** | | **129,696** | **125,136** | **57,979** (46 %) | **27,189** (22 %) | 4,560 |

`DONE_ALL_48.txt` lists all 48 opt_v02 FBX files: 38 from opt_v01 and 10 from the source.
