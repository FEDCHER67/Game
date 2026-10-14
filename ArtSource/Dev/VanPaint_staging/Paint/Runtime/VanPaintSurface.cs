using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Vehicles.Paint
{
    public sealed class VanPaintSurface : MonoBehaviour
    {
        [SerializeField] string vanId = "grandpa-test-van-g20";
        [SerializeField] int resolution = 1024;
        [SerializeField] Shader brushShader;
        [SerializeField] Renderer[] paintRenderers;
        [SerializeField] Vector3 atlasWorldSize = new(2, 2, 4.8f);
        readonly List<PaintStroke> strokes = new();
        readonly List<Vector3> vertices = new();
        readonly List<Vector2> uvs = new();
        readonly List<Vector4> clips = new();
        readonly List<Color> colors = new();
        readonly List<int> triangles = new();
        RenderTexture mask;
        Material brush;
        Mesh mesh;
        CommandBuffer commands;
        PaintStroke pending;
        int totalDabs;
        public RenderTexture Mask => mask;
        public string VanId => vanId;
        public int StrokeCount => strokes.Count;
        public string Status { get; private set; } = "Clean body";
        public event Action<PaintStroke> StrokeCommitted;
        public event Action<string> HistoryChanged;

        public void Configure(Shader shader, Renderer[] renderers, Vector3 worldSize)
        { brushShader = shader; paintRenderers = renderers; atlasWorldSize = worldSize; }

        void Awake()
        {
            mask = new RenderTexture(resolution, resolution, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear)
            { name = "VanPaint_" + vanId, wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            mask.Create();
            brush = new Material(brushShader);
            brush.SetMatrix("_PaintMatrix", GL.GetGPUProjectionMatrix(Matrix4x4.Ortho(0, 1, 0, 1, -1, 1), true));
            mesh = new Mesh { name = "VanPaint brush batch", indexFormat = IndexFormat.UInt32 };
            mesh.MarkDynamic();
            commands = new CommandBuffer { name = "VanPaint UV dabs" };
            ClearMask();
            foreach (var r in paintRenderers)
            {
                var block = new MaterialPropertyBlock();
                r.GetPropertyBlock(block); block.SetTexture("_PaintMask", mask); block.SetFloat("_PaintEnabled", 1); r.SetPropertyBlock(block);
            }
            LoadPaint();
        }

        public Rect Island(Vector2 uv)
        {
            int x = Mathf.Clamp((int)(uv.x * 3), 0, 2), y = Mathf.Clamp((int)(uv.y * 2), 0, 1);
            return new Rect(x / 3f + .012f, y / 2f + .012f, 1 / 3f - .024f, .5f - .024f);
        }

        public Vector2 UvPerMetre(Vector2 uv)
        {
            int face = Mathf.Clamp((int)(uv.y * 2), 0, 1) * 3 + Mathf.Clamp((int)(uv.x * 3), 0, 2);
            Vector2 size = face < 2 ? new Vector2(atlasWorldSize.z, atlasWorldSize.y) :
                face < 4 ? new Vector2(atlasWorldSize.x, atlasWorldSize.z) : new Vector2(atlasWorldSize.x, atlasWorldSize.y);
            Rect rect = Island(uv);
            return new Vector2(rect.width / size.x, rect.height / size.y);
        }

        public bool BeginStroke(Color color, string text = null)
        {
            EndStroke();
            if (strokes.Count >= 256 || totalDabs >= 100000) { Status = "Paint limit reached. Wipe to start a new design."; return false; }
            pending = new PaintStroke { color = color, text = text }; return true;
        }

        public bool AddDabs(IReadOnlyList<PaintDab> dabs)
        {
            if (pending == null || pending.dabs.Count + dabs.Count > 8192 || totalDabs + dabs.Count > 100000) return false;
            foreach (var dab in dabs) { pending.dabs.Add(dab); totalDabs++; }
            Draw(dabs, pending.color); return true;
        }

        public void EndStroke()
        {
            if (pending == null) return;
            var done = pending; pending = null;
            if (done.dabs.Count == 0) return;
            strokes.Add(done); Status = "Paint applied";
            // Send a copy: subscribers/transport must not mutate the local undo journal.
            StrokeCommitted?.Invoke(JsonUtility.FromJson<PaintStroke>(JsonUtility.ToJson(done)));
        }

        public bool ApplyStroke(PaintStroke stroke)
        {
            int committedCount = strokes.Count + (pending != null && pending.dabs.Count > 0 ? 1 : 0);
            if (!Valid(stroke) || strokes.Exists(s => s.id == stroke.id) || pending?.id == stroke.id ||
                committedCount >= 256 || totalDabs + stroke.dabs.Count > 100000) return false;
            EndStroke();
            var copy = JsonUtility.FromJson<PaintStroke>(JsonUtility.ToJson(stroke));
            strokes.Add(copy); totalDabs += copy.dabs.Count; Draw(copy.dabs, copy.color); return true;
        }

        public static bool Valid(PaintStroke s)
        {
            bool Finite(float f) => !float.IsNaN(f) && !float.IsInfinity(f);
            if (s == null || string.IsNullOrEmpty(s.id) || s.dabs == null || s.dabs.Count == 0 || s.dabs.Count > 8192 ||
                !Finite(s.color.r) || !Finite(s.color.g) || !Finite(s.color.b) || !Finite(s.color.a) ||
                s.color.r < 0 || s.color.r > 1 || s.color.g < 0 || s.color.g > 1 || s.color.b < 0 || s.color.b > 1 || s.color.a < 0 || s.color.a > 1) return false;
            foreach (var d in s.dabs)
                if (!Finite(d.uv.x) || !Finite(d.uv.y) || !Finite(d.radius.x) || !Finite(d.radius.y) ||
                    !Finite(d.clip.x) || !Finite(d.clip.y) || !Finite(d.clip.width) || !Finite(d.clip.height) ||
                    d.uv.x < 0 || d.uv.x > 1 || d.uv.y < 0 || d.uv.y > 1 ||
                    d.radius.x <= 0 || d.radius.y <= 0 || d.radius.x > .25f || d.radius.y > .25f ||
                    d.clip.xMin < 0 || d.clip.yMin < 0 || d.clip.xMax > 1 || d.clip.yMax > 1 || d.clip.width <= 0 || d.clip.height <= 0) return false;
            return true;
        }

        public void UndoStroke()
        {
            EndStroke(); if (strokes.Count == 0) { Status = "Nothing to undo"; return; }
            totalDabs -= strokes[^1].dabs.Count; strokes.RemoveAt(strokes.Count - 1);
            ClearMask(); foreach (var s in strokes) Draw(s.dabs, s.color);
            Status = "Last stroke undone"; HistoryChanged?.Invoke("undo");
        }

        public void Wipe()
        {
            pending = null; strokes.Clear(); totalDabs = 0; ClearMask();
            Status = "Body wiped. J saves this clean state."; HistoryChanged?.Invoke("wipe");
        }

        void ClearMask()
        {
            var previous = RenderTexture.active;
            try { RenderTexture.active = mask; GL.Clear(false, true, Color.clear); }
            finally { RenderTexture.active = previous; }
        }

        void Draw(IReadOnlyList<PaintDab> dabs, Color color)
        {
            vertices.Clear(); uvs.Clear(); colors.Clear(); clips.Clear(); triangles.Clear();
            foreach (var d in dabs)
            {
                int n = vertices.Count;
                for (int i = 0; i < 4; i++)
                {
                    Vector2 corner = new(i == 1 || i == 2 ? 1 : 0, i >= 2 ? 1 : 0);
                    vertices.Add(d.uv + Vector2.Scale(corner * 2 - Vector2.one, d.radius));
                    uvs.Add(corner); colors.Add(color.linear);
                    clips.Add(new Vector4(d.clip.xMin, d.clip.yMin, d.clip.xMax, d.clip.yMax));
                }
                triangles.Add(n); triangles.Add(n + 1); triangles.Add(n + 2);
                triangles.Add(n); triangles.Add(n + 2); triangles.Add(n + 3);
            }
            mesh.Clear(); mesh.SetVertices(vertices); mesh.SetUVs(0, uvs); mesh.SetUVs(1, clips);
            mesh.SetColors(colors); mesh.SetTriangles(triangles, 0);
            commands.Clear(); commands.SetRenderTarget(mask); commands.DrawMesh(mesh, Matrix4x4.identity, brush);
            var previous = RenderTexture.active;
            try { Graphics.ExecuteCommandBuffer(commands); }
            finally { RenderTexture.active = previous; }
        }

        public byte[] SnapshotPng()
        {
            var previous = RenderTexture.active;
            var tex = new Texture2D(resolution, resolution, TextureFormat.RGBA32, false, true);
            try { RenderTexture.active = mask; tex.ReadPixels(new Rect(0, 0, resolution, resolution), 0, 0); tex.Apply(); return tex.EncodeToPNG(); }
            finally { RenderTexture.active = previous; Destroy(tex); }
        }

        public bool SavePaint()
        {
            EndStroke();
            try
            {
                var data = new VanPaintSave { vanId = vanId, resolution = resolution, strokes = new List<PaintStroke>(strokes) };
                string file = VanPaintStorage.Save(data, SnapshotPng());
                Status = "Saved " + strokes.Count + " strokes"; Debug.Log("[VanPaint] Saved " + file); return true;
            }
            catch (Exception e) { Status = "Save failed: " + e.Message; Debug.LogWarning("[VanPaint] " + Status); return false; }
        }

        public bool LoadPaint()
        {
            Texture2D tex = null;
            try
            {
                if (!VanPaintStorage.Load(vanId, resolution, out var data, out var png)) return false;
                tex = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
                if (!tex.LoadImage(png) || tex.width != resolution || tex.height != resolution) throw new InvalidOperationException("Wrong PNG dimensions.");
                var previous = RenderTexture.active;
                try { Graphics.Blit(tex, mask); } finally { RenderTexture.active = previous; }
                pending = null; strokes.Clear(); strokes.AddRange(data.strokes);
                totalDabs = 0; foreach (var s in strokes) totalDabs += s.dabs.Count;
                Status = "Loaded " + strokes.Count + " strokes"; HistoryChanged?.Invoke("load"); return true;
            }
            catch (Exception e) { Status = "Load failed: " + e.Message; Debug.LogWarning("[VanPaint] " + Status); return false; }
            finally { if (tex != null) Destroy(tex); }
        }

        void OnDestroy()
        {
            commands?.Dispose();
            if (mask != null) { mask.Release(); Destroy(mask); }
            if (brush != null) Destroy(brush);
            if (mesh != null) Destroy(mesh);
        }
    }
}
