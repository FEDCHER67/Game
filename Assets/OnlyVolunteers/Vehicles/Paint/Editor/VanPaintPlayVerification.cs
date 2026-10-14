using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Vehicles.Paint.Editor
{
    // Explicit MCP-invoked checks. Nothing runs automatically on import or in map scenes.
    public static class VanPaintPlayVerification
    {
        const string Review = "Working/Reviews/VanPaint";
        static VanPaintInteractor Input => UnityEngine.Object.FindAnyObjectByType<VanPaintInteractor>();
        static VanPaintSurface Van => UnityEngine.Object.FindAnyObjectByType<VanPaintSurface>();
        static void RequirePlay()
        {
            VanPaintTestBuilder.RequireLock();
            if (!EditorApplication.isPlaying || SceneManager.GetActiveScene().path != VanPaintTestBuilder.ScenePath)
                throw new InvalidOperationException("G20 verification requires Play in VanPaint_Test only.");
        }
        static void Check(bool ok, string message) { if (!ok) throw new InvalidOperationException("[VanPaint CHECK FAILED] " + message); }
        static Ray SideRay(float y, float z) => new(new Vector3(-5, y, z), Vector3.right);
        static bool Pick(string name)
        {
            var prop = UnityEngine.Object.FindObjectsByType<VanPaintProp>().First(p => p.name == name);
            var collider = prop.GetComponentsInChildren<Collider>().First(c => c.enabled);
            Vector3 to = collider.bounds.center;
            // The same raycast/pickup command used by B; point from above to avoid the table.
            return Input.PickUp(new Ray(to + Vector3.up * 2, Vector3.down));
        }
        public static string Paint()
        {
            RequirePlay();
            Check(Van.StrokeCount == 0, "Fresh test identity must start without paint; existing player design was preserved.");
            Check(!Input.PaintAt(SideRay(1.03f,-.6f)) && !Input.OpenText(SideRay(1.56f,-.65f)), "Paint and text require held tools");
            Check(Pick("Grandpa's fence brush"), "Brush pickup");
            Check(Pick("Paint can Blue"), "Can pickup");
            Check(Input.HasTools, "Both held props");
            int hits = 0;
            for (int i = 0; i <= 70; i++)
            {
                float t = i / 70f;
                if (Input.PaintAt(SideRay(1.03f + Mathf.Sin(t * 6.28f) * .13f, -1.6f + t * 2.0f))) hits++;
            }
            Input.FinishStroke();
            Check(hits > 60 && Van.StrokeCount == 1, "Raycast UV stroke commits as one undo unit");
            Check(CountPaintPixels() > 100, "RenderTexture contains painted pixels");
            Check(AlphaAt(SideRay(1.03f, -.6f)) > .5f, "Paint mask lands at the ray's actual UV, without vertical flip");
            SessionState.SetString("G20.paintHash", VanPaintStorage.Hash(Van.SnapshotPng()));
            return "PASS: brush + blue can picked up through rays; " + hits + " mesh ray hits; one stroke; nonempty mask.";
        }
        public static string LetteringAndUndo()
        {
            RequirePlay();
            Check(Van.StrokeCount == 1, "Run Paint first");
            Check(Pick("Paint can Forest"), "Swap colour can");
            Check(Input.OpenText(SideRay(1.56f, -.65f)), "Aim and open text mode");
            Check(Input.SubmitText("ТЦК"), "Cyrillic lettering: " + Input.Message);
            Check(Van.StrokeCount == 2 && !Input.TextOpen, "Text is one committed stroke and input closes");
            string expected = VanPaintStorage.Hash(Van.SnapshotPng());
            Check(expected != SessionState.GetString("G20.paintHash", ""), "Text changed mask pixels");
            Check(Pick("Paint can Red"), "Swap red can");
            PaintStroke captured = null;
            void CaptureStroke(PaintStroke stroke) { captured = stroke; }
            Van.StrokeCommitted += CaptureStroke;
            for (int i = 0; i < 15; i++) Check(Input.PaintAt(SideRay(1.3f + i * .013f, -.9f)), "Extra stroke ray");
            Input.FinishStroke();
            Van.StrokeCommitted -= CaptureStroke;
            Check(Van.StrokeCount == 3, "Extra stroke created");
            string extraHash = VanPaintStorage.Hash(Van.SnapshotPng());
            Check(extraHash != expected, "Extra stroke is visible in mask");
            Van.UndoStroke();
            Check(Van.StrokeCount == 2 && VanPaintStorage.Hash(Van.SnapshotPng()) == expected, "Undo restores exact previous PNG pixels");
            Check(Van.ApplyStroke(captured) && VanPaintStorage.Hash(Van.SnapshotPng()) == extraHash, "Data-only command replay reproduces the stroke");
            Check(!Van.ApplyStroke(captured) && Van.StrokeCount == 3, "Duplicate command ID rejected");
            Van.UndoStroke();
            Check(VanPaintStorage.Hash(Van.SnapshotPng()) == expected, "Undo after command replay");
            Check(Van.SavePaint(), "Save PNG and JSON");
            SessionState.SetString("G20.savedHash", expected);
            SessionState.SetInt("G20.savedCount", Van.StrokeCount);
            Directory.CreateDirectory(Review);
            WriteNew("verification_before_restart.txt", "PASS\n" + DateTime.UtcNow.ToString("o") + "\nPaint: 71 ray samples, UV pixel location checked\nText: ТЦК\nUndo: exact PNG hash restored\nCommand replay: identical PNG; duplicate rejected\nSave: " + VanPaintStorage.Folder(Van.VanId) + "\nSHA256: " + expected);
            return "PASS: ТЦК stamped in Forest; red stroke undone with exact PNG equality; two strokes saved. Stop and re-enter Play next.";
        }
        public static string RestoreAndWipe()
        {
            RequirePlay();
            string expected = SessionState.GetString("G20.savedHash", "");
            Check(expected.Length > 0, "Prior Play session save evidence exists");
            Check(Van.StrokeCount == SessionState.GetInt("G20.savedCount", -1), "Journal auto-restored on Awake");
            Check(VanPaintStorage.Hash(Van.SnapshotPng()) == expected, "Auto-restored PNG identical after re-entering Play");
            Van.Wipe(); Check(Van.StrokeCount == 0 && CountPaintPixels() == 0, "Full wipe empties mask and history");
            Check(Van.LoadPaint() && Van.StrokeCount == 2 && VanPaintStorage.Hash(Van.SnapshotPng()) == expected, "Load restores saved design after wipe");
            Van.UndoStroke(); Check(Van.StrokeCount == 1 && VanPaintStorage.Hash(Van.SnapshotPng()) == SessionState.GetString("G20.paintHash", ""), "Undo after load restores the original freehand stroke");
            Check(Van.LoadPaint(), "Final restore for review");
            WriteNew("verification_after_restart.txt", "PASS\n" + DateTime.UtcNow.ToString("o") + "\nRe-enter Play: identical PNG hash and 2 strokes\nFull wipe: zero alpha pixels, empty journal\nLoad after wipe: identical PNG\nUndo after load: identical original stroke\nFinal display: saved design restored\nSHA256: " + expected);
            return "PASS: PNG + two strokes auto-restored across Play sessions; wipe, reload, and undo after load passed.";
        }
        public static string Capture(string filename)
        {
            RequirePlay();
            if (Path.GetFileName(filename) != filename || !filename.EndsWith(".png", StringComparison.Ordinal)) throw new ArgumentException("Simple PNG filename required.");
            Directory.CreateDirectory(Review); string path = Path.Combine(Review, filename);
            Check(!File.Exists(path), "Screenshot name must be new");
            Camera camera = UnityEngine.Object.FindAnyObjectByType<VanPaintInteractor>().GetComponentInChildren<Camera>();
            if (camera == null) camera = Camera.main;
            var target = RenderTexture.GetTemporary(1600,900,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
            var old = camera.targetTexture; var active = RenderTexture.active;
            var image = new Texture2D(1600,900,TextureFormat.RGB24,false);
            try
            {
                camera.targetTexture=target; camera.Render(); RenderTexture.active=target;
                image.ReadPixels(new Rect(0,0,1600,900),0,0); image.Apply();
                using var output = new FileStream(path,FileMode.CreateNew,FileAccess.Write);
                byte[] bytes=image.EncodeToPNG(); output.Write(bytes,0,bytes.Length);
            }
            finally { camera.targetTexture=old; RenderTexture.active=active; RenderTexture.ReleaseTemporary(target); UnityEngine.Object.DestroyImmediate(image); }
            return Path.GetFullPath(path);
        }
        static int CountPaintPixels()
        {
            var image = new Texture2D(2,2,TextureFormat.RGBA32,false,true);
            try { image.LoadImage(Van.SnapshotPng()); return image.GetPixels32().Count(p => p.a > 10); }
            finally { UnityEngine.Object.DestroyImmediate(image); }
        }
        static float AlphaAt(Ray ray)
        {
            Check(Physics.Raycast(ray,out var hit,12), "UV sample ray hit");
            var image = new Texture2D(2,2,TextureFormat.RGBA32,false,true);
            try { image.LoadImage(Van.SnapshotPng()); return image.GetPixelBilinear(hit.textureCoord.x,hit.textureCoord.y).a; }
            finally { UnityEngine.Object.DestroyImmediate(image); }
        }
        static void WriteNew(string name, string text)
        {
            using var writer = new StreamWriter(new FileStream(Path.Combine(Review,name),FileMode.CreateNew,FileAccess.Write));
            writer.Write(text);
        }
    }
}
