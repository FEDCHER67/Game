using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace OnlyVolunteers.Vehicles.Paint.Editor
{
    public static class VanPaintTestBuilder
    {
        public const string Root = "Assets/OnlyVolunteers/Vehicles/Paint";
        public const string ScenePath = "Assets/OnlyVolunteers/Scenes/Dev/VanPaint_Test.unity";
        const string Generated = Root + "/Generated";
        const string Prefab = "Assets/OnlyVolunteers/Vehicles/Van/Prefabs/Van.prefab";
        const string LockPath = "C:/Users/Zeyo-ne/AppData/Local/Temp/claude/C--Dev/ea60d9e7-6c0b-4ef6-b304-3bbf5da8bf0f/scratchpad/unity.lock";

        public static void RequireLock()
        {
            string[] parts = File.Exists(LockPath) ? File.ReadAllText(LockPath).Split((char[])null, StringSplitOptions.RemoveEmptyEntries) : Array.Empty<string>();
            string owner = parts.Length > 0 ? parts[0] : "";
            if (!string.Equals(owner, "G20", StringComparison.OrdinalIgnoreCase) &&
                !string.Equals(owner, "gpt-g20", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("G20 must own the shared Unity lock.");
        }

        [MenuItem("OnlyVolunteers/Van Paint/Create G20 Test Scene (new only)")]
        public static void Build()
        {
            RequireLock();
            if (EditorApplication.isPlaying || File.Exists(ScenePath) || Directory.Exists(Generated))
                throw new InvalidOperationException("Build creates new deliverables only. Stop Play; never overwrite an existing test scene/generated set.");
            for (int i = 0; i < SceneManager.sceneCount; i++)
                if (SceneManager.GetSceneAt(i).isDirty) throw new InvalidOperationException("An existing scene has unsaved changes; it was preserved.");
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            if (prefab == null) throw new InvalidOperationException("Existing van prefab not found.");
            Shader paintShader = AssetDatabase.LoadAssetAtPath<Shader>(Root + "/Shaders/VanPaintBody.shader");
            Shader brushShader = AssetDatabase.LoadAssetAtPath<Shader>(Root + "/Shaders/VanPaintBrush.shader");
            if (paintShader == null || brushShader == null || !paintShader.isSupported || !brushShader.isSupported)
                throw new InvalidOperationException("Paint shaders must compile before building the scene.");
            Directory.CreateDirectory(Generated);
            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            AssetDatabase.Refresh();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(.65f, .68f, .68f);
            RenderSettings.skybox = null;
            var sun = new GameObject("G20 Afternoon light").AddComponent<Light>();
            sun.type = LightType.Directional; sun.intensity = 1.1f; sun.color = new Color(1, .92f, .78f);
            sun.transform.rotation = Quaternion.Euler(40, -30, 0); sun.shadows = LightShadows.Soft;

            var van = new GameObject("G20 Paintable Van").AddComponent<VanPaintSurface>();
            MeshFilter[] filters = prefab.GetComponentsInChildren<MeshFilter>(true);
            var bounds = new Bounds(Vector3.zero, Vector3.zero);
            bool first = true;
            foreach (var f in filters)
                foreach (var p in f.sharedMesh.vertices)
                {
                    Vector3 q = f.transform.TransformPoint(p);
                    if (first) { bounds = new Bounds(q, Vector3.zero); first = false; } else bounds.Encapsulate(q);
                }
            var painted = new List<Renderer>();
            var paintMaterials = new Dictionary<Material, Material>();
            int index = 0;
            foreach (var f in filters)
            {
                var sourceRenderer = f.GetComponent<MeshRenderer>();
                if (sourceRenderer == null) continue;
                var go = new GameObject(f.name); go.transform.SetParent(van.transform, false);
                var mf = go.AddComponent<MeshFilter>(); var renderer = go.AddComponent<MeshRenderer>();
                Material[] materials = sourceRenderer.sharedMaterials;
                bool any = false;
                foreach (var mat in materials) if (IsPaint(mat)) any = true;
                bool[] allowed;
                Mesh mesh = AtlasMesh(f, bounds, materials, out allowed);
                mesh.name = f.name + "_PaintUV";
                AssetDatabase.CreateAsset(mesh, Generated + "/Mesh_" + index++ + ".asset");
                mf.sharedMesh = mesh;
                for (int m = 0; m < materials.Length; m++)
                {
                    var original = materials[m];
                    if (!IsPaint(original)) continue;
                    if (!paintMaterials.TryGetValue(original, out var paintMat))
                    {
                        paintMat = new Material(paintShader) { name = original.name + "_G20Paint" };
                        paintMat.SetColor("_BaseColor", original.HasProperty("_BaseColor") ? original.GetColor("_BaseColor") : new Color(.9f, .86f, .77f));
                        AssetDatabase.CreateAsset(paintMat, Generated + "/" + paintMat.name + ".mat");
                        paintMaterials.Add(original, paintMat);
                    }
                    materials[m] = paintMat;
                }
                renderer.sharedMaterials = materials;
                go.AddComponent<MeshCollider>().sharedMesh = mesh;
                if (any) { painted.Add(renderer); go.AddComponent<VanPaintTarget>().Configure(van, allowed); }
            }
            van.Configure(brushShader, painted.ToArray(), bounds.size);

            var grass = Material("Ground", new Color(.38f, .43f, .31f));
            var wood = Material("OldWood", new Color(.36f, .25f, .16f));
            var cream = Material("Fence", new Color(.73f, .70f, .54f));
            var roof = Material("Roof", new Color(.22f, .30f, .27f));
            var metal = Material("Tin", new Color(.48f, .52f, .48f));
            var dark = Material("Door", new Color(.15f, .19f, .16f));
            Cube("G20 Ground", new Vector3(0, -.15f, 0), new Vector3(28, .25f, 28), grass);
            Cube("Grandpa's hut placeholder", new Vector3(4.5f, 1.2f, -3), new Vector3(3.4f, 2.4f, 3.4f), wood);
            Cube("Hut roof", new Vector3(4.5f, 2.55f, -3), new Vector3(3.9f, .3f, 3.9f), roof);
            Cube("Hut door", new Vector3(4.5f, .9f, -1.27f), new Vector3(.9f, 1.8f, .06f), dark);
            for (int i = 0; i < 15; i++) Cube("Freshly painted fence " + i, new Vector3(-3.5f + i * .55f, .65f, -4.3f), new Vector3(.38f, 1.3f, .10f), cream);
            Cube("Fence rail", new Vector3(.4f, .8f, -4.36f), new Vector3(8.5f, .12f, .1f), wood);
            Vector3 table = new(-2.9f, .75f, .6f);
            Cube("Grandpa's paint table", table, new Vector3(.9f, .10f, 2.5f), wood);
            foreach (float x in new[] { -.35f, .35f }) foreach (float z in new[] { -1f, 1f })
                Cube("Table leg", table + new Vector3(x, -.38f, z), new Vector3(.09f, .7f, .09f), wood);
            Color[] colors = { new(.17f,.43f,.65f), new(.77f,.22f,.16f), new(.94f,.68f,.16f), new(.12f,.18f,.15f) };
            string[] names = { "Blue", "Red", "Ochre", "Forest" };
            for (int i = 0; i < colors.Length; i++)
            {
                var can = new GameObject("Paint can " + names[i]); can.transform.position = table + new Vector3(0, .08f, -.85f + i * .48f);
                var tin = Primitive(PrimitiveType.Cylinder, "Tin", Vector3.zero, new Vector3(.24f, .14f, .24f), metal, can.transform);
                tin.transform.localPosition = new Vector3(0,.14f,0);
                var pigment = Material("Can_" + names[i], colors[i]);
                Primitive(PrimitiveType.Cylinder, "Paint inside", new Vector3(0, .286f, 0), new Vector3(.205f, .006f, .205f), pigment, can.transform);
                Primitive(PrimitiveType.Cylinder, "Colour band", new Vector3(0, .14f, 0), new Vector3(.244f, .06f, .244f), pigment, can.transform);
                can.AddComponent<VanPaintProp>().Configure(false, colors[i], names[i]);
            }
            var brushProp = new GameObject("Grandpa's fence brush"); brushProp.transform.position = table + new Vector3(-.30f,.09f,1.0f);
            Cube("Brush handle", new Vector3(0,.16f,0), new Vector3(.06f,.32f,.055f), wood, brushProp.transform);
            Cube("Brush ferrule", new Vector3(0,.35f,0), new Vector3(.18f,.10f,.065f), metal, brushProp.transform);
            Cube("Brush bristles", new Vector3(0,.44f,0), new Vector3(.17f,.11f,.06f), cream, brushProp.transform);
            brushProp.AddComponent<VanPaintProp>().Configure(true, Color.white, "Brush");

            var camera = new GameObject("G20 Paint Camera").AddComponent<Camera>(); camera.tag = "MainCamera";
            camera.transform.position = new Vector3(-6.8f, 3.2f, 6.5f); camera.transform.LookAt(new Vector3(0,1,0));
            camera.fieldOfView = 45; camera.nearClipPlane = .05f; camera.farClipPlane = 80;
            camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.64f,.74f,.77f);
            camera.gameObject.AddComponent<AudioListener>();
            Transform Hand(string name, Vector3 pos)
            { var t = new GameObject(name).transform; t.SetParent(camera.transform,false); t.localPosition = pos; return t; }
            var left = Hand("Held can", new Vector3(-.48f,-.44f,1.1f));
            var right = Hand("Held brush", new Vector3(.50f,-.40f,1.1f));
            var controller = new GameObject("G20 Painting Controls").AddComponent<VanPaintInteractor>();
            var ui = new GameObject("G20 Painting HUD");
            var document = ui.AddComponent<UIDocument>();
            var settings = ScriptableObject.CreateInstance<PanelSettings>();
            settings.themeStyleSheet = AssetDatabase.LoadAssetAtPath<ThemeStyleSheet>(Root + "/UI/VanPaintTheme.tss");
            settings.scaleMode = PanelScaleMode.ScaleWithScreenSize; settings.referenceResolution = new Vector2Int(1600,900);
            AssetDatabase.CreateAsset(settings, Generated + "/PaintPanelSettings.asset");
            document.panelSettings = settings; document.visualTreeAsset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(Root + "/UI/VanPaintHud.uxml");
            var hud = ui.AddComponent<VanPaintHud>();
            controller.Configure(camera, van, hud, left, right); hud.Configure(controller, van);
            if (!EditorSceneManager.SaveScene(scene, ScenePath)) throw new IOException("Test scene could not be saved.");
            Debug.Log("[VanPaint] Created " + ScenePath + "; " + painted.Count + " paint renderers. Existing van prefab and maps unchanged.");
        }

        static bool IsPaint(Material material) => material != null && material.name.StartsWith("VAN_Body", StringComparison.Ordinal);
        static Material Material(string name, Color color)
        {
            var mat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "G20_" + name };
            mat.SetColor("_BaseColor", color); mat.SetFloat("_Smoothness", .18f);
            AssetDatabase.CreateAsset(mat, Generated + "/" + mat.name + ".mat"); return mat;
        }
        static GameObject Cube(string name, Vector3 pos, Vector3 scale, Material mat, Transform parent = null) => Primitive(PrimitiveType.Cube,name,pos,scale,mat,parent);
        static GameObject Primitive(PrimitiveType type, string name, Vector3 pos, Vector3 scale, Material mat, Transform parent)
        {
            var go = GameObject.CreatePrimitive(type); go.name = name;
            go.transform.SetParent(parent,false); go.transform.localPosition = pos; go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = mat; return go;
        }

        static Mesh AtlasMesh(MeshFilter source, Bounds bounds, Material[] materials, out bool[] allowed)
        {
            Mesh original = source.sharedMesh;
            var originalPositions = original.vertices; var originalNormals = original.normals;
            var positions = new List<Vector3>(); var normals = new List<Vector3>(); var uv = new List<Vector2>();
            var triangleLists = new List<int[]>(); var flags = new List<bool>();
            for (int sub = 0; sub < original.subMeshCount; sub++)
            {
                int[] indices = original.GetTriangles(sub); int[] replacement = new int[indices.Length];
                for (int t = 0; t < indices.Length; t += 3)
                {
                    Vector3 a=source.transform.TransformPoint(originalPositions[indices[t]]), b=source.transform.TransformPoint(originalPositions[indices[t+1]]), c=source.transform.TransformPoint(originalPositions[indices[t+2]]);
                    Vector3 n=Vector3.Cross(b-a,c-a).normalized;
                    int face = Mathf.Abs(n.x) >= Mathf.Abs(n.y) && Mathf.Abs(n.x) >= Mathf.Abs(n.z) ? (n.x < 0 ? 0 : 1) : Mathf.Abs(n.y) >= Mathf.Abs(n.z) ? (n.y > 0 ? 2 : 3) : (n.z > 0 ? 4 : 5);
                    for(int k=0;k<3;k++)
                    {
                        int vi=indices[t+k]; Vector3 p=source.transform.TransformPoint(originalPositions[vi]);
                        Vector3 normalized = new((p.x-bounds.min.x)/bounds.size.x,(p.y-bounds.min.y)/bounds.size.y,(p.z-bounds.min.z)/bounds.size.z);
                        Vector2 flat = face == 0 ? new Vector2(1-normalized.z,normalized.y) : face == 1 ? new Vector2(normalized.z,normalized.y) :
                            face == 2 ? new Vector2(normalized.x,normalized.z) : face == 3 ? new Vector2(normalized.x,1-normalized.z) :
                            face == 4 ? new Vector2(1-normalized.x,normalized.y) : new Vector2(normalized.x,normalized.y);
                        uv.Add(new Vector2(face%3/3f+.012f+flat.x*(1/3f-.024f),face/3/2f+.012f+flat.y*(.5f-.024f)));
                        replacement[t+k]=positions.Count; positions.Add(p);
                        normals.Add(originalNormals.Length == originalPositions.Length ? source.transform.TransformDirection(originalNormals[vi]).normalized : n);
                    }
                    flags.Add(sub < materials.Length && IsPaint(materials[sub]));
                }
                triangleLists.Add(replacement);
            }
            var mesh=new Mesh { indexFormat=IndexFormat.UInt32 };
            mesh.SetVertices(positions); mesh.SetNormals(normals); mesh.SetUVs(0,uv); mesh.subMeshCount=triangleLists.Count;
            for(int i=0;i<triangleLists.Count;i++) mesh.SetTriangles(triangleLists[i],i);
            mesh.RecalculateBounds(); allowed=flags.ToArray(); return mesh;
        }
    }
}
