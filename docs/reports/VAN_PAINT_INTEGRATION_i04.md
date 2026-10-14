# G20 — van paint in v19 i04

2026-10-14, 17:53 Moscow. Implemented and verified in Unity 6000.5.11f1.

## Result

- New scene: `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i04_vanpaint.unity`, copied from **i03 sky**, without rebuilding the map.
- Grandpa's hut exists: plan `ArtSource/References/Map/Greybox/greybox_v19_build_v07_flat.json`, building `02_B02` / `grandpa_hut_base2`; scene object `B_02_B02`. Four coloured cans and a brush stand beside it at **(183.40, -0.05, 523.30)**, clear of the entrance steps. No fallback location was needed.
- The **real player van** has six paintable renderers, including its moving doors. New mesh/material copies are scene overrides; the original prefab, physics colliders, Rigidbody and driving scripts remain unchanged. Mesh triangle queries follow each door transform and respect world obstructions. No extra MeshColliders were added to the dynamic van.
- The test scene is `Assets/OnlyVolunteers/Scenes/Dev/VanPaint_Test.unity`. Its core implementation and limits are documented in `docs/reports/VAN_PAINT_PROTOTYPE.md`.

## Files and integration hooks

All paint assets/code are under `Assets/OnlyVolunteers/Vehicles/Paint/`, with matching Unity metas:

- `Runtime/`, `Shaders/`, `UI/`, `Editor/`, `Generated/`: complete prototype, guarded test builder, and verification helpers.
- `Runtime/VanPaintMeshQuery.cs`: moving-mesh UV ray queries without physics changes.
- `Integration/VanPaintMapMode.cs`: first-person paint mode and temporary input ownership.
- `Integration/Editor/VanPaintMapInstaller.cs`: guarded, new-only i03 → i04 installer.
- `Generated_i04/`: six copied paint meshes and two body materials.
- Development sources remain in `ArtSource/Dev/VanPaint_staging/`; complete sets were compiled there before import under the G20 lock.

**No existing gameplay source hooks were changed.** The new scene adds components to the van, held-prop anchors to the player camera, a station, HUD and input adapter. The adapter temporarily disables grab, inventory, contextual interaction and phone controls while painting, then restores only the components it disabled. Walking and mouse look continue; lettering temporarily locks movement and releases the cursor.

## Controls

| Input | Action in the map |
|---|---|
| B, aiming at a brush/can within 3.5 m | Pick up; starts paint mode. Pick both tools. |
| B, aiming away from paint props | Stow both tools at the station and restore normal gameplay. Stow before entering the van or using the phone. |
| Hold LMB, aiming at the body | Paint in the held can's colour. |
| Wheel | Change brush size. |
| V, aiming at the body | Open lettering at the aimed spot. Enter/button stamps; Esc cancels. |
| Z | Undo last stroke/stamp. |
| Delete twice within 3 seconds | Wipe all paint. |
| J / L | Save / load. |

The map uses the player's crosshair; it does not use the test scene's orbit camera. Saves are explicit, per van, under `persistentDataPath/VanPaint/hamlet-player-van-g20/`. The test van uses a separate identity. PNG and JSON generations preserve older saves. The verified blue stroke and «ТЦК» design remain in this machine's local save; another machine starts blank.

## Verification

| Check | Result |
|---|---|
| Test scene | PASS: brush/can pickup, 71 ray samples, mask at correct UV, «ТЦК», exact undo, data-command replay/duplicate rejection, save/re-enter Play, wipe/reload and undo after reload. Evidence: `verification_before_restart.txt`, `verification_after_restart.txt`. |
| Real van in map | PASS: 71 ray hits; blue stroke; Forest-colour «ТЦК» through the actual UI field and a targeted Enter event; exclusive input and modal restoration; exact undo; save/restart exact PNG and journal; wipe/reload; undo after load. |
| Moving door | PASS: fully open driver door query matches its rendered triangle UV; paint and exact undo passed. |
| Pickup/stow | PASS: three repeated cycles preserve prop scale and restore normal input. |
| Walking/driving | PASS: existing route harness, 111.5 m orchard walk and 137.5 m Hamlet drive, peak 43.7 km/h, zero airborne frames. Existing chassis/ground contact matches i03. `Working/Reviews/Map_v19_Pilots/routes_g20_i04_v01.json`. Crowd/police are suppressed by that harness for repeatability. |
| Final scene | PASS: Play stopped, i04 saved clean, zero Console errors, zero missing scripts, all new asset metas present. Existing unrelated obsolete-API/serialization warnings remain. |
| Preservation | PASS: i03 scene, original van prefab and ProjectSettings file hashes unchanged. No existing scene blocks removed; changed blocks are the van/player prefab overrides and root list. Trees, terrain, grass and sky scene blocks are unchanged. `Working/Reviews/VanPaint/preservation_i04_v01.json`. |

Map PNG SHA256 after save/restart: `938411EFC72A7AC08F4D3CBDD9429A52B15FD6907C0BFC7A491457A0CEA8533F`. Checks use real Play objects, rays and UI handlers through MCP; they do not claim a human keyboard/mouse feel test.

## Captures and limits

Final review set in `Working/Reviews/VanPaint/`: `01_Test_Paint.png`, `02_Test_Text_Undo.png`, `03_Test_Restored.png`, **`04_Map_Hut_Station_v02.png`**, **`06_Map_Restored_Open_Door.png`**. These are 1600×900 renders from Play cameras. Earlier `04_Map_Hut_Station.png` and `05_Map_Painted_Van.png` are retained intermediate captures, before moving the table clear of the steps; they are not the final station layout.

Prototype limits: six planar UV islands; no seam wrapping; uppercase Cyrillic/Latin/digits and limited punctuation, up to 24 characters; 1024² mask; synchronous undo/readback/save; bounded stroke history; no save cleanup, autosave or networking. Stroke data/events support a later ordered replication adapter. Performance under sustained heavy painting and multiplayer are not verified.

The shared map builder was not edited: a future rebuild must preserve/reapply the tree, grass and sky chain, then run the same paint installation against a new destination. The installer deliberately refuses existing i04/generated outputs. No commits, deletions, WORK_SYNC edits, global URP/settings changes or window operations. No review bridge, per the current integration protocol.
