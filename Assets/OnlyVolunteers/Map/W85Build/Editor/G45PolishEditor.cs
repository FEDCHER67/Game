// G45 bounded import, partial rebuild and evidence. No global look or player edits.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;
using OnlyVolunteers.Map.W76;
using OnlyVolunteers.Map.Look.V3;
using Object = UnityEngine.Object;
namespace OnlyVolunteers.Map.W85
{
    public static partial class W85Builder
    {
        const string G45Dir = "C:/Dev/Game/Working/Reviews/W86Polish_2026-10-25/G45";
        const string G45Trees = "Assets/OnlyVolunteers/Art/Trees/Conifers_v04_03";
        static void G45Guard()
        {
            var path = UnityEngine.SceneManagement.SceneManager.GetActiveScene().path;
            if (EditorApplication.isPlaying || EditorApplication.isCompiling || path != "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity")
                throw new InvalidOperationException("G45 requires stopped, compiled Map_W85_Play_v02");
            SetVersion("v02");
            Ter = Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None).Single(t => t.name == "Terrain_W85_v02");
        }
        [MenuItem("OnlyVolunteers/Map/G45/1 Import conifers v04_03")]
        public static void G45ImportConifers()
        {
            G45Guard(); Folder(G45Trees + "/Materials"); Folder(G45Trees + "/Prefabs"); Folder(G45Trees + "/Meshes");
            var mats = new Dictionary<string, Material>();
            foreach (var pair in new[] { ("Bark", "Bark"), ("LeafDark", "LeafDark"), ("LeafPine", "LeafPine") })
            {
                string path = G45Trees + "/Materials/G45_" + pair.Item1 + "_Wind_v04_03.mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m)
                {
                    var src = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Materials/Pine_" + pair.Item2 + "_Wind_v01.mat");
                    if (!src) throw new InvalidOperationException("Missing approved wind material");
                    m = new Material(src) { name = "G45_" + pair.Item1 + "_Wind_v04_03", enableInstancing = true };
                    m.SetFloat("_FlexibleHeight", 9f); AssetDatabase.CreateAsset(m, path);
                }
                mats["G45_" + pair.Item1] = m;
            }
            string[] names = { "Spruce_A", "Spruce_B", "Fir", "Young" };
            float[] radii = { .264f, .284f, .254f, .184f }, heights = { 3.2f, 3.2f, 3.15f, 2.52f };
            var evidence = new List<string>();
            for (int i = 0; i < names.Length; i++)
            {
                string id = "Forest_" + names[i] + "_v04_03";
                string modelPath = G45Trees + "/Models/" + id + ".fbx";
                var importer = AssetImporter.GetAtPath(modelPath) as ModelImporter;
                if (!importer) throw new InvalidOperationException("Missing FBX " + modelPath);
                importer.materialImportMode = ModelImporterMaterialImportMode.None; importer.isReadable = true;
                importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
                importer.SaveAndReimport();
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
                var root = new GameObject(id + "_Wind");
                try
                {
                    var lods = new LOD[3];
                    for (int l = 0; l < 3; l++)
                    {
                        var source = model.GetComponentsInChildren<MeshFilter>(true).Single(f => f.name.EndsWith("LOD" + l, StringComparison.Ordinal));
                        var go = new GameObject("LOD" + l); go.transform.SetParent(root.transform, false);
                        var axis = model.transform.worldToLocalMatrix * source.transform.localToWorldMatrix;
                        var mesh = Object.Instantiate(source.sharedMesh); mesh.name = id + "_LOD" + l;
                        mesh.vertices = mesh.vertices.Select(axis.MultiplyPoint3x4).ToArray();
                        mesh.normals = mesh.normals.Select(n => axis.MultiplyVector(n).normalized).ToArray();
                        mesh.RecalculateBounds(); mesh.RecalculateTangents();
                        string meshPath = G45Trees + "/Meshes/" + mesh.name + ".asset";
                        var stored = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
                        if (stored) { EditorUtility.CopySerialized(mesh, stored); Object.DestroyImmediate(mesh); mesh = stored; EditorUtility.SetDirty(mesh); }
                        else AssetDatabase.CreateAsset(mesh, meshPath);
                        AssetDatabase.SaveAssetIfDirty(mesh);
                        go.AddComponent<MeshFilter>().sharedMesh = mesh;
                        var renderer = go.AddComponent<MeshRenderer>();
                        // Mesh helper exports materials in Bark, LeafDark, LeafPine order.
                        renderer.sharedMaterials = new[] { mats["G45_Bark"], mats["G45_LeafDark"], mats["G45_LeafPine"] };
                        renderer.shadowCastingMode = l == 2 ? ShadowCastingMode.Off : ShadowCastingMode.On;
                        renderer.receiveShadows = true; renderer.motionVectorGenerationMode = MotionVectorGenerationMode.Object;
                        lods[l] = new LOD(new[] { .328f, .1184f, .018f }[l], new Renderer[] { renderer });
                        evidence.Add(id + "|" + l + "|" + mesh.triangles.Length / 3 + "|" + mesh.bounds);
                        if (mesh.bounds.min.y < -.01f || mesh.bounds.min.y > .01f) throw new Exception("Ungrounded root");
                    }
                    var capsule = root.AddComponent<CapsuleCollider>(); capsule.radius = radii[i]; capsule.height = heights[i]; capsule.center = new Vector3(0, heights[i] / 2f, 0);
                    var group = root.AddComponent<LODGroup>(); group.SetLODs(lods); group.RecalculateBounds();
                    PrefabUtility.SaveAsPrefabAsset(root, G45Trees + "/Prefabs/" + id + "_Wind.prefab");
                }
                finally { Object.DestroyImmediate(root); }
            }
            File.WriteAllLines(G45Dir + "/unity_conifers_v04_03.tsv", evidence);
        }
        [MenuItem("OnlyVolunteers/Map/G45/2 Rebuild vegetation only")]
        public static void G45RebuildTrees()
        {
            G45Guard(); Trees(Ter.terrainData); EditorUtility.SetDirty(Ter.terrainData); AssetDatabase.SaveAssetIfDirty(Ter.terrainData); Ter.Flush();
        }
        [MenuItem("OnlyVolunteers/Map/G45/3 Rebuild casino and access only")]
        public static void G45RebuildCasino()
        {
            G45Guard();
            var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            var parent = GameObject.Find("District_quiet_valley").transform;
            var dj = Obj(Json.Parse(File.ReadAllText(Data + "/districts/quiet_valley_v85.json")));
            Gen = Root + "/Generated/v02_G45"; Folder(Gen + "/Meshes"); Folder(Gen + "/Materials"); Folder(Gen + "/Textures");
            Log.Clear(); Mats.Clear(); SlotMats.Clear(); MatTile.Clear(); Built.Clear();
            var mj = Obj(Json.Parse(File.ReadAllText(Data + "/materials_v85.json")));
            MatMap = Obj(Get(mj, "materials")); Slots = Obj(Get(mj, "slots"));
            Sample = LoadSample(); LoadSampleRules(); RolloutInit(); W86Init(); W86RolloutInit();
            var old = parent.Find("B_08_03_casino"); if (!old) throw new Exception("Casino missing"); Object.DestroyImmediate(old.gameObject);
            var casino = Arr(Get(dj, "buildings")).Select(Obj).Single(b => S(Get(b, "id")) == "08_03_casino");
            if (!Building(parent, casino, "quiet_valley")) throw new Exception("Casino rebuild failed");
            foreach (string id in new[] { "08-casino-forecourt", "08-casino-parking-north-link" })
            {
                var zone = Arr(Get(dj, "zones")).Select(Obj).Single(z => S(Get(z, "id")) == id);
                var previous = parent.Find("Zone_" + id); if (previous) Object.DestroyImmediate(previous.gameObject);
                if (!Zone(parent, zone)) throw new Exception("Access surface missing " + id);
            }
            var touched = new List<string>();
            // Trim only the old casino stall/oil triangles; preserve every other marking in shared chunks.
            var hooks = GameObject.Find("Map_W85_v02").transform.Find("DecalHooks_W86");
            foreach (var mf in hooks.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!(mf.name.Contains(GM) || mf.name.Contains(GO))) continue;
                var mesh = mf.sharedMesh; var vertices = mesh.vertices; var indices = mesh.triangles; var kept = new List<int>(); bool changed = false;
                for (int n = 0; n < indices.Length; n += 3)
                {
                    Vector3 c = mf.transform.TransformPoint((vertices[indices[n]] + vertices[indices[n + 1]] + vertices[indices[n + 2]]) / 3f);
                    if (c.x >= 506.3f && c.x <= 516.9f && c.z >= 151f && c.z <= 172.2f) { changed = true; continue; }
                    kept.Add(indices[n]); kept.Add(indices[n + 1]); kept.Add(indices[n + 2]);
                }
                if (changed) { touched.Add(AssetDatabase.GetAssetPath(mesh)); mesh.SetTriangles(kept, 0); mesh.RecalculateBounds(); EditorUtility.SetDirty(mesh); AssetDatabase.SaveAssetIfDirty(mesh); }
            }
            var owned = hooks.Find("G45_CasinoParking"); if (owned) Object.DestroyImmediate(owned.gameObject);
            owned = new GameObject("G45_CasinoParking").transform; owned.SetParent(hooks, false);
            DMats.Clear(); DBat.Clear(); DGrp.Clear(); DCnt.Clear(); DSurf.Clear(); DFoot.Clear();
            DGroupMake(owned, GM, 128f, 0, "G45 casino stalls, north aisle clear"); DGroupMake(owned, GO, 64f, 150f, "G45 casino oil");
            foreach (var c in parent.GetComponentsInChildren<Collider>(true)) if (c.name.StartsWith("Zone_")) DSurf.Add(c);
            DFoot.Add(V2s(Get(casino, "footprint"))); Physics.SyncTransforms();
            var parking = Arr(Get(dj, "zones")).Select(Obj).Single(z => S(Get(z, "id")) == "08-casino-parking");
            DParking(new List<Dictionary<string, object>> { new() { ["zones"] = new List<object> { parking } } }); DFlush();
            // Scoped saves; never save unrelated dirty assets.
            foreach (string guid in AssetDatabase.FindAssets("", new[] { Gen }))
            { var asset = AssetDatabase.LoadMainAssetAtPath(AssetDatabase.GUIDToAssetPath(guid)); if (asset) AssetDatabase.SaveAssetIfDirty(asset); }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            touched.AddRange(AssetDatabase.FindAssets("", new[] { Gen }).Select(AssetDatabase.GUIDToAssetPath));
            touched.Add(scene.path); File.WriteAllLines(G45Dir + "/casino_assets_touched_v01.txt", touched.Distinct().OrderBy(p => p));
            File.WriteAllText(G45Dir + "/casino_partial_build_v01.log", Log.ToString()); SetVersion("v02");
        }
        public static void G45Snapshot(string label)
        {
            G45Guard(); var ci = System.Globalization.CultureInfo.InvariantCulture; var td = Ter.terrainData;
            File.WriteAllLines(G45Dir + "/trees_" + label + ".tsv", td.treeInstances.Select(t => string.Join("|", new[] { t.position.x.ToString("R", ci), t.position.y.ToString("R", ci), t.position.z.ToString("R", ci), t.widthScale.ToString("R", ci), t.heightScale.ToString("R", ci), t.rotation.ToString("R", ci), AssetDatabase.GetAssetPath(td.treePrototypes[t.prototypeIndex].prefab) })));
            var weather = Object.FindObjectsByType<DistrictAtmosphere19>(FindObjectsSortMode.None).First();
            File.WriteAllLines(G45Dir + "/districts_" + label + ".tsv", weather.districts.Select(d => d.id + "|" + d.bounds.x.ToString(ci) + "|" + d.bounds.y.ToString(ci) + "|" + d.bounds.z.ToString(ci) + "|" + d.bounds.w.ToString(ci)));
            var lab = GameObject.Find("B_08_01_lab");
            File.WriteAllLines(G45Dir + "/lab_" + label + ".tsv", lab.GetComponentsInChildren<Transform>(true).Select(x => x.name + "|" + x.position.ToString("F6") + "|" + x.rotation.ToString("F6") + "|" + x.localScale.ToString("F6")));
        }

        // Identical transient observer camera in Play; original player/camera settings are never saved.
        static bool G45PerfBusy;
        public static void G45Performance(string label)
        {
            if (G45PerfBusy) return;
            G45PerfBusy = true;
            File.AppendAllText(G45Dir + "/perf_invocations_v01.log", DateTime.UtcNow.ToString("o") + " " + label + "\n");
            if (!EditorApplication.isPlaying) throw new Exception("Performance probe requires Play");
            var terrain = Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None).Single(t => t.name == "Terrain_W85_v02");
            var original = Camera.main; bool enabled = original && original.enabled;
            var go = new GameObject("G45 temporary performance camera") { hideFlags = HideFlags.HideAndDontSave };
            var cam = go.AddComponent<Camera>(); if (original) cam.CopyFrom(original);
            cam.enabled = true; cam.fieldOfView = 65; cam.farClipPlane = 1200;
            var data = go.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
            var rt = new RenderTexture(1280, 720, 24); cam.targetTexture = rt;
            if (original) original.enabled = false;
            int view = 0, count = 0, lastFrame = -1;
            var samples = new List<float>(); var result = new List<string>();
            void Place()
            {
                Vector3 p = view == 0 ? new Vector3(312, 0, 170) : new Vector3(370, 0, 272);
                p.y = terrain.SampleHeight(p) + terrain.transform.position.y + 1.65f;
                cam.transform.SetPositionAndRotation(p, Quaternion.Euler(2, view == 0 ? 45 : 225, 0));
            }
            void Image()
            {
                var active = RenderTexture.active; RenderTexture.active = rt;
                var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0); tex.Apply();
                File.WriteAllBytes(G45Dir + "/forest_play_view" + (view + 1) + "_" + label + ".png", tex.EncodeToPNG());
                Object.Destroy(tex); RenderTexture.active = active;
            }
            EditorApplication.CallbackFunction tick = null;
            tick = () =>
            {
                if (!EditorApplication.isPlaying) { EditorApplication.update -= tick; G45PerfBusy = false; return; }
                if (lastFrame == Time.frameCount) return; lastFrame = Time.frameCount;
                count++;
                if (count > 60) samples.Add(Time.unscaledDeltaTime);
                if (count < 240) return;
                result.Add(view + "|" + (1f / samples.Average()).ToString("F2", System.Globalization.CultureInfo.InvariantCulture) + "|" + (samples.Average() * 1000).ToString("F3", System.Globalization.CultureInfo.InvariantCulture));
                Image(); view++; count = 0; samples.Clear();
                if (view < 2) { Place(); return; }
                EditorApplication.update -= tick; G45PerfBusy = false; if (original) original.enabled = enabled;
                cam.targetTexture = null; Object.Destroy(go); rt.Release(); Object.Destroy(rt);
                File.WriteAllLines(G45Dir + "/fps_" + label + ".tsv", result);
                Debug.Log("G45 PERFORMANCE " + label + " " + string.Join(";", result));
            };
            Place(); EditorApplication.update += tick;
        }

        public static void G45DriveAndWalk()
        {
            if (!EditorApplication.isPlaying) throw new Exception("G45 access test requires Play");
            var terrain = Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None).Single(t => t.name == "Terrain_W85_v02");
            float Ground(float x, float z) => terrain.SampleHeight(new Vector3(x, 0, z)) + terrain.transform.position.y;
            var van = Object.FindObjectsByType<OnlyVolunteers.Vehicles.VanController>(FindObjectsSortMode.None).Single(v => v.gameObject.name == "Van");
            var upgrade = van.GetComponent<OnlyVolunteers.Vehicles.VanUpgrades>();
            if (!upgrade || !upgrade.StartAtMax || Enum.GetValues(typeof(OnlyVolunteers.Vehicles.VanUpgradeCategory)).Cast<OnlyVolunteers.Vehicles.VanUpgradeCategory>().Any(c => upgrade.GetLevel(c) != 3)) throw new Exception("Van is not at max upgrades");
            var driver = van.GetComponent<OnlyVolunteers.Vehicles.VanDriveInput>(); if (driver) driver.enabled = false;
            var body = van.GetComponent<Rigidbody>(); van.enabled = true; body.isKinematic = false;
            body.position = new Vector3(543.5f, Ground(543.5f, 275) + .12f, 275); body.rotation = Quaternion.Euler(0, 183, 0); body.linearVelocity = Vector3.zero; body.angularVelocity = Vector3.zero;
            var character = Object.FindObjectsByType<KinematicCharacterController.Examples.ExampleCharacterController>(FindObjectsSortMode.None).First(c => c.transform.root.name == "Player_KCC");
            var input = Object.FindObjectsByType<OnlyVolunteers.Player.KccFirstPersonInput>(FindObjectsSortMode.None).FirstOrDefault(i => i.Character == character); if (input) input.enabled = false;
            var motor = character.Motor;
            Vector2[] route = { new(542.4f, 250), new(544.4f,228.8f), new(550.6f,211.8f), new(558.46f,195.72f), new(564.24f,183.8f), new(565.5f,178), new(561,174), new(550,174), new(539,174), new(526,174), new(515,174), new(509,173), new(509,163) };
            Vector2[] walk = { new(559,174), new(549,174), new(538.4f,174), new(538.4f,170), new(538.4f,168.5f) };
            var log = new List<string> { "Van: max Engine/Brakes/Handling=3; real WheelColliders/VanController; throttle/steer supplied through existing input API", "Player capsule height=" + motor.Capsule.height };
            int phase = 0, point = 0, lastFrame = -1; float started = Time.realtimeSinceStartup, lastProgress = started, best = float.MaxValue;
            EditorApplication.CallbackFunction tick = null;
            void Finish(string result)
            {
                van.Throttle = 0; van.Steer = 0; van.Handbrake = true;
                var ai = new KinematicCharacterController.Examples.AICharacterInputs { MoveVector = Vector3.zero, LookVector = Vector3.forward }; character.SetInputs(ref ai);
                EditorApplication.update -= tick; log.Add(result); File.WriteAllLines(G45Dir + "/access_play_v01.tsv", log); Debug.Log("G45 ACCESS " + result);
            }
            tick = () =>
            {
                if (!EditorApplication.isPlaying) { EditorApplication.update -= tick; return; }
                if (lastFrame == Time.frameCount) return; lastFrame = Time.frameCount;
                if (Time.realtimeSinceStartup - started > 180) { Finish("FAIL: 180 second time limit"); return; }
                Vector2 target = phase == 0 ? route[point] : walk[point]; Vector3 current = phase == 0 ? body.position : motor.TransientPosition;
                Vector3 delta = new Vector3(target.x - current.x, 0, target.y - current.z); float distance = delta.magnitude;
                if (distance < best - .2f) { best = distance; lastProgress = Time.realtimeSinceStartup; }
                if (Time.realtimeSinceStartup - lastProgress > 12) { log.Add("stuck at " + current + " target " + target + " speed=" + van.SpeedKmh); Finish("FAIL: blocked progress"); return; }
                if (distance < (phase == 0 ? 2.8f : .45f))
                {
                    log.Add((phase == 0 ? "van" : "walk") + " checkpoint " + point + " " + current.ToString("F3")); point++; best = float.MaxValue; lastProgress = Time.realtimeSinceStartup;
                    if (phase == 0 && point == route.Length)
                    {
                        van.Throttle = 0; van.Handbrake = true; body.linearVelocity = Vector3.zero;
                        phase = 1; point = 0; motor.SetPosition(new Vector3(565, Ground(565,174) + .1f,174)); return;
                    }
                    if (phase == 1 && point == walk.Length) { Finish("PASS: main-road drive, forecourt, west parking; walk from road through north door"); return; }
                    return;
                }
                if (phase == 0)
                {
                    float angle = Vector3.SignedAngle(van.transform.forward, delta, Vector3.up);
                    van.Steer = Mathf.Clamp(angle / van.MaxSteerAngle, -1f, 1f);
                    float targetSpeed = Mathf.Abs(angle) > 35 ? 5 : current.z < 180 ? 7 : 12;
                    van.Throttle = van.SpeedKmh < targetSpeed ? .28f : -.12f; van.Handbrake = false;
                }
                else
                {
                    var ai = new KinematicCharacterController.Examples.AICharacterInputs { MoveVector = delta.normalized, LookVector = delta.normalized }; character.SetInputs(ref ai);
                }
            };
            EditorApplication.update += tick;
        }
    }
}
