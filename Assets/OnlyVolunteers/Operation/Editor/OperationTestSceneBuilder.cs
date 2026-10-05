using OnlyVolunteers.Inventory;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Operation
{
    // OnlyVolunteers/Operation/Build Operation Test Scene: a garage "base" room built from primitives with the operating
    // table, an instrument cart, a cooler, a delivered patient lying on the floor and a test walker with LocalInventory.
    // Writes Operation/Scenes/OperationTest.unity and its materials under Operation/Generated (both builder output).
    public static class OperationTestSceneBuilder
    {
        private const string Root = "Assets/OnlyVolunteers/Operation";
        private const string ScenePath = Root + "/Scenes/OperationTest.unity";
        private const string MaterialDir = Root + "/Generated";
        private const string ItemDatabasePath = "Assets/OnlyVolunteers/Inventory/Items/ItemDatabase.asset";
        private const string KidneyItemPath = "Assets/OnlyVolunteers/Inventory/Items/Item_Kidney.asset";

        // Patient on the table: root at the rest pose, lying along +X (head at +X), face up.
        private const float TableTop = 0.94f;
        private const float BodyRadius = 0.24f;

        [MenuItem("OnlyVolunteers/Operation/Build Operation Test Scene")]
        private static void Build()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            var database = AssetDatabase.LoadAssetAtPath<ItemDatabase>(ItemDatabasePath);
            var kidney = AssetDatabase.LoadAssetAtPath<ItemDefinition>(KidneyItemPath);
            if (database == null || kidney == null)
            {
                Debug.LogError($"[OperationTest] missing {ItemDatabasePath} or {KidneyItemPath}");
                return;
            }
            EnsureFolder(Root, "Scenes");
            EnsureFolder(Root, "Generated");

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            BuildRoom();
            OperationTable table = BuildTable(kidney, out OperationSession session);
            BuildCart();
            BuildPatient(new Vector3(2.6f, 0.35f, 1.6f), Quaternion.Euler(0f, 35f, 0f));
            BuildPlayer(database, table, session);

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log($"[OperationTest] built {ScenePath}. Play: pick up the patient (E), put him on the table (E), " +
                      "hold E to strap, E to operate.");
        }

        private static void BuildRoom()
        {
            var sun = new GameObject("Directional Light").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 0.7f;
            sun.transform.rotation = Quaternion.Euler(55f, -30f, 0f);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.42f, 0.42f, 0.46f);

            var room = new GameObject("Garage").transform;
            Box(room, "Floor", new Vector3(0f, -0.05f, 0f), new Vector3(9f, 0.1f, 9f), Mat("Floor", new Color(0.46f, 0.46f, 0.44f)), true);
            Material wall = Mat("Wall", new Color(0.62f, 0.66f, 0.6f));
            Box(room, "Wall_N", new Vector3(0f, 1.4f, 4.5f), new Vector3(9f, 2.8f, 0.2f), wall, true);
            Box(room, "Wall_S", new Vector3(0f, 1.4f, -4.5f), new Vector3(9f, 2.8f, 0.2f), wall, true);
            Box(room, "Wall_E", new Vector3(4.5f, 1.4f, 0f), new Vector3(0.2f, 2.8f, 9f), wall, true);
            Box(room, "Wall_W", new Vector3(-4.5f, 1.4f, 0f), new Vector3(0.2f, 2.8f, 9f), wall, true);

            // One bare bulb over the table: the "garage surgery" look of the early base.
            var bulb = new GameObject("Lamp").AddComponent<Light>();
            bulb.type = LightType.Point;
            bulb.color = new Color(1f, 0.9f, 0.72f);
            bulb.intensity = 3f;
            bulb.range = 6f;
            bulb.transform.position = new Vector3(0f, 2.5f, 0f);
            Shape(bulb.transform, PrimitiveType.Sphere, "Bulb", Vector3.zero, Vector3.one * 0.12f, Mat("Bulb", new Color(1f, 0.95f, 0.75f)));
        }

        private static OperationTable BuildTable(ItemDefinition kidney, out OperationSession session)
        {
            var root = new GameObject("OperatingTable");
            Material metal = Mat("TableMetal", new Color(0.55f, 0.62f, 0.6f));
            Box(root.transform, "Top", new Vector3(0f, TableTop - 0.04f, 0f), new Vector3(2.1f, 0.08f, 0.8f), metal, true);
            for (int i = 0; i < 4; i++)
            {
                float x = i < 2 ? -0.95f : 0.95f;
                float z = i % 2 == 0 ? -0.33f : 0.33f;
                Box(root.transform, $"Leg{i}", new Vector3(x, (TableTop - 0.08f) * 0.5f, z), new Vector3(0.06f, TableTop - 0.08f, 0.06f), metal, true);
            }

            var rest = new GameObject("RestPose").transform;
            rest.SetParent(root.transform, false);
            rest.localPosition = new Vector3(0f, TableTop + BodyRadius, 0f);

            var anchor = new GameObject("CameraAnchor").transform;
            anchor.SetParent(root.transform, false);
            anchor.localPosition = new Vector3(-0.05f, 2.2f, -0.6f);
            Vector3 lookAt = new Vector3(-0.08f, TableTop + BodyRadius * 2f, 0f);
            anchor.rotation = Quaternion.LookRotation(lookAt - anchor.position);

            Material strapMat = Mat("Strap", new Color(0.12f, 0.1f, 0.09f));
            float[] strapX = { -0.68f, -0.45f, 0.42f };
            var straps = new GameObject[strapX.Length];
            for (int i = 0; i < strapX.Length; i++)
            {
                var strap = new GameObject($"Strap{i}").transform;
                strap.SetParent(root.transform, false);
                float top = TableTop + BodyRadius * 2f + 0.01f;
                Box(strap, "Over", new Vector3(strapX[i], top, 0f), new Vector3(0.07f, 0.02f, 0.52f), strapMat, false);
                Box(strap, "SideA", new Vector3(strapX[i], (top + TableTop) * 0.5f, 0.27f), new Vector3(0.07f, top - TableTop, 0.02f), strapMat, false);
                Box(strap, "SideB", new Vector3(strapX[i], (top + TableTop) * 0.5f, -0.27f), new Vector3(0.07f, top - TableTop, 0.02f), strapMat, false);
                strap.gameObject.SetActive(false);
                straps[i] = strap.gameObject;
            }

            var audio = root.AddComponent<AudioSource>();
            audio.playOnAwake = false;
            audio.spatialBlend = 0f;
            var table = root.AddComponent<OperationTable>();
            table.Configure(rest, anchor, straps, audio);
            session = root.AddComponent<OperationSession>();
            session.Configure(kidney, audio);
            return table;
        }

        // Decoration only: the four tool props that exist in ArtSource (SCALPEL/BONESAW/DUCTTAPE/COOLER-ASTRA-001),
        // as primitives until their models are imported.
        private static void BuildCart()
        {
            var cart = new GameObject("InstrumentCart").transform;
            cart.position = new Vector3(0.2f, 0f, 1.0f);
            Material metal = Mat("TableMetal", new Color(0.55f, 0.62f, 0.6f));
            Box(cart, "Top", new Vector3(0f, 0.78f, 0f), new Vector3(0.9f, 0.04f, 0.45f), metal, true);
            Box(cart, "Leg", new Vector3(0f, 0.38f, 0f), new Vector3(0.06f, 0.76f, 0.06f), metal, true);

            Material steel = Mat("Steel", new Color(0.82f, 0.85f, 0.9f));
            Material handle = Mat("Handle", new Color(0.25f, 0.3f, 0.36f));
            Box(cart, "Scalpel_Blade", new Vector3(-0.32f, 0.81f, 0f), new Vector3(0.04f, 0.01f, 0.02f), steel, false);
            Box(cart, "Scalpel_Handle", new Vector3(-0.24f, 0.81f, 0f), new Vector3(0.12f, 0.015f, 0.02f), handle, false);
            Box(cart, "Saw_Blade", new Vector3(0f, 0.81f, 0.05f), new Vector3(0.3f, 0.01f, 0.08f), steel, false);
            Box(cart, "Saw_Handle", new Vector3(0.19f, 0.83f, 0.05f), new Vector3(0.09f, 0.04f, 0.05f), Mat("SawHandle", new Color(0.75f, 0.2f, 0.15f)), false);
            Shape(cart, PrimitiveType.Cylinder, "DuctTape", new Vector3(0.33f, 0.83f, -0.08f), new Vector3(0.12f, 0.025f, 0.12f), Mat("Tape", new Color(0.62f, 0.63f, 0.6f)));
            Label(cart, "СКАЛЬПЕЛЬ  ПИЛА  СКОТЧ", new Vector3(0f, 1.0f, 0f));

            var cooler = new GameObject("Cooler").transform;
            cooler.position = new Vector3(1.3f, 0f, 1.0f);
            Box(cooler, "Body", new Vector3(0f, 0.2f, 0f), new Vector3(0.55f, 0.4f, 0.35f), Mat("CoolerBody", new Color(0.92f, 0.93f, 0.95f)), true);
            Box(cooler, "Lid", new Vector3(0f, 0.42f, 0f), new Vector3(0.58f, 0.05f, 0.38f), Mat("CoolerLid", new Color(0.2f, 0.45f, 0.85f)), true);
            Label(cooler, "ХОЛОДИЛЬНИК", new Vector3(0f, 0.7f, 0f));
        }

        private static void BuildPatient(Vector3 position, Quaternion rotation)
        {
            var root = new GameObject("Patient");
            root.transform.SetPositionAndRotation(position, rotation);
            var body = root.AddComponent<Rigidbody>();
            body.mass = 70f;
            body.linearDamping = 0.3f;
            body.angularDamping = 0.8f;
            var collider = root.AddComponent<CapsuleCollider>();
            collider.direction = 0;
            collider.radius = BodyRadius;
            collider.height = 1.95f;
            collider.center = new Vector3(0.02f, 0f, 0f);

            var visual = new GameObject("Visual").transform;
            visual.SetParent(root.transform, false);
            Material skin = Mat("PatientSkin", new Color(0.95f, 0.72f, 0.6f));
            Material shirt = Mat("PatientShirt", new Color(0.25f, 0.55f, 0.75f));
            Material pants = Mat("PatientPants", new Color(0.25f, 0.27f, 0.35f));
            Material dark = Mat("PatientEyes", new Color(0.05f, 0.05f, 0.06f));
            Material mouthMat = Mat("PatientMouth", new Color(0.45f, 0.08f, 0.12f));

            // A rounded sausage body: torso (shirt), legs (trousers), head; capsules lie along X.
            Shape(visual, PrimitiveType.Capsule, "Torso", new Vector3(0.05f, 0f, 0f), new Vector3(0.48f, 0.42f, 0.48f), shirt, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Capsule, "Legs", new Vector3(-0.58f, -0.02f, 0f), new Vector3(0.42f, 0.38f, 0.42f), pants, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Sphere, "Head", new Vector3(0.72f, 0.02f, 0f), Vector3.one * 0.42f, skin);
            Shape(visual, PrimitiveType.Capsule, "ArmL", new Vector3(0.12f, 0.02f, 0.28f), new Vector3(0.12f, 0.28f, 0.12f), skin, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Capsule, "ArmR", new Vector3(0.12f, 0.02f, -0.28f), new Vector3(0.12f, 0.28f, 0.12f), skin, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Sphere, "EyeL", new Vector3(0.8f, 0.2f, 0.07f), new Vector3(0.05f, 0.03f, 0.05f), dark);
            Shape(visual, PrimitiveType.Sphere, "EyeR", new Vector3(0.8f, 0.2f, -0.07f), new Vector3(0.05f, 0.03f, 0.05f), dark);
            // Rotated so the mouth's local Y (the axis OperationPatient scales to "open" it) runs head-to-feet.
            Transform mouth = Shape(visual, PrimitiveType.Cube, "Mouth", new Vector3(0.66f, 0.218f, 0f), new Vector3(0.012f, 0.03f, 0.1f), mouthMat,
                Quaternion.Euler(0f, 0f, 90f));

            // Kidney incision on the belly, a little off-centre (the second kidney mirrors it in Z).
            float surface = Mathf.Sqrt(BodyRadius * BodyRadius - 0.09f * 0.09f);
            var incisionStart = new GameObject("KidneyIncisionStart").transform;
            incisionStart.SetParent(visual, false);
            incisionStart.localPosition = new Vector3(-0.26f, surface, 0.09f);
            var incisionEnd = new GameObject("KidneyIncisionEnd").transform;
            incisionEnd.SetParent(visual, false);
            incisionEnd.localPosition = new Vector3(0.1f, surface, 0.09f);

            root.AddComponent<OperationPatient>().Configure(OrganQuality.Good, 2, visual, mouth, incisionStart, incisionEnd);
        }

        private static void BuildPlayer(ItemDatabase database, OperationTable table, OperationSession session)
        {
            var root = new GameObject("TestPlayer");
            root.transform.SetPositionAndRotation(new Vector3(-2.6f, 0.05f, -2.2f), Quaternion.Euler(0f, 50f, 0f));
            var controller = root.AddComponent<CharacterController>();
            controller.height = 1.8f;
            controller.radius = 0.35f;
            controller.center = new Vector3(0f, 0.9f, 0f);

            var cameraObject = new GameObject("Main Camera");
            cameraObject.tag = "MainCamera";
            cameraObject.transform.SetParent(root.transform, false);
            cameraObject.transform.localPosition = new Vector3(0f, 1.6f, 0f);
            var view = cameraObject.AddComponent<Camera>();
            view.nearClipPlane = 0.05f;
            view.fieldOfView = 70f;
            cameraObject.AddComponent<AudioListener>();

            root.AddComponent<LocalInventory>().Configure(database, 6, 12, 0);
            root.AddComponent<InventoryHud>();
            root.AddComponent<InventoryInput>();
            root.AddComponent<OperationTestPlayer>().Configure(view, table, session);
        }

        private static void Box(Transform parent, string name, Vector3 localPosition, Vector3 size, Material material, bool keepCollider)
        {
            Transform box = Shape(parent, PrimitiveType.Cube, name, localPosition, size, material, Quaternion.identity, keepCollider);
            box.gameObject.isStatic = keepCollider;
        }

        private static Transform Shape(Transform parent, PrimitiveType type, string name, Vector3 localPosition, Vector3 scale, Material material) =>
            Shape(parent, type, name, localPosition, scale, material, Quaternion.identity);

        private static Transform Shape(Transform parent, PrimitiveType type, string name, Vector3 localPosition, Vector3 scale, Material material,
            Quaternion localRotation, bool keepCollider = false)
        {
            GameObject go = GameObject.CreatePrimitive(type);
            go.name = name;
            if (!keepCollider) Object.DestroyImmediate(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPosition;
            go.transform.localRotation = localRotation;
            go.transform.localScale = scale;
            go.GetComponent<MeshRenderer>().sharedMaterial = material;
            return go.transform;
        }

        private static void Label(Transform parent, string text, Vector3 localPosition)
        {
            var go = new GameObject($"Label_{text}");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPosition;
            var mesh = go.AddComponent<TextMesh>();
            mesh.text = text;
            mesh.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            go.GetComponent<MeshRenderer>().sharedMaterial = mesh.font.material;
            mesh.fontSize = 48;
            mesh.characterSize = 0.012f;
            mesh.anchor = TextAnchor.MiddleCenter;
            mesh.color = new Color(0.1f, 0.1f, 0.1f);
        }

        private static Material Mat(string name, Color color)
        {
            string path = $"{MaterialDir}/{name}.mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(material, path);
            }
            material.SetColor("_BaseColor", color);
            material.SetFloat("_Smoothness", 0.15f);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void EnsureFolder(string parent, string name)
        {
            if (!AssetDatabase.IsValidFolder($"{parent}/{name}")) AssetDatabase.CreateFolder(parent, name);
        }
    }
}
