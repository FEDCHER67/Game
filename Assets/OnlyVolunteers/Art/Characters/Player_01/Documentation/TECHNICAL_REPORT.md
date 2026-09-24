# PLAYER-CHAR-003 technical report

Status: **human visual approval required**. Player_01 is an isolated prototype. It has not been integrated with Unity gameplay, tuned as a ragdoll, given final materials, or animated.

## Visual adaptation

- Retained the original single mesh, all four source materials and colors, flat faceting, plain featureless face, head, thin limbs, mitten hands, shoes, clothing, and overall proportions.
- Baked the source FBX transform and scaled the mesh to 1.8 m, with the origin at the feet and a clean upright Blender transform.
- Expanded and gently rounded only 32 shirt torso vertices for slightly more internal volume. Maximum vertex displacement: **1.55 cm**. Mesh topology, head, hands, legs, and footwear were not remodeled. Hands and shoes were already readable and were not enlarged.

## Rig and mesh

- One mesh object, one armature object; **675 vertices, 1,332 triangles, 4 materials**. Source topology is retained, including seven harmless loose source vertices.
- Rest bounds: **1.86585 m wide** across the extended arms, **0.40856 m deep**, **1.8 m tall**. The character faces **-Y** in Blender; FBX export uses `-Z` forward and `Y` up for Unity import.
- **20 bones**, of which 19 deform: nondeforming `Root` → `Hips` → `Spine` → `Chest` → `Neck` → `Head`; paired `Shoulder` → `UpperArm` → `LowerArm` → `Hand`; paired `UpperLeg` → `LowerLeg` → `Foot` branches from `Hips`.
- Automatic Blender bone heat weights passed coverage and side checks. All 675 vertices have normalized weights summing to 1.0, with at most six influences. An explicit bounded region fallback remains in the repeatable build script.
- Humanoid hierarchy and labels are prepared for Unity Avatar mapping. **Unity Humanoid import/Avatar validity has not yet been checked**; this awaits the visual gate and a later focused import check.

## Validation

- Blender 5.2.1 opened the saved `.blend`; the armature modifier references the armature and all 1,332 faces remain flat shaded.
- FBX export succeeded. A clean Blender FBX reimport retained one mesh, the armature hierarchy, 675 vertices, 1,332 triangles, 19 weight groups, and approximately 1.8 m height. FBX bone tails were lengthened by FBX length semantics, with hierarchy preserved.
- Eight 1024×1024 neutral or diagnostic PNGs were rendered: front, side, three quarter, back, wireframe, rig, bent arm/leg, crouch. The posed views were inspected for obvious separation or collapse.
- `pose_validation.json` confirms finite vertices and no extent explosion in the bent arm/leg and crouch views. `technical_pose_validation.json` additionally checks neutral, arms raised, elbows bent, knees bent, and extreme limb rotations. All checks passed and rest pose was restored. These numerical checks cannot prove every future animation or collision configuration.
- `build_player_01.py`, `render_player_01_previews.py`, and `validate_player_01.py` provide repeatable construction, preview rendering, and pose validation. No Unity gameplay integration was performed.

## Human review

Review the eight PNGs in `Player_01/Preview/`, especially face/silhouette, rounded torso, wireframe, rig placement, elbow and knee bending, and crouch. Human visual approval is required before any gameplay integration or ragdoll tuning.
