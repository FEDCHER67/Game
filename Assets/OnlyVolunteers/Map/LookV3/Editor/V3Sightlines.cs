using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Occlusion metric of the open look scene (v17 phase A brief): for the sample points of each phase-A district
    // (Working/Reviews/Map_v17_A/sightline_samples.json, made by map_plan_v17.py and identical for v16 and v17), 24
    // horizontal rays at eye 1.7 m and van seat 2.2 m: physics raycasts against every non-trigger collider (buildings,
    // props, fences, terrain) plus tree crowns as vertical cylinders (terrain tree instances, crown radius from the
    // prototype bounds) up to 600 m. Invisible inland-edge blockers are switched off for the run (the view continues).
    // Reports the median free distance and the share of rays free beyond 60, 120 and 250 m; writes sightlines_<label>.json.
    public static class V3Sightlines
    {
        public const string Dir = "Working/Reviews/Map_v17_A";
        private const float MaxDistance = 600f;
        private const int Rays = 24;

        public static string Run(string label)
        {
            string project = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string samplesPath = Path.Combine(project, Dir, "sightline_samples.json");
            if (!File.Exists(samplesPath)) return "no " + samplesPath;
            var sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            Terrain terrain = Object.FindAnyObjectByType<Terrain>();
            if (sampler == null || terrain == null) return "open a look scene (MapHeightSampler + Terrain) first";
            var trees = Trees(terrain);
            var disabled = new List<Collider>();
            foreach (Collider c in Object.FindObjectsByType<Collider>(FindObjectsInactive.Exclude))
            {
                Transform t = c.transform;
                bool blocker = false;
                for (Transform q = t; q != null; q = q.parent)
                    if (q.name == "Blockers" || q.name.StartsWith("Boundary")) { blocker = true; break; }
                if (blocker && c.enabled) { c.enabled = false; disabled.Add(c); }
            }
            Physics.SyncTransforms();
            var sb = new StringBuilder();
            var json = new StringBuilder("{\"label\":\"" + label + "\",\"trees\":" + trees.Count + ",\"districts\":{");
            try
            {
                var root = (Dictionary<string, object>)V3Json.Parse(File.ReadAllText(samplesPath));
                var districts = (Dictionary<string, object>)root["districts"];
                bool firstD = true;
                foreach (var kv in districts)
                {
                    var pts = (List<object>)((Dictionary<string, object>)kv.Value)["points"];
                    if (!firstD) json.Append(',');
                    firstD = false;
                    json.Append("\"" + kv.Key + "\":{");
                    bool firstE = true;
                    foreach (float eye in new[] { 1.7f, 2.2f })
                    {
                        var free = new List<float>();
                        int used = 0, skipped = 0;
                        for (int i = 0; i < pts.Count; i++)
                        {
                            var p = (List<object>)pts[i];
                            float x = (float)(double)p[0], z = (float)(double)p[1];
                            var o = new Vector3(x, sampler.Height(x, z) + eye, z);
                            if (Physics.CheckSphere(o, 0.2f, ~0, QueryTriggerInteraction.Ignore)) { skipped++; continue; }
                            used++;
                            var near = new List<Vector4>();
                            foreach (Vector4 t in trees)
                            {
                                float dx = t.x - x, dz = t.y - z;
                                if (dx * dx + dz * dz < (MaxDistance + 10f) * (MaxDistance + 10f)) near.Add(t);
                            }
                            float offset = (Mathf.Abs((i * 7919 + 104729) % 997) / 997f) * (360f / Rays);
                            for (int r = 0; r < Rays; r++)
                            {
                                float a = (offset + r * 360f / Rays) * Mathf.Deg2Rad;
                                var dir = new Vector3(Mathf.Sin(a), 0f, Mathf.Cos(a));
                                float dist = MaxDistance;
                                if (Physics.Raycast(o, dir, out RaycastHit hit, MaxDistance, ~0, QueryTriggerInteraction.Ignore)) dist = hit.distance;
                                foreach (Vector4 t in near)
                                {
                                    if (t.w < eye) continue;              // crown/bush top below the eye: no block
                                    float cx = t.x - x, cz = t.y - z;
                                    float along = cx * dir.x + cz * dir.z;
                                    if (along <= 0f || along - t.z > dist) continue;
                                    float perp2 = cx * cx + cz * cz - along * along;
                                    float r2 = t.z * t.z;
                                    if (perp2 >= r2) continue;
                                    float h = along - Mathf.Sqrt(r2 - perp2);
                                    if (h < dist) dist = Mathf.Max(0f, h);
                                }
                                free.Add(dist);
                            }
                        }
                        free.Sort();
                        float median = free.Count > 0 ? free[free.Count / 2] : 0f;
                        float Over(float m) { int n = 0; foreach (float f in free) if (f > m) n++; return free.Count > 0 ? 100f * n / free.Count : 0f; }
                        string line = $"{label} {kv.Key} eye {eye:0.0} m: {used} points ({skipped} inside geometry), median free {median:0.0} m, >60 m {Over(60f):0.0} %, >120 m {Over(120f):0.0} %, >250 m {Over(250f):0.0} %";
                        sb.AppendLine(line);
                        if (!firstE) json.Append(',');
                        firstE = false;
                        json.Append(System.FormattableString.Invariant($"\"eye_{eye:0.0}\":{{\"points\":{used},\"skipped\":{skipped},\"median_m\":{median:0.0},\"over60_pct\":{Over(60f):0.0},\"over120_pct\":{Over(120f):0.0},\"over250_pct\":{Over(250f):0.0}}}"));
                    }
                    json.Append('}');
                }
                json.Append("}}");
                File.WriteAllText(Path.Combine(project, Dir, $"sightlines_{label}.json"), json.ToString());
            }
            finally
            {
                foreach (Collider c in disabled) c.enabled = true;
            }
            return sb.ToString();
        }

        // Tree cylinders (x, z, crown radius * 0.75, top height above its ground) from the terrain instances.
        private static List<Vector4> Trees(Terrain terrain)
        {
            TerrainData td = terrain.terrainData;
            var protoSize = new Vector2[td.treePrototypes.Length];
            for (int i = 0; i < protoSize.Length; i++)
            {
                GameObject pf = td.treePrototypes[i].prefab;
                var b = new Bounds();
                bool first = true;
                if (pf != null)
                {
                    LODGroup lg = pf.GetComponentInChildren<LODGroup>();
                    var rs = lg != null && lg.GetLODs().Length > 0 ? lg.GetLODs()[0].renderers : pf.GetComponentsInChildren<Renderer>();
                    foreach (Renderer r in rs)
                    {
                        if (!(r is MeshRenderer) || r.GetComponent<MeshFilter>()?.sharedMesh == null) continue;
                        Bounds mb = r.GetComponent<MeshFilter>().sharedMesh.bounds;
                        Matrix4x4 m = pf.transform.worldToLocalMatrix * r.transform.localToWorldMatrix;
                        for (int k = 0; k < 8; k++)
                        {
                            Vector3 c = m.MultiplyPoint3x4(mb.center + Vector3.Scale(mb.extents, new Vector3((k & 1) == 0 ? -1 : 1, (k & 2) == 0 ? -1 : 1, (k & 4) == 0 ? -1 : 1)));
                            if (first) { b = new Bounds(c, Vector3.zero); first = false; }
                            else b.Encapsulate(c);
                        }
                    }
                }
                protoSize[i] = first ? new Vector2(1f, 1f) : new Vector2((b.size.x + b.size.z) / 4f, b.max.y);
            }
            var list = new List<Vector4>();
            Vector3 tp = terrain.transform.position, ts = td.size;
            foreach (TreeInstance ti in td.treeInstances)
            {
                Vector2 s = protoSize[ti.prototypeIndex];
                list.Add(new Vector4(tp.x + ti.position.x * ts.x, tp.z + ti.position.z * ts.z, s.x * ti.widthScale * 0.75f, s.y * ti.heightScale));
            }
            return list;
        }
    }
}
