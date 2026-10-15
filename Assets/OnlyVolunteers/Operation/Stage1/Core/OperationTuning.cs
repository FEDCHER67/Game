using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>One authored authority for the stage-one game rules. Amounts are fictional, normalized game units.
    /// v02 retune (2026-10-15): readable dose window, generous cutting, short cord snips, softer pull.</summary>
    [CreateAssetMenu(menuName = "OnlyVolunteers/Operation/Stage 1 tuning")]
    public sealed class OperationTuning : ScriptableObject
    {
        [Header("Patient / placement")]
        public float patientMass = 12f;
        public int bloodBagCount = 3;
        public float alignmentSeconds = 0.6f;
        [Tooltip("Max distance from PatientRest for a released patient to start aligning (the pad box check comes first).")]
        public float placementRadius = 1.2f;
        public float padTop = 0.6634f;
        public Vector3 padHalfExtents = new Vector3(0.42f, 0.5f, 1.05f);
        public float tableReach = 3.2f;
        public float enterDistance = 2.2f;
        public float toolReach = 2.5f;
        public float dazedSeconds = 4f;
        public float escapeSeconds = 7f;
        public float rescueSeconds = 8f;
        [Header("Anesthesia (units: 1.0 = the centre of the suitable range)")]
        public float dosePerSecond = 0.5f;
        public float suitableMinimum = 0.8f;
        [Tooltip("Above this the patient shows comic distress (eyes roll, twitch, 'хватит?..'). Not lethal yet.")]
        public float suitableMaximum = 1.25f;
        public float overdoseAbove = 2.25f;
        public float sleepSeconds = 90f;
        public float residualPerSecond = 1f / 90f;
        public float syringeCapacity = 3f;
        [Tooltip("Bottle stock that refills the syringe each time it is put back into its slot.")]
        public float anesthesiaStock = 9f;
        public float syringeStock = 10f; // v01 field
        [Header("Blood / death")]
        public float bloodSeconds = 4.5f;
        public float unsealedBloodSeconds = 120f;
        public float sealSeconds = 1f;
        public int bloodValue = 50;
        public int weakenedPortion = 2;
        public int fatalPortion = 3;
        public float firstKidneyChance = 0.1f;
        public float secondKidneyChance = 0.2f;
        public float liverChance = 0.3f;
        public float bloodChancePerPortion = 0.1f;
        public float corpseGraceSeconds = 45f;
        public float corpseGradeSeconds = 40f;
        public int earlyOverdoseLoss = 2;
        [Header("Incisions (marker-local metres)")]
        public float neatTolerance = 0.02f;
        public float cutTolerance = 0.05f;
        [Tooltip("A stroke may start this far (in incision lengths) before the start point...")]
        public float cutStartSlack = 0.2f;
        [Tooltip("...and up to this far past the current progress.")]
        public float cutResumeWindow = 0.3f;
        [Tooltip("Speed cap of the blade along the guide, m/s. A normal drag must never outrun it for long.")]
        public float cutSpeed = 0.7f;
        public float sloppyFraction = 0.5f;
        public float offLineWeight = 0.5f;
        public float[] incisionLengths = { 0.075f, 0.075f, 0.075f };
        [Tooltip("True: the guide runs across the body (marker X) instead of along it (marker Y).")]
        public bool[] guideAcross = { false, false, false };
        public Vector2[] openingHalfSize = { new(0.027f, 0.0455f), new(0.027f, 0.0455f), new(0.029f, 0.0455f) };
        public Vector2[] organHalfSize = { new(0.018f, 0.031f), new(0.018f, 0.031f), new(0.021f, 0.032f) };
        public float organLift = 0.01f;
        [Tooltip("How far past the opening rim the cords reach onto the skin (longer = easier to hit).")]
        public float cordOverhang = 0.026f;
        public float[] cordPhase = { 40f, -40f, 90f };
        [Header("Cords / pull / impact")]
        public float connectionSeconds = 0.3f;
        public float cordHitRadius = 0.045f;
        public float organHitRadius = 0.08f;
        public float contactRadius = 0.07f;
        public float pullDistance = 0.2f;
        public float pullResponse = 6f;
        public float springSpeed = 0.4f;
        public float abruptSpeed = 0.9f;
        public float pullScreenFraction = 0.22f;
        public float impactSpeed = 2.4f;
        public float impactCooldown = 0.6f;
        public float organItemScale = 0.5f;
        public int sloppyLoss = 1;
        public int directCutLoss = 2;
        public int abruptLoss = 1;
        public int impactLoss = 1;
        [Header("Tools")]
        public float toolReturnSeconds = 2f;
        public float toolFlySeconds = 0.35f;
        public float toolHover = 0.025f;
        [Header("Network / presentation")]
        public float inputInterval = 0.05f;
        public float inputTimeout = 0.5f;
        public float snapshotInterval = 0.066f;
        public float saveInterval = 5f;
        public float cameraFieldOfView = 50f;
        public float cameraBlendSeconds = 0.35f;
        public float maxZoom = 0.62f;
        public float magnifierSize = 220f;   // v01 field
        public float magnifierZoom = 2.2f;   // v01 field
        [Tooltip("Use cameraPosition/cameraLookAt (table-local) instead of the table's CameraAnchor. The props v02 anchor sees the " +
                 "incisions at a grazing angle; this steeper framing keeps the whole patient, the openings and the stand readable.")]
        public bool overrideCameraAnchor = true;
        public Vector3 cameraPosition = new Vector3(-1.2f, 2.45f, 0.1f);
        public Vector3 cameraLookAt = new Vector3(-0.08f, 0.55f, -0.12f);
        public Vector3 patientRest = new Vector3(0, 0.66f, 0f); // table_rest_contract_v01
        public Vector3 workSurface = new Vector3(0, 0.655f, 0); // v01 field
        public Vector3 trayPosition = new Vector3(0.66f, 0f, 0.05f);
        public Vector3 floorSpawn = new Vector3(-1.15f, 0.05f, -0.1f);
        public Vector3 toolRackOffset = new Vector3(0.2f, 0.12f, 0);   // v01 field
        public float toolRackSpacing = 0.3f;                          // v01 field
        public Vector3 outputRackOffset = new Vector3(-0.2f, 0.12f, -0.35f); // v01 field
        public Vector3 outputRackSpacing = new Vector3(0.23f, 0, 0.35f);     // v01 field
        public float incisionLength = 0.12f;          // v01 field; v02 uses incisionLengths
        public float connectionRadius = 0.045f;       // v01 field
        public float incisionSurfaceTolerance = 0.06f;
        [Tooltip("Girth in metres: L arm, R arm, L leg, R leg, torso.")]
        public float[] strapGirth = { 0.25f, 0.25f, 0.35f, 0.35f, 0.9f };
        public int[] connections = { 2, 2, 3 };
        [Tooltip("Known-grade test fixtures; not a production NPC distribution.")]
        public int[] intrinsicGrades = { 4, 3, 2 };
        public Vector3[] restraintPositions = { new(-0.38f, 0, 0.35f), new(0.38f, 0, 0.35f), new(-0.16f, 0, -0.65f), new(0.16f, 0, -0.65f), new(0, 0, 0.03f) }; // v01 field

        public float IncisionLength(int organ) => incisionLengths != null && organ >= 0 && organ < incisionLengths.Length ? incisionLengths[organ] : incisionLength;
        public Vector3 ConnectionOffset(int organ, int connection)
        {
            OperationGeometry.Cord(this, organ, connection, out var attach, out var rim);
            return (attach + rim) * 0.5f;
        }
        /// <summary>Hold time (s) that reaches a residual amount from zero, ignoring decay.</summary>
        public float HoldSecondsFor(float amount) => amount / Mathf.Max(0.0001f, dosePerSecond);
    }
}
