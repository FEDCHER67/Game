using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>Put on the root of an item's visual (view-model proxy and/or world prefab). Declares how hands hold
    /// it (spec §4): a pose id, the main-hand socket and an optional off-hand socket. Socket child names:
    /// <c>Grip_Main</c>, <c>Grip_Off</c>, optional <c>Tip</c> (needle / blade point for use effects).
    /// A socket's pose is where the hand's grip point must be (same axes as Hand_R_Grip / Hand_L_Grip): origin in the
    /// centre of the closed fist, +Z out of the knuckles (forearm direction), +Y out of the thumb side along a gripped
    /// handle, +X out of the back of the right hand (palm of the left). Identity = handshake fist, handle upright.</summary>
    [DisallowMultipleComponent]
    public sealed class ItemGrip : MonoBehaviour
    {
        public const string MainSocketName = "Grip_Main", OffSocketName = "Grip_Off", TipName = "Tip";

        public HandPoseId pose = HandPoseId.GripCylinder;
        public HandSide mainHand = HandSide.Right;
        [Tooltip("Both hands carry it (cooler, body bag): blocks other hand actions; the off hand IKs to Grip_Off.")]
        public bool twoHanded;
        public Transform mainSocket;
        public Transform offSocket;
        public Transform tip;
        [Header("First-person tweak (view space, added to the pose's main-hand target)")]
        public Vector3 viewOffset;
        public Vector3 viewEuler;
        [Tooltip("Scale of the FP proxy only (view models are often drawn slightly smaller).")]
        [Min(0.01f)] public float viewScale = 1f;
        [Tooltip("0 light .. 1 heavy: more sway lag, slower bob.")]
        [Range(0f, 1f)] public float heft;

        public Pose ViewTweak => new Pose(viewOffset, Quaternion.Euler(viewEuler));
        public HandSide OffHand => mainHand == HandSide.Right ? HandSide.Left : HandSide.Right;
        public bool HasOffSocket => offSocket != null;

        /// <summary>Socket pose relative to this item's root: rotation in root space, offset in world units at the
        /// item's current scale (so <see cref="PlaceByMainGrip"/> stays exact for a scaled proxy).</summary>
        public Pose SocketLocal(HandSide side)
        {
            Transform s = side == mainHand ? mainSocket : offSocket;
            if (s == null) return new Pose(Vector3.zero, Quaternion.identity);
            Quaternion inv = Quaternion.Inverse(transform.rotation);
            return new Pose(inv * (s.position - transform.position), inv * s.rotation);
        }

        /// <summary>Places the item so its main socket lies on <paramref name="mainGripWorld"/>.</summary>
        public void PlaceByMainGrip(Pose mainGripWorld)
        {
            Pose p = HandsMath.ItemPoseFromGrip(mainGripWorld, SocketLocal(mainHand));
            transform.SetPositionAndRotation(p.position, p.rotation);
        }

        public bool TryGetSocketWorld(HandSide side, out Pose socket)
        {
            Transform s = side == mainHand ? mainSocket : offSocket;
            socket = s != null ? new Pose(s.position, s.rotation) : default;
            return s != null;
        }

        public void FindSockets()
        {
            if (mainSocket == null) mainSocket = FindDeep(transform, MainSocketName);
            if (offSocket == null) offSocket = FindDeep(transform, OffSocketName);
            if (tip == null) tip = FindDeep(transform, TipName);
        }

        private void Awake() => FindSockets();
        private void Reset() => FindSockets();

        private static Transform FindDeep(Transform root, string name)
        {
            for (int i = 0; i < root.childCount; i++)
            {
                Transform c = root.GetChild(i);
                if (c.name == name) return c;
                Transform d = FindDeep(c, name);
                if (d != null) return d;
            }
            return null;
        }
    }
}
