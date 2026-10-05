using UnityEngine;

namespace OnlyVolunteers.Operation
{
    /// <summary>
    /// The operating table at the base: takes a carried patient, needs the straps done (hold the use key) before an
    /// operation starts, and lets an unstrapped patient roll off after a few seconds.
    /// </summary>
    public sealed class OperationTable : MonoBehaviour
    {
        [Tooltip("Where the patient lies (position and rotation of the patient root).")]
        [SerializeField] private Transform restPose;
        [Tooltip("Overhead view used during the operation.")]
        [SerializeField] private Transform cameraAnchor;
        [Tooltip("Strap visuals, shown one by one while strapping. Inactive at start.")]
        [SerializeField] private GameObject[] straps = new GameObject[0];
        [SerializeField, Min(0.2f)] private float strapSeconds = 1.2f;
        [Tooltip("An unstrapped patient rolls off the table after this long.")]
        [SerializeField, Min(1f)] private float rollOffSeconds = 6f;
        [SerializeField] private AudioSource sfx;

        private float strapProgress;
        private float looseTime;

        public OperationPatient Patient { get; private set; }
        public Transform CameraAnchor => cameraAnchor;
        public float StrapProgress => strapProgress;
        public float RollOffIn => Patient != null && !Patient.Strapped ? Mathf.Max(0f, rollOffSeconds - looseTime) : 0f;
        public bool Ready => Patient != null && Patient.Strapped;

        public void Configure(Transform rest, Transform anchor, GameObject[] strapVisuals, AudioSource source)
        {
            restPose = rest;
            cameraAnchor = anchor;
            straps = strapVisuals ?? new GameObject[0];
            sfx = source;
        }

        public void Accept(OperationPatient patient)
        {
            Patient = patient;
            patient.LayOn(restPose);
            patient.Jolt();
            strapProgress = 0f;
            looseTime = 0f;
            ShowStraps();
            OperationSfx.Play(sfx, OperationCue.Yelp, 0.4f);
        }

        /// <summary>Called every frame the use key is held on an unstrapped patient. True once strapped.</summary>
        public bool HoldStrap(float deltaTime)
        {
            if (Patient == null || Patient.Strapped) return Patient != null;
            int shownBefore = StrapsShown();
            strapProgress = Mathf.Min(1f, strapProgress + deltaTime / strapSeconds);
            looseTime = 0f;
            if (StrapsShown() > shownBefore) OperationSfx.Play(sfx, OperationCue.Strap);
            ShowStraps();
            if (strapProgress < 1f) return false;
            Patient.SetStrapped(true);
            return true;
        }

        /// <summary>Unstraps and frees the table (a later "carry the body away" step would call this).</summary>
        public OperationPatient Release()
        {
            OperationPatient patient = Patient;
            Patient = null;
            strapProgress = 0f;
            ShowStraps();
            return patient;
        }

        private void Update()
        {
            if (Patient == null) return;
            if (!Patient.OnTable)
            {
                Release();
                return;
            }
            if (Patient.Strapped) return;
            looseTime += Time.deltaTime;
            if (looseTime < rollOffSeconds) return;
            // Comedy beat from the draft: nobody strapped him, so he rolls off and lands on the floor.
            OperationPatient patient = Release();
            patient.Drop(transform.right * 1.6f + Vector3.up * 1.2f);
            patient.Jolt();
            OperationSfx.Play(sfx, OperationCue.Boing);
        }

        private int StrapsShown() => straps.Length == 0 ? 0 : Mathf.FloorToInt(strapProgress * straps.Length + 0.001f);

        private void ShowStraps()
        {
            int shown = StrapsShown();
            for (int i = 0; i < straps.Length; i++)
                if (straps[i] != null) straps[i].SetActive(i < shown);
        }
    }
}
