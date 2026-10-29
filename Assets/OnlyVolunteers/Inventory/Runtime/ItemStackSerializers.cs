using FishNet.Serializing;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Explicit FishNet serializer: ItemStack lives in the engine-free core assembly, so it is not
    /// left to codegen there.
    /// </summary>
    public static class ItemStackSerializers
    {
        public static void WriteItemStack(this Writer writer, ItemStack value)
        {
            writer.WriteInt32(value.ItemId);
            writer.WriteInt32(value.Count);
            writer.WriteInt32(value.UnitValue);
            writer.WriteSyringe(value.Syringe);
        }

        public static ItemStack ReadItemStack(this Reader reader) =>
            new ItemStack(reader.ReadInt32(), reader.ReadInt32(), reader.ReadInt32(), reader.ReadSyringe());

        public static void WriteSyringe(this Writer writer, SyringeInstance value)
        {
            writer.WriteBoolean(value != null); if (value == null) return;
            writer.WriteString(value.ItemId); writer.WriteInt32((int)value.Kind); writer.WriteString(value.PersonId);
            writer.WriteBoolean(value.LegacyUnknown); writer.WriteBoolean(value.Discarded);
            writer.WriteSingle(value.Fill); writer.WriteString(value.PendingPersonId);
            writer.WriteBoolean(value.Portion != null); if (value.Portion == null) return;
            writer.WriteString(value.Portion.Id); writer.WriteString(value.Portion.PersonId);
            writer.WriteBoolean(value.Portion.Sealed); writer.WriteSingle(value.Portion.FreshSeconds);
        }
        public static SyringeInstance ReadSyringe(this Reader reader)
        {
            if (!reader.ReadBoolean()) return null;
            var value = new SyringeInstance { ItemId = reader.ReadString(), Kind = (SyringeKind)reader.ReadInt32(),
                PersonId = reader.ReadString(), LegacyUnknown = reader.ReadBoolean(), Discarded = reader.ReadBoolean() };
            value.Fill = reader.ReadSingle(); value.PendingPersonId = reader.ReadString();
            if (reader.ReadBoolean()) value.Portion = new BloodPortion { Id = reader.ReadString(), PersonId = reader.ReadString(),
                Sealed = reader.ReadBoolean(), FreshSeconds = reader.ReadSingle() };
            return value;
        }
    }
}
