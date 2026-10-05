# COOLER-ASTRA-001 — provenance

## Approved reference images

- Date: 2026-10-05.
- Service: ordinary ChatGPT, image generation in «Федя чат».
- Conversation: https://chatgpt.com/g/g-p-6aadbaaa21c081918dcf9006013794cd-only-volunteers/c/6aadbae4-9db8-83eb-b549-cced1b1c33b2
- Brief: white/blue portable organ cooler, raised U-shaped handle, closed lid, two front latches, short feet, front-only biohazard sticker «ОРГАНЫ / НЕ КАНТОВАТЬ».
- Approval: explicit user message relaying Claude/Fedya's approval of **COOLER Rev02**, four consistent views, sticker only at front.

`Source/TripoViews/Rev02/01_front.png` and `02_left.png` are unchanged Rev01 images. `03_right.png` corrects the original pivot/proportion error; `04_back.png` restores body width and a blank rear wall. All four are separate 1254×1254 PNGs. Rejected Rev01 RIGHT/BACK remain intact.

Generated PNGs were transferred unchanged from ChatGPT file previews. No local cropping, resizing, drawing or colour editing was applied to reference images. Hashes in `Source/reference_manifest_Rev02.json` were checked against stored files.

## Tripo generation

- Model: https://studio.tripo3d.ai/ru/workspace/generate/90bcd79c-274a-4547-aa47-4095f2fef721
- Inputs: exact approved Rev02 FRONT, LEFT, RIGHT, BACK.
- Settings: multi-view image-to-3D, Smart Mesh, quads, P2.0; lowest available target setting (500). Actual budget reduction performed locally.
- Exactly one Create action at **100 credits**; balance **780 → 680**.
- UI result: 549 faces / 556 vertices; original FBX import: 992 triangulated faces.
- Original export: geometry-only FBX; no paid textures, retopology or repeat generations.
- Input slots cleared after generation.

Evidence: `Source/tripo_before_create_100.png`, `Source/tripo_generated_680.png`, `Source/tripo_slots_cleared.png`.

Original export retained at `C:\Dev\Game\Working\Tripo\cooler_tripo_base.fbx`; original download retained at `C:\Users\Zeyo-ne\Downloads\cooler_astra_001_tripo_base.fbx`.

Original FBX SHA-256: `3F5789976424D370729622B7758396A98623DBCE8FBDE4275EB2CA8F9FC532FA`.

## Local finishing

Blender 5.2.1 LTS. Repaired openings and one internal branch, seated feet, reduced only the large body surface, retained handle/hardware, smooth shading, UV atlas and FBX export. Original source mesh was not replaced with a separately generated model.

The approved FRONT sticker was projected in the material onto existing front wall faces and baked into a 2048px atlas. Solid colours and the smooth lid/body colour boundary were baked locally. No separate lettering geometry or paid texture service.

v01 is retained as local history; v02 corrects its jagged colour boundary. Final mesh/FBX: 880 triangles, 14 closed component shells in one assembled object. Both validation reports pass. Seven final preview views inspected.

These records describe source and processing history; they do not make an independent licensing claim about provider outputs.
