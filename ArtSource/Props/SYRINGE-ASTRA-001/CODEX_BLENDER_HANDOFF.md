# SYRINGE-ASTRA-001 — Blender handoff for the PowerShell Codex session

Send this task only after `Working/Tripo/syringe_tripo_base.fbx` exists and has been inspected. The Tripo mesh is the uncolored starting point.

## Task

In `C:\Dev\Game-main`, finish the approved syringe as a stylized, Unity-ready prop for VOLUNTEERS ONLY. Read this file, `TRIPO_WORKFLOW.md`, `REFERENCE_PROPOSAL.md`, the four numbered images in `Source/TripoViews/`, and the current organ preview images and technical reports under `research/LUNGS-ASTRA-001/`, `research/HEART-ASTRA-007/`, `research/KIDNEY-ASTRA-001/`, and `research/BRAIN-ASTRA-001/`. Use the organ assets as the visual benchmark for clean, soft, matte, readable forms. The approved syringe is option A: short thick transparent chamber, broad finger flange, oversized thumb pad, and an elegant tapered hub with a fine needle.

Import `C:\Dev\Game-main\research\SYRINGE-ASTRA-001\Working\Tripo\syringe_tripo_base.fbx`. Preserve the original Tripo export. Repair or rebuild individual parts as needed so the final silhouette stays faithful to the four views and works in game. Use separate, clearly named pieces for barrel, plunger, stopper, hub, and needle. Make an internal blood fill mesh that is legible through the chamber; its height must support EMPTY, PARTIAL, and FULL states. Animate blood being drawn into the syringe: as the thumb pad and stopper retract together, the red fill rises smoothly from the needle end into the clear chamber. Expose a simple fill parameter or clearly named animation clips so Unity can drive the same motion. Avoid realistic gore, wet shine, crosses, borrowed logos, and tiny markings that disappear at game camera distance. Treat the Tripo result as geometry input, not an authority for materials, topology quality, or mechanical separation.

Create clean stylized materials to sit beside the finished organs: soft matte neutral plastic, controlled translucent chamber, dark warm blood red, and restrained metal. Choose actual colors after visually comparing the organ renders, not by copying arbitrary web reference colors. Keep the fine needle readable and avoid making it oversized. Use practical geometry and material counts for a small interactable prop; inspect normals, unwanted holes, smoothing, transforms, pivots, and scale. Give the plunger a usable local axis. Keep any review lights and cameras out of the game FBX.

Deliver `C:\Dev\Game-main\research\SYRINGE-ASTRA-001\SYRINGE-ASTRA-001.blend` and `C:\Dev\Game-main\research\SYRINGE-ASTRA-001\SYRINGE-ASTRA-001.fbx`, plus front, rear, left and right three-quarter, side, and close-up previews under `Previews/`. Include a short technical report naming the separate pieces, fill control/animation, materials, geometry counts, validation, and any known Unity import limits. Reopen the `.blend`, reimport the FBX in a clean Blender scene, and visually check the saved result.

When the final `.blend` has been saved and checked, run:

```powershell
& 'C:\Dev\Game-main\tools\Show-AssetForReview.ps1' -BlendPath 'C:\Dev\Game-main\research\SYRINGE-ASTRA-001\SYRINGE-ASTRA-001.blend' -AssetName 'Шприц'
```

This must open the finished model visibly in Blender and play the completion alarm. Leave Blender open for user review. Report the exact output paths. Do not edit unrelated work, gameplay code, Unity scenes or prefabs, package files, project settings, third-party code, or `Assets/_Recovery/`. Do not run `git reset`, `git clean`, `git restore`, `git stash`, `git commit`, or `git push`.
