Branch claude/facade-kit-v01 from main; push; DRAFT PR into main. Reasoning: xhigh.

Context: VOLUNTEERS ONLY, map v76 (Vadim) is being built in Unity by GPT chat G43. Fedya wants buildings with real 3D volume (not flat 2D-looking facades) and full collisions (known bug: roof ridges had no collision). Blender works headless via `pip install bpy`. Textures will be re-chosen later: clean UVs + placeholder materials. Credits limited: efficient, but quality matters.

Read docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v01.md (§2, §5: Rough §5.4 khrushchevkas with 3D balconies glazed/open + classic entrances; Downtown §5.5 fire escapes in alleys, AC units, rooftop water tanks; Hamlet §5.2; Construction §5.3; Beach/Elite villas), Working/Reviews/Textures_2026-10-17/TEXTURE_DECISIONS.md (KH_windows_atlas_v01; frames, sills, cornices as geometry), and existing props in ArtSource/Props for the stylized low-poly look.

Build with bpy, headless, a modular FACADE KIT in ArtSource/Props/FACADE_KIT_v01/:
- Rough (khrushchevka): balcony open, balcony glazed, entrance canopy, entrance steps 2/3, iron door frame, window frame + sill (fit KH1b 12.8x11.2 m grid; document window pitch), drainpipe, roof parapet, roof vent.
- Downtown: fire escape modules (landing + stair + ladder, stackable), window frame/sill/lintel, cornice, AC unit, rooftop water tank on stand, parapet, storefront awning, alley dumpster.
- Hamlet: porch roof + posts, window with shutters, steps, chimney, gutter.
- Generic: roof ridge caps (slate/metal/tile).
Rules: 1 unit = 1 m; pivots on the attach plane (documented); floor height 2.8 m (Rough) / 3.5 m (Downtown); each piece <= 600 tris (most <= 200); clean UV0 + placeholder material per kind; every solid piece has UCX_ convex colliders (balconies/canopies/steps/landings solid, railings thin boxes); LOD1 for pieces > 150 tris. Export each piece as FBX (Unity axes) + one library .blend + JSON manifest (name, size, pivot, attach type, collider count, tris).
Also ROOF_COLLISION_NOTE.md: robust recipe for full roof colliders incl. ridge (convex hull or box + wedge) for the Unity builder.
One contact sheet PNG (headless) of all pieces with a 1 m grid + a sample khrushchevka bay and a Downtown alley corner assembled from the kit. .fbx/.blend/.png are LFS-tracked. Concise final summary.
