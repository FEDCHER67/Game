using System;
using OnlyVolunteers.Operation.Stage1;

namespace OnlyVolunteers.Capture
{
    /// <summary>Organ quality from district, NPC type and condition (CAPTURE_DELIVERY_SPEC v01 §6, D8, D9).
    /// Grades use the operation tiers: 0 «Убитое», 1 «Сойдёт», 2 «Хорошее», 3 «Отличное», 4 «Идеальное».
    /// Intrinsic grades are rolled ONCE per identity at first capture from a seed derived from the PatientId, so the same
    /// NPC always rolls the same grades (re-rolls cannot be farmed). The condition loss is applied at extraction
    /// (OperationState.conditionLoss, OperationRules.Extract).</summary>
    public static class CaptureGrades
    {
        public const int Damaged = 0, Acceptable = 1, Good = 2, Perfect = 3, PerfectPlus = 4, Organs = 3;

        /// <summary>The five rows of the district table (§6.1).</summary>
        public enum Row : byte { Rough, Hamlet, Downtown, Elite, Tramduro }

        /// <summary>Crowd data district ids (Map/Data/crowd_v19_build_v07.json) to rows. Unknown and unlisted districts
        /// (Industrial Port = "industrial") use the Hamlet row, as the spec says.</summary>
        public static Row RowFor(string districtId)
        {
            switch ((districtId ?? "").Trim().ToLowerInvariant())
            {
                case "forest": case "residential": case "rough": return Row.Rough;
                case "village": case "hamlet": case "transition": case "construction": return Row.Hamlet;
                case "old_town": case "downtown": case "beach": return Row.Downtown;
                case "elite": case "fields": case "quiet_valley": return Row.Elite;
                case "tramduro": return Row.Tramduro;
                default: return Row.Hamlet;
            }
        }

        /// <summary>Weight of each grade 0..4 in a row (proposed presets: "mostly X, sometimes Y/Z" = 70/15/15,
        /// "X and Y equally" = 50/50, "mostly X, sometimes Y" = 75/25).</summary>
        public static float[] Weights(Row row)
        {
            switch (row)
            {
                case Row.Rough: return new[] { 0.15f, 0.70f, 0.15f, 0f, 0f };
                case Row.Downtown: return new[] { 0f, 0f, 0.50f, 0.50f, 0f };
                case Row.Elite: return new[] { 0f, 0f, 0f, 0.75f, 0.25f };
                case Row.Tramduro: return new[] { 0f, 0f, 0f, 0.50f, 0.50f };
                default: return new[] { 0f, 0.25f, 0.75f, 0f, 0f };
            }
        }

        /// <summary>The grade a uniform number u in [0, 1) picks from a row.</summary>
        public static int Pick(Row row, double u)
        {
            float[] w = Weights(row);
            double acc = 0;
            int last = 0;
            for (int g = 0; g < w.Length; g++)
            {
                if (w[g] <= 0f) continue;
                last = g;
                acc += w[g];
                if (u < acc) return g;
            }
            return last;
        }

        /// <summary>Type shifts per organ (left kidney, right kidney, liver), ±1 grade, clamped later (§6.2). Matched on
        /// keywords of the type id (SAUSAGE_BUDDY types: BAD_DRUNK, FOREST_OD_JUNKIE, HAMLET_GRANNY...). Lungs are not an
        /// operation organ yet: the smoker/vaper shift is recorded by LungShift only.</summary>
        public static int[] TypeShift(string typeId)
        {
            string t = (typeId ?? "").ToUpperInvariant();
            var shift = new int[Organs];
            bool old = t.Contains("GRANNY") || t.Contains("GRANDMA") || t.Contains("GRANDPA") || t.Contains("OLD_") || t.Contains("_OLD");
            if (old) for (int i = 0; i < Organs; i++) shift[i] -= 1;
            if (t.Contains("JUNKIE") || t.Contains("DRUNK") || t.Contains("BOMZH") || t.Contains("HOMELESS")) shift[2] -= 1;
            if (t.Contains("BODYBUILDER") || t.Contains("FITNESS")) { shift[0] += 1; shift[1] += 1; }
            return shift;
        }

        public static int LungShift(string typeId)
        {
            string t = (typeId ?? "").ToUpperInvariant();
            int shift = t.Contains("BODYBUILDER") || t.Contains("FITNESS") ? 1 : 0;
            if (t.Contains("SMOK") || t.Contains("VAPER")) shift -= 1;
            return shift;
        }

        /// <summary>D8: condition 0..100 removes grades from every organ at extraction.</summary>
        public static int ConditionLoss(float condition) =>
            condition >= 75f ? 0 : condition >= 50f ? 1 : condition >= 25f ? 2 : 3;

        public static int Clamp(int grade) => grade < Damaged ? Damaged : grade > PerfectPlus ? PerfectPlus : grade;

        /// <summary>Stable 64-bit seed of an identity (FNV-1a over the id's chars).</summary>
        public static ulong Seed(string patientId)
        {
            ulong h = 14695981039346656037UL;
            foreach (char c in patientId ?? "")
            {
                h ^= c;
                h *= 1099511628211UL;
            }
            return h;
        }

        /// <summary>SplitMix64 step: deterministic on every platform (System.Random is not specified to be).</summary>
        public static ulong Next(ref ulong state)
        {
            state += 0x9E3779B97F4A7C15UL;
            ulong z = state;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
            return z ^ (z >> 31);
        }

        public static double Uniform(ref ulong state) => (Next(ref state) >> 11) * (1.0 / 9007199254740992.0);

        /// <summary>Intrinsic grades of the three operation organs for one identity: the district row rolled per organ,
        /// then the type shift, clamped to 0..4. The same id always gives the same grades.</summary>
        public static int[] RollIntrinsic(string patientId, string districtId, string typeId)
        {
            Row row = RowFor(districtId);
            int[] shift = TypeShift(typeId);
            ulong state = Seed(patientId);
            var grades = new int[Organs];
            for (int i = 0; i < Organs; i++) grades[i] = Clamp(Pick(row, Uniform(ref state)) + shift[i]);
            return grades;
        }

        /// <summary>Writes rolled grades into an operation state (before any damage).</summary>
        public static void Apply(OperationState state, int[] grades)
        {
            if (state == null || state.organs == null || grades == null) return;
            for (int i = 0; i < state.organs.Length && i < grades.Length; i++) state.organs[i].intrinsicGrade = grades[i];
        }

        /// <summary>The grade an organ comes out with after a clean extraction: intrinsic - condition loss, floored.</summary>
        public static int CleanExtractionGrade(int intrinsic, float condition) => Math.Max(Damaged, intrinsic - ConditionLoss(condition));
    }
}
