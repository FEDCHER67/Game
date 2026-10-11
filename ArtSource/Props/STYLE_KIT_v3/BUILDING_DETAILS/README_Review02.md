# G12 — preview placement refinement, review02

The 33 module meshes, master, FBXs, triangle counts and validation remain **v01**. No geometry changed after export. `README.md` contains the full English module table, material contract, pivots and snapping rules. This addendum identifies the final review previews; all first-pass previews remain intact.

Final preview files:

| View | Relative path |
| --- | --- |
| All 33 modules plus 1.75 m scale box | `Previews/v01/01_all_modules_lineup_review02.png` |
| Three-storey plaster townhouse | `Previews/v01/02_townhouse_eye_3q_review02.png` |
| Five-storey panel block | `Previews/v01/03_panel_block_eye_3q_review02.png` |
| One-storey shop and striped awning | `Previews/v01/04_shop_eye_3q_review02.png` |

The three matching `*_plain_box_same_camera_review02.png` files use the identical camera/light with the modules hidden. `preview_manifest_v01_review02.json` records dimensions, storeys, module instances and the 1.75 m camera elevation. The editable final demonstration scenes are in `SK3-BLDDETAILS-001_Demos_v01_review02.blend`; they are excluded from the export master.

Changes after inspecting the first four renders:

- The townhouse gas run stops on each side of the entrance instead of crossing the doorway. Its plinth also leaves the porch opening clear.
- Townhouse and shop cornices stop at the half-metre corner sockets. Actual `CORNICE_CORNER` instances close their convex corners without overlapping straight pieces.
- The panel-block demonstration box is 14.0 m wide, matching fourteen unscaled parapet modules. Its floor pitch remains 2.8 m; the short end remains blank as required by the style bible.
- The lineup centres modules within the wall panels, moves their names above the meshes and prints actual triangles / maximum. The canopy brackets now fit within their panel.

To add missing review02 previews without replacing anything:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python ArtSource/Props/STYLE_KIT_v3/BUILDING_DETAILS/build_building_details.py -- --revision 1 --preview-existing --review-previews --samples 32
```

The mode compares all 33 geometry hashes with the original validation before rendering. Existing PNGs, master, FBXs, validation and preview project files are skipped. For geometry changes, use a new numbered revision.
