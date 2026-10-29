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
    public static partial class W85PlayIntegrator   // + W85PlayIntegrator.Pharmacy.cs (city pharmacy, step 8b)
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
            EditorSceneManager.SaveOpenScenes(); // no "save modified scenes?" dialog (Fedya 25.10)
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

            // 8b. W86 look pass (lead 25.10, brief §2): SMAA, live sky reflection, material response on play-time copies (W86LookV01).
            if (ver != "v01")
            {
                var lookGo = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "W86_Look");
                if (!lookGo) { lookGo = new GameObject("W86_Look"); UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(lookGo, scene); }
                if (!lookGo.GetComponent<W86LookV01>()) lookGo.AddComponent<W86LookV01>();
                // Escape pause menu + graphics settings page (lead 25.10): owns Escape and the ov_gfx_* settings in this scene
                if (!lookGo.GetComponent<OnlyVolunteers.UI.Pause.W86PauseMenuV01>()) lookGo.AddComponent<OnlyVolunteers.UI.Pause.W86PauseMenuV01>();
                Note("look: W86LookV01 (SMAA High, sky reflection cubemap, material response rules)");
                Note(W86SmoothNormalsV01.Apply(scene, ver));
                Note(W86PropFixV01.Apply(scene, ver)); // lamps: stems between arms and lanterns (Fedya 25.10, screenshot 07)
                Note(W85Builder.LightAllLamps(scene));
                Note(W86PropFixV01.LiftCoplanar(scene)); // z-fighting surfaces (the square "shadow" in Fedya's recording)
                Note(W86PropFixV01.TrafficSignals(scene, ver)); // signal heads with hoods and a working cycle (Fedya 25.10, screenshot 06)
                Note(W86VehiclesV01.Apply(scene)); // G47 stage 2: CC0 world vehicles with LODs and colliders
                foreach (var life in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<OnlyVolunteers.Map.Look.V3.DistrictLife19V02>(true)))
                    if (life.wornLamps != null && life.wornLamps.Length > 0 && (life.calmAreas == null || life.calmAreas.Length == 0))
                    { life.calmAreas = new[] { W85Builder.DowntownCalmRect }; EditorUtility.SetDirty(life); Note("lamps: Downtown calm flicker area set"); }
                // ECONOMY spec v01 §6.3 + STORY M06 (lead 28.10): the W86 workshop building at Fedya's red mark (prefab Workshop_W86_v01,
                // ground fitted, reversible), its anchors (repair zone over the pit, mechanic, rival hand-in in the western bay) + story anchors.
                PlaceWorkshopZone(scene, dataDir, GroundNew);
                // Fedya 28.10: the city pharmacy in the ground-floor west bays of Rough 04-H3 (prefab Pharmacy_W86_v01, house cut
                // along the unit, front path, cash desk / staff routine / van stop anchors); W85PlayIntegrator.Pharmacy.cs.
                PlacePharmacy(scene, sideDir);
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

        // ------------------------------------------------------------------ ECONOMY + STORY: workshop and mission anchors
        /// <summary>ECONOMY spec v01 §6.3 + STORY_MISSIONS_SPEC v01 §9 / §17.2 (lead 28.10). The workshop is the W86 building
        /// Workshop_W86_v01 (prefab <see cref="WorkshopPrefabPath"/>, art ArtSource/Buildings/Workshop_W86, palette A) at Fedya's
        /// red mark (28.10: the meadow north of Stroyka, south of the Rough, east of the river, beside the curved road
        /// hamlet_to_rough), pose <see cref="WorkshopPos"/> / <see cref="WorkshopYaw"/>, doors and apron facing that road.
        /// The step places the building (find-or-create by name), fits the ground to it (<see cref="FitWorkshopGround"/>: local
        /// grading, a terrain hole for the pit, a gravel forecourt to the road, trees and baked grass cleared; undone and redone
        /// on every run through a backup beside the play scene) and moves the root <see cref="WorkshopAnchorsName"/> onto the
        /// building's pose, its children at the building-local points of Workshop_W86_anchors_v01.json: the van repair zone
        /// (OnlyVolunteers.Economy.WorkshopZone, middle bay over the pit), the mechanic point (StoryAnchor Workshop.Mechanic,
        /// beside the desk) and the M06 rival receiving zone (StoryAnchor M06.RivalHandIn, inside the western bay). The old
        /// 03-01-workshop on Stroyka stays as plain scenery with no function (no second workshop).
        /// A second root <see cref="StoryAnchorsName"/> carries the anchors that do not move with the workshop: the rival's
        /// occupied canopy on Stroyka (08:00-18:00), his off-shift spot and C01's placeholder arrival point at base 2.
        /// Idempotent: roots and children found by name (duplicates and the older single-zone root removed), every field re-set.</summary>
        public const string WorkshopAnchorsName = "W86_Workshop_Anchors";
        public const string StoryAnchorsName = "W86_Story_Anchors";
        /// <summary>The single-zone root of the first integration (28.10 morning); removed when found.</summary>
        public const string WorkshopZoneName = "[Economy] Workshop repair zone (03-01-workshop, middle bay)";
        // Story anchors on Stroyka / base 2 (world plan metres; placeholder poses).
        static readonly Vector2 RivalCanopyFallback = new(624.2f, 397.0f);    // beside 03-01-van (van on jacks), north side
        static readonly Vector2 RivalOffShiftAt = new(642.44f, 451.4f);       // in front of the dormitory door (03-08-dorm)
        static readonly Vector2 C01ArrivalAt = new(251.5f, 515.0f);           // in front of the B02 shed, west of the van spawn

        /// <summary>The workshop / story anchor step on the open play scene (building, ground, anchors; the scene is marked dirty,
        /// not saved; the terrain / grass assets and the ground backup are saved): no full Make needed.</summary>
        public static string PlaceWorkshopZoneInOpenScene(string mapTag, string ver)
        {
            Log.Clear();
            if (EditorApplication.isPlaying) return Fail("leave Play mode first");
            var scene = SceneManager.GetActiveScene();
            var roots = scene.GetRootGameObjects();
            string dataDir = DataDir(mapTag, ver, out _);
            Terrain terrain = roots.SelectMany(g => g.GetComponentsInChildren<Terrain>(true)).OrderBy(t => t.GetComponent<TerrainCollider>() ? 0 : 1).FirstOrDefault();
            MapHeightSampler sampler = roots.SelectMany(g => g.GetComponentsInChildren<MapHeightSampler>(true)).FirstOrDefault();
            var skip = new HashSet<Transform>(roots.Where(g => Carry.Contains(g.name)).Select(g => g.transform));
            PlaceWorkshopZone(scene, dataDir, (x, z) => Ground(scene, sampler, terrain, skip, x, z));
            EditorSceneManager.MarkSceneDirty(scene);
            AssetDatabase.SaveAssets();
            return Log.ToString();
        }

        static void PlaceWorkshopZone(Scene scene, string dataDir, Func<float, float, float> ground)
        {
            Physics.SyncTransforms();
            // the rival's canopy stays on Stroyka, beside 03-01-van of the construction data
            string file = dataDir != null && Directory.Exists(dataDir + "/districts") ? Directory.GetFiles(dataDir + "/districts", "construction_*.json").FirstOrDefault() : null;
            var district = file != null ? MiniJson.Parse(File.ReadAllText(file)) as Dictionary<string, object> : null;
            Vector2 canopy = RivalCanopyFallback;
            var van = List(district, "props").OfType<Dictionary<string, object>>().FirstOrDefault(p => Str(p, "id") == "03-01-van");
            Vector2[] vanPos = van != null && van.TryGetValue("pos", out var vp) ? Pts(new List<object> { vp }) : null;
            if (vanPos != null && vanPos.Length == 1) canopy = vanPos[0] + new Vector2(0f, 2.55f);

            // ---- the building at the red mark, its ground, then its anchors
            var A = WorkshopAnchorsData();
            if (A == null) { Note("missing: " + WorkshopAnchorsJsonPath + " (workshop not placed, anchors left where they are)"); return; }
            var building = PlaceWorkshopBuilding(scene);
            Note(FitWorkshopGround(scene, dataDir));
            Physics.SyncTransforms();
            Quaternion rot = Quaternion.Euler(0f, WorkshopYaw, 0f);
            Vector3 centre = WorkshopPos;

            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == WorkshopZoneName).ToList()) Object.DestroyImmediate(old);
            GameObject root = UniqueRoot(scene, WorkshopAnchorsName);
            root.transform.SetPositionAndRotation(centre, rot);
            root.transform.localScale = Vector3.one;
            EditorUtility.SetDirty(root);

            var zj = WsObj(A, "middle_bay_repair_zone");
            Vector3 zoneLocal = WsV3(zj, "position"), zoneSize = WsV3(zj, "size");
            if (zoneSize.x < .5f) zoneSize = new Vector3(3.2f, 3f, 6.4f);
            GameObject zoneGo = UniqueChild(root.transform, "RepairZone (middle bay)");
            zoneGo.transform.localPosition = zoneLocal;
            zoneGo.transform.localRotation = Quaternion.Euler(0f, WsNum(zj != null && zj.TryGetValue("yaw", out var zy) ? zy : null), 0f);
            zoneGo.transform.localScale = Vector3.one;
            var zone = zoneGo.GetComponent<OnlyVolunteers.Economy.WorkshopZone>();
            if (!zone) zone = zoneGo.AddComponent<OnlyVolunteers.Economy.WorkshopZone>();
            zone.Size = zoneSize;
            zone.Title = "Мастерская — ремонтная зона";
            zone.ShowMarkers = true;
            EditorUtility.SetDirty(zone);
            EditorUtility.SetDirty(zoneGo);

            var hj = WsObj(A, "west_bay_handin_zone");
            Vector3 handSize = WsV3(hj, "size");
            var handIn = Anchor(root.transform, "RivalHandInZone (western bay)", OnlyVolunteers.Story.StoryAnchor.RivalHandIn,
                "Приём конкурента (M06)", WsV3(hj, "position"), handSize, true, new Color(1f, 0.45f, 0.3f));
            var mj = WsObj(A, "mechanic_standing_point");
            // the mechanic is a character now (WorkshopMechanicV01): no placeholder post / title over his point
            var mechanic = Anchor(root.transform, "MechanicPoint", OnlyVolunteers.Story.StoryAnchor.WorkshopMechanic,
                "Механик", WsV3(mj, "position"), Vector3.zero, false, new Color(0.45f, 0.85f, 1f));
            mechanic.transform.localRotation = Quaternion.Euler(0f, WsNum(mj != null && mj.TryGetValue("yaw", out var my) ? my : null), 0f);
            Note(PlaceWorkshopLift(root, building, zone, mechanic.transform, A));

            // ---- story anchors that stay where they are when the workshop moves ----
            GameObject story = UniqueRoot(scene, StoryAnchorsName);
            story.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            story.transform.localScale = Vector3.one;
            EditorUtility.SetDirty(story);
            var canopyA = WorldAnchor(scene, story.transform, "RivalCanopy (Stroyka, 08-18)", OnlyVolunteers.Story.StoryAnchor.RivalCanopy,
                "Навес конкурента (заглушка)", canopy, 180f, true, new Color(1f, 0.6f, 0.2f), ground);
            var offShift = WorldAnchor(scene, story.transform, "RivalOffShift (dorm)", OnlyVolunteers.Story.StoryAnchor.RivalOffShift,
                "", RivalOffShiftAt, 0f, false, new Color(1f, 0.6f, 0.2f), ground);
            var c01 = WorldAnchor(scene, story.transform, "C01Arrival (base 2, placeholder)", OnlyVolunteers.Story.StoryAnchor.C01ArrivalB02,
                "C01 — скупщик крови (заглушка)", C01ArrivalAt, 270f, true, new Color(0.85f, 0.25f, 0.3f), ground);

            // ---- checks: van parked over the pit, both drive-ins, the hand-in floor, the partition doorway; ground under them ----
            Physics.SyncTransforms();
            Vector3 L(float x, float z) => root.transform.TransformPoint(new Vector3(x, 0f, z));
            Vector3 vanC = root.transform.TransformPoint(WsV3(WsObj(A, "van_park_point"), "position"));
            Vector3 handC = handIn.transform.position;
            string vanIn = Inside(scene, vanC, rot, new Vector3(2.2f, 2.4f, 5.4f));
            string midDrive = Inside(scene, L(0f, 10.5f), rot, new Vector3(2.4f, 2.4f, 9f));
            string westDrive = Inside(scene, L(-8.175f, 10.5f), rot, new Vector3(2.4f, 2.4f, 9f));
            string handInside = Inside(scene, handC, rot, handSize);
            string doorway = Inside(scene, L(-4.5f, -1.0f), rot, new Vector3(.5f, 1.8f, .8f));
            float mechGround = GroundRay(scene, mechanic.transform.position.x, mechanic.transform.position.z, ground) - mechanic.transform.position.y;
            Note($"workshop anchors: root {WorkshopAnchorsName} = building {(building ? building.name : "MISSING")} at {F(centre)} yaw {WorkshopYaw:0.#} (Fedya's red mark, north of Stroyka by hamlet_to_rough)");
            Note($"  repair zone {zoneSize.x:0.#} x {zoneSize.z:0.#} m at {F(zoneGo.transform.position)} (middle bay over the pit), ground {Spread(scene, zoneGo.transform.position, rot, zoneSize, ground)}; " +
                 (vanIn.Length > 0 ? "WARNING van box over the pit blocked by: " + vanIn : "van box over the pit clear") +
                 (midDrive.Length > 0 ? "; WARNING middle drive-in blocked by: " + midDrive : "; middle drive-in 2.4 x 9 m clear"));
            Note($"  rival hand-in {handSize.x:0.##} x {handSize.z:0.#} m at {F(handC)} (inside the western bay), ground {Spread(scene, handC, rot, handSize, ground)}" +
                 (handInside.Length > 0 ? "; WARNING inside: " + handInside : "; clear") +
                 (westDrive.Length > 0 ? "; WARNING west drive-in blocked by: " + westDrive : "; west drive-in 2.4 x 9 m clear") +
                 (doorway.Length > 0 ? "; WARNING partition doorway blocked by: " + doorway : "; partition doorway to the mechanic clear"));
            Note($"  mechanic point at {F(mechanic.transform.position)}, ground {mechGround:+0.00;-0.00} m");
            Note($"story anchors: canopy {F(canopyA.transform.position)} (beside 03-01-van, Stroyka), off-shift {F(offShift.transform.position)}, C01 {F(c01.transform.position)}; " +
                 $"canopy to hand-in {Vector3.Distance(canopyA.transform.position, handC):0.0} m, hand-in to repair {Vector3.Distance(handC, zoneGo.transform.position):0.0} m");
        }

        /// <summary>The lift session and the mechanic on W86_Workshop_Anchors (Fedya 29.10): the van park point (lift centre,
        /// yaw 180) and the control box point from Workshop_W86_lift_v01.json, WorkshopServiceV01 with the six moving nodes of
        /// the lift in the building instance (two carriages, four arms + their swing-in yaw), travel from the JSON, the zone
        /// switched to lift-only buying; WorkshopMechanicV01 at the mechanic point. Idempotent (found by name, fields re-set).</summary>
        static string PlaceWorkshopLift(GameObject root, GameObject building, OnlyVolunteers.Economy.WorkshopZone zone, Transform mechanic, Dictionary<string, object> A)
        {
            var L = WorkshopLiftData();
            var park = UniqueChild(root.transform, "VanParkPoint (lift centre, nose to the back wall)");
            Vector3 parkLocal = L != null ? WsV3(WsObj(L, "placement"), "lift_centre") : WsV3(WsObj(A, "van_park_point"), "position");
            park.transform.localPosition = parkLocal;
            park.transform.localRotation = Quaternion.Euler(0f, WsNum(WsObj(A, "van_park_point") is Dictionary<string, object> vp && vp.TryGetValue("yaw", out var vy) ? vy : null, 180f), 0f);
            var cb = WsObj(L, "control_box");
            var control = UniqueChild(root.transform, "MechanicControlPoint (lift control box)");
            control.transform.localPosition = cb != null ? WsV3(cb, "interaction_point") : parkLocal + new Vector3(-2.55f, 0f, 0f);
            control.transform.localRotation = Quaternion.Euler(0f, WsNum(cb != null && cb.TryGetValue("interaction_yaw", out var iy) ? iy : null, 90f), 0f);

            var service = root.GetComponent<OnlyVolunteers.Economy.WorkshopServiceV01>();
            if (!service) service = root.AddComponent<OnlyVolunteers.Economy.WorkshopServiceV01>();
            service.Zone = zone;
            service.VanPark = park.transform;
            service.ControlPoint = control.transform;
            service.Mechanic = mechanic;
            var liftRoot = building ? building.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Workshop_W86_lift_v01") : null;
            var moving = liftRoot ? WsLiftMoving.Select(n => liftRoot.Cast<Transform>().FirstOrDefault(t => t.name == n)).Where(t => t).ToArray() : new Transform[0];
            var parts = WsObj(L, "moving_parts");
            var arms = moving.Where(t => t.name.StartsWith("Lift_Arms_")).ToArray();
            service.LiftParts = moving;
            service.LiftArms = arms;
            service.ArmEngagedYaw = arms.Select(a => WsNum(WsObj(parts, a.name) is Dictionary<string, object> pj && pj.TryGetValue("engaged_local_yaw", out var ey) ? ey : null)).ToArray();
            var travel = WsObj(L, "travel");
            service.LiftTravel = WsNum(travel != null && travel.TryGetValue("max", out var tm) ? tm : null, OnlyVolunteers.Economy.LiftSession.DefaultTravel);
            service.LiftSeconds = WsLiftSeconds;
            service.ArmSwingSeconds = WsArmSwingSeconds;
            EditorUtility.SetDirty(service);
            if (zone) { zone.LiftOnly = moving.Length > 0; EditorUtility.SetDirty(zone); }

            var talk = root.GetComponent<OnlyVolunteers.Economy.WorkshopMechanicV01>();
            if (!talk) talk = root.AddComponent<OnlyVolunteers.Economy.WorkshopMechanicV01>();
            talk.Spot = mechanic;
            EditorUtility.SetDirty(talk);
            Note(PlaceWorkshopMechanic(root)); // MECHANIC_W86 v01: model, route, brain (W85PlayIntegrator.Mechanic.cs)
            // checks: the van box on the park point is clear with the arms stowed, the control point stands on the floor
            Physics.SyncTransforms();
            Vector3 pc = park.transform.position;
            var hits = Physics.OverlapBox(pc + Vector3.up * 1.25f, new Vector3(1.0f, 1.0f, 2.6f), park.transform.rotation, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                .Where(c => c.gameObject.scene == root.scene && !(c is TerrainCollider) && c.transform.root.name != "Van").Select(c => PathOf(c.transform)).Distinct().ToList();
            return $"workshop lift: {(liftRoot ? liftRoot.name : "NO LIFT ART in the building instance")} - {moving.Length}/6 moving nodes, arms {string.Join(", ", arms.Select((a, i) => a.name + " " + service.ArmEngagedYaw[i].ToString("+0.0;-0.0", CultureInfo.InvariantCulture)))}, " +
                   $"travel {service.LiftTravel:0.##} m in {service.LiftSeconds:0.#} s (arms {service.ArmSwingSeconds:0.#} s); van park {F(pc)} yaw {park.transform.eulerAngles.y:0}, control box point {F(control.transform.position)}; " +
                   (hits.Count == 0 ? "van box (2.0 x 2.0 x 5.2 m, sills up) on the park point clear" : "WARNING van box hits: " + string.Join(", ", hits.Take(6))) +
                   $"; zone {(zone && zone.LiftOnly ? "lift-only" : "direct buying")}; mechanic WorkshopMechanicV01 at {F(mechanic.position)} (id {OnlyVolunteers.Economy.WorkshopMechanicV01.MechanicId})";
        }

        // ------------------------------------------------------------------ W86 workshop building (Workshop_W86_v01)
        public const string WorkshopBuildingName = "W86_Workshop_Building (Workshop_W86_v01)";
        public const string WorkshopArtDir = "Assets/OnlyVolunteers/Art/Buildings/Workshop_W86";
        public const string WorkshopPrefabPath = WorkshopArtDir + "/Workshop_W86_v01.prefab";
        const string WorkshopAnchorsJsonPath = WorkshopArtDir + "/Workshop_W86_anchors_v01.json";
        const string WorkshopMaterialsJsonPath = WorkshopArtDir + "/Workshop_W86_materials_v01.json";
        const string WorkshopGroundBackup = "workshop_W86_ground_backup_v01.bytes";
        /// <summary>Building root = floor level at the footprint centre, yaw about +Y (0 = doors facing +Z). Red mark 28.10: the
        /// meadow SE of the road hamlet_to_rough, doors and apron towards it (road axis ~25 m from the centre: a ~6.5 m gravel
        /// forecourt between the apron and the road edge). Floor 5.6 m: the road there lies at ~6.05, the meadow at 4.7-5.9.</summary>
        public static readonly Vector3 WorkshopPos = new(628.7f, 5.6f, 593.5f);
        public const float WorkshopYaw = -57.3f;
        /// <summary>true = the step also clears / re-seats the play scene's baked tall grass under the site (reversible through
        /// the backup). false = the grass file is left alone (blades then stand in the workshop).</summary>
        public static bool WorkshopClearGrass = true;
        /// <summary>True: ignore the old ground backup and take the CURRENT terrain (and grass) as the original - for a terrain /
        /// grass asset replaced from outside (e.g. Vadim's newer TerrainData): the fit is then made on his ground and a fresh
        /// backup written. False (default): the backup is restored first, but only where the terrain still holds exactly what
        /// the last fit wrote; anything else (a rebuilt or replaced terrain) is detected and the current ground is taken as
        /// original automatically.</summary>
        public static bool WorkshopRecaptureGround = false;
        const float WsStripIntensity = 6f, WsBulkheadIntensity = 3f, WsWallSpotIntensity = 20f, WsEmission = 2.5f;

        // site shapes in the building frame (x along the front, z out of the doors; metres)
        static readonly Rect WsBuildingRect = Rect.MinMaxRect(-12.3f, -6.7f, 12.3f, 6.02f);
        static readonly Rect WsApronRect = Rect.MinMaxRect(-16f, 6.02f, 16f, 15f);
        static readonly Vector2[] WsDrive = { new(-14f, 15f), new(6f, 15f), new(12f, 27f), new(-20f, 27f) };   // forecourt, clipped at the road
        static readonly Vector2[] WsPit = { new(-.5f, -1.65f), new(.5f, -1.65f), new(.5f, 3.45f), new(-.5f, 3.45f) };  // pit opening + 5 cm
        const float WsBlend = 6f, WsRoadKeep = .4f;
        static readonly string[] WsFbx = { "Workshop_W86_building_v01.fbx", "Workshop_W86_props_v01.fbx", "Workshop_W86_apron_v01.fbx", "Workshop_W86_westdoor_curtain_v01.fbx", "Workshop_W86_lift_v01.fbx" };
        /// <summary>The two-post lift over the pit (ArtSource/Buildings/Workshop_W86, red palette, Fedya 29.10): its data JSON
        /// (moving nodes, travel, arm swing, park point, control box) drives the prefab and WorkshopServiceV01.</summary>
        const string WorkshopLiftJsonPath = WorkshopArtDir + "/Workshop_W86_lift_v01.json";
        static readonly string[] WsLiftMoving = { "Lift_Carriage_L", "Lift_Carriage_R", "Lift_Arms_FL", "Lift_Arms_FR", "Lift_Arms_RL", "Lift_Arms_RR" };
        /// <summary>The lift's rise (Fedya's brief: about 4 s; the art JSON suggests 8 s, the brief wins) and the arm swing.</summary>
        const float WsLiftSeconds = 4f, WsArmSwingSeconds = 1.5f;

        static Dictionary<string, object> WorkshopLiftData() =>
            File.Exists(WorkshopLiftJsonPath) ? MiniJson.Parse(File.ReadAllText(WorkshopLiftJsonPath)) as Dictionary<string, object> : null;

        static Dictionary<string, object> WorkshopAnchorsData() =>
            File.Exists(WorkshopAnchorsJsonPath) ? MiniJson.Parse(File.ReadAllText(WorkshopAnchorsJsonPath)) as Dictionary<string, object> : null;
        static Dictionary<string, object> WsObj(Dictionary<string, object> d, string key) => d != null && d.TryGetValue(key, out var v) ? v as Dictionary<string, object> : null;
        static float WsNum(object o, float fallback = 0f) => o == null || o is string ? fallback : Convert.ToSingle(o, CultureInfo.InvariantCulture);
        static Vector3 WsV3(Dictionary<string, object> d, string key) =>
            d != null && d.TryGetValue(key, out var v) && v is List<object> l && l.Count >= 3 ? new Vector3(WsNum(l[0]), WsNum(l[1]), WsNum(l[2])) : Vector3.zero;

        /// <summary>Imports the workshop art (FBX importer settings + material remap), builds the URP Lit materials from
        /// Workshop_W86_materials_v01.json (matte: smoothness capped at .3 except glass / oil) and saves the prefab
        /// <see cref="WorkshopPrefabPath"/>: building (LODGroup LOD0 / LOD1) + props (per-prop LODGroup) + apron, UCX_ hulls as
        /// box / convex colliders without renderers, lights at the anchors JSON points, static flags like the map buildings.</summary>
        public static string BuildWorkshopPrefab()
        {
            var sb = new StringBuilder();
            if (EditorApplication.isPlaying) return "workshop prefab: leave Play mode first";
            var mats = WorkshopMaterials(sb);
            if (mats.Count == 0) return sb.Append("workshop prefab: no materials").ToString();
            foreach (string f in WsFbx)
            {
                string p = WorkshopArtDir + "/" + f;
                if (!(AssetImporter.GetAtPath(p) is ModelImporter mi)) { sb.AppendLine("missing: " + p); continue; }
                mi.globalScale = 1f; mi.useFileScale = true;
                mi.importAnimation = false; mi.animationType = ModelImporterAnimationType.None;
                mi.importCameras = false; mi.importLights = false; mi.importBlendShapes = false; mi.importVisibility = false;
                mi.isReadable = true; mi.addCollider = false; mi.generateSecondaryUV = false;
                mi.meshCompression = ModelImporterMeshCompression.Off;
                mi.importNormals = ModelImporterNormals.Import; mi.importTangents = ModelImporterTangents.CalculateMikk;
                mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
                foreach (var kv in mats) mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), kv.Key), kv.Value);
                mi.SaveAndReimport();
            }
            var anchors = WorkshopAnchorsData();
            var stage = EditorSceneManager.NewPreviewScene();
            try
            {
                var root = new GameObject("Workshop_W86_v01");
                SceneManager.MoveGameObjectToScene(root, stage);
                GameObject Inst(string f)
                {
                    var src = AssetDatabase.LoadAssetAtPath<GameObject>(WorkshopArtDir + "/" + f);
                    if (!src) return null;
                    var g = (GameObject)PrefabUtility.InstantiatePrefab(src, stage);
                    PrefabUtility.UnpackPrefabInstance(g, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                    g.transform.SetParent(root.transform, false);
                    g.transform.localPosition = Vector3.zero; g.transform.localRotation = Quaternion.identity; g.transform.localScale = Vector3.one;
                    return g;
                }
                var building = Inst(WsFbx[0]); var props = Inst(WsFbx[1]); var apron = Inst(WsFbx[2]);
                if (!building || !props || !apron) return sb.Append("workshop prefab: FBX missing").ToString();
                var lift = Inst(WsFbx[4]);   // optional: the prefab still builds without the lift art
                if (lift) lift.name = "Workshop_W86_lift_v01";
                foreach (var g in new[] { props, apron, lift }) { if (!g) continue; var imp = g.GetComponent<LODGroup>(); if (imp) Object.DestroyImmediate(imp); }   // the importer's file-level group would own the props' LODs

                // UCX_ hulls -> colliders (box when the hull is an axis-aligned box, else a convex mesh); no renderers
                int boxes = 0, hulls = 0;
                foreach (var t in root.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("UCX_")).ToList())
                {
                    var mf = t.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null;
                    var mr = t.GetComponent<MeshRenderer>(); if (mr) Object.DestroyImmediate(mr);
                    if (mesh)
                    {
                        if (IsBoxHull(mesh)) { var bc = t.gameObject.AddComponent<BoxCollider>(); bc.center = mesh.bounds.center; bc.size = mesh.bounds.size; boxes++; }
                        else { var mc = t.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mesh; mc.convex = true; hulls++; }
                    }
                    if (mf) Object.DestroyImmediate(mf);
                }

                // LODs: building LOD0 / LOD1 (shell + interior), large props LOD0 / LOD1, every prop culled when small on screen
                Renderer[] Rs(Transform p, string suffix) => p.GetComponentsInChildren<Renderer>(true).Where(r => r.name.EndsWith(suffix)).ToArray();
                var lg = building.GetComponent<LODGroup>(); if (!lg) lg = building.AddComponent<LODGroup>();   // the importer may add one (_LOD0 / _LOD1 names)
                lg.SetLODs(new[] { new LOD(.12f, Rs(building.transform, "_LOD0")), new LOD(.006f, Rs(building.transform, "_LOD1")) });
                lg.RecalculateBounds();
                int propLods = 0, propCull = 0;
                foreach (Transform h in lift ? props.transform.Cast<Transform>().Concat(lift.transform.Cast<Transform>()).ToList() : props.transform.Cast<Transform>().ToList())
                {
                    var r0 = Rs(h, "_LOD0"); var r1 = Rs(h, "_LOD1");
                    var plg = h.GetComponent<LODGroup>(); if (!plg) plg = h.gameObject.AddComponent<LODGroup>();
                    if (r0.Length > 0 && r1.Length > 0) { plg.SetLODs(new[] { new LOD(.15f, r0), new LOD(.025f, r1) }); propLods++; }
                    else { plg.SetLODs(new[] { new LOD(.012f, h.GetComponentsInChildren<Renderer>(true)) }); propCull++; }
                    plg.RecalculateBounds();
                }

                // lights at the anchors JSON points: ceiling strips + bulkhead (points), wall lamps (spots down); no shadows
                var lightsRoot = new GameObject("Lights").transform;
                lightsRoot.SetParent(root.transform, false);
                int nl = 0;
                foreach (var o in List(anchors, "lights").OfType<Dictionary<string, object>>())
                {
                    string name = Str(o, "name"), type = Str(o, "type");
                    var go = new GameObject(name);
                    go.transform.SetParent(lightsRoot, false);
                    go.transform.localPosition = WsV3(o, "position");
                    var l = go.AddComponent<Light>();
                    l.color = ColorUtility.TryParseHtmlString(Str(o, "colour"), out Color col) ? col : Color.white;
                    l.shadows = LightShadows.None;
                    var sug = WsObj(o, "suggested");
                    if (type.StartsWith("spot"))
                    {
                        l.type = LightType.Spot;
                        l.range = WsNum(sug != null && sug.TryGetValue("spot_range_m", out var sr) ? sr : null, 9f);
                        l.spotAngle = WsNum(sug != null && sug.TryGetValue("spot_angle_deg", out var sa) ? sa : null, 100f);
                        l.innerSpotAngle = l.spotAngle * .55f;
                        l.intensity = WsWallSpotIntensity;
                        go.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
                    }
                    else
                    {
                        l.type = LightType.Point;
                        l.range = WsNum(sug != null && sug.TryGetValue("point_range_m", out var pr) ? pr : null, 7f);
                        l.intensity = name.Contains("Bulkhead") ? WsBulkheadIntensity : WsStripIntensity;
                    }
                    nl++;
                }

                // static like the map buildings / props (W85Builder: batching + occludee; the shell also occluder); lights not
                const StaticEditorFlags prop = StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic;
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (!t.IsChildOf(lightsRoot)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, prop);
                // the lift's carriages and arms move (WorkshopServiceV01): never static, never batched
                int liftMoving = 0;
                if (lift)
                    foreach (Transform node in lift.transform)
                        if (WsLiftMoving.Contains(node.name))
                        {
                            foreach (var t in node.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, 0);
                            liftMoving++;
                        }
                foreach (var r in Rs(building.transform, "").Where(r => r.name.StartsWith("WS_Building_Shell")))
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject, prop | StaticEditorFlags.OccluderStatic);

                PrefabUtility.SaveAsPrefabAsset(root, WorkshopPrefabPath, out bool ok);
                sb.AppendLine($"workshop prefab {(ok ? "saved" : "FAILED")}: {WorkshopPrefabPath}; colliders {boxes} box + {hulls} convex (UCX_, renderers off); " +
                              $"LODGroups: building LOD0/LOD1, {propLods} props + lift parts LOD0/LOD1, {propCull} cull-only; {nl} lights; " +
                              (lift ? $"lift {lift.name}: {liftMoving}/6 moving nodes (not static)" : "no lift art (" + WsFbx[4] + " missing)"));
            }
            finally { EditorSceneManager.ClosePreviewScene(stage); }
            return sb.ToString();
        }

        static bool IsBoxHull(Mesh m)
        {
            var v = m.vertices; var b = m.bounds;
            var uniq = new HashSet<Vector3Int>();
            foreach (var p in v)
            {
                uniq.Add(Vector3Int.RoundToInt(p * 1000f));
                bool Edge(float x, float lo, float hi) => Mathf.Abs(x - lo) < 1e-3f || Mathf.Abs(x - hi) < 1e-3f;
                if (!Edge(p.x, b.min.x, b.max.x) || !Edge(p.y, b.min.y, b.max.y) || !Edge(p.z, b.min.z, b.max.z)) return false;
            }
            return uniq.Count == 8;
        }

        static Dictionary<string, Material> WorkshopMaterials(StringBuilder sb)
        {
            var res = new Dictionary<string, Material>();
            if (!File.Exists(WorkshopMaterialsJsonPath)) { sb.AppendLine("missing: " + WorkshopMaterialsJsonPath); return res; }
            var all = WsObj(MiniJson.Parse(File.ReadAllText(WorkshopMaterialsJsonPath)) as Dictionary<string, object>, "materials");
            if (all == null) { sb.AppendLine("no materials in " + WorkshopMaterialsJsonPath); return res; }
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            Folder(WorkshopArtDir + "/Materials");
            // the roller-door texture is new in this art set: repeating colour texture
            string doorTex = WorkshopArtDir + "/Workshop_rollerdoor_v01.png";
            if (AssetImporter.GetAtPath(doorTex) is TextureImporter ti && (ti.wrapMode != TextureWrapMode.Repeat || ti.anisoLevel != 4 || !ti.sRGBTexture))
            { ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.wrapMode = TextureWrapMode.Repeat; ti.mipmapEnabled = true; ti.anisoLevel = 4; ti.SaveAndReimport(); }
            foreach (var kv in all)
            {
                if (!(kv.Value is Dictionary<string, object> m)) continue;
                string key = kv.Key.StartsWith("MAT_WS_") ? kv.Key.Substring(7) : kv.Key;
                // the metals get own names so the W86 look's runtime "metal_dark" rule (smoothness .42 / metallic .55) keeps off them (matte)
                string asset = key == "metal_dark" ? "steel_dark" : key == "metal_worn" ? "steel_worn" : key;
                string path = $"{WorkshopArtDir}/Materials/WS86_{asset}_v01.mat";
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!mat) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, path); }
                if (mat.shader != shader) mat.shader = shader;
                string alb = m.TryGetValue("albedo", out var av) ? av as string : null;
                if (alb != null && alb.StartsWith("ArtSource/")) alb = WorkshopArtDir + "/" + Path.GetFileName(alb);
                var albT = alb != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(alb) : null;
                if (alb != null && !albT) sb.AppendLine("missing texture " + alb);
                mat.SetTexture("_BaseMap", albT);
                string nrm = m.TryGetValue("normal", out var nv) ? nv as string : null;
                var nrmT = nrm != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(nrm) : null;
                if (nrmT && AssetImporter.GetAtPath(nrm) is TextureImporter nti && nti.textureType != TextureImporterType.NormalMap) { sb.AppendLine("normal map not imported as NormalMap, skipped: " + nrm); nrmT = null; }
                mat.SetTexture("_BumpMap", nrmT);
                if (nrmT) { mat.EnableKeyword("_NORMALMAP"); mat.SetFloat("_BumpScale", 1f); } else mat.DisableKeyword("_NORMALMAP");
                float tiling = WsNum(m.TryGetValue("unity_tiling", out var tv) ? tv : null, 1f);
                mat.SetTextureScale("_BaseMap", new Vector2(tiling, tiling));
                mat.SetTextureOffset("_BaseMap", Vector2.zero);
                Color tint = ColorUtility.TryParseHtmlString(Str(m, "tint"), out Color tc) ? tc : Color.white;
                float alpha = m.TryGetValue("alpha", out var al) && al != null ? WsNum(al, 1f) : 1f;
                tint.a = alpha;
                mat.SetColor("_BaseColor", tint);
                // matte (lead 28.10): smoothness capped at .3 (glass and oil keep their sheen), painted metal and cladding barely metallic
                float smooth = WsNum(m.TryGetValue("smoothness", out var sv) ? sv : null, .2f), metal = WsNum(m.TryGetValue("metallic", out var mv) ? mv : null);
                bool painted = key == "red_steel" || key == "yellow_rail" || key.StartsWith("rollerdoor");
                smooth = key == "glass" ? smooth : key == "oil" ? Mathf.Min(smooth, .5f) : Mathf.Min(smooth, .3f);
                metal = painted || key == "corrugated_grey" ? Mathf.Min(metal, .1f) : Mathf.Min(metal, .35f);   // the cladding in shade otherwise mirrors the brown ground
                mat.SetFloat("_Smoothness", smooth);
                mat.SetFloat("_Metallic", metal);
                mat.SetFloat("_SmoothnessTextureChannel", 0f);
                string em = m.TryGetValue("emission", out var ev) ? ev as string : null;
                if (em != null && ColorUtility.TryParseHtmlString(em, out Color ec))
                { mat.EnableKeyword("_EMISSION"); mat.SetColor("_EmissionColor", ec * WsEmission); mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive; }
                else
                { mat.DisableKeyword("_EMISSION"); mat.SetColor("_EmissionColor", Color.black); mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack; }
                if (alpha < .99f)
                {
                    mat.SetFloat("_Surface", 1f); mat.SetFloat("_Blend", 0f); mat.SetOverrideTag("RenderType", "Transparent");
                    mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha); mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_SrcBlendAlpha", (float)UnityEngine.Rendering.BlendMode.One); mat.SetFloat("_DstBlendAlpha", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_ZWrite", 0f); mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
                }
                else
                {
                    mat.SetFloat("_Surface", 0f); mat.SetOverrideTag("RenderType", "Opaque");
                    mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.One); mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.Zero);
                    mat.SetFloat("_SrcBlendAlpha", (float)UnityEngine.Rendering.BlendMode.One); mat.SetFloat("_DstBlendAlpha", (float)UnityEngine.Rendering.BlendMode.Zero);
                    mat.SetFloat("_ZWrite", 1f); mat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.renderQueue = -1;
                }
                EditorUtility.SetDirty(mat);
                res[kv.Key] = mat;
            }
            AssetDatabase.SaveAssets();
            sb.AppendLine($"workshop materials: {res.Count} URP Lit in {WorkshopArtDir}/Materials");
            return res;
        }

        static GameObject PlaceWorkshopBuilding(Scene scene)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(WorkshopPrefabPath);
            // a prefab from before the lift art (or without it) is rebuilt once the lift FBX is there
            bool liftArt = File.Exists(WorkshopArtDir + "/" + WsFbx[4]);
            bool liftInPrefab = prefab && prefab.GetComponentsInChildren<Transform>(true).Any(t => t.name == "Workshop_W86_lift_v01");
            if (!prefab || liftArt && !liftInPrefab) { Note(BuildWorkshopPrefab()); prefab = AssetDatabase.LoadAssetAtPath<GameObject>(WorkshopPrefabPath); }
            if (!prefab) { Note("missing: " + WorkshopPrefabPath + " (workshop building not placed)"); return null; }
            GameObject go = null;
            int removed = 0;
            foreach (var g in scene.GetRootGameObjects().Where(g => g.name == WorkshopBuildingName).ToList())
            {
                bool mine = go == null && PrefabUtility.IsOutermostPrefabInstanceRoot(g) && PrefabUtility.GetCorrespondingObjectFromSource(g) == prefab;
                if (mine) go = g; else { Object.DestroyImmediate(g); removed++; }
            }
            bool reused = go != null;
            if (go) PrefabUtility.RevertPrefabInstance(go, InteractionMode.AutomatedAction);
            else
            {
                go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                if (go.transform.parent) go.transform.SetParent(null, true);
            }
            go.name = WorkshopBuildingName;
            go.transform.SetPositionAndRotation(WorkshopPos, Quaternion.Euler(0f, WorkshopYaw, 0f));
            go.transform.localScale = Vector3.one;
            EditorUtility.SetDirty(go);
            Note($"workshop building: {(reused ? "kept and reverted" : "placed")} {WorkshopBuildingName} ({WorkshopPrefabPath}) at {F(WorkshopPos)} yaw {WorkshopYaw:0.#}" + (removed > 0 ? $"; {removed} stale copy(ies) removed" : ""));
            return go;
        }

        // ---- ground fit: reversible local grading (backup beside the play scene) ----
        sealed class WsRoad { public Vector2[] Pts; public float Half; }
        sealed class WsBackup
        {
            public int Hx, Hz, Hw, Hh; public float[,] HOrig, HNew;
            public int Ax, Az, Aw, Ah, Al; public byte[] AOrig, ANew;
            public int Ox, Oz, Ow, Oh; public bool[,] Holes;
            public List<TreeInstance> Trees = new();
            public string GrassPath = "";
            public List<(int i, float oy, float oh, float ny, float nh)> Blades = new();
        }

        struct WsSite { public Vector2 L; public float DB, DA, DD, RE; public bool Same; }

        static List<WsRoad> WsRoads(string dataDir)
        {
            var res = new List<WsRoad>();
            string f = dataDir != null ? dataDir + "/roads_v85.json" : null;
            if (f == null || !File.Exists(f) || !(MiniJson.Parse(File.ReadAllText(f)) is Dictionary<string, object> rj)) return res;
            var c = new Vector2(WorkshopPos.x, WorkshopPos.z);
            foreach (var r in List(rj, "roads").OfType<Dictionary<string, object>>())
            {
                var pts = Pts(r.TryGetValue("points", out var p) ? p : null);
                if (pts.Length < 2 || DistToPolyline(pts, c, out _) > 150f) continue;
                res.Add(new WsRoad { Pts = pts, Half = WsNum(r.TryGetValue("width_m", out var w) ? w : null, 6.4f) * .5f });
            }
            return res;
        }

        static float WsSmooth(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }

        static float WsDistPoly(Vector2[] poly, Vector2 p)
        {
            if (InsidePoly(poly, p, 0f)) return 0f;
            float best = float.MaxValue;
            for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            {
                Vector2 a = poly[j], ab = poly[i] - a;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
                best = Mathf.Min(best, Vector2.Distance(p, a + ab * t));
            }
            return best;
        }

        static bool WsOverlap(Vector2[] a, Vector2[] b)
        {
            foreach (var poly in new[] { a, b })
                for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
                {
                    Vector2 e = poly[i] - poly[j], n = new(-e.y, e.x);
                    float amin = float.MaxValue, amax = float.MinValue, bmin = float.MaxValue, bmax = float.MinValue;
                    foreach (var p in a) { float d = Vector2.Dot(p, n); amin = Mathf.Min(amin, d); amax = Mathf.Max(amax, d); }
                    foreach (var p in b) { float d = Vector2.Dot(p, n); bmin = Mathf.Min(bmin, d); bmax = Mathf.Max(bmax, d); }
                    if (amax <= bmin || bmax <= amin) return false;
                }
            return true;
        }

        /// <summary>Fits the map terrain to the workshop: the footprint 0.30 m under the floor, the apron 0.05 m under its top,
        /// a gravel forecourt ramping from the apron to the road edge (the road band itself untouched), all blended into the
        /// original ground over 6 m; a terrain hole over the inspection pit; gravel / worn grass painted around; terrain trees
        /// under or against the building, apron and forecourt removed, the rest re-seated; the play scene's baked grass blades
        /// cleared there and re-seated where the ground moved. The previous fit is undone first from the backup
        /// (<see cref="WorkshopGroundBackup"/> beside the play scene) while the terrain still holds exactly what it wrote, so a
        /// rerun gives the same ground and a moved pose leaves nothing behind. The TerrainData is the map build's (shared with
        /// Map_W85_Build_v02): a full map rebuild resets it, the next run of this step fits it again.</summary>
        static string FitWorkshopGround(Scene scene, string dataDir)
        {
            var ter = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Terrain>(true)).FirstOrDefault(t => t.GetComponent<TerrainCollider>());
            if (!ter) return "workshop ground: missing the map terrain (not fitted)";
            if (string.IsNullOrEmpty(scene.path)) return "workshop ground: unsaved scene (no place for the backup; not fitted)";
            var td = ter.terrainData; Vector3 tp = ter.transform.position, size = td.size;
            string backup = scene.path.Substring(0, scene.path.Length - ".unity".Length) + "/" + WorkshopGroundBackup;
            var sb = new StringBuilder("workshop ground: ");
            var grass = WorkshopClearGrass ? scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<W85GrassRenderer>(true)).FirstOrDefault(g => g.data && g.data.instances) : null;
            string grassPath = grass ? AssetDatabase.GetAssetPath(grass.data.instances) : "";
            byte[] gb = grass && File.Exists(grassPath) ? File.ReadAllBytes(grassPath) : null;
            bool grassDirty = false;

            // 1. undo the previous fit (or, asked to recapture, take the current ground as the original)
            if (File.Exists(backup) && WorkshopRecaptureGround) sb.Append("backup ignored (WorkshopRecaptureGround): the current terrain and grass are the original; ");
            else if (File.Exists(backup)) sb.Append(WsRestore(ter, backup, grassPath, gb, ref grassDirty)).Append("; ");

            // 2. the site in the building frame
            float H = WorkshopPos.y;
            var rot = Quaternion.Euler(0f, WorkshopYaw, 0f); var inv = Quaternion.Inverse(rot);
            var c2 = new Vector2(WorkshopPos.x, WorkshopPos.z);
            Vector2 Loc(Vector2 w) { var l = inv * new Vector3(w.x - c2.x, 0f, w.y - c2.y); return new Vector2(l.x, l.z); }
            Vector2 Wld(Vector2 l) { var w = rot * new Vector3(l.x, 0f, l.y); return new Vector2(w.x + c2.x, w.z + c2.y); }
            var roads = WsRoads(dataDir);
            if (roads.Count == 0) sb.Append("WARNING no road data (road band not protected); ");
            WsSite Site(Vector2 w)
            {
                var s = new WsSite { L = Loc(w), RE = 999f, Same = true };
                foreach (var r in roads)
                {
                    float d = DistToPolyline(r.Pts, w, out var q) - r.Half;
                    if (d < s.RE) { s.RE = d; s.Same = Vector2.Dot(w - q, c2 - q) > 0f; }
                }
                s.DB = DistToRect(WsBuildingRect, s.L); s.DA = DistToRect(WsApronRect, s.L); s.DD = WsDistPoly(WsDrive, s.L);
                return s;
            }
            bool InDrive(in WsSite s) => s.DD <= 0f && s.Same && s.RE > WsRoadKeep;
            float Target(in WsSite s, float o, out float wgt)
            {
                float s0 = Mathf.Max(0f, s.L.y - WsApronRect.yMax), r0 = Mathf.Max(0f, s.RE - WsRoadKeep);
                float tt = s0 / (s0 + r0 + 1e-3f);
                float drive = Mathf.Lerp(H - .05f, o, Mathf.Lerp(tt, WsSmooth(tt), .5f));   // half eased: no steep middle on the ramp
                wgt = 1f;
                if (s.DB <= 0f) return H - .30f;            // under the floor (foundation band to -0.8 hides the edge)
                if (s.DA <= 0f) return H - .05f;            // under the apron top (bevel to -0.05, skirt to -0.6)
                if (InDrive(s)) return drive;               // forecourt: apron level -> the ground at the road edge
                float wB = 1f / (s.DB + .3f), wA = 1f / (s.DA + .3f), wD = 1f / (s.DD + .3f);
                float pad = H - (.18f * wB + .08f * wA) / (wB + wA);
                float d = Mathf.Min(Mathf.Min(s.DB, s.DA), s.DD);
                wgt = s.Same ? WsSmooth(1f - d / WsBlend) * WsSmooth((s.RE - WsRoadKeep) / 2f) : 0f;
                return (pad * (wB + wA) + drive * wD) / (wB + wA + wD);
            }
            float Gravel(in WsSite s)
            {
                if (!s.Same || s.RE < 0f) return 0f;
                if (s.DB <= 0f || s.DA <= 0f) return 1f;
                return Mathf.Max(1f - WsSmooth(s.DD / 1.5f), .8f * (1f - WsSmooth(Mathf.Min(s.DB, s.DA) / 2f)));
            }
            float Worn(in WsSite s, float g) => s.Same && s.RE >= 0f ? .45f * (1f - WsSmooth(Mathf.Min(Mathf.Min(s.DB, s.DA), s.DD) / 4.5f)) * (1f - g) : 0f;

            var lpts = new List<Vector2>();
            foreach (var r in new[] { WsBuildingRect, WsApronRect }) lpts.AddRange(new[] { new Vector2(r.xMin, r.yMin), new Vector2(r.xMax, r.yMin), new Vector2(r.xMin, r.yMax), new Vector2(r.xMax, r.yMax) });
            lpts.AddRange(WsDrive);
            (float x0, float z0, float x1, float z1) Box(float e)
            {
                var w = lpts.SelectMany(p => new[] { Wld(p + new Vector2(-e, -e)), Wld(p + new Vector2(e, -e)), Wld(p + new Vector2(-e, e)), Wld(p + new Vector2(e, e)) }).ToList();
                return (w.Min(p => p.x), w.Min(p => p.y), w.Max(p => p.x), w.Max(p => p.y));
            }
            var box = Box(WsBlend + 1.5f);
            var bk = new WsBackup { GrassPath = grassPath };

            // 3. heights
            int R = td.heightmapResolution; float hdx = size.x / (R - 1), hdz = size.z / (R - 1);
            bk.Hx = Mathf.Clamp(Mathf.FloorToInt((box.x0 - tp.x) / hdx), 0, R - 1); bk.Hz = Mathf.Clamp(Mathf.FloorToInt((box.z0 - tp.z) / hdz), 0, R - 1);
            bk.Hw = Mathf.Clamp(Mathf.CeilToInt((box.x1 - tp.x) / hdx), 0, R - 1) - bk.Hx + 1; bk.Hh = Mathf.Clamp(Mathf.CeilToInt((box.z1 - tp.z) / hdz), 0, R - 1) - bk.Hz + 1;
            bk.HOrig = td.GetHeights(bk.Hx, bk.Hz, bk.Hw, bk.Hh);
            var nh = new float[bk.Hh, bk.Hw];
            int moved = 0; float maxCut = 0f, maxFill = 0f;
            for (int j = 0; j < bk.Hh; j++)
                for (int i = 0; i < bk.Hw; i++)
                {
                    float o = bk.HOrig[j, i] * size.y + tp.y;
                    var s = Site(new Vector2(tp.x + (bk.Hx + i) * hdx, tp.z + (bk.Hz + j) * hdz));
                    float t = Target(s, o, out float wgt), v = Mathf.Lerp(o, t, wgt);
                    nh[j, i] = Mathf.Clamp01((v - tp.y) / size.y);
                    if (Mathf.Abs(v - o) > .01f) { moved++; maxCut = Mathf.Max(maxCut, o - v); maxFill = Mathf.Max(maxFill, v - o); }
                }
            td.SetHeights(bk.Hx, bk.Hz, nh);
            bk.HNew = td.GetHeights(bk.Hx, bk.Hz, bk.Hw, bk.Hh);
            float Delta(float x, float z)
            {
                float fx = Mathf.Clamp((x - tp.x) / hdx - bk.Hx, 0f, bk.Hw - 1.001f), fz = Mathf.Clamp((z - tp.z) / hdz - bk.Hz, 0f, bk.Hh - 1.001f);
                int i0 = (int)fx, j0 = (int)fz; float u = fx - i0, v = fz - j0;
                float D(int jj, int ii) => (bk.HNew[jj, ii] - bk.HOrig[jj, ii]) * size.y;
                return Mathf.Lerp(Mathf.Lerp(D(j0, i0), D(j0, i0 + 1), u), Mathf.Lerp(D(j0 + 1, i0), D(j0 + 1, i0 + 1), u), v);
            }

            // 4. pit hole (every terrain quad that overlaps the pit opening)
            int HR = td.holesResolution; float odx = size.x / HR, odz = size.z / HR;
            var pitW = WsPit.Select(Wld).ToArray();
            bk.Ox = Mathf.Clamp(Mathf.FloorToInt((pitW.Min(p => p.x) - tp.x) / odx) - 1, 0, HR - 1); bk.Oz = Mathf.Clamp(Mathf.FloorToInt((pitW.Min(p => p.y) - tp.z) / odz) - 1, 0, HR - 1);
            bk.Ow = Mathf.Clamp(Mathf.CeilToInt((pitW.Max(p => p.x) - tp.x) / odx) + 1, 0, HR - 1) - bk.Ox + 1; bk.Oh = Mathf.Clamp(Mathf.CeilToInt((pitW.Max(p => p.y) - tp.z) / odz) + 1, 0, HR - 1) - bk.Oz + 1;
            bk.Holes = td.GetHoles(bk.Ox, bk.Oz, bk.Ow, bk.Oh);
            var holes = (bool[,])bk.Holes.Clone();
            int cut = 0;
            for (int j = 0; j < bk.Oh; j++)
                for (int i = 0; i < bk.Ow; i++)
                {
                    float qx = tp.x + (bk.Ox + i) * odx, qz = tp.z + (bk.Oz + j) * odz;
                    var quad = new[] { new Vector2(qx, qz), new Vector2(qx + odx, qz), new Vector2(qx + odx, qz + odz), new Vector2(qx, qz + odz) };
                    if (WsOverlap(quad, pitW)) { if (holes[j, i]) cut++; holes[j, i] = false; }
                }
            td.SetHoles(bk.Ox, bk.Oz, holes);

            // 5. gravel forecourt / ring + worn grass (texels of the pad, forecourt and 5 m around)
            int AR = td.alphamapResolution, AL = td.alphamapLayers;
            int gl = Array.FindIndex(td.terrainLayers, t => t && t.name.ToLowerInvariant().Contains("gravel"));
            int wl = Array.FindIndex(td.terrainLayers, t => t && t.name.ToLowerInvariant().Contains("worn_grass"));
            int painted = 0;
            if (gl >= 0 && wl >= 0)
            {
                float adx = size.x / AR, adz = size.z / AR;
                var abox = Box(5f);
                bk.Ax = Mathf.Clamp(Mathf.FloorToInt((abox.x0 - tp.x) / adx), 0, AR - 1); bk.Az = Mathf.Clamp(Mathf.FloorToInt((abox.z0 - tp.z) / adz), 0, AR - 1);
                bk.Aw = Mathf.Clamp(Mathf.CeilToInt((abox.x1 - tp.x) / adx), 0, AR - 1) - bk.Ax + 1; bk.Ah = Mathf.Clamp(Mathf.CeilToInt((abox.z1 - tp.z) / adz), 0, AR - 1) - bk.Az + 1; bk.Al = AL;
                var a = td.GetAlphamaps(bk.Ax, bk.Az, bk.Aw, bk.Ah);
                bk.AOrig = WsPack(a);
                for (int j = 0; j < bk.Ah; j++)
                    for (int i = 0; i < bk.Aw; i++)
                    {
                        var s = Site(new Vector2(tp.x + (bk.Ax + i + .5f) * adx, tp.z + (bk.Az + j + .5f) * adz));
                        float g = Gravel(s), w = Worn(s, g);
                        if (g + w < .004f) continue;
                        float keep = 1f - g - w;
                        for (int l = 0; l < AL; l++) a[j, i, l] *= keep;
                        a[j, i, gl] += g; a[j, i, wl] += w;
                        painted++;
                    }
                td.SetAlphamaps(bk.Ax, bk.Az, a);
                bk.ANew = WsPack(td.GetAlphamaps(bk.Ax, bk.Az, bk.Aw, bk.Ah));
            }
            else sb.Append("WARNING no gravel / worn_grass terrain layer (not painted); ");

            // 6. terrain trees: off the building (+4.5 m), apron (+2 m) and forecourt (+2 m); the rest re-seated on the new ground
            var keepTrees = new List<TreeInstance>(td.treeInstanceCount); int seated = 0;
            foreach (var t0 in td.treeInstances)
            {
                var t = t0;
                float wx = t.position.x * size.x + tp.x, wz = t.position.z * size.z + tp.z;
                if (wx < box.x0 || wx > box.x1 || wz < box.z0 || wz > box.z1) { keepTrees.Add(t); continue; }
                var s = Site(new Vector2(wx, wz));
                if (s.DB < 4.5f || s.DA < 2f || (s.Same && s.RE > 0f && s.DD < 2f)) { bk.Trees.Add(t); continue; }
                float gy = td.GetInterpolatedHeight(t.position.x, t.position.z) / size.y;
                if (Mathf.Abs(gy - t.position.y) > 1e-6f) { t.position = new Vector3(t.position.x, gy, t.position.z); seated++; }
                keepTrees.Add(t);
            }
            if (bk.Trees.Count > 0 || seated > 0) td.SetTreeInstances(keepTrees.ToArray(), false);

            // 7. baked tall grass (the play scene's W85GrassRenderer data): cleared on the pad / forecourt / gravel, re-seated where the ground moved
            int gCleared = 0, gSeated = 0;
            if (gb != null)
            {
                foreach (var ch in grass.data.chunks)
                {
                    if (ch.centre.x + ch.extents.x < box.x0 || ch.centre.x - ch.extents.x > box.x1 || ch.centre.z + ch.extents.z < box.z0 || ch.centre.z - ch.extents.z > box.z1) continue;
                    for (uint k = ch.start; k < ch.start + ch.count && (k + 1) * 32 <= gb.Length; k++)
                    {
                        int off = (int)k * 32;
                        float x = BitConverter.ToSingle(gb, off), y = BitConverter.ToSingle(gb, off + 4), z = BitConverter.ToSingle(gb, off + 8), h = BitConverter.ToSingle(gb, off + 12);
                        if (x < box.x0 || x > box.x1 || z < box.z0 || z > box.z1 || h <= 0f) continue;
                        var s = Site(new Vector2(x, z));
                        float ny = y, nhh = h;
                        if (s.DB < .6f || s.DA < .6f || (s.Same && s.RE > -.2f && s.DD < .4f) || Gravel(s) > .45f) { nhh = 0f; gCleared++; }
                        else { float d = Delta(x, z); if (Mathf.Abs(d) > .005f) { ny = y + d; gSeated++; } }
                        if (ny == y && nhh == h) continue;
                        Buffer.BlockCopy(BitConverter.GetBytes(ny), 0, gb, off + 4, 4);
                        Buffer.BlockCopy(BitConverter.GetBytes(nhh), 0, gb, off + 12, 4);
                        bk.Blades.Add(((int)k, y, h, ny, nhh));
                        grassDirty = true;
                    }
                }
            }
            if (grassDirty) { File.WriteAllBytes(grassPath, gb); AssetDatabase.ImportAsset(grassPath, ImportAssetOptions.ForceUpdate); }

            EditorUtility.SetDirty(td);
            foreach (var tex in td.alphamapTextures) EditorUtility.SetDirty(tex);
            ter.Flush();
            Folder(Path.GetDirectoryName(backup).Replace('\\', '/'));
            WsWrite(backup, bk);
            AssetDatabase.ImportAsset(backup);
            sb.Append($"floor {H:0.00} m, {moved} height samples moved (cut <= {maxCut:0.00} m, fill <= {maxFill:0.00} m, blend {WsBlend:0} m, road band kept), " +
                      $"pit hole {cut} quad(s), {painted} texels gravel / worn grass, {bk.Trees.Count} tree(s) removed, {seated} re-seated, " +
                      (gb != null ? $"grass {gCleared} blade(s) cleared, {gSeated} re-seated ({grassPath})" : "grass untouched") + $"; backup {backup}");
            return sb.ToString();
        }

        static byte[] WsPack(float[,,] a)
        {
            int h = a.GetLength(0), w = a.GetLength(1), l = a.GetLength(2); var r = new byte[h * w * l]; int k = 0;
            for (int j = 0; j < h; j++) for (int i = 0; i < w; i++) for (int c = 0; c < l; c++) r[k++] = (byte)Mathf.Clamp(Mathf.RoundToInt(a[j, i, c] * 255f), 0, 255);
            return r;
        }

        static float[,,] WsUnpack(byte[] b, int h, int w, int l)
        {
            var r = new float[h, w, l]; int k = 0;
            for (int j = 0; j < h; j++) for (int i = 0; i < w; i++) for (int c = 0; c < l; c++) r[j, i, c] = b[k++] / 255f;
            return r;
        }

        static string WsRestore(Terrain ter, string path, string grassPath, byte[] gb, ref bool grassDirty)
        {
            var td = ter.terrainData; Vector3 tp = ter.transform.position, size = td.size;
            WsBackup bk;
            try { bk = WsRead(path); } catch (Exception e) { return "backup unreadable (" + e.Message + "), ignored"; }
            int R = td.heightmapResolution;
            if (bk.Hx + bk.Hw > R || bk.Hz + bk.Hh > R) return "backup does not fit this terrain, ignored";
            var cur = td.GetHeights(bk.Hx, bk.Hz, bk.Hw, bk.Hh);
            for (int j = 0; j < bk.Hh; j++)
                for (int i = 0; i < bk.Hw; i++)
                    if (Mathf.Abs(cur[j, i] - bk.HNew[j, i]) > 2e-6f) return "backup stale (the terrain changed since the last fit, e.g. a map rebuild): the current ground is taken as original";
            td.SetHeights(bk.Hx, bk.Hz, bk.HOrig);
            string alpha = "";
            if (bk.AOrig != null && bk.ANew != null && bk.Al == td.alphamapLayers)
            {
                var a = WsPack(td.GetAlphamaps(bk.Ax, bk.Az, bk.Aw, bk.Ah)); int diff = 0;
                for (int k = 0; k < a.Length; k++) if (Mathf.Abs(a[k] - bk.ANew[k]) > 1) diff++;
                if (diff == 0) td.SetAlphamaps(bk.Ax, bk.Az, WsUnpack(bk.AOrig, bk.Ah, bk.Aw, bk.Al)); else alpha = $", paint changed since ({diff} values): kept";
            }
            if (bk.Holes != null) td.SetHoles(bk.Ox, bk.Oz, bk.Holes);
            if (bk.Trees.Count > 0) td.SetTreeInstances(td.treeInstances.Concat(bk.Trees).ToArray(), false);
            // re-seat the trees of the old region on the restored ground
            float x0 = tp.x + bk.Hx * size.x / (R - 1), x1 = tp.x + (bk.Hx + bk.Hw) * size.x / (R - 1), z0 = tp.z + bk.Hz * size.z / (R - 1), z1 = tp.z + (bk.Hz + bk.Hh) * size.z / (R - 1);
            var trees = td.treeInstances; int seat = 0;
            for (int k = 0; k < trees.Length; k++)
            {
                float wx = trees[k].position.x * size.x + tp.x, wz = trees[k].position.z * size.z + tp.z;
                if (wx < x0 || wx > x1 || wz < z0 || wz > z1) continue;
                float gy = td.GetInterpolatedHeight(trees[k].position.x, trees[k].position.z) / size.y;
                if (Mathf.Abs(gy - trees[k].position.y) > 1e-6f) { trees[k].position = new Vector3(trees[k].position.x, gy, trees[k].position.z); seat++; }
            }
            if (seat > 0) td.SetTreeInstances(trees, false);
            int blades = 0;
            if (gb != null && bk.GrassPath == grassPath)
                foreach (var b in bk.Blades)
                {
                    int off = b.i * 32; if (off + 32 > gb.Length) continue;
                    float y = BitConverter.ToSingle(gb, off + 4), h = BitConverter.ToSingle(gb, off + 12);
                    if (y != b.ny || h != b.nh) continue;
                    Buffer.BlockCopy(BitConverter.GetBytes(b.oy), 0, gb, off + 4, 4);
                    Buffer.BlockCopy(BitConverter.GetBytes(b.oh), 0, gb, off + 12, 4);
                    blades++;
                }
            grassDirty |= blades > 0;
            return $"previous fit undone ({bk.Hw} x {bk.Hh} heights, {bk.Trees.Count} trees back, {blades} grass blades{alpha})";
        }

        static void WsWrite(string path, WsBackup b)
        {
            using var w = new BinaryWriter(File.Create(path));
            w.Write("WSG1");
            w.Write(b.Hx); w.Write(b.Hz); w.Write(b.Hw); w.Write(b.Hh);
            for (int j = 0; j < b.Hh; j++) for (int i = 0; i < b.Hw; i++) { w.Write(b.HOrig[j, i]); w.Write(b.HNew[j, i]); }
            w.Write(b.Ax); w.Write(b.Az); w.Write(b.Aw); w.Write(b.Ah); w.Write(b.Al);
            w.Write(b.AOrig?.Length ?? 0); if (b.AOrig != null) { w.Write(b.AOrig); w.Write(b.ANew); }
            w.Write(b.Ox); w.Write(b.Oz); w.Write(b.Ow); w.Write(b.Oh);
            for (int j = 0; j < b.Oh; j++) for (int i = 0; i < b.Ow; i++) w.Write(b.Holes[j, i]);
            w.Write(b.Trees.Count);
            foreach (var t in b.Trees)
            {
                w.Write(t.position.x); w.Write(t.position.y); w.Write(t.position.z); w.Write(t.widthScale); w.Write(t.heightScale); w.Write(t.rotation);
                w.Write(t.color.r); w.Write(t.color.g); w.Write(t.color.b); w.Write(t.color.a);
                w.Write(t.lightmapColor.r); w.Write(t.lightmapColor.g); w.Write(t.lightmapColor.b); w.Write(t.lightmapColor.a); w.Write(t.prototypeIndex);
            }
            w.Write(b.GrassPath ?? ""); w.Write(b.Blades.Count);
            foreach (var x in b.Blades) { w.Write(x.i); w.Write(x.oy); w.Write(x.oh); w.Write(x.ny); w.Write(x.nh); }
        }

        static WsBackup WsRead(string path)
        {
            using var r = new BinaryReader(File.OpenRead(path));
            if (r.ReadString() != "WSG1") throw new InvalidDataException("not a workshop ground backup");
            var b = new WsBackup { Hx = r.ReadInt32(), Hz = r.ReadInt32(), Hw = r.ReadInt32(), Hh = r.ReadInt32() };
            b.HOrig = new float[b.Hh, b.Hw]; b.HNew = new float[b.Hh, b.Hw];
            for (int j = 0; j < b.Hh; j++) for (int i = 0; i < b.Hw; i++) { b.HOrig[j, i] = r.ReadSingle(); b.HNew[j, i] = r.ReadSingle(); }
            b.Ax = r.ReadInt32(); b.Az = r.ReadInt32(); b.Aw = r.ReadInt32(); b.Ah = r.ReadInt32(); b.Al = r.ReadInt32();
            int an = r.ReadInt32(); if (an > 0) { b.AOrig = r.ReadBytes(an); b.ANew = r.ReadBytes(an); }
            b.Ox = r.ReadInt32(); b.Oz = r.ReadInt32(); b.Ow = r.ReadInt32(); b.Oh = r.ReadInt32();
            b.Holes = new bool[b.Oh, b.Ow];
            for (int j = 0; j < b.Oh; j++) for (int i = 0; i < b.Ow; i++) b.Holes[j, i] = r.ReadBoolean();
            int nt = r.ReadInt32();
            for (int k = 0; k < nt; k++)
                b.Trees.Add(new TreeInstance
                {
                    position = new Vector3(r.ReadSingle(), r.ReadSingle(), r.ReadSingle()), widthScale = r.ReadSingle(), heightScale = r.ReadSingle(), rotation = r.ReadSingle(),
                    color = new Color32(r.ReadByte(), r.ReadByte(), r.ReadByte(), r.ReadByte()), lightmapColor = new Color32(r.ReadByte(), r.ReadByte(), r.ReadByte(), r.ReadByte()), prototypeIndex = r.ReadInt32(),
                });
            b.GrassPath = r.ReadString();
            int nb = r.ReadInt32();
            for (int k = 0; k < nb; k++) b.Blades.Add((r.ReadInt32(), r.ReadSingle(), r.ReadSingle(), r.ReadSingle(), r.ReadSingle()));
            return b;
        }

        static string Inside(Scene scene, Vector3 c, Quaternion r, Vector3 size) => string.Join(", ",
            Physics.OverlapBox(c + Vector3.up * (size.y * .5f + .3f), new Vector3(size.x * .5f, size.y * .5f, size.z * .5f), r, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                .Where(x => x.gameObject.scene == scene && !(x is TerrainCollider) && x.transform.root.name != "Van").Select(x => PathOf(x.transform)).Distinct());

        static string Spread(Scene scene, Vector3 c, Quaternion r, Vector3 size, Func<float, float, float> ground)
        {
            float lo = float.MaxValue, hi = float.MinValue;
            for (int k = 0; k < 4; k++)
            {
                Vector3 q = c + r * new Vector3(((k & 1) == 0 ? -.5f : .5f) * size.x, 0f, ((k & 2) == 0 ? -.5f : .5f) * size.z);
                float y = GroundRay(scene, q.x, q.z, ground);
                lo = Mathf.Min(lo, y - c.y); hi = Mathf.Max(hi, y - c.y);
            }
            return $"{lo:+0.00;-0.00}..{hi:+0.00;-0.00} m";
        }

        static GameObject UniqueRoot(Scene scene, string name)
        {
            var found = scene.GetRootGameObjects().Where(g => g.name == name).ToList();
            foreach (var extra in found.Skip(1)) Object.DestroyImmediate(extra);
            GameObject go = found.FirstOrDefault();
            if (!go) { go = new GameObject(name); SceneManager.MoveGameObjectToScene(go, scene); }
            return go;
        }

        static GameObject UniqueChild(Transform parent, string name)
        {
            var found = parent.Cast<Transform>().Where(t => t.name == name).Select(t => t.gameObject).ToList();
            foreach (var extra in found.Skip(1)) Object.DestroyImmediate(extra);
            GameObject go = found.FirstOrDefault();
            if (!go) { go = new GameObject(name); go.transform.SetParent(parent, false); }
            return go;
        }

        static OnlyVolunteers.Story.StoryAnchor Anchor(Transform parent, string name, string id, string title, Vector3 local, Vector3 size, bool markers, Color color)
        {
            GameObject go = UniqueChild(parent, name);
            go.transform.localPosition = local;
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale = Vector3.one;
            var a = go.GetComponent<OnlyVolunteers.Story.StoryAnchor>();
            if (!a) a = go.AddComponent<OnlyVolunteers.Story.StoryAnchor>();
            a.Id = id; a.Title = title; a.Size = size; a.ShowMarkers = markers; a.MarkerColor = color;
            EditorUtility.SetDirty(a);
            EditorUtility.SetDirty(go);
            return a;
        }

        static OnlyVolunteers.Story.StoryAnchor WorldAnchor(Scene scene, Transform parent, string name, string id, string title, Vector2 at, float yaw, bool markers, Color color, Func<float, float, float> ground)
        {
            var a = Anchor(parent, name, id, title, Vector3.zero, Vector3.zero, markers, color);
            a.transform.SetPositionAndRotation(new Vector3(at.x, GroundRay(scene, at.x, at.y, ground), at.y), Quaternion.Euler(0f, yaw, 0f));
            return a;
        }

        /// <summary>Ground under a plan point by a downward ray: the terrain hit, raised to a wide flat surface outside
        /// buildings lying on it (a yard / pad / road, at most 0.5 m above the terrain; roofs, vehicles and props do not
        /// count); the ground sampler when the ray meets no terrain.</summary>
        static float GroundRay(Scene scene, float x, float z, Func<float, float, float> fallback)
        {
            var hits = Physics.RaycastAll(new Vector3(x, 400f, z), Vector3.down, 800f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                .Where(h => h.collider.gameObject.scene == scene).ToArray();
            var terrainHits = hits.Where(h => h.collider is TerrainCollider).ToArray();
            if (terrainHits.Length == 0) return fallback(x, z);
            float best = terrainHits.Max(h => h.point.y), terrainY = best;
            foreach (var h in hits)
            {
                var c = h.collider;
                if (c is TerrainCollider || h.normal.y < .7f || h.point.y <= best || h.point.y > terrainY + .5f) continue;
                if (InBuilding(c.transform) || Mathf.Max(c.bounds.size.x, c.bounds.size.z) < 2f || c.transform.root.name == "Van") continue;
                best = h.point.y;
            }
            return best;
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
