using System.Collections.Generic;
using System.IO;
using OnlyVolunteers.Vehicles;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Vehicles.EditorTools
{
    // Rebuilds the van prefab (materials, colliders, wheels, doors) from the imported FBX and the
    // standalone VanDriveTest scene. Re-run after importing a new numbered van revision.
    public static class VanSetupBuilder
    {
        private const string Root = "Assets/OnlyVolunteers/Vehicles/Van";
        private const string ModelPath = Root + "/Model/VAN-TIER0-ASTRA-001_v02.fbx";
        private const string MaterialDir = Root + "/Materials";
        private const string PrefabPath = Root + "/Prefabs/Van.prefab";
        private const string ScenePath = "Assets/OnlyVolunteers/Scenes/VanDriveTest.unity";

        // Blender-space reference points (Z up, -Y forward, +X = vehicle left) used to map collider boxes.
        private static readonly Vector3 BFrontLeft = new(0.80f, -1.60f, 0.37f);
        private static readonly Vector3 BFrontRight = new(-0.80f, -1.60f, 0.37f);
        private static readonly Vector3 BRearLeft = new(0.80f, 1.56f, 0.37f);
        private static readonly Vector3 BEye = new(0.48f, -0.78f, 1.60f);

        private static readonly Dictionary<string, (Color32 color, float smooth, float alpha)> Materials = new()
        {
            ["VAN_Body_Cream"] = (new Color32(233, 222, 203, 255), 0.25f, 1f),
            ["VAN_Body_Crease"] = (new Color32(196, 184, 163, 255), 0.2f, 1f),
            ["VAN_Interior"] = (new Color32(150, 144, 134, 255), 0.1f, 1f),
            ["VAN_Trim_Dark"] = (new Color32(62, 63, 66, 255), 0.15f, 1f),
            ["VAN_Grille_Black"] = (new Color32(34, 35, 37, 255), 0.1f, 1f),
            ["VAN_Glass"] = (new Color32(58, 66, 80, 255), 0.85f, 0.42f),
            ["VAN_Light_White"] = (new Color32(236, 236, 232, 255), 0.6f, 1f),
            ["VAN_Indicator_Orange"] = (new Color32(226, 128, 28, 255), 0.5f, 1f),
            ["VAN_Tail_Red"] = (new Color32(204, 38, 38, 255), 0.5f, 1f),
            ["VAN_Hub_Cream"] = (new Color32(214, 205, 186, 255), 0.2f, 1f),
            ["VAN_Tire"] = (new Color32(44, 44, 46, 255), 0.05f, 1f),
            ["VAN_Seat"] = (new Color32(70, 72, 78, 255), 0.05f, 1f),
        };

        [MenuItem("OnlyVolunteers/Van/Rebuild Van Prefab And Test Scene")]
        public static void BuildAll()
        {
            ConfigureModel();
            GameObject prefab = BuildPrefab();
            BuildScene(prefab);
            Debug.Log("[Van] prefab and VanDriveTest scene rebuilt");
        }

        private static void ConfigureModel()
        {
            Directory.CreateDirectory(MaterialDir);
            var importer = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            importer.animationType = ModelImporterAnimationType.None;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            foreach (var kv in Materials)
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), kv.Key), GetOrCreateMaterial(kv.Key, kv.Value));
            importer.SaveAndReimport();
        }

        private static Material GetOrCreateMaterial(string name, (Color32 color, float smooth, float alpha) spec)
        {
            string path = $"{MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            Color c = spec.color;
            c.a = spec.alpha;
            mat.SetColor("_BaseColor", c);
            mat.SetFloat("_Smoothness", spec.smooth);
            mat.SetFloat("_Metallic", 0f);
            if (spec.alpha < 1f)
            {
                mat.SetFloat("_Surface", 1f);
                mat.SetFloat("_Blend", 0f);
                mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                mat.SetFloat("_ZWrite", 0f);
                mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                mat.renderQueue = (int)RenderQueue.Transparent;
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static GameObject BuildPrefab()
        {
            Directory.CreateDirectory(Path.GetDirectoryName(PrefabPath));
            var root = new GameObject("Van");
            try
            {
                var modelAsset = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
                var model = (GameObject)PrefabUtility.InstantiatePrefab(modelAsset, root.transform);
                model.name = "Model";

                Transform fl = Find(model.transform, "VAN_Wheel_Front_Left");
                Transform fr = Find(model.transform, "VAN_Wheel_Front_Right");
                Transform rl = Find(model.transform, "VAN_Wheel_Rear_Left");
                Transform rr = Find(model.transform, "VAN_Wheel_Rear_Right");

                // Face the van along +Z, then put the wheelbase centre on the ground at the root origin.
                Vector3 forward = (fl.position + fr.position - rl.position - rr.position) * 0.5f;
                forward.y = 0f;
                model.transform.rotation = Quaternion.FromToRotation(forward.normalized, Vector3.forward) * model.transform.rotation;
                float radius = fl.GetComponent<Renderer>().bounds.extents.y;
                Vector3 mid = (fl.position + fr.position + rl.position + rr.position) * 0.25f;
                model.transform.position -= new Vector3(mid.x, mid.y - radius, mid.z);
                if (fl.position.x > fr.position.x)
                    Debug.LogError("[Van] vehicle left is not on -X; the FBX axes differ from the expected conversion");

                // Blender -> van-root affine map from four non-coplanar reference points.
                Transform eye = Find(model.transform, "SOCKET_DriverEye");
                Matrix4x4 map = SolveMap(fl.position, fr.position, rl.position, eye.position);

                var body = root.AddComponent<Rigidbody>();
                body.mass = 1800f;
                body.linearDamping = 0.02f;
                body.angularDamping = 0.35f;
                body.interpolation = RigidbodyInterpolation.Interpolate;
                body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;

                BuildBodyColliders(root.transform, map);
                var controller = root.AddComponent<VanController>();
                controller.Front.Left = MakeWheel(root.transform, "WheelCollider_FrontLeft", fl, radius);
                controller.Front.Right = MakeWheel(root.transform, "WheelCollider_FrontRight", fr, radius);
                controller.Rear.Left = MakeWheel(root.transform, "WheelCollider_RearLeft", rl, radius);
                controller.Rear.Right = MakeWheel(root.transform, "WheelCollider_RearRight", rr, radius);
                controller.Front.LeftVisual = fl;
                controller.Front.RightVisual = fr;
                controller.Rear.LeftVisual = rl;
                controller.Rear.RightVisual = rr;
                controller.SteeringWheel = Find(model.transform, "VAN_SteeringWheel");
                root.AddComponent<VanUpgrades>();
                controller.CenterOfMass = new Vector3(0f, 0.6f, 0.2f);

                SetupDoor(model.transform, root.transform, "VAN_Door_Front_Left", VanDoor.Kind.Hinge, 70f, Vector3.left);
                SetupDoor(model.transform, root.transform, "VAN_Door_Front_Right", VanDoor.Kind.Hinge, 70f, Vector3.right);
                SetupDoor(model.transform, root.transform, "VAN_Door_Rear_Left", VanDoor.Kind.Hinge, 100f, Vector3.back);
                SetupDoor(model.transform, root.transform, "VAN_Door_Rear_Right", VanDoor.Kind.Hinge, 100f, Vector3.back);
                VanDoor slide = SetupDoor(model.transform, root.transform, "VAN_Door_Slide", VanDoor.Kind.Slide, 0f, Vector3.right);
                slide.SlidePop = new Vector3(0.07f, 0f, 0f);
                slide.SlideTravel = new Vector3(0.07f, 0f, -1.02f);
                slide.Duration = 1.1f;

                return PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        private static Matrix4x4 SolveMap(Vector3 uFl, Vector3 uFr, Vector3 uRl, Vector3 uEye)
        {
            var b = Matrix4x4.identity;
            b.SetColumn(0, BFrontRight - BFrontLeft);
            b.SetColumn(1, BRearLeft - BFrontLeft);
            b.SetColumn(2, BEye - BFrontLeft);
            var u = Matrix4x4.identity;
            u.SetColumn(0, uFr - uFl);
            u.SetColumn(1, uRl - uFl);
            u.SetColumn(2, uEye - uFl);
            Matrix4x4 m = u * b.inverse;
            Vector3 t = uFl - m.MultiplyVector(BFrontLeft);
            m.SetColumn(3, new Vector4(t.x, t.y, t.z, 1f));
            return m;
        }

        // Box given in Blender coordinates (min/max corners) -> BoxCollider in van-root space.
        private static void Box(Transform parent, Matrix4x4 map, string name, Vector3 bMin, Vector3 bMax)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var box = go.AddComponent<BoxCollider>();
            box.center = map.MultiplyPoint3x4((bMin + bMax) * 0.5f);
            Vector3 s = map.MultiplyVector(bMax - bMin);
            box.size = new Vector3(Mathf.Abs(s.x), Mathf.Abs(s.y), Mathf.Abs(s.z));
        }

        private static void BuildBodyColliders(Transform root, Matrix4x4 map)
        {
            var col = new GameObject("Colliders").transform;
            col.SetParent(root, false);
            Box(col, map, "Floor", new(-0.94f, -1.70f, 0.35f), new(0.94f, 2.19f, 0.55f));
            Box(col, map, "Roof", new(-0.80f, -0.99f, 1.98f), new(0.80f, 2.19f, 2.08f));
            Box(col, map, "Nose", new(-0.94f, -2.29f, 0.35f), new(0.94f, -1.70f, 1.08f));
            Box(col, map, "Hood", new(-0.92f, -2.20f, 1.08f), new(0.92f, -1.72f, 1.30f));
            Box(col, map, "Dashboard", new(-0.88f, -1.72f, 0.55f), new(0.88f, -1.40f, 1.30f));
            Box(col, map, "BumperFront", new(-0.97f, -2.42f, 0.28f), new(0.97f, -2.23f, 0.62f));
            Box(col, map, "BumperRear", new(-0.97f, 2.13f, 0.28f), new(0.97f, 2.36f, 0.62f));
            Box(col, map, "LeftWallLow", new(0.89f, -0.44f, 0.55f), new(0.94f, 2.19f, 1.30f));
            Box(col, map, "LeftWallHigh", new(0.80f, -0.44f, 1.30f), new(0.90f, 2.19f, 1.98f));
            Box(col, map, "RightWallLow", new(-0.94f, 0.90f, 0.55f), new(-0.89f, 2.19f, 1.30f));
            Box(col, map, "RightWallHigh", new(-0.90f, 0.90f, 1.30f), new(-0.80f, 2.19f, 1.98f));
            Box(col, map, "RearPillarLeft", new(0.80f, 2.13f, 0.55f), new(0.94f, 2.19f, 1.98f));
            Box(col, map, "RearPillarRight", new(-0.94f, 2.13f, 0.55f), new(-0.80f, 2.19f, 1.98f));
            Box(col, map, "SeatDriver", new(0.26f, -1.06f, 0.55f), new(0.72f, -0.50f, 0.98f));
            Box(col, map, "SeatDriverBack", new(0.26f, -0.62f, 0.98f), new(0.72f, -0.50f, 1.66f));
            Box(col, map, "SeatBench", new(-0.82f, -1.06f, 0.55f), new(-0.10f, -0.50f, 0.98f));
            Box(col, map, "SeatBenchBack", new(-0.82f, -0.62f, 0.98f), new(-0.10f, -0.50f, 1.66f));
            Box(col, map, "HousingRearLeft", new(0.52f, 1.10f, 0.55f), new(0.89f, 2.02f, 0.85f));
            Box(col, map, "HousingRearRight", new(-0.89f, 1.10f, 0.55f), new(-0.52f, 2.02f, 0.85f));

            // Windshield: slanted slab from the roof edge down to the cowl.
            var ws = new GameObject("Windshield").transform;
            ws.SetParent(col, false);
            Vector3 top = map.MultiplyPoint3x4(new Vector3(0f, -0.99f, 2.08f));
            Vector3 bottom = map.MultiplyPoint3x4(new Vector3(0f, -1.69f, 1.38f));
            Vector3 slope = top - bottom;
            Vector3 side = map.MultiplyVector(Vector3.right).normalized;
            Vector3 normal = Vector3.Cross(slope.normalized, side).normalized;
            if (Vector3.Dot(normal, Vector3.up) < 0f) normal = -normal;
            ws.localPosition = (top + bottom) * 0.5f - normal * 0.03f;
            ws.localRotation = Quaternion.LookRotation(slope.normalized, normal);
            var wsBox = ws.gameObject.AddComponent<BoxCollider>();
            wsBox.size = new Vector3(1.72f, 0.06f, slope.magnitude);
        }

        private static WheelCollider MakeWheel(Transform root, string name, Transform visual, float radius)
        {
            var go = new GameObject(name);
            go.transform.SetParent(root, false);
            go.transform.position = visual.position + root.up * 0.1f;
            var w = go.AddComponent<WheelCollider>();
            w.radius = radius;
            w.mass = 25f;
            w.wheelDampingRate = 0.6f;
            w.suspensionDistance = 0.2f;
            w.forceAppPointDistance = 0.15f;
            var spring = new JointSpring { spring = 52000f, damper = 5200f, targetPosition = 0.5f };
            w.suspensionSpring = spring;
            w.forwardFriction = new WheelFrictionCurve
            { extremumSlip = 0.4f, extremumValue = 1f, asymptoteSlip = 0.8f, asymptoteValue = 0.6f, stiffness = 1.5f };
            w.sidewaysFriction = new WheelFrictionCurve
            { extremumSlip = 0.25f, extremumValue = 1f, asymptoteSlip = 0.5f, asymptoteValue = 0.75f, stiffness = 1.7f };
            return w;
        }

        private static VanDoor SetupDoor(Transform model, Transform root, string name, VanDoor.Kind kind, float angle, Vector3 outward)
        {
            Transform t = Find(model, name);
            var mf = t.GetComponent<MeshFilter>();
            var box = t.gameObject.AddComponent<BoxCollider>();
            box.center = mf.sharedMesh.bounds.center;
            box.size = mf.sharedMesh.bounds.size;
            var door = t.gameObject.AddComponent<VanDoor>();
            door.DoorKind = kind;
            door.Van = root;
            door.OpenAngle = angle;
            door.OutwardHint = outward;
            return door;
        }

        private static Transform Find(Transform parent, string name)
        {
            foreach (Transform t in parent.GetComponentsInChildren<Transform>(true))
                if (t.name == name) return t;
            throw new System.InvalidOperationException($"[Van] '{name}' not found in the model");
        }

        // ------------------------------------------------------------------ test scene
        private static void BuildScene(GameObject vanPrefab)
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.3f;
            sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(48f, -35f, 0f);
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.62f, 0.68f, 0.78f);
            RenderSettings.ambientEquatorColor = new Color(0.45f, 0.47f, 0.48f);
            RenderSettings.ambientGroundColor = new Color(0.25f, 0.24f, 0.22f);

            Material ground = SceneMaterial("VanTest_Ground", new Color(0.55f, 0.57f, 0.55f), CheckerTexture());
            ground.mainTextureScale = new Vector2(100f, 100f);
            ground.SetTextureScale("_BaseMap", new Vector2(100f, 100f));
            Material ramp = SceneMaterial("VanTest_Ramp", new Color(0.86f, 0.62f, 0.25f), null);
            Material cone = SceneMaterial("VanTest_Cone", new Color(0.95f, 0.42f, 0.08f), null);
            Material crate = SceneMaterial("VanTest_Crate", new Color(0.55f, 0.40f, 0.25f), null);
            Material wall = SceneMaterial("VanTest_Wall", new Color(0.70f, 0.72f, 0.75f), null);

            var floor = Prim(PrimitiveType.Cube, "Ground", new Vector3(0f, -0.5f, 0f), new Vector3(400f, 1f, 400f), Quaternion.identity, ground);
            floor.isStatic = true;
            for (int i = 0; i < 4; i++)
            {
                float a = i * 90f;
                Vector3 dir = Quaternion.Euler(0f, a, 0f) * Vector3.forward;
                Prim(PrimitiveType.Cube, $"Wall_{i}", dir * 150f + Vector3.up * 1.5f, new Vector3(300f, 3f, 2f), Quaternion.Euler(0f, a, 0f), wall).isStatic = true;
            }
            Prim(PrimitiveType.Cube, "Ramp_Kicker", new Vector3(0f, 0.9f, 45f), new Vector3(8f, 0.6f, 9f), Quaternion.Euler(-12f, 0f, 0f), ramp).isStatic = true;
            Prim(PrimitiveType.Cube, "Ramp_Wide", new Vector3(-30f, 1.2f, 70f), new Vector3(14f, 0.6f, 14f), Quaternion.Euler(-10f, 0f, 0f), ramp).isStatic = true;
            Prim(PrimitiveType.Cube, "Ramp_Side", new Vector3(30f, 0.7f, 75f), new Vector3(10f, 0.6f, 10f), Quaternion.Euler(0f, 0f, 9f), ramp).isStatic = true;
            for (int i = 0; i < 6; i++)
                Prim(PrimitiveType.Cylinder, $"Bump_{i}", new Vector3(-20f, 0f, 15f + i * 5f), new Vector3(0.45f, 4f, 0.45f), Quaternion.Euler(0f, 0f, 90f), wall).isStatic = true;
            for (int i = 0; i < 10; i++)
            {
                var c = Prim(PrimitiveType.Cylinder, $"Cone_{i}", new Vector3(20f, 0.45f, 10f + i * 9f), new Vector3(0.45f, 0.45f, 0.45f), Quaternion.identity, cone);
                c.AddComponent<Rigidbody>().mass = 4f;
            }
            for (int x = 0; x < 3; x++)
            for (int y = 0; y < 3; y++)
            {
                var c = Prim(PrimitiveType.Cube, $"Crate_{x}_{y}", new Vector3(-12f + x * 1.05f, 0.5f + y * 1.01f, 30f), Vector3.one, Quaternion.identity, crate);
                c.AddComponent<Rigidbody>().mass = 30f;
            }

            var van = (GameObject)PrefabUtility.InstantiatePrefab(vanPrefab);
            van.transform.position = new Vector3(0f, 0.05f, 0f);
            for (int i = 0; i < 2; i++)
            {
                var c = Prim(PrimitiveType.Cube, $"CargoCrate_{i}", van.transform.TransformPoint(new Vector3(i * 0.4f - 0.2f, 1.0f, -0.8f - i * 0.7f)), Vector3.one * 0.55f, Quaternion.identity, crate);
                c.AddComponent<Rigidbody>().mass = 15f;
            }

            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.05f;
            cam.fieldOfView = 70f;
            camGo.AddComponent<AudioListener>();
            camGo.transform.position = new Vector3(0f, 3.5f, -8f);
            var rig = camGo.AddComponent<VanCameraRig>();
            rig.Van = van.transform;
            rig.DriverEye = Find(van.transform, "SOCKET_DriverEye");

            var input = van.AddComponent<VanDriveInput>();
            input.FrontLeft = Find(van.transform, "VAN_Door_Front_Left").GetComponent<VanDoor>();
            input.FrontRight = Find(van.transform, "VAN_Door_Front_Right").GetComponent<VanDoor>();
            input.Slide = Find(van.transform, "VAN_Door_Slide").GetComponent<VanDoor>();
            input.RearLeft = Find(van.transform, "VAN_Door_Rear_Left").GetComponent<VanDoor>();
            input.RearRight = Find(van.transform, "VAN_Door_Rear_Right").GetComponent<VanDoor>();
            input.CameraRig = rig;

            EditorSceneManager.SaveScene(scene, ScenePath);
        }

        private static GameObject Prim(PrimitiveType type, string name, Vector3 pos, Vector3 scale, Quaternion rot, Material mat)
        {
            var go = GameObject.CreatePrimitive(type);
            go.name = name;
            go.transform.SetPositionAndRotation(pos, rot);
            go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = mat;
            return go;
        }

        private static Material SceneMaterial(string name, Color color, Texture2D tex)
        {
            string path = $"{Root}/TestScene/{name}.mat";
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", 0.1f);
            if (tex != null) mat.SetTexture("_BaseMap", tex);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static Texture2D CheckerTexture()
        {
            string path = $"{Root}/TestScene/VanTest_Checker.png";
            if (!File.Exists(path))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                var tex = new Texture2D(64, 64, TextureFormat.RGB24, false);
                for (int y = 0; y < 64; y++)
                for (int x = 0; x < 64; x++)
                {
                    bool dark = (x < 32) ^ (y < 32);
                    bool line = x == 0 || y == 0;
                    float v = line ? 0.62f : dark ? 0.80f : 0.92f;
                    tex.SetPixel(x, y, new Color(v, v, v));
                }
                File.WriteAllBytes(path, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(path);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                ti.filterMode = FilterMode.Bilinear;
                ti.wrapMode = TextureWrapMode.Repeat;
                ti.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
    }
}
