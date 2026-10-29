using System;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>An NPC's authored donor condition. Saved: append only.</summary>
    public enum DonorCondition { Ordinary = 0, SevereDrugIntoxication = 1 }

    public enum DonorExtraction { Blood = 0, Organ = 1 }

    /// <summary>
    /// The donor extraction budget of one person (inside his OperationState, so it travels with him through capture, the van,
    /// the table, the field, death, save/load and reconnect). Ordinary donors keep every existing rule untouched. A person in
    /// the AUTHORED severe drug-intoxication condition (Fedya 29.10: e.g. the tutorial addict at the wagon) has ONE extraction
    /// in total — one blood portion OR one organ item, shared by both paths: the first successful extraction spends it and
    /// causes his ordinary authoritative death; any later blood or organ extraction from that body is refused, even where
    /// ordinary corpse processing would allow it. Never derived from a model, a type name, sleep or our anaesthetic.
    /// </summary>
    [Serializable]
    public sealed class DonorBudget
    {
        /// <summary>DonorCondition.</summary>
        public int condition;
        /// <summary>Who authored the condition (e.g. "authored:Forest/WagonAddict01"), for checks and saves.</summary>
        public string conditionSource = "";
        /// <summary>The one outcome that spent the budget ("blood:…/blood/1", "organ:…/organ/0"); "" = not spent.</summary>
        public string spentOn = "";

        public DonorCondition Condition => (DonorCondition)condition;
        public bool SevereIntoxication => condition == (int)DonorCondition.SevereDrugIntoxication;
        public bool Exhausted => SevereIntoxication && !string.IsNullOrEmpty(spentOn);
    }

    /// <summary>Pure rules of <see cref="DonorBudget"/> (no Unity). OperationRules calls them at its one blood choke point
    /// (FillBlood / FillSyringe) and at Extract.</summary>
    public static class DonorBudgetRules
    {
        /// <summary>Authoring: marks a person as severely drug-intoxicated. Needs a provenance string, and only before anything
        /// was extracted from him (the condition is a starting fact, never applied after the fact to dodge earlier
        /// extractions). The same condition again is a harmless repeat (load, re-authoring).</summary>
        public static bool MarkSevereDrugIntoxication(DonorBudget budget, string source, int bloodPortionsSoFar, int organsSoFar)
        {
            if (budget == null || string.IsNullOrWhiteSpace(source)) return false;
            if (budget.SevereIntoxication) return true;
            if (bloodPortionsSoFar > 0 || organsSoFar > 0 || !string.IsNullOrEmpty(budget.spentOn)) return false;
            budget.condition = (int)DonorCondition.SevereDrugIntoxication;
            budget.conditionSource = source.Trim();
            return true;
        }

        /// <summary>One-extraction donor (the severe condition).</summary>
        public static bool LimitsToOne(DonorBudget budget) => budget != null && budget.SevereIntoxication;

        /// <summary>May this kind of extraction still happen? Ordinary (or no budget) = always (the existing rules decide).</summary>
        public static bool Allows(DonorBudget budget, DonorExtraction kind) => !LimitsToOne(budget) || !budget.Exhausted;

        /// <summary>Records the ONE outcome of a one-extraction donor. True = spent now (the caller commits his death, once);
        /// false = nothing to do (an ordinary donor) or already spent (a concurrent/duplicate request).</summary>
        public static bool TrySpend(DonorBudget budget, DonorExtraction kind, string outcomeId)
        {
            if (!LimitsToOne(budget) || budget.Exhausted) return false;
            budget.spentOn = OutcomeKey(kind, outcomeId);
            return true;
        }

        public static string OutcomeKey(DonorExtraction kind, string outcomeId) =>
            (kind == DonorExtraction.Blood ? "blood:" : "organ:") + (string.IsNullOrEmpty(outcomeId) ? "?" : outcomeId);
    }
}
