using System.IO;
using OnlyVolunteers.Map;
using OnlyVolunteers.Player.Physics;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // The police half of "Build Map Look + Gameplay" (MapGreyboxBuilder.PlaceGameplay with the CrowdDirector): a "Police"
    // object with the PoliceDirector (PoliceConfig + police_vNN.asset, re-baked first when missing or made from another
    // plan file), the station respawn point, the cars in the station lot's spaces (car_police from the vehicle kit wrapped
    // in a Rigidbody, PoliceCarMotor and PoliceUnit; a siren AudioSource, two roof lights) and two crew Buddies per car
    // (inactive, inside). The static parked police cars of the look are left out of the play build (PropScatterer).
    // The menu toggle switches all of it off (back to the crowd's placeholder police hook).
    public static class MapPolicePlacer
    {
        private const string PrefKey = "OnlyVolunteers.Map.Police";
        private const string MenuPath = "OnlyVolunteers/Map/Police: place police in Build Map Look + Gameplay";
        private const string CarPrefab = "Assets/OnlyVolunteers/Art/Map/Prefabs/CARS/car_police.prefab";
        private const string RedLight = "Assets/OnlyVolunteers/Map/Look/Materials/Look_mat_red__D23B32.mat";
        private const string BlueLight = "Assets/OnlyVolunteers/Map/Look/Materials/Look_mat_neon_blue__3D7BFF.mat";
        private const string BodyMaterialPath = PoliceBaker.DataDir + "/PoliceCarBody.asset";
        // car_police.prefab: a 1.72 x 1.57 x 4.075 m box from the ground up. The physics box starts 0.38 m up (the springs
        // carry the car; the box must not drag on kerbs).
        private static readonly Vector3 BodyCenter = new(0f, 0.955f, 0.0125f), BodySize = new(1.72f, 1.15f, 4.075f);

        public static bool Enabled
        {
            get => EditorPrefs.GetBool(PrefKey, true);
            set => EditorPrefs.SetBool(PrefKey, value);
        }

        [MenuItem(MenuPath, false, 201)]
        private static void Toggle()
        {
            Enabled = !Enabled;
            Debug.Log($"[Police] Build Map Look + Gameplay will {(Enabled ? "place the police (cars, crews, director)" : "not place the police (placeholder hook only)")}.");
        }

        [MenuItem(MenuPath, true)]
        private static bool ToggleValidate()
        {
            Menu.SetChecked(MenuPath, Enabled);
            return true;
        }

        /// <summary>The police data of plan 'revision' (null = the newest plan): baked now when missing or stale (any bake
        /// input changed: the plan, look or crowd file, PoliceConfig, the van prefab's pace numbers).</summary>
        public static PoliceMapData EnsureData(string revision, out string status)
        {
            string rev = revision;
            string plan = revision != null ? PoliceBaker.PlanPath(revision) : PoliceBaker.LatestPlan(out rev);
            if (revision == null && rev != null) Debug.LogWarning($"[Police] no plan revision given: using the newest plan, {rev}.");
            if (plan == null || !File.Exists(plan))
            {
                status = "no plan";
                return null;
            }
            string path = PoliceBaker.DataPath(rev);
            var data = AssetDatabase.LoadAssetAtPath<PoliceMapData>(path);
            string hash = PoliceBaker.InputsHash(rev, plan, PoliceBaker.EnsureConfig());
            if (data != null && data.InputsHash == hash && data.NodeCount > 0)
            {
                status = "inputs hash ok";
                return data;
            }
            if (data != null)
                Debug.Log($"[Police] {path}: bake inputs changed (plan / look / crowd / PoliceConfig / van; hash {data.InputsHash ?? "none"}, now {hash}): baking again.");
            data = PoliceBaker.Bake(true, rev);
            status = data != null ? "baked now" : "bake failed";
            return data;
        }

        /// <summary>revision: the plan the scene is built from ("v12"); null = the newest plan.</summary>
        /// <summary>Null (and a logged error, nothing half-placed left behind) when the data or the placement fails: the
        /// caller then keeps the crowd's placeholder police hook.</summary>
        internal static GameObject Place(string revision, MapGreyboxBuilder.GameplayGround ground, GameObject[] buddies, GrabPhysicsProfile grabProfile, bool sea)
        {
            GameObject placed = null;
            try
            {
                placed = PlaceUnchecked(revision, ground, buddies, grabProfile, sea);
                return placed;
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[Police] placing the police failed ({e.GetType().Name}: {e.Message}); no police in this build.\n{e.StackTrace}");
                GameObject partial = placed != null ? placed : GameObject.Find("Police");
                if (partial != null && partial.GetComponent<PoliceDirector>() != null) Object.DestroyImmediate(partial);
                return null;
            }
        }

        private static GameObject PlaceUnchecked(string revision, MapGreyboxBuilder.GameplayGround ground, GameObject[] buddies, GrabPhysicsProfile grabProfile, bool sea)
        {
            PoliceConfig config = PoliceBaker.EnsureConfig();
            PoliceMapData data = EnsureData(revision, out string status);
            if (data == null || data.NodeCount == 0 || buddies == null || buddies.Length == 0)
            {
                Debug.LogError($"[Police] no police data ({status}; OnlyVolunteers/Map/Police/Bake Police Data) or no Buddy prefabs; no police placed.");
                return null;
            }
            var root = new GameObject("Police");
            var director = root.AddComponent<PoliceDirector>();
            director.Config = config;
            director.Data = data;
            var respawn = new GameObject("Station_Respawn").transform;
            respawn.SetParent(root.transform, false);
            respawn.SetPositionAndRotation(new Vector3(data.Respawn.x, ground.Height(data.Respawn.x, data.Respawn.y), data.Respawn.y),
                                           Quaternion.Euler(0f, data.RespawnYaw, 0f));
            director.Respawn = respawn;

            var carPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(CarPrefab);
            if (carPrefab == null) Debug.LogWarning($"[Police] {CarPrefab} missing: police cars are grey boxes.");
            PhysicsMaterial body = BodyMaterial();
            var crews = new GameObject("Crews").transform;
            crews.SetParent(root.transform, false);
            int cars = Mathf.Max(0, config.Cars), crew = 0;
            for (int i = 0; i < cars; i++)
            {
                Vector3 stall = data.Stalls.Length > 0 ? data.Stalls[Mathf.Min(i, data.Stalls.Length - 1)] : new Vector3(data.Entrance.x, data.Entrance.y, 0f);
                Vector2 fwd = new(Mathf.Sin(stall.z * Mathf.Deg2Rad), Mathf.Cos(stall.z * Mathf.Deg2Rad));
                // Like the look's parked cars: 0.85 m back from the space's centre, facing the aisle.
                Vector2 p = new Vector2(stall.x, stall.y) - fwd * 0.85f;
                if (i >= data.Stalls.Length && data.Stalls.Length > 0) p += new Vector2(fwd.y, -fwd.x) * 3.3f * (i - data.Stalls.Length + 1);
                var pose = new Vector3(p.x, ground.Height(p.x, p.y) + 0.05f, p.y);
                PoliceUnit unit = Car(root.transform, i, carPrefab, body, pose, stall.z, sea);
                unit.Stall = Mathf.Min(i, Mathf.Max(0, data.Stalls.Length - 1));
                unit.Crew = new PoliceOfficer[2];
                for (int k = 0; k < 2; k++)
                {
                    GameObject npc = MapGreyboxBuilder.SpawnCrowdNpc(buddies[(i * 2 + k) % buddies.Length], $"PoliceCrew_{i + 1}_{(k == 0 ? "Thin" : "Fat")}",
                                                                     pose, stall.z, grabProfile, sea);
                    npc.transform.SetParent(crews, true);
                    var gnpc = npc.GetComponent<GreyboxNpc>();
                    gnpc.WalkerScareRadius = 0f;
                    gnpc.VanScareRadius = 0f;
                    var officer = npc.AddComponent<PoliceOfficer>();
                    officer.Fat = k == 1;
                    var so = new SerializedObject(officer);
                    so.FindProperty("_inside").boolValue = true;
                    so.ApplyModifiedPropertiesWithoutUndo();
                    npc.SetActive(false);
                    unit.Crew[k] = officer;
                    crew++;
                }
            }
            Debug.Log($"[Police] placed: {data.Revision}, station {data.StationId}, {cars} cars, {crew} crew, data {data.name} ({status})");
            return root;
        }

        private static PoliceUnit Car(Transform parent, int index, GameObject prefab, PhysicsMaterial body, Vector3 position, float yaw, bool sea)
        {
            var car = new GameObject($"PoliceCar_{index + 1}") { layer = OvLayers.Vehicle };
            car.transform.SetParent(parent, false);
            car.transform.SetPositionAndRotation(position, Quaternion.Euler(0f, yaw, 0f));
            var rb = car.AddComponent<Rigidbody>();
            rb.mass = 1300f;
            var box = car.AddComponent<BoxCollider>();
            box.center = BodyCenter;
            box.size = BodySize;
            box.sharedMaterial = body;
            if (prefab != null)
            {
                var visual = (GameObject)PrefabUtility.InstantiatePrefab(prefab, car.transform);
                visual.transform.localPosition = Vector3.zero;
                visual.transform.localRotation = Quaternion.identity;
                // A moving car: no static flags (the kit prop is static), no collider of its own (the root's box is the body).
                foreach (Transform t in visual.GetComponentsInChildren<Transform>(true))
                {
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, 0);
                    t.gameObject.layer = OvLayers.Vehicle;
                }
                foreach (Collider c in visual.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
            }
            else
            {
                var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                cube.name = "Body";
                Object.DestroyImmediate(cube.GetComponent<Collider>());
                cube.transform.SetParent(car.transform, false);
                cube.transform.localPosition = new Vector3(0f, 0.8f, 0f);
                cube.transform.localScale = new Vector3(1.72f, 1.5f, 4.07f);
            }
            car.AddComponent<PoliceCarMotor>();
            var unit = car.AddComponent<PoliceUnit>();
            unit.Index = index;
            var siren = car.AddComponent<AudioSource>();
            siren.playOnAwake = false;
            siren.loop = true;
            siren.spatialBlend = 1f;
            siren.minDistance = 6f;
            siren.maxDistance = 160f;
            siren.rolloffMode = AudioRolloffMode.Linear;
            siren.volume = 0.55f;
            unit.Siren = siren;
            unit.Lights = new[]
            {
                Light(car.transform, "Light_Red", new Vector3(-0.32f, 1.62f, -0.15f), RedLight),
                Light(car.transform, "Light_Blue", new Vector3(0.32f, 1.62f, -0.15f), BlueLight),
            };
            var label = new GameObject("Label");
            label.transform.SetParent(car.transform, false);
            label.transform.localPosition = new Vector3(0f, 2.5f, 0f);
            var text = label.AddComponent<TextMesh>();
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            label.GetComponent<MeshRenderer>().sharedMaterial = text.font.material;
            text.fontSize = 48;
            text.characterSize = 0.05f;
            text.anchor = TextAnchor.MiddleCenter;
            text.color = new Color(1f, 0.5f, 0.4f);
            text.text = "";
            label.AddComponent<GreyboxBillboard>();
            unit.Label = text;
            if (sea) car.AddComponent<SeaReturnTracker>();
            return unit;
        }

        private static Renderer Light(Transform car, string name, Vector3 local, string material)
        {
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.name = name;
            cube.layer = OvLayers.Vehicle;
            Object.DestroyImmediate(cube.GetComponent<Collider>());
            cube.transform.SetParent(car, false);
            cube.transform.localPosition = local;
            cube.transform.localScale = new Vector3(0.32f, 0.12f, 0.22f);
            var r = cube.GetComponent<Renderer>();
            var mat = AssetDatabase.LoadAssetAtPath<Material>(material);
            if (mat != null) r.sharedMaterial = mat;
            r.enabled = false;
            return r;
        }

        // Low friction: a car pushed along a wall slides instead of sticking (the springs, not the box, touch the road).
        private static PhysicsMaterial BodyMaterial()
        {
            var mat = AssetDatabase.LoadAssetAtPath<PhysicsMaterial>(BodyMaterialPath);
            if (mat != null) return mat;
            mat = new PhysicsMaterial("PoliceCarBody")
            {
                dynamicFriction = 0.2f, staticFriction = 0.2f, bounciness = 0.05f,
                frictionCombine = PhysicsMaterialCombine.Minimum, bounceCombine = PhysicsMaterialCombine.Average,
            };
            AssetDatabase.CreateAsset(mat, BodyMaterialPath);
            return mat;
        }
    }
}
