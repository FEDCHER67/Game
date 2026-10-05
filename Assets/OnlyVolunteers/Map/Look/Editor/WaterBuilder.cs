using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Water surfaces (no colliders; the van fords where the bed allows): lake plane at its level, river and canal
    // ribbons as wide as the carved channel at water level, concrete lining on the canal banks, the sea as its own
    // polygon plus an outward apron on open edges (never a global plane, which would show inside carved basins) and a
    // foam line along the surf. Also fills the sampler's water zones.
    public static class WaterBuilder
    {
        public static void Build(LookData d, HeightModel hm, MapLookRegistry registry, LookAssetStore store, Transform parent, MapHeightSampler sampler, List<string> log)
        {
            var root = new GameObject("Water").transform;
            root.SetParent(parent, false);
            foreach (LookWater w in d.water)
            {
                var draft = new MeshDraft();
                if (w.kind == "lake")
                {
                    draft.PlanTris(draft.Slot("mat/water/lake"), w.tris, (x, y) => w.level, 0f);
                    sampler.Water.Add(new WaterZone { Id = w.id, Kind = "lake", Level = w.level, Pts = w.pts });
                }
                else
                {
                    float half = HeightModel.WaterHalfWidth(w);
                    Ribbon(draft, draft.Slot(w.kind == "canal" ? "mat/water/canal" : "mat/water/river"), w.pts, half, (x, y) => w.level);
                    if (w.kind == "canal") CanalLining(draft, w, hm);
                    sampler.Water.Add(new WaterZone { Id = w.id, Kind = w.kind, Level = w.level, HalfWidth = half, Pts = w.pts });
                }
                Emit(root, $"Water_{w.id}", draft, registry, store);
            }
            Sea(d, root, registry, store, sampler);
            log.Add($"water: {d.water.Length} bodies + sea");
        }

        private static void Ribbon(MeshDraft draft, int slot, float[] pts, float half, System.Func<float, float, float> height)
        {
            if (LookGeom.Count(pts) < 2) return;
            float[] line = LookGeom.Resample(pts, 2f, out _);
            int n = LookGeom.Count(line);
            var rows = new List<Vector3[]>(n);
            for (int i = 0; i < n; i++)
            {
                LookGeom.Normal(line, i, n, out float nx, out float ny, out float miter);
                float x = line[2 * i], z = line[2 * i + 1], o = half * Mathf.Min(miter, 1.6f);
                rows.Add(new[]
                {
                    new Vector3(x + nx * o, height(x + nx * o, z + ny * o), z + ny * o),
                    new Vector3(x, height(x, z), z),
                    new Vector3(x - nx * o, height(x - nx * o, z - ny * o), z - ny * o),
                });
            }
            draft.Ribbon(slot, rows);
        }

        // Concrete banks: strips draped on the carved canal slopes on both sides.
        private static void CanalLining(MeshDraft draft, LookWater w, HeightModel hm)
        {
            HeightModel.Channel(w, out float top, out float bottom, out _);
            float[] line = LookGeom.Resample(w.pts, 2f, out _);
            int n = LookGeom.Count(line);
            int slot = draft.Slot("mat/concrete");
            for (int side = -1; side <= 1; side += 2)
            {
                var rows = new List<Vector3[]>(n);
                for (int i = 0; i < n; i++)
                {
                    LookGeom.Normal(line, i, n, out float nx, out float ny, out _);
                    float x = line[2 * i], z = line[2 * i + 1];
                    var row = new Vector3[3];
                    float[] offs = { bottom, (bottom + top) / 2f, top + 0.4f };
                    for (int k = 0; k < 3; k++)
                    {
                        float px = x + nx * offs[k] * side, pz = z + ny * offs[k] * side;
                        row[k] = new Vector3(px, hm.Height(px, pz) + 0.03f, pz);
                    }
                    rows.Add(row);
                }
                draft.Ribbon(slot, rows);
            }
        }

        private const float SeaHorizon = 1800f;

        private static void Sea(LookData d, Transform root, MapLookRegistry registry, LookAssetStore store, MapHeightSampler sampler)
        {
            LookSea sea = d.sea;
            if (LookGeom.Count(sea.pts) < 3) return;
            var draft = new MeshDraft();
            int slot = draft.Slot("mat/water/sea");
            draft.PlanTris(slot, sea.tris, (x, y) => sea.level, 0f);
            // Open edges reach far past the terrain edge (the terrain beyond them is sunk to the sea bed by HeightModel),
            // so from the beach and the hill the water runs into the haze instead of ending at a strip of land.
            float[] apron = LookGeom.OffsetPolygon(sea.pts, Mathf.Max(SeaHorizon, sea.apron));
            int n = LookGeom.Count(sea.pts);
            bool Open(int i) => HeightModel.OpenSeaVertex(d, i);
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                if (!Open(i) || !Open(j)) continue;
                var a = new Vector3(sea.pts[2 * i], sea.level, sea.pts[2 * i + 1]);
                var b = new Vector3(sea.pts[2 * j], sea.level, sea.pts[2 * j + 1]);
                var c = new Vector3(apron[2 * j], sea.level, apron[2 * j + 1]);
                var e = new Vector3(apron[2 * i], sea.level, apron[2 * i + 1]);
                draft.QuadFacing(slot, a, b, c, e, Vector3.up);
            }
            Emit(root, "Sea", draft, registry, store);
            sampler.Water.Add(new WaterZone { Id = sea.id, Kind = "sea", Level = sea.level, Pts = sea.pts });
            if (LookGeom.Count(d.beach.pts) >= 3) sampler.Water.Add(new WaterZone { Id = "BEACH_SURF", Kind = "sea", Level = sea.level, Pts = d.beach.pts });

            // Foam where the beach profile (-1.5 t^3) crosses the sea level.
            if (LookGeom.Count(d.beach.land) < 2 || LookGeom.Count(d.beach.sea) < 2) return;
            float t = Mathf.Pow(Mathf.Clamp01(-sea.level / 1.5f), 1f / 3f);
            float[] land = LookGeom.Resample(d.beach.land, 3f, out _);
            var foamLine = new List<float>();
            for (int i = 0; i < LookGeom.Count(land); i++)
            {
                float x = land[2 * i], y = land[2 * i + 1];
                LookGeom.DistToPolyline(d.beach.sea, x, y, false, out int seg, out float tt);
                float sx = Mathf.Lerp(d.beach.sea[2 * seg], d.beach.sea[2 * seg + 2], tt), sy = Mathf.Lerp(d.beach.sea[2 * seg + 1], d.beach.sea[2 * seg + 3], tt);
                foamLine.Add(Mathf.Lerp(x, sx, t));
                foamLine.Add(Mathf.Lerp(y, sy, t));
            }
            var foam = new MeshDraft();
            Ribbon(foam, foam.Slot("mat/water/foam"), foamLine.ToArray(), 0.7f, (x, y) => sea.level + 0.025f);
            Emit(root, "Sea_Foam", foam, registry, store);
        }

        private static void Emit(Transform root, string name, MeshDraft draft, MapLookRegistry registry, LookAssetStore store)
        {
            if (draft.IsEmpty) return;
            var go = new GameObject(name);
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = store.AddMesh(draft.ToMesh(name));
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterials = LookAssetStore.Materials(draft, registry);
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            DistrictCombiner.MarkStatic(go);
        }
    }
}
