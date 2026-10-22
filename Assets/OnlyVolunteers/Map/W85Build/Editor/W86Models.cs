using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // W86 integration (B2, 22.10): real models instead of the grey placeholder boxes.
    //  M1 vehicles (Editor/W86Data/MODELS_M1.json = copy of MapW86_TexturesAll_2026-10-22/M1/MODELS_M1.json): per instance model, variant,
    //     scale, Unity yaw; water craft at sea level 0.0; one URP Lit material per family + variant (MW86_<Family>_<V>); LOD0 / LOD1 of the
    //     FBX through its LODGroup; colliders from the manifest (boxes, or a convex mesh on LOD1); the black SUV for the Elite SUVs.
    //  M2 static props (Art/Props/MapW86_v01/Static/MODELS_M2.json): per data id FBX, rotation rule (-rot or 90 - rot), y offset (gold
    //     statue +1.3, lectern +0.8, neon heart +2.3, fenders -1.0), uniform scale; UCX_* children -> convex MeshColliders (renderer
    //     removed); one URP Lit material for the swatch atlas (mipmaps off on the atlas).
    //  Procedural where no model exists: P1 containers (TT7 atlas, alternating colours), P3 light masts, DC3 tall lamps / bollards / flags,
    //     E2 road lamps, C2 tower crane, traffic lights. NPC spots stay empty markers (W86Prop).
    public static partial class W85Builder
    {
        const string M1Dir = "Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles/";
        const string M2Json = "Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static/MODELS_M2.json";
        const string M2Tex = "Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static/Textures/";
        static string M1Json => Root + "/Editor/W86Data/MODELS_M1.json";

        sealed class M1Inst { public string Model, Kind; public char Var; public float Scale, Yaw, Elev; public bool Water; }
        sealed class M2Inst { public string Type, Fbx; public bool Rot90; public float Y, Scale; }
        static readonly Dictionary<string, M1Inst> M1ById = new();
        static readonly Dictionary<string, Dictionary<string, object>> M1Models = new();
        static readonly Dictionary<string, M2Inst> M2ById = new();
        static readonly Dictionary<string, Material> ModelMats = new();
        static readonly Dictionary<string, GameObject> FbxCache = new();
        static readonly Dictionary<string, int> ModelCount = new();
        static Material m2Mat;

        static void ModelsInit()
        {
            M1ById.Clear(); M1Models.Clear(); M2ById.Clear(); ModelMats.Clear(); FbxCache.Clear(); ModelCount.Clear(); m2Mat = null; propBatches.Clear();
            Folder(Gen + "/Materials/Models");
            if (File.Exists(M1Json))
            {
                var j = Obj(Json.Parse(File.ReadAllText(M1Json)));
                foreach (var kv in Obj(Get(j, "models")) ?? new Dictionary<string, object>()) M1Models[kv.Key] = Obj(kv.Value);
                foreach (var kv in Obj(Get(j, "kinds")) ?? new Dictionary<string, object>())
                    foreach (var i in Arr(Get(Obj(kv.Value), "instances")).Select(Obj))
                    {
                        string model = S(Get(i, "model")) ?? S(Get(Obj(kv.Value), "model"));
                        M1ById[S(Get(i, "id"))] = new M1Inst { Model = model, Kind = kv.Key, Var = (S(Get(i, "variant"), "A") ?? "A")[0], Scale = F(Get(i, "scale"), 1f), Yaw = F(Get(i, "unity_yaw_deg")), Elev = F(Get(i, "elevation_m")),
                            Water = kv.Key == "yacht" || kv.Key == "patrol_boat" };
                    }
            }
            else Note("models: no " + M1Json);
            if (File.Exists(M2Json))
            {
                var j = Obj(Json.Parse(File.ReadAllText(M2Json)));
                foreach (var kv in Obj(Get(j, "types")) ?? new Dictionary<string, object>())
                {
                    var t = Obj(kv.Value);
                    bool rot90 = (S(Get(t, "unity_rotation"), "") ?? "").Contains("90 - rot");
                    foreach (var i in Arr(Get(t, "ids")).Select(Obj))
                        M2ById[S(Get(i, "id"))] = new M2Inst { Type = kv.Key, Fbx = S(Get(i, "fbx")), Rot90 = rot90, Y = F(Get(t, "y_offset_m")), Scale = F(Get(i, "uniform_scale"), 1f) };
                }
            }
            else Note("models: no " + M2Json);
            // texture import as the manifests ask (M2 atlas: no mipmaps, no compression, clamp; M1: mipmaps, clamp, 512)
            foreach (var (p, srgb) in new[] { ("MW86_StaticPalette_v01_Albedo.png", true), ("MW86_StaticPalette_v01_MetallicSmoothness.png", false), ("MW86_StaticPalette_v01_Emission.png", true) })
            {
                var ti = AssetImporter.GetAtPath(M2Tex + p) as TextureImporter; if (!ti) continue;
                if (ti.mipmapEnabled || ti.textureCompression != TextureImporterCompression.Uncompressed || ti.wrapMode != TextureWrapMode.Clamp || ti.sRGBTexture != srgb || ti.maxTextureSize != 256)
                { ti.mipmapEnabled = false; ti.textureCompression = TextureImporterCompression.Uncompressed; ti.wrapMode = TextureWrapMode.Clamp; ti.sRGBTexture = srgb; ti.maxTextureSize = 256; ti.filterMode = FilterMode.Bilinear; ti.SaveAndReimport(); }
            }
            foreach (string f in Directory.Exists(M1Dir + "Textures") ? Directory.GetFiles(M1Dir + "Textures", "*.png") : new string[0])
            {
                var ti = AssetImporter.GetAtPath(f.Replace('\\', '/')) as TextureImporter; if (!ti) continue;
                if (!ti.mipmapEnabled || ti.wrapMode != TextureWrapMode.Clamp || ti.maxTextureSize != 512 || ti.textureCompression != TextureImporterCompression.CompressedHQ)
                { ti.mipmapEnabled = true; ti.wrapMode = TextureWrapMode.Clamp; ti.maxTextureSize = 512; ti.textureCompression = TextureImporterCompression.CompressedHQ; ti.filterMode = FilterMode.Bilinear; ti.SaveAndReimport(); }
            }
            Note($"models: M1 {M1ById.Count} instances / {M1Models.Count} models, M2 {M2ById.Count} ids");
        }

        static GameObject Fbx(string path)
        {
            if (FbxCache.TryGetValue(path, out var g)) return g;
            return FbxCache[path] = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        }
        static Dictionary<string, object> M1Rec(string model) => model != null && M1Models.TryGetValue(model, out var r) ? r : null;
        static GameObject M1Model(string model) { string fbx = S(Get(M1Rec(model), "fbx")); return fbx != null ? Fbx(fbx) : null; }

        static Material M1Mat(string family, char v)
        {
            string key = $"MW86_{family}_{v}";
            if (ModelMats.TryGetValue(key, out var m) && m) return m;
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(M1Dir + "Textures/" + key + ".png");
            m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = key, enableInstancing = true };
            if (tex) m.SetTexture("_BaseMap", tex);
            m.SetColor("_BaseColor", Color.white); m.SetFloat("_Smoothness", .1f); m.SetFloat("_Metallic", 0f);
            AssetDatabase.CreateAsset(m, Gen + "/Materials/Models/" + key + ".mat"); created++;
            return ModelMats[key] = m;
        }

        static Material M2Mat()
        {
            if (m2Mat) return m2Mat;
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "MW86_StaticPalette_v01", enableInstancing = true };
            var alb = AssetDatabase.LoadAssetAtPath<Texture2D>(M2Tex + "MW86_StaticPalette_v01_Albedo.png");
            var ms = AssetDatabase.LoadAssetAtPath<Texture2D>(M2Tex + "MW86_StaticPalette_v01_MetallicSmoothness.png");
            var em = AssetDatabase.LoadAssetAtPath<Texture2D>(M2Tex + "MW86_StaticPalette_v01_Emission.png");
            if (alb) m.SetTexture("_BaseMap", alb);
            m.SetColor("_BaseColor", Color.white);
            if (ms) { m.SetTexture("_MetallicGlossMap", ms); m.EnableKeyword("_METALLICSPECGLOSSMAP"); m.SetFloat("_Smoothness", 1f); m.SetFloat("_SmoothnessTextureChannel", 0f); }
            if (em) { m.SetTexture("_EmissionMap", em); m.SetColor("_EmissionColor", Color.white * 1.5f); m.EnableKeyword("_EMISSION"); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None; }
            AssetDatabase.CreateAsset(m, Gen + "/Materials/Models/MW86_StaticPalette_v01.mat"); created++;
            return m2Mat = m;
        }

        // M1 collider spec -> list of (centre, size) boxes, or null = convex mesh on LOD1
        static List<(Vector3 c, Vector3 s)> M1Colliders(string model)
        {
            var col = Obj(Get(M1Rec(model), "collider"));
            string type = S(Get(col, "type"), "");
            if (type == "convex_mesh") return null;
            var boxes = Arr(Get(col, "boxes")).Select(Obj).Where(x => x != null).ToList();
            Vector3 V3(object o) { var a = Arr(o); return a.Count >= 3 ? new Vector3(F(a[0]), F(a[1]), F(a[2])) : Vector3.zero; }
            return boxes.Select(x => (V3(Get(x, "center")), V3(Get(x, "size")))).ToList();
        }

        // a model (plain copy, no prefab link: UCX children are stripped), placed, materialled, collided, LODs set
        static GameObject PlaceModel(Transform parent, string name, GameObject src, Vector3 pos, float yaw, float scale, Material mat, List<(Vector3 c, Vector3 s)> boxes, bool isStatic, bool m2 = false)
        {
            var go = Object.Instantiate(src, parent);
            go.name = name;
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0, yaw, 0));
            go.transform.localScale = Vector3.one * scale;
            bool ucx = false;
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true).Where(m => m.name.StartsWith("UCX_")).ToList())
            {
                var o = mf.gameObject; var mesh = mf.sharedMesh;
                Object.DestroyImmediate(o.GetComponent<MeshRenderer>()); Object.DestroyImmediate(mf);
                var mc = o.AddComponent<MeshCollider>(); mc.sharedMesh = mesh; mc.convex = true; ucx = true;
            }
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>(true))
                if (mat) r.sharedMaterials = Enumerable.Repeat(mat, Mathf.Max(1, r.sharedMaterials.Length)).ToArray();
            if (!ucx)
            {
                if (boxes != null && boxes.Count > 0)
                {
                    var cols = new GameObject("colliders").transform; cols.SetParent(go.transform, false);
                    foreach (var (c, s) in boxes) { var bc = cols.gameObject.AddComponent<BoxCollider>(); bc.center = c; bc.size = s; }
                }
                else if (boxes == null)
                {
                    var lod1 = go.GetComponentsInChildren<MeshFilter>(true).FirstOrDefault(m => m.name.EndsWith("_LOD1")) ?? go.GetComponentsInChildren<MeshFilter>(true).FirstOrDefault();
                    if (lod1) { var mc = lod1.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = lod1.sharedMesh; mc.convex = true; }
                }
            }
            // LODs: LOD0 above 15 % (M1) / 8 % (M2) of the screen height, LOD1 to 2 % / 1 %; single-mesh props culled below 1 %
            var lg = go.GetComponent<LODGroup>();
            var r0 = go.GetComponentsInChildren<Renderer>(true).Where(r => r.name.EndsWith("_LOD0")).ToArray();
            var r1 = go.GetComponentsInChildren<Renderer>(true).Where(r => r.name.EndsWith("_LOD1")).ToArray();
            if (!lg) lg = go.AddComponent<LODGroup>();
            if (r0.Length > 0 && r1.Length > 0) lg.SetLODs(new[] { new LOD(m2 ? .08f : .15f, r0), new LOD(m2 ? .01f : .02f, r1) });
            else lg.SetLODs(new[] { new LOD(m2 ? .01f : .015f, go.GetComponentsInChildren<Renderer>(true)) });
            lg.RecalculateBounds();
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true))
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, isStatic ? StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic : 0);
            return go;
        }

        // ================================================================== Prop hook (before W86Prop / the prefab table / the box)
        static bool W86Model(Transform parent, Dictionary<string, object> p, string kind, string id, Vector2 q)
        {
            try
            {
                if (id == "10-portico" && T2Available()) return true;                    // the T115 palace has its own portico steps
                float rot = F(Get(p, "rot_deg"));
                bool grip = (Get(p, "grip_anchor") is bool g && g) || Grip.Contains(kind);
                if (M2ById.TryGetValue(id, out var m2) && m2.Fbx != null && Fbx(m2.Fbx))
                {
                    float y = Height(q.x, q.y) + m2.Y;
                    var go = PlaceModel(parent, id, Fbx(m2.Fbx), new Vector3(q.x, y, q.y), m2.Rot90 ? 90f - rot : -rot, m2.Scale, M2Mat(), new List<(Vector3, Vector3)>(), true, true);
                    if (grip) go.AddComponent<W76GripAnchor>();
                    if (kind == "leave_country_button") go.AddComponent<W76LeaveCountryButton>();
                    ModelCount["M2 " + m2.Type] = ModelCount.TryGetValue("M2 " + m2.Type, out int c) ? c + 1 : 1;
                    return true;
                }
                if (M1ById.TryGetValue(id, out var m1))
                {
                    var src = M1Model(m1.Model);
                    if (src)
                    {
                        string fam = S(Get(M1Rec(m1.Model), "family"), "Machines");
                        float y = m1.Water ? 0f : Height(q.x, q.y) + m1.Elev;
                        var go = PlaceModel(parent, id, src, new Vector3(q.x, y, q.y), m1.Yaw, m1.Scale, M1Mat(fam, m1.Var), M1Colliders(m1.Model), m1.Kind != "patrol_boat");
                        if (grip) go.AddComponent<W76GripAnchor>();
                        ModelCount["M1 " + m1.Model] = ModelCount.TryGetValue("M1 " + m1.Model, out int c) ? c + 1 : 1;
                        return true;
                    }
                }
                switch (kind)
                {
                    case "round_hay_bale":
                    {   // T14 a: the T1 bale (radius 0.75, along local X, pivot at the centre)
                        var pf = AssetDatabase.LoadAssetAtPath<GameObject>(T1Pref + "T1_HayBale_a.prefab"); if (!pf) return false;
                        var go = (GameObject)PrefabUtility.InstantiatePrefab(pf, parent);
                        go.name = id; go.transform.SetPositionAndRotation(P(q, .72f), Quaternion.Euler(0, 90f - rot, 0));
                        if (!go.GetComponentInChildren<Collider>()) { var cc = go.AddComponent<CapsuleCollider>(); cc.direction = 0; cc.radius = .72f; cc.height = 1.2f; }
                        foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                        Done("T14 hay bales");
                        return true;
                    }
                    case "shipping_container_20ft": case "shipping_container_40ft":
                    {
                        if (Get(p, "on_truck") is bool ot && ot) return true;                 // the M1 truck model carries its own 40 ft box
                        var sz = Arr(Get(p, "size"));
                        float L = sz.Count > 0 ? F(sz[0]) : 6.06f, Wd = sz.Count > 1 ? F(sz[1]) : 2.44f;
                        int tiers = Mathf.Max(1, (int)F(Get(p, "tiers"), 1f));
                        float lift = F(Get(p, "lifted_m")), y0 = Height(q.x, q.y) + lift;
                        var b = PropBatch(parent, "Containers_P1");
                        for (int t = 0; t < tiers; t++)
                            RContainer(b, new Vector3(q.x, y0 + t * 2.59f, q.y), kind.Contains("40"), -rot, RX(P1Colours[(int)(RHash(id + t, 31) * P1Colours.Length) % P1Colours.Length]), new Vector3(L, 2.59f, Wd));
                        var col = new GameObject(id).AddComponent<BoxCollider>(); col.transform.SetParent(parent, false);
                        col.transform.SetPositionAndRotation(new Vector3(q.x, y0 + tiers * 1.295f, q.y), Quaternion.Euler(0, -rot, 0)); col.size = new Vector3(L, tiers * 2.59f, Wd);
                        Done("P1 containers", tiers);
                        return true;
                    }
                    case "light_mast" when parent.name.Contains("port"):
                    {
                        float h = Arr(Get(p, "size")).Count > 2 ? F(Arr(Get(p, "size"))[2]) : 20f;
                        P3Mast(PropBatch(parent, "Masts_P3"), P(q), h);
                        PoleCollider(parent, id, P(q), h, grip);
                        Done("P3 light masts");
                        return true;
                    }
                    case "lamp_tall" when parent.name.Contains("downtown"):
                    {   // DC3 tall lamp, own object (the N-R3 night light finds it by name)
                        var b = new RBatch();
                        DcTallLamp(b, Vector3.zero, RX("E6E6E2"), (int)(RHash(id, 5) * 2) == 0 ? RX("E07A2E") : RX("3A3D42"), q.x > 1028f);
                        var go = new GameObject(id); go.transform.SetParent(parent, false); go.transform.position = P(q);
                        RFlushLocal(b, go.transform, "DC3_lamp_" + id);
                        PoleCollider(go.transform, "pole", P(q), 6.2f, grip, true);
                        Done("DC3 tall lamps");
                        return true;
                    }
                    case "flagpole":
                    {
                        float h = Arr(Get(p, "size")).Count > 2 ? F(Arr(Get(p, "size"))[2]) : 10f;
                        var b = PropBatch(parent, "Flags_W86");
                        Vector3 at = P(q);
                        RCyl(b, T7("flat_metal"), at, .06f, h, 8, RX("D6D6D2"));
                        RCyl(b, T7("flat_metal"), at + Vector3.up * h, .09f, .12f, 8, RX("C9A44C"));
                        var flag = T1M("T1_flag");
                        string fk = flag ? RSurfKey("t1:flag", flag, 1f) : T7("flat");
                        Color fc = parent.name.Contains("elite") ? RX("2F4E8C") : new[] { RX("E07A2E"), RX("3A3D42"), RX("D6D4CE") }[(int)(RHash(id, 6) * 3) % 3];
                        float fw = 1.8f, fh = 1.2f; Vector3 dir = Quaternion.Euler(0, -rot, 0) * Vector3.right;
                        Vector3 o = at + Vector3.up * (h - .15f);
                        b[fk].Quad(o, o + Vector3.down * fh, o + Vector3.down * fh + dir * fw, o + dir * fw, new(0, 1), new(0, 0), new(1, 0), new(1, 1), fc);
                        b[fk].Quad(o + dir * fw, o + Vector3.down * fh + dir * fw, o + Vector3.down * fh, o, new(1, 1), new(1, 0), new(0, 0), new(0, 1), fc);
                        PoleCollider(parent, id, at, h, grip);
                        Done("flagpoles + cloth flags");
                        return true;
                    }
                    case "tower_crane":
                    {
                        var sz = Arr(Get(p, "size"));
                        float H = sz.Count > 2 ? F(sz[2]) : 32f;
                        var b = PropBatch(parent, "TowerCrane_C2");
                        TowerCrane(b, P(q), -rot, RX("C8463A"), RX("EDEBE4"), H, F(Get(p, "jib_len_m"), 30f), F(Get(p, "counter_jib_len_m"), 9.2f));
                        var col = new GameObject(id).AddComponent<BoxCollider>(); col.transform.SetParent(parent, false);
                        col.transform.position = P(q, H / 2 + .8f); col.size = new Vector3(1.8f, H + 1.6f, 1.8f);
                        if (grip) col.gameObject.AddComponent<W76GripAnchor>();
                        Done("C2 tower crane");
                        return true;
                    }
                    case "traffic_light":
                    {
                        var b = PropBatch(parent, "TrafficLights_W86");
                        TrafficLight(b, P(q), -rot);
                        PoleCollider(parent, id, P(q), 4.2f, true);
                        Done("traffic lights");
                        return true;
                    }
                }
            }
            catch (Exception e) { RolloutIssue($"{id} ({kind}) model failed: {e.Message}"); }
            return false;
        }

        static void PoleCollider(Transform parent, string name, Vector3 at, float h, bool grip, bool keepName = false)
        {
            var g = new GameObject(name); g.transform.SetParent(parent, false); g.transform.position = at + Vector3.up * h * .5f;
            var c = g.AddComponent<CapsuleCollider>(); c.radius = .18f; c.height = h;
            if (grip) g.AddComponent<W76GripAnchor>();
            GameObjectUtility.SetStaticEditorFlags(g, StaticEditorFlags.BatchingStatic);
        }

        // merged procedural props per district (one mesh per surface), flushed at the end of the district
        static readonly Dictionary<(Transform, string), RBatch> propBatches = new();
        static RBatch PropBatch(Transform parent, string name)
        {
            if (!propBatches.TryGetValue((parent, name), out var b)) propBatches[(parent, name)] = b = new RBatch();
            return b;
        }
        static void FlushPropBatches(Transform parent)
        {
            foreach (var kv in propBatches.Where(k => k.Key.Item1 == parent).ToList())
            {
                var holder = new GameObject(kv.Key.Item2).transform; holder.SetParent(parent, false);
                RFlush(kv.Value, holder, Safe(parent.name) + "_" + kv.Key.Item2);
                var lod = holder.gameObject.AddComponent<LODGroup>(); lod.SetLODs(new[] { new LOD(.004f, holder.GetComponentsInChildren<Renderer>()) }); lod.RecalculateBounds();
                propBatches.Remove(kv.Key);
            }
        }

        // flush a batch built around the object's own origin (local mesh)
        static void RFlushLocal(RBatch b, Transform go, string name)
        {
            foreach (var kv in b.By)
            {
                var mb = kv.Value; if (mb.V.Count == 0) continue;
                var mesh = new Mesh { name = name + "_" + kv.Key.Replace(':', '_') };
                mesh.SetVertices(mb.V); mesh.SetUVs(0, mb.U); mesh.SetColors(mb.C); mesh.SetTriangles(mb.T, 0);
                mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, Gen + "/Meshes/" + Safe(mesh.name) + ".asset");
                var g = new GameObject(mesh.name); g.transform.SetParent(go, false);
                g.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = g.AddComponent<MeshRenderer>(); r.sharedMaterial = RS[kv.Key].M;
                if (RNoShadow.Contains(kv.Key)) r.shadowCastingMode = ShadowCastingMode.Off;
                GameObjectUtility.SetStaticEditorFlags(g, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            }
        }

        // procedural traffic light: dark pole, arm over the carriageway, head with three lamps (no text)
        static void TrafficLight(RBatch b, Vector3 at, float yaw)
        {
            var f = RFr.Yaw(at, yaw);
            string fm = T7("flat_metal"); Color dk = RX("2B2D30");
            RCyl(b, fm, at, .1f, 4.4f, 10, dk);
            RBeam(b, fm, f.P(0, 4.2f, 0), f.P(2.6f, 4.3f, 0), .08f, .08f, dk);
            RBox(b, fm, f, new Vector3(2.6f, 3.75f, 0), new Vector3(.34f, .95f, .3f), dk, RALL6);
            string lamp = RSurfKey("w86:signal", W86Mat("W86_signal_lens", new Color(.9f, .85f, .7f), .6f, 0f, new Color(.5f, .45f, .3f)), 1f, true);
            foreach (var (y, c) in new[] { (4.05f, RX("C8463A")), (3.75f, RX("E2B32E")), (3.45f, RX("4FA35A")) })
                RBox(b, lamp, f, new Vector3(2.6f, y, -.16f), new Vector3(.2f, .2f, .03f), c, RALL6);
            RBox(b, fm, f, new Vector3(0, 2.8f, -.12f), new Vector3(.24f, .5f, .18f), dk, RALL6);       // pedestrian head
        }

        // E2 lamps on the stone road (the W85 Lamp cylinders: colliders + grip kept, the cylinder renderer off)
        static void EliteRoadLamps(Transform root)
        {
            var lamps = root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith("Lamps_elite"));
            if (!lamps) return;
            var b = new RBatch(); int n = 0;
            foreach (Transform l in lamps)
            {
                var mr = l.GetComponent<MeshRenderer>(); if (!mr) continue;
                Vector3 baseP = l.position - Vector3.up * l.localScale.y;
                E2Lamp(b, baseP);
                Object.DestroyImmediate(mr); var mf = l.GetComponent<MeshFilter>(); if (mf) Object.DestroyImmediate(mf);
                n++;
            }
            var holder = new GameObject("E2_lamps").transform; holder.SetParent(lamps, false);
            RFlush(b, holder, "E2_road_lamps");
            if (n > 0) Done("E2 stone road lamps", n);
        }

        // DC3 bollards along a row (dark posts with a cap); one merged mesh, a box collider + grip anchor per bollard
        static void DcBollards(Transform parent, string id, Vector2[] line, bool grip)
        {
            var b = new RBatch(); string fm = T7("flat_metal"); Color c = RX("383C40");
            var holder = new GameObject("Bollards_" + id).transform; holder.SetParent(parent, false);
            int n = 0;
            foreach (var q in Resample(line, 1.6f))
            {
                Vector3 at = P(q);
                RCyl(b, fm, at, .11f, .9f, 12, c); RCyl(b, fm, at + Vector3.up * .9f, .13f, .06f, 12, c);
                var g = new GameObject("Bollard"); g.transform.SetParent(holder, false); g.transform.position = at + Vector3.up * .45f;
                g.AddComponent<BoxCollider>().size = new Vector3(.24f, .9f, .24f);
                if (grip) g.AddComponent<W76GripAnchor>();
                n++;
            }
            RFlush(b, holder, "DC3_bollards_" + id);
            Done("DC3 bollards", n);
        }

        // ================================================================== remaining grey placeholders (primitive cube / cylinder renderers)
        static readonly string[] DeliberatePrimitives = { "Planter_", "Pier_bridge_", "Portal_", "04-box-floodlight" };
        static string GreyBoxReport(Transform root)
        {
            var groups = new Dictionary<string, int>(); int n = 0, kept = 0;
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!mf.sharedMesh || (mf.sharedMesh.name != "Cube" && mf.sharedMesh.name != "Cylinder")) continue;
                var r = mf.GetComponent<MeshRenderer>(); if (!r || !r.enabled) continue;
                if (DeliberatePrimitives.Any(p => mf.name.StartsWith(p))) { kept++; continue; }       // textured kerbs / piers / masts
                string top = mf.transform.parent ? mf.transform.parent.name : "";
                string key = top + "/" + System.Text.RegularExpressions.Regex.Replace(mf.name, "[0-9]+", "#") + " (" + (r.sharedMaterial ? r.sharedMaterial.name : "no material") + ")";
                groups[key] = groups.TryGetValue(key, out int c) ? c + 1 : 1; n++;
            }
            return $"grey placeholders left (untextured primitive cube / cylinder props): {n}" + (n > 0 ? " - " + string.Join(", ", groups.OrderByDescending(k => k.Value).Select(k => $"{k.Key} {k.Value}")) : "") +
                   $"; textured primitive pieces kept (planter kerbs, bridge piers, portals, floodlight masts): {kept}";
        }

        static string ModelSummary() =>
            $"models: {ModelCount.Values.Sum()} placed (" + string.Join(", ", ModelCount.OrderBy(k => k.Key).Select(k => $"{k.Key} {k.Value}")) + ")";
    }
}
