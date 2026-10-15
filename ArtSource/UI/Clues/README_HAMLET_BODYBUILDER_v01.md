# G31 — HAMLET_BODYBUILDER clue card v01

Three portrait PNGs (768 × 1152, RGB), for Fedya's visual selection:
- CLUE_HAMLET_BODYBUILDER_v01.png — three-quarter view, resting beneath the bar.
- CLUE_HAMLET_BODYBUILDER_v01b.png — opposite-side view, raised pull-up pose with feet off the ground.
- CLUE_HAMLET_BODYBUILDER_v01c.png — closer, tilted oblique snapshot.

The procedural set suggests the Khutor square through a simple iron pull-up bar, uneven timber fence, grass, and a house edge. Warm low morning sunlight, mild optical softness and slight shutter motion suggest a candid phone capture. The bottom 18% is a caption area with replaceable ASCII text; KHUTOR / 06:00-10:00 identifies the clue's location and morning window. Final Russian copy is intentionally left for the UI pass.

Source (opened, never saved):
C:\Dev\Game\ArtSource\Characters\SAUSAGE_BUDDY_01\Types\HAMLET_BODYBUILDER\SAUSAGE_BUDDY_HAMLET_BODYBUILDER_v04.blend
SHA-256 before/after: E1A5675B44E583EFFF8279BDB485185466793C6CF1128BA4306847F8867AC125

Background-only rendering command (PowerShell):
```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b 'C:\Dev\Game\ArtSource\Characters\SAUSAGE_BUDDY_01\Types\HAMLET_BODYBUILDER\SAUSAGE_BUDDY_HAMLET_BODYBUILDER_v04.blend' --python 'C:\Dev\Game\ArtSource\UI\Clues\render_clue_hamlet_bodybuilder_v01.py'
```
The script protects existing outputs. For a future delivery, change to a new numbered revision. The --replace-draft argument was used only while reviewing unfinished images in this task. The script builds the set and poses in memory and contains no blend-save operation. No extra models, textures, or fonts are required.

Verification:
- PASS: three PNGs rendered in Blender 5.2.1 LTS background CLI and visually inspected.
- PASS: source SHA-256 unchanged.
- PASS: all five deliverable files exist under C:\Dev\Game\ArtSource\UI\Clues.
- No Unity, scene edits, operation assets, commits or pushes.
- Blender reported that the source was written by a newer binary build; it loaded and rendered successfully. The source was not resaved.
- OPEN: Fedya's preferred variant and final caption text.
