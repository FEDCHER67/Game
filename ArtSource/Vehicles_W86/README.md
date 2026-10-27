# G47 W86 world vehicles — Step 1 review package

**STOP: no Unity import or map changes until Fedya sends go.**

Integration allowlist: selected_models_v01.json. Earlier numbered revisions and PANEL_VAN are working history, not integration candidates. The v01 sources/exports are preserved; technical and visual repairs use distinct numbered revisions. Never import whole directories blindly.

| Selected asset | LOD0 / LOD1 / LOD2 triangles | Blender | Visual FBX | Collision FBX | Collision JSON |
|---|---|---|---|---|---|
| SEDAN | 2954 / 1476 / 678 | [SEDAN_v01.blend](C:/Dev/Game/ArtSource/Vehicles_W86/SEDAN/SEDAN_v01.blend) | [SEDAN_v01.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/SEDAN/SEDAN_v01.fbx) | [SEDAN_collisions_v01.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/SEDAN/SEDAN_collisions_v01.fbx) | [SEDAN_collisions_v01.json](C:/Dev/Game/ArtSource/Vehicles_W86/SEDAN/SEDAN_collisions_v01.json) |
| COMPACT | 3124 / 1562 / 718 | [COMPACT_v01.blend](C:/Dev/Game/ArtSource/Vehicles_W86/COMPACT/COMPACT_v01.blend) | [COMPACT_v01.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/COMPACT/COMPACT_v01.fbx) | [COMPACT_collisions_v01.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/COMPACT/COMPACT_collisions_v01.fbx) | [COMPACT_collisions_v01.json](C:/Dev/Game/ArtSource/Vehicles_W86/COMPACT/COMPACT_collisions_v01.json) |
| DISPLAY_COUPE | 3066 / 1532 / 704 | [DISPLAY_COUPE_v01.blend](C:/Dev/Game/ArtSource/Vehicles_W86/DISPLAY_COUPE/DISPLAY_COUPE_v01.blend) | [DISPLAY_COUPE_v01.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/DISPLAY_COUPE/DISPLAY_COUPE_v01.fbx) | [DISPLAY_COUPE_collisions_v01.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/DISPLAY_COUPE/DISPLAY_COUPE_collisions_v01.fbx) | [DISPLAY_COUPE_collisions_v01.json](C:/Dev/Game/ArtSource/Vehicles_W86/DISPLAY_COUPE/DISPLAY_COUPE_collisions_v01.json) |
| DISPLAY_GT | 3148 / 1574 / 724 | [DISPLAY_GT_v01.blend](C:/Dev/Game/ArtSource/Vehicles_W86/DISPLAY_GT/DISPLAY_GT_v01.blend) | [DISPLAY_GT_v01.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/DISPLAY_GT/DISPLAY_GT_v01.fbx) | [DISPLAY_GT_collisions_v01.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/DISPLAY_GT/DISPLAY_GT_collisions_v01.fbx) | [DISPLAY_GT_collisions_v01.json](C:/Dev/Game/ArtSource/Vehicles_W86/DISPLAY_GT/DISPLAY_GT_collisions_v01.json) |
| DUMP_TRUCK | 3564 / 1782 / 814 | [DUMP_TRUCK_v07.blend](C:/Dev/Game/ArtSource/Vehicles_W86/FLATBED/DUMP_TRUCK_v07.blend) | [DUMP_TRUCK_v07.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/FLATBED/DUMP_TRUCK_v07.fbx) | [DUMP_TRUCK_collisions_v07.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/FLATBED/DUMP_TRUCK_collisions_v07.fbx) | [DUMP_TRUCK_collisions_v07.json](C:/Dev/Game/ArtSource/Vehicles_W86/FLATBED/DUMP_TRUCK_collisions_v07.json) |
| CONTAINER_TRUCK | 6708 / 3354 / 1509 | [CONTAINER_TRUCK_v07.blend](C:/Dev/Game/ArtSource/Vehicles_W86/BOX_TRUCK/CONTAINER_TRUCK_v07.blend) | [CONTAINER_TRUCK_v07.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/BOX_TRUCK/CONTAINER_TRUCK_v07.fbx) | [CONTAINER_TRUCK_collisions_v07.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/BOX_TRUCK/CONTAINER_TRUCK_collisions_v07.fbx) | [CONTAINER_TRUCK_collisions_v07.json](C:/Dev/Game/ArtSource/Vehicles_W86/BOX_TRUCK/CONTAINER_TRUCK_collisions_v07.json) |
| ASTRA_STATIC_VAN | 2554 / 1276 / 565 | [ASTRA_STATIC_VAN_v06.blend](C:/Dev/Game/ArtSource/Vehicles_W86/ASTRA_STATIC_VAN/ASTRA_STATIC_VAN_v06.blend) | [ASTRA_STATIC_VAN_v06.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/ASTRA_STATIC_VAN/ASTRA_STATIC_VAN_v06.fbx) | [ASTRA_STATIC_VAN_collisions_v06.fbx](C:/Dev/Game/ArtSource/Vehicles_W86/ASTRA_STATIC_VAN/ASTRA_STATIC_VAN_collisions_v06.fbx) | [ASTRA_STATIC_VAN_collisions_v06.json](C:/Dev/Game/ArtSource/Vehicles_W86/ASTRA_STATIC_VAN/ASTRA_STATIC_VAN_collisions_v06.json) |

## Material and geometry conventions

One shared material MAT_W86_VehiclePalette_v01; shared/W86_VehiclePalette_v01.png is sRGB BaseMap; shared/W86_VehicleSurface_v01.png is linear packed R=metallic, G=roughness, A=smoothness. Both are 128×64. Use Point, Clamp and mipmaps off for this face-centred palette. Bind both maps explicitly in the existing URP Lit workflow at Step 2: FBX does not reproduce the Blender node graph automatically. Glass is opaque dark blue with controlled highlights for static props.

Metres; Blender Z-up, nose -Y; origin at the visual footprint base centre; visual object transforms applied. Export: axis_forward=-Z, axis_up=Y, FBX_SCALE_ALL, apply units, bake_space_transform, no animation. There are three independent LOD meshes per visual FBX; Step 2 must create/configure LODGroup explicitly (suggested initial screen heights 0.35 / 0.12 / 0.035; tune in scene).

Collision FBXs are separate. UCX objects are convex boxes, all checked closed and convex; each JSON contains Blender and proposed Unity-local centres/sizes. UCX names alone do not create Unity colliders. Use the JSON to add BoxColliders, or explicitly instantiate convex MeshColliders and disable UCX rendering. Never render/import collision files as visible vehicles.

Static render surfaces retain a few source contact edges: COMPACT and DISPLAY_COUPE have two four-face contacts each; Astra retains source part-contact edges. These are separate from the validated closed convex collision meshes. Render meshes have no open boundary or degenerate triangles in the selected LOD0s. Strict watertight render-topology approval is not claimed.

The approved Astra body remains 2554 triangles after closing the original glass panes, below the approximate 3k target; it was deliberately reused rather than padded. Other selected LOD0s are approximately 3k–6.7k. Materials and LOD appearance still need Unity verification after approval.

## Review and evidence

[Approval comparison sheet](C:/Dev/Game/Working/Reviews/W86Polish_2026-10-25/vehicles_v01.png) · [Current builder vehicles](C:/Dev/Game/ArtSource/Vehicles_W86/previews/current_vehicles_v01.png) · [Six-side / LOD inspection](C:/Dev/Game/ArtSource/Vehicles_W86/previews/technical_views_v02.png)

[FBX roundtrip check](C:/Dev/Game/ArtSource/Vehicles_W86/roundtrip_validation_v01.json) · [Builder inventory](C:/Dev/Game/ArtSource/Vehicles_W86/CURRENT_VEHICLES.md) · [Sources](C:/Dev/Game/ArtSource/Vehicles_W86/SOURCES.md) · [Notices](C:/Dev/Game/ArtSource/Vehicles_W86/THIRD_PARTY_NOTICES.md)

Verification command (read-only Blender FBX reimport):

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python "C:\Dev\Game\ArtSource\Vehicles_W86\tools\verify_roundtrip_v01.py"

NOT RUN: Unity import, live shader/material binding, culling/LOD transitions, driving or performance tests. These belong to Step 2 after explicit go and unity_lock.ps1 -Id G47.
