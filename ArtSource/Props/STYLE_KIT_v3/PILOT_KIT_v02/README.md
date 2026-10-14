# G18 PILOT_KIT_v02 — lived-in gardens and sparse district life

Checkpoint P addition, 2026-10-14. Original low-poly meshes, metres, Blender X right / Y back / Z up, front -Y. Eight ordered BUILDING_DETAILS material roles, palette UVs, flat faces, zero export transforms. Read-only use of the v01 geometry, validation and FBX export helpers; no v01 deliverables are overwritten.

Anatomy before production: laundry has two grounded timber posts, supported lines and clothes pinned to those lines; doghouse has side/back walls, a real open front and two roof slopes; hen run has posts, rails, an open gate and a raised coop; bicycle has two open faceted tyres, frame triangles, fork, saddle and bars; garden objects are positioned by their support surfaces. The garden is an apple grower's yard, with laundry drying beside a tended flower bed and a work corner. These are clusters, not scatter.

Declared budgets: laundry 1,000 triangles; flowers 1,500; doghouse 500; coop/run 1,500; axe/logs 1,200; bucket/can 1,000; bicycle 2,000; swing 500; basket 1,000; curtains 300; crooked fence 500; picnic table 600; sparse tree 1,200; crow 300; butterfly 150. Tiny wildlife and flowers are decorative; large solid members use compound box collision proxies. No invisible volume across doghouse or run openings. Static kit pieces do not contain rigs or animation. Runtime birds and insects use cheap procedural motion in the v19 preview only.

Validation outputs and Blender previews accompany the master and numbered FBX files. Final human art acceptance remains pending at checkpoint P. These modules are a first garden/detail kit, not placement across every plot in the final map.

Current manifest: fourteen garden/wildlife FBXs use `_v02`; `LEAFLESS_TREE_v03.fbx` replaces only the tree. The v03 trunk reaches every branch root (3.4 m). Its separate master `SK3-PILOT-001_v03.blend`, validation and FBX re-import audit are the authoritative tree repair. The fifteen-module v02 master remains as the original working revision. Total current geometry: 4,596 triangles. No older outputs were overwritten.

Unity uses metre-baked `LEAFLESS_TERRAIN_v03.prefab` for the terrain tree prototype; the ordinary kit wrapper has a child MeshRenderer and is unsuitable for Unity Terrain instancing. The terrain variant preserves all eleven fitted box proxies. Correctly framed six-sided tree previews and a three-quarter view are under `Previews/v03/contact_review_02/`.
