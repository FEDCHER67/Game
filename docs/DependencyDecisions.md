# Dependency decisions — Field Clinic catalogue (47 entries)

Reviewed 2026-10-13 for VOLUNTEERS ONLY (Unity 6000.5.11f1, URP 17.5.0, FishNet 4.7.3/Tugboat).
Input: `Tools/FieldClinicBrief/03_REPOSITORIES.json` (47 entries) and brief §4/§5/§12–§14.
Nothing was installed, downloaded or compiled for this review.

**How this was checked.** Every GitHub entry (34) was queried on `https://api.github.com/repos/{owner}/{repo}` on 2026-10-13 for `pushed_at`, `archived` and `license.spdx_id`. Releases were also fetched for the candidates. Non-GitHub entries (Unity docs, asset sites, documentation pages) were judged from the JSON, the brief and what the project already uses; they were **not** re-fetched. "NOASSERTION" means GitHub could not detect a standard licence. Unity packages then usually use the Unity Companion License (UCL), which allows commercial use inside Unity projects.

**The rule applied (Fedya: "if some tools already exist, skip them").** A repo that duplicates a system we already have is REJECTED or REFERENCE_ONLY. Systems we already have:
- FishNet networking;
- the KCC player motor;
- our own WheelCollider van (`VanController`, upgrades, `VehicleEngineAudio` with engine, skid and impact sound);
- an 11-body NPC ragdoll with stun, grab and loading;
- crowd AI and police on NavMesh;
- the procedural map pipeline (`map_plan_v*.py` → `MapLookBuilderV3`) with roads, terrain, grass and fences;
- Blender 5.2 procedural kits with deterministic builders and FBX export;
- the Uber Stylized Water shader (MIT, our v02 derivative);
- Audio Library_v1 (ambience bake and player);
- the phone UI;
- an inventory;
- an operation prototype.

**Classes:** ACCEPTED (in use or approved now, pinned), REFERENCE_ONLY (read it, do not install), SANDBOX (test outside the main project first), DEFERRED (valid, but no task needs it yet), REJECTED (duplicate, stale, wrong style or out of scope), BLOCKED (cannot proceed).

| Class | Count | Entries |
|---|---:|---|
| ACCEPTED | 7 | #1, #3, #4, #5, #9, #34, #38 |
| REFERENCE_ONLY | 8 | #2, #14, #16, #24, #26, #45, #46, #47 |
| SANDBOX | 2 | #25, #30 |
| DEFERRED | 12 | #6, #13, #17, #19, #22, #23, #32, #33, #35, #36, #37, #44 |
| REJECTED | 18 | #7, #8, #10, #11, #12, #15, #18, #20, #21, #27, #28, #29, #31, #39, #40, #41, #42, #43 |
| BLOCKED | 0 | none |

**Where the JSON was wrong or incomplete:**
- #12 RoadCreator and #15 UnityOctree are **archived** on GitHub. The JSON calls them SANDBOX and LATER.
- #24 has **no licence**, so its code cannot be reused.
- #3 is not an "alternative": it is the bridge we already run, at v10.2.0.
- #4's URL now resolves to `ahujasid/mcp-for-blender`.
- #10 was last pushed in 2020 and #11 in 2023.
- #25 TexTools' last release (v1.6.1, 2024-03) predates Blender 5.x.

---

## Agent integration

**#1 unity-agent-plugin**: https://github.com/Unity-Technologies/unity-agent-plugin
- Does: official Unity skills and commands for Claude and Codex. It is a client plugin, not a UPM package.
- Maintenance: pushed 2026-10-09; not archived; licence NOASSERTION (UCL per JSON).
- Compatibility: Unity 6+; no project files change.
- Conflicts: none. It is already installed in Claude as `unity@claude-plugins-official` (the `unity:*` skills).
- **ACCEPTED (existing, client-level)**: it is already in use, and we only use the relevant skills. Installed version `0.1.6-beta`, plugin commit `ba48956ae8bee4ef8a3ef3d75dec03c16aa5cc89`. Beta: re-check before updating. It has not been confirmed that this marketplace entry is built from exactly this repo.

**#2 unity-skills**: https://github.com/Unity-Technologies/skills
- Does: the source catalogue of the same official skills.
- Maintenance: pushed 2026-10-09; not archived; NOASSERTION.
- **REFERENCE_ONLY**: it duplicates #1, which is already installed. Read it only when a skill is missing.

**#3 unity-mcp (MCP for Unity)**: https://github.com/CoplayDev/unity-mcp
- Does: the MCP bridge between agents and the Unity Editor (scenes, scripts, tests, console).
- Maintenance: pushed 2026-10-08; not archived; MIT; default branch is `beta`.
- Compatibility: works today in our 6000.5.11f1 project (editor-only package).
- Conflicts: do not run a second Unity bridge.
- **ACCEPTED (existing)**: it is our only editor bridge. Pinned as `…unity-mcp.git?path=/MCPForUnity#v10.2.0`, lock hash `30d22075093d1d35dfb0091c1c7550e9ad948577`, with server `mcpforunityserver==10.2.0` (uvx).

**#4 blender-mcp**: https://github.com/ahujasid/mcp-for-blender (the JSON URL redirects here)
- Does: drives the live Blender 5.2 through Python, plus viewport capture.
- Maintenance: pushed 2026-10-06; MIT.
- Conflicts: none. Its `generate_3d` and asset-import tools can spend credits or download files, so they need Fedya's explicit approval.
- **ACCEPTED (existing)**: in daily use. Installed PyPI `blender-mcp 2.0.0` plus the `blender_mcp.py` add-on in Blender 5.2. **Gap:** `~/.claude.json` launches the unpinned `uvx blender-mcp`. Pin it to `blender-mcp==2.0.0` (recommendation 2).

## Unity base

**#5 input-system**: https://github.com/Unity-Technologies/InputSystem
- Maintenance: pushed 2026-10-12; UCL.
- Compatibility: Unity 6 OK; registry package.
- **ACCEPTED (existing)**: `com.unity.inputsystem 1.20.0` is already in the manifest. Keep the registry version and never import the GitHub project.

**#6 cinemachine**: https://github.com/Unity-Technologies/com.unity.cinemachine
- Does: camera rigs and blends.
- Maintenance: pushed 2026-09-29; licence not detected (UCL).
- Compatibility: Cinemachine 3.x supports Unity 6.
- Conflicts: the KCC first-person camera and the van test camera are our own code.
- **DEFERRED**: no gap yet. Revisit when van entry/exit and third-person driving cameras are designed. If adopted, use only Cinemachine 3 and keep one AudioListener.

**#7 probuilder**: https://github.com/Unity-Technologies/com.unity.probuilder
- Maintenance: pushed 2026-10-09; UCL.
- **REJECTED**: it duplicates the map greybox and LookV3 builders and the Blender kits. Blockouts come from `map_plan_v*.py`.

**#8 splines** (com.unity.splines 2.8 docs; not GitHub)
- Compatibility: Unity 6 OK; UCL.
- **REJECTED**: roads, junctions and sidewalks are already generated from the plan JSON by `MapLookBuilderV3`. A second road authoring path would fork the source of truth.

**#9 ai-navigation** (com.unity.ai.navigation 2.0 docs)
- **ACCEPTED (existing)**: `com.unity.ai.navigation 2.0.14` is in the manifest and used by `GreyboxNpc`, `PoliceOfficer` and `PoliceUnit`. The van is not driven as a NavMeshAgent.

## Map and world

**#10 arcade-car**: https://github.com/SergeyMakeev/ArcadeCarPhysics
- Maintenance: last push 2020-03-10; MIT.
- **REJECTED**: it duplicates our WheelCollider `VanController` and its upgrades, which the owner likes. The code is stale.

**#11 openkcc**: https://github.com/nicholas-maltbie/OpenKCC
- Maintenance: last push 2023-09-15; MIT.
- **REJECTED**: it duplicates the KCC motor we already use. The brief allows one on-foot controller.

**#12 roadcreator**: https://github.com/MarcusElg/roadcreator
- Maintenance: **archived**, last push 2019-10-12; MIT.
- **REJECTED**: archived, pre-URP 17 and a duplicate of our road generation.

**#13 fastnoise (FastNoiseLite)**: https://github.com/Auburn/FastNoiseLite
- Maintenance: pushed 2026-06-21; MIT.
- Compatibility: a single C# file; engine-neutral.
- **DEFERRED**: the map is planned in Python with fixed seeds. Add the single C# file only if runtime noise in Unity becomes necessary.

**#14 addressables-samples**: https://github.com/Unity-Technologies/Addressables-Sample
- Maintenance: pushed 2026-05-06; licence not detected.
- **REFERENCE_ONLY**: the world is one generated scene today. Read it when streaming is designed; additive scenes come first (brief §14), with one loader only.

**#15 unity-octree**: https://github.com/Nition/UnityOctree
- Maintenance: **archived**, last push 2021-06-07; BSD-2-Clause.
- **REJECTED**: archived, and FPS is explicitly not a priority now. Physics overlap queries plus district data are enough until profiling proves otherwise.

## Patients and operations

**#16 unity-hfsm**: https://github.com/Inspiaaa/UnityHFSM
- Maintenance: pushed 2026-03-25; MIT; well tested.
- **REFERENCE_ONLY**: NPC flee/stun/ragdoll, crowd and police already run on our own state code. Migrating would rewrite working, tested systems. Borrow ideas only if the NPC states grow unmanageable.

**#17 serialize-reference (SerializeReferenceExtensions)**: https://github.com/mackysoft/Unity-SerializeReferenceExtensions
- Maintenance: pushed 2026-10-13; MIT; latest release 1.7.0 (2026-01-18).
- Compatibility: editor-only; Unity 2021.3+.
- **DEFERRED**: it fills a real gap once operation steps and conditions are authored in the Inspector. The operation prototype is not there yet. Pin `1.7.0` when adopted (recommendation 6).

**#18 xnode**: https://github.com/Siccity/xNode
- Maintenance: last push 2024-08-26; MIT.
- **REJECTED**: a graph editor framework is overkill for a list of operation steps. Its maintenance is slowing.

**#19 litmotion**: https://github.com/annulusgames/LitMotion
- Maintenance: pushed 2026-09-18; MIT; release v2.0.2 (2026-05-10).
- Dependencies: pulls in Unity Collections/Burst.
- **DEFERRED**: van doors and phone UI already use our own easing. Adopt it only as the single tween engine if UI work grows.

**#20 naughty-attributes**: https://github.com/dbrizov/NaughtyAttributes
- Maintenance: pushed 2026-09-16; MIT.
- **REJECTED**: no gap. Our tools are menu-driven builders and MCP-driven, and Inspector sugar does not justify a dependency.

**#21 ezy-slice**: https://github.com/DavidArayan/ezy-slice
- Maintenance: last push 2023-08-10; MIT.
- **REJECTED**: the canon operation uses prepared organ meshes and drops, not runtime mesh slicing.

**#22 goap**: https://github.com/crashkonijn/GOAP
- Maintenance: pushed 2026-03-06; Apache-2.0.
- **DEFERRED**: crowd AI and police states suffice. Reconsider only if NPC behaviour needs planning.

**#23 yarn-spinner**: https://github.com/YarnSpinnerTool/YarnSpinner-Unity
- Maintenance: pushed 2026-10-13; MIT.
- **DEFERRED**: the buyer messages are JSON drafts on the phone. A dialogue engine is not needed until dispatcher and NPC dialogue are designed.

**#24 inventory-reference**: https://github.com/adammyhre/Unity-Inventory-System
- Maintenance: last push 2024-06-27; **no licence**.
- **REFERENCE_ONLY**: we already have an inventory. With no licence, its code must not be copied; read it for ideas only.

## Models and materials

**#25 textools**: https://github.com/franMarz/TexTools-Blender
- Maintenance: pushed 2024-12-02; last release v1.6.1 (2024-03); NOASSERTION (a GPL-family add-on, which does not affect the exported assets).
- Compatibility: Blender 5.2 is **unverified**.
- **SANDBOX**: it fills a real gap. The v3 tiled textures need consistent texel density, and the BUILDING_DETAILS README says palette UVs must be replaced by world-scale UVs. Test it in a throwaway Blender profile first. Fallback: our own texel-density script.

**#26 material-maker**: https://github.com/RodZill4/material-maker
- Maintenance: pushed 2026-10-07; MIT.
- **REFERENCE_ONLY**: we already have ProcTexture CC0 bases, the G13 Python grade and recolour tools, and our own painting. A second procedural authoring app would duplicate them. Its node recipes are a useful reference for painting the flat bitumen roof and the logs.

**#27 mesh-simplifier**: https://github.com/Whinarn/UnityMeshSimplifier
- Maintenance: pushed 2026-01-07; MIT; v3.1.1.
- **REJECTED**: LODs are built in Blender (for example the Sausage Buddy crowd LOD). Unity 6 also has built-in Mesh LOD import (6000.2+; check in 6000.5 before LOD work). FPS is not a priority now.

**#28 gltf-transform**: https://github.com/donmccurdy/glTF-Transform
- Maintenance: pushed 2026-10-06; MIT.
- **REJECTED**: our pipeline is FBX only, so a glTF toolchain has no use.

**#29 nilo-example**: https://github.com/ColinLeung-NiloCat/UnityURPToonLitShaderExample
- Maintenance: pushed 2026-07-02; MIT; targets 2022.3.
- **REJECTED**: the art direction is URP Lit with no banded toon shading and no outlines (STYLE_OAR_NOTES §4).

## Sound

**#30 engine-sound (enginesound)**: https://github.com/DasEtwas/enginesound
- Maintenance: last push 2023-06-06; release v1.6 (2021-09); MIT.
- Compatibility: an external generator of WAV files; no Unity code.
- **SANDBOX**: `VehicleEngineAudio` exists, but its loops come from a sample pack. This tool can produce matched idle/low/mid/high RPM loops for the van and police car. Run the release binary outside the project after approval, and A/B the result against the current loops.

**#31 jsam**: https://github.com/jackyyang09/Simple-Unity-Audio-Manager
- Maintenance: pushed 2026-01-27; MIT.
- **REJECTED**: it duplicates our audio stack (`VehicleEngineAudio`, the SfxLibrary, AmbienceData/Baker/Player). The brief allows one audio manager.

**#32 steam-audio**: https://github.com/ValveSoftware/steam-audio
- Maintenance: pushed 2026-03-25; Apache-2.0.
- **DEFERRED**: only after the base mix is accepted, and then for one measured scenario.

**#33 audacity**: https://github.com/audacity/audacity
- Maintenance: pushed 2026-10-13; NOASSERTION (GPL); a desktop app.
- **DEFERRED**: optional manual tool for a human. Agent audio processing is scripted and recorded in the Library_v1 manifest. Install only if Fedya wants hand editing.

## Diagnostics

**#34 asset-usage (Asset Usage Detector)**: https://github.com/yasirkula/UnityAssetUsageDetector
- Maintenance: pushed 2026-09-12; MIT; release v2.6.3 (2026-09-12).
- Compatibility: editor-only; `package.json` at the repo root; no runtime code.
- **ACCEPTED (not yet installed)**: it fills a real gap. The project accumulates many numbered revisions and generated assets, and cleanup must prove "unused" before deleting. Pin: `"com.yasirkula.assetusagedetector": "https://github.com/yasirkula/UnityAssetUsageDetector.git#v2.6.3"`, commit `b0bf247aa47d9fe8babbddeea6ba2f6949c63455`. Its results never authorise deletion by themselves: also check Resources, string paths and generated builders.

**#35 graphy**: https://github.com/Tayx94/graphy
- Maintenance: pushed 2026-08-29; MIT.
- **DEFERRED**: FPS is not a priority now, and the F11 overlay plus the Unity Profiler cover the need. Use it in development builds only, for the later 60 FPS pass.

**#36 renderdoc**: https://github.com/baldurk/renderdoc
- Maintenance: pushed 2026-10-12; MIT; external app.
- **DEFERRED**: install only when a rendering bug needs a frame capture. Unity can load it from the Game view.

**#37 memory-profiler** (com.unity.memoryprofiler 1.1 docs)
- Licence: UCL.
- **DEFERRED**: becomes relevant with district streaming. Use registry version 1.1.x, matched to the editor.

**#38 test-framework** (com.unity.test-framework docs)
- **ACCEPTED (existing)**: `com.unity.test-framework 1.7.0` is in the manifest, and the EditMode suites already run (ragdoll and loading tests).

## Source assets

**#39 quaternius-characters** (quaternius.com; CC0 free tier)
- **REJECTED**: it duplicates our own NPC line (Sausage Buddy BASE plus 25 pool types, NPC_BASE_01).

**#40 quaternius-animation** (CC0 free tier)
- **REJECTED**: we already use Mixamo clips plus our own Blender animators on the 65-bone Mixamo rig. A different rig adds retargeting work for no gain.

**#41 quaternius-city** (CC0 free tier)
- **REJECTED**: the style does not match. We have our own STYLE_KIT_v3 BUILDING_DETAILS (post-Soviet) and BUILDING_DETAILS_US (American Downtown). A Quaternius/Kenney mix already in `ArtSource/Environments/ForestClearing_v01` stays a past experiment.

**#42 kenney-cars** (CC0)
- **REJECTED**: the van and our own VEHICLES_KIT already exist.

**#43 kenney-industrial** (CC0)
- **REJECTED**: our own builders and kits cover the industrial zone. Kenney *audio* (CC0) is already used in Library_v1.

**#44 sonniss (GDC bundle)** (sonniss.com; royalty-free, commercial use, no attribution, no resale)
- **DEFERRED**: it fills the tyre, skid, impact and ambience gaps, but the archives are multi-GB. Download a selective pick only with Fedya's approval, and record every file in Library_v1 `LICENSES.md` (recommendation 4).

## Documentation

**#45 unity-releases** (unity.com/releases/unity-6)
- **REFERENCE_ONLY**: the project stays on 6000.5.11f1. No editor change and no automatic upgrade.

**#46 claude-skills-docs** (code.claude.com/docs/en/skills)
- **REFERENCE_ONLY**: the format reference for `.claude/skills/fc-*`, which is already in place.

**#47 codex-skills-docs** (developers.openai.com/codex/skills)
- **REFERENCE_ONLY**: the format reference for `.agents/skills/fc-*`, which is already in place.

---

## Recommended next integrations

Ordered by value over risk. Each needs the lead's or Fedya's approval and one change at a time (brief §4: add, wait for compile, check the Console and run a test). No Unity calls while Fedya is playtesting.

1. **Asset Usage Detector v2.6.3** (#34)
   - Why: safe cleanup of the many numbered revisions, generated meshes and textures (the project cleanup rule), with proof of non-use.
   - Risk: low; editor-only, MIT, active.
   - Rollback: remove the one manifest line; it leaves no runtime trace.
2. **Pin blender-mcp to 2.0.0** (#4)
   - Why: the current `uvx blender-mcp` floats to any new PyPI release, which is not reproducible.
   - Risk: none.
   - Rollback: restore the `args` entry. This is a user-config change (`~/.claude.json`), so Fedya or the lead applies it.
3. **enginesound loop sandbox** (#30)
   - Why: van and police engine loops matched by RPM for the existing `VehicleEngineAudio` crossfade.
   - Risk: a 2021 binary; download and run only with approval, outside `Assets`.
   - Rollback: delete the generated WAVs; the current loops stay.
4. **Selective Sonniss pick** (#44)
   - Why: tyre, skid, impact, door and ambience sources beyond the CC0 packs.
   - Risk: download size and per-file licence bookkeeping.
   - Rollback: drop the files; Library_v1 stays as is.
5. **TexTools sandbox in Blender 5.2** (#25)
   - Why: consistent texel density and world-scale UVs for v3 textured kits.
   - Risk: add-on incompatibility with 5.x.
   - Rollback: uninstall the add-on, or write our own texel-density script instead.
6. **SerializeReferenceExtensions 1.7.0** (#17), when operation-step authoring starts
   - Why: polymorphic step and condition lists in the Inspector without custom drawers.
   - Risk: low; editor-only.
   - Rollback: remove the package, after which `[SerializeReference]` fields still serialise.
