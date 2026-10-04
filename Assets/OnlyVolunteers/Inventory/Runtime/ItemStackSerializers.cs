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
        }

        public static ItemStack ReadItemStack(this Reader reader) =>
            new ItemStack(reader.ReadInt32(), reader.ReadInt32(), reader.ReadInt32());
    }
}
