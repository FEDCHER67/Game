using System.Collections.Generic;
using NUnit.Framework;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Capture.Tests
{
    /// <summary>EditMode (no Play, no physics): the van cargo body on real components. GreyboxNpc's one knock emitter
    /// (CargoKnocked) fires for a real knock and never when the knock is blocked (padded walls of containment II, tied
    /// hands); VanCargoFitoutV01 applies the purchases idempotently (capacity, rails / rings only with I, padding only
    /// with II, no colliders anywhere) and puts strap fittings on its floor rails.</summary>
    public sealed class CargoContainmentEditorTests
    {
        private readonly List<GameObject> made = new List<GameObject>();
        private readonly List<(GreyboxNpc, Vector3)> heard = new List<(GreyboxNpc, Vector3)>();

        private void Heard(GreyboxNpc npc, Vector3 point) => heard.Add((npc, point));

        [SetUp] public void Listen() { heard.Clear(); GreyboxNpc.CargoKnocked += Heard; }

        [TearDown]
        public void Clean()
        {
            GreyboxNpc.CargoKnocked -= Heard;
            foreach (GameObject g in made) if (g != null) Object.DestroyImmediate(g);
            made.Clear();
        }

        private (GreyboxNpc npc, VanCargoFitoutV01 fitout) LoadedNpcInVan()
        {
            var van = new GameObject("TestVan_CargoBody");
            made.Add(van);
            VanCargoSpace space = van.AddComponent<VanCargoSpace>();
            VanCargoFitoutV01 fitout = VanCargoFitoutV01.Ensure(van);
            var go = new GameObject("TestNpc_Captive");
            made.Add(go);
            GreyboxNpc npc = go.AddComponent<GreyboxNpc>();
            npc.State = NpcState.CargoSeated;
            npc.InCargo = true;
            npc.Carrier = space;
            return (npc, fitout);
        }

        [Test]
        public void Knock_EventFiresInAStockVan_AndWithContainmentI()
        {
            (GreyboxNpc npc, VanCargoFitoutV01 fitout) = LoadedNpcInVan();
            Assert.That(npc.EmitCargoKnock(new Vector3(1f, 2f, 3f)), Is.True);
            fitout.Apply(3, true, false);
            Assert.That(npc.CarrierPadded, Is.False);
            Assert.That(npc.EmitCargoKnock(Vector3.zero), Is.True, "containment I keeps the hands free");
            Assert.That(heard.Count, Is.EqualTo(2));
            Assert.That(heard[0].Item1, Is.SameAs(npc));
            Assert.That(heard[0].Item2, Is.EqualTo(new Vector3(1f, 2f, 3f)));
        }

        [Test]
        public void Knock_BlockedByPaddedWalls_AndByTiedHands_NoEvent()
        {
            (GreyboxNpc npc, VanCargoFitoutV01 fitout) = LoadedNpcInVan();
            fitout.Apply(5, true, true);
            Assert.That(npc.CarrierPadded, Is.True);
            Assert.That(npc.CanKnock, Is.False);
            Assert.That(npc.EmitCargoKnock(Vector3.zero), Is.False);
            fitout.Apply(5, true, false);
            npc.HandsBound = true;
            Assert.That(npc.EmitCargoKnock(Vector3.zero), Is.False);
            Assert.That(heard, Is.Empty);
            // out of the van the padding of that van no longer applies
            npc.HandsBound = false;
            fitout.Apply(5, true, true);
            npc.InCargo = false;
            Assert.That(npc.CarrierPadded, Is.False);
        }

        [Test]
        public void Fitout_AppliesThePurchasesIdempotently_VisualsOnlyWhenBought_NoColliders()
        {
            var (_, fitout) = LoadedNpcInVan();
            fitout.Apply(4, false, false);
            Assert.That(fitout.Capacity, Is.EqualTo(4));
            Transform visuals = fitout.transform.Find(VanCargoFitoutV01.VisualsName);
            Assert.That(visuals, Is.Not.Null);
            Assert.That(visuals.Find("Rails").gameObject.activeSelf, Is.False);
            Assert.That(visuals.Find("Padding").gameObject.activeSelf, Is.False);
            int version = fitout.Version;
            fitout.Apply(4, false, false);
            Assert.That(fitout.Version, Is.EqualTo(version), "the same purchases change nothing");
            Assert.That(fitout.Matches(4, false, false), Is.True);

            fitout.Apply(5, true, true);
            Assert.That(visuals.Find("Rails").gameObject.activeSelf, Is.True);
            Assert.That(visuals.Find("Padding").gameObject.activeSelf, Is.True);
            Transform rings = visuals.Find("Rings");
            for (int i = 0; i < VanCargoFitoutV01.MaxCapacity; i++)
                Assert.That(rings.Find("Ring_" + i).gameObject.activeSelf, Is.True, "five rings with capacity II");
            fitout.Apply(3, true, true);
            Assert.That(rings.Find("Ring_3").gameObject.activeSelf || rings.Find("Ring_4").gameObject.activeSelf, Is.False, "rings above the capacity hidden");
            Assert.That(fitout.GetComponentsInChildren<Collider>(true), Is.Empty, "the fit-out never touches anyone");
            Assert.That(fitout.transform.Find(VanCargoFitoutV01.AnchorsName).Find("Rail_0_A"), Is.Not.Null, "anchors created for the current van");
        }

        [Test]
        public void Fitout_StrapFittingSitsOnTheNearestFloorRail()
        {
            var (_, fitout) = LoadedNpcInVan();
            fitout.Apply(5, true, false);
            Vector3 anchor = fitout.StrapAnchor(fitout.transform.TransformPoint(new Vector3(-0.1f, 0.8f, -1.0f)));
            Assert.That(anchor.x, Is.EqualTo(-0.72f).Within(1e-4f), "the left rail");
            Assert.That(anchor.z, Is.EqualTo(-1.0f).Within(1e-4f));
            Assert.That(anchor.y, Is.EqualTo(0.562f).Within(1e-3f), "on the rail top");
            anchor = fitout.StrapAnchor(fitout.transform.TransformPoint(new Vector3(0.7f, 0.6f, 3f)));
            Assert.That(anchor.x, Is.EqualTo(0.72f).Within(1e-4f));
            Assert.That(anchor.z, Is.EqualTo(0.36f).Within(1e-4f), "clamped to the rail's end");
        }
    }
}
