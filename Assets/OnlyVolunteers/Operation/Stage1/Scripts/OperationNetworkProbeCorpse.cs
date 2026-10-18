using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Network;
using OnlyVolunteers.Player.Physics;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    public sealed partial class OperationNetworkProbe
    {
        public static string LastCorpseBagId;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator G35AimCorpse(CaptureCorpse corpse)
        {
            aimed = false;
            var ragdoll = corpse.GetComponent<OperationPatientRagdoll>();
            int count = ragdoll != null ? ragdoll.BoneCount : 1;
            for (int i = 0; i < count; i++)
            {
                LookAt(ragdoll != null ? ragdoll.Bone(i).position : corpse.Center); yield return Frames(3);
                if (Physics.Raycast(Cam.transform.position, Cam.transform.forward, out var hit, 3f, OnlyVolunteers.Map.OvLayers.ShootMask, QueryTriggerInteraction.Ignore) && hit.collider.GetComponentInParent<CaptureCorpse>() == corpse)
                { aimed = true; break; }
            }
        }
        private static Vector3 G35WaterPoint(WaterKind kind)
        {
            var data = WaterQuery.Data;
            if (data != null) foreach (var area in data.Areas)
                if (area != null && area.Kind == kind)
                    for (int i = 0; i + 5 < area.Triangles.Length; i += 6)
                    {
                        var t = area.Triangles; var point = new Vector3((t[i] + t[i+2] + t[i+4]) / 3f, area.SurfaceY, (t[i+1] + t[i+3] + t[i+5]) / 3f);
                        if (WaterQuery.Depth(point) > 0.6f) return point;
                    }
            throw new InvalidOperationException("No existing deep water surface: " + kind);
        }
        // G35Corpse (the old "bag in hands" item flow) was replaced by ClBag (OperationNetworkProbeReworkBag.cs): the bag
        // is now the corpse ragdoll itself (Fedya 2026-10-18).
        private IEnumerator G35Water()
        {
            var director = CaptureDirector.Instance;
            foreach (var kind in new[] { WaterKind.River, WaterKind.Lake, WaterKind.Canal })
            {
                Vector3 water = G35WaterPoint(kind);
                string id = "G35-water-" + kind + "-" + Guid.NewGuid().ToString("N").Substring(0,6);
                var state = OperationRules.Create(id, table.Tuning); state.alive = false; state.deathCause = DeathCause.Overdose;
                var facts = new CaptureFacts { patientId = id, districtId = "village" };
                // A stable player fixture avoids a falling camera lagging beyond the network's validated eye range.
                // The corpse stays dynamic, above the EXISTING water; its grab and release still use real LMB.
                Vector3 stand = water + Vector3.up * 6f + Vector3.right * 1.15f;
                var platform = GameObject.CreatePrimitive(PrimitiveType.Cube); platform.name = "G35 water test stance";
                platform.transform.position = stand - Vector3.up * 0.1f; platform.transform.localScale = new Vector3(0.7f, 0.2f, 0.7f);
                platform.GetComponent<Renderer>().enabled = false;
                Teleport(stand + Vector3.up * 0.02f); yield return new WaitForSeconds(0.3f);
                director.Disposal.Restore(new List<CaptureCorpseSave> { new CaptureCorpseSave { facts = facts, operation = state, position = water + Vector3.up * 6f } }, director.Disposal.Stock);
                var corpse = director.Disposal.Corpses.First(x => x.PatientId == id);
                foreach (var collider in corpse.GetComponentsInChildren<Collider>()) Physics.IgnoreCollision(collider, platform.GetComponent<Collider>());
                yield return Frames(3);
                yield return G35AimCorpse(corpse); Check(aimed, kind + ": real ray reaches unbagged corpse");
                yield return Button(true); yield return new WaitForSeconds(0.2f);
                Check(corpse.Held, kind + ": real LMB holds the unbagged ragdoll before release");
                yield return Button(false); Destroy(platform); yield return new WaitForSeconds(0.4f); Shot("corpse_water_" + kind);
                yield return WaitFor(() => director.Disposal.LastDisposed == id, 10f, kind + ": physical ragdoll drop sinks and clears identity");
                Check(director.Registry.IsCompleted(id) && !director.Facts.ContainsKey(id), kind + ": evidence and active identity cleared");
            }
        }
#endif
    }
}
