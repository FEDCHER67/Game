# COOLER-ASTRA-001

Portable white/blue medical organ cooler, matching the clean, slightly puffy style of existing inventory props. Final revision: **v02, 880 triangles**, within the approved 500–900 budget.

## Deliverables

- `COOLER_ASTRA_001_v02.blend` — editable source, packed texture, preview camera and lights.
- `COOLER_ASTRA_001_v02.fbx` — mesh-only export with embedded texture.
- `Textures/COOLER_basecolor_v02.png` — 2048×2048 colour atlas.
- `Previews/01_front_v02.png` through `07_hero_v02.png` — front, back, left, right, top, bottom and hero.
- `REPORT.md`, `PROVENANCE.md`, `Validation/mesh_v02.json`, `Validation/fbx_roundtrip_v02.json`.

v01 is preserved as local history. Use v02: it fixes the triangle-shaped lid colour boundary without spending credits or changing the triangle count.

## Model

- Object: `Item_OrganCooler`; 468 vertices, 654 polygons, 880 triangulated faces.
- Overall size: 40.00 × 23.74 × 35.35 cm, raised handle included.
- Front -Y; Z up; origin centred at the floor; smooth shading.
- One mesh object, 14 closed component shells for body, handle, feet and hardware. This is an assembled prop, not a single continuous welded shell.
- White body, blue closed lid and raised U-shaped handle, navy front latches and rear hinges, four short feet.
- Biohazard sticker «ОРГАНЫ / НЕ КАНТОВАТЬ» baked onto the existing front wall, readable in front/hero previews. Rear and sides blank. No lettering geometry.
- Static closed container; contents/ice not visible. Lid/handle animation and gameplay behaviour not included.

## Source and workflow

Rev02's four 1254×1254 views were explicitly approved in this chat on 2026-10-05. FRONT/LEFT reuse Rev01 unchanged; corrected RIGHT/BACK are from Rev02. Rejected Rev01 views remain intact.

One Tripo multi-view Smart Mesh / quads / P2.0 generation, **Create = 100**, balance **780 → 680**. No repeat generation, paid texturing or paid retopology. Inputs cleared. Original FBX: `C:\Dev\Game\Working\Tripo\cooler_tripo_base.fbx`.

Local Blender repair closed source openings, removed an internal flap, seated four feet and simplified only broad body surfaces. Mesh validation and independent FBX re-import passed. Exact results in the report.
