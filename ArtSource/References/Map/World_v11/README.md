# World map v11 — 2D master for the 3D map

Approved by Vadim on 11.10.2026. This plan replaces MAP_PLAN_R01_v12 for geography, district placement, roads and district layouts.

**Read first:** [docs/WORLD_MAP_3D_BRIEF.md](../../../../docs/WORLD_MAP_3D_BRIEF.md). It covers what to build, the vibe of each district, nature, textures, water and the approval steps with Fedya.

- `WORLD_MAP_v11.json` — machine-readable map in metres: origin at the bottom-left of the frame, x east, y north, Unity `(x, height, y)`. `WORLD_MAP_v11_json_check.png` is the same JSON drawn back as a picture.
- `VOLUNTEERS_MAP_v11_FINAL.png` (1 px = 0.2 m), `VOLUNTEERS_MAP_v11_PREVIEW.png`, `VOLUNTEERS_MAP_v11_MASTER.svg` — the approved map.
- `Districts/` — each district cut from the final map at 1:1, the detailed Downtown v16 and Construction v10 plans (Russian specs and legends), and the source plans of Forest, Hamlet, Rough District and City Beach.
- `References/` — look references:
  - Finnish pine forest;
  - modern villa vibe for Elite Hill;
  - four Downtown city shots;
  - two illustrated maps showing the wanted nature harmony;
  - composition illustrations of the Forest, Hamlet, City Beach, Quiet Valley and Rough District.

Source: Vadim's 2D builder `Desktop\Map\00_Сборка_общей_карты\build_v04` (`build_world_v04.py`, `export_world_json.py`) on his PC. Regenerate through Vadim's chat; do not edit these files by hand.
