using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Animated van door. Hinge doors swing about the van's up axis through their pivot;
    // the sliding door first pops outward, then runs back along its rail. Motion is expressed
    // in van-local space, so it stays correct while the van drives.
    public sealed class VanDoor : MonoBehaviour
    {
        public enum Kind { Hinge, Slide }

        public Kind DoorKind = Kind.Hinge;
        public Transform Van;
        [Tooltip("Hinge: opening angle in degrees. Direction is picked so the free edge moves toward OutwardHint.")]
        public float OpenAngle = 70f;
        [Tooltip("Hinge: van-local direction the free edge should move when opening.")]
        public Vector3 OutwardHint = Vector3.right;
        [Tooltip("Slide: van-local offset after the outward pop.")]
        public Vector3 SlidePop = new(0.07f, 0f, 0f);
        [Tooltip("Slide: van-local offset when fully open.")]
        public Vector3 SlideTravel = new(0.07f, 0f, -1.02f);
        [Range(0.05f, 0.6f)] public float PopFraction = 0.22f;
        public float Duration = 0.85f;

        public bool IsOpen => _target > 0.5f;
        public float Openness => _t;

        private Vector3 _closedLocalPos;
        private Quaternion _closedLocalRot;
        private float _signedAngle;
        private float _t;
        private float _target;

        private void Awake()
        {
            _closedLocalPos = transform.localPosition;
            _closedLocalRot = transform.localRotation;
            if (Van == null)
                Van = GetComponentInParent<Rigidbody>() != null ? GetComponentInParent<Rigidbody>().transform : transform.root;
            _signedAngle = DoorKind == Kind.Hinge ? ChooseHingeSign() : 0f;
        }

        public void Toggle() => _target = IsOpen ? 0f : 1f;
        public void Open() => _target = 1f;
        public void Close() => _target = 0f;

        private void Update()
        {
            if (Mathf.Approximately(_t, _target))
                return;
            _t = Mathf.MoveTowards(_t, _target, Time.deltaTime / Mathf.Max(0.01f, Duration));
            Apply(_t);
        }

        private void Apply(float t)
        {
            Transform parent = transform.parent;
            if (DoorKind == Kind.Hinge)
            {
                Vector3 axis = parent.InverseTransformDirection(Van.up);
                transform.localRotation = Quaternion.AngleAxis(_signedAngle * Ease(t), axis) * _closedLocalRot;
                return;
            }

            Vector3 offset = t < PopFraction
                ? Vector3.Lerp(Vector3.zero, SlidePop, Ease(t / PopFraction))
                : Vector3.Lerp(SlidePop, SlideTravel, Ease((t - PopFraction) / (1f - PopFraction)));
            transform.localPosition = _closedLocalPos + parent.InverseTransformVector(Van.TransformVector(offset));
        }

        private static float Ease(float x)
        {
            x = Mathf.Clamp01(x);
            return x * x * (3f - 2f * x);
        }

        // Pick +angle or -angle so the door's centre moves toward OutwardHint (works for any import axes).
        private float ChooseHingeSign()
        {
            Renderer r = GetComponent<Renderer>();
            if (r == null)
                return OpenAngle;
            Vector3 pivot = transform.position;
            Vector3 centre = r.bounds.center;
            Vector3 outward = Van.TransformDirection(OutwardHint);
            Vector3 plus = Quaternion.AngleAxis(OpenAngle, Van.up) * (centre - pivot);
            Vector3 minus = Quaternion.AngleAxis(-OpenAngle, Van.up) * (centre - pivot);
            return Vector3.Dot(plus - (centre - pivot), outward) >= Vector3.Dot(minus - (centre - pivot), outward)
                ? OpenAngle
                : -OpenAngle;
        }
    }
}
