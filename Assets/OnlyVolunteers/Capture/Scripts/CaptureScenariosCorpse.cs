using System.Collections;
using System.Linq;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    public sealed partial class CaptureScenarioDriver
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator CorpseProbe(string scenarioName)
        {
            Teardown();
            var probe = gameObject.GetComponent<OperationNetworkProbe>(); if (probe == null) probe = gameObject.AddComponent<OperationNetworkProbe>();
            OperationNetworkProbe.EvidenceRoot = output;
            yield return Frames(2); probe.Begin(scenarioName);
            float end = Time.time + 160f;
            while (probe.Busy && Time.time < end) yield return null;
            foreach (var line in probe.Log) if (line.Contains(" PASS ") || line.Contains(" FAIL ")) Line("  ops: " + line);
            Check(!probe.Busy && probe.LastResult == "PASS", scenarioName + " real-input result: " + probe.LastResult);
            SetupDevices(); SetupCapture(pawn.ViewCamera);
        }
        private IEnumerator Corpse()
        {
            var npc = SpawnLocal("SausageBuddy_B", d.Table.transform.position + Vector3.forward * 2f, 0f);
            yield return Frames(2);
            float impulse = npc.HitImpulse; npc.HitImpulse = 0f;
            npc.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, npc.Center); npc.HitImpulse = impulse;
            yield return Frames(2);
            // Initial patient fixture; all straps, injections, corpse grab, R packing, G/E/LMB and water release below use real devices.
            npc.Ragdoll.PlaceLying(d.Table.transform.position + Vector3.up * 0.7f, d.Table.transform.forward, true);
            yield return WaitFor(() => d.Table.HasPatient && d.Table.State.aligned, 8f, "corpse scenario patient fixture admitted under the normal cloud");
            yield return CorpseProbe("cl-bag"); // Rework 2026-10-18: the bag is the corpse ragdoll, wrapped
        }
        private IEnumerator CorpseReload()
        {
            yield return new WaitForSeconds(1.0f);
            string id = OperationNetworkProbe.LastBagId;
            var bag = d.Disposal.Corpses.FirstOrDefault(x => x != null && x.PatientId == id);
            var saved = JsonUtility.FromJson<CaptureSaveData>(System.IO.File.ReadAllText(d.SavePath));
            var data = saved.corpses.FirstOrDefault(x => x.facts.patientId == id);
            Check(bag != null && bag.Bagged && bag.Ragdoll.Active && bag.Ragdoll.DynamicBodies == 11, "reload restores the same body bag as a wrapped ragdoll (11 bodies)");
            var wrap = bag != null ? bag.GetComponent<OperationBodyBagWrap>() : null;
            Check(wrap != null && wrap.Applied && wrap.Skin.enabled, "the restored bag wears the bag art");
            Check(bag != null && data != null && Vector3.Distance(bag.Center, data.bonePositions[0]) < 0.6f, "it lies where it was saved (" + (bag != null && data != null ? Vector3.Distance(bag.Center, data.bonePositions[0]).ToString("F2") : "-") + " m from the saved pelvis)");
            Check(bag != null && !d.Registry.IsCompleted(id) && d.Facts.ContainsKey(id), "reloaded bag is still an active identity, not disposed");
            Check(d.Disposal.Stock == saved.bodyBags && d.Disposal.Corpses.Count(x => x != null && x.Bagged) == 1, "reload restores the bag stock and exactly one bag");
            if (bag != null) { LookAt(bag.Center); yield return Frames(3); }
            Shot("corpse_07_reload_bag");
        }
        private IEnumerator CorpseWater() { yield return CorpseProbe("g35-water"); }
#endif
    }
}
