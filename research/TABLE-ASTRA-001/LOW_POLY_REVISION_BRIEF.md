# TABLE-ASTRA-001 — low-poly reference revision

Status (2026-09-29): first four views in `Source/TripoViews/` were rejected as too detailed. A new concept is saved at `Source/Concept/02_low_poly.png`. The user approved the Rev03 four-view set in `Source/TripoViews/Rev03/`, generated in the ordinary FEDCHER ChatGPT chat with High (3/3) reasoning. Exactly one Tripo multi-view job consumed 100 credits. The Blender model and six review renders are ready; await the user's visual approval of the modeled asset. Ordinary chat: https://chatgpt.com/g/g-p-6aa6b8a4108c81919e59c95ac93a1145-fedcher/c/6abb70ee-6638-83eb-bf8e-231fcd5b8807

## Required visual changes

- Stylized, relatively low-polygon game prop, with broad readable forms and no photoreal surface texture.
- Matte, rough dark-gray frame with minimal reflections; muted blue-gray padded top.
- Straight rectangular frame with four simple legs and one lower longitudinal brace. Avoid extra beams and decorative hardware.
- No individual tiny bolts, visible screws, complex caster forks, wheel spokes, tread, or elaborate brake assemblies. Four thick simple wheels only, one at each corner, each with a clear rotation axis and steering pivot silhouette.
- Two thin flat dark bands across the mattress, with at most a small flat buckle or loop. No bulky clamps or layered strap fasteners.
- Single simple push handle at the foot end. Slight raised head pad at the opposite end, kept identical in all views.
- No person, tools, blood, labels, logos, electronics, hospital rails, folding X frame, or extra wheels.

## Rigging and movement status

The frame, four caster steering pivots, and four wheel roll pivots are separate. Four simple circular 24-sided wheels use a 0.105 m radius and 0.035 m caster trail. Distance-based rolling and caster steering are implemented, shown in an 18-second Blender motion preview, and tested with the actual FBX in an isolated Unity project. Production scene/body collision integration remains pending. See `PRODUCTION_REPORT.md` for evidence and limits. No additional Tripo generation was needed.

## View convention

1. FRONT: narrow foot end with push handle toward camera.
2. LEFT: long profile, head pad left, handle right.
3. RIGHT: opposite long profile, head pad right, handle left.
4. BACK: narrow head end, no second handle.

All four views should show the same fixed table, proportions, colors, two straps, four wheels, and lighting on a neutral background at 4:3. Use low-detail studio-render style and near-orthographic camera framing. Keep the table fully visible.

The old ordinary chat “ВЧ ЧАТ 2” reached its maximum length after the first set. The replacement set was made in a new ordinary FEDCHER project chat, not in Codex Work.

Visual QA note: Rev02 had inconsistent wheel rims and an extra lower crossbar in 04 BACK. Rev03 replaces 03 RIGHT and 04 BACK with simpler dark disc wheels and removes that crossbar. This is the approved Tripo input set.
