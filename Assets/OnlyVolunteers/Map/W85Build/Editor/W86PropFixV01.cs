using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Map.W85
{
    // W86 prop fixes v01 (Fedya 25.10 screenshot 07): the Old Town double street lamp's two lantern bodies hang ~0.15 m above the tips of
    // their curled arms, connected to nothing. A fixed copy adds a short black stem on each side from the arm (x ±0.62, y 3.02) into the
    // lantern's bottom finial (y 3.36), in the black-metal submesh. Source meshes stay as they are (copies in Generated/<ver>/PropFix_v01);
    // the play scene's filters (original or the smooth-normals copy) are pointed at the fixed copy. Runs from W85PlayIntegrator after
    // the smooth-normals step; idempotent.
    public static class W86PropFixV01
    {
        const string LampDouble = "lamp_oldtown_double";

        public static string Apply(Scene scene, string ver)
        {
            string dir = $"Assets/OnlyVolunteers/Map/W85Build/Generated/{ver}/PropFix_v01";
            if (!AssetDatabase.IsValidFolder(dir)) AssetDatabase.CreateFolder($"Assets/OnlyVolunteers/Map/W85Build/Generated/{ver}", "PropFix_v01");
            string outPath = $"{dir}/{LampDouble}_fix01.asset";
            Mesh fixedMesh = AssetDatabase.LoadAssetAtPath<Mesh>(outPath);
            int n = 0;
            foreach (var mf in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshFilter>(true)))
            {
                var m = mf.sharedMesh;
                if (!m || m == fixedMesh || !(m.name == LampDouble || m.name == LampDouble + "_sn01")) continue;
                if (!fixedMesh)
                {
                    fixedMesh = WithStems(m);
                    AssetDatabase.CreateAsset(fixedMesh, outPath);
                }
                mf.sharedMesh = fixedMesh;
                PrefabUtility.RecordPrefabInstancePropertyModifications(mf);
                n++;
            }
            AssetDatabase.SaveAssets();
            return $"prop fixes v01: {n} Old Town double lamps get stems between arms and lanterns";
        }

        // ---------------------------------------------------------------- coplanar surfaces (Fedya's recording 25.10)
        // The "tower shadow that pops with distance" on the Downtown square was z-fighting: zone surfaces generated at the same
        // height (plaza 5.04 / parking 5.04 / stone band 5.05) overlap, and depth precision picks one or the other by camera
        // distance. Every flat surface (zones, plaza bands, sidewalks, streets) lying on a larger one within 2.5 cm is lifted 3 cm
        // above it (smaller on top; chains stack). Scene transforms only (the meshes stay); re-run safe: it starts from a marker.
        public static string LiftCoplanar(Scene scene)
        {
            bool Flat(Renderer r) => r && r.bounds.size.y < .35f && r.bounds.size.x * r.bounds.size.z > 4f &&
                (r.name.StartsWith("Zone_") || r.name.Contains("plaza") || r.name.StartsWith("Sidewalk") || r.name.StartsWith("Street_") || r.name.StartsWith("DC3_"));
            var rs = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>(true)).Where(Flat)
                .OrderByDescending(r => r.bounds.size.x * r.bounds.size.z).ToList();
            var top = new Dictionary<Renderer, float>(); int lifted = 0;
            foreach (var r in rs)
            {
                var b = r.bounds; float y = b.max.y, lift = 0f;
                foreach (var kv in top)
                {
                    var o = kv.Key.bounds;
                    if (b.max.x <= o.min.x || b.min.x >= o.max.x || b.max.z <= o.min.z || b.min.z >= o.max.z) continue; // no XZ overlap
                    if (kv.Key.sharedMaterial == r.sharedMaterial) continue; // same surface (sidewalk on sidewalk): no visible fight, no step
                    if (Mathf.Abs(kv.Value - (y + lift)) < .025f) lift = kv.Value - y + .03f;
                }
                if (lift > 0f && !r.name.EndsWith("_lifted"))
                {
                    r.transform.position += Vector3.up * lift; r.name += "_lifted"; lifted++;
                    EditorUtility.SetDirty(r.transform);
                }
                top[r] = y + (r.name.EndsWith("_lifted") ? lift : 0f);
            }
            return $"coplanar: {lifted} flat surfaces lifted 3 cm above the larger surface they overlapped (z-fighting)";
        }

        // ---------------------------------------------------------------- traffic signals (screenshot 06)
        // The built signals are one merged mesh per district (pole, arm, flat head, lens tiles that cannot switch). Over every head
        // (placements: kind traffic_light in details_v85.json + downtown_v85.json) goes a real one: a deeper housing that encloses the
        // old head, a backplate, a collar on the arm, a hood over each lens, and three lens discs switched by W86TrafficSignalsV01.
        public static string TrafficSignals(Scene scene, string ver)
        {
            var old = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).FirstOrDefault(t => t.name == "W86_TrafficSignals");
            if (old) Object.DestroyImmediate(old.gameObject); // rebuilt each run (cheap, idempotent)
            string data = Application.dataPath + $"/OnlyVolunteers/Map/W85Build/Data/{ver}/";
            var places = new List<(Vector2 p, float rot, string junction)>();
            foreach (var file in new[] { data + "details_v85.json", data + "districts/downtown_v85.json" })
            {
                if (!System.IO.File.Exists(file)) continue;
                string txt = System.IO.File.ReadAllText(file);
                foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(txt, @"\{[^{}]*""traffic_light""[^{}]*\}"))
                {
                    var pm = System.Text.RegularExpressions.Regex.Match(m.Value, @"""pos""\s*:\s*\[\s*([-0-9.]+)\s*,\s*([-0-9.]+)");
                    if (!pm.Success) continue;
                    var rm = System.Text.RegularExpressions.Regex.Match(m.Value, @"""(?:rot_deg|facing_deg)""\s*:\s*([-0-9.]+)");
                    var jm = System.Text.RegularExpressions.Regex.Match(m.Value, @"""junction""\s*:\s*""([^""]+)""");
                    var q = new Vector2(float.Parse(pm.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture), float.Parse(pm.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture));
                    if (places.Any(x => (x.p - q).sqrMagnitude < 1f)) continue;
                    places.Add((q, rm.Success ? float.Parse(rm.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : 0f, jm.Success ? jm.Groups[1].Value : q.ToString()));
                }
            }
            if (places.Count == 0) return "signals: no traffic_light placements found";
            string dir = $"Assets/OnlyVolunteers/Map/W85Build/Generated/{ver}/PropFix_v01";
            Material Lens(string name, Color c, bool on)
            {
                string path = $"{dir}/W86_Signal_{name}_{(on ? "on" : "off")}.mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, path); }
                m.SetColor("_BaseColor", on ? Color.Lerp(c, Color.white, .25f) : c * .22f); m.SetFloat("_Smoothness", .85f); m.SetFloat("_Metallic", 0f);
                if (on) { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", c * 4.5f); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None; }
                else { m.DisableKeyword("_EMISSION"); m.SetColor("_EmissionColor", Color.black); }
                EditorUtility.SetDirty(m); return m;
            }
            Color red = new(1f, .16f, .1f), amber = new(1f, .62f, .08f), green = new(.2f, 1f, .45f);
            var housingMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Art/TextureTest_v01/Built_v04/Materials/Kit/TT_FK_Metal_Dark.mat");
            var rootGo = new GameObject("W86_TrafficSignals"); SceneManager.MoveGameObjectToScene(rootGo, scene);
            var comp = rootGo.AddComponent<W86TrafficSignalsV01>();
            comp.redOn = Lens("red", red, true); comp.redOff = Lens("red", red, false);
            comp.amberOn = Lens("amber", amber, true); comp.amberOff = Lens("amber", amber, false);
            comp.greenOn = Lens("green", green, true); comp.greenOff = Lens("green", green, false);
            var heads = new List<W86TrafficSignalsV01.Head>(); var junctionIds = new Dictionary<string, int>();
            var terrain = Terrain.activeTerrain;
            foreach (var (q, rot, junction) in places)
            {
                float y = terrain ? terrain.SampleHeight(new Vector3(q.x, 0, q.y)) + terrain.transform.position.y : 0f;
                var head = new GameObject("Signal_" + junction); head.transform.SetParent(rootGo.transform, false);
                head.transform.SetPositionAndRotation(new Vector3(q.x, y, q.y), Quaternion.Euler(0, -rot, 0));
                GameObject Box(string n, Vector3 c, Vector3 s, Material m, bool isStatic = true)
                {
                    var g = GameObject.CreatePrimitive(PrimitiveType.Cube); g.name = n; Object.DestroyImmediate(g.GetComponent<Collider>());
                    g.transform.SetParent(head.transform, false); g.transform.localPosition = c; g.transform.localScale = s;
                    g.GetComponent<MeshRenderer>().sharedMaterial = m;
                    if (isStatic) GameObjectUtility.SetStaticEditorFlags(g, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                    return g;
                }
                Box("Housing", new Vector3(2.6f, 3.75f, 0f), new Vector3(.44f, 1.08f, .38f), housingMat);
                Box("Backplate", new Vector3(2.6f, 3.75f, .215f), new Vector3(.64f, 1.26f, .03f), housingMat);
                Box("Collar", new Vector3(2.6f, 4.3f, 0f), new Vector3(.17f, .12f, .17f), housingMat);
                var lens = new Renderer[3]; int k = 0;
                foreach (float ly in new[] { 4.07f, 3.75f, 3.43f })
                {
                    Box("Hood", new Vector3(2.6f, ly + .135f, -.27f), new Vector3(.27f, .025f, .17f), housingMat);
                    var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder); disc.name = "Lens"; Object.DestroyImmediate(disc.GetComponent<Collider>());
                    disc.transform.SetParent(head.transform, false); disc.transform.localPosition = new Vector3(2.6f, ly, -.19f);
                    disc.transform.localRotation = Quaternion.Euler(90f, 0, 0); disc.transform.localScale = new Vector3(.21f, .012f, .21f);
                    var r = disc.GetComponent<MeshRenderer>(); r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                    lens[k++] = r;
                }
                lens[0].sharedMaterial = comp.redOff; lens[1].sharedMaterial = comp.amberOff; lens[2].sharedMaterial = comp.greenOff;
                if (!junctionIds.TryGetValue(junction, out int jid)) junctionIds[junction] = jid = junctionIds.Count;
                int axis = Mathf.RoundToInt(Mathf.Repeat(rot, 180f) / 90f) % 2;
                heads.Add(new W86TrafficSignalsV01.Head { red = lens[0], amber = lens[1], green = lens[2], junction = jid, axis = axis });
            }
            comp.heads = heads.ToArray();
            AssetDatabase.SaveAssets();
            return $"signals: {heads.Count} heads at {junctionIds.Count} junctions (housing, hoods, switching lenses)";
        }

        static Mesh WithStems(Mesh src)
        {
            var m = Object.Instantiate(src); m.name = LampDouble + "_fix01";
            var v = new List<Vector3>(m.vertices); var nrm = new List<Vector3>(m.normals);
            var uv = new List<Vector2>(); m.GetUVs(0, uv); while (uv.Count < v.Count) uv.Add(Vector2.zero);
            var cols = new List<Color>(); m.GetColors(cols); bool hasCols = cols.Count == v.Count;
            var subs = new List<int[]>(); for (int s = 0; s < m.subMeshCount; s++) subs.Add(m.GetTriangles(s));
            var add = new List<int>(subs[0]); // black metal
            foreach (float x in new[] { .62f, -.62f })
            {
                const int seg = 10; const float r = .032f, y0 = 3.02f, y1 = 3.36f;
                int b = v.Count;
                for (int i = 0; i <= seg; i++)
                {
                    float a = i / (float)seg * Mathf.PI * 2; var d = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
                    v.Add(new Vector3(x, y0, 0) + d * r); nrm.Add(d); uv.Add(new Vector2(i / (float)seg, 0));
                    v.Add(new Vector3(x, y1, 0) + d * r); nrm.Add(d); uv.Add(new Vector2(i / (float)seg, 1));
                    if (hasCols) { cols.Add(Color.white); cols.Add(Color.white); }
                }
                for (int i = 0; i < seg; i++)
                {
                    int a0 = b + i * 2, a1 = a0 + 1, b0 = a0 + 2, b1 = a0 + 3;
                    add.AddRange(new[] { a0, a1, b0, b0, a1, b1 });
                }
            }
            subs[0] = add.ToArray();
            m.SetVertices(v); m.SetNormals(nrm); m.SetUVs(0, uv); if (hasCols) m.SetColors(cols);
            for (int s = 0; s < subs.Count; s++) m.SetTriangles(subs[s], s);
            m.RecalculateTangents(); m.RecalculateBounds();
            return m;
        }
    }
}
