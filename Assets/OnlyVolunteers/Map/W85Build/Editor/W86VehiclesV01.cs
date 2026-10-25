using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Map.W85
{
    // W86 world vehicles v01 (brief §10, G47 stage 2; Fedya 25.10 "go"): the six selected CC0 models from ArtSource/Vehicles_W86
    // (selected_models_v01.json; Astra static van not placed yet) become prefabs with a 3-level cross-fading LODGroup and box colliders
    // from G47's collision JSON (UCX meshes are not imported). The play scene's old parked cars and the two W86 trucks are swapped
    // for them in place: same parent, the new car's base centre on the old one's, long axis along the old long axis. Two display cars
    // go on G47's proposed Downtown bays. The player's van is a different object and is never touched. Runs from W85PlayIntegrator
    // (v02) and the menu; idempotent (new instances never match the swap rules again).
    public static class W86VehiclesV01
    {
        const string Root = "Assets/OnlyVolunteers/Art/Vehicles/W86_v01/";
        static readonly (string name, string fbx, string json)[] Models =
        {
            // Fedya 25.10 revision: bigger wheels, +6 cm stance, door seams + handles, sedan quarter pane filled (ArtSource/Vehicles_W86)
            ("SEDAN", "SEDAN_v02", "SEDAN_collisions_v02"), ("COMPACT", "COMPACT_v03", "COMPACT_collisions_v03"),
            ("DISPLAY_COUPE", "DISPLAY_COUPE_v03", "DISPLAY_COUPE_collisions_v03"), ("DISPLAY_GT", "DISPLAY_GT_v02", "DISPLAY_GT_collisions_v02"),
            ("DUMP_TRUCK", "DUMP_TRUCK_v07", "DUMP_TRUCK_collisions_v07"), ("CONTAINER_TRUCK", "CONTAINER_TRUCK_v07", "CONTAINER_TRUCK_collisions_v07"),
        };
        // old visual (prefab asset path / FBX path fragment) -> new model
        static readonly (string match, string model)[] Swaps =
        {
            ("Prefabs/CARS/car_sedan_", "SEDAN"), ("Prefabs/CARS/car_hatchback", "COMPACT"),
            ("MW86_DumpTruck_v01", "DUMP_TRUCK"), ("MW86_TruckContainer_v01", "CONTAINER_TRUCK"),
        };
        static readonly (string model, Vector2 xz, float yaw)[] Display = { ("DISPLAY_COUPE", new(1011f, 514.8f), 90f), ("DISPLAY_GT", new(1068f, 514.8f), 90f) };

        [MenuItem("OnlyVolunteers/Map/W86 Vehicles v01: build prefabs + swap in the open play scene")]
        static void Menu()
        {
            var scene = SceneManager.GetActiveScene();
            Debug.Log(BuildPrefabs() + "\n" + Apply(scene));
            EditorSceneManager.MarkSceneDirty(scene);
        }

        static string PrefabPath(string model) => $"{Root}{model}/{model}_v01.prefab";

        [System.Serializable] class ColliderJson { public string name; public float[] unity_local_center; public float[] unity_local_size; }
        [System.Serializable] class CollisionsJson { public ColliderJson[] colliders; }

        // G47 README: one shared URP Lit material; palette = sRGB BaseMap, surface = linear R metallic / A smoothness; both 128x64,
        // face-centred, so Point / Clamp / no mips. FBX does not carry the Blender node graph: the maps are bound here.
        static Material EnsureMaterial()
        {
            string dir = Root + "shared/", matPath = dir + "MAT_W86_VehiclePalette_v01.mat";
            void Tex(string file, bool srgb)
            {
                if (AssetImporter.GetAtPath(dir + file) is not TextureImporter ti) return;
                if (ti.sRGBTexture == srgb && ti.filterMode == FilterMode.Point && !ti.mipmapEnabled && ti.wrapMode == TextureWrapMode.Clamp) return;
                ti.sRGBTexture = srgb; ti.filterMode = FilterMode.Point; ti.mipmapEnabled = false; ti.wrapMode = TextureWrapMode.Clamp;
                ti.textureCompression = TextureImporterCompression.Uncompressed; ti.SaveAndReimport();
            }
            Tex("W86_VehiclePalette_v01.png", true); Tex("W86_VehicleSurface_v02.png", false);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (!mat) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "MAT_W86_VehiclePalette_v01" }; AssetDatabase.CreateAsset(mat, matPath); }
            mat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(dir + "W86_VehiclePalette_v01.png")); mat.SetColor("_BaseColor", Color.white);
            mat.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(dir + "W86_VehicleSurface_v02.png"));
            mat.EnableKeyword("_METALLICSPECGLOSSMAP"); mat.SetFloat("_SmoothnessTextureChannel", 0f);
            mat.SetFloat("_Smoothness", .9f); // gloss scale over the map's A channel; surface v02 already carries matte paint (.30-.35, metallic .05), glass stays .85
            mat.enableInstancing = true;
            EditorUtility.SetDirty(mat);
            return mat;
        }

        public static string BuildPrefabs()
        {
            int made = 0; var notes = new List<string>();
            var mat = EnsureMaterial();
            foreach (var m in Models)
            {
                var fbx = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}{m.name}/{m.fbx}.fbx");
                if (!fbx) { notes.Add("missing " + m.fbx); continue; }
                var go = (GameObject)Object.Instantiate(fbx);
                go.name = m.name + "_v01";
                foreach (var r in go.GetComponentsInChildren<Renderer>(true).Where(r => r.name.StartsWith("UCX")).ToList()) Object.DestroyImmediate(r.gameObject);
                var rends = go.GetComponentsInChildren<MeshRenderer>(true);
                foreach (var r in rends) r.sharedMaterials = Enumerable.Repeat(mat, r.sharedMaterials.Length).ToArray();
                Renderer[] Lod(int i) => rends.Where(r => r.name.Contains("LOD" + i)).Cast<Renderer>().ToArray();
                var lods = new List<LOD>();
                float[] heights = { .07f, .022f, .005f }; // ~4.4 m car with lodBias 2: LOD1 from ~80 m, LOD2 from ~260 m, culled ~1.1 km
                for (int i = 0; i < 3; i++) { var rs = Lod(i); if (rs.Length > 0) lods.Add(new LOD(heights[i], rs)); }
                if (lods.Count > 0)
                {
                    var lg = go.GetComponent<LODGroup>(); if (!lg) lg = go.AddComponent<LODGroup>(); // the importer makes one from the _LOD names
                    lg.SetLODs(lods.ToArray()); lg.RecalculateBounds();
                    lg.fadeMode = LODFadeMode.CrossFade; lg.animateCrossFading = true;
                }
                else notes.Add(m.name + ": no LOD-named meshes, kept as is");
                var jsonPath = $"{Root}{m.name}/{m.json}.json";
                if (File.Exists(jsonPath))
                {
                    var cj = JsonUtility.FromJson<CollisionsJson>(File.ReadAllText(jsonPath));
                    foreach (var c in cj.colliders ?? new ColliderJson[0])
                    {
                        var bc = go.AddComponent<BoxCollider>();
                        bc.center = new Vector3(c.unity_local_center[0], c.unity_local_center[1], c.unity_local_center[2]);
                        bc.size = new Vector3(c.unity_local_size[0], c.unity_local_size[1], c.unity_local_size[2]);
                    }
                }
                else notes.Add(m.name + ": no collision JSON");
                foreach (var t in go.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic);
                PrefabUtility.SaveAsPrefabAsset(go, PrefabPath(m.name));
                Object.DestroyImmediate(go);
                made++;
            }
            AssetDatabase.SaveAssets();
            return $"vehicles v01: {made} prefabs" + (notes.Count > 0 ? " (" + string.Join("; ", notes) + ")" : "");
        }

        public static string Apply(Scene scene)
        {
            if (Models.Any(m => !File.Exists(PrefabPath(m.name)))) BuildPrefabs();
            var prefabs = Models.ToDictionary(m => m.name, m => AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(m.name)));
            var targets = new Dictionary<GameObject, string>();
            foreach (var t in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)))
            {
                var go = t.gameObject;
                if (PrefabUtility.IsOutermostPrefabInstanceRoot(go))
                {
                    string path = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go);
                    if (path.StartsWith(Root)) continue;
                    foreach (var s in Swaps) if (path.Contains(s.match)) { targets[go] = s.model; break; }
                }
                var mf = go.GetComponent<MeshFilter>();
                if (mf && mf.sharedMesh)
                {
                    string mp = AssetDatabase.GetAssetPath(mf.sharedMesh);
                    foreach (var s in Swaps)
                        if (mp.Contains(s.match) && mp.EndsWith(".fbx"))
                        {
                            var owner = go.GetComponentInParent<LODGroup>() ? go.GetComponentInParent<LODGroup>().gameObject : go.transform.parent ? go.transform.parent.gameObject : go;
                            targets[owner] = s.model; break;
                        }
                }
            }
            int swapped = 0;
            foreach (var kv in targets)
            {
                var old = kv.Key; if (!old) continue;
                var prefab = prefabs[kv.Value]; if (!prefab) continue;
                // the old car's footprint in its own space: base centre + which local axis is the long one
                var root = old.transform; var mn = Vector3.positiveInfinity; var mx = Vector3.negativeInfinity;
                foreach (var mfo in old.GetComponentsInChildren<MeshFilter>(true))
                {
                    if (!mfo.sharedMesh) continue; var b = mfo.sharedMesh.bounds;
                    for (int c = 0; c < 8; c++)
                    {
                        var corner = b.center + Vector3.Scale(b.extents, new Vector3((c & 1) == 0 ? -1 : 1, (c & 2) == 0 ? -1 : 1, (c & 4) == 0 ? -1 : 1));
                        var p = root.InverseTransformPoint(mfo.transform.TransformPoint(corner)); mn = Vector3.Min(mn, p); mx = Vector3.Max(mx, p);
                    }
                }
                if (float.IsInfinity(mn.x)) continue;
                var baseLocal = new Vector3((mn.x + mx.x) / 2, mn.y, (mn.z + mx.z) / 2);
                bool longX = (mx.x - mn.x) > (mx.z - mn.z);
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                inst.transform.SetParent(root.parent, false);
                inst.transform.position = root.TransformPoint(baseLocal);
                inst.transform.rotation = root.rotation * Quaternion.Euler(0, longX ? 90f : 0f, 0); // the new models run along local Z
                inst.transform.SetSiblingIndex(root.GetSiblingIndex());
                inst.name = old.name + "_W86v01";
                Object.DestroyImmediate(old);
                swapped++;
            }
            int shown = 0;
            foreach (var d in Display)
            {
                string name = "W86_Display_" + d.model;
                if (scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).Any(t => t.name == name)) continue;
                var prefab = prefabs[d.model]; if (!prefab) continue;
                float y = Ground(d.xz);
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                inst.name = name; inst.transform.SetPositionAndRotation(new Vector3(d.xz.x, y, d.xz.y), Quaternion.Euler(0, d.yaw, 0));
                shown++;
            }
            return $"vehicles v01: {swapped} parked/world vehicles swapped, {shown} display cars placed; " + Seat(scene);
        }

        // Fedya 25.10: tyres sank into the asphalt. Instances kept the old car's base height while roads/zones are drawn above it (often
        // with no collider), so each car is put on the highest drawn ground under its four wheels. Idempotent; props above are ignored.
        public static string Seat(Scene scene)
        {
            var cars = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true))
                .Where(t => t.name.EndsWith("_W86v01") || t.name.StartsWith("W86_Display_")).ToList();
            var temp = new List<GameObject>();
            // ground meshes without colliders get a temporary MeshCollider so the rays see what the player sees
            foreach (var r in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>(true)))
            {
                string n = r.name;
                if (!(n.StartsWith("Road") || n.StartsWith("Zone_") || n.StartsWith("Street_") || n.StartsWith("Sidewalk") || n.StartsWith("DC3_") || n.Contains("plaza") || n.Contains("Curb"))) continue;
                if (r.GetComponent<Collider>() || !r.TryGetComponent<MeshFilter>(out var mf) || !mf.sharedMesh) continue;
                var b = r.bounds; if (!cars.Any(c => b.Contains(new Vector3(c.position.x, b.center.y, c.position.z)))) continue;
                var go = new GameObject("tmp_ground"); go.transform.SetPositionAndRotation(r.transform.position, r.transform.rotation); go.transform.localScale = r.transform.lossyScale;
                go.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh; temp.Add(go);
            }
            Physics.SyncTransforms();
            int moved = 0; float maxUp = 0f;
            foreach (var car in cars)
            {
                var own = new HashSet<Collider>(car.GetComponentsInChildren<Collider>(true));
                var bc = car.GetComponent<BoxCollider>(); var half = bc ? new Vector2(bc.size.x * .4f, bc.size.z * .35f) : new Vector2(.75f, 1.3f);
                float best = float.NegativeInfinity, y0 = car.position.y;
                foreach (var o in new[] { new Vector3(-half.x, 0, half.y), new Vector3(half.x, 0, half.y), new Vector3(-half.x, 0, -half.y), new Vector3(half.x, 0, -half.y) })
                    foreach (var h in Physics.RaycastAll(car.TransformPoint(o) + Vector3.up * .4f, Vector3.down, 1.4f, ~0, QueryTriggerInteraction.Ignore))
                        if (!own.Contains(h.collider) && !h.collider.attachedRigidbody && !h.collider.name.StartsWith("UCX") && h.point.y > best) best = h.point.y;
                if (float.IsNegativeInfinity(best) || Mathf.Abs(best - y0) < .003f) continue;
                car.position = new Vector3(car.position.x, best, car.position.z); maxUp = Mathf.Max(maxUp, best - y0); moved++;
            }
            foreach (var go in temp) Object.DestroyImmediate(go);
            return $"seated {moved}/{cars.Count} vehicles (max lift {maxUp:F3} m)";
        }

        static float Ground(Vector2 xz)
        {
            float best = float.NegativeInfinity;
            foreach (var h in Physics.RaycastAll(new Vector3(xz.x, 200f, xz.y), Vector3.down, 400f, ~0, QueryTriggerInteraction.Ignore))
                if (!h.collider.attachedRigidbody && h.point.y > best && h.point.y < 60f) best = h.point.y;
            if (float.IsNegativeInfinity(best) && Terrain.activeTerrain) best = Terrain.activeTerrain.SampleHeight(new Vector3(xz.x, 0, xz.y)) + Terrain.activeTerrain.transform.position.y;
            return float.IsNegativeInfinity(best) ? 0f : best;
        }
    }
}
