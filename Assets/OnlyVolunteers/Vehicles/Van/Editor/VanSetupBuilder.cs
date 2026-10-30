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
    // Two model layouts: v02 (Van.prefab, the W86 map, VanLab, VanDriveTest; BuildAll) and v05 (Van_v05.prefab, Vadim 30.10:
    // v02's design stretched to 6.15 x 2.16 x 2.6 m, a bulkhead with a mesh window, two front seats; BuildV05Prefab, used
    // by VadimVanLab.RunVanOnly). Building v05 never touches Van.prefab, the v02 model or the shared VAN_* materials (it
    // only adds its own _NoShadow interior materials).
    public static class VanSetupBuilder
    {
        private const string Root = "Assets/OnlyVolunteers/Vehicles/Van";
        private const string MaterialDir = Root + "/Materials";
        private const string ScenePath = "Assets/OnlyVolunteers/Scenes/VanDriveTest.unity";
        public const string V05PrefabPath = Root + "/Prefabs/Van_v05.prefab";

        // One model layout. Blender-space numbers (Z up, -Y forward, +X = vehicle left), as in ArtSource build_van.py.
        private sealed class Layout
        {
            public string ModelPath, PrefabPath;
            // Reference points used to map collider boxes: wheel centres and the driver's eye.
            public Vector3 FrontLeft, FrontRight, RearLeft, Eye;
            public (string name, Vector3 min, Vector3 max)[] Boxes;
            // Slanted slabs (windshield, roof cap): top edge, bottom edge (centre line), width across.
            public (string name, Vector3 top, Vector3 bottom, float width)[] Slabs;
            public float SlideTravel;
            public int InteriorRevision;       // VanInteriorColliders.ModelRevision
            public Bounds? CargoBox;           // VanCargoSpace.LocalBox (null = the component's v02 default)
            public bool UpdateMaterials;       // v02 keeps rewriting the shared VAN_* materials as before; v05 only loads them
            // Interior-only FBX materials remapped to "<name>_NoShadow.mat" copies that receive no shadows (null: none).
            public string[] NoShadowMaterials;
            // Body paint of this layout only: FBX material -> its own asset and colour (null: the shared VAN_* materials).
            public Dictionary<string, (string asset, Color32 color, float smooth)> Paint;
        }

        private static readonly Layout V02 = new()
        {
            ModelPath = Root + "/Model/VAN-TIER0-ASTRA-001_v02.fbx",
            PrefabPath = Root + "/Prefabs/Van.prefab",
            FrontLeft = new(0.80f, -1.60f, 0.37f),
            FrontRight = new(-0.80f, -1.60f, 0.37f),
            RearLeft = new(0.80f, 1.56f, 0.37f),
            Eye = new(0.48f, -0.78f, 1.60f),
            Boxes = new (string, Vector3, Vector3)[]
            {
                ("Floor", new(-0.94f, -1.70f, 0.35f), new(0.94f, 2.19f, 0.55f)),
                ("Roof", new(-0.80f, -0.99f, 1.98f), new(0.80f, 2.19f, 2.08f)),
                ("Nose", new(-0.94f, -2.29f, 0.35f), new(0.94f, -1.70f, 1.08f)),
                ("Hood", new(-0.92f, -2.20f, 1.08f), new(0.92f, -1.72f, 1.30f)),
                ("Dashboard", new(-0.88f, -1.72f, 0.55f), new(0.88f, -1.40f, 1.30f)),
                ("BumperFront", new(-0.97f, -2.42f, 0.28f), new(0.97f, -2.23f, 0.62f)),
                ("BumperRear", new(-0.97f, 2.13f, 0.28f), new(0.97f, 2.36f, 0.62f)),
                ("LeftWallLow", new(0.89f, -0.44f, 0.55f), new(0.94f, 2.19f, 1.30f)),
                ("LeftWallHigh", new(0.80f, -0.44f, 1.30f), new(0.90f, 2.19f, 1.98f)),
                ("RightWallLow", new(-0.94f, 0.90f, 0.55f), new(-0.89f, 2.19f, 1.30f)),
                ("RightWallHigh", new(-0.90f, 0.90f, 1.30f), new(-0.80f, 2.19f, 1.98f)),
                ("RearPillarLeft", new(0.80f, 2.13f, 0.55f), new(0.94f, 2.19f, 1.98f)),
                ("RearPillarRight", new(-0.94f, 2.13f, 0.55f), new(-0.80f, 2.19f, 1.98f)),
                ("SeatDriver", new(0.26f, -1.06f, 0.55f), new(0.72f, -0.50f, 0.98f)),
                ("SeatDriverBack", new(0.26f, -0.62f, 0.98f), new(0.72f, -0.50f, 1.66f)),
                ("SeatBench", new(-0.82f, -1.06f, 0.55f), new(-0.10f, -0.50f, 0.98f)),
                ("SeatBenchBack", new(-0.82f, -0.62f, 0.98f), new(-0.10f, -0.50f, 1.66f)),
                ("HousingRearLeft", new(0.52f, 1.10f, 0.55f), new(0.89f, 2.02f, 0.85f)),
                ("HousingRearRight", new(-0.89f, 1.10f, 0.55f), new(-0.52f, 2.02f, 0.85f)),
            },
            // Windshield: slanted slab from the roof edge down to the cowl.
            Slabs = new (string, Vector3, Vector3, float)[] { ("Windshield", new(0f, -0.99f, 2.08f), new(0f, -1.69f, 1.38f), 1.72f) },
            SlideTravel = 1.02f,
            InteriorRevision = 2,
            CargoBox = null,
            UpdateMaterials = true,
        };

        // v05 (build_van.py --revision 5, Vadim 30.10): v02's design stretched (x 1.15, y 1.1715, z 1.3356 z - 0.178) and the
        // cargo section 0.55 m longer (everything behind y 1.15 moved back): body 5.80 m (6.15 with bumpers) x 2.16 x 2.60,
        // floor 0.557, inner roof 2.54, inner walls x +-1.031 (+-0.879 under the roof), wheels R 0.44 at x +-0.92, axles
        // y -1.874 / 2.378, two front seats (x +-0.10..+-0.90), a bulkhead at y -0.534..-0.494, sliding door y -0.492..1.054
        // up to 2.46, rear doors x +-0.92 from 0.65 to 2.50 at y 3.116. Interior materials get their own _NoShadow copies
        // with shadow receiving off (no shadow shimmer in the cab and the bay).
        private static readonly Layout V05 = new()
        {
            ModelPath = Root + "/Model/VAN-TIER0-ASTRA-001_v05.fbx",
            PrefabPath = V05PrefabPath,
            FrontLeft = new(0.92f, -1.8744f, 0.44f),
            FrontRight = new(-0.92f, -1.8744f, 0.44f),
            RearLeft = new(0.92f, 2.3775f, 0.44f),
            Eye = new(0.552f, -0.9138f, 1.959f),
            Boxes = new (string, Vector3, Vector3)[]
            {
                ("Floor", new(-1.081f, -1.9915f, 0.2895f), new(1.081f, 3.1156f, 0.5566f)),
                ("Roof", new(-0.92f, -1.1598f, 2.54f), new(0.92f, 3.1156f, 2.6f)),
                ("Nose", new(-1.081f, -2.6827f, 0.2895f), new(1.081f, -1.9915f, 1.2644f)),
                ("Hood", new(-1.058f, -2.5773f, 1.2644f), new(1.058f, -2.015f, 1.5583f)),
                ("Dashboard", new(-1.012f, -2.015f, 0.5566f), new(1.012f, -1.6401f, 1.5583f)),
                ("BumperFront", new(-1.1155f, -2.835f, 0.196f), new(1.1155f, -2.6124f, 0.6501f)),
                ("BumperRear", new(-1.1155f, 3.0453f, 0.196f), new(1.1155f, 3.3147f, 0.6501f)),
                ("LeftWallLow", new(1.031f, -0.535f, 0.5566f), new(1.081f, 3.1156f, 1.5583f)),
                ("LeftWallHigh", new(0.8793f, -0.535f, 1.5583f), new(1.041f, 3.1156f, 2.54f)),
                ("RightWallLow", new(-1.081f, 1.0544f, 0.5566f), new(-1.031f, 3.1156f, 1.5583f)),
                ("RightWallHigh", new(-1.041f, 1.0544f, 1.5583f), new(-0.8793f, 3.1156f, 2.54f)),
                ("RearPillarLeft", new(0.92f, 3.0453f, 0.5566f), new(1.081f, 3.1156f, 2.54f)),
                ("RearPillarRight", new(-1.081f, 3.0453f, 0.5566f), new(-0.92f, 3.1156f, 2.54f)),
                ("SeatBench", new(-0.90f, -1.2418f, 0.5566f), new(0.90f, -0.5857f, 1.1309f)),
                ("SeatBenchBack", new(-0.90f, -0.7263f, 1.1309f), new(0.90f, -0.5857f, 1.8f)),
                ("HousingRearLeft", new(0.598f, 1.8275f, 0.5566f), new(1.031f, 2.9275f, 0.99f)),
                ("HousingRearRight", new(-1.031f, 1.8275f, 0.5566f), new(-0.598f, 2.9275f, 0.99f)),
            },
            Slabs = new (string, Vector3, Vector3, float)[] { ("Windshield", new(0f, -1.1598f, 2.6f), new(0f, -1.9798f, 1.6651f), 1.98f) },
            SlideTravel = 1.195f,
            InteriorRevision = 5,
            // floor 0.557 to inner roof 2.54, inner walls (x +-0.92), rear wall (z -2.794) to the bulkhead (z 0.746)
            CargoBox = new Bounds(new Vector3(0f, 1.548f, -1.024f), new Vector3(1.84f, 1.983f, 3.539f)),
            UpdateMaterials = false,
            NoShadowMaterials = new[] { "VAN_Interior", "VAN_Dash", "VAN_Seat", "VAN_Seat_Fabric", "VAN_Interior_Black" },
            // Vadim 30.10: a muted cartoon military olive, matte; bumpers, trim, lights, glass, tyres and hubs stay as they are
            Paint = new()
            {
                ["VAN_Body_Cream"] = ("VAN_Body_Olive_v05", new Color32(118, 128, 82, 255), 0.12f),
                ["VAN_Body_Crease"] = ("VAN_Body_Crease_Olive_v05", new Color32(98, 107, 68, 255), 0.10f),
            },
        };

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
            // v05 interior-only names (their _NoShadow copies are made in ConfigureModel; v02 has none of these)
            ["VAN_Dash"] = (new Color32(62, 63, 66, 255), 0.15f, 1f),
            ["VAN_Interior_Black"] = (new Color32(34, 35, 37, 255), 0.1f, 1f),
            ["VAN_Seat_Fabric"] = (new Color32(112, 117, 128, 255), 0.05f, 1f),
        };
        private static readonly HashSet<string> V05OnlyMaterials = new() { "VAN_Dash", "VAN_Interior_Black", "VAN_Seat_Fabric" };

        [MenuItem("OnlyVolunteers/Van/Rebuild Van Prefab And Test Scene")]
        public static void BuildAll()
        {
            ConfigureModel(V02);
            GameObject prefab = BuildPrefab(V02);
            BuildScene(prefab);
            Debug.Log("[Van] prefab and VanDriveTest scene rebuilt");
        }

        /// <summary>Van_v05.prefab from VAN-TIER0-ASTRA-001_v05.fbx: the same parts and behaviour as Van.prefab, v05 sizes.
        /// No test scene; VadimVanLab.RunVanOnly puts it into the VanOnly scene.</summary>
        [MenuItem("OnlyVolunteers/Van/Build Van v05 Prefab")]
        public static GameObject BuildV05Prefab()
        {
            ConfigureModel(V05);
            GameObject prefab = BuildPrefab(V05);
            Debug.Log("[Van] " + V05.PrefabPath + " rebuilt");
            return prefab;
        }

        private static void ConfigureModel(Layout layout)
        {
            Directory.CreateDirectory(MaterialDir);
            var importer = (ModelImporter)AssetImporter.GetAtPath(layout.ModelPath);
            if (importer == null) throw new FileNotFoundException("[Van] model not imported: " + layout.ModelPath);
            importer.animationType = ModelImporterAnimationType.None;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            foreach (var kv in Materials)
            {
                if (layout.NoShadowMaterials == null && V05OnlyMaterials.Contains(kv.Key)) continue; // v02 keeps its remaps
                Material m = layout.Paint != null && layout.Paint.TryGetValue(kv.Key, out var paint)
                    ? GetOrCreateMaterial(paint.asset, (paint.color, paint.smooth, 1f))
                    : layout.NoShadowMaterials != null && System.Array.IndexOf(layout.NoShadowMaterials, kv.Key) >= 0
                    ? NoShadowMaterial(kv.Key, kv.Value)
                    : GetOrCreateMaterial(kv.Key, kv.Value, layout.UpdateMaterials);
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), kv.Key), m);
            }
            importer.SaveAndReimport();
        }

        // "<name>_NoShadow.mat": the interior twin of a VAN_* material that receives no shadows. Inside the van every surface is
        // in the body's own shadow, and the shadow-map edges and filtering on it crawl and shimmer while the van moves.
        private static Material NoShadowMaterial(string name, (Color32 color, float smooth, float alpha) spec)
        {
            string path = $"{MaterialDir}/{name}_NoShadow.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            Color c = spec.color;
            c.a = 1f;
            mat.SetColor("_BaseColor", c);
            mat.SetFloat("_Smoothness", spec.smooth);
            mat.SetFloat("_Metallic", 0f);
            mat.SetFloat("_ReceiveShadows", 0f);
            mat.EnableKeyword("_RECEIVE_SHADOWS_OFF");
            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static Material GetOrCreateMaterial(string name, (Color32 color, float smooth, float alpha) spec, bool update = true)
        {
            string path = $"{MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat != null && !update) return mat;
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

        private static GameObject BuildPrefab(Layout layout)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(layout.PrefabPath));
            var root = new GameObject("Van");
            try
            {
                var modelAsset = AssetDatabase.LoadAssetAtPath<GameObject>(layout.ModelPath);
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
                Matrix4x4 map = SolveMap(layout, fl.position, fr.position, rl.position, eye.position);

                var body = root.AddComponent<Rigidbody>();
                body.mass = 1800f;
                body.linearDamping = 0.02f;
                body.angularDamping = 0.35f;
                body.interpolation = RigidbodyInterpolation.Interpolate;
                body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;

                BuildBodyColliders(root.transform, map, layout);
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
                slide.SlideTravel = new Vector3(0.07f, 0f, -layout.SlideTravel);
                slide.Duration = 0.6f; // NPC capture stage 1: the driver's button opens it in ~0.6 s (was 1.1)

                // NPC capture stage 1: the cargo bay as a carrier (riding, loading), and the extra colliders (steps under
                // the cargo doors, cab partition, thicker walls) with every van collider on layer Vehicle. Baked here; the
                // same component rebuilds them idempotently at runtime on older prefab instances.
                var space = root.AddComponent<VanCargoSpace>();
                if (layout.CargoBox is Bounds cargo) space.LocalBox = cargo;
                var interior = root.AddComponent<VanInteriorColliders>();
                interior.ModelRevision = layout.InteriorRevision;
                interior.Build();

                return PrefabUtility.SaveAsPrefabAsset(root, layout.PrefabPath);
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        private static Matrix4x4 SolveMap(Layout layout, Vector3 uFl, Vector3 uFr, Vector3 uRl, Vector3 uEye)
        {
            var b = Matrix4x4.identity;
            b.SetColumn(0, layout.FrontRight - layout.FrontLeft);
            b.SetColumn(1, layout.RearLeft - layout.FrontLeft);
            b.SetColumn(2, layout.Eye - layout.FrontLeft);
            var u = Matrix4x4.identity;
            u.SetColumn(0, uFr - uFl);
            u.SetColumn(1, uRl - uFl);
            u.SetColumn(2, uEye - uFl);
            Matrix4x4 m = u * b.inverse;
            Vector3 t = uFl - m.MultiplyVector(layout.FrontLeft);
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

        private static void BuildBodyColliders(Transform root, Matrix4x4 map, Layout layout)
        {
            var col = new GameObject("Colliders").transform;
            col.SetParent(root, false);
            foreach ((string name, Vector3 min, Vector3 max) in layout.Boxes)
                Box(col, map, name, min, max);

            // Slanted slabs (the windshield): from the top edge down to the bottom edge.
            foreach ((string name, Vector3 bTop, Vector3 bBottom, float width) in layout.Slabs)
            {
                var ws = new GameObject(name).transform;
                ws.SetParent(col, false);
                Vector3 top = map.MultiplyPoint3x4(bTop);
                Vector3 bottom = map.MultiplyPoint3x4(bBottom);
                Vector3 slope = top - bottom;
                Vector3 side = map.MultiplyVector(Vector3.right).normalized;
                Vector3 normal = Vector3.Cross(slope.normalized, side).normalized;
                if (Vector3.Dot(normal, Vector3.up) < 0f) normal = -normal;
                ws.localPosition = (top + bottom) * 0.5f - normal * 0.03f;
                ws.localRotation = Quaternion.LookRotation(slope.normalized, normal);
                var wsBox = ws.gameObject.AddComponent<BoxCollider>();
                wsBox.size = new Vector3(width, 0.06f, slope.magnitude);
            }
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
