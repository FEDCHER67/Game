using OnlyVolunteers.Map.Dev;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map
{
    public static class BuddyLocomotionPreviewBuilder
    {
        public const string ScenePath = "Assets/OnlyVolunteers/Scenes/Map/Buddy_Locomotion_v01.unity";

        [MenuItem("Tools/Only Volunteers/Characters/Build Locomotion Preview")]
        public static void Build()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.65f, 0.7f, 0.8f);
            RenderSettings.fog = false;
            var light = new GameObject("Soft key").AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.8f;
            light.shadows = LightShadows.Soft;
            light.transform.rotation = Quaternion.Euler(40f, -35f, 0f);

            Material floor = Material("Floor", new Color(0.23f, 0.29f, 0.34f));
            Material marks = Material("Metre marks", new Color(0.48f, 0.55f, 0.6f));
            Box("Ground", new Vector3(0, -0.1f, 8), new Vector3(40, 0.2f, 60), floor);
            for (int z = -20; z <= 35; z++)
                Box("Metre " + z, new Vector3(0, 0.001f, z), new Vector3(8, 0.002f, 0.018f), marks, false);

            var preview = new GameObject("Locomotion Preview").AddComponent<BuddyLocomotionPreview>();
            preview.Actors = new Animator[2];
            for (int i = 0; i < 2; i++)
            {
                var root = new GameObject(i == 0 ? "Player A" : "Comparison B");
                root.transform.position = new Vector3(i == 0 ? -0.8f : 0.8f, 0, 0);
                string path = "Assets/OnlyVolunteers/Characters/SausageBuddy/SausageBuddy_" + (i == 0 ? "A" : "B") + ".prefab";
                var visual = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path), root.transform);
                preview.Actors[i] = visual.GetComponent<Animator>();
                preview.Actors[i].Play("Idle", 0, 0f);
                preview.Actors[i].Update(0f);
                if (i == 0)
                {
                    var capsule = root.AddComponent<CharacterController>();
                    capsule.height = 1.7f;
                    capsule.radius = 0.28f;
                    capsule.skinWidth = 0.01f;
                    capsule.center = new Vector3(0, 0.85f, 0);
                    preview.Player = root.AddComponent<GreyboxWalker>();
                    preview.Player.enabled = false;
                    capsule.enabled = false;
                }
            }
            Camera camera = new GameObject("Main Camera").AddComponent<Camera>();
            camera.tag = "MainCamera";
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0.12f, 0.16f, 0.2f);
            camera.fieldOfView = 36f;
            camera.nearClipPlane = 0.05f;
            camera.farClipPlane = 100f;
            camera.transform.position = new Vector3(3.8f, 2.5f, 5f);
            camera.transform.LookAt(new Vector3(0, 0.9f, 0));
            camera.gameObject.AddComponent<AudioListener>();
            preview.PreviewCamera = camera;
            preview.Follow = camera.gameObject.AddComponent<GreyboxFollowCamera>();
            preview.Follow.Target = preview.Player.transform;
            preview.Follow.Distance = 4.5f;
            preview.Follow.Height = 1f;
            preview.Follow.enabled = false;
            preview.Player.Follow = preview.Follow;
            preview.Player.CameraTransform = camera.transform;
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), ScenePath);
        }

        private static Material Material(string name, Color colour)
        {
            string path = "Assets/OnlyVolunteers/Characters/SausageBuddy/Animations/Preview_" + name.Replace(' ', '_') + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(material, path);
            }
            material.color = colour;
            material.SetFloat("_Smoothness", 0.1f);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void Box(string name, Vector3 position, Vector3 scale, Material material, bool collider = true)
        {
            var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
            box.name = name;
            box.transform.SetPositionAndRotation(position, Quaternion.identity);
            box.transform.localScale = scale;
            box.GetComponent<Renderer>().sharedMaterial = material;
            if (!collider) Object.DestroyImmediate(box.GetComponent<Collider>());
        }
    }
}
