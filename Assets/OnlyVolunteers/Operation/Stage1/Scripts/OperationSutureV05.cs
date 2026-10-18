using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Round 3 (Fedya: "every operation ends with suturing the incision"): the approved OperationSutured_v05 meshes in
    /// the opening's INC_ABDOMEN frame (the same recipe as OperationOpeningV02: the meshes are authored in that frame).
    /// SUTURE_SKIN closes exactly the stencilled hole (the opening's ABDOMEN_MASK and the skin stencil stay on) with the
    /// patient's ORIGINAL skin material in its Buddy_Skin slot; SUTURE_STITCH_01..N appear in their 'order' as the seam
    /// progresses; SUTURE_BLOOD is the dried blood along the seam. A body that left the table dead and unsewn shows the plain
    /// patch with blood and no stitches (never a see-through cavity off the table).</summary>
    public sealed class OperationSutureV05 : MonoBehaviour
    {
        private readonly List<Material> owned = new();
        private readonly List<GameObject> stitches = new();
        private GameObject skin, blood;
        public int StitchCount => stitches.Count;
        public int StitchesShown { get; private set; }
        public bool Shown => gameObject.activeSelf;
        /// <summary>Round 4: the skin edges closing toward the line stitch by stitch (null: no readable mesh, the round-3 pop).</summary>
        private readonly List<Closer> closers = new();
        private float shownClosure = -1f, closureTarget = 1f;
        public float ShownClosure => shownClosure;
        public bool CanClose => closers.Count > 0;

        public static OperationSutureV05 Create(OperationTuning tuning, Transform zone, Material originalSkin)
        {
            if (tuning == null || tuning.suturedModel == null) return null;
            var root = new GameObject("Sutured v05"); root.transform.SetParent(zone, false);
            var result = root.AddComponent<OperationSutureV05>();
            var byOrder = new SortedDictionary<int, GameObject>();
            foreach (var source in tuning.suturedModel.GetComponentsInChildren<MeshFilter>(true))
            {
                string name = source.name;
                if (!name.StartsWith("SUTURE_") || name == "SUTURE_THREAD_ALL") continue; // per-stitch objects instead of the UV1 clip
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = source.sharedMesh;
                var renderer = go.AddComponent<MeshRenderer>();
                var originals = source.GetComponent<Renderer>().sharedMaterials;
                var materials = new Material[originals.Length];
                for (int i = 0; i < materials.Length; i++)
                {
                    string m = originals[i] != null ? originals[i].name : "";
                    if (m.StartsWith("Buddy_Skin") && originalSkin != null) { materials[i] = originalSkin; continue; }
                    Color color = m.Contains("Thread") ? new Color(0.12f, 0.15f, 0.34f) : m.Contains("DriedBlood") ? new Color(0.40f, 0.07f, 0.07f)
                        : m.Contains("Cut") ? new Color(0.50f, 0.12f, 0.12f) : m.Contains("Seam") ? new Color(0.90f, 0.52f, 0.47f) : new Color(0.88f, 0.56f, 0.40f);
                    materials[i] = new Material(OperationVisuals.Lit(m + " suture v05", color, m.Contains("Thread") ? 0.35f : 0.5f));
                    result.owned.Add(materials[i]);
                }
                renderer.sharedMaterials = materials;
                renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                if (name == "SUTURE_SKIN") result.skin = go;
                else if (name == "SUTURE_BLOOD") result.blood = go;
                if (name == "SUTURE_SKIN" || name == "SUTURE_BLOOD")
                {
                    var closer = Closer.Create(tuning, source.sharedMesh, go.GetComponent<MeshFilter>());
                    if (closer != null) result.closers.Add(closer);
                }
                else if (name.StartsWith("SUTURE_STITCH_") && int.TryParse(name.Substring("SUTURE_STITCH_".Length), out int order)) byOrder[order] = go;
            }
            foreach (var pair in byOrder) result.stitches.Add(pair.Value);
            root.SetActive(false);
            return result;
        }

        /// <summary>Patch on/off and the first 'stitchCount' stitches (in order); blood along the seam with the patch.</summary>
        public void Show(bool patch, int stitchCount)
        {
            if (gameObject.activeSelf != patch) gameObject.SetActive(patch);
            if (!patch) return;
            stitchCount = Mathf.Clamp(stitchCount, 0, stitches.Count);
            // Round 4: with the closing edges the stitches follow the shown (smoothed) closure, not the raw count.
            if (closers.Count > 0 && shownClosure >= 0f && stitches.Count > 0)
                stitchCount = Mathf.Min(stitchCount, Mathf.FloorToInt(shownClosure * stitches.Count + 0.001f));
            if (stitchCount == StitchesShown && skin != null && skin.activeSelf) return;
            for (int i = 0; i < stitches.Count; i++) if (stitches[i] != null) stitches[i].SetActive(i < stitchCount);
            if (skin != null) skin.SetActive(true);
            if (blood != null) blood.SetActive(true);
            StitchesShown = stitchCount;
        }

        /// <summary>Round 4: target closure 0..1 along the line (the seam progress, 1 when sewn or patched). The edges follow it
        /// smoothly (about one stitch per 0.12 s); instant jumps straight there (loading, leaving the table).</summary>
        public void SetClosure(float progress, bool instant = false)
        {
            closureTarget = Mathf.Clamp01(progress);
            if (!instant && shownClosure >= 0f) return; // Update follows the target
            shownClosure = closureTarget;
            Apply();
        }
        private void Update()
        {
            if (closers.Count == 0 || shownClosure < 0f || Mathf.Approximately(shownClosure, closureTarget)) return;
            float rate = Mathf.Max(1f, stitches.Count) * 0.12f;
            shownClosure = Mathf.MoveTowards(shownClosure, closureTarget, Time.deltaTime / rate * Mathf.Max(1f, Mathf.Abs(closureTarget - shownClosure) * 8f));
            Apply();
        }
        private void Apply() { foreach (var c in closers) c.Apply(shownClosure); }

        private void OnDestroy()
        {
            foreach (var m in owned) if (m != null) Destroy(m);
            foreach (var c in closers) if (c.mesh != null) Destroy(c.mesh);
        }

        /// <summary>Round 4: progress-driven closing of one seam mesh (SUTURE_SKIN, SUTURE_BLOOD) in the INC_ABDOMEN frame
        /// (= the zone frame: y toward the head, x across the line, z out of the belly). The triangles are split at the line
        /// into a left and a right flap. Ahead of the closing front each flap lies folded back onto its rim (the opening's
        /// edge at that height, measured from the mesh itself), so the cavity shows; behind the front it is at its authored
        /// place (exactly the round-3 sewn patch). Around the front the flap swings in with a small lift (the fold).</summary>
        private sealed class Closer
        {
            private const int Bins = 32;
            public Mesh mesh;
            private Vector3[] rest, work;
            private float[] along, side;
            private readonly float[] rim = new float[Bins];
            private float aMin, aMax, window;

            public static Closer Create(OperationTuning tuning, Mesh source, MeshFilter target)
            {
                Mesh readable = Readable(source, tuning);
                if (readable == null || target == null) return null;
                var c = new Closer();
                var vertices = readable.vertices;
                var normals = readable.normals;
                var tangents = readable.tangents;
                var uv = readable.uv; var uv2 = readable.uv2; var colors = readable.colors;
                int n = vertices.Length;
                var map = new Dictionary<long, int>();
                var pos = new List<Vector3>(); var nor = new List<Vector3>(); var tan = new List<Vector4>();
                var u0 = new List<Vector2>(); var u1 = new List<Vector2>(); var col = new List<Color>();
                var sides = new List<float>();
                var subs = new List<int>[readable.subMeshCount];
                for (int sm = 0; sm < readable.subMeshCount; sm++)
                {
                    var tris = readable.GetTriangles(sm);
                    subs[sm] = new List<int>(tris.Length);
                    for (int t = 0; t + 2 < tris.Length; t += 3)
                    {
                        float cx = (vertices[tris[t]].x + vertices[tris[t + 1]].x + vertices[tris[t + 2]].x) / 3f;
                        int s = cx < 0f ? -1 : 1;
                        for (int k = 0; k < 3; k++)
                        {
                            int v = tris[t + k];
                            long key = v * 2L + (s > 0 ? 1 : 0);
                            if (!map.TryGetValue(key, out int index))
                            {
                                index = pos.Count; map[key] = index;
                                pos.Add(vertices[v]); sides.Add(s);
                                if (normals != null && normals.Length == n) nor.Add(normals[v]);
                                if (tangents != null && tangents.Length == n) tan.Add(tangents[v]);
                                if (uv != null && uv.Length == n) u0.Add(uv[v]);
                                if (uv2 != null && uv2.Length == n) u1.Add(uv2[v]);
                                if (colors != null && colors.Length == n) col.Add(colors[v]);
                            }
                            subs[sm].Add(index);
                        }
                    }
                }
                var m = new Mesh { name = source.name + " closing v05" };
                if (pos.Count > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                m.SetVertices(pos);
                if (nor.Count == pos.Count) m.SetNormals(nor);
                if (tan.Count == pos.Count) m.SetTangents(tan);
                if (u0.Count == pos.Count) m.SetUVs(0, u0);
                if (u1.Count == pos.Count) m.SetUVs(1, u1);
                if (col.Count == pos.Count) m.SetColors(col);
                m.subMeshCount = subs.Length;
                for (int sm = 0; sm < subs.Length; sm++) m.SetTriangles(subs[sm], sm);
                m.RecalculateBounds();
                m.MarkDynamic();
                c.mesh = m; c.rest = pos.ToArray(); c.work = pos.ToArray(); c.side = sides.ToArray();
                c.along = new float[c.rest.Length];
                c.aMin = float.PositiveInfinity; c.aMax = float.NegativeInfinity;
                for (int i = 0; i < c.rest.Length; i++)
                {
                    float a = OperationAbdomenGeometry.Coordinates(tuning, OperationAbdomenGeometry.ZoneGuide, c.rest[i]).x;
                    c.along[i] = a; c.aMin = Mathf.Min(c.aMin, a); c.aMax = Mathf.Max(c.aMax, a);
                }
                if (!(c.aMax > c.aMin)) return null;
                for (int i = 0; i < c.rest.Length; i++)
                {
                    int b = c.Bin(c.along[i]);
                    c.rim[b] = Mathf.Max(c.rim[b], Mathf.Abs(c.rest[i].x));
                }
                // Empty bins borrow from their neighbours, so every height has a rim.
                for (int pass = 0; pass < Bins; pass++)
                    for (int b = 0; b < Bins; b++)
                        if (c.rim[b] <= 0f) c.rim[b] = Mathf.Max(b > 0 ? c.rim[b - 1] : 0f, b < Bins - 1 ? c.rim[b + 1] : 0f);
                c.window = Mathf.Max(0.04f, 1.5f / Mathf.Max(1, tuning.sutureStitches));
                target.sharedMesh = m;
                return c;
            }

            private int Bin(float a) => Mathf.Clamp(Mathf.FloorToInt((a - aMin) / (aMax - aMin) * Bins), 0, Bins - 1);

            /// <summary>0 = both flaps folded back (open), 1 = the authored sewn patch.</summary>
            public void Apply(float closure)
            {
                // The front sweeps the whole mesh (its ends lie a little beyond the line's 0..1) while the seam goes 0..1.
                float front = Mathf.Lerp(aMin - window, aMax + window, closure);
                for (int i = 0; i < rest.Length; i++)
                {
                    Vector3 p = rest[i];
                    float c = Mathf.Clamp01((front - along[i]) / window + 0.5f);
                    c = c * c * (3f - 2f * c);
                    if (c < 0.999f)
                    {
                        float edge = side[i] * rim[Bin(along[i])];
                        p.x = Mathf.Lerp(edge, p.x, c);
                        p.z += Mathf.Sin(c * Mathf.PI) * 0.006f;
                    }
                    work[i] = p;
                }
                mesh.vertices = work;
                mesh.RecalculateBounds();
            }

            /// <summary>The source itself when readable, else its readable copy baked by OperationQueryMeshBaker (same name
            /// + "_query", same vertex count). Null (no error): the seam then pops closed as in round 3.</summary>
            private static Mesh Readable(Mesh source, OperationTuning tuning)
            {
                if (source == null) return null;
                if (source.isReadable) return source;
                if (tuning.queryMeshes != null)
                    foreach (var copy in tuning.queryMeshes)
                        if (copy != null && copy.isReadable && copy.vertexCount == source.vertexCount && copy.subMeshCount == source.subMeshCount &&
                            (copy.name == source.name + OperationQueryMeshes.Suffix || copy.name.EndsWith("__" + source.name + OperationQueryMeshes.Suffix))) return copy;
                return null;
            }
        }
    }
}
