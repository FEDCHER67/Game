using System;
using System.Collections.Generic;
using FishNet;
using FishNet.Object;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Buyers.Runtime
{
    /// <summary>W86 minimal first buyer (a reversible playtest stand-in, not sales Stage A). SALES SG-D27: the first organ
    /// buyer's Hamlet surface is a wide wooden crate by the shed. An organ (OperationPhysicalItem, kidney or liver) that
    /// lies free on/in the crate's sale zone for SettleSeconds is bought at once: price = BuyerCatalog.UnitPrice over the
    /// bound G48 catalogue (buyer_first: base price x G48 quality multiplier x buyer coefficient, no haggle, not cooled =
    /// G48 uncooled multiplier because no cooler exists yet, saturation -5 % per unit of the kind already sold this
    /// session; no catalogue = no sale), paid ONCE into the team's shared fund (TeamEconomy, ECONOMY spec v01 §3.1; key = the
    /// organ's id, never per player), the item is despawned and a short HUD toast shows the sale. Server only; no phone, buyer NPC, car, meeting, XP or
    /// save of the sold count. SaleEnabled off (or the object off) = the crate is a plain prop. It is NOT the C01 blood
    /// buyer (blood is refused here; C01's placeholder sale is OnlyVolunteers.Story.StoryDirector). Its first committed
    /// organ purchase also counts as the team's acquaintance with the first organ buyer (M05, once).</summary>
    [DisallowMultipleComponent]
    public sealed class FirstBuyerCrateV01 : MonoBehaviour
    {
        [Tooltip("W86 toggle: off = no sale, the crate is only a prop.")]
        public bool SaleEnabled = true;
        [Tooltip("Sale zone in the crate's local frame (centre, size), m: above the lid.")]
        public Vector3 ZoneCenter = new(0f, 0.95f, 0f);
        public Vector3 ZoneSize = new(1.5f, 0.7f, 0.9f);
        [Tooltip("An organ must lie free in the zone this long, s.")]
        [Min(0f)] public float SettleSeconds = 0.4f;
        [Tooltip("No cooler box in this build: the catalogue's not-cooled factor (x0.9) applies.")]
        public bool DeliveredCooled;
        [Tooltip("Hint shown when the player stands this close, m.")]
        [Min(0f)] public float HintRadius = 3f;

        public static FirstBuyerCrateV01 Instance { get; private set; }
        public int SoldCount { get; private set; }
        public int EarnedTotal { get; private set; }
        public string LastSale { get; private set; } = "";

        private readonly Dictionary<OperationPhysicalItem, float> since = new();
        private readonly Dictionary<ProductKind, int> soldOfKind = new();
        private readonly HashSet<OperationPhysicalItem> refused = new();
        private float nextScan;
        private bool hintShown;

        private void OnEnable() => Instance = this;
        private void OnDisable() { if (Instance == this) Instance = null; }

        /// <summary>World-space centre of the sale zone (where to drop an organ).</summary>
        public Vector3 ZoneWorldCenter => transform.TransformPoint(ZoneCenter);

        public bool InZone(Vector3 world)
        {
            Vector3 p = transform.InverseTransformPoint(world) - ZoneCenter;
            Vector3 h = ZoneSize * 0.5f;
            return Mathf.Abs(p.x) <= h.x && Mathf.Abs(p.y) <= h.y && Mathf.Abs(p.z) <= h.z;
        }

        /// <summary>The catalogue price of one unit (whole dollars) of an operation item for this buyer, or -1 when he does
        /// not buy it (blood, syringes).</summary>
        public int PriceOf(OperationPhysicalItem item, out ProductKind kind, out QualityTier tier)
        {
            kind = item.Kind == 1 ? ProductKind.Liver : ProductKind.Kidney;
            tier = (QualityTier)Mathf.Clamp(item.Grade + 1, 1, 5);
            if (!item.IsOrgan) return -1;
            soldOfKind.TryGetValue(kind, out int already);
            EconomyCatalog catalog = EconomyCatalogSource.Ensure();
            if (catalog == null) return -2; // the ONE price source is unavailable: no sale, never a fallback table
            decimal price;
            try { price = BuyerCatalog.UnitPrice(catalog, "buyer_first", kind, tier, 0, false, DeliveredCooled, already, false); }
            catch (ArgumentOutOfRangeException) { return -1; } // below the buyer's quality floor
            return (int)Math.Round(price, MidpointRounding.AwayFromZero);
        }

        private void Update()
        {
            if (!SaleEnabled || !InstanceFinder.IsServerStarted || Time.time < nextScan) return;
            nextScan = Time.time + 0.1f;
            var items = FindObjectsByType<OperationPhysicalItem>();
            var seen = new HashSet<OperationPhysicalItem>();
            foreach (var item in items)
            {
                if (item == null || !item.IsSpawned || item.Holder != null || item.Data == null || !InZone(item.transform.position)) continue;
                seen.Add(item);
                if (!since.TryGetValue(item, out float t0)) { since[item] = Time.time; continue; }
                if (Time.time - t0 < SettleSeconds) continue;
                TrySell(item);
            }
            var gone = new List<OperationPhysicalItem>();
            foreach (var k in since.Keys) if (k == null || !seen.Contains(k)) gone.Add(k);
            foreach (var k in gone) since.Remove(k);
        }

        private void TrySell(OperationPhysicalItem item)
        {
            int price = PriceOf(item, out ProductKind kind, out QualityTier tier);
            if (price == -2) { if (refused.Add(item)) Toast("Скупщик: цены не загружены (каталог G48) — продажа недоступна", CaptureHud.Bad); return; }
            if (price < 0)
            {
                if (refused.Add(item)) Toast(item.IsOrgan ? "Скупщик: «Такое качество не беру»" : "Скупщик: «Кровь не беру — только органы» (кровь берёт C01)", CaptureHud.Warn);
                return;
            }
            // ECONOMY spec v01 §3.1: the sale pays the team's shared fund once (any team size), not a player's pocket. The
            // organ's own id is the transaction key: the same organ can never be paid twice. The save is still loading:
            // the organ stays on the crate and sells a moment later.
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy == null || !economy.IsServer) { if (refused.Add(item)) Toast("Скупщик: «Некуда платить» (нет общего фонда)", CaptureHud.Bad); return; }
            if (!economy.ServerCanCommit) return;
            string title = item.Title;
            string key = "sale:first-buyer:" + (string.IsNullOrEmpty(item.Identity) ? "noid:" + Guid.NewGuid().ToString("N") : item.Identity);
            if (!TryPaySale(price, $"Скупщик: {title} · {BuyerCatalog.QualityLabel(tier)}", key, kind, out FundResult paid, out int xpEach)) { if (refused.Add(item)) Toast("Скупщик: оплата не прошла", CaptureHud.Bad); return; }
            // M05 (STORY spec §8): a committed purchase proves the acquaintance with this buyer (an early valid world action
            // is reconciled, once). Locked before C01's referral: the sale still stands, the story fact waits.
            economy.ServerState?.CommitFirstOrganBuyerAcquaintance("first organ purchase at the crate " + key);
            if (paid.Replayed) Debug.LogWarning($"[SALE] {key} was already paid: the organ is taken without a second payment", this);
            soldOfKind[kind] = (soldOfKind.TryGetValue(kind, out int n) ? n : 0) + 1;
            SoldCount++; EarnedTotal += paid.Replayed ? 0 : price;
            since.Remove(item);
            LastSale = $"{title} · {BuyerCatalog.QualityLabel(tier)} → +${price}" + (!paid.Replayed && xpEach > 0 ? $" · +{xpEach} XP" : "");
            Debug.Log($"[SALE] first buyer crate: {item.Identity} {kind} {tier} -> ${price} to the team fund (fund now ${paid.Balance}, sold {SoldCount}, total ${EarnedTotal})", this);
            if (item.NetworkObject != null && item.IsSpawned) InstanceFinder.ServerManager.Despawn(item.NetworkObject, DespawnType.Destroy);
            else Destroy(item.gameObject);
            Toast("Скупщик забрал: " + LastSale, CaptureHud.Good);
            // Stage A: the table snapshots its items for the capture save; the sold organ is gone from the next snapshot.
            StartCoroutine(SnapshotNextFrame());
        }

        /// <summary>The crate's ONE fund path (G49 hook 4): every purchase of this buyer credits the shared fund here, once
        /// per key. Ok = paid now or already paid under this key (Replayed). WP02: the same commit grants the organ's XP
        /// (20 each present participant, + the world's first-of-a-kind bonus once) in the team economy's one XP store.</summary>
        private bool TryPaySale(int price, string title, string key, ProductKind kind, out FundResult paid, out int xpEach)
        {
            paid = default;
            xpEach = 0;
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy == null || !economy.IsServer || !economy.ServerCanCommit) return false;
            SaleCommit commit = economy.ServerCommitSale(price, title, key, new[] { kind });
            paid = commit.Fund;
            xpEach = commit.XpEach;
            return paid.Ok;
        }

        private System.Collections.IEnumerator SnapshotNextFrame()
        {
            yield return null;
            var table = CaptureDirector.Instance != null ? CaptureDirector.Instance.Table : null;
            if (table != null) table.Save();
        }

        private static void Toast(string text, Color color)
        {
            var hud = CaptureDirector.Instance != null ? CaptureDirector.Instance.Hud : null;
            if (hud != null) hud.Toast(text, color, 4f);
            else Debug.Log("[SALE] " + text);
        }

        private void OnGUI()
        {
            if (!SaleEnabled) return;
            var director = CaptureDirector.Instance;
            var pawn = director != null ? director.Pawn : null;
            hintShown = pawn != null && pawn.Controlled && (pawn.Position - transform.position).sqrMagnitude < HintRadius * HintRadius;
            if (!hintShown) return;
            var style = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter, fontSize = 20, fontStyle = FontStyle.Bold };
            string text = "Ящик скупщика: положи сюда орган (G) — заплатит сразу";
            var r = new Rect(0f, Screen.height * 0.72f, Screen.width, 32f);
            style.normal.textColor = new Color(0f, 0f, 0f, 0.8f);
            GUI.Label(new Rect(r.x + 2f, r.y + 2f, r.width, r.height), text, style);
            style.normal.textColor = new Color(1f, 0.93f, 0.7f);
            GUI.Label(r, text, style);
        }

        private void OnDrawGizmosSelected()
        {
            Gizmos.matrix = transform.localToWorldMatrix;
            Gizmos.color = new Color(0.3f, 1f, 0.4f, 0.5f);
            Gizmos.DrawWireCube(ZoneCenter, ZoneSize);
        }
    }
}
