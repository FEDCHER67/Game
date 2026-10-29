using NUnit.Framework;

namespace OnlyVolunteers.Economy.Tests
{
    /// <summary>The E conversation with the workshop mechanic (29.10 fix, "E at the mechanic does nothing"): reach is measured
    /// from his body wherever he walks (flat, same level) or by the crosshair on him, never from his physics capsule; the van
    /// keeps its E unless the player looks at him; the server accepts every line chosen in an open menu.</summary>
    public sealed class WorkshopMechanicTalkReachTests
    {
        private const float Eye = 1.65f;

        /// <summary>A player standing at (x, z) from the mechanic's feet, eye at 1.65 m, looking at the point (lx, ly, lz)
        /// (relative to his feet).</summary>
        private static MechanicTalkInput At(float x, float z, float lx = float.NaN, float ly = 1.2f, float lz = 0f, float dy = 0f)
        {
            var i = new MechanicTalkInput { HasPlayer = true, EconomyReady = true, SightClear = true, Dx = x, Dy = dy, Dz = z, EyeX = x, EyeY = dy + Eye, EyeZ = z };
            if (float.IsNaN(lx)) { lx = 0f; ly = 1.2f; lz = 0f; } // default: looks at his chest
            i.HasView = true;
            i.ViewX = lx - i.EyeX; i.ViewY = ly - i.EyeY; i.ViewZ = lz - i.EyeZ;
            return i;
        }

        private static MechanicTalkInput LookingAway(float x, float z)
        {
            MechanicTalkInput i = At(x, z);
            i.ViewX = x; i.ViewY = 0f; i.ViewZ = z; // straight away from him
            return i;
        }

        [Test]
        public void Close_by_opens_whether_he_idles_walks_or_attends()
        {
            // the rule only knows where his body is: idle at home, mid-leg on his route or turned to the player, all the same
            Assert.That(MechanicTalkReach.Check(LookingAway(0.9f, 0.4f)), Is.EqualTo(MechanicTalkRefusal.None), "right beside him (his capsule is off then)");
            Assert.That(MechanicTalkReach.Check(LookingAway(2.0f, -1.5f)), Is.EqualTo(MechanicTalkRefusal.None), "2.5 m, not looking");
            Assert.That(MechanicTalkReach.Check(LookingAway(2.95f, 0f)), Is.EqualTo(MechanicTalkRefusal.None), "just inside 3 m");
            Assert.That(MechanicTalkReach.Check(LookingAway(3.2f, 0f)), Is.EqualTo(MechanicTalkRefusal.TooFar), "3.2 m, not looking at him");
        }

        [Test]
        public void Reach_is_horizontal_so_a_step_or_the_lift_floor_does_not_cut_it()
        {
            // the old rule was a 3 m sphere from his feet: 2.9 m away and 0.9 m higher failed
            Assert.That(MechanicTalkReach.Check(At(2.9f, 0f, dy: 0.9f)), Is.EqualTo(MechanicTalkRefusal.None));
            Assert.That(MechanicTalkReach.Check(At(1.0f, 0f, dy: -1.8f)), Is.EqualTo(MechanicTalkRefusal.OtherLevel), "down in the pit");
            Assert.That(MechanicTalkReach.Check(At(1.0f, 0f, dy: 2.5f)), Is.EqualTo(MechanicTalkRefusal.OtherLevel), "on the roof");
        }

        [Test]
        public void Looking_at_him_reaches_farther_with_a_clear_sight_line()
        {
            Assert.That(MechanicTalkReach.Check(At(3.8f, 0f)), Is.EqualTo(MechanicTalkRefusal.None), "3.8 m, crosshair on his chest");
            Assert.That(MechanicTalkReach.Check(At(0f, 4.2f, 0f, 0.4f, 0f)), Is.EqualTo(MechanicTalkRefusal.None), "4.2 m, crosshair at his knees");
            Assert.That(MechanicTalkReach.Check(At(5.2f, 0f)), Is.EqualTo(MechanicTalkRefusal.TooFar), "5.2 m is beyond the aim reach");
            MechanicTalkInput wall = At(3.8f, 0f);
            wall.SightClear = false;
            Assert.That(MechanicTalkReach.Check(wall), Is.EqualTo(MechanicTalkRefusal.TooFar), "a wall / the van between");
            MechanicTalkInput over = At(3.8f, 0f, 0f, 2.6f, 0f);
            Assert.That(MechanicTalkReach.Check(over), Is.EqualTo(MechanicTalkRefusal.TooFar), "looking over his head");
            MechanicTalkInput beside = At(3.8f, 0f, 0f, 1.2f, 1.2f);
            Assert.That(MechanicTalkReach.Check(beside), Is.EqualTo(MechanicTalkRefusal.TooFar), "looking 1.2 m beside him");
        }

        [Test]
        public void Aim_test_is_geometric()
        {
            Assert.That(MechanicTalkReach.Aimed(2f, Eye, 0f, -1f, -0.2f, 0f), Is.True, "at him, slightly down");
            Assert.That(MechanicTalkReach.Aimed(2f, Eye, 0f, 1f, 0f, 0f), Is.False, "away from him");
            Assert.That(MechanicTalkReach.Aimed(2f, Eye, 0f, 0f, -1f, 0f), Is.False, "straight down at own feet");
            Assert.That(MechanicTalkReach.Aimed(2f, Eye, 0f, 0f, 0f, 0f), Is.False, "no direction");
            Assert.That(MechanicTalkReach.Aimed(2f, Eye, 0.45f, -1f, -0.2f, 0f), Is.True, "0.45 m off his axis still counts (his belly)");
        }

        [Test]
        public void The_van_keeps_its_E_unless_the_player_looks_at_him()
        {
            MechanicTalkInput away = LookingAway(1.5f, 0f);
            away.VanOffersE = true;
            Assert.That(MechanicTalkReach.Check(away), Is.EqualTo(MechanicTalkRefusal.VanOwnsE));
            MechanicTalkInput looking = At(1.5f, 0f);
            looking.VanOffersE = true;
            Assert.That(MechanicTalkReach.Check(looking), Is.EqualTo(MechanicTalkRefusal.None));
        }

        [Test]
        public void Menus_missing_player_used_E_and_a_loading_economy_refuse()
        {
            MechanicTalkInput i = At(1.5f, 0f);
            i.MenuOpen = true;
            Assert.That(MechanicTalkReach.Check(i), Is.EqualTo(MechanicTalkRefusal.MenuOpen));
            i = At(1.5f, 0f);
            i.HasPlayer = false;
            Assert.That(MechanicTalkReach.Check(i), Is.EqualTo(MechanicTalkRefusal.NoPlayer));
            i = At(1.5f, 0f);
            i.ETaken = true;
            Assert.That(MechanicTalkReach.Check(i), Is.EqualTo(MechanicTalkRefusal.ETaken));
            i = At(1.5f, 0f);
            i.EconomyReady = false;
            Assert.That(MechanicTalkReach.Check(i), Is.EqualTo(MechanicTalkRefusal.EconomyLoading));
        }

        [Test]
        public void An_open_talk_and_the_server_agree_with_the_reach()
        {
            // the menu stays open within the leash of him or of where it was opened
            Assert.That(MechanicTalkReach.KeepOpen(5.0f, 0f, 9f, 0f), Is.True);
            Assert.That(MechanicTalkReach.KeepOpen(9f, 0f, 1f, 0f), Is.True, "he walked to the lift box, the player stayed");
            Assert.That(MechanicTalkReach.KeepOpen(7f, 0f, 7f, 0f), Is.False);
            // whatever the client may open from, the server accepts the M06 / lift request
            for (float d = 0f; d <= MechanicTalkReach.Leash; d += 0.25f)
                Assert.That(MechanicTalkReach.ServerAccepts(d, 0.5f, 0f), Is.True, "server refuses an open menu at " + d);
            Assert.That(MechanicTalkReach.ServerAccepts(MechanicTalkReach.ServerReach + 0.5f, 0f, 0f), Is.False);
            Assert.That(MechanicTalkReach.ServerAccepts(1f, 4f, 0f), Is.False, "another floor");
        }
    }
}
