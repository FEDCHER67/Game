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
        [Tooltip("Round 3 (Fedya): the torso strap is removed for now; only the four limb straps hold him. True brings it back " +
                 "(5 straps, the torso alone holds him, as in stage 1).")]
        public bool torsoStrap = false;
        [Tooltip("Awake on the table with a free hand: seconds that hand needs to unbuckle the next closed strap (procedural " +
                 "for now; per-strap escape clips can be plugged into the Unbuckled cue).")]
        public float unbuckleSeconds = 5f;
        [Tooltip("Round 3: suturing speed along the incision line, m/s of seam.")]
        public float sutureSpeed = 0.35f;
        [Tooltip("Round 3: stitches of the seam (OperationSutured_v05 has SUTURE_STITCH_01..20).")]
        public int sutureStitches = 20;
        [Tooltip("Round 3: the approved sutured state (OperationSutured_v05.fbx, the INC_ABDOMEN frame of the opening).")]
        public GameObject suturedModel;
        [Tooltip("Length of Op_EscapeFall_v01: the root stays on PatientRest while it plays.")]
        public float escapeFallSeconds = 3f;
        [Tooltip("PatientRest-local root of the KnockedOut clip after the EscapeFall clip: the floor point under the landed hips. " +
                 "v03 uses the mirrored clips (Op_*_Mirror_v01, escape over the patient's RIGHT = the table camera's side), so this is " +
                 "the mirror of validation_op_v01.json cross_contracts (-1.5, -0.66, 0.36).")]
        public Vector3 escapeLandingOffset = new Vector3(1.5f, -0.66f, 0.36f);
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
        [Tooltip("Rework 2026-10-18 (Fedya): a full blood syringe empties into the clicked bag over this time: the plunger goes " +
                 "down, the barrel empties and the bag fills by the same amount.")]
        public float bloodTransferSeconds = 1.2f;
        [Tooltip("Portions one bag holds; a portion fills 1/this of the bag.")]
        public int bloodPortionsPerBag = 1;
        [Tooltip("Angle of the syringe to the skin while it draws blood or injects (degrees).")]
        public float syringeSkinAngle = 30f;
        public float unsealedBloodSeconds = 120f;
        public float sealSeconds = 1f;
        public int bloodValue = 50;
        public int weakenedPortion = 2;
        public int fatalPortion = 3;
        public float firstKidneyChance = 0.1f;
        public float secondKidneyChance = 0.2f;
        public float liverChance = 0.3f;
        [Tooltip("Lead decision 2026-10-18 (Fedya's playtest: liver + both kidneys out and he lived): removing the liver, or the " +
                 "second kidney, kills him at once (chance 1). Only the first kidney keeps its roll (+ blood portions).")]
        public bool liverOrBothKidneysFatal = true;
        public float bloodChancePerPortion = 0.1f;
        public float corpseGraceSeconds = 45f;
        public float corpseGradeSeconds = 40f;
        public int earlyOverdoseLoss = 2;
        [Header("Incisions (marker-local metres)")]
        [Tooltip("v04: one shared belly opening; the original v01/v02 assets keep their per-organ guides.")]
        public bool sharedAbdomen;
        [Header("Approved anatomy v02 (imported copies; source models stay unchanged)")]
        public bool anatomicalLayout;
        public GameObject abdomenModel;
        public Texture2D abdomenGradient;
        public Shader skinStencilShader;
        public Shader maskStencilShader;
        [Tooltip("Readable copies of the table's strap meshes and the v02 ABDOMEN_MASK for the query-only MeshColliders. " +
                 "The source FBX meshes are not readable: a runtime MeshCollider on them has no collision data in a player build " +
                 "(Fedya's 2026-10-18 build: straps could not be clicked at all). Baked by OperationQueryMeshBaker.")]
        public Mesh[] queryMeshes = new Mesh[0];
        [Header("Approved anatomy v03 (organs at their SOCKET_* frames 1:1, chest visuals; Claude 2026-10-18)")]
        [Tooltip("Patient_v03 + Organs_v03 + OperationAbdomen_v03: organs are the ORGAN_*_v03 meshes at the patient's SOCKET_* " +
                 "frames, unscaled, the same mesh on the tray; belly guide and kidney cords come from the fields below.")]
        public bool anatomyV03;
        [Tooltip("INC_ABDOMEN-local Unity metres of the belly guide (v03 ORGANS_LAYOUT guide_belly).")]
        public Vector3 bellyStart, bellyEnd;
        [Tooltip("Kidney cords, marker-local Unity metres: L artery, L vein, R artery, R vein (v03 organs.*.cords).")]
        public Vector3[] cordStarts = new Vector3[0], cordEnds = new Vector3[0];
        [Tooltip("v03 organ meshes for organ 0 (left kidney), 1 (right kidney), 2 (liver): FBX roots, the mesh is used at 1:1.")]
        public GameObject[] organModelsV03 = new GameObject[0];
        [Tooltip("Visual-only chest parts: heart, left lung, right lung (at SOCKET_HEART/LUNG_L/LUNG_R), ribcage and chest vessels (SOCKET_THORAX).")]
        public GameObject[] chestModelsV03 = new GameObject[0];
        [Tooltip("BLOOD-BAG v05 (BLOOD_LIQUID blend shapes Fill_025..Fill_100) for the bags on the tray and the sealed bag.")]
        public GameObject bloodBagModel;
        public float abdomenCutLength = 0.32f;
        public Vector2 abdomenHalfSize = new Vector2(0.145f, 0.19f);
        [Tooltip("v04: centre of the opening from the midpoint of the two kidney markers: x along the table toward the head, " +
                 "y up (just above the highest belly skin, so the skin never shows through the opening).")]
        public Vector2 abdomenOffset = new Vector2(0.045f, 0.006f);
        public Vector2 liverLoopRadius = new Vector2(0.050f, 0.049f);
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
        [Tooltip("v04: the same local wheel can back out from the close belly framing to reach the leg straps.")]
        public float minZoom;
        [Tooltip("v04: table-local camera offset at minZoom (fully wheeled out): up and toward the feet, so the whole " +
                 "patient, all five straps and the tray are on screen. Zero keeps the v01-v03 behaviour.")]
        public Vector3 wideCameraOffset;
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
