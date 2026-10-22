# Types_opt_v02 in Unity: status (TASK-000900, stopped 22.10 17:46 on Fedya's order)

Nothing committed or pushed. WORK_SYNC.md not touched.

## Done in Unity
- Importer `NpcTypesImportV01`: OptDir/OptTag = Types_opt_v02 / opt_v02. New `Repoint` (used by ApplyOptimized and UpdatePrefab): the prefab keeps LOD0 under the plain names (Body/Face/Outfit/Props_*) and gets the FBX `X_LOD0` mesh. It adds sibling `X_LOD1`/`X_LOD2` SkinnedMeshRenderers on the same bones, with X's layer and render settings, plus a LODGroup on the root. The LODGroup has fade off, a fixed size of 1.8 m world and switches at 15 m / 40 m with a cull at 150 m. Its screen heights 0.156 / 0.059 / 0.016 assume the runtime camera FOV of 75 and the PC lodBias of 2. BuildPrefab renames `X_LOD0` to `X`. Triangle counts, prop detection and the feet check use LOD0 only.
- Menu "NPC Types v01: Use Optimized Meshes + crowd LODs (opt_v02)" was run on all **48 types: 48 OK, 0 failed**, each with a 3-level LODGroup. The 10 late types were re-imported after DONE_ALL_48.txt appeared. All 48 copies in Models match ArtSource byte for byte. Presets updated: SourceFbx and Triangles (LOD0).
- Name-lookup fixes:
  - `GreyboxFace` drives all Face levels, matching shape keys by name. Face_LOD1/2 keep 6 shape keys.
  - `CaptureTableBridge.SpawnTrash` uses LOD0 only.
  - `NpcHeldProps` drops LOD0 and hides the LOD1/2 renderers.
  - `CaptureUndress`: Body_LOD1/2 get the undressed body, and Shorts are added to every level.
- Compiles clean, no console errors, not in play mode.
- Baseline FPS before the change: 205 at the Downtown square (F6 spot, play mode). No "after" number was measured.
- NOTE: the play scene rebuild (`W85PlayIntegrator.MakeV02`) had already finished (17:45, before the stop arrived). It saved `Map_W85_Play_v02.unity` with 38 type templates added. The editor still marks the open scene dirty after the save; it was **not** saved again.

## Changed files (uncommitted)
- `Assets/OnlyVolunteers/Characters/SausageBuddy/Types_v01/Editor/NpcTypesImportV01.cs`
- `Assets/OnlyVolunteers/Map/Scripts/GreyboxFace.cs`, `Assets/OnlyVolunteers/Characters/Scripts/NpcHeldProps.cs`, `Assets/OnlyVolunteers/Capture/Scripts/CaptureTableBridge.cs`, `Assets/OnlyVolunteers/Capture/Scripts/CaptureUndress.cs`
- 48 prefabs `Types_v01/Prefabs/SausageBuddy_*.prefab`, 48 presets `Types_v01/Data/Presets/*.asset`
- 48 new `Types_v01/Models/SAUSAGE_BUDDY_*_opt_v02.fbx` + .meta (the old opt_v01 copies stay)
- `Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity` (rebuilt)
- `ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v02/` (untracked, from the art agent)

## Remaining
- Sanity in play mode: the crowd spawns with LODGroups (count them), the Downtown FPS after the change (baseline 205, F6 spot), console clean.
- Decide whether to save the dirty scene state, or re-run the rebuild cleanly.
- Commit + push the paths above (explicit paths; skip the large render sheets) and WORK_SYNC TASK-000900. Per the worker rules, this is for the lead or Fedya.
