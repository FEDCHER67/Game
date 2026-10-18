using System;
using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Items.Core;

namespace WorkInventory.Checks
{
    public sealed class Scenario
    {
        public string Name;
        public Action Run;
        public Scenario(string name, Action run) { Name = name; Run = run; }
        public override string ToString() => Name;
    }
    public static partial class Scenarios
    {
        public static IEnumerable<Scenario> All() => Catalog().Concat(Storage()).Concat(Players()).Concat(Intents()).Concat(Saves());
        internal static void Equal<T>(T expected, T actual, string detail = "")
        { if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new InvalidOperationException(detail + " expected=" + expected + " actual=" + actual); }
        internal static void True(bool condition, string detail = "condition") { if (!condition) throw new InvalidOperationException(detail); }
        internal static void Near(double expected, double actual, string detail = "") { True(Math.Abs(expected - actual) < 1e-8, detail + " expected=" + expected + " actual=" + actual); }
        internal static void Throws<T>(Action action) where T : Exception
        { try { action(); } catch (T) { return; } throw new InvalidOperationException("Expected " + typeof(T).Name); }
    }
    internal sealed class World
    {
        public readonly ItemDefTable Defs = ItemCatalog.CreateDefaults();
        public ItemLedger L;
        public ItemIntentServer S;
        public double Now;
        private readonly Dictionary<string, long> sequences = new Dictionary<string, long>();
        private int organSeq;
        private long press;
        public World() { L = new ItemLedger(Defs); L.EnsurePlayer("p"); L.EnsurePlayer("q"); S = new ItemIntentServer(L); }
        public long Next(string actor = "p") { sequences.TryGetValue(actor, out long n); sequences[actor] = ++n; return n; }
        public string Mint(int def = 102, Destination? dest = null, int tier = 5, int count = 1, FillData fill = null)
        {
            Defs.TryGet(def, out var d); var destination = dest ?? Destination.ToWorld();
            var r = d.Class == ItemClass.Organ ? L.MintOrgan("P-test/organ/" + organSeq++, def,
                new OrganData { Tier = tier, DonorPatientId = "P-test", DonorPersonId = "person-1", DonorRoleKey = "lineage-1", DonorNpcType = "HAMLET_BODYBUILDER", DonorDistrict = "Khutor", ExtractedAtGameSeconds = 3600 }, destination, Now) :
                fill != null ? L.MintFilled(def, fill, destination, Now) : L.Mint(def, count, destination, Now);
            Scenarios.True(r.Ok, "mint " + def + " " + r.Error); return r.ItemId;
        }
        public string Cooler(bool open = true) { string id = Mint(301); L.SetOpen(id, open); return id; }
        public string Box(ContainerKind kind, string id = "box")
        {
            int size = kind == ContainerKind.Fridge ? 24 : kind == ContainerKind.Tray ? 6 : kind == ContainerKind.Stash ? 4 : kind == ContainerKind.VanShelf ? 12 : kind == ContainerKind.VanCoolerMount ? 1 : 8;
            L.CreateContainer(id, kind, "team", size); L.SetOpen(id, true); return id;
        }
        public MoveResult Move(string id, Destination destination, string actor = "p", int count = 0) => L.Move(actor, Next(actor), id, destination, Now, count);
        public string Held(int def, FillData fill = null, int count = 1)
        {
            string id = Mint(def, Destination.ToContainer(ItemLedger.PocketsId("p"), 0), count:count, fill:fill);
            L.SelectSlot("p", Next(), 0, Now); return id;
        }
        public IntentContext Context(string actor = "p") => new IntentContext { SenderPlayerId = actor, OwnerPlayerId = actor, HasActivePlayer = true,
            HasLineOfSight = true, Distance = 1, OriginDistance = 1, HasSurface = true, Target = TargetKind.Npc,
            Alive = true, Asleep = true, CanDrawBlood = true, DonorPatientId = "donor", StrapsOpen = true, Downed = true, ResolvedTargetId = "npc" };
        public MoveResult Send(ItemIntent r, IntentContext c = null)
        {
            c = c ?? Context();
            // Test harness emulates the host resolving these identities; production does server scene lookups.
            if (c.ResolvedItemId == "") c.ResolvedItemId = r.ItemId;
            if (c.ResolvedContainerId == "") c.ResolvedContainerId = r.ContainerId;
            if (r.RequestId == 0) r.RequestId = Next(c.SenderPlayerId); return S.Execute(r, c, Now);
        }
        public MoveResult Hold(bool secondary, double duration, IntentContext c = null, TargetPart part = TargetPart.Arms)
        {
            long p = ++press; var kind = secondary ? ItemIntentKind.Secondary : ItemIntentKind.Use;
            var result = Send(new ItemIntent { Kind = kind, PressId = p, Phase = PressPhase.Begin, TargetId = "npc", Part = part }, c);
            if (!result.Ok) return result;
            double end = Now + duration;
            while (Now < end - 1e-10)
            {
                Now = Math.Min(end, Now + 0.25);
                result = Send(new ItemIntent { Kind = kind, PressId = p, Phase = PressPhase.Hold, TargetId = "npc", Part = part }, c);
                if (!result.Ok) return result;
            }
            return result;
        }
    }
}
