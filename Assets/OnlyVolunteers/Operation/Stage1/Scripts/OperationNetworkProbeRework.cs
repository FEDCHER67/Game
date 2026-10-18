using System.Collections;
using System.Collections.Generic;
using OnlyVolunteers.Capture;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Claude rework of G35 (Fedya's 2026-10-18 build: "the straps don't work at all"). Real virtual
    /// Mouse/Keyboard in the real PREP view, as a player: every strap toggles by a click on its band and on its buckle,
    /// with every tool, independently of the other four; the arm strap cuts the hand zip-tie, the leg strap the foot tie;
    /// closed straps hold a struggling patient. It also asserts the cause of the build failure: every strap hit target
    /// (and the v02 opening mask) must use a READABLE mesh, because a runtime MeshCollider on a non-readable FBX mesh has
    /// no collision data in a player (it only works in the Editor).</summary>
    public sealed partial class OperationNetworkProbe
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private enum StrapPart { Band, Buckle }

        /// <summary>Aims the real cursor at the band (near the hinge) or the buckle (the far end) of one strap.</summary>
        private IEnumerator ClAimStrap(int index, StrapPart part)
        {
            var points = new List<Vector3>();
            var targets = table.GetComponent<OperationStrapTargets>();
            Vector3 hinge = table.StrapTransform(index) != null ? table.StrapTransform(index).position : table.transform.position;
            if (targets != null)
                foreach (var collider in targets.Targets(index))
                {
                    if (collider == null) continue;
                    var mesh = collider.sharedMesh;
                    if (mesh != null && mesh.isReadable)
                    {
                        var v = mesh.vertices; var t = mesh.triangles; var tri = new List<(Vector3 p, float d)>();
                        for (int k = 0; k + 2 < t.Length; k += 3)
                        {
                            var p = collider.transform.TransformPoint((v[t[k]] + v[t[k + 1]] + v[t[k + 2]]) / 3f);
                            tri.Add((p, Vector3.Distance(p, hinge)));
                        }
                        tri.Sort((a, b) => a.d.CompareTo(b.d));
                        int n = tri.Count;
                        int from = part == StrapPart.Band ? n / 6 : n * 4 / 5, to = part == StrapPart.Band ? n / 2 : n;
                        for (int k = from; k < to; k += Mathf.Max(1, (to - from) / 14)) points.Add(tri[k].p);
                    }
                    else points.AddRange(StrapCandidates(collider.bounds)); // a non-readable mesh: only its bounds are known
                }
            var renderer = table.StrapTransform(index) != null ? table.StrapTransform(index).GetComponentInChildren<Renderer>() : null;
            if (points.Count == 0 && renderer != null) points.AddRange(StrapCandidates(renderer.bounds));
            yield return AimAt(t => t.kind == TargetKind.Strap && t.index == index, points, "strap " + index + " " + part);
        }

        private bool OnlyToggled(bool[] before, int index)
        {
            if (S.restraints[index] == before[index]) return false;
            for (int j = 0; j < 5; j++) if (j != index && S.restraints[j] != before[j]) return false;
            return true;
        }

        private IEnumerator ClStraps()
        {
            var director = CaptureDirector.Instance;
            if (!table.HasPatient && !table.AdmissionMode)
            {
                yield return TableHome(); yield return Tap(Key.F10); yield return new WaitForSeconds(0.6f);
                yield return Tap(Key.F9); yield return new WaitForSeconds(0.8f);
            }
            yield return WaitFor(() => table.HasPatient && S != null && S.onTable && S.aligned, 8f, "a patient lies aligned on the table");
            if (!table.HasPatient || S == null) yield break;
            // Fixture: asleep, so he cannot wriggle off while every strap is clicked open and shut; the struggle is below.
            S.sleepRemaining = Mathf.Max(S.sleepRemaining, 120f);
            var facts = director != null ? director.Bridge.PatientFacts : null;
            if (facts != null) Check(facts.restraints.hands && facts.restraints.feet, "fixture: hands and feet are zip-tied when he lies on the table");
            yield return EnterTable(); Shot("cl_straps_01_prep");

            // ---- the build failure itself ----
            var targets = table.GetComponent<OperationStrapTargets>();
            for (int i = 0; i < 5; i++)
            {
                var list = targets != null ? targets.Targets(i) : null;
                bool safe = list != null && list.Count > 0;
                if (safe) foreach (var c in list) safe &= c != null && c.enabled && OperationQueryMeshes.PlayerSafe(c);
                Check(safe, "strap " + i + " (" + OperationText.Straps[i] + "): its hit target uses a READABLE mesh (a non-readable one is empty in a player build)");
                bool same = safe;
                if (safe)
                    foreach (var c in list)
                    {
                        var visible = c.transform.parent != null ? c.transform.parent.GetComponent<MeshFilter>() : null;
                        same &= visible != null && visible.sharedMesh != null && visible.sharedMesh.vertexCount == c.sharedMesh.vertexCount &&
                                Vector3.Distance(visible.sharedMesh.bounds.size, c.sharedMesh.bounds.size) < 0.001f;
                    }
                Check(same, "strap " + i + ": the hit mesh has the visible strap's own geometry (band + buckle)");
            }
            if (table.Tuning.anatomicalLayout)
            {
                var openings = table.PatientObject != null ? table.PatientObject.GetComponentsInChildren<OperationOpeningV02>(true) : new OperationOpeningV02[0];
                bool maskSafe = openings.Length > 0;
                foreach (var o in openings) maskSafe &= OperationQueryMeshes.PlayerSafe(o.Mask);
                Check(maskSafe, "the v02 opening mask collider uses a readable mesh too");
            }

            // ---- every strap: band click and buckle click, a different tool each, independent of the others ----
            var slots = new[] { ToolSlot.Hands, ToolSlot.Anesthesia, ToolSlot.Blood, ToolSlot.Scalpel };
            var hotkeys = new[] { Key.Digit1, Key.Digit2, Key.Digit3, Key.Digit4 };
            for (int i = 0; i < 5; i++)
            {
                int tool = i % 4;
                yield return Select(hotkeys[tool], slots[tool]);
                if (view.CameraMode != TableCamera.Prep) { yield return Tap(Key.Tab); yield return new WaitForSeconds(0.5f); }
                foreach (var part in new[] { StrapPart.Band, StrapPart.Buckle })
                {
                    var before = (bool[])S.restraints.Clone();
                    yield return ClAimStrap(i, part);
                    if (!Check(aimed, slots[tool] + ": the real cursor finds the " + part + " of strap " + i + " (" + OperationText.Straps[i] + ")")) continue;
                    if (i == 1 && part == StrapPart.Band) Shot("cl_straps_02_hover_right_arm_band");
                    if (i == 4 && part == StrapPart.Buckle) Shot("cl_straps_03_hover_torso_buckle");
                    yield return Click(); yield return new WaitForSeconds(0.35f);
                    Check(OnlyToggled(before, i), slots[tool] + ": PREP click on the " + part + " toggles strap " + i + " only (now " + (S.restraints[i] ? "closed" : "open") + ")");
                    if (facts != null && part == StrapPart.Band && i == 0)
                        Check(!facts.restraints.hands && facts.restraints.feet, "closing the left ARM strap cut the hand zip-tie; the foot tie is still on");
                    if (facts != null && part == StrapPart.Band && i == 2)
                        Check(!facts.restraints.feet, "closing the left LEG strap cut the foot zip-tie");
                }
            }
            // A bare shoulder with a syringe never offers a strap (Fedya: the syringe over the right shoulder offered the torso).
            yield return Select(Key.Digit2, ToolSlot.Anesthesia);
            if (view.CameraMode != TableCamera.Prep) { yield return Tap(Key.Tab); yield return new WaitForSeconds(0.5f); }
            yield return AimBody(t => t.kind == TargetKind.Body, new[] { BodyPart.ShoulderR }, "bare right shoulder");
            Check(aimed && view.Current.target.kind != TargetKind.Strap, "syringe over the bare right shoulder: no strap action offered");
            // OPERATION view: straps are never targets there.
            yield return Tap(Key.Tab); yield return new WaitForSeconds(0.5f);
            var strapRenderer = table.StrapTransform(1).GetComponentInChildren<Renderer>();
            yield return MoveTo(Scr(strapRenderer.bounds.center), 0.15f);
            var closedBefore = (bool[])S.restraints.Clone();
            Check(view.CameraMode == TableCamera.Operation && view.Current.target.kind != TargetKind.Strap, "OPERATION view never offers a strap");
            yield return Click(); yield return new WaitForSeconds(0.25f);
            bool unchanged = true; for (int j = 0; j < 5; j++) unchanged &= S.restraints[j] == closedBefore[j];
            Check(unchanged, "a click in the OPERATION view changes no strap");
            yield return Tap(Key.Tab); yield return new WaitForSeconds(0.5f);

            // ---- close all five, then wake him: the closed straps hold the struggling patient ----
            yield return Select(Key.Digit1, ToolSlot.Hands);
            for (int i = 0; i < 5; i++)
            {
                if (S.restraints[i]) continue;
                yield return ClAimStrap(i, StrapPart.Band); yield return Click(); yield return new WaitForSeconds(0.35f);
            }
            Check(S.restraints[0] && S.restraints[1] && S.restraints[2] && S.restraints[3] && S.restraints[4], "all five straps closed by clicks");
            Shot("cl_straps_04_all_closed");
            // Fixture: the anesthesia wears off (time passes).
            S.sleepRemaining = 0f; S.residual = 0f; S.dazedRemaining = 0f;
            yield return new WaitForSeconds(1f);
            var rig = table.PatientRig;
            Check(S.alive && !S.Sleeping && S.onTable, "he is awake on the table");
            float wait = table.Tuning.escapeSeconds + 1f, end = Time.time + wait; bool limbsHeld = true;
            while (Time.time < end) { if (rig != null) for (int l = 0; l < 4; l++) limbsHeld &= rig.LimbMotion[l] == 0f; yield return null; }
            Check(S.onTable && S.aligned && S.escapes == 0 && S.escapeProgress == 0f, "awake for " + wait.ToString("F0") + " s with the straps closed: he struggles but stays on the table");
            Check(limbsHeld, "strapped arms and legs never flail while he struggles");
            Shot("cl_straps_05_struggle_strapped");
            // Torso open: he starts wriggling free; an open arm strap lets that arm flail, the strapped one stays down.
            yield return ClAimStrap(4, StrapPart.Buckle); yield return Click();
            yield return new WaitForSeconds(1.5f);
            Check(!S.restraints[4] && S.escapeProgress > 0f, "torso strap open: he starts wriggling toward the edge");
            yield return ClAimStrap(0, StrapPart.Buckle); yield return Click();
            yield return new WaitForSeconds(0.8f);
            Check(rig != null && !S.restraints[0] && rig.LimbMotion[0] > 0f && rig.LimbMotion[1] == 0f, "the unstrapped left arm flails, the strapped right arm stays held");
            Shot("cl_straps_06_torso_and_left_arm_open");
            yield return ClAimStrap(4, StrapPart.Band); yield return Click();
            yield return ClAimStrap(0, StrapPart.Band); yield return Click();
            yield return new WaitForSeconds(0.4f);
            Check(S.restraints[4] && S.restraints[0] && S.escapeProgress == 0f && S.onTable, "torso closed again in time: the escape stops, he is still on the table");
            S.sleepRemaining = 120f; // fixture: asleep again for whatever runs next
            yield return Tap(Key.Escape); yield return new WaitForSeconds(table.Tuning.cameraBlendSeconds + 0.1f);
        }
#endif
    }
}
