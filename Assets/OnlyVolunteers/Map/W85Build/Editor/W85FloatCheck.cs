using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Map.W85
{
    // Fedya 21.10 (Hamlet near base 2: roofs in the air): every roof / canopy / awning / porch / shelter piece of the map must hang on a
    // wall of its building or stand on supports that reach the ground. Check over the whole scene (map build + play scene):
    //  - pieces of a generated building (B_*: kit porch roofs, entrance canopies, storefront awnings): attached when the box around
    //    the piece, grown by 0.3 m, touches a collider of that building;
    //  - free pieces (shelters, sheds, canopies carried from i10, samples, prefabs): each of the 4 corners of the piece's underside
    //    (inset 0.3 m) must be supported — a collider straight below it, a collider within 0.35 m (a wall), or a renderer under it that
    //    reaches the ground (a post without collider); >= 3 of 4 = ok;
    //  - any raised piece taller than 1.5 m (porch roof / shelter with its own posts) must stand on the ground, attached or not;
    //  - generated building roofs stand on their walls by construction (roof collision test) and are skipped.
    // Fix: a post under every unsupported corner, ground to underside — a copy of the piece's own post when its group has one
    // (same style), else the pilot-kit POST_v01 stretched.
    public static class W85FloatCheck
    {
        const string PostPrefab = "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v01/Prefabs/POST_v01.prefab";
        static readonly string[] Words = { "roof", "canopy", "awning", "porch", "shelter", "shed", "naves" };

        // G46: a tilted cliff rock's pivot is not its support. Test the actual mesh against the map terrain.
        // Only unattached rocks move, by the smallest vertical displacement that embeds a real vertex by 15 cm.
        public static bool SeatRock(Transform rock)
        {
            float gap = float.PositiveInfinity;
            foreach (var mf in rock.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!mf.sharedMesh) continue;
                foreach (var v in mf.sharedMesh.vertices)
                {
                    Vector3 p = mf.transform.TransformPoint(v);
                    gap = Mathf.Min(gap, p.y - Ground(p));
                }
            }
            if (float.IsInfinity(gap) || gap <= .05f) return false;
            rock.position += Vector3.down * (gap + .15f);
            return true;
        }

        public static string Run(Scene scene, bool fix)
        {
            Physics.SyncTransforms();
            var sb = new StringBuilder();
            int checkedN = 0, floaters = 0, fixedN = 0;
            var renderers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Renderer>()).Where(r => r.enabled && !(r is ParticleSystemRenderer)).ToList();
            var candidates = new List<Transform>();
            foreach (var r in renderers)
            {
                string n = r.name.ToLowerInvariant();
                if (!Words.Any(w => n.Contains(w))) continue;
                if (n.Contains("vent") || n.Contains("roof_flat") || n.Contains("tank") || n.Contains("rooftop") || n.Contains("chimney")) continue;   // pieces ON a roof
                if (Building(r.transform) != null && (n == "roof" || n == "gables" || n == "parapet")) continue;   // generated roofs stand on their walls
                var piece = KitPiece(r.transform) ?? r.transform;
                if (!candidates.Contains(piece)) candidates.Add(piece);
            }
            foreach (var piece in candidates)
            {
                var rs = piece.GetComponentsInChildren<Renderer>().Where(x => x.enabled).ToArray();
                if (rs.Length == 0) continue;
                var bb = rs[0].bounds; foreach (var x in rs) bb.Encapsulate(x.bounds);
                float ground = Ground(bb.center);
                if (bb.min.y - ground < .6f) continue;                                   // reaches the ground itself
                checkedN++;
                var host = Building(piece);
                bool ok;
                var missing = new List<Vector3>();
                if (bb.size.y > 1.5f && bb.max.y - ground < 6f)
                {   // a piece with its own posts / legs (porch roof on posts, shelter) hangs in the air even when its back touches a wall
                    // (the Hamlet kit porch roofs were 2.3 m up): it must stand on the ground -> fix = put it down
                    floaters++;
                    sb.AppendLine($"  hanging {Path(piece)} at ({bb.center.x:0.0}, {bb.center.z:0.0}): {bb.size.y:0.0} m tall piece, its feet {bb.min.y - ground:0.0} m above the ground");
                    if (fix) { piece.position += Vector3.down * (bb.min.y - ground); fixedN++; sb.AppendLine("    -> put down onto the ground"); }
                    continue;
                }
                if (host != null)
                {
                    var hostCols = new HashSet<Collider>(host.GetComponentsInChildren<Collider>());
                    var hits = Physics.OverlapBox(bb.center, bb.extents + Vector3.one * .3f, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore);
                    ok = hits.Any(h => hostCols.Contains(h));
                    if (!ok) missing.AddRange(Corners(bb));
                }
                else
                {
                    int sup = 0;
                    foreach (var c in Corners(bb))
                        if (Supported(c, piece, renderers)) sup++; else missing.Add(c);
                    ok = sup >= 3;
                }
                if (ok) continue;
                floaters++;
                sb.AppendLine($"  floater {Path(piece)} at ({bb.center.x:0.0}, {bb.center.z:0.0}) underside {bb.min.y - ground:0.0} m above ground, host {(host ? host.name : "none")}, unsupported corners {missing.Count}");
                if (!fix) continue;
                foreach (var c in missing)
                {
                    float g = Ground(c), h = c.y - g;
                    if (h < .3f) continue;
                    var post = MakePost(piece, h);
                    if (post == null) continue;
                    // stretch to the gap, stand on the ground under the corner
                    var pb = Bounds(post);
                    var s = post.transform.localScale;
                    post.transform.localScale = new Vector3(s.x, s.y * h / Mathf.Max(.05f, pb.size.y), s.z);
                    pb = Bounds(post);
                    post.transform.position += new Vector3(c.x - pb.center.x, g - pb.min.y, c.z - pb.center.z);
                    post.name = "Support_post_W85";
                    if (!post.GetComponentInChildren<Collider>()) post.AddComponent<BoxCollider>();
                    foreach (var t in post.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic);
                    fixedN++;
                }
                sb.AppendLine($"    -> {missing.Count} support post(s) added");
            }
            sb.Insert(0, $"floating check: {checkedN} raised roof / canopy / awning / porch / shelter pieces, {floaters} floaters" + (fix ? $", {fixedN} fixes (support posts / put down)" : "") + "\n");
            return sb.ToString();
        }

        // A post in the style of the piece: its group's own post (a renderer named *post* / *pillar* standing on the ground), else the kit post.
        static GameObject MakePost(Transform piece, float h)
        {
            var holder = Holder(piece);
            var group = piece.root;
            var own = group.GetComponentsInChildren<Renderer>().Where(r => r.enabled && !r.transform.IsChildOf(piece) && r.name != "Support_post_W85"
                    && (r.name.ToLowerInvariant().Contains("post") || r.name.ToLowerInvariant().Contains("pillar"))
                    && r.bounds.size.y > 1f && r.bounds.size.x < .6f && r.bounds.size.z < .6f && r.bounds.min.y - Ground(r.bounds.center) < .3f)
                .OrderBy(r => (r.bounds.center - piece.position).sqrMagnitude).FirstOrDefault();
            GameObject post;
            if (own != null)
            {
                post = Object.Instantiate(own.gameObject, holder);
                foreach (Transform ch in post.transform.Cast<Transform>().ToList()) Object.DestroyImmediate(ch.gameObject);
                post.transform.SetPositionAndRotation(own.transform.position, own.transform.rotation);
                post.transform.localScale = own.transform.localScale;
                if (own.transform.parent != holder)
                {   // carry the world scale of the original
                    var ws = own.transform.lossyScale; var hs = holder.lossyScale;
                    post.transform.localScale = new Vector3(ws.x / hs.x, ws.y / hs.y, ws.z / hs.z);
                }
            }
            else
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PostPrefab);
                if (prefab == null) return null;
                post = (GameObject)PrefabUtility.InstantiatePrefab(prefab, holder);
                post.transform.rotation = Quaternion.identity;
                var hs = holder.lossyScale;
                post.transform.localScale = new Vector3(1f / hs.x, 1f / hs.y, 1f / hs.z);
            }
            return post;
        }

        // the nearest ancestor with a unit world scale (posts must not inherit the scale of a stretched roof cube)
        static Transform Holder(Transform piece)
        {
            for (var t = piece.parent; t != null; t = t.parent)
                if ((t.lossyScale - Vector3.one).sqrMagnitude < 1e-4f) return t;
            return piece.root;
        }

        static Bounds Bounds(GameObject g)
        {
            var rs = g.GetComponentsInChildren<Renderer>();
            if (rs.Length == 0) return new Bounds(g.transform.position, Vector3.one * .1f);
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            return b;
        }

        static IEnumerable<Vector3> Corners(Bounds b)
        {
            float ix = Mathf.Min(.3f, b.extents.x * .5f), iz = Mathf.Min(.3f, b.extents.z * .5f), y = b.min.y;
            yield return new Vector3(b.min.x + ix, y, b.min.z + iz); yield return new Vector3(b.max.x - ix, y, b.min.z + iz);
            yield return new Vector3(b.max.x - ix, y, b.max.z - iz); yield return new Vector3(b.min.x + ix, y, b.max.z - iz);
        }

        static bool Supported(Vector3 c, Transform self, List<Renderer> renderers)
        {
            float ground = Ground(c), gap = Mathf.Max(.1f, c.y - ground);
            // a collider straight below in the gap (posts, walls, fences, a table under a lamp shade...)
            foreach (var h in Physics.RaycastAll(c + Vector3.down * .02f, Vector3.down, gap + .2f, ~0, QueryTriggerInteraction.Ignore))
                if (!h.collider.transform.IsChildOf(self) && !(h.collider is TerrainCollider)) return true;
            // a wall within 0.35 m of the underside
            foreach (var h in Physics.OverlapSphere(c + Vector3.down * .3f, .35f, ~0, QueryTriggerInteraction.Ignore))
                if (!h.transform.IsChildOf(self) && !(h is TerrainCollider)) return true;
            // a renderer under the corner that reaches the ground (a post without a collider)
            var col = new Bounds(new Vector3(c.x, ground + gap / 2, c.z), new Vector3(.6f, gap, .6f));
            foreach (var r in renderers)
            {
                if (r.transform.IsChildOf(self)) continue;
                var rb = r.bounds;
                if (rb.min.y - Ground(rb.center) < .5f && rb.Intersects(col) && rb.max.y > c.y - .3f && rb.size.x < 40 && rb.size.z < 40) return true;
            }
            return false;
        }

        // W86: the map has a second, collider-less terrain (steppe backdrop) - the ground is the terrain with a collider under the point
        static float Ground(Vector3 p)
        {
            Terrain best = null;
            foreach (var t in Terrain.activeTerrains)
            {
                if (!t || !t.GetComponent<TerrainCollider>()) continue;
                Vector3 o = t.transform.position, s = t.terrainData.size;
                bool inside = p.x >= o.x && p.z >= o.z && p.x <= o.x + s.x && p.z <= o.z + s.z;
                if (inside || best == null) best = t;
                if (inside) break;
            }
            if (!best) best = Terrain.activeTerrain;
            return best ? best.SampleHeight(p) + best.transform.position.y : 0f;
        }

        static Transform Building(Transform t)
        {
            for (var x = t; x != null; x = x.parent) if (x.name.StartsWith("B_")) return x;
            return null;
        }

        static Transform KitPiece(Transform t)
        {
            for (var x = t; x != null; x = x.parent) if (x.name.StartsWith("FK_") && !x.name.EndsWith("_Mesh") && !x.name.StartsWith("UCX_")) return x;
            return null;
        }

        static string Path(Transform t) => t.parent == null ? t.name : Path(t.parent) + "/" + t.name;
    }
}
