using System;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// What the HUD and the input need from an inventory: NetworkInventory in the game,
    /// LocalInventory in offline test scenes such as the map grey-box.
    /// </summary>
    public interface IInventoryView
    {
        event Action Changed;
        /// <summary>True on the machine that controls this inventory (the HUD is shown only there).</summary>
        bool IsLocalOwner { get; }
        ItemDatabase Database { get; }
        int SlotCount { get; }
        int SelectedIndex { get; }
        int Cash { get; }
        ItemStack GetSlot(int index);
        void RequestSelect(int index);
        void RequestSelectNext(int direction);
        bool RequestPickup(Ray ray);
        bool RequestDropSelected(Ray view);
    }
}
