namespace OnlyVolunteers.Operation
{
    /// <summary>Organ grade. Order matters: a penalty moves the grade down by whole steps.</summary>
    public enum OrganQuality
    {
        Damaged = 0,
        Normal = 1,
        Good = 2,
        Perfect = 3,
        PerfectPlus = 4,
    }

    /// <summary>
    /// Grade -> price, from docs/drafts/ECONOMY_PROGRESSION_DRAFT.md 4.2 (not approved):
    /// Damaged x0.3, Normal x1, Good x1.6, Perfect x2.6, Perfect+ x4.2 of the item's base value.
    /// </summary>
    public static class OrganGrading
    {
        private static readonly int[] Percent = { 30, 100, 160, 260, 420 };

        public static int UnitValue(int baseValue, OrganQuality quality) =>
            (baseValue * Percent[(int)quality] + 50) / 100;

        /// <summary>The operation can only lower the grade the NPC arrived with, never raise it (canon 24, 42).</summary>
        public static OrganQuality Lower(OrganQuality quality, int steps)
        {
            int value = (int)quality - (steps > 0 ? steps : 0);
            return (OrganQuality)(value < 0 ? 0 : value);
        }

        public static string Label(OrganQuality quality) => quality == OrganQuality.PerfectPlus ? "Perfect+" : quality.ToString();
    }
}
