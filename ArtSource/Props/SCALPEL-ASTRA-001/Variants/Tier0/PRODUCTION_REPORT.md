# Knife tier 0 — KNIFE-TIER0-ASTRA-001

2026-10-01, WORK_SYNC TASK-000035. Ready for the owner's personal visual review; do not start tier 1 before acceptance.

## Generation and permission

The owner personally approved these exact Rev01 FRONT/LEFT/RIGHT/BACK PNGs: «Да, утверждаю эти четыре фото — запускай за 100». Reference hashes and ordinary ChatGPT High provenance are in Source/TripoViews/Rev01/REFERENCE_MANIFEST.md. The new follow-up asked for a polygon budget matching the simplified existing props.

One Tripo Smart Mesh P2.0 multi-view model, generation count 1, Quad topology, target 500 (UI minimum; maximum 25000). Immediately before the only Create click the exact enabled button read **Создать 100**. Balance **1280 → 1180**, actual expense **100 credits**. No paid texture/remesh/retry action. Generated model: https://studio.tripo3d.ai/ru/workspace/generate/rusty-folding-knife-with-brown-handle-and-metal-blade-10ad3e81-a321-4119-9b2c-fb21fb193456 . Raw FBX: Source/Tripo/KNIFE-TIER0-ASTRA-001_Tripo.fbx.

After obtaining the model, all four input photos were removed. The four empty labelled FRONT/LEFT/RIGHT/BACK slots were visually verified. Raw export downloaded to Windows Downloads; the browser download-event wait timed out, but the completed 32992-byte FBX was found and successfully imported. Do not regenerate because of that event timeout.

## Authoring and budget

| Item | Raw Tripo | Final Blender/FBX | Unity imported |
|---|---:|---:|---:|
| Polygon faces | 524 | 105 (quads and ngons) | triangulated |
| Render triangles | 1006 | 252 | **248** |
| Geometry vertices | 534 | 134 | 452 split UV/normal vertices |
| Meshes / materials | 1 / 1 | 1 / 1 | 1 / 1 |

Unity removes exactly four zero-area triangles caused by collinear ngon corners: Blender reimport checked those triangle areas are 0. The four dropped triangles do not carry a visible surface. This explains 252 authoring tris vs 248 engine tris, rather than concealing the importer difference. Final engine reduction from source: approximately 75.3%; not an FPS measurement.

Source silhouette was sampled from projected side faces and simplified. Handle rebuilt as a closed prism with a single segment chamfer; blade rebuilt as a straight, planar closed prism centred on the handle, constant **1.6 mm** thickness. Two eight-sided pivot discs retained as the recognizable folding-joint cue. Raw blade was thick and offset; that was corrected. Final Blender dimensions **180 × 12.3 × 33.15 mm**; Unity axes **180 × 33.15 × 12.3 mm**, root scale 1. This is a fixed open knife; no folding animation was requested or implemented.

Dark brown handle, dull grey blade and restrained rust/wear spots baked as color only into **Textures/Knife0_BaseColor.png**, **512×512**, one UV map, one matte material. No normal/displacement detail, metallic reflection or costly procedural game shader. Blender roughness .88; Unity URP Lit smoothness .12, metallic 0 and specular highlights off. Game FBX embeds the atlas; the separate atlas is supplied for the Unity material.

## Files and validation

- Editable model: KNIFE-TIER0-ASTRA-001.blend; export: KNIFE-TIER0-ASTRA-001.fbx.
- TECHNICAL_VALIDATION.json and FBX_VALIDATION.json: one closed mesh, no boundary/nonmanifold edges, finite coordinates, UV/material/texture counts, dimensions and source/final mesh budgets checked.
- Previews/01_front.png, 02_back.png, 03_three_quarter.png, 04_other_three_quarter.png, 05_top_edge.png, 06_game_distance.png: all rendered from the final baked material and final geometry. The sixth image is a smaller comparative view, not a screenshot from gameplay.
- Unity imported FBX + texture + material and KnifeTier0Visual.prefab under Assets/OnlyVolunteers/Props/KnifeTier0Astra. Unity 6000.5.11f1 batch import verified 248 triangles, one mesh/material, length .18 m, root scale 1 and valid prefab mesh references. Validation JSON/log are in local task outputs; temporary Editor audit code removed afterward.

Unity prefab is a visual asset for later placement. It is not registered as a new FishNet pickup or spawned into NetworkTest yet. Existing tier 2, network code, grab tuning and scenes remain as before this task. No new two-player playtest or build is claimed.

## Review and delivery

Six final PNGs sent as actual attachments to ordinary «Федя чат»: https://chatgpt.com/g/g-p-6aadbaaa21c081918dcf9006013794cd/c/6aadbae4-9db8-83eb-b549-cced1b1c33b2 . Its independent recommendation: recognizable, matte, consistent with the existing simple props; no mandatory correction, angular joint acceptable. This is advice, **not the owner's personal acceptance**. Owner review pending. No local Blender window opened under the latest request. PC remains Remote Idle / HDR off.
