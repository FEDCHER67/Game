using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using FishNet.Object;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Buyers.Runtime;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Characters.Types;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Look.V3;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // G43 "integrate only" as a re-runnable step after every map rebuild: the built map scene is saved as a play scene and
    // the finished capture -> operations setup of the playtested i10 scene is carried over unchanged (i10 is opened
    // additively, its objects are moved over and i10 is closed unsaved; neither the map scene nor i10 is ever saved):
    // FishNet solo host, CaptureDirector (+ its serialized table / tuning / body-bag / save refs), the KCC pawn with
    // NetworkPlayer, NetworkGrabber and inventory, the van, the van camera rig, grandpa's operating shed + paint station
    // (base 2), van paint mode, fly toggle, the crowd (pool, templates) and the ambience player that wires WaterQuery.
    // Placement: the i10 base group is moved rigidly from the face of the i10 hut that looks at the van onto the face of
    // the new hut that looks at its van pad (rotation = angle between the two faces), pushed off the pad/apron if it would
    // stand on them, each group snapped to the ground (its lowest-standing part never below the ground); van on the pad,
    // pawn beside it as in i10. Re-wired: crowd data (the Hamlet streets of the map data as crowd loops, i10 Hamlet density)
    // + map height sampler + G44 NPC type templates, WaterQuery -> the map's WaterData (through the ambience scene data, as
    // i10 does), fog van headlights, FishNet scene ids regenerated for the new scene path. Generated files go into a folder
    // named like the play scene, next to it. Everything is logged; "missing:" lines name what could not be connected.
    public static class W85PlayIntegrator
    {
        public const string SourceScene = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i10_capture_delivery.unity";
        const string MapScene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Build_v01.unity";
        const string PlayScene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v01.unity";
        public static string MapSceneOf(string ver) => $"Assets/OnlyVolunteers/Scenes/Map/Map_W85_Build_{ver}.unity";
        public static string PlaySceneOf(string ver) => $"Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_{ver}.unity";
        const string HutName = "B_02-A-BASE", HutDistrict = "District_hamlet", I10Hut = "MapLook_v19_StyleV3/Buildings/B_02_B02";
        const string Shed = "[Capture] Base B02 — operating shed", PaintStation = "G20 Grandpa's paint station — B02 hut";
        const string CrowdDistrict = "hamlet";
        const string Ambience = "Ambience_v19_full_v01";
        static readonly string[] Carry =
        {
            "[Capture] Network (solo host)", "[Capture] Stage A director", "Player_KCC", "Van", "Main Camera", Shed, PaintStation,
            "G20 Map paint controls", "G20 Map painting HUD", "Crowd", "V3_FlyToggle", Ambience,
        };
        static readonly string[] BaseGroups = { Shed, PaintStation };
        static readonly StringBuilder Log = new();

        [MenuItem("OnlyVolunteers/Map/W85 Build/Make Play scene (capture + ops)")]
        static void MakeMenu()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Debug.Log(Make(MapScene, PlayScene, "W85"));
        }

        // W86: the play scene of the data v02 map (Map_W85_Build_v02 -> Map_W85_Play_v02); same steps, own side files, own saves.
        [MenuItem("OnlyVolunteers/Map/W86 Make Play scene (v02)")]
        static void MakeMenuV02()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Debug.Log(Make(MapSceneOf("v02"), PlaySceneOf("v02"), "W85", "v02"));
        }

        public static string MakeV02() => Make(MapSceneOf("v02"), PlaySceneOf("v02"), "W85", "v02");

        sealed class Group
        {
            public string Name;
            public Transform Root;
            public Vector3 I10Pos;
            public Quaternion I10Rot;
            public readonly List<Vector2> Pts = new();   // ground sample points (i10 plan)
            public readonly List<float> Src = new();     // i10 ground under them
            public Bounds Local;                          // colliders in the root's frame (overlap test)
        }

        public static string Make(string mapScenePath, string playScenePath, string mapTag) => Make(mapScenePath, playScenePath, mapTag, "v01");

        // ver = the map data / generated version (v01 W85, v02 W86): map data, WaterData and the side files of the play scene follow it.
        public static string Make(string mapScenePath, string playScenePath, string mapTag, string ver)
        {
            Log.Clear();
            Note($"[W85Play] {mapScenePath} -> {playScenePath} ({mapTag}, data {ver})");
            if (EditorApplication.isPlaying) return Fail("leave Play mode first");
            if (!File.Exists(mapScenePath)) return Fail("no map scene " + mapScenePath);
            if (!File.Exists(SourceScene)) return Fail("no source scene " + SourceScene);
            if (playScenePath == mapScenePath || playScenePath == SourceScene) return Fail("the play scene must be a new path");
            string sideDir = playScenePath.Substring(0, playScenePath.Length - ".unity".Length);
            Folder(Path.GetDirectoryName(playScenePath).Replace('\\', '/'));
            Folder(sideDir);

            // 1. The map scene becomes the play scene (save as: the map file itself is never written).
            var scene = EditorSceneManager.OpenScene(mapScenePath, OpenSceneMode.Single);
            if (!EditorSceneManager.SaveScene(scene, playScenePath)) return Fail("could not save " + playScenePath);
            var mapRoots = scene.GetRootGameObjects();
            Transform hut = FindHut(mapRoots);
            // the map terrain = the one with a collider (W86: the steppe backdrop is a second, collider-less terrain)
            Terrain terrain = mapRoots.SelectMany(g => g.GetComponentsInChildren<Terrain>(true)).OrderBy(t => t.GetComponent<TerrainCollider>() ? 0 : 1).FirstOrDefault();
            MapHeightSampler sampler = mapRoots.SelectMany(g => g.GetComponentsInChildren<MapHeightSampler>(true)).FirstOrDefault();
            if (sampler == null && terrain != null) { sampler = terrain.gameObject.AddComponent<MapHeightSampler>(); sampler.Terrain = terrain; Note("map had no MapHeightSampler: added one on " + terrain.name); }
            var mapCameras = mapRoots.SelectMany(g => g.GetComponentsInChildren<Camera>(true)).Where(c => c.CompareTag("MainCamera")).ToList();
            string dataDir = DataDir(mapTag, ver, out string districtFile);
            var district = districtFile != null ? MiniJson.Parse(File.ReadAllText(districtFile)) as Dictionary<string, object> : null;
            Note(districtFile != null ? "map data: " + districtFile : "missing: Hamlet district JSON under Map/" + mapTag + "Build/Data (crowd loops and van pad need it)");
            Vector2[] pad = ZonePoly(district, "BASE-PAD"), apron = ZonePoly(district, "BASE-TURN");
            Vector2? door = HutDoor(district, hut != null ? hut.name : HutName);
            if (hut == null) Note($"missing: map hut {HutName} under {HutDistrict}; base 2 stays at the i10 coordinates");
            if (terrain == null) Note("missing: map terrain (ground snapping uses colliders only)");

            // 2. i10 additively: read, move the finished objects over, close unsaved.
            var src = EditorSceneManager.OpenScene(SourceScene, OpenSceneMode.Additive);
            SceneManager.SetActiveScene(scene);
            var carried = new Dictionary<string, GameObject>();
            var carriedRoots = new HashSet<Transform>();
            var groups = new List<Group>();
            Vector3 vanI10 = Vector3.zero, pawnI10 = Vector3.zero; float vanYawI10 = 0f, vanGroundI10 = 0f, pawnGroundI10 = 0f;
            Quaternion turn = Quaternion.identity; Vector3 originI10 = Vector3.zero, originNew = Vector3.zero, normalNew = Vector3.forward;
            bool frame = false;
            Light[] headlights = Array.Empty<Light>(); DistrictFog19V05.Halo[] headHalos = Array.Empty<DistrictFog19V05.Halo>();
            TextAsset i10Crowd = null;
            try
            {
                var srcRoots = src.GetRootGameObjects();
                foreach (string n in Carry)
                {
                    var g = srcRoots.FirstOrDefault(r => r.name == n);
                    if (g == null) { Note("missing: i10 object " + n); continue; }
                    carried[n] = g; carriedRoots.Add(g.transform);
                }
                var srcSampler = srcRoots.SelectMany(g => g.GetComponentsInChildren<MapHeightSampler>(true)).FirstOrDefault();
                var srcTerrain = srcSampler != null ? srcSampler.Terrain : srcRoots.SelectMany(g => g.GetComponentsInChildren<Terrain>(true)).FirstOrDefault();
                Physics.SyncTransforms();
                float GroundI10(float x, float z) => Ground(src, srcSampler, srcTerrain, carriedRoots, x, z);
                if (carried.TryGetValue("Van", out var van))
                {
                    vanI10 = van.transform.position; vanYawI10 = van.transform.eulerAngles.y; vanGroundI10 = GroundI10(vanI10.x, vanI10.z);
                    var fog = srcRoots.SelectMany(g => g.GetComponentsInChildren<DistrictFog19V05>(true)).FirstOrDefault();
                    if (fog != null)
                    {
                        headlights = fog.vanHeadlights.Where(l => l != null && l.transform.IsChildOf(van.transform)).ToArray();
                        headHalos = fog.halos.Where(h => h.light != null && h.light.transform.IsChildOf(van.transform)).ToArray();
                    }
                }
                if (carried.TryGetValue("Player_KCC", out var pawnGo)) { pawnI10 = pawnGo.transform.position; pawnGroundI10 = GroundI10(pawnI10.x, pawnI10.z); }
                if (carried.TryGetValue("Crowd", out var crowdGo)) i10Crowd = crowdGo.GetComponent<CrowdDirector>()?.Data;

                // Frame: centre of the hut face that looks at the van (i10) / at the van pad (map).
                Transform hutI10 = FindPath(srcRoots, I10Hut);
                if (hutI10 != null && hut != null && HutBox(hutI10, out Vector3 cI10, out Quaternion rI10, out Vector3 hI10) && HutBox(hut, out Vector3 cNew, out Quaternion rNew, out Vector3 hNew))
                {
                    Face(cI10, rI10, hI10, vanI10 - cI10, out originI10, out Vector3 nI10);
                    Vector3 towards = pad != null ? Centre3(pad) - cNew : rNew * (Quaternion.Inverse(rI10) * (vanI10 - cI10));
                    Face(cNew, rNew, hNew, towards, out originNew, out normalNew);
                    turn = Quaternion.Euler(0f, Vector3.SignedAngle(nI10, normalNew, Vector3.up), 0f);
                    frame = true;
                    Note($"base frame: i10 hut face {F(originI10)} n{F(nI10)} -> {hut.name} face {F(originNew)} n{F(normalNew)}, turn {turn.eulerAngles.y:0.#} deg");
                }
                else if (hut != null) Note("missing: i10 hut " + I10Hut + " or a box collider on " + hut.name + "; base 2 stays at the i10 coordinates");

                foreach (string n in BaseGroups)
                {
                    if (!carried.TryGetValue(n, out var g)) continue;
                    var grp = new Group { Name = n, Root = g.transform, I10Pos = g.transform.position, I10Rot = g.transform.rotation };
                    var cols = g.GetComponentsInChildren<Collider>(true).Where(c => !c.isTrigger).ToArray();
                    Bounds low = default, all = default; bool hasLow = false, hasAll = false;
                    foreach (var c in cols)
                    {
                        var b = c.bounds;
                        if (hasAll) all.Encapsulate(b); else { all = b; hasAll = true; }
                        if (b.min.y > GroundI10(b.center.x, b.center.z) + .5f) continue;
                        if (hasLow) low.Encapsulate(b); else { low = b; hasLow = true; }
                    }
                    if (!hasLow) { Note("missing: colliders on " + n + " (not snapped)"); continue; }
                    for (int ix = 0; ix < 3; ix++)
                        for (int iz = 0; iz < 3; iz++)
                        {
                            float x = Mathf.Lerp(low.min.x + .1f, low.max.x - .1f, ix * .5f), z = Mathf.Lerp(low.min.z + .1f, low.max.z - .1f, iz * .5f);
                            grp.Pts.Add(new Vector2(x, z)); grp.Src.Add(GroundI10(x, z));
                        }
                    grp.Local = new Bounds(g.transform.InverseTransformPoint(all.center), all.size); // i10 roots are unrotated, unscaled
                    groups.Add(grp);
                }

                foreach (var g in carried.Values) SceneManager.MoveGameObjectToScene(g, scene);
                Note($"moved from i10: {string.Join(", ", carried.Keys)}");
            }
            finally
            {
                if (src.isLoaded) EditorSceneManager.CloseScene(src, true);
                SceneManager.SetActiveScene(scene);
            }

            // 3. Base 2 at the new hut, snapped to the ground; van on the pad, pawn beside it.
            Physics.SyncTransforms();
            float GroundNew(float x, float z) => Ground(scene, sampler, terrain, carriedRoots, x, z);
            Vector3 ToNew(Vector3 p) { if (!frame) return p; var q = originNew + turn * (new Vector3(p.x, 0f, p.z) - originI10); return new Vector3(q.x, p.y, q.z); }
            foreach (var grp in groups)
            {
                var t = grp.Root;
                t.SetPositionAndRotation(ToNew(t.position), turn * t.rotation);
                var keepOut = new[] { pad, apron }.Where(p => p != null).ToArray();
                if (frame && keepOut.Length > 0)
                {
                    bool Overlaps() => grp.Pts.Any(p => keepOut.Any(k => InsidePoly(k, Plan(MapPt(grp, p)), .25f)));
                    float shift = 0f, maxShift = Mathf.Max(0f, MinFaceGap(grp, originNew, normalNew) - .8f);
                    while (Overlaps() && shift + .1f <= maxShift) { shift += .1f; t.position -= normalNew * .1f; }
                    if (shift > 0f || Overlaps()) Note($"{grp.Name}: pushed {shift:0.0} m toward the hut, off the van pad/apron" + (Overlaps() ? " (WARNING: still overlaps them)" : ""));
                }
                float dyMax = float.MinValue, dyMin = float.MaxValue;
                for (int k = 0; k < grp.Pts.Count; k++)
                {
                    Vector2 p = Plan(MapPt(grp, grp.Pts[k]));
                    float dy = GroundNew(p.x, p.y) - grp.Src[k];
                    dyMax = Mathf.Max(dyMax, dy); dyMin = Mathf.Min(dyMin, dy);
                }
                t.position = new Vector3(t.position.x, grp.I10Pos.y + dyMax, t.position.z);
                var fp = Footprint(grp);
                Note($"{grp.Name}: at {F(t.position)} yaw {t.eulerAngles.y:0.#}; footprint x {fp.xMin:0.0}..{fp.xMax:0.0} z {fp.yMin:0.0}..{fp.yMax:0.0}; ground range {dyMax - dyMin:0.00} m" +
                     (dyMax - dyMin > .12f ? $" -> WARNING: the low side stands {dyMax - dyMin:0.00} m above the ground; the map needs this rect flat" : ""));
                if (door.HasValue) { float d = DistToRect(fp, door.Value); if (d < 1f) Note($"WARNING {grp.Name} is {d:0.0} m from the hut door"); }
            }
            Physics.SyncTransforms();
            if (carried.TryGetValue("Van", out var vanGo))
            {
                Vector3 at = pad != null ? Centre3(pad) : ToNew(vanI10);
                float yaw = vanYawI10 + turn.eulerAngles.y;
                at.y = GroundNew(at.x, at.z) + (vanI10.y - vanGroundI10);
                vanGo.transform.SetPositionAndRotation(at, Quaternion.Euler(0f, yaw, 0f));
                Note($"van: {F(at)} yaw {yaw:0.#}" + (pad != null ? " (centre of the van pad)" : " (i10 offset, no pad in the data)"));
                if (carried.TryGetValue("Player_KCC", out var pawnGo))
                {
                    Vector3 p = at + turn * (new Vector3(pawnI10.x - vanI10.x, 0f, pawnI10.z - vanI10.z));
                    p.y = GroundNew(p.x, p.z) + (pawnI10.y - pawnGroundI10);
                    pawnGo.transform.SetPositionAndRotation(p, turn * pawnGo.transform.rotation);
                    Note($"player spawn: {F(p)} (beside the van as in i10)");
                }
            }
            Physics.SyncTransforms();
            foreach (var grp in groups) ClearInside(scene, grp.Root, grp.Local, carriedRoots, terrain, GroundNew, grp.Name);
            // W86 integration (T1 T23 a / T24 a): grandpa's operating shed + paint table in the T1 materials, cube UVs in metres / 2 m
            foreach (string n in new[] { Shed, PaintStation }) if (carried.TryGetValue(n, out var tg)) Note(T1Retexture(tg, sideDir));
            // W86: F1-F8 teleports (GreyboxTripMeter on the carried van) re-derived from the map data; i10's points were v19 places
            if (vanGo != null) Note(W85Teleports.Apply(vanGo, dataDir, GroundNew, carriedRoots));
            if (vanGo != null)
            {
                var vb = vanGo.GetComponentsInChildren<Collider>(true).Where(c => !c.isTrigger).Select(c => c.bounds).ToArray();
                if (vb.Length > 0)
                {
                    var b = vb[0]; foreach (var x in vb) b.Encapsulate(x);
                    ClearInside(scene, vanGo.transform, new Bounds(vanGo.transform.InverseTransformPoint(b.center), b.size), carriedRoots, terrain, GroundNew, "van");
                }
            }
            var yard = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).FirstOrDefault(t => t.name == "Base2_GrandpaYard");
            Note(yard ? $"grandpa's yard props (GRANDPA_YARD_v01): {yard.childCount} objects from the map build (rocking chair, barrel, paint cans + brush, rain drum + downpipe)"
                      : "missing: Base2_GrandpaYard in the map build (grandpa's rocking chair / barrel / rain drum)");
            // Fedya 21.10: no roof / canopy / porch in the air — the whole play scene (map + carried i10 objects), posts where something floats
            Physics.SyncTransforms();
            Note(W85FloatCheck.Run(scene, true).TrimEnd());

            // 4. One main camera / audio listener: the map's plain camera gives way to i10's (van rig) + the pawn's.
            foreach (var cam in mapCameras)
            {
                if (cam == null) continue;
                bool plain = cam.GetComponents<Component>().All(c => c is Transform || c is Camera || c is AudioListener || c.GetType().Name == "UniversalAdditionalCameraData");
                if (plain) { Note("removed the map's camera " + PathOf(cam.transform)); Object.DestroyImmediate(cam.gameObject); }
                else { cam.enabled = false; var al = cam.GetComponent<AudioListener>(); if (al) al.enabled = false; cam.tag = "Untagged"; Note("disabled the map's camera " + PathOf(cam.transform)); }
            }

            // 5. Crowd: Hamlet loops from the map data, i10 density, map height sampler, G44 type templates.
            if (carried.TryGetValue("Crowd", out var crowd2) && crowd2.TryGetComponent(out CrowdDirector director))
            {
                var tables = AssetDatabase.LoadAssetAtPath<NpcSpawnTables>(NpcTypesImportV01.TablesPath);
                var data = WriteCrowd(sideDir, mapTag, ver, district, dataDir, pad, i10Crowd, tables);
                if (data != null) director.Data = data;
                else Note("missing: Hamlet streets in the map data; the crowd keeps the i10 file (v19 coordinates)");
                director.Sampler = sampler;
                if (tables != null) Note($"NPC types: {NpcTypesImportV01.AddTypeTemplates(director, tables, true)} type templates added, spawn tables {NpcTypesImportV01.TablesPath}");
                else Note("missing: " + NpcTypesImportV01.TablesPath);
                // W86: the tables' idle placements (buried / castle / detector / lounger / pull-up bar) have no spawner yet
                if (tables != null && tables.Placements.Count > 0)
                    Note($"not wired: {tables.Placements.Count} NPC placements in the tables ({string.Join(", ", tables.Placements.Select(p => p.Type != null ? p.Type.TypeId : "?"))}): no placement spawner exists (CrowdDirector reads only the district rows); their types walk via the tables or not at all");
                // FPS (lead, 21.10): distance culling of far walkers (renderers + animator off beyond ~190 m, CullUpdateTransforms closer)
                if (!director.GetComponent<W85CrowdCull>()) director.gameObject.AddComponent<W85CrowdCull>();
                EditorUtility.SetDirty(director);
            }

            // 6. WaterQuery -> the map's WaterData (i10 wires it through the ambience player's scene data, WaterOverride).
            var water = AssetDatabase.LoadAssetAtPath<WaterData>($"Assets/OnlyVolunteers/Map/{mapTag}Build/Generated/{ver}/{mapTag}_WaterData_{ver}.asset");
            if (water == null && AssetDatabase.IsValidFolder($"Assets/OnlyVolunteers/Map/{mapTag}Build/Generated/{ver}"))
            {
                string guid = AssetDatabase.FindAssets("t:WaterData", new[] { $"Assets/OnlyVolunteers/Map/{mapTag}Build/Generated/{ver}" }).FirstOrDefault();
                if (guid != null) water = AssetDatabase.LoadAssetAtPath<WaterData>(AssetDatabase.GUIDToAssetPath(guid));
            }
            if (water != null) Note($"water: {AssetDatabase.GetAssetPath(water)}: " + string.Join(", ", water.Areas.GroupBy(a => a.Kind).Select(g => g.Key + " " + g.Count())) + (water.Areas.Any(a => a.Kind == WaterKind.River || a.Kind == WaterKind.Lake || a.Kind == WaterKind.Canal) ? "" : " (WARNING: no River/Lake/Canal for body disposal)"));
            else Note($"missing: map WaterData (Map/{mapTag}Build/Generated/{ver}/{mapTag}_WaterData_{ver}.asset); body disposal falls back to Resources Water_latest");
            if (carried.TryGetValue(Ambience, out var ambGo) && ambGo.TryGetComponent(out AmbiencePlayer amb))
            {
                var data = amb.SceneData != null ? Object.Instantiate(amb.SceneData) : ScriptableObject.CreateInstance<AmbienceData>();
                data.WaterOverride = water; data.PlanRevision = mapTag;
                // the v19 district beds / spots / coast / fountains are v19 positions: not carried onto this map
                data.Districts = Array.Empty<AmbienceData.District>(); data.BlendBounds = Array.Empty<Vector4>(); data.DistrictBlendMetres = 0f;
                data.Spots = Array.Empty<AmbienceData.Spot>(); data.Coastlines = Array.Empty<AmbienceData.Coastline>();
                data.Fountains = Array.Empty<Vector3>(); data.Offices = Array.Empty<Vector3>();
                string path = $"{sideDir}/Ambience_{mapTag}_play_{ver}.asset";
                AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(data, path);
                amb.SceneData = data; ambGo.name = $"Ambience_{mapTag}_play (WaterQuery = map water)";
                EditorUtility.SetDirty(amb);
                Note($"ambience: {path} (i10 scene data, WaterOverride = map water; v19 district beds not carried)");
            }

            // 7. Re-wire the map look's fog to the carried van headlights (i10 had them; the map build emptied them).
            var fogs = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<DistrictFog19V05>(true)).ToArray();
            foreach (var fog in fogs)
            {
                if (headlights.Length > 0) fog.vanHeadlights = headlights;
                fog.halos = fog.halos.Where(h => h.light == null || !headlights.Contains(h.light)).Concat(headHalos).ToArray();
                EditorUtility.SetDirty(fog);
            }
            if (fogs.Length > 0 && headlights.Length > 0) Note($"fog: {headlights.Length} van headlights + {headHalos.Length} halos re-wired");

            // 8. Saves of this map apart from i10's (release builds; the editor slot is fixed in CaptureDirector).
            if (carried.TryGetValue("[Capture] Stage A director", out var dirGo) && dirGo.TryGetComponent(out CaptureDirector cd))
            {
                cd.SaveFileName = $"capture_stageA_{mapTag}_{ver}.json";                 // per map data: v01 saves never load on v02
                EditorUtility.SetDirty(cd);
                // editor sessions: own slot too (CaptureTestHooks.SaveSlot override, set before CaptureDirector starts) — lead, 21.10
                var slot = dirGo.GetComponent<W85EditorSaveSlot>() ?? dirGo.AddComponent<W85EditorSaveSlot>();
                slot.EditorSlot = ver == "v01" ? $"capture_stageA_editor_{mapTag}.json" : $"capture_stageA_editor_{mapTag}_{ver}.json";
                Note($"capture director: table {Name(cd.TablePrefab)} at {(cd.TableSpawn ? F(cd.TableSpawn.position) : "missing: TableSpawn")}, pawn {Name(cd.PawnNetworkObject)}, tuning {Name(cd.Tuning)}, body bag {Name(cd.BodyBagPrefab)}, LoadOnStart {cd.LoadOnStart}, autosave {cd.AutosaveSeconds} s, save file {cd.SaveFileName}");
            }

            // 9. Missing scripts carried from i10 (G20 painting HUD) would warn every load.
            int removed = 0;
            foreach (var g in carried.Values)
                foreach (var t in g.GetComponentsInChildren<Transform>(true))
                    if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject) > 0)
                        try { removed += GameObjectUtility.RemoveMonoBehavioursWithMissingScript(t.gameObject); }
                        catch (Exception e) { Note("could not remove a missing script on " + PathOf(t) + ": " + e.Message); }
            if (removed > 0) Note($"removed {removed} missing-script component(s) carried from i10");

            // 9b. W86 sale (toggle FirstBuyerCrate): the first buyer's wide wooden crate beside the operating shed (SALES SG-D27).
            Physics.SyncTransforms();
            if (!FirstBuyerCrate) Note("buyer crate: off (W85PlayIntegrator.FirstBuyerCrate = false)");
            else if (carried.TryGetValue(Shed, out var shedGo)) Note(PlaceBuyerCrate(scene, shedGo.transform, pad, apron, GroundNew, sideDir));
            else Note("missing: the operating shed; no buyer crate");

            // 9c. W86: this play scene first in Build Settings (Shift+K "new game" reloads the active scene by its build index).
            if (ver != "v01") Note(BuildSettingsFirst(playScenePath));

            // 10. Save, then FishNet scene ids for this scene path (force: unique, valid), save again.
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Note(SceneIds(scene));
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();

            int listeners = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<AudioListener>(false)).Count(a => a.enabled);
            int mains = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(false)).Count(c => c.enabled && c.CompareTag("MainCamera"));
            Note($"check: enabled MainCamera cameras {mains}, enabled audio listeners {listeners}");
            Note("saved " + playScenePath);
            return Log.ToString();
        }

        static readonly Dictionary<string, string> T1Swap = new()
        {
            ["Capture_Shed_Concrete_v01"] = "T1_T23_floor", ["Capture_Shed_Plank_v01"] = "T1_T23a_planks", ["Capture_Shed_Roof_v01"] = "T1_T23a_roof",
            ["Capture_Shed_Tile_v01"] = "T1_T23_tiles", ["Capture_Shed_Wood_v01"] = "T1_T23_wood", ["G20_OldWood"] = "T1_T24a_table", ["G20_Tin"] = "T1_T24_tin",
        };
        static string T1Retexture(GameObject root, string sideDir)
        {
            int n = 0, meshes = 0;
            var cache = new Dictionary<string, Mesh>();
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mats = r.sharedMaterials; bool hit = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (!mats[i] || !T1Swap.TryGetValue(mats[i].name, out string t1)) continue;
                    var m = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Materials/" + t1 + ".mat");
                    if (m) { mats[i] = m; hit = true; }
                }
                if (!hit) continue;
                r.sharedMaterials = mats; n++;
                var mf = r.GetComponent<MeshFilter>();
                if (mf && mf.sharedMesh && mf.sharedMesh.name == "Cube")
                {   // the primitive stretches 0..1 over each face: metre UVs (2 m tile) for this box size
                    Vector3 sc = r.transform.lossyScale;
                    string key = $"{Mathf.Abs(sc.x):0.00}_{Mathf.Abs(sc.y):0.00}_{Mathf.Abs(sc.z):0.00}";
                    if (!cache.TryGetValue(key, out var mesh))
                    {
                        mesh = Object.Instantiate(mf.sharedMesh); mesh.name = "T1box_" + key;
                        var v = mesh.vertices; var nn = mesh.normals; var uv = new Vector2[v.Length];
                        for (int i = 0; i < v.Length; i++)
                        {
                            Vector3 q = Vector3.Scale(v[i], new Vector3(Mathf.Abs(sc.x), Mathf.Abs(sc.y), Mathf.Abs(sc.z))) / 2f;
                            uv[i] = Mathf.Abs(nn[i].y) > .5f ? new Vector2(q.x, q.z) : Mathf.Abs(nn[i].x) > .5f ? new Vector2(q.z, q.y) : new Vector2(q.x, q.y);
                        }
                        mesh.uv = uv;
                        string path = $"{sideDir}/T1box_{key.Replace('.', 'p')}.asset";
                        AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(mesh, path);
                        cache[key] = mesh; meshes++;
                    }
                    mf.sharedMesh = mesh;
                }
            }
            return $"T1 retexture {root.name}: {n} renderers, {meshes} metre-UV box meshes";
        }

        // ------------------------------------------------------------------ W86 sale: the first buyer's crate
        /// <summary>W86 toggle (reversible): true = the play scene gets the first buyer's crate at base 2 (FirstBuyerCrateV01:
        /// an organ laid on it is bought at the catalogue price into the inventory cash). false = the next Make leaves it
        /// out; in an existing play scene switch the "[Sale] ..." object (or the component's SaleEnabled) off.</summary>
        public static bool FirstBuyerCrate = true;
        public const string CrateName = "[Sale] First buyer crate (SALES SG-D27, W86)";
        static readonly Vector3 CrateSize = new(1.4f, 0.72f, 0.8f);          // a wide wooden crate: length, height, depth (m)

        /// <summary>Re-places the crate in the open play scene (not saved): for a check without a full Make.</summary>
        public static string PlaceBuyerCrateInOpenScene(string mapTag, string ver)
        {
            Log.Clear();
            var scene = SceneManager.GetActiveScene();
            var roots = scene.GetRootGameObjects();
            var shed = roots.FirstOrDefault(g => g.name == Shed);
            if (shed == null) return "missing: " + Shed + " in " + scene.path;
            DataDir(mapTag, ver, out string districtFile);
            var district = districtFile != null ? MiniJson.Parse(File.ReadAllText(districtFile)) as Dictionary<string, object> : null;
            Terrain terrain = roots.SelectMany(g => g.GetComponentsInChildren<Terrain>(true)).OrderBy(t => t.GetComponent<TerrainCollider>() ? 0 : 1).FirstOrDefault();
            MapHeightSampler sampler = roots.SelectMany(g => g.GetComponentsInChildren<MapHeightSampler>(true)).FirstOrDefault();
            var skip = new HashSet<Transform>(roots.Where(g => Carry.Contains(g.name)).Select(g => g.transform));
            string sideDir = scene.path.Substring(0, scene.path.Length - ".unity".Length);
            Physics.SyncTransforms();
            return PlaceBuyerCrate(scene, shed.transform, ZonePoly(district, "BASE-PAD"), ZonePoly(district, "BASE-TURN"),
                (x, z) => Ground(scene, sampler, terrain, skip, x, z), sideDir);
        }

        // Outside a solid shed wall (a "*wall*" box collider at least crate-long), the wall facing the van pad first; the
        // crate's long side along the wall, 0.2 m off it. A spot is taken when the crate stays off the van pad / turning
        // apron (0.3 m), stands on ground no steeper than 0.25 m across, and its box hits no other collider above the ground.
        static string PlaceBuyerCrate(Scene scene, Transform shed, Vector2[] pad, Vector2[] apron, Func<float, float, float> ground, string sideDir)
        {
            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == CrateName).ToArray()) Object.DestroyImmediate(old);
            var shedCols = shed.GetComponentsInChildren<Collider>(true).Where(c => !c.isTrigger).ToArray();
            if (shedCols.Length == 0) return "missing: colliders on the shed; no buyer crate";
            Bounds all = shedCols[0].bounds; foreach (var c in shedCols) all.Encapsulate(c.bounds);
            Vector3 centre = new(all.center.x, 0f, all.center.z);
            Vector3 toPad = pad != null ? Centre3(pad) - centre : shed.forward; toPad.y = 0f; toPad.Normalize();
            var cands = new List<(float score, Vector3 pos, Quaternion rot, string wall)>();
            foreach (var box in shedCols.OfType<BoxCollider>())
            {
                if (box.name.IndexOf("wall", StringComparison.OrdinalIgnoreCase) < 0) continue;
                Vector3 s = Vector3.Scale(box.size, box.transform.lossyScale);
                bool thinX = Mathf.Abs(s.x) < Mathf.Abs(s.z);
                float length = Mathf.Abs(thinX ? s.z : s.x), thick = Mathf.Abs(thinX ? s.x : s.z);
                if (length < CrateSize.x + .4f) continue;
                Vector3 wc = box.transform.TransformPoint(box.center);
                Vector3 across = box.transform.rotation * (thinX ? Vector3.right : Vector3.forward); across.y = 0f; across.Normalize();
                if (Vector3.Dot(across, new Vector3(wc.x, 0f, wc.z) - centre) < 0f) across = -across;   // outward
                Vector3 p = wc + across * (thick * .5f + .2f + CrateSize.z * .5f);
                // along the wall: from its pad-side end (seen from the van) back to its middle, every 0.2 m
                Vector3 along = Vector3.Cross(Vector3.up, across); if (Vector3.Dot(along, toPad) < 0f) along = -along;
                float slack = (length - CrateSize.x) * .5f - .1f;
                for (float o = slack; o >= -.01f; o -= .2f)
                {
                    Vector3 q = p + along * Mathf.Max(0f, o);
                    cands.Add((Vector3.Dot(across, toPad) + o * .01f, new Vector3(q.x, 0f, q.z), Quaternion.LookRotation(across, Vector3.up), box.name));
                }
            }
            var rejected = new List<string>();
            var noted = new HashSet<string>();
            foreach (var cand in cands.OrderByDescending(k => k.score))
            {
                var corners = new List<Vector3>();
                for (int k = 0; k < 4; k++) corners.Add(cand.pos + cand.rot * new Vector3(((k & 1) == 0 ? -.5f : .5f) * CrateSize.x, 0f, ((k & 2) == 0 ? -.5f : .5f) * CrateSize.z));
                if (corners.Concat(new[] { cand.pos }).Any(q => new[] { pad, apron }.Any(poly => poly != null && InsidePoly(poly, Plan(q), .3f)))) { if (noted.Add(cand.wall)) rejected.Add(cand.wall + ": on the van pad/apron"); continue; }
                var gys = corners.Select(q => ground(q.x, q.z)).ToArray();
                if (gys.Max() - gys.Min() > .25f) { if (noted.Add(cand.wall)) rejected.Add(cand.wall + $": ground slope {gys.Max() - gys.Min():0.00} m"); continue; }
                Vector3 at = new(cand.pos.x, gys.Average() - .03f, cand.pos.z);
                var hits = Physics.OverlapBox(at + Vector3.up * (CrateSize.y * .5f + .1f), CrateSize * .5f - new Vector3(.02f, .08f, .02f), cand.rot, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                    .Where(c => c.gameObject.scene == scene && !(c is TerrainCollider) && !c.transform.IsChildOf(shed) && c.bounds.max.y > ground(c.bounds.center.x, c.bounds.center.z) + .3f).ToArray();
                if (hits.Length > 0) { if (noted.Add(cand.wall)) rejected.Add(cand.wall + ": hits " + PathOf(hits[0].transform)); continue; }
                var crate = BuildCrate(scene, at, cand.rot, sideDir);
                return $"buyer crate: {CrateName} at {F(at)} yaw {cand.rot.eulerAngles.y:0.#}, outside the shed's {cand.wall}" +
                       (rejected.Count > 0 ? " (skipped: " + string.Join("; ", rejected) + ")" : "") +
                       $"; sale zone {F(crate.ZoneWorldCenter)}, FirstBuyerCrateV01 SaleEnabled {crate.SaleEnabled}";
            }
            return "WARNING: no clear spot for the buyer crate beside the shed walls" + (rejected.Count > 0 ? " (" + string.Join("; ", rejected) + ")" : " (no wall colliders)");
        }

        static FirstBuyerCrateV01 BuildCrate(Scene scene, Vector3 at, Quaternion rot, string sideDir)
        {
            const string T1 = "Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Materials/";
            var planks = AssetDatabase.LoadAssetAtPath<Material>(T1 + "T1_T23a_planks.mat");
            var wood = AssetDatabase.LoadAssetAtPath<Material>(T1 + "T1_T23_wood.mat") ?? planks;
            var root = new GameObject(CrateName);
            SceneManager.MoveGameObjectToScene(root, scene);
            root.transform.SetPositionAndRotation(at, rot);
            Vector3 sz = CrateSize;
            var cache = new Dictionary<string, Mesh>();
            void Part(string name, Vector3 centre, Vector3 size, Material mat)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                Object.DestroyImmediate(go.GetComponent<Collider>());
                go.name = name;
                go.transform.SetParent(root.transform, false);
                go.transform.localPosition = centre; go.transform.localScale = size;
                var mf = go.GetComponent<MeshFilter>();
                string key = $"{size.x:0.00}_{size.y:0.00}_{size.z:0.00}";
                if (!cache.TryGetValue(key, out var mesh))
                {   // metre UVs (2 m tile), as the shed's T1 boxes
                    mesh = Object.Instantiate(mf.sharedMesh); mesh.name = "CrateBox_" + key;
                    var v = mesh.vertices; var nn = mesh.normals; var uv = new Vector2[v.Length];
                    for (int i = 0; i < v.Length; i++)
                    {
                        Vector3 q = Vector3.Scale(v[i], size) / 2f;
                        uv[i] = Mathf.Abs(nn[i].y) > .5f ? new Vector2(q.x, q.z) : Mathf.Abs(nn[i].x) > .5f ? new Vector2(q.z, q.y) : new Vector2(q.x, q.y);
                    }
                    mesh.uv = uv;
                    string path = $"{sideDir}/CrateBox_{key.Replace('.', 'p')}.asset";
                    AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(mesh, path);
                    cache[key] = mesh;
                }
                mf.sharedMesh = mesh;
                if (mat != null) go.GetComponent<MeshRenderer>().sharedMaterial = mat;
            }
            Part("Body", new Vector3(0f, sz.y * .5f - .02f, 0f), new Vector3(sz.x - .06f, sz.y - .04f, sz.z - .06f), planks);
            Part("Lid", new Vector3(0f, sz.y - .025f, 0f), new Vector3(sz.x, .05f, sz.z), wood);
            for (int k = 0; k < 4; k++)
                Part("Corner batten " + k, new Vector3(((k & 1) == 0 ? -.5f : .5f) * (sz.x - .08f), sz.y * .5f - .02f, ((k & 2) == 0 ? -.5f : .5f) * (sz.z - .08f)), new Vector3(.09f, sz.y - .04f, .09f), wood);
            Part("Skid front", new Vector3(0f, .03f, -.5f * (sz.z - .14f)), new Vector3(sz.x - .02f, .06f, .1f), wood);
            Part("Skid back", new Vector3(0f, .03f, .5f * (sz.z - .14f)), new Vector3(sz.x - .02f, .06f, .1f), wood);
            var col = root.AddComponent<BoxCollider>();
            col.center = new Vector3(0f, sz.y * .5f, 0f); col.size = sz;
            var crate = root.AddComponent<FirstBuyerCrateV01>();
            crate.ZoneCenter = new Vector3(0f, sz.y + .3f, 0f);
            crate.ZoneSize = new Vector3(sz.x + .1f, .7f, sz.z + .1f);
            EditorUtility.SetDirty(root);
            return crate;
        }

        static string BuildSettingsFirst(string scenePath)
        {
            var list = EditorBuildSettings.scenes.Where(s => s.path != scenePath).ToList();
            list.Insert(0, new EditorBuildSettingsScene(scenePath, true));
            EditorBuildSettings.scenes = list.ToArray();
            return "build settings: " + string.Join(", ", list.Select(s => Path.GetFileNameWithoutExtension(s.path) + (s.enabled ? "" : " (off)"))) + " (this play scene first)";
        }

        // ------------------------------------------------------------------ crowd file
        // G44 phase 2 (lead, 21.10): the crowd walks in every inhabited district of the map, each with its district id = the id of the
        // G44 spawn tables (hamlet, rough, downtown, construction, beach, port, forest), so Vadim's NPC types appear where they live.
        // Densities = i10's per district (village 3/2, residential 14/14, old_town 12/14, transition 6/5, beach 8/4, industrial 5/3, forest 2/2).
        sealed class CrowdSpec { public string Id, NameRu, Profile = "town_walker"; public int Day, Evening; public List<(string id, Vector2[] pts)> Lines = new(); }

        static TextAsset WriteCrowd(string sideDir, string mapTag, string ver, Dictionary<string, object> district, string dataDir, Vector2[] pad, TextAsset i10Crowd, NpcSpawnTables tables)
        {
            var specs = new List<CrowdSpec>();
            var hamlet = new CrowdSpec { Id = CrowdDistrict, NameRu = "Хутор", Day = 3, Evening = 2 };
            foreach (var z in List(district, "zones").OfType<Dictionary<string, object>>())
            {
                string kind = Str(z, "kind");
                if ((kind == "street" || kind == "footpath" || kind == "path" || kind == "lane") && z.ContainsKey("line")) hamlet.Lines.Add((Str(z, "id"), Pts(z["line"])));
            }
            specs.Add(hamlet);
            Dictionary<string, object> Load(string name)
            {
                if (dataDir == null) return null;
                string f = Directory.Exists(dataDir + "/districts") ? Directory.GetFiles(dataDir + "/districts", name + "_*.json").FirstOrDefault() : null;
                return f != null ? MiniJson.Parse(File.ReadAllText(f)) as Dictionary<string, object> : null;
            }
            void FromZones(CrowdSpec s, string file, params string[] kinds)
            {
                var d = Load(file);
                if (d == null) return;
                foreach (var z in List(d, "zones").OfType<Dictionary<string, object>>())
                    if (kinds.Contains(Str(z, "kind")) && (z.ContainsKey("line") || z.ContainsKey("poly_line")))
                        s.Lines.Add((Str(z, "id"), Pts(z.TryGetValue("line", out var l) ? l : z["poly_line"])));
                if (s.Lines.Count > 0) specs.Add(s);
            }
            FromZones(new CrowdSpec { Id = "rough", NameRu = "Неблагополучный", Day = 14, Evening = 14 }, "rough", "track", "road");
            FromZones(new CrowdSpec { Id = "construction", NameRu = "Стройка", Day = 6, Evening = 5 }, "construction", "track", "path");
            FromZones(new CrowdSpec { Id = "beach", NameRu = "Пляж", Day = 8, Evening = 4, Profile = "beach_walker" }, "beach", "path", "boardwalk", "van_route");
            FromZones(new CrowdSpec { Id = "port", NameRu = "Порт", Day = 5, Evening = 3 }, "port", "road");
            FromZones(new CrowdSpec { Id = "forest", NameRu = "Лес", Day = 2, Evening = 2 }, "forest", "road");
            var dt = Load("downtown");
            if (dt != null)
            {   // Downtown: walk lines on both sidewalks (axis +- 8.5 m), cut where they would cross another street's carriageway
                var streets = List(dt, "zones").OfType<Dictionary<string, object>>().Where(z => Str(z, "kind") == "street" && z.ContainsKey("poly_line")).Select(z => (Str(z, "id"), Pts(z["poly_line"]))).ToList();
                var s = new CrowdSpec { Id = "downtown", NameRu = "Даунтаун", Day = 12, Evening = 14 };
                foreach (var (sid, pl) in streets)
                    foreach (int sg in new[] { 1, -1 })
                    {
                        var run = new List<Vector2>(); int k = 0;
                        for (int i = 0; i + 1 < pl.Length; i++)
                        {
                            Vector2 a = pl[i], b = pl[i + 1], d = (b - a).normalized, nrm = new Vector2(-d.y, d.x) * sg;
                            int n = Mathf.Max(1, Mathf.CeilToInt((b - a).magnitude / 2f));
                            for (int j = 0; j <= n; j++)
                            {
                                Vector2 q = Vector2.Lerp(a, b, j / (float)n) + nrm * 8.5f;
                                bool cross = streets.Any(o => o.Item1 != sid && DistToPolyline(o.Item2, q, out _) < 6.6f);
                                if (!cross) { run.Add(q); continue; }
                                if (run.Count > 6) s.Lines.Add(($"{sid}_{(sg > 0 ? "L" : "R")}{k++}", run.ToArray()));
                                run = new List<Vector2>();
                            }
                        }
                        if (run.Count > 6) s.Lines.Add(($"{sid}_{(sg > 0 ? "L" : "R")}{k++}", run.ToArray()));
                    }
                if (s.Lines.Count > 0) specs.Add(s);
            }
            Vector2? padC = pad != null ? Centre(pad) : (Vector2?)null;
            bool NearPad(Vector2 p, float r) => padC.HasValue && Vector2.Distance(p, padC.Value) < r;
            var dists = new StringBuilder(); var routes = new StringBuilder(); var spawns = new StringBuilder(); var conns = new StringBuilder();
            int nr = 0, ns = 0, nc = 0;
            var summary = new List<string>();
            foreach (var s in specs)
            {
                var all = s.Lines.Select(l => (l.id, pts: Clean(l.pts))).Where(l => l.pts.Length > 1).ToList();
                var loops = all.Where(l => Length(l.pts) >= 25f && !NearPad(l.pts[0], 15f) && !NearPad(l.pts[l.pts.Length - 1], 15f)).ToList();
                if (loops.Count == 0) continue;
                var ends = new List<Vector2>();
                for (int i = 0; i < all.Count; i++)
                    foreach (var e in new[] { all[i].pts[0], all[i].pts[all[i].pts.Length - 1] })
                        if (!all.Where((l, j) => j != i).Any(l => DistToPolyline(l.pts, e, out _) < 4f) && !NearPad(e, 30f) && !ends.Any(x => Vector2.Distance(x, e) < 5f)) ends.Add(e);
                var links = new List<Vector2[]>();
                for (int i = 0; i < all.Count; i++)
                    foreach (var e in new[] { all[i].pts[0], all[i].pts[all[i].pts.Length - 1] })
                    {
                        float best = s.Id == "downtown" ? 18f : 10f; Vector2 q = default; bool found = false;
                        for (int j = 0; j < all.Count; j++)
                        {
                            if (j == i) continue;
                            float d = DistToPolyline(all[j].pts, e, out Vector2 p);
                            if (d < best) { best = d; q = p; found = true; }
                        }
                        if (found) links.Add(new[] { e, q });
                    }
                Vector2 speed = s.Profile == "beach_walker" ? new Vector2(.8f, 1.2f) : new Vector2(1.0f, 1.5f);
                if (s.Id == CrowdDistrict && i10Crowd != null)
                {   // the Hamlet keeps i10's numbers exactly (G43)
                    var i10 = CrowdData.Parse(i10Crowd.text);
                    var ids = new HashSet<string> { CrowdDistrict };
                    var row = tables != null ? tables.Find(CrowdDistrict) : null;
                    if (row != null && row.Aliases != null) ids.UnionWith(row.Aliases);
                    var d = i10.Districts.FirstOrDefault(x => ids.Contains(x.Id));
                    if (d != null) { s.Day = d.Day; s.Evening = d.Evening; if (d.Routes.Count > 0) speed = i10.Routes[d.Routes[0]].Speed; }
                }
                // walk graph of this district alone: keep loops / spawn points connected to its longest loop
                string One(List<(string id, Vector2[] pts)> L, List<Vector2> E) => ComposeCrowd(mapTag, new[] { s }, L, E, all, links, speed);
                var graph = CrowdData.Parse(One(loops, ends));
                var prof = s.Profile == "beach_walker" ? CrowdProfile.Beach : CrowdProfile.Town;
                int main = Enumerable.Range(0, loops.Count).OrderByDescending(i => Length(loops[i].pts)).First();
                var tmp = new List<Vector2>();
                bool Reaches(Vector2 p)
                {
                    int a = graph.Graph.Nearest(p, prof), b = graph.Graph.Nearest(loops[main].pts[0], prof);
                    tmp.Clear();
                    return a >= 0 && b >= 0 && graph.Graph.FindPath(a, b, prof, tmp);
                }
                var keepLoops = loops.Where(l => Reaches(l.pts[0])).ToList();
                var keepEnds = ends.Where(Reaches).ToList();
                if (keepEnds.Count == 0) keepEnds = keepLoops.SelectMany(l => new[] { l.pts[0], l.pts[l.pts.Length - 1] }).Where(e => !NearPad(e, 30f)).Take(4).ToList();
                dists.Append(dists.Length > 0 ? ", " : "").Append($"{{\"id\": \"{s.Id}\", \"name_ru\": \"{s.NameRu}\", \"walkers_day\": {s.Day}, \"walkers_evening\": {s.Evening}}}");
                for (int i = 0; i < keepLoops.Count; i++)
                {
                    var p = keepLoops[i].pts;
                    var there = p.Concat(p.Reverse().Skip(1).Take(p.Length - 2)).ToArray();
                    routes.Append(nr++ > 0 ? ",\n    " : "\n    ").Append($"{{\"id\": \"ROUTE_{s.Id}_{i + 1:00}\", \"source\": \"{keepLoops[i].id}\", \"district_id\": \"{s.Id}\", \"profile\": \"{s.Profile}\", \"closed\": true, \"speed_mps\": [{N(speed.x)}, {N(speed.y)}], \"polyline_m\": {Json(there)}}}");
                }
                for (int i = 0; i < keepEnds.Count; i++)
                    spawns.Append(ns++ > 0 ? ",\n    " : "\n    ").Append($"{{\"id\": \"SPAWN_{s.Id}_{i + 1:00}\", \"district_id\": \"{s.Id}\", \"position_m\": [{N(keepEnds[i].x)}, {N(keepEnds[i].y)}], \"usage\": [\"spawn\", \"despawn\"], \"min_player_distance_m\": 25, \"visibility_grace_s\": 2}}");
                foreach (var l in all) conns.Append(nc++ > 0 ? ",\n    " : "\n    ").Append($"{{\"id\": \"STREET_{s.Id}_{l.id}\", \"profile\": \"{s.Profile}\", \"purpose\": \"network_connection\", \"polyline_m\": {Json(l.pts)}}}");
                foreach (var l in links) conns.Append(nc++ > 0 ? ",\n    " : "\n    ").Append($"{{\"id\": \"LINK_{s.Id}_{nc:000}\", \"profile\": \"{s.Profile}\", \"purpose\": \"network_connection\", \"polyline_m\": {Json(l)}}}");
                summary.Add($"{s.Id} {keepLoops.Count} loops / {keepEnds.Count} spawns ({s.Day}/{s.Evening})");
            }
            var sbAll = new StringBuilder();
            sbAll.Append("{\n  \"schema_version\": \"1.0\",\n  \"revision\": \"").Append(mapTag).Append("_play_").Append(ver).Append("_districts\",\n");
            sbAll.Append("  \"generator\": \"W85PlayIntegrator: out-and-back loops on the streets / tracks / sidewalks of every inhabited district\",\n");
            sbAll.Append("  \"coordinates\": {\"unit\": \"metre\", \"x\": \"east\", \"y\": \"north\", \"unity_mapping\": \"(x, terrain_height, y)\"},\n");
            sbAll.Append("  \"districts\": [").Append(dists).Append("],\n  \"routes\": [").Append(routes).Append("\n  ],\n  \"spawn_despawn_points\": [").Append(spawns).Append("\n  ],\n  \"connections\": [").Append(conns).Append("\n  ]\n}\n");
            string path = $"{sideDir}/crowd_{mapTag}_play_{ver}.json";
            File.WriteAllText(path, sbAll.ToString(), new UTF8Encoding(false));
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var asset = AssetDatabase.LoadAssetAtPath<TextAsset>(path);
            var check = asset != null ? CrowdData.Parse(asset.text) : null;
            Note(check == null ? "missing: crowd file did not import " + path
                : $"crowd: {path}: {check.Districts.Count} districts, {check.Routes.Count} loops, {check.Spawns.Count} spawn points, {check.Graph.Count} graph nodes — " + string.Join("; ", summary));
            return asset;
        }

        static string ComposeCrowd(string mapTag, IEnumerable<CrowdSpec> specs, List<(string id, Vector2[] pts)> loops, List<Vector2> ends, List<(string id, Vector2[] pts)> all, List<Vector2[]> links, Vector2 speed)
        {
            var s = specs.First();
            var sb = new StringBuilder();
            sb.Append("{\n  \"schema_version\": \"1.0\",\n  \"revision\": \"").Append(mapTag).Append("_check\",\n  \"generator\": \"check\",\n");
            sb.Append("  \"coordinates\": {\"unit\": \"metre\", \"x\": \"east\", \"y\": \"north\", \"unity_mapping\": \"(x, terrain_height, y)\"},\n");
            sb.Append($"  \"districts\": [{{\"id\": \"{s.Id}\", \"name_ru\": \"{s.NameRu}\", \"walkers_day\": {s.Day}, \"walkers_evening\": {s.Evening}}}],\n  \"routes\": [");
            for (int i = 0; i < loops.Count; i++)
            {
                var p = loops[i].pts;
                var there = p.Concat(p.Reverse().Skip(1).Take(p.Length - 2)).ToArray();
                sb.Append(i > 0 ? ",\n    " : "\n    ").Append($"{{\"id\": \"R{i}\", \"source\": \"{loops[i].id}\", \"district_id\": \"{s.Id}\", \"profile\": \"{s.Profile}\", \"closed\": true, \"speed_mps\": [{N(speed.x)}, {N(speed.y)}], \"polyline_m\": {Json(there)}}}");
            }
            sb.Append("\n  ],\n  \"spawn_despawn_points\": [");
            for (int i = 0; i < ends.Count; i++)
                sb.Append(i > 0 ? ",\n    " : "\n    ").Append($"{{\"id\": \"S{i}\", \"district_id\": \"{s.Id}\", \"position_m\": [{N(ends[i].x)}, {N(ends[i].y)}], \"usage\": [\"spawn\", \"despawn\"], \"min_player_distance_m\": 25, \"visibility_grace_s\": 2}}");
            sb.Append("\n  ],\n  \"connections\": [");
            int n = 0;
            foreach (var l in all) sb.Append(n++ > 0 ? ",\n    " : "\n    ").Append($"{{\"id\": \"C{n}\", \"profile\": \"{s.Profile}\", \"purpose\": \"network_connection\", \"polyline_m\": {Json(l.pts)}}}");
            foreach (var l in links) sb.Append(n++ > 0 ? ",\n    " : "\n    ").Append($"{{\"id\": \"L{n}\", \"profile\": \"{s.Profile}\", \"purpose\": \"network_connection\", \"polyline_m\": {Json(l)}}}");
            sb.Append("\n  ]\n}\n");
            return sb.ToString();
        }

        // ------------------------------------------------------------------ placement helpers
        static float Ground(Scene scene, MapHeightSampler sampler, Terrain terrain, HashSet<Transform> skip, float x, float z)
        {
            float t = sampler != null && sampler.Terrain != null ? sampler.Height(x, z)
                : terrain != null ? terrain.SampleHeight(new Vector3(x, 0f, z)) + terrain.transform.position.y : 0f;
            float best = t;
            // flat ground overlays (roads, pads, yards: wide and low) a little above the terrain count as ground
            foreach (var h in Physics.RaycastAll(new Vector3(x, t + 3f, z), Vector3.down, 6f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
            {
                var c = h.collider;
                if (c.gameObject.scene != scene || c is TerrainCollider || h.normal.y < .7f || h.point.y > t + .35f || h.point.y <= best) continue;
                if (skip.Contains(c.transform.root) || InBuilding(c.transform)) continue;
                if (Mathf.Max(c.bounds.size.x, c.bounds.size.z) < 2f) continue;
                best = h.point.y;
            }
            return best;
        }

        // Map props standing inside a placed group are hidden in the play scene (small ones only); buildings, big objects
        // and terrain trees are reported.
        static void ClearInside(Scene scene, Transform root, Bounds local, HashSet<Transform> skip, Terrain terrain, Func<float, float, float> ground, string label)
        {
            var ext = local.extents - new Vector3(.1f, 0f, .1f);
            ext.y = Mathf.Max(.1f, ext.y - .15f);
            var centre = root.TransformPoint(local.center + new Vector3(0f, .15f, 0f));
            var hidden = new HashSet<GameObject>();
            foreach (var c in Physics.OverlapBox(centre, Vector3.Max(ext, Vector3.one * .05f), root.rotation, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
            {
                if (c.gameObject.scene != scene || c is TerrainCollider || skip.Contains(c.transform.root)) continue;
                var cb = c.bounds;
                if (cb.max.y < ground(cb.center.x, cb.center.z) + .3f) continue; // a ground overlay
                if (InBuilding(c.transform)) { Note($"WARNING {label} intersects the building {PathOf(c.transform)}"); continue; }
                Transform top = c.transform;
                while (top.parent != null && top.parent.parent != null && !top.parent.name.StartsWith("District_")) top = top.parent;
                var rs = top.GetComponentsInChildren<Renderer>(true);
                var tb = rs.Length > 0 ? rs.Select(r => r.bounds).Aggregate((a, b) => { a.Encapsulate(b); return a; }) : cb;
                if (Mathf.Max(tb.size.x, tb.size.z) > 4f) { Note($"WARNING {label} intersects {PathOf(top)} (too big to hide)"); continue; }
                if (hidden.Add(top.gameObject)) { top.gameObject.SetActive(false); Note($"hid map prop {PathOf(top)} (stood inside {label})"); }
            }
            if (terrain == null) return;
            var td = terrain.terrainData; int trees = 0;
            foreach (var tree in td.treeInstances)
            {
                var w = Vector3.Scale(tree.position, td.size) + terrain.transform.position;
                var l = root.InverseTransformPoint(w);
                if (Mathf.Abs(l.x - local.center.x) < local.extents.x && Mathf.Abs(l.z - local.center.z) < local.extents.z) trees++;
            }
            if (trees > 0) Note($"WARNING {label}: {trees} terrain tree(s) inside (TerrainData belongs to the map build: remove them there)");
            // baked tall grass (G24) is a map asset too: count the blades that would poke through the floor
            int blades = 0;
            foreach (var grass in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<OnlyVolunteers.ThirdParty.GrassInstancerMB.ChunkedGrassRenderer24>(true)))
            {
                var data = grass.data;
                if (data == null || data.instances == null) continue;
                byte[] bytes = data.instances.bytes;
                foreach (var ch in data.chunks)
                {
                    var cb = new Bounds(ch.centre, ch.extents * 2f);
                    var box = new Bounds(root.TransformPoint(local.center), Vector3.one * (local.extents.magnitude * 2f));
                    if (!cb.Intersects(box)) continue;
                    for (uint i = ch.start; i < ch.start + ch.count && (i + 1) * 32 <= bytes.Length; i++)
                    {
                        var w = new Vector3(BitConverter.ToSingle(bytes, (int)i * 32), 0f, BitConverter.ToSingle(bytes, (int)i * 32 + 8));
                        var l = root.InverseTransformPoint(w);
                        if (Mathf.Abs(l.x - local.center.x) < local.extents.x && Mathf.Abs(l.z - local.center.z) < local.extents.z) blades++;
                    }
                }
            }
            if (blades > 0) Note($"WARNING {label}: {blades} baked grass blade(s) inside (the map's grass bake must treat this rect as a hard surface)");
        }

        // Where an i10 plan point of the group is now (the root moved rigidly).
        static Vector3 MapPt(Group g, Vector2 i10Plan) =>
            g.Root.position + g.Root.rotation * (Quaternion.Inverse(g.I10Rot) * (new Vector3(i10Plan.x, g.I10Pos.y, i10Plan.y) - g.I10Pos));

        static float MinFaceGap(Group g, Vector3 faceCentre, Vector3 normal) =>
            g.Pts.Min(p => Vector3.Dot(MapPt(g, p) - faceCentre, normal));

        static Rect Footprint(Group g)
        {
            var pts = g.Pts.Select(p => Plan(MapPt(g, p))).ToArray();
            return Rect.MinMaxRect(pts.Min(p => p.x), pts.Min(p => p.y), pts.Max(p => p.x), pts.Max(p => p.y));
        }

        static bool HutBox(Transform hut, out Vector3 centre, out Quaternion rot, out Vector3 half)
        {
            var box = hut.GetComponentsInChildren<BoxCollider>(true).Where(b => !b.isTrigger)
                .OrderByDescending(b => Vector3.Scale(b.size, b.transform.lossyScale).x * Vector3.Scale(b.size, b.transform.lossyScale).z).FirstOrDefault();
            if (box == null) { centre = default; rot = default; half = default; return false; }
            centre = box.transform.TransformPoint(box.center); centre.y = 0f;
            rot = Quaternion.Euler(0f, box.transform.eulerAngles.y, 0f);
            half = Vector3.Scale(box.size, box.transform.lossyScale) * .5f;
            return true;
        }

        // Centre and outward normal of the box face that looks most towards `dir` (plan).
        static void Face(Vector3 c, Quaternion r, Vector3 half, Vector3 dir, out Vector3 centre, out Vector3 normal)
        {
            dir.y = 0f;
            var faces = new[] { (r * Vector3.right, half.x), (r * Vector3.left, half.x), (r * Vector3.forward, half.z), (r * Vector3.back, half.z) };
            var best = faces.OrderByDescending(f => Vector3.Dot(f.Item1, dir)).First();
            normal = best.Item1; centre = c + best.Item1 * best.Item2;
        }

        static Transform FindHut(GameObject[] roots)
        {
            Transform any = null;
            foreach (var g in roots)
                foreach (var t in g.GetComponentsInChildren<Transform>(true))
                    if (t.name == HutName)
                    {
                        if (t.parent != null && t.parent.name == HutDistrict) return t;
                        any ??= t;
                    }
            return any;
        }

        static Transform FindPath(GameObject[] roots, string path)
        {
            int i = path.IndexOf('/');
            var root = roots.FirstOrDefault(g => g.name == (i < 0 ? path : path.Substring(0, i)));
            return root == null ? null : i < 0 ? root.transform : root.transform.Find(path.Substring(i + 1));
        }

        static bool InBuilding(Transform t)
        {
            for (; t != null; t = t.parent) if (t.name.StartsWith("B_") || t.name == "Buildings") return true;
            return false;
        }

        // ------------------------------------------------------------------ FishNet
        static string SceneIds(Scene scene)
        {
            var create = typeof(NetworkObject).GetMethod("CreateSceneId", BindingFlags.NonPublic | BindingFlags.Static, null,
                new[] { typeof(Scene), typeof(bool), typeof(int).MakeByRefType() }, null);
            var idField = typeof(NetworkObject).GetField("SceneId", BindingFlags.NonPublic | BindingFlags.Instance);
            if (create == null || idField == null) return "missing: FishNet NetworkObject.CreateSceneId (API changed): use Fish-Networking > Utility > Reserialize NetworkObjects";
            object[] args = { scene, true, 0 };
            var nobs = create.Invoke(null, args) as List<NetworkObject> ?? new List<NetworkObject>();
            var ids = nobs.Select(n => (ulong)idField.GetValue(n)).ToList();
            int unset = nobs.Count(n => !n.IsSceneObject), dup = ids.Count - ids.Distinct().Count();
            return $"FishNet: {nobs.Count} scene NetworkObject(s) ({string.Join(", ", nobs.Select(n => n.name))}), {(int)args[2]} id(s) regenerated for {scene.path}, unset {unset}, duplicates {dup}";
        }

        // ------------------------------------------------------------------ data
        static string DataDir(string mapTag, string ver, out string districtFile)
        {
            districtFile = null;
            string root = $"Assets/OnlyVolunteers/Map/{mapTag}Build/Data";
            if (!Directory.Exists(root)) return null;
            string own = root + "/" + ver;                                      // the version the map was built from
            if (Directory.Exists(own + "/districts"))
            {
                string f0 = Directory.GetFiles(own + "/districts", "hamlet_*.json").FirstOrDefault();
                if (f0 != null) { districtFile = f0.Replace('\\', '/'); return own; }
            }
            foreach (string dir in Directory.GetDirectories(root, "v*").OrderByDescending(d => int.TryParse(Path.GetFileName(d).Substring(1), out int v) ? v : -1))
            {
                string f = Directory.Exists(dir + "/districts") ? Directory.GetFiles(dir + "/districts", "hamlet_*.json").FirstOrDefault() : null;
                if (f != null) { districtFile = f.Replace('\\', '/'); return dir.Replace('\\', '/'); }
            }
            return null;
        }

        static Vector2[] ZonePoly(Dictionary<string, object> district, string idSuffix)
        {
            var z = List(district, "zones").OfType<Dictionary<string, object>>().FirstOrDefault(d => Str(d, "id").EndsWith(idSuffix) && !Str(d, "id").Contains("no-tree"));
            var pts = z != null && z.TryGetValue("poly", out var p) ? Pts(p) : null;
            return pts != null && pts.Length >= 3 ? pts : null;
        }

        static Vector2? HutDoor(Dictionary<string, object> district, string hutName)
        {
            string id = hutName.StartsWith("B_") ? hutName.Substring(2) : hutName;
            var b = List(district, "buildings").OfType<Dictionary<string, object>>().FirstOrDefault(d => Str(d, "id") == id);
            var e = b != null ? List(b, "entrances").OfType<Dictionary<string, object>>().FirstOrDefault() : null;
            var p = e != null && e.TryGetValue("pos", out var v) ? Pts(new List<object> { v }) : null;
            return p != null && p.Length == 1 ? p[0] : (Vector2?)null;
        }

        static IEnumerable<object> List(Dictionary<string, object> d, string key) =>
            d != null && d.TryGetValue(key, out var v) && v is List<object> l ? l : Enumerable.Empty<object>();

        static string Str(Dictionary<string, object> d, string key) => d != null && d.TryGetValue(key, out var v) && v is string s ? s : "";

        static Vector2[] Pts(object o)
        {
            if (!(o is List<object> l)) return Array.Empty<Vector2>();
            var r = new List<Vector2>();
            foreach (var p in l)
                if (p is List<object> xy && xy.Count >= 2) r.Add(new Vector2(Convert.ToSingle(xy[0], CultureInfo.InvariantCulture), Convert.ToSingle(xy[1], CultureInfo.InvariantCulture)));
            return r.ToArray();
        }

        static Vector2[] Clean(Vector2[] pts)
        {
            var r = new List<Vector2>();
            foreach (var p in pts) if (r.Count == 0 || Vector2.Distance(r[r.Count - 1], p) > .05f) r.Add(p);
            return r.ToArray();
        }

        static float Length(Vector2[] p) { float s = 0f; for (int i = 1; i < p.Length; i++) s += Vector2.Distance(p[i - 1], p[i]); return s; }

        static float DistToPolyline(Vector2[] line, Vector2 p, out Vector2 nearest)
        {
            float best = float.MaxValue; nearest = line.Length > 0 ? line[0] : p;
            for (int i = 0; i + 1 < line.Length; i++)
            {
                Vector2 a = line[i], ab = line[i + 1] - a;
                float t = ab.sqrMagnitude > 1e-6f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude) : 0f;
                Vector2 q = t <= .01f ? a : t >= .99f ? line[i + 1] : a + ab * t; // vertices exactly, so the crowd graph merges them
                float d = Vector2.Distance(p, q);
                if (d < best) { best = d; nearest = q; }
            }
            return best;
        }

        static bool InsidePoly(Vector2[] poly, Vector2 p, float margin)
        {
            bool inside = false;
            for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
                if ((poly[i].y > p.y) != (poly[j].y > p.y) && p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x) inside = !inside;
            if (inside) return true;
            for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            {
                Vector2 a = poly[j], ab = poly[i] - a;
                float t = ab.sqrMagnitude > 1e-6f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude) : 0f;
                if (Vector2.Distance(p, a + ab * t) < margin) return true;
            }
            return false;
        }

        static float DistToRect(Rect r, Vector2 p) => Vector2.Distance(p, new Vector2(Mathf.Clamp(p.x, r.xMin, r.xMax), Mathf.Clamp(p.y, r.yMin, r.yMax)));
        static Vector2 Centre(Vector2[] poly) => new(poly.Average(p => p.x), poly.Average(p => p.y));
        static Vector3 Centre3(Vector2[] poly) { var c = Centre(poly); return new Vector3(c.x, 0f, c.y); }
        static Vector2 Plan(Vector3 p) => new(p.x, p.z);
        static string N(float v) => v.ToString("0.###", CultureInfo.InvariantCulture);
        static string Json(Vector2[] pts) => "[" + string.Join(", ", pts.Select(p => $"[{N(p.x)}, {N(p.y)}]")) + "]";
        static string F(Vector3 v) => $"({v.x:0.0}, {v.y:0.00}, {v.z:0.0})";
        static string Name(Object o) => o == null ? "MISSING" : !string.IsNullOrEmpty(o.name) ? o.name : Path.GetFileNameWithoutExtension(AssetDatabase.GetAssetPath(o));
        static string PathOf(Transform t) => t.parent == null ? t.name : PathOf(t.parent) + "/" + t.name;
        static void Note(string s) => Log.AppendLine(s);
        static string Fail(string s) { Note("FAILED: " + s); Debug.LogError("[W85Play] " + s); return Log.ToString(); }

        static void Folder(string path)
        {
            string[] parts = path.Split('/');
            string cur = parts[0];
            for (int i = 1; i < parts.Length; i++)
            {
                string next = cur + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(cur, parts[i]);
                cur = next;
            }
        }
    }
}
