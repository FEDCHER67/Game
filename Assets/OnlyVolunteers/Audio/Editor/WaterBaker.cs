using System;
using System.Collections.Generic;
using OnlyVolunteers.Map.Look;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Audio.EditorTools
{
    public static class WaterBaker
    {
        // Keep the legacy Water_latest asset intact; each scene revision owns its baked water.
        private static string AssetPathFor(string revision) => "Assets/OnlyVolunteers/Audio/Resources/Water_" + revision + ".asset";

        [MenuItem("OnlyVolunteers/Audio/Bake Water Zones (latest plan)")]
        public static void Bake() => Bake(MapLookBuilder.LatestRevision());

        [MenuItem("OnlyVolunteers/Audio/Bake Water Zones (v12)")]
        public static void BakeV12() => Bake("v12");

        [MenuItem("OnlyVolunteers/Audio/Bake Water Zones (v16)")]
        public static void BakeV16() => Bake("v16");

        public static void Bake(string revision)
        {
            if (EditorApplication.isPlaying) { Debug.LogWarning("[WaterBake] Exit Play mode first."); return; }
            if (string.IsNullOrEmpty(revision)) { Debug.LogError("[WaterBake] No look_vNN_flat.json found."); return; }
            // v17+: the plan has every body at -0.3 m and of kind "lake"; the style v3 look build bakes Water_<rev> from the
            // built surfaces (pools on Elite Hill, river vs canal) instead (Map/LookV3/Editor/V3WaterAudio17).
            if (OnlyVolunteers.Map.Look.V3.MapLookBuilderV3.IsV17(revision))
            {
                Debug.Log("[WaterBake] " + revision + ": baked by OnlyVolunteers/Map/Style v3/Build Map Look " + revision +
                          " (+ Gameplay) from the built water surfaces; nothing to do here.");
                return;
            }
            try
            {
                LookData look = MapLookBuilder.Load(revision);
                BuildGeometry(look, out WaterData.Area[] areas, out WaterData.Emitter[] emitters);
                string assetPath = AssetPathFor(revision);
                WaterData data = AssetDatabase.LoadAssetAtPath<WaterData>(assetPath);
                bool created = data == null;
                if (created) data = ScriptableObject.CreateInstance<WaterData>();
                data.PlanRevision = revision;
                data.Areas = areas;
                data.Emitters = emitters;
                if (created) AssetDatabase.CreateAsset(data, assetPath);
                else EditorUtility.SetDirty(data);
                AssetDatabase.SaveAssetIfDirty(data);
                Debug.Log("[WaterBake] " + revision + ": " + areas.Length + " areas, " + emitters.Length +
                    " emitters -> " + assetPath + ". Refill SfxLibrary for the water ids before listening.", data);
            }
            catch (Exception exception) { Debug.LogError("[WaterBake] " + exception); }
        }

        // Pure geometry entry point: offline checks and the editor bake share the exact implementation.
        public static void BuildGeometry(LookData look, out WaterData.Area[] areas, out WaterData.Emitter[] emitters)
        {
            var water = new List<WaterData.Area>();
            var sound = new List<WaterData.Emitter>();
            foreach (LookWater w in look.water)
            {
                WaterKind kind = Kind(w.kind, w.id);
                // WaterBuilder uses the lake triangles and resamples every river/canal ribbon at 2 m.
                bool polygon = w.kind == "lake";
                float[] triangles = polygon ? w.tris : Ribbon(w);
                water.Add(new WaterData.Area { Id = w.id, Kind = kind, SurfaceY = w.level, Triangles = triangles });
                if (polygon) EmitAlong(w.pts, true, w.level, SfxIds.AmbLakeShore, sound);
                else if (kind != WaterKind.Puddle)
                    EmitAlong(w.pts, false, w.level, Math.Max(w.w, w.wet_w) < 4f ? SfxIds.AmbStream : SfxIds.AmbRiver, sound);
            }

            LookSea sea = look.sea;
            if (LookGeom.Count(sea.pts) >= 3)
            {
                var triangles = new List<float>(sea.tris);
                // This is WaterBuilder.Sea's finite apron, including its open-edge test (no global sea plane).
                float[] apron = LookGeom.OffsetPolygon(sea.pts, Math.Max(1800f, sea.apron));
                int n = LookGeom.Count(sea.pts);
                for (int i = 0; i < n; i++)
                {
                    int j = (i + 1) % n;
                    if (!HeightModel.OpenSeaVertex(look, i) || !HeightModel.OpenSeaVertex(look, j)) continue;
                    Vector2 a = Point(sea.pts, i), b = Point(sea.pts, j), c = Point(apron, j), d = Point(apron, i);
                    // Match MeshDraft.QuadFacing's diagonal as well as its footprint.
                    Vector2 ab = b - a, ac = c - a;
                    if (ab.x * ac.y - ab.y * ac.x > 0f) Quad(triangles, d, c, b, a);
                    else Quad(triangles, a, b, c, d);
                }
                water.Add(new WaterData.Area { Id = sea.id, Kind = WaterKind.Sea, SurfaceY = sea.level, Triangles = triangles.ToArray() });
            }
            // Look landmarks carry a ground/roof/world height in z; absent waterfall data creates no emitter.
            foreach (LookLandmark landmark in look.landmarks)
                if (string.Equals(landmark.type, "waterfall", StringComparison.OrdinalIgnoreCase))
                    sound.Add(new WaterData.Emitter { Position = new Vector3(landmark.x, landmark.z, landmark.y), SoundId = SfxIds.AmbWaterfall });
            areas = water.ToArray();
            emitters = sound.ToArray();
        }

        private static WaterKind Kind(string kind, string id)
        {
            // Polygon ponds/bogs/pools use the look schema's lake geometry, with their own id.
            if (id != null)
            {
                if (id.IndexOf("pond", StringComparison.OrdinalIgnoreCase) >= 0) return WaterKind.Pond;
                if (id.IndexOf("bog", StringComparison.OrdinalIgnoreCase) >= 0) return WaterKind.Bog;
                if (id.IndexOf("pool", StringComparison.OrdinalIgnoreCase) >= 0) return WaterKind.Pool;
            }
            if (Enum.TryParse(kind, true, out WaterKind result)) return result;
            throw new InvalidOperationException("Unknown built water kind: " + kind + " (" + id + ").");
        }

        private static float[] Ribbon(LookWater w)
        {
            if (LookGeom.Count(w.pts) < 2) return Array.Empty<float>();
            float[] line = LookGeom.Resample(w.pts, 2f, out _);
            int n = LookGeom.Count(line);
            float half = HeightModel.WaterHalfWidth(w);
            var triangles = new List<float>((n - 1) * 24);
            Vector2 left = default, centre = default, right = default;
            for (int i = 0; i < n; i++)
            {
                LookGeom.Normal(line, i, n, out float nx, out float nz, out float miter);
                float offset = half * Math.Min(miter, 1.6f);
                Vector2 nextCentre = Point(line, i);
                Vector2 nextLeft = nextCentre + new Vector2(nx * offset, nz * offset);
                Vector2 nextRight = nextCentre - new Vector2(nx * offset, nz * offset);
                if (i > 0)
                {
                    Quad(triangles, left, nextLeft, nextCentre, centre);
                    Quad(triangles, centre, nextCentre, nextRight, right);
                }
                left = nextLeft; centre = nextCentre; right = nextRight;
            }
            return triangles.ToArray();
        }

        private static Vector2 Point(float[] pts, int i) => new Vector2(pts[2 * i], pts[2 * i + 1]);
        private static void Quad(List<float> tris, Vector2 a, Vector2 b, Vector2 c, Vector2 d)
        {
            tris.Add(a.x); tris.Add(a.y); tris.Add(b.x); tris.Add(b.y); tris.Add(c.x); tris.Add(c.y);
            tris.Add(a.x); tris.Add(a.y); tris.Add(c.x); tris.Add(c.y); tris.Add(d.x); tris.Add(d.y);
        }

        private static void EmitAlong(float[] pts, bool closed, float y, string id, List<WaterData.Emitter> emitters)
        {
            int count = LookGeom.Count(pts);
            if (count < 2) return;
            float next = 0f;
            for (int i = 0; i < (closed ? count : count - 1); i++)
            {
                Vector2 a = Point(pts, i), b = Point(pts, (i + 1) % count);
                float length = (b - a).magnitude;
                while (next < length)
                {
                    Vector2 p = a + (b - a) * (next / length);
                    emitters.Add(new WaterData.Emitter { Position = new Vector3(p.x, y + 0.1f, p.y), SoundId = id });
                    next += 30f;
                }
                next -= length;
            }
        }
    }
}
