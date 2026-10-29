using System.Collections.Generic;
using NUnit.Framework;

namespace OnlyVolunteers.Session.Tests
{
    public sealed class PlayerAppearanceTests
    {
        static PlayerAppearance Custom()
        {
            var a = AppearanceRules.Default();
            a.skin = "Skin_05"; a.hair = "Hair_02"; a.hairColour = "hc_ginger"; a.facialHair = "Beard_03";
            a.top = "Top_02"; a.topColour = "Sw_07"; a.bottom = "Bottom_02"; a.bottomColour = "Sw_03"; a.accessory = "Head_02";
            return a;
        }

        [Test] public void DefaultIsValidInEverySlotAndStable()
        {
            var a = AppearanceRules.Default();
            foreach (var s in AppearanceCatalogV01.Slots) Assert.True(AppearanceCatalogV01.IsValid(s, a.Get(s)), s.ToString());
            Assert.True(a.SameAs(AppearanceRules.Default()));
            Assert.AreEqual("Sw_01", a.topColour); Assert.AreEqual("Sw_05", a.bottomColour); // the parts manifest default selection
            Assert.AreEqual("Hair_03", a.hair); Assert.AreEqual("Skin_02", a.skin);
        }

        [Test] public void CatalogueIsCompactAndIdsAreUnique()
        {
            Assert.AreEqual(5, AppearanceCatalogV01.Options(AppearanceSlot.Hair).Count); // 29.10: ~5 per aspect
            Assert.AreEqual(5, AppearanceCatalogV01.Options(AppearanceSlot.Top).Count); // 29.10: ~5 per aspect
            Assert.AreEqual(5, AppearanceCatalogV01.Options(AppearanceSlot.Bottom).Count); // 29.10: ~5 per aspect
            Assert.AreEqual(5, AppearanceCatalogV01.Options(AppearanceSlot.Accessory).Count, "nothing + cap + beanie + bandana + glasses");
            Assert.AreEqual(8, AppearanceCatalogV01.Options(AppearanceSlot.TopColour).Count, "the manifest clothing swatches");
            Assert.AreEqual(5, AppearanceCatalogV01.Options(AppearanceSlot.FacialHair).Count);
            foreach (var s in AppearanceCatalogV01.Slots)
            {
                var ids = new HashSet<string>();
                foreach (var o in AppearanceCatalogV01.Options(s)) Assert.True(ids.Add(o.Id), s + " " + o.Id);
                if (AppearanceCatalogV01.IsColourSlot(s))
                    foreach (var o in AppearanceCatalogV01.Options(s)) StringAssert.IsMatch("^#[0-9A-F]{6}$", o.Hex);
            }
        }

        [Test] public void WireRoundTripKeepsEveryChoice()
        {
            var a = Custom();
            string wire = AppearanceRules.Encode(a);
            StringAssert.StartsWith(AppearanceRules.WirePrefix + ";", wire);
            Assert.True(AppearanceRules.TryDecode(wire, out var back));
            Assert.True(a.SameAs(back));
        }

        [Test] public void UnknownOrMissingCosmeticsFallBackPerSlotOnly()
        {
            var replaced = new List<AppearanceSlot>();
            Assert.True(AppearanceRules.TryDecode("ova1;Skin_05;hair_dreadlocks_v9;hc_ginger", out var a, replaced));
            Assert.AreEqual("Skin_05", a.skin, "a known id is kept");
            Assert.AreEqual("Hair_03", a.hair, "an unknown (newer/older) cosmetic becomes the default");
            Assert.AreEqual("hc_ginger", a.hairColour);
            Assert.AreEqual(AppearanceCatalogV01.DefaultId(AppearanceSlot.Top), a.top, "missing fields get defaults");
            CollectionAssert.Contains(replaced, AppearanceSlot.Hair);
            CollectionAssert.DoesNotContain(replaced, AppearanceSlot.Skin);
        }

        [Test] public void AfternoonV01IdsMigrateToTheNearestPart()
        {
            var replaced = new List<AppearanceSlot>();
            Assert.True(AppearanceRules.TryDecode("ova1;skin_03;hair_short;hc_darkbrown;fh_none;top_tshirt;c_grey;bottom_jeans;c_navy;acc_none", out var a, replaced));
            Assert.AreEqual("Skin_02", a.skin); Assert.AreEqual("Hair_03", a.hair); Assert.AreEqual("Beard_01", a.facialHair);
            Assert.AreEqual("Top_01", a.top); Assert.AreEqual("Sw_02", a.topColour); Assert.AreEqual("Bottom_01", a.bottom);
            Assert.AreEqual("Sw_05", a.bottomColour); Assert.AreEqual("Head_01", a.accessory);
            Assert.AreEqual(0, replaced.Count, "an old id is migrated, not reset");
            Assert.AreEqual("Head_02", AppearanceCatalogV01.Migrate(AppearanceSlot.Accessory, "acc_cap"));
            Assert.IsNull(AppearanceCatalogV01.Migrate(AppearanceSlot.Top, "acc_cap"), "an alias of another slot does not migrate");
        }

        [Test] public void NewerBuildExtraFieldsAreIgnored()
        {
            string wire = AppearanceRules.Encode(Custom()) + ";glasses_round;tattoo_1";
            Assert.True(AppearanceRules.TryDecode(wire, out var a));
            Assert.True(Custom().SameAs(a));
        }

        [Test] public void GarbageIsRefusedWithDefaultLook()
        {
            foreach (string bad in new[] { null, "", "hello", "ova2;skin_01", new string('x', AppearanceRules.MaxWireLength + 1) })
            {
                Assert.False(AppearanceRules.TryDecode(bad, out var a), bad ?? "null");
                Assert.True(a.SameAs(AppearanceRules.Default()));
            }
        }

        [Test] public void SanitizeNullAndTamperedValues()
        {
            Assert.True(AppearanceRules.Sanitize(null).SameAs(AppearanceRules.Default()));
            var a = Custom(); a.topColour = "#FF00FF"; a.skin = "Skin_05;hair=x";
            var s = AppearanceRules.Sanitize(a);
            Assert.AreEqual("Sw_01", s.topColour); Assert.AreEqual("Skin_02", s.skin); Assert.AreEqual("Hair_02", s.hair);
        }

        [Test] public void CustomiserOffersOnlyPresentMeshPartsButAlwaysColours()
        {
            Assert.AreEqual(0, AppearanceRules.Selectable(AppearanceSlot.Hair, null).Count, "no model yet: no imaginary hairstyles");
            Assert.AreEqual(5, AppearanceRules.Selectable(AppearanceSlot.Skin, null).Count);
            System.Func<AppearanceSlot, string, bool> present = (slot, id) => id == "Hair_03" || id == "Hair_05";
            var hair = AppearanceRules.Selectable(AppearanceSlot.Hair, present);
            Assert.AreEqual(2, hair.Count);
            Assert.AreEqual("Hair_05", AppearanceRules.Cycle(AppearanceSlot.Hair, "Hair_03", 1, present));
            Assert.AreEqual("Hair_03", AppearanceRules.Cycle(AppearanceSlot.Hair, "Hair_05", 1, present), "wraps");
            Assert.AreEqual("Hair_04", AppearanceRules.Cycle(AppearanceSlot.Hair, "Hair_04", 1, null), "nothing selectable: keeps current");
            Assert.AreEqual("Skin_01", AppearanceRules.Cycle(AppearanceSlot.Skin, "Skin_02", -1, null));
        }

        [Test] public void BookNeverCopiesAnotherPlayersLook()
        {
            var book = new AppearanceBook();
            var host = Custom();
            Assert.True(book.Submit(PlayerIds.Host, AppearanceRules.Encode(host), out _));
            const string friend = "0123456789abcdef0123456789abcdef";
            Assert.True(book.Get(friend).SameAs(AppearanceRules.Default()), "a player without a submission is default, not the host's look");
            var mine = AppearanceRules.Default(); mine.hairColour = "hc_blond";
            Assert.True(book.Submit(friend, AppearanceRules.Encode(mine), out _));
            // reconnect: the same id submits again from its own profile and replaces only its own entry
            mine.top = "Top_03";
            Assert.True(book.Submit(friend, AppearanceRules.Encode(mine), out var applied));
            Assert.True(applied.SameAs(book.Get(friend)));
            Assert.True(host.SameAs(book.Get(PlayerIds.Host)));
            Assert.AreEqual(2, book.Count);
        }

        [Test] public void BookRefusesInvalidIdsAndGarbage()
        {
            var book = new AppearanceBook();
            Assert.False(book.Submit("client:3", AppearanceRules.Encode(Custom()), out _), "temporary ids are not stable identities");
            Assert.False(book.Submit("abc", AppearanceRules.Encode(Custom()), out _));
            Assert.False(book.Submit("0123456789abcdef", "garbage", out _));
            Assert.AreEqual(0, book.Count);
        }

        [Test] public void ProfileKeyIsPerPlayerGuid()
        {
            Assert.AreNotEqual(AppearanceRules.ProfileKey("aaaaaaaa1"), AppearanceRules.ProfileKey("bbbbbbbb2"));
            StringAssert.StartsWith(AppearanceRules.ProfileKeyPrefix, AppearanceRules.ProfileKey("aaaaaaaa1"));
        }
    }
}
