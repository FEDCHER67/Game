# Types_opt_v01: lighter LOD0 derivatives of Vadim's Sausage Buddy NPC types

Workflow: `build_types_opt_v01.py`, with the method and settings in its docstring (crowd budget 15k, TOL 1.5 / 3 mm, hidden faces over 17 poses, controlled per-material collapse, source normals, at most 4 weights). Vadim's originals in `Types/` are never modified, and outputs are never overwritten. `NpcTypesImportV01` prefers `SAUSAGE_BUDDY_<TYPE>_vNN_opt_v01.fbx` when it exists. First batch (commit 7fd76b88): 27 of 37 types, 728k -> 554k tris (`opt_report_opt_v01.json`).

## Addendum 2026-10-22 (W86): Vadim's commit 976100c7, 14 models

`build_types_opt_v01_w86.py` runs the same `optimise()` with the same settings on this pool. Reports go to `reports/<TYPE>.json`; the CONSTR updates use `reports/<TYPE>_vNN.json` so that the earlier reports are kept. The merged report is `opt_report_opt_v01_w86.json`, and the check script is `verify_opt_v01_w86.py`. Review sheet: `Working/Reviews/Integration_W86_2026-10-22/vadim_models_opt_sheet.jpg`.

| Type | Rev | Tris before | Tris after | Saved |
|---|---|---:|---:|---:|
| VIP_BEASTMAN * | v01 | 25,139 | 19,303 | 23.2 % |
| VIP_SPEEDSTER | v01 | 23,026 | 19,398 | 15.8 % |
| ARMY_SOLDIER | v01 | 21,925 | 16,884 | 23.0 % |
| HAMLET_HUNTER_GRANDPA | v01 | 21,420 | 16,664 | 22.2 % |
| CONSTR_INDIAN * | v08 | 20,932 | 15,892 | 24.1 % |
| CONSTR_MEXICAN | v05 | 20,063 | 15,621 | 22.1 % |
| TRAMDURO | v01 | 19,467 | 13,994 | 28.1 % |
| POLICE_FAT | v02 | 19,274 | 14,858 | 22.9 % |
| VIP_BLINDFOLD | v01 | 19,058 | 14,094 | 26.0 % |
| OLD_POPKING | v01 | 18,101 | 13,064 | 27.8 % |
| HAMLET_MUZHIK | v01 | 18,058 | 14,454 | 20.0 % |
| CONSTR_UZBEK | v05 | 17,380 | 12,868 | 26.0 % |
| POLICE_THIN | v02 | 16,510 | 12,768 | 22.7 % |
| FBI_AGENT | v01 | 16,096 | 12,668 | 21.3 % |
| **Total** | | **276,449** | **212,530** | **23.1 %** |

\* Per-type exceptions (documented in the wrapper), each found on the review renders:
- VIP_BEASTMAN: the `VIP_BEASTMAN_Logo*` decal stack is not decimated. Its layers are 0.6–0.8 mm apart, which is below TOL, and Logo_Bg showed through the kitten. The hidden faces of `VIP_BEASTMAN_Jeans` are kept, because step 1 opened a hole in the back of the rolled cuff.
- CONSTR_INDIAN v08: `CONSTR_INDIAN_Hair` is not decimated, because the decimated glossy hair had a bright blotch behind the ear. The accepted `CONSTR_INDIAN_v07_opt_v01` has the same blotch.

All 14 were checked against their sources:
- Same 65 bones: names, parents and rest matrices.
- Same objects, vertex groups, material slots, UV layers, shape keys and 26 actions.
- No unweighted vertices, and at most 4 influences.
- Bounds within 0.31 % (FBX: within 1.24 mm).
