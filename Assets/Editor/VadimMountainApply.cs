using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Hutor massif (Vadim 28.10, ChatGPT reference 28): stepped grey rock walls, 2-3 wide tiers with dense conifers, rocky NE peaks,
    /// rock cliff to the sea, the lake and a cascading waterfall. Local W86 scene + terrain only. Order on the scene: Hill -> Forest -> Mountains.
    /// Design (heights delta + zones, 1 m grid x 0..760, z 300..950) comes from the plan script: Assets/VadimLocal/Mountain/Data.
    /// Run() = VadimForestApply.Run() (Hill + Forest state) -> renders "before" -> mountains -> save -> renders "after". Restore() = VadimForestApply.Run().</summary>
    static class VadimMountainApply
    {
        const string Scene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        const string Bak = @"C:\Users\chern_0eqkb03\VolunteersBuilds\backup_mountains";
        const string Dir = "Assets/VadimLocal/Mountain";
        const string Out = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";
        const string ShotDir = @"C:\Users\chern_0eqkb03\VolunteersBuilds\mountain_shots_v01\";
        const string TexSrc = @"C:\Users\chern_0eqkb03\VolunteersBuilds\mountain_tex_v01\";
        static readonly RectInt Area = new RectInt(0, 300, 760, 650);   // x 0..760, z 300..950 (the design grid)
        const int GX = 761, GZ = 651;

        public static void Compile() { Debug.Log("[Mountain] compiled"); }

        // ================================================================================================ backup / restore

        static void SafetyBackup()
        {
            Directory.CreateDirectory(Bak);
            if (File.Exists(Path.Combine(Bak, "terrain_path.txt"))) return;
            var guid = AssetDatabase.FindAssets("TerrainData_W85_v02 t:TerrainData").FirstOrDefault();
            string tdPath = guid != null ? AssetDatabase.GUIDToAssetPath(guid) : null;
            if (string.IsNullOrEmpty(tdPath)) throw new System.Exception("TerrainData_W85_v02 not found");
            File.Copy(tdPath, Path.Combine(Bak, Path.GetFileName(tdPath)), true);
            File.Copy(Scene, Path.Combine(Bak, Path.GetFileName(Scene)), true);
            File.WriteAllText(Path.Combine(Bak, "terrain_path.txt"), tdPath);
            Debug.Log("[Mountain] one-time safety backup written to " + Bak);
        }

        /// <summary>Back to the Hill + Forest state (the forest tool restores its own pre-forest backup and re-applies the forest).</summary>
        public static void Restore() { VadimForestApply.Run(); Debug.Log("[Mountain] restored = forest state"); }

        // ================================================================================================ run

        static Terrain ter; static TerrainData td; static Vector3 tp; static int groundLayer;
        static StringBuilder log;
        static System.Random Rng;

        public static void Run()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            SafetyBackup();
            VadimForestApply.Run();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != Scene) scene = EditorSceneManager.OpenScene(Scene);
            Shots("before");
            Apply(scene);
        }

        /// <summary>Only the mountains on the scene as it is (for a scene that already holds the forest state; not idempotent).</summary>
        static void Apply(UnityEngine.SceneManagement.Scene scene)
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            log = new StringBuilder(); Rng = new System.Random(2811);
            ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); td = ter.terrainData; tp = ter.transform.position; groundLayer = ter.gameObject.layer;
            Folders();
            LoadDesign();
            Materials();
            var root = GameObject.Find("Map_W85_v02").transform;
            var old = root.Find("VadimMountain"); if (old) Object.DestroyImmediate(old.gameObject);
            mRoot = new GameObject("VadimMountain").transform; mRoot.SetParent(root, false);
            SnapshotOld();
            LoadWater();
            Heights();
            Splat();
            RockWork(root);
            Trees();
            Boulders();
            Water(root);
            Grass();
            FillSea("Sea_fill_mountain", Rect.MinMaxRect(-10, 390, 140, 900), c => NewY(c) < -.05f && Z(c).mask);
            ter.Flush();
            EditorUtility.SetDirty(td);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Out + "mountain_apply.txt", log.ToString());
            Debug.Log("[Mountain] applied:\n" + log);
            Shots("after");
        }

        /// <summary>Only the falls (Vadim 28.10: mountains are final): rebuilds the water group of the mountain on the saved scene, saves, renders
        /// waterfall_close / waterfall_mid / cascade, two moments each. Terrain, rock, trees untouched.</summary>
        public static void WaterOnly()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            var scene = EditorSceneManager.OpenScene(Scene);
            log = new StringBuilder(); Rng = new System.Random(2811);
            ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); td = ter.terrainData; tp = ter.transform.position; groundLayer = ter.gameObject.layer;
            var root = GameObject.Find("Map_W85_v02").transform; mRoot = root.Find("VadimMountain");
            if (!mRoot) throw new System.Exception("no VadimMountain group - run Run() first");
            var oldW = mRoot.Find("Water_mountain_cascade"); if (oldW) Object.DestroyImmediate(oldW.gameObject);
            foreach (var g in AssetDatabase.FindAssets("t:Mesh", new[] { Dir + "/Meshes" }))
            {   // the old fall meshes only (everything else in the folder is the mountain)
                string mp = AssetDatabase.GUIDToAssetPath(g); string fn = Path.GetFileNameWithoutExtension(mp);
                if (fn.StartsWith("Waterfall_") || fn.StartsWith("Base_") || fn.StartsWith("Water_spring") || fn.StartsWith("Water_cascade") || fn.StartsWith("FoamRing_cascade")) AssetDatabase.DeleteAsset(mp);
            }
            var puff = Puff();
            sprayMat = Particle("MT_spray", new Color(1f, 1f, 1f, .85f), puff);
            mistMat = Particle("MT_mist", new Color(.92f, .95f, 1f, .22f), puff);
            ringMat = Particle("MT_ripple_ring", new Color(1f, 1f, 1f, .7f), RingTex());
            foreach (var pm in new[] { sprayMat, mistMat, ringMat }) { pm.renderQueue = 3004; EditorUtility.SetDirty(pm); }   // after water 3000, stream 3001, foam 3002/3003
            rockMat = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/Materials/MT_stone_grey.mat"); if (rockMat) NoGlow(rockMat);
            wetMat = WetMaterial(); NoGlow(wetMat); WetLayer();
            LoadWater();
            Water(root);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            var dbg = new StringBuilder("gorge renderers (x 468..504, z 662..708):");
            foreach (var r in Object.FindObjectsByType<MeshRenderer>())
            {
                var bb = r.bounds; if (bb.size.x > 200 || bb.max.x < 468 || bb.min.x > 504 || bb.max.z < 662 || bb.min.z > 708 || r.name.StartsWith("FK_")) continue;
                dbg.Append($" {r.name}[{string.Join("+", r.sharedMaterials.Select(m => m ? m.name : "-"))}]");
            }
            log.AppendLine(dbg.ToString());
            File.WriteAllText(Out + "mountain_water_apply.txt", log.ToString());
            Debug.Log("[Mountain] water rebuilt:\n" + log);
            onlyWater = true; try { Shots("after"); } finally { onlyWater = false; }
        }
        static bool onlyWater;

        // ================================================================================================ waterfall preview exe (Vadim 28.10)

        const string PreviewDir = Dir + "/WaterfallPreview";
        const string PreviewScene = PreviewDir + "/WaterfallPreview.unity";
        const string PreviewExe = @"C:\Users\chern_0eqkb03\VolunteersBuilds\WaterfallPreview\WaterfallPreview.exe";

        /// <summary>One Unity start: the falls rebuilt on the map (renders) and the preview exe rebuilt.</summary>
        public static void WaterAndPreview() { WaterOnly(); WaterfallPreviewBuild(); }

        /// <summary>A separate scene with only the lower waterfall (its stream layers, foam, ripples, particles, wet rock), the rock skins /
        /// blocks right round it, the plunge pool, the stream, a ground patch and the trees there; the map's sun and sky; a fly camera at the
        /// mid view. Built to VolunteersBuilds\WaterfallPreview\WaterfallPreview.exe. The map scene and the Build Settings list are not changed.</summary>
        public static void WaterfallPreviewBuild()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            log = new StringBuilder();
            if (!AssetDatabase.IsValidFolder(PreviewDir)) AssetDatabase.CreateFolder(Dir, "WaterfallPreview");
            var map = EditorSceneManager.OpenScene(Scene, OpenSceneMode.Single);
            ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); td = ter.terrainData; tp = ter.transform.position; groundLayer = ter.gameObject.layer;
            LoadWater();
            var root = GameObject.Find("Map_W85_v02").transform; var vm = root.Find("VadimMountain");
            var region = Rect.MinMaxRect(430f, 615f, 545f, 765f);
            bool Over(Bounds b) => region.Overlaps(Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z));
            var srcs = new List<GameObject>();
            var wc = vm.Find("Water_mountain_cascade");
            foreach (Transform c in wc) if (c.name.StartsWith("Waterfall_lower")) srcs.Add(c.gameObject);
            var fxs = wc.Find("Spray_mountain"); if (fxs) foreach (Transform c in fxs) if (c.name.Contains("_lower")) srcs.Add(c.gameObject);
            var water = root.Find("Water");
            foreach (Transform c in water)
            {
                if (!c.gameObject.activeInHierarchy) continue; var r = c.GetComponent<Renderer>();
                if (c.name == "Water_River_river" || r && Over(r.bounds) && r.bounds.size.x < 150f) srcs.Add(c.gameObject);
            }
            foreach (var r in vm.GetComponentsInChildren<MeshRenderer>())
                if ((r.name.StartsWith("RockSkin_") || r.name.StartsWith("RockBlocks_") || r.name.StartsWith("Boulders_")) && Over(r.bounds)) srcs.Add(r.gameObject);
            var oc = root.Find("RockFaces/RockOutcrops"); if (oc) foreach (Transform c in oc) { var r = c.GetComponentInChildren<Renderer>(); if (c.gameObject.activeInHierarchy && r && Over(r.bounds)) srcs.Add(c.gameObject); }
            var sunSrc = RenderSettings.sun ? RenderSettings.sun : Object.FindObjectsByType<Light>().FirstOrDefault(l => l.type == LightType.Directional);
            var sky = RenderSettings.skybox; var amode = RenderSettings.ambientMode; Color aSky = RenderSettings.ambientSkyColor, aEq = RenderSettings.ambientEquatorColor, aGr = RenderSettings.ambientGroundColor; float aInt = RenderSettings.ambientIntensity;
            // trees of the area (terrain instances -> prefab instances)
            var trees = new List<(GameObject pf, Vector3 pos, float rot, Vector3 sc)>();
            foreach (var ti in td.treeInstances)
            {
                var w = new Vector3(tp.x + ti.position.x * td.size.x, tp.y + ti.position.y * td.size.y, tp.z + ti.position.z * td.size.z);
                if (!region.Contains(new Vector2(w.x, w.z))) continue; var pf = td.treePrototypes[ti.prototypeIndex].prefab; if (!pf) continue;
                trees.Add((pf, w, ti.rotation * Mathf.Rad2Deg, new Vector3(ti.widthScale, ti.heightScale, ti.widthScale)));
            }
            var ground = PreviewGround(region);
            float G(float x, float z) => ter.SampleHeight(new Vector3(x, 0, z)) + tp.y;
            var camPos = new Vector3(483f, G(483f, 664f) + 5f, 664f);

            // ---- the preview scene
            var prev = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            UnityEngine.SceneManagement.SceneManager.SetActiveScene(prev);
            var proot = new GameObject("WaterfallPreview").transform;
            int copied = 0;
            foreach (var s in srcs)
            {
                var cp = Object.Instantiate(s, s.transform.position, s.transform.rotation); cp.name = s.name;
                cp.transform.localScale = s.transform.lossyScale; cp.transform.SetParent(proot, true); cp.SetActive(true); copied++;
            }
            var gGo = new GameObject("Ground_patch"); gGo.transform.SetParent(proot, false);
            gGo.AddComponent<MeshFilter>().sharedMesh = ground.mesh; gGo.AddComponent<MeshRenderer>().sharedMaterials = ground.mats; gGo.AddComponent<MeshCollider>().sharedMesh = ground.mesh;
            var tr = new GameObject("Trees").transform; tr.SetParent(proot, false);
            foreach (var t in trees) { var g = (GameObject)PrefabUtility.InstantiatePrefab(t.pf, prev); g.transform.SetParent(tr, false); g.transform.position = t.pos; g.transform.rotation = Quaternion.Euler(0, t.rot, 0); g.transform.localScale = t.sc; }
            var sun = new GameObject("Sun").AddComponent<Light>(); sun.type = LightType.Directional;
            if (sunSrc) { sun.transform.rotation = sunSrc.transform.rotation; sun.color = sunSrc.color; sun.intensity = sunSrc.intensity; sun.shadows = sunSrc.shadows; sun.shadowStrength = sunSrc.shadowStrength; sun.colorTemperature = sunSrc.colorTemperature; sun.useColorTemperature = sunSrc.useColorTemperature; }
            else { sun.transform.rotation = Quaternion.Euler(37f, 45f, 0f); sun.color = new Color(1f, .89f, .745f); sun.intensity = 1.05f; sun.shadows = LightShadows.Soft; }
            RenderSettings.sun = sun; RenderSettings.skybox = sky; RenderSettings.ambientMode = amode; RenderSettings.ambientSkyColor = aSky; RenderSettings.ambientEquatorColor = aEq; RenderSettings.ambientGroundColor = aGr; RenderSettings.ambientIntensity = aInt; RenderSettings.fog = false;
            var camGo = new GameObject("Camera"); camGo.tag = "MainCamera"; var cam = camGo.AddComponent<Camera>(); cam.nearClipPlane = .1f; cam.farClipPlane = 2500f; cam.fieldOfView = 60f;
            camGo.AddComponent<AudioListener>(); camGo.transform.position = camPos; camGo.transform.LookAt(new Vector3(485.5f, 21f, 702f));
            var fly = camGo.AddComponent<OnlyVolunteers.Map.Look.LookFlyCamera>(); fly.Speed = 6f;
            var appType = System.Type.GetType("OnlyVolunteers.VadimLocal.WaterfallPreviewApp, Assembly-CSharp");
            if (appType != null) camGo.AddComponent(appType); else log.AppendLine("preview: WaterfallPreviewApp type not found (Esc / window size missing)");
            EditorSceneManager.SaveScene(prev, PreviewScene);
            EditorSceneManager.CloseScene(map, true);
            log.AppendLine($"preview scene {PreviewScene}: {copied} objects copied, {trees.Count} trees, ground patch {ground.mesh.vertexCount} verts");
            // ---- build (scene path passed directly; Build Settings and Player Settings untouched)
            Directory.CreateDirectory(Path.GetDirectoryName(PreviewExe));
            // own product / company name, so the preview's window settings (HKCU\Software\<company>\<product>) never leak into the game's; restored after
            string pn0 = PlayerSettings.productName, cn0 = PlayerSettings.companyName; UnityEditor.Build.Reporting.BuildReport rep;
            try
            {
                PlayerSettings.productName = "WaterfallPreview"; PlayerSettings.companyName = "VadimPreview";
                rep = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { PreviewScene }, locationPathName = PreviewExe, target = BuildTarget.StandaloneWindows64, targetGroup = BuildTargetGroup.Standalone, options = BuildOptions.None });
            }
            finally { PlayerSettings.productName = pn0; PlayerSettings.companyName = cn0; }
            log.AppendLine($"preview built as VadimPreview / WaterfallPreview, player settings restored to {cn0} / {pn0}");
            log.AppendLine($"build: {rep.summary.result}, {rep.summary.totalErrors} errors, {rep.summary.totalSize / 1048576f:0.0} MB, {rep.summary.totalTime.TotalMinutes:0.0} min -> {PreviewExe}");
            File.WriteAllText(Out + "waterfall_preview_build.txt", log.ToString());
            Debug.Log("[Mountain] waterfall preview:\n" + log);
        }

        /// <summary>The ground of the preview area as one mesh (1 m), stone on the steep parts, wet stone right round the fall, grass elsewhere.</summary>
        static (Mesh mesh, Material[] mats) PreviewGround(Rect r)
        {
            int nx = Mathf.CeilToInt(r.width), nz = Mathf.CeilToInt(r.height);
            var V = new List<Vector3>(); var tris = new[] { new List<int>(), new List<int>(), new List<int>() };
            for (int j = 0; j <= nz; j++) for (int i = 0; i <= nx; i++) { float x = r.xMin + i, z = r.yMin + j; V.Add(new Vector3(x, ter.SampleHeight(new Vector3(x, 0, z)) + tp.y - .05f, z)); }
            for (int j = 0; j < nz; j++) for (int i = 0; i < nx; i++)
            {
                int a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1; var p = new Vector2(r.xMin + i + .5f, r.yMin + j + .5f);
                int sm = WetNear(p) > .45f ? 2 : Slope(p) > 33f ? 1 : 0;
                tris[sm].AddRange(new[] { a, c, d, a, d, b });
            }
            var m = new Mesh { name = "WaterfallPreview_ground", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.SetVertices(V); m.subMeshCount = 3; for (int s = 0; s < 3; s++) m.SetTriangles(tris[s], s); m.RecalculateNormals(); m.RecalculateBounds();
            string mp = PreviewDir + "/WaterfallPreview_ground.asset"; AssetDatabase.DeleteAsset(mp); AssetDatabase.CreateAsset(m, mp);
            string gp = PreviewDir + "/MT_preview_grass.mat"; var grass = AssetDatabase.LoadAssetAtPath<Material>(gp);
            if (!grass) { grass = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "MT_preview_grass" }; AssetDatabase.CreateAsset(grass, gp); }
            grass.SetColor("_BaseColor", new Color(.36f, .5f, .22f)); grass.SetFloat("_Smoothness", .05f); EditorUtility.SetDirty(grass);
            var stone = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/Materials/MT_stone_grey.mat"); var wet = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/Materials/MT_stone_wet.mat");
            return (m, new[] { grass, stone, wet });
        }

        /// <summary>Renders of the scene as it is now (after a Run), same cameras.</summary>
        public static void AfterShots()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            EditorSceneManager.OpenScene(Scene);
            Shots("after");
        }

        static Transform mRoot;
        /// <summary>The stream gorge from the waterfall pool down to the road bridge (outside the massif, but its walls are the same stone).</summary>
        static readonly Rect Gorge = Rect.MinMaxRect(455f, 600f, 530f, 722f);
        /// <summary>The lower waterfall's face (the stepped sheet hangs here).</summary>
        static readonly Rect FallFace = Rect.MinMaxRect(481.5f, 696.5f, 489f, 705.5f);
        static float NearWaterCalm(Vector2 p) { var z = Z(p); float c = 1f - z.prot; if (Casc != null && p.x > 465f && p.x < 515f && p.y > 680f && p.y < 875f) c *= Sm(2.5f, 9f, Mathf.Min(PolyDist(p, Casc), (p - new Vector2(485.2f, 701f)).magnitude - 3f)); return c; }

        static void Folders()
        {
            foreach (var sub in new[] { "", "/Textures", "/Materials", "/Meshes", "/Data", "/Layers" })
            {
                string p = Dir + sub; if (AssetDatabase.IsValidFolder(p)) continue;
                AssetDatabase.CreateFolder(p.Substring(0, p.LastIndexOf('/')), p.Substring(p.LastIndexOf('/') + 1));
            }
            foreach (var g in AssetDatabase.FindAssets("t:Mesh", new[] { Dir + "/Meshes" })) AssetDatabase.DeleteAsset(AssetDatabase.GUIDToAssetPath(g));
        }

        // ================================================================================================ design data

        static float[] delta; static byte[] zone;
        struct Zn { public bool mask; public float w, scree, prot, peak, edge; }

        static void LoadDesign()
        {
            var db = File.ReadAllBytes(Dir + "/Data/mountain_delta_v01.bytes"); var zb = File.ReadAllBytes(Dir + "/Data/mountain_zone_v01.bytes");
            if (db.Length != GX * GZ * 4 || zb.Length != GX * GZ * 5) throw new System.Exception("mountain design: unexpected size");
            delta = new float[GX * GZ]; System.Buffer.BlockCopy(db, 0, delta, 0, db.Length); zone = zb;
            int n = 0; for (int k = 0; k < GX * GZ; k++) if (zone[k * 5] > 0) n++;
            log.AppendLine($"design: {n} massif cells (1 m), delta {delta.Min():0.0}..{delta.Max():0.0} m");
        }

        static float Delta(float x, float z)
        {
            float u = x - Area.xMin, v = z - Area.yMin; if (u < 0 || v < 0 || u > GX - 1 || v > GZ - 1) return 0f;
            int i0 = Mathf.Min((int)u, GX - 2), j0 = Mathf.Min((int)v, GZ - 2); float fu = u - i0, fv = v - j0;
            return Mathf.Lerp(Mathf.Lerp(delta[j0 * GX + i0], delta[j0 * GX + i0 + 1], fu), Mathf.Lerp(delta[(j0 + 1) * GX + i0], delta[(j0 + 1) * GX + i0 + 1], fu), fv);
        }
        static Zn Z(Vector2 p)
        {
            int i = Mathf.RoundToInt(p.x - Area.xMin), j = Mathf.RoundToInt(p.y - Area.yMin);
            if (i < 0 || j < 0 || i >= GX || j >= GZ) return new Zn();
            int o = (j * GX + i) * 5; byte r = zone[o];
            return new Zn { mask = r > 0, w = r > 0 ? (r - 1) / 254f : 0f, scree = zone[o + 1] / 255f, prot = zone[o + 2] / 255f, peak = zone[o + 3] / 255f, edge = zone[o + 4] / 255f };
        }
        /// <summary>Inside the massif or within r metres of it.</summary>
        static bool NearMask(Vector2 p, float r)
        {
            if (Z(p).mask) return true;
            for (int a = 0; a < 8; a++) { float ang = a * Mathf.PI / 4f; if (Z(p + new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)) * r).mask) return true; }
            return false;
        }

        // ================================================================================================ materials: plain stone (forest rocks), scree M06, forest floor M04

        static Material rockMat, boulderMat, sprayMat, mistMat, wetMat, ringMat;
        static int Lwet = -1;
        static int Lrock = -1, Lscree = -1, Lfloor = -1;
        const int Meadow = 0, Worn = 1, OldRock = 7;
        static readonly Color StoneColor = new Color(.44f, .445f, .45f);    // Vadim 28.10: neutral grey (skins, blocks, boulders)
        static readonly Color StoneLift = new Color(.30f, .275f, .235f);   // self-light (~.07/.06/.045 linear): shadowed faces stay grey, not dark blue
        static readonly Color TerrainStone = new Color(.53f, .525f, .51f);  // the terrain stone layer has no self-light: a little lighter so it matches the skins
        static readonly Color ScreeTint = new Color(.86f, .83f, .79f);     // M06 (mean .584/.596/.62) tinted to the same grey

        static Texture2D ImportTex(string name)
        {
            string dst = Dir + "/Textures/" + name + ".png", src = TexSrc + name + ".png";
            if (!File.Exists(dst) || new FileInfo(dst).Length != new FileInfo(src).Length) { File.Copy(src, dst, true); AssetDatabase.ImportAsset(dst, ImportAssetOptions.ForceUpdate); }
            var ti = (TextureImporter)AssetImporter.GetAtPath(dst); bool dirty = false;
            if (ti.wrapMode != TextureWrapMode.Repeat) { ti.wrapMode = TextureWrapMode.Repeat; dirty = true; }
            if (!ti.mipmapEnabled) { ti.mipmapEnabled = true; dirty = true; }
            if (ti.anisoLevel != 4) { ti.anisoLevel = 4; dirty = true; }
            if (ti.maxTextureSize != 1024) { ti.maxTextureSize = 1024; dirty = true; }
            if (!ti.sRGBTexture) { ti.sRGBTexture = true; dirty = true; }
            if (dirty) ti.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(dst);
        }

        static TerrainLayer Layer(string name, Texture2D tex, float tile, Color tint, float smooth)
        {
            string p = Dir + "/Layers/" + name + ".terrainlayer"; var l = AssetDatabase.LoadAssetAtPath<TerrainLayer>(p);
            if (!l) { l = new TerrainLayer(); AssetDatabase.CreateAsset(l, p); }
            l.diffuseTexture = tex; l.tileSize = new Vector2(tile, tile); l.tileOffset = Vector2.zero; l.diffuseRemapMin = Vector4.zero; l.diffuseRemapMax = new Vector4(tint.r, tint.g, tint.b, 1f);
            l.smoothness = smooth; l.metallic = 0f; l.normalMapTexture = null; l.maskMapTexture = null; EditorUtility.SetDirty(l);
            return l;
        }

        static Material Lit(string name, Color c, Texture tex, float smooth)
        {
            string p = Dir + "/Materials/" + name + ".mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            var sh = Shader.Find("Universal Render Pipeline/Lit");
            if (!m) { m = new Material(sh) { name = name }; AssetDatabase.CreateAsset(m, p); }
            m.shader = sh; m.enableInstancing = true; m.SetColor("_BaseColor", c); m.SetTexture("_BaseMap", tex); m.SetTextureScale("_BaseMap", Vector2.one);
            m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", 0f); m.SetFloat("_EnvironmentReflections", 0f); m.SetFloat("_SpecularHighlights", 0f);
            m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            EditorUtility.SetDirty(m); return m;
        }

        static Material Particle(string name, Color c, Texture tex)
        {
            string p = Dir + "/Materials/" + name + ".mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            var sh = Shader.Find("Universal Render Pipeline/Particles/Unlit");
            if (!m) { m = new Material(sh) { name = name }; AssetDatabase.CreateAsset(m, p); }
            m.shader = sh; m.SetTexture("_BaseMap", tex); m.SetColor("_BaseColor", c);
            m.SetFloat("_Surface", 1f); m.SetFloat("_Blend", 0f); m.SetFloat("_ZWrite", 0f); m.SetFloat("_Cull", 0f);
            m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            m.SetOverrideTag("RenderType", "Transparent"); m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.SetFloat("_SoftParticlesEnabled", 0f); m.enableInstancing = true;
            EditorUtility.SetDirty(m); return m;
        }

        /// <summary>A soft round puff (white, alpha falls off to the rim) for the spray and mist particles.</summary>
        static Texture2D Puff()
        {
            string p = Dir + "/Textures/MT_puff.png";
            if (!File.Exists(p))
            {
                var t = new Texture2D(64, 64, TextureFormat.RGBA32, false);
                for (int y = 0; y < 64; y++) for (int x = 0; x < 64; x++)
                {
                    float d = new Vector2(x - 31.5f, y - 31.5f).magnitude / 31.5f; float a = Mathf.Clamp01(1f - d); a = a * a * (3f - 2f * a);
                    t.SetPixel(x, y, new Color(1, 1, 1, a));
                }
                File.WriteAllBytes(p, t.EncodeToPNG()); Object.DestroyImmediate(t); AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate);
                var ti = (TextureImporter)AssetImporter.GetAtPath(p); ti.alphaIsTransparency = true; ti.wrapMode = TextureWrapMode.Clamp; ti.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(p);
        }

        /// <summary>A flat stone texture of the forest rock colour with a very soft large mottle (the terrain rock layer under the faceted
        /// skins reads as the same plain grey stone).</summary>
        static Texture2D PlainStone(string file, Color baseC)
        {
            string p = Dir + "/Textures/" + file + ".png";
            string tag = $"{baseC.r:0.000} {baseC.g:0.000} {baseC.b:0.000}";
            if (!File.Exists(p) || !File.Exists(p + ".col") || File.ReadAllText(p + ".col") != tag)
            {
                int N = 256; var t = new Texture2D(N, N, TextureFormat.RGB24, false);
                for (int y = 0; y < N; y++) for (int x = 0; x < N; x++)
                {
                    float u = x / (float)N * 6.2832f, v = y / (float)N * 6.2832f;   // tileable: sums of sines with whole periods
                    float n = .5f * Mathf.Sin(u * 2f + Mathf.Sin(v * 3f) * .8f) * Mathf.Cos(v * 2f + Mathf.Sin(u * 1f)) + .3f * Mathf.Sin(u * 5f + v * 3f) * Mathf.Sin(v * 6f - u * 2f);
                    float f = 1f + n * .045f;
                    t.SetPixel(x, y, new Color(baseC.r * f, baseC.g * f, baseC.b * f));
                }
                File.WriteAllBytes(p, t.EncodeToPNG()); File.WriteAllText(p + ".col", tag); Object.DestroyImmediate(t); AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate);
            }
            var ti = (TextureImporter)AssetImporter.GetAtPath(p); if (ti.wrapMode != TextureWrapMode.Repeat || !ti.sRGBTexture) { ti.wrapMode = TextureWrapMode.Repeat; ti.sRGBTexture = true; ti.SaveAndReimport(); }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(p);
        }

        static void Materials()
        {
            var m04 = ImportTex("M04_shelf_forest_floor"); var m06 = ImportTex("M06_scree");
            // Vadim 28.10: the walls are real faceted rock in the forest rocks' plain grey stone (forest_kit_v02 FK_Rock), not a textured wall
            rockMat = Lit("MT_stone_grey", StoneColor, null, .05f);   // own grey (FK_Rock reads beige under the warm sun)
            NoGlow(rockMat);
            wetMat = WetMaterial();
            boulderMat = rockMat;
            foreach (var old in new[] { Dir + "/Materials/MT_rock_wall_M01.mat", Dir + "/Materials/MT_boulder_grey.mat", Dir + "/Layers/TL_M01_rock_wall.terrainlayer" }) if (File.Exists(old)) AssetDatabase.DeleteAsset(old);
            var puff = Puff();
            sprayMat = Particle("MT_spray", new Color(1f, 1f, 1f, .85f), puff);
            mistMat = Particle("MT_mist", new Color(.92f, .95f, 1f, .22f), puff);
            ringMat = Particle("MT_ripple_ring", new Color(1f, 1f, 1f, .7f), RingTex());
            foreach (var pm in new[] { sprayMat, mistMat, ringMat }) { pm.renderQueue = 3004; EditorUtility.SetDirty(pm); }   // after water 3000, stream 3001, foam 3002/3003
            // three new terrain layers: plain stone (the rock colour), scree M06 tinted to the same stone, forest floor M04; grass = the game's own layers; global layer 7 untouched
            var lr = Layer("TL_stone_plain", PlainStone("MT_stone_plain", TerrainStone), 9f, Color.white, .05f); var lw = WetLayer(); var ls = Layer("TL_M06_scree", m06, 6f, ScreeTint, .03f); var lf = Layer("TL_M04_shelf_forest_floor", m04, 7.5f, Color.white, 0f);
            var layers = td.terrainLayers.ToList();
            int Idx(TerrainLayer l) { int i = layers.IndexOf(l); if (i < 0) { layers.Add(l); i = layers.Count - 1; } return i; }
            Lrock = Idx(lr); Lscree = Idx(ls); Lfloor = Idx(lf); Lwet = Idx(lw);
            if (layers.Count != td.terrainLayers.Length) td.terrainLayers = layers.ToArray();
            log.AppendLine($"layers: stone = {Lrock}, scree M06 = {Lscree}, forest floor M04 = {Lfloor}, wet stone = {Lwet}; terrain now {td.terrainLayers.Length} layers ({(td.terrainLayers.Length + 3) / 4} splat passes); rock material {AssetDatabase.GetAssetPath(rockMat)}");
        }

        // ================================================================================================ heights

        static float[,] oldY;   // 1 m over the design grid, before the change
        static float NewY(Vector2 p) => ter.SampleHeight(new Vector3(p.x, 0, p.y)) + tp.y;
        static float OldY(Vector2 p)
        {
            float u = p.x - Area.xMin, v = p.y - Area.yMin; if (u < 0 || v < 0 || u > GX - 1 || v > GZ - 1) return NewY(p);
            int i0 = Mathf.Min((int)u, GX - 2), j0 = Mathf.Min((int)v, GZ - 2); float fu = u - i0, fv = v - j0;
            return Mathf.Lerp(Mathf.Lerp(oldY[j0, i0], oldY[j0, i0 + 1], fu), Mathf.Lerp(oldY[j0 + 1, i0], oldY[j0 + 1, i0 + 1], fu), fv);
        }
        static float Slope(Vector2 p) => td.GetSteepness((p.x - tp.x) / td.size.x, (p.y - tp.z) / td.size.z);
        static float Sm(float a, float b, float x) { float t = Mathf.Clamp01((x - a) / (b - a)); return t * t * (3f - 2f * t); }
        static float R01() => (float)Rng.NextDouble();
        static float RRange(float a, float b) => a + (b - a) * (float)Rng.NextDouble();

        static void SnapshotOld()
        {
            oldY = new float[GZ, GX];
            for (int j = 0; j < GZ; j++) for (int i = 0; i < GX; i++) oldY[j, i] = ter.SampleHeight(new Vector3(Area.xMin + i, 0, Area.yMin + j)) + tp.y;
        }

        static void Heights()
        {
            int hr = td.heightmapResolution; float sx = td.size.x / (hr - 1), sz = td.size.z / (hr - 1);
            int c0 = Mathf.Max(0, Mathf.FloorToInt((Area.xMin - tp.x) / sx)), c1 = Mathf.Min(hr - 1, Mathf.CeilToInt((Area.xMax - tp.x) / sx));
            int r0 = Mathf.Max(0, Mathf.FloorToInt((Area.yMin - tp.z) / sz)), r1 = Mathf.Min(hr - 1, Mathf.CeilToInt((Area.yMax - tp.z) / sz));
            var h = td.GetHeights(c0, r0, c1 - c0 + 1, r1 - r0 + 1); int n = 0; float top = 0f;
            for (int r = 0; r <= r1 - r0; r++) for (int c = 0; c <= c1 - c0; c++)
            {
                float x = tp.x + (c0 + c) * sx, z = tp.z + (r0 + r) * sz, d = Delta(x, z); if (Mathf.Abs(d) < 1e-4f) continue;
                h[r, c] = Mathf.Clamp01(h[r, c] + d / td.size.y); n++; top = Mathf.Max(top, h[r, c] * td.size.y + tp.y);
            }
            td.SetHeights(c0, r0, h);
            td.SyncHeightmap();
            log.AppendLine($"heights: {n} samples changed, highest point {top:0.0} m");
        }

        // ================================================================================================ splat: one plain stone on the walls and peaks, scree (M06) at the feet, forest floor (M04) on the shelves

        /// <summary>Right round the falling water the stone and scree are wet: darker, a little glossy.</summary>
        static void Wet(float[,,] al, int j, int i, Vector2 p, int L)
        {
            float wn = WetNear(p); if (wn <= 0f) return;
            float mv = wn * (al[j, i, Lrock] + al[j, i, Lscree]); al[j, i, Lrock] *= 1f - wn; al[j, i, Lscree] *= 1f - wn; al[j, i, Lwet] += mv;
            float s = 0f; for (int l = 0; l < L; l++) s += al[j, i, l]; for (int l = 0; l < L; l++) al[j, i, l] /= Mathf.Max(s, 1e-4f);
        }

        static void Splat()
        {
            int A = td.alphamapResolution; float ax = td.size.x / A, az = td.size.z / A;
            int a0 = Mathf.Max(0, Mathf.FloorToInt((Area.xMin - tp.x) / ax)), a1 = Mathf.Min(A, Mathf.CeilToInt((Area.xMax - tp.x) / ax));
            int b0 = Mathf.Max(0, Mathf.FloorToInt((Area.yMin - tp.z) / az)), b1 = Mathf.Min(A, Mathf.CeilToInt((Area.yMax - tp.z) / az));
            var al = td.GetAlphamaps(a0, b0, a1 - a0, b1 - b0); int L = td.alphamapLayers; var tgt = new float[L]; int painted = 0;
            for (int j = 0; j < b1 - b0; j++) for (int i = 0; i < a1 - a0; i++)
            {
                var p = new Vector2(tp.x + (a0 + i + .5f) * ax, tp.z + (b0 + j + .5f) * az);
                var z = Z(p);
                if (!z.mask)
                {   // the gorge below the waterfall: its old dark rock becomes our stone too (one grey with the skins)
                    if (!Gorge.Contains(p)) continue;
                    float g7 = al[j, i, OldRock], gst = Slope(p);
                    if (g7 > 0f) { al[j, i, OldRock] = 0f; if (gst > 30f) al[j, i, Lrock] += g7; else al[j, i, Lscree] += g7; }
                    Wet(al, j, i, p, L); painted++; continue;
                }
                float st = Slope(p);
                float ws = Mathf.Max(z.w, z.prot * z.edge);   // the protected water banks are repainted too (heights kept)
                System.Array.Clear(tgt, 0, L);
                float n1 = Mathf.PerlinNoise(p.x / 37f + 3.1f, p.y / 37f + 7.7f), n2 = Mathf.PerlinNoise(p.x / 6.3f + 1.7f, p.y / 6.3f + 9.2f);
                float rock = Sm(31f, 39f, st + (n2 - .5f) * 4f);
                rock = Mathf.Max(rock, z.peak * Sm(22f, 30f, st));
                if (InWater(p, 2.5f) && !(PolyDist(p, Casc) < 4f)) rock *= .15f;   // the brook / pool banks stay soft ground, not a grey strip
                float scree = Mathf.Max(z.scree, Sm(21f, 30f, st) * .85f) * (1f - rock);
                if (InWater(p, 2.5f) && PolyDist(p, Casc) >= 4f) scree *= .3f;
                else if (st < 31f)
                {   // next to a wall: the ground the bulging stone skin overhangs is stone (rim above) or scree (foot below), never green through a gap
                    float y0 = NewY(p);
                    for (int a = 0; a < 6; a++)
                    {
                        var q = p + new Vector2(Mathf.Cos(a * 1.0472f), Mathf.Sin(a * 1.0472f)) * 2.6f; if (Slope(q) < 40f) continue;
                        if (NewY(q) > y0) scree = Mathf.Max(scree, .85f); else rock = Mathf.Max(rock, .8f);
                    }
                    scree = Mathf.Min(scree, 1f - rock);
                }
                float rest = Mathf.Max(0f, 1f - rock - scree);
                float clear = Sm(.6f, .72f, n1);                                    // clearings and rims: the game's grass
                tgt[Lrock] = rock; tgt[Lscree] = scree;
                tgt[Lfloor] = rest * (1f - clear) * (.8f + .2f * n2); tgt[Meadow] = rest * (clear * .7f + (1f - clear) * .2f * (1f - n2)); tgt[Worn] = rest * clear * .3f;
                float sum = 0f; for (int l = 0; l < L; l++) sum += tgt[l];
                for (int l = 0; l < L; l++) al[j, i, l] = Mathf.Lerp(al[j, i, l], tgt[l] / Mathf.Max(sum, 1e-4f), ws);
                // the old dark rock (layer 7) and its blocky grass spots go everywhere in the massif: into our stone / scree
                float o7 = al[j, i, OldRock]; if (o7 > 0f) { al[j, i, OldRock] = 0f; if (st > 30f) al[j, i, Lrock] += o7; else al[j, i, Lscree] += o7; }
                Wet(al, j, i, p, L);
                sum = 0f; for (int l = 0; l < L; l++) sum += al[j, i, l]; for (int l = 0; l < L; l++) al[j, i, l] /= Mathf.Max(sum, 1e-4f);
                painted++;
            }
            td.SetAlphamaps(a0, b0, al);
            log.AppendLine($"splat: {painted} cells repainted");
        }

        // ================================================================================================ rock: old faces / outcrops out, faceted stone skins over every steep cell of the massif

        static void RockWork(Transform root)
        {
            int cut = 0, meshes = 0, off = 0, moved = 0;
            var rf = root.Find("RockFaces");
            if (rf) foreach (var mf in rf.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!mf.sharedMesh || mf.transform.parent != rf) continue;
                var bnd = mf.GetComponent<Renderer>().bounds; if (!new Rect(Area.xMin, Area.yMin, Area.width, Area.height).Overlaps(Rect.MinMaxRect(bnd.min.x, bnd.min.z, bnd.max.x, bnd.max.z))) continue;
                var m = mf.sharedMesh; if (!m.isReadable) { log.AppendLine("rock face not readable: " + mf.name); continue; }
                var v = m.vertices; var tri = m.triangles; var keep = new List<int>(); var l2w = mf.transform.localToWorldMatrix;
                for (int k = 0; k < tri.Length; k += 3)
                {
                    var c = l2w.MultiplyPoint3x4((v[tri[k]] + v[tri[k + 1]] + v[tri[k + 2]]) / 3f);
                    if (NearMask(new Vector2(c.x, c.z), 2.5f) || Gorge.Contains(new Vector2(c.x, c.z)) && c.y > -1f) cut++; else keep.AddRange(new[] { tri[k], tri[k + 1], tri[k + 2] });
                }
                if (keep.Count == tri.Length) continue;
                var nm = Object.Instantiate(m); nm.name = m.name + "_mountain"; nm.SetTriangles(keep, 0); nm.RecalculateBounds();
                string path = Dir + "/Meshes/rockface_" + meshes + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(nm, path);
                mf.sharedMesh = nm; var col = mf.GetComponent<MeshCollider>(); if (col) col.sharedMesh = nm; meshes++;
                if (keep.Count == 0) mf.gameObject.SetActive(false);
            }
            var oc = root.Find("RockFaces/RockOutcrops");
            if (oc) foreach (Transform r in oc)
            {
                var p = new Vector2(r.position.x, r.position.z); var z = Z(p); if (!z.mask || !r.gameObject.activeSelf) continue;
                float dy = NewY(p) - OldY(p);
                if (z.w > .05f || Mathf.Abs(dy) > .3f) { r.gameObject.SetActive(false); off++; } else if (Mathf.Abs(dy) > .02f) { r.position += Vector3.up * dy; moved++; }
            }
            int recol = 0;
            foreach (var grp in new[] { root.Find("Water"), root.Find("RockFaces/RockOutcrops") })
                if (grp) foreach (Transform r in grp)
                {
                    if (!r.name.StartsWith("Rock_") || !r.gameObject.activeSelf) continue; var p = new Vector2(r.position.x, r.position.z);
                    if (!(Z(p).mask || Gorge.Contains(p))) continue;
                    foreach (var mr in r.GetComponentsInChildren<MeshRenderer>(true)) { mr.sharedMaterials = mr.sharedMaterials.Select(_ => rockMat).ToArray(); recol++; }
                }
            log.AppendLine($"rock: {recol} kept river rocks / outcrops in the massif and the gorge now the same stone");
            // skins: every steep cell (> 33 deg) of the massif + the gorge: coarse faceted low-poly rock (2 m cells, blocky columns, flat shading)
            var skins = new GameObject("RockSkin_mountain").transform; skins.SetParent(mRoot, false); int tris = 0, chunks = 0;
            for (int cx = Area.xMin; cx < Area.xMax; cx += 64) for (int cz = Area.yMin; cz < Area.yMax; cz += 64)
            {
                int t = SkinFacet($"RockSkin_mountain_{cx}_{cz}", new RectInt(cx, cz, Mathf.Min(64, Area.xMax - cx), Mathf.Min(64, Area.yMax - cz)), skins);
                if (t > 0) { tris += t; chunks++; }
            }
            log.AppendLine($"rock: Fedya's faces cut {cut} tris in {meshes} meshes; {off} old outcrops off, {moved} re-seated; faceted stone skins {tris} tris in {chunks} chunks");
            // debug: what stands on the gorge's east bank (the 'bluish' rock of the first renders)
            var sbd = new StringBuilder("gorge east bank renderers:");
            foreach (var r in Object.FindObjectsByType<MeshRenderer>())
            {
                var b = r.bounds; if (b.max.x < 494 || b.min.x > 514 || b.max.z < 650 || b.min.z > 700 || b.size.x > 300) continue;
                if (r.name.StartsWith("FK_") || r.name.Contains("LOD")) continue;
                sbd.Append($" {r.name}({(r.sharedMaterial ? r.sharedMaterial.name : "-")})");
            }
            log.AppendLine(sbd.ToString());
        }

        static bool SteepCell(float x, float z)
        {
            var p = new Vector2(x, z); bool inside = Z(p).mask || Gorge.Contains(p) && NewY(p) > .3f; if (!inside) return false;
            if (FallFace.Contains(p) || InWater(p, .6f)) return false;          // the water runs over the bare stone (no skin in front of it)
            return Slope(p) > 33f;
        }
        static float Hash(int a, int b, int c = 0)
        {
            unchecked { uint h = (uint)(a * 374761393 + b * 668265263 + c * 1274126177); h = (h ^ (h >> 13)) * 1274126177u; h ^= h >> 16; return (h & 0xffffff) / 16777216f; }
        }
        /// <summary>Smooth 3D value noise 0..1 (world space, so neighbouring tiles agree and nothing repeats).</summary>
        static float VN3(float x, float y, float z)
        {
            int ix = Mathf.FloorToInt(x), iy = Mathf.FloorToInt(y), iz = Mathf.FloorToInt(z);
            float fx = x - ix, fy = y - iy, fz = z - iz; fx = fx * fx * (3f - 2f * fx); fy = fy * fy * (3f - 2f * fy); fz = fz * fz * (3f - 2f * fz);
            float H(int a, int b, int c) => Hash(ix + a, iy + b * 7919, iz + c);
            float x00 = Mathf.Lerp(H(0, 0, 0), H(1, 0, 0), fx), x10 = Mathf.Lerp(H(0, 1, 0), H(1, 1, 0), fx), x01 = Mathf.Lerp(H(0, 0, 1), H(1, 0, 1), fx), x11 = Mathf.Lerp(H(0, 1, 1), H(1, 1, 1), fx);
            return Mathf.Lerp(Mathf.Lerp(x00, x10, fy), Mathf.Lerp(x01, x11, fy), fz);
        }
        static float Fbm3(float x, float y, float z, int oct)
        {
            float v = 0f, a = 1f, t = 0f;
            for (int o = 0; o < oct; o++) { v += a * VN3(x, y, z); t += a; a *= .5f; x = x * 2.03f + 17.1f; y = y * 2.03f + 3.7f; z = z * 2.03f + 9.3f; }
            return v / t;
        }

        /// <summary>Multi-scale sculpted rock relief (Vadim 28.10: varied, not cheaply chopped): (1) big vertical buttresses and slabs bulging
        /// up to ~4 m with gullies between, (2) overhang-like ledge lines and blocky steps / cuts, each only in its own zones, (3) calm zones
        /// where the face stays a fairly smooth slab. Everything is driven by world-space noise: no grid, no repeat.</summary>
        static float WallRelief(Vector3 p)
        {
            // tall columns / slabs: narrow across (8-14 m), long up the wall (60 m), firm edges, flat faces
            float big = Sm(.42f, .58f, Fbm3(p.x / 11f, p.y / 60f, p.z / 11f, 2));
            float round = Fbm3(p.x / 9f + 40f, p.y / 30f, p.z / 9f, 1);
            float D = 3.2f * big + .55f * (round - .5f) + .4f;
            float lm = Sm(.56f, .7f, Fbm3(p.x / 52f + 11f, p.y / 70f, p.z / 52f, 2));          // ledge zones (rarer)
            if (lm > 0f)
            {
                float hb = 6.5f + 6f * VN3(p.x / 41f, 3.3f, p.z / 41f);
                float band = (p.y + 7f * Fbm3(p.x / 23f + 3f, 1.1f, p.z / 23f, 2)) / hb, f = band - Mathf.Floor(band);
                D += lm * 1.7f * Sm(.1f, .88f, f) * (1f - Sm(.9f, 1f, f));                        // each band juts out higher up, then steps back: a ledge line
            }
            float mm = Sm(.6f, .74f, Fbm3(p.x / 37f + 70f, p.y / 45f, p.z / 37f, 2));         // broken zones: blocks, steps, cuts (only here and there)
            if (mm > 0f)
            {
                float w = 2.6f + 3.6f * VN3(p.x / 29f, p.y / 29f + 5f, p.z / 29f), hgt = w * (1.3f + .9f * VN3(p.x / 17f, 9.1f, p.z / 17f));
                D += mm * (.2f + 1.0f * Hash(Mathf.FloorToInt(p.x / w), Mathf.FloorToInt(p.y / hgt), Mathf.FloorToInt(p.z / w)));
            }
            return D;
        }
        /// <summary>The direction a wall point is pushed: mostly outward horizontally (buttresses, overhang-like rims), a little along the normal.</summary>
        static Vector3 PushDir(Vector3 n)
        {
            var h = new Vector3(n.x, 0f, n.z); if (h.sqrMagnitude < .04f) return n;
            return (h.normalized * .8f + n * .35f).normalized;
        }

        /// <summary>The stone skin over the steep cells of one 64 m tile: 1.6 m cells, vertices wandering a little and pushed out by the
        /// multi-scale relief, border vertices sunk into the ground; normals smooth across gentle bends and split only at hard edges (> 38 deg),
        /// so big faces read as smooth slabs and edges stay crisp (stylised low-poly rock); collider for the bulges.</summary>
        static int SkinFacet(string name, RectInt R, Transform parent)
        {
            const float C = 1.6f; const int P = 4;
            int nx = Mathf.CeilToInt(R.width / C), nz = Mathf.CeilToInt(R.height / C);
            var flag = new bool[nx + 2 * P, nz + 2 * P];
            for (int i = -P; i < nx + P; i++) for (int j = -P; j < nz + P; j++)
            {
                float x0 = R.xMin + i * C, z0 = R.yMin + j * C;
                flag[i + P, j + P] = SteepCell(x0 + .4f, z0 + .4f) || SteepCell(x0 + 1.2f, z0 + .4f) || SteepCell(x0 + .4f, z0 + 1.2f) || SteepCell(x0 + 1.2f, z0 + 1.2f);
            }
            bool On(int i, int j) => i >= -P && j >= -P && i < nx + P && j < nz + P && flag[i + P, j + P];
            int OnCount(int i, int j, int r) { int c = 0; for (int a = -r; a < r; a++) for (int b = -r; b < r; b++) if (On(i + a, j + b)) c++; return c; }
            var cache = new Dictionary<long, Vector3>();
            long Key(int i, int j) => ((long)i << 32) ^ (uint)j;
            Vector3 Vt(int i, int j)
            {
                long key = Key(i, j); if (cache.TryGetValue(key, out var cv)) return cv;
                float x = R.xMin + i * C, z = R.yMin + j * C; int gx = Mathf.RoundToInt(x * 10f), gz = Mathf.RoundToInt(z * 10f);
                bool inner = OnCount(i, j, 1) == 4;
                if (inner) { x += (Hash(gx, gz, 21) - .5f) * .8f; z += (Hash(gx, gz, 22) - .5f) * .8f; }
                float u = (x - tp.x) / td.size.x, v = (z - tp.z) / td.size.z;
                var nrm = td.GetInterpolatedNormal(u, v); var basep = new Vector3(x, td.GetInterpolatedHeight(u, v) + tp.y, z);
                if (!inner) cv = basep - nrm * .4f;
                else
                {
                    float amp = Sm(.3f, 1f, OnCount(i, j, 3) / 36f) * (Gorge.Contains(new Vector2(x, z)) && !Z(new Vector2(x, z)).mask ? .35f : 1f) * NearWaterCalm(new Vector2(x, z));
                    cv = basep + nrm * .35f + PushDir(nrm) * (amp * WallRelief(basep));
                }
                cache[key] = cv; return cv;
            }
            // shared corners first (to smooth by angle), then unshared output vertices
            var faces = new List<(long a, long b, long c)>();
            for (int i = 0; i < nx; i++) for (int j = 0; j < nz; j++)
            {
                if (!On(i, j)) continue;
                long k00 = Key(i, j), k10 = Key(i + 1, j), k01 = Key(i, j + 1), k11 = Key(i + 1, j + 1);
                Vt(i, j); Vt(i + 1, j); Vt(i, j + 1); Vt(i + 1, j + 1);
                if (Hash(Mathf.RoundToInt(R.xMin / C) + i, Mathf.RoundToInt(R.yMin / C) + j, 5) < .5f) { faces.Add((k00, k01, k11)); faces.Add((k00, k11, k10)); }
                else { faces.Add((k00, k01, k10)); faces.Add((k01, k11, k10)); }
            }
            if (faces.Count == 0) return 0;
            var fn = new Vector3[faces.Count]; var fa = new float[faces.Count]; var byKey = new Dictionary<long, List<int>>();
            for (int f = 0; f < faces.Count; f++)
            {
                var (a, b, c) = faces[f]; var n = Vector3.Cross(cache[b] - cache[a], cache[c] - cache[a]);
                if (n.y < 0) { n = -n; faces[f] = (a, c, b); }
                fa[f] = n.magnitude; fn[f] = fa[f] > 1e-6f ? n / fa[f] : Vector3.up;
                foreach (var k in new[] { a, b, c }) { if (!byKey.TryGetValue(k, out var l)) byKey[k] = l = new List<int>(); l.Add(f); }
            }
            float cosHard = Mathf.Cos(38f * Mathf.Deg2Rad);
            var V = new List<Vector3>(faces.Count * 3); var N = new List<Vector3>(faces.Count * 3); var T = new List<int>(faces.Count * 3); var TW = new List<int>();
            for (int f = 0; f < faces.Count; f++)
            {
                if (fa[f] < 1e-5f) continue;
                var (a, b, c) = faces[f]; var cen = (cache[a] + cache[b] + cache[c]) / 3f; var tl = WetNear(new Vector2(cen.x, cen.z)) > .45f ? TW : T;
                foreach (var k in new[] { a, b, c })
                {
                    var sum = Vector3.zero; foreach (int g in byKey[k]) if (Vector3.Dot(fn[g], fn[f]) > cosHard) sum += fn[g] * fa[g];
                    tl.Add(V.Count); V.Add(cache[k]); N.Add(sum.sqrMagnitude > 1e-8f ? sum.normalized : fn[f]);
                }
            }
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.SetVertices(V); m.SetNormals(N); m.subMeshCount = TW.Count > 0 ? 2 : 1; m.SetTriangles(T, 0); if (TW.Count > 0) m.SetTriangles(TW, 1); m.RecalculateBounds();
            string pth = Dir + "/Meshes/" + name + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(m, pth);
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.layer = groundLayer;
            go.AddComponent<MeshFilter>().sharedMesh = m; var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = TW.Count > 0 ? new[] { rockMat, wetMat } : new[] { rockMat };
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;    // buttresses shade the wall (only within the game's 40 m shadow distance)
            go.AddComponent<MeshCollider>().sharedMesh = m;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
            return (T.Count + TW.Count) / 3;
        }

        // ================================================================================================ rock pieces: big blocks along the walls, boulders piled at the feet / rims (combined per 64 m tile)

        sealed class Item { public string name; public Mesh mesh; public Matrix4x4 local; public Bounds bounds; }
        static readonly Dictionary<string, Item> Items = new();
        static readonly string[] BigRocks = { "Boulder_1", "Boulder_2", "Boulder_4" }, SmallRocks = { "Boulder_3", "Boulder_5", "Boulder_6", "Boulder_2" };
        static readonly Dictionary<long, List<CombineInstance>> Tiles = new();

        static Item ItemOf(string name)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/VadimLocal/Forest/Models/" + name + ".fbx"); if (!model) throw new System.Exception("forest kit model missing: " + name);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model); inst.transform.position = Vector3.zero; inst.transform.rotation = Quaternion.identity; inst.transform.localScale = Vector3.one;
            var mf = inst.GetComponentInChildren<MeshFilter>();
            var it = new Item { name = name, mesh = mf.sharedMesh, local = mf.transform.localToWorldMatrix };
            Object.DestroyImmediate(inst);
            var b = new Bounds(); bool first = true;
            foreach (var v in it.mesh.vertices) { var w = it.local.MultiplyPoint3x4(v); if (first) { b = new Bounds(w, Vector3.zero); first = false; } else b.Encapsulate(w); }
            it.bounds = b; return it;
        }
        static void AddPiece(Item it, Matrix4x4 world)
        {
            var c = world.MultiplyPoint3x4(Vector3.zero); long key = ((long)Mathf.FloorToInt(c.x / 64f) << 32) ^ (uint)Mathf.FloorToInt(c.z / 64f);
            if (!Tiles.TryGetValue(key, out var l)) Tiles[key] = l = new List<CombineInstance>();
            for (int s = 0; s < it.mesh.subMeshCount; s++) l.Add(new CombineInstance { mesh = it.mesh, subMeshIndex = s, transform = world * it.local });
        }
        static int BuildTiles(string name, Transform parent, bool shadows)
        {
            int n = 0, tris = 0;
            foreach (var kv in Tiles)
            {
                var m = new Mesh { name = $"{name}_{n}", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
                m.CombineMeshes(kv.Value.ToArray(), true, true); m.RecalculateBounds();
                string pth = Dir + "/Meshes/" + m.name + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(m, pth);
                var go = new GameObject(m.name); go.transform.SetParent(parent, false); go.layer = groundLayer;
                go.AddComponent<MeshFilter>().sharedMesh = m; var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = rockMat;
                mr.shadowCastingMode = shadows ? UnityEngine.Rendering.ShadowCastingMode.On : UnityEngine.Rendering.ShadowCastingMode.Off;
                go.AddComponent<MeshCollider>().sharedMesh = m;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                n++; tris += (int)(m.GetIndexCount(0) / 3);
            }
            Tiles.Clear(); return tris;
        }

        /// <summary>Rock blocks merged into the walls: a few huge (9-15 m), some large (5-9 m), more medium (2.5-5 m); stretched up 1.1-1.7x,
        /// turned to the wall with varied tilt, set into the sculpted skin surface so only their outer half shows (no stuck-on boxes).
        /// None in the narrow gorge (the stream stays open).</summary>
        static void WallBlocks()
        {
            var cand = new List<Vector2>();
            for (float z = Area.yMin + 1f; z < Area.yMax - 1f; z += 2f) for (float x = Area.xMin + 1f; x < Area.xMax - 1f; x += 2f)
            {
                var p = new Vector2(x + RRange(-.9f, .9f), z + RRange(-.9f, .9f));
                if (!Z(p).mask || Gorge.Contains(p) || Z(p).prot > .3f) continue;
                if (Slope(p) < 46f || NewY(p) < .5f || InWater(p, 3f)) continue;
                cand.Add(p);
            }
            for (int i = cand.Count - 1; i > 0; i--) { int j = Rng.Next(i + 1); (cand[i], cand[j]) = (cand[j], cand[i]); }
            var placed = new List<(Vector3 c, float r)>(); var grid = new Dictionary<long, List<int>>(); int count = 0, huge = 0, large = 0;
            bool FreeB(Vector3 q, float r)
            {
                int cx = Mathf.FloorToInt(q.x / 16f), cz = Mathf.FloorToInt(q.z / 16f);
                for (int a = cx - 1; a <= cx + 1; a++) for (int b = cz - 1; b <= cz + 1; b++)
                    if (grid.TryGetValue(((long)a << 32) ^ (uint)b, out var l)) foreach (int k in l) { float rr = Mathf.Max(r, placed[k].r) * .8f; if ((placed[k].c - q).sqrMagnitude < rr * rr) return false; }
                return true;
            }
            foreach (var p in cand)
            {
                if (count >= 520) break;
                float u = (p.x - tp.x) / td.size.x, v = (p.y - tp.z) / td.size.z;
                var n = td.GetInterpolatedNormal(u, v); var c = new Vector3(p.x, NewY(p), p.y);
                float roll = R01(); float size = roll < .15f ? RRange(9f, 15f) : RRange(5.5f, 9f);
                if (!FreeB(c, size)) continue;
                var it = Items[BigRocks[Rng.Next(BigRocks.Length)]];
                var dir = PushDir(n); var hz = new Vector3(dir.x, 0, dir.z); if (hz.sqrMagnitude < 1e-4f) hz = Vector3.forward; hz.Normalize();
                var rot = Quaternion.AngleAxis(RRange(-4f, 14f), Vector3.Cross(Vector3.up, hz)) * Quaternion.LookRotation(hz) * Quaternion.Euler(RRange(-10f, 10f), RRange(-40f, 40f), RRange(-12f, 12f));
                var b = it.bounds; float sx = size / Mathf.Max(.1f, b.size.x), sz = size * RRange(.6f, .9f) / Mathf.Max(.1f, b.size.z), sy = Mathf.Min(size * RRange(1.1f, 1.7f), 16f) / Mathf.Max(.1f, b.size.y);
                float depth = b.size.z * sz;
                var surf = c + n * .35f + dir * WallRelief(c);                       // the sculpted skin surface here
                var target = surf - dir * (depth * RRange(.48f, .68f));             // most of the block inside the wall: it reads as part of the rock
                var pos = target - rot * new Vector3(b.center.x * sx, b.center.y * sy, b.center.z * sz);
                float top = target.y + sy * b.size.y * .5f, rim = -1e9f;
                for (int a = 0; a < 8; a++) { float ang = a * Mathf.PI / 4f; foreach (float rr in new[] { size * .6f, size * 1.2f }) rim = Mathf.Max(rim, NewY(p + new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)) * rr)); }
                if (top > rim - .6f || NearWaterCalm(p) < .6f) continue;   // the wall top stays the wall's own line
                AddPiece(it, Matrix4x4.TRS(pos, rot, new Vector3(sx, sy, sz)));
                placed.Add((c, size)); long key = ((long)Mathf.FloorToInt(c.x / 16f) << 32) ^ (uint)Mathf.FloorToInt(c.z / 16f);
                if (!grid.TryGetValue(key, out var gl)) grid[key] = gl = new List<int>(); gl.Add(placed.Count - 1); count++;
                if (size >= 9f) huge++; else if (size >= 5f) large++;
            }
            var parent = new GameObject("RockBlocks_mountain").transform; parent.SetParent(mRoot, false);
            int tris = BuildTiles("RockBlocks_mountain", parent, true);
            log.AppendLine($"wall blocks: {count} set into the walls ({huge} huge, {large} large, {count - huge - large} medium; {tris} tris, combined per 64 m tile)");
        }

        static readonly List<(Vector2 p, float r)> RockSpots = new();
        static int rockCount, rockGroups;
        static bool RockFree(Vector2 p, float r) { foreach (var q in RockSpots) if ((q.p - p).sqrMagnitude < (q.r + r) * (q.r + r)) return false; return true; }
        static Vector2 Random2() { float a = R01() * 6.283f, r = Mathf.Sqrt(R01()); return new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r; }

        /// <summary>One boulder on the ground: on the lowest ground under its footprint, sunk 15-30 % (never floating on a slope).</summary>
        static void PlaceRock(Item it, Vector2 p, float yaw, float scale, float sink)
        {
            var rot = Quaternion.Euler(RRange(-10f, 10f), yaw, RRange(-10f, 10f));
            var b = it.bounds; float hgt = b.size.y * scale; float lo = 1e9f, hi = -1e9f;
            foreach (var o in new[] { new Vector2(0, 0), new Vector2(b.min.x, b.min.z), new Vector2(b.max.x, b.min.z), new Vector2(b.min.x, b.max.z), new Vector2(b.max.x, b.max.z) })
            {
                var w = rot * new Vector3(o.x * scale, 0, o.y * scale); float y = NewY(p + new Vector2(w.x, w.z)); lo = Mathf.Min(lo, y); hi = Mathf.Max(hi, y);
            }
            AddPiece(it, Matrix4x4.TRS(new Vector3(p.x, lo - b.min.y * scale - sink * hgt - (hi - lo) * .15f, p.y), rot, Vector3.one * scale));
        }

        static void RockGroup(Vector2 c, float mainScale, int n)
        {
            int made = 0;
            for (int k = 0; k < n; k++)
            {
                string nm = k == 0 ? BigRocks[Rng.Next(BigRocks.Length)] : SmallRocks[Rng.Next(SmallRocks.Length)];
                var it = Items[nm]; float sc = k == 0 ? mainScale : mainScale * RRange(.3f, .65f) * (nm == "Boulder_6" || nm == "Boulder_3" ? 1.8f : 1f);
                float rad = Mathf.Max(it.bounds.size.x, it.bounds.size.z) * sc * .5f;
                var p = k == 0 ? c : c + Random2() * (mainScale * 1.7f + rad);
                var z = Z(p); if (!z.mask || z.prot > .2f || NewY(p) < .3f) continue;
                if (Slope(p) > 38f || InWater(p, .8f) || !Free(p, .8f)) continue;
                if (!RockFree(p, rad * .7f)) continue;
                PlaceRock(it, p, RRange(0, 360), sc, RRange(.15f, .3f));
                RockSpots.Add((p, rad * .8f)); rockCount++; made++;
            }
            if (made > 0) rockGroups++;
        }

        /// <summary>Is there a wall (steep, higher ground) within `r` m uphill of p, or a drop (steep, lower) within `r` m - the foot / the rim.</summary>
        static bool NearWall(Vector2 p, float r, bool above)
        {
            float y = NewY(p);
            for (int a = 0; a < 10; a++)
            {
                float ang = a * Mathf.PI / 5f; var q = p + new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)) * r;
                if (Slope(q) > 42f && (above ? NewY(q) > y + 1.2f : NewY(q) < y - 1.2f)) return true;
            }
            return false;
        }

        static void Boulders()
        {
            foreach (var n in BigRocks.Concat(SmallRocks).Distinct()) Items[n] = ItemOf(n);
            WallBlocks();
            RockSpots.Clear(); rockCount = 0; rockGroups = 0;
            var centres = new Dictionary<long, List<Vector2>>();
            bool Far(Vector2 p, float d)
            {
                int cx = Mathf.FloorToInt(p.x / 16f), cz = Mathf.FloorToInt(p.y / 16f);
                for (int a = cx - 1; a <= cx + 1; a++) for (int b = cz - 1; b <= cz + 1; b++)
                    if (centres.TryGetValue(((long)a << 32) ^ (uint)b, out var l)) foreach (var q in l) if ((q - p).sqrMagnitude < d * d) return false;
                return true;
            }
            void Mark(Vector2 p) { long k = ((long)Mathf.FloorToInt(p.x / 16f) << 32) ^ (uint)Mathf.FloorToInt(p.y / 16f); if (!centres.TryGetValue(k, out var l)) centres[k] = l = new List<Vector2>(); l.Add(p); }
            int foot = 0, rim = 0, band = 0;
            for (int tries = 0; tries < 160000 && foot < 520; tries++)
            {   // piled at every wall foot (scree)
                var p = new Vector2(RRange(Area.xMin, Area.xMax), RRange(Area.yMin, Area.yMax)); var z = Z(p);
                if (!z.mask || z.prot > .1f || NewY(p) < .8f) continue;
                if (Slope(p) > 33f || !NearWall(p, 3.2f, true) || !Far(p, 8.5f)) continue;
                Mark(p); RockGroup(p, RRange(.9f, 2.1f), Rng.Next(3, 8)); foot++;
            }
            for (int tries = 0; tries < 80000 && rim < 170; tries++)
            {   // on the shelf edges (rims)
                var p = new Vector2(RRange(Area.xMin, Area.xMax), RRange(Area.yMin, Area.yMax)); var z = Z(p);
                if (!z.mask || z.prot > .1f || z.w < .5f) continue;
                if (Slope(p) > 26f || !NearWall(p, 3f, false) || !Free(p, 1.2f) || !Far(p, 13f)) continue;
                Mark(p); RockGroup(p, RRange(.7f, 1.5f), Rng.Next(3, 6)); rim++;
            }
            for (int tries = 0; tries < 60000 && band < 60; tries++)
            {   // the foot band into the fields
                var p = new Vector2(RRange(Area.xMin, Area.xMax), RRange(Area.yMin, Area.yMax)); var z = Z(p);
                if (!z.mask || z.prot > .1f || z.scree < .45f || Slope(p) > 30f || NewY(p) < 1f || !Far(p, 15f)) continue;
                Mark(p); RockGroup(p, RRange(1.1f, 2.2f), Rng.Next(3, 8)); band++;
            }
            var parent = new GameObject("Boulders_mountain").transform; parent.SetParent(mRoot, false);
            int tris = BuildTiles("Boulders_mountain", parent, true);
            log.AppendLine($"boulders: {rockCount} in {rockGroups} groups ({foot} at wall feet, {rim} on rims, {band} in the foot band; {tris} tris combined per tile)");
        }

        // ================================================================================================ trees: dense conifers on every shelf (forest kit v02 prefabs)

        static readonly string[] TreeNames = { "Fir_Young", "Fir_Mid", "Fir_Big", "Fir_Old", "Pine_18", "Pine_20", "Pine_25", "Birch" };
        static readonly List<(Vector2 p, float r)> Placed = new();
        static readonly Dictionary<long, List<int>> PlacedHash = new();
        static long HKey(int x, int z) => ((long)x << 32) ^ (uint)z;
        static bool Free(Vector2 p, float r)
        {
            int cx = Mathf.FloorToInt(p.x / 4f), cz = Mathf.FloorToInt(p.y / 4f), rr = Mathf.CeilToInt(r / 4f) + 1;
            for (int x = cx - rr; x <= cx + rr; x++) for (int z = cz - rr; z <= cz + rr; z++)
                if (PlacedHash.TryGetValue(HKey(x, z), out var l)) foreach (int i in l) { float m = Mathf.Min(r, Placed[i].r); if ((Placed[i].p - p).sqrMagnitude < m * m) return false; }
            return true;
        }
        static void AddPlaced(Vector2 p, float r)
        {
            Placed.Add((p, r)); long k = HKey(Mathf.FloorToInt(p.x / 4f), Mathf.FloorToInt(p.y / 4f));
            if (!PlacedHash.TryGetValue(k, out var l)) PlacedHash[k] = l = new List<int>(); l.Add(Placed.Count - 1);
        }
        /// <summary>A trunk must stand on its shelf: the ground round it within ~1.5 m is not a wall.</summary>
        static bool Footing(Vector2 p)
        {
            for (int a = 0; a < 6; a++) { float ang = a * Mathf.PI / 3f; if (Slope(p + new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)) * 1.6f) > 32f) return false; }
            return true;
        }

        static void Trees()
        {
            var protos = td.treePrototypes.ToList(); var idx = new int[TreeNames.Length];
            for (int s = 0; s < TreeNames.Length; s++)
            {
                int f = protos.FindIndex(pr => pr.prefab && pr.prefab.name == "FK_" + TreeNames[s]);
                if (f < 0)
                {
                    var pf = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/VadimLocal/Forest/Prefabs/FK_" + TreeNames[s] + ".prefab");
                    if (!pf) throw new System.Exception("forest kit prefab missing: FK_" + TreeNames[s]);
                    protos.Add(new TreePrototype { prefab = pf, bendFactor = 0f }); f = protos.Count - 1;
                }
                idx[s] = f;
            }
            if (protos.Count != td.treePrototypes.Length) { td.treePrototypes = protos.ToArray(); td.RefreshPrototypes(); }
            var trees = td.treeInstances.ToList(); int removed = 0, reseated = 0;
            Placed.Clear(); PlacedHash.Clear();
            for (int k = trees.Count - 1; k >= 0; k--)
            {
                var ti = trees[k]; var p = new Vector2(tp.x + ti.position.x * td.size.x, tp.z + ti.position.z * td.size.z);
                if (p.x < Area.xMin || p.x > Area.xMax || p.y < Area.yMin || p.y > Area.yMax) continue;
                var z = Z(p);
                if (z.mask && (z.w > .08f || Slope(p) > 30f || Mathf.Abs(NewY(p) - OldY(p)) > .4f)) { trees.RemoveAt(k); removed++; continue; }
                float ny = (NewY(p) - tp.y) / td.size.y;
                if (Mathf.Abs(ny - ti.position.y) * td.size.y > .02f) { ti.position = new Vector3(ti.position.x, ny, ti.position.z); trees[k] = ti; reseated++; }
                if (z.mask || NearMask(p, 6f)) AddPlaced(p, 3f);
            }
            var cand = new List<Vector2>();
            for (float z = Area.yMin + 1f; z < Area.yMax - 1f; z += 1.3f) for (float x = Area.xMin + 1f; x < Area.xMax - 1f; x += 1.3f)
                if (Z(new Vector2(x, z)).mask) cand.Add(new Vector2(x + RRange(-.6f, .6f), z + RRange(-.6f, .6f)));
            for (int i = cand.Count - 1; i > 0; i--) { int j = Rng.Next(i + 1); (cand[i], cand[j]) = (cand[j], cand[i]); }
            var count = new int[TreeNames.Length]; int added = 0;
            foreach (var p in cand)
            {
                var z = Z(p); if (z.prot > .15f || z.w < .15f) continue;
                if (InWater(p, 2.2f)) continue;
                float st = Slope(p); if (st > 27f) continue;
                float y = NewY(p); if (y < 1.2f) continue;
                if (z.peak > .6f && st > 20f) continue;
                if (!Footing(p)) continue;
                float n1 = Mathf.PerlinNoise(p.x / 37f + 3.1f, p.y / 37f + 7.7f), n3 = Mathf.PerlinNoise(p.x / 19f + 5.3f, p.y / 19f + 1.9f);
                float clear = Sm(.6f, .72f, n1);                                    // the same clearings as the splat (grass)
                // density: dense forest on the shelves, thinning on the scree and towards the foot (sparse trees into the fields)
                float dens = (1f - clear * .85f) * (1f - z.scree * .8f) * Mathf.Lerp(.25f, 1f, Sm(.15f, .7f, z.w));
                if (R01() > dens) continue;
                float r = Mathf.Lerp(2.3f, 3.1f, n3) / Mathf.Max(.45f, dens);
                if (!Free(p, r)) continue;
                // species: firs and tall pines close together, a few young firs at the edges, rare birches low down
                float pineN = Mathf.PerlinNoise(p.x / 44f + 11f, p.y / 44f + 3f);
                float[] w = { 8f + 14f * z.scree + 10f * clear, 20f, 17f, 11f, 8f, 9f, 8f, y < 40f ? 3f : .5f };
                float pf = Mathf.Lerp(.5f, 2f, Sm(.35f, .65f, pineN)); for (int s = 4; s <= 6; s++) w[s] *= pf;
                // Vadim 28.10: from the Hutor the walls above must read - near a rim only young / mid firs, sparse; tall pines from ~20 m back
                int rimBand = NearWall(p, 5f, false) ? 0 : NearWall(p, 11f, false) ? 1 : NearWall(p, 19f, false) ? 2 : 3;
                bool edge = rimBand < 2 || NearWall(p, 6f, true);
                if (rimBand == 0 && R01() < .55f) continue;
                if (rimBand <= 1) { w[0] *= 4f; w[2] = 0f; w[3] = 0f; for (int s = 4; s <= 7; s++) w[s] = 0f; if (rimBand == 0) w[1] = 0f; }
                else if (rimBand == 2) { w[3] *= .4f; for (int s = 5; s <= 6; s++) w[s] *= .15f; }
                else if (edge) { w[0] *= 2.5f; w[2] *= .35f; w[3] *= .35f; for (int s = 4; s <= 6; s++) w[s] *= .12f; }
                float tot = w.Sum(), pick = R01() * tot; int spc = 0; for (; spc < w.Length - 1; spc++) { pick -= w[spc]; if (pick <= 0f) break; }
                float scale = spc == 0 ? RRange(.75f, 1.25f) : RRange(.85f, 1.2f); if (edge) scale *= .82f; if (rimBand == 0) scale *= .85f;
                float nx = (p.x - tp.x) / td.size.x, nz = (p.y - tp.z) / td.size.z;
                trees.Add(new TreeInstance { position = new Vector3(nx, (y - .05f - tp.y) / td.size.y, nz), prototypeIndex = idx[spc], widthScale = scale * RRange(.93f, 1.07f), heightScale = scale, rotation = R01() * 6.283f, color = Color.white, lightmapColor = Color.white });
                AddPlaced(p, r); count[spc]++; added++;
            }
            td.SetTreeInstances(trees.ToArray(), true);
            log.AppendLine($"trees: removed {removed} old in the massif, re-seated {reseated}, added {added} kit trees: " + string.Join(", ", TreeNames.Select((n, i) => n + " " + count[i])) + $"; terrain total {td.treeInstanceCount}");
            treesAdded = added;
        }
        static int treesAdded;

        // ================================================================================================ water: the waterfall cascades (filled in step 2)

        static Vector2 Spring, Pool; static float SpringY, PoolY, SpringR, PoolR; static List<Vector2> Casc, Brook, LowerSteps; static float[] BrookSurf;

        static float PolyDist(Vector2 p, List<Vector2> pl)
        {
            float d = 1e9f;
            for (int i = 0; i + 1 < pl.Count; i++) { var ab = pl[i + 1] - pl[i]; float l2 = ab.sqrMagnitude; float t = l2 < 1e-6f ? 0f : Mathf.Clamp01(Vector2.Dot(p - pl[i], ab) / l2); d = Mathf.Min(d, (p - (pl[i] + ab * t)).magnitude); }
            return d;
        }
        /// <summary>On (or within `margin` of) the new spring / cascade / pool / brook.</summary>
        static bool InWater(Vector2 p, float margin)
        {
            if (Casc == null) return false;
            if (p.x < 470f || p.x > 512f || p.y < 755f || p.y > 870f) return false;
            return (p - Spring).magnitude < SpringR + margin || (p - Pool).magnitude < PoolR + margin || PolyDist(p, Casc) < 2f + margin || PolyDist(p, Brook) < 1.3f + margin;
        }

        static void LoadWater()
        {
            var d = new Dictionary<string, float[]>();
            foreach (var raw in File.ReadAllLines(Dir + "/Data/mountain_water_v01.txt"))
            {
                var t = raw.Trim().Split(' '); if (t.Length < 2) continue;
                d[t[0]] = t.Skip(1).Select(v => float.Parse(v, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
            }
            List<Vector2> Pts(float[] a) { var l = new List<Vector2>(); for (int i = 0; i + 1 < a.Length; i += 2) l.Add(new Vector2(a[i], a[i + 1])); return l; }
            Spring = new Vector2(d["spring"][0], d["spring"][1]); SpringY = d["spring"][2]; SpringR = d["spring"][3];
            Pool = new Vector2(d["pool"][0], d["pool"][1]); PoolY = d["pool"][2]; PoolR = d["pool"][3];
            Casc = Pts(d["cascade"]); Brook = Pts(d["brook"]); BrookSurf = d["brook_surf"]; LowerSteps = d.TryGetValue("lower_steps", out var ls) ? Pts(ls) : null;
        }

        static Mesh SaveMesh(string name, List<Vector3> v, List<Vector2> uv, List<int> t, List<Vector2> uv1 = null, List<Color> col = null)
        {
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.SetVertices(v); if (uv != null) m.SetUVs(0, uv); if (uv1 != null) m.SetUVs(1, uv1); if (col != null) m.SetColors(col); m.SetTriangles(t, 0);
            m.RecalculateNormals(); m.RecalculateBounds(); if (uv != null) m.RecalculateTangents();
            string path = Dir + "/Meshes/" + name + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }
        static GameObject MeshGo(string name, Transform parent, Mesh mesh, Material mat)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.layer = groundLayer;
            go.AddComponent<MeshFilter>().sharedMesh = mesh; var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return go;
        }
        static Mesh Disc(string name, Vector2 c, float r, float y)
        {
            var v = new List<Vector3> { new Vector3(c.x, y, c.y) }; var uv = new List<Vector2> { c / 10f }; var uv1 = new List<Vector2> { Vector2.zero }; var t = new List<int>();
            int n = 28;
            for (int k = 0; k < n; k++)
            {
                float a = k * Mathf.PI * 2f / n, rr = r * (1f + .08f * Mathf.Sin(k * 2.3f) + .05f * Mathf.Cos(k * 4.1f));
                var p = c + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * rr; v.Add(new Vector3(p.x, y, p.y)); uv.Add(p / 10f); uv1.Add(Vector2.zero);
                t.AddRange(new[] { 0, 1 + (k + 1) % n, 1 + k });
            }
            return SaveMesh(name, v, uv, t, uv1);
        }
        /// <summary>The v05 shader's FoamSplash mode: a quad with radial UV (0..1, centre 0.5), white vertex colour.</summary>
        static void Splash(Transform parent, string name, Vector2 c, float y, float r, Material mat)
        {
            var v = new List<Vector3> { new Vector3(c.x - r, y, c.y - r), new Vector3(c.x - r, y, c.y + r), new Vector3(c.x + r, y, c.y + r), new Vector3(c.x + r, y, c.y - r) };
            var uv = new List<Vector2> { new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0) };
            MeshGo(name, parent, SaveMesh(name, v, uv, new List<int> { 0, 1, 2, 0, 2, 3 }, null, Enumerable.Repeat(Color.white, 4).ToList()), mat);
        }
        static void FoamRing(Transform parent, string name, Vector2 foot, Vector2 dir, float y, Material mat, float sx = 4.5f, float sz = 3.5f)
        {
            Vector2 r = new Vector2(dir.y, -dir.x);
            Vector2 a = foot - r * sx - dir * sz, b = foot + r * sx - dir * sz, c = foot + r * sx + dir * sz, d = foot - r * sx + dir * sz;
            var v = new List<Vector3> { new Vector3(a.x, y, a.y), new Vector3(d.x, y, d.y), new Vector3(c.x, y, c.y), new Vector3(b.x, y, b.y) };
            var uv = new List<Vector2> { new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0) };
            var t = new List<int> { 0, 1, 2, 0, 2, 3 };
            var n = Vector3.Cross(v[1] - v[0], v[2] - v[0]); if (n.y < 0) t = new List<int> { 0, 2, 1, 0, 3, 2 };
            MeshGo(name, parent, SaveMesh(name, v, uv, t), mat);
        }

        /// <summary>Cheap Shuriken spray (droplets thrown up and falling back) or soft mist, culled beyond ~130 m / ~400 m by a LODGroup.</summary>
        static void Spray(Transform parent, string name, Vector3 at, float radius, bool mist, bool lod = true)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.position = at;
            var ps = go.AddComponent<ParticleSystem>(); var r = go.GetComponent<ParticleSystemRenderer>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.loop = true; main.prewarm = true; main.playOnAwake = true; main.simulationSpace = ParticleSystemSimulationSpace.World; main.scalingMode = ParticleSystemScalingMode.Hierarchy;
            var em = ps.emission; var sh = ps.shape; var col = ps.colorOverLifetime; col.enabled = true;
            var gr = new Gradient();
            if (!mist)
            {
                main.maxParticles = 45; main.startLifetime = new ParticleSystem.MinMaxCurve(.7f, 1.2f); main.startSpeed = new ParticleSystem.MinMaxCurve(2.2f, 4.2f);
                main.startSize = new ParticleSystem.MinMaxCurve(.18f, .42f); main.gravityModifier = .9f; main.startColor = new Color(1f, 1f, 1f, .9f);
                em.rateOverTime = 34f; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 38f; sh.radius = radius; sh.rotation = new Vector3(-90f, 0f, 0f);
                gr.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) }, new[] { new GradientAlphaKey(.9f, 0f), new GradientAlphaKey(.7f, .6f), new GradientAlphaKey(0f, 1f) });
            }
            else
            {
                main.maxParticles = 12; main.startLifetime = new ParticleSystem.MinMaxCurve(3f, 4.5f); main.startSpeed = new ParticleSystem.MinMaxCurve(.3f, .8f);
                main.startSize = new ParticleSystem.MinMaxCurve(radius * 1.1f, radius * 1.9f); main.gravityModifier = -.015f; main.startColor = new Color(1f, 1f, 1f, .5f);
                main.startRotation = new ParticleSystem.MinMaxCurve(0f, 6.28f);
                em.rateOverTime = 3.2f; sh.shapeType = ParticleSystemShapeType.Circle; sh.radius = radius; sh.rotation = new Vector3(-90f, 0f, 0f);
                gr.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) }, new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(.55f, .3f), new GradientAlphaKey(0f, 1f) });
            }
            col.color = new ParticleSystem.MinMaxGradient(gr);
            r.renderMode = ParticleSystemRenderMode.Billboard; r.sharedMaterial = mist ? mistMat : sprayMat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false; r.maxParticleSize = mist ? 1f : .3f;
            if (lod) { var lg = go.AddComponent<LODGroup>(); lg.SetLODs(new[] { new LOD(mist ? .025f : .045f, new Renderer[] { r }) }); lg.size = mist ? radius * 4f : radius * 2f + 3f; }
            ps.Play();
        }

        // ------------------------------------------------------------------------------------------------ live falls (Vadim 28.10)

        static Material ChurnMaterial(Material splash)
        {
            string p = Dir + "/Materials/MT_foam_churn.mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (!m) { m = new Material(splash) { name = "MT_foam_churn" }; AssetDatabase.CreateAsset(m, p); }
            m.shader = splash.shader; m.CopyPropertiesFromMaterial(splash); m.shaderKeywords = splash.shaderKeywords;
            if (m.HasProperty("_OV_SplashSpeed")) m.SetFloat("_OV_SplashSpeed", splash.GetFloat("_OV_SplashSpeed") * 1.9f);
            m.renderQueue = splash.renderQueue + 1; EditorUtility.SetDirty(m); return m;
        }

        /// <summary>The stream layers' materials: copies of the mountain waterfall material (Vadim's water textures / colours), tuned per layer and
        /// length. kind 0 = core (darker, translucent, fast scroll, slow big wobble), 1 = shell (aerated white, faster, different noise scale,
        /// fast shimmer), 2 = edge streaks (thin white, fastest, mid wobble) - three wobble frequencies together.</summary>
        /// <summary>Wet stone right round the falls: the same grey ~25 % darker, a little glossy (skins and the terrain layer).</summary>
        /// <summary>No self-light on the stone (an emission left on it turned shaded rock white in a fresh session).</summary>
        static void NoGlow(Material m) { m.SetColor("_EmissionColor", Color.black); m.DisableKeyword("_EMISSION"); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack; EditorUtility.SetDirty(m); }
        static Material WetMaterial() { var c = StoneColor * .75f; c.a = 1f; var m = Lit("MT_stone_wet", c, null, .32f); NoGlow(m); return m; }
        static TerrainLayer WetLayer() { var c = TerrainStone * .75f; c.a = 1f; return Layer("TL_stone_wet", PlainStone("MT_stone_wet", c), 9f, Color.white, .32f); }

        static Material waterRef;   // the lake material: the stream takes its blue
        static Material FallMat(string name, Material src, int kind, float length)
        {
            string p = Dir + "/Materials/MT_fall_" + name + ".mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (!m) { m = new Material(src) { name = "MT_fall_" + name }; AssetDatabase.CreateAsset(m, p); }
            m.shader = src.shader; m.CopyPropertiesFromMaterial(src); m.shaderKeywords = src.shaderKeywords;
            void F(string k, float v) { if (m.HasProperty(k)) m.SetFloat(k, v); }
            void V(string k, Vector4 v) { if (m.HasProperty(k)) m.SetVector(k, v); }
            if (kind == 0)
            {
                F("_OV_FallOpacity", .93f); F("_OV_FallFoam", .16f); F("_OV_FallSpeed", 1.3f);
                V("_OV_FallTiling", new Vector4(3.3f, Mathf.Max(1f, 1.3f * length / .8f), 0, 0)); V("_OV_Wobble", new Vector4(.08f, .5f, 2.2f, 0));   // length = travel time (s): the pattern moves with the water
                // Vadim 28.10: the stream is blue water - the lake / river colour; its streaks are only lighter blue (no white along the fall)
                var wr = waterRef ? waterRef : src;
                Color sh = wr.HasProperty("_Color_Shallow") ? wr.GetColor("_Color_Shallow") : src.GetColor("_Color_Shallow"), dp = wr.HasProperty("_Color_Deep") ? wr.GetColor("_Color_Deep") : sh * .6f;
                var blue = Color.Lerp(sh, dp, .35f); blue.a = 1f; if (m.HasProperty("_Color_Shallow")) m.SetColor("_Color_Shallow", blue);
                var hi = Color.Lerp(sh, Color.white, .22f); hi.a = .5f; if (m.HasProperty("_OV_FoamColor")) m.SetColor("_OV_FoamColor", hi);
            }
            else if (kind == 1)
            {
                F("_OV_FallOpacity", .05f); F("_OV_FallFoam", 1.35f); F("_OV_FallSpeed", 2.0f);
                V("_OV_FallTiling", new Vector4(2.9f, Mathf.Max(1.5f, length / 2.6f), 0, 0)); V("_OV_Wobble", new Vector4(.05f, 2.3f, 8f, 0));
            }
            else
            {
                F("_OV_FallOpacity", .22f); F("_OV_FallFoam", 2f); F("_OV_FallSpeed", 2.5f);
                V("_OV_FallTiling", new Vector4(1f, Mathf.Max(2f, length / 1.8f), 0, 0)); V("_OV_Wobble", new Vector4(.06f, 1.1f, 4.2f, 0));
            }
            F("_Cull", kind == 0 ? 2f : 0f);   // the core is a closed body: outward faces only, never two layers of itself
            m.renderQueue = (waterRef ? waterRef.renderQueue : src.renderQueue) + 1 + kind;   // right after the river / pools, before the foam
            EditorUtility.SetDirty(m); return m;
        }

        /// <summary>One fall step: along the ledge / brook to the lip, a rounded curl up and over the edge, then a free fall that leaves the lip
        /// level and bows away from the wall (even forward, accelerating down).</summary>
        static List<Vector3> FallArc(Vector3 start, Vector3 lip, Vector3 foot, int nf = 16, float bump = 0f)
        {
            var c = new List<Vector3>(); int na = Mathf.Max(1, Mathf.CeilToInt((lip - start).magnitude / .3f));
            for (int q = 0; q < na; q++) c.Add(Vector3.Lerp(start, lip, q / (float)na));
            for (int q = 0; q <= nf; q++)
            {
                float t = q / (float)nf; var h = Vector3.Lerp(new Vector3(lip.x, 0, lip.z), new Vector3(foot.x, 0, foot.z), t);
                float y = lip.y - (lip.y - foot.y) * t * t + bump * Mathf.Sin(Mathf.Clamp01(t * 3f) * Mathf.PI);
                c.Add(new Vector3(h.x, y, h.z));
            }
            return c;
        }

        /// <summary>One fall as ONE closed body of water (Vadim 28.10 #2). Every section is a flattened, rounded loop: the front bulges hf[k] out
        /// along o, the back reaches hb[k] behind it (into the rock / down to the river bed), full width w[k] (the river / pool outlet it leaves).
        /// Outward faces only (Cull Back): from any side - front, sides, below, behind - it reads as solid water, never an open shell, and never
        /// shows two layers of itself. Vertex alpha: a[k] per section (fade-in on the water it leaves; the side edges fade there too) and, from
        /// section kEnd on, below `waterY` (the stream sinks into the pool it enters and fades out under its surface). V follows the travel
        /// time (slow on the flat like the river, fast on the drops), so the pattern moves with the water; only the last stretch round the
        /// waterline gets V &lt; .2, which the shader whitens (foam at the foot only).</summary>
        static void Stream(Transform parent, string name, List<Vector3> c, List<Vector3> o, List<float> w, List<float> hf, List<float> hb, List<float> a, int kEnd, float waterY, Material src)
        {
            int n = c.Count, M = 24;
            var fw = new Vector3[n]; var W = new float[n];
            for (int k = 0; k < n; k++) fw[k] = (c[Mathf.Min(k + 1, n - 1)] - c[Mathf.Max(k - 1, 0)]).normalized;
            for (int k = 1; k < n; k++) { float sp = Mathf.Lerp(1.4f, 8f, Sm(.2f, .9f, Mathf.Abs(fw[k].y))); W[k] = W[k - 1] + (c[k] - c[k - 1]).magnitude / sp; }
            int k06 = n - 2, k0 = n - 1;
            for (int k = Mathf.Clamp(kEnd, 0, n - 1); k < n; k++) if (c[k].y + hf[k] <= waterY + .6f) { k06 = Mathf.Max(1, k); break; }
            for (int k = k06; k < n; k++) if (c[k].y <= waterY) { k0 = k; break; }
            if (k0 <= k06) k0 = Mathf.Min(n - 1, k06 + 1);
            var Vs = new float[n];
            for (int k = 0; k < n; k++)
            {
                if (k <= k06) Vs[k] = .2f + .8f * (1f - W[k] / Mathf.Max(W[k06], .01f));
                else if (k <= k0) Vs[k] = Mathf.Lerp(.2f, .1f, (W[k] - W[k06]) / Mathf.Max(W[k0] - W[k06], .001f));
                else Vs[k] = Mathf.Lerp(.1f, 0f, (W[k] - W[k0]) / Mathf.Max(W[n - 1] - W[k0], .001f));
            }
            var mat = FallMat(name + "_core", src, 0, W[k06]);
            var V = new List<Vector3>(); var UV = new List<Vector2>(); var Cl = new List<Color>(); var T = new List<int>();
            var mids = new List<Vector3>();
            for (int k = 0; k < n; k++)
            {
                var nrm = o[k] - fw[k] * Vector3.Dot(o[k], fw[k]); nrm = nrm.sqrMagnitude > 1e-4f ? nrm.normalized : o[k];
                var side = Vector3.Cross(nrm, fw[k]); if (side.sqrMagnitude < 1e-4f) side = Vector3.Cross(Vector3.up, nrm); side.Normalize();
                mids.Add(c[k] + nrm * ((hf[k] - hb[k]) * .5f));
                for (int j = 0; j <= M; j++)
                {   // back centre -> one side -> front -> other side -> back centre (a squarish superellipse: flat front, rounded sides)
                    float th = -Mathf.PI * .5f + 2f * Mathf.PI * j / M, cx = Mathf.Cos(th), sy = Mathf.Sin(th);
                    float x = Mathf.Sign(cx) * Mathf.Pow(Mathf.Abs(cx), .6f), y = Mathf.Sign(sy) * Mathf.Pow(Mathf.Abs(sy), .6f);
                    var p = c[k] + side * (x * w[k] * .5f) + nrm * (y > 0f ? y * hf[k] : y * hb[k]);
                    float al = a[k] * Mathf.Lerp(1f - Sm(.55f, 1f, Mathf.Abs(x)), 1f, a[k]);
                    if (k >= kEnd && p.y < waterY) al *= Mathf.Clamp01(1f - (waterY - p.y) / .7f);
                    V.Add(p); UV.Add(new Vector2(.07f + .86f * j / M, Vs[k])); Cl.Add(new Color(1f, 1f, 1f, al));
                }
                if (k > 0) for (int j = 0; j < M; j++) { int i0 = (k - 1) * (M + 1) + j, i1 = k * (M + 1) + j; T.AddRange(new[] { i0, i1, i1 + 1, i0, i1 + 1, i0 + 1 }); }
            }
            // faces outward: test one front quad in the middle against its section centre, flip all if needed
            int km = Mathf.Clamp(n / 2, 1, n - 1), jm = M / 4 + M / 8, q0 = (km - 1) * (M + 1) + jm, q1 = km * (M + 1) + jm;
            var fn = Vector3.Cross(V[q1] - V[q0], V[q1 + 1] - V[q0]);
            if (Vector3.Dot(fn, V[q0] - mids[km]) < 0f) for (int k = 0; k < T.Count; k += 3) (T[k + 1], T[k + 2]) = (T[k + 2], T[k + 1]);
            string nm = name + "_core";
            MeshGo(nm, parent, SaveMesh(nm, V, UV, T, null, Cl), mat);
            log.AppendLine($"{name}: closed body, {n} sections, width {w[0]:0.00} -> {w[n - 1]:0.00} m, travel {W[k06]:0.0} s, waterline at section {k06}/{n}");
        }

        /// <summary>0..1 per path point: how steep the path runs there (0 flat, 1 falling), smoothed.</summary>
        static List<float> Steep(List<Vector3> c)
        {
            var s = new List<float>();
            for (int k = 0; k < c.Count; k++) { var f = (c[Mathf.Min(k + 1, c.Count - 1)] - c[Mathf.Max(k - 1, 0)]).normalized; s.Add(Sm(.25f, .8f, Mathf.Abs(f.y))); }
            for (int pass = 0; pass < 2; pass++) for (int k = 1; k + 1 < s.Count; k++) s[k] = (s[k - 1] + s[k] * 2f + s[k + 1]) * .25f;
            return s;
        }

        /// <summary>The river's own cross-sections (the vertex pairs of its strip mesh) up to `len` m upstream of `lip` along `up`: mid point,
        /// width, upstream distance; upstream first. The fall takes its width and centre from these (it spans the whole river).</summary>
        static List<(Vector3 mid, float w, float d)> RiverSections(Transform river, Vector3 lip, Vector3 up, float len)
        {
            var res = new List<(Vector3 mid, float w, float d)>(); var mf = river ? river.GetComponent<MeshFilter>() : null;
            if (!mf || !mf.sharedMesh || !mf.sharedMesh.isReadable) return res;
            var v = mf.sharedMesh.vertices;
            for (int i = 0; i + 1 < v.Length; i += 2)
            {
                Vector3 pa = river.TransformPoint(v[i]), pb = river.TransformPoint(v[i + 1]); var mid = (pa + pb) * .5f; float wd = (pa - pb).magnitude;
                var h = new Vector3(mid.x - lip.x, 0f, mid.z - lip.z); float d = Vector3.Dot(h, up), lat = (h - up * d).magnitude;
                if (wd > 12f || Mathf.Abs(pa.y - pb.y) > .3f || d < -1f || d > len || lat > 3f || Mathf.Abs(mid.y - lip.y) > 1.5f) continue;
                res.Add((mid, wd, d));
            }
            res.Sort((p, q) => q.d.CompareTo(p.d));
            return res;
        }

        /// <summary>The plunge pool's water carried on from its round north edge to the wall foot (the round pool stopped ~1 m short of the
        /// fall, so the fall's sides came down on dry rock): same material and height; its south edge is exactly the pool's own edge (no
        /// overlap, no gap); the terrain hides it wherever the ground stands above the water.</summary>
        static void PoolToWall(Transform parent, string name, Transform pool, float zWall)
        {
            var mf = pool ? pool.GetComponent<MeshFilter>() : null; if (!mf || !mf.sharedMesh) { log.AppendLine("pool to wall: no plunge pool"); return; }
            var vs = mf.sharedMesh.vertices.Select(q => pool.TransformPoint(q)).ToList();
            float cz = vs.Average(q => q.z), y = vs.Average(q => q.y);
            var rim = vs.Where(q => q.z >= cz - .01f).OrderBy(q => q.x).ToList();
            if (rim.Count < 2) return;
            var V = new List<Vector3>(); var uv = new List<Vector2>(); var uv1 = new List<Vector2>(); var T = new List<int>();
            foreach (var r in rim) { V.Add(new Vector3(r.x, y, r.z)); V.Add(new Vector3(r.x, y, Mathf.Max(zWall, r.z + .3f))); }
            for (int i = 0; i < V.Count; i++) { uv.Add(new Vector2(V[i].x, V[i].z) / 10f); uv1.Add(Vector2.zero); }
            for (int i = 0; i + 1 < rim.Count; i++) { int q = i * 2; T.AddRange(new[] { q, q + 1, q + 3, q, q + 3, q + 2 }); }
            for (int k = 0; k < T.Count; k += 3) { var nn = Vector3.Cross(V[T[k + 1]] - V[T[k]], V[T[k + 2]] - V[T[k]]); if (nn.y < 0) (T[k + 1], T[k + 2]) = (T[k + 2], T[k + 1]); }
            MeshGo(name, parent, SaveMesh(name, V, uv, T, uv1), pool.GetComponent<MeshRenderer>().sharedMaterial);
            log.AppendLine($"pool to wall: {rim.Count} rim points, x {rim[0].x:0.0}..{rim[rim.Count - 1].x:0.0}, up to z {zWall:0.0}, y {y:0.00}");
        }

        /// <summary>A round pool (like Disc) whose outline also takes in `extra` points (convex hull): a pool narrowing to its outlet.</summary>
        static Mesh Teardrop(string name, Vector2 c, float r, float y, Vector2[] extra)
        {
            var pts = new List<Vector2>(); int n = 28;
            for (int k = 0; k < n; k++) { float an = k * Mathf.PI * 2f / n, rr = r * (1f + .08f * Mathf.Sin(k * 2.3f) + .05f * Mathf.Cos(k * 4.1f)); pts.Add(c + new Vector2(Mathf.Cos(an), Mathf.Sin(an)) * rr); }
            pts.AddRange(extra);
            pts = pts.OrderBy(p => p.x).ThenBy(p => p.y).ToList();
            float Cr(Vector2 o0, Vector2 a0, Vector2 b0) => (a0.x - o0.x) * (b0.y - o0.y) - (a0.y - o0.y) * (b0.x - o0.x);
            var h = new List<Vector2>();
            foreach (var p in pts) { while (h.Count >= 2 && Cr(h[h.Count - 2], h[h.Count - 1], p) <= 0f) h.RemoveAt(h.Count - 1); h.Add(p); }
            int lo = h.Count + 1;
            for (int i = pts.Count - 2; i >= 0; i--) { while (h.Count >= lo && Cr(h[h.Count - 2], h[h.Count - 1], pts[i]) <= 0f) h.RemoveAt(h.Count - 1); h.Add(pts[i]); }
            h.RemoveAt(h.Count - 1);
            var ctr = Vector2.zero; foreach (var p in h) ctr += p; ctr /= h.Count;
            var v = new List<Vector3> { new Vector3(ctr.x, y, ctr.y) }; var uv = new List<Vector2> { ctr / 10f }; var uv1 = new List<Vector2> { Vector2.zero }; var t = new List<int>();
            for (int k = 0; k < h.Count; k++) { v.Add(new Vector3(h[k].x, y, h[k].y)); uv.Add(h[k] / 10f); uv1.Add(Vector2.zero); t.AddRange(new[] { 0, 1 + (k + 1) % h.Count, 1 + k }); }
            for (int k = 0; k < t.Count; k += 3) { var nn = Vector3.Cross(v[t[k + 1]] - v[t[k]], v[t[k + 2]] - v[t[k]]); if (nn.y < 0) (t[k + 1], t[k + 2]) = (t[k + 2], t[k + 1]); }
            return SaveMesh(name, v, uv, t, uv1);
        }

        /// <summary>The base foam: a copy of the splash material drawn after the stream (so the foam ring lies over the stream's foot).</summary>
        static Material BaseFoamMaterial(Material splash)
        {
            string p = Dir + "/Materials/MT_foam_base.mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (!m) { m = new Material(splash) { name = "MT_foam_base" }; AssetDatabase.CreateAsset(m, p); }
            m.shader = splash.shader; m.CopyPropertiesFromMaterial(splash); m.shaderKeywords = splash.shaderKeywords;
            m.renderQueue = (waterRef ? waterRef.renderQueue : 3000) + 2; EditorUtility.SetDirty(m); return m;
        }

        /// <summary>Bulge direction along a path: up where the water runs flat (ledge, lip), out from the wall where it falls.</summary>
        static List<Vector3> BulgeDirs(List<Vector3> c, System.Func<int, Vector3> wallOut)
        {
            var o = new List<Vector3>();
            for (int k = 0; k < c.Count; k++)
            {
                var fwd = (c[Mathf.Min(k + 1, c.Count - 1)] - c[Mathf.Max(k - 1, 0)]).normalized;
                o.Add(Vector3.Lerp(Vector3.up, wallOut(k), Sm(.25f, .8f, Mathf.Abs(fwd.y))).normalized);
            }
            for (int pass = 0; pass < 3; pass++) for (int k = 1; k + 1 < o.Count; k++) o[k] = (o[k - 1] + o[k] * 2f + o[k + 1]).normalized;   // no kinks
            return o;
        }

        /// <summary>A soft ring (white, transparent centre and rim) for the ripple rings that spread from every fall foot.</summary>
        static Texture2D RingTex()
        {
            string p = Dir + "/Textures/MT_ring.png";
            if (!File.Exists(p))
            {
                var t = new Texture2D(128, 128, TextureFormat.RGBA32, false);
                for (int y = 0; y < 128; y++) for (int x = 0; x < 128; x++)
                {
                    float d = new Vector2(x - 63.5f, y - 63.5f).magnitude / 63.5f; float a = Mathf.Clamp01(1f - Mathf.Abs(d - .82f) / .1f); a = a * a * (3f - 2f * a);
                    t.SetPixel(x, y, new Color(1, 1, 1, a));
                }
                File.WriteAllBytes(p, t.EncodeToPNG()); Object.DestroyImmediate(t); AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate);
                var ti = (TextureImporter)AssetImporter.GetAtPath(p); ti.alphaIsTransparency = true; ti.wrapMode = TextureWrapMode.Clamp; ti.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(p);
        }

        static ParticleSystem NewPS(Transform parent, string name, Vector3 at, int max, Material mat, ParticleSystemRenderMode mode)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.position = at;
            var ps = go.AddComponent<ParticleSystem>(); ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.loop = true; main.prewarm = true; main.playOnAwake = true; main.maxParticles = max; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.renderMode = mode; r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return ps;
        }
        static ParticleSystem.MinMaxGradient Fade(float a0, float aMid, float midAt)
        {
            var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) }, new[] { new GradientAlphaKey(a0, 0f), new GradientAlphaKey(aMid, midAt), new GradientAlphaKey(0f, 1f) });
            return new ParticleSystem.MinMaxGradient(g);
        }

        /// <summary>The foot of a fall: churning foam (two splash discs at different speeds), droplets thrown out and falling back, soft rising
        /// mist; on a pool also ripple rings spreading out and foam clumps that drift away and bob. Everything is culled beyond ~120 m.</summary>
        static void Base(Transform parent, string name, Vector3 at, float r, bool pool, Material splashMat, Material churnMat, Vector3 downstream = default)
        {
            var go = new GameObject(name).transform; go.SetParent(parent, false);
            var p2 = new Vector2(at.x, at.z);
            Splash(go, name + "_foam", p2, at.y, r, splashMat);
            Splash(go, name + "_churn", p2 + new Vector2(.3f, -.2f), at.y + .012f, r * .62f, churnMat);
            if (pool) { Splash(go, name + "_churn2", p2 + new Vector2(-.25f, .15f), at.y + .018f, r * .78f, churnMat); Splash(go, name + "_core", p2, at.y + .024f, r * .42f, churnMat); }
            Spray(go, name + "_drops", at + Vector3.up * .1f, r * .35f, false, false);
            Spray(go, name + "_mist", at + Vector3.up * .6f, r * .75f, true, false);
            if (pool)
            {
                var rings = NewPS(go, name + "_rings", at + Vector3.up * .03f, 3, ringMat, ParticleSystemRenderMode.HorizontalBillboard);
                var m = rings.main; m.startLifetime = new ParticleSystem.MinMaxCurve(1.6f, 2.3f); m.startSpeed = 0f; m.startSize = new ParticleSystem.MinMaxCurve(r * 1.3f, r * 1.8f); m.startColor = new Color(1, 1, 1, .6f); m.gravityModifier = 0f;
                var em = rings.emission; em.rateOverTime = 1.35f; var sh = rings.shape; sh.shapeType = ParticleSystemShapeType.Circle; sh.radius = r * .2f; sh.rotation = new Vector3(-90f, 0, 0);
                var sz = rings.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, .22f, 1f, 1f));
                var col = rings.colorOverLifetime; col.enabled = true; col.color = Fade(.75f, .5f, .4f);
                rings.Play();
                var clumps = NewPS(go, name + "_clumps", at + Vector3.up * .05f, 14, sprayMat, ParticleSystemRenderMode.HorizontalBillboard);
                m = clumps.main; m.startLifetime = new ParticleSystem.MinMaxCurve(3.5f, 5.5f); m.startSpeed = new ParticleSystem.MinMaxCurve(.25f, .55f); m.startSize = new ParticleSystem.MinMaxCurve(.3f, .75f);
                m.startColor = new Color(1, 1, 1, .9f); m.gravityModifier = 0f; m.startRotation = new ParticleSystem.MinMaxCurve(0f, 6.28f);
                em = clumps.emission; em.rateOverTime = 3.2f; sh = clumps.shape; sh.shapeType = ParticleSystemShapeType.Circle; sh.radius = r * .35f; sh.rotation = new Vector3(-90f, 0, 0);
                if (downstream != default) { var vel = clumps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World; vel.x = downstream.x * .35f; vel.y = 0f; vel.z = downstream.z * .35f; }
                var nz = clumps.noise; nz.enabled = true; nz.separateAxes = true; nz.strengthX = .06f; nz.strengthY = .1f; nz.strengthZ = .06f; nz.frequency = .7f; nz.scrollSpeed = .4f;
                col = clumps.colorOverLifetime; col.enabled = true; col.color = Fade(.9f, .8f, .7f);
                clumps.Play();
            }
            var lg = go.gameObject.AddComponent<LODGroup>(); lg.SetLODs(new[] { new LOD((r * 3f + 2f) / 138f, go.GetComponentsInChildren<Renderer>()) }); lg.size = r * 3f + 2f;
        }

        /// <summary>A light spray thrown off a lip.</summary>
        static void LipSpray(Transform parent, string name, Vector3 at, Vector3 dir)
        {
            var ps = NewPS(parent, name, at, 14, sprayMat, ParticleSystemRenderMode.Billboard);
            var m = ps.main; m.startLifetime = new ParticleSystem.MinMaxCurve(.5f, .9f); m.startSpeed = new ParticleSystem.MinMaxCurve(1.2f, 2.4f); m.startSize = new ParticleSystem.MinMaxCurve(.1f, .25f);
            m.gravityModifier = .6f; m.startColor = new Color(1, 1, 1, .8f);
            var em = ps.emission; em.rateOverTime = 6f; em.SetBursts(new[] { new ParticleSystem.Burst(0f, 4, 7, 0, .75f) }); var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 25f; sh.radius = .6f;
            sh.rotation = Quaternion.LookRotation(dir.sqrMagnitude > 1e-4f ? dir : Vector3.forward).eulerAngles;
            var col = ps.colorOverLifetime; col.enabled = true; col.color = Fade(.8f, .6f, .5f);
            ps.GetComponent<ParticleSystemRenderer>().maxParticleSize = .2f;
            var lg = ps.gameObject.AddComponent<LODGroup>(); lg.SetLODs(new[] { new LOD(.022f, new Renderer[] { ps.GetComponent<Renderer>() }) }); lg.size = 3f;
            ps.Play();
        }

        /// <summary>Droplets peeling off along the whole lip and falling alongside the stream.</summary>
        static void FallDroplets(Transform parent, string name, Vector3 lip, Vector3 side, Vector3 outDir, float width, float drop)
        {
            var ps = NewPS(parent, name, lip + outDir * .3f, 26, sprayMat, ParticleSystemRenderMode.Billboard);
            var m = ps.main; float tf = Mathf.Sqrt(2f * Mathf.Max(drop, 1f) / 9.81f);
            m.startLifetime = new ParticleSystem.MinMaxCurve(tf * .8f, tf * 1.15f); m.startSpeed = new ParticleSystem.MinMaxCurve(.3f, .9f); m.startSize = new ParticleSystem.MinMaxCurve(.06f, .15f);
            m.gravityModifier = 1f; m.startColor = new Color(1, 1, 1, .85f);
            var em = ps.emission; em.rateOverTime = Mathf.Min(18f, 26f / tf); var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(width * 1.15f, .1f, .2f);
            sh.rotation = Quaternion.LookRotation(outDir, Vector3.up).eulerAngles + new Vector3(15f, 0, 0);
            var col = ps.colorOverLifetime; col.enabled = true; col.color = Fade(.85f, .7f, .7f);
            ps.GetComponent<ParticleSystemRenderer>().maxParticleSize = .1f;
            var lg = ps.gameObject.AddComponent<LODGroup>(); lg.SetLODs(new[] { new LOD(.03f, new Renderer[] { ps.GetComponent<Renderer>() }) }); lg.size = width + 3f;
            ps.Play();
        }

        /// <summary>0..1: how close to falling water (the cascade, its pools, the lower fall) - wet dark rock.</summary>
        static float WetNear(Vector2 p)
        {
            if (Casc == null || p.x < 465f || p.x > 515f || p.y < 680f || p.y > 870f) return 0f;
            float d = Mathf.Min(PolyDist(p, Casc) - 1.3f, Mathf.Min((p - Pool).magnitude - PoolR, (p - Spring).magnitude - SpringR));
            d = Mathf.Min(d, PolyDist(p, LowerFallLine) - 2.7f);
            return 1f - Sm(.4f, 3.6f, d);
        }
        static readonly List<Vector2> LowerFallLine = new() { new Vector2(485.2f, 696.5f), new Vector2(485.2f, 705.5f) };

        static void Water(Transform root)
        {
            var waterRoot = root.Find("Water");
            var lakeGo = waterRoot.Find("Water_Lake_mountain_lake"); var fallGo = waterRoot.Find("Waterfall_waterfall_mountain");
            var foamGo = waterRoot.Find("Foam_waterfall_mountain"); var ringGo = waterRoot.Find("FoamRing_waterfall_mountain");
            if (!lakeGo || !fallGo || !foamGo) { log.AppendLine("water: the mountain lake / waterfall objects are missing, cascade skipped"); return; }
            var flowMat = lakeGo.GetComponent<MeshRenderer>().sharedMaterial; waterRef = flowMat; var splashMat = foamGo.GetComponent<MeshRenderer>().sharedMaterial;
            var ringMat = ringGo ? ringGo.GetComponent<MeshRenderer>().sharedMaterial : null;
            var streamMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/VadimLocal/Forest/Materials/W86_water_stream_forest.mat") ?? flowMat;
            var wroot = new GameObject("Water_mountain_cascade").transform; wroot.SetParent(mRoot, false);
            // 1. spring pool on the NE summit shelf and the pool at the foot of the cascade (the lake's own water material)
            MeshGo("Water_cascade_pool", wroot, Disc("Water_cascade_pool", Pool, PoolR + 1.1f, PoolY), flowMat);
            // 2. the falls (Vadim 28.10: live, volumetric water): every fall is a curved stream with thickness that curls over its lip,
            //    two layers (a darker translucent core + an aerated white outer layer with ragged edges, faster), its own base kit
            var fallSrc = fallGo.GetComponent<MeshRenderer>().sharedMaterial;
            var baseFoam = BaseFoamMaterial(splashMat); var churnMat = ChurnMaterial(baseFoam);   // foam 3002 / churn 3003: over the stream's foot
            var fx = new GameObject("Spray_mountain").transform; fx.SetParent(wroot, false);
            int pieces = 0;
            // 2a. the upper cascade: spring rim -> wall -> ledge -> wall -> pool; the sheet follows the rock (+ curl at each top)
            var pts = new List<Vector2>(); for (int k = 0; k + 1 < Casc.Count; k++) { var a = Casc[k]; var b = Casc[k + 1]; int n = Mathf.Max(1, Mathf.CeilToInt((b - a).magnitude / .5f)); for (int q = 0; q < n; q++) pts.Add(Vector2.Lerp(a, b, q / (float)n)); }
            pts.Add(Casc[Casc.Count - 1]);
            int s0 = 0; while (s0 < pts.Count - 1 && (pts[s0] - Spring).magnitude < SpringR - .5f) s0++;
            int s1 = pts.Count - 1; while (s1 > s0 && (pts[s1] - Pool).magnitude < PoolR - .6f) s1--;
            pts = pts.GetRange(s0, s1 - s0 + 1);
            float L = 0f; var acc = new List<float> { 0f }; for (int k = 1; k < pts.Count; k++) { L += (pts[k] - pts[k - 1]).magnitude; acc.Add(L); }
            int mid = 0; float best = 1e9f; for (int k = 1; k < pts.Count - 1; k++) { float sl = Slope(pts[k]); if (sl < best && acc[k] > L * .3f && acc[k] < L * .75f) { best = sl; mid = k; } }
            Vector3 OnRock(Vector2 p) => new Vector3(p.x, NewY(p) + .45f, p.y);
            Vector3 NormalAt(Vector2 p) { var n = td.GetInterpolatedNormal((p.x - tp.x) / td.size.x, (p.y - tp.z) / td.size.z); return n; }
            float yTop = Mathf.Max(SpringY, OnRock(pts[0]).y), yBot = PoolY;
            {   // Vadim 28.10 #2: the whole outlet of the spring pool goes over the rim. The stream starts inside the pool (1 m from its centre,
                // faded in, flat at the pool's level) at the outlet's full width, and the pool narrows to that width at its outlet; the stream
                // follows the rock down both walls and ends under the surface of the cascade pool (faded out there)
                const float wOut = 4.6f;
                var dir0 = (pts[0] - Spring).sqrMagnitude > .01f ? (pts[0] - Spring).normalized : Vector2.down;
                var sp = new List<Vector2>(); for (float dd = 1f; dd < (pts[0] - Spring).magnitude - .25f; dd += .5f) sp.Add(Spring + dir0 * dd);
                sp.AddRange(pts);
                var c = new List<Vector3>(); var wall = new List<Vector3>(); var a = new List<float>(); bool dropped = false; float sd = 0f, dDrop = 0f;
                for (int k = 0; k < sp.Count; k++)
                {
                    if (k > 0) sd += (sp[k] - sp[k - 1]).magnitude;
                    float ry = NewY(sp[k]);
                    if (!dropped && ry < SpringY - .6f) { dropped = true; dDrop = sd; }
                    float y = ry + Mathf.Lerp(.1f, .45f, dropped ? Sm(0f, 2f, sd - dDrop) : 0f);
                    if (!dropped) y = Mathf.Max(y, SpringY - .015f);
                    if (k == sp.Count - 1) y = Mathf.Min(y, PoolY + .25f);
                    c.Add(new Vector3(sp[k].x, y, sp[k].y)); wall.Add(NormalAt(sp[k])); a.Add(Sm(0f, 2.6f, sd));
                }
                // the drop bows out from the wall where it is steep (the body's back reaches the rock again)
                for (int k = 1; k + 1 < c.Count; k++) { var fwd = (c[k + 1] - c[k - 1]).normalized; c[k] += wall[k] * (.55f * Sm(.5f, .9f, Mathf.Abs(fwd.y))); }
                for (int k = 1; k + 1 < c.Count; k++) c[k] = (c[k - 1] + c[k] * 2f + c[k + 1]) * .25f;
                // on into the cascade pool, down under its surface
                var last = c[c.Count - 1]; var pd = new Vector3(Pool.x - last.x, 0f, Pool.y - last.z); float pl = pd.magnitude; pd = pl > .01f ? pd / pl : Vector3.zero;
                int kEndU = Mathf.Max(0, c.Count - 3);
                c.Add(new Vector3(last.x, PoolY - .25f, last.z) + pd * Mathf.Min(.5f, pl * .25f)); c.Add(new Vector3(last.x, PoolY - .8f, last.z) + pd * Mathf.Min(1f, pl * .45f));
                wall.Add(wall[wall.Count - 1]); wall.Add(wall[wall.Count - 1]); a.Add(1f); a.Add(1f);
                var o = BulgeDirs(c, k => wall[k]); var st = Steep(c);
                float Lc = 0f; var cum = new List<float> { 0f }; for (int k = 1; k < c.Count; k++) { Lc += (c[k] - c[k - 1]).magnitude; cum.Add(Lc); }
                var w = new List<float>(); var hf = new List<float>(); var hb = new List<float>();
                for (int k = 0; k < c.Count; k++) { w.Add(Mathf.Lerp(wOut, wOut * 1.1f, cum[k] / Mathf.Max(Lc, .01f))); hf.Add(.03f + .47f * Sm(.2f, 1.2f, SpringY - c[k].y)); hb.Add(Mathf.Max(.1f, Mathf.Lerp(.6f, 1.15f, st[k]) * Sm(.3f, 2f, SpringY - c[k].y))); }   // thin in the pool / over the rim
                Stream(wroot, "Waterfall_upper", c, o, w, hf, hb, a, kEndU, PoolY, fallSrc); pieces++;
                // the spring pool narrows to the stream at its outlet (round pool + tangents to the outlet's two corners)
                var side0 = new Vector2(-dir0.y, dir0.x); var exit = Spring + dir0 * (SpringR + 1.3f);
                MeshGo("Water_spring_pool", wroot, Teardrop("Water_spring_pool", Spring, SpringR + .9f, SpringY, new[] { exit + side0 * (wOut * .5f), exit - side0 * (wOut * .5f) }), flowMat);
            }
            var ledge3 = OnRock(pts[mid]); var poolC = new Vector3(Pool.x, PoolY, Pool.y);
            Base(fx, "Base_cascade_ledge", ledge3 + Vector3.up * .05f, 1.7f, false, baseFoam, churnMat);
            var brookDir = new Vector3(Brook[0].x - Pool.x, 0, Brook[0].y - Pool.y).normalized;
            Base(fx, "Base_cascade_pool", poolC + Vector3.up * .04f, 2.8f, true, baseFoam, churnMat, brookDir);
            if (ringMat) { var poolDir = (Pool - pts[pts.Count - 1]).sqrMagnitude > .01f ? (Pool - pts[pts.Count - 1]).normalized : Vector2.down; FoamRing(wroot, "FoamRing_cascade_pool", Pool - poolDir * .8f, poolDir, PoolY + .07f, ringMat, 3.6f, 2.8f); }
            LipSpray(fx, "LipSpray_cascade_a", OnRock(pts[1]), (OnRock(pts[3]) - OnRock(pts[0])).normalized);
            LipSpray(fx, "LipSpray_cascade_b", OnRock(pts[mid + 1]), (OnRock(pts[Mathf.Min(mid + 3, pts.Count - 1)]) - OnRock(pts[mid])).normalized);
            float drop = yTop - yBot; var ledge = new Vector2(ledge3.x, ledge3.z); float ledgeY = ledge3.y;
            // 4. the brook across shelf 1 into the lake (the forest stream's flowing material)
            var bv = new List<Vector3>(); var buv = new List<Vector2>(); var buv1 = new List<Vector2>(); var bt = new List<int>();
            var bp = new List<Vector2>(); for (int k = 0; k + 1 < Brook.Count; k++) { var a = Brook[k]; var b = Brook[k + 1]; int n = Mathf.Max(1, Mathf.CeilToInt((b - a).magnitude / 1f)); for (int q = 0; q < n; q++) bp.Add(Vector2.Lerp(a, b, q / (float)n)); }
            bp.Add(Brook[Brook.Count - 1]);
            float BL = 0f; for (int k = 1; k < Brook.Count; k++) BL += (Brook[k] - Brook[k - 1]).magnitude;
            float sacc = 0f; bp.Insert(0, Pool + (Brook[0] - Pool).normalized * (PoolR - .3f));
            for (int k = 0; k < bp.Count; k++)
            {
                if (k > 0) sacc += (bp[k] - bp[k - 1]).magnitude;
                float sb = Mathf.Max(0f, sacc - (Brook[0] - bp[0]).magnitude);
                float f = Mathf.Clamp01(sb / BL) * (BrookSurf.Length - 1); int fi = Mathf.Min((int)f, BrookSurf.Length - 2);
                float y = Mathf.Lerp(BrookSurf[fi], BrookSurf[fi + 1], f - fi); if (k == 0) y = PoolY - .02f;
                var d = (bp[Mathf.Min(k + 1, bp.Count - 1)] - bp[Mathf.Max(k - 1, 0)]).normalized; var nn = new Vector2(-d.y, d.x); float hw = 1.15f + .15f * Mathf.Sin(k * .7f);
                var a2 = bp[k] + nn * hw; var b2 = bp[k] - nn * hw;
                bv.Add(new Vector3(a2.x, y, a2.y)); bv.Add(new Vector3(b2.x, y, b2.y)); buv.Add(a2 / 10f); buv.Add(b2 / 10f);
                float speed = Mathf.Lerp(.6f, 1.2f, Mathf.Clamp01((BrookSurf[0] - y) * 2f)); buv1.Add(d * speed); buv1.Add(d * speed);
                if (k > 0) { int q = bv.Count - 4; bt.AddRange(new[] { q, q + 2, q + 3, q, q + 3, q + 1 }); }
            }
            for (int k = 0; k < bt.Count; k += 3) { var n = Vector3.Cross(bv[bt[k + 1]] - bv[bt[k]], bv[bt[k + 2]] - bv[bt[k]]); if (n.y < 0) (bt[k + 1], bt[k + 2]) = (bt[k + 2], bt[k + 1]); }
            MeshGo("Water_cascade_brook", wroot, SaveMesh("Water_cascade_brook", bv, buv, bt, buv1), streamMat);
            // 5. the lower waterfall: three falls over the two ledges cut into its face, each a curling volumetric stream with its own base
            string lowNote = "";
            if (LowerSteps != null && LowerSteps.Count >= 6)
            {
                const float cx = 485.2f; var outD = new Vector3(0, 0, -1);
                Vector3 P3(Vector2 zy) => new Vector3(cx, zy.y, zy.x);
                var lip1 = P3(LowerSteps[0]); var foot1 = P3(LowerSteps[1]); var lip2 = P3(LowerSteps[2]); var foot2 = P3(LowerSteps[3]); var lip3 = P3(LowerSteps[4]); var foot3 = P3(LowerSteps[5]);
                foot3 += outD * .4f;   // lands inside the pool, not on its rocky rim
                // Vadim 28.10 #2: the whole river goes over the lip. Its own cross-sections (the vertex pairs of the river mesh) give the width,
                // centre and level for the last ~3.6 m; the stream lies on them (faded in), then curls over at the river's end edge, follows
                // the three steps and sinks under the plunge pool's surface
                var plunge = waterRoot.Find("Water_Lake_plunge_pool"); float poolW = plunge ? plunge.GetComponent<Renderer>().bounds.center.y : foot3.y;
                var secs = RiverSections(waterRoot.Find("Water_River_river"), lip1, -outD, 4.2f);
                var path = new List<Vector3>(); var w = new List<float>(); var a = new List<float>(); var hbA = new List<float>(); float wLip;
                if (secs.Count >= 2)
                {
                    float dEnd = secs[secs.Count - 1].d, d0 = Mathf.Min(secs[0].d, dEnd + 3.6f);
                    int nA = Mathf.Max(2, Mathf.CeilToInt((d0 - dEnd) / .3f));
                    for (int q = 0; q <= nA; q++)
                    {
                        float d = Mathf.Lerp(d0, dEnd, q / (float)nA); int s = 0; while (s + 2 < secs.Count && secs[s + 1].d > d) s++;
                        float f = Mathf.Clamp01((secs[s].d - d) / Mathf.Max(secs[s].d - secs[s + 1].d, .001f));
                        var m = Vector3.Lerp(secs[s].mid, secs[s + 1].mid, f); float ww = Mathf.Lerp(secs[s].w, secs[s + 1].w, f);
                        path.Add(m + Vector3.up * (.015f - .03f)); w.Add(ww + .1f); a.Add(Sm(0f, 2.4f, d0 - d));
                        hbA.Add(Mathf.Clamp(m.y - NewY(new Vector2(m.x, m.z)) - .05f, .3f, 1.5f));   // down to the river bed
                    }
                    wLip = w[w.Count - 1];
                    lowNote = $", lower fall: river {secs[secs.Count - 1].w:0.00} m wide at its end edge ({secs.Count} river sections)";
                }
                else
                {
                    path.Add(lip1 + new Vector3(0, -.015f, 1.8f)); w.Add(5f); a.Add(0f); hbA.Add(1f); wLip = 5f; lowNote = ", lower fall: river mesh not found, width 5 m";
                }
                int kLip = path.Count - 1; var lipE = path[kLip];
                if (secs.Count >= 2) path.AddRange(FallArc(lipE, lipE, foot1).Skip(2)); else path.AddRange(FallArc(lipE, lip1, foot1).Skip(1));
                path.AddRange(FallArc(foot1, lip2, foot2).Skip(1));
                int kEnd = path.Count;
                path.AddRange(FallArc(foot2, lip3, foot3).Skip(1));
                path.Add(foot3 + outD * .45f + Vector3.down * .45f); path.Add(foot3 + outD * .85f + Vector3.down * .9f);   // under the pool surface
                int nAll = path.Count;
                // soften the steps: the ledges are only ~1 m deep, so the water front runs on as one sheet with gentle bulges, not stacked rolls
                for (int pass = 0; pass < 20; pass++) { var zs = path.Select(pp => pp.z).ToList(); for (int k = kLip + 2; k < nAll - 1; k++) path[k] = new Vector3(path[k].x, path[k].y, (zs[k - 1] + zs[k] * 2f + zs[k + 1]) * .25f); }
                for (int k = w.Count; k < nAll; k++) { float f = (k - kLip) / (float)Mathf.Max(1, nAll - 1 - kLip); w.Add(Mathf.Lerp(wLip, wLip * 1.08f, f)); a.Add(1f); }
                var o = BulgeDirs(path, k => outD); var st = Steep(path); float hbL = hbA[hbA.Count - 1];
                var hf = new List<float>(); var hb = new List<float>();
                for (int k = 0; k < nAll; k++)
                {   // by depth below the lip: a thin skin on the river (nothing under its surface to show through it); the front (.5) and the back
                    // (1 m, reaching the stepped wall) grow only once the water is below the lip, so the back never sweeps up-stream into the river
                    float dr = lipE.y - path[k].y;
                    hf.Add(k <= kLip ? .03f : .03f + .47f * Sm(.2f, 1.2f, dr)); hb.Add(k <= kLip ? .12f : .12f + .88f * Sm(.3f, 2f, dr));
                }
                Stream(wroot, "Waterfall_lower", path, o, w, hf, hb, a, kEnd, poolW, fallSrc); pieces++;
                PoolToWall(wroot, "Waterfall_lower_pool", plunge, foot3.z + 1.4f);
                var lips = new[] { lip1, lip2, lip3 }; var feet = new[] { foot1, foot2, foot3 }; int fi = 0;
                for (; fi < 3; fi++)
                {
                    bool pool = fi == 2;
                    Base(fx, "Base_lower_" + fi, feet[fi] + new Vector3(0, pool ? .05f : .1f, pool ? -1.0f : -.2f), pool ? 4.2f : 1.6f, pool, baseFoam, churnMat, outD);
                    LipSpray(fx, "LipSpray_lower_" + fi, lips[fi] + outD * .25f, (outD - Vector3.up * .45f).normalized);
                }
                fallGo.gameObject.SetActive(false);
                lowNote += $", {fi} steps, width {wLip:0.00} -> {wLip * 1.08f:0.00} m, pool carried to the wall foot";
            }
            log.AppendLine($"water: spring pool {SpringY:0.0} m, upper cascade {L:0} m ({drop:0} m drop) in 2 falls, {pieces} streams (one closed full-width body each, river/pool -> lip -> fall -> under the pool surface), " +
                           $"bases with churning foam / droplets / mist (+ ripple rings and bobbing foam clumps on the pools), lip spray, pool {PoolY:0.00} m + foam ring, brook into the lake{lowNote}; lake / brook / plunge pool kept");
        }

        // ================================================================================================ tall grass blades: re-seated, off the rock and the scree

        static void Grass()
        {
            var grass = Object.FindAnyObjectByType<OnlyVolunteers.Map.W85.W85GrassRenderer>(FindObjectsInactive.Include);
            if (!grass || !grass.data || !grass.data.instances) { log.AppendLine("grass: no renderer"); return; }
            var src = grass.data; var bytes = (byte[])src.instances.bytes.Clone(); var chunks = (OnlyVolunteers.Map.Grass.GrassPatchData24.Chunk[])src.chunks.Clone();
            var win = new Rect(Area.xMin, Area.yMin, Area.width, Area.height); int moved = 0, hidden = 0; var wb = src.worldBounds;
            void Put(int o, float v) { var b4 = System.BitConverter.GetBytes(v); System.Buffer.BlockCopy(b4, 0, bytes, o, 4); }
            for (int c = 0; c < chunks.Length; c++)
            {
                var ch = chunks[c];
                if (!new Rect(ch.centre.x - ch.extents.x, ch.centre.z - ch.extents.z, ch.extents.x * 2f, ch.extents.z * 2f).Overlaps(win)) continue;
                float ymin = 1e9f, ymax = -1e9f; bool touched = false;
                for (uint k = ch.start; k < ch.start + ch.count && (k + 1) * 32 <= bytes.Length; k++)
                {
                    int o = (int)k * 32;
                    float gx = System.BitConverter.ToSingle(bytes, o), gyOld = System.BitConverter.ToSingle(bytes, o + 4), gz = System.BitConverter.ToSingle(bytes, o + 8), gh = System.BitConverter.ToSingle(bytes, o + 12);
                    var p = new Vector2(gx, gz); float gy = gyOld;
                    if (win.Contains(p) && NearMask(p, 1.5f))
                    {
                        touched = true; gy = NewY(p);
                        if (Mathf.Abs(gy - gyOld) > .02f) { Put(o + 4, gy); moved++; }
                        var z = Z(p); float st = Slope(p);
                        bool kill = st > 29f || z.scree > .55f || z.peak > .5f || InWater(p, .4f);
                        if (!kill && z.w > .5f) { uint hsh = (uint)(gx * 73856093f) ^ (uint)(gz * 19349663f); if ((hsh % 1000) / 1000f < .45f) kill = true; }   // thinner under the dense firs
                        if (kill && gh > 0f) { Put(o + 12, 0f); gh = 0f; hidden++; }
                    }
                    ymin = Mathf.Min(ymin, gy); ymax = Mathf.Max(ymax, gy + gh);
                }
                if (touched && ymax > ymin) { ch.centre.y = (ymin + ymax) * .5f; ch.extents.y = (ymax - ymin) * .5f + .5f; chunks[c] = ch; wb.Encapsulate(new Vector3(ch.centre.x, ymin, ch.centre.z)); wb.Encapsulate(new Vector3(ch.centre.x, ymax, ch.centre.z)); }
            }
            string bp = Dir + "/Data/Grass_W86_mountain.bytes"; File.WriteAllBytes(bp, bytes); AssetDatabase.ImportAsset(bp, ImportAssetOptions.ForceUpdate);
            var nd = ScriptableObject.CreateInstance<OnlyVolunteers.Map.Grass.GrassPatchData24>();
            nd.instances = AssetDatabase.LoadAssetAtPath<TextAsset>(bp); nd.instanceCount = src.instanceCount; nd.worldBounds = wb; nd.chunks = chunks;
            nd.sourceScene = src.sourceScene; nd.sourceCommit = src.sourceCommit; nd.placementSummary = src.placementSummary + " | VadimMountain v1: massif blades re-seated, off rock / scree";
            string dp = Dir + "/Data/GrassData_W86_mountain.asset"; AssetDatabase.DeleteAsset(dp); AssetDatabase.CreateAsset(nd, dp);
            grass.data = nd; EditorUtility.SetDirty(grass);
            log.AppendLine($"grass: {moved} blades re-seated, {hidden} hidden (rock, scree, steep, thinned under the firs)");
        }

        // ================================================================================================ sea quads where the ground went below the water (VadimHillApply.FillSea)

        static void FillSea(string name, Rect r, System.Func<Vector2, bool> want)
        {
            var seaGo = GameObject.Find("Sea_dense_0m"); if (!seaGo) { log.AppendLine("FillSea: no Sea_dense_0m"); return; }
            var old = seaGo.transform.parent.Find(name); if (old) Object.DestroyImmediate(old.gameObject);
            var mc = seaGo.AddComponent<MeshCollider>(); mc.sharedMesh = seaGo.GetComponent<MeshFilter>().sharedMesh; Physics.SyncTransforms();
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            for (float z = -200f + Mathf.Floor((r.yMin + 200f) / 4f) * 4f; z < r.yMax; z += 4f)
                for (float x = -200f + Mathf.Floor((r.xMin + 200f) / 4f) * 4f; x < r.xMax; x += 4f)
                {
                    var c = new Vector2(x + 2f, z + 2f);
                    bool need = want(c) || want(new Vector2(x + .5f, z + .5f)) || want(new Vector2(x + 3.5f, z + .5f)) || want(new Vector2(x + .5f, z + 3.5f)) || want(new Vector2(x + 3.5f, z + 3.5f));
                    if (!need || mc.Raycast(new Ray(new Vector3(c.x, 50f, c.y), Vector3.down), out _, 100f)) continue;
                    int n = v.Count;
                    v.Add(new Vector3(x, 0, z)); v.Add(new Vector3(x, 0, z + 4f)); v.Add(new Vector3(x + 4f, 0, z + 4f)); v.Add(new Vector3(x + 4f, 0, z));
                    uv.Add(new Vector2(x, z) / 10f); uv.Add(new Vector2(x, z + 4f) / 10f); uv.Add(new Vector2(x + 4f, z + 4f) / 10f); uv.Add(new Vector2(x + 4f, z) / 10f);
                    t.AddRange(new[] { n, n + 1, n + 2, n, n + 2, n + 3 });
                }
            Object.DestroyImmediate(mc);
            log.AppendLine($"{name}: {t.Count / 6} sea quads added");
            if (v.Count == 0) return;
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 }; m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0); m.RecalculateNormals(); m.RecalculateBounds();
            string pth = Dir + "/Meshes/" + name + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(m, pth);
            var go = new GameObject(name); go.transform.SetParent(seaGo.transform.parent, false); go.layer = seaGo.layer;
            go.AddComponent<MeshFilter>().sharedMesh = m; var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = seaGo.GetComponent<MeshRenderer>().sharedMaterial;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        // ================================================================================================ probe (before state, for the plan script)

        public static void Probe()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            EditorSceneManager.OpenScene(Scene);
            var sb = new StringBuilder();
            var t = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tdd = t.terrainData; var tpp = t.transform.position;
            sb.AppendLine($"TERRAIN pos={tpp} size={tdd.size} hmRes={tdd.heightmapResolution} alphaRes={tdd.alphamapResolution} layers={tdd.terrainLayers.Length} trees={tdd.treeInstanceCount} protos={tdd.treePrototypes.Length}");
            for (int i = 0; i < tdd.terrainLayers.Length; i++) { var l = tdd.terrainLayers[i]; sb.AppendLine($"  layer {i} {(l ? l.name : "null")} path={(l ? AssetDatabase.GetAssetPath(l) : "-")} tile={(l ? l.tileSize.ToString() : "")} remapMax={(l ? l.diffuseRemapMax.ToString() : "")}"); }
            int nx = Area.width + 1, nz = Area.height + 1; var hb = new byte[nx * nz * 4];
            for (int j = 0; j < nz; j++) for (int i = 0; i < nx; i++) { float y = t.SampleHeight(new Vector3(Area.xMin + i, 0, Area.yMin + j)) + tpp.y; System.Buffer.BlockCopy(System.BitConverter.GetBytes(y), 0, hb, (j * nx + i) * 4, 4); }
            File.WriteAllBytes(Out + "mountain_probe_h.f32", hb);
            File.WriteAllText(Out + "mountain_probe.txt", sb.ToString());
            Debug.Log("[Mountain] probe written");
        }

        // ================================================================================================ renders

        static Camera shotCam;
        static void NoFog(UnityEngine.Rendering.ScriptableRenderContext ctx, Camera c) { if (c == shotCam) RenderSettings.fog = false; }

        /// <summary>Same cameras before and after: top of the whole massif (the reference frame), 3/4 from the south-east, along the sea cliff,
        /// ground views from the Hutor, at a wall foot, at the waterfall, the NE peaks.</summary>
        public static void Shots(string tag)
        {
            Directory.CreateDirectory(ShotDir);
            var cams0 = Object.FindObjectsByType<Camera>().Where(c => c.enabled).ToList();   // restored in finally (a disabled player camera saved into the scene = grey game)
            foreach (var c in cams0) c.enabled = false;
            bool fog0 = RenderSettings.fog; RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tp = ter.transform.position;
            float lodBias0 = QualitySettings.lodBias; int maxLod0 = QualitySettings.maximumLODLevel; float shadow0 = QualitySettings.shadowDistance;
            float treeDist0 = ter.treeDistance, base0 = ter.basemapDistance, bill0 = ter.treeBillboardDistance;
            var go = new GameObject("MountainShotCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox; cam.nearClipPlane = .1f;
            shotCam = cam;
            var fogMbs = Object.FindObjectsByType<MonoBehaviour>().Where(m => m && System.Text.RegularExpressions.Regex.IsMatch(m.GetType().Name, "^District(Fog|Aerial)")).ToList();
            fogMbs = fogMbs.Where(m => m.enabled).ToList(); foreach (var m in fogMbs) m.enabled = false;
            UnityEngine.Rendering.RenderPipelineManager.beginCameraRendering += NoFog;
            string pre = ShotDir + tag + "_";
            // a fresh batch session would draw not-yet-compiled shader variants with the cyan-white placeholder: compile them synchronously
            bool async0 = ShaderUtil.allowAsyncCompilation; ShaderUtil.allowAsyncCompilation = false;
            float G(float x, float z) => ter.SampleHeight(new Vector3(x, 0, z)) + tp.y;
            try
            {
                if (!onlyWater) {
                QualitySettings.lodBias = 50f; ter.treeDistance = 2000f; ter.basemapDistance = 5000f; QualitySettings.shadowDistance = 600f;
                cam.orthographic = true; cam.orthographicSize = 295f; cam.aspect = 720f / 590f;
                go.transform.position = new Vector3(360f, 400f, 655f); go.transform.rotation = Quaternion.Euler(90, 0, 0);
                Shot(cam, 1440, 1180, pre + "top.png"); Shot(cam, 1440, 1180, pre + "top.png");
                cam.orthographic = false; cam.fieldOfView = 55f; cam.aspect = 1600f / 900f;
                QualitySettings.lodBias = 4f; ter.treeDistance = 1500f; QualitySettings.shadowDistance = 400f;
                go.transform.position = new Vector3(575f, 165f, 380f); go.transform.LookAt(new Vector3(320f, 35f, 720f)); Shot(cam, 1600, 900, pre + "se34.png");
                go.transform.position = new Vector3(-90f, 70f, 330f); go.transform.LookAt(new Vector3(120f, 30f, 680f)); Shot(cam, 1600, 900, pre + "seacliff.png");
                QualitySettings.shadowDistance = 250f; cam.fieldOfView = 60f; cam.aspect = 1400f / 800f;
                foreach (var v in GroundViews())
                {
                    go.transform.position = new Vector3(v.eye.x, G(v.eye.x, v.eye.y) + v.up, v.eye.y);
                    go.transform.LookAt(new Vector3(v.look.x, v.lookY, v.look.y));
                    Shot(cam, 1400, 800, pre + v.name + ".png");
                }
                }
                QualitySettings.lodBias = 4f; ter.treeDistance = 1500f; QualitySettings.shadowDistance = 250f; cam.orthographic = false; cam.fieldOfView = 60f; cam.aspect = 1400f / 800f;
                // the falls: close and mid views, two moments each (particles simulated; the fall materials' scroll / shake phase moved for the 2nd)
                var wm = GameObject.Find("Map_W85_v02/VadimMountain");
                var pss = wm ? wm.GetComponentsInChildren<ParticleSystem>() : new ParticleSystem[0];
                var fallMats = wm ? wm.GetComponentsInChildren<MeshRenderer>().Select(r => r.sharedMaterial).Where(m => m && m.name.StartsWith("MT_fall_")).Distinct().ToList() : new List<Material>();
                var speed0 = fallMats.Select(m => (m.GetFloat("_OV_FallSpeed"), m.GetVector("_OV_Wobble"))).ToList();
                try
                {
                    foreach (var v in WaterViews()) { ter.drawTreesAndFoliage = !v.bare; go.transform.position = new Vector3(v.eye.x, G(v.eye.x, v.eye.y) + v.up, v.eye.y); go.transform.LookAt(new Vector3(v.look.x, v.lookY, v.look.y)); Shot(cam, 320, 180, Out + "_warmup.png"); }   // warm-up
                    for (int frame = 0; frame < 2; frame++)
                    {
                        foreach (var ps in pss) ps.Simulate(2f + .55f * frame, true, true);
                        for (int q = 0; q < fallMats.Count; q++) { fallMats[q].SetFloat("_OV_FallSpeed", speed0[q].Item1 * (frame == 0 ? 1f : 1.07f)); var wv = speed0[q].Item2; wv.z *= frame == 0 ? 1f : 1.12f; fallMats[q].SetVector("_OV_Wobble", wv); }
                        foreach (var v in WaterViews())
                        {
                            go.transform.position = new Vector3(v.eye.x, G(v.eye.x, v.eye.y) + v.up, v.eye.y);
                            go.transform.LookAt(new Vector3(v.look.x, v.lookY, v.look.y)); ter.drawTreesAndFoliage = !v.bare;
                            Shot(cam, 1400, 800, pre + v.name + "_t" + frame + ".png");
                        }
                    }
                }
                finally { for (int q = 0; q < fallMats.Count; q++) { fallMats[q].SetFloat("_OV_FallSpeed", speed0[q].Item1); fallMats[q].SetVector("_OV_Wobble", speed0[q].Item2); } }
            }
            finally
            {
                ShaderUtil.allowAsyncCompilation = async0;
                UnityEngine.Rendering.RenderPipelineManager.beginCameraRendering -= NoFog;
                foreach (var m in fogMbs) if (m) m.enabled = true;
                QualitySettings.lodBias = lodBias0; QualitySettings.maximumLODLevel = maxLod0; QualitySettings.shadowDistance = shadow0;
                ter.treeDistance = treeDist0; ter.basemapDistance = base0; ter.treeBillboardDistance = bill0; RenderSettings.fog = fog0; ter.drawTreesAndFoliage = true;
                Object.DestroyImmediate(go);
                foreach (var c in cams0) if (c) c.enabled = true;
            }
            Debug.Log("[Mountain] shots " + tag + " written to " + ShotDir);
        }

        static List<(string name, Vector2 eye, float up, Vector2 look, float lookY)> GroundViews() => new()
        {
            ("hutor", new Vector2(476f, 594f), 1.9f, new Vector2(485.5f, 703f), 24f),      // from the Hutor road bridge: the gorge, the tiers and the stepped waterfall (ref 03)
            ("gorge", new Vector2(483f, 618f), 2.6f, new Vector2(485.5f, 702f), 20f),      // in the gorge, up the stream to the stepped lower fall
            ("hutor_walls", new Vector2(400f, 588f), 1.7f, new Vector2(405f, 720f), 48f),  // from the Hutor north field to the tiers
            ("hutor_west", new Vector2(262f, 600f), 1.7f, new Vector2(200f, 720f), 45f),   // the west / north-west walls above the Hutor
            ("foot", new Vector2(302f, 633f), 1.7f, new Vector2(298f, 672f), 24f),         // close at a wall foot / scree (one wall up close)
            ("waterfall", new Vector2(483f, 664f), 5f, new Vector2(485.5f, 702f), 21f),     // the stepped waterfall from above the stream
            ("ne_peaks", new Vector2(600f, 690f), 32f, new Vector2(515f, 880f), 80f),      // the NE peaks from the Rough side (above the park trees)
            ("lake", new Vector2(500f, 743f), 1.7f, new Vector2(491f, 835f), 56f),         // from the lake shore up the upper cascade
            ("shelf", new Vector2(300f, 690f), 1.7f, new Vector2(240f, 740f), 50f),        // on a shelf, in the fir forest
            ("hutor_far", new Vector2(330f, 548f), 1.7f, new Vector2(318f, 760f), 72f),    // from inside the Hutor: the tiers rising behind each other
            ("hutor_ne", new Vector2(424f, 566f), 1.7f, new Vector2(440f, 770f), 70f),     // from the Hutor north field to the east tiers and the NE peaks
        };

        static List<(string name, Vector2 eye, float up, Vector2 look, float lookY, bool bare)> WaterViews() => new()
        {
            ("waterfall_close", new Vector2(485.4f, 689.5f), 2.3f, new Vector2(485.2f, 701.5f), 19f, false),   // the lower fall from its plunge pool
            ("waterfall_mid", new Vector2(483f, 664f), 5f, new Vector2(485.5f, 702f), 21f, false),             // the lower fall from above the stream
            ("waterfall_lip", new Vector2(483f, 712.5f), 4.5f, new Vector2(485.4f, 701.5f), 24f, false),        // river -> lip -> fall, from above the river, upstream
            ("waterfall_below", new Vector2(480.8f, 694.5f), 1f, new Vector2(485.4f, 700.6f), 18.5f, false),   // low by the pool, up the side of the stream
            ("cascade", new Vector2(491.4f, 775f), 30f, new Vector2(490.8f, 840f), 55f, true),                 // the upper cascade, trees hidden (unobstructed)
            ("cascade_top", new Vector2(484f, 861f), 5f, new Vector2(489.7f, 850.5f), 84.5f, true),            // spring pool -> outlet -> over the rim
        };

        static void Shot(Camera cam, int w, int h, string file)
        {
            var rt = new RenderTexture(w, h, 24); cam.targetTexture = rt; cam.Render();
            RenderTexture.active = rt; var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply(); File.WriteAllBytes(file, tex.EncodeToPNG());
            RenderTexture.active = null; cam.targetTexture = null; Object.DestroyImmediate(tex); rt.Release(); Object.DestroyImmediate(rt);
        }
    }
}
