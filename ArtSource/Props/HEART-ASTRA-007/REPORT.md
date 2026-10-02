# HEART-ASTRA-007 — current candidate audit

## File and decision

- **Human visual selection:** YES. `Working/Heart_Astra_007_v6.blend` is the current candidate by the human handoff. This audit does not replace that choice.
- **Exact path:** `C:\Dev\Game\_worktrees\fedya-player-v2\research\HEART-ASTRA-007\Working\Heart_Astra_007_v6.blend`
- **SHA-256:** `2017E336992FD2D45427C7AD74688DB1515DD6106906AAC3A0EFE95E79BBB401`
- **Size:** 4,851,997 bytes.
- The candidate was inspected read-only. It was not saved or modified. No Git synchronization was performed.

## Blender technical audit

| Check | Result |
| --- | --- |
| Reopen | **PASS** in Blender 5.2.1 LTS; file reports Blender data version 5.2.44. No file-load error. |
| Scene size at saved frame 55 | Evaluated visible mesh bounds: **0.12021 × 0.08695 × 0.17649 Blender units** (X × Y × Z). The scene unit system is `NONE`; the file's scale marker says 1 unit = 1 metre, which would imply about 12.0 × 8.7 × 17.6 cm. |
| Orientation / transforms | Long dimension along Blender **Z**. Main meshes have unit object scale but nonzero location/rotation; rig has nonzero location/rotation. Unity axis/transform conversion has not been tested. |
| Objects | **27:** 21 meshes (3 main anatomical meshes and 18 surface vessel meshes), 1 armature with **19 bones**, 1 empty scale marker, 3 lights, 1 camera. **0 curves.** |
| Base geometry | **6,048 vertices / 11,606 triangles** across 21 meshes. |
| Evaluated geometry | **9,990 vertices / 19,576 triangles** at saved frame 55, with modifiers evaluated. |
| Materials | **6 node-based procedural materials**; active outputs and links valid. |
| Animation | **6 actions**, each with 190 F-curves. Active action: `Heartbeat | v5 regional amplitude and sculpted return` (4,276 keys). Scene frames **1–85 at 24 fps**. |
| Full-cycle integrity | **PASS:** all 21 meshes evaluated on all 85 frames (1,785 evaluations). No nonfinite vertices, degenerate faces, unstable evaluated counts, invalid skin-weight entries, invalid armature targets, invalid constraints/drivers/material links, or mesh self-intersection pairs found. Frame 1/85 vertex and active-curve seam error: **0**. This is mesh self-intersection testing; it does not constitute a Unity runtime or cross-object contact test. |

## Dependencies

- External images/textures: **0**. Packed image textures: **0**. Unpacked image textures: **0**. The materials are procedural Blender nodes.
- Linked Blender libraries: **0**. External fonts, sounds, movie clips, and volumes: **0**.
- Missing referenced assets: **0** among those categories. No external file is needed for Blender reopen.

## Gates and scope

- **BLENDER TECHNICAL AUDIT:** PASS.
- **TECHNICAL PRODUCTION READY:** **NO — not established.** There is no validated Unity export/import, shader conversion, animation import, rig orientation/scale check, or game performance test for this candidate. The Blender file is internally sound, but that is a narrower result.
- **PROVENANCE CLEARED:** **NO.** See [PROVENANCE.md](PROVENANCE.md): the three main meshes retain third-party source topology, and the source heartbeat action is present. The source license/permission is unverified. Do not promote to production on this audit.
- **HUMAN VISUAL SELECTION:** YES.

No changes were made to HEART-REFERENCE-004, HEART-ORIGINAL-005/006, Player_01, gameplay, project configuration, sibling worktrees, or the candidate `.blend`. **NO COMMIT. NO PUSH.**
