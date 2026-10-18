using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>v04 scenarios of the dev input driver: ragdoll carry and snap, the one belly incision, kidney cords from
    /// below, the liver loop (natural circular mouse movement either way round), the top camera framing and the tray.</summary>
    public sealed partial class OperationNetworkProbe
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private static string FreshEvidenceFolder(string requested)
        {
            string candidate = requested;
            for (int revision = 2; System.IO.Directory.Exists(candidate); revision++)
                candidate = requested + "_" + revision.ToString("D2");
            return candidate;
        }

        /// <summary>Extra points over a strap's visible top face, for when its centre lies under something else on screen
        /// (a person moves along the strap until it lights up).</summary>
        private List<Vector3> StrapCandidates(Bounds b)
        {
            var list = new List<Vector3>();
            for (int i = 0; i <= 8; i++)
                for (int j = 0; j <= 2; j++)
                {
                    var p = new Vector3(Mathf.Lerp(b.min.x, b.max.x, i / 8f), b.max.y, Mathf.Lerp(b.min.z, b.max.z, 0.25f + j * 0.25f));
                    list.Add(p);
                }
            list.Sort((a, c) => Vector3.Distance(a, b.center).CompareTo(Vector3.Distance(c, b.center)));
            return list;
        }

        /// <summary>One stroke on a v04 guide with the real mouse. The belly line: a straight drag. The liver loop: a
        /// human circle (a slightly wobbly radius, constant speed, past the seam at the end) from the start dot in
        /// 'direction', up to 'until' of the loop. 'sloppy' keeps the blade ~2.5 cm off the line (still on the band).</summary>
        private IEnumerator CutShared(int guide, bool sloppy = false, bool capture = false, int direction = 1, float until = 1f)
        {
            if (view.LocalSlot != ToolSlot.Scalpel) yield return Select(Key.Digit4, ToolSlot.Scalpel);
            if (table.GuideProgress(guide) >= 1f) yield break;
            var abdomen = table.Abdomen;
            float begin = table.GuideProgress(guide);
            bool loop = guide != OperationAbdomenGeometry.ZoneGuide;
            int dir = loop && begin > 0f ? abdomen.Direction(guide) : direction;
            // An awake (strapped) patient struggles and the dot moves with him: look again, like a person would.
            for (int attempt = 0; attempt < 4; attempt++)
            {
                Vector3 n = table.OrganNormal(guide);
                Vector3 dot = abdomen.ResumePoint(guide);
                yield return AimAt(t => t.kind == TargetKind.Incision && t.index == guide,
                    new[] { dot + n * 0.011f, dot, table.SitePoint(guide, OperationAbdomenGeometry.Point(table.Tuning, guide, begin + 0.01f, dir)) },
                    "shared guide " + guide, attempt == 0 ? 0.25f : 0.08f);
                if (aimed) break;
            }
            if (!aimed) { Check(false, "shared guide " + guide + " start dot is under the cursor"); yield break; }
            if (capture) Shot(loop ? (begin > 0f ? "v04_12b_liver_loop_resume" : "v04_12_liver_loop_start") : "v04_06_belly_start");
            // Keep the blade on the moving resume dot through the real input/network tick before advancing.
            mPos = Scr(abdomen.ResumePoint(guide)); PushMouse(); yield return Frames(2);
            yield return Button(true);
            float startUntil = Time.time + 0.12f;
            while (Time.time < startUntil) { mPos = Scr(abdomen.ResumePoint(guide)); PushMouse(); yield return null; }
            float end = loop ? Mathf.Min(1.04f, until + (until >= 1f ? 0.04f : 0f)) : 1.03f;
            float r = Mathf.Min(table.Tuning.liverLoopRadius.x, table.Tuning.liverLoopRadius.y);
            float seconds = loop ? 1.5f * (end - begin) : 0.95f * (end - begin);
            float t0 = Time.time; bool shot = false;
            while (true)
            {
                float k = Mathf.Clamp01((Time.time - t0) / seconds);
                float along = Mathf.Lerp(begin, end, k);
                Vector3 local = OperationAbdomenGeometry.Point(table.Tuning, guide, along, dir);
                if (loop)
                {
                    float wobble = 1f + (sloppy ? 0.025f / r : 0f) + 0.09f * Mathf.Sin(along * 23f) + 0.05f * Mathf.Sin(along * 7f + 1f);
                    Vector3 center = table.Tuning.anatomicalLayout ? OperationAnatomyV02.LiverLoopCenter : Vector3.zero;
                    local = center + new Vector3((local.x - center.x) * wobble, (local.y - center.y) * wobble, local.z - center.z);
                }
                else local.x += sloppy ? 0.032f : 0.004f * Mathf.Sin(along * 19f);
                mPos = Scr(table.SitePoint(guide, local)); PushMouse();
                if (capture && !shot && k >= 0.5f) { Shot(loop ? "v04_13_liver_loop_cut" : "v04_07_big_cut"); shot = true; }
                if (k >= 1f) break;
                yield return null;
            }
            yield return new WaitForSeconds(0.2f);
            yield return Button(false);
            yield return Settle();
            if (loop && until < 1f)
            {
                yield return new WaitForSeconds(0.1f);
                float p = table.GuideProgress(guide);
                Check(p > until - 0.08f && p < until + 0.05f && !S.organs[2].Released, $"liver loop stopped where the mouse stopped ({p:F2})");
                yield break;
            }
            yield return WaitFor(() => table.GuideProgress(guide) >= 1f, 2f, "guide " + guide + " completed with real mouse input");
            if (!loop)
            {
                Check(S.zoneOpened && S.organs[0].Opened && S.organs[1].Opened && S.organs[2].Opened,
                    "one belly cut exposes all three independent organs");
                yield return new WaitForSeconds(0.4f);
                if (capture) Shot("v04_08_one_opening_three_organs");
            }
            else
            {
                Check(S.organs[2].Released && S.organs[2].CordsLeft == 0, "the guided loop released the liver's three original connections");
                if (capture) { yield return new WaitForSeconds(0.3f); Shot("v04_13b_liver_free"); }
            }
        }

        private IEnumerator V04WatchCarry()
        {
            OperationPatientRagdoll adapter = null;
            bool seenHeld = false, seenFlight = false, animatedOff = false;
            int maxBodies = 0;
            float angle = 0f; Quaternion first = Quaternion.identity; bool sampled = false, captured = false;
            float end = Time.time + 30f;
            while (Time.time < end && (S == null || !S.onTable))
            {
                if (table.PatientObject != null) adapter = table.PatientObject.GetComponent<OperationPatientRagdoll>();
                if (adapter != null && adapter.Active)
                {
                    bool held = table.PatientBody.HasHolder;
                    seenHeld |= held; seenFlight |= !held;
                    maxBodies = Mathf.Max(maxBodies, adapter.DynamicBodies);
                    animatedOff |= !table.PatientRig.Animator.enabled;
                    var rotation = Quaternion.Inverse(table.PatientBody.transform.rotation) * adapter.Bone(3).rotation;
                    if (!sampled) { first = rotation; sampled = true; }
                    angle = Mathf.Max(angle, Quaternion.Angle(first, rotation));
                    if (!captured && held && angle > 10f && adapter.Bone(0).position.y > table.transform.position.y + 0.85f)
                    { Shot("v04_02_ragdoll_carry"); Overview("v04_02a_ragdoll_carry_side", new Vector3(-3.4f, 2.1f, 2.2f), new Vector3(-0.7f, 0.8f, -0.1f)); captured = true; }
                }
                yield return null;
            }
            Check(seenHeld && animatedOff && maxBodies == 11,
                "carried patient uses the existing 11 dynamic ragdoll bodies; Animator yields ownership");
            Check(angle > 5f, "ragdoll limbs move independently of the grab handle (" + angle.ToString("F1") + " degrees)");
            Line("RAGDOLL flight observed=" + seenFlight);
            // The hand-back: shots while the body morphs into the table pose and slides onto PatientRest.
            float t0 = Time.time;
            while (S != null && S.onTable && !S.aligned && Time.time - t0 < 2f)
            {
                if (Time.time - t0 > 0.15f && Time.time - t0 < 0.3f && !snapShot) { OverviewShot("v04_02b_snap_morph"); snapShot = true; }
                yield return null;
            }
        }
        private bool snapShot;
        private void OverviewShot(string name) => Overview(name, new Vector3(-1.6f, 1.9f, -0.9f), new Vector3(0f, 0.7f, 0.15f));

        private bool homeKnown;
        private Pose tableHome;
        /// <summary>The v04 scenarios start from the scene's own table spot (the rotated scenario moves the gurney on
        /// purpose, and the PlayMode suite shares one session).</summary>
        private IEnumerator TableHome()
        {
            if (view.Active) { yield return Tap(Key.Escape); yield return new WaitForSeconds(table.Tuning.cameraBlendSeconds + 0.1f); }
            var rb = table.GetComponent<Rigidbody>();
            if (rb != null && homeKnown)
            {
                rb.position = tableHome.position; rb.rotation = tableHome.rotation;
                table.transform.SetPositionAndRotation(tableHome.position, tableHome.rotation);
                rb.linearVelocity = Vector3.zero; rb.angularVelocity = Vector3.zero;
                Teleport(TableFoot(new Vector3(-2.4f, 0f, 0.9f))); // clear of the fresh patient's floor collider before F10
                yield return new WaitForSeconds(0.3f);
            }
        }

        private IEnumerator V04Loop()
        {
            yield return TableHome();
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            Check(table.Tuning.sharedAbdomen, "approved v02 scene has the v04 extension enabled");
            snapShot = false;
            StartCoroutine(V04WatchCarry());
            Vector3 gurney = table.transform.position;
            yield return CarryPatientOntoTable();
            yield return new WaitForSeconds(0.6f);
            Check(Vector3.Distance(table.transform.position, gurney) < 0.02f,
                $"the gurney stays put while the dangling patient is carried onto it ({Vector3.Distance(table.transform.position, gurney):F3} m)");
            OverviewShot("v04_02c_snapped");
            var adapter = table.PatientObject.GetComponent<OperationPatientRagdoll>();
            Check(adapter != null && !adapter.Active && adapter.DynamicBodies == 0 && table.PatientRig.Animator.enabled,
                "magnet snap returns ownership to the existing table Animator");
            Check(Vector3.Distance(table.PatientBody.transform.position, table.RestPose.position) < 0.015f &&
                Quaternion.Angle(table.PatientBody.transform.rotation, table.RestPose.rotation) < 0.5f,
                "ragdoll snaps into the exact approved PatientRest pose");
            yield return EnterTable(); Shot("v04_03a_prep_view");
            Check(Vector3.Dot(Cam.transform.forward, -table.transform.up) > 0.9999f, "real table camera is straight top-down");
            // PREP (default on E): the whole patient, all five straps and the tray, clickable without zooming.
            Check(view.CameraMode == TableCamera.Prep, "E opens the PREP view");
            for (int i = 0; i < OperationStraps.Count(table.Tuning); i++) Check(StrapOnScreen(i), "PREP: strap " + i + " (" + OperationText.Straps[i] + ") on screen");
            Check(InFrame(table.PatientRig.HeadTop.position, 0.02f) && InFrame(table.PatientRig.transform.position, 0.02f), "PREP: the whole patient is on screen");
            for (int i = 0; i < 3; i++) Check(InFrame(table.OrganSlotPose(i).position, 0.02f), "PREP: tray organ slot " + i + " on screen");
            Check(InFrame(table.BagPose(0).position, 0.02f) && InFrame(table.DockPose(table.ToolOf(ToolSlot.Anesthesia)).position, 0.02f),
                "PREP: bags and syringes on the tray are on screen");
            yield return Straps(true); Shot("v04_04_straps");
            Check(view.CameraMode == TableCamera.Prep, "straps were clicked in the PREP view");
            Check(OperationStraps.AllClosed(S, table.Tuning), "all straps closed with real clicks");
            yield return Inject(2f, "v04 main"); Shot("v04_05_anesthesia");
            Check(S.Sleeping && S.alive, "patient asleep with the existing dose rules");
            Check(view.CameraMode == TableCamera.Prep, "anesthesia given in the PREP view");
            // Taking the scalpel opens the OPERATION view (the approved close v04 framing).
            yield return Select(Key.Digit4, ToolSlot.Scalpel);
            yield return WaitFor(() => view.CameraMode == TableCamera.Operation, 1f, "taking the scalpel opens the OPERATION view");
            yield return new WaitForSeconds(0.5f);
            Shot("v04_03_snapped_top_camera");
            float headY = Cam.WorldToViewportPoint(table.PatientRig.HeadTop.position).y;
            var zonePose = table.Abdomen.ZonePose;
            float bellyY = Cam.WorldToViewportPoint(zonePose.position + zonePose.rotation * new Vector3(0f, -table.Tuning.abdomenHalfSize.y, 0f)).y;
            float guideEndY = Cam.WorldToViewportPoint(table.GuidePosition(OperationAbdomenGeometry.ZoneGuide, 1f)).y;
            Check(headY > 0.88f && headY < 0.99f && bellyY > 0.09f && bellyY < 0.2f && guideEndY > bellyY,
                $"close framing: head top near the top edge ({headY:F2}), opening ends just above the hotbar ({bellyY:F2}, guide end {guideEndY:F2})");
            for (int i = 0; i < 3; i++)
                Check(InFrame(table.OrganSlotPose(i).position, 0.03f), "tray organ slot " + i + " is on screen in the close framing");
            Check(InFrame(table.BagPose(0).position, 0.03f) && InFrame(table.DockPose(table.ToolOf(ToolSlot.Scalpel)).position, 0.03f),
                "bags and tools on the tray are on screen in the close framing");
            // Tab toggles both ways with a short blend.
            yield return Tap(Key.Tab); yield return new WaitForSeconds(0.45f);
            Check(view.CameraMode == TableCamera.Prep && Vector3.Distance(Cam.transform.position, view.ViewPose.position) < 0.03f, "Tab: OPERATION -> PREP");
            Shot("v04_04a_tab_prep");
            yield return Tap(Key.Tab); yield return new WaitForSeconds(0.45f);
            Check(view.CameraMode == TableCamera.Operation && Mathf.Abs(view.Zoom) < 0.02f &&
                  Vector3.Distance(Cam.transform.position, table.CameraPose.position) < 0.03f, "Tab: PREP -> OPERATION (the close framing)");
            // The wheel is only a fine adjustment now: out a little, never the wide view; back in stops at the close framing.
            for (int i = 0; i < 8; i++) yield return Scroll(-120f);
            yield return new WaitForSeconds(0.5f);
            Check(view.Zoom > -0.32f && view.Zoom < -0.1f && view.CameraMode == TableCamera.Operation, $"wheel out is a fine adjustment only ({view.Zoom:F2})");
            for (int i = 0; i < 2; i++) yield return Scroll(120f);
            yield return new WaitForSeconds(0.5f);
            Check(Mathf.Abs(view.Zoom) < 0.02f && Vector3.Distance(Cam.transform.position, table.CameraPose.position) < 0.03f,
                $"wheel in returns to the close framing ({view.Zoom:F2})");
            yield return CutShared(OperationAbdomenGeometry.ZoneGuide, false, true);
            int visible = 0;
            foreach (var t in table.PatientObject.GetComponentsInChildren<Transform>(true))
                if (t.name == "Organ" && t.gameObject.activeInHierarchy) visible++;
            Check(visible == 3, "all three organ models are visible in the one prepared opening");
            for (int i = 0; i < 3; i++) Check(InFrame(table.OrganPosition(i), 0.08f), "organ " + i + " is well inside the close framing");
            for (int i = 0; i < 2; i++)
            {
                OperationGeometry.Cord(table.Tuning, i, 0, out var attach, out var rim);
                if (table.Tuning.anatomicalLayout)
                {
                    OperationAnatomyV02.Cord(table.Tuning, i, 0, out var expectedAttach, out var expectedEnd);
                    OperationGeometry.Cord(table.Tuning, i, 1, out var veinAttach, out var veinEnd);
                    Check(Vector3.Distance(attach, expectedAttach) < 0.001f && Vector3.Distance(rim, expectedEnd) < 0.001f &&
                        Vector3.Distance((attach + rim) * 0.5f, (veinAttach + veinEnd) * 0.5f) > 0.015f && table.Tuning.cordHitRadius <= 0.0101f,
                        "kidney " + i + " approved artery/vein endpoints and separate small snip targets");
                }
                else Check(attach.z < table.Tuning.organLift && rim.z < table.Tuning.organLift && rim.y < -table.Tuning.organHalfSize[i].y,
                    "kidney " + i + " cords originate underneath and expose a lower snip point");
                yield return Snip(i, true); Shot("v04_09_kidney_" + i + "_cords_cut");
                yield return Pull(i, 0.9f, true); Shot("v04_10_kidney_" + i + "_on_tray");
            }
            yield return CutShared(2, false, true);
            yield return Pull(2, 0.9f, true); Shot("v04_14_liver_on_tray");
            var ids = new HashSet<string>(); foreach (var item in table.ServerItems) if (item != null) ids.Add(item.Identity);
            Check(S.extracted == 3 && table.ServerItems.Count == 3 && ids.Count == 3, $"full new input loop produces each organ exactly once ({table.ServerItems.Count} items, {ids.Count} ids)");
            for (int i = 0; i < 3; i++)
            {
                Check(S.organs[i].damage == 0, "neat new flow preserves organ " + i + " quality");
                Check(S.organs[i].rollCompleted || !S.alive, "organ " + i + " death roll recorded (chance " + S.organs[i].deathChance.ToString("F2") + ")");
            }
            LogOrgans();
            yield return MoveTo(Scr(table.OrganSlotPose(1).position + table.transform.up * 0.2f), 0.3f);
            yield return new WaitForSeconds(0.3f);
            Shot("v04_15_tray_complete");
            yield return Tap(Key.Escape);
        }

        private bool StrapOnScreen(int strap)
        {
            foreach (var tag in table.GetComponentsInChildren<OperationTargetTag>())
            {
                if (tag.kind != TargetKind.Strap || tag.index != strap) continue;
                var b = tag.GetComponent<Collider>().bounds;
                foreach (var p in StrapCandidates(b))
                {
                    var v = Cam.WorldToViewportPoint(p);
                    // On screen and not under the hotbar (bottom-centre).
                    if (v.z > 0f && v.x > 0.02f && v.x < 0.98f && v.y > 0.02f && v.y < 0.98f && !(v.y < 0.13f && v.x > 0.37f && v.x < 0.63f)) return true;
                }
            }
            return false;
        }

        private bool InFrame(Vector3 world, float margin)
        {
            var p = Cam.WorldToViewportPoint(world);
            return p.z > 0f && p.x >= margin && p.x <= 1f - margin && p.y >= margin && p.y <= 1f - margin;
        }

        private IEnumerator V04GuideEdges()
        {
            yield return TableHome();
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.7f);
            yield return Tap(Key.F9); yield return new WaitForSeconds(0.4f);
            yield return EnterTable(); yield return Straps(false);
            yield return Select(Key.Digit4, ToolSlot.Scalpel);
            // 1) the belly line refuses a start at the wrong end
            yield return MoveTo(Scr(table.GuidePosition(3, 0.9f)), 0.2f);
            yield return Hold(0.3f);
            Check(S.zoneCut == 0f && !S.zoneOpened, "a shared cut starting at the wrong end is refused");
            // 2) half a cut, release, leave the table, come back: the one cut is still half done
            yield return MoveTo(Scr(table.GuidePosition(3, 0f)), 0.2f);
            yield return Button(true);
            for (int i = 1; i <= 25; i++)
            { mPos = Scr(table.GuidePosition(3, i / 50f)); PushMouse(); yield return new WaitForSeconds(0.025f); }
            yield return Button(false);
            yield return new WaitForSeconds(0.3f); // let the real release intent reach the authoritative tick
            float progress = S.zoneCut;
            Check(progress > 0.35f && progress < 0.7f && !S.zoneOpened, $"releasing midway keeps the shared cut progress ({progress:F2})");
            yield return Tap(Key.E); yield return new WaitForSeconds(0.4f);
            Check(!view.Active && Mathf.Abs(S.zoneCut - progress) < 0.001f, $"leaving the table keeps the one cut ({S.zoneCut:F2})");
            yield return EnterTable();
            Check(Mathf.Abs(S.zoneCut - progress) < 0.001f, $"leaving and re-entering preserves the one cut ({progress:F2} -> {S.zoneCut:F2})");
            yield return CutShared(3, false, true);
            Check(S.organs[0].damage == 0 && S.organs[1].damage == 0 && S.organs[2].damage == 0,
                "a resumed neat incision does not penalize any organ");
            // 3) liver loop the other way round, released at 45 %, resumed from the moved start dot
            yield return CutShared(2, false, false, -1, 0.45f);
            Check(S.organs[2].connectionDirection == -1, "the loop can be cut the other way round (clockwise on screen)");
            Check(S.organs[2].connections[0] >= 1f && S.organs[2].CordsLeft == 2, "a third of the loop releases the first liver connection");
            Shot("v04_12c_liver_loop_paused");
            yield return CutShared(2, false, true);
            Check(S.organs[2].damage == 0, "a resumed neat loop costs nothing");
            // 4) the hands are still needed: the freed liver comes out by the existing pull
            yield return Pull(2, 0.9f, false);
            Check(S.organs[2].removed && S.extracted == 1, "the freed liver is pulled out once");
            // 5) a sloppy loop on a fresh patient: the liver alone loses one grade
            yield return Tap(Key.Escape); yield return new WaitForSeconds(0.3f);
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.7f);
            yield return Tap(Key.F9); yield return new WaitForSeconds(0.4f);
            yield return EnterTable(); yield return Straps(false);
            yield return CutShared(3, false, false);
            yield return CutShared(2, true, false);
            Check(S.organs[2].Released && S.organs[2].damage == table.Tuning.sloppyLoss && S.organs[0].damage == 0 && S.organs[1].damage == 0,
                $"a sloppy loop (2.5 cm off the line) frees the liver at -1 (damage {S.organs[2].damage})");
            // 6) a deliberate scalpel press on the liver itself is still a direct cut (-2)
            int before = S.organs[2].damage;
            yield return Select(Key.Digit4, ToolSlot.Scalpel);
            yield return AimAt(t => t.kind == TargetKind.Organ && t.index == 2, Around(table.OrganPosition(2), table.transform.forward, table.transform.right, 0.008f), "liver body (direct cut)");
            if (aimed) { yield return Click(); yield return new WaitForSeconds(0.3f); }
            Check(aimed && S.organs[2].directCuts == 1 && S.organs[2].damage == before + table.Tuning.directCutLoss,
                $"a scalpel click on the liver costs {table.Tuning.directCutLoss} (damage {before} -> {S.organs[2].damage})");
            yield return Tap(Key.Escape);
        }

        private IEnumerator V04RemoteCarry()
        {
            bool saw = false; int samples = 0; float end = Time.time + 50f; float lastAt = -1f; bool shot = false;
            OperationPatientRagdoll adapter = null;
            while (Time.time < end && S != null && !S.onTable)
            {
                adapter = table.PatientObject != null ? table.PatientObject.GetComponent<OperationPatientRagdoll>() : null;
                if (adapter != null && adapter.Active)
                {
                    if (!saw) { Check(adapter.DynamicBodies == 0 && !table.PatientRig.Animator.enabled,
                        "client observes the server ragdoll with zero locally simulated bodies"); saw = true; }
                    if (adapter.PoseReceivedAt != lastAt) { samples++; lastAt = adapter.PoseReceivedAt; }
                    if (!shot && samples > 12 && adapter.Bone(0).position.y > table.transform.position.y + 0.6f)
                    { Overview("n00_client_sees_ragdoll_carry", new Vector3(-3.4f, 2.1f, 2.2f), new Vector3(-0.7f, 0.8f, -0.1f)); shot = true; }
                }
                yield return null;
            }
            Check(saw && samples >= 3, $"client received live ragdoll bone snapshots during the host's real-input carry ({samples})");
            float t0 = Time.time;
            while (adapter != null && (adapter.Active || adapter.Blending) && Time.time - t0 < 3f) yield return null;
            Check(saw && adapter != null && !adapter.Active && table.PatientRig.Animator.enabled, "client hands the body back to the table Animator at the snap");
        }

        private IEnumerator V04Throw()
        {
            yield return TableHome();
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            var body = table.PatientBody;
            var adapter = body.GetComponent<OperationPatientRagdoll>();
            Vector3 start = body.transform.position;
            Vector3 away = Vector3.ProjectOnPlane(start - table.transform.position, Vector3.up).normalized;
            Teleport(start + away * 1.2f + Vector3.up * 0.02f); yield return Frames(3);
            LookAt(start + Vector3.up * 0.15f); yield return Frames(3);
            yield return Button(true); yield return new WaitForSeconds(0.4f);
            Check(body.HasHolder && adapter.Active && adapter.DynamicBodies == 11, "physical LMB grab activates all 11 ragdoll bodies");
            LookAt(start + Vector3.up * 1.6f); yield return new WaitForSeconds(0.8f);
            LookAt(start + table.transform.forward * 0.5f + Vector3.up * 1.4f); yield return new WaitForSeconds(0.12f);
            yield return Button(false);
            yield return new WaitForSeconds(0.08f);
            Check(!body.HasHolder && adapter.Active && adapter.DynamicBodies == 11 && !table.PatientRig.Animator.enabled,
                "released/thrown off the table: server physics keeps the ragdoll active");
            Shot("v04_throw_01_flight");
            yield return new WaitForSeconds(3f);
            Check(!S.onTable && adapter.Active, "off-table ragdoll stays at rest without snapping to a distant table");
            bool finite = true;
            for (int i = 0; i < adapter.BoneCount; i++)
            { var p = adapter.Bone(i).position; finite &= OperationRules.Finite(p.x) && OperationRules.Finite(p.y) && OperationRules.Finite(p.z); }
            Check(finite, "ragdoll bones remain finite after the throw and landing");
            yield return new WaitForSeconds(1f);
            int sent = adapter.PosesSent; Vector3 gurney0 = table.transform.position, pelvis0 = adapter.PlacementPoint;
            yield return new WaitForSeconds(2f);
            Line($"INFO in those 2 s the gurney moved {(table.transform.position - gurney0).magnitude * 1000f:F1} mm, the body's centre {(adapter.PlacementPoint - pelvis0).magnitude * 1000f:F1} mm");
            Check(adapter.PosesSent - sent <= 6, $"a resting ragdoll sends a slow heartbeat, not the 20 Hz stream ({adapter.PosesSent - sent} poses in 2 s)");
            Shot("v04_throw_02_landed");
            Vector3 center = adapter.PlacementPoint;
            Teleport(new Vector3(center.x, 0.02f, center.z) + away * 1.15f); yield return Frames(3);
            bool found = false;
            for (int i = 0; i < adapter.BoneCount && !found; i++)
            {
                LookAt(adapter.Bone(i).position); yield return Frames(3);
                if (Physics.Raycast(Cam.transform.position, Cam.transform.forward, out var hit, 3f, ~0, QueryTriggerInteraction.Ignore))
                    found = hit.rigidbody != null && hit.rigidbody.GetComponentInParent<OnlyVolunteers.Network.NetworkPhysicsBody>() == body;
            }
            Check(found, "real first-person ray can target a resting ragdoll bone");
            if (found)
            {
                yield return Button(true); yield return new WaitForSeconds(0.4f);
                Check(body.HasHolder, "resting ragdoll can be grabbed again through the existing network grabber");
                yield return Button(false);
            }
        }
#endif
    }
}
