using OnlyVolunteers.Operation;
using UnityEngine;

namespace OnlyVolunteers.Clinic
{
    // Field Clinic loop (docs/Progress.md, skill fc-patient-lifecycle): one stable PatientId per captured NPC and one
    // explicit stage. Allowed moves:
    //   Available -> Captured      knocked down (lying, GreyboxNpc.State Down)
    //   Captured  -> Available     got up and left (awake, out of any van)
    //   Captured  -> Loaded        counted as cargo by GreyboxVanCargo (InCargo)
    //   Loaded    -> Captured      dragged or slid out of the bay, still down
    //   Loaded    -> Available     escaped from the van awake
    //   Captured  -> AtBase        left lying on the base pad (ClinicDropOff): the NPC object is removed, the record and
    //                              the table's stand-in carry the id from here on
    //   AtBase    -> InOperation   the operation starts (ClinicOperationRunner)
    //   InOperation -> AtBase      cancelled before the organ came out: retry later, nothing lost
    //   InOperation -> Resolved    finished: the reward is paid once (PatientRegistry.TryResolve)
    // Resolved is final. Anything else is refused and logged. Movement owner per stage: the NPC's own controller
    // (Available), its physical body (Captured, Loaded: the van's cargo bay damps it), the table (AtBase, InOperation).
    public enum PatientStage : byte { Available, Captured, Loaded, AtBase, InOperation, Resolved }

    /// <summary>Plain data of one patient; the NPC GameObject or the table's stand-in only represent it.</summary>
    public sealed class PatientRecord
    {
        public readonly string Id;
        public PatientStage Stage;
        /// <summary>GreyboxNpc.Condition (0..100) when it was handed over at the base.</summary>
        public float Condition = 100f;
        /// <summary>Grade the organ starts from (from Condition at the hand-over); the operation can only lower it.</summary>
        public OrganQuality Quality = OrganQuality.Good;
        public bool Rewarded;
        public int Reward;

        public PatientRecord(string id, PatientStage stage)
        {
            Id = id;
            Stage = stage;
        }

        public override string ToString() => $"{Id} {Stage}";
    }

    public static class PatientLifecycle
    {
        public static bool CanMove(PatientStage from, PatientStage to)
        {
            switch (from)
            {
                case PatientStage.Available: return to == PatientStage.Captured;
                case PatientStage.Captured: return to == PatientStage.Available || to == PatientStage.Loaded || to == PatientStage.AtBase;
                case PatientStage.Loaded: return to == PatientStage.Captured || to == PatientStage.Available;
                case PatientStage.AtBase: return to == PatientStage.InOperation;
                case PatientStage.InOperation: return to == PatientStage.AtBase || to == PatientStage.Resolved;
                default: return false; // Resolved is final
            }
        }

        /// <summary>Condition 0..100 at the hand-over -> starting grade: careful delivery keeps more value (PRODUCT.md).</summary>
        public static OrganQuality QualityFor(float condition) =>
            condition >= 95f ? OrganQuality.Perfect :
            condition >= 75f ? OrganQuality.Good :
            condition >= 45f ? OrganQuality.Normal : OrganQuality.Damaged;

        public static string NewId() => "P-" + System.Guid.NewGuid().ToString("N").Substring(0, 10);
    }

    /// <summary>Marks a crowd NPC that became a patient (added at runtime when it is first knocked down).</summary>
    public sealed class PatientTag : MonoBehaviour
    {
        public string PatientId;
    }
}
