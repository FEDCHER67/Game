namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>The severe drug-intoxication donor rule inside the server rules (DonorBudget). One blood portion OR one organ
    /// in total; the first successful extraction spends it and kills him by the ordinary Die path (DeathCause.Blood /
    /// DeathCause.Extraction, the same cues, spoilage and corpse handling as any death). Failed or cancelled attempts never
    /// reach these calls, so they spend nothing.</summary>
    public sealed partial class OperationRules
    {
        /// <summary>Authoring (server, before any extraction): this person is in the severe drug-intoxication condition.</summary>
        public bool MarkSevereDrugIntoxication(string source)
        {
            State.donor ??= new DonorBudget();
            return DonorBudgetRules.MarkSevereDrugIntoxication(State.donor, source, State.bloodPortions, State.extracted);
        }

        public bool DonorExhausted => State.donor != null && State.donor.Exhausted;

        private bool DonorAllows(DonorExtraction kind) => DonorBudgetRules.Allows(State.donor, kind);

        /// <summary>After a completed blood portion (and, for a syringe, after its identified portion is minted): a
        /// one-extraction donor is spent and dies now. Ordinary donors: nothing (their portion rules ran in FillBloodPortion).</summary>
        private void CommitDonorBlood()
        {
            if (!DonorBudgetRules.TrySpend(State.donor, DonorExtraction.Blood, State.patientId + "/blood/" + State.bloodPortions)) return;
            if (State.alive) Die(DeathCause.Blood);
        }

        /// <summary>At a successful organ extraction of a one-extraction donor: spends the budget and, if he still lives, kills
        /// him (no survival roll). True = handled here (the caller skips the ordinary death roll).</summary>
        private bool CommitDonorOrgan(OrganState organ)
        {
            if (!DonorBudgetRules.TrySpend(State.donor, DonorExtraction.Organ, organ.outputId)) return false;
            bool wasAlive = State.alive;
            organ.deathChance = wasAlive ? 1f : 0f;
            organ.rollCompleted = wasAlive;
            organ.fatal = wasAlive;
            if (wasAlive) Die(DeathCause.Extraction);
            return true;
        }
    }
}
