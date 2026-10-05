using UnityEngine;

namespace OnlyVolunteers.Operation
{
    /// <summary>
    /// Prototype stand-in for a delivered NPC: one rigid body that can be carried, put on the table and strapped in.
    /// The visual child wriggles (less when strapped, less again when someone holds it down); everything drawn on the
    /// body during the operation is parented to that child, so the incision moves with the wriggle.
    /// </summary>
    [RequireComponent(typeof(Rigidbody))]
    public sealed class OperationPatient : MonoBehaviour
    {
        [Tooltip("Grade the NPC arrived with (capture/delivery quality). The operation can only lower it.")]
        [SerializeField] private OrganQuality condition = OrganQuality.Good;
        [SerializeField, Min(0)] private int kidneysLeft = 2;
        [SerializeField] private Transform visual;
        [SerializeField] private Transform mouth;
        [Tooltip("Incision end points for the kidney, children of the visual.")]
        [SerializeField] private Transform kidneyIncisionStart;
        [SerializeField] private Transform kidneyIncisionEnd;
        [Tooltip("Side-to-side wriggle when strapped and not held down, metres. No anaesthesia in the prototype (canon 43-44).")]
        [SerializeField, Min(0f)] private float strappedWiggle = 0.035f;
        [SerializeField, Min(0f)] private float looseWiggle = 0.09f;

        private Rigidbody body;
        private Vector3 visualRest;
        private Vector3 mouthRest;
        private float jolt;
        private float scream;

        public OrganQuality Condition => condition;
        public int KidneysLeft => kidneysLeft;
        public Transform Visual => visual;
        public Transform KidneyIncisionStart => kidneyIncisionStart;
        public Transform KidneyIncisionEnd => kidneyIncisionEnd;
        public bool Carried { get; private set; }
        public bool OnTable { get; private set; }
        public bool Strapped { get; private set; }

        /// <summary>0..1: how firmly someone presses the patient down this frame (the "holder" role).</summary>
        public float HeldDown { get; set; }

        /// <summary>0..1: how loudly the patient complains right now (mouth size); set by the mini-game.</summary>
        public float Scream
        {
            get => scream;
            set => scream = Mathf.Clamp01(value);
        }

        public void Configure(OrganQuality arrivedCondition, int kidneys, Transform visualRoot, Transform mouthTransform,
            Transform incisionStart, Transform incisionEnd)
        {
            condition = arrivedCondition;
            kidneysLeft = Mathf.Max(0, kidneys);
            visual = visualRoot;
            mouth = mouthTransform;
            kidneyIncisionStart = incisionStart;
            kidneyIncisionEnd = incisionEnd;
        }

        private void Awake()
        {
            body = GetComponent<Rigidbody>();
            if (visual != null) visualRest = visual.localPosition;
            if (mouth != null) mouthRest = mouth.localScale;
        }

        private void Update()
        {
            float amplitude = Carried ? 0.02f : OnTable ? (Strapped ? strappedWiggle : looseWiggle) : 0.01f;
            amplitude *= 1f - 0.75f * HeldDown;
            amplitude += jolt * 0.06f;
            jolt = Mathf.MoveTowards(jolt, 0f, Time.deltaTime * 3f);
            float t = Time.time;
            if (visual != null)
            {
                Vector3 offset = new Vector3(0f, Mathf.Abs(Mathf.Sin(t * 7.3f)) * amplitude * 0.3f,
                    (Mathf.Sin(t * 9.1f) + 0.45f * Mathf.Sin(t * 23.7f)) * amplitude);
                visual.localPosition = visualRest + offset;
            }
            if (mouth != null)
            {
                float open = 0.25f + 0.75f * Mathf.Max(scream, jolt) + (OnTable && !Strapped ? 0.4f * Mathf.Abs(Mathf.Sin(t * 11f)) : 0f);
                mouth.localScale = new Vector3(mouthRest.x, mouthRest.y * (0.4f + 2.2f * open), mouthRest.z);
            }
            HeldDown = 0f;
        }

        /// <summary>A short flinch: bigger wriggle and an open mouth for a moment.</summary>
        public void Jolt() => jolt = 1f;

        public void BeginCarry(Transform holder, Vector3 localOffset)
        {
            Carried = true;
            OnTable = false;
            body.isKinematic = true;
            body.detectCollisions = false;
            transform.SetParent(holder, true);
            transform.localPosition = localOffset;
            transform.localRotation = Quaternion.identity; // lies across the carrier's arms, head to the right
        }

        public void Drop(Vector3 push)
        {
            transform.SetParent(null, true);
            Carried = false;
            OnTable = false;
            Strapped = false;
            body.isKinematic = false;
            body.detectCollisions = true;
            body.linearVelocity = push;
            body.angularVelocity = Random.insideUnitSphere * 2f;
        }

        public void LayOn(Transform restPose)
        {
            transform.SetParent(null, true);
            Carried = false;
            OnTable = true;
            Strapped = false;
            body.isKinematic = true;
            body.detectCollisions = true;
            transform.SetPositionAndRotation(restPose.position, restPose.rotation);
        }

        public void SetStrapped(bool strapped)
        {
            Strapped = strapped;
            if (strapped) Jolt();
        }

        /// <summary>Takes one kidney out of the stock. False when none is left.</summary>
        public bool TakeKidney()
        {
            if (kidneysLeft <= 0) return false;
            kidneysLeft--;
            return true;
        }
    }
}
