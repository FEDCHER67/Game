using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Clinic;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Capture
{
    public sealed partial class CaptureScenarioDriver
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        // The Hamlet stretch of the main dirt road, ~45 m east of the base (crowd district "village").
        private static readonly Vector3 CaptureSpot = new Vector3(226.2f, 0f, 525.5f);
        private static readonly Vector3 VanSpot = new Vector3(229.6f, 0f, 520.5f);
        private static readonly Vector3[] RouteToBase =
        {
            new Vector3(229.2f, 0f, 512f), new Vector3(226.5f, 0f, 506.9f), new Vector3(218f, 0f, 504.4f), new Vector3(207f, 0f, 503.6f),
            new Vector3(200.2f, 0f, 504.8f), new Vector3(195.8f, 0f, 507.0f), new Vector3(193.4f, 0f, 511.2f), new Vector3(192.6f, 0f, 515.5f),
        };

        // ---------- NPCs ----------
        private GreyboxNpc SpawnLocal(string visual, Vector3 at, float yaw)
        {
            var crowd = CrowdDirector.Instance;
            GameObject template = null;
            foreach (var t in crowd.Templates)
            {
                if (t == null) continue;
                var a = t.GetComponentInChildren<Animator>(true);
                if (template == null || (a != null && a.gameObject.name == visual)) template = t;
                if (a != null && a.gameObject.name == visual) break;
            }
            var go = Instantiate(template, Ground(at), Quaternion.Euler(0f, yaw, 0f), template.transform.parent != null ? template.transform.parent.parent : null);
            go.name = "Hamlet local " + visual + " " + Random.Range(100, 999);
            go.SetActive(true);
            return go.GetComponent<GreyboxNpc>();
        }

        private static Vector3 Ground(Vector3 p)
        {
            if (Physics.Raycast(p + Vector3.up * 3f, Vector3.down, out RaycastHit hit, 8f, OvLayers.ShootMask & ~OvLayers.NpcMask, QueryTriggerInteraction.Ignore))
                return hit.point;
            return p;
        }

        /// <summary>An arm (or leg) bone of a lying NPC that the crosshair can actually reach from here (a crossed leg can hide
        /// one forearm): the first whose view ray hits that body's arm (leg) part.</summary>
        private Transform VisibleLimb(GreyboxNpc npc, bool arm)
        {
            string[] bones = arm ? new[] { "LeftForeArm", "RightForeArm", "LeftArm", "RightArm" } : new[] { "LeftLeg", "RightLeg", "LeftUpLeg", "RightUpLeg" };
            Vector3 eye = pawn.ViewCamera.transform.position;
            var rag = npc.Ragdoll;
            foreach (var name in bones)
            {
                var bone = Bone(npc, name);
                Vector3 to = bone.position - eye;
                if (!Physics.Raycast(eye, to.normalized, out RaycastHit hit, to.magnitude + 0.3f, OvLayers.ShootMask, QueryTriggerInteraction.Ignore)) continue;
                if (hit.collider.GetComponentInParent<GreyboxNpc>() != npc || rag == null || !rag.Active) continue;
                int part = rag.PartOf(hit.collider);
                if (part < 0) continue;
                var kind = rag.Profile.Parts[part].Kind;
                bool isArm = kind == NpcRagdollProfile.Kind.UpperArm || kind == NpcRagdollProfile.Kind.ForeArm;
                bool isLeg = kind == NpcRagdollProfile.Kind.Thigh || kind == NpcRagdollProfile.Kind.Calf;
                if (arm ? isArm : isLeg) { Info("aiming at his " + name); return bone; }
            }
            return Bone(npc, bones[0]);
        }

        private static Transform Bone(GreyboxNpc npc, string name)
        {
            foreach (var t in npc.GetComponentsInChildren<Transform>(true)) if (t.name == "mixamorig:" + name) return t;
            return npc.transform;
        }

        /// <summary>Q as GreyboxInteractor does it: the current weapon, the zone along the view ray, the hit.</summary>
        private void KnockOut(GreyboxNpc npc)
        {
            Vector3 head = Bone(npc, "Head").position;
            LookAt(head);
            var interactor = pawn.GetComponentInChildren<GreyboxInteractor>(true);
            WeaponStun weapon = interactor != null ? interactor.CurrentWeapon : WeaponStun.Fist;
            Transform eye = pawn.ViewCamera.transform;
            var ray = new Ray(eye.position, (head - eye.position).normalized);
            npc.Hit(weapon, npc.ZoneAlong(ray), pawn.Position, head);
        }

        private Vector3 Pelvis(GreyboxNpc npc) => npc.PhysicalBody != null && npc.PhysicalBody.Active ? npc.PhysicalBody.Landmark(NpcLandmark.Pelvis) : npc.Center;
        private Vector3 Collar(GreyboxNpc npc) => npc.PhysicalBody != null && npc.PhysicalBody.Active ? npc.PhysicalBody.Landmark(NpcLandmark.Collar) : npc.Center;

        /// <summary>Lays a downed body along the cargo bay (as GreyboxNpc lays a sitter that goes down there).</summary>
        private void PlaceInBay(GreyboxNpc npc, float alongZ, float acrossX = 0f)
        {
            var bay = cargo.CargoSpace;
            Bounds box = bay.LocalBox;
            Vector3 floor = bay.ToWorld(new Vector3(box.center.x + acrossX, box.min.y + 0.02f, alongZ));
            if (npc.Ragdoll != null && npc.Ragdoll.Active) npc.Ragdoll.PlaceLying(floor, bay.Rotation * Vector3.forward, true);
            else if (npc.PhysicalBody != null) npc.PhysicalBody.PlaceLying(floor, bay.Rotation * Vector3.forward);
        }

        private int InVan()
        {
            int n = 0;
            foreach (var npc in GreyboxNpc.All) if (npc != null && npc.InCargo && ReferenceEquals(npc.Carrier, cargo.CargoSpace)) n++;
            return n;
        }

        /// <summary>Walks up to a lying body (about 1.1 m from his hips), as a player would before using a tool.</summary>
        private IEnumerator Approach(GreyboxNpc npc, float distance = 1.1f)
        {
            Vector3 hips = Pelvis(npc);
            Vector3 from = pawn.Position - hips; from.y = 0f;
            if (from.sqrMagnitude < 0.01f) from = Vector3.back;
            Vector3 stand = hips + from.normalized * distance;
            Vector3 before = pawn.Position;
            yield return WalkTo(Ground(stand), 8f);
            Info($"walked {Vector3.Distance(before, pawn.Position):0.0} m to him (now {Vector3.Distance(pawn.Position, hips):0.0} m from his hips)");
        }

        // ---------- the map carry (LMB: the map's PhysicsGrabber in its script-driven mode) ----------
        private bool Grab(Vector3 point, GreyboxNpc expected = null)
        {
            grabber.ScriptDriven = true;
            LookAt(point);
            pawn.ViewCamera.transform.rotation = Quaternion.LookRotation(point - pawn.ViewCamera.transform.position);
            bool ok = grabber.ScriptGrab();
            if (ok && expected != null && (grabber.GrabbedBody == null || grabber.GrabbedBody.GetComponentInParent<GreyboxNpc>() != expected))
            { Info("another body blocks the intended patient's grab ray"); grabber.ScriptRelease(); ok = false; }
            if (ok) grabber.PointHoldDistance = Vector3.Distance(pawn.ViewCamera.transform.position, point);
            else
            {
                Transform eye = pawn.ViewCamera.transform;
                string what = Physics.Raycast(eye.position, eye.forward, out RaycastHit hit, 4f, ~(1 << OvLayers.VehicleInterior), QueryTriggerInteraction.Ignore)
                    ? $"{hit.collider.name} at {hit.distance:0.00} m (layer {LayerMask.LayerToName(hit.collider.gameObject.layer)}, body {(hit.rigidbody != null ? hit.rigidbody.name : "-")})" : "nothing";
                Info($"grab missed: eye {eye.position}, point {point} ({Vector3.Distance(eye.position, point):0.00} m), the ray hits {what}");
            }
            return ok;
        }
        private void Release() { if (grabber.IsHolding) grabber.ScriptRelease(); }
        /// <summary>Moves the hand (the view ray and the hold distance, like the mouse and the wheel) to 'target' over 'seconds'.</summary>
        private IEnumerator HandTo(Vector3 target, float seconds)
        {
            Vector3 from = grabber.PointHoldTarget;
            float t0 = Time.time;
            if (!grabber.IsHolding) Info($"HandTo {target}: not holding (lost before)");
            while (Time.time - t0 < seconds && grabber.IsHolding)
            {
                float k = Mathf.Clamp01((Time.time - t0) / seconds);
                k = k * k * (3f - 2f * k);
                Vector3 p = Vector3.Lerp(from, target, k);
                LookAt(p);
                grabber.PointHoldDistance = Vector3.Distance(pawn.ViewCamera.transform.position, p);
                yield return new WaitForFixedUpdate();
                if (!grabber.IsHolding) Info($"HandTo {target}: the hold broke at {k:0.00} (hand {p}, eye {pawn.ViewCamera.transform.position})");
            }
        }
        /// <summary>Walks while the hand keeps the held point at 'height', 'lead' metres ahead along the way (dragging).</summary>
        private IEnumerator CarryWalk(Vector3 to, float height, float timeout, float speed = 0.6f, float trail = 1.0f)
        {
            walkTarget = to; walkSpeedScale = speed; walking = true;
            float end = Time.time + timeout;
            while (Time.time < end && grabber.IsHolding)
            {
                Vector3 flat = to - pawn.Position; flat.y = 0f;
                if (flat.magnitude < 0.3f) break;
                Vector3 held = grabber.GrabbedBody != null ? grabber.GrabbedBody.worldCenterOfMass : pawn.Position;
                Vector3 back = held - pawn.Position; back.y = 0f;
                Vector3 hand = pawn.Position + (back.sqrMagnitude > 0.01f ? back.normalized : -flat.normalized) * trail;
                hand.y = pawn.Position.y + height;
                LookAt(hand);
                grabber.PointHoldDistance = Vector3.Distance(pawn.ViewCamera.transform.position, hand);
                yield return null;
                if (!grabber.IsHolding) Info($"CarryWalk to {to}: the hold broke (player {pawn.Position}, body {held})");
            }
            walking = false;
            yield return Frames(2);
        }

        // ---------- driving ----------
        private static readonly MethodInfo GetOutMethod = typeof(GreyboxVanSeat).GetMethod("GetOut", BindingFlags.Instance | BindingFlags.NonPublic);
        private IEnumerator EnterVan()
        {
            Vector3 door = van.transform.TransformPoint(seat.DoorPoint);
            Teleport(Ground(door), van.transform.eulerAngles.y);
            yield return Frames(3);
            seat.Enter(); // E at the driver door (GreyboxInteractor -> GreyboxVanSeat.Enter)
            yield return Frames(3);
            driving = true; throttle = 0f; steer = 0f; handbrake = false;
        }
        private IEnumerator ExitVan()
        {
            throttle = 0f; handbrake = true;
            float end = Time.time + 6f;
            while (Mathf.Abs(van.SpeedKmh) > 1f && Time.time < end) { throttle = van.SpeedKmh > 0f ? -0.6f : 0.6f; yield return null; }
            throttle = 0f;
            yield return new WaitForSeconds(0.3f);
            driving = false;
            van.Handbrake = false;
            GetOutMethod?.Invoke(seat, null); // E while (almost) stopped
            yield return Frames(4);
            UseCamera(pawn.ViewCamera);
        }
        private IEnumerator DriveRoute(Vector3[] points, float kmh, float timeout)
        {
            float end = Time.time + timeout;
            int i = 0;
            while (i < points.Length && Time.time < end)
            {
                Vector3 to = points[i] - van.transform.position; to.y = 0f;
                bool last = i == points.Length - 1;
                if (to.magnitude < (last ? 1.8f : 3.2f)) { i++; continue; }
                Vector3 fwd = van.transform.forward; fwd.y = 0f;
                float angle = Vector3.SignedAngle(fwd, to, Vector3.up);
                steer = Mathf.Clamp(angle / 28f, -1f, 1f);
                float want = last ? Mathf.Min(kmh, 4f + to.magnitude * 2.5f) : kmh * (Mathf.Abs(angle) > 35f ? 0.55f : 1f);
                float speed = van.SpeedKmh;
                throttle = speed < want - 1f ? Mathf.Clamp01((want - speed) / 8f + 0.25f) : speed > want + 3f ? -0.4f : 0.05f;
                yield return null;
            }
            steer = 0f;
            Check(i >= points.Length, $"van driven to the base ({Vector3.Distance(van.transform.position, points[points.Length - 1]):0.0} m from the stop)");
        }

        // =====================================================================================
        // The full loop (CD-01..08): Hamlet NPC -> Q -> ties -> anesthesia -> blood -> van (cap 3) -> drive -> table ->
        // cloud -> operation of one kidney -> grade and blood at the table.
        // =====================================================================================
        private IEnumerator Loop()
        {
            string testSave = d.SavePath;
            if (File.Exists(testSave)) File.Delete(testSave);
            Check(d.Table.AdmissionMode && !d.Table.HasPatient, "the base table starts empty, in admission mode (no drop-off pad)");
            Check(GameObject.Find("FC_ClinicLoop") == null, "the old drop-off pad loop is off in this scene");

            // 1. A Hamlet local on the dirt road; the van parked next to him, sliding door toward him.
            van.ResetUpright(Ground(VanSpot) + Vector3.up * 0.35f, 180f);
            var npc = SpawnLocal("SausageBuddy_B", CaptureSpot, 60f);
            yield return new WaitForSeconds(0.6f);
            string district = CaptureDirector.DistrictAt(npc.Center);
            Check(district == "village", "the capture spot is in the Hamlet (crowd district " + district + ")");
            Vector3 behind = npc.transform.position - npc.transform.forward * 1.4f;
            Teleport(Ground(behind), npc.transform.eulerAngles.y);
            KnockOut(npc); // the same frame: he never sees it coming
            yield return Frames(3);
            var c = CaptureNpc.Of(npc);
            Check(npc.State == NpcState.Down && c != null, "Q knocks him down and he becomes a capture identity");
            if (c == null) yield break;
            string id = c.PatientId;
            Info($"identity {id}: district {c.Facts.districtId}, type {c.Facts.npcTypeId}, intrinsic {c.Facts.intrinsic[0]}/{c.Facts.intrinsic[1]}/{c.Facts.intrinsic[2]}");
            Check(c.Facts.districtId == "village" && c.State.organs[0].intrinsicGrade == c.Facts.intrinsic[0], "intrinsic grades rolled from the Hamlet row at the first capture");
            var record = d.Registry.Get(id);
            Check(record != null && record.Operation == c.State, "one record, one OperationState for this identity");
            // Rough handling: eight more blows while he lies there (5 condition each, as the map does): condition 60.
            float impulse = npc.HitImpulse;
            npc.HitImpulse = 0f; // the blows themselves, not eight shoves across the road
            for (int k = 0; k < 8; k++) KnockOut(npc);
            npc.HitImpulse = impulse;
            Check(Mathf.Abs(npc.Condition - 60f) < 0.01f, $"eight more blows on the downed NPC: condition {npc.Condition:0}");
            yield return new WaitForSeconds(1.2f);
            yield return Approach(npc);
            LookAt(Bone(npc, "Spine2").position);
            Shot("01_knocked_out");

            // 2. Zip ties: the kit slot (2) puts them in hand; hold LMB on the arms (hands), then on the legs (feet).
            yield return TakeTool(FieldTool.Ties);
            Check(d.Kit.Tool == FieldTool.Ties, "the kit slot (2) puts the zip ties in hand");
            int ties = d.Kit.Ties;
            Transform arm = VisibleLimb(npc, true);
            yield return HoldLeft(CaptureRules.TieSeconds + 0.25f, () => arm.position);
            Check(c.Ties.hands && d.Kit.Ties == ties - 1, "a ~1 s hold on his arms ties the hands (one tie used)");
            Check(npc.HandsBound, "hands tied: his hands are out of use (no grab, no knock)");
            Shot("02a_hands_tied");
            yield return Approach(npc);
            Transform leg = VisibleLimb(npc, false);
            yield return HoldLeft(CaptureRules.TieSeconds + 0.25f, () => leg.position);
            Check(c.Ties.feet && c.Ties.Both, "a ~1 s hold on his legs ties the feet");
            Check(npc.KickTearChance[1] < 0.2f * 0.71f, $"hands + feet: carrying him is 30 % easier (tear chance {npc.KickTearChance[1]:0.000})");
            Shot("02b_feet_tied");

            // 3. Anesthesia: 2 again (the kit cycles), hold LMB 2 s.
            yield return Approach(npc);
            yield return TakeTool(FieldTool.Anesthesia);
            Check(d.Kit.Tool == FieldTool.Anesthesia, "pressing 2 again cycles the kit to the anesthesia syringe");
            yield return HoldLeft(2.0f, () => Bone(npc, "Neck").position);
            yield return new WaitForSeconds(0.2f);
            var tuning = d.Tuning;
            Check(c.State.Sleeping && c.State.residual >= tuning.suitableMinimum && c.State.residual <= tuning.suitableMaximum,
                $"a 2 s injection in the field puts him to sleep by the table's rules (residual {c.State.residual:F2}, sleep {c.State.sleepRemaining:F0} s)");
            Shot("03_injected");

            // 4. Blood: 2 again (the blood syringe), hold LMB until one portion.
            yield return Approach(npc);
            yield return TakeTool(FieldTool.Blood);
            Check(d.Kit.Tool == FieldTool.Blood, "and once more to the blood syringe");
            float bloodSeconds = tuning.bloodSeconds + 0.5f;
            bool shotHalf = false;
            yield return HoldLeft(bloodSeconds, () => Bone(npc, "RightArm").position, () => { if (!shotHalf && d.Kit.BloodFill > 0.5f) { shotHalf = true; Shot("04a_blood_drawing"); } });
            Check(c.State.bloodPortions == 1 && d.Kit.BloodFill >= 1f, $"one blood portion drawn in the field: the syringe is full ({c.State.bloodPortions}, fill {d.Kit.BloodFill:0.00})");
            Shot("04b_blood_bag");
            yield return TakeTool(FieldTool.Hands); // empty hands (slot 1) to carry him

            // 5. Carry him into the van through the sliding door.
            if (!cargo.DoorOpen(0)) cargo.ToggleDoor(0); // E at the door
            yield return new WaitForSeconds(0.8f);
            yield return LoadIntoVan(npc, "05");
            Check(npc.InCargo && ReferenceEquals(npc.Carrier, cargo.CargoSpace), "he lies loaded in the van");
            Check(record.Stage == PatientStage.Loaded, "the lifecycle says Loaded");

            // 6. Two more already in the van, then a 4th: blocked.
            var extras = new List<GreyboxNpc>();
            for (int k = 0; k < 3; k++)
            {
                var e = SpawnLocal("SausageBuddy_A", van.transform.position + van.transform.right * 3f + van.transform.forward * (k - 1) * 1.2f, 0f);
                yield return Frames(2);
                var eye = pawn.ViewCamera.transform.position;
                e.Hit(WeaponStun.Fist, HitZone.Head, eye, e.Center);
                yield return Frames(1);
                var ce = Captured(e);
                if (ce != null) ce.QueueDose(1.0f); // asleep, so they wait in the van (D6)
                extras.Add(e);
            }
            yield return new WaitForSeconds(0.5f);
            PlaceInBay(extras[0], -1.2f, -0.3f);
            PlaceInBay(extras[1], -1.2f, 0.3f);
            yield return WaitFor(() => InVan() >= 3, 12f, "three bodies loaded (the stock van holds 3)");
            Overview("06a_three_in_van", van.transform.TransformPoint(new Vector3(3.2f, 2.4f, -0.6f)), van.transform.TransformPoint(new Vector3(0f, 0.8f, -0.9f)));
            PlaceInBay(extras[2], -0.1f, 0f);
            yield return new WaitForSeconds(1.0f);
            Check(capacity.BodiesInside >= 4 && capacity.Overloaded, $"a 4th body inside: overloaded ({capacity.BodiesInside} of {capacity.Capacity})");
            int refused = capacity.RefusedDoors;
            cargo.ToggleDoor(0); // try to shut the sliding door
            yield return new WaitForSeconds(0.5f);
            Check(cargo.DoorOpen(0) && capacity.RefusedDoors > refused, "the doors won't close with 4 inside");
            Overview("06b_fourth_body_doors_wont_close", van.transform.TransformPoint(new Vector3(3.4f, 2.0f, 0.4f)), van.transform.TransformPoint(new Vector3(0f, 0.9f, -0.6f)));
            yield return EnterVan();
            UseCamera(seat.VanCamera != null ? seat.VanCamera.GetComponent<Camera>() : Camera.main);
            Vector3 vanBefore = van.transform.position;
            int stalls = capacity.Stalls;
            throttle = 1f;
            yield return new WaitForSeconds(1.6f);
            Check(capacity.Stalls > stalls && Vector3.Distance(van.transform.position, vanBefore) < 0.6f, $"the van won't drive off: it coughs and stalls (moved {Vector3.Distance(van.transform.position, vanBefore):0.00} m)");
            Shot("06c_stall_tesno");
            throttle = 0f;
            yield return ExitVan();
            // Take the 4th one out again (as a player drags him out) and shut the door: with 3 it works.
            var fourth = extras[2];
            if (fourth.Ragdoll != null && fourth.Ragdoll.Active) fourth.Ragdoll.PlaceLying(Ground(van.transform.TransformPoint(new Vector3(3.2f, 0f, -0.3f))), van.transform.forward, true);
            yield return new WaitForSeconds(1.0f);
            Check(!capacity.Overloaded, $"back to {capacity.BodiesInside} inside");
            // shut the sliding door; a limb in the doorway stalls it (VanDoor): tidy it in and try again, as a player would
            for (int attempt = 0; attempt < 3 && (cargo.DoorOpen(0) || cargo.Slide.Openness > 0.02f); attempt++)
            {
                Teleport(WG(2.3f, -0.25f), van.transform.eulerAngles.y - 90f);
                yield return new WaitForSeconds(0.3f);
                yield return ClearDoorway();
                if (!cargo.DoorOpen(0)) cargo.ToggleDoor(0);
                cargo.ToggleDoor(0);
                float shutEnd = Time.time + 2.5f;
                while (Time.time < shutEnd && cargo.Slide.Openness > 0.02f) yield return null;
            }
            Check(!cargo.DoorOpen(0) && cargo.Slide.Openness < 0.02f, "with 3 inside the sliding door closes");

            // 7. Drive to the base.
            yield return EnterVan();
            UseCamera(seat.VanCamera != null ? seat.VanCamera.GetComponent<Camera>() : Camera.main);
            yield return new WaitForSeconds(0.3f);
            bool shotDrive = false;
            var route = new Vector3[RouteToBase.Length];
            for (int k = 0; k < route.Length; k++) route[k] = Ground(RouteToBase[k]);
            StartCoroutine(ShotWhen(() => !shotDrive && van.SpeedKmh > 12f, "07a_driving", () => shotDrive = true));
            yield return DriveRoute(route, 22f, 70f);
            yield return ExitVan();
            Check(InVan() == 3 && npc.InCargo, $"all three stayed in the van on the way ({InVan()})");
            Check(c.State.Sleeping, $"he is still asleep on arrival ({c.State.sleepRemaining:F0} s left)");
            Overview("07b_van_at_base", new Vector3(196f, 4.5f, 520f), new Vector3(188f, 0.8f, 510f));

            // 8. Out of the van and onto the table: the cloud. A top-up of anesthesia first, through the open door, in the
            //    van (D1: anywhere) — the trip ate most of his 90 s of sleep.
            if (!cargo.DoorOpen(0)) cargo.ToggleDoor(0);
            yield return new WaitForSeconds(0.9f);
            // Climb in and lean around the other two bodies until a part of THIS patient is visible.
            // The door frame and the front body can hide every bone from a standing eye outside the bay.
            holdInputs = true; crouch = true;
            yield return new WaitForSeconds(0.35f);
            pawn.Teleport(W(0.65f, 0.56f, -0.45f), van.transform.eulerAngles.y + 90f);
            yield return new WaitForSeconds(0.4f);
            yield return TakeTool(FieldTool.Anesthesia);
            float residualBefore = c.State.residual;
            string visibleBone = null;
            foreach (var lean in new[] { new Vector3(0.65f, 0.56f, -0.45f), new Vector3(0.25f, 0.56f, -1.45f), new Vector3(-0.55f, 0.56f, -0.5f) })
            {
                yield return Shuffle(W(lean.x, lean.y, lean.z), 0.4f);
                yield return new WaitForSeconds(0.25f);
                Vector3 eyeNow = pawn.ViewCamera.transform.position;
                foreach (string bone in new[] { "Spine2", "Head", "LeftArm", "RightArm", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg", "LeftFoot", "RightFoot" })
                {
                    Vector3 to = Bone(npc, bone).position - eyeNow;
                    if (to.magnitude < CaptureFieldKit.Reach && Physics.Raycast(eyeNow, to.normalized, out RaycastHit seen, CaptureFieldKit.Reach, OvLayers.ShootMask, QueryTriggerInteraction.Ignore) &&
                        seen.collider.GetComponentInParent<GreyboxNpc>() == npc) { visibleBone = bone; break; }
                }
                if (visibleBone != null) break;
            }
            Check(visibleBone != null, "a visible part of the patient is reachable inside the van");
            if (visibleBone != null)
            {
                LookAt(Bone(npc, visibleBone).position);
                yield return Frames(3);
                Info($"top-up aimed at his {visibleBone}; kit target {(d.Kit.AimedNpc != null ? d.Kit.AimedNpc.name : "-")}");
                yield return HoldLeft(1.0f, () => Bone(npc, visibleBone).position);
            }
            yield return TakeTool(FieldTool.Hands);
            Check(c.State.residual > residualBefore + 0.3f && c.State.Sleeping, $"a top-up injection in the van ({residualBefore:F2} -> {c.State.residual:F2}, sleep {c.State.sleepRemaining:F0} s)");
            holdInputs = false; crouch = false;
            int trashBefore = d.Bridge.Trash.Count;
            yield return CarryToTable(npc, "08");
            float t0 = Time.time;
            bool cloudShot = false;
            while (Time.time - t0 < 4f && !d.Table.HasPatient)
            {
                if (!cloudShot && d.Bridge.Busy) { yield return new WaitForSeconds(0.14f); Overview("08b_cloud", d.Table.transform.position + new Vector3(0f, 2.3f, 2.6f), d.Table.transform.position + Vector3.up * 0.8f); cloudShot = true; }
                yield return null;
            }
            Check(d.Table.HasPatient && d.Bridge.LastAdmittedId == id, "laid on the table he is admitted under the cloud (same PatientId)");
            Check(npc == null, "the NPC object is gone; the table owns the identity now");
            Check(d.Table.State == c.State, "the table operates on the very same OperationState that travelled with him");
            if (!d.Table.HasPatient) yield break;
            yield return new WaitForSeconds(1.2f);
            Check(d.Table.State.onTable && d.Table.State.aligned, "the existing magnet snap aligned him on PatientRest");
            Check(d.Bridge.Trash.Count > trashBefore, "his cap dropped next to the table as trash");
            foreach (var trash in d.Bridge.Trash) if (trash != null) Info($"trash {trash.name} at {trash.transform.position} (floor y {trash.transform.position.y:0.00})");
            Overview("08c_undressed_on_table", d.Table.transform.position + new Vector3(0.2f, 2.4f, 2.2f), d.Table.transform.position + Vector3.up * 0.75f);
            var patient = d.Table.PatientObject;
            bool shorts = false, body = false;
            if (patient != null) foreach (var smr in patient.GetComponentsInChildren<SkinnedMeshRenderer>()) { if (smr.name == "Shorts" && smr.enabled) shorts = true; if (smr.name == "Body") body = true; }
            Check(shorts && body, "undressed: the patient body in the patient shorts, his own head and face");
            Check(d.Table.State.Sleeping && d.Table.State.bloodPortions == 1, $"sleep and blood carried to the table (sleep {d.Table.State.sleepRemaining:F0} s, blood {d.Table.State.bloodPortions})");
            Check(d.Bridge.PatientFacts != null && d.Bridge.PatientFacts.restraints.Both, "his zip ties are still on (until the straps)");

            // 9. Operate one kidney: the operation's own real-input driver at this table (PREP, straps, OPERATION, cut, cords, pull).
            Teardown();
            var probe = gameObject.GetComponent<OperationNetworkProbe>() ?? gameObject.AddComponent<OperationNetworkProbe>();
            OperationNetworkProbe.EvidenceRoot = output;
            yield return Frames(2);
            probe.Begin("capture-kidney");
            float pend = Time.time + 180f;
            while (probe.Busy && Time.time < pend) yield return null;
            foreach (var l in probe.Log) if (l.Contains(" PASS ") || l.Contains(" FAIL ")) Line("  ops: " + l.Substring(l.IndexOf(']') + 2));
            Check(probe.LastResult == "PASS", "operation of one kidney with real input: " + probe.LastResult);
            SetupDevices();
            SetupCapture(pawn.ViewCamera);

            // 10. Grade = intrinsic - condition loss; blood at the table = 1.
            var s = d.Table.State;
            var kidney = s.organs[0];
            int expected = Mathf.Max(0, c.Facts.intrinsic[0] - CaptureGrades.ConditionLoss(c.Facts.condition));
            Info($"kidney L: intrinsic {kidney.intrinsicGrade}, condition {c.Facts.condition:0} -> loss {s.conditionLoss}, damage {kidney.damage}, grade {kidney.Grade}, card {OperationNetworkProbe.LastCardGrade}");
            Check(s.conditionLoss == 1, $"condition {c.Facts.condition:0} removes 1 grade at extraction (D8)");
            Check(kidney.removed && kidney.Grade == expected && kidney.damage == s.conditionLoss, $"kidney grade = intrinsic - condition loss ({OperationText.Tier(kidney.intrinsicGrade)} -> {OperationText.Tier(kidney.Grade)})");
            Check(OperationNetworkProbe.LastCardGrade == kidney.Grade, "the organ card shows that final grade");
            Check(s.bloodPortions == 1, "bloodPortions = 1 at the table");
            Check(Mathf.Abs(kidney.deathChance - (tuning.firstKidneyChance + tuning.bloodChancePerPortion)) < 0.001f, $"the field portion counts in the first-kidney death chance ({kidney.deathChance:F2})");
            Check(d.Bridge.PatientFacts != null && !d.Bridge.PatientFacts.restraints.Any, "closing the arm and leg straps cut both zip ties");
            Check(record.Stage == PatientStage.InOperation, "the lifecycle says InOperation");

            // Save with K (the next scenario reloads it).
            yield return Tap(Key.K);
            yield return new WaitForSeconds(0.3f);
            Check(File.Exists(testSave), "K saves the game");
        }

        /// <summary>Dev: just the van load and the carry to the table, with the van wherever it stands.</summary>
        private IEnumerator CarryOnly()
        {
            if (cargo.DoorOpen(0) == false) cargo.ToggleDoor(0);
            Teleport(WG(4.6f, -0.2f), van.transform.eulerAngles.y - 90f);
            var npc = SpawnLocal("SausageBuddy_A", WG(3.2f, -0.2f), 0f);
            yield return Frames(2);
            float impulse = npc.HitImpulse; npc.HitImpulse = 0f;
            npc.Hit(WeaponStun.Fist, HitZone.Head, pawn.Position, npc.Center);
            npc.HitImpulse = impulse;
            yield return Frames(2);
            var c = Captured(npc);
            c.QueueDose(1.0f);
            yield return new WaitForSeconds(1.5f);
            yield return LoadIntoVan(npc, "c05");
            yield return new WaitForSeconds(1f);
            yield return CarryToTable(npc, "c08");
        }

        private IEnumerator ShotWhen(System.Func<bool> when, string name, System.Action done)
        {
            float end = Time.time + 60f;
            while (Time.time < end) { if (when()) { Shot(name); done(); yield break; } yield return null; }
        }

        // Van-local frame (VanSetupBuilder's boxes): x across (+x = the sliding door side), z along (+z = the front),
        // the cargo floor at y 0.55 (the same frame NpcLoadingTest h1 uses). Points beside the van: y 0 = its wheels' ground.
        private Vector3 W(float x, float y, float z) => van.transform.TransformPoint(new Vector3(x, y, z));
        private Vector3 WG(float x, float z) => Ground(van.transform.TransformPoint(new Vector3(x, 0f, z)));

        /// <summary>The player's teleport-shuffle inside the cramped bay (crouched there, as after climbing in).</summary>
        private IEnumerator Shuffle(Vector3 to, float seconds)
        {
            Vector3 from = pawn.Position;
            float t0 = Time.time;
            while (Time.time - t0 < seconds)
            {
                float k = Mathf.Clamp01((Time.time - t0) / seconds);
                kcc.Character.Motor.SetPosition(Vector3.Lerp(from, to, k));
                yield return new WaitForFixedUpdate();
            }
        }

        /// <summary>Pushes any hand, foot or head lying in the sliding doorway back into the bay (a player tidying up).</summary>
        private IEnumerator ClearDoorway()
        {
            foreach (var npc in new List<GreyboxNpc>(GreyboxNpc.All))
            {
                if (npc == null || npc.Ragdoll == null || !npc.Ragdoll.Active) continue;
                foreach (string part in new[] { "LeftFoot", "RightFoot", "LeftHand", "RightHand", "Head" })
                {
                    Vector3 local = van.transform.InverseTransformPoint(Bone(npc, part).position);
                    if (local.x < 0.72f || local.x > 2.2f || local.z < -1.1f || local.z > 0.6f) continue;
                    yield return WalkTo(WG(1.75f, Mathf.Clamp(local.z, -0.9f, 0.4f)), 4f);
                    if (Grab(Bone(npc, part).position))
                    {
                        yield return HandTo(W(0.3f, 1.0f, Mathf.Clamp(local.z, -0.9f, 0.3f)), 0.6f);
                        yield return HandTo(W(-0.2f, 0.85f, Mathf.Clamp(local.z, -0.9f, 0.3f)), 0.4f);
                        Release();
                        Info($"pushed {npc.name}'s {part} out of the doorway");
                    }
                    grabber.ScriptDriven = false;
                    yield return new WaitForSeconds(0.4f);
                }
            }
        }

        /// <summary>Stand by a lying body on the side toward 'toward' (to drag him there with the body trailing behind).</summary>
        private IEnumerator ApproachToward(GreyboxNpc npc, Vector3 toward, float distance = 0.9f)
        {
            Vector3 collar = Collar(npc);
            Vector3 dir = toward - collar; dir.y = 0f;
            if (dir.sqrMagnitude < 0.01f) dir = Vector3.forward;
            yield return WalkTo(Ground(collar + dir.normalized * distance), 8f);
        }

        /// <summary>The solo load through the sliding door, as NpcLoadingTest h1 does it with the same grabber: drag him by
        /// the collar to the door, climb in, take the collar again from inside, lift it over the sill, back into the bay
        /// (the van's body slide takes the hips up), lower, let go.</summary>
        private IEnumerator LoadIntoVan(GreyboxNpc npc, string shot)
        {
            Vector3 doorOut = WG(1.3f, -0.15f);
            yield return ApproachToward(npc, doorOut);
            bool grabbed = Grab(Collar(npc), npc);
            if (!grabbed) Warn("LMB (scripted) missed his collar"); else Line("PASS LMB grabs him by the collar");
            if (grabbed)
            {
                yield return HandTo(Collar(npc) + Vector3.up * 0.35f, 0.4f);
                Shot(shot + "a_carry");
                yield return CarryWalk(doorOut, 0.5f, 10f, 0.45f, 0.75f);
                yield return HandTo(W(1.25f, 1.02f, -0.15f), 0.8f);
                Info($"drag to the door: holding={grabber.IsHolding}, collar {van.transform.InverseTransformPoint(Collar(npc))} (van-local)");
                Release();
            }
            yield return new WaitForSeconds(0.5f);
            // climb in (crouched: the capsule crouches first, then fits under the 1.43 m roof) and take the collar again
            holdInputs = true; crouch = true;
            yield return new WaitForSeconds(0.35f);
            pawn.Teleport(W(0.70f, 0.56f, -0.15f), van.transform.eulerAngles.y + 90f);
            yield return new WaitForSeconds(0.3f);
            yield return new WaitForSeconds(0.4f); // keep Ctrl held while reaching over the sill
            grabbed = Grab(Collar(npc), npc);
            for (int attempt = 0; attempt < 2 && !grabbed; attempt++)
            {
                // lean over to another spot in the bay and try again
                yield return Shuffle(W(attempt == 0 ? 0.45f : 0.75f, 0.56f, attempt == 0 ? -0.6f : 0.25f), 0.4f);
                grabbed = Grab(Collar(npc), npc);
            }
            Info($"from inside: grab={grabbed} at {Vector3.Distance(pawn.ViewCamera.transform.position, Collar(npc)):0.00} m");
            if (grabbed)
            {
                Vector3 c0 = Collar(npc);
                yield return HandTo(new Vector3(c0.x, W(0f, 1.12f, 0f).y, c0.z), 0.5f);
                StartCoroutine(Shuffle(W(0.0f, 0.56f, -0.75f), 1.2f));
                yield return HandTo(W(0.54f, 1.12f, -0.12f), 1.2f);
                yield return HandTo(W(0.24f, 0.90f, -0.12f), 0.3f);
                StartCoroutine(Shuffle(W(-0.45f, 0.56f, -0.75f), 0.9f));
                yield return HandTo(W(-0.70f, 0.90f, -0.12f), 0.9f);
                yield return HandTo(W(-0.70f, 0.85f, -0.12f), 0.4f);
                Info($"load: still holding at the end = {grabber.IsHolding}");
                Release();
            }
            grabber.ScriptDriven = false;
            float end = Time.time + 5f;
            while (!npc.InCargo && Time.time < end) yield return null;
            Shot(shot + "b_loaded");
            pawn.Teleport(WG(2.4f, -0.7f), van.transform.eulerAngles.y - 90f);
            holdInputs = false; crouch = false;
            yield return new WaitForSeconds(0.3f);
            // a foot still in the doorway would stall the sliding door: push it in like a player would
            foreach (string foot in new[] { "LeftFoot", "RightFoot" })
            {
                Vector3 local = van.transform.InverseTransformPoint(Bone(npc, foot).position);
                if (local.x < 0.75f) continue;
                yield return WalkTo(WG(1.7f, local.z), 4f);
                if (Grab(Bone(npc, foot).position, npc))
                {
                    yield return HandTo(W(1.15f, 1.05f, -0.25f), 0.6f);
                    yield return HandTo(W(0.25f, 1.0f, -0.25f), 0.8f);
                    yield return HandTo(W(-0.1f, 0.85f, -0.25f), 0.5f);
                    Release();
                    Info($"pushed the {foot} into the bay");
                }
                grabber.ScriptDriven = false;
            }
            end = Time.time + 4f; // cargo needs EVERY limb below 0.25 m/s for a further 0.5 s after the feet are let go
            while (!npc.InCargo && Time.time < end) yield return null;
            Info($"load settled: collar {van.transform.InverseTransformPoint(Collar(npc))}, pelvis {van.transform.InverseTransformPoint(Pelvis(npc))}, cargo {npc.InCargo}");
            if (!npc.InCargo)
            {
                Check(false, "physical carry into the van completed without fallback placement");
                Warn("the scripted carry did not load him this run (fallback: laid in the bay)");
                PlaceInBay(npc, -0.9f);
                end = Time.time + 4f;
                while (!npc.InCargo && Time.time < end) yield return null;
            }
            else Line("PASS the scripted carry (drag to the door, collar from inside into the bay) loaded him through the sliding door");
        }

        /// <summary>In the bay (crouched): the collar to the door and over the sill; out, the collar again, dragged round
        /// to the shed, the upper body lifted onto the table, then the legs; let go over the pad (the bridge and the
        /// table's magnet snap take over).</summary>
        private IEnumerator CarryToTable(GreyboxNpc npc, string shot)
        {
            var table = d.Table.transform;
            if (!cargo.DoorOpen(0)) cargo.ToggleDoor(0);
            yield return new WaitForSeconds(0.8f);
            holdInputs = true; crouch = true;
            yield return new WaitForSeconds(0.35f);
            Vector3 collarLocal = van.transform.InverseTransformPoint(Collar(npc));
            pawn.Teleport(W(Mathf.Clamp(collarLocal.x + 0.8f, -0.3f, 0.7f), 0.56f, Mathf.Clamp(collarLocal.z - 0.7f, -1.9f, 0.2f)), van.transform.eulerAngles.y + 90f);
            yield return new WaitForSeconds(0.3f);
            yield return new WaitForSeconds(0.4f);
            bool grabbed = Grab(Collar(npc), npc);
            foreach (var lean in new[] { new Vector3(0.65f, 0.56f, -0.45f), new Vector3(0.25f, 0.56f, -1.45f), new Vector3(-0.55f, 0.56f, -0.5f) })
            {
                if (grabbed) break;
                yield return Shuffle(W(lean.x, lean.y, lean.z), 0.3f); yield return new WaitForSeconds(0.2f);
                grabbed = Grab(Collar(npc), npc);
            }
            if (!grabbed) Warn("LMB (scripted) missed him in the van"); else Line("PASS LMB grabs him in the van");
            if (grabbed)
            {
                yield return HandTo(W(collarLocal.x + 0.3f, 1.05f, collarLocal.z), 0.5f);
                StartCoroutine(Shuffle(W(0.65f, 0.56f, -0.85f), 0.9f));
                yield return HandTo(W(0.8f, 1.05f, -0.25f), 0.9f);
                yield return HandTo(W(1.35f, 1.0f, -0.25f), 0.6f);
                yield return HandTo(W(1.95f, 0.85f, -0.25f), 0.7f);
                Release();
            }
            yield return new WaitForSeconds(0.4f);
            // out of the van, the collar again, dragged out and round to the open (north) side of the table
            // Stay crouched, on the outside road: an above-van ground ray can choose its roof.
            pawn.Teleport(W(1.8f, 0.04f, -0.25f), van.transform.eulerAngles.y - 90f);
            yield return new WaitForSeconds(0.5f);
            grabbed = Grab(Collar(npc), npc);
            for (int attempt = 0; attempt < 3 && !grabbed; attempt++)
            {
                float z = Mathf.Clamp(van.transform.InverseTransformPoint(Collar(npc)).z, -0.8f, 0.35f);
                pawn.Teleport(W(1.65f + attempt * 0.15f, 0.04f, z), van.transform.eulerAngles.y - 90f);
                yield return new WaitForSeconds(0.3f);
                grabbed = Grab(Collar(npc), npc);
            }
            Info($"outside: grab={grabbed}");
            if (grabbed)
            {
                yield return CarryWalk(WG(3.3f, -0.25f), 0.75f, 6f, 0.45f, 0.8f);
                Shot(shot + "a_out_of_van");
                // shut the sliding door behind him (its open panel lies along the side, where the way to the shed goes)
                Release();
                yield return new WaitForSeconds(0.4f);
                if (cargo.DoorOpen(0)) cargo.ToggleDoor(0);
                yield return new WaitForSeconds(0.9f);
                yield return ApproachToward(npc, Ground(new Vector3(190.0f, 0f, 511.9f)));
                grabbed = Grab(Collar(npc), npc);
                Info($"after shutting the door: grab={grabbed}");
            }
            if (grabbed)
            {
                Vector3 north = table.position + new Vector3(0f, 0f, 1.0f);
                // past the van's rear and west into the shed's open side; a slipped grip is taken again
                var vanBounds = new Bounds(van.transform.position, Vector3.zero);
                foreach (var collider in van.GetComponentsInChildren<Collider>())
                    if (!collider.isTrigger) vanBounds.Encapsulate(collider.bounds);
                // Clear the WHOLE van by a body length before turning: the former 3.4 m waypoint cut its front corner.
                float clearZ = Mathf.Min(vanBounds.min.z - 1.8f, table.position.z + 2.8f);
                var route = new[] { Ground(new Vector3(vanBounds.max.x + 1.3f, 0f, clearZ)),
                                    Ground(new Vector3(table.position.x + 2.0f, 0f, clearZ)), Ground(north + new Vector3(0.6f, 0f, 0.3f)) };
                for (int w = 0; w < route.Length; w++)
                {
                    for (int attempt = 0; attempt < 3; attempt++)
                    {
                        yield return CarryWalk(route[w], 0.7f, 10f, 0.5f);
                        if (grabber.IsHolding) break;
                        Info($"regrab on the way to {route[w]}");
                        yield return ApproachToward(npc, route[w], 0.65f);
                        holdInputs = true; crouch = true;
                        yield return new WaitForSeconds(0.3f);
                        if (!Grab(Collar(npc), npc)) break;
                    }
                }
                Release();
                yield return new WaitForSeconds(0.5f);
                // round to his far side, so he lies between the player and the table; then push the collar up over the
                // table's edge onto the pad (the edge works like the van's sill) and let go: the magnet does the rest
                Vector3 c1 = Collar(npc);
                Vector3 away = c1 - table.position; away.y = 0f;
                yield return WalkTo(Ground(c1 + away.normalized * 1.05f), 6f);
                if (Grab(Collar(npc), npc))
                {
                    yield return HandTo(Collar(npc) + Vector3.up * 0.3f, 0.4f);
                    // Step up to the long side before reaching over the pad: the real wheel/hand range is limited.
                    yield return CarryWalk(Ground(table.position + new Vector3(0f, 0f, 1.05f)), 0.9f, 8f, 0.4f, 0.7f);
                    yield return HandTo(table.position + Vector3.up * 1.05f + new Vector3(0f, 0f, 0.2f), 1.6f);
                    yield return new WaitForSeconds(0.6f);
                    Info($"table lift: collar local {table.InverseTransformPoint(Collar(npc))}, hand local {table.InverseTransformPoint(grabber.PointHoldTarget)}, player {pawn.Position}");
                    Shot(shot + "a_onto_table");
                    Info($"table: still holding = {grabber.IsHolding}");
                    Release();
                }
            }
            yield return new WaitForSeconds(0.6f);
            // the legs
            if (!d.Bridge.Busy && !d.Table.HasPatient && npc != null)
            {
                // step over to his legs first (from the open side of the table)
                Vector3 knee = Bone(npc, "LeftLeg").position;
                Vector3 side = pawn.Position - knee; side.y = 0f;
                if (side.sqrMagnitude < 0.01f) side = Vector3.forward;
                yield return WalkTo(Ground(knee + side.normalized * 0.75f), 6f);
                holdInputs = true; crouch = true;
                yield return new WaitForSeconds(0.3f);
                knee = Bone(npc, "LeftLeg").position;
                if (Grab(knee, npc))
                {
                    yield return HandTo(knee + Vector3.up * 0.6f, 0.5f);
                    yield return HandTo(table.position + Vector3.up * 1.05f + new Vector3(-0.55f, 0f, 0f), 0.8f);
                    yield return HandTo(table.position + Vector3.up * 0.85f + new Vector3(-0.55f, 0f, 0f), 0.4f);
                    Release();
                }
            }
            grabber.ScriptDriven = false;
            float end = Time.time + 3f;
            while (!d.Bridge.Busy && !d.Table.HasPatient && Time.time < end) yield return null;
            if (!d.Bridge.Busy && !d.Table.HasPatient && npc != null)
            {
                var body = npc.PhysicalBody;
                if (body != null && body.Active)
                {
                    Vector3 l = table.InverseTransformPoint(body.CenterOfMass + table.up * 0.1f);
                    Info($"on the table? COM table-local {l} (pad ±{d.Table.Tuning.padHalfExtents.x}/±{d.Table.Tuning.padHalfExtents.z}, top {d.Table.Tuning.padTop}), held {body.HolderCount}, state {npc.State}");
                }
                Check(false, "physical carry onto the table completed without fallback placement");
                Warn("the scripted carry did not get him onto the table this run (fallback: laid on the pad)");
                if (npc.Ragdoll != null && npc.Ragdoll.Active) npc.Ragdoll.PlaceLying(table.position + Vector3.up * 0.7f, table.forward, true);
            }
            else Line("PASS the scripted carry (out of the bay, dragged round, collar over the edge) got him onto the table pad");
            holdInputs = false; crouch = false;
        }

#endif
    }
}
