using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // W86 VIEW B viewpoint (lead 22.10, data v02 rerun): the view_b_spur road ends in a 22 x 17 m pocket at 46 m on the hill B summit
    // (roads_v85.json road.pocket, also features_v85.json view_B_pocket). Gravel surface flush with the ground, a low stone parapet
    // (~0.8 m) with a continuous metal rail along the open (falling) rim - no gap, the van cannot drive off - two benches facing the
    // view, one lamp on the inner side; no text sign.
    public static partial class W85Builder
    {
        static void ViewPocket(Transform root)
        {
            if (!IsV2) return;
            Dictionary<string, object> pocket = null; Vector2[] road = null; float roadW = 5f; string id = "view_B";
            foreach (var r in Arr(Get(Obj(Json.Parse(File.ReadAllText(Data + "/roads_v85.json"))), "roads")).Select(Obj))
                if (Obj(Get(r, "pocket")) is Dictionary<string, object> pk) { pocket = pk; road = V2s(Get(r, "points")); roadW = F(Get(r, "width_m"), 5f); id = S(Get(r, "id"), id); break; }
            if (pocket == null) pocket = Obj(Get(Obj(Json.Parse(File.ReadAllText(Data + "/features_v85.json"))), "view_B_pocket"));
            var poly = V2s(Get(pocket, "poly"));
            if (poly.Length < 3) { Note("view pocket: none in the data"); return; }
            var parent = new GameObject("ViewPocket_" + id).transform; parent.SetParent(root, false);
            Vector2 c = V2(Get(pocket, "centre")); if (c == Vector2.zero) c = poly.Aggregate(Vector2.zero, (s, q) => s + q) / poly.Length;
            // gravel, flush with the ground (s03 levelled the pocket); UV in metres
            var gravel = GravelMat();
            var mesh = Fill("ViewPocket_" + id + "_gravel", poly, q => Height(q.x, q.y) + .035f, Vector2.zero);
            mesh.uv = mesh.vertices.Select(v => new Vector2(v.x, v.z) / 4f).ToArray();
            EditorUtility.SetDirty(mesh);
            MeshGo("Zone_" + id + "_pocket", parent, mesh, gravel, true);
            // open rim: the ground 3 m outside drops > 1 m below the pocket, away from the road end
            float level = Height(c.x, c.y);
            Vector2 roadEnd = road != null && road.Length > 0 ? road.OrderBy(q => (q - c).sqrMagnitude).First() : new Vector2(float.MaxValue, 0);
            var ring = Resample(poly.Append(poly[0]).ToArray(), .5f);
            // the side the data calls open ("open to the south / south-east") + wherever the ground falls away; never the road entry
            string view = (S(Get(pocket, "view")) ?? "").ToLowerInvariant();
            Vector2 open0 = Vector2.zero;
            if (view.Contains("south")) open0 += Vector2.down; if (view.Contains("north")) open0 += Vector2.up;
            if (view.Contains("east")) open0 += Vector2.right * .6f; if (view.Contains("west")) open0 += Vector2.left * .6f;
            if (open0 == Vector2.zero) open0 = Vector2.down;
            open0.Normalize();
            bool Open(Vector2 q)
            {
                Vector2 o = (q - c).normalized;
                if (road != null && W76Atmosphere.Distance(road, q) < roadW * .5f + 2.5f) return false;
                return Vector2.Dot(o, open0) > .25f || Height(q.x + o.x * 3f, q.y + o.y * 3f) < level - 1f || Height(q.x + o.x * 6f, q.y + o.y * 6f) < level - 2f;
            }
            var open = ring.Select(Open).ToList();
            // fill single-sample holes so the parapet run has no gap
            for (int i = 1; i + 1 < open.Count; i++) if (!open[i] && open[i - 1] && open[i + 1]) open[i] = true;
            var stone = new MB(); var rail = new MB(); Transform cols = null;
            int runs = 0, posts = 0; float len = 0f, sinceP = 99f; bool was = false;
            for (int i = 1; i < ring.Count; i++)
            {
                if (!(open[i - 1] && open[i])) { was = false; continue; }
                if (!was) runs++;
                was = true;
                Vector2 a = ring[i - 1], b = ring[i]; float L = (b - a).magnitude;
                if (L < .01f) continue;
                Vector2 d = (b - a) / L, inw = (c - (a + b) * .5f).normalized;
                Vector2 a2 = a + inw * .25f, b2 = b + inw * .25f;          // parapet 0.25 m inside the rim
                float ya = Height(a2.x, a2.y) - .2f, yb = Height(b2.x, b2.y) - .2f;
                WallSlab(stone, a2, b2, inw, .4f, ya, yb, ya + 1.0f, yb + 1.0f, len, Tile("cobble_SK2c"));
                // rail on short posts: continuous top tube 1.1 m over the pocket
                MBBox(rail, new Vector3((a2.x + b2.x) * .5f - inw.x * .2f, (ya + yb) * .5f + 1.32f, (a2.y + b2.y) * .5f - inw.y * .2f), new Vector3(L + .03f, .06f, .06f), -Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg);
                sinceP += L;
                if (sinceP >= 2f) { MBBox(rail, new Vector3(a2.x - inw.x * .2f, ya + 1.1f, a2.y - inw.y * .2f), new Vector3(.06f, .45f, .06f), 0f); sinceP = 0f; posts++; }
                if (!cols) { cols = new GameObject("parapet_colliders").transform; cols.SetParent(parent, false); }
                AddBox(cols, (a2 + b2) * .5f - inw * .2f, Mathf.Min(ya, yb), Mathf.Max(ya, yb) + 1.35f, L + .05f, .4f, -Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg);
                len += L;
            }
            if (stone.V.Count > 0) MeshGo("Parapet_" + id + "_stone", parent, stone.Build("ViewPocket_" + id + "_parapet"), Mat("cobble_SK2c"));
            if (rail.V.Count > 0) MeshGo("Parapet_" + id + "_rail", parent, rail.Build("ViewPocket_" + id + "_rail"), Mat("metal_painted_SK6a"));
            // benches facing the view (middle of the longest open run), lamp on the inner side
            var openPts = ring.Where((q, i) => open[i]).ToList();
            Vector2 viewDir = openPts.Count > 0 ? (openPts.Aggregate(Vector2.zero, (s, q) => s + q) / openPts.Count - c).normalized : Vector2.down;
            Vector2 side = new(-viewDir.y, viewDir.x);
            float reach = openPts.Count > 0 ? openPts.Min(q => (q - c).magnitude) : 7f;
            int benches = 0;
            foreach (int sg in new[] { -1, 1 })
            {
                Vector2 q = c + viewDir * Mathf.Max(2f, reach - 2.2f) + side * sg * 3.2f;
                var pf = Prefab("bench");
                if (!pf) continue;
                var g = (GameObject)PrefabUtility.InstantiatePrefab(pf, parent);
                g.name = id + "_bench" + (sg < 0 ? "A" : "B");
                g.transform.SetPositionAndRotation(P(q), Quaternion.LookRotation(new Vector3(viewDir.x, 0, viewDir.y)));   // bench_park: seat faces +Z (back rest at -Z)
                g.AddComponent<W76GripAnchor>();
                foreach (Transform t in g.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                benches++;
            }
            var lp = Prefab("lamp_oldtown_single") ?? Prefab("street_lamp");
            if (lp)
            {
                var g = (GameObject)PrefabUtility.InstantiatePrefab(lp, parent);
                g.name = id + "_lamp";
                Vector2 q = c - viewDir * Mathf.Max(2f, reach - 3f) + side * 2.5f;
                g.transform.SetPositionAndRotation(P(q), Quaternion.LookRotation(new Vector3(viewDir.x, 0, viewDir.y)));
                g.AddComponent<W76GripAnchor>();
            }
            // no terrain tree in the pocket (+2 m) or on the last 30 m of the spur
            int felled = 0;
            if (Ter)
            {
                var td = Ter.terrainData; var trees = td.treeInstances;
                var tail = road != null ? road.Where(q => (q - c).magnitude < 40f).ToArray() : new Vector2[0];
                var kept = trees.Where(ti =>
                {
                    var w = new Vector2(ti.position.x * td.size.x, ti.position.z * td.size.z);
                    bool inPocket = W76Atmosphere.Inside(poly, w) || W76Atmosphere.Distance(poly.Append(poly[0]).ToArray(), w) < 2f;
                    bool onTail = tail.Length >= 2 && W76Atmosphere.Distance(tail, w) < roadW * .5f + 2f;
                    return !(inPocket || onTail);
                }).ToArray();
                felled = trees.Length - kept.Length;
                if (felled > 0) { td.SetTreeInstances(kept, true); EditorUtility.SetDirty(td); }
            }
            Note($"view pocket {id}: {felled} terrain tree(s) removed from the pocket; gravel {poly.Length}-gon at {level:0.0} m, stone parapet + rail {len:0} m in {runs} run(s) on the open rim ({posts} posts), {benches} benches facing ({viewDir.x:0.0}, {viewDir.y:0.0}), lamp {(lp ? "on" : "missing")}, no sign");
        }

        static Material gravelMat;
        static Material GravelMat()
        {
            if (gravelMat && AssetDatabase.GetAssetPath(gravelMat).StartsWith(Gen)) return gravelMat;
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "W86_gravel_SK1d", enableInstancing = true };
            var tex = ImportTexture(S(Get(Obj(Get(MatMap, "L06_gravel_SK1d")), "texture")));
            if (tex) m.SetTexture("_BaseMap", tex);
            m.SetFloat("_Smoothness", .05f);
            Folder(Gen + "/Materials/W86");
            AssetDatabase.CreateAsset(m, Gen + "/Materials/W86/W86_gravel_SK1d.mat"); created++;
            return gravelMat = m;
        }
    }
}
