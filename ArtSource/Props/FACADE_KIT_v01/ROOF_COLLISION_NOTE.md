# ROOF_COLLISION_NOTE — full roof colliders, including the ridge (for the Unity builder)

**Known bug:** gable roofs had colliders only on the walls or slopes, so the ridge had a gap. The van or the player fell through or snagged there.

## Recipe (pick one per roof; both are fully closed)
1. **Convex hull of the whole roof (recommended for simple gables/hips).**
   Collect the eave rectangle (4 corners at eave height) + ridge endpoints (2 points, or 1 for a pyramid hip),
   build ONE `MeshCollider{convex=true}` from those points (≤ 6 verts, 8 faces). The ridge is a hull edge → no gap.
2. **Box + wedge (for L/T roofs or roofs with overhangs).**
   - Box: wall footprint × (0 … eave height) — the building body.
   - Wedge per roof wing: triangular prism (eave-L, eave-R, ridge) × wing length, **extended 0.05 m past the ridge
     line and overlapped 0.1 m with neighbouring wedges** at valleys/hips. Each wedge is its own convex MeshCollider.
   - Overhang: make the wedge base = roof outline incl. overhang (not the wall footprint).
3. **Ridge caps from FACADE_KIT_v01** (`FK_G_RidgeCap_*`) carry their own `UCX_` wedge (±0.25 m, −0.2…+0.09 m),
   which plugs any remaining seam if the roof mesh collider is a non-convex MeshCollider built from slopes only.

## Rules
- Never rely on a plane/quad collider for a slope (one-sided, thin → tunnelling). Use closed convex volumes.
- Flat roofs (khrushchevka, Downtown): one box from the wall top to the roof surface + parapet boxes (the kit parapets have UCX).
- Layer: same `Static/Building` layer as the walls; no gaps > 0.02 m between body box and roof volume.
- UCX import: for each child named `UCX_<piece>_NN` → add `MeshCollider(convex=true, sharedMesh=its mesh)` on the
  piece root and disable/destroy the UCX renderer object (Unity does not do this automatically).
- Check: cast a ray straight down every 0.5 m over the roof footprint; every ray must hit the roof collider.
