# G21 — approved organ recolour integration

**PASS — 14 October 2026.** Integrated all six approved exports and verified them in Play on `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i04_vanpaint.unity`, following the current V19 integration brief. The scene remains unchanged, clean, and stopped. No new map revision was needed.

## Delivered

New model prefabs under `Assets/OnlyVolunteers/Props/Organs/`:

| Organ | New FBX | Main palette (sRGB) |
|---|---|---|
| Heart | `HEART-ASTRA-007_recolour_v01.fbx` | Coral `#D8656C`, soft coral `#E98287`, rose `#B75263`, teal `#65999D` / `#50858C` |
| Lungs | `LUNGS-ASTRA-001_recolour_v01.fbx` | Pink `#E9959C`, airway `#F0BAC0`, rose `#B75263` |
| Liver | `LIVER-ASTRA-001_recolour_v01.fbx` | Warm brown-red `#A86659` |
| Kidney | `KIDNEY-ASTRA-001_recolour_v01.fbx` | Deep rose `#B75263`, tube `#DF9B96` |
| Brain | `BRAIN-ASTRA-002_recolour_v01.fbx` | Pink-beige `#E4B5AC`, stem `#CE8C88` |
| Eye | `EYE_ASTRA_001_v05.fbx` | Ivory `#F4EFE6`, iris `#559A9A` / `#7DB4A7`, rim `#3E737A`, pupil `#30383E` |

All six FBX files match the approved ArtSource exports byte for byte. Prior importer settings were retained for the five existing models; the eye is a new static import. Twelve shared URP Lit materials and the approved eye texture live in `Props/Organs/Recolour_v01/`. All use metallic 0 and smoothness 0.18, translating the approved roughness 0.82 into a consistent broad highlight. No global lighting or render settings changed.

The six existing `Inventory/Items/Item_*.asset` definitions now point to the new model prefabs. Item IDs, prices, carry sizes, physics settings and existing GUIDs are preserved. The eye now displays its approved textured model instead of the previous fallback cube. The reference scan found no separate organ `.prefab` requiring replacement.

Four scoped scripts changed: `KidneyMiniGame`, `OperationSession`, `ClinicOperationRunner`, and `ItemWorldModelMenu`. Both operation paths use the catalog kidney model. The minigame displays one existing half of the paired model, uniformly fitted to 0.24 m including its long tube, while retaining the existing pull/pop animation ratios and bruising feedback. No model mesh was edited. Gameplay thresholds, timing and rewards were preserved.

## Verification

- **Clinic operation on i04: PASS.** Real mouse input events completed cut, gradual extraction and all three tape strips. Neatness 0.999609, zero slips, no yank, reward 400, patient resolved and discharged. A temporary runtime callback recorded the result without invoking the save/reward UI callback; no quick-save was triggered.
- **Inventory: PASS.** All six organs were picked up through `LocalInventory.RequestPickup`, displayed in the hotbar, and dropped through `RequestDropSelected`. Every resulting world item had the approved model and materials. Clinic normally pays directly rather than adding its extracted kidney to inventory; inventory was checked separately.
- **Walk/drive: PASS.** Live KCC movement covered 9.13 m; the real driver seat was entered and the van drove 5.16 m, reaching 12.26 km/h. Public controller inputs drove actual physics while keyboard adapters were temporarily disabled.
- **Unity: PASS.** No Console errors; zero missing scripts in the running scene, stopped scene, or organ model prefabs. Final scene dirty flag is false.
- **Geometry/preservation: PASS.** All 23 meshes in the five previously imported models match vertex counts, submesh index counts and bounds. The approved source proof covers all six organs, including unchanged faces, UVs, rigs and animation. Five legacy FBX files, 71 existing metadata files, 27 ProjectSettings files and all 40 map scenes remain byte-identical. No commits or project-file deletions.

## Review and scope

Review sheet: [organs_in_game_v01.jpg](C:/Dev/Game/Working/Reviews/Organs_recolour/organs_in_game_v01.jpg). The same folder contains the original before/after PNGs, final kidney capture `ingame_kidney_i04_after_v02.png`, table close-up, and hotbar proof. Table arrangements, fixed dropped bodies and review camera framing were temporary Play-only setup. Forest morning lighting was retained; the close-up uses a narrower review field of view. Earlier kidney capture v01 is retained; v02 shows the final display scale.

Machine-readable evidence: `integration_final_audit_v02.json`, `integration_code_changes_v02.json`, `unity_reference_map_v01.json`, `unity_item_verification_v01.json`, `play_operation_i04_after_v02.json`, `play_inventory_i04_after_v02.json`, `play_movement_i04_v01.json`, and `unity_final_state_v01.json`, all in `Working/Reviews/Organs_recolour/`.

Per the latest **no map scene change** instruction, direct legacy model instances in existing scenes and their map-builder paths were retained. The catalog, runtime drops and Clinic operation use the new models. A future migration of static map organ props would require a separate scene revision. Multiplayer host/client behavior was not exercised in this offline i04 check. No review bridge was run, as the current V19 protocol explicitly requests stopping after handoff.

Handoff completed 2026-10-14 18:14 Moscow: Play stopped, Unity lock released with G21 done, and the scene chain updated with an asset-only note retaining i04.
