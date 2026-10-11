# Master v02 digitizing — handoff (Claude → GPT), 2026-10-07

Done by Claude (logical stop point = the FRAME is finished; district tracing had just started and was stopped, no fragments finished):
- `m2_frame.json` — the pixel→metre transform for REF_FEDYA_MASTER_v02_map.png (1280×714): scale bar measured (0.98644 px/m, 1.0137 m/px, ±0.5 %), origin = bottom-left of the land bbox at source px (6, 684), x east, y north (Unity: x, height, y), crop list with offsets/scales, notes (right 53 px is a dark viewer margin; object/base key labels are unreadable even at 3–4×).
- `m2_crop_<district>.png` + `_grid.png` — 2–3× upscaled crops per district (01 forest … 09 beach), whole map and legend, with metre grids.
- `m2_fragment_template.json` — the fragment format a district tracer writes (district polygon, roads with class/width, buildings with footprint/kind/floors, water, beaches, fields, trees, points, fences, labels) — compatible with the plan v14 JSON schema.
- `m2_v14_struct.txt`, `m2_v14_samples.txt` — summary of the v14 plan schema and sample records (what map_plan_v14.py writes and the downstream tools read).
- `m2_frame_setup.py`, `m2_frame_tools.py` — the scripts that made the frame and helper functions (px↔m conversion, crops).
- `m2_mask_water_partial.png` — a partial water segmentation from the network tracer (sea/river/lakes), use as a hint only.
