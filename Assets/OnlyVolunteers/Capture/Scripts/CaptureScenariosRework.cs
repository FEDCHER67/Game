using System.Collections;
using System.IO;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>Claude rework of G35 Stage A: map-side fixtures and checks for the rework scenarios (straps, gurney,
    /// body bag). Setup uses fixtures; every feature action goes through the real input path (virtual Mouse/Keyboard
    /// for Input System code, the driver's per-frame KCC inputs for legacy W/A/S/D walking).</summary>
    public sealed partial class CaptureScenarioDriver
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        /// <summary>A knocked-out Hamlet NPC with hands AND feet zip-tied, laid on the base table (fixture), then the
        /// real-input strap scenario in the PREP view (cl-straps).</summary>
        private IEnumerator StrapsOnTable()
        {
            var npc = SpawnLocal("SausageBuddy_B", d.Table.transform.position + Vector3.forward * 2f, 0f);
            yield return Frames(2);
            float impulse = npc.HitImpulse; npc.HitImpulse = 0f;
            npc.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, npc.Center); npc.HitImpulse = impulse;
            yield return Frames(3);
            var c = CaptureNpc.Of(npc);
            if (!Check(c != null, "fixture: the knocked-out NPC is a capture identity")) yield break;
            // Fixture (the Z-hold tie flow is covered by the loop/rules scenarios): both ties on, asleep.
            c.SetTies(new Restraints { hands = true, feet = true });
            c.State.sleepRemaining = 120f;
            npc.Ragdoll.PlaceLying(d.Table.transform.position + Vector3.up * 0.7f, d.Table.transform.forward, true);
            yield return WaitFor(() => d.Table.HasPatient && d.Table.State != null && d.Table.State.aligned, 8f, "fixture: the tied patient is admitted under the normal cloud");
            yield return CorpseProbe("cl-straps");
        }

        /// <summary>A corpse in the field (died there, fixture: the overdose rule) packed with real R where it lies: it becomes
        /// the same bag ragdoll as a table corpse (network patient ragdoll, same identity), then E carries it.</summary>
        private IEnumerator FieldBag()
        {
            Vector3 spot = d.Table.transform.position + Vector3.forward * 5.5f;
            var npc = SpawnLocal("SausageBuddy_B", spot, 0f);
            yield return Frames(2);
            float impulse = npc.HitImpulse; npc.HitImpulse = 0f;
            npc.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, npc.Center); npc.HitImpulse = impulse;
            yield return new WaitForSeconds(1.5f);
            var c = CaptureNpc.Of(npc);
            if (!Check(c != null, "fixture: a knocked-out capture identity")) yield break;
            string id = c.PatientId;
            c.Rules.Die(DeathCause.Overdose); // fixture: died in the field (the field overdose itself is covered by 'rules')
            yield return new WaitForSeconds(0.5f);
            var corpse = d.Disposal.Corpses.Find(x => x != null && x.PatientId == id);
            Check(corpse != null && corpse.FieldNpc != null, "the field corpse is registered with its identity");
            Vector3 pelvis = npc.PhysicalBody.Landmark(NpcLandmark.Pelvis);
            Teleport(Ground(pelvis + Vector3.right * 1.0f), -90f); yield return Frames(3);
            LookAt(pelvis); yield return Frames(3);
            Check(d.Disposal.Aimed != null && d.Disposal.Aimed.PatientId == id, "first-person aim finds the field corpse (hint «" + d.Disposal.Hint + "»)");
            int stock = d.Disposal.Stock;
            keys.Add(UnityEngine.InputSystem.Key.R); PushKeys();
            float end = Time.time + 1.3f; while (Time.time < end) { PushKeys(); LookAt(pelvis); yield return null; }
            keys.Remove(UnityEngine.InputSystem.Key.R); PushKeys(); yield return new WaitForSeconds(0.5f);
            var bag = d.Disposal.Corpses.Find(x => x != null && x.PatientId == id);
            Check(bag != null && bag.Bagged && bag.FieldNpc == null && bag.Ragdoll != null && bag.Ragdoll.DynamicBodies == 11, "hold R packs the field corpse: the same identity is now the bag ragdoll");
            Check(npc == null, "the field NPC object is gone (one body per identity)");
            Check(d.Disposal.Stock == stock - 1, "one bag used");
            if (bag == null) yield break;
            yield return new WaitForSeconds(0.6f);
            Check(BodyShowsOutsideBag(bag, out string showing) == 0, "packed in the field: only the bag shows, no head or arms outside it (" + showing + ")");
            Overview("bag_field_packed", bag.Center + Vector3.right * 1.8f + Vector3.up * 1.5f + Vector3.forward * 0.6f, bag.Center);
            Overview("bag_field_packed_top", bag.Center + Vector3.up * 2.2f + Vector3.forward * 0.01f, bag.Center, 60f);
            LookAt(bag.Center); yield return Frames(3);
            yield return Tap(UnityEngine.InputSystem.Key.E); yield return new WaitForSeconds(1.0f);
            Check(d.Disposal.Hands.Carrying == bag && bag.Held, "E carries the field bag too");
            Shot("bag_field_carried_fp");
            yield return Tap(UnityEngine.InputSystem.Key.G); yield return new WaitForSeconds(0.8f);
            Check(d.Disposal.Hands.Carrying == null && !bag.Held, "G puts it down");
        }

        /// <summary>Character renderers still drawn around a packed bag (its own ones other than the wrap, and any other body's
        /// within 1.5 m): Fedya saw head and arms poking out of a field bag.</summary>
        private static int BodyShowsOutsideBag(CaptureCorpse bag, out string names)
        {
            var wrap = bag.GetComponent<OperationBodyBagWrap>(); int count = 0; var sb = new System.Text.StringBuilder();
            foreach (var r in bag.GetComponentsInChildren<Renderer>(false))
                if (r.enabled && (wrap == null || r != wrap.Skin)) { count++; sb.Append(r.name).Append(' '); }
            foreach (var r in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None))
            {
                if (!r.enabled || !r.gameObject.activeInHierarchy || r.transform.IsChildOf(bag.transform)) continue;
                if (Vector3.Distance(r.bounds.center, bag.Center) > 1.5f) continue;
                count++; sb.Append(r.name).Append("@").Append(r.transform.root.name).Append(' ');
            }
            names = count == 0 ? "none" : sb.ToString();
            return count;
        }

        // ---------- third-person evidence video ----------
        private bool overviewRecording;
        private int overviewFrame;
        /// <summary>Records 960x540 frames from a third-person camera following 'pose' into output/overview_frames.</summary>
        private IEnumerator RecordOverview(System.Func<(Vector3 eye, Vector3 at)> pose)
        {
            string folder = Path.Combine(output, "overview_frames"); Directory.CreateDirectory(folder);
            var go = new GameObject("CaptureOverviewRecorder"); var cam = go.AddComponent<Camera>();
            cam.fieldOfView = 50f; cam.nearClipPlane = 0.05f; cam.farClipPlane = 400f; cam.enabled = false;
            var target = new RenderTexture(960, 540, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2 }; cam.targetTexture = target;
            var tex = new Texture2D(960, 540, TextureFormat.RGB24, false);
            overviewRecording = true;
            while (overviewRecording)
            {
                var p = pose(); go.transform.SetPositionAndRotation(p.eye, Quaternion.LookRotation(p.at - p.eye));
                cam.Render();
                var prev = RenderTexture.active; RenderTexture.active = target;
                tex.ReadPixels(new Rect(0, 0, 960, 540), 0, 0); tex.Apply(); RenderTexture.active = prev;
                File.WriteAllBytes(Path.Combine(folder, "o" + (overviewFrame++).ToString("D5") + ".jpg"), tex.EncodeToJPG(82));
                yield return new WaitForSeconds(0.1f);
            }
            Destroy(tex); cam.targetTexture = null; target.Release(); Destroy(target); Destroy(go);
        }

        private static float Flat(Vector3 a, Vector3 b) { a.y = 0f; b.y = 0f; return Vector3.Distance(a, b); }
        private static float RagdollMass(NpcRagdoll r) { float m = 0f; for (int i = 0; i < r.PartCount; i++) if (r.BodyOf(i) != null) m += r.BodyOf(i).mass; return m; }

        /// <summary>Fedya: a ragdoll thrown into the gurney nudges it a LITTLE; it never slides freely, never tips and never
        /// pushes the player standing against it. (The walking push is round 2's "gurney2".)</summary>
        private IEnumerator GurneyNudge()
        {
            var table = d.Table; var body = table.GetComponent<Rigidbody>(); var brake = table.GetComponent<OperationTableBrake>();
            Check(table.IsServerInitialized && brake != null && !body.isKinematic && body.mass >= OperationTableBrake.MinMass &&
                  (body.constraints & RigidbodyConstraints.FreezePosition) == 0 && (body.constraints & RigidbodyConstraints.FreezeRotationX) != 0,
                  "the gurney is a heavy (" + body.mass.ToString("0") + " kg), upright, dynamic server body: not frozen, not kinematic");
            Check(table.GetComponent<FishNet.Component.Transforming.NetworkTransform>() != null, "its position replicates from the server (NetworkTransform)");
            Vector3 north = -table.transform.right; north.y = 0f; north.Normalize(); // the long side toward the open yard
            // ---- 1. (round 2: walking into it now pushes it along at 12.5 % walk speed: scenario "gurney2") ----
            // ---- 2. a knocked-out NPC thrown into the far long side, the player standing against the near side ----
            Vector3 at = table.transform.position;
            Teleport(Ground(at - north * 0.78f), Mathf.Atan2(north.x, north.z) * Mathf.Rad2Deg); // inside the shed, touching it
            var npc = SpawnLocal("SausageBuddy_B", at + north * 2.4f, 0f);
            yield return Frames(2);
            float impulse = npc.HitImpulse; npc.HitImpulse = 0f;
            npc.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, npc.Center); npc.HitImpulse = impulse;
            yield return new WaitForSeconds(1.6f);
            Check(npc.Ragdoll != null && npc.Ragdoll.Active, "the NPC lies as a ragdoll");
            Vector3 before = table.transform.position, player0 = pawn.Position; float playerMax = 0f, tableMax = 0f;
            // Thrown like a player throws a carried body: from hand height, about 1.4 m out, straight at the pad.
            float ragdollMass = RagdollMass(npc.Ragdoll);
            Vector3 com = npc.Ragdoll.CenterOfMass, toTable = at - com; toTable.y = 0f; toTable.Normalize();
            Vector3 release = new Vector3(at.x, at.y + 0.95f, at.z) - toTable * 1.4f;
            npc.Ragdoll.MoveRigid(com, Quaternion.identity, release, Quaternion.identity, toTable * 5f + Vector3.up * 0.5f);
            Shot("gurney_02_ragdoll_thrown");
            float end = Time.time + 2.5f;
            while (Time.time < end)
            {
                playerMax = Mathf.Max(playerMax, Vector3.Distance(player0, pawn.Position));
                Vector3 v = body.linearVelocity; v.y = 0f; tableMax = Mathf.Max(tableMax, v.magnitude);
                yield return new WaitForFixedUpdate();
            }
            float knocked = Flat(before, table.transform.position);
            Shot("gurney_03_after_ragdoll");
            Info("thrown ragdoll mass " + ragdollMass.ToString("F1") + " kg" + (npc == null ? "; it landed on the pad and was admitted (cloud)" : ""));
            Check(knocked > 0.002f && knocked < 0.3f, "a ragdoll thrown into it nudges the gurney slightly: " + (knocked * 100f).ToString("F1") + " cm (peak " + (tableMax * 100f).ToString("F1") + " cm/s)");
            Check(Vector3.Dot(table.transform.up, Vector3.up) > 0.999f, "the thrown ragdoll does not tip it");
            Check(playerMax < 0.005f, "the gurney never pushes the player standing against it (" + (playerMax * 100f).ToString("F1") + " cm)");
            yield return Frames(3);
            if (npc != null) Destroy(npc.gameObject);
        }
#endif
    }
}
