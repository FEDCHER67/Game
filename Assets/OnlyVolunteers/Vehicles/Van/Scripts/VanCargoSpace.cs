using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // The van's cargo bay as a carrier: a box in van-root space between the floor (0.55) and the roof (1.98), the inner
    // walls (x +-0.80), the rear doors (z -2.19) and the cab partition (z 0.45). Pure data plus queries, no collider:
    // the grey-box rider (players) and the cargo logic (NPC bodies) ask it whether a point is inside and how fast the
    // van moves at that point. Works with a runtime AddComponent (grey-box scene) or on the prefab (VanSetupBuilder).
    [DisallowMultipleComponent]
    public sealed class VanCargoSpace : MonoBehaviour, ICarrier
    {
        // Every enabled cargo bay; riders scan this instead of searching the scene each tick.
        public static readonly List<VanCargoSpace> All = new();

        [Tooltip("Cargo volume in van-root space (centre, size).")]
        public Bounds LocalBox = new(new Vector3(0f, 1.265f, -0.87f), new Vector3(1.60f, 1.43f, 2.64f));

        private Rigidbody _body;

        public Rigidbody Body => _body != null ? _body : _body = GetComponentInParent<Rigidbody>();
        public Transform Space => transform;
        public bool Upright => Vector3.Dot(transform.up, Vector3.up) > 0.3f;

        // Domain reload may be off in the editor: start every play session with an empty list.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => All.Clear();

        private void OnEnable()
        {
            if (!All.Contains(this)) All.Add(this);
        }

        private void OnDisable() => All.Remove(this);

        /// <summary>Whether a world point lies inside the box grown by margin metres on every side.</summary>
        public bool Contains(Vector3 world, float margin = 0f)
        {
            Vector3 d = ToLocal(world) - LocalBox.center;
            Vector3 half = LocalBox.extents;
            return Mathf.Abs(d.x) <= half.x + margin && Mathf.Abs(d.y) <= half.y + margin && Mathf.Abs(d.z) <= half.z + margin;
        }

        // Van-root space <-> world on the van body's physics pose when the body sits on this transform (stage 1, chunk 3):
        // the callers compare physics poses in FixedUpdate (NPC bodies, the KCC's transient position), and the transform
        // of an interpolated body may still show the last drawn pose there (up to one tick of travel, ~0.2 m at 40 km/h).
        public Vector3 ToLocal(Vector3 world)
        {
            Rigidbody body = Body;
            return body != null && body.transform == transform
                ? Quaternion.Inverse(body.rotation) * (world - body.position)
                : transform.InverseTransformPoint(world);
        }

        public Vector3 ToWorld(Vector3 local)
        {
            Rigidbody body = Body;
            return body != null && body.transform == transform ? body.position + body.rotation * local : transform.TransformPoint(local);
        }

        public Quaternion Rotation
        {
            get
            {
                Rigidbody body = Body;
                return body != null && body.transform == transform ? body.rotation : transform.rotation;
            }
        }

        /// <summary>Velocity of the van at a world point (linear plus spin), the reference for "at rest" inside.</summary>
        public Vector3 PointVelocity(Vector3 world) => Body != null ? Body.GetPointVelocity(world) : Vector3.zero;

        private void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(0.2f, 0.9f, 0.4f, 0.6f);
            Gizmos.matrix = transform.localToWorldMatrix;
            Gizmos.DrawWireCube(LocalBox.center, LocalBox.size);
        }
    }
}
