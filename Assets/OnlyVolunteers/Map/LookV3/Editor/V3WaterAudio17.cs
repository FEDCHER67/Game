using System;
using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Audio.EditorTools;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // v17 water audio data from the BUILT water (Fedya 2026-10-12: no splash or wading sound in the Elite pools and the
    // river). The plan bake (WaterBaker) puts every body at the plan's absolute -0.3 m and calls everything a lake: the
    // look json writes all water as kind "lake", so the river and canal became lakes with 159 lake-shore emitters, and the
    // style v3 pools / fountain / well stand on their own ground (pools 4.9-14.8 m up Elite Hill), metres above the
    // baked surface, so WaterQuery never saw anyone in them. Here every surface triangle of the built water meshes keeps
    // its own height, the kind comes from the body (river ribbon split river / canal by the plan polygons; pools and the
    // fountain = Pool), and the ambience follows the kind (river banks amb_river, canal amb_stream, lakes / ponds / bogs
    // amb_lake_shore, waterfalls as the plan bake). Written to Audio/Resources/Water_<rev>.asset, the file WaterQuery loads
    // for Map_Look_<rev>_Play; WaterBaker leaves v17+ to this.
    public static class V3WaterAudio17
    {
        public static string AssetPath(string revision) => "Assets/OnlyVolunteers/Audio/Resources/Water_" + revision + ".asset";

        public static void Bake(Transform waterRoot, string revision, List<string> log)
        {
            if (waterRoot == null)
            {
                log.Add("water audio: no Water group, skipped");
                return;
            }
            LookData plan = MapLookBuilder.Load(revision);
            WaterBaker.BuildGeometry(plan, out WaterData.Area[] planAreas, out WaterData.Emitter[] planEmitters);
            var canals = new List<float[]>();
            foreach (LookWater w in plan.water)
                if (w.id == "CANAL" || w.id == "CANAL_MOUTH") canals.Add(w.pts);

            var areas = new List<WaterData.Area>();
            var kinds = new Dictionary<WaterKind, int>();
            foreach (MeshFilter mf in waterRoot.GetComponentsInChildren<MeshFilter>(true))
            {
                string name = mf.name;
                if (mf.sharedMesh == null || !(name.StartsWith("Water_") || name == "Sea")) continue;
                string body = name == "Sea" ? "SEA" : name.Substring("Water_".Length);
                WaterKind bodyKind = KindOf(body);
                // Triangles grouped per kind and 5 cm of height: one area each.
                var groups = new Dictionary<(WaterKind, int), List<float>>();
                Matrix4x4 m = mf.transform.localToWorldMatrix;
                using (Mesh.MeshDataArray arr = Mesh.AcquireReadOnlyMeshData(mf.sharedMesh))
                {
                    Mesh.MeshData md = arr[0];
                    var v = new Unity.Collections.NativeArray<Vector3>(md.vertexCount, Unity.Collections.Allocator.Temp);
                    md.GetVertices(v);
                    for (int s = 0; s < md.subMeshCount; s++)
                    {
                        var idx = new Unity.Collections.NativeArray<int>(md.GetSubMesh(s).indexCount, Unity.Collections.Allocator.Temp);
                        md.GetIndices(idx, s);
                        for (int t = 0; t + 2 < idx.Length; t += 3)
                        {
                            Vector3 a = m.MultiplyPoint3x4(v[idx[t]]), b = m.MultiplyPoint3x4(v[idx[t + 1]]), c = m.MultiplyPoint3x4(v[idx[t + 2]]);
                            float y = (a.y + b.y + c.y) / 3f;
                            WaterKind kind = bodyKind;
                            if (body == "RiverCanal")
                            {
                                float cx = (a.x + b.x + c.x) / 3f, cz = (a.z + b.z + c.z) / 3f;
                                kind = WaterKind.River;
                                foreach (float[] poly in canals)
                                    if (LookGeom.Count(poly) >= 3 && LookGeom.Inside(poly, cx, cz)) kind = WaterKind.Canal;
                            }
                            var key = (kind, Mathf.RoundToInt(y * 20f));
                            if (!groups.TryGetValue(key, out var list)) groups[key] = list = new List<float>();
                            list.AddRange(new[] { a.x, a.z, b.x, b.z, c.x, c.z });
                        }
                        idx.Dispose();
                    }
                    v.Dispose();
                }
                foreach (var g in groups)
                {
                    areas.Add(new WaterData.Area { Id = $"{body}@{g.Key.Item2 * 0.05f:0.00}", Kind = g.Key.Item1, SurfaceY = g.Key.Item2 * 0.05f, Triangles = g.Value.ToArray() });
                    kinds.TryGetValue(g.Key.Item1, out int k);
                    kinds[g.Key.Item1] = k + g.Value.Count / 6;
                }
            }
            // The sea keeps the plan bake's finite apron (the built Sea mesh is the same surface, the apron is wider).
            bool sea = false;
            foreach (WaterData.Area a in planAreas)
                if (a.Kind == WaterKind.Sea)
                {
                    areas.RemoveAll(x => x.Kind == WaterKind.Sea);
                    areas.Add(a);
                    sea = true;
                }

            WaterQuery.InitializeGeometry(areas.ToArray());
            var emitters = new List<WaterData.Emitter>();
            foreach (WaterData.Emitter e in planEmitters)
                if (e.SoundId == SfxIds.AmbWaterfall) emitters.Add(e);
            int river = 0, canal = 0, shore = 0;
            foreach (LookWater w in plan.water)
            {
                if (LookGeom.Count(w.pts) < 3) continue;
                string src = w.id ?? "";
                WaterKind kind = src == "RIVER" ? WaterKind.River : src.StartsWith("CANAL") ? WaterKind.Canal : KindOf(src);
                if (kind == WaterKind.Pool || kind == WaterKind.Puddle) continue;
                string sound = kind == WaterKind.River ? SfxIds.AmbRiver : kind == WaterKind.Canal ? SfxIds.AmbStream : SfxIds.AmbLakeShore;
                float spacing = kind == WaterKind.River ? 26f : 30f;
                LookGeom.Centroid(w.pts, out float cx, out float cy);
                foreach (Vector2 p in Along(w.pts, spacing))
                {
                    // The bank point itself may be just outside the surface: look a little inward, towards the centroid.
                    Vector2 probe = p + (new Vector2(cx, cy) - p).normalized * 1.5f;
                    if (!WaterQuery.SurfaceAt(new Vector3(probe.x, 0f, probe.y), out float y, out _) &&
                        !WaterQuery.SurfaceAt(new Vector3(p.x, 0f, p.y), out y, out _)) y = w.level;
                    emitters.Add(new WaterData.Emitter { Position = new Vector3(p.x, y + 0.1f, p.y), SoundId = sound });
                    if (sound == SfxIds.AmbRiver) river++;
                    else if (sound == SfxIds.AmbStream) canal++;
                    else shore++;
                }
            }

            string path = AssetPath(revision);
            var data = AssetDatabase.LoadAssetAtPath<WaterData>(path);
            bool created = data == null;
            if (created) data = ScriptableObject.CreateInstance<WaterData>();
            data.PlanRevision = revision;
            data.Areas = areas.ToArray();
            data.Emitters = emitters.ToArray();
            if (created) AssetDatabase.CreateAsset(data, path);
            else EditorUtility.SetDirty(data);
            AssetDatabase.SaveAssetIfDirty(data);
            var parts = new List<string>();
            foreach (var kv in kinds) parts.Add($"{kv.Key} {kv.Value}");
            log.Add($"water audio: {areas.Count} areas from the built surfaces (triangles: {string.Join(", ", parts)}{(sea ? ", sea with the plan apron" : "")}); " +
                    $"emitters: river {river}, canal {canal}, lake shore {shore}, waterfall {emitters.Count - river - canal - shore} -> {path}");
        }

        private static WaterKind KindOf(string id)
        {
            string s = id.ToLowerInvariant();
            if (s == "sea") return WaterKind.Sea;
            if (s.Contains("pool") || s.Contains("fountain")) return WaterKind.Pool;
            if (s.Contains("bog")) return WaterKind.Bog;
            if (s.Contains("pond") || s.Contains("well")) return WaterKind.Pond;
            if (s.Contains("canal")) return WaterKind.Canal;
            if (s.Contains("river")) return WaterKind.River;
            return WaterKind.Lake;
        }

        private static IEnumerable<Vector2> Along(float[] pts, float step)
        {
            int n = LookGeom.Count(pts);
            float next = 0f;
            for (int i = 0; i < n; i++)
            {
                var a = new Vector2(pts[2 * i], pts[2 * i + 1]);
                int j = (i + 1) % n;
                var b = new Vector2(pts[2 * j], pts[2 * j + 1]);
                float len = (b - a).magnitude;
                while (next < len)
                {
                    yield return a + (b - a) * (next / Mathf.Max(1e-4f, len));
                    next += step;
                }
                next -= len;
            }
        }
    }
}
