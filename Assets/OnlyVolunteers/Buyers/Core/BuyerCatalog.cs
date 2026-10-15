using System;

namespace OnlyVolunteers.Buyers
{
    /// <summary>Only unresolved presets live here. All confirmed tables below are fixed.</summary>
    public sealed class BuyerTuning
    {
        public int CounterAfter5 = 0;
        public int CounterAfter10 = 5;
        public int CounterAfter20 = 10;
        public int MoneyDecimalPlaces = 0;
        internal BuyerTuning Copy()
        {
            if (CounterAfter5 != 0 || CounterAfter10 < 0 || CounterAfter10 >= 10 ||
                CounterAfter20 < 0 || CounterAfter20 >= 20 || MoneyDecimalPlaces < 0 || MoneyDecimalPlaces > 2)
                throw new ArgumentOutOfRangeException(nameof(BuyerTuning));
            return (BuyerTuning)MemberwiseClone();
        }
        internal int Counter(int ask) => ask == 5 ? CounterAfter5 : ask == 10 ? CounterAfter10 : CounterAfter20;
    }

    public static class BuyerCatalog
    {
        public const string BloodBuyer = "C01";
        // Canon has not finally assigned the universal first buyer to C02.
        public const string OrganBuyer = "ORGANS_01";
        public const long Hour = 3600;
        public const long Day = 24 * Hour;
        private static readonly int[,] Chances = { {40,20,5}, {55,35,15}, {70,50,25}, {85,65,40}, {95,80,60} };
        private static readonly string[] RespectNames = { "ууу хиляк", "новобранец", "бывалый", "проверенный", "своячок" };
        private static readonly string[] QualityNames = { "Убитое", "Сойдёт", "Хорошее", "Отличное", "Идеальное" };
        // Palette preset matches the existing operation presentation; the specs define color families only.
        private static readonly string[] QualityColors = { "#8C7B6B", "#C2B23A", "#4DC25A", "#3E8DFF", "#A75CFF" };
        private static readonly decimal[] Multipliers = { .3m, 1m, 1.6m, 2.6m, 4.2m };

        public static bool IsOrgan(ProductKind kind) => kind >= ProductKind.Kidney && kind <= ProductKind.Brain;
        public static int RespectLevel(int respect) => Math.Min(5, Math.Max(0, respect) / 20 + 1);
        public static string RespectName(int respect) => RespectNames[RespectLevel(respect) - 1];
        private static int TierIndex(QualityTier tier)
        {
            int value = (int)tier;
            if (value < 1 || value > 5) throw new ArgumentOutOfRangeException(nameof(tier));
            return value - 1;
        }
        public static string QualityLabel(QualityTier tier) => QualityNames[TierIndex(tier)] + " " + ((int)tier * 20) + "%";
        public static string QualityColor(QualityTier tier) => QualityColors[TierIndex(tier)];
        public static decimal TierMultiplier(QualityTier tier) => Multipliers[TierIndex(tier)];
        public static decimal BasePrice(ProductKind kind)
        {
            switch (kind)
            {
                case ProductKind.Kidney: return 250;
                case ProductKind.Liver: return 350;
                case ProductKind.Lungs: return 450;
                case ProductKind.Heart: return 1000;
                case ProductKind.Eye: return 200;
                case ProductKind.Brain: return 1200;
                case ProductKind.BloodBag: return 50;
                case ProductKind.IntroSyringe: return 10;
                default: throw new ArgumentOutOfRangeException(nameof(kind));
            }
        }
        public static int FirstTypeBonus(ProductKind kind)
        {
            switch (kind)
            {
                case ProductKind.Kidney: case ProductKind.Liver: case ProductKind.Eye: return 100;
                case ProductKind.Lungs: return 150;
                case ProductKind.Heart: return 200;
                case ProductKind.Brain: return 250;
                default: throw new ArgumentOutOfRangeException(nameof(kind));
            }
        }
        public static int UpgradeCost(int nextLevel)
        {
            switch (nextLevel)
            {
                case 1: return 500;
                case 2: return 1000;
                case 3: return 2000;
                default: throw new ArgumentOutOfRangeException(nameof(nextLevel));
            }
        }
        public static int NegotiationChance(int respect, int skillLevel, int askPercent)
        {
            if (skillLevel < 0 || skillLevel > 3) throw new ArgumentOutOfRangeException(nameof(skillLevel));
            int col = askPercent == 5 ? 0 : askPercent == 10 ? 1 : askPercent == 20 ? 2 : -1;
            if (col < 0) throw new ArgumentOutOfRangeException(nameof(askPercent));
            return Math.Min(95, Chances[RespectLevel(respect) - 1, col] + skillLevel * 5);
        }
        public static decimal SaturationMultiplier(int unitsAlreadySold)
        {
            if (unitsAlreadySold < 0) throw new ArgumentOutOfRangeException(nameof(unitsAlreadySold));
            return 1m - Math.Min(6, unitsAlreadySold) * .05m;
        }
        public static decimal UnitPrice(ProductKind kind, QualityTier tier, int negotiatedPercent,
            bool onTimeSpecial, bool deliveredCooled, int unitsAlreadySold, bool isSpecial)
        {
            if (negotiatedPercent < 0 || negotiatedPercent > 20) throw new ArgumentOutOfRangeException(nameof(negotiatedPercent));
            if (!IsOrgan(kind)) return BasePrice(kind) * (kind == ProductKind.IntroSyringe ? 1m : 1m + negotiatedPercent / 100m);
            return BasePrice(kind) * TierMultiplier(tier) * (1m + negotiatedPercent / 100m) *
                (onTimeSpecial ? 1.25m : 1m) * (deliveredCooled ? 1m : .9m) *
                (isSpecial ? 1m : SaturationMultiplier(unitsAlreadySold));
        }
        public static ProductKind OrderKind(OrderTemplate template) => template == OrderTemplate.HamletKidney ? ProductKind.Kidney : ProductKind.Brain;
        public static QualityTier OrderMinimum(OrderTemplate template) => template == OrderTemplate.HamletKidney ? QualityTier.Good : QualityTier.Perfect;
        public static string OrderNpcType(OrderTemplate template) => template == OrderTemplate.HamletKidney ? "HAMLET_BODYBUILDER" : "OLD_STREAMER";
    }
}
