# LUNGS-ASTRA-001 provenance

## Supplied files

- Main geometry source: `Working/Tripo/lungs_tripo_base.fbx` — SHA-256 `3DCE8869801A6EC175CA8D0E0FAA361457A571E1F09F69FC268BE6295938A126`.
- Motion reference: `Working/DonorAnimation/lungs_motion_donor.zip` — SHA-256 `4B273F5C6D72BEDDFB2E7C9C2C3253267FCD7CF75A51B165033B7B82DEB476B4`.
- The donor ZIP contains `source/lungs-blendshape-1.zip`, which contains `source/lungs_blendShape (1).fbx`. Neither archive contains a license or attribution file.

The final asset continues to use the supplied Tripo-derived lung geometry. This second pass edited the existing `LUNGS-ASTRA-001.blend`; it did not restart from or replace the base model. The 1024 × 1024 rear-branch colour mask in `Textures/Rear_Vessel_Paint.png` was created for this project from the existing lung relief. No third-party image was used for that mask.

The donor FBX was inspected **only as a motion and timing reference**. Its 30 fps timebase and GOOD/BAD breathing periods informed new keyframes on the project's own three-bone lungs rig. No donor mesh, armature, shape key, texture, or animation curve was copied into the blend or FBX. The donor's missing external normal map is not a dependency of the deliverable.

Distribution rights for the supplied Tripo-derived geometry and donor source have **not** been independently confirmed. Do not infer a license from the archive names. Confirm the project's permission to ship the source-derived lung geometry before production release; preserve this provenance note with the asset. The donor is not included in the exported game asset.
