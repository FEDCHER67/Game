using System.Collections;
using System.Collections.Generic;
using System.IO;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Network;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Player.Physics;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Capture
{
    public sealed partial class CaptureScenarioDriver
    {
        /// <summary>What save-a stored, checked by save-b after the scene was reloaded (statics survive the reload).</summary>
        public static class SavedExpectation
        {
            public static readonly List<CaptureNpcSave> Npcs = new List<CaptureNpcSave>();
            public static Vector3 Van;
            public static Vector3 Table;
            public static int Ties;
            public static int Bags;
            public static float SavedAt;
        }

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private CaptureNpc Captured(GreyboxNpc npc) => CaptureNpc.Of(npc) ?? d.Ensure(npc);

        // =====================================================================================
        // CD-09: quit with NPCs in the van and on the base floor, reload: same places, sleep, blood, ties; no time passed.
        // =====================================================================================
        private IEnumerator SaveA()
        {
            if (File.Exists(d.SavePath)) File.Delete(d.SavePath);
            SavedExpectation.Npcs.Clear();
            // NPC 1: asleep, one portion drawn, hands + feet tied, in the van.
            var one = SpawnLocal("SausageBuddy_A", van.transform.position + van.transform.right * 3f, 0f);
            yield return Frames(2);
            one.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, one.Center);
            yield return Frames(2);
            var c1 = Captured(one);
            c1.Tie(TieTarget.Hands); c1.Tie(TieTarget.Feet);
            c1.QueueDose(1.0f);
            float fill = 0f;
            c1.DrawBlood(ref fill, d.Tuning.bloodSeconds + 0.1f);
            yield return new WaitForSeconds(0.4f);
            PlaceInBay(one, -1.2f);
            // NPC 2: feet tied, awake and groggy on the base floor in front of the shed.
            var two = SpawnLocal("SausageBuddy_B", new Vector3(187.2f, 0f, 512.6f), 90f);
            yield return Frames(2);
            two.Hit(WeaponStun.Fist, HitZone.Torso, pawn.Position, two.Center);
            yield return Frames(2);
            var c2 = Captured(two);
            c2.Tie(TieTarget.Feet);
            yield return WaitFor(() => one.InCargo, 6f, "NPC 1 loaded in the van");
            yield return new WaitForSeconds(1.0f);
            Overview("save_a_before", van.transform.TransformPoint(new Vector3(3.2f, 2.6f, -0.4f)), van.transform.TransformPoint(new Vector3(0f, 0.8f, -1.0f)));
            // Round 2: the gurney is movable now; push it aside (fixture) so the save must remember where it stands.
            var gurney = d.Table.GetComponent<Rigidbody>();
            Vector3 moved = d.Table.transform.position - d.Table.transform.right * 0.6f;
            gurney.position = moved; d.Table.transform.position = moved; gurney.linearVelocity = Vector3.zero; Physics.SyncTransforms();
            yield return new WaitForSeconds(0.6f);
            SavedExpectation.Table = d.Table.transform.position;
            // K: save. The expectations are read from the same moment.
            yield return Tap(Key.K);
            yield return Frames(1);
            Check(File.Exists(d.SavePath), "K wrote the save");
            var data = JsonUtility.FromJson<CaptureSaveData>(File.ReadAllText(d.SavePath));
            foreach (var n in data.npcs) if (n.facts.patientId == c1.PatientId || n.facts.patientId == c2.PatientId) SavedExpectation.Npcs.Add(n);
            SavedExpectation.Van = data.vanPosition;
            SavedExpectation.Ties = data.kit.ties;
            SavedExpectation.Bags = data.kit.bloodBags;
            SavedExpectation.SavedAt = Time.realtimeSinceStartup;
            Check(SavedExpectation.Npcs.Count == 2, "both NPCs are in the save");
            foreach (var n in SavedExpectation.Npcs)
                Info($"saved {n.facts.patientId}: cargo={n.inCargo} pelvis={n.pelvis} sleep={n.operation.sleepRemaining:F1} residual={n.operation.residual:F2} blood={n.operation.bloodPortions} ties={n.facts.restraints}");
            // The game keeps running for a while after the save: none of that may count after the reload.
            yield return new WaitForSeconds(5f);
        }

        private IEnumerator SaveB()
        {
            yield return WaitFor(() => d.Loaded, 5f, "the reloaded scene loaded the save");
            yield return new WaitForSeconds(1.0f);
            Info($"{Time.realtimeSinceStartup - SavedExpectation.SavedAt:0.0} s of real time since the save");
            Check(Vector3.Distance(van.transform.position, SavedExpectation.Van) < 0.6f, $"the van is where it was ({Vector3.Distance(van.transform.position, SavedExpectation.Van):0.00} m)");
            Check(d.Kit.Ties == SavedExpectation.Ties && d.Kit.BloodBags + (d.Kit.BloodFill >= 1f ? 1 : 0) >= SavedExpectation.Bags, "the field kit (ties, blood) is restored");
            Check(Flat(d.Table.transform.position, SavedExpectation.Table) < 0.05f, $"the moved gurney is back where it was saved ({Flat(d.Table.transform.position, SavedExpectation.Table) * 100f:F1} cm)");
            Check(d.Kit.Inventory != null && d.Kit.Inventory.Model != null && SlotWithKit() >= 0, "the field kit item is back in the hotbar after the reload");
            foreach (var n in SavedExpectation.Npcs)
            {
                CaptureNpc found = null;
                foreach (var c in CaptureNpc.All) if (c != null && c.PatientId == n.facts.patientId) found = c;
                if (!Check(found != null, "NPC " + n.facts.patientId + " is back")) continue;
                Vector3 pelvis = Pelvis(found.Npc);
                Vector3 want = n.inCargo ? van.transform.TransformPoint(n.pelvis) : n.pelvis;
                Check(Vector3.Distance(pelvis, want) < 0.45f, $"{n.facts.patientId}: same place ({Vector3.Distance(pelvis, want):0.00} m){(n.inCargo ? ", in the van" : "")}");
                if (n.inCargo) yield return WaitFor(() => found.Npc.InCargo, 4f, n.facts.patientId + ": loaded in the van again");
                // Only the game time since the reload may have run off his sleep (Claude rework: the fixed 2.5 s margin was
                // shorter than the reload + the cargo wait above, so it failed whenever loading took a little longer).
                float ran = Time.time - d.LoadedAt, expected = Mathf.Max(0f, n.operation.sleepRemaining - ran);
                Check(Mathf.Abs(found.State.sleepRemaining - expected) < 1f,
                    $"{n.facts.patientId}: sleep {found.State.sleepRemaining:F1} s vs saved {n.operation.sleepRemaining:F1} s minus {ran:F1} s played since the reload (no time passed while closed)");
                Check(found.State.bloodPortions == n.operation.bloodPortions && Mathf.Abs(found.State.residual - n.operation.residual) < 0.05f,
                    $"{n.facts.patientId}: blood {found.State.bloodPortions}, residual {found.State.residual:F2}");
                Check(found.Ties.hands == n.facts.restraints.hands && found.Ties.feet == n.facts.restraints.feet, $"{n.facts.patientId}: ties {found.Ties}");
                Check(found.Facts.intrinsic[0] == n.facts.intrinsic[0] && found.State.organs[2].intrinsicGrade == n.operation.organs[2].intrinsicGrade, $"{n.facts.patientId}: the same intrinsic grades");
                Check(found.Npc.State == NpcState.Down, $"{n.facts.patientId}: still down");
            }
            Overview("save_b_after_reload", van.transform.TransformPoint(new Vector3(3.2f, 2.6f, -0.4f)), van.transform.TransformPoint(new Vector3(0f, 0.8f, -1.0f)));
        }

        // =====================================================================================
        // Fedya's v04 bug: held / carried / loose physics never move the player; vehicles still push.
        // =====================================================================================
        private IEnumerator Push()
        {
            // the open Hamlet dirt road (no fences or trees in the way)
            Vector3 spot = Ground(new Vector3(227.4f, 0f, 526f));
            Teleport(spot, 0f);
            yield return new WaitForSeconds(0.5f);
            // (1) a held organ under the player, pulled up: the player must stay on the ground.
            var organ = SpawnOrgan(spot + new Vector3(0f, 0.05f, 0.85f));
            yield return new WaitForSeconds(0.5f);
            float organRise = OrganLift(organ, true, out float liftedTo);
            yield return organRiseRoutine;
            Check(organGrabbed, "LMB (virtual mouse) grabs a loose organ with the NetworkGrabber");
            Check(!PlayerPushPolicy.Allows(organ.GetComponentInChildren<Collider>(true)), "a held / loose organ is never solid for the player's motor (no ground, no push)");
            Check(maxRise < 0.05f, $"standing on a held organ and pulling it up does not lift the player (rose {maxRise:0.000} m, organ went {organTop:0.00} m up)");
            _ = organRise; _ = liftedTo;
            // the same without the policy, for the record (shows the bug the policy fixes)
            var policy = KinematicCharacterController.Examples.ExampleCharacterController.ColliderPolicy;
            KinematicCharacterController.Examples.ExampleCharacterController.ColliderPolicy = null;
            Teleport(spot, 0f);
            yield return new WaitForSeconds(0.5f);
            organ.transform.position = spot + new Vector3(0f, 0.05f, 0.85f);
            if (organ.TryGetComponent(out Rigidbody orb)) { orb.position = organ.transform.position; orb.linearVelocity = Vector3.zero; }
            yield return new WaitForSeconds(0.4f);
            OrganLift(organ, false, out _);
            yield return organRiseRoutine;
            Info($"without the policy the same move lifted the player {maxRise:0.00} m (organ {organTop:0.00} m)");
            KinematicCharacterController.Examples.ExampleCharacterController.ColliderPolicy = policy;
            Teleport(spot + Vector3.back * 4f, 0f);
            yield return new WaitForSeconds(0.5f);

            // (2) walking into a lying ragdoll: no shove sideways, no climbing onto it.
            var lying = SpawnLocal("SausageBuddy_A", spot + new Vector3(0f, 0f, 2.2f), 90f);
            yield return Frames(2);
            lying.Hit(WeaponStun.Fist, HitZone.Head, spot, lying.Center);
            yield return new WaitForSeconds(2.5f);
            Teleport(spot, 0f);
            yield return new WaitForSeconds(0.4f);
            Vector3 start = pawn.Position;
            float worstSide = 0f, worstUp = 0f;
            walkTarget = start + Vector3.forward * 4.5f; walkSpeedScale = 1f; walking = true;
            float end = Time.time + 3.5f;
            while (Time.time < end)
            {
                Vector3 p = pawn.Position - start;
                worstSide = Mathf.Max(worstSide, Mathf.Abs(p.x));
                worstUp = Mathf.Max(worstUp, p.y);
                yield return null;
            }
            walking = false;
            Check(worstSide < 0.15f && worstUp < 0.12f, $"walking into a lying ragdoll does not shove or lift the player (side {worstSide:0.00} m, up {worstUp:0.00} m)");

            // (3) a body thrown at a standing player: it must not move him.
            Teleport(spot + Vector3.back * 8f, 0f);
            yield return new WaitForSeconds(0.5f);
            Vector3 still = pawn.Position;
            var thrown = SpawnLocal("SausageBuddy_B", still + new Vector3(0f, 0.4f, 2.0f), 180f);
            yield return Frames(2);
            thrown.Hit(WeaponStun.Fist, HitZone.Head, still, thrown.Center);
            yield return Frames(2);
            if (thrown.Ragdoll != null && thrown.Ragdoll.Active) thrown.Ragdoll.SetVelocity(new Vector3(0f, 1f, -5f), Vector3.zero);
            float moved = 0f;
            end = Time.time + 1.6f;
            while (Time.time < end) { moved = Mathf.Max(moved, Vector3.Distance(pawn.Position, still)); yield return null; }
            Check(moved < 0.05f, $"a ragdoll thrown at the player does not move him ({moved:0.000} m)");

            // (4) a carried (held) NPC swung into the player: held bodies never push.
            Teleport(spot + Vector3.back * 12f, 0f);
            yield return new WaitForSeconds(0.4f);
            var carried = SpawnLocal("SausageBuddy_A", pawn.Position + new Vector3(0f, 0f, 1.6f), 0f);
            yield return Frames(2);
            carried.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, carried.Center);
            yield return new WaitForSeconds(1.5f);
            yield return Approach(carried, 0.9f);
            yield return new WaitForSeconds(0.3f);
            Vector3 before = pawn.Position;
            bool carriedGrab = Grab(Collar(carried));
            Check(carriedGrab, "LMB grabs the knocked-out NPC by the collar (the carried-NPC check is not vacuous)");
            if (carriedGrab)
            {
                yield return HandTo(pawn.Position + Vector3.up * 1.2f + Vector3.forward * 0.6f, 0.5f);
                yield return HandTo(pawn.Position + Vector3.up * 0.9f + Vector3.forward * 0.4f + Vector3.right * 0.1f, 0.6f);
                yield return new WaitForSeconds(0.5f);
                Release();
            }
            grabber.ScriptDriven = false;
            yield return new WaitForSeconds(0.6f);
            float carriedMove = Vector3.Distance(pawn.Position, before);
            Check(carriedMove < 0.06f, $"a carried NPC pulled into the player does not move him ({carriedMove:0.000} m)");

            // (5) the operation patient's ragdoll bones are bodies too (never a mover).
            var patientPrefab = d.Table != null ? d.Table.GetComponent<NetworkOperationTable>() : null;
            Check(!PlayerPushPolicy.IsAllowListedMover(thrown.Ragdoll != null ? thrown.Ragdoll.MainBody : null), "NPC ragdoll bodies are not on the allow-list");

            // (6) the van IS on the allow-list: it still pushes the player.
            Vector3 vanStart = Ground(spot + new Vector3(-1.2f, 0f, 6f)) + Vector3.up * 0.35f;
            van.ResetUpright(vanStart, 0f);
            yield return new WaitForSeconds(1.0f);
            Vector3 standFront = van.transform.TransformPoint(new Vector3(0f, 0f, 3.2f));
            Teleport(Ground(standFront), 180f);
            yield return new WaitForSeconds(0.5f);
            Vector3 hit0 = pawn.Position;
            yield return EnterVanKeepPlayer();
            // No one sits in the van, so its wheels are not the point here: roll the van body itself at a walking pace
            // (2.5 m/s) into the player. What is tested is that the KCC treats the allow-listed van as a solid mover.
            var vanBody = van.GetComponent<Rigidbody>();
            Vector3 rollDir = van.transform.forward; rollDir.y = 0f; rollDir.Normalize();
            end = Time.time + 2.5f;
            float pushed = 0f;
            while (Time.time < end)
            {
                pushed = Mathf.Max(pushed, Vector3.Distance(pawn.Position, hit0));
                if (vanBody != null && !vanBody.isKinematic)
                {
                    Vector3 v = vanBody.linearVelocity;
                    vanBody.linearVelocity = new Vector3(rollDir.x * 2.5f, v.y, rollDir.z * 2.5f);
                }
                yield return new WaitForFixedUpdate();
            }
            if (vanBody != null && !vanBody.isKinematic) vanBody.linearVelocity = Vector3.zero;
            throttle = 0f; handbrake = true; yield return new WaitForSeconds(0.6f); driving = false;
            Check(pushed > 0.4f, $"the van (allow-listed) still pushes the player ({pushed:0.00} m)");
            Check(PlayerPushPolicy.IsAllowListedMover(van.GetComponent<Rigidbody>()), "the van is on the allow-list");
        }

        // The van drives without the player in it (an "AI driver"): the pawn stays on foot in front of it.
        private IEnumerator EnterVanKeepPlayer()
        {
            driving = true; throttle = 0f; steer = 0f; handbrake = false;
            yield return null;
        }

        private OperationPhysicalItem SpawnOrgan(Vector3 at)
        {
            var table = d.Table;
            var field = typeof(NetworkOperationTable).GetField("merchandisePrefabs", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
            var defs = typeof(NetworkOperationTable).GetField("merchandiseDefinitions", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
            var prefabs = (OperationPhysicalItem[])field.GetValue(table);
            var definitions = (ItemDefinition[])defs.GetValue(table);
            var item = Instantiate(prefabs[1], at, Quaternion.identity);
            item.Initialize(new OperationItemState { id = "push-test/liver", kind = 1, organIndex = 2, grade = 2, position = at, rotation = Quaternion.identity }, d.Tuning, definitions[1]);
            FishNet.InstanceFinder.ServerManager.Spawn(item.NetworkObject);
            NetworkSession.Active?.RegisterBody(item.GetComponent<NetworkPhysicsBody>());
            return item;
        }

        private IEnumerator organRiseRoutine;
        private bool organGrabbed;
        private float maxRise, organTop;
        private float OrganLift(OperationPhysicalItem organ, bool record, out float top)
        {
            organRiseRoutine = OrganLiftRoutine(organ, record);
            top = 0f;
            return 0f;
        }
        private IEnumerator OrganLiftRoutine(OperationPhysicalItem organ, bool record)
        {
            maxRise = 0f; organTop = 0f;
            LookAt(organ.transform.position);
            yield return Frames(3);
            lmb = true; PushMouse();
            yield return new WaitForSeconds(0.4f);
            if (record) organGrabbed = organ.GetComponent<NetworkPhysicsBody>().HasHolder;
            // put it under the feet: look straight down
            float y0 = pawn.Position.y;
            float startY = organ.transform.position.y;
            for (float t = 0f; t < 0.8f; t += Time.deltaTime) { SetYawPitch(Yaw, Mathf.Lerp(20f, 85f, t / 0.8f)); PushMouse(); yield return null; }
            // "pull up": raise the view slowly while holding
            for (float t = 0f; t < 2.5f; t += Time.deltaTime)
            {
                SetYawPitch(Yaw, Mathf.Lerp(85f, -40f, t / 2.5f));
                PushMouse();
                maxRise = Mathf.Max(maxRise, pawn.Position.y - y0);
                organTop = Mathf.Max(organTop, organ.transform.position.y - startY);
                yield return null;
            }
            lmb = false; PushMouse();
            yield return new WaitForSeconds(0.6f);
            SetYawPitch(Yaw, 10f);
        }

        // =====================================================================================
        // Rules in the field: overdose kills (CD-03), blood refusals (CD-05), the tie rows (CD-06).
        // =====================================================================================
        private IEnumerator Rules()
        {
            Vector3 spot = Ground(CaptureSpot + new Vector3(0f, 0f, 3f));
            Teleport(spot, 0f);
            yield return new WaitForSeconds(0.4f);
            // CD-05: an awake, unrestrained NPC refuses blood; a corpse gives none; asleep or hands tied: yes.
            var a = SpawnLocal("SausageBuddy_A", spot + new Vector3(0f, 0f, 1.6f), 180f);
            yield return Frames(2);
            KnockOut(a);
            yield return Frames(2);
            var ca = Captured(a);
            yield return new WaitForSeconds(1.5f); // a knocked-out body flies 2-7 m: let it land first
            yield return Approach(a);
            a.StunLeft = 3f; a.StunTotal = 10f; // groggy now: awake and kicking
            yield return new WaitForSeconds(0.3f);
            Check(ca.CanDrawBlood() == FieldRefusal.Squirming, "blood is refused from an awake, unrestrained (groggy) NPC");
            yield return TakeTool(FieldTool.Blood);
            LookAt(Bone(a, "RightArm").position);
            yield return Frames(3);
            Info($"kit: tool {d.Kit.Tool}, aimed {(d.Kit.Aimed != null ? d.Kit.Aimed.PatientId : "-")}, npc {(d.Kit.AimedNpc != null ? d.Kit.AimedNpc.name : "-")}, suspended {d.Kit.Suspended}, controlled {pawn.Controlled}, cursor {OpsInput.CursorLocked}");
            d.Kit.BloodFill = 0f; // fixture: an empty syringe (a test save can bring back a full one: round 2 keeps the portion in it)
            float fill0 = d.Kit.BloodFill;
            yield return HoldLeft(1.0f, () => Bone(a, "RightArm").position);
            Check(Mathf.Approximately(d.Kit.BloodFill, fill0) && ca.State.bloodPortions == 0, "holding the blood syringe on him draws nothing (refused)");
            ca.Tie(TieTarget.Hands);
            Check(ca.CanDrawBlood() == FieldRefusal.None, "with his hands tied the blood can be drawn");
            yield return HoldLeft(1.0f, () => Bone(a, "RightArm").position);
            Check(d.Kit.BloodFill > fill0 + 0.1f, $"and the syringe fills ({d.Kit.BloodFill:0.00})");
            yield return TakeTool(FieldTool.Hands);

            // CD-03: an overdose in the field kills; a corpse gives no blood.
            var b = SpawnLocal("SausageBuddy_B", spot + new Vector3(2.2f, 0f, 1.6f), 180f);
            yield return Frames(2);
            KnockOut(b);
            yield return Frames(2);
            var cb = Captured(b);
            yield return new WaitForSeconds(1.5f);
            yield return Approach(b);
            yield return new WaitForSeconds(0.3f);
            yield return TakeTool(FieldTool.Anesthesia);
            yield return HoldLeft(5.2f, () => Bone(b, "Neck").position);
            yield return new WaitForSeconds(0.2f);
            Check(!cb.State.alive && cb.State.deathCause == DeathCause.Overdose, $"5 s of anesthesia in the field is an overdose: he dies (residual {cb.State.residual:F2})");
            Check(cb.CanDrawBlood() == FieldRefusal.Dead, "a corpse gives no blood");
            yield return new WaitForSeconds(2f);
            Check(b.State == NpcState.Down && b.Phase == StunPhase.Out, "the corpse stays limp, never wakes");
            yield return TakeTool(FieldTool.Hands);

            // CD-06 feet: he never gets up and runs; he crawls.
            var f = SpawnLocal("SausageBuddy_A", spot + new Vector3(-3f, 0f, 3f), 0f);
            yield return Frames(2);
            f.Hit(WeaponStun.Fist, HitZone.Limb, pawn.Position, f.Center);
            yield return Frames(2);
            var cf = Captured(f);
            cf.Tie(TieTarget.Feet);
            Vector3 from = Pelvis(f);
            yield return new WaitForSeconds(12f);
            Check(f.State == NpcState.Down && f.Phase == StunPhase.Groggy, $"feet tied: 12 s later he is still down, groggy, not on his feet ({f.State}/{f.Phase})");
            Info($"feet tied: crawled {Vector3.Distance(Pelvis(f), from):0.00} m in 12 s");

            // CD-06 both: in the van with a door open he cannot get out on his own.
            van.ResetUpright(Ground(VanSpot) + Vector3.up * 0.35f, 180f);
            yield return new WaitForSeconds(0.8f);
            var w = SpawnLocal("SausageBuddy_B", van.transform.position + van.transform.right * 3f, 0f);
            yield return Frames(2);
            w.Hit(WeaponStun.Fist, HitZone.Limb, pawn.Position, w.Center);
            yield return Frames(2);
            var cw = Captured(w);
            cw.Tie(TieTarget.Hands); cw.Tie(TieTarget.Feet);
            PlaceInBay(w, -0.8f);
            yield return WaitFor(() => w.InCargo, 5f, "the trussed NPC is loaded");
            w.StunLeft = 3f; w.StunTotal = 10f;
            if (!cargo.DoorOpen(0)) cargo.ToggleDoor(0);
            if (!cargo.DoorOpen(1)) cargo.ToggleDoor(1);
            yield return new WaitForSeconds(12f);
            Check(w.InCargo && w.State == NpcState.Down, "hands + feet tied: 12 s with both doors open and he is still in the van");
            Check(!w.HandsBound || cw.Ties.hands, "his hands stay out of use");
            // hands only: he wakes, sits up, but never knocks on the van wall
            cw.SetTies(new Restraints { hands = true, feet = false });
            cargo.ToggleDoor(0); cargo.ToggleDoor(1);
            w.StunLeft = 0.2f;
            yield return new WaitForSeconds(14f);
            Info($"hands tied, awake in the van: state {w.State}, kicks {w.Kicks}");
            Check(w.HandsBound, "hands tied: GreyboxNpc.HandsBound blocks the wall knock (the only hand action in this build)");
        }
#endif
    }
}
