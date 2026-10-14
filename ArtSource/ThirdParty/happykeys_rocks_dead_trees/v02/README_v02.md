# Happykeys bare trees — COZY proportion prefab revision v02

Task G23, 2026-10-14. This is a **prefab revision**, using the source v01 geometry unchanged. The source archive, FBXs, palette, `.blend` and v01 Unity prefabs are read-only. No rock revision is included.

| Source tree | Source height | v02 height | Trunk width factor | Unity prefab |
| --- | ---: | ---: | ---: | --- |
| TREE_BARE_01 | 5.00 m | 3.90 m | 1.25 | `Assets/OnlyVolunteers/Art/Trees/v02/Prefabs/TREE_BARE_01_v19_Cozy_v02.prefab` |
| TREE_BARE_02 | 7.00 m | 5.46 m | 1.25 | `Assets/OnlyVolunteers/Art/Trees/v02/Prefabs/TREE_BARE_02_v19_Cozy_v02.prefab` |
| TREE_BARE_03 | 9.00 m | 7.02 m | 1.25 | `Assets/OnlyVolunteers/Art/Trees/v02/Prefabs/TREE_BARE_03_v19_Cozy_v02.prefab` |

Editable implementation: `ArtSource/Dev/Trees_staging/v02/`. The `Proportions_v02` child has XYZ scale `(1.25, 0.78, 1.25)`; prefab roots and rebuilt capsule proxies have unit scale. Source geometry is identical; only mesh culling bounds are enlarged for wind. Capsules use transformed source centres and axes, 1.25 radial expansion and shortened axial lengths. They remain static because the trunk base does not move and upper movement is subtle.

The material retains the existing Rough District bark colour and uses `OnlyVolunteers/Trees/Cozy Sway v02`. The source COZY image was viewed as an artistic reference only; no files were copied from it. It is not a dependency of these assets.

Model and palette provenance/licence: Trekkerac / happykeys, CC0-1.0; see `../v01/source/PROVENANCE.md`. Parent model hashes and topology caveats remain in `../v01/manifest_v01.json` and `../v01/validation_v01.json`. This task does not repair or replace that topology.

Final verification and G18 handoff: `docs/reports/TREES_COZY_v02.md`. Actual imported measurements: `Working/Reviews/Trees/proportions_v02.csv`.
