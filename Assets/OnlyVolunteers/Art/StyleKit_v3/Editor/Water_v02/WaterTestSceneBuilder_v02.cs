// G14 v02. Explicit editor menu only; no downloads, automatic callbacks or runtime scripts.
// C# 9. Every invocation creates a new numbered scene and its own mesh/material assets.
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Art.WaterV02.Editor
{
    internal static class WaterTestSceneBuilderV02
    {
        private const string MaterialRoot = "Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/";
        private const string TestRoot = "Assets/OnlyVolunteers/Art/StyleKit_v3/WaterTests";
        private const string RigName = "G14_Water_v02_CameraRig";
        private const string ShaderName = "OnlyVolunteers/Uber Stylized Water v02";
        private const string ViewMenu = "OnlyVolunteers/Art/Water Test View/";

        [MenuItem("OnlyVolunteers/Art/Build Water Test Scene")]
        private static void Build()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("G14: leave Play Mode before building the water test scene.");
            if (PrefabStageUtility.GetCurrentPrefabStage() != null)
                throw new InvalidOperationException("G14: finish your prefab edit and leave Prefab Mode before building the water test scene. Nothing was written.");
            // Do not close, save, discard or alter anyone's unsaved scene work.
            for (int i = 0; i < SceneManager.sceneCount; ++i)
                if (SceneManager.GetSceneAt(i).isDirty)
                    throw new InvalidOperationException("G14: save your open scene drafts first, then run Build Water Test Scene again. Nothing was written.");

            var sea = LoadWater("Sea");
            var lake = LoadWater("Lake");
            var river = LoadWater("River");
            var fall = LoadWater("Waterfall");
            var splash = LoadWater("FoamSplash");
            var solidShader = Shader.Find("Universal Render Pipeline/Simple Lit");
            if (solidShader == null)
                throw new InvalidOperationException("G14: URP Simple Lit is missing; allow the pinned URP package to finish importing.");

            string folder = AllocateFolder();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            scene.name = Path.GetFileName(folder);
            var root = new GameObject("G14 Water v02 - metres - visual review").transform;
            var sand = Solid(folder, "Sand", "F1DEAC", solidShader);
            var grass = Solid(folder, "Grass", "8CBC5E", solidShader);
            var stone = Solid(folder, "Stone", "A3A6AB", solidShader);
            var wood = Solid(folder, "Pier", "9C6E4A", solidShader);
            var chalk = Solid(folder, "Chalk", "F4EFE6", solidShader);
            var yellow = Solid(folder, "VanYellow", "E0A830", solidShader);
            var dark = Solid(folder, "Rubber", "3B4048", solidShader);

            // Sea: 0.28 slope, 1.5 m shallows, >6 m depth at the front. Mesh spacing <=0.5 m.
            Grid(folder, root, "Sea_SandSlope", sand, 64, 80, (u, v) =>
            {
                float x = Mathf.Lerp(-32, -4, u), z = Mathf.Lerp(-18, 22, v);
                return new Vector3(x, Mathf.Clamp(0.25f - (12 - z) * 0.28f, -7.6f, 1.1f), z);
            });
            Grid(folder, root, "Sea_Subdivided_Surface", sea, 56, 64,
                (u, v) => new Vector3(Mathf.Lerp(-31, -5, u), 0, Mathf.Lerp(-17, 13, v)), null, 0.5f);
            Box(root, "Sea_Pier_Deck", new Vector3(-22, 0.85f, 7), new Vector3(2.6f, 0.25f, 9), wood);
            foreach (float z in new[] { 3.5f, 7f, 10.5f })
                foreach (float x in new[] { -23f, -21f })
                    Cylinder(root, "Pier_Post_Intersection", new Vector3(x, -0.2f, z), new Vector3(0.32f, 1.4f, 0.32f), wood);
            Rock(root, new Vector3(-8, -0.05f, 9), new Vector3(1.8f, 1.9f, 1.4f), stone);
            Box(root, "Boat_Opaque_Contact_Proxy", new Vector3(-27, 0.04f, 5), new Vector3(1.5f, 0.65f, 3.2f), chalk);
            Box(root, "Boat_Seat_Proxy", new Vector3(-27, 0.44f, 5), new Vector3(1.4f, 0.2f, 0.5f), wood);
            BuildVanProxy(root, yellow, dark);

            // A shallow oval basin: calm normals and only centimetre-scale displacement.
            Grid(folder, root, "Lake_Basin", sand, 48, 40, (u, v) =>
            {
                float x = Mathf.Lerp(1, 23, u), z = Mathf.Lerp(1, 21, v);
                float radius2 = Mathf.Pow((x - 12) / 10, 2) + Mathf.Pow((z - 11) / 8, 2);
                return new Vector3(x, 0.45f - 2.65f * Mathf.Clamp01(1 - radius2), z);
            });
            Grid(folder, root, "Lake_Subdivided_Surface", lake, 44, 40,
                (u, v) => new Vector3(Mathf.Lerp(2, 22, u), 0, Mathf.Lerp(3, 19, v)), null, 0.12f);
            Box(root, "Lake_Grass_Terrace", new Vector3(25, 0.1f, 11), new Vector3(4, 0.6f, 20), grass);
            Rock(root, new Vector3(7, -0.15f, 6), new Vector3(1.6f, 1.5f, 1.2f), stone);

            // Flow is the real converter contract: UV1.xy = signed world XZ metres per second.
            Grid(folder, root, "River_Bed_and_Banks", stone, 64, 24, (u, v) =>
            {
                float x = Mathf.Lerp(-1, 29, u), across = Mathf.Lerp(-5, 5, v);
                float y = Mathf.Lerp(-1.5f, 0.6f, Mathf.SmoothStep(0, 1, Mathf.InverseLerp(2.8f, 4.6f, Mathf.Abs(across))));
                return new Vector3(x, y, RiverZ(x) + across);
            });
            Grid(folder, root, "River_UV1_Flow_0.55mps", river, 64, 16,
                (u, v) => new Vector3(Mathf.Lerp(0, 28, u), 0, RiverZ(Mathf.Lerp(0, 28, u)) + Mathf.Lerp(-4, 4, v)),
                (u, v) => new Vector2(1, 0.252f * Mathf.Cos(Mathf.Lerp(0, 28, u) * 0.18f)).normalized * 0.55f, 0.08f);
            float bridgeZ = RiverZ(15);
            Box(root, "Bridge_Pillar_Intersection", new Vector3(15, 0.05f, bridgeZ), new Vector3(0.85f, 3.1f, 0.85f), chalk);
            Box(root, "Bridge_Deck", new Vector3(15, 1.7f, bridgeZ), new Vector3(1.8f, 0.3f, 10), wood);
            Rock(root, new Vector3(7.5f, -0.25f, RiverZ(7.5f) - 1.4f), new Vector3(1.1f, 1.7f, 1.6f), stone);

            // Standalone vertical sheet into the lake; an opaque cliff provides a depth reference.
            Box(root, "Waterfall_Cliff", new Vector3(13, 2.1f, 19.8f), new Vector3(7.6f, 6.3f, 2.5f), stone);
            Box(root, "Waterfall_Upper_Ledge", new Vector3(13, 5.15f, 19.2f), new Vector3(5.3f, 0.25f, 2), grass);
            Grid(folder, root, "Waterfall_V_Upwards", fall, 20, 28, (u, v) =>
                new Vector3(Mathf.Lerp(10.8f, 15.2f, u), Mathf.Lerp(0.06f, 5.32f, v),
                    18.28f - 0.38f * Mathf.Pow(1 - v, 3)));
            Grid(folder, root, "Waterfall_Base_FoamSplash", splash, 1, 1,
                (u, v) => new Vector3(Mathf.Lerp(9.3f, 16.7f, u), 0.065f, Mathf.Lerp(14.3f, 19.1f, v)));

            AddCameraAndLight();
            string scenePath = folder + "/" + scene.name + ".unity";
            if (File.Exists(scenePath) || !EditorSceneManager.SaveScene(scene, scenePath, false))
                throw new IOException("G14: could not save the new water scene. Keep the open scene for recovery; no existing scene was overwritten.");
            Selection.activeGameObject = root.gameObject;
            SceneView.lastActiveSceneView?.FrameSelected();
            Debug.Log("G14 water test created: " + scenePath +
                "\nUse OnlyVolunteers/Art/Water Test View for the single camera's capture angles. Enable Animated Materials in Scene view, or Play for moving water. No URP assets changed.");
        }

        private static Material LoadWater(string kind)
        {
            string path = MaterialRoot + "M3_Water_" + kind + "_v02.mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null || material.shader == null || material.shader.name != ShaderName)
                throw new InvalidOperationException("G14: import the v02 water assets first. Missing/wrong shader: " + path);
            if (!material.shader.isSupported || ShaderUtil.ShaderHasError(material.shader))
                throw new InvalidOperationException("G14: resolve the water shader import errors in Console before generating a scene.");
            return material;
        }

        private static string AllocateFolder()
        {
            EnsureFolder(TestRoot);
            for (int revision = 1; revision < 10000; ++revision)
            {
                string path = TestRoot + "/WaterTest_v02_" + revision.ToString("D3");
                if (Directory.Exists(path) || File.Exists(path + ".meta") || AssetDatabase.IsValidFolder(path)) continue;
                EnsureFolder(path);
                return path;
            }
            throw new IOException("G14: no free numbered water test folder.");
        }

        private static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path)?.Replace('\\', '/');
            if (string.IsNullOrEmpty(parent)) throw new IOException("Invalid asset folder: " + path);
            EnsureFolder(parent);
            if (string.IsNullOrEmpty(AssetDatabase.CreateFolder(parent, Path.GetFileName(path))))
                throw new IOException("Could not create folder: " + path);
        }

        private static Material Solid(string folder, string name, string hex, Shader shader)
        {
            var material = new Material(shader) { name = "Test_" + name };
            material.SetColor("_BaseColor", Hex(hex));
            material.SetFloat("_Smoothness", 0.18f);
            material.SetFloat("_SpecularHighlights", 0);
            AssetDatabase.CreateAsset(material, folder + "/Test_" + name + ".mat");
            return material;
        }

        private static void Grid(string folder, Transform parent, string name, Material material, int nx, int nz,
            Func<float, float, Vector3> position, Func<float, float, Vector2> flow = null,
            float boundsPadding = 0)
        {
            int count = (nx + 1) * (nz + 1);
            var vertices = new Vector3[count];
            var uv = new Vector2[count];
            var velocity = new List<Vector2>(count);
            var colours = new Color[count];
            var triangles = new int[nx * nz * 6];
            for (int z = 0; z <= nz; ++z)
                for (int x = 0; x <= nx; ++x)
                {
                    int index = z * (nx + 1) + x;
                    float u = (float)x / nx, v = (float)z / nz;
                    vertices[index] = position(u, v);
                    uv[index] = new Vector2(u, v);
                    velocity.Add(flow != null ? flow(u, v) : Vector2.zero);
                    colours[index] = Color.white;
                }
            int t = 0;
            for (int z = 0; z < nz; ++z)
                for (int x = 0; x < nx; ++x)
                {
                    int a = z * (nx + 1) + x, b = a + nx + 1;
                    // Horizontal grids face +Y; the vertical waterfall faces the capture camera (-Z).
                    triangles[t++] = a; triangles[t++] = b; triangles[t++] = a + 1;
                    triangles[t++] = a + 1; triangles[t++] = b; triangles[t++] = b + 1;
                }
            var mesh = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
            mesh.vertices = vertices; mesh.uv = uv; mesh.colors = colours; mesh.triangles = triangles;
            mesh.SetUVs(1, velocity);
            mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
            var bounds = mesh.bounds;
            bounds.Expand(boundsPadding * 2);
            mesh.bounds = bounds;
            AssetDatabase.CreateAsset(mesh, folder + "/" + name + ".asset");
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(parent, false);
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = material.shader.name == ShaderName ? ShadowCastingMode.Off : ShadowCastingMode.On;
            renderer.receiveShadows = true;
        }

        private static void Box(Transform parent, string name, Vector3 centre, Vector3 size, Material material)
            => Primitive(parent, name, PrimitiveType.Cube, centre, size, material);

        private static void Cylinder(Transform parent, string name, Vector3 centre, Vector3 scale, Material material)
            => Primitive(parent, name, PrimitiveType.Cylinder, centre, scale, material);

        private static void Rock(Transform parent, Vector3 centre, Vector3 size, Material material)
        {
            var go = Primitive(parent, "Rock_Intersection", PrimitiveType.Cube, centre, size, material);
            go.transform.rotation = Quaternion.Euler(9, 27, 12);
        }

        private static GameObject Primitive(Transform parent, string name, PrimitiveType type, Vector3 centre, Vector3 scale, Material material)
        {
            var go = GameObject.CreatePrimitive(type);
            go.name = name; go.transform.SetParent(parent, false);
            go.transform.position = centre; go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = material;
            return go;
        }

        private static void BuildVanProxy(Transform parent, Material body, Material tyre)
        {
            Box(parent, "Van_Opaque_Depth_Proxy", new Vector3(-13, 0.6f, 10), new Vector3(2, 1.4f, 3.8f), body);
            foreach (float x in new[] { -14f, -12f })
                foreach (float z in new[] { 8.9f, 11.1f })
                {
                    var wheel = Primitive(parent, "Van_Wheel_Contact", PrimitiveType.Cylinder,
                        new Vector3(x, 0.07f, z), new Vector3(0.65f, 0.14f, 0.65f), tyre);
                    wheel.transform.rotation = Quaternion.Euler(0, 0, 90);
                }
        }

        private static float RiverZ(float x) => -8 + 1.4f * Mathf.Sin(x * 0.18f);
        private static Color Hex(string hex) => ColorUtility.TryParseHtmlString("#" + hex, out var c) ? c : Color.white;

        private static void AddCameraAndLight()
        {
            RenderSettings.skybox = null;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = Hex("C8E5EF");
            RenderSettings.ambientEquatorColor = Hex("ACCBD1");
            RenderSettings.ambientGroundColor = Hex("9EB1B7");
            RenderSettings.fog = false;
            var sun = new GameObject("Warm_Sun", typeof(Light)).GetComponent<Light>();
            sun.type = LightType.Directional; sun.intensity = 1.15f; sun.color = Hex("FFF4DE");
            sun.shadows = LightShadows.Soft; sun.shadowStrength = 0.75f;
            sun.transform.rotation = Quaternion.Euler(47, -32, 0);
            RenderSettings.sun = sun;
            var rig = new GameObject(RigName).transform;
            var camera = new GameObject("Capture_Camera", typeof(Camera)).GetComponent<Camera>();
            camera.transform.SetParent(rig, false);
            camera.nearClipPlane = 0.1f; camera.farClipPlane = 300;
            camera.allowHDR = true; camera.allowMSAA = true;
            camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = Hex("BFE2EF");
            var urp = camera.GetUniversalAdditionalCameraData();
            urp.requiresDepthTexture = true; urp.requiresColorTexture = true;
            urp.renderPostProcessing = false;
            Pose(rig, "Overview", new Vector3(-42, 36, -46), new Vector3(-2, 0, 4));
            Pose(rig, "Sea", new Vector3(-32, 6, -1), new Vector3(-18, 0, 9));
            Pose(rig, "River", new Vector3(7, 5, -18), new Vector3(15, 0, -8));
            Pose(rig, "Lake_Waterfall", new Vector3(2, 6, 0), new Vector3(12, 1, 14));
            ApplyView("Overview", false);
        }

        private static void Pose(Transform rig, string name, Vector3 position, Vector3 target)
        {
            var pose = new GameObject(name).transform;
            pose.SetParent(rig, false); pose.position = position;
            pose.rotation = Quaternion.LookRotation(target - position, Vector3.up);
        }

        [MenuItem(ViewMenu + "Overview")] private static void Overview() => ApplyView("Overview", true);
        [MenuItem(ViewMenu + "Sea")] private static void SeaView() => ApplyView("Sea", true);
        [MenuItem(ViewMenu + "River")] private static void RiverView() => ApplyView("River", true);
        [MenuItem(ViewMenu + "Lake and Waterfall")] private static void FallView() => ApplyView("Lake_Waterfall", true);

        private static void ApplyView(string name, bool recordUndo)
        {
            foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
            {
                if (root.name != RigName) continue;
                var camera = root.GetComponentInChildren<Camera>();
                var pose = root.transform.Find(name);
                if (camera == null || pose == null) break;
                if (recordUndo) Undo.RecordObjects(new UnityEngine.Object[] { camera.transform, camera }, "Water capture view");
                camera.transform.SetPositionAndRotation(pose.position, pose.rotation);
                camera.fieldOfView = name == "Overview" ? 48 : 52;
                Selection.activeGameObject = camera.gameObject;
                return;
            }
            throw new InvalidOperationException("Open a generated G14 v02 water test scene before choosing its capture view.");
        }
    }
}
