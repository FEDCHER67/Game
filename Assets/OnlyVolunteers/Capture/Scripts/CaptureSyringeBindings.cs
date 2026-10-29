using FishNet;
using OnlyVolunteers.Inventory;

namespace OnlyVolunteers.Capture
{
    public sealed partial class CaptureFieldKit
    {
        public SyringeInstance BloodSyringe { get; private set; }
        public SyringeInstance AnaesthesiaSyringe { get; private set; }
        // Called by the existing save adapter after reading FieldKitSave (insertion in G49 report).
        public void RestoreSyringes(SyringeInstance blood, SyringeInstance anaesthesia)
        {
            BloodSyringe = blood; AnaesthesiaSyringe = anaesthesia;
            if (blood != null) BloodFill = blood.Fill;
        }
        private bool SyringeAllowed(SyringeInstance item, SyringeKind kind, string person, bool alive)
        {
            if (!InstanceFinder.IsServerStarted) return false;
            if (inventory?.Model?.Selected.Syringe != item || item == null)
            { if (UnityEngine.Time.time >= nextRefusalAt) { nextRefusalAt = UnityEngine.Time.time + 1.2f; Refuse("Возьми шприц в руку"); } return false; }
            var result = SyringeRules.Check(item, kind, person, alive, true);
            if (result == SyringeUseResult.Success) return true;
            if (UnityEngine.Time.time >= nextRefusalAt)
            {
                nextRefusalAt = UnityEngine.Time.time + 1.2f;
                Refuse(result == SyringeUseResult.OtherPerson ? SyringeRules.OtherPersonNotice :
                    result == SyringeUseResult.LegacyUnknown ? "История шприца неизвестна — нужен новый" : "Нужен пригодный шприц и живой человек");
            }
            return false;
        }
        private void CancelPartialBlood()
        {
            if (BloodSyringe?.Portion != null) return;
            SyringeRules.CancelDraw(BloodSyringe); BloodFill = 0;
        }
    }
}
