# TABLE-ASTRA-001 — design proposal

Status (2026-09-29): user explicitly approved the base design shown in the ordinary ChatGPT conversation “ВЧ ЧАТ 2”, then requested a lower-polygon, more matte revision. The first concept is `Source/Concept/01_three_quarter_draft.png`; its four first-pass views under `Source/TripoViews/` are rejected as too detailed. The revised concept is `Source/Concept/02_low_poly.png`, and the four approved views are under `Source/TripoViews/Rev03/`. They were generated in the ordinary FEDCHER ChatGPT conversation https://chatgpt.com/g/g-p-6aa6b8a4108c81919e59c95ac93a1145-fedcher/c/6abb70ee-6638-83eb-bf8e-231fcd5b8807 with High / 3 of 3 reasoning. The user explicitly approved those exact PNGs before one paid Tripo generation. The Blender asset is now ready for visual review; see `PRODUCTION_REPORT.md`.

## User revision for the game's art direction (2026-09-29)

The game as a whole uses a relatively low-polygon style. Redesign this table as a simpler, readable game prop: no individually modeled tiny bolts, complex multi-part wheel forks, or bulky high-detail strap buckles/attachments. Use broad forms, simple wheel hubs and supports, flat restraint bands, and a matte dark-metal finish with weak highlights. Keep enough shape for a clear table silhouette and four functional-looking caster wheels. The first-pass photorealistic views under `Source/TripoViews/` are revision references only, not approved Tripo inputs.

Wheel motion is now implemented with separate circular wheels, roll/steering pivots and positive caster trail. The 18-second Blender video demonstrates distance-based roll and steering through forward, reverse, curved, lateral and in-place movement. Actual FBX import and component checks passed in isolated Unity 6000.5.11f1; production frame collision and gameplay integration are still pending. See `PRODUCTION_REPORT.md`.

## Role in VOLUNTEERS ONLY

One early-game prop combines a simple operating surface in a garage/basement with a movable NPC gurney. The current canon describes an improvised first laboratory, physical interaction with the table and tools, reduced NPC resistance after fixation, and wheeled transport as a gameplay pillar (`docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md`, sections 28 and 37–44).

## Visual references (shape and function only)

1. [Midmark Ritter 203 treatment table](https://www.midmark.com/docs/default-source/product-literature/medical/manual-examination-tables/ritter-manual-examination-tables-literature.pdf?sfvrsn=bfb12ddc_3): simple, flat, human-length padded top and visible four-leg structure. Use the clear top silhouette, not its brand, exact dimensions or clinical color scheme.
2. [FERNO Model 35A cot](https://ferno.com/getmedia/36ba8c8c-177c-45fd-aac9-17701a6c8865/Product-Guide_US_2022_V3.pdf): four-wheel mobile base, end handles and compact side restraints/rails. Use these functional cues, not the complex folding X-frame.
3. [Harbor Freight Yukon 48-inch workbench](https://www.harborfreight.com/48-in-workbench-w-light-58695.html): broad square-tube steel-frame language suited to an improvised garage. Do not copy its lamp, pegboard, drawers or branding.

## Recommended design A — improvised mobile procedure table

- Low, sturdy rectangular four-leg frame made from broad square tubes, with a clearly visible lower cross brace.
- Long, flat one-piece padded top, rounded corners and a slightly raised head pad; no articulated backrest in the first version.
- Four chunky caster wheels, with two visible brake tabs. One end has a broad push handle.
- Two wide simple restraint bands across the top, modeled as separate pieces in Blender after Tripo if the generated mesh fuses them. Keep a broad unobstructed center area for later gameplay interaction.
- Approximate human scale: 1.9–2.0 m long, 0.7–0.8 m wide, 0.8–0.9 m high. Exact Unity scale to be checked against the project character rig.
- Material direction after geometry: matte dark steel frame, muted blue-gray or desaturated burgundy pad, pale utilitarian bands; restrained wear only. No blood, logos, text, patient, tools or clinical electronics on the base model.

The first concept image should show this as one readable object in a clean three-quarter view. After the user approves the design, generate four exact neutral-background front/left/right/back PNGs in ordinary ChatGPT, send those PNGs to the user for a separate approval gate, then consider one Tripo multiview generation. Do not infer image approval from concept approval.

View convention for the four Tripo slots: front = narrow foot end with push handle; back = narrow head end with raised head pad; left/right = opposite long sides. Keep the same fixed rest pose, body proportions, wheel count, straps, materials, background and camera height across all four images.
