# FACADE_KIT_v01

Modular 3D facade and roof pieces: 28 pieces for Rough (khrushchevka), Downtown, Hamlet and Generic roof ridges.
They are generated headless by `build_facade_kit_v01.py` (`pip install bpy matplotlib`; `python3 build_facade_kit_v01.py`).
The contact sheet is made by `contact_sheet.py`.

- `FBX/<piece>.fbx`: one piece per file (Unity axes: +Y up, **+Z = out of the wall**). `FACADE_KIT_v01.blend`: the library.
- `FACADE_KIT_v01_manifest.json`: name, size, bounds, attach type, notes, LOD0/LOD1 tris, collider count, materials.
- `FACADE_KIT_v01_contact_sheet.png`: every piece on a 1 m grid, plus a sample khrushchevka bay and a Downtown alley corner.
- `ROOF_COLLISION_NOTE.md`: the recipe for full roof colliders, including the ridge.

## Conventions
- 1 unit = 1 m. Floor height: 2.8 m (Rough) and 3.5 m (Downtown).
- **Pivot = attach plane.**
  - `wall`: the wall face, centre X, bottom of the piece/opening. The piece protrudes outward.
  - `wall+ground`: wall face at ground level.
  - `roof`: roof surface, centre.
  - `roof-edge`: outer wall face at the top of the wall.
  - `eave`: the eave line.
  - `ridge`: the roof apex, with X along the ridge.
  - `ground`: centre of the base.
- Hierarchy: root empty `<piece>`, then either `<piece>_Mesh` (≤150 tris) or `<piece>_LOD0` + `<piece>_LOD1`, then `UCX_<piece>_NN`.
- Colliders: every piece has convex `UCX_` hulls. Balconies, canopies, steps and landings are solid boxes; railings are thin boxes. The builder turns them into convex MeshColliders and hides their renderers.
- UV0: box projection with 1 UV = 1 m, ready for tiling. One placeholder material per kind (`FK_*`); the real textures are chosen later.
- Budget: all pieces ≤ 312 tris. Only 4 pieces are over 150 tris, and they have a LOD1.

## Khrushchevka grid (KH1b 12.8 × 11.2 m)
One texture tile covers **4 bays × 3.2 m pitch** and **4 floors × 2.8 m**.
- Window centre: at the bay centre (1.6 m into each bay).
- Window opening: 1.5 × 1.45 m, sill +0.85 m above the floor.
- Balcony: 2.6 m wide, 1.0 m deep, centred in its bay. Its slab top is at floor level.
- Entrance: in its own bay. Door 1.2 × 2.2 m on the steps (3 steps = +0.48 m). Canopy at +2.95 m.
