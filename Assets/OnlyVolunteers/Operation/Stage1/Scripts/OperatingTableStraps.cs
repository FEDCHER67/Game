using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>
    /// The five hinged restraint straps of TABLE-ASTRA-001 v02 (OperatingTableAstra_v02.prefab).
    /// Order: 0 left arm, 1 right arm, 2 left leg, 3 right leg, 4 torso (patient's left/right).
    /// Each strap's pivot is its hinge on the pad edge; opening is a rotation about the strap's local +X
    /// (positive = the inner end lifts and flips up/outward), see table_rest_contract_v01.json.
    /// Purely local presentation: not networked; the caller decides when to open or close.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class OperatingTableStraps : MonoBehaviour
    {
        public const int Count = 5;
        public static readonly string[] Names = { "STRAP_ARM_L", "STRAP_ARM_R", "STRAP_LEG_L", "STRAP_LEG_R", "STRAP_TORSO" };

        [Tooltip("L arm, R arm, L leg, R leg, torso. Found by name under this object when left empty.")]
        [SerializeField] private Transform[] straps = new Transform[Count];
        [Tooltip("Fully open angle per strap (degrees about the strap's local +X).")]
        [SerializeField] private float[] openAngles = { 120f, 120f, 120f, 120f, 120f };
        [SerializeField] private Vector3 hingeAxisLocal = Vector3.right;
        [Tooltip("Smoothing time (seconds) of the open/close motion.")]
        [SerializeField, Min(0.01f)] private float smoothTime = 0.15f;

        private Quaternion[] closedRotation;
        private readonly float[] target = new float[Count];
        private readonly float[] current = new float[Count];
        private readonly float[] velocity = new float[Count];

        public Transform Strap(int index) { Cache(); return straps[index]; }
        public float GetOpen(int index) => target[index];
        public float CurrentOpen(int index) => current[index];

        /// <summary>Smoothly opens (1) or closes (0) one strap; values in between hold a partial opening.</summary>
        public void SetOpen(int index, float open01)
        {
            if (index < 0 || index >= Count) return;
            Cache();
            target[index] = Mathf.Clamp01(open01);
            enabled = true;
        }

        /// <summary>Same as SetOpen but without smoothing (e.g. when restoring a saved table).</summary>
        public void SetOpenImmediate(int index, float open01)
        {
            if (index < 0 || index >= Count) return;
            Cache();
            target[index] = current[index] = Mathf.Clamp01(open01);
            velocity[index] = 0f;
            Apply(index);
        }

        private void Awake() => Cache();

        private void Cache()
        {
            if (closedRotation != null) return;
            if (straps == null || straps.Length != Count) straps = new Transform[Count];
            closedRotation = new Quaternion[Count];
            for (int i = 0; i < Count; i++)
            {
                if (straps[i] == null) straps[i] = FindDeep(transform, Names[i]);
                closedRotation[i] = straps[i] != null ? straps[i].localRotation : Quaternion.identity;
            }
        }

        private void LateUpdate()
        {
            bool moving = false;
            for (int i = 0; i < Count; i++)
            {
                if (Mathf.Abs(current[i] - target[i]) < 0.0005f && Mathf.Abs(velocity[i]) < 0.001f)
                {
                    if (current[i] != target[i]) { current[i] = target[i]; velocity[i] = 0f; Apply(i); }
                    continue;
                }
                current[i] = Mathf.SmoothDamp(current[i], target[i], ref velocity[i], smoothTime);
                Apply(i);
                moving = true;
            }
            if (!moving) enabled = false;
        }

        private void Apply(int i)
        {
            if (straps[i] == null) return;
            float angle = (openAngles != null && i < openAngles.Length ? openAngles[i] : 120f) * current[i];
            straps[i].localRotation = closedRotation[i] * Quaternion.AngleAxis(angle, hingeAxisLocal);
        }

        private static Transform FindDeep(Transform root, string name)
        {
            if (root.name == name) return root;
            for (int i = 0; i < root.childCount; i++)
            {
                var r = FindDeep(root.GetChild(i), name);
                if (r != null) return r;
            }
            return null;
        }
    }
}
