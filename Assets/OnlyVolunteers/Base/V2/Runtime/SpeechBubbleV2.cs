using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.BaseV2
{
    /// <summary>
    /// A world-space speech bubble for base NPCs (V2 P1: the mechanic's greeting). A chunky 3D cartoon bubble (a rounded
    /// slab with bevelled edges and a tail toward the speaker; geometry, not a painted sprite) with the line in dark text on
    /// its face, above the speaker's head, turned to the camera about the vertical only, shown for a few seconds. Matte
    /// unlit cream material (readable in the dim hall, nothing to shimmer); the text is a TextMesh 5 mm in front of the
    /// face. Local only: every machine shows its own copy of the cue.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SpeechBubbleV2 : MonoBehaviour
    {
        public Material PanelMaterial;
        [Tooltip("Depth-tested text material (BubbleTextV2 shader); the font atlas is set at run time. Empty = the font's own (draws through walls).")]
        public Material TextMaterial;
        public Color TextColor = new Color(0.16f, 0.11f, 0.07f, 1f);
        [Tooltip("World height of one text line (m).")]
        public float LineHeight = 0.15f;
        public float Padding = 0.17f;
        public float Thickness = 0.05f;
        [Tooltip("Metres above the anchor (the speaker's feet).")]
        public float Above = 2.1f;
        [Tooltip("A longer line is broken in two at the space nearest its middle.")]
        public int WrapAt = 16;

        private Transform anchor;
        private Vector3 anchorOffset;
        private float until = -1f;
        private GameObject panel;
        private MeshFilter panelFilter;
        private TextMesh text;
        private MeshRenderer textRenderer;
        private Material textMat;
        private Mesh mesh;
        private int sizeFrames;
        private Vector2 estimate;

        /// <summary>Test / review shots: face this point instead of the main camera.</summary>
        public static Transform Viewer;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => Viewer = null;

        public bool Showing => until > Time.time && panel != null && panel.activeSelf;
        public string Line { get; private set; } = "";
        /// <summary>The panel's size once fitted to the text (tests).</summary>
        public Vector2 PanelSize { get; private set; }
        /// <summary>The text size the panel was fitted to (tests).</summary>
        public Vector2 TextSize { get; private set; }
        /// <summary>How far the generated text sat off the panel centre before it was moved back (tests).</summary>
        public Vector2 TextShift { get; private set; }

        private void Awake() => Build();

        private void OnDestroy()
        {
            Font.textureRebuilt -= OnFontRebuilt;
            if (textMat != null) Destroy(textMat);
        }

        private void Build()
        {
            if (panel != null) return;
            panel = new GameObject("Bubble panel");
            panel.transform.SetParent(transform, false);
            panelFilter = panel.AddComponent<MeshFilter>();
            var mr = panel.AddComponent<MeshRenderer>();
            mr.sharedMaterial = PanelMaterial;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
            mr.renderingLayerMask = 1u | (1u << 1) | (1u << 2);
            var tg = new GameObject("Bubble text");
            tg.transform.SetParent(panel.transform, false);
            text = tg.AddComponent<TextMesh>();
            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            text.font = font;
            textRenderer = tg.GetComponent<MeshRenderer>();
            if (TextMaterial != null)
            {
                textMat = new Material(TextMaterial) { mainTexture = font.material.mainTexture };
                textRenderer.sharedMaterial = textMat;
                Font.textureRebuilt += OnFontRebuilt;
            }
            else textRenderer.sharedMaterial = font.material;
            textRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            textRenderer.renderingLayerMask = 1u | (1u << 1) | (1u << 2);
            text.fontSize = 64;
            text.characterSize = LineHeight / 6.4f;
            text.anchor = TextAnchor.MiddleCenter;
            text.alignment = TextAlignment.Center;
            text.color = TextColor;
            panel.SetActive(false);
        }

        private void OnFontRebuilt(Font f)
        {
            if (textMat != null && text != null && f == text.font) textMat.mainTexture = f.material.mainTexture;
        }

        /// <summary>Shows 'line' above 'speaker' (its feet + Above) for 'seconds'.</summary>
        public void Say(string line, Transform speaker, float seconds, Vector3 offset = default)
        {
            Build();
            Line = line ?? "";
            anchor = speaker;
            anchorOffset = offset;
            text.text = Wrap(Line, WrapAt);
            text.transform.localPosition = new Vector3(0f, 0.02f, -Thickness * 0.5f - 0.006f);
            // a first panel from an estimate; LateUpdate fits it to the generated text once it exists
            string[] lines = text.text.Split('\n');
            int longest = 0;
            foreach (string l in lines) longest = Mathf.Max(longest, l.Length);
            estimate = new Vector2(longest * LineHeight * 0.6f, lines.Length * LineHeight * 1.2f);
            Fit(estimate.x, estimate.y);
            sizeFrames = 3;
            panel.SetActive(true);
            until = Time.time + Mathf.Max(0.5f, seconds);
            Place();
        }

        private void Fit(float textW, float textH)
        {
            float w = Mathf.Max(0.5f, textW + Padding * 2f), h = Mathf.Max(LineHeight + Padding * 2f, textH + Padding * 2f);
            PanelSize = new Vector2(w, h);
            mesh = BubbleMesh(w, h, Thickness, mesh);
            panelFilter.sharedMesh = mesh;
        }

        /// <summary>Breaks a long line in two at the space nearest its middle.</summary>
        public static string Wrap(string s, int at)
        {
            if (string.IsNullOrEmpty(s) || s.Length <= at || s.Contains("\n")) return s;
            int mid = s.Length / 2, best = -1;
            for (int i = 0; i < s.Length; i++)
                if (s[i] == ' ' && (best < 0 || Mathf.Abs(i - mid) < Mathf.Abs(best - mid))) best = i;
            return best < 0 ? s : s.Substring(0, best) + "\n" + s.Substring(best + 1);
        }

        public void Hide()
        {
            until = -1f;
            if (panel != null) panel.SetActive(false);
        }

        private void LateUpdate()
        {
            if (panel == null || !panel.activeSelf) return;
            if (Time.time > until) { panel.SetActive(false); return; }
            if (sizeFrames > 0)
            {
                sizeFrames--;
                // the generated glyph quads: a thin plane turned about the vertical, so its width is the AABB's x/z diagonal
                Bounds wb = textRenderer.bounds;
                float tw = Mathf.Sqrt(wb.size.x * wb.size.x + wb.size.z * wb.size.z), th = wb.size.y;
                if (tw > 0.05f && th > 0.02f)
                {
                    TextSize = new Vector2(tw, th);
                    Fit(Mathf.Max(tw, estimate.x * 0.8f), Mathf.Max(th, estimate.y * 0.8f));
                    // centre the generated glyphs on the panel (the dynamic font's layout can sit off its anchor)
                    Vector3 off = wb.center - text.transform.position;
                    TextShift = new Vector2(Vector3.Dot(off, panel.transform.right), off.y);
                    text.transform.localPosition -= new Vector3(TextShift.x, TextShift.y, 0f);
                    sizeFrames = 0;
                }
            }
            Place();
        }

        private void Place()
        {
            Vector3 at = (anchor != null ? anchor.position : transform.position) + anchorOffset + Vector3.up * Above;
            panel.transform.position = at;
            Camera cam = Camera.main;
            if (cam == null && Viewer == null) return;
            Vector3 away = at - (Viewer != null ? Viewer.position : cam.transform.position);
            away.y = 0f;
            if (away.sqrMagnitude > 1e-4f) panel.transform.rotation = Quaternion.LookRotation(away.normalized, Vector3.up);
        }

        /// <summary>The bubble slab: a rounded rectangle w x h (centre at the origin, the face toward -Z), t thick, its
        /// edges bevelled 30 % of the thickness, and a tail under the lower-left third pointing down to the speaker.</summary>
        public static Mesh BubbleMesh(float w, float h, float t, Mesh reuse = null)
        {
            var v = new List<Vector3>();
            var n = new List<Vector3>();
            var tri = new List<int>();
            float r = Mathf.Min(h * 0.45f, 0.14f), b = t * 0.3f, hz = t * 0.5f;
            const int seg = 6;
            List<Vector2> Ring(float inset)
            {
                var pts = new List<Vector2>();
                float hw = w * 0.5f - inset, hh = h * 0.5f - inset, rr = Mathf.Max(0.01f, r - inset);
                Vector2[] centres = { new(hw - rr, hh - rr), new(-hw + rr, hh - rr), new(-hw + rr, -hh + rr), new(hw - rr, -hh + rr) };
                for (int c = 0; c < 4; c++)
                    for (int i = 0; i <= seg; i++)
                    {
                        float a = (c * 90f + i * 90f / seg) * Mathf.Deg2Rad;
                        pts.Add(centres[c] + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * rr);
                    }
                return pts;
            }
            List<Vector2> outer = Ring(0f), inner = Ring(b);
            int N = outer.Count;
            void Cap(List<Vector2> ring, float z, Vector3 normal)
            {
                int c0 = v.Count;
                v.Add(new Vector3(0f, 0f, z)); n.Add(normal);
                for (int i = 0; i < N; i++) { v.Add(new Vector3(ring[i].x, ring[i].y, z)); n.Add(normal); }
                for (int i = 0; i < N; i++)
                {
                    int a = c0 + 1 + i, d = c0 + 1 + (i + 1) % N;
                    if (normal.z < 0f) { tri.Add(c0); tri.Add(d); tri.Add(a); } else { tri.Add(c0); tri.Add(a); tri.Add(d); }
                }
            }
            void Band(List<Vector2> r0, float z0, List<Vector2> r1, float z1)
            {
                for (int i = 0; i < N; i++)
                {
                    int j = (i + 1) % N;
                    Vector3 p0 = new(r0[i].x, r0[i].y, z0), p1 = new(r0[j].x, r0[j].y, z0), p2 = new(r1[j].x, r1[j].y, z1), p3 = new(r1[i].x, r1[i].y, z1);
                    Vector3 nn = Vector3.Cross(p1 - p0, p3 - p0).normalized;
                    Vector2 mid = (r0[i] + r0[j]) * 0.5f;
                    if (Vector3.Dot(nn, new Vector3(mid.x, mid.y, (z0 + z1) * 0.5f)) < 0f) nn = -nn;
                    int k = v.Count;
                    v.Add(p0); v.Add(p1); v.Add(p2); v.Add(p3);
                    for (int q = 0; q < 4; q++) n.Add(nn);
                    if (Vector3.Dot(Vector3.Cross(p1 - p0, p2 - p0), nn) > 0f) { tri.Add(k); tri.Add(k + 1); tri.Add(k + 2); tri.Add(k); tri.Add(k + 2); tri.Add(k + 3); }
                    else { tri.Add(k); tri.Add(k + 2); tri.Add(k + 1); tri.Add(k); tri.Add(k + 3); tri.Add(k + 2); }
                }
            }
            Cap(inner, -hz, Vector3.back);
            Band(inner, -hz, outer, -hz + b);
            Band(outer, -hz + b, outer, hz - b);
            Band(outer, hz - b, inner, hz);
            Cap(inner, hz, Vector3.forward);
            // the tail: a wedge from the bottom edge down toward the speaker
            float tx = -w * 0.18f, ty = -h * 0.5f + 0.01f, tw = Mathf.Min(0.16f, w * 0.2f), tl = 0.22f, th = t * 0.6f;
            Vector3[] f = { new(tx - tw * 0.5f, ty, -th * 0.5f), new(tx + tw * 0.5f, ty, -th * 0.5f), new(tx - tw * 0.15f, ty - tl, -th * 0.5f) };
            Vector3[] k3 = { f[0] + Vector3.forward * th, f[1] + Vector3.forward * th, f[2] + Vector3.forward * th };
            void Tri(Vector3 a, Vector3 c, Vector3 d)
            {
                Vector3 nn = Vector3.Cross(c - a, d - a).normalized;
                int k = v.Count;
                v.Add(a); v.Add(c); v.Add(d);
                n.Add(nn); n.Add(nn); n.Add(nn);
                tri.Add(k); tri.Add(k + 1); tri.Add(k + 2);
            }
            void Quad(Vector3 a, Vector3 c, Vector3 d, Vector3 e) { Tri(a, c, d); Tri(a, d, e); }
            Tri(f[0], f[1], f[2]);          // front (toward -Z): wound so the normal faces -Z
            Tri(k3[0], k3[2], k3[1]);       // back
            Quad(f[1], k3[1], k3[2], f[2]); // right slope
            Quad(f[2], k3[2], k3[0], f[0]); // left slope
            Mesh m = reuse != null ? reuse : new Mesh { name = "SpeechBubbleV2" };
            m.Clear();
            m.SetVertices(v);
            m.SetNormals(n);
            m.SetTriangles(tri, 0);
            m.RecalculateBounds();
            return m;
        }
    }
}
