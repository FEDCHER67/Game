using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Forest (district 01) rebuild, Vadim 28.10: plan v06 (ChatGPT forest v03 on our map) - relief, lake, swamp, ravine stream,
    /// winding foot paths, short rail tunnel -> wagon v03, kit trees / rocks / ground cover. Local W86 scene + terrain only.
    /// Backup of the scene + TerrainData before the first run in VolunteersBuilds\backup_forest; Run() = restore that backup, then apply.</summary>
    static class VadimForestApply
    {
        const string Scene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        const string Bak = @"C:\Users\chern_0eqkb03\VolunteersBuilds\backup_forest";
        const string Dir = "Assets/VadimLocal/Forest";
        const string Out = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";

        public static void Compile() { Debug.Log("[Forest] compiled"); }

        // ------------------------------------------------------------------------------------------------ backup / restore

        static void Backup()
        {
            Directory.CreateDirectory(Bak);
            if (File.Exists(Path.Combine(Bak, "terrain_path.txt"))) return;
            var guid = AssetDatabase.FindAssets("TerrainData_W85_v02 t:TerrainData").FirstOrDefault();
            string tdPath = guid != null ? AssetDatabase.GUIDToAssetPath(guid) : null;
            if (string.IsNullOrEmpty(tdPath)) throw new System.Exception("TerrainData_W85_v02 not found");
            File.Copy(tdPath, Path.Combine(Bak, Path.GetFileName(tdPath)), true);
            File.Copy(Scene, Path.Combine(Bak, Path.GetFileName(Scene)), true);
            File.WriteAllText(Path.Combine(Bak, "terrain_path.txt"), tdPath);
            Debug.Log("[Forest] backup written to " + Bak);
        }

        public static void Restore()
        {
            string tdPath = File.ReadAllText(Path.Combine(Bak, "terrain_path.txt")).Trim();
            File.Copy(Path.Combine(Bak, Path.GetFileName(tdPath)), tdPath, true);
            File.Copy(Path.Combine(Bak, Path.GetFileName(Scene)), Scene, true);
            AssetDatabase.ImportAsset(tdPath, ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(Scene, ImportAssetOptions.ForceUpdate);
            AssetDatabase.Refresh();
            Debug.Log("[Forest] restored scene + terrain from " + Bak);
        }

        // ------------------------------------------------------------------------------------------------ probe

        public static void Probe()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            Backup();
            EditorSceneManager.OpenScene(Scene);
            var sb = new StringBuilder();
            var area = Rect.MinMaxRect(150, 20, 560, 520);
            foreach (var t in Object.FindObjectsByType<Terrain>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                var td = t.terrainData; var tp = t.transform.position;
                sb.AppendLine($"TERRAIN {t.name} active={t.gameObject.activeInHierarchy} pos={tp} size={td.size} hmRes={td.heightmapResolution} alphaRes={td.alphamapResolution} holesRes={td.holesResolution} detailRes={td.detailResolution} path={AssetDatabase.GetAssetPath(td)}");
                sb.AppendLine($"  treeDistance={t.treeDistance} billboard={t.treeBillboardDistance} crossFade={t.treeCrossFadeLength} maxFullLOD={t.treeMaximumFullLODCount} pixErr={t.heightmapPixelError} basemap={t.basemapDistance} instanced={t.drawInstanced} detailDist={t.detailObjectDistance} detailDens={t.detailObjectDensity} drawTrees={t.drawTreesAndFoliage} layer={t.gameObject.layer} mat={(t.materialTemplate ? t.materialTemplate.name + "/" + t.materialTemplate.shader.name : "-")}");
                for (int i = 0; i < td.terrainLayers.Length; i++) { var l = td.terrainLayers[i]; sb.AppendLine($"  layer {i} {(l ? l.name : "null")} tex={(l && l.diffuseTexture ? AssetDatabase.GetAssetPath(l.diffuseTexture) : "-")} tile={(l ? l.tileSize.ToString() : "")} remapMax={(l ? l.diffuseRemapMax.ToString() : "")}"); }
                for (int i = 0; i < td.treePrototypes.Length; i++)
                {
                    var pr = td.treePrototypes[i]; var go = pr.prefab;
                    string info = go ? $"{go.name} path={AssetDatabase.GetAssetPath(go)} lod={(go.GetComponent<LODGroup>() ? go.GetComponent<LODGroup>().lodCount.ToString() : "none")} rends={string.Join(",", go.GetComponentsInChildren<Renderer>().Select(r => r.name + ":" + string.Join("+", r.sharedMaterials.Select(m => m ? m.name + "(" + m.shader.name + ")" : "null"))))} cols={string.Join(",", go.GetComponentsInChildren<Collider>().Select(c => c.GetType().Name))}" : "null";
                    sb.AppendLine($"  treeProto {i} {info} bend={pr.bendFactor}");
                }
                for (int i = 0; i < td.detailPrototypes.Length; i++) { var d = td.detailPrototypes[i]; sb.AppendLine($"  detailProto {i} mode={d.renderMode} proto={(d.prototype ? d.prototype.name : "-")} tex={(d.prototypeTexture ? d.prototypeTexture.name : "-")} inst={d.useInstancing}"); }
                var cnt = new Dictionary<int, int>(); int inArea = 0;
                var csv = new StringBuilder("x,y,z,proto,ws,hs,rot\n");
                foreach (var ti in td.treeInstances)
                {
                    var w = new Vector3(tp.x + ti.position.x * td.size.x, tp.y + ti.position.y * td.size.y, tp.z + ti.position.z * td.size.z);
                    if (!area.Contains(new Vector2(w.x, w.z))) continue;
                    inArea++; cnt.TryGetValue(ti.prototypeIndex, out int c0); cnt[ti.prototypeIndex] = c0 + 1;
                    csv.AppendLine($"{w.x:0.00},{w.y:0.00},{w.z:0.00},{ti.prototypeIndex},{ti.widthScale:0.00},{ti.heightScale:0.00},{ti.rotation:0.00}");
                }
                sb.AppendLine($"  trees total {td.treeInstanceCount}, in probe area {inArea}: " + string.Join(" ", cnt.OrderBy(k => k.Key).Select(k => k.Key + ":" + k.Value)));
                if (t.name == "Terrain_W85_v02")
                {
                    File.WriteAllText(Out + "forest_probe_trees.csv", csv.ToString());
                    // heights 1 m over the probe area (float32, row-major z then x), for the design script
                    int nx = (int)area.width + 1, nz = (int)area.height + 1; var bytes = new byte[nx * nz * 4]; int o = 0;
                    for (int j = 0; j < nz; j++) for (int i = 0; i < nx; i++) { float y = t.SampleHeight(new Vector3(area.xMin + i, 0, area.yMin + j)) + tp.y; System.Buffer.BlockCopy(System.BitConverter.GetBytes(y), 0, bytes, o, 4); o += 4; }
                    File.WriteAllBytes(Out + "forest_probe_heights_150_20_1m.f32", bytes);
                    sb.AppendLine($"  heights dumped {nx}x{nz} from ({area.xMin},{area.yMin})");
                    // splat: dominant layer + weights of every layer, 1 m
                    int A = td.alphamapResolution; float ax = td.size.x / A, az = td.size.z / A;
                    int a0 = Mathf.FloorToInt((area.xMin - tp.x) / ax), b0 = Mathf.FloorToInt((area.yMin - tp.z) / az), a1 = Mathf.CeilToInt((area.xMax - tp.x) / ax), b1 = Mathf.CeilToInt((area.yMax - tp.z) / az);
                    var al = td.GetAlphamaps(a0, b0, a1 - a0, b1 - b0); int L = td.alphamapLayers;
                    var sbytes = new byte[(a1 - a0) * (b1 - b0) * L];
                    for (int j = 0; j < b1 - b0; j++) for (int i = 0; i < a1 - a0; i++) for (int l = 0; l < L; l++) sbytes[(j * (a1 - a0) + i) * L + l] = (byte)Mathf.RoundToInt(al[j, i, l] * 255f);
                    File.WriteAllBytes(Out + "forest_probe_splat.u8", sbytes);
                    sb.AppendLine($"  splat dumped {a1 - a0}x{b1 - b0}x{L} from alpha cell ({a0},{b0}) cell size {ax}x{az}");
                    // holes in the area
                    int hr = td.holesResolution; float hx = td.size.x / hr, hz = td.size.z / hr; int c0h = Mathf.FloorToInt((area.xMin - tp.x) / hx), r0h = Mathf.FloorToInt((area.yMin - tp.z) / hz);
                    var holes = td.GetHoles(c0h, r0h, Mathf.CeilToInt(area.width / hx), Mathf.CeilToInt(area.height / hz)); int nh = 0;
                    for (int j = 0; j < holes.GetLength(0); j++) for (int i = 0; i < holes.GetLength(1); i++) if (!holes[j, i]) nh++;
                    sb.AppendLine($"  holes in area: {nh}");
                }
            }
            var root = GameObject.Find("Map_W85_v02");
            if (root) { sb.AppendLine("ROOT children:"); foreach (Transform c in root.transform) sb.AppendLine($"  {c.name} kids={c.childCount} active={c.gameObject.activeSelf} pos={c.position}"); }
            foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects()) sb.AppendLine($"SCENE ROOT {go.name} kids={go.transform.childCount} active={go.activeSelf}");
            var df = GameObject.Find("District_forest");
            if (df) { sb.AppendLine("District_forest children:"); foreach (Transform c in df.transform) sb.AppendLine($"  {c.name} kids={c.childCount} active={c.gameObject.activeSelf} pos={c.position:F1} rot={c.eulerAngles:F0} scale={c.localScale:F2}"); }
            sb.AppendLine("RENDERERS in area (bounds < 400 m):");
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                var b = r.bounds; if (b.size.x > 400 || b.size.z > 400 || !area.Overlaps(Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z))) continue;
                string n = r.name; if (n.Contains("LOD1") || n.Contains("LOD2")) continue;
                string path = n; for (var q = r.transform.parent; q != null; q = q.parent) path = q.name + "/" + path;
                var mf = r.GetComponent<MeshFilter>(); int tris = mf && mf.sharedMesh ? (int)(mf.sharedMesh.triangles.Length / 3) : -1;
                sb.AppendLine($"{path} | act={r.gameObject.activeInHierarchy} | {b.min.x:0.0},{b.min.y:0.0},{b.min.z:0.0}..{b.max.x:0.0},{b.max.y:0.0},{b.max.z:0.0} | mats={string.Join("+", r.sharedMaterials.Select(m => m ? m.name : "null"))} | sh={(r.sharedMaterial ? r.sharedMaterial.shader.name : "-")} | mesh={(mf && mf.sharedMesh ? mf.sharedMesh.name + " (" + AssetDatabase.GetAssetPath(mf.sharedMesh) + ")" : "-")} tris={tris} | layer={r.gameObject.layer} | col={string.Join(",", r.GetComponents<Collider>().Select(c => c.GetType().Name))}");
            }
            sb.AppendLine("COLLIDER-ONLY objects in area:");
            foreach (var c in Object.FindObjectsByType<Collider>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (c.GetComponent<Renderer>() || c is TerrainCollider) continue; var b = c.bounds;
                if (b.size.x > 400 || !area.Overlaps(Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z))) continue;
                string path = c.name; for (var q = c.transform.parent; q != null; q = q.parent) path = q.name + "/" + path;
                sb.AppendLine($"{path} | {c.GetType().Name} trig={c.isTrigger} | {b.min:F1}..{b.max:F1} | layer={c.gameObject.layer}");
            }
            sb.AppendLine("WATER-like renderers anywhere:");
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                var m = r.sharedMaterial; if (!m) continue;
                if (!(m.shader.name.ToLower().Contains("water") || r.name.Contains("Water") || r.name.Contains("Sea"))) continue;
                sb.AppendLine($"  {r.name} parent={(r.transform.parent ? r.transform.parent.name : "-")} mat={m.name} ({AssetDatabase.GetAssetPath(m)}) sh={m.shader.name} b={r.bounds.center:F1} size={r.bounds.size:F1}");
            }
            var grass = Object.FindFirstObjectByType<OnlyVolunteers.Map.W85.W85GrassRenderer>(FindObjectsInactive.Include);
            if (grass)
            {
                sb.AppendLine($"GRASS {grass.name} data={(grass.data ? AssetDatabase.GetAssetPath(grass.data) : "-")} count={(grass.data ? grass.data.instanceCount : 0)} mat={(grass.material ? AssetDatabase.GetAssetPath(grass.material) : "-")} chunks={(grass.data ? grass.data.chunks.Length : 0)} summary={(grass.data ? grass.data.placementSummary : "")}");
                if (grass.data && grass.data.instances)
                {
                    var bytes = grass.data.instances.bytes; int nIn = 0; var codes = new Dictionary<string, int>(); float hmin = 9, hmax = 0;
                    for (int k = 0; (k + 1) * 32 <= bytes.Length; k++)
                    {
                        float gx = System.BitConverter.ToSingle(bytes, k * 32), gz = System.BitConverter.ToSingle(bytes, k * 32 + 8), gh = System.BitConverter.ToSingle(bytes, k * 32 + 12), code = System.BitConverter.ToSingle(bytes, k * 32 + 28);
                        if (!Rect.MinMaxRect(170, 40, 520, 420).Contains(new Vector2(gx, gz))) continue;
                        nIn++; string key = code.ToString("0.0"); codes.TryGetValue(key, out int cc); codes[key] = cc + 1; hmin = Mathf.Min(hmin, gh); hmax = Mathf.Max(hmax, gh);
                    }
                    sb.AppendLine($"  blades in forest box: {nIn}, h {hmin:0.00}..{hmax:0.00}, codes " + string.Join(" ", codes.OrderBy(k => k.Key).Take(30).Select(k => k.Key + ":" + k.Value)));
                }
            }
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                string tn = mb.GetType().Name;
                if (tn.Contains("Ambience") || tn.Contains("Water") || tn.Contains("Spawn") || tn.Contains("Crowd") || tn.Contains("Teleport") || tn.Contains("Base"))
                    sb.AppendLine($"MB {tn} on {mb.name} at {mb.transform.position:F1}");
            }
            var amb = Object.FindFirstObjectByType<OnlyVolunteers.Audio.AmbiencePlayer>(FindObjectsInactive.Include);
            if (amb) sb.AppendLine($"AMBIENCE sceneData={(amb.SceneData ? AssetDatabase.GetAssetPath(amb.SceneData) : "-")} waterOverride={(amb.SceneData && amb.SceneData.WaterOverride ? AssetDatabase.GetAssetPath(amb.SceneData.WaterOverride) : "-")}");
            sb.AppendLine($"QUALITY lodBias={QualitySettings.lodBias} maxLOD={QualitySettings.maximumLODLevel} shadowDist={QualitySettings.shadowDistance} level={QualitySettings.GetQualityLevel()} names={string.Join(",", QualitySettings.names)}");
            File.WriteAllText(Out + "forest_probe.txt", sb.ToString());
            Shots("before");
        }

        // ================================================================================================ RUN

        static Terrain ter; static TerrainData td; static Vector3 tp;
        static Transform forestRoot; static int groundLayer;
        static StringBuilder log;
        static readonly System.Random Rng = new System.Random(2810);

        public static void Run()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            Backup();
            Restore();
            var scene = EditorSceneManager.OpenScene(Scene);
            log = new StringBuilder();
            ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); td = ter.terrainData; tp = ter.transform.position;
            groundLayer = ter.gameObject.layer; fBorder = null;
            Folders();
            LoadDesign();
            BuildFields();
            Kit();
            var root = GameObject.Find("Map_W85_v02").transform;
            var old = root.Find("VadimForest"); if (old) Object.DestroyImmediate(old.gameObject);
            forestRoot = new GameObject("VadimForest").transform; forestRoot.SetParent(root, false);

            OldObjectsOff(root);
            Heights();
            Splat();
            Water();
            RockWork();
            Trees();
            Rails();
            Props();
            Rocks();
            GroundCover();
            LeafLitter();
            Grass();
            WaterQueryData();
            ForestFogOff();
            SwampSinkZone();
            TerrainMatte(); OilOffBeach(); BeachOilBack(); NearFoliageFeature(); UnderwaterObject();
            SnapLeftovers(root);

            ter.Flush();
            EditorUtility.SetDirty(td);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Out + "forest_apply.txt", log.ToString());
            Shots("");
        }

        /// <summary>Only the renders of the current scene (no rebuild).</summary>
        public static void AfterShots()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            EditorSceneManager.OpenScene(Scene);
            PrepareForShots();
            Shots("");
        }

        static void Folders()
        {
            foreach (var sub in new[] { "", "/Models", "/Materials", "/Meshes", "/Prefabs", "/Textures", "/Data" })
            {
                string p = Dir + sub; if (AssetDatabase.IsValidFolder(p)) continue;
                string parent = p.Substring(0, p.LastIndexOf('/')), name = p.Substring(p.LastIndexOf('/') + 1);
                AssetDatabase.CreateFolder(parent, name);
            }
            foreach (var g in AssetDatabase.FindAssets("t:Mesh", new[] { Dir + "/Meshes" })) AssetDatabase.DeleteAsset(AssetDatabase.GUIDToAssetPath(g));
        }

        // ================================================================================================ design data

        static readonly Dictionary<string, List<Vector2>> Dsg = new();
        static Color[] maskPx, refPx; static int mW, mH; static Vector2 mO;
        static List<Vector2> Lake, Swamp, Stream, PathUp, PathWb, PathRed, Gat, GatLink, GatReturn, ValleyLink, ValleyKeep, Brook;
        static Vector2 WagonP, TunnelP, BridgeP, DenP, BigPine; static List<Vector2> Hills, Npc, Stash;
        static List<List<Vector2>> KeepStreets = new(), OldRoads = new();

        static void LoadDesign()
        {
            Dsg.Clear(); KeepStreets.Clear(); OldRoads.Clear();
            foreach (var raw in File.ReadAllLines(Dir + "/Data/forest_design_v01.txt"))
            {
                var t = raw.Trim().Split(' '); if (t.Length == 0 || t[0].Length == 0) continue;
                var pts = new List<Vector2>();
                for (int i = 1; i + 1 < t.Length; i += 2) pts.Add(new Vector2(float.Parse(t[i], System.Globalization.CultureInfo.InvariantCulture), float.Parse(t[i + 1], System.Globalization.CultureInfo.InvariantCulture)));
                Dsg[t[0]] = pts;
                if (t[0].StartsWith("street_")) KeepStreets.Add(pts);
                if (t[0].StartsWith("oldroad_") && t[0] != "oldroad_forest_to_valley") OldRoads.Add(pts);
            }
            Lake = Dsg["lake"]; Swamp = Dsg["swamp"]; OldSwamp = Dsg.TryGetValue("swamp_v1", out var sv1) ? sv1 : null; Stream = Dsg["stream"]; PathUp = Dsg["path_up"]; PathWb = Dsg["path_wb"]; PathRed = Dsg["path_red"];
            Gat = Dsg["gat"]; GatLink = Dsg["gat_link"]; GatReturn = Dsg.TryGetValue("gat_return", out var gr) ? gr : null; Brook = Dsg.TryGetValue("brook", out var bk) && bk.Count > 3 ? bk : null; ValleyLink = Dsg["valley_link"]; ValleyKeep = Dsg["valley_keep"];
            WagonP = Dsg["wagon"][0]; TunnelP = Dsg["tunnel"][0]; BridgeP = Dsg["bridge"][0]; DenP = Dsg["den"][0]; BigPine = Dsg["big_pine"][0];
            Hills = new List<Vector2>(Dsg["hills"]); Hills.AddRange(HillsExtra); Npc = Dsg["npc"]; Stash = Dsg["stash"];
            // the forest_to_valley road west of the red path goes (it ran parallel to it); its kept part is protected below
            var tvAll = Dsg["oldroad_forest_to_valley"]; var cut = ValleyKeep[0];
            int ci = 0; for (int i = 1; i < tvAll.Count; i++) if ((tvAll[i] - cut).sqrMagnitude < (tvAll[ci] - cut).sqrMagnitude) ci = i;
            OldRoads.Add(tvAll.Take(ci + 1).ToList());
            var win = Dsg["mask_window"]; mO = win[0]; mW = (int)win[1].x; mH = (int)win[1].y;
            var tex = new Texture2D(2, 2); tex.LoadImage(File.ReadAllBytes(Dir + "/Data/forest_mask_v01.png")); maskPx = tex.GetPixels();
            var tex2 = new Texture2D(2, 2); tex2.LoadImage(File.ReadAllBytes(Dir + "/Data/forest_ref_v01.png")); refPx = tex2.GetPixels();
            if (tex.width != mW || tex.height != mH || tex2.width != mW) throw new System.Exception("forest masks: unexpected size");
            log.AppendLine($"design: lake {Lake.Count} pts, swamp {Swamp.Count}, stream {Stream.Count}, paths {PathUp.Count}/{PathWb.Count}/{PathRed.Count}, old roads {OldRoads.Count}, kept streets {KeepStreets.Count}");
        }

        static Color MaskSample(Color[] px, Vector2 p)
        {
            float u = p.x - mO.x - .5f, v = p.y - mO.y - .5f;
            int i0 = Mathf.Clamp(Mathf.FloorToInt(u), 0, mW - 1), j0 = Mathf.Clamp(Mathf.FloorToInt(v), 0, mH - 1);
            int i1 = Mathf.Min(i0 + 1, mW - 1), j1 = Mathf.Min(j0 + 1, mH - 1); float fu = Mathf.Clamp01(u - i0), fv = Mathf.Clamp01(v - j0);
            if (u < -1 || v < -1 || u > mW || v > mH) return Color.clear;
            return Color.Lerp(Color.Lerp(px[j0 * mW + i0], px[j0 * mW + i1], fu), Color.Lerp(px[j1 * mW + i0], px[j1 * mW + i1], fu), fv);
        }
        /// <summary>Edit weight: 1 inside the forest (and its band to the Hamlet), 0 on the Hamlet, the roads and everything outside.</summary>
        static float M(Vector2 p) => MaskSample(maskPx, p).r;
        // Vadim 28.10: the north and west parts of the swamp became forest (design key swamp_v1 = the old outline):
        // there the reference (drawn for the old swamp: open, no trees) reads as an ordinary mixed stand
        static float RefTrees(Vector2 p) => WasSwamp(p) ? .62f : MaskSample(refPx, p).r;
        static bool WasSwamp(Vector2 p) => OldSwamp != null && p.x > 198f && p.x < 292f && p.y > 194f && p.y < 312f && InOutline(OldSwamp, p) && !InOutline(Swamp, p);
        static bool InOutline(List<Vector2> poly, Vector2 p)
        {
            bool inside = false;
            for (int i = 0, j = poly.Count - 1; i < poly.Count; j = i++)
                if ((poly[i].y > p.y) != (poly[j].y > p.y) && p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x) inside = !inside;
            return inside;
        }
        static List<Vector2> OldSwamp;
        static float RefRocks(Vector2 p) => MaskSample(refPx, p).g;
        static float RefOpen(Vector2 p) => WasSwamp(p) ? .18f : MaskSample(refPx, p).b;

        // ================================================================================================ distance fields (0.5 m)

        sealed class Field
        {
            public readonly int W, H; public readonly Vector2 O; public const float C = .5f;
            public readonly float[] D, S; public readonly byte[] Id; public readonly sbyte[] Side;
            public Field(Vector2 o, int w, int h) { O = o; W = w; H = h; D = new float[w * h]; S = new float[w * h]; Id = new byte[w * h]; Side = new sbyte[w * h]; for (int i = 0; i < D.Length; i++) D[i] = 999f; }
            public void AddLine(List<Vector2> pl, byte id, float R, bool closed = false)
            {
                float acc = 0f; int n = pl.Count;
                for (int k = 0; k < (closed ? n : n - 1); k++)
                {
                    Vector2 a = pl[k], b = pl[(k + 1) % n], ab = b - a; float l2 = ab.sqrMagnitude, L = Mathf.Sqrt(l2);
                    int x0 = Mathf.Max(0, Mathf.FloorToInt((Mathf.Min(a.x, b.x) - R - O.x) / C)), x1 = Mathf.Min(W - 1, Mathf.CeilToInt((Mathf.Max(a.x, b.x) + R - O.x) / C));
                    int z0 = Mathf.Max(0, Mathf.FloorToInt((Mathf.Min(a.y, b.y) - R - O.y) / C)), z1 = Mathf.Min(H - 1, Mathf.CeilToInt((Mathf.Max(a.y, b.y) + R - O.y) / C));
                    for (int j = z0; j <= z1; j++) for (int i = x0; i <= x1; i++)
                    {
                        var p = new Vector2(O.x + i * C, O.y + j * C);
                        float t = l2 < 1e-8f ? 0f : Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2); var q = a + ab * t; float d = (p - q).magnitude;
                        int o = j * W + i; if (d >= D[o]) continue;
                        D[o] = d; S[o] = acc + t * L; Id[o] = id; Side[o] = (sbyte)((ab.x * (p.y - a.y) - ab.y * (p.x - a.x)) >= 0 ? 1 : -1);
                    }
                    acc += L;
                }
            }
            public void Sign(List<Vector2> poly)
            {   // scanline fill: inside -> distance negative
                for (int j = 0; j < H; j++)
                {
                    float z = O.y + j * C; var xs = new List<float>();
                    for (int k = 0; k < poly.Count; k++)
                    {
                        Vector2 a = poly[k], b = poly[(k + 1) % poly.Count];
                        if ((a.y > z) != (b.y > z)) xs.Add(a.x + (z - a.y) / (b.y - a.y) * (b.x - a.x));
                    }
                    xs.Sort();
                    for (int k = 0; k + 1 < xs.Count; k += 2)
                    {
                        int i0 = Mathf.Max(0, Mathf.CeilToInt((xs[k] - O.x) / C)), i1 = Mathf.Min(W - 1, Mathf.FloorToInt((xs[k + 1] - O.x) / C));
                        for (int i = i0; i <= i1; i++) D[j * W + i] = -Mathf.Abs(D[j * W + i]);
                    }
                }
            }
            int Idx(Vector2 p) { int i = Mathf.Clamp(Mathf.RoundToInt((p.x - O.x) / C), 0, W - 1), j = Mathf.Clamp(Mathf.RoundToInt((p.y - O.y) / C), 0, H - 1); return j * W + i; }
            public float Dist(Vector2 p)
            {   // bilinear (signed fields stay smooth across the outline)
                float u = (p.x - O.x) / C, v = (p.y - O.y) / C; int i0 = Mathf.Clamp(Mathf.FloorToInt(u), 0, W - 2), j0 = Mathf.Clamp(Mathf.FloorToInt(v), 0, H - 2);
                float fu = Mathf.Clamp01(u - i0), fv = Mathf.Clamp01(v - j0);
                return Mathf.Lerp(Mathf.Lerp(D[j0 * W + i0], D[j0 * W + i0 + 1], fu), Mathf.Lerp(D[(j0 + 1) * W + i0], D[(j0 + 1) * W + i0 + 1], fu), fv);
            }
            public float Along(Vector2 p) => S[Idx(p)];
            public byte Which(Vector2 p) => Id[Idx(p)];
            public int SideOf(Vector2 p) => Side[Idx(p)];
        }

        static Field fPath, fStream, fLake, fSwamp, fRail, fGat, fOldRoad, fKeepRoad, fGully, fBrook;
        static readonly Vector2 FO = new Vector2(150, 20); const int FW = 820, FH = 1000;
        // path ids: 1 up, 2 wagon-bridge, 3 red, 4 gat link, 5 valley link, 6 gat return trail
        static readonly float[] PathHalf = { 0f, 2.1f, 1.25f, 1.45f, 0.9f, 2.4f, .85f };
        static List<Vector2>[] PathLines;
        static Vector2 RailA, RailB; static float RailLen;
        static List<Vector2> GullyLine;

        static void BuildFields()
        {
            PathLines = new[] { null, PathUp, PathWb, PathRed, GatLink, ValleyLink, GatReturn };
            fPath = new Field(FO, FW, FH);
            for (byte k = 1; k < PathLines.Length; k++) if (PathLines[k] != null && PathLines[k].Count > 1) fPath.AddLine(PathLines[k], k, 14f);
            fStream = new Field(FO, FW, FH); fStream.AddLine(Stream, 1, 34f);
            fBrook = null; if (Brook != null) { fBrook = new Field(FO, FW, FH); fBrook.AddLine(Brook, 1, 12f); }
            fLake = new Field(FO, FW, FH); fLake.AddLine(Lake, 1, 30f, true); fLake.Sign(Lake);
            fSwamp = new Field(FO, FW, FH); fSwamp.AddLine(Swamp, 1, 30f, true); fSwamp.Sign(Swamp);
            fGat = new Field(FO, FW, FH); fGat.AddLine(Gat, 1, 8f);
            fOldRoad = new Field(FO, FW, FH); foreach (var r in OldRoads) fOldRoad.AddLine(r, 1, 8f);
            fKeepRoad = new Field(FO, FW, FH); foreach (var r in KeepStreets) fKeepRoad.AddLine(r, 1, 10f); fKeepRoad.AddLine(ValleyKeep, 2, 10f);
            // rail: from the portal face (in the west ridge) to the dead end behind the wagon
            var dir = (WagonP - TunnelP).normalized;
            RailA = new Vector2(198.6f, TunnelP.y + (198.6f - TunnelP.x) * dir.y / dir.x);
            RailB = WagonP + dir * 7.6f; RailLen = (RailB - RailA).magnitude;
            fRail = new Field(FO, FW, FH); fRail.AddLine(new List<Vector2> { RailA, RailB }, 1, 14f);
            // the den's side gully: from the den down to the stream
            float best = 1e9f; Vector2 js = Stream[0];
            foreach (var q in Stream) { float d = (q - DenP).sqrMagnitude; if (d < best && q.y < DenP.y + 6f) { best = d; js = q; } }
            GullyLine = new List<Vector2>(); for (int i = 0; i <= 20; i++) { float t = i / 20f; var q = Vector2.Lerp(DenP, js, t); q.y += Mathf.Sin(t * 3.1416f) * 2.2f; GullyLine.Add(q); }
            fGully = new Field(FO, FW, FH); fGully.AddLine(GullyLine, 1, 16f);
            // lake pier spot (east shore, by the NPC spot)
            { var want = new Vector2(409f, 228f); var sp = Lake.OrderBy(q => (q - want).sqrMagnitude).First(); var cen = new Vector2(Lake.Average(q => q.x), Lake.Average(q => q.y)); PierShore = sp; PierDir = (cen - sp).normalized; }
            log.AppendLine($"rail {RailA} -> {RailB} ({RailLen:0.0} m); gully den {DenP} -> {js}");
        }

        static float PathDist(Vector2 p, out byte id, out float s) { id = fPath.Which(p); s = fPath.Along(p); return fPath.Dist(p); }
        /// <summary>Distance to the nearest path edge (negative on the path).</summary>
        static float PathEdge(Vector2 p) { float d = PathDist(p, out byte id, out _); return id == 0 ? 999f : d - PathHalf[id]; }

        // ================================================================================================ noise

        static float Fbm(float x, float y, int oct)
        {
            float s = 0f, a = .5f, f = 1f, norm = 0f;
            for (int o = 0; o < oct; o++) { s += a * Mathf.PerlinNoise(x * f + 31.7f * o + 11.3f, y * f + 17.3f * o + 5.1f); norm += a; a *= .5f; f *= 2f; }
            return s / norm;
        }
        static float Sm(float a, float b, float x) { float t = Mathf.Clamp01((x - a) / (b - a)); return t * t * (3f - 2f * t); }
        static float R01() => (float)Rng.NextDouble();
        static float RRange(float a, float b) => a + (b - a) * (float)Rng.NextDouble();

        // ================================================================================================ kit: materials, models, prefabs

        const string KitSrc = @"C:\Users\chern_0eqkb03\VolunteersBuilds\forest_kit_v02\fbx_final\";
        const string LodSrc = @"C:\Users\chern_0eqkb03\VolunteersBuilds\forest_build\lod\";
        const string WagonSrc = @"C:\Users\chern_0eqkb03\VolunteersBuilds\wagon_model_v03\";
        const string PropSrc = @"C:\Users\chern_0eqkb03\VolunteersBuilds\forest_props_v01\fbx\";
        // pass 3 (Vadim 28.10): approved Bush_v05 / Blueberry_v05 replace the round lime Bush_Small / Blueberry_Bush, the spiky grass clumps are out;
        // the approved Birch_v06 (upright oval crown, white trunk to the ground) replaces the kit birch
        const string BushSrc = @"C:\Users\chern_0eqkb03\VolunteersBuilds\forest_kit_v02\fbx_final_birch_v05\";
        const string BirchSrc = @"C:\Users\chern_0eqkb03\VolunteersBuilds\forest_kit_v02\fbx_final_birch_v06\";
        static readonly string[] TreeNames = { "Fir_Young", "Fir_Mid", "Fir_Big", "Fir_Old", "Pine_18", "Pine_20", "Pine_25", "Birch" };
        static readonly string[] SmallNames = { "Boulder_1", "Boulder_2", "Boulder_3", "Boulder_4", "Boulder_5", "Boulder_6", "Cones", "Fern", "Log_Rotten", "Reeds", "Stump" };
        static readonly string[] BushNames = { "Bush_v05", "Blueberry_v05" };
        const string UgSrc = @"C:\Users\chern_0eqkb03\VolunteersBuilds\forest_kit_v02\fbx_final_undergrowth_v01\";   // build_undergrowth_v01.py
        static readonly string[] UgNames = { "Shrub_S_v01", "Shrub_M_v01", "Shrub_L_v01", "Clump_A_v01", "Clump_B_v01", "Clump_C_v01", "Fern_v01", "Blueberry_Twig_v01" };

        sealed class Item { public string name; public Mesh mesh; public Material[] mats; public Matrix4x4 local; public Bounds bounds; }
        static readonly Dictionary<string, Item> Items = new();
        static readonly Dictionary<string, Material> Mats = new();
        static readonly Dictionary<string, GameObject> TreePrefabs = new();
        static Shader windShader, litShader;
        // Vadim 28.10: tree leaf cards turn see-through near the camera (no green screen inside a crown)
        const string NearShaderName = "OnlyVolunteers/Forest/FoliageNearFade_v01";
        static Shader NearShader => Shader.Find(NearShaderName);
        // see-through below 1.5 m, solid from 4.5 m, nearly invisible when touching (Vadim 28.10: radius a bit smaller, strength as is)
        static void NearFadeParams(Material m) { m.SetVector("_NearFade", new Vector4(1.5f, 4.5f, 0f, 0f)); m.SetFloat("_NearAlpha", .04f); }

        static Color S(float r, float g, float b) => new Color(r, g, b, 1f);   // sRGB as typed in materials.json
        static readonly Color StoneGrey = new Color(.44f, .445f, .45f, 1f);   // = VadimMountainApply.StoneColor: one grey for boulders, portal rock, mountain walls
        const string SignTex = "/Textures/Sign_BuyingBlood_v01.png";          // pass 3: the wagon notice in English (signs in English)

        static Material WindMat(string name, Color c, float response, float flex, float cull, bool vtint = false)
        {
            string p = Dir + "/Materials/" + name + ".mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (!m) { m = new Material(windShader) { name = name }; AssetDatabase.CreateAsset(m, p); }
            m.shader = name.StartsWith("FK_Leaf") && NearShader ? NearShader : windShader; m.enableInstancing = true;
            m.SetColor("_BaseColor", c); m.SetFloat("_WindResponse", response); m.SetFloat("_FlexibleHeight", flex); m.SetFloat("_TipFlash", .025f);
            m.SetFloat("_Cull", cull); m.SetFloat("_UseVertexTint", vtint ? 1f : 0f); m.SetFloat("_UseVertexMask", 0f); m.SetFloat("_Cutoff", 0f);
            m.SetVector("_WindPivotOS", Vector4.zero); if (m.shader == NearShader) NearFadeParams(m);
            EditorUtility.SetDirty(m); Mats[name] = m; return m;
        }

        static Material LitMat(string name, Color c, float smooth = .06f, float metal = 0f, Texture tex = null, Vector2? tile = null)
        {
            string p = Dir + "/Materials/" + name + ".mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (!m) { m = new Material(litShader) { name = name }; AssetDatabase.CreateAsset(m, p); }
            m.shader = litShader; m.enableInstancing = true;
            m.SetColor("_BaseColor", c); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
            m.SetTexture("_BaseMap", tex); m.SetTextureScale("_BaseMap", tile ?? Vector2.one);
            EditorUtility.SetDirty(m); Mats[name] = m; return m;
        }

        static void KitMaterials()
        {
            windShader = Shader.Find("OnlyVolunteers/Wind/v03/GenericFoliageScaled"); litShader = Shader.Find("Universal Render Pipeline/Lit");
            if (!windShader || !litShader) throw new System.Exception("forest: shaders missing");
            // trees: in-game wind settings of Conifers_v04_03 (response .028, stiff 9 m), two-sided foliage cards
            WindMat("FK_Bark", S(.408f, .314f, .235f), .028f, 9f, 2f);
            WindMat("FK_Leaf", S(.361f, .588f, .251f), .028f, 9f, 0f);
            WindMat("FK_LeafDark", S(.227f, .431f, .22f), .028f, 9f, 0f);
            WindMat("FK_LeafLight", S(.525f, .69f, .29f), .028f, 9f, 0f);
            WindMat("FK_LeafPine", S(.173f, .376f, .259f), .028f, 9f, 0f);
            WindMat("FK_BirchBark", S(.86f, .85f, .8f), .028f, 9f, 2f);
            WindMat("FK_BirchMark", S(.2f, .19f, .17f), .028f, 9f, 0f);
            // ground plants (merged chunks: the pivot is the chunk's, so only a breath of wind)
            WindMat("FK_Plant_Leaf", S(.361f, .588f, .251f), .02f, .6f, 0f);
            WindMat("FK_Plant_LeafDark", S(.227f, .431f, .22f), .02f, .6f, 0f);
            WindMat("FK_Plant_LeafLight", S(.525f, .69f, .29f), .02f, .6f, 0f);
            WindMat("FK_Plant_Bark", S(.408f, .314f, .235f), .0f, 1f, 2f);
            WindMat("FK_Berry", S(.2f, .24f, .48f), .02f, .6f, 2f);
            WindMat("FK_Grass_VC", Color.white, .05f, .6f, 0f, true);
            WindMat("FK_ReedHead", S(.36f, .22f, .11f), .05f, 1.5f, 2f);
            LitMat("FK_Cone", S(.47f, .31f, .18f));
            LitMat("FK_Moss", S(.42f, .5f, .25f), .04f);
            LitMat("FK_Rock", StoneGrey, .05f);     // pass 3: the mountains' neutral grey (MT_stone_grey), not the beige kit stone
            LitMat("FK_WoodCut", S(.72f, .58f, .40f));
            LitMat("FK_WoodRotten", S(.52f, .40f, .29f));
            LitMat("FK_Log_Bark", S(.408f, .314f, .235f));
        }

        /// <summary>Copies an FBX into the project (once), imports it readable with the axis conversion baked and its materials remapped.</summary>
        static GameObject ImportModel(string src, string dstName, System.Func<string, Material> mapMat)
        {
            string dst = Dir + "/Models/" + dstName;
            if (!File.Exists(dst) || new FileInfo(dst).Length != new FileInfo(src).Length) { File.Copy(src, dst, true); AssetDatabase.ImportAsset(dst, ImportAssetOptions.ForceUpdate); }
            var mi = (ModelImporter)AssetImporter.GetAtPath(dst);
            bool dirty = false;
            if (!mi.isReadable) { mi.isReadable = true; dirty = true; }
            if (!mi.bakeAxisConversion) { mi.bakeAxisConversion = true; dirty = true; }
            if (mi.importAnimation) { mi.importAnimation = false; dirty = true; }
            if (mi.materialImportMode != ModelImporterMaterialImportMode.ImportStandard) { mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard; dirty = true; }
            if (mi.meshCompression != ModelImporterMeshCompression.Off) { mi.meshCompression = ModelImporterMeshCompression.Off; dirty = true; }
            if (dirty) mi.SaveAndReimport();
            var embedded = AssetDatabase.LoadAllAssetRepresentationsAtPath(dst).OfType<Material>().ToList();
            var remaps = mi.GetExternalObjectMap();
            var names = embedded.Select(m => m.name).Concat(remaps.Keys.Where(k => k.type == typeof(Material)).Select(k => k.name)).Distinct().ToList();
            bool changed = false;
            foreach (var n in names)
            {
                var want = mapMat(n); if (!want) continue;
                var id = new AssetImporter.SourceAssetIdentifier(typeof(Material), n);
                if (remaps.TryGetValue(id, out var cur) && cur == want) continue;
                mi.RemoveRemap(id); mi.AddRemap(id, want); changed = true;
            }
            if (changed) mi.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<GameObject>(dst);
        }

        static Item ItemOf(string name, GameObject model)
        {
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model); inst.transform.position = Vector3.zero; inst.transform.rotation = Quaternion.identity; inst.transform.localScale = Vector3.one;
            var mf = inst.GetComponentInChildren<MeshFilter>(); var mr = mf.GetComponent<MeshRenderer>();
            var it = new Item { name = name, mesh = mf.sharedMesh, mats = mr.sharedMaterials, local = mf.transform.localToWorldMatrix };
            Object.DestroyImmediate(inst);
            var b = new Bounds(); bool first = true;
            foreach (var v in it.mesh.vertices) { var w = it.local.MultiplyPoint3x4(v); if (first) { b = new Bounds(w, Vector3.zero); first = false; } else b.Encapsulate(w); }
            if (b.size.z > b.size.y * 1.6f && (name.StartsWith("Fir") || name.StartsWith("Pine") || name.StartsWith("Birch") || name == "Reeds"))
            {   // the up axis came in as Z: turn it up
                it.local = Matrix4x4.Rotate(Quaternion.Euler(-90, 0, 0)) * it.local; b = new Bounds(); first = true;
                foreach (var v in it.mesh.vertices) { var w = it.local.MultiplyPoint3x4(v); if (first) { b = new Bounds(w, Vector3.zero); first = false; } else b.Encapsulate(w); }
                log.AppendLine($"kit {name}: up axis fixed");
            }
            it.bounds = b; return it;
        }

        /// <summary>A model whose origin is on its floor (the wagon: on the rail top): turn the axis that starts at the floor up.</summary>
        static void Upright(Item it, float tall)
        {
            var b = it.bounds; if (Mathf.Abs(b.min.y) < .5f && b.max.y > tall * .8f) return;
            Vector3 up = Vector3.zero;
            if (Mathf.Abs(b.min.z) < .5f && b.max.z > tall * .8f) up = Vector3.forward; else if (Mathf.Abs(b.max.z) < .5f && b.min.z < -tall * .8f) up = Vector3.back;
            else if (Mathf.Abs(b.min.x) < .5f && b.max.x > tall * .8f) up = Vector3.right; else if (Mathf.Abs(b.max.x) < .5f && b.min.x < -tall * .8f) up = Vector3.left;
            else if (Mathf.Abs(b.max.y) < .5f && b.min.y < -tall * .8f) up = Vector3.down;
            if (up == Vector3.zero) { log.AppendLine($"upright {it.name}: no floor axis found, bounds {b}"); return; }
            it.local = Matrix4x4.Rotate(Quaternion.FromToRotation(up, Vector3.up)) * it.local;
            var nb = new Bounds(); bool first = true;
            foreach (var v in it.mesh.vertices) { var w = it.local.MultiplyPoint3x4(v); if (first) { nb = new Bounds(w, Vector3.zero); first = false; } else nb.Encapsulate(w); }
            it.bounds = nb; log.AppendLine($"upright {it.name}: {up} turned up, bounds now {nb.min:F2}..{nb.max:F2}");
        }

        static Material KitMap(string fbxMat, bool plant)
        {
            string n = fbxMat.Replace(".001", "");
            if (plant)
            {
                if (n == "FK_Leaf") n = "FK_Plant_Leaf"; else if (n == "FK_LeafDark") n = "FK_Plant_LeafDark"; else if (n == "FK_LeafLight") n = "FK_Plant_LeafLight"; else if (n == "FK_Bark") n = "FK_Plant_Bark";
            }
            else if (n == "FK_Bark" && fbxMat != "FK_Bark") n = "FK_Bark";
            return Mats.TryGetValue(n, out var m) ? m : null;
        }

        static void Kit()
        {
            KitMaterials();
            // stumps and logs: bark without wind
            foreach (var n in SmallNames)
            {
                bool plant = n == "Fern" || n == "Stump" || n == "Log_Rotten";
                var model = ImportModel(KitSrc + n + ".fbx", n + ".fbx", m => (n == "Stump" || n == "Log_Rotten") && m.StartsWith("FK_Bark") ? Mats["FK_Log_Bark"] : KitMap(m, plant));
                Items[n] = ItemOf(n, model);
            }
            foreach (var n in BushNames) Items[n] = ItemOf(n, ImportModel(BushSrc + n + ".fbx", n + ".fbx", m => KitMap(m, true)));
            foreach (var n in UgNames) Items[n] = ItemOf(n, ImportModel(UgSrc + n + ".fbx", n + ".fbx", m => KitMap(m, true)));
            foreach (var n in TreeNames)
            {
                bool birch = n == "Birch";
                Items[n] = ItemOf(n, birch ? ImportModel(BirchSrc + "Birch_v06.fbx", "Birch_v06.fbx", m => KitMap(m, false)) : ImportModel(KitSrc + n + ".fbx", n + ".fbx", m => KitMap(m, false)));
                for (int l = 1; l <= 2; l++)
                {
                    string ln = n + "_LOD" + l, src = birch ? BirchSrc + "Birch_v06_LOD" + l + ".fbx" : LodSrc + ln + ".fbx";
                    if (File.Exists(src)) Items[ln] = ItemOf(ln, ImportModel(src, birch ? "Birch_v06_LOD" + l + ".fbx" : ln + ".fbx", m => KitMap(m, false)));
                }
                TreePrefabs[n] = TreePrefab(n);
            }
            PropsKit();
            var sb = new StringBuilder("kit:");
            foreach (var kv in Items) sb.Append($" {kv.Key} {kv.Value.bounds.size.x:0.0}x{kv.Value.bounds.size.y:0.0}x{kv.Value.bounds.size.z:0.0} mats {kv.Value.mats.Length};");
            log.AppendLine(sb.ToString());
        }

        static readonly Dictionary<string, (float r, float h)> TrunkCollider = new()
        {
            ["Fir_Young"] = (.12f, 2.2f), ["Fir_Mid"] = (.28f, 5f), ["Fir_Big"] = (.4f, 6f), ["Fir_Old"] = (.38f, 6f),
            ["Pine_18"] = (.3f, 8f), ["Pine_20"] = (.32f, 8f), ["Pine_25"] = (.36f, 9f), ["Birch"] = (.2f, 7f)
        };

        /// <summary>The fir prefab with leaf materials that never fade near the camera (the border row stays solid at the barrier).</summary>
        static GameObject WallPrefab(string n)
        {
            var src = TreePrefabs[n]; var go = (GameObject)PrefabUtility.InstantiatePrefab(src); PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            go.name = "FK_" + n + "_Wall";
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var ms = r.sharedMaterials;
                for (int i = 0; i < ms.Length; i++)
                {
                    if (!ms[i] || !ms[i].name.StartsWith("FK_Leaf")) continue;
                    string mp = Dir + "/Materials/" + ms[i].name + "_Wall.mat"; var wm = AssetDatabase.LoadAssetAtPath<Material>(mp);
                    if (!wm) { wm = new Material(ms[i]) { name = ms[i].name + "_Wall" }; AssetDatabase.CreateAsset(wm, mp); }
                    wm.CopyPropertiesFromMaterial(ms[i]); wm.shader = windShader; wm.enableInstancing = true; EditorUtility.SetDirty(wm); ms[i] = wm;
                }
                r.sharedMaterials = ms;
            }
            var pf = PrefabUtility.SaveAsPrefabAsset(go, Dir + "/Prefabs/FK_" + n + "_Wall.prefab"); Object.DestroyImmediate(go); return pf;
        }

        static GameObject TreePrefab(string n)
        {
            var go = new GameObject("FK_" + n);
            var lods = new List<LOD>(); float[] th = { .45f, .17f, .01f };
            for (int l = 0; l <= 2; l++)
            {
                var it = l == 0 ? Items[n] : Items.TryGetValue(n + "_LOD" + l, out var li) ? li : null; if (it == null) continue;
                var c = new GameObject(n + "_LOD" + l); c.transform.SetParent(go.transform, false);
                c.transform.localPosition = it.local.GetColumn(3); c.transform.localRotation = it.local.rotation; c.transform.localScale = it.local.lossyScale;
                c.AddComponent<MeshFilter>().sharedMesh = it.mesh; var r = c.AddComponent<MeshRenderer>(); r.sharedMaterials = it.mats;
                r.shadowCastingMode = l == 2 ? UnityEngine.Rendering.ShadowCastingMode.Off : UnityEngine.Rendering.ShadowCastingMode.On;
                lods.Add(new LOD(th[Mathf.Min(l, 2)], new Renderer[] { r }));
            }
            if (lods.Count > 1) { var lg = go.AddComponent<LODGroup>(); lg.SetLODs(lods.ToArray()); lg.RecalculateBounds(); }
            var (cr, ch) = TrunkCollider[n];
            var cc = go.AddComponent<CapsuleCollider>(); cc.radius = cr; cc.height = ch; cc.center = new Vector3(0, ch * .5f, 0);
            string p = Dir + "/Prefabs/FK_" + n + ".prefab";
            var pf = PrefabUtility.SaveAsPrefabAsset(go, p); Object.DestroyImmediate(go); return pf;
        }

        // ================================================================================================ terrain heights

        const float LakeY = 4.0f, SwampY = 4.5f;
        // pass 3 (ref 21/02): real height changes, 9-14 m hills (slopes kept under ~27 deg: wide radii), two more hills between the paths
        static readonly float[] HillH = { 12.5f, 11f, 13.5f, 9.5f, 9f, 8.5f }, HillR = { 47f, 42f, 48f, 38f, 33f, 30f };
        static readonly Vector2[] HillsExtra = { new Vector2(318f, 182f), new Vector2(247f, 106f) };
        static float[,] Y0, Y1; static int hI0, hJ0, hW, hH; static float hsx, hsz;
        static float bridgeDeckY, streamTotal, streamShore, sWater;
        static float[] bedS; static float[] bedY;     // stream bed profile (s -> y)
        static float denFloorY;
        static readonly Rect OldLakeBox = Rect.MinMaxRect(328, 214, 396, 274);

        static Vector2 HP(int i, int j) => new Vector2(tp.x + (hI0 + i) * hsx, tp.z + (hJ0 + j) * hsz);
        static float GridY(float[,] g, Vector2 p)
        {
            float u = (p.x - tp.x) / hsx - hI0, v = (p.y - tp.z) / hsz - hJ0;
            int i0 = Mathf.Clamp(Mathf.FloorToInt(u), 0, hW - 2), j0 = Mathf.Clamp(Mathf.FloorToInt(v), 0, hH - 2); float fu = Mathf.Clamp01(u - i0), fv = Mathf.Clamp01(v - j0);
            return Mathf.Lerp(Mathf.Lerp(g[j0, i0], g[j0, i0 + 1], fu), Mathf.Lerp(g[j0 + 1, i0], g[j0 + 1, i0 + 1], fu), fv);
        }
        static float SoftMin(float a, float b, float k) { float h = Mathf.Clamp01(.5f + .5f * (b - a) / k); return Mathf.Lerp(b, a, h) - k * h * (1f - h); }
        static float StreamBase(float s)
        {
            if (bedS == null) return 0f;
            if (s <= bedS[0]) return bedY[0];
            for (int i = 1; i < bedS.Length; i++) if (s <= bedS[i]) return Mathf.Lerp(bedY[i - 1], bedY[i], (s - bedS[i - 1]) / (bedS[i] - bedS[i - 1]));
            return bedY[bedY.Length - 1];
        }
        /// <summary>The bed: the base profile plus a pool-and-riffle rhythm (flatter pools, a ~0.1 m step every ~13 m): the water steps and reads as moving.</summary>
        static float StreamBed(float s)
        {
            float b = StreamBase(s), a = streamOut + 6f, e = sWater - 12f;
            if (s > a && s < e)
            {
                float slope = (StreamBase(s - 1f) - StreamBase(s + 1f)) * .5f, amp = Mathf.Clamp(slope * 13f * .8f, 0f, .13f);
                float u = (s - a) / 13f, steps = Mathf.Floor(u) + Sm(.86f, 1f, u - Mathf.Floor(u));
                b += amp * (u - steps) * Sm(0f, 1f, (s - a) / 4f) * Sm(0f, 1f, (e - s) / 4f);
            }
            return b;
        }
        static float streamOut, brookS0, brookS1, brookTotal, fordS = -1f, fordPathS = -1f, fordY;
        static float BrookWater(float s) => Mathf.Lerp(SwampY - .02f, LakeY - .02f, Mathf.Clamp01((s - brookS0) / Mathf.Max(1f, brookS1 - brookS0)));
        // the water stands .42 m over the bed; over the last 8 m to the old water line it thins out into the sea level (no lip, no overlap)
        static float StreamWater(float s) => Mathf.Max(StreamBed(s) + .42f * (1f - Sm(sWater - 8f, sWater, s)), .015f);
        static float HillAt(Vector2 p, out float top)
        {
            var w = p + new Vector2(Fbm(p.x / 25f, p.y / 25f, 2) - .5f, Fbm(p.x / 25f + 7.7f, p.y / 25f + 3.1f, 2) - .5f) * 12f;
            float hsum = 0f; top = 0f;
            for (int k = 0; k < Hills.Count && k < HillH.Length; k++)
            {
                var c = Hills[k]; var d = w - c; d.x *= 1f + .25f * Mathf.Sin(k * 1.7f); float t = 1f - d.magnitude / HillR[k];
                if (t <= 0f) continue; float sh = Mathf.Pow(Sm(0f, 1f, t), 1.25f) * HillH[k]; hsum += sh; top = Mathf.Max(top, Sm(.45f, .8f, t));
            }
            return hsum;
        }
        // Vadim 28.10: the whole forest border (west and south sea coast, round to the east cliff; only the Quiet Valley exit stays
        // open) is a narrow row of trees right on the cliff top, with gaps where the cliff and the sea show. The invisible barrier
        // runs just on the forest side of it. Design key "border" = Vadim's rough line, snapped here to the real cliff top.
        const float WallBand = 6f, BarrierOff = 7.5f;
        static List<Vector2> BorderEdge, BorderInland; static Field fBorder, fFoot;
        // the wall fills the coastal rock rim's inner slope and stands WallBand deep on the forest floor at its foot (Vadim 28.10:
        // from the forest you see a wall of trees, not the rock rim)
        static bool InThicket(Vector2 p) { float d = Border().Dist(p); return d < .5f && fFoot.Dist(p) > -WallBand; }
        static Field Border() { if (fBorder == null) BuildBorder(); return fBorder; }

        static void BuildBorder()
        {
            // the hand line every 1 m
            var hand = new List<Vector2>(); var src = Dsg["border"];
            for (int i = 0; i + 1 < src.Count; i++) { float len = (src[i + 1] - src[i]).magnitude; int n = Mathf.Max(1, Mathf.CeilToInt(len)); for (int k = 0; k < n; k++) hand.Add(Vector2.Lerp(src[i], src[i + 1], (float)k / n)); }
            hand.Add(src[src.Count - 1]);
            int N = hand.Count; var nrm = new Vector2[N]; var off = new float[N];
            bool InWin(Vector2 q) => q.x > 151f && q.x < 559f && q.y > 21f && q.y < 519f;
            for (int k = 0; k < N; k++)
            {
                var t = (hand[Mathf.Min(k + 3, N - 1)] - hand[Mathf.Max(k - 3, 0)]).normalized; nrm[k] = new Vector2(-t.y, t.x);   // left of the line = inland
                float found = float.NaN;
                for (float sd = -14f; sd <= 26f && float.IsNaN(found); sd += .5f)
                {
                    var a = hand[k] - nrm[k] * sd; var b = a - nrm[k] * 1.5f; if (!InWin(a) || !InWin(b)) continue;
                    float ya = OldY(a); if (ya < 1.5f || ya - OldY(b) < .9f) continue;                // a steep drop seaward ...
                    for (float u = 2f; u <= 24f; u += 1f) { var c = a - nrm[k] * u; if (InWin(c) && OldY(c) < 1.2f) { found = sd; break; } }   // ... down to the sea
                }
                off[k] = float.IsNaN(found) ? 0f : found;
            }
            BorderEdge = new List<Vector2>(); var inl = new List<Vector2>();
            for (int k = 0; k < N; k++)
            {
                var w = new List<float>(); for (int d = -6; d <= 6; d++) w.Add(off[Mathf.Clamp(k + d, 0, N - 1)]); w.Sort();
                BorderEdge.Add(hand[k] - nrm[k] * w[6]);
            }
            // the foot of the rim: the first 6 m flat stretch (< 1.6 m rise) inland of the cliff top
            var foot = new float[N];
            for (int k = 0; k < N; k++)
            {
                foot[k] = 20f;
                for (float u = 0f; u <= 20f; u += 1f)
                {
                    float lo = 1e9f, hi = -1e9f;
                    for (float v = 0f; v <= 6f; v += 1f) { float h = OldY(BorderEdge[k] + nrm[k] * (u + v)); lo = Mathf.Min(lo, h); hi = Mathf.Max(hi, h); }
                    if (hi - lo < 1.6f) { foot[k] = u; break; }
                }
            }
            var footLine = new List<Vector2>();
            for (int k = 0; k < N; k++)
            {
                var w = new List<float>(); for (int d = -6; d <= 6; d++) w.Add(foot[Mathf.Clamp(k + d, 0, N - 1)]); w.Sort();
                footLine.Add(BorderEdge[k] + nrm[k] * w[6]); inl.Add(BorderEdge[k] + nrm[k] * (w[6] + BarrierOff));
            }
            BorderInland = inl;
            var polyF = new List<Vector2>(footLine) { new Vector2(560f, footLine[N - 1].y), new Vector2(560f, 520f), new Vector2(150f, 520f), new Vector2(150f, footLine[0].y) };
            fFoot = new Field(FO, FW, FH); fFoot.AddLine(footLine, 1, 30f); fFoot.Sign(polyF);
            log.AppendLine($"border rim foot: {foot.Average():0.0} m inland of the cliff top on average (max {foot.Max():0})");
            var poly = new List<Vector2>(BorderEdge) { new Vector2(560f, BorderEdge[N - 1].y), new Vector2(560f, 520f), new Vector2(150f, 520f), new Vector2(150f, BorderEdge[0].y) };
            fBorder = new Field(FO, FW, FH); fBorder.AddLine(BorderEdge, 1, 30f); fBorder.Sign(poly);
            log.AppendLine($"border: {N} m of line, snapped to the cliff top at {off.Count(o => o != 0f)} m");
        }

        static void Heights()
        {
            int R = td.heightmapResolution; hsx = td.size.x / (R - 1); hsz = td.size.z / (R - 1); float sy = td.size.y;
            hI0 = Mathf.FloorToInt((150f - tp.x) / hsx); int i1 = Mathf.CeilToInt((560f - tp.x) / hsx);
            hJ0 = Mathf.FloorToInt((20f - tp.z) / hsz); int j1 = Mathf.CeilToInt((520f - tp.z) / hsz);
            hW = i1 - hI0 + 1; hH = j1 - hJ0 + 1;
            var h = td.GetHeights(hI0, hJ0, hW, hH);
            Y0 = new float[hH, hW]; var Y = new float[hH, hW];
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++) Y0[j, i] = Y[j, i] = tp.y + h[j, i] * sy;

            // where relief may change: not on / near steep ground (Fedya's cliffs and rock faces keep their ground)
            var steep = new float[hH, hW];
            for (int j = 1; j < hH - 1; j++) for (int i = 1; i < hW - 1; i++)
            {
                float gx = (Y0[j, i + 1] - Y0[j, i - 1]) / (2f * hsx), gz = (Y0[j + 1, i] - Y0[j - 1, i]) / (2f * hsz);
                steep[j, i] = Mathf.Atan(Mathf.Sqrt(gx * gx + gz * gz)) * Mathf.Rad2Deg > 23f ? 1f : 0f;
            }
            var near = Blur(steep, Mathf.RoundToInt(7f / hsx), Mathf.RoundToInt(7f / hsz), 2);

            // 1. the old round lake basin is filled back to forest ground
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j); if (!OldLakeBox.Contains(p) || M(p) < .5f) continue;
                if (Y[j, i] < 4.45f) Y[j, i] = Mathf.Max(Y[j, i], 4.45f + (Fbm(p.x / 9f, p.y / 9f, 2) - .5f) * .3f);
            }
            Y = Blur(Y, 2, 3, 1, (i, j) => OldLakeBox.Contains(HP(i, j)) && M(HP(i, j)) > .5f);

            // 2. relief: hills 3-8 m, gentle rolls, micro relief (only on flat ground, faded at the mask edge)
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j); float m = M(p); if (m <= 0f) continue;
                float allow = m * Mathf.Clamp01(1f - near[j, i] * 2.5f); if (allow <= 0f) continue;
                float hill = HillAt(p, out float top);
                float roll = (Fbm(p.x / 55f + 3.3f, p.y / 55f + 9.1f, 3) - .5f) * 3.4f;
                float micro = (Fbm(p.x / 11f + 13f, p.y / 11f + 2f, 3) - .5f) * .9f + (Mathf.PerlinNoise(p.x / 4.3f + 5f, p.y / 4.3f + 1f) - .5f) * .28f;
                float crest = top > 0f ? Mathf.Pow(1f - Mathf.Abs(2f * Mathf.PerlinNoise(p.x / 9f + 41f, p.y / 9f + 7f) - 1f), 2.2f) * 1.1f * top : 0f;
                float rough = InThicket(p) ? (Fbm(p.x / 5.5f + 2f, p.y / 5.5f + 8f, 2) - .5f) * .9f : 0f;
                Y[j, i] += allow * (hill + roll + micro + crest + rough);
            }

            // 3. the swamp: still pools between mud banks and hummocks, a flat water level
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j); float ds = fSwamp.Dist(p); if (ds > 5f) continue;
                if (ds > 0f) { if (M(p) > .2f) Y[j, i] = Mathf.Max(Y[j, i], SwampY + .14f + ds * .06f); continue; }
                float din = -ds, w = Sm(0f, 7f, din);
                float r = (Fbm(p.x / 9.5f + 1.3f, p.y / 9.5f + 4.4f, 3) - .5f) * 1.6f + (Fbm(p.x / 3.7f + 9f, p.y / 3.7f + 2f, 2) - .5f) * .4f
                          - .22f * Sm(5f, 22f, din) + .3f * (1f - Sm(0f, 6f, din)) + .5f * Mathf.Max(0f, Mathf.PerlinNoise(p.x / 2.6f + 3f, p.y / 2.6f + 7f) - .58f) / .42f;
                r += .07f * Mathf.Clamp(r / .05f, -1f, 1f);   // no near-flat water line (no flicker): banks cross the level quickly
                Y[j, i] = Mathf.Lerp(Mathf.Max(Y[j, i], SwampY + .14f), SwampY + r, w);
            }

            // 4. the lake: basin with a shallow shelf, banks always above the water
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j); float dl = fLake.Dist(p); if (dl > 7f) continue;
                // one continuous profile: steep through the water line (0.2 m inside the outline, a thin foam line), gentle bank above, basin below
                // the bank drops off right under the water line (~1 m deep 1.2 m out): the shore foam stays a thin line, not a white rim
                float shore = dl >= .5f ? LakeY + .21f + .14f * (dl - .5f) : dl >= -.2f ? LakeY + .06f + .3f * dl : dl >= -1.4f ? LakeY - .8f * (-.2f - dl) : LakeY - .96f;
                if (dl >= 0f) { Y[j, i] = Mathf.Max(Y[j, i], shore); continue; }
                float din = -dl;
                Y[j, i] = shore - 1.3f * Sm(1.4f, 14f, din) + (Fbm(p.x / 7f, p.y / 7f, 2) - .5f) * .5f * Sm(3f, 10f, din);
            }

            // 5. the stream ravine: V cut from the lake to the sea (soil walls ~31 deg in the forest, rock gorge through the coastal rim)
            {
                var sAt = new float[Stream.Count]; for (int k = 1; k < Stream.Count; k++) sAt[k] = sAt[k - 1] + (Stream[k] - Stream[k - 1]).magnitude;
                streamTotal = sAt[Stream.Count - 1];
                int kb = 0; for (int k = 1; k < Stream.Count; k++) if ((Stream[k] - BridgeP).sqrMagnitude < (Stream[kb] - BridgeP).sqrMagnitude) kb = k;
                int ks = Stream.Count - 1; while (ks > 0 && GridY(Y0, Stream[ks]) < 1.0f) ks--;          // the old shore line
                int kw = Stream.Count - 1; while (kw > 0 && GridY(Y0, Stream[kw]) < 0f) kw--;           // the old water line
                int km = 0; for (int k = 1; k < Stream.Count; k++) if ((Stream[k] - new Vector2(382.3f, 84.2f)).sqrMagnitude < (Stream[km] - new Vector2(382.3f, 84.2f)).sqrMagnitude) km = k;
                // a stone sill at the outlet holds the lake (no water plane over a lower channel), the stream starts below it
                float sW = Mathf.Max(sAt[kw], sAt[ks] + .5f); sWater = sW;
                float sOut = 0f; for (int k = 0; k < Stream.Count; k++) if (fLake.Dist(Stream[k]) >= 0f) { sOut = sAt[k]; break; }
                streamOut = sOut;
                bedS = new[] { 0f, sOut + .9f, sOut + 3.4f, sAt[kb], sAt[km], sAt[ks], sW, streamTotal + 1.5f };
                bedY = new[] { LakeY - .6f, LakeY - .2f, LakeY - .78f, 2.95f, 1.05f, .12f, -.04f, -.9f };
                streamShore = sAt[ks];
                log.AppendLine($"stream {streamTotal:0} m: bridge at s {sAt[kb]:0}, mid {sAt[km]:0}, old shore {sAt[ks]:0}");
                // deck level of the footbridge: the forest ground at the two ends, before the cut
                var dirB = (Stream[Mathf.Min(kb + 2, Stream.Count - 1)] - Stream[Mathf.Max(kb - 2, 0)]).normalized; var nB = new Vector2(-dirB.y, dirB.x);
                bridgeDeckY = Mathf.Max(GridY(Y, BridgeP + nB * 6.5f), GridY(Y, BridgeP - nB * 6.5f)) + .05f;
            }
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j); float ds = fStream.Dist(p); if (ds > 33f) continue;
                float s = fStream.Along(p), bed = StreamBed(s), e0 = Y0[j, i] - bed;
                float b = .75f + .35f * Fbm(p.x / 8f + 2f, p.y / 8f, 2);
                float k = Mathf.Lerp(.5f, 1.8f, Sm(5.5f, 9.5f, e0)) * (1f + .12f * fStream.SideOf(p) * (Fbm(s / 14f, 3.3f, 2) - .5f) * 2f);
                if (s > streamTotal - .5f) b += (s - streamTotal + .5f) * .8f;                       // the mouth opens to the sea
                float yv = bed + Mathf.Min(Mathf.Max(0f, ds - b) * 1.25f, .62f) + Mathf.Max(0f, ds - b - .5f) * k;   // channel, then the V
                Y[j, i] = SoftMin(Y[j, i], yv, .45f);
            }

            // 5b. the brook: swamp -> lake, a small winding channel; it fords path_up
            if (Brook != null)
            {
                var sB = new float[Brook.Count]; for (int k = 1; k < Brook.Count; k++) sB[k] = sB[k - 1] + (Brook[k] - Brook[k - 1]).magnitude;
                brookTotal = sB[Brook.Count - 1];
                int k0 = 0; while (k0 < Brook.Count - 1 && fSwamp.Dist(Brook[k0]) < 0f) k0++;
                int k1 = k0; while (k1 < Brook.Count - 1 && fLake.Dist(Brook[k1]) > 0f) k1++;
                brookS0 = sB[k0]; brookS1 = sB[k1];
                fordS = -1f;
                for (int k = k0; k <= k1; k++) { float d = PathDist(Brook[k], out byte id, out float ps); if (id == 1 && d < 1.2f && (fordS < 0f || d < 1f)) { fordS = sB[k]; fordPathS = ps; } }
                fordY = fordS >= 0f ? BrookWater(fordS) - .01f : 0f;
                for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
                {
                    var p = HP(i, j); float d = fBrook.Dist(p); if (d > 9f) continue;
                    float sb = fBrook.Along(p), bed = BrookWater(sb) - .3f, b = .42f + .2f * Fbm(p.x / 6f + 9f, p.y / 6f, 2);
                    float yb = bed + Mathf.Min(Mathf.Max(0f, d - b) * 1.3f, .42f) + Mathf.Max(0f, d - b - .32f) * .55f;
                    Y[j, i] = SoftMin(Y[j, i], yb, .3f);
                }
                log.AppendLine($"brook {brookTotal:0} m: leaves the swamp at s {brookS0:0}, enters the lake at s {brookS1:0}, ford over path_up at s {fordS:0} (path s {fordPathS:0}, road {fordY:0.00} m)");
            }

            // 6. the den's side gully (a dry side valley, flat floor at the den)
            {
                float Lg = 0f; for (int k = 1; k < GullyLine.Count; k++) Lg += (GullyLine[k] - GullyLine[k - 1]).magnitude;
                denFloorY = GridY(Y, DenP) - 1.35f; float yJ = StreamBed(fStream.Along(GullyLine[GullyLine.Count - 1])) + .6f;
                if (denFloorY < yJ + .3f) denFloorY = yJ + .3f;
                for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
                {
                    var p = HP(i, j); float dg = fGully.Dist(p); if (dg > 15f) continue;
                    float t = Mathf.Clamp01(fGully.Along(p) / Lg), bedG = Mathf.Lerp(denFloorY, yJ, t * t * (3f - 2f * t));
                    float bw = Mathf.Lerp(3.4f, 1.0f, t), yg = bedG + Mathf.Max(0f, dg - bw) * .55f;
                    Y[j, i] = SoftMin(Y[j, i], yg, .4f);
                }
            }

            // 7. the crag round the blocked tunnel: the ridge face moved forward so the portal sits in rock
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j); var q = new Vector2((p.x - 194.2f) / 6.5f, (p.y - RailA.y) / 10.5f); float e = q.magnitude; if (e > 1.6f) continue;
                float dz = Mathf.Abs(p.y - RailA.y), frontX = RailA.x - .1f - Mathf.Max(0f, dz - 4.3f) * .35f + (Fbm(p.y / 5f, 7.7f, 2) - .5f) * (dz > 4.3f ? 1.4f : 0f);
                float back = frontX - p.x; if (back < 0f) continue;
                float baseY = GridY(Y0, RailA + (RailB - RailA).normalized * 1.5f);
                float target = Mathf.Min(12.8f + (Fbm(p.x / 4f, p.y / 4f, 2) - .5f) * 1.8f, baseY + back * 1.9f);
                float w = Sm(1.6f, .8f, e);
                Y[j, i] = Mathf.Max(Y[j, i], Mathf.Lerp(Y[j, i], target, w));
            }
            // pass 3: smooth rock steps - the crag's creases and its foot softened (the portal face itself stays as it is)
            Y = Blur(Y, 1, 1, 2, (i, j) => { var q = HP(i, j); return new Vector2((q.x - 194.2f) / 6.5f, (q.y - RailA.y) / 10.5f).magnitude < 1.7f && Mathf.Abs(q.y - RailA.y) > 4.6f; });

            // 8. the wagon clearing: gentler ground round the wagon and the camp
            {
                var cc = WagonP + new Vector2(1f, 7f); float sum = 0f; int n = 0;
                for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++) { var p = HP(i, j); if ((p - cc).sqrMagnitude < 144f) { sum += Y[j, i]; n++; } }
                float avg = n > 0 ? sum / n : 4.5f;
                for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++) { var p = HP(i, j); float d = (p - cc).magnitude; if (d < 15f) Y[j, i] = Mathf.Lerp(Y[j, i], avg, .7f * Sm(15f, 7f, d)); }
            }

            // 9. the rail bed: a smooth grade from the portal to the dead end
            float yA = GridY(Y, RailA + (RailB - RailA).normalized * 1.5f), yB = GridY(Y, RailB);
            railBedA = Mathf.Min(yA, 4.6f); railBedB = yB;
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j); float d = fRail.Dist(p); if (d > 5f) continue;
                float s = fRail.Along(p); if (s < .3f || s > RailLen + 3f) continue;
                float by = RailBed(s) - .05f;
                Y[j, i] = Mathf.Lerp(by, Y[j, i], Sm(2.0f, 4.8f, d) * (s > RailLen ? 1f : 1f));
            }

            // 10. paths: smooth along, level across, never on a cross slope
            for (byte id = 1; id < PathLines.Length; id++)
            {
                var pl = PathLines[id]; if (pl == null || pl.Count < 2) continue;
                var ys = new float[pl.Count];
                for (int k = 0; k < pl.Count; k++) ys[k] = GridY(Y, pl[k]);
                for (int k = 0; k < pl.Count; k++) if ((pl[k] - BridgeP).magnitude < 7.5f) ys[k] = bridgeDeckY;
                for (int it = 0; it < 4; it++)
                {
                    var c = (float[])ys.Clone();
                    for (int k = 0; k < pl.Count; k++)
                    {
                        if ((pl[k] - BridgeP).magnitude < 7.5f) continue;
                        float s2 = 0f; int n2 = 0; for (int q = Mathf.Max(0, k - 5); q <= Mathf.Min(pl.Count - 1, k + 5); q++) { s2 += c[q]; n2++; }
                        ys[k] = s2 / n2;
                    }
                }
                if (id == 1 && fordS >= 0f)        // the road dips into the brook's ford (a film of water over it)
                    for (int k = 0; k < pl.Count; k++) ys[k] = Mathf.Min(ys[k], fordY + Mathf.Max(0f, Mathf.Abs(k - fordPathS) - 2.4f) * .085f);
                float maxG = id == 1 ? .11f : .17f;
                for (int k = 1; k < pl.Count; k++) ys[k] = Mathf.Clamp(ys[k], ys[k - 1] - maxG, ys[k - 1] + maxG);
                for (int k = pl.Count - 2; k >= 0; k--) ys[k] = Mathf.Clamp(ys[k], ys[k + 1] - maxG, ys[k + 1] + maxG);
                pathY[id] = ys;
            }
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j); float d = PathDist(p, out byte id, out float s); if (id == 0 || pathY[id] == null) continue;
                float half = PathHalf[id]; if (d > half + 2.8f) continue;
                if ((p - BridgeP).magnitude < 6.8f) continue;        // under the footbridge the ravine stays
                if (fLake.Dist(p) < .5f || fSwamp.Dist(p) < -1f) continue;
                var ys = pathY[id]; int k = Mathf.Clamp(Mathf.RoundToInt(s), 0, ys.Length - 1);
                float t = Sm(half + 2.8f, half + .25f, d);
                Y[j, i] = Mathf.Lerp(Y[j, i], ys[k] - .03f, t);
            }

            // 11. outside the forest, the ravine corridor, the crag and the rail nothing moves
            Y1 = new float[hH, hW]; int changed = 0;
            for (int j = 0; j < hH; j++) for (int i = 0; i < hW; i++)
            {
                var p = HP(i, j);
                float infl = Mathf.Max(M(p), Sm(34f, 26f, fStream.Dist(p)));
                infl = Mathf.Max(infl, Sm(16f, 10f, fGully.Dist(p)));
                if (fBrook != null) infl = Mathf.Max(infl, Sm(10f, 7f, fBrook.Dist(p)));
                infl = Mathf.Max(infl, Sm(1.7f, 1.3f, new Vector2((p.x - 194.2f) / 6.5f, (p.y - RailA.y) / 10.5f).magnitude));
                infl = Mathf.Max(infl, Sm(6f, 5f, fRail.Dist(p)));
                float y = Mathf.Lerp(Y0[j, i], Y[j, i], Mathf.Clamp01(infl));
                Y1[j, i] = y; if (Mathf.Abs(y - Y0[j, i]) > .05f) changed++;
                h[j, i] = Mathf.Clamp01((y - tp.y) / sy);
            }
            td.SetHeights(hI0, hJ0, h);
            log.AppendLine($"heights: {changed} samples changed; lake {LakeY} m, swamp {SwampY} m, bridge deck {bridgeDeckY:0.00} m, rail bed {railBedA:0.00} -> {railBedB:0.00} m, den floor {denFloorY:0.00} m");
        }

        static readonly float[][] pathY = new float[7][];
        static float railBedA, railBedB;
        static float RailBed(float s) => Mathf.Lerp(railBedA, railBedB, Sm(0f, 1f, Mathf.Clamp01(s / RailLen)));
        static float NewY(Vector2 p) => ter.SampleHeight(new Vector3(p.x, 0, p.y)) + tp.y;
        static float OldY(Vector2 p) => Y0 != null ? GridY(Y0, p) : NewY(p);
        static float Slope(Vector2 p) => td.GetSteepness((p.x - tp.x) / td.size.x, (p.y - tp.z) / td.size.z);

        static float[,] Blur(float[,] src, int rx, int rz, int passes, System.Func<int, int, bool> only = null)
        {
            int H = src.GetLength(0), W = src.GetLength(1); var a = (float[,])src.Clone(); var b = new float[H, W];
            for (int pass = 0; pass < passes; pass++)
            {
                for (int j = 0; j < H; j++) { float acc = 0; int n = 0; for (int i = -rx; i <= rx; i++) if (i >= 0 && i < W) { acc += a[j, i]; n++; }
                    for (int i = 0; i < W; i++) { b[j, i] = acc / n; int o = i - rx, ni = i + rx + 1; if (o >= 0) { acc -= a[j, o]; n--; } if (ni < W) { acc += a[j, ni]; n++; } } }
                for (int i = 0; i < W; i++) { float acc = 0; int n = 0; for (int j = -rz; j <= rz; j++) if (j >= 0 && j < H) { acc += b[j, i]; n++; }
                    for (int j = 0; j < H; j++) { a[j, i] = acc / n; int o = j - rz, nj = j + rz + 1; if (o >= 0) { acc -= b[o, i]; n--; } if (nj < H) { acc += b[nj, i]; n++; } } }
            }
            if (only != null) for (int j = 0; j < H; j++) for (int i = 0; i < W; i++) if (!only(i, j)) a[j, i] = src[j, i];
            return a;
        }

        // ------------------------------------------------------------------------------------------------ fog off + swamp (Vadim 28.10)

        /// <summary>Only these two on the current scene (no rebuild, mountains untouched).</summary>
        public static void FogAndSwamp()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            var scene = EditorSceneManager.OpenScene(Scene); log = new StringBuilder();
            LoadDesign(); forestRoot = GameObject.Find("Map_W85_v02").transform.Find("VadimForest");
            ForestFogOff(); SwampSinkZone();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Out + "forest_fog_swamp.txt", log.ToString());
        }

        /// <summary>No forest fog: the district "forest" (dense milk fog, 8-65 m haze) gets the village haze and a new id, so
        /// the district fog / aerial passes give it zero weight. The palette (exposure, colour) stays.</summary>
        static void ForestFogOff()
        {
            int n = 0;
            foreach (var atm in Object.FindObjectsByType<OnlyVolunteers.Map.Look.V3.DistrictAtmosphere19>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                foreach (var d in atm.districts) if (d.id == "forest" || d.id == "forest_clear") { d.id = "forest_clear"; d.fogStart = 95f; d.fogEnd = 480f; n++; }
                VillageGrade(atm.districts); EditorUtility.SetDirty(atm);
            }
            // the weather components (DistrictWeather19V02..V05, read by the sky bridge even when disabled) keep their own lists
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (!mb || !mb.GetType().Name.StartsWith("DistrictWeather")) continue;
                var f = mb.GetType().GetField("districts"); if (f == null || !(f.GetValue(mb) is System.Array arr)) continue;
                foreach (var d in arr)
                {
                    var t = d.GetType(); var idF = t.GetField("id");
                    if (idF == null || !((string)idF.GetValue(d)).StartsWith("forest")) continue;
                    idF.SetValue(d, "forest_clear"); t.GetField("fogStart")?.SetValue(d, 95f); t.GetField("fogEnd")?.SetValue(d, 480f); n++;
                }
                VillageGrade(arr); EditorUtility.SetDirty(mb);
            }
            ForestWeather();
            log.AppendLine($"forest fog off: {n} district entries");
        }

        /// <summary>Vadim 28.10: no lighting filter in the forest. Each district also has a weather entry (the sky bridge blends
        /// sun / ambient / cloud / shadow by district): the forest one was overcast and dim (cloud .94, sun .43, ambient .7,
        /// shadow .16). It becomes a copy of the village weather in every component that holds districts + weather.</summary>
        static void ForestWeather()
        {
            int n = 0;
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (!mb) continue;
                var t = mb.GetType(); var fd = t.GetField("districts"); var fw = t.GetField("weather");
                if (fd == null || fw == null || !(fd.GetValue(mb) is System.Collections.IList ds) || !(fw.GetValue(mb) is System.Collections.IList ws)) continue;
                int fi = -1, vi = -1;
                for (int i = 0; i < ds.Count; i++)
                {
                    var id = ds[i] == null ? null : (string)ds[i].GetType().GetField("id")?.GetValue(ds[i]);
                    if (id != null && id.StartsWith("forest")) fi = i; else if (id == "village") vi = i;
                }
                if (fi < 0 || vi < 0 || fi >= ws.Count || vi >= ws.Count || ws[vi] == null) continue;
                var wt = ws[vi].GetType(); ws[fi] = JsonUtility.FromJson(JsonUtility.ToJson(ws[vi]), wt);
                if (fw.FieldType.IsArray) fw.SetValue(mb, ws);
                EditorUtility.SetDirty(mb); n++;
            }
            log.AppendLine($"forest weather = village: {n} components");
        }

        /// <summary>Vadim 28.10: no darker "filter" in the forest at any time of day: the forest district takes the village grading
        /// (palette, exposure, saturation, contrast, temperature) instead of its dark mysterious one (exposure .12, saturation -28).</summary>
        static void VillageGrade(System.Collections.IEnumerable list)
        {
            object village = null; foreach (var d in list) if (d != null && (string)d.GetType().GetField("id")?.GetValue(d) == "village") village = d;
            if (village == null) { log.AppendLine("grade: no village entry"); return; }
            foreach (var d in list)
            {
                if (d == null || (string)d.GetType().GetField("id")?.GetValue(d) != "forest_clear") continue;
                foreach (var f in new[] { "palette", "exposure", "saturation", "contrast", "temperature", "fogColour" })
                {
                    var fi = d.GetType().GetField(f); if (fi != null) fi.SetValue(d, fi.GetValue(village));
                }
                var mood = d.GetType().GetField("mood"); if (mood != null) mood.SetValue(d, "clear forest, village light (Vadim 28.10)");
            }
        }

        /// <summary>Vadim 28.10: white sparkles on the ground. Every terrain layer took its smoothness from the albedo alpha
        /// (SmoothnessSource 1 = diffuse alpha, opaque = 1), so grass and pebbles shone like wet glass and the normal maps glittered.
        /// All layers of the scene terrains: constant matte smoothness.</summary>
        static void TerrainMatte()
        {
            var done = new HashSet<TerrainLayer>();
            foreach (var t in Object.FindObjectsByType<Terrain>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                foreach (var l in t.terrainData ? t.terrainData.terrainLayers : new TerrainLayer[0])
                {
                    if (!l || !done.Add(l)) continue;
                    var so = new SerializedObject(l);
                    so.FindProperty("m_SmoothnessSource").intValue = 2; so.FindProperty("m_Smoothness").floatValue = .04f; so.FindProperty("m_Metallic").floatValue = 0f;
                    so.ApplyModifiedPropertiesWithoutUndo(); EditorUtility.SetDirty(l);
                }
            log.AppendLine($"terrain matte: {done.Count} layers -> constant smoothness .04");
        }

        /// <summary>Vadim 28.10: oil (mazut) only on the beach. Oil decals anywhere else go.</summary>
        static void OilOffBeach()
        {
            var beach = new Rect(770f, 26f, 770f, 168f);   // the "beach" district (x 790..1520, z 46..174) + 20 m
            int gone = 0, kept = 0;
            foreach (var tr in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None).ToList())
            {
                if (!tr || !(tr.name.StartsWith("Decal_T124_oil") || tr.name == "T124_oil_film")) continue;
                if (tr.childCount > 0) continue;   // a group: its children decide
                var r = tr.GetComponent<Renderer>(); var p = r ? r.bounds.center : tr.position;
                if (beach.Contains(new Vector2(p.x, p.z))) { kept++; continue; }
                if (PrefabUtility.IsPartOfPrefabInstance(tr) && !PrefabUtility.IsOutermostPrefabInstanceRoot(tr.gameObject)) { tr.gameObject.SetActive(false); gone++; continue; }
                Object.DestroyImmediate(tr.gameObject); gone++;
            }
            log.AppendLine($"oil off the beach: {gone} decals removed, {kept} kept on the beach");
        }

        // the 6 oil decals of the beach (x 790..1520, z 46..174), removed by the first OilOffBeach (it read the 0,0,0 transform): name mesh material
        static readonly string[] BeachOil = {
            "Decal_T124_oil_gptwear_14_2 80c3fad26b08dec4ea99ffef06197d82 2c46687b8aee54d48a025b67bc7522ca",
            "Decal_T124_oil_gptwear_18_2 09d504247063ad14ca26b3f8dacc5bcd 2c46687b8aee54d48a025b67bc7522ca",
            "Decal_T124_oil_oil_12_1 1d6b8a79004d35d4b9f802fe70b5b54f 50dbf2a2d2f65314fa7d6b7e8af4951e",
            "Decal_T124_oil_gptwear_16_2 a4a51fdd8654f3b48a0df01116186afa 2c46687b8aee54d48a025b67bc7522ca",
            "Decal_T124_oil_oil_13_1 fa3ca6e40e1b22b43abd66befa7625ec 50dbf2a2d2f65314fa7d6b7e8af4951e",
            "Decal_T124_oil_film_oilfilm_6_0 781499808ffdf5e41881f849bb8f8a44 61efbdbad936fee47b0e175e4c3e596b" };

        static void BeachOilBack()
        {
            var hooks = GameObject.Find("Map_W85_v02").transform.Find("DecalHooks_W86"); if (!hooks) { log.AppendLine("beach oil: no DecalHooks_W86"); return; }
            var grp = hooks.Find("T124_oil"); if (!grp) { grp = new GameObject("T124_oil").transform; grp.SetParent(hooks, false); }
            int made = 0;
            foreach (var row in BeachOil)
            {
                var a = row.Split(' '); if (grp.Find(a[0])) continue;
                var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(AssetDatabase.GUIDToAssetPath(a[1])); var mat = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(a[2]));
                if (!mesh || !mat) { log.AppendLine("beach oil: missing asset for " + a[0]); continue; }
                var go = new GameObject(a[0]); go.transform.SetParent(grp, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = true;
                made++;
            }
            log.AppendLine($"beach oil back: {made} decals");
        }

        /// <summary>The pass "FoliageNearFade" of the leaf shader is drawn by a RenderObjects feature after the transparents,
        /// on every renderer the game or the shots can use.</summary>
        static void NearFoliageFeature()
        {
            var assets = new List<UnityEngine.Rendering.RenderPipelineAsset> { AssetDatabase.LoadAssetAtPath<UnityEngine.Rendering.RenderPipelineAsset>("Assets/Settings/PC_RPAsset.asset"), UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline };
            for (int q = 0; q < QualitySettings.names.Length; q++) assets.Add(QualitySettings.GetRenderPipelineAssetAt(q));
            int added = 0; var seen = new HashSet<Object>();
            foreach (var a in assets)
            {
                if (!(a is UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset u) || !seen.Add(u)) continue;
                var list = new SerializedObject(u).FindProperty("m_RendererDataList");
                for (int i = 0; i < list.arraySize; i++)
                {
                    var rd = list.GetArrayElementAtIndex(i).objectReferenceValue as UnityEngine.Rendering.Universal.ScriptableRendererData;
                    if (!rd || !seen.Add(rd) || rd.rendererFeatures.Any(f => f && f.name == "ForestNearFoliage")) continue;
                    var ro = ScriptableObject.CreateInstance<UnityEngine.Rendering.Universal.RenderObjects>(); ro.name = "ForestNearFoliage";
                    ro.settings.passTag = "ForestNearFoliage"; ro.settings.Event = UnityEngine.Rendering.Universal.RenderPassEvent.AfterRenderingTransparents;
                    ro.settings.filterSettings.RenderQueueType = UnityEngine.Rendering.Universal.RenderQueueType.Opaque;
                    ro.settings.filterSettings.LayerMask = ~0; ro.settings.filterSettings.PassNames = new[] { "FoliageNearFade" };
                    AssetDatabase.AddObjectToAsset(ro, rd); AssetDatabase.SaveAssets();
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(ro, out string _, out long lid);
                    var so = new SerializedObject(rd);
                    var feats = so.FindProperty("m_RendererFeatures"); feats.arraySize++; feats.GetArrayElementAtIndex(feats.arraySize - 1).objectReferenceValue = ro;
                    var map = so.FindProperty("m_RendererFeatureMap"); map.arraySize++; map.GetArrayElementAtIndex(map.arraySize - 1).longValue = lid;
                    so.ApplyModifiedPropertiesWithoutUndo(); rd.SetDirty(); EditorUtility.SetDirty(rd); added++;
                    log.AppendLine($"near foliage feature -> {AssetDatabase.GetAssetPath(rd)}");
                }
            }
            AssetDatabase.SaveAssets(); log.AppendLine($"near foliage feature: {added} renderers");
        }

        /// <summary>Vadim 28.10 pass: forest grading, matte ground, oil only on the beach, see-through crowns near the camera.
        /// Shots before and after: inside a fir crown and the ground at the wagon.</summary>
        public static void Polish()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            var scene = EditorSceneManager.OpenScene(Scene); log = new StringBuilder();
            LoadDesign(); forestRoot = GameObject.Find("Map_W85_v02").transform.Find("VadimForest");
            PolishShots("before");
            ForestFogOff(); TerrainMatte(); OilOffBeach(); NearFoliageFeature();
            if (!NearShader) throw new System.Exception("forest: near-fade shader missing");
            foreach (var n in new[] { "FK_Leaf", "FK_LeafDark", "FK_LeafLight", "FK_LeafPine" })
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/Materials/" + n + ".mat"); if (!m) { log.AppendLine("missing " + n); continue; }
                m.shader = NearShader; EditorUtility.SetDirty(m);
            }
            AssetDatabase.SaveAssets();
            PolishShots("after");
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Out + "forest_polish.txt", log.ToString());
        }

        /// <summary>Second polish run: the beach oil back, wider see-through zone in the crowns, crown shots again.</summary>
        public static void Polish2()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            var scene = EditorSceneManager.OpenScene(Scene); log = new StringBuilder();
            LoadDesign(); forestRoot = GameObject.Find("Map_W85_v02").transform.Find("VadimForest");
            BeachOilBack(); OilOffBeach();
            foreach (var n in new[] { "FK_Leaf", "FK_LeafDark", "FK_LeafLight", "FK_LeafPine" })
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/Materials/" + n + ".mat"); if (!m) continue;
                m.shader = NearShader; NearFadeParams(m); EditorUtility.SetDirty(m);
            }
            AssetDatabase.SaveAssets();
            PolishShots("after2");
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Out + "forest_polish2.txt", log.ToString());
        }

        /// <summary>Third polish: forest weather = village (no lighting filter), wider and clearer see-through crowns.</summary>
        public static void Polish3()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            var scene = EditorSceneManager.OpenScene(Scene); log = new StringBuilder();
            LoadDesign(); forestRoot = GameObject.Find("Map_W85_v02").transform.Find("VadimForest");
            ForestFogOff();
            foreach (var n in new[] { "FK_Leaf", "FK_LeafDark", "FK_LeafLight", "FK_LeafPine" })
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/Materials/" + n + ".mat"); if (!m) continue;
                m.shader = NearShader; NearFadeParams(m); EditorUtility.SetDirty(m);
            }
            AssetDatabase.SaveAssets();
            PolishShots("after3");
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Out + "forest_polish3.txt", log.ToString());
        }

        /// <summary>Everything the W86 play scene and the game pipeline need (recursive), for the push: VolunteersBuilds\w86_deps.txt.</summary>
        public static void DepsList()
        {
            var roots = new[] { Scene, "Assets/Settings/PC_RPAsset.asset", "Assets/Settings/PC_Renderer.asset", "Assets/Settings/Mobile_Renderer.asset" };
            var deps = AssetDatabase.GetDependencies(roots, true).Distinct().OrderBy(x => x).ToArray();
            File.WriteAllLines(Out + "w86_deps.txt", deps);
        }

        /// <summary>Check shots of the west border row: top view of the west strip + two views from the barrier (no save).</summary>
        public static void WallCheck()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            EditorSceneManager.OpenScene(Scene); log = new StringBuilder();
            ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); td = ter.terrainData; tp = ter.transform.position;
            var gameCams = Object.FindObjectsByType<Camera>(FindObjectsSortMode.None).Where(c => c.enabled).ToList();
            foreach (var c in gameCams) c.enabled = false;
            RenderSettings.fog = false;
            var go = new GameObject("WallCam"); var cam = go.AddComponent<Camera>(); cam.nearClipPlane = .1f; cam.farClipPlane = 2000f;
            float tdist = ter.treeDistance; ter.treeDistance = 2000f;
            // top: x 150..300, z 140..400 at 4 px/m (the barrier line drawn by the log only)
            cam.orthographic = true; cam.orthographicSize = 130f; cam.aspect = 150f / 260f;
            go.transform.position = new Vector3(225f, 400f, 270f); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(cam, 600, 1040, Out + "forest_wall_top.png"); Shot(cam, 600, 1040, Out + "forest_wall_top.png");
            ter.treeDistance = tdist; cam.orthographic = false; cam.fieldOfView = 60f;
            // from the barrier, looking out to the sea: two on the west coast, two on the south coast
            int k = 0; var bar = GameObject.Find("Map_W85_v02").transform.Find("VadimForest/Barrier_west_thicket");
            foreach (var target in new[] { new Vector2(185f, 220f), new Vector2(180f, 300f), new Vector2(300f, 72f), new Vector2(460f, 66f) })
            {
                Vector3 bp = new Vector3(target.x, 0f, target.y); float bd = 1e9f;
                if (bar) foreach (Transform c in bar) { float d = (new Vector2(c.position.x, c.position.z) - target).sqrMagnitude; if (d < bd) { bd = d; bp = c.position; } }
                var inward = (new Vector2(340f, 240f) - new Vector2(bp.x, bp.z)).normalized;
                var e = new Vector3(bp.x + inward.x * 1.5f, 0f, bp.z + inward.y * 1.5f); e.y = ter.SampleHeight(e) + tp.y + 1.7f;
                go.transform.position = e; go.transform.rotation = Quaternion.LookRotation(new Vector3(-inward.x, -.05f, -inward.y));
                Shot(cam, 1400, 800, Out + "forest_wall_ground_" + k + ".png");
                var far = e + new Vector3(inward.x, 0f, inward.y) * 10f; far.y = ter.SampleHeight(far) + tp.y + 1.7f; go.transform.position = far;
                Shot(cam, 1400, 800, Out + "forest_wall_far_" + k + ".png"); go.transform.position = e; k++;
                log.AppendLine($"view {k}: barrier box at {bp.x:0.0}, {bp.z:0.0}");
            }
            // the whole forest from above (the border row and the barrier line are what to check)
            cam.orthographic = true; cam.orthographicSize = 190f; cam.aspect = 355f / 380f; ter.treeDistance = 2000f;
            go.transform.position = new Vector3(342.5f, 400f, 230f); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(cam, 1065, 1140, Out + "forest_wall_topall.png"); Shot(cam, 1065, 1140, Out + "forest_wall_topall.png");
            ter.treeDistance = tdist; cam.orthographic = false;
            // the former north-west swamp, now forest: from its north edge looking south-east over what is left of the bog
            var sv = new Vector3(222f, 0f, 302f); sv.y = ter.SampleHeight(sv) + tp.y + 1.7f;
            go.transform.position = sv; go.transform.rotation = Quaternion.Euler(6f, 145f, 0f);
            Shot(cam, 1400, 800, Out + "forest_wall_swamp.png");
            File.WriteAllText(Out + "forest_wallcheck.txt", log.ToString());
        }

        /// <summary>The border wall as the player meets it: from 3 m and 14 m in front of the barrier, facing the wall, at free spots.</summary>
        public static void WallViews()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            EditorSceneManager.OpenScene(Scene); log = new StringBuilder();
            ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); td = ter.terrainData; tp = ter.transform.position;
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false;
            var go = new GameObject("WallCam"); var cam = go.AddComponent<Camera>(); cam.nearClipPlane = .1f; cam.farClipPlane = 2000f; cam.fieldOfView = 60f;
            var tr = td.treeInstances.Select(t => new Vector2(tp.x + t.position.x * td.size.x, tp.z + t.position.z * td.size.z)).ToList();
            bool FreeAt(Vector3 e) => !Physics.CheckSphere(e, .7f, ~0, QueryTriggerInteraction.Ignore) && !tr.Any(q => (q - new Vector2(e.x, e.z)).sqrMagnitude < 1.6f * 1.6f);
            var bar = GameObject.Find("Map_W85_v02").transform.Find("VadimForest/Barrier_west_thicket"); int k = 0;
            foreach (var target in new[] { new Vector2(185f, 220f), new Vector2(178f, 300f), new Vector2(240f, 85f), new Vector2(330f, 62f), new Vector2(460f, 66f) })
            {
                Transform best = null; float bd = 1e9f;
                foreach (Transform c in bar) { float d = (new Vector2(c.position.x, c.position.z) - target).sqrMagnitude; if (d < bd) { bd = d; best = c; } }
                var bp = best.position; var n = new Vector2(best.right.x, best.right.z).normalized;
                float hA = ter.SampleHeight(bp + new Vector3(n.x, 0, n.y) * 12f), hB = ter.SampleHeight(bp - new Vector3(n.x, 0, n.y) * 12f);
                if (Vector2.Dot(n, new Vector2(340f, 240f) - new Vector2(bp.x, bp.z)) < 0f) n = -n;   // n points inland
                foreach (float dist in new[] { 3f, 14f })
                {
                    Vector3 e = Vector3.zero; bool ok = false;
                    for (int t = 0; t < 40 && !ok; t++)
                    {
                        float side = (t % 2 == 0 ? 1 : -1) * (t / 2) * 1.5f, dd = dist + (t / 10) * 1.5f;
                        var q = new Vector2(bp.x, bp.z) + n * dd + new Vector2(-n.y, n.x) * side;
                        e = new Vector3(q.x, 0f, q.y); e.y = ter.SampleHeight(e) + tp.y + 1.7f; ok = FreeAt(e);
                    }
                    go.transform.position = e; go.transform.rotation = Quaternion.LookRotation(new Vector3(-n.x, -.03f, -n.y));
                    string f = Out + $"forest_wallview_{k}_{dist:0}.png"; Shot(cam, 1400, 800, f); Shot(cam, 1400, 800, f);
                    log.AppendLine($"view {k} {dist:0} m: {e.x:0.0}, {e.z:0.0} free={ok}");
                }
                k++;
            }
            File.WriteAllText(Out + "forest_wallviews.txt", log.ToString());
        }

        public static void WallProfile()
        {
            EditorSceneManager.OpenScene(Scene); var sb = new StringBuilder();
            var t = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>();
            var bar = GameObject.Find("Map_W85_v02").transform.Find("VadimForest/Barrier_west_thicket");
            foreach (var target in new[] { new Vector2(185f, 220f), new Vector2(178f, 300f), new Vector2(240f, 85f), new Vector2(330f, 62f), new Vector2(460f, 66f), new Vector2(200f, 140f), new Vector2(400f, 50f) })
            {
                Transform best = null; float bd = 1e9f;
                foreach (Transform c in bar) { float d = (new Vector2(c.position.x, c.position.z) - target).sqrMagnitude; if (d < bd) { bd = d; best = c; } }
                var bp = best.position; var n = new Vector2(best.right.x, best.right.z).normalized;
                if (Vector2.Dot(n, new Vector2(340f, 240f) - new Vector2(bp.x, bp.z)) < 0f) n = -n;
                sb.Append($"{bp.x:0},{bp.z:0}: ");
                for (int d = -22; d <= 30; d += 2) { var q = new Vector3(bp.x + n.x * d, 0, bp.z + n.y * d); sb.Append($"{(d == 0 ? "|" : "")}{t.SampleHeight(q) + t.transform.position.y:0} "); }
                sb.AppendLine();
            }
            File.WriteAllText(Out + "forest_wallprofile.txt", sb.ToString());
        }

        public static void WallProbe()
        {
            EditorSceneManager.OpenScene(Scene); var sb = new StringBuilder();
            foreach (var q in new[] { new Vector2(185f, 220f), new Vector2(178f, 300f), new Vector2(240f, 85f), new Vector2(330f, 62f), new Vector2(460f, 66f) })
            {
                sb.AppendLine($"== {q}");
                foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
                {
                    var b = r.bounds; var c = new Vector2(b.center.x, b.center.z);
                    if (b.size.magnitude > 400f) continue;
                    var cl = new Vector2(Mathf.Clamp(q.x, b.min.x, b.max.x), Mathf.Clamp(q.y, b.min.z, b.max.z));
                    if ((cl - q).magnitude < 14f) { var t = r.transform; string path = t.name; for (var u = t.parent; u && path.Length < 160; u = u.parent) path = u.name + "/" + path; sb.AppendLine($"  {path}  size {b.size.x:0},{b.size.y:0},{b.size.z:0}  ymax {b.max.y:0.0}"); }
                }
            }
            File.WriteAllText(Out + "forest_wallprobe.txt", sb.ToString());
        }

        static void PolishShots(string tag)
        {
            var gameCams = Object.FindObjectsByType<Camera>(FindObjectsSortMode.None).Where(c => c.enabled).ToList(); bool fogWas = RenderSettings.fog;
            foreach (var c in gameCams) c.enabled = false;
            var go = new GameObject("ForestPolishCam"); var cam = go.AddComponent<Camera>(); cam.nearClipPlane = .1f; cam.farClipPlane = 1500f; cam.fieldOfView = 60f;
            try
            {
                var ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tdd = ter.terrainData; var tpp = ter.transform.position;
                int big = System.Array.FindIndex(tdd.treePrototypes, pr => pr.prefab && pr.prefab.name.Contains("Fir_Big"));
                Vector3 best = Vector3.zero; float bd = 1e9f; var w2 = new Vector3(WagonP.x, 0f, WagonP.y);
                foreach (var ti in tdd.treeInstances)
                {
                    if (ti.prototypeIndex != big) continue;
                    var wp = tpp + Vector3.Scale(ti.position, tdd.size); float d = (new Vector3(wp.x, 0f, wp.z) - w2).sqrMagnitude;
                    if (d > 25f * 25f && d < bd) { bd = d; best = wp; }   // the nearest big fir, not on the wagon itself
                }
                // inside the crown: 1.3 m from the trunk at eye height, looking along the branches
                go.transform.position = best + new Vector3(1.3f, 1.7f, 0f); go.transform.rotation = Quaternion.Euler(4f, 0f, 0f);
                Shot(cam, 1200, 720, Out + "forest_polish_crown_" + tag + ".png");
                go.transform.position = best + new Vector3(2.6f, 1.7f, -1.2f); go.transform.rotation = Quaternion.Euler(2f, -70f, 0f);
                Shot(cam, 1200, 720, Out + "forest_polish_crown2_" + tag + ".png");
                // the ground near the wagon, looking down (the sparkles)
                var g = new Vector3(WagonP.x + 8f, 0f, WagonP.y + 10f); g.y = ter.SampleHeight(g) + tpp.y + 1.7f;
                go.transform.position = g; go.transform.rotation = Quaternion.Euler(28f, 35f, 0f);
                Shot(cam, 1600, 960, Out + "forest_polish_ground_" + tag + ".png");
                log.AppendLine($"shots {tag}: fir at {best}");
            }
            finally { Object.DestroyImmediate(go); foreach (var c in gameCams) if (c) c.enabled = true; RenderSettings.fog = fogWas; }
        }

        /// <summary>Vadim 28.10: under the sea / a lake the view is in blue water (OnlyVolunteers.Map.UnderwaterView), one per scene.</summary>
        static void UnderwaterObject()
        {
            if (Object.FindFirstObjectByType<OnlyVolunteers.Map.UnderwaterView>(FindObjectsInactive.Include)) { log.AppendLine("underwater view: present"); return; }
            var go = new GameObject("UnderwaterView"); go.transform.SetParent(GameObject.Find("Map_W85_v02").transform, false);
            go.AddComponent<OnlyVolunteers.Map.UnderwaterView>(); log.AppendLine("underwater view: added");
        }

        /// <summary>Adds the underwater view to the current scene (no rebuild).</summary>
        public static void Underwater()
        {
            var scene = EditorSceneManager.OpenScene(Scene); log = new StringBuilder();
            UnderwaterObject(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Out + "forest_underwater.txt", log.ToString());
        }

        /// <summary>The swamp pulls a walker down (OnlyVolunteers.Map.SwampSink) inside the design outline, below the mud top.</summary>
        static void SwampSinkZone()
        {
            var old = forestRoot ? forestRoot.Find("SwampSink") : null; if (old) Object.DestroyImmediate(old.gameObject);
            var go = new GameObject("SwampSink"); if (forestRoot) go.transform.SetParent(forestRoot, false);
            var s = go.AddComponent<OnlyVolunteers.Map.SwampSink>(); s.Outline = Swamp.ToArray(); s.MudTopY = SwampY + .25f;
            log.AppendLine($"swamp sink: {Swamp.Count} outline points, mud top {s.MudTopY:0.00} m");
        }

        // ================================================================================================ splat

        const int Meadow = 0, Worn = 1, Dirt = 2, ForestL = 3, WetSand = 5, Gravel = 6, RockL = 7, Pebbles = 11;

        static void Splat()
        {
            int A = td.alphamapResolution; float ax = td.size.x / A, az = td.size.z / A;
            int a0 = Mathf.FloorToInt((150f - tp.x) / ax), a1 = Mathf.CeilToInt((560f - tp.x) / ax), b0 = Mathf.FloorToInt((20f - tp.z) / az), b1 = Mathf.CeilToInt((520f - tp.z) / az);
            var al = td.GetAlphamaps(a0, b0, a1 - a0, b1 - b0); int L = td.alphamapLayers; var tgt = new float[L]; int painted = 0, erased = 0;
            // pass 3 floor (Vadim 28.10 13:45, his camp screenshots): mottled living ground instead of one dark olive layer -
            // soft moss patches in three greens (ForestL dark / Meadow / Worn warm), brown earth patches 1-4 m (Dirt), grey pebble spots (Pebbles),
            // mixed by warped noise at ~2.5 m and ~8 m. The noises are turned into ranks inside the forest, so the shares are exact.
            float[] cdfShade, cdfDirt, cdfPeb;
            {
                var ls = new List<float>(); var ld = new List<float>(); var lp = new List<float>(); var rs = new System.Random(77);
                for (int k = 0; k < 40000; k++)
                {
                    var q = new Vector2(170f + 340f * (float)rs.NextDouble(), 45f + 360f * (float)rs.NextDouble()); if (M(q) < .6f) continue;
                    FloorNoise(q, out float a, out float b, out float c); ls.Add(a); ld.Add(b); lp.Add(c);
                }
                cdfShade = ls.OrderBy(v => v).ToArray(); cdfDirt = ld.OrderBy(v => v).ToArray(); cdfPeb = lp.OrderBy(v => v).ToArray();
            }
            float Rank(float[] cdf, float v) { int k = System.Array.BinarySearch(cdf, v); if (k < 0) k = ~k; return (float)k / cdf.Length; }
            float[] share = new float[L]; float shareW = 0f;
            for (int j = 0; j < b1 - b0; j++) for (int i = 0; i < a1 - a0; i++)
            {
                var p = new Vector2(tp.x + (a0 + i + .5f) * ax, tp.z + (b0 + j + .5f) * az);
                float m = M(p), dStream = fStream.Dist(p), dGully = fGully.Dist(p), dRail = fRail.Dist(p);
                float ravine = Sm(14f, 4f, dStream) * (fLake.Dist(p) > -.5f ? 1f : 0f);
                float w = Mathf.Max(m, Mathf.Max(ravine, Mathf.Max(Sm(10f, 4f, dGully), Sm(5f, 3f, dRail))));
                if (fBrook != null) w = Mathf.Max(w, Sm(7f, 3f, fBrook.Dist(p)));
                float keep = Sm(9f, 6f, fKeepRoad.Dist(p));
                // old dirt roads that are gone: their brown goes, also where the mask fades (not on the kept Hamlet streets)
                float oldR = Sm(5.5f, 3.5f, fOldRoad.Dist(p)) * (1f - keep);
                if (w <= 0f && oldR <= 0f) continue;
                w = Mathf.Max(w * (1f - keep), oldR);
                System.Array.Clear(tgt, 0, L);
                float y = NewY(p), st = Slope(p), dens = RefTrees(p), open = RefOpen(p);
                float n1 = Fbm(p.x / 13f, p.y / 13f, 2), n2 = Mathf.PerlinNoise(p.x / 3.1f + 7f, p.y / 3.1f + 2f);
                // forest ground (pass 3): moss in three shades by the shade rank, a lighter warmer mix in the openings
                FloorNoise(p, out float fShade, out float fDirt, out float fPeb);
                float rS = Mathf.Clamp01(Rank(cdfShade, fShade) + .1f * (open - .35f) - .06f * (dens - .5f)), rD = Rank(cdfDirt, fDirt), rP = Rank(cdfPeb, fPeb);
                float dark = 1f - Sm(.16f, .34f, rS), warm = Sm(.64f, .84f, rS);
                tgt[ForestL] = dark * .85f; tgt[Meadow] = (1f - dark) * (1f - warm) + dark * .15f; tgt[Worn] = (1f - dark) * warm;
                void Mix(int layer, float a) { a = Mathf.Clamp01(a); for (int l = 0; l < L; l++) tgt[l] *= 1f - a; tgt[layer] += a; }
                Mix(Dirt, Sm(.80f, .90f, rD) * .88f);                       // brown earth patches, 1-4 m, soft rims
                Mix(Pebbles, Sm(.885f, .955f, rP) * .72f);                  // grey pebble spots, clustered by the 10 m part of the noise
                // swamp: wet mud and dark moss round the pools; a wide ragged (noise-warped) edge, no line round the bog
                float dsw = fSwamp.Dist(p), dswW = dsw + (Fbm(p.x / 6.5f + 12f, p.y / 6.5f + 4f, 2) - .5f) * 6f;
                if (dswW < 7f) { float ws = Sm(7f, -4f, dswW), wet = Sm(SwampY + .1f, SwampY - .03f, y); Mix(Worn, ws * .4f); Mix(Meadow, ws * (1f - wet) * .3f * n2); Mix(Dirt, ws * wet * .75f); }
                // lake: pebble beach ring at the water line, dark bed below
                float dl = fLake.Dist(p);
                if (dl < 1.4f) { Mix(Pebbles, Sm(1.4f, .1f, dl) * (.4f + .35f * n2) * Sm(.38f, .62f, Fbm(p.x / 7f + 50f, p.y / 7f, 2))); if (dl < -1.2f) Mix(Dirt, .55f); }
                // the stream: pebbles in the bed, worn grass on the banks, stone where it is steep
                if (ravine > 0f) { Mix(Worn, Sm(6f, 2f, dStream) * .35f); Mix(Pebbles, Sm(2.2f, 1.1f, dStream)); }
                if (fBrook != null) { float db = fBrook.Dist(p); if (db < 4f) { Mix(Worn, Sm(4f, 1.5f, db) * .35f); Mix(Pebbles, Sm(1.5f, .8f, db)); } }
                if (dGully < 4f) { Mix(Worn, .4f); Mix(Dirt, Sm(4f, 1.5f, dGully) * .45f); }
                // paths: trodden dirt with ragged edges
                float pe = PathEdge(p) + (n2 - .5f) * .6f;
                if (pe < 1.2f) { Mix(Worn, Sm(1.2f, 0f, pe) * .6f); Mix(Dirt, Sm(.6f, -.5f, pe) * .82f); }
                // rail: spilled ballast beside the bed; the wagon camp is trodden
                if (dRail < 3.2f && fRail.Along(p) > .2f && fRail.Along(p) < RailLen + 1.5f) { Mix(Gravel, Sm(3.2f, 1.6f, dRail) * .7f); }
                float dc = (p - (WagonP + new Vector2(1f, 7f))).magnitude;
                if (dc < 11f) { Mix(Worn, Sm(11f, 5f, dc) * .55f); Mix(Dirt, Sm(6f, 1f, dc) * .35f * n2); }
                if ((p - DenP).magnitude < 6f) Mix(Dirt, Sm(6f, 2f, (p - DenP).magnitude) * .5f);
                // stone where it is steep (the gorge, the crag, hill tops): one grey with the rock skins
                Mix(RockL, Sm(30f, 40f, st));
                float sum = 0f; for (int l = 0; l < L; l++) sum += tgt[l];
                for (int l = 0; l < L; l++) al[j, i, l] = Mathf.Lerp(al[j, i, l], tgt[l] / Mathf.Max(sum, 1e-4f), w);
                sum = 0f; for (int l = 0; l < L; l++) sum += al[j, i, l]; for (int l = 0; l < L; l++) al[j, i, l] /= Mathf.Max(sum, 1e-4f);
                if (m > .9f) { for (int l = 0; l < L; l++) share[l] += al[j, i, l]; shareW += 1f; }
                painted++; if (oldR > .5f) erased++;
            }
            td.SetAlphamaps(a0, b0, al);
            log.AppendLine($"splat: {painted} cells repainted ({erased} on the removed roads); forest floor shares: " + string.Join(" ", Enumerable.Range(0, L).Where(l => share[l] / Mathf.Max(1f, shareW) > .005f).Select(l => $"L{l} {100f * share[l] / Mathf.Max(1f, shareW):0}%")));
        }

        static void FloorNoise(Vector2 p, out float shade, out float dirt, out float peb)
        {
            var q = p + new Vector2(Fbm(p.x / 12f + 40.3f, p.y / 12f + 3.7f, 2) - .5f, Fbm(p.x / 12f + 9.1f, p.y / 12f + 61.2f, 2) - .5f) * 7f;   // warp: no round blobs, no lines
            shade = .62f * Fbm(q.x / 8.5f + 21f, q.y / 8.5f + 5f, 3) + .38f * Fbm(q.x / 2.7f + 3f, q.y / 2.7f + 44f, 2);
            dirt = .64f * Fbm(q.x / 3.1f + 77f, q.y / 3.1f + 13f, 2) + .36f * Fbm(q.x / 9f + 5f, q.y / 9f + 90f, 2);
            peb = .55f * Fbm(q.x / 2.2f + 31f, q.y / 2.2f + 8f, 2) + .45f * Fbm(q.x / 10f + 66f, q.y / 10f + 27f, 2);
        }

        // ================================================================================================ meshes

        static Mesh SaveMesh(string name, List<Vector3> v, List<Vector2> uv, List<int> t, List<Vector2> uv1 = null, bool recalc = true, List<Color> col = null)
        {
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.SetVertices(v); if (uv != null) m.SetUVs(0, uv); if (uv1 != null) m.SetUVs(1, uv1); if (col != null) m.SetColors(col); m.SetTriangles(t, 0);
            if (recalc) m.RecalculateNormals(); m.RecalculateBounds();
            string path = Dir + "/Meshes/" + name + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static GameObject MeshGo(string name, Transform parent, Mesh mesh, Material mat, bool collider, bool shadows = true, Material[] mats = null)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.layer = groundLayer;
            go.AddComponent<MeshFilter>().sharedMesh = mesh; var r = go.AddComponent<MeshRenderer>();
            if (mats != null) r.sharedMaterials = mats; else r.sharedMaterial = mat;
            r.shadowCastingMode = shadows ? UnityEngine.Rendering.ShadowCastingMode.On : UnityEngine.Rendering.ShadowCastingMode.Off;
            if (collider) go.AddComponent<MeshCollider>().sharedMesh = mesh;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);
            return go;
        }

        static float SignedArea(List<Vector2> poly) { float a = 0f; for (int i = 0; i < poly.Count; i++) { var p = poly[i]; var q = poly[(i + 1) % poly.Count]; a += p.x * q.y - q.x * p.y; } return a * .5f; }

        static List<Vector2> Offset(List<Vector2> poly, float d)
        {
            float sgn = SignedArea(poly) > 0 ? 1f : -1f; var o = new List<Vector2>();
            for (int i = 0; i < poly.Count; i++)
            {
                Vector2 a = poly[(i - 1 + poly.Count) % poly.Count], b = poly[i], c = poly[(i + 1) % poly.Count];
                Vector2 n1 = new Vector2(b.y - a.y, -(b.x - a.x)).normalized, n2 = new Vector2(c.y - b.y, -(c.x - b.x)).normalized;
                o.Add(b + (n1 + n2).normalized * d * sgn);
            }
            return o;
        }

        /// <summary>Ear clipping of a simple polygon (x,z), triangles facing up.</summary>
        static List<int> Triangulate(List<Vector2> poly)
        {
            var idx = Enumerable.Range(0, poly.Count).ToList(); var tri = new List<int>();
            bool ccw = SignedArea(poly) > 0;
            float Cross(Vector2 a, Vector2 b, Vector2 c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
            bool In(Vector2 p, Vector2 a, Vector2 b, Vector2 c) { float d1 = Cross(a, b, p), d2 = Cross(b, c, p), d3 = Cross(c, a, p); return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0)); }
            int guard = 0;
            while (idx.Count > 3 && guard++ < 100000)
            {
                bool cut = false;
                for (int k = 0; k < idx.Count; k++)
                {
                    int ia = idx[(k - 1 + idx.Count) % idx.Count], ib = idx[k], ic = idx[(k + 1) % idx.Count];
                    Vector2 a = poly[ia], b = poly[ib], c = poly[ic]; float cr = Cross(a, b, c);
                    if (ccw ? cr <= 1e-6f : cr >= -1e-6f) continue;
                    bool any = false;
                    foreach (int q in idx) { if (q == ia || q == ib || q == ic) continue; if (In(poly[q], a, b, c)) { any = true; break; } }
                    if (any) continue;
                    tri.AddRange(new[] { ia, ib, ic }); idx.RemoveAt(k); cut = true; break;
                }
                if (!cut) break;
            }
            if (idx.Count == 3) tri.AddRange(new[] { idx[0], idx[1], idx[2] });
            // face up (Unity: clockwise seen from above)
            for (int k = 0; k < tri.Count; k += 3)
            {
                Vector2 a = poly[tri[k]], b = poly[tri[k + 1]], c = poly[tri[k + 2]];
                var n = Vector3.Cross(new Vector3(b.x - a.x, 0, b.y - a.y), new Vector3(c.x - a.x, 0, c.y - a.y));
                if (n.y < 0) { (tri[k + 1], tri[k + 2]) = (tri[k + 2], tri[k + 1]); }
            }
            return tri;
        }

        static Mesh FlatWater(string name, List<Vector2> outline, float y)
        {
            var v = outline.Select(q => new Vector3(q.x, y, q.y)).ToList(); var uv = outline.Select(q => q / 10f).ToList(); var uv1 = outline.Select(_ => Vector2.zero).ToList();
            return SaveMesh(name, v, uv, Triangulate(outline), uv1);
        }

        // ================================================================================================ water

        static Material flowMat, swampMat;

        static void Water()
        {
            var waterRoot = GameObject.Find("Map_W85_v02/Water").transform;
            var lakeGo = waterRoot.Find("Water_Lake_01-lake");
            flowMat = lakeGo ? lakeGo.GetComponent<MeshRenderer>().sharedMaterial : AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/W85Build/Generated/v02/Materials/W85_water_flow.mat");
            // lake: same object and material, new outline (0.6 m under the banks)
            var lm = FlatWater("Water_Lake_01-lake_forest", Offset(Lake, .6f), LakeY);
            if (lakeGo) { lakeGo.GetComponent<MeshFilter>().sharedMesh = lm; var mc = lakeGo.GetComponent<MeshCollider>(); if (mc) mc.sharedMesh = lm; }
            else lakeGo = MeshGo("Water_Lake_01-lake", waterRoot, lm, flowMat, false, false).transform;
            // swamp: our water shader, dark still green-brown, no waves, no flow foam
            string sp = Dir + "/Materials/W86_water_swamp_forest.mat"; swampMat = AssetDatabase.LoadAssetAtPath<Material>(sp);
            if (!swampMat) { swampMat = new Material(flowMat) { name = "W86_water_swamp_forest" }; AssetDatabase.CreateAsset(swampMat, sp); }
            swampMat.CopyPropertiesFromMaterial(flowMat); swampMat.shader = flowMat.shader;
            swampMat.SetFloat("_ENABLEWAVE", 0f); swampMat.DisableKeyword("_ENABLEWAVE");
            swampMat.SetFloat("_OV_MeshFlow", 0f); swampMat.DisableKeyword("_OV_FLOW"); swampMat.SetFloat("_OV_FlowFoam", 0f);
            swampMat.SetColor("_Color_Shallow", new Color(.33f, .36f, .22f)); swampMat.SetColor("_Color_Deep", new Color(.12f, .17f, .12f));
            swampMat.SetColor("_OV_ColorMid", new Color(.2f, .25f, .16f)); swampMat.SetFloat("_OV_MidDepth", .55f);
            swampMat.SetFloat("_OV_ShallowDepth", .3f); swampMat.SetFloat("_OV_DeepDepth", 1.2f);
            swampMat.SetColor("_OV_ShoreColor", new Color(.3f, .3f, .18f)); swampMat.SetFloat("_OV_ShoreTintStrength", .2f); swampMat.SetFloat("_OV_ShoreTintDepth", .25f);
            var fc = new Color(.55f, .56f, .45f, .22f); swampMat.SetColor("_OV_FoamColor", fc);
            swampMat.SetFloat("_OV_InnerWidth", .05f); swampMat.SetFloat("_OV_OuterWidth", .04f); swampMat.SetFloat("_OV_OuterStrength", .15f); swampMat.SetFloat("_OV_FoamPeriod", 11f);
            swampMat.SetFloat("_OV_IntersectionWidth", .08f);
            swampMat.SetFloat("_Normal_Strength", .05f); swampMat.SetFloat("_Normal_DistanceStrength", .01f); swampMat.SetFloat("_Normal_Pan", .025f);
            swampMat.SetFloat("_OV_CrestFoam", 0f); swampMat.SetVector("_OV_Glints", new Vector4(.07f, 420f, 0, 0)); swampMat.SetFloat("_OV_Clarity", .03f);
            swampMat.SetVector("_OV_Caustics", Vector4.zero); swampMat.SetFloat("_ENABLECAUSTICS", 0f); swampMat.DisableKeyword("_ENABLECAUSTICS");
            swampMat.SetFloat("_OV_Refraction", .0012f); swampMat.SetVector("_OV_Fresnel", new Vector4(.22f, 4f, 0, 0));
            EditorUtility.SetDirty(swampMat);
            var swm = FlatWater("Water_Bog_01-swamp_forest", Offset(Swamp, .5f), SwampY);
            MeshGo("Water_Bog_01-swamp_forest", waterRoot, swm, swampMat, false, false);
            // the stream: a narrow flowing ribbon from below the outlet sill to the old shore line
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var uv1 = new List<Vector2>(); var t = new List<int>();
            float acc = 0f; int rows = 0;
            for (int k = 0; k < Stream.Count; k++)
            {
                if (k > 0) acc += (Stream[k] - Stream[k - 1]).magnitude;
                if (acc < streamOut - .6f || acc > sWater) continue;
                Vector2 d = (Stream[Mathf.Min(k + 1, Stream.Count - 1)] - Stream[Mathf.Max(k - 1, 0)]).normalized, n = new Vector2(-d.y, d.x);
                float hw = 1.1f + .3f * Fbm(acc / 9f, 1.7f, 2) + .5f, y = Mathf.Min(StreamWater(acc), LakeY - .02f);
                var a = Stream[k] + n * hw; var b = Stream[k] - n * hw;
                v.Add(new Vector3(a.x, y, a.y)); v.Add(new Vector3(b.x, y, b.y)); uv.Add(a / 10f); uv.Add(b / 10f);
                float speed = Mathf.Lerp(.75f, 1.9f, Mathf.Clamp01((StreamBed(acc - 1f) - StreamBed(acc + 1f)) * 7f));
                uv1.Add(d * speed); uv1.Add(d * speed);
                if (rows > 0) { int q = v.Count - 4; t.AddRange(new[] { q, q + 2, q + 3, q, q + 3, q + 1 }); }
                rows++;
            }
            for (int k = 0; k < t.Count; k += 3)
            {
                var n = Vector3.Cross(v[t[k + 1]] - v[t[k]], v[t[k + 2]] - v[t[k]]);
                if (n.y < 0) { (t[k + 1], t[k + 2]) = (t[k + 2], t[k + 1]); }
            }
            var smesh = SaveMesh("Water_River_01-stream", v, uv, t, uv1);
            string stp = Dir + "/Materials/W86_water_stream_forest.mat"; var streamMat = AssetDatabase.LoadAssetAtPath<Material>(stp);
            if (!streamMat) { streamMat = new Material(flowMat) { name = "W86_water_stream_forest" }; AssetDatabase.CreateAsset(streamMat, stp); }
            streamMat.CopyPropertiesFromMaterial(flowMat); streamMat.shader = flowMat.shader;
            streamMat.SetColor("_Color_Shallow", new Color(.28f, .8f, .92f)); streamMat.SetColor("_Color_Deep", new Color(.12f, .62f, .86f)); streamMat.SetColor("_OV_ColorMid", new Color(.18f, .7f, .9f));   // sea colours, a touch brighter (Vadim 28.10)
            streamMat.SetFloat("_OV_MidDepth", .35f); streamMat.SetFloat("_OV_ShallowDepth", .15f); streamMat.SetFloat("_OV_DeepDepth", .9f); streamMat.SetFloat("_OV_Clarity", .42f);
            streamMat.SetColor("_OV_FoamColor", new Color(.9f, .9f, .85f, .35f)); streamMat.SetFloat("_OV_InnerWidth", .04f); streamMat.SetFloat("_OV_OuterWidth", .035f); streamMat.SetFloat("_OV_OuterStrength", .25f);
            streamMat.SetFloat("_OV_FlowFoam", .42f); streamMat.SetFloat("_OV_IntersectionWidth", .09f); streamMat.SetFloat("_OV_FlowSpeed", 1.4f);
            EditorUtility.SetDirty(streamMat);
            MeshGo("Water_River_01-stream", waterRoot, smesh, streamMat, false, false);
            if (Brook != null)
            {   // the brook ribbon: from under the swamp's surface to under the lake's
                var bv = new List<Vector3>(); var buv = new List<Vector2>(); var buv1 = new List<Vector2>(); var bt = new List<int>(); float ba = 0f; int brow = 0;
                for (int k = 0; k < Brook.Count; k++)
                {
                    if (k > 0) ba += (Brook[k] - Brook[k - 1]).magnitude;
                    if (ba < brookS0 - 1.5f || ba > brookS1 + 1.5f) continue;
                    Vector2 d = (Brook[Mathf.Min(k + 1, Brook.Count - 1)] - Brook[Mathf.Max(k - 1, 0)]).normalized, n = new Vector2(-d.y, d.x);
                    float hw = .55f + .2f * Fbm(ba / 7f, 4.4f, 2) + .4f, y = BrookWater(ba);
                    var a = Brook[k] + n * hw; var b = Brook[k] - n * hw;
                    bv.Add(new Vector3(a.x, y, a.y)); bv.Add(new Vector3(b.x, y, b.y)); buv.Add(a / 10f); buv.Add(b / 10f); buv1.Add(d * .7f); buv1.Add(d * .7f);
                    if (brow > 0) { int q = bv.Count - 4; bt.AddRange(new[] { q, q + 2, q + 3, q, q + 3, q + 1 }); }
                    brow++;
                }
                for (int k = 0; k < bt.Count; k += 3) { var n = Vector3.Cross(bv[bt[k + 1]] - bv[bt[k]], bv[bt[k + 2]] - bv[bt[k]]); if (n.y < 0) { (bt[k + 1], bt[k + 2]) = (bt[k + 2], bt[k + 1]); } }
                if (brow > 1) MeshGo("Water_River_01-brook", waterRoot, SaveMesh("Water_River_01-brook", bv, buv, bt, buv1), streamMat, false, false);
                log.AppendLine($"brook ribbon {brow} rows (swamp {SwampY} -> lake {LakeY} m)");
            }
            // where the gorge mouth now lies below the sea, the sea needs its quads
            // (no sea fill: the gorge bed stays above the sea until the old water line, where the sea's own quads are)
            log.AppendLine($"water: lake {Lake.Count} pt outline at {LakeY} m, swamp at {SwampY} m (W86_water_swamp_forest), stream ribbon {rows} rows");
        }

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
            var m = SaveMesh(name, v, uv, t);
            var go = new GameObject(name); go.transform.SetParent(seaGo.transform.parent, false); go.layer = seaGo.layer;
            go.AddComponent<MeshFilter>().sharedMesh = m; var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = seaGo.GetComponent<MeshRenderer>().sharedMaterial;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        // ================================================================================================ rock: skins on the new steep ground, Fedya's faces cut

        static Material stoneMat;
        static Bounds portalBox; static Matrix4x4 portalW2L;

        static void RockWork()
        {
            stoneMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/VadimLocal/Rock/W86_rock_stone_v01.mat");
            if (!stoneMat) stoneMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/W85Build/Generated/v02/Materials/W86_rock_face.mat");
            // the portal volume (in front of and inside the crag): Fedya's rock face shell must not cover it
            var dir = (RailB - RailA).normalized; var fwd = new Vector3(dir.x, 0, dir.y);
            var rot = Quaternion.LookRotation(fwd, Vector3.up); var pos = new Vector3(RailA.x, RailBed(0f), RailA.y);
            portalW2L = Matrix4x4.TRS(pos, rot, Vector3.one).inverse; portalBox = new Bounds(new Vector3(0, 3.6f, -1.2f), new Vector3(8.6f, 8.2f, 8.4f));
            // skins: new steep ground (changed > 0.25 m and steeper than 33 deg), 1 m cells
            var R = new RectInt(150, 20, 410, 500); int tris = 0;
            var rockRoot = new GameObject("RockSkin_forest").transform; rockRoot.SetParent(forestRoot, false);
            tris += SkinOver("RockSkin_forest_a", new RectInt(150, 20, 410, 250), (x, z, y, st) => SkinWant(new Vector2(x, z), y, st), rockRoot);
            tris += SkinOver("RockSkin_forest_b", new RectInt(150, 270, 410, 250), (x, z, y, st) => SkinWant(new Vector2(x, z), y, st), rockRoot);
            // Fedya's rock faces where the ground moved away (gorge, crag) or the portal is
            int cut = 0, meshes = 0;
            var rf = GameObject.Find("Map_W85_v02/RockFaces");
            if (rf) foreach (var mf in rf.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!mf.sharedMesh || mf.transform.parent != rf.transform) continue;
                var bnd = mf.GetComponent<Renderer>().bounds; if (!Rect.MinMaxRect(150, 20, 560, 520).Overlaps(Rect.MinMaxRect(bnd.min.x, bnd.min.z, bnd.max.x, bnd.max.z))) continue;
                var m = mf.sharedMesh; if (!m.isReadable) continue;
                var v = m.vertices; var tri = m.triangles; var keep = new List<int>(); var l2w = mf.transform.localToWorldMatrix;
                for (int k = 0; k < tri.Length; k += 3)
                {
                    var c = l2w.MultiplyPoint3x4((v[tri[k]] + v[tri[k + 1]] + v[tri[k + 2]]) / 3f); var p = new Vector2(c.x, c.z);
                    float gy = NewY(p), oy = OldY(p);
                    bool bad = Mathf.Abs(gy - oy) > .3f && (c.y - gy > .45f || M(p) > .5f && Mathf.Abs(c.y - gy) > .25f);   // floating, or poking through the new forest ground
                    bad |= portalBox.Contains(portalW2L.MultiplyPoint3x4(c));
                    if (bad) cut++; else keep.AddRange(new[] { tri[k], tri[k + 1], tri[k + 2] });
                }
                if (keep.Count == tri.Length) continue;
                var nm = Object.Instantiate(m); nm.name = m.name + "_forest"; nm.SetTriangles(keep, 0); nm.RecalculateBounds();
                string path = Dir + "/Meshes/rockface_" + meshes + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(nm, path);
                mf.sharedMesh = nm; var col = mf.GetComponent<MeshCollider>(); if (col) col.sharedMesh = nm; meshes++;
            }
            log.AppendLine($"rock: skins {tris} tris, Fedya's rock faces cut {cut} tris in {meshes} meshes");
        }

        static bool SkinWant(Vector2 p, float y, float st)
        {
            if (st < 33f) return false;
            bool gorge = p.y < 80f && fStream.Dist(p) < 32f, crag = new Vector2((p.x - 194.2f) / 6.5f, (p.y - RailA.y) / 10.5f).magnitude < 1.75f;
            if (!gorge && !crag) return false;
            float dy = Mathf.Abs(y - OldY(p)); if (dy < .25f) return false;
            if (fLake.Dist(p) < -.5f || fSwamp.Dist(p) < 0f) return false;
            if (portalBox.Contains(portalW2L.MultiplyPoint3x4(new Vector3(p.x, y, p.y)))) return false;
            return true;
        }

        /// <summary>VadimHillApply.SkinOver: a box-projected rock skin over the picked 1 m terrain cells, edges sunk into the ground.</summary>
        static int SkinOver(string name, RectInt R, System.Func<float, float, float, float, bool> on, Transform parent)
        {
            var flag = new bool[R.width + 2, R.height + 2];
            for (int x = R.xMin; x <= R.xMax; x++) for (int z = R.yMin; z <= R.yMax; z++)
            {
                float u = (x + .5f - tp.x) / td.size.x, v = (z + .5f - tp.z) / td.size.z;
                flag[x - R.xMin, z - R.yMin] = on(x + .5f, z + .5f, td.GetInterpolatedHeight(u, v) + tp.y, td.GetSteepness(u, v));
            }
            bool On(int x, int z) => x >= R.xMin && z >= R.yMin && x <= R.xMax && z <= R.yMax && flag[x - R.xMin, z - R.yMin];
            Vector3 Vt(int vx, int vz)
            {
                bool inner = On(vx - 1, vz - 1) && On(vx, vz - 1) && On(vx - 1, vz) && On(vx, vz);
                float u = (vx - tp.x) / td.size.x, v = (vz - tp.z) / td.size.z;
                return new Vector3(vx, td.GetInterpolatedHeight(u, v) + tp.y, vz) + td.GetInterpolatedNormal(u, v) * (inner ? .12f : -.3f);
            }
            var V = new List<Vector3>(); var UV = new List<Vector2>(); var T = new List<int>();
            void Tri(Vector3 a, Vector3 b, Vector3 c)
            {
                var n = Vector3.Cross(b - a, c - a); float ax = Mathf.Abs(n.x), ay = Mathf.Abs(n.y), az = Mathf.Abs(n.z);
                Vector2 Uv(Vector3 q) => ay >= ax && ay >= az ? new Vector2(q.x, q.z) / 7f : ax >= az ? new Vector2(q.z, q.y) / 7f : new Vector2(q.x, q.y) / 7f;
                if (n.y < 0) { var t0 = b; b = c; c = t0; }
                int k = V.Count; V.Add(a); V.Add(b); V.Add(c); UV.Add(Uv(a)); UV.Add(Uv(b)); UV.Add(Uv(c)); T.Add(k); T.Add(k + 1); T.Add(k + 2);
            }
            for (int x = R.xMin; x <= R.xMax; x++) for (int z = R.yMin; z <= R.yMax; z++)
            {
                if (!On(x, z)) continue;
                Vector3 p00 = Vt(x, z), p10 = Vt(x + 1, z), p01 = Vt(x, z + 1), p11 = Vt(x + 1, z + 1);
                Tri(p00, p01, p11); Tri(p00, p11, p10);
            }
            if (V.Count == 0 || !stoneMat) return 0;
            var m = SaveMesh(name, V, UV, T);
            // smooth normals over every corner at the same spot (one stone, no faceted checker - Vadim 25.10)
            var acc = new Dictionary<Vector3Int, Vector3>();
            Vector3Int K(Vector3 q) => new Vector3Int(Mathf.RoundToInt(q.x * 50), Mathf.RoundToInt(q.y * 50), Mathf.RoundToInt(q.z * 50));
            for (int k = 0; k < T.Count; k += 3) { var nn = Vector3.Cross(V[T[k + 1]] - V[T[k]], V[T[k + 2]] - V[T[k]]); for (int q = 0; q < 3; q++) { var key = K(V[T[k + q]]); acc[key] = (acc.TryGetValue(key, out var a0) ? a0 : Vector3.zero) + nn; } }
            m.normals = V.Select(q => acc.TryGetValue(K(q), out var a2) && a2.sqrMagnitude > 0 ? a2.normalized : Vector3.up).ToArray();
            EditorUtility.SetDirty(m);
            MeshGo(name, parent, m, stoneMat, false, false);
            return T.Count / 3;
        }

        // ================================================================================================ old objects

        static GameObject oldCampfire, oldBench, oldPortal;
        static Material ballastMat, sleeperMat, railMat;

        static void OldObjectsOff(Transform root)
        {
            var df = root.Find("District_forest");
            if (df)
            {
                foreach (Transform c in df)
                {
                    if (c.name == "Railway_01-railway")
                    {
                        foreach (var r in c.GetComponentsInChildren<MeshRenderer>(true))
                        { var mn = r.sharedMaterial ? r.sharedMaterial.name : ""; if (mn.Contains("ballast")) ballastMat = r.sharedMaterial; else if (mn.Contains("boards")) sleeperMat = r.sharedMaterial; else if (mn.Contains("metal")) railMat = r.sharedMaterial; }
                        c.gameObject.SetActive(false);
                    }
                    else if (c.name.StartsWith("B_01_B01")) c.gameObject.SetActive(false);
                    else if (c.name == "01-campfire") oldCampfire = c.gameObject;
                    else if (c.name == "01_B03") oldBench = c.gameObject;
                    else if (c.name == "01-tunnel-mouth") oldPortal = c.gameObject;
                }
            }
            var water = root.Find("Water");
            if (water) foreach (Transform c in water) if (c.name.StartsWith("Water_Bog_01-swamp")) c.gameObject.SetActive(false);
            int decals = 0;
            var dh = root.Find("DecalHooks_W86");
            if (dh) foreach (var r in dh.GetComponentsInChildren<MeshRenderer>(true))
            {
                var c = r.bounds.center; var p = new Vector2(c.x, c.z);
                if (M(p) > .3f || fOldRoad.Dist(p) < 4f && fKeepRoad.Dist(p) > 8f) { r.gameObject.SetActive(false); decals++; }
            }
            log.AppendLine($"old: wagon B01 + railway + swamp water off, {decals} ground decals in the forest off; campfire {(oldCampfire ? "kept" : "-")}, bench {(oldBench ? "kept" : "-")}, portal {(oldPortal ? "kept" : "-")}");
        }

        // ================================================================================================ trees (terrain instances: cheap, instanced, LODs)

        static readonly List<(Vector2 p, float r, int sp)> Placed = new();
        static Dictionary<long, List<int>> placedHash = new();
        static long HKey(int x, int z) => ((long)x << 32) ^ (uint)z;
        static void HashAdd(int idx) { var p = Placed[idx].p; long k = HKey(Mathf.FloorToInt(p.x / 4f), Mathf.FloorToInt(p.y / 4f)); if (!placedHash.TryGetValue(k, out var l)) placedHash[k] = l = new List<int>(); l.Add(idx); }
        /// <summary>No tree trunk (kit trees, snags) closer than d to p.</summary>
        static bool TrunkClear(Vector2 p, float d)
        {
            int cx = Mathf.FloorToInt(p.x / 4f), cz = Mathf.FloorToInt(p.y / 4f), rr = Mathf.CeilToInt(d / 4f) + 1;
            for (int x = cx - rr; x <= cx + rr; x++) for (int z = cz - rr; z <= cz + rr; z++)
                if (placedHash.TryGetValue(HKey(x, z), out var l)) foreach (int i in l) if ((Placed[i].p - p).sqrMagnitude < d * d) return false;
            return true;
        }

        static bool Free(Vector2 p, float r)
        {
            int cx = Mathf.FloorToInt(p.x / 4f), cz = Mathf.FloorToInt(p.y / 4f), rr = Mathf.CeilToInt(r / 4f) + 1;
            for (int x = cx - rr; x <= cx + rr; x++) for (int z = cz - rr; z <= cz + rr; z++)
                if (placedHash.TryGetValue(HKey(x, z), out var l)) foreach (int i in l) { float m = Mathf.Min(r, Placed[i].r); if ((Placed[i].p - p).sqrMagnitude < m * m) return false; }
            return true;
        }

        static Vector2 ClearingC => WagonP + new Vector2(1f, 7f);
        static Vector2 PierShore, PierDir;

        /// <summary>Where nothing tall may stand: paths (+2 m), water, the ravine cut, rails, the camp, the den, the bridge, the portal, NPC spots.</summary>
        static bool Blocked(Vector2 p, float pathMargin, bool waterOk = false)
        {
            if (PathEdge(p) < pathMargin) return true;
            if (!waterOk && (fLake.Dist(p) < 1.6f || fSwamp.Dist(p) < 1.5f)) return true;
            if (fStream.Dist(p) < 3.2f || NewY(p) < OldY(p) - .45f && fStream.Dist(p) < 30f) return true;
            if (fGully.Dist(p) < 3.5f) return true;
            if (fBrook != null && fBrook.Dist(p) < 2.4f) return true;
            if (fRail.Dist(p) < 4.2f && fRail.Along(p) > -3f && fRail.Along(p) < RailLen + 3f) return true;
            if ((p - ClearingC).magnitude < 12.5f + 2.5f * (Fbm(p.x / 7f, p.y / 7f, 2) - .5f) * 2f) return true;
            if ((p - DenP).magnitude < 7.5f || (p - BridgeP).magnitude < 9f || (p - RailA).magnitude < 11f) return true;
            if (PierDir != Vector2.zero && (p - (PierShore - PierDir * 1.5f)).magnitude < 6.5f) return true;
            foreach (var q in Npc) if ((p - q).magnitude < 3.2f) return true;
            foreach (var q in Stash) if ((p - q).magnitude < 2.4f) return true;
            return false;
        }

        static void Trees()
        {
            var protos = td.treePrototypes.ToList(); int baseIdx = protos.Count;
            foreach (var n in TreeNames) protos.Add(new TreePrototype { prefab = TreePrefabs[n], bendFactor = 0f });
            int wallBase = protos.Count;   // the border row: the firs with crowns that never turn see-through
            for (int k = 0; k < 4; k++) protos.Add(new TreePrototype { prefab = WallPrefab(TreeNames[k]), bendFactor = 0f });
            td.treePrototypes = protos.ToArray(); td.RefreshPrototypes();
            var bare = new List<int>(); for (int i = 0; i < protos.Count; i++) if (protos[i].prefab && protos[i].prefab.name.StartsWith("TREE_BARE")) bare.Add(i);
            // pass 3: the in-game round lime Leafy bushes (Bush_A / Bush_B) go from the forest and its fringe (Vadim: "just a green spot on the floor")
            var leafyBush = new HashSet<int>(); for (int i = 0; i < protos.Count; i++) if (protos[i].prefab && protos[i].prefab.name.StartsWith("Bush_")) leafyBush.Add(i);
            var trees = td.treeInstances.ToList(); int removed = 0, removedBush = 0;
            for (int k = trees.Count - 1; k >= 0; k--)
            {
                var ti = trees[k]; var p = new Vector2(tp.x + ti.position.x * td.size.x, tp.z + ti.position.z * td.size.z);
                if (p.x < 150 || p.x > 560 || p.y < 20 || p.y > 520) continue;
                bool lb = leafyBush.Contains(ti.prototypeIndex) && M(p) > .02f;
                if (lb || M(p) > .2f || Blocked(p, 1.5f) || fStream.Dist(p) < 30f && NewY(p) < OldY(p) - .3f) { trees.RemoveAt(k); removed++; if (lb) removedBush++; }
            }
            Placed.Clear(); placedHash.Clear();
            var cand = new List<Vector2>();
            for (float z = 22f; z < 518f; z += 1.25f) for (float x = 152f; x < 558f; x += 1.25f) cand.Add(new Vector2(x + RRange(-.6f, .6f), z + RRange(-.6f, .6f)));
            for (int i = cand.Count - 1; i > 0; i--) { int j = Rng.Next(i + 1); (cand[i], cand[j]) = (cand[j], cand[i]); }
            var count = new int[TreeNames.Length]; int added = 0;
            void Add(Vector2 p, int sp, float scale, float r, bool wallTree = false)
            {
                float nx = (p.x - tp.x) / td.size.x, nz = (p.y - tp.z) / td.size.z;
                trees.Add(new TreeInstance
                {
                    position = new Vector3(nx, (NewY(p) - tp.y) / td.size.y, nz), prototypeIndex = (wallTree && sp < 4 ? wallBase : baseIdx) + sp,
                    widthScale = scale * RRange(.94f, 1.06f), heightScale = scale, rotation = R01() * 6.283f, color = Color.white, lightmapColor = Color.white
                });
                Placed.Add((p, r, sp)); HashAdd(Placed.Count - 1); count[sp]++; added++;
            }
            // the lone big pine on the rocky hill (Vadim's point 6)
            Add(BigPine, 6, 1.28f, 5f);
            foreach (var p in cand)
            {
                bool thick = InThicket(p);
                float m = M(p); if (!thick && m < .4f + .38f * Fbm(p.x / 16f + 70f, p.y / 16f + 3f, 2)) continue;
                if (Blocked(p, 2.0f)) continue;
                float y = NewY(p); if (y < .8f) continue;
                if (Slope(p) > (thick ? 50f : 31f)) continue;
                if ((p - BigPine).magnitude < 7f) continue;
                float dens = RefTrees(p), open = RefOpen(p);
                if (!thick && open > .55f && dens < .4f) continue;                                    // the reference's clearings
                float cl = Fbm(p.x / 30f + 4f, p.y / 30f + 9f, 3);
                float d = thick ? 1.3f : Mathf.Clamp01(.18f + .82f * dens) * (.7f + .6f * cl);
                if (!thick && d < .28f) continue;
                bool wall = thick;                                                    // the border row on the cliff top
                // Vadim 28.10 (GPT ref 33 v01 approved): a solid wall, no gaps - 2-3 staggered rows of our firs, lower limbs to the ground
                float r = wall ? RRange(1.3f, 1.75f) : Mathf.Lerp(6.4f, 3.4f, Mathf.Clamp01(d)) * Mathf.Lerp(1.7f, 1f, Sm(.55f, .92f, m));
                if (!Free(p, r)) continue;
                if (!wall && R01() > .85f) continue;                                  // Vadim 28.10: ~8 % fewer trees than pass 3
                // species: stands by noise (dark fir stands, light pine stands, birch patches at edges / openings)
                float pine = Fbm(p.x / 46f + 21f, p.y / 46f + 3f, 2), birchN = Fbm(p.x / 33f + 8f, p.y / 33f + 15f, 2);
                float edge = Mathf.Clamp01(1f - PathEdge(p) / 9f) + Mathf.Clamp01(1f - Mathf.Abs(fSwamp.Dist(p)) / 10f) + Mathf.Clamp01(1f - fLake.Dist(p) / 12f) + Mathf.Clamp01(open * 1.5f);
                float dIn = wall ? -fFoot.Dist(p) : 0f;                                // < 0 on the rim slope, 0 at its foot .. 6 at the forest side
                float[] w = wall ? (dIn > 3.5f ? new[] { 34f, 36f, 22f, 8f, 0f, 0f, 0f, 0f } : new[] { 12f, 30f, 35f, 23f, 0f, 0f, 0f, 0f }) : thick ? new[] { 30f, 35f, 20f, 10f, 0f, 0f, 0f, 5f } : new[] { 10f, 18f, 15f, 12f, 13f, 12f, 10f, 10f };
                if (!thick)
                {
                    float pf = Mathf.Lerp(.45f, 1.9f, Sm(.35f, .65f, pine)), ff = Mathf.Lerp(1.5f, .55f, Sm(.35f, .65f, pine));
                    for (int s = 1; s <= 3; s++) w[s] *= ff; for (int s = 4; s <= 6; s++) w[s] *= pf;
                    w[7] *= Mathf.Lerp(.5f, 2.8f, Sm(.45f, .7f, birchN)) * (1f + edge * .8f);
                    w[0] *= 1f + edge * .9f;
                    float hill = HillAt(p, out float top); if (top > .2f) { for (int s = 4; s <= 6; s++) w[s] *= 1.8f; }
                }
                float tot = w.Sum(), pick = R01() * tot; int spc = 0; for (; spc < w.Length - 1; spc++) { pick -= w[spc]; if (pick <= 0f) break; }
                float scale = spc == 0 ? RRange(.7f, 1.2f) : RRange(.85f, 1.15f);
                if (thick && spc == 0) scale = RRange(.9f, 1.35f);
                if (wall) scale *= RRange(1.0f, 1.15f);                               // fuller crowns: they meet and close every sightline
                Add(p, spc, scale, r, wall);
            }
            // a few dead snags on the swamp hummocks
            int snags = 0;
            if (bare.Count > 0 && !HasProp("Swamp_DeadTree_A"))
                for (int tries = 0; tries < 3000 && snags < 11; tries++)
                {
                    var p = new Vector2(RRange(205f, 290f), RRange(196f, 312f));
                    if (fSwamp.Dist(p) > -3f || NewY(p) < SwampY + .08f || fGat.Dist(p) < 2.5f || !Free(p, 5f)) continue;
                    float nx = (p.x - tp.x) / td.size.x, nz = (p.y - tp.z) / td.size.z; float sc = RRange(.5f, .85f);
                    trees.Add(new TreeInstance { position = new Vector3(nx, (NewY(p) - tp.y) / td.size.y, nz), prototypeIndex = bare[Rng.Next(bare.Count)], widthScale = sc, heightScale = sc, rotation = R01() * 6.283f, color = Color.white, lightmapColor = Color.white });
                    Placed.Add((p, 5f, -1)); HashAdd(Placed.Count - 1); snags++;
                }
            td.SetTreeInstances(trees.ToArray(), true);
            log.AppendLine($"trees: removed {removed} old (incl. {removedBush} Leafy bushes), added {added} kit trees + {snags} snags (protos {baseIdx}..{baseIdx + TreeNames.Length - 1}): " + string.Join(", ", TreeNames.Select((n, i) => n + " " + count[i])) + $"; terrain total {td.treeInstanceCount}");
            treesAdded = added;
        }
        static int treesAdded;

        // ================================================================================================ rails, portal, wagon, camp

        static Vector2 RailDir => (RailB - RailA).normalized;
        static Vector3 RailPt(float s, float up) { var q = RailA + RailDir * s; return new Vector3(q.x, RailBed(Mathf.Clamp(s, 0f, RailLen)) + up, q.y); }
        static float wagonS; static Vector3 wagonPos; static Quaternion wagonRot;

        sealed class MB
        {
            public readonly List<Vector3> V = new(); public readonly List<Vector2> UV = new(); public readonly List<int> T = new();
            public void Box(Vector3 c, Vector3 size, Quaternion r, float uvScale = 1f)
            {
                var h = size * .5f; var ax = r * Vector3.right; var ay = r * Vector3.up; var az = r * Vector3.forward;
                void Face(Vector3 n, Vector3 u, Vector3 v, float hn, float hu, float hv)
                {
                    int k = V.Count; var o = c + n * hn;
                    V.Add(o - u * hu - v * hv); V.Add(o - u * hu + v * hv); V.Add(o + u * hu + v * hv); V.Add(o + u * hu - v * hv);
                    UV.Add(new Vector2(-hu, -hv) * uvScale); UV.Add(new Vector2(-hu, hv) * uvScale); UV.Add(new Vector2(hu, hv) * uvScale); UV.Add(new Vector2(hu, -hv) * uvScale);
                    var nn = Vector3.Cross(V[k + 1] - V[k], V[k + 2] - V[k]);
                    if (Vector3.Dot(nn, n) >= 0) T.AddRange(new[] { k, k + 1, k + 2, k, k + 2, k + 3 }); else T.AddRange(new[] { k, k + 2, k + 1, k, k + 3, k + 2 });
                }
                Face(ay, ax, az, h.y, h.x, h.z); Face(-ay, ax, az, h.y, h.x, h.z); Face(ax, az, ay, h.x, h.z, h.y); Face(-ax, az, ay, h.x, h.z, h.y); Face(az, ax, ay, h.z, h.x, h.y); Face(-az, ax, ay, h.z, h.x, h.y);
            }
            public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 n, float uvScale = 1f)
            {
                int k = V.Count; V.Add(a); V.Add(b); V.Add(c); V.Add(d);
                var u = (b - a).normalized; var w = Vector3.Cross(n, u);
                foreach (var q in new[] { a, b, c, d }) UV.Add(new Vector2(Vector3.Dot(q - a, u), Vector3.Dot(q - a, w)) * uvScale);
                if (Vector3.Dot(Vector3.Cross(b - a, c - a), n) >= 0) T.AddRange(new[] { k, k + 1, k + 2, k, k + 2, k + 3 }); else T.AddRange(new[] { k, k + 2, k + 1, k, k + 3, k + 2 });
            }
            public Mesh Save(string name) => SaveMesh(name, V, UV, T);
        }

        static Material Mat(string name, Color c, float smooth = .08f, float metal = 0f) => Mats.TryGetValue(name, out var m) ? m : LitMat(name, c, smooth, metal);

        static void Rails()
        {
            var root = new GameObject("Rail_forest").transform; root.SetParent(forestRoot, false);
            bool propRails = PropRails(root);
            float sb = RailLen - .15f; var fw = Quaternion.LookRotation(new Vector3(RailDir.x, 0, RailDir.y)); var n3 = new Vector3(-RailDir.y, 0, RailDir.x);
            if (!propRails) {
            ballastMat = LitMat("FK_Ballast", S(.58f, .54f, .5f), .05f, 0f, AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/1d_gravel/1d_gravel_v07_albedo.png"));
            sleeperMat = LitMat("FK_Sleeper", S(.27f, .21f, .16f), .05f);
            railMat = LitMat("FK_RailSteel", S(.34f, .24f, .18f), .3f, .45f);
            // ballast: a trapezoid bed from inside the rubble at the portal to just past the buffer stop
            var bm = new MB(); float s0 = -1.5f, s1 = RailLen + 1.2f;
            var rows = new List<Vector3[]>();
            for (float s = s0; s <= s1 + .01f; s += 1f)
            {
                var c = RailPt(s, 0f); float sink = s < 0f ? .25f : 0f;
                rows.Add(new[] { c - n3 * 1.85f + Vector3.up * (-.16f - sink), c - n3 * 1.2f + Vector3.up * (.25f - sink), c + n3 * 1.2f + Vector3.up * (.25f - sink), c + n3 * 1.85f + Vector3.up * (-.16f - sink) });
            }
            for (int k = 1; k < rows.Count; k++)
                for (int e = 0; e < 3; e++) bm.Quad(rows[k - 1][e], rows[k][e], rows[k][e + 1], rows[k - 1][e + 1], Vector3.up, .5f);
            var bmesh = bm.Save("Rail_forest_ballast"); var bgo = MeshGo("Rail_forest_ballast", root, bmesh, ballastMat, true, false);
            // sleepers (old: some skewed, a few missing) and the two rails (1.52 m gauge) out of the rubble to the end
            var sm = new MB(); int sl = 0;
            for (float s = -1.2f; s < RailLen - .2f; s += .62f)
            {
                if (R01() < .04f && s > 3f) continue;
                var c = RailPt(s, .26f + RRange(-.012f, .01f)); var rot = Quaternion.LookRotation(new Vector3(RailDir.x, 0, RailDir.y)) * Quaternion.Euler(RRange(-1.5f, 1.5f), RRange(-3f, 3f), RRange(-1f, 1f));
                sm.Box(c, new Vector3(2.6f, .14f, .24f), rot, .8f); sl++;
            }
            MeshGo("Rail_forest_sleepers", root, sm.Save("Rail_forest_sleepers"), sleeperMat, false, true);
            var rm = new MB();
            foreach (float side in new[] { -.76f, .76f })
                for (float s = -1.6f; s < RailLen - .25f; s += 2f)
                {
                    float e = Mathf.Min(s + 2f, RailLen - .25f); var a = RailPt(s, .33f + .075f) + n3 * side; var b = RailPt(e, .33f + .075f) + n3 * side;
                    var c = (a + b) * .5f; var rot = Quaternion.LookRotation((b - a).normalized);
                    rm.Box(c, new Vector3(.075f, .15f, (b - a).magnitude + .01f), rot, 1f);
                }
            MeshGo("Rail_forest_rails", root, rm.Save("Rail_forest_rails"), railMat, false, true);
            log.AppendLine($"rail: ballast {s1 - s0:0} m, {sl} sleepers, rails {RailLen - .25f + 1.6f:0.0} m (from inside the portal rubble to the buffer stop)");
            // the buffer stop at the dead end (timber blocks on a steel frame, red-white beam)
            var bs = new MB(); var bc = RailPt(sb, .33f);
            foreach (float side in new[] { -.8f, .8f }) { bs.Box(bc + n3 * side + Vector3.up * .55f, new Vector3(.22f, 1.1f, .22f), fw); bs.Box(bc + n3 * side + Vector3.up * .45f - new Vector3(RailDir.x, 0, RailDir.y) * .55f, new Vector3(.16f, .16f, 1.3f), fw * Quaternion.Euler(-38f, 0, 0)); }
            var bsr = MeshGo("BufferStop_forest_frame", root, bs.Save("BufferStop_forest_frame"), railMat, true, true);
            var beam = new MB(); beam.Box(bc + Vector3.up * .78f + new Vector3(RailDir.x, 0, RailDir.y) * -.05f, new Vector3(2.3f, .32f, .28f), fw, 2f);
            MeshGo("BufferStop_forest_beam", root, beam.Save("BufferStop_forest_beam"), Mat("FK_BufferRed", S(.55f, .14f, .1f), .2f), true, true);
            bufferS = sb - .4f; railTopUp = .48f;
            }

            // the wagon v03 on the rails at the dead end, its open door to the camp (north)
            var wmats = WagonMaterials();
            var wmodel = ImportModel(WagonSrc + "MW86_RailWagon_Base1_v03.fbx", "MW86_RailWagon_Base1_v03.fbx", n => wmats.TryGetValue(n, out var m) ? m : null);
            var wit = ItemOf("Wagon", wmodel); Upright(wit, 4f); var wb = wit.bounds;
            float doorSign = wb.max.z > -wb.min.z ? 1f : -1f;          // the open sliding door sticks out on that side
            var north = new Vector3(-RailDir.y, 0, RailDir.x); if (north.z < 0) north = -north;
            float yaw = Mathf.Atan2(north.x, north.z) * Mathf.Rad2Deg - (doorSign > 0 ? 0f : 180f);
            wagonRot = Quaternion.Euler(0, yaw, 0);
            var along = new Vector3(RailDir.x, 0, RailDir.y);
            float extEnd = -1e9f; foreach (var v in wit.mesh.vertices) extEnd = Mathf.Max(extEnd, Vector3.Dot(wagonRot * wit.local.MultiplyPoint3x4(v), along));
            wagonS = bufferS - .05f - extEnd; var wp = RailPt(wagonS, railTopUp); wagonPos = wp;
            var wgo = new GameObject("Wagon_Base1_v03"); wgo.transform.SetParent(forestRoot, false); wgo.transform.SetPositionAndRotation(wp, wagonRot);
            var wc = new GameObject("MW86_RailWagon_Base1_v03"); wc.transform.SetParent(wgo.transform, false);
            wc.transform.localPosition = wit.local.GetColumn(3); wc.transform.localRotation = wit.local.rotation; wc.transform.localScale = wit.local.lossyScale;
            wc.AddComponent<MeshFilter>().sharedMesh = wit.mesh; wc.AddComponent<MeshRenderer>().sharedMaterials = wit.mats; wc.AddComponent<MeshCollider>().sharedMesh = wit.mesh;
            wc.layer = groundLayer; GameObjectUtility.SetStaticEditorFlags(wc, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI);
            log.AppendLine($"wagon v03: bounds {wb.size:F2}, door side {(doorSign > 0 ? "+z" : "-z")}, yaw {yaw:0}, at s {wagonS:0.0} {wp:F2}");
        }

        static Dictionary<string, Material> WagonMaterials()
        {
            Texture2D Tex(string file)
            {
                string dst = Dir + "/Textures/" + file; string src = WagonSrc + "MW86_RailWagon_Base1_v03.fbm\\" + file;
                if (!File.Exists(dst) && File.Exists(src)) { File.Copy(src, dst); AssetDatabase.ImportAsset(dst); }
                return AssetDatabase.LoadAssetAtPath<Texture2D>(dst);
            }
            Color G(float r, float g, float b) => new Color(Mathf.LinearToGammaSpace(r), Mathf.LinearToGammaSpace(g), Mathf.LinearToGammaSpace(b));
            return new Dictionary<string, Material>
            {
                ["Wagon_Body_WoodRed"] = LitMat("Wagon_Body_WoodRed", Color.white, .12f, 0f, Tex("A_teplushka_red.png")),
                ["Wagon_Inside_Walls"] = LitMat("Wagon_Inside_Walls", Color.white, .08f, 0f, Tex("Inside_walls_boards.png")),
                ["Wagon_Inside_Floor"] = LitMat("Wagon_Inside_Floor", Color.white, .08f, 0f, Tex("Inside_floor_planks.png")),
                ["Wagon_Roof"] = LitMat("Wagon_Roof", G(.09f, .08f, .075f), .3f, .4f),
                ["Wagon_Frame"] = LitMat("Wagon_Frame", G(.09f, .08f, .075f), .3f, .4f),
                ["Wagon_Steel"] = LitMat("Wagon_Steel", G(.13f, .12f, .11f), .45f, .6f),
                ["Wagon_Wood"] = LitMat("Wagon_Wood", G(.36f, .27f, .18f), .08f),
            };
        }

        // ================================================================================================ props: portal, camp, sign, footbridge, boardwalk, pier, den, lilies

        static GameObject Place(string name, GameObject src, Vector3 pos, Quaternion rot, Transform parent, float scale = 1f)
        {
            var g = Object.Instantiate(src, parent); g.name = name; g.SetActive(true);
            g.transform.SetPositionAndRotation(pos, rot); g.transform.localScale = Vector3.one * scale; return g;
        }

        static void Props()
        {
            var props = new GameObject("Props_forest").transform; props.SetParent(forestRoot, false);
            var fwd = new Vector3(RailDir.x, 0, RailDir.y);
            // tunnel portal: the old blocked mouth, turned to the rails and pushed into the crag (the new one from forest_props_v01 if there)
            bool newPortal = HasProp("Tunnel_Portal") && HasProp("Rail_Straight_6m");
            if (newPortal) { if (oldPortal) oldPortal.SetActive(false); }
            else if (oldPortal)
            {
                var g = Place("TunnelPortal_forest", oldPortal, Vector3.zero, Quaternion.LookRotation(fwd) * Quaternion.Euler(0, -90f, 0), props);
                var rends = g.GetComponentsInChildren<Renderer>(); var b = rends[0].bounds; foreach (var r in rends) b.Encapsulate(r.bounds);
                float front = -1e9f; var side = new Vector3(-fwd.z, 0, fwd.x);
                foreach (var cx in new[] { b.min.x, b.max.x }) foreach (var cz in new[] { b.min.z, b.max.z }) front = Mathf.Max(front, Vector3.Dot(new Vector3(cx, 0, cz), fwd));
                float lat = Vector3.Dot(b.center, side);
                var a3 = RailPt(0f, 0f);
                g.transform.position = new Vector3(a3.x, 0, a3.z) + fwd * (.25f - front) - side * lat + Vector3.up * (RailBed(0f) - .15f - b.min.y);
                oldPortal.SetActive(false);
                log.AppendLine($"portal (old blocked mouth reused): bounds {b.size:F1}, at {g.transform.position:F1}");
            }
            // camp: cold campfire + log seats north of the wagon, sign post by the door
            var camp = ClearingC + new Vector2(-4f, 2.5f);
            bool propCamp = PropCamp(props);
            if (propCamp) { if (oldCampfire) oldCampfire.SetActive(false); if (oldBench) oldBench.SetActive(false); }
            else {
            if (oldCampfire) { var c = Place("Campfire_forest", oldCampfire, V3(camp, 0f), Quaternion.Euler(0, 20, 0), props); SeatOnGround(c, .02f); oldCampfire.SetActive(false); }
            if (oldBench) { var bpos = camp + new Vector2(0f, 3.1f); var c = Place("LogSeat_forest_a", oldBench, V3(bpos, 0f), Quaternion.Euler(0, 8, 0), props); SeatOnGround(c, .05f); oldBench.SetActive(false); }
            if (Items.TryGetValue("Log_Rotten", out var log1))
            {
                PlaceItem("LogSeat_forest_b", log1, camp + new Vector2(2.9f, -1.2f), 112f, .9f, props, true, .08f);
                PlaceItem("LogSeat_forest_c", log1, camp + new Vector2(-3.0f, -.8f), 65f, .8f, props, true, .08f);
            }
            SignPost(props, ClearingC + new Vector2(3.5f, -3.2f));
            }
            if (!PropFootbridge(props)) Footbridge(props);
            if (!PropBoardwalk(props)) Boardwalk(props);
            if (!PropPier(props)) Pier(props);
            if (!PropDen(props)) Den(props);
            PropSwamp(props);
            if (!HasProp("Swamp_Lily_Pads")) Lilies(props);
        }

        static Vector3 V3(Vector2 p, float up) => new Vector3(p.x, NewY(p) + up, p.y);

        static void SeatOnGround(GameObject g, float sink)
        {
            var rends = g.GetComponentsInChildren<Renderer>(); if (rends.Length == 0) return;
            var b = rends[0].bounds; foreach (var r in rends) b.Encapsulate(r.bounds);
            float gy = NewY(new Vector2(b.center.x, b.center.z));
            foreach (var c in new[] { new Vector2(b.min.x, b.min.z), new Vector2(b.max.x, b.min.z), new Vector2(b.min.x, b.max.z), new Vector2(b.max.x, b.max.z) }) gy = Mathf.Min(gy, NewY(c));
            g.transform.position += Vector3.up * (gy - b.min.y - sink);
        }

        static GameObject PlaceItem(string name, Item it, Vector2 p, float yaw, float scale, Transform parent, bool collider, float sink, float tilt = 0f)
        {
            var g = new GameObject(name); g.transform.SetParent(parent, false); g.layer = groundLayer;
            var c = new GameObject(it.name); c.transform.SetParent(g.transform, false); c.layer = groundLayer;
            c.transform.localPosition = it.local.GetColumn(3); c.transform.localRotation = it.local.rotation; c.transform.localScale = it.local.lossyScale;
            c.AddComponent<MeshFilter>().sharedMesh = it.mesh; c.AddComponent<MeshRenderer>().sharedMaterials = it.mats;
            g.transform.rotation = Quaternion.Euler(RRange(-tilt, tilt), yaw, RRange(-tilt, tilt)); g.transform.localScale = Vector3.one * scale;
            // sit on the lowest ground under the footprint, sunk a little (never floating on a slope)
            var b = it.bounds; float hgt = b.size.y * scale; float lo = 1e9f, hi = -1e9f;
            foreach (var o in new[] { new Vector2(0, 0), new Vector2(b.min.x, b.min.z), new Vector2(b.max.x, b.min.z), new Vector2(b.min.x, b.max.z), new Vector2(b.max.x, b.max.z) })
            {
                var w = g.transform.rotation * new Vector3(o.x * scale, 0, o.y * scale); float y = NewY(p + new Vector2(w.x, w.z)); lo = Mathf.Min(lo, y); hi = Mathf.Max(hi, y);
            }
            g.transform.position = new Vector3(p.x, lo - b.min.y * scale - sink * hgt - (hi - lo) * .15f, p.y);
            if (collider) { var mc = c.AddComponent<MeshCollider>(); mc.sharedMesh = it.mesh; mc.convex = true; }
            GameObjectUtility.SetStaticEditorFlags(g, StaticEditorFlags.BatchingStatic); GameObjectUtility.SetStaticEditorFlags(c, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI);
            return g;
        }

        static void SignPost(Transform parent, Vector2 p)
        {
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir + SignTex);
            var paper = LitMat("FK_SignPaper", Color.white, .05f, 0f, tex);
            var wood = Mat("FK_Planks", S(.47f, .38f, .27f));
            var face = (V3(ClearingC, 0f) - V3(p, 0f)); face.y = 0; var rot = Quaternion.LookRotation(-face.normalized);
            var g = new GameObject("SignPost_KuplyuKrov"); g.transform.SetParent(parent, false); g.transform.SetPositionAndRotation(V3(p, -.25f), rot);
            var post = new MB(); post.Box(new Vector3(0, 1.15f, 0), new Vector3(.11f, 2.3f, .11f), Quaternion.identity); post.Box(new Vector3(0, 1.62f, .03f), new Vector3(.95f, .62f, .03f), Quaternion.identity);
            var pg = MeshGo("post", g.transform, post.Save("SignPost_post"), wood, true, true);
            var sh = new MB(); sh.Quad(new Vector3(-.4f, 1.36f, -.0f), new Vector3(.4f, 1.36f, -.0f), new Vector3(.4f, 1.88f, -.0f), new Vector3(-.4f, 1.88f, -.0f), -Vector3.forward);
            for (int k = 0; k < sh.UV.Count; k++) sh.UV[k] = new Vector2(sh.UV[k].x / .8f, sh.UV[k].y / .52f);
            MeshGo("notice", g.transform, sh.Save("SignPost_notice"), paper, false, false).transform.localPosition = new Vector3(0, 0, -.003f);
        }

        static void Footbridge(Transform parent)
        {
            // along the path over the ravine: from path_wb's end to path_red's start
            Vector2 a = PathWb[Mathf.Max(0, PathWb.Count - 9)], b = PathRed[Mathf.Min(8, PathRed.Count - 1)]; var d = (b - a).normalized; var n = new Vector2(-d.y, d.x);
            float half = 7.0f; var e0 = BridgeP - d * half; var e1 = BridgeP + d * half;
            float y0 = NewY(e0), y1 = NewY(e1);
            var wood = Mat("FK_Planks", S(.47f, .38f, .27f)); var bark = Mats["FK_Log_Bark"];
            var deck = new MB(); var logs = new MB(); var fw = new Vector3(d.x, 0, d.y); var side = new Vector3(n.x, 0, n.y);
            var A = new Vector3(e0.x, y0 + .14f, e0.y); var B = new Vector3(e1.x, y1 + .14f, e1.y); var dir = (B - A).normalized; float L = (B - A).magnitude;
            var rot = Quaternion.LookRotation(dir);
            for (float s = .1f; s < L - .05f; s += .24f)
            {
                var c = A + dir * s + Vector3.up * RRange(-.01f, .01f);
                deck.Box(c, new Vector3(1.7f, .07f, .21f), rot * Quaternion.Euler(0, RRange(-2f, 2f), 0), 1f);
            }
            foreach (float sd in new[] { -.6f, .6f }) logs.Box(A + dir * (L * .5f) + side * sd - Vector3.up * .18f, new Vector3(.26f, .26f, L + .6f), rot);
            for (float s = .4f; s < L; s += 2.3f) foreach (float sd in new[] { -.86f, .86f }) logs.Box(A + dir * s + side * sd + Vector3.up * .5f, new Vector3(.11f, 1.0f, .11f), Quaternion.identity);
            foreach (float sd in new[] { -.86f, .86f }) logs.Box(A + dir * (L * .5f) + side * sd + Vector3.up * .98f, new Vector3(.1f, .1f, L - .4f), rot);
            var g = new GameObject("Footbridge_forest"); g.transform.SetParent(parent, false);
            MeshGo("deck", g.transform, deck.Save("Footbridge_deck"), wood, false, true);
            MeshGo("logs", g.transform, logs.Save("Footbridge_logs"), bark, false, true);
            var col = new GameObject("walk"); col.transform.SetParent(g.transform, false); col.transform.SetPositionAndRotation((A + B) * .5f - Vector3.up * .02f, rot);
            var bc = col.AddComponent<BoxCollider>(); bc.size = new Vector3(1.7f, .12f, L + .4f);
            foreach (float sd in new[] { -.86f, .86f }) { var rc = new GameObject("rail"); rc.transform.SetParent(g.transform, false); rc.transform.SetPositionAndRotation((A + B) * .5f + side * sd + Vector3.up * .55f, rot); rc.AddComponent<BoxCollider>().size = new Vector3(.12f, 1.0f, L); }
            log.AppendLine($"footbridge: span {L:0.0} m at {BridgeP}, ends {y0:0.00} / {y1:0.00} m, water below {StreamWater(fStream.Along(BridgeP)):0.00} m");
        }

        static void Boardwalk(Transform parent)
        {
            // the gat line, carried on to dry ground at the far end
            var line = new List<Vector2>(Gat); var dEnd = (line[line.Count - 1] - line[line.Count - 2]).normalized;
            for (int k = 0; k < 12 && fSwamp.Dist(line[line.Count - 1]) < 2.5f; k++) line.Add(line[line.Count - 1] + dEnd * 2f);
            var wood = Mat("FK_Planks_Grey", S(.42f, .36f, .28f)); var bark = Mats["FK_Log_Bark"];
            var planks = new MB(); var posts = new MB(); var walk = new MB(); int np = 0;
            for (int k = 1; k < line.Count; k++)
            {
                Vector2 a = line[k - 1], b = line[k]; float L = (b - a).magnitude; var d = (b - a) / L; var n = new Vector2(-d.y, d.x);
                var rot = Quaternion.LookRotation(new Vector3(d.x, 0, d.y));
                float Yat(Vector2 q) => Mathf.Max(SwampY + .34f, NewY(q) + .16f);
                for (float s = 0f; s < L; s += .27f)
                {
                    if (R01() < .025f) continue;
                    var q = a + d * s; var c = new Vector3(q.x, Yat(q) + RRange(-.012f, .012f), q.y);
                    planks.Box(c, new Vector3(1.25f, .06f, .21f), rot * Quaternion.Euler(RRange(-1.5f, 1.5f), RRange(-3f, 3f), RRange(-1f, 1f)), 1f); np++;
                }
                for (float s = 0f; s < L; s += 2f)
                    foreach (float sd in new[] { -.55f, .55f })
                    {
                        var q = a + d * s + n * sd; float top = Yat(q) - .03f, bot = Mathf.Min(NewY(q), SwampY) - .45f;
                        posts.Box(new Vector3(q.x, (top + bot) * .5f, q.y), new Vector3(.12f, top - bot, .12f), Quaternion.Euler(RRange(-3f, 3f), RRange(0f, 90f), RRange(-3f, 3f)));
                    }
                foreach (float sd in new[] { -.6f, .6f }) posts.Box(new Vector3((a.x + b.x) * .5f + n.x * sd, (Yat(a) + Yat(b)) * .5f - .08f, (a.y + b.y) * .5f + n.y * sd), new Vector3(.1f, .1f, L + .1f), rot);
                var wa = a - n * .62f; var wb = a + n * .62f; var wc = b + n * .62f; var wd = b - n * .62f;
                walk.Quad(new Vector3(wa.x, Yat(a) + .02f, wa.y), new Vector3(wd.x, Yat(b) + .02f, wd.y), new Vector3(wc.x, Yat(b) + .02f, wc.y), new Vector3(wb.x, Yat(a) + .02f, wb.y), Vector3.up);
            }
            var g = new GameObject("Boardwalk_gat_forest"); g.transform.SetParent(parent, false);
            MeshGo("planks", g.transform, planks.Save("Gat_planks"), wood, false, true);
            MeshGo("posts", g.transform, posts.Save("Gat_posts"), bark, false, true);
            var wgo = new GameObject("walk"); wgo.transform.SetParent(g.transform, false); wgo.AddComponent<MeshCollider>().sharedMesh = walk.Save("Gat_walk");
            log.AppendLine($"boardwalk: {line.Count - 1} legs, {np} planks");
        }

        static void Pier(Transform parent)
        {
            var d = PierDir; var n = new Vector2(-d.y, d.x); var a = PierShore - d * 2.2f; float L = 7.2f; float y = LakeY + .48f;
            var wood = Mat("FK_Planks_Grey", S(.42f, .36f, .28f)); var bark = Mats["FK_Log_Bark"];
            var planks = new MB(); var posts = new MB(); var rot = Quaternion.LookRotation(new Vector3(d.x, 0, d.y));
            for (float s = 0f; s < L; s += .26f) { var q = a + d * s; planks.Box(new Vector3(q.x, Mathf.Max(y, NewY(q) + .12f) + RRange(-.008f, .008f), q.y), new Vector3(1.9f, .06f, .21f), Quaternion.LookRotation(new Vector3(n.x, 0, n.y)) * Quaternion.Euler(0, RRange(-2, 2) + 90f, 0)); }
            for (float s = .3f; s < L; s += 1.7f) foreach (float sd in new[] { -.85f, .85f }) { var q = a + d * s + n * sd; float bot = NewY(q) - .5f; posts.Box(new Vector3(q.x, (y + bot) * .5f, q.y), new Vector3(.16f, y - bot, .16f), Quaternion.identity); }
            foreach (float sd in new[] { -.85f, .85f }) posts.Box(new Vector3(a.x + d.x * L * .5f + n.x * sd, y - .1f, a.y + d.y * L * .5f + n.y * sd), new Vector3(.12f, .12f, L), rot);
            var g = new GameObject("Pier_lake_forest"); g.transform.SetParent(parent, false);
            MeshGo("planks", g.transform, planks.Save("Pier_planks"), wood, false, true); MeshGo("posts", g.transform, posts.Save("Pier_posts"), bark, false, true);
            var col = new GameObject("walk"); col.transform.SetParent(g.transform, false); col.transform.SetPositionAndRotation(new Vector3(a.x + d.x * L * .5f, y, a.y + d.y * L * .5f), rot); col.AddComponent<BoxCollider>().size = new Vector3(1.9f, .1f, L);
            // rowboat beside the pier (the Hamlet's fishing boat if it is a small one)
            var boat = GameObject.Find("Map_W85_v02/District_hamlet/02-FISH-BOAT");
            if (boat)
            {
                var rends = boat.GetComponentsInChildren<Renderer>(); var bb = rends[0].bounds; foreach (var r in rends) bb.Encapsulate(r.bounds);
                if (Mathf.Max(bb.size.x, bb.size.z) < 7f)
                {
                    var bp = a + d * (L * .62f) + n * 2.1f; var gb = Place("Rowboat_lake_forest", boat, Vector3.zero, Quaternion.LookRotation(new Vector3(d.x, 0, d.y)) * Quaternion.Euler(0, 90f + 8f, 0), parent);
                    var rr = gb.GetComponentsInChildren<Renderer>(); var b2 = rr[0].bounds; foreach (var r in rr) b2.Encapsulate(r.bounds);
                    gb.transform.position += new Vector3(bp.x - b2.center.x, (LakeY - .16f) - b2.min.y, bp.y - b2.center.z);
                    log.AppendLine($"rowboat: Hamlet boat copy, size {bb.size:F1}");
                }
            }
            log.AppendLine($"pier: shore {PierShore}, into the lake {d}");
        }

        static void Den(Transform parent)
        {
            var g = new GameObject("Den_forest"); g.transform.SetParent(parent, false);
            var c = DenP; var face = (BridgeP - c).normalized;
            var cloth = Mat("FK_Mattress", S(.42f, .44f, .46f), .03f); var cloth2 = Mat("FK_MattressStain", S(.47f, .4f, .33f), .03f);
            var tarp = Mat("FK_Tarp", S(.18f, .27f, .33f), .15f); var glass = Mat("FK_BottleGreen", S(.16f, .36f, .18f), .7f); var glass2 = Mat("FK_BottleBrown", S(.33f, .19f, .08f), .7f);
            var rag = Mat("FK_Rag", S(.55f, .5f, .42f), .02f); var bark = Mats["FK_Log_Bark"];
            Vector3 P(float x, float z, float up) { var q = c + new Vector2(x, z); return new Vector3(q.x, NewY(q) + up, q.y); }
            var m1 = new MB(); m1.Box(P(-1.0f, .4f, .06f), new Vector3(1.9f, .14f, .85f), Quaternion.Euler(1.5f, 25f, 0)); MeshGo("mattress_a", g.transform, m1.Save("Den_mattress_a"), cloth, true, true);
            var m2 = new MB(); m2.Box(P(1.1f, 1.0f, .05f), new Vector3(1.85f, .12f, .8f), Quaternion.Euler(-2f, 98f, 1f)); MeshGo("mattress_b", g.transform, m2.Save("Den_mattress_b"), cloth2, true, true);
            // tarp lean-to over the mattresses: two sticks and a sagging sheet down to the ground
            var st = new MB(); st.Box(P(-2.2f, 1.6f, .85f), new Vector3(.07f, 1.7f, .07f), Quaternion.Euler(4, 0, -6)); st.Box(P(1.6f, 2.2f, .85f), new Vector3(.07f, 1.7f, .07f), Quaternion.Euler(-3, 0, 5));
            st.Box(P(-.3f, 1.9f, 1.66f), new Vector3(.06f, .06f, 4.0f), Quaternion.Euler(0, 81f, 0));
            MeshGo("sticks", g.transform, st.Save("Den_sticks"), bark, false, true);
            var tm = new MB(); var t0 = P(-2.2f, 1.7f, 1.68f); var t1 = P(1.6f, 2.2f, 1.68f); var t2 = P(1.9f, -1.0f, .02f); var t3 = P(-2.4f, -1.4f, .02f);
            tm.Quad(t0, t1, t2, t3, Vector3.up); tm.Quad(t0, t3, t2, t1, -Vector3.up);
            MeshGo("tarp", g.transform, tm.Save("Den_tarp"), tarp, false, true);
            var bt = new MB(); var bt2 = new MB();
            for (int k = 0; k < 7; k++)
            {
                var q = new Vector2(RRange(-2.6f, 2.8f), RRange(-2.4f, 2.6f)); bool lying = R01() < .6f;
                var box = lying ? new Vector3(.08f, .08f, .28f) : new Vector3(.08f, .28f, .08f);
                (k % 3 == 0 ? bt2 : bt).Box(P(q.x, q.y, lying ? .04f : .14f), box, Quaternion.Euler(0, RRange(0, 360), lying ? 0 : RRange(-8, 8)));
            }
            MeshGo("bottles_g", g.transform, bt.Save("Den_bottles_g"), glass, false, false); MeshGo("bottles_b", g.transform, bt2.Save("Den_bottles_b"), glass2, false, false);
            var rg = new MB(); for (int k = 0; k < 4; k++) rg.Box(P(RRange(-2.5f, 2.5f), RRange(-2f, 2.2f), .02f), new Vector3(RRange(.4f, .8f), .03f, RRange(.3f, .6f)), Quaternion.Euler(RRange(-4, 4), RRange(0, 360), RRange(-4, 4)));
            MeshGo("rags", g.transform, rg.Save("Den_rags"), rag, false, false);
            if (oldCampfire) { var f = Place("campfire", oldCampfire, P(.3f, -1.9f, 0f), Quaternion.Euler(0, 140, 0), g.transform); f.SetActive(true); SeatOnGround(f, .02f); }
            log.AppendLine($"den at {c} (floor {denFloorY:0.00} m): 2 mattresses, tarp lean-to, bottles, rags, cold fire");
        }

        static void Lilies(Transform parent)
        {
            var mat = Mat("FK_LilyPad", S(.27f, .42f, .17f), .25f); var lm = new MB(); int n = 0;
            for (int tries = 0; tries < 9000 && n < 320; tries++)
            {
                bool swamp = tries % 4 != 0; Vector2 p;
                if (swamp) { p = new Vector2(RRange(205f, 290f), RRange(196f, 312f)); if (fSwamp.Dist(p) > -1f || NewY(p) > SwampY - .12f || fGat.Dist(p) < 1.5f) continue; }
                else { p = new Vector2(RRange(335f, 415f), RRange(188f, 270f)); float dl = fLake.Dist(p); if (dl > -1.2f || dl < -5f || (p - PierShore).magnitude < 8f) continue; }
                float y = (swamp ? SwampY : LakeY) + .012f, r = RRange(.16f, .34f), a0 = RRange(0, 6.28f);
                if (Mathf.PerlinNoise(p.x / 6f, p.y / 6f) < .45f) continue;
                var ctr = new Vector3(p.x, y, p.y); int seg = 10;
                for (int k = 0; k < seg; k++)
                {
                    if (k == 0) continue;   // the notch
                    float a1 = a0 + k * 6.283f / seg, a2 = a0 + (k + 1) * 6.283f / seg;
                    int b = lm.V.Count; lm.V.Add(ctr); lm.V.Add(ctr + new Vector3(Mathf.Cos(a1), 0, Mathf.Sin(a1)) * r); lm.V.Add(ctr + new Vector3(Mathf.Cos(a2), 0, Mathf.Sin(a2)) * r);
                    lm.UV.Add(Vector2.zero); lm.UV.Add(Vector2.one); lm.UV.Add(Vector2.right);
                    var nn = Vector3.Cross(lm.V[b + 1] - lm.V[b], lm.V[b + 2] - lm.V[b]); if (nn.y >= 0) lm.T.AddRange(new[] { b, b + 1, b + 2 }); else lm.T.AddRange(new[] { b, b + 2, b + 1 });
                }
                n++;
            }
            MeshGo("LilyPads_forest", parent, lm.Save("LilyPads_forest"), mat, false, false);
            log.AppendLine($"lilies: {n}");
        }

        // ================================================================================================ rocks: groups of 3-7, one main, sunk 15-30 %

        static int rockCount, rockGroups;
        // pass 3: no tall pointed Boulder_1 ("beige pyramid") - the low rounded ones, in the mountains' grey
        static readonly string[] BigRocks = { "Boulder_4", "Boulder_2", "Boulder_4" }, SmallRocks = { "Boulder_2", "Boulder_3", "Boulder_5", "Boulder_6" };
        static readonly List<(Vector2 p, float r)> RockSpots = new();

        static bool RockFree(Vector2 p, float r) { foreach (var q in RockSpots) if ((q.p - p).magnitude < q.r + r) return false; return true; }

        static void RockGroup(Vector2 c, float mainScale, int n, Transform parent, bool waterEdge = false, float spread = 1f)
        {
            int made = 0;
            for (int k = 0; k < n; k++)
            {
                string nm = k == 0 ? BigRocks[Rng.Next(BigRocks.Length)] : SmallRocks[Rng.Next(SmallRocks.Length)];
                var it = Items[nm]; float sc = k == 0 ? mainScale : mainScale * RRange(.35f, .7f) * (nm == "Boulder_6" || nm == "Boulder_3" ? 1.8f : 1f);
                float rad = Mathf.Max(it.bounds.size.x, it.bounds.size.z) * sc * .5f;
                var p = k == 0 ? c : c + Random2() * (mainScale * 1.6f * spread + rad);
                if (Blocked(p, 1.2f, true) && !waterEdge) continue;
                if (PathEdge(p) < rad * .8f + .6f) continue;
                if (!waterEdge && (fLake.Dist(p) < .5f || fSwamp.Dist(p) < 1f)) continue;
                if (fSwamp.Dist(p) < -1f || fLake.Dist(p) < -2.2f) continue;
                if (!RockFree(p, rad * .6f)) continue;
                float sink = RRange(.15f, .3f);
                var g = PlaceItem("Rock_" + rockCount, it, p, RRange(0, 360), sc, parent, it.bounds.size.y * sc > .45f, sink, 12f);
                RockSpots.Add((p, rad * .8f)); rockCount++; made++;
            }
            if (made > 0) rockGroups++;
        }
        static Vector2 Random2() { float a = R01() * 6.283f, r = Mathf.Sqrt(R01()); return new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r; }

        static void Rocks()
        {
            var parent = new GameObject("Rocks_forest").transform; parent.SetParent(forestRoot, false);
            RockSpots.Clear(); rockCount = 0; rockGroups = 0;
            // the lake: big rounded boulders round most of the shore, half in the water (like the reference)
            float acc = 0f, next = 0f;
            for (int k = 1; k < Lake.Count; k++)
            {
                acc += (Lake[k] - Lake[k - 1]).magnitude; if (acc < next) continue; next = acc + RRange(3.5f, 6.5f);
                var q = Lake[k]; if ((q - PierShore).magnitude < 7f || (q - Stream[0]).magnitude < 5f || PathEdge(q) < 4f) continue;
                var outward = (q - new Vector2(Lake.Average(z => z.x), Lake.Average(z => z.y))).normalized;
                float want = .18f + .82f * Mathf.Max(RefRocks(q + outward * 3f), RefRocks(q - outward * 2f)) * 1.4f;
                if (R01() > want) continue;
                RockGroup(q + outward * RRange(-.6f, .8f), RRange(1.25f, 2.15f), 3 + Rng.Next(4), parent, true, .75f);
            }
            // the outlet sill: a line of stones across the start of the stream
            { int ko = 0; float ao = 0f; for (int k = 1; k < Stream.Count; k++) { ao += (Stream[k] - Stream[k - 1]).magnitude; if (ao >= streamOut + .9f) { ko = k; break; } }
              var d = (Stream[Mathf.Min(ko + 2, Stream.Count - 1)] - Stream[Mathf.Max(ko - 2, 0)]).normalized; var n = new Vector2(-d.y, d.x); var s0 = Stream[ko];
              for (int k = -2; k <= 2; k++) { var p = s0 + n * (k * .75f) + d * RRange(-.3f, .3f); var it = Items[k == 0 ? "Boulder_2" : SmallRocks[Rng.Next(SmallRocks.Length)]]; PlaceItem("Rock_sill_" + k, it, p, RRange(0, 360), RRange(.7f, 1.1f), parent, true, .25f, 10f); rockCount++; RockSpots.Add((p, .6f)); } }
            // the hills: rocky tops, hill 6 a proper outcrop round the big pine
            for (int h = 0; h < Hills.Count; h++)
            {
                int groups = h == 0 ? 8 : 5;                     // pass 3: the higher hills carry more rock (ref 21/02)
                for (int g = 0; g < groups; g++)
                {
                    var c = h == 0 && g < 4 ? BigPine + new Vector2(Mathf.Cos(g * 1.7f + .4f), Mathf.Sin(g * 1.7f + .4f)) * RRange(4.5f, 8f) : Hills[h] + Random2() * HillR[Mathf.Min(h, HillR.Length - 1)] * (h == 0 ? .42f : .34f);
                    if ((c - BigPine).magnitude < 3.8f) continue;
                    RockGroup(c, RRange(1.6f, 2.6f) * (h == 0 ? 1.3f : 1f), 4 + Rng.Next(4), parent);
                }
            }
            // where the reference shows grey rocks
            for (int tries = 0; tries < 6000; tries++)
            {
                var p = new Vector2(RRange(170f, 515f), RRange(45f, 410f)); float rr = RefRocks(p);
                if (rr < .45f || M(p) < .6f || R01() > rr * .55f || !RockFree(p, 7f)) continue;
                if (fLake.Dist(p) < 6f) continue;
                RockGroup(p, RRange(1.0f, 1.9f), 3 + Rng.Next(4), parent);
            }
            // the stream: stones at the water's edge on both banks every 2.5-4.5 m, a boulder cluster up a bank every ~12 m,
            // a stone in the water every ~8 m (the water foams round it); bigger in the gorge
            float sAcc = 0f, nextEdge = 0f, nextCluster = 0f, nextIn = 0f; int nEdge = 0, nIn = 0;
            for (int k = 1; k < Stream.Count; k++)
            {
                sAcc += (Stream[k] - Stream[k - 1]).magnitude;
                if (sAcc < streamOut + 3.5f || sAcc > sWater) continue;
                if ((Stream[k] - BridgeP).magnitude < 5.5f) continue;
                var d = (Stream[Mathf.Min(k + 1, Stream.Count - 1)] - Stream[k - 1]).normalized; var n = new Vector2(-d.y, d.x);
                bool gorge = sAcc > streamShore - 28f;
                if (sAcc >= nextEdge)
                {
                    nextEdge = sAcc + RRange(2.5f, 4.5f);
                    foreach (float side in R01() < .65f ? new[] { -1f, 1f } : new[] { R01() < .5f ? -1f : 1f })
                    {
                        var p = Stream[k] + n * side * RRange(1.0f, 1.7f) + d * RRange(-.8f, .8f);
                        var it = Items[SmallRocks[Rng.Next(SmallRocks.Length)]];
                        PlaceItem("Rock_bank_" + nEdge, it, p, RRange(0, 360), RRange(.55f, 1.15f) * (gorge ? 1.4f : 1f), parent, it.bounds.size.y > .5f, .3f, 18f); rockCount++; nEdge++;
                    }
                }
                if (sAcc >= nextCluster)
                {
                    nextCluster = sAcc + RRange(9f, 15f);
                    var c = Stream[k] + n * (R01() < .5f ? -1f : 1f) * RRange(2.4f, 4.2f);
                    RockGroup(c, RRange(1.1f, 2.0f) * (gorge ? 1.3f : 1f), 3 + Rng.Next(4), parent, true, .7f);
                }
                if (sAcc >= nextIn)
                {
                    nextIn = sAcc + RRange(6f, 10f);
                    var p = Stream[k] + n * RRange(-.4f, .4f);
                    PlaceItem("Rock_in_" + nIn, Items[R01() < .5f ? "Boulder_5" : "Boulder_2"], p, RRange(0, 360), RRange(.4f, .7f), parent, true, .32f, 14f); rockCount++; nIn++;
                }
            }
            // the brook: small stones along its banks
            if (Brook != null)
            {
                float ba = 0f, nb = 0f; int nBr = 0;
                for (int k = 1; k < Brook.Count; k++)
                {
                    ba += (Brook[k] - Brook[k - 1]).magnitude; if (ba < brookS0 + 1f || ba > brookS1 - 1f || ba < nb) continue;
                    if (fordS >= 0f && Mathf.Abs(ba - fordS) < 4f) continue;
                    nb = ba + RRange(2.5f, 5f);
                    var d = (Brook[Mathf.Min(k + 1, Brook.Count - 1)] - Brook[k - 1]).normalized; var n = new Vector2(-d.y, d.x) * (R01() < .5f ? -1f : 1f);
                    var p = Brook[k] + n * RRange(.75f, 1.2f);
                    PlaceItem("Rock_brook_" + nBr, Items[SmallRocks[Rng.Next(SmallRocks.Length)]], p, RRange(0, 360), RRange(.45f, .95f), parent, false, .3f, 16f); rockCount++; nBr++;
                }
            }
            // boulder clusters over the forest floor (the reference's big grey rocks under the trees): 3-7, one main, ~25 m apart
            for (float gz = 55f; gz < 405f; gz += 12f) for (float gx = 175f; gx < 512f; gx += 12f)
            {
                var c = new Vector2(gx + RRange(-5f, 5f), gz + RRange(-5f, 5f));
                if (M(c) < .7f || R01() > .3f + .6f * RefRocks(c)) continue;
                if (!RockFree(c, 13f) || Blocked(c, 3f) || Slope(c) > 26f) continue;
                RockGroup(c, RRange(1.2f, 2.3f), 3 + Rng.Next(5), parent);
            }
            // single boulders under the trees, and the thicket full of them
            for (int tries = 0; tries < 6000 && rockCount < 1250; tries++)
            {
                var p = new Vector2(RRange(170f, 515f), RRange(50f, 400f)); if (M(p) < .7f) continue;
                bool thick = InThicket(p); if (thick || R01() > .2f) continue;     // Vadim 28.10: no boulders in the border wall
                if (!RockFree(p, thick ? 3f : 7f) || Blocked(p, 2f)) continue;
                var it = Items[thick || R01() < .5f ? BigRocks[Rng.Next(BigRocks.Length)] : SmallRocks[Rng.Next(SmallRocks.Length)]];
                PlaceItem("Rock_s_" + rockCount, it, p, RRange(0, 360), thick ? RRange(1.1f, 2f) : RRange(.7f, 1.4f), parent, true, .22f, 12f); rockCount++; RockSpots.Add((p, 1.5f));
            }
            // stash spots: a mossy stump or a rock to hang around at
            for (int k = 0; k < Stash.Count; k++)
            {
                var p = Stash[k] + new Vector2(.9f, .4f);
                if (k % 2 == 0) PlaceItem("Stash_stump_" + k, Items["Stump"], p, RRange(0, 360), RRange(1.1f, 1.4f), parent, true, .08f);
                else PlaceItem("Stash_rock_" + k, Items["Boulder_2"], p, RRange(0, 360), RRange(.9f, 1.2f), parent, true, .2f, 8f);
            }
            log.AppendLine($"rocks: {rockCount} boulders in {rockGroups} groups (+ singles, sill, stream), stash markers {Stash.Count}");
        }

        // ================================================================================================ ground cover: terrain details (GPU instanced, only density maps stored)

        // pass 3: undergrowth = Bush_v05 (main bush), Blueberry_v05 + the small undergrowth v01 (ChatGPT ref 32/01, Bush_v05 leaf style):
        // shrubs 0.3 / 0.45 / 0.6 m, low leaf clumps, fern, twiggy blueberry - instead of the spiky grass clumps and the fine grass (Vadim 28.10)
        static readonly string[] DetailNames = { "Fern_v01", "Blueberry_v05", "Blueberry_Twig_v01", "Bush_v05", "Shrub_S_v01", "Shrub_M_v01", "Shrub_L_v01",
            "Clump_A_v01", "Clump_B_v01", "Clump_C_v01", "Reeds", "Stump", "Cones" };
        static readonly Dictionary<string, int> CoverCount = new();

        // ================================================================================================ leaf litter (Vadim 28.10, sheet v02 option D)

        // option D: green-yellow leaves, some ochre, a rare orange one (sRGB as on the sheet)
        static readonly Color[] LeafCols = { S(.588f, .659f, .259f), S(.502f, .596f, .235f), S(.69f, .69f, .282f), S(.627f, .627f, .235f), S(.769f, .651f, .251f), S(.784f, .502f, .204f) };
        static readonly float[] LeafW = { 3f, 3f, 2f, 2f, 1.2f, .5f };

        /// <summary>A loose cluster of flat low-poly leaves (~0.8 m), each leaf two-tone along its midrib, a few mm apart in height.</summary>
        static Mesh LeafClusterMesh(int seed)
        {
            var rnd = new System.Random(seed); float Rr(float a, float b) => a + (b - a) * (float)rnd.NextDouble();
            Color Pick() { float t = Rr(0f, LeafW.Sum()); for (int k = 0; k < LeafW.Length; k++) { t -= LeafW[k]; if (t <= 0f) return LeafCols[k].linear; } return LeafCols[0].linear; }
            var V = new List<Vector3>(); var N = new List<Vector3>(); var C = new List<Color>(); var T = new List<int>();
            int n = rnd.Next(10, 16);
            for (int i = 0; i < n; i++)
            {
                float rad = Mathf.Sqrt(Rr(0f, 1f)) * .4f, a = Rr(0f, 6.283f), ang = Rr(0f, 6.283f), L = Rr(.08f, .13f), w = L * Rr(.3f, .38f);
                var c = new Vector3(Mathf.Cos(a) * rad, .012f + i * .0025f, Mathf.Sin(a) * rad);
                var q = Quaternion.Euler(Rr(-8f, 8f), ang * Mathf.Rad2Deg, Rr(-8f, 8f));
                // outline: tip, two sides, base; the midrib splits it into two tones
                Vector3 tip = new(L * .5f, 0f, 0f), b = new(-L * .5f, 0f, 0f);
                Vector3[] left = { tip, new(L * .2f, 0f, w), new(-L * .2f, 0f, w * .8f), b }, right = { tip, new(L * .2f, 0f, -w), new(-L * .2f, 0f, -w * .8f), b };
                Color col = Pick(), dark = col * .8f; dark.a = 1f;
                foreach (var (side, cc, flip) in new[] { (left, col, false), (right, dark, true) })
                {
                    int o = V.Count;
                    foreach (var v in side) { V.Add(c + q * v); N.Add(q * Vector3.up); C.Add(cc); }
                    if (!flip) { T.AddRange(new[] { o, o + 2, o + 1, o, o + 3, o + 2 }); } else { T.AddRange(new[] { o, o + 1, o + 2, o, o + 2, o + 3 }); }
                }
            }
            var m = new Mesh { name = "Detail_LeafLitter_" + seed };
            m.SetVertices(V); m.SetNormals(N); m.SetColors(C); m.SetTriangles(T, 0); m.RecalculateBounds();
            string path = Dir + "/Meshes/Detail_LeafLitter_" + seed + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        /// <summary>Fallen leaves as terrain details (instanced, drawn near only, lying on the slope): loose drifts over the forest floor,
        /// thicker under the birches and on the path rims, never on a path, in water or on the rails. Own random, so the rest of
        /// the ground cover stays where it is. Adds to the detail layers that GroundCover made.</summary>
        static void LeafLitter()
        {
            var mat = WindMat("FK_GroundLeaves", Color.white, 0f, 1f, 0f, true);
            var protos = td.detailPrototypes.Where(d => !(d.prototype && d.prototype.name.StartsWith("FD_LeafLitter"))).ToList();
            int first = protos.Count;
            for (int k = 0; k < 3; k++)
            {
                var go = new GameObject("FD_LeafLitter_" + k); go.AddComponent<MeshFilter>().sharedMesh = LeafClusterMesh(501 + k);
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                var pf = PrefabUtility.SaveAsPrefabAsset(go, Dir + "/Prefabs/FD_LeafLitter_" + k + ".prefab"); Object.DestroyImmediate(go);
                protos.Add(new DetailPrototype
                {
                    prototype = pf, usePrototypeMesh = true, renderMode = DetailRenderMode.VertexLit, useInstancing = true,
                    minWidth = .8f, maxWidth = 1.3f, minHeight = 1f, maxHeight = 1f, noiseSpread = .4f, healthyColor = Color.white, dryColor = Color.white,
                    alignToGround = 1f, positionJitter = 1f
                });
            }
            td.detailPrototypes = protos.ToArray();
            int res = td.detailResolution; float cx = td.size.x / res, cz = td.size.z / res;
            int x0 = Mathf.FloorToInt((150f - tp.x) / cx), x1 = Mathf.CeilToInt((560f - tp.x) / cx), z0 = Mathf.FloorToInt((20f - tp.z) / cz), z1 = Mathf.CeilToInt((520f - tp.z) / cz);
            int w = x1 - x0, h = z1 - z0; var layers = new int[3][,]; for (int l = 0; l < 3; l++) layers[l] = new int[h, w];
            // birch trunks on a 4 m grid (leaves gather under them)
            var birch = new HashSet<long>();
            for (int i = 0; i < td.treeInstances.Length; i++)
            {
                var ti = td.treeInstances[i]; var pf = td.treePrototypes[ti.prototypeIndex].prefab; if (!pf || !pf.name.Contains("Birch")) continue;
                var wp = tp + Vector3.Scale(ti.position, td.size); birch.Add(HKey(Mathf.FloorToInt(wp.x / 4f), Mathf.FloorToInt(wp.z / 4f)));
            }
            bool NearBirch(Vector2 q) { int gx = Mathf.FloorToInt(q.x / 4f), gz = Mathf.FloorToInt(q.y / 4f); for (int dz = -1; dz <= 1; dz++) for (int dx = -1; dx <= 1; dx++) if (birch.Contains(HKey(gx + dx, gz + dz))) return true; return false; }
            var rnd = new System.Random(2810); float Rn() => (float)rnd.NextDouble(); int total = 0;
            for (int j = 0; j < h; j++) for (int i = 0; i < w; i++)
            {
                var p = new Vector2(tp.x + (x0 + i + .5f) * cx, tp.z + (z0 + j + .5f) * cz); float m = M(p);
                if (m < .45f) continue;
                if (fSwamp.Dist(p) < 1.5f || fLake.Dist(p) < 1.5f || fStream.Dist(p) < 2.2f || fBrook != null && fBrook.Dist(p) < 1.6f) continue;
                float pe = PathEdge(p); if (pe < .3f) continue;                          // not on the trodden path
                if (fRail.Dist(p) < 2.4f && fRail.Along(p) > -2f && fRail.Along(p) < RailLen + 2f) continue;
                if ((p - RailA).magnitude < 8f) continue;
                // drifts: noise patches, more under birches and in the path rims
                float drift = Mathf.Clamp01((Fbm(p.x / 7f + 41f, p.y / 7f + 9f, 2) - .38f) * 3f);
                float chance = (.1f + .55f * drift) * (NearBirch(p) ? 2.2f : 1f) + (pe < 2.2f ? .35f : 0f);
                if (Rn() >= Mathf.Clamp01(chance)) continue;
                int cnt = Rn() < .3f * drift ? 2 : 1; layers[rnd.Next(3)][j, i] += cnt; total += cnt;
            }
            for (int l = 0; l < 3; l++) td.SetDetailLayer(x0, z0, first + l, layers[l]);
            log.AppendLine($"leaf litter (option D): {total} clusters in 3 variants, {birch.Count} birch cells");
        }

        /// <summary>Leaf litter on the current scene (the rest stays), plus a ground shot at the wagon.</summary>
        public static void Leaves()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            var scene = EditorSceneManager.OpenScene(Scene); log = new StringBuilder();
            ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); td = ter.terrainData; tp = ter.transform.position;
            windShader = Shader.Find("OnlyVolunteers/Wind/v03/GenericFoliageScaled"); litShader = Shader.Find("Universal Render Pipeline/Lit");
            LoadDesign(); BuildFields(); forestRoot = GameObject.Find("Map_W85_v02").transform.Find("VadimForest");
            LeafLitter();
            EditorUtility.SetDirty(td); AssetDatabase.SaveAssets();
            PolishShots("leaves");
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Out + "forest_leaves.txt", log.ToString());
        }

        /// <summary>One submesh with the kit's flat colours baked into vertex colours (the kit grass keeps its own gradient), standing up,
        /// so one instanced material draws it.</summary>
        static Mesh DetailMesh(Item it)
        {
            var src = it.mesh; var v = src.vertices; var nrm = src.normals; var col = src.colors; bool hasCol = col != null && col.Length == v.Length;
            var V = new List<Vector3>(); var N = new List<Vector3>(); var C = new List<Color>(); var T = new List<int>();
            var nmx = it.local.inverse.transpose;
            for (int sm = 0; sm < src.subMeshCount; sm++)
            {
                var mat = sm < it.mats.Length ? it.mats[sm] : null;
                bool vc = mat && mat.HasProperty("_UseVertexTint") && mat.GetFloat("_UseVertexTint") > .5f;
                Color mc = mat && mat.HasProperty("_BaseColor") ? mat.GetColor("_BaseColor").linear : Color.white;
                foreach (int i in src.GetTriangles(sm))
                {
                    T.Add(V.Count); V.Add(it.local.MultiplyPoint3x4(v[i]));
                    N.Add(nrm != null && nrm.Length == v.Length ? nmx.MultiplyVector(nrm[i]).normalized : Vector3.up);
                    C.Add(vc && hasCol ? col[i] : mc);
                }
            }
            var m = new Mesh { name = "Detail_" + it.name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.SetVertices(V); m.SetNormals(N); m.SetColors(C); m.SetTriangles(T, 0); m.RecalculateBounds();
            string path = Dir + "/Meshes/Detail_" + it.name + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static void GroundCover()
        {
            CoverCount.Clear();
            var vcMat = WindMat("FK_Detail_VC", Color.white, .06f, .8f, 0f, true);
            var vcStatic = WindMat("FK_Detail_VC_Static", Color.white, 0f, 1f, 2f, true);
            var scale = new Dictionary<string, Vector2>
            {
                ["Fern_v01"] = new(.8f, 1.2f), ["Blueberry_v05"] = new(.85f, 1.3f), ["Blueberry_Twig_v01"] = new(.85f, 1.25f), ["Bush_v05"] = new(.7f, 1.2f),
                ["Shrub_S_v01"] = new(.85f, 1.2f), ["Shrub_M_v01"] = new(.85f, 1.2f), ["Shrub_L_v01"] = new(.85f, 1.15f),
                ["Clump_A_v01"] = new(.85f, 1.3f), ["Clump_B_v01"] = new(.85f, 1.3f), ["Clump_C_v01"] = new(.85f, 1.2f),
                ["Reeds"] = new(.8f, 1.25f), ["Stump"] = new(.8f, 1.35f), ["Cones"] = new(.9f, 1.4f)
            };
            var protos = new List<DetailPrototype>();
            foreach (var n in DetailNames)
            {
                var mesh = DetailMesh(Items[n]);
                var go = new GameObject("FD_" + n); go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = n == "Stump" || n == "Cones" ? vcStatic : vcMat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                var pf = PrefabUtility.SaveAsPrefabAsset(go, Dir + "/Prefabs/FD_" + n + ".prefab"); Object.DestroyImmediate(go);
                var sc = scale[n];
                var dp = new DetailPrototype
                {
                    prototype = pf, usePrototypeMesh = true, renderMode = DetailRenderMode.VertexLit, useInstancing = true,
                    minWidth = sc.x, maxWidth = sc.y, minHeight = sc.x, maxHeight = sc.y, noiseSpread = .4f, healthyColor = Color.white, dryColor = Color.white,
                    alignToGround = n == "Reeds" ? 0f : .45f, positionJitter = 1f
                };
                if (!dp.Validate(out string err)) log.AppendLine($"detail {n}: {err}");
                protos.Add(dp);
            }
            const int res = 1024;
            td.SetDetailScatterMode(DetailScatterMode.InstanceCountMode);
            td.SetDetailResolution(res, 32);
            td.detailPrototypes = protos.ToArray();
            float cx = td.size.x / res, cz = td.size.z / res;
            int x0 = Mathf.FloorToInt((150f - tp.x) / cx), x1 = Mathf.CeilToInt((560f - tp.x) / cx), z0 = Mathf.FloorToInt((20f - tp.z) / cz), z1 = Mathf.CeilToInt((520f - tp.z) / cz);
            int w = x1 - x0, h = z1 - z0; var layers = new int[DetailNames.Length][,]; for (int l = 0; l < layers.Length; l++) layers[l] = new int[h, w];
            int Li(string n) => System.Array.IndexOf(DetailNames, n);
            var pineCells = new HashSet<long>(); var stumpCells = new HashSet<long>(); float cellHalf = .5f * Mathf.Sqrt(cx * cx + cz * cz);
            bool NearCell(HashSet<long> set, int ci, int cj, int r) { for (int a = -r; a <= r; a++) for (int b = -r; b <= r; b++) if (set.Contains(HKey(ci + a, cj + b))) return true; return false; }
            foreach (var t in Placed) if (t.sp >= 4 && t.sp <= 6)
                for (int dz = -2; dz <= 2; dz++) for (int dx = -1; dx <= 1; dx++) pineCells.Add(HKey(Mathf.FloorToInt((t.p.x - tp.x) / cx) + dx, Mathf.FloorToInt((t.p.y - tp.z) / cz) + dz));
            for (int j = 0; j < h; j++) for (int i = 0; i < w; i++)
            {
                var p = new Vector2(tp.x + (x0 + i + .5f) * cx, tp.z + (z0 + j + .5f) * cz); float m = M(p);
                if (m < .35f) continue;
                int jj = j, ii = i;
                void Put(string n, int c) { layers[Li(n)][jj, ii] += c; CoverCount.TryGetValue(n, out int cc); CoverCount[n] = cc + c; }
                float dsw = fSwamp.Dist(p), dl = fLake.Dist(p), y = NewY(p);
                bool thick = InThicket(p);
                // reeds: the swamp's pool edges and the lake's west / north shallows
                if (dsw < -1f && y > SwampY - .25f && y < SwampY + .12f && fGat.Dist(p) > 1.6f) { if (R01() < .45f) Put("Reeds", R01() < .3f ? 2 : 1); continue; }
                if (dl > -1.8f && dl < -.2f && (p.x < 372f || p.y > 245f) && (p - PierShore).magnitude > 7f) { if (R01() < .3f) Put("Reeds", 1); continue; }
                if (dsw < 1.5f && y < SwampY + .1f) continue;                 // pools
                if (dl < 1.2f || fStream.Dist(p) < 1.9f || fBrook != null && fBrook.Dist(p) < 1.4f) continue;
                if (PathEdge(p) < .65f) continue;
                if (fRail.Dist(p) < 2.4f && fRail.Along(p) > -2f && fRail.Along(p) < RailLen + 2f) continue;
                if ((p - ClearingC).magnitude < 6.5f || (p - DenP).magnitude < 3.5f || (p - RailA).magnitude < 10f) continue;
                if (Slope(p) > 36f) continue;
                if (dsw < 0f) { float rr = R01(); if (rr < .1f) Put("Blueberry_v05", 1); else if (rr < .2f) Put("Clump_B_v01", 1); else if (rr < .26f) Put("Fern_v01", 1); continue; }   // hummocks: low shrubs
                float dens = RefTrees(p), open = RefOpen(p), pe = PathEdge(p);
                float fernN = Fbm(p.x / 14f + 3f, p.y / 14f + 1f, 2), berryN = Fbm(p.x / 11f + 17f, p.y / 11f + 6f, 2), bushN = Fbm(p.x / 17f + 30f, p.y / 17f + 12f, 2), grassN = Fbm(p.x / 9f + 30f, p.y / 9f + 12f, 2);
                float under = Mathf.Clamp01(dens * 1.2f) * (thick ? 1.4f : 1f);
                float swampFade = Sm(-1f, 7f, dsw);                                     // the shrubs thin out towards the bog (soft edge)
                bool wall = thick;
                if (wall) { if (R01() < .85f) Put("Bush_v05", R01() < .55f ? 2 : 1); if (R01() < .3f) Put("Fern_v01", 1); }   // the border wall: its foot sealed bush to bush
                else if (thick && R01() < .26f) Put("Bush_v05", 1);
                if (fernN > .5f && R01() < .3f * under) Put("Fern_v01", 1);
                if (berryN > .48f && R01() < .38f * under * swampFade) Put(R01() < .5f ? "Blueberry_v05" : "Blueberry_Twig_v01", R01() < .3f ? 2 : 1);
                // the small undergrowth where the grass clumps and the fine grass were: openings, path rims, light under the trees
                float gs = ((.08f + .4f * open + .14f * (1f - dens)) * Sm(.3f, .6f, grassN) + (pe < 2.6f ? .12f : 0f)) * swampFade;
                if (R01() < gs)
                {
                    float rr = R01();
                    Put(rr < .22f ? "Clump_A_v01" : rr < .42f ? "Clump_B_v01" : rr < .58f ? "Clump_C_v01" : rr < .76f ? "Shrub_S_v01" : rr < .9f ? "Shrub_M_v01" : "Shrub_L_v01", 1);
                }
                // Bush_v05, the main forest bush: in loose clumps (noise), along the path edges and the openings' rims, never on the path
                float edge = Mathf.Clamp01(1f - Mathf.Abs(pe - 3f) / 3f) * .6f + Mathf.Clamp01(open * 1.4f) * .5f + Mathf.Clamp01(1f - Mathf.Abs(dsw - 6f) / 5f) * .3f;
                if (!thick && pe > 1.6f && R01() < (.03f + .1f * edge + .09f * under) * Sm(.42f, .62f, bushN) * swampFade) Put("Bush_v05", 1);
                // Vadim 28.10: a stump never grows into a tree or another stump (the detail can sit anywhere in its cell)
                if (R01() < .008f * (1f + under) && TrunkClear(p, 1.3f + cellHalf) && !NearCell(stumpCells, x0 + i, z0 + j, 2)) { Put("Stump", 1); stumpCells.Add(HKey(x0 + i, z0 + j)); }
                if (pineCells.Contains(HKey(x0 + i, z0 + j)) && R01() < .14f) Put("Cones", 1);
            }
            // fallen logs (with colliders), more in the thicket. Vadim 28.10: a log never touches a tree, a rock, a stump or another log -
            // checked along its whole length; the bushes / grass / stumps under it are cleared
            var logs = new GameObject("Logs_forest").transform; logs.SetParent(forestRoot, false); int nl = 0, cleared = 0;
            var logIt = Items["Log_Rotten"]; var lb = logIt.bounds; bool alongX = lb.size.x >= lb.size.z;
            Vector3 axisL = alongX ? Vector3.right : Vector3.forward; float lenL = Mathf.Max(lb.size.x, lb.size.z), widL = Mathf.Min(lb.size.x, lb.size.z);
            var logPts = new List<Vector2>();
            for (int tries = 0; tries < 12000 && nl < 230; tries++)
            {
                var p = new Vector2(RRange(172f, 515f), RRange(48f, 405f)); if (M(p) < .7f) continue;
                bool thick = InThicket(p); if (!thick && R01() > .45f) continue;
                if (Blocked(p, 3.0f) || Slope(p) > 22f || !RockFree(p, 2.5f)) continue;
                float yaw = RRange(0, 360), sc = RRange(.9f, 1.35f), half = lenL * sc * .5f + .3f, hw = widL * sc * .5f;
                var ax3 = Quaternion.Euler(0f, yaw, 0f) * axisL; var ax = new Vector2(ax3.x, ax3.z).normalized;
                var pts = new List<Vector2>(); for (float t = -half; t <= half + .01f; t += .5f) pts.Add(p + ax * t);
                bool ok = true;
                foreach (var q in pts)
                {
                    if (!TrunkClear(q, 1.0f + hw) || !RockFree(q, hw + .25f) || Slope(q) > 26f) { ok = false; break; }
                    foreach (var o in logPts) if ((o - q).sqrMagnitude < (2f * hw + .6f) * (2f * hw + .6f)) { ok = false; break; }
                    int ci = Mathf.FloorToInt((q.x - tp.x) / cx), cj = Mathf.FloorToInt((q.y - tp.z) / cz);
                    if (ok && NearCell(stumpCells, ci, cj, 0)) { stumpCells.Remove(HKey(ci, cj)); }   // the stump under it goes (below)
                    if (!ok) break;
                }
                if (!ok) continue;
                PlaceItem("Log_" + nl, logIt, p, yaw, sc, logs, true, .12f, 3f); RockSpots.Add((p, 2.2f)); nl++;
                logPts.AddRange(pts);
                // nothing grows through the log: clear the detail cells along it
                foreach (var q in pts)
                    for (int a = -1; a <= 1; a++) for (int b = -1; b <= 1; b++)
                    {
                        int ii = Mathf.FloorToInt((q.x - tp.x) / cx) + a - x0, jj = Mathf.FloorToInt((q.y - tp.z) / cz) + b - z0; if (ii < 0 || jj < 0 || ii >= w || jj >= h) continue;
                        var cc = new Vector2(tp.x + (x0 + ii + .5f) * cx, tp.z + (z0 + jj + .5f) * cz); if ((cc - q).magnitude > hw + cellHalf + .2f) continue;
                        for (int l = 0; l < layers.Length; l++) if (layers[l][jj, ii] > 0) { layers[l][jj, ii] = 0; cleared++; }
                    }
            }
            log.AppendLine($"logs: {nl} (checked along {lenL:0.0} m x scale, {cleared} detail cells cleared under them)");
            for (int l = 0; l < layers.Length; l++) td.SetDetailLayer(x0, z0, l, layers[l]);
            log.AppendLine($"ground cover (terrain details {res}, instanced, drawn to {ter.detailObjectDistance:0} m): " + string.Join(", ", CoverCount.OrderBy(k => k.Key).Select(k => k.Key + " " + k.Value)));
            // the invisible barrier deep in the western thicket (Vadim 27.10: impassable thicket + barrier, "beyond is just forest")
            var bar = new GameObject("Barrier_west_thicket").transform; bar.SetParent(forestRoot, false); int nb = 0;
            // the whole border line, 7.5 m inland of the cliff top, 12 m tall, overlapping boxes every 4 m (no gaps)
            Border();
            for (int k = 0; k + 4 < BorderInland.Count; k += 4)
            {
                var a = BorderInland[k]; var b = BorderInland[Mathf.Min(k + 4, BorderInland.Count - 1)];
                float ylo = Mathf.Min(NewY(a), NewY(b)), y = Mathf.Max(NewY(a), NewY(b));
                var c = new GameObject("wall_" + nb); c.transform.SetParent(bar, false); c.transform.SetPositionAndRotation(new Vector3((a.x + b.x) * .5f, (ylo - 2f + y + 10f) * .5f, (a.y + b.y) * .5f), Quaternion.LookRotation(new Vector3(b.x - a.x, 0, b.y - a.y)));
                c.AddComponent<BoxCollider>().size = new Vector3(1.2f, y + 10f - (ylo - 2f), (b - a).magnitude + 1f); nb++;
            }
            log.AppendLine($"barrier: {nb} collider boxes along the whole border, 7.5 m inland of the cliff top, 12 m (no renderer)");
        }

        // ================================================================================================ tall grass (W85 blades): re-seated, thinned under trees, off paths / water

        static void Grass()
        {
            var grass = Object.FindFirstObjectByType<OnlyVolunteers.Map.W85.W85GrassRenderer>(FindObjectsInactive.Include);
            if (!grass || !grass.data || !grass.data.instances) { log.AppendLine("grass: no renderer"); return; }
            var src = grass.data; var bytes = (byte[])src.instances.bytes.Clone(); var chunks = (OnlyVolunteers.Map.Grass.GrassPatchData24.Chunk[])src.chunks.Clone();
            var win = Rect.MinMaxRect(150, 20, 560, 520); int moved = 0, hidden = 0, recol = 0; var wb = src.worldBounds;
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
                    if (win.Contains(p))
                    {
                        touched = true; gy = NewY(p);
                        if (Mathf.Abs(gy - gyOld) > .02f) { Put(o + 4, gy); moved++; }
                        float m = M(p);
                        bool kill = PathEdge(p) < .2f || fLake.Dist(p) < .6f || fSwamp.Dist(p) < 0f && gy < SwampY + .06f || fStream.Dist(p) < 1.4f || Slope(p) > 38f;
                        kill |= fRail.Dist(p) < 1.9f && fRail.Along(p) > -2f && fRail.Along(p) < RailLen + 1f || (p - DenP).magnitude < 2.5f || (p - BridgeP).magnitude < 3f || (p - RailA).magnitude < 5f;
                        kill |= fGat.Dist(p) < .8f || (gy < OldY(p) - .6f && fStream.Dist(p) < 30f && Slope(p) > 30f) || fBrook != null && fBrook.Dist(p) < 1.1f;
                        kill |= m > .2f;                                  // pass 3 (Vadim 28.10): no fine grass in the forest at all - the small undergrowth replaces it
                        if (!kill && m > .3f)
                        {   // under the trees fewer and darker blades
                            float dens = RefTrees(p); uint hsh = (uint)(gx * 73856093f) ^ (uint)(gz * 19349663f); float rr = (hsh % 1000) / 1000f;
                            if (rr < .55f * dens * m) kill = true;
                            else { float code = System.BitConverter.ToSingle(bytes, o + 28); float nc = Mathf.Floor(code) + Mathf.Lerp(code - Mathf.Floor(code), .12f + .3f * (1f - dens), m); if (code < 1.5f) { Put(o + 28, nc); recol++; } }
                        }
                        if (kill && gh > 0f) { Put(o + 12, 0f); gh = 0f; hidden++; }
                    }
                    ymin = Mathf.Min(ymin, gy); ymax = Mathf.Max(ymax, gy + gh);
                }
                if (touched && ymax > ymin) { ch.centre.y = (ymin + ymax) * .5f; ch.extents.y = (ymax - ymin) * .5f + .5f; chunks[c] = ch; wb.Encapsulate(new Vector3(ch.centre.x, ymin, ch.centre.z)); wb.Encapsulate(new Vector3(ch.centre.x, ymax, ch.centre.z)); }
            }
            string bp = Dir + "/Data/Grass_W86_forest.bytes"; File.WriteAllBytes(bp, bytes); AssetDatabase.ImportAsset(bp, ImportAssetOptions.ForceUpdate);
            var nd = ScriptableObject.CreateInstance<OnlyVolunteers.Map.Grass.GrassPatchData24>();
            nd.instances = AssetDatabase.LoadAssetAtPath<TextAsset>(bp); nd.instanceCount = src.instanceCount; nd.worldBounds = wb; nd.chunks = chunks;
            nd.sourceScene = src.sourceScene; nd.sourceCommit = src.sourceCommit; nd.placementSummary = src.placementSummary + " | VadimForest v1: forest blades re-seated, thinned under trees";
            string dp = Dir + "/Data/GrassData_W86_forest.asset"; AssetDatabase.DeleteAsset(dp); AssetDatabase.CreateAsset(nd, dp);
            grass.data = nd; EditorUtility.SetDirty(grass);
            log.AppendLine($"grass: {moved} blades re-seated, {hidden} hidden (paths, water, rails, steep, thinned under trees), {recol} darker");
        }

        // ================================================================================================ WaterQuery: the new lake / swamp / stream

        static void WaterQueryData()
        {
            var amb = Object.FindFirstObjectByType<OnlyVolunteers.Audio.AmbiencePlayer>(FindObjectsInactive.Include);
            if (!amb || !amb.SceneData || !amb.SceneData.WaterOverride) { log.AppendLine("water data: no ambience override, skipped"); return; }
            var wd = Object.Instantiate(amb.SceneData.WaterOverride); wd.name = "W85_WaterData_v02_forest";
            float[] Tris(List<Vector2> outline) { var t = Triangulate(outline); var f = new float[t.Count * 2]; for (int k = 0; k < t.Count; k++) { f[k * 2] = outline[t[k]].x; f[k * 2 + 1] = outline[t[k]].y; } return f; }
            var areas = wd.Areas.Where(a => a != null && a.Id != "01-lake" && a.Id != "01-swamp" && !a.Id.StartsWith("01-stream")).ToList();
            areas.Add(new OnlyVolunteers.Audio.WaterData.Area { Id = "01-lake", Kind = OnlyVolunteers.Audio.WaterKind.Lake, SurfaceY = LakeY, Triangles = Tris(Lake) });
            areas.Add(new OnlyVolunteers.Audio.WaterData.Area { Id = "01-swamp", Kind = OnlyVolunteers.Audio.WaterKind.Bog, SurfaceY = SwampY, Triangles = Tris(Swamp) });
            float acc = 0f; Vector2 pa = Vector2.zero, pb = Vector2.zero; int ns = 0;
            for (int k = 0; k < Stream.Count; k++)
            {
                if (k > 0) acc += (Stream[k] - Stream[k - 1]).magnitude; if (acc < streamOut || acc > sWater) continue;
                var d = (Stream[Mathf.Min(k + 1, Stream.Count - 1)] - Stream[Mathf.Max(k - 1, 0)]).normalized; var n = new Vector2(-d.y, d.x) * .9f;
                Vector2 a = Stream[k] + n, b = Stream[k] - n;
                if (ns > 0 && k % 2 == 0) areas.Add(new OnlyVolunteers.Audio.WaterData.Area { Id = "01-stream_" + ns, Kind = OnlyVolunteers.Audio.WaterKind.River, SurfaceY = StreamWater(acc), Triangles = new[] { pa.x, pa.y, pb.x, pb.y, b.x, b.y, pa.x, pa.y, b.x, b.y, a.x, a.y } });
                if (ns == 0 || k % 2 == 0) { pa = a; pb = b; ns++; }
            }
            wd.Areas = areas.ToArray();
            string wp = Dir + "/Data/W85_WaterData_v02_forest.asset"; AssetDatabase.DeleteAsset(wp); AssetDatabase.CreateAsset(wd, wp);
            var sd = Object.Instantiate(amb.SceneData); sd.name = "Ambience_W85_play_v02_forest"; sd.WaterOverride = wd;
            string sp = Dir + "/Data/Ambience_W85_play_v02_forest.asset"; AssetDatabase.DeleteAsset(sp); AssetDatabase.CreateAsset(sd, sp);
            amb.SceneData = sd; EditorUtility.SetDirty(amb);
            log.AppendLine($"water data: lake / swamp / {ns} stream pieces -> {wp}, ambience copy {sp}");
        }

        // ================================================================================================ everything else that stood on the changed ground

        static void SnapLeftovers(Transform root)
        {
            int moved = 0, off = 0;
            var oc = GameObject.Find("Map_W85_v02/RockFaces/RockOutcrops");
            if (oc) foreach (Transform r in oc.transform)
            {
                var p = new Vector2(r.position.x, r.position.z); if (p.x < 150 || p.x > 560 || p.y < 20 || p.y > 520) continue;
                float dy = NewY(p) - OldY(p); if (Mathf.Abs(dy) < .05f) continue;
                if (fLake.Dist(p) < 0f || fSwamp.Dist(p) < 0f || PathEdge(p) < 1f || fStream.Dist(p) < 3f) { r.gameObject.SetActive(false); off++; continue; }
                r.position += Vector3.up * dy; moved++;
            }
            foreach (Transform g in root)
            {
                if (!g.name.StartsWith("District_") || g.name == "District_hamlet") continue;
                foreach (Transform c in g)
                {
                    if (!c.gameObject.activeSelf) continue; var p3 = c.position; var p = new Vector2(p3.x, p3.z);
                    if (p.x < 150 || p.x > 560 || p.y < 20 || p.y > 520) continue;
                    float oy = OldY(p), ny = NewY(p); if (Mathf.Abs(p3.y - oy) > 1.5f || Mathf.Abs(ny - oy) < .05f) continue;
                    c.position = p3 + Vector3.up * (ny - oy); moved++;
                }
            }
            log.AppendLine($"leftovers: {moved} objects re-seated, {off} outcrops off (in water / on paths)");
        }

        // ================================================================================================ forest_props_v01 (second agent): portal, rails, camp, bridge, pier, swamp, den

        static readonly string[] PropNames = { "Tunnel_Portal", "Rail_Straight_6m", "Buffer_Stop", "Sign_Post", "Campfire", "Log_Seat_A", "Log_Seat_B", "Footbridge", "Pier_Small", "Rowboat",
            "Swamp_Boardwalk_Straight", "Swamp_Boardwalk_Turn", "Swamp_DeadTree_A", "Swamp_DeadTree_B", "Swamp_Hummock_A", "Swamp_Hummock_B", "Swamp_Hummock_C", "Swamp_Lily_Pads", "Swamp_MudBank", "Swamp_Reeds_Big",
            "Den_Mattress", "Den_Bottles", "Den_Rags", "Den_Tarp" };
        static bool HasProp(string n) => Items.ContainsKey("P_" + n);
        static Item Prop(string n) => Items["P_" + n];

        static Material PropMat(string fbxMat)
        {
            string n = fbxMat.Replace(".001", "");
            switch (n)
            {   // kit materials keep the kit look (props do not sway: their bark is the plain log bark)
                case "FK_Bark": return Mats["FK_Log_Bark"];
                case "FK_Leaf": return Mats["FK_Plant_Leaf"];
                case "FK_LeafDark": return Mats["FK_Plant_LeafDark"];
                case "FK_LeafLight": return Mats["FK_Plant_LeafLight"];
                case "FK_Grass_VC": case "FK_ReedHead": case "FK_Rock": case "FK_Moss": case "FK_WoodCut": case "FK_WoodRotten": return Mats.TryGetValue(n, out var km) ? km : null;
                case "FK_SignBoard": return LitMat("FK_SignBoard", Color.white, .05f, 0f, AssetDatabase.LoadAssetAtPath<Texture2D>(Dir + SignTex));
                case "FK_CliffRock": return LitMat("FK_CliffRock", StoneGrey, .05f);    // pass 3: the portal rock = the plain grey of the boulders and the mountain walls (was near black)
                case "FK_Rust": return LitMat("FKP_Rust", S(.34f, .28f, .24f), .12f, .25f);   // pass 3: every rail one muted steel brown (the orange rust read as two colours in sun / shade)
            }
            var col = new Dictionary<string, Color>
            {
                ["FK_Ash"] = S(.46f, .45f, .43f), ["FK_Char"] = S(.13f, .12f, .11f), ["FK_ClothBeige"] = S(.66f, .6f, .48f), ["FK_ClothRed"] = S(.55f, .24f, .2f),
                ["FK_GlassBrown"] = S(.4f, .22f, .1f), ["FK_GlassGreen"] = S(.2f, .38f, .24f), ["FK_Mud"] = S(.36f, .29f, .21f), ["FK_MudWet"] = S(.24f, .2f, .15f),
                ["FK_Red"] = S(.72f, .16f, .12f), ["FK_Rust"] = S(.45f, .27f, .16f), ["FK_Snag"] = S(.5f, .48f, .44f), ["FK_Stone"] = S(.6f, .59f, .56f),
                ["FK_StoneDark"] = S(.4f, .4f, .39f), ["FK_Tarp"] = S(.33f, .45f, .55f), ["FK_Void"] = S(.07f, .07f, .07f), ["FK_White"] = S(.9f, .89f, .85f),
                ["FK_WoodDark"] = S(.29f, .23f, .18f), ["FK_WoodGrey"] = S(.55f, .5f, .43f), ["FK_Yellow"] = S(.92f, .76f, .26f),
            };
            if (col.TryGetValue(n, out var c)) return LitMat("FKP_" + n.Substring(3), c, n.StartsWith("FK_Glass") ? .6f : .03f, n == "FK_Rust" ? .3f : 0f);
            return null;
        }

        static void PropsKit()
        {
            if (!Directory.Exists(PropSrc)) { log.AppendLine("props: forest_props_v01 not there, placeholders"); return; }
            int n = 0;
            foreach (var p in PropNames)
            {
                if (!File.Exists(PropSrc + p + ".fbx")) continue;
                Items["P_" + p] = ItemOf("P_" + p, ImportModel(PropSrc + p + ".fbx", "P_" + p + ".fbx", PropMat)); n++;
            }
            if (HasProp("Tunnel_Portal"))
            {
                var pb = Prop("Tunnel_Portal").bounds;
                if (pb.max.z < 6f && pb.min.z < -6f)
                {
                    foreach (var p in PropNames.Where(HasProp))
                    {
                        var it = Prop(p); it.local = Matrix4x4.Rotate(Quaternion.Euler(0, 180f, 0)) * it.local;
                        var nb = new Bounds(); bool first = true;
                        foreach (var v in it.mesh.vertices) { var w = it.local.MultiplyPoint3x4(v); if (first) { nb = new Bounds(w, Vector3.zero); first = false; } else nb.Encapsulate(w); }
                        it.bounds = nb;
                    }
                    log.AppendLine($"props: came in turned 180 deg (portal z {pb.min.z:0.0}..{pb.max.z:0.0}), turned back to the documented frame");
                }
            }
            log.AppendLine($"props: {n}/{PropNames.Length} forest_props_v01 models imported: " + string.Join(", ", PropNames.Where(HasProp).Select(p => $"{p} {Prop(p).bounds.size.x:0.0}x{Prop(p).bounds.size.y:0.0}x{Prop(p).bounds.size.z:0.0}")));
        }

        /// <summary>A prop at its pivot (no ground fitting), facing local +Z along fwd.</summary>
        static GameObject PutProp(string name, string prop, Vector3 pos, Quaternion rot, Transform parent, bool collider, bool convex = false, Vector3? scale = null)
        {
            var it = Prop(prop);
            var g = new GameObject(name); g.transform.SetParent(parent, false); g.layer = groundLayer; g.transform.SetPositionAndRotation(pos, rot); g.transform.localScale = scale ?? Vector3.one;
            var c = new GameObject(prop); c.transform.SetParent(g.transform, false); c.layer = groundLayer;
            c.transform.localPosition = it.local.GetColumn(3); c.transform.localRotation = it.local.rotation; c.transform.localScale = it.local.lossyScale;
            c.AddComponent<MeshFilter>().sharedMesh = it.mesh; c.AddComponent<MeshRenderer>().sharedMaterials = it.mats;
            if (collider) { var mc = c.AddComponent<MeshCollider>(); mc.sharedMesh = it.mesh; mc.convex = convex; }
            GameObjectUtility.SetStaticEditorFlags(g, StaticEditorFlags.BatchingStatic); GameObjectUtility.SetStaticEditorFlags(c, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI);
            return g;
        }
        static Quaternion Face(Vector2 dir) => Quaternion.LookRotation(new Vector3(dir.x, 0, dir.y));

        static bool PropRails(Transform root)
        {
            if (!HasProp("Tunnel_Portal") || !HasProp("Rail_Straight_6m")) return false;
            var fwd2 = RailDir; var fwd = new Vector3(fwd2.x, 0, fwd2.y);
            // the portal: pivot = track centre on the ground at the portal face, rails out along +Z; its back pushed into the crag
            var a3 = RailPt(0f, 0f);
            PutProp("Tunnel_Portal_forest", "Tunnel_Portal", new Vector3(a3.x, RailBed(0f), a3.z), Quaternion.LookRotation(fwd), root, true);
            // 6 m track pieces from the end of the portal's own rails (Z 7.2) to the buffer stop, following the bed's grade
            int nPieces = Mathf.Max(1, Mathf.FloorToInt((RailLen - .5f - 7.2f) / 6f)); float sEnd = 7.2f + 6f * nPieces;
            for (int k = 0; k < nPieces; k++)
            {
                float sc = 7.2f + 3f + 6f * k, y0 = RailBed(sc - 3f), y1 = RailBed(sc + 3f);
                var dir = new Vector3(fwd.x * 6f, y1 - y0, fwd.z * 6f).normalized; var c = RailPt(sc, 0f); c.y = (y0 + y1) * .5f;
                PutProp("Rail_" + k, "Rail_Straight_6m", c, Quaternion.LookRotation(dir), root, k == 0, false);
            }
            railTopEnd = sEnd;
            // buffer stop: beam front .5 m before the rails end, facing the wagon
            if (HasProp("Buffer_Stop")) { float sb = sEnd - .5f; var b = RailPt(sb, 0f); PutProp("Buffer_Stop_forest", "Buffer_Stop", new Vector3(b.x, RailBed(sb), b.z), Quaternion.LookRotation(-fwd), root, true, false); bufferS = sb; }
            else bufferS = sEnd - .5f;
            railTopUp = .30f;
            log.AppendLine($"rail (props): portal at {a3:F1}, {nPieces} x 6 m pieces to s {sEnd:0.0}, buffer stop at s {bufferS:0.0}");
            return true;
        }
        static float railTopEnd, bufferS = -1f, railTopUp = .48f;

        static bool PropCamp(Transform props)
        {
            if (!HasProp("Campfire")) return false;
            var camp = ClearingC + new Vector2(-4f, 2.5f);
            PutProp("Campfire_forest", "Campfire", V3(camp, -.02f), Quaternion.Euler(0, 20, 0), props, false);
            if (HasProp("Log_Seat_A")) { var p = camp + new Vector2(0f, 2.3f); PutProp("LogSeat_forest_a", "Log_Seat_A", V3(p, -.04f), Face(new Vector2(1f, .1f)), props, true, true); }
            if (HasProp("Log_Seat_B")) { var p = camp + new Vector2(2.2f, -1.0f); PutProp("LogSeat_forest_b", "Log_Seat_B", V3(p, -.03f), Face(new Vector2(.45f, .9f)), props, true, true); }
            if (Items.TryGetValue("Log_Rotten", out var lg)) PlaceItem("LogSeat_forest_c", lg, camp + new Vector2(-2.6f, -1.2f), 65f, .75f, props, true, .1f);
            if (HasProp("Sign_Post"))
            {   // by the wagon door, the notice facing the camp and the path
                var sp = ClearingC + new Vector2(1.6f, -1.9f); var face = (ClearingC + new Vector2(-3f, 5f)) - sp;
                PutProp("SignPost_KuplyuKrov", "Sign_Post", V3(sp, -.1f), Face(face.normalized), props, true, true);
            }
            log.AppendLine("camp (props): campfire, 2 log seats + a log, sign post");
            return true;
        }

        static bool PropFootbridge(Transform props)
        {
            if (!HasProp("Footbridge")) return false;
            Vector2 a = PathWb[Mathf.Max(0, PathWb.Count - 9)], b = PathRed[Mathf.Min(8, PathRed.Count - 1)]; var d = (b - a).normalized;
            float deck = bridgeDeckY;
            float Rim(float sgn) { for (float t = .5f; t < 9f; t += .25f) if (NewY(BridgeP + d * sgn * t) > deck - .25f) return t; return 9f; }
            float r0 = Rim(-1f), r1 = Rim(1f); float span = r0 + r1 + 1.3f; float sz = Mathf.Clamp(span / 6.3f, 1f, 1.7f);
            var mid = BridgeP + d * ((r1 - r0) * .5f);
            float y = Mathf.Min(NewY(mid + d * (span * .5f - .4f)), NewY(mid - d * (span * .5f - .4f)));
            PutProp("Footbridge_forest", "Footbridge", new Vector3(mid.x, y, mid.y), Face(d), props, true, false, new Vector3(1f, 1f, sz));
            log.AppendLine($"footbridge (prop): rims {r0:0.0} / {r1:0.0} m from the stream, length x{sz:0.00}, ends at {y:0.00} m");
            return true;
        }

        static bool PropPier(Transform props)
        {
            if (!HasProp("Pier_Small")) return false;
            var shore = PierShore + PierDir * .6f;                          // the water line, ~0.6 m inside the outline
            var c = shore + PierDir * 3f;
            PutProp("Pier_lake_forest", "Pier_Small", new Vector3(c.x, LakeY, c.y), Face(PierDir), props, true, false);
            if (HasProp("Rowboat"))
            {   // left of the pier (seen from the shore), afloat
                var left = new Vector2(-PierDir.y, PierDir.x); var bp = c + left * 2.1f + PierDir * .6f;
                PutProp("Rowboat_lake_forest", "Rowboat", new Vector3(bp.x, LakeY - .15f, bp.y), Face(PierDir) * Quaternion.Euler(0, 6f, 0), props, true, true);
            }
            log.AppendLine("pier (prop) + rowboat on its left");
            return true;
        }

        static bool PropBoardwalk(Transform props)
        {
            if (!HasProp("Swamp_Boardwalk_Straight")) return false;
            var line = new List<Vector2>(Gat); var dEnd = (line[line.Count - 1] - line[line.Count - 2]).normalized;
            for (int k = 0; k < 12 && fSwamp.Dist(line[line.Count - 1]) < 2.5f; k++) line.Add(line[line.Count - 1] + dEnd * 2f);
            int n = 0; var walk = new MB();
            for (int k = 1; k < line.Count; k++)
            {
                Vector2 a = line[k - 1], b = line[k]; float L = (b - a).magnitude; var d = (b - a) / L; var nn = new Vector2(-d.y, d.x);
                // each leg: straight 3 m pieces stretched to the leg (+0.5 m into the corner, so the zigzag joins overlap like a real gat)
                float LL = L + .5f; int cnt = Mathf.Max(1, Mathf.RoundToInt(LL / 3f)); float pl = LL / cnt;
                for (int q = 0; q < cnt; q++)
                {
                    var c = a - d * .25f + d * (pl * (q + .5f));
                    float y = Mathf.Max(SwampY, NewY(c) - .14f, NewY(c - d * pl * .5f) - .14f, NewY(c + d * pl * .5f) - .14f);
                    PutProp("Gat_" + n, "Swamp_Boardwalk_Straight", new Vector3(c.x, y + (k % 2 == 0 ? 0f : .03f), c.y), Face(d) * Quaternion.Euler(0, (q % 2 == 0 ? .6f : -.5f), 0), props, false, false, new Vector3(1f, 1f, pl / 3f));
                    n++;
                }
                float ya = Mathf.Max(SwampY, NewY(a) - .14f) + .34f, yb = Mathf.Max(SwampY, NewY(b) - .14f) + .34f;
                var wa = a - nn * .5f; var wb = a + nn * .5f; var wc = b + nn * .5f; var wd = b - nn * .5f;
                walk.Quad(new Vector3(wa.x, ya, wa.y), new Vector3(wd.x, yb, wd.y), new Vector3(wc.x, yb, wc.y), new Vector3(wb.x, ya, wb.y), Vector3.up);
            }
            var wgo = new GameObject("Gat_walk"); wgo.transform.SetParent(props, false); wgo.AddComponent<MeshCollider>().sharedMesh = walk.Save("Gat_walk");
            log.AppendLine($"boardwalk (props): {n} pieces along {line.Count - 1} legs");
            return true;
        }

        static void PropSwamp(Transform props)
        {
            if (!HasProp("Swamp_Hummock_A")) return;
            var g = new GameObject("Swamp_forest").transform; g.SetParent(props, false);
            int hum = 0, mud = 0, lil = 0, reed = 0, dead = 0; var spots = new List<Vector2>();
            bool Free(Vector2 p, float r) { foreach (var q in spots) if ((q - p).magnitude < r) return false; return true; }
            for (int tries = 0; tries < 12000; tries++)
            {
                var p = new Vector2(RRange(205f, 290f), RRange(195f, 312f)); if (fSwamp.Dist(p) > -1.5f || fGat.Dist(p) < 1.8f) continue;
                float y = NewY(p), depth = SwampY - y;
                if (depth > .12f && hum < 46 && R01() < .4f && Free(p, 2.2f))
                { string[] hs = { "Swamp_Hummock_A", "Swamp_Hummock_B", "Swamp_Hummock_C" }; PutProp("Hummock_" + hum, hs[Rng.Next(3)], new Vector3(p.x, SwampY, p.y), Quaternion.Euler(0, RRange(0, 360), 0), g, false, false, Vector3.one * RRange(.85f, 1.4f)); spots.Add(p); hum++; continue; }
                if (depth > .05f && depth < .3f && mud < 9 && HasProp("Swamp_MudBank") && R01() < .08f && Free(p, 5f))
                { PutProp("MudBank_" + mud, "Swamp_MudBank", new Vector3(p.x, SwampY, p.y), Quaternion.Euler(0, RRange(0, 360), 0), g, false); spots.Add(p); mud++; continue; }
                if (depth > .15f && lil < 42 && HasProp("Swamp_Lily_Pads") && R01() < .25f && Free(p, 2.4f))
                { PutProp("Lilies_" + lil, "Swamp_Lily_Pads", new Vector3(p.x, SwampY, p.y), Quaternion.Euler(0, RRange(0, 360), 0), g, false, false, Vector3.one * RRange(.8f, 1.3f)); spots.Add(p); lil++; continue; }
                if (depth > -.05f && depth < .25f && reed < 60 && HasProp("Swamp_Reeds_Big") && R01() < .2f && Free(p, 1.6f))
                { PutProp("ReedsBig_" + reed, "Swamp_Reeds_Big", new Vector3(p.x, SwampY, p.y), Quaternion.Euler(0, RRange(0, 360), 0), g, false, false, Vector3.one * RRange(.8f, 1.25f)); spots.Add(p); reed++; continue; }
                if (depth < -.06f && dead < 11 && HasProp("Swamp_DeadTree_A") && R01() < .05f && Free(p, 6f))
                { PutProp("DeadTree_" + dead, R01() < .55f ? "Swamp_DeadTree_A" : "Swamp_DeadTree_B", new Vector3(p.x, y - .12f, p.y), Quaternion.Euler(RRange(-4, 4), RRange(0, 360), RRange(-4, 4)), g, true, true, Vector3.one * RRange(.85f, 1.3f)); spots.Add(p); dead++; }
            }
            // a few lily pads in the lake's west / north shallows too
            if (HasProp("Swamp_Lily_Pads"))
                for (int tries = 0, n = 0; tries < 3000 && n < 9; tries++)
                {
                    var p = new Vector2(RRange(335f, 415f), RRange(188f, 270f)); float dl = fLake.Dist(p);
                    if (dl > -1.6f || dl < -5f || (p - PierShore).magnitude < 10f || !(p.x < 372f || p.y > 245f) || !Free(p, 6f)) continue;
                    PutProp("LakeLilies_" + n, "Swamp_Lily_Pads", new Vector3(p.x, LakeY, p.y), Quaternion.Euler(0, RRange(0, 360), 0), g, false); spots.Add(p); n++; lil++;
                }
            log.AppendLine($"swamp props: {hum} hummocks, {mud} mud banks, {lil} lily patches, {reed} big reeds, {dead} dead trees");
        }

        static bool PropDen(Transform props)
        {
            if (!HasProp("Den_Tarp")) return false;
            var g = new GameObject("Den_forest").transform; g.SetParent(props, false);
            var c = DenP; var toStream = (GullyLine[GullyLine.Count - 1] - c).normalized; var side = new Vector2(-toStream.y, toStream.x);
            PutProp("tarp", "Den_Tarp", V3(c + side * .4f - toStream * .6f, -.05f), Face(toStream), g, true, true);
            if (HasProp("Den_Mattress")) { PutProp("mattress_a", "Den_Mattress", V3(c + side * .3f - toStream * .9f, -.02f), Face(side) * Quaternion.Euler(0, 6f, 0), g, false); PutProp("mattress_b", "Den_Mattress", V3(c - side * 2.4f + toStream * .4f, -.02f), Face(toStream) * Quaternion.Euler(0, 75f, 0), g, false); }
            if (HasProp("Den_Rags")) PutProp("rags", "Den_Rags", V3(c + side * 3.4f + toStream * .8f, -.05f), Face(side) * Quaternion.Euler(0, 80f, 0), g, false);
            if (HasProp("Den_Bottles")) { PutProp("bottles_a", "Den_Bottles", V3(c + toStream * 1.6f + side * .9f, -.01f), Quaternion.Euler(0, 40, 0), g, false); PutProp("bottles_b", "Den_Bottles", V3(c - side * 1.4f - toStream * 1.2f, -.01f), Quaternion.Euler(0, 200, 0), g, false); }
            if (HasProp("Campfire")) PutProp("campfire", "Campfire", V3(c + toStream * 2.4f - side * .6f, -.02f), Quaternion.Euler(0, 130, 0), g, false);
            log.AppendLine($"den (props) at {c}: tarp, 2 mattresses, rags line, bottles, cold fire");
            return true;
        }

        // ------------------------------------------------------------------------------------------------ shots

        static List<(string name, Vector3 eye, Vector3 look)> ViewList()
        {
            float G(Vector2 p) => ter.SampleHeight(new Vector3(p.x, 0, p.y)) + tp.y;
            Vector3 E(Vector2 p, float up = 1.7f) => new Vector3(p.x, G(p) + up, p.y);
            Vector3 L(Vector2 p, float up = 1.2f) => new Vector3(p.x, G(p) + up, p.y);
            var v = new List<(string, Vector3, Vector3)>();
            var rd = (RailB - RailA).normalized; var side = new Vector2(-rd.y, rd.x); if (side.y < 0) side = -side;
            v.Add(("wagon", E(PathWb[Mathf.Min(7, PathWb.Count - 1)]), L(RailA + rd * 4f, 2f)));
            v.Add(("portal", E(RailA + rd * 17f + side * 3f), L(RailA + rd * .5f, 2.5f)));
            v.Add(("camp", E(WagonP + side * 11f + rd * 6f), L(WagonP + rd * -1f, 1.6f)));
            var lc = new Vector2(Lake.Average(q => q.x), Lake.Average(q => q.y));
            var pe = PierShore + PierDir * 4.5f; v.Add(("lake", new Vector3(pe.x, LakeY + .5f + 1.7f, pe.y), new Vector3(lc.x - PierDir.x * -30f, LakeY + .5f, lc.y - PierDir.y * -30f)));
            var sw = Lake.OrderBy(q => (q - new Vector2(348f, 203f)).sqrMagnitude).First(); var swo = Stream[0] - (Stream[3] - Stream[0]).normalized * 1.5f;
            v.Add(("lake_shore", E(swo, 1.9f), L(PierShore, 1.0f)));
            var g0 = Gat[0] + (Gat[1] - Gat[0]).normalized * 1.2f; v.Add(("swamp", new Vector3(g0.x, Mathf.Max(SwampY + .34f, G(g0) + .16f) + 1.7f, g0.y), L(Gat[2], .8f)));
            v.Add(("swamp_edge", E(GatLink[Mathf.Max(0, GatLink.Count / 2)]), L(new Vector2(Swamp.Average(q => q.x), Swamp.Average(q => q.y)), .5f)));
            v.Add(("bridge", E(PathWb[Mathf.Max(0, PathWb.Count - 17)]), L(BridgeP, .8f)));
            int kb = 0; for (int k = 1; k < Stream.Count; k++) if ((Stream[k] - BridgeP).sqrMagnitude < (Stream[kb] - BridgeP).sqrMagnitude) kb = k;
            v.Add(("ravine", new Vector3(BridgeP.x, G(BridgeP + (PathRed[Mathf.Min(8, PathRed.Count - 1)] - BridgeP).normalized * 6.5f) + .2f + 1.7f, BridgeP.y), L(Stream[Mathf.Min(kb + 32, Stream.Count - 1)], .6f)));
            v.Add(("den", E(GullyLine[Mathf.Min(13, GullyLine.Count - 1)]), L(DenP, .7f)));
            v.Add(("redpath", E(PathRed[Mathf.Min(150, PathRed.Count - 1)]), L(PathRed[Mathf.Min(178, PathRed.Count - 1)])));
            v.Add(("redpath_north", E(PathRed[Mathf.Min(300, PathRed.Count - 1)]), L(PathRed[Mathf.Min(330, PathRed.Count - 1)])));
            v.Add(("path_up", E(PathUp[Mathf.Min(70, PathUp.Count - 1)]), L(PathUp[Mathf.Min(100, PathUp.Count - 1)])));
            if (Brook != null)
            {   // from the brook's bank a few metres below the ford, looking down the brook to the lake
                // from the brook's mouth at the lake, looking up the brook towards the ford and the swamp
                int km = Brook.Count - 1; while (km > 4 && fLake.Dist(Brook[km]) < .8f) km--;
                var bd = (Brook[km] - Brook[Mathf.Max(km - 4, 0)]).normalized; var bn = new Vector2(-bd.y, bd.x);
                v.Add(("brook", E(Brook[km] + bn * 1.6f, 1.6f), L(Brook[Mathf.Max(km - 24, 0)], .3f)));
                int kp = PathUp.Count > 0 ? Mathf.Clamp(Mathf.RoundToInt(fordPathS) - 13, 0, PathUp.Count - 1) : 0;
                v.Add(("ford", E(PathUp[kp], 1.7f), L(PathUp[Mathf.Clamp(Mathf.RoundToInt(fordPathS), 0, PathUp.Count - 1)], .1f)));
            }
            { int ko = 0; float ao = 0f; for (int k = 1; k < Stream.Count; k++) { ao += (Stream[k] - Stream[k - 1]).magnitude; if (ao >= streamOut + 9f) { ko = k; break; } }
              var od = (Stream[ko + 2] - Stream[ko - 2]).normalized; var on = new Vector2(-od.y, od.x);
              v.Add(("outlet", E(Stream[ko] + on * 3.2f, 1.9f), L(Stream[0], .3f))); }
            v.Add(("pine_hill", E(BigPine + new Vector2(5.5f, -4.5f), 1.7f), L(BigPine + new Vector2(-6f, 3f), .8f)));
            v.Add(("thicket", E(new Vector2(238f, 165f)), L(new Vector2(199f, 184f), 2f)));
            v.Add(("hamlet", E(new Vector2(305.2f, 391f)), L(PathUp[Mathf.Max(0, PathUp.Count - 32)])));
            int ke = Stream.Count - 1; while (ke > 0 && (Stream[ke] - Stream[Stream.Count - 1]).magnitude < 22f) ke--;
            var gd = (Stream[Mathf.Min(ke + 3, Stream.Count - 1)] - Stream[Mathf.Max(ke - 3, 0)]).normalized;
            v.Add(("gorge", E(Stream[ke] - gd * 18f + new Vector2(-gd.y, gd.x) * 9f, 2.5f), L(Stream[Mathf.Min(ke + 12, Stream.Count - 1)], .2f)));
            return v;
        }

        public static void BeforeShots()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            Backup();
            EditorSceneManager.OpenScene(Scene);
            PrepareForShots();
            Shots("before");
        }

        /// <summary>The backup's renders from the same views as the result, then the full rebuild (one Unity start).</summary>
        public static void BeforeAndRun()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            Backup(); Restore();
            EditorSceneManager.OpenScene(Scene);
            PrepareForShots();
            Shots("before");
            Run();
        }

        /// <summary>Close-ups of the joins (portal, rails, wagon, buffer, bridge, boardwalk, pier, mouth) and zoomed top views; no rebuild.</summary>
        public static void Detail()
        {
            System.Threading.Thread.CurrentThread.CurrentCulture = System.Globalization.CultureInfo.InvariantCulture;
            EditorSceneManager.OpenScene(Scene);
            PrepareForShots();
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var fogMbs = Object.FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None).Where(m => m && m.enabled && System.Text.RegularExpressions.Regex.IsMatch(m.GetType().Name, "^District(Fog|Aerial)")).ToList();
            var rp0 = QualitySettings.renderPipeline; int aa0 = QualitySettings.antiAliasing;
            foreach (var m in fogMbs) m.enabled = false;
            float lodBias0 = QualitySettings.lodBias; float treeDist0 = ter.treeDistance, base0 = ter.basemapDistance;
            var go = new GameObject("ForestDetailCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.nearClipPlane = .05f; cam.clearFlags = CameraClearFlags.Skybox;
            shotCam = cam; shotFog = false; UnityEngine.Rendering.RenderPipelineManager.beginCameraRendering += NoFog;
            float G(Vector2 p) => ter.SampleHeight(new Vector3(p.x, 0, p.y)) + tp.y;
            Vector3 At(string path, Vector3 fallback) { var g = GameObject.Find(path); return g ? g.transform.position : fallback; }
            try
            {
                cam.fieldOfView = 55f;
                var rd = (RailB - RailA).normalized; var side = new Vector2(-rd.y, rd.x); if (side.y < 0) side = -side;
                void V(string n, Vector3 eye, Vector3 look) { go.transform.position = eye; go.transform.LookAt(look); Shot(cam, 1200, 720, Out + "forest_v1_detail_" + n + ".png"); }
                Vector3 E(Vector2 p, float up) => new Vector3(p.x, G(p) + up, p.y);
                V("portal_close", E(RailA + rd * 9f + side * 4f, 2.2f), E(RailA, 2.6f));
                V("portal_side", E(RailA + rd * 4f - side * 11f, 3f), E(RailA + side * 1f, 3f));
                var wp = At("Map_W85_v02/VadimForest/Wagon_Base1_v03", E(WagonP, 0f));
                V("wagon_wheels", new Vector3(wp.x, wp.y, wp.z) + new Vector3(side.x, 0, side.y) * 4.5f + new Vector3(rd.x, 0, rd.y) * 3f + Vector3.up * .3f, wp + new Vector3(rd.x, 0, rd.y) * 2f + Vector3.up * .2f);
                var bs = At("Map_W85_v02/VadimForest/Rail_forest/Buffer_Stop_forest", wp);
                V("buffer", bs + new Vector3(side.x, 0, side.y) * 5f + new Vector3(rd.x, 0, rd.y) * 3f + Vector3.up * 1.6f, bs + Vector3.up * .8f);
                V("rails_join", E(RailA + rd * 13f + side * 2.6f, 1.2f), E(RailA + rd * 22f, .2f));
                var fb = At("Map_W85_v02/VadimForest/Props_forest/Footbridge_forest", E(BridgeP, 0f));
                int kb = 0; for (int k = 1; k < Stream.Count; k++) if ((Stream[k] - BridgeP).sqrMagnitude < (Stream[kb] - BridgeP).sqrMagnitude) kb = k;
                var sd = (Stream[Mathf.Min(kb + 3, Stream.Count - 1)] - Stream[Mathf.Max(kb - 3, 0)]).normalized;
                V("bridge_side", new Vector3(fb.x, 0, fb.z) + new Vector3(sd.x, 0, sd.y) * 9f + Vector3.up * (fb.y + .8f), fb + Vector3.up * .3f);
                var g0 = Gat[1]; V("gat_corner", E(g0 + (Gat[2] - Gat[1]).normalized * -5f + new Vector2(2.5f, 2.5f), 2.2f), E(g0, .3f));
                var pr = At("Map_W85_v02/VadimForest/Props_forest/Pier_lake_forest", E(PierShore, 0f));
                V("pier", pr + new Vector3(-PierDir.y, 0, PierDir.x) * 7f + new Vector3(PierDir.x, 0, PierDir.y) * -2f + Vector3.up * 2.2f, pr);
                int ke = Stream.Count - 1; while (ke > 0 && (Stream[ke] - Stream[Stream.Count - 1]).magnitude < 10f) ke--;
                V("mouth", E(Stream[ke], 6f) + new Vector3(0, 0, 0), E(Stream[Stream.Count - 1], -.5f));
                V("den_close", E(DenP + (GullyLine[GullyLine.Count - 1] - DenP).normalized * 6f + new Vector2(0, 2f), 1.9f), E(DenP, .5f));
                V("camp_close", E(ClearingC + new Vector2(2f, 9f), 2.2f), E(ClearingC + new Vector2(-4f, 2.5f), 0f));
                var views = ViewList();
                foreach (var vv in views) if (vv.name == "brook" || vv.name == "ford" || vv.name == "outlet" || vv.name == "pine_hill") { go.transform.position = vv.eye; go.transform.LookAt(vv.look); Shot(cam, 1200, 720, Out + "forest_v1_detail_" + vv.name + ".png"); }
                var rocks = GameObject.Find("Map_W85_v02/VadimForest/Rocks_forest");
                if (rocks)
                {   // a big boulder cluster seen from the red path
                    int made = 0;
                    foreach (Transform r in rocks.transform)
                    {
                        if (made >= 2 || r.localScale.x < 1.6f) continue; var rp = new Vector2(r.position.x, r.position.z);
                        float d = PathDist(rp, out byte id, out float ps); if (id != 3 || d < 5f || d > 11f) continue;
                        var eye = PathRed[Mathf.Clamp(Mathf.RoundToInt(ps), 0, PathRed.Count - 1)];
                        V("rocks_floor" + (made == 0 ? "" : "_b"), new Vector3(eye.x, G(eye) + 1.7f, eye.y), r.position + Vector3.up * .6f); made++;
                    }
                }
                // zoomed top views, 8 px/m
                ter.treeDistance = 2000f; ter.basemapDistance = 5000f;   // (QualitySettings untouched: Unity would save them into ProjectSettings)
                cam.orthographic = true; go.transform.rotation = Quaternion.Euler(90, 0, 0);
                void T(string n, Vector2 c, float half) { cam.orthographicSize = half; cam.aspect = 1f; go.transform.position = new Vector3(c.x, 300f, c.y); Shot(cam, (int)(half * 16), (int)(half * 16), Out + "forest_v1_detail_top_" + n + ".png"); }
                T("wagon", (RailA + RailB) * .5f + new Vector2(0, 6f), 36f);
                T("lake", new Vector2(Lake.Average(q => q.x), Lake.Average(q => q.y)), 45f);
                T("swamp", new Vector2(Swamp.Average(q => q.x), Swamp.Average(q => q.y)), 58f);
                T("bridge_den", (BridgeP + DenP) * .5f, 30f);
                T("hamlet_edge", new Vector2(330f, 380f), 55f);
                T("east", new Vector2(462f, 250f), 50f);
                T("mouth", Stream[Stream.Count - 1] + new Vector2(-6f, 14f), 30f);
            }
            finally
            {
                UnityEngine.Rendering.RenderPipelineManager.beginCameraRendering -= NoFog;
                ter.treeDistance = treeDist0; ter.basemapDistance = base0;
                foreach (var m in fogMbs) if (m) m.enabled = true;
                if (QualitySettings.renderPipeline != rp0) QualitySettings.renderPipeline = rp0;
                if (QualitySettings.antiAliasing != aa0) QualitySettings.antiAliasing = aa0;
                Object.DestroyImmediate(go);
            }
        }

        static void PrepareForShots()
        {
            log = new StringBuilder();
            ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); td = ter.terrainData; tp = ter.transform.position;
            LoadDesign(); BuildFields();
            // the water marks the views need (Heights computes them on a rebuild)
            { float a = 0f; for (int k = 0; k < Stream.Count; k++) { if (k > 0) a += (Stream[k] - Stream[k - 1]).magnitude; if (fLake.Dist(Stream[k]) >= 0f) { streamOut = a; break; } } }
            if (Brook != null)
            {
                float a = 0f; fordS = -1f;
                for (int k = 0; k < Brook.Count; k++) { if (k > 0) a += (Brook[k] - Brook[k - 1]).magnitude; float d = PathDist(Brook[k], out byte id, out float ps); if (id == 1 && d < 1.2f && (fordS < 0f || d < 1f)) { fordS = a; fordPathS = ps; } }
            }
        }

        static string Pre(string tag) => tag == "" ? "forest_v1_" : "forest_v1_" + tag + "_";
        static Camera shotCam; static bool shotFog;
        static void NoFog(UnityEngine.Rendering.ScriptableRenderContext ctx, Camera c) { if (c == shotCam && !shotFog) RenderSettings.fog = false; }

        public static void Shots(string tag)
        {
            // the game cameras go off for the shots and back on after (Mountains saves the scene after these shots: a saved-off player camera = grey game)
            var gameCams = Object.FindObjectsByType<Camera>(FindObjectsSortMode.None).Where(c => c.enabled).ToList(); bool fogWas = RenderSettings.fog;
            foreach (var c in gameCams) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tp = ter.transform.position;
            float lodBias0 = QualitySettings.lodBias; int maxLod0 = QualitySettings.maximumLODLevel; float shadow0 = QualitySettings.shadowDistance;
            float treeDist0 = ter.treeDistance, base0 = ter.basemapDistance;
            var go = new GameObject("ForestShotCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox; cam.nearClipPlane = .1f;
            shotCam = cam; shotFog = false;
            // the district fog / aerial passes (forest milk fog, G45) hide the ground; off for the check shots, on again for the game-fog shot
            var fogMbs = Object.FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None).Where(m => m && m.enabled && System.Text.RegularExpressions.Regex.IsMatch(m.GetType().Name, "^District(Fog|Aerial)")).ToList();
            var rp0 = QualitySettings.renderPipeline; int aa0 = QualitySettings.antiAliasing;
            foreach (var m in fogMbs) m.enabled = false;
            // the sky (SkyRenderer22) turns the district fog on at every camera begin; this runs after it and turns it off for our camera
            UnityEngine.Rendering.RenderPipelineManager.beginCameraRendering += NoFog;
            try
            {
                // top: x 165..520, z 40..420 at 3 px/m
                ter.treeDistance = 2000f; ter.basemapDistance = 5000f;   // (QualitySettings untouched: Unity would save them into ProjectSettings)
                cam.orthographic = true; cam.orthographicSize = 190f; cam.aspect = 355f / 380f;
                go.transform.position = new Vector3(342.5f, 400f, 230f); go.transform.rotation = Quaternion.Euler(90, 0, 0);
                Shot(cam, 1065, 1140, Out + Pre(tag) + "top.png"); Shot(cam, 1065, 1140, Out + Pre(tag) + "top.png");
                ter.treeDistance = treeDist0;
                cam.orthographic = false; cam.fieldOfView = 60f; cam.aspect = 1400f / 800f;
                var views = ViewList();
                foreach (var v in views)
                {
                    go.transform.position = v.eye; go.transform.LookAt(v.look);
                    Shot(cam, 1400, 800, Out + Pre(tag) + v.name + ".png");
                }
                // oblique overview from the south-east, above the sea
                go.transform.position = new Vector3(470, 110, 10); go.transform.LookAt(new Vector3(330, 10, 230)); Shot(cam, 1600, 900, Out + Pre(tag) + "oblique.png");
                // one view with the game's own district fog (as the player sees it)
                shotFog = true; foreach (var m in fogMbs) m.enabled = true; var w0 = views[0];
                go.transform.position = w0.eye; go.transform.LookAt(w0.look);
                Shot(cam, 1400, 800, Out + Pre(tag) + "wagon_gamefog.png");
            }
            finally
            {
                UnityEngine.Rendering.RenderPipelineManager.beginCameraRendering -= NoFog;
                foreach (var m in fogMbs) if (m) m.enabled = true;
                if (QualitySettings.renderPipeline != rp0) QualitySettings.renderPipeline = rp0;
                if (QualitySettings.antiAliasing != aa0) QualitySettings.antiAliasing = aa0;

                ter.treeDistance = treeDist0; ter.basemapDistance = base0;
                foreach (var c in gameCams) if (c) c.enabled = true; RenderSettings.fog = fogWas;
                Object.DestroyImmediate(go);
            }
        }

        static void Shot(Camera cam, int w, int h, string file)
        {
            var rt = new RenderTexture(w, h, 24); cam.targetTexture = rt; cam.Render();
            RenderTexture.active = rt; var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply(); File.WriteAllBytes(file, tex.EncodeToPNG());
            RenderTexture.active = null; cam.targetTexture = null; Object.DestroyImmediate(tex); rt.Release(); Object.DestroyImmediate(rt);
        }
    }
}
