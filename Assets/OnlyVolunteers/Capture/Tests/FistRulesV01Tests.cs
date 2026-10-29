using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Capture.Tests
{
    /// <summary>Fist anti-spam (Fedya 30.10): the per-player swing gate and the per-NPC repeat-contact resistance.</summary>
    public sealed class FistRulesV01Tests
    {
        private static readonly float[] Table = FistResistanceRulesV01.DefaultMultipliers;
        private const float Recovery = FistResistanceRulesV01.DefaultRecoverySeconds;

        // ---------- the swing gate ----------

        [Test]
        public void Gate_OneSecondBetweenAcceptedStarts_AMissConsumesIt_PressesDuringTheCooldownAreDropped()
        {
            var gate = new FistSwingGateV01();
            Assert.IsTrue(gate.TryAccept(gate.NextRequestId(), 10f, 1f), "first swing (it may miss: the gate does not care)");
            Assert.IsFalse(gate.TryAccept(gate.NextRequestId(), 10.5f, 1f), "half a second later: dropped");
            Assert.IsFalse(gate.TryAccept(gate.NextRequestId(), 10.999f, 1f), "just before the boundary: dropped");
            Assert.IsTrue(gate.TryAccept(gate.NextRequestId(), 11f, 1f), "at exactly 1.0 s: accepted");
            Assert.AreEqual(12f, gate.NextAllowed, 1e-5f, "measured from the accepted start, the dropped presses queue nothing");
            // a burst of presses (holding / mashing) during one cooldown is one swing only
            int accepted = 0;
            for (int i = 0; i < 30; i++) if (gate.TryAccept(gate.NextRequestId(), 11.02f + i * 0.03f, 1f)) accepted++;
            Assert.AreEqual(0, accepted);
        }

        [Test]
        public void Gate_DuplicateRequestReturnsThePriorOutcome_AndNeverSwingsTwice()
        {
            var gate = new FistSwingGateV01();
            Assert.AreEqual(FistSwingResult.Accepted, gate.Request(7, 5f, 1f, out bool replay));
            Assert.IsFalse(replay);
            Assert.AreEqual(FistSwingResult.Accepted, gate.Request(7, 6.5f, 1f, out replay), "same id: the recorded outcome");
            Assert.IsTrue(replay, "...flagged as a replay, so the caller does not swing again");
            Assert.IsFalse(gate.TryAccept(7, 6.5f, 1f), "a replayed id is never a new swing, even after the cooldown");
            Assert.AreEqual(FistSwingResult.CoolingDown, gate.Request(8, 5.5f, 1f, out replay));
            Assert.AreEqual(FistSwingResult.CoolingDown, gate.Request(8, 9f, 1f, out replay), "the rejection is replayed too");
            Assert.IsTrue(replay);
            Assert.IsFalse(gate.TryAccept(3, 50f, 1f), "an older id than the last is never accepted");
            Assert.IsTrue(gate.TryAccept(9, 6.01f, 1f), "a fresh id after the cooldown is");
        }

        // ---------- the repeat-contact resistance ----------

        [Test]
        public void Resistance_ExactProgression_AndZeroStaysZero()
        {
            var npc = new FistResistanceV01();
            float[] want = { 1f, 0.7f, 0.45f, 0.25f, 0.1f, 0f, 0f, 0f };
            for (int i = 0; i < want.Length; i++)
            {
                float m = FistResistanceRulesV01.Contact(ref npc, true, Recovery, Table, out int index);
                Assert.AreEqual(i + 1, index);
                Assert.AreEqual(want[i], m, 1e-6f, $"contact {i + 1}");
                FistResistanceRulesV01.Tick(ref npc, 1f, true, Recovery); // a second apart, the NPC still stunned
            }
            // an otherwise 8 s stun: 8 / 5.6 / 3.6 / 2 / 0.8 / 0
            Assert.AreEqual(5.6f, 8f * FistResistanceRulesV01.Multiplier(2, Table), 1e-4f);
            Assert.AreEqual(0.8f, 8f * FistResistanceRulesV01.Multiplier(5, Table), 1e-4f);
            Assert.AreEqual(0f, 8f * FistResistanceRulesV01.Multiplier(6, Table));
            Assert.AreEqual(1f, FistResistanceRulesV01.Multiplier(3, null), "no table: every contact stuns fully (other weapons)");
        }

        [Test]
        public void Resistance_BelongsToTheNpc_SharedByAttackers_SeparatePerNpc()
        {
            var a = new FistResistanceV01();
            var b = new FistResistanceV01();
            // two attackers alternating on A: the sequence is A's, not per attacker
            FistResistanceRulesV01.Contact(ref a, true, Recovery, Table, out _); // player 1
            FistResistanceRulesV01.Contact(ref a, true, Recovery, Table, out _); // player 2
            float third = FistResistanceRulesV01.Contact(ref a, true, Recovery, Table, out int index); // player 1 again
            Assert.AreEqual(3, index);
            Assert.AreEqual(0.45f, third, 1e-6f);
            // B is untouched by A's sequence
            float first = FistResistanceRulesV01.Contact(ref b, false, Recovery, Table, out index);
            Assert.AreEqual(1, index);
            Assert.AreEqual(1f, first);
        }

        [Test]
        public void Stun_PositiveWeakHitNeverShortens_ZeroHitChangesNothingAndDoesNotKnockDown()
        {
            Assert.AreEqual(6f, FistResistanceRulesV01.StunAfter(6f, 0.8f), "10 % (0.8 s) on 6 s left: still 6 s");
            Assert.AreEqual(5.6f, FistResistanceRulesV01.StunAfter(2f, 5.6f), 1e-6f, "a longer contribution raises it (not adds)");
            Assert.AreEqual(3f, FistResistanceRulesV01.StunAfter(3f, 0f), "zero: unchanged");
            Assert.AreEqual(0f, FistResistanceRulesV01.StunAfter(0f, 0f), "zero on a free NPC: no stun at all (not a 0.1 s minimum)");
            Assert.IsFalse(FistResistanceRulesV01.Stuns(0f), "a zero contact never restarts the knockdown / get-up / phase");
            Assert.IsTrue(FistResistanceRulesV01.Stuns(0.8f));
        }

        [Test]
        public void Recovery_EightActiveSecondsAndOnlyOnceStunAndGetUpAreOver()
        {
            var npc = new FistResistanceV01();
            for (int i = 0; i < 4; i++) FistResistanceRulesV01.Contact(ref npc, true, Recovery, Table, out _);
            // 20 s pass but he is still down (stun or get-up running): no recovery
            for (int i = 0; i < 20; i++) FistResistanceRulesV01.Tick(ref npc, 1f, true, Recovery);
            Assert.AreEqual(4, npc.contacts);
            Assert.AreEqual(0.1f, Multiplier(npc), 1e-6f, "the next contact would be the fifth");
            // up again: recovers at once since the quiet time has long passed
            FistResistanceRulesV01.Tick(ref npc, 0.016f, false, Recovery);
            Assert.AreEqual(0, npc.contacts, "fresh");

            var fresh = new FistResistanceV01();
            FistResistanceRulesV01.Contact(ref fresh, false, Recovery, Table, out _);
            for (int i = 0; i < 7; i++) FistResistanceRulesV01.Tick(ref fresh, 1f, false, Recovery);
            Assert.AreEqual(1, fresh.contacts, "7 s: not yet");
            float second = FistResistanceRulesV01.Contact(ref fresh, false, Recovery, Table, out _);
            Assert.AreEqual(0.7f, second, 1e-6f, "a hit at 7 s continues the sequence...");
            Assert.AreEqual(0f, fresh.quietSeconds, "...and restarts its quiet time");
            for (int i = 0; i < 8; i++) FistResistanceRulesV01.Tick(ref fresh, 1f, false, Recovery);
            Assert.AreEqual(0, fresh.contacts, "8 quiet active seconds, nothing running: starts over");
            Assert.AreEqual(1f, FistResistanceRulesV01.Contact(ref fresh, false, Recovery, Table, out _));

            var zero = new FistResistanceV01 { contacts = 6 };
            FistResistanceRulesV01.Tick(ref zero, 5f, false, Recovery);
            Assert.AreEqual(0f, FistResistanceRulesV01.Contact(ref zero, false, Recovery, Table, out _), "a zero hit at 5 s...");
            FistResistanceRulesV01.Tick(ref zero, 5f, false, Recovery);
            Assert.AreEqual(7, zero.contacts, "...still moved the quiet-time boundary (5 s after it: not recovered)");
            FistResistanceRulesV01.Tick(ref zero, 0f, false, Recovery);
            Assert.AreEqual(7, zero.contacts, "no time passing never recovers it (paused game)");
        }

        [Test]
        public void Save_RemainingActiveTime_RoundTripsThroughTheNpcSaveBlock_AndOldSavesStartFresh()
        {
            var npc = new FistResistanceV01();
            for (int i = 0; i < 3; i++) FistResistanceRulesV01.Contact(ref npc, true, Recovery, Table, out _);
            FistResistanceRulesV01.Tick(ref npc, 2.5f, true, Recovery);
            var save = new CaptureNpcSave
            {
                fistContacts = npc.contacts,
                fistRecoverLeft = FistResistanceRulesV01.RecoverLeft(npc, Recovery),
            };
            Assert.AreEqual(5.5f, save.fistRecoverLeft, 1e-5f, "remaining active seconds, not a clock time");
            string json = JsonUtility.ToJson(save);
            var back = JsonUtility.FromJson<CaptureNpcSave>(json);
            var restored = FistResistanceRulesV01.FromSave(back.fistContacts, back.fistRecoverLeft, Recovery);
            Assert.AreEqual(3, restored.contacts, "the sequence survives a save/load (and a representation change: it is the NPC's)");
            Assert.AreEqual(2.5f, restored.quietSeconds, 1e-5f);
            Assert.AreEqual(0.25f, FistResistanceRulesV01.Contact(ref restored, true, Recovery, Table, out _), 1e-6f, "the fourth");

            // a save written before 30.10 has no fist fields
            var old = JsonUtility.FromJson<CaptureNpcSave>("{\"npcState\":1,\"stunLeft\":3.0,\"stunTotal\":8.0}");
            var fromOld = FistResistanceRulesV01.FromSave(old.fistContacts, old.fistRecoverLeft, Recovery);
            Assert.AreEqual(0, fromOld.contacts);
            Assert.AreEqual(1f, FistResistanceRulesV01.Contact(ref fromOld, true, Recovery, Table, out _), "old saves: a fresh sequence");
        }

        private static float Multiplier(FistResistanceV01 s) => FistResistanceRulesV01.Multiplier(s.contacts + 1, Table);
    }
}
