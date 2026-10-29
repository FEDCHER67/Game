using System;
using System.Collections.Generic;
using OnlyVolunteers.Buyers;

namespace OnlyVolunteers.Inventory
{
    public enum SyringeReturnChoice { TakeEmpty = 0, LeaveWithBuyer = 1 }
    [Serializable]
    public sealed class SyringeSaleReceipt
    {
        public string TransactionId = "", PortionId = "", ItemId = "";
        public int Amount, XpEach, Participants;
        public SyringeReturnChoice ReturnChoice;
        public SyringeSaleReceipt Copy() => (SyringeSaleReceipt)MemberwiseClone();
    }
    [Serializable]
    public sealed class SyringeSalesSave
    {
        public bool FirstSyringeSold;
        public bool FirstBloodXpGranted;
        public List<string> SoldPortions = new List<string>();
        public List<SyringeSaleReceipt> Receipts = new List<SyringeSaleReceipt>();
        public SyringeSalesSave Copy() => new SyringeSalesSave {
            FirstSyringeSold = FirstSyringeSold, FirstBloodXpGranted = FirstBloodXpGranted,
            SoldPortions = new List<string>(SoldPortions), Receipts = Receipts.ConvertAll(r => r.Copy()) };
    }
    /// <summary>Adapter MUST use the existing crate/sale payout transaction, never a second wallet.
    /// Book payout, XP, item outcome and this save block together durably under TransactionId.
    /// false means nothing was committed. Replayed transactions must not book payout or XP again.</summary>
    public interface ISyringeSalePayout
    {
        bool TryCommit(SyringeSaleReceipt sale, SyringeSalesSave nextState, SyringeInstance itemAfter);
    }

    /// <summary>Pure C01 confirmation rule. Its receipt is a command for the existing payout path, not money storage.</summary>
    public sealed class SyringeSaleRules
    {
        private readonly object gate = new object();
        private SyringeSalesSave state;
        public SyringeSaleRules(SyringeSalesSave saved = null) { state = (saved ?? new SyringeSalesSave()).Copy(); }
        public SyringeSalesSave Snapshot { get { lock (gate) return state.Copy(); } }
        public int Quote => BuyerCatalog.SyringePrice(state.FirstSyringeSold ? "c01_blood_repeat" : "c01_blood_first");
        public bool IsSold(string portionId) { lock (gate) return state.SoldPortions.Contains(portionId); }
        public bool TryConfirm(string transactionId, BloodPortion portion, SyringeInstance syringe, int participants,
            ISyringeSalePayout payout, out SyringeSaleReceipt receipt, SyringeReturnChoice choice = SyringeReturnChoice.TakeEmpty)
        {
            lock (gate)
            {
                receipt = null;
                if (string.IsNullOrWhiteSpace(transactionId)) return false;
                var previous = state.Receipts.Find(r => r.TransactionId == transactionId);
                if (previous != null) { receipt = previous.Copy(); return true; }
                if (portion == null || !portion.Saleable || state.SoldPortions.Contains(portion.Id) ||
                    participants < 1 || participants > 4 || payout == null || !Enum.IsDefined(typeof(SyringeReturnChoice), choice)) return false;
                bool inSyringe = syringe != null;
                if (inSyringe && (syringe.Kind != SyringeKind.Blood || syringe.Discarded || syringe.LegacyUnknown ||
                    syringe.Portion == null || syringe.Portion.Id != portion.Id || syringe.PersonId != portion.PersonId || portion.Sealed)) return false;
                if (!inSyringe && !portion.Sealed) return false;
                var next = state.Copy();
                var command = new SyringeSaleReceipt { TransactionId = transactionId, PortionId = portion.Id,
                    ItemId = syringe?.ItemId ?? "", ReturnChoice = choice, Participants = participants,
                    Amount = inSyringe ? Quote : (int)BuyerCatalog.BasePrice(ProductKind.BloodBag),
                    XpEach = 5 + (state.FirstBloodXpGranted ? 0 : 50) };
                next.FirstBloodXpGranted = true;
                if (inSyringe) next.FirstSyringeSold = true;
                next.SoldPortions.Add(portion.Id); next.Receipts.Add(command.Copy());
                var itemAfter = syringe?.Copy();
                if (itemAfter != null) { SyringeRules.Empty(itemAfter); itemAfter.Discarded = choice == SyringeReturnChoice.LeaveWithBuyer; }
                if (!payout.TryCommit(command.Copy(), next.Copy(), itemAfter)) return false;
                if (inSyringe) { syringe.Portion = null; syringe.Fill = 0; syringe.PendingPersonId = ""; syringe.Discarded = choice == SyringeReturnChoice.LeaveWithBuyer; }
                state = next; receipt = command.Copy(); return true;
            }
        }
    }
}
