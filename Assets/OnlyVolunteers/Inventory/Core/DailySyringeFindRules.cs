using System;

namespace OnlyVolunteers.Inventory
{
    [Serializable]
    public sealed class DailySyringeFindSave
    {
        public string WorldId = "";
        public long LastMorning = long.MinValue;
        public SyringeInstance Uncollected;
    }
    [Serializable]
    public sealed class SyringeFindSpot
    {
        public string Id = "";
        public SyringeKind Kind = SyringeKind.Blood;
        // Authored content only. Absence of a daily guarantee is deliberate; no procedural spot generator.
        public bool Enabled;
    }
    [Serializable]
    public sealed class SyringeFindData
    {
        public string GuaranteedAnchorId = "wagon";
        public SyringeFindSpot[] ExtraSpots = Array.Empty<SyringeFindSpot>();
    }
    public static class DailySyringeFindRules
    {
        public const long Morning = 6 * 3600, Day = 24 * 3600;
        public static long MorningId(long gameSeconds)
        {
            if (gameSeconds < 0) throw new ArgumentOutOfRangeException(nameof(gameSeconds));
            return gameSeconds < Morning ? -1 : (gameSeconds - Morning) / Day;
        }
        /// <summary>Start, join, load and morning tick use exactly this one rule and saved world record.
        /// Only current active-world time is supplied; no offline backfill and at most one uncollected item.</summary>
        public static bool Advance(DailySyringeFindSave state, string worldId, long gameSeconds, bool worldActive)
        {
            if (state == null || string.IsNullOrWhiteSpace(worldId)) throw new ArgumentException("Saved team world identity required");
            if (!worldActive) return false;
            long morning = MorningId(gameSeconds);
            if (state.WorldId != "" && state.WorldId != worldId) throw new ArgumentException("Wrong team world");
            state.WorldId = worldId;
            if (morning <= state.LastMorning) return false;
            state.LastMorning = morning;
            if (state.Uncollected != null) return false;
            state.Uncollected = SyringeInstance.New(SyringeKind.Blood, worldId + "/wagon/syringe/" + morning);
            return true;
        }
        public static SyringeInstance Collect(DailySyringeFindSave state, string expectedItemId)
        {
            if (state?.Uncollected == null || state.Uncollected.ItemId != expectedItemId) return null;
            var item = state.Uncollected; state.Uncollected = null; return item;
        }
    }
}
