using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Debug = UnityEngine.Debug;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Hangar rooms of the V2 base (Vadim 30.10): VAN UPGRADES workshop bay (17 x 10 x 6 m, 8 x 4.4 m roller door) and
    /// PHARMACY (11 x 7 x 4.2 m, window-counter onto the hall), built from Fedya's v1 Workshop_W86 / Pharmacy_W86 geometry and
    /// re-dressed to docs/specs/HANGAR_ROOMS_STYLE_2026-10-30.md (one palette with a per-room accent, the hangar's warm lamps,
    /// real 3D details, ArtDirection section 2 shape rules).
    /// Geometry comes from Assets/Editor/VadimHangarRooms_blender_v01.py (Blender 5.2, reads the v1 FBX files, writes
    /// Rooms/&lt;Room&gt;/Source/&lt;Room&gt;Room_geo_v01.json); this script turns that JSON into meshes (one .asset per room), the
    /// room materials and the prefab (root = the room's floor centre, +Z = front / hall side), then renders review shots.
    /// Batch: -executeMethod OnlyVolunteers.EditorTools.VadimHangarRooms.BuildRenderBatch (OV_ROOMS_BLENDER=1 also re-runs Blender).
    /// Shared hangar materials (Assets/VadimLocal/Hangar/Materials, texture set 45) are only referenced, never changed.</summary>
    public static class VadimHangarRooms
    {
        const string RoomsDir = "Assets/VadimLocal/Hangar/Rooms";
        const string HangarMatDir = "Assets/VadimLocal/Hangar/Materials/";
        const string BlenderScript = "Assets/Editor/VadimHangarRooms_blender_v01.py";
        const string BlenderExe = @"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe";
        const string VanPrefab = "Assets/OnlyVolunteers/Vehicles/Van/Prefabs/Van_v05.prefab";
        public const string ShotDir = @"C:\Users\chern_0eqkb03\VolunteersBuilds\hangar_rooms_v01";
        const uint L0 = 1u, Hall = 1u << 1, Room = 1u << 2;

        sealed class RoomDef
        {
            public string Name, Accent;
            public Vector3 Size;
        }

        static readonly RoomDef[] Defs =
        {
            new RoomDef { Name = "Workshop", Accent = "#9A4A36", Size = new Vector3(17f, 6f, 10f) },
            new RoomDef { Name = "Pharmacy", Accent = "#4F8A6E", Size = new Vector3(11f, 4.2f, 7f) },
        };

        static StringBuilder _log;

        public static string PrefabPath(string room) => $"{RoomsDir}/{room}/{room}Room_v01.prefab";

        // ------------------------------------------------------------------ JSON (filled by JsonUtility)
#pragma warning disable 0649
        [Serializable] class Geo { public string room; public int tris; public PartJ[] parts; public ColJ[] colliders; public LightJ[] lights; public AnchorJ[] anchors; }
        [Serializable] class PartJ { public string name, group, layer; public bool @static; public float[] pos, v, n, uv; public SubJ[] sub; public int tris; }
        [Serializable] class SubJ { public string role; public int[] t; }
        [Serializable] class ColJ { public string name; public float[] c, s; public float yaw; }
        [Serializable] class LightJ { public string name, type, mask; public float[] p, col; public float i, r, a; public bool sh; }
        [Serializable] class AnchorJ { public string name; public float[] p; public float yaw; }
#pragma warning restore 0649

        // ------------------------------------------------------------------ entries
        [MenuItem("Volunteers/Hangar Rooms/Build Workshop + Pharmacy prefabs")]
        public static void BuildWorkshopAndPharmacy()
        {
            _log = new StringBuilder();
            foreach (var d in Defs) Build(d);
            AssetDatabase.SaveAssets();
            WriteLog("build_log.txt");
        }

        [MenuItem("Volunteers/Hangar Rooms/Regenerate geometry in Blender + build")]
        public static void RegenerateAndBuild()
        {
            RunBlender();
            AssetDatabase.Refresh();
            BuildWorkshopAndPharmacy();
        }

        [MenuItem("Volunteers/Hangar Rooms/Render review shots")]
        public static void RenderPreviewsMenu()
        {
            _log = new StringBuilder();
            RenderPreviews();
            WriteLog("render_log.txt");
        }

        /// <summary>Batch: optional Blender pass (OV_ROOMS_BLENDER=1), build both prefabs, render the review shots.</summary>
        public static void BuildRenderBatch()
        {
            if (Environment.GetEnvironmentVariable("OV_ROOMS_BLENDER") == "1") { RunBlender(); AssetDatabase.Refresh(); }
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            BuildWorkshopAndPharmacy();
            _log = new StringBuilder();
            RenderPreviews();
            WriteLog("render_log.txt");
        }

        static void RunBlender()
        {
            if (!File.Exists(BlenderExe)) throw new FileNotFoundException("Blender 5.2 not found", BlenderExe);
            var psi = new ProcessStartInfo(BlenderExe, $"-b --factory-startup -P \"{Path.GetFullPath(BlenderScript)}\" -- both")
            { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
            using var p = Process.Start(psi);
            string o = p.StandardOutput.ReadToEnd();
            p.WaitForExit();
            foreach (var line in o.Split('\n').Where(l => l.StartsWith("[rooms]"))) Debug.Log(line.Trim());
            if (p.ExitCode != 0) throw new Exception("Blender failed: " + p.StandardError.ReadToEnd());
        }

        static void WriteLog(string file)
        {
            Directory.CreateDirectory(ShotDir);
            File.WriteAllText(Path.Combine(ShotDir, file), _log.ToString());
            Debug.Log("[HangarRooms]\n" + _log);
        }

        // ------------------------------------------------------------------ materials
        static Material Hangar(string name)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(HangarMatDir + name + ".mat");
            if (!m) throw new FileNotFoundException("hangar material missing: " + name);
            return m;
        }

        static Color Hex(string h)
        {
            ColorUtility.TryParseHtmlString(h, out var c);
            return c;
        }

        static Material Flat(string dir, string room, string role, Color c, float smooth, float metal)
        {
            string path = $"{dir}/{room}Room_{role}_v01.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, path); }
            m.SetColor("_BaseColor", c);
            m.SetColor("_Color", c);
            m.SetFloat("_Smoothness", smooth);
            m.SetFloat("_Metallic", metal);
            m.SetFloat("_EnvironmentReflections", 1f);
            EditorUtility.SetDirty(m);
            return m;
        }

        const string WS86Corrugated = "Assets/OnlyVolunteers/Art/Buildings/Workshop_W86/Materials/WS86_corrugated_grey_v01.mat";

        /// <summary>The v1 workshop wall material Vadim likes, copied once, with Fedya's v1 values pinned (grey tint, tile 1.5 m).</summary>
        static Material CorrugatedGrey(string dir, string room)
        {
            string path = $"{dir}/{room}Room_CorrugatedGrey_v01.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m)
            {
                var src = AssetDatabase.LoadAssetAtPath<Material>(WS86Corrugated);
                if (!src) throw new FileNotFoundException("v1 workshop wall material missing", WS86Corrugated);
                m = new Material(src) { name = Path.GetFileNameWithoutExtension(path) };
                AssetDatabase.CreateAsset(m, path);
            }
            var tint = new Color(0.6392157f, 0.65882355f, 0.67058825f);
            m.SetColor("_BaseColor", tint);
            m.SetColor("_Color", tint);
            foreach (var p in new[] { "_BaseMap", "_MainTex" }) { m.SetTextureScale(p, new Vector2(0.66667f, 0.66667f)); m.SetTextureOffset(p, Vector2.zero); }
            m.SetFloat("_Smoothness", 0.099f);
            m.SetFloat("_Metallic", 0.1f);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Texture2D LabelsTexture(string path)
        {
            if (!(AssetImporter.GetAtPath(path) is TextureImporter imp))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                imp = AssetImporter.GetAtPath(path) as TextureImporter;
                if (imp == null) throw new FileNotFoundException("labels atlas missing: " + path);
            }
            if (!imp.mipmapEnabled || imp.anisoLevel != 8 || imp.wrapMode != TextureWrapMode.Clamp || imp.maxTextureSize != 2048 ||
                imp.textureCompression != TextureImporterCompression.CompressedHQ || imp.filterMode != FilterMode.Trilinear)
            {
                imp.textureType = TextureImporterType.Default;
                imp.mipmapEnabled = true;
                imp.sRGBTexture = true;
                imp.anisoLevel = 8;
                imp.filterMode = FilterMode.Trilinear;
                imp.wrapMode = TextureWrapMode.Clamp;
                imp.textureCompression = TextureImporterCompression.CompressedHQ;
                imp.maxTextureSize = 2048;
                imp.alphaSource = TextureImporterAlphaSource.None;
                imp.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        /// <summary>Role -> material. Shared roles use the hangar's own materials (set 45, world-scale tiling = the meshes'
        /// 1 UV = 1 m); the accent, warm off-white, bare steel, marking yellow, light wood and cardboard are flat (even)
        /// room materials. Not used on purpose (Vadim 30.10 night, no striped surfaces): 03 hangar corrugated, 06 hazard
        /// stripes, 07 wood cladding, 12 pallet wood. The workshop's walls and ceiling wear CorrWS, a copy of Fedya's
        /// WS86_corrugated_grey_v01 (T7_metal_trapez albedo + normal, 1.5 m tile = 8 modelled ribs), kept as a copy so a
        /// darker hall tint of the v1 material can never reach the workshop.</summary>
        static Dictionary<string, Material> Materials(RoomDef d)
        {
            string dir = $"{RoomsDir}/{d.Name}/Materials";
            EnsureFolder(dir);
            var m = new Dictionary<string, Material>
            {
                ["Floor"] = Hangar("Hangar_01_Floor_Concrete_v01"),
                ["Graphite"] = Hangar("Hangar_04_Truss_Graphite_v01"),
                ["Roller"] = Hangar("Hangar_05_RollerDoor_Gate_v01"),
                ["Olive"] = Hangar("Hangar_11_Crate_Military_v01"),
                ["Sign"] = Hangar("Hangar_14_Signs_v01"),
                ["Rubber"] = Hangar("Hangar_Rubber_Black_v01"),
                ["Glass"] = Hangar("Hangar_Glass_v01"),
                ["Lamp"] = Hangar("Hangar_LampPanel_Warm_v01"),
                ["Fabric"] = Hangar("Hangar_Sofa_v01"),
                ["Accent"] = Flat(dir, d.Name, "Accent", Hex(d.Accent), .25f, .1f),
                ["OffWhite"] = Flat(dir, d.Name, "OffWhite", Hex("#D9CDB4"), .2f, 0f),
                ["Steel"] = Flat(dir, d.Name, "Steel", Hex("#8E9396"), .3f, .2f),
                // the hall's lemon marking yellow (VadimHangarLab mMarkY): reads yellow, not orange, under the 3000 K lamps
                ["Yellow"] = Flat(dir, d.Name, "MarkingYellow", new Color(.86f, .95f, .22f), .3f, 0f),
                ["LightWood"] = Flat(dir, d.Name, "LightWood", Hex("#B08858"), .12f, 0f),
                ["Cardboard"] = Flat(dir, d.Name, "Cardboard", Hex("#A8895F"), .1f, 0f),
            };
            if (d.Name == "Workshop") m["CorrWS"] = CorrugatedGrey(dir, d.Name);
            if (d.Name == "Pharmacy")
            {
                var lab = Flat(dir, d.Name, "Labels", new Color(.92f, .92f, .92f), .2f, 0f);
                var tex = LabelsTexture($"{RoomsDir}/Pharmacy/Textures/PharmacyRoom_Labels_v01.png");
                foreach (var p in new[] { "_BaseMap", "_MainTex" }) { lab.SetTexture(p, tex); lab.SetTextureScale(p, Vector2.one); lab.SetTextureOffset(p, Vector2.zero); }
                EditorUtility.SetDirty(lab);
                m["Labels"] = lab;
            }
            return m;
        }

        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }

        // ------------------------------------------------------------------ build
        static void Build(RoomDef d)
        {
            string dir = $"{RoomsDir}/{d.Name}";
            string json = $"{dir}/Source/{d.Name}Room_geo_v01.json";
            var geo = JsonUtility.FromJson<Geo>(File.ReadAllText(json));
            var mats = Materials(d);
            string meshPath = $"{dir}/{d.Name}Room_Meshes_v01.asset";
            if (File.Exists(meshPath)) AssetDatabase.DeleteAsset(meshPath);

            var root = new GameObject($"{d.Name}Room_v01");
            var groups = new Dictionary<string, Transform>();
            Transform G(string n)
            {
                if (!groups.TryGetValue(n, out var t)) { t = new GameObject(n).transform; t.SetParent(root.transform, false); groups[n] = t; }
                return t;
            }
            Object container = null;
            int tris = 0, verts = 0;
            var byGroup = new Dictionary<string, int>();
            foreach (var p in geo.parts)
            {
                int nv = p.v.Length / 3;
                var V = new Vector3[nv];
                var N = new Vector3[nv];
                var U = new Vector2[nv];
                for (int i = 0; i < nv; i++)
                {
                    V[i] = new Vector3(p.v[3 * i], p.v[3 * i + 1], p.v[3 * i + 2]);
                    N[i] = new Vector3(p.n[3 * i], p.n[3 * i + 1], p.n[3 * i + 2]).normalized;
                    U[i] = new Vector2(p.uv[2 * i], p.uv[2 * i + 1]);
                }
                var mesh = new Mesh { name = $"{d.Name}_{p.name}" };
                if (nv > 65000) mesh.indexFormat = IndexFormat.UInt32;
                mesh.vertices = V;
                mesh.normals = N;
                mesh.uv = U;
                mesh.subMeshCount = p.sub.Length;
                for (int s = 0; s < p.sub.Length; s++) mesh.SetTriangles(p.sub[s].t, s);
                mesh.RecalculateBounds();
                mesh.RecalculateTangents();
                if (container == null) { AssetDatabase.CreateAsset(mesh, meshPath); container = mesh; }
                else AssetDatabase.AddObjectToAsset(mesh, container);

                var go = new GameObject(p.name);
                go.transform.SetParent(G(p.group), false);
                go.transform.localPosition = new Vector3(p.pos[0], p.pos[1], p.pos[2]);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterials = p.sub.Select(s => mats.TryGetValue(s.role, out var mm) ? mm : throw new KeyNotFoundException("role " + s.role)).ToArray();
                r.renderingLayerMask = p.layer == "hall" ? L0 | Hall : p.layer == "both" ? L0 | Hall | Room : L0 | Room;
                r.shadowCastingMode = p.sub.All(s => s.role == "Glass" || s.role == "Lamp") ? ShadowCastingMode.Off : ShadowCastingMode.On;
                r.receiveShadows = true;
                if (p.@static)
                    GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic);
                tris += p.tris;
                verts += nv;
                byGroup[p.group] = (byGroup.TryGetValue(p.group, out int bg) ? bg : 0) + p.tris;
            }

            var cols = new GameObject("Colliders").transform;
            cols.SetParent(root.transform, false);
            foreach (var c in geo.colliders)
            {
                var go = new GameObject("C_" + c.name);
                go.transform.SetParent(cols, false);
                go.transform.localPosition = new Vector3(c.c[0], c.c[1], c.c[2]);
                go.transform.localRotation = Quaternion.Euler(0f, c.yaw, 0f);
                go.AddComponent<BoxCollider>().size = new Vector3(c.s[0], c.s[1], c.s[2]);
                go.isStatic = true;
            }

            var lights = new GameObject("Lights").transform;
            lights.SetParent(root.transform, false);
            foreach (var l in geo.lights)
            {
                var go = new GameObject(l.name);
                go.transform.SetParent(lights, false);
                go.transform.localPosition = new Vector3(l.p[0], l.p[1], l.p[2]);
                go.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
                var L = go.AddComponent<Light>();
                L.type = l.type == "Spot" ? LightType.Spot : LightType.Point;
                L.color = new Color(l.col[0], l.col[1], l.col[2]);
                L.intensity = l.i;
                L.range = l.r;
                if (L.type == LightType.Spot) { L.spotAngle = l.a; L.innerSpotAngle = l.a * .4f; }
                L.shadows = l.sh ? LightShadows.Soft : LightShadows.None;
                L.shadowStrength = .8f;
                L.shadowNearPlane = .2f;
                L.lightmapBakeType = LightmapBakeType.Realtime;
                var ld = L.GetUniversalAdditionalLightData();
                ld.renderingLayers = l.mask == "hall" ? Hall : Hall | Room;
                ld.customShadowLayers = false;
            }

            var anchors = new GameObject("Anchors").transform;
            anchors.SetParent(root.transform, false);
            foreach (var a in geo.anchors)
            {
                var go = new GameObject(a.name);
                go.transform.SetParent(anchors, false);
                go.transform.localPosition = new Vector3(a.p[0], a.p[1], a.p[2]);
                go.transform.localRotation = Quaternion.Euler(0f, a.yaw, 0f);
            }

            // size check: the wall / ceiling colliders are the room box; renderer bounds include the sign and frames
            var wallB = BoundsOf(cols.GetComponentsInChildren<BoxCollider>().Where(b => b.name.StartsWith("C_wall") || b.name == "C_ceiling" || b.name == "C_floor").Select(b => b.bounds));
            var rendB = BoundsOf(root.GetComponentsInChildren<Renderer>().Select(r => r.bounds));
            var shellB = BoundsOf(root.GetComponentsInChildren<Renderer>().Where(r => r.transform.parent.name != "Sign").Select(r => r.bounds));
            string prefab = PrefabPath(d.Name);
            PrefabUtility.SaveAsPrefabAsset(root, prefab);
            Object.DestroyImmediate(root);
            _log.AppendLine($"{d.Name}: prefab {prefab}; meshes {meshPath}; {geo.parts.Length} parts, {tris} triangles, {verts} vertices; " +
                            string.Join(", ", byGroup.Select(k => $"{k.Key} {k.Value}")));
            _log.AppendLine($"  walls+ceiling box {V3(wallB.size)} (min {V3(wallB.min)} max {V3(wallB.max)}; floor collider is 0.3 m below y 0); " +
                            $"renderers without sign {V3(shellB.size)} (min {V3(shellB.min)} max {V3(shellB.max)}); all renderers {V3(rendB.size)}");
            _log.AppendLine($"  colliders {geo.colliders.Length}, lights {geo.lights.Length} ({geo.lights.Count(l => l.sh)} shadowed), anchors {geo.anchors.Length}");
        }

        static Bounds BoundsOf(IEnumerable<Bounds> bs)
        {
            bool first = true;
            var b = new Bounds();
            foreach (var x in bs) { if (first) { b = x; first = false; } else b.Encapsulate(x); }
            return b;
        }

        static string V3(Vector3 v) => $"({v.x:F2}, {v.y:F2}, {v.z:F2})";

        // ------------------------------------------------------------------ review shots
        struct ShotDef
        {
            public string Name;
            public Vector3 Pos, Look;
            public float Fov;
            public bool NoCeiling;
            public ShotDef(string n, Vector3 p, Vector3 l, float fov, bool noCeil = false) { Name = n; Pos = p; Look = l; Fov = fov; NoCeiling = noCeil; }
        }

        static readonly Dictionary<string, ShotDef[]> Shots = new()
        {
            ["Workshop"] = new[]
            {
                new ShotDef("01_eye_from_door", new Vector3(-3.2f, 1.7f, 4.5f), new Vector3(1.2f, 1.2f, -4.6f), 72f),
                new ShotDef("02_overview_34_no_ceiling", new Vector3(8.5f, 15.5f, 14f), new Vector3(0f, 0f, -0.6f), 50f, true),
                new ShotDef("03_from_hall", new Vector3(3.0f, 1.7f, 13.5f), new Vector3(0f, 2.3f, 0f), 60f),
                new ShotDef("04_van_on_lift", new Vector3(-4.8f, 1.7f, 2.9f), new Vector3(0f, 1.1f, -0.7f), 62f),
                new ShotDef("05_close_workbench_toolboard", new Vector3(-5.6f, 1.65f, 1.2f), new Vector3(-8.1f, 1.1f, -0.3f), 55f),
                new ShotDef("06_close_toolchest_shelving", new Vector3(-6.0f, 1.4f, 3.4f), new Vector3(-8.0f, 0.7f, 0.9f), 55f),
                new ShotDef("07_close_lift_post", new Vector3(-3.7f, 1.3f, 1.5f), new Vector3(-2.0f, 0.9f, -0.4f), 58f),
                new ShotDef("08_back_to_door", new Vector3(4.0f, 1.7f, -4.3f), new Vector3(-1.0f, 2.2f, 5f), 72f),
            },
            ["Pharmacy"] = new[]
            {
                new ShotDef("01_eye_from_door", new Vector3(-4.5f, 1.7f, 3.15f), new Vector3(-0.8f, 1.0f, -3.5f), 72f),
                new ShotDef("02_overview_34_no_ceiling", new Vector3(5.5f, 10.5f, 10f), new Vector3(0f, 0f, -0.4f), 50f, true),
                new ShotDef("03_from_hall", new Vector3(1.0f, 1.7f, 9.5f), new Vector3(0.3f, 1.6f, 0f), 60f),
                new ShotDef("04_back_to_front", new Vector3(0.6f, 1.7f, -2.5f), new Vector3(0f, 1.2f, 3.5f), 72f),
                new ShotDef("05_close_counter_from_hall", new Vector3(-1.6f, 1.6f, 5.3f), new Vector3(-2.4f, 1.0f, 3.2f), 55f),
                new ShotDef("06_close_wall_shelving", new Vector3(-3.0f, 1.6f, 1.2f), new Vector3(-5.2f, 1.1f, 0.2f), 55f),
                new ShotDef("07_close_fridge_from_hall", new Vector3(3.2f, 1.6f, 5.6f), new Vector3(4.35f, 1.1f, 3.4f), 50f),
                new ShotDef("08_close_back_cabinets_rack", new Vector3(1.5f, 1.6f, 0.0f), new Vector3(4.0f, 1.0f, -3.0f), 60f),
            },
        };

        public static void RenderPreviews()
        {
            Directory.CreateDirectory(ShotDir);
            ShaderUtil.allowAsyncCompilation = false;   // the first batch frame otherwise renders with placeholder shaders
            // dark warm environment for reflections (the empty preview scene would reflect Unity's default bright sky on the
            // concrete at grazing angles; inside the hangar the surroundings are dim)
            var cube = new Cubemap(16, TextureFormat.RGBA32, false);
            var px = Enumerable.Repeat(new Color(.06f, .052f, .045f), 16 * 16).ToArray();
            foreach (CubemapFace f in new[] { CubemapFace.PositiveX, CubemapFace.NegativeX, CubemapFace.PositiveY, CubemapFace.NegativeY, CubemapFace.PositiveZ, CubemapFace.NegativeZ })
                cube.SetPixels(px, f);
            cube.Apply();
            foreach (var d in Defs)
            {
                var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(d.Name));
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                inst.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                // the hangar's inside ambient (HangarLighting defaults) and no sun: only the room's own warm lamps
                var sh = new SphericalHarmonicsL2();
                sh.AddAmbientLight(new Color(0.13f, 0.105f, 0.08f));
                sh.AddDirectionalLight(Vector3.up, new Color(0.075f, 0.07f, 0.065f) - new Color(0.13f, 0.105f, 0.08f), 1f);
                RenderSettings.ambientMode = AmbientMode.Custom;
                RenderSettings.ambientProbe = sh;
                RenderSettings.reflectionIntensity = 0.25f;
                RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
                RenderSettings.customReflectionTexture = cube;
                RenderSettings.fog = false;
                RenderSettings.skybox = null;
                // the hall floor around the room (hangar concrete, 2 cm lower so nothing is coplanar with the room floor)
                var hall = GameObject.CreatePrimitive(PrimitiveType.Plane);
                hall.name = "Preview hall floor";
                Object.DestroyImmediate(hall.GetComponent<Collider>());
                hall.transform.position = new Vector3(0f, -0.02f, 0f);
                hall.transform.localScale = new Vector3(6f, 1f, 6f);
                var hr = hall.GetComponent<MeshRenderer>();
                hr.sharedMaterial = Hangar("Hangar_01_Floor_Concrete_v01");
                hr.renderingLayerMask = L0 | Hall | Room;
                var hallLight = new GameObject("Preview hall pendant").AddComponent<Light>();
                hallLight.type = LightType.Spot;
                hallLight.transform.SetPositionAndRotation(new Vector3(0f, 7f, d.Size.z * .5f + 4f), Quaternion.Euler(90f, 0f, 0f));
                hallLight.color = new Color(1f, .78f, .52f);
                hallLight.intensity = 30f;
                hallLight.range = 12f;
                hallLight.spotAngle = 100f;
                hallLight.GetUniversalAdditionalLightData().renderingLayers = Hall;

                GameObject van = null;
                if (d.Name == "Workshop") van = PlaceVan(inst);
                Physics.SyncTransforms();

                foreach (var c in Object.FindObjectsByType<Camera>()) c.enabled = false;
                var go = new GameObject("ShotCam");
                var cam = go.AddComponent<Camera>();
                cam.nearClipPlane = .05f;
                cam.farClipPlane = 300f;
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = new Color(.035f, .03f, .028f);
                var cd = cam.GetUniversalAdditionalCameraData();
                cd.renderPostProcessing = true;
                cd.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
                var ceiling = inst.transform.Find("Ceiling");
                // warm-up frame (discarded): uploads the new materials / textures before the first saved shot
                go.transform.position = inst.transform.TransformPoint(Shots[d.Name][0].Pos);
                go.transform.LookAt(inst.transform.TransformPoint(Shots[d.Name][0].Look));
                Shot(cam, 320, 180, null);
                foreach (var s in Shots[d.Name])
                {
                    if (ceiling) ceiling.gameObject.SetActive(!s.NoCeiling);
                    go.transform.position = inst.transform.TransformPoint(s.Pos);
                    go.transform.LookAt(inst.transform.TransformPoint(s.Look));
                    cam.fieldOfView = s.Fov;
                    Shot(cam, 1600, 900, $"{d.Name}_{s.Name}");
                }
                if (ceiling) ceiling.gameObject.SetActive(true);
                _log.AppendLine($"{d.Name}: {Shots[d.Name].Length} shots -> {ShotDir}");
                Object.DestroyImmediate(go);
                if (van) Object.DestroyImmediate(van);
            }
        }

        /// <summary>Puts van v05 on the lift (bounds centre on Anchor_VanOnLift, nose to the back wall) and logs the fit:
        /// overlaps with the room colliders, the clearance to the lift posts and the carriages, height under the beam.</summary>
        static GameObject PlaceVan(GameObject room)
        {
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(VanPrefab);
            if (!src) { _log.AppendLine("van prefab missing: " + VanPrefab); return null; }
            var van = (GameObject)PrefabUtility.InstantiatePrefab(src);
            var anchor = room.transform.Find("Anchors/Anchor_VanOnLift");
            van.transform.rotation = anchor.rotation;
            van.transform.position = anchor.position;
            var rs = van.GetComponentsInChildren<Renderer>(true).Where(r => r.enabled && r.gameObject.activeInHierarchy && !(r is ParticleSystemRenderer)).ToList();
            var b = BoundsOf(rs.Select(r => r.bounds));
            van.transform.position += new Vector3(anchor.position.x - b.center.x, anchor.position.y - b.min.y + 0.0f, anchor.position.z - b.center.z);
            foreach (var r in rs) r.renderingLayerMask = (r.renderingLayerMask | L0 | Hall) & ~(1u << 3);
            Physics.SyncTransforms();
            b = BoundsOf(rs.Select(r => r.bounds));
            _log.AppendLine($"van v05 renderer bounds: size {V3(b.size)}, min {V3(b.min)}, max {V3(b.max)}");
            var roomCols = room.GetComponentsInChildren<BoxCollider>().Where(c => c.name != "C_floor").ToList();
            var hits = roomCols.Where(c => c.bounds.Intersects(b)).Select(c => c.name).ToList();
            _log.AppendLine("van bounds vs room colliders: " + (hits.Count == 0 ? "no overlap" : "OVERLAP " + string.Join(", ", hits)));
            foreach (var c in roomCols.Where(c => c.name.StartsWith("C_lift")))
            {
                var cb = c.bounds;
                float gap = cb.min.x > b.max.x ? cb.min.x - b.max.x : cb.max.x < b.min.x ? b.min.x - cb.max.x : 0f;
                _log.AppendLine($"  {c.name}: x {cb.min.x:F2}..{cb.max.x:F2}, y {cb.min.y:F2}..{cb.max.y:F2}; side gap to the van {gap:F2} m");
            }
            var carriages = room.GetComponentsInChildren<MeshRenderer>().Where(r => r.name.StartsWith("Lift_Carriage")).Select(r => r.bounds).ToList();
            foreach (var cb in carriages)
            {
                float gap = cb.min.x > b.max.x ? cb.min.x - b.max.x : b.min.x - cb.max.x;
                _log.AppendLine($"  carriage x {cb.min.x:F2}..{cb.max.x:F2}: gap to the van body/mirrors {gap:F2} m");
            }
            var arms = room.GetComponentsInChildren<MeshRenderer>().Where(r => r.name.StartsWith("Lift_Arms")).Select(r => r.bounds).ToList();
            _log.AppendLine($"  arms intersect van bounds: {arms.Count(a => a.Intersects(b))} of {arms.Count} (arms lie on the floor beside the wheels; bounds are a coarse test)");
            return van;
        }

        static void Shot(Camera cam, int w, int h, string name)
        {
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2 };
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            if (name != null) File.WriteAllBytes(Path.Combine(ShotDir, name + ".png"), tex.EncodeToPNG());
            RenderTexture.active = null;
            cam.targetTexture = null;
            Object.DestroyImmediate(tex);
            rt.Release();
        }
    }
}
