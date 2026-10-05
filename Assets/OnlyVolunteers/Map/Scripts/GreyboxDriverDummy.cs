using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // The driver, visible in the cab (canon section 151), offline stand-in for the chase view: the real player stays
    // switched off while driving (GreyboxVanSeat) until it can sit in a seat socket (draft A7/B7, with the network work).
    // Grey-box primitives under the van, no colliders: a seated capsule body with thighs and shins, two arms to the
    // steering wheel, and a head (with a nose box) that turns toward where the van camera looks, clamped to +-HeadYawLimit.
    // Shown while someone drives; the head hides in the cockpit view, where the camera sits inside it.
    [RequireComponent(typeof(VanController))]
    public sealed class GreyboxDriverDummy : MonoBehaviour
    {
        private const string RootName = "DriverDummy";

        public GreyboxVanSeat Seat;
        public VanCameraRig ViewCamera;
        [Tooltip("Van-local centre of the seated body capsule (driver seat, left-hand drive).")]
        public Vector3 SeatPoint = new(-0.49f, 1.05f, 0.76f);
        [Tooltip("Van-local centre of the head.")]
        public Vector3 HeadPoint = new(-0.49f, 1.62f, 0.70f);
        [Tooltip("Van-local steering wheel hub, used when the van has no SteeringWheel transform.")]
        public Vector3 WheelFallback = new(-0.49f, 1.25f, 1.2f);
        public float HeadYawLimit = 70f;
        public float HeadTurnSpeed = 360f;
        public Color Clothes = new(0.30f, 0.36f, 0.48f);
        public Color Skin = new(0.93f, 0.76f, 0.62f);

        private Transform _root;
        private Transform _head;
        private float _yaw;

        private void Start() => Build();

        private void Build()
        {
            _root = transform.Find(RootName);
            if (_root != null) Destroy(_root.gameObject); // a reload in Play mode: build afresh
            _root = new GameObject(RootName).transform;
            _root.SetParent(transform, false);

            (Mesh capsule, Mesh sphere, Mesh cube, Material baseMaterial) = Primitives();
            var clothes = new Material(baseMaterial) { name = "DriverDummy_Clothes", color = Clothes };
            var skin = new Material(baseMaterial) { name = "DriverDummy_Skin", color = Skin };

            // Body: a 0.9 m capsule from the cushion to the shoulders; thighs forward, shins down to the pedals.
            Part("Body", capsule, clothes, _root, SeatPoint, Quaternion.identity, new Vector3(0.4f, 0.45f, 0.36f));
            Part("Thighs", cube, clothes, _root, SeatPoint + new Vector3(0f, -0.05f, 0.24f), Quaternion.identity, new Vector3(0.36f, 0.16f, 0.46f));
            Part("Shins", cube, clothes, _root, SeatPoint + new Vector3(0f, -0.27f, 0.45f), Quaternion.identity, new Vector3(0.32f, 0.44f, 0.13f));

            // Arms: shoulders to the wheel rim, a hand either side of the hub.
            Vector3 hub = WheelFallback;
            if (TryGetComponent(out VanController van) && van.SteeringWheel != null)
            {
                Vector3 local = transform.InverseTransformPoint(van.SteeringWheel.position);
                if (Vector3.Distance(local, SeatPoint) < 1.2f) hub = local; // a wild pivot falls back to the default
            }
            for (int side = -1; side <= 1; side += 2)
            {
                Vector3 shoulder = SeatPoint + new Vector3(0.19f * side, 0.36f, 0f);
                Vector3 hand = hub + new Vector3(0.17f * side, 0f, 0f);
                Vector3 arm = hand - shoulder;
                Part(side < 0 ? "ArmLeft" : "ArmRight", cube, clothes, _root, (shoulder + hand) * 0.5f,
                    Quaternion.LookRotation(arm.normalized, Vector3.up), new Vector3(0.09f, 0.09f, arm.magnitude));
            }

            // Head: a pivot that turns, with the skull and a nose box showing where it looks.
            _head = new GameObject("Head").transform;
            _head.SetParent(_root, false);
            _head.localPosition = HeadPoint;
            Part("Skull", sphere, skin, _head, Vector3.zero, Quaternion.identity, Vector3.one * 0.26f);
            Part("Nose", cube, skin, _head, new Vector3(0f, -0.01f, 0.13f), Quaternion.identity, new Vector3(0.05f, 0.05f, 0.07f));

            _root.gameObject.SetActive(false);
        }

        private void LateUpdate()
        {
            if (_root == null) return;
            bool show = Seat != null && Seat.Driving;
            if (_root.gameObject.activeSelf != show) _root.gameObject.SetActive(show);
            if (!show) return;
            bool cockpit = ViewCamera != null && ViewCamera.CurrentMode == VanCameraRig.Mode.Cockpit;
            if (_head.gameObject.activeSelf == cockpit) _head.gameObject.SetActive(!cockpit);
            if (ViewCamera == null) return;
            // The van camera's look direction in van space -> head yaw, clamped like a neck.
            Vector3 look = transform.InverseTransformDirection(ViewCamera.transform.forward);
            float target = look.x * look.x + look.z * look.z > 1e-4f ? Mathf.Atan2(look.x, look.z) * Mathf.Rad2Deg : 0f;
            target = Mathf.Clamp(target, -HeadYawLimit, HeadYawLimit);
            _yaw = Mathf.MoveTowardsAngle(_yaw, target, HeadTurnSpeed * Time.deltaTime);
            _head.localRotation = Quaternion.Euler(0f, _yaw, 0f);
        }

        private static void Part(string name, Mesh mesh, Material material, Transform parent, Vector3 localPosition, Quaternion localRotation, Vector3 scale)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.SetLocalPositionAndRotation(localPosition, localRotation);
            go.transform.localScale = scale;
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial = material;
        }

        private static Mesh _capsule, _sphere, _cube;
        private static Material _material;

        // Unity's primitive meshes and the pipeline's default material, taken from throwaway primitives created away from
        // the van and destroyed at once, so no collider ever joins the van's compound body.
        private static (Mesh, Mesh, Mesh, Material) Primitives()
        {
            if (_capsule == null) _capsule = Take(PrimitiveType.Capsule);
            if (_sphere == null) _sphere = Take(PrimitiveType.Sphere);
            if (_cube == null) _cube = Take(PrimitiveType.Cube);
            return (_capsule, _sphere, _cube, _material);
        }

        private static Mesh Take(PrimitiveType type)
        {
            GameObject temp = GameObject.CreatePrimitive(type);
            Mesh mesh = temp.GetComponent<MeshFilter>().sharedMesh;
            if (_material == null) _material = temp.GetComponent<MeshRenderer>().sharedMaterial;
            DestroyImmediate(temp);
            return mesh;
        }
    }
}
