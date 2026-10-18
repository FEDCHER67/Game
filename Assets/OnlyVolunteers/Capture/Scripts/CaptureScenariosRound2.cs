using System.Collections;
using System.Collections.Generic;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;
using UnityEngine.InputSystem;
using System.Reflection;
using System.IO;

namespace OnlyVolunteers.Capture
{
    /// <summary>Round 2 of the Claude rework (Fedya's build_v02 playtest, 2026-10-18): real-input scenarios for the gurney
    /// push (walking into it / holding it with LMB), the body-bag carry speed and the rest of the round.</summary>
    public sealed partial class CaptureScenarioDriver
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private static float FlatSpeed(Vector3 a, Vector3 b, float seconds) { a.y = 0f; b.y = 0f; return Vector3.Distance(a, b) / Mathf.Max(0.001f, seconds); }

        private struct PushRun { public float player, gurney, minGap, jitter, yaw, lift; }

        /// <summary>Walks the player toward 'goal' for 'seconds' (holding LMB if 'hold'), measuring over the last
        /// 'steady' seconds: the player's and the gurney's mean speed, the smallest capsule-gurney clearance, the gurney's
        /// speed jitter (std / mean) and its yaw change.</summary>
        private IEnumerator MeasurePush(Vector3 goal, float seconds, float steady, System.Action<PushRun> result)
        {
            var table = d.Table; var brake = table.GetComponent<OperationTableBrake>(); var motor = kcc.Character.Motor;
            float yaw0 = table.transform.eulerAngles.y, foot0 = pawn.Position.y;
            walkTarget = goal; walkSpeedScale = 1f; walking = true;
            float t0 = Time.time, minGap = float.MaxValue, lift = 0f;
            Vector3 p0 = Vector3.zero, g0 = Vector3.zero; bool started = false; float ts = 0f;
            var speeds = new List<float>(); Vector3 lastG = table.transform.position;
            while (Time.time - t0 < seconds)
            {
                yield return new WaitForFixedUpdate();
                if (brake.Gap(motor, out float gap, out _)) minGap = Mathf.Min(minGap, gap);
                lift = Mathf.Max(lift, pawn.Position.y - foot0);
                if (!started && Time.time - t0 >= seconds - steady) { started = true; ts = Time.time; p0 = pawn.Position; g0 = table.transform.position; }
                if (started) { speeds.Add(FlatSpeed(lastG, table.transform.position, Time.fixedDeltaTime)); }
                lastG = table.transform.position;
                if (lmb) PushMouse();
            }
            float span = Time.time - ts;
            var r = new PushRun { player = FlatSpeed(p0, pawn.Position, span), gurney = FlatSpeed(g0, table.transform.position, span), minGap = minGap, lift = lift };
            float mean = 0f; foreach (var s in speeds) mean += s; mean /= Mathf.Max(1, speeds.Count);
            float var = 0f; foreach (var s in speeds) var += (s - mean) * (s - mean); var /= Mathf.Max(1, speeds.Count);
            r.jitter = mean > 1e-3f ? Mathf.Sqrt(var) / mean : 0f;
            r.yaw = Mathf.Abs(Mathf.DeltaAngle(yaw0, table.transform.eulerAngles.y));
            if (r.gurney < 0.2f || r.jitter > 0.2f) Info("slow/jerky push: what touches the gurney: " + Touching(table));
            result(r);
        }

        private static string Touching(NetworkOperationTable table)
        {
            var body = table.GetComponent<Rigidbody>(); var sb = new System.Text.StringBuilder();
            foreach (var c in table.GetComponentsInChildren<Collider>())
            {
                if (c.attachedRigidbody != body || c.isTrigger || !c.enabled) continue;
                var b = c.bounds; b.Expand(0.04f);
                foreach (var o in Physics.OverlapBox(b.center, b.extents, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore))
                    if (o.attachedRigidbody != body && !o.transform.IsChildOf(table.transform)) sb.Append(c.name).Append("~").Append(o.name).Append("(").Append(LayerMask.LayerToName(o.gameObject.layer)).Append(") ");
            }
            return sb.Length == 0 ? "nothing" : sb.ToString();
        }

        private IEnumerator StopCheck(string label)
        {
            var table = d.Table;
            walking = false; Vector3 at = table.transform.position;
            yield return new WaitForSeconds(0.6f);
            float slid = Flat(at, table.transform.position);
            var v = table.GetComponent<Rigidbody>().linearVelocity; v.y = 0f;
            Check(slid < 0.05f && v.magnitude < 0.01f, label + ": when he stops it stops quickly (slid " + (slid * 100f).ToString("F1") + " cm)");
        }

        /// <summary>Puts the player 'distance' m out from the gurney's side 'outward' (a unit vector), facing it.</summary>
        private IEnumerator StandAt(Vector3 outward, float clearance)
        {
            var table = d.Table; var brake = table.GetComponent<OperationTableBrake>(); var motor = kcc.Character.Motor;
            Vector3 c = table.transform.position;
            float dist = 0.6f;
            for (int i = 0; i < 4; i++)
            {
                Teleport(Ground(c + outward * dist), Mathf.Atan2(-outward.x, -outward.z) * Mathf.Rad2Deg);
                yield return new WaitForFixedUpdate(); yield return new WaitForFixedUpdate();
                if (!brake.Gap(motor, out float gap, out _)) break;
                dist += clearance - gap;
            }
            Teleport(Ground(c + outward * dist), Mathf.Atan2(-outward.x, -outward.z) * Mathf.Rad2Deg);
            yield return new WaitForSeconds(0.4f);
        }

        /// <summary>Free floor ahead of the gurney along 'dir': its whole outline swept (a box cast; the gurney itself, the
        /// floor under its wheels and players ignored).</summary>
        private float Room(Vector3 dir)
        {
            var table = d.Table; var body = table.GetComponent<Rigidbody>();
            Bounds b = new Bounds(table.transform.position, Vector3.zero); bool any = false;
            foreach (var c in table.GetComponentsInChildren<Collider>()) if (c.attachedRigidbody == body && !c.isTrigger && c.enabled) { if (!any) { b = c.bounds; any = true; } else b.Encapsulate(c.bounds); }
            Vector3 half = b.extents; half.y = Mathf.Max(0.05f, half.y - 0.08f);
            Vector3 centre = b.center + Vector3.up * 0.08f;
            float room = 6f;
            foreach (var hit in Physics.BoxCastAll(centre, half * 0.98f, dir, Quaternion.identity, 6f, ~0, QueryTriggerInteraction.Ignore))
            {
                if (hit.collider.attachedRigidbody == body || hit.collider.transform.IsChildOf(table.transform) || hit.collider.GetComponentInParent<KinematicCharacterController.KinematicCharacterMotor>() != null) continue;
                if (hit.distance <= 0f) continue; // already overlapping at the start (the floor under it)
                room = Mathf.Min(room, hit.distance);
            }
            return room;
        }

        private Vector3 Roomier(Vector3 a) => Room(a) >= Room(-a) ? a : -a;

        /// <summary>Fedya round 2: walking into the gurney the player keeps 10-15 % of his walk speed and the gurney moves
        /// along with him; holding it with LMB he pushes it at 40-50 % and never passes through it, from any side.</summary>
        private IEnumerator GurneyPush()
        {
            var table = d.Table; var body = table.GetComponent<Rigidbody>(); var brake = table.GetComponent<OperationTableBrake>();
            var handle = table.GetComponent<OnlyVolunteers.Network.NetworkPhysicsBody>();
            float walk = OperationPlayerSpeed.WalkSpeed;
            Check(table.IsServerInitialized && brake != null && !body.isKinematic, "the gurney is a dynamic server body (" + body.mass.ToString("0") + " kg)");
            Vector3 across = table.transform.right; across.y = 0f; across.Normalize();
            Vector3 along = table.transform.forward; along.y = 0f; along.Normalize();
            Vector3 top = table.transform.position + Vector3.up * 2.3f;
            Overview("r2_gurney_00_start_top", top + along * 0.01f, table.transform.position, 100f);
            PushRun run = default;
            // ---- 1. walking into a long side, no hands; then 2. into an end ----
            foreach (var axis in new[] { across, along })
            {
                Vector3 dir = Roomier(axis); float room = Room(dir);
                string name = axis == across ? "side" : "end";
                Info($"walk-push {name}: {room:F2} m of free floor ahead (and {Room(-dir):F2} m behind)");
                yield return StandAt(-dir, 0.25f);
                float seconds = Mathf.Clamp((room - 0.3f) / (walk * 0.125f), 1.2f, 3f);
                yield return MeasurePush(table.transform.position + dir * 6f, seconds, seconds - 0.8f, r => run = r);
                Overview("r2_gurney_01_walk_push_" + name + "_top", top + along * 0.01f, table.transform.position, 100f);
                Info($"walk-push {name}: player {run.player:F2} m/s ({run.player / walk * 100f:F1} % of walk {walk:F2}), gurney {run.gurney:F2} m/s, min gap {run.minGap * 100f:F1} cm, jitter {run.jitter * 100f:F0} %, yaw {run.yaw:F1} deg, lift {run.lift * 100f:F1} cm");
                Check(run.player >= walk * 0.10f && run.player <= walk * 0.15f, $"walking into its {name} he keeps 10-15 % of his walk speed ({run.player / walk * 100f:F1} %)");
                Check(Mathf.Abs(run.gurney - run.player) <= run.player * 0.12f + 0.01f, $"the gurney moves along with him at his speed ({run.gurney:F2} vs {run.player:F2} m/s)");
                Check(run.minGap > -0.01f, $"he never walks into it (smallest clearance {run.minGap * 100f:F1} cm)");
                Check(run.jitter < 0.2f, $"smooth: the gurney speed varies {run.jitter * 100f:F0} % (< 20 %)");
                Check(Vector3.Dot(table.transform.up, Vector3.up) > 0.999f && run.yaw < 4f && run.lift < 0.02f, $"no tipping, it keeps its heading (yaw {run.yaw:F1} deg), the player is never lifted");
                yield return StopCheck("walk-push " + name);
            }
            // ---- 3. holding it with LMB (the NetworkGrabber hold, real virtual mouse), walking into it: side and end ----
            foreach (var axis in new[] { across, along })
            {
                Vector3 dir = Roomier(axis); string name = axis == across ? "side" : "end";
                Info($"LMB push {name}: {Room(dir):F2} m of free floor ahead");
                yield return StandAt(-dir, 0.35f);
                Vector3 grabAt = table.transform.position + Vector3.up * 0.8f - dir * 0.15f;
                LookAt(grabAt); yield return Frames(2);
                var eyeRay = new Ray(pawn.ViewCamera.transform.position, pawn.ViewCamera.transform.forward);
                Info("LMB aim: " + (Physics.Raycast(eyeRay, out RaycastHit aimHit, 3f, ~0, QueryTriggerInteraction.Ignore) ? aimHit.collider.name + " at " + aimHit.distance.ToString("F2") + " m" : "nothing"));
                lmb = true; PushMouse(); yield return new WaitForSeconds(0.4f);
                Check(handle.HasHolder && brake.LocalHolds(kcc), "LMB takes hold of the gurney (" + name + "); the local player knows he holds it (" + handle.HasHolder + "/" + brake.LocalHolds(kcc) + ")");
                float seconds = Mathf.Clamp((Room(dir) - 0.3f) / (walk * 0.45f), 1.2f, 2.5f);
                yield return MeasurePush(table.transform.position + dir * 6f, seconds, seconds - 0.7f, r => run = r);
                Overview("r2_gurney_02_lmb_push_" + name + "_top", top + along * 0.01f, table.transform.position, 100f);
                lmb = false; PushMouse(); walking = false; yield return new WaitForSeconds(0.5f);
                Info($"LMB push {name}: player {run.player:F2} m/s ({run.player / walk * 100f:F1} %), gurney {run.gurney:F2} m/s, min gap {run.minGap * 100f:F1} cm, jitter {run.jitter * 100f:F0} %");
                Check(run.player >= walk * 0.40f && run.player <= walk * 0.50f, $"holding it he pushes at 40-50 % of his walk speed ({run.player / walk * 100f:F1} %)");
                Check(Mathf.Abs(run.gurney - run.player) <= run.player * 0.15f + 0.02f, $"the gurney goes with him ({run.gurney:F2} vs {run.player:F2} m/s)");
                Check(run.minGap > -0.01f, $"he never passes through it (smallest clearance {run.minGap * 100f:F1} cm)");
                Check(Vector3.Dot(table.transform.up, Vector3.up) > 0.999f, "held and pushed it stays upright");
            }
            // ---- 4. walking alongside it (no intent to push) moves nothing: the long side without the tray ----
            Vector3 trayAt = table.TrayAnchor != null ? table.TrayAnchor.position : table.transform.position;
            Vector3 side = Vector3.Dot(trayAt - table.transform.position, across) > 0f ? -across : across;
            yield return StandAt(side, 0.12f);
            Vector3 before = table.transform.position;
            walkTarget = pawn.Position + along * 0.7f; walking = true; yield return new WaitForSeconds(1.0f); walking = false;
            yield return new WaitForSeconds(0.3f);
            Info("side walk moved the gurney by " + (table.transform.position - before).ToString("F3") + "; touching: " + Touching(table));
            Check(Flat(before, table.transform.position) < 0.03f, "walking along its side does not drag it (" + (Flat(before, table.transform.position) * 100f).ToString("F1") + " cm)");
            yield return Frames(3);
        }

        /// <summary>Item 3: how fast can a player walk with a body bag in his arms (E) before it lags or flies behind? The
        /// bag is carried at several speed caps; the hand-to-bag lag and its growth are measured, then the shipped cap.</summary>
        /// <summary>"Follows smoothly": walking adds at most this much hand-to-bag lag over the offset at rest, and it does not grow.</summary>
        private const float CarryLagLimit = 0.25f;
        private IEnumerator CarrySpeed()
        {
            Vector3 spot = d.Table.transform.position + Vector3.forward * 5.5f;
            var npc = SpawnLocal("SausageBuddy_B", spot, 0f);
            yield return Frames(2);
            float impulse = npc.HitImpulse; npc.HitImpulse = 0f;
            npc.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, npc.Center); npc.HitImpulse = impulse;
            yield return new WaitForSeconds(1.5f);
            var c = CaptureNpc.Of(npc); string id = c.PatientId;
            c.Rules.Die(DeathCause.Overdose);
            yield return new WaitForSeconds(0.5f);
            Vector3 pelvis = npc.PhysicalBody.Landmark(NpcLandmark.Pelvis);
            Teleport(Ground(pelvis + Vector3.right * 1.0f), -90f); yield return Frames(3);
            LookAt(pelvis); yield return Frames(3);
            keys.Add(UnityEngine.InputSystem.Key.R); PushKeys();
            float end = Time.time + 1.3f; while (Time.time < end) { PushKeys(); LookAt(pelvis); yield return null; }
            keys.Remove(UnityEngine.InputSystem.Key.R); PushKeys(); yield return new WaitForSeconds(0.5f);
            var bag = d.Disposal.Corpses.Find(x => x != null && x.PatientId == id);
            if (!Check(bag != null && bag.Bagged, "fixture: the field corpse is packed (real R)")) yield break;
            LookAt(bag.Center); yield return Frames(3);
            yield return Tap(UnityEngine.InputSystem.Key.E); yield return new WaitForSeconds(1.2f);
            if (!Check(d.Disposal.Hands.Carrying == bag, "E carries the bag")) yield break;
            var hands = d.Disposal.Hands;
            var results = new List<string>();
            float best = 0f;
            Vector3 dir = Vector3.left; // along the open road from the base yard
            foreach (float cap in new[] { 2.0f, 2.5f, 3.0f, 3.5f, 4.0f, -1f })
            {
                CaptureCorpseHands.CarrySpeedOverride = cap;
                // settle (the hand-to-bag offset at rest is the baseline), then walk straight on where the floor is free
                walking = false; yield return new WaitForSeconds(0.5f);
                float bestFree = 0f;
                for (int k = 0; k < 16; k++)
                {
                    Vector3 cand = Quaternion.Euler(0f, k * 22.5f, 0f) * Vector3.forward;
                    float free = 14f;
                    foreach (var wallHit in Physics.SphereCastAll(pawn.Position + Vector3.up * 0.6f, 0.45f, cand, 14f, ~0, QueryTriggerInteraction.Ignore))
                    {
                        if (wallHit.distance <= 0f || wallHit.collider.GetComponentInParent<CaptureCorpse>() != null || wallHit.collider.GetComponentInParent<KinematicCharacterController.KinematicCharacterMotor>() != null) continue;
                        free = Mathf.Min(free, wallHit.distance);
                    }
                    if (free > bestFree) { bestFree = free; dir = cand; }
                }
                // Face the way he will walk (the bag is carried in front, across the view), let it settle there.
                SetYawPitch(Mathf.Atan2(dir.x, dir.z) * Mathf.Rad2Deg, 12f);
                yield return new WaitForSeconds(1.5f);
                float baseline = 0f;
                for (int k = 0; k < 10; k++) { yield return new WaitForFixedUpdate(); if (bag.Ragdoll != null) baseline += Flat(hands.HandPoint, bag.Ragdoll.PlacementPoint) / 10f; }
                Vector3 start = pawn.Position;
                walkTarget = start + dir * 30f; walking = true;
                float t0 = Time.time, lagMax = 0f, lagEnd = 0f, lagMid = 0f; Vector3 p0 = pawn.Position; bool dropped = false;
                float walkFor = Mathf.Clamp((bestFree - 1.2f) / Mathf.Max(0.5f, cap > 0f ? cap : CaptureCorpseHands.CarrySpeed), 1.6f, 3f);
                while (Time.time - t0 < walkFor)
                {
                    yield return new WaitForFixedUpdate();
                    var rag = bag.Ragdoll; if (rag == null || hands.Carrying != bag) { dropped = true; break; }
                    Vector3 hand = hands.HandPoint, com = rag.PlacementPoint;
                    float lag = Flat(hand, com);
                    if (Time.time - t0 > 0.8f) lagMax = Mathf.Max(lagMax, lag);
                    if (Time.time - t0 > 1.2f && lagMid == 0f) lagMid = lag;
                    lagEnd = lag;
                }
                walking = false;
                float speed = FlatSpeed(p0, pawn.Position, Time.time - t0);
                string label = cap < 0f ? "shipped cap" : "cap " + cap.ToString("F1");
                float extra = lagMax - baseline;
                string line = $"{label}: player {speed:F2} m/s, hand-to-bag at rest {baseline:F2} m, walking max {lagMax:F2} m (+{extra:F2}; 1.4 s {lagMid:F2} -> 3 s {lagEnd:F2}), dropped {dropped}";
                results.Add(line); Info("carry " + line);
                bool smooth = !dropped && extra < CarryLagLimit && lagEnd - lagMid < 0.1f;
                if (cap > 0f && smooth) best = Mathf.Max(best, cap);
                if (cap < 0f)
                {
                    Check(!dropped && smooth, "at the shipped carry speed (" + CaptureCorpseHands.CarrySpeed.ToString("F2") + " m/s) the bag follows smoothly (+" + CarryLagLimit.ToString("F2") + " m max): " + line);
                    Check(speed <= CaptureCorpseHands.CarrySpeed + 0.15f && speed >= CaptureCorpseHands.CarrySpeed - 0.5f, "carrying, the player walks at the carry cap (" + speed.ToString("F2") + " m/s)");
                }
                if (dropped) { LookAt(bag.Center); yield return Frames(3); yield return Tap(UnityEngine.InputSystem.Key.E); yield return new WaitForSeconds(1.0f); }

            }
            CaptureCorpseHands.CarrySpeedOverride = -1f;
            Info("carry: highest smooth cap measured " + best.ToString("F1") + " m/s; shipped " + CaptureCorpseHands.CarrySpeed.ToString("F2") + " m/s");
            Shot("r2_carry_bag");
        }
        // ---------- items 9-11: bags at the table, the field syringe into a table bag, the kit slot, syringe orientation ----------

        /// <summary>The needle tip and the plunger end of a first-person syringe model in camera space (z = away from the eye).</summary>
        private bool SyringeEnds(FieldTool tool, out float needleZ, out float plungerZ)
        {
            needleZ = plungerZ = 0f;
            var vm = d.Kit != null ? KitViewModel() : null;
            var model = vm != null ? vm.Model(tool) : null;
            if (model == null) return false;
            Transform needle = null, plunger = null;
            foreach (var t in model.GetComponentsInChildren<Transform>(false))
            {
                if (needle == null && (t.name == "NEEDLE" || t.name == "SM_FineNeedle")) needle = t;
                if (plunger == null && (t.name == "PLUNGER" || t.name == "SM_ThumbPad")) plunger = t;
            }
            if (needle == null || plunger == null) return false;
            var cam = pawn.ViewCamera.transform;
            Vector3 Centre(Transform t) => t.TryGetComponent(out Renderer r) ? r.bounds.center : t.position;
            needleZ = cam.InverseTransformPoint(Centre(needle)).z;
            plungerZ = cam.InverseTransformPoint(Centre(plunger)).z;
            return true;
        }

        private CaptureViewModel KitViewModel()
        {
            var field = typeof(CaptureFieldKit).GetField("viewModel", BindingFlags.Instance | BindingFlags.NonPublic);
            return field != null ? field.GetValue(d.Kit) as CaptureViewModel : null;
        }

        private int SealedBloodItems()
        {
            int n = 0;
            foreach (var item in d.Table.ServerItems) if (item != null && item.Kind == 2) n++;
            return n;
        }

        /// <summary>Fedya round 2, items 9-11 (real keys and mouse): the empty blood bags lie on the tray before any patient;
        /// the kit is one hotbar slot whose key cycles ties → anesthesia → blood → empty hands; a tool in hand + LMB is used on
        /// the NPC (no grab); the blood drawn in the field stays in the syringe and is poured into an empty table bag with the
        /// same smooth plunger/bag animation (portion counted once, one sealed bag, saved); both syringes point the needle
        /// away from the player, idle and in use.</summary>
        private IEnumerator FieldBlood()
        {
            var table = d.Table;
            // ---- 9a. bags at the table from the start ----
            yield return new WaitForSeconds(0.5f);
            int bagsShown = 0;
            foreach (var t in table.GetComponentsInChildren<Transform>(false)) if (t.name.StartsWith("EmptyBag_")) bagsShown++;
            Check(!table.HasPatient && bagsShown == table.Tuning.bloodBagCount, $"before any patient the tray shows its {bagsShown} empty blood bags");
            var bag0 = table.BagPose(0);
            Overview("r2_blood_01_bags_at_start", bag0.position + Vector3.up * 0.6f + table.transform.forward * 0.15f + table.transform.right * 0.25f, bag0.position, 60f);
            // ---- 10. the kit slot ----
            Check(d.Kit.Inventory != null && SlotWithKit() == CaptureFieldKit.KitSlot, "the field kit is one hotbar item in slot 2 (slot 1 = bare hands)");
            yield return Tap(Key.Digit1);
            Check(d.Kit.Tool == FieldTool.Hands, "1: bare hands");
            var order = new[] { FieldTool.Ties, FieldTool.Anesthesia, FieldTool.Blood, FieldTool.Hands, FieldTool.Ties };
            string seen = "";
            foreach (var want in order) { yield return Tap(Key.Digit2); seen += d.Kit.Tool + " "; }
            Check(seen.Trim() == string.Join(" ", order), "pressing 2 again and again cycles the kit: " + seen.Trim());
            var keyboard = OpsInput.Keyboard;
            Check(keyboard != null && !keyboard.zKey.isPressed, "the old Z/X/C keys are gone (no handler reads them)");
            // ---- the NPC (fixture: knocked out, hands tied so blood may be drawn) ----
            Vector3 spot = table.transform.position + Vector3.forward * 5.5f;
            var npc = SpawnLocal("SausageBuddy_A", spot, 0f);
            yield return Frames(2);
            float impulse = npc.HitImpulse; npc.HitImpulse = 0f;
            npc.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, npc.Center); npc.HitImpulse = impulse;
            yield return new WaitForSeconds(1.5f);
            var c = Captured(npc);
            c.Tie(TieTarget.Hands);
            yield return Approach(npc);
            // ---- 11. syringe orientation, idle ----
            foreach (var tool in new[] { FieldTool.Anesthesia, FieldTool.Blood })
            {
                yield return TakeTool(tool);
                yield return Frames(3);
                bool ok = SyringeEnds(tool, out float nz, out float pz);
                Check(ok && nz > pz + 0.05f, $"{tool} syringe in hand: the needle points away from the player (needle {nz:F2} m, plunger {pz:F2} m from the eye)");
                Shot("r2_blood_02_" + tool.ToString().ToLowerInvariant() + "_idle");
            }
            // ---- a tool in hand + LMB is used, never a grab ----
            yield return TakeTool(FieldTool.Ties);
            yield return Frames(2);
            Check(grabber.ScriptDriven, "with a tool in hand the map grab steps aside (LMB is the tool)");
            yield return TakeTool(FieldTool.Hands);
            yield return Frames(3);
            Check(!grabber.ScriptDriven || grabber.IsHolding, "with empty hands the map grab takes LMB again");
            // ---- 11b. anesthesia in use ----
            yield return TakeTool(FieldTool.Anesthesia);
            SyringeEnds(FieldTool.Anesthesia, out _, out float before);
            bool inUse = false;
            yield return HoldLeft(1.0f, () => Bone(npc, "Neck").position, () =>
            {
                if (!inUse && d.Kit.Using && SyringeEnds(FieldTool.Anesthesia, out float nz, out float pz))
                { inUse = true; Check(nz > pz + 0.05f, $"anesthesia syringe in use: the needle points away ({nz:F2} vs {pz:F2} m)"); Shot("r2_blood_06_anesthesia_in_use"); }
            });
            Check(inUse, "the anesthesia syringe was used with LMB (aimed " + (d.Kit.Aimed != null ? d.Kit.Aimed.PatientId : "-") + ", barrel " + d.Kit.AnesthesiaBarrel.ToString("F2") + ", hint «" + d.Hud.LastHint + "»)");
            // ---- 9b. the field draw: the portion stays in the syringe ----
            yield return TakeTool(FieldTool.Blood);
            float plungerAt = 0f; bool usingSeen = false;
            yield return HoldLeft(d.Tuning.bloodSeconds + 2.0f, () => Bone(npc, "RightArm").position, () =>
            {
                if (!usingSeen && d.Kit.Using && d.Kit.BloodFill > 0.5f && SyringeEnds(FieldTool.Blood, out float nz, out float pz))
                { usingSeen = true; plungerAt = pz; Check(nz > pz + 0.05f, $"blood syringe in use: the needle still points away ({nz:F2} vs {pz:F2} m)"); Shot("r2_blood_03_drawing"); }
            });
            Check(c.State.bloodPortions == 1 && d.Kit.BloodFill >= 1f, $"a field draw fills the syringe with one portion (portions {c.State.bloodPortions}, fill {d.Kit.BloodFill:0.00})");
            yield return HoldLeft(1.0f, () => Bone(npc, "RightArm").position);
            Check(c.State.bloodPortions == 1 && d.Kit.BloodFill >= 1f, "a full syringe draws no second portion before it is emptied");
            // ---- 9c. walk up to the table, pour it into an empty bag ----
            Vector3 stand = table.transform.position + (bag0.position - table.transform.position).normalized * 1.3f; stand.y = pawn.Position.y;
            yield return WalkTo(Ground(stand), 10f);
            int items0 = SealedBloodItems(); int used0 = table.View.bagsUsedMask;
            Collider bagHit = null;
            foreach (var tag in table.GetComponentsInChildren<OperationTargetTag>(true)) if (tag.kind == TargetKind.BloodBag && tag.index == 0) bagHit = tag.GetComponent<Collider>();
            Vector3 bagAt = bagHit != null ? bagHit.bounds.center : bag0.position;
            Info($"bag 0: pose {bag0.position:F3}, hit box {(bagHit != null ? bagHit.bounds.center.ToString("F3") + " enabled " + bagHit.enabled + " active " + bagHit.gameObject.activeInHierarchy : "none")}, eye {pawn.ViewCamera.transform.position:F3}");
            LookAt(bagAt); yield return Frames(3);
            {
                var eye = pawn.ViewCamera.transform; var sb = new System.Text.StringBuilder();
                var hits = Physics.RaycastAll(eye.position, eye.forward, 3f, ~0, QueryTriggerInteraction.Collide);
                System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
                foreach (var h in hits) sb.Append(h.collider.name).Append(h.collider.isTrigger ? "(T)" : "").Append("@").Append(h.distance.ToString("F2")).Append(" ");
                Info("aim at bag 0 (" + Vector3.Distance(eye.position, bag0.position).ToString("F2") + " m): " + sb);
            }
            Check(d.Kit.AimedBag == 0, "aiming the full syringe at the first empty bag (hint «" + (d.Hud != null ? d.Hud.LastHint : "") + "»)");
            lmb = true; PushMouse(); yield return Frames(2); lmb = false; PushMouse();
            yield return new WaitForSeconds(table.Tuning.bloodTransferSeconds * 0.5f);
            float bagMid = table.View.bagFill != null && table.View.bagFill.Length > 0 ? table.View.bagFill[0] : -1f;
            Check(d.Kit.Transferring && d.Kit.BloodFill > 0.2f && d.Kit.BloodFill < 0.8f && Mathf.Abs(bagMid + d.Kit.BloodFill - 1f) < 0.1f,
                  $"mid-transfer: the syringe empties ({d.Kit.BloodFill:0.00}) as the bag fills by the same amount ({bagMid:0.00})");
            SyringeEnds(FieldTool.Blood, out float nzT, out float pzT);
            Check(pzT > plungerAt - 0.001f || d.Kit.BloodFill < 0.99f, "the plunger goes down while pouring");
            Shot("r2_blood_04_pouring");
            yield return new WaitForSeconds(table.Tuning.bloodTransferSeconds + 0.6f);
            Check(!d.Kit.Transferring && d.Kit.BloodFill <= 0.001f, "the field syringe is empty after the transfer");
            Check((table.View.bagsUsedMask & 1) != 0 && used0 == 0 && SealedBloodItems() == items0 + 1, $"one sealed blood bag on the tray (items {items0} -> {SealedBloodItems()})");
            Check(c.State.bloodPortions == 1, "the portion was counted once (on the NPC, when drawn)");
            OperationPhysicalItem sealedBag = null;
            foreach (var item in table.ServerItems) if (item != null && item.Kind == 2) sealedBag = item;
            Vector3 holderAt = bagHit != null ? bagHit.transform.parent.position : bag0.position;
            Info($"sealed bag item at {(sealedBag != null ? sealedBag.transform.position.ToString("F3") : "-")}, bag slot {holderAt:F3}, BagPose {table.BagPose(0).position:F3}");
            Check(sealedBag != null && Vector3.Distance(sealedBag.transform.position, holderAt) < 0.3f, "the sealed bag lies on the tray where the empty one was");
            Overview("r2_blood_05_bag_sealed", bag0.position + Vector3.up * 0.6f + table.transform.forward * 0.15f + table.transform.right * 0.25f, bag0.position, 60f);
            // ---- saved ----
            yield return Tap(Key.K); yield return Frames(2);
            var data = JsonUtility.FromJson<CaptureSaveData>(File.ReadAllText(d.SavePath));
            int savedBlood = 0; if (data.table != null && data.table.items != null) foreach (var it in data.table.items) if (it.sealedBlood) savedBlood++;
            Check(data.kit.bloodFill <= 0.001f && savedBlood >= 1, $"saved: the field syringe empty, the sealed bag on the tray ({savedBlood})");
            yield return TakeTool(FieldTool.Hands);
        }
        // ---------- item 8: internals never poke through the skin off the table ----------

        /// <summary>Item 5 (G38 contract): the 96 UCX bone colliders are convex, renderer off, layer SurgicalBone, tagged, collide
        /// with nothing; a tool's sphere sweep (8 mm) from the top camera with the SurgicalBone mask hits only rib/sternum
        /// colliders or nothing (the intercostal gaps stay open).</summary>
        private IEnumerator BoneSweep(Transform body)
        {
            int layer = OperationSurgicalBones.Layer, colliders = 0, bad = 0;
            var bounds = new Bounds(); bool any = false;
            foreach (var c in body.GetComponentsInChildren<MeshCollider>(true))
            {
                if (!c.name.StartsWith("UCX_")) continue;
                colliders++;
                var r = c.GetComponent<MeshRenderer>();
                bool tagOk = c.CompareTag(c.name.StartsWith("UCX_STERNUM") ? OperationSurgicalBones.SternumTag : OperationSurgicalBones.RibTag);
                if (!c.convex || c.gameObject.layer != layer || (r != null && r.enabled) || !tagOk || c.isTrigger) bad++;
                if (!any) { bounds = c.bounds; any = true; } else bounds.Encapsulate(c.bounds);
            }
            bool isolated = layer >= 0;
            for (int i = 0; i < 32 && isolated; i++) if (!Physics.GetIgnoreLayerCollision(layer, i)) isolated = false;
            Check(colliders == 96 && bad == 0 && isolated, $"bone colliders: {colliders} UCX, {bad} not convex/layer SurgicalBone/tagged/renderer off; the layer collides with nothing: {isolated}");
            var up = d.Table.transform.up;
            int hits = 0, misses = 0, wrong = 0, unmaskedOther = 0; const int N = 9;
            Vector3 right = d.Table.transform.right, fwd = d.Table.transform.forward;
            for (int a = 0; a < N; a++)
                for (int b = 0; b < N; b++)
                {
                    Vector3 p = bounds.center + right * Mathf.Lerp(-bounds.extents.x, bounds.extents.x, a / (N - 1f)) * 0.95f
                                              + fwd * Mathf.Lerp(-bounds.extents.z, bounds.extents.z, b / (N - 1f)) * 0.95f + up * 0.6f;
                    if (Physics.SphereCast(p, 0.004f, -up, out RaycastHit hit, 1.2f, OperationSurgicalBones.Mask, QueryTriggerInteraction.Ignore))
                    {
                        hits++;
                        if (hit.collider.gameObject.layer != layer || !(hit.collider.CompareTag(OperationSurgicalBones.RibTag) || hit.collider.CompareTag(OperationSurgicalBones.SternumTag))) wrong++;
                    }
                    else misses++;
                    if (Physics.SphereCast(p, 0.004f, -up, out RaycastHit any0, 1.2f, ~0, QueryTriggerInteraction.Ignore) && any0.collider.gameObject.layer != layer) unmaskedOther++;
                }
            Check(wrong == 0 && hits > 0, $"top-camera sphere sweeps (8 mm, SurgicalBone mask, {N * N}): {hits} hit a rib/sternum, {misses} nothing, {wrong} anything else");
            Info($"without the mask {unmaskedOther} of {N * N} sweeps first hit something else (skin, organs, table): the bone tools must use the mask");
            yield return null;
        }

        /// <summary>Drawn internal parts under a body: chest visuals (ribcage, heart, lungs, vessels) and in-body organs.</summary>
        private static int ActiveInternals(Transform body)
        {
            int n = 0;
            if (body == null) return 0;
            foreach (var t in body.GetComponentsInChildren<Transform>(false))
                if (t.name.EndsWith("(chest visual)") || (t.name.StartsWith("Organ_") && t.name.EndsWith("_v03"))) n++;
            return n;
        }

        /// <summary>Fedya round 2 item 8: a corpse with an open belly is taken off the table and lands in several poses
        /// (dropped head first, folded over the gurney's edge, on its side): its ribs, heart, lungs, vessels and organs are
        /// hidden off the table (they hang on Spine while the chest part bends), shown again on the table.</summary>
        private IEnumerator Internals()
        {
            var table = d.Table; var presentation = table.GetComponent<OperationPresentation>();
            var npc = SpawnLocal("SausageBuddy_B", table.transform.position + Vector3.forward * 2f, 0f);
            yield return Frames(2);
            float impulse = npc.HitImpulse; npc.HitImpulse = 0f;
            npc.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, npc.Center); npc.HitImpulse = impulse;
            yield return Frames(3);
            npc.Ragdoll.PlaceLying(table.transform.position + Vector3.up * 0.7f, table.transform.forward, true);
            yield return WaitFor(() => table.HasPatient && table.State != null && table.State.aligned, 8f, "fixture: the patient is admitted (cloud)");
            yield return new WaitForSeconds(2.5f);
            // Fixture: the belly is open (the real cut is covered by the operation probes).
            var rules = table.ServerRules; rules.State.zoneOpened = true; rules.State.zoneCut = 1f; foreach (var o in rules.State.organs) o.cut = 1f;
            yield return new WaitForSeconds(1.0f);
            var patientBody = table.PatientObject.transform;
            int onTable = ActiveInternals(patientBody);
            Check(presentation.InternalsShown && onTable >= 8, $"on the table, belly open: ribs, heart, lungs, vessels and the three organs show ({onTable})");
            Check(presentation.BoneColliders == 96, $"the ribcage carries the 96 bone colliders ({presentation.BoneColliders})");
            yield return BoneSweep(patientBody);
            Vector3 zone = table.Abdomen != null ? table.Abdomen.ZonePose.position : table.transform.position + Vector3.up * 0.8f;
            Overview("r2_internals_00_on_table_top", zone + Vector3.up * 0.9f + table.transform.forward * 0.01f, zone, 60f);
            // Fixture: dead, straps open (both covered elsewhere); then the real LMB take-off with empty hands.
            rules.Die(DeathCause.Blood);
            for (int i = 0; i < rules.State.restraints.Length; i++) rules.State.restraints[i] = false;
            yield return new WaitForSeconds(0.6f);
            yield return TakeTool(FieldTool.Hands);
            Vector3 pelvis = table.PatientObject.transform.position;
            Teleport(Ground(pelvis + table.transform.right * 1.1f), Mathf.Atan2(-table.transform.right.x, -table.transform.right.z) * Mathf.Rad2Deg);
            yield return Frames(3);
            LookAt(pelvis + Vector3.up * 0.05f); yield return Frames(3);
            lmb = true; PushMouse(); yield return Frames(2); lmb = false; PushMouse(); yield return new WaitForSeconds(0.8f);
            var corpse = d.Disposal.Corpses.Find(x => x != null && x.Ragdoll != null && x.Ragdoll.Active && x.FieldNpc == null);
            if (!Check(corpse != null && !table.HasPatient, "LMB with empty hands takes the open-bellied corpse off the table")) yield break;
            var ragdoll = corpse.GetComponent<NpcRagdoll>();
            var poses = new (string name, Vector3 at, Quaternion turn, Vector3 velocity)[]
            {
                ("dropped_head_first", table.transform.position + table.transform.right * 1.6f + Vector3.up * 1.4f, Quaternion.Euler(80f, 0f, 0f), Vector3.down * 2f),
                ("folded_over_gurney", table.transform.position + Vector3.up * 1.3f, Quaternion.Euler(0f, 90f, 0f), Vector3.zero),
                ("on_its_side", table.transform.position - table.transform.right * 1.4f + Vector3.up * 0.6f, Quaternion.Euler(0f, 0f, 90f), Vector3.zero),
            };
            foreach (var pose in poses)
            {
                Vector3 com = ragdoll.CenterOfMass;
                ragdoll.MoveRigid(com, Quaternion.identity, pose.at, pose.turn, pose.velocity);
                yield return new WaitForSeconds(2.5f);
                int shown = ActiveInternals(corpse.transform);
                Vector3 c = ragdoll.CenterOfMass;
                Check(!presentation.InternalsShown && shown == 0, $"{pose.name}: no internal part is drawn off the table ({shown} shown)");
                Overview("r2_internals_" + pose.name + "_a", c + new Vector3(1.1f, 1.0f, 0.6f), c, 55f);
                Overview("r2_internals_" + pose.name + "_b", c + new Vector3(-0.9f, 0.7f, -1.0f), c, 55f);
            }
        }
#endif
    }
}
