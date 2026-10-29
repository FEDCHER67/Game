using OnlyVolunteers.Inventory;

namespace OnlyVolunteers.Operation.Stage1
{
    public sealed partial class OperationRules
    {
        /// <summary>Binding is checked BEFORE FillBlood; cancelled partial draws bind nobody or consume a portion.</summary>
        public SyringeUseResult FillSyringe(SyringeInstance syringe, float seconds, bool validSite, out bool completed)
        {
            completed = false;
            var check = SyringeRules.Check(syringe, SyringeKind.Blood, State.patientId, State.alive, validSite);
            if (check != SyringeUseResult.Success) return check;
            if (syringe.Portion != null || !Finite(seconds) || seconds <= 0 || State.bloodPortions >= tuning.fatalPortion ||
                !DonorAllows(DonorExtraction.Blood))
                return SyringeUseResult.Failed;
            if (syringe.PendingPersonId != "" && syringe.PendingPersonId != State.patientId) return SyringeUseResult.OtherPerson;
            float before = syringe.Fill;
            completed = FillBloodPortion(ref syringe.Fill, seconds);
            if (syringe.Fill <= before) return SyringeUseResult.Failed;
            syringe.PendingPersonId = State.patientId;
            if (completed)
            {
                syringe.PersonId = State.patientId;
                syringe.PendingPersonId = "";
                syringe.Portion = new BloodPortion { Id = State.patientId + "/blood/" + State.bloodPortions,
                    PersonId = State.patientId, FreshSeconds = tuning.unsealedBloodSeconds };
                CommitDonorBlood(); // PLAYER stage: the identified portion exists first, then a one-extraction donor is spent and dies
            }
            return SyringeUseResult.Success;
        }
        /// <summary>The caller queues exactly the returned amount in the existing dose tick.</summary>
        public SyringeUseResult DoseSyringe(SyringeInstance syringe, float requested, bool validSite, out float accepted)
        {
            accepted = 0;
            float dose = requested;
            var result = SyringeRules.TryUse(syringe, SyringeKind.Anaesthesia, State.patientId, State.alive, validSite,
                () => Finite(dose) && dose > 0);
            if (result == SyringeUseResult.Success) accepted = requested;
            return result;
        }
    }
}
